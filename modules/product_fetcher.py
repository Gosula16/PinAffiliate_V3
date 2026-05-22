"""M2 — Product Fetcher: Gadgets only, all fields, CSV, affiliate + manual links."""

import json, logging, os, time, random, re, requests, csv
from html import unescape
from datetime import datetime, timedelta
from urllib.parse import parse_qs, quote_plus, urlparse
from config import (AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY, AMAZON_PARTNER_TAG,
                    PRODUCTS_FILE, PRODUCTS_CSV, POSTED_LOG, DATA_DIR,
                    MAX_PRODUCTS_PER_KW, ASIN_REPOST_DAYS, GADGET_KEYWORDS)

logger = logging.getLogger("pinbot.products")


def _posted_asins():
    if not os.path.exists(POSTED_LOG): return set()
    with open(POSTED_LOG) as f: log = json.load(f)
    cutoff = datetime.now() - timedelta(days=ASIN_REPOST_DAYS)
    return {e["asin"] for e in log if datetime.fromisoformat(e["posted_at"]) > cutoff}


def _aff_link(asin):
    if AMAZON_PARTNER_TAG:
        return f"https://www.amazon.in/dp/{asin}?tag={AMAZON_PARTNER_TAG}"
    return None

def _manual_link(asin):
    return f"https://www.amazon.in/dp/{asin}"

def _sitestripe(asin):
    # SiteStripe appears on the Amazon product page when the Associate is logged in.
    # The Associate Central textlink URL redirects to the SiteStripe help/home page.
    return _manual_link(asin)

def _search_url(keyword):
    return f"https://www.amazon.in/s?k={quote_plus(keyword)}&i=electronics"


def _clean_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return unescape(re.sub(r"\s+", " ", value)).strip()


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
        # Pinterest ready fields
        "pin_title":      f"Best {keyword.title()} India 2026 | Top Pick",
        "pin_description":(f"Looking for the best {kw} in India? "
                           f"This top-rated gadget is available for {price_str} on Amazon. "
                           f"Check the link for full specs and today's lowest price! "
                           f"#{kw.replace(' ','')} #amazonindia #gadgets #techindia"),
        "pin_link":       aff or manual,
        "pin_board":      "Best Tech Gadgets India",
        "pin_image_size": "1000x1500px",
        "pin_alt_text":   f"{title} — available on Amazon India",
    }


def _product_page(asin: str, source_url: str | None = None) -> dict | None:
    """Build a product record from a direct Amazon URL/ASIN."""
    url = source_url or _manual_link(asin)
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
            products.append(product)
            seen.add(asin)
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump({"fetched_at": datetime.now().isoformat(), "products": products}, f, indent=2, ensure_ascii=False)
    _save_csv(products)
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
    use_kw = GADGET_KEYWORDS  # always gadgets only

    all_products, seen = [], set()
    for kw in use_kw:
        logger.info(f"Fetching: {kw}")
        prods = _paapi(kw, MAX_PRODUCTS_PER_KW) or _scrape(kw, MAX_PRODUCTS_PER_KW)
        for p in prods:
            if p["asin"] not in posted and p["asin"] not in seen:
                seen.add(p["asin"])
                all_products.append(p)
        time.sleep(random.uniform(1.0, 2.0))

    # Save JSON
    with open(PRODUCTS_FILE, "w") as f:
        json.dump({"fetched_at": datetime.now().isoformat(), "products": all_products}, f, indent=2, ensure_ascii=False)

    # Save CSV — all fields
    _save_csv(all_products)
    logger.info(f"Saved {len(all_products)} gadgets | CSV + JSON written")
    return all_products


def _save_csv(products):
    if not products: return
    fields = ["asin","title","price","currency","rating","reviews","keyword","category",
              "source","fetched_at","has_affiliate","product_url","affiliate_link","manual_link",
              "sitestripe_url","search_url","pin_title","pin_description","pin_link",
              "pin_board","pin_image_size","pin_alt_text","image_url"]
    with open(PRODUCTS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(products)
    logger.info(f"CSV: {PRODUCTS_CSV}")


def load_products():
    if not os.path.exists(PRODUCTS_FILE): return []
    with open(PRODUCTS_FILE) as f:
        return json.load(f).get("products", [])
