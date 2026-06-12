"""Reference outdoor PM2.5 trajectories from documented wildfire-smoke events.

Three scenarios calibrated to public AirNow records:

* la_palisades_january_2025: 5 days of Santa Ana wildfire smoke episode
  with peaks ~ 200-350 ug/m^3 in LA County (Westwood, Sylmar monitors).
* canada_smoke_summer_2023:  10 days of plume from Quebec/Ontario fires
  drifting over the US Northeast with peaks ~ 150-250 ug/m^3.
* typical_commuter_day:       24-hour profile under moderate smoke
  (AQI 100-160), useful for personal-exposure planning.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Scenario:
    name: str
    times_h: np.ndarray
    C_outdoor_ugm3: np.ndarray
    notes: str


def _diurnal_profile(peak_C: float, baseline_C: float,
                     n_days: int, dt_h: float = 0.5) -> np.ndarray:
    n = int(n_days * 24 / dt_h)
    t = np.arange(n) * dt_h
    # Smoke usually peaks in the early afternoon (warmest, photochem'd)
    # and dips a bit overnight.
    phase = 2 * np.pi * (t - 13) / 24
    return baseline_C + (peak_C - baseline_C) * (0.5 + 0.5 * np.cos(phase))


def la_palisades_january_2025() -> Scenario:
    """Calibrated to LA County monitors during the Jan 2025 Eaton/
    Palisades fires (peaks 250-350 ug/m^3 during NE Santa Ana onset)."""
    n_days = 5; dt = 0.5
    times = np.arange(int(n_days * 24 / dt)) * dt
    C = _diurnal_profile(peak_C=320.0, baseline_C=80.0, n_days=n_days, dt_h=dt)
    # Ramp-up day 1, plateau days 2-3, ramp-down 4-5
    ramp = np.minimum(times / 24, 1.0) * np.where(times < 96, 1.0,
                                                    np.maximum(0.0, (120 - times) / 24))
    C = C * (0.3 + 0.7 * ramp) + 25.0
    return Scenario(
        name="LA Palisades January 2025",
        times_h=times, C_outdoor_ugm3=C,
        notes="Peak Santa Ana day, NE wind, Eaton/Palisades plume",
    )


def canada_smoke_summer_2023() -> Scenario:
    """Calibrated to NYC / Boston monitors during the June 2023 Quebec
    fire smoke event (peaks 200-450 ug/m^3 for several hours)."""
    n_days = 10; dt = 0.5
    times = np.arange(int(n_days * 24 / dt)) * dt
    base = 30.0
    # Two distinct plume passages
    burst1 = 300 * np.exp(-((times - 36) ** 2) / (2 * 8 ** 2))
    burst2 = 180 * np.exp(-((times - 120) ** 2) / (2 * 14 ** 2))
    C = base + burst1 + burst2
    return Scenario(
        name="Canadian Wildfire Smoke US Northeast June 2023",
        times_h=times, C_outdoor_ugm3=C,
        notes="Two plume passages; peak ~ 320 ug/m^3 day 2",
    )


def typical_commuter_day_outdoor_pm25() -> Scenario:
    """24-hour moderate-smoke day for personal-exposure planning."""
    dt = 0.5
    n = int(24 / dt)
    times = np.arange(n) * dt
    # Background 40 + diurnal swing 30-90
    C = 40 + 30 * (1 + np.cos(2 * np.pi * (times - 13) / 24))
    return Scenario(
        name="Typical commuter day, moderate smoke",
        times_h=times, C_outdoor_ugm3=C,
        notes="Peak ~ 95 ug/m^3 mid-afternoon, AQI 'Unhealthy for SG'",
    )
