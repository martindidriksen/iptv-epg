import os
from lxml import etree

SOURCES = [
    "kvf/kvf.xml",
    "kvf/kvf2.xml",
    "ruv/ruv.xml",
    "ruv/ruv2.xml",
    "dr/dr1.xml",
    "dr/dr2.xml",
    "dr/drtva.xml",
]

OUT = "epg.xml"


root = etree.Element(
    "tv",
    attrib={
        "source-info-url": "https://github.com/martindidriksen/kvf-epg",
        "generator-info-name": "Combined EPG",
    },
)

channels = []
programmes = []

for path in SOURCES:
    if not os.path.exists(path):
        print(f"Skipping missing file: {path}")
        continue

    tree = etree.parse(path)
    src = tree.getroot()

    for ch in src.findall("channel"):
        ch.tail = None
        channels.append(ch)
    for pr in src.findall("programme"):
        pr.tail = None
        programmes.append(pr)

for ch in channels:
    root.append(ch)
for pr in programmes:
    root.append(pr)

etree.indent(root, space="  ")

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

print(
    f"Generated {OUT} with {len(channels)} channels and {len(programmes)} programmes"
)
