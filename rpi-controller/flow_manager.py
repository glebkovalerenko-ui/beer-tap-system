import logging
import time
import uuid
from datetime import datetime, timezone

from config import PRICE_PER_100ML_CENTS, TAP_ID


class FlowManager:
    def __init__(self, hardware, db_handler, sync_manager):
        self.hardware = hardware
        self.db_handler = db_handler
        self.sync_manager = sync_manager

    def process(self):
        if self.db_handler.has_unsynced_for_tap(TAP_ID):
            logging.info("Tap is in processing_sync: unsynced pour exists, blocking new pour start.")
            return

        if not self.hardware.is_card_present():
            return

        card_uid = self.hardware.get_card_uid()
        if not card_uid:
            return

        card_uid = card_uid.replace(" ", "").lower()
        logging.info(f"Authorizing card {card_uid}...")

        if not self.sync_manager.check_card_auth(card_uid):
            logging.info(f"Card {card_uid} is not authorized")
            while self.hardware.is_card_present():
                time.sleep(0.5)
            return

        self.hardware.valve_open()
        logging.info("Valve opened")
        start_ts = datetime.now(timezone.utc).isoformat()
        total_volume_ml = 0
        last_volume_ml = 0
        timeout_counter = 0
        emergency_check_counter = 0
        client_tx_id = str(uuid.uuid4())
        short_id = client_tx_id.replace("-", "")[:8].upper()
        card_removed_by_timeout = False

        try:
            while self.hardware.is_card_present():
                emergency_check_counter += 1

                if emergency_check_counter >= 6:
                    if self.sync_manager.check_emergency_stop():
                        logging.info("Emergency stop is enabled. Closing valve.")
                        break
                    emergency_check_counter = 0

                current_volume_ml = int(self.hardware.get_volume_liters() * 1000)
                if current_volume_ml > last_volume_ml:
                    total_volume_ml = current_volume_ml
                    last_volume_ml = current_volume_ml
                    timeout_counter = 0
                else:
                    timeout_counter += 1

                if timeout_counter >= 30:
                    logging.info("Valve closed by timeout")
                    card_removed_by_timeout = True
                    timeout_price_cents = int((total_volume_ml / 100.0) * PRICE_PER_100ML_CENTS)
                    logging.info(
                        f"Timeout details: short_id={short_id}, volume_ml={total_volume_ml}, cost_cents={timeout_price_cents}"
                    )
                    break

                time.sleep(0.5)
        finally:
            self.hardware.valve_close()
            if not card_removed_by_timeout:
                logging.info("Valve closed (card removed)")
            logging.info(f"Session finished. Poured: {total_volume_ml} ml")

        if total_volume_ml > 1:
            end_ts = datetime.now(timezone.utc).isoformat()
            price_cents = int((total_volume_ml / 100.0) * PRICE_PER_100ML_CENTS)
            pour_data = {
                "client_tx_id": client_tx_id,
                "short_id": short_id,
                "card_uid": card_uid,
                "tap_id": TAP_ID,
                "start_ts": start_ts,
                "end_ts": end_ts,
                "volume_ml": total_volume_ml,
                "price_cents": price_cents,
                "price_per_ml_at_pour": float(PRICE_PER_100ML_CENTS / 100.0),
            }
            self.db_handler.add_pour(pour_data)
            logging.info("Pour record added to local DB")

        self.hardware.reset_pulses()

        while self.hardware.is_card_present():
            time.sleep(0.5)
