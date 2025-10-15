import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Импортируем ключевые компоненты нашего приложения
from main import app
from database import Base, get_db

# 1. Определяем URL для тестовой базы данных SQLite в памяти.
# connect_args - это хак, необходимый только для SQLite, чтобы он работал с FastAPI.
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool, # Используем StaticPool для SQLite в памяти
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2. Создаем функцию-заменитель для нашей зависимости `get_db`.
def override_get_db():
    """
    Эта функция будет вызываться вместо `get_db` во время выполнения тестов,
    предоставляя сессию к нашей временной базе данных в памяти.
    """
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# 3. Применяем "магию" FastAPI: заменяем зависимость во всем приложении.
app.dependency_overrides[get_db] = override_get_db

# 4. Создаем главную фикстуру `pytest`, которую будут использовать наши тесты.
@pytest.fixture(scope="function")
def client():
    """
    Эта фикстура подготавливает все необходимое для одного теста:
    - Создает таблицы в временной БД.
    - Предоставляет тестовый клиент для отправки запросов.
    - Удаляет таблицы после завершения теста.
    """
    # Создаем все таблицы перед каждым тестом
    Base.metadata.create_all(bind=engine)
    
    # `yield` передает управление тесту, который использует эту фикстуру.
    # `TestClient` позволяет делать "виртуальные" запросы к нашему FastAPI приложению.
    with TestClient(app) as c:
        yield c
    
    # После того как тест завершился, удаляем все таблицы.
    # Это гарантирует, что следующий тест начнется с абсолютно чистой БД.
    Base.metadata.drop_all(bind=engine)