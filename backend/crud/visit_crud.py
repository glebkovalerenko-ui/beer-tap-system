from datetime import date, datetime, timedelta
import json
import uuid
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from crud import card_crud, display_crud, lost_card_crud, pour_policy, system_crud
from pos_adapter import get_pos_adapter


VISIT_OP_ACTIVE_ASSIGNED = "active_assigned"
VISIT_OP_ACTIVE_BLOCKED_LOST = "active_blocked_lost_card"
VISIT_OP_CLOSED_OK = "closed_ok"
VISIT_OP_CLOSED_MISSING = "closed_missing_card"


def _normalize_card_uid(card_uid: str) -> str:
    return card_crud.normalize_card_uid(card_uid)


def _is_adult(date_of_birth: date) -> bool:
    today = date.today()
    years = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return years >= 18


def _add_audit_log(
    db: Session,
    *,
    actor_id: str,
    action: str,
    target_entity: str,
    target_id: str,
    details: dict,
):
    db.add(
        models.AuditLog(
            actor_id=actor_id,
            action=action,
            target_entity=target_entity,
            target_id=target_id,
            details=json.dumps(details, ensure_ascii=False),
        )
    )


def _add_visit_card_audit_event(
    db: Session,
    *,
    actor_id: str | None,
    event_type: str,
    visit: models.Visit,
    card_uid: str,
    previous_state: dict,
    next_state: dict,
    source_channel: str,
    reason_code: str | None = None,
    comment: str | None = None,
    request_id: str | None = None,
    extra: dict | None = None,
):
    payload = {
        "event_type": event_type,
        "occurred_at": "db_timestamp",
        "actor_id": actor_id,
        "visit_id": str(visit.visit_id),
        "guest_id": str(visit.guest_id),
        "card_uid": card_uid,
        "source_channel": source_channel,
        "reason_code": reason_code,
        "comment": comment,
        "request_id": request_id,
        "previous_state": previous_state,
        "next_state": next_state,
    }
    if extra:
        payload.update(extra)
    _add_audit_log(
        db,
        actor_id=actor_id or "system",
        action=event_type,
        target_entity="Visit",
        target_id=str(visit.visit_id),
        details=payload,
    )


def _authorize_error(
    status_code: int,
    *,
    reason: str,
    message: str,
    context: dict | None = None,
) -> HTTPException:
    detail = {"reason": reason, "message": message}
    if context:
        detail["context"] = context
    return HTTPException(status_code=status_code, detail=detail)


def _build_authorize_context(*, guest: models.Guest, beverage: models.Beverage, policy: dict[str, int]) -> dict[str, int]:
    balance_cents = pour_policy.balance_to_cents(guest.balance)
    price_per_ml_cents = pour_policy.sell_price_per_liter_to_price_per_ml_cents(beverage.sell_price_per_liter)
    max_volume_ml = pour_policy.calculate_max_volume_ml(
        balance_cents=balance_cents,
        allowed_overdraft_cents=policy["allowed_overdraft_cents"],
        price_per_ml_cents=price_per_ml_cents,
        safety_ml=policy["safety_ml"],
    )
    return {
        "min_start_ml": policy["min_start_ml"],
        "max_volume_ml": max_volume_ml,
        "price_per_ml_cents": price_per_ml_cents,
        "balance_cents": balance_cents,
        "allowed_overdraft_cents": policy["allowed_overdraft_cents"],
        "safety_ml": policy["safety_ml"],
    }


def _build_insufficient_funds_detail(context: dict[str, int]) -> dict:
    detail_context = dict(context)
    detail_context["required_cents"] = pour_policy.required_cents_for_volume(
        context["min_start_ml"],
        context["price_per_ml_cents"],
    )
    return {
        "reason": "insufficient_funds",
        "message": "Insufficient funds: top up guest balance before pouring.",
        "context": detail_context,
    }


def _compact_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _derive_display_context(db: Session, *, tap_id: int | None, has_incident: bool, incident_count: int) -> schemas.SessionDisplayContext:
    if tap_id is None:
        return schemas.SessionDisplayContext(
            available=False,
            source="not_saved",
            note="Display context не был сохранён для этой сессии.",
            incident_link=(
                f"В сессии есть инциденты ({incident_count}), но связать их с экраном нельзя: tap/display context не был сохранён."
                if has_incident else None
            ),
        )

    try:
        snapshot = display_crud.build_display_snapshot(db, tap_id=tap_id)
    except Exception:
        return schemas.SessionDisplayContext(
            available=False,
            source="not_saved",
            tap_id=tap_id,
            note="Display context не был сохранён для этой сессии.",
            incident_link=(
                f"В сессии есть инциденты ({incident_count}), поэтому display context стоит проверять отдельно: исторический snapshot не сохранился."
                if has_incident else None
            ),
        )

    tap_status = snapshot.tap.status
    enabled = snapshot.tap.enabled
    has_assignment = snapshot.assignment.has_assignment
    if not enabled:
        display_state = "display_disabled"
        availability_label = "Экран был отключён для гостя"
    elif tap_status == "empty" or not has_assignment:
        display_state = "fallback_empty"
        availability_label = "Гость видел fallback для пустого или неназначенного крана"
    elif tap_status in {"cleaning", "locked"}:
        display_state = "maintenance"
        availability_label = "Гость видел сервисный/недоступный экран"
    else:
        display_state = "beverage_spotlight"
        availability_label = "Гость видел обычную карточку напитка"

    title = None
    subtitle = None
    if display_state == "display_disabled":
        title = _compact_text(snapshot.copy_block.maintenance_title) or _compact_text(snapshot.copy_block.fallback_title)
        subtitle = _compact_text(snapshot.copy_block.maintenance_subtitle) or _compact_text(snapshot.copy_block.fallback_subtitle)
    elif display_state == "fallback_empty":
        title = _compact_text(snapshot.copy_block.fallback_title) or _compact_text(snapshot.presentation.brand_name) or _compact_text(snapshot.presentation.name)
        subtitle = _compact_text(snapshot.copy_block.fallback_subtitle) or _compact_text(snapshot.presentation.description_short)
    elif display_state == "maintenance":
        title = _compact_text(snapshot.copy_block.maintenance_title) or _compact_text(snapshot.copy_block.fallback_title)
        subtitle = _compact_text(snapshot.copy_block.maintenance_subtitle) or _compact_text(snapshot.copy_block.fallback_subtitle)
    else:
        title = _compact_text(snapshot.presentation.brand_name) or _compact_text(snapshot.presentation.name) or _compact_text(snapshot.copy_block.fallback_title)
        subtitle = _compact_text(snapshot.presentation.description_short) or _compact_text(snapshot.copy_block.idle_instruction)

    important_overrides = []
    if snapshot.tap.enabled is False:
        important_overrides.append("Tap display выключен на уровне крана")
    if _compact_text(snapshot.copy_block.idle_instruction):
        important_overrides.append(f"Idle instruction: {snapshot.copy_block.idle_instruction}")
    if _compact_text(snapshot.theme.accent_color):
        important_overrides.append(f"Accent color: {snapshot.theme.accent_color}")
    if snapshot.theme.background_asset is not None:
        important_overrides.append("Есть background override/asset для guest screen")
    if snapshot.pricing.display_mode and snapshot.pricing.display_mode != "hidden":
        important_overrides.append(f"Price mode: {snapshot.pricing.display_mode}")

    maintenance_mode = None
    fallback_mode = None
    if display_state == "maintenance":
        maintenance_mode = f"{title or 'Сервисный экран'} — {subtitle or 'без дополнительного описания'}"
    if display_state in {"fallback_empty", "display_disabled"}:
        fallback_mode = f"{title or 'Fallback экран'} — {subtitle or 'без дополнительного описания'}"

    incident_link = None
    if has_incident:
        incident_link = (
            f"В этой сессии есть инциденты ({incident_count}). Их narrative стоит читать вместе с контекстом экрана: {availability_label.lower()}."
        )

    return schemas.SessionDisplayContext(
        available=True,
        source="reconstructed_from_current_tap_config",
        tap_id=snapshot.tap.tap_id,
        tap_name=snapshot.tap.display_name,
        display_state=display_state,
        availability_label=availability_label,
        title=title,
        subtitle=subtitle,
        maintenance_mode=maintenance_mode,
        fallback_mode=fallback_mode,
        important_overrides=important_overrides,
        note="Контекст восстановлен по текущей конфигурации tap display; исторический snapshot сессии отдельно не сохранялся.",
        incident_link=incident_link,
    )


def get_active_visit_by_guest_id(db: Session, guest_id: uuid.UUID):
    return db.query(models.Visit).filter(
        models.Visit.guest_id == guest_id,
        models.Visit.status == "active",
    ).first()


def get_active_visit_by_card_uid(db: Session, card_uid: str):
    normalized_uid = _normalize_card_uid(card_uid)
    return db.query(models.Visit).filter(
        func.lower(models.Visit.card_uid) == normalized_uid,
        models.Visit.status == "active",
    ).first()


def search_active_visit_by_guest_query(db: Session, query: str):
    normalized = query.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Query must not be empty")

    like_query = f"%{normalized.lower()}%"

    return db.query(models.Visit).join(models.Guest, models.Visit.guest_id == models.Guest.guest_id).filter(
        models.Visit.status == "active",
        or_(
            models.Guest.phone_number.ilike(like_query),
            models.Guest.last_name.ilike(like_query),
            models.Guest.first_name.ilike(like_query),
            models.Guest.patronymic.ilike(like_query),
        ),
    ).order_by(models.Visit.opened_at.desc()).first()


def get_visit(db: Session, visit_id: uuid.UUID):
    return db.query(models.Visit).filter(models.Visit.visit_id == visit_id).first()


def _get_pending_pour_for_visit_tap(db: Session, visit_id: uuid.UUID, tap_id: int):
    return (
        db.query(models.Pour)
        .filter(
            models.Pour.visit_id == visit_id,
            models.Pour.tap_id == tap_id,
            models.Pour.sync_status == "pending_sync",
            models.Pour.is_manual_reconcile.is_(False),
        )
        .order_by(models.Pour.created_at.desc())
        .first()
    )


def _ensure_pending_pour_for_active_visit(
    db: Session,
    visit: models.Visit,
    tap_id: int,
    *,
    price_per_ml: Decimal,
) -> str:
    existing = _get_pending_pour_for_visit_tap(db=db, visit_id=visit.visit_id, tap_id=tap_id)
    if existing:
        existing.price_per_ml_at_pour = price_per_ml
        return "pending_exists"

    tap = db.query(models.Tap).filter(models.Tap.tap_id == tap_id).first()
    if not tap or not tap.keg_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tap is not configured with keg")

    pending_client_tx_id = f"pending-sync:{visit.visit_id}:{tap_id}:{uuid.uuid4().hex[:8]}"
    db.add(
        models.Pour(
            client_tx_id=pending_client_tx_id,
            card_uid=visit.card_uid,
            tap_id=tap_id,
            visit_id=visit.visit_id,
            volume_ml=0,
            poured_at=func.now(),
            authorized_at=func.now(),
            amount_charged=Decimal("0.00"),
            price_per_ml_at_pour=price_per_ml,
            duration_ms=None,
            guest_id=visit.guest_id,
            keg_id=tap.keg_id,
            sync_status="pending_sync",
            short_id=None,
            is_manual_reconcile=False,
        )
    )
    return "pending_created"


def get_active_visits_list(db: Session):
    visits = db.query(models.Visit).join(models.Guest, models.Visit.guest_id == models.Guest.guest_id).filter(
        models.Visit.status == "active"
    ).order_by(models.Visit.opened_at.desc()).all()

    result = []
    for visit in visits:
        guest = visit.guest
        full_name = " ".join([part for part in [guest.last_name, guest.first_name, guest.patronymic] if part]) if guest else "—"
        balance = guest.balance if guest else Decimal("0.00")
        projected_remaining_allowance_ml = None
        projected_remaining_allowance_source = None
        allowance_calculation_note = None
        price_per_ml_cents = None

        if visit.active_tap_id is not None:
            tap = (
                db.query(models.Tap)
                .join(models.Keg, models.Tap.keg_id == models.Keg.keg_id)
                .join(models.Beverage, models.Keg.beverage_id == models.Beverage.beverage_id)
                .filter(models.Tap.tap_id == visit.active_tap_id)
                .first()
            )
            beverage = tap.keg.beverage if tap and tap.keg and tap.keg.beverage else None
            if beverage and beverage.sell_price_per_liter is not None:
                policy = system_crud.get_pour_policy(db)
                balance_cents = pour_policy.balance_to_cents(balance)
                price_per_ml_cents = pour_policy.sell_price_per_liter_to_price_per_ml_cents(beverage.sell_price_per_liter)
                projected_remaining_allowance_ml = pour_policy.calculate_max_volume_ml(
                    balance_cents=balance_cents,
                    allowed_overdraft_cents=policy["allowed_overdraft_cents"],
                    price_per_ml_cents=price_per_ml_cents,
                    safety_ml=policy["safety_ml"],
                )
                projected_remaining_allowance_source = "balance_price_policy"
                allowance_calculation_note = (
                    "Лимит рассчитан backend из баланса гостя, цены напитка на активном кране, allowed overdraft и safety_ml."
                )
            else:
                projected_remaining_allowance_source = "not_configured"
                allowance_calculation_note = "Для активного крана не настроена цена напитка, поэтому лимит не вычисляется."
        else:
            projected_remaining_allowance_source = "not_applicable"
            allowance_calculation_note = "Пока визит не привязан к активному крану, backend не рассчитывает лимит в мл."

        result.append({
            "visit_id": visit.visit_id,
            "guest_id": visit.guest_id,
            "guest_full_name": full_name,
            "phone_number": guest.phone_number if guest else "",
            "balance": balance,
            "status": visit.status,
            "operational_status": visit.operational_status,
            "card_uid": visit.card_uid,
            "active_tap_id": visit.active_tap_id,
            "lock_set_at": visit.lock_set_at,
            "opened_at": visit.opened_at,
            "projected_remaining_allowance_ml": projected_remaining_allowance_ml,
            "projected_remaining_allowance_source": projected_remaining_allowance_source,
            "allowance_calculation_note": allowance_calculation_note,
            "price_per_ml_cents": price_per_ml_cents,
        })
    return result


def open_visit(db: Session, guest_id: uuid.UUID, card_uid: str | None = None):
    guest = db.query(models.Guest).filter(models.Guest.guest_id == guest_id).first()
    if not guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")

    if not _is_adult(guest.date_of_birth):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Guest must be 18+ to open visit")

    existing_guest_visit = get_active_visit_by_guest_id(db=db, guest_id=guest_id)
    if existing_guest_visit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Guest already has an active visit", "visit_id": str(existing_guest_visit.visit_id)},
        )

    if card_uid is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Card UID is required for the normal visit open flow",
        )

    normalized_uid = _normalize_card_uid(card_uid)
    card = card_crud.get_card_by_uid(db, normalized_uid)
    auto_registered = False
    if not card:
        card = models.Card(
            card_uid=normalized_uid,
            status=card_crud.CARD_STATUS_AVAILABLE,
            guest_id=None,
        )
        db.add(card)
        try:
            db.flush()
            auto_registered = True
        except IntegrityError:
            db.rollback()
            card = card_crud.get_card_by_uid(db, normalized_uid)
            if not card:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Card registration conflict, retry visit open")

    if card.status in {card_crud.CARD_STATUS_LOST, card_crud.CARD_STATUS_RETIRED}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Card is not issuable from state {card.status}")
    if card.status == card_crud.CARD_STATUS_ASSIGNED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Card is already assigned to an active visit")

    existing_card_visit = get_active_visit_by_card_uid(db=db, card_uid=normalized_uid)
    if existing_card_visit:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Card already used by another active visit")

    previous_card_status = "not_registered" if auto_registered else card.status

    try:
        visit = models.Visit(
            guest_id=guest_id,
            card_uid=normalized_uid,
            status="active",
            operational_status=VISIT_OP_ACTIVE_ASSIGNED,
            active_tap_id=None,
            card_returned=False,
        )
        db.add(visit)
        db.flush()
        card.status = card_crud.CARD_STATUS_ASSIGNED
        card.guest_id = None

        _add_visit_card_audit_event(
            db,
            actor_id="operator",
            event_type="visit_card_issue",
            visit=visit,
            card_uid=normalized_uid,
            previous_state={"card_status": previous_card_status},
            next_state={"visit_status": visit.status, "operational_status": visit.operational_status, "card_status": card.status},
            source_channel="operator_open_visit",
            extra={"issue_source": "auto_registered" if auto_registered else "inventory_pool"},
        )

        db.commit()
        db.refresh(visit)
        return visit
    except IntegrityError as exc:
        db.rollback()
        message = str(getattr(exc, "orig", exc))
        if "uq_visits_one_active_per_guest" in message:
            detail = "Guest already has an active visit"
        elif "uq_visits_one_active_per_card" in message:
            detail = "Card already used by another active visit"
        else:
            detail = "Visit invariant violation"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def authorize_pour_lock(db: Session, card_uid: str, tap_id: int, actor_id: str):
    normalized_uid = _normalize_card_uid(card_uid)
    if lost_card_crud.is_lost_card(db=db, card_uid=normalized_uid):
        _add_audit_log(
            db,
            actor_id=actor_id,
            action="lost_card_blocked",
            target_entity="Card",
            target_id=normalized_uid,
            details={
                "card_uid": normalized_uid,
                "tap_id": tap_id,
                "blocked_at": "db_timestamp",
            },
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"reason": "lost_card", "message": "Card is marked as lost"},
        )

    active_visit = get_active_visit_by_card_uid(db=db, card_uid=normalized_uid)
    if not active_visit:
        raise _authorize_error(
            status.HTTP_409_CONFLICT,
            reason="no_active_visit",
            message=f"No active visit for Card {normalized_uid}.",
        )
    if active_visit.operational_status != VISIT_OP_ACTIVE_ASSIGNED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"reason": "visit_not_authorizable", "message": "Visit is not in an authorizable state"},
        )

    if active_visit.active_tap_id is not None and active_visit.active_tap_id != tap_id:
        _add_audit_log(
            db,
            actor_id=actor_id,
            action="card_in_use_on_other_tap",
            target_entity="Visit",
            target_id=str(active_visit.visit_id),
            details={
                "card_uid": normalized_uid,
                "requested_tap_id": tap_id,
                "active_tap_id": active_visit.active_tap_id,
                "event": "authorize_conflict",
            },
        )
        db.commit()
        raise _authorize_error(
            status.HTTP_409_CONFLICT,
            reason="card_in_use_on_other_tap",
            message=f"Card already in use on Tap {active_visit.active_tap_id}",
            context={"active_tap_id": active_visit.active_tap_id, "requested_tap_id": tap_id},
        )

    tap = db.query(models.Tap).filter(models.Tap.tap_id == tap_id).first()
    if not tap or not tap.keg_id:
        raise _authorize_error(
            status.HTTP_409_CONFLICT,
            reason="tap_not_configured",
            message="Tap is not configured with keg",
            context={"tap_id": tap_id},
        )

    beverage = tap.keg.beverage if tap.keg else None
    guest = active_visit.guest
    if not beverage or not guest:
        raise _authorize_error(
            status.HTTP_409_CONFLICT,
            reason="tap_not_configured",
            message="Tap is not configured with beverage pricing",
            context={"tap_id": tap_id},
        )

    policy = system_crud.get_pour_policy(db)
    authorize_context = _build_authorize_context(guest=guest, beverage=beverage, policy=policy)
    if authorize_context["max_volume_ml"] < authorize_context["min_start_ml"]:
        detail = _build_insufficient_funds_detail(authorize_context)
        _add_audit_log(
            db,
            actor_id=actor_id,
            action="insufficient_funds_blocked",
            target_entity="Visit",
            target_id=str(active_visit.visit_id),
            details={
                "card_uid": normalized_uid,
                "guest_id": str(active_visit.guest_id),
                "visit_id": str(active_visit.visit_id),
                "tap_id": tap_id,
                "balance_cents": authorize_context["balance_cents"],
                "required_cents": detail["context"]["required_cents"],
                "min_start_ml": authorize_context["min_start_ml"],
                "max_volume_ml": authorize_context["max_volume_ml"],
            },
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )

    if active_visit.active_tap_id is not None and active_visit.active_tap_id != tap_id:
        _add_audit_log(
            db,
            actor_id=actor_id,
            action="card_in_use_on_other_tap",
            target_entity="Visit",
            target_id=str(active_visit.visit_id),
            details={
                "card_uid": card_uid,
                "requested_tap_id": tap_id,
                "active_tap_id": active_visit.active_tap_id,
                "event": "authorize_conflict",
            },
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Card already in use on Tap {active_visit.active_tap_id}",
        )

    tap = db.query(models.Tap).filter(models.Tap.tap_id == tap_id).first()
    if not tap or not tap.keg_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tap is not configured with keg")

    beverage = tap.keg.beverage if tap.keg else None
    guest = active_visit.guest
    if beverage and guest:
        minimum_charge = (beverage.sell_price_per_liter / Decimal("1000")).quantize(Decimal("0.0001"))
        if guest.balance < minimum_charge:
            _add_audit_log(
                db,
                actor_id=actor_id,
                action="insufficient_funds_denied",
                target_entity="Visit",
                target_id=str(active_visit.visit_id),
                details={
                    "card_uid": normalized_uid,
                    "guest_id": str(active_visit.guest_id),
                    "visit_id": str(active_visit.visit_id),
                    "tap_id": tap_id,
                    "balance": str(guest.balance),
                    "minimum_charge": str(minimum_charge),
                },
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "reason": "insufficient_funds",
                    "message": "Insufficient funds: top up guest balance before pouring.",
                },
            )

    lock_attempt = db.execute(
        update(models.Visit)
        .where(
            models.Visit.visit_id == active_visit.visit_id,
            models.Visit.status == "active",
            or_(models.Visit.active_tap_id.is_(None), models.Visit.active_tap_id == tap_id),
        )
        .values(active_tap_id=tap_id, lock_set_at=func.now())
    )

    if lock_attempt.rowcount == 0:
        current = get_visit(db, active_visit.visit_id)
        current_tap_id = current.active_tap_id if current else None
        _add_audit_log(
            db,
            actor_id=actor_id,
            action="card_in_use_on_other_tap",
            target_entity="Visit",
            target_id=str(active_visit.visit_id),
            details={
                "card_uid": normalized_uid,
                "requested_tap_id": tap_id,
                "active_tap_id": current_tap_id,
                "event": "authorize_conflict",
            },
        )
        db.commit()
        raise _authorize_error(
            status.HTTP_409_CONFLICT,
            reason="card_in_use_on_other_tap",
            message=f"Card already in use on Tap {current_tap_id}",
            context={"active_tap_id": current_tap_id, "requested_tap_id": tap_id},
        )

    if tap and tap.status == "active":
        tap.status = "processing_sync"
    price_per_ml = pour_policy.sell_price_per_liter_to_price_per_ml(beverage.sell_price_per_liter)
    pending_outcome = _ensure_pending_pour_for_active_visit(
        db=db,
        visit=active_visit,
        tap_id=tap_id,
        price_per_ml=price_per_ml,
    )

    db.commit()
    db.refresh(active_visit)
    return active_visit, pending_outcome, authorize_context




def _safe_details(details: str | None) -> dict:
    if not details:
        return {}
    try:
        return json.loads(details)
    except json.JSONDecodeError:
        return {}


def _operator_action_label(action: str, details: dict) -> tuple[str, str | None]:
    mapping = {
        "visit_force_unlock": "Оператор снял блокировку",
        "reconcile_done": "Оператор выполнил ручную сверку",
        "lost_card_blocked": "Карта заблокирована как потерянная",
        "card_in_use_on_other_tap": "Попытка наливать на другом кране",
        "insufficient_funds_blocked": "Налив заблокирован из-за недостатка средств",
        "sync_tail_overdraft_accepted": "Принят налив с хвостом сверх баланса",
        "sync_missing_pending": "Синхронизация пришла без pending-авторизации",
        "sync_conflict": "Конфликт синхронизации по крану",
        "sync_rejected_insufficient_funds": "Синхронизация отклонена: не хватило средств",
        "late_sync_mismatch": "Поздняя синхронизация зафиксирована как инцидент",
        "late_sync_matched": "Поздняя синхронизация сопоставлена с ручной сверкой",
    }
    detail_text = None
    if action == 'visit_force_unlock':
        detail_text = details.get('reason')
    elif action == 'reconcile_done':
        detail_text = details.get('comment') or details.get('reason')
    elif action in {'card_in_use_on_other_tap', 'sync_conflict'}:
        detail_text = f"Кран {details.get('requested_tap_id') or details.get('tap_id')} vs активный {details.get('active_tap_id')}"
    elif action.startswith('sync_'):
        detail_text = details.get('reason') or details.get('short_id')
    return mapping.get(action, action), detail_text


def _build_session_history_item(db: Session, visit: models.Visit, include_narrative: bool = False):
    guest = visit.guest
    full_name = ' '.join([part for part in [guest.last_name, guest.first_name, guest.patronymic] if part]) if guest else '—'
    pours = list(sorted(visit.pours, key=lambda item: item.authorized_at or item.poured_at or item.created_at or visit.opened_at))
    pour_tap_ids = sorted({int(p.tap_id) for p in pours if p.tap_id is not None})
    tap_ids = set(pour_tap_ids)
    audit_logs = db.query(models.AuditLog).filter(
        models.AuditLog.target_entity == 'Visit',
        models.AuditLog.target_id == str(visit.visit_id),
    ).order_by(models.AuditLog.timestamp.asc()).all()
    operator_actions = []
    incident_actions = []
    last_operator_action_at = None
    contains_tail_pour = False
    last_sync_at = None
    for log in audit_logs:
        details = _safe_details(log.details)
        label, detail_text = _operator_action_label(log.action, details)
        if log.action in {
            'visit_force_unlock','reconcile_done','lost_card_blocked','card_in_use_on_other_tap',
            'insufficient_funds_blocked','insufficient_funds_denied','sync_tail_overdraft_accepted','sync_missing_pending',
            'sync_conflict','sync_rejected_insufficient_funds','late_sync_mismatch','late_sync_matched'
        }:
            operator_actions.append(schemas.SessionOperatorAction(timestamp=log.timestamp, action=log.action, actor_id=log.actor_id, label=label, details=detail_text))
            last_operator_action_at = log.timestamp
        if log.action in {'card_in_use_on_other_tap','insufficient_funds_blocked','insufficient_funds_denied','sync_missing_pending','sync_conflict','sync_rejected_insufficient_funds','late_sync_mismatch','lost_card_blocked'}:
            incident_actions.append(log)
        if log.action == 'sync_tail_overdraft_accepted':
            contains_tail_pour = True
            last_sync_at = log.timestamp

    short_ids = [p.short_id for p in pours if p.short_id]
    flow_filters = []
    if visit.card_uid:
        flow_filters.append(models.NonSaleFlow.card_uid == visit.card_uid)
    if short_ids:
        flow_filters.append(models.NonSaleFlow.short_id.in_(short_ids))
    non_sale_flows = []
    if flow_filters:
        non_sale_query = db.query(models.NonSaleFlow).filter(or_(*flow_filters))
        non_sale_query = non_sale_query.filter(models.NonSaleFlow.last_seen_at >= visit.opened_at - timedelta(hours=1))
        if visit.closed_at is not None:
            non_sale_query = non_sale_query.filter(models.NonSaleFlow.last_seen_at <= visit.closed_at + timedelta(hours=1))
        non_sale_flows = non_sale_query.all()
    contains_non_sale_flow = len(non_sale_flows) > 0

    sync_statuses = {p.sync_status for p in pours}
    if 'pending_sync' in sync_statuses or visit.active_tap_id is not None:
        sync_state = 'pending_sync'
    elif 'rejected' in sync_statuses:
        sync_state = 'rejected'
    elif 'reconciled' in sync_statuses:
        sync_state = 'reconciled'
    elif 'synced' in sync_statuses:
        sync_state = 'synced'
    else:
        sync_state = 'not_started'

    has_unsynced = sync_state in {'pending_sync','rejected'}
    primary_tap_id = pour_tap_ids[-1] if pour_tap_ids else visit.active_tap_id
    if visit.active_tap_id is not None:
        tap_ids.add(int(visit.active_tap_id))
    completion_source = None
    if visit.status == 'closed':
        reason = (visit.closed_reason or '').strip()
        completion_source = reason or None
    elif contains_non_sale_flow:
        completion_source = 'no_sale_flow'
    elif any(action.action == 'lost_card_blocked' for action in operator_actions):
        completion_source = 'blocked_lost_card'
    elif any(action.action == 'insufficient_funds_blocked' for action in operator_actions):
        completion_source = 'blocked_insufficient_funds'
    elif any(action.action == 'card_in_use_on_other_tap' for action in operator_actions):
        completion_source = 'blocked_card_in_use'
    elif any(action.action == 'insufficient_funds_denied' for action in operator_actions):
        completion_source = 'denied_insufficient_funds'
    elif visit.active_tap_id is None and has_unsynced:
        completion_source = 'sync_pending'

    operator_status = 'Активна' if visit.status == 'active' else 'Завершена'
    if visit.status == 'closed' and (visit.closed_reason or '').strip() not in {'', 'guest_checkout', 'operator_close', 'manual_close'}:
        operator_status = 'Прервана'
    elif has_unsynced:
        operator_status = 'Требует внимания'
    elif incident_actions:
        operator_status = 'С инцидентами'

    first_authorized_at = next((p.authorized_at for p in pours if p.authorized_at), None)
    first_pour_started_at = next((p.started_at for p in pours if p.started_at), None)
    last_pour_ended_at = max([p.ended_at for p in pours if p.ended_at], default=None)
    if last_sync_at is None:
        last_sync_at = max([dt for dt in [p.synced_at or p.reconciled_at for p in pours] if dt], default=None)
    last_event_at = max([dt for dt in [visit.closed_at, last_pour_ended_at, last_sync_at, last_operator_action_at, visit.lock_set_at, visit.opened_at] if dt])

    item = schemas.SessionHistoryDetail if include_narrative else schemas.SessionHistoryListItem
    display_context = _derive_display_context(
        db,
        tap_id=primary_tap_id,
        has_incident=bool(incident_actions),
        incident_count=len(incident_actions),
    ) if include_narrative else None

    payload = dict(
        visit_id=visit.visit_id, guest_id=visit.guest_id, guest_full_name=full_name, phone_number=guest.phone_number if guest else None,
        card_uid=visit.card_uid, visit_status=visit.status, operational_status=visit.operational_status,
        operator_status=operator_status, completion_source=completion_source,
        sync_state=sync_state, primary_tap_id=primary_tap_id, taps=sorted(tap_ids), incident_count=len(incident_actions),
        has_incident=bool(incident_actions), has_unsynced=has_unsynced, contains_tail_pour=contains_tail_pour,
        contains_non_sale_flow=contains_non_sale_flow, opened_at=visit.opened_at, closed_at=visit.closed_at, last_event_at=last_event_at,
        operator_actions=operator_actions, lifecycle=schemas.SessionLifecycleTimestamps(
            opened_at=visit.opened_at, first_authorized_at=first_authorized_at, first_pour_started_at=first_pour_started_at,
            last_pour_ended_at=last_pour_ended_at, closed_at=visit.closed_at, last_sync_at=last_sync_at, last_operator_action_at=last_operator_action_at,
        ),
    )
    if not include_narrative:
        return item(**payload)

    narrative = [schemas.SessionNarrativeEvent(timestamp=visit.opened_at, kind='open', title='Сессия открыта', description='Оператор открыл визит для гостя.')]
    if first_authorized_at:
        tap_text = f'Кран #{primary_tap_id}' if primary_tap_id is not None else 'кран не определён'
        narrative.append(schemas.SessionNarrativeEvent(timestamp=first_authorized_at, kind='authorize', title='Налив авторизован', description=f'Backend разрешил налив, {tap_text}.', status=sync_state))
    for pour in pours:
        if pour.started_at:
            tail_flag = ''
            narrative.append(schemas.SessionNarrativeEvent(timestamp=pour.started_at, kind='pour', title='Зафиксирован налив', description=f'Продажа {pour.volume_ml} мл, чек {pour.amount_charged} ₽, short ID {pour.short_id or "—"}.{tail_flag}', status=pour.sync_status))
        terminal_ts = pour.synced_at or pour.reconciled_at or pour.ended_at or pour.poured_at
        if terminal_ts:
            title = 'Синхронизация подтверждена' if pour.sync_status == 'synced' else ('Ручная сверка подтверждена' if pour.sync_status == 'reconciled' else 'Синхронизация завершилась ошибкой')
            narrative.append(schemas.SessionNarrativeEvent(timestamp=terminal_ts, kind='sync_result', title=title, description=f'Статус backend: {pour.sync_status}.', status=pour.sync_status))
    for flow in non_sale_flows:
        narrative.append(schemas.SessionNarrativeEvent(timestamp=flow.last_seen_at, kind='non_sale', title='Зафиксирован несервисный/непродажный поток', description=f'Кран #{flow.tap_id}, причина: {flow.reason}, объём {flow.volume_ml} мл.', status=flow.flow_category))
    for action in operator_actions:
        narrative.append(schemas.SessionNarrativeEvent(timestamp=action.timestamp, kind='operator', title=action.label, description=action.details or 'Операторское вмешательство.', status=action.action, actor_id=action.actor_id))
    if visit.closed_at:
        close_kind = 'abort' if operator_status == 'Прервана' else 'close'
        narrative.append(schemas.SessionNarrativeEvent(timestamp=visit.closed_at, kind=close_kind, title='Сессия завершена', description=f'Причина завершения: {visit.closed_reason or "не указана"}.', status=visit.status))
    payload['narrative'] = sorted(narrative, key=lambda item: item.timestamp)
    payload['display_context'] = display_context
    return item(**payload)


def get_session_history(db: Session, *, date_from=None, date_to=None, tap_id=None, status=None, card_uid=None, incident_only=False, unsynced_only=False):
    query = db.query(models.Visit).join(models.Guest).order_by(models.Visit.opened_at.desc())
    if date_from:
        query = query.filter(func.date(models.Visit.opened_at) >= date_from)
    if date_to:
        query = query.filter(func.date(models.Visit.opened_at) <= date_to)
    if card_uid:
        query = query.filter(models.Visit.card_uid.ilike(f'%{card_uid.strip()}%'))
    if status in {'active','closed'}:
        query = query.filter(models.Visit.status == status)
    visits = query.all()
    items = [_build_session_history_item(db, visit) for visit in visits]
    if tap_id is not None:
        items = [item for item in items if tap_id in item.taps or item.primary_tap_id == tap_id]
    if status == 'aborted':
        items = [item for item in items if item.operator_status == 'Прервана']
    if incident_only:
        items = [item for item in items if item.has_incident]
    if unsynced_only:
        items = [item for item in items if item.has_unsynced]
    return items


def get_session_history_detail(db: Session, visit_id: uuid.UUID):
    visit = db.query(models.Visit).filter(models.Visit.visit_id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Visit not found')
    return _build_session_history_item(db, visit, include_narrative=True)


def report_lost_card_from_visit(
    db: Session,
    *,
    visit_id: uuid.UUID,
    reason: str | None,
    comment: str | None,
    actor_id: str | None,
):
    visit = get_visit(db=db, visit_id=visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only active visit can report lost card")
    if not visit.card_uid:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Visit has no card assigned")
    if visit.operational_status == VISIT_OP_ACTIVE_BLOCKED_LOST:
        lost_card = lost_card_crud.get_lost_card_by_uid(db=db, card_uid=visit.card_uid)
        if not lost_card:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Visit is already blocked by lost-card flow")
        return visit, lost_card, False

    lost_card, created = lost_card_crud.create_lost_card_idempotent(
        db=db,
        card_uid=visit.card_uid,
        reported_by=actor_id,
        reason=reason,
        comment=comment,
        visit_id=visit.visit_id,
        guest_id=visit.guest_id,
        auto_commit=False,
    )
    card = card_crud.get_card_by_uid(db, visit.card_uid)
    previous_card_status = card.status if card else None
    previous_operational_status = visit.operational_status
    if card:
        card.status = card_crud.CARD_STATUS_LOST
        card.guest_id = None
    visit.operational_status = VISIT_OP_ACTIVE_BLOCKED_LOST
    _add_visit_card_audit_event(
        db,
        actor_id=actor_id,
        event_type="visit_card_lost",
        visit=visit,
        card_uid=visit.card_uid,
        previous_state={"operational_status": previous_operational_status, "card_status": previous_card_status},
        next_state={"operational_status": visit.operational_status, "card_status": card.status if card else card_crud.CARD_STATUS_LOST},
        source_channel="operator_report_lost_card",
        reason_code=reason,
        comment=comment,
    )
    db.commit()
    db.refresh(visit)
    return visit, lost_card, created


def restore_lost_card_for_visit(
    db: Session,
    *,
    visit_id: uuid.UUID,
    reason: str | None,
    comment: str | None,
    actor_id: str | None,
):
    visit = get_visit(db=db, visit_id=visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.status != "active" or visit.operational_status != VISIT_OP_ACTIVE_BLOCKED_LOST:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a blocked-lost active visit can cancel the lost-card mark")
    if not visit.card_uid:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Visit has no card assigned")

    lost_card = lost_card_crud.get_lost_card_by_uid(db=db, card_uid=visit.card_uid)
    if not lost_card:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Blocked-lost visit has no matching lost-card record")
    if lost_card.visit_id and lost_card.visit_id != visit.visit_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Lost-card record is linked to another visit")

    card = card_crud.get_card_by_uid(db, visit.card_uid)
    if not card:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Blocked-lost visit card is missing from inventory")
    if card.status == card_crud.CARD_STATUS_RETIRED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Retired card cannot be restored to an active visit")

    previous_card_status = card.status
    previous_operational_status = visit.operational_status
    card.status = card_crud.CARD_STATUS_ASSIGNED
    card.guest_id = None
    visit.operational_status = VISIT_OP_ACTIVE_ASSIGNED
    db.delete(lost_card)

    _add_visit_card_audit_event(
        db,
        actor_id=actor_id,
        event_type="visit_card_lost_cancelled",
        visit=visit,
        card_uid=visit.card_uid,
        previous_state={"operational_status": previous_operational_status, "card_status": previous_card_status, "lost_registry_present": True},
        next_state={"operational_status": visit.operational_status, "card_status": card.status, "lost_registry_present": False},
        source_channel="operator_restore_lost_card_for_visit",
        reason_code=reason,
        comment=comment,
    )

    db.commit()
    db.refresh(visit)
    return visit


def force_unlock_visit(db: Session, visit_id: uuid.UUID, reason: str, comment: str | None, actor_id: str):
    visit = get_visit(db, visit_id=visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")

    if visit.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only active visit can be force-unlocked")

    previous_tap_id = visit.active_tap_id
    visit.active_tap_id = None
    visit.lock_set_at = None

    if previous_tap_id is not None:
        tap = db.query(models.Tap).filter(models.Tap.tap_id == previous_tap_id).first()
        if tap and tap.status == "processing_sync":
            tap.status = "active"

    _add_audit_log(
        db,
        actor_id=actor_id,
        action="visit_force_unlock",
        target_entity="Visit",
        target_id=str(visit.visit_id),
        details={
            "card_uid": visit.card_uid,
            "previous_tap_id": previous_tap_id,
            "reason": reason,
            "comment": comment,
        },
    )

    db.commit()
    db.refresh(visit)
    return visit


def close_visit(db: Session, visit_id: uuid.UUID, closed_reason: str, returned_card_uid: str, actor_id: str):
    visit = get_visit(db, visit_id=visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")

    if visit.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Visit is already closed")
    if visit.operational_status != VISIT_OP_ACTIVE_ASSIGNED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an active assigned visit can be normally closed with card return confirmation",
        )

    pending_sync = (
        db.query(models.Pour.pour_id)
        .filter(
            models.Pour.visit_id == visit_id,
            models.Pour.sync_status == "pending_sync",
            models.Pour.is_manual_reconcile.is_(False),
        )
        .first()
    )
    if pending_sync:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="pending_sync_exists_for_visit")

    normalized_returned_uid = _normalize_card_uid(returned_card_uid)
    if normalized_returned_uid != visit.card_uid:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Returned card UID does not match the active visit card")

    visit.status = "closed"
    visit.operational_status = VISIT_OP_CLOSED_OK
    visit.closed_reason = closed_reason
    visit.closed_at = func.now()
    visit.card_returned = True
    previous_tap_id = visit.active_tap_id
    visit.active_tap_id = None
    visit.lock_set_at = None
    visit.return_method = "operator_nfc"
    visit.returned_by = actor_id
    visit.returned_at = func.now()

    if previous_tap_id is not None:
        tap = db.query(models.Tap).filter(models.Tap.tap_id == previous_tap_id).first()
        if tap and tap.status == "processing_sync":
            tap.status = "active"

    card = card_crud.get_card_by_uid(db, visit.card_uid)
    if card:
        previous_card_status = card.status
        card.status = card_crud.CARD_STATUS_RETURNED
        card.guest_id = None
        _add_visit_card_audit_event(
            db,
            actor_id=actor_id,
            event_type="visit_card_return",
            visit=visit,
            card_uid=visit.card_uid,
            previous_state={"operational_status": VISIT_OP_ACTIVE_ASSIGNED, "card_status": previous_card_status},
            next_state={"operational_status": visit.operational_status, "card_status": card.status},
            source_channel="operator_return_scan_close",
            reason_code=closed_reason,
            extra={"confirm_method": "nfc_scan_match", "matched": True, "returned_card_uid": normalized_returned_uid},
        )

    db.commit()
    db.refresh(visit)
    return visit


def assign_card_to_active_visit(db: Session, visit_id: uuid.UUID, card_uid: str):
    visit = get_visit(db, visit_id=visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only active visit can be updated")
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Normal operator flow no longer supports separate card assignment; open with card or use reissue flow")


def reissue_card_for_visit(
    db: Session,
    *,
    visit_id: uuid.UUID,
    new_card_uid: str,
    reason: str,
    comment: str | None,
    actor_id: str,
):
    visit = get_visit(db, visit_id=visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.status != "active" or visit.operational_status != VISIT_OP_ACTIVE_BLOCKED_LOST:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a blocked-lost active visit can be reissued")

    normalized_uid = _normalize_card_uid(new_card_uid)
    existing_card_visit = get_active_visit_by_card_uid(db=db, card_uid=normalized_uid)
    if existing_card_visit and existing_card_visit.visit_id != visit.visit_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Card already used by another active visit")

    card = card_crud.get_card_by_uid(db, normalized_uid)
    auto_registered = False
    if not card:
        card = models.Card(
            card_uid=normalized_uid,
            status=card_crud.CARD_STATUS_AVAILABLE,
            guest_id=None,
        )
        db.add(card)
        try:
            db.flush()
            auto_registered = True
        except IntegrityError:
            db.rollback()
            visit = get_visit(db, visit_id=visit_id)
            if not visit:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
            if visit.status != "active" or visit.operational_status != VISIT_OP_ACTIVE_BLOCKED_LOST:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a blocked-lost active visit can be reissued")
            existing_card_visit = get_active_visit_by_card_uid(db=db, card_uid=normalized_uid)
            if existing_card_visit and existing_card_visit.visit_id != visit.visit_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Card already used by another active visit")
            card = card_crud.get_card_by_uid(db, normalized_uid)
            if not card:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Replacement card registration conflict, retry reissue")
    if card.status not in {card_crud.CARD_STATUS_AVAILABLE, card_crud.CARD_STATUS_RETURNED}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Replacement card is not issuable from state {card.status}")

    previous_card_uid = visit.card_uid
    previous_card_status = "not_registered" if auto_registered else card.status
    visit.card_uid = normalized_uid
    visit.operational_status = VISIT_OP_ACTIVE_ASSIGNED
    card.status = card_crud.CARD_STATUS_ASSIGNED
    card.guest_id = None

    _add_visit_card_audit_event(
        db,
        actor_id=actor_id,
        event_type="visit_card_reissue",
        visit=visit,
        card_uid=normalized_uid,
        previous_state={"operational_status": VISIT_OP_ACTIVE_BLOCKED_LOST, "old_card_uid": previous_card_uid, "new_card_status": previous_card_status},
        next_state={"operational_status": visit.operational_status, "card_status": card.status, "old_card_uid": previous_card_uid, "new_card_uid": normalized_uid},
        source_channel="operator_reissue_card_for_visit",
        reason_code=reason,
        comment=comment,
        extra={"replacement_source": "auto_registered" if auto_registered else "inventory_pool"},
    )

    db.commit()
    db.refresh(visit)
    return visit


def service_close_missing_card(
    db: Session,
    *,
    visit_id: uuid.UUID,
    closed_reason: str,
    reason_code: str,
    comment: str | None,
    actor_id: str,
):
    visit = get_visit(db, visit_id=visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Visit is already closed")

    pending_sync = (
        db.query(models.Pour.pour_id)
        .filter(
            models.Pour.visit_id == visit_id,
            models.Pour.sync_status == "pending_sync",
            models.Pour.is_manual_reconcile.is_(False),
        )
        .first()
    )
    if pending_sync:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="pending_sync_exists_for_visit")

    previous_tap_id = visit.active_tap_id
    if previous_tap_id is not None:
        tap = db.query(models.Tap).filter(models.Tap.tap_id == previous_tap_id).first()
        if tap and tap.status == "processing_sync":
            tap.status = "active"

    card = card_crud.get_card_by_uid(db, visit.card_uid)
    previous_card_status = card.status if card else None
    if card:
        card.status = card_crud.CARD_STATUS_LOST
        card.guest_id = None
    lost_card_crud.create_lost_card_idempotent(
        db=db,
        card_uid=visit.card_uid,
        reported_by=actor_id,
        reason=reason_code,
        comment=comment,
        visit_id=visit.visit_id,
        guest_id=visit.guest_id,
        auto_commit=False,
    )

    visit.status = "closed"
    visit.operational_status = VISIT_OP_CLOSED_MISSING
    visit.closed_reason = closed_reason
    visit.closed_at = func.now()
    visit.card_returned = False
    visit.active_tap_id = None
    visit.lock_set_at = None

    _add_visit_card_audit_event(
        db,
        actor_id=actor_id,
        event_type="visit_service_close",
        visit=visit,
        card_uid=visit.card_uid,
        previous_state={"operational_status": VISIT_OP_ACTIVE_BLOCKED_LOST if previous_card_status == card_crud.CARD_STATUS_LOST else VISIT_OP_ACTIVE_ASSIGNED, "card_status": previous_card_status},
        next_state={"operational_status": visit.operational_status, "card_status": card.status if card else card_crud.CARD_STATUS_LOST},
        source_channel="operator_service_close_missing_card",
        reason_code=reason_code,
        comment=comment,
    )

    db.commit()
    db.refresh(visit)
    return visit


def reconcile_pour(
    db: Session,
    *,
    visit_id: uuid.UUID,
    tap_id: int,
    short_id: str,
    volume_ml: int,
    amount,
    duration_ms: int | None,
    reason: str,
    comment: str | None,
    actor_id: str,
):
    visit = get_visit(db, visit_id=visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")

    existing = (
        db.query(models.Pour)
        .filter(
            models.Pour.visit_id == visit_id,
            models.Pour.short_id == short_id,
            models.Pour.is_manual_reconcile.is_(True),
        )
        .first()
    )
    if existing:
        if visit.active_tap_id == tap_id:
            visit.active_tap_id = None
            visit.lock_set_at = None
            tap = db.query(models.Tap).filter(models.Tap.tap_id == tap_id).first()
            if tap and tap.status == "processing_sync":
                tap.status = "active"
        db.commit()
        db.refresh(visit)
        return visit

    if visit.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only active visit can be reconciled")
    if visit.active_tap_id != tap_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Visit is not locked on Tap {tap_id}")
    if not visit.card_uid:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Visit has no card assigned")

    tap = (
        db.query(models.Tap)
        .filter(models.Tap.tap_id == tap_id)
        .first()
    )
    if not tap or not tap.keg_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tap is not configured with keg")

    guest = db.query(models.Guest).filter(models.Guest.guest_id == visit.guest_id).first()
    if not guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")

    if guest.balance < amount:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient guest balance for manual reconcile")

    keg = db.query(models.Keg).filter(models.Keg.keg_id == tap.keg_id).first()
    if not keg:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Keg not found")
    if keg.current_volume_ml < volume_ml:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient keg volume for manual reconcile")

    price_per_ml = (Decimal(amount) / Decimal(volume_ml)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    pending_pour = _get_pending_pour_for_visit_tap(db=db, visit_id=visit_id, tap_id=tap_id)
    finalized_pour = pending_pour
    if pending_pour:
        pending_pour.card_uid = visit.card_uid
        pending_pour.guest_id = visit.guest_id
        pending_pour.keg_id = tap.keg_id
        pending_pour.volume_ml = volume_ml
        pending_pour.poured_at = func.now()
        pending_pour.amount_charged = amount
        pending_pour.price_per_ml_at_pour = price_per_ml
        pending_pour.duration_ms = duration_ms
        pending_pour.sync_status = "reconciled"
        pending_pour.reconciled_at = func.now()
        pending_pour.synced_at = None
        pending_pour.short_id = short_id
        pending_pour.is_manual_reconcile = True
    else:
        manual_client_tx_id = f"manual-reconcile:{visit_id}:{short_id}"
        finalized_pour = models.Pour(
            client_tx_id=manual_client_tx_id,
            card_uid=visit.card_uid,
            tap_id=tap_id,
            visit_id=visit_id,
            volume_ml=volume_ml,
            poured_at=func.now(),
            amount_charged=amount,
            price_per_ml_at_pour=price_per_ml,
            duration_ms=duration_ms,
            guest_id=visit.guest_id,
            keg_id=tap.keg_id,
            sync_status="reconciled",
            reconciled_at=func.now(),
            short_id=short_id,
            is_manual_reconcile=True,
        )
        db.add(finalized_pour)

    guest.balance -= amount
    keg.current_volume_ml -= volume_ml
    visit.active_tap_id = None
    visit.lock_set_at = None
    if tap.status == "processing_sync":
        tap.status = "active"
    db.flush()
    db.refresh(finalized_pour)
    get_pos_adapter().notify_pour(db=db, pour=finalized_pour, guest=guest)

    _add_audit_log(
        db,
        actor_id=actor_id,
        action="reconcile_done",
        target_entity="Visit",
        target_id=str(visit.visit_id),
        details={
            "tap_id": tap_id,
            "short_id": short_id,
            "volume_ml": volume_ml,
            "amount": str(amount),
            "reason": reason,
            "comment": comment,
        },
    )

    db.commit()
    db.refresh(visit)
    return visit
