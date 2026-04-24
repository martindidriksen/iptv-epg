import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from lxml import etree

URL = "https://kvf.fo/nskra/sv"

def xmltv_timestamp(dt):
    return dt.strftime("%Y%m%d%H%M%S %z")


# ---- Fetch HTML ----

r = requests.get(
    URL,
    timeout=30,
    headers={
        "User-Agent": "Mozilla/5.0"
    }
)

r.raise_for_status()

soup = BeautifulSoup(r.text, "html.parser")


# ---- Parse schedule rows ----

rows = []

for entry in soup.select("div.views-row"):

    normal = entry.select_one(".s-normal")
    if not normal:
        continue

    # first text node in s-normal is the time (e.g. 19:30)
    raw_time = normal.find(string=True)

    if not raw_time:
        continue

    start_time = raw_time.strip()

    if ":" not in start_time:
        continue

    title_el = entry.select_one(".s-heiti")
    if not title_el:
        continue

    title = title_el.get_text(" ", strip=True)

    subtitle_el = entry.select_one(".s-subtitle")
    subtitle = (
        subtitle_el.get_text(" ", strip=True)
        if subtitle_el else ""
    )

    desc_el = entry.select_one(".s-text")
    desc = (
        desc_el.get_text(" ", strip=True)
        if desc_el else ""
    )

    rows.append({
        "time": start_time,
        "title": title,
        "subtitle": subtitle,
        "desc": desc
    })


# ---- Safety check ----

if len(rows) < 5:
    raise Exception(
        f"Scrape likely failed, only found {len(rows)} programs"
    )


# ---- Build XMLTV ----

root = etree.Element(
    "tv",
    attrib={
        "source-info-url": "https://github.com/martindidriksen/kvf-epg",
        "generator-info-name": "KVF EPG Scraper"
    }
)

channel = etree.SubElement(
    root,
    "channel",
    id="kvf.fo"
)

display = etree.SubElement(
    channel,
    "display-name"
)

display.text = "KVF"


# Use Faroe timezone (handles DST)
tz = ZoneInfo("Atlantic/Faroe")
today = datetime.now(tz).date()


for i, p in enumerate(rows):

    hour, minute = map(int, p["time"].split(":"))

    start_dt = datetime.combine(
        today,
        datetime.min.time(),
        tzinfo=tz
    ) + timedelta(
        hours=hour,
        minutes=minute
    )

    # stop time = next show's start
    if i < len(rows)-1:

        nh, nm = map(
            int,
            rows[i+1]["time"].split(":")
        )

        stop_dt = datetime.combine(
            today,
            datetime.min.time(),
            tzinfo=tz
        ) + timedelta(
            hours=nh,
            minutes=nm
        )

        # handle midnight rollover
        if stop_dt <= start_dt:
            stop_dt += timedelta(days=1)

    else:
        # fallback for last program
        stop_dt = start_dt + timedelta(hours=1)


    programme = etree.SubElement(
        root,
        "programme",
        start=xmltv_timestamp(start_dt),
        stop=xmltv_timestamp(stop_dt),
        channel="kvf.fo"
    )

    title = etree.SubElement(
        programme,
        "title"
    )
    title.text = p["title"]

    if p["subtitle"]:
        sub = etree.SubElement(
            programme,
            "sub-title"
        )
        sub.text = p["subtitle"]

    if p["desc"]:
        desc = etree.SubElement(
            programme,
            "desc"
        )
        desc.text = p["desc"]


# ---- Write atomically ----

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

import os
os.replace(tmp_file, final_file)

print("Generated kvf.xml successfully")