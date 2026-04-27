import json
import os
import re
import requests
from datetime import datetime, timedelta, date, timezone
from lxml import etree

BASE_URL = "https://www.ruv.is/sjonvarp/dagskra/ruv"
DAYS = 7

CHANNELS = [
    {"api": "ruv", "id": "ruv.is", "display": "RÚV 1", "out": "ruv.xml"},
    {"api": "ruv2", "id": "ruv2.is", "display": "RÚV 2", "out": "ruv2.xml"},
]

APOLLO_RE = re.compile(
    r'<script[^>]*id="apollo"[^>]*>window\.__APOLLO_STATE__\s*=\s*(\{.*?\});?</script>',
    re.DOTALL,
)


def xmltv_timestamp(dt: datetime):
    return dt.strftime("%Y%m%d%H%M%S %z")


def fetch_apollo_state(day: date) -> dict:
    url = f"{BASE_URL}/{day.isoformat()}"
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    m = APOLLO_RE.search(r.text)
    if not m:
        raise RuntimeError(f"Apollo state not found at {url}")
    return json.loads(m.group(1))


def parse_hhmm(s: str):
    hour, minute = map(int, s.split(":"))
    return hour, minute


def collect_events(state: dict, api_channel: str, day: date):
    schedule_key = f'Schedule({{"channel":"{api_channel}","date":"{day.isoformat()}"}})'
    refs = state["ROOT_QUERY"].get(schedule_key, {}).get("events", [])

    events = []
    prev_start_minutes = -1
    day_offset = 0

    for ref in refs:
        item = state[ref["__ref"]]

        if item.get("is_header"):
            continue

        start_str = item.get("start_time_friendly")
        end_str = item.get("end_time_friendly")
        if not start_str or not end_str or start_str == end_str:
            continue

        sh, sm = parse_hhmm(start_str)
        eh, em = parse_hhmm(end_str)

        start_minutes = sh * 60 + sm
        if start_minutes < prev_start_minutes:
            day_offset += 1
        prev_start_minutes = start_minutes

        start_dt = datetime(day.year, day.month, day.day, sh, sm, tzinfo=timezone.utc) + timedelta(days=day_offset)
        end_dt = datetime(day.year, day.month, day.day, eh, em, tzinfo=timezone.utc) + timedelta(days=day_offset)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)

        events.append({
            "start": start_dt,
            "stop": end_dt,
            "title": item.get("title") or "",
            "subtitle": item.get("subtitle") or "",
            "desc": item.get("description") or "",
        })

    return events


def build_xml(channel: dict, events: list):
    root = etree.Element(
        "tv",
        attrib={
            "source-info-url": "https://github.com/martindidriksen/kvf-epg",
            "generator-info-name": "RUV EPG Scraper",
        },
    )

    ch = etree.SubElement(root, "channel", id=channel["id"])
    display = etree.SubElement(ch, "display-name")
    display.text = channel["display"]

    seen = set()
    for e in events:
        key = (e["start"], e["title"])
        if key in seen:
            continue
        seen.add(key)

        programme = etree.SubElement(
            root,
            "programme",
            start=xmltv_timestamp(e["start"]),
            stop=xmltv_timestamp(e["stop"]),
            channel=channel["id"],
        )

        title = etree.SubElement(programme, "title")
        title.text = e["title"]

        if e["subtitle"]:
            sub = etree.SubElement(programme, "sub-title")
            sub.text = e["subtitle"]

        if e["desc"]:
            desc = etree.SubElement(programme, "desc")
            desc.text = e["desc"]

    return root


today = date.today()
states = {}
for offset in range(DAYS):
    day = today + timedelta(days=offset)
    states[day] = fetch_apollo_state(day)

for channel in CHANNELS:
    all_events = []
    for day, state in states.items():
        all_events.extend(collect_events(state, channel["api"], day))
    all_events.sort(key=lambda e: e["start"])

    root = build_xml(channel, all_events)

    tmp_file = channel["out"] + ".tmp"
    with open(tmp_file, "wb") as f:
        f.write(
            etree.tostring(
                root,
                pretty_print=True,
                xml_declaration=True,
                encoding="UTF-8",
            )
        )
    os.replace(tmp_file, channel["out"])

    print(f"Generated {channel['out']} successfully with {len(all_events)} events")
