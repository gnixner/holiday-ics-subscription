from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
import argparse
import sys
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_holidays import load_holidays, validate_holidays

CALENDAR_DOMAIN = "calendar.local"
DEFAULT_YEARS = 5
DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "holidays.yaml"
DIST_DIR = Path(__file__).resolve().parents[1] / "dist"
PRODID = "-//Other Holidays ICS//ZH//EN"
CALENDAR_METADATA = {
    "all.ics": ("其他节日（全部）", "中国大陆法定节假日之外的补充型节日订阅。"),
    "environment.ics": ("其他节日（环保与社会议题）", "环保、健康、包容与社会主题相关节日订阅。"),
    "culture-reading.ics": ("其他节日（文化与阅读）", "阅读、语言、教育、博物馆与文化主题节日订阅。"),
    "festivals.ics": ("其他节日（常见节庆）", "大众熟知的国际文化节庆订阅。"),
}
CATEGORY_TO_FILE = {
    "environment": "environment.ics",
    "culture-reading": "culture-reading.ics",
    "festivals": "festivals.ics",
}


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def build_uid(holiday_id: str, year: int, domain: str) -> str:
    return f"{holiday_id}-{year}@{domain}"


def expand_holiday(holiday: dict, year: int, domain: str) -> dict:
    start_date = date(year, int(holiday["month"]), int(holiday["day"]))
    end_date = start_date.fromordinal(start_date.toordinal() + 1)
    return {
        "uid": build_uid(holiday["id"], year, domain),
        "summary": holiday["name_zh"],
        "description": holiday.get("description", ""),
        "start": start_date.strftime("%Y%m%d"),
        "end": end_date.strftime("%Y%m%d"),
        "status": "CONFIRMED",
        "transp": "TRANSPARENT",
        "category": holiday["categories"][0],
        "holiday_id": holiday["id"],
    }


def escape_ics_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def render_event(event: dict, dtstamp: str) -> list[str]:
    lines = [
        "BEGIN:VEVENT",
        f"UID:{event['uid']}",
        f"DTSTAMP:{dtstamp}",
        f"SUMMARY:{escape_ics_text(event['summary'])}",
    ]
    if event["description"]:
        lines.append(f"DESCRIPTION:{escape_ics_text(event['description'])}")
    lines.extend(
        [
            f"DTSTART;VALUE=DATE:{event['start']}",
            f"DTEND;VALUE=DATE:{event['end']}",
            f"STATUS:{event['status']}",
            f"TRANSP:{event['transp']}",
            "END:VEVENT",
        ]
    )
    return lines


def render_calendar(filename: str, events: list[dict], dtstamp: str) -> str:
    cal_name, cal_desc = CALENDAR_METADATA[filename]
    lines = [
        "BEGIN:VCALENDAR",
        f"PRODID:{PRODID}",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{escape_ics_text(cal_name)}",
        f"X-WR-CALDESC:{escape_ics_text(cal_desc)}",
    ]
    for event in sorted(events, key=lambda item: (item["start"], item["holiday_id"])):
        lines.extend(render_event(event, dtstamp))
    lines.append("END:VCALENDAR")
    return "\n".join(lines) + "\n"


def render_index(base_url: str) -> str:
    normalized = normalize_base_url(base_url)
    items: list[str] = []
    for filename, (name, desc) in CALENDAR_METADATA.items():
        items.extend(
            [
                "    <li>",
                f"      <h2>{name}</h2>",
                f"      <p>{desc}</p>",
                f'      <p><a href="{normalized}/{filename}">{normalized}/{filename}</a></p>',
                "    </li>",
            ]
        )
    lines = [
        "<!doctype html>",
        '<html lang="zh-CN">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1">',
        "  <title>其他节日 ICS 订阅</title>",
        "</head>",
        "<body>",
        "  <h1>其他节日 ICS 订阅</h1>",
        "  <p>中国大陆法定节假日之外的补充型节日订阅。</p>",
        "  <ul>",
        *items,
        "  </ul>",
        "</body>",
        "</html>",
    ]
    return "\n".join(lines) + "\n"


def build_all_calendars(
    holidays: Iterable[dict],
    start_year: int,
    years: int,
    domain: str,
    dist_dir: str | Path,
    base_url: str | None = None,
) -> dict[str, str]:
    calendar_events = {filename: [] for filename in CALENDAR_METADATA}
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for holiday in holidays:
        if not holiday.get("enabled", False):
            continue
        for year in range(start_year, start_year + years):
            event = expand_holiday(holiday, year, domain)
            calendar_events["all.ics"].append(event)
            calendar_events[CATEGORY_TO_FILE[event["category"]]].append(event)

    dist_path = Path(dist_dir)
    dist_path.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, str] = {}
    for filename, events in calendar_events.items():
        target = dist_path / filename
        target.write_text(render_calendar(filename, events, dtstamp), encoding="utf-8")
        outputs[filename] = str(target)
    if base_url:
        index_target = dist_path / "index.html"
        index_target.write_text(render_index(base_url), encoding="utf-8")
        outputs["index.html"] = str(index_target)
    return outputs


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build holiday ICS subscription files.")
    parser.add_argument("--start-year", type=int, default=date.today().year)
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--domain", default=CALENDAR_DOMAIN)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--dist-dir", default=str(DIST_DIR))
    parser.add_argument("--data-file", default=str(DATA_FILE))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    holidays = load_holidays(args.data_file)
    validate_holidays(holidays)
    outputs = build_all_calendars(
        holidays=holidays,
        start_year=args.start_year,
        years=args.years,
        domain=args.domain,
        dist_dir=args.dist_dir,
        base_url=args.base_url,
    )
    print(f"Generated {len(outputs)} calendar files in {args.dist_dir}.")
    for filename in sorted(outputs):
        print(f"- {filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
