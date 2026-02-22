-- ============================================================
-- Advanced SQL Analytics Queries
-- Live-Streaming Platform (Tango-like)
--
-- Covers: Window Functions, CTEs, Multi-Source Joins,
--         Subqueries, Pivoting, Cohort Analysis
-- ============================================================


-- ============================================================
-- 1. DAILY REVENUE TREND (rolling 7-day average)
-- Skills: Window Functions (AVG OVER), date functions
-- ============================================================
SELECT
    revenue_date,
    daily_revenue_usd,
    ROUND(AVG(daily_revenue_usd) OVER (
        ORDER BY revenue_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_7d_avg
FROM (
    SELECT
        DATE(sent_at) AS revenue_date,
        ROUND(SUM(usd_value), 2) AS daily_revenue_usd
    FROM gift_transactions
    GROUP BY DATE(sent_at)
) daily
ORDER BY revenue_date;


-- ============================================================
-- 2. TOP 20 STREAMERS BY TOTAL REVENUE (gifts + subscriptions)
-- Skills: Multi-source JOIN, COALESCE, aggregation
-- ============================================================
SELECT
    s.streamer_id,
    s.display_name,
    s.category,
    s.tier,
    s.follower_count,
    COALESCE(g.gift_revenue, 0)  AS gift_revenue_usd,
    COALESCE(sub.sub_revenue, 0) AS subscription_revenue_usd,
    ROUND(COALESCE(g.gift_revenue, 0) + COALESCE(sub.sub_revenue, 0), 2) AS total_revenue_usd
FROM streamers s
LEFT JOIN (
    SELECT receiver_id, ROUND(SUM(usd_value), 2) AS gift_revenue
    FROM gift_transactions
    GROUP BY receiver_id
) g ON g.receiver_id = s.streamer_id
LEFT JOIN (
    SELECT streamer_id, ROUND(SUM(price_usd), 2) AS sub_revenue
    FROM subscriptions
    GROUP BY streamer_id
) sub ON sub.streamer_id = s.streamer_id
ORDER BY total_revenue_usd DESC
LIMIT 20;


-- ============================================================
-- 3. STREAMER RANK BY CATEGORY (monthly)
-- Skills: Window Functions (RANK, PARTITION BY), CTEs
-- ============================================================
WITH monthly_revenue AS (
    SELECT
        st.streamer_id,
        s.display_name,
        s.category,
        STRFTIME('%Y-%m', gt.sent_at) AS month,
        ROUND(SUM(gt.usd_value), 2) AS revenue
    FROM gift_transactions gt
    JOIN streams st ON gt.stream_id = st.stream_id
    JOIN streamers s ON st.streamer_id = s.streamer_id
    GROUP BY st.streamer_id, s.display_name, s.category, STRFTIME('%Y-%m', gt.sent_at)
)
SELECT
    month,
    category,
    display_name,
    revenue,
    RANK() OVER (PARTITION BY month, category ORDER BY revenue DESC) AS category_rank
FROM monthly_revenue
WHERE category_rank <= 5
ORDER BY month DESC, category, category_rank;


-- ============================================================
-- 4. USER COHORT RETENTION ANALYSIS
-- Skills: CTEs, self-join, DATE arithmetic, cohort analysis
-- ============================================================
WITH user_cohorts AS (
    SELECT
        user_id,
        STRFTIME('%Y-%m', registration_date) AS cohort_month
    FROM users
),
user_activity AS (
    SELECT
        user_id,
        STRFTIME('%Y-%m', session_start) AS activity_month
    FROM user_sessions
    GROUP BY user_id, STRFTIME('%Y-%m', session_start)
),
retention AS (
    SELECT
        uc.cohort_month,
        -- Calculate months since registration
        CAST(
            (JULIANDAY(ua.activity_month || '-01') - JULIANDAY(uc.cohort_month || '-01')) / 30
        AS INTEGER) AS months_since_reg,
        COUNT(DISTINCT ua.user_id) AS active_users
    FROM user_cohorts uc
    JOIN user_activity ua ON uc.user_id = ua.user_id
    GROUP BY uc.cohort_month, months_since_reg
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM user_cohorts
    GROUP BY cohort_month
)
SELECT
    r.cohort_month,
    cs.cohort_size,
    r.months_since_reg,
    r.active_users,
    ROUND(100.0 * r.active_users / cs.cohort_size, 1) AS retention_pct
FROM retention r
JOIN cohort_sizes cs ON r.cohort_month = cs.cohort_month
WHERE r.months_since_reg BETWEEN 0 AND 12
ORDER BY r.cohort_month, r.months_since_reg;


-- ============================================================
-- 5. WHALE ANALYSIS — Users spending 2× the average
-- Skills: Correlated subquery, HAVING, aggregation
-- ============================================================
SELECT
    u.user_id,
    u.username,
    u.country,
    u.age,
    ROUND(SUM(gt.usd_value), 2) AS total_spent_usd,
    COUNT(gt.transaction_id) AS num_transactions,
    ROUND(SUM(gt.usd_value) / COUNT(gt.transaction_id), 2) AS avg_per_transaction
FROM users u
JOIN gift_transactions gt ON u.user_id = gt.sender_id
GROUP BY u.user_id, u.username, u.country, u.age
HAVING total_spent_usd > (
    SELECT 2 * AVG(user_total)
    FROM (
        SELECT SUM(usd_value) AS user_total
        FROM gift_transactions
        GROUP BY sender_id
    )
)
ORDER BY total_spent_usd DESC
LIMIT 50;


-- ============================================================
-- 6. DAY-OF-WEEK ENGAGEMENT HEATMAP
-- Skills: CASE expressions, pivoting, aggregation
-- ============================================================
SELECT
    CASE CAST(STRFTIME('%w', session_start) AS INTEGER)
        WHEN 0 THEN 'Sunday'
        WHEN 1 THEN 'Monday'
        WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
    END AS day_of_week,
    CAST(STRFTIME('%H', session_start) AS INTEGER) AS hour_of_day,
    COUNT(*) AS session_count,
    ROUND(AVG(duration_seconds) / 60.0, 1) AS avg_duration_minutes,
    SUM(streams_watched) AS total_streams_watched,
    SUM(gifts_sent) AS total_gifts_sent
FROM user_sessions
GROUP BY STRFTIME('%w', session_start), STRFTIME('%H', session_start)
ORDER BY CAST(STRFTIME('%w', session_start) AS INTEGER),
         CAST(STRFTIME('%H', session_start) AS INTEGER);


-- ============================================================
-- 7. GIFT POPULARITY & REVENUE CONTRIBUTION
-- Skills: Window Functions (SUM OVER for running total / %), JOIN
-- ============================================================
SELECT
    g.gift_name,
    g.coin_cost,
    g.category,
    COUNT(gt.transaction_id) AS times_sent,
    SUM(gt.quantity) AS total_quantity,
    ROUND(SUM(gt.usd_value), 2) AS total_revenue_usd,
    ROUND(100.0 * SUM(gt.usd_value) / SUM(SUM(gt.usd_value)) OVER (), 2) AS pct_of_total_revenue,
    ROUND(
        SUM(SUM(gt.usd_value)) OVER (ORDER BY SUM(gt.usd_value) DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
        / SUM(SUM(gt.usd_value)) OVER () * 100, 2
    ) AS cumulative_pct
FROM gifts g
JOIN gift_transactions gt ON g.gift_id = gt.gift_id
GROUP BY g.gift_id, g.gift_name, g.coin_cost, g.category
ORDER BY total_revenue_usd DESC;


-- ============================================================
-- 8. STREAMER PERFORMANCE: AVG VIEWERS, STREAM FREQ, REVENUE/STREAM
-- Skills: Multi-table JOIN, aggregation, ROUND
-- ============================================================
SELECT
    s.streamer_id,
    s.display_name,
    s.category,
    s.tier,
    COUNT(st.stream_id) AS total_streams,
    ROUND(AVG(st.duration_minutes), 0) AS avg_duration_min,
    ROUND(AVG(st.avg_viewers), 0) AS avg_viewers,
    MAX(st.peak_viewers) AS max_peak_viewers,
    ROUND(SUM(gt_agg.stream_revenue), 2) AS total_gift_revenue,
    ROUND(SUM(gt_agg.stream_revenue) / COUNT(st.stream_id), 2) AS revenue_per_stream
FROM streamers s
JOIN streams st ON s.streamer_id = st.streamer_id
LEFT JOIN (
    SELECT stream_id, SUM(usd_value) AS stream_revenue
    FROM gift_transactions
    GROUP BY stream_id
) gt_agg ON st.stream_id = gt_agg.stream_id
GROUP BY s.streamer_id, s.display_name, s.category, s.tier
ORDER BY total_gift_revenue DESC
LIMIT 30;


-- ============================================================
-- 9. MONTHLY ACTIVE USERS (DAU / WAU / MAU)
-- Skills: CTEs, DISTINCT counting, date functions
-- ============================================================
WITH months AS (
    SELECT DISTINCT STRFTIME('%Y-%m', session_start) AS month
    FROM user_sessions
)
SELECT
    m.month,
    (SELECT COUNT(DISTINCT user_id)
     FROM user_sessions
     WHERE STRFTIME('%Y-%m', session_start) = m.month
    ) AS mau,
    (SELECT ROUND(AVG(weekly_active), 0)
     FROM (
         SELECT STRFTIME('%Y-%W', session_start) AS week, COUNT(DISTINCT user_id) AS weekly_active
         FROM user_sessions
         WHERE STRFTIME('%Y-%m', session_start) = m.month
         GROUP BY STRFTIME('%Y-%W', session_start)
     )
    ) AS avg_wau,
    (SELECT ROUND(AVG(daily_active), 0)
     FROM (
         SELECT DATE(session_start) AS day, COUNT(DISTINCT user_id) AS daily_active
         FROM user_sessions
         WHERE STRFTIME('%Y-%m', session_start) = m.month
         GROUP BY DATE(session_start)
     )
    ) AS avg_dau
FROM months m
ORDER BY m.month;


-- ============================================================
-- 10. SUBSCRIPTION CHURN ANALYSIS
-- Skills: CASE, DATE arithmetic, cohort grouping
-- ============================================================
SELECT
    plan,
    COUNT(*) AS total_subscriptions,
    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS still_active,
    SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) AS churned,
    ROUND(100.0 * SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS churn_rate_pct,
    ROUND(AVG(
        CASE WHEN cancelled_at IS NOT NULL
            THEN JULIANDAY(cancelled_at) - JULIANDAY(start_date)
            ELSE NULL
        END
    ), 0) AS avg_days_to_churn,
    ROUND(SUM(price_usd), 2) AS total_revenue_usd
FROM subscriptions
GROUP BY plan
ORDER BY churn_rate_pct DESC;


-- ============================================================
-- 11. FUNNEL ANALYSIS: Registration → Session → Stream Watch → Gift
-- Skills: CTEs, LEFT JOINs, funnel metrics
-- ============================================================
WITH step1_registered AS (
    SELECT COUNT(*) AS cnt FROM users
),
step2_had_session AS (
    SELECT COUNT(DISTINCT user_id) AS cnt FROM user_sessions
),
step3_watched_stream AS (
    SELECT COUNT(DISTINCT user_id) AS cnt
    FROM user_sessions
    WHERE streams_watched > 0
),
step4_sent_gift AS (
    SELECT COUNT(DISTINCT sender_id) AS cnt FROM gift_transactions
),
step5_subscribed AS (
    SELECT COUNT(DISTINCT user_id) AS cnt FROM subscriptions
)
SELECT
    'Registered' AS step,
    (SELECT cnt FROM step1_registered) AS users,
    100.0 AS pct_of_registered,
    100.0 AS pct_of_previous
UNION ALL
SELECT
    'Had Session',
    (SELECT cnt FROM step2_had_session),
    ROUND(100.0 * (SELECT cnt FROM step2_had_session) / (SELECT cnt FROM step1_registered), 1),
    ROUND(100.0 * (SELECT cnt FROM step2_had_session) / (SELECT cnt FROM step1_registered), 1)
UNION ALL
SELECT
    'Watched Stream',
    (SELECT cnt FROM step3_watched_stream),
    ROUND(100.0 * (SELECT cnt FROM step3_watched_stream) / (SELECT cnt FROM step1_registered), 1),
    ROUND(100.0 * (SELECT cnt FROM step3_watched_stream) / (SELECT cnt FROM step2_had_session), 1)
UNION ALL
SELECT
    'Sent Gift',
    (SELECT cnt FROM step4_sent_gift),
    ROUND(100.0 * (SELECT cnt FROM step4_sent_gift) / (SELECT cnt FROM step1_registered), 1),
    ROUND(100.0 * (SELECT cnt FROM step4_sent_gift) / (SELECT cnt FROM step3_watched_stream), 1)
UNION ALL
SELECT
    'Subscribed',
    (SELECT cnt FROM step5_subscribed),
    ROUND(100.0 * (SELECT cnt FROM step5_subscribed) / (SELECT cnt FROM step1_registered), 1),
    ROUND(100.0 * (SELECT cnt FROM step5_subscribed) / (SELECT cnt FROM step4_sent_gift), 1);


-- ============================================================
-- 12. COUNTRY-LEVEL REVENUE & ENGAGEMENT BREAKDOWN
-- Skills: Multi-table JOIN, aggregation, derived metrics
-- ============================================================
SELECT
    u.country,
    COUNT(DISTINCT u.user_id) AS total_users,
    COUNT(DISTINCT CASE WHEN u.is_streamer = 1 THEN u.user_id END) AS num_streamers,
    ROUND(COALESCE(SUM(gt.usd_value), 0), 2) AS gift_revenue_usd,
    COUNT(DISTINCT gt.sender_id) AS gift_senders,
    ROUND(
        COALESCE(SUM(gt.usd_value), 0) /
        NULLIF(COUNT(DISTINCT gt.sender_id), 0), 2
    ) AS arpu_gifters,
    ROUND(AVG(us.duration_seconds) / 60.0, 1) AS avg_session_minutes
FROM users u
LEFT JOIN gift_transactions gt ON u.user_id = gt.sender_id
LEFT JOIN user_sessions us ON u.user_id = us.user_id
GROUP BY u.country
ORDER BY gift_revenue_usd DESC;


-- ============================================================
-- 13. RUNNING TOTAL OF GIFT REVENUE PER STREAMER (cumulative)
-- Skills: Window function (SUM OVER ORDER BY)
-- ============================================================
SELECT
    s.display_name,
    DATE(gt.sent_at) AS txn_date,
    ROUND(SUM(gt.usd_value), 2) AS daily_revenue,
    ROUND(SUM(SUM(gt.usd_value)) OVER (
        PARTITION BY s.streamer_id
        ORDER BY DATE(gt.sent_at)
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2) AS cumulative_revenue
FROM gift_transactions gt
JOIN streamers s ON gt.receiver_id = s.streamer_id
WHERE s.tier = 'diamond'
GROUP BY s.streamer_id, s.display_name, DATE(gt.sent_at)
ORDER BY s.display_name, txn_date;


-- ============================================================
-- 14. A/B TEST RESULTS — Gift Animation Experiment
-- Skills: CTEs, GROUP BY variant, AVG, statistical prep
-- ============================================================
WITH experiment_data AS (
    SELECT
        aa.variant,
        ae.user_id,
        AVG(ae.event_value) AS avg_gifts_per_session,
        COUNT(*) AS num_sessions
    FROM ab_assignments aa
    JOIN ab_events ae ON aa.experiment_id = ae.experiment_id
                     AND aa.user_id = ae.user_id
    WHERE aa.experiment_id = 1
    GROUP BY aa.variant, ae.user_id
)
SELECT
    variant,
    COUNT(*) AS num_users,
    ROUND(AVG(avg_gifts_per_session), 4) AS mean_gifts_per_session,
    ROUND(AVG(avg_gifts_per_session * avg_gifts_per_session)
        - AVG(avg_gifts_per_session) * AVG(avg_gifts_per_session), 4) AS variance,
    ROUND(MIN(avg_gifts_per_session), 2) AS min_val,
    ROUND(MAX(avg_gifts_per_session), 2) AS max_val,
    SUM(num_sessions) AS total_sessions
FROM experiment_data
GROUP BY variant;


-- ============================================================
-- 15. A/B TEST RESULTS — Premium Pricing Experiment
-- Skills: Proportions, CASE, aggregation
-- ============================================================
SELECT
    aa.variant,
    COUNT(*) AS num_users,
    SUM(CAST(ae.event_value AS INTEGER)) AS conversions,
    ROUND(100.0 * SUM(ae.event_value) / COUNT(*), 2) AS conversion_rate_pct,
    ROUND(SUM(ae.event_value) / COUNT(*), 6) AS conversion_proportion
FROM ab_assignments aa
JOIN ab_events ae ON aa.experiment_id = ae.experiment_id
                 AND aa.user_id = ae.user_id
WHERE aa.experiment_id = 2
GROUP BY aa.variant;


-- ============================================================
-- 16. SUPERCHAT REVENUE ANALYSIS
-- Skills: JOIN, CASE, aggregation, ranking
-- ============================================================
SELECT
    s.display_name,
    s.category,
    COUNT(cm.message_id) AS total_superchats,
    SUM(cm.superchat_amount) AS total_superchat_coins,
    ROUND(SUM(cm.superchat_amount) * 1.0 / 100, 2) AS superchat_revenue_usd,
    RANK() OVER (ORDER BY SUM(cm.superchat_amount) DESC) AS revenue_rank
FROM chat_messages cm
JOIN streams st ON cm.stream_id = st.stream_id
JOIN streamers s ON st.streamer_id = s.streamer_id
WHERE cm.is_superchat = 1
GROUP BY s.streamer_id, s.display_name, s.category
ORDER BY revenue_rank
LIMIT 20;
