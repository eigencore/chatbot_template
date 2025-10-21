# app/api/routes/whatsapp_webhook.py
from fastapi import APIRouter, Request, Depends, BackgroundTasks
from app.whatsapp.utils import handle_message, verify
from app.api.deps.security import signature_required

whatsapp_webhook_router = APIRouter()

@whatsapp_webhook_router.get("/webhook")
async def webhook_get(request: Request):
    return await verify(request)

@whatsapp_webhook_router.post("/webhook")
async def webhook_post(request: Request, background: BackgroundTasks, _=Depends(signature_required)):
    return await handle_message(request, background)
