# security.py (FastAPI)
import logging
import hashlib
import hmac
from fastapi import Request, HTTPException, status

from app.core.settings import settings


def validate_signature(payload: bytes, signature: str) -> bool:
    """
    Validate the incoming payload's signature against our expected signature
    using the app secret stored in FastAPI's app.state.
    """
    app_secret = settings.APP_SECRET
    if not app_secret:
        logging.error("APP_SECRET is not configured")
        raise HTTPException(status_code=500, detail="Server not configured")

    expected_signature = hmac.new(
        bytes(app_secret, "latin-1"),
        msg=payload,  # use raw bytes to avoid encoding issues
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


async def signature_required(request: Request):
    """
    Dependency to ensure that the incoming requests to our webhook are valid
    and signed with the correct signature.
    """
    header = request.headers.get("X-Hub-Signature-256", "")
    signature = header[7:] if header.startswith("sha256=") else header  # remove 'sha256='

    body = await request.body()  # raw bytes

    if not validate_signature(body, signature):
        logging.info("Signature verification failed!")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid signature",
        )
