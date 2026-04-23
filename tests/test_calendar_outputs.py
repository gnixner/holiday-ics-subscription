from pathlib import Path

from scripts.build_ics import build_all_calendars, expand_holiday, parse_args
from scripts.validate_holidays import load_holidays


def test_parse_args_overrides_publish_settings():
    args = parse_args(
        [
            "--start-year",
            "2030",
            "--years",
            "2",
            "--domain",
            "calendar.example.com",
            "--base-url",
            "https://calendar.example.com",
            "--dist-dir",
            "public",
        ]
    )

    assert args.start_year == 2030
    assert args.years == 2
    assert args.domain == "calendar.example.com"
    assert args.base_url == "https://calendar.example.com"
    assert args.dist_dir == "public"


def test_expand_holiday_to_single_day_event():
    holiday = {
        "id": "earth-day",
        "name_zh": "地球日",
        "month": 4,
        "day": 22,
        "categories": ["environment"],
        "description": "全球关注环境保护与可持续发展的主题日。",
        "enabled": True,
    }

    event = expand_holiday(holiday, 2026, "calendar.local")

    assert event["summary"] == "地球日"
    assert event["start"] == "20260422"
    assert event["end"] == "20260423"
    assert event["status"] == "CONFIRMED"
    assert event["transp"] == "TRANSPARENT"


def test_build_all_calendars_writes_expected_files(tmp_path):
    holidays = load_holidays("data/holidays.yaml")

    outputs = build_all_calendars(
        holidays=holidays,
        start_year=2026,
        years=1,
        domain="calendar.local",
        dist_dir=tmp_path,
        base_url="https://calendar.example.com",
    )

    assert set(outputs) == {
        "all.ics",
        "environment.ics",
        "culture-reading.ics",
        "festivals.ics",
        "index.html",
    }

    all_content = Path(outputs["all.ics"]).read_text(encoding="utf-8")
    assert "SUMMARY:地球日" in all_content
    assert "SUMMARY:世界读书日" in all_content
    assert "SUMMARY:圣诞节" in all_content
    assert "元旦" not in all_content
    assert "国际劳动节" not in all_content
    assert "X-WR-CALNAME:其他节日（全部）" in all_content

    landing_page = Path(outputs["index.html"]).read_text(encoding="utf-8")
    assert "https://calendar.example.com/all.ics" in landing_page
    assert "https://calendar.example.com/environment.ics" in landing_page
    assert "其他节日（全部）" in landing_page
    assert 'id="three-scene"' in landing_page
    assert 'https://unpkg.com/three@0.164.1/build/three.module.js' in landing_page
    assert "class HolidayParticleField" in landing_page
    assert 'class="enter-stage"' in landing_page
    assert "进入节日宇宙" in landing_page
    assert "Menu" in landing_page
    assert "ABOUT" in landing_page
    assert "holiday observance archive" in landing_page
    assert "将国际节日放进你的日历星图" in landing_page
    assert "订阅全部节日" in landing_page
    assert "audio-track" not in landing_page
