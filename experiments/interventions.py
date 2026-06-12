"""Intervention tradeoff experiment.

For each archetype and each outdoor PM2.5 level, evaluate all 5
interventions and report:

    * indoor PM2.5 reduction (ug/m^3 and %)
    * one-time + daily cost
    * effective "$/ug/m^3 reduced" cost-effectiveness
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from smokeshield import (
    HOME_ARCHETYPES, evaluate_interventions, indoor_steady_state, aqi_from_pm25,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def main(out_path: Path = RESULTS_DIR / "interventions.json",
         C_outs=(50.0, 150.0, 250.0)):
    rows = []
    overall = time.time()
    for arch_key, profile in HOME_ARCHETYPES.items():
        for C_out in C_outs:
            baseline = indoor_steady_state(profile, C_out)
            ints = evaluate_interventions(profile, C_out)
            for it in ints:
                # cost effectiveness: weight one-time over a 5-year span
                cost_amortised = (it["one_time_cost_usd"] / (5 * 365)
                                    + it["daily_cost_usd"])
                rows.append({
                    "archetype": arch_key,
                    "C_outdoor_ugm3": float(C_out),
                    "intervention": it["intervention"],
                    "baseline_indoor_ugm3": float(baseline),
                    "after_intervention_indoor_ugm3": float(it["indoor_pm25_ugm3_after"]),
                    "reduction_percent": float(it["reduction_percent"]),
                    "reduction_ugm3":    float(it["reduction_ugm3"]),
                    "daily_amortised_cost_usd": float(cost_amortised),
                    "cost_per_ugm3_reduced": float(
                        cost_amortised / max(it["reduction_ugm3"], 1e-6)
                    ),
                    "one_time_cost_usd": float(it["one_time_cost_usd"]),
                    "baseline_aqi": int(aqi_from_pm25(baseline)),
                    "after_aqi":    int(aqi_from_pm25(it["indoor_pm25_ugm3_after"])),
                })

    print(f"Total: {time.time() - overall:.1f}s")

    # Pretty summary table
    print("\nIntervention ranking by % reduction (averaged over scenarios)")
    by_int = {}
    for r in rows:
        by_int.setdefault(r["intervention"], []).append(r)
    summary = []
    for it, rs in by_int.items():
        mean_red = float(np.mean([r["reduction_percent"] for r in rs]))
        mean_amort = float(np.mean([r["daily_amortised_cost_usd"] for r in rs]))
        mean_cost_eff = float(np.median([r["cost_per_ugm3_reduced"] for r in rs]))
        summary.append({"intervention": it,
                        "mean_reduction_percent": mean_red,
                        "mean_daily_amortised_cost_usd": mean_amort,
                        "median_cost_per_ugm3_reduced": mean_cost_eff})
    summary.sort(key=lambda r: -r["mean_reduction_percent"])
    for s in summary:
        print(f"  {s['intervention']:30s} "
              f"reduction={s['mean_reduction_percent']:5.1f}%  "
              f"daily_cost=${s['mean_daily_amortised_cost_usd']:.2f}  "
              f"$/ug={s['median_cost_per_ugm3_reduced']:.3f}")

    out_path.write_text(json.dumps({"per_case": rows, "summary": summary}, indent=2))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
