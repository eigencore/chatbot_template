"""create chatbot tables

Revision ID: aafb3209aa64
Revises: 
Create Date: 2025-10-20 16:13:40.042319

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

message_role_enum = postgresql.ENUM(
    "user",
    "assistant",
    "system",
    name="message_role",
    create_type=False,
)

# revision identifiers, used by Alembic.
revision: str = 'aafb3209aa64'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(sa.text("DROP TYPE IF EXISTS message_role CASCADE"))
    message_role_enum.create(op.get_bind(), checkfirst=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phone_number", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("phone_number", name="uq_users_phone_number"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", message_role_enum, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("read", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    message_role_enum.drop(op.get_bind(), checkfirst=False)

    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_table("conversations")

    op.drop_table("users")
