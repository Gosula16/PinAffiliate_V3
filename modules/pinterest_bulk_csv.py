"""Pinterest Ads Bulk Editor CSV export.

Pinterest's Ads Bulk Editor rejects files that do not preserve the current
template's header + instruction rows. This module writes product ads onto the
bundled one-row-per-ad v2 template and uses public image URLs in the
"Media File Name" column so no separate media upload is needed.
"""

import csv
import os
from datetime import datetime

from config import BASE_DIR, PINTEREST_BULK_CSV

TEMPLATE_PATH = os.path.join(BASE_DIR, "data", "bulk_editor_template_one_row_per_ad_v2.csv")


def _read_template_rows() -> tuple[list[str], list[list[str]]]:
    with open(TEMPLATE_PATH, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if len(rows) < 3:
        raise ValueError("Pinterest bulk editor template must include header and instruction rows")
    return rows[0], rows[1:3]


def _keywords(product: dict) -> str:
    values = [
        product.get("seo_keyword") or product.get("keyword") or "",
        product.get("trend_label") or "",
        product.get("buyer_intent") or "",
        product.get("quality_grade") or "",
        "amazon finds",
        "daily finds",
    ]
    seen = []
    for value in values:
        value = str(value).strip()
        if value and value.lower() not in {item.lower() for item in seen}:
            seen.append(value)
    return ", ".join(seen)


def _media_url(product: dict) -> str:
    image_url = product.get("image_url") or ""
    return image_url if image_url.startswith(("http://", "https://")) else ""


def _row(product: dict, index: int, today: str) -> dict:
    title = str(product.get("pin_title") or product.get("title") or "")[:100]
    description = str(product.get("pin_description") or product.get("google_description") or "")[:500]
    destination = product.get("pin_link") or product.get("affiliate_link") or product.get("manual_link") or ""
    keyword = _keywords(product)
    return {
        "Campaign Objective": "CONSIDERATION",
        "Campaign Name": f"PinAffiliate Daily Finds {today}",
        "Campaign Status": "DRAFT",
        "Campaign Budget": "NO",
        "Time Zone": "Asia/Kolkata",
        "Ad Group Name": "Daily Pinterest product pins",
        "Ad Group Budget": "100.00",
        "Ad Group Pacing Type": "STANDARD",
        "Ad Group Budget Type": "DAILY",
        "Ad Group Status": "DRAFT",
        "Performance+ Targeting": "YES",
        "Ad Placement": "SEARCH,BROWSE",
        "Ad Group Keyword (Match Type BROAD)": keyword,
        "Media File Name": _media_url(product),
        "Pin Title": title,
        "Pin Description": description,
        "Organic Pin URL": destination,
        "Image Alternative Text": str(product.get("pin_alt_text") or product.get("title") or title)[:500],
        "Is Ad-only Pin": "NO",
        "Promoted Pin Status": "DRAFT",
        "Ad Format": "STANDARD",
        "Promoted Pin Name": f"{index:02d} {title}"[:256],
        "Promoted Pin URL": destination,
        "Is Removable Pin Promotion": "NO",
        "Grid Click Type": "DIRECT_TO_DESTINATION",
        "CTA Selection": "SHOP_NOW",
        "Keyword Status": "ACTIVE",
        "Keyword (Match Type BROAD)": keyword,
        "Version": "BulkSheetVersion=V2",
    }


def save_pinterest_bulk_csv(products: list[dict], path: str = PINTEREST_BULK_CSV) -> str | None:
    rows = [product for product in products if _media_url(product)]
    if not rows:
        return None

    headers, instruction_rows = _read_template_rows()
    today = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(instruction_rows)
        for index, product in enumerate(rows, start=1):
            values = {header: "" for header in headers}
            values.update(_row(product, index, today))
            writer.writerow([values.get(header, "") for header in headers])
    return path
