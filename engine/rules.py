"""Rule engine: fast, predictable red flag checks. Owner: A1.

check_rules(text, price, city) -> list of Flag dicts (see the shared contract in the brief).
Every flag quote is the exact text from the listing, so the UI can show it.
"""
import re

try:
    from data.rent_averages import get_average
except Exception:  # never crash the demo
    def get_average(city):
        return None

PRICE_TOO_LOW_RATIO = 0.6  # flag if price is under 60% of the city average

W = r"[^.!?\n]"  # "any character that stays inside the same sentence"

RULES = [
    {
        "id": "pay_before_viewing",
        "title": "Pay before viewing",
        "severity": "high",
        "reason": "Real landlords let you view the home before taking money.",
        "patterns": [
            # "send £400 to secure", "pay a deposit to reserve", "transfer the fee to hold the room"
            rf"\b(?:send|pay|paying|transfer|deposit|wire)\b{W}{{0,50}}?\b(?:to|and i will|so (?:i|we) can|and we will)\s+(?:secure|reserve|hold|book)\b",
            rf"\b(?:deposit|payment|fee|money)\b{W}{{0,30}}?\b(?:to|will|and)\s+(?:secure|reserve|hold|book)\b",
            # "pay the deposit before viewing", "payment prior to seeing the flat"
            rf"\b(?:pay|paid|payment|deposit|send|transfer|fee)\b{W}{{0,50}}?\b(?:before|prior to|without)\s+(?:a\s+|any\s+|the\s+|you\s+)?(?:view|viewing|viewings|visit|seeing|see)\b",
            # "holding fee" only when it is demanded now or before a viewing
            rf"\b(?:send|transfer|pay|paid)\b{W}{{0,25}}?\bholding (?:fee|deposit)\b{W}{{0,40}}?\b(?:now|today|immediately|asap|first|upfront|before|to (?:secure|reserve|hold))\b",
            rf"\bholding (?:fee|deposit)\b{W}{{0,40}}?\b(?:now|today|immediately|asap|upfront|before (?:a |any |the )?(?:view|viewing|seeing))\b",
            # "no viewings", "cannot arrange a viewing"
            r"\bno viewings?\b(?!\s+(?:fees?|charges?|costs?))",
            r"\bviewings? (?:is |are )?(?:not possible|unavailable|impossible|not available)\b",
            r"\b(?:can'?t|cannot|unable to|not able to) (?:arrange|offer|do|allow) (?:a |any )?viewings?\b",
        ],
    },
    {
        "id": "landlord_abroad",
        "title": "Landlord is abroad",
        "severity": "high",
        "reason": "Scammers often say they are abroad so you can never meet them or see the home.",
        "patterns": [
            rf"\b(?:i am|i'm|im|currently|now|owner is|landlord is|we are|we're|i live|i work)\b{W}{{0,25}}?\b(?:abroad|overseas|out of (?:the )?(?:country|uk|town)|not in the uk|working away|away for work|away on work)\b",
            r"\bworking (?:abroad|overseas|away)\b",
            r"\bliving (?:abroad|overseas)\b",
            # "agent will post the keys", "keys will be couriered"
            rf"\bkeys?\b{W}{{0,40}}?\b(?:posted|post|sent|mailed|couriered|shipped|delivered by (?:post|courier))\b",
            rf"\b(?:post|send|mail|courier|ship)\b{W}{{0,25}}?\bkeys?\b",
        ],
    },
    {
        "id": "odd_payment",
        "title": "Unusual payment method",
        "severity": "high",
        "reason": "Gift cards, crypto and money transfer apps are almost impossible to get back. Real landlords take a normal UK bank transfer.",
        "patterns": [
            r"\bwestern union\b",
            r"\bmoney ?gram\b",
            r"\bbitcoin\b",
            r"\bcrypto\w*\b",
            r"\busdt\b",
            r"\b(?:gift|itunes|google play|amazon|steam) ?cards?\b",
            r"\bpaypal friends\b",
            r"\bfriends (?:and|&) family\b",
            r"\b(?:zelle|cash ?app)\b",
            r"\bcash (?:in|by) (?:the )?post\b",
        ],
    },
    {
        "id": "off_platform",
        "title": "Chat moved off the platform",
        "severity": "medium",
        "reason": "Moving the chat away from the listing site removes its protection and records.",
        "patterns": [
            r"\b(?:whatsapp|telegram|wechat|signal)\s+(?:me|us)\b",
            r"\b(?:contact|message|text|email|e-mail|reach|dm)\s+(?:me|us)\s+(?:directly|privately|outside|off|on\s+(?:whatsapp|telegram|wechat|signal)|via\s+(?:whatsapp|telegram|wechat|signal))",
            r"\b(?:don'?t|do not|no need to|avoid)\s+(?:use|using|go through|message on)\s+(?:the\s+)?(?:site|platform|app|website|spareroom|gumtree|marketplace|facebook)\b",
            rf"\b(?:whatsapp|telegram|wechat)\b{W}{{0,20}}?\bonly\b",
            r"\bonly\s+(?:on\s+)?(?:whatsapp|telegram|wechat)\b",
        ],
    },
    {
        "id": "urgency",
        "title": "Pressure to act fast",
        "severity": "medium",
        "reason": "Scammers rush you so you do not stop to check things.",
        "patterns": [
            rf"\b(?:many|several|lots of|loads of|a lot of|plenty of|multiple)\s+(?:other\s+)?(?:people|students|applicants|viewers|enquiries|inquiries|tenants)\b{W}{{0,30}}?\b(?:interested|waiting|viewing|enquir\w+|inquir\w+|asking)\b",
            r"\b(?:today only|only today|offer ends|ends (?:today|tonight|soon)|first (?:come|to pay|to send|to reserve)|first served|won'?t last|will (?:be )?gone|going fast|last (?:room|chance|one)|hurry|act (?:fast|now|quickly))\b",
            r"\b(?:reply|respond|decide|pay|send)\s+(?:today|now|immediately|asap|within \d+ hours?)\b",
        ],
    },
    {
        "id": "no_contract",
        "title": "No contract or checks",
        "severity": "medium",
        "reason": "A real tenancy comes with a written agreement, and your deposit must be protected.",
        "patterns": [
            r"\b(?:no|without|skip(?:ping)?|don'?t need|do not need|no need for)\s+(?:a\s+|any\s+|the\s+)?(?:contract|tenancy agreement|agreement|paperwork|references?|credit checks?|checks?|id|identification|deposit protection)\b",
            r"\b(?:contract|agreement|paperwork)\s+(?:later|after (?:you )?(?:arrive|move in|payment|paying))\b",
            r"\b(?:won'?t|will not|refuse[sd]?(?: to)?|can'?t|cannot)\s+(?:show|provide|send|share|give)\s+(?:my\s+|any\s+)?(?:id|identification|passport|proof)\b",
            r"\brefuse[sd]?\s+(?:to\s+)?(?:\w+\s+){0,2}?(?:id|identification)\b",
        ],
    },
]

for _rule in RULES:
    _rule["compiled"] = [re.compile(p, re.IGNORECASE) for p in _rule["patterns"]]


_NORMALISE_MAP = str.maketrans({
    "\u2019": "'", "\u2018": "'", "\u02bc": "'", "\u00b4": "'", "\u0060": "'",
    "\u00a0": " ", "\u2009": " ", "\u202f": " ",
})


def _normalise(text):
    """Same length as the input, so match positions can be used on the original text."""
    return text.translate(_NORMALISE_MAP)


def _make_flag(rule, quote):
    return {
        "id": rule["id"],
        "title": rule["title"],
        "severity": rule["severity"],
        "quote": quote,
        "reason": rule["reason"],
        "source": "rule",
    }


def _find_price_quote(text, price):
    """Find the price as written in the listing, so we can quote it. Returns '' if not found."""
    try:
        number = f"{int(round(float(price))):,}"
    except (TypeError, ValueError):
        return ""
    plain = number.replace(",", "")
    pattern = rf"£\s?(?:{re.escape(number)}|{re.escape(plain)})(?:\.\d{{2}})?(?:\s?(?:pcm|pm|per month|a month|/month|/ month))?"
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return m.group(0).strip() if m else ""


def check_rules(text, price=None, city=None):
    """Return a list of Flag dicts. Never raises."""
    flags = []
    try:
        text = text if isinstance(text, str) else ""
        # Phones and Word turn ' into a curly quote. Match on a same length copy
        # (so positions line up) but quote the listing's own original text.
        norm = _normalise(text)

        for rule in RULES:
            best = None
            for pattern in rule["compiled"]:
                m = pattern.search(norm)
                if m and (best is None or m.start() < best.start()):
                    best = m  # keep the earliest match as the quote
            if best:
                flags.append(_make_flag(rule, text[best.start():best.end()].strip()))

        # price_too_low: price under 60% of the city average
        try:
            price_num = float(price) if price is not None else None
        except (TypeError, ValueError):
            price_num = None
        average = get_average(city)
        if price_num and price_num > 0 and average and price_num < PRICE_TOO_LOW_RATIO * average:
            flags.append({
                "id": "price_too_low",
                "title": "Price far below average",
                "severity": "high",
                "quote": _find_price_quote(text, price_num),
                "reason": (
                    f"£{int(price_num):,} a month is far below the typical £{average:,} for a room in "
                    f"{str(city).strip().title()}. Very cheap prices are often bait to make you reply fast."
                ),
                "source": "rule",
            })
    except Exception:
        pass  # a broken rule must never crash the app
    return flags
