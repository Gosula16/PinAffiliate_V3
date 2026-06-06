"""Pinterest-ready CSV export for manual/bulk posting fallback."""

import csv
import os
from datetime import datetime
from typing import Iterable

from config import DATA_DIR

PINTEREST_CSV = os.path.join(DATA_DIR, "pinterest_pins.csv")

PINTEREST_FIELDS = [
    "Title",
    "Description",
    "Destination URL",
    "Board",
    "Alt Text",
    "Image Path",
    "Image URL",
    "ASIN",
    "Price",
    "Exact Product URL",
    "Affiliate Link",
    "Manual Link",
    "SiteStripe URL",
    "AI Score",
    "Conversion Score",
    "Buyer Intent",
    "Quality Grade",
    "Recommendation",
    "AI Action",
    "Risk Flags",
    "HF Category",
    "HF Image Label",
    "Duplicate Cluster",
    "Best Posting Window",
    "Status",
    "Failure Reason",
    "Created At",
]


def _hashtags(caption: dict) -> str:
    return " ".join(f"#{tag.lstrip('#')}" for tag in caption.get("hashtags", []))


def build_row(item: dict, status: str = "ready", failure_reason: str = "") -> dict:
    product = item.get("product", {})
    caption = item.get("caption", {})
    description = f"{caption.get('description', product.get('pin_description', ''))} {_hashtags(caption)}".strip()
    link = product.get("pin_link") or product.get("affiliate_link") or product.get("manual_link") or ""
    return {
        "Title": str(caption.get("title") or product.get("pin_title") or product.get("title", ""))[:100],
        "Description": description[:500],
        "Destination URL": link,
        "Board": product.get("pin_board") or product.get("board_suggested") or "Best Tech Gadgets India",
        "Alt Text": str(product.get("pin_alt_text") or product.get("title", ""))[:500],
        "Image Path": item.get("image_path", ""),
        "Image URL": product.get("image_url", ""),
        "ASIN": product.get("asin", ""),
        "Price": product.get("price", ""),
        "Exact Product URL": product.get("product_url") or product.get("manual_link", ""),
        "Affiliate Link": product.get("affiliate_link", ""),
        "Manual Link": product.get("manual_link", ""),
        "SiteStripe URL": product.get("sitestripe_url", ""),
        "AI Score": product.get("ai_score") or product.get("product_score", ""),
        "Conversion Score": product.get("conversion_score", ""),
        "Buyer Intent": product.get("buyer_intent", ""),
        "Quality Grade": product.get("quality_grade", ""),
        "Recommendation": product.get("recommendation", ""),
        "AI Action": product.get("ai_action", ""),
        "Risk Flags": product.get("risk_flags", ""),
        "HF Category": product.get("hf_category", ""),
        "HF Image Label": product.get("hf_image_label", ""),
        "Duplicate Cluster": product.get("duplicate_cluster", ""),
        "Best Posting Window": product.get("best_posting_window", ""),
        "Status": status,
        "Failure Reason": failure_reason or item.get("failure_reason", ""),
        "Created At": datetime.now().isoformat(),
    }


def save_pinterest_csv(items: Iterable[dict], path: str = PINTEREST_CSV,
                       status: str = "ready", failure_reason: str = "") -> str | None:
    rows = [build_row(item, status=status, failure_reason=failure_reason) for item in items]
    if not rows:
        return None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PINTEREST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path
