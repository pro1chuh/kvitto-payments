# Kvitto Payments

API для приёма платежей онлайн-школы.

Стек: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2 и SQLite.
Все суммы передаются и хранятся как целые числа в копейках.

## Возможности

- Тарифы `basic`, `standard` и `premium`.
- Создание платежей картой, через СБП или в рассрочку.
- Промокод `KVITTO10` со скидкой 10%.
- Идемпотентность по заголовку `Idempotency-Key`.
- Вебхук банка с проверкой допустимых переходов статусов.
- HMAC-SHA256 подпись вебхука через `WEBHOOK_SECRET`.
- Фильтрация платежей по email и статусу.

## Быстрый запуск через Docker

Это рекомендуемый способ запуска.

1. Запустите Docker Desktop и дождитесь статуса `Engine running`.
2. В терминале WSL откройте папку проекта.
3. Убедитесь, что Docker доступен:

   ```bash
   docker info
   ```

4. Соберите образ и запустите сервис:

   ```bash
   docker compose -p kvitto-payments up --build
   ```

После запуска доступны:

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- OpenAPI: http://localhost:8000/openapi.json

Для запуска в фоне:

```bash
docker compose -p kvitto-payments up --build -d
docker compose -p kvitto-payments logs -f
```

Остановить сервис:

```bash
docker compose -p kvitto-payments down
```

SQLite хранится в Docker volume, поэтому данные сохраняются после перезапуска контейнера.

## Локальный запуск без Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Для Windows PowerShell активация виртуального окружения:

```powershell
.venv\Scripts\Activate.ps1
```

## Тесты и линтер

```bash
pip install -r requirements-dev.txt
pytest -q
ruff check .
```

## Переменные окружения

- `DATABASE_URL`: строка подключения к БД. Значение по умолчанию: `sqlite:///./payments.db`.
- `WEBHOOK_SECRET`: секрет для подписи вебхука. Если переменная не задана, проверка подписи отключена.

## Примеры запросов

Получить тарифы:

```bash
curl http://127.0.0.1:8000/tariffs
```

Создать платёж в рассрочку с промокодом:

```bash
curl -X POST http://127.0.0.1:8000/payments \
  -H "Content-Type: application/json" \
  -d '{"tariff_id":2,"email":"student@example.com","method":"installment","installment_months":3,"promo_code":"kvitto10"}'
```

Создать идемпотентный платёж:

```bash
curl -X POST http://127.0.0.1:8000/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: order-42" \
  -d '{"tariff_id":1,"email":"student@example.com","method":"card"}'
```

Получить платёж:

```bash
curl http://127.0.0.1:8000/payments/1
```

Отправить вебхук без подписи. Работает, когда `WEBHOOK_SECRET` не задан:

```bash
curl -X POST http://127.0.0.1:8000/webhooks/bank \
  -H "Content-Type: application/json" \
  -d '{"payment_id":1,"status":"succeeded"}'
```

Отправить подписанный вебхук:

```bash
BODY='{"payment_id":1,"status":"succeeded"}'
SIGNATURE=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -hex | sed 's/^.* //')
curl -X POST http://127.0.0.1:8000/webhooks/bank \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"
```

## Принятые решения

- Несуществующий `tariff_id` и неизвестный промокод возвращают 422.
- `installment_months` допустим только для способа оплаты `installment`.
- Повторная установка статуса запрещена и возвращает `409` с телом `{"error":"invalid_transition"}`.
- Повторный `Idempotency-Key` возвращает первоначальный платёж с кодом 200.
- Пустой `promo_code` считается неизвестным промокодом и возвращает 422.
- `GET /payments` сортирует записи по `id` по возрастанию.
- Время создания платежа хранится в UTC.