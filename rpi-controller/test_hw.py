from hardware import HardwareHandler
import time

def main():
    hw = HardwareHandler()

    try:
        while True:
            card_present = hw.is_card_present()
            card_uid = hw.get_card_uid() if card_present else "No card"
            volume = hw.get_volume_liters()

            print(f"Card Present: {card_present}, Card UID: {card_uid}, Volume (L): {volume}")

            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()