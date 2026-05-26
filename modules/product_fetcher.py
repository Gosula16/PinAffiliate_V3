"""M2 — Product Fetcher: Gadgets only, all fields, CSV, affiliate + manual links."""

import json, logging, os, time, random, re, requests, csv
from html import unescape
from datetime import datetime, timedelta
from urllib.parse import parse_qs, quote_plus, urlparse
from config import (AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY, AMAZON_PARTNER_TAG, AMAZON_MARKETPLACE,
                    PRODUCTS_FILE, PRODUCTS_CSV, POSTED_LOG, DATA_DIR,
                    MAX_PRODUCTS_PER_KW, DAILY_PRODUCT_COUNT, ASIN_REPOST_DAYS,
                    GADGET_KEYWORDS)
from modules.pinterest_bulk_csv import save_pinterest_bulk_csv

logger = logging.getLogger("pinbot.products")


def _posted_asins():
    if not os.path.exists(POSTED_LOG): return set()
    with open(POSTED_LOG) as f: log = json.load(f)
    cutoff = datetime.now() - timedelta(days=ASIN_REPOST_DAYS)
    return {e["asin"] for e in log if datetime.fromisoformat(e["posted_at"]) > cutoff}


def _aff_link(asin):
    if AMAZON_PARTNER_TAG:
        return f"https://{AMAZON_MARKETPLACE}/dp/{asin}?tag={AMAZON_PARTNER_TAG}"
    return None

def _manual_link(asin):
    return f"https://{AMAZON_MARKETPLACE}/dp/{asin}"

def _sitestripe(asin):
    # SiteStripe appears on the Amazon product page when the Associate is logged in.
    # The Associate Central textlink URL redirects to the SiteStripe help/home page.
    return _manual_link(asin)

def _search_url(keyword):
    return f"https://{AMAZON_MARKETPLACE}/s?k={quote_plus(keyword)}"


def _clean_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return unescape(re.sub(r"\s+", " ", value)).strip()


def _short_title(title: str, max_len: int = 64) -> str:
    title = re.split(r"\s+[|(-]\s*", title)[0].strip() or title
    title = re.sub(r"\b(with|for)\b.*$", "", title, flags=re.I).strip() or title
    return title[:max_len].rstrip(" ,|-")


def _display_keyword(keyword: str) -> str:
    keyword = re.sub(r"^best\s+", "", keyword.strip(), flags=re.I)
    return keyword.title()


def _trend_label(keyword: str) -> str:
    keyword = keyword.lower()
    if any(word in keyword for word in ["viral", "tiktok", "pinterest", "aesthetic"]):
        return "viral trend"
    if any(word in keyword for word in ["best seller", "best sellers", "amazon"]):
        return "best seller"
    if any(word in keyword for word in ["under", "budget", "deal"]):
        return "budget pick"
    return "daily trend"


def _review_count(value) -> int:
    if value is None:
        return 0
    digits = re.sub(r"[^0-9]", "", str(value))
    return int(digits) if digits else 0


def _product_score(product: dict) -> float:
    rating = float(product.get("rating") or 0)
    reviews = _review_count(product.get("reviews"))
    price = float(product.get("price") or 0)
    score = rating * 18
    score += min(35, reviews ** 0.5 / 3)
    if product.get("image_url"):
        score += 8
    if product.get("has_affiliate"):
        score += 5
    if 499 <= price <= 4999:
        score += 7
    elif 5000 <= price <= 14999:
        score += 3
    elif price > 15000:
        score -= 8
    score += float(product.get("trend_score") or 0)
    return round(score, 2)


def _board_for_keyword(keyword: str) -> str:
    kw = keyword.lower()
    if any(w in kw for w in ["kitchen", "air fryer", "mixer", "vacuum", "home", "decor", "storage", "organ"]):
        return "Trending Home Finds"
    if any(w in kw for w in ["fitness", "gym", "workout", "trimmer", "self care", "beauty", "skincare"]):
        return "Wellness Beauty And Fitness Finds"
    if any(w in kw for w in ["travel", "backpack", "car"]):
        return "Travel And Everyday Essentials"
    if any(w in kw for w in ["desk", "office", "laptop", "phone", "tech", "gadget", "gaming"]):
        return "Budget Tech And Desk Setup"
    return "Viral Amazon Finds"


def extract_asin(value: str) -> str | None:
    """Extract an ASIN from common Amazon product URL formats or raw ASIN text."""
    if not value:
        return None
    value = value.strip()
    if re.fullmatch(r"[A-Z0-9]{10}", value):
        return value
    for pattern in (
        r"/dp/([A-Z0-9]{10})",
        r"/gp/product/([A-Z0-9]{10})",
        r"/product/([A-Z0-9]{10})",
        r"/([A-Z0-9]{10})(?:[/?]|$)",
    ):
        match = re.search(pattern, value)
        if match:
            return match.group(1)
    parsed = urlparse(value)
    for key in ("asin", "ASIN"):
        asin = parse_qs(parsed.query).get(key, [None])[0]
        if asin and re.fullmatch(r"[A-Z0-9]{10}", asin):
            return asin
    return None


def _build(asin, title, price, img, rating, reviews, keyword, source):
    aff  = _aff_link(asin)
    manual = _manual_link(asin)
    kw   = keyword.lower()
    price_str = f"Rs. {int(price):,}" if price else "check listing"
    short = _short_title(title)
    board = _board_for_keyword(keyword)
    display_kw = _display_keyword(keyword)
    trend_label = _trend_label(keyword)
    google_title = f"{short} | {display_kw} Price, Review And Deals"
    google_description = (
        f"{short} is a {trend_label} for {kw}. Compare current price, rating, "
        f"features and exact Amazon product link before you buy."
    )
    return {
        "asin":           asin,
        "title":          title,
        "price":          price,
        "currency":       "INR",
        "image_url":      img or "",
        "rating":         rating,
        "reviews":        reviews,
        "keyword":        keyword,
        "category":       "Electronics & Gadgets",
        "source":         source,
        "fetched_at":     datetime.now().isoformat(),
        # Links
        "has_affiliate":  bool(aff),
        "product_url":    manual,
        "affiliate_link": aff or "",
        "manual_link":    manual,
        "sitestripe_url": _sitestripe(asin),
        "search_url":     _search_url(keyword),
        "trend_label":    trend_label,
        "seo_keyword":    keyword,
        "google_title":   google_title[:120],
        "google_description": google_description[:220],
        # Pinterest ready fields
        "pin_title":      f"{short} | {display_kw}"[:100],
        "pin_description":(f"{short} is today's {trend_label} for {kw}. "
                           f"Price: {price_str}. Check the exact product page for specs, reviews "
                           f"and current offers. #{re.sub(r'[^a-z0-9]', '', kw)} #amazonfinds #dailyfinds #budgetshopping"),
        "pin_link":       aff or manual,
        "pin_board":      board,
        "pin_image_size": "1000x1500px",
        "pin_alt_text":   f"{title} available on Amazon",
    }


def _product_page(asin: str, source_url: str | None = None) -> dict | None:
    """Build a product record from a direct Amazon URL/ASIN."""
    url = source_url if source_url and source_url.startswith(("http://", "https://")) else _manual_link(asin)
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
            "Accept-Language": "en-IN,en;q=0.9",
        }
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            logger.warning(f"Amazon product page returned HTTP {r.status_code} for {asin}")
            return _build(asin, f"Amazon gadget {asin}", None, "", None, None, "amazon product", "url")
        html = r.text
        title_match = re.search(r'id="productTitle"[^>]*>(.*?)<', html, re.S)
        image_match = re.search(r'"hiRes"\s*:\s*"([^"]+)"', html) or re.search(r'"large"\s*:\s*"([^"]+)"', html)
        price_match = re.search(r'class="a-price-whole">([0-9,]+)<', html)
        rating_match = re.search(r'([0-9.]+) out of 5', html)
        reviews_match = re.search(r'([\d,]+) ratings', html)
        title = unescape(re.sub(r"\s+", " ", title_match.group(1)).strip()) if title_match else f"Amazon gadget {asin}"
        price = float(price_match.group(1).replace(",", "")) if price_match else None
        image = image_match.group(1).replace("\\/", "/") if image_match else ""
        rating = float(rating_match.group(1)) if rating_match else None
        reviews = reviews_match.group(1) if reviews_match else None
        return _build(asin, title, price, image, rating, reviews, "amazon product", "url")
    except Exception as e:
        logger.warning(f"Direct Amazon URL fetch failed for {asin}: {e}")
        return _build(asin, f"Amazon gadget {asin}", None, "", None, None, "amazon product", "url")


def fetch_products_from_urls(urls: list[str]) -> list[dict]:
    """Fetch Pinterest-ready product records from explicit Amazon URLs or ASINs."""
    os.makedirs(DATA_DIR, exist_ok=True)
    products, seen = [], set()
    for value in urls:
        asin = extract_asin(value)
        if not asin:
            logger.warning(f"Could not extract ASIN from: {value}")
            continue
        if asin in seen:
            continue
        product = _product_page(asin, value)
        if product:
            product["product_score"] = _product_score(product)
            products.append(product)
            seen.add(asin)
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump({"fetched_at": datetime.now().isoformat(), "products": products}, f, indent=2, ensure_ascii=False)
    _save_csv(products)
    save_pinterest_bulk_csv(products)
    return products


def _paapi(keyword, n):
    if not AMAZON_ACCESS_KEY or not AMAZON_SECRET_KEY: return []
    try:
        from amazon.paapi import AmazonApi
        api   = AmazonApi(AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY, AMAZON_PARTNER_TAG, "IN")
        items = api.search_items(keywords=keyword, item_count=n*2)
        out   = []
        for item in (items.items or []):
            try:
                asin  = item.asin
                title = item.item_info.title.display_value
                price = None
                if item.offers and item.offers.listings:
                    price = item.offers.listings[0].price.amount
                img = None
                if item.images and item.images.primary:
                    img = item.images.primary.large.url
                out.append(_build(asin, title, price, img, None, None, keyword, "paapi"))
                if len(out) >= n: break
            except: continue
        return out
    except Exception as e:
        logger.warning(f"PAAPI '{keyword}': {e}")
        return []


def _scrape(keyword, n):
    try:
        url = _search_url(keyword)
        headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Accept-Language":"en-IN,en;q=0.9"}
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200: return []
        matches = list(re.finditer(r'data-asin="([A-Z0-9]{10})"', r.text))
        out = []
        seen = set()
        for i, match in enumerate(matches):
            asin = match.group(1)
            if not asin or asin in seen:
                continue
            seen.add(asin)
            end = matches[i + 1].start() if i + 1 < len(matches) else match.start() + 16000
            block = r.text[match.start():end]

            title_match = (
                re.search(r'<h2[^>]*>.*?<span[^>]*>(.*?)</span>', block, re.S)
                or re.search(r'aria-label="([^"]{20,250})"', block, re.S)
                or re.search(r'<img[^>]+alt="([^"]{20,250})"', block, re.S)
            )
            title = _clean_html(title_match.group(1)) if title_match else keyword.title()
            title = title.rstrip(".")[:220]
            if len(title) < 16 or len(title.split()) < 3:
                continue

            price_match = re.search(r'a-price-whole">([0-9,]+)<', block)
            rating_match = re.search(r'([0-9.]+) out of 5', block)
            reviews_match = re.search(r'([\d,]+) ratings', block)
            image_match = re.search(r'class="s-image"[^>]*src="([^"]+)"', block)
            price = float(price_match.group(1).replace(",","")) if price_match else None
            out.append(_build(
                asin,
                title,
                price,
                image_match.group(1) if image_match else None,
                float(rating_match.group(1)) if rating_match else None,
                reviews_match.group(1) if reviews_match else None,
                keyword, "scrape"
            ))
            if len(out) >= n: break
        return out
    except Exception as e:
        logger.warning(f"Scrape '{keyword}': {e}")
        return []


def fetch_products(keywords=None):
    os.makedirs(DATA_DIR, exist_ok=True)
    posted = _posted_asins()
    use_kw = []
    for keyword in (keywords or []) + GADGET_KEYWORDS:
        normalized = re.sub(r"\s+", " ", str(keyword)).strip()
        if normalized and normalized.lower() not in {k.lower() for k in use_kw}:
            use_kw.append(normalized)

    all_products, seen = [], set()
    for trend_index, kw in enumerate(use_kw):
        logger.info(f"Fetching: {kw}")
        prods = _paapi(kw, MAX_PRODUCTS_PER_KW) or _scrape(kw, MAX_PRODUCTS_PER_KW)
        for p in prods:
            if p["asin"] not in posted and p["asin"] not in seen:
                p["trend_score"] = max(0, 30 - trend_index)
                p["product_score"] = _product_score(p)
                seen.add(p["asin"])
                all_products.append(p)
        time.sleep(random.uniform(1.0, 2.0))

    ranked_products = sorted(
        all_products,
        key=lambda p: (p.get("product_score", 0), _review_count(p.get("reviews")), float(p.get("rating") or 0)),
        reverse=True,
    )
    all_products, seen_titles = [], set()
    for product in ranked_products:
        title_key = re.sub(r"[^a-z0-9]+", " ", _short_title(product.get("title", ""), 52).lower()).strip()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        all_products.append(product)
        if len(all_products) >= DAILY_PRODUCT_COUNT:
            break

    if not all_products:
        logger.warning("No fresh products found; keeping the last good product feed")
        return []

    # Save JSON
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump({"fetched_at": datetime.now().isoformat(), "products": all_products}, f, indent=2, ensure_ascii=False)

    # Save CSV — all fields
    _save_csv(all_products)
    save_pinterest_bulk_csv(all_products)
    logger.info(f"Saved {len(all_products)} trend-ranked products | CSV + JSON written")
    return all_products


def _save_csv(products):
    if not products: return
    fields = ["asin","title","price","currency","rating","reviews","keyword","category",
              "source","fetched_at","has_affiliate","product_url","affiliate_link","manual_link",
              "sitestripe_url","search_url","trend_label","seo_keyword","google_title","google_description",
              "trend_score","product_score","pin_title","pin_description","pin_link",
              "pin_board","pin_image_size","pin_alt_text","image_url"]
    with open(PRODUCTS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(products)
    logger.info(f"CSV: {PRODUCTS_CSV}")


def _coerce_csv_value(value: str):
    value = value or ""
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    number = re.sub(r"[^0-9.]", "", value)
    if number and re.fullmatch(r"\d+(\.\d+)?", number):
        try:
            return float(number) if "." in number else int(number)
        except ValueError:
            return value
    return value


def load_products_csv():
    if not os.path.exists(PRODUCTS_CSV):
        return []
    with open(PRODUCTS_CSV, newline="", encoding="utf-8") as f:
        return [
            {key: _coerce_csv_value(value) for key, value in row.items()}
            for row in csv.DictReader(f)
        ]


def load_products():
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, encoding="utf-8") as f:
            products = json.load(f).get("products", [])
            if products:
                return products
    return load_products_csv()


def refresh_cached_products(products: list[dict], reason: str = "cached fallback") -> list[dict]:
    if not products:
        return []
    now = datetime.now().isoformat()
    refreshed = []
    for product in products:
        item = dict(product)
        item["fetched_at"] = now
        item["queue_date"] = now[:10]
        item["source"] = item.get("source") or "cached"
        item["fallback_reason"] = reason
        refreshed.append(item)
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump({"fetched_at": now, "products": refreshed}, f, indent=2, ensure_ascii=False)
    _save_csv(refreshed)
    save_pinterest_bulk_csv(refreshed)
    logger.info(f"Refreshed {len(refreshed)} cached products for today's queue")
    return refreshed
