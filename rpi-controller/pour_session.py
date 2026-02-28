def calculate_price_cents(volume_ml: int, price_per_ml_cents: int) -> int:
    return max(int(volume_ml), 0) * max(int(price_per_ml_cents), 0)


def has_reached_pour_limit(poured_ml: int, max_volume_ml: int) -> bool:
    return max_volume_ml > 0 and poured_ml >= max_volume_ml
