import json
import redis
from app.core.settings import settings

DEBOUNCE_SEC = 1.5  # ventana de 1.5 segundos

r = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def buf_key(wa_id):
    return f"ws:buf:{wa_id}"

async def push_message_to_buffer(wa_id: str, message: dict):
    """Agrega un mensaje (como JSON) al buffer del usuario."""
    await r.rpush(buf_key(wa_id), json.dumps(message))

async def pop_all_messages_from_buffer(wa_id: str):
    """Extrae todos los mensajes del buffer (y los borra)."""
    key = buf_key(wa_id)
    messages = []
    while True:
        msg_json = await r.lpop(key)
        if msg_json is None:
            break
        messages.append(json.loads(msg_json))
    return messages


def debounce_key(wa_id):
    return f"ws:debounce:{wa_id}"

def try_start_debounce(wa_id: str, ttl: float = DEBOUNCE_SEC) -> bool:
    """
    Crea la clave de debounce si no existe.
    Devuelve True si se creó (es decir, hay que programar un flush),
    False si ya había una ventana activa.
    """
    return r.set(debounce_key(wa_id), "1", nx=True, ex=int(ttl)) is True

def clear_debounce(wa_id: str):
    """Elimina la clave de debounce (una vez procesado el buffer)."""
    r.delete(debounce_key(wa_id))
