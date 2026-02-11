from gpiozero import DigitalInputDevice, OutputDevice
from threading import Lock
import time
from config import PIN_RELAY, PIN_FLOW_SENSOR, FLOW_SENSOR_K_FACTOR
from smartcard.System import readers
from smartcard.util import toHexString

class HardwareHandler:
    def __init__(self):
        # Инициализация реле и датчика потока
        self.relay = OutputDevice(PIN_RELAY)
        self.flow_sensor = DigitalInputDevice(PIN_FLOW_SENSOR)

        # Переменные для подсчета импульсов
        self.pulse_count = 0
        self.lock = Lock()

        # Установка обработчика прерываний для датчика потока
        self.flow_sensor.when_activated = self._pulse_detected

    def _pulse_detected(self):
        with self.lock:
            self.pulse_count += 1

    def is_card_present(self):
        r = readers()
        if not r:
            return False
        connection = r[0].createConnection()
        try:
            connection.connect()
            return True
        except Exception:
            return False

    def get_card_uid(self):
        r = readers()
        if not r:
            return None
        connection = r[0].createConnection()
        try:
            connection.connect()
            apdu = [0xFF, 0xCA, 0x00, 0x00, 0x00]  # Команда для получения UID
            response, sw1, sw2 = connection.transmit(apdu)
            if sw1 == 0x90 and sw2 == 0x00:
                return toHexString(response)
        except Exception:
            pass
        return None

    def valve_open(self):
        self.relay.on()

    def valve_close(self):
        self.relay.off()

    def get_volume_liters(self):
        with self.lock:
            pulses = self.pulse_count
            self.pulse_count = 0
        # Расчет объема в литрах
        return (pulses / FLOW_SENSOR_K_FACTOR) / 1000