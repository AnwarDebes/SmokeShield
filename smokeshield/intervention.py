"""Intervention recommendations.

Given a baseline ``HomeProfile`` and an outdoor PM2.5 trajectory, we
enumerate candidate interventions, compute the resulting steady-state
indoor concentration, and rank by expected reduction in personal
exposure per unit of effort/cost.

Five canonical interventions calibrated to published cost-effectiveness:

* close_windows:      drop intentional ventilation to 0; no equipment cost.
* upgrade_filter_13:  swap HVAC filter to MERV 13; ~ $25 cost.
* run_hvac_continuously:  HVAC duty cycle -> 0.95; ~ $0.50/day energy.
* portable_hepa:      add stand-alone HEPA purifier in main room;
                      ~ $200 one-time + $0.20/day power.
* evacuate_to_tight_home:  pretend the user is in the
                          ``tight_modern_merv13`` archetype (e.g., visit
                          a neighbour's tighter home, or a public
                          cleaner-air shelter).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import List

from .home import HomeProfile, HOME_ARCHETYPES
from .filter import MERVFilter
from .physics import indoor_steady_state


@dataclass
class Intervention:
    key: str
    label: str
    one_time_cost_usd: float
    daily_cost_usd: float
    description: str


INTERVENTIONS = {
    "close_windows": Intervention(
        key="close_windows",
        label="Close all windows and external doors",
        one_time_cost_usd=0.0, daily_cost_usd=0.0,
        description="Most effective first step; drops intentional ventilation to zero.",
    ),
    "upgrade_filter_13": Intervention(
        key="upgrade_filter_13",
        label="Upgrade HVAC filter to MERV 13",
        one_time_cost_usd=25.0, daily_cost_usd=0.05,
        description="MERV 13 captures ~85% of PM2.5 vs ~42% for MERV 8.",
    ),
    "run_hvac_continuously": Intervention(
        key="run_hvac_continuously",
        label="Run HVAC fan continuously (duty cycle -> 95%)",
        one_time_cost_usd=0.0, daily_cost_usd=0.50,
        description="Recirculation through filter dominates indoor PM2.5 removal.",
    ),
    "portable_hepa": Intervention(
        key="portable_hepa",
        label="Add portable HEPA air purifier (300 m3/h CADR)",
        one_time_cost_usd=200.0, daily_cost_usd=0.20,
        description="Adds ~6 air changes per hour of HEPA-filtered air in a small room.",
    ),
    "evacuate_clean_shelter": Intervention(
        key="evacuate_clean_shelter",
        label="Relocate to cleaner-air shelter (e.g., library, mall, well-sealed friend's home)",
        one_time_cost_usd=0.0, daily_cost_usd=0.0,
        description="Public cleaner-air shelters typically achieve MERV 13+ filtration.",
    ),
}


def _apply_intervention(profile: HomeProfile, intervention_key: str
                          ) -> HomeProfile:
    p = copy.copy(profile)
    if intervention_key == "close_windows":
        p.intentional_ventilation_ach = 0.0
        p.penetration_factor = min(0.85, p.penetration_factor)
    elif intervention_key == "upgrade_filter_13":
        p.hvac_filter = MERVFilter(merv_rating=13)
        if p.hvac_duty_cycle == 0:
            p.hvac_duty_cycle = 0.30
            p.hvac_recirculation_ach = max(p.hvac_recirculation_ach, 5.0)
    elif intervention_key == "run_hvac_continuously":
        p.hvac_duty_cycle = 0.95
        if p.hvac_filter.merv_rating < 8:
            p.hvac_filter = MERVFilter(merv_rating=8)
        if p.hvac_recirculation_ach <= 0:
            p.hvac_recirculation_ach = 5.0
    elif intervention_key == "portable_hepa":
        # 300 m^3/h CADR through near-perfect HEPA in addition to HVAC
        cadr_ach = 300.0 / max(p.room_volume_m3, 1e-6)
        # Model as an additional HVAC recirc with HEPA at 100% duty
        eff_existing = p.hvac_filter.efficiency * p.hvac_recirculation_ach * p.hvac_duty_cycle
        eff_hepa = 0.995 * cadr_ach * 1.0
        # Lumped: pretend HVAC capacity grows by an equivalent term.
        total_eta_x_q_x_d = eff_existing + eff_hepa
        # Refactor as MERV17 (HEPA) recirc at duty 1.0
        p.hvac_filter = MERVFilter(merv_rating=17)
        p.hvac_recirculation_ach = total_eta_x_q_x_d / 0.995
        p.hvac_duty_cycle = 1.0
    elif intervention_key == "evacuate_clean_shelter":
        # Replace profile with archetype "tight_modern_merv13"
        return HOME_ARCHETYPES["tight_modern_merv13"]
    return p


def evaluate_interventions(profile: HomeProfile, C_outdoor_ugm3: float,
                             intervention_keys: List[str] = None) -> List[dict]:
    """Return per-intervention steady-state indoor PM2.5 and % reduction."""
    if intervention_keys is None:
        intervention_keys = list(INTERVENTIONS.keys())
    baseline = indoor_steady_state(profile, C_outdoor_ugm3)
    rows = []
    for key in intervention_keys:
        new_profile = _apply_intervention(profile, key)
        new_C = indoor_steady_state(new_profile, C_outdoor_ugm3)
        rows.append({
            "intervention": key,
            "label": INTERVENTIONS[key].label,
            "indoor_pm25_ugm3_after": float(new_C),
            "indoor_pm25_ugm3_baseline": float(baseline),
            "reduction_ugm3": float(baseline - new_C),
            "reduction_percent": float(100 * (baseline - new_C) / max(baseline, 1e-9)),
            "one_time_cost_usd": INTERVENTIONS[key].one_time_cost_usd,
            "daily_cost_usd": INTERVENTIONS[key].daily_cost_usd,
        })
    rows.sort(key=lambda r: -r["reduction_percent"])
    return rows


def recommend_interventions(profile: HomeProfile, C_outdoor_ugm3: float,
                              max_recommendations: int = 3) -> List[dict]:
    """Top-K interventions ranked by absolute reduction.  Filters out
    interventions that are no-ops on the given profile (e.g.,
    close_windows when no windows are open)."""
    rows = evaluate_interventions(profile, C_outdoor_ugm3)
    filtered = [r for r in rows if r["reduction_percent"] > 1.0]
    return filtered[:max_recommendations]
