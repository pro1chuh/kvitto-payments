from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.enums import PaymentMethod, PaymentStatus
from app.models import Payment, Tariff
from app.schemas import PaymentCreate
from app.services.pricing import apply_promo, build_schedule
from app.services.statuses import can_transition


def get_payment(session: Session, payment_id: int) -> Payment | None:
    return session.get(Payment, payment_id)


def find_by_idempotency_key(session: Session, key: str) -> Payment | None:
    return session.scalar(select(Payment).where(Payment.idempotency_key == key))


def create_payment(
    session: Session, data: PaymentCreate, tariff: Tariff, idempotency_key: str | None = None
) -> tuple[Payment, bool]:
    amount, discount, promo_code = apply_promo(tariff.price, data.promo_code)
    schedule = (
        build_schedule(amount, data.installment_months)
        if data.method == PaymentMethod.installment
        else None
    )
    payment = Payment(
        tariff_id=tariff.id,
        amount=amount,
        discount=discount,
        method=data.method.value,
        installment_months=data.installment_months,
        schedule=schedule,
        email=str(data.email),
        promo_code=promo_code,
        idempotency_key=idempotency_key,
    )
    session.add(payment)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        if idempotency_key is None:
            raise
        existing_payment = find_by_idempotency_key(session, idempotency_key)
        if existing_payment is None:
            raise
        return existing_payment, True
    session.refresh(payment)
    return payment, False


def get_tariff(session: Session, tariff_id: int) -> Tariff | None:
    return session.scalar(select(Tariff).where(Tariff.id == tariff_id))


def list_payments(
    session: Session, email: str | None = None, status: PaymentStatus | None = None
) -> list[Payment]:
    statement = select(Payment).order_by(Payment.id)
    if email is not None:
        statement = statement.where(func.lower(Payment.email) == email.lower())
    if status is not None:
        statement = statement.where(Payment.status == status.value)
    return list(session.scalars(statement))


def change_status(session: Session, payment_id: int, new_status: PaymentStatus) -> str:
    payment = get_payment(session, payment_id)
    if payment is None:
        return "not_found"

    current_status = PaymentStatus(payment.status)
    if not can_transition(current_status, new_status):
        return "invalid_transition"

    result = session.execute(
        update(Payment)
        .where(Payment.id == payment_id, Payment.status == current_status.value)
        .values(status=new_status.value)
    )
    if result.rowcount != 1:
        session.rollback()
        return "invalid_transition"
    session.commit()
    return "ok"
