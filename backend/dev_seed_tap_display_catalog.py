#!/usr/bin/env python3
import argparse
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import joinedload

from database import SessionLocal
import models


SCRIPT_NAME = "dev_seed_tap_display_catalog"

BEVERAGE_FIXTURES = [
    {
        "name": "Иванушка",
        "legacy_names": ["Citra Flow IPA", "ШпаТест", "Иванушка"],
        "brewery": "Пивоварня Brewlok, Воронеж",
        "style": "Хеллес лагер",
        "abv": Decimal("5.2"),
        "sell_price_per_liter": Decimal("520.00"),
        "description_short": "Классический хеллес в баварском стиле: мягкий, чистый, питкий и с лёгкой горчинкой.",
        "ibu": None,
        "display_brand_name": "Брюлок",
        "accent_color": "#D9A441",
        "text_theme": "dark",
        "price_display_mode_default": "per_100ml",
        "keg": {
            "initial_volume_ml": 30000,
            "purchase_price": Decimal("4200.00"),
        },
    },
    {
        "name": "Кикимора",
        "legacy_names": ["Velvet Stout", "Кикимора"],
        "brewery": "Пивоварня Brewlok, Воронеж",
        "style": "Милк-стаут",
        "abv": Decimal("6.5"),
        "sell_price_per_liter": Decimal("590.00"),
        "description_short": "Лёгкий сливочный стаут с бархатистой сладостью, который мягко обволакивает вкус.",
        "ibu": None,
        "display_brand_name": "Брюлок",
        "accent_color": "#5B3427",
        "text_theme": "light",
        "price_display_mode_default": "per_100ml",
        "keg": {
            "initial_volume_ml": 30000,
            "purchase_price": Decimal("4600.00"),
        },
    },
    {
        "name": "Поздний завтрак",
        "legacy_names": ["Berry Orchard Cider", "Мельница на реке", "Поздний завтрак"],
        "brewery": "Пивоварня Jaws, Белоярский",
        "style": "Овсяный стаут",
        "abv": Decimal("5.2"),
        "sell_price_per_liter": Decimal("560.00"),
        "description_short": "Тёмный стаут с шоколадом и кофе во вкусе, а овёс делает его мягким и бархатистым.",
        "ibu": Decimal("23"),
        "display_brand_name": "Джоус",
        "accent_color": "#4B2E2B",
        "text_theme": "light",
        "price_display_mode_default": "per_100ml",
        "keg": {
            "initial_volume_ml": 30000,
            "purchase_price": Decimal("4100.00"),
        },
    },
    {
        "name": "Пикник у паба",
        "legacy_names": ["Bohemian Pils", "Наглецы из Воронежа Pils", "Пикник у паба"],
        "brewery": "Пивоварня Jaws, Белоярский",
        "style": "Пэйл эль",
        "abv": Decimal("5.2"),
        "sell_price_per_liter": Decimal("540.00"),
        "description_short": "Бисквитная солодовая база и аккуратная цветочно-древесная горчинка благородных хмелей.",
        "ibu": Decimal("25"),
        "display_brand_name": "Джоус",
        "accent_color": "#C97B2B",
        "text_theme": "dark",
        "price_display_mode_default": "per_100ml",
        "keg": {
            "initial_volume_ml": 30000,
            "purchase_price": Decimal("4300.00"),
        },
    },
    {
        "name": "Атомная Прачечная",
        "legacy_names": ["Mango Tide Sour", "Бархатное Традиционное", "Атомная Прачечная"],
        "brewery": "Пивоварня Jaws, Белоярский",
        "style": "Индийский пэйл эль",
        "abv": Decimal("7.0"),
        "sell_price_per_liter": Decimal("620.00"),
        "description_short": "Яркий IPA с тропическими фруктами, цитрусом, хвоей и мощной узнаваемой горечью.",
        "ibu": Decimal("101"),
        "display_brand_name": "Джоус",
        "accent_color": "#D86A1A",
        "text_theme": "dark",
        "price_display_mode_default": "per_100ml",
        "keg": {
            "initial_volume_ml": 30000,
            "purchase_price": Decimal("4700.00"),
        },
    },
]

PRIMARY_TAP_COPY = {
    "enabled": True,
    "idle_instruction": "Приложите карту гостя, чтобы начать налив",
    "fallback_title": "Кран №1 сейчас не наливает",
    "fallback_subtitle": (
        "На этот кран ещё не назначен напиток или кега уже закончилась. "
        "Бармен скоро подключит новый сорт."
    ),
    "maintenance_title": "Кран №1 временно на паузе",
    "maintenance_subtitle": (
        "Идёт промывка линии или кран временно заблокирован оператором. "
        "Пожалуйста, выберите другой кран или обратитесь к бармену."
    ),
    "override_accent_color": None,
    "show_price_mode": None,
}


def _get_primary_tap(db):
    return (
        db.query(models.Tap)
        .options(
            joinedload(models.Tap.keg).joinedload(models.Keg.beverage),
            joinedload(models.Tap.display_config),
        )
        .order_by(models.Tap.tap_id.asc())
        .first()
    )


def _get_beverage_by_name(db, name: str):
    return db.query(models.Beverage).filter(models.Beverage.name == name).first()


def _find_matching_beverage(db, fixture: dict) -> models.Beverage | None:
    candidate_names = [fixture["name"], *fixture.get("legacy_names", [])]
    return (
        db.query(models.Beverage)
        .filter(models.Beverage.name.in_(candidate_names))
        .order_by(models.Beverage.updated_at.desc().nullslast(), models.Beverage.name.asc())
        .first()
    )


def _apply_beverage_fields(beverage: models.Beverage, fixture: dict) -> None:
    beverage.name = fixture["name"]
    beverage.brewery = fixture["brewery"]
    beverage.style = fixture["style"]
    beverage.abv = fixture["abv"]
    beverage.sell_price_per_liter = fixture["sell_price_per_liter"]
    beverage.description_short = fixture["description_short"]
    beverage.ibu = fixture["ibu"]
    beverage.display_brand_name = fixture["display_brand_name"]
    beverage.accent_color = fixture["accent_color"]
    beverage.text_theme = fixture["text_theme"]
    beverage.price_display_mode_default = fixture["price_display_mode_default"]


def _ensure_beverage(db, fixture: dict, *, primary_target: models.Beverage | None = None) -> tuple[models.Beverage, str]:
    if primary_target is not None:
        _apply_beverage_fields(primary_target, fixture)
        return primary_target, "updated_current"

    beverage = _find_matching_beverage(db, fixture)
    if beverage is None:
        beverage = models.Beverage()
        db.add(beverage)
        action = "created"
    else:
        action = "updated"

    _apply_beverage_fields(beverage, fixture)
    db.flush()
    return beverage, action


def _ensure_full_keg(db, beverage: models.Beverage, fixture: dict) -> tuple[models.Keg, str]:
    keg_fixture = fixture["keg"]
    existing = (
        db.query(models.Keg)
        .filter(
            models.Keg.beverage_id == beverage.beverage_id,
            models.Keg.status == "full",
            models.Keg.initial_volume_ml == keg_fixture["initial_volume_ml"],
            models.Keg.current_volume_ml == keg_fixture["initial_volume_ml"],
            models.Keg.purchase_price == keg_fixture["purchase_price"],
        )
        .order_by(models.Keg.created_at.asc())
        .first()
    )
    if existing is not None:
        return existing, "reused"

    keg = models.Keg(
        beverage_id=beverage.beverage_id,
        initial_volume_ml=keg_fixture["initial_volume_ml"],
        current_volume_ml=keg_fixture["initial_volume_ml"],
        purchase_price=keg_fixture["purchase_price"],
        status="full",
    )
    db.add(keg)
    db.flush()
    return keg, "created"


def _ensure_primary_tap_assignment(tap: models.Tap | None, primary_beverage: models.Beverage | None) -> str:
    if tap is None:
        return "tap_missing"

    if primary_beverage is None:
        return "beverage_missing"

    if tap.keg_id is not None and tap.status == "active":
        return "kept_existing"

    candidate = None
    for keg in sorted(
        primary_beverage.kegs or [],
        key=lambda item: (
            item.status != "full",
            -(item.current_volume_ml or 0),
            item.created_at or datetime.min.replace(tzinfo=timezone.utc),
        ),
    ):
        if keg.status == "full":
            candidate = keg
            break

    if candidate is None:
        return "no_full_keg"

    tap.keg_id = candidate.keg_id
    tap.status = "active"
    candidate.status = "in_use"
    if candidate.tapped_at is None:
        candidate.tapped_at = datetime.now(timezone.utc)
    return f"assigned:{candidate.keg_id}"


def _clear_display_override(tap: models.Tap | None) -> bool:
    if tap is None or tap.display_config is None or tap.display_config.override_accent_color is None:
        return False
    tap.display_config.override_accent_color = None
    return True


def _ensure_primary_tap_copy(tap: models.Tap | None) -> str:
    if tap is None:
        return "tap_missing"

    if tap.display_config is None:
        tap.display_config = models.TapDisplayConfig(tap_id=tap.tap_id)
        action = "created"
    else:
        action = "updated"

    for key, value in PRIMARY_TAP_COPY.items():
        setattr(tap.display_config, key, value)

    return action


def _print_summary(db) -> None:
    print("")
    print("Tap display catalog")
    taps = (
        db.query(models.Tap)
        .options(joinedload(models.Tap.keg).joinedload(models.Keg.beverage))
        .order_by(models.Tap.tap_id.asc())
        .all()
    )
    beverages = db.query(models.Beverage).order_by(models.Beverage.name.asc()).all()

    for tap in taps:
        beverage_name = tap.keg.beverage.name if tap.keg and tap.keg.beverage else "-"
        print(
            f"- tap #{tap.tap_id}: {tap.display_name} | status={tap.status} | "
            f"beverage={beverage_name}"
        )

    print("- beverages:")
    for beverage in beverages:
        full_kegs = (
            db.query(models.Keg.keg_id)
            .filter(
                models.Keg.beverage_id == beverage.beverage_id,
                models.Keg.status == "full",
            )
            .count()
        )
        in_use_kegs = (
            db.query(models.Keg.keg_id)
            .filter(
                models.Keg.beverage_id == beverage.beverage_id,
                models.Keg.status == "in_use",
            )
            .count()
        )
        print(
            f"  * {beverage.name} | {beverage.style or '-'} | "
            f"{beverage.sell_price_per_liter} RUB/L | full_kegs={full_kegs} | in_use_kegs={in_use_kegs}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Populate the local dev database with richer tap display beverage catalog data."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned changes without writing to the database.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        primary_tap = _get_primary_tap(db)
        primary_beverage = primary_tap.keg.beverage if primary_tap and primary_tap.keg and primary_tap.keg.beverage else None

        print("Tap display catalog seed started")
        print(f"- dry_run: {'yes' if args.dry_run else 'no'}")
        if primary_tap:
            print(f"- primary_tap: #{primary_tap.tap_id} ({primary_tap.display_name})")
        else:
            print("- primary_tap: not found")

        for index, fixture in enumerate(BEVERAGE_FIXTURES):
            beverage, beverage_action = _ensure_beverage(
                db,
                fixture,
                primary_target=primary_beverage if index == 0 else None,
            )
            keg, keg_action = _ensure_full_keg(db, beverage, fixture)
            print(
                f"[{beverage_action}] {beverage.name} | keg={keg_action} | "
                f"keg_id={keg.keg_id}"
            )

        assignment_action = _ensure_primary_tap_assignment(primary_tap, primary_beverage)
        print(f"- primary_tap_assignment: {assignment_action}")
        tap_copy_action = _ensure_primary_tap_copy(primary_tap)
        print(f"- primary_tap_copy: {tap_copy_action}")
        display_override_cleared = _clear_display_override(primary_tap)
        print(f"- display_override_cleared: {'yes' if display_override_cleared else 'no'}")

        if args.dry_run:
            db.rollback()
            print("")
            print("Dry-run finished; no changes committed.")
            return 0

        db.commit()
        _print_summary(db)
        print("")
        print(f"{SCRIPT_NAME} finished")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
