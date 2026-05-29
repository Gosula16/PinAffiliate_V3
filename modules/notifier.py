"""
Telegram Notifier — sends Pinterest-ready product alerts with image,
all pin fields, affiliate link, and SiteStripe button per product.
"""

import requests, logging, os
from datetime import date, datetime
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT

logger = logging.getLogger("publisher.telegram")


# ── Core send functions ───────────────────────────────────────

def _send_text(text: str):
    """Send plain Markdown text message."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        logger.warning("Telegram not configured — skipping notification")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id":    TELEGRAM_CHAT,
                "text":       text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
            },
            timeout=15,
        )
    except Exception as e:
        logger.warning(f"Telegram text send failed: {e}")


def _send_photo(image_url: str, caption: str):
    """Send product image with caption (Pinterest pin preview)."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
            json={
                "chat_id":    TELEGRAM_CHAT,
                "photo":      image_url,
                "caption":    caption[:1024],  # Telegram caption limit
                "parse_mode": "Markdown",
            },
            timeout=15,
        )
    except Exception as e:
        logger.warning(f"Telegram photo send failed: {e} — sending text only")
        _send_text(caption)


def _send_document(file_path: str, caption: str):
    """Send CSV file to Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    try:
        with open(file_path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument",
                data={"chat_id": TELEGRAM_CHAT, "caption": caption, "parse_mode": "Markdown"},
                files={"document": f},
                timeout=30,
            )
        logger.info("CSV sent to Telegram")
    except Exception as e:
        logger.warning(f"Telegram file send failed: {e}")


def notify_manual_csv(csv_path: str, failed_count: int, reason: str = ""):
    """Tell Telegram that manual Pinterest posting CSV is ready."""
    msg = (
        "*Pinterest manual CSV ready*\n"
        f"Pins needing manual post: *{failed_count}*\n"
        f"Reason: `{(reason or 'Pinterest API unavailable')[:200]}`\n"
        "Use the attached CSV fields for Pinterest bulk/manual posting."
    )
    _send_text(msg)
    if csv_path and os.path.exists(csv_path):
        _send_document(csv_path, "*Pinterest-ready fallback CSV*")


# ── Pinterest-format product notification ────────────────────

def notify_product_pin(product: dict, caption: dict):
    """
    Send full Pinterest-ready pin details to Telegram.
    Includes product image, all copy-paste fields, and affiliate link.
    """
    title       = caption.get("title", product.get("title", ""))[:80]
    description = caption.get("description", product.get("pin_description", ""))
    hashtags    = " ".join(f"#{h.lstrip('#')}" for h in caption.get("hashtags", []))
    price       = product.get("price")
    price_str   = f"Rs. {int(price):,}" if price else "Check listing"
    asin        = product.get("asin", "")
    aff_link    = product.get("affiliate_link") or product.get("pin_link", "")
    manual_link = product.get("manual_link", f"https://www.amazon.in/dp/{asin}")
    sitestripe  = product.get("sitestripe_url", f"https://affiliate-program.amazon.in/home/textlink/sitestripe?asin={asin}")
    board       = product.get("pin_board", product.get("board_suggested", "Best Tech Gadgets India"))
    image_url   = product.get("image_url", "")
    rating      = product.get("rating", "")
    has_aff     = product.get("has_affiliate", False)

    # ── Pinterest copy-paste message ─────────────────────────
    msg = f"""📌 *NEW PIN READY — Pinterest Format*
━━━━━━━━━━━━━━━━━━━━━

🏷 *TITLE* _(copy this)_
`{title}`

📝 *DESCRIPTION* _(copy this)_
`{description[:400]}`
`{hashtags}`

💰 *PRICE:* {price_str}
⭐ *RATING:* {rating if rating else "N/A"}
📦 *ASIN:* `{asin}`
🗂 *BOARD:* `{board}`
🖼 *IMAGE SIZE:* `1000 × 1500 px`

━━━━━━━━━━━━━━━━━━━━━
🔗 *LINKS*
"""
    if has_aff and aff_link:
        msg += f"✅ *Affiliate Link* _(copy this)_\n`{aff_link}`\n\n"
    else:
        msg += f"⚠️ *No affiliate tag — use manual link:*\n`{manual_link}`\n\n"
        msg += f"🛒 *Get affiliate link via SiteStripe:*\n{sitestripe}\n\n"

    msg += f"━━━━━━━━━━━━━━━━━━━━━\n🕐 {datetime.now().strftime('%d %b %Y, %I:%M %p IST')}"

    # Send with image if available
    if image_url:
        _send_photo(image_url, msg)
    else:
        _send_text(msg)


# ── Batch summary notification ───────────────────────────────

def notify_batch_done(posted: int, total: int, products: list = None):
    """
    Send batch completion summary with all posted products listed.
    Includes affiliate links and SiteStripe links for each product.
    """
    max_pins = int(os.getenv("MAX_PINS_PER_DAY", 15))
    pct      = min(100, round(total / max_pins * 100))

    msg = f"""✅ *PinAffiliate — Batch Complete*
━━━━━━━━━━━━━━━━━━━━━
📌 Posted this batch: *{posted} pins*
📊 Today total: *{total}/{max_pins}* ({pct}%)
📅 Date: {date.today().strftime('%d %b %Y')}
━━━━━━━━━━━━━━━━━━━━━
"""
    if products:
        msg += "🛍 *Products Posted:*\n"
        for i, p in enumerate(products[:8], 1):  # max 8 in summary
            asin  = p.get("asin", "")
            title = p.get("title", "")[:50]
            price = p.get("price")
            ps    = f"Rs. {int(price):,}" if price else "—"
            aff   = p.get("affiliate_link") or p.get("manual_link", "")
            has_aff = p.get("has_affiliate", False)
            link_label = "✅ Aff" if has_aff else "⚠️ Manual"
            msg += f"\n*{i}. {title}*\n"
            msg += f"   💰 {ps} | {link_label}\n"
            msg += f"   🔗 `{aff}`\n"

    msg += f"\n━━━━━━━━━━━━━━━━━━━━━\n🤖 PinAffiliate | newdro04-21"
    _send_text(msg)


# ── Daily summary with CSV ───────────────────────────────────

def notify_daily_summary(stats: dict, csv_path: str = None):
    """Send daily stats summary. Optionally attach CSV file."""
    today = date.today().isoformat()
    s     = stats.get(today, {})
    posted = s.get("pins_posted", 0)
    errors = s.get("errors", 0)
    status = "✅ All good" if errors == 0 else f"⚠️ {errors} errors — check logs"

    msg = f"""📊 *PinAffiliate — Daily Summary*
━━━━━━━━━━━━━━━━━━━━━
📅 Date: {today}
📌 Pins posted: *{posted}*
❌ Errors: *{errors}*
🔰 Status: {status}
━━━━━━━━━━━━━━━━━━━━━
📁 Products CSV attached below ↓
🤖 PinAffiliate | newdro04-21"""

    _send_text(msg)

    # Attach CSV
    if csv_path and os.path.exists(csv_path):
        _send_document(csv_path, "📥 *Today's Product Sheet — All Pinterest Fields*")


# ── Error & alert notifications ──────────────────────────────

def notify_error(module: str, error: str):
    _send_text(
        f"🔴 *PinAffiliate ERROR — {module}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"`{str(error)[:300]}`\n"
        f"🕐 {datetime.now().strftime('%I:%M %p IST')}"
    )


def notify_token_expired():
    _send_text(
        "⚠️ *PinAffiliate ALERT — Pinterest Token Expired!*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "1. Go to developers.pinterest.com\n"
        "2. Open your app → Generate new token\n"
        "3. Update PINTEREST_ACCESS_TOKEN in GitHub Secrets\n"
        "4. Re-run the workflow"
    )


def notify_startup():
    _send_text(
        f"🚀 *PinAffiliate Started*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 {datetime.now().strftime('%d %b %Y, %I:%M %p IST')}\n"
        f"🎯 Niche: Electronics & Gadgets\n"
        f"🏷 Tag: newdro04-21\n"
        f"Pipeline running..."
    )
