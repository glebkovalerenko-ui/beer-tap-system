import logging
import sys
import threading
import time

from config import SYNC_INTERVAL_SECONDS
from database import DatabaseHandler
from display_runtime import DisplayRuntimePublisher
from flow_manager import FlowManager
from hardware import HardwareHandler
from sync_manager import SyncManager


def start_sync_worker(db, sync_manager):
    while True:
        sync_manager.sync_cycle(db)
        time.sleep(SYNC_INTERVAL_SECONDS)


def main():
    for stream_name in ("stdout", "stderr"):
        reconfigure = getattr(getattr(sys, stream_name, None), "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    db_handler = DatabaseHandler()
    hardware = HardwareHandler()
    sync_manager = SyncManager()
    runtime_publisher = DisplayRuntimePublisher()
    sync_manager.log_startup_config()
    sync_manager.probe_backend()
    flow_manager = FlowManager(hardware, db_handler, sync_manager, runtime_publisher=runtime_publisher)

    threading.Thread(target=start_sync_worker, args=(db_handler, sync_manager), daemon=True).start()

    try:
        while True:
            flow_manager.process()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nПолучен сигнал остановки...")
    finally:
        hardware.valve_close()
        print("Клапан закрыт. Контроллер остановлен.")


if __name__ == "__main__":
    main()
