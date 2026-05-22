import os
from dotenv import load_dotenv
load_dotenv()

# ── Amazon ────────────────────────────────────────────────────
AMAZON_ACCESS_KEY   = os.getenv("AMAZON_ACCESS_KEY", "")
AMAZON_SECRET_KEY   = os.getenv("AMAZON_SECRET_KEY", "")
AMAZON_PARTNER_TAG  = os.getenv("AMAZON_PARTNER_TAG", "newdro04-21")
AMAZON_MARKETPLACE  = "www.amazon.in"

# ── Pinterest ─────────────────────────────────────────────────
PINTEREST_TOKEN     = os.getenv("PINTEREST_ACCESS_TOKEN", "")
PINTEREST_BOARDS    = {
    "tech":    os.getenv("BOARD_TECH",    ""),
    "home":    os.getenv("BOARD_HOME",    ""),
    "fitness": os.getenv("BOARD_FITNESS", ""),
    "deals":   os.getenv("BOARD_DEALS",  ""),
}

# ── Gemini ────────────────────────────────────────────────────
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY", "")

# ── Telegram ──────────────────────────────────────────────────
TELEGRAM_TOKEN      = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT       = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Bot behaviour ─────────────────────────────────────────────
MAX_PINS_PER_DAY    = int(os.getenv("MAX_PINS_PER_DAY", 8))
MIN_DELAY_SEC       = int(os.getenv("MIN_DELAY_SEC", 180))
MAX_DELAY_SEC       = int(os.getenv("MAX_DELAY_SEC", 420))
MAX_PRODUCTS_PER_KW = 3
ASIN_REPOST_DAYS    = 30

# ── Posting windows (IST 24h) ─────────────────────────────────
POST_WINDOWS = [
    {"start": "07:30", "end": "09:00", "pins": 4},
    {"start": "12:00", "end": "13:00", "pins": 3},
    {"start": "18:30", "end": "20:00", "pins": 5},
    {"start": "22:00", "end": "23:00", "pins": 3},
]

# ── Paths ─────────────────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
OUTPUT_IMAGES  = os.path.join(BASE_DIR, "output", "images")
DATA_DIR       = os.path.join(BASE_DIR, "data")
LOGS_DIR       = os.path.join(BASE_DIR, "logs")
PRODUCTS_FILE  = os.path.join(DATA_DIR, "products.json")
PRODUCTS_CSV   = os.path.join(DATA_DIR, "products.csv")
POSTED_LOG     = os.path.join(DATA_DIR, "posted_log.json")
TRENDS_FILE    = os.path.join(DATA_DIR, "trends.json")
DAILY_STATS    = os.path.join(DATA_DIR, "daily_stats.json")

# ── Gadget keywords (always used — filters non-gadgets out) ──
GADGET_KEYWORDS = [
    "best wireless earbuds under 2000",
    "power bank 20000mah india",
    "gaming mouse budget india",
    "mechanical keyboard india",
    "usb hub laptop india",
    "ring light youtube creator",
    "webcam work from home",
    "laptop stand adjustable",
    "portable bluetooth speaker",
    "smartwatch under 3000 india",
    "action camera budget",
    "dash cam car india",
    "smart bulb wifi india",
    "external ssd 1tb india",
    "gaming headset budget india",
]

# Backward-compatible alias used by the trend engine.
FALLBACK_KEYWORDS = GADGET_KEYWORDS
# ── Fallback keywords (used when pytrends fails) ──────────────
FALLBACK_KEYWORDS = [
    "best wireless earbuds under 2000",
    "power bank 20000mah india",
    "gaming mouse budget india",
    "mechanical keyboard india",
    "usb hub laptop india",
    "ring light youtube creator",
    "webcam work from home",
    "laptop stand adjustable",
    "portable bluetooth speaker",
    "smartwatch under 3000 india",
    "action camera budget",
    "dash cam car india",
    "smart bulb wifi india",
    "external ssd 1tb india",
    "gaming headset budget india",
]

# ── Image templates ───────────────────────────────────────────
IMAGE_TEMPLATES = [
    {"bg": (20,20,30),    "text": (255,255,255), "badge": (230,57,70),  "name": "dark_red"},
    {"bg": (245,240,230), "text": (30,30,30),    "badge": (39,174,96),  "name": "cream_green"},
    {"bg": (240,248,255), "text": (29,53,87),    "badge": (69,123,157), "name": "light_blue"},
    {"bg": (255,255,255), "text": (20,20,20),    "badge": (230,57,70),  "name": "minimal_white"},
    {"bg": (29,53,87),    "text": (255,255,255), "badge": (241,196,15), "name": "navy_gold"},
]
