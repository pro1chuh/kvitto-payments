from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import WebhookIn
from app.security import verify_signature
from app.services.payments import change_status

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/bank", dependencies=[Depends(verify_signature)])
def bank_webhook(
    data: WebhookIn, session: Session = Depends(get_session)  # noqa: B008
) -> JSONResponse:
    result = change_status(session, data.payment_id, data.status)
    if result == "not_found":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Payment not found"}
        )
    if result == "invalid_transition":
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT, content={"error": "invalid_transition"}
        )
    return JSONResponse(content={"result": "ok"})
