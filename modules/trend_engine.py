"""M1 - Trend Engine: fetch fresh buyer-intent product keywords."""

import json
import logging
import os
import re
from datetime import datetime

from config import DATA_DIR, FALLBACK_KEYWORDS, TREND_SEED_KEYWORDS, TRENDS_FILE

logger = logging.getLogger("pinbot.trends")

COMMERCIAL_WORDS = [
    "best", "top", "buy", "cheap", "under", "budget", "review", "price",
    "deal", "deals", "amazon", "seller", "viral", "finds", "gadget",
    "essentials", "decor", "organizer", "storage", "earbuds", "headphone",
    "phone", "laptop", "tablet", "camera", "speaker", "charger", "cable",
    "watch", "smartwatch", "mixer", "cooler", "fan", "light", "lamp", "bag",
    "shoes", "bottle", "fitness", "gym", "yoga", "kitchen", "blender",
    "trimmer", "iron", "desk", "home", "travel", "beauty", "skincare",
]

NON_COMMERCIAL = [
    "cricket", "ipl", "election", "movie", "film", "song", "actor",
    "actress", "politician", "party", "war", "news", "weather", "match",
    "score", "lottery", "exam result", "books", "book", "nonfiction",
    "rank", "kindle", "audible",
]


def _is_product_keyword(keyword: str) -> bool:
    keyword = keyword.lower()
    if any(bad in keyword for bad in NON_COMMERCIAL):
        return False
    return any(good in keyword for good in COMMERCIAL_WORDS)


def _buyer_query(term: str) -> str:
    term = re.sub(r"\s+", " ", term).strip().lower()
    if not term:
        return ""
    if any(word in term for word in ("best", "under", "budget", "amazon", "buy")):
        return term
    return f"best {term} under budget"


def fetch_trends() -> list[str]:
    """Try pytrends first, then blend evergreen Pinterest/Amazon searches."""
    os.makedirs(DATA_DIR, exist_ok=True)
    raw: list[str] = []

    try:
        from pytrends.request import TrendReq

        pt = TrendReq(hl="en-US", tz=0, timeout=(10, 25))
        for seed in TREND_SEED_KEYWORDS:
            try:
                pt.build_payload(kw_list=[seed], geo="", timeframe="now 1-d")
                related = pt.related_queries()
                for keyword_data in related.values():
                    if keyword_data and keyword_data.get("top") is not None:
                        raw += keyword_data["top"]["query"].tolist()
                    if keyword_data and keyword_data.get("rising") is not None:
                        raw += keyword_data["rising"]["query"].tolist()
            except Exception as seed_error:
                logger.debug(f"pytrends seed skipped '{seed}': {seed_error}")

        for region in ("united_states", "india"):
            try:
                trending = pt.trending_searches(pn=region)
                raw += trending[0].tolist()
            except Exception:
                pass

        logger.info(f"pytrends returned {len(raw)} raw trend terms")

    except Exception as error:
        logger.warning(f"pytrends failed ({error}) - using evergreen fallback keywords")

    keywords = [_buyer_query(k) for k in raw if _is_product_keyword(k)]
    keywords += FALLBACK_KEYWORDS

    seen = set()
    unique: list[str] = []
    for keyword in keywords:
        cleaned = re.sub(r"\s+", " ", keyword).strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            unique.append(cleaned)
        if len(unique) >= 30:
            break

    result = {
        "fetched_at": datetime.now().isoformat(),
        "source": "pytrends+evergreen" if raw else "evergreen",
        "keywords": unique,
    }
    with open(TRENDS_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(unique)} trend keywords to {TRENDS_FILE}")
    return unique


def load_trends() -> list[str]:
    if not os.path.exists(TRENDS_FILE):
        return fetch_trends()
    with open(TRENDS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    fetched = datetime.fromisoformat(data["fetched_at"])
    if (datetime.now() - fetched).total_seconds() > 43200:
        return fetch_trends()
    return data["keywords"]
