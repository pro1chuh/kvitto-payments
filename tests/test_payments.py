from fastapi.testclient import TestClient


def test_create_installment_payment(client: TestClient) -> None:
    response = client.post(
        "/payments",
        json={
            "tariff_id": 2,
            "email": "student@example.com",
            "method": "installment",
            "installment_months": 3,
            "promo_code": "kvitto10",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["amount"] == 1791000
    assert body["discount"] == 199000
    assert body["schedule"] == [597000, 597000, 597000]
    assert "promo_code" not in body
    assert "idempotency_key" not in body


def test_card_payment_has_no_schedule(client: TestClient) -> None:
    response = client.post(
        "/payments",
        json={"tariff_id": 1, "email": "student@example.com", "method": "card"},
    )

    assert response.status_code == 201
    assert response.json()["schedule"] is None


def test_get_unknown_payment_returns_404(client: TestClient) -> None:
    response = client.get("/payments/99")

    assert response.status_code == 404
    assert response.json() == {"detail": "Payment not found"}


def test_payment_validation(client: TestClient) -> None:
    invalid_requests = [
        {"tariff_id": 1, "email": "student@example.com", "method": "installment"},
        {
            "tariff_id": 1,
            "email": "student@example.com",
            "method": "installment",
            "installment_months": 5,
        },
        {
            "tariff_id": 1,
            "email": "student@example.com",
            "method": "card",
            "installment_months": 3,
        },
        {"tariff_id": 1, "email": "not-an-email", "method": "card"},
    ]

    for payload in invalid_requests:
        assert client.post("/payments", json=payload).status_code == 422


def test_unknown_tariff_and_promo_return_422(client: TestClient) -> None:
    unknown_tariff = client.post(
        "/payments",
        json={"tariff_id": 99, "email": "student@example.com", "method": "card"},
    )
    unknown_promo = client.post(
        "/payments",
        json={
            "tariff_id": 1,
            "email": "student@example.com",
            "method": "card",
            "promo_code": "wrong",
        },
    )

    assert unknown_tariff.status_code == 422
    assert unknown_tariff.json()["detail"][0]["loc"] == ["body", "tariff_id"]
    assert unknown_promo.status_code == 422
    assert unknown_promo.json()["detail"][0]["loc"] == ["body", "promo_code"]


def test_list_payments_filters_by_case_insensitive_email_and_status(client: TestClient) -> None:
    first = client.post(
        "/payments",
        json={"tariff_id": 1, "email": "Student@Example.com", "method": "card"},
    ).json()
    second = client.post(
        "/payments",
        json={"tariff_id": 2, "email": "other@example.com", "method": "card"},
    ).json()
    client.post("/webhooks/bank", json={"payment_id": second["id"], "status": "succeeded"})

    by_email = client.get("/payments", params={"email": "student@example.com"})
    by_status = client.get("/payments", params={"status": "succeeded"})

    assert [payment["id"] for payment in by_email.json()] == [first["id"]]
    assert [payment["id"] for payment in by_status.json()] == [second["id"]]
