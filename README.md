# 📊 StreamPulse — Live-Streaming Platform Business Analytics

A comprehensive business analytics project simulating a **Tango-like live-streaming platform** with realistic synthetic data, advanced SQL analytics, interactive dashboards, and A/B testing with statistical analysis.

🔗 **[Live Demo](https://tangolivestream-n9ieuldkgjmxywd3feedgv.streamlit.app/)**

## 🎯 Skills Practised

| Skill                        | What's Covered                                                                                       |
| ---------------------------- | ---------------------------------------------------------------------------------------------------- |
| **Advanced SQL**             | Window functions, CTEs, multi-source JOINs, correlated subqueries, cohort retention, funnel analysis |
| **BI Tools**                 | Pre-aggregated CSV exports ready for Power BI / Tableau + built-in Streamlit dashboard               |
| **Large-scale Data**         | ~1M+ rows across 11 tables with realistic patterns (whales, churn, seasonality)                      |
| **Statistics & A/B Testing** | t-tests, z-tests, chi-squared, confidence intervals, effect sizes, power analysis                    |

## 🏗️ Project Structure

```
├── README.md
├── requirements.txt
├── sql/
│   ├── schema.sql               # 11-table DDL with indexes
│   └── analytics_queries.sql    # 16 advanced analytical queries
├── scripts/
│   ├── data_generator.py        # Synthetic data generation (~1M rows)
│   ├── seed_database.py         # Load data into SQLite
│   └── export_for_bi.py         # CSV exports for BI tools
├── dashboard/
│   └── dashboard.py             # Streamlit interactive dashboard (4 pages)
├── analysis/
│   ├── ab_testing.py            # A/B test statistical analysis
│   └── statistical_report.py    # Markdown report generator
└── data/                        # Generated data (auto-created)
    ├── platform.db              # SQLite database
    ├── *.json                   # Raw generated data
    ├── bi_exports/              # CSVs for Power BI / Tableau
    └── ab_results/              # A/B test plots and report
```

## 🚀 Quick Start

### Option A: Docker (Recommended)

```bash
docker compose up --build
```

This generates the data, seeds the database, and launches the dashboard at **http://localhost:8501** — all in one command.

### Option B: Manual Setup

#### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate Data & Seed Database

```bash
python scripts/data_generator.py
python scripts/seed_database.py
```

### 3. Explore SQL Queries

Open `sql/analytics_queries.sql` in any SQL editor connected to `data/platform.db`, or run queries directly:

```bash
sqlite3 data/platform.db < sql/analytics_queries.sql
```

### 4. Export CSVs for Power BI / Tableau

```bash
python scripts/export_for_bi.py
```

Exports are saved to `data/bi_exports/`. Import them into your BI tool of choice.

### 5. Launch Interactive Dashboard

```bash
streamlit run dashboard/dashboard.py
```

### 6. Run A/B Test Analysis

```bash
python analysis/ab_testing.py
python analysis/statistical_report.py
```

## 📐 Data Model

```
users (10K) ──┬── streamers (500) ── streams (20K) ── chat_messages (300K)
              │                          │
              │                    gift_transactions (200K)
              │
              ├── subscriptions (15K)
              ├── user_sessions (500K)
              └── ab_assignments ── ab_events
```

### Key Data Patterns

- **Whale behaviour**: ~2% of users generate ~50% of gift revenue (power-law)
- **Churn curves**: 30% of subscriptions churn within 1 month, 50% within 3 months
- **Peak hours**: Streaming and engagement peak between 18:00–21:00
- **Seasonality**: Registration and activity growth over the 2-year window

## 🧪 A/B Experiments

| Experiment              | Hypothesis                                             | Metric            | Test                   |
| ----------------------- | ------------------------------------------------------ | ----------------- | ---------------------- |
| Gift Animation Redesign | New animations increase gift send rate by 10%          | gifts_per_session | Welch's t-test         |
| Premium Tier Pricing    | Lowering price from $14.99→$9.99 increases conversions | conversion_rate   | Z-test for proportions |

Statistical methods: t-tests, z-tests, chi-squared, Wilson CIs, Cohen's d/h, power analysis.

## 📊 SQL Query Highlights

| #     | Query                                | Techniques               |
| ----- | ------------------------------------ | ------------------------ |
| 1     | Daily revenue with rolling 7-day avg | Window functions         |
| 2     | Top streamers by combined revenue    | Multi-source JOIN        |
| 3     | Monthly streamer rank by category    | RANK + PARTITION BY      |
| 4     | Cohort retention analysis            | CTEs + date arithmetic   |
| 5     | Whale identification (2× avg spend)  | Correlated subquery      |
| 6     | Day × hour engagement heatmap        | CASE pivoting            |
| 7     | Gift revenue Pareto (cumulative %)   | Running window sums      |
| 8     | Streamer performance dashboard       | Multi-table aggregation  |
| 9     | DAU / WAU / MAU trends               | DISTINCT counting        |
| 10    | Subscription churn analysis          | CASE + date diff         |
| 11    | Registration → gift funnel           | CTEs + UNIONs            |
| 12    | Country-level revenue breakdown      | LEFT JOINs + ARPU        |
| 13    | Cumulative revenue per streamer      | Partitioned running sum  |
| 14–15 | A/B test result extraction           | Experiment JOIN patterns |
| 16    | Superchat revenue ranking            | RANK window function     |
