import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import schemas
import security
from api import (
    audit,
    beverages,
    cards,
    controllers,
    display,
    guests,
    incidents,
    kegs,
    lost_cards,
    operator,
    pours,
    reports,
    shifts,
    system,
    taps,
    visits,
)
from crud import pour_crud
from database import DATABASE_URL, engine, get_db
from operator_stream import operator_stream_hub
from runtime_diagnostics import get_alembic_revision, get_db_identity, get_request_id
from startup_checks import verify_database_ready


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    force=True,
)


def _cors_allowed_origins() -> list[str]:
    raw_value = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
    if raw_value:
        parsed = []
        for item in raw_value.split(","):
            origin = item.strip().rstrip("/")
            if not origin:
                continue
            if origin == "*":
                logging.warning("CORS_ALLOWED_ORIGINS=* enables wildcard CORS. Do not use this in pilot.")
                return ["*"]
            parsed.append(origin)
        if parsed:
            return parsed

    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    security.validate_security_configuration()
    verify_database_ready(engine, DATABASE_URL)
    logging.info("Application startup complete.")
    yield
    logging.info("Application shutdown.")


app = FastAPI(
    title="Beer Tap System API",
    description="API for Beer Tap System",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allowed_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(guests.router, prefix="/api")
app.include_router(cards.router, prefix="/api")
app.include_router(taps.router, prefix="/api")
app.include_router(kegs.router, prefix="/api")
app.include_router(beverages.router, prefix="/api")
app.include_router(controllers.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(incidents.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(pours.router, prefix="/api")
app.include_router(visits.router, prefix="/api")
app.include_router(shifts.router, prefix="/api")
app.include_router(lost_cards.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(display.router, prefix="/api")
app.include_router(operator.router, prefix="/api")


@app.get("/", tags=["System"])
def read_root():
    return {"Status": "Beer Tap System Backend is running!"}


@app.post("/api/token", tags=["System"])
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    try:
        security.ensure_bootstrap_auth_available()
    except security.SecurityConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    user = security.get_user(form_data.username)
    if not user or form_data.password != user.get("hashed_password"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    role = user.get("role", "operator")
    access_token = security.create_access_token(
        data={
            "sub": user["username"],
            "role": role,
            "permissions": sorted(security.ROLE_PERMISSIONS.get(role, set())),
        }
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/me", tags=["System"])
async def get_me(
    current_user: Annotated[dict, Depends(security.get_current_user)],
):
    return {
        "username": current_user.get("username"),
        "full_name": current_user.get("full_name"),
        "role": current_user.get("role"),
        "permissions": current_user.get("permissions", []),
    }


@app.post("/api/sync/pours", response_model=schemas.SyncResponse, tags=["Controllers"])
@app.post("/api/sync/pours/", response_model=schemas.SyncResponse, tags=["Controllers"])
def sync_pours(
    sync_data: schemas.SyncRequest,
    request: Request,
    current_user: Annotated[dict, Depends(security.get_internal_service_user)] = None,
    db: Session = Depends(get_db),
):
    response_results = []
    logger = logging.getLogger("m4.runtime.sync")
    request_id = get_request_id(request)
    db_identity = get_db_identity(db)
    alembic_revision = get_alembic_revision(db)

    logger.info(
        "sync_pours_start request_id=%s db_identity=%s alembic_revision=%s batch_size=%s actor=%s",
        request_id,
        db_identity,
        alembic_revision,
        len(sync_data.pours),
        (current_user or {}).get("username", "unknown"),
    )

    try:
        for pour_data in sync_data.pours:
            existing_pour = pour_crud.get_pour_by_client_tx_id(db, client_tx_id=pour_data.client_tx_id)
            if existing_pour:
                duplicate_status = "accepted"
                duplicate_outcome = "duplicate_existing"
                duplicate_reason = "duplicate"
                if existing_pour.sync_status == "rejected":
                    duplicate_status = "rejected"
                    duplicate_outcome = "duplicate_existing_rejected"
                    duplicate_reason = "duplicate_existing_rejected"
                duplicate_result = schemas.SyncResult(
                    client_tx_id=pour_data.client_tx_id,
                    status=duplicate_status,
                    outcome=duplicate_outcome,
                    reason=duplicate_reason,
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
        operator_stream_hub.emit_invalidation(resource="today", reason="sync_pours_batch")
        operator_stream_hub.emit_invalidation(resource="taps", reason="sync_pours_batch")
        operator_stream_hub.emit_invalidation(resource="session", reason="sync_pours_batch")
        operator_stream_hub.emit_invalidation(resource="incident", reason="sync_pours_batch")
        operator_stream_hub.emit_invalidation(resource="system", reason="sync_pours_batch")
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.error(
            "sync_pours_failed request_id=%s db_identity=%s alembic_revision=%s error=%s",
            request_id,
            db_identity,
            alembic_revision,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to commit pours batch: {str(exc)}",
        )

    return schemas.SyncResponse(results=response_results)
