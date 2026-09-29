"""seed dim_country - catálogo de países del calendario económico

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-29 00:10 UTC

`0001` crea `dim_country` (country_code, country_name, region, currency_code)
y `0002` siembra `dim_asset`/`dim_time`/`dim_trading_session`, pero el país
nunca se cargó: el catálogo quedaba **vacío** tras `alembic upgrade head`.

Como `fact_economic_event.country` referencia `dim_country(country_code)`
(`fact_economic_event_country_fkey`), cualquier carga del calendario
económico en una BD nueva fallaba por violación de FK.

Esta revisión siembra los 11 países del calendario económico (los mismos
`country_code` presentes en la BD viva y en `fact_economic_event`):

    AU, CA, CH, CN, DE, ES, FR, GB, IT, JP, US

Idempotente: `INSERT ... ON CONFLICT (country_code) DO UPDATE`, de modo que
re-ejecutarla sincroniza `country_name`/`region`/`currency_code` con el
catálogo de referencia sin duplicar ni desalinear las filas existentes.

Los archivos 0001-0006 ya aplicados no se tocan.

Uso: `cd proy_bd_heatmap && ./venv/bin/alembic upgrade head`.
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

# country_code, country_name, region, currency_code
_PAISES = (
    ("AU", "Australia", "Oceania", "AUD"),
    ("CA", "Canada", "Americas", "CAD"),
    ("CH", "Switzerland", "Europe", "CHF"),
    ("CN", "China", "Asia", "CNY"),
    ("DE", "Germany", "Europe", "EUR"),
    ("ES", "Spain", "Europe", "EUR"),
    ("FR", "France", "Europe", "EUR"),
    ("GB", "United Kingdom", "Europe", "GBP"),
    ("IT", "Italy", "Europe", "EUR"),
    ("JP", "Japan", "Asia", "JPY"),
    ("US", "United States", "Americas", "USD"),
)

_VALORES = ",\n    ".join(
    f"('{code}', '{name}', '{region}', '{cur}')" for code, name, region, cur in _PAISES
)

_DATOS = f"""
INSERT INTO public.dim_country
    (country_code, country_name, region, currency_code)
VALUES
    {_VALORES}
ON CONFLICT (country_code) DO UPDATE
   SET country_name  = EXCLUDED.country_name,
       region        = EXCLUDED.region,
       currency_code = EXCLUDED.currency_code;
"""

_CODIGOS = [c for c, *_ in _PAISES]

_DOWNGRADE = """
DELETE FROM public.dim_country c
 WHERE c.country_code = ANY(%s)
   AND NOT EXISTS (SELECT 1 FROM public.fact_economic_event e
                    WHERE e.country = c.country_code);
"""


def upgrade():
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DATOS)


def downgrade():
    """Borra los países sembrados por esta revisión.

    Se omiten los que ya tengan eventos en `fact_economic_event` (FK): el
    downgrade deja el catálogo íntegro antes que romper la integridad.
    """
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DOWNGRADE, (_CODIGOS,))
