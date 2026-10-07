from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_serializer, model_validator

from app.enums import PaymentMethod, PaymentStatus


class TariffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    price: int


class PaymentCreate(BaseModel):
    tariff_id: int
    email: EmailStr
    method: PaymentMethod
    installment_months: int | None = None
    promo_code: str | None = None

    @model_validator(mode="after")
    def validate_installment(self) -> "PaymentCreate":
        if self.method == PaymentMethod.installment:
            if self.installment_months not in {3, 6, 12}:
                raise ValueError("installment_months must be 3, 6, or 12")
        elif self.installment_months is not None:
            raise ValueError("installment_months is only allowed for installment")
        return self


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: PaymentStatus
    tariff_id: int
    amount: int
    discount: int
    method: PaymentMethod
    installment_months: int | None
    schedule: list[int] | None
    email: EmailStr
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        # SQLite возвращает время без часового пояса; в БД оно хранится в UTC
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.isoformat()


class WebhookIn(BaseModel):
    payment_id: int
    status: PaymentStatus
