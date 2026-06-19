# FootyOracle ⚽🔥

A production-grade Telegram bot that ingests a daily FootyStats CSV export, scores matches using a weighted statistical model, selects the best betting opportunities, and posts them automatically to a Telegram channel. Tracks pick history and ROI over time.

No scraping — pure CSV ingestion.

## Stack

- **Backend:** Python 3.12, FastAPI
- **Data:** Pandas (CSV import/validation)
- **Database:** PostgreSQL (Railway-managed) via SQLAlchemy
- **Scheduling:** APScheduler (daily cron job)
- **Bot:** python-telegram-bot (async, command polling)
- **Hosting:** Railway (Docker)

## How it works

```
data/latest.csv
      │
      ▼
 CSVImporter (load → clean → validate → save)
      │
      ▼
 Scorer (weighted composite score, 0-100)
      │
      ▼
 MatchFilter (reject low quality / bad odds / unknown leagues)
      │
      ▼
 PickGenerator (SAFE / VALUE / HIGH_RISK, max 5/day)
      │
      ▼
 Publisher (generate → store → send → mark_posted)
      │
      ▼
   Telegram channel
```

This whole pipeline runs automatically every day at `POST_HOUR` (default 08:00, `TIMEZONE` default `Africa/Lagos`), with 3 retry attempts on failure. It can also be triggered manually via `POST /import` + the scheduler's publish logic, or by calling the relevant service directly.

## Folder structure

```
footyoracle/
├── app/
│   ├── api/        # FastAPI routes (/health, /import, /today, /stats)
│   ├── bot/        # Telegram bot + command handlers
│   ├── core/       # Config + logging
│   ├── data/       # CSV import + parsing
│   ├── engine/     # Scoring, filtering, pick generation
│   ├── jobs/       # APScheduler daily job
│   ├── models/     # SQLAlchemy models (Match, Prediction)
│   ├── services/   # Publisher (orchestration) + ROI tracker
│   ├── storage/    # DB engine/session setup
│   └── main.py     # Entrypoint — wires FastAPI + bot + scheduler together
├── data/
│   └── latest.csv  # Daily CSV drop location
├── tests/
├── requirements.txt
├── Dockerfile
├── railway.json
├── schema.sql
└── .env.example
```

## Scoring model

Weighted composite, normalized to 0–100:

| Factor              | Weight |
|----------------------|--------|
| Over 2.5 Goals prob.  | 30%    |
| BTTS probability      | 25%    |
| Total xG              | 20%    |
| Odds (inverted)       | 15%    |
| League reliability    | 10%    |

**Categories:**
- 🟢 **SAFE** — score ≥ 80
- 🟡 **VALUE** — score 75–79
- 🔴 **HIGH RISK** — score 70–74

**Filters (reject before scoring):**
- Score < `MIN_SCORE` (default 75)
- Odds > 2.3
- Missing xG data
- Unrecognized league
- Duplicate match (same league/teams/date)

Max 5 picks published per day, sorted by confidence.

## CSV format

`data/latest.csv` must contain these columns:

```
date,league,home,away,xg_home,xg_away,btts,over25,odds
```

- `date` — ISO datetime, future or today
- `league` — one of the known league codes (EPL, LA_LIGA, SERIE_A, LIGUE_1, BUNDESLIGA, EREDIVISIE, SUPER_LEAGUE, etc.)
- `btts` / `over25` — probabilities as decimals (0–1) or percentages
- `odds` — decimal odds, must be ≤ 2.3 to be considered

A sample file is included at `data/latest.csv`.

## Telegram commands

| Command     | Description                  |
|-------------|-------------------------------|
| `/start`    | Welcome + command list         |
| `/today`    | Full daily sheet               |
| `/safe`     | SAFE picks only                |
| `/value`    | VALUE picks only                |
| `/results`  | Recent settled results          |
| `/stats`    | Last 30 days performance        |
| `/roi`      | ROI summary (alias of /stats)   |
| `/month`    | Current month's stats           |
| `/history`  | Last 10 picks                   |
| `/help`     | Show command list               |

## API endpoints

| Method | Path      | Description                          |
|--------|-----------|----------------------------------------|
| GET    | `/health` | Health check (used by Railway)         |
| POST   | `/import` | Manually trigger a CSV import          |
| GET    | `/today`  | Get today's generated picks            |
| GET    | `/stats`  | ROI/performance stats (default 30d)    |

## Environment variables

See `.env.example`. Required:

```
BOT_TOKEN=          # Telegram bot token from @BotFather
CHAT_ID=             # Telegram chat/channel ID to post to
DATABASE_URL=        # postgresql://... (Railway provides this automatically)

POST_HOUR=8
MIN_SCORE=75
MAX_DAILY_PICKS=5
TIMEZONE=Africa/Lagos
```

## Local development

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in BOT_TOKEN, CHAT_ID, DATABASE_URL (can use a local sqlite:///./dev.db for testing)

python -m app.main
```

Run tests:

```bash
pytest tests/ -v
```

## Deploying to Railway

1. Push this repo to GitHub.
2. In Railway:
   ```bash
   railway login
   railway link        # or `railway init` for a new project
   ```
3. Add a **PostgreSQL** plugin to the project — Railway will inject `DATABASE_URL` automatically.
4. Set the remaining environment variables in the Railway dashboard (`BOT_TOKEN`, `CHAT_ID`, `POST_HOUR`, `MIN_SCORE`, `MAX_DAILY_PICKS`, `TIMEZONE`).
5. Deploy:
   ```bash
   railway up
   ```
6. Railway builds via the included `Dockerfile` and runs `python -m app.main` (per `railway.json`), exposing port 8000 with `/health` as the healthcheck path.

Each day at `POST_HOUR` (in `TIMEZONE`), the scheduler imports `data/latest.csv`, scores matches, generates picks, and posts the daily sheet to `CHAT_ID`. You'll need to update `data/latest.csv` daily (e.g. via a CI job, manual commit, or by wiring `POST /import` to a different CSV source) — this build intentionally uses static CSV ingestion only, no scraping.

## Database schema

See `schema.sql` for the raw SQL (also auto-created via SQLAlchemy on first boot).

**matches** — id, date, league, home, away, xg_home, xg_away, btts, over25, odds, score, status, created_at

**predictions** — id, match_id, pick, confidence, category, result, profit, posted, posted_at, created_at

## Notes

- Duplicate matches (same league/home/away/date) are skipped on import.
- The importer only accepts matches dated today or in the future.
- Telegram send failures are retried up to 3 times before the pipeline gives up for that run (picks remain stored even if the send fails).
