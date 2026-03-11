from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

import models
import schemas


FINAL_SALE_SYNC_STATUSES = {"synced", "reconciled"}


def is_non_sale_flow_event(payload: schemas.ControllerFlowEventRequest) -> bool:
    return payload.session_state != "authorized_session"


def classify_non_sale_flow(*, session_state: str, reason: str) -> str:
    if reason == "flow_detected_when_valve_closed_without_active_session":
        if session_state == "no_card_no_session":
            return "closed_valve_no_card"
        if session_state == "card_present_no_session":
            return "closed_valve_no_session"
        return "closed_valve_no_valid_session"
    return "controller_flow_anomaly"


def _event_started_at(now: datetime, duration_ms: int) -> datetime:
    if duration_ms <= 0:
        return now
    return now - timedelta(milliseconds=duration_ms)


def _deplete_keg_for_non_sale_flow(
    *,
    tap: models.Tap | None,
    keg: models.Keg | None,
    delta_ml: int,
    now: datetime,
) -> None:
    if keg is None or delta_ml <= 0:
        return

    keg.current_volume_ml = max(int(keg.current_volume_ml or 0) - delta_ml, 0)
    if keg.current_volume_ml == 0:
        keg.status = "empty"
        keg.finished_at = now
        if tap is not None:
            tap.status = "empty"


def record_non_sale_flow(
    db: Session,
    *,
    payload: schemas.ControllerFlowEventRequest,
) -> models.NonSaleFlow:
    now = datetime.utcnow()
    flow = (
        db.query(models.NonSaleFlow)
        .filter(models.NonSaleFlow.event_id == payload.event_id)
        .first()
    )
    tap = (
        db.query(models.Tap)
        .options(joinedload(models.Tap.keg))
        .filter(models.Tap.tap_id == payload.tap_id)
        .first()
    )

    if flow is None:
        flow = models.NonSaleFlow(
            event_id=payload.event_id,
            tap_id=payload.tap_id,
            volume_ml=0,
            accounted_volume_ml=0,
            duration_ms=0,
            flow_category=classify_non_sale_flow(
                session_state=payload.session_state,
                reason=payload.reason,
            ),
            session_state=payload.session_state,
            reason=payload.reason,
            card_present=payload.card_present,
            valve_open=payload.valve_open,
            card_uid=payload.card_uid,
            short_id=payload.short_id,
            started_at=_event_started_at(now, int(payload.duration_ms or 0)),
            last_seen_at=now,
            finalized_at=now if payload.event_status == "stopped" else None,
            keg_id=tap.keg_id if tap else None,
        )
        db.add(flow)

    flow.flow_category = classify_non_sale_flow(
        session_state=payload.session_state,
        reason=payload.reason,
    )
    flow.session_state = payload.session_state
    flow.reason = payload.reason
    flow.card_present = payload.card_present
    flow.valve_open = payload.valve_open
    flow.card_uid = payload.card_uid
    flow.short_id = payload.short_id
    flow.last_seen_at = now
    flow.duration_ms = max(int(flow.duration_ms or 0), int(payload.duration_ms or 0))
    if flow.started_at is None:
        flow.started_at = _event_started_at(now, int(payload.duration_ms or 0))
    if flow.keg_id is None and tap is not None and tap.keg_id is not None:
        flow.keg_id = tap.keg_id

    latest_volume_ml = max(int(flow.volume_ml or 0), int(payload.volume_ml or 0))
    delta_ml = max(latest_volume_ml - int(flow.accounted_volume_ml or 0), 0)

    accounting_keg = None
    if flow.keg_id is not None:
        if tap is not None and tap.keg_id == flow.keg_id and tap.keg is not None:
            accounting_keg = tap.keg
        else:
            accounting_keg = (
                db.query(models.Keg)
                .filter(models.Keg.keg_id == flow.keg_id)
                .first()
            )

    _deplete_keg_for_non_sale_flow(
        tap=tap,
        keg=accounting_keg,
        delta_ml=delta_ml,
        now=now,
    )
    flow.volume_ml = latest_volume_ml
    flow.accounted_volume_ml = latest_volume_ml

    if payload.event_status == "stopped":
        flow.finalized_at = now

    return flow


def get_flow_summary(
    db: Session,
    *,
    tap_id: int | None = None,
) -> schemas.FlowSummaryResponse:
    sale_query = (
        db.query(
            models.Pour.tap_id.label("tap_id"),
            func.coalesce(func.sum(models.Pour.volume_ml), 0).label("sale_volume_ml"),
        )
        .filter(models.Pour.sync_status.in_(tuple(FINAL_SALE_SYNC_STATUSES)))
    )
    if tap_id is not None:
        sale_query = sale_query.filter(models.Pour.tap_id == tap_id)
    sale_rows = sale_query.group_by(models.Pour.tap_id).all()

    non_sale_query = (
        db.query(
            models.NonSaleFlow.tap_id.label("tap_id"),
            func.coalesce(func.sum(models.NonSaleFlow.volume_ml), 0).label("non_sale_volume_ml"),
        )
    )
    if tap_id is not None:
        non_sale_query = non_sale_query.filter(models.NonSaleFlow.tap_id == tap_id)
    non_sale_rows = non_sale_query.group_by(models.NonSaleFlow.tap_id).all()

    breakdown_query = (
        db.query(
            models.NonSaleFlow.tap_id.label("tap_id"),
            models.NonSaleFlow.flow_category.label("reason_code"),
            func.coalesce(func.sum(models.NonSaleFlow.volume_ml), 0).label("volume_ml"),
        )
    )
    if tap_id is not None:
        breakdown_query = breakdown_query.filter(models.NonSaleFlow.tap_id == tap_id)
    breakdown_rows = (
        breakdown_query
        .group_by(models.NonSaleFlow.tap_id, models.NonSaleFlow.flow_category)
        .all()
    )

    overall_breakdown_query = (
        db.query(
            models.NonSaleFlow.flow_category.label("reason_code"),
            func.coalesce(func.sum(models.NonSaleFlow.volume_ml), 0).label("volume_ml"),
        )
    )
    if tap_id is not None:
        overall_breakdown_query = overall_breakdown_query.filter(models.NonSaleFlow.tap_id == tap_id)
    overall_breakdown_rows = (
        overall_breakdown_query
        .group_by(models.NonSaleFlow.flow_category)
        .all()
    )

    tap_ids = {int(row.tap_id) for row in sale_rows} | {int(row.tap_id) for row in non_sale_rows}
    taps = (
        db.query(models.Tap)
        .filter(models.Tap.tap_id.in_(tap_ids))
        .all()
        if tap_ids
        else []
    )
    tap_names = {tap.tap_id: tap.display_name for tap in taps}

    sale_by_tap = {int(row.tap_id): int(row.sale_volume_ml or 0) for row in sale_rows}
    non_sale_by_tap = {int(row.tap_id): int(row.non_sale_volume_ml or 0) for row in non_sale_rows}
    breakdown_by_tap: dict[int, list[schemas.FlowSummaryBreakdownItem]] = defaultdict(list)
    for row in breakdown_rows:
        breakdown_by_tap[int(row.tap_id)].append(
            schemas.FlowSummaryBreakdownItem(
                reason_code=str(row.reason_code),
                volume_ml=int(row.volume_ml or 0),
            )
        )

    by_tap = []
    for item_tap_id in sorted(tap_ids):
        sale_volume_ml = sale_by_tap.get(item_tap_id, 0)
        non_sale_volume_ml = non_sale_by_tap.get(item_tap_id, 0)
        by_tap.append(
            schemas.TapFlowSummaryItem(
                tap_id=item_tap_id,
                tap_name=tap_names.get(item_tap_id),
                sale_volume_ml=sale_volume_ml,
                non_sale_volume_ml=non_sale_volume_ml,
                total_volume_ml=sale_volume_ml + non_sale_volume_ml,
                non_sale_breakdown=sorted(
                    breakdown_by_tap.get(item_tap_id, []),
                    key=lambda item: item.reason_code,
                ),
            )
        )

    sale_volume_ml = sum(item.sale_volume_ml for item in by_tap)
    non_sale_volume_ml = sum(item.non_sale_volume_ml for item in by_tap)

    return schemas.FlowSummaryResponse(
        sale_volume_ml=sale_volume_ml,
        non_sale_volume_ml=non_sale_volume_ml,
        total_volume_ml=sale_volume_ml + non_sale_volume_ml,
        non_sale_breakdown=[
            schemas.FlowSummaryBreakdownItem(
                reason_code=str(row.reason_code),
                volume_ml=int(row.volume_ml or 0),
            )
            for row in sorted(overall_breakdown_rows, key=lambda item: item.reason_code)
        ],
        by_tap=by_tap,
    )
