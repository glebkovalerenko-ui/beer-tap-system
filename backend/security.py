# backend/security.py

from datetime import datetime, timedelta, timezone
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
SECRET_KEY = "your-very-secret-key-that-should-be-in-env-file"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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

INTERNAL_API_KEY = "demo-secret-key"

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
    print(f"DEBUG AUTH: Path: {request.url.path} | Headers: {dict(request.headers)}")
    received_token = request.headers.get("x-internal-token")

    if received_token and received_token.strip() == INTERNAL_API_KEY.strip():
        return {"username": "internal_rpi"}

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