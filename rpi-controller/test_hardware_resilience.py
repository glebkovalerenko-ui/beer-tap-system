import importlib
import sys
import types


class DummyLGPIOFactory:
    pass


class DummyDevice:
    pin_factory = None


class DummyOutputDevice:
    def __init__(self, *_args, **_kwargs):
        self.is_active = False

    def on(self):
        self.is_active = True

    def off(self):
        self.is_active = False


class DummyInputDevice:
    def __init__(self, *_args, **_kwargs):
        self.when_activated = None


sys.modules.setdefault("gpiozero", types.ModuleType("gpiozero"))
sys.modules["gpiozero"].Device = DummyDevice
sys.modules["gpiozero"].DigitalInputDevice = DummyInputDevice
sys.modules["gpiozero"].OutputDevice = DummyOutputDevice
sys.modules.setdefault("gpiozero.pins", types.ModuleType("gpiozero.pins"))
sys.modules["gpiozero.pins.lgpio"] = types.SimpleNamespace(LGPIOFactory=DummyLGPIOFactory)
sys.modules.setdefault("smartcard", types.ModuleType("smartcard"))
sys.modules["smartcard.System"] = types.SimpleNamespace(readers=lambda: [])
sys.modules["smartcard.util"] = types.SimpleNamespace(toHexString=lambda response: " ".join(response))

hardware = importlib.import_module("hardware")


def test_is_card_present_returns_false_when_reader_enumeration_raises(monkeypatch):
    monkeypatch.setattr(hardware, "readers", lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    handler = hardware.HardwareHandler()

    assert handler.is_card_present() is False


def test_get_card_uid_returns_none_when_reader_enumeration_raises(monkeypatch):
    monkeypatch.setattr(hardware, "readers", lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    handler = hardware.HardwareHandler()

    assert handler.get_card_uid() is None
