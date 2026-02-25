import logging
import threading
import time

from config import SYNC_INTERVAL_SECONDS
from database import DatabaseHandler
from flow_manager import FlowManager
from hardware import HardwareHandler
from sync_manager import SyncManager


def start_sync_worker(db, sync_manager):
    while True:
        sync_manager.sync_cycle(db)
        time.sleep(SYNC_INTERVAL_SECONDS)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    db_handler = DatabaseHandler()
    hardware = HardwareHandler()
    sync_manager = SyncManager()
    flow_manager = FlowManager(hardware, db_handler, sync_manager)

    threading.Thread(target=start_sync_worker, args=(db_handler, sync_manager), daemon=True).start()

    try:
        while True:
            flow_manager.process()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    finally:
        hardware.valve_close()
        print("Valve closed. Controller stopped.")


if __name__ == "__main__":
    main()
