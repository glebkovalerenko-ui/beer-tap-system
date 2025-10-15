# backend/security.py
from datetime import datetime, timedelta, timezone # Добавляем timezone
from jose import JWTError, jwt
from typing import Annotated # Добавляем Annotated
from sqlalchemy.orm import Session # Добавляем Session

# Импортируем все необходимое из FastAPI и от нашего приложения
from fastapi import Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from database import get_db
from crud import audit_crud
import schemas

# --- НАСТРОЙКИ ---
SECRET_KEY = "your-very-secret-key-that-should-be-in-env-file"
ALGORITHM = "HS256" # Исправлено на HS256, так как это стандарт
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- ВРЕМЕННАЯ БАЗА ДАННЫХ ПОЛЬЗОВАТЕЛЕЙ (заглушка) ---
FAKE_USERS_DB = {
    "admin": {
        "username": "admin",
        "full_name": "Admin User",
        "hashed_password": "fake_password"
    }
}

# --- ОСНОВНАЯ ЛОГИКА ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

def get_user(username: str):
    if username in FAKE_USERS_DB:
        return FAKE_USERS_DB[username]
    return None

def create_access_token(data: dict):
    to_encode = data.copy()
    # Исправлено на современный, timezone-aware способ работы с UTC
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    request: Request,
    background_tasks: BackgroundTasks,
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)]
) -> dict: # Явно указываем тип возвращаемого значения
    """
    Зависимость, которая:
    1. Проверяет JWT-токен.
    2. Возвращает данные пользователя.
    3. В фоновом режиме добавляет задачу для записи в журнал аудита,
       если метод запроса изменяет состояние (POST, PUT, DELETE).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user(username) # В будущем это будет crud.get_user(db, ...)
    if user is None:
        raise credentials_exception

    # --- НОВАЯ ЛОГИКА АУДИТА ---
    # Мы будем добавлять задачу в фон только для запросов, меняющих состояние
    if request.method in ["POST", "PUT", "DELETE"]:
        action = f"{request.method}_{request.url.path}"
        
        # Добавляем задачу, которая выполнится ПОСЛЕ успешного ответа эндпоинта.
        # Она будет использовать ту же сессию `db`, которая была передана в эндпоинт.
        background_tasks.add_task(
            audit_crud.create_audit_log,
            db=db,
            actor_id=user["username"],
            action=action
        )
    
    return user