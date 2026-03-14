import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from config import DISPLAY_RUNTIME_PATH, TAP_ID


class DisplayRuntimePublisher:
    def __init__(self, *, tap_id: int = TAP_ID, output_path: str = DISPLAY_RUNTIME_PATH):
        self.tap_id = tap_id
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def publish(
        self,
        *,
        phase: str,
        reason_code: str | None = None,
        card_present: bool = False,
        guest_first_name: str | None = None,
        balance_cents_at_authorize: int | None = None,
        price_per_ml_cents: int | None = None,
        max_volume_ml: int | None = None,
        current_volume_ml: int = 0,
        current_cost_cents: int = 0,
        projected_remaining_balance_cents: int | None = None,
        session_short_id: str | None = None,
    ) -> dict:
        snapshot = {
            "schema_version": 1,
            "tap_id": self.tap_id,
            "phase": phase,
            "reason_code": reason_code,
            "card_present": bool(card_present),
            "guest_first_name": guest_first_name,
            "balance_cents_at_authorize": balance_cents_at_authorize,
            "price_per_ml_cents": price_per_ml_cents,
            "max_volume_ml": max_volume_ml,
            "current_volume_ml": int(current_volume_ml or 0),
            "current_cost_cents": int(current_cost_cents or 0),
            "projected_remaining_balance_cents": projected_remaining_balance_cents,
            "session_short_id": session_short_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        serialized = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(self.output_path.parent),
            delete=False,
        ) as temp_file:
            temp_file.write(serialized)
            temp_path = Path(temp_file.name)

        os.replace(temp_path, self.output_path)
        return snapshot
