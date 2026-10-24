import base64, json, os, re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

PROVIDERS = {
    "ollama": {
        "base_url": os.getenv("OLLAMA_URL", "http://localhost:11434/v1/"),
        "api_key": "ollama",
        "model": os.getenv("OLLAMA_MODEL", "gemma4:e4b"),
        "timeout": 90,
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": os.getenv("GEMINI_API_KEY", ""),
        "model": os.getenv("GEMINI_MODEL", "gemma-4-31b-it"),
        "timeout": 90,
    },
}
PROVIDER_ORDER = [p.strip() for p in os.getenv("PROVIDER_ORDER", "gemini,ollama").split(",") if p.strip()]
VALID_SEVERITY = {"high", "medium", "low"}

PROMPT = """You are a UK student housing scam detector.
Analyse the rental listing (text and/or screenshot) and return ONLY valid JSON,
no other text, in exactly this shape:
one JSON object with two keys.
"flags": a list of objects, each with keys id (snake_case), title (2-5 words),
severity (high, medium or low), quote (text copied exactly from the listing)
and reason (one sentence a student understands).
"advice": a list of 2-4 short practical next steps.
Fill every value from THIS listing. Output the JSON object once, nothing else.
Look for: paying before a viewing, landlord abroad or unavailable, pressure or urgency,
moving chat off the platform (WhatsApp, email), unusual payment methods
(bank transfer to a personal account, Western Union, crypto, gift cards),
no contract or refusing ID, a price that seems too good to be true,
an inconsistent story, or templated/copied text.
Use these ids when they fit: pay_before_viewing, landlord_abroad, odd_payment, off_platform, urgency, no_contract, price_too_low. Only invent a new snake_case id for a sign that none of these cover.
Max 5 flags. The quote MUST be copied exactly from the listing.
If the listing looks legitimate, return "flags": [] with 2-3 helpful general tips.
Write advice for a stressed student: short and practical."""


def _build_messages(text, image_bytes, image_mime):
    listing = text.strip() if text and text.strip() else "(no text, see screenshot)"
    content = [{"type": "text", "text": f"{PROMPT}\n\nLISTING:\n{listing}"}]
    if image_bytes:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        content.append({"type": "image_url", "image_url": {"url": f"data:{image_mime};base64,{b64}"}})
    return [{"role": "user", "content": content}]


def _parse_json(raw):
    raw = re.sub(r"`{3}(?:json)?", "", raw)
    decoder = json.JSONDecoder()
    found = []
    i = 0
    while i < len(raw):
        if raw[i] == "{":
            try:
                obj, j = decoder.raw_decode(raw, i)
                if isinstance(obj, dict):
                    found.append(obj)
                i = j
                continue
            except json.JSONDecodeError:
                pass
        i += 1
    with_flags = [o for o in found if "flags" in o]
    if with_flags:
        return with_flags[-1]
    if found:
        return found[-1]
    print("[llm] raw model output was:", raw[:500])
    raise ValueError("no JSON object in model output")


def _clean_flags(flags, text, has_image):
    cleaned = []
    lowered = (text or "").lower()
    for f in flags[:5]:
        if not isinstance(f, dict):
            continue
        title = str(f.get("title", "")).strip()
        if not title or title.lower() == "short label":
            continue
        severity = str(f.get("severity", "medium")).lower().strip()
        if severity not in VALID_SEVERITY:
            severity = "medium"
        quote = str(f.get("quote", "")).strip()
        if quote and not has_image and quote.lower() not in lowered:
            quote = ""
        flag_id = re.sub(r"[^a-z0-9]+", "_", str(f.get("id") or title).lower()).strip("_") or "ai_flag"
        cleaned.append({"id": flag_id, "title": title, "severity": severity, "quote": quote,
                        "reason": str(f.get("reason", "")).strip(), "source": "ai"})
    return cleaned


def check_llm(text, image_bytes=None, image_mime="image/png"):
    if not (text and text.strip()) and not image_bytes:
        return {"flags": [], "advice": [], "error": True}
    messages = _build_messages(text, image_bytes, image_mime)
    for name in PROVIDER_ORDER:
        cfg = PROVIDERS.get(name)
        if not cfg:
            continue
        if name == "gemini" and not cfg["api_key"]:
            print("[llm] skipping gemini: no GEMINI_API_KEY in .env")
            continue
        try:
            client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"], timeout=cfg["timeout"])
            resp = client.chat.completions.create(model=cfg["model"], messages=messages, temperature=0.2)
            data = _parse_json(resp.choices[0].message.content or "")
            advice = [str(a).strip() for a in data.get("advice", []) if str(a).strip()][:5]
            return {"flags": _clean_flags(data.get("flags", []), text, bool(image_bytes)),
                    "advice": advice, "model": f"{name}:{cfg['model']}"}
        except Exception as e:
            print(f"[llm] {name} failed: {type(e).__name__}: {e}")
    return {"flags": [], "advice": [], "error": True}


if __name__ == "__main__":
    sample = ("Lovely double room near Surrey uni, £350/month all bills included. "
              "I'm currently working abroad so can't show the flat, but my agent will post the keys. "
              "Send £500 deposit today by bank transfer to secure it, many people interested. "
              "WhatsApp me on 07700 900123.")
    print(json.dumps(check_llm(sample), indent=2))
