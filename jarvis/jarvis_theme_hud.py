"""JARVIS HUD — the cinematic, living interface.

One full-viewport stage instead of a gallery of dashboard pages:
conversation at the center, a breathing arc-reactor core that reflects
Jarvis's real state, and mission/approval/agent panels that materialize
around the dialogue. Every readout is wired to a live endpoint — the
core pulses amber only when something genuinely needs Chris, the agent
constellation lights only on real events, and the model name shown is
whatever actually answered. Nothing is simulated.

Implementation notes:
- Plain string template with __TOKEN__ substitution, deliberately NOT an
  f-string: this codebase has a documented history of f-string escape
  sequences (\\n, \\') and brace-doubling corrupting embedded JS.
- Self-contained: no external fonts/CDNs beyond what the shell already
  allows; all CSS/JS inline (the page is small, unlike the Glass shell).
"""

from __future__ import annotations


def render_hud_shell(runtime, initial_packet: str = "") -> str:
    try:
        user_name = runtime.config.your_name or "Chris"
    except Exception:
        user_name = "Chris"
    html = _HUD_TEMPLATE.replace("__USER_NAME__", user_name)
    return html


_HUD_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>JARVIS</title>
<link rel="icon" href="data:,">
<style>
  :root {
    --void: #030810;
    --void-2: #060d1a;
    --panel: rgba(10, 20, 35, 0.55);
    --panel-solid: rgba(8, 16, 28, 0.92);
    --stroke: rgba(94, 234, 212, 0.16);
    --stroke-bright: rgba(94, 234, 212, 0.45);
    --cyan: #22d3ee;
    --cyan-soft: #67e8f9;
    --teal: #5eead4;
    --amber: #fbbf24;
    --red: #fb7185;
    --green: #4ade80;
    --text: #e6f5f8;
    --text-dim: #7d99ad;
    --text-mono: #9adbe8;
    --mono: "SF Mono", "JetBrains Mono", "Fira Code", ui-monospace, monospace;
    --sans: "SF Pro Display", "Inter", "Segoe UI", system-ui, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; }
  body {
    background: var(--void);
    color: var(--text);
    font-family: var(--sans);
    overflow: hidden;
    -webkit-font-smoothing: antialiased;
  }

  /* ── Deep space backdrop ─────────────────────────────────────────── */
  .backdrop {
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background:
      radial-gradient(ellipse 60% 40% at 50% -5%, rgba(34, 211, 238, 0.09), transparent 60%),
      radial-gradient(ellipse 40% 30% at 85% 100%, rgba(94, 234, 212, 0.05), transparent 60%),
      linear-gradient(180deg, var(--void) 0%, var(--void-2) 50%, var(--void) 100%);
  }
  .backdrop::before {
    content: ""; position: absolute; inset: -1px;
    background-image:
      linear-gradient(rgba(94, 234, 212, 0.025) 1px, transparent 1px),
      linear-gradient(90deg, rgba(94, 234, 212, 0.025) 1px, transparent 1px);
    background-size: 56px 56px;
    mask-image: radial-gradient(ellipse 90% 70% at 50% 40%, black 30%, transparent 75%);
    animation: gridDrift 60s linear infinite;
  }
  @keyframes gridDrift { from { background-position: 0 0, 0 0; } to { background-position: 0 56px, 56px 0; } }

  /* ── Boot sequence ───────────────────────────────────────────────── */
  #boot {
    position: fixed; inset: 0; z-index: 100;
    background: var(--void);
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 26px; transition: opacity 0.6s ease;
  }
  #boot.done { opacity: 0; pointer-events: none; }
  #boot .boot-title {
    font-family: var(--mono); font-size: 13px; letter-spacing: 1.1em; padding-left: 1.1em;
    color: var(--cyan-soft); opacity: 0; animation: bootFade 0.8s ease 0.3s forwards;
  }
  #boot .boot-lines { font-family: var(--mono); font-size: 11px; color: var(--text-dim); min-height: 54px; text-align: center; line-height: 1.9; letter-spacing: 0.12em; }
  #boot .boot-lines div { opacity: 0; animation: bootFade 0.4s ease forwards; }
  @keyframes bootFade { to { opacity: 1; } }

  /* ── The Core (arc reactor) ──────────────────────────────────────── */
  .core-wrap { position: relative; width: 120px; height: 120px; flex: none; }
  .core-wrap svg { position: absolute; inset: 0; overflow: visible; }
  .core-ring { fill: none; stroke-linecap: round; transform-origin: 60px 60px; }
  .ring-a { stroke: var(--cyan); stroke-width: 1.6; animation: spin 14s linear infinite; }
  .ring-b { stroke: var(--teal); stroke-width: 1.1; animation: spinRev 22s linear infinite; opacity: 0.75; }
  .ring-c { stroke: var(--cyan-soft); stroke-width: 0.8; animation: spin 36s linear infinite; opacity: 0.45; }
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes spinRev { to { transform: rotate(-360deg); } }
  .core-orb {
    position: absolute; inset: 34px; border-radius: 50%;
    background: radial-gradient(circle at 42% 38%, rgba(165, 243, 252, 0.95), rgba(34, 211, 238, 0.55) 45%, rgba(8, 47, 73, 0.9) 100%);
    box-shadow: 0 0 24px rgba(34, 211, 238, 0.55), 0 0 80px rgba(34, 211, 238, 0.22), inset 0 0 18px rgba(3, 8, 16, 0.55);
    animation: breathe 4.2s ease-in-out infinite;
  }
  @keyframes breathe { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.06); } }

  .hud[data-state="thinking"] .ring-a { animation-duration: 2.4s; }
  .hud[data-state="thinking"] .ring-b { animation-duration: 3.6s; }
  .hud[data-state="thinking"] .core-orb { animation-duration: 1.4s; box-shadow: 0 0 34px rgba(34, 211, 238, 0.85), 0 0 110px rgba(34, 211, 238, 0.35), inset 0 0 18px rgba(3, 8, 16, 0.5); }
  .hud[data-state="attention"] .core-orb {
    background: radial-gradient(circle at 42% 38%, rgba(254, 240, 199, 0.95), rgba(251, 191, 36, 0.6) 45%, rgba(74, 44, 6, 0.9) 100%);
    box-shadow: 0 0 26px rgba(251, 191, 36, 0.6), 0 0 90px rgba(251, 191, 36, 0.22), inset 0 0 18px rgba(20, 10, 2, 0.55);
  }
  .hud[data-state="attention"] .ring-a { stroke: var(--amber); }

  /* ── Stage layout ────────────────────────────────────────────────── */
  .hud {
    position: relative; z-index: 1;
    display: grid; height: 100vh; height: 100dvh;
    grid-template-columns: 320px minmax(0, 1fr) 320px;
    grid-template-rows: 52px minmax(0, 1fr);
    grid-template-areas: "top top top" "left stage right";
    gap: 0 18px; padding: 0 18px 0;
  }

  /* ── Top strip ───────────────────────────────────────────────────── */
  .topstrip {
    grid-area: top; display: flex; align-items: center; justify-content: space-between;
    font-family: var(--mono); font-size: 11px; letter-spacing: 0.14em;
    color: var(--text-dim); border-bottom: 1px solid rgba(94, 234, 212, 0.08);
  }
  .topstrip .wordmark { color: var(--cyan-soft); letter-spacing: 0.5em; font-weight: 600; }
  .topstrip .readouts { display: flex; align-items: center; gap: 22px; }
  .topstrip .readouts a { color: var(--text-dim); text-decoration: none; transition: color 0.2s; }
  .topstrip .readouts a:hover { color: var(--cyan-soft); }
  .topnav { display: flex; align-items: center; gap: 16px; padding-left: 16px; border-left: 1px solid rgba(94, 234, 212, 0.14); }
  .badge-attn { color: var(--amber); }
  .dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--green); margin-right: 6px; vertical-align: 1px; box-shadow: 0 0 6px var(--green); }

  /* ── Docks (side panels) ─────────────────────────────────────────── */
  .dock { grid-area: left; overflow-y: auto; padding: 20px 2px 110px; scrollbar-width: none; }
  .dock::-webkit-scrollbar { display: none; }
  .dock.right { grid-area: right; }
  .card {
    position: relative; background: var(--panel); border: 1px solid var(--stroke);
    border-radius: 4px; padding: 16px 16px 14px; margin-bottom: 16px;
    backdrop-filter: blur(14px); opacity: 0; transform: translateY(10px);
    animation: materialize 0.6s ease forwards;
  }
  .card:nth-child(2) { animation-delay: 0.12s; }
  .card:nth-child(3) { animation-delay: 0.24s; }
  @keyframes materialize { to { opacity: 1; transform: none; } }
  /* sci-fi corner brackets */
  .card::before, .card::after {
    content: ""; position: absolute; width: 14px; height: 14px; pointer-events: none;
    border-color: var(--stroke-bright); border-style: solid;
  }
  .card::before { top: -1px; left: -1px; border-width: 1.5px 0 0 1.5px; }
  .card::after { bottom: -1px; right: -1px; border-width: 0 1.5px 1.5px 0; }
  .card h3 {
    font-family: var(--mono); font-size: 10px; font-weight: 600;
    letter-spacing: 0.28em; color: var(--text-mono); text-transform: uppercase;
    margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;
  }
  .card h3 .count { color: var(--cyan); }
  .card h3 .count.warn { color: var(--amber); }

  .row { padding: 9px 0; border-top: 1px solid rgba(125, 153, 173, 0.1); font-size: 13px; }
  .row:first-of-type { border-top: none; }
  .row .r-title { color: var(--text); line-height: 1.35; margin-bottom: 3px; }
  .row .r-meta { font-family: var(--mono); font-size: 10px; letter-spacing: 0.1em; color: var(--text-dim); text-transform: uppercase; }
  .row .r-meta.crit { color: var(--red); }
  .row .r-meta.high { color: var(--amber); }
  .lane-now { color: var(--green); }
  .lane-next { color: var(--cyan-soft); }
  .lane-blocked { color: var(--amber); }
  .empty-note { font-size: 12px; color: var(--text-dim); font-style: italic; padding: 6px 0; }

  .act-btns { display: flex; gap: 8px; margin-top: 8px; }
  .act-btns button {
    font-family: var(--mono); font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase;
    padding: 6px 12px; border-radius: 3px; cursor: pointer;
    border: 1px solid var(--stroke-bright); background: rgba(34, 211, 238, 0.08); color: var(--cyan-soft);
    transition: all 0.2s;
  }
  .act-btns button:hover { background: rgba(34, 211, 238, 0.2); }
  .act-btns button.deny { border-color: rgba(251, 113, 133, 0.4); background: rgba(251, 113, 133, 0.06); color: var(--red); }

  /* ── Agent constellation ─────────────────────────────────────────── */
  .constellation { position: relative; height: 190px; }
  .constellation .c-center {
    position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
    font-family: var(--mono); font-size: 9px; letter-spacing: 0.2em; color: var(--text-dim);
    text-align: center;
  }
  .agent-node { position: absolute; width: 8px; height: 8px; border-radius: 50%; transform: translate(-50%, -50%); cursor: default; }
  .agent-node .n-dot { width: 100%; height: 100%; border-radius: 50%; background: rgba(103, 232, 249, 0.35); box-shadow: 0 0 6px rgba(103, 232, 249, 0.3); transition: all 0.3s; }
  .agent-node[data-status="running"] .n-dot { background: var(--cyan); box-shadow: 0 0 10px var(--cyan); }
  .agent-node[data-status="blocked"] .n-dot { background: var(--amber); box-shadow: 0 0 8px rgba(251, 191, 36, 0.7); }
  .agent-node[data-status="error"] .n-dot { background: var(--red); box-shadow: 0 0 8px rgba(251, 113, 133, 0.7); }
  .agent-node.flash .n-dot { animation: nodeFlash 1.2s ease; }
  @keyframes nodeFlash {
    0% { transform: scale(1); box-shadow: 0 0 6px var(--cyan); }
    30% { transform: scale(2.2); box-shadow: 0 0 22px var(--cyan); background: #fff; }
    100% { transform: scale(1); }
  }
  .agent-node .n-label {
    position: absolute; top: -18px; left: 50%; transform: translateX(-50%);
    font-family: var(--mono); font-size: 8px; letter-spacing: 0.08em; color: var(--text-dim);
    white-space: nowrap; opacity: 0; transition: opacity 0.2s; pointer-events: none;
  }
  .agent-node:hover .n-label { opacity: 1; }
  .constellation svg.orbits { position: absolute; inset: 0; }
  .constellation svg.orbits circle { fill: none; stroke: rgba(94, 234, 212, 0.08); stroke-dasharray: 3 6; }

  /* ── Telemetry readout ───────────────────────────────────────────── */
  .telemetry { font-family: var(--mono); font-size: 10.5px; letter-spacing: 0.1em; line-height: 2.1; color: var(--text-dim); }
  .telemetry b { color: var(--text-mono); font-weight: 500; float: right; }

  /* ── Center stage: conversation ──────────────────────────────────── */
  .stage { grid-area: stage; display: flex; flex-direction: column; min-height: 0; position: relative; }
  .stage-head { display: flex; justify-content: center; padding: 14px 0 2px; flex: none; }
  .stream { flex: 1; overflow-y: auto; padding: 10px 8px 150px; scrollbar-width: thin; scrollbar-color: rgba(94,234,212,0.2) transparent; }

  .hello { text-align: center; margin-top: 4vh; opacity: 0; animation: materialize 0.8s ease 0.5s forwards; }
  .hello .h-greet { font-size: clamp(26px, 3.4vw, 40px); font-weight: 200; letter-spacing: -0.01em; line-height: 1.2; }
  .hello .h-greet b { font-weight: 600; color: var(--cyan-soft); }
  .hello .h-sub { margin-top: 14px; font-size: 14px; color: var(--text-dim); max-width: 560px; margin-left: auto; margin-right: auto; line-height: 1.6; }
  .hello .h-priority {
    margin: 26px auto 0; max-width: 540px; text-align: left;
    border-left: 2px solid var(--amber); padding: 10px 16px;
    background: rgba(251, 191, 36, 0.05); font-size: 13.5px; line-height: 1.55;
  }
  .hello .h-priority .p-label { font-family: var(--mono); font-size: 9px; letter-spacing: 0.3em; color: var(--amber); display: block; margin-bottom: 5px; }
  .chips { display: flex; gap: 10px; justify-content: center; margin-top: 30px; flex-wrap: wrap; }
  .chips button {
    font-family: var(--mono); font-size: 11px; letter-spacing: 0.1em;
    padding: 9px 18px; border-radius: 999px; cursor: pointer;
    border: 1px solid var(--stroke); background: transparent; color: var(--text-dim);
    transition: all 0.25s;
  }
  .chips button:hover { border-color: var(--stroke-bright); color: var(--cyan-soft); background: rgba(34, 211, 238, 0.05); }

  .msg { max-width: 720px; margin: 0 auto 22px; opacity: 0; transform: translateY(8px); animation: materialize 0.45s ease forwards; }
  .msg.you { text-align: right; }
  .msg.you .bubble {
    display: inline-block; text-align: left; font-size: 14.5px; line-height: 1.55;
    padding: 10px 16px; border-radius: 14px 14px 3px 14px;
    background: rgba(34, 211, 238, 0.1); border: 1px solid rgba(34, 211, 238, 0.18);
  }
  .msg.jarvis .who { font-family: var(--mono); font-size: 9px; letter-spacing: 0.34em; color: var(--cyan); margin-bottom: 7px; }
  .msg.jarvis .bubble {
    font-size: 15px; line-height: 1.68; color: var(--text);
    border-left: 2px solid var(--cyan); padding: 2px 0 2px 18px;
    white-space: pre-wrap; word-wrap: break-word;
  }
  .msg.jarvis .b-meta { font-family: var(--mono); font-size: 9px; letter-spacing: 0.12em; color: rgba(125, 153, 173, 0.55); margin-top: 8px; padding-left: 20px; }
  .thinking-line { max-width: 720px; margin: 0 auto 22px; }
  .thinking-line .scan {
    height: 2px; background: linear-gradient(90deg, transparent, var(--cyan), transparent);
    background-size: 200% 100%; animation: scanMove 1.4s linear infinite; border-radius: 2px; max-width: 220px;
  }
  .thinking-line .t-label { font-family: var(--mono); font-size: 9px; letter-spacing: 0.3em; color: var(--text-dim); margin-bottom: 8px; }
  @keyframes scanMove { from { background-position: 200% 0; } to { background-position: -200% 0; } }

  /* ── Composer ────────────────────────────────────────────────────── */
  .composer-wrap {
    position: absolute; left: 0; right: 0; bottom: 0; padding: 30px 8px 22px;
    background: linear-gradient(180deg, transparent, rgba(3, 8, 16, 0.85) 40%, rgba(3, 8, 16, 0.97));
    display: flex; justify-content: center; pointer-events: none;
  }
  .composer {
    pointer-events: auto; width: min(720px, 100%);
    display: flex; align-items: flex-end; gap: 10px;
    background: var(--panel-solid); border: 1px solid var(--stroke);
    border-radius: 16px; padding: 10px 10px 10px 18px;
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(34, 211, 238, 0.03);
    transition: border-color 0.3s, box-shadow 0.3s;
  }
  .composer:focus-within { border-color: var(--stroke-bright); box-shadow: 0 8px 40px rgba(0,0,0,0.5), 0 0 24px rgba(34, 211, 238, 0.08); }
  .composer textarea {
    flex: 1; background: transparent; border: none; outline: none; resize: none;
    color: var(--text); font-family: var(--sans); font-size: 15px; line-height: 1.5;
    max-height: 140px; padding: 6px 0;
  }
  .composer textarea::placeholder { color: rgba(125, 153, 173, 0.55); }
  .c-btn {
    flex: none; width: 40px; height: 40px; border-radius: 12px; cursor: pointer;
    border: 1px solid var(--stroke); background: transparent; color: var(--text-dim);
    display: flex; align-items: center; justify-content: center; font-size: 16px;
    transition: all 0.2s;
  }
  .c-btn:hover { color: var(--cyan-soft); border-color: var(--stroke-bright); }
  .c-btn.send { background: var(--cyan); color: #04222b; border: none; font-weight: 700; }
  .c-btn.send:hover { background: var(--cyan-soft); }
  .c-btn.mic.listening { color: var(--red); border-color: rgba(251, 113, 133, 0.5); animation: micPulse 1.2s ease-in-out infinite; }
  @keyframes micPulse { 50% { box-shadow: 0 0 14px rgba(251, 113, 133, 0.5); } }

  /* ── Holographic panels (summoned data / artifacts) ─────────────── */
  .veil {
    position: fixed; inset: 0; z-index: 80;
    background: rgba(2, 6, 12, 0.62); backdrop-filter: blur(6px);
    display: flex; align-items: center; justify-content: center; padding: 4vh 18px;
    opacity: 0; pointer-events: none; transition: opacity 0.25s ease;
  }
  .veil.open { opacity: 1; pointer-events: auto; }
  .holo {
    position: relative; width: min(680px, 100%); max-height: 86vh;
    display: flex; flex-direction: column;
    background: var(--panel-solid); border: 1px solid var(--stroke-bright);
    border-radius: 6px; box-shadow: 0 0 60px rgba(34, 211, 238, 0.14), 0 30px 80px rgba(0,0,0,0.6);
    transform: scale(0.94) translateY(12px); filter: blur(4px); opacity: 0;
    transition: transform 0.3s cubic-bezier(0.2, 0.9, 0.3, 1.2), filter 0.3s ease, opacity 0.3s ease;
  }
  .veil.open .holo { transform: none; filter: none; opacity: 1; }
  .holo::before, .holo::after {
    content: ""; position: absolute; width: 22px; height: 22px; pointer-events: none;
    border-color: var(--cyan); border-style: solid;
  }
  .holo::before { top: -2px; left: -2px; border-width: 2px 0 0 2px; }
  .holo::after { bottom: -2px; right: -2px; border-width: 0 2px 2px 0; }
  .holo-head {
    display: flex; align-items: flex-start; gap: 14px;
    padding: 18px 20px 14px; border-bottom: 1px solid var(--stroke); flex: none;
  }
  .holo-head .hk {
    font-family: var(--mono); font-size: 9px; letter-spacing: 0.32em;
    color: var(--cyan); text-transform: uppercase; margin-bottom: 6px;
  }
  .holo-head .ht { font-size: 17px; font-weight: 600; line-height: 1.35; }
  .holo-head .hx {
    margin-left: auto; flex: none; width: 30px; height: 30px; cursor: pointer;
    border: 1px solid var(--stroke); border-radius: 4px; background: transparent;
    color: var(--text-dim); font-size: 13px; line-height: 1;
    display: flex; align-items: center; justify-content: center; transition: all 0.2s;
  }
  .holo-head .hx:hover { color: var(--red); border-color: rgba(251, 113, 133, 0.5); }
  .holo-body { overflow-y: auto; padding: 16px 20px 20px; scrollbar-width: thin; }
  .holo-body .h-summary { font-size: 13.5px; color: var(--text-dim); line-height: 1.6; margin-bottom: 14px; }
  .holo-body .h-section {
    font-family: var(--mono); font-size: 9px; letter-spacing: 0.28em;
    color: var(--text-mono); text-transform: uppercase; margin: 16px 0 8px;
  }
  .holo-body .h-row {
    display: flex; gap: 10px; align-items: baseline;
    padding: 9px 12px; margin-bottom: 6px; font-size: 13.5px; line-height: 1.5;
    border: 1px solid var(--stroke); border-radius: 4px; background: rgba(255,255,255,0.02);
  }
  .holo-body .h-row .h-mark { font-family: var(--mono); color: var(--cyan); flex: none; font-size: 11px; }
  .holo-body .h-row .h-note { color: var(--text-dim); font-size: 12px; }
  .holo-foot {
    flex: none; padding: 10px 20px; border-top: 1px solid var(--stroke);
    font-family: var(--mono); font-size: 9px; letter-spacing: 0.18em; color: var(--text-dim);
    display: flex; justify-content: space-between;
  }
  .artifact-chips { max-width: 720px; margin: -12px auto 22px; padding-left: 20px; display: flex; gap: 8px; flex-wrap: wrap; }
  .artifact-chips button {
    font-family: var(--mono); font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase;
    padding: 7px 13px; border-radius: 3px; cursor: pointer;
    border: 1px solid var(--stroke-bright); background: rgba(34, 211, 238, 0.07); color: var(--cyan-soft);
    transition: all 0.2s;
  }
  .artifact-chips button:hover { background: rgba(34, 211, 238, 0.18); box-shadow: 0 0 14px rgba(34, 211, 238, 0.15); }

  /* ── Responsive ──────────────────────────────────────────────────── */
  @media (max-width: 1180px) {
    .hud { grid-template-columns: 280px minmax(0, 1fr); grid-template-areas: "top top" "left stage"; }
    .dock.right { display: none; }
  }
  @media (max-width: 860px) {
    .hud { grid-template-columns: minmax(0, 1fr); grid-template-areas: "top" "stage"; padding: 0 10px; }
    .dock { display: none; }
    .core-wrap { width: 84px; height: 84px; }
    .core-orb { inset: 24px; }
    .topstrip .readouts .hide-sm { display: none; }
  }
</style>
</head>
<body>
<div class="backdrop"></div>

<div id="boot">
  <div class="core-wrap">
    <svg viewBox="0 0 120 120">
      <circle class="core-ring ring-a" cx="60" cy="60" r="52" stroke-dasharray="70 24 12 24 70 24"></circle>
      <circle class="core-ring ring-b" cx="60" cy="60" r="44" stroke-dasharray="40 18 90 18"></circle>
      <circle class="core-ring ring-c" cx="60" cy="60" r="58" stroke-dasharray="4 10"></circle>
    </svg>
    <div class="core-orb"></div>
  </div>
  <div class="boot-title">J A R V I S</div>
  <div class="boot-lines" id="boot-lines"></div>
</div>

<div class="hud" id="hud" data-state="ambient">
  <div class="topstrip">
    <span class="wordmark">JARVIS</span>
    <div class="readouts">
      <span id="ro-clock">--:--</span>
      <span class="hide-sm" id="ro-agents"><span class="dot"></span>&mdash; agents</span>
      <span id="ro-needs">&mdash;</span>
      <nav class="topnav">
        <a href="/health-center">HEALTH</a>
        <a href="/forge">FORGE</a>
        <a href="/mission-board" class="hide-sm">MISSIONS</a>
        <a href="/command-center" class="hide-sm">OPS</a>
        <a href="/settings-center" class="hide-sm">SETTINGS</a>
      </nav>
      <a href="/glass" class="hide-sm">CLASSIC</a>
    </div>
  </div>

  <aside class="dock left">
    <div class="card" id="card-needs">
      <h3>Needs You <span class="count" id="needs-count">&mdash;</span></h3>
      <div id="needs-list"><div class="empty-note">Reaching Jarvis&hellip;</div></div>
    </div>
    <div class="card" id="card-missions">
      <h3>Missions <span class="count" id="missions-count">&mdash;</span></h3>
      <div id="missions-list"><div class="empty-note">Reaching Jarvis&hellip;</div></div>
    </div>
  </aside>

  <main class="stage">
    <div class="stage-head">
      <div class="core-wrap">
        <svg viewBox="0 0 120 120">
          <circle class="core-ring ring-a" cx="60" cy="60" r="52" stroke-dasharray="70 24 12 24 70 24"></circle>
          <circle class="core-ring ring-b" cx="60" cy="60" r="44" stroke-dasharray="40 18 90 18"></circle>
          <circle class="core-ring ring-c" cx="60" cy="60" r="58" stroke-dasharray="4 10"></circle>
        </svg>
        <div class="core-orb"></div>
      </div>
    </div>

    <div class="stream" id="stream">
      <div class="hello" id="hello">
        <div class="h-greet" id="hello-greet">Good day, <b>__USER_NAME__</b>.</div>
        <div class="h-sub" id="hello-sub">Systems standing by.</div>
        <div class="h-priority" id="hello-priority" style="display:none">
          <span class="p-label">Priority</span>
          <span id="hello-priority-text"></span>
        </div>
        <div class="chips">
          <button onclick="quickSend('Give me my morning brief')">Morning brief</button>
          <button onclick="quickSend('What needs my attention right now?')">What needs me</button>
          <button onclick="quickSend('What are my agents working on?')">Agent status</button>
        </div>
      </div>
    </div>

    <div class="composer-wrap">
      <div class="composer">
        <textarea id="input" rows="1" placeholder="Talk to Jarvis&hellip;"></textarea>
        <button class="c-btn mic" id="mic-btn" title="Voice input" style="display:none">&#9679;</button>
        <button class="c-btn send" id="send-btn" title="Send">&uarr;</button>
      </div>
    </div>
  </main>

  <aside class="dock right">
    <div class="card">
      <h3>Agents <span class="count" id="agents-count">&mdash;</span></h3>
      <div class="constellation" id="constellation">
        <svg class="orbits" viewBox="0 0 100 100" preserveAspectRatio="none">
          <circle cx="50" cy="50" r="40" vector-effect="non-scaling-stroke"></circle>
          <circle cx="50" cy="50" r="26" vector-effect="non-scaling-stroke"></circle>
        </svg>
        <div class="c-center" id="const-center">WORKFORCE</div>
      </div>
    </div>
    <div class="card">
      <h3>Today</h3>
      <div id="today-list"><div class="empty-note">Reaching Jarvis&hellip;</div></div>
    </div>
    <div class="card">
      <h3>Telemetry</h3>
      <div class="telemetry">
        <div>CHANNEL <b id="tm-model">&mdash;</b></div>
        <div>LATENCY <b id="tm-latency">&mdash;</b></div>
        <div>LINK <b id="tm-link">CONNECTING</b></div>
        <div>EVENTS <b id="tm-events">0</b></div>
      </div>
    </div>
  </aside>
</div>

<div class="veil" id="veil" aria-modal="true" role="dialog">
  <div class="holo">
    <div class="holo-head">
      <div><div class="hk" id="holo-kind"></div><div class="ht" id="holo-title"></div></div>
      <button class="hx" id="holo-close" title="Dismiss (Esc)">&#10005;</button>
    </div>
    <div class="holo-body" id="holo-body"></div>
    <div class="holo-foot"><span id="holo-foot-left"></span><span>ESC TO DISMISS</span></div>
  </div>
</div>

<script>
'use strict';
const USER_NAME = "__USER_NAME__";
const $ = (id) => document.getElementById(id);
const hud = $('hud');
let conversationId = localStorage.getItem('jarvis-hud-conversation') || '';
let eventCount = 0;
let agentNodes = {};

/* ── Boot sequence (once per session) ─────────────────────────────── */
(function boot() {
  const el = $('boot');
  if (sessionStorage.getItem('jarvis-hud-booted')) { el.remove(); return; }
  const lines = $('boot-lines');
  const add = (text, delay) => {
    const d = document.createElement('div');
    d.textContent = text;
    d.style.animationDelay = delay + 'ms';
    lines.appendChild(d);
  };
  add('INITIALIZING CORE', 500);
  add('LINKING AGENT WORKFORCE', 900);
  add('SYSTEMS ONLINE', 1350);
  const finish = () => {
    el.classList.add('done');
    sessionStorage.setItem('jarvis-hud-booted', '1');
    setTimeout(() => el.remove(), 700);
  };
  setTimeout(finish, 2100);
  el.addEventListener('click', finish);
})();

/* ── Clock ────────────────────────────────────────────────────────── */
function tickClock() {
  const now = new Date();
  $('ro-clock').textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
tickClock(); setInterval(tickClock, 10000);

/* ── Greeting (time-aware immediately; enriched by real brief) ────── */
(function localGreeting() {
  const h = new Date().getHours();
  const part = h < 5 ? 'Good evening' : h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
  $('hello-greet').innerHTML = part + ', <b>' + USER_NAME + '</b>.';
})();

async function loadBrief() {
  try {
    const r = await fetch('/api/briefing/module?actor=' + encodeURIComponent(USER_NAME));
    const d = await r.json();
    const mb = d.morning_brief || {};
    if (mb.greeting) {
      const cleaned = String(mb.greeting).replace(/\s*I've been paying attention\.?\s*$/, '');
      $('hello-greet').innerHTML = cleaned.replace(USER_NAME, '<b>' + USER_NAME + '</b>');
      $('hello-sub').textContent = "I've been paying attention.";
    }
    if (mb.recommendation) {
      $('hello-priority-text').textContent = mb.recommendation;
      $('hello-priority').style.display = '';
    }
    const today = $('today-list');
    const items = [];
    (mb.what_changed || []).slice(0, 3).forEach(t => items.push(['CHANGED', t]));
    (d.open_loops && d.open_loops.items || []).slice(0, 2).forEach(l => items.push(['OPEN', l.title || l.summary || '']));
    if (items.length) {
      today.innerHTML = items.map(([k, t]) =>
        '<div class="row"><div class="r-meta">' + k + '</div><div class="r-title">' + escapeHtml(String(t)).slice(0, 110) + '</div></div>'
      ).join('');
    } else {
      today.innerHTML = '<div class="empty-note">Quiet so far today.</div>';
    }
  } catch (e) {
    $('today-list').innerHTML = '<div class="empty-note">Brief unavailable.</div>';
  }
}

/* ── Command center payload: needs, missions, agents ──────────────── */
async function loadOps() {
  try {
    const r = await fetch('/api/command-center');
    const d = await r.json();

    // Needs You
    const needs = (d.needs_cockpit && d.needs_cockpit.items) || [];
    const needsTotal = (d.needs_cockpit && d.needs_cockpit.total) || 0;
    $('needs-count').textContent = needsTotal;
    $('needs-count').className = 'count' + (needsTotal > 0 ? ' warn' : '');
    $('ro-needs').innerHTML = needsTotal > 0
      ? '<span class="badge-attn">&#9650; ' + needsTotal + ' need you</span>'
      : 'all clear';
    hud.dataset.state = needsTotal > 0 ? 'attention' : 'ambient';
    const nl = $('needs-list');
    if (needs.length === 0) {
      nl.innerHTML = '<div class="empty-note">Nothing waiting on you.</div>';
    } else {
      nl.innerHTML = needs.slice(0, 5).map(item => {
        const urg = String(item.urgency || 'normal');
        const cls = urg === 'critical' ? 'crit' : (urg === 'high' ? 'high' : '');
        let btns = '';
        const pa = item.primary_action || {};
        if (pa.endpoint && pa.method) {
          btns = '<div class="act-btns"><button onclick="doAction(this, \'' + pa.endpoint + '\', \'' + (pa.method || 'POST') + '\')">' + escapeHtml(pa.label || 'Approve') + '</button></div>';
        } else if (item.route) {
          btns = '<div class="act-btns"><button onclick="location.href=\'' + item.route + '\'">' + escapeHtml(item.route_label || 'Open') + '</button></div>';
        }
        return '<div class="row"><div class="r-meta ' + cls + '">' + escapeHtml(urg) + '</div><div class="r-title">' + escapeHtml(String(item.title || '')).slice(0, 90) + '</div>' + btns + '</div>';
      }).join('');
    }

    // Missions
    const missions = ((d.mission_task_board || {}).items || []).filter(m => String(m.lane || '') !== 'completed');
    $('missions-count').textContent = missions.length;
    const ml = $('missions-list');
    ml.innerHTML = missions.length === 0
      ? '<div class="empty-note">No active missions. Say the word.</div>'
      : missions.slice(0, 5).map(m =>
          '<div class="row"><div class="r-meta lane-' + escapeHtml(String(m.lane || 'next')) + '">' + escapeHtml(String(m.lane || 'next')) + '</div><div class="r-title">' + escapeHtml(String(m.title || '')).slice(0, 90) + '</div></div>'
        ).join('');

    // Agent constellation
    const roster = ((d.agent_ops_roster || {}).items || []);
    $('agents-count').textContent = roster.length;
    const running = roster.filter(a => String(a.runtime_status || '') === 'running').length;
    $('ro-agents').innerHTML = '<span class="dot"></span>' + roster.length + ' agents';
    buildConstellation(roster);
  } catch (e) {
    $('needs-list').innerHTML = '<div class="empty-note">Ops feed unavailable.</div>';
    $('missions-list').innerHTML = '<div class="empty-note">Ops feed unavailable.</div>';
  }
}

function buildConstellation(roster) {
  const c = $('constellation');
  c.querySelectorAll('.agent-node').forEach(n => n.remove());
  agentNodes = {};
  const W = c.clientWidth || 280, H = c.clientHeight || 190;
  roster.slice(0, 14).forEach((a, i) => {
    const ring = i % 2 === 0 ? 0.40 : 0.26;
    const angle = (i / Math.min(roster.length, 14)) * Math.PI * 2 - Math.PI / 2;
    const x = W / 2 + Math.cos(angle) * W * ring;
    const y = H / 2 + Math.sin(angle) * H * ring * 0.95;
    const status = String(a.runtime_status || a.status || 'idle');
    const label = String(a.label || a.agent_id || 'agent');
    const node = document.createElement('div');
    node.className = 'agent-node';
    node.dataset.status = status;
    node.style.left = x + 'px';
    node.style.top = y + 'px';
    node.innerHTML = '<div class="n-dot"></div><span class="n-label">' + escapeHtml(label) + ' &middot; ' + escapeHtml(status) + '</span>';
    c.appendChild(node);
    agentNodes[label.toLowerCase()] = node;
  });
}

/* ── Live event stream ────────────────────────────────────────────── */
function connectEvents() {
  let ws;
  try {
    const proto = location.protocol === 'https:' ? 'wss://' : 'ws://';
    ws = new WebSocket(proto + location.host + '/ws/events');
  } catch (e) { $('tm-link').textContent = 'OFFLINE'; return; }
  ws.onopen = () => { $('tm-link').textContent = 'LIVE'; };
  ws.onclose = () => { $('tm-link').textContent = 'OFFLINE'; setTimeout(connectEvents, 8000); };
  ws.onmessage = (ev) => {
    eventCount += 1;
    $('tm-events').textContent = eventCount;
    try {
      const data = JSON.parse(ev.data);
      const agent = String(data.agent_id || data.agent || data.source || '').toLowerCase();
      if (agent && agentNodes[agent]) {
        const n = agentNodes[agent];
        n.classList.remove('flash'); void n.offsetWidth; n.classList.add('flash');
      }
    } catch (e) { /* non-JSON event: ignore */ }
  };
}

/* ── Approve/deny actions ─────────────────────────────────────────── */
async function doAction(btn, endpoint, method) {
  btn.disabled = true; btn.textContent = '…';
  try {
    const r = await fetch(endpoint, { method: method, headers: { 'Content-Type': 'application/json' }, body: '{}' });
    btn.textContent = r.ok ? 'DONE' : 'FAILED';
    if (r.ok) setTimeout(loadOps, 800);
  } catch (e) { btn.textContent = 'FAILED'; }
}

/* ── Conversation ─────────────────────────────────────────────────── */
const stream = $('stream');
const input = $('input');

function escapeHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function addMsg(role, text, meta) {
  $('hello') && $('hello').remove();
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  if (role === 'you') {
    div.innerHTML = '<span class="bubble">' + escapeHtml(text) + '</span>';
  } else {
    div.innerHTML = '<div class="who">JARVIS</div><div class="bubble">' + escapeHtml(text) + '</div>' +
      (meta ? '<div class="b-meta">' + escapeHtml(meta) + '</div>' : '');
  }
  stream.appendChild(div);
  stream.scrollTop = stream.scrollHeight;
}

let thinkingEl = null;
function showThinking() {
  thinkingEl = document.createElement('div');
  thinkingEl.className = 'thinking-line';
  thinkingEl.innerHTML = '<div class="t-label">PROCESSING</div><div class="scan"></div>';
  stream.appendChild(thinkingEl);
  stream.scrollTop = stream.scrollHeight;
  hud.dataset.state = 'thinking';
}
function hideThinking() {
  if (thinkingEl) { thinkingEl.remove(); thinkingEl = null; }
  hud.dataset.state = 'ambient';
}

async function send() {
  const text = input.value.trim();
  if (!text) return;
  input.value = ''; autoGrow();
  addMsg('you', text);
  showThinking();
  const t0 = performance.now();
  try {
    const r = await fetch('/api/respond', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actor: USER_NAME, room: 'office', request: text, conversation_id: conversationId, source: 'hud' })
    });
    const d = await r.json();
    hideThinking();
    const ms = Math.round(performance.now() - t0);
    if (d.conversation_id) {
      conversationId = d.conversation_id;
      localStorage.setItem('jarvis-hud-conversation', conversationId);
    }
    const model = String(d.model || '');
    $('tm-model').textContent = model ? model.toUpperCase().slice(0, 18) : '—';
    $('tm-latency').textContent = (ms / 1000).toFixed(1) + 's';
    addMsg('jarvis', String(d.output_text || '(no reply)'), model ? model + ' · ' + (ms / 1000).toFixed(1) + 's' : '');
    presentArtifacts(d);
    loadOps();
  } catch (e) {
    hideThinking();
    addMsg('jarvis', 'I lost the link mid-thought. Try that again in a moment.');
  }
}

function presentArtifacts(d) {
  const found = [];
  for (const [key, val] of Object.entries(d)) {
    if (key.startsWith('created_') && val && typeof val === 'object' && Object.keys(val).length) {
      found.push([key, val]);
    }
  }
  if (found.length) {
    const wrap = document.createElement('div');
    wrap.className = 'artifact-chips';
    for (const [kind, obj] of found) {
      const id = 'art-' + (++artifactSeq);
      artifactStore[id] = { kind, obj };
      const btn = document.createElement('button');
      btn.innerHTML = '&#9670; ' + kindLabel(kind);
      btn.addEventListener('click', () => summonArtifact(kind, obj));
      wrap.appendChild(btn);
    }
    stream.appendChild(wrap);
    stream.scrollTop = stream.scrollHeight;
    // materialize the first artifact — it appears because it was just made
    const [k0, o0] = found[0];
    setTimeout(() => summonArtifact(k0, o0), 550);
  } else if (d.requested_packet) {
    summonPacket(String(d.requested_packet));
  }
}

function quickSend(text) { input.value = text; send(); }

function autoGrow() {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 140) + 'px';
}
input.addEventListener('input', autoGrow);
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
});
$('send-btn').addEventListener('click', send);
document.addEventListener('keydown', (e) => {
  if (e.key === '/' && document.activeElement !== input) { e.preventDefault(); input.focus(); }
});

/* ── Holographic panels: artifacts & data sets, summoned on demand ── */
const veil = $('veil');
const artifactStore = {};   // chip-id -> {kind, obj}
let artifactSeq = 0;

const META_KEYS = new Set(['actor', 'room', 'status', 'source_request', 'creation_proof',
  'object_kind', 'created_at', 'updated_at', 'truth_mode', 'live_retrieval_used',
  'title', 'topic', 'item_count']);

function kindLabel(kind) {
  return kind.replace(/^created_/, '').replace(/_/g, ' ').toUpperCase();
}

function renderArtifactBody(obj) {
  let html = '';
  const summary = obj.summary || obj.recommendation_note || obj.note || '';
  if (summary) html += '<div class="h-summary">' + escapeHtml(String(summary)) + '</div>';
  for (const [key, val] of Object.entries(obj)) {
    if (META_KEYS.has(key) || /_id$/.test(key)) continue;
    if (key === 'summary' || key === 'recommendation_note') continue;
    if (Array.isArray(val) && val.length) {
      html += '<div class="h-section">' + escapeHtml(key.replace(/_/g, ' ')) + '</div>';
      for (const entry of val.slice(0, 40)) {
        if (entry && typeof entry === 'object') {
          const mark = ('completed' in entry) ? (entry.completed ? '&#9745;' : '&#9744;') : '&#9656;';
          const main = entry.text || entry.label || entry.title || entry.name || entry.question || entry.step || JSON.stringify(entry).slice(0, 120);
          const note = entry.notes || entry.detail || entry.why || entry.reason || '';
          html += '<div class="h-row"><span class="h-mark">' + mark + '</span><span>' + escapeHtml(String(main)) +
            (note ? ' <span class="h-note">&mdash; ' + escapeHtml(String(note)) + '</span>' : '') + '</span></div>';
        } else {
          html += '<div class="h-row"><span class="h-mark">&#9656;</span><span>' + escapeHtml(String(entry)) + '</span></div>';
        }
      }
    } else if (typeof val === 'string' && val.trim() && val.length > 1) {
      html += '<div class="h-section">' + escapeHtml(key.replace(/_/g, ' ')) + '</div>';
      html += '<div class="h-row"><span>' + escapeHtml(val).slice(0, 4000) + '</span></div>';
    }
  }
  return html || '<div class="h-summary">Created. No detail fields to display.</div>';
}

function summonArtifact(kind, obj) {
  $('holo-kind').textContent = kindLabel(kind);
  $('holo-title').textContent = String(obj.title || obj.topic || 'Untitled');
  if (kind === 'created_obsidian_note_proposal') {
    $('holo-body').innerHTML = renderObsidianProposalBody(obj);
  } else if (kind === 'created_marketing_assets') {
    $('holo-body').innerHTML = renderMarketingAssetsBody(obj);
  } else {
    $('holo-body').innerHTML = renderArtifactBody(obj);
  }
  $('holo-foot-left').textContent = obj.created_at ? String(obj.created_at).slice(0, 16).replace('T', ' &middot; '.replace(/&middot;/, '·')) : '';
  veil.classList.add('open');
}

function renderObsidianProposalBody(obj) {
  const preview = String(obj.body_preview || '').replace(/\n/g, '<br>');
  const tags = (obj.tags || []).map(t => escapeHtml(String(t))).join(', ');
  return (
    '<div class="h-summary">' + escapeHtml(String(obj.summary || '')) + '</div>' +
    '<div class="h-section">Draft</div>' +
    '<div class="h-row"><span>' + preview + '</span></div>' +
    (tags ? '<div class="h-row"><span class="h-note">tags: ' + tags + '</span></div>' : '') +
    '<div class="act-btns" style="margin-top:14px">' +
    '<button onclick="approveObsidianProposal(this, \'' + escapeHtml(String(obj.proposal_id || '')) + '\')">Approve &amp; Write to Vault</button>' +
    '<button class="deny" onclick="rejectObsidianProposal(this, \'' + escapeHtml(String(obj.proposal_id || '')) + '\')">Discard</button>' +
    '</div>'
  );
}

async function approveObsidianProposal(btn, proposalId) {
  btn.disabled = true; btn.textContent = 'Writing…';
  try {
    const r = await fetch('/api/obsidian/proposals/' + proposalId + '/approve', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}'
    });
    const d = await r.json();
    if (d.written) {
      btn.textContent = 'Written: ' + (d.path || 'vault');
    } else {
      btn.textContent = 'Approved (not written)';
      const body = $('holo-body');
      const note = document.createElement('div');
      note.className = 'h-row';
      note.innerHTML = '<span class="h-note">' + escapeHtml(String(d.reason || 'Could not write from this machine.')) + '</span>';
      body.appendChild(note);
    }
  } catch (e) { btn.textContent = 'Failed'; }
}

async function rejectObsidianProposal(btn, proposalId) {
  btn.disabled = true;
  try {
    await fetch('/api/approvals/' + proposalId + '/reject', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason: 'Discarded from HUD' })
    });
    dismissPanel();
  } catch (e) { btn.textContent = 'Failed'; }
}

function renderMarketingAssetsBody(obj) {
  const platforms = (obj.platforms || []).map(p => escapeHtml(String(p))).join(', ');
  const twitter = String(obj.twitter_preview || '').replace(/\n/g, '<br>');
  const press = String(obj.press_release_preview || '').replace(/\n/g, '<br>');
  return (
    '<div class="h-summary">Drafted for &ldquo;' + escapeHtml(String(obj.book_title || '')) + '&rdquo; &mdash; ' +
    escapeHtml(platforms || 'multiple platforms') +
    '. Jarvis cannot publish these &mdash; no social/press API is connected. Approve to mark them ready, then hand-post them yourself.</div>' +
    (twitter ? '<div class="h-section">Twitter (first post)</div><div class="h-row"><span>' + twitter + '</span></div>' : '') +
    (press ? '<div class="h-section">Press release (preview)</div><div class="h-row"><span>' + press + '</span></div>' : '') +
    '<div class="act-btns" style="margin-top:14px">' +
    '<button onclick="approveMarketingAssets(this, \'' + escapeHtml(String(obj.proposal_id || '')) + '\')">Approve (ready to hand-post)</button>' +
    '<button class="deny" onclick="rejectMarketingAssets(this, \'' + escapeHtml(String(obj.proposal_id || '')) + '\')">Discard</button>' +
    '</div>'
  );
}

async function approveMarketingAssets(btn, proposalId) {
  btn.disabled = true; btn.textContent = 'Approving…';
  try {
    const r = await fetch('/api/approvals/' + proposalId + '/approve', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}'
    });
    const d = await r.json();
    btn.textContent = (d.status === 'approved') ? 'Approved — ready to hand-post' : 'Failed';
  } catch (e) { btn.textContent = 'Failed'; }
}

async function rejectMarketingAssets(btn, proposalId) {
  btn.disabled = true;
  try {
    await fetch('/api/approvals/' + proposalId + '/reject', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason: 'Discarded from HUD' })
    });
    dismissPanel();
  } catch (e) { btn.textContent = 'Failed'; }
}

function summonDataPanel(kindLabelText, title, rowsHtml) {
  $('holo-kind').textContent = kindLabelText;
  $('holo-title').textContent = title;
  $('holo-body').innerHTML = rowsHtml || '<div class="h-summary">Nothing to show right now.</div>';
  $('holo-foot-left').textContent = 'LIVE';
  veil.classList.add('open');
}

function dismissPanel() { veil.classList.remove('open'); }
$('holo-close').addEventListener('click', dismissPanel);
veil.addEventListener('click', (e) => { if (e.target === veil) dismissPanel(); });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && veil.classList.contains('open')) dismissPanel(); });

/* Data-set summons for packets Jarvis requests during conversation */
async function summonPacket(packet) {
  try {
    if (packet === 'mission-control' || packet === 'missions') {
      const d = await (await fetch('/api/command-center')).json();
      const items = ((d.mission_task_board || {}).items || []);
      summonDataPanel('MISSIONS', 'Active Missions', items.map(m =>
        '<div class="h-row"><span class="h-mark lane-' + escapeHtml(String(m.lane || 'next')) + '">' + escapeHtml(String(m.lane || 'next').toUpperCase()) + '</span><span>' + escapeHtml(String(m.title || '')) + '</span></div>'
      ).join(''));
    } else if (packet === 'approvals' || packet === 'approval-queue') {
      const d = await (await fetch('/api/command-center')).json();
      const items = ((d.needs_cockpit || {}).items || []);
      summonDataPanel('NEEDS YOU', 'Waiting on your decision', items.map(i =>
        '<div class="h-row"><span class="h-mark">&#9650;</span><span>' + escapeHtml(String(i.title || '')) +
        ' <span class="h-note">&mdash; ' + escapeHtml(String(i.urgency || '')) + '</span></span></div>'
      ).join(''));
    } else if (packet === 'briefing' || packet === 'daily-brief') {
      const d = await (await fetch('/api/briefing/module?actor=' + encodeURIComponent(USER_NAME))).json();
      const mb = d.morning_brief || {};
      let rows = '';
      for (const sec of ['what_changed', 'what_matters', 'what_is_waiting', 'jarvis_prepared']) {
        const list = mb[sec] || [];
        if (!list.length) continue;
        rows += '<div class="h-section">' + sec.replace(/_/g, ' ') + '</div>';
        rows += list.slice(0, 6).map(t => '<div class="h-row"><span class="h-mark">&#9656;</span><span>' + escapeHtml(String(t)) + '</span></div>').join('');
      }
      summonDataPanel('DAILY BRIEF', String(mb.greeting || 'Your day'), rows);
    }
  } catch (e) { /* panel just doesn't appear; conversation already has the answer */ }
}

/* ── Voice input (browser speech recognition, if available) ───────── */
(function initMic() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return;
  const btn = $('mic-btn');
  btn.style.display = '';
  let rec = null, listening = false;
  btn.addEventListener('click', () => {
    if (listening) { rec && rec.stop(); return; }
    rec = new SR();
    rec.lang = 'en-US';
    rec.interimResults = true;
    listening = true; btn.classList.add('listening');
    rec.onresult = (ev) => {
      let t = '';
      for (const res of ev.results) t += res[0].transcript;
      input.value = t; autoGrow();
    };
    rec.onend = () => {
      listening = false; btn.classList.remove('listening');
      if (input.value.trim()) send();
    };
    rec.onerror = () => { listening = false; btn.classList.remove('listening'); };
    rec.start();
  });
})();

/* ── Go ───────────────────────────────────────────────────────────── */
loadBrief();
loadOps();
connectEvents();
setInterval(loadOps, 60000);
</script>
</body>
</html>"""
