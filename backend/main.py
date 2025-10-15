# backend/main.py
# --- Стандартные и внешние импорты ---
import uuid
import json
from typing import List, Annotated
from fastapi import FastAPI, Depends, HTTPException, status, Request 
from starlette.concurrency import iterate_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

# --- Локальные импорты ---
import models, schemas, security
from database import engine, get_db
from crud import guest_crud, pour_crud, transaction_crud, audit_crud

# --- Импорты для новых роутеров API ---
from api import guests, cards, taps, kegs, beverages, controllers, system, audit # <-- Импортируем роутеры

# Эта команда говорит SQLAlchemy создать все таблицы в БД.
# ВНИМАНИЕ: Для продакшена эту строку лучше удалить,
# так как управление схемой БД должно полностью перейти к Alembic.
models.Base.metadata.create_all(bind=engine)

# --- Инициализация FastAPI приложения ---
app = FastAPI(
    title="Beer Tap System API",
    description="API для управления системой автоматизации пивных кранов",
    version="1.0.0"
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Для разработки разрешаем все источники.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# НОВОЕ Middleware для автоматического аудита
@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    # Пропускаем запрос дальше, чтобы он выполнился
    response = await call_next(request)

    # Логируем только успешные запросы, которые изменяют состояние
    if request.method in ["POST", "PUT", "DELETE"] and 200 <= response.status_code < 300:
        
        actor_id = "anonymous"
        # Пытаемся извлечь ID пользователя из JWT-токена
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = security.jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
                actor_id = payload.get("sub", "token_user")
            except security.JWTError:
                actor_id = "invalid_token_user"

        # Собираем детали для лога
        action = f"{request.method}_{request.url.path}"
        
        # Читаем тело ответа, чтобы получить ID созданного/обновленного объекта
        response_body = [chunk async for chunk in response.body_iterator]
        response.body_iterator = iterate_in_threadpool(iter(response_body))
        
        target_id = None
        try:
            resp_json = json.loads(b"".join(response_body).decode())
            possible_id_keys = ["guest_id", "keg_id", "tap_id", "card_uid", "beverage_id", "controller_id"]
            for key in possible_id_keys:
                if key in resp_json:
                    target_id = str(resp_json[key])
                    break
        except Exception:
            pass # Не страшно, если ID не нашелся

        # Создаем запись в журнале аудита
        db = next(get_db())
        try:
            audit_crud.create_audit_log(
                db=db,
                actor_id=actor_id,
                action=action,
                target_id=target_id,
            )
        finally:
            db.close()

    return response

# --- Подключение модульных роутеров ---
# Все эндпоинты, связанные с Напитками, Гостями и Кегами, теперь управляются из отдельных файлов.
app.include_router(guests.router) # <-- Подключаем роутер для гостей
app.include_router(cards.router) # <-- Подключаем роутер для карт
app.include_router(taps.router) # <-- Подключаем роутер для крана
app.include_router(kegs.router) # <-- Подключаем роутер для кег
app.include_router(beverages.router) # <-- Подключаем роутер для напитков
app.include_router(controllers.router) # <-- Подключаем роутер для контроллеров
app.include_router(system.router) # <-- Подключаем роутер для состояния системы
app.include_router(audit.router) # <-- Подключаем роутер для Летописца

# --- Системные и служебные эндпоинты, оставшиеся в main.py ---

@app.get("/", tags=["System"])
def read_root():
    """ Корневой эндпоинт для проверки статуса API. """
    return {"Status": "Beer Tap System Backend is running!"}

@app.post("/api/token", tags=["System"])
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """ Эндпоинт для аутентификации и получения JWT-токена. """
    user = security.get_user(form_data.username)
    if not user or form_data.password != user["hashed_password"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password"
        )
    
    access_token = security.create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/sync/pours/", response_model=schemas.SyncResponse, tags=["Controllers"])
def sync_pours(sync_data: schemas.SyncRequest, db: Session = Depends(get_db)):
    """
    Эндпоинт для получения пакета данных о наливах от RPi контроллеров.
    Для каждой записи выполняет полную валидацию и атомарно обновляет состояние.
    Вся пачка обрабатывается в рамках одной транзакции БД.
    """
    response_results = []
    
    for pour_data in sync_data.pours:
        # 1. Проверка на идемпотентность (дубликат)
        existing_pour = pour_crud.get_pour_by_client_tx_id(db, client_tx_id=pour_data.client_tx_id)
        if existing_pour:
            response_results.append(schemas.SyncResult(
                client_tx_id=pour_data.client_tx_id,
                status="accepted",
                reason="duplicate"
            ))
            continue # Переходим к следующему наливу в пакете
        
        # 2. Обработка налива с помощью новой "умной" функции
        result = pour_crud.process_pour(db, pour_data=pour_data)
        
        # 3. Добавляем результат в ответ
        response_results.append(schemas.SyncResult(
            client_tx_id=pour_data.client_tx_id,
            status=result["status"],
            reason=result.get("reason")
        ))

    # 4. После обработки всей пачки, коммитим изменения в БД.
    # Если в середине обработки любого из наливов произойдет ошибка,
    # FastAPI автоматически сделает rollback всей сессии, и ни один налив из пачки не будет сохранен.
    # Это гарантирует целостность данных.
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        # В случае ошибки коммита, нужно вернуть ошибку 500,
        # чтобы контроллер понял, что пачку нужно отправить повторно.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to commit pours batch: {str(e)}"
        )

    return schemas.SyncResponse(results=response_results)