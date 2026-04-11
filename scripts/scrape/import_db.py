"""
Import processed story JSON files into MythAtlas via the POST /api/stories endpoint.

Input:  data/processed/<region>.json   (from process_llm.py)

Usage:
    python import_db.py                                  # import everything in data/processed/
    python import_db.py --files greek.json norse.json    # specific files
    python import_db.py --dry-run                        # preview without inserting
    python import_db.py --api http://localhost:8000 --token your-admin-token

The backend must be running. Default target: http://localhost:8000
Default token: dev-admin-change-me  (set ADMIN_TOKEN in your .env)

Requirements: pip install requests
"""

import argparse
import json
import time
from pathlib import Path

import requests


def health_check(api_base: str) -> bool:
    try:
        r = requests.get(f"{api_base}/api/health", timeout=5)
        if r.status_code == 200:
            print(f"Backend OK: {api_base}")
            return True
        print(f"Backend returned {r.status_code}")
        return False
    except requests.exceptions.ConnectionError:
        print(f"Cannot reach backend at {api_base}")
        print("Is it running? Try: docker compose up  (or  cd backend && uvicorn app.main:app)")
        return False


def import_file(
    file: Path,
    api_base: str,
    token: str,
    dry_run: bool,
    skip_duplicates: bool,
) -> tuple[int, int]:
    """
    Import one JSON file. Returns (inserted, skipped).
    Handles both the east_asia_stories.json format (has 'stories' key)
    and a bare list of story objects.
    """
    with open(file, encoding="utf-8") as f:
        data = json.load(f)

    stories: list[dict] = data.get("stories", data) if isinstance(data, dict) else data
    if not isinstance(stories, list):
        print(f"  Skipping {file.name}: unexpected format (not a list)")
        return 0, 0

    headers = {
        "X-Admin-Token": token,
        "Content-Type": "application/json",
    }

    inserted = skipped = 0

    for story in stories:
        # Map summary_* -> content_*  (JSON files use summary_, API schema uses content_)
        payload = {
            "title_en":   story.get("title_en", "").strip(),
            "title_zh":   story.get("title_zh", "").strip(),
            "content_en": (story.get("summary_en") or story.get("content_en", "")).strip(),
            "content_zh": (story.get("summary_zh") or story.get("content_zh", "")).strip(),
            "country":    story.get("country", "Unknown").strip(),
            "tags":       story.get("tags", []),
            "emoji":      story.get("emoji", "📖"),
            "lat":        float(story.get("lat", 0.0)),
            "lng":        float(story.get("lng", 0.0)),
        }

        # Basic validation before sending
        missing = [k for k in ("title_en", "title_zh", "content_en", "content_zh") if not payload[k]]
        if missing:
            print(f"  SKIP (missing {missing}): {payload['title_en'] or '(no title)'}")
            skipped += 1
            continue

        if dry_run:
            print(f"  [DRY RUN] {payload['title_en']} ({payload['country']})")
            inserted += 1
            continue

        try:
            r = requests.post(
                f"{api_base}/api/stories",
                json=payload,
                headers=headers,
                timeout=30,
            )

            if r.status_code == 200:
                new_id = r.json().get("id", "?")
                print(f"  OK  [{new_id}] {payload['title_en']}")
                inserted += 1

            elif r.status_code == 422:
                print(f"  INVALID  {payload['title_en']}: {r.json().get('detail', r.text)[:120]}")
                skipped += 1

            elif r.status_code in (401, 403):
                print("  AUTH ERROR: wrong admin token. Check --token or ADMIN_TOKEN in .env")
                # Fatal — no point continuing
                return inserted, skipped + (len(stories) - inserted - skipped)

            else:
                print(f"  ERROR {r.status_code}  {payload['title_en']}: {r.text[:100]}")
                skipped += 1

        except requests.exceptions.Timeout:
            print(f"  TIMEOUT  {payload['title_en']}")
            skipped += 1
        except Exception as exc:
            print(f"  FAIL  {payload['title_en']}: {exc}")
            skipped += 1

        time.sleep(0.05)  # Gentle pacing

    return inserted, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Import processed mythology stories into MythAtlas")
    parser.add_argument("--api", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--token", default="dev-admin-change-me", help="Admin token")
    parser.add_argument("--dir", default="data/processed", help="Directory of processed JSON files")
    parser.add_argument("--files", nargs="*", help="Specific filenames inside --dir to import")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be imported without sending any requests"
    )
    args = parser.parse_args()

    data_dir = Path(args.dir)
    if not data_dir.exists():
        print(f"Directory not found: {data_dir}")
        print("Run process_llm.py first.")
        return

    if args.files:
        files = [data_dir / fn for fn in args.files]
    else:
        files = sorted(data_dir.glob("*.json"))

    files = [f for f in files if f.exists()]
    if not files:
        print(f"No JSON files found in {data_dir}")
        return

    print(f"Found {len(files)} file(s) to import")

    if not args.dry_run and not health_check(args.api):
        return

    total_inserted = total_skipped = 0
    for file in files:
        print(f"\n--- {file.name} ---")
        n_in, n_sk = import_file(file, args.api, args.token, args.dry_run, skip_duplicates=True)
        total_inserted += n_in
        total_skipped += n_sk
        print(f"  Inserted: {n_in}  |  Skipped: {n_sk}")

    print(f"\nDone. Total inserted: {total_inserted}  |  Total skipped: {total_skipped}")
    if args.dry_run:
        print("(Dry run — nothing was actually written)")


if __name__ == "__main__":
    main()
