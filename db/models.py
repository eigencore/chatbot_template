from sqlalchemy import (
    Table, Column, MetaData, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

metadata = MetaData()

# USERS
users = Table(
    "users", metadata,
    Column("id", UUID(as_uuid=False), primary_key=True),
    Column("phone_number", String(32), nullable=False, unique=True),  # E.164 recomendado
    Column("email", String(255), nullable=True, unique=True),
    Column("name", String(128), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

# CONVERSATIONS (por usuario y canal)
conversations = Table(
    "conversations", metadata,
    Column("id", UUID(as_uuid=False), primary_key=True),
    Column("user_id", UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("channel", String(32), nullable=False, server_default="whatsapp"),  # futuro multi-canal
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)
Index("ix_conversations_user_id", conversations.c.user_id)

# SESSIONS (sub-conversación temporal alineada a ventana 24h)
sessions = Table(
    "sessions", metadata,
    Column("id", UUID(as_uuid=False), primary_key=True),
    Column("conversation_id", UUID(as_uuid=False), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
    Column("is_active", Boolean, server_default="true", nullable=False),
    Column("started_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=True),  # opcional: 24h desde primer mensaje
    Column("ended_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)
Index("ix_sessions_conversation_active", sessions.c.conversation_id, sessions.c.is_active)

# MESSAGES
message_role = Enum("user", "assistant", "system", name="message_role")
delivery_status = Enum("queued", "sent", "delivered", "read", "failed", name="delivery_status")

messages = Table(
    "messages", metadata,
    Column("id", UUID(as_uuid=False), primary_key=True),
    Column("session_id", UUID(as_uuid=False), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
    Column("channel_id", String(255), unique=True, nullable=True),  # ID del mensaje en canal externo
    Column("role", message_role, nullable=False),
    Column("message_type", String(32), nullable=False, server_default="text"),  # text|image|...
    Column("content", Text, nullable=True),  
    Column("status", delivery_status, nullable=False, server_default="queued"), # queued|sent|delivered|read|failed
    Column("status_updated_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)
Index("ix_messages_session_created", messages.c.session_id, messages.c.created_at)
Index("ix_messages_status", messages.c.status)

