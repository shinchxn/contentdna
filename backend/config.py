# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
import os
load_dotenv()

SUPABASE_URL          = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY  = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_ANON_KEY     = os.getenv("SUPABASE_ANON_KEY")
FAISS_INDEX_PATH      = os.getenv("FAISS_INDEX_PATH", "./data/faiss_index.bin")
MATCH_THRESHOLD       = float(os.getenv("MATCH_THRESHOLD", "0.85"))
REDIS_URL             = os.getenv("REDIS_URL", "redis://localhost:6379/0")
HUNTER_MAX_DEPTH      = int(os.getenv("HUNTER_MAX_DEPTH", "3"))
HUNTER_MAX_PAGES      = int(os.getenv("HUNTER_MAX_PAGES", "100"))
YOUTUBE_API_KEY       = os.getenv("YOUTUBE_API_KEY")
BING_SEARCH_API_KEY   = os.getenv("BING_SEARCH_API_KEY")

# ── Crawler credentials (Person 2 additions) ──────────────────────────────────
REDDIT_CLIENT_ID      = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET  = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT     = os.getenv("REDDIT_USER_AGENT", "contentdna/1.0")

INSTAGRAM_USERNAME    = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD    = os.getenv("INSTAGRAM_PASSWORD")

# ── Google Custom Search Engine ───────────────────────────────────────────────
GOOGLE_CSE_API_KEY    = os.getenv("GOOGLE_CSE_API_KEY")
GOOGLE_CSE_ID         = os.getenv("GOOGLE_CSE_ID")

