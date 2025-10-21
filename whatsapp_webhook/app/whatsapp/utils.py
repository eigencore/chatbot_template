# app/whatsapp/utils.py
import logging 
import json, asyncio, time
from fastapi import Request, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette import status
from redis.asyncio import Redis
from app.core.settings import settings

# ====== Config ======
WINDOW_MS = 4000  # 4s de ventana (ajústalo a 1500–3000 ms)
DEDUP_TTL_S = 60 * 60
TIMER_GRACE_MS = 5000  # margen para expiración del timer
LOCK_TTL_MS = 5000     # para evitar doble procesamiento

redis: Redis | None = None

# Logger
logging.basicConfig(level=logging.INFO)

async def get_redis() -> Redis:
    global redis
    if not redis:
        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis

def _k_buf(uid):   return f"wa:{uid}:buf"
def _k_timer(uid): return f"wa:{uid}:timer"
def _k_lock(uid):  return f"wa:{uid}:lock"
def _k_dedup(mid): return f"wa:dedup:{mid}"

def is_valid_whatsapp_message(body) -> bool:
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )

def _extract_msg(body):
    value = body["entry"][0]["changes"][0]["value"]
    contact = value["contacts"][0]
    msg = value["messages"][0]
    wa_id = contact["wa_id"]
    name = contact["profile"]["name"]
    msg_id = msg["id"]
    ts_ms = int(msg["timestamp"]) * 1000
    text = msg.get("text", {}).get("body", "").strip()
    return wa_id, name, msg_id, ts_ms, text

async def verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == settings.VERIFY_TOKEN:
            logging.info("WEBHOOK_VERIFIED")
            return PlainTextResponse(challenge, status_code=status.HTTP_200_OK)
        else:
            logging.info("VERIFICATION_FAILED")
            return JSONResponse({"status": "error", "message": "Verification failed"}, status_code=status.HTTP_403_FORBIDDEN)
    else:
        logging.info("MISSING_PARAMETER")
        return JSONResponse({"status": "error", "message": "Missing parameters"}, status_code=status.HTTP_400_BAD_REQUEST)

async def handle_message(request: Request, background: BackgroundTasks | None = None):
    try:
        body = await request.json()
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON")
        return JSONResponse({"status": "error", "message": "Invalid JSON provided"}, status_code=status.HTTP_400_BAD_REQUEST)

    # Status callback? Ignóralo rápido
    if body.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("statuses"):
        logging.info("Received a WhatsApp status update.")
        return JSONResponse({"status": "ok"}, status_code=status.HTTP_200_OK)

    if not is_valid_whatsapp_message(body):
        return JSONResponse({"status": "error", "message": "Not a WhatsApp API event"}, status_code=status.HTTP_404_NOT_FOUND)

    # # ---- Debounce + Buffer ----
    # r = await get_redis()
    wa_id, name, msg_id, ts_ms, text = _extract_msg(body)
    
    # # Check if user exists in DB (example usage of ORM)
    
    logging.info(f"Received message from {wa_id} ({name}): {text}")

    # # # Idempotencia: ignora reintentos del mismo msg_id
    # was_set = await r.set(_k_dedup(msg_id), "1", nx=True, ex=DEDUP_TTL_S)
    # if not was_set:
    #     return JSONResponse({"status": "ok"}, status_code=status.HTTP_200_OK)

    # # Mete al buffer como JSONL
    # item = json.dumps({"id": msg_id, "ts": ts_ms, "text": text})
    # await r.rpush(_k_buf(wa_id), item)
    # await r.expire(_k_buf(wa_id), DEDUP_TTL_S)

    # # (Re)programa timer (guardamos el fireAt en ms)
    # fire_at = int(time.time() * 1000) + WINDOW_MS
    # # Timer con expiración: si no llega nada, expira solo
    # await r.psetex(_k_timer(wa_id), WINDOW_MS + TIMER_GRACE_MS, str(fire_at))

    # # Dispara verificación luego de la ventana
    # if background is not None:
    #     background.add_task(_schedule_try_process, wa_id, WINDOW_MS)
    # else:
    #     # fallback si llamas sin BackgroundTasks
    #     asyncio.create_task(_schedule_try_process(wa_id, WINDOW_MS))

    return JSONResponse({"status": "ok"}, status_code=status.HTTP_200_OK)

async def _schedule_try_process(wa_id: str, delay_ms: int):
    await asyncio.sleep((delay_ms + 50) / 1000.0)
    print(f"Procesando mensajes para {wa_id}...")
    try:
        await try_process(wa_id)
    except Exception as e:
        logging.exception(f"try_process error for {wa_id}: {e}")

async def try_process(wa_id: str):
    r = await get_redis()
    tkey = _k_timer(wa_id)
    fire_at_str = await r.get(tkey)
    if not fire_at_str:
        # Hubo mensaje nuevo o ya se procesó
        return
    if int(time.time() * 1000) < int(fire_at_str):
        # Aún dentro de ventana; algún otro task lo revisará
        return

    # Evita doble procesamiento concurrente
    lock_key = _k_lock(wa_id)
    got_lock = await r.set(lock_key, "1", nx=True, px=LOCK_TTL_MS)
    if not got_lock:
        return  # otro worker lo tomará

    try:
        # Verifica de nuevo el timer (double-check)
        fire_at_str = await r.get(tkey)
        if not fire_at_str or int(time.time() * 1000) < int(fire_at_str):
            return

        # Extrae todo el buffer
        buf_key = _k_buf(wa_id)
        msgs_raw = []
        while True:
            item = await r.lpop(buf_key)
            if not item:
                break
            msgs_raw.append(item)
        # Borra el timer para esta tanda
        await r.delete(tkey)

        if not msgs_raw:
            return

        msgs = [json.loads(x) for x in msgs_raw]
        msgs.sort(key=lambda m: m["ts"])  # orden temporal

        # Construye el bloque/turno
        prompt = _join_messages(msgs)
        
        print(f"→ Mensajes recibidos de {wa_id}: {prompt}")

        # Aquí pones tu integración NLU/LLM o tus reglas
        reply = generate_reply(prompt)
        
        print(f"← Respuesta generada para {wa_id}: {reply}")

        # Envía UNA sola respuesta
        await send_whatsapp_message(wa_id, reply)

    finally:
        # Suelta el lock
        await r.delete(lock_key)

def _join_messages(msgs: list[dict]) -> str:
    # Une con puntuación simple (puedes personalizar)
    parts = []
    for m in msgs:
        t = (m.get("text") or "").strip()
        if not t:
            continue
        # evita duplicar puntos
        if t.endswith((".", "?", "¡", "!", "¿")):
            parts.append(t)
        else:
            parts.append(t + ".")
    return " ".join(parts).strip()

def generate_reply(prompt: str) -> str:
    # Ejemplo tonto; reemplázalo con tu motor
    if any(w in prompt.lower() for w in ["cotizacion", "cotización"]):
        return "¡Claro! Para cotizar, dime: producto/servicio, cantidad y ciudad de entrega."
    return "¡Gracias! ¿En qué puedo ayudarte?"

async def send_whatsapp_message(to_wa_id: str, text: str):
    # Implementa tu cliente WhatsApp (Cloud API/proveedor)
    # p.ej. con httpx y tu PHONE_NUMBER_ID + access_token
    logging.info(f"→ Respondiendo a {to_wa_id}: {text}")
