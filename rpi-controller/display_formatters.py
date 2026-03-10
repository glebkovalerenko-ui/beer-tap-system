def format_money_minor_units(minor_units: int) -> str:
    value = max(int(minor_units or 0), 0)
    rubles = value / 100
    return f"{rubles:.2f}".replace(".", ",") + " ₽"


def format_volume(volume_ml: int) -> str:
    value = max(int(volume_ml or 0), 0)
    if value < 1000:
        return f"{value} мл"

    liters = value / 1000
    return f"{liters:.1f}".replace(".", ",") + " л"
