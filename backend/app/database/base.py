"""
SQLAlchemy declarative base.

All persistent database models inherit from Base.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.
    """

    pass