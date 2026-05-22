"""M3 — Image Generator: Creates 1000x1500 Pinterest pins using Pillow."""

import os, random, logging, requests, textwrap
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from config import OUTPUT_IMAGES, IMAGE_TEMPLATES

logger = logging.getLogger("pinbot.images")

CANVAS_W, CANVAS_H = 1000, 1500


def _download_image(url: str) -> Image.Image | None:
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGBA")
        return img
    except Exception as e:
        logger.warning(f"Could not download image {url}: {e}")
        return None


def _get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Try to load a system font, fall back to default."""
    candidates = []
    if bold:
        candidates = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    else:
        candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_rounded_rect(draw, xy, radius, fill):
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
    draw.ellipse([x1, y1, x1 + 2*radius, y1 + 2*radius], fill=fill)
    draw.ellipse([x2 - 2*radius, y1, x2, y1 + 2*radius], fill=fill)
    draw.ellipse([x1, y2 - 2*radius, x1 + 2*radius, y2], fill=fill)
    draw.ellipse([x2 - 2*radius, y2 - 2*radius, x2, y2], fill=fill)


def generate_pin_image(product: dict) -> str | None:
    """
    Creates a Pinterest pin image for a product.
    Returns the saved file path or None on failure.
    """
    os.makedirs(OUTPUT_IMAGES, exist_ok=True)

    tmpl  = random.choice(IMAGE_TEMPLATES)
    bg    = tmpl["bg"]
    fg    = tmpl["text"]
    badge = tmpl["badge"]

    # ── Canvas ──────────────────────────────────────────────────
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), bg)
    draw   = ImageDraw.Draw(canvas)

    # ── Top strip ───────────────────────────────────────────────
    strip_color = tuple(max(0, c - 30) for c in bg)
    draw.rectangle([0, 0, CANVAS_W, 160], fill=strip_color)

    kw = product.get("keyword", "Product Pick").title()
    kw = kw[:40]
    font_strip = _get_font(42, bold=True)
    draw.text((CANVAS_W // 2, 80), kw, font=font_strip, fill=fg, anchor="mm")

    # ── Product image ────────────────────────────────────────────
    img_url = product.get("image_url")
    if img_url:
        prod_img = _download_image(img_url)
        if prod_img:
            prod_img = prod_img.resize((680, 680), Image.LANCZOS)
            # White background box for product
            draw.rectangle([100, 190, 900, 870], fill=(255, 255, 255))
            # Paste centered
            canvas.paste(prod_img, (160, 200), prod_img if prod_img.mode == "RGBA" else None)

    # ── Title text ───────────────────────────────────────────────
    title = product.get("title", "Amazing Product")
    title = title[:90]
    lines = textwrap.wrap(title, width=32)[:3]  # max 3 lines
    font_title = _get_font(38, bold=False)
    y_title = 910
    for line in lines:
        draw.text((CANVAS_W // 2, y_title), line, font=font_title, fill=fg, anchor="mm")
        y_title += 50

    # ── Price badge ──────────────────────────────────────────────
    price = product.get("price")
    if price:
        price_text = f"Rs. {int(price):,}"
    else:
        price_text = "Check Price"

    font_price = _get_font(52, bold=True)
    bbox = draw.textbbox((0, 0), price_text, font=font_price)
    pw = bbox[2] - bbox[0] + 60
    ph = bbox[3] - bbox[1] + 30
    px = (CANVAS_W - pw) // 2
    py = 1080
    _draw_rounded_rect(draw, [px, py, px + pw, py + ph], 18, badge)
    draw.text((CANVAS_W // 2, py + ph // 2), price_text,
              font=font_price, fill=(255, 255, 255), anchor="mm")

    # ── CTA Bottom strip ─────────────────────────────────────────
    draw.rectangle([0, 1360, CANVAS_W, CANVAS_H], fill=strip_color)
    font_cta = _get_font(34, bold=True)
    ctas = [
        "Tap link to buy on Amazon",
        "See full details — link in pin",
        "Check lowest price on Amazon",
        "Limited stock — see price now",
    ]
    draw.text((CANVAS_W // 2, 1430), random.choice(ctas),
              font=font_cta, fill=fg, anchor="mm")

    # ── Watermark ────────────────────────────────────────────────
    font_wm = _get_font(22)
    draw.text((CANVAS_W - 20, CANVAS_H - 20), "via Amazon.in",
              font=font_wm, fill=tuple(min(255, c + 60) for c in bg), anchor="rm")

    # ── Save ─────────────────────────────────────────────────────
    asin = product.get("asin", "unknown")
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{asin}_{tmpl['name']}_{ts}.jpg"
    filepath = os.path.join(OUTPUT_IMAGES, filename)
    canvas.save(filepath, "JPEG", quality=92)

    logger.info(f"Generated image: {filename}")
    return filepath
