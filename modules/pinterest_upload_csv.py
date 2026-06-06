"""Pinterest organic bulk upload CSV export.

This is the simple CSV accepted by Pinterest Settings > Import content.
It is separate from the Ads Bulk Editor spreadsheet.
"""

import csv
import os

from config import PINTEREST_UPLOAD_CSV

HEADERS = [
    "Title",
    "Media URL",
    "Pinterest board",
    "Thumbnail",
    "Description",
    "Link",
    "Publish date",
    "Keywords",
]


def _public_media_url(product: dict) -> str:
    image_url = product.get("image_url") or product.get("Media URL") or ""
    if image_url.startswith(("http://", "https://")):
        return image_url
    return ""


def _keywords(product: dict) -> str:
    values = [
        product.get("seo_keyword") or product.get("keyword") or "",
        product.get("trend_label") or "",
        product.get("buyer_intent") or "",
        product.get("quality_grade") or "",
        product.get("hf_category") or "",
        product.get("ai_action") or "",
        "amazon finds",
        "daily finds",
    ]
    seen = []
    for value in values:
        value = str(value).strip()
        if value and value.lower() not in {item.lower() for item in seen}:
            seen.append(value)
    return ", ".join(seen)


def build_row(product: dict) -> dict:
    title = str(product.get("pin_title") or product.get("Title") or product.get("title") or "")
    description = str(product.get("pin_description") or product.get("Description") or product.get("google_description") or "")
    link = product.get("pin_link") or product.get("affiliate_link") or product.get("manual_link") or product.get("Link") or ""
    board = product.get("pin_board") or product.get("board_suggested") or product.get("Pinterest board") or "Viral Amazon Finds"
    return {
        "Title": title[:100],
        "Media URL": _public_media_url(product),
        "Pinterest board": board,
        "Thumbnail": "",
        "Description": description[:500],
        "Link": link,
        "Publish date": "",
        "Keywords": _keywords(product),
    }


def save_pinterest_upload_csv(products: list[dict], path: str = PINTEREST_UPLOAD_CSV) -> str | None:
    rows = [build_row(product) for product in products if _public_media_url(product)]
    if not rows:
        return None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    return path
