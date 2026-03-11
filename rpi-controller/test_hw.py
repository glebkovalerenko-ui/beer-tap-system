import time

import pytest

pytest.importorskip("gpiozero")
pytest.importorskip("smartcard")

from hardware import HardwareHandler

def main():
    hw = HardwareHandler()

    try:
        while True:
            card_present = hw.is_card_present()
            card_uid = hw.get_card_uid() if card_present else "карта отсутствует"
            volume = hw.get_volume_liters()

            print(f"Карта вставлена: {card_present}, UID карты: {card_uid}, объем (л): {volume}")

            time.sleep(1)
    except KeyboardInterrupt:
        print("\nЗавершение проверки...")

if __name__ == "__main__":
    main()
