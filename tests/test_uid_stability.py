from scripts.build_ics import build_uid, expand_holiday


def test_uid_is_stable():
    uid1 = build_uid("earth-day", 2026, "calendar.local")
    uid2 = build_uid("earth-day", 2026, "calendar.local")
    assert uid1 == uid2 == "earth-day-2026@calendar.local"


def test_uid_changes_with_year():
    assert build_uid("earth-day", 2026, "calendar.local") != build_uid(
        "earth-day", 2027, "calendar.local"
    )


def test_uid_rule_type_does_not_change_uid_shape():
    holiday = {
        "id": "mothers-day",
        "name_zh": "母亲节",
        "rule_type": "nth_weekday_of_month",
        "month": 5,
        "nth": 2,
        "weekday": 6,
        "categories": ["festivals"],
        "enabled": True,
    }

    event = expand_holiday(holiday, 2026, "calendar.local")
    assert event["uid"] == "mothers-day-2026@calendar.local"


def test_uid_is_stable_for_lunar_rule_type():
    holiday = {
        "id": "dragon-head-raising-day",
        "name_zh": "龙抬头",
        "rule_type": "lunar_date",
        "lunar_month": 2,
        "lunar_day": 2,
        "categories": ["festivals"],
        "enabled": True,
    }

    event = expand_holiday(holiday, 2026, "calendar.local")
    assert event["uid"] == "dragon-head-raising-day-2026@calendar.local"
