from pour_session import calculate_price_cents, has_reached_pour_limit


def test_calculate_price_cents_uses_authorized_price():
    assert calculate_price_cents(30, 50) == 1500
    assert calculate_price_cents(0, 50) == 0


def test_has_reached_pour_limit_clamps_at_or_above_limit():
    assert has_reached_pour_limit(20, 20) is True
    assert has_reached_pour_limit(21, 20) is True
    assert has_reached_pour_limit(19, 20) is False
