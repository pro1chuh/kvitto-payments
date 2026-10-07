import pytest

from app.enums import PaymentStatus
from app.services.pricing import apply_promo, build_schedule
from app.services.statuses import can_transition


def test_apply_promo_normalizes_code_and_calculates_integer_discount() -> None:
    amount, discount, promo_code = apply_promo(1990000, " KvItTo10 ")

    assert (amount, discount, promo_code) == (1791000, 199000, "KVITTO10")


def test_apply_promo_without_code_keeps_price() -> None:
    assert apply_promo(990000, None) == (990000, 0, None)


@pytest.mark.parametrize("promo_code", ["", "other"])
def test_apply_promo_rejects_unknown_code(promo_code: str) -> None:
    with pytest.raises(ValueError, match="Unknown promo code"):
        apply_promo(990000, promo_code)


@pytest.mark.parametrize("months", [3, 6, 12])
def test_installment_schedule_has_exact_total(months: int) -> None:
    schedule = build_schedule(1990000, months)

    assert sum(schedule) == 1990000
    assert len(schedule) == months


def test_installment_remainder_is_in_first_payments() -> None:
    assert build_schedule(1990000, 3) == [663334, 663333, 663333]


def test_status_transition_rules() -> None:
    assert can_transition(PaymentStatus.pending, PaymentStatus.succeeded)
    assert can_transition(PaymentStatus.pending, PaymentStatus.failed)
    assert can_transition(PaymentStatus.succeeded, PaymentStatus.refunded)
    assert not can_transition(PaymentStatus.succeeded, PaymentStatus.succeeded)
    assert not can_transition(PaymentStatus.failed, PaymentStatus.succeeded)
