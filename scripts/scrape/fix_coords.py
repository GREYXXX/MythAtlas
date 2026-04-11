"""
Spread stories that share the same or very close coordinates so they are
visually distinct on the globe. Accuracy is intentionally sacrificed for UX.

Operates on processed JSON files in data/processed/ and overwrites them in place.
Re-run import_db.py afterwards to push the updated coordinates into the database.

Usage:
    python fix_coords.py                      # fix all files in data/processed/
    python fix_coords.py --dir data/processed
    python fix_coords.py --preview            # print changes without writing

Requirements: none (stdlib only)
"""

import argparse
import json
import math
import random
from pathlib import Path


# Bucket size in degrees — stories within this distance are treated as "stacked"
CLUSTER_RADIUS_DEG = 0.4

# Ring radius (degrees latitude) per tier; longitude is corrected for latitude
def _spread_radius(n: int) -> float:
    if n <= 2:  return 0.35
    if n <= 5:  return 0.55
    if n <= 10: return 0.85
    if n <= 20: return 1.2
    return 1.8


def spread_stories(stories: list[dict]) -> tuple[list[dict], int]:
    """
    Group stories whose rounded (lat, lng) fall in the same bucket.
    Spread each group of 2+ stories in an evenly-spaced ring.
    Returns (updated_stories, n_moved).
    """
    # Grid key: snap to CLUSTER_RADIUS_DEG grid
    def bucket(lat: float, lng: float) -> tuple:
        step = CLUSTER_RADIUS_DEG
        return (round(lat / step) * step, round(lng / step) * step)

    # Build buckets
    groups: dict[tuple, list[int]] = {}
    for i, s in enumerate(stories):
        key = bucket(float(s.get("lat", 0)), float(s.get("lng", 0)))
        groups.setdefault(key, []).append(i)

    updated = [dict(s) for s in stories]
    n_moved = 0

    for key, indices in groups.items():
        if len(indices) < 2:
            continue

        # Centroid of the group
        lats = [float(stories[i]["lat"]) for i in indices]
        lngs = [float(stories[i]["lng"]) for i in indices]
        clat = sum(lats) / len(lats)
        clng = sum(lngs) / len(lngs)

        n = len(indices)
        radius = _spread_radius(n)
        # Add a small random rotation so clusters from different countries
        # don't all point in the same direction
        angle_offset = random.uniform(0, 2 * math.pi)
        # Longitude degrees shrink with latitude
        lng_scale = 1.0 / max(math.cos(math.radians(clat)), 0.1)

        for rank, idx in enumerate(indices):
            angle = angle_offset + (2 * math.pi * rank) / n
            new_lat = clat + radius * math.cos(angle)
            new_lng = clng + radius * math.sin(angle) * lng_scale
            # Clamp to valid range
            new_lat = max(-89.9, min(89.9, new_lat))
            new_lng = ((new_lng + 180) % 360) - 180
            updated[idx]["lat"] = round(new_lat, 4)
            updated[idx]["lng"] = round(new_lng, 4)
            n_moved += 1

    return updated, n_moved


def fix_file(path: Path, preview: bool) -> int:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    stories = data.get("stories", data) if isinstance(data, dict) else data
    if not isinstance(stories, list):
        print(f"  Skipping {path.name}: unexpected format")
        return 0

    fixed, n_moved = spread_stories(stories)
    print(f"  {path.name}: {len(stories)} stories, {n_moved} coordinates adjusted")

    if preview:
        return n_moved

    # Write back
    if isinstance(data, dict):
        data["stories"] = fixed
        out = data
    else:
        out = fixed

    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    return n_moved


def main() -> None:
    parser = argparse.ArgumentParser(description="Spread stacked story coordinates for globe UX")
    parser.add_argument("--dir", default="data/processed", help="Directory of processed JSON files")
    parser.add_argument("--preview", action="store_true", help="Show changes without writing")
    args = parser.parse_args()

    data_dir = Path(args.dir)
    if not data_dir.exists():
        print(f"Directory not found: {data_dir}")
        return

    files = sorted(data_dir.glob("*.json"))
    if not files:
        print(f"No JSON files in {data_dir}")
        return

    total = 0
    for f in files:
        total += fix_file(f, args.preview)

    print(f"\nTotal coordinates adjusted: {total}")
    if not args.preview:
        print("Done. Re-import with: python import_db.py")
    else:
        print("(Preview only — no files were written)")


if __name__ == "__main__":
    main()
