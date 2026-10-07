from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.enums import PaymentStatus
from app.models import Payment
from app.schemas import PaymentCreate, PaymentOut
from app.services.payments import (
    create_payment,
    find_by_idempotency_key,
    get_payment,
    get_tariff,
    list_payments,
)
from app.services.pricing import apply_promo

router = APIRouter(tags=["payments"])


@router.post("/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def make_payment(
    data: PaymentCreate,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),  # noqa: B008
) -> Payment:
    if idempotency_key is not None and not idempotency_key.strip():
        idempotency_key = None  # пустой заголовок = ключ не передан
    if idempotency_key is not None:
        existing_payment = find_by_idempotency_key(session, idempotency_key)
        if existing_payment is not None:
            response.status_code = status.HTTP_200_OK
            return existing_payment
    tariff = get_tariff(session, data.tariff_id)
    if tariff is None:
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "type": "value_error",
                    "loc": ["body", "tariff_id"],
                    "msg": "Value error, Tariff not found",
                    "input": data.tariff_id,
                }
            ],
        )
    try:
        apply_promo(tariff.price, data.promo_code)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "type": "value_error",
                    "loc": ["body", "promo_code"],
                    "msg": "Value error, Unknown promo code",
                    "input": data.promo_code,
                }
            ],
        ) from None
    payment, is_repeat = create_payment(session, data, tariff, idempotency_key)
    if is_repeat:
        response.status_code = status.HTTP_200_OK
    return payment


@router.get("/payments", response_model=list[PaymentOut])
def read_payments(  # noqa: B008
    email: str | None = None,
    payment_status: PaymentStatus | None = Query(default=None, alias="status"),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> list[Payment]:
    return list_payments(session, email, payment_status)


@router.get("/payments/{payment_id}", response_model=PaymentOut)
def read_payment(payment_id: int, session: Session = Depends(get_session)) -> Payment:  # noqa: B008
    payment = get_payment(session, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment
