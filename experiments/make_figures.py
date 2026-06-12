"""Generate the figures used in the SmokeShield paper.

Produces:
    fig_validation.pdf         - I/O ratio vs published bands
    fig_interventions.pdf      - intervention ranking by % reduction & cost
    fig_scenarios_la.pdf       - LA Palisades 2025 indoor traces
    fig_scenarios_canada.pdf   - Canada 2023 indoor traces
    fig_frontend_mock.pdf      - ASCII-like mock of the web UI
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from smokeshield import (
    HOME_ARCHETYPES, simulate_indoor, indoor_steady_state,
    evaluate_interventions,
    la_palisades_january_2025, canada_smoke_summer_2023,
    typical_commuter_day_outdoor_pm25,
    aqi_from_pm25,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "results"
FIG_DIR = ROOT / "paper" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 110,
    "savefig.dpi": 200,
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "legend.fontsize": 8,
    "figure.constrained_layout.use": True,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

ORANGE = "#d24a14"
BLUE = "#1e6fb8"
GREEN = "#1f8a3f"
GREY = "#5b6566"


def fig_validation():
    data = json.loads((RESULTS / "validation.json").read_text())
    rows = data["per_case"]
    archetypes = []
    seen = set()
    for r in rows:
        if r["archetype"] not in seen:
            archetypes.append(r["archetype"])
            seen.add(r["archetype"])
    fig, ax = plt.subplots(figsize=(7, 3.6))
    y = np.arange(len(archetypes))
    for i, a in enumerate(archetypes):
        per = [r for r in rows if r["archetype"] == a]
        io_pred = np.mean([r["io_ratio_predicted"] for r in per])
        io_lo = per[0]["io_ratio_published_min"]
        io_hi = per[0]["io_ratio_published_max"]
        ax.barh(i, io_hi - io_lo, left=io_lo, color="lightgrey",
                edgecolor="grey", label="Published range" if i == 0 else None)
        ax.plot([io_pred], [i], "o", color=ORANGE, markersize=10,
                label="SmokeShield prediction" if i == 0 else None)
        src = per[0]["source"]
        ax.text(0.985, i + 0.35, src, ha="right", va="bottom",
                fontsize=7, color=GREY)
    ax.set_yticks(y)
    ax.set_yticklabels([a.replace("_", " ") for a in archetypes])
    ax.set_xlabel("Steady-state indoor/outdoor PM2.5 ratio")
    ax.set_xlim(0, 1.0)
    ax.invert_yaxis()
    ax.legend(loc="lower right")
    ax.set_title("Validation: SmokeShield predictions vs published I/O bands")
    fig.savefig(FIG_DIR / "fig_validation.pdf")
    plt.close(fig)


def fig_interventions():
    data = json.loads((RESULTS / "interventions.json").read_text())
    summary = data["summary"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.4))
    interventions = [s["intervention"].replace("_", " ") for s in summary]
    pcts = [s["mean_reduction_percent"] for s in summary]
    costs = [s["mean_daily_amortised_cost_usd"] for s in summary]
    y = np.arange(len(interventions))

    bars = ax1.barh(y, pcts, color=BLUE, alpha=0.85)
    ax1.set_yticks(y); ax1.set_yticklabels(interventions)
    ax1.invert_yaxis()
    ax1.set_xlabel("Mean indoor PM2.5 reduction (%)")
    ax1.set_title("Intervention efficacy (averaged across archetypes & C_out)")
    ax1.set_xlim(0, 100)
    for i, p in enumerate(pcts):
        ax1.text(p + 1.5, i, f"{p:.0f}%", va="center", fontsize=9)

    ax2.barh(y, costs, color=ORANGE, alpha=0.85)
    ax2.set_yticks(y); ax2.set_yticklabels(["" for _ in interventions])
    ax2.invert_yaxis()
    ax2.set_xlabel("Mean daily amortised cost ($/day)")
    ax2.set_title("Cost (5-year amortisation of one-time spend)")
    for i, c in enumerate(costs):
        ax2.text(c + 0.02, i, f"${c:.2f}", va="center", fontsize=9)

    fig.savefig(FIG_DIR / "fig_interventions.pdf")
    plt.close(fig)


def _plot_scenario(scenario, archetypes, filename, suptitle=None):
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    ax.plot(scenario.times_h, scenario.C_outdoor_ugm3,
            color=ORANGE, linewidth=2, label="Outdoor")
    colors = ["#8c4a02", "#2078b4", "#1f8a3f", "#7e1adb", "#cc2222"]
    for ci, key in enumerate(archetypes):
        profile = HOME_ARCHETYPES[key]
        state = simulate_indoor(profile, scenario.times_h,
                                  scenario.C_outdoor_ugm3,
                                  C_in_init_ugm3=15.0)
        ax.plot(state.times_h, state.C_indoor_ugm3,
                color=colors[ci % len(colors)], linewidth=1.6,
                label=profile.label)
    ax.axhline(15, color="grey", linestyle="--", linewidth=1,
               label="WHO 24-h guideline")
    ax.set_xlabel("Time (h)")
    ax.set_ylabel("PM2.5 (μg/m³)")
    ax.set_title(suptitle or scenario.name)
    ax.legend(loc="upper right", framealpha=0.9, fontsize=8)
    fig.savefig(FIG_DIR / filename)
    plt.close(fig)


def fig_scenarios():
    _plot_scenario(la_palisades_january_2025(),
                   ["leaky_old_no_hvac", "typical_modern_merv8",
                    "tight_modern_merv13", "passive_house_hepa"],
                   "fig_scenarios_la.pdf",
                   "LA Palisades Fire, Jan 2025: indoor PM2.5 by home archetype")
    _plot_scenario(canada_smoke_summer_2023(),
                   ["leaky_old_no_hvac", "typical_modern_merv8",
                    "tight_modern_merv13", "passive_house_hepa"],
                   "fig_scenarios_canada.pdf",
                   "Canadian wildfire smoke (US Northeast), Jun 2023")
    _plot_scenario(typical_commuter_day_outdoor_pm25(),
                   ["leaky_old_no_hvac", "typical_modern_merv8",
                    "tight_modern_merv13", "passive_house_hepa"],
                   "fig_scenarios_commuter.pdf",
                   "Typical moderate-smoke day, 24h")


def fig_frontend_mock():
    """Render a screenshot of the frontend's layout for the paper."""
    fig, ax = plt.subplots(figsize=(8.3, 5.5))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6)
    ax.axis("off")

    # Header
    ax.add_patch(plt.Rectangle((0.0, 5.4), 10.0, 0.6, color="white",
                                 ec="#bcbcbc", lw=0.6))
    ax.text(0.25, 5.7, "SmokeShield", color=ORANGE, weight="bold", fontsize=14)
    ax.text(2.0, 5.7, "indoor air during wildfire smoke", color=GREY, fontsize=8)
    ax.text(9.7, 5.7, "no login, no tracking", color=GREY, fontsize=7, ha="right")

    # Input card
    ax.add_patch(plt.Rectangle((0.2, 0.3), 3.8, 5.0, color="white",
                                 ec="#bcbcbc", lw=0.6))
    ax.text(0.4, 5.05, "1. Outdoor air", weight="bold")
    ax.text(0.4, 4.75, "PM2.5 [150] μg/m³", fontsize=8, color="black",
              bbox=dict(boxstyle="round", facecolor="#fbfaf6"))
    ax.text(0.4, 4.45, "AQI 199 (Unhealthy)",  fontsize=8, color="#771010",
              bbox=dict(boxstyle="round", facecolor="#f1c4c4"))
    ax.text(0.4, 4.05, "2. Your home", weight="bold")
    ax.text(0.4, 3.75, "Modern home, MERV 8 HVAC ▾", fontsize=8,
              bbox=dict(boxstyle="round", facecolor="#fbfaf6"))
    ax.text(0.4, 3.45, "▸ Advanced: room volume, MERV…", fontsize=8, color=GREY)
    ax.text(0.4, 3.05, "3. Forecast horizon", weight="bold")
    ax.text(0.4, 2.75, "Hours [48]   ☑ constant outdoor",
              fontsize=8, color=GREY)
    ax.text(0.4, 1.8, "[ Forecast my indoor air ]", fontsize=8,
              color="white", bbox=dict(boxstyle="round", facecolor=ORANGE))
    ax.text(0.4, 1.3, "[ Save my home ]", fontsize=8, color=GREY,
              bbox=dict(boxstyle="round", facecolor="white", edgecolor=GREY))

    # Output card
    ax.add_patch(plt.Rectangle((4.2, 0.3), 5.6, 5.0, color="white",
                                 ec="#bcbcbc", lw=0.6))
    ax.text(4.4, 5.05, "What you would breathe indoors", weight="bold")
    ax.text(9.5, 5.05, "37.5 μg/m³", weight="bold", fontsize=15, color=BLUE, ha="right")
    ax.text(9.5, 4.7,  "AQI 105 (USG)  I/O 0.25", color=GREY, fontsize=7, ha="right")

    # Mini chart
    t = np.linspace(0, 48, 200)
    Cout = np.full_like(t, 150.0)
    Cin = 37.5 + (15 - 37.5) * np.exp(-0.6 * t)
    ax2 = fig.add_axes([0.46, 0.46, 0.45, 0.32])
    ax2.plot(t, Cout, color=ORANGE, lw=2)
    ax2.plot(t, Cin, color=BLUE, lw=2)
    ax2.axhline(15, color="grey", lw=0.7, ls="--")
    ax2.set_xlabel("hours", fontsize=7); ax2.set_ylabel("μg/m³", fontsize=7)
    ax2.tick_params(labelsize=6)
    ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

    # Recommendations
    ax.text(4.4, 2.2, "What to do  (ranked)", weight="bold")
    ax.text(4.4, 1.85, "1. Run HVAC fan continuously",        fontsize=8)
    ax.text(9.7, 1.85, "-58%   $0.50/d", ha="right", fontsize=8, color=GREEN)
    ax.text(4.4, 1.55, "2. Relocate to cleaner shelter",      fontsize=8)
    ax.text(9.7, 1.55, "-76%   free",     ha="right", fontsize=8, color=GREEN)
    ax.text(4.4, 1.25, "3. Add portable HEPA purifier",       fontsize=8)
    ax.text(9.7, 1.25, "-37%   $200+$0.20/d", ha="right", fontsize=8, color=GREEN)
    ax.text(4.4, 0.95, "4. Upgrade HVAC filter to MERV 13",   fontsize=8)
    ax.text(9.7, 0.95, "-34%   $25+$0.05/d",   ha="right", fontsize=8, color=GREEN)

    fig.savefig(FIG_DIR / "fig_frontend_mock.pdf")
    plt.close(fig)


def main():
    fig_validation()
    fig_interventions()
    fig_scenarios()
    fig_frontend_mock()
    print(f"Wrote figures to {FIG_DIR}")
    for f in sorted(FIG_DIR.glob("*.pdf")):
        print(f"  {f.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
