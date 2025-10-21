import os
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.engine import URL

from alembic import context

from app.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def load_env_file(filename: str = ".env") -> None:
    """Populate os.environ with values from a dotenv file if present."""
    base_dir = Path(config.config_file_name or ".").resolve().parent
    env_path = (base_dir / filename).resolve()
    if not env_path.is_file():
        return

    with env_path.open("r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def get_database_url() -> str | None:
    """Build the database URL from environment variables."""
    if url := os.getenv("DATABASE_URL"):
        return url

    host = os.getenv("BD_HOST")
    user = os.getenv("BD_USER")
    password = os.getenv("BD_PASSWORD")
    name = os.getenv("BD_NAME")
    driver = os.getenv("BD_DRIVER", "postgresql")

    port_raw = os.getenv("BD_PORT")
    port = int(port_raw) if port_raw else None

    if not (host and user and name):
        return None

    return URL.create(
        drivername=driver,
        username=user,
        password=password,
        host=host,
        port=port,
        database=name,
    ).render_as_string(hide_password=False)


load_env_file()

if database_url := get_database_url():
    config.set_main_option("sqlalchemy.url", database_url)

# Register project metadata for autogeneration.
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
