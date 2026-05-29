"""PinAffiliateBot — Complete Pipeline with Telegram Pinterest-format notifications."""

import logging, os, sys, json, time, random
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("output/images", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("pinbot.main")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.trend_engine    import load_trends, fetch_trends
from modules.product_fetcher import fetch_products, fetch_products_from_urls, load_products, refresh_cached_products
from modules.image_generator import generate_pin_image
from modules.caption_writer  import generate_caption
from modules.pin_poster      import post_batch, pinterest_config_status
from modules.pinterest_csv   import save_pinterest_csv
from modules.board_rotation  import queue_rotation, get_due_rotations, mark_rotation_done
from modules.notifier        import (notify_startup, notify_product_pin,
                                     notify_batch_done, notify_daily_summary,
                                     notify_error, notify_token_expired,
                                     notify_manual_csv)
from modules.scheduler       import (is_posting_window, get_pins_posted_today,
                                     record_pins_posted, record_error,
                                     record_manual_fallback, wait_for_next_window)
from config import MAX_PINS_PER_DAY, POST_WINDOWS, DAILY_STATS, PRODUCTS_CSV


def _fallback_csv(batch_items: list[dict], status: str, reason: str) -> str | None:
    csv_path = save_pinterest_csv(batch_items, status=status, failure_reason=reason)
    if csv_path:
        record_manual_fallback(len(batch_items), csv_path, reason)
        logger.info(f"Pinterest-ready fallback CSV saved: {csv_path}")
        notify_manual_csv(csv_path, len(batch_items), reason)
    return csv_path


def _scheduled_batch_size(in_window: bool, window_pins: int, remaining: int) -> int:
    if in_window and window_pins:
        return min(window_pins, remaining)
    return min(POST_WINDOWS[0]["pins"], remaining)


def run_pipeline(dry_run: bool = False, amazon_urls: list[str] | None = None,
                 wait_for_window: bool = True, scheduled_run: bool = False):
    logger.info("=" * 60)
    logger.info(f"PinAffiliateBot | dry_run={dry_run} | scheduled_run={scheduled_run} | {datetime.now()}")
    logger.info("=" * 60)
    notify_startup()

    # ── Daily cap ────────────────────────────────────────────
    pins_today = get_pins_posted_today()
    if pins_today >= MAX_PINS_PER_DAY:
        logger.info(f"Daily cap reached ({pins_today}/{MAX_PINS_PER_DAY})")
        return
    remaining = MAX_PINS_PER_DAY - pins_today

    # ── Window check ─────────────────────────────────────────
    in_window, window_pins = is_posting_window()
    if not in_window and not dry_run and wait_for_window:
        wait_for_next_window()
        in_window, window_pins = is_posting_window()
    if dry_run and not in_window:
        window_pins = max(w["pins"] for w in POST_WINDOWS)
    if scheduled_run and not wait_for_window:
        batch_size = _scheduled_batch_size(in_window, window_pins, remaining)
    else:
        batch_size = min(window_pins, remaining)
    if batch_size <= 0:
        logger.warning("No posting window is active; run with --scheduled-run to prepare the morning batch without waiting")
        return
    logger.info(f"Batch size: {batch_size} pins")

    # ── M1: Trends ───────────────────────────────────────────
    logger.info("── M1: Trends ──")
    try:
        keywords = [] if amazon_urls else load_trends()
        logger.info(f"  {len(keywords)} keywords ready")
    except Exception as e:
        notify_error("M1 Trends", str(e)); record_error(); return

    # ── M2: Products ─────────────────────────────────────────
    logger.info("── M2: Products ──")
    try:
        if amazon_urls:
            products = fetch_products_from_urls(amazon_urls)
        else:
            products = fetch_products(keywords)
            if not products:
                cached_products = load_products()
                if cached_products and scheduled_run:
                    products = refresh_cached_products(
                        cached_products,
                        reason="Amazon returned no fresh products on scheduled run",
                    )
                else:
                    products = cached_products
        if not products:
            logger.error("No products — aborting"); return
        logger.info(f"  {len(products)} trend-ranked products ready | CSV saved")
    except Exception as e:
        notify_error("M2 Products", str(e)); record_error(); return

    selected = products[:batch_size]

    # ── M3 + M4: Images & Captions ───────────────────────────
    logger.info("── M3+M4: Images & Captions ──")
    batch_items = []
    for product in selected:
        try:
            img_path = generate_pin_image(product)
            if not img_path:
                continue
            caption = generate_caption(product)

            # ── Send Pinterest-format alert to Telegram ───────
            notify_product_pin(product, caption)

            batch_items.append({
                "product":    product,
                "image_path": img_path,
                "caption":    caption,
            })
            logger.info(f"  ✓ {product.get('asin')} — {product.get('title','')[:50]}")
        except Exception as e:
            logger.error(f"  M3/M4 error {product.get('asin')}: {e}")
            record_error()
    logger.info(f"  {len(batch_items)} pins prepared")

    # ── Dry run exit ─────────────────────────────────────────
    if dry_run:
        csv_path = save_pinterest_csv(batch_items, status="dry_run")
        if csv_path:
            logger.info(f"Pinterest-ready CSV saved: {csv_path}")
        logger.info("DRY RUN — skipping post. Check output/images/")
        return

    # ── M5: Post ─────────────────────────────────────────────
    logger.info("── M5: Posting to Pinterest ──")
    try:
        config_ready, config_reason = pinterest_config_status()
        if not config_ready:
            _fallback_csv(batch_items, status="manual_fallback", reason=config_reason)
            logger.info("Pinterest credentials are not configured; skipped API posting and prepared manual CSV")
            return

        result = post_batch(batch_items)
        posted = result["posted"]
        failed = result["failed"]
        record_pins_posted(len(posted))
        logger.info(f"  {len(posted)}/{len(batch_items)} pins posted")

        # Queue board rotations
        for i, result in enumerate(posted):
            try:
                queue_rotation(
                    batch_items[i]["product"]["asin"],
                    result.get("id", ""),
                    result.get("board_id", ""),
                )
            except Exception:
                pass

        # Send batch summary with all products + links to Telegram
        notify_batch_done(
            posted    = len(posted),
            total     = get_pins_posted_today(),
            products  = [item["product"] for item in batch_items],
        )

        if failed:
            csv_path = _fallback_csv(failed, status="failed", reason="Pinterest API post failed")
            logger.warning(f"{len(failed)} pins need manual posting. CSV: {csv_path}")

    except Exception as e:
        if "401" in str(e):
            notify_token_expired()
        else:
            notify_error("M5 Poster", str(e))
        record_error(); return

    # ── Board rotations ───────────────────────────────────────
    try:
        for rot in get_due_rotations():
            logger.info(f"  Rotating {rot['asin']} → {rot['target_board']}")
            time.sleep(random.uniform(90, 180))
            mark_rotation_done(rot["asin"], rot["target_board"])
    except Exception as e:
        logger.warning(f"Rotation error: {e}")

    # ── Daily summary + CSV ───────────────────────────────────
    if os.path.exists(DAILY_STATS):
        with open(DAILY_STATS) as f:
            stats = json.load(f)
        notify_daily_summary(stats, csv_path=PRODUCTS_CSV)

    logger.info("Pipeline complete!")
    logger.info("=" * 60)


def run_scheduler_loop():
    logger.info("Scheduler loop active — Ctrl+C to stop")
    while True:
        try:
            run_pipeline()
        except KeyboardInterrupt:
            logger.info("Stopped."); break
        except Exception as e:
            logger.error(f"Loop error: {e}")
            notify_error("Main Loop", str(e)); record_error()
        time.sleep(300)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="PinAffiliateBot v1.0")
    p.add_argument("--dry-run",  action="store_true", help="Generate but don't post")
    p.add_argument("--once",     action="store_true", help="Run one batch and exit")
    p.add_argument("--loop",     action="store_true", help="Run continuously")
    p.add_argument("--trends",   action="store_true", help="Refresh trends only")
    p.add_argument("--products", action="store_true", help="Fetch products only")
    p.add_argument("--summary",  action="store_true", help="Send Telegram daily summary")
    p.add_argument("--scheduled-run", action="store_true",
                   help="Run one scheduled batch without sleeping; post if Pinterest is configured, otherwise save fallback CSV")
    p.add_argument("--amazon-url", action="append", default=[], help="Amazon product URL/ASIN to pin; repeat for more")
    args = p.parse_args()

    if args.trends:
        fetch_trends()
    elif args.products:
        prods = fetch_products_from_urls(args.amazon_url) if args.amazon_url else fetch_products(load_trends())
        logger.info(f"Manual daily product feed ready: {len(prods)} products")
    elif args.summary:
        if os.path.exists(DAILY_STATS):
            with open(DAILY_STATS) as f:
                notify_daily_summary(json.load(f), csv_path=PRODUCTS_CSV)
    elif args.loop:
        run_scheduler_loop()
    else:
        run_pipeline(
            dry_run=args.dry_run,
            amazon_urls=args.amazon_url,
            wait_for_window=not args.scheduled_run,
            scheduled_run=args.scheduled_run,
        )
