"""
Fetch mythology/folklore articles from Wikipedia via the MediaWiki API.
Saves raw article data to data/raw/<region>.json.

Usage:
    python fetch_wiki.py                        # all regions
    python fetch_wiki.py --regions greek norse  # specific regions
    python fetch_wiki.py --max 100              # cap articles per region (default 300)

Requirements: pip install requests
"""

import argparse
import json
import time
from pathlib import Path

import requests

API_URL = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "MythAtlas/1.0 (mythology scraper; educational use)"}

# (region_slug, Wikipedia category, default_country, default_lat, default_lng)
CATEGORIES = [
    ("greek",        "Greek_mythology",                  "Greece 希腊",                37.98,   23.73),
    ("roman",        "Roman_mythology",                  "Italy 意大利",                41.87,   12.57),
    ("norse",        "Norse_mythology",                  "Norse / Scandinavia 北欧",    59.91,   10.75),
    ("celtic",       "Celtic_mythology",                 "Ireland 爱尔兰",              53.33,   -6.25),
    ("arthurian",    "Arthurian_legend",                 "England 英格兰",              52.36,   -1.17),
    ("egyptian",     "Egyptian_mythology",               "Egypt 埃及",                  26.82,   30.80),
    ("mesopotamian", "Mesopotamian_mythology",           "Iraq 伊拉克",                 33.22,   43.68),
    ("persian",      "Persian_mythology",                "Iran 伊朗",                   32.43,   53.69),
    ("hindu",        "Hindu_mythology",                  "India 印度",                  20.59,   78.96),
    ("japanese",     "Japanese_mythology",               "Japan 日本",                  36.20,  138.25),
    ("chinese",      "Chinese_mythology",                "China 中国",                  35.86,  104.19),
    ("aztec",        "Aztec_mythology",                  "Mexico 墨西哥",               23.63, -102.55),
    ("inca",         "Inca_mythology",                   "Peru 秘鲁",                   -9.19,  -75.02),
    ("slavic",       "Slavic_mythology",                 "Russia 俄罗斯",               55.75,   37.62),
    ("polynesian",   "Polynesian_mythology",             "Polynesia 波利尼西亚",       -17.73, -168.32),
    ("maori",        "Māori_mythology",                  "New Zealand 新西兰",          -40.90,  174.89),
    ("aboriginal",   "Australian_Aboriginal_mythology",  "Australia 澳大利亚",          -25.27,  133.78),
    ("yoruba",       "Yoruba_mythology",                 "Nigeria 尼日利亚",              9.08,    8.68),
    ("korean",       "Korean_mythology",                 "Korea 韩国",                   35.91,  127.77),
]

# Titles containing these strings are skipped (disambiguation, list articles, etc.)
SKIP_IF_CONTAINS = (
    "list of", "(disambiguation)", "category:", "template:",
    "bibliography", "index of", "outline of",
)


def get_category_members(category: str, limit: int) -> list[str]:
    """Return page titles in a Wikipedia category, up to limit."""
    titles: list[str] = []
    params: dict = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmtype": "page",
        "cmlimit": min(limit, 500),
        "format": "json",
    }
    while len(titles) < limit:
        r = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        for m in data.get("query", {}).get("categorymembers", []):
            title = m["title"]
            lower = title.lower()
            if not any(skip in lower for skip in SKIP_IF_CONTAINS):
                titles.append(title)
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            break
        params["cmcontinue"] = cont
        time.sleep(0.3)
    return titles[:limit]


def fetch_pages_batch(titles: list[str]) -> dict:
    """
    Fetch extract + coordinates + zh langlink for up to 20 pages at once.
    Returns the raw 'pages' dict from the API response.
    """
    params = {
        "action": "query",
        "titles": "|".join(titles),
        "prop": "extracts|coordinates|langlinks",
        "exintro": True,       # Introduction section only
        "explaintext": True,   # Plain text, no wikimarkup
        "exsectionformat": "plain",
        "lllang": "zh",        # Only fetch Chinese language link
        "lllimit": 1,
        "redirects": True,
        "format": "json",
    }
    r = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json().get("query", {}).get("pages", {})


def fetch_region(
    region: str,
    category: str,
    default_country: str,
    default_lat: float,
    default_lng: float,
    out_dir: Path,
    max_articles: int,
) -> int:
    """Scrape one category, save incrementally to out_dir/<region>.json."""
    out_file = out_dir / f"{region}.json"

    # Resume: load already-fetched articles
    existing: dict[str, dict] = {}
    if out_file.exists():
        with open(out_file, encoding="utf-8") as f:
            for art in json.load(f):
                existing[art["title"]] = art
        print(f"  [{region}] Resuming — {len(existing)} articles already saved")

    print(f"  [{region}] Walking category: {category}")
    all_titles = get_category_members(category, limit=max_articles)
    print(f"  [{region}] Found {len(all_titles)} candidate titles")

    new_titles = [t for t in all_titles if t not in existing]
    print(f"  [{region}] {len(new_titles)} new articles to fetch")

    articles = list(existing.values())

    BATCH = 20
    for batch_start in range(0, len(new_titles), BATCH):
        batch = new_titles[batch_start : batch_start + BATCH]
        try:
            pages = fetch_pages_batch(batch)
        except Exception as exc:
            print(f"  [{region}] Batch error: {exc} — skipping")
            time.sleep(2)
            continue

        for page in pages.values():
            if page.get("missing"):
                continue
            extract: str = page.get("extract", "").strip()
            if len(extract) < 150:  # Skip very short stubs
                continue

            coords = page.get("coordinates", [])
            lat = coords[0]["lat"] if coords else default_lat
            lng = coords[0]["lon"] if coords else default_lng

            langlinks = page.get("langlinks", [])
            wiki_zh_title = langlinks[0].get("*") if langlinks else None
            wiki_zh = (
                f"https://zh.wikipedia.org/wiki/{wiki_zh_title.replace(' ', '_')}"
                if wiki_zh_title
                else None
            )

            title = page["title"]
            articles.append({
                "title": title,
                "extract": extract[:3500],  # Cap for LLM context window
                "lat": lat,
                "lng": lng,
                "default_country": default_country,
                "wiki_en": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                "wiki_zh": wiki_zh,
                "region": region,
            })

        # Save after every batch so progress isn't lost
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)

        done = batch_start + len(batch)
        print(f"  [{region}] {done}/{len(new_titles)} fetched, {len(articles)} total saved")
        time.sleep(0.5)  # Be polite to Wikipedia

    print(f"  [{region}] Done — {len(articles)} articles in {out_file}")
    return len(articles)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch mythology articles from Wikipedia")
    parser.add_argument("--out", default="data/raw", help="Output directory (default: data/raw)")
    parser.add_argument("--max", type=int, default=300, help="Max articles per region (default: 300)")
    parser.add_argument("--regions", nargs="*", help="Only fetch these region slugs")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = CATEGORIES
    if args.regions:
        slugs = set(args.regions)
        targets = [c for c in CATEGORIES if c[0] in slugs]
        if not targets:
            print(f"No matching regions found. Available: {[c[0] for c in CATEGORIES]}")
            return

    total = 0
    for region, category, default_country, default_lat, default_lng in targets:
        print(f"\n--- {region.upper()} ({category}) ---")
        n = fetch_region(
            region, category, default_country, default_lat, default_lng, out_dir, args.max
        )
        total += n

    print(f"\nFinished. Total articles scraped: {total}")
    print(f"Raw data saved to: {Path(args.out).resolve()}")
    print("Next step: python process_llm.py")


if __name__ == "__main__":
    main()
