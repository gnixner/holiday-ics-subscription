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


def test_expand_nth_weekday_holiday_event():
    holiday = {
        "id": "mothers-day",
        "name_zh": "母亲节",
        "rule_type": "nth_weekday_of_month",
        "month": 5,
        "nth": 2,
        "weekday": 6,
        "categories": ["festivals"],
        "description": "五月的第二个星期日。",
        "enabled": True,
    }

    event = expand_holiday(holiday, 2026, "calendar.local")

    assert event["summary"] == "母亲节"
    assert event["start"] == "20260510"
    assert event["end"] == "20260511"


def test_expand_easter_relative_holiday_event():
    holiday = {
        "id": "good-friday",
        "name_zh": "耶稣受难日",
        "rule_type": "easter_relative",
        "offset_days": -2,
        "categories": ["festivals"],
        "description": "复活节前的星期五。",
        "enabled": True,
    }

    event = expand_holiday(holiday, 2026, "calendar.local")

    assert event["summary"] == "耶稣受难日"
    assert event["start"] == "20260403"
    assert event["end"] == "20260404"


def test_expand_lunar_holiday_event():
    holiday = {
        "id": "dragon-head-raising-day",
        "name_zh": "龙抬头",
        "rule_type": "lunar_date",
        "lunar_month": 2,
        "lunar_day": 2,
        "categories": ["festivals"],
        "description": "农历二月初二。",
        "enabled": True,
    }

    event = expand_holiday(holiday, 2026, "calendar.local")

    assert event["summary"] == "龙抬头"
    assert event["start"] == "20260320"
    assert event["end"] == "20260321"


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
    assert "SUMMARY:母亲节" in all_content
    assert "SUMMARY:父亲节" in all_content
    assert "SUMMARY:感恩节" in all_content
    assert "SUMMARY:复活节" in all_content
    assert "SUMMARY:耶稣受难日" in all_content
    assert "SUMMARY:黑色星期五" in all_content
    assert "SUMMARY:教师节" in all_content
    assert "SUMMARY:植树节" in all_content
    assert "SUMMARY:情人节" in all_content
    assert "SUMMARY:平安夜" in all_content
    assert "SUMMARY:腊八节" in all_content
    assert "SUMMARY:小年" in all_content
    assert "SUMMARY:龙抬头" in all_content
    assert "国际妇女节" not in all_content
    assert "元旦" not in all_content
    assert "国际劳动节" not in all_content
    assert "X-WR-CALNAME:其他节日（全部）" in all_content

    landing_page = Path(outputs["index.html"]).read_text(encoding="utf-8")
    assert "https://calendar.example.com/all.ics" in landing_page
    assert "https://calendar.example.com/environment.ics" in landing_page
    assert ">全部<" in landing_page
    assert ">环保与社会议题<" in landing_page
    assert ">文化与阅读<" in landing_page
    assert ">常见节庆<" in landing_page
    assert "其他节日（全部）" not in landing_page
    assert "其他节日（环保与社会议题）" not in landing_page
    assert "其他节日（文化与阅读）" not in landing_page
    assert "其他节日（常见节庆）" not in landing_page
    assert 'id="three-scene"' in landing_page
    assert 'https://unpkg.com/three@0.164.1/build/three.module.js' in landing_page
    assert "class HolidayParticleField" in landing_page
    assert "有些日子，值得留下" in landing_page
    assert "把重要的日子，留在眼前" in landing_page
    assert "母亲节、父亲节这样的日子，也能被记住。" in landing_page
    assert "收下全部" in landing_page
    assert 'content="width=device-width, initial-scale=1"' in landing_page
    assert "font-family: 'PingFang SC', 'Noto Sans SC'" in landing_page
    assert 'color: var(--text-strong);' in landing_page
    assert 'color: var(--text-muted);' in landing_page
    assert '@media (max-width: 960px)' in landing_page
    assert '@media (max-width: 640px)' in landing_page
    assert 'grid-template-columns: 1fr;' in landing_page
    assert 'height: 100dvh' in landing_page
    assert 'padding: 1.15rem 1rem 6.25rem' in landing_page
    assert 'h1 { font-size: clamp(2rem, 10vw, 2.95rem); max-width: 7.2ch; }' in landing_page
    assert 'gap: 0.55rem;' in landing_page
    assert 'width: 100%; justify-content: flex-start; padding: 0.8rem 0.95rem;' in landing_page
    assert 'background: rgba(255,255,255,0.045);' in landing_page
    assert 'border: 1px solid rgba(255,255,255,0.08);' in landing_page
    assert 'min-height: 3.35rem' in landing_page
    assert 'font-weight: 500;' in landing_page
    assert 'background: linear-gradient(180deg, rgba(34, 26, 31, 0.56), rgba(19, 15, 19, 0.48));' in landing_page
    assert 'border: 1px solid rgba(255,255,255,0.09);' in landing_page
    assert 'touchstart' in landing_page
    assert 'touchend' in landing_page
    assert 'class="page-track"' in landing_page
    assert 'class="page-panel page-panel-hero is-active"' in landing_page
    assert 'data-page-nav="prev"' in landing_page
    assert 'data-page-nav="next"' in landing_page
    assert 'data-page-jump="1"' in landing_page
    assert "handleWheel" in landing_page
    assert "复制链接" in landing_page
    assert "navigator.clipboard.writeText" in landing_page
    assert 'id="copy-toast"' in landing_page
    assert "链接已复制" in landing_page
    assert 'class="enter-stage"' not in landing_page
    assert "进入节日宇宙" not in landing_page
    assert "Menu" not in landing_page
    assert "ABOUT" not in landing_page
    assert "Other Holidays Archive" not in landing_page
    assert "Three.js 真 3D 粒子背景 + 左右翻页式首页切换。" not in landing_page
    assert "复制 / 打开链接" not in landing_page
    assert "左右翻页在首页、订阅页与说明页之间切换" not in landing_page
    assert "audio-track" not in landing_page
