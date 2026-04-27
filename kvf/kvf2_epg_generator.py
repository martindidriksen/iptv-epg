import os
from datetime import datetime, timedelta, date, timezone
from lxml import etree

CHANNEL_ID = "kvf2.fo"
DISPLAY = "KVF 2"
PLACEHOLDER_TITLE = "Onki á skrá"
DAYS = 7
OUT = "kvf2.xml"


def xmltv_timestamp(dt: datetime):
    return dt.strftime("%Y%m%d%H%M%S %z")


root = etree.Element(
    "tv",
    attrib={
        "source-info-url": "https://github.com/martindidriksen/kvf-epg",
        "generator-info-name": "KVF2 placeholder EPG",
    },
)

channel = etree.SubElement(root, "channel", id=CHANNEL_ID)
display = etree.SubElement(channel, "display-name")
display.text = DISPLAY

today = date.today()
for offset in range(DAYS):
    day = today + timedelta(days=offset)
    start_dt = datetime(day.year, day.month, day.day, 0, 0, tzinfo=timezone.utc)
    stop_dt = start_dt + timedelta(days=1)

    programme = etree.SubElement(
        root,
        "programme",
        start=xmltv_timestamp(start_dt),
        stop=xmltv_timestamp(stop_dt),
        channel=CHANNEL_ID,
    )

    title = etree.SubElement(programme, "title")
    title.text = PLACEHOLDER_TITLE

tmp = OUT + ".tmp"
with open(tmp, "wb") as f:
    f.write(
        etree.tostring(
            root,
            pretty_print=True,
            xml_declaration=True,
            encoding="UTF-8",
        )
    )
os.replace(tmp, OUT)

print(f"Generated {OUT} with {DAYS} placeholder entries")
