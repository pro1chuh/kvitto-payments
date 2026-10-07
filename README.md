# Kvitto Payments

Небольшой сервис приёма платежей онлайн-школы. Реализован на Python 3.11+, FastAPI,
SQLAlchemy 2 (синхронный режим), Pydantic 2 и SQLite.

Все суммы передаются и хранятся как целые числа в копейках.

## Запуск

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

На macOS/Linux вместо активации выше используйте `source .venv/bin/activate`.

## Проверки

```bash
pip install -r requirements-dev.txt
pytest -q
ruff check .
```

## Переменные окружения

- `DATABASE_URL` — URL базы данных; по умолчанию `sqlite:///./payments.db`.
- `WEBHOOK_SECRET` — секрет HMAC вебхука. Пустое или отсутствующее значение отключает
  проверку подписи.

## Примеры API

```bash
curl http://127.0.0.1:8000/tariffs
```

```bash
curl -X POST http://127.0.0.1:8000/payments \
  -H "Content-Type: application/json" \
  -d '{"tariff_id":2,"email":"student@example.com","method":"installment","installment_months":3,"promo_code":"kvitto10"}'
```

```bash
curl -X POST http://127.0.0.1:8000/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: order-42" \
  -d '{"tariff_id":1,"email":"student@example.com","method":"card"}'
```

```bash
curl http://127.0.0.1:8000/payments/1
```

```bash
BODY='{"payment_id":1,"status":"succeeded"}'
SIGNATURE=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -hex | sed 's/^.* //')
curl -X POST http://127.0.0.1:8000/webhooks/bank \
  -H "Content-Type: application/json" -H "X-Signature: $SIGNATURE" -d "$BODY"
```

## Docker

```bash
docker compose up
```

## Принятые решения

- Несуществующий `tariff_id` и неизвестный промокод возвращают 422 с FastAPI-совместимым
  списком ошибок.
- `installment_months` допустим только для `installment`; для `card` и `sbp` это 422.
- Повторная установка того же статуса запрещена и возвращает `409 invalid_transition`.
- Повторный `Idempotency-Key` возвращает первоначальный платёж с `200`, даже при другом теле.
- Пустой `promo_code` не считается отсутствующим и даёт 422.
- Список платежей отсортирован по возрастанию `id`.
- Время создания хранится в UTC.
