from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .conversations import Conversation


class User(TimestampMixin, Base):
    """Chatbot end user stored in the database."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, phone_number={self.phone_number!r})"
    
