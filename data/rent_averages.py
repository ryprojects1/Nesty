"""Average monthly room rent by city, in pounds. Owner: A1.

Source: SpareRoom Rental Index, Q3 2026 (page updated October 2026). These averages include bills.
Sheffield is from the July 2026 update, because it was missing from the October table I could see.
Guildford is an ESTIMATE (it is not in SpareRoom's top city list). Replace it if you find a real figure.

The price_too_low rule flags a price under 60% of the city average, so these only need to be roughly right.
"""
import re

RENT_AVERAGES = {
    "london": 1002,          # SpareRoom "London (Inner)"
    "guildford": 750,        # ESTIMATE, not an official figure
    "manchester": 685,
    "bristol": 746,
    "birmingham": 614,
    "leeds": 578,
    "edinburgh": 894,
    "nottingham": 588,
    "sheffield": 533,        # July 2026 figure
    "glasgow": 692,
    # A few more student cities so the demo works beyond the main ten
    "oxford": 834,
    "cambridge": 792,
    "brighton": 762,
    "exeter": 681,
    "cardiff": 650,
    "newcastle": 604,
    "liverpool": 554,
    "coventry": 571,
    "southampton": 662,
    "portsmouth": 664,
}

# Other ways people write a city name
ALIASES = {
    "greater london": "london",
    "inner london": "london",
    "brighton and hove": "brighton",
    "brighton & hove": "brighton",
    "newcastle upon tyne": "newcastle",
    "newcastle-upon-tyne": "newcastle",
}


def _clean(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z&\- ]", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def get_average(city):
    """Return the average monthly room rent for a city, or None if we do not know it."""
    if not city or not isinstance(city, str):
        return None
    name = _clean(city)
    if not name:
        return None
    name = ALIASES.get(name, name)
    if name in RENT_AVERAGES:
        return RENT_AVERAGES[name]
    # Handle things like "central manchester" or "manchester city centre"
    for key in sorted(RENT_AVERAGES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(key)}\b", name):
            return RENT_AVERAGES[key]
    return None
