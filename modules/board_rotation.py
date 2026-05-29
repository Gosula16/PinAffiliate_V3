"""Board rotation — schedules re-pins to secondary boards over 3–7 days."""

import json, logging, os
from datetime import datetime, timedelta
from config import PINTEREST_BOARDS, DATA_DIR

logger = logging.getLogger("publisher.rotation")

ROTATION_FILE = os.path.join(DATA_DIR, "rotation_queue.json")

# How many days after first post to re-pin on secondary boards
ROTATION_SCHEDULE = [
    {"days": 2, "board_key": "deals",   "label": "Re-pin to Deals board"},
    {"days": 5, "board_key": "home",    "label": "Re-pin to broader board"},
]


def queue_rotation(asin: str, first_pin_id: str, primary_board: str):
    """After posting, queue this pin for re-pinning on future days."""
    os.makedirs(DATA_DIR, exist_ok=True)
    queue = _load_queue()
    now = datetime.now()
    for sched in ROTATION_SCHEDULE:
        target_board = PINTEREST_BOARDS.get(sched["board_key"], "")
        if not target_board or target_board == primary_board:
            continue
        queue.append({
            "asin":         asin,
            "source_pin_id": first_pin_id,
            "target_board": target_board,
            "scheduled_for": (now + timedelta(days=sched["days"])).isoformat(),
            "label":        sched["label"],
            "done":         False,
        })
    _save_queue(queue)
    logger.info(f"Queued {len(ROTATION_SCHEDULE)} rotation tasks for ASIN {asin}")


def get_due_rotations() -> list[dict]:
    """Returns rotation tasks that are due today or overdue."""
    queue = _load_queue()
    now   = datetime.now()
    due   = [r for r in queue if not r["done"] and datetime.fromisoformat(r["scheduled_for"]) <= now]
    logger.info(f"{len(due)} rotation tasks due")
    return due


def mark_rotation_done(asin: str, target_board: str):
    queue = _load_queue()
    for r in queue:
        if r["asin"] == asin and r["target_board"] == target_board:
            r["done"] = True
    _save_queue(queue)


def _load_queue() -> list:
    if not os.path.exists(ROTATION_FILE):
        return []
    with open(ROTATION_FILE) as f:
        return json.load(f)


def _save_queue(queue: list):
    with open(ROTATION_FILE, "w") as f:
        json.dump(queue, f, indent=2)
