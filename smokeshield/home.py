"""Home profile: ventilation, sealing, HVAC, room volume.

Three archetypes calibrated to published data on US/Canadian housing
stock and wildfire-smoke studies:

* leaky_old:    Pre-1980 single-family detached, no central HVAC,
                window-only AC.  Infiltration 1.0-1.5 ACH, no MERV
                filter.  Documented I/O ratio without intervention:
                ~ 0.7-0.9 (NCCEH 2023 review).
* typical_modern: 1980-2010 single-family with central HVAC, MERV 8.
                Infiltration 0.3-0.5 ACH, HVAC recirc 5 ACH at 30%
                duty cycle.  Documented I/O ratio: ~ 0.3-0.5.
* tight_passive: Post-2010 well-sealed with central HVAC, MERV 13.
                Infiltration 0.15-0.25 ACH.  Documented I/O ratio:
                ~ 0.10-0.20.

Penetration factor P depends on envelope tightness and particle size;
for PM2.5 typical residential values are 0.7-0.9 (Liu and Nazaroff
2001, AAQR 2021).

References:
    Persily 1998 ASHRAE 62.2 ventilation rates
    Liu & Nazaroff 2001 Atmospheric Environment "Particle penetration"
    Aerosol and Air Quality Research 2021 (MERV vs I/O ratios)
    ACS ES&T Air 2024 (campus buildings during wildfire smoke)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from .filter import MERVFilter, MERV_EFFICIENCY


@dataclass
class HomeProfile:
    """One home's air-quality-relevant parameters."""
    label: str
    room_volume_m3: float                    # conditioned volume
    infiltration_ach: float                  # natural air changes per hour
    intentional_ventilation_ach: float       # additional intentional (windows open, fans)
    penetration_factor: float                # PM2.5 envelope penetration (0-1)
    deposition_rate_per_h: float             # PM2.5 deposition to surfaces (1/h)
    hvac_recirculation_ach: float            # HVAC circulation rate
    hvac_duty_cycle: float                   # fraction of time HVAC fan runs (0-1)
    hvac_filter: MERVFilter
    indoor_source_ug_per_h: float = 0.0      # cooking, smoking, candles


HOME_ARCHETYPES: Dict[str, HomeProfile] = {
    "leaky_old_no_hvac": HomeProfile(
        label="Pre-1980 leaky house, no central HVAC",
        room_volume_m3=350.0,                # ~150 m^2 floor x 2.4 m ceiling
        infiltration_ach=1.2,
        intentional_ventilation_ach=0.0,
        penetration_factor=0.85,
        deposition_rate_per_h=0.20,
        hvac_recirculation_ach=0.0,
        hvac_duty_cycle=0.0,
        hvac_filter=MERVFilter(merv_rating=0),
        indoor_source_ug_per_h=0.0,
    ),
    "typical_modern_merv8": HomeProfile(
        label="1980-2010 home, central HVAC, MERV 8 default",
        room_volume_m3=400.0,
        infiltration_ach=0.4,
        intentional_ventilation_ach=0.0,
        penetration_factor=0.80,
        deposition_rate_per_h=0.25,
        hvac_recirculation_ach=5.0,
        hvac_duty_cycle=0.30,
        hvac_filter=MERVFilter(merv_rating=8),
        indoor_source_ug_per_h=0.0,
    ),
    "tight_modern_merv13": HomeProfile(
        label="Post-2010 well-sealed home, central HVAC, MERV 13",
        room_volume_m3=420.0,
        infiltration_ach=0.20,
        intentional_ventilation_ach=0.0,
        penetration_factor=0.75,
        deposition_rate_per_h=0.30,
        hvac_recirculation_ach=6.0,
        hvac_duty_cycle=0.40,
        hvac_filter=MERVFilter(merv_rating=13),
        indoor_source_ug_per_h=0.0,
    ),
    "apartment_window_open": HomeProfile(
        label="Apartment with one window open",
        room_volume_m3=180.0,
        infiltration_ach=0.5,
        intentional_ventilation_ach=4.0,     # cross-ventilation
        penetration_factor=0.95,
        deposition_rate_per_h=0.20,
        hvac_recirculation_ach=0.0,
        hvac_duty_cycle=0.0,
        hvac_filter=MERVFilter(merv_rating=0),
        indoor_source_ug_per_h=0.0,
    ),
    "passive_house_hepa": HomeProfile(
        label="Passive House with HEPA whole-house filtration",
        room_volume_m3=400.0,
        infiltration_ach=0.05,
        intentional_ventilation_ach=0.30,
        penetration_factor=0.40,
        deposition_rate_per_h=0.30,
        hvac_recirculation_ach=4.0,
        hvac_duty_cycle=0.80,
        hvac_filter=MERVFilter(merv_rating=17),
        indoor_source_ug_per_h=0.0,
    ),
}


def archetype_to_profile(archetype_key: str) -> HomeProfile:
    return HOME_ARCHETYPES[archetype_key]
