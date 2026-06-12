"""SmokeShield: Personal Indoor Air Quality Forecaster for Wildfire Smoke.

A physics-based model for indoor PM2.5 concentration given outdoor
concentration and home characteristics (room volume, ventilation rate,
HVAC filter MERV rating, duty cycle, window status), with cumulative
exposure tracking and intervention recommendations.

The science:
    Indoor PM2.5 dynamics follow a first-order mass-balance ODE
    (ASHRAE 62.1, Persily-Walton airflow):

        V * dC_in/dt = lambda * V * P * C_out
                      - lambda * V * C_in
                      - k_dep * V * C_in
                      - eta_HVAC * Q_HVAC * C_in
                      + S_indoor

    where:
        V             = room volume (m^3)
        lambda        = air change rate (1/h), infiltration + intentional
        P             = particle penetration factor through envelope (0-1)
        eta_HVAC      = HVAC filter capture efficiency for PM2.5 (0-1)
        Q_HVAC        = HVAC recirculation flow (m^3/h)
        k_dep         = deposition rate to surfaces (1/h)
        S_indoor      = indoor PM2.5 sources (cooking, candles, etc.) (ug/h)
        C_out, C_in   = outdoor/indoor PM2.5 (ug/m^3)

Outputs:
    * Steady-state indoor PM2.5 given outdoor
    * Time-varying indoor PM2.5 given an outdoor trajectory
    * Time-weighted personal exposure (ug-h/m^3)
    * Equivalent outdoor exposure (for risk comparison)
    * Intervention recommendations (filter upgrade, sealing, etc.)
"""

from .filter import MERVFilter, MERV_EFFICIENCY, hepa_efficiency
from .home import HomeProfile, HOME_ARCHETYPES, archetype_to_profile
from .physics import (
    IndoorAirState, indoor_steady_state, simulate_indoor,
)
from .exposure import (
    ExposureRecord, time_weighted_exposure, accumulated_dose,
)
from .health import (
    aqi_from_pm25, pm25_from_aqi, health_risk_level,
    PM25_DAILY_GUIDELINE_UGM3, PM25_ANNUAL_GUIDELINE_UGM3,
    relative_mortality_risk,
)
from .scenarios import (
    Scenario, la_palisades_january_2025, canada_smoke_summer_2023,
    typical_commuter_day_outdoor_pm25,
)
from .intervention import (
    Intervention, INTERVENTIONS, evaluate_interventions,
    recommend_interventions,
)

__version__ = "0.1.0"

__all__ = [
    "MERVFilter", "MERV_EFFICIENCY", "hepa_efficiency",
    "HomeProfile", "HOME_ARCHETYPES", "archetype_to_profile",
    "IndoorAirState", "indoor_steady_state", "simulate_indoor",
    "ExposureRecord", "time_weighted_exposure", "accumulated_dose",
    "aqi_from_pm25", "pm25_from_aqi", "health_risk_level",
    "PM25_DAILY_GUIDELINE_UGM3", "PM25_ANNUAL_GUIDELINE_UGM3",
    "relative_mortality_risk",
    "Scenario", "la_palisades_january_2025", "canada_smoke_summer_2023",
    "typical_commuter_day_outdoor_pm25",
    "Intervention", "INTERVENTIONS", "evaluate_interventions",
    "recommend_interventions",
]
