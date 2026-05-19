"""JARVIS · Glass Theme — Surgical Glass · Marvel Aesthetic · Adaptive Chromatic"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runtime import JarvisRuntime


def render_glass_shell(runtime, initial_packet: str = "") -> str:
    """Return the complete Glass theme HTML document string."""
    import json as _json

    try:
        user_name = runtime.config.your_name or "Chris"
    except Exception:
        user_name = "Chris"

    _packet = _json.dumps(initial_packet)
    _user_name_js = _json.dumps(user_name)

    return f"""<!DOCTYPE html>
<html lang="en" data-domain="overview">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>JARVIS · Glass</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
  <style>

/* ═══════════════════════════════════════════════════════════════════
   CSS CUSTOM PROPERTIES
═══════════════════════════════════════════════════════════════════ */
:root {{
  /* Surface — surgical glass palette */
  --bg:          #DFE8F2;
  --bg-gradient: linear-gradient(145deg, #E8EEF6 0%, #D8E4F0 40%, #E2EAF5 100%);
  --surface:     rgba(255,255,255,0.65);
  --surface-hi:  rgba(255,255,255,0.88);
  --border:      rgba(255,255,255,0.55);
  --border-hi:   rgba(255,255,255,0.80);

  /* Text */
  --text-1:  #0F172A;
  --text-2:  #475569;
  --text-3:  #94A3B8;

  /* Fixed semantic colors — NEVER shift */
  --navy:    #0A1628;
  --crimson: #C41E3A;
  --gold:    #C9A84C;
  --success: #10B981;

  /* Hue tokens — ONLY these shift per domain */
  --hue:      #00B4FF;
  --hue-dim:  rgba(0,180,255,0.12);
  --hue-glow: rgba(0,180,255,0.35);
  --hue-tint: rgba(0,180,255,0.03);
  --hue-rgb:  0, 180, 255;

  /* Typography */
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'Fira Code', 'SF Mono', monospace;

  /* Layout */
  --nav-h:    58px;
  --strip-h:  2px;
  --bar-h:    70px;
}}

/* ── Domain overrides — ONLY the 4 hue vars change ── */
[data-domain="forge"]         {{ --hue: #F59E0B; --hue-dim: rgba(245,158,11,0.12); --hue-glow: rgba(245,158,11,0.35); --hue-tint: rgba(245,158,11,0.04); --hue-rgb: 245,158,11; }}
[data-domain="vision"]        {{ --hue: #06B6D4; --hue-dim: rgba(6,182,212,0.12);  --hue-glow: rgba(6,182,212,0.35);  --hue-tint: rgba(6,182,212,0.03);  --hue-rgb: 6,182,212; }}
[data-domain="catalyst"]      {{ --hue: #8B5CF6; --hue-dim: rgba(139,92,246,0.12); --hue-glow: rgba(139,92,246,0.35); --hue-tint: rgba(139,92,246,0.04); --hue-rgb: 139,92,246; }}
[data-domain="chronicle"]     {{ --hue: #3B82F6; --hue-dim: rgba(59,130,246,0.12); --hue-glow: rgba(59,130,246,0.35); --hue-tint: rgba(59,130,246,0.03); --hue-rgb: 59,130,246; }}
[data-domain="publishing"]    {{ --hue: #D97706; --hue-dim: rgba(217,119,6,0.12);  --hue-glow: rgba(217,119,6,0.35);  --hue-tint: rgba(217,119,6,0.03);  --hue-rgb: 217,119,6; }}
[data-domain="workshop"]      {{ --hue: #EA580C; --hue-dim: rgba(234,88,12,0.12);  --hue-glow: rgba(234,88,12,0.35);  --hue-tint: rgba(234,88,12,0.04);  --hue-rgb: 234,88,12; }}
[data-domain="agents"]        {{ --hue: #14B8A6; --hue-dim: rgba(20,184,166,0.12); --hue-glow: rgba(20,184,166,0.35); --hue-tint: rgba(20,184,166,0.03); --hue-rgb: 20,184,166; }}
[data-domain="intelligence"]  {{ --hue: #10B981; --hue-dim: rgba(16,185,129,0.12); --hue-glow: rgba(16,185,129,0.35); --hue-tint: rgba(16,185,129,0.03); --hue-rgb: 16,185,129; }}
[data-domain="briefing"]      {{ --hue: #7C3AED; --hue-dim: rgba(124,58,237,0.12); --hue-glow: rgba(124,58,237,0.35); --hue-tint: rgba(124,58,237,0.04); --hue-rgb: 124,58,237; }}
[data-domain="family"]        {{ --hue: #F43F5E; --hue-dim: rgba(244,63,94,0.12);  --hue-glow: rgba(244,63,94,0.35);  --hue-tint: rgba(244,63,94,0.03);  --hue-rgb: 244,63,94; }}
[data-domain="chat"]          {{ --hue: #00B4FF; --hue-dim: rgba(0,180,255,0.12);  --hue-glow: rgba(0,180,255,0.35);  --hue-tint: rgba(0,180,255,0.03);  --hue-rgb: 0,180,255; }}

/* ── Global transitions for chromatic shift ── */
*, *::before, *::after {{
  box-sizing: border-box;
  transition:
    background-color 0.45s ease,
    border-color     0.45s ease,
    color            0.45s ease,
    box-shadow       0.45s ease,
    fill             0.45s ease,
    stroke           0.45s ease;
}}

/* Suppress layout transitions */
.view, .nav-bar, .domain-strip, .command-bar,
.agent-grid, .card, .stats-strip {{
  transition:
    background-color 0.45s ease,
    border-color     0.45s ease,
    color            0.45s ease,
    box-shadow       0.45s ease;
}}

/* ═══════════════════════════════════════════════════════════════════
   RESET & BASE
═══════════════════════════════════════════════════════════════════ */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

html {{
  scroll-behavior: smooth;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}}

body {{
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-1);
  background: var(--bg-gradient);
  background-attachment: fixed;
  min-height: 100vh;
  overflow-x: hidden;
}}

/* S.H.I.E.L.D. hex-grid background */
body::before {{
  content: '';
  position: fixed;
  inset: 0;
  z-index: 0;
  opacity: 0.035;
  pointer-events: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='56' height='100'%3E%3Cpath d='M28 66L0 50V17L28 0l28 17v33L28 66zm0 34L0 83V67l28 17 28-17v17L28 100z' fill='none' stroke='%230A1628' stroke-width='1'/%3E%3C/svg%3E");
  background-size: 56px 100px;
}}

/* Domain hue tint overlay */
body::after {{
  content: '';
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background: var(--hue-tint);
  transition: background 0.45s ease;
}}

/* ═══════════════════════════════════════════════════════════════════
   GLASS CARD — Surgical Glass with Marvel Feel
   Three-layer technique:
     1. Interior gradient  — bright frost at top → clear at bottom
     2. Edge highlight     — asymmetric bright gleam on top-left
     3. Corner glow        — pseudo-element ambient hue reflection
═══════════════════════════════════════════════════════════════════ */
.card {{
  position: relative;
  /* Interior gradient: luminous frost fading downward */
  background:
    linear-gradient(
      160deg,
      rgba(255,255,255,0.72) 0%,
      rgba(255,255,255,0.40) 40%,
      rgba(255,255,255,0.22) 100%
    );
  backdrop-filter: blur(28px) saturate(200%) brightness(1.05);
  -webkit-backdrop-filter: blur(28px) saturate(200%) brightness(1.05);
  /* Asymmetric border: bright top-left, subdued bottom-right */
  border-top:    1px solid rgba(255,255,255,0.90);
  border-left:   1px solid rgba(255,255,255,0.80);
  border-right:  1px solid rgba(255,255,255,0.30);
  border-bottom: 1px solid rgba(255,255,255,0.25);
  border-radius: 14px;
  /* Shadow stack: ambient + directional lift + inner glow strip */
  box-shadow:
    0  1px  2px rgba(0,0,0,0.04),
    0  8px 24px rgba(0,0,0,0.07),
    0 24px 48px rgba(0,0,0,0.05),
    inset 0 1px 0 rgba(255,255,255,0.95),
    inset 1px 0 0 rgba(255,255,255,0.50);
}}

/* Edge highlight flare — the characteristic bright gleam seen in glass */
.card::before {{
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(
    90deg,
    rgba(255,255,255,0) 0%,
    rgba(255,255,255,1) 20%,
    rgba(255,255,255,1) 50%,
    rgba(255,255,255,0.4) 80%,
    rgba(255,255,255,0) 100%
  );
  border-radius: 14px 14px 0 0;
  z-index: 1;
  pointer-events: none;
}}

/* Corner glow — ambient hue reflection from domain accent colour */
.card::after {{
  content: '';
  position: absolute;
  top: -10px; left: -10px;
  width: 140px; height: 140px;
  background: radial-gradient(
    circle,
    rgba(var(--hue-rgb), 0.10) 0%,
    rgba(var(--hue-rgb), 0.04) 50%,
    transparent 70%
  );
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
  transition: background 0.45s ease;
}}

.card-hi {{
  background:
    linear-gradient(
      160deg,
      rgba(255,255,255,0.85) 0%,
      rgba(255,255,255,0.55) 40%,
      rgba(255,255,255,0.30) 100%
    );
  box-shadow:
    0  1px  2px rgba(0,0,0,0.04),
    0  8px 24px rgba(0,0,0,0.08),
    0 24px 48px rgba(0,0,0,0.05),
    inset 0 1px 0 rgba(255,255,255,1),
    inset 1px 0 0 rgba(255,255,255,0.70);
}}

/* ── Tactical card with L-bracket corner accents ── */
.card-tactical {{
  position: relative;
}}
.card-tactical::before,
.card-tactical::after {{
  content: '';
  position: absolute;
  width: 12px;
  height: 12px;
  border-color: var(--hue);
  border-style: solid;
  transition: border-color 0.45s ease;
  z-index: 2;
}}
.card-tactical::before {{
  top: -1px; left: -1px;
  border-width: 2px 0 0 2px;
  border-radius: 4px 0 0 0;
}}
.card-tactical::after {{
  bottom: -1px; right: -1px;
  border-width: 0 2px 2px 0;
  border-radius: 0 0 4px 0;
}}

/* ── Needs-you card with gold corner accents ── */
.card-needs-you {{
  position: relative;
}}
.card-needs-you::before,
.card-needs-you::after {{
  content: '';
  position: absolute;
  width: 12px;
  height: 12px;
  border-color: var(--gold);
  border-style: solid;
  z-index: 2;
}}
.card-needs-you::before {{
  top: -1px; left: -1px;
  border-width: 2px 0 0 2px;
  border-radius: 4px 0 0 0;
}}
.card-needs-you::after {{
  bottom: -1px; right: -1px;
  border-width: 0 2px 2px 0;
  border-radius: 0 0 4px 0;
}}

/* ═══════════════════════════════════════════════════════════════════
   SCROLLBAR
═══════════════════════════════════════════════════════════════════ */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{
  background: var(--hue);
  border-radius: 99px;
  opacity: 0.5;
}}

/* ═══════════════════════════════════════════════════════════════════
   NAV BAR
═══════════════════════════════════════════════════════════════════ */
.nav-bar {{
  position: fixed;
  top: 0; left: 0; right: 0;
  height: var(--nav-h);
  z-index: 100;
  background: linear-gradient(
    180deg,
    rgba(255,255,255,0.92) 0%,
    rgba(255,255,255,0.78) 100%
  );
  backdrop-filter: blur(32px) saturate(200%) brightness(1.04);
  -webkit-backdrop-filter: blur(32px) saturate(200%) brightness(1.04);
  /* Bright edge highlight on top; subtle bottom separator */
  border-top: 1px solid rgba(255,255,255,1);
  border-bottom: 1px solid rgba(200,215,232,0.60);
  box-shadow:
    0 1px  0 rgba(255,255,255,0.9),
    0 4px 20px rgba(0,0,0,0.06),
    0 1px  3px rgba(0,0,0,0.04);
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 16px;
}}

.nav-wordmark {{
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.18em;
  color: var(--navy);
  white-space: nowrap;
  flex-shrink: 0;
  user-select: none;
}}

.nav-tabs {{
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  justify-content: center;
  overflow-x: auto;
  scrollbar-width: none;
}}
.nav-tabs::-webkit-scrollbar {{ display: none; }}

.nav-tab {{
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-2);
  cursor: pointer;
  border: none;
  background: transparent;
  white-space: nowrap;
  position: relative;
  user-select: none;
}}
.nav-tab:hover {{
  background: var(--hue-dim);
  color: var(--navy);
}}
.nav-tab.active {{
  background: var(--hue-dim);
  color: var(--hue);
}}
.nav-tab.active::after {{
  content: '';
  position: absolute;
  bottom: -2px; left: 20%; right: 20%;
  height: 2px;
  background: var(--hue);
  border-radius: 99px;
  transition: background 0.45s ease;
}}

.nav-tab svg {{
  width: 13px; height: 13px;
  flex-shrink: 0;
}}

.nav-right {{
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}}

.agent-badge-pill {{
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  color: var(--hue);
  background: var(--hue-dim);
  border: 1px solid rgba(var(--hue-rgb),0.2);
  border-radius: 99px;
  padding: 3px 10px;
  white-space: nowrap;
  transition: background 0.45s ease, color 0.45s ease, border-color 0.45s ease;
}}

.settings-btn {{
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  cursor: pointer;
  color: var(--text-2);
}}
.settings-btn:hover {{ background: var(--surface-hi); color: var(--navy); }}

/* ── Domain identity strip ── */
.domain-strip {{
  position: fixed;
  top: var(--nav-h); left: 0; right: 0;
  height: var(--strip-h);
  background: var(--hue);
  z-index: 99;
  transition: background 0.45s ease;
}}

/* ═══════════════════════════════════════════════════════════════════
   MAIN CONTENT
═══════════════════════════════════════════════════════════════════ */
.main {{
  position: relative;
  z-index: 1;
  padding-top: calc(var(--nav-h) + var(--strip-h) + 20px);
  padding-bottom: calc(var(--bar-h) + 24px);
  padding-left: 20px;
  padding-right: 20px;
  max-width: 1400px;
  margin: 0 auto;
}}

/* ── View sections ── */
.view {{ display: none; }}
.view.active {{ display: block; }}

/* ── View header ── */
.view-header {{
  margin-bottom: 20px;
}}
.view-title {{
  font-size: 20px;
  font-weight: 700;
  color: var(--navy);
  letter-spacing: -0.01em;
  display: flex;
  align-items: center;
  gap: 10px;
}}
.view-title-line {{
  flex: 1;
  height: 2px;
  background: linear-gradient(to right, var(--hue), transparent);
  border-radius: 99px;
  transition: background 0.45s ease;
}}
.view-subtitle {{
  font-size: 12px;
  color: var(--text-3);
  font-family: var(--font-mono);
  margin-top: 4px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}}

/* ── Section label ── */
.section-label {{
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-3);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}}
.section-label::after {{
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}}

/* ═══════════════════════════════════════════════════════════════════
   STATS STRIP
═══════════════════════════════════════════════════════════════════ */
.stats-strip {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}}
@media(max-width:640px) {{ .stats-strip {{ grid-template-columns: repeat(2,1fr); }} }}

.stat-tile {{
  padding: 16px 18px;
}}
.stat-label {{
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-3);
  margin-bottom: 6px;
}}
.stat-value {{
  font-family: var(--font-mono);
  font-size: 28px;
  font-weight: 500;
  color: var(--navy);
  line-height: 1;
}}
.stat-tile.accent .stat-value {{
  color: var(--hue);
  transition: color 0.45s ease;
}}
.stat-tile.gold-accent .stat-value {{
  color: var(--gold);
}}
.stat-sub {{
  font-size: 11px;
  color: var(--text-3);
  margin-top: 4px;
}}

/* ═══════════════════════════════════════════════════════════════════
   CARD GRID
═══════════════════════════════════════════════════════════════════ */
.card-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}}
.card-grid-2 {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}}
@media(max-width:700px) {{ .card-grid-2 {{ grid-template-columns: 1fr; }} }}

.card-inner {{
  padding: 18px 20px;
}}

.card-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}}
.card-title {{
  font-size: 12px;
  font-weight: 700;
  color: var(--navy);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  font-family: var(--font-mono);
}}

/* ═══════════════════════════════════════════════════════════════════
   STATUS DOTS
═══════════════════════════════════════════════════════════════════ */
.dot {{
  display: inline-block;
  width: 7px; height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}}
.dot-active {{
  background: var(--hue);
  box-shadow: 0 0 0 2px var(--hue-dim);
  animation: pulse-dot 2s ease-in-out infinite;
  transition: background 0.45s ease, box-shadow 0.45s ease;
}}
.dot-standby {{
  background: var(--text-3);
}}
.dot-success {{
  background: var(--success);
  box-shadow: 0 0 0 2px rgba(16,185,129,0.15);
}}
.dot-error {{
  background: var(--crimson);
  box-shadow: 0 0 0 2px rgba(196,30,58,0.15);
}}
.dot-gold {{
  background: var(--gold);
  box-shadow: 0 0 0 2px rgba(201,168,76,0.18);
}}

@keyframes pulse-dot {{
  0%,100% {{ opacity: 1; }}
  50%      {{ opacity: 0.45; }}
}}

/* ═══════════════════════════════════════════════════════════════════
   BADGES / PILLS
═══════════════════════════════════════════════════════════════════ */
.pill {{
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 99px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-family: var(--font-mono);
}}
.pill-hue  {{ background: var(--hue-dim); color: var(--hue); border: 1px solid rgba(var(--hue-rgb),0.25); transition: all 0.45s ease; }}
.pill-navy {{ background: rgba(10,22,40,0.08); color: var(--navy); border: 1px solid var(--border); }}
.pill-gold {{ background: rgba(201,168,76,0.12); color: var(--gold); border: 1px solid rgba(201,168,76,0.25); }}
.pill-crimson {{ background: rgba(196,30,58,0.08); color: var(--crimson); border: 1px solid rgba(196,30,58,0.2); }}
.pill-success {{ background: rgba(16,185,129,0.1); color: var(--success); border: 1px solid rgba(16,185,129,0.25); }}

/* ═══════════════════════════════════════════════════════════════════
   BUTTONS
═══════════════════════════════════════════════════════════════════ */
.btn {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  cursor: pointer;
  border: none;
  font-family: var(--font-sans);
  white-space: nowrap;
}}
.btn-hue {{
  background: var(--hue);
  color: #fff;
  box-shadow: 0 2px 8px var(--hue-glow);
  transition: background 0.45s ease, box-shadow 0.45s ease, opacity 0.2s;
}}
.btn-hue:hover {{ opacity: 0.88; }}
.btn-crimson {{
  background: var(--crimson);
  color: #fff;
  box-shadow: 0 2px 8px rgba(196,30,58,0.25);
}}
.btn-crimson:hover {{ opacity: 0.88; }}
.btn-outline {{
  background: var(--surface-hi);
  color: var(--text-2);
  border: 1px solid var(--border-hi);
}}
.btn-outline:hover {{ color: var(--navy); background: #fff; }}
.btn-sm {{ padding: 4px 10px; font-size: 11px; }}

/* ═══════════════════════════════════════════════════════════════════
   LIST ROWS
═══════════════════════════════════════════════════════════════════ */
.list-row {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}}
.list-row:last-child {{ border-bottom: none; padding-bottom: 0; }}
.list-row:first-child {{ padding-top: 0; }}

.list-row-name {{
  font-size: 13px;
  font-weight: 600;
  color: var(--navy);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}}
.list-row-sub {{
  font-size: 11px;
  color: var(--text-3);
  margin-top: 1px;
}}
.list-row-meta {{
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-3);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  text-align: right;
  flex-shrink: 0;
}}

/* ═══════════════════════════════════════════════════════════════════
   PROGRESS BAR
═══════════════════════════════════════════════════════════════════ */
.progress-bar {{
  height: 6px;
  background: var(--hue-dim);
  border-radius: 99px;
  overflow: hidden;
  margin-top: 8px;
  transition: background 0.45s ease;
}}
.progress-fill {{
  height: 100%;
  background: var(--hue);
  border-radius: 99px;
  transition: background 0.45s ease, width 0.6s ease;
}}

/* ── Pipeline segment bar ── */
.pipeline-bar {{
  display: flex;
  gap: 2px;
  margin-top: 10px;
}}
.pipeline-seg {{
  flex: 1;
  height: 6px;
  border-radius: 2px;
  background: var(--border);
}}
.pipeline-seg.done  {{ background: var(--hue); opacity: 0.7; transition: background 0.45s ease; }}
.pipeline-seg.current {{
  background: var(--hue);
  animation: pipeline-pulse 1.5s ease-in-out infinite;
  transition: background 0.45s ease;
}}
@keyframes pipeline-pulse {{
  0%,100% {{ opacity: 1; }}
  50%      {{ opacity: 0.4; }}
}}

/* ═══════════════════════════════════════════════════════════════════
   APPROVAL ITEM
═══════════════════════════════════════════════════════════════════ */
.approval-item {{
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}}
.approval-item:last-child {{ border-bottom: none; padding-bottom: 0; }}
.approval-item:first-child {{ padding-top: 0; }}

.approval-title {{
  font-size: 13px;
  font-weight: 600;
  color: var(--navy);
  margin-bottom: 4px;
}}
.approval-meta {{
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-3);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 8px;
}}
.approval-actions {{
  display: flex;
  gap: 8px;
}}

/* ═══════════════════════════════════════════════════════════════════
   AGENT BADGES
═══════════════════════════════════════════════════════════════════ */
.filter-strip {{
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}}
.filter-pill {{
  padding: 5px 12px;
  border-radius: 99px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-family: var(--font-mono);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-2);
  cursor: pointer;
}}
.filter-pill.active {{
  background: var(--hue-dim);
  color: var(--hue);
  border-color: rgba(var(--hue-rgb),0.3);
  transition: all 0.45s ease;
}}
.filter-pill:hover {{ background: var(--surface-hi); }}

.agent-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 10px;
}}

.agent-badge {{
  position: relative;
  background: linear-gradient(
    150deg,
    rgba(255,255,255,0.75) 0%,
    rgba(255,255,255,0.45) 100%
  );
  backdrop-filter: blur(24px) saturate(180%) brightness(1.03);
  -webkit-backdrop-filter: blur(24px) saturate(180%) brightness(1.03);
  border-top:    1px solid rgba(255,255,255,0.90);
  border-left:   1px solid rgba(255,255,255,0.75);
  border-right:  1px solid rgba(255,255,255,0.30);
  border-bottom: 1px solid rgba(255,255,255,0.25);
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04), 0 4px 16px rgba(0,0,0,0.05), inset 0 1px 0 rgba(255,255,255,0.95);
  padding: 12px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-left-width: 3px;
  border-left-style: solid;
  cursor: default;
}}
.agent-badge:hover {{
  box-shadow: 0 2px 8px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.9);
  transform: translateY(-1px);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}}

.agent-info {{ flex: 1; min-width: 0; }}
.agent-name {{
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  color: var(--navy);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.agent-title {{
  font-size: 10px;
  color: var(--text-3);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.agent-domain {{
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-3);
  margin-top: 1px;
}}
.agent-status {{
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;
}}
.agent-status-label {{
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}}
.agent-status-label.active {{ color: var(--hue); transition: color 0.45s ease; }}
.agent-status-label.standby {{ color: var(--text-3); }}

/* ═══════════════════════════════════════════════════════════════════
   HUDDLE VIEW
═══════════════════════════════════════════════════════════════════ */
.huddle-meta {{
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  padding: 10px 16px;
  background: rgba(255,255,255,0.5);
  backdrop-filter: blur(16px);
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.7);
  margin-bottom: 20px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.06em;
}}
.huddle-stat {{
  color: var(--text-secondary);
  display: flex; align-items: center; gap: 6px;
}}
.huddle-refresh-btn {{
  margin-left: auto;
  padding: 4px 14px;
  background: var(--brand-blue);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 10px;
  font-family: var(--font-mono);
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: opacity .2s;
}}
.huddle-refresh-btn:hover {{ opacity: .85; }}
.huddle-section {{ margin-bottom: 28px; }}
.huddle-section-label {{
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.15em;
  color: var(--text-secondary);
  text-transform: uppercase;
  margin-bottom: 10px;
  padding-left: 2px;
}}
.huddle-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
}}
.huddle-card {{
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  padding: 14px 16px;
  transition: box-shadow .2s;
}}
.huddle-card:hover {{ box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
.hc-header {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 10px;
}}
.hc-name {{
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 0.02em;
}}
.hc-domain {{
  font-size: 9px;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  margin-top: 2px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}}
.hc-source-badge {{
  font-size: 8px;
  font-family: var(--font-mono);
  padding: 2px 7px;
  border-radius: 4px;
  background: rgba(0,0,0,0.06);
  color: var(--text-secondary);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
}}
.hc-section {{ margin-bottom: 8px; }}
.hc-section-label {{
  font-family: var(--font-mono);
  font-size: 8px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-secondary);
  margin-bottom: 3px;
}}
.hc-text {{
  font-size: 11px;
  color: var(--text-primary);
  line-height: 1.5;
}}
.hc-needs {{
  font-size: 11px;
  color: var(--text-primary);
  line-height: 1.5;
}}
.hc-needs.has-need {{
  color: #b45309;
  background: rgba(250,204,21,0.08);
  padding: 4px 8px;
  border-radius: 6px;
  border-left: 3px solid #f59e0b;
}}
.hc-highlights {{
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}}
.hc-highlight-tag {{
  font-size: 9px;
  padding: 2px 7px;
  border-radius: 4px;
  background: rgba(99,102,241,0.1);
  color: var(--brand-blue);
  font-family: var(--font-mono);
}}
.hc-work-count {{
  font-size: 9px;
  font-family: var(--font-mono);
  color: var(--text-secondary);
  margin-top: 8px;
  border-top: 1px solid rgba(0,0,0,0.05);
  padding-top: 6px;
}}
/* Approvals needed */
.huddle-approval-list {{ display: flex; flex-direction: column; gap: 8px; margin-bottom: 8px; }}
.approval-item {{
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 8px;
  background: rgba(250,204,21,0.06);
  border: 1px solid rgba(250,204,21,0.3);
}}
.approval-item-agent {{
  font-size: 9px;
  font-family: var(--font-mono);
  font-weight: 700;
  color: var(--text-secondary);
  text-transform: uppercase;
  min-width: 80px;
}}
.approval-item-title {{ font-size: 12px; font-weight: 600; color: var(--text-primary); }}
.approval-item-desc {{ font-size: 10px; color: var(--text-secondary); margin-top: 2px; line-height: 1.4; }}
.approval-item-actions {{ margin-left: auto; display: flex; gap: 6px; flex-shrink: 0; }}
.approve-btn, .reject-btn {{
  padding: 4px 12px;
  border-radius: 5px;
  border: none;
  font-size: 10px;
  font-family: var(--font-mono);
  cursor: pointer;
  transition: opacity .2s;
}}
.approve-btn {{ background: #10b981; color: #fff; }}
.reject-btn {{ background: rgba(0,0,0,0.08); color: var(--text-secondary); }}
.approve-btn:hover, .reject-btn:hover {{ opacity: .8; }}
/* Passive income pipeline */
.pi-pipeline-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}}
.pi-card {{
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  border: 1px solid var(--glass-border);
  border-radius: 10px;
  padding: 12px 14px;
}}
.pi-card-status {{
  font-size: 8px;
  font-family: var(--font-mono);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 4px;
  display: inline-block;
  margin-bottom: 6px;
}}
.pi-status-dreamed {{ background: rgba(139,92,246,0.12); color: #7c3aed; }}
.pi-status-researching {{ background: rgba(59,130,246,0.12); color: #2563eb; }}
.pi-status-proposed {{ background: rgba(245,158,11,0.12); color: #b45309; }}
.pi-status-approved {{ background: rgba(16,185,129,0.12); color: #059669; }}
.pi-status-implementing {{ background: rgba(236,72,153,0.12); color: #db2777; }}
.pi-status-tracking {{ background: rgba(14,165,233,0.12); color: #0284c7; }}
.pi-status-closed {{ background: rgba(0,0,0,0.06); color: var(--text-secondary); }}
.pi-card-title {{ font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }}
.pi-card-idea {{ font-size: 10px; color: var(--text-secondary); line-height: 1.5; }}
.pi-empty {{
  padding: 24px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 12px;
  font-family: var(--font-mono);
  letter-spacing: 0.08em;
}}

/* Party Mode Bar */
.party-bar {{
  display: flex; align-items: center; gap: 12px;
  background: rgba(var(--accent-rgb, 139,92,246), 0.08);
  border: 1px solid rgba(var(--accent-rgb, 139,92,246), 0.2);
  border-radius: 10px; padding: 10px 16px; margin-bottom: 20px;
  font-size: 12px; color: var(--text-primary);
}}
.party-bar-indicator {{
  width: 8px; height: 8px; border-radius: 50%;
  background: #22c55e;
  animation: party-pulse 1.5s ease-in-out infinite;
  flex-shrink: 0;
}}
@keyframes party-pulse {{
  0%, 100% {{ opacity: 1; transform: scale(1); }}
  50% {{ opacity: 0.5; transform: scale(0.8); }}
}}
.party-bar-btn {{
  margin-left: auto; padding: 5px 12px; border-radius: 6px;
  background: rgba(var(--accent-rgb, 139,92,246), 0.15);
  border: 1px solid rgba(var(--accent-rgb, 139,92,246), 0.3);
  color: var(--text-primary); font-size: 11px; cursor: pointer;
  transition: background 0.2s;
}}
.party-bar-btn:hover {{ background: rgba(var(--accent-rgb, 139,92,246), 0.25); }}

/* Dossier Grid */
.dossier-grid {{
  display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
}}
.dossier-card {{
  background: var(--card-bg, rgba(255,255,255,0.05));
  border: 1px solid var(--card-border, rgba(255,255,255,0.08));
  border-radius: 12px; padding: 16px; cursor: pointer;
  transition: all 0.2s; position: relative;
}}
.dossier-card:hover {{
  border-color: rgba(var(--accent-rgb, 139,92,246), 0.4);
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
  transform: translateY(-1px);
}}
.dossier-card-status {{
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 9px; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; padding: 2px 7px; border-radius: 4px;
  margin-bottom: 8px;
}}
.dc-status-ready {{ background: rgba(34,197,94,0.15); color: #22c55e; }}
.dc-status-building {{ background: rgba(234,179,8,0.15); color: #eab308; }}
.dc-status-presented {{ background: rgba(148,163,184,0.15); color: #94a3b8; }}
.dossier-card-header-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
.dossier-qa-badge {{
  font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 4px;
  background: rgba(239,68,68,0.12); color: #ef4444;
  border: 1px solid rgba(239,68,68,0.25); cursor: help;
}}
.dossier-qa-ok {{
  font-size: 9px; font-weight: 600; padding: 2px 6px; border-radius: 4px;
  background: rgba(34,197,94,0.1); color: #22c55e;
  border: 1px solid rgba(34,197,94,0.2);
}}
.dossier-card-qa-warn {{
  border-color: rgba(239,68,68,0.3) !important;
}}
.dossier-card-qa-warn:hover {{
  border-color: rgba(239,68,68,0.5) !important;
}}
.dossier-qa-issues-block {{
  background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2);
  border-radius: 6px; padding: 10px 12px; margin-bottom: 14px;
}}
.dossier-qa-issues-title {{
  font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
  color: #ef4444; margin-bottom: 6px;
}}
.dossier-qa-issue-item {{
  font-size: 11px; color: rgba(220,230,255,0.75); margin-bottom: 3px;
  padding-left: 10px; position: relative;
}}
.dossier-qa-issue-item::before {{ content: "•"; position: absolute; left: 0; color: #ef4444; }}
.dossier-card-title {{ font-size: 13px; font-weight: 600; color: #1e293b; margin-bottom: 6px; }}
.dossier-card-summary {{ font-size: 11px; color: #475569; line-height: 1.5; margin-bottom: 10px; }}
.dossier-metrics {{
  display: flex; gap: 12px; flex-wrap: wrap;
}}
.dossier-metric {{
  font-size: 10px; color: #64748b;
}}
.dossier-metric strong {{ color: #1e293b; }}
.dossier-confidence-bar {{
  width: 100%; height: 3px; background: rgba(255,255,255,0.08);
  border-radius: 2px; margin-top: 10px; overflow: hidden;
}}
.dossier-confidence-fill {{
  height: 100%; border-radius: 2px;
  background: linear-gradient(90deg, #22c55e, #86efac);
  transition: width 0.6s ease;
}}
.dossier-card-actions {{
  display: flex; gap: 6px; margin-top: 12px;
}}
.dossier-read-btn {{
  flex: 1; padding: 6px; border-radius: 6px; font-size: 10px;
  background: rgba(15,23,42,0.05); border: 1px solid rgba(15,23,42,0.12);
  color: #475569; cursor: pointer; transition: all 0.2s;
  text-align: center;
}}
.dossier-read-btn:hover {{ background: rgba(15,23,42,0.1); color: #1e293b; }}
.dossier-approve-btn {{
  flex: 1; padding: 6px; border-radius: 6px; font-size: 10px;
  background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.25);
  color: #22c55e; cursor: pointer; transition: all 0.2s; text-align: center;
}}
.dossier-approve-btn:hover {{ background: rgba(34,197,94,0.2); }}

/* Dossier Modal */
.dossier-modal-overlay {{
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(0,0,0,0.7); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}}
.dossier-modal {{
  background: var(--surface-bg, #1a1a2e);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 16px; width: 100%; max-width: 720px;
  max-height: 85vh; overflow-y: auto; padding: 28px;
}}
.dossier-modal-header {{
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 20px;
}}
.dossier-modal-title {{ font-size: 18px; font-weight: 700; color: var(--text-primary); }}
.dossier-modal-close {{
  background: none; border: none; color: rgba(200,210,240,0.6);
  font-size: 20px; cursor: pointer; padding: 0 4px;
}}
.dossier-section-block {{ margin-bottom: 18px; }}
.dossier-section-heading {{
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.1em; color: var(--accent, #8b5cf6);
  margin-bottom: 6px; padding-bottom: 4px;
  border-bottom: 1px solid rgba(var(--accent-rgb, 139,92,246), 0.2);
}}
.dossier-section-text {{
  font-size: 12px; color: rgba(220,230,255,0.85); line-height: 1.7;
}}
.dossier-section-text h3 {{
  font-size: 13px; font-weight: 700; color: rgba(220,230,255,1);
  margin: 12px 0 4px; letter-spacing: 0.02em;
}}
.dossier-section-text h4 {{
  font-size: 12px; font-weight: 600; color: rgba(200,215,255,0.95);
  margin: 10px 0 3px;
}}
.dossier-section-text strong {{ color: rgba(240,245,255,1); font-weight: 600; }}
.dossier-section-text em {{ color: rgba(200,215,255,0.9); font-style: italic; }}
.dossier-section-text ul, .dossier-section-text ol {{
  margin: 6px 0; padding-left: 18px;
}}
.dossier-section-text li {{ margin-bottom: 3px; }}
.dossier-section-text p {{ margin: 0 0 8px; }}
.dossier-section-text p:last-child {{ margin-bottom: 0; }}
.dossier-sources-list {{
  font-size: 10px; color: rgba(180,190,220,0.7);
}}
.dossier-sources-list a {{ color: var(--accent, #8b5cf6); text-decoration: none; }}
.dossier-modal-actions {{
  display: flex; gap: 10px; margin-top: 20px; padding-top: 16px;
  border-top: 1px solid rgba(255,255,255,0.08);
}}
.dossier-modal-approve {{
  flex: 1; padding: 10px; border-radius: 8px;
  background: rgba(34,197,94,0.15); border: 1px solid rgba(34,197,94,0.3);
  color: #22c55e; font-size: 12px; font-weight: 600; cursor: pointer;
}}
.dossier-modal-pass {{
  flex: 1; padding: 10px; border-radius: 8px;
  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
  color: var(--text-secondary); font-size: 12px; cursor: pointer;
}}
/* ── Dossier chat / refinement panel ── */
.dossier-chat-panel {{
  margin-top: 20px; padding-top: 16px;
  border-top: 1px solid rgba(255,255,255,0.08);
}}
.dossier-chat-label {{
  font-size: 10px; font-weight: 700; color: rgba(180,195,230,0.7);
  text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px;
}}
.dossier-chat-row {{
  display: flex; gap: 8px;
}}
.dossier-chat-input {{
  flex: 1; padding: 8px 12px; border-radius: 8px; resize: none;
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
  color: rgba(220,230,255,0.9); font-size: 12px; font-family: inherit;
  line-height: 1.4; min-height: 38px; max-height: 90px;
  outline: none;
}}
.dossier-chat-input:focus {{ border-color: rgba(139,92,246,0.5); }}
.dossier-chat-input::placeholder {{ color: rgba(180,195,230,0.35); }}
.dossier-chat-send {{
  padding: 8px 14px; border-radius: 8px; cursor: pointer;
  background: rgba(139,92,246,0.2); border: 1px solid rgba(139,92,246,0.35);
  color: #a78bfa; font-size: 12px; font-weight: 600; white-space: nowrap;
  align-self: flex-end;
}}
.dossier-chat-send:hover {{ background: rgba(139,92,246,0.3); }}
.dossier-chat-send:disabled {{ opacity: 0.4; cursor: not-allowed; }}
.dossier-chat-response {{
  margin-top: 10px; padding: 10px 12px; border-radius: 8px;
  background: rgba(139,92,246,0.06); border: 1px solid rgba(139,92,246,0.15);
  font-size: 12px; color: rgba(220,230,255,0.85); line-height: 1.7;
  display: none;
}}
.dossier-chat-response.visible {{ display: block; }}
.dossier-chat-response h3 {{
  font-size: 12px; font-weight: 700; color: rgba(220,230,255,1); margin: 10px 0 3px;
}}
.dossier-chat-response h4 {{
  font-size: 11px; font-weight: 600; margin: 8px 0 2px;
}}
.dossier-chat-response strong {{ color: rgba(240,245,255,1); font-weight: 600; }}
.dossier-chat-response ul, .dossier-chat-response ol {{
  margin: 4px 0; padding-left: 18px;
}}
.dossier-chat-response li {{ margin-bottom: 2px; }}
.dossier-chat-response p {{ margin: 0 0 6px; }}

/* ── Expandable text ── */
.expand-toggle {{
  cursor: pointer;
}}
.expand-toggle:hover {{
  opacity: 0.85;
}}

/* ═══════════════════════════════════════════════════════════════════
   AGENTS RUNTIME VIEW
═══════════════════════════════════════════════════════════════════ */
.runtime-status-bar {{
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  padding: 10px 16px;
  background: rgba(255,255,255,0.5);
  backdrop-filter: blur(16px);
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.7);
  margin-bottom: 20px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.06em;
}}
.runtime-stat {{ display: flex; align-items: center; gap: 6px; }}
.runtime-stat-val {{ font-size: 16px; font-weight: 700; font-family: var(--font-mono); color: var(--navy); }}
.runtime-stat-lbl {{ color: var(--text-3); }}
.runtime-divider {{ width: 1px; height: 24px; background: rgba(0,0,0,0.08); }}
.runtime-mode-badge {{
  font-family: var(--font-mono); font-size: 9px; letter-spacing: 0.1em;
  padding: 3px 8px; border-radius: 4px;
  background: rgba(0,180,255,0.12); color: var(--hue);
  border: 1px solid rgba(0,180,255,0.2);
  text-transform: uppercase;
}}
.quiet-badge {{
  font-family: var(--font-mono); font-size: 9px; letter-spacing: 0.1em;
  padding: 3px 8px; border-radius: 4px;
  background: rgba(124,58,237,0.12); color: #7c3aed;
  border: 1px solid rgba(124,58,237,0.2);
  text-transform: uppercase;
}}
.runtime-last-tick {{ margin-left: auto; color: var(--text-3); font-size: 9px; }}

.runtime-section-label {{
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-3);
  margin: 0 0 12px 2px;
  display: flex;
  align-items: center;
  gap: 8px;
}}
.runtime-section-label::after {{
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(0,0,0,0.07);
}}

.runtime-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 14px;
  margin-bottom: 32px;
}}

.agent-runtime-card {{
  position: relative;
  background: linear-gradient(150deg, rgba(255,255,255,0.78) 0%, rgba(255,255,255,0.46) 100%);
  backdrop-filter: blur(24px) saturate(180%) brightness(1.03);
  -webkit-backdrop-filter: blur(24px) saturate(180%) brightness(1.03);
  border-top:    1px solid rgba(255,255,255,0.92);
  border-left:   1px solid rgba(255,255,255,0.80);
  border-right:  1px solid rgba(255,255,255,0.30);
  border-bottom: 1px solid rgba(255,255,255,0.25);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05), 0 6px 20px rgba(0,0,0,0.06);
  padding: 14px 16px;
  border-left-width: 3px;
  border-left-style: solid;
  border-left-color: rgba(0,180,255,0.5);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}}
.agent-runtime-card:hover {{
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.08), 0 10px 32px rgba(0,0,0,0.08);
}}
.agent-runtime-card.state-awake  {{ border-left-color: #22c55e; }}
.agent-runtime-card.state-idle   {{ border-left-color: rgba(100,116,139,0.5); }}
.agent-runtime-card.state-blocked {{ border-left-color: #ef4444; }}

.arc-header {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; margin-bottom: 8px; }}
.arc-names {{ flex: 1; min-width: 0; }}
.arc-label {{
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--navy);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}}
.arc-id {{ font-size: 10px; color: var(--text-3); margin-top: 1px; font-family: var(--font-mono); }}

.state-badge {{
  flex-shrink: 0;
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: 4px;
  white-space: nowrap;
}}
.state-badge.awake   {{ background: rgba(34,197,94,0.15);  color: #16a34a; border: 1px solid rgba(34,197,94,0.25); }}
.state-badge.idle    {{ background: rgba(100,116,139,0.1); color: #64748b; border: 1px solid rgba(100,116,139,0.2); }}
.state-badge.blocked {{ background: rgba(239,68,68,0.12);  color: #dc2626; border: 1px solid rgba(239,68,68,0.2); }}

.arc-reason {{
  font-size: 12px;
  color: var(--text-2);
  line-height: 1.5;
  margin-bottom: 9px;
  font-style: italic;
}}

.arc-owns {{
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 10px;
}}
.arc-own-tag {{
  font-size: 9px;
  font-family: var(--font-mono);
  background: rgba(0,0,0,0.055);
  color: var(--text-2);
  padding: 2px 7px;
  border-radius: 3px;
  letter-spacing: 0.04em;
  white-space: nowrap;
}}

.arc-block-warning {{
  background: rgba(239,68,68,0.08);
  border: 1px solid rgba(239,68,68,0.2);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 10px;
  color: #dc2626;
  font-family: var(--font-mono);
  margin-bottom: 9px;
}}

.arc-footer {{
  display: flex;
  gap: 16px;
  padding-top: 9px;
  border-top: 1px solid rgba(0,0,0,0.055);
  flex-wrap: wrap;
}}
.arc-time {{
  display: flex;
  flex-direction: column;
  gap: 1px;
}}
.arc-time-lbl {{ font-size: 8px; font-family: var(--font-mono); color: var(--text-3); letter-spacing: 0.08em; text-transform: uppercase; }}
.arc-time-val {{ font-size: 11px; font-family: var(--font-mono); color: var(--text-2); font-weight: 500; }}
.arc-time-val.overdue {{ color: #dc2626; }}
.arc-cadence {{ margin-left: auto; font-size: 9px; color: var(--text-3); font-family: var(--font-mono); align-self: flex-end; }}

.roster-toggle {{
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  background: rgba(255,255,255,0.6);
  border: 1px solid rgba(0,0,0,0.1);
  border-radius: 6px;
  padding: 5px 12px;
  cursor: pointer;
  color: var(--text-2);
  transition: background 0.15s;
}}
.roster-toggle:hover {{ background: rgba(255,255,255,0.85); }}

/* Domain left-border colors — fixed, not hue */
.domain-command     {{ border-left-color: #0A1628; }}
.domain-engineering {{ border-left-color: #F59E0B; }}
.domain-intelligence{{ border-left-color: #3B82F6; }}
.domain-vision      {{ border-left-color: #06B6D4; }}
.domain-publishing  {{ border-left-color: #D97706; }}
.domain-power       {{ border-left-color: #EF4444; }}
.domain-analysis    {{ border-left-color: #8B5CF6; }}
.domain-finance     {{ border-left-color: #10B981; }}
.domain-scheduling  {{ border-left-color: #7C3AED; }}
.domain-interface   {{ border-left-color: #00B4FF; }}
.domain-workshop    {{ border-left-color: #EA580C; }}
.domain-operations  {{ border-left-color: #64748B; }}
.domain-chronicle   {{ border-left-color: #3B82F6; }}

/* ═══════════════════════════════════════════════════════════════════
   INTELLIGENCE VIEW
═══════════════════════════════════════════════════════════════════ */
.service-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px,1fr));
  gap: 10px;
  margin-bottom: 20px;
}}
.service-card {{
  padding: 14px 16px;
}}
.service-name {{
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  color: var(--navy);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 7px;
}}
.service-detail {{
  font-size: 11px;
  color: var(--text-3);
}}

/* LLM Ladder */
.llm-ladder {{
  display: flex;
  align-items: center;
  gap: 0;
  flex-wrap: wrap;
  padding: 18px 20px;
}}
.llm-node {{
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  border-radius: 8px;
  min-width: 110px;
}}
.llm-node.current {{
  background: var(--hue-dim);
  border: 1px solid rgba(var(--hue-rgb),0.3);
  transition: background 0.45s ease, border-color 0.45s ease;
}}
.llm-label {{
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  color: var(--text-2);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}}
.llm-node.current .llm-label {{ color: var(--hue); transition: color 0.45s ease; }}
.llm-tier {{
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--text-3);
  letter-spacing: 0.06em;
}}
.llm-arrow {{
  font-size: 14px;
  color: var(--text-3);
  padding: 0 4px;
  flex-shrink: 0;
}}

/* Bridge connections */
.bridge-row {{
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}}
.bridge-row:last-child {{ border-bottom: none; }}
.bridge-name {{
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 500;
  color: var(--navy);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}}
.bridge-url {{
  font-size: 11px;
  color: var(--text-3);
  margin-left: auto;
}}

/* ═══════════════════════════════════════════════════════════════════
   CHRONICLE SEARCH
═══════════════════════════════════════════════════════════════════ */
.search-wrap {{
  position: relative;
  margin-bottom: 18px;
}}
.search-input {{
  width: 100%;
  padding: 11px 16px 11px 40px;
  background: var(--surface-hi);
  border: 1px solid var(--border);
  border-radius: 10px;
  font-size: 14px;
  font-family: var(--font-sans);
  color: var(--text-1);
  outline: none;
}}
.search-input:focus {{
  border-color: var(--hue);
  box-shadow: 0 0 0 3px var(--hue-dim);
  transition: border-color 0.2s, box-shadow 0.2s;
}}
.search-icon {{
  position: absolute;
  left: 13px; top: 50%;
  transform: translateY(-50%);
  color: var(--text-3);
  width: 16px; height: 16px;
  pointer-events: none;
}}

/* Chronicle entry */
.chronicle-entry {{
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}}
.chronicle-entry:last-child {{ border-bottom: none; padding-bottom: 0; }}
.chronicle-ts {{
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-3);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 4px;
}}
.chronicle-text {{
  font-size: 13px;
  color: var(--text-1);
  margin-bottom: 6px;
  line-height: 1.4;
}}
.chronicle-tags {{
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}}

.tag-cloud {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 16px 20px;
}}
.tag-chip {{
  padding: 4px 10px;
  border-radius: 99px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-2);
  background: var(--hue-dim);
  border: 1px solid rgba(var(--hue-rgb),0.2);
  cursor: pointer;
  transition: all 0.45s ease;
}}
.tag-chip:hover {{ background: var(--hue); color: #fff; }}

/* ═══════════════════════════════════════════════════════════════════
   CAMERA GRID (VISION)
═══════════════════════════════════════════════════════════════════ */
.camera-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
}}
.camera-cell {{
  padding: 20px;
  min-height: 140px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-align: center;
}}
.camera-icon {{
  color: var(--hue);
  transition: color 0.45s ease;
}}
.camera-label {{
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--navy);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}}
.camera-ts {{
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-3);
}}

/* ═══════════════════════════════════════════════════════════════════
   CHAT CONVERSATION
═══════════════════════════════════════════════════════════════════ */
.chat-area {{
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 0 0 24px 0;
  min-height: 200px;
  max-height: calc(100vh - 220px);
  overflow-y: auto;
  scroll-behavior: smooth;
}}
.chat-empty {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
  opacity: 0.5;
}}
.chat-empty-icon {{ font-size: 36px; }}
.chat-empty-text {{ font-family: var(--font-mono); font-size: 12px; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.08em; }}

.msg-row {{
  display: flex;
  gap: 12px;
  align-items: flex-start;
}}
.msg-row.user {{
  flex-direction: row-reverse;
}}
.msg-avatar {{
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
  font-family: var(--font-mono);
}}
.msg-row.user .msg-avatar {{
  background: var(--hue);
  color: #fff;
}}
.msg-row.jarvis .msg-avatar {{
  background: var(--navy);
  color: var(--gold);
  font-size: 10px;
  letter-spacing: 0.05em;
}}
.msg-bubble {{
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}}
.msg-row.user .msg-bubble {{
  background: var(--hue);
  color: #fff;
  border-radius: 14px 4px 14px 14px;
}}
.msg-row.jarvis .msg-bubble {{
  background: linear-gradient(150deg, rgba(255,255,255,0.82) 0%, rgba(255,255,255,0.55) 100%);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-top: 1px solid rgba(255,255,255,0.90);
  border-left: 1px solid rgba(255,255,255,0.75);
  border-right: 1px solid rgba(255,255,255,0.30);
  border-bottom: 1px solid rgba(255,255,255,0.25);
  color: var(--text-1);
  border-radius: 4px 14px 14px 14px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05), inset 0 1px 0 rgba(255,255,255,0.95);
}}
.msg-meta {{
  font-size: 10px;
  color: var(--text-3);
  font-family: var(--font-mono);
  margin-top: 4px;
  padding: 0 4px;
}}
.msg-row.user .msg-meta {{ text-align: right; }}

/* Typing indicator */
.msg-typing .msg-bubble {{
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 14px 18px;
}}
.typing-dot {{
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-3);
  animation: typingBounce 1.2s ease-in-out infinite;
}}
.typing-dot:nth-child(2) {{ animation-delay: 0.2s; }}
.typing-dot:nth-child(3) {{ animation-delay: 0.4s; }}
@keyframes typingBounce {{
  0%, 80%, 100% {{ transform: translateY(0); opacity: 0.4; }}
  40% {{ transform: translateY(-6px); opacity: 1; }}
}}

/* ═══════════════════════════════════════════════════════════════════
   COMMAND BAR
═══════════════════════════════════════════════════════════════════ */
.command-bar {{
  position: fixed;
  bottom: 0; left: 0; right: 0;
  height: auto;
  min-height: var(--bar-h);
  z-index: 100;
  background: linear-gradient(
    0deg,
    rgba(255,255,255,0.96) 0%,
    rgba(255,255,255,0.82) 100%
  );
  backdrop-filter: blur(32px) saturate(200%) brightness(1.03);
  -webkit-backdrop-filter: blur(32px) saturate(200%) brightness(1.03);
  /* Bright top gleam on command bar */
  border-top: 1px solid rgba(255,255,255,0.95);
  border-bottom: 1px solid rgba(255,255,255,1);
  box-shadow:
    0 -1px  0 rgba(200,215,232,0.50),
    0 -4px 20px rgba(0,0,0,0.05),
    inset 0 1px 0 rgba(255,255,255,1);
  padding: 8px 20px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}}

.cmd-chips {{
  display: flex;
  gap: 6px;
  flex-wrap: nowrap;
  overflow-x: auto;
  scrollbar-width: none;
}}
.cmd-chips::-webkit-scrollbar {{ display: none; }}

.cmd-chip {{
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 99px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-2);
  background: var(--surface);
  border: 1px solid var(--border);
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
}}
.cmd-chip:hover {{
  background: var(--hue-dim);
  color: var(--hue);
  border-color: rgba(var(--hue-rgb),0.3);
  transition: all 0.2s;
}}

.cmd-row {{
  display: flex;
  align-items: center;
  gap: 8px;
}}

.cmd-input {{
  flex: 1;
  padding: 10px 14px;
  background: var(--surface);
  border: 1px solid var(--border-hi);
  border-radius: 10px;
  font-size: 14px;
  font-family: var(--font-sans);
  color: var(--text-1);
  outline: none;
  min-width: 0;
}}
.cmd-input::placeholder {{ color: var(--text-3); }}
.cmd-input:focus {{
  border-color: var(--hue);
  box-shadow: 0 0 0 3px var(--hue-dim);
  transition: border-color 0.2s, box-shadow 0.2s;
}}

.cmd-mic {{
  width: 38px; height: 38px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  color: var(--text-2);
  flex-shrink: 0;
}}
.cmd-mic:hover {{ background: var(--surface-hi); color: var(--navy); }}

.cmd-send {{
  height: 38px;
  padding: 0 18px;
  border-radius: 10px;
  border: none;
  background: var(--hue);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-family: var(--font-mono);
  cursor: pointer;
  box-shadow: 0 2px 8px var(--hue-glow);
  flex-shrink: 0;
  transition: background 0.45s ease, box-shadow 0.45s ease, opacity 0.2s;
}}
.cmd-send:hover {{ opacity: 0.88; }}

/* ═══════════════════════════════════════════════════════════════════
   TOAST
═══════════════════════════════════════════════════════════════════ */
#toast-wrap {{
  position: fixed;
  top: 80px; right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}}
.toast {{
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  color: #fff;
  box-shadow: 0 4px 24px rgba(0,0,0,0.15);
  animation: toast-in 0.3s ease;
  pointer-events: auto;
}}
.toast-info    {{ background: var(--hue); }}
.toast-success {{ background: var(--success); }}
.toast-error   {{ background: var(--crimson); }}
@keyframes toast-in {{
  from {{ opacity: 0; transform: translateX(20px); }}
  to   {{ opacity: 1; transform: translateX(0); }}
}}

/* ═══════════════════════════════════════════════════════════════════
   SETTINGS MODAL
═══════════════════════════════════════════════════════════════════ */
.modal-overlay {{
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(10,22,40,0.55);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}}
.modal-overlay.hidden {{ display: none; }}

.modal {{
  position: relative;
  background: linear-gradient(
    155deg,
    rgba(255,255,255,0.97) 0%,
    rgba(255,255,255,0.88) 50%,
    rgba(255,255,255,0.82) 100%
  );
  backdrop-filter: blur(40px) saturate(220%) brightness(1.05);
  -webkit-backdrop-filter: blur(40px) saturate(220%) brightness(1.05);
  border-top:    1px solid rgba(255,255,255,1);
  border-left:   1px solid rgba(255,255,255,0.90);
  border-right:  1px solid rgba(255,255,255,0.40);
  border-bottom: 1px solid rgba(255,255,255,0.35);
  border-radius: 18px;
  box-shadow:
    0 24px 64px rgba(0,0,0,0.16),
    0  8px 24px rgba(0,0,0,0.10),
    inset 0 1px 0 rgba(255,255,255,1),
    inset 1px 0 0 rgba(255,255,255,0.60);
  max-width: 480px;
  width: 100%;
  padding: 28px 28px 24px;
}}
.modal-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}}
.modal-title {{
  font-size: 16px;
  font-weight: 700;
  color: var(--navy);
  letter-spacing: -0.01em;
}}
.modal-close {{
  width: 30px; height: 30px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  color: var(--text-2);
  font-size: 16px;
}}
.modal-close:hover {{ background: var(--surface-hi); color: var(--navy); }}

.theme-cards {{
  display: flex;
  gap: 12px;
}}
.theme-card {{
  flex: 1;
  border-radius: 12px;
  border: 2px solid var(--border);
  padding: 16px;
  cursor: pointer;
  text-align: center;
  background: var(--surface);
}}
.theme-card:hover {{ border-color: var(--hue); }}
.theme-card.current {{ border-color: var(--hue); background: var(--hue-dim); }}
.theme-preview {{
  height: 60px;
  border-radius: 8px;
  margin-bottom: 10px;
}}
.theme-preview-classic  {{ background: linear-gradient(135deg, #0A1628 60%, #00B4FF 100%); }}
.theme-preview-nexus    {{ background: linear-gradient(135deg, #0D1117 60%, #7C3AED 100%); }}
.theme-preview-glass    {{ background: linear-gradient(135deg, #EEF2F7 60%, rgba(0,180,255,0.3) 100%); border: 1px solid var(--border); }}
.theme-name {{
  font-size: 12px;
  font-weight: 700;
  color: var(--navy);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-family: var(--font-mono);
}}
.theme-desc {{
  font-size: 11px;
  color: var(--text-3);
  margin-top: 2px;
}}

/* ═══════════════════════════════════════════════════════════════════
   SKELETON LOADER
═══════════════════════════════════════════════════════════════════ */
.skel {{
  background: linear-gradient(90deg, var(--border) 25%, rgba(255,255,255,0.5) 50%, var(--border) 75%);
  background-size: 200% 100%;
  animation: skel-shine 1.4s ease infinite;
  border-radius: 4px;
}}
@keyframes skel-shine {{
  from {{ background-position: 200% center; }}
  to   {{ background-position: -200% center; }}
}}

/* ── Misc ── */
.mono {{ font-family: var(--font-mono); }}
.text-1 {{ color: var(--text-1); }}
.text-2 {{ color: var(--text-2); }}
.text-3 {{ color: var(--text-3); }}
.mt-0 {{ margin-top: 0; }}
.mb-0 {{ margin-bottom: 0; }}
.gap-4 {{ gap: 4px; }}
.gap-8 {{ gap: 8px; }}
.flex {{ display: flex; }}
.items-center {{ align-items: center; }}
.justify-between {{ justify-content: space-between; }}

/* ═══════════════════════════════════════════════════════════════════
   OVERVIEW QUICK-CARDS (email/calendar)
═══════════════════════════════════════════════════════════════════ */
.card-hdr {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 16px 10px;
  border-bottom: 1px solid var(--border);
}}
.card-icon {{
  font-size: 16px;
  flex-shrink: 0;
}}
.card-badge {{
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  color: var(--hue);
  background: var(--hue-dim);
  border: 1px solid rgba(var(--hue-rgb),0.25);
  border-radius: 99px;
  padding: 2px 8px;
  transition: all 0.45s ease;
}}
.card-body {{ padding: 10px 16px 14px; }}
.card-row {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
}}
.card-row .lbl {{
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-3);
}}
.card-row .val {{
  font-size: 14px;
  font-weight: 600;
  color: var(--navy);
}}
.card-cta {{
  margin-top: 10px;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  color: var(--hue);
  letter-spacing: 0.06em;
  transition: color 0.45s ease;
}}
.next-event-preview {{
  font-size: 12px;
  color: var(--text-2);
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}

/* ═══════════════════════════════════════════════════════════════════
   VIEW HEADER WITH ACTIONS
═══════════════════════════════════════════════════════════════════ */
.view-header {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
  gap: 12px;
}}
.view-header > div:first-child {{ flex: 1; min-width: 0; }}
.view-sub {{
  font-size: 12px;
  color: var(--text-3);
  font-family: var(--font-mono);
  margin-top: 2px;
  letter-spacing: 0.04em;
}}
.view-actions {{
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}}
.btn-ghost {{
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-2);
  cursor: pointer;
  font-family: var(--font-sans);
}}
.btn-ghost:hover {{ background: var(--surface-hi); color: var(--navy); }}
.btn-primary {{
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  border: none;
  background: var(--hue);
  color: #fff;
  cursor: pointer;
  font-family: var(--font-sans);
  box-shadow: 0 2px 8px var(--hue-glow);
  transition: background 0.45s ease, box-shadow 0.45s ease, opacity 0.2s;
}}
.btn-primary:hover {{ opacity: 0.88; }}

/* ═══════════════════════════════════════════════════════════════════
   STAT ROW (email / calendar stats strip)
═══════════════════════════════════════════════════════════════════ */
.stat-row {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}}
.stat-card {{
  padding: 14px 16px;
  background: linear-gradient(
    150deg,
    rgba(255,255,255,0.78) 0%,
    rgba(255,255,255,0.48) 100%
  );
  border-top:    1px solid rgba(255,255,255,0.92);
  border-left:   1px solid rgba(255,255,255,0.78);
  border-right:  1px solid rgba(255,255,255,0.30);
  border-bottom: 1px solid rgba(255,255,255,0.25);
  border-radius: 12px;
  backdrop-filter: blur(24px) saturate(200%) brightness(1.03);
  -webkit-backdrop-filter: blur(24px) saturate(200%) brightness(1.03);
  box-shadow:
    0 2px 8px rgba(0,0,0,0.04),
    inset 0 1px 0 rgba(255,255,255,0.95);
}}
.stat-card.accent .stat-num {{ color: var(--hue); transition: color 0.45s ease; }}
.stat-num {{
  font-family: var(--font-mono);
  font-size: 28px;
  font-weight: 500;
  color: var(--navy);
  line-height: 1;
}}
.stat-lbl {{
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-3);
  margin-top: 4px;
}}

/* ═══════════════════════════════════════════════════════════════════
   EMAIL VIEW
═══════════════════════════════════════════════════════════════════ */
.email-list {{ display:flex; flex-direction:column; gap:2px; margin-top:12px; }}
.email-item {{ display:grid; grid-template-columns:8px 1fr auto; gap:12px; align-items:start; padding:12px 16px; background:var(--surface); border:1px solid var(--border); border-radius:10px; cursor:pointer; transition:background 0.15s; }}
.email-item:hover {{ background:var(--surface-hi); }}
.email-item.unread {{ border-left:3px solid var(--hue); }}
.email-source-dot {{ width:8px; height:8px; border-radius:50%; margin-top:4px; flex-shrink:0; }}
.email-source-dot.gmail {{ background:#EA4335; }}
.email-source-dot.outlook {{ background:#0078D4; }}
.email-from {{ font-size:12px; font-weight:600; color:var(--text-2); font-family:var(--font-mono); text-transform:uppercase; letter-spacing:0.04em; }}
.email-subject {{ font-size:14px; font-weight:500; color:var(--text-1); margin:2px 0; }}
.email-item.unread .email-subject {{ font-weight:700; color:var(--navy); }}
.email-snippet {{ font-size:12px; color:var(--text-3); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.email-time {{ font-size:11px; color:var(--text-3); font-family:var(--font-mono); white-space:nowrap; }}
.email-importance {{ font-size:11px; font-weight:700; color:var(--crimson); margin-top:4px; }}
.email-subject.flagged::after {{ content:'🚩'; margin-left:6px; font-size:11px; }}
.source-tabs {{ display:flex; gap:8px; margin:16px 0 0; }}
.source-tab {{ padding:6px 14px; border-radius:20px; font-size:12px; font-weight:600; border:1px solid var(--border); background:transparent; cursor:pointer; color:var(--text-2); transition:all 0.2s; }}
.source-tab.active {{ background:var(--hue); color:white; border-color:var(--hue); }}
.source-dot {{ display:inline-block; width:6px; height:6px; border-radius:50%; margin-right:4px; }}
.source-dot.gmail {{ background:#EA4335; }}
.source-dot.outlook {{ background:#0078D4; }}
.source-dot.cozi {{ background:#7C3AED; }}
.loading-state {{ padding:24px; text-align:center; color:var(--text-3); font-size:13px; font-family:var(--font-mono); }}

/* ═══════════════════════════════════════════════════════════════════
   CALENDAR VIEW
═══════════════════════════════════════════════════════════════════ */
.event-list {{ display:flex; flex-direction:column; gap:2px; padding:4px 0; }}
.event-item {{ display:grid; grid-template-columns:80px 1fr auto; gap:12px; align-items:center; padding:10px 16px; border-radius:8px; transition:background 0.15s; }}
.event-item:hover {{ background:rgba(0,0,0,0.03); }}
.event-time-col {{ display:flex; flex-direction:column; gap:4px; }}
.event-time {{ font-size:11px; font-family:var(--font-mono); color:var(--text-3); font-weight:500; }}
.event-title {{ font-size:14px; font-weight:500; color:var(--text-1); }}
.event-location {{ font-size:11px; color:var(--text-3); margin-top:2px; }}
.event-duration {{ font-size:11px; color:var(--text-3); font-family:var(--font-mono); white-space:nowrap; }}
.event-source-dot {{ width:6px; height:6px; border-radius:50%; margin-top:2px; flex-shrink:0; }}
.event-source-dot.google {{ background:#4285F4; }}
.event-source-dot.outlook {{ background:#0078D4; }}
.event-source-dot.cozi {{ background:#7C3AED; }}
.cal-legend {{ display:flex; gap:16px; margin-top:16px; padding:12px; flex-wrap:wrap; }}
.legend-item {{ font-size:11px; color:var(--text-3); display:flex; align-items:center; gap:6px; }}
.empty-state {{ padding:24px 16px; text-align:center; color:var(--text-3); font-size:12px; font-family:var(--font-mono); }}

/* ═══════════════════════════════════════════════════════════════════
   HOME PROJECTS (in publishing view)
═══════════════════════════════════════════════════════════════════ */
.project-item {{
  display:grid;
  grid-template-columns:1fr auto;
  gap:12px;
  align-items:start;
  padding:12px 0;
  border-bottom:1px solid var(--border);
}}
.project-item:last-child {{ border-bottom:none; padding-bottom:0; }}
.project-item:first-child {{ padding-top:0; }}
.project-name {{ font-size:13px; font-weight:600; color:var(--navy); }}
.project-meta {{ font-family:var(--font-mono); font-size:10px; color:var(--text-3); text-transform:uppercase; letter-spacing:0.06em; margin-top:2px; }}
.project-track {{ display:inline-block; padding:2px 7px; border-radius:99px; font-size:9px; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; font-family:var(--font-mono); }}
.track-revenue {{ background:rgba(16,185,129,0.1); color:var(--success); border:1px solid rgba(16,185,129,0.25); }}
.track-savings {{ background:rgba(59,130,246,0.1); color:#3B82F6; border:1px solid rgba(59,130,246,0.25); }}
.track-ops {{ background:rgba(148,163,184,0.15); color:var(--text-2); border:1px solid var(--border); }}
.project-value {{ font-family:var(--font-mono); font-size:12px; font-weight:600; color:var(--navy); text-align:right; }}
.project-value-lbl {{ font-size:9px; color:var(--text-3); letter-spacing:0.06em; text-transform:uppercase; }}

  </style>
</head>
<body>

<!-- ═══════════════════════════════════════════════════════════════════
     NAV BAR
══════════════════════════════════════════════════════════════════════ -->
<nav class="nav-bar">
  <span class="nav-wordmark">J·A·R·V·I·S</span>

  <div class="nav-tabs" id="nav-tabs">
    <button class="nav-tab" data-view="chat" onclick="switchView('chat')">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 2h12v9H9l-3 3v-3H2z"/></svg>
      Chat
    </button>
    <button class="nav-tab" data-view="overview" onclick="switchView('overview')">
      <svg viewBox="0 0 16 16" fill="currentColor"><rect x="1" y="1" width="6" height="6" rx="1"/><rect x="9" y="1" width="6" height="6" rx="1"/><rect x="1" y="9" width="6" height="6" rx="1"/><rect x="9" y="9" width="6" height="6" rx="1"/></svg>
      Overview
    </button>
    <button class="nav-tab" data-view="forge" onclick="switchView('forge')">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 2v12M4 6l4-4 4 4M3 14h10"/></svg>
      Forge
    </button>
    <button class="nav-tab" data-view="vision" onclick="switchView('vision')">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="2.5"/><path d="M1 8C2.5 4 5 2 8 2s5.5 2 7 6c-1.5 4-4 6-7 6S2.5 12 1 8z"/></svg>
      Vision
    </button>
    <button class="nav-tab" data-view="catalyst" onclick="switchView('catalyst')">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 1L7 9h5L7 15"/></svg>
      Catalyst
    </button>
    <button class="nav-tab" data-view="chronicle" onclick="switchView('chronicle')">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="12" height="12" rx="1"/><path d="M5 6h6M5 9h4"/></svg>
      Chronicle
    </button>
    <button class="nav-tab" data-view="publishing" onclick="switchView('publishing')">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 1h8v14H4zM7 1v14"/></svg>
      Publishing
    </button>
    <button class="nav-tab" data-view="workshop" onclick="switchView('workshop')">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="9" width="12" height="5" rx="1"/><path d="M5 9V6a3 3 0 016 0v3"/><circle cx="8" cy="4" r="1.5"/></svg>
      Workshop
    </button>
    <button class="nav-tab" data-view="huddle" onclick="switchView('huddle')">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="4" cy="6" r="2"/><circle cx="12" cy="6" r="2"/><circle cx="8" cy="4" r="2"/><path d="M1 14c0-2 1.5-3 3-3h2m4 0h2c1.5 0 3 1 3 3"/><path d="M6 11c0-1.5 1-2.5 2-2.5s2 1 2 2.5"/></svg>
      Huddle
    </button>
    <button class="nav-tab" data-view="agents" onclick="switchView('agents')">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="6" cy="5" r="2.5"/><circle cx="11" cy="5" r="2"/><path d="M1 14c0-3 2-4.5 5-4.5s5 1.5 5 4.5"/><path d="M12 9.5c2 .5 3 1.5 3 3.5"/></svg>
      Agents
    </button>
    <button class="nav-tab" data-view="intelligence" onclick="switchView('intelligence')">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 2a5 5 0 100 12A5 5 0 008 2z"/><path d="M8 6v2l1.5 1.5"/></svg>
      Intel
    </button>
    <button class="nav-tab" data-view="email" onclick="switchView('email')">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1" y="3" width="14" height="10" rx="1.5"/><path d="M1 5l7 5 7-5"/></svg>
      Email
    </button>
    <button class="nav-tab" data-view="calendar" onclick="switchView('calendar')">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1" y="2" width="14" height="13" rx="1.5"/><path d="M5 1v3M11 1v3M1 7h14"/></svg>
      Calendar
    </button>
  </div>

  <div class="nav-right">
    <span class="agent-badge-pill" id="active-count">▲ — ACTIVE</span>
    <button class="settings-btn" onclick="openSettings()" title="Settings">
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="8" cy="8" r="2.5"/>
        <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.22 3.22l1.41 1.41M11.36 11.36l1.42 1.42M3.22 12.78l1.41-1.41M11.36 4.64l1.42-1.42"/>
      </svg>
    </button>
  </div>
</nav>

<!-- Domain identity strip -->
<div class="domain-strip"></div>

<!-- ═══════════════════════════════════════════════════════════════════
     MAIN CONTENT
══════════════════════════════════════════════════════════════════════ -->
<main class="main">

  <!-- ── CHAT ────────────────────────────────────────────── -->
  <div id="view-chat" class="view">
    <div class="view-header">
      <div class="view-title">CHAT <div class="view-title-line"></div></div>
      <div class="view-subtitle">Direct channel to JARVIS</div>
    </div>
    <div id="chat-area" class="chat-area">
      <!-- messages appear here -->
      <div class="chat-empty" id="chat-empty">
        <div class="chat-empty-icon">💬</div>
        <div class="chat-empty-text">Type a command below to start</div>
      </div>
    </div>
  </div>

  <!-- ── OVERVIEW ──────────────────────────────────────────── -->
  <div id="view-overview" class="view">
    <div class="view-header">
      <div class="view-title">
        OVERVIEW
        <div class="view-title-line"></div>
      </div>
      <div class="view-subtitle">Tactical Command Dashboard · S.H.I.E.L.D. Priority View</div>
    </div>

    <!-- Stats strip -->
    <div class="stats-strip">
      <div class="card stat-tile accent">
        <div class="stat-label">Active Agents</div>
        <div class="stat-value" id="stat-agents">—</div>
        <div class="stat-sub">of 56 total</div>
      </div>
      <div class="card stat-tile">
        <div class="stat-label">Missions</div>
        <div class="stat-value" id="stat-missions">—</div>
        <div class="stat-sub">in progress</div>
      </div>
      <div class="card stat-tile gold-accent">
        <div class="stat-label">Needs You</div>
        <div class="stat-value" id="stat-approvals">—</div>
        <div class="stat-sub">pending action</div>
      </div>
      <div class="card stat-tile">
        <div class="stat-label">Memory</div>
        <div class="stat-value" id="stat-memory">—</div>
        <div class="stat-sub">chronicle entries</div>
      </div>
    </div>

    <div class="card-grid">

      <!-- Needs You -->
      <div class="card card-needs-you">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">Needs You</span>
            <span class="dot dot-gold"></span>
          </div>
          <div id="approvals-list">
            <div class="list-row">
              <div style="flex:1">
                <div class="skel" style="height:12px;width:70%;margin-bottom:6px;"></div>
                <div class="skel" style="height:10px;width:40%;"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Active Agents -->
      <div class="card card-tactical">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">Active Agents</span>
            <span class="pill pill-hue" id="active-agents-count">—</span>
          </div>
          <div id="active-agents-list">
            <div class="list-row"><div class="skel" style="height:10px;width:60%;"></div></div>
            <div class="list-row"><div class="skel" style="height:10px;width:55%;"></div></div>
            <div class="list-row"><div class="skel" style="height:10px;width:65%;"></div></div>
          </div>
        </div>
      </div>

      <!-- 3D Forge quick -->
      <div class="card card-tactical">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">3D Forge</span>
            <span class="pill pill-navy">Print Queue</span>
          </div>
          <div id="overview-forge">
            <div class="list-row">
              <span class="dot dot-standby"></span>
              <div>
                <div class="list-row-name">No active print</div>
                <div class="list-row-sub">Queue empty</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Vision quick -->
      <div class="card card-tactical">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">Vision System</span>
            <span class="pill pill-success">LIVE</span>
          </div>
          <div id="overview-vision">
            <div class="list-row">
              <span class="dot dot-success"></span>
              <div>
                <div class="list-row-name">4 Cameras</div>
                <div class="list-row-sub">No events in last 5m</div>
              </div>
              <div class="list-row-meta">SECURE</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Catalyst quick -->
      <div class="card card-tactical">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">Catalyst</span>
            <span class="pill pill-hue" id="catalyst-flows">—</span>
          </div>
          <div id="overview-catalyst">
            <div class="list-row">
              <div class="skel" style="height:10px;width:75%;"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Chronicle quick -->
      <div class="card card-tactical">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">Chronicle</span>
            <span class="pill pill-navy" id="chronicle-count">—</span>
          </div>
          <div id="overview-chronicle">
            <div class="skel" style="height:10px;width:80%;margin-bottom:6px;"></div>
            <div class="skel" style="height:10px;width:60%;"></div>
          </div>
        </div>
      </div>

      <!-- Publishing quick -->
      <div class="card card-tactical">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">Publishing</span>
            <span class="pill pill-gold">Stan Lee</span>
          </div>
          <div id="overview-publishing">
            <div class="skel" style="height:10px;width:65%;margin-bottom:6px;"></div>
            <div class="skel" style="height:10px;width:50%;"></div>
          </div>
        </div>
      </div>

      <!-- Email quick-card -->
      <div class="card card-tactical" onclick="switchView('email')" style="cursor:pointer;">
        <div class="card-hdr">
          <span class="card-icon">✉</span>
          <span class="card-title">EMAIL</span>
          <span class="card-badge" id="emailUnreadBadge">—</span>
        </div>
        <div class="card-body">
          <div class="card-row"><span class="lbl">GMAIL</span><span class="val mono" id="overviewGmailUnread">—</span></div>
          <div class="card-row"><span class="lbl">OUTLOOK</span><span class="val mono" id="overviewOutlookUnread">—</span></div>
          <div class="card-cta">Open inbox →</div>
        </div>
      </div>

      <!-- Calendar quick-card -->
      <div class="card card-tactical" onclick="switchView('calendar')" style="cursor:pointer;">
        <div class="card-hdr">
          <span class="card-icon">📅</span>
          <span class="card-title">CALENDAR</span>
          <span class="card-badge" id="calEventCount">—</span>
        </div>
        <div class="card-body">
          <div class="card-row"><span class="lbl">TODAY</span><span class="val mono" id="overviewTodayEvents">—</span></div>
          <div id="overviewNextEvent" class="next-event-preview">—</div>
          <div class="card-cta">View agenda →</div>
        </div>
      </div>

      <!-- Briefing quick -->
      <div class="card">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">Morning Brief</span>
            <span class="mono" style="font-size:10px;color:var(--text-3);" id="brief-date">—</span>
          </div>
          <div id="brief-text" style="font-size:13px;color:var(--text-2);line-height:1.6;">
            <div class="skel" style="height:10px;width:100%;margin-bottom:5px;"></div>
            <div class="skel" style="height:10px;width:90%;margin-bottom:5px;"></div>
            <div class="skel" style="height:10px;width:75%;"></div>
          </div>
        </div>
      </div>

    </div>
  </div>

  <!-- ── FORGE ──────────────────────────────────────────────── -->
  <div id="view-forge" class="view">
    <div class="view-header">
      <div class="view-title">3D FORGE<div class="view-title-line"></div></div>
      <div class="view-subtitle">Print Queue · Material Inventory · Completions</div>
    </div>

    <div class="card-grid">

      <!-- Active Print -->
      <div class="card card-tactical" style="grid-column: 1/-1;">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">Active Print Job</span>
            <span class="pill pill-hue" id="forge-status">IDLE</span>
          </div>
          <div id="forge-active">
            <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:12px;">
              <div style="flex:1;min-width:180px;">
                <div class="list-row-name" id="forge-job-name">No active job</div>
                <div class="list-row-sub" id="forge-job-detail">Queue is empty · Printer ready</div>
              </div>
              <div style="font-family:var(--font-mono);font-size:11px;color:var(--text-3);text-align:right;">
                <div>LAYER <span id="forge-layer" style="color:var(--hue);">—</span> / <span id="forge-total">—</span></div>
                <div>ETA <span id="forge-eta">—</span></div>
              </div>
            </div>
            <div class="progress-bar"><div class="progress-fill" id="forge-progress" style="width:0%"></div></div>
          </div>
        </div>
      </div>

      <!-- Queue -->
      <div class="card">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Print Queue</span></div>
          <div id="forge-queue">
            <div class="list-row"><span class="dot dot-standby"></span><div><div class="list-row-name">—</div><div class="list-row-sub">No jobs queued</div></div></div>
          </div>
        </div>
      </div>

      <!-- Materials -->
      <div class="card">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Material Inventory</span></div>
          <div id="forge-materials">
            <div class="list-row"><div class="list-row-name">PLA White</div><div class="list-row-meta">2.4 kg</div></div>
            <div class="list-row"><div class="list-row-name">PETG Black</div><div class="list-row-meta">1.1 kg</div></div>
            <div class="list-row"><div class="list-row-name">TPU Flex</div><div class="list-row-meta">0.6 kg</div></div>
            <div class="list-row"><div class="list-row-name">ABS Grey</div><div class="list-row-meta">0.3 kg</div></div>
          </div>
        </div>
      </div>

      <!-- Completions -->
      <div class="card">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Recent Completions</span></div>
          <div id="forge-completions">
            <div class="list-row"><span class="dot dot-success"></span><div><div class="list-row-name">—</div><div class="list-row-sub">No recent completions</div></div></div>
          </div>
        </div>
      </div>

    </div>
  </div>

  <!-- ── VISION ─────────────────────────────────────────────── -->
  <div id="view-vision" class="view">
    <div class="view-header">
      <div class="view-title">VISION SYSTEM<div class="view-title-line"></div></div>
      <div class="view-subtitle">Camera Array · Detection Feed · Alert History</div>
    </div>

    <!-- Camera grid -->
    <div class="section-label">Camera Array</div>
    <div class="camera-grid">
      <div class="card camera-cell">
        <svg class="camera-icon" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/>
        </svg>
        <div class="camera-label">CAM-01</div>
        <span class="pill pill-success">LIVE</span>
        <div class="camera-ts">Last event: —</div>
      </div>
      <div class="card camera-cell">
        <svg class="camera-icon" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/>
        </svg>
        <div class="camera-label">CAM-02</div>
        <span class="pill pill-success">LIVE</span>
        <div class="camera-ts">Last event: —</div>
      </div>
      <div class="card camera-cell">
        <svg class="camera-icon" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/>
        </svg>
        <div class="camera-label">CAM-03</div>
        <span class="pill pill-success">LIVE</span>
        <div class="camera-ts">Last event: —</div>
      </div>
      <div class="card camera-cell">
        <svg class="camera-icon" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/>
        </svg>
        <div class="camera-label">CAM-04</div>
        <span class="pill pill-success">LIVE</span>
        <div class="camera-ts">Last event: —</div>
      </div>
    </div>

    <div class="card-grid-2">
      <div class="card">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Detection Feed</span><span class="pill pill-success">LIVE</span></div>
          <div id="vision-feed">
            <div class="list-row"><span class="dot dot-standby"></span><div><div class="list-row-name">Awaiting events</div><div class="list-row-sub">All clear</div></div></div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Alert History</span></div>
          <div id="vision-alerts">
            <div class="list-row"><div class="list-row-name">No alerts</div></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── CATALYST ───────────────────────────────────────────── -->
  <div id="view-catalyst" class="view">
    <div class="view-header">
      <div class="view-title">CATALYST<div class="view-title-line"></div></div>
      <div class="view-subtitle">Automation Flows · Triggers · Run Analytics</div>
    </div>

    <div class="stats-strip" style="grid-template-columns:repeat(3,1fr);">
      <div class="card stat-tile accent">
        <div class="stat-label">Runs Today</div>
        <div class="stat-value" id="cat-runs">—</div>
      </div>
      <div class="card stat-tile accent">
        <div class="stat-label">Success Rate</div>
        <div class="stat-value" id="cat-rate">—</div>
      </div>
      <div class="card stat-tile">
        <div class="stat-label">Flows Registered</div>
        <div class="stat-value" id="cat-total">—</div>
      </div>
    </div>

    <div class="card-grid-2">
      <div class="card card-tactical">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Active Flows</span></div>
          <div id="catalyst-flows">
            <div class="list-row"><span class="dot dot-standby"></span><div><div class="list-row-name">No active flows</div></div></div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Recent Triggers</span></div>
          <div id="catalyst-triggers">
            <div class="list-row"><div class="list-row-name">No recent triggers</div></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── CHRONICLE ──────────────────────────────────────────── -->
  <div id="view-chronicle" class="view">
    <div class="view-header">
      <div class="view-title">CHRONICLE<div class="view-title-line"></div></div>
      <div class="view-subtitle">Persistent Memory · Knowledge Graph · Agent Journal</div>
    </div>

    <div class="search-wrap">
      <svg class="search-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="6.5" cy="6.5" r="4"/><path d="M11 11l3 3"/>
      </svg>
      <input class="search-input" type="text" placeholder="Search memory entries…" id="chronicle-search" oninput="searchChronicle(this.value)">
    </div>

    <div class="card-grid-2">
      <div class="card" style="grid-column:1/-1;">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">Recent Entries</span>
            <span class="pill pill-hue" id="chronicle-total">—</span>
          </div>
          <div id="chronicle-list">
            <div class="chronicle-entry">
              <div class="chronicle-ts">Loading…</div>
              <div class="skel" style="height:10px;width:80%;margin:6px 0;"></div>
              <div class="skel" style="height:10px;width:55%;"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header" style="padding:16px 20px 0;">
        <span class="card-title">Tag Cloud</span>
      </div>
      <div class="tag-cloud" id="tag-cloud">
        <div class="skel" style="height:24px;width:60px;border-radius:99px;"></div>
        <div class="skel" style="height:24px;width:80px;border-radius:99px;"></div>
        <div class="skel" style="height:24px;width:50px;border-radius:99px;"></div>
      </div>
    </div>
  </div>

  <!-- ── PUBLISHING ─────────────────────────────────────────── -->
  <div id="view-publishing" class="view">
    <div class="view-header">
      <div class="view-title">PUBLISHING<div class="view-title-line"></div></div>
      <div class="view-subtitle">Books · Pipeline · Pending Reviews · Stan Lee Bridge</div>
    </div>

    <!-- Home Projects section -->
    <div class="section-label">Home Projects</div>
    <div class="card card-tactical" style="margin-bottom:20px;">
      <div class="card-hdr">
        <span class="card-title">ACTIVE PROJECTS</span>
        <span class="card-badge" id="homeProjectsBadge">—</span>
      </div>
      <div class="card-inner" style="padding-top:8px;">
        <div id="homeProjectsList">
          <div class="loading-state" style="text-align:left;padding:12px 0;">Loading projects...</div>
        </div>
      </div>
    </div>

    <div class="section-label">Book Pipeline</div>
    <div class="card-grid" id="publishing-books">
      <div class="card">
        <div class="card-inner">
          <div class="skel" style="height:12px;width:70%;margin-bottom:8px;"></div>
          <div class="pipeline-bar">
            <div class="pipeline-seg done"></div>
            <div class="pipeline-seg done"></div>
            <div class="pipeline-seg current"></div>
            <div class="pipeline-seg"></div>
            <div class="pipeline-seg"></div>
            <div class="pipeline-seg"></div>
            <div class="pipeline-seg"></div>
            <div class="pipeline-seg"></div>
            <div class="pipeline-seg"></div>
          </div>
        </div>
      </div>
    </div>

    <div class="section-label">Pending Reviews</div>
    <div class="card card-needs-you">
      <div class="card-inner">
        <div id="publishing-reviews">
          <div class="list-row"><span class="dot dot-gold"></span><div><div class="list-row-name">No pending reviews</div></div></div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── WORKSHOP ───────────────────────────────────────────── -->
  <div id="view-workshop" class="view">
    <div class="view-header">
      <div>
        <div class="view-title">WORKSHOP<div class="view-title-line"></div></div>
        <div class="view-sub">Tasks · Overdue · Today's Focus</div>
      </div>
      <div class="view-actions">
        <button class="btn-primary" onclick="loadHomeTasks()">Refresh ↻</button>
      </div>
    </div>

    <!-- Task stats -->
    <div class="stat-row" style="grid-template-columns:repeat(3,1fr);margin-bottom:16px;">
      <div class="stat-card accent"><div class="stat-num" id="workshopStatOverdue">—</div><div class="stat-lbl">OVERDUE</div></div>
      <div class="stat-card"><div class="stat-num" id="workshopStatToday">—</div><div class="stat-lbl">DUE TODAY</div></div>
      <div class="stat-card"><div class="stat-num" id="workshopStatTotal">—</div><div class="stat-lbl">OPEN TASKS</div></div>
    </div>

    <div class="card-grid">
      <!-- Overdue tasks -->
      <div class="card card-needs-you">
        <div class="card-hdr">
          <span class="card-title">OVERDUE</span>
          <span class="card-badge" id="overdueCount">—</span>
        </div>
        <div class="card-inner" style="padding-top:8px;">
          <div id="overdueTasks">
            <div class="loading-state" style="padding:12px 0;text-align:left;">Loading...</div>
          </div>
        </div>
      </div>

      <!-- Today tasks -->
      <div class="card card-tactical">
        <div class="card-hdr">
          <span class="card-title">DUE TODAY</span>
          <span class="card-badge" id="todayTaskCount">—</span>
        </div>
        <div class="card-inner" style="padding-top:8px;">
          <div id="todayTasks">
            <div class="loading-state" style="padding:12px 0;text-align:left;">Loading...</div>
          </div>
        </div>
      </div>

      <!-- All open tasks -->
      <div class="card" style="grid-column:1/-1;">
        <div class="card-hdr">
          <span class="card-title">ALL OPEN TASKS</span>
          <span class="card-badge" id="allTaskCount">—</span>
        </div>
        <div class="card-inner" style="padding-top:8px;">
          <div id="allTasks">
            <div class="loading-state" style="padding:12px 0;text-align:left;">Loading...</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── HUDDLE ─────────────────────────────────────────────── -->
  <div id="view-huddle" class="view">
    <div class="view-header">
      <div class="view-title">MORNING HUDDLE · DOSSIER REVIEW<div class="view-title-line"></div></div>
      <div class="view-subtitle">Daily Standup · What Every Agent Did, Needs, and Plans</div>
    </div>
    <div id="huddle-meta" class="huddle-meta">
      <span class="huddle-stat" id="huddle-active-work">— active items</span>
      <span class="huddle-stat" id="huddle-blockers-count">— blockers</span>
      <span class="huddle-stat" id="huddle-approvals-count">— awaiting approval</span>
      <button class="huddle-refresh-btn" onclick="loadHuddle()">↺ Refresh</button>
    </div>

    <!-- Party Mode Status -->
    <div id="party-mode-bar" class="party-bar" style="display:none">
      <span class="party-bar-indicator"></span>
      <span id="party-bar-text">Agents working...</span>
      <button class="party-bar-btn" onclick="startPartyMode()">⚡ Wake the Agents</button>
    </div>

    <!-- Overnight Dossiers -->
    <div class="huddle-section" id="dossier-section">
      <div class="huddle-section-label">🗂 OVERNIGHT DOSSIERS — Ready for Review</div>
      <div id="huddle-dossier-grid" class="dossier-grid">
        <div class="skeleton-block" style="height:120px;border-radius:8px;"></div>
      </div>
    </div>

    <!-- Blockers / Approvals Needed row -->
    <div id="huddle-approvals" class="huddle-section" style="display:none">
      <div class="huddle-section-label">⚡ NEEDS YOUR ATTENTION</div>
      <div id="huddle-approvals-list" class="huddle-approval-list"></div>
    </div>

    <!-- Passive Income Pipeline -->
    <div class="huddle-section">
      <div class="huddle-section-label">💡 PASSIVE INCOME PIPELINE</div>
      <div id="huddle-pi-pipeline" class="pi-pipeline-grid">
        <div class="skeleton-block" style="height:80px;border-radius:8px;"></div>
      </div>
    </div>

    <!-- Agent standups grid -->
    <div class="huddle-section">
      <div class="huddle-section-label">📋 AGENT STANDUPS</div>
      <div id="huddle-reports-grid" class="huddle-grid">
        <!-- populated by loadHuddle() -->
        <div class="skeleton-block" style="height:140px;border-radius:8px;"></div>
        <div class="skeleton-block" style="height:140px;border-radius:8px;"></div>
        <div class="skeleton-block" style="height:140px;border-radius:8px;"></div>
      </div>
    </div>
  </div>

  <!-- ── AGENTS ─────────────────────────────────────────────── -->
  <div id="view-agents" class="view">
    <div class="view-header">
      <div class="view-title">AGENT OPS CENTER<div class="view-title-line"></div></div>
      <div class="view-subtitle">Live Runtime · What Every Agent Is Doing Right Now</div>
    </div>

    <!-- System status bar -->
    <div class="runtime-status-bar" id="runtime-status-bar">
      <div class="runtime-stat">
        <span class="dot dot-success"></span>
        <span class="runtime-stat-val" id="rt-awake-count">—</span>
        <span class="runtime-stat-lbl">AWAKE</span>
      </div>
      <div class="runtime-divider"></div>
      <div class="runtime-stat">
        <span class="dot dot-standby"></span>
        <span class="runtime-stat-val" id="rt-idle-count">—</span>
        <span class="runtime-stat-lbl">IDLE</span>
      </div>
      <div class="runtime-divider"></div>
      <div class="runtime-stat">
        <span class="dot dot-error"></span>
        <span class="runtime-stat-val" id="rt-blocked-count">—</span>
        <span class="runtime-stat-lbl">BLOCKED</span>
      </div>
      <div class="runtime-divider"></div>
      <span id="rt-mode-badge" class="runtime-mode-badge">—</span>
      <span id="rt-quiet-badge" class="quiet-badge" style="display:none;">QUIET HOURS</span>
      <span class="runtime-last-tick" id="rt-last-tick">last tick: —</span>
    </div>

    <!-- Live runtime cards -->
    <div class="runtime-section-label">LIVE RUNTIME</div>
    <div class="runtime-grid" id="runtime-grid">
      <div class="agent-runtime-card state-idle">
        <div class="arc-header"><div class="arc-names"><div class="arc-label">Loading…</div></div></div>
      </div>
    </div>

    <!-- Full roster toggle -->
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
      <div class="runtime-section-label" style="margin-bottom:0;flex:1;">FULL ROSTER — 56 OPERATIVES</div>
      <button class="roster-toggle" onclick="toggleRoster()">SHOW ROSTER ▾</button>
    </div>
    <div id="roster-section" style="display:none;">
      <div class="filter-strip" id="agent-filters" style="margin-bottom:14px;">
        <button class="filter-pill active" onclick="filterAgents('all')">ALL</button>
        <button class="filter-pill" onclick="filterAgents('active')">ACTIVE</button>
        <button class="filter-pill" onclick="filterAgents('Command')">Command</button>
        <button class="filter-pill" onclick="filterAgents('Engineering')">Engineering</button>
        <button class="filter-pill" onclick="filterAgents('Intelligence')">Intelligence</button>
        <button class="filter-pill" onclick="filterAgents('Analysis')">Analysis</button>
        <button class="filter-pill" onclick="filterAgents('Operations')">Operations</button>
        <button class="filter-pill" onclick="filterAgents('Publishing')">Publishing</button>
        <button class="filter-pill" onclick="filterAgents('Vision')">Vision</button>
        <button class="filter-pill" onclick="filterAgents('Power')">Power</button>
        <button class="filter-pill" onclick="filterAgents('Workshop')">Workshop</button>
        <button class="filter-pill" onclick="filterAgents('Interface')">Interface</button>
      </div>
      <div class="agent-grid" id="agent-grid"></div>
    </div>
  </div>

  <!-- ── INTELLIGENCE ───────────────────────────────────────── -->
  <div id="view-intelligence" class="view">
    <div class="view-header">
      <div class="view-title">INTELLIGENCE<div class="view-title-line"></div></div>
      <div class="view-subtitle">Service Health · LLM Ladder · Bridge Connections</div>
    </div>

    <div class="section-label">Service Health</div>
    <div class="service-grid" id="service-grid">
      <div class="card service-card">
        <div class="service-name"><span class="dot dot-standby"></span>Loading…</div>
      </div>
    </div>

    <div class="section-label">LLM Escalation Ladder</div>
    <div class="card" style="margin-bottom:20px;">
      <div class="llm-ladder">
        <div class="llm-node">
          <div class="llm-label">phi3.5</div>
          <div class="llm-tier">TIER 1</div>
        </div>
        <div class="llm-arrow">→</div>
        <div class="llm-node">
          <div class="llm-label">gpt-oss:20b</div>
          <div class="llm-tier">TIER 2</div>
        </div>
        <div class="llm-arrow">→</div>
        <div class="llm-node">
          <div class="llm-label">gpt-5.4-mini</div>
          <div class="llm-tier">TIER 3</div>
        </div>
        <div class="llm-arrow">→</div>
        <div class="llm-node current">
          <div class="llm-label">gpt-5.4-thinking</div>
          <div class="llm-tier">TIER 4 · ACTIVE</div>
        </div>
        <div class="llm-arrow">→</div>
        <div class="llm-node">
          <div class="llm-label">gpt-5.5-thinking</div>
          <div class="llm-tier">TIER 5</div>
        </div>
      </div>
    </div>

    <div class="section-label">Bridge Connections</div>
    <div class="card" style="margin-bottom:20px;">
      <div class="card-inner">
        <div class="bridge-row">
          <span class="dot dot-success"></span>
          <span class="bridge-name">Ghostwritr</span>
          <span class="pill pill-success">CONNECTED</span>
          <span class="bridge-url mono" style="font-size:10px;color:var(--text-3);">ghostwritr.local</span>
        </div>
        <div class="bridge-row">
          <span class="dot dot-success"></span>
          <span class="bridge-name">Chronicle</span>
          <span class="pill pill-success">CONNECTED</span>
          <span class="bridge-url mono" style="font-size:10px;color:var(--text-3);">chronicle.local</span>
        </div>
        <div class="bridge-row">
          <span class="dot dot-standby"></span>
          <span class="bridge-name">OpenViking</span>
          <span class="pill pill-navy">STANDBY</span>
          <span class="bridge-url mono" style="font-size:10px;color:var(--text-3);">openviking.local</span>
        </div>
      </div>
    </div>

  </div>

  <!-- ── EMAIL ─────────────────────────────────────────────── -->
  <div id="view-email" class="view" style="display:none">
    <div class="view-header">
      <div>
        <div class="view-title">EMAIL<div class="view-title-line"></div></div>
        <div class="view-sub">Gmail · Outlook · unified inbox</div>
      </div>
      <div class="view-actions">
        <button class="btn-ghost" onclick="loadHomeEmail(true)">Unread only</button>
        <button class="btn-ghost" onclick="loadHomeEmail(false)">All</button>
        <button class="btn-primary" onclick="syncSource('gmail'); syncSource('outlook')">Sync ↻</button>
      </div>
    </div>

    <!-- Stats strip -->
    <div class="stat-row">
      <div class="stat-card accent"><div class="stat-num" id="emailStatUnread">—</div><div class="stat-lbl">UNREAD</div></div>
      <div class="stat-card"><div class="stat-num" id="emailStatGmail">—</div><div class="stat-lbl">GMAIL UNREAD</div></div>
      <div class="stat-card"><div class="stat-num" id="emailStatOutlook">—</div><div class="stat-lbl">OUTLOOK UNREAD</div></div>
    </div>

    <!-- Source tabs -->
    <div class="source-tabs">
      <button class="source-tab active" data-source="all" onclick="filterEmail('all', this)">All</button>
      <button class="source-tab" data-source="gmail" onclick="filterEmail('gmail', this)">
        <span class="source-dot gmail"></span> Gmail
      </button>
      <button class="source-tab" data-source="outlook" onclick="filterEmail('outlook', this)">
        <span class="source-dot outlook"></span> Outlook
      </button>
    </div>

    <!-- Email list -->
    <div id="emailList" class="email-list">
      <div class="loading-state">Loading email...</div>
    </div>
  </div>

  <!-- ── CALENDAR ───────────────────────────────────────────── -->
  <div id="view-calendar" class="view" style="display:none">
    <div class="view-header">
      <div>
        <div class="view-title">CALENDAR<div class="view-title-line"></div></div>
        <div class="view-sub" id="calendarDateLabel">Today</div>
      </div>
      <div class="view-actions">
        <button class="btn-primary" onclick="syncAll()">Sync ↻</button>
      </div>
    </div>

    <!-- Today's agenda -->
    <div class="card card-tactical" style="margin-bottom:16px">
      <div class="card-hdr">
        <span class="card-title">TODAY'S AGENDA</span>
        <span class="card-badge" id="todayEventCount">0 events</span>
      </div>
      <div id="todayEventList" class="event-list" style="padding:4px 0 8px;"></div>
    </div>

    <!-- Upcoming events -->
    <div class="card" style="margin-bottom:16px">
      <div class="card-hdr"><span class="card-title">NEXT 7 DAYS</span></div>
      <div id="upcomingEventList" class="event-list" style="padding:4px 0 8px;"></div>
    </div>

    <!-- Source legend -->
    <div class="cal-legend">
      <span class="legend-item"><span class="source-dot" style="background:#4285F4;display:inline-block;width:8px;height:8px;border-radius:50%;"></span> Google Calendar</span>
      <span class="legend-item"><span class="source-dot" style="background:#0078D4;display:inline-block;width:8px;height:8px;border-radius:50%;"></span> Outlook</span>
      <span class="legend-item"><span class="source-dot" style="background:#7C3AED;display:inline-block;width:8px;height:8px;border-radius:50%;"></span> Cozi Family</span>
    </div>
  </div>

</main>

<!-- ═══════════════════════════════════════════════════════════════════
     COMMAND BAR
══════════════════════════════════════════════════════════════════════ -->
<div class="command-bar">
  <div class="cmd-chips">
    <button class="cmd-chip" onclick="setCmd('Status report')">📊 Status</button>
    <button class="cmd-chip" onclick="setCmd('Show active agents')">👥 Agents</button>
    <button class="cmd-chip" onclick="setCmd('What needs approval?')">⚡ Approvals</button>
    <button class="cmd-chip" onclick="setCmd('Morning briefing')">📰 Brief</button>
    <button class="cmd-chip" onclick="setCmd('Start print job')">🖨️ Forge</button>
    <button class="cmd-chip" onclick="setCmd('Run diagnostics')">🔬 Diag</button>
    <button class="cmd-chip" onclick="setCmd('Chronicle search:')">🔍 Memory</button>
  </div>
  <div class="cmd-row">
    <input class="cmd-input" id="cmd-input" type="text" placeholder="Command JARVIS…" onkeydown="cmdKey(event)">
    <button class="cmd-mic" id="cmd-mic" onclick="toggleMic()" title="Voice input">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="9" y="2" width="6" height="11" rx="3"/><path d="M5 10a7 7 0 0014 0"/><path d="M12 21v-4"/>
      </svg>
    </button>
    <button class="cmd-send" onclick="sendCmd()">SEND</button>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════════
     SETTINGS MODAL
══════════════════════════════════════════════════════════════════════ -->
<div class="modal-overlay hidden" id="settings-overlay" onclick="closeSettingsIfOuter(event)">
  <div class="modal" id="settings-modal">
    <div class="modal-header">
      <div class="modal-title">Settings &amp; Theme</div>
      <button class="modal-close" onclick="closeSettings()">✕</button>
    </div>

    <p style="font-size:12px;color:var(--text-3);margin-bottom:18px;font-family:var(--font-mono);letter-spacing:0.04em;text-transform:uppercase;">Interface Theme</p>
    <div class="theme-cards">
      <div class="theme-card" onclick="setTheme('classic')">
        <div class="theme-preview theme-preview-classic"></div>
        <div class="theme-name">Classic</div>
        <div class="theme-desc">Dark navy · Arc blue</div>
      </div>
      <div class="theme-card" onclick="setTheme('nexus')">
        <div class="theme-preview theme-preview-nexus"></div>
        <div class="theme-name">Nexus</div>
        <div class="theme-desc">Obsidian · Violet</div>
      </div>
      <div class="theme-card current" onclick="setTheme('glass')">
        <div class="theme-preview theme-preview-glass"></div>
        <div class="theme-name">Glass</div>
        <div class="theme-desc">Surgical · Adaptive</div>
      </div>
    </div>

    <p style="font-size:12px;color:var(--text-3);margin:20px 0 10px;font-family:var(--font-mono);letter-spacing:0.04em;text-transform:uppercase;">Welcome, {user_name}</p>
    <p style="font-size:12px;color:var(--text-2);">JARVIS Glass — Adaptive Chromatic Interface<br>Version 3.0 · S.H.I.E.L.D. Clearance Level 6</p>
  </div>
</div>

<!-- Toast container -->
<div id="toast-wrap"></div>

<!-- Debug panel — hidden by default, shown on JS errors -->
<div id="_dbg-panel" style="display:none;position:fixed;bottom:0;left:0;right:0;z-index:99999;background:rgba(220,30,30,0.92);color:#fff;font-family:monospace;font-size:13px;padding:12px 16px;max-height:200px;overflow-y:auto;">
  <strong>⚠ JARVIS Init Errors</strong> (open DevTools Console for full trace)
</div>

<!-- ═══════════════════════════════════════════════════════════════════
     JAVASCRIPT
══════════════════════════════════════════════════════════════════════ -->
<script>
'use strict';

/* ── Constants ── */
const INITIAL_PACKET = {_packet};
const USER_NAME      = {_user_name_js};
const WS_URL         = 'ws://' + location.host + '/ws';

/* ── Agent roster (56 operatives) ── */
const AGENTS = [
  {{id:'nick-fury',       name:'NICK FURY',        title:'Director',             domain:'Command',       status:'active'}},
  {{id:'iron-man',        name:'IRON MAN',          title:'Engineering Lead',     domain:'Engineering',   status:'active'}},
  {{id:'captain-america', name:'CAPTAIN AMERICA',   title:'Operations Chief',     domain:'Operations',    status:'standby'}},
  {{id:'black-widow',     name:'BLACK WIDOW',       title:'Intelligence',         domain:'Intelligence',  status:'active'}},
  {{id:'thor',            name:'THOR',              title:'Power Systems',        domain:'Power',         status:'standby'}},
  {{id:'hulk',            name:'HULK',              title:'Data Analysis',        domain:'Analysis',      status:'standby'}},
  {{id:'vision',          name:'VISION',            title:'Perception Engine',    domain:'Vision',        status:'active'}},
  {{id:'scarlet-witch',   name:'SCARLET WITCH',     title:'Pattern Recognition',  domain:'Analysis',      status:'standby'}},
  {{id:'stan-lee',        name:'STAN LEE',          title:'Publishing Bridge',    domain:'Publishing',    status:'active'}},
  {{id:'pepper-potts',    name:'PEPPER POTTS',      title:'Chief of Staff',       domain:'Command',       status:'active'}},
  {{id:'friday',          name:'FRIDAY',            title:'Voice Interface',      domain:'Interface',     status:'active'}},
  {{id:'spider-man',      name:'SPIDER-MAN',        title:'API & Web',            domain:'Engineering',   status:'standby'}},
  {{id:'black-panther',   name:'BLACK PANTHER',     title:'Financial Intel',      domain:'Finance',       status:'active'}},
  {{id:'doctor-strange',  name:'DOCTOR STRANGE',    title:'Scheduling',           domain:'Scheduling',    status:'active'}},
  {{id:'loki',            name:'LOKI',              title:'Testing & QA',         domain:'Engineering',   status:'standby'}},
  {{id:'hawkeye',         name:'HAWKEYE',           title:'Monitoring',           domain:'Intelligence',  status:'active'}},
  {{id:'falcon',          name:'FALCON',            title:'Network Recon',        domain:'Intelligence',  status:'standby'}},
  {{id:'winter-soldier',  name:'WINTER SOLDIER',    title:'Security',             domain:'Intelligence',  status:'standby'}},
  {{id:'war-machine',     name:'WAR MACHINE',       title:'Deployment',           domain:'Engineering',   status:'standby'}},
  {{id:'ant-man',         name:'ANT-MAN',           title:'Micro-Optimization',   domain:'Engineering',   status:'standby'}},
  {{id:'wasp',            name:'WASP',              title:'UX & Interface',       domain:'Interface',     status:'standby'}},
  {{id:'captain-marvel',  name:'CAPTAIN MARVEL',    title:'Compute & Power',      domain:'Power',         status:'standby'}},
  {{id:'shang-chi',       name:'SHANG-CHI',         title:'Workflow Engine',      domain:'Operations',    status:'standby'}},
  {{id:'ms-marvel',       name:'MS. MARVEL',        title:'Social Engine',        domain:'Publishing',    status:'standby'}},
  {{id:'moon-knight',     name:'MOON KNIGHT',       title:'Night Watch',          domain:'Intelligence',  status:'standby'}},
  {{id:'she-hulk',        name:'SHE-HULK',          title:'Legal & Compliance',   domain:'Operations',    status:'standby'}},
  {{id:'blade',           name:'BLADE',             title:'Threat Detection',     domain:'Intelligence',  status:'standby'}},
  {{id:'ghost-rider',     name:'GHOST RIDER',       title:'Process Runner',       domain:'Operations',    status:'standby'}},
  {{id:'daredevil',       name:'DAREDEVIL',         title:'Precision Audit',      domain:'Intelligence',  status:'standby'}},
  {{id:'jessica-jones',   name:'JESSICA JONES',     title:'Investigative',        domain:'Intelligence',  status:'standby'}},
  {{id:'luke-cage',       name:'LUKE CAGE',         title:'Reliability',          domain:'Engineering',   status:'standby'}},
  {{id:'iron-fist',       name:'IRON FIST',         title:'Performance',          domain:'Engineering',   status:'standby'}},
  {{id:'punisher',        name:'PUNISHER',          title:'Cleanup & Prune',      domain:'Operations',    status:'standby'}},
  {{id:'elektra',         name:'ELEKTRA',           title:'Precision Strike',     domain:'Operations',    status:'standby'}},
  {{id:'gamora',          name:'GAMORA',            title:'Data Integrity',       domain:'Analysis',      status:'standby'}},
  {{id:'rocket',          name:'ROCKET',            title:'Tooling',              domain:'Workshop',      status:'standby'}},
  {{id:'groot',           name:'GROOT',             title:'Dependencies',         domain:'Engineering',   status:'standby'}},
  {{id:'drax',            name:'DRAX',              title:'Resource Manager',     domain:'Operations',    status:'standby'}},
  {{id:'star-lord',       name:'STAR-LORD',         title:'Orchestration',        domain:'Command',       status:'standby'}},
  {{id:'nebula',          name:'NEBULA',            title:'Sync & Mirror',        domain:'Engineering',   status:'standby'}},
  {{id:'mantis',          name:'MANTIS',            title:'Sentiment Analysis',   domain:'Analysis',      status:'standby'}},
  {{id:'okoye',           name:'OKOYE',             title:'System Guard',         domain:'Intelligence',  status:'standby'}},
  {{id:'shuri',           name:'SHURI',             title:'Research & Dev',       domain:'Engineering',   status:'active'}},
  {{id:'mbaku',           name:"M'BAKU",            title:'Compute Cluster',      domain:'Power',         status:'standby'}},
  {{id:'valkyrie',        name:'VALKYRIE',          title:'Recovery',             domain:'Operations',    status:'standby'}},
  {{id:'korg',            name:'KORG',              title:'Build System',         domain:'Engineering',   status:'standby'}},
  {{id:'heimdall',        name:'HEIMDALL',          title:'Observatory',          domain:'Intelligence',  status:'active'}},
  {{id:'wong',            name:'WONG',              title:'Knowledge Guard',      domain:'Chronicle',     status:'active'}},
  {{id:'nick-fury-jr',    name:'FURY JR.',          title:'Field Ops',            domain:'Operations',    status:'standby'}},
  {{id:'agent-13',        name:'AGENT 13',          title:'Comms',                domain:'Intelligence',  status:'standby'}},
  {{id:'yelena',          name:'YELENA',            title:'Rapid Response',       domain:'Operations',    status:'standby'}},
  {{id:'kate-bishop',     name:'KATE BISHOP',       title:'Precision Tasks',      domain:'Operations',    status:'standby'}},
  {{id:'america-chavez',  name:'AMERICA CHAVEZ',    title:'Multiverse Router',    domain:'Engineering',   status:'standby'}},
  {{id:'sentry',          name:'SENTRY',            title:'High Availability',    domain:'Power',         status:'standby'}},
  {{id:'nova',            name:'NOVA',              title:'Speed Ops',            domain:'Operations',    status:'standby'}},
  {{id:'makkari',         name:'MAKKARI',           title:'Data Transfer',        domain:'Engineering',   status:'standby'}},
];

/* Domain → left-border CSS class */
const DOMAIN_CLASS = {{
  'Command':      'domain-command',
  'Engineering':  'domain-engineering',
  'Intelligence': 'domain-intelligence',
  'Vision':       'domain-vision',
  'Publishing':   'domain-publishing',
  'Power':        'domain-power',
  'Analysis':     'domain-analysis',
  'Finance':      'domain-finance',
  'Scheduling':   'domain-scheduling',
  'Interface':    'domain-interface',
  'Workshop':     'domain-workshop',
  'Operations':   'domain-operations',
  'Chronicle':    'domain-chronicle',
}};

/* ── State ── */
let currentView    = 'overview';
let ws             = null;
let wsRetries      = 0;
let micActive      = false;
let currentFilter  = 'all';
let homeData       = {{}};
let emailCache     = [];
let emailFilter    = 'all';

/* ═══════════════════════════════════════════════════════════════
   INIT
═══════════════════════════════════════════════════════════════ */
/* ── Global error catcher — surfaces JS crashes on remote machines ── */
window.onerror = function(msg, src, line, col, err) {{
  const panel = document.getElementById('_dbg-panel');
  if (panel) {{
    panel.style.display = 'block';
    panel.innerHTML += '<p><b>' + (src||'?').split('/').pop() + ':' + line + '</b> — ' + escHtml(String(msg)) + '</p>';
  }}
  console.error('[JARVIS init error]', msg, src, line, col, err);
}};
window.onunhandledrejection = function(e) {{
  const panel = document.getElementById('_dbg-panel');
  if (panel) {{
    panel.style.display = 'block';
    panel.innerHTML += '<p><b>UnhandledPromise</b> — ' + escHtml(String(e.reason)) + '</p>';
  }}
  console.error('[JARVIS promise error]', e.reason);
}};

function _showDbg(label, msg) {{
  const panel = document.getElementById('_dbg-panel');
  if (panel) {{
    panel.style.display = 'block';
    panel.innerHTML += '<p><b>' + escHtml(label) + '</b> — ' + escHtml(String(msg)) + '</p>';
  }}
}}

function init() {{
  try {{
    switchView('overview');
  }} catch(e) {{ _showDbg('switchView', e); }}
  try {{
    renderAgents('all');
  }} catch(e) {{ _showDbg('renderAgents', e); }}
  loadStatus();
  loadApprovals();
  loadBriefing();
  connectWebSocket();
  updateActiveCounts();
  loadHomeDashboard();
  loadOverviewAgents();
  loadOverviewCatalyst();
  loadOverviewChronicle();
  loadOverviewPublishing();

  // Handle initial packet from server
  if (INITIAL_PACKET && typeof INITIAL_PACKET === 'object') {{
    try {{ handlePacket(INITIAL_PACKET); }} catch(e) {{ _showDbg('handlePacket', e); }}
  }}
}}

/* ═══════════════════════════════════════════════════════════════
   VIEW SWITCHING — CHROMATIC SHIFT LIVES HERE
═══════════════════════════════════════════════════════════════ */
function switchView(name) {{
  document.querySelectorAll('.view').forEach(v => {{
    v.style.display = 'none';
    v.classList.remove('active');
  }});

  const el = document.getElementById('view-' + name);
  if (el) {{
    el.style.display = 'block';
    el.classList.add('active');
  }}

  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  const tab = document.querySelector('[data-view="' + name + '"]');
  if (tab) tab.classList.add('active');

  /* ← THE CHROMATIC SHIFT — sets domain on <html> */
  document.documentElement.setAttribute('data-domain', name);

  currentView = name;
  loadViewData(name);
}}

function loadViewData(name) {{
  // Stop any existing agents refresh timer
  if (_agentsRefreshTimer) {{ clearInterval(_agentsRefreshTimer); _agentsRefreshTimer = null; }}

  switch (name) {{
    case 'overview':     loadApprovals(); loadBriefing(); loadHomeDashboard(); loadOverviewAgents(); loadOverviewCatalyst(); loadOverviewChronicle(); loadOverviewPublishing(); break;
    case 'agents':
      loadLiveAgents();
      // Auto-refresh every 30s while on this view
      _agentsRefreshTimer = setInterval(loadLiveAgents, 30000);
      break;
    case 'huddle':       loadHuddle(); loadPassiveIncomePipeline(); loadDossiers(); loadPartyStatus(); break;
    case 'publishing':   loadPublishing(); loadHomeProjects(); break;
    case 'intelligence': loadStatus(); break;
    case 'chronicle':    loadChronicle(); break;
    case 'email':        loadHomeEmail(); break;
    case 'calendar':     loadHomeCalendar(); break;
    case 'workshop':     loadHomeTasks(); break;
  }}
}}

/* ═══════════════════════════════════════════════════════════════
   API CALLS
═══════════════════════════════════════════════════════════════ */
async function loadStatus() {{
  try {{
    const res = await fetch('/api/status');
    if (!res.ok) {{ console.warn('loadStatus', res.status); return; }}
    const data = await res.json();
    renderStatus(data);
  }} catch(e) {{ console.error('loadStatus failed', e); }}
}}

async function loadApprovals() {{
  try {{
    const res = await fetch('/api/approvals');
    if (!res.ok) {{ console.warn('loadApprovals', res.status); return; }}
    const data = await res.json();
    renderApprovals(data);
  }} catch(e) {{ console.error('loadApprovals failed', e); }}
}}

async function loadPublishing() {{
  try {{
    const res = await fetch('/api/publishing/dashboard');
    if (!res.ok) {{ console.warn('loadPublishing', res.status); return; }}
    const data = await res.json();
    renderPublishing(data);
  }} catch(e) {{ console.error('loadPublishing failed', e); }}
}}

async function loadBriefing() {{
  try {{
    const res = await fetch('/api/briefing');
    if (!res.ok) {{ console.warn('loadBriefing', res.status); return; }}
    const data = await res.json();
    renderBriefing(data);
  }} catch(e) {{ console.error('loadBriefing failed', e); }}
}}

async function loadChronicle() {{
  try {{
    const res = await fetch('/api/chronicle/recent');
    if (!res.ok) {{ console.warn('loadChronicle', res.status); return; }}
    const data = await res.json();
    renderChronicle(data);
  }} catch(e) {{ console.error('loadChronicle failed', e); }}
}}

/* ═══════════════════════════════════════════════════════════════
   HOME INTELLIGENCE API
═══════════════════════════════════════════════════════════════ */
async function loadHomeDashboard() {{
  try {{
    const r = await fetch('/api/home/dashboard');
    if (!r.ok) return;
    const d = await r.json();
    homeData = d;
    updateOverviewHomeCards(d);
  }} catch(e) {{ console.error('home dashboard failed', e); }}
}}

async function loadHomeEmail(unreadOnly) {{
  if (unreadOnly === undefined) unreadOnly = false;
  try {{
    const url = '/api/home/email?unread_only=' + (unreadOnly ? 'true' : 'false') + '&limit=50';
    const r = await fetch(url);
    if (!r.ok) return;
    const d = await r.json();
    emailCache = d.emails || [];
    // Update stats
    const s = d.stats || {{}};
    setEl('emailStatUnread', (s.gmail ? s.gmail.unread : 0) + (s.outlook ? s.outlook.unread : 0));
    setEl('emailStatGmail', s.gmail ? s.gmail.unread : '—');
    setEl('emailStatOutlook', s.outlook ? s.outlook.unread : '—');
    setEl('emailUnreadBadge', ((s.gmail ? s.gmail.unread : 0) + (s.outlook ? s.outlook.unread : 0)));
    setEl('overviewGmailUnread', s.gmail ? s.gmail.unread : '—');
    setEl('overviewOutlookUnread', s.outlook ? s.outlook.unread : '—');
    renderEmailList(emailCache, emailFilter);
  }} catch(e) {{ console.error('email load failed', e); }}
}}

async function loadHomeCalendar() {{
  try {{
    const [todayRes, upcomingRes] = await Promise.all([
      fetch('/api/home/calendar/today'),
      fetch('/api/home/calendar/upcoming?days=7')
    ]);
    if (todayRes.ok) {{
      const d = await todayRes.json();
      const dateLabel = document.getElementById('calendarDateLabel');
      if (dateLabel && d.date) dateLabel.textContent = d.date;
      const count = d.event_count || 0;
      setEl('todayEventCount', count + ' event' + (count !== 1 ? 's' : ''));
      renderEventList('todayEventList', d.events || []);
    }}
    if (upcomingRes.ok) {{
      const d = await upcomingRes.json();
      renderEventList('upcomingEventList', d.events || []);
    }}
  }} catch(e) {{ console.error('calendar load failed', e); }}
}}

async function loadHomeProjects() {{
  try {{
    const r = await fetch('/api/home/projects?status=active');
    if (!r.ok) return;
    const d = await r.json();
    renderHomeProjects(d.projects || [], d.total);
  }} catch(e) {{ console.error('projects load failed', e); }}
}}

async function loadHomeTasks() {{
  try {{
    const [allRes, overdueRes, todayRes] = await Promise.all([
      fetch('/api/home/tasks?status=open'),
      fetch('/api/home/tasks/overdue'),
      fetch('/api/home/tasks/today')
    ]);
    if (allRes.ok) {{
      const d = await allRes.json();
      setEl('workshopStatTotal', d.total ?? '—');
      setEl('allTaskCount', d.total ?? '—');
      renderTaskList('allTasks', d.tasks || []);
    }}
    if (overdueRes.ok) {{
      const d = await overdueRes.json();
      setEl('workshopStatOverdue', d.total ?? '—');
      setEl('overdueCount', d.total ?? '—');
      renderTaskList('overdueTasks', d.tasks || []);
    }}
    if (todayRes.ok) {{
      const d = await todayRes.json();
      setEl('workshopStatToday', d.total ?? '—');
      setEl('todayTaskCount', d.total ?? '—');
      renderTaskList('todayTasks', d.tasks || []);
    }}
  }} catch(e) {{ console.error('tasks load failed', e); }}
}}

async function syncAll() {{
  showToast('Syncing all sources...', 'info');
  try {{
    const r = await fetch('/api/home/sync', {{method:'POST'}});
    const d = await r.json();
    const newEmails = (d.summary && d.summary.new_emails) || 0;
    const newEvents = (d.summary && d.summary.new_events) || 0;
    showToast('Sync complete — ' + newEmails + ' new emails, ' + newEvents + ' new events', 'success');
    await loadHomeDashboard();
    if (currentView === 'email') loadHomeEmail();
    if (currentView === 'calendar') loadHomeCalendar();
  }} catch(e) {{ showToast('Sync failed: ' + e.message, 'error'); }}
}}

async function syncSource(source) {{
  try {{
    await fetch('/api/home/sync/' + source, {{method:'POST'}});
    showToast(source + ' synced', 'success');
    loadHomeDashboard();
  }} catch(e) {{ showToast('Sync failed: ' + e.message, 'error'); }}
}}

async function completeTask(taskId) {{
  try {{
    await fetch('/api/home/tasks/' + taskId + '/complete', {{method:'POST'}});
    showToast('Task completed', 'success');
    loadHomeTasks();
  }} catch(e) {{ showToast('Could not complete task', 'error'); }}
}}

/* ═══════════════════════════════════════════════════════════════
   HOME INTELLIGENCE RENDER FUNCTIONS
═══════════════════════════════════════════════════════════════ */
/* ─── Live Agents Ops Center ─── */

let _agentsRefreshTimer = null;

async function loadLiveAgents() {{
  try {{
    const res = await fetch('/api/agents');
    if (!res.ok) return;
    const d = await res.json();
    renderLiveAgents(d);
  }} catch(e) {{ console.error('live agents failed', e); }}
}}

function relTime(iso) {{
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.round(Math.abs(diff) / 60000);
  const sign = diff >= 0 ? '' : 'in ';
  if (mins < 1) return diff >= 0 ? 'just now' : 'in <1m';
  if (mins < 60) return sign + mins + 'm ago'.replace('ago','').trim() + (diff >= 0 ? ' ago' : '');
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return sign + h + 'h ' + (m > 0 ? m + 'm ' : '') + (diff >= 0 ? 'ago' : '');
}}

function renderLiveAgents(d) {{
  // Status bar
  const awake = d.awake_count ?? 0;
  const idle  = d.idle_count  ?? 0;
  const blk   = d.blocked_count ?? 0;
  setEl('rt-awake-count',   awake);
  setEl('rt-idle-count',    idle);
  setEl('rt-blocked-count', blk);

  const modeBadge = document.getElementById('rt-mode-badge');
  if (modeBadge) modeBadge.textContent = (d.active_mode || '—').replace(/-/g,' ').toUpperCase();

  const quietBadge = document.getElementById('rt-quiet-badge');
  if (quietBadge) quietBadge.style.display = d.quiet_hours_active ? '' : 'none';

  if (d.last_tick_at) {{
    setEl('rt-last-tick', 'last tick: ' + relTime(d.last_tick_at));
  }}

  // Overview card update
  const ovCountEl = document.getElementById('active-agents-count');
  if (ovCountEl) ovCountEl.textContent = awake + ' awake';
  const statEl = document.getElementById('stat-agents');
  if (statEl) statEl.textContent = awake;

  // Runtime grid
  const grid = document.getElementById('runtime-grid');
  if (!grid) return;

  const statuses = d.statuses || [];
  if (statuses.length === 0) {{
    grid.innerHTML = '<div class="agent-runtime-card state-idle"><div class="arc-header"><div class="arc-names"><div class="arc-label">No runtime data</div><div class="arc-id">Check that the agent loop is running.</div></div></div></div>';
    return;
  }}

  // Sort: awake first, then blocked, then idle
  const order = {{ awake: 0, blocked: 1, idle: 2 }};
  const sorted = [...statuses].sort((a, b) => (order[a.state]??3) - (order[b.state]??3));

  grid.innerHTML = sorted.map(agent => {{
    const state  = agent.state || 'idle';
    const label  = agent.label || agent.agent_id;
    const id     = agent.agent_id || '';
    const reason = agent.reason || '—';
    const owns   = agent.owns || [];
    const deps   = agent.blocked_dependencies || [];
    const lastRun = agent.last_run_at;
    const nextRun = agent.next_run_at;
    const cadence = agent.cadence_minutes;
    const prio   = agent.priority || '';
    const dueNow = agent.due_now;

    // state badge
    const badgeCls = state === 'awake' ? 'awake' : state === 'blocked' ? 'blocked' : 'idle';
    const badgeLbl = state.toUpperCase();

    // next run timing
    const nextMs = nextRun ? new Date(nextRun).getTime() - Date.now() : null;
    const nextStr = nextRun ? relTime(nextRun) : '—';
    const isOverdue = dueNow && nextMs !== null && nextMs < 0;

    // blocked warning html
    const blockHtml = deps.length > 0 ? `
      <div class="arc-block-warning">
        ⚠ WAITING ON: ${{deps.map(d => escHtml(d.toUpperCase())).join(' · ')}}
      </div>` : '';

    // owns tags
    const ownsHtml = owns.length > 0
      ? `<div class="arc-owns">${{owns.map(o => `<span class="arc-own-tag">${{escHtml(o)}}</span>`).join('')}}</div>`
      : '';

    // priority indicator
    const prioCls = prio === 'high' ? 'color:#0A1628;font-weight:600;' : prio === 'hold' ? 'color:#dc2626;' : '';
    const prioHtml = prio ? `<span style="font-size:8px;font-family:var(--font-mono);letter-spacing:0.08em;${{prioCls}}">${{prio.toUpperCase()}}</span>` : '';

    return `
    <div class="agent-runtime-card state-${{state}}">
      <div class="arc-header">
        <div class="arc-names">
          <div class="arc-label">${{escHtml(label)}}</div>
          <div class="arc-id">${{escHtml(id.replace(/-/g,' '))}}</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">
          <span class="state-badge ${{badgeCls}}">${{badgeLbl}}</span>
          ${{prioHtml}}
        </div>
      </div>
      <div class="arc-reason">"${{escHtml(reason)}}"</div>
      ${{blockHtml}}
      ${{ownsHtml}}
      <div class="arc-footer">
        <div class="arc-time">
          <div class="arc-time-lbl">LAST RUN</div>
          <div class="arc-time-val">${{lastRun ? relTime(lastRun) : '—'}}</div>
        </div>
        <div class="arc-time">
          <div class="arc-time-lbl">NEXT RUN</div>
          <div class="arc-time-val ${{isOverdue ? 'overdue' : ''}}">${{isOverdue ? 'OVERDUE' : nextStr}}</div>
        </div>
        ${{cadence ? `<div class="arc-cadence">every ${{cadence}}m</div>` : ''}}
      </div>
    </div>`;
  }}).join('');
}}

function toggleRoster() {{
  const sec = document.getElementById('roster-section');
  const btn = document.querySelector('.roster-toggle');
  if (!sec) return;
  const showing = sec.style.display !== 'none';
  sec.style.display = showing ? 'none' : 'block';
  if (btn) btn.textContent = showing ? 'SHOW ROSTER ▾' : 'HIDE ROSTER ▴';
  if (!showing) renderAgents('all');
}}

/* ═══════════════════════════════════════════════════════════════
   HUDDLE VIEW
═══════════════════════════════════════════════════════════════ */

async function loadHuddle() {{
  const grid = document.getElementById('huddle-reports-grid');
  const approvalsSection = document.getElementById('huddle-approvals');
  const approvalsList = document.getElementById('huddle-approvals-list');
  if (grid) grid.innerHTML = '<div class="skeleton-block" style="height:140px;border-radius:8px;"></div>'.repeat(3);

  try {{
    const res = await fetch('/api/huddle');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const d = await res.json();

    // Update meta bar
    const awEl = document.getElementById('huddle-active-work');
    if (awEl) awEl.textContent = (d.total_active_work || 0) + ' active items';
    const blEl = document.getElementById('huddle-blockers-count');
    if (blEl) blEl.textContent = (d.blockers || []).length + ' blockers';
    const apEl = document.getElementById('huddle-approvals-count');
    if (apEl) apEl.textContent = (d.approvals_needed || []).length + ' awaiting approval';

    // Approvals needed
    const approvals = d.approvals_needed || [];
    if (approvals.length > 0 && approvalsSection && approvalsList) {{
      approvalsSection.style.display = 'block';
      approvalsList.innerHTML = approvals.map(a => {{
        const work_id = escHtml(a.work_id || '');
        const title = escHtml(a.title || 'Untitled');
        const agent = escHtml(a.agent || a.agent_id || '?');
        const fullProposal = escHtml(a.proposal || a.idea || '');
        const shortProposal = escHtml((a.proposal || a.idea || '').slice(0, 120));
        const proposalHtml = fullProposal.length > 120
          ? '<div class="approval-item-desc expand-toggle" data-full="' + fullProposal + '" data-short="' + shortProposal + '" data-expanded="0" title="Click to expand" onclick="toggleExpand(this)">' + shortProposal + '…</div>'
          : '<div class="approval-item-desc">' + shortProposal + '</div>';
        return '<div class="approval-item">' +
          '<div>' +
            '<div class="approval-item-agent">' + agent + '</div>' +
            '<div class="approval-item-title">' + title + '</div>' +
            proposalHtml +
          '</div>' +
          '<div class="approval-item-actions">' +
            '<button class="approve-btn" data-wid="' + work_id + '" onclick="approveWorkItem(this.dataset.wid)">✓ Approve</button>' +
            '<button class="reject-btn" data-wid="' + work_id + '" onclick="rejectWorkItem(this.dataset.wid)">✗ Pass</button>' +
          '</div>' +
        '</div>';
      }}).join('');
    }} else if (approvalsSection) {{
      approvalsSection.style.display = 'none';
    }}

    // Standup cards
    const reports = d.agent_reports || [];
    if (grid) {{
      if (reports.length === 0) {{
        grid.innerHTML = '<div class="pi-empty">No standups generated yet — agents will report after their first run.</div>';
        return;
      }}
      grid.innerHTML = reports.map(r => renderHuddleCard(r)).join('');
    }}
  }} catch (e) {{
    if (grid) grid.innerHTML = '<div class="pi-empty">Huddle unavailable: ' + escHtml(e.message) + '</div>';
  }}
}}

function renderHuddleCard(r) {{
  const name = escHtml(r.agent_name || r.agent_id);
  const domain = escHtml(r.domain || '');
  const source = escHtml(r.source || 'stub');
  const yesterday = escHtml(r.yesterday || 'No report.');
  const today = escHtml(r.today || '—');
  const needs = r.needs || 'Nothing needed today.';
  const hasNeed = needs && !needs.toLowerCase().includes('nothing needed') && !needs.toLowerCase().includes('running independently');
  const needsHtml = escHtml(needs);
  const highlights = (r.highlights || []).slice(0, 4);
  const activeCount = r.active_work_count || 0;

  const highlightHtml = highlights.length
    ? '<div class="hc-highlights">' + highlights.map(h => '<span class="hc-highlight-tag">' + escHtml(h) + '</span>').join('') + '</div>'
    : '';

  return '<div class="huddle-card">' +
    '<div class="hc-header">' +
      '<div><div class="hc-name">' + name + '</div><div class="hc-domain">' + domain + '</div></div>' +
      '<span class="hc-source-badge">' + source + '</span>' +
    '</div>' +
    '<div class="hc-section">' +
      '<div class="hc-section-label">Yesterday</div>' +
      '<div class="hc-text">' + yesterday + '</div>' +
    '</div>' +
    '<div class="hc-section">' +
      '<div class="hc-section-label">Today</div>' +
      '<div class="hc-text">' + today + '</div>' +
    '</div>' +
    '<div class="hc-section">' +
      '<div class="hc-section-label">Needs</div>' +
      '<div class="hc-needs' + (hasNeed ? ' has-need' : '') + '">' + needsHtml + '</div>' +
    '</div>' +
    highlightHtml +
    (activeCount > 0 ? '<div class="hc-work-count">' + activeCount + ' active work item' + (activeCount !== 1 ? 's' : '') + ' in pipeline</div>' : '') +
  '</div>';
}}

async function approveWorkItem(workId) {{
  if (!workId) return;
  try {{
    const res = await fetch('/api/agent-work/approve/' + encodeURIComponent(workId), {{method:'POST'}});
    if (res.ok) {{ loadHuddle(); loadPassiveIncomePipeline(); }}
    else alert('Approval failed: HTTP ' + res.status);
  }} catch (e) {{ alert('Approval error: ' + e.message); }}
}}

async function rejectWorkItem(workId) {{
  if (!workId) return;
  const reason = prompt('Reason for passing on this? (optional)') || 'Declined';
  try {{
    const res = await fetch('/api/agent-work/reject/' + encodeURIComponent(workId), {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{reason}})
    }});
    if (res.ok) {{ loadHuddle(); loadPassiveIncomePipeline(); }}
    else alert('Reject failed: HTTP ' + res.status);
  }} catch (e) {{ alert('Reject error: ' + e.message); }}
}}

async function loadPassiveIncomePipeline() {{
  const grid = document.getElementById('huddle-pi-pipeline');
  if (!grid) return;
  grid.innerHTML = '<div class="skeleton-block" style="height:80px;border-radius:8px;"></div>';
  try {{
    const res = await fetch('/api/agent-work/passive-income');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const d = await res.json();
    const items = (d.items || []).slice(0, 12);
    if (items.length === 0) {{
      grid.innerHTML = '<div class="pi-empty">No passive income ideas yet — Mantis will dream some up on her next run.</div>';
      return;
    }}
    grid.innerHTML = items.map(item => {{
      const status = item.status || 'dreamed';
      const title = escHtml(item.title || 'Untitled');
      const fullIdea = escHtml(item.idea || item.proposal || item.research || '');
      const shortIdea = escHtml((item.idea || item.proposal || item.research || '').slice(0, 120));
      const ideaHtml = fullIdea.length > 120
        ? '<div class="pi-card-idea expand-toggle" data-full="' + fullIdea + '" data-short="' + shortIdea + '" data-expanded="0" title="Click to expand" onclick="toggleExpand(this)">' + shortIdea + '…</div>'
        : '<div class="pi-card-idea">' + shortIdea + '</div>';
      const agent = escHtml(item.agent_id || '?');
      return '<div class="pi-card">' +
        '<span class="pi-card-status pi-status-' + status + '">' + status + '</span>' +
        '<div class="pi-card-title">' + title + '</div>' +
        ideaHtml +
      '</div>';
    }}).join('');
  }} catch (e) {{
    grid.innerHTML = '<div class="pi-empty">Pipeline unavailable: ' + escHtml(e.message) + '</div>';
  }}
}}

/* ─── Party Mode + Dossier System ─── */

async function loadPartyStatus() {{
  try {{
    const res = await fetch('/api/party-mode/status');
    if (!res.ok) return;
    const d = await res.json();
    const bar = document.getElementById('party-mode-bar');
    const txt = document.getElementById('party-bar-text');
    if (!bar || !txt) return;
    if (d.status === 'running') {{
      bar.style.display = 'flex';
      const built = (d.dossiers_built || []).length;
      const last = d.last_log || 'Working...';
      txt.textContent = 'Agents are researching overnight · ' + built + ' dossier' + (built !== 1 ? 's' : '') + ' built · ' + escHtml(last);
    }} else if (d.status === 'completed') {{
      bar.style.display = 'flex';
      bar.querySelector('.party-bar-indicator').style.background = '#94a3b8';
      bar.querySelector('.party-bar-indicator').style.animation = 'none';
      const built = (d.dossiers_built || []).length;
      txt.textContent = 'Last night: ' + built + ' dossier' + (built !== 1 ? 's' : '') + ' completed · Session ended ' + (d.ended_at ? new Date(d.ended_at).toLocaleTimeString() : '');
    }} else {{
      bar.style.display = 'none';
    }}
  }} catch (e) {{}}
}}

async function startPartyMode() {{
  try {{
    const res = await fetch('/api/party-mode/start', {{method:'POST'}});
    const d = await res.json();
    if (d.status === 'started' || d.status === 'already_running') {{
      setTimeout(() => {{ loadPartyStatus(); loadDossiers(); }}, 2000);
    }}
  }} catch (e) {{ alert('Could not start party mode: ' + e.message); }}
}}

async function loadDossiers() {{
  const grid = document.getElementById('huddle-dossier-grid');
  const section = document.getElementById('dossier-section');
  if (!grid) return;
  try {{
    const res = await fetch('/api/dossiers');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const d = await res.json();
    const dossiers = (d.dossiers || []).filter(x => x.status !== 'presented');
    if (dossiers.length === 0) {{
      section.style.display = 'none';
      return;
    }}
    section.style.display = 'block';
    grid.innerHTML = dossiers.map(renderDossierCard).join('');
  }} catch (e) {{
    grid.innerHTML = '<div class="pi-empty">Dossiers unavailable.</div>';
  }}
}}

function renderDossierCard(d) {{
  const title = escHtml(d.title || 'Untitled');
  const summary = escHtml((d.executive_summary || d.market_opportunity || '').slice(0, 160));
  const status = d.status || 'building';
  const low = d.revenue_estimate_low || 0;
  const high = d.revenue_estimate_high || 0;
  const effort = d.effort_hours || 0;
  const conf = Math.min(10, Math.max(0, d.confidence_score || 0));
  const confPct = (conf / 10 * 100).toFixed(0);
  const revenueStr = (low > 0 || high > 0) ? '$' + low.toLocaleString() + '–$' + high.toLocaleString() + '/mo' : 'TBD';
  const effortStr = effort > 0 ? effort + 'h to MVP' : 'TBD';
  const wid = escHtml(d.work_id || '');
  const did = d.dossier_id || '';
  const qaFailed = d.qa_passed === false;
  const qaIssues = (d.qa_issues || []);
  const qaIssueCount = qaIssues.length;
  const qaRetries = d.qa_retries || 0;
  // QA warning badge — shown on cards that have unresolved issues
  const qaBadge = qaFailed
    ? '<span class="dossier-qa-badge" title="' + escHtml(qaIssues.join(' | ')) + '">⚠ ' + qaIssueCount + ' QA issue' + (qaIssueCount !== 1 ? 's' : '') + '</span>'
    : (qaRetries > 0 ? '<span class="dossier-qa-ok" title="Passed QA after ' + qaRetries + ' retr' + (qaRetries===1?'y':'ies') + '">✓ QA verified</span>' : '<span class="dossier-qa-ok">✓ QA verified</span>');
  return '<div class="dossier-card' + (qaFailed ? ' dossier-card-qa-warn' : '') + '" onclick="openDossier(\\'' + did + '\\')">' +
    '<div class="dossier-card-header-row">' +
      '<span class="dossier-card-status dc-status-' + status + '">' + status + '</span>' +
      qaBadge +
    '</div>' +
    '<div class="dossier-card-title">' + title + '</div>' +
    '<div class="dossier-card-summary">' + summary + (summary.length >= 160 ? '…' : '') + '</div>' +
    '<div class="dossier-metrics">' +
      '<div class="dossier-metric"><strong>' + revenueStr + '</strong> revenue est.</div>' +
      '<div class="dossier-metric"><strong>' + effortStr + '</strong></div>' +
      '<div class="dossier-metric"><strong>' + conf.toFixed(1) + '/10</strong> confidence</div>' +
    '</div>' +
    '<div class="dossier-confidence-bar"><div class="dossier-confidence-fill" style="width:' + confPct + '%"></div></div>' +
    '<div class="dossier-card-actions">' +
      '<button class="dossier-read-btn" onclick="event.stopPropagation();openDossier(\\'' + did + '\\')">📄 Read Full Dossier</button>' +
      (wid ? '<button class="dossier-approve-btn" onclick="event.stopPropagation();approveWorkItem(\\'' + wid + '\\')">✓ Greenlight</button>' : '') +
    '</div>' +
  '</div>';
}}

/* ── Inline expand/collapse for truncated text ── */
function toggleExpand(el) {{
  const full = el.dataset.full;
  const short = el.dataset.short;
  if (!full || !short) return;
  const expanded = el.dataset.expanded === '1';
  if (expanded) {{
    el.textContent = short + '…';
    el.dataset.expanded = '0';
    el.title = 'Click to expand';
  }} else {{
    el.textContent = full;
    el.dataset.expanded = '1';
    el.title = 'Click to collapse';
  }}
}}

function closeDossierModal() {{
  const ov = document.getElementById('dossier-modal-overlay');
  if (ov) ov.remove();
}}

/* ── Lightweight markdown → HTML renderer for dossier sections ── */
function mdToHtml(md) {{
  if (!md) return '';
  const e = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  // Inline: bold, italic (applied to already-escaped text)
  const inline = s => s
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>');

  const lines = md.split('\n');
  const out = [];
  let inUl = false, inOl = false, inP = false;

  const closeList = () => {{
    if (inUl) {{ out.push('</ul>'); inUl = false; }}
    if (inOl) {{ out.push('</ol>'); inOl = false; }}
  }};
  const closeP = () => {{ if (inP) {{ out.push('</p>'); inP = false; }} }};

  for (const raw of lines) {{
    const line = raw.trimEnd();

    // blank line
    if (!line.trim()) {{
      closeList();
      closeP();
      continue;
    }}

    // heading
    const h3 = line.match(/^###?\s+(.*)/);
    const h4 = line.match(/^####\s+(.*)/);
    if (h4) {{ closeList(); closeP(); out.push('<h4>' + inline(e(h4[1])) + '</h4>'); continue; }}
    if (h3) {{ closeList(); closeP(); out.push('<h3>' + inline(e(h3[1])) + '</h3>'); continue; }}

    // unordered list item
    const ul = line.match(/^[-*•]\s+(.*)/);
    if (ul) {{
      closeP();
      if (!inUl) {{ if (inOl) {{ out.push('</ol>'); inOl=false; }} out.push('<ul>'); inUl=true; }}
      out.push('<li>' + inline(e(ul[1])) + '</li>');
      continue;
    }}

    // ordered list item
    const ol = line.match(/^\d+\.\s+(.*)/);
    if (ol) {{
      closeP();
      if (!inOl) {{ if (inUl) {{ out.push('</ul>'); inUl=false; }} out.push('<ol>'); inOl=true; }}
      out.push('<li>' + inline(e(ol[1])) + '</li>');
      continue;
    }}

    // regular paragraph text
    closeList();
    if (!inP) {{ out.push('<p>'); inP = true; }} else {{ out.push('<br>'); }}
    out.push(inline(e(line)));
  }}
  closeList();
  closeP();
  return out.join('');
}}

async function openDossier(dossierId) {{
  const existing = document.getElementById('dossier-modal-overlay');
  if (existing) existing.remove();

  let dossier = null;
  try {{
    const res = await fetch('/api/dossiers');
    const all = await res.json();
    dossier = (all.dossiers || []).find(d => d.dossier_id === dossierId);
  }} catch (e) {{ return; }}
  if (!dossier) return;

  const overlay = document.createElement('div');
  overlay.className = 'dossier-modal-overlay';
  overlay.id = 'dossier-modal-overlay';
  overlay.onclick = (e) => {{ if (e.target === overlay) overlay.remove(); }};

  const sections = [
    ['Executive Summary', dossier.executive_summary],
    ['Market Opportunity', dossier.market_opportunity],
    ['Competitive Landscape', dossier.competitive_landscape],
    ['Technical Requirements', dossier.technical_requirements],
    ['Revenue Model', dossier.revenue_model],
    ['Risk Assessment', dossier.risk_assessment],
    ['90-Day Implementation Plan', dossier.implementation_plan],
    ['First Action to Approve', dossier.first_action],
  ];

  const sourcesHtml = (dossier.web_sources || []).length > 0
    ? '<div class="dossier-section-block">' +
        '<div class="dossier-section-heading">Web Sources Researched</div>' +
        '<div class="dossier-sources-list">' +
          (dossier.web_sources || []).slice(0, 8).map(u => '<a href="' + escHtml(u) + '" target="_blank">' + escHtml(u.slice(0,60)) + '…</a><br>').join('') +
        '</div></div>'
    : '';

  const wid = escHtml(dossier.work_id || '');
  const qaFailed = dossier.qa_passed === false;
  const qaIssues = (dossier.qa_issues || []);
  const qaRetries = dossier.qa_retries || 0;

  // QA panel — only shown when issues exist
  const qaHtml = qaFailed
    ? '<div class="dossier-qa-issues-block">' +
        '<div class="dossier-qa-issues-title">⚠ QA Issues — Adversarial Review Found Problems</div>' +
        qaIssues.map(i => '<div class="dossier-qa-issue-item">' + escHtml(i) + '</div>').join('') +
        '<div style="font-size:10px;color:rgba(220,230,255,0.45);margin-top:6px;">Sections were regenerated ' + qaRetries + ' time(s). Use judgment when reviewing.</div>' +
      '</div>'
    : (qaRetries > 0
        ? '<div style="font-size:10px;color:#22c55e;margin-bottom:12px;">✓ All sections passed adversarial QA after ' + qaRetries + ' retr' + (qaRetries===1?'y':'ies') + '</div>'
        : '<div style="font-size:10px;color:#22c55e;margin-bottom:12px;">✓ All sections passed adversarial QA on first attempt</div>');

  overlay.innerHTML = '<div class="dossier-modal">' +
    '<div class="dossier-modal-header">' +
      '<div>' +
        '<div class="dossier-modal-title">' + escHtml(dossier.title || 'Dossier') + '</div>' +
        '<div style="font-size:10px;color:rgba(180,195,230,0.6);margin-top:4px;">Confidence ' + (dossier.confidence_score||0).toFixed(1) + '/10 · ' + (dossier.web_sources||[]).length + ' sources · Built by Mantis</div>' +
      '</div>' +
      '<button class="dossier-modal-close" onclick="closeDossierModal()">✕</button>' +
    '</div>' +
    qaHtml +
    sections.filter(([,v]) => v).map(([label, text]) =>
      '<div class="dossier-section-block">' +
        '<div class="dossier-section-heading">' + escHtml(label) + '</div>' +
        '<div class="dossier-section-text">' + mdToHtml(text) + '</div>' +
      '</div>'
    ).join('') +
    sourcesHtml +
    '<div class="dossier-modal-actions">' +
      (wid && !qaFailed ? '<button class="dossier-modal-approve" onclick="approveWorkItem(\\'' + wid + '\\');closeDossierModal()">✓ Greenlight This Idea</button>' : '') +
      (wid && qaFailed ? '<button class="dossier-modal-approve" style="background:rgba(239,68,68,0.15);border-color:rgba(239,68,68,0.3);color:#ef4444;" onclick="approveWorkItem(\\'' + wid + '\\');closeDossierModal()">⚠ Greenlight Anyway</button>' : '') +
      '<button class="dossier-modal-pass" onclick="closeDossierModal()">Close</button>' +
    '</div>' +
    '<div class="dossier-chat-panel">' +
      '<div class="dossier-chat-label">💬 Ask or Refine This Idea</div>' +
      '<div class="dossier-chat-row">' +
        '<textarea class="dossier-chat-input" id="dossier-chat-input-' + did + '" ' +
          'placeholder="Ask a question or request a change... e.g. &quot;What&apos;s the biggest risk?&quot; or &quot;Reframe this for B2B healthcare.&quot;" ' +
          'rows="2" onkeydown="if(event.key===\\'Enter\\'&&!event.shiftKey){{event.preventDefault();dossierChat(\\'' + did + '\\')}}"></textarea>' +
        '<button class="dossier-chat-send" id="dossier-chat-btn-' + did + '" onclick="dossierChat(\\'' + did + '\\')">Ask →</button>' +
      '</div>' +
      '<div class="dossier-chat-response" id="dossier-chat-resp-' + did + '"></div>' +
    '</div>' +
  '</div>';
  document.body.appendChild(overlay);
}}

async function dossierChat(dossierId) {{
  const inp = document.getElementById('dossier-chat-input-' + dossierId);
  const btn = document.getElementById('dossier-chat-btn-' + dossierId);
  const resp = document.getElementById('dossier-chat-resp-' + dossierId);
  if (!inp || !btn || !resp) return;
  const msg = inp.value.trim();
  if (!msg) return;

  btn.disabled = true;
  btn.textContent = '…';
  resp.className = 'dossier-chat-response visible';
  resp.innerHTML = '<span style="opacity:0.5;font-style:italic">Thinking…</span>';

  try {{
    const res = await fetch('/api/dossiers/' + dossierId + '/chat', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{message: msg}})
    }});
    const data = await res.json();
    if (data.error) {{
      resp.innerHTML = '<span style="color:#ef4444">Error: ' + escHtml(data.error) + '</span>';
    }} else {{
      resp.innerHTML = mdToHtml(data.response || '(no response)');
    }}
  }} catch(e) {{
    resp.innerHTML = '<span style="color:#ef4444">Request failed: ' + escHtml(e.message) + '</span>';
  }}
  btn.disabled = false;
  btn.textContent = 'Ask →';
}}

/* ─── Overview mini-card loaders (populate overview-* elements) ─── */

async function loadOverviewAgents() {{
  try {{
    const res = await fetch('/api/agents');
    if (!res.ok) return;
    const d = await res.json();
    const agents = d.agents || {{}};
    const names = Object.keys(agents);
    const awake = names.filter(n => agents[n].state === 'awake');
    const blocked = names.filter(n => agents[n].state === 'blocked');
    const idle = names.filter(n => agents[n].state === 'idle');
    const total = names.length;

    const countEl = document.getElementById('active-agents-count');
    if (countEl) countEl.textContent = awake.length + ' awake';

    const statEl = document.getElementById('stat-agents');
    if (statEl) statEl.textContent = awake.length;

    const listEl = document.getElementById('active-agents-list');
    if (!listEl) return;

    if (total === 0) {{
      listEl.innerHTML = '<div class="list-row"><span class="dot dot-standby"></span><div class="list-row-name">No agents running</div></div>';
      return;
    }}

    const rows = names.slice(0, 6).map(n => {{
      const s = agents[n].state || 'idle';
      const dot = s === 'awake' ? 'dot-success' : s === 'blocked' ? 'dot-error' : 'dot-standby';
      const label = s.toUpperCase();
      const niceName = n.replace(/-/g,' ').replace(/\b\w/g, c => c.toUpperCase());
      return `<div class="list-row"><span class="dot ${{dot}}"></span><div style="flex:1"><div class="list-row-name">${{escHtml(niceName)}}</div></div><span style="font-size:9px;color:var(--text-3);font-family:var(--font-mono);">${{label}}</span></div>`;
    }}).join('');

    const more = total > 6 ? `<div class="list-row-sub" style="padding-top:4px;text-align:right;cursor:pointer;color:var(--accent,#8b5cf6);" onclick="switchView('agents')" title="View all agents">+${{total - 6}} more →</div>` : '';
    listEl.innerHTML = rows + more;
  }} catch(e) {{ console.error('agents overview failed', e); }}
}}

async function loadOverviewCatalyst() {{
  try {{
    const res = await fetch('/api/catalyst-overview');
    if (!res.ok) return;
    const d = await res.json();
    const lanes = d.portfolio_lanes || [];
    const connectors = (d.connectors || []).filter(c => c.status === 'active' || c.status === 'local');

    const flowsEl = document.getElementById('catalyst-flows');
    if (flowsEl) flowsEl.textContent = lanes.length + ' lanes';

    const el = document.getElementById('overview-catalyst');
    if (!el) return;

    if (lanes.length === 0) {{
      el.innerHTML = '<div class="list-row-sub">No portfolio lanes configured.</div>';
      return;
    }}

    el.innerHTML = lanes.slice(0, 3).map(lane => `
      <div class="list-row">
        <span class="dot dot-standby"></span>
        <div><div class="list-row-name">${{escHtml(lane.label)}}</div></div>
      </div>
    `).join('') + (lanes.length > 3 ? `<div class="list-row-sub" style="text-align:right;cursor:pointer;color:var(--accent,#8b5cf6);" onclick="switchView('catalyst')" title="View all lanes">+${{lanes.length - 3}} more lanes →</div>` : '');
  }} catch(e) {{ console.error('loadOverviewCatalyst failed', e); }}
}}

async function loadOverviewChronicle() {{
  try {{
    const res = await fetch('/api/chronicle/recent');
    if (!res.ok) return;
    const d = await res.json();
    const entries = d.entries || [];
    const total = d.total || entries.length;

    const countEl = document.getElementById('chronicle-count');
    if (countEl) countEl.textContent = total ? total + ' entries' : '—';

    const statEl = document.getElementById('stat-memory');
    if (statEl) statEl.textContent = total || '—';

    const el = document.getElementById('overview-chronicle');
    if (!el) return;

    if (entries.length === 0) {{
      el.innerHTML = '<div class="list-row-sub" style="color:var(--text-3);font-style:italic;">No chronicle entries yet.</div>';
      return;
    }}

    el.innerHTML = entries.slice(0, 2).map(e => {{
      const fullText = e.content || e.text || '';
      const text = fullText.slice(0, 80);
      const ts = e.ts || e.created_at || '';
      const tsStr = ts ? new Date(ts).toLocaleDateString([], {{month:'short', day:'numeric'}}) : '';
      const textHtml = fullText.length > 80
        ? `<div class="expand-toggle" data-full="${{escHtml(fullText)}}" data-short="${{escHtml(text)}}" data-expanded="0" title="Click to expand" onclick="toggleExpand(this)" style="font-size:12px;color:var(--text-2);line-height:1.4;cursor:pointer;">${{escHtml(text)}}…</div>`
        : `<div style="font-size:12px;color:var(--text-2);line-height:1.4;">${{escHtml(text)}}</div>`;
      return `<div style="margin-bottom:8px;"><div style="font-size:10px;color:var(--text-3);font-family:var(--font-mono);">${{escHtml(tsStr)}}</div>${{textHtml}}</div>`;
    }}).join('');
    if (total > 2) {{
      el.innerHTML += `<div class="list-row-sub" style="text-align:right;cursor:pointer;color:var(--accent,#8b5cf6);margin-top:4px;" onclick="switchView('chronicle')" title="View all entries">+${{total - 2}} more entries →</div>`;
    }}
  }} catch(e) {{ console.error('loadOverviewChronicle failed', e); }}
}}

async function loadOverviewPublishing() {{
  try {{
    const res = await fetch('/api/publishing/dashboard');
    if (!res.ok) return;
    const d = await res.json();
    const books = d.active_books || d.books || [];

    const el = document.getElementById('overview-publishing');
    if (!el) return;

    if (books.length === 0) {{
      el.innerHTML = '<div class="list-row-sub" style="color:var(--text-3);font-style:italic;">No active books.</div>';
      return;
    }}

    const STAGES = ['Outline','Draft','Edit','Review','Polish','Cover','Format','Proof','Publish'];
    el.innerHTML = books.slice(0, 3).map(book => {{
      const stage = book.current_stage || book.stage || '—';
      const stageStr = typeof stage === 'number' ? (STAGES[stage] || '—') : stage;
      const pct = book.stages_complete != null && book.total_stages
        ? Math.round((book.stages_complete / book.total_stages) * 100) : null;
      const barHtml = pct != null
        ? `<div style="margin-top:4px;height:3px;background:rgba(0,0,0,0.08);border-radius:2px;"><div style="width:${{pct}}%;height:100%;background:var(--hue);border-radius:2px;"></div></div>`
        : '';
      return `<div style="margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;align-items:baseline;">
          <div style="font-size:12px;color:var(--text-1);font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:70%;">${{escHtml(book.title || '—')}}</div>
          <div style="font-size:9px;color:var(--hue);font-family:var(--font-mono);text-transform:uppercase;">${{escHtml(stageStr)}}</div>
        </div>
        ${{barHtml}}
      </div>`;
    }}).join('');
  }} catch(e) {{ console.error('loadOverviewPublishing failed', e); }}
}}

function updateOverviewHomeCards(d) {{
  const em = d.email || {{}};
  const cal = d.calendar || {{}};
  setEl('overviewGmailUnread', em.gmail_unread != null ? em.gmail_unread : '—');
  setEl('overviewOutlookUnread', em.outlook_unread != null ? em.outlook_unread : '—');
  const totalUnread = em.total_unread != null ? em.total_unread : '—';
  setEl('emailUnreadBadge', totalUnread);
  setEl('emailStatUnread', totalUnread);
  setEl('emailStatGmail', em.gmail_unread != null ? em.gmail_unread : '—');
  setEl('emailStatOutlook', em.outlook_unread != null ? em.outlook_unread : '—');
  const todayCount = cal.today_count != null ? cal.today_count : '—';
  setEl('overviewTodayEvents', todayCount);
  setEl('calEventCount', todayCount !== '—' ? todayCount + ' today' : '—');
  const upcoming = cal.upcoming_3_days;
  const next = upcoming && upcoming.length > 0 ? upcoming[0] : null;
  setEl('overviewNextEvent', next ? escHtml(next.title) : 'No upcoming events');
  if (d.projects) {{
    setEl('overviewActiveProjects', d.projects.active != null ? d.projects.active : '—');
  }}
}}

function setEl(id, val) {{
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}}

function renderEmailList(emails, filter) {{
  const list = document.getElementById('emailList');
  if (!list) return;
  let items = emails;
  if (filter && filter !== 'all') items = emails.filter(e => e.source === filter);
  if (items.length === 0) {{
    list.innerHTML = '<div class="loading-state">No emails found.</div>';
    return;
  }}
  list.innerHTML = items.map(em => {{
    const unreadCls = !em.is_read ? 'unread' : '';
    const flaggedCls = em.is_flagged ? 'flagged' : '';
    const sender = escHtml(em.sender_name || em.sender_email || '—');
    const subject = escHtml(em.subject || '(no subject)');
    const snippet = escHtml(em.snippet || '');
    const src = em.source || 'gmail';
    const timeStr = em.received_at ? fmtTime(em.received_at) : '—';
    const impHtml = em.importance === 'high' ? '<div class="email-importance">!</div>' : '';
    return `<div class="email-item ${{unreadCls}}" data-id="${{em.id}}" data-source="${{src}}">
      <div class="email-source-dot ${{src}}"></div>
      <div class="email-body">
        <div class="email-from">${{sender}}</div>
        <div class="email-subject ${{flaggedCls}}">${{subject}}</div>
        <div class="email-snippet">${{snippet}}</div>
      </div>
      <div class="email-meta">
        <div class="email-time">${{timeStr}}</div>
        ${{impHtml}}
      </div>
    </div>`;
  }}).join('');
}}

function filterEmail(src, btn) {{
  emailFilter = src;
  document.querySelectorAll('.source-tab').forEach(t => t.classList.remove('active'));
  if (btn) btn.classList.add('active');
  renderEmailList(emailCache, src);
}}

function renderEventList(containerId, events) {{
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!events || events.length === 0) {{
    el.innerHTML = '<div class="empty-state">No events.</div>';
    return;
  }}
  el.innerHTML = events.map(ev => {{
    const timeStr = ev.all_day ? 'ALL DAY' : fmtTime(ev.start_time);
    const dur = (!ev.all_day && ev.start_time && ev.end_time) ? fmtDuration(ev.start_time, ev.end_time) : '';
    const src = ev.source || 'google';
    const dotSrc = src.includes('google') ? 'google' : src.includes('outlook') ? 'outlook' : 'cozi';
    const locHtml = ev.location ? `<div class="event-location">📍 ${{escHtml(ev.location)}}</div>` : '';
    return `<div class="event-item">
      <div class="event-time-col">
        <div class="event-time">${{escHtml(timeStr)}}</div>
        <div class="event-source-dot ${{dotSrc}}"></div>
      </div>
      <div class="event-body">
        <div class="event-title">${{escHtml(ev.title || '—')}}</div>
        ${{locHtml}}
      </div>
      <div class="event-duration">${{escHtml(dur)}}</div>
    </div>`;
  }}).join('');
}}

function renderHomeProjects(projects, total) {{
  const el = document.getElementById('homeProjectsList');
  const badge = document.getElementById('homeProjectsBadge');
  if (badge) badge.textContent = total != null ? total : projects.length;
  if (!el) return;
  if (!projects || projects.length === 0) {{
    el.innerHTML = '<div class="loading-state" style="padding:12px 0;text-align:left;">No active projects.</div>';
    return;
  }}
  el.innerHTML = projects.map(p => {{
    const trackCls = p.track === 'revenue' ? 'track-revenue' : p.track === 'savings' ? 'track-savings' : 'track-ops';
    const val = p.projected_value ? '$' + Number(p.projected_value).toLocaleString() : '—';
    const lbl = p.track === 'revenue' ? 'PROJ REVENUE' : p.track === 'savings' ? 'PROJ SAVINGS' : 'VALUE';
    return `<div class="project-item">
      <div>
        <div class="project-name">${{escHtml(p.title || '—')}}</div>
        <div class="project-meta">
          <span class="project-track ${{trackCls}}">${{escHtml((p.track || 'ops').toUpperCase())}}</span>
          &nbsp; ${{escHtml(p.category || p.status || '—')}}
        </div>
      </div>
      <div style="text-align:right;">
        <div class="project-value">${{val}}</div>
        <div class="project-value-lbl">${{lbl}}</div>
      </div>
    </div>`;
  }}).join('');
}}

function renderTaskList(containerId, tasks) {{
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!tasks || tasks.length === 0) {{
    el.innerHTML = '<div class="loading-state" style="padding:8px 0;text-align:left;">None.</div>';
    return;
  }}
  el.innerHTML = tasks.map(t => {{
    const prioClass = t.priority === 'high' ? 'dot-error' : t.priority === 'medium' ? 'dot-gold' : 'dot-standby';
    const due = t.due_date ? ' · Due ' + t.due_date : '';
    const blocked = t.blocked_reason ? ' <span style="color:var(--crimson);font-size:10px;">BLOCKED</span>' : '';
    return `<div class="list-row">
      <span class="dot ${{prioClass}}"></span>
      <div style="flex:1;min-width:0;">
        <div class="list-row-name" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${{escHtml(t.title || '—')}}${{blocked}}</div>
        <div class="list-row-sub">${{escHtml(t.status || '—')}}${{escHtml(due)}}</div>
      </div>
      <button class="btn btn-outline btn-sm" onclick="completeTask('${{t.id}}')">Done</button>
    </div>`;
  }}).join('');
}}

/* ── Time helpers ── */
function fmtTime(iso) {{
  if (!iso) return '—';
  try {{
    const d = new Date(iso);
    return d.toLocaleTimeString([], {{hour:'2-digit', minute:'2-digit'}});
  }} catch(_) {{ return iso; }}
}}

function fmtDuration(start, end) {{
  try {{
    const s = new Date(start);
    const e = new Date(end);
    const mins = Math.round((e - s) / 60000);
    if (mins < 60) return mins + 'm';
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return h + 'h' + (m ? m + 'm' : '');
  }} catch(_) {{ return ''; }}
}}

async function sendCommand(text) {{
  if (!text.trim()) return;

  /* ── Switch to chat view and reveal it ── */
  switchView('chat');

  const chatArea = document.getElementById('chat-area');
  const emptyEl  = document.getElementById('chat-empty');
  if (emptyEl) emptyEl.style.display = 'none';

  /* ── Helper: append a message row ── */
  function appendMsg(role, content, meta) {{
    const row = document.createElement('div');
    row.className = 'msg-row ' + role;

    const avatarText = role === 'user' ? 'CB' : 'J';
    const bubble = role === 'jarvis'
      ? `<div class="msg-bubble">${{escHtml(content)}}</div>`
      : `<div class="msg-bubble">${{escHtml(content)}}</div>`;

    row.innerHTML = `
      <div class="msg-avatar">${{avatarText}}</div>
      <div>
        ${{bubble}}
        ${{meta ? `<div class="msg-meta">${{escHtml(meta)}}</div>` : ''}}
      </div>`;
    chatArea.appendChild(row);
    chatArea.scrollTop = chatArea.scrollHeight;
    return row;
  }}

  /* ── Append user message ── */
  const now = new Date().toLocaleTimeString([], {{hour:'2-digit', minute:'2-digit'}});
  appendMsg('user', text, now);

  /* ── Typing indicator ── */
  const typingRow = document.createElement('div');
  typingRow.className = 'msg-row jarvis msg-typing';
  typingRow.innerHTML = `
    <div class="msg-avatar">J</div>
    <div><div class="msg-bubble">
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
    </div></div>`;
  chatArea.appendChild(typingRow);
  chatArea.scrollTop = chatArea.scrollHeight;

  try {{
    const res = await fetch('/api/respond', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ request: text, actor: 'Chris', source: 'glass' }})
    }});

    chatArea.removeChild(typingRow);

    if (!res.ok) {{
      appendMsg('jarvis', 'Command failed — JARVIS returned ' + res.status, null);
      return;
    }}

    const data = await res.json();
    const reply = data.output_text || data.reply || data.status || '…';
    const metaParts = [];
    if (data.provider) metaParts.push(data.provider);
    if (data.model)    metaParts.push(data.model);
    const replyMeta = metaParts.length ? metaParts.join(' · ') + ' · ' + new Date().toLocaleTimeString([], {{hour:'2-digit', minute:'2-digit'}}) : new Date().toLocaleTimeString([], {{hour:'2-digit', minute:'2-digit'}});
    appendMsg('jarvis', reply, replyMeta);

    if (data.refresh) loadViewData(currentView);
  }} catch(e) {{
    chatArea.removeChild(typingRow);
    appendMsg('jarvis', 'No connection to JARVIS — ' + e.message, null);
  }}
}}

async function handleApproval(id, action) {{
  try {{
    const res = await fetch('/api/approvals/' + id + '/' + action, {{ method: 'POST' }});
    if (!res.ok) {{ showToast('Action failed', 'error'); return; }}
    showToast(action === 'approve' ? 'Approved ✓' : 'Denied', action === 'approve' ? 'success' : 'error');
    loadApprovals();
  }} catch(e) {{
    showToast('No connection', 'error');
  }}
}}

/* ═══════════════════════════════════════════════════════════════
   RENDER FUNCTIONS
═══════════════════════════════════════════════════════════════ */
function renderApprovals(items) {{
  const el = document.getElementById('approvals-list');
  const countEl = document.getElementById('stat-approvals');

  if (!items || items.length === 0) {{
    el.innerHTML = '<div class="list-row"><span class="dot dot-standby"></span><div><div class="list-row-name">No pending approvals</div><div class="list-row-sub">All clear, Director</div></div></div>';
    if (countEl) countEl.textContent = '0';
    return;
  }}

  if (countEl) countEl.textContent = items.length;

  el.innerHTML = items.map(item => {{
    const id = item.id || item.request_id || '';
    // API returns `request` as the human-readable action; fall back to title/name
    const title = item.request || item.title || item.name || 'Untitled';
    const agent = item.owner_agent || item.agent || '—';
    const domain = item.domain || item.type || 'REQUEST';
    const risk = item.action_class ? item.action_class.replace(/_/g,' ') : '';
    const riskHtml = risk ? '<span style="color:var(--gold);font-size:9px;margin-left:6px;">' + escHtml(risk) + '</span>' : '';
    return `
    <div class="approval-item">
      <div class="approval-title">${{escHtml(title)}}</div>
      <div class="approval-meta">${{escHtml(domain.toUpperCase())}} &nbsp;·&nbsp; ${{escHtml(agent)}} ${{riskHtml}}</div>
      <div class="approval-actions">
        <button class="btn btn-hue btn-sm" onclick="handleApproval('${{id}}','approve')">Approve</button>
        <button class="btn btn-crimson btn-sm" onclick="handleApproval('${{id}}','deny')">Deny</button>
      </div>
    </div>
  `}}).join('');
}}

function renderStatus(data) {{
  const grid = document.getElementById('service-grid');
  if (!data || !data.services) return;

  grid.innerHTML = data.services.map(svc => {{
    const dotClass = svc.status === 'ok' ? 'dot-success' : svc.status === 'error' ? 'dot-error' : 'dot-standby';
    const pillClass = svc.status === 'ok' ? 'pill-success' : svc.status === 'error' ? 'pill-crimson' : 'pill-navy';
    const label = svc.status === 'ok' ? 'OK' : svc.status === 'error' ? 'ERROR' : 'UNKNOWN';
    return `
      <div class="card service-card">
        <div class="service-name"><span class="dot ${{dotClass}}"></span>${{escHtml(svc.name)}}</div>
        <div style="margin-top:4px;display:flex;align-items:center;gap:8px;">
          <span class="pill ${{pillClass}}">${{label}}</span>
        </div>
        <div class="service-detail" style="margin-top:6px;">${{escHtml(svc.detail || '')}}</div>
      </div>
    `;
  }}).join('');
}}

function renderBriefing(data) {{
  const textEl = document.getElementById('brief-text');
  const dateEl = document.getElementById('brief-date');
  if (!data) return;
  // Support both {{date: ...}} and auto-compute today
  const dateStr = data.date || new Date().toLocaleDateString([], {{weekday:'short', month:'short', day:'numeric'}});
  if (dateEl) dateEl.textContent = dateStr;
  // API returns `briefing` field (not `content`)
  const raw = data.briefing || data.content || data.text || '';
  const text = typeof raw === 'string' ? raw : (raw[0] || '');
  if (textEl && text) {{
    if (text.length > 420) {{
      textEl.dataset.full = text;
      textEl.dataset.short = text.slice(0, 420);
      textEl.dataset.expanded = '0';
      textEl.textContent = text.slice(0, 420) + '…';
      textEl.style.cursor = 'pointer';
      textEl.title = 'Click to read full briefing';
      textEl.onclick = () => toggleExpand(textEl);
    }} else {{
      textEl.textContent = text;
    }}
  }} else if (textEl && !text) {{
    textEl.innerHTML = '<span style="color:var(--text-3);font-style:italic;">No briefing available yet.</span>';
  }}
}}

function renderPublishing(data) {{
  if (!data) return;
  const booksEl = document.getElementById('publishing-books');
  if (data.books && data.books.length > 0) {{
    const STAGES = ['Outline','Draft','Edit','Review','Polish','Cover','Format','Proof','Publish'];
    booksEl.innerHTML = data.books.map(book => {{
      const current = (book.stage || 0);
      const segs = STAGES.map((s, i) => {{
        const cls = i < current ? 'done' : i === current ? 'current' : '';
        return `<div class="pipeline-seg ${{cls}}" title="${{s}}"></div>`;
      }}).join('');
      return `
        <div class="card">
          <div class="card-inner">
            <div class="card-header">
              <span class="card-title">${{escHtml(book.title)}}</span>
              <span class="pill pill-hue">${{STAGES[current] || '—'}}</span>
            </div>
            <div class="pipeline-bar">${{segs}}</div>
          </div>
        </div>
      `;
    }}).join('');
  }}
  if (data.pending_reviews && data.pending_reviews.length > 0) {{
    const revEl = document.getElementById('publishing-reviews');
    revEl.innerHTML = data.pending_reviews.map(r => `
      <div class="approval-item">
        <div class="approval-title">${{escHtml(r.title)}}</div>
        <div class="approval-meta">${{escHtml(r.type || 'REVIEW')}}</div>
        <div class="approval-actions">
          <button class="btn btn-hue btn-sm" onclick="handleApproval('${{r.id}}','approve')">Approve</button>
          <button class="btn btn-crimson btn-sm" onclick="handleApproval('${{r.id}}','deny')">Reject</button>
        </div>
      </div>
    `).join('');
  }}
}}

function renderChronicle(data) {{
  const list = document.getElementById('chronicle-list');
  const total = document.getElementById('chronicle-total');
  if (!data) return;

  if (total && data.total != null) total.textContent = data.total + ' entries';
  if (data.entries && data.entries.length > 0) {{
    list.innerHTML = data.entries.map(entry => {{
      const fullContent = entry.content || '';
      const shortContent = fullContent.slice(0, 120);
      const contentHtml = fullContent.length > 120
        ? `<div class="chronicle-text expand-toggle" data-full="${{escHtml(fullContent)}}" data-short="${{escHtml(shortContent)}}" data-expanded="0" title="Click to expand" onclick="toggleExpand(this)" style="cursor:pointer;">${{escHtml(shortContent)}}…</div>`
        : `<div class="chronicle-text">${{escHtml(shortContent)}}</div>`;
      return `
        <div class="chronicle-entry">
          <div class="chronicle-ts">${{escHtml(entry.ts || entry.created_at || '—')}}</div>
          ${{contentHtml}}
          <div class="chronicle-tags">${{(entry.tags || []).map(t => `<span class="pill pill-hue">${{escHtml(t)}}</span>`).join('')}}</div>
        </div>
      `;
    }}).join('');
  }} else {{
    list.innerHTML = '<div class="chronicle-entry"><div class="chronicle-ts">No entries found</div></div>';
  }}

  if (data.tags) {{
    const cloud = document.getElementById('tag-cloud');
    cloud.innerHTML = data.tags.map(t => `<span class="tag-chip" onclick="searchChronicle('${{escHtml(t)}}')">${{escHtml(t)}}</span>`).join('');
  }}
}}

/* ═══════════════════════════════════════════════════════════════
   AGENT GRID
═══════════════════════════════════════════════════════════════ */
function renderAgents(filter) {{
  currentFilter = filter || 'all';
  const grid = document.getElementById('agent-grid');

  // Update filter pill styles
  document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
  const activePill = document.querySelector('.filter-pill[onclick*="\\'' + filter + '\\'"]');
  if (activePill) activePill.classList.add('active');

  let filtered = AGENTS;
  if (filter === 'active') {{
    filtered = AGENTS.filter(a => a.status === 'active');
  }} else if (filter !== 'all') {{
    filtered = AGENTS.filter(a => a.domain === filter);
  }}

  const activeCount = AGENTS.filter(a => a.status === 'active').length;
  const activeEl = document.getElementById('active-count');
  if (activeEl) activeEl.textContent = '▲ ' + activeCount + ' ACTIVE';

  grid.innerHTML = filtered.map(agent => {{
    const domainCls = DOMAIN_CLASS[agent.domain] || 'domain-operations';
    const isActive  = agent.status === 'active';
    const dotCls    = isActive ? 'dot-active' : 'dot-standby';
    const statCls   = isActive ? 'active' : 'standby';
    const statLbl   = isActive ? 'ACTIVE' : 'STANDBY';
    return `
      <div class="agent-badge ${{domainCls}}" data-domain="${{agent.domain}}" data-status="${{agent.status}}">
        <span class="dot ${{dotCls}}"></span>
        <div class="agent-info">
          <div class="agent-name">${{escHtml(agent.name)}}</div>
          <div class="agent-title">${{escHtml(agent.title)}}</div>
          <div class="agent-domain">${{escHtml(agent.domain)}}</div>
        </div>
        <div class="agent-status">
          <span class="agent-status-label ${{statCls}}">${{statLbl}}</span>
        </div>
      </div>
    `;
  }}).join('');
}}

function filterAgents(domain) {{
  renderAgents(domain);
}}

function updateActiveCounts() {{
  const active = AGENTS.filter(a => a.status === 'active').length;
  const countEl = document.getElementById('active-count');
  if (countEl) countEl.textContent = '▲ ' + active + ' ACTIVE';
  const statEl = document.getElementById('stat-agents');
  if (statEl) statEl.textContent = active;
}}

/* ═══════════════════════════════════════════════════════════════
   CHRONICLE SEARCH
═══════════════════════════════════════════════════════════════ */
async function searchChronicle(query) {{
  const input = document.getElementById('chronicle-search');
  if (input && query && input.value !== query) input.value = query;
  try {{
    const q = encodeURIComponent(query || '');
    const res = await fetch('/api/chronicle/search?q=' + q);
    if (!res.ok) return;
    const data = await res.json();
    renderChronicle(data);
  }} catch(e) {{ /* silent */ }}
}}

/* ═══════════════════════════════════════════════════════════════
   COMMAND BAR
═══════════════════════════════════════════════════════════════ */
function setCmd(text) {{
  const input = document.getElementById('cmd-input');
  if (input) {{ input.value = text; input.focus(); }}
}}

function cmdKey(e) {{
  if (e.key === 'Enter' && !e.shiftKey) {{
    e.preventDefault();
    sendCmd();
  }}
}}

function sendCmd() {{
  const input = document.getElementById('cmd-input');
  if (!input) return;
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  sendCommand(text);
}}

function toggleMic() {{
  micActive = !micActive;
  const btn = document.getElementById('cmd-mic');
  if (!btn) return;
  if (micActive) {{
    btn.style.color = 'var(--crimson)';
    btn.style.borderColor = 'var(--crimson)';
    showToast('Microphone active', 'info');
  }} else {{
    btn.style.color = '';
    btn.style.borderColor = '';
  }}
  // Web Speech API hook (browser permitting)
  if (micActive && 'webkitSpeechRecognition' in window) {{
    const recog = new webkitSpeechRecognition();
    recog.continuous = false;
    recog.interimResults = false;
    recog.onresult = e => {{
      const t = e.results[0][0].transcript;
      setCmd(t);
      micActive = false;
      btn.style.color = '';
      btn.style.borderColor = '';
    }};
    recog.onerror = () => {{ micActive = false; btn.style.color=''; btn.style.borderColor=''; }};
    recog.start();
  }}
}}

/* ═══════════════════════════════════════════════════════════════
   WEBSOCKET
═══════════════════════════════════════════════════════════════ */
function connectWebSocket() {{
  try {{
    ws = new WebSocket(WS_URL);
    ws.onopen    = () => {{ wsRetries = 0; }};
    ws.onmessage = e => {{
      try {{ handlePacket(JSON.parse(e.data)); }} catch(_) {{}}
    }};
    ws.onclose = () => {{
      wsRetries++;
      const delay = Math.min(1000 * Math.pow(1.5, wsRetries), 30000);
      setTimeout(connectWebSocket, delay);
    }};
    ws.onerror = () => ws.close();
  }} catch(e) {{ /* no WS in dev */ }}
}}

function handlePacket(pkt) {{
  if (!pkt || !pkt.type) return;
  switch (pkt.type) {{
    case 'approvals_update':  renderApprovals(pkt.data);   break;
    case 'status_update':     renderStatus(pkt.data);      break;
    case 'briefing_update':   renderBriefing(pkt.data);    break;
    case 'toast':             showToast(pkt.message, pkt.level || 'info'); break;
    case 'agent_status': {{
      const agent = AGENTS.find(a => a.id === pkt.agent_id);
      if (agent) {{ agent.status = pkt.status; renderAgents(currentFilter); updateActiveCounts(); }}
      break;
    }}
  }}
}}

/* ═══════════════════════════════════════════════════════════════
   TOAST NOTIFICATIONS
═══════════════════════════════════════════════════════════════ */
function showToast(msg, type) {{
  const wrap = document.getElementById('toast-wrap');
  if (!wrap) return;
  const div = document.createElement('div');
  div.className = 'toast toast-' + (type || 'info');
  div.textContent = msg;
  wrap.appendChild(div);
  setTimeout(() => {{
    div.style.opacity = '0';
    div.style.transition = 'opacity 0.3s';
    setTimeout(() => div.remove(), 350);
  }}, 3500);
}}

/* ═══════════════════════════════════════════════════════════════
   SETTINGS MODAL
═══════════════════════════════════════════════════════════════ */
function openSettings() {{
  const ov = document.getElementById('settings-overlay');
  if (ov) ov.classList.remove('hidden');
}}

function closeSettings() {{
  const ov = document.getElementById('settings-overlay');
  if (ov) ov.classList.add('hidden');
}}

function closeSettingsIfOuter(e) {{
  if (e.target === document.getElementById('settings-overlay')) closeSettings();
}}

function setTheme(theme) {{
  document.cookie = 'jarvis-theme=' + theme + '; path=/; max-age=31536000';
  switch (theme) {{
    case 'classic': window.location.href = '/'; break;
    case 'nexus':   window.location.href = '/?theme=nexus'; break;
    case 'glass':   window.location.href = '/glass'; break;
    default:        window.location.reload();
  }}
}}

/* ═══════════════════════════════════════════════════════════════
   UTILITIES
═══════════════════════════════════════════════════════════════ */
function escHtml(str) {{
  if (str == null) return '';
  return String(str)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;')
    .replace(/'/g,'&#39;');
}}

/* ── Boot ── */
document.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>"""
