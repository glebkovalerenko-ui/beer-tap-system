from datetime import datetime, timedelta, timezone
import logging
import os
from typing import Annotated, Any

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from fastapi import BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from crud import audit_crud
from database import SessionLocal, get_db


logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
DEV_ONLY_SECRET_KEY = "dev-only-secret-key-change-in-production"
PLACEHOLDER_PREFIXES = ("replace-with", "change-me")


class SecurityConfigurationError(RuntimeError):
    pass


BOOTSTRAP_USERS = {
    "admin": {
        "username": "admin",
        "full_name": "Admin User",
        "role": "engineer_owner",
    },
    "shift_lead": {
        "username": "shift_lead",
        "full_name": "Shift Lead User",
        "role": "shift_lead",
    },
    "operator": {
        "username": "operator",
        "full_name": "Operator User",
        "role": "operator",
    },
}


ROLE_PERMISSIONS = {
    "operator": {
        "taps_view",
        "sessions_view",
        "cards_lookup",
        "cards_open_active_session",
        "cards_history_view",
        "incidents_view",
        "system_health_view",
    },
    "shift_lead": {
        "taps_view",
        "taps_control",
        "sessions_view",
        "cards_lookup",
        "cards_open_active_session",
        "cards_history_view",
        "cards_top_up",
        "cards_block_manage",
        "cards_reissue_manage",
        "incidents_view",
        "incidents_manage",
        "system_health_view",
        "maintenance_actions",
    },
    "engineer_owner": {
        "taps_view",
        "taps_control",
        "sessions_view",
        "cards_lookup",
        "cards_open_active_session",
        "cards_history_view",
        "cards_top_up",
        "cards_block_manage",
        "cards_reissue_manage",
        "incidents_view",
        "incidents_manage",
        "system_health_view",
        "system_engineering_actions",
        "maintenance_actions",
        "display_override",
        "settings_manage",
        "debug_tools",
        "role_switch",
    },
}


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token", auto_error=False)


def _normalize_token(value: str | None) -> str:
    if value is None:
        return ""
    normalized = value.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {'"', "'"}:
        normalized = normalized[1:-1].strip()
    return normalized


def _looks_like_placeholder(value: str | None) -> bool:
    normalized = _normalize_token(value).lower()
    if not normalized:
        return True
    return any(normalized.startswith(prefix) for prefix in PLACEHOLDER_PREFIXES)


def _env_flag(name: str, default: bool = False) -> bool:
    fallback = "true" if default else "false"
    return os.getenv(name, fallback).strip().lower() in {"1", "true", "yes", "on"}


def _permissions_for_role(role: str | None) -> set[str]:
    if not role:
        return set()
    return set(ROLE_PERMISSIONS.get(role, set()))


def is_bootstrap_auth_enabled() -> bool:
    return _env_flag("ENABLE_BOOTSTRAP_AUTH", default=False)


def _get_bootstrap_auth_password() -> str:
    password = _normalize_token(os.getenv("BOOTSTRAP_AUTH_PASSWORD", ""))
    if _looks_like_placeholder(password):
        return ""
    return password


def ensure_bootstrap_auth_available() -> None:
    if not is_bootstrap_auth_enabled():
        raise SecurityConfigurationError(
            "Bootstrap auth is disabled. Set ENABLE_BOOTSTRAP_AUTH=true for local development or controlled pilot use."
        )
    if not _get_bootstrap_auth_password():
        raise SecurityConfigurationError(
            "ENABLE_BOOTSTRAP_AUTH=true requires BOOTSTRAP_AUTH_PASSWORD to be set to a non-placeholder value."
        )


def get_user(username: str):
    template = BOOTSTRAP_USERS.get(username)
    if template is None:
        return None

    user = dict(template)
    password = _get_bootstrap_auth_password()
    if password:
        user["hashed_password"] = password
    return user


def _get_secret_key() -> str:
    configured = _normalize_token(os.getenv("SECRET_KEY", ""))
    if configured and configured != DEV_ONLY_SECRET_KEY and not _looks_like_placeholder(configured):
        return configured

    if _env_flag("ALLOW_INSECURE_DEV_SECRET_KEY", default=False):
        logger.warning(
            "Using insecure development SECRET_KEY fallback because ALLOW_INSECURE_DEV_SECRET_KEY=true. Do not use this in pilot."
        )
        return DEV_ONLY_SECRET_KEY

    raise SecurityConfigurationError(
        "SECRET_KEY must be set to a non-placeholder value. Set ALLOW_INSECURE_DEV_SECRET_KEY=true only for local development."
    )


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, _get_secret_key(), algorithm=ALGORITHM)
    return encoded_jwt


def _get_env_token_set(*, primary_name: str, multi_name: str) -> set[str]:
    keys: set[str] = set()

    primary = _normalize_token(os.getenv(primary_name, ""))
    if primary and not _looks_like_placeholder(primary):
        keys.add(primary)

    multi = _normalize_token(os.getenv(multi_name, ""))
    if multi:
        for raw in multi.split(","):
            token = _normalize_token(raw)
            if token and not _looks_like_placeholder(token):
                keys.add(token)

    return keys


def _get_internal_api_keys() -> set[str]:
    keys = _get_env_token_set(primary_name="INTERNAL_API_KEY", multi_name="INTERNAL_API_KEYS")

    legacy = _normalize_token(os.getenv("INTERNAL_TOKEN", ""))
    if legacy and not _looks_like_placeholder(legacy):
        keys.add(legacy)

    if _env_flag("ALLOW_LEGACY_DEMO_INTERNAL_TOKEN", default=False):
        keys.add("demo-secret-key")

    return keys


def _get_display_api_keys() -> set[str]:
    return _get_env_token_set(primary_name="DISPLAY_API_KEY", multi_name="DISPLAY_API_KEYS")


def validate_security_configuration() -> None:
    _get_secret_key()
    if is_bootstrap_auth_enabled():
        ensure_bootstrap_auth_available()

    internal_keys = _get_internal_api_keys()
    display_keys = _get_display_api_keys()

    if not internal_keys:
        logger.warning(
            "INTERNAL_API_KEY/INTERNAL_API_KEYS/INTERNAL_TOKEN are not configured. Internal controller routes will reject token-authenticated requests."
        )
    if not display_keys:
        logger.warning(
            "DISPLAY_API_KEY/DISPLAY_API_KEYS are not configured. Display-agent read routes will reject display-token requests."
        )

    logger.info(
        "Security configuration loaded: bootstrap_auth=%s internal_tokens=%s display_tokens=%s",
        "enabled" if is_bootstrap_auth_enabled() else "disabled",
        len(internal_keys),
        len(display_keys),
    )


def audit_log_task_wrapper(
    actor_id: str,
    action: str,
    target_entity: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
):
    db = SessionLocal()
    try:
        audit_crud.create_audit_log_entry(
            db=db,
            actor_id=actor_id,
            action=action,
            target_entity=target_entity,
            target_id=target_id,
            details=details,
        )
    finally:
        db.close()


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _authenticate_bearer_user(token: str | None) -> dict:
    credentials_exception = _credentials_exception()

    if token is None:
        raise credentials_exception

    try:
        payload = jwt.decode(token, _get_secret_key(), algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user(username)
    if user is None:
        raise credentials_exception

    role = payload.get("role") or user.get("role") or "operator"
    payload_permissions = payload.get("permissions")
    permission_set = set()
    if isinstance(payload_permissions, list):
        permission_set = {str(item).strip() for item in payload_permissions if str(item).strip()}
    if not permission_set:
        permission_set = _permissions_for_role(role)

    return {
        "username": username,
        "full_name": user.get("full_name"),
        "role": role,
        "permissions": sorted(permission_set),
    }


def _maybe_schedule_audit_log(
    *,
    request: Request,
    background_tasks: BackgroundTasks,
    actor_id: str,
) -> None:
    if request.method in ["POST", "PUT", "DELETE"]:
        action = f"{request.method}_{request.url.path}"
        background_tasks.add_task(
            audit_log_task_wrapper,
            actor_id=actor_id,
            action=action,
        )


def _authenticate_named_token(
    *,
    request: Request,
    header_name: str,
    allowed_tokens: set[str],
    actor_id: str,
    warning_message: str,
) -> dict | None:
    received_token = _normalize_token(request.headers.get(header_name))
    if not received_token:
        return None

    if received_token in allowed_tokens:
        return {"username": actor_id}

    logger.warning(warning_message, request.url.path)
    raise _credentials_exception()


async def get_current_user(
    request: Request,
    background_tasks: BackgroundTasks,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    user = _authenticate_bearer_user(token)
    _maybe_schedule_audit_log(
        request=request,
        background_tasks=background_tasks,
        actor_id=user["username"],
    )
    return user


async def get_internal_service_user(
    request: Request,
    background_tasks: BackgroundTasks,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    internal_keys = _get_internal_api_keys()
    if request.headers.get("x-internal-token") and not internal_keys:
        logger.warning(
            "Internal token presented for path %s, but INTERNAL_API_KEY/INTERNAL_API_KEYS/INTERNAL_TOKEN are not configured.",
            request.url.path,
        )

    internal_principal = _authenticate_named_token(
        request=request,
        header_name="x-internal-token",
        allowed_tokens=internal_keys,
        actor_id="internal_rpi",
        warning_message="Internal token rejected for path %s. Check INTERNAL_API_KEY/INTERNAL_TOKEN alignment.",
    )
    if internal_principal is not None:
        return internal_principal
    return await get_current_user(request, background_tasks, token, db)


async def get_display_reader(
    request: Request,
    background_tasks: BackgroundTasks,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    display_keys = _get_display_api_keys()
    if request.headers.get("x-display-token") and not display_keys:
        logger.warning(
            "Display token presented for path %s, but DISPLAY_API_KEY/DISPLAY_API_KEYS are not configured.",
            request.url.path,
        )

    display_principal = _authenticate_named_token(
        request=request,
        header_name="x-display-token",
        allowed_tokens=display_keys,
        actor_id="display_agent",
        warning_message="Display token rejected for path %s. Check DISPLAY_API_KEY/DISPLAY_API_KEYS alignment.",
    )
    if display_principal is not None:
        return display_principal
    return await get_current_user(request, background_tasks, token, db)


def require_permissions(*required_permissions: str):
    required = [permission.strip() for permission in required_permissions if permission and permission.strip()]

    async def dependency(
        current_user: Annotated[dict, Depends(get_current_user)],
    ) -> dict:
        if not required:
            return current_user

        granted = {
            str(item).strip()
            for item in (current_user or {}).get("permissions", [])
            if str(item).strip()
        }
        missing = [permission for permission in required if permission not in granted]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "reason": "forbidden",
                    "message": "Action is not available for current role",
                    "required_permissions": required,
                    "missing_permissions": missing,
                    "role": (current_user or {}).get("role"),
                },
            )
        return current_user

    return dependency
