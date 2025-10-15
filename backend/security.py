from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# --- НАСТРОЙКИ ---
SECRET_KEY = "your-very-secret-key-that-should-be-in-env-file"  # ЗАМЕНИТЬ НА СЕКРЕТ ИЗ .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- ВРЕМЕННАЯ БАЗА ДАННЫХ ПОЛЬЗОВАТЕЛЕЙ (заглушка) ---
# В будущем это будет заменено на реальную таблицу в PostgreSQL
FAKE_USERS_DB = {
    "admin": {
        "username": "admin",
        "full_name": "Admin User",
        "hashed_password": "fake_password" # В реальном приложении здесь будет хеш
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
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
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
    
    user = get_user(username)
    if user is None:
        raise credentials_exception
    return user