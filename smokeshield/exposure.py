"""Personal exposure calculation: time-weighted concentration + cumulative dose.

A person spending t_indoor hours inside (concentration C_indoor) and
t_outdoor hours outside (C_outdoor) accumulates a time-weighted average
PM2.5 exposure:

    avg = (t_indoor * C_indoor + t_outdoor * C_outdoor) / (t_indoor + t_outdoor)

For risk comparison we report the equivalent "outdoor-only" daily
exposure -- the outdoor concentration that, breathed all day, would
produce the same dose.  This is the operational metric that matches
how EPA AQI bands are interpreted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np


@dataclass
class ExposureRecord:
    times_h: np.ndarray              # observation times
    C_breathed_ugm3: np.ndarray      # PM2.5 concentration the person was breathing
    fraction_indoor: np.ndarray      # 0-1 per timestep
    cumulative_dose_ugh_per_m3: float
    time_weighted_avg_ugm3: float
    equivalent_24h_outdoor_ugm3: float


def time_weighted_exposure(
    times_h: np.ndarray,
    C_outdoor_ugm3: np.ndarray,
    C_indoor_ugm3: np.ndarray,
    fraction_indoor: np.ndarray,
) -> ExposureRecord:
    times = np.asarray(times_h, dtype=np.float64)
    C_out = np.asarray(C_outdoor_ugm3, dtype=np.float64)
    C_in = np.asarray(C_indoor_ugm3, dtype=np.float64)
    f_in = np.asarray(fraction_indoor, dtype=np.float64)
    f_in = np.clip(f_in, 0.0, 1.0)
    C_breathed = f_in * C_in + (1.0 - f_in) * C_out
    dt = np.diff(times, prepend=times[0])
    dose = float(np.sum(C_breathed * dt))
    if times[-1] - times[0] > 0:
        twa = dose / (times[-1] - times[0])
    else:
        twa = float(C_breathed.mean())
    return ExposureRecord(
        times_h=times, C_breathed_ugm3=C_breathed, fraction_indoor=f_in,
        cumulative_dose_ugh_per_m3=dose,
        time_weighted_avg_ugm3=float(twa),
        equivalent_24h_outdoor_ugm3=float(twa),
    )


def accumulated_dose(
    times_h: np.ndarray, C_breathed_ugm3: np.ndarray,
) -> float:
    """Just the integral C * dt in units of ug-h/m^3."""
    times = np.asarray(times_h, dtype=np.float64)
    Cs = np.asarray(C_breathed_ugm3, dtype=np.float64)
    return float(np.trapezoid(Cs, times))
