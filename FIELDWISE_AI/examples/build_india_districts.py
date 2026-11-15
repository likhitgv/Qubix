"""Build config/india_districts.csv (state, district, centre) from Census 2011 boundaries.

Source : datameet/maps  Districts/Census_2011/2011_Dist.shp + 2011_Dist.dbf
         https://github.com/datameet/maps (public boundary data, India Census 2011)
Output : config/india_districts.csv   columns: state, district, latitude, longitude
         config/india_districts_provenance.json

Run (needs `pip install pyshp`, a build-time tool only):
    py -3.11 -m examples.build_india_districts <path-to>/2011_Dist

Pass the path WITHOUT the extension. The centre is the area-weighted centroid of the
district polygon in degrees; it is a reference point for looking up the nearest NASA
grid cell, not a claim about where farms are.

Known limits of the 2011 boundaries: Telangana districts are listed under Andhra
Pradesh, districts created after 2011 are missing, and some names use pre-2014
spellings. A few spellings are corrected below; everything else is left as in source.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import shapefile  # pyshp

ROOT = Path(__file__).resolve().parents[1]
OUT_CSV = ROOT / "config" / "india_districts.csv"
OUT_PROVENANCE = ROOT / "config" / "india_districts_provenance.json"

STATE_FIXES = {
    "Arunanchal Pradesh": "Arunachal Pradesh",
    "Dadara & Nagar Havelli": "Dadra & Nagar Haveli",
    "Andaman & Nicobar Island": "Andaman & Nicobar Islands",
    "NCT of Delhi": "Delhi",
}

# Official renamings that matter for the five districts KAIRO validated (Karnataka, 2014).
DISTRICT_FIXES = {
    ("Karnataka", "Bellary"): "Ballari",
    ("Karnataka", "Shimoga"): "Shivamogga",
    ("Karnataka", "Bijapur"): "Vijayapura",
    ("Karnataka", "Belgaum"): "Belagavi",
}


def ring_centroid(points: list[tuple[float, float]]) -> tuple[float, float, float]:
    """Return (signed_area, cx, cy) of a closed ring using the shoelace formula."""
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    a *= 0.5
    if a == 0:
        xs, ys = zip(*points)
        return 0.0, sum(xs) / len(xs), sum(ys) / len(ys)
    return a, cx / (6 * a), cy / (6 * a)


def shape_centroid(shape) -> tuple[float, float]:
    """Area-weighted centroid over all rings; holes (opposite sign) subtract naturally."""
    pts = shape.points
    bounds = list(shape.parts) + [len(pts)]
    total = wx = wy = 0.0
    for start, end in zip(bounds, bounds[1:]):
        ring = pts[start:end]
        if len(ring) < 3:
            continue
        a, cx, cy = ring_centroid(ring)
        total += a
        wx += a * cx
        wy += a * cy
    if total == 0:
        west, south, east, north = shape.bbox
        return (south + north) / 2, (west + east) / 2
    return wy / total, wx / total  # latitude, longitude


def main(base: str) -> None:
    reader = shapefile.Reader(shp=open(base + ".shp", "rb"), dbf=open(base + ".dbf", "rb"))
    names = [f[0] for f in reader.fields[1:]]
    rows = []
    for shape_record in reader.iterShapeRecords():
        rec = dict(zip(names, shape_record.record))
        state = STATE_FIXES.get(rec["ST_NM"], rec["ST_NM"]).strip()
        district = DISTRICT_FIXES.get((state, rec["DISTRICT"]), rec["DISTRICT"]).strip()
        lat, lon = shape_centroid(shape_record.shape)
        if not (6 <= lat <= 38 and 68 <= lon <= 98):
            raise SystemExit(f"Centroid outside India for {district}, {state}: {lat}, {lon}")
        rows.append((state, district, round(lat, 4), round(lon, 4)))

    rows.sort()
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["state", "district", "latitude", "longitude"])
        writer.writerows(rows)

    OUT_PROVENANCE.write_text(json.dumps({
        "source": "datameet/maps Districts/Census_2011 (2011_Dist.shp, 2011_Dist.dbf)",
        "url": "https://github.com/datameet/maps/tree/master/Districts/Census_2011",
        "districts": len(rows),
        "states": len({r[0] for r in rows}),
        "centre_method": "area-weighted polygon centroid in degrees",
        "limits": [
            "Census 2011 boundaries: Telangana is inside Andhra Pradesh; later districts are missing.",
            "Centres are reference points for NASA grid lookup, not farm locations.",
        ],
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=2), encoding="utf-8")
    print(f"districts: {len(rows)} | states: {len({r[0] for r in rows})}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: py -3.11 -m examples.build_india_districts <path-to>/2011_Dist")
    main(sys.argv[1])
