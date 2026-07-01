CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE assets (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id     UUID NOT NULL,
    filename     TEXT,
    media_type   TEXT CHECK (media_type IN ('image','video')),
    storage_url  TEXT,
    phash        TEXT NOT NULL,
    watermark_id UUID,
    faiss_id     INTEGER UNIQUE,
    title        TEXT,
    created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE alerts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id            UUID REFERENCES assets(id) ON DELETE CASCADE,
    owner_id            UUID NOT NULL,
    source_type         TEXT CHECK (source_type IN ('hunter','crawler','manual','dorking')),
    platform            TEXT CHECK (platform IN ('instagram','youtube','tiktok','reddit','web','live')),
    source_url          TEXT,
    page_url            TEXT,
    match_score         FLOAT NOT NULL,
    severity            TEXT CHECK (severity IN ('CRITICAL','HIGH','MEDIUM')),
    thumbnail_url       TEXT,
    watermark_confirmed BOOLEAN DEFAULT false,
    crawled_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE hunt_jobs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id      UUID NOT NULL,
    seed_url      TEXT NOT NULL,
    status        TEXT DEFAULT 'pending',
    pages_crawled INTEGER DEFAULT 0,
    media_found   INTEGER DEFAULT 0,
    matches_found INTEGER DEFAULT 0,
    started_at    TIMESTAMPTZ,
    completed_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_alerts_owner    ON alerts(owner_id);
CREATE INDEX idx_alerts_platform ON alerts(platform);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_assets_owner    ON assets(owner_id);

CREATE TABLE watched_accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id        UUID NOT NULL,
    platform        TEXT CHECK (platform IN ('instagram','youtube','tiktok','reddit')),
    handle          TEXT NOT NULL,           -- username/channel handle, no @ or URL
    label           TEXT,                    -- optional display name
    source          TEXT CHECK (source IN ('manual','auto_discovered')) DEFAULT 'manual',
    last_checked_at TIMESTAMPTZ,
    last_match_count INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (owner_id, platform, handle)
);

CREATE INDEX idx_watched_accounts_owner    ON watched_accounts(owner_id);
CREATE INDEX idx_watched_accounts_platform ON watched_accounts(platform);

