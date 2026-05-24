"""
health_dashboard.py — JARVIS Health Dashboard

Serves a self-contained HTML health dashboard at GET /health-dashboard.
All CSS and JS are inline. Data is loaded from existing JARVIS API endpoints.

Routes added via register_routes(app):
  GET /health-dashboard  — full dashboard page
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def get_dashboard_html() -> str:
    """Return the complete dashboard HTML as a self-contained string."""

    return r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JARVIS HEALTH</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:        #0d1117;
    --card:      #161b22;
    --border:    #30363d;
    --blue:      #58a6ff;
    --green:     #3fb950;
    --red:       #f85149;
    --amber:     #d29922;
    --muted:     #8b949e;
    --text:      #e6edf3;
    --radius:    8px;
    --gap:       20px;
  }

  html, body {
    background: var(--bg);
    color: var(--text);
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 14px;
    line-height: 1.5;
    min-height: 100vh;
  }

  /* ── Layout ── */
  .page { max-width: 1280px; margin: 0 auto; padding: 20px 24px 48px; }

  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: var(--gap); }
  .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--gap); }

  @media (max-width: 900px) {
    .grid-4 { grid-template-columns: repeat(2, 1fr); }
    .grid-2 { grid-template-columns: 1fr; }
  }

  /* ── Cards ── */
  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px 24px;
  }
  .card-title {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 16px;
  }

  /* ── Header ── */
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
    flex-wrap: wrap;
    gap: 12px;
  }
  .logo {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: .12em;
    color: var(--blue);
  }
  .logo span { color: var(--muted); font-weight: 400; font-size: 13px; margin-left: 10px; }
  .clock {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 13px;
    color: var(--muted);
  }

  /* ── Status bar ── */
  .status-bar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: var(--gap);
  }
  .pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 100px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: .04em;
    border: 1px solid transparent;
  }
  .pill-blue   { background: rgba(88,166,255,.15); border-color: rgba(88,166,255,.4);  color: var(--blue);  }
  .pill-green  { background: rgba(63,185,80,.15);  border-color: rgba(63,185,80,.4);   color: var(--green); }
  .pill-red    { background: rgba(248,81,73,.15);  border-color: rgba(248,81,73,.4);   color: var(--red);   }
  .pill-amber  { background: rgba(210,153,34,.15); border-color: rgba(210,153,34,.4);  color: var(--amber); }
  .pill-muted  { background: rgba(139,148,158,.1); border-color: rgba(139,148,158,.3); color: var(--muted); }
  .dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; display: inline-block; }

  .stat-label { font-size: 11px; color: var(--muted); margin-right: 4px; }
  .stat-value { font-size: 13px; color: var(--text); font-weight: 500; }

  /* ── Three Moves ── */
  .moves-list { list-style: none; counter-reset: moves; }
  .moves-list li {
    counter-increment: moves;
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 12px 0;
    border-bottom: 1px solid var(--border);
  }
  .moves-list li:last-child { border-bottom: none; }
  .moves-list li::before {
    content: counter(moves);
    flex-shrink: 0;
    width: 28px; height: 28px;
    background: rgba(88,166,255,.15);
    border: 1px solid rgba(88,166,255,.4);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 700; color: var(--blue);
  }
  .moves-list li span { padding-top: 4px; font-size: 15px; line-height: 1.4; }

  /* ── Metric tiles ── */
  .metric-tile {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 18px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .metric-label { font-size: 11px; color: var(--muted); font-weight: 600; letter-spacing: .06em; text-transform: uppercase; }
  .metric-row { display: flex; align-items: baseline; gap: 6px; }
  .metric-value { font-size: 28px; font-weight: 700; line-height: 1; }
  .metric-unit  { font-size: 12px; color: var(--muted); }
  .metric-trend { font-size: 16px; margin-left: auto; }
  .metric-sub   { font-size: 11px; color: var(--muted); margin-top: 2px; }
  .green { color: var(--green); }
  .red   { color: var(--red);   }
  .amber { color: var(--amber); }
  .blue  { color: var(--blue);  }

  /* ── Drift pills ── */
  .drift-grid { display: flex; flex-wrap: wrap; gap: 8px; }
  #drift-empty { color: var(--muted); font-style: italic; }

  /* ── Council ── */
  .council-list { list-style: none; }
  .council-item {
    border-bottom: 1px solid var(--border);
    overflow: hidden;
  }
  .council-item:last-child { border-bottom: none; }
  .council-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 0;
    cursor: pointer;
    user-select: none;
  }
  .council-header:hover { background: rgba(255,255,255,.03); margin: 0 -4px; padding-left: 4px; padding-right: 4px; border-radius: 4px; }
  .council-avatar {
    width: 32px; height: 32px; border-radius: 50%;
    background: rgba(88,166,255,.15);
    border: 1px solid rgba(88,166,255,.3);
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; flex-shrink: 0;
  }
  .council-name  { font-weight: 600; font-size: 13px; }
  .council-title { font-size: 11px; color: var(--muted); }
  .council-headline { font-size: 13px; color: var(--muted); margin-left: auto; max-width: 340px; text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .council-body {
    display: none;
    padding: 0 0 14px 44px;
    font-size: 13px;
    color: var(--muted);
    line-height: 1.6;
    white-space: pre-wrap;
  }
  .council-item.open .council-body { display: block; }
  .council-chevron { color: var(--muted); margin-left: 8px; transition: transform .2s; flex-shrink: 0; }
  .council-item.open .council-chevron { transform: rotate(90deg); }

  /* ── Medication table ── */
  .med-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .med-table th {
    text-align: left;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .06em;
    text-transform: uppercase;
    color: var(--muted);
    padding: 6px 8px;
    border-bottom: 1px solid var(--border);
  }
  .med-table td { padding: 8px 8px; border-bottom: 1px solid rgba(48,54,61,.6); vertical-align: top; }
  .med-table tr:last-child td { border-bottom: none; }
  .flag { font-size: 11px; color: var(--red); font-weight: 600; margin-top: 2px; display: block; }

  /* ── Upcoming actions ── */
  .check-list { list-style: none; display: flex; flex-direction: column; gap: 10px; }
  .check-item { display: flex; align-items: flex-start; gap: 10px; }
  .check-item input[type=checkbox] { margin-top: 2px; accent-color: var(--blue); width: 15px; height: 15px; flex-shrink: 0; }
  .check-item label { font-size: 13px; line-height: 1.4; cursor: pointer; }
  .check-meta { font-size: 11px; color: var(--muted); }

  /* ── Sparklines ── */
  .sparkline-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--gap); }
  @media (max-width: 600px) { .sparkline-grid { grid-template-columns: 1fr; } }
  .sparkline-card { }
  .spark-label { font-size: 12px; font-weight: 600; color: var(--text); margin-bottom: 4px; }
  .spark-sub    { font-size: 11px; color: var(--muted); margin-bottom: 8px; }
  .spark-latest { font-size: 22px; font-weight: 700; }
  svg.sparkline { display: block; width: 100%; height: 50px; overflow: visible; }

  /* ── Loading ── */
  .loading { color: var(--muted); font-style: italic; font-size: 13px; }

  /* ── Section spacing ── */
  .section { margin-bottom: var(--gap); }

  /* Twin panel */
  .twin-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
  .twin-metric { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 12px; }
  .twin-metric-name { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
  .twin-current { font-size: 13px; color: #8b949e; }
  .twin-projected { font-size: 20px; font-weight: 600; margin: 4px 0; }
  .twin-ci { font-size: 11px; color: #8b949e; }
  .twin-direction { font-size: 12px; margin-top: 4px; }
  .twin-track-good { color: #3fb950; }
  .twin-track-bad { color: #f85149; }
  .twin-track-ok { color: #d29922; }
  .twin-stable { color: #8b949e; }
  .btn-small { background: #21262d; border: 1px solid #30363d; color: #c9d1d9; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; }
  .btn-small:hover { background: #30363d; }
  .showdown-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
  .showdown-table th { text-align: left; padding: 6px 8px; color: #8b949e; border-bottom: 1px solid #30363d; }
  .showdown-table td { padding: 6px 8px; border-bottom: 1px solid #21262d; }
  .twin-loading { color: #8b949e; font-size: 13px; padding: 20px; text-align: center; }

  /* ── Longevity Card ── */
  .longevity-hero { display: flex; gap: 32px; align-items: flex-start; flex-wrap: wrap; margin-bottom: 20px; }
  .longevity-main { display: flex; flex-direction: column; align-items: center; min-width: 160px; }
  .longevity-number { font-size: 4.5rem; font-weight: 800; line-height: 1; letter-spacing: -2px; }
  .longevity-number.amber { color: #d29922; }
  .longevity-number.green { color: #3fb950; }
  .longevity-number.red   { color: #f85149; }
  .longevity-label { font-size: 11px; text-transform: uppercase; letter-spacing: .1em; color: #8b949e; margin-top: 2px; }
  .longevity-remaining { font-size: 14px; color: #8b949e; margin-top: 4px; }
  .longevity-ci { font-size: 12px; color: #58a6ff; margin-top: 2px; }
  .longevity-optimized { border-left: 3px solid #3fb950; padding-left: 16px; }
  .longevity-opt-num { font-size: 2.5rem; font-weight: 700; color: #3fb950; line-height: 1; }
  .longevity-opt-label { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: .08em; }
  .longevity-opt-gain { font-size: 13px; color: #3fb950; margin-top: 4px; }
  .longevity-graph { width: 100%; margin: 12px 0 20px 0; }
  .longevity-factors { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .lon-factor-title { font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid #30363d; }
  .lon-factor-title.neg { color: #f85149; }
  .lon-factor-title.pos { color: #3fb950; }
  .lon-factor-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; font-size: 12px; border-bottom: 1px solid rgba(48,54,61,0.5); }
  .lon-factor-name { color: #c9d1d9; flex: 1; }
  .lon-factor-val { font-weight: 700; font-size: 13px; white-space: nowrap; margin-left: 8px; }
  .lon-factor-val.neg { color: #f85149; }
  .lon-factor-val.pos { color: #3fb950; }
  .lon-modifiable { margin-top: 14px; background: rgba(210,153,34,0.1); border: 1px solid rgba(210,153,34,0.3); border-radius: 6px; padding: 10px 12px; font-size: 12px; color: #d29922; text-align: center; }
  .lon-loading { color: #8b949e; font-size: 13px; padding: 30px; text-align: center; }
</style>
</head>
<body>
<div class="page">

  <!-- ─── HEADER ─── -->
  <header>
    <div>
      <div class="logo">JARVIS HEALTH<span>Longevity Command Center</span></div>
    </div>
    <div class="clock" id="clock">--:--:-- --</div>
  </header>

  <!-- ─── STATUS BAR ─── -->
  <div class="status-bar section" id="status-bar">
    <span class="pill pill-muted" id="oracle-badge"><span class="dot"></span> Loading…</span>
    <span><span class="stat-label">Last council:</span><span class="stat-value" id="last-council">—</span></span>
    <span><span class="stat-label">Score:</span><span class="stat-value" id="completeness">—</span></span>
    <span id="day-type-badge" class="pill pill-blue" style="display:none"></span>
  </div>

  <!-- ─── TODAY'S THREE MOVES ─── -->
  <div class="card section">
    <div class="card-title">Today's Three Moves</div>
    <ul class="moves-list" id="three-moves">
      <li><span>Confirm last night's CPAP session in the app and log compliance.</span></li>
      <li><span>Take semaglutide dose (weekly — verify day of week) and log in health log.</span></li>
      <li><span>15-minute walk after dinner to support glucose control and LDL management.</span></li>
    </ul>
  </div>

  <!-- ─── KEY METRICS GRID ─── -->
  <div class="section">
    <div class="grid-4" style="margin-bottom: var(--gap)">

      <div class="metric-tile">
        <div class="metric-label">A1c</div>
        <div class="metric-row">
          <span class="metric-value amber" id="m-a1c">7.3</span>
          <span class="metric-unit">%</span>
          <span class="metric-trend amber">↑</span>
        </div>
        <div class="metric-sub">Target &lt;7.0 · Last: Apr 2026</div>
      </div>

      <div class="metric-tile">
        <div class="metric-label">LDL</div>
        <div class="metric-row">
          <span class="metric-value red" id="m-ldl">156</span>
          <span class="metric-unit">mg/dL</span>
          <span class="metric-trend red">↑</span>
        </div>
        <div class="metric-sub">Target &lt;100 · Last: Apr 2026</div>
      </div>

      <div class="metric-tile">
        <div class="metric-label">Blood Pressure</div>
        <div class="metric-row">
          <span class="metric-value green" id="m-bp">118/76</span>
          <span class="metric-unit">mmHg</span>
          <span class="metric-trend green">→</span>
        </div>
        <div class="metric-sub">Target &lt;130/80 · Omron</div>
      </div>

      <div class="metric-tile">
        <div class="metric-label">eGFR</div>
        <div class="metric-row">
          <span class="metric-value amber" id="m-egfr">87</span>
          <span class="metric-unit">mL/min</span>
          <span class="metric-trend amber">↓</span>
        </div>
        <div class="metric-sub">Stage 2 CKD · Last: Apr 2026</div>
      </div>

    </div>
    <div class="grid-4">

      <div class="metric-tile">
        <div class="metric-label">Weight</div>
        <div class="metric-row">
          <span class="metric-value blue" id="m-weight">—</span>
          <span class="metric-unit">lbs</span>
          <span class="metric-trend" id="m-weight-trend">—</span>
        </div>
        <div class="metric-sub" id="m-weight-sub">Loading from health DB…</div>
      </div>

      <div class="metric-tile">
        <div class="metric-label">BMI</div>
        <div class="metric-row">
          <span class="metric-value amber" id="m-bmi">—</span>
          <span class="metric-unit"></span>
          <span class="metric-trend amber">↓</span>
        </div>
        <div class="metric-sub">Target &lt;25 · Calculated</div>
      </div>

      <div class="metric-tile">
        <div class="metric-label">HRV</div>
        <div class="metric-row">
          <span class="metric-value blue" id="m-hrv">—</span>
          <span class="metric-unit">ms</span>
          <span class="metric-trend" id="m-hrv-trend">→</span>
        </div>
        <div class="metric-sub">Apple Watch · 7-day avg</div>
      </div>

      <div class="metric-tile">
        <div class="metric-label">Steps</div>
        <div class="metric-row">
          <span class="metric-value blue" id="m-steps">—</span>
          <span class="metric-unit">today</span>
          <span class="metric-trend" id="m-steps-trend">→</span>
        </div>
        <div class="metric-sub">Target 8,000 · Apple Watch</div>
      </div>

    </div>
  </div>

  <!-- ─── DRIFT ALERTS + COUNCIL (side by side) ─── -->
  <div class="grid-2 section">

    <div class="card">
      <div class="card-title">Drift Alerts</div>
      <div class="drift-grid" id="drift-container">
        <span class="loading">Scanning drift clusters…</span>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Medication Safety</div>
      <div id="med-container">
        <span class="loading">Loading medications…</span>
      </div>
    </div>

  </div>

  <!-- ─── COUNCIL SUMMARY ─── -->
  <div class="card section">
    <div class="card-title" style="display:flex;align-items:center;justify-content:space-between;">
      <span>Longevity Council</span>
      <button onclick="refreshCouncil()" style="background:rgba(88,166,255,.12);border:1px solid rgba(88,166,255,.3);color:var(--blue);border-radius:6px;padding:3px 10px;font-size:11px;cursor:pointer;">Refresh ↻</button>
    </div>
    <ul class="council-list" id="council-list">
      <li style="padding:12px 0;color:var(--muted);font-style:italic;">Assembling the council…</li>
    </ul>
  </div>

  <!-- ─── UPCOMING ACTIONS + LAB TRENDS (side by side) ─── -->
  <div class="grid-2 section">

    <div class="card">
      <div class="card-title">Upcoming Actions</div>
      <ul class="check-list">
        <li class="check-item">
          <input type="checkbox" id="c1">
          <label for="c1"><strong>CPAP compliance confirm</strong> — verify last night's session in the myAir app<br><span class="check-meta">Daily · AHI target &lt;5 events/hr</span></label>
        </li>
        <li class="check-item">
          <input type="checkbox" id="c2">
          <label for="c2"><strong>Colonoscopy scheduled</strong> — confirm appointment and prep instructions<br><span class="check-meta">Overdue · High priority</span></label>
        </li>
        <li class="check-item">
          <input type="checkbox" id="c3">
          <label for="c3"><strong>Dr. Wenk follow-up</strong> — Nov 13 appointment prep: A1c trend, LDL escalation, CKD monitoring<br><span class="check-meta">Nov 13 · Primary care</span></label>
        </li>
        <li class="check-item">
          <input type="checkbox" id="c4">
          <label for="c4"><strong>Semaglutide refill</strong> — contact pharmacy before supply runs out<br><span class="check-meta">Weekly dose · GLP-1 agonist</span></label>
        </li>
        <li class="check-item">
          <input type="checkbox" id="c5">
          <label for="c5"><strong>Repeat lipid panel</strong> — LDL at 156 mg/dL, statin discussion with Dr. Wenk<br><span class="check-meta">Pending · Discuss medication escalation</span></label>
        </li>
      </ul>
    </div>

    <div class="card">
      <div class="card-title">Lab Trends</div>
      <div class="sparkline-grid" id="sparklines">
        <!-- Rendered by JS -->
      </div>
    </div>

  </div>

  <!-- ─── LONGEVITY PROJECTION ─── -->
  <div class="card section" id="longevity-panel">
    <div class="card-title">⏳ Longevity Projection</div>
    <div id="longevity-content"><div class="lon-loading">Loading longevity estimate…</div></div>
  </div>

  <!-- ─── DIGITAL TWIN ─── -->
  <div class="card section" id="twin-panel">
    <div class="card-title">🧬 Digital Twin — 12-Month Projections</div>
    <div class="twin-grid" id="twin-grid">
      <!-- Populated by JS from /api/health/twin/project -->
      <div class="twin-loading">Loading twin projections…</div>
    </div>
    <div class="twin-actions" style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;">
      <button class="btn-small" onclick="runLDLShowdown()">LDL Showdown</button>
      <button class="btn-small" onclick="simulateIntervention('add_ezetimibe_10mg,exercise_150min_week')">Ezetimibe + Exercise</button>
      <button class="btn-small" onclick="simulateIntervention('weight_loss_10pct,cpap_confirmed')">Weight Loss + CPAP</button>
      <button class="btn-small" onclick="simulateIntervention('add_alirocumab_75mg')">PCSK9i</button>
    </div>
    <div id="twin-showdown" style="margin-top:16px; display:none;"></div>
  </div>

</div><!-- /page -->

<script>
// ── Live clock ───────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  document.getElementById('clock').textContent = now.toLocaleString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  });
}
updateClock();
setInterval(updateClock, 1000);

// ── Oracle badge helper ──────────────────────────────────────
function setOracleBadge(pathway) {
  const el = document.getElementById('oracle-badge');
  const map = {
    'O-CLEAR':   ['pill-green',  '● O-CLEAR'],
    'O-MONITOR': ['pill-amber',  '● O-MONITOR'],
    'O-URGENT':  ['pill-amber',  '▲ O-URGENT'],
    'O-911':     ['pill-red',    '⚠ O-911'],
  };
  const [cls, label] = map[pathway] || ['pill-muted', '○ ' + (pathway || 'Unknown')];
  el.className = 'pill ' + cls;
  el.innerHTML = '<span class="dot"></span> ' + label;
}

// ── Fetch council ─────────────────────────────────────────────
const AGENT_ICONS = {
  helen:     '🧬', cormac: '🫀', maxwell: '🧠', sherlock: '💊',
  sebastian: '😴', atlas:  '💪', nikolai: '🔬', iris: '👁',
  ada:       '📊', theodore: '🍽', bartholomew: '🫁', reginald: '🦷',
  oracle:    '🔮',
};

async function loadCouncil() {
  try {
    const resp = await fetch('/api/health/council');
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const data = await resp.json();

    // Oracle pathway
    if (data.oracle_pathway) setOracleBadge(data.oracle_pathway);
    else if (data.status === 'generating') setOracleBadge('O-MONITOR');

    // Last council timestamp
    if (data.generated_at) {
      const d = new Date(data.generated_at);
      document.getElementById('last-council').textContent = d.toLocaleString('en-US', {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
      });
    }

    // Completeness
    if (data.completeness_score != null) {
      const score = data.completeness_score;
      const letter = score >= 90 ? 'A' : score >= 80 ? 'B' : score >= 70 ? 'B-' : score >= 60 ? 'C' : 'D';
      document.getElementById('completeness').textContent = score + '/100 — ' + letter;
    }

    // Day type
    if (data.day_type) {
      const dayBadge = document.getElementById('day-type-badge');
      const dayMap = { Push: 'pill-blue', Maintain: 'pill-green', Recovery: 'pill-amber', 'Medical Attention': 'pill-red' };
      dayBadge.className = 'pill ' + (dayMap[data.day_type] || 'pill-muted');
      dayBadge.textContent = data.day_type;
      dayBadge.style.display = '';
    }

    // Three moves
    if (data.three_moves && data.three_moves.length) {
      const ul = document.getElementById('three-moves');
      ul.innerHTML = data.three_moves.map(m =>
        '<li><span>' + escHtml(m) + '</span></li>'
      ).join('');
    }

    // Council member list
    if (data.status === 'generating') {
      document.getElementById('council-list').innerHTML =
        '<li style="padding:12px 0;color:var(--muted);font-style:italic;">Council analysis in progress — check back in ~2 minutes. <a href="#" onclick="loadCouncil();return false;" style="color:var(--blue)">Refresh</a></li>';
      return;
    }

    const agents = data.agents || data.members || [];
    if (agents.length) {
      document.getElementById('council-list').innerHTML = agents.map(a => {
        const icon = AGENT_ICONS[a.agent_id] || AGENT_ICONS[a.id] || '🤖';
        const name = a.agent_name || a.name || a.agent_id || 'Agent';
        const title = a.title || a.domain || '';
        const headline = a.headline || a.summary || '';
        const body = a.assessment || a.full_text || a.detail || '';
        return `<li class="council-item" onclick="this.classList.toggle('open')">
          <div class="council-header">
            <div class="council-avatar">${icon}</div>
            <div>
              <div class="council-name">${escHtml(name)}</div>
              <div class="council-title">${escHtml(title)}</div>
            </div>
            <div class="council-headline">${escHtml(headline)}</div>
            <span class="council-chevron">▶</span>
          </div>
          <div class="council-body">${escHtml(body || headline)}</div>
        </li>`;
      }).join('');
    } else {
      document.getElementById('council-list').innerHTML =
        '<li style="padding:12px 0;color:var(--muted);font-style:italic;">No council data. Click Refresh to run analysis.</li>';
    }

    // Live metrics from council context if available
    if (data.context) {
      const ctx = data.context;
      if (ctx.weight)  setMetric('m-weight', ctx.weight, 'm-weight-sub', 'Today · Health DB');
      if (ctx.bmi)     setMetric('m-bmi', ctx.bmi.toFixed(1));
      if (ctx.hrv)     setMetric('m-hrv', ctx.hrv);
      if (ctx.steps)   setMetric('m-steps', Number(ctx.steps).toLocaleString());
    }

  } catch (err) {
    console.warn('Council fetch failed:', err);
    setOracleBadge('O-MONITOR');
    document.getElementById('council-list').innerHTML =
      '<li style="padding:12px 0;color:var(--muted);font-style:italic;">Could not reach council endpoint. ' + err.message + '</li>';
  }
}

async function refreshCouncil() {
  document.getElementById('council-list').innerHTML =
    '<li style="padding:12px 0;color:var(--muted);font-style:italic;">Triggering refresh… this takes ~90 seconds.</li>';
  try {
    await fetch('/api/health/council/refresh', { method: 'POST' });
    setTimeout(loadCouncil, 5000);
  } catch (e) {
    console.warn('Refresh failed:', e);
    loadCouncil();
  }
}

// ── Fetch drift ──────────────────────────────────────────────
async function loadDrift() {
  const container = document.getElementById('drift-container');
  try {
    const resp = await fetch('/api/health/drift/scan');
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const data = await resp.json();

    const clusters = data.active_clusters || data.clusters || [];
    const active   = clusters.filter(c => c.active || c.status === 'active');

    if (!active.length) {
      container.innerHTML = '<span id="drift-empty" style="color:var(--green);font-size:13px;">✓ No active drift detected</span>';
      return;
    }

    const severityClass = { critical: 'pill-red', high: 'pill-amber', moderate: 'pill-amber', low: 'pill-muted' };
    container.innerHTML = active.map(c => {
      const sev = (c.severity || 'moderate').toLowerCase();
      const cls = severityClass[sev] || 'pill-muted';
      const name = c.cluster_name || c.name || c.id || 'Drift';
      return `<span class="pill ${cls}"><span class="dot"></span>${escHtml(name)}</span>`;
    }).join('');

    if (data.alerts && data.alerts.length) {
      const alertDiv = document.createElement('div');
      alertDiv.style.cssText = 'width:100%;margin-top:12px;font-size:12px;color:var(--muted)';
      alertDiv.textContent = data.alerts[0];
      container.appendChild(alertDiv);
    }

  } catch (err) {
    console.warn('Drift fetch failed:', err);
    container.innerHTML = '<span class="loading">Drift data unavailable</span>';
  }
}

// ── Fetch medications ────────────────────────────────────────
async function loadMedications() {
  const container = document.getElementById('med-container');
  try {
    const resp = await fetch('/api/health/medication/list');
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const data = await resp.json();
    const meds  = data.medications || [];

    // Also grab safety flags
    let safetyFlags = {};
    try {
      const sr = await fetch('/api/health/medication/safety');
      if (sr.ok) {
        const sd = await sr.json();
        if (sd.oracle_risk) {
          const riskBadge = document.createElement('div');
          riskBadge.style.cssText = 'margin-bottom:12px';
          const riskClass = sd.oracle_risk === 'O-CLEAR' ? 'pill-green' : 'pill-red';
          riskBadge.innerHTML = `<span class="pill ${riskClass}"><span class="dot"></span> ${escHtml(sd.oracle_risk)}</span>`;
          if (sd.serious_count) {
            riskBadge.innerHTML += ` <span style="font-size:12px;color:var(--red);margin-left:8px;">⚠ ${sd.serious_count} serious interaction(s)</span>`;
          }
          container.innerHTML = '';
          container.appendChild(riskBadge);
        }
      }
    } catch(e) { /* silent */ }

    if (!meds.length) {
      container.innerHTML += '<span class="loading">No medications on file</span>';
      return;
    }

    const table = document.createElement('div');
    table.innerHTML = `<table class="med-table">
      <thead><tr>
        <th>Medication</th><th>Dose</th><th>Indication</th><th>Risk</th>
      </tr></thead>
      <tbody>${meds.map(m => {
        const risk = m.risk_level || m.risk || '';
        const riskClass = risk === 'high' ? 'red' : risk === 'moderate' ? 'amber' : '';
        const flags = m.flags || m.warnings || [];
        return `<tr>
          <td><strong>${escHtml(m.name || m.drug_name || '')}</strong>
            ${flags.map(f => `<span class="flag">⚠ ${escHtml(f)}</span>`).join('')}
          </td>
          <td>${escHtml(m.dose || m.dosage || '—')}</td>
          <td>${escHtml(m.indication || m.reason || '—')}</td>
          <td class="${riskClass}">${escHtml(risk || '—')}</td>
        </tr>`;
      }).join('')}</tbody>
    </table>`;
    container.appendChild(table);

  } catch (err) {
    console.warn('Medication fetch failed:', err);
    container.innerHTML = renderFallbackMeds();
  }
}

function renderFallbackMeds() {
  const fallback = [
    { name: 'Semaglutide (Ozempic)', dose: '1 mg/wk SQ', indication: 'T2DM / weight', risk: 'low' },
    { name: 'Metformin',             dose: '1000 mg BID', indication: 'T2DM',          risk: 'low' },
    { name: 'Lisinopril',            dose: '10 mg QD',    indication: 'HTN / CKD',     risk: 'low' },
    { name: 'Atorvastatin',          dose: '40 mg QD',    indication: 'LDL ↑',         risk: 'low' },
  ];
  return `<table class="med-table">
    <thead><tr><th>Medication</th><th>Dose</th><th>Indication</th><th>Risk</th></tr></thead>
    <tbody>${fallback.map(m =>
      `<tr>
        <td><strong>${m.name}</strong></td>
        <td>${m.dose}</td>
        <td>${m.indication}</td>
        <td>${m.risk}</td>
      </tr>`
    ).join('')}</tbody>
  </table>
  <div style="margin-top:8px;font-size:11px;color:var(--muted);font-style:italic">Cached data — live endpoint unavailable</div>`;
}

// ── Fetch live health metrics ────────────────────────────────
async function loadMetrics() {
  try {
    const resp = await fetch('/api/health/latest');
    if (!resp.ok) return;
    const data = await resp.json();
    const m = data.metrics || data;
    if (m.weight)      setMetric('m-weight', m.weight.toFixed(1), 'm-weight-sub', 'Today · Health DB');
    if (m.bmi)         setMetric('m-bmi', m.bmi.toFixed(1));
    if (m.hrv)         setMetric('m-hrv', Math.round(m.hrv));
    if (m.steps)       setMetric('m-steps', Number(m.steps).toLocaleString());
    if (m.resting_hr)  { /* could add HR tile */ }
  } catch (e) { /* silent — tiles stay at defaults */ }
}

function setMetric(id, val, subId, subText) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
  if (subId && subText) {
    const sub = document.getElementById(subId);
    if (sub) sub.textContent = subText;
  }
}

// ── Sparklines ───────────────────────────────────────────────
const LAB_DATA = {
  'A1c': {
    points: [{y:10.2,x:'2021'},{y:7.1,x:'mid-21'},{y:6.3,x:'2023'},{y:5.9,x:'2024'},{y:7.3,x:'2025'},{y:7.3,x:'2026'}],
    unit: '%', latest: '7.3', color: '#d29922',
    ref: 'Target <7.0',
  },
  'LDL': {
    points: [{y:99,x:'2021'},{y:138,x:'2024'},{y:146,x:'2025'},{y:156,x:'2026'}],
    unit: 'mg/dL', latest: '156', color: '#f85149',
    ref: 'Target <100',
  },
  'eGFR': {
    points: [{y:98,x:'2020'},{y:87,x:'2026'}],
    unit: 'mL/min', latest: '87', color: '#d29922',
    ref: 'Stage 2 CKD',
  },
  'K+': {
    points: [{y:5.4,x:'2025'},{y:4.5,x:'2026'}],
    unit: 'mEq/L', latest: '4.5', color: '#3fb950',
    ref: 'Normal range 3.5–5.0',
  },
};

function buildSparkline(points, color) {
  if (points.length < 2) {
    // Single point — just a dot
    return `<svg class="sparkline" viewBox="0 0 200 50" preserveAspectRatio="none">
      <circle cx="100" cy="25" r="4" fill="${color}"/>
    </svg>`;
  }
  const vals = points.map(p => p.y);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const W = 200, H = 50, PAD = 6;

  const coords = points.map((p, i) => {
    const x = PAD + (i / (points.length - 1)) * (W - PAD * 2);
    const y = H - PAD - ((p.y - min) / range) * (H - PAD * 2);
    return [x, y];
  });

  const path = coords.map((c, i) => (i === 0 ? `M${c[0]},${c[1]}` : `L${c[0]},${c[1]}`)).join(' ');
  const area = `${path} L${coords[coords.length-1][0]},${H} L${coords[0][0]},${H} Z`;

  // Year labels
  const labels = points.map((p, i) => {
    const [x, y] = coords[i];
    return `<text x="${x}" y="${H - 1}" text-anchor="middle" font-size="7" fill="#8b949e">${p.x}</text>`;
  }).join('');

  const lastDot = coords[coords.length - 1];

  return `<svg class="sparkline" viewBox="0 0 ${W} ${H + 10}" preserveAspectRatio="none">
    <defs>
      <linearGradient id="sg${color.replace('#','')}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${color}" stop-opacity=".25"/>
        <stop offset="100%" stop-color="${color}" stop-opacity=".02"/>
      </linearGradient>
    </defs>
    <path d="${area}" fill="url(#sg${color.replace('#','')})" />
    <path d="${path}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round"/>
    <circle cx="${lastDot[0]}" cy="${lastDot[1]}" r="3.5" fill="${color}"/>
    ${labels}
  </svg>`;
}

function renderSparklines() {
  const container = document.getElementById('sparklines');
  container.innerHTML = Object.entries(LAB_DATA).map(([name, d]) => `
    <div class="sparkline-card">
      <div class="spark-label">${name}</div>
      <div class="spark-sub">${d.ref}</div>
      <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:10px">
        <span class="spark-latest" style="color:${d.color}">${d.latest}</span>
        <span style="font-size:12px;color:var(--muted)">${d.unit}</span>
      </div>
      ${buildSparkline(d.points, d.color)}
    </div>
  `).join('');
}

// Digital Twin
async function loadTwinProjections() {
  try {
    const r = await fetch('/api/health/twin/project?months=12');
    const data = await r.json();
    renderTwinGrid(data.projections || []);
  } catch(e) {
    document.getElementById('twin-grid').innerHTML = '<div class="twin-loading">Twin unavailable</div>';
  }
}

function renderTwinGrid(projections) {
  const grid = document.getElementById('twin-grid');
  if (!projections.length) { grid.innerHTML = '<div class="twin-loading">No projections available — run calibration</div>'; return; }

  const directionIcon = (d) => d === 'improving' ? '↗' : d === 'worsening' ? '↘' : d === 'volatile' ? '↕' : '→';
  const directionClass = (p) => p.on_track_to_goal ? 'twin-track-good' : p.direction === 'worsening' ? 'twin-track-bad' : p.direction === 'stable' ? 'twin-stable' : 'twin-track-ok';

  grid.innerHTML = projections.map(p => `
    <div class="twin-metric">
      <div class="twin-metric-name">${p.metric.replace(/_/g,' ')}</div>
      <div class="twin-current">Now: ${p.current_value} ${p.unit}</div>
      <div class="twin-projected ${directionClass(p)}">${p.projected_value?.toFixed(1)} ${p.unit}</div>
      <div class="twin-ci">80% CI: ${p.ci_low?.toFixed(1)} – ${p.ci_high?.toFixed(1)}</div>
      <div class="twin-direction ${directionClass(p)}">${directionIcon(p.direction)} ${p.direction}${p.at_goal ? ' ✓ at goal' : p.goal_value ? ` (goal: ${p.goal_value})` : ''}</div>
    </div>
  `).join('');
}

async function runLDLShowdown() {
  const el = document.getElementById('twin-showdown');
  el.style.display = 'block';
  el.innerHTML = '<div class="twin-loading">Running LDL showdown…</div>';
  try {
    const r = await fetch('/api/health/twin/ldl-showdown');
    const data = await r.json();
    renderShowdown(data, el);
  } catch(e) { el.innerHTML = '<div class="twin-loading">Showdown failed</div>'; }
}

async function simulateIntervention(interventionStr) {
  const el = document.getElementById('twin-showdown');
  el.style.display = 'block';
  el.innerHTML = '<div class="twin-loading">Simulating…</div>';
  try {
    const interventions = interventionStr.split(',');
    const r = await fetch('/api/health/twin/simulate', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({interventions, timeframe_months: 12})
    });
    const data = await r.json();
    renderSimulation(data, el);
  } catch(e) { el.innerHTML = '<div class="twin-loading">Simulation failed</div>'; }
}

function renderShowdown(data, el) {
  const rows = (data.strategies || []).map(s => `
    <tr>
      <td>${s.strategy}</td>
      <td>${s.projected_ldl} mg/dL</td>
      <td>${s.ldl_reduction}</td>
      <td>${s.ascvd_delta}</td>
      <td>${s.evidence_grade}</td>
    </tr>
  `).join('');
  el.innerHTML = `
    <div style="font-size:12px;color:#8b949e;margin-bottom:8px;">LDL Strategy Comparison (12 months)</div>
    <table class="showdown-table">
      <thead><tr><th>Strategy</th><th>Projected LDL</th><th>Reduction</th><th>ASCVD Δ</th><th>Grade</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderSimulation(data, el) {
  const changed = (data.intervention_projections || []).filter(p =>
    data.baseline_projections?.find(b => b.metric === p.metric)
  );
  const rows = changed.map(p => {
    const base = data.baseline_projections?.find(b => b.metric === p.metric);
    return `<tr>
      <td>${p.metric.replace(/_/g,' ')}</td>
      <td>${base?.projected_value?.toFixed(1)} ${p.unit}</td>
      <td><strong>${p.projected_value?.toFixed(1)} ${p.unit}</strong></td>
      <td>${p.on_track_to_goal ? '<span style="color:#3fb950">✓ On track</span>' : '<span style="color:#d29922">—</span>'}</td>
    </tr>`;
  }).join('');
  const flags = (data.safety_flags || []).map(f => `<li style="color:#f85149">${f}</li>`).join('');
  el.innerHTML = `
    <div style="font-size:12px;color:#8b949e;margin-bottom:8px;">
      Intervention: ${(data.interventions_applied||[]).join(' + ')} | ASCVD Δ: ${data.net_ascvd_delta_pct > 0 ? '+' : ''}${data.net_ascvd_delta_pct?.toFixed(1)}%
    </div>
    <table class="showdown-table">
      <thead><tr><th>Metric</th><th>Baseline (12mo)</th><th>With Intervention</th><th>Status</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    ${flags ? `<ul style="margin-top:8px;padding-left:16px;font-size:11px;">${flags}</ul>` : ''}
  `;
}

// ── Longevity Projection ─────────────────────────────────────
async function loadLongevity() {
  const el = document.getElementById('longevity-content');
  try {
    const [estRes, trajRes] = await Promise.all([
      fetch('/api/health/longevity/estimate'),
      fetch('/api/health/longevity/trajectory'),
    ]);
    const est  = await estRes.json();
    const traj = await trajRes.json();
    renderLongevity(est, traj, el);
  } catch(e) {
    el.innerHTML = '<div class="lon-loading">Longevity estimate unavailable</div>';
  }
}

function renderLongevity(est, traj, el) {
  const le   = est.estimated_life_expectancy;
  const rem  = est.years_remaining;
  const opt  = est.optimized_life_expectancy;
  const gain = est.optimized_gain_years;
  const dir  = est.trajectory_direction;
  const numClass = dir === 'improving' ? 'green' : dir === 'declining' ? 'red' : 'amber';

  // Build SVG trajectory graph
  const svgHtml = buildLongevityGraph(traj, le, est);

  // Separate risk adjustments
  const neg = (est.risk_adjustments || []).filter(a => a.adjustment_years < 0)
                .sort((a,b) => a.adjustment_years - b.adjustment_years);
  const pos = (est.risk_adjustments || []).filter(a => a.adjustment_years > 0)
                .sort((a,b) => b.adjustment_years - a.adjustment_years);

  const negRows = neg.map(a => `
    <div class="lon-factor-row">
      <span class="lon-factor-name">${escHtml(a.factor)}</span>
      <span class="lon-factor-val neg">${a.adjustment_years} yr</span>
    </div>`).join('');

  const posRows = pos.map(a => `
    <div class="lon-factor-row">
      <span class="lon-factor-name">${escHtml(a.factor)}</span>
      <span class="lon-factor-val pos">+${a.adjustment_years} yr</span>
    </div>`).join('');

  const modifiable = (est.modifiable_years_at_stake || 0);

  el.innerHTML = `
    <div class="longevity-hero">
      <div class="longevity-main">
        <div class="longevity-number ${numClass}">${le}</div>
        <div class="longevity-label">Estimated Life Expectancy</div>
        <div class="longevity-remaining">${rem} years remaining</div>
        <div class="longevity-ci">80% CI: ${est.ci_lower} – ${est.ci_upper}</div>
      </div>
      <div class="longevity-optimized">
        <div class="longevity-opt-label">Optimized Upside</div>
        <div class="longevity-opt-num">${opt}</div>
        <div class="longevity-opt-gain">+${gain} years possible</div>
        <div style="font-size:11px;color:#8b949e;margin-top:6px;">CPAP + ezetimibe + A1c control</div>
      </div>
    </div>

    <div class="longevity-graph">${svgHtml}</div>

    <div class="longevity-factors">
      <div>
        <div class="lon-factor-title neg">▼ Dragging You Down</div>
        ${negRows}
      </div>
      <div>
        <div class="lon-factor-title pos">▲ Working For You</div>
        ${posRows}
      </div>
    </div>

    ${modifiable > 0 ? `
    <div class="lon-modifiable">
      ⚡ ${modifiable} modifiable years at stake — these are recoverable with targeted interventions
    </div>` : ''}
  `;
}

function buildLongevityGraph(history, currentLE, est) {
  // All data points: history (2021-2026) + projections (2026-2031)
  const W = 600, H = 200;
  const PAD = { top: 24, right: 20, bottom: 36, left: 36 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top  - PAD.bottom;

  // Current + optimized trajectories hardcoded (from longevity_calculator)
  const currentPath = [
    {year: 2026.4, age: currentLE},
    {year: 2027.4, age: currentLE - 1},
    {year: 2028.4, age: currentLE - 1},
    {year: 2029.4, age: currentLE - 2},
    {year: 2030.4, age: currentLE - 2},
    {year: 2031.4, age: currentLE - 3},
  ];
  const optPath = [
    {year: 2026.4, age: currentLE},
    {year: 2027.4, age: currentLE + 1},
    {year: 2028.4, age: currentLE + 2},
    {year: 2029.4, age: currentLE + 3},
    {year: 2030.4, age: currentLE + 4},
    {year: 2031.4, age: currentLE + 5},
  ];

  // Parse history dates → decimal years
  const histPts = history.map(h => {
    const [yr, mo] = h.date.split('-').map(Number);
    return { year: yr + (mo - 1) / 12, age: h.estimated_age, note: h.note };
  });

  const allYears = [...histPts.map(p=>p.year), ...currentPath.map(p=>p.year), ...optPath.map(p=>p.year)];
  const allAges  = [...histPts.map(p=>p.age),  ...currentPath.map(p=>p.age), ...optPath.map(p=>p.age)];
  const minY = 2021, maxY = 2031.5;
  const minA = Math.min(...allAges) - 2, maxA = Math.max(...allAges) + 2;

  const xScale = y => PAD.left + (y - minY) / (maxY - minY) * plotW;
  const yScale = a => PAD.top  + (1 - (a - minA) / (maxA - minA)) * plotH;

  const pointsToPath = pts => pts.map((p,i) =>
    `${i===0?'M':'L'}${xScale(p.year).toFixed(1)},${yScale(p.age).toFixed(1)}`).join(' ');

  // Grid lines at ages 70, 75, 80
  const gridAges = [70, 75, 80];
  const gridLines = gridAges.map(a => {
    const y = yScale(a).toFixed(1);
    return `<line x1="${PAD.left}" y1="${y}" x2="${W - PAD.right}" y2="${y}" stroke="#30363d" stroke-width="1"/>
            <text x="${PAD.left - 4}" y="${(parseFloat(y)+4).toFixed(0)}" fill="#8b949e" font-size="9" text-anchor="end">${a}</text>`;
  }).join('');

  // Year labels on x-axis
  const xLabels = [2021, 2023, 2025, 2026, 2028, 2031].map(yr => {
    const x = xScale(yr).toFixed(1);
    return `<text x="${x}" y="${H - PAD.bottom + 16}" fill="#8b949e" font-size="9" text-anchor="middle">${yr}</text>`;
  }).join('');

  // Today divider line
  const todayX = xScale(2026.4).toFixed(1);

  // Reference lines: current LE and actuarial
  const leY = yScale(currentLE).toFixed(1);
  const actY = yScale(80.5).toFixed(1);

  // Dots on historical line
  const dots = histPts.map(p =>
    `<circle cx="${xScale(p.year).toFixed(1)}" cy="${yScale(p.age).toFixed(1)}" r="4.5" fill="#3fb950" stroke="#0d1117" stroke-width="1.5"/>`
  ).join('');

  // Legend
  const legend = `
    <rect x="${PAD.left}" y="6" width="10" height="3" rx="1.5" fill="#3fb950"/>
    <text x="${PAD.left + 14}" y="11" fill="#8b949e" font-size="9">Historical</text>
    <rect x="${PAD.left + 72}" y="6" width="10" height="2" rx="1" fill="#d29922" stroke-dasharray="3,2"/>
    <text x="${PAD.left + 86}" y="11" fill="#8b949e" font-size="9">Current path</text>
    <rect x="${PAD.left + 168}" y="6" width="10" height="2" rx="1" fill="#58a6ff"/>
    <text x="${PAD.left + 182}" y="11" fill="#8b949e" font-size="9">Optimized</text>`;

  return `<svg viewBox="0 0 ${W} ${H}" width="100%" style="display:block;" xmlns="http://www.w3.org/2000/svg">
    ${gridLines}
    ${xLabels}

    <!-- Today divider -->
    <line x1="${todayX}" y1="${PAD.top}" x2="${todayX}" y2="${H - PAD.bottom}" stroke="#30363d" stroke-width="1" stroke-dasharray="4,3"/>
    <text x="${parseFloat(todayX)+3}" y="${PAD.top + 10}" fill="#8b949e" font-size="8">TODAY</text>

    <!-- Actuarial reference -->
    <line x1="${PAD.left}" y1="${actY}" x2="${W - PAD.right}" y2="${actY}" stroke="#30363d" stroke-width="1" stroke-dasharray="2,4"/>
    <text x="${W - PAD.right + 2}" y="${parseFloat(actY)+3}" fill="#8b949e" font-size="8">80.5</text>

    <!-- Current trajectory (dashed amber) -->
    <path d="${pointsToPath(currentPath)}" fill="none" stroke="#d29922" stroke-width="2" stroke-dasharray="6,3" opacity="0.8"/>

    <!-- Optimized trajectory (dashed blue) -->
    <path d="${pointsToPath(optPath)}" fill="none" stroke="#58a6ff" stroke-width="2" stroke-dasharray="6,3" opacity="0.8"/>

    <!-- Historical line (solid green) -->
    <path d="${pointsToPath(histPts)}" fill="none" stroke="#3fb950" stroke-width="2.5"/>
    ${dots}

    ${legend}
  </svg>`;
}

// Load twin on page load
loadTwinProjections();

// ── Utility ──────────────────────────────────────────────────
function escHtml(s) {
  if (!s) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Boot ─────────────────────────────────────────────────────
async function boot() {
  renderSparklines();
  await Promise.allSettled([
    loadCouncil(),
    loadDrift(),
    loadMedications(),
    loadMetrics(),
    loadLongevity(),
  ]);
}

boot();

// Auto-refresh every 5 minutes
setInterval(() => {
  loadCouncil();
  loadDrift();
  loadMedications();
  loadMetrics();
  loadTwinProjections();
  loadLongevity();
}, 5 * 60 * 1000);
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# FastAPI route
# ---------------------------------------------------------------------------

def get_dashboard_route():
    """Return the FastAPI async route handler for GET /health-dashboard."""
    from fastapi.responses import HTMLResponse

    async def dashboard():
        return HTMLResponse(content=get_dashboard_html())

    return dashboard


def register_routes(app) -> None:
    """Register the health dashboard route on an existing FastAPI app."""
    app.get(
        "/health-dashboard",
        tags=["health"],
        summary="JARVIS Health Dashboard",
        response_class=None,   # HTMLResponse returned directly
        include_in_schema=True,
    )(get_dashboard_route())
