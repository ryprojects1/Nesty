# Nesty

**A rental scam checker for students.** Paste a listing (and any landlord messages), add the rent and city, and Nesty gives you a risk score from 0 to 100, a green / amber / red verdict, every warning sign quoted from the listing with a plain-English reason, and next steps.

Built in one day at a hackathon (24 October 2026) by a team of four.

> **Challenges entered:** Best Open-Source AI Project · Best Use of Gemma 4

---

## Why we built it

Students looking for housing get caught by fake listings on sites like Facebook Marketplace, SpareRoom and Gumtree. The typical scam: the "landlord" is abroad, asks for a deposit before any viewing, pushes urgency, moves the chat to WhatsApp, and the rent is suspiciously cheap.

Figures from Action Fraud (UK national fraud reporting centre):

- About **£9m** lost to rental fraud in 2024, across about 5,000 reports (average about £1,800 per victim).
- People aged **11 to 29** lost **£4.27m** across 2,483 reports in 2023 (average £1,720).

Students are often renting for the first time, far from home, under deadline pressure and on a tight budget, which is what scammers rely on.

---

## What it does

1. You paste the listing text and optionally enter the monthly rent and the city.
2. Two checks run:
   - **Rule engine:** deterministic keyword and pattern checks, plus a price check against city averages.
   - **Gemma 4 analysis:** an open-weight AI model looks for subtler signs such as pressure tactics, inconsistent stories and templated text.
3. The results are merged, de-duplicated and scored, then shown with the exact quote behind each warning.

**If the AI is unavailable, the rules still return a result.** The app shows an "AI check unavailable" notice instead of crashing.

---

## The AI: Gemma 4

| | |
|---|---|
| **Model** | `gemma-4-26b-a4b-it` (Gemma 4, Mixture of Experts, about 4B active parameters) |
| **Accessed through** | The Gemini API (OpenAI-compatible endpoint), called from `engine/llm.py` |
| **Licence** | Apache License 2.0, see [Google's Gemma 4 licence page](https://ai.google.dev/gemma/apache_2) |
| **Open weights** | Yes, so it can be self-hosted (for example by a university) instead of using a hosted API |

**How the AI part works**

- `engine/llm.py` sends the listing to Gemma 4 with a prompt that asks for red flags as JSON (id, title, severity, exact quote, reason) plus advice.
- Gemma's flags are merged with the rule engine's flags in `engine/analyse.py`, duplicates are removed, and the result is scored from 0 to 100.
- If Gemma fails or the internet is down, the app uses the rules only (tested with Wi-Fi off).
- A provider switch, `PROVIDER_ORDER` in `.env` (`gemini`, `ollama`), lets the same code run Gemma locally with Ollama on a machine with enough memory.

**Key dependencies**

| Package | Used for |
|---|---|
| `streamlit` | The website |
| `openai` | Only as a **client library** for the Gemini API's OpenAI-compatible endpoint. **No OpenAI model is used**; the model is Gemma 4 |
| `python-dotenv` | Loading the `.env` file |

---

## How the rules and scoring work

Rule checks are case-insensitive and return the exact text that triggered them.

| Flag id | Severity | Detects (examples) |
|---|---|---|
| `pay_before_viewing` | High | "deposit to secure", "pay to reserve", "before viewing", "holding fee" |
| `landlord_abroad` | High | "I'm abroad / overseas / working away", "agent will post the keys" |
| `odd_payment` | High | "Western Union", "MoneyGram", "crypto", "gift card", "friends and family" |
| `price_too_low` | High | Rent below 60% of the city average (`data/rent_averages.py`) |
| `off_platform` | Medium | "WhatsApp me", "email me directly", "don't use the site" |
| `urgency` | Medium | "many people interested", "today only", "first to pay" |
| `no_contract` | Medium | "no need for a contract", "no paperwork", refuses ID |

**Scoring (in `engine/analyse.py`)**

- Each flag adds a weight: high = 35, medium = 20, low = 10. The total is capped at 100.
- If the rules and the AI report the same flag id, one copy is kept (the rule version).
- If `pay_before_viewing` and `landlord_abroad` are both present, the score is at least 80.
- Levels: **0 to 29** green (no obvious red flags), **30 to 59** amber (medium risk), **60 to 100** red (high risk).

The score represents detected warning signs, **not a verified probability of fraud**. A low score does not guarantee that a listing is genuine.

`data/rent_averages.py` holds approximate average monthly student room rents (in £) for about ten UK university cities (London, Guildford, Manchester, Bristol, Birmingham, Leeds, Edinburgh, Nottingham, Sheffield, Glasgow).

---

## Run it

You need Python 3.11 or later and a free Gemini API key from [aistudio.google.com](https://aistudio.google.com).

**1. Create a `.env` file** in the project folder (it is in `.gitignore` and never committed):

```
PROVIDER_ORDER=gemini
GEMINI_MODEL=gemma-4-26b-a4b-it
GEMINI_API_KEY=your_key_here
```

**2. Then run three commands:**

```bash
git clone https://github.com/ryprojects1/Nesty.git && cd Nesty
pip install -r requirements.txt
streamlit run app.py
```

Open the address shown in the terminal, normally <http://localhost:8501>.

On Windows, if `streamlit` isn't found, use `py -m pip install -r requirements.txt` and `python -m streamlit run app.py`.

The AI part needs an internet connection and takes about 45 seconds per check. The rule checks work offline and are instant.

### Demo mode (no AI, no key)

Demo mode loads fixed sample results from `mock_result.json`. It does **not** analyse the text you submit.

```bash
# macOS / Linux
REDFLAT_USE_MOCK=1 streamlit run app.py
```

```cmd
:: Windows Command Prompt
set REDFLAT_USE_MOCK=1
python -m streamlit run app.py
```

To return to live mode, stop Streamlit with Ctrl+C and run it again without the variable (on Windows, `set REDFLAT_USE_MOCK=`). The interface also falls back to `mock_result.json`, labelled as demo data, if the engine can't be imported.

---

## The website

The frontend is built with Python and Streamlit.

**Features**

- Nesty branding with navy and yellow styling.
- Two-column layout, with inputs on the left and results on the right.
- Text area for listings and landlord messages, an optional monthly rent input and a city selector.
- Three example buttons: **Obvious scam**, **Subtle scam** and **Legit listing**.
- Loading indicator during analysis, and results kept across page reruns using Streamlit session state.

**Results display**

- Risk score from 0 to 100, with a coloured badge and a visual gauge.
- Warning cards showing severity, title, supporting quote and explanation, each labelled as coming from the rules or the AI.
- Warning quotes highlighted inside the submitted listing.
- Recommended next steps, and an "AI check unavailable" notice when only rule checks ran.

**Validation and error handling**

- Empty submissions show a friendly warning, and analysis failures show a retry message.
- Missing example files use built-in sample listings.
- User-provided text is HTML-escaped before being displayed in styled results.

The frontend calls the shared engine:

```python
from engine.analyse import analyse

result = analyse(text, price, city)
# result: score, level, flags, advice, ai_available
```

---

## Project structure

```
Nesty/
├── app.py                 # Streamlit website: layout, inputs, results
├── mock_result.json       # Fixed sample result for demo mode
├── engine/
│   ├── rules.py           # Rule engine: check_rules(text, price, city)
│   ├── llm.py             # Gemma 4 check: check_llm(text)
│   └── analyse.py         # Merges, de-duplicates and scores both checks
├── data/
│   └── rent_averages.py   # Average student room rent by city
├── test_listings/         # Test listings and EXPECTED.md
├── requirements.txt
└── LICENSE
```

---

## Testing

`test_listings/` holds five listings, with the expected result for each in `EXPECTED.md`:

| File | Expected |
|---|---|
| `obvious_scam.txt` | Red |
| `subtle_scam.txt` | Amber or red |
| `legit.txt` | Green |
| `edge_legit_holding_deposit.txt` | Green (a genuine landlord taking a holding deposit after a viewing; tests false alarms) |
| `edge_short_cheap.txt` | Amber (very short text; only the price rule should fire) |

`EXPECTED.md` also lists extra checks: empty input, no price or city, an unknown city, the AI switched off, and very long text.

---

## Honest limits

- **Nesty can be wrong.** It can raise false alarms and miss real scams. Always view the property in person, or by a live video call, and get a written contract before paying anything.
- **A Gemma check takes about 45 seconds.** Gemma 4 always reasons step by step before answering, and the API rejects turning that off.
- **The AI part needs internet.** The rules still work offline.
- **Our test set is five listings written by us.** It shows the app behaves as designed on those cases, not how accurate it is on real listings.
- **The subtle-scam result depends on the AI**, so it can vary between runs.
- **Wording affects the score.** Some trigger words raise the risk score more than others.
- **Text only.** There are no photo uploads, postcode searches or automatic extraction from property links. `check_llm()` already accepts images (Gemma 4 is multimodal), but we didn't wire screenshot support into the website in time. That is the next step.
- **Data handling:** the frontend keeps the current submission and results in session state and doesn't save them to disk or a database. Submitted text is sent to the model provider, and retention depends on the provider's terms.

---

## What we learned

**AI side (A2)**

- It was our first time running an open model. We tried Gemma 4 locally with Ollama on an 8 GB M1 Mac. The E4B model needed 8.8 GiB and E2B needed 6.9 GiB of free memory, so neither fit. We switched to the hosted Gemini API but kept Ollama support in the code.
- The 31B dense model timed out, so we switched to 26B-A4B (Mixture of Experts), which is faster.
- Bug: Gemma copied the placeholder template from our prompt instead of filling it in. We fixed it by describing the format in words rather than showing a fill-in-the-blanks example.
- Bug: a greedy regex broke JSON parsing when Gemma added extra text around its answer. We fixed it with Python's JSON decoder.
- Bug: `analyse.py` gave up on Gemma after 20 seconds while Gemma needed about 45 seconds, so the AI result was dropped and subtle scams were scored on the rules only. We raised the timeout to fix it.

**Testing and pitch (B2)**

- I learned how to test a web application, and how the different parts come together to make an application that solves a real-world problem.

---

## Team and contributions

Built by a team of four. The contributors are listed on the [GitHub contributors page](https://github.com/ryprojects1/Nesty/graphs/contributors) and in the hackathon submission.

| Role | Contribution |
|---|---|
| A1: Rules and scoring | Rule engine, rent averages, scoring in `analyse.py` |
| A2: AI | Gemma 4 integration (`llm.py`), provider switch, merging in `analyse.py` |
| B1: Frontend | Streamlit interface, styling, input validation, example buttons, risk gauge, quote highlighting, source-labelled warning cards, backend integration |
| B2: Testing and pitch | Test listings and expected results, pitch slides, demo, submission |

---

## AI tools we used

The AI inside the app is **Gemma 4** (see above). We also used AI tools while building it:

- **Claude (Anthropic), used by B2:** to draft the test listings and expected results, build the slide deck, look up the Gemma 4 licence and the challenge rules, and draft the submission text and these README notes. B2 reviewed and edited the output.
- Any other AI tools used by teammates while coding are declared in our hackathon submission.

---

## Licence

The project code is released under the [MIT License](LICENSE).

Gemma 4 is released by Google under the [Apache License 2.0](https://ai.google.dev/gemma/apache_2). Check the terms of each model and dependency you use.
