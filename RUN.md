# ContentDNA — How to Run

## Prerequisites

- Python 3.11+
- Node.js 18+
- Redis (running locally or via Docker)

---

## 1 — One-time Setup

### Python environment

```powershell
# From the project root (d:\contentdna)
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Frontend

```powershell
cd frontend
npm install
cd ..
```

### Environment variables

```powershell
copy .env.example .env
# Then open .env and fill in your keys:
#   SUPABASE_URL, SUPABASE_SERVICE_KEY
#   YOUTUBE_API_KEY
#   INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD
#   REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
#   REDIS_URL (default: redis://localhost:6379/0)
```

### Database

Run the SQL in `schema.sql` against your Supabase project once:

```powershell
# Paste the contents of schema.sql into the Supabase SQL Editor, or:
# psql <your-supabase-connection-string> -f schema.sql
```

---

## 2 — Start Redis

If you don't have Redis installed, run it via Docker:

```powershell
docker run -d -p 6379:6379 redis:alpine
```

---

## 3 — Run (open 4 terminals, each with venv activated)

### Terminal 1 — FastAPI backend

```powershell
.\venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --port 8000
```

API available at: http://localhost:8000  
Swagger docs at: http://localhost:8000/docs

### Terminal 2 — Celery worker

```powershell
.\venv\Scripts\Activate.ps1
celery -A backend.crawlers.worker worker --loglevel=info
```

### Terminal 3 — Celery beat scheduler (runs crawlers every 15 min)

```powershell
.\venv\Scripts\Activate.ps1
celery -A backend.crawlers.worker beat --loglevel=info
```

### Terminal 4 — React frontend

```powershell
cd frontend
npm run dev
```

Frontend available at: http://localhost:5173

---

## 4 — Quick Smoke Test

```powershell
# With venv active, from project root:
python test_backend.py
```

Expected output:
```
[1] phash_encoder import: OK
[2] fusion import: OK
[3] fusion self-score: 1.0 OK
[4] severity mapping: OK
[5] url_classifier: 5/5 cases OK
[6] FAISS: add+search OK
[7] pHash: self-distance=0 OK
=== ALL TESTS PASSED ===
```

---

## 5 — Verify Each Service

| Check | How |
|-------|-----|
| API health | GET http://localhost:8000/health |
| Hunt job runs | POST http://localhost:8000/hunt with `{"url":"https://example.com","owner_id":"<uuid>"}` |
| Platform crawl | Click "Trigger Now" on http://localhost:5173/monitor |
| Alerts page | http://localhost:5173/alerts — should load with filters |
| Account search | http://localhost:5173/accounts — enter a handle and check |

---

## Common Issues

**`celery-beat-schedule` error on startup** — delete the file and restart beat:
```powershell
del celerybeat-schedule
```

**`Redis connection refused`** — make sure Redis is running (step 2).

**`SUPABASE_URL not set`** — check your `.env` file exists and is populated.

**Instagram login fails** — delete `./data/instagram_session.json` and retry.
