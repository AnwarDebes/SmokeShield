"""Indoor PM2.5 mass-balance ODE.

For a well-mixed indoor volume V with first-order loss terms:

    V dC_in/dt
      = (lambda * P * V) * C_out          # infiltration + intentional vent
        - lambda * V * C_in
        - k_dep * V * C_in                # surface deposition
        - eta * (Q_hvac * D) * C_in       # HVAC filtration
        + S_indoor                        # indoor sources

with steady-state solution:

    C_in_ss = (lambda * P * C_out + S/V) / (lambda + k_dep + eta * Q_hvac * D / V)

The transient solution at constant C_out is exponential with time
constant tau = 1 / (lambda + k_dep + eta * Q_hvac * D / V).  For
piecewise-constant C_out we solve the ODE analytically per piece.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .home import HomeProfile


@dataclass
class IndoorAirState:
    """Time series of indoor PM2.5 along with the loss terms."""
    times_h: np.ndarray
    C_indoor_ugm3: np.ndarray
    C_outdoor_ugm3: np.ndarray
    loss_rate_total_per_h: float
    io_ratio_steady_state: float


def _loss_rate(profile: HomeProfile) -> float:
    """Effective decay rate (1/h) for indoor PM2.5 inside ``profile``."""
    lam = profile.infiltration_ach + profile.intentional_ventilation_ach
    hvac = (profile.hvac_filter.efficiency
            * profile.hvac_recirculation_ach
            * profile.hvac_duty_cycle)
    return lam + profile.deposition_rate_per_h + hvac


def _source_rate(profile: HomeProfile, C_outdoor: float) -> float:
    """Effective production rate (1/h * ug/m^3) for indoor PM2.5."""
    lam = profile.infiltration_ach + profile.intentional_ventilation_ach
    return (lam * profile.penetration_factor * C_outdoor
            + profile.indoor_source_ug_per_h / max(profile.room_volume_m3, 1e-6))


def indoor_steady_state(profile: HomeProfile, C_outdoor_ugm3: float) -> float:
    """Steady-state indoor PM2.5 given constant outdoor concentration."""
    L = _loss_rate(profile)
    if L <= 0:
        return float(C_outdoor_ugm3)
    S = _source_rate(profile, C_outdoor_ugm3)
    return float(S / L)


def simulate_indoor(
    profile: HomeProfile,
    times_h: np.ndarray,
    C_outdoor_series_ugm3: np.ndarray,
    C_in_init_ugm3: float = 12.0,
) -> IndoorAirState:
    """Solve the mass-balance ODE for a piecewise-constant outdoor series.

    On each interval [t_k, t_{k+1}] with C_out = C_k, the solution is
    C_in(t) = C_in_ss + (C_in(t_k) - C_in_ss) * exp(-L * (t - t_k)),
    where C_in_ss is the steady state on that interval.
    """
    times = np.asarray(times_h, dtype=np.float64)
    C_out = np.asarray(C_outdoor_series_ugm3, dtype=np.float64)
    if times.shape != C_out.shape:
        raise ValueError("times_h and C_outdoor must have equal shape")
    L = _loss_rate(profile)
    C_in = np.zeros_like(times)
    C_in[0] = C_in_init_ugm3
    for k in range(len(times) - 1):
        dt = times[k + 1] - times[k]
        C_ss = indoor_steady_state(profile, C_out[k])
        # Average the analytical solution at the next step
        C_in[k + 1] = C_ss + (C_in[k] - C_ss) * np.exp(-L * dt)
    # I/O steady-state at the mean outdoor concentration
    io_ratio = (indoor_steady_state(profile, float(C_out.mean()))
                / max(float(C_out.mean()), 1e-9))
    return IndoorAirState(
        times_h=times, C_indoor_ugm3=C_in, C_outdoor_ugm3=C_out,
        loss_rate_total_per_h=float(L),
        io_ratio_steady_state=float(io_ratio),
    )
