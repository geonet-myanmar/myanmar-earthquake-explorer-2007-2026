#!/usr/bin/env python3
"""Export the TMD regional archive and GEM faults intersecting Myanmar."""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
TMD = "https://earthquake.tmd.go.th/inside.html"
GEM_COMMIT = "56816508ad92fd6846dad1163b1c8c01376a2cd1"
BOUNDARY_COMMIT = "9380cca83db5f9aef52d5e762765100745f84b27"
GEM_URL = f"https://raw.githubusercontent.com/GEMScienceTools/gem-global-active-faults/{GEM_COMMIT}/geojson/gem_active_faults.geojson"
BOUNDARY_URL = f"https://raw.githubusercontent.com/nvkelso/natural-earth-vector/{BOUNDARY_COMMIT}/geojson/ne_10m_admin_0_countries.geojson"
PAGE_SIZE = 200
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "MyanmarEarthquakeDashboard/1.0 (public data research)"


def get(url, **kwargs):
    for attempt in range(4):
        try:
            response = SESSION.get(url, timeout=90, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(2**attempt)


def number(text):
    text = text.strip().replace(",", "")
    if not text or text in {"-", "–"}:
        return None
    return float(text)


def parse_page(html):
    soup = BeautifulSoup(html, "html.parser")
    match = re.search(r"เหตุการณ์ที่\s+(\d+)\s+to\s+(\d+)\s+of\s+(\d+)", soup.get_text(" ", strip=True))
    if not match:
        raise ValueError("TMD page has no archive pagination summary")
    start, end, total = map(int, match.groups())
    rows = []
    for row in soup.select("tr[onclick^=\"window.open('/EQ\"]"):
        event_id = re.search(r"/EQ(\d+)", row["onclick"]).group(1)
        cells = row.find_all("td", recursive=False)
        if len(cells) < 7:
            raise ValueError(f"Incomplete TMD row {event_id}")
        values = [cell.get_text(" ", strip=True) for cell in cells]
        dates = re.findall(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", values[0])
        if len(dates) != 2:
            raise ValueError(f"Unexpected origin times for {event_id}: {values[0]}")
        location = cells[6].get_text(" | ", strip=True).split(" | ")
        rows.append({
            "id": event_id,
            "time_utc": dates[1].replace(" ", "T") + "Z",
            "time_thailand": dates[0].replace(" ", "T") + "+07:00",
            "magnitude": number(values[1]),
            "latitude": number(values[2]),
            "longitude": number(values[3]),
            "depth_km": number(values[4]),
            "phase_count": number(values[5]),
            "region_th": location[0] if location else "",
            "region_en": " ".join(location[1:]),
            "felt": bool(row.select_one('img[src*="peq6"]')),
            "source_url": f"https://earthquake.tmd.go.th/EQ{event_id}",
        })
    if len(rows) != end - start + 1:
        raise ValueError(f"TMD page expected {end - start + 1} rows, found {len(rows)}")
    return start, end, total, rows


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")


def main():
    retrieved = datetime.now(timezone.utc).isoformat(timespec="seconds")
    start, end, total, first = parse_page(get(TMD, params={"ps": PAGE_SIZE, "pageNum_thaievent": 0}).text)
    if start != 1:
        raise ValueError("Archive did not start at row 1")
    rows = first
    for page in range(1, (total + PAGE_SIZE - 1) // PAGE_SIZE):
        time.sleep(0.2)
        page_start, page_end, page_total, batch = parse_page(
            get(TMD, params={"ps": PAGE_SIZE, "pageNum_thaievent": page}).text
        )
        if page_total != total or page_start != page * PAGE_SIZE + 1:
            raise ValueError("TMD archive changed during download; retry for a consistent snapshot")
        rows.extend(batch)
        print(f"TMD archive: {page_end}/{total}", flush=True)
    ids = {row["id"] for row in rows}
    if len(rows) != total or len(ids) != total:
        raise ValueError("TMD archive contains duplicate or missing events")
    if parse_page(get(TMD, params={"ps": PAGE_SIZE, "pageNum_thaievent": 0}).text)[3][0]["id"] != rows[0]["id"]:
        raise ValueError("TMD archive changed during download; retry for a consistent snapshot")

    selected = [row for row in rows if re.search(r"เมียนมา|พม่า|myanmar|burma", row["region_th"] + " " + row["region_en"], re.I)]
    features = []
    for row in selected:
        lon, lat = row.pop("longitude"), row.pop("latitude")
        if lon is None or lat is None:
            raise ValueError(f"Missing coordinates for Myanmar event {row['id']}")
        features.append({"type": "Feature", "id": row["id"], "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": row})
    earthquakes = {
        "type": "FeatureCollection",
        "metadata": {
            "source": TMD,
            "retrieved_utc": retrieved,
            "selection": "Archive region label contains Myanmar, Burma, เมียนมา or พม่า.",
            "coverage": "TMD regional archive, 2–25°N and 92–110°E; coordinates are rounded to 0.01° in the archive.",
            "regional_rows_scanned": total,
        },
        "features": features,
    }

    boundary_data = get(BOUNDARY_URL).json()
    boundary_feature = next(f for f in boundary_data["features"] if f["properties"].get("ISO_A3") == "MMR")
    boundary = shape(boundary_feature["geometry"])
    gem = get(GEM_URL).json()
    faults = [f for f in gem["features"] if f.get("geometry") and shape(f["geometry"]).intersects(boundary)]
    fault_collection = {
        "type": "FeatureCollection",
        "metadata": {
            "source": GEM_URL,
            "retrieved_utc": retrieved,
            "selection": "Original GEM traces intersecting the Natural Earth 1:10m Myanmar polygon; full traces retained.",
            "boundary_source": BOUNDARY_URL,
            "license": "CC BY-SA 4.0",
            "citation": "Styron, R. and Pagani, M. (2020), The GEM Global Active Faults Database, Earthquake Spectra 36(1_suppl), 160–180. https://doi.org/10.1177/8755293020944182",
        },
        "features": faults,
    }
    write_json(ROOT / "data" / "myanmar-earthquakes.geojson", earthquakes)
    write_json(ROOT / "data" / "myanmar-active-faults.geojson", fault_collection)
    print(f"Exported {len(features)} Myanmar events and {len(faults)} intersecting fault traces.")


if __name__ == "__main__":
    main()
