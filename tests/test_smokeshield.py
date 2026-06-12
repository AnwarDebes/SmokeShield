"""Unit tests for SmokeShield."""

import numpy as np
import pytest

from smokeshield import (
    MERVFilter, MERV_EFFICIENCY, hepa_efficiency,
    HOME_ARCHETYPES, HomeProfile,
    indoor_steady_state, simulate_indoor,
    time_weighted_exposure, accumulated_dose,
    aqi_from_pm25, pm25_from_aqi, health_risk_level,
    la_palisades_january_2025, canada_smoke_summer_2023,
    typical_commuter_day_outdoor_pm25,
    evaluate_interventions, recommend_interventions,
)


def test_merv_efficiency_monotone():
    for r in range(1, 16):
        assert MERV_EFFICIENCY[r] <= MERV_EFFICIENCY[r + 1] + 1e-9


def test_hepa_efficiency_high():
    assert hepa_efficiency() > 0.99


def test_aqi_monotone():
    prev = 0
    for c in (5, 10, 30, 70, 200, 400, 700):
        a = aqi_from_pm25(c)
        assert a >= prev
        prev = a


def test_aqi_round_trip_approx():
    # Going PM2.5 -> AQI -> PM2.5 should return ~ original within band
    for c in (8.5, 25.0, 45.0, 100.0, 180.0):
        aqi = aqi_from_pm25(c)
        c_back = pm25_from_aqi(aqi)
        # Within the band's upper bound
        assert c <= c_back + 5.0


def test_steady_state_below_outdoor_for_all_archetypes():
    """Indoor steady-state should always be lower than outdoor (no
    indoor sources) and lower for tighter / better-filtered homes."""
    C_out = 200.0
    Cs = {k: indoor_steady_state(p, C_out) for k, p in HOME_ARCHETYPES.items()}
    for c in Cs.values():
        assert c <= C_out + 1e-6
    # Tight modern with MERV 13 should be far below leaky old
    assert Cs["tight_modern_merv13"] < Cs["leaky_old_no_hvac"] / 2


def test_io_ratio_matches_published():
    """Literature-cited I/O ratios on PM2.5 at moderate outdoor (~50 ug/m3):
        leaky no-HVAC house:     ~ 0.7 (NCCEH 2023)
        modern MERV 8:           ~ 0.25-0.30 (Aerosol AQR 2021)
        tight MERV 13:           ~ 0.10-0.15 (ACS ES&T Air 2024)
    """
    C_out = 50.0
    io_leaky = indoor_steady_state(HOME_ARCHETYPES["leaky_old_no_hvac"], C_out) / C_out
    io_merv8 = indoor_steady_state(HOME_ARCHETYPES["typical_modern_merv8"], C_out) / C_out
    io_merv13 = indoor_steady_state(HOME_ARCHETYPES["tight_modern_merv13"], C_out) / C_out
    assert 0.6 < io_leaky < 0.85, f"leaky I/O {io_leaky}"
    assert 0.18 < io_merv8 < 0.40, f"MERV8 I/O {io_merv8}"
    assert 0.03 < io_merv13 < 0.20, f"MERV13 I/O {io_merv13}"


def test_simulate_indoor_converges_to_steady():
    profile = HOME_ARCHETYPES["typical_modern_merv8"]
    n_hours = 24; dt = 0.25
    times = np.arange(int(n_hours / dt)) * dt
    C_out = np.full_like(times, 100.0)
    state = simulate_indoor(profile, times, C_out, C_in_init_ugm3=0.0)
    final = state.C_indoor_ugm3[-1]
    expected = indoor_steady_state(profile, 100.0)
    assert abs(final - expected) < 0.5


def test_intervention_reduces_indoor_concentration():
    profile = HOME_ARCHETYPES["typical_modern_merv8"]
    rows = evaluate_interventions(profile, C_outdoor_ugm3=200.0)
    # Best intervention reduces concentration substantially
    assert rows[0]["reduction_percent"] > 30


def test_recommend_interventions_filters_noops():
    """Closing windows on a profile that has none open should be filtered."""
    profile = HOME_ARCHETYPES["typical_modern_merv8"]
    recs = recommend_interventions(profile, 200.0)
    for r in recs:
        assert r["reduction_percent"] > 1.0


def test_exposure_calculation_basic():
    times = np.arange(0, 24, 0.5)
    C_out = np.full_like(times, 100.0)
    C_in = np.full_like(times, 30.0)
    f_in = np.full_like(times, 0.8)
    ex = time_weighted_exposure(times, C_out, C_in, f_in)
    # 80% time at 30 + 20% time at 100 = 0.8*30 + 0.2*100 = 44
    assert abs(ex.time_weighted_avg_ugm3 - 44.0) < 1.5


def test_scenarios_have_realistic_peaks():
    """LA 2025 peaks 200-400; Canada 2023 peaks 150-450."""
    la = la_palisades_january_2025()
    ca = canada_smoke_summer_2023()
    com = typical_commuter_day_outdoor_pm25()
    assert 200 < la.C_outdoor_ugm3.max() < 400
    assert 150 < ca.C_outdoor_ugm3.max() < 500
    assert 60 < com.C_outdoor_ugm3.max() < 120


def test_health_risk_levels():
    assert health_risk_level(5.0) == "good"
    assert health_risk_level(25.0) == "moderate"
    assert health_risk_level(45.0) == "unhealthy_sensitive"
    assert health_risk_level(100.0) == "unhealthy"
    assert health_risk_level(200.0) == "very_unhealthy"
    assert health_risk_level(300.0) == "hazardous"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
