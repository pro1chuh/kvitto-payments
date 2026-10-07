PROMO_CODE = "KVITTO10"
PROMO_PERCENT = 10


def apply_promo(price: int, promo_code: str | None) -> tuple[int, int, str | None]:
    if promo_code is None:
        return price, 0, None

    normalized_code = promo_code.strip().upper()
    if normalized_code != PROMO_CODE:
        raise ValueError("Unknown promo code")

    discount = price * PROMO_PERCENT // 100
    return price - discount, discount, normalized_code


def build_schedule(amount: int, months: int) -> list[int]:
    base, remainder = divmod(amount, months)
    return [base + 1] * remainder + [base] * (months - remainder)
