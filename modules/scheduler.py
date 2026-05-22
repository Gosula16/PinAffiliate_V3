"""M6 — Scheduler: Runs the pipeline on a daily schedule with posting windows."""

import logging, json, os, random, time
from datetime import datetime, date
from config import POST_WINDOWS, MAX_PINS_PER_DAY, DAILY_STATS, DATA_DIR

logger = logging.getLogger("pinbot.scheduler")


def is_posting_window() -> tuple[bool, int]:
    """Returns (is_in_window, pins_allowed_this_window)."""
    now = datetime.now().strftime("%H:%M")
    for window in POST_WINDOWS:
        if window["start"] <= now <= window["end"]:
            return True, window["pins"]
    return False, 0


def get_pins_posted_today() -> int:
    if not os.path.exists(DAILY_STATS):
        return 0
    with open(DAILY_STATS) as f:
        stats = json.load(f)
    today = date.today().isoformat()
    return stats.get(today, {}).get("pins_posted", 0)


def record_pins_posted(count: int):
    os.makedirs(DATA_DIR, exist_ok=True)
    stats = {}
    if os.path.exists(DAILY_STATS):
        with open(DAILY_STATS) as f:
            stats = json.load(f)
    today = date.today().isoformat()
    if today not in stats:
        stats[today] = {"pins_posted": 0, "errors": 0}
    stats[today]["pins_posted"] += count
    with open(DAILY_STATS, "w") as f:
        json.dump(stats, f, indent=2)


def record_error():
    os.makedirs(DATA_DIR, exist_ok=True)
    stats = {}
    if os.path.exists(DAILY_STATS):
        with open(DAILY_STATS) as f:
            stats = json.load(f)
    today = date.today().isoformat()
    if today not in stats:
        stats[today] = {"pins_posted": 0, "errors": 0}
    stats[today]["errors"] += 1
    with open(DAILY_STATS, "w") as f:
        json.dump(stats, f, indent=2)


def wait_for_next_window():
    """Sleep until the next posting window opens."""
    now = datetime.now().strftime("%H:%M")
    for window in POST_WINDOWS:
        if window["start"] > now:
            # Calculate seconds until this window
            h, m = map(int, window["start"].split(":"))
            cn = datetime.now()
            target = cn.replace(hour=h, minute=m, second=0, microsecond=0)
            wait = (target - cn).total_seconds()
            if wait > 0:
                logger.info(f"Next window at {window['start']} — waiting {int(wait/60)} min")
                time.sleep(wait)
                return
    # No more windows today — wait until tomorrow's first window
    h, m = map(int, POST_WINDOWS[0]["start"].split(":"))
    cn = datetime.now()
    tomorrow = cn.replace(hour=h, minute=m, second=0, microsecond=0)
    if tomorrow < cn:
        from datetime import timedelta
        tomorrow += timedelta(days=1)
    wait = (tomorrow - cn).total_seconds()
    logger.info(f"No more windows today — sleeping until tomorrow {POST_WINDOWS[0]['start']}")
    time.sleep(wait)
