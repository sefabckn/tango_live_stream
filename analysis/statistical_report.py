"""
Generate a formatted Markdown report summarising A/B test results.

Usage:
    python analysis/statistical_report.py
"""

import sqlite3
import math
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "platform.db"
REPORT_PATH = PROJECT_ROOT / "data" / "ab_results" / "statistical_report.md"
REPORT_PATH.parent.mkdir(exist_ok=True)


def get_conn():
    return sqlite3.connect(str(DB_PATH))


def generate_report():
    conn = get_conn()

    lines = []
    lines.append("# A/B Testing — Statistical Report")
    lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Platform:** Live-Streaming Analytics (Tango-like)")
    lines.append("")

    # ─── Experiment 1 ─────────────────────────────────────────
    lines.append("---")
    lines.append("## Experiment 1: Gift Animation Redesign")
    lines.append("")

    exp1 = pd.read_sql_query("""
        SELECT * FROM ab_experiments WHERE experiment_id = 1
    """, conn).iloc[0]

    lines.append(f"**Hypothesis:** {exp1['hypothesis']}")
    lines.append(f"**Period:** {exp1['start_date']} → {exp1['end_date']}")
    lines.append(f"**Primary Metric:** {exp1['primary_metric']}")
    lines.append(f"**Traffic:** {exp1['traffic_pct']}%")
    lines.append("")

    data1 = pd.read_sql_query("""
        SELECT aa.variant, ae.user_id,
               AVG(ae.event_value) AS avg_metric
        FROM ab_assignments aa
        JOIN ab_events ae ON aa.experiment_id = ae.experiment_id
                         AND aa.user_id = ae.user_id
        WHERE aa.experiment_id = 1
        GROUP BY aa.variant, ae.user_id
    """, conn)

    ctrl1 = data1[data1["variant"] == "control"]["avg_metric"]
    treat1 = data1[data1["variant"] == "treatment"]["avg_metric"]

    t_stat, p_val = stats.ttest_ind(ctrl1, treat1, equal_var=False)
    ci_c = stats.t.interval(0.95, len(ctrl1)-1, loc=ctrl1.mean(), scale=stats.sem(ctrl1))
    ci_t = stats.t.interval(0.95, len(treat1)-1, loc=treat1.mean(), scale=stats.sem(treat1))

    pooled_std = math.sqrt(((len(ctrl1)-1)*ctrl1.var() + (len(treat1)-1)*treat1.var())
                           / (len(ctrl1)+len(treat1)-2))
    d = (treat1.mean() - ctrl1.mean()) / pooled_std if pooled_std > 0 else 0
    lift = (treat1.mean() - ctrl1.mean()) / ctrl1.mean() * 100

    lines.append("### Results")
    lines.append("")
    lines.append("| Metric | Control | Treatment |")
    lines.append("|--------|---------|-----------|")
    lines.append(f"| Sample Size | {len(ctrl1):,} | {len(treat1):,} |")
    lines.append(f"| Mean | {ctrl1.mean():.4f} | {treat1.mean():.4f} |")
    lines.append(f"| Std Dev | {ctrl1.std():.4f} | {treat1.std():.4f} |")
    lines.append(f"| 95% CI | [{ci_c[0]:.4f}, {ci_c[1]:.4f}] | [{ci_t[0]:.4f}, {ci_t[1]:.4f}] |")
    lines.append("")
    lines.append("### Statistical Tests")
    lines.append("")
    lines.append(f"- **Welch's t-test:** t = {t_stat:.4f}, p = {p_val:.6f}")
    lines.append(f"- **Cohen's d:** {d:.4f}")
    lines.append(f"- **Relative Lift:** {lift:+.2f}%")
    lines.append(f"- **Conclusion:** {'✅ Statistically significant (p < 0.05)' if p_val < 0.05 else '❌ Not statistically significant (p ≥ 0.05)'}")
    lines.append("")

    if p_val < 0.05:
        lines.append("> **Recommendation:** The new gift animation shows a statistically significant "
                     f"increase of {lift:.1f}% in gifts per session. We recommend rolling out to 100% of users.")
    else:
        lines.append("> **Recommendation:** The results are not statistically significant. "
                     "Consider extending the experiment or increasing sample size.")
    lines.append("")

    # ─── Experiment 2 ─────────────────────────────────────────
    lines.append("---")
    lines.append("## Experiment 2: Premium Tier Pricing")
    lines.append("")

    exp2 = pd.read_sql_query("""
        SELECT * FROM ab_experiments WHERE experiment_id = 2
    """, conn).iloc[0]

    lines.append(f"**Hypothesis:** {exp2['hypothesis']}")
    lines.append(f"**Period:** {exp2['start_date']} → {exp2['end_date']}")
    lines.append(f"**Primary Metric:** {exp2['primary_metric']}")
    lines.append(f"**Traffic:** {exp2['traffic_pct']}%")
    lines.append("")

    data2 = pd.read_sql_query("""
        SELECT aa.variant,
               COUNT(*) AS n,
               SUM(CAST(ae.event_value AS INTEGER)) AS conversions
        FROM ab_assignments aa
        JOIN ab_events ae ON aa.experiment_id = ae.experiment_id
                         AND aa.user_id = ae.user_id
        WHERE aa.experiment_id = 2
        GROUP BY aa.variant
    """, conn)

    ctrl2 = data2[data2["variant"] == "control"].iloc[0]
    treat2 = data2[data2["variant"] == "treatment"].iloc[0]

    p_c = ctrl2["conversions"] / ctrl2["n"]
    p_t = treat2["conversions"] / treat2["n"]

    p_pool = (ctrl2["conversions"] + treat2["conversions"]) / (ctrl2["n"] + treat2["n"])
    se = math.sqrt(p_pool * (1-p_pool) * (1/ctrl2["n"] + 1/treat2["n"]))
    z = (p_t - p_c) / se if se > 0 else 0
    p_val2 = 2 * (1 - stats.norm.cdf(abs(z)))

    # Wilson CIs
    def wilson_ci(p, n):
        z_val = 1.96
        denom = 1 + z_val**2/n
        centre = (p + z_val**2/(2*n)) / denom
        margin = z_val * math.sqrt((p*(1-p) + z_val**2/(4*n))/n) / denom
        return (centre - margin, centre + margin)

    ci_c2 = wilson_ci(p_c, ctrl2["n"])
    ci_t2 = wilson_ci(p_t, treat2["n"])
    h = 2 * (math.asin(math.sqrt(p_t)) - math.asin(math.sqrt(p_c)))
    lift2 = (p_t - p_c) / p_c * 100 if p_c > 0 else 0

    # Chi-squared
    contingency = np.array([
        [int(ctrl2["conversions"]), int(ctrl2["n"] - ctrl2["conversions"])],
        [int(treat2["conversions"]), int(treat2["n"] - treat2["conversions"])]
    ])
    chi2, chi_p, _, _ = stats.chi2_contingency(contingency)

    lines.append("### Results")
    lines.append("")
    lines.append("| Metric | Control | Treatment |")
    lines.append("|--------|---------|-----------|")
    lines.append(f"| Sample Size | {int(ctrl2['n']):,} | {int(treat2['n']):,} |")
    lines.append(f"| Conversions | {int(ctrl2['conversions']):,} | {int(treat2['conversions']):,} |")
    lines.append(f"| Conversion Rate | {p_c*100:.2f}% | {p_t*100:.2f}% |")
    lines.append(f"| 95% CI | [{ci_c2[0]*100:.2f}%, {ci_c2[1]*100:.2f}%] | [{ci_t2[0]*100:.2f}%, {ci_t2[1]*100:.2f}%] |")
    lines.append("")
    lines.append("### Statistical Tests")
    lines.append("")
    lines.append(f"- **Z-test for proportions:** z = {z:.4f}, p = {p_val2:.6f}")
    lines.append(f"- **Chi-squared test:** χ² = {chi2:.4f}, p = {chi_p:.6f}")
    lines.append(f"- **Cohen's h:** {h:.4f}")
    lines.append(f"- **Relative Lift:** {lift2:+.2f}%")
    lines.append(f"- **Conclusion:** {'✅ Statistically significant (p < 0.05)' if p_val2 < 0.05 else '❌ Not statistically significant (p ≥ 0.05)'}")
    lines.append("")

    if p_val2 < 0.05:
        lines.append("> **Recommendation:** The lower premium price shows a statistically significant "
                     f"increase of {lift2:.1f}% in conversion rate. Evaluate revenue impact before rollout "
                     "(lower price × higher volume may or may not net more revenue).")
    else:
        lines.append("> **Recommendation:** The results are not statistically significant at α = 0.05. "
                     "Consider running the experiment longer or with a larger sample.")
    lines.append("")

    # ─── Methodology ──────────────────────────────────────────
    lines.append("---")
    lines.append("## Methodology")
    lines.append("")
    lines.append("### Continuous Metrics")
    lines.append("- **Test:** Welch's two-sample t-test (does not assume equal variances)")
    lines.append("- **Confidence Intervals:** Student's t-distribution")
    lines.append("- **Effect Size:** Cohen's d = (M₂ − M₁) / s_pooled")
    lines.append("")
    lines.append("### Binary Metrics")
    lines.append("- **Test:** Z-test for two proportions + Chi-squared independence test")
    lines.append("- **Confidence Intervals:** Wilson score interval")
    lines.append("- **Effect Size:** Cohen's h = 2·arcsin(√p₂) − 2·arcsin(√p₁)")
    lines.append("")
    lines.append("### Decision Criteria")
    lines.append("- Significance level: α = 0.05")
    lines.append("- Two-tailed tests")
    lines.append("- p < 0.05 → reject H₀ → effect is statistically significant")
    lines.append("")

    conn.close()

    # Write report
    report = "\n".join(lines)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ Statistical report saved: {REPORT_PATH}")
    print(f"   ({len(lines)} lines)")


if __name__ == "__main__":
    generate_report()
