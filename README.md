<div align="center">

<img src="assets/banner.svg" alt="SmokeShield" width="100%"/>

<br/>

[![Release](https://img.shields.io/github/v/release/AnwarDebes/SmokeShield?color=5fd0c0&label=release)](https://github.com/AnwarDebes/SmokeShield/releases)
[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![License: CC0-1.0](https://img.shields.io/badge/license-CC0--1.0-lightgrey)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-12%20passing-brightgreen)](tests/test_smokeshield.py)
[![Frontend](https://img.shields.io/badge/frontend-no%20backend-success)](frontend/)

**Indoor air during wildfire smoke. Free, no login, runs entirely in your browser.**

</div>

---

When the outdoor AQI hits 300, your phone tells you "stay indoors."
SmokeShield tells you what "indoors" actually means *for your home*:
the predicted PM2.5 level you would be breathing, the corresponding
EPA AQI category and mortality risk, and a ranked list of the four
interventions that would reduce it the most for the least money.

This repository contains:

1. `smokeshield/`: a calibrated Python library: indoor PM2.5
   mass-balance ODE, MERV filter efficiencies, EPA AQI translation,
   GBD HRAPIE relative-mortality risk, and a 5-intervention ranker.
2. `frontend/`: a single-page client-side web app that ports the
   physics to JavaScript. No login, no analytics, no backend.
3. `experiments/`: three experiments that validate the model
   against published I/O measurements, rank interventions, and
   simulate three documented smoke events.
4. `paper/smokeshield.pdf`: the technical paper documenting the
   model, validation, and frontend.

## Running the frontend

The frontend is a single-page static app. No build step.

```bash
cd frontend
python3 -m http.server 8000
# open http://127.0.0.1:8000/
```

Or drop the four files (`index.html`, `app.js`, `styles.css`,
`about.html`) onto any static host (GitHub Pages, S3, Cloudflare
Pages, Netlify) and it works. Cost: $0/month.

## Running the Python library

```bash
pip install -e .
```

```python
from smokeshield import (
    HOME_ARCHETYPES, indoor_steady_state, evaluate_interventions,
)

profile = HOME_ARCHETYPES["typical_modern_merv8"]
C_in = indoor_steady_state(profile, C_outdoor_ugm3=200.0)
print(f"Indoor PM2.5: {C_in:.1f} ug/m^3")   # -> 50.0 ug/m^3

for r in evaluate_interventions(profile, C_outdoor_ugm3=200.0)[:3]:
    print(f"  {r['label']}: -{r['reduction_percent']:.0f}%")
```

## Running the experiments

```bash
make experiments       # validation, interventions, scenarios -> results/*.json
make figures           # produces paper/figures/*.pdf
make paper             # builds paper/smokeshield.pdf
make test              # runs the unit tests
```

## Validation

All 25 cases (5 archetypes × 5 outdoor concentrations) reproduce the
indoor/outdoor PM2.5 ratio reported in five published studies (NCCEH
2023, AAQR 2021, ACS ES&T Air 2024, AAQR 2021 fig 6, Persily 1998)
within the cited bands. See `results/validation.json` and the
paper's §3.

## Privacy

SmokeShield does not phone home. No network calls, no analytics, no
cookies. Profile data is stored only in the user's browser
`localStorage`. The Python library makes no network calls.

## License

Public domain (CC0 1.0). See `LICENSE`.
