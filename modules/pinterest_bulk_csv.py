"""Pinterest Bulk Editor CSV export for one row per product pin."""

import csv
import os
from datetime import datetime

from config import PINTEREST_BULK_CSV

PIN_TEMPLATE_HEADERS = """Campaign ID,Campaign Objective,Campaign Name,Campaign Status,Lifetime Spend Limit,Daily Spend Limit,Campaign Order Line ID,Campaign Third Party Tracking Urls,Campaign Budget,Default Ad Group Budget,Campaign Start Date,Campaign Start Time,Campaign End Date,Campaign End Time,Time Zone,Performance+ daily budget,Campaign Keyword (Match Type NEGATIVE_PHRASE),Campaign Keyword (Match Type NEGATIVE_EXACT),Ad Group ID,Ad Group Name,Ad Group Start Date*,Ad Group Start Time,Ad Group End Date*,Ad Group End Time,Ad Group Budget,Ad Group Pacing Type,Ad Group Budget Type,Ad Group Status,Is Creative Optimization,Max Bid,Monthly Frequency Cap,Ad Group Third Party Tracking Urls,Performance+ Targeting,Ad Placement,Goal Value,Conversion Tag ID,Reporting Event,Conversion Event,Conversion Optimization,Click Window Days,Engagement Window Days,View Window Days,Frequency Target Time Range,Frequency Target,Bid strategy type,Targeting Template ID,Promo Ids,Scheduled Budget Adjustment,Locations,Excluded Locations,Geos,Excluded Geos,Genders,AgeBuckets,Minimum Age,Maximum Age,Languages,Devices,Interests,Included Audiences,Excluded Audiences,Dynamic Retargeting Lookback,Dynamic Retargeting Exclusion,Dynamic Retargeting Event Tag Types,Ad Group Keyword (Match Type BROAD),Ad Group Keyword (Match Type EXACT),Ad Group Keyword (Match Type PHRASE),Ad Group Keyword (Match Type NEGATIVE_PHRASE),Ad Group Keyword (Match Type NEGATIVE_EXACT),Existing Pin ID,Media File Name,Pin Title,Pin Description,Organic Pin URL,Image Alternative Text,Is Ad-only Pin,Promoted Pin Status,Promoted Pin ID,Ad Format,Promoted Pin Name,Promoted Pin URL,Promoted Pin Third Party Tracking Urls,Is Removable Pin Promotion,Carousel Card 1 Image File Name,Carousel Card 1 Title,Carousel Card 1 Description,Carousel Card 1 Organic Pin URL,Carousel Card 1 Destination URL,Carousel Card 1 Android Deep Link,Carousel Card 1 iOS Deep Link,Carousel Card 2 Image File Name,Carousel Card 2 Title,Carousel Card 2 Description,Carousel Card 2 Organic Pin URL,Carousel Card 2 Destination URL,Carousel Card 2 Android Deep Link,Carousel Card 2 iOS Deep Link,Carousel Card 3 Image File Name,Carousel Card 3 Title,Carousel Card 3 Description,Carousel Card 3 Organic Pin URL,Carousel Card 3 Destination URL,Carousel Card 3 Android Deep Link,Carousel Card 3 iOS Deep Link,Carousel Card 4 Image File Name,Carousel Card 4 Title,Carousel Card 4 Description,Carousel Card 4 Organic Pin URL,Carousel Card 4 Destination URL,Carousel Card 4 Android Deep Link,Carousel Card 4 iOS Deep Link,Carousel Card 5 Image File Name,Carousel Card 5 Title,Carousel Card 5 Description,Carousel Card 5 Organic Pin URL,Carousel Card 5 Destination URL,Carousel Card 5 Android Deep Link,Carousel Card 5 iOS Deep Link,Collections Secondary Creative Destination Url,Title Card Organic PinID,Card 1 Organic PinID,Card 2 Organic PinID,Card 3 Organic PinID,Card 4 Organic PinID,Quiz pin question 1 text,Question 1 options text,Quiz pin question 2 text,Question 2 options text,Quiz pin question 3 text,Question 3 options text,Result 1 organic Pin ID,Result 1 iOS deep link url,Result 1 Android deep link url,Result 1 destination url,Result 2 organic Pin ID,Result 2 iOS deep link url,Result 2 Android deep link url,Result 2 destination url,Result 3 organic Pin ID,Result 3 iOS deep link url,Result 3 Android deep link url,Result 3 destination url,Grid Click Type,CTA Selection,Keyword Status,Keyword (Match Type BROAD),Keyword (Match Type EXACT),Keyword (Match Type PHRASE),Keyword (Match Type NEGATIVE_PHRASE),Keyword (Match Type NEGATIVE_EXACT),Product Group ID,Product Group Reference ID,Product Group Name,Product Group Status,Tracking Template,Shopping Collections Hero Pin ID,Shopping Collections Hero Pin URL,Slideshow Collections Title,Slideshow Collections Description,Product Group Selected Ad Image Tag,Is Generate Background,Status,Version"""

HEADERS = next(csv.reader([PIN_TEMPLATE_HEADERS]))


def _image_name(product: dict) -> str:
    asin = product.get("asin") or "pin"
    return f"{asin}_pin.jpg"


def _keywords(product: dict) -> str:
    keyword = product.get("seo_keyword") or product.get("keyword") or ""
    title = product.get("pin_title") or product.get("title") or ""
    return ", ".join([value for value in [keyword, title[:80]] if value])


def save_pinterest_bulk_csv(products: list[dict], path: str = PINTEREST_BULK_CSV) -> str | None:
    if not products:
        return None

    os.makedirs(os.path.dirname(path), exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    rows = []
    for index, product in enumerate(products, start=1):
        row = {header: "" for header in HEADERS}
        title = (product.get("pin_title") or product.get("title") or "")[:100]
        description = (product.get("pin_description") or product.get("google_description") or "")[:500]
        destination = product.get("pin_link") or product.get("affiliate_link") or product.get("manual_link") or ""

        row.update({
            "Campaign Objective": "CONSIDERATION",
            "Campaign Name": f"PinAffiliateBot Daily Finds {today}",
            "Campaign Status": "DRAFT",
            "Campaign Budget": "NO",
            "Time Zone": "America/New_York",
            "Ad Group Name": "Daily product pins",
            "Ad Group Budget Type": "DAILY",
            "Ad Group Status": "DRAFT",
            "Performance+ Targeting": "YES",
            "Ad Placement": "SEARCH,BROWSE",
            "Ad Group Keyword (Match Type BROAD)": _keywords(product),
            "Media File Name": _image_name(product),
            "Pin Title": title,
            "Pin Description": description,
            "Organic Pin URL": destination,
            "Image Alternative Text": (product.get("pin_alt_text") or product.get("title") or title)[:500],
            "Is Ad-only Pin": "NO",
            "Promoted Pin Status": "DRAFT",
            "Ad Format": "STANDARD",
            "Promoted Pin Name": f"{index:02d} {title}"[:256],
            "Promoted Pin URL": destination,
            "Grid Click Type": "DIRECT_TO_DESTINATION",
            "CTA Selection": "SHOP_NOW",
            "Keyword Status": "ACTIVE",
            "Keyword (Match Type BROAD)": _keywords(product),
            "Status": "ready",
            "Version": "BulkSheetVersion=V2",
        })
        rows.append(row)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    return path
