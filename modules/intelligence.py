"""AI ranking and optimization layer for product selection.

The module is deterministic by default and can enrich quality signals with a
Hugging Face text-classification model when HUGGINGFACE_API_TOKEN is configured.
"""

from __future__ import annotations

import json
import logging
import math
import re
from functools import lru_cache

import requests

from config import HUGGINGFACE_API_TOKEN, HF_TEXT_MODEL, AI_MIN_PRODUCT_SCORE

logger = logging.getLogger("publisher.intelligence")


def _num(value, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    cleaned = re.sub(r"[^0-9.]", "", str(value))
    if not cleaned:
        return default
    try:
        return float(cleaned)
    except ValueError:
        return default


def _review_count(value) -> int:
    return int(_num(value, 0))


def _clean_words(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(value or "").lower())


def _buyer_intent(keyword: str, title: str) -> tuple[int, str]:
    text = f"{keyword} {title}".lower()
    high = ["best seller", "best", "under", "deal", "budget", "review", "price", "useful", "trending"]
    medium = ["amazon", "finds", "essentials", "setup", "home", "travel", "gift"]
    score = sum(9 for word in high if word in text) + sum(5 for word in medium if word in text)
    if score >= 22:
        return min(100, score + 45), "high"
    if score >= 10:
        return score + 42, "medium"
    return max(28, score + 30), "low"


def _price_score(price: float) -> int:
    if not price:
        return 42
    if 299 <= price <= 2999:
        return 95
    if 3000 <= price <= 6999:
        return 82
    if 7000 <= price <= 14999:
        return 62
    if price < 299:
        return 58
    return 38


def _seo_variants(product: dict) -> list[str]:
    title = str(product.get("title") or product.get("pin_title") or "Amazon find")
    keyword = str(product.get("seo_keyword") or product.get("keyword") or "amazon finds")
    short = re.split(r"\s+[|(-]\s*", title)[0].strip()[:54].rstrip(" ,|-") or title[:54]
    price = _num(product.get("price"))
    price_part = f" Under Rs {int(math.ceil(price / 100.0) * 100)}" if 299 <= price <= 9999 else ""
    base = keyword.title()
    variants = [
        f"Best {base}{price_part} India",
        f"{short} Review And Price",
        f"Useful Amazon Find: {short}",
        f"{base} For Home And Daily Use",
        f"Top Rated {base} Worth Checking",
    ]
    seen = []
    for item in variants:
        item = re.sub(r"\s+", " ", item).strip()[:100]
        if item.lower() not in {v.lower() for v in seen}:
            seen.append(item)
    return seen


def _description_variants(product: dict) -> list[str]:
    title = str(product.get("title") or product.get("pin_title") or "This Amazon find")
    keyword = str(product.get("seo_keyword") or product.get("keyword") or "amazon find").lower()
    price = _num(product.get("price"))
    price_text = f"around Rs. {int(price):,}" if price else "with current Amazon pricing"
    short = re.split(r"\s+[|(-]\s*", title)[0].strip()[:72] or title[:72]
    return [
        f"{short} is a strong {keyword} pick at {price_text}. Check the exact product page for latest specs, reviews and offers.",
        f"Looking for {keyword}? {short} has useful everyday appeal and is worth comparing before you buy.",
        f"Save this {keyword} idea for later. {short} may fit home, work or gifting needs depending on today's Amazon price.",
    ]


@lru_cache(maxsize=256)
def _hf_text_signal(text: str) -> tuple[int, str]:
    if not HUGGINGFACE_API_TOKEN:
        return 0, "heuristic"
    try:
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_TEXT_MODEL}",
            headers={"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"},
            json={"inputs": text[:900]},
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload[0] if payload and isinstance(payload[0], list) else payload
        labels = {str(row.get("label", "")).lower(): float(row.get("score", 0)) for row in rows if isinstance(row, dict)}
        positive = max(labels.get("positive", 0), labels.get("label_2", 0), labels.get("5 stars", 0))
        negative = max(labels.get("negative", 0), labels.get("label_0", 0), labels.get("1 star", 0))
        signal = round((positive - negative) * 12)
        return signal, "huggingface"
    except Exception as exc:
        logger.info(f"Hugging Face signal skipped: {exc}")
        return 0, "heuristic"


def enrich_product(product: dict) -> dict:
    item = dict(product)
    title = str(item.get("title") or item.get("pin_title") or "")
    keyword = str(item.get("keyword") or item.get("seo_keyword") or "")
    rating = _num(item.get("rating"))
    reviews = _review_count(item.get("reviews"))
    price = _num(item.get("price"))
    trend = _num(item.get("trend_score"))
    intent_score, intent = _buyer_intent(keyword, title)
    hf_signal, hf_source = _hf_text_signal(f"{title}. {keyword}. {item.get('pin_description', '')}")

    score = 0
    score += min(22, rating * 4.5)
    score += min(18, math.sqrt(reviews) / 5)
    score += _price_score(price) * 0.18
    score += min(16, trend * 0.55)
    score += intent_score * 0.14
    score += 8 if item.get("image_url") else -4
    score += 5 if item.get("has_affiliate") else 0
    score += hf_signal
    score = max(0, min(100, round(score, 2)))

    flags = []
    if rating and rating < 3.8:
        flags.append("low-rating")
    if reviews and reviews < 50:
        flags.append("low-review-proof")
    if not item.get("image_url"):
        flags.append("missing-image")
    if not item.get("has_affiliate"):
        flags.append("manual-link")
    if price > 15000:
        flags.append("high-price")

    item["ai_score"] = score
    item["product_score"] = score
    item["buyer_intent"] = intent
    item["quality_grade"] = "A" if score >= 78 else "B" if score >= 64 else "C" if score >= 50 else "D"
    item["recommendation"] = "post" if score >= AI_MIN_PRODUCT_SCORE and len(flags) <= 2 else "review"
    item["risk_flags"] = ", ".join(flags) if flags else "clean"
    item["hf_signal"] = hf_signal
    item["hf_signal_source"] = hf_source
    item["seo_title_variants"] = json.dumps(_seo_variants(item), ensure_ascii=False)
    item["caption_variants"] = json.dumps(_description_variants(item), ensure_ascii=False)
    item["best_posting_window"] = _best_window(item)
    return item


def _best_window(product: dict) -> str:
    text = f"{product.get('keyword', '')} {product.get('title', '')}".lower()
    if any(word in text for word in ["kitchen", "home", "cleaning", "organization"]):
        return "12:00-13:30"
    if any(word in text for word in ["beauty", "fitness", "self care"]):
        return "18:30-20:00"
    if any(word in text for word in ["deal", "budget", "gift"]):
        return "22:00-23:00"
    return "07:30-09:00"


def enrich_products(products: list[dict]) -> list[dict]:
    return [enrich_product(product) for product in products]


def rank_products(products: list[dict]) -> list[dict]:
    enriched = enrich_products(products)
    return sorted(
        enriched,
        key=lambda p: (
            p.get("recommendation") == "post",
            float(p.get("ai_score") or 0),
            p.get("buyer_intent") == "high",
            _review_count(p.get("reviews")),
        ),
        reverse=True,
    )


def select_diverse_batch(products: list[dict], limit: int) -> list[dict]:
    if limit <= 0:
        return []
    ranked = rank_products(products)
    selected, category_counts = [], {}
    for product in ranked:
        category = str(product.get("pin_board") or product.get("keyword") or "general")
        if category_counts.get(category, 0) >= 4 and len(selected) < max(6, limit // 2):
            continue
        selected.append(product)
        category_counts[category] = category_counts.get(category, 0) + 1
        if len(selected) >= limit:
            break
    if len(selected) < limit:
        selected_ids = {p.get("asin") for p in selected}
        selected.extend([p for p in ranked if p.get("asin") not in selected_ids][: limit - len(selected)])
    return selected[:limit]
