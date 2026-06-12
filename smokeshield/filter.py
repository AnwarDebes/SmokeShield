"""HVAC filter efficiency for PM2.5.

Filter efficiency for fine particles depends on the MERV rating
(ASHRAE 52.2-2017).  Published data:

    MERV 1-4:    < 20% on PM2.5 (cosmetic / fibreglass)
    MERV 6:      ~ 20-30%
    MERV 8:      ~ 40-50% (typical residential default)
    MERV 11:     ~ 65-80%
    MERV 13:     ~ 85% (recommended for wildfire smoke)
    MERV 14-16:  ~ 90-95%
    HEPA:        > 99.97% on PM0.3 (effective ~99.5%+ on PM2.5)

Numbers from Consumer Reports 2025 wildfire-smoke testing,
ACS ES&T Air 2024 university-building study (MERV 8 -> 0.28 IO ratio;
MERV 13 -> 0.12 IO ratio), and ASHRAE Standard 52.2 minimum
composite efficiencies for the E1 size range (0.3-1.0 um, which
covers the wildfire smoke peak).
"""

from __future__ import annotations

from dataclasses import dataclass


# MERV rating -> efficiency on PM2.5 (fraction captured)
# Values approximate the lower bound of ASHRAE 52.2 E1 size range.
MERV_EFFICIENCY = {
    1:  0.05,  2: 0.10,  3: 0.12,  4: 0.15,
    5:  0.18,  6: 0.22,  7: 0.30,  8: 0.42,
    9:  0.55, 10: 0.62, 11: 0.72, 12: 0.78,
    13: 0.85, 14: 0.90, 15: 0.92, 16: 0.95,
}


def hepa_efficiency() -> float:
    """True HEPA filters achieve > 99.97% on PM0.3 -- effectively ~ 0.995
    capture on PM2.5 by mass."""
    return 0.995


@dataclass
class MERVFilter:
    """An HVAC filter characterised by its MERV rating."""
    merv_rating: int

    @property
    def efficiency(self) -> float:
        if self.merv_rating <= 0:
            return 0.0
        if self.merv_rating >= 17:
            return hepa_efficiency()
        return MERV_EFFICIENCY.get(self.merv_rating, 0.42)

    @property
    def label(self) -> str:
        if self.merv_rating >= 17:
            return "HEPA"
        return f"MERV {self.merv_rating}"
