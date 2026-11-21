import pytest
from sqlalchemy import select

from app.db.models import UniverseMember
from app.universe import loader
from app.universe.loader import Constituent, UniverseError, parse_constituents
from app.universe.service import (
    active_tickers,
    count_by_sector,
    sector_map,
    sector_of,
    sync_universe,
)

HEADER = "Symbol,Security,GICS Sector,GICS Sub-Industry,Date added\n"


def _csv(rows: list[str]) -> str:
    return HEADER + "\n".join(rows) + "\n"


@pytest.fixture(autouse=True)
def _rango_pequeno(monkeypatch):
    """Los tests usan listas cortas: relajamos el control de tamaño."""
    monkeypatch.setattr(loader, "MIN_EXPECTED", 1)


def _c(ticker, sector="Information Technology", name=None):
    return Constituent(ticker=ticker, name=name or ticker, sector=sector)


# ── Lectura del CSV ─────────────────────────────────────────────────────────
def test_parsea_filas_validas():
    cs = parse_constituents(
        _csv(
            [
                "aapl,Apple Inc.,Information Technology,Hardware,1982-11-30",
                "JPM,JPMorgan,Financials,,",
            ]
        )
    )
    assert cs[0].ticker == "AAPL"
    assert cs[0].added_to_index.year == 1982
    assert cs[1].sub_industry is None and cs[1].added_to_index is None


def test_falla_si_faltan_columnas():
    with pytest.raises(UniverseError, match="columnas"):
        parse_constituents("Symbol,Security\nAAPL,Apple\n")


def test_falla_con_ticker_duplicado():
    with pytest.raises(UniverseError, match="duplicado"):
        parse_constituents(_csv(["AAPL,Apple,IT,,", "AAPL,Apple,IT,,"]))


def test_falla_con_sector_vacio():
    with pytest.raises(UniverseError, match="vacío"):
        parse_constituents(_csv(["AAPL,Apple,,,"]))


def test_falla_si_el_numero_de_empresas_es_absurdo(monkeypatch):
    monkeypatch.setattr(loader, "MIN_EXPECTED", 450)
    with pytest.raises(UniverseError, match="inesperado"):
        parse_constituents(_csv(["AAPL,Apple,IT,,"]))


def test_fecha_mal_formada_no_invalida_la_lista():
    cs = parse_constituents(_csv(["AAPL,Apple,IT,,no-es-fecha"]))
    assert cs[0].added_to_index is None


# ── Sincronización ──────────────────────────────────────────────────────────
def test_primera_carga_inserta_todo(session):
    r = sync_universe(session, [_c("AAPL"), _c("JPM", "Financials")])
    assert sorted(r.added) == ["AAPL", "JPM"] and not r.removed
    assert active_tickers(session) == ["AAPL", "JPM"]


def test_sincronizar_dos_veces_no_cambia_nada(session):
    lista = [_c("AAPL"), _c("JPM", "Financials")]
    sync_universe(session, lista)
    r = sync_universe(session, lista)
    assert not r.changed
    assert len(session.scalars(select(UniverseMember)).all()) == 2


def test_empresa_que_sale_se_marca_inactiva_no_se_borra(session):
    sync_universe(session, [_c("AAPL"), _c("GE")])
    r = sync_universe(session, [_c("AAPL")])
    assert r.removed == ["GE"]
    ge = session.scalars(select(UniverseMember).where(UniverseMember.ticker == "GE")).one()
    assert ge.is_active is False and ge.removed_at is not None
    assert active_tickers(session) == ["AAPL"]
    assert sector_of(session, "GE") == "Information Technology"  # el histórico se conserva


def test_empresa_que_vuelve_se_reactiva(session):
    sync_universe(session, [_c("AAPL"), _c("GE")])
    sync_universe(session, [_c("AAPL")])
    r = sync_universe(session, [_c("AAPL"), _c("GE")])
    assert r.reactivated == ["GE"]
    ge = session.scalars(select(UniverseMember).where(UniverseMember.ticker == "GE")).one()
    assert ge.is_active and ge.removed_at is None


def test_cambio_de_sector_se_actualiza(session):
    sync_universe(session, [_c("GOOGL", "Information Technology")])
    r = sync_universe(session, [_c("GOOGL", "Communication Services")])
    assert r.updated == ["GOOGL"]
    assert sector_of(session, "GOOGL") == "Communication Services"


# ── Consultas ───────────────────────────────────────────────────────────────
def test_consultas_ignoran_inactivas(session):
    sync_universe(
        session, [_c("AAPL"), _c("MSFT"), _c("JPM", "Financials"), _c("GE", "Industrials")]
    )
    sync_universe(session, [_c("AAPL"), _c("MSFT"), _c("JPM", "Financials")])
    assert sector_map(session) == {
        "AAPL": "Information Technology",
        "MSFT": "Information Technology",
        "JPM": "Financials",
    }
    assert count_by_sector(session) == {"Financials": 1, "Information Technology": 2}
    assert sector_of(session, "NOEXISTE") is None


# ── Lista incluida en el repo ───────────────────────────────────────────────
def test_la_lista_incluida_es_valida(monkeypatch):
    monkeypatch.undo()  # sin relajar el control de tamaño: debe cumplir el rango real
    cs = loader.load_from_file()
    assert 450 <= len(cs) <= 550
    assert len({c.ticker for c in cs}) == len(cs)
    sectores = {c.sector for c in cs}
    assert len(sectores) == 11  # los 11 sectores GICS
    assert {"AAPL", "MSFT", "JPM"} <= {c.ticker for c in cs}


def test_cli_carga_la_lista_incluida(tmp_path, monkeypatch, capsys):
    import sys

    from alembic import command
    from app.core.config import get_settings
    from app.db import session as db_session
    from app.universe import __main__ as cli
    from tests.test_migrations import _cfg

    db = f"sqlite:///{tmp_path / 'u.db'}"
    monkeypatch.setenv("DATABASE_URL", db)
    monkeypatch.setattr(db_session, "_engine", None)
    monkeypatch.setattr(sys, "argv", ["app.universe", "sync"])
    monkeypatch.setattr(loader, "MIN_EXPECTED", 450)
    get_settings.cache_clear()
    try:
        command.upgrade(_cfg(db), "head")
        cli.main()
    finally:
        get_settings.cache_clear()
    out = capsys.readouterr().out
    assert "añadidas=503" in out and "Information Technology" in out
