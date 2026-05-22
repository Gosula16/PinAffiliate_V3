# PinAffiliateBot v1.0
**Pinterest + Amazon Affiliate Automation — Complete System**

---

## What This Does
1. Fetches trending product keywords from Google India
2. Searches Amazon.in for matching products via PAAPI
3. Generates Pinterest-optimized images (1000×1500px) with Pillow
4. Writes unique AI captions per pin via Anthropic API
5. Posts to Pinterest with human-like random delays
6. Re-pins to secondary boards over 3–7 days automatically
7. Sends Telegram alerts for stats and errors

---

## Folder Structure
```
pinbot/
├── main.py                  # Master runner — start here
├── config.py                # All settings and keys
├── setup.bat                # Windows one-click setup
├── requirements.txt         # pip dependencies
├── .env.example             # Copy to .env and fill keys
├── dashboard.html           # Open in browser for control panel
├── modules/
│   ├── trend_engine.py      # M1: Google Trends
│   ├── product_fetcher.py   # M2: Amazon PAAPI
│   ├── image_generator.py   # M3: Pillow pin images
│   ├── caption_writer.py    # M4: Anthropic AI captions
│   ├── pin_poster.py        # M5: Pinterest API poster
│   ├── scheduler.py         # M6: Posting windows
│   ├── board_rotation.py    # Re-pin to secondary boards
│   ├── notifier.py          # Telegram alerts
│   └── retry.py             # Exponential backoff for APIs
├── output/images/           # Generated pin images saved here
├── data/
│   ├── trends.json          # Today's keywords cache
│   ├── products.json        # Fetched products cache
│   ├── posted_log.json      # Every pin ever posted
│   ├── daily_stats.json     # Daily pin counts
│   └── rotation_queue.json  # Board re-pin schedule
└── logs/
    └── app.log              # Full activity log
```

---

## Step-by-Step Setup

### Step 1 — Run setup.bat
```
Double-click setup.bat
```
This installs all Python packages and creates folders.

### Step 2 — Get Your API Keys

**Amazon Associates + PAAPI:**
1. Sign up: https://affiliate-program.amazon.in
2. Make 3 qualifying sales to unlock PAAPI
3. Go to: Associates Central → Tools → Product Advertising API
4. Copy: Access Key, Secret Key, Partner Tag (format: yourname-21)

**Pinterest Developer Token:**
1. Go to: https://developers.pinterest.com
2. Create App → Generate Access Token
3. Enable scopes: `pins:read_write` and `boards:read`
4. Copy your Board IDs from each board's URL

**Anthropic API Key:**
1. Go to: https://console.anthropic.com
2. Create API key → copy it

**Telegram Bot (optional but recommended):**
1. Message @BotFather on Telegram → /newbot
2. Copy your bot token
3. Get your Chat ID from @userinfobot

### Step 3 — Fill .env file
```
Copy .env.example → rename to .env
Fill in all your keys
```

### Step 4 — Test Run (no posting)
```bash
python main.py --dry-run
```
Check `output/images/` — you should see generated pin images.

### Step 5 — First Real Run
```bash
python main.py --once
```
Posts one batch to Pinterest. Check your Pinterest account.

### Step 6 — Full Auto Mode
```bash
python main.py --loop
```
Runs continuously, respects posting windows, auto-schedules.

---

## All Commands
```bash
python main.py --dry-run    # Test without posting — check images
python main.py --once       # Post one batch now
python main.py --loop       # Run continuously (for VPS/always-on PC)
python main.py --trends     # Refresh trends only
python main.py --products   # Fetch products only
python main.py --summary    # Send Telegram daily summary
```

---

## Posting Schedule (IST)
| Window | Time | Pins |
|--------|------|------|
| Morning | 07:30 – 09:00 | 5 |
| Lunch | 12:00 – 13:00 | 4 |
| Evening | 18:30 – 20:00 | 5 |
| Night | 22:00 – 23:00 | 3 |
| **Total/day** | | **17** |

Delays between pins: **3–7 minutes random** (human-like)

---

## Anti-Ban Rules (CRITICAL)
- Week 1: max 8 pins/day — set `MAX_PINS_PER_DAY=8` in .env
- Week 2: increase to 12
- Week 3: increase to 17
- Never run before 7 AM or after 11 PM
- Manually like/save a few pins per day from your account
- Verify your website domain in Pinterest settings

---

## Expandability Roadmap
- V1.5: Add Flipkart affiliate as second source
- V2.0: Multi-account manager (10+ accounts)
- V2.5: Hindi/Hinglish captions for regional reach
- V3.0: Video pins via MoviePy, Idea Pins support

---

## Troubleshooting
| Problem | Fix |
|---------|-----|
| Pinterest 401 error | Token expired — generate new OAuth token |
| PAAPI empty results | Check partner tag, wait for 3 sales quota |
| Images not generating | Install Pillow: `pip install Pillow` |
| pytrends blocked | Falls back to evergreen keywords automatically |
| No products showing | Run `python main.py --products` to debug |
