# Nesty
mlh

## The AI on the website

The website (`index.html` on GitHub Pages) runs the rule checks in the browser. To add Gemma 4, it sends the listing text to `api.py`, a small FastAPI server on DigitalOcean. The server holds `GEMINI_API_KEY`, calls Gemma 4 through Google's Gemini API, and sends back only the flags and advice. It never stores or logs the text. Visitors can untick "Also ask Gemma 4" to keep everything in their browser.

Run it locally:

```bash
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

Then open `http://localhost:8000/docs` to try it.

Settings (environment variables):

| Name | What it does | Default |
|---|---|---|
| `GEMINI_API_KEY` | Key for the Gemini API (required) | none |
| `ALLOWED_ORIGINS` | Sites allowed to call the API from a browser, comma separated | `https://ryprojects1.github.io` |
| `RATE_PER_MINUTE` | Checks one visitor can run per minute | `6` |
| `DAILY_LIMIT` | Checks everyone together can run per day | `500` |

The page calls the URL in `AI_URL` near the top of the AI section of the script in `index.html`. Change it if the server moves.
