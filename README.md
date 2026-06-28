# ContentDNA
> "Your content. Fingerprinted. Found. Protected."

AI-powered digital media rights enforcement system.
Detects stolen sports media across Instagram, YouTube, TikTok, Reddit, and any website.

---

## Two Person Build

| Person | File | Owns |
|---|---|---|
| Person 1 | PERSON1_BACKEND_BUILD.md | Backend + AI pipeline |
| Person 2 | PERSON2_FRONTEND_BUILD.md | Frontend + Crawlers + Extension |

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- Redis (local or Docker)
- ffmpeg (`brew install ffmpeg` or `apt install ffmpeg`)
- Supabase account (free tier)

---

## Setup — Person 1 (Backend)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# Fill in .env with your API keys
# Run schema.sql in your Supabase SQL editor
uvicorn backend.main:app --reload
```

## Setup — Person 2 (Frontend)

```bash
git clone https://github.com/YOUR_USERNAME/contentdna.git
cd contentdna
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cd frontend && npm install && cd ..
npm run dev
```

---

## Run Everything

```bash
# Terminal 1 — API
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Celery Worker
celery -A backend.crawlers.worker worker -c 4

# Terminal 3 — Celery Beat Scheduler
celery -A backend.crawlers.worker beat

# Terminal 4 — Frontend
cd frontend && npm run dev

# Terminal 5 — Task Monitor (optional)
celery -A backend.crawlers.worker flower --port=5555
```

---

## Open Source Dependencies (clone into project/)

```bash
git clone https://github.com/scrapy/scrapy                    project/hunter/scrapy_engine/
git clone https://github.com/microsoft/playwright-python      project/hunter/playwright_engine/
git clone https://github.com/yt-dlp/yt-dlp                   project/hunter/ytdlp_engine/
git clone https://github.com/mikf/gallery-dl                  project/hunter/gallerydl_engine/
git clone https://github.com/streamlink/streamlink            project/hunter/streamlink_engine/
git clone https://github.com/JohannesBuchner/imagehash        project/fingerprint/imagehash/
git clone https://github.com/ShieldMnt/invisible-watermark    project/fingerprint/watermark/
git clone https://github.com/facebookresearch/faiss           project/store/faiss/
git clone https://github.com/subzeroid/instagrapi             project/crawlers/instagram/
git clone https://github.com/praw-dev/praw                    project/crawlers/reddit/
git clone https://github.com/Nv7-GitHub/googlesearch          project/discovery/googlesearch/
git clone https://github.com/shadcn-ui/ui                     project/frontend/components/
git clone https://github.com/shinchxnn/Real-Time-tracking     project/reference/
```

project/ is in .gitignore — these clones stay local only.
