"""Saved GeoNames US postal locations for ZIP pins and city/state search."""

import argparse
import csv
import io
import math
import re
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "zip_places.csv"
SOURCE_URL = "https://download.geonames.org/export/zip/US.zip"


def normalize(value):
    return " ".join(re.sub(r"[^\w\s]", " ", value.casefold()).split())


def download_locations(path=DATA_PATH):
    """Explicit setup command; the public app never downloads this on startup."""
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "LendwardDealerMap/1.0"})
    with urllib.request.urlopen(request, timeout=45) as response:
        archive = response.read()
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        content = zipped.read("US.txt").decode("utf-8")
    rows = []
    for parts in csv.reader(io.StringIO(content), delimiter="\t"):
        lat, lon = float(parts[9]), float(parts[10])
        if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("GeoNames returned invalid coordinates")
        rows.append([parts[1], parts[2], parts[4], parts[3], lat, lon])
    if len(rows) < 30000:
        raise ValueError("GeoNames returned an unexpectedly small US postal dataset")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["zip", "city", "state", "state_name", "latitude", "longitude"])
        writer.writerows(rows)
    temporary.replace(path)
    print(f"Saved {len(rows):,} US postal locations to {path}")


def load_locations(path=DATA_PATH):
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    zip_groups, city_groups = defaultdict(list), defaultdict(list)
    for row in rows:
        row["latitude"] = float(row["latitude"])
        row["longitude"] = float(row["longitude"])
        zip_groups[row["zip"]].append(row)
        city_groups[(row["city"], row["state"])].append(row)
    cities = []
    for (city, state), group in sorted(city_groups.items()):
        cities.append({
            "label": f"{city}, {state}",
            "search": normalize(f"{city} {state} {group[0]['state_name']}"),
            "latitude": sum(r["latitude"] for r in group) / len(group),
            "longitude": sum(r["longitude"] for r in group) / len(group),
        })
    return dict(zip_groups), cities


def zip_location(zip_code, state, zip_groups):
    matches = [row for row in zip_groups.get(zip_code, []) if row["state"] == state]
    if not matches:
        return None
    return {
        "city": " / ".join(sorted({row["city"] for row in matches})),
        "latitude": sum(row["latitude"] for row in matches) / len(matches),
        "longitude": sum(row["longitude"] for row in matches) / len(matches),
    }


def search_places(query, zip_groups, cities):
    query = normalize(query)
    if not query:
        return []
    if query.isdigit():
        return [{**row, "label": f"{row['zip']} - {row['city']}, {row['state']}"}
                for row in zip_groups.get(query.zfill(5), [])]
    tokens = query.split()
    matches = [city for city in cities if all(token in city["search"].split() for token in tokens)]
    return sorted(matches, key=lambda city: (normalize(city["label"]) != query, city["label"]))[:50]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", required=True)
    parser.parse_args()
    download_locations()
