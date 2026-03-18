import logging
import time
from threading import Lock

from gpiozero import Device
from gpiozero import DigitalInputDevice, OutputDevice
from gpiozero.pins.lgpio import LGPIOFactory
from smartcard.System import readers
from smartcard.util import toHexString

from config import FLOW_SENSOR_K_FACTOR, PIN_FLOW_SENSOR, PIN_RELAY


Device.pin_factory = LGPIOFactory()


class HardwareHandler:
    PCSC_ERROR_LOG_INTERVAL_SECONDS = 5.0

    def __init__(self):
        self.relay = OutputDevice(PIN_RELAY)
        self.flow_sensor = DigitalInputDevice(PIN_FLOW_SENSOR)
        self.pulse_count = 0
        self.lock = Lock()
        self._last_pcsc_error_logged_at = 0.0
        self.flow_sensor.when_activated = self._pulse_detected

    def _pulse_detected(self):
        with self.lock:
            self.pulse_count += 1

    def _log_pcsc_error(self, action, exc):
        now = time.monotonic()
        if now - self._last_pcsc_error_logged_at < self.PCSC_ERROR_LOG_INTERVAL_SECONDS:
            return
        self._last_pcsc_error_logged_at = now
        logging.warning("PC/SC unavailable during %s: %s", action, exc)

    def _create_card_connection(self):
        try:
            available_readers = readers()
        except Exception as exc:
            self._log_pcsc_error("reader enumeration", exc)
            return None
        if not available_readers:
            return None
        try:
            return available_readers[0].createConnection()
        except Exception as exc:
            self._log_pcsc_error("reader connection setup", exc)
            return None

    def is_card_present(self):
        connection = self._create_card_connection()
        if not connection:
            return False
        try:
            connection.connect()
            return True
        except Exception:
            return False

    def get_card_uid(self):
        connection = self._create_card_connection()
        if not connection:
            return None
        try:
            connection.connect()
            apdu = [0xFF, 0xCA, 0x00, 0x00, 0x00]
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
        return (pulses / FLOW_SENSOR_K_FACTOR) / 1000

    def reset_pulses(self):
        with self.lock:
            self.pulse_count = 0
