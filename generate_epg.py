import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, date, timezone
from lxml import etree
import os

BASE_URL = "https://kvf.fo/nskra/sv"
DAYS = 7


def xmltv_timestamp(dt: datetime):
    return dt.strftime("%Y%m%d%H%M%S %z")

root = etree.Element(
    "tv",
    attrib={
        "source-info-url": "https://github.com/martindidriksen/kvf-epg",
        "generator-info-name": "KVF EPG Scraper"
    }
)

channel = etree.SubElement(root, "channel", id="kvf.fo")
display = etree.SubElement(channel, "display-name")
display.text = "KVF"
events = []
today = date.today()

for offset in range(DAYS):

    day = today + timedelta(days=offset)
    url = f"{BASE_URL}?date={day.isoformat()}"

    r = requests.get(
        url,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    for entry in soup.select("div.views-row"):

        normal = entry.select_one(".s-normal")
        if not normal:
            continue

        raw_time = normal.find(string=True)
        if not raw_time:
            continue

        time_str = raw_time.strip()
        if ":" not in time_str:
            continue

        title_el = entry.select_one(".s-heiti")
        if not title_el:
            continue

        subtitle_el = entry.select_one(".s-subtitle")
        desc_el = entry.select_one(".s-text")

        hour, minute = map(int, time_str.split(":"))

        local_dt = datetime(
            year=day.year,
            month=day.month,
            day=day.day,
            hour=hour,
            minute=minute
        )

        utc_dt = local_dt.replace(tzinfo=timezone.utc)

        events.append({
            "dt": utc_dt,
            "title": title_el.get_text(" ", strip=True),
            "subtitle": subtitle_el.get_text(" ", strip=True) if subtitle_el else "",
            "desc": desc_el.get_text(" ", strip=True) if desc_el else ""
        })


events.sort(key=lambda x: x["dt"])


for i, e in enumerate(events):

    start_dt = e["dt"]

    if i < len(events) - 1:
        stop_dt = events[i + 1]["dt"]
    else:
        stop_dt = start_dt + timedelta(hours=1)

    programme = etree.SubElement(
        root,
        "programme",
        start=xmltv_timestamp(start_dt),
        stop=xmltv_timestamp(stop_dt),
        channel="kvf.fo"
    )

    title = etree.SubElement(programme, "title")
    title.text = e["title"]

    if e["subtitle"]:
        sub = etree.SubElement(programme, "sub-title")
        sub.text = e["subtitle"]

    if e["desc"]:
        desc = etree.SubElement(programme, "desc")
        desc.text = e["desc"]



tmp_file = "kvf.xml.tmp"
final_file = "kvf.xml"

with open(tmp_file, "wb") as f:
    f.write(
        etree.tostring(
            root,
            pretty_print=True,
            xml_declaration=True,
            encoding="UTF-8"
        )
    )

os.replace(tmp_file, final_file)

print(f"Generated kvf.xml successfully with {len(events)} events")