# PocketSmart AI — Your Smart Budget & Recommendation Assistant

A GenAI-powered, cross-platform recommendation system that delivers
personalized, budget-based suggestions for **Home Interiors**, **Party
Planning**, and **Jewelry** — sourced from platforms like Amazon,
Flipkart, IKEA, Swiggy, Zomato, and OYO. Built with **FastAPI** on the
backend and **Google Gemini (1.5 Flash)** as the recommendation engine,
with a server-rendered **Jinja2 + HTML/CSS/JS** frontend.

This is the complete, runnable implementation of the project described
in the PocketSmart AI design document (Milestones 1–5): Gemini setup,
core planner logic, FastAPI routes (auth, planners, session, history),
and the full UI.

---

## 1. Features

- **Home Interior Planner** — enter a budget + room list (lights, fans,
  dining tables, sofas, wardrobes) → get furniture/decor suggestions.
- **Party Planner** — enter budget, guest count, event type → get a
  catering/decoration/entertainment/venue budget split.
- **Jewelry Planner** — enter budget, occasion, style, and *optionally
  an outfit photo* → get jewelry picks, color-matched to the outfit
  when an image is provided (multimodal Gemini call).
- **Auth** — register/login/logout with hashed passwords (bcrypt) and
  JWT session cookies; also exposes a standard OAuth2 `/token` route
  for API clients.
- **History** — every recommendation is saved per-user and viewable on
  `/history` and `/dashboard`.
- **Mock mode** — if no `GEMINI_API_KEY` is set, the app automatically
  falls back to deterministic, rule-based recommendations so the whole
  product still works end-to-end for local dev/demo/testing.
- **Real, working links** — each recommended item links to a live
  search-results page on the matching platform (not a fabricated
  product URL).

## 2. Architecture

```
Browser (Jinja2 + HTML/CSS/JS)
        |  fetch() / form POST
        v
FastAPI app (app/main.py)
 |- routes/pages_routes.py     -> renders HTML pages
 |- routes/auth_routes.py      -> register / login / logout / token
 |- routes/planner_routes.py   -> /generate-home /generate-party /generate-jewelry
 |- routes/history_routes.py   -> /history /session-info /session-data
 |- services/gemini_utils.py   -> Gemini prompt orchestration + fallback
 |- services/product_links.py  -> builds real per-platform search URLs
 |- auth.py                    -> JWT + bcrypt
 |- database.py                -> JSON-file persistence (users/history)
 `- models/schemas.py          -> Pydantic request/response models
```

## 3. Project Structure

```
pocketsmart-ai/
|-- app/
|   |-- main.py               # FastAPI app, middleware, routers, startup
|   |-- config.py             # Loads .env into a Settings object
|   |-- database.py           # JSON-file "DB" for users + history
|   |-- auth.py               # Password hashing, JWT, current-user deps
|   |-- deps.py               # Shared Jinja2Templates instance
|   |-- models/
|   |   `-- schemas.py        # Pydantic input/output models
|   |-- routes/
|   |   |-- pages_routes.py
|   |   |-- auth_routes.py
|   |   |-- planner_routes.py
|   |   `-- history_routes.py
|   |-- services/
|   |   |-- gemini_utils.py   # Gemini calls + rule-based fallback
|   |   `-- product_links.py  # Real platform search-URL builder
|   |-- templates/            # Jinja2 HTML templates
|   |-- static/
|   |   |-- css/style.css
|   |   `-- js/main.js
|   `-- data/                 # users.json / history.json (auto-created)
|-- tests/
|   `-- test_app.py           # pytest end-to-end tests (mock mode)
|-- .env.example               # Copy to .env and fill in
|-- .gitignore
|-- requirements.txt
|-- run.py                     # `python run.py` convenience entrypoint
`-- README.md
```

---

## 4. Prerequisites

- **Python 3.10+**
- **VS Code** with the *Python* extension (ms-python.python)
- (Optional but recommended) a **Google Gemini API key** — get one free
  at https://aistudio.google.com/app/apikey. Without a key, the app
  runs in **mock mode** using rule-based fallback recommendations, so
  you can build/test/demo the whole app with zero API cost.

---

## 5. Setup in VS Code (step by step)

### Step 1 — Open the project
Open the `pocketsmart-ai` folder in VS Code: `File -> Open Folder...`

### Step 2 — Create a virtual environment
Open a terminal in VS Code (`Ctrl+backtick`) and run:

**macOS / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell)**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

VS Code will usually prompt "Select Python Interpreter" — pick the one
inside `./venv`. If it doesn't prompt, open the Command Palette
(`Ctrl+Shift+P`) -> **Python: Select Interpreter** -> choose `venv`.

### Step 3 — Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4 — Configure environment variables
```bash
cp .env.example .env      # macOS/Linux
copy .env.example .env    # Windows
```
Open `.env` and:
- Paste your key into `GEMINI_API_KEY=` (or leave blank for mock mode).
- Set `SECRET_KEY` to a real random string:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

### Step 5 — Run the app
Any of these work:
```bash
python run.py
# or
uvicorn app.main:app --reload
# or press F5 in VS Code and pick "PocketSmart AI: Run FastAPI (uvicorn)"
```
Then open **http://127.0.0.1:8000** in your browser.

Interactive API docs (Swagger UI) are at **http://127.0.0.1:8000/docs**.

### Step 6 — Try it out
1. Go to `/register`, create an account.
2. You'll land on `/dashboard`.
3. Open **Home Planner**, **Party Planner**, or **Jewelry Planner**,
   fill the form, and submit — recommendations render inline with
   working links to the actual platform's search results.
4. Check `/history` to see everything you've generated.

---

## 6. Running Tests

The test suite uses FastAPI's `TestClient` and forces mock mode (no
API key needed), so tests are fast, free, and offline-friendly.

```bash
pip install pytest httpx   # if not already installed via requirements.txt
pytest -v
```

Or in VS Code: open the **Testing** sidebar -> it auto-discovers
`tests/test_app.py` via the pytest settings in `.vscode/settings.json`
— or press `F5` and choose **"PocketSmart AI: Run Tests"**.

The suite covers:
- Landing page and health check
- Register -> login -> dashboard session flow
- OAuth2 `/token` issuance
- All three `/generate-*` endpoints (including jewelry with and
  without an outfit image)
- History persistence and `/session-info` / `/session-data`
- Unauthenticated redirect behavior

---

## 7. Switching between Mock Mode and Live Gemini

| | Mock mode | Live Gemini |
|---|---|---|
| `.env` setting | `GEMINI_API_KEY=` (empty) | `GEMINI_API_KEY=<your key>` |
| Recommendation source | Rule-based fallback (`source: "fallback"` in the JSON response) | Real Gemini call (`source: "gemini"`) |
| Cost | Free | Uses your Gemini quota |
| Use case | Local dev, demos, CI/tests | Production-quality recommendations |

You can check which mode is active anytime at **`/health`**.

---

## 8. Troubleshooting

- **`ModuleNotFoundError`** — make sure your venv is activated and you
  ran `pip install -r requirements.txt` inside it.
- **Gemini errors / rate limits** — the app automatically falls back to
  mock-mode recommendations for that request; check server logs for
  the warning, and verify your API key/quota at
  https://aistudio.google.com/app/apikey.
- **Login redirects in a loop** — clear cookies for `127.0.0.1:8000` or
  restart the server (a changed `SECRET_KEY` invalidates old tokens).
- **Port already in use** — change `PORT` in `.env`, or run
  `uvicorn app.main:app --port 8001`.
- **bcrypt install issues on Windows** — upgrade pip
  (`python -m pip install --upgrade pip`) before installing
  requirements; bcrypt ships prebuilt wheels for recent Python versions.

---

## 9. Notes on data storage

For simplicity this build uses JSON files (`app/data/users.json`,
`app/data/history.json`) instead of a full database — genuinely
persisted across restarts, zero setup required. To move to a real
database later, only `app/database.py` needs to change; every route
already calls it through simple functions (`get_user`, `create_user`,
`add_history_entry`, `get_history`, ...), so the rest of the app is
unaffected.
