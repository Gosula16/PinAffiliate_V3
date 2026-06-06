import os
from dotenv import load_dotenv

load_dotenv()

# Amazon
AMAZON_ACCESS_KEY = os.getenv("AMAZON_ACCESS_KEY", "")
AMAZON_SECRET_KEY = os.getenv("AMAZON_SECRET_KEY", "")
AMAZON_PARTNER_TAG = os.getenv("AMAZON_PARTNER_TAG", "newdro04-21")
AMAZON_MARKETPLACE = os.getenv("AMAZON_MARKETPLACE", "www.amazon.in")

# Pinterest
PINTEREST_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN", "")
PINTEREST_BOARDS = {
    "tech": os.getenv("BOARD_TECH", ""),
    "home": os.getenv("BOARD_HOME", ""),
    "fitness": os.getenv("BOARD_FITNESS", ""),
    "deals": os.getenv("BOARD_DEALS", ""),
}

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Hugging Face optional intelligence checks
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN", "")
HF_TEXT_MODEL = os.getenv("HF_TEXT_MODEL", "cardiffnlp/twitter-roberta-base-sentiment-latest")
HF_ZERO_SHOT_MODEL = os.getenv("HF_ZERO_SHOT_MODEL", "facebook/bart-large-mnli")
HF_IMAGE_MODEL = os.getenv("HF_IMAGE_MODEL", "google/vit-base-patch16-224")
HF_MAX_AI_CALLS = int(os.getenv("HF_MAX_AI_CALLS", 24))
AI_MIN_PRODUCT_SCORE = int(os.getenv("AI_MIN_PRODUCT_SCORE", 55))

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")

# Publisher behaviour
MAX_PINS_PER_DAY = int(os.getenv("MAX_PINS_PER_DAY", 30))
MIN_DELAY_SEC = int(os.getenv("MIN_DELAY_SEC", 180))
MAX_DELAY_SEC = int(os.getenv("MAX_DELAY_SEC", 420))
MAX_PRODUCTS_PER_KW = int(os.getenv("MAX_PRODUCTS_PER_KW", 5))
DAILY_PRODUCT_COUNT = int(os.getenv("DAILY_PRODUCT_COUNT", 30))
ASIN_REPOST_DAYS = int(os.getenv("ASIN_REPOST_DAYS", 30))

# Posting windows (IST 24h)
POST_WINDOWS = [
    {"start": "07:30", "end": "09:00", "pins": 8},
    {"start": "12:00", "end": "13:30", "pins": 7},
    {"start": "18:30", "end": "20:00", "pins": 8},
    {"start": "22:00", "end": "23:00", "pins": 7},
]

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_IMAGES = os.path.join(BASE_DIR, "output", "images")
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
PRODUCTS_CSV = os.path.join(DATA_DIR, "products.csv")
PINTEREST_BULK_CSV = os.path.join(DATA_DIR, "pinterest_bulk_editor.csv")
PINTEREST_UPLOAD_CSV = os.path.join(DATA_DIR, "pinterest_upload.csv")
POSTED_LOG = os.path.join(DATA_DIR, "posted_log.json")
TRENDS_FILE = os.path.join(DATA_DIR, "trends.json")
DAILY_STATS = os.path.join(DATA_DIR, "daily_stats.json")

# Daily product discovery keywords. The trend engine blends live Google Trends
# terms with these evergreen Pinterest/Amazon buyer searches.
TREND_SEED_KEYWORDS = [
    "amazon best sellers",
    "viral amazon finds",
    "tiktok made me buy it",
    "pinterest shopping trends",
    "budget home gadgets",
]

GADGET_KEYWORDS = [
    "viral amazon finds under budget",
    "best wireless earbuds under budget",
    "portable power bank best seller",
    "aesthetic desk setup essentials",
    "home office gadgets under budget",
    "kitchen gadgets trending",
    "home organization products",
    "travel essentials amazon",
    "fitness accessories for home workout",
    "self care products trending",
    "beauty tools under budget",
    "cleaning gadgets for home",
    "car accessories useful",
    "phone accessories trending",
    "laptop accessories best sellers",
    "smart home gadgets budget",
    "creator gadgets ring light microphone",
    "water bottle trending",
    "backpack travel laptop",
    "mini projector budget",
    "air fryer best seller",
    "mixer grinder best seller",
    "vacuum cleaner home budget",
    "office chair ergonomic budget",
    "trimmer for men best seller",
    "fitness band under budget",
    "bluetooth speaker portable",
    "gaming accessories budget",
    "daily deals useful products",
    "gift ideas useful products",
]

PINTEREST_TREND_KEYWORDS = [
    "aesthetic room decor",
    "minimal desk setup",
    "kitchen organization",
    "small space storage",
    "travel packing essentials",
    "gym bag essentials",
    "skincare tools",
    "clean girl routine",
    "work from home setup",
    "budget tech finds",
]

FALLBACK_KEYWORDS = GADGET_KEYWORDS + PINTEREST_TREND_KEYWORDS

# Image templates
IMAGE_TEMPLATES = [
    {"bg": (20, 20, 30), "text": (255, 255, 255), "badge": (230, 57, 70), "name": "dark_red"},
    {"bg": (245, 240, 230), "text": (30, 30, 30), "badge": (39, 174, 96), "name": "cream_green"},
    {"bg": (240, 248, 255), "text": (29, 53, 87), "badge": (69, 123, 157), "name": "light_blue"},
    {"bg": (255, 255, 255), "text": (20, 20, 20), "badge": (230, 57, 70), "name": "minimal_white"},
    {"bg": (29, 53, 87), "text": (255, 255, 255), "badge": (241, 196, 15), "name": "navy_gold"},
]
