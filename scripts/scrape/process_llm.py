"""
Process raw Wikipedia articles with a local Qwen model via Ollama.
Produces JSON files matching the east_asia_stories.json schema.

Input:  data/raw/<region>.json       (from fetch_wiki.py)
Output: data/processed/<region>.json

Usage:
    python process_llm.py                          # all regions in data/raw/
    python process_llm.py --regions greek norse    # specific regions
    python process_llm.py --model qwen2.5:14b      # bigger model

Requirements:
    pip install requests
    ollama pull qwen2.5:7b        # or qwen2.5:14b if you have headroom

Ollama must be running: ollama serve
"""

import argparse
import json
import math
import random
import re
import time
from pathlib import Path

import requests

DEFAULT_MODEL = "qwen2.5:7b"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"

SYSTEM_PROMPT = """You are a mythology and folklore expert. Given a Wikipedia article about a myth, legend, folklore figure, or epic story, write a structured summary.

Output ONLY a valid JSON object with exactly these keys:

{
  "title_en": "English name of this myth/figure/story (clean, no parentheses)",
  "title_zh": "Chinese name in Chinese characters",
  "summary_en": "150-250 word narrative retelling of the myth or legend in prose. Tell the story — not a biography list or Wikipedia-style facts. Make it vivid.",
  "summary_zh": "Same story in Chinese, same length, literary prose (not a translation word-for-word, but natural Chinese storytelling style)",
  "country": "Cultural origin in format: English Name 中文名  (e.g. Greece 希腊, Japan 日本, Egypt 埃及). Use the default_country if unsure.",
  "emoji": "One emoji that best represents this story",
  "type": "one of: myth, legend, epic, folklore",
  "tags": ["4 to 8 lowercase English strings — themes, motifs, era. Era must be one of: ancient, classical, medieval, modern"]
}

Rules:
- summary_en must be a story, not a list of facts
- title_zh must be real Chinese characters, not pinyin
- tags must include exactly one era tag (ancient, classical, medieval, modern)
- Return ONLY the JSON object, no explanation, no markdown fences"""


def call_ollama(title: str, extract: str, default_country: str, model: str) -> str | None:
    """Call Ollama chat API. Returns the raw response string or None on failure."""
    user_msg = (
        f"Article title: {title}\n"
        f"Default country: {default_country}\n\n"
        f"Wikipedia extract:\n{extract}"
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.3,
            "num_predict": 900,
        },
    }
    try:
        r = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=120)
        r.raise_for_status()
        return r.json()["message"]["content"]
    except requests.exceptions.ConnectionError:
        print("    ERROR: Cannot connect to Ollama. Is it running? Run: ollama serve")
        return None
    except Exception as exc:
        print(f"    Ollama error: {exc}")
        return None


def parse_json(text: str) -> dict | None:
    """Parse JSON from LLM response with tolerance for minor formatting issues."""
    text = text.strip()
    # Extract the first {...} block in case of surrounding text
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        text = match.group(0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


REQUIRED_KEYS = {"title_en", "title_zh", "summary_en", "summary_zh", "country", "emoji", "type", "tags"}
VALID_TYPES = {"myth", "legend", "epic", "folklore"}


def validate(story: dict) -> str | None:
    """Return None if valid, or an error message string if not."""
    missing = REQUIRED_KEYS - story.keys()
    if missing:
        return f"missing keys: {missing}"
    if story.get("type") not in VALID_TYPES:
        return f"invalid type: {story.get('type')!r}"
    if not isinstance(story.get("tags"), list) or not story["tags"]:
        return "tags must be a non-empty list"
    if len(story.get("summary_en", "")) < 80:
        return "summary_en too short"
    if len(story.get("summary_zh", "")) < 40:
        return "summary_zh too short"
    # title_zh should contain actual Chinese characters
    if not re.search(r"[\u4e00-\u9fff]", story.get("title_zh", "")):
        return "title_zh has no Chinese characters"
    return None


def process_file(raw_file: Path, out_file: Path, model: str, max_errors: int) -> int:
    with open(raw_file, encoding="utf-8") as f:
        raw_articles: list[dict] = json.load(f)

    # Resume: skip titles already processed
    processed: list[dict] = []
    done_titles: set[str] = set()
    if out_file.exists():
        with open(out_file, encoding="utf-8") as f:
            existing = json.load(f)
        processed = existing.get("stories", [])
        done_titles = {s["title_en"] for s in processed}
        print(f"  Resuming — {len(processed)} already processed")

    region_label = raw_file.stem.replace("_", " ").title()
    consecutive_errors = 0

    for idx, article in enumerate(raw_articles):
        title = article["title"]
        if title in done_titles:
            continue

        print(f"  [{idx + 1}/{len(raw_articles)}] {title}")

        response = call_ollama(title, article["extract"], article["default_country"], model)
        if response is None:
            consecutive_errors += 1
            if consecutive_errors >= max_errors:
                print(f"  {max_errors} consecutive errors — stopping. Re-run to resume.")
                break
            time.sleep(1)
            continue

        story = parse_json(response)
        if story is None:
            print(f"    Skipped: could not parse JSON response")
            consecutive_errors += 1
            continue

        error = validate(story)
        if error:
            print(f"    Skipped: {error}")
            consecutive_errors += 1
            continue

        consecutive_errors = 0

        # Merge geo + wiki data that the LLM doesn't have
        story["title_en"] = story["title_en"] or title
        story["lat"] = article["lat"]
        story["lng"] = article["lng"]
        story["wiki_en"] = article["wiki_en"]
        if article.get("wiki_zh"):
            story["wiki_zh"] = article["wiki_zh"]

        processed.append(story)
        done_titles.add(story["title_en"])

        # Save incrementally so progress is never lost
        _save(out_file, region_label, processed)

    print(f"  Done — {len(processed)} stories -> {out_file}")
    return len(processed)


def _spread_coords(stories: list[dict]) -> list[dict]:
    """
    Spread stories that share the same or very close coordinates into a ring
    so they are visually distinct on the globe. Accuracy is sacrificed for UX.
    """
    STEP = 0.4  # degrees — bucket size

    def bucket(lat: float, lng: float) -> tuple:
        return (round(lat / STEP) * STEP, round(lng / STEP) * STEP)

    groups: dict[tuple, list[int]] = {}
    for i, s in enumerate(stories):
        key = bucket(float(s.get("lat", 0)), float(s.get("lng", 0)))
        groups.setdefault(key, []).append(i)

    result = [dict(s) for s in stories]
    for indices in groups.values():
        if len(indices) < 2:
            continue
        n = len(indices)
        lats = [float(stories[i]["lat"]) for i in indices]
        lngs = [float(stories[i]["lng"]) for i in indices]
        clat = sum(lats) / len(lats)
        clng = sum(lngs) / len(lngs)

        # Radius grows with group size
        radius = 0.35 if n <= 2 else 0.55 if n <= 5 else 0.85 if n <= 10 else 1.2 if n <= 20 else 1.8
        angle_offset = random.uniform(0, 2 * math.pi)
        lng_scale = 1.0 / max(math.cos(math.radians(clat)), 0.1)

        for rank, idx in enumerate(indices):
            angle = angle_offset + (2 * math.pi * rank) / n
            new_lat = max(-89.9, min(89.9, clat + radius * math.cos(angle)))
            new_lng = ((clng + radius * math.sin(angle) * lng_scale + 180) % 360) - 180
            result[idx]["lat"] = round(new_lat, 4)
            result[idx]["lng"] = round(new_lng, 4)

    return result


def _save(out_file: Path, region_label: str, stories: list[dict]) -> None:
    spread = _spread_coords(stories)
    output = {
        "meta": {
            "region": region_label,
            "count": len(spread),
            "generated": "2026-04-11",
            "note": "Scraped from Wikipedia, summarized with a local Qwen model via Ollama.",
        },
        "stories": spread,
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def check_ollama(model: str) -> bool:
    """Verify Ollama is running and the model is available."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        r.raise_for_status()
        available = [m["name"] for m in r.json().get("models", [])]
        # Model names may include tags like "qwen2.5:7b"
        base = model.split(":")[0]
        found = any(base in m for m in available)
        if not found:
            print(f"WARNING: model '{model}' not found in Ollama.")
            print(f"Available models: {available}")
            print(f"Run: ollama pull {model}")
            return False
        return True
    except requests.exceptions.ConnectionError:
        print("ERROR: Ollama is not running. Start it with: ollama serve")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process raw Wikipedia articles with Ollama/Qwen into story JSON"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model (default: {DEFAULT_MODEL})")
    parser.add_argument("--raw", default="data/raw", help="Raw data directory (default: data/raw)")
    parser.add_argument("--out", default="data/processed", help="Output directory (default: data/processed)")
    parser.add_argument("--regions", nargs="*", help="Only process these region slugs")
    parser.add_argument("--max-errors", type=int, default=5, help="Stop after N consecutive errors")
    args = parser.parse_args()

    if not check_ollama(args.model):
        return

    raw_dir = Path(args.raw)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_files = sorted(raw_dir.glob("*.json"))
    if args.regions:
        slugs = set(args.regions)
        raw_files = [f for f in raw_files if f.stem in slugs]

    if not raw_files:
        print(f"No raw JSON files found in {raw_dir}. Run fetch_wiki.py first.")
        return

    total = 0
    for raw_file in raw_files:
        print(f"\n--- Processing: {raw_file.name} ---")
        out_file = out_dir / raw_file.name
        n = process_file(raw_file, out_file, args.model, args.max_errors)
        total += n

    print(f"\nFinished. Total stories: {total}")
    print(f"Processed files in: {out_dir.resolve()}")
    print("Next step: python import_db.py")


if __name__ == "__main__":
    main()
