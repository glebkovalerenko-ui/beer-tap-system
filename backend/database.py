# backend/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
# Это нужно, чтобы локально запущенное приложение тоже имело к ним доступ
load_dotenv()

# Формируем URL для подключения к БД из переменных окружения
# Если DATABASE_URL не задана, используется значение по умолчанию (для отладки)
DATABASE_URL = os.getenv("DATABASE_URL")

# Создаем "движок" SQLAlchemy - основной интерфейс для работы с БД
engine = create_engine(DATABASE_URL)

# Создаем фабрику сессий. Каждая сессия будет отдельной транзакцией с БД.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для всех наших будущих моделей SQLAlchemy
Base = declarative_base()

# Функция-зависимость (Dependency) для FastAPI.
# Она будет создавать новую сессию для каждого запроса и закрывать ее после выполнения.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()