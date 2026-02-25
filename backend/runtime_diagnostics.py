import uuid

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.orm import Session


def get_request_id(request: Request) -> str:
    raw = request.headers.get("x-request-id", "").strip()
    return raw or uuid.uuid4().hex


def get_db_identity(db: Session) -> str:
    bind = db.get_bind()
    if bind is None or getattr(bind, "url", None) is None:
        return "unknown"

    url = bind.url
    host = getattr(url, "host", None) or "local"
    port = getattr(url, "port", None) or "-"
    name = getattr(url, "database", None) or "-"
    return f"{host}:{port}/{name}"


def get_alembic_revision(db: Session) -> str:
    try:
        revision = db.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
    except Exception:
        db.rollback()
        return "unknown"

    return str(revision) if revision else "unknown"
