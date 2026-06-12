# Changelog

All notable changes to SmokeShield are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-06-12

First public release.

### Added

- Indoor PM2.5 mass-balance ODE with infiltration, deposition, and
  filtration, calibrated for 5 home archetypes.
- MERV filter efficiency curves and HEPA/portable purifier modelling.
- EPA AQI translation and GBD HRAPIE relative-mortality risk.
- 5 candidate interventions ranked by PM2.5 reduction per dollar.
- Validation: 25 cases reproducing published indoor/outdoor ratios
  (NCCEH 2023, AAQR 2021, ACS ES&T Air 2024, Persily 1998).
- Simulations of three documented smoke events (LA Palisades Fire
  Jan 2025, Canadian wildfire smoke over the US Northeast Jun 2023,
  commuter scenario).
- Static browser frontend porting the physics to JavaScript: no build
  step, no network calls, profile stored in `localStorage` only.
- Validation, intervention, and scenario experiments with JSON outputs.
- LaTeX paper with figures.
- 12 unit tests.

[0.1.0]: https://github.com/AnwarDebes/SmokeShield/releases/tag/v0.1.0
