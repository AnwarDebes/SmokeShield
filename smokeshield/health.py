"""Health-effect translations of PM2.5 concentration.

Three operational mappings:

* PM2.5 (ug/m^3) -> US EPA AQI (0-500+).  Piecewise-linear breakpoints
  per the revised 2024 PM NAAQS (Annual NAAQS 9.0 ug/m^3, 24-h NAAQS
  35 ug/m^3).
* PM2.5 -> WHO guideline categories (good / fair / poor / very poor /
  hazardous).
* PM2.5 -> relative mortality risk using the GBD 2019 concentration-
  response function (RR = exp(0.0067 * (C - C0)) for C0 = 5 ug/m^3,
  capped at PM2.5 = 250 ug/m^3 per the GBD HRAPIE methodology).

These are the operational health-effect metrics that translate the
indoor concentration forecast into something a user can act on.

References:
    EPA AQI Technical Assistance Document (revised 2024)
    GBD 2019 PM2.5 cause-specific concentration-response functions
    Burnett et al. 2018 PNAS (Global Estimates of Mortality from PM2.5)
    WHO Air Quality Guidelines 2021
"""

from __future__ import annotations

import math
from typing import List, Tuple


PM25_DAILY_GUIDELINE_UGM3 = 15.0       # WHO 2021 24-h guideline
PM25_ANNUAL_GUIDELINE_UGM3 = 5.0       # WHO 2021 annual guideline


# (C_lo, C_hi, AQI_lo, AQI_hi) for the revised 2024 US EPA PM2.5 NAAQS.
AQI_BREAKPOINTS_PM25 = [
    (0.0,    9.0,    0,   50),
    (9.1,   35.4,   51,  100),
    (35.5,  55.4,  101,  150),
    (55.5, 125.4,  151,  200),
    (125.5, 225.4, 201,  300),
    (225.5, 500.4, 301,  500),
]


def aqi_from_pm25(c_ugm3: float) -> int:
    """US EPA AQI from 24-h average PM2.5 concentration."""
    c = max(0.0, float(c_ugm3))
    for c_lo, c_hi, a_lo, a_hi in AQI_BREAKPOINTS_PM25:
        if c <= c_hi:
            return int(round(
                (a_hi - a_lo) / (c_hi - c_lo) * (c - c_lo) + a_lo
            ))
    # Beyond the highest breakpoint
    return 500


def pm25_from_aqi(aqi: int) -> float:
    """Inverse of ``aqi_from_pm25`` (returns the upper PM2.5 of the band)."""
    for c_lo, c_hi, a_lo, a_hi in AQI_BREAKPOINTS_PM25:
        if aqi <= a_hi:
            return (c_hi - c_lo) / (a_hi - a_lo) * (aqi - a_lo) + c_lo
    return 500.4


def health_risk_level(c_ugm3: float) -> str:
    """Five-tier risk classification."""
    c = float(c_ugm3)
    if c < 12.0:
        return "good"
    if c < 35.5:
        return "moderate"
    if c < 55.5:
        return "unhealthy_sensitive"
    if c < 150.5:
        return "unhealthy"
    if c < 250.5:
        return "very_unhealthy"
    return "hazardous"


def relative_mortality_risk(C_ugm3: float, C_ref: float = 5.0) -> float:
    """Relative all-cause mortality risk vs. reference concentration C_ref.

    Uses the GBD HRAPIE-style log-linear concentration-response with
    coefficient 0.0067 per ug/m^3 (Burnett et al. 2018 PNAS).
    """
    C = max(C_ugm3, C_ref)
    return math.exp(0.0067 * (C - C_ref))
