import time
import uuid
from datetime import datetime, timezone
from config import PRICE_PER_100ML_CENTS, TAP_ID
import logging

class FlowManager:
    def __init__(self, hardware, db_handler, sync_manager):
        self.hardware = hardware
        self.db_handler = db_handler
        self.sync_manager = sync_manager

    def process(self):
        # Состояние ожидания
        if not self.hardware.is_card_present():
            return

        # Авторизация
        card_uid = self.hardware.get_card_uid()
        if not card_uid:
            return

        logging.info(f"Авторизация карты {card_uid}...")

        if not self.sync_manager.check_card_auth(card_uid):
            logging.info(f"КАРТА {card_uid} НЕ ЗАРЕГИСТРИРОВАНА. ДОСТУП ЗАПРЕЩЕН")
            while self.hardware.is_card_present():
                time.sleep(0.5)
            return

        if self.sync_manager.check_emergency_stop():
            while self.hardware.is_card_present():
                time.sleep(0.5)
            return

        # Налив (Активная сессия)
        self.hardware.valve_open()
        logging.info("КЛАПАН ОТКРЫТ")
        start_ts = datetime.now(timezone.utc).isoformat()
        total_volume_ml = 0
        last_volume_ml = 0
        timeout_counter = 0
        client_tx_id = str(uuid.uuid4())

        try:
            while self.hardware.is_card_present():
                if self.sync_manager.check_emergency_stop():
                    logging.info("Emergency stop активирован. Закрытие клапана.")
                    break

                current_volume_ml = int(self.hardware.get_volume_liters() * 1000)
                if current_volume_ml > last_volume_ml:
                    total_volume_ml = current_volume_ml
                    last_volume_ml = current_volume_ml
                    timeout_counter = 0
                else:
                    timeout_counter += 1

                if timeout_counter >= 30:  # 15 секунд (30 итераций по 0.5 сек)
                    logging.info("КЛАПАН ЗАКРЫТ (ТАЙМАУТ)")
                    break

                time.sleep(0.5)
        finally:
            self.hardware.valve_close()
            logging.info("КЛАПАН ЗАКРЫТ (КАРТА УБРАНА)")
            logging.info(f"Сессия завершена. Налито: {total_volume_ml} мл")

        # Завершение
        if total_volume_ml > 1:  # Минимальный объем 1 мл
            end_ts = datetime.now(timezone.utc).isoformat()
            price_cents = int((total_volume_ml / 100.0) * PRICE_PER_100ML_CENTS)
            pour_data = {
                "client_tx_id": client_tx_id,
                "card_uid": card_uid,
                "tap_id": TAP_ID,
                "start_ts": start_ts,
                "end_ts": end_ts,
                "volume_ml": total_volume_ml,
                "price_cents": price_cents
            }
            self.db_handler.add_pour(pour_data)
            logging.info("ЗАПИСЬ В БД: УСПЕХ")

        self.hardware.reset_pulses()

        # Ожидание удаления карты
        while self.hardware.is_card_present():
            time.sleep(0.5)