"""Nesty AI API: lets the static site (GitHub Pages) use Gemma 4.

The browser can't hold the Gemini API key safely, so the page sends the listing
text here, this server calls Gemma 4 with the key it keeps in its environment,
and only the flags and advice go back.

Run locally:  uvicorn api:app --reload --port 8000
Deploy:       uvicorn api:app --host 0.0.0.0 --port 8080

Settings (environment variables, all optional except GEMINI_API_KEY):
  GEMINI_API_KEY    key for Google's Gemini API, which serves Gemma 4
  ALLOWED_ORIGINS   comma separated sites allowed to call this from a browser
  RATE_PER_MINUTE   checks one visitor can run per minute (default 6)
  DAILY_LIMIT       checks everyone together can run per day (default 500)
"""
import os
import threading
import time
from collections import defaultdict, deque
from datetime import date

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from engine.llm import check_llm

MAX_CHARS = 5000
ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS", "https://ryprojects1.github.io").split(",") if o.strip()]
RATE_PER_MINUTE = int(os.getenv("RATE_PER_MINUTE", "6"))
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "500"))

app = FastAPI(title="Nesty AI API", docs_url="/docs", redoc_url=None)

# CORS: the browser only lets a page read our reply if its site is on this list.
# It is a browser rule, not real security (curl ignores it), so the limits below matter too.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ---------------------------------------------------------------------------
# Limits, so nobody can script requests and burn through the Gemini quota.
# Kept in memory: fine for one small server, resets when it restarts.
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_recent = defaultdict(deque)          # visitor ip -> times of their recent checks
_day = {"date": date.today(), "count": 0}


def _visitor_ip(request: Request) -> str:
    # Behind DigitalOcean's proxy, request.client is the proxy, not the visitor.
    for header in ("do-connecting-ip", "x-forwarded-for"):
        value = request.headers.get(header)
        if value:
            return value.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_limits(ip: str) -> None:
    now = time.monotonic()
    with _lock:
        if _day["date"] != date.today():
            _day["date"], _day["count"] = date.today(), 0
        if _day["count"] >= DAILY_LIMIT:
            raise HTTPException(status_code=503, detail="Daily AI limit reached")

        times = _recent[ip]
        while times and now - times[0] > 60:
            times.popleft()
        if len(times) >= RATE_PER_MINUTE:
            raise HTTPException(status_code=429, detail="Too many checks, wait a minute")

        times.append(now)
        _day["count"] += 1


# ---------------------------------------------------------------------------
# Routes. Registered with and without /api, because DigitalOcean can strip the
# route prefix before the request arrives, depending on how the route is set up.
# ---------------------------------------------------------------------------
class Listing(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_CHARS)


router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True, "ai_configured": bool(os.getenv("GEMINI_API_KEY"))}


@router.post("/ai-check")
def ai_check(body: Listing, request: Request):
    # A plain def, not async: check_llm blocks for several seconds, so FastAPI
    # runs it in a worker thread and the server keeps answering other people.
    _check_limits(_visitor_ip(request))
    out = check_llm(body.text)
    if out.get("error"):
        raise HTTPException(status_code=503, detail="AI unavailable")
    # Only send back what the page needs. The listing text is never stored or logged.
    return {"flags": out.get("flags", []), "advice": out.get("advice", [])}


app.include_router(router, prefix="/api")
app.include_router(router)
