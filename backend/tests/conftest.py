from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base
from app.db.session import make_engine


@pytest.fixture
def session() -> Iterator[Session]:
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(engine, expire_on_commit=False)() as s:
        yield s
    engine.dispose()
