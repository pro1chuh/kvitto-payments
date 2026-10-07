from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Tariff


def test_tariffs_are_seeded_once(client: TestClient, session: Session) -> None:
    response = client.get("/tariffs")

    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "title": "basic", "price": 990000},
        {"id": 2, "title": "standard", "price": 1990000},
        {"id": 3, "title": "premium", "price": 2990000},
    ]
    assert session.scalar(select(func.count()).select_from(Tariff)) == 3
