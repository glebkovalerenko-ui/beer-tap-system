# alembic/env.py (Синхронная версия)

from logging.config import fileConfig

# --- ШАГ 1: Добавляем импорты для доступа к нашим моделям ---
import os
import sys
# Добавляем корневую директорию 'backend' в системный путь Python.
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
# --- КОНЕЦ ШАГА 1 ---

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# --- ШАГ 2: Импортируем 'Base' из наших моделей ---
from models import Base
# --- КОНЕЦ ШАГА 2 ---


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- ШАГ 3: Указываем Alembic на метаданные наших моделей ---
target_metadata = Base.metadata
# --- КОНЕЦ ШАГА 3 ---


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    (Этот раздел остается без изменений)
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
    
    В этой версии мы полностью удаляем асинхронную логику (asyncio)
    и используем стандартный синхронный подход.
    """

    # Мы программно создаем URL для подключения,
    # читая переменные окружения напрямую с помощью Python.
    # Это самый надежный способ, который обходит проблемы парсинга .ini файла.
    db_url = "postgresql://{user}:{password}@{host}/{db}".format(
        user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD"),
        host=os.environ.get("POSTGRES_HOST", "postgres"), # Используем 'postgres' как хост по умолчанию
        db=os.environ.get("POSTGRES_DB"),
    )
    # Принудительно устанавливаем опцию 'sqlalchemy.url' в конфигурации Alembic.
    # Теперь все, что написано в alembic.ini, будет проигнорировано в пользу этого URL.
    config.set_main_option('sqlalchemy.url', db_url)

    # Создаем "connectable" - объект, который знает, как подключиться к БД,
    # используя конфигурацию из alembic.ini
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Используем этот connectable для установления соединения
    with connectable.connect() as connection:
        # Настраиваем контекст Alembic для работы с этим соединением
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        # Выполняем миграции внутри транзакции
        with context.begin_transaction():
            context.run_migrations()


# Главный логический блок.
# Он остался почти без изменений, но теперь `run_migrations_online`
# является синхронной функцией.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()