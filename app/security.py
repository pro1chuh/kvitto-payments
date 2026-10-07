import hashlib
import hmac
import os

from fastapi import HTTPException, Request, status


async def verify_signature(request: Request) -> None:
    secret = os.getenv("WEBHOOK_SECRET")
    if not secret:
        return

    signature = request.headers.get("X-Signature")
    expected_signature = hmac.new(
        secret.encode(), await request.body(), hashlib.sha256
    ).hexdigest()
    if signature is None or not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")
