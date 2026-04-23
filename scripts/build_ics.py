from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import argparse
import sys
from typing import Iterable

from lunardate import LunarDate

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
    "all.ics": {
        "calendar_name": "其他节日（全部）",
        "page_title": "全部",
        "description": "把这些日子，都留在一起。",
    },
    "environment.ics": {
        "calendar_name": "其他节日（环保与社会议题）",
        "page_title": "环保与社会议题",
        "description": "关于地球，也关于彼此。",
    },
    "culture-reading.ics": {
        "calendar_name": "其他节日（文化与阅读）",
        "page_title": "文化与阅读",
        "description": "适合阅读、语言与文化。",
    },
    "festivals.ics": {
        "calendar_name": "其他节日（常见节庆）",
        "page_title": "常见节庆",
        "description": "留给那些熟悉的节日。",
    },
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


def resolve_nth_weekday_date(year: int, month: int, nth: int, weekday: int) -> date:
    if nth > 0:
        first_day = date(year, month, 1)
        days_until_weekday = (weekday - first_day.weekday()) % 7
        return first_day + timedelta(days=days_until_weekday + (nth - 1) * 7)

    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    last_day = next_month - timedelta(days=1)
    days_back = (last_day.weekday() - weekday) % 7
    return last_day - timedelta(days=days_back)


def calculate_western_easter(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def resolve_lunar_date(year: int, lunar_month: int, lunar_day: int) -> date:
    return LunarDate(year, lunar_month, lunar_day, 0).toSolarDate()


def resolve_holiday_date(holiday: dict, year: int) -> date:
    rule_type = holiday.get("rule_type", "fixed_date")
    if rule_type == "nth_weekday_of_month":
        return resolve_nth_weekday_date(
            year,
            int(holiday["month"]),
            int(holiday["nth"]),
            int(holiday["weekday"]),
        )
    if rule_type == "easter_relative":
        return calculate_western_easter(year) + timedelta(days=int(holiday["offset_days"]))
    if rule_type == "lunar_date":
        return resolve_lunar_date(year, int(holiday["lunar_month"]), int(holiday["lunar_day"]))
    return date(year, int(holiday["month"]), int(holiday["day"]))


def expand_holiday(holiday: dict, year: int, domain: str) -> dict:
    start_date = resolve_holiday_date(holiday, year)
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
    metadata = CALENDAR_METADATA[filename]
    cal_name = metadata["calendar_name"]
    cal_desc = metadata["description"]
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
    cards: list[str] = []
    for filename, metadata in CALENDAR_METADATA.items():
        href = f"{normalized}/{filename}"
        page_title = metadata["page_title"]
        desc = metadata["description"]
        primary_cta = "收下全部" if filename == "all.ics" else "收下这一组"
        cards.extend(
            [
                '          <article class="subscription-card">',
                f'            <p class="eyebrow">{filename}</p>',
                f'            <h3>{page_title}</h3>',
                f'            <p class="card-description">{desc}</p>',
                '            <div class="card-actions">',
                f'              <a class="button button-primary" href="{href}">{primary_cta}</a>',
                f'              <button class="button button-secondary" type="button" data-copy-url="{href}">复制链接</button>',
                '            </div>',
                f'            <p class="subscription-url">{href}</p>',
                '          </article>',
            ]
        )

    lines = [
        "<!doctype html>",
        '<html lang="zh-CN">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1">',
        '  <meta name="color-scheme" content="dark">',
        '  <meta name="description" content="中国大陆法定节假日之外的补充型节日订阅，支持 Apple Calendar 等支持 ICS 的日历客户端。">',
        '  <link rel="preconnect" href="https://fonts.googleapis.com">',
        '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        '  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600&display=swap" rel="stylesheet">',
        "  <title>其他节日 ICS 订阅</title>",
        "  <style>",
        "    :root {",
        "      --bg: #1f171d;",
        "      --bg-soft: rgba(46, 32, 40, 0.72);",
        "      --panel: rgba(29, 22, 28, 0.52);",
        "      --panel-border: rgba(231, 221, 216, 0.12);",
        "      --text-strong: rgba(245, 240, 236, 0.96);",
        "      --text: rgba(231, 221, 216, 0.84);",
        "      --text-muted: rgba(231, 221, 216, 0.62);",
        "      --text-soft: rgba(231, 221, 216, 0.46);",
        "      --accent: #8d7a84;",
        "      --accent-strong: rgba(244, 229, 236, 0.74);",
        "      --glow: rgba(111, 143, 139, 0.32);",
        "      --lavender: rgba(184, 166, 184, 0.55);",
        "      --pale-lilac: rgba(207, 198, 207, 0.7);",
        "      --sage: rgba(124, 154, 116, 0.34);",
        "      --moss: rgba(77, 107, 69, 0.30);",
        "      --warm: rgba(175, 143, 124, 0.14);",
        "      --shadow: 0 30px 80px rgba(0, 0, 0, 0.45);",
        "      --radius: 28px;",
        "      font-family: 'PingFang SC', 'Noto Sans SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;",
        "    }",
        "    * { box-sizing: border-box; }",
        "    html, body { height: 100%; scroll-behavior: smooth; }",
        "    body {",
        "      margin: 0;",
        "      color: var(--text);",
        "      background:",
        "        radial-gradient(circle at 20% 20%, rgba(77, 107, 69, 0.28), transparent 30%),",
        "        radial-gradient(circle at 78% 18%, rgba(184, 166, 184, 0.20), transparent 26%),",
        "        radial-gradient(circle at 52% 75%, rgba(207, 198, 207, 0.10), transparent 24%),",
        "        linear-gradient(180deg, #34262f 0%, #241b23 42%, #1a1318 100%);",
        "      overflow-x: hidden;",
        "    }",
        "    body::before {",
        "      content: '';",
        "      position: fixed;",
        "      inset: 0;",
        "      background: linear-gradient(180deg, rgba(9, 8, 9, 0.08) 0%, rgba(20, 14, 18, 0.36) 100%);",
        "      pointer-events: none;",
        "      z-index: 1;",
        "    }",
        "    #three-scene {",
        "      position: fixed;",
        "      inset: 0;",
        "      width: 100%;",
        "      height: 100%;",
        "      z-index: 0;",
        "      pointer-events: none;",
        "      opacity: 0.98;",
        "      mix-blend-mode: screen;",
        "    }",
        "    .orb {",
        "      position: fixed;",
        "      border-radius: 50%;",
        "      filter: blur(60px);",
        "      pointer-events: none;",
        "      z-index: 0;",
        "      opacity: 0.45;",
        "    }",
        "    .orb-left {",
        "      width: 24rem; height: 24rem; left: -6rem; top: 12vh;",
        "      background: rgba(77, 107, 69, 0.26);",
        "      animation: drift 18s ease-in-out infinite alternate;",
        "    }",
        "    .orb-right {",
        "      width: 20rem; height: 20rem; right: -4rem; top: 8vh;",
        "      background: rgba(184, 166, 184, 0.22);",
        "      animation: drift 22s ease-in-out infinite alternate-reverse;",
        "    }",
        "    .page-shell { position: relative; z-index: 2; height: 100vh; overflow: hidden; }",
        "    .chrome-nav {",
        "      position: fixed; inset: 0; z-index: 3; pointer-events: none;",
        "      padding: 1.4rem 1.4rem 1.8rem;",
        "    }",
        "    .chrome-nav a, .chrome-nav button { pointer-events: auto; }",
        "    .chrome-top { display: flex; justify-content: flex-end; align-items: flex-start; gap: 1rem; min-height: 2rem; }",
        "    .chrome-sides { position: absolute; inset: 50% 0 auto; transform: translateY(-50%); display: flex; justify-content: space-between; padding: 0 1rem; }",
        "    .side-arrow {",
        "      width: 2.8rem; height: 2.8rem; border-radius: 999px; border: 1px solid rgba(231,221,216,0.16); display: inline-flex; align-items: center; justify-content: center; color: rgba(231,221,216,0.82); text-decoration: none; background: rgba(29,22,28,0.24); backdrop-filter: blur(10px); cursor: pointer;",
        "    }",
        "    .side-arrow span { font-size: 1.1rem; transform: translateY(-1px); }",
        "    .page-viewport { width: 100%; height: 100%; overflow: hidden; }",
        "    .page-track { display: flex; width: 200vw; height: 100%; transition: transform 980ms cubic-bezier(0.16, 1, 0.3, 1); will-change: transform; touch-action: pan-y; }",
        "    .page-panel { width: 100vw; height: 100vh; flex: 0 0 100vw; padding: 2rem clamp(1.25rem, 3vw, 3rem) 4rem; display: grid; align-items: center; }",
        "    .page-panel-subscriptions { align-items: stretch; padding-top: 6rem; padding-bottom: 5rem; overflow-y: auto; }",
        "    .page-panel.is-active .section-fade, .page-panel .section-fade.is-visible { opacity: 1; transform: translateY(0); }",
        "    .hero-panel {",
        "      max-width: 1180px;",
        "      margin: 0 auto;",
        "      width: 100%;",
        "      display: grid;",
        "      grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.95fr);",
        "      gap: clamp(1.5rem, 3vw, 3rem);",
        "      align-items: center;",
        "    }",
        "    .intro {",
        "      padding: clamp(1rem, 2vw, 2rem);",
        "    }",
        "    .kicker {",
        "      letter-spacing: 0.22em;",
        "      text-transform: uppercase;",
        "      color: var(--text-soft);",
        "      font-size: 0.78rem;",
        "      margin-bottom: 1.25rem;",
        "    }",
        "    h1 {",
        "      margin: 0;",
        "      font-family: 'PingFang SC', 'Noto Sans SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;",
        "      font-size: clamp(2.45rem, 5vw, 4.7rem);",
        "      font-weight: 300;",
        "      line-height: 1.1;",
        "      letter-spacing: -0.04em;",
        "      color: var(--text-strong);",
        "      max-width: 8.5ch;",
        "      text-wrap: balance;",
        "    }",
        "    .lead {",
        "      margin: 1.35rem 0 0;",
        "      max-width: 34rem;",
        "      font-size: clamp(1rem, 1.65vw, 1.12rem);",
        "      line-height: 1.9;",
        "      color: var(--text-muted);",
        "    }",
        "    .meta-row {",
        "      margin-top: 2rem;",
        "      display: flex;",
        "      flex-wrap: wrap;",
        "      gap: 0.75rem;",
        "    }",
        "    .meta-pill {",
        "      display: inline-flex; align-items: center; gap: 0.55rem;",
        "      padding: 0.72rem 0.95rem;",
        "      border-radius: 999px;",
        "      background: rgba(255,255,255,0.045);",
        "      border: 1px solid rgba(255,255,255,0.08);",
        "      backdrop-filter: blur(12px);",
        "      color: var(--text);",
        "      font-size: 0.92rem;",
        "    }",
        "    .meta-dot { width: 0.5rem; height: 0.5rem; border-radius: 50%; background: var(--accent); box-shadow: 0 0 14px var(--glow); }",
        "    .hero-actions {",
        "      margin-top: 2rem;",
        "      display: flex;",
        "      gap: 0.9rem;",
        "      flex-wrap: wrap;",
        "      animation: rise-in 900ms ease both;",
        "    }",
        "    .section-fade { opacity: 0; transform: translateY(26px); transition: opacity 800ms ease, transform 800ms ease; }",
        "    .section-fade.is-visible { opacity: 1; transform: translateY(0); }",
        "    .button {",
        "      display: inline-flex;",
        "      align-items: center;",
        "      justify-content: center;",
        "      min-height: 3.35rem;",
        "      padding: 0.95rem 1.35rem;",
        "      border-radius: 999px;",
        "      border: 1px solid transparent;",
        "      text-decoration: none;",
        "      font-weight: 500;",
        "      letter-spacing: -0.01em;",
        "      transition: transform 160ms ease, background 160ms ease, border-color 160ms ease, box-shadow 160ms ease;",
        "    }",
        "    .button:hover { transform: translateY(-1px); }",
        "    .button-primary {",
        "      color: #1d171b;",
        "      background: linear-gradient(135deg, #dfd9d5 0%, #8ba39e 100%);",
        "      box-shadow: 0 16px 38px rgba(111, 143, 139, 0.28);",
        "    }",
        "    .button-secondary {",
        "      color: var(--text);",
        "      border-color: rgba(255,255,255,0.14);",
        "      background: rgba(255,255,255,0.04);",
        "      backdrop-filter: blur(14px);",
        "    }",
        "    .hero-note {",
        "      margin-top: 1rem;",
        "      font-size: 0.92rem;",
        "      color: var(--text-muted);",
        "      letter-spacing: 0.06em;",
        "    }",
        "    .hero-card {",
        "      position: relative;",
        "      padding: clamp(1.4rem, 2vw, 2rem);",
        "      background: linear-gradient(180deg, rgba(34, 26, 31, 0.56), rgba(19, 15, 19, 0.48));",
        "      border: 1px solid rgba(255,255,255,0.09);",
        "      border-radius: var(--radius);",
        "      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.34);",
        "      backdrop-filter: blur(18px);",
        "      overflow: hidden;",
        "      isolation: isolate;",
        "    }",
        "    .hero-card::before {",
        "      content: '';",
        "      position: absolute;",
        "      inset: auto -20% 65% 45%;",
        "      height: 10rem;",
        "      background: linear-gradient(90deg, rgba(111, 143, 139, 0), rgba(111, 143, 139, 0.16), rgba(184, 166, 184, 0));",
        "      transform: rotate(-18deg);",
        "      z-index: -1;",
        "    }",
        "    .section-label {",
        "      font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.22em; color: var(--text-soft); margin-bottom: 1rem;",
        "    }",
        "    .section-title { margin: 0 0 0.8rem; font-size: 1.35rem; color: var(--text-strong); }",
        "    .section-copy { margin: 0; color: var(--text-muted); line-height: 1.8; }",
        "    .stats {",
        "      margin-top: 1.5rem;",
        "      display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.9rem;",
        "    }",
        "    .stat {",
        "      padding: 1rem; border-radius: 20px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);",
        "    }",
        "    .stat strong { display: block; font-size: 1.4rem; margin-bottom: 0.3rem; }",
        "    .stat span { font-size: 0.88rem; color: var(--text-muted); }",
        "    .subscriptions { width: 100%; display: grid; align-items: center; }",
        "    .subscriptions-inner { max-width: 1180px; margin: 0 auto; width: 100%; }",
        "    .subscriptions-header { margin-bottom: 1.5rem; }",
        "    .subscriptions-header h2 { margin: 0; font-size: clamp(1.8rem, 3vw, 2.7rem); color: var(--text-strong); }",
        "    .subscriptions-header p { margin: 0.9rem 0 0; color: var(--text-muted); max-width: 44rem; line-height: 1.8; }",
        "    .subscription-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }",
        "    .subscription-card {",
        "      position: relative;",
        "      padding: 1.4rem;",
        "      background: linear-gradient(180deg, rgba(35, 27, 32, 0.74), rgba(18, 15, 18, 0.68));",
        "      border-radius: 24px;",
        "      border: 1px solid rgba(255,255,255,0.1);",
        "      box-shadow: var(--shadow);",
        "      backdrop-filter: blur(18px);",
        "      overflow: hidden;",
        "    }",
        "    .subscription-card::after {",
        "      content: ''; position: absolute; inset: 0; background: linear-gradient(135deg, rgba(111,143,139,0.10), rgba(255,255,255,0) 45%, rgba(184,166,184,0.08)); pointer-events: none;",
        "    }",
        "    .eyebrow { margin: 0 0 0.8rem; color: var(--text-soft); font-size: 0.78rem; letter-spacing: 0.18em; text-transform: uppercase; }",
        "    .subscription-card h3 { margin: 0; font-size: 1.25rem; color: var(--text-strong); }",
        "    .card-description { margin: 0.8rem 0 1rem; color: var(--text-muted); line-height: 1.75; min-height: 4.8em; }",
        "    .card-actions { display: flex; gap: 0.75rem; flex-wrap: wrap; }",
        "    .subscription-url { margin: 1rem 0 0; color: var(--text-soft); font-size: 0.82rem; line-height: 1.65; word-break: break-all; }",
        "    .copy-toast {",
        "      position: fixed; left: 50%; bottom: 2rem; transform: translate(-50%, 20px);",
        "      padding: 0.85rem 1.1rem; border-radius: 999px; background: rgba(20,16,20,0.88);",
        "      color: var(--text); border: 1px solid rgba(255,255,255,0.1); box-shadow: var(--shadow);",
        "      opacity: 0; pointer-events: none; transition: opacity 220ms ease, transform 220ms ease; z-index: 5;",
        "      backdrop-filter: blur(14px); font-size: 0.92rem; letter-spacing: 0.04em;",
        "    }",
        "    .copy-toast.is-visible { opacity: 1; transform: translate(-50%, 0); }",
        "    @keyframes drift {",
        "      from { transform: translate3d(0, 0, 0) scale(1); }",
        "      to { transform: translate3d(2rem, -1.5rem, 0) scale(1.06); }",
        "    }",
        "    @keyframes pulse-ring {",
        "      0%, 100% { transform: scale(1); opacity: 0.9; }",
        "      50% { transform: scale(1.035); opacity: 1; }",
        "    }",
        "    @keyframes float-title {",
        "      0%, 100% { transform: translateY(0); }",
        "      50% { transform: translateY(-8px); }",
        "    }",
        "    @keyframes rise-in {",
        "      from { opacity: 0; transform: translateY(16px); }",
        "      to { opacity: 1; transform: translateY(0); }",
        "    }",
        "    @media (max-width: 960px) {",
        "      .hero-panel, .subscription-grid { grid-template-columns: 1fr; }",
        "      .page-panel { padding: 1.5rem 1.1rem 4.25rem; }",
        "      .stats { grid-template-columns: 1fr 1fr; }",
        "      .hero-card { margin-top: 0.35rem; }",
        "      h1 { max-width: 10ch; }",
        "    }",
        "    @media (max-width: 640px) {",
        "      .page-shell { height: 100dvh; }",
        "      .chrome-nav { padding: 0.9rem 0.9rem 1rem; }",
        "      .chrome-sides { position: fixed; inset: auto 0 1rem; transform: none; display: flex; justify-content: center; gap: 0.85rem; padding: 0; }",
        "      .side-arrow { width: 3.15rem; height: 3.15rem; background: rgba(26, 20, 24, 0.52); border-color: rgba(255,255,255,0.14); }",
        "      .page-panel { height: 100dvh; padding: 1.15rem 1rem 6.25rem; align-items: start; overflow-y: auto; -webkit-overflow-scrolling: touch; }",
        "      .page-panel-subscriptions { padding-top: 4.75rem; padding-bottom: 6.5rem; }",
        "      .intro { padding: 4rem 0 0.35rem; }",
        "      h1 { font-size: clamp(2rem, 10vw, 2.95rem); max-width: 7.2ch; }",
        "      .lead { font-size: 0.98rem; max-width: 20rem; margin-top: 1.1rem; }",
        "      .meta-row { gap: 0.55rem; margin-top: 1.35rem; }",
        "      .meta-pill { width: 100%; justify-content: flex-start; padding: 0.8rem 0.95rem; }",
        "      .hero-actions, .card-actions { flex-direction: column; gap: 0.7rem; }",
        "      .button { width: 100%; min-height: 3.35rem; padding: 1rem 1.15rem; }",
        "      .hero-card { padding: 1.1rem; border-radius: 22px; }",
        "      .section-copy { line-height: 1.72; }",
        "      .stats { grid-template-columns: 1fr; gap: 0.7rem; }",
        "      .stat { padding: 0.95rem 1rem; }",
        "      .subscriptions-inner { padding-bottom: 0.25rem; }",
        "      .subscriptions-header { margin-bottom: 1.15rem; }",
        "      .subscriptions-header h2 { font-size: 1.7rem; }",
        "      .subscriptions-header p { margin-top: 0.7rem; line-height: 1.7; max-width: 18rem; }",
        "      .subscription-grid { gap: 0.85rem; }",
        "      .subscription-card { padding: 1.15rem; border-radius: 22px; }",
        "      .card-description { min-height: 0; margin-bottom: 0.9rem; line-height: 1.68; }",
        "      .subscription-url { margin-top: 0.85rem; }",
        "    }",
        "  </style>",
        "</head>",
        "<body>",
        '  <canvas id="three-scene" aria-hidden="true"></canvas>',
        '  <div class="orb orb-left" aria-hidden="true"></div>',
        '  <div class="orb orb-right" aria-hidden="true"></div>',
        '  <div class="chrome-nav" aria-hidden="false">',
        '    <div class="chrome-top"></div>',
        '    <div class="chrome-sides">',
        '      <button class="side-arrow" type="button" data-page-nav="prev" aria-label="Previous page"><span>‹</span></button>',
        '      <button class="side-arrow" type="button" data-page-nav="next" aria-label="Next page"><span>›</span></button>',
        '    </div>',
        '  </div>',
        '  <div class="page-shell">',
        '    <main class="page-viewport">',
        '      <div class="page-track" data-page-track>',
        '      <section class="page-panel page-panel-hero is-active" id="hero-content">',
        '        <div class="hero-panel">',
        '          <div class="intro">',
        '            <p class="kicker">有些日子，值得留下</p>',
        '            <h1>把重要的日子，留在眼前</h1>',
        '            <p class="lead">它们不必热闹。母亲节、父亲节这样的日子，也能被记住。</p>',
        '            <div class="meta-row">',
        '              <span class="meta-pill"><span class="meta-dot"></span>已经验证</span>',
        '              <span class="meta-pill"><span class="meta-dot"></span>按主题整理</span>',
        '              <span class="meta-pill"><span class="meta-dot"></span>适合长期放着</span>',
        '            </div>',
        '            <div class="hero-actions">',
        f'              <a class="button button-primary" href="{normalized}/all.ics">收下全部</a>',
        '              <button class="button button-secondary" type="button" data-page-jump="1">看看分类</button>',
        '            </div>',
        '          </div>',
        '          <aside class="hero-card">',
        '            <p class="section-label">被记住的日子</p>',
        '            <h2 class="section-title">想留下的，都在这里</h2>',
        '            <p class="section-copy">环保、阅读、节庆。慢慢放进生活。</p>',
        '            <div class="stats">',
        '              <div class="stat"><strong>4</strong><span>个入口</span></div>',
        '              <div class="stat"><strong>5 年</strong><span>一直看得到</span></div>',
        '              <div class="stat"><strong>0</strong><span>不与法定日重复</span></div>',
        '            </div>',
        '          </aside>',
        '        </div>',
      '      </section>',
      '      <section class="page-panel page-panel-subscriptions" id="subscriptions">',
        '        <div class="subscriptions-inner">',
          '          <div class="subscriptions section-fade">',
        '          <div class="subscriptions-header">',
        '            <h2>选一个留下</h2>',
        '            <p>全收下，或只留一部分。</p>',
        '          </div>',
        '          <div class="subscription-grid">',
        *cards,
        '          </div>',
        '          </div>',
        '        </div>',
        '      </section>',
        '      </div>',
        '    </main>',
        '  </div>',
        '  <div class="copy-toast" id="copy-toast" role="status" aria-live="polite">链接已复制</div>',
        '  <script type="module">',
        "    import * as THREE from 'https://unpkg.com/three@0.164.1/build/three.module.js';",
        "",
        "    class HolidayParticleField {",
        "      constructor(canvas) {",
        "        this.canvas = canvas;",
        "        this.prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;",
        "        this.pointer = { x: 0, y: 0 };",
        "        this.track = document.querySelector('[data-page-track]');",
        "        this.panels = [...document.querySelectorAll('.page-panel')];",
        "        this.navButtons = [...document.querySelectorAll('[data-page-nav]')];",
        "        this.jumpButtons = [...document.querySelectorAll('[data-page-jump]')];",
        "        this.copyButtons = [...document.querySelectorAll('[data-copy-url]')];",
        "        this.copyToast = document.getElementById('copy-toast');",
        "        this.pageIndex = 0;",
        "        this.wheelLocked = false;",
        "        this.touchStartX = 0;",
        "        this.touchStartY = 0;",
        "        this.toastTimer = null;",
        "        this.fadeSections = [...document.querySelectorAll('.section-fade')];",
        "        this.clock = new THREE.Clock();",
        "        this.scene = new THREE.Scene();",
        "        this.camera = new THREE.PerspectiveCamera(46, window.innerWidth / window.innerHeight, 0.1, 120);",
        "        this.camera.position.set(0, 0.2, 22);",
        "        this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true, alpha: true });",
        "        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));",
        "        this.renderer.setSize(window.innerWidth, window.innerHeight);",
        "        this.group = new THREE.Group();",
        "        this.scene.add(this.group);",
        "        this.scene.fog = new THREE.FogExp2(0x241b23, 0.025);",
        "",
        "        this.addLights();",
        "        this.createStars();",
        "        this.createConstellation();",
        "        this.createHalo();",
        "        this.handleResize = this.handleResize.bind(this);",
        "        this.handlePointerMove = this.handlePointerMove.bind(this);",
        "        this.handleKeydown = this.handleKeydown.bind(this);",
        "        this.handleWheel = this.handleWheel.bind(this);",
        "        this.handleTouchStart = this.handleTouchStart.bind(this);",
        "        this.handleTouchEnd = this.handleTouchEnd.bind(this);",
        "        this.handleCopyClick = this.handleCopyClick.bind(this);",
        "        window.addEventListener('resize', this.handleResize);",
        "        window.addEventListener('pointermove', this.handlePointerMove, { passive: true });",
        "        window.addEventListener('keydown', this.handleKeydown);",
        "        window.addEventListener('wheel', this.handleWheel, { passive: false });",
        "        this.track?.addEventListener('touchstart', this.handleTouchStart, { passive: true });",
        "        this.track?.addEventListener('touchend', this.handleTouchEnd, { passive: true });",
        "        this.navButtons.forEach((button) => button.addEventListener('click', () => this.movePage(button.dataset.pageNav === 'next' ? 1 : -1)));",
        "        this.jumpButtons.forEach((button) => button.addEventListener('click', () => this.goToPage(Number(button.dataset.pageJump) || 0)));",
        "        this.copyButtons.forEach((button) => button.addEventListener('click', this.handleCopyClick));",
        "        this.applyPageState();",
        "        this.render = this.render.bind(this);",
        "        this.render();",
        "      }",
        "",
        "      addLights() {",
        "        const ambient = new THREE.AmbientLight(0xdccfcc, 1.18);",
        "        const point = new THREE.PointLight(0x6f8f8b, 17, 100, 1.7);",
        "        point.position.set(2.8, 3.0, 13);",
        "        const rim = new THREE.PointLight(0xb8a6b8, 10, 84, 1.2);",
        "        rim.position.set(-5.5, -1.5, 7);",
        "        const moss = new THREE.PointLight(0x4d6b45, 7, 70, 1.1);",
        "        moss.position.set(0, 4, -4);",
        "        this.scene.add(ambient, point, rim, moss);",
        "      }",
        "",
        "      createStars() {",
        "        const count = window.innerWidth < 768 ? 3400 : 5600;",
        "        const positions = new Float32Array(count * 3);",
        "        const colors = new Float32Array(count * 3);",
        "        const sizes = new Float32Array(count);",
        "        const seeds = new Float32Array(count);",
        "        const color = new THREE.Color();",
        "        const palette = [0xcfc6cf, 0xb8a6b8, 0x7c9a74, 0x4d6b45, 0xe7ddd8, 0x6f8f8b];",
        "",
        "        for (let index = 0; index < count; index += 1) {",
        "          const stride = index * 3;",
        "          const radius = 6 + Math.random() * 28;",
        "          const angle = Math.random() * Math.PI * 2;",
        "          const spread = Math.pow(Math.random(), 0.72);",
        "          const height = (Math.random() - 0.5) * 18;",
        "          positions[stride] = Math.cos(angle) * radius * spread + (Math.random() - 0.5) * 1.6;",
        "          positions[stride + 1] = height;",
        "          positions[stride + 2] = (Math.random() - 0.5) * 30;",
        "          color.setHex(palette[Math.floor(Math.random() * palette.length)]);",
        "          color.offsetHSL((Math.random() - 0.5) * 0.03, 0, (Math.random() - 0.5) * 0.08);",
        "          colors[stride] = color.r;",
        "          colors[stride + 1] = color.g;",
        "          colors[stride + 2] = color.b;",
        "          sizes[index] = 0.22 + Math.random() * 0.9;",
        "          seeds[index] = Math.random() * 100;",
        "        }",
        "",
        "        const geometry = new THREE.BufferGeometry();",
        "        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));",
        "        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));",
        "        geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));",
        "        geometry.setAttribute('seed', new THREE.BufferAttribute(seeds, 1));",
        "",
        "        const material = new THREE.ShaderMaterial({",
        "          transparent: true,",
        "          depthWrite: false,",
        "          blending: THREE.AdditiveBlending,",
        "          vertexColors: true,",
        "          uniforms: { pixelRatio: { value: Math.min(window.devicePixelRatio || 1, 2) }, time: { value: 0 } },",
        "          vertexShader: `",
        "            attribute float size;",
        "            attribute float seed;",
        "            varying vec3 vColor;",
        "            uniform float pixelRatio;",
        "            uniform float time;",
        "            void main() {",
        "              vColor = color;",
        "              vec3 transformed = position;",
        "              transformed.x += sin(time * 0.17 + seed) * 0.06;",
        "              transformed.y += sin(time * 0.22 + seed * 1.7) * 0.12;",
        "              transformed.z += cos(time * 0.12 + seed * 0.8) * 0.24;",
        "              vec4 mvPosition = modelViewMatrix * vec4(transformed, 1.0);",
        "              float twinkle = 0.75 + 0.25 * sin(time * 1.8 + seed * 8.0);",
        "              gl_PointSize = size * twinkle * (220.0 / -mvPosition.z) * pixelRatio;",
        "              gl_Position = projectionMatrix * mvPosition;",
        "            }`,",
        "          fragmentShader: `",
        "            varying vec3 vColor;",
        "            void main() {",
        "              float distanceToCenter = length(gl_PointCoord - vec2(0.5));",
        "              float strength = smoothstep(0.52, 0.0, distanceToCenter);",
        "              strength *= 0.72 + 0.28 * smoothstep(0.18, 0.0, distanceToCenter);",
        "              gl_FragColor = vec4(vColor, strength * 0.82);",
        "            }`,",
        "        });",
        "",
        "        this.starField = new THREE.Points(geometry, material);",
        "        this.group.add(this.starField);",
        "      }",
        "",
        "      createConstellation() {",
        "        const geometry = new THREE.BufferGeometry();",
        "        const positions = new Float32Array([",
        "          -6.4,  1.9,  1.8,   -3.0,  0.7, -0.9,",
        "          -3.0,  0.7, -0.9,   -0.5,  2.8, -2.2,",
        "          -0.5,  2.8, -2.2,    2.6,  0.6, -0.7,",
        "           2.6,  0.6, -0.7,    5.7, -1.2,  1.4,",
        "          -1.3, -1.7,  0.4,    1.8, -3.0, -1.8,",
        "        ]);",
        "        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));",
        "        const material = new THREE.LineBasicMaterial({ color: 0xcfc6cf, transparent: true, opacity: 0.16 });",
        "        this.constellation = new THREE.LineSegments(geometry, material);",
        "        this.scene.add(this.constellation);",
        "",
        "        const nodeGeometry = new THREE.SphereGeometry(0.06, 14, 14);",
        "        const nodeMaterial = new THREE.MeshBasicMaterial({ color: 0xe7ddd8, transparent: true, opacity: 0.82 });",
        "        const nodes = [",
        "          [-6.4, 1.9, 1.8], [-3.0, 0.7, -0.9], [-0.5, 2.8, -2.2], [2.6, 0.6, -0.7], [5.7, -1.2, 1.4], [-1.3, -1.7, 0.4], [1.8, -3.0, -1.8],",
        "        ];",
        "        nodes.forEach(([x, y, z]) => {",
        "          const mesh = new THREE.Mesh(nodeGeometry, nodeMaterial);",
        "          mesh.position.set(x, y, z);",
        "          this.scene.add(mesh);",
        "        });",
        "",
        "        const archCurve = new THREE.EllipseCurve(0, -0.3, 6.8, 5.6, Math.PI * 1.02, Math.PI * 1.98, false, 0);",
        "        const archPoints = archCurve.getPoints(120).map((point) => new THREE.Vector3(point.x, point.y, -3.6));",
        "        const archGeometry = new THREE.BufferGeometry().setFromPoints(archPoints);",
        "        const archMaterial = new THREE.LineBasicMaterial({ color: 0x7c9a74, transparent: true, opacity: 0.14 });",
        "        this.archway = new THREE.Line(archGeometry, archMaterial);",
        "        this.scene.add(this.archway);",
        "      }",
        "",
        "      createHalo() {",
        "        const haloGeometry = new THREE.TorusGeometry(7.3, 0.04, 16, 180);",
        "        const haloMaterial = new THREE.MeshBasicMaterial({ color: 0x6f8f8b, transparent: true, opacity: 0.13 });",
        "        this.halo = new THREE.Mesh(haloGeometry, haloMaterial);",
        "        this.halo.rotation.x = Math.PI / 2.4;",
        "        this.halo.rotation.y = Math.PI / 10;",
        "        this.scene.add(this.halo);",
        "      }",
        "",
        "      handleResize() {",
        "        this.camera.aspect = window.innerWidth / window.innerHeight;",
        "        this.camera.updateProjectionMatrix();",
        "        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));",
        "        this.renderer.setSize(window.innerWidth, window.innerHeight);",
        "        this.applyPageState();",
        "        if (this.starField?.material?.uniforms?.pixelRatio) {",
        "          this.starField.material.uniforms.pixelRatio.value = Math.min(window.devicePixelRatio || 1, 2);",
        "        }",
        "      }",
        "",
        "      handlePointerMove(event) {",
        "        this.pointer.x = (event.clientX / window.innerWidth) * 2 - 1;",
        "        this.pointer.y = -((event.clientY / window.innerHeight) * 2 - 1);",
        "      }",
        "",
        "      handleKeydown(event) {",
        "        if (event.key === 'ArrowRight') this.movePage(1);",
        "        if (event.key === 'ArrowLeft') this.movePage(-1);",
        "      }",
        "",
        "      handleTouchStart(event) {",
        "        const touch = event.changedTouches?.[0];",
        "        if (!touch) return;",
        "        this.touchStartX = touch.clientX;",
        "        this.touchStartY = touch.clientY;",
        "      }",
        "",
        "      handleTouchEnd(event) {",
        "        const touch = event.changedTouches?.[0];",
        "        if (!touch) return;",
        "        const deltaX = touch.clientX - this.touchStartX;",
        "        const deltaY = touch.clientY - this.touchStartY;",
        "        if (Math.abs(deltaX) < 48 || Math.abs(deltaX) <= Math.abs(deltaY)) return;",
        "        this.movePage(deltaX < 0 ? 1 : -1);",
        "      }",
        "",
        "      handleWheel(event) {",
        "        if (this.wheelLocked) return;",
        "        const dominantDelta = Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY;",
        "        if (Math.abs(dominantDelta) < 22) return;",
        "        event.preventDefault();",
        "        this.wheelLocked = true;",
        "        this.movePage(dominantDelta > 0 ? 1 : -1);",
        "        window.setTimeout(() => { this.wheelLocked = false; }, 820);",
        "      }",
        "",
        "      async handleCopyClick(event) {",
        "        const url = event.currentTarget.dataset.copyUrl || '';",
        "        if (!url) return;",
        "        try {",
        "          await navigator.clipboard.writeText(url);",
        "          this.showToast('链接已复制');",
        "        } catch (error) {",
        "          this.showToast('复制失败，请手动复制');",
        "        }",
        "      }",
        "",
        "      showToast(message) {",
        "        if (!this.copyToast) return;",
        "        this.copyToast.textContent = message;",
        "        this.copyToast.classList.add('is-visible');",
        "        if (this.toastTimer) window.clearTimeout(this.toastTimer);",
        "        this.toastTimer = window.setTimeout(() => {",
        "          this.copyToast.classList.remove('is-visible');",
        "        }, 1800);",
        "      }",
        "",
        "      movePage(delta) {",
        "        this.goToPage(this.pageIndex + delta);",
        "      }",
        "",
        "      goToPage(nextIndex) {",
        "        const clampedIndex = Math.max(0, Math.min(this.panels.length - 1, nextIndex));",
        "        if (clampedIndex === this.pageIndex) return;",
        "        this.pageIndex = clampedIndex;",
        "        this.applyPageState();",
        "      }",
        "",
        "      applyPageState() {",
        "        if (this.track) {",
        "          this.track.style.transform = `translate3d(${-100 * this.pageIndex}vw, 0, 0)`;",
        "        }",
        "        this.panels.forEach((panel, index) => {",
        "          const isActive = index === this.pageIndex;",
        "          panel.classList.toggle('is-active', isActive);",
        "          panel.setAttribute('aria-hidden', String(!isActive));",
        "          panel.querySelectorAll('.section-fade').forEach((section) => section.classList.toggle('is-visible', isActive));",
        "        });",
        "        this.navButtons.forEach((button) => {",
        "          const isPrev = button.dataset.pageNav === 'prev';",
        "          button.disabled = isPrev ? this.pageIndex === 0 : this.pageIndex === this.panels.length - 1;",
        "          button.style.opacity = button.disabled ? '0.28' : '1';",
        "        });",
        "      }",
        "",
        "      render() {",
        "        const elapsed = this.clock.getElapsedTime();",
        "        const motion = this.prefersReducedMotion ? 0.18 : 1;",
        "        if (this.starField?.material?.uniforms?.time) {",
        "          this.starField.material.uniforms.time.value = elapsed;",
        "        }",
        "        this.group.rotation.y = elapsed * 0.02 * motion + this.pointer.x * 0.06;",
        "        this.group.rotation.x = Math.sin(elapsed * 0.11) * 0.04 * motion + this.pointer.y * 0.035;",
        "        this.group.position.x = this.pointer.x * 0.42;",
        "        this.group.position.y = this.pointer.y * 0.24;",
        "        this.group.position.z = Math.sin(elapsed * 0.18) * 0.45 * motion;",
        "        this.constellation.rotation.z = elapsed * 0.02 * motion;",
        "        this.constellation.rotation.y = elapsed * 0.045 * motion;",
        "        this.halo.rotation.z = elapsed * 0.05 * motion;",
        "        this.halo.rotation.y = Math.PI / 10 + Math.sin(elapsed * 0.24) * 0.09 * motion;",
        "        if (this.archway) {",
        "          this.archway.rotation.z = Math.sin(elapsed * 0.12) * 0.025 * motion;",
        "          this.archway.position.y = Math.sin(elapsed * 0.2) * 0.16 * motion;",
        "        }",
        "        this.camera.position.z = 22 - Math.sin(elapsed * 0.16) * 0.45 * motion;",
        "        this.renderer.render(this.scene, this.camera);",
        "        if (!this.prefersReducedMotion) {",
        "          requestAnimationFrame(this.render);",
        "        }",
        "      }",
        "    }",
        "",
        "    new HolidayParticleField(document.getElementById('three-scene'));",
        "  </script>",
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
