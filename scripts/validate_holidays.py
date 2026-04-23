from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
from typing import Iterable

import yaml

ALLOWED_CATEGORIES = {"environment", "culture-reading", "festivals"}
MAINLAND_CONFLICT_DATES = {(1, 1), (5, 1)}
BASE_REQUIRED_FIELDS = {"id", "name_zh", "categories", "enabled"}
RULE_TYPE_FIXED_DATE = "fixed_date"
RULE_TYPE_NTH_WEEKDAY = "nth_weekday_of_month"
ALLOWED_RULE_TYPES = {RULE_TYPE_FIXED_DATE, RULE_TYPE_NTH_WEEKDAY}
APPLE_CHINA_HOLIDAY_NAMES = {
    "七夕节",
    "中秋节",
    "儿童节",
    "元宵节",
    "元旦",
    "冬至",
    "劳动节",
    "国庆节",
    "处暑",
    "夏至",
    "大寒",
    "大暑",
    "大雪",
    "妇女节",
    "寒露",
    "小寒",
    "小暑",
    "小满",
    "小雪",
    "建党节",
    "建军节",
    "惊蛰",
    "春分",
    "春节",
    "正月初三",
    "正月初二",
    "清明",
    "白露",
    "秋分",
    "立冬",
    "立夏",
    "立春",
    "立秋",
    "端午节",
    "芒种",
    "谷雨",
    "重阳节",
    "除夕",
    "雨水",
    "霜降",
    "青年节",
}
APPLE_CHINA_NAME_ALIASES = {
    "国际妇女节": "妇女节",
}


def load_holidays(path: str | Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as handle:
        holidays = yaml.safe_load(handle)
    if not isinstance(holidays, list):
        raise ValueError("holidays file must contain a list")
    return holidays


def get_rule_type(holiday: dict) -> str:
    return holiday.get("rule_type", RULE_TYPE_FIXED_DATE)


def validate_required_fields(holidays: Iterable[dict]) -> None:
    for holiday in holidays:
        missing = BASE_REQUIRED_FIELDS - holiday.keys()
        if missing:
            raise ValueError(f"holiday {holiday.get('id', '<missing-id>')} missing fields: {sorted(missing)}")


def validate_unique_ids(holidays: Iterable[dict]) -> None:
    seen: set[str] = set()
    for holiday in holidays:
        holiday_id = holiday["id"]
        if holiday_id in seen:
            raise ValueError(f"duplicate holiday id: {holiday_id}")
        seen.add(holiday_id)


def validate_rule_values(holidays: Iterable[dict]) -> None:
    for holiday in holidays:
        rule_type = get_rule_type(holiday)
        if rule_type not in ALLOWED_RULE_TYPES:
            raise ValueError(f"holiday {holiday['id']} has invalid rule_type: {rule_type}")

        month = int(holiday["month"])
        if rule_type == RULE_TYPE_FIXED_DATE:
            if "day" not in holiday:
                raise ValueError(f"holiday {holiday['id']} missing fields: ['day']")
            try:
                date(2024, month, int(holiday["day"]))
            except Exception as exc:  # noqa: BLE001
                raise ValueError(f"invalid date for {holiday['id']}") from exc
            continue

        if "day" in holiday:
            raise ValueError(f"holiday {holiday['id']} should not define day for {rule_type}")
        if "nth" not in holiday or "weekday" not in holiday:
            raise ValueError(f"holiday {holiday['id']} missing fields for {rule_type}: ['nth', 'weekday']")

        nth = int(holiday["nth"])
        weekday = int(holiday["weekday"])
        if nth not in {1, 2, 3, 4, -1}:
            raise ValueError(f"holiday {holiday['id']} has invalid nth: {nth}")
        if weekday < 0 or weekday > 6:
            raise ValueError(f"holiday {holiday['id']} has invalid weekday: {weekday}")
        if month < 1 or month > 12:
            raise ValueError(f"holiday {holiday['id']} has invalid month: {month}")


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
        if get_rule_type(holiday) != RULE_TYPE_FIXED_DATE:
            continue
        conflict_key = (int(holiday["month"]), int(holiday["day"]))
        if conflict_key in MAINLAND_CONFLICT_DATES:
            raise ValueError(f"holiday {holiday['id']} conflicts with mainland holiday")


def validate_apple_china_duplicates(holidays: Iterable[dict]) -> None:
    for holiday in holidays:
        normalized_name = APPLE_CHINA_NAME_ALIASES.get(holiday["name_zh"], holiday["name_zh"])
        if normalized_name in APPLE_CHINA_HOLIDAY_NAMES:
            raise ValueError(f"holiday {holiday['id']} duplicates Apple China holiday: {normalized_name}")


def validate_holidays(holidays: Iterable[dict]) -> None:
    holiday_list = list(holidays)
    validate_required_fields(holiday_list)
    validate_unique_ids(holiday_list)
    validate_rule_values(holiday_list)
    validate_categories(holiday_list)
    validate_mainland_conflicts(holiday_list)
    validate_apple_china_duplicates(holiday_list)


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
