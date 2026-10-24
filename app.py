"""Red Flat: the Streamlit front end. Owner: B1.

Paste a listing, get a verdict in 10 seconds.
Calls analyse(text, price, city) from the shared contract. Never crashes: if the engine
is missing or fails, it shows a friendly message (or the demo data in mock_result.json).

Run:  streamlit run app.py
Demo data only:  REDFLAT_USE_MOCK=1 streamlit run app.py
"""
import html
import json
import os
import re
from pathlib import Path

import streamlit as st

HERE = Path(__file__).parent
AI_NAME = "Gemma 4"                      # shown in the UI so judges can see the AI at work
USE_MOCK = os.getenv("REDFLAT_USE_MOCK", "0") == "1"
NOT_SURE = "Not sure"

st.set_page_config(page_title="Red Flat", page_icon="🚩", layout="wide")

# ---------------------------------------------------------------------------
# Engine and data (both optional, so the page always loads)
# ---------------------------------------------------------------------------
try:
    from engine.analyse import analyse
    ENGINE_OK = True
except Exception:
    analyse = None
    ENGINE_OK = False

try:
    from data.rent_averages import RENT_AVERAGES
    CITIES = sorted(c.title() for c in RENT_AVERAGES)
except Exception:
    CITIES = ["Birmingham", "Bristol", "Edinburgh", "Glasgow", "Guildford", "Leeds",
              "London", "Manchester", "Nottingham", "Sheffield"]

# Each example sets the text, price and city together, so the price check can fire.
EXAMPLES = [
    ("Obvious scam", "obvious_scam.txt", 250, "Guildford"),
    ("Subtle scam", "subtle_scam.txt", None, NOT_SURE),
    ("Legit listing", "legit.txt", 680, "Guildford"),
]
EXAMPLE_FALLBACK = {
    "obvious_scam.txt": "Lovely double room near campus, only £250 a month, bills included! I am currently abroad so my agent will post the keys. Please send £400 deposit to secure the room before viewing. Many people interested so reply today. WhatsApp me. Pay by bitcoin.",
    "subtle_scam.txt": "Thanks for your interest. I'm out of the country most of the year, but a friend can hand over the keys. Please transfer a holding fee of £200 now to take it off the market, as several students are interested. Message me directly and don't use the site. No need for a contract.",
    "legit.txt": "Double room in a four person student house, 10 minutes' walk from campus. £680 per month including bills. Viewings available this weekend through our office. Deposit protected in the DPS. Tenancy agreement provided before you pay. Pay by bank transfer to the agency account.",
}

LEVELS = {
    "red": ("High risk", "#B3261E",
            "This listing matches several patterns often seen in rental scams. Do not pay anything yet."),
    "amber": ("Medium risk", "#9A5B00",
              "There are some warning signs. Check the details before you send any money."),
    "green": ("No obvious red flags", "#1B7F4B",
              "We found no obvious red flags. Still view the home and read the tenancy agreement before you pay."),
}
SEVERITY_LABEL = {"high": "High", "medium": "Medium", "low": "Low"}

PREVIEW_TEXT = ("Nice room near campus! I am currently abroad, so please send £400 to secure "
                "the room before viewing. Many people interested.")
PREVIEW_FLAGS = [
    {"quote": "I am currently abroad", "severity": "high"},
    {"quote": "send £400 to secure the room before viewing", "severity": "high"},
    {"quote": "Many people interested", "severity": "medium"},
]

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------
CSS = """
<style>
.block-container {padding-top: 2.2rem; max-width: 1180px;}
header[data-testid="stHeader"] {background: transparent;}
.rf-title {font-family: "Avenir Next", "Segoe UI", system-ui, sans-serif; font-weight: 800;
  font-size: 2.5rem; letter-spacing: -0.02em; line-height: 1.1; margin: 0; color: #14202E;}
.rf-title mark {background: #FFE45C; color: #14202E; padding: 0 0.18em; border-radius: 3px;}
.rf-tagline {font-size: 1.15rem; color: #3A4A5C; margin: 0.35rem 0 1.6rem 0;}
.rf-help {font-size: 0.9rem; color: #4A5B6D; margin: 0.15rem 0 0.9rem 0;}
.rf-small {font-size: 0.85rem; color: #4A5B6D; line-height: 1.5;}

.rf-badge {display: flex; justify-content: space-between; align-items: center; gap: 1.2rem;
  background: var(--lv); color: #fff; border-radius: 10px; padding: 1.2rem 1.4rem;}
.rf-badge-label {font-family: "Avenir Next", "Segoe UI", system-ui, sans-serif; font-weight: 800;
  font-size: 1.9rem; line-height: 1.1;}
.rf-badge-text {margin-top: 0.4rem; font-size: 1rem; line-height: 1.45; max-width: 34rem;}
.rf-badge-score {text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap;}
.rf-badge-score span {font-size: 3.4rem; font-weight: 800; line-height: 1; display: block;}
.rf-badge-score small {font-size: 0.85rem; opacity: 0.92;}

.rf-gauge {position: relative; height: 10px; border-radius: 5px; margin: 1.1rem 0 0.2rem 0;
  background: linear-gradient(to right, #8FD0AB 0 30%, #F0C46A 30% 60%, #E88C84 60% 100%);}
.rf-gauge i {position: absolute; top: -5px; width: 4px; height: 20px; background: #14202E;
  border-radius: 2px; transform: translateX(-2px);}
.rf-gauge-scale {display: flex; justify-content: space-between; font-size: 0.75rem; color: #4A5B6D;
  font-variant-numeric: tabular-nums;}

.rf-note {font-size: 0.88rem; color: #3A4A5C; margin: 0.8rem 0 0 0;}
.rf-note b {color: #14202E;}

.rf-h {font-family: "Avenir Next", "Segoe UI", system-ui, sans-serif; font-weight: 700;
  font-size: 1.15rem; color: #14202E; margin: 1.7rem 0 0.6rem 0;}

.rf-listing {background: #fff; border: 1px solid #D5DBE3; border-radius: 8px; padding: 1rem 1.2rem;
  font-family: Georgia, "Times New Roman", serif; font-size: 1.02rem; line-height: 1.7; color: #1B2733;}
.rf-listing mark {color: #14202E; padding: 0.05em 0.15em; border-radius: 3px;}
.rf-listing mark.m-high {background: #FFD43B; box-shadow: inset 0 -3px 0 #B3261E;}
.rf-listing mark.m-medium {background: #FFE88A; box-shadow: inset 0 -3px 0 #9A5B00;}
.rf-listing mark.m-low {background: #FFF3BF;}
.rf-listing.rf-muted {opacity: 0.9;}

.rf-flag {background: #fff; border: 1px solid #D5DBE3; border-left: 6px solid var(--sev);
  border-radius: 6px; padding: 0.8rem 1rem; margin: 0 0 0.7rem 0;}
.rf-flag-head {display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.3rem;}
.rf-chip {font-size: 0.8rem; font-weight: 700; color: #fff; background: var(--sev);
  padding: 0.1rem 0.55rem; border-radius: 99px;}
.rf-src {font-size: 0.8rem; color: #4A5B6D; border: 1px solid #C3CCD6; padding: 0.05rem 0.5rem;
  border-radius: 99px;}
.rf-flag-title {font-weight: 700; font-size: 1.05rem; color: #14202E;}
.rf-quote {font-family: Georgia, "Times New Roman", serif; font-style: italic; color: #1B2733;
  background: #FFF3BF; display: inline-block; padding: 0.1rem 0.4rem; border-radius: 3px;
  margin: 0.35rem 0 0.2rem 0;}
.rf-reason {color: #2B3A4A; line-height: 1.5; margin-top: 0.2rem;}
.sev-high {--sev: #B3261E;} .sev-medium {--sev: #9A5B00;} .sev-low {--sev: #5B6B7C;}

.rf-advice {margin: 0; padding-left: 1.2rem; color: #1B2733; line-height: 1.6;}
.rf-advice li {margin-bottom: 0.35rem;}
.rf-disclaimer {margin-top: 1.6rem; font-size: 0.85rem; color: #4A5B6D; line-height: 1.5;
  border-top: 1px solid #D5DBE3; padding-top: 0.8rem;}
.rf-empty {color: #2B3A4A; line-height: 1.55; margin: 0.9rem 0 0 0;}
</style>
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def esc(value):
    """Escape text for HTML. Also stops a $ from being read as maths by Streamlit."""
    return html.escape(str(value), quote=True).replace("$", "&#36;")


def read_example(filename):
    try:
        text = (HERE / "test_listings" / filename).read_text(encoding="utf-8").strip()
        if text:
            return text
    except Exception:
        pass
    return EXAMPLE_FALLBACK.get(filename, "")


def load_mock():
    try:
        return json.loads((HERE / "mock_result.json").read_text(encoding="utf-8"))
    except Exception:
        return {"score": 0, "level": "green", "flags": [], "advice": [], "ai_available": False}


def normalise_result(raw):
    """Fill in anything missing so the page can never hit a KeyError."""
    if not isinstance(raw, dict):
        return None
    flags = []
    for f in raw.get("flags") or []:
        if isinstance(f, dict):
            sev = str(f.get("severity", "medium")).lower()
            flags.append({
                "title": str(f.get("title") or "Warning sign"),
                "severity": sev if sev in SEVERITY_LABEL else "medium",
                "quote": str(f.get("quote") or ""),
                "reason": str(f.get("reason") or ""),
                "source": str(f.get("source") or "rule"),
            })
    try:
        score = max(0, min(100, int(raw.get("score", 0))))
    except (TypeError, ValueError):
        score = 0
    level = raw.get("level") if raw.get("level") in LEVELS else (
        "red" if score >= 60 else "amber" if score >= 30 else "green")
    advice = [str(a) for a in (raw.get("advice") or []) if isinstance(a, str)]
    return {"score": score, "level": level, "flags": flags, "advice": advice,
            "ai_available": bool(raw.get("ai_available"))}


def highlight_html(text, flags):
    """The listing with each quote marked like a highlighter pen. Text is escaped first."""
    spans = []
    for f in flags:
        quote = (f.get("quote") or "").strip()
        if not quote:
            continue
        m = re.search(re.escape(quote), text, flags=re.IGNORECASE)
        if m:
            spans.append((m.start(), m.end(), f.get("severity", "medium")))
    spans.sort()
    merged = []
    for start, end, sev in spans:
        if merged and start < merged[-1][1]:
            p_start, p_end, p_sev = merged[-1]
            merged[-1] = (p_start, max(p_end, end), "high" if "high" in (p_sev, sev) else p_sev)
        else:
            merged.append((start, end, sev))
    out, pos = [], 0
    for start, end, sev in merged:
        out.append(esc(text[pos:start]))
        out.append(f'<mark class="m-{sev}">{esc(text[start:end])}</mark>')
        pos = end
    out.append(esc(text[pos:]))
    return "".join(out).replace("\r", "").replace("\n", "<br>")


def run_check(text, price, city):
    """Returns (result or None, is_demo). Never raises."""
    if USE_MOCK or not ENGINE_OK:
        return normalise_result(load_mock()), True
    try:
        return normalise_result(analyse(text, price, city)), False
    except Exception:
        return None, False


# ---------------------------------------------------------------------------
# State and callbacks (buttons only set state; the check runs in the main flow
# so the spinner can be shown)
# ---------------------------------------------------------------------------
st.session_state.setdefault("listing", "")
st.session_state.setdefault("price", None)
st.session_state.setdefault("city", NOT_SURE)
st.session_state.setdefault("pending", False)
st.session_state.setdefault("result", None)
st.session_state.setdefault("checked_text", "")
st.session_state.setdefault("is_demo", False)
st.session_state.setdefault("message", "")


def start_check():
    st.session_state.pending = True


def load_example(index):
    _label, filename, price, city = EXAMPLES[index]
    st.session_state.listing = read_example(filename)
    st.session_state.price = price
    st.session_state.city = city
    st.session_state.pending = True


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
st.markdown(CSS, unsafe_allow_html=True)
st.markdown('<h1 class="rf-title"><mark>Red</mark> Flat</h1>', unsafe_allow_html=True)
st.markdown('<p class="rf-tagline">Paste a listing, get a verdict in 10 seconds.</p>',
            unsafe_allow_html=True)

left, right = st.columns([5, 6], gap="large")

with left:
    st.text_area("Paste the listing", key="listing", height=270,
                 placeholder="Paste the text of the listing here.")
    st.markdown('<p class="rf-help">Add the landlord’s messages too if you have them. '
                'Price and city are optional, but they let us check if the rent is far too low.</p>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.number_input("Monthly rent in £ (optional)", key="price", value=None,
                        min_value=0, step=10, format="%d", placeholder="e.g. 450")
    with c2:
        st.selectbox("City (optional)", [NOT_SURE] + CITIES, key="city")
    st.button("Check listing", type="primary", use_container_width=True, on_click=start_check)

    st.markdown('<p class="rf-small" style="margin-top:1.3rem;margin-bottom:0.4rem;">'
                'No listing handy? Try an example.</p>', unsafe_allow_html=True)
    cols = st.columns(len(EXAMPLES))
    for i, (label, _f, _p, _c) in enumerate(EXAMPLES):
        with cols[i]:
            st.button(label, key=f"example_{i}", use_container_width=True,
                      on_click=load_example, args=(i,))
    st.markdown('<p class="rf-small" style="margin-top:1rem;">Red Flat does not save what you paste.</p>',
                unsafe_allow_html=True)

with right:
    if st.session_state.pending:
        st.session_state.pending = False
        text = (st.session_state.listing or "").strip()
        if not text:
            st.session_state.result = None
            st.session_state.message = "Paste the text of a listing first, then press Check listing."
        else:
            price = st.session_state.price
            price = int(price) if price else None
            city = st.session_state.city
            city = None if city in (None, NOT_SURE) else city
            with st.spinner(f"{AI_NAME} is checking the listing..."):
                result, demo = run_check(text, price, city)
            st.session_state.checked_text = text
            st.session_state.is_demo = demo
            if result is None:
                st.session_state.result = None
                st.session_state.message = "Something went wrong while checking. Please try again."
            else:
                st.session_state.result = result
                st.session_state.message = ""

    result = st.session_state.result
    if result is None:
        if st.session_state.message:
            st.warning(st.session_state.message)
        st.markdown(
            '<div class="rf-listing rf-muted">' + highlight_html(PREVIEW_TEXT, PREVIEW_FLAGS) + '</div>'
            '<p class="rf-empty">Your result will appear here. Red Flat marks the warning signs in the '
            'listing like a highlighter pen, explains each one in plain words, and tells you what to do next.</p>',
            unsafe_allow_html=True)
    else:
        label, colour, sentence = LEVELS[result["level"]]
        score = result["score"]
        st.markdown(
            f'<div class="rf-badge" style="--lv:{colour}">'
            f'<div><div class="rf-badge-label">{esc(label)}</div>'
            f'<div class="rf-badge-text">{esc(sentence)}</div></div>'
            f'<div class="rf-badge-score"><span>{score}</span><small>out of 100</small></div></div>'
            f'<div class="rf-gauge"><i style="left:{score}%"></i></div>'
            '<div class="rf-gauge-scale"><span>0</span><span>30</span><span>60</span><span>100</span></div>',
            unsafe_allow_html=True)

        if result["ai_available"]:
            note = f'<b>Checked by rules and {esc(AI_NAME)}.</b>'
        else:
            note = '<b>AI check unavailable.</b> Showing the rule checks only.'
        if st.session_state.is_demo:
            note += ' This is demo data.'
        st.markdown(f'<p class="rf-note">{note}</p>', unsafe_allow_html=True)

        checked = st.session_state.checked_text
        if checked and any(f["quote"] for f in result["flags"]):
            st.markdown('<div class="rf-h">Your listing, with the warning signs marked</div>'
                        '<div class="rf-listing">' + highlight_html(checked, result["flags"]) + '</div>',
                        unsafe_allow_html=True)

        st.markdown('<div class="rf-h">What we found</div>', unsafe_allow_html=True)
        if not result["flags"]:
            st.markdown('<p class="rf-reason">No warning signs found in the text you pasted.</p>',
                        unsafe_allow_html=True)
        for f in result["flags"]:
            source = AI_NAME if f["source"] == "ai" else "Rule"
            quote = f'<div class="rf-quote">“{esc(f["quote"])}”</div>' if f["quote"] else ""
            st.markdown(
                f'<div class="rf-flag sev-{f["severity"]}"><div class="rf-flag-head">'
                f'<span class="rf-chip">{SEVERITY_LABEL[f["severity"]]}</span>'
                f'<span class="rf-src">{esc(source)}</span></div>'
                f'<div class="rf-flag-title">{esc(f["title"])}</div>{quote}'
                f'<div class="rf-reason">{esc(f["reason"])}</div></div>',
                unsafe_allow_html=True)

        if result["advice"]:
            items = "".join(f"<li>{esc(a)}</li>" for a in result["advice"])
            st.markdown(f'<div class="rf-h">What to do next</div><ul class="rf-advice">{items}</ul>',
                        unsafe_allow_html=True)

    st.markdown('<div class="rf-disclaimer">Red Flat shows signs often seen in rental scams. '
                'It can be wrong, and it is not proof about any person. '
                'Never pay before you have viewed the home and read the tenancy agreement.</div>',
                unsafe_allow_html=True)
