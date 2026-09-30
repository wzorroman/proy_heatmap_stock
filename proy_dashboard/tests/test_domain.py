"""Tests del dominio — dataclasses puras."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from domain import (
    ActivoTick,
    ComponenteScore,
    EventoEconomico,
    RiesgoItem,
    ScoreActivo,
    ScoreMercado,
    SectorSnapshot,
)


def test_componente_score_es_inmutable():
    comp = ComponenteScore(nombre="rsi", valor=70.0, norm=0.7, peso=20.0)
    assert comp.norm == 0.7
    with pytest.raises(FrozenInstanceError):
        comp.peso = 10  # type: ignore[misc]


def test_score_activo_defaults_y_componentes():
    a = ScoreActivo(asset_id=1, symbol="NASDAQ:NVDA", score_general=7.5)
    b = ScoreActivo(asset_id=2, symbol="NASDAQ:AAPL", score_general=3.0)
    a.componentes.append(ComponenteScore("rsi", 70.0, 0.7, 20.0))

    assert a.zona == "NEUTRAL"
    assert len(a.componentes) == 1
    # listas por instancia (no compartidas)
    assert b.componentes == []


def test_score_mercado_defaults():
    ts = datetime(2026, 9, 30, 14, 0, tzinfo=timezone.utc)
    s = ScoreMercado(timestamp_utc=ts)

    assert s.score_momentum is None
    assert s.n_simbolos == 0
    assert s.pesos == {} and s.zonas == {}
    s.pesos["rsi"] = 20
    assert ScoreMercado(timestamp_utc=ts).pesos == {}


def test_activo_tick_campos():
    ts = datetime(2026, 9, 30, 14, 0, tzinfo=timezone.utc)
    tick = ActivoTick(asset_id=1039, symbol="AMEX:SPY", timestamp_utc=ts, asset_class="etf", close=764.35)

    assert tick.asset_class == "etf"
    assert tick.rsi_15 is None
    assert tick.cci20_15 is None


def test_sector_y_riesgo():
    sector = SectorSnapshot(sector="Finance", n_activos=199, change_medio=-0.42)
    assert sector.ganadores == 0

    riesgo = RiesgoItem(logical_key="VIX", symbol="TVC:VIX", valor=15.0, rsi=48.0, norm_dir=5.2)
    assert riesgo.estado == "NEUTRAL"


def test_evento_economico_defaults():
    ts = datetime(2026, 9, 30, 12, 30, tzinfo=timezone.utc)
    evento = EventoEconomico(event_id=1, title="CPI", event_timestamp=ts)

    assert evento.pasado is False
    assert evento.sorpresa_pct is None
    assert evento.importance is None
