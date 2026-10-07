from app.enums import PaymentStatus

ALLOWED_TRANSITIONS = {
    PaymentStatus.pending: {PaymentStatus.succeeded, PaymentStatus.failed},
    PaymentStatus.succeeded: {PaymentStatus.refunded},
    PaymentStatus.failed: set(),
    PaymentStatus.refunded: set(),
}


def can_transition(current: PaymentStatus, new: PaymentStatus) -> bool:
    return new in ALLOWED_TRANSITIONS[current]
