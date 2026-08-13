import pytest

from app.database.connection import database
from app.database.health import check_database_connection
from app.database.initializer import database_initializer


def test_database_initializes():
    database.initialize()

    assert database.is_initialized is True


def test_database_connection():
    database.initialize()

    assert check_database_connection() is True


def test_database_initializer():
    database_initializer.initialize()

    assert database_initializer.initialized is True
    
def test_database_get_session():
    database.initialize()

    session = database.get_session()

    try:
        assert session.is_active is True
    finally:
        session.close()


def test_database_get_session_requires_initialization():
    database.dispose()

    with pytest.raises(
        RuntimeError,
        match="Database has not been initialized",
    ):
        database.get_session()