"""Tests del watchdog de frescura del score (job H).

Cubre la lógica de decisión del job con un Container falso (sin BD real) y una
prueba de integración del SQL contra la BD scratch del docker.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

import jobs.check_score_freshness as job

PROJECT_PATH = Path(__file__).resolve().parent.parent


class _StubSettings:
    """Settings mínimos: `business` devuelve el default (20 min)."""

    def business(self, *keys, default=None):
        return default


class _FakeRepo:
    def __init__(self, edad):
        self._edad = edad

    def fetch_agg_edad_minutos(self):
        return self._edad


class _FakeContainer:
    def __init__(self, edad, *, habilitada=True):
        self.db_habilitada = habilitada
        self.score_repo = _FakeRepo(edad)
        self.cerrado = False

    def close(self):
        self.cerrado = True


def _preparar(monkeypatch, container):
    """Sustituye settings, logging y Container.build por dobles."""
    monkeypatch.setattr(job, "get_settings", lambda: _StubSettings())
    monkeypatch.setattr(job, "setup_global_logging", lambda *a, **k: None)
    monkeypatch.setattr(job.Container, "build", classmethod(lambda cls, **k: container))
    return container


# --- Lógica de decisión ------------------------------------------------------


def test_fresco_sale_0(monkeypatch):
    _preparar(monkeypatch, _FakeContainer(2.0))
    assert job.run([]) == 0


def test_rancio_sale_5(monkeypatch):
    _preparar(monkeypatch, _FakeContainer(120.0))
    assert job.run([]) == 5


def test_rancio_en_el_limite_no_falla(monkeypatch):
    # 20.0 no es > 20 → fresco (el umbral es estricto)
    _preparar(monkeypatch, _FakeContainer(20.0))
    assert job.run([]) == 0


def test_rancio_dry_run_sale_0(monkeypatch):
    _preparar(monkeypatch, _FakeContainer(120.0))
    assert job.run(["--dry-run"]) == 0


def test_tabla_vacia_sale_5(monkeypatch):
    # Sin ningún ciclo el retraso es infinito → rancio.
    _preparar(monkeypatch, _FakeContainer(None))
    assert job.run([]) == 5


def test_tabla_vacia_dry_run_sale_0(monkeypatch):
    _preparar(monkeypatch, _FakeContainer(None))
    assert job.run(["--dry-run"]) == 0


def test_bd_no_configurada_sale_3(monkeypatch):
    _preparar(monkeypatch, _FakeContainer(1.0, habilitada=False))
    assert job.run([]) == 3


def test_umbral_override(monkeypatch):
    _preparar(monkeypatch, _FakeContainer(30.0))
    assert job.run([]) == 5  # 30 > 20 (default)
    assert job.run(["--max-edad-min", "60"]) == 0  # 30 < 60


def test_error_de_consulta_sale_1(monkeypatch):
    class _RepoMalo:
        def fetch_agg_edad_minutos(self):
            raise RuntimeError("boom")

    container = _FakeContainer(1.0)
    container.score_repo = _RepoMalo()
    _preparar(monkeypatch, container)
    assert job.run([]) == 1


def test_siempre_cierra_el_container(monkeypatch):
    container = _preparar(monkeypatch, _FakeContainer(1.0))
    job.run([])
    assert container.cerrado is True


# --- Launcher: el modo de fallo que costó 16 h -------------------------------


def test_launcher_falla_ruidosamente_sin_env(tmp_path):
    """Sin `.env` el launcher debe salir 4 y decir por qué, no seguir en silencio."""
    destino = tmp_path / "run_check_score_freshness.sh"
    shutil.copy2(PROJECT_PATH / "run_check_score_freshness.sh", destino)

    r = subprocess.run([str(destino)], capture_output=True, text=True)

    assert r.returncode == 4
    assert "falta .env" in r.stderr


def test_launcher_es_ejecutable():
    script = PROJECT_PATH / "run_check_score_freshness.sh"
    assert script.is_file()
    assert script.stat().st_mode & 0o111


# --- Integración del SQL (BD scratch docker) ---------------------------------


def test_repo_edad_minutos_docker(docker_connector):
    from repositories import ScoreRepository

    repo = ScoreRepository(docker_connector)
    docker_connector.execute("DELETE FROM fact_market_score_agg")
    try:
        assert repo.fetch_agg_edad_minutos() is None  # tabla vacía → None

        docker_connector.execute(
            "INSERT INTO fact_market_score_agg (timestamp_utc, score_market) "
            "VALUES (now() - interval '90 minutes', 5.0)"
        )
        edad = repo.fetch_agg_edad_minutos()
        assert edad is not None
        assert 89.0 <= edad <= 92.0
    finally:
        docker_connector.execute("DELETE FROM fact_market_score_agg")


@pytest.mark.parametrize("umbral,edad,esperado", [(20, 5, 0), (20, 25, 5)])
def test_tabla_de_decision(monkeypatch, umbral, edad, esperado):
    _preparar(monkeypatch, _FakeContainer(float(edad)))
    assert job.run(["--max-edad-min", str(umbral)]) == esperado
