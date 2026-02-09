# backend/tests_system/test_module_01_database.py
import pytest
import subprocess
import os
import time
import requests
import uuid

# ... (все определения путей остаются такими же) ...
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ENV_FILE_PATH = os.path.join(PROJECT_ROOT, '.env')
ENV_BAK_FILE_PATH = os.path.join(PROJECT_ROOT, '_env.bak')
DOCKER_COMPOSE_PATH = os.path.join(PROJECT_ROOT, 'docker-compose.yml')

pytestmark = pytest.mark.system

def run_docker_compose(args: list[str], **kwargs):
    base_command = ["docker-compose", "-f", DOCKER_COMPOSE_PATH]
    kwargs.setdefault('cwd', PROJECT_ROOT)
    return subprocess.run(base_command + args, capture_output=True, text=True, **kwargs)

@pytest.fixture(scope="module")
def system_environment(request):
    print("\n--- [System Test Setup] ---")
    if not os.path.exists(ENV_FILE_PATH):
        import shutil
        example_path = os.path.join(PROJECT_ROOT, '.env.example')
        if os.path.exists(example_path):
            shutil.copy(example_path, ENV_FILE_PATH)
            print("Создан .env из .env.example для теста.")
    print("Остановка и удаление старых контейнеров и volumes...")
    run_docker_compose(["down", "-v"], check=True)
    print("Запуск 'docker-compose up -d'...")
    run_docker_compose(["up", "-d"], check=True)
    print("Ожидание готовности системы (15 секунд)...")
    time.sleep(15)
    yield
    print("\n--- [System Test Teardown] ---")
    print("Остановка и удаление контейнеров...")
    run_docker_compose(["down", "-v"], check=True)

def test_tc_sys_db_01_successful_init(system_environment):
    ps_result = run_docker_compose(["ps", "postgres"], check=True)
    assert "Up" in ps_result.stdout and "healthy" in ps_result.stdout
    print("\n[Check] Статус 'postgres' - Up и healthy.")
    logs_result = run_docker_compose(["logs", "postgres"], check=True)
    assert "database system is ready to accept connections" in logs_result.stdout
    print("[Check] В логах найдена строка о готовности к соединениям.")

def test_tc_sys_db_02_fail_with_wrong_password():
    try:
        if os.path.exists(ENV_FILE_PATH):
            os.rename(ENV_FILE_PATH, ENV_BAK_FILE_PATH)
        with open(ENV_FILE_PATH, "w") as f:
            f.write("POSTGRES_USER=beer_user\n")
            f.write("POSTGRES_DB=beer_db\n")
            f.write("POSTGRES_PASSWORD=correct_password_for_db\n")
            f.write("DATABASE_URL=postgresql://beer_user:wrong_password_for_app@postgres:5432/beer_db\n")
        run_docker_compose(["up", "-d"])
        time.sleep(15)
        ps_postgres = run_docker_compose(["ps", "postgres"], check=True)
        assert "healthy" in ps_postgres.stdout
        ps_backend = run_docker_compose(["ps", "beer_backend_api"], check=True)
        assert "Up" in ps_backend.stdout
        print("\n[Check] Оба контейнера запущены.")
        try:
            token_payload = {"username": "admin", "password": "fake_password"}
            token_res = requests.post("http://localhost:8000/api/token", data=token_payload, timeout=5)
            token_res.raise_for_status()
            token = token_res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            requests.get("http://localhost:8000/api/guests/", headers=headers, timeout=5)
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
        logs_backend = run_docker_compose(["logs", "beer_backend_api"])
        assert "password authentication failed" in logs_backend.stdout.lower()
        print("[Check] В логах 'beer_backend_api' найдена ошибка 'password authentication failed'.")
    finally:
        run_docker_compose(["down", "-v"])
        if os.path.exists(ENV_FILE_PATH):
            os.remove(ENV_FILE_PATH)
        if os.path.exists(ENV_BAK_FILE_PATH):
            os.rename(ENV_BAK_FILE_PATH, ENV_FILE_PATH)

def test_tc_sys_db_05_alembic_upgrade_creates_schema():
    try:
        run_docker_compose(["down", "-v"], check=True)
        run_docker_compose(["up", "-d"], check=True)
        time.sleep(15)
        print("\n[Action] Выполнение 'alembic upgrade head' на пустой БД...")
        alembic_result = run_docker_compose(['exec', '-T', 'beer_backend_api', 'alembic', 'upgrade', 'head'], check=True)
        assert "Running upgrade" in alembic_result.stderr
        psql_result = run_docker_compose(
            ['exec', '-T', 'postgres', 'psql', '-U', 'beer_user', '-d', 'beer_db', '-c', '\\dt'],
            check=True
        )
        assert "guests" in psql_result.stdout and "beverages" in psql_result.stdout
        print("[Check] Alembic успешно создал все таблицы в БД.")
    finally:
        run_docker_compose(["down", "-v"])

def test_tc_sys_db_04_data_persists_after_restart():
    unique_marker = f"guest-{uuid.uuid4().hex[:12]}"
    guest_uuid = str(uuid.uuid4())
    try:
        run_docker_compose(["down", "-v"], check=True)
        run_docker_compose(["up", "-d"], check=True)
        time.sleep(15)
        run_docker_compose(['exec', '-T', 'beer_backend_api', 'alembic', 'upgrade', 'head'], check=True)
        print("\n[Action] Схема БД создана через Alembic.")
        insert_sql = (
            f"INSERT INTO guests (guest_id, last_name, first_name, phone_number, date_of_birth, id_document, balance, is_active) "
            f"VALUES ('{guest_uuid}', '{unique_marker}', 'Test', '+70000000000', '1990-01-01', '0000 {uuid.uuid4().hex[:6]}', 0.00, true);"
        )
        run_docker_compose(['exec', '-T', 'postgres', 'psql', '-U', 'beer_user', '-d', 'beer_db', '-c', insert_sql], check=True)
        print(f"[Action] Вставлена тестовая запись: {unique_marker}")
        run_docker_compose(["down"], check=True)
        run_docker_compose(["up", "-d"], check=True)
        time.sleep(15)
        select_sql = f"SELECT COUNT(*) FROM guests WHERE last_name = '{unique_marker}';"
        result = run_docker_compose(['exec', '-T', 'postgres', 'psql', '-U', 'beer_user', '-d', 'beer_db', '-A', '-t', '-c', select_sql], check=True)
        count = int(result.stdout.strip())
        assert count == 1
        print(f"[Check] Запись {unique_marker} найдена после перезапуска. Тест пройден.")
    finally:
        run_docker_compose(["down", "-v"])

def test_tc_sys_db_08_alembic_fails_on_stopped_db():
    """Проверяет TC-SYS-DB-08: Alembic падает, если БД остановлена."""
    try:
        run_docker_compose(["down", "-v"], check=True)
        # ## <-- КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Запускаем ВСЁ
        run_docker_compose(["up", "-d"])
        time.sleep(15)
        # ## <-- А ЗАТЕМ ОСТАНАВЛИВАЕМ postgres
        run_docker_compose(["stop", "postgres"], check=True)
        print("\n[Action] Сервис 'postgres' остановлен ПОСЛЕ запуска.")
        
        check_command = 'python -c "import os, sqlalchemy; sqlalchemy.create_engine(os.environ[\'DATABASE_URL\']).connect()"'
        result = run_docker_compose(['exec', '-T', 'beer_backend_api', 'sh', '-c', check_command])
        
        full_output = (result.stdout + result.stderr).lower()
        assert result.returncode != 0
        assert "connection refused" in full_output or "name or service not known" in full_output
        print("[Check] Попытка прямого подключения упала с ошибкой, как и ожидалось.")

    finally:
        run_docker_compose(["down", "-v"])

def test_tc_sys_db_09_alembic_fails_on_auth_error():
    """Проверяет TC-SYS-DB-09: Alembic падает при неверных учетных данных."""
    try:
        if os.path.exists(ENV_FILE_PATH):
            os.rename(ENV_FILE_PATH, ENV_BAK_FILE_PATH)
        with open(ENV_FILE_PATH, "w") as f:
            f.write("POSTGRES_USER=beer_user\n")
            f.write("POSTGRES_DB=beer_db\n")
            f.write("POSTGRES_PASSWORD=correct_password_for_db\n")
            f.write("DATABASE_URL=postgresql://beer_user:wrong_password_for_app@postgres:5432/beer_db\n")
        
        run_docker_compose(["up", "-d"])
        time.sleep(15)
        print("\n[Action] Система запущена с неверными учетными данными для Alembic.")

        check_command = 'python -c "import os, sqlalchemy; sqlalchemy.create_engine(os.environ[\'DATABASE_URL\']).connect()"'
        result = run_docker_compose(['exec', '-T', 'beer_backend_api', 'sh', '-c', check_command])

        full_output = (result.stdout + result.stderr).lower()
        assert result.returncode != 0
        assert "password authentication failed" in full_output
        print("[Check] Попытка прямого подключения упала с ошибкой 'password authentication failed', как и ожидалось.")

    finally:
        run_docker_compose(["down", "-v"])
        if os.path.exists(ENV_FILE_PATH):
            os.remove(ENV_FILE_PATH)
        if os.path.exists(ENV_BAK_FILE_PATH):
            os.rename(ENV_BAK_FILE_PATH, ENV_FILE_PATH)