from scripts.build_ics import build_uid


def test_uid_is_stable():
    uid1 = build_uid("earth-day", 2026, "calendar.local")
    uid2 = build_uid("earth-day", 2026, "calendar.local")
    assert uid1 == uid2 == "earth-day-2026@calendar.local"


def test_uid_changes_with_year():
    assert build_uid("earth-day", 2026, "calendar.local") != build_uid(
        "earth-day", 2027, "calendar.local"
    )
