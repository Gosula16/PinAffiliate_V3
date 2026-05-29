"""M4 — Caption Writer: Gemini API — unique Pinterest captions per pin."""

import json, logging, re, requests
from config import GEMINI_API_KEY

logger = logging.getLogger("publisher.captions")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={}"

SYSTEM_PROMPT = """You write Pinterest pin captions for Amazon India gadget products.
Rules:
- Natural helpful tone, NOT like an ad
- Mention price naturally inside sentence
- End with soft CTA: Check link / See full details / Worth a look
- Use 4-6 hashtags only — specific ones like #wirelessearbuds #amazonindia
- No ALL CAPS anywhere
- Return ONLY valid JSON, no markdown fences, no extra text"""

USER_TEMPLATE = """Write Pinterest caption for this Amazon India gadget:
Title: {title}
Price: Rs. {price}
Keyword: {keyword}
Category: {category}

Return this exact JSON:
{{
  "title": "pin title 50-100 chars keyword first",
  "description": "natural description 200-400 chars with price and soft CTA",
  "hashtags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}"""


def _category(product):
    kw = (product.get("keyword","") + " " + product.get("title","")).lower()
    if any(w in kw for w in ["earbuds","headphone","speaker","audio"]): return "Audio Gadgets"
    if any(w in kw for w in ["laptop","keyboard","mouse","monitor","webcam","usb","hub"]): return "Laptop & PC"
    if any(w in kw for w in ["phone","charger","power bank","cable"]): return "Phone Accessories"
    if any(w in kw for w in ["camera","ring light","action","dash"]): return "Camera & Creator"
    if any(w in kw for w in ["smart","wifi","bulb","router","alexa"]): return "Smart Home"
    if any(w in kw for w in ["gaming","game","rgb","controller"]): return "Gaming"
    return "Electronics & Gadgets"


def generate_caption(product):
    price = int(product.get("price") or 0)
    prompt = USER_TEMPLATE.format(
        title    = product.get("title","")[:120],
        price    = f"{price:,}" if price else "check listing",
        keyword  = product.get("keyword","gadget"),
        category = _category(product),
    )
    if GEMINI_API_KEY:
        try:
            url  = GEMINI_URL.format(GEMINI_API_KEY)
            body = {
                "contents":[{"parts":[{"text": SYSTEM_PROMPT + "\n\n" + prompt}]}],
                "generationConfig":{"temperature":0.85,"maxOutputTokens":400}
            }
            r = requests.post(url, json=body, timeout=20)
            r.raise_for_status()
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            text = re.sub(r"^```[a-z]*\n?","",text)
            text = re.sub(r"\n?```$","",text).strip()
            result = json.loads(text)
            if all(k in result for k in ["title","description","hashtags"]):
                logger.info(f"Gemini caption OK — {product.get('asin')}")
                return result
        except Exception as e:
            logger.warning(f"Gemini error: {e} — fallback")
    return _fallback(product)


def _fallback(product):
    kw    = product.get("keyword","gadget").lower()
    price = int(product.get("price") or 0)
    ps    = f"Rs. {price:,}" if price else "at a great price"
    return {
        "title":       f"Best {kw.title()} India 2026 | Top Pick",
        "description": f"Looking for the best {kw} in India? This top-rated gadget is available for {ps} on Amazon — great value for money. Check the link for full specs and today's price.",
        "hashtags":    [kw.replace(" ",""), "amazonindia", "budgetgadgets", "techindia", "amazondeals"],
    }
