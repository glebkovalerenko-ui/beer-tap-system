from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP


BALANCE_CENTS_SCALE = Decimal("100")
ML_PER_LITER = Decimal("1000")


@dataclass(frozen=True)
class PourPolicy:
    min_start_ml: int
    safety_ml: int
    allowed_overdraft_cents: int


def balance_to_cents(balance: Decimal) -> int:
    normalized = (Decimal(balance) * BALANCE_CENTS_SCALE).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(normalized)


def sell_price_per_liter_to_price_per_ml(balance_price_per_liter: Decimal) -> Decimal:
    return (Decimal(balance_price_per_liter) / ML_PER_LITER).quantize(Decimal("0.0001"))


def sell_price_per_liter_to_price_per_ml_cents(balance_price_per_liter: Decimal) -> int:
    price_cents_per_liter = Decimal(balance_price_per_liter) * BALANCE_CENTS_SCALE
    if price_cents_per_liter <= 0:
        raise ValueError("sell_price_per_liter must be positive")
    price_cents_per_ml = (price_cents_per_liter / ML_PER_LITER).quantize(Decimal("1"), rounding=ROUND_CEILING)
    return max(int(price_cents_per_ml), 1)


def required_cents_for_volume(volume_ml: int, price_per_ml_cents: int) -> int:
    return max(int(volume_ml), 0) * max(int(price_per_ml_cents), 0)


def calculate_max_volume_ml(
    *,
    balance_cents: int,
    allowed_overdraft_cents: int,
    price_per_ml_cents: int,
    safety_ml: int,
) -> int:
    if price_per_ml_cents <= 0:
        return 0
    gross_ml = (
        Decimal(balance_cents + allowed_overdraft_cents) / Decimal(price_per_ml_cents)
    ).quantize(Decimal("1"), rounding=ROUND_FLOOR)
    return max(int(gross_ml) - max(safety_ml, 0), 0)
