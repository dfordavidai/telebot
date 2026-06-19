-- FootyOracle database schema (PostgreSQL)
-- Note: app.storage.database.Database.init_db() creates these automatically
-- via SQLAlchemy on startup. This file is provided for reference, manual
-- inspection, or setting up the schema outside the app.

CREATE TABLE IF NOT EXISTS matches (
    id          SERIAL PRIMARY KEY,
    date        TIMESTAMP NOT NULL,
    league      VARCHAR NOT NULL,
    home        VARCHAR NOT NULL,
    away        VARCHAR NOT NULL,
    xg_home     FLOAT,
    xg_away     FLOAT,
    btts        FLOAT,          -- probability 0-1
    over25      FLOAT,          -- probability 0-1
    odds        FLOAT,
    score       INTEGER,        -- composite betting score 0-100
    status      VARCHAR DEFAULT 'pending',  -- pending, completed, cancelled
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_matches_date ON matches (date);
CREATE INDEX IF NOT EXISTS idx_matches_league ON matches (league);

CREATE TABLE IF NOT EXISTS predictions (
    id          SERIAL PRIMARY KEY,
    match_id    INTEGER NOT NULL REFERENCES matches(id),
    pick        VARCHAR NOT NULL,        -- Over2.5, BTTS
    confidence  INTEGER NOT NULL,        -- 0-100
    category    VARCHAR NOT NULL,        -- SAFE, VALUE, HIGH_RISK
    result      VARCHAR,                 -- WON, LOST, VOID, PENDING
    profit      FLOAT,                   -- stake units won/lost
    posted      BOOLEAN DEFAULT FALSE,
    posted_at   TIMESTAMP,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_predictions_match_id ON predictions (match_id);
CREATE INDEX IF NOT EXISTS idx_predictions_posted ON predictions (posted);
