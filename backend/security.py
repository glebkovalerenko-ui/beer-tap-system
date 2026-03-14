# backend/security.py

from datetime import datetime, timedelta, timezone
import os
import logging
from jose import JWTError, jwt
from typing import Annotated
from sqlalchemy.orm import Session

from fastapi import Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
# --- ИЗМЕНЕНИЕ: импортируем SessionLocal для создания сессий в фоне ---
from database import get_db, SessionLocal
from crud import audit_crud
import schemas

# --- НАСТРОЙКИ (без изменений) ---
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

if SECRET_KEY == "dev-only-secret-key-change-in-production":
    logging.warning("SECRET_KEY is not set. Using development fallback value; do not use in production.")

# --- ВРЕМЕННАЯ БАЗА ДАННЫХ ПОЛЬЗОВАТЕЛЕЙ (без изменений) ---
FAKE_USERS_DB = {
    "admin": {
        "username": "admin",
        "full_name": "Admin User",
        "hashed_password": "fake_password"
    }
}

# --- ОСНОВНАЯ ЛОГИКА (без изменений) ---
# Изменение параметра auto_error для OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token", auto_error=False)

def get_user(username: str):
    if username in FAKE_USERS_DB:
        return FAKE_USERS_DB[username]
    return None

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def _normalize_token(value: str | None) -> str:
    if value is None:
        return ""
    normalized = value.strip()
    # Частая проблема: токен передается в кавычках из env/systemd/docker.
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {'"', "'"}:
        normalized = normalized[1:-1].strip()
    return normalized

def _env_flag(name: str, default: bool = False) -> bool:
    fallback = "true" if default else "false"
    return os.getenv(name, fallback).strip().lower() in {"1", "true", "yes", "on"}

def _get_env_token_set(*, primary_name: str, multi_name: str) -> set[str]:
    keys: set[str] = set()

    primary = _normalize_token(os.getenv(primary_name, ""))
    if primary:
        keys.add(primary)

    multi = _normalize_token(os.getenv(multi_name, ""))
    if multi:
        for raw in multi.split(","):
            token = _normalize_token(raw)
            if token:
                keys.add(token)

    return keys

def _get_internal_api_keys() -> set[str]:
    """
    Возвращает набор допустимых internal API токенов.

    Поддерживает:
    - INTERNAL_API_KEY (основной ключ)
    - INTERNAL_API_KEYS (список ключей через запятую для безопасной ротации)
    - INTERNAL_TOKEN (legacy-переменная для совместимости с rpi-controller)
    """
    keys = _get_env_token_set(primary_name="INTERNAL_API_KEY", multi_name="INTERNAL_API_KEYS")

    legacy = _normalize_token(os.getenv("INTERNAL_TOKEN", ""))
    if legacy:
        keys.add(legacy)

    # Для разработки/демо можно всегда держать legacy-ключ совместимости.
    if _env_flag("ALLOW_LEGACY_DEMO_INTERNAL_TOKEN", default=True):
        keys.add("demo-secret-key")

    # Fallback, если никаких ключей не задано.
    if not keys:
        keys.add("demo-secret-key")

    return keys

def _get_display_api_keys() -> set[str]:
    return _get_env_token_set(primary_name="DISPLAY_API_KEY", multi_name="DISPLAY_API_KEYS")

# --- Функция-обертка для фоновой задачи ---
def audit_log_task_wrapper(
    actor_id: str,
    action: str
):
    """
    Эта обертка создает свою собственную сессию БД, выполняет логирование
    и закрывает сессию.
    """
    db = SessionLocal() # Создаем новую, независимую сессию
    try:
        audit_crud.create_audit_log_entry(
            db=db,
            actor_id=actor_id,
            action=action
        )
    finally:
        db.close()


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

def _authenticate_bearer_user(token: str | None) -> dict:
    credentials_exception = _credentials_exception()

    if token is None:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user(username)
    if user is None:
        raise credentials_exception
    return user

def _maybe_schedule_audit_log(
    *,
    request: Request,
    background_tasks: BackgroundTasks,
    actor_id: str,
) -> None:
    if request.method in ["POST", "PUT", "DELETE"]:
        action = f"{request.method}_{request.url.path}"
        background_tasks.add_task(
            audit_log_task_wrapper,
            actor_id=actor_id,
            action=action
        )

def _authenticate_named_token(
    *,
    request: Request,
    header_name: str,
    allowed_tokens: set[str],
    actor_id: str,
    warning_message: str,
) -> dict | None:
    received_token = _normalize_token(request.headers.get(header_name))
    if not received_token:
        return None

    if received_token in allowed_tokens:
        return {"username": actor_id}

    logging.warning(warning_message, request.url.path)
    raise _credentials_exception()

async def get_current_user(
    request: Request,
    background_tasks: BackgroundTasks,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)]
) -> dict:
    user = _authenticate_bearer_user(token)
    _maybe_schedule_audit_log(
        request=request,
        background_tasks=background_tasks,
        actor_id=user["username"],
    )
    return user

async def get_internal_service_user(
    request: Request,
    background_tasks: BackgroundTasks,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)]
) -> dict:
    internal_principal = _authenticate_named_token(
        request=request,
        header_name="x-internal-token",
        allowed_tokens=_get_internal_api_keys(),
        actor_id="internal_rpi",
        warning_message="Internal token rejected for path %s. Check INTERNAL_API_KEY/INTERNAL_TOKEN alignment.",
    )
    if internal_principal is not None:
        return internal_principal
    return await get_current_user(request, background_tasks, token, db)

async def get_display_reader(
    request: Request,
    background_tasks: BackgroundTasks,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)]
) -> dict:
    display_keys = _get_display_api_keys()
    if request.headers.get("x-display-token") and not display_keys:
        logging.warning(
            "Display token presented for path %s, but DISPLAY_API_KEY/DISPLAY_API_KEYS are not configured.",
            request.url.path,
        )

    display_principal = _authenticate_named_token(
        request=request,
        header_name="x-display-token",
        allowed_tokens=display_keys,
        actor_id="display_agent",
        warning_message="Display token rejected for path %s. Check DISPLAY_API_KEY/DISPLAY_API_KEYS alignment.",
    )
    if display_principal is not None:
        return display_principal
    return await get_current_user(request, background_tasks, token, db)
