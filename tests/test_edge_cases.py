import hashlib
import hmac
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Payment
from app.routers import payments as payments_router

PRICES = {1: 990000, 2: 1990000, 3: 2990000}


def test_blank_idempotency_key_is_treated_as_missing(client: TestClient) -> None:
    body = {"tariff_id": 1, "email": "student@example.com", "method": "card"}

    first = client.post("/payments", json=body, headers={"Idempotency-Key": ""})
    second = client.post("/payments", json=body, headers={"Idempotency-Key": ""})

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_unique_violation_falls_back_to_existing_payment(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Имитация гонки: предварительный поиск ключа ничего не нашёл, но INSERT упёрся в UNIQUE."""
    body = {"tariff_id": 2, "email": "student@example.com", "method": "card"}
    headers = {"Idempotency-Key": "race-key"}
    first = client.post("/payments", json=body, headers=headers)
    monkeypatch.setattr(payments_router, "find_by_idempotency_key", lambda *_: None)

    second = client.post("/payments", json=body, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert session.scalar(select(func.count()).select_from(Payment)) == 1


@pytest.mark.parametrize("promo_code", [None, "kvitto10"])
@pytest.mark.parametrize("months", [3, 6, 12])
@pytest.mark.parametrize("tariff_id", [1, 2, 3])
def test_schedule_matches_amount_for_every_tariff(
    client: TestClient, tariff_id: int, months: int, promo_code: str | None
) -> None:
    price = PRICES[tariff_id]
    expected_discount = price * 10 // 100 if promo_code else 0

    response = client.post(
        "/payments",
        json={
            "tariff_id": tariff_id,
            "email": "student@example.com",
            "method": "installment",
            "installment_months": months,
            "promo_code": promo_code,
        },
    )

    body = response.json()
    schedule = body["schedule"]
    assert response.status_code == 201
    assert body["discount"] == expected_discount
    assert body["amount"] == price - expected_discount
    assert len(schedule) == months
    assert sum(schedule) == body["amount"]
    assert schedule == sorted(schedule, reverse=True)
    assert max(schedule) - min(schedule) <= 1


def test_wrong_signature_returns_401_and_keeps_status(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret")
    payment_id = client.post(
        "/payments",
        json={"tariff_id": 1, "email": "student@example.com", "method": "card"},
    ).json()["id"]
    body = f'{{"payment_id":{payment_id},"status":"succeeded"}}'.encode()
    wrong = hmac.new(b"other-secret", body, hashlib.sha256).hexdigest()

    response = client.post(
        "/webhooks/bank",
        content=body,
        headers={"Content-Type": "application/json", "X-Signature": wrong},
    )

    assert response.status_code == 401
    assert client.get(f"/payments/{payment_id}").json()["status"] == "pending"


def test_created_at_is_utc_with_offset(client: TestClient) -> None:
    response = client.post(
        "/payments",
        json={"tariff_id": 1, "email": "student@example.com", "method": "card"},
    )

    created_at = datetime.fromisoformat(response.json()["created_at"])
    assert created_at.tzinfo is not None
    assert created_at.utcoffset().total_seconds() == 0
