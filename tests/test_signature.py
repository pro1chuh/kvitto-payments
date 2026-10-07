import hashlib
import hmac

from fastapi.testclient import TestClient


def create_payment(client: TestClient) -> int:
    response = client.post(
        "/payments",
        json={"tariff_id": 1, "email": "student@example.com", "method": "card"},
    )
    return response.json()["id"]


def test_webhook_signature_is_optional_without_secret(client: TestClient) -> None:
    payment_id = create_payment(client)

    response = client.post("/webhooks/bank", json={"payment_id": payment_id, "status": "succeeded"})

    assert response.status_code == 200


def test_webhook_requires_valid_signature_when_secret_is_set(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret")
    payment_id = create_payment(client)
    body = f'{{"payment_id":{payment_id},"status":"succeeded"}}'.encode()
    signature = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()

    valid = client.post(
        "/webhooks/bank",
        content=body,
        headers={"Content-Type": "application/json", "X-Signature": signature},
    )
    missing = client.post(
        "/webhooks/bank", content=body, headers={"Content-Type": "application/json"}
    )

    assert valid.status_code == 200
    assert missing.status_code == 401
