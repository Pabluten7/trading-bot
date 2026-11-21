"""Sincronización y consulta del universo en la base de datos."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import UniverseMember
from app.universe.loader import Constituent


@dataclass
class SyncResult:
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    reactivated: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.added or self.updated or self.removed or self.reactivated)

    def summary(self) -> str:
        return (
            f"añadidas={len(self.added)} actualizadas={len(self.updated)} "
            f"salidas={len(self.removed)} reactivadas={len(self.reactivated)}"
        )


def sync_universe(session: Session, constituents: list[Constituent]) -> SyncResult:
    """Deja la tabla igual que la lista recibida.

    Las empresas que salen del índice NO se borran: se marcan inactivas, para
    conservar el histórico (backtests y operaciones antiguas).
    """
    result = SyncResult()
    now = datetime.now(UTC)
    existing = {m.ticker: m for m in session.scalars(select(UniverseMember))}
    incoming = {c.ticker: c for c in constituents}

    for ticker, c in incoming.items():
        member = existing.get(ticker)
        if member is None:
            session.add(
                UniverseMember(
                    ticker=ticker,
                    name=c.name,
                    sector=c.sector,
                    sub_industry=c.sub_industry,
                    added_to_index=c.added_to_index,
                )
            )
            result.added.append(ticker)
            continue

        dirty = False
        for attr in ("name", "sector", "sub_industry", "added_to_index"):
            new = getattr(c, attr)
            if getattr(member, attr) != new:
                setattr(member, attr, new)
                dirty = True
        if not member.is_active:
            member.is_active = True
            member.removed_at = None
            result.reactivated.append(ticker)
        elif dirty:
            result.updated.append(ticker)

    for ticker, member in existing.items():
        if ticker not in incoming and member.is_active:
            member.is_active = False
            member.removed_at = now
            result.removed.append(ticker)

    session.commit()
    return result


def active_tickers(session: Session) -> list[str]:
    return list(
        session.scalars(
            select(UniverseMember.ticker)
            .where(UniverseMember.is_active.is_(True))
            .order_by(UniverseMember.ticker)
        )
    )


def sector_of(session: Session, ticker: str) -> str | None:
    return session.scalar(select(UniverseMember.sector).where(UniverseMember.ticker == ticker))


def sector_map(session: Session) -> dict[str, str]:
    """ticker -> sector de las empresas activas (para el filtro de máx. 3 por sector)."""
    rows = session.execute(
        select(UniverseMember.ticker, UniverseMember.sector).where(
            UniverseMember.is_active.is_(True)
        )
    )
    return {ticker: sector for ticker, sector in rows}


def count_by_sector(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(UniverseMember.sector, func.count())
        .where(UniverseMember.is_active.is_(True))
        .group_by(UniverseMember.sector)
        .order_by(UniverseMember.sector)
    )
    return {sector: n for sector, n in rows}
