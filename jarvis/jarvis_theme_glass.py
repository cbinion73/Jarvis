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

/* ── Weather widget ── */
.nav-weather {{
  display: flex; align-items: center; gap: 5px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 99px; padding: 3px 10px;
  cursor: pointer; transition: background 0.2s;
  font-family: var(--font-mono); font-size: 11px; color: var(--text-1);
  white-space: nowrap;
}}
.nav-weather:hover {{ background: var(--surface-hi); }}
.nav-weather-icon {{ font-size: 14px; line-height: 1; }}
.nav-clock {{ font-family: var(--font-mono); font-size: 11px; color: var(--text-2); white-space: nowrap; }}

/* ── Weather modal ── */
.weather-modal-overlay {{
  position: fixed; inset: 0; z-index: 3000;
  background: rgba(15,23,42,0.55); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
}}
.weather-modal-overlay.hidden {{ display: none; }}
.weather-modal {{
  background: var(--surface-hi); border: 1px solid var(--border-hi);
  border-radius: 20px; padding: 28px;
  width: min(680px, 95vw); max-height: 90vh; overflow-y: auto;
  box-shadow: 0 24px 64px rgba(0,0,0,0.2);
}}
.weather-modal-header {{
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 20px;
}}
.weather-modal-title {{ font-size: 18px; font-weight: 700; color: var(--text-1); }}
.weather-modal-close {{
  width: 32px; height: 32px; border-radius: 8px; border: 1px solid var(--border);
  background: transparent; cursor: pointer; color: var(--text-2);
  font-size: 16px; display: flex; align-items: center; justify-content: center;
}}
.weather-hero {{
  display: flex; align-items: center; gap: 20px; margin-bottom: 24px;
  padding: 20px; background: rgba(255,255,255,0.4); border-radius: 14px;
}}
.weather-hero-icon {{ font-size: 56px; line-height: 1; }}
.weather-hero-temp {{ font-size: 48px; font-weight: 700; font-family: var(--font-mono); color: var(--text-1); }}
.weather-hero-detail {{ color: var(--text-2); font-size: 13px; line-height: 1.6; }}
.weather-grid {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(140px,1fr));
  gap: 10px; margin-bottom: 20px;
}}
.weather-stat {{
  background: rgba(255,255,255,0.4); border-radius: 10px; padding: 12px;
  text-align: center;
}}
.weather-stat-val {{ font-size: 18px; font-weight: 700; font-family: var(--font-mono); color: var(--text-1); }}
.weather-stat-lbl {{ font-size: 10px; color: var(--text-3); text-transform: uppercase; margin-top: 2px; }}
.weather-radar-frame {{
  border-radius: 12px; overflow: hidden; border: 1px solid var(--border);
  margin-bottom: 20px; background: #000;
}}
.weather-radar-frame img {{ width: 100%; display: block; }}
.weather-forecast-row {{
  display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px;
}}
.weather-forecast-item {{
  flex-shrink: 0; background: rgba(255,255,255,0.4); border-radius: 10px;
  padding: 10px 14px; text-align: center; min-width: 70px;
}}
.weather-forecast-label {{ font-size: 10px; color: var(--text-3); margin-bottom: 4px; }}
.weather-forecast-icon {{ font-size: 18px; }}
.weather-forecast-hi {{ font-size: 13px; font-weight: 700; color: var(--text-1); }}
.weather-forecast-lo {{ font-size: 11px; color: var(--text-3); }}

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

/* ── Task domain chips ── */
.task-domain-chip {{
  display: inline-block; padding: 1px 7px; border-radius: 20px;
  font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
  line-height: 18px;
}}
.tdc-personal  {{ background: rgba(59,130,246,0.12);  color: #3B82F6; border: 1px solid rgba(59,130,246,0.25); }}
.tdc-work      {{ background: rgba(139,92,246,0.12);  color: #8B5CF6; border: 1px solid rgba(139,92,246,0.25); }}
.tdc-family    {{ background: rgba(34,197,94,0.12);   color: #16A34A; border: 1px solid rgba(34,197,94,0.25); }}
.tdc-home      {{ background: rgba(249,115,22,0.12);  color: #EA580C; border: 1px solid rgba(249,115,22,0.25); }}
.tdc-faith     {{ background: rgba(201,168,76,0.12);  color: #B45309; border: 1px solid rgba(201,168,76,0.3); }}
.tdc-health    {{ background: rgba(239,68,68,0.1);    color: #DC2626; border: 1px solid rgba(239,68,68,0.25); }}
.tdc-finance   {{ background: rgba(20,184,166,0.12);  color: #0F766E; border: 1px solid rgba(20,184,166,0.25); }}
.tdc-workshop  {{ background: rgba(148,163,184,0.15); color: #64748B; border: 1px solid rgba(148,163,184,0.3); }}
/* ── Task priority dot override ── */
.task-pri-high   {{ color: #DC2626; }}
.task-pri-normal {{ color: #94A3B8; }}
.task-pri-low    {{ color: #CBD5E1; }}
/* ── Tasks panel misc ── */
.tasks-filter-bar {{ display:flex; gap:4px; margin-bottom:8px; flex-wrap:wrap; }}
.tasks-filter-pill {{
  padding: 3px 10px; border-radius: 20px; font-size: 10px; font-weight: 500; cursor: pointer;
  background: rgba(255,255,255,0.3); border: 1px solid rgba(255,255,255,0.45);
  color: var(--text-2); transition: background 0.2s, color 0.2s;
}}
.tasks-filter-pill.active {{
  background: var(--hue-dim); color: var(--hue); border-color: rgba(var(--hue-rgb),0.3);
}}
.tasks-add-bar {{ display:flex; gap:6px; margin-bottom:10px; flex-wrap:wrap; }}
.tasks-add-bar input, .tasks-add-bar select {{
  background: rgba(255,255,255,0.4); border: 1px solid rgba(255,255,255,0.5);
  border-radius: 6px; padding: 5px 8px; font-size: 11px; color: var(--text-1); outline: none;
}}
.tasks-add-bar input[type="text"] {{ flex: 1; min-width: 120px; }}
.tasks-add-bar input[type="date"] {{ width: 128px; }}
.tasks-add-bar select {{ min-width: 90px; }}
.tasks-group-label {{
  font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em;
  color: var(--text-3); margin: 8px 0 4px; padding-bottom: 2px;
  border-bottom: 1px solid var(--border);
}}

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

/* Idea Inbox */
.idea-filter-pill {{
  padding: 4px 12px; border-radius: 20px; border: 1px solid var(--border);
  background: var(--surface-hi); font-size: 10px; font-weight: 600;
  color: var(--text-3); cursor: pointer; letter-spacing: 0.04em;
  transition: all 0.15s;
}}
.idea-filter-pill:hover {{ border-color: var(--hue); color: var(--hue); }}
.idea-filter-pill.active {{ background: var(--hue); color: #fff; border-color: var(--hue); }}
.idea-row {{
  display: flex; align-items: flex-start; gap: 10px;
  padding: 10px 14px; border-radius: 10px;
  border: 1px solid var(--border); background: var(--surface-hi);
  transition: border-color 0.15s;
}}
.idea-row:hover {{ border-color: rgba(var(--hue-rgb,245,158,11),0.4); }}
.idea-row-text {{ flex: 1; font-size: 13px; color: var(--text-1); line-height: 1.45; }}
.idea-row-notes {{ font-size: 10px; color: var(--text-3); margin-top: 3px; font-style: italic; }}
.idea-status-chip {{
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px; border-radius: 10px; font-size: 9px; font-weight: 700;
  letter-spacing: 0.05em; white-space: nowrap; flex-shrink: 0;
}}
.idea-chip-captured {{ background: rgba(100,116,139,0.15); color: #94a3b8; }}
.idea-chip-queued {{ background: rgba(245,158,11,0.15); color: #f59e0b; }}
.idea-chip-researching {{ background: rgba(99,102,241,0.2); color: #818cf8; }}
.idea-chip-done {{ background: rgba(16,185,129,0.15); color: #10b981; }}
.idea-chip-passed {{ background: rgba(100,116,139,0.1); color: #64748b; }}
.idea-row-actions {{ display: flex; gap: 5px; flex-shrink: 0; }}
.idea-act-btn {{
  padding: 3px 9px; border-radius: 6px; border: 1px solid var(--border);
  background: transparent; font-size: 10px; font-weight: 600;
  color: var(--text-2); cursor: pointer; transition: all 0.12s;
}}
.idea-act-btn:hover {{ border-color: var(--hue); color: var(--hue); }}
.idea-act-btn.primary {{ background: var(--hue); color: #fff; border-color: var(--hue); }}
.idea-act-btn.primary:hover {{ opacity: 0.85; }}
.idea-act-btn.danger {{ color: #ef4444; border-color: rgba(239,68,68,0.3); }}
.idea-act-btn.danger:hover {{ background: rgba(239,68,68,0.1); border-color: #ef4444; }}
.idea-dossier-link {{
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 10px; color: var(--hue); font-weight: 600; cursor: pointer;
  margin-top: 4px; text-decoration: none;
}}
.idea-dossier-link:hover {{ text-decoration: underline; }}

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

/* ═══════════════════════════════════════════════════════════════════
   FORGE — OBJECT-TO-MANUFACTURING WORKSPACE
═══════════════════════════════════════════════════════════════════ */
.forge-workspace {{ display:flex; flex-direction:column; gap:16px; height:100%; }}
.forge-header {{ display:flex; align-items:center; gap:12px; flex-wrap:wrap; }}
.forge-header select {{ flex:1; min-width:200px; padding:8px 12px; border:1px solid var(--border); border-radius:8px; background:var(--surface-hi); font-size:13px; color:var(--text-1); cursor:pointer; }}
.forge-main {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; flex:1; min-height:0; }}
@media(max-width:900px){{ .forge-main{{ grid-template-columns:1fr; }} }}
.forge-left,.forge-right {{ display:flex; flex-direction:column; gap:12px; }}
.forge-viewer-container {{ position:relative; background:#111827; border-radius:12px; overflow:hidden; min-height:320px; flex:1; border:1px solid rgba(255,255,255,0.08); }}
#forge-3d-canvas {{ width:100%; height:100%; display:block; }}
.forge-viewer-overlay {{ position:absolute; top:8px; right:10px; font-family:var(--font-mono); font-size:10px; color:rgba(255,255,255,0.55); line-height:1.7; text-align:right; pointer-events:none; }}
.forge-viewer-controls {{ position:absolute; bottom:10px; left:10px; display:flex; gap:6px; flex-wrap:wrap; }}
.forge-viewer-btn {{ padding:4px 10px; border-radius:6px; border:1px solid rgba(255,255,255,0.2); background:rgba(0,0,0,0.45); color:rgba(255,255,255,0.8); font-size:11px; cursor:pointer; transition:background 0.15s; }}
.forge-viewer-btn:hover {{ background:rgba(255,255,255,0.1); }}
.forge-upload-zone {{ position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; border:2px dashed rgba(255,255,255,0.15); border-radius:12px; cursor:pointer; color:rgba(255,255,255,0.4); font-size:13px; gap:10px; text-align:center; padding:24px; transition:border-color 0.2s,background 0.2s; }}
.forge-upload-zone:hover,.forge-upload-zone.drag-over {{ border-color:var(--hue); background:rgba(245,158,11,0.06); color:rgba(255,255,255,0.7); }}
.forge-upload-zone svg {{ opacity:0.4; }}
.forge-upload-btns {{ display:flex; gap:8px; margin-top:6px; flex-wrap:wrap; justify-content:center; }}
.forge-capture-panel,.forge-measurements-panel {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px 16px; }}
.forge-panel-title {{ font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:var(--text-2); margin-bottom:10px; display:flex; align-items:center; justify-content:space-between; }}
.forge-capture-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:6px; margin-top:6px; }}
.forge-view-chip {{ display:flex; flex-direction:column; align-items:center; gap:3px; padding:6px 4px; border-radius:7px; border:1px solid var(--border); background:var(--surface-hi); font-size:9px; font-family:var(--font-mono); text-transform:uppercase; letter-spacing:0.05em; color:var(--text-3); transition:border-color 0.15s; }}
.forge-view-chip.view-captured {{ border-color:var(--success); color:var(--success); background:rgba(16,185,129,0.07); }}
.forge-view-chip.view-missing {{ border-color:var(--crimson); color:var(--crimson); background:rgba(196,30,58,0.06); }}
.forge-view-chip.view-optional {{ border-color:var(--border); color:var(--text-3); }}
.forge-confidence-row {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:8px; font-size:10px; font-family:var(--font-mono); }}
.forge-conf-chip {{ padding:3px 9px; border-radius:99px; font-size:9px; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; }}
.confidence-low {{ background:rgba(245,158,11,0.12); color:#F59E0B; border:1px solid rgba(245,158,11,0.3); }}
.confidence-medium {{ background:rgba(234,179,8,0.12); color:#CA8A04; border:1px solid rgba(234,179,8,0.3); }}
.confidence-high {{ background:rgba(16,185,129,0.12); color:var(--success); border:1px solid rgba(16,185,129,0.3); }}
.confidence-not_ready {{ background:rgba(148,163,184,0.12); color:var(--text-3); border:1px solid var(--border); }}
.forge-meas-list {{ display:flex; flex-direction:column; gap:5px; margin-top:6px; max-height:140px; overflow-y:auto; }}
.forge-meas-row {{ display:flex; align-items:center; gap:8px; font-size:12px; }}
.forge-meas-label {{ flex:1; color:var(--text-2); font-weight:500; }}
.forge-meas-value {{ font-family:var(--font-mono); font-size:11px; color:var(--text-1); font-weight:600; }}
.forge-meas-confirmed {{ font-size:9px; padding:2px 6px; border-radius:99px; font-family:var(--font-mono); font-weight:700; }}
.meas-confirmed {{ background:rgba(16,185,129,0.12); color:var(--success); border:1px solid rgba(16,185,129,0.25); }}
.meas-assumed {{ background:rgba(245,158,11,0.1); color:#F59E0B; border:1px solid rgba(245,158,11,0.2); }}
.forge-chat-panel {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px 16px; display:flex; flex-direction:column; flex:1; min-height:280px; }}
#forge-chat-messages {{ flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:8px; margin-bottom:10px; max-height:220px; padding-right:4px; }}
.forge-msg-user {{ align-self:flex-end; background:var(--hue); color:#fff; padding:8px 12px; border-radius:10px 10px 2px 10px; font-size:13px; max-width:85%; }}
.forge-msg-jarvis {{ align-self:flex-start; background:var(--surface-hi); color:var(--text-1); padding:8px 12px; border-radius:10px 10px 10px 2px; font-size:13px; max-width:90%; border:1px solid var(--border); }}
.forge-chat-input {{ display:flex; gap:8px; }}
.forge-chat-input input {{ flex:1; padding:8px 12px; border:1px solid var(--border); border-radius:8px; background:var(--surface-hi); font-size:13px; color:var(--text-1); outline:none; }}
.forge-chat-input input:focus {{ border-color:var(--hue); }}
.forge-readiness-panel {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px 16px; }}
.forge-readiness-list {{ display:flex; flex-direction:column; gap:6px; margin:8px 0; }}
.readiness-row {{ display:flex; align-items:center; gap:8px; font-size:12px; }}
.readiness-ok {{ color:var(--success); font-weight:600; }}
.readiness-warn {{ color:#F59E0B; font-weight:600; }}
.readiness-fail {{ color:var(--crimson); font-weight:600; }}
.forge-action-bar {{ display:flex; gap:8px; flex-wrap:wrap; padding-top:4px; }}
.forge-action-btn {{ padding:9px 18px; border-radius:8px; border:1px solid var(--border); background:var(--surface-hi); font-size:12px; font-weight:600; color:var(--text-1); cursor:pointer; transition:all 0.15s; letter-spacing:0.02em; }}
.forge-action-btn:hover {{ border-color:var(--hue); color:var(--hue); }}
.forge-action-btn.primary {{ background:var(--hue); color:#fff; border-color:var(--hue); }}
.forge-action-btn.primary:hover {{ opacity:0.88; }}
.forge-printer-chip {{ padding:5px 12px; border-radius:99px; font-size:10px; font-family:var(--font-mono); font-weight:700; text-transform:uppercase; letter-spacing:0.06em; border:1px solid var(--border); color:var(--text-3); margin-left:auto; }}
.forge-printer-chip.online {{ border-color:var(--success); color:var(--success); background:rgba(16,185,129,0.08); }}
.forge-modal-overlay {{ position:fixed; inset:0; background:rgba(0,0,0,0.4); z-index:900; display:flex; align-items:center; justify-content:center; }}
.forge-modal-overlay.hidden {{ display:none !important; }}
.forge-modal {{ background:var(--surface-hi); border:1px solid var(--border); border-radius:16px; padding:24px; min-width:340px; max-width:540px; width:90%; box-shadow:0 20px 60px rgba(0,0,0,0.2); }}
.forge-modal-title {{ font-size:15px; font-weight:700; margin-bottom:16px; color:var(--text-1); }}
.forge-timeline-list {{ display:flex; flex-direction:column; gap:6px; max-height:400px; overflow-y:auto; }}
.forge-tl-row {{ display:flex; gap:10px; font-size:11px; padding:6px 0; border-bottom:1px solid var(--border); }}
.forge-tl-ts {{ font-family:var(--font-mono); color:var(--text-3); white-space:nowrap; min-width:140px; }}
.forge-tl-event {{ color:var(--hue); font-weight:600; min-width:120px; }}
.forge-tl-detail {{ color:var(--text-2); flex:1; }}
.forge-camera-preview {{ width:100%; border-radius:10px; margin-bottom:12px; max-height:220px; object-fit:cover; }}

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
    <span class="nav-clock" id="nav-clock"></span>
    <button class="nav-weather" id="nav-weather-btn" onclick="openWeatherModal()" title="Live weather">
      <span class="nav-weather-icon" id="nav-weather-icon">⛅</span>
      <span id="nav-weather-temp">--°</span>
      <span id="nav-weather-cond" style="color:var(--text-2);">--</span>
    </button>
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

      <!-- Reminders -->
      <div class="card card-tactical">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">Reminders</span>
            <span class="pill pill-hue" id="reminders-count">—</span>
          </div>
          <div id="overview-reminders">
            <div class="list-row"><div class="skel" style="height:10px;width:70%;"></div></div>
            <div class="list-row"><div class="skel" style="height:10px;width:55%;"></div></div>
          </div>
          <div style="margin-top:10px;display:flex;gap:6px;">
            <input id="reminder-input" type="text" placeholder="Add reminder…" style="flex:1;background:rgba(255,255,255,0.4);border:1px solid rgba(255,255,255,0.5);border-radius:6px;padding:5px 8px;font-size:12px;color:var(--text-1);outline:none;" onkeydown="if(event.key==='Enter')addReminder()">
            <button onclick="addReminder()" style="background:var(--hue);color:#fff;border:none;border-radius:6px;padding:5px 10px;font-size:12px;cursor:pointer;">+</button>
          </div>
        </div>
      </div>

      <!-- Tasks -->
      <div class="card card-tactical" style="grid-column: 1 / -1;">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">Tasks</span>
            <span class="pill pill-hue" id="tasks-count">—</span>
          </div>
          <!-- Add-task bar -->
          <div class="tasks-add-bar">
            <input id="task-title-input" type="text" placeholder="New task…" onkeydown="if(event.key==='Enter')addJarvisTask()">
            <select id="task-domain-select">
              <option value="personal">Personal</option>
              <option value="work">Work</option>
              <option value="family">Family</option>
              <option value="home">Home</option>
              <option value="health">Health</option>
              <option value="faith">Faith</option>
              <option value="finance">Finance</option>
              <option value="workshop">Workshop</option>
            </select>
            <select id="task-priority-select">
              <option value="normal">Normal</option>
              <option value="high">High</option>
              <option value="low">Low</option>
            </select>
            <input id="task-due-input" type="date">
            <button onclick="addJarvisTask()" style="background:var(--hue);color:#fff;border:none;border-radius:6px;padding:5px 12px;font-size:12px;cursor:pointer;white-space:nowrap;">+ Add</button>
          </div>
          <!-- Filter pills -->
          <div class="tasks-filter-bar" id="tasks-filter-bar">
            <span class="tasks-filter-pill active" data-filter="all"    onclick="setTaskFilter('all')">All</span>
            <span class="tasks-filter-pill"         data-filter="today"  onclick="setTaskFilter('today')">Today</span>
            <span class="tasks-filter-pill"         data-filter="week"   onclick="setTaskFilter('week')">This Week</span>
            <span class="tasks-filter-pill"         data-filter="domain" onclick="setTaskFilter('domain')">By Domain</span>
          </div>
          <!-- Task list -->
          <div id="overview-tasks">
            <div class="list-row"><div class="skel" style="height:10px;width:75%;margin-bottom:5px;"></div></div>
            <div class="list-row"><div class="skel" style="height:10px;width:60%;"></div></div>
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

      <!-- Idea Inbox quick-capture -->
      <div class="card" style="grid-column:1/-1;">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-icon">💡</span>
            <span class="card-title">IDEA INBOX</span>
            <span class="card-badge" id="idea-inbox-badge">—</span>
            <button class="btn-ghost" style="margin-left:auto;font-size:10px;" onclick="switchView('huddle')">View All →</button>
          </div>
          <div style="display:flex;gap:8px;margin-top:8px;">
            <input type="text" id="idea-inbox-input"
              placeholder="Dump an idea — JARVIS will research it and bring back a full dossier..."
              style="flex:1;padding:9px 13px;border:1px solid var(--border);border-radius:8px;background:var(--surface-hi);font-size:13px;color:var(--text-1);outline:none;"
              onkeydown="if(event.key==='Enter')overviewAddIdea()"
              onfocus="this.style.borderColor='var(--hue)'"
              onblur="this.style.borderColor='var(--border)'">
            <button class="btn-primary" onclick="overviewAddIdea()" style="white-space:nowrap;">+ Add Idea</button>
          </div>
          <div id="idea-inbox-recent" style="margin-top:10px;display:flex;flex-wrap:wrap;gap:6px;min-height:20px;"></div>
        </div>
      </div>

    </div>
  </div>

  <!-- ── FORGE ──────────────────────────────────────────────── -->
  <!-- ── FORGE ─────────────────────────────────────────────────── -->
  <!-- Three.js CDN (loaded lazily when Forge view is first activated) -->
  <script id="forge-three-placeholder" data-loaded="false"></script>

  <div id="view-forge" class="view">
    <div class="view-header">
      <div class="view-title">FORGE WORKSPACE<div class="view-title-line"></div></div>
      <div class="view-subtitle">Object Capture · 3D Modeling · Print Gate · Manufacturing</div>
    </div>

    <div class="forge-workspace">

      <!-- Header: project selector + new button -->
      <div class="forge-header">
        <select id="forge-project-select" onchange="forgeLoadProject(this.value)">
          <option value="">— Select a project —</option>
        </select>
        <button class="forge-action-btn" onclick="forgeNewProject()">+ New Project</button>
        <span class="pill pill-hue" id="forge-project-status" style="display:none;">IDEA</span>
      </div>

      <!-- Two-column main -->
      <div class="forge-main">

        <!-- LEFT: viewer + capture + measurements -->
        <div class="forge-left">

          <!-- 3D Viewer -->
          <div class="forge-viewer-container" id="forge-viewer-container">
            <canvas id="forge-3d-canvas"></canvas>
            <div class="forge-viewer-overlay" id="forge-bbox-overlay" style="display:none;">
              <div id="forge-bbox-text" style="font-size:10px;"></div>
            </div>
            <div class="forge-viewer-controls" id="forge-viewer-controls" style="display:none;">
              <button class="forge-viewer-btn" onclick="forgeCameraReset()">Reset</button>
              <button class="forge-viewer-btn" onclick="forgeCameraTop()">Top</button>
              <button class="forge-viewer-btn" onclick="forgeCameraFront()">Front</button>
              <button class="forge-viewer-btn" onclick="forgeCameraLayFlat()">Lay Flat</button>
              <button class="forge-viewer-btn" onclick="forgeScreenshot()">Screenshot</button>
              <button class="forge-viewer-btn" onclick="forgeDownloadSTL()" id="forge-dl-stl-btn" style="display:none;">Download STL</button>
            </div>
            <!-- Upload zone (shown when no model loaded) -->
            <div class="forge-upload-zone" id="forge-upload-zone"
                 onclick="document.getElementById('forge-file-input').click()"
                 ondragover="event.preventDefault();this.classList.add('drag-over')"
                 ondragleave="this.classList.remove('drag-over')"
                 ondrop="forgeHandleDrop(event)">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              <div style="font-size:13px;font-weight:500;">Drop STL / OBJ / GLB / 3MF here<br>or click to upload</div>
              <div class="forge-upload-btns">
                <button class="forge-action-btn" style="font-size:11px;padding:5px 12px;"
                  onclick="event.stopPropagation();document.getElementById('forge-photo-input').click()">Upload Photos</button>
                <button class="forge-action-btn" style="font-size:11px;padding:5px 12px;"
                  onclick="event.stopPropagation();forgeCameraCapture()">Camera</button>
              </div>
            </div>
            <input type="file" id="forge-file-input" style="display:none" accept=".stl,.obj,.glb,.3mf"
                   onchange="forgeUploadFile(this.files[0])">
            <input type="file" id="forge-photo-input" style="display:none" accept="image/*" multiple
                   onchange="forgeUploadPhotos(this.files)">
          </div>

          <!-- Capture panel -->
          <div class="forge-capture-panel" id="forge-capture-panel">
            <div class="forge-panel-title">
              Capture Status
              <button class="forge-action-btn" style="font-size:10px;padding:3px 8px;"
                onclick="forgeCameraCapture()">+ Frame</button>
            </div>
            <div class="forge-capture-grid" id="forge-capture-grid">
              <!-- filled by forgeRenderCapture() -->
              <div class="forge-view-chip view-missing">Front</div>
              <div class="forge-view-chip view-missing">Back</div>
              <div class="forge-view-chip view-missing">Left</div>
              <div class="forge-view-chip view-missing">Right</div>
              <div class="forge-view-chip view-missing">Top</div>
              <div class="forge-view-chip view-optional">Bottom</div>
              <div class="forge-view-chip view-optional">Scale</div>
              <div class="forge-view-chip view-optional">Detail</div>
            </div>
            <div class="forge-confidence-row" id="forge-confidence-row">
              <span class="forge-conf-chip confidence-not_ready">Geometry: —</span>
              <span class="forge-conf-chip confidence-not_ready">Scale: —</span>
              <span class="forge-conf-chip confidence-not_ready">Print: —</span>
            </div>
          </div>

          <!-- Measurements panel -->
          <div class="forge-measurements-panel">
            <div class="forge-panel-title">
              Measurements
              <button class="forge-action-btn" style="font-size:10px;padding:3px 8px;"
                onclick="forgeAddMeasurement()">+ Add</button>
            </div>
            <div class="forge-meas-list" id="forge-meas-list">
              <div style="color:var(--text-3);font-size:11px;font-family:var(--font-mono);">No measurements yet.</div>
            </div>
          </div>

        </div><!-- .forge-left -->

        <!-- RIGHT: chat + readiness -->
        <div class="forge-right">

          <!-- Chat panel -->
          <div class="forge-chat-panel">
            <div class="forge-panel-title" style="margin-bottom:6px;">
              JARVIS Forge · Chat
              <button class="forge-action-btn" style="font-size:10px;padding:3px 8px;margin-left:auto;"
                onclick="forgeQuickDescribe()">Describe Part</button>
            </div>
            <div id="forge-chat-messages">
              <div class="forge-msg-jarvis">Select a project to begin. Describe a part to generate it, upload a sketch to analyze it, or use Design Council for a full agent roundtable.</div>
            </div>
            <div class="forge-chat-input">
              <input type="text" id="forge-chat-input" placeholder="Describe a part or ask Forge anything..."
                     onkeydown="if(event.key==='Enter')forgeSendChat()">
              <button class="forge-action-btn primary" onclick="forgeSendChat()">Send</button>
            </div>
            <!-- Sketch upload row -->
            <div style="display:flex;align-items:center;gap:8px;margin-top:8px;">
              <span style="font-size:10px;color:var(--text-3);font-weight:600;letter-spacing:0.05em;">SKETCH</span>
              <input type="file" id="forge-sketch-input" accept="image/*"
                     style="display:none;" onchange="forgeHandleSketchUpload(this)">
              <button class="forge-action-btn" style="font-size:10px;padding:3px 10px;"
                onclick="document.getElementById('forge-sketch-input').click()">Upload Drawing</button>
              <span id="forge-sketch-status" style="font-size:10px;color:var(--text-3);font-family:var(--font-mono);"></span>
            </div>
          </div>

          <!-- Print readiness panel -->
          <div class="forge-readiness-panel">
            <div class="forge-panel-title">
              Print Readiness
              <button class="forge-action-btn" style="font-size:10px;padding:3px 8px;"
                onclick="forgeInspectActive()">Inspect</button>
            </div>
            <div class="forge-readiness-list" id="forge-readiness-list">
              <div style="color:var(--text-3);font-size:11px;font-family:var(--font-mono);">No inspection yet. Upload a model and click Inspect.</div>
            </div>
            <div id="forge-readiness-verdict" style="margin-top:8px;font-size:12px;font-weight:600;color:var(--text-3);font-family:var(--font-mono);">VERDICT: —</div>
          </div>

          <!-- Printer status chip -->
          <div id="forge-printer-status-row" style="display:none;margin-top:2px;">
            <span class="forge-printer-chip" id="forge-printer-chip">K2 Pro — checking...</span>
          </div>

        </div><!-- .forge-right -->

      </div><!-- .forge-main -->

      <!-- Action bar -->
      <div class="forge-action-bar">
        <button class="forge-action-btn" style="background:linear-gradient(135deg,#7c3aed22,#06b6d422);border-color:#7c3aed66;color:var(--hue);"
          onclick="forgeRunDesignCouncil()">⚡ Design Council</button>
        <button class="forge-action-btn" onclick="forgeStageSlice()">Stage Slice</button>
        <button class="forge-action-btn primary" onclick="forgeApprove()">Approve &amp; Send</button>
        <button class="forge-action-btn" onclick="forgeShowTimeline()">View Timeline</button>
        <button class="forge-action-btn" onclick="forgeArchive()">Archive</button>
        <span class="forge-printer-chip" id="forge-printer-chip-bar" style="display:none;margin-left:auto;">K2 Pro —</span>
      </div>

      <!-- Design Council modal -->
      <div id="forge-council-modal" class="forge-modal-overlay hidden">
        <div class="forge-modal" style="max-width:680px;">
          <div class="forge-modal-title">⚡ Forge Design Council</div>
          <div style="font-size:11px;color:var(--text-3);margin-bottom:12px;">
            Tony · Forge · AntMan · Rocket — four agents review your brief, debate the design, then generate a model.
          </div>
          <div id="forge-council-status" style="display:none;font-size:12px;color:var(--hue);margin-bottom:10px;font-family:var(--font-mono);">
            Council in session...
          </div>
          <div id="forge-council-roundtable" style="display:none;margin-bottom:14px;"></div>
          <div id="forge-council-spec" style="display:none;margin-bottom:14px;background:var(--surface-hi);border:1px solid var(--border);border-radius:8px;padding:12px;font-size:11px;font-family:var(--font-mono);color:var(--text-2);white-space:pre-wrap;max-height:160px;overflow-y:auto;"></div>
          <div id="forge-council-result" style="display:none;margin-bottom:14px;font-size:12px;color:var(--text-2);"></div>
          <textarea id="forge-council-brief" placeholder="Describe what you want to build in plain English. Include purpose, rough dimensions, materials, and any special requirements."
            style="width:100%;height:80px;padding:10px;border:1px solid var(--border);border-radius:8px;background:var(--surface-hi);font-size:12px;color:var(--text-1);font-family:var(--font-mono);resize:vertical;outline:none;box-sizing:border-box;"></textarea>
          <div style="display:flex;gap:8px;margin-top:10px;">
            <button class="forge-action-btn primary" onclick="forgeSubmitDesignCouncil()" id="forge-council-submit-btn">Convene Council</button>
            <button class="forge-action-btn" onclick="document.getElementById('forge-council-modal').classList.add('hidden');_forgeCouncilRunning=false;">Close</button>
          </div>
        </div>
      </div>

    </div><!-- .forge-workspace -->
  </div><!-- #view-forge -->

  <!-- Camera capture modal -->
  <div id="forge-camera-modal" class="forge-modal-overlay hidden">
    <div class="forge-modal">
      <div class="forge-modal-title">Capture Frame</div>
      <video id="forge-camera-video" class="forge-camera-preview" autoplay muted playsinline></video>
      <div style="margin-bottom:12px;">
        <label style="font-size:12px;color:var(--text-2);font-weight:500;">View type:</label>
        <select id="forge-camera-view-type" style="margin-left:8px;padding:5px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-hi);font-size:12px;">
          <option value="front">Front</option>
          <option value="back">Back</option>
          <option value="left">Left</option>
          <option value="right">Right</option>
          <option value="top">Top</option>
          <option value="bottom">Bottom</option>
          <option value="scale_reference">Scale Reference</option>
          <option value="detail">Detail</option>
        </select>
      </div>
      <div style="display:flex;gap:8px;">
        <button class="forge-action-btn primary" onclick="forgeCaptureSnapshot()">Capture</button>
        <button class="forge-action-btn" onclick="forgeCloseCameraModal()">Cancel</button>
      </div>
    </div>
  </div>

  <!-- Timeline modal -->
  <div id="forge-timeline-modal" class="forge-modal-overlay hidden">
    <div class="forge-modal" style="max-width:660px;">
      <div class="forge-modal-title">Project Timeline</div>
      <div class="forge-timeline-list" id="forge-timeline-list"></div>
      <div style="margin-top:16px;text-align:right;">
        <button class="forge-action-btn" onclick="document.getElementById('forge-timeline-modal').classList.add('hidden')">Close</button>
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

    <!-- ── Idea Inbox ──────────────────────────────────────────── -->
    <div class="huddle-section" id="idea-inbox-section">
      <div class="huddle-section-label" style="display:flex;align-items:center;gap:12px;">
        💡 IDEA INBOX
        <span id="idea-inbox-counts" style="font-size:10px;font-weight:400;color:var(--text-3);font-family:var(--font-mono);"></span>
        <button class="party-bar-btn" style="margin-left:auto;" onclick="showIdeaAddModal()">+ New Idea</button>
      </div>

      <!-- Quick-capture bar -->
      <div style="display:flex;gap:8px;margin-bottom:14px;">
        <input type="text" id="huddle-idea-input"
          placeholder="Describe an idea — JARVIS will research it and return a full dossier..."
          style="flex:1;padding:10px 14px;border:1px solid var(--border);border-radius:8px;background:var(--surface-hi);font-size:13px;color:var(--text-1);outline:none;"
          onkeydown="if(event.key==='Enter')huddleAddIdea()"
          onfocus="this.style.borderColor='var(--hue)'"
          onblur="this.style.borderColor='var(--border)'">
        <button class="btn-primary" onclick="huddleAddIdea()">Capture</button>
      </div>

      <!-- Status filter pills -->
      <div style="display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap;" id="idea-filter-pills">
        <button class="idea-filter-pill active" data-status="" onclick="setIdeaFilter(this,'')">All</button>
        <button class="idea-filter-pill" data-status="captured" onclick="setIdeaFilter(this,'captured')">Captured</button>
        <button class="idea-filter-pill" data-status="queued" onclick="setIdeaFilter(this,'queued')">Queued</button>
        <button class="idea-filter-pill" data-status="researching" onclick="setIdeaFilter(this,'researching')">Researching</button>
        <button class="idea-filter-pill" data-status="done" onclick="setIdeaFilter(this,'done')">Done ✓</button>
        <button class="idea-filter-pill" data-status="passed" onclick="setIdeaFilter(this,'passed')">Passed</button>
      </div>

      <!-- Idea list -->
      <div id="idea-inbox-list" style="display:flex;flex-direction:column;gap:8px;">
        <div style="color:var(--text-3);font-size:12px;padding:12px 0;">Loading ideas...</div>
      </div>
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

<!-- Weather modal -->
<div class="weather-modal-overlay hidden" id="weather-modal-overlay" onclick="closeWeatherModal(event)">
  <div class="weather-modal" id="weather-modal">
    <div class="weather-modal-header" id="weather-modal-header">
      <div class="weather-modal-title" id="weather-modal-title">Live Weather</div>
      <button class="weather-modal-close" onclick="closeWeatherModal()">✕</button>
    </div>
    <div class="weather-hero">
      <div class="weather-hero-icon" id="wm-icon">⛅</div>
      <div>
        <div class="weather-hero-temp" id="wm-temp">--°F</div>
        <div class="weather-hero-detail" id="wm-detail">Loading…</div>
      </div>
    </div>
    <div class="weather-grid" id="wm-stats"></div>
    <div id="wm-radar-wrap"></div>
    <div id="wm-forecast-wrap"></div>
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
  loadOverviewReminders();
  loadJarvisTasks();
  loadIdeaInbox();

  // Clock — update every minute
  updateNavClock();
  setInterval(updateNavClock, 30000);

  // Tasks — refresh every 60 seconds
  setInterval(loadJarvisTasks, 60000);

  // Weather widget — load once, refresh every 10 min
  loadWeatherWidget();
  setInterval(loadWeatherWidget, 600000);

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
    case 'overview':     loadApprovals(); loadBriefing(); loadHomeDashboard(); loadOverviewAgents(); loadOverviewCatalyst(); loadOverviewChronicle(); loadOverviewPublishing(); loadOverviewReminders(); loadJarvisTasks(); loadIdeaInbox(); break;
    case 'forge':        forgeInit(); break;
    case 'agents':
      loadLiveAgents();
      // Auto-refresh every 30s while on this view
      _agentsRefreshTimer = setInterval(loadLiveAgents, 30000);
      break;
    case 'huddle':       loadHuddle(); loadPassiveIncomePipeline(); loadDossiers(); loadPartyStatus(); loadIdeaInbox(); break;
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

// ═══════════════════════════════════════════════════════════════
// IDEA INBOX
// ═══════════════════════════════════════════════════════════════

let _ideaFilter = '';

function setIdeaFilter(btn, status) {{
  _ideaFilter = status;
  document.querySelectorAll('.idea-filter-pill').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  loadIdeaInbox();
}}

async function loadIdeaInbox() {{
  const listEl = document.getElementById('idea-inbox-list');
  const badgeEl = document.getElementById('idea-inbox-badge');
  const overviewBadge = document.getElementById('idea-inbox-badge');
  const countsEl = document.getElementById('idea-inbox-counts');
  if (listEl) listEl.innerHTML = '<div style="color:var(--text-3);font-size:11px;">Loading...</div>';

  try {{
    const url = '/api/ideas' + (_ideaFilter ? '?status=' + encodeURIComponent(_ideaFilter) : '');
    const res = await fetch(url);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    const ideas = data.ideas || [];
    const s = (data.stats && data.stats.by_status) || {{}};

    // Update badges
    const pending = (s.captured || 0) + (s.queued || 0) + (s.researching || 0);
    if (badgeEl) badgeEl.textContent = pending || ideas.length;
    if (countsEl) countsEl.textContent =
      [
        s.captured ? s.captured + ' captured' : '',
        s.queued ? s.queued + ' queued' : '',
        s.researching ? s.researching + ' researching' : '',
        s.done ? s.done + ' done' : '',
        s.passed ? s.passed + ' passed' : '',
      ].filter(Boolean).join(' · ');

    // Update overview widget too
    const overviewRecent = document.getElementById('idea-inbox-recent');
    if (overviewRecent) {{
      const recent = (data.ideas || []).filter(i => ['captured','queued','researching'].includes(i.status)).slice(0,5);
      overviewRecent.innerHTML = recent.map(i => renderIdeaChip(i)).join('');
    }}

    if (!listEl) return;
    if (!ideas.length) {{
      listEl.innerHTML = '<div style="color:var(--text-3);font-size:12px;padding:16px 0;text-align:center;">No ideas yet. Capture your first one above.</div>';
      return;
    }}
    listEl.innerHTML = ideas.map(renderIdeaRow).join('');
  }} catch(e) {{
    if (listEl) listEl.innerHTML = '<div style="color:#ef4444;font-size:11px;">Error: ' + e + '</div>';
  }}
}}

function renderIdeaChip(idea) {{
  const chips = {{captured:'💡',queued:'⏳',researching:'🔬',done:'✅',passed:'✕'}};
  const icon = chips[idea.status] || '💡';
  return '<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:12px;background:var(--surface-hi);border:1px solid var(--border);font-size:10px;color:var(--text-2);cursor:pointer;" onclick="switchView(\\'huddle\\')" title="' + escHtml(idea.text) + '">' +
    icon + ' ' + escHtml((idea.text||'').slice(0,28)) + (idea.text.length > 28 ? '…' : '') + '</span>';
}}

function ideaStatusChip(status) {{
  const map = {{
    captured: ['captured','idea-chip-captured'],
    queued: ['queued','idea-chip-queued'],
    researching: ['🔬 researching','idea-chip-researching'],
    done: ['✓ dossier ready','idea-chip-done'],
    passed: ['passed','idea-chip-passed'],
  }};
  const [label, cls] = map[status] || [status, 'idea-chip-captured'];
  return '<span class="idea-status-chip ' + cls + '">' + label + '</span>';
}}

function renderIdeaRow(idea) {{
  const actions = [];

  if (idea.status === 'captured') {{
    actions.push('<button class="idea-act-btn primary" onclick="ideaResearchNow(\\'' + idea.id + '\\')">Research Now ⚡</button>');
    actions.push('<button class="idea-act-btn" onclick="ideaQueue(\\'' + idea.id + '\\')">Queue</button>');
    actions.push('<button class="idea-act-btn danger" onclick="ideaPass(\\'' + idea.id + '\\')">Pass</button>');
  }} else if (idea.status === 'queued') {{
    actions.push('<button class="idea-act-btn primary" onclick="ideaResearchNow(\\'' + idea.id + '\\')">Research Now ⚡</button>');
    actions.push('<button class="idea-act-btn danger" onclick="ideaPass(\\'' + idea.id + '\\')">Pass</button>');
  }} else if (idea.status === 'researching') {{
    actions.push('<button class="idea-act-btn" style="cursor:default;opacity:0.6;" disabled>Researching...</button>');
  }} else if (idea.status === 'done') {{
    if (idea.dossier_id) {{
      actions.push('<button class="idea-act-btn primary" onclick="openDossier(\\'' + idea.dossier_id + '\\')">📄 Open Dossier</button>');
    }}
  }} else if (idea.status === 'passed') {{
    actions.push('<button class="idea-act-btn" onclick="ideaResearchNow(\\'' + idea.id + '\\')">Reconsider</button>');
    actions.push('<button class="idea-act-btn danger" onclick="ideaDelete(\\'' + idea.id + '\\')">Delete</button>');
  }}

  const dossierLink = (idea.status === 'done' && idea.dossier_id)
    ? '<div><span class="idea-dossier-link" onclick="openDossier(\\'' + idea.dossier_id + '\\')">→ Dossier ready — click to review</span></div>'
    : '';

  const age = idea.created_at ? ' · ' + timeAgo(idea.created_at) : '';

  return '<div class="idea-row" id="idea-row-' + idea.id + '">' +
    '<div style="flex:1;min-width:0;">' +
      '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">' +
        ideaStatusChip(idea.status) +
        '<span style="font-size:9px;color:var(--text-3);font-family:var(--font-mono);">' + escHtml(idea.domain||'') + age + '</span>' +
      '</div>' +
      '<div class="idea-row-text">' + escHtml(idea.text) + '</div>' +
      (idea.notes ? '<div class="idea-row-notes">' + escHtml(idea.notes) + '</div>' : '') +
      dossierLink +
    '</div>' +
    '<div class="idea-row-actions">' + actions.join('') + '</div>' +
  '</div>';
}}

function timeAgo(isoStr) {{
  if (!isoStr) return '';
  const diff = Date.now() - new Date(isoStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 2) return 'just now';
  if (m < 60) return m + 'm ago';
  const h = Math.floor(m / 60);
  if (h < 24) return h + 'h ago';
  return Math.floor(h / 24) + 'd ago';
}}

async function huddleAddIdea() {{
  const inp = document.getElementById('huddle-idea-input');
  if (!inp) return;
  const text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  inp.placeholder = 'Saving...';
  try {{
    const res = await fetch('/api/ideas', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ text }}),
    }});
    if (!res.ok) {{ showToast('Error saving idea: ' + res.status, 'error'); return; }}
    showToast('Idea captured. Click "Research Now" to build a dossier.', 'info');
    inp.placeholder = 'Describe an idea — JARVIS will research it and return a full dossier...';
    loadIdeaInbox();
  }} catch(e) {{
    showToast('Error: ' + e, 'error');
    inp.placeholder = 'Describe an idea...';
  }}
}}

async function overviewAddIdea() {{
  const inp = document.getElementById('idea-inbox-input');
  if (!inp) return;
  const text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  try {{
    const res = await fetch('/api/ideas', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ text }}),
    }});
    if (!res.ok) {{ showToast('Error saving idea: ' + res.status, 'error'); return; }}
    showToast('Idea captured! Go to Huddle to research it.', 'info');
    loadIdeaInbox();
  }} catch(e) {{
    showToast('Error: ' + e, 'error');
  }}
}}

async function ideaResearchNow(ideaId) {{
  const rowEl = document.getElementById('idea-row-' + ideaId);
  if (rowEl) rowEl.style.opacity = '0.5';
  showToast('Starting research — this runs in the background. Check Huddle for the dossier.', 'info');
  try {{
    const res = await fetch('/api/ideas/' + encodeURIComponent(ideaId) + '/research-now', {{
      method: 'POST',
    }});
    if (!res.ok) {{
      const err = await res.json().catch(() => ({{}}));
      showToast('Research error: ' + (err.detail || res.status), 'error');
    }} else {{
      const data = await res.json();
      showToast(data.message || 'Research started.', 'info');
    }}
    if (rowEl) rowEl.style.opacity = '1';
    loadIdeaInbox();
    // Poll for dossier after 30s
    setTimeout(() => {{ loadDossiers(); loadIdeaInbox(); }}, 30000);
  }} catch(e) {{
    showToast('Error: ' + e, 'error');
    if (rowEl) rowEl.style.opacity = '1';
  }}
}}

async function ideaQueue(ideaId) {{
  await fetch('/api/ideas/' + encodeURIComponent(ideaId) + '/queue', {{ method: 'POST' }});
  loadIdeaInbox();
}}

async function ideaPass(ideaId) {{
  await fetch('/api/ideas/' + encodeURIComponent(ideaId) + '/pass', {{ method: 'POST' }});
  loadIdeaInbox();
}}

async function ideaDelete(ideaId) {{
  if (!confirm('Delete this idea permanently?')) return;
  await fetch('/api/ideas/' + encodeURIComponent(ideaId), {{ method: 'DELETE' }});
  loadIdeaInbox();
}}

// ═══════════════════════════════════════════════════════════════
// HUDDLE
// ═══════════════════════════════════════════════════════════════

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
    .replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>')
    .replace(/\\*(.+?)\\*/g, '<em>$1</em>');

  const lines = md.split('\\n');
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
    const h3 = line.match(/^###?\\s+(.*)/);
    const h4 = line.match(/^####\\s+(.*)/);
    if (h4) {{ closeList(); closeP(); out.push('<h4>' + inline(e(h4[1])) + '</h4>'); continue; }}
    if (h3) {{ closeList(); closeP(); out.push('<h3>' + inline(e(h3[1])) + '</h3>'); continue; }}

    // unordered list item
    const ul = line.match(/^[-*•]\\s+(.*)/);
    if (ul) {{
      closeP();
      if (!inUl) {{ if (inOl) {{ out.push('</ol>'); inOl=false; }} out.push('<ul>'); inUl=true; }}
      out.push('<li>' + inline(e(ul[1])) + '</li>');
      continue;
    }}

    // ordered list item
    const ol = line.match(/^\\d+\\.\\s+(.*)/);
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
        '<textarea class="dossier-chat-input" id="dossier-chat-input-' + dossierId + '" ' +
          'placeholder="Ask a question or request a change... e.g. &quot;What&apos;s the biggest risk?&quot; or &quot;Reframe this for B2B healthcare.&quot;" ' +
          'rows="2" onkeydown="if(event.key===\\'Enter\\'&&!event.shiftKey){{event.preventDefault();dossierChat(\\'' + dossierId + '\\')}}"></textarea>' +
        '<button class="dossier-chat-send" id="dossier-chat-btn-' + dossierId + '" onclick="dossierChat(\\'' + dossierId + '\\')">Ask →</button>' +
      '</div>' +
      '<div class="dossier-chat-response" id="dossier-chat-resp-' + dossierId + '"></div>' +
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
      const niceName = n.replace(/-/g,' ').replace(/\\b\\w/g, c => c.toUpperCase());
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

/* ═══════════════════════════════════════════════════════════════
   REMINDERS
═══════════════════════════════════════════════════════════════ */
async function loadOverviewReminders() {{
  try {{
    const res = await fetch('/api/reminders');
    if (!res.ok) {{ console.warn('loadOverviewReminders', res.status); return; }}
    const d = await res.json();
    const items = d.reminders || [];
    const countEl = document.getElementById('reminders-count');
    if (countEl) countEl.textContent = items.length || '0';
    const el = document.getElementById('overview-reminders');
    if (!el) return;
    if (items.length === 0) {{
      el.innerHTML = '<div class="list-row-sub" style="color:var(--text-3);font-style:italic;">No pending reminders.</div>';
      return;
    }}
    el.innerHTML = items.slice(0, 5).map(r => {{
      const pri = r.priority === 'high' ? 'dot-error' : r.priority === 'low' ? 'dot-standby' : 'dot-active';
      const due = r.due ? ' <span style="font-size:9px;color:var(--text-3);">' + new Date(r.due).toLocaleDateString([], {{month:'short',day:'numeric'}}) + '</span>' : '';
      return `<div class="list-row" style="align-items:center;">
        <span class="dot ${{pri}}" style="cursor:pointer;flex-shrink:0;" onclick="completeReminder('${{escHtml(r.id)}}')" title="Mark done"></span>
        <div style="flex:1;font-size:12px;color:var(--text-1);">${{escHtml(r.text)}}${{due}}</div>
        <span style="font-size:10px;color:var(--text-3);cursor:pointer;" onclick="deleteReminder('${{escHtml(r.id)}}')" title="Delete">✕</span>
      </div>`;
    }}).join('');
  }} catch(e) {{ console.error('loadOverviewReminders failed', e); }}
}}

async function addReminder() {{
  const input = document.getElementById('reminder-input');
  if (!input) return;
  const text = input.value.trim();
  if (!text) return;
  try {{
    const res = await fetch('/api/reminders', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{text}})
    }});
    if (res.ok) {{ input.value = ''; loadOverviewReminders(); }}
  }} catch(e) {{ console.error('addReminder failed', e); }}
}}

async function completeReminder(id) {{
  try {{
    await fetch('/api/reminders/' + id + '/complete', {{method: 'POST'}});
    loadOverviewReminders();
  }} catch(e) {{}}
}}

async function deleteReminder(id) {{
  try {{
    await fetch('/api/reminders/' + id, {{method: 'DELETE'}});
    loadOverviewReminders();
  }} catch(e) {{}}
}}

/* ═══════════════════════════════════════════════════════════════
   JARVIS TASKS
═══════════════════════════════════════════════════════════════ */
let _tasksFilter = 'all';
let _tasksData   = [];

const _TASK_DOMAIN_CLASS = {{
  personal: 'tdc-personal', work: 'tdc-work', family: 'tdc-family',
  home: 'tdc-home', faith: 'tdc-faith', health: 'tdc-health',
  finance: 'tdc-finance', workshop: 'tdc-workshop',
}};

function setTaskFilter(f) {{
  _tasksFilter = f;
  document.querySelectorAll('.tasks-filter-pill').forEach(p => {{
    p.classList.toggle('active', p.dataset.filter === f);
  }});
  renderJarvisTasks();
}}

async function loadJarvisTasks() {{
  try {{
    const res = await fetch('/api/tasks');
    if (!res.ok) {{ console.warn('loadJarvisTasks', res.status); return; }}
    const d = await res.json();
    _tasksData = d.tasks || [];
    const countEl = document.getElementById('tasks-count');
    if (countEl) countEl.textContent = _tasksData.length || '0';
    renderJarvisTasks();
  }} catch(e) {{ console.error('loadJarvisTasks failed', e); }}
}}

function renderJarvisTasks() {{
  const el = document.getElementById('overview-tasks');
  if (!el) return;

  const today = new Date();
  today.setHours(0,0,0,0);
  const weekEnd = new Date(today); weekEnd.setDate(weekEnd.getDate() + 7);

  let tasks = _tasksData.slice();

  if (_tasksFilter === 'today') {{
    tasks = tasks.filter(t => {{
      if (!t.due) return false;
      const d = new Date(t.due + 'T00:00:00');
      return d <= today || (d.getFullYear() === today.getFullYear() && d.getMonth() === today.getMonth() && d.getDate() === today.getDate());
    }});
  }} else if (_tasksFilter === 'week') {{
    tasks = tasks.filter(t => {{
      if (!t.due) return false;
      const d = new Date(t.due + 'T00:00:00');
      return d >= today && d <= weekEnd;
    }});
  }}

  if (tasks.length === 0) {{
    el.innerHTML = '<div class="list-row-sub" style="color:var(--text-3);font-style:italic;padding:4px 0;">No tasks.</div>';
    return;
  }}

  if (_tasksFilter === 'domain') {{
    // Group by domain
    const groups = {{}};
    tasks.forEach(t => {{
      const dom = t.domain || 'personal';
      if (!groups[dom]) groups[dom] = [];
      groups[dom].push(t);
    }});
    el.innerHTML = Object.keys(groups).sort().map(dom => {{
      const label = dom.charAt(0).toUpperCase() + dom.slice(1);
      const rows = groups[dom].map(t => _renderTaskRow(t)).join('');
      return `<div class="tasks-group-label">${{escHtml(label)}}</div>${{rows}}`;
    }}).join('');
  }} else {{
    el.innerHTML = tasks.map(t => _renderTaskRow(t)).join('');
  }}
}}

function _renderTaskRow(t) {{
  const priClass  = t.priority === 'high' ? 'task-pri-high' : t.priority === 'low' ? 'task-pri-low' : 'task-pri-normal';
  const domClass  = _TASK_DOMAIN_CLASS[t.domain] || 'tdc-personal';
  const domLabel  = (t.domain || 'personal').charAt(0).toUpperCase() + (t.domain || 'personal').slice(1);
  const dueStr    = t.due ? (() => {{
    try {{
      const d = new Date(t.due + 'T00:00:00');
      return d.toLocaleDateString([], {{month:'short', day:'numeric'}});
    }} catch(e) {{ return t.due; }}
  }})() : '';
  const actorStr  = (t.actor && t.actor !== 'chris') ? ` <span class="task-domain-chip" style="background:rgba(148,163,184,0.1);color:var(--text-3);border-color:var(--border);">${{escHtml(t.actor)}}</span>` : '';
  return `<div class="list-row" style="align-items:center;gap:6px;padding:4px 0;">
    <span class="${{priClass}}" style="font-size:10px;flex-shrink:0;cursor:pointer;" title="Priority: ${{escHtml(t.priority)}}">&#9679;</span>
    <div style="flex:1;min-width:0;">
      <span style="font-size:12px;color:var(--text-1);">${{escHtml(t.title)}}</span>
      ${{dueStr ? `<span style="font-size:9px;color:var(--text-3);margin-left:6px;">${{escHtml(dueStr)}}</span>` : ''}}
      ${{actorStr}}
    </div>
    <span class="task-domain-chip ${{domClass}}">${{escHtml(domLabel)}}</span>
    <span style="font-size:11px;color:var(--success);cursor:pointer;padding:0 4px;" onclick="completeJarvisTask('${{escHtml(t.id)}}')" title="Complete">&#10003;</span>
    <span style="font-size:10px;color:var(--text-3);cursor:pointer;padding:0 4px;" onclick="deleteJarvisTask('${{escHtml(t.id)}}')" title="Delete">&#10005;</span>
  </div>`;
}}

async function addJarvisTask() {{
  const titleEl    = document.getElementById('task-title-input');
  const domainEl   = document.getElementById('task-domain-select');
  const priorityEl = document.getElementById('task-priority-select');
  const dueEl      = document.getElementById('task-due-input');
  if (!titleEl) return;
  const title = titleEl.value.trim();
  if (!title) return;
  try {{
    const res = await fetch('/api/tasks', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        title,
        domain:   domainEl   ? domainEl.value   : 'personal',
        priority: priorityEl ? priorityEl.value : 'normal',
        due:      dueEl && dueEl.value ? dueEl.value : null,
        source:   'manual',
      }})
    }});
    if (res.ok) {{
      titleEl.value = '';
      if (dueEl) dueEl.value = '';
      loadJarvisTasks();
    }}
  }} catch(e) {{ console.error('addJarvisTask failed', e); }}
}}

async function completeJarvisTask(id) {{
  try {{
    await fetch('/api/tasks/' + id + '/complete', {{method: 'POST'}});
    loadJarvisTasks();
  }} catch(e) {{}}
}}

async function deleteJarvisTask(id) {{
  try {{
    await fetch('/api/tasks/' + id, {{method: 'DELETE'}});
    loadJarvisTasks();
  }} catch(e) {{}}
}}

/* ═══════════════════════════════════════════════════════════════
   WEATHER WIDGET + MODAL
═══════════════════════════════════════════════════════════════ */
let _weatherData = null;

function _weatherIcon(cond) {{
  if (!cond) return '⛅';
  const c = cond.toLowerCase();
  if (c.includes('thunder') || c.includes('lightning')) return '⛈';
  if (c.includes('snow') || c.includes('blizzard')) return '❄';
  if (c.includes('freezing')) return '❄';
  if (c.includes('rain') || c.includes('shower') || c.includes('drizzle')) return '☂';
  if (c.includes('fog') || c.includes('mist') || c.includes('haze')) return '🌫';
  if (c.includes('cloud') || c.includes('overcast')) return '☁';
  if (c.includes('clear') || c.includes('sunny')) return '☀';
  if (c.includes('wind')) return '💨';
  return '⛅';
}}

async function loadWeatherWidget() {{
  try {{
    const res = await fetch('/api/storm-weather');
    if (!res.ok) return;
    const d = await res.json();
    _weatherData = d;
    const cur = d.current || {{}};
    const icon = cur.icon || _weatherIcon(cur.condition || '');
    const temp = cur.temperature_f != null ? cur.temperature_f + '°' : '--°';
    const cond = cur.condition || '--';
    const el = document.getElementById('nav-weather-btn');
    if (el) el.title = (d.location || '') + ' · ' + cond;
    const iconEl = document.getElementById('nav-weather-icon');
    if (iconEl) iconEl.textContent = icon;
    const tempEl = document.getElementById('nav-weather-temp');
    if (tempEl) tempEl.textContent = temp;
    const condEl = document.getElementById('nav-weather-cond');
    if (condEl) condEl.textContent = cond.length > 12 ? cond.slice(0,12) + '…' : cond;
  }} catch(e) {{ console.warn('weather widget failed', e); }}
}}

function openWeatherModal() {{
  const overlay = document.getElementById('weather-modal-overlay');
  if (overlay) overlay.classList.remove('hidden');
  if (_weatherData) {{
    renderWeatherModal(_weatherData);
  }} else {{
    fetch('/api/storm-weather').then(r => r.json()).then(d => {{
      _weatherData = d;
      renderWeatherModal(d);
    }}).catch(() => {{}});
  }}
}}

function closeWeatherModal(e) {{
  if (e && e.target !== document.getElementById('weather-modal-overlay')) return;
  const overlay = document.getElementById('weather-modal-overlay');
  if (overlay) overlay.classList.add('hidden');
}}

/* Map visual_key → storm-assets filename */
const _VISUAL_ASSET = {{
  'clear_day':              'clear_day.png',
  'clear_night':            'clear_night_no_moon.png',
  'partly_cloudy_day':      'partly_cloudy_day.png',
  'partly_cloudy_night':    'partly_cloudy_day.png',
  'cloudy':                 'partly_cloudy_day.png',
  'light_rain_day':         'light_rain.png',
  'light_rain_night':       'light_rain.png',
  'heavy_rain_day':         'heavy_rain.png',
  'heavy_rain_night':       'heavy_rain.png',
  'thunderstorm_day':       'thunderstorm.png',
  'thunderstorm_night':     'thunderstorm.png',
  'severe_weather_alert':   'thunderstorm.png',
  'snow_day':               'light_snow.png',
  'snow_night':             'light_snow.png',
  'heavy_snow':             'heavy_snow.png',
  'freezing_rain':          'light_snow.png',
  'blizzard':               'blizzard.png',
  'windy':                  'clear_day.png',
  'fog':                    'partly_cloudy_day.png',
  'haze_smoke':             'partly_cloudy_day.png',
  'extreme_heat':           'clear_day.png',
  'extreme_cold':           'light_snow.png',
}};

function renderWeatherModal(d) {{
  const cur = d.current || {{}};
  const icon = cur.icon || _weatherIcon(cur.condition || '');
  const temp = cur.temperature_f != null ? cur.temperature_f + '°F' : '--°F';
  const feels = cur.feels_like_f != null ? 'Feels like ' + cur.feels_like_f + '°F · ' : '';
  const cond = cur.condition || '';
  const wind = cur.wind || '';
  const humidity = cur.humidity_pct != null ? cur.humidity_pct + '% humidity' : '';
  const sunrise = cur.sunrise || '';
  const sunset = cur.sunset || '';
  const visualKey = cur.visual_key || '';
  const assetFile = _VISUAL_ASSET[visualKey] || '';

  const title = document.getElementById('weather-modal-title');
  if (title) title.textContent = (d.location || 'Live Weather') + ' · ' + (cur.stamp_label || '');

  // Condition image — full-width banner above hero
  const modal = document.getElementById('weather-modal');
  let imgBanner = document.getElementById('wm-condition-img');
  if (assetFile) {{
    if (!imgBanner) {{
      imgBanner = document.createElement('img');
      imgBanner.id = 'wm-condition-img';
      imgBanner.style.cssText = 'width:100%;height:180px;object-fit:cover;border-radius:12px;margin-bottom:16px;display:block;';
      modal.insertBefore(imgBanner, document.getElementById('weather-modal-header').nextSibling);
    }}
    imgBanner.src = '/storm-assets/' + assetFile;
    imgBanner.alt = cond;
    imgBanner.style.display = 'block';
  }} else if (imgBanner) {{
    imgBanner.style.display = 'none';
  }}

  const iconEl = document.getElementById('wm-icon');
  if (iconEl) iconEl.textContent = icon;
  const tempEl = document.getElementById('wm-temp');
  if (tempEl) tempEl.textContent = temp;
  const detailEl = document.getElementById('wm-detail');
  if (detailEl) detailEl.innerHTML = escHtml(cond) + '<br>' +
    escHtml(feels) + escHtml(wind ? 'Wind: ' + wind : '') + '<br>' +
    escHtml(humidity) + (sunrise ? ' · 🌅 ' + escHtml(sunrise) : '') + (sunset ? ' · 🌇 ' + escHtml(sunset) : '');

  // Stats grid
  const stats = [
    {{ val: cur.humidity_pct != null ? cur.humidity_pct + '%' : '--', lbl: 'Humidity' }},
    {{ val: cur.dew_point_f != null ? cur.dew_point_f + '°F' : '--', lbl: 'Dew Point' }},
    {{ val: cur.wind || '--', lbl: 'Wind' }},
    {{ val: cur.visibility_miles != null ? cur.visibility_miles + ' mi' : '--', lbl: 'Visibility' }},
    {{ val: cur.pressure_hpa != null ? cur.pressure_hpa + ' hPa' : '--', lbl: 'Pressure' }},
    {{ val: cur.precip_probability != null ? cur.precip_probability + '%' : '--', lbl: 'Precip %' }},
  ];
  const statsEl = document.getElementById('wm-stats');
  if (statsEl) statsEl.innerHTML = stats.map(s =>
    `<div class="weather-stat"><div class="weather-stat-val">${{escHtml(String(s.val))}}</div><div class="weather-stat-lbl">${{escHtml(s.lbl)}}</div></div>`
  ).join('');

  // Radar image
  const radar = d.radar || {{}};
  const radarWrap = document.getElementById('wm-radar-wrap');
  if (radarWrap) {{
    if (radar.loop_image_url) {{
      radarWrap.innerHTML = `<div class="section-label" style="margin:16px 0 8px;">Radar</div>
        <div class="weather-radar-frame">
          <img src="${{escHtml(radar.loop_image_url)}}" alt="Radar loop" onerror="this.parentElement.style.display='none'">
        </div>`;
    }} else {{
      radarWrap.innerHTML = '';
    }}
  }}

  // Forecast
  const forecast = d.forecast || [];
  const forecastWrap = document.getElementById('wm-forecast-wrap');
  if (forecastWrap && forecast.length > 0) {{
    forecastWrap.innerHTML = `<div class="section-label" style="margin:16px 0 8px;">Forecast</div>
      <div class="weather-forecast-row">` +
      forecast.slice(0, 7).map(f => `
        <div class="weather-forecast-item">
          <div class="weather-forecast-label">${{escHtml(f.label || f.name || '')}}</div>
          <div class="weather-forecast-icon">${{f.icon || _weatherIcon(f.condition || '')}}</div>
          <div class="weather-forecast-hi">${{f.temperature != null ? f.temperature + '°' : '--'}}</div>
          <div class="weather-forecast-lo">${{f.condition ? f.condition.slice(0,10) : ''}}</div>
        </div>`).join('') +
      `</div>`;
  }} else if (forecastWrap) {{
    forecastWrap.innerHTML = '';
  }}
}}

/* ── Clock ── */
function updateNavClock() {{
  const el = document.getElementById('nav-clock');
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleTimeString([], {{hour:'2-digit', minute:'2-digit'}});
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
    const endpoint = action === 'deny' ? 'reject' : action;
    const res = await fetch('/api/approvals/' + id + '/' + endpoint, {{ method: 'POST' }});
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
   FORGE — OBJECT-TO-MANUFACTURING WORKSPACE
═══════════════════════════════════════════════════════════════ */

// ── State ─────────────────────────────────────────────────────
let _forgeCurrentProjectId = null;
let _forgeCurrentModelFile = null;
let _forgeThreeLoaded = false;
let _forgeScene = null;
let _forgeCamera = null;
let _forgeRenderer = null;
let _forgeControls = null;
let _forgeMesh = null;
let _forgeCameraStream = null;

// ── Init ──────────────────────────────────────────────────────
async function forgeInit() {{
  await forgeEnsureThree();
  await forgeLoadProjectList();
}}

async function forgeEnsureThree() {{
  if (_forgeThreeLoaded) return;
  // r128 is the last release with legacy examples/js/ paths (OrbitControls, loaders as globals)
  const CDN = 'https://cdn.jsdelivr.net/npm/three@0.128.0';
  const scripts = [
    CDN + '/build/three.min.js',
    CDN + '/examples/js/controls/OrbitControls.js',
    CDN + '/examples/js/loaders/STLLoader.js',
    CDN + '/examples/js/loaders/OBJLoader.js',
    CDN + '/examples/js/loaders/GLTFLoader.js',
  ];
  for (const src of scripts) {{
    await new Promise((res, rej) => {{
      if (document.querySelector('script[src="' + src + '"]')) {{ res(); return; }}
      const s = document.createElement('script');
      s.src = src;
      s.onload = res;
      s.onerror = (e) => {{ console.error('Three.js CDN load failed:', src, e); rej(e); }};
      document.head.appendChild(s);
    }});
  }}
  _forgeThreeLoaded = true;
  forgeInitViewer();
}}

function forgeInitViewer() {{
  const canvas = document.getElementById('forge-3d-canvas');
  const container = document.getElementById('forge-viewer-container');
  if (!canvas || !window.THREE) return;
  _forgeScene = new THREE.Scene();
  _forgeScene.background = new THREE.Color(0x111827);
  const w = container.clientWidth || 480;
  const h = container.clientHeight || 320;
  _forgeCamera = new THREE.PerspectiveCamera(45, w / h, 0.1, 10000);
  _forgeCamera.position.set(150, 120, 200);
  _forgeRenderer = new THREE.WebGLRenderer({{ canvas, antialias: true }});
  _forgeRenderer.setPixelRatio(window.devicePixelRatio);
  _forgeRenderer.setSize(w, h);
  // Lights
  const ambient = new THREE.AmbientLight(0xffffff, 0.55);
  _forgeScene.add(ambient);
  const dir = new THREE.DirectionalLight(0xffffff, 0.9);
  dir.position.set(300, 500, 200);
  _forgeScene.add(dir);
  const dir2 = new THREE.DirectionalLight(0xffffff, 0.35);
  dir2.position.set(-200, -100, -300);
  _forgeScene.add(dir2);
  // Grid + axes
  const grid = new THREE.GridHelper(400, 20, 0x2d3748, 0x2d3748);
  _forgeScene.add(grid);
  const axes = new THREE.AxesHelper(60);
  _forgeScene.add(axes);
  // OrbitControls
  if (THREE.OrbitControls) {{
    _forgeControls = new THREE.OrbitControls(_forgeCamera, _forgeRenderer.domElement);
    _forgeControls.enableDamping = true;
    _forgeControls.dampingFactor = 0.08;
  }}
  // Animate
  function animate() {{
    requestAnimationFrame(animate);
    if (_forgeControls) _forgeControls.update();
    _forgeRenderer.render(_forgeScene, _forgeCamera);
  }}
  animate();
  // Resize observer
  new ResizeObserver(() => {{
    const ww = container.clientWidth || 480;
    const hh = container.clientHeight || 320;
    _forgeCamera.aspect = ww / hh;
    _forgeCamera.updateProjectionMatrix();
    _forgeRenderer.setSize(ww, hh);
  }}).observe(container);
}}

// ── Project list ──────────────────────────────────────────────
async function forgeLoadProjectList() {{
  try {{
    const res = await fetch('/api/forge/projects');
    if (!res.ok) return;
    const data = await res.json();
    const projects = data.projects || [];
    const sel = document.getElementById('forge-project-select');
    if (!sel) return;
    const cur = _forgeCurrentProjectId;
    sel.innerHTML = '<option value="">— Select a project —</option>';
    projects.forEach(p => {{
      const opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = p.title + ' [' + (p.status || 'idea') + ']';
      if (p.id === cur) opt.selected = true;
      sel.appendChild(opt);
    }});
    // Auto-select the first project if nothing is currently selected
    if (!cur && projects.length > 0) {{
      sel.value = projects[0].id;
      await forgeLoadProject(projects[0].id);
    }}
  }} catch(e) {{ console.warn('forgeLoadProjectList', e); }}
}}

async function forgeLoadProject(projectId) {{
  if (!projectId) {{
    _forgeCurrentProjectId = null;
    return;
  }}
  _forgeCurrentProjectId = projectId;
  try {{
    const res = await fetch('/api/forge/projects/' + encodeURIComponent(projectId));
    if (!res.ok) {{
      // Project missing on disk — clear selection and refresh list
      _forgeCurrentProjectId = null;
      const sel = document.getElementById('forge-project-select');
      if (sel) sel.value = '';
      await forgeLoadProjectList();
      return;
    }}
    const project = await res.json();
    forgeRenderProject(project);
  }} catch(e) {{ console.warn('forgeLoadProject', e); }}
}}

function forgeRenderProject(project) {{
  // Status badge
  const badge = document.getElementById('forge-project-status');
  if (badge) {{
    badge.textContent = (project.status || 'idea').replace(/_/g,' ').toUpperCase();
    badge.style.display = 'inline-flex';
  }}
  // Measurements
  forgeRenderMeasurements(project.measurements || []);
  // Capture
  forgeRenderCapture(project.capture_sessions || []);
  // Most recent model
  const models = project.generated_models || [];
  if (models.length > 0) {{
    const latest = models[models.length - 1];
    _forgeCurrentModelFile = latest.filename;
    forgeLoadModel(project.id, latest.filename);
    if (latest.print_readiness && latest.print_readiness.ok) {{
      forgeRenderReadiness(latest.print_readiness);
    }}
    // Show bbox
    if (latest.bounding_box_mm) {{
      forgeShowBbox(latest.bounding_box_mm);
    }}
  }} else {{
    // Show upload zone
    const zone = document.getElementById('forge-upload-zone');
    if (zone) zone.style.display = 'flex';
    const ctrls = document.getElementById('forge-viewer-controls');
    if (ctrls) ctrls.style.display = 'none';
  }}
}}

function forgeRenderMeasurements(measurements) {{
  const list = document.getElementById('forge-meas-list');
  if (!list) return;
  if (!measurements.length) {{
    list.innerHTML = '<div style="color:var(--text-3);font-size:11px;font-family:var(--font-mono);">No measurements yet.</div>';
    return;
  }}
  list.innerHTML = measurements.map(m => {{
    const cls = m.confirmed ? 'meas-confirmed' : 'meas-assumed';
    const lbl = m.confirmed ? 'confirmed' : 'assumed';
    return '<div class="forge-meas-row">'
      + '<span class="forge-meas-label">' + escHtml(m.label) + '</span>'
      + '<span class="forge-meas-value">' + m.value + m.unit + '</span>'
      + '<span class="forge-meas-confirmed ' + cls + '">' + lbl + '</span>'
      + '</div>';
  }}).join('');
}}

function forgeRenderCapture(sessions) {{
  const grid = document.getElementById('forge-capture-grid');
  const confRow = document.getElementById('forge-confidence-row');
  if (!grid) return;
  const allViews = ['front','back','left','right','top','bottom','scale_reference','detail'];
  const required = new Set(['front','back','left','right','top']);
  let captured = new Set();
  let confidence = {{geometry:'—',scale:'—',print_readiness:'—'}};
  if (sessions.length > 0) {{
    const latest = sessions[sessions.length - 1];
    (latest.frames || []).forEach(f => captured.add(f.view_type));
    if (latest.confidence) confidence = latest.confidence;
  }}
  grid.innerHTML = allViews.map(v => {{
    const isRequired = required.has(v);
    let cls = 'view-optional';
    let icon = '–';
    if (captured.has(v)) {{ cls = 'view-captured'; icon = '✓'; }}
    else if (isRequired) {{ cls = 'view-missing'; icon = '✗'; }}
    const label = v.replace('_reference','').replace('_',' ');
    return '<div class="forge-view-chip ' + cls + '">' + icon + '<span>' + escHtml(label) + '</span></div>';
  }}).join('');
  if (confRow) {{
    confRow.innerHTML = [
      ['Geometry', confidence.geometry || '—'],
      ['Scale', confidence.scale || '—'],
      ['Print', confidence.print_readiness || '—'],
    ].map(([lbl, val]) => {{
      const key = (val || 'not_ready').replace(/\\s+/g,'_').toLowerCase();
      return '<span class="forge-conf-chip confidence-' + escHtml(key) + '">' + escHtml(lbl) + ': ' + escHtml(String(val)) + '</span>';
    }}).join('');
  }}
}}

function forgeRenderReadiness(inspection) {{
  const list = document.getElementById('forge-readiness-list');
  const verdict = document.getElementById('forge-readiness-verdict');
  if (!list) return;
  const rows = [];
  if (inspection.is_watertight !== undefined) {{
    const cls = inspection.is_watertight ? 'readiness-ok' : 'readiness-fail';
    const icon = inspection.is_watertight ? '✓' : '✗';
    rows.push('<div class="readiness-row"><span class="' + cls + '">' + icon + '</span><span>Manifold / watertight</span></div>');
  }}
  if (inspection.oversized_for_k2_pro !== undefined) {{
    const cls = inspection.oversized_for_k2_pro ? 'readiness-fail' : 'readiness-ok';
    const icon = inspection.oversized_for_k2_pro ? '✗' : '✓';
    rows.push('<div class="readiness-row"><span class="' + cls + '">' + icon + '</span><span>Fits K2 Pro bed (300×300×600 mm)</span></div>');
  }}
  (inspection.warnings || []).forEach(w => {{
    rows.push('<div class="readiness-row"><span class="readiness-warn">⚠</span><span>' + escHtml(w) + '</span></div>');
  }});
  if (inspection.was_repaired) {{
    rows.push('<div class="readiness-row"><span class="readiness-warn">✎</span><span>Mesh was auto-repaired. ' + escHtml(inspection.repair_notes || '') + '</span></div>');
  }}
  list.innerHTML = rows.join('') || '<div style="color:var(--text-3);font-size:11px;">No issues detected.</div>';
  if (verdict) {{
    const ok = inspection.printable;
    verdict.textContent = 'VERDICT: ' + (ok ? 'PRINTABLE' : 'NOT PRINTABLE');
    verdict.style.color = ok ? 'var(--success)' : 'var(--crimson)';
  }}
}}

function forgeShowBbox(bbox) {{
  const overlay = document.getElementById('forge-bbox-overlay');
  const txt = document.getElementById('forge-bbox-text');
  if (!overlay || !txt) return;
  txt.textContent = 'W ' + (bbox.x||0).toFixed(1) + ' × D ' + (bbox.y||0).toFixed(1) + ' × H ' + (bbox.z||0).toFixed(1) + ' mm';
  overlay.style.display = 'block';
}}

// ── 3D model loading ──────────────────────────────────────────
async function forgeLoadModel(projectId, filename) {{
  if (!_forgeScene || !window.THREE) return;
  const url = '/api/forge/projects/' + encodeURIComponent(projectId) + '/file/' + encodeURIComponent(filename);
  const ext = filename.split('.').pop().toLowerCase();
  // Hide upload zone, show controls
  const zone = document.getElementById('forge-upload-zone');
  if (zone) zone.style.display = 'none';
  const ctrls = document.getElementById('forge-viewer-controls');
  if (ctrls) ctrls.style.display = 'flex';
  // Remove old mesh
  if (_forgeMesh) {{ _forgeScene.remove(_forgeMesh); _forgeMesh = null; }}
  try {{
    if (ext === 'stl' && THREE.STLLoader) {{
      const loader = new THREE.STLLoader();
      loader.load(url, geom => {{
        geom.computeVertexNormals();
        const mat = new THREE.MeshPhongMaterial({{ color: 0xF59E0B, specular: 0x222222, shininess: 40 }});
        _forgeMesh = new THREE.Mesh(geom, mat);
        _forgeMesh.castShadow = true;
        _forgeScene.add(_forgeMesh);
        forgeFitCamera(_forgeMesh);
        forgeUpdateBboxFromMesh(_forgeMesh);
      }}, undefined, e => console.warn('STL load error', e));
    }} else if ((ext === 'glb' || ext === 'gltf') && THREE.GLTFLoader) {{
      const loader = new THREE.GLTFLoader();
      loader.load(url, gltf => {{
        _forgeMesh = gltf.scene;
        _forgeScene.add(_forgeMesh);
        forgeFitCamera(_forgeMesh);
        forgeUpdateBboxFromMesh(_forgeMesh);
      }}, undefined, e => console.warn('GLTF load error', e));
    }} else if (ext === 'obj' && THREE.OBJLoader) {{
      const loader = new THREE.OBJLoader();
      loader.load(url, obj => {{
        _forgeMesh = obj;
        _forgeScene.add(_forgeMesh);
        forgeFitCamera(_forgeMesh);
        forgeUpdateBboxFromMesh(_forgeMesh);
      }}, undefined, e => console.warn('OBJ load error', e));
    }}
  }} catch(e) {{ console.warn('forgeLoadModel error', e); }}
}}

function forgeFitCamera(object) {{
  if (!_forgeCamera || !_forgeControls) return;
  const box = new THREE.Box3().setFromObject(object);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z);
  const fov = _forgeCamera.fov * (Math.PI / 180);
  let dist = Math.abs(maxDim / Math.sin(fov / 2)) * 0.75;
  _forgeCamera.position.set(center.x + dist * 0.7, center.y + dist * 0.5, center.z + dist * 0.9);
  _forgeCamera.lookAt(center);
  if (_forgeControls.target) _forgeControls.target.copy(center);
  _forgeControls.update();
}}

function forgeUpdateBboxFromMesh(object) {{
  if (!object) return;
  const box = new THREE.Box3().setFromObject(object);
  const size = box.getSize(new THREE.Vector3());
  forgeShowBbox({{ x: size.x, y: size.y, z: size.z }});
}}

// ── Camera presets ────────────────────────────────────────────
function forgeCameraReset() {{
  if (!_forgeMesh) return;
  forgeFitCamera(_forgeMesh);
}}
function forgeCameraTop() {{
  if (!_forgeCamera || !_forgeMesh) return;
  const box = new THREE.Box3().setFromObject(_forgeMesh);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const dist = Math.max(size.x, size.z) * 1.2;
  _forgeCamera.position.set(center.x, center.y + dist, center.z + 0.001);
  _forgeCamera.lookAt(center);
  if (_forgeControls) {{ _forgeControls.target.copy(center); _forgeControls.update(); }}
}}
function forgeCameraFront() {{
  if (!_forgeCamera || !_forgeMesh) return;
  const box = new THREE.Box3().setFromObject(_forgeMesh);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const dist = Math.max(size.x, size.y) * 1.5;
  _forgeCamera.position.set(center.x, center.y, center.z + dist);
  _forgeCamera.lookAt(center);
  if (_forgeControls) {{ _forgeControls.target.copy(center); _forgeControls.update(); }}
}}
function forgeCameraLayFlat() {{
  if (!_forgeCamera || !_forgeMesh) return;
  const box = new THREE.Box3().setFromObject(_forgeMesh);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const dist = Math.max(size.x, size.y, size.z) * 1.5;
  _forgeCamera.position.set(center.x + dist, center.y + dist * 0.3, center.z + dist);
  _forgeCamera.lookAt(center);
  if (_forgeControls) {{ _forgeControls.target.copy(center); _forgeControls.update(); }}
}}

function forgeScreenshot() {{
  if (!_forgeRenderer) return;
  _forgeRenderer.render(_forgeScene, _forgeCamera);
  const data = _forgeRenderer.domElement.toDataURL('image/png');
  const a = document.createElement('a');
  a.href = data;
  a.download = 'forge-screenshot.png';
  a.click();
}}

function forgeDownloadSTL() {{
  if (!_forgeCurrentProjectId || !_forgeCurrentModelFile) return;
  const url = '/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId)
    + '/file/' + encodeURIComponent(_forgeCurrentModelFile);
  const a = document.createElement('a');
  a.href = url;
  a.download = _forgeCurrentModelFile;
  a.click();
}}

// ── File upload ───────────────────────────────────────────────
function forgeHandleDrop(event) {{
  event.preventDefault();
  const zone = document.getElementById('forge-upload-zone');
  if (zone) zone.classList.remove('drag-over');
  const file = event.dataTransfer.files[0];
  if (file) forgeUploadFile(file);
}}

async function forgeUploadFile(file) {{
  if (!_forgeCurrentProjectId) {{
    showToast('Select or create a project first.', 'warn');
    return;
  }}
  if (!file) return;
  const fd = new FormData();
  fd.append('file', file);
  try {{
    showToast('Uploading ' + file.name + '...', 'info');
    const res = await fetch('/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId) + '/upload', {{
      method: 'POST', body: fd,
    }});
    if (!res.ok) {{ showToast('Upload failed: ' + res.status, 'error'); return; }}
    const data = await res.json();
    showToast('Uploaded: ' + data.filename, 'info');
    if (data.file_type === '3d_model') {{
      _forgeCurrentModelFile = data.filename;
      forgeLoadModel(_forgeCurrentProjectId, data.filename);
      const dlBtn = document.getElementById('forge-dl-stl-btn');
      if (dlBtn) dlBtn.style.display = 'inline-block';
    }}
    forgeLoadProject(_forgeCurrentProjectId);
    forgeLoadProjectList();
  }} catch(e) {{ showToast('Upload error: ' + e, 'error'); }}
}}

async function forgeUploadPhotos(files) {{
  if (!_forgeCurrentProjectId) {{ showToast('Select or create a project first.', 'warn'); return; }}
  const arr = Array.from(files);
  if (!arr.length) return;
  showToast('Uploading ' + arr.length + ' photo' + (arr.length > 1 ? 's' : '') + '...', 'info');
  let ok = 0, fail = 0;
  for (const file of arr) {{
    const fd = new FormData();
    fd.append('file', file);
    try {{
      const res = await fetch('/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId) + '/upload', {{
        method: 'POST', body: fd,
      }});
      if (res.ok) ok++; else fail++;
    }} catch(e) {{ fail++; }}
  }}
  if (fail === 0) {{
    showToast(ok + ' photo' + (ok > 1 ? 's' : '') + ' uploaded ✓', 'success');
  }} else {{
    showToast(ok + ' uploaded, ' + fail + ' failed', fail === arr.length ? 'error' : 'warn');
  }}
  forgeLoadProject(_forgeCurrentProjectId);
}}

// ── Chat ──────────────────────────────────────────────────────
async function forgeSendChat() {{
  if (!_forgeCurrentProjectId) {{ showToast('Select a project first.', 'warn'); return; }}
  const input = document.getElementById('forge-chat-input');
  if (!input) return;
  const message = input.value.trim();
  if (!message) return;
  input.value = '';
  forgeAppendMsg(message, 'user');
  try {{
    const res = await fetch('/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId) + '/chat', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ message }}),
    }});
    if (!res.ok) {{ forgeAppendMsg('Error: ' + res.status, 'jarvis'); return; }}
    const data = await res.json();
    forgeAppendMsg(data.reply || '(no reply)', 'jarvis');
    // Auto-load generated model if chat triggered CAD generation
    if (data.generated_model && data.generated_model.filename) {{
      forgeAppendMsg('✓ Model generated: ' + data.generated_model.filename +
        ' (engine: ' + (data.generated_model.export_engine || '?') + ')', 'jarvis');
      forgeHandleChatGeneration(data.generated_model);
    }}
  }} catch(e) {{ forgeAppendMsg('Network error: ' + e, 'jarvis'); }}
}}

function forgeAppendMsg(text, role) {{
  const container = document.getElementById('forge-chat-messages');
  if (!container) return;
  const div = document.createElement('div');
  div.className = role === 'user' ? 'forge-msg-user' : 'forge-msg-jarvis';
  div.textContent = text;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}}

// ── Measurements ──────────────────────────────────────────────
async function forgeAddMeasurement() {{
  if (!_forgeCurrentProjectId) {{ showToast('Select a project first.', 'warn'); return; }}
  const label = prompt('Measurement label (e.g. hole_diameter, overall_width):');
  if (!label) return;
  const valStr = prompt('Value (number):');
  if (!valStr) return;
  const value = parseFloat(valStr);
  if (isNaN(value)) {{ showToast('Invalid number.', 'warn'); return; }}
  const unit = prompt('Unit (mm / cm / in):', 'mm') || 'mm';
  const confirmedStr = prompt('Confirmed by you? (yes/no):', 'yes');
  const confirmed = (confirmedStr || 'yes').trim().toLowerCase() === 'yes';
  try {{
    const res = await fetch('/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId) + '/measurements', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ label, value, unit, confirmed }}),
    }});
    if (!res.ok) {{ showToast('Measurement error: ' + res.status, 'error'); return; }}
    showToast('Measurement added.', 'info');
    forgeLoadProject(_forgeCurrentProjectId);
  }} catch(e) {{ showToast('Error: ' + e, 'error'); }}
}}

// ── Inspection ────────────────────────────────────────────────
async function forgeInspectActive() {{
  if (!_forgeCurrentProjectId || !_forgeCurrentModelFile) {{
    showToast('No model loaded. Upload a 3D file first.', 'warn');
    return;
  }}
  showToast('Inspecting model...', 'info');
  try {{
    const res = await fetch('/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId) + '/inspect', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ model_filename: _forgeCurrentModelFile }}),
    }});
    if (!res.ok) {{ showToast('Inspect error: ' + res.status, 'error'); return; }}
    const data = await res.json();
    forgeRenderReadiness(data);
    if (data.bounding_box_mm) forgeShowBbox(data.bounding_box_mm);
    showToast(data.printable ? 'Model is printable.' : 'Model has issues — see readiness panel.', data.printable ? 'info' : 'warn');
    forgeLoadProjectList();
  }} catch(e) {{ showToast('Error: ' + e, 'error'); }}
}}

// ── Slice ─────────────────────────────────────────────────────
async function forgeStageSlice() {{
  if (!_forgeCurrentProjectId) {{ showToast('Select a project first.', 'warn'); return; }}
  // Find model_id from project
  try {{
    const pRes = await fetch('/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId));
    if (!pRes.ok) return;
    const project = await pRes.json();
    const models = project.generated_models || [];
    if (!models.length) {{ showToast('No model to slice. Upload a 3D file first.', 'warn'); return; }}
    const model_id = models[models.length - 1].model_id;
    const material = prompt('Material (PLA, PETG, ABS...):', 'PLA') || 'PLA';
    const res = await fetch('/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId) + '/slice', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ model_id, material }}),
    }});
    if (!res.ok) {{ showToast('Slice error: ' + res.status, 'error'); return; }}
    showToast('Slice report staged. Ready for approval.', 'info');
    forgeLoadProject(_forgeCurrentProjectId);
    forgeLoadProjectList();
  }} catch(e) {{ showToast('Error: ' + e, 'error'); }}
}}

// ── Approve ───────────────────────────────────────────────────
async function forgeApprove() {{
  if (!_forgeCurrentProjectId) {{ showToast('Select a project first.', 'warn'); return; }}
  const notes = prompt('Approval notes (optional):') || '';
  try {{
    const res = await fetch('/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId) + '/approve', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ notes }}),
    }});
    if (!res.ok) {{ showToast('Approve error: ' + res.status, 'error'); return; }}
    const data = await res.json();
    showToast('Approved. Status: ' + (data.new_status || '').replace(/_/g,' '), 'info');
    forgeLoadProject(_forgeCurrentProjectId);
    forgeLoadProjectList();
  }} catch(e) {{ showToast('Error: ' + e, 'error'); }}
}}

// ── Archive ───────────────────────────────────────────────────
async function forgeArchive() {{
  if (!_forgeCurrentProjectId) {{ showToast('Select a project first.', 'warn'); return; }}
  if (!confirm('Archive this project?')) return;
  try {{
    const res = await fetch('/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId), {{
      method: 'DELETE',
    }});
    if (!res.ok) {{ showToast('Archive error: ' + res.status, 'error'); return; }}
    showToast('Project archived.', 'info');
    _forgeCurrentProjectId = null;
    forgeLoadProjectList();
  }} catch(e) {{ showToast('Error: ' + e, 'error'); }}
}}

// ── Describe Part quick-action ────────────────────────────────
function forgeQuickDescribe() {{
  if (!_forgeCurrentProjectId) {{ showToast('Select a project first.', 'warn'); return; }}
  const hint = prompt(
    'Describe the part you want to build (include rough dimensions and purpose):\\n\\n' +
    'Example: "Wall bracket 80x40mm with two 5mm mounting holes, 3mm thick, for holding a 2kg shelf"'
  );
  if (!hint) return;
  const input = document.getElementById('forge-chat-input');
  if (input) {{ input.value = hint; }}
  forgeSendChat();
}}

// ── Sketch upload & analyze ───────────────────────────────────
async function forgeHandleSketchUpload(fileInput) {{
  if (!_forgeCurrentProjectId) {{ showToast('Select a project first.', 'warn'); return; }}
  const file = fileInput.files[0];
  if (!file) return;

  const statusEl = document.getElementById('forge-sketch-status');
  if (statusEl) statusEl.textContent = 'Uploading...';

  // Upload to project uploads/
  const fd = new FormData();
  fd.append('file', file);
  fd.append('project_id', _forgeCurrentProjectId);
  let uploadedFilename = '';
  try {{
    const upRes = await fetch('/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId) + '/upload', {{
      method: 'POST', body: fd,
    }});
    if (!upRes.ok) {{
      if (statusEl) statusEl.textContent = 'Upload failed.';
      showToast('Sketch upload failed: ' + upRes.status, 'error');
      fileInput.value = '';
      return;
    }}
    const upData = await upRes.json();
    uploadedFilename = upData.filename || file.name;
  }} catch(e) {{
    if (statusEl) statusEl.textContent = 'Upload error.';
    showToast('Upload error: ' + e, 'error');
    fileInput.value = '';
    return;
  }}

  if (statusEl) statusEl.textContent = 'Analyzing with vision AI...';
  forgeAppendMsg('Sketch uploaded: ' + uploadedFilename + ' — running vision analysis...', 'user');

  try {{
    const res = await fetch('/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId) + '/analyze-sketch', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ image_filename: uploadedFilename, auto_generate: true }}),
    }});
    if (!res.ok) {{
      const err = await res.json().catch(() => ({{}}));
      forgeAppendMsg('Vision analysis failed: ' + (err.detail || res.status), 'jarvis');
      if (statusEl) statusEl.textContent = 'Analysis failed.';
    }} else {{
      const data = await res.json();
      const ex = data.extraction || {{}};
      let summary = 'Sketch analyzed.';
      if (ex.object_description) summary = ex.object_description;
      if (ex.confidence) summary += ' (confidence: ' + ex.confidence + ')';
      if (ex.assumptions && ex.assumptions.length) {{
        summary += '\\n\\nAssumptions: ' + ex.assumptions.join('; ');
      }}
      if (data.generation && data.generation.ok) {{
        summary += '\\n\\n✓ Model generated: ' + (data.generation.filename || '');
        forgeLoadProject(_forgeCurrentProjectId);
        forgeLoadProjectList();
      }} else if (data.generation && !data.generation.ok) {{
        summary += '\\n\\nModel generation: ' + (data.generation.error || 'not attempted');
      }} else if (!ex.ready_to_generate) {{
        summary += '\\n\\nNot enough info to generate automatically — add measurements and try again.';
      }}
      forgeAppendMsg(summary, 'jarvis');
      if (statusEl) statusEl.textContent = '✓ Done';
    }}
  }} catch(e) {{
    forgeAppendMsg('Analysis error: ' + e, 'jarvis');
    if (statusEl) statusEl.textContent = 'Error.';
  }}
  fileInput.value = '';
}}

// ── Design Council ────────────────────────────────────────────
let _forgeCouncilRunning = false;

function forgeRunDesignCouncil() {{
  if (!_forgeCurrentProjectId) {{ showToast('Select a project first.', 'warn'); return; }}
  const modal = document.getElementById('forge-council-modal');
  if (modal) {{
    // Reset state
    const statusEl = document.getElementById('forge-council-status');
    const rtEl = document.getElementById('forge-council-roundtable');
    const specEl = document.getElementById('forge-council-spec');
    const resEl = document.getElementById('forge-council-result');
    const btn = document.getElementById('forge-council-submit-btn');
    if (statusEl) {{ statusEl.style.display = 'none'; statusEl.textContent = 'Council in session...'; }}
    if (rtEl) {{ rtEl.style.display = 'none'; rtEl.innerHTML = ''; }}
    if (specEl) {{ specEl.style.display = 'none'; specEl.textContent = ''; }}
    if (resEl) {{ resEl.style.display = 'none'; resEl.textContent = ''; }}
    if (btn) btn.disabled = false;
    modal.classList.remove('hidden');
  }}
}}

async function forgeSubmitDesignCouncil() {{
  if (_forgeCouncilRunning) return;
  if (!_forgeCurrentProjectId) {{ showToast('Select a project first.', 'warn'); return; }}
  const briefEl = document.getElementById('forge-council-brief');
  const brief = (briefEl && briefEl.value.trim()) ? briefEl.value.trim() : '';
  if (!brief) {{ showToast('Enter a design brief first.', 'warn'); return; }}

  _forgeCouncilRunning = true;
  const btn = document.getElementById('forge-council-submit-btn');
  if (btn) btn.disabled = true;
  const statusEl = document.getElementById('forge-council-status');
  if (statusEl) {{ statusEl.style.display = 'block'; statusEl.textContent = 'Council in session — 4 agents deliberating...'; }}

  try {{
    const res = await fetch('/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId) + '/design-council', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ brief, auto_inspect: true }}),
    }});
    if (!res.ok) {{
      const err = await res.json().catch(() => ({{}}));
      if (statusEl) statusEl.textContent = 'Council failed: ' + (err.detail || res.status);
      _forgeCouncilRunning = false;
      if (btn) btn.disabled = false;
      return;
    }}
    const data = await res.json();

    // Render roundtable
    const rtEl = document.getElementById('forge-council-roundtable');
    if (rtEl && data.roundtable) {{
      rtEl.innerHTML = data.roundtable.map(r =>
        '<div style="margin-bottom:10px;">' +
        '<div style="font-size:10px;font-weight:700;color:var(--hue);letter-spacing:0.05em;margin-bottom:3px;">' +
        r.agent.toUpperCase() + ' · ' + r.title + '</div>' +
        '<div style="font-size:11px;color:var(--text-2);line-height:1.5;">' + r.response + '</div>' +
        '</div>'
      ).join('');
      rtEl.style.display = 'block';
    }}

    // Render spec
    const specEl = document.getElementById('forge-council-spec');
    if (specEl && data.spec) {{
      const spec = data.spec;
      const specLines = [];
      if (spec.part_name) specLines.push('Part: ' + spec.part_name);
      if (spec.shape_family) specLines.push('Shape: ' + spec.shape_family);
      if (spec.material) specLines.push('Material: ' + spec.material);
      if (spec.machine) specLines.push('Machine: ' + spec.machine);
      if (spec.dimensions) specLines.push('Dimensions:\\n  ' + spec.dimensions.replace(/\\n/g, '\\n  '));
      if (spec.constraints) specLines.push('Constraints: ' + spec.constraints);
      if (spec.design_notes) specLines.push('Notes: ' + spec.design_notes);
      specEl.textContent = specLines.join('\\n');
      specEl.style.display = 'block';
    }}

    // Result summary
    const resEl = document.getElementById('forge-council-result');
    if (resEl) {{
      if (data.ok && data.generation && data.generation.filename) {{
        const insp = data.inspection || {{}};
        const printable = insp.printable;
        resEl.innerHTML =
          '<span style="color:#10b981;font-weight:600;">✓ Model generated: ' + data.generation.filename + '</span><br>' +
          '<span style="font-size:10px;color:var(--text-3);">Engine: ' + (data.generation.export_engine || '?') +
          ' · Status: ' + (data.generation.export_status || '?') + '</span>' +
          (printable != null ? '<br><span style="font-size:10px;color:' + (printable ? '#10b981' : '#f59e0b') +
            ';">Print readiness: ' + (printable ? '✓ Printable' : '⚠ Review required') + '</span>' : '');
      }} else {{
        resEl.innerHTML = '<span style="color:#f59e0b;">Model generation: ' +
          (data.generation && data.generation.error ? data.generation.error : 'not available') + '</span>';
      }}
      resEl.style.display = 'block';
    }}

    if (statusEl) statusEl.textContent = data.ok ? '✓ Council complete — model ready for review.' : 'Council complete.';
    if (data.ok) {{
      forgeLoadProject(_forgeCurrentProjectId);
      forgeLoadProjectList();
    }}
  }} catch(e) {{
    if (statusEl) statusEl.textContent = 'Error: ' + e;
  }}
  _forgeCouncilRunning = false;
  if (btn) btn.disabled = false;
}}

// Auto-load model generated from chat
async function forgeHandleChatGeneration(genModel) {{
  if (!genModel || !genModel.filename) return;
  const ext = genModel.filename.split('.').pop().toLowerCase();
  if (['stl', '3mf', 'obj', 'glb'].includes(ext)) {{
    _forgeCurrentModelFile = genModel.filename;
    try {{
      forgeLoadModel(_forgeCurrentProjectId, genModel.filename);
      showToast('Model generated and loaded: ' + genModel.filename, 'info');
    }} catch(e) {{ /* viewer errors are non-fatal */ }}
  }} else {{
    showToast('Model generated (' + ext.toUpperCase() + '): ' + genModel.filename, 'info');
  }}
  forgeLoadProject(_forgeCurrentProjectId);
  forgeLoadProjectList();
}}

// ── Timeline ──────────────────────────────────────────────────
async function forgeShowTimeline() {{
  if (!_forgeCurrentProjectId) {{ showToast('Select a project first.', 'warn'); return; }}
  try {{
    const res = await fetch('/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId) + '/timeline');
    if (!res.ok) return;
    const data = await res.json();
    const list = document.getElementById('forge-timeline-list');
    if (!list) return;
    list.innerHTML = (data.events || []).map(ev => {{
      const ts = (ev.ts || '').replace('T',' ').replace(/\\.\\d+Z$/,'').replace('Z','');
      return '<div class="forge-tl-row">'
        + '<span class="forge-tl-ts">' + escHtml(ts) + '</span>'
        + '<span class="forge-tl-event">' + escHtml(ev.event || '') + '</span>'
        + '<span class="forge-tl-detail">' + escHtml(ev.detail || '') + '</span>'
        + '</div>';
    }}).join('') || '<div style="color:var(--text-3);font-size:11px;font-family:var(--font-mono);">No events yet.</div>';
    const modal = document.getElementById('forge-timeline-modal');
    if (modal) modal.classList.remove('hidden');
  }} catch(e) {{ showToast('Error: ' + e, 'error'); }}
}}

// ── New project ───────────────────────────────────────────────
async function forgeNewProject() {{
  const title = prompt('Project title:');
  if (!title || !title.trim()) return;
  const description = prompt('Description (optional):') || '';
  try {{
    const res = await fetch('/api/forge/projects', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ title: title.trim(), description }}),
    }});
    if (!res.ok) {{ showToast('Create error: ' + res.status, 'error'); return; }}
    const project = await res.json();
    showToast('Project created: ' + project.title, 'info');
    await forgeLoadProjectList();
    const sel = document.getElementById('forge-project-select');
    if (sel) {{ sel.value = project.id; }}
    _forgeCurrentProjectId = project.id;
    forgeRenderProject(project);
  }} catch(e) {{ showToast('Error: ' + e, 'error'); }}
}}

// ── Camera capture ────────────────────────────────────────────
async function forgeCameraCapture() {{
  if (!_forgeCurrentProjectId) {{ showToast('Select a project first.', 'warn'); return; }}
  const modal = document.getElementById('forge-camera-modal');
  const video = document.getElementById('forge-camera-video');
  if (!modal || !video) return;
  try {{
    _forgeCameraStream = await navigator.mediaDevices.getUserMedia({{ video: true }});
    video.srcObject = _forgeCameraStream;
    modal.classList.remove('hidden');
  }} catch(e) {{
    showToast('Camera not available: ' + e.message, 'warn');
  }}
}}

async function forgeCaptureSnapshot() {{
  const video = document.getElementById('forge-camera-video');
  const viewType = document.getElementById('forge-camera-view-type');
  if (!video || !_forgeCurrentProjectId) return;
  // Draw to canvas and get blob
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  canvas.getContext('2d').drawImage(video, 0, 0);
  canvas.toBlob(async blob => {{
    const filename = 'capture_' + (viewType ? viewType.value : 'view') + '_' + Date.now() + '.jpg';
    const file = new File([blob], filename, {{ type: 'image/jpeg' }});
    // Upload
    const fd = new FormData();
    fd.append('file', file);
    try {{
      const upRes = await fetch('/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId) + '/upload', {{
        method: 'POST', body: fd,
      }});
      if (!upRes.ok) {{ showToast('Upload error: ' + upRes.status, 'error'); return; }}
      // Register frame
      const vt = viewType ? viewType.value : 'front';
      await fetch('/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId) + '/capture-frame', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{ filename, view_type: vt }}),
      }});
      showToast('Frame captured: ' + vt, 'info');
      forgeLoadProject(_forgeCurrentProjectId);
    }} catch(e) {{ showToast('Capture error: ' + e, 'error'); }}
  }}, 'image/jpeg', 0.90);
  forgeCloseCameraModal();
}}

function forgeCloseCameraModal() {{
  const modal = document.getElementById('forge-camera-modal');
  if (modal) modal.classList.add('hidden');
  if (_forgeCameraStream) {{
    _forgeCameraStream.getTracks().forEach(t => t.stop());
    _forgeCameraStream = null;
  }}
  const video = document.getElementById('forge-camera-video');
  if (video) video.srcObject = null;
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
    case 'kdp.2fa_required':
      kdpShow2faModal();
      break;
    case 'kdp.sync_complete':
      kdpHide2faModal();
      if (pkt.ok) {{
        showToast('📚 KDP sync complete!', 'success');
        kdpLoadStatus && kdpLoadStatus();
      }} else {{
        showToast('⚠️ KDP sync failed: ' + (pkt.error || 'unknown'), 'warning');
      }}
      break;
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

/* ── KDP / Amazon Publishing ──────────────────────────────────── */
async function kdpLoadStatus() {{
  try {{
    const r = await fetch('/api/kdp/status');
    const d = await r.json();
    const el = document.getElementById('kdp-settings-status');
    if (!el) return;
    if (d.configured) {{
      el.textContent = d.last_sync ? `Last sync: ${{d.last_sync}}` : 'Credentials saved. Ready to sync.';
    }} else {{
      el.textContent = 'Not configured — enter credentials below.';
    }}
  }} catch(e) {{ /* ignore */ }}
}}

async function kdpSaveCredentials() {{
  const email = document.getElementById('kdp-email')?.value.trim();
  const password = document.getElementById('kdp-password')?.value;
  const msg = document.getElementById('kdp-settings-msg');
  if (!email || !password) {{ if(msg) msg.textContent = 'Email and password required.'; return; }}
  try {{
    const r = await fetch('/api/kdp/credentials', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{email, password}})
    }});
    const d = await r.json();
    if (msg) msg.textContent = d.ok ? '✓ Credentials saved.' : ('Error: ' + (d.detail || 'unknown'));
    if (d.ok) {{ document.getElementById('kdp-email').value = ''; document.getElementById('kdp-password').value = ''; kdpLoadStatus(); }}
  }} catch(e) {{ if(msg) msg.textContent = 'Error: ' + e.message; }}
}}

async function kdpTriggerSync() {{
  const btn = document.getElementById('kdp-sync-btn');
  const msg = document.getElementById('kdp-settings-msg');
  if (btn) {{ btn.disabled = true; btn.textContent = '⏳ Starting…'; }}
  try {{
    const r = await fetch('/api/kdp/sync', {{method:'POST'}});
    const d = await r.json();
    if (d.ok && d.started) {{
      if (msg) msg.textContent = '⏳ Sync running in background…';
      if (btn) btn.textContent = '⏳ Syncing…';
      // Poll status every 5s
      const poll = setInterval(async () => {{
        try {{
          const sr = await fetch('/api/kdp/sync-status');
          const sd = await sr.json();
          if (sd.status === 'needs_2fa') {{
            kdpShow2faModal();
          }} else if (sd.status === 'done') {{
            clearInterval(poll);
            if (btn) {{ btn.disabled = false; btn.textContent = '🔄 Sync Now'; }}
            if (msg) msg.textContent = '✓ Sync complete!';
            kdpLoadStatus();
          }} else if (sd.status === 'error') {{
            clearInterval(poll);
            if (btn) {{ btn.disabled = false; btn.textContent = '🔄 Sync Now'; }}
            if (msg) msg.textContent = '⚠️ Sync failed. Check KDP credentials.';
          }}
        }} catch(e) {{ clearInterval(poll); }}
      }}, 5000);
    }} else if (!d.ok) {{
      if (msg) msg.textContent = d.detail || 'Sync failed.';
      if (btn) {{ btn.disabled = false; btn.textContent = '🔄 Sync Now'; }}
    }}
  }} catch(e) {{
    if (msg) msg.textContent = 'Error: ' + e.message;
    if (btn) {{ btn.disabled = false; btn.textContent = '🔄 Sync Now'; }}
  }}
}}

/* ── KDP 2FA ─────────────────────────────────────────────────── */
function kdpShow2faModal() {{
  const el = document.getElementById('kdp-2fa-overlay');
  if (el) {{ el.style.display = 'flex'; setTimeout(() => {{ document.getElementById('kdp-2fa-input')?.focus(); }}, 100); }}
}}
function kdpHide2faModal() {{
  const el = document.getElementById('kdp-2fa-overlay');
  if (el) el.style.display = 'none';
}}
async function kdpSubmit2fa() {{
  const code = document.getElementById('kdp-2fa-input')?.value?.trim();
  const msg = document.getElementById('kdp-2fa-msg');
  if (!code) {{ if(msg) msg.textContent = 'Please enter the code.'; return; }}
  if(msg) msg.textContent = 'Submitting…';
  try {{
    const r = await fetch('/api/kdp/2fa-code', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{code}})
    }});
    const d = await r.json();
    if (d.ok) {{
      if(msg) msg.textContent = 'Code sent ✓ — continuing sync…';
      setTimeout(kdpHide2faModal, 2000);
    }} else {{
      if(msg) msg.textContent = 'Error: ' + (d.detail || 'unknown');
    }}
  }} catch(e) {{
    if(msg) msg.textContent = 'Error: ' + e.message;
  }}
}}
function kdpCancel2fa() {{
  kdpHide2faModal();
  showToast('KDP sync cancelled', 'warning');
}}

/* ── Boot ── */
document.addEventListener('DOMContentLoaded', init);
</script>

<!-- ── KDP 2FA Modal ─────────────────────────────────────────── -->
<div id="kdp-2fa-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:10000;align-items:center;justify-content:center;">
  <div style="background:var(--glass-bg,rgba(20,22,35,0.97));border:1px solid rgba(255,255,255,0.12);border-radius:18px;padding:36px 40px;max-width:420px;width:90%;box-shadow:0 24px 80px rgba(0,0,0,0.6);">
    <div style="font-size:28px;margin-bottom:12px;">🔐</div>
    <div style="font-size:16px;font-weight:600;color:rgba(255,255,255,0.9);margin-bottom:8px;">Amazon Verification Required</div>
    <div style="font-size:13px;color:rgba(255,255,255,0.5);margin-bottom:24px;line-height:1.5;">
      Amazon is asking for a one-time verification code. Check your email or authenticator app and enter it below.
    </div>
    <input id="kdp-2fa-input" type="text" inputmode="numeric" pattern="[0-9]*" maxlength="8"
      placeholder="Enter code (e.g. 123456)"
      style="width:100%;box-sizing:border-box;background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.15);border-radius:10px;padding:12px 16px;font-size:18px;letter-spacing:0.2em;color:#fff;outline:none;margin-bottom:16px;text-align:center;"
      onkeydown="if(event.key==='Enter') kdpSubmit2fa()">
    <div style="display:flex;gap:10px;">
      <button class="glass-btn" style="flex:1;padding:12px;" onclick="kdpSubmit2fa()">Submit Code</button>
      <button class="glass-btn" style="padding:12px 18px;opacity:0.6;" onclick="kdpCancel2fa()">Cancel</button>
    </div>
    <div id="kdp-2fa-msg" style="margin-top:12px;font-size:12px;color:rgba(255,255,200,0.6);min-height:16px;"></div>
  </div>
</div>

</body>
</html>"""
