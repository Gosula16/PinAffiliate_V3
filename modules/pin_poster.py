"""M5 — Pin Poster: Posts pins to Pinterest via API v5 with human-like delays."""

import json, logging, os, random, time, requests
from datetime import datetime
from config import (PINTEREST_TOKEN, PINTEREST_BOARDS, POSTED_LOG,
                    MIN_DELAY_SEC, MAX_DELAY_SEC, DATA_DIR)

logger = logging.getLogger("pinbot.poster")

PINTEREST_API = "https://api.pinterest.com/v5"


def _headers():
    return {
        "Authorization": f"Bearer {PINTEREST_TOKEN}",
        "Content-Type":  "application/json",
    }


def _upload_image(image_path: str) -> str | None:
    """Upload image to Pinterest and return media_id."""
    try:
        # Step 1: Register upload
        r = requests.post(
            f"{PINTEREST_API}/media",
            headers=_headers(),
            json={"media_type": "image"},
            timeout=30,
        )
        r.raise_for_status()
        data       = r.json()
        upload_url = data["upload_url"]
        media_id   = data["media_id"]
        upload_params = data.get("upload_parameters", {})

        # Step 2: Upload file
        with open(image_path, "rb") as f:
            files   = {"file": ("pin.jpg", f, "image/jpeg")}
            payload = {k: v for k, v in upload_params.items()}
            upload_r = requests.post(upload_url, data=payload, files=files, timeout=60)
            upload_r.raise_for_status()

        logger.info(f"Image uploaded, media_id={media_id}")
        return media_id
    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        return None


def _pick_board(product: dict) -> str:
    """Pick the most relevant board for a product."""
    kw  = (product.get("keyword", "") + " " + product.get("title", "")).lower()
    if any(w in kw for w in ["earbuds","phone","laptop","charger","gadget","speaker","tablet"]):
        board = PINTEREST_BOARDS.get("tech")
    elif any(w in kw for w in ["kitchen","home","mixer","cooker","lamp","fan","cooler"]):
        board = PINTEREST_BOARDS.get("home")
    elif any(w in kw for w in ["gym","fitness","yoga","sport","dumbbell","protein"]):
        board = PINTEREST_BOARDS.get("fitness")
    else:
        board = PINTEREST_BOARDS.get("deals")
    return board or list(PINTEREST_BOARDS.values())[0]


def post_pin(product: dict, image_path: str, caption: dict) -> dict | None:
    """Post one pin to Pinterest. Returns pin data or None on failure."""
    if not PINTEREST_TOKEN:
        logger.warning("No Pinterest token — skipping post")
        return None

    board_id = _pick_board(product)
    if not board_id:
        logger.error("No board ID configured")
        return None

    # Upload image
    media_id = _upload_image(image_path)
    if not media_id:
        return None

    # Build description with hashtags
    hashtags   = " ".join(f"#{h.lstrip('#')}" for h in caption.get("hashtags", []))
    description = f"{caption.get('description', '')} {hashtags}".strip()[:500]

    payload = {
        "board_id":     board_id,
        "title":        caption.get("title", "")[:100],
        "description":  description,
        "link":         product.get("affiliate_link", ""),
        "alt_text":     product.get("title", "")[:500],
        "media_source": {
            "source_type": "media_id",
            "media_id":    media_id,
        },
    }

    try:
        r = requests.post(
            f"{PINTEREST_API}/pins",
            headers=_headers(),
            json=payload,
            timeout=30,
        )
        r.raise_for_status()
        pin_data = r.json()
        pin_id   = pin_data.get("id")
        logger.info(f"Pin posted! ID={pin_id} ASIN={product.get('asin')}")

        # Log it
        _log_posted(product, pin_id, board_id, image_path)
        return pin_data

    except requests.HTTPError as e:
        logger.error(f"Pinterest API error {e.response.status_code}: {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Post failed: {e}")
        return None


def _log_posted(product: dict, pin_id: str, board_id: str, image_path: str):
    os.makedirs(DATA_DIR, exist_ok=True)
    log = []
    if os.path.exists(POSTED_LOG):
        with open(POSTED_LOG) as f:
            log = json.load(f)
    log.append({
        "asin":       product.get("asin"),
        "pin_id":     pin_id,
        "board_id":   board_id,
        "title":      product.get("title", "")[:80],
        "price":      product.get("price"),
        "image_path": image_path,
        "link":       product.get("affiliate_link"),
        "posted_at":  datetime.now().isoformat(),
    })
    with open(POSTED_LOG, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def post_batch(products_with_data: list[dict]) -> list[dict]:
    """
    Post a batch of pins with random human-like delays between each.
    products_with_data: list of {product, image_path, caption}
    Returns list of successfully posted pin results.
    """
    posted = []
    for i, item in enumerate(products_with_data):
        result = post_pin(item["product"], item["image_path"], item["caption"])
        if result:
            posted.append(result)

        # Human-like delay between pins (skip delay after last pin)
        if i < len(products_with_data) - 1:
            delay = random.uniform(MIN_DELAY_SEC, MAX_DELAY_SEC)
            # Occasionally add a longer "break" pause
            if random.random() < 0.15:
                delay += random.uniform(300, 600)
                logger.info(f"  Taking longer break: {int(delay)}s")
            else:
                logger.info(f"  Waiting {int(delay)}s before next pin...")
            time.sleep(delay)

    logger.info(f"Batch complete: {len(posted)}/{len(products_with_data)} pins posted")
    return posted
