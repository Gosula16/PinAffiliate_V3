"""M1 — Trend Engine: Fetches trending product keywords from Google Trends India."""

import json, logging, os, re
from datetime import datetime
from config import TRENDS_FILE, FALLBACK_KEYWORDS, DATA_DIR

logger = logging.getLogger("pinbot.trends")

COMMERCIAL_WORDS = [
    "best", "top", "buy", "cheap", "under", "budget", "review", "price",
    "india", "2025", "2026", "earbuds", "headphone", "phone", "laptop",
    "tablet", "camera", "speaker", "charger", "cable", "watch", "smartwatch",
    "mixer", "cooler", "fan", "light", "lamp", "bag", "shoes", "bottle",
    "fitness", "gym", "yoga", "kitchen", "blender", "trimmer", "iron",
]

NON_COMMERCIAL = [
    "cricket", "ipl", "election", "movie", "film", "song", "actor", "actress",
    "politician", "party", "war", "news", "weather", "match", "score",
]


def _is_product_keyword(kw: str) -> bool:
    kw_lower = kw.lower()
    if any(bad in kw_lower for bad in NON_COMMERCIAL):
        return False
    if any(good in kw_lower for good in COMMERCIAL_WORDS):
        return True
    return False


def fetch_trends() -> list[str]:
    """Try pytrends first; fall back to evergreen list if unavailable."""
    os.makedirs(DATA_DIR, exist_ok=True)
    keywords = []

    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="en-IN", tz=330, timeout=(10, 25))
        pt.build_payload(kw_list=["amazon india"], geo="IN", timeframe="now 1-d")
        related = pt.related_queries()
        raw = []
        for kw_data in related.values():
            if kw_data and kw_data.get("top") is not None:
                raw += kw_data["top"]["query"].tolist()

        # Also grab daily trending searches
        try:
            trending = pt.trending_searches(pn="india")
            raw += trending[0].tolist()
        except Exception:
            pass

        keywords = [k for k in raw if _is_product_keyword(k)]
        logger.info(f"pytrends returned {len(keywords)} product keywords")

    except Exception as e:
        logger.warning(f"pytrends failed ({e}) — using fallback keywords")

    if len(keywords) < 5:
        keywords = FALLBACK_KEYWORDS.copy()
        logger.info("Using evergreen fallback keyword list")

    # Deduplicate, keep top 15
    seen = set()
    unique = []
    for k in keywords:
        kl = k.lower().strip()
        if kl not in seen:
            seen.add(kl)
            unique.append(k.strip())
        if len(unique) >= 15:
            break

    result = {
        "fetched_at": datetime.now().isoformat(),
        "source": "pytrends" if len(keywords) > len(FALLBACK_KEYWORDS) else "fallback",
        "keywords": unique,
    }
    with open(TRENDS_FILE, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"Saved {len(unique)} keywords to {TRENDS_FILE}")
    return unique


def load_trends() -> list[str]:
    if not os.path.exists(TRENDS_FILE):
        return fetch_trends()
    with open(TRENDS_FILE) as f:
        data = json.load(f)
    fetched = datetime.fromisoformat(data["fetched_at"])
    # Refresh if older than 12 hours
    if (datetime.now() - fetched).total_seconds() > 43200:
        return fetch_trends()
    return data["keywords"]
