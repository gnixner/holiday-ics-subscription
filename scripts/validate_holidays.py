from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
from typing import Iterable

import yaml

ALLOWED_CATEGORIES = {"environment", "culture-reading", "festivals"}
MAINLAND_CONFLICT_DATES = {(1, 1), (5, 1)}
REQUIRED_FIELDS = {"id", "name_zh", "month", "day", "categories", "enabled"}


def load_holidays(path: str | Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as handle:
        holidays = yaml.safe_load(handle)
    if not isinstance(holidays, list):
        raise ValueError("holidays file must contain a list")
    return holidays


def validate_required_fields(holidays: Iterable[dict]) -> None:
    for holiday in holidays:
        missing = REQUIRED_FIELDS - holiday.keys()
        if missing:
            raise ValueError(f"holiday {holiday.get('id', '<missing-id>')} missing fields: {sorted(missing)}")


def validate_unique_ids(holidays: Iterable[dict]) -> None:
    seen: set[str] = set()
    for holiday in holidays:
        holiday_id = holiday["id"]
        if holiday_id in seen:
            raise ValueError(f"duplicate holiday id: {holiday_id}")
        seen.add(holiday_id)


def validate_date_values(holidays: Iterable[dict]) -> None:
    for holiday in holidays:
        try:
            date(2024, int(holiday["month"]), int(holiday["day"]))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"invalid date for {holiday['id']}") from exc


def validate_categories(holidays: Iterable[dict]) -> None:
    for holiday in holidays:
        categories = holiday["categories"]
        if not isinstance(categories, list) or len(categories) != 1:
            raise ValueError(f"holiday {holiday['id']} must have exactly one category")
        category = categories[0]
        if category not in ALLOWED_CATEGORIES:
            raise ValueError(f"holiday {holiday['id']} has invalid category: {category}")


def validate_mainland_conflicts(holidays: Iterable[dict]) -> None:
    for holiday in holidays:
        conflict_key = (int(holiday["month"]), int(holiday["day"]))
        if conflict_key in MAINLAND_CONFLICT_DATES:
            raise ValueError(f"holiday {holiday['id']} conflicts with mainland holiday")


def validate_holidays(holidays: Iterable[dict]) -> None:
    holiday_list = list(holidays)
    validate_required_fields(holiday_list)
    validate_unique_ids(holiday_list)
    validate_date_values(holiday_list)
    validate_categories(holiday_list)
    validate_mainland_conflicts(holiday_list)


def main() -> int:
    holidays = load_holidays(Path(__file__).resolve().parents[1] / "data" / "holidays.yaml")
    validate_holidays(holidays)
    print(f"Validated {len(holidays)} holidays successfully.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
