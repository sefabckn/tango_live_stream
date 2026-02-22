"""
Interactive Streamlit Dashboard for Live-Streaming Platform Analytics.

Pages:
  1. Revenue Overview
  2. Streamer Performance
  3. User Engagement
  4. A/B Test Results

Usage:
    streamlit run dashboard/dashboard.py
"""

import sqlite3
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from scipy import stats

# ─── Configuration ───────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "platform.db"

st.set_page_config(
    page_title="StreamPulse Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                padding: 16px; border-radius: 12px; border: 1px solid #233554; }
    .stMetric label { color: #8892b0 !important; font-size: 0.85rem !important; }
    .stMetric [data-testid="stMetricValue"] { color: #64ffda !important;
                                               font-size: 1.8rem !important; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #0a192f 0%, #112240 100%); }
    h1, h2, h3 { color: #ccd6f6 !important; }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_connection():
    """Return a cached SQLite connection."""
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)


@st.cache_data(ttl=600)
def run_query(query: str) -> pd.DataFrame:
    """Execute SQL and return a DataFrame."""
    conn = get_connection()
    return pd.read_sql_query(query, conn)


# ─── Sidebar ─────────────────────────────────────────────────
st.sidebar.title("📊 StreamPulse")
st.sidebar.caption("Live-Streaming Platform Analytics")

page = st.sidebar.radio(
    "Navigate",
    ["🏠 Revenue Overview", "🎤 Streamer Performance",
     "👥 User Engagement", "🧪 A/B Test Results"],
)


# ═══════════════════════════════════════════════════════════════
# PAGE 1: REVENUE OVERVIEW
# ═══════════════════════════════════════════════════════════════
if page == "🏠 Revenue Overview":
    st.title("🏠 Revenue Overview")

    # KPI row
    kpis = run_query("""
        SELECT
            ROUND(SUM(usd_value), 2) AS total_revenue,
            COUNT(DISTINCT sender_id) AS unique_gifters,
            ROUND(SUM(usd_value) / COUNT(DISTINCT sender_id), 2) AS arpu,
            COUNT(*) AS total_transactions
        FROM gift_transactions
    """)
    sub_kpis = run_query("""
        SELECT
            ROUND(SUM(price_usd), 2) AS sub_revenue,
            COUNT(DISTINCT user_id) AS subscribers
        FROM subscriptions
    """)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💰 Gift Revenue", f"${kpis['total_revenue'].iloc[0]:,.0f}")
    c2.metric("💳 Subscription Revenue", f"${sub_kpis['sub_revenue'].iloc[0]:,.0f}")
    c3.metric("🎁 Total Transactions", f"{kpis['total_transactions'].iloc[0]:,}")
    c4.metric("👤 Unique Gifters", f"{kpis['unique_gifters'].iloc[0]:,}")
    c5.metric("📈 ARPU (Gifters)", f"${kpis['arpu'].iloc[0]:,.2f}")

    st.divider()

    # Daily revenue trend with rolling average
    daily = run_query("""
        SELECT
            DATE(sent_at) AS date,
            ROUND(SUM(usd_value), 2) AS revenue
        FROM gift_transactions
        GROUP BY DATE(sent_at)
        ORDER BY date
    """)
    daily["date"] = pd.to_datetime(daily["date"])
    daily["rolling_7d"] = daily["revenue"].rolling(7).mean()

    fig = go.Figure()
    fig.add_trace(go.Bar(x=daily["date"], y=daily["revenue"],
                         name="Daily Revenue", marker_color="#233554", opacity=0.6))
    fig.add_trace(go.Scatter(x=daily["date"], y=daily["rolling_7d"],
                             name="7-Day Rolling Avg", line=dict(color="#64ffda", width=3)))
    fig.update_layout(
        title="Daily Gift Revenue (USD)",
        template="plotly_dark", height=400,
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        legend=dict(orientation="h", y=1.12),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Revenue by gift type
    col1, col2 = st.columns(2)
    with col1:
        gift_rev = run_query("""
            SELECT g.gift_name, g.category, g.coin_cost,
                   ROUND(SUM(gt.usd_value), 2) AS revenue
            FROM gifts g
            JOIN gift_transactions gt ON g.gift_id = gt.gift_id
            GROUP BY g.gift_id
            ORDER BY revenue DESC
        """)
        fig2 = px.treemap(gift_rev, path=["category", "gift_name"],
                          values="revenue", color="revenue",
                          color_continuous_scale="tealgrn",
                          title="Revenue by Gift Type")
        fig2.update_layout(template="plotly_dark", height=400,
                           paper_bgcolor="#0e1117")
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        country_rev = run_query("""
            SELECT u.country, ROUND(SUM(gt.usd_value), 2) AS revenue
            FROM gift_transactions gt
            JOIN users u ON gt.sender_id = u.user_id
            GROUP BY u.country
            ORDER BY revenue DESC
        """)
        fig3 = px.bar(country_rev, x="country", y="revenue",
                      color="revenue", color_continuous_scale="tealgrn",
                      title="Revenue by Country")
        fig3.update_layout(template="plotly_dark", height=400,
                           paper_bgcolor="#0e1117", plot_bgcolor="#0e1117")
        st.plotly_chart(fig3, use_container_width=True)

    # Top gifters (whales)
    st.subheader("🐋 Top 15 Gifters (Whales)")
    whales = run_query("""
        SELECT u.username, u.country, u.age,
               ROUND(SUM(gt.usd_value), 2) AS total_spent,
               COUNT(*) AS num_gifts
        FROM users u
        JOIN gift_transactions gt ON u.user_id = gt.sender_id
        GROUP BY u.user_id
        ORDER BY total_spent DESC
        LIMIT 15
    """)
    st.dataframe(whales, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════
# PAGE 2: STREAMER PERFORMANCE
# ═══════════════════════════════════════════════════════════════
elif page == "🎤 Streamer Performance":
    st.title("🎤 Streamer Performance")

    # Filter by category
    categories = run_query("SELECT DISTINCT category FROM streamers ORDER BY category")
    selected_cat = st.sidebar.multiselect(
        "Filter by Category", categories["category"].tolist(),
        default=categories["category"].tolist()
    )
    cat_filter = "', '".join(selected_cat) if selected_cat else "''"

    perf = run_query(f"""
        SELECT
            s.display_name, s.category, s.tier, s.country,
            s.follower_count, s.is_verified,
            COUNT(DISTINCT st.stream_id) AS streams,
            COALESCE(ROUND(AVG(st.avg_viewers), 0), 0) AS avg_viewers,
            COALESCE(MAX(st.peak_viewers), 0) AS peak_viewers,
            COALESCE(ROUND(SUM(gt_agg.rev), 2), 0) AS gift_revenue
        FROM streamers s
        LEFT JOIN streams st ON s.streamer_id = st.streamer_id
        LEFT JOIN (
            SELECT receiver_id, SUM(usd_value) AS rev FROM gift_transactions GROUP BY receiver_id
        ) gt_agg ON s.streamer_id = gt_agg.receiver_id
        WHERE s.category IN ('{cat_filter}')
        GROUP BY s.streamer_id
        ORDER BY gift_revenue DESC
    """)

    # KPIs
    c1, c2, c3 = st.columns(3)
    c1.metric("🎤 Streamers", f"{len(perf):,}")
    c2.metric("📺 Total Streams", f"{perf['streams'].sum():,}")
    c3.metric("💰 Combined Revenue", f"${perf['gift_revenue'].sum():,.0f}")

    st.divider()

    # Scatter: followers vs revenue
    fig = px.scatter(perf, x="follower_count", y="gift_revenue",
                     size="streams", color="tier",
                     hover_name="display_name",
                     color_discrete_map={"bronze": "#cd7f32", "silver": "#c0c0c0",
                                         "gold": "#ffd700", "diamond": "#b9f2ff"},
                     title="Followers vs Gift Revenue (bubble size = stream count)",
                     log_x=True, log_y=True)
    fig.update_layout(template="plotly_dark", height=500,
                      paper_bgcolor="#0e1117", plot_bgcolor="#0e1117")
    st.plotly_chart(fig, use_container_width=True)

    # Leaderboard
    st.subheader("🏆 Streamer Leaderboard")
    st.dataframe(
        perf[["display_name", "category", "tier", "follower_count",
              "streams", "avg_viewers", "peak_viewers", "gift_revenue"]].head(30),
        use_container_width=True, hide_index=True,
    )

    # Revenue by category
    cat_rev = perf.groupby("category")["gift_revenue"].sum().reset_index()
    fig2 = px.pie(cat_rev, names="category", values="gift_revenue",
                  title="Revenue Share by Category",
                  color_discrete_sequence=px.colors.qualitative.Set2)
    fig2.update_layout(template="plotly_dark", height=400,
                       paper_bgcolor="#0e1117")
    st.plotly_chart(fig2, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# PAGE 3: USER ENGAGEMENT
# ═══════════════════════════════════════════════════════════════
elif page == "👥 User Engagement":
    st.title("👥 User Engagement")

    # MAU / DAU / WAU
    mau_data = run_query("""
        SELECT
            STRFTIME('%Y-%m', session_start) AS month,
            COUNT(DISTINCT user_id) AS mau
        FROM user_sessions
        GROUP BY month ORDER BY month
    """)
    dau_data = run_query("""
        SELECT
            DATE(session_start) AS date,
            COUNT(DISTINCT user_id) AS dau
        FROM user_sessions
        GROUP BY date ORDER BY date
    """)

    c1, c2, c3, c4 = st.columns(4)
    total_users = run_query("SELECT COUNT(*) AS cnt FROM users")["cnt"].iloc[0]
    active = run_query("SELECT COUNT(DISTINCT user_id) AS cnt FROM user_sessions")["cnt"].iloc[0]
    c1.metric("👤 Total Users", f"{total_users:,}")
    c2.metric("✅ Ever Active", f"{active:,}")
    c3.metric("📊 Avg MAU", f"{mau_data['mau'].mean():,.0f}")
    c4.metric("📈 Avg DAU", f"{dau_data['dau'].mean():,.0f}")

    st.divider()

    # MAU trend
    fig = px.line(mau_data, x="month", y="mau",
                  title="Monthly Active Users (MAU)", markers=True)
    fig.update_traces(line=dict(color="#64ffda", width=3))
    fig.update_layout(template="plotly_dark", height=350,
                      paper_bgcolor="#0e1117", plot_bgcolor="#0e1117")
    st.plotly_chart(fig, use_container_width=True)

    # Session duration distribution
    col1, col2 = st.columns(2)
    with col1:
        dur = run_query("""
            SELECT duration_seconds / 60.0 AS duration_min
            FROM user_sessions
            WHERE duration_seconds < 3600
        """)
        fig2 = px.histogram(dur, x="duration_min", nbins=50,
                            title="Session Duration Distribution (minutes)",
                            color_discrete_sequence=["#64ffda"])
        fig2.update_layout(template="plotly_dark", height=350,
                           paper_bgcolor="#0e1117", plot_bgcolor="#0e1117")
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        # Engagement by platform
        plat = run_query("""
            SELECT platform,
                   COUNT(*) AS sessions,
                   ROUND(AVG(duration_seconds)/60.0, 1) AS avg_min,
                   ROUND(AVG(streams_watched), 1) AS avg_streams
            FROM user_sessions
            GROUP BY platform
        """)
        fig3 = px.bar(plat, x="platform", y="sessions",
                      color="avg_min", color_continuous_scale="tealgrn",
                      title="Sessions by Platform")
        fig3.update_layout(template="plotly_dark", height=350,
                           paper_bgcolor="#0e1117", plot_bgcolor="#0e1117")
        st.plotly_chart(fig3, use_container_width=True)

    # Engagement funnel
    st.subheader("🔻 Conversion Funnel")
    funnel = run_query("""
        SELECT 'Registered' AS step, 1 AS ord, COUNT(*) AS users FROM users
        UNION ALL SELECT 'Had Session', 2, COUNT(DISTINCT user_id) FROM user_sessions
        UNION ALL SELECT 'Watched Stream', 3, COUNT(DISTINCT user_id)
            FROM user_sessions WHERE streams_watched > 0
        UNION ALL SELECT 'Sent Gift', 4, COUNT(DISTINCT sender_id) FROM gift_transactions
        UNION ALL SELECT 'Subscribed', 5, COUNT(DISTINCT user_id) FROM subscriptions
        ORDER BY ord
    """)
    fig4 = go.Figure(go.Funnel(
        y=funnel["step"], x=funnel["users"],
        textinfo="value+percent initial",
        marker=dict(color=["#64ffda", "#52d9c0", "#3fb3a6", "#2d8d8c", "#1a6772"]),
    ))
    fig4.update_layout(template="plotly_dark", height=400,
                       paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                       title="User Conversion Funnel")
    st.plotly_chart(fig4, use_container_width=True)

    # Day-of-week heatmap
    st.subheader("🗓️ Engagement Heatmap (Day × Hour)")
    heatmap_data = run_query("""
        SELECT
            CASE CAST(STRFTIME('%w', session_start) AS INTEGER)
                WHEN 0 THEN 'Sun' WHEN 1 THEN 'Mon' WHEN 2 THEN 'Tue'
                WHEN 3 THEN 'Wed' WHEN 4 THEN 'Thu' WHEN 5 THEN 'Fri'
                WHEN 6 THEN 'Sat'
            END AS day,
            CAST(STRFTIME('%w', session_start) AS INTEGER) AS day_num,
            CAST(STRFTIME('%H', session_start) AS INTEGER) AS hour,
            COUNT(*) AS sessions
        FROM user_sessions
        GROUP BY day_num, hour
        ORDER BY day_num, hour
    """)
    pivot = heatmap_data.pivot(index="day", columns="hour", values="sessions").fillna(0)
    day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    pivot = pivot.reindex([d for d in day_order if d in pivot.index])

    fig5 = px.imshow(pivot, color_continuous_scale="tealgrn",
                     title="Sessions by Day of Week and Hour",
                     labels=dict(x="Hour", y="Day", color="Sessions"))
    fig5.update_layout(template="plotly_dark", height=350,
                       paper_bgcolor="#0e1117", plot_bgcolor="#0e1117")
    st.plotly_chart(fig5, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# PAGE 4: A/B TEST RESULTS
# ═══════════════════════════════════════════════════════════════
elif page == "🧪 A/B Test Results":
    st.title("🧪 A/B Test Results")

    experiments = run_query("SELECT * FROM ab_experiments")

    for _, exp in experiments.iterrows():
        st.subheader(f"Experiment: {exp['experiment_name'].replace('_', ' ').title()}")
        st.caption(f"**Hypothesis:** {exp['hypothesis']}")
        st.caption(f"**Period:** {exp['start_date']} → {exp['end_date']} | "
                   f"**Metric:** {exp['primary_metric']}")

        exp_id = exp["experiment_id"]

        if exp["primary_metric"] == "gifts_per_session":
            # Continuous metric — t-test
            data = run_query(f"""
                SELECT aa.variant, ae.user_id,
                       AVG(ae.event_value) AS metric_value
                FROM ab_assignments aa
                JOIN ab_events ae ON aa.experiment_id = ae.experiment_id
                                 AND aa.user_id = ae.user_id
                WHERE aa.experiment_id = {exp_id}
                GROUP BY aa.variant, ae.user_id
            """)

            control = data[data["variant"] == "control"]["metric_value"]
            treatment = data[data["variant"] == "treatment"]["metric_value"]

            t_stat, p_value = stats.ttest_ind(control, treatment)
            cohens_d = (treatment.mean() - control.mean()) / np.sqrt(
                (control.std()**2 + treatment.std()**2) / 2
            )

            ci_control = stats.t.interval(0.95, len(control)-1,
                                          loc=control.mean(), scale=stats.sem(control))
            ci_treatment = stats.t.interval(0.95, len(treatment)-1,
                                            loc=treatment.mean(), scale=stats.sem(treatment))

            # KPIs
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Control Mean", f"{control.mean():.4f}",
                      help=f"95% CI: [{ci_control[0]:.4f}, {ci_control[1]:.4f}]")
            c2.metric("Treatment Mean", f"{treatment.mean():.4f}",
                      delta=f"{((treatment.mean() - control.mean())/control.mean()*100):.1f}%",
                      help=f"95% CI: [{ci_treatment[0]:.4f}, {ci_treatment[1]:.4f}]")
            c3.metric("p-value", f"{p_value:.6f}")
            c4.metric("Effect Size (Cohen's d)", f"{cohens_d:.4f}")

            sig = "✅ Statistically Significant" if p_value < 0.05 else "❌ Not Significant"
            st.info(f"**Result:** {sig} (α = 0.05)")

            # Distribution comparison
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=control, name="Control",
                                       marker_color="#8892b0", opacity=0.7, nbinsx=30))
            fig.add_trace(go.Histogram(x=treatment, name="Treatment",
                                       marker_color="#64ffda", opacity=0.7, nbinsx=30))
            fig.update_layout(
                title="Distribution: Avg Gifts per Session",
                barmode="overlay", template="plotly_dark", height=350,
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                legend=dict(orientation="h", y=1.1),
            )
            st.plotly_chart(fig, use_container_width=True)

            # CI plot
            fig2 = go.Figure()
            for i, (name, mean, ci) in enumerate([
                ("Control", control.mean(), ci_control),
                ("Treatment", treatment.mean(), ci_treatment),
            ]):
                fig2.add_trace(go.Scatter(
                    x=[mean], y=[name],
                    error_x=dict(type="data",
                                 array=[ci[1] - mean],
                                 arrayminus=[mean - ci[0]]),
                    mode="markers", marker=dict(size=14,
                                                color="#64ffda" if i else "#8892b0"),
                    name=name,
                ))
            fig2.update_layout(
                title="95% Confidence Intervals",
                template="plotly_dark", height=250,
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True)

        elif exp["primary_metric"] == "subscription_conversion_rate":
            # Binary metric — chi-squared / z-test for proportions
            data = run_query(f"""
                SELECT aa.variant,
                       COUNT(*) AS n,
                       SUM(CAST(ae.event_value AS INTEGER)) AS conversions
                FROM ab_assignments aa
                JOIN ab_events ae ON aa.experiment_id = ae.experiment_id
                                 AND aa.user_id = ae.user_id
                WHERE aa.experiment_id = {exp_id}
                GROUP BY aa.variant
            """)

            ctrl = data[data["variant"] == "control"].iloc[0]
            treat = data[data["variant"] == "treatment"].iloc[0]

            p_ctrl = ctrl["conversions"] / ctrl["n"]
            p_treat = treat["conversions"] / treat["n"]

            # Z-test for proportions
            p_pool = (ctrl["conversions"] + treat["conversions"]) / (ctrl["n"] + treat["n"])
            se = np.sqrt(p_pool * (1 - p_pool) * (1/ctrl["n"] + 1/treat["n"]))
            z_stat = (p_treat - p_ctrl) / se if se > 0 else 0
            p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

            # CIs for proportions
            def prop_ci(p, n, z=1.96):
                se = np.sqrt(p * (1 - p) / n)
                return (p - z * se, p + z * se)

            ci_ctrl = prop_ci(p_ctrl, ctrl["n"])
            ci_treat = prop_ci(p_treat, treat["n"])

            c1, c2, c3 = st.columns(3)
            c1.metric("Control Rate", f"{p_ctrl*100:.2f}%",
                      help=f"n={int(ctrl['n']):,}, conversions={int(ctrl['conversions']):,}")
            c2.metric("Treatment Rate", f"{p_treat*100:.2f}%",
                      delta=f"{((p_treat - p_ctrl)/p_ctrl*100):.1f}% relative lift",
                      help=f"n={int(treat['n']):,}, conversions={int(treat['conversions']):,}")
            c3.metric("p-value", f"{p_value:.6f}")

            sig = "✅ Statistically Significant" if p_value < 0.05 else "❌ Not Significant"
            st.info(f"**Result:** {sig} (α = 0.05)")

            # Bar chart with CIs
            fig = go.Figure()
            for name, rate, ci, color in [
                ("Control", p_ctrl, ci_ctrl, "#8892b0"),
                ("Treatment", p_treat, ci_treat, "#64ffda"),
            ]:
                fig.add_trace(go.Bar(
                    x=[name], y=[rate * 100],
                    error_y=dict(type="data",
                                 array=[(ci[1] - rate) * 100],
                                 arrayminus=[(rate - ci[0]) * 100]),
                    marker_color=color, name=name,
                ))
            fig.update_layout(
                title="Conversion Rate (%) with 95% Confidence Intervals",
                yaxis_title="Conversion Rate (%)",
                template="plotly_dark", height=400,
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

            # Sample size context table
            st.markdown("**Experiment Details:**")
            st.dataframe(data, use_container_width=True, hide_index=True)

        st.divider()

    # Statistical methodology
    with st.expander("📖 Statistical Methodology"):
        st.markdown("""
        **Continuous metrics** (gifts per session):
        - Two-sample **Welch's t-test** (unequal variances)
        - **95% confidence intervals** using t-distribution
        - **Cohen's d** for effect size

        **Binary metrics** (conversion rate):
        - **Z-test for two proportions** (pooled standard error)
        - **95% CI** using normal approximation
        - **Relative lift** = (treatment - control) / control × 100%

        **Decision criteria:**
        - α = 0.05 (significance level)
        - p < 0.05 → reject H₀ → statistically significant
        """)
