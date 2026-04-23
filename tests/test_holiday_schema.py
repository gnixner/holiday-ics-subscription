import pytest

from scripts.validate_holidays import load_holidays, validate_holidays


def test_holidays_yaml_is_loadable():
    holidays = load_holidays("data/holidays.yaml")
    assert isinstance(holidays, list)
    assert len(holidays) == 27


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
