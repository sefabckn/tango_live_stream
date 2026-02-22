-- ============================================================
-- Live-Streaming Platform (Tango-like) — Database Schema
-- Compatible with SQLite (primary) and PostgreSQL
-- ============================================================

-- ----------------------------------------------------------
-- USERS: all platform users (viewers and potential streamers)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY,
    username        TEXT    NOT NULL UNIQUE,
    email           TEXT    NOT NULL UNIQUE,
    country         TEXT    NOT NULL,
    gender          TEXT    CHECK (gender IN ('M', 'F', 'Other')),
    age             INTEGER CHECK (age BETWEEN 13 AND 99),
    registration_date DATE  NOT NULL,
    is_streamer     INTEGER NOT NULL DEFAULT 0,  -- boolean
    coin_balance    INTEGER NOT NULL DEFAULT 0,
    account_status  TEXT    NOT NULL DEFAULT 'active'
                            CHECK (account_status IN ('active', 'suspended', 'deleted')),
    platform        TEXT    CHECK (platform IN ('ios', 'android', 'web')),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_country ON users(country);
CREATE INDEX idx_users_registration_date ON users(registration_date);
CREATE INDEX idx_users_is_streamer ON users(is_streamer);

-- ----------------------------------------------------------
-- STREAMERS: extended profile for users who stream
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS streamers (
    streamer_id     INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL UNIQUE REFERENCES users(user_id),
    display_name    TEXT    NOT NULL,
    category        TEXT    NOT NULL
                            CHECK (category IN ('music', 'talk_show', 'gaming', 'dance',
                                                 'cooking', 'fitness', 'art', 'education', 'other')),
    tier            TEXT    NOT NULL DEFAULT 'bronze'
                            CHECK (tier IN ('bronze', 'silver', 'gold', 'diamond')),
    follower_count  INTEGER NOT NULL DEFAULT 0,
    total_earnings  REAL    NOT NULL DEFAULT 0.0,
    country         TEXT    NOT NULL,
    joined_date     DATE    NOT NULL,
    is_verified     INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_streamers_category ON streamers(category);
CREATE INDEX idx_streamers_tier ON streamers(tier);

-- ----------------------------------------------------------
-- STREAMS: individual live-stream sessions
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS streams (
    stream_id       INTEGER PRIMARY KEY,
    streamer_id     INTEGER NOT NULL REFERENCES streamers(streamer_id),
    title           TEXT    NOT NULL,
    category        TEXT    NOT NULL,
    start_time      TIMESTAMP NOT NULL,
    end_time        TIMESTAMP,
    duration_minutes INTEGER,
    peak_viewers    INTEGER NOT NULL DEFAULT 0,
    avg_viewers     INTEGER NOT NULL DEFAULT 0,
    total_gifts_value INTEGER NOT NULL DEFAULT 0,
    status          TEXT    NOT NULL DEFAULT 'live'
                            CHECK (status IN ('live', 'ended', 'cancelled'))
);

CREATE INDEX idx_streams_streamer_id ON streams(streamer_id);
CREATE INDEX idx_streams_start_time ON streams(start_time);
CREATE INDEX idx_streams_category ON streams(category);

-- ----------------------------------------------------------
-- GIFTS: virtual gift catalog
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS gifts (
    gift_id         INTEGER PRIMARY KEY,
    gift_name       TEXT    NOT NULL UNIQUE,
    coin_cost       INTEGER NOT NULL CHECK (coin_cost > 0),
    category        TEXT    NOT NULL
                            CHECK (category IN ('basic', 'premium', 'luxury', 'event_special')),
    animation_type  TEXT    DEFAULT 'standard'
                            CHECK (animation_type IN ('standard', 'animated', 'full_screen')),
    is_active       INTEGER NOT NULL DEFAULT 1
);

-- ----------------------------------------------------------
-- GIFT_TRANSACTIONS: every gift sent during a stream
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS gift_transactions (
    transaction_id  INTEGER PRIMARY KEY,
    sender_id       INTEGER NOT NULL REFERENCES users(user_id),
    receiver_id     INTEGER NOT NULL REFERENCES streamers(streamer_id),
    stream_id       INTEGER NOT NULL REFERENCES streams(stream_id),
    gift_id         INTEGER NOT NULL REFERENCES gifts(gift_id),
    quantity        INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    total_coins     INTEGER NOT NULL,
    usd_value       REAL    NOT NULL,
    sent_at         TIMESTAMP NOT NULL
);

CREATE INDEX idx_gift_tx_sender ON gift_transactions(sender_id);
CREATE INDEX idx_gift_tx_receiver ON gift_transactions(receiver_id);
CREATE INDEX idx_gift_tx_stream ON gift_transactions(stream_id);
CREATE INDEX idx_gift_tx_sent_at ON gift_transactions(sent_at);

-- ----------------------------------------------------------
-- SUBSCRIPTIONS: monthly subscriptions to streamers
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(user_id),
    streamer_id     INTEGER NOT NULL REFERENCES streamers(streamer_id),
    plan            TEXT    NOT NULL
                            CHECK (plan IN ('basic', 'premium', 'vip')),
    price_usd       REAL    NOT NULL,
    start_date      DATE    NOT NULL,
    end_date        DATE,
    is_active       INTEGER NOT NULL DEFAULT 1,
    auto_renew      INTEGER NOT NULL DEFAULT 1,
    cancelled_at    DATE
);

CREATE INDEX idx_subs_user ON subscriptions(user_id);
CREATE INDEX idx_subs_streamer ON subscriptions(streamer_id);
CREATE INDEX idx_subs_start ON subscriptions(start_date);

-- ----------------------------------------------------------
-- CHAT_MESSAGES: messages sent during live streams
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_messages (
    message_id      INTEGER PRIMARY KEY,
    stream_id       INTEGER NOT NULL REFERENCES streams(stream_id),
    user_id         INTEGER NOT NULL REFERENCES users(user_id),
    message_text    TEXT    NOT NULL,
    is_superchat    INTEGER NOT NULL DEFAULT 0,
    superchat_amount INTEGER DEFAULT 0,
    sent_at         TIMESTAMP NOT NULL
);

CREATE INDEX idx_chat_stream ON chat_messages(stream_id);
CREATE INDEX idx_chat_user ON chat_messages(user_id);
CREATE INDEX idx_chat_sent_at ON chat_messages(sent_at);

-- ----------------------------------------------------------
-- USER_SESSIONS: app engagement tracking
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id      INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(user_id),
    session_start   TIMESTAMP NOT NULL,
    session_end     TIMESTAMP,
    duration_seconds INTEGER,
    platform        TEXT    CHECK (platform IN ('ios', 'android', 'web')),
    pages_viewed    INTEGER DEFAULT 1,
    streams_watched INTEGER DEFAULT 0,
    gifts_sent      INTEGER DEFAULT 0
);

CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_start ON user_sessions(session_start);

-- ----------------------------------------------------------
-- A/B EXPERIMENTS: experiment definitions
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS ab_experiments (
    experiment_id   INTEGER PRIMARY KEY,
    experiment_name TEXT    NOT NULL UNIQUE,
    description     TEXT,
    hypothesis      TEXT,
    primary_metric  TEXT    NOT NULL,
    start_date      DATE    NOT NULL,
    end_date        DATE,
    status          TEXT    NOT NULL DEFAULT 'running'
                            CHECK (status IN ('draft', 'running', 'completed', 'cancelled')),
    traffic_pct     REAL    NOT NULL DEFAULT 100.0
);

-- ----------------------------------------------------------
-- A/B ASSIGNMENTS: user → variant mapping
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS ab_assignments (
    assignment_id   INTEGER PRIMARY KEY,
    experiment_id   INTEGER NOT NULL REFERENCES ab_experiments(experiment_id),
    user_id         INTEGER NOT NULL REFERENCES users(user_id),
    variant         TEXT    NOT NULL CHECK (variant IN ('control', 'treatment')),
    assigned_at     TIMESTAMP NOT NULL,
    UNIQUE(experiment_id, user_id)
);

CREATE INDEX idx_ab_assign_exp ON ab_assignments(experiment_id);
CREATE INDEX idx_ab_assign_user ON ab_assignments(user_id);

-- ----------------------------------------------------------
-- A/B EVENTS: conversion / metric events per experiment
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS ab_events (
    event_id        INTEGER PRIMARY KEY,
    experiment_id   INTEGER NOT NULL REFERENCES ab_experiments(experiment_id),
    user_id         INTEGER NOT NULL REFERENCES users(user_id),
    event_type      TEXT    NOT NULL,
    event_value     REAL,
    event_timestamp TIMESTAMP NOT NULL
);

CREATE INDEX idx_ab_events_exp ON ab_events(experiment_id);
CREATE INDEX idx_ab_events_user ON ab_events(user_id);
