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
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

# --- Локальные импорты ---
import models, schemas, security
from database import get_db
from crud import pour_crud
from runtime_diagnostics import get_alembic_revision, get_db_identity, get_request_id

# --- Импорты для новых роутеров API ---
from api import guests, cards, taps, kegs, beverages, controllers, system, audit, pours, visits

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
app.include_router(visits.router, prefix="/api")


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

@app.post("/api/sync/pours", response_model=schemas.SyncResponse, tags=["Controllers"])
@app.post("/api/sync/pours/", response_model=schemas.SyncResponse, tags=["Controllers"])
def sync_pours(sync_data: schemas.SyncRequest, request: Request, db: Session = Depends(get_db)):
    """
    Эндпоинт для получения пакета данных о наливах от RPi контроллеров.
    Для каждой записи выполняет полную валидацию и атомарно обновляет состояние.
    Вся пачка обрабатывается в рамках одной транзакции БД.
    """
    response_results = []
    logger = logging.getLogger("m4.runtime.sync")
    request_id = get_request_id(request)
    db_identity = get_db_identity(db)
    alembic_revision = get_alembic_revision(db)

    logger.info(
        "sync_pours_start request_id=%s db_identity=%s alembic_revision=%s batch_size=%s",
        request_id,
        db_identity,
        alembic_revision,
        len(sync_data.pours),
    )

    try:
        for pour_data in sync_data.pours:
            existing_pour = pour_crud.get_pour_by_client_tx_id(db, client_tx_id=pour_data.client_tx_id)
            if existing_pour:
                duplicate_result = schemas.SyncResult(
                    client_tx_id=pour_data.client_tx_id,
                    status="accepted",
                    outcome="duplicate_existing",
                    reason="duplicate",
                )
                response_results.append(duplicate_result)
                logger.info(
                    "sync_pours_result request_id=%s client_tx_id=%s status=%s outcome=%s reason=%s",
                    request_id,
                    duplicate_result.client_tx_id,
                    duplicate_result.status,
                    duplicate_result.outcome,
                    duplicate_result.reason,
                )
                continue

            result = pour_crud.process_pour(db, pour_data=pour_data)

            if result["status"] == "conflict":
                logger.warning(
                    "sync_pours_result request_id=%s client_tx_id=%s status=%s outcome=%s reason=%s",
                    request_id,
                    pour_data.client_tx_id,
                    result["status"],
                    result.get("outcome"),
                    result.get("reason"),
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=result.get("reason", "Sync conflict"),
                )

            sync_result = schemas.SyncResult(
                client_tx_id=pour_data.client_tx_id,
                status=result["status"],
                outcome=result.get("outcome"),
                reason=result.get("reason"),
            )
            response_results.append(sync_result)
            logger.info(
                "sync_pours_result request_id=%s client_tx_id=%s status=%s outcome=%s reason=%s",
                request_id,
                sync_result.client_tx_id,
                sync_result.status,
                sync_result.outcome,
                sync_result.reason,
            )

        db.commit()
        logger.info(
            "sync_pours_done request_id=%s db_identity=%s alembic_revision=%s processed=%s",
            request_id,
            db_identity,
            alembic_revision,
            len(response_results),
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            "sync_pours_failed request_id=%s db_identity=%s alembic_revision=%s error=%s",
            request_id,
            db_identity,
            alembic_revision,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to commit pours batch: {str(e)}"
        )

    return schemas.SyncResponse(results=response_results)
