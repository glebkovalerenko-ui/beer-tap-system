from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import uuid

from fastapi import HTTPException, status
from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas


KEG_PLACEHOLDER_NOTE = "Will be added when keg<->pour linkage is implemented"


def _is_timezone_aware(value: datetime | None) -> bool:
    if value is None:
        return False
    return value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None


def _align_datetime_to_reference(value: datetime, reference: datetime | None) -> datetime:
    if reference is None:
        return value

    reference_is_aware = _is_timezone_aware(reference)
    value_is_aware = _is_timezone_aware(value)

    if reference_is_aware and not value_is_aware:
        return value.replace(tzinfo=timezone.utc)
    if not reference_is_aware and value_is_aware:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _amount_to_cents(value: Decimal | int | float | None) -> int:
    if value is None:
        return 0
    if not isinstance(value, Decimal):
        value = Decimal(value)
    return int((value * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _get_shift_or_404(db: Session, shift_id: uuid.UUID) -> models.Shift:
    shift = db.query(models.Shift).filter(models.Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
    return shift


def _resolve_window_end(shift: models.Shift, generated_at: datetime) -> datetime:
    if shift.closed_at and shift.closed_at < generated_at:
        return shift.closed_at
    return generated_at


def _get_mismatch_count(db: Session, shift: models.Shift, window_end: datetime) -> int:
    count = (
        db.query(func.count(models.AuditLog.log_id))
        .filter(
            models.AuditLog.action == "late_sync_mismatch",
            models.AuditLog.timestamp >= shift.opened_at,
            models.AuditLog.timestamp <= window_end,
        )
        .scalar()
    )
    return int(count or 0)


def build_shift_report_payload(
    db: Session,
    *,
    shift: models.Shift,
    report_type: str,
    generated_at: datetime | None = None,
) -> schemas.ShiftReportPayload:
    generated_at = generated_at or datetime.now(timezone.utc)
    generated_at = _align_datetime_to_reference(generated_at, shift.opened_at)
    window_end = _resolve_window_end(shift=shift, generated_at=generated_at)

    totals_row = (
        db.query(
            func.count(models.Pour.pour_id).label("pours_count"),
            func.coalesce(func.sum(models.Pour.volume_ml), 0).label("total_volume_ml"),
            func.coalesce(func.sum(models.Pour.amount_charged), 0).label("total_amount"),
            func.coalesce(
                func.sum(case((models.Pour.sync_status == "pending_sync", 1), else_=0)),
                0,
            ).label("pending_sync_count"),
            func.coalesce(
                func.sum(case((models.Pour.sync_status == "reconciled", 1), else_=0)),
                0,
            ).label("reconciled_count"),
        )
        .filter(
            models.Pour.poured_at >= shift.opened_at,
            models.Pour.poured_at <= window_end,
        )
        .one()
    )

    by_tap_rows = (
        db.query(
            models.Pour.tap_id.label("tap_id"),
            func.count(models.Pour.pour_id).label("pours_count"),
            func.coalesce(func.sum(models.Pour.volume_ml), 0).label("volume_ml"),
            func.coalesce(func.sum(models.Pour.amount_charged), 0).label("amount_total"),
            func.coalesce(
                func.sum(case((models.Pour.sync_status == "pending_sync", 1), else_=0)),
                0,
            ).label("pending_sync_count"),
        )
        .filter(
            models.Pour.poured_at >= shift.opened_at,
            models.Pour.poured_at <= window_end,
        )
        .group_by(models.Pour.tap_id)
        .order_by(models.Pour.tap_id.asc())
        .all()
    )

    visits_row = (
        db.query(
            func.coalesce(func.sum(case((models.Visit.status == "active", 1), else_=0)), 0).label(
                "active_visits_count"
            ),
            func.coalesce(func.sum(case((models.Visit.status == "closed", 1), else_=0)), 0).label(
                "closed_visits_count"
            ),
        )
        .filter(
            models.Visit.opened_at >= shift.opened_at,
            models.Visit.opened_at <= window_end,
        )
        .one()
    )

    mismatch_count = _get_mismatch_count(db=db, shift=shift, window_end=window_end)

    payload = schemas.ShiftReportPayload(
        meta=schemas.ShiftReportMeta(
            shift_id=shift.id,
            report_type="Z" if report_type == "Z" else "X",
            generated_at=generated_at,
            opened_at=shift.opened_at,
            closed_at=shift.closed_at,
        ),
        totals=schemas.ShiftReportTotals(
            pours_count=int(totals_row.pours_count or 0),
            total_volume_ml=int(totals_row.total_volume_ml or 0),
            total_amount_cents=_amount_to_cents(totals_row.total_amount),
            pending_sync_count=int(totals_row.pending_sync_count or 0),
            reconciled_count=int(totals_row.reconciled_count or 0),
            mismatch_count=mismatch_count,
        ),
        by_tap=[
            schemas.ShiftReportByTapItem(
                tap_id=int(row.tap_id),
                pours_count=int(row.pours_count or 0),
                volume_ml=int(row.volume_ml or 0),
                amount_cents=_amount_to_cents(row.amount_total),
                pending_sync_count=int(row.pending_sync_count or 0),
            )
            for row in by_tap_rows
        ],
        visits=schemas.ShiftReportVisits(
            active_visits_count=int(visits_row.active_visits_count or 0),
            closed_visits_count=int(visits_row.closed_visits_count or 0),
        ),
        kegs=schemas.ShiftReportKegs(
            status="not_available_yet",
            note=KEG_PLACEHOLDER_NOTE,
        ),
    )
    return payload


def get_x_report_for_shift(db: Session, shift_id: uuid.UUID) -> schemas.ShiftReportPayload:
    shift = _get_shift_or_404(db=db, shift_id=shift_id)
    return build_shift_report_payload(db=db, shift=shift, report_type="X")


def _to_document_schema(db_report: models.ShiftReport) -> schemas.ShiftReportDocument:
    payload = schemas.ShiftReportPayload.model_validate(db_report.payload)
    return schemas.ShiftReportDocument(
        report_id=db_report.report_id,
        shift_id=db_report.shift_id,
        report_type="Z",
        generated_at=db_report.generated_at,
        payload=payload,
    )


def create_or_get_z_report(db: Session, shift_id: uuid.UUID) -> schemas.ShiftReportDocument:
    shift = _get_shift_or_404(db=db, shift_id=shift_id)
    if shift.status != "closed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shift must be closed for Z report",
        )

    existing = (
        db.query(models.ShiftReport)
        .filter(
            models.ShiftReport.shift_id == shift_id,
            models.ShiftReport.report_type == "Z",
        )
        .first()
    )
    if existing:
        return _to_document_schema(existing)

    generated_at = datetime.now(timezone.utc)
    payload = build_shift_report_payload(
        db=db,
        shift=shift,
        report_type="Z",
        generated_at=generated_at,
    )
    db_report = models.ShiftReport(
        shift_id=shift_id,
        report_type="Z",
        generated_at=generated_at,
        payload=payload.model_dump(mode="json"),
    )
    db.add(db_report)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(models.ShiftReport)
            .filter(
                models.ShiftReport.shift_id == shift_id,
                models.ShiftReport.report_type == "Z",
            )
            .first()
        )
        if existing:
            return _to_document_schema(existing)
        raise

    db.refresh(db_report)
    return _to_document_schema(db_report)


def get_z_report(db: Session, shift_id: uuid.UUID) -> schemas.ShiftReportDocument:
    _get_shift_or_404(db=db, shift_id=shift_id)
    db_report = (
        db.query(models.ShiftReport)
        .filter(
            models.ShiftReport.shift_id == shift_id,
            models.ShiftReport.report_type == "Z",
        )
        .first()
    )
    if not db_report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Z report not found")
    return _to_document_schema(db_report)


def list_z_reports_by_date(db: Session, *, from_date: date, to_date: date) -> list[schemas.ShiftZReportListItem]:
    if from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'from' must be less than or equal to 'to'",
        )

    sample = db.query(models.ShiftReport.generated_at).order_by(models.ShiftReport.generated_at.desc()).first()
    reference_dt = sample[0] if sample else datetime.now(timezone.utc)

    from_dt = _align_datetime_to_reference(
        datetime.combine(from_date, time.min, tzinfo=timezone.utc),
        reference_dt,
    )
    to_dt_exclusive = _align_datetime_to_reference(
        datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=timezone.utc),
        reference_dt,
    )

    db_reports = (
        db.query(models.ShiftReport)
        .filter(
            models.ShiftReport.report_type == "Z",
            models.ShiftReport.generated_at >= from_dt,
            models.ShiftReport.generated_at < to_dt_exclusive,
        )
        .order_by(models.ShiftReport.generated_at.desc())
        .all()
    )

    items: list[schemas.ShiftZReportListItem] = []
    for report in db_reports:
        totals = (report.payload or {}).get("totals", {})
        visits = (report.payload or {}).get("visits", {})
        items.append(
            schemas.ShiftZReportListItem(
                report_id=report.report_id,
                shift_id=report.shift_id,
                generated_at=report.generated_at,
                total_volume_ml=int(totals.get("total_volume_ml", 0) or 0),
                total_amount_cents=int(totals.get("total_amount_cents", 0) or 0),
                pours_count=int(totals.get("pours_count", 0) or 0),
                active_visits_count=int(visits.get("active_visits_count", 0) or 0),
                closed_visits_count=int(visits.get("closed_visits_count", 0) or 0),
            )
        )
    return items
