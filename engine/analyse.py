"""analyse(): runs the rule engine and the AI check, merges, scores, returns the Result.

Owners: A1 (merge, score, advice) and A2 (the AI call in engine/llm.py).
Follows the shared contract in the team brief. It must NEVER crash during the demo.
"""
import re
from concurrent.futures import ThreadPoolExecutor

from engine.rules import check_rules

WEIGHTS = {"high": 35, "medium": 20, "low": 10}
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
LLM_TIMEOUT_SECONDS = 100   # A2's call has its own ~15s timeout; this is a safety net
MAX_AI_FLAGS = 5
MAX_ADVICE = 6

ADVICE_BY_ID = {
    "pay_before_viewing": "Do not send any money until you have seen the home in person or on a live video call.",
    "landlord_abroad": "Ask for someone local to show you the home. If nobody can, walk away.",
    "odd_payment": "Only pay by UK bank transfer to an account in the landlord's or agent's name. Never use gift cards, crypto or money transfer apps.",
    "off_platform": "Keep talking through the listing site or the agent's official email, so there is a record.",
    "urgency": "Take your time. Ask them to hold the room for 48 hours while you check the details.",
    "no_contract": "Ask to read the tenancy agreement first, and ask which scheme will protect your deposit.",
    "price_too_low": "Compare the price with similar rooms nearby. If it is far cheaper, ask why.",
}
ALWAYS_IF_RISKY = [
    "Check the person is real: ask for the full address and look up the property and its owner (for example on the Land Registry).",
    "If you think you have been targeted, report it to Action Fraud and to the site where you found the listing.",
]


def _empty_result():
    return {
        "score": 0,
        "level": "green",
        "flags": [],
        "advice": ["Paste the text of a listing to check it."],
        "ai_available": False,
    }


def _run_llm(text):
    """Call A2's check_llm(text). Returns (flags, advice, ok). Never raises."""
    executor = None
    try:
        from engine.llm import check_llm  # A2's file; may not exist yet
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(check_llm, text)
        out = future.result(timeout=LLM_TIMEOUT_SECONDS)
        if not isinstance(out, dict) or out.get("error"):
            return [], [], False
        flags = out.get("flags", [])
        advice = out.get("advice", [])
        return (
            flags if isinstance(flags, list) else [],
            advice if isinstance(advice, list) else [],
            True,
        )
    except Exception:
        return [], [], False
    finally:
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)


def _clean_ai_flag(raw, text):
    """Make an AI flag safe and contract shaped. Returns None if unusable."""
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title") or "").strip()
    reason = str(raw.get("reason") or "").strip()
    if not title or not reason:
        return None
    flag_id = re.sub(r"[^a-z0-9]+", "_", str(raw.get("id") or title).lower()).strip("_") or "ai_flag"
    severity = str(raw.get("severity") or "medium").lower()
    if severity not in WEIGHTS:
        severity = "medium"
    quote = str(raw.get("quote") or "").strip()
    # Only keep the quote if it really appears in the listing (stops made up quotes)
    if quote and quote.lower() not in text.lower():
        quote = ""
    return {
        "id": flag_id,
        "title": title,
        "severity": severity,
        "quote": quote,
        "reason": reason,
        "source": "ai",
    }


def _level(score):
    if score >= 60:
        return "red"
    if score >= 30:
        return "amber"
    return "green"


def _build_advice(flags, ai_advice, level):
    """Specific advice first, then the closing lines. The closing lines always keep their
    place, so a very risky listing still tells the student to check the person and report it."""
    if level == "green":
        closing = ["No obvious red flags found, but still view the home and read the tenancy agreement before you pay anything."]
    else:
        closing = list(ALWAYS_IF_RISKY)

    seen = {c.lower() for c in closing}
    specific = []

    def add(line):
        line = str(line).strip()
        if line and line.lower() not in seen:
            seen.add(line.lower())
            specific.append(line)

    for f in flags:
        if f["id"] in ADVICE_BY_ID:
            add(ADVICE_BY_ID[f["id"]])
    for line in ai_advice:
        if isinstance(line, str):
            add(line)
    room = max(0, MAX_ADVICE - len(closing))
    return specific[:room] + closing


def analyse(text, price=None, city=None):
    """Return the Result dict from the shared contract:
    {"score", "level", "flags", "advice", "ai_available"}"""
    try:
        text = text.strip() if isinstance(text, str) else ""
        if not text:
            return _empty_result()

        # 1. Rules (always available)
        flags = check_rules(text, price, city)

        # 2. AI check (may fail, and that is fine)
        ai_flags_raw, ai_advice, ai_ok = _run_llm(text)

        # 3. Merge and dedupe: keep ONE flag per id, and prefer the rule version
        seen = {f["id"] for f in flags}
        ai_added = 0
        for raw in ai_flags_raw:
            if ai_added >= MAX_AI_FLAGS:
                break
            flag = _clean_ai_flag(raw, text)
            if flag and flag["id"] not in seen:
                flags.append(flag)
                seen.add(flag["id"])
                ai_added += 1

        # 4. Sort high to low (stable, so rules keep their order within a level)
        flags.sort(key=lambda f: SEVERITY_ORDER[f["severity"]])

        # 5. Score: sum of weights, capped at 100, with the override
        score = min(100, sum(WEIGHTS[f["severity"]] for f in flags))
        if "pay_before_viewing" in seen and "landlord_abroad" in seen:
            score = max(score, 80)

        level = _level(score)
        return {
            "score": int(score),
            "level": level,
            "flags": flags,
            "advice": _build_advice(flags, ai_advice, level),
            "ai_available": bool(ai_ok),
        }
    except Exception:
        # Last line of defence: never crash the demo
        result = _empty_result()
        result["advice"] = ["Something went wrong while checking. Please try again."]
        return result
