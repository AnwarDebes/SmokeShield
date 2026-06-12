// SmokeShield front-end.
// Pure client-side physics; no backend, no network calls.
// Mirrors the Python smokeshield library exactly.
//
// Physics model:  V dC_in/dt = (lam*P*V)*C_out - (lam + k_dep + eta*Q_hvac*D)*V*C_in
// Steady state:   C_in_ss = lam*P*C_out / (lam + k_dep + eta*Q_hvac*D)

"use strict";

// ---------- physics ----------

const MERV_EFFICIENCY = {
  0:0.00, 1:0.05, 2:0.10, 3:0.12, 4:0.15,
  5:0.18, 6:0.22, 7:0.30, 8:0.42,
  9:0.55, 10:0.62, 11:0.72, 12:0.78,
  13:0.85, 14:0.90, 15:0.92, 16:0.95,
  17:0.995    // HEPA
};

function mervEfficiency(merv) {
  if (merv <= 0) return 0;
  if (merv >= 17) return 0.995;
  return MERV_EFFICIENCY[merv] ?? 0.42;
}

function mervLabel(merv) {
  if (merv <= 0) return "no filter";
  if (merv >= 17) return "HEPA";
  return `MERV ${merv}`;
}

// Home archetypes: same numbers as smokeshield/home.py
const ARCHETYPES = {
  leaky_old_no_hvac: {
    label: "Pre-1980 leaky house, no central HVAC",
    volume: 350, infiltration: 1.2, ventilation: 0.0,
    penetration: 0.85, deposition: 0.20,
    hvacAch: 0.0, duty: 0.0, merv: 0,
  },
  typical_modern_merv8: {
    label: "1980-2010 home, central HVAC, MERV 8",
    volume: 400, infiltration: 0.4, ventilation: 0.0,
    penetration: 0.80, deposition: 0.25,
    hvacAch: 5.0, duty: 0.30, merv: 8,
  },
  tight_modern_merv13: {
    label: "Post-2010 well-sealed home, MERV 13",
    volume: 420, infiltration: 0.20, ventilation: 0.0,
    penetration: 0.75, deposition: 0.30,
    hvacAch: 6.0, duty: 0.40, merv: 13,
  },
  apartment_window_open: {
    label: "Apartment with one window open",
    volume: 180, infiltration: 0.5, ventilation: 4.0,
    penetration: 0.95, deposition: 0.20,
    hvacAch: 0.0, duty: 0.0, merv: 0,
  },
  passive_house_hepa: {
    label: "Passive House with HEPA whole-house filtration",
    volume: 400, infiltration: 0.05, ventilation: 0.30,
    penetration: 0.40, deposition: 0.30,
    hvacAch: 4.0, duty: 0.80, merv: 17,
  },
};

function lossRate(p) {
  const lam = p.infiltration + p.ventilation;
  const hvac = mervEfficiency(p.merv) * p.hvacAch * p.duty;
  // Portable HEPA injects additional cleaning at 100% duty against HEPA.
  const portable = (p.portableCadr || 0) / Math.max(p.volume, 1e-6) * 0.995;
  return lam + p.deposition + hvac + portable;
}

function sourceRate(p, Cout) {
  const lam = p.infiltration + p.ventilation;
  // indoor sources, not exposed in UI here
  return lam * p.penetration * Cout;
}

function steadyState(p, Cout) {
  const L = lossRate(p);
  if (L <= 0) return Cout;
  return sourceRate(p, Cout) / L;
}

function simulate(p, hoursTotal, Cout_series, dtH = 0.25, Cin0 = 12) {
  const n = Math.max(2, Math.round(hoursTotal / dtH));
  const times = new Array(n);
  const Cout = new Array(n);
  const Cin = new Array(n);
  const L = lossRate(p);
  for (let k = 0; k < n; k++) {
    times[k] = k * dtH;
    Cout[k] = (typeof Cout_series === "function")
      ? Cout_series(times[k])
      : Cout_series;
  }
  Cin[0] = Cin0;
  for (let k = 0; k < n - 1; k++) {
    const dt = times[k + 1] - times[k];
    const Css = steadyState(p, Cout[k]);
    Cin[k + 1] = Css + (Cin[k] - Css) * Math.exp(-L * dt);
  }
  return { times, Cout, Cin, L };
}

// ---------- AQI + risk ----------

const AQI_BREAKPOINTS = [
  [0.0,   9.0,   0,  50, "good",      "Good"],
  [9.1,  35.4,  51, 100, "moderate",  "Moderate"],
  [35.5, 55.4, 101, 150, "usg",       "Unhealthy for sensitive groups"],
  [55.5,125.4, 151, 200, "unhealthy", "Unhealthy"],
  [125.5,225.4,201, 300, "very",      "Very unhealthy"],
  [225.5,500.4,301, 500, "hazard",    "Hazardous"],
];

function aqiFromPm25(c) {
  c = Math.max(0, c);
  for (const [clo, chi, alo, ahi] of AQI_BREAKPOINTS) {
    if (c <= chi) {
      return Math.round((ahi - alo) / (chi - clo) * (c - clo) + alo);
    }
  }
  return 500;
}

function aqiCategoryForPm25(c) {
  c = Math.max(0, c);
  for (const [clo, chi, alo, ahi, cssClass, label] of AQI_BREAKPOINTS) {
    if (c <= chi) return { cssClass, label };
  }
  return { cssClass: "hazard", label: "Beyond hazardous" };
}

function relativeMortalityRisk(c) {
  // GBD HRAPIE log-linear, reference 5 ug/m3
  const x = Math.max(c, 5);
  return Math.exp(0.0067 * (x - 5));
}

// ---------- interventions ----------

function applyIntervention(p, key) {
  const q = { ...p };
  switch (key) {
    case "close_windows":
      q.ventilation = 0;
      q.penetration = Math.min(0.85, q.penetration);
      break;
    case "upgrade_filter_13":
      q.merv = 13;
      if (q.duty === 0) { q.duty = 0.30; q.hvacAch = Math.max(q.hvacAch, 5); }
      break;
    case "run_hvac_continuously":
      q.duty = 0.95;
      if (q.merv < 8) q.merv = 8;
      if (q.hvacAch <= 0) q.hvacAch = 5;
      break;
    case "portable_hepa": {
      const cadrAch = 300 / Math.max(q.volume, 1e-6);
      const effExisting = mervEfficiency(q.merv) * q.hvacAch * q.duty;
      const effHepa = 0.995 * cadrAch * 1.0;
      const totalEtaQD = effExisting + effHepa;
      q.merv = 17;
      q.hvacAch = totalEtaQD / 0.995;
      q.duty = 1.0;
      break;
    }
    case "evacuate_clean_shelter":
      return { ...ARCHETYPES.tight_modern_merv13 };
  }
  return q;
}

const INTERVENTION_INFO = {
  close_windows: {
    label: "Close all windows and external doors",
    desc:  "Drops intentional ventilation to zero; the cheapest first step.",
    oneTime: 0, daily: 0,
  },
  upgrade_filter_13: {
    label: "Upgrade your HVAC filter to MERV 13",
    desc:  "MERV 13 captures ~85% of PM2.5 vs ~42% for MERV 8.  Sold at any hardware store.",
    oneTime: 25, daily: 0.05,
  },
  run_hvac_continuously: {
    label: "Run your HVAC fan continuously",
    desc:  "Recirculation through the filter dominates indoor PM2.5 removal.  ~$0.50/day in power.",
    oneTime: 0, daily: 0.50,
  },
  portable_hepa: {
    label: "Add a portable HEPA air purifier (300 m³/h CADR)",
    desc:  "Adds ~6 air changes per hour of HEPA-clean air in a small room.  ~$150-250 one-time.",
    oneTime: 200, daily: 0.20,
  },
  evacuate_clean_shelter: {
    label: "Relocate to a cleaner-air shelter",
    desc:  "Public library, mall, or a friend's well-sealed home with central HVAC.",
    oneTime: 0, daily: 0,
  },
};

function rankInterventions(p, Cout) {
  const base = steadyState(p, Cout);
  const out = [];
  for (const key of Object.keys(INTERVENTION_INFO)) {
    const q = applyIntervention(p, key);
    const Cnew = steadyState(q, Cout);
    const reduction = base - Cnew;
    if (reduction <= 0.05) continue;     // skip no-ops
    out.push({
      key,
      label: INTERVENTION_INFO[key].label,
      desc:  INTERVENTION_INFO[key].desc,
      after: Cnew, baseline: base,
      reductionUgm3: reduction,
      reductionPct: 100 * reduction / Math.max(base, 1e-9),
      oneTime: INTERVENTION_INFO[key].oneTime,
      daily:   INTERVENTION_INFO[key].daily,
    });
  }
  out.sort((a, b) => b.reductionPct - a.reductionPct);
  return out;
}

// ---------- DOM + state ----------

const els = {
  outdoorPm25: document.getElementById("outdoorPm25"),
  archetype:   document.getElementById("archetype"),
  customPanel: document.getElementById("customPanel"),
  hours:       document.getElementById("hours"),
  constantOutdoor: document.getElementById("constantOutdoor"),
  recompute:   document.getElementById("recompute"),
  saveProfile: document.getElementById("saveProfile"),
  statusHint:  document.getElementById("statusHint"),
  aqiBadge:    document.getElementById("aqiBadge"),
  nowBox:      document.getElementById("nowBox"),
  indoorNow:   document.getElementById("indoorNow"),
  indoorAqi:   document.getElementById("indoorAqi"),
  ioRatio:     document.getElementById("ioRatio"),
  twa:         document.getElementById("twa"),
  rr:          document.getElementById("rr"),
  risk:        document.getElementById("risk"),
  recs:        document.getElementById("recs"),
  chart:       document.getElementById("chart"),
  // advanced
  volume:      document.getElementById("volume"),
  infiltration:document.getElementById("infiltration"),
  ventilation: document.getElementById("ventilation"),
  penetration: document.getElementById("penetration"),
  merv:        document.getElementById("merv"),
  hvacAch:     document.getElementById("hvacAch"),
  duty:        document.getElementById("duty"),
  portableCadr:document.getElementById("portableCadr"),
};

const PRESET_BUTTONS = document.querySelectorAll(".preset-btn");

function readProfileFromUi() {
  const key = els.archetype.value;
  if (key !== "custom") {
    const arch = ARCHETYPES[key];
    return { ...arch, portableCadr: 0 };
  }
  return {
    volume:       Math.max(20, parseFloat(els.volume.value)),
    infiltration: Math.max(0,  parseFloat(els.infiltration.value)),
    ventilation:  Math.max(0,  parseFloat(els.ventilation.value)),
    penetration:  Math.min(1, Math.max(0, parseFloat(els.penetration.value))),
    deposition:   0.25,
    hvacAch:      Math.max(0, parseFloat(els.hvacAch.value)),
    duty:         Math.min(1, Math.max(0, parseFloat(els.duty.value))),
    merv:         parseInt(els.merv.value, 10),
    portableCadr: Math.max(0, parseFloat(els.portableCadr.value)),
  };
}

function syncArchetypeToCustomFields() {
  const key = els.archetype.value;
  if (key === "custom") return;
  const a = ARCHETYPES[key];
  els.volume.value       = a.volume;
  els.infiltration.value = a.infiltration;
  els.ventilation.value  = a.ventilation;
  els.penetration.value  = a.penetration;
  els.merv.value         = a.merv;
  els.hvacAch.value      = a.hvacAch;
  els.duty.value         = a.duty;
}

// ---------- chart ----------

function drawChart(times, Cout, Cin) {
  const c = els.chart;
  if (!c || typeof c.getContext !== "function") return;
  const dpr = window.devicePixelRatio || 1;
  const cssW = c.clientWidth || 800, cssH = c.clientHeight || 320;
  c.width = cssW * dpr; c.height = cssH * dpr;
  const ctx = c.getContext("2d");
  if (!ctx) return;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, cssW, cssH);

  const padL = 50, padR = 16, padT = 14, padB = 32;
  const W = cssW - padL - padR;
  const H = cssH - padT - padB;

  const maxC = Math.max(50, ...Cout, ...Cin) * 1.1;
  const maxT = times[times.length - 1];

  // Background bands for AQI categories
  for (const [clo, chi, alo, ahi, cssClass] of AQI_BREAKPOINTS) {
    const yHi = padT + H * (1 - Math.min(chi, maxC) / maxC);
    const yLo = padT + H * (1 - Math.min(clo, maxC) / maxC);
    if (yLo <= padT || yHi >= padT + H) continue;
    const color = {
      good: "rgba(31,138,63,0.05)", moderate: "rgba(217,179,0,0.06)",
      usg: "rgba(217,118,0,0.07)", unhealthy: "rgba(204,34,34,0.07)",
      very: "rgba(126,26,219,0.07)", hazard: "rgba(94,13,13,0.08)"
    }[cssClass];
    ctx.fillStyle = color;
    ctx.fillRect(padL, yHi, W, yLo - yHi);
  }

  // Axes
  ctx.strokeStyle = "#999";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padL, padT); ctx.lineTo(padL, padT + H);
  ctx.lineTo(padL + W, padT + H); ctx.stroke();

  // Y ticks
  ctx.fillStyle = "#5b6566";
  ctx.font = "11px -apple-system, sans-serif";
  ctx.textAlign = "right";
  const yTicks = 5;
  for (let i = 0; i <= yTicks; i++) {
    const v = (maxC * i) / yTicks;
    const y = padT + H * (1 - i / yTicks);
    ctx.fillText(v.toFixed(0), padL - 4, y + 3);
    ctx.strokeStyle = i === 0 ? "#999" : "#e2e2dd";
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(padL + W, y); ctx.stroke();
  }
  // X ticks
  ctx.textAlign = "center";
  const xTicks = Math.min(6, Math.floor(maxT));
  for (let i = 0; i <= xTicks; i++) {
    const t = (maxT * i) / xTicks;
    const x = padL + (W * i) / xTicks;
    ctx.fillText(`${t.toFixed(0)}h`, x, padT + H + 16);
  }
  // Axis labels
  ctx.save();
  ctx.translate(14, padT + H / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("PM2.5 (μg/m³)", 0, 0);
  ctx.restore();

  // WHO guideline at 15
  ctx.strokeStyle = "#888";
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  const yG = padT + H * (1 - 15 / maxC);
  ctx.moveTo(padL, yG); ctx.lineTo(padL + W, yG);
  ctx.stroke();
  ctx.setLineDash([]);

  const xOf = (t) => padL + (t / maxT) * W;
  const yOf = (c) => padT + (1 - c / maxC) * H;

  // Outdoor
  ctx.strokeStyle = "#d24a14";
  ctx.lineWidth = 2;
  ctx.beginPath();
  for (let i = 0; i < times.length; i++) {
    const x = xOf(times[i]); const y = yOf(Cout[i]);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.stroke();

  // Indoor
  ctx.strokeStyle = "#1e6fb8";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  for (let i = 0; i < times.length; i++) {
    const x = xOf(times[i]); const y = yOf(Cin[i]);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.stroke();

  // Fill area under indoor curve for emphasis
  ctx.fillStyle = "rgba(30,111,184,0.10)";
  ctx.lineTo(xOf(times[times.length - 1]), padT + H);
  ctx.lineTo(xOf(times[0]), padT + H);
  ctx.closePath();
  ctx.fill();
}

// ---------- forecast driver ----------

function computeAndRender() {
  const Cout = Math.max(0, parseFloat(els.outdoorPm25.value));
  const hours = Math.max(6, parseInt(els.hours.value, 10));
  const profile = readProfileFromUi();

  // simulate
  const series = els.constantOutdoor.checked
    ? Cout
    : (t) => {
        // Sinusoidal smoke pulse, peak at t=hours/3, returning to background.
        const peak = Cout * 1.25;
        const base = Math.max(20, Cout * 0.4);
        const sigma = hours / 4;
        const mu = hours / 3;
        return base + (peak - base) * Math.exp(-((t - mu) ** 2) / (2 * sigma * sigma));
      };
  const sim = simulate(profile, hours, series);

  drawChart(sim.times, sim.Cout, sim.Cin);

  // Steady-state under the headline (final value of indoor)
  const Css = steadyState(profile, Cout);
  els.indoorNow.textContent = Css.toFixed(1);
  const indoorCat = aqiCategoryForPm25(Css);
  els.indoorAqi.textContent = `AQI ${aqiFromPm25(Css)} | ${indoorCat.label}`;
  els.indoorAqi.className = `now-aqi aqi-${indoorCat.cssClass}`;
  const io = Css / Math.max(Cout, 1e-6);
  els.ioRatio.textContent = `I/O ratio ${io.toFixed(2)}`;

  // Outdoor AQI badge
  const outdoorCat = aqiCategoryForPm25(Cout);
  els.aqiBadge.textContent = `AQI ${aqiFromPm25(Cout)} (${outdoorCat.label})`;
  els.aqiBadge.className = `info-pill aqi-${outdoorCat.cssClass}`;

  // TWA, RR, risk (assume 90% indoors)
  let twa = 0;
  for (let i = 0; i < sim.times.length - 1; i++) {
    const dt = sim.times[i + 1] - sim.times[i];
    const breathed = 0.9 * sim.Cin[i] + 0.1 * sim.Cout[i];
    twa += breathed * dt;
  }
  twa /= sim.times[sim.times.length - 1] || 1;
  els.twa.textContent = `${twa.toFixed(1)} μg/m³`;
  const rr = relativeMortalityRisk(twa);
  els.rr.textContent = `${rr.toFixed(2)}x`;
  const cat = aqiCategoryForPm25(Css);
  els.risk.textContent = cat.label;

  // Recommendations
  const recs = rankInterventions(profile, Cout).slice(0, 4);
  els.recs.innerHTML = "";
  for (const r of recs) {
    const li = document.createElement("li");
    const main = document.createElement("div");
    const nums = document.createElement("div");
    main.innerHTML = `<div class="rec-label">${r.label}</div>
                      <div class="rec-desc">${r.desc}</div>`;
    const cost = r.oneTime > 0
        ? `~$${r.oneTime.toFixed(0)} one-time + $${r.daily.toFixed(2)}/day`
        : (r.daily > 0 ? `$${r.daily.toFixed(2)}/day` : "free");
    nums.className = "rec-numbers";
    nums.innerHTML = `<span class="reduction">-${r.reductionPct.toFixed(0)}%</span>
                      <span>${r.after.toFixed(1)} μg/m³ indoor</span><br/>
                      <span>${cost}</span>`;
    li.appendChild(main); li.appendChild(nums);
    els.recs.appendChild(li);
  }
  if (recs.length === 0) {
    els.recs.innerHTML = "<li>Your home is already shielding you well.  Stay indoors and recheck if outdoor AQI rises.</li>";
  }

  els.statusHint.textContent = `Last forecast: outdoor ${Cout.toFixed(0)} μg/m³ → indoor ${Css.toFixed(1)} μg/m³ (I/O ${io.toFixed(2)}).`;
}

// ---------- persistence + bindings ----------

const STORAGE_KEY = "smokeshield.profile.v1";

function saveProfile() {
  const profile = {
    archetype: els.archetype.value,
    outdoorPm25: els.outdoorPm25.value,
    hours: els.hours.value,
    constantOutdoor: els.constantOutdoor.checked,
    volume: els.volume.value, infiltration: els.infiltration.value,
    ventilation: els.ventilation.value, penetration: els.penetration.value,
    merv: els.merv.value, hvacAch: els.hvacAch.value, duty: els.duty.value,
    portableCadr: els.portableCadr.value,
  };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
    els.statusHint.textContent = "Saved your home profile to this browser.";
  } catch (e) {
    els.statusHint.textContent = "Could not save (storage disabled).";
  }
}

function loadProfile() {
  try {
    const j = localStorage.getItem(STORAGE_KEY);
    if (!j) return;
    const p = JSON.parse(j);
    if (p.archetype)       els.archetype.value       = p.archetype;
    if (p.outdoorPm25)     els.outdoorPm25.value     = p.outdoorPm25;
    if (p.hours)           els.hours.value           = p.hours;
    if (typeof p.constantOutdoor === "boolean")
      els.constantOutdoor.checked = p.constantOutdoor;
    if (p.volume)          els.volume.value          = p.volume;
    if (p.infiltration)    els.infiltration.value    = p.infiltration;
    if (p.ventilation)     els.ventilation.value     = p.ventilation;
    if (p.penetration)     els.penetration.value     = p.penetration;
    if (p.merv)            els.merv.value            = p.merv;
    if (p.hvacAch)         els.hvacAch.value         = p.hvacAch;
    if (p.duty)            els.duty.value            = p.duty;
    if (p.portableCadr)    els.portableCadr.value    = p.portableCadr;
  } catch (_) {}
}

// Event bindings
els.recompute.addEventListener("click", computeAndRender);
els.saveProfile.addEventListener("click", saveProfile);
els.archetype.addEventListener("change", () => {
  if (els.archetype.value !== "custom") {
    syncArchetypeToCustomFields();
    els.customPanel.open = false;
  } else {
    els.customPanel.open = true;
  }
  computeAndRender();
});
els.outdoorPm25.addEventListener("input", computeAndRender);
els.hours.addEventListener("input", computeAndRender);
els.constantOutdoor.addEventListener("change", computeAndRender);

for (const id of ["volume","infiltration","ventilation","penetration",
                  "merv","hvacAch","duty","portableCadr"]) {
  els[id].addEventListener("input", () => {
    if (els.archetype.value !== "custom") els.archetype.value = "custom";
    computeAndRender();
  });
}

PRESET_BUTTONS.forEach(btn => {
  btn.addEventListener("click", () => {
    els.outdoorPm25.value = btn.dataset.preset;
    computeAndRender();
  });
});

// On window resize, redraw the chart
window.addEventListener("resize", () => computeAndRender());

// Initial render
loadProfile();
syncArchetypeToCustomFields();
computeAndRender();
