#!/usr/bin/env python3
import argparse

from crud import card_crud, shift_crud, visit_crud
from database import SessionLocal
import models
import schemas


SCRIPT_ACTOR = "dev_db_cleanup"
DEFAULT_POOL_CARD_UIDS = (
    "dev-pool-001",
    "dev-pool-002",
    "dev-pool-003",
)


def _pending_sync_count_for_visit(db, visit_id) -> int:
    return (
        db.query(models.Pour.pour_id)
        .filter(
            models.Pour.visit_id == visit_id,
            models.Pour.sync_status == "pending_sync",
            models.Pour.is_manual_reconcile.is_(False),
        )
        .count()
    )


def _has_active_lock_for_tap(db, tap_id: int) -> bool:
    return (
        db.query(models.Visit.visit_id)
        .filter(
            models.Visit.status == "active",
            models.Visit.active_tap_id == tap_id,
        )
        .first()
        is not None
    )


def _has_pending_sync_for_tap(db, tap_id: int) -> bool:
    return (
        db.query(models.Pour.pour_id)
        .filter(
            models.Pour.tap_id == tap_id,
            models.Pour.sync_status == "pending_sync",
            models.Pour.is_manual_reconcile.is_(False),
        )
        .first()
        is not None
    )


def _print_summary(db) -> None:
    active_visits = (
        db.query(models.Visit)
        .filter(models.Visit.status == "active")
        .order_by(models.Visit.opened_at.asc())
        .all()
    )
    issuable_cards = (
        db.query(models.Card.card_uid)
        .filter(
            models.Card.status.in_(
                [card_crud.CARD_STATUS_AVAILABLE, card_crud.CARD_STATUS_RETURNED]
            )
        )
        .count()
    )
    lost_cards = (
        db.query(models.Card.card_uid)
        .filter(models.Card.status == card_crud.CARD_STATUS_LOST)
        .count()
    )
    pending_sync = (
        db.query(models.Pour.pour_id)
        .filter(
            models.Pour.sync_status == "pending_sync",
            models.Pour.is_manual_reconcile.is_(False),
        )
        .count()
    )
    processing_sync_taps = (
        db.query(models.Tap.tap_id)
        .filter(models.Tap.status == "processing_sync")
        .count()
    )
    open_shift = shift_crud.get_open_shift(db)

    print("")
    print("Summary")
    print(f"- open_shift: {'yes' if open_shift else 'no'}")
    print(f"- active_visits: {len(active_visits)}")
    print(f"- issuable_cards: {issuable_cards}")
    print(f"- lost_cards: {lost_cards}")
    print(f"- pending_sync_pours: {pending_sync}")
    print(f"- processing_sync_taps: {processing_sync_taps}")

    if active_visits:
        print("- active_visit_details:")
        for visit in active_visits:
            guest = visit.guest
            guest_label = (
                f"{guest.last_name} {guest.first_name}".strip()
                if guest
                else str(visit.guest_id)
            )
            print(
                f"  * {visit.visit_id} | guest={guest_label} | card={visit.card_uid} | "
                f"operational_status={visit.operational_status} | tap={visit.active_tap_id or '-'}"
            )


def _ensure_open_shift(db, *, dry_run: bool) -> None:
    open_shift = shift_crud.get_open_shift(db)
    if open_shift:
        print(f"[ok] shift already open: {open_shift.id}")
        return
    if dry_run:
        print("[plan] would open a new shift")
        return
    opened = shift_crud.open_shift(db, opened_by=SCRIPT_ACTOR)
    print(f"[done] opened shift: {opened.id}")


def _close_blocked_lost_visits(db, *, dry_run: bool) -> None:
    blocked_visits = (
        db.query(models.Visit)
        .filter(
            models.Visit.status == "active",
            models.Visit.operational_status == visit_crud.VISIT_OP_ACTIVE_BLOCKED_LOST,
        )
        .order_by(models.Visit.opened_at.asc())
        .all()
    )

    if not blocked_visits:
        print("[ok] no blocked-lost active visits found")
        return

    for visit in blocked_visits:
        pending_sync = _pending_sync_count_for_visit(db, visit.visit_id)
        if pending_sync:
            print(
                f"[skip] blocked visit {visit.visit_id} still has {pending_sync} pending_sync pour(s)"
            )
            continue
        if dry_run:
            print(f"[plan] would service-close blocked visit {visit.visit_id}")
            continue
        visit_crud.service_close_missing_card(
            db=db,
            visit_id=visit.visit_id,
            closed_reason="service_close_missing_card",
            reason_code="dev_cleanup_blocked_lost_visit",
            comment="Closed by dev DB cleanup script",
            actor_id=SCRIPT_ACTOR,
        )
        print(f"[done] service-closed blocked visit {visit.visit_id}")


def _repair_orphan_processing_sync_taps(db, *, dry_run: bool) -> None:
    taps = (
        db.query(models.Tap)
        .filter(models.Tap.status == "processing_sync")
        .order_by(models.Tap.tap_id.asc())
        .all()
    )

    if not taps:
        print("[ok] no taps in processing_sync")
        return

    changed = False
    for tap in taps:
        has_active_lock = _has_active_lock_for_tap(db, tap.tap_id)
        has_pending_sync = _has_pending_sync_for_tap(db, tap.tap_id)
        if has_active_lock or has_pending_sync:
            print(
                f"[skip] tap {tap.tap_id} kept in processing_sync "
                f"(active_lock={has_active_lock}, pending_sync={has_pending_sync})"
            )
            continue
        if dry_run:
            print(f"[plan] would reset tap {tap.tap_id} from processing_sync to active")
            continue
        tap.status = "active"
        changed = True
        print(f"[done] reset tap {tap.tap_id} from processing_sync to active")

    if changed:
        db.commit()


def _ensure_pool_cards(db, *, dry_run: bool, card_uids: list[str]) -> None:
    for raw_uid in card_uids:
        normalized_uid = card_crud.normalize_card_uid(raw_uid)
        card = card_crud.get_card_by_uid(db, normalized_uid)
        if card is None:
            if dry_run:
                print(f"[plan] would create pool card {normalized_uid}")
                continue
            created = card_crud.create_card(db, schemas.CardCreate(card_uid=normalized_uid))
            print(f"[done] created pool card {created.card_uid} with status {created.status}")
            continue

        if card.status in {
            card_crud.CARD_STATUS_AVAILABLE,
            card_crud.CARD_STATUS_RETURNED,
        } and card.guest_id is None:
            print(f"[ok] pool card ready: {card.card_uid} ({card.status})")
            continue

        print(
            f"[skip] card {card.card_uid} left as-is "
            f"(status={card.status}, guest_id={card.guest_id or '-'})"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sanitize the local dev database for manual testing."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned changes without writing to the database.",
    )
    parser.add_argument(
        "--card",
        action="append",
        dest="card_uids",
        default=[],
        help="Ensure a pool card with this UID exists. Can be provided multiple times.",
    )
    args = parser.parse_args()

    target_card_uids = args.card_uids or list(DEFAULT_POOL_CARD_UIDS)

    db = SessionLocal()
    try:
        print("Dev DB cleanup started")
        print(f"- dry_run: {'yes' if args.dry_run else 'no'}")
        print(f"- ensure_cards: {', '.join(target_card_uids)}")

        _ensure_open_shift(db, dry_run=args.dry_run)
        _close_blocked_lost_visits(db, dry_run=args.dry_run)
        _repair_orphan_processing_sync_taps(db, dry_run=args.dry_run)
        _ensure_pool_cards(db, dry_run=args.dry_run, card_uids=target_card_uids)

        _print_summary(db)
        print("")
        print("Dev DB cleanup finished")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
