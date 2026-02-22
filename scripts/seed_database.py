"""
Seed the SQLite database from generated JSON data files.

Usage:
    python scripts/seed_database.py
"""

import json
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "platform.db"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"


def load_json(name: str) -> list[dict]:
    path = DATA_DIR / f"{name}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed():
    """Create database, apply schema, and insert all data."""
    # Remove existing DB
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing database: {DB_PATH}")

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    cur = conn.cursor()

    # Apply schema
    print("Applying schema...")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        cur.executescript(f.read())
    print("  ✓ Schema applied")

    # Table configs: (json_filename, table_name, column_order)
    tables = [
        ("users", "users", [
            "user_id", "username", "email", "country", "gender", "age",
            "registration_date", "is_streamer", "coin_balance",
            "account_status", "platform",
        ]),
        ("streamers", "streamers", [
            "streamer_id", "user_id", "display_name", "category", "tier",
            "follower_count", "total_earnings", "country", "joined_date", "is_verified",
        ]),
        ("gifts", "gifts", [
            "gift_id", "gift_name", "coin_cost", "category", "animation_type", "is_active",
        ]),
        ("streams", "streams", [
            "stream_id", "streamer_id", "title", "category", "start_time",
            "end_time", "duration_minutes", "peak_viewers", "avg_viewers",
            "total_gifts_value", "status",
        ]),
        ("gift_transactions", "gift_transactions", [
            "transaction_id", "sender_id", "receiver_id", "stream_id",
            "gift_id", "quantity", "total_coins", "usd_value", "sent_at",
        ]),
        ("subscriptions", "subscriptions", [
            "subscription_id", "user_id", "streamer_id", "plan",
            "price_usd", "start_date", "end_date", "is_active",
            "auto_renew", "cancelled_at",
        ]),
        ("chat_messages", "chat_messages", [
            "message_id", "stream_id", "user_id", "message_text",
            "is_superchat", "superchat_amount", "sent_at",
        ]),
        ("user_sessions", "user_sessions", [
            "session_id", "user_id", "session_start", "session_end",
            "duration_seconds", "platform", "pages_viewed",
            "streams_watched", "gifts_sent",
        ]),
        ("ab_experiments", "ab_experiments", [
            "experiment_id", "experiment_name", "description", "hypothesis",
            "primary_metric", "start_date", "end_date", "status", "traffic_pct",
        ]),
        ("ab_assignments", "ab_assignments", [
            "assignment_id", "experiment_id", "user_id", "variant", "assigned_at",
        ]),
        ("ab_events", "ab_events", [
            "event_id", "experiment_id", "user_id", "event_type",
            "event_value", "event_timestamp",
        ]),
    ]

    for json_name, table_name, columns in tables:
        data = load_json(json_name)
        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)
        sql = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"

        rows = [tuple(row.get(c) for c in columns) for row in data]

        # Batch insert
        BATCH_SIZE = 5000
        for i in range(0, len(rows), BATCH_SIZE):
            cur.executemany(sql, rows[i:i + BATCH_SIZE])

        conn.commit()
        print(f"  ✓ {table_name}: {len(rows):,} rows inserted")

    # Verify counts
    print("\n--- Verification ---")
    for _, table_name, _ in tables:
        count = cur.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  {table_name}: {count:,}")

    conn.close()
    print(f"\n✅ Database seeded: {DB_PATH}")
    print(f"   Size: {DB_PATH.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    seed()
