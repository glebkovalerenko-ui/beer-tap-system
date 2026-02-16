# backend/main.py

# --- ИЗМЕНЕНИЕ: Добавляем централизованную конфигурацию логирования в самом начале ---
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    force=True, # Перезаписывает любую существующую конфигурацию (важно для Uvicorn)
)
# --- КОНЕЦ ИЗМЕНЕНИЯ ---

# --- Стандартные и внешние импорты ---
from typing import List, Annotated
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

# --- Локальные импорты ---
import models, schemas, security
from database import get_db, engine
from crud import pour_crud

# --- Импорты для новых роутеров API ---
from api import guests, cards, taps, kegs, beverages, controllers, system, audit, pours

# --- Создание таблиц в БД на основе моделей ---
models.Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Application startup complete.")
    yield
    logging.info("Application shutdown.")

# --- Инициализация FastAPI приложения ---
app = FastAPI(
    title="Beer Tap System API",
    description="API для управления системой автоматизации пивных кранов",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Для разработки разрешаем все источники.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Подключение модульных роутеров ---
app.include_router(guests.router, prefix="/api")
app.include_router(cards.router, prefix="/api")
app.include_router(taps.router, prefix="/api")
app.include_router(kegs.router, prefix="/api")
app.include_router(beverages.router, prefix="/api")
app.include_router(controllers.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(pours.router, prefix="/api")


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
        existing_pour = pour_crud.get_pour_by_client_tx_id(db, client_tx_id=pour_data.client_tx_id)
        if existing_pour:
            response_results.append(schemas.SyncResult(
                client_tx_id=pour_data.client_tx_id,
                status="accepted",
                reason="duplicate"
            ))
            continue
        
        result = pour_crud.process_pour(db, pour_data=pour_data)
        
        response_results.append(schemas.SyncResult(
            client_tx_id=pour_data.client_tx_id,
            status=result["status"],
            reason=result.get("reason")
        ))
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        # --- ИЗМЕНЕНИЕ: Используем logger для ошибок ---
        logging.error(f"Failed to commit pours batch: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to commit pours batch: {str(e)}"
        )

    return schemas.SyncResponse(results=response_results)