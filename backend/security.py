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
ALLOW_LEGACY_DEMO_INTERNAL_TOKEN = os.getenv("ALLOW_LEGACY_DEMO_INTERNAL_TOKEN", "true").strip().lower() in {"1", "true", "yes", "on"}

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

def _get_internal_api_keys() -> set[str]:
    """
    Возвращает набор допустимых internal API токенов.

    Поддерживает:
    - INTERNAL_API_KEY (основной ключ)
    - INTERNAL_API_KEYS (список ключей через запятую для безопасной ротации)
    - INTERNAL_TOKEN (legacy-переменная для совместимости с rpi-controller)
    """
    keys: set[str] = set()

    primary = _normalize_token(os.getenv("INTERNAL_API_KEY", ""))
    if primary:
        keys.add(primary)

    multi = _normalize_token(os.getenv("INTERNAL_API_KEYS", ""))
    if multi:
        for raw in multi.split(","):
            token = _normalize_token(raw)
            if token:
                keys.add(token)

    legacy = _normalize_token(os.getenv("INTERNAL_TOKEN", ""))
    if legacy:
        keys.add(legacy)

    # Для разработки/демо можно всегда держать legacy-ключ совместимости.
    if ALLOW_LEGACY_DEMO_INTERNAL_TOKEN:
        keys.add("demo-secret-key")

    # Fallback, если никаких ключей не задано.
    if not keys:
        keys.add("demo-secret-key")

    return keys

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


async def get_current_user(
    request: Request,
    background_tasks: BackgroundTasks,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)]
) -> dict:
    received_token = _normalize_token(request.headers.get("x-internal-token"))

    allowed_internal_keys = _get_internal_api_keys()
    if received_token and received_token in allowed_internal_keys:
        return {"username": "internal_rpi"}

    if received_token and received_token not in allowed_internal_keys:
        logging.warning(
            "Internal token rejected for path %s. Check INTERNAL_API_KEY/INTERNAL_TOKEN alignment.",
            request.url.path,
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

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

    if request.method in ["POST", "PUT", "DELETE"]:
        action = f"{request.method}_{request.url.path}"
        background_tasks.add_task(
            audit_log_task_wrapper,
            actor_id=user["username"],
            action=action
        )

    return user