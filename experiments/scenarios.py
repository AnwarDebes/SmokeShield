"""Apply SmokeShield to documented historical scenarios.

For each scenario (LA Palisades 2025, Canada smoke 2023, typical
commuter day), simulate indoor PM2.5 over time for the five
archetypes and compute per-archetype cumulative exposure.

This is the "what would your home have done" experiment that
demonstrates the value of the model to a homeowner.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from smokeshield import (
    HOME_ARCHETYPES, simulate_indoor,
    la_palisades_january_2025, canada_smoke_summer_2023,
    typical_commuter_day_outdoor_pm25,
    time_weighted_exposure, aqi_from_pm25, relative_mortality_risk,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def run_scenario(scenario, archetypes_to_show=None) -> dict:
    if archetypes_to_show is None:
        archetypes_to_show = list(HOME_ARCHETYPES.keys())
    out = {"name": scenario.name, "notes": scenario.notes,
           "outdoor_peak_ugm3": float(scenario.C_outdoor_ugm3.max()),
           "outdoor_mean_ugm3": float(scenario.C_outdoor_ugm3.mean()),
           "outdoor_peak_aqi":   int(aqi_from_pm25(float(scenario.C_outdoor_ugm3.max()))),
           "outdoor_mean_aqi":   int(aqi_from_pm25(float(scenario.C_outdoor_ugm3.mean()))),
           "per_archetype": []}
    for key in archetypes_to_show:
        profile = HOME_ARCHETYPES[key]
        state = simulate_indoor(profile, scenario.times_h,
                                  scenario.C_outdoor_ugm3,
                                  C_in_init_ugm3=15.0)
        f_in = np.ones_like(state.times_h) * 0.90       # spend 90% indoors
        ex = time_weighted_exposure(
            state.times_h, state.C_outdoor_ugm3, state.C_indoor_ugm3, f_in,
        )
        rr = relative_mortality_risk(ex.time_weighted_avg_ugm3)
        out["per_archetype"].append({
            "archetype": key,
            "label": profile.label,
            "peak_indoor_ugm3": float(state.C_indoor_ugm3.max()),
            "mean_indoor_ugm3": float(state.C_indoor_ugm3.mean()),
            "peak_indoor_aqi":   int(aqi_from_pm25(float(state.C_indoor_ugm3.max()))),
            "mean_indoor_aqi":   int(aqi_from_pm25(float(state.C_indoor_ugm3.mean()))),
            "time_weighted_breathed_ugm3": float(ex.time_weighted_avg_ugm3),
            "relative_mortality_risk":     float(rr),
            "loss_rate_per_h": float(state.loss_rate_total_per_h),
            "io_ratio_steady_state": float(state.io_ratio_steady_state),
        })
    return out


def main(out_path: Path = RESULTS_DIR / "scenarios.json"):
    scenarios = [
        la_palisades_january_2025(),
        canada_smoke_summer_2023(),
        typical_commuter_day_outdoor_pm25(),
    ]
    results = []
    overall = time.time()
    for sc in scenarios:
        r = run_scenario(sc)
        results.append(r)
        print(f"\n=== {r['name']} (outdoor peak {r['outdoor_peak_ugm3']:.0f} "
              f"ug/m3, AQI {r['outdoor_peak_aqi']}) ===")
        print(f"  notes: {r['notes']}")
        for arch in r["per_archetype"]:
            print(f"  {arch['archetype']:25s}: peak_indoor={arch['peak_indoor_ugm3']:6.1f} ug/m3 "
                  f"(AQI {arch['peak_indoor_aqi']:3d})  twa={arch['time_weighted_breathed_ugm3']:6.1f}  "
                  f"RR={arch['relative_mortality_risk']:.3f}")
    print(f"\nTotal: {time.time() - overall:.1f}s")

    # Persist
    out_path.write_text(json.dumps({"per_scenario": results}, indent=2))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
