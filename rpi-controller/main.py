import threading
import time
import logging
from hardware import HardwareHandler
from database import DatabaseHandler
from sync_manager import SyncManager
from flow_manager import FlowManager

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Инициализация компонентов
    db_handler = DatabaseHandler()
    hardware = HardwareHandler()
    sync_manager = SyncManager()
    flow_manager = FlowManager(hardware, db_handler, sync_manager)

    # Запуск фонового потока для синхронизации
    sync_thread = threading.Thread(target=sync_manager.sync_cycle, args=(db_handler,), daemon=True)
    sync_thread.start()

    try:
        # Основной цикл
        while True:
            flow_manager.process()
            time.sleep(0.1)  # Задержка между итерациями
    except KeyboardInterrupt:
        print("\nЗавершение работы...")
    finally:
        # Закрытие клапана перед выходом
        hardware.valve_close()
        print("Клапан закрыт. Программа завершена.")

if __name__ == "__main__":
    main()