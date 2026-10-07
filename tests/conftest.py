import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session, init_db
from app.main import create_app


@pytest.fixture
def session() -> Session:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(test_engine)
    with Session(test_engine) as test_session:
        yield test_session
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def client(session: Session) -> TestClient:
    application = create_app()

    def get_test_session():
        yield session

    application.dependency_overrides[get_session] = get_test_session
    with TestClient(application) as test_client:
        yield test_client
    application.dependency_overrides.clear()
