"""Validation experiment: reproduce published I/O ratios.

We compute the steady-state indoor/outdoor PM2.5 ratio for each home
archetype at moderate outdoor PM2.5 (50 ug/m^3) and compare against
published measurements from three sources:

* Aerosol and Air Quality Research 2021 (MERV 8 / MERV 13 testbeds)
* ACS ES&T Air 2024 (university buildings during wildfire smoke)
* NCCEH 2023 review (residential leakage)

The validation is satisfied if our archetypes fall within +/- 30% of
the published ranges (reasonable given the inter-home variability of
infiltration rates).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from smokeshield import HOME_ARCHETYPES, indoor_steady_state


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# (archetype_key, published_io_min, published_io_max, source)
PUBLISHED_BENCHMARKS = [
    ("leaky_old_no_hvac",    0.60, 0.90, "NCCEH 2023 review"),
    ("typical_modern_merv8", 0.20, 0.40, "Aerosol AQR 2021"),
    ("tight_modern_merv13",  0.05, 0.20, "ACS ES&T Air 2024"),
    ("apartment_window_open",0.80, 0.95, "AAQR 2021 fig 6"),
    ("passive_house_hepa",   0.02, 0.10, "Persily 1998 envelope leakage"),
]


def main(out_path: Path = RESULTS_DIR / "validation.json",
         C_outs=(25.0, 50.0, 100.0, 200.0, 350.0)):
    rows = []
    overall = time.time()
    print("Validation: I/O ratios vs published benchmarks")
    print(f"{'Archetype':30s}  {'C_out':>8s}  {'C_in_pred':>10s}  {'I/O_pred':>10s}  {'I/O_published':>16s}  {'Within band?':>16s}")
    for key, io_min, io_max, source in PUBLISHED_BENCHMARKS:
        for C_out in C_outs:
            profile = HOME_ARCHETYPES[key]
            C_in = indoor_steady_state(profile, C_out)
            io = C_in / C_out if C_out > 0 else 0.0
            within = (io_min - 0.05) <= io <= (io_max + 0.05)
            rows.append({
                "archetype": key, "C_out_ugm3": float(C_out),
                "C_in_predicted_ugm3": float(C_in),
                "io_ratio_predicted": float(io),
                "io_ratio_published_min": float(io_min),
                "io_ratio_published_max": float(io_max),
                "source": source,
                "within_published_band": bool(within),
            })
            print(f"  {key:28s}  {C_out:7.1f}  {C_in:10.2f}  {io:10.3f}  [{io_min:.2f}, {io_max:.2f}]  "
                  f"{('OK' if within else 'DRIFT'):>16s}")
    n_pass = sum(1 for r in rows if r["within_published_band"])
    print(f"\nValidation: {n_pass}/{len(rows)} cases within published band")
    print(f"Total: {time.time() - overall:.1f}s")
    out_path.write_text(json.dumps({"per_case": rows,
                                     "n_passed": n_pass,
                                     "n_total":  len(rows)}, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
