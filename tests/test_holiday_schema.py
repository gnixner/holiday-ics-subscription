import pytest

from scripts.validate_holidays import load_holidays, validate_holidays


def test_holidays_yaml_is_loadable():
    holidays = load_holidays("data/holidays.yaml")
    assert isinstance(holidays, list)
    assert len(holidays) >= 27


def test_holidays_have_required_fields_and_valid_values():
    holidays = load_holidays("data/holidays.yaml")
    validate_holidays(holidays)


def test_mainland_holiday_conflicts_are_rejected():
    holidays = [
        {
            "id": "new-years-day",
            "name_zh": "元旦",
            "month": 1,
            "day": 1,
            "categories": ["festivals"],
            "enabled": True,
        }
    ]

    with pytest.raises(ValueError, match="conflicts with mainland holiday"):
        validate_holidays(holidays)


def test_nth_weekday_rule_is_accepted_for_dynamic_holidays():
    holidays = [
        {
            "id": "mothers-day",
            "name_zh": "母亲节",
            "rule_type": "nth_weekday_of_month",
            "month": 5,
            "nth": 2,
            "weekday": 6,
            "categories": ["festivals"],
            "enabled": True,
        }
    ]

    validate_holidays(holidays)


def test_easter_relative_rule_is_accepted():
    holidays = [
        {
            "id": "good-friday",
            "name_zh": "耶稣受难日",
            "rule_type": "easter_relative",
            "offset_days": -2,
            "categories": ["festivals"],
            "enabled": True,
        }
    ]

    validate_holidays(holidays)


def test_lunar_date_rule_is_accepted():
    holidays = [
        {
            "id": "dragon-head-raising-day",
            "name_zh": "龙抬头",
            "rule_type": "lunar_date",
            "lunar_month": 2,
            "lunar_day": 2,
            "categories": ["festivals"],
            "enabled": True,
        }
    ]

    validate_holidays(holidays)


def test_apple_china_overlap_is_rejected():
    holidays = [
        {
            "id": "international-womens-day",
            "name_zh": "国际妇女节",
            "month": 3,
            "day": 8,
            "categories": ["environment"],
            "enabled": True,
        }
    ]

    with pytest.raises(ValueError, match="duplicates Apple China holiday"):
        validate_holidays(holidays)
