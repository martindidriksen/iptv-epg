import os
import requests
from datetime import datetime, timedelta, date, timezone
from lxml import etree

API_URL = "https://production-cdn.dr-massive.com/api/schedules"
DAYS = 7

CHANNELS = [
    {"channel_id": "20875", "id": "dr1.dk", "display": "DR1", "out": "dr1.xml"},
    {"channel_id": "20876", "id": "dr2.dk", "display": "DR2", "out": "dr2.xml"},
    {"channel_id": "192099", "id": "drtva.dk", "display": "DR TVA", "out": "drtva.xml"},
]


def xmltv_timestamp(dt: datetime):
    return dt.strftime("%Y%m%d%H%M%S %z")


def parse_iso_z(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def fetch_day(channel_id: str, day: date) -> list:
    params = {
        "channels": channel_id,
        "date": day.isoformat(),
        "hour": 0,
        "duration": 24,
        "segments": "drtv",
        "device": "web_browser",
        "sub": "anonymous",
    }
    r = requests.get(
        API_URL,
        params=params,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
    )
    r.raise_for_status()
    data = r.json()
    if not data:
        return []
    return data[0].get("schedules", []) or []


def collect_events(channel_id: str) -> list:
    events = []
    today = date.today()
    for offset in range(DAYS):
        day = today + timedelta(days=offset)
        for s in fetch_day(channel_id, day):
            item = s.get("item") or {}
            title = item.get("title") or ""
            if not title:
                continue
            events.append({
                "start": parse_iso_z(s["startDate"]),
                "stop": parse_iso_z(s["endDate"]),
                "title": title,
                "desc": item.get("description") or item.get("shortDescription") or "",
                "season": item.get("seasonNumber"),
                "episode": item.get("episodeNumber"),
            })
    return events


def build_xml(channel: dict, events: list):
    root = etree.Element(
        "tv",
        attrib={
            "source-info-url": "https://github.com/martindidriksen/kvf-epg",
            "generator-info-name": "DR EPG Scraper",
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

        if e["desc"]:
            desc = etree.SubElement(programme, "desc")
            desc.text = e["desc"]

        if e["season"] and e["episode"]:
            ep = etree.SubElement(programme, "episode-num", system="xmltv_ns")
            ep.text = f"{int(e['season']) - 1}.{int(e['episode']) - 1}.0"

    return root


for channel in CHANNELS:
    events = collect_events(channel["channel_id"])
    events.sort(key=lambda e: e["start"])

    root = build_xml(channel, events)

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

    print(f"Generated {channel['out']} successfully with {len(events)} events")
