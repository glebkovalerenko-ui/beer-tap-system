import logging
from urllib.parse import urlsplit, urlunsplit

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine
from alembic.runtime.migration import MigrationContext


def redact_database_url(database_url: str | None) -> str:
    if not database_url:
        return "<missing>"

    parts = urlsplit(database_url)
    hostname = parts.hostname or ""
    if parts.username:
        hostname = f"{parts.username}:***@{hostname}"
    elif parts.password:
        hostname = f":***@{hostname}"

    if parts.port:
        hostname = f"{hostname}:{parts.port}"

    return urlunsplit((parts.scheme, hostname, parts.path, parts.query, parts.fragment))


def verify_database_ready(engine: Engine, database_url: str | None) -> None:
    logger = logging.getLogger("startup")
    safe_database_url = redact_database_url(database_url)

    if not database_url:
        logger.error("Database startup check failed: DATABASE_URL is not set")
        raise RuntimeError("DATABASE_URL is not set")

    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
            current_revision = MigrationContext.configure(connection).get_current_revision()
    except SQLAlchemyError as exc:
        logger.error(
            "Database startup check failed: DATABASE_URL=%s error=%s",
            safe_database_url,
            exc,
        )
        raise RuntimeError("Database is not reachable") from exc

    alembic_config = Config("alembic.ini")
    head_revisions = ScriptDirectory.from_config(alembic_config).get_heads()

    if current_revision not in head_revisions:
        logger.error(
            "Database migration check failed: DATABASE_URL=%s current_revision=%s heads=%s",
            safe_database_url,
            current_revision or "<none>",
            ",".join(head_revisions),
        )
        raise RuntimeError("Database schema is not migrated to the current head")

    logger.info(
        "Database startup check passed: DATABASE_URL=%s current_revision=%s",
        safe_database_url,
        current_revision,
    )
