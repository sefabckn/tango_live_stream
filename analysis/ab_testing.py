"""
A/B Testing Statistical Analysis for Live-Streaming Platform.

Implements:
  - Two-sample t-test (continuous metrics)
  - Z-test for proportions (binary metrics)
  - Chi-squared test
  - 95% Confidence Intervals
  - Cohen's d effect size
  - Power analysis & sample size estimation

Usage:
    python analysis/ab_testing.py
"""

import sqlite3
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "platform.db"
OUTPUT_DIR = PROJECT_ROOT / "data" / "ab_results"
OUTPUT_DIR.mkdir(exist_ok=True)


def get_conn():
    return sqlite3.connect(str(DB_PATH))


# ─── Utility Functions ───────────────────────────────────────

def cohens_d(group1, group2):
    """Calculate Cohen's d effect size."""
    n1, n2 = len(group1), len(group2)
    var1, var2 = group1.var(), group2.var()
    pooled_std = math.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    return (group2.mean() - group1.mean()) / pooled_std if pooled_std > 0 else 0


def interpret_cohens_d(d):
    """Interpret effect size magnitude."""
    d = abs(d)
    if d < 0.2:
        return "negligible"
    elif d < 0.5:
        return "small"
    elif d < 0.8:
        return "medium"
    else:
        return "large"


def required_sample_size(effect_size, alpha=0.05, power=0.80):
    """
    Estimate required sample size per group for a two-sample t-test.
    Uses the formula: n = 2 * ((z_alpha/2 + z_beta) / effect_size)^2
    """
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)
    n = 2 * ((z_alpha + z_beta) / effect_size) ** 2
    return int(math.ceil(n))


def proportion_ci(p, n, confidence=0.95):
    """Wilson score interval for a proportion."""
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
    return (centre - margin, centre + margin)


# ─── Experiment 1: Gift Animation Redesign ───────────────────

def analyse_gift_animation():
    """Analyse continuous metric: gifts per session."""
    print("=" * 60)
    print("  EXPERIMENT 1: Gift Animation Redesign")
    print("=" * 60)

    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT aa.variant, ae.user_id,
               AVG(ae.event_value) AS avg_gifts_per_session,
               COUNT(*) AS num_sessions
        FROM ab_assignments aa
        JOIN ab_events ae ON aa.experiment_id = ae.experiment_id
                         AND aa.user_id = ae.user_id
        WHERE aa.experiment_id = 1
        GROUP BY aa.variant, ae.user_id
    """, conn)
    conn.close()

    control = df[df["variant"] == "control"]["avg_gifts_per_session"]
    treatment = df[df["variant"] == "treatment"]["avg_gifts_per_session"]

    print(f"\n📊 Sample Sizes:")
    print(f"   Control:   n = {len(control):,}")
    print(f"   Treatment: n = {len(treatment):,}")

    print(f"\n📈 Descriptive Statistics:")
    print(f"   Control   — Mean: {control.mean():.4f}, Std: {control.std():.4f}, "
          f"Median: {control.median():.4f}")
    print(f"   Treatment — Mean: {treatment.mean():.4f}, Std: {treatment.std():.4f}, "
          f"Median: {treatment.median():.4f}")

    # ── Two-sample t-test (Welch's) ──
    t_stat, p_value = stats.ttest_ind(control, treatment, equal_var=False)
    print(f"\n🧪 Welch's Two-Sample T-Test:")
    print(f"   t-statistic: {t_stat:.4f}")
    print(f"   p-value:     {p_value:.6f}")
    print(f"   Significant: {'✅ YES' if p_value < 0.05 else '❌ NO'} (α = 0.05)")

    # ── Mann-Whitney U (non-parametric alternative) ──
    u_stat, mw_p = stats.mannwhitneyu(control, treatment, alternative="two-sided")
    print(f"\n🧪 Mann-Whitney U Test (non-parametric):")
    print(f"   U-statistic: {u_stat:.0f}")
    print(f"   p-value:     {mw_p:.6f}")

    # ── Confidence Intervals ──
    ci_ctrl = stats.t.interval(0.95, len(control)-1,
                               loc=control.mean(), scale=stats.sem(control))
    ci_treat = stats.t.interval(0.95, len(treatment)-1,
                                loc=treatment.mean(), scale=stats.sem(treatment))
    print(f"\n📐 95% Confidence Intervals:")
    print(f"   Control:   [{ci_ctrl[0]:.4f}, {ci_ctrl[1]:.4f}]")
    print(f"   Treatment: [{ci_treat[0]:.4f}, {ci_treat[1]:.4f}]")

    # ── Effect Size ──
    d = cohens_d(control, treatment)
    print(f"\n📏 Effect Size:")
    print(f"   Cohen's d: {d:.4f} ({interpret_cohens_d(d)})")

    # ── Relative Lift ──
    lift = (treatment.mean() - control.mean()) / control.mean() * 100
    print(f"\n🚀 Relative Lift: {lift:+.2f}%")

    # ── Power Analysis ──
    if abs(d) > 0:
        req_n = required_sample_size(abs(d))
        print(f"\n⚡ Power Analysis:")
        print(f"   Required n per group (80% power): {req_n:,}")
        print(f"   Actual n per group: ~{len(control):,}")
        print(f"   Sufficiently powered: {'✅ YES' if len(control) >= req_n else '⚠️ NO'}")

    # ── Visualisations ──
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle("Experiment 1: Gift Animation Redesign", fontsize=14, fontweight="bold")

    # Distribution overlay
    axes[0].hist(control, bins=30, alpha=0.6, color="#8892b0", label="Control", density=True)
    axes[0].hist(treatment, bins=30, alpha=0.6, color="#64ffda", label="Treatment", density=True)
    axes[0].axvline(control.mean(), color="#8892b0", linestyle="--", linewidth=2)
    axes[0].axvline(treatment.mean(), color="#64ffda", linestyle="--", linewidth=2)
    axes[0].set_title("Distribution of Avg Gifts/Session")
    axes[0].set_xlabel("Avg Gifts per Session")
    axes[0].legend()

    # CI plot
    means = [control.mean(), treatment.mean()]
    errors = [[m - ci[0], ci[1] - m] for m, ci in
              zip(means, [ci_ctrl, ci_treat])]
    colors = ["#8892b0", "#64ffda"]
    axes[1].barh(["Control", "Treatment"], means,
                 xerr=np.array(errors).T, color=colors, capsize=5, height=0.4)
    axes[1].set_title("Mean with 95% CI")
    axes[1].set_xlabel("Avg Gifts per Session")

    # Box plot
    axes[2].boxplot([control.values, treatment.values],
                    labels=["Control", "Treatment"],
                    patch_artist=True,
                    boxprops=dict(facecolor="#233554", color="#64ffda"),
                    medianprops=dict(color="#64ffda"))
    axes[2].set_title("Box Plot Comparison")
    axes[2].set_ylabel("Avg Gifts per Session")

    plt.tight_layout()
    path = OUTPUT_DIR / "experiment1_gift_animation.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="#0e1117")
    plt.close()
    print(f"\n📊 Plot saved: {path}")

    return {
        "experiment": "Gift Animation Redesign",
        "metric": "gifts_per_session",
        "n_control": len(control),
        "n_treatment": len(treatment),
        "mean_control": control.mean(),
        "mean_treatment": treatment.mean(),
        "ci_control": ci_ctrl,
        "ci_treatment": ci_treat,
        "t_stat": t_stat,
        "p_value": p_value,
        "cohens_d": d,
        "lift_pct": lift,
        "significant": p_value < 0.05,
    }


# ─── Experiment 2: Premium Tier Pricing ──────────────────────

def analyse_premium_pricing():
    """Analyse binary metric: subscription conversion rate."""
    print("\n" + "=" * 60)
    print("  EXPERIMENT 2: Premium Tier Pricing")
    print("=" * 60)

    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT aa.variant,
               COUNT(*) AS n,
               SUM(CAST(ae.event_value AS INTEGER)) AS conversions
        FROM ab_assignments aa
        JOIN ab_events ae ON aa.experiment_id = ae.experiment_id
                         AND aa.user_id = ae.user_id
        WHERE aa.experiment_id = 2
        GROUP BY aa.variant
    """, conn)
    conn.close()

    ctrl = df[df["variant"] == "control"].iloc[0]
    treat = df[df["variant"] == "treatment"].iloc[0]

    n_ctrl, conv_ctrl = int(ctrl["n"]), int(ctrl["conversions"])
    n_treat, conv_treat = int(treat["n"]), int(treat["conversions"])

    p_ctrl = conv_ctrl / n_ctrl
    p_treat = conv_treat / n_treat

    print(f"\n📊 Sample Sizes:")
    print(f"   Control:   n = {n_ctrl:,}, conversions = {conv_ctrl:,}")
    print(f"   Treatment: n = {n_treat:,}, conversions = {conv_treat:,}")

    print(f"\n📈 Conversion Rates:")
    print(f"   Control:   {p_ctrl*100:.2f}%")
    print(f"   Treatment: {p_treat*100:.2f}%")

    # ── Z-test for two proportions ──
    p_pool = (conv_ctrl + conv_treat) / (n_ctrl + n_treat)
    se = math.sqrt(p_pool * (1 - p_pool) * (1/n_ctrl + 1/n_treat))
    z_stat = (p_treat - p_ctrl) / se if se > 0 else 0
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

    print(f"\n🧪 Z-Test for Two Proportions:")
    print(f"   z-statistic: {z_stat:.4f}")
    print(f"   p-value:     {p_value:.6f}")
    print(f"   Significant: {'✅ YES' if p_value < 0.05 else '❌ NO'} (α = 0.05)")

    # ── Chi-squared test ──
    contingency = np.array([
        [conv_ctrl, n_ctrl - conv_ctrl],
        [conv_treat, n_treat - conv_treat]
    ])
    chi2, chi_p, dof, expected = stats.chi2_contingency(contingency)
    print(f"\n🧪 Chi-Squared Test:")
    print(f"   χ² statistic: {chi2:.4f}")
    print(f"   p-value:      {chi_p:.6f}")
    print(f"   dof:          {dof}")

    # ── Confidence Intervals (Wilson) ──
    ci_ctrl = proportion_ci(p_ctrl, n_ctrl)
    ci_treat = proportion_ci(p_treat, n_treat)
    print(f"\n📐 95% Confidence Intervals (Wilson):")
    print(f"   Control:   [{ci_ctrl[0]*100:.2f}%, {ci_ctrl[1]*100:.2f}%]")
    print(f"   Treatment: [{ci_treat[0]*100:.2f}%, {ci_treat[1]*100:.2f}%]")

    # ── Relative Lift ──
    lift = (p_treat - p_ctrl) / p_ctrl * 100 if p_ctrl > 0 else 0
    print(f"\n🚀 Relative Lift: {lift:+.2f}%")

    # ── Effect Size (Cohen's h) ──
    h = 2 * (math.asin(math.sqrt(p_treat)) - math.asin(math.sqrt(p_ctrl)))
    print(f"\n📏 Effect Size:")
    print(f"   Cohen's h: {h:.4f} ({interpret_cohens_d(abs(h))})")

    # ── Power Analysis ──
    if abs(h) > 0:
        req_n = required_sample_size(abs(h))
        print(f"\n⚡ Power Analysis:")
        print(f"   Required n per group (80% power): {req_n:,}")
        print(f"   Actual n per group: ~{n_ctrl:,}")
        print(f"   Sufficiently powered: {'✅ YES' if n_ctrl >= req_n else '⚠️ NO'}")

    # ── Visualisations ──
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Experiment 2: Premium Tier Pricing", fontsize=14, fontweight="bold")

    # Conversion rates with CI
    rates = [p_ctrl * 100, p_treat * 100]
    ci_low = [ci_ctrl[0] * 100, ci_treat[0] * 100]
    ci_high = [ci_ctrl[1] * 100, ci_treat[1] * 100]
    errors = [[r - lo, hi - r] for r, lo, hi in zip(rates, ci_low, ci_high)]

    bars = axes[0].bar(["Control", "Treatment"], rates,
                       yerr=np.array(errors).T, color=["#8892b0", "#64ffda"],
                       capsize=8, width=0.5)
    axes[0].set_ylabel("Conversion Rate (%)")
    axes[0].set_title("Conversion Rate with 95% CI")
    for bar, rate in zip(bars, rates):
        axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                     f"{rate:.2f}%", ha="center", fontweight="bold")

    # Contingency table visualisation
    labels = [["Converted\n(Control)", "Not Converted\n(Control)"],
              ["Converted\n(Treatment)", "Not Converted\n(Treatment)"]]
    axes[1].imshow(contingency, cmap="YlGnBu", aspect="auto")
    for i in range(2):
        for j in range(2):
            axes[1].text(j, i, f"{labels[i][j]}\n{contingency[i][j]:,}",
                        ha="center", va="center", fontsize=10, fontweight="bold")
    axes[1].set_xticks([0, 1])
    axes[1].set_xticklabels(["Converted", "Not Converted"])
    axes[1].set_yticks([0, 1])
    axes[1].set_yticklabels(["Control", "Treatment"])
    axes[1].set_title("Contingency Table")

    plt.tight_layout()
    path = OUTPUT_DIR / "experiment2_premium_pricing.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="#0e1117")
    plt.close()
    print(f"\n📊 Plot saved: {path}")

    return {
        "experiment": "Premium Tier Pricing",
        "metric": "subscription_conversion_rate",
        "n_control": n_ctrl,
        "n_treatment": n_treat,
        "rate_control": p_ctrl,
        "rate_treatment": p_treat,
        "ci_control": ci_ctrl,
        "ci_treatment": ci_treat,
        "z_stat": z_stat,
        "p_value": p_value,
        "chi2": chi2,
        "chi_p": chi_p,
        "cohens_h": h,
        "lift_pct": lift,
        "significant": p_value < 0.05,
    }


# ─── Main ────────────────────────────────────────────────────

def main():
    print("\n" + "█" * 60)
    print("  A/B TESTING — STATISTICAL ANALYSIS")
    print("█" * 60)

    results = []
    results.append(analyse_gift_animation())
    results.append(analyse_premium_pricing())

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    for r in results:
        status = "✅ SIGNIFICANT" if r["significant"] else "❌ NOT SIGNIFICANT"
        print(f"\n  {r['experiment']}:")
        print(f"    Metric:    {r['metric']}")
        print(f"    p-value:   {r['p_value']:.6f}")
        print(f"    Lift:      {r['lift_pct']:+.2f}%")
        print(f"    Result:    {status}")

    print(f"\n✅ All results saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
