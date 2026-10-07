import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.enums import PaymentStatus
from app.models import Payment
from app.services.statuses import can_transition


def create_payment(client: TestClient) -> int:
    response = client.post(
        "/payments",
        json={"tariff_id": 1, "email": "student@example.com", "method": "card"},
    )
    return response.json()["id"]


def test_webhook_changes_status_along_allowed_chain(client: TestClient) -> None:
    payment_id = create_payment(client)

    succeeded = client.post(
        "/webhooks/bank", json={"payment_id": payment_id, "status": "succeeded"}
    )
    refunded = client.post("/webhooks/bank", json={"payment_id": payment_id, "status": "refunded"})

    assert succeeded.status_code == 200
    assert succeeded.json() == {"result": "ok"}
    assert refunded.status_code == 200
    assert client.get(f"/payments/{payment_id}").json()["status"] == "refunded"


def test_webhook_rejects_invalid_transition_without_changing_status(client: TestClient) -> None:
    payment_id = create_payment(client)

    response = client.post("/webhooks/bank", json={"payment_id": payment_id, "status": "refunded"})

    assert response.status_code == 409
    assert response.json() == {"error": "invalid_transition"}
    assert client.get(f"/payments/{payment_id}").json()["status"] == "pending"


def test_webhook_returns_404_for_unknown_payment(client: TestClient) -> None:
    response = client.post("/webhooks/bank", json={"payment_id": 99, "status": "succeeded"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Payment not found"}


@pytest.mark.parametrize("current", list(PaymentStatus))
@pytest.mark.parametrize("new", list(PaymentStatus))
def test_every_status_pair_has_expected_result(
    client: TestClient, session: Session, current: PaymentStatus, new: PaymentStatus
) -> None:
    payment = Payment(
        status=current.value,
        tariff_id=1,
        amount=990000,
        discount=0,
        method="card",
        email="student@example.com",
    )
    session.add(payment)
    session.commit()

    response = client.post("/webhooks/bank", json={"payment_id": payment.id, "status": new.value})

    if can_transition(current, new):
        assert response.status_code == 200
        assert response.json() == {"result": "ok"}
        assert session.get(Payment, payment.id).status == new.value
    else:
        assert response.status_code == 409
        assert response.json() == {"error": "invalid_transition"}
        assert session.get(Payment, payment.id).status == current.value


def test_webhook_rejects_unknown_status(client: TestClient) -> None:
    response = client.post("/webhooks/bank", json={"payment_id": 1, "status": "unknown"})

    assert response.status_code == 422
