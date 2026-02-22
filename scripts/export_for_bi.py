"""
Export pre-aggregated CSVs from the platform database for BI tool import.

Generates:
  - daily_revenue.csv
  - streamer_performance.csv
  - user_cohorts.csv
  - engagement_funnel.csv
  - country_metrics.csv
  - subscription_churn.csv

Usage:
    python scripts/export_for_bi.py
"""

import sqlite3
from pathlib import Path
import csv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "platform.db"
EXPORT_DIR = PROJECT_ROOT / "data" / "bi_exports"
EXPORT_DIR.mkdir(exist_ok=True)


def export_query(conn, query: str, filename: str):
    """Run a query and write results to CSV."""
    cur = conn.execute(query)
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()

    path = EXPORT_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    print(f"  ✓ {filename}: {len(rows):,} rows")
    return path


def main():
    print("=" * 60)
    print("  BI Export — CSV Generator")
    print("=" * 60)

    conn = sqlite3.connect(str(DB_PATH))

    # 1. Daily Revenue
    export_query(conn, """
        SELECT
            DATE(sent_at) AS date,
            COUNT(transaction_id) AS num_transactions,
            SUM(quantity) AS total_gifts_sent,
            ROUND(SUM(usd_value), 2) AS revenue_usd,
            COUNT(DISTINCT sender_id) AS unique_senders,
            COUNT(DISTINCT receiver_id) AS unique_receivers
        FROM gift_transactions
        GROUP BY DATE(sent_at)
        ORDER BY date
    """, "daily_revenue.csv")

    # 2. Streamer Performance
    export_query(conn, """
        SELECT
            s.streamer_id,
            s.display_name,
            s.category,
            s.tier,
            s.country,
            s.follower_count,
            s.is_verified,
            COUNT(DISTINCT st.stream_id) AS total_streams,
            COALESCE(ROUND(AVG(st.duration_minutes), 0), 0) AS avg_stream_duration_min,
            COALESCE(ROUND(AVG(st.avg_viewers), 0), 0) AS avg_viewers,
            COALESCE(MAX(st.peak_viewers), 0) AS max_peak_viewers,
            COALESCE(ROUND(SUM(gt.usd_value), 2), 0) AS gift_revenue_usd,
            COALESCE(ROUND(SUM(sub.price_usd), 2), 0) AS subscription_revenue_usd,
            COALESCE(COUNT(DISTINCT sub.subscription_id), 0) AS total_subscribers
        FROM streamers s
        LEFT JOIN streams st ON s.streamer_id = st.streamer_id
        LEFT JOIN gift_transactions gt ON s.streamer_id = gt.receiver_id
        LEFT JOIN subscriptions sub ON s.streamer_id = sub.streamer_id
        GROUP BY s.streamer_id
        ORDER BY gift_revenue_usd DESC
    """, "streamer_performance.csv")

    # 3. User Cohorts (monthly)
    export_query(conn, """
        WITH cohorts AS (
            SELECT
                user_id,
                STRFTIME('%Y-%m', registration_date) AS cohort_month
            FROM users
        ),
        activity AS (
            SELECT user_id, STRFTIME('%Y-%m', session_start) AS activity_month
            FROM user_sessions
            GROUP BY user_id, STRFTIME('%Y-%m', session_start)
        )
        SELECT
            c.cohort_month,
            COUNT(DISTINCT c.user_id) AS cohort_size,
            a.activity_month,
            COUNT(DISTINCT a.user_id) AS active_users,
            CAST(
                (JULIANDAY(a.activity_month || '-01') - JULIANDAY(c.cohort_month || '-01')) / 30
            AS INTEGER) AS months_since_reg
        FROM cohorts c
        JOIN activity a ON c.user_id = a.user_id
        GROUP BY c.cohort_month, a.activity_month
        ORDER BY c.cohort_month, a.activity_month
    """, "user_cohorts.csv")

    # 4. Engagement Funnel
    export_query(conn, """
        SELECT 'Registered' AS step, 1 AS step_order, COUNT(*) AS users FROM users
        UNION ALL
        SELECT 'Had Session', 2, COUNT(DISTINCT user_id) FROM user_sessions
        UNION ALL
        SELECT 'Watched Stream', 3, COUNT(DISTINCT user_id)
        FROM user_sessions WHERE streams_watched > 0
        UNION ALL
        SELECT 'Sent Gift', 4, COUNT(DISTINCT sender_id) FROM gift_transactions
        UNION ALL
        SELECT 'Subscribed', 5, COUNT(DISTINCT user_id) FROM subscriptions
        ORDER BY step_order
    """, "engagement_funnel.csv")

    # 5. Country Metrics
    export_query(conn, """
        SELECT
            u.country,
            COUNT(DISTINCT u.user_id) AS total_users,
            COUNT(DISTINCT CASE WHEN u.is_streamer = 1 THEN u.user_id END) AS streamers,
            COALESCE(ROUND(SUM(gt.usd_value), 2), 0) AS gift_revenue_usd,
            COUNT(DISTINCT gt.sender_id) AS gift_senders,
            COALESCE(ROUND(AVG(us.duration_seconds) / 60.0, 1), 0) AS avg_session_min
        FROM users u
        LEFT JOIN gift_transactions gt ON u.user_id = gt.sender_id
        LEFT JOIN user_sessions us ON u.user_id = us.user_id
        GROUP BY u.country
        ORDER BY gift_revenue_usd DESC
    """, "country_metrics.csv")

    # 6. Subscription Churn
    export_query(conn, """
        SELECT
            plan,
            STRFTIME('%Y-%m', start_date) AS start_month,
            COUNT(*) AS new_subscriptions,
            SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS still_active,
            SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) AS churned,
            ROUND(100.0 * SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS churn_rate_pct,
            ROUND(SUM(price_usd), 2) AS total_revenue_usd
        FROM subscriptions
        GROUP BY plan, STRFTIME('%Y-%m', start_date)
        ORDER BY start_month, plan
    """, "subscription_churn.csv")

    conn.close()
    print(f"\n✅ All exports saved to: {EXPORT_DIR}")


if __name__ == "__main__":
    main()
