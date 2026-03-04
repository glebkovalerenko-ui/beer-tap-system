import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol

from sqlalchemy.orm import Session

import models


POS_STUB_PREFIX = "[POS_STUB]"
POS_STUB_SOURCE = "stub"

logger = logging.getLogger("m7.pos_stub")


def _decimal_to_cents(amount: Decimal | None) -> int | None:
    if amount is None:
        return None
    return int((amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _timestamp_to_iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat()


class POSAdapter(Protocol):
    def notify_topup(self, db: Session, *, transaction: models.Transaction, guest: models.Guest) -> None:
        ...

    def notify_refund(self, db: Session, *, transaction: models.Transaction, guest: models.Guest) -> None:
        ...

    def notify_pour(self, db: Session, *, pour: models.Pour, guest: models.Guest | None = None) -> None:
        ...


class StubPOSAdapter:
    def _emit_event(
        self,
        db: Session,
        *,
        action: str,
        target_entity: str,
        target_id: str,
        payload: dict,
    ) -> None:
        existing = (
            db.query(models.AuditLog.log_id)
            .filter(
                models.AuditLog.action == action,
                models.AuditLog.target_id == target_id,
            )
            .first()
        )
        if existing:
            return

        db.add(
            models.AuditLog(
                actor_id=POS_STUB_SOURCE,
                action=action,
                target_entity=target_entity,
                target_id=target_id,
                details=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            )
        )
        logger.info("%s %s", POS_STUB_PREFIX, json.dumps(payload, ensure_ascii=False, sort_keys=True))

    def notify_topup(self, db: Session, *, transaction: models.Transaction, guest: models.Guest) -> None:
        payload = {
            "event_type": "topup",
            "event_id": str(transaction.transaction_id),
            "guest_id": str(transaction.guest_id),
            "visit_id": str(transaction.visit_id) if transaction.visit_id else None,
            "amount_cents": _decimal_to_cents(transaction.amount),
            "volume_ml": None,
            "timestamp_db": _timestamp_to_iso(transaction.created_at),
            "payment_method": transaction.payment_method,
            "source": POS_STUB_SOURCE,
        }
        self._emit_event(
            db,
            action="pos_stub_topup_notified",
            target_entity="Transaction",
            target_id=str(transaction.transaction_id),
            payload=payload,
        )

    def notify_refund(self, db: Session, *, transaction: models.Transaction, guest: models.Guest) -> None:
        payload = {
            "event_type": "refund",
            "event_id": str(transaction.transaction_id),
            "guest_id": str(transaction.guest_id),
            "visit_id": str(transaction.visit_id) if transaction.visit_id else None,
            "amount_cents": _decimal_to_cents(transaction.amount),
            "volume_ml": None,
            "timestamp_db": _timestamp_to_iso(transaction.created_at),
            "payment_method": transaction.payment_method,
            "source": POS_STUB_SOURCE,
        }
        self._emit_event(
            db,
            action="pos_stub_refund_notified",
            target_entity="Transaction",
            target_id=str(transaction.transaction_id),
            payload=payload,
        )

    def notify_pour(self, db: Session, *, pour: models.Pour, guest: models.Guest | None = None) -> None:
        guest_id = guest.guest_id if guest else pour.guest_id
        timestamp_db = pour.reconciled_at or pour.synced_at or pour.poured_at
        payload = {
            "event_type": "pour",
            "event_id": str(pour.pour_id),
            "guest_id": str(guest_id) if guest_id else None,
            "visit_id": str(pour.visit_id) if pour.visit_id else None,
            "amount_cents": _decimal_to_cents(pour.amount_charged),
            "volume_ml": pour.volume_ml,
            "timestamp_db": _timestamp_to_iso(timestamp_db),
            "sync_status": pour.sync_status,
            "client_tx_id": pour.client_tx_id,
            "source": POS_STUB_SOURCE,
        }
        self._emit_event(
            db,
            action="pos_stub_pour_notified",
            target_entity="Pour",
            target_id=str(pour.pour_id),
            payload=payload,
        )


_adapter = StubPOSAdapter()


def get_pos_adapter() -> POSAdapter:
    return _adapter
