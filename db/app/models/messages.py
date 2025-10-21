from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import expression

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .conversations import Conversation


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(TimestampMixin, Base):
    """Single message exchanged within a conversation."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role", create_type=False),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(
        Boolean,
        server_default=expression.false(),
        nullable=False,
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"Message(id={self.id!r}, conversation_id={self.conversation_id!r})"
