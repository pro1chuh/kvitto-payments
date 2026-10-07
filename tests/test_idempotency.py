from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Payment


def payment_payload(email: str = "student@example.com") -> dict[str, object]:
    return {"tariff_id": 2, "email": email, "method": "card"}


def test_same_idempotency_key_returns_original_payment(
    client: TestClient, session: Session
) -> None:
    headers = {"Idempotency-Key": "request-123"}
    first = client.post("/payments", json=payment_payload(), headers=headers)
    second = client.post("/payments", json=payment_payload("another@example.com"), headers=headers)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["email"] == "student@example.com"
    assert session.scalar(select(func.count()).select_from(Payment)) == 1


def test_requests_without_idempotency_key_create_separate_payments(client: TestClient) -> None:
    first = client.post("/payments", json=payment_payload())
    second = client.post("/payments", json=payment_payload())

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
