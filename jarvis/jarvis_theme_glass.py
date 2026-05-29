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
  <link rel="icon" href="data:,">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
  <style>

/* ═══════════════════════════════════════════════════════════════════
   CSS CUSTOM PROPERTIES
═══════════════════════════════════════════════════════════════════ */
:root {{
  /* Surface — Dark Command Center */
  --bg:          #07101E;
  --bg-gradient: linear-gradient(145deg, #08121F 0%, #060E1A 40%, #07101C 100%);
  --surface:     rgba(255,255,255,0.065);
  --surface-hi:  rgba(255,255,255,0.10);
  --border:      rgba(255,255,255,0.11);
  --border-hi:   rgba(255,255,255,0.20);

  /* Text */
  --text-1:  #FFFFFF;
  --text-2:  #D8E8F4;
  --text-3:  #A8C4D8;

  /* Fixed semantic colors */
  --navy:    #0A1628;
  --crimson: #EF4444;
  --gold:    #F59E0B;
  --success: #10B981;

  /* Hue tokens — arc reactor blue */
  --hue:      #3B9EFF;
  --hue-dim:  rgba(59,158,255,0.14);
  --hue-glow: rgba(59,158,255,0.40);
  --hue-tint: rgba(59,158,255,0.05);
  --hue-rgb:  59, 158, 255;

  /* Typography */
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'Fira Code', 'SF Mono', monospace;

  /* Layout */
  --nav-w:    210px;
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
[data-domain="news"]          {{ --hue: #0369A1; --hue-dim: rgba(3,105,161,0.12); --hue-glow: rgba(3,105,161,0.35); --hue-tint: rgba(3,105,161,0.04); --hue-rgb: 3,105,161; }}
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
  opacity: 0.06;
  pointer-events: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='56' height='100'%3E%3Cpath d='M28 66L0 50V17L28 0l28 17v33L28 66zm0 34L0 83V67l28 17 28-17v17L28 100z' fill='none' stroke='%233B9EFF' stroke-width='0.8'/%3E%3C/svg%3E");
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
   LIQUID GLASS CARD — Apple iOS 26 Liquid Glass aesthetic
   Five-layer technique:
     1. Frosted base        — deep blur + saturation picks up background
     2. Specular highlight  — inset top-edge bright line (THE key effect)
     3. Refraction sweep    — ::before diagonal light across glass face
     4. Hue tint            — ::after arc reactor ambient wash
     5. Interactive spring  — hover lifts + brightens specular
═══════════════════════════════════════════════════════════════════ */
.card {{
  position: relative;
  overflow: hidden;
  background: rgba(255,255,255,0.07);
  backdrop-filter: blur(48px) saturate(200%) brightness(1.08);
  -webkit-backdrop-filter: blur(48px) saturate(200%) brightness(1.08);
  border: 1px solid rgba(255,255,255,0.18);
  border-radius: 20px;
  box-shadow:
    /* Depth */
    0  2px  4px  rgba(0,0,0,0.30),
    0  8px  24px rgba(0,0,0,0.40),
    0 24px  56px rgba(0,0,0,0.28),
    /* Specular top edge — the Liquid Glass signature */
    inset 0  1px 0 rgba(255,255,255,0.55),
    /* Specular left edge */
    inset 1px 0  0 rgba(255,255,255,0.18),
    /* Base shadow */
    inset 0 -1px 0 rgba(0,0,0,0.12);
  transition:
    transform   0.35s cubic-bezier(0.34,1.56,0.64,1),
    box-shadow  0.35s ease,
    background  0.25s ease;
}}

/* Refraction sweep — diagonal light across the glass face */
.card::before {{
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 19px;
  background: linear-gradient(
    135deg,
    rgba(255,255,255,0.16) 0%,
    rgba(255,255,255,0.05) 30%,
    transparent 55%,
    rgba(255,255,255,0.02) 100%
  );
  pointer-events: none;
  z-index: 1;
}}

/* Hue ambient wash — arc reactor tint at top */
.card::after {{
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 50%;
  background: linear-gradient(
    180deg,
    rgba(var(--hue-rgb), 0.055) 0%,
    transparent 100%
  );
  border-radius: 19px 19px 0 0;
  pointer-events: none;
  z-index: 0;
  transition: opacity 0.35s ease;
}}

/* Liquid Glass interactive hover — surface brightens and lifts */
.card:hover {{
  background: rgba(255,255,255,0.10);
  transform: translateY(-2px);
  box-shadow:
    0  2px  4px  rgba(0,0,0,0.25),
    0  8px  32px rgba(0,0,0,0.45),
    0 32px  64px rgba(0,0,0,0.32),
    inset 0  1px 0 rgba(255,255,255,0.70),
    inset 1px 0  0 rgba(255,255,255,0.28),
    inset 0 -1px 0 rgba(0,0,0,0.08);
}}

/* Hero card — stronger glass, more prominent specular */
.card-hi {{
  background: rgba(255,255,255,0.10);
  border-color: rgba(255,255,255,0.24);
  box-shadow:
    0  2px  4px  rgba(0,0,0,0.30),
    0  8px  32px rgba(0,0,0,0.45),
    0 32px  64px rgba(0,0,0,0.32),
    0  0   80px  rgba(var(--hue-rgb),0.08),
    inset 0  1px 0 rgba(255,255,255,0.70),
    inset 1px 0  0 rgba(255,255,255,0.28),
    inset 0 -1px 0 rgba(0,0,0,0.10);
}}

.card-hi::before {{
  background: linear-gradient(
    135deg,
    rgba(255,255,255,0.22) 0%,
    rgba(255,255,255,0.07) 28%,
    transparent 52%,
    rgba(255,255,255,0.03) 100%
  );
}}

/* ── News view ─────────────────────────────── */
.news-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  padding: 0;
}}
.news-featured {{
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  border-radius: 12px;
  overflow: hidden;
  background: var(--surface);
  border: 1px solid var(--border);
  min-height: 180px;
}}
.news-featured-body {{
  padding: 24px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}}
.news-featured-image {{
  background: var(--surface-hi);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 64px;
  position: relative;
  overflow: hidden;
  min-height: 220px;
}}
.news-featured-image img {{
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}}
.news-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  cursor: pointer;
  transition: border-color 0.15s, transform 0.15s, box-shadow 0.15s;
  text-decoration: none;
  overflow: hidden;
}}
.news-card.news-card-has-thumb {{
  padding-top: 0;
}}
.news-thumb {{
  width: calc(100% + 32px);
  margin: 0 -16px 12px -16px;
  height: 150px;
  overflow: hidden;
  border-radius: 12px 12px 0 0;
  flex-shrink: 0;
}}
.news-thumb img {{
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}}
.news-card:hover {{
  border-color: var(--hue);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.2);
}}
.news-source-badge {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .06em;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: 20px;
  width: fit-content;
}}
.news-source-icon {{
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 900;
  color: #fff;
  flex-shrink: 0;
}}
.news-headline {{
  font-size: 14px;
  font-weight: 600;
  color: var(--text-1);
  line-height: 1.4;
}}
.news-featured .news-headline {{
  font-size: 20px;
  line-height: 1.3;
}}
.news-summary {{
  font-size: 12px;
  color: var(--text-3);
  line-height: 1.5;
  flex: 1;
}}
.news-read-link {{
  font-size: 11px;
  color: var(--hue);
  font-weight: 600;
  text-decoration: none;
  align-self: flex-end;
  margin-top: auto;
}}
.news-filter-bar {{
  display: flex;
  gap: 6px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  align-items: center;
}}
.news-filter-btn {{
  padding: 5px 14px;
  border-radius: 20px;
  border: 1px solid var(--border);
  background: var(--surface-hi);
  color: var(--text-2);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  letter-spacing: .04em;
}}
.news-filter-btn.active {{
  background: var(--hue);
  border-color: var(--hue);
  color: #fff;
}}
.news-filter-btn:hover:not(.active) {{
  border-color: var(--hue);
  color: var(--text-1);
}}
.news-refresh-info {{
  margin-left: auto;
  font-size: 10px;
  color: var(--text-3);
  display: flex;
  align-items: center;
  gap: 6px;
}}
.news-section-label {{
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--text-3);
  margin: 20px 0 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
}}

/* ── Tactical card — hue-tinted Liquid Glass ── */
.card-tactical {{
  border-color: rgba(var(--hue-rgb), 0.30);
  box-shadow:
    0  2px  4px  rgba(0,0,0,0.30),
    0  8px  24px rgba(0,0,0,0.40),
    0 24px  56px rgba(0,0,0,0.28),
    0  0   40px  rgba(var(--hue-rgb),0.06),
    inset 0  1px 0 rgba(255,255,255,0.55),
    inset 1px 0  0 rgba(255,255,255,0.18),
    inset 0 -1px 0 rgba(0,0,0,0.12);
}}

/* ── Needs-you card — gold-tinted Liquid Glass ── */
.card-needs-you {{
  border-color: rgba(245,158,11,0.30);
  box-shadow:
    0  2px  4px  rgba(0,0,0,0.30),
    0  8px  24px rgba(0,0,0,0.40),
    0 24px  56px rgba(0,0,0,0.28),
    0  0   40px  rgba(245,158,11,0.07),
    inset 0  1px 0 rgba(255,255,255,0.55),
    inset 1px 0  0 rgba(255,255,255,0.18),
    inset 0 -1px 0 rgba(0,0,0,0.12);
}}
.card-needs-you::after {{
  background: linear-gradient(
    180deg,
    rgba(245,158,11,0.06) 0%,
    transparent 100%
  );
}}
/* ── placeholder ── */
.card-needs-you-x {{
  display: none;
}}
.card-needs-you::after {{
  bottom: -1px; right: -1px;
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
  top: 0; left: 0; bottom: 0; right: auto;
  width: var(--nav-w);
  height: 100vh;
  z-index: 100;
  background: rgba(8,16,32,0.72);
  backdrop-filter: blur(56px) saturate(190%) brightness(0.96);
  -webkit-backdrop-filter: blur(56px) saturate(190%) brightness(0.96);
  border-right: 1px solid rgba(255,255,255,0.12);
  box-shadow:
    4px 0 32px rgba(0,0,0,0.50),
    inset -1px 0 0 rgba(255,255,255,0.12),
    inset  1px 0 0 rgba(255,255,255,0.04);
  display: flex;
  flex-direction: column;
  align-items: stretch;
  padding: 0;
  gap: 0;
}}

/* Hamburger button — hidden on desktop, visible on mobile */
.nav-hamburger {{
  display: none;
  position: fixed;
  top: 14px;
  left: 14px;
  z-index: 400;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.15);
  background: rgba(8,16,32,0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--text-1);
  font-size: 18px;
  line-height: 1;
  padding: 0;
}}
/* Drawer backdrop overlay */
#nav-drawer-overlay {{
  display: none;
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(0,0,0,0.55);
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
}}

.nav-wordmark {{
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.20em;
  color: var(--hue);
  white-space: nowrap;
  user-select: none;
  padding: 20px 16px 18px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  flex-shrink: 0;
  text-shadow: 0 0 20px rgba(59,158,255,0.6);
}}

.nav-tabs {{
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 2px;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 10px 8px;
  scrollbar-width: none;
}}
.nav-tabs::-webkit-scrollbar {{ display: none; }}

.nav-tab {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-2);
  cursor: pointer;
  border: none;
  background: transparent;
  white-space: nowrap;
  position: relative;
  user-select: none;
  text-align: left;
  width: 100%;
}}
.nav-tab:hover {{
  background: rgba(255,255,255,0.05);
  color: var(--text-1);
}}
.nav-tab.active {{
  background: var(--hue-dim);
  color: var(--hue);
  border-left: 2px solid var(--hue);
  padding-left: 10px;
}}
.nav-tab.active::after {{
  display: none;
}}

.nav-tab svg {{
  width: 13px; height: 13px;
  flex-shrink: 0;
}}

.nav-right {{
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  flex-shrink: 0;
  padding: 12px 12px 16px;
  border-top: 1px solid rgba(255,255,255,0.06);
}}

.agent-badge-pill {{
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  color: var(--hue);
  background: var(--hue-dim);
  border: 1px solid rgba(var(--hue-rgb),0.25);
  border-radius: 6px;
  padding: 4px 8px;
  white-space: nowrap;
  width: 100%;
  text-align: center;
  transition: background 0.45s ease, color 0.45s ease, border-color 0.45s ease;
  text-shadow: 0 0 10px rgba(var(--hue-rgb),0.5);
}}

/* ── Weather widget ── */
.nav-weather {{
  display: flex; align-items: center; gap: 5px;
  background: transparent; border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px; padding: 5px 8px;
  cursor: pointer; transition: background 0.2s;
  font-family: var(--font-mono); font-size: 10px; color: var(--text-2);
  white-space: nowrap; width: 100%;
}}
.nav-weather:hover {{ background: rgba(255,255,255,0.05); color: var(--text-1); }}
.nav-weather-icon {{ font-size: 13px; line-height: 1; }}
.nav-clock {{ font-family: var(--font-mono); font-size: 11px; color: var(--text-3); white-space: nowrap; letter-spacing: 0.05em; }}

/* ── Weather modal ── */
.weather-modal-overlay {{
  position: fixed; inset: 0; z-index: 3000;
  background: rgba(5,10,20,0.50);
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  display: flex; align-items: center; justify-content: center;
  animation: modal-overlay-in 0.25s ease;
}}
.weather-modal-overlay.hidden {{ display: none; animation: none; }}
.weather-modal {{
  position: relative; overflow: hidden;
  background: rgba(255,255,255,0.08);
  backdrop-filter: blur(60px) saturate(220%) brightness(1.10);
  -webkit-backdrop-filter: blur(60px) saturate(220%) brightness(1.10);
  border: 1px solid rgba(255,255,255,0.22);
  border-radius: 24px; padding: 28px;
  width: min(680px, 95vw); max-height: 90vh; overflow-y: auto;
  box-shadow:
    0  4px  8px  rgba(0,0,0,0.35),
    0 16px  48px rgba(0,0,0,0.50),
    0 48px  96px rgba(0,0,0,0.35),
    inset 0  1px 0 rgba(255,255,255,0.65),
    inset 1px 0  0 rgba(255,255,255,0.22),
    inset 0 -1px 0 rgba(0,0,0,0.15);
  animation: modal-in 0.38s cubic-bezier(0.34,1.56,0.64,1);
}}
.weather-modal::before {{
  content: '';
  position: absolute; inset: 0; border-radius: 23px; pointer-events: none; z-index: 0;
  background: linear-gradient(
    135deg,
    rgba(255,255,255,0.18) 0%,
    rgba(255,255,255,0.05) 30%,
    transparent 55%,
    rgba(255,255,255,0.02) 100%
  );
}}
.weather-modal > * {{ position: relative; z-index: 1; }}
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

/* ── Who Are You — identity landing overlay ──────────────────────── */
#wau-overlay {{
  position: fixed; inset: 0; z-index: 9000;
  background: rgba(5,10,20,0.82);
  backdrop-filter: blur(28px) saturate(160%);
  -webkit-backdrop-filter: blur(28px) saturate(160%);
  display: flex; align-items: center; justify-content: center;
  animation: modal-overlay-in 0.35s ease;
}}
#wau-overlay.hidden {{ display: none !important; animation: none; }}
#wau-box {{
  position: relative; overflow: hidden;
  background: rgba(255,255,255,0.07);
  backdrop-filter: blur(60px) saturate(220%) brightness(1.08);
  -webkit-backdrop-filter: blur(60px) saturate(220%) brightness(1.08);
  border: 1px solid rgba(255,255,255,0.18);
  border-radius: 28px; padding: 40px 36px 32px;
  width: min(560px, 95vw);
  box-shadow:
    0  8px  24px rgba(0,0,0,0.45),
    0 32px  80px rgba(0,0,0,0.55),
    inset 0 1px 0 rgba(255,255,255,0.55),
    inset 1px 0 0 rgba(255,255,255,0.18);
  animation: modal-in 0.42s cubic-bezier(0.34,1.56,0.64,1);
  text-align: center;
}}
#wau-box::before {{
  content: ''; position: absolute; inset: 0; border-radius: 27px;
  pointer-events: none; z-index: 0;
  background: linear-gradient(135deg,
    rgba(255,255,255,0.15) 0%, rgba(255,255,255,0.04) 35%, transparent 60%);
}}
#wau-box > * {{ position: relative; z-index: 1; }}
.wau-logo {{
  font-size: 42px; line-height: 1; margin-bottom: 10px;
}}
.wau-title {{
  font-size: 22px; font-weight: 700; color: var(--text-1);
  letter-spacing: -0.02em; margin-bottom: 4px;
}}
.wau-subtitle {{
  font-size: 13px; color: var(--text-3); margin-bottom: 28px;
}}
.wau-grid {{
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 14px; margin-bottom: 20px;
}}
.wau-card {{
  background: rgba(255,255,255,0.06);
  border: 1.5px solid rgba(255,255,255,0.12);
  border-radius: 16px; padding: 20px 14px 18px;
  cursor: pointer; transition: all 0.18s;
  display: flex; flex-direction: column;
  align-items: center; gap: 8px;
  position: relative; overflow: hidden;
}}
.wau-card:hover {{
  background: rgba(0,212,255,0.10);
  border-color: rgba(0,212,255,0.45);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,212,255,0.15);
}}
.wau-card:active {{ transform: translateY(0); }}
.wau-card-avatar {{
  font-size: 36px; line-height: 1;
}}
.wau-card-name {{
  font-size: 15px; font-weight: 700; color: var(--text-1);
}}
.wau-card-role {{
  font-size: 11px; color: var(--text-3); margin-top: -4px;
}}
.wau-card-badge {{
  position: absolute; top: 10px; right: 10px;
  font-size: 9px; font-weight: 700; letter-spacing: 0.06em;
  padding: 2px 6px; border-radius: 4px;
  background: rgba(0,212,255,0.15); color: #00D4FF;
  border: 1px solid rgba(0,212,255,0.3);
}}
.wau-guest {{
  font-size: 12px; color: var(--text-3); cursor: pointer;
  padding: 6px; border-radius: 8px; transition: color 0.15s;
  background: none; border: none; width: 100%;
}}
.wau-guest:hover {{ color: var(--text-2); }}
.wau-status {{
  font-size: 12px; color: var(--text-3); margin-top: 12px;
  min-height: 16px; transition: color 0.2s;
}}
.weather-hero {{
  display: flex; align-items: center; gap: 20px; margin-bottom: 24px;
  padding: 20px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.18);
  border-radius: 14px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.35);
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
.settings-btn:hover {{ background: var(--surface-hi); color: var(--text-1); }}

/* ── Domain identity strip — left edge of sidebar → right border accent ── */
.domain-strip {{
  position: fixed;
  top: 0; left: calc(var(--nav-w) - 1px); right: auto; bottom: 0;
  width: 2px;
  height: 100vh;
  background: linear-gradient(
    180deg,
    transparent 0%,
    rgba(var(--hue-rgb),0.6) 20%,
    rgba(var(--hue-rgb),0.6) 80%,
    transparent 100%
  );
  z-index: 99;
  transition: background 0.45s ease;
}}

/* ═══════════════════════════════════════════════════════════════════
   MAIN CONTENT
═══════════════════════════════════════════════════════════════════ */
.main {{
  position: relative;
  z-index: 1;
  padding-top: 24px;
  padding-bottom: calc(var(--bar-h) + 24px);
  padding-left: calc(var(--nav-w) + 24px);
  padding-right: 24px;
  max-width: none;
  margin: 0;
}}

/* ── View sections ── */
.view {{ display: none; }}
.view.active {{ display: block; }}

/* ── View header ── */
.view-header {{
  margin-bottom: 20px;
}}
.view-title {{
  font-size: 18px;
  font-weight: 700;
  color: var(--text-1);
  letter-spacing: 0.04em;
  text-transform: uppercase;
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

/* ── Sam Wilson Check-In Banner ─────────────────────────────────── */
.sam-checkin-banner {{
  position: relative; overflow: hidden;
  border-radius: 16px; padding: 18px 20px 16px;
  background: rgba(255,255,255,0.07);
  backdrop-filter: blur(32px) saturate(180%);
  -webkit-backdrop-filter: blur(32px) saturate(180%);
  border: 1px solid rgba(255,255,255,0.16);
  box-shadow: 0 4px 20px rgba(0,0,0,0.30),
    inset 0 1px 0 rgba(255,255,255,0.45), inset 1px 0 0 rgba(255,255,255,0.12);
  margin-bottom: 16px;
}}
.sam-checkin-banner::before {{
  content: ''; position: absolute; inset: 0; border-radius: 15px; pointer-events: none;
  background: linear-gradient(135deg, rgba(255,255,255,0.14) 0%, transparent 50%);
}}
.sam-checkin-banner > * {{ position: relative; z-index: 1; }}
.sam-checkin-mode-chip {{
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 9px; font-weight: 800; letter-spacing: .10em; text-transform: uppercase;
  padding: 3px 9px; border-radius: 20px; margin-bottom: 10px; font-family: var(--font-mono);
}}
.sam-checkin-mode-chip.morning {{ background: rgba(245,158,11,0.15); color: var(--amber); border: 1px solid rgba(245,158,11,0.30); }}
.sam-checkin-mode-chip.evening {{ background: rgba(99,102,241,0.15); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.30); }}
.sam-checkin-greeting {{ font-size: 13px; font-weight: 600; color: var(--blue); font-style: italic; margin-bottom: 12px; line-height: 1.4; }}
.sam-checkin-meta {{ display: flex; align-items: center; gap: 14px; flex-wrap: wrap; margin-bottom: 12px; }}
.sam-checkin-stat {{ display: flex; flex-direction: column; align-items: center; min-width: 48px; }}
.sam-checkin-stat-val {{ font-size: 18px; font-weight: 700; font-family: var(--font-mono); color: var(--text-1); line-height: 1; }}
.sam-checkin-stat-lbl {{ font-size: 8px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--text-3); margin-top: 2px; }}
.sam-checkin-divider {{ width: 1px; height: 28px; background: rgba(255,255,255,0.12); }}
.sam-checkin-streak {{ font-size: 12px; font-weight: 700; color: var(--amber); display: flex; align-items: center; gap: 4px; }}
.sam-checkin-focus {{ background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.10); border-radius: 10px; padding: 10px 12px; margin-bottom: 10px; }}
.sam-checkin-focus-label {{ font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: var(--text-3); margin-bottom: 4px; }}
.sam-checkin-focus-primary {{ font-size: 13px; font-weight: 700; color: var(--text-1); margin-bottom: 2px; }}
.sam-checkin-focus-detail {{ font-size: 11px; color: var(--text-3); line-height: 1.4; }}
.sam-checkin-watch {{ font-size: 11px; color: var(--amber); background: rgba(217,119,6,0.10); border: 1px solid rgba(217,119,6,0.25); border-radius: 8px; padding: 6px 10px; margin-bottom: 10px; }}
.sam-checkin-actions {{ display: flex; gap: 8px; margin-top: 4px; }}
.sam-evening-list {{ display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }}
.sam-evening-item {{ display: flex; align-items: flex-start; gap: 10px; padding: 8px 10px; border-radius: 8px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); cursor: pointer; transition: background 0.2s; }}
.sam-evening-item:hover {{ background: rgba(255,255,255,0.09); }}
.sam-evening-item.checked {{ border-color: rgba(34,197,94,0.35); background: rgba(34,197,94,0.07); }}
.sam-evening-item input[type=checkbox] {{ margin-top:1px; cursor:pointer; accent-color:#22c55e; flex-shrink:0; }}
.sam-evening-item-icon {{ font-size: 15px; line-height: 1; }}
.sam-evening-item-label {{ font-size: 12px; color: var(--text-2); font-weight: 500; flex: 1; }}
.sam-evening-notes {{ width:100%; box-sizing:border-box; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); border-radius:8px; padding:8px 10px; font-size:12px; color:var(--text-1); resize:none; outline:none; font-family:var(--font-body); transition:border-color 0.2s; }}
.sam-evening-notes:focus {{ border-color: rgba(99,102,241,0.45); }}
.sam-checkin-response {{ margin-top:12px; padding:12px 14px; background:rgba(99,102,241,0.10); border:1px solid rgba(99,102,241,0.25); border-radius:10px; display:none; }}
.sam-checkin-response.visible {{ display:block; }}
.sam-checkin-response-text {{ font-size:12px; color:var(--text-2); font-style:italic; line-height:1.6; }}
.sam-checkin-response-streak {{ font-size:10px; color:var(--amber); font-weight:700; margin-top:6px; }}

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

/* ── Daily Health Score ── */
.health-score-panel {{
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 20px;
}}
.health-score-ring {{
  flex-shrink: 0;
  position: relative;
  width: 72px;
  height: 72px;
}}
.health-score-sparkline {{
  flex: 1;
  min-width: 0;
}}
.sparkline-svg {{
  width: 100%;
  height: 44px;
  overflow: visible;
}}
.score-domain-bar {{
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}}
.score-domain-label {{
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .07em;
  color: var(--text-3);
  width: 68px;
  flex-shrink: 0;
}}
.score-domain-track {{
  flex: 1;
  height: 4px;
  background: rgba(255,255,255,0.08);
  border-radius: 2px;
  overflow: hidden;
}}
.score-domain-fill {{
  height: 100%;
  border-radius: 2px;
  transition: width 0.6s ease;
}}
.score-domain-pts {{
  font-size: 9px;
  font-family: var(--font-mono);
  color: var(--text-3);
  width: 28px;
  text-align: right;
  flex-shrink: 0;
}}

.stat-tile {{
  padding: 16px 18px;
  cursor: pointer;
}}
.stat-label {{
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-2);
  margin-bottom: 6px;
}}
.stat-value {{
  font-family: var(--font-mono);
  font-size: 28px;
  font-weight: 500;
  color: var(--text-1);
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
  color: var(--text-2);
  margin-top: 4px;
}}

/* ── Journey View ────────────────────────────────────────────────── */
.journey-day-header {{
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: rgba(255,255,255,0.35);
  text-transform: uppercase;
  padding: 4px 0;
  margin-top: 8px;
}}
.journey-event {{
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 14px;
  background: rgba(255,255,255,0.04);
  border-radius: 10px;
  border-left: 2px solid rgba(255,255,255,0.1);
}}
.journey-event-icon {{ font-size: 18px; flex-shrink: 0; margin-top: 1px; }}
.journey-event-body {{ flex: 1; min-width: 0; }}
.journey-event-title {{ font-size: 13px; color: rgba(255,255,255,0.85); font-weight: 500; }}
.journey-event-time {{ font-size: 11px; color: rgba(255,255,255,0.35); margin-top: 2px; }}
.journey-event-payload {{ font-size: 12px; color: rgba(255,255,255,0.5); margin-top: 3px; font-style: italic; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 400px; }}

/* ── Adaptive Overview Layout ───────────────────────────────────── */
.overview-mode-bar {{
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}}
.mode-pill {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .05em;
  text-transform: uppercase;
  font-family: var(--font-mono);
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.10);
  color: var(--text-2);
  cursor: pointer;
  transition: background 0.2s, color 0.2s, border-color 0.2s, box-shadow 0.2s;
}}
.mode-pill:hover {{
  background: rgba(255,255,255,0.09);
  color: var(--text-1);
}}
.mode-pill.active {{
  background: var(--hue-dim);
  border-color: var(--hue);
  color: var(--hue);
  box-shadow: 0 0 0 3px rgba(var(--hue-rgb, 99,102,241), .15);
}}
.mode-pill.manual-override {{
  border-color: rgba(201,168,76,.6);
  box-shadow: 0 0 0 2px rgba(201,168,76,.15);
}}
.mode-auto-chip {{
  font-size: 9px;
  font-weight: 700;
  letter-spacing: .12em;
  font-family: var(--font-mono);
  text-transform: uppercase;
  color: var(--success);
  background: rgba(16,185,129,.1);
  border: 1px solid rgba(16,185,129,.25);
  border-radius: 10px;
  padding: 2px 8px;
}}
.mode-auto-chip.override {{
  color: #a07a10;
  background: rgba(201,168,76,.1);
  border-color: rgba(201,168,76,.3);
}}
.mode-clock {{
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-3);
  letter-spacing: .04em;
}}
.overview-alert-banner {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-radius: 10px;
  margin-bottom: 14px;
  font-size: 13px;
  font-weight: 500;
  transform: translateY(-10px);
  opacity: 0;
  transition: transform 0.3s ease, opacity 0.3s ease;
  border: 1px solid transparent;
  pointer-events: none;
}}
.overview-alert-banner.visible {{
  transform: translateY(0);
  opacity: 1;
  pointer-events: auto;
}}
.overview-alert-banner.level-amber {{
  background: rgba(201,168,76,.1);
  border-color: rgba(201,168,76,.4);
  color: #7d5f0a;
}}
.overview-alert-banner.level-red {{
  background: rgba(196,30,58,.08);
  border-color: rgba(196,30,58,.35);
  color: #9b1c1c;
}}
.overview-alert-banner.level-blue {{
  background: rgba(59,130,246,.08);
  border-color: rgba(59,130,246,.35);
  color: #1d4ed8;
}}
.alert-banner-msg {{ flex: 1; }}
.alert-banner-action {{
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid currentColor;
  background: transparent;
  color: inherit;
  font-family: var(--font-mono);
  transition: background .15s;
}}
.alert-banner-action:hover {{ background: rgba(255,255,255,.2); }}
.alert-banner-dismiss {{
  background: none;
  border: none;
  cursor: pointer;
  color: inherit;
  font-size: 15px;
  opacity: .55;
  padding: 0 4px;
  line-height: 1;
}}
.overview-hero-zone {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
  min-height: 200px;
}}
/* ── Mobile nav drawer ── */
@media (max-width: 768px) {{
  .nav-hamburger {{ display: flex; }}

  .nav-bar {{
    transform: translateX(-100%);
    transition: transform 0.28s cubic-bezier(0.4,0,0.2,1);
    z-index: 300;
    width: 220px;
    box-shadow: none;
  }}
  .nav-bar.mobile-open {{
    transform: translateX(0);
    box-shadow: 4px 0 40px rgba(0,0,0,0.70);
  }}
  #nav-drawer-overlay.active {{ display: block; }}

  .domain-strip {{ left: 0 !important; }}

  .main {{
    padding-left: 16px !important;
    padding-right: 16px !important;
    padding-top: 60px !important;   /* clear the hamburger button */
  }}

  /* Mode pills: scroll horizontally, don't wrap */
  .overview-mode-bar {{
    overflow-x: auto;
    flex-wrap: nowrap;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    padding-bottom: 2px;
  }}
  .overview-mode-bar::-webkit-scrollbar {{ display: none; }}
  .mode-pill {{
    flex-shrink: 0;
    font-size: 10px;
    padding: 6px 12px;
    white-space: nowrap;
  }}

  /* Stats strip: 2-col on mobile */
  .stats-strip {{ grid-template-columns: repeat(2,1fr) !important; }}

  /* Command bar: full width on mobile (nav is hidden) */
  .command-bar {{
    left: 0 !important;
    padding: 8px 12px 16px;
  }}

  /* Mic button: larger tap target on mobile */
  .cmd-mic {{
    width: 40px !important;
    height: 40px !important;
    min-width: 40px !important;
    flex-shrink: 0;
  }}

  #nav-close-btn {{ display: block !important; }}
}}
@media(max-width: 768px) {{
  .overview-hero-zone {{ grid-template-columns: 1fr; }}
}}
.overview-priority-strip {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 18px;
}}
@media(max-width: 768px) {{
  .overview-priority-strip {{ grid-template-columns: repeat(2, 1fr); }}
}}
@media(max-width: 480px) {{
  .overview-priority-strip {{ grid-template-columns: 1fr; }}
}}
.overview-ambient-row {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
}}
.ambient-tile {{
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 14px;
  border-radius: 12px;
  background: rgba(255,255,255,0.07);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border: 1px solid rgba(255,255,255,0.16);
  box-shadow:
    0 2px 8px rgba(0,0,0,0.25),
    inset 0  1px 0 rgba(255,255,255,0.40),
    inset 1px 0  0 rgba(255,255,255,0.12);
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-2);
  text-transform: uppercase;
  letter-spacing: .05em;
  font-family: var(--font-mono);
  transition: background 0.25s ease, transform 0.3s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.25s ease, color 0.2s;
  white-space: nowrap;
}}
.ambient-tile:hover {{
  background: rgba(255,255,255,0.12);
  color: var(--text-1);
  transform: translateY(-2px);
  box-shadow:
    0 4px 16px rgba(0,0,0,0.30),
    inset 0  1px 0 rgba(255,255,255,0.60),
    inset 1px 0  0 rgba(255,255,255,0.20);
}}
.ambient-badge {{
  font-size: 10px;
  background: var(--hue-dim);
  color: var(--hue);
  border-radius: 10px;
  padding: 1px 6px;
  font-weight: 700;
}}
.layout-card {{
  transition: opacity .3s ease, transform .3s ease,
              box-shadow .45s ease, background-color .45s ease,
              border-color .45s ease;
}}
.layout-card.entering {{
  opacity: 0;
  transform: translateY(8px);
}}
@keyframes pulse-amber-ring {{
  0%,100% {{ box-shadow: 0 0 0 0 rgba(201,168,76,0); }}
  50%      {{ box-shadow: 0 0 0 5px rgba(201,168,76,.35); }}
}}
@keyframes pulse-red-ring {{
  0%,100% {{ box-shadow: 0 0 0 0 rgba(196,30,58,0); }}
  50%      {{ box-shadow: 0 0 0 5px rgba(196,30,58,.35); }}
}}
@keyframes pulse-blue-ring {{
  0%,100% {{ box-shadow: 0 0 0 0 rgba(59,130,246,0); }}
  50%      {{ box-shadow: 0 0 0 5px rgba(59,130,246,.3); }}
}}
.layout-card.alert-pulse-amber {{ animation: pulse-amber-ring 2.5s ease-in-out infinite; }}
.layout-card.alert-pulse-red   {{ animation: pulse-red-ring   2s   ease-in-out infinite; }}
.layout-card.alert-pulse-blue  {{ animation: pulse-blue-ring  2s   ease-in-out infinite; }}

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
  color: var(--text-1);
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
.pill-navy {{ background: rgba(59,158,255,0.10); color: var(--hue); border: 1px solid rgba(59,158,255,0.20); }}
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
.btn-outline:hover {{ color: var(--text-1); background: rgba(255,255,255,0.08); }}
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
  color: var(--text-1);
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

/* ── Faith Agents ─────────────────────────────────────────────────────── */
.faith-roster {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 8px;
}}
.faith-agent-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: border-color .18s, transform .15s, box-shadow .18s;
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(18px);
}}
.faith-agent-card::before {{
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: var(--agent-color, var(--hue));
  border-radius: 12px 12px 0 0;
}}
.faith-agent-card:hover {{
  border-color: var(--agent-color, var(--hue));
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,.35);
}}
.faith-agent-card.active {{
  border-color: var(--agent-color, var(--hue));
  box-shadow: 0 0 0 1px var(--agent-color, var(--hue)), 0 8px 24px rgba(0,0,0,.4);
}}
.faith-agent-avatar {{
  width: 44px; height: 44px;
  border-radius: 50%;
  background: var(--agent-color, var(--hue));
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; color: #000;
  margin-bottom: 10px;
  opacity: .9;
}}
.faith-agent-name {{
  font-size: 14px; font-weight: 700; color: var(--text-1);
  margin-bottom: 2px;
}}
.faith-agent-title {{
  font-size: 10px; color: var(--agent-color, var(--hue));
  text-transform: uppercase; letter-spacing: .06em;
  margin-bottom: 6px;
}}
.faith-agent-desc {{
  font-size: 11px; color: var(--text-3); line-height: 1.45;
}}

/* Daily Word banner */
.faith-daily-word {{
  padding: 16px 20px;
  border-left: 3px solid var(--hue);
}}
.faith-dw-header {{
  display: flex; align-items: center; gap: 10px; margin-bottom: 8px;
}}
.faith-dw-agent {{
  font-size: 12px; font-weight: 700; color: var(--text-1);
}}
.faith-dw-tag {{
  font-size: 10px; color: var(--text-3); text-transform: uppercase; letter-spacing: .06em;
  background: rgba(255,255,255,.07); padding: 2px 8px; border-radius: 20px;
}}
.faith-dw-body {{
  font-size: 14px; color: var(--text-2); line-height: 1.6; margin-bottom: 6px;
}}
.faith-dw-passage {{
  font-size: 11px; color: var(--text-3); font-style: italic;
}}

/* Faith Chat Panel */
.faith-chat-panel {{
  padding: 0; overflow: hidden;
}}
.faith-chat-header {{
  display: flex; align-items: center; gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
}}
.faith-chat-avatar {{
  width: 38px; height: 38px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; color: #000; flex-shrink: 0;
}}
.faith-chat-name {{
  font-size: 14px; font-weight: 700; color: var(--text-1);
}}
.faith-chat-domain {{
  font-size: 11px; color: var(--text-3);
}}
.faith-chat-passage-row {{
  padding: 10px 18px;
  border-bottom: 1px solid var(--border);
}}
.faith-chat-passage-input {{
  width: 100%; background: rgba(255,255,255,.04);
  border: 1px solid var(--border); border-radius: 8px;
  color: var(--text-2); font-size: 12px; padding: 6px 10px;
  outline: none;
}}
.faith-chat-passage-input:focus {{
  border-color: var(--hue);
}}
.faith-chat-messages {{
  height: 340px; overflow-y: auto;
  padding: 16px 18px;
  display: flex; flex-direction: column; gap: 12px;
}}
.faith-chat-bubble {{
  max-width: 82%; padding: 10px 14px; border-radius: 12px;
  font-size: 13px; line-height: 1.55; white-space: pre-wrap;
}}
.faith-chat-bubble.user {{
  align-self: flex-end;
  background: var(--hue);
  color: #fff; border-radius: 12px 12px 2px 12px;
}}
.faith-chat-bubble.agent {{
  align-self: flex-start;
  background: rgba(255,255,255,.08);
  color: var(--text-1); border-radius: 2px 12px 12px 12px;
  border: 1px solid var(--border);
}}
.faith-chat-bubble.agent strong {{ color: var(--text-1); }}
.faith-chat-bubble.agent em {{ color: var(--text-3); }}
.faith-chat-input-row {{
  display: flex; gap: 8px; padding: 10px 18px;
  border-top: 1px solid var(--border);
}}
.faith-chat-textarea {{
  flex: 1; background: rgba(255,255,255,.04);
  border: 1px solid var(--border); border-radius: 8px;
  color: var(--text-1); font-size: 13px; padding: 8px 12px;
  resize: none; outline: none; font-family: inherit;
}}
.faith-chat-textarea:focus {{ border-color: var(--hue); }}
.faith-send-btn {{ align-self: flex-end; height: 38px; padding: 0 16px; }}
.faith-typing {{
  display: flex; gap: 4px; align-items: center; padding: 10px 14px;
  background: rgba(255,255,255,.08); border-radius: 2px 12px 12px 12px;
  width: fit-content; border: 1px solid var(--border);
}}
.faith-typing-dot {{
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--text-3);
  animation: faithDotPulse 1.2s ease-in-out infinite;
}}
.faith-typing-dot:nth-child(2) {{ animation-delay: .2s; }}
.faith-typing-dot:nth-child(3) {{ animation-delay: .4s; }}
@keyframes faithDotPulse {{
  0%,80%,100% {{ opacity:.25; transform:scale(.8); }}
  40% {{ opacity:1; transform:scale(1); }}
}}

/* ═══════════════════════════════════════════════════════════════════
   CHRONICLE — ENTRY CARDS & SIDEBAR
═══════════════════════════════════════════════════════════════════ */
.chr-entry-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 10px;
  position: relative;
  overflow: hidden;
  cursor: default;
  transition: border-color 0.2s, box-shadow 0.2s;
}}
.chr-entry-card:hover {{
  border-color: rgba(var(--hue-rgb), 0.30);
  box-shadow: 0 4px 16px rgba(0,0,0,0.25);
}}
.chr-entry-type-bar {{
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  border-radius: 12px 0 0 12px;
}}
.chr-type-insight  .chr-entry-type-bar {{ background: var(--hue); }}
.chr-type-prayer   .chr-entry-type-bar {{ background: #8B5CF6; }}
.chr-type-study    .chr-entry-type-bar {{ background: #10B981; }}
.chr-type-reflection .chr-entry-type-bar {{ background: #F59E0B; }}
.chr-type-note     .chr-entry-type-bar {{ background: #64748b; }}
.chr-entry-header {{
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 5px;
  padding-left: 10px;
}}
.chr-entry-type-pill {{
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}}
.chr-type-insight  .chr-entry-type-pill {{ background: rgba(59,158,255,0.15); color: var(--hue); }}
.chr-type-prayer   .chr-entry-type-pill {{ background: rgba(139,92,246,0.15); color: #8B5CF6; }}
.chr-type-study    .chr-entry-type-pill {{ background: rgba(16,185,129,0.15); color: #10B981; }}
.chr-type-reflection .chr-entry-type-pill {{ background: rgba(245,158,11,0.15); color: #F59E0B; }}
.chr-type-note     .chr-entry-type-pill {{ background: rgba(100,116,139,0.15); color: #94a3b8; }}
.chr-entry-title {{
  font-size: 13px;
  font-weight: 600;
  color: var(--text-1);
  flex: 1;
}}
.chr-entry-date {{
  font-size: 10px;
  color: var(--text-3);
  flex-shrink: 0;
}}
.chr-entry-body {{
  font-size: 12px;
  color: var(--text-2);
  line-height: 1.55;
  padding-left: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}}
.chr-entry-footer {{
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding-left: 10px;
  flex-wrap: wrap;
}}
.chr-passage {{
  font-size: 10px;
  color: var(--text-3);
  font-style: italic;
}}
.chr-theme-tag {{
  font-size: 9px;
  background: rgba(255,255,255,0.06);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1px 5px;
  color: var(--text-3);
}}
/* Prayer list items */
.chr-prayer-item {{
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
}}
.chr-prayer-item:last-child {{ border-bottom: none; }}
.chr-prayer-cat {{
  font-size: 9px;
  font-weight: 700;
  letter-spacing: .06em;
  text-transform: uppercase;
  padding: 2px 5px;
  border-radius: 3px;
  flex-shrink: 0;
  margin-top: 1px;
}}
.chr-cat-people  {{ background: rgba(59,158,255,0.12); color: var(--hue); }}
.chr-cat-needs   {{ background: rgba(245,158,11,0.12); color: #F59E0B; }}
.chr-cat-praise  {{ background: rgba(16,185,129,0.12); color: #10B981; }}
.chr-cat-world   {{ background: rgba(139,92,246,0.12); color: #8B5CF6; }}
.chr-prayer-text {{ font-size: 12px; color: var(--text-2); flex: 1; line-height: 1.4; }}
.chr-prayer-count {{ font-size: 10px; color: var(--text-3); flex-shrink: 0; margin-top: 1px; }}
.chr-prayer-answered {{ opacity: 0.45; text-decoration: line-through; }}
/* Rhythm items */
.chr-rhythm-item {{
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
}}
.chr-rhythm-item:last-child {{ border-bottom: none; }}
.chr-rhythm-title {{
  font-size: 12px;
  font-weight: 600;
  color: var(--text-1);
  margin-bottom: 3px;
  display: flex;
  align-items: center;
  gap: 6px;
}}
.chr-rhythm-cadence {{
  font-size: 9px;
  background: rgba(255,255,255,0.06);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 1px 5px;
  color: var(--text-3);
  text-transform: uppercase;
  letter-spacing: .05em;
}}
.chr-rhythm-focus {{
  font-size: 11px;
  color: var(--text-3);
  font-style: italic;
}}
.chr-rhythm-passage {{
  font-size: 10px;
  color: var(--hue);
  margin-top: 3px;
  opacity: 0.8;
}}
/* Chronicle modals */
.chr-modal-backdrop {{
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.65);
  backdrop-filter: blur(6px);
  z-index: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  animation: fadeIn 0.15s ease;
}}
@keyframes fadeIn {{ from {{ opacity:0; }} to {{ opacity:1; }} }}
.chr-modal {{
  background: rgba(10,18,34,0.96);
  backdrop-filter: blur(32px) saturate(160%);
  border: 1px solid rgba(255,255,255,0.13);
  border-radius: 16px;
  box-shadow: 0 8px 48px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.04), inset 0 1px 0 rgba(255,255,255,0.10);
  width: 100%;
  max-width: 680px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideUp 0.18s ease;
}}
.chr-modal.chr-modal-wide {{ max-width: 820px; }}
@keyframes slideUp {{ from {{ transform: translateY(12px); opacity:0; }} to {{ transform: translateY(0); opacity:1; }} }}
.chr-modal-header {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 20px 14px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  flex-shrink: 0;
}}
.chr-modal-title {{
  font-size: 15px;
  font-weight: 600;
  color: var(--text-1);
  flex: 1;
}}
.chr-modal-close {{
  width: 28px; height: 28px;
  border-radius: 6px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.08);
  color: var(--text-3);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
  transition: background 0.15s, color 0.15s;
}}
.chr-modal-close:hover {{ background: rgba(255,255,255,0.12); color: var(--text-1); }}
.chr-modal-body {{
  flex: 1;
  overflow-y: auto;
  padding: 18px 20px;
}}
.chr-modal-footer {{
  padding: 12px 20px;
  border-top: 1px solid rgba(255,255,255,0.08);
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
}}
/* Bible study modal tabs */
/* Faith agent selector strip (replaces old 4-tab study mode) */
.chr-agent-strip {{
  display: flex;
  gap: 6px;
  padding: 10px 18px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  overflow-x: auto;
  flex-shrink: 0;
  scrollbar-width: none;
}}
.chr-agent-strip::-webkit-scrollbar {{ display: none; }}
.chr-agent-pill {{
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px 5px 5px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.09);
  color: var(--text-3);
  transition: background 0.15s, color 0.15s, border-color 0.15s;
  flex-shrink: 0;
}}
.chr-agent-pill:hover {{
  background: rgba(255,255,255,0.09);
  color: var(--text-2);
  border-color: var(--pill-color, var(--hue));
}}
.chr-agent-pill.active {{
  background: rgba(255,255,255,0.10);
  color: var(--text-1);
  border-color: var(--pill-color, var(--hue));
  box-shadow: 0 0 0 1px var(--pill-color, var(--hue));
}}
.chr-agent-pill-av {{
  width: 20px; height: 20px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 8px; font-weight: 800; color: #000;
  flex-shrink: 0;
}}
.chr-agent-label {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  border-left: 3px solid var(--hue);
  background: rgba(255,255,255,0.03);
  transition: border-color 0.2s;
}}
/* ── Quick Capture ──────────────────────────────────────────────────────── */
.cmd-chip-faith {{
  border-color: rgba(139,92,246,0.35);
  color: rgba(139,92,246,0.9);
}}
.cmd-chip-faith:hover {{
  background: rgba(139,92,246,0.12);
  border-color: rgba(139,92,246,0.6);
  color: #a78bfa;
}}
.chr-capture-card {{
  padding: 14px 16px;
  margin-bottom: 18px;
}}
.chr-capture-type-row {{
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}}
.chr-capture-type {{
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.10);
  color: var(--text-3);
  transition: all .15s;
}}
.chr-capture-type:hover {{
  color: var(--text-2);
  background: rgba(255,255,255,0.09);
}}
.chr-capture-type.active {{
  background: rgba(var(--hue-rgb),0.15);
  border-color: var(--hue);
  color: var(--hue);
}}
.chr-capture-input-row {{
  display: flex;
  gap: 8px;
  align-items: center;
}}
.chr-capture-input {{
  flex: 2;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-1);
  font-size: 13px;
  padding: 8px 12px;
  outline: none;
  font-family: inherit;
}}
.chr-capture-input:focus {{ border-color: var(--hue); }}
.chr-capture-passage {{
  flex: 1;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-2);
  font-size: 12px;
  padding: 8px 10px;
  outline: none;
  font-family: inherit;
  min-width: 0;
}}
.chr-capture-passage:focus {{ border-color: var(--hue); }}

/* Quick capture modal (from command bar) */
.qc-modal-backdrop {{
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(6px);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
}}
.qc-modal {{
  background: rgba(10,18,32,0.97);
  border: 1px solid rgba(255,255,255,0.14);
  border-radius: 16px;
  padding: 24px;
  width: min(480px,90vw);
  box-shadow: 0 24px 60px rgba(0,0,0,.6);
}}
.qc-modal-title {{
  font-size: 13px;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 14px;
  letter-spacing: .04em;
  text-transform: uppercase;
}}
.qc-modal-textarea {{
  width: 100%;
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--text-1);
  font-size: 14px;
  padding: 12px 14px;
  resize: none;
  outline: none;
  font-family: inherit;
  line-height: 1.55;
  margin-bottom: 10px;
}}
.qc-modal-textarea:focus {{ border-color: var(--hue); }}
.qc-passage-input {{
  width: 100%;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-2);
  font-size: 12px;
  padding: 7px 10px;
  outline: none;
  font-family: inherit;
  margin-bottom: 14px;
}}
.qc-passage-input:focus {{ border-color: var(--hue); }}
.qc-footer {{
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}}

/* Spiritual context in Morning Brief */
.brief-spiritual-ctx {{
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid rgba(255,255,255,0.07);
}}
.brief-spiritual-row {{
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--text-3);
}}
.brief-spiritual-icon {{
  flex-shrink: 0;
  width: 16px;
  text-align: center;
  font-size: 12px;
  margin-top: 1px;
}}
.brief-spiritual-text {{
  flex: 1;
  color: var(--text-2);
  line-height: 1.45;
}}
.brief-chr-btn {{
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 12px;
  background: rgba(var(--hue-rgb),0.12);
  border: 1px solid rgba(var(--hue-rgb),0.25);
  color: var(--hue);
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: background .15s;
}}
.brief-chr-btn:hover {{ background: rgba(var(--hue-rgb),0.22); }}

/* Pattern insights in Faith/Chronicle */
.pattern-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px,1fr));
  gap: 10px;
  margin-top: 12px;
}}
.pattern-tile {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px;
  text-align: center;
}}
.pattern-tile-num {{
  font-size: 22px;
  font-weight: 700;
  color: var(--hue);
  margin-bottom: 2px;
}}
.pattern-tile-lbl {{
  font-size: 10px;
  color: var(--text-3);
  text-transform: uppercase;
  letter-spacing: .06em;
}}
.pattern-theme-chip {{
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  background: rgba(var(--hue-rgb),0.10);
  border: 1px solid rgba(var(--hue-rgb),0.20);
  color: var(--hue);
  margin: 3px;
}}
/* Chat area */
.chr-chat-messages {{
  flex: 1;
  overflow-y: auto;
  padding: 14px 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 200px;
  max-height: 340px;
}}
.chr-chat-msg {{
  display: flex;
  gap: 10px;
  align-items: flex-start;
}}
.chr-chat-msg.user {{ flex-direction: row-reverse; }}
.chr-chat-avatar {{
  width: 28px; height: 28px;
  border-radius: 50%;
  background: var(--surface-hi);
  border: 1px solid var(--border);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
}}
.chr-chat-bubble {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 10px 13px;
  font-size: 12px;
  line-height: 1.55;
  color: var(--text-2);
  max-width: 85%;
}}
.chr-chat-bubble.user {{
  background: rgba(var(--hue-rgb),0.12);
  border-color: rgba(var(--hue-rgb),0.20);
  color: var(--text-1);
}}
.chr-chat-bubble p {{ margin: 0 0 6px; }}
.chr-chat-bubble p:last-child {{ margin-bottom: 0; }}
.chr-chat-bubble h3 {{ font-size: 12px; font-weight: 700; color: var(--text-1); margin: 8px 0 3px; }}
.chr-chat-bubble ul, .chr-chat-bubble ol {{ margin: 4px 0; padding-left: 16px; }}
.chr-chat-bubble li {{ margin-bottom: 3px; }}
.chr-chat-bubble strong {{ color: var(--text-1); }}
.chr-chat-input-row {{
  display: flex;
  gap: 8px;
  margin-top: 10px;
  align-items: flex-end;
}}
.chr-chat-input {{
  flex: 1;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 9px 13px;
  font-size: 12px;
  color: var(--text-1);
  resize: none;
  min-height: 38px;
  max-height: 100px;
  font-family: var(--font-sans);
  outline: none;
}}
.chr-chat-input:focus {{ border-color: rgba(var(--hue-rgb),0.40); }}
.chr-chat-input::placeholder {{ color: var(--text-3); }}
.chr-typing-dot {{
  display: inline-block;
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--text-3);
  animation: typingBounce 1.2s ease-in-out infinite;
  margin: 0 1px;
}}
.chr-typing-dot:nth-child(2) {{ animation-delay: 0.2s; }}
.chr-typing-dot:nth-child(3) {{ animation-delay: 0.4s; }}
@keyframes typingBounce {{ 0%,60%,100% {{ transform:translateY(0); }} 30% {{ transform:translateY(-5px); }} }}
/* Prayer modal */
.chr-prayer-meta-row {{
  display: flex;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}}
.chr-prayer-stat {{
  flex: 1;
  min-width: 90px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  text-align: center;
}}
.chr-prayer-stat-num {{ font-size: 20px; font-weight: 700; color: var(--text-1); }}
.chr-prayer-stat-lbl {{ font-size: 10px; color: var(--text-3); text-transform: uppercase; letter-spacing: .06em; margin-top: 2px; }}

/* ═══════════════════════════════════════════════════════════════════
   PUBLISHING — BOOK CARDS
═══════════════════════════════════════════════════════════════════ */
.pub-book-card {{
  background: rgba(255,255,255,0.065);
  backdrop-filter: blur(28px) saturate(160%) brightness(1.04);
  -webkit-backdrop-filter: blur(28px) saturate(160%) brightness(1.04);
  border: 1px solid rgba(255,255,255,0.13);
  border-radius: 14px;
  padding: 18px 20px;
  margin-bottom: 16px;
  position: relative;
  overflow: hidden;
  box-shadow:
    0  1px  0   rgba(255,255,255,0.06),
    0  8px 24px rgba(0,0,0,0.40),
    0 20px 48px rgba(0,0,0,0.25),
    inset 0 1px 0 rgba(255,255,255,0.14),
    inset 1px 0 0 rgba(255,255,255,0.05);
}}
.pub-book-card::before {{
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(var(--hue-rgb), 0.55) 25%,
    rgba(var(--hue-rgb), 0.55) 75%,
    transparent 100%
  );
  border-radius: 14px 14px 0 0;
}}
.pub-book-header {{
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 12px;
}}
.pub-book-title {{
  font-size: 15px;
  font-weight: 600;
  color: var(--text-1);
  flex: 1;
  line-height: 1.3;
}}
.pub-book-subtitle {{
  font-size: 11px;
  color: var(--text-3);
  margin-top: 2px;
  font-style: italic;
}}
.pub-book-meta {{
  display: flex;
  gap: 6px;
  align-items: center;
  flex-shrink: 0;
}}
.pub-progress-wrap {{
  margin-bottom: 14px;
}}
.pub-progress-label {{
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--text-3);
  margin-bottom: 4px;
}}
.pub-progress-bar {{
  height: 4px;
  background: var(--border);
  border-radius: 2px;
  overflow: hidden;
}}
.pub-progress-fill {{
  height: 100%;
  border-radius: 2px;
  background: linear-gradient(90deg, var(--hue) 0%, #5BB8FF 100%);
  transition: width 0.5s ease;
}}
.pub-groups-grid {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}}
@media (max-width: 700px) {{
  .pub-groups-grid {{ grid-template-columns: repeat(2, 1fr); }}
}}
.pub-group {{
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 10px;
  padding: 8px 10px;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.09),
    0 2px 8px rgba(0,0,0,0.30);
}}
.pub-group-name {{
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--text-3);
  text-transform: uppercase;
  margin-bottom: 6px;
}}
.pub-stage-dots {{
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  margin-bottom: 4px;
}}
.pub-stage-dot {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  cursor: default;
  transition: transform 0.15s;
}}
.pub-stage-dot:hover {{ transform: scale(1.4); }}
.pub-stage-dot.committed    {{ background: #3ecf8e; }}
.pub-stage-dot.in_progress  {{ background: var(--hue); animation: pipeline-pulse 1.5s ease-in-out infinite; }}
.pub-stage-dot.review       {{ background: #f0b429; }}
.pub-stage-dot.blocked      {{ background: #e5534b; }}
.pub-stage-dot.not_started  {{ background: var(--border); }}
.pub-group-count {{
  font-size: 9px;
  color: var(--text-3);
}}
.pub-group-count.all-done {{ color: #3ecf8e; }}
.pub-book-footer {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}}
.pub-current-stage {{
  font-size: 11px;
  color: var(--text-2);
}}
.pub-current-stage .stage-chip {{
  background: rgba(59,158,255,0.12);
  color: var(--hue);
  border-radius: 4px;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 500;
  margin-left: 4px;
}}
.pub-review-badge {{
  background: rgba(240,180,41,0.15);
  color: #f0b429;
  border-radius: 4px;
  padding: 2px 7px;
  font-size: 10px;
  font-weight: 600;
  margin-left: 8px;
  letter-spacing: 0.04em;
}}
.pub-open-link {{
  font-size: 11px;
  color: var(--hue);
  text-decoration: none;
  opacity: 0.8;
  transition: opacity 0.2s;
}}
.pub-open-link:hover {{ opacity: 1; text-decoration: underline; }}
.pub-review-item {{
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  border-bottom: 1px solid var(--border);
}}
.pub-review-item:last-child {{ border-bottom: none; }}
.pub-review-book {{ font-size: 13px; font-weight: 600; color: var(--text-1); }}
.pub-review-stage {{ font-size: 11px; color: #f0b429; font-weight: 500; }}
.pub-review-preview {{ font-size: 11px; color: var(--text-3); font-style: italic; }}
.pub-review-meta {{ font-size: 10px; color: var(--text-3); }}
.pub-review-actions {{ display: flex; gap: 6px; margin-top: 4px; }}

/* ═══════════════════════════════════════════════════════════════════
   KASA HOME AUTOMATION
═══════════════════════════════════════════════════════════════════ */
.kasa-header-strip {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}}
.kasa-stats {{
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}}
.kasa-stat {{
  background: var(--glass-1);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 8px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 70px;
}}
.kasa-stat-val {{
  font-size: 20px;
  font-weight: 700;
  color: var(--text-1);
  font-family: var(--font-mono);
  line-height: 1;
}}
.kasa-stat-val.on {{ color: #FBBF24; }}
.kasa-stat-label {{
  font-size: 9px;
  color: var(--text-3);
  letter-spacing: 0.07em;
  margin-top: 2px;
  text-transform: uppercase;
}}
/* Scene buttons */
.kasa-scenes {{
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}}
.kasa-scene-btn {{
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  background: var(--glass-1);
  border: 1px solid var(--border);
  border-radius: 20px;
  font-size: 12px;
  color: var(--text-2);
  cursor: pointer;
  transition: all 0.15s;
  font-weight: 500;
}}
.kasa-scene-btn:hover {{
  background: var(--surface-hi);
  border-color: var(--hue);
  color: var(--text-1);
}}
.kasa-scene-btn:active {{
  transform: scale(0.96);
}}
.kasa-scene-btn.running {{
  border-color: var(--hue);
  color: var(--hue);
  background: var(--hue-dim);
}}
/* Room sections */
.kasa-room-section {{
  margin-bottom: 20px;
}}
.kasa-room-label {{
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--text-3);
  text-transform: uppercase;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}}
.kasa-room-label::after {{
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}}
.kasa-device-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
}}
/* Individual device card */
.kasa-device-card {{
  background: var(--glass-1);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: border-color 0.2s, box-shadow 0.2s;
  cursor: default;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.06);
}}
.kasa-device-card.device-on {{
  border-color: rgba(251,191,36,0.35);
  box-shadow: 0 2px 12px rgba(251,191,36,0.10), inset 0 1px 0 rgba(255,255,255,0.08);
}}
.kasa-device-card.device-off {{
  opacity: 0.65;
}}
.kasa-device-top {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}}
.kasa-device-icon {{
  font-size: 20px;
  line-height: 1;
}}
.kasa-device-info {{
  flex: 1;
  min-width: 0;
}}
.kasa-device-alias {{
  font-size: 12px;
  font-weight: 600;
  color: var(--text-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.kasa-device-model {{
  font-size: 10px;
  color: var(--text-3);
  margin-top: 1px;
}}
/* Toggle switch */
.kasa-toggle {{
  position: relative;
  width: 36px;
  height: 20px;
  flex-shrink: 0;
  cursor: pointer;
}}
.kasa-toggle input {{
  opacity: 0;
  width: 0;
  height: 0;
  position: absolute;
}}
.kasa-toggle-track {{
  position: absolute;
  inset: 0;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 10px;
  transition: background 0.2s, border-color 0.2s;
}}
.kasa-toggle input:checked + .kasa-toggle-track {{
  background: rgba(251,191,36,0.55);
  border-color: rgba(251,191,36,0.6);
}}
.kasa-toggle-thumb {{
  position: absolute;
  top: 3px;
  left: 3px;
  width: 14px;
  height: 14px;
  background: rgba(255,255,255,0.6);
  border-radius: 50%;
  transition: transform 0.2s, background 0.2s;
}}
.kasa-toggle input:checked ~ .kasa-toggle-thumb {{
  transform: translateX(16px);
  background: #fff;
}}
/* Brightness slider */
.kasa-slider-row {{
  display: flex;
  align-items: center;
  gap: 8px;
}}
.kasa-slider-label {{
  font-size: 9px;
  color: var(--text-3);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  width: 14px;
  text-align: right;
  flex-shrink: 0;
}}
.kasa-slider {{
  flex: 1;
  -webkit-appearance: none;
  height: 3px;
  border-radius: 2px;
  background: rgba(255,255,255,0.1);
  outline: none;
  cursor: pointer;
}}
.kasa-slider::-webkit-slider-thumb {{
  -webkit-appearance: none;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #FBBF24;
  cursor: pointer;
}}
.kasa-slider-val {{
  font-size: 10px;
  color: var(--text-3);
  font-family: var(--font-mono);
  width: 28px;
  text-align: right;
  flex-shrink: 0;
}}
/* Camera card */
.kasa-camera-card {{
  grid-column: 1 / -1;
}}
.kasa-live-btn {{
  padding: 5px 14px;
  background: rgba(239,68,68,0.15);
  border: 1px solid rgba(239,68,68,0.4);
  border-radius: 14px;
  color: #ef4444;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}}
.kasa-live-btn:hover {{
  background: rgba(239,68,68,0.25);
}}
.kasa-camera-video {{
  background: #000;
  border-radius: 8px;
}}
/* Status dot on card */
.kasa-device-type-badge {{
  font-size: 9px;
  color: var(--text-3);
  background: rgba(255,255,255,0.05);
  border-radius: 4px;
  padding: 1px 5px;
  margin-top: 3px;
  display: inline-block;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}}
/* Offline / unavailable */
.kasa-unavailable {{
  text-align: center;
  padding: 60px 20px;
  color: var(--text-3);
  font-size: 14px;
}}
.kasa-unavailable-icon {{
  font-size: 36px;
  margin-bottom: 12px;
  opacity: 0.4;
}}
.kasa-refresh-btn {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 16px;
  padding: 8px 18px;
  background: var(--glass-1);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--hue);
  font-size: 12px;
  cursor: pointer;
  transition: background 0.15s;
}}
.kasa-refresh-btn:hover {{ background: var(--surface-hi); }}

/* ═══════════════════════════════════════════════════════════════════
   APPROVAL ITEM
═══════════════════════════════════════════════════════════════════ */
.approval-item {{
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}}
.approval-item:last-child {{ border-bottom: none; padding-bottom: 0; }}
.approval-item:first-child {{ padding-top: 0; }}

.launch-tab {{
  padding: 8px 14px; font-size: 11px; font-weight: 600; letter-spacing: 0.04em;
  background: none; border: none; border-bottom: 2px solid transparent;
  color: var(--text-3); cursor: pointer; white-space: nowrap; transition: color 0.15s;
}}
.launch-tab:hover {{ color: var(--text-1); }}
.launch-tab.active {{ color: var(--hue); border-bottom-color: var(--hue); }}
.launch-post-card {{
  background: var(--surface-hi); border-radius: 8px; padding: 12px 14px;
  margin-bottom: 8px; font-size: 12px; line-height: 1.6; color: var(--text-1);
  display: flex; gap: 10px; align-items: flex-start;
}}
.launch-post-body {{ flex: 1; white-space: pre-wrap; }}
.launch-copy-btn {{
  flex-shrink: 0; padding: 3px 10px; font-size: 10px; background: var(--glass-1);
  border: 1px solid var(--border); border-radius: 6px; cursor: pointer;
  color: var(--text-2); transition: background 0.15s;
}}
.launch-copy-btn:hover {{ background: var(--hue); color: #fff; border-color: var(--hue); }}
.launch-book-row {{
  display: flex; align-items: center; gap: 10px; padding: 10px 0;
  border-bottom: 1px solid var(--border); font-size: 12px;
}}
.launch-book-row:last-child {{ border-bottom: none; }}
.launch-book-title {{ flex: 1; font-weight: 600; color: var(--text-1); }}
.launch-book-stage {{ font-size: 10px; color: var(--text-3); font-family: var(--font-mono); }}

.approval-title {{
  font-size: 13px;
  font-weight: 600;
  color: var(--text-1);
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
  background: rgba(255,255,255,0.04);
  backdrop-filter: blur(16px) saturate(140%);
  -webkit-backdrop-filter: blur(16px) saturate(140%);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.30), 0 4px 16px rgba(0,0,0,0.20);
  padding: 12px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-left-width: 3px;
  border-left-style: solid;
  cursor: default;
}}
.agent-badge:hover {{
  box-shadow: 0 2px 8px rgba(0,0,0,0.40), 0 8px 24px rgba(0,0,0,0.30);
  transform: translateY(-1px);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}}

.agent-info {{ flex: 1; min-width: 0; }}
.agent-name {{
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  color: var(--text-1);
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
.dossier-card-title {{ font-size: 13px; font-weight: 600; color: var(--text-1); margin-bottom: 6px; }}
.dossier-card-summary {{ font-size: 11px; color: var(--text-2); line-height: 1.5; margin-bottom: 10px; }}
.dossier-metrics {{
  display: flex; gap: 12px; flex-wrap: wrap;
}}
.dossier-metric {{
  font-size: 10px; color: var(--text-3);
}}
.dossier-metric strong {{ color: var(--text-1); }}
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
  color: var(--text-2); cursor: pointer; transition: all 0.2s;
  text-align: center;
}}
.dossier-read-btn:hover {{ background: rgba(255,255,255,0.08); color: var(--text-1); }}
.dossier-approve-btn {{
  flex: 1; padding: 6px; border-radius: 6px; font-size: 10px;
  background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.25);
  color: #22c55e; cursor: pointer; transition: all 0.2s; text-align: center;
}}
.dossier-approve-btn:hover {{ background: rgba(34,197,94,0.2); }}

/* Dossier Modal */
.dossier-modal-overlay {{
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(5,10,20,0.50);
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
  animation: modal-overlay-in 0.25s ease;
}}
.dossier-modal {{
  position: relative; overflow: hidden;
  background: rgba(255,255,255,0.08);
  backdrop-filter: blur(60px) saturate(220%) brightness(1.10);
  -webkit-backdrop-filter: blur(60px) saturate(220%) brightness(1.10);
  border: 1px solid rgba(255,255,255,0.22);
  border-radius: 24px; width: 100%; max-width: 720px;
  max-height: 85vh; overflow-y: auto; padding: 28px;
  box-shadow:
    0  4px  8px  rgba(0,0,0,0.35),
    0 16px  48px rgba(0,0,0,0.50),
    0 48px  96px rgba(0,0,0,0.35),
    inset 0  1px 0 rgba(255,255,255,0.65),
    inset 1px 0  0 rgba(255,255,255,0.22),
    inset 0 -1px 0 rgba(0,0,0,0.15);
  animation: modal-in 0.38s cubic-bezier(0.34,1.56,0.64,1);
}}
.dossier-modal::before {{
  content: '';
  position: absolute; inset: 0; border-radius: 23px; pointer-events: none; z-index: 0;
  background: linear-gradient(
    135deg,
    rgba(255,255,255,0.18) 0%,
    rgba(255,255,255,0.05) 30%,
    transparent 55%,
    rgba(255,255,255,0.02) 100%
  );
}}
.dossier-modal > * {{ position: relative; z-index: 1; }}
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
.runtime-stat-val {{ font-size: 16px; font-weight: 700; font-family: var(--font-mono); color: var(--text-1); }}
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
  background: rgba(255,255,255,0.04);
  backdrop-filter: blur(16px) saturate(140%);
  -webkit-backdrop-filter: blur(16px) saturate(140%);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3), 0 6px 20px rgba(0,0,0,0.2);
  padding: 14px 16px;
  border-left-width: 3px;
  border-left-style: solid;
  border-left-color: rgba(59,158,255,0.5);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}}
.agent-runtime-card:hover {{
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.4), 0 10px 32px rgba(0,0,0,0.3);
  background: rgba(255,255,255,0.06);
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
  color: var(--text-1);
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
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 6px;
  padding: 5px 12px;
  cursor: pointer;
  color: var(--text-2);
  transition: background 0.15s;
}}
.roster-toggle:hover {{ background: rgba(255,255,255,0.10); color: var(--text-1); }}

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
  color: var(--text-1);
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
  color: var(--text-1);
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
  color: var(--text-1);
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
   AGENT TOOL BLOCKS
═══════════════════════════════════════════════════════════════════ */
.tool-block {{
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  margin: 6px 0;
  overflow: hidden;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
}}
.tool-header {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  cursor: pointer;
  user-select: none;
  background: rgba(255,255,255,0.03);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}}
.tool-header:hover {{ background: rgba(255,255,255,0.06); }}
.tool-icon {{ font-size: 13px; }}
.tool-name {{ color: rgba(255,255,255,0.85); font-weight: 600; }}
.tool-status {{
  margin-left: auto;
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 20px;
  font-weight: 500;
}}
.tool-status.running {{ background: rgba(99,179,237,0.2); color: #63b3ed; }}
.tool-status.done    {{ background: rgba(72,187,120,0.2); color: #48bb78; }}
.tool-status.error   {{ background: rgba(252,129,129,0.2); color: #fc8181; }}
.tool-status.skipped {{ background: rgba(160,160,160,0.2); color: #a0aec0; }}
.tool-input-line {{
  padding: 5px 12px;
  color: rgba(255,255,255,0.5);
  font-size: 11px;
  white-space: pre-wrap;
  word-break: break-all;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}}
.tool-output-area {{
  padding: 8px 12px;
  color: rgba(255,255,255,0.75);
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
  display: none;
}}
.tool-output-area.expanded {{ display: block; }}
.tool-chevron {{ font-size: 10px; color: rgba(255,255,255,0.4); transition: transform 0.2s; }}
.tool-chevron.open {{ transform: rotate(90deg); }}

/* Approval card */
.approval-card {{
  background: rgba(246,173,85,0.08);
  border: 1px solid rgba(246,173,85,0.3);
  border-radius: 10px;
  padding: 12px 14px;
  margin: 6px 0;
}}
.approval-title {{ color: #f6ad55; font-weight: 600; font-size: 13px; margin-bottom: 6px; }}
.approval-detail {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: rgba(255,255,255,0.6);
  background: rgba(0,0,0,0.2);
  padding: 6px 9px;
  border-radius: 6px;
  white-space: pre-wrap;
  word-break: break-all;
  margin-bottom: 10px;
  max-height: 150px;
  overflow-y: auto;
}}
.approval-btns {{ display: flex; gap: 8px; }}
.approval-btn {{
  padding: 6px 16px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  transition: opacity 0.15s;
}}
.approval-btn:hover {{ opacity: 0.8; }}
.approval-btn.approve {{ background: #48bb78; color: #fff; }}
.approval-btn.decline {{ background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.7); }}
.approval-resolved {{ color: rgba(255,255,255,0.4); font-size: 12px; font-style: italic; padding: 4px 0; }}

/* Streaming text cursor */
.streaming-cursor {{
  display: inline-block;
  width: 2px;
  height: 1em;
  background: rgba(255,255,255,0.7);
  margin-left: 1px;
  animation: blink 0.8s step-end infinite;
  vertical-align: text-bottom;
}}
@keyframes blink {{ 50% {{ opacity: 0; }} }}

/* ═══════════════════════════════════════════════════════════════════
   COMMAND BAR
═══════════════════════════════════════════════════════════════════ */
.command-bar {{
  position: fixed;
  bottom: 0; left: var(--nav-w); right: 0;
  height: auto;
  min-height: var(--bar-h);
  z-index: 100;
  background: rgba(6, 11, 22, 0.82);
  backdrop-filter: blur(40px) saturate(150%);
  -webkit-backdrop-filter: blur(40px) saturate(150%);
  border-top: 1px solid rgba(255,255,255,0.10);
  box-shadow:
    0 -4px 32px rgba(0,0,0,0.55),
    0 -1px 0 rgba(var(--hue-rgb),0.10),
    inset 0 1px 0 rgba(255,255,255,0.08);
  padding: 8px 24px 12px;
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
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.10);
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
.cmd-mic:hover {{ background: var(--surface-hi); color: var(--text-1); }}

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
  background: rgba(5,10,20,0.50);
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  animation: modal-overlay-in 0.25s ease;
}}
.modal-overlay.hidden {{ display: none; animation: none; }}
@keyframes modal-overlay-in {{
  from {{ opacity: 0; }}
  to   {{ opacity: 1; }}
}}

.modal {{
  position: relative;
  overflow: hidden;
  background: rgba(255,255,255,0.08);
  backdrop-filter: blur(60px) saturate(220%) brightness(1.10);
  -webkit-backdrop-filter: blur(60px) saturate(220%) brightness(1.10);
  border: 1px solid rgba(255,255,255,0.22);
  border-radius: 24px;
  box-shadow:
    0  4px  8px  rgba(0,0,0,0.35),
    0 16px  48px rgba(0,0,0,0.50),
    0 48px  96px rgba(0,0,0,0.35),
    inset 0  1px 0 rgba(255,255,255,0.65),
    inset 1px 0  0 rgba(255,255,255,0.22),
    inset 0 -1px 0 rgba(0,0,0,0.15);
  max-width: 480px;
  width: 100%;
  padding: 28px 28px 24px;
  animation: modal-in 0.38s cubic-bezier(0.34,1.56,0.64,1);
}}
/* Full-screen settings panel — replaces old #settings-modal small modal */
#settings-overlay {{
  position: fixed;
  inset: 0;
  z-index: 300;
  background: rgba(0,0,0,0.85);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  animation: modal-overlay-in 0.22s ease;
}}
#settings-overlay.hidden {{ display: none; animation: none; }}

#settings-panel {{
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 860px;
  height: min(88vh, 680px);
  background: var(--surface-1, rgba(20,24,34,0.97));
  border: 1px solid var(--border);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 24px 80px rgba(0,0,0,0.6), 0 4px 16px rgba(0,0,0,0.4);
  animation: modal-in 0.3s cubic-bezier(0.34,1.4,0.64,1);
}}

#settings-topbar {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}}
#settings-topbar-title {{
  font-size: 15px;
  font-weight: 700;
  color: var(--text-1);
  letter-spacing: -0.01em;
}}

#settings-body {{
  display: flex;
  flex: 1;
  min-height: 0;
}}

#settings-nav {{
  width: 190px;
  flex-shrink: 0;
  border-right: 1px solid var(--border);
  padding: 16px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
}}
.settings-nav-pill {{
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 12px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-2);
  cursor: pointer;
  border: none;
  background: transparent;
  width: 100%;
  text-align: left;
  transition: background 0.15s, color 0.15s;
}}
.settings-nav-pill:hover {{ background: rgba(255,255,255,0.06); color: var(--text-1); }}
.settings-nav-pill.active {{
  background: var(--accent, var(--hue));
  color: #fff;
}}
.settings-nav-pill .snp-icon {{ font-size: 15px; width: 18px; text-align: center; }}
.settings-nav-section-label {{
  font-size: 10px;
  font-family: var(--font-mono);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-3);
  padding: 10px 12px 4px;
}}

#settings-content {{
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
}}

/* section-level header */
.sset-section-hdr {{
  font-size: 11px;
  font-family: var(--font-mono);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-3);
  margin: 0 0 12px;
}}
.sset-divider {{ height: 1px; background: var(--border); margin: 22px 0; }}
.sset-card {{
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 12px;
}}
.sset-row {{
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}}
.sset-row:last-child {{ margin-bottom: 0; }}
.sset-label {{ font-size: 12px; color: var(--text-2); flex: 1; }}
.sset-badge {{
  font-size: 10px;
  font-family: var(--font-mono);
  padding: 2px 7px;
  border-radius: 99px;
  font-weight: 700;
  letter-spacing: 0.06em;
}}
.sset-badge-green {{ background: rgba(74,222,128,0.15); color: #4ade80; border: 1px solid rgba(74,222,128,0.3); }}
.sset-badge-grey  {{ background: rgba(255,255,255,0.06); color: var(--text-3); border: 1px solid var(--border); }}
.sset-badge-amber {{ background: rgba(251,191,36,0.12); color: #fbbf24; border: 1px solid rgba(251,191,36,0.3); }}
.sset-btn {{
  padding: 6px 14px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: rgba(255,255,255,0.06);
  color: var(--text-2);
  font-size: 12px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}}
.sset-btn:hover {{ background: rgba(255,255,255,0.12); color: var(--text-1); }}
.sset-btn-accent {{
  border-color: var(--accent, var(--hue));
  color: var(--accent, var(--hue));
  background: transparent;
}}
.sset-btn-accent:hover {{ background: rgba(var(--hue-rgb),0.12); color: var(--accent, var(--hue)); }}
.sset-textarea {{
  width: 100%;
  box-sizing: border-box;
  background: var(--surface-2, rgba(255,255,255,0.04));
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 11px;
  color: var(--text-1);
  font-family: var(--font-mono);
  resize: vertical;
  outline: none;
  margin-bottom: 8px;
}}
.sset-msg {{
  font-size: 11px;
  color: var(--text-3);
  margin-top: 6px;
  min-height: 16px;
}}
.sset-select {{
  background: var(--surface-2, rgba(255,255,255,0.06));
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 12px;
  color: var(--text-1);
  outline: none;
  cursor: pointer;
}}

/* Mobile: collapse nav to top tabs */
@media (max-width: 600px) {{
  #settings-panel {{ height: 100dvh; max-width: 100%; border-radius: 0; }}
  #settings-body {{ flex-direction: column; }}
  #settings-nav {{
    width: 100%;
    flex-direction: row;
    overflow-x: auto;
    border-right: none;
    border-bottom: 1px solid var(--border);
    padding: 8px 8px 0;
    gap: 2px;
  }}
  .settings-nav-pill {{ white-space: nowrap; padding: 8px 12px; border-radius: 8px 8px 0 0; }}
  .settings-nav-section-label {{ display: none; }}
}}
.modal::before {{
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 23px;
  background: linear-gradient(
    135deg,
    rgba(255,255,255,0.18) 0%,
    rgba(255,255,255,0.05) 30%,
    transparent 55%,
    rgba(255,255,255,0.02) 100%
  );
  pointer-events: none;
  z-index: 1;
}}
@keyframes modal-in {{
  from {{ opacity: 0; transform: scale(0.93) translateY(20px); }}
  to   {{ opacity: 1; transform: scale(1)    translateY(0);    }}
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
  color: var(--text-1);
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
.modal-close:hover {{ background: var(--surface-hi); color: var(--text-1); }}

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
  color: var(--text-1);
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
  background: linear-gradient(90deg, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.10) 50%, rgba(255,255,255,0.05) 75%);
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
  color: var(--text-1);
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
.btn-ghost:hover {{ background: var(--surface-hi); color: var(--text-1); }}

/* ── Health Chat Console ──────────────────────────────── */
.hchat-wrap {{
  display: flex;
  flex-direction: column;
  min-height: 460px;
}}
/* ── Doctor selector bar ── */
.hchat-selector-bar {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
  position: relative;
}}
.hchat-selector-label {{
  font-size: 9px;
  font-weight: 700;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--text-3);
  white-space: nowrap;
}}
.hchat-active-pill {{
  display: flex;
  align-items: center;
  gap: 7px;
  background: var(--hue-dim);
  border: 1px solid var(--hue);
  border-radius: 20px;
  padding: 5px 12px 5px 9px;
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
  color: var(--hue);
  transition: background .15s;
  user-select: none;
}}
.hchat-active-pill:hover {{ background: color-mix(in srgb, var(--hue) 20%, transparent); }}
.hchat-active-pill-icon {{ font-size: 15px; line-height: 1; }}
.hchat-active-pill-name {{ white-space: nowrap; }}
.hchat-active-pill-arrow {{
  font-size: 9px;
  opacity: .7;
  transition: transform .2s;
  margin-left: 2px;
}}
.hchat-active-pill.open .hchat-active-pill-arrow {{ transform: rotate(180deg); }}
.hchat-active-pill-subtitle {{
  font-size: 9px;
  color: var(--text-3);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: .05em;
  white-space: nowrap;
}}
/* ── Dropdown panel ── */
.hchat-dropdown {{
  display: none;
  position: absolute;
  top: calc(100% + 4px);
  left: 14px;
  z-index: 9999;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,.35);
  padding: 10px;
  width: 380px;
  max-width: calc(100vw - 28px);
  max-height: 380px;
  overflow-y: auto;
}}
.hchat-dropdown.open {{ display: block; }}
.hchat-dropdown::-webkit-scrollbar {{ width: 4px; }}
.hchat-dropdown::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}
.hchat-dropdown-label {{
  font-size: 9px;
  font-weight: 700;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--text-3);
  padding: 2px 4px 8px;
}}
.hchat-dropdown-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
}}
.hchat-doc-btn {{
  display: flex;
  align-items: center;
  gap: 8px;
  text-align: left;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 7px 10px;
  cursor: pointer;
  transition: background .15s, border-color .15s;
  width: 100%;
}}
.hchat-doc-btn:hover {{ background: var(--surface-hi); border-color: var(--border); }}
.hchat-doc-btn.active {{ background: var(--hue-dim); border-color: var(--hue); }}
.hchat-doc-icon {{ font-size: 17px; flex-shrink: 0; line-height: 1; }}
.hchat-doc-info {{ display: flex; flex-direction: column; gap: 1px; overflow: hidden; }}
.hchat-doc-name {{
  font-size: 11px; font-weight: 600; color: var(--text-1);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.hchat-doc-btn.active .hchat-doc-name {{ color: var(--hue); }}
.hchat-doc-domain {{
  font-size: 9px; color: var(--text-3);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  font-family: var(--font-mono); text-transform: uppercase; letter-spacing: .04em;
}}
.hchat-msg-user {{
  align-self: flex-end;
  background: var(--hue);
  color: #fff;
  border-radius: 12px 12px 2px 12px;
  padding: 10px 14px;
  font-size: 12px;
  max-width: 75%;
  line-height: 1.5;
}}
.hchat-msg-doctor {{
  align-self: flex-start;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 2px 12px 12px 12px;
  padding: 12px 14px;
  font-size: 12px;
  max-width: 85%;
  line-height: 1.6;
}}
.hchat-msg-doctor-name {{
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .08em;
  color: var(--hue);
  margin-bottom: 6px;
}}
.hchat-msg-body h3,
.hchat-msg-body h4 {{
  font-size: 12px;
  font-weight: 700;
  color: var(--text-1);
  margin: 10px 0 4px;
}}
.hchat-msg-body h3 {{ font-size: 13px; }}
.hchat-msg-body p {{ margin: 0 0 6px; }}
.hchat-msg-body ul,
.hchat-msg-body ol {{
  margin: 4px 0 8px 16px;
  padding: 0;
}}
.hchat-msg-body li {{ margin-bottom: 3px; }}
.hchat-msg-body strong {{ font-weight: 700; color: var(--text-1); }}
.hchat-msg-body em {{ font-style: italic; }}

/* ── Health metric sparklines ───────────────────────────── */
.hm-sparkline {{
  display: block;
  width: 100%;
  margin-top: 6px;
  line-height: 0;
}}
.hm-sparkline svg {{
  display: block;
  width: 100%;
  height: 42px;
}}

.hchat-thinking {{
  align-self: flex-start;
  padding: 10px 14px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 2px 12px 12px 12px;
  font-size: 11px;
  color: var(--text-3);
  font-style: italic;
}}

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
  color: var(--text-1);
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
.forge-modal-overlay {{
  position:fixed; inset:0; z-index:900;
  background: rgba(5,10,20,0.50);
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  display:flex; align-items:center; justify-content:center;
  animation: modal-overlay-in 0.25s ease;
}}
.forge-modal-overlay.hidden {{ display:none !important; animation:none; }}
.forge-modal {{
  position: relative; overflow: hidden;
  background: rgba(255,255,255,0.08);
  backdrop-filter: blur(60px) saturate(220%) brightness(1.10);
  -webkit-backdrop-filter: blur(60px) saturate(220%) brightness(1.10);
  border: 1px solid rgba(255,255,255,0.22);
  border-radius: 24px; padding:24px;
  min-width:340px; max-width:540px; width:90%;
  box-shadow:
    0  4px  8px  rgba(0,0,0,0.35),
    0 16px  48px rgba(0,0,0,0.50),
    0 48px  96px rgba(0,0,0,0.35),
    inset 0  1px 0 rgba(255,255,255,0.65),
    inset 1px 0  0 rgba(255,255,255,0.22),
    inset 0 -1px 0 rgba(0,0,0,0.15);
  animation: modal-in 0.38s cubic-bezier(0.34,1.56,0.64,1);
}}
.forge-modal::before {{
  content:''; position:absolute; inset:0; border-radius:23px; pointer-events:none; z-index:0;
  background: linear-gradient(135deg,rgba(255,255,255,0.18) 0%,rgba(255,255,255,0.05) 30%,transparent 55%,rgba(255,255,255,0.02) 100%);
}}
.forge-modal > * {{ position:relative; z-index:1; }}
.forge-modal-title {{ font-size:15px; font-weight:700; margin-bottom:16px; color:var(--text-1); }}
.forge-timeline-list {{ display:flex; flex-direction:column; gap:6px; max-height:400px; overflow-y:auto; }}
.forge-tl-row {{ display:flex; gap:10px; font-size:11px; padding:6px 0; border-bottom:1px solid var(--border); }}
.forge-tl-ts {{ font-family:var(--font-mono); color:var(--text-3); white-space:nowrap; min-width:140px; }}
.forge-tl-event {{ color:var(--hue); font-weight:600; min-width:120px; }}
.forge-tl-detail {{ color:var(--text-2); flex:1; }}
.forge-camera-preview {{ width:100%; border-radius:10px; margin-bottom:12px; max-height:220px; object-fit:cover; }}

/* ═══ FINANCE SETUP MODAL ════════════════════════════════════ */
.finance-modal-overlay {{
  position:fixed; inset:0; z-index:1100;
  background: rgba(5,10,20,0.55);
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  display:flex; align-items:center; justify-content:center;
  animation: modal-overlay-in 0.25s ease;
}}
.finance-modal-overlay.hidden {{ display:none !important; animation:none; }}
.finance-modal {{
  position:relative; overflow:hidden;
  background: rgba(255,255,255,0.08);
  backdrop-filter: blur(60px) saturate(220%) brightness(1.10);
  -webkit-backdrop-filter: blur(60px) saturate(220%) brightness(1.10);
  border: 1px solid rgba(255,255,255,0.22);
  border-radius:24px; padding:28px;
  min-width:380px; max-width:620px; width:92%;
  max-height:88vh; overflow-y:auto;
  box-shadow:
    0  4px  8px  rgba(0,0,0,0.35),
    0 16px  48px rgba(0,0,0,0.50),
    0 48px  96px rgba(0,0,0,0.35),
    inset 0  1px 0 rgba(255,255,255,0.65),
    inset 1px 0  0 rgba(255,255,255,0.22),
    inset 0 -1px 0 rgba(0,0,0,0.15);
  animation: modal-in 0.38s cubic-bezier(0.34,1.56,0.64,1);
}}
.finance-modal::before {{
  content:''; position:absolute; inset:0; border-radius:23px; pointer-events:none; z-index:0;
  background: linear-gradient(135deg,rgba(255,255,255,0.18) 0%,rgba(255,255,255,0.05) 30%,transparent 55%,rgba(255,255,255,0.02) 100%);
}}
.finance-modal > * {{ position:relative; z-index:1; }}
.finance-tabs {{
  display:flex; gap:6px; margin-bottom:20px;
  background:rgba(255,255,255,0.05); border-radius:10px; padding:4px;
}}
.finance-tab {{
  flex:1; padding:7px 0; font-size:11px; font-weight:600; text-transform:uppercase;
  letter-spacing:0.05em; border:none; border-radius:7px; cursor:pointer;
  background:transparent; color:var(--text-3); transition:background 0.15s,color 0.15s;
}}
.finance-tab.active {{
  background:rgba(255,255,255,0.12); color:var(--text-1);
}}
.finance-panel {{ display:none; }}
.finance-panel.active {{ display:block; }}
.finance-row {{
  display:flex; align-items:center; gap:8px;
  padding:8px 10px; background:rgba(255,255,255,0.05);
  border-radius:8px; margin-bottom:6px;
}}
.finance-row-name  {{ flex:1; font-size:12px; font-weight:600; color:var(--text-1); }}
.finance-row-sub   {{ font-size:10px; color:var(--text-3); margin-top:1px; }}
.finance-row-val   {{ font-family:var(--font-mono); font-size:13px; font-weight:700; color:var(--text-1); white-space:nowrap; }}
.finance-row-del   {{
  width:22px; height:22px; border-radius:6px; border:1px solid rgba(255,255,255,0.1);
  background:rgba(239,68,68,0.12); color:#ef4444; cursor:pointer; font-size:11px;
  display:flex; align-items:center; justify-content:center; flex-shrink:0;
  transition:background 0.15s;
}}
.finance-row-del:hover {{ background:rgba(239,68,68,0.30); }}
.finance-form {{ border-top:1px solid rgba(255,255,255,0.08); padding-top:14px; margin-top:4px; }}
.finance-form-title {{ font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:var(--text-3); margin-bottom:10px; }}
.finance-inputs {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:10px; }}
.finance-inputs.single {{ grid-template-columns:1fr; }}
.finance-inp, .finance-sel {{
  padding:8px 10px; font-size:12px;
  background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12);
  border-radius:8px; color:var(--text-1); outline:none;
  transition:border-color 0.15s,background 0.15s;
}}
.finance-inp::placeholder {{ color:var(--text-3); }}
.finance-inp:focus, .finance-sel:focus {{ border-color:rgba(255,255,255,0.30); background:rgba(255,255,255,0.09); }}
.finance-sel option {{ background:#1a1f2e; color:#fff; }}
.finance-add-btn {{
  width:100%; padding:9px; font-size:12px; font-weight:700; text-transform:uppercase;
  letter-spacing:0.06em; border:none; border-radius:10px; cursor:pointer;
  background: linear-gradient(135deg,rgba(99,179,237,0.7) 0%,rgba(129,140,248,0.7) 100%);
  color:#fff; transition:opacity 0.15s;
}}
.finance-add-btn:hover {{ opacity:0.85; }}
.finance-empty {{ font-size:11px; color:var(--text-3); text-align:center; padding:16px 0; font-style:italic; }}
.finance-setup-link {{
  display:inline-flex; align-items:center; gap:5px;
  padding:5px 10px; font-size:10px; font-weight:600;
  border:1px solid rgba(255,255,255,0.15); border-radius:7px;
  background:rgba(255,255,255,0.06); color:var(--text-2); cursor:pointer;
  margin-top:6px; transition:background 0.15s, color 0.15s;
}}
.finance-setup-link:hover {{ background:rgba(255,255,255,0.12); color:var(--text-1); }}

/* ═══ VITALS ENTRY MODAL ════════════════════════════════════ */
.vitals-modal-overlay {{
  position:fixed; inset:0; z-index:1200;
  background: rgba(5,10,20,0.55);
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  display:flex; align-items:center; justify-content:center;
  animation: modal-overlay-in 0.25s ease;
}}
.vitals-modal-overlay.hidden {{ display:none !important; animation:none; }}
.vitals-modal {{
  position:relative; overflow:hidden;
  background: rgba(255,255,255,0.08);
  backdrop-filter: blur(60px) saturate(220%) brightness(1.10);
  -webkit-backdrop-filter: blur(60px) saturate(220%) brightness(1.10);
  border: 1px solid rgba(255,255,255,0.22);
  border-radius:24px; padding:28px;
  min-width:360px; max-width:560px; width:92%;
  max-height:88vh; overflow-y:auto;
  box-shadow:
    0  4px  8px  rgba(0,0,0,0.35),
    0 16px  48px rgba(0,0,0,0.50),
    0 48px  96px rgba(0,0,0,0.35),
    inset 0  1px 0 rgba(255,255,255,0.65),
    inset 1px 0  0 rgba(255,255,255,0.22),
    inset 0 -1px 0 rgba(0,0,0,0.15);
  animation: modal-in 0.38s cubic-bezier(0.34,1.56,0.64,1);
}}
.vitals-modal::before {{
  content:''; position:absolute; inset:0; border-radius:23px; pointer-events:none; z-index:0;
  background: linear-gradient(135deg,rgba(255,255,255,0.18) 0%,rgba(255,255,255,0.05) 30%,transparent 55%,rgba(255,255,255,0.02) 100%);
}}
.vitals-modal > * {{ position:relative; z-index:1; }}
.vitals-section-label {{
  font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.1em;
  color:var(--text-3); margin-bottom:10px; margin-top:18px; padding-bottom:6px;
  border-bottom:1px solid rgba(255,255,255,0.08);
}}
.vitals-section-label:first-of-type {{ margin-top:4px; }}
.vitals-grid {{
  display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:4px;
}}
.vitals-grid.triple {{ grid-template-columns:1fr 1fr 1fr; }}
.vitals-field {{ display:flex; flex-direction:column; gap:4px; }}
.vitals-label {{
  font-size:10px; font-weight:600; color:var(--text-3);
  text-transform:uppercase; letter-spacing:0.06em;
}}
.vitals-inp {{
  padding:9px 11px; font-size:13px; font-family:var(--font-mono);
  background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12);
  border-radius:9px; color:var(--text-1); outline:none; width:100%; box-sizing:border-box;
  transition:border-color 0.15s, background 0.15s;
}}
.vitals-inp::placeholder {{ color:rgba(255,255,255,0.2); font-family:var(--font-mono); }}
.vitals-inp:focus {{ border-color:rgba(99,179,237,0.5); background:rgba(255,255,255,0.09); }}
.vitals-unit {{
  font-size:9px; color:var(--text-3); margin-top:2px;
  text-transform:uppercase; letter-spacing:0.05em;
}}
.vitals-date-row {{
  display:flex; align-items:center; gap:8px; margin-bottom:14px;
  font-size:11px; color:var(--text-3);
}}
.vitals-date-inp {{
  padding:6px 10px; font-size:11px;
  background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12);
  border-radius:7px; color:var(--text-1); outline:none;
  transition:border-color 0.15s;
}}
.vitals-date-inp:focus {{ border-color:rgba(99,179,237,0.5); }}
.vitals-submit {{
  width:100%; padding:10px; font-size:12px; font-weight:700;
  text-transform:uppercase; letter-spacing:0.07em;
  border:none; border-radius:11px; cursor:pointer; margin-top:18px;
  background: linear-gradient(135deg,rgba(99,179,237,0.75) 0%,rgba(129,140,248,0.75) 100%);
  color:#fff; transition:opacity 0.15s;
}}
.vitals-submit:hover {{ opacity:0.85; }}
.vitals-submit:disabled {{ opacity:0.4; cursor:not-allowed; }}
.vitals-log-btn {{
  display:inline-flex; align-items:center; gap:5px;
  padding:5px 11px; font-size:10px; font-weight:700; text-transform:uppercase;
  letter-spacing:0.06em; border:1px solid rgba(255,255,255,0.15);
  border-radius:7px; background:rgba(255,255,255,0.06); color:var(--text-2);
  cursor:pointer; transition:background 0.15s, color 0.15s;
}}
.vitals-log-btn:hover {{ background:rgba(255,255,255,0.12); color:var(--text-1); }}

/* ═══ SAM HISTORY MODAL ══════════════════════════════════════ */
.sam-hist-overlay {{
  position:fixed; inset:0; z-index:1300;
  background: rgba(5,10,20,0.55);
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  display:flex; align-items:center; justify-content:center;
  animation: modal-overlay-in 0.25s ease;
}}
.sam-hist-overlay.hidden {{ display:none !important; animation:none; }}

/* Sam Daily Journal */
#sam-journal-overlay {{ display:flex; }}
#sam-journal-overlay.hidden {{ display:none !important; }}
.sam-hist-modal {{
  position:relative; overflow:hidden;
  background: rgba(255,255,255,0.08);
  backdrop-filter: blur(60px) saturate(220%) brightness(1.10);
  -webkit-backdrop-filter: blur(60px) saturate(220%) brightness(1.10);
  border: 1px solid rgba(255,255,255,0.22);
  border-radius:24px; padding:26px 28px;
  width:92%; max-width:480px; max-height:88vh; overflow-y:auto;
  box-shadow:
    0  4px  8px  rgba(0,0,0,0.35),
    0 16px  48px rgba(0,0,0,0.50),
    0 48px  96px rgba(0,0,0,0.35),
    inset 0  1px 0 rgba(255,255,255,0.65),
    inset 1px 0  0 rgba(255,255,255,0.22),
    inset 0 -1px 0 rgba(0,0,0,0.15);
  animation: modal-in 0.38s cubic-bezier(0.34,1.56,0.64,1);
}}
.sam-hist-modal::before {{
  content:''; position:absolute; inset:0; border-radius:23px; pointer-events:none; z-index:0;
  background: linear-gradient(135deg,rgba(255,255,255,0.18) 0%,rgba(255,255,255,0.05) 30%,transparent 55%,rgba(255,255,255,0.02) 100%);
}}
.sam-hist-modal > * {{ position:relative; z-index:1; }}
/* Day navigator */
.sam-hist-nav {{
  display:flex; align-items:center; justify-content:space-between;
  margin-bottom:18px;
}}
.sam-hist-nav-btn {{
  width:34px; height:34px; border-radius:10px;
  border:1px solid rgba(255,255,255,0.14); background:rgba(255,255,255,0.06);
  color:var(--text-2); font-size:16px; cursor:pointer; display:flex;
  align-items:center; justify-content:center;
  transition:background 0.15s, color 0.15s;
}}
.sam-hist-nav-btn:hover {{ background:rgba(255,255,255,0.14); color:var(--text-1); }}
.sam-hist-nav-btn:disabled {{ opacity:0.25; cursor:default; }}
.sam-hist-date {{
  text-align:center; flex:1; padding:0 12px;
}}
.sam-hist-date-label {{
  font-size:15px; font-weight:700; color:var(--text-1);
}}
.sam-hist-date-rel {{
  font-size:10px; color:var(--text-3); margin-top:2px;
  text-transform:uppercase; letter-spacing:0.08em;
}}
/* Adherence ring / bar */
.sam-hist-pct {{
  text-align:center; margin-bottom:16px;
}}
.sam-hist-pct-num {{
  font-size:36px; font-weight:700; font-family:var(--font-mono); line-height:1;
}}
.sam-hist-pct-bar {{
  height:4px; background:rgba(255,255,255,0.08); border-radius:3px; margin:8px 0 2px;
}}
.sam-hist-pct-fill {{
  height:100%; border-radius:3px; transition:width 0.5s ease;
  background: linear-gradient(90deg, var(--green), #34d399);
}}
/* Checklist */
.sam-hist-list {{
  display:flex; flex-direction:column; gap:8px; margin-bottom:14px;
}}
.sam-hist-item {{
  display:flex; align-items:center; gap:10px;
  padding:9px 12px; border-radius:10px;
  background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07);
  cursor:pointer; user-select:none; transition:background 0.12s, border-color 0.12s;
}}
.sam-hist-item:hover {{ background:rgba(255,255,255,0.08); }}
.sam-hist-item.checked {{
  background:rgba(52,211,153,0.10); border-color:rgba(52,211,153,0.30);
}}
.sam-hist-item-icon {{ font-size:16px; width:22px; text-align:center; flex-shrink:0; }}
.sam-hist-item-label {{ flex:1; font-size:12px; font-weight:500; color:var(--text-2); }}
.sam-hist-item.checked .sam-hist-item-label {{ color:var(--text-1); font-weight:600; }}
.sam-hist-cb {{
  width:17px; height:17px; border-radius:5px; border:1.5px solid rgba(255,255,255,0.2);
  background:rgba(255,255,255,0.05); display:flex; align-items:center; justify-content:center;
  flex-shrink:0; transition:all 0.12s;
}}
.sam-hist-item.checked .sam-hist-cb {{
  background:var(--green); border-color:var(--green); color:#000; font-size:10px;
}}
/* Notes */
.sam-hist-notes {{
  width:100%; box-sizing:border-box; resize:vertical; min-height:60px;
  padding:9px 11px; font-size:12px; font-family:var(--font-body);
  background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12);
  border-radius:9px; color:var(--text-1); outline:none;
  transition:border-color 0.15s;
  margin-bottom:14px;
}}
.sam-hist-notes::placeholder {{ color:rgba(255,255,255,0.2); }}
.sam-hist-notes:focus {{ border-color:rgba(99,179,237,0.4); }}
/* Save button */
.sam-hist-save {{
  width:100%; padding:10px; font-size:12px; font-weight:700;
  text-transform:uppercase; letter-spacing:0.07em;
  border:none; border-radius:11px; cursor:pointer;
  background: linear-gradient(135deg,rgba(52,211,153,0.7) 0%,rgba(99,179,237,0.7) 100%);
  color:#fff; transition:opacity 0.15s;
}}
.sam-hist-save:hover {{ opacity:0.85; }}
.sam-hist-save:disabled {{ opacity:0.4; cursor:not-allowed; }}
/* Streak ribbon */
.sam-hist-streak {{
  display:flex; gap:6px; flex-wrap:wrap; justify-content:center;
  margin-bottom:14px;
}}
.sam-hist-dot {{
  width:8px; height:8px; border-radius:50%;
  background:rgba(255,255,255,0.12);
  transition:background 0.2s;
}}
.sam-hist-dot.done {{ background:var(--green); }}
.sam-hist-dot.today {{ background:var(--amber); }}

/* ═══ WORK INTELLIGENCE ══════════════════════════════════════ */
.wi-pane {{ animation: wi-fade-in 0.18s ease; }}
@keyframes wi-fade-in {{ from {{ opacity:0; transform:translateY(5px); }} to {{ opacity:1; transform:none; }} }}
.wi-status-dot {{ display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:3px; background:var(--text-3); vertical-align:middle; }}
.wi-status-dot.active {{ background:var(--success); }}
.wi-status-dot.error  {{ background:var(--crimson); }}
.wi-status-dot.paused {{ background:#F59E0B; }}
.wi-signal-type {{ font-family:var(--font-mono); font-size:9px; letter-spacing:0.1em; text-transform:uppercase; color:var(--hue); background:var(--hue-dim); padding:2px 6px; border-radius:4px; white-space:nowrap; flex-shrink:0; }}
.wi-priority-ring {{ display:inline-block; width:8px; height:8px; border-radius:50%; flex-shrink:0; }}
.wi-priority-ring.p1 {{ background:var(--crimson); box-shadow:0 0 0 2px rgba(239,68,68,0.25); }}
.wi-priority-ring.p2 {{ background:#F59E0B; box-shadow:0 0 0 2px rgba(245,158,11,0.25); }}
.wi-priority-ring.p3 {{ background:var(--success); }}
.wi-complete-btn {{ padding:3px 10px; font-size:10px; background:var(--glass-1,rgba(255,255,255,0.06)); border:1px solid var(--border); border-radius:6px; cursor:pointer; color:var(--text-2); transition:background 0.15s,color 0.15s; white-space:nowrap; flex-shrink:0; }}
.wi-complete-btn:hover {{ background:var(--success); color:#fff; border-color:var(--success); }}
.wi-refresh-btn {{ padding:4px 12px; font-size:10px; background:var(--glass-1,rgba(255,255,255,0.06)); border:1px solid var(--border); border-radius:6px; cursor:pointer; color:var(--text-2); transition:background 0.15s,color 0.15s; }}
.wi-refresh-btn:hover {{ background:var(--hue); color:#fff; border-color:var(--hue); }}
.wi-project-row {{ display:flex; align-items:flex-start; gap:10px; padding:10px 0; border-bottom:1px solid var(--border); }}
.wi-project-row:last-child {{ border-bottom:none; padding-bottom:0; }}
.wi-project-info {{ flex:1; min-width:0; }}
.wi-project-name {{ font-size:13px; font-weight:600; color:var(--text-1); }}
.wi-project-sub  {{ font-size:11px; color:var(--text-3); margin-top:2px; }}
.wi-project-badge {{ padding:2px 8px; font-size:9px; border-radius:10px; font-family:var(--font-mono); letter-spacing:0.06em; white-space:nowrap; }}
.wi-project-badge.on-track {{ background:rgba(16,185,129,0.15); color:var(--success); }}
.wi-project-badge.at-risk   {{ background:rgba(245,158,11,0.15); color:#F59E0B; }}
.wi-project-badge.active    {{ background:var(--hue-dim); color:var(--hue); }}
.wi-commit-row {{ display:flex; align-items:flex-start; gap:10px; padding:8px 0; border-bottom:1px solid var(--border); }}
.wi-commit-row:last-child {{ border-bottom:none; padding-bottom:0; }}
.wi-commit-text {{ flex:1; min-width:0; font-size:12px; color:var(--text-2); line-height:1.5; }}
.wi-commit-due  {{ font-size:10px; font-family:var(--font-mono); color:var(--text-3); white-space:nowrap; }}
.wi-commit-status {{ font-size:9px; padding:2px 7px; border-radius:10px; font-family:var(--font-mono); letter-spacing:0.06em; white-space:nowrap; }}
.wi-commit-status.open     {{ background:var(--hue-dim); color:var(--hue); }}
.wi-commit-status.overdue  {{ background:rgba(239,68,68,0.15); color:var(--crimson); }}
.wi-commit-status.on-track {{ background:rgba(16,185,129,0.15); color:var(--success); }}
.wi-surface-item {{ padding:8px 0; border-bottom:1px solid var(--border); }}
.wi-surface-item:last-child {{ border-bottom:none; padding-bottom:0; }}
.wi-surface-title {{ font-size:12px; color:var(--text-1); font-weight:500; }}
.wi-surface-reason {{ font-size:11px; color:var(--text-3); margin-top:2px; }}

/* ═══════════════════════════════════════════════════════════════
   NAVIGATION / WAZE
═══════════════════════════════════════════════════════════════ */
.nav-container {{
  display: flex;
  flex-direction: row;
  height: calc(100vh - 120px);
  overflow: hidden;
}}
.nav-sidebar {{
  width: 380px;
  min-width: 320px;
  overflow-y: auto;
  border-right: 1px solid var(--border);
  background: rgba(255,255,255,0.03);
  display: flex;
  flex-direction: column;
  gap: 0;
}}
.nav-map-pane {{
  flex: 1;
  position: relative;
  overflow: hidden;
}}
#nav-map {{
  width: 100%;
  height: 100%;
  min-height: 400px;
  background: #1a1a2e;
}}
.nav-route-inputs {{
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-bottom: 1px solid var(--border);
}}
.nav-input-row {{
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
}}
.nav-input {{
  flex: 1;
  background: rgba(255,255,255,0.06);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-1);
  padding: 8px 12px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}}
.nav-input:focus {{
  border-color: var(--accent);
}}
.nav-autocomplete-results {{
  position: absolute;
  top: 100%;
  left: 24px;
  right: 0;
  background: #1e2030;
  border: 1px solid var(--border);
  border-radius: 8px;
  z-index: 1000;
  max-height: 200px;
  overflow-y: auto;
}}
.nav-autocomplete-item {{
  padding: 8px 12px;
  font-size: 12px;
  color: var(--text-1);
  cursor: pointer;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}}
.nav-autocomplete-item:hover {{
  background: rgba(255,255,255,0.08);
}}
.nav-swap-btn {{
  background: rgba(255,255,255,0.08);
  border: 1px solid var(--border);
  border-radius: 50%;
  width: 34px;
  height: 34px;
  color: var(--text-1);
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.2s;
}}
.nav-swap-btn:hover {{
  background: rgba(255,255,255,0.15);
}}
.nav-go-btn {{
  flex: 1;
  background: var(--accent);
  border: none;
  border-radius: 8px;
  color: #000;
  font-size: 13px;
  font-weight: 600;
  padding: 8px 16px;
  cursor: pointer;
  transition: opacity 0.2s;
}}
.nav-go-btn:hover {{
  opacity: 0.85;
}}
.nav-poi-toggles {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}}
.nav-poi-toggle {{
  background: rgba(255,255,255,0.06);
  border: 1px solid var(--border);
  border-radius: 20px;
  color: var(--text-2);
  font-size: 11px;
  padding: 4px 10px;
  cursor: pointer;
  transition: all 0.2s;
}}
.nav-poi-toggle.active[data-cat="food"] {{ background: rgba(255,107,53,0.25); border-color: #FF6B35; color: #FF6B35; }}
.nav-poi-toggle.active[data-cat="starbucks"] {{ background: rgba(0,112,74,0.25); border-color: #00704A; color: #00704A; }}
.nav-poi-toggle.active[data-cat="parks"] {{ background: rgba(45,106,79,0.25); border-color: #2D6A4F; color: #2D6A4F; }}
.nav-poi-toggle.active[data-cat="historic"] {{ background: rgba(201,168,76,0.25); border-color: #C9A84C; color: #C9A84C; }}
.nav-poi-toggle.active[data-cat="family"] {{ background: rgba(123,45,139,0.25); border-color: #7B2D8B; color: #7B2D8B; }}
.nav-poi-toggle.active[data-cat="gas"] {{ background: rgba(33,150,243,0.25); border-color: #2196F3; color: #2196F3; }}
.nav-summary-bar {{
  display: flex;
  flex-direction: row;
  gap: 0;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}}
.nav-stat {{
  flex: 1;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 2px;
}}
.nav-stat span {{
  font-size: 15px;
  font-weight: 600;
  color: var(--text-1);
}}
.nav-stat label {{
  font-size: 10px;
  color: var(--text-3);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}}
.nav-section-title {{
  font-size: 10px;
  font-weight: 600;
  color: var(--text-3);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  padding: 10px 16px 4px;
}}
.nav-turn-card {{
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}}
.nav-turn-icon {{
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(0,212,255,0.15);
  border: 1px solid rgba(0,212,255,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
  color: var(--accent);
}}
.nav-poi-card {{
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}}
.nav-poi-distance-chip {{
  background: rgba(0,212,255,0.12);
  border: 1px solid rgba(0,212,255,0.25);
  border-radius: 12px;
  font-size: 10px;
  color: var(--accent);
  padding: 2px 8px;
  white-space: nowrap;
  flex-shrink: 0;
}}
/* Mobile HUD */
.nav-hud {{
  position: absolute;
  top: 0; left: 0; right: 0;
  background: rgba(15,20,40,0.92);
  backdrop-filter: blur(8px);
  padding: 16px 20px;
  z-index: 200;
}}
.nav-hud-turn {{
  font-size: 40px;
  line-height: 1;
  color: var(--accent);
  min-width: 48px;
  text-align: center;
}}
.nav-hud-distance {{
  font-size: 32px;
  font-weight: 700;
  color: var(--text-1);
  line-height: 1;
}}
.nav-hud-instruction {{
  font-size: 14px;
  color: var(--text-2);
  margin-top: 4px;
}}
.nav-eta-strip {{
  position: absolute;
  bottom: 0; left: 0; right: 0;
  background: rgba(15,20,40,0.9);
  padding: 10px 20px;
  font-size: 13px;
  color: var(--text-2);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  z-index: 200;
}}
.nav-poi-alert {{
  position: absolute;
  bottom: 80px; left: 16px; right: 16px;
  background: rgba(20,25,45,0.95);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 300;
  transform: translateY(160px);
  transition: transform 0.35s cubic-bezier(0.34,1.56,0.64,1);
}}
.nav-poi-alert.visible {{
  transform: translateY(0);
}}
.nav-voice-btn {{
  position: absolute;
  top: 12px; right: 12px;
  background: rgba(255,255,255,0.1);
  border: 1px solid var(--border);
  border-radius: 50%;
  width: 40px; height: 40px;
  font-size: 18px;
  cursor: pointer;
  z-index: 250;
  display: flex;
  align-items: center;
  justify-content: center;
}}
.nav-start-btn, .nav-stop-btn {{
  position: absolute;
  bottom: 56px; left: 50%;
  transform: translateX(-50%);
  background: var(--accent);
  color: #000;
  font-weight: 700;
  font-size: 14px;
  border: none;
  border-radius: 24px;
  padding: 12px 32px;
  cursor: pointer;
  z-index: 250;
  white-space: nowrap;
}}
.nav-stop-btn {{
  background: #ef4444;
  color: #fff;
}}
@media (max-width: 768px) {{
  .nav-sidebar {{
    display: none;
  }}
  .nav-map-pane {{
    width: 100%;
  }}
}}
/* Aerial view modal close on outside click handled by JS */
#nav-aerial-modal video {{
    max-height: 70vh;
    object-fit: cover;
}}
#nav-sv-panel img {{
    object-fit: cover;
    height: 140px;
    width: 100%;
}}
.nav-sv-label {{
    font-size: 10px;
    text-transform: uppercase;
    opacity: 0.5;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
}}
.nav-radius-row {{
    padding: 8px 12px 4px;
    border-top: 1px solid rgba(255,255,255,0.06);
    margin-top: 4px;
}}
.nav-radius-slider {{
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
    height: 4px;
    border-radius: 2px;
    background: linear-gradient(to right, #4CAF50 0%, #4CAF50 25%, rgba(255,255,255,0.15) 25%);
    outline: none;
    cursor: pointer;
}}
.nav-radius-slider::-webkit-slider-thumb {{
    -webkit-appearance: none;
    appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #4CAF50;
    border: 2px solid #fff;
    cursor: pointer;
    box-shadow: 0 0 6px rgba(76,175,80,0.6);
}}
.nav-radius-slider::-moz-range-thumb {{
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #4CAF50;
    border: 2px solid #fff;
    cursor: pointer;
}}
/* NPS park card in sidebar */
.nav-nps-card {{
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 10px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    cursor: pointer;
    transition: background 0.15s;
}}
.nav-nps-card:hover {{
    background: rgba(255,255,255,0.04);
}}
.nav-nps-badge {{
    font-size: 10px;
    background: rgba(45,106,79,0.4);
    color: #81C784;
    border: 1px solid rgba(45,106,79,0.6);
    border-radius: 4px;
    padding: 1px 5px;
    white-space: nowrap;
}}
@keyframes spin {{
    to {{ transform: rotate(360deg); }}
}}
.nav-home-btn {{
    flex: 1;
    padding: 6px 10px;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    color: rgba(255,255,255,0.8);
    font-size: 12px;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
    white-space: nowrap;
}}
.nav-home-btn:hover {{
    background: rgba(255,255,255,0.13);
    border-color: rgba(255,255,255,0.25);
}}
/* ═══════════════════════════════════════════════════════════════
   END NAVIGATION CSS
═══════════════════════════════════════════════════════════════ */

  </style>
  <script src="https://cdn.jsdelivr.net/npm/hls.js@latest/dist/hls.min.js"></script>
</head>
<body>

<!-- ═══════════════════════════════════════════════════════════════════
     NAV BAR
══════════════════════════════════════════════════════════════════════ -->
<!-- Mobile hamburger button -->
<button class="nav-hamburger" id="nav-hamburger" onclick="toggleMobileNav()" aria-label="Menu">☰</button>
<!-- Mobile nav drawer backdrop -->
<div id="nav-drawer-overlay" onclick="closeMobileNav()"></div>

<nav class="nav-bar">
  <div style="display:flex;align-items:center;justify-content:space-between;padding:18px 12px 16px;">
    <span class="nav-wordmark" style="padding:0;border:none;">J·A·R·V·I·S</span>
    <button onclick="closeMobileNav()" id="nav-close-btn" style="display:none;background:none;border:none;color:var(--text-2);font-size:18px;cursor:pointer;padding:4px;">✕</button>
  </div>

  <div class="nav-tabs" id="nav-tabs">
    <button class="nav-tab" data-view="chat" onclick="switchView('chat')">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 2h12v9H9l-3 3v-3H2z"/></svg>
      Chat
    </button>
    <button class="nav-tab" data-view="overview" onclick="switchView('overview')">
      <svg viewBox="0 0 16 16" fill="currentColor"><rect x="1" y="1" width="6" height="6" rx="1"/><rect x="9" y="1" width="6" height="6" rx="1"/><rect x="1" y="9" width="6" height="6" rx="1"/><rect x="9" y="9" width="6" height="6" rx="1"/></svg>
      Overview
    </button>
    <button class="nav-tab" data-view="notifications" onclick="switchView('notifications')">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 2a3 3 0 0 1 3 3v1.5c0 .8.3 1.5.8 2.1l.9 1V11H3.3V9.6l.9-1A3.2 3.2 0 0 0 5 6.5V5a3 3 0 0 1 3-3z"/><path d="M6.5 13a1.5 1.5 0 0 0 3 0"/></svg>
      Notifications
    </button>
    <button class="nav-tab" data-view="dining" onclick="switchView('dining')">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M5 2v5a3 3 0 0 0 6 0V2M8 9v5M6 14h4"/></svg>
      Dining
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
    <button class="nav-tab" data-view="faith" onclick="switchView('faith')">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 2v12M2 8h12" stroke-linecap="round"/></svg>
      Faith
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
    <button class="nav-tab" data-view="health" onclick="switchView('health')">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
      HEALTH
    </button>
    <button class="nav-tab" data-view="news" onclick="switchView('news')">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1" y="2" width="14" height="12" rx="1.5"/><path d="M4 6h8M4 9h5"/></svg>
      News
    </button>
    <button class="nav-tab" data-view="home" onclick="switchView('home')">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
      Home
    </button>
    <button class="nav-tab" data-view="navigate" onclick="switchView('navigate')">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>
      Navigate
    </button>
    <button class="nav-tab" data-view="journey" onclick="switchView('journey')">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12h18M3 6h18M3 18h18"/><circle cx="8" cy="12" r="2" fill="currentColor" stroke="none"/></svg>
      Journey
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
        <div class="chat-empty-icon">🤖</div>
        <div class="chat-empty-text">JARVIS Agent — build, troubleshoot, run code</div>
        <div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:20px;">
          <button class="glass-btn" style="font-size:12px;padding:8px 14px;" onclick="setCmd('What is the current state of the JARVIS codebase?');sendCmd();">🔍 Codebase status</button>
          <button class="glass-btn" style="font-size:12px;padding:8px 14px;" onclick="setCmd('Run the JARVIS test suite and fix any failures');sendCmd();">🧪 Run tests</button>
          <button class="glass-btn" style="font-size:12px;padding:8px 14px;" onclick="setCmd('Show me recent git changes and summarize what was built');sendCmd();">📋 Recent changes</button>
          <button class="glass-btn" style="font-size:12px;padding:8px 14px;" onclick="setCmd('Check which services are running and their health');sendCmd();">🌡 Service health</button>
          <button class="glass-btn" style="font-size:12px;padding:8px 14px;" onclick="setCmd('Search the JARVIS codebase for TODO and FIXME comments');sendCmd();">📌 Find TODOs</button>
        </div>
        <div style="margin-top:16px;font-size:11px;color:rgba(255,255,255,0.25);">slash commands: /clear /memory /context /tools /restart /undo</div>
      </div>
    </div>
  </div>

  <!-- ── OVERVIEW ──────────────────────────────────────────────── -->
  <div id="view-overview" class="view">
    <div class="view-header">
      <div class="view-title">
        OVERVIEW
        <div class="view-title-line"></div>
      </div>
      <div class="view-subtitle" id="overview-subtitle">Tactical Command Dashboard · S.H.I.E.L.D. Priority View</div>
      <div id="overview-greeting" style="font-size:12px;color:rgba(255,255,255,0.45);margin-top:4px;letter-spacing:0.05em;"></div>
    </div>

    <!-- Mode Bar -->
    <div class="overview-mode-bar" id="overview-mode-bar">
      <button class="mode-pill" data-mode="morning_brief" onclick="setLayoutMode('morning_brief')">
        🌅 Morning Brief
      </button>
      <button class="mode-pill" data-mode="lunch_brief" onclick="setLayoutMode('lunch_brief')">
        ☀️ Lunch Brief
      </button>
      <button class="mode-pill" data-mode="daily_recap" onclick="setLayoutMode('daily_recap')">
        🌙 Daily Recap
      </button>
      <span class="mode-auto-chip" id="mode-auto-chip">AUTO</span>
      <span class="mode-clock" id="mode-clock">—</span>
    </div>

    <!-- Alert Banner (hidden by default) -->
    <div class="overview-alert-banner" id="overview-alert-banner" style="display:none;">
      <span id="alert-banner-icon">⚠️</span>
      <span class="alert-banner-msg" id="alert-banner-msg"></span>
      <button class="alert-banner-action" id="alert-banner-action-btn" onclick="alertBannerNavigate()">View →</button>
      <button class="alert-banner-dismiss" onclick="dismissAlertBanner()">✕</button>
    </div>

    <!-- User Identity Bar (shown when non-Chris user is active) -->
    <div id="overview-user-bar" style="display:none;margin-bottom:12px;padding:8px 14px;background:rgba(0,212,255,0.07);border:1px solid rgba(0,212,255,0.18);border-radius:10px;align-items:center;gap:10px;font-size:12px;">
      <span id="overview-user-avatar" style="font-size:20px;line-height:1;"></span>
      <div style="flex:1;min-width:0;">
        <div id="overview-user-name" style="font-weight:600;color:var(--text-1);"></div>
        <div id="overview-user-role" style="font-size:10px;color:var(--text-3);"></div>
      </div>
      <button onclick="switchUser()" style="background:none;border:1px solid rgba(255,255,255,0.2);border-radius:6px;color:var(--text-2);padding:4px 12px;font-size:11px;cursor:pointer;white-space:nowrap;">Switch User</button>
    </div>

    <!-- Family Presence Bar (who's online right now) -->
    <div id="overview-family-bar" style="display:none;margin-bottom:12px;"></div>

    <!-- Stats Strip -->
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

    <!-- Hero Zone (cockpit: two equal cards side-by-side) -->
    <div class="overview-hero-zone" id="overview-hero-zone">
      <!-- populated by applyLayout() -->
    </div>

    <!-- Priority Strip (3-column) -->
    <div class="overview-priority-strip" id="overview-priority-strip">
      <!-- populated by applyLayout() -->
    </div>

    <!-- Ambient Row (compact tiles) -->
    <div class="overview-ambient-row" id="overview-ambient-row">
      <!-- populated by applyLayout() -->
    </div>

  </div>

  <!-- ── NOTIFICATIONS ───────────────────────────────────────── -->
  <div id="view-notifications" class="view" style="display:none;">
    <div class="view-header">
      <div class="view-title">NOTIFICATION CENTER<div class="view-title-line"></div></div>
      <div class="view-subtitle">Shared household attention, event spine, and actionable alerts</div>
    </div>

    <div class="stats-strip" style="grid-template-columns:repeat(3,1fr);margin-bottom:16px;">
      <div class="card stat-tile accent">
        <div class="stat-label">Pending</div>
        <div class="stat-value" id="notif-stat-pending">—</div>
        <div class="stat-sub">needs triage</div>
      </div>
      <div class="card stat-tile">
        <div class="stat-label">Visible</div>
        <div class="stat-value" id="notif-stat-active">—</div>
        <div class="stat-sub">in inbox</div>
      </div>
      <div class="card stat-tile">
        <div class="stat-label">Recent Events</div>
        <div class="stat-value" id="notif-stat-events">—</div>
        <div class="stat-sub">event spine</div>
      </div>
    </div>

    <div class="card-grid-2">
      <div class="card">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">Inbox</span>
            <button class="btn-ghost" style="font-size:10px;padding:3px 8px;" onclick="loadNotificationCenter()">Refresh ↻</button>
          </div>
          <div id="notification-center-list">
            <div class="list-row"><div class="list-row-name" style="color:var(--text-3);">Loading notifications…</div></div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Event Spine</span></div>
          <div id="notification-event-list">
            <div class="list-row"><div class="list-row-name" style="color:var(--text-3);">Loading events…</div></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── DINING ─────────────────────────────────────────────────── -->
  <div id="view-dining" class="view">
    <div class="view-header">
      <div class="view-title">DINING<div class="view-title-line"></div></div>
      <div class="view-subtitle">Sam's picks · Nearby restaurants · Favorites</div>
    </div>

    <!-- Filter bar -->
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px;align-items:center;">
      <select id="dining-cuisine-filter" onchange="reloadDiningView()"
        style="padding:6px 12px;border:1px solid var(--border);border-radius:8px;background:var(--surface-hi);color:var(--text-1);font-size:12px;">
        <option value="any">All Cuisines</option>
        <option value="american">American</option>
        <option value="mexican">Mexican</option>
        <option value="italian">Italian</option>
        <option value="chinese">Chinese</option>
        <option value="japanese">Japanese / Sushi</option>
        <option value="barbecue">BBQ</option>
        <option value="breakfast">Breakfast</option>
        <option value="pizza">Pizza</option>
        <option value="burgers">Burgers</option>
        <option value="seafood">Seafood</option>
        <option value="steak">Steakhouse</option>
        <option value="thai">Thai</option>
        <option value="indian">Indian</option>
      </select>
      <label style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-2);cursor:pointer;">
        <input type="checkbox" id="dining-open-now" onchange="reloadDiningView()" style="accent-color:var(--hue);">
        Open now
      </label>
      <select id="dining-radius-filter" onchange="reloadDiningView()"
        style="padding:6px 12px;border:1px solid var(--border);border-radius:8px;background:var(--surface-hi);color:var(--text-1);font-size:12px;">
        <option value="5">Within 5 mi</option>
        <option value="10" selected>Within 10 mi</option>
        <option value="20">Within 20 mi</option>
      </select>
      <select id="dining-rating-filter" onchange="reloadDiningView()"
        style="padding:6px 12px;border:1px solid var(--border);border-radius:8px;background:var(--surface-hi);color:var(--text-1);font-size:12px;">
        <option value="3.5">3.5★+</option>
        <option value="4.0" selected>4.0★+</option>
        <option value="4.5">4.5★+</option>
      </select>
      <button class="btn-ghost" style="margin-left:auto;font-size:11px;" onclick="loadDiningFavorites()">❤ Favorites</button>
    </div>

    <!-- Sam recommendation strip -->
    <div class="card" style="margin-bottom:18px;" id="dining-sam-strip">
      <div class="card-inner">
        <div class="card-header"><span class="card-icon">🦅</span><span class="card-title">SAM'S PICKS RIGHT NOW</span></div>
        <div id="dining-sam-picks" style="padding:8px 0;">
          <div class="skel" style="height:10px;width:60%;margin-bottom:6px;"></div>
          <div class="skel" style="height:10px;width:40%;"></div>
        </div>
      </div>
    </div>

    <!-- Results grid -->
    <div id="dining-results" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px;">
    </div>

    <!-- Favorites panel (hidden by default) -->
    <div id="dining-favorites-panel" style="display:none;margin-top:20px;">
      <div class="card"><div class="card-inner">
        <div class="card-header"><span class="card-icon">❤</span><span class="card-title">SAVED FAVORITES</span></div>
        <div id="dining-favorites-list" style="padding:8px 0;"></div>
      </div></div>
    </div>

    <!-- Detail sheet (modal) -->
    <div id="dining-detail-sheet" style="display:none;position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.6);backdrop-filter:blur(4px);align-items:flex-end;justify-content:center;"
         onclick="if(event.target===this)closeDiningDetail()">
      <div style="background:var(--surface);border-radius:20px 20px 0 0;padding:24px;width:100%;max-width:560px;max-height:80vh;overflow-y:auto;" id="dining-detail-inner">
      </div>
    </div>
  </div><!-- #view-dining -->

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
            <input type="file" id="forge-view-capture-input" style="display:none" accept="image/*" multiple
                   onchange="forgeHandleViewCaptureFiles(this.files, this._pendingViewType)">
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
            <button id="forge-build-3d-btn" class="forge-action-btn primary"
              style="display:none;margin-top:8px;width:100%;font-size:12px;"
              onclick="forgeTriggerReconstruct()">🧊 Build 3D Model</button>
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

          <!-- WoW Model Bridge panel -->
          <div class="forge-measurements-panel" id="forge-wow-panel" style="margin-top:8px;">
            <div class="forge-panel-title" style="cursor:pointer;" onclick="forgeWowToggle()">
              <span>⚔️ WoW Models</span>
              <span id="forge-wow-count" style="font-size:10px;color:var(--text-3);font-family:var(--font-mono);margin-left:6px;"></span>
              <button class="forge-action-btn" style="font-size:10px;padding:3px 8px;margin-left:auto;"
                onclick="event.stopPropagation();forgeWowRefresh()">Refresh</button>
            </div>
            <div id="forge-wow-body" style="display:none;margin-top:6px;">
              <div id="forge-wow-status-row" style="font-size:10px;font-family:var(--font-mono);color:var(--text-3);margin-bottom:8px;line-height:1.6;"></div>
              <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;">
                <input type="text" id="forge-wow-search" placeholder="Search models..."
                  style="flex:1;min-width:100px;padding:4px 8px;border:1px solid var(--border);border-radius:6px;background:var(--surface-hi);color:var(--text-1);font-size:11px;outline:none;"
                  oninput="forgeWowSearch(this.value)">
                <button class="forge-action-btn" style="font-size:10px;padding:3px 8px;"
                  onclick="forgeWowOpenSetup()">⚙ Setup</button>
              </div>
              <div id="forge-wow-model-list" style="max-height:180px;overflow-y:auto;display:flex;flex-direction:column;gap:4px;">
                <div style="color:var(--text-3);font-size:11px;font-family:var(--font-mono);">Click Refresh to scan export folder.</div>
              </div>
            </div>
          </div>

          <!-- WoW Setup modal -->
          <div id="forge-wow-setup-modal" class="forge-modal-overlay hidden">
            <div class="forge-modal" style="max-width:480px;">
              <div class="forge-modal-title">⚔️ WoW Model Bridge Setup</div>
              <div style="font-size:11px;color:var(--text-3);margin-bottom:14px;line-height:1.7;">
                <b>Step 1</b> — Download <a href="https://github.com/Kruithne/wow.export/releases/latest"
                  target="_blank" style="color:var(--hue);">wow.export</a> (free, macOS ARM64 native)<br>
                <b>Step 2</b> — Open it, connect to your WoW install, search your character/model<br>
                <b>Step 3</b> — Export as GLB — files land in your export folder<br>
                <b>Step 4</b> — Hit Refresh in Forge and click Import next to the model
              </div>
              <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:14px;">
                <label style="font-size:11px;color:var(--text-2);font-weight:600;">Export Folder (where wow.export saves files)</label>
                <input type="text" id="forge-wow-cfg-folder"
                  style="padding:6px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-hi);color:var(--text-1);font-size:11px;font-family:var(--font-mono);outline:none;width:100%;box-sizing:border-box;">
                <label style="font-size:11px;color:var(--text-2);font-weight:600;">WoW Install Path</label>
                <input type="text" id="forge-wow-cfg-wow"
                  style="padding:6px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-hi);color:var(--text-1);font-size:11px;font-family:var(--font-mono);outline:none;width:100%;box-sizing:border-box;">
                <label style="font-size:11px;color:var(--text-2);font-weight:600;">Blender Path (optional — for M2→GLB conversion)</label>
                <input type="text" id="forge-wow-cfg-blender"
                  style="padding:6px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-hi);color:var(--text-1);font-size:11px;font-family:var(--font-mono);outline:none;width:100%;box-sizing:border-box;">
              </div>
              <div style="display:flex;gap:8px;">
                <button class="forge-action-btn primary" onclick="forgeWowSaveConfig()">Save</button>
                <button class="forge-action-btn" onclick="document.getElementById('forge-wow-setup-modal').classList.add('hidden')">Cancel</button>
              </div>
            </div>
          </div>

          <!-- Forge Convert panel -->
          <div class="forge-measurements-panel" id="forge-convert-panel" style="margin-top:8px;">
            <div class="forge-panel-title" style="cursor:pointer;" onclick="forgeConvertToggle()">
              <span>🔧 Convert Tools</span>
              <button class="forge-action-btn" style="font-size:10px;padding:3px 8px;margin-left:auto;"
                onclick="event.stopPropagation();forgeConvertToggle()">▾</button>
            </div>
            <div id="forge-convert-body" style="display:none;margin-top:8px;">

              <!-- Format Converter -->
              <div style="margin-bottom:12px;">
                <div style="font-size:10px;font-weight:700;color:var(--text-2);text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px;">Format Converter</div>
                <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:6px;">
                  <select id="forge-conv-src-file"
                    style="flex:1;min-width:120px;padding:4px 8px;border:1px solid var(--border);border-radius:6px;background:var(--surface-hi);color:var(--text-1);font-size:11px;outline:none;">
                    <option value="">— pick project file —</option>
                  </select>
                  <select id="forge-conv-fmt"
                    style="width:68px;padding:4px 6px;border:1px solid var(--border);border-radius:6px;background:var(--surface-hi);color:var(--text-1);font-size:11px;outline:none;">
                    <option value="glb">GLB</option>
                    <option value="obj">OBJ</option>
                    <option value="stl">STL</option>
                    <option value="ply">PLY</option>
                  </select>
                  <button class="forge-action-btn" style="font-size:10px;padding:3px 10px;"
                    onclick="forgeConvertFormat()">Convert</button>
                </div>
                <div style="font-size:10px;color:var(--text-3);margin-bottom:4px;">or upload a file to convert:</div>
                <input type="file" id="forge-conv-upload-input" accept=".stl,.obj,.glb,.ply"
                  style="display:none;" onchange="forgeConvertFormatFromUpload(this)">
                <button class="forge-action-btn" style="font-size:10px;padding:3px 10px;width:100%;"
                  onclick="document.getElementById('forge-conv-upload-input').click()">Upload &amp; Convert</button>
              </div>

              <!-- WoW-specific tools -->
              <div style="margin-bottom:12px;padding-top:10px;border-top:1px solid var(--border);">
                <div style="font-size:10px;font-weight:700;color:var(--text-2);text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px;">WoW Tools</div>
                <div style="display:flex;gap:6px;flex-wrap:wrap;">
                  <a href="https://github.com/Kruithne/wow.export/releases/latest" target="_blank"
                    class="forge-action-btn" style="font-size:10px;padding:3px 10px;text-decoration:none;">
                    ⬇ Download wow.export
                  </a>
                  <button class="forge-action-btn" style="font-size:10px;padding:3px 10px;"
                    onclick="forgeConvertCheckBlender()">Check Blender Setup</button>
                </div>
                <div id="forge-conv-blender-result"
                  style="font-size:10px;font-family:var(--font-mono);color:var(--text-3);margin-top:6px;line-height:1.6;display:none;"></div>
              </div>

              <!-- Mesh Repair -->
              <div style="margin-bottom:12px;padding-top:10px;border-top:1px solid var(--border);">
                <div style="font-size:10px;font-weight:700;color:var(--text-2);text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px;">Mesh Repair</div>
                <select id="forge-repair-src-file"
                  style="width:100%;padding:4px 8px;border:1px solid var(--border);border-radius:6px;background:var(--surface-hi);color:var(--text-1);font-size:11px;outline:none;margin-bottom:6px;">
                  <option value="">— pick project file —</option>
                </select>
                <div style="display:flex;gap:10px;margin-bottom:8px;flex-wrap:wrap;">
                  <label style="font-size:10px;color:var(--text-2);display:flex;align-items:center;gap:4px;cursor:pointer;">
                    <input type="checkbox" id="forge-repair-normals" checked> Fix Normals</label>
                  <label style="font-size:10px;color:var(--text-2);display:flex;align-items:center;gap:4px;cursor:pointer;">
                    <input type="checkbox" id="forge-repair-holes" checked> Fill Holes</label>
                  <label style="font-size:10px;color:var(--text-2);display:flex;align-items:center;gap:4px;cursor:pointer;">
                    <input type="checkbox" id="forge-repair-winding" checked> Fix Winding</label>
                </div>
                <button class="forge-action-btn primary" style="font-size:10px;padding:4px 14px;"
                  onclick="forgeConvertRepair()">Repair Mesh</button>
                <div id="forge-conv-repair-result"
                  style="font-size:10px;font-family:var(--font-mono);color:var(--text-3);margin-top:6px;line-height:1.6;display:none;"></div>
              </div>

              <!-- Scale & Unit Tools -->
              <div style="padding-top:10px;border-top:1px solid var(--border);">
                <div style="font-size:10px;font-weight:700;color:var(--text-2);text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px;">Scale &amp; Units</div>
                <select id="forge-scale-src-file"
                  style="width:100%;padding:4px 8px;border:1px solid var(--border);border-radius:6px;background:var(--surface-hi);color:var(--text-1);font-size:11px;outline:none;margin-bottom:6px;">
                  <option value="">— pick project file —</option>
                </select>
                <select id="forge-scale-op"
                  style="width:100%;padding:4px 8px;border:1px solid var(--border);border-radius:6px;background:var(--surface-hi);color:var(--text-1);font-size:11px;outline:none;margin-bottom:6px;"
                  onchange="forgeConvertScaleOpChange(this.value)">
                  <option value="rescale">Rescale to target size</option>
                  <option value="normalize_bbox">Normalize bounding box (unit cube)</option>
                  <option value="center_origin">Center on origin</option>
                </select>
                <div id="forge-scale-rescale-opts" style="display:flex;gap:6px;margin-bottom:6px;flex-wrap:wrap;align-items:center;">
                  <input type="number" id="forge-scale-target-size" value="100" min="0.001" step="0.1"
                    style="width:80px;padding:4px 8px;border:1px solid var(--border);border-radius:6px;background:var(--surface-hi);color:var(--text-1);font-size:11px;outline:none;">
                  <select id="forge-scale-target-unit"
                    style="width:60px;padding:4px 6px;border:1px solid var(--border);border-radius:6px;background:var(--surface-hi);color:var(--text-1);font-size:11px;outline:none;">
                    <option value="mm">mm</option>
                    <option value="cm">cm</option>
                    <option value="in">in</option>
                    <option value="m">m</option>
                  </select>
                  <span style="font-size:10px;color:var(--text-3);">src:</span>
                  <select id="forge-scale-current-unit"
                    style="width:60px;padding:4px 6px;border:1px solid var(--border);border-radius:6px;background:var(--surface-hi);color:var(--text-1);font-size:11px;outline:none;">
                    <option value="mm">mm</option>
                    <option value="cm">cm</option>
                    <option value="in">in</option>
                    <option value="m">m</option>
                  </select>
                </div>
                <button class="forge-action-btn primary" style="font-size:10px;padding:4px 14px;"
                  onclick="forgeConvertScale()">Apply Scale</button>
                <div id="forge-conv-scale-result"
                  style="font-size:10px;font-family:var(--font-mono);color:var(--text-3);margin-top:6px;line-height:1.6;display:none;"></div>
              </div>

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

  <!-- ── CATALYST / WORK INTELLIGENCE ───────────────────────── -->
  <div id="view-catalyst" class="view" data-domain="catalyst">
    <div class="view-header">
      <div class="view-title">WORK INTELLIGENCE<div class="view-title-line"></div></div>
      <div class="view-subtitle">Projects · Commitments · Briefings · Signals</div>
    </div>

    <!-- Stats strip -->
    <div class="stats-strip" style="grid-template-columns:repeat(4,1fr);">
      <div class="card stat-tile accent">
        <div class="stat-label">Active Projects</div>
        <div class="stat-value" id="wi-stat-projects">—</div>
      </div>
      <div class="card stat-tile accent">
        <div class="stat-label">Open Tasks</div>
        <div class="stat-value" id="wi-stat-tasks">—</div>
      </div>
      <div class="card stat-tile">
        <div class="stat-label">Overdue</div>
        <div class="stat-value" id="wi-stat-overdue" style="color:var(--crimson);">—</div>
      </div>
      <div class="card stat-tile">
        <div class="stat-label">Workers</div>
        <div class="stat-value" id="wi-stat-workers" style="font-size:13px;padding-top:4px;">—</div>
      </div>
    </div>

    <!-- Tab bar -->
    <div style="display:flex;gap:0;border-bottom:1px solid var(--border);margin-bottom:16px;overflow-x:auto;">
      <button class="launch-tab active" data-wi-tab="overview"  onclick="switchWITab(this,'overview')">🏠 Overview</button>
      <button class="launch-tab"        data-wi-tab="projects"  onclick="switchWITab(this,'projects')">📂 Projects</button>
      <button class="launch-tab"        data-wi-tab="tasks"     onclick="switchWITab(this,'tasks')">✅ Tasks</button>
      <button class="launch-tab"        data-wi-tab="briefing"  onclick="switchWITab(this,'briefing')">📋 Briefing</button>
      <button class="launch-tab"        data-wi-tab="signals"   onclick="switchWITab(this,'signals')">📡 Signals</button>
    </div>

    <!-- ── Overview pane ── -->
    <div id="wi-pane-overview" class="wi-pane">
      <div class="card-grid-2">
        <div class="card card-hi">
          <div class="card-inner">
            <div class="card-header">
              <span class="card-title">Today's ONE Recommendation</span>
              <span class="pill pill-hue">AI</span>
            </div>
            <div id="wi-one-rec" style="font-size:13px;line-height:1.7;color:var(--text-2);padding-top:4px;">
              <div class="skel" style="height:10px;width:90%;margin-bottom:6px;"></div>
              <div class="skel" style="height:10px;width:70%;"></div>
            </div>
          </div>
        </div>
        <div class="card card-hi">
          <div class="card-inner">
            <div class="card-header"><span class="card-title">Proactive Surfaces</span></div>
            <div id="wi-surfaces" style="font-size:12px;line-height:1.6;">
              <div class="skel" style="height:10px;width:80%;margin-bottom:6px;"></div>
              <div class="skel" style="height:10px;width:60%;"></div>
            </div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">Open Commitments</span>
            <span class="pill pill-hue" id="wi-commit-count">—</span>
          </div>
          <div id="wi-commitments">
            <div class="list-row"><div class="list-row-name" style="color:var(--text-3);">Loading…</div></div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Projects pane ── -->
    <div id="wi-pane-projects" class="wi-pane" style="display:none;">
      <div class="card">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">Active Projects</span>
            <span class="pill pill-hue" id="wi-proj-count">—</span>
          </div>
          <div id="wi-projects-list">
            <div class="list-row"><div class="list-row-name" style="color:var(--text-3);">Loading…</div></div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Tasks pane ── -->
    <div id="wi-pane-tasks" class="wi-pane" style="display:none;">
      <div class="card">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">Open Tasks</span>
            <span class="pill pill-hue" id="wi-tasks-count">—</span>
          </div>
          <div id="wi-tasks-list">
            <div class="list-row"><div class="list-row-name" style="color:var(--text-3);">Loading…</div></div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Briefing pane ── -->
    <div id="wi-pane-briefing" class="wi-pane" style="display:none;">
      <div class="card card-hi">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">Daily Briefing</span>
            <button class="wi-refresh-btn" onclick="wiRefreshBriefing()">↻ Refresh</button>
          </div>
          <div id="wi-briefing-content" style="font-size:13px;line-height:1.75;color:var(--text-2);">
            <div class="skel" style="height:10px;width:85%;margin-bottom:6px;"></div>
            <div class="skel" style="height:10px;width:70%;margin-bottom:6px;"></div>
            <div class="skel" style="height:10px;width:60%;"></div>
          </div>
          <div id="wi-briefing-meta" style="font-size:10px;color:var(--text-3);margin-top:10px;font-family:var(--font-mono);"></div>
        </div>
      </div>
    </div>

    <!-- ── Signals pane ── -->
    <div id="wi-pane-signals" class="wi-pane" style="display:none;">
      <div class="card">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">Recent Signals</span>
            <span class="pill pill-hue" id="wi-signals-count">—</span>
          </div>
          <div id="wi-signals-list">
            <div class="list-row"><div class="list-row-name" style="color:var(--text-3);">Loading…</div></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── FAITH ──────────────────────────────────────────────── -->
  <div id="view-faith" class="view">
    <div class="view-header">
      <div class="view-title">FAITH<div class="view-title-line"></div></div>
      <div class="view-subtitle" id="faith-subtitle">Your council of 11 — Scripture · Prayer · Formation · Apologetics</div>
    </div>

    <!-- Daily Word banner -->
    <div class="faith-daily-word card" id="faith-daily-word" style="margin-bottom:20px;display:none;">
      <div class="faith-dw-header">
        <span class="faith-dw-agent" id="faith-dw-agent">—</span>
        <span class="faith-dw-tag" id="faith-dw-tag">Daily Word</span>
      </div>
      <div class="faith-dw-body" id="faith-dw-body">—</div>
      <div class="faith-dw-passage" id="faith-dw-passage"></div>
    </div>

    <!-- Agent roster grid -->
    <div class="section-label" style="margin-bottom:12px;">Your Council</div>
    <div class="faith-roster" id="faith-roster">
      <div class="skel" style="height:120px;border-radius:12px;"></div>
      <div class="skel" style="height:120px;border-radius:12px;"></div>
      <div class="skel" style="height:120px;border-radius:12px;"></div>
    </div>

    <!-- Chat panel (hidden until agent selected) -->
    <div class="faith-chat-panel card" id="faith-chat-panel" style="display:none;margin-top:24px;">
      <div class="faith-chat-header">
        <div class="faith-chat-avatar" id="faith-chat-avatar"></div>
        <div>
          <div class="faith-chat-name" id="faith-chat-name">—</div>
          <div class="faith-chat-domain" id="faith-chat-domain">—</div>
        </div>
        <button class="btn btn-sm" style="margin-left:auto;" onclick="closeFaithChat()">✕ Close</button>
      </div>
      <div class="faith-chat-passage-row">
        <input class="faith-chat-passage-input" id="faith-chat-passage" type="text" placeholder="Passage (optional — e.g. John 1:14)…">
      </div>
      <div class="faith-chat-messages" id="faith-chat-messages"></div>
      <div class="faith-chat-input-row">
        <textarea class="faith-chat-textarea" id="faith-chat-input" rows="2"
          placeholder="Ask anything…"
          onkeydown="if(event.key==='Enter'&&!event.shiftKey){{event.preventDefault();faithSend();}}"></textarea>
        <button class="btn btn-hue btn-sm faith-send-btn" onclick="faithSend()" id="faith-send-btn">Send</button>
      </div>
    </div>
  </div>

  <!-- ── CHRONICLE ──────────────────────────────────────────── -->
  <div id="view-chronicle" class="view">
    <div class="view-header">
      <div class="view-title">CHRONICLE<div class="view-title-line"></div></div>
      <div class="view-subtitle">Entries · Prayer · Formation · Scripture</div>
    </div>

    <!-- Quick capture card -->
    <div class="chr-capture-card card" id="chr-capture-card">
      <div class="chr-capture-type-row" id="chr-capture-types">
        <button class="chr-capture-type active" data-type="note" onclick="setChrCaptureType(this,'note')">📝 Note</button>
        <button class="chr-capture-type" data-type="gratitude" onclick="setChrCaptureType(this,'gratitude')">🙏 Gratitude</button>
        <button class="chr-capture-type" data-type="prayer" onclick="setChrCaptureType(this,'prayer')">✦ Prayer</button>
        <button class="chr-capture-type" data-type="insight" onclick="setChrCaptureType(this,'insight')">💡 Insight</button>
        <button class="chr-capture-type" data-type="milestone" onclick="setChrCaptureType(this,'milestone')">🏆 Milestone</button>
      </div>
      <div class="chr-capture-input-row">
        <input class="chr-capture-input" id="chr-capture-input" type="text"
          placeholder="What's on your heart? Press Enter to capture…"
          onkeydown="if(event.key==='Enter')chrQuickCapture()">
        <input class="chr-capture-passage" id="chr-capture-passage" type="text"
          placeholder="Passage (optional)">
        <button class="btn btn-hue btn-sm" onclick="chrQuickCapture()" style="height:36px;padding:0 14px;flex-shrink:0;">Capture</button>
      </div>
    </div>

    <!-- Stats strip -->
    <div style="display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap;">
      <div class="card" style="flex:1;min-width:100px;padding:12px 16px;">
        <div style="font-size:10px;color:var(--text-3);letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px;">Entries</div>
        <div style="font-size:22px;font-weight:700;color:var(--text-1);" id="chronicle-total">—</div>
      </div>
      <div class="card" style="flex:1;min-width:100px;padding:12px 16px;">
        <div style="font-size:10px;color:var(--text-3);letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px;">Active Prayer</div>
        <div style="font-size:22px;font-weight:700;color:var(--hue);" id="chr-active-prayers">—</div>
      </div>
      <div class="card" style="flex:1;min-width:100px;padding:12px 16px;">
        <div style="font-size:10px;color:var(--text-3);letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px;">Answered</div>
        <div style="font-size:22px;font-weight:700;color:#3ecf8e;" id="chr-answered-prayers">—</div>
      </div>
      <div class="card" style="flex:1;min-width:100px;padding:12px 16px;">
        <div style="font-size:10px;color:var(--text-3);letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px;">Rhythms</div>
        <div style="font-size:22px;font-weight:700;color:var(--text-2);" id="chr-rhythms-count">—</div>
      </div>
    </div>

    <!-- Search -->
    <div class="search-wrap" style="margin-bottom:20px;">
      <svg class="search-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="6.5" cy="6.5" r="4"/><path d="M11 11l3 3"/>
      </svg>
      <input class="search-input" type="text" placeholder="Search entries, passages, themes…" id="chronicle-search"
             oninput="searchChronicle(this.value)">
    </div>

    <!-- Two-column layout -->
    <div style="display:grid;grid-template-columns:1fr 340px;gap:16px;align-items:start;">

      <!-- Left: Entry feed -->
      <div>
        <div class="section-label" style="display:flex;align-items:center;gap:8px;">
          Recent Entries
          <button class="btn btn-sm btn-hue" style="margin-left:auto;font-size:10px;" onclick="openBibleStudyModal()">✦ Bible Study</button>
        </div>
        <div id="chronicle-list">
          <div class="chr-entry-card"><div class="skel" style="height:12px;width:60%;margin-bottom:8px;"></div><div class="skel" style="height:10px;width:85%;"></div></div>
          <div class="chr-entry-card"><div class="skel" style="height:12px;width:45%;margin-bottom:8px;"></div><div class="skel" style="height:10px;width:70%;"></div></div>
        </div>
      </div>

      <!-- Right: Prayer + Formation sidebar -->
      <div>
        <div class="section-label">Prayer List</div>
        <div class="card" style="margin-bottom:16px;">
          <div class="card-inner" style="padding:0;">
            <div id="chr-prayer-list">
              <div style="padding:16px;color:var(--text-3);font-size:12px;">Loading…</div>
            </div>
          </div>
        </div>

        <div class="section-label">Formation Rhythms</div>
        <div class="card" style="margin-bottom:16px;">
          <div class="card-inner" style="padding:0;">
            <div id="chr-rhythms-list">
              <div style="padding:16px;color:var(--text-3);font-size:12px;">Loading…</div>
            </div>
          </div>
        </div>

        <div class="section-label">Themes</div>
        <div class="tag-cloud" id="tag-cloud" style="margin-bottom:0;">
          <div class="skel" style="height:24px;width:60px;border-radius:99px;"></div>
          <div class="skel" style="height:24px;width:80px;border-radius:99px;"></div>
        </div>
      </div>

    </div>

    <!-- Patterns section (Phase 5 foundation) -->
    <div style="margin-top:24px;">
      <div class="section-label" style="margin-bottom:12px;">30-Day Patterns</div>
      <div id="chr-patterns" class="card" style="padding:16px;">
        <div class="skel" style="height:80px;border-radius:8px;"></div>
      </div>
    </div>
  </div>

  <!-- ── PUBLISHING ─────────────────────────────────────────── -->
  <div id="view-publishing" class="view">
    <div class="view-header">
      <div class="view-title">PUBLISHING<div class="view-title-line"></div></div>
      <div class="view-subtitle" id="pub-subtitle">Ghostwritr Book Studio · Stage Pipeline · Pending Reviews</div>
    </div>

    <!-- Stats strip -->
    <div style="display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap;">
      <div class="card" style="flex:1;min-width:120px;padding:12px 16px;">
        <div style="font-size:10px;color:var(--text-3);letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px;">Books</div>
        <div style="font-size:22px;font-weight:700;color:var(--text-1);" id="homeProjectsBadge">—</div>
      </div>
      <div class="card" style="flex:1;min-width:120px;padding:12px 16px;">
        <div style="font-size:10px;color:var(--text-3);letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px;">Reviews</div>
        <div style="font-size:22px;font-weight:700;color:#f0b429;" id="pub-review-count">—</div>
      </div>
      <div class="card" style="flex:1;min-width:120px;padding:12px 16px;">
        <div style="font-size:10px;color:var(--text-3);letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px;">In Progress</div>
        <div style="font-size:22px;font-weight:700;color:var(--hue);" id="pub-inprogress-count">—</div>
      </div>
      <div class="card" style="flex:1;min-width:160px;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;">
        <div>
          <div style="font-size:10px;color:var(--text-3);letter-spacing:.06em;text-transform:uppercase;margin-bottom:2px;">Ghostwritr</div>
          <div style="font-size:12px;font-weight:500;" id="pub-gw-status">—</div>
        </div>
        <a href="http://localhost:3000" target="_blank" class="btn btn-sm" style="font-size:10px;text-decoration:none;white-space:nowrap;">Open Studio ↗</a>
      </div>
    </div>

    <!-- Pending Reviews — shown only if reviews exist -->
    <div id="pub-reviews-section" style="display:none;margin-bottom:20px;">
      <div class="section-label" style="display:flex;align-items:center;gap:8px;">
        Pending Reviews
        <span id="pub-review-count-badge" class="pill pill-gold" style="font-size:9px;">0</span>
      </div>
      <div class="card card-needs-you">
        <div class="card-inner" style="padding:0;">
          <div id="publishing-reviews"></div>
        </div>
      </div>
    </div>

    <!-- Book Pipeline -->
    <div class="section-label">Book Pipeline</div>
    <div id="publishing-books">
      <!-- Skeleton while loading -->
      <div class="pub-book-card">
        <div class="skel" style="height:14px;width:55%;margin-bottom:10px;"></div>
        <div class="skel" style="height:4px;width:100%;margin-bottom:14px;"></div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
          <div class="skel" style="height:60px;border-radius:8px;"></div>
          <div class="skel" style="height:60px;border-radius:8px;"></div>
          <div class="skel" style="height:60px;border-radius:8px;"></div>
          <div class="skel" style="height:60px;border-radius:8px;"></div>
        </div>
      </div>
    </div>

    <!-- Book Launch Campaign Panel -->
    <div class="section-label" style="margin-top:24px;">
      Book Launch
      <button class="card-badge" style="margin-left:auto;cursor:pointer;padding:3px 10px;font-size:10px;"
        onclick="loadLaunchPanel()">↺ Scan</button>
    </div>
    <div class="card card-tactical" style="margin-bottom:20px;">
      <div class="card-hdr">
        <span class="card-title">LAUNCH ASSETS</span>
        <span class="card-badge" id="launch-books-badge">—</span>
      </div>
      <div class="card-inner" style="padding-top:8px;">
        <div id="publishing-launch-books">
          <div class="loading-state" style="text-align:left;padding:12px 0;font-size:12px;color:var(--text-3);">
            Connect Ghostwritr and click Scan to see your books here.
          </div>
        </div>
      </div>
    </div>

    <!-- Asset Viewer (shown when a book is expanded) -->
    <div id="publishing-launch-assets" style="display:none;margin-bottom:20px;">
      <div class="card">
        <div class="card-hdr" style="align-items:center;gap:12px;">
          <span class="card-title" id="launch-asset-title">Launch Assets</span>
          <div style="margin-left:auto;display:flex;gap:8px;">
            <button class="btn btn-sm" style="font-size:10px;" onclick="regenerateLaunchAssets()">↺ Regenerate</button>
            <button class="btn btn-sm" style="font-size:10px;" onclick="document.getElementById('publishing-launch-assets').style.display='none'">✕ Close</button>
          </div>
        </div>
        <!-- Tab strip -->
        <div style="display:flex;gap:2px;padding:0 16px;border-bottom:1px solid var(--border);overflow-x:auto;">
          <button class="launch-tab active" data-tab="dispatch"   onclick="switchLaunchTab(this,'dispatch')">📣 Dispatch</button>
          <button class="launch-tab"         data-tab="bureau"    onclick="switchLaunchTab(this,'bureau')">📰 Bureau</button>
          <button class="launch-tab"         data-tab="marquee"   onclick="switchLaunchTab(this,'marquee')">🏷️ Marquee</button>
          <button class="launch-tab"         data-tab="studio"    onclick="switchLaunchTab(this,'studio')">🎙️ Studio</button>
          <button class="launch-tab"         data-tab="podium"    onclick="switchLaunchTab(this,'podium')">🎓 Podium</button>
          <button class="launch-tab"         data-tab="lectern"   onclick="switchLaunchTab(this,'lectern')">🎤 Lectern</button>
          <button class="launch-tab"         data-tab="twitter"   onclick="switchLaunchTab(this,'twitter')">𝕏 Quick Social</button>
          <button class="launch-tab"         data-tab="amazon"    onclick="switchLaunchTab(this,'amazon')">Quick Amazon</button>
          <button class="launch-tab"         data-tab="extended"  onclick="switchLaunchTab(this,'extended')">Extended</button>
        </div>
        <div id="launch-asset-content" class="card-inner" style="padding-top:16px;min-height:120px;">
          <!-- populated by viewLaunchAssets() -->
        </div>
      </div>
    </div>

    <!-- KDP Section -->
    <div class="view-section" style="margin-top:24px;">
      <div class="section-title-row">
        <h2 class="section-title">KDP · AMAZON PUBLISHING</h2>
        <div style="display:flex;gap:8px;align-items:center;">
          <span id="kdp-view-status" style="font-size:11px;color:var(--text-3);">—</span>
          <button class="card-action-btn" onclick="kdpViewSync()" id="kdp-sync-btn">↻ Sync</button>
        </div>
      </div>

      <!-- Stats strip -->
      <div class="stats-strip" id="kdp-stats-strip">
        <div class="stat-tile"><div class="stat-value" id="kdp-stat-books">—</div><div class="stat-label">Books</div></div>
        <div class="stat-tile"><div class="stat-value" id="kdp-stat-units">—</div><div class="stat-label">Units Sold</div></div>
        <div class="stat-tile"><div class="stat-value" id="kdp-stat-kenp">—</div><div class="stat-label">KENP Reads</div></div>
        <div class="stat-tile"><div class="stat-value" id="kdp-stat-royalties">—</div><div class="stat-label">Royalties</div></div>
      </div>

      <!-- Insights -->
      <div id="kdp-insights" style="margin:16px 0;display:none;">
        <div class="section-title-row"><h3 style="font-size:11px;font-family:var(--font-mono);text-transform:uppercase;color:var(--text-3);letter-spacing:.08em;">Insights</h3></div>
        <div id="kdp-insights-list"></div>
      </div>

      <!-- Books table -->
      <div id="kdp-books-section" style="display:none;">
        <div class="section-title-row"><h3 style="font-size:11px;font-family:var(--font-mono);text-transform:uppercase;color:var(--text-3);letter-spacing:.08em;">Your Books</h3></div>
        <div id="kdp-books-list"></div>
      </div>

      <!-- Not configured state -->
      <div id="kdp-not-configured" style="text-align:center;padding:40px 20px;color:var(--text-3);">
        <div style="font-size:32px;margin-bottom:12px;">📚</div>
        <div style="font-size:14px;color:var(--text-2);margin-bottom:8px;">KDP not connected</div>
        <div style="font-size:12px;margin-bottom:16px;">Add your Amazon credentials in Settings → Accounts → KDP</div>
        <button class="card-action-btn" onclick="openSettings();settingsNavTo('accounts')">Open Settings</button>
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
      <div style="display:flex;gap:8px;margin-bottom:8px;">
        <input type="text" id="huddle-idea-input"
          placeholder="Describe an idea — JARVIS will research it and return a full dossier..."
          style="flex:1;padding:10px 14px;border:1px solid var(--border);border-radius:8px;background:var(--surface-hi);font-size:13px;color:var(--text-1);outline:none;"
          onkeydown="if(event.key==='Enter')huddleAddIdea()"
          onfocus="this.style.borderColor='var(--hue)'"
          onblur="this.style.borderColor='var(--border)'">
        <button class="btn-primary" onclick="huddleAddIdea()">Capture</button>
      </div>

      <!-- Bulk import row -->
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">
        <input type="file" id="huddle-bulk-import-input" accept=".docx,.txt,.md,.json,.csv"
          style="display:none;" onchange="huddleBulkImport(this)">
        <button class="party-bar-btn" style="font-size:11px;padding:4px 12px;"
          onclick="document.getElementById('huddle-bulk-import-input').click()">
          📄 Import from File
        </button>
        <select id="huddle-bulk-domain"
          style="padding:4px 8px;border:1px solid var(--border);border-radius:6px;background:var(--surface-hi);color:var(--text-1);font-size:11px;outline:none;">
          <option value="passive-income">Passive Income</option>
          <option value="publishing">Publishing / Books</option>
          <option value="software">Software</option>
          <option value="creative">Creative</option>
          <option value="personal">Personal</option>
          <option value="general">General</option>
        </select>
        <span style="font-size:10px;color:var(--text-3);">.docx · .txt · .md · .json</span>
        <div id="huddle-bulk-status" style="font-size:11px;color:var(--text-3);display:none;margin-left:4px;"></div>
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
      <div class="view-subtitle">
        Live Runtime · What Every Agent Is Doing Right Now
        <span id="agent-roster-count" style="margin-left:12px;font-family:var(--font-mono);font-size:10px;color:var(--hue);background:var(--hue-dim);padding:2px 8px;border-radius:10px;vertical-align:middle;">— agents</span>
      </div>
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
        <div style="font-size:10px;color:var(--text-3);margin-top:4px;padding-left:18px;">
          MCP: <span id="mcp-status" style="color:var(--amber);">checking…</span>
          <span style="margin-left:8px;cursor:pointer;" onclick="checkMcpStatus()" title="Refresh MCP">↺</span>
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

  <!-- ═══════════════════════════════════════════════════════ HEALTH VIEW ═══ -->
  <div id="view-health" class="view" style="display:none;">
    <div class="view-header">
      <div class="view-title">HEALTH INTELLIGENCE</div>
      <div style="display:flex;align-items:center;gap:12px;">
        <div style="font-size:11px;color:var(--text-3);" id="health-last-sync">—</div>
        <button class="vitals-log-btn" onclick="openVitalsEntry()" title="Log missed vitals">＋ Log vitals</button>
        <button class="btn btn-hue btn-sm" onclick="helenRefresh()" id="helen-refresh-btn" style="font-size:10px;">↻ Refresh Analysis</button>
      </div>
    </div>
    <div class="view-body" style="padding:20px;display:flex;flex-direction:column;gap:16px;">

      <!-- ── DAILY HEALTH SCORE ──────────────────────────────────────────── -->
      <div class="health-score-panel" id="daily-score-panel">
        <!-- Score ring -->
        <div class="health-score-ring">
          <svg viewBox="0 0 72 72" style="width:72px;height:72px;transform:rotate(-90deg);">
            <circle cx="36" cy="36" r="30" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="6"/>
            <circle id="dhs-ring" cx="36" cy="36" r="30" fill="none" stroke="#f59e0b" stroke-width="6"
              stroke-linecap="round" stroke-dasharray="188.5" stroke-dashoffset="188.5"
              style="transition:stroke-dashoffset 1s ease,stroke 0.5s ease;"/>
          </svg>
          <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;">
            <div id="dhs-score" style="font-size:20px;font-weight:800;font-family:var(--font-mono);color:var(--amber);line-height:1;">—</div>
            <div id="dhs-grade" style="font-size:9px;font-weight:700;text-transform:uppercase;color:var(--text-3);margin-top:1px;">—</div>
          </div>
        </div>
        <!-- Breakdown + sparkline -->
        <div style="flex:1;min-width:0;">
          <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:8px;">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--text-2);">Daily Health Score</div>
            <div id="dhs-date" style="font-size:10px;color:var(--text-3);">Today</div>
          </div>
          <!-- Domain bars -->
          <div id="dhs-breakdown" style="margin-bottom:10px;"></div>
          <!-- Sparkline -->
          <div>
            <div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--text-3);margin-bottom:4px;">30-Day Trend</div>
            <svg id="dhs-sparkline" class="sparkline-svg" viewBox="0 0 280 44" preserveAspectRatio="none">
              <text x="140" y="24" text-anchor="middle" fill="rgba(255,255,255,0.2)" font-size="10">Loading…</text>
            </svg>
          </div>
        </div>
      </div>

      <!-- ── HELEN CHO ASSESSMENT HEADER ─────────────────────────────────── -->
      <div class="card card-tactical" id="helen-assessment-card" style="border-left:3px solid var(--hue);">
        <div class="card-inner" style="padding:16px;">
          <!-- Top row: score + headline -->
          <div style="display:flex;align-items:flex-start;gap:20px;margin-bottom:12px;">
            <!-- Score circle -->
            <div style="text-align:center;flex-shrink:0;">
              <div id="helen-score" style="font-size:52px;font-weight:800;color:var(--amber);font-family:var(--font-mono);line-height:1;">—</div>
              <div id="helen-grade" style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--text-2);margin-top:2px;">Analysing…</div>
              <div id="helen-risk-badge" style="margin-top:6px;display:inline-block;padding:2px 8px;border-radius:10px;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;background:var(--surface-2);color:var(--text-3);">—</div>
            </div>
            <!-- Headline + narrative -->
            <div style="flex:1;min-width:0;">
              <div style="font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--hue);margin-bottom:4px;">Helen Cho · Medical Intelligence</div>
              <div id="helen-headline" style="font-size:14px;font-weight:600;color:var(--text-1);margin-bottom:8px;line-height:1.4;">Loading health analysis…</div>
              <div id="helen-narrative" style="font-size:11px;color:var(--text-2);line-height:1.7;max-height:120px;overflow:hidden;position:relative;">
                <div id="helen-narrative-text"></div>
                <div id="helen-narrative-fade" style="position:absolute;bottom:0;left:0;right:0;height:30px;background:linear-gradient(transparent,var(--surface-1));display:none;"></div>
              </div>
              <button id="helen-expand-btn" onclick="helenToggleNarrative()" style="display:none;font-size:10px;color:var(--hue);background:none;border:none;cursor:pointer;padding:4px 0;margin-top:2px;">Show more ▾</button>
            </div>
          </div>
          <!-- Positive findings strip -->
          <div id="helen-positives" style="display:none;padding:8px 10px;background:rgba(16,185,129,0.08);border-radius:6px;border:1px solid rgba(16,185,129,0.2);font-size:10px;color:var(--green);margin-top:4px;"></div>
        </div>
      </div>

      <!-- ── KEY METRICS STRIP ──────────────────────────────────────────────── -->
      <div id="health-metrics-strip" style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;">
        <!-- A1c -->
        <div style="background:var(--surface-1);border:1px solid var(--border);border-radius:10px;padding:14px 16px;">
          <div style="font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-3);margin-bottom:6px;">A1c</div>
          <div style="display:flex;align-items:baseline;gap:6px;">
            <span id="hm-a1c" style="font-size:28px;font-weight:700;font-family:var(--font-mono);color:var(--amber);">7.3</span>
            <span style="font-size:10px;color:var(--text-3);">%</span>
            <span style="font-size:14px;color:var(--amber);margin-left:auto;">↑</span>
          </div>
          <div style="font-size:9px;color:var(--text-3);margin-top:4px;">Target &lt;7.0 · Apr 2026</div>
          <div id="spark-a1c" class="hm-sparkline"></div>
        </div>
        <!-- LDL -->
        <div style="background:var(--surface-1);border:1px solid var(--border);border-radius:10px;padding:14px 16px;">
          <div style="font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-3);margin-bottom:6px;">LDL</div>
          <div style="display:flex;align-items:baseline;gap:6px;">
            <span id="hm-ldl" style="font-size:28px;font-weight:700;font-family:var(--font-mono);color:var(--red,#ef4444);">156</span>
            <span style="font-size:10px;color:var(--text-3);">mg/dL</span>
            <span style="font-size:14px;color:var(--red,#ef4444);margin-left:auto;">↑</span>
          </div>
          <div style="font-size:9px;color:var(--text-3);margin-top:4px;">Target &lt;100 · Apr 2026</div>
          <div id="spark-ldl" class="hm-sparkline"></div>
        </div>
        <!-- BP (live) -->
        <div style="background:var(--surface-1);border:1px solid var(--border);border-radius:10px;padding:14px 16px;">
          <div style="font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-3);margin-bottom:6px;">Blood Pressure</div>
          <div style="display:flex;align-items:baseline;gap:6px;">
            <span id="hm-bp" style="font-size:22px;font-weight:700;font-family:var(--font-mono);color:var(--green);">—/—</span>
            <span style="font-size:10px;color:var(--text-3);">mmHg</span>
            <span id="hm-bp-arrow" style="font-size:14px;margin-left:auto;">→</span>
          </div>
          <div style="font-size:9px;color:var(--text-3);margin-top:4px;">Target &lt;130/80</div>
          <div id="spark-bp" class="hm-sparkline"></div>
        </div>
        <!-- eGFR -->
        <div style="background:var(--surface-1);border:1px solid var(--border);border-radius:10px;padding:14px 16px;">
          <div style="font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-3);margin-bottom:6px;">eGFR</div>
          <div style="display:flex;align-items:baseline;gap:6px;">
            <span id="hm-egfr" style="font-size:28px;font-weight:700;font-family:var(--font-mono);color:var(--amber);">87</span>
            <span style="font-size:10px;color:var(--text-3);">mL/min</span>
            <span style="font-size:14px;color:var(--amber);margin-left:auto;">↓</span>
          </div>
          <div style="font-size:9px;color:var(--text-3);margin-top:4px;">Stage 2 CKD · Apr 2026</div>
          <div id="spark-egfr" class="hm-sparkline"></div>
        </div>
        <!-- HRV (live) -->
        <div style="background:var(--surface-1);border:1px solid var(--border);border-radius:10px;padding:14px 16px;">
          <div style="font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-3);margin-bottom:6px;">HRV</div>
          <div style="display:flex;align-items:baseline;gap:6px;">
            <span id="hm-hrv" style="font-size:28px;font-weight:700;font-family:var(--font-mono);color:var(--blue);">—</span>
            <span style="font-size:10px;color:var(--text-3);">ms</span>
            <span style="font-size:14px;color:var(--text-3);margin-left:auto;">→</span>
          </div>
          <div style="font-size:9px;color:var(--text-3);margin-top:4px;">Apple Watch · 7-day avg</div>
          <div id="spark-hrv" class="hm-sparkline"></div>
        </div>
        <!-- Steps (live) -->
        <div style="background:var(--surface-1);border:1px solid var(--border);border-radius:10px;padding:14px 16px;">
          <div style="font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-3);margin-bottom:6px;">Steps</div>
          <div style="display:flex;align-items:baseline;gap:6px;">
            <span id="hm-steps" style="font-size:28px;font-weight:700;font-family:var(--font-mono);color:var(--blue);">—</span>
            <span style="font-size:10px;color:var(--text-3);">today</span>
          </div>
          <div style="font-size:9px;color:var(--text-3);margin-top:4px;">Target 8,000 · Apple Watch</div>
          <div id="spark-steps" class="hm-sparkline"></div>
        </div>
        <!-- Sleep (live) -->
        <div style="background:var(--surface-1);border:1px solid var(--border);border-radius:10px;padding:14px 16px;">
          <div style="font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-3);margin-bottom:6px;">Sleep</div>
          <div style="display:flex;align-items:baseline;gap:6px;">
            <span id="hm-sleep" style="font-size:28px;font-weight:700;font-family:var(--font-mono);color:var(--blue);">—</span>
            <span style="font-size:10px;color:var(--text-3);">hrs</span>
          </div>
          <div style="font-size:9px;color:var(--text-3);margin-top:4px;">Target 8.0 · Apple Watch</div>
          <div id="spark-sleep" class="hm-sparkline"></div>
        </div>
        <!-- Weight (live) -->
        <div style="background:var(--surface-1);border:1px solid var(--border);border-radius:10px;padding:14px 16px;">
          <div style="font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-3);margin-bottom:6px;">Weight</div>
          <div style="display:flex;align-items:baseline;gap:6px;">
            <span id="hm-weight" style="font-size:28px;font-weight:700;font-family:var(--font-mono);color:var(--blue);">—</span>
            <span style="font-size:10px;color:var(--text-3);">lbs</span>
            <span style="font-size:14px;color:var(--green);margin-left:auto;">↓</span>
          </div>
          <div style="font-size:9px;color:var(--text-3);margin-top:4px;">Goal: &lt;200 · Scale</div>
          <div id="spark-weight" class="hm-sparkline"></div>
        </div>
      </div>

      <!-- ── PRIORITY ACTION BOARD ─────────────────────────────────────────── -->
      <div>
        <div class="section-label" style="margin-bottom:8px;">Priority Actions <span id="helen-action-count" style="color:var(--text-3);font-weight:400;"></span></div>
        <div id="helen-actions" style="display:flex;flex-direction:column;gap:6px;">
          <div style="font-size:11px;color:var(--text-3);padding:8px 0;">Generating action plan…</div>
        </div>
      </div>

      <!-- ── DATA GRID (3 columns) ─────────────────────────────────────────── -->
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;">

        <!-- Column 1: Conditions + Goals + Medications -->
        <div>
          <div class="section-label" style="margin-bottom:8px;">Conditions</div>
          <div class="card" style="margin-bottom:12px;">
            <div class="card-inner" id="helen-conditions" style="padding:8px 0;">
              <div style="font-size:11px;color:var(--text-3);">Loading…</div>
            </div>
          </div>

          <div class="section-label" style="margin-bottom:8px;">Treatment Goals</div>
          <div class="card" style="margin-bottom:12px;">
            <div class="card-inner" id="helen-goals" style="padding:8px 0;">
              <div style="font-size:11px;color:var(--text-3);">Loading…</div>
            </div>
          </div>

          <div class="section-label" style="margin-bottom:8px;">Cardiovascular Risk</div>
          <div class="card" style="margin-bottom:12px;">
            <div class="card-inner" id="helen-cv-risk" style="padding:8px 0;">
              <div style="font-size:11px;color:var(--text-3);">Loading…</div>
            </div>
          </div>

          <div class="section-label" style="margin-bottom:8px;">5-Year Trajectory</div>
          <div class="card">
            <div class="card-inner" id="helen-trajectory" style="padding:8px 0;">
              <div style="font-size:11px;color:var(--text-3);">Loading…</div>
            </div>
          </div>
        </div>

        <!-- Column 2: Vitals + ECG + BP -->
        <div>
          <div class="section-label" style="margin-bottom:8px;">Today's Vitals <span class="card-badge" id="health-apple-badge">—</span></div>
          <div class="card" style="margin-bottom:12px;">
            <div class="card-inner" id="health-metrics-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:10px 0;">
              <div style="font-size:11px;color:var(--text-3);">No data yet</div>
            </div>
          </div>

          <div class="section-label" style="margin-bottom:8px;">Blood Pressure <span class="card-badge" id="health-omron-badge">Omron</span></div>
          <div class="card" style="margin-bottom:12px;">
            <div class="card-inner" style="padding:10px 0;">
              <div style="display:flex;align-items:baseline;gap:6px;padding-bottom:8px;border-bottom:1px solid var(--border);margin-bottom:8px;">
                <span style="font-size:28px;font-weight:700;font-family:var(--font-mono);" id="health-bp-value">—/—</span>
                <span style="font-size:10px;color:var(--text-3);">mmHg</span>
                <span style="font-size:12px;color:var(--text-2);" id="health-bp-pulse"></span>
                <span style="font-size:9px;color:var(--text-3);margin-left:auto;" id="health-bp-date"></span>
              </div>
              <div id="health-bp-history" style="font-size:10px;color:var(--text-3);">No readings yet</div>
              <div id="health-omron-connect-section" style="margin-top:8px;">
                <button class="btn-ghost" onclick="omronConnect()" id="health-omron-btn" style="font-size:10px;">Connect Omron</button>
              </div>
            </div>
          </div>

          <div class="section-label" style="margin-bottom:8px;">ECG <span class="card-badge" id="health-ecg-badge">KardiaMobile</span></div>
          <div class="card">
            <div class="card-inner" id="health-ecg-list" style="padding:8px 0;">
              <div style="font-size:11px;color:var(--text-3);">Loading…</div>
            </div>
          </div>
        </div>

        <!-- Column 3: Labs + Medication Insights -->
        <div>
          <div class="section-label" style="margin-bottom:8px;">Lab Alerts</div>
          <div class="card" style="margin-bottom:12px;">
            <div class="card-inner" id="helen-lab-alerts" style="padding:8px 0;">
              <div style="font-size:11px;color:var(--text-3);">Loading…</div>
            </div>
          </div>

          <div class="section-label" style="margin-bottom:8px;">Medication Insights</div>
          <div class="card" style="margin-bottom:12px;">
            <div class="card-inner" id="helen-med-insights" style="padding:8px 0;">
              <div style="font-size:11px;color:var(--text-3);">Loading…</div>
            </div>
          </div>

          <div class="section-label" style="margin-bottom:8px;">Diabetes Risk Profile</div>
          <div class="card" style="margin-bottom:12px;">
            <div class="card-inner" id="helen-diabetes-risk" style="padding:8px 0;">
              <div style="font-size:11px;color:var(--text-3);">Loading…</div>
            </div>
          </div>

          <div class="section-label" style="margin-bottom:8px;">Post-Bariatric Status</div>
          <div class="card">
            <div class="card-inner" id="helen-post-bariatric" style="padding:8px 0;">
              <div style="font-size:11px;color:var(--text-3);">Loading…</div>
            </div>
          </div>
        </div>

      </div><!-- end 3-col grid -->

      <!-- ── LAB SPARKLINES ─────────────────────────────────────────────────── -->
      <div style="margin-bottom:4px;">
        <div class="section-label" style="margin-bottom:8px;">Lab Trends <span style="color:var(--text-3);font-weight:400;font-size:9px;">sparkline — full history</span></div>
        <div class="card">
          <div class="card-inner" style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:12px 0;">
            <!-- A1c mini sparkline -->
            <div style="border-right:1px solid var(--border);padding-right:12px;">
              <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:2px;">
                <span style="font-size:10px;font-weight:700;color:var(--text-2);">A1c</span>
                <span style="font-size:13px;font-weight:700;font-family:var(--font-mono);color:var(--amber);">7.3<span style="font-size:9px;color:var(--text-3);font-weight:400;">%</span></span>
              </div>
              <div style="font-size:8px;color:var(--text-3);margin-bottom:4px;">Target &lt;7.0</div>
              <div id="spark-lab-a1c" style="height:36px;"></div>
            </div>
            <!-- LDL mini sparkline -->
            <div style="border-right:1px solid var(--border);padding-right:12px;">
              <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:2px;">
                <span style="font-size:10px;font-weight:700;color:var(--text-2);">LDL</span>
                <span style="font-size:13px;font-weight:700;font-family:var(--font-mono);color:var(--red,#ef4444);">156<span style="font-size:9px;color:var(--text-3);font-weight:400;"> mg</span></span>
              </div>
              <div style="font-size:8px;color:var(--text-3);margin-bottom:4px;">Target &lt;100</div>
              <div id="spark-lab-ldl" style="height:36px;"></div>
            </div>
            <!-- eGFR mini sparkline -->
            <div style="border-right:1px solid var(--border);padding-right:12px;">
              <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:2px;">
                <span style="font-size:10px;font-weight:700;color:var(--text-2);">eGFR</span>
                <span style="font-size:13px;font-weight:700;font-family:var(--font-mono);color:var(--amber);">87<span style="font-size:9px;color:var(--text-3);font-weight:400;"> mL</span></span>
              </div>
              <div style="font-size:8px;color:var(--text-3);margin-bottom:4px;">Stage 2 CKD watch</div>
              <div id="spark-lab-egfr" style="height:36px;"></div>
            </div>
            <!-- K+ mini sparkline -->
            <div>
              <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:2px;">
                <span style="font-size:10px;font-weight:700;color:var(--text-2);">K⁺</span>
                <span style="font-size:13px;font-weight:700;font-family:var(--font-mono);color:var(--green);">4.5<span style="font-size:9px;color:var(--text-3);font-weight:400;"> mEq</span></span>
              </div>
              <div style="font-size:8px;color:var(--text-3);margin-bottom:4px;">ARB + spiro monitor</div>
              <div id="spark-lab-kplus" style="height:36px;"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── KEY TRENDS ──────────────────────────────────────────────────── -->
      <div style="margin-bottom:16px;">
        <div class="section-label" style="margin-bottom:8px;">Key Lab Trends <span style="color:var(--text-3);font-weight:400;font-size:9px;">↑↘↔ trajectory over all recorded history</span></div>
        <div class="card">
          <div class="card-inner" id="helen-key-trends" style="padding:8px 0;display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:0 20px;">
            <div style="font-size:11px;color:var(--text-3);">Loading…</div>
          </div>
        </div>
      </div>

      <!-- ── SAM WILSON CHECK-IN BANNER ───────────────────────────────────────── -->
      <div id="sam-checkin-banner-wrap" style="margin-bottom:0;">
        <div class="section-label" style="margin-bottom:8px;">🦅 Sam Wilson
          <span style="color:var(--text-3);font-weight:400;font-size:9px;">Health &amp; Fitness Coach</span>
        </div>
        <div class="sam-checkin-banner" id="sam-checkin-banner">
          <div style="font-size:11px;color:var(--text-3);">Loading check-in…</div>
        </div>
      </div>

      <!-- ── SAM WILSON DAILY PROTOCOL ────────────────────────────────────────── -->
      <div style="margin-bottom:16px;" id="sam-protocol-section">
        <div class="section-label" style="margin-bottom:8px;">Full Daily Protocol
          <span id="sam-streak-badge" class="card-badge" style="margin-left:8px;display:none;">🔥 0 day streak</span>
        </div>
        <div class="card">
          <div class="card-inner" id="sam-protocol-content" style="padding:12px 0;">
            <div style="font-size:11px;color:var(--text-3);">Loading protocol…</div>
          </div>
        </div>
        <!-- Food Diary Strip -->
        <div id="sam-food-strip" style="margin-top:12px;display:none;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
            <span style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-3);">Today's Food Log</span>
            <span id="sam-food-protein-label" style="font-size:10px;color:var(--text-3);font-family:var(--font-mono);">—g protein</span>
          </div>
          <!-- Protein progress bar -->
          <div style="height:4px;background:var(--surface-3);border-radius:2px;margin-bottom:8px;overflow:hidden;">
            <div id="sam-food-protein-bar" style="height:100%;width:0%;background:var(--blue);border-radius:2px;transition:width .4s ease;"></div>
          </div>
          <!-- Meal list -->
          <div id="sam-food-meals" style="font-size:11px;color:var(--text-2);display:flex;flex-wrap:wrap;gap:4px;"></div>
        </div>
        <!-- Sam Chat -->
        <div style="margin-top:10px;">
          <!-- Mode indicator -->
          <div id="sam-chat-mode-bar" style="display:none;margin-bottom:6px;padding:5px 10px;background:var(--surface-3);border-radius:6px;font-size:11px;color:var(--blue);display:flex;align-items:center;justify-content:space-between;">
            <span id="sam-chat-mode-label">🎤 Interview mode</span>
            <button onclick="samCancelMode()" style="background:none;border:none;color:var(--text-3);font-size:10px;cursor:pointer;padding:0;">✕ Cancel</button>
          </div>
          <div id="sam-chat-messages" style="display:none;max-height:240px;overflow-y:auto;padding:8px;background:var(--surface-2);border-radius:8px;margin-bottom:8px;font-size:12px;"></div>
          <div style="display:flex;gap:6px;align-items:center;">
            <input id="sam-chat-input" type="text" placeholder="Talk to Sam… or log food (e.g. 'I had eggs and toast')"
              style="flex:1;background:var(--surface-2);border:1px solid var(--border);border-radius:6px;padding:7px 10px;font-size:12px;color:var(--text-1);outline:none;"
              onkeydown="if(event.key==='Enter'){{samChat();}}"/>
            <button class="btn-ghost" style="font-size:11px;padding:6px 12px;" onclick="samChat()">Send</button>
          </div>
          <div style="display:flex;gap:6px;margin-top:6px;">
            <button class="btn-ghost" style="font-size:10px;padding:4px 10px;" onclick="samStartInterview()">📋 Diet Interview</button>
            <button class="btn-ghost" style="font-size:10px;padding:4px 10px;" onclick="samSwitchMode('food')">🍽 Log Food</button>
            <button class="btn-ghost" style="font-size:10px;padding:4px 10px;" onclick="openSamJournal()">📓 Daily Journal</button>
          </div>
        </div>
      </div>

      <!-- ── LONGEVITY PROJECTION ──────────────────────────────────────────── -->
      <div style="margin-bottom:16px;">
        <div class="section-label" style="margin-bottom:8px;">Longevity Projection <span style="color:var(--text-3);font-weight:400;font-size:9px;">actuarial + risk-adjusted</span></div>
        <div class="card">
          <div class="card-inner" id="health-longevity-content" style="padding:12px 0;">
            <div style="font-size:11px;color:var(--text-3);">Loading…</div>
          </div>
        </div>
      </div>

      <!-- ── DIGITAL TWIN ───────────────────────────────────────────────────── -->
      <div style="margin-bottom:4px;">
        <div class="section-label" style="margin-bottom:8px;">Digital Twin — 12-Month Projections <span style="color:var(--text-3);font-weight:400;font-size:9px;">model-based forecast</span></div>
        <div class="card">
          <div class="card-inner" id="health-twin-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;padding:12px 0;">
            <div style="font-size:11px;color:var(--text-3);">Loading projections…</div>
          </div>
        </div>
      </div>

      <!-- ── DOCTOR APPOINTMENT PREP ───────────────────────────────────────── -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
        <div>
          <div class="section-label" style="margin-bottom:8px;">Questions for Dr. Wenk <span id="helen-appt-date" style="color:var(--text-3);font-size:9px;font-weight:400;"></span></div>
          <div class="card">
            <div class="card-inner" id="helen-doctor-questions" style="padding:8px 0;">
              <div style="font-size:11px;color:var(--text-3);">Loading…</div>
            </div>
          </div>
        </div>
        <div>
          <div class="section-label" style="margin-bottom:8px;">Missing Data / Gaps</div>
          <div class="card" style="margin-bottom:12px;">
            <div class="card-inner" id="helen-missing-data" style="padding:8px 0;">
              <div style="font-size:11px;color:var(--text-3);">Loading…</div>
            </div>
          </div>
          <!-- Readiness -->
          <div class="section-label" style="margin-bottom:8px;">Today's Readiness</div>
          <div class="card">
            <div class="card-inner" style="padding:12px 0;text-align:center;">
              <div id="health-readiness-score" style="font-size:40px;font-weight:700;color:var(--amber);font-family:var(--font-mono);">—</div>
              <div id="health-readiness-grade" style="font-size:11px;color:var(--text-2);margin-bottom:6px;">—</div>
              <div id="health-readiness-message" style="font-size:10px;color:var(--text-3);padding:0 8px;"></div>
              <div id="health-readiness-factors" style="padding:8px 0 0;text-align:left;"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── DATA CONNECTIONS (compact) ───────────────────────────────────── -->
      <div>
        <div class="section-label" style="margin-bottom:8px;">Data Connections</div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
          <!-- Apple Health -->
          <div class="card">
            <div class="card-inner" style="padding:10px 0;">
              <div style="font-size:10px;font-weight:600;color:var(--text-2);margin-bottom:6px;">Apple Health Auto Export</div>
              <div style="font-family:var(--font-mono);font-size:9px;background:var(--surface-2);padding:4px 8px;border-radius:4px;color:var(--amber);word-break:break-all;margin-bottom:6px;">http://192.168.5.47:8787/api/health/ingest</div>
              <div style="font-size:9px;color:var(--text-3);">REST API export · POST · JSON · Daily 7 AM</div>
              <button class="btn-ghost" style="font-size:9px;margin-top:6px;" onclick="healthTestIngest()">Test Ingest</button>
            </div>
          </div>
          <!-- MyChart -->
          <div class="card">
            <div class="card-inner" style="padding:10px 0;">
              <div style="font-size:10px;font-weight:600;color:var(--text-2);margin-bottom:6px;">MyChart Sync <span id="mychart-sync-badge" style="font-size:9px;color:var(--text-3);"></span></div>
              <div id="mychart-sync-status" style="font-size:9px;color:var(--text-3);margin-bottom:6px;"></div>
              <div id="mychart-progress-wrap" style="display:none;margin-bottom:6px;">
                <div style="background:var(--surface-2);border-radius:4px;height:4px;overflow:hidden;">
                  <div id="mychart-progress-bar" style="height:100%;background:var(--hue);width:0%;transition:width 0.4s;"></div>
                </div>
              </div>
              <div style="display:flex;gap:6px;">
                <button class="btn-ghost" style="font-size:9px;" onclick="mychartStartSync()" id="mychart-sync-btn">⟳ Sync</button>
                <button class="btn-ghost" style="font-size:9px;" onclick="mychartViewRecords()">Records</button>
              </div>
            </div>
          </div>
          <!-- Omron -->
          <div class="card">
            <div class="card-inner" style="padding:10px 0;">
              <div style="font-size:10px;font-weight:600;color:var(--text-2);margin-bottom:6px;">Omron Connect <span style="font-size:9px;font-weight:400;color:var(--text-3);">Blood Pressure</span></div>
              <div id="helen-omron-status-text" style="font-size:9px;color:var(--text-3);margin-bottom:6px;">Not configured</div>
              <div style="font-size:9px;color:var(--text-3);margin-bottom:6px;">Add OMRON_CLIENT_ID + OMRON_CLIENT_SECRET to .env</div>
              <button class="btn-ghost" style="font-size:9px;" onclick="omronConnect()">Connect</button>
            </div>
          </div>
        </div>
      </div>

      <!-- ── HEALTH CHAT CONSOLE ───────────────────────────────────────────── -->
      <div style="margin-bottom:4px;">
        <div class="section-label" style="margin-bottom:8px;">
          Ask Your Medical Team
          <span style="color:var(--text-3);font-weight:400;font-size:9px;">Helen Cho · Longevity Council · Direct consultation</span>
        </div>
        <div class="card" style="border:1px solid var(--hue);border-radius:12px;overflow:hidden;padding:0;">
          <div class="hchat-wrap">

            <!-- ── Doctor selector bar ── -->
            <div class="hchat-selector-bar">
              <span class="hchat-selector-label">CONSULT WITH</span>
              <!-- Active doctor pill / dropdown trigger -->
              <div class="hchat-active-pill" id="hchat-active-pill" onclick="hchatToggleDropdown(event)">
                <span class="hchat-active-pill-icon" id="hchat-active-icon">🧬</span>
                <span class="hchat-active-pill-name" id="hchat-active-name">Helen Cho</span>
                <span class="hchat-active-pill-arrow">▾</span>
              </div>
              <span class="hchat-active-pill-subtitle" id="hchat-active-title">Chief Medical Intelligence Officer</span>

              <!-- Floating dropdown -->
              <div class="hchat-dropdown" id="hchat-dropdown">
                <div class="hchat-dropdown-label">Your Medical Team</div>
                <div class="hchat-dropdown-grid" id="hchat-dropdown-grid">
                  <!-- Injected by JS -->
                </div>
              </div>
            </div>

            <!-- ── Messages ── -->
            <div id="hchat-messages" style="flex:1;min-height:320px;max-height:420px;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px;scroll-behavior:smooth;">
              <div style="text-align:center;color:var(--text-3);font-size:11px;padding:30px 20px;">
                <div style="font-size:24px;margin-bottom:8px;">🧬</div>
                <div style="font-weight:600;color:var(--text-2);margin-bottom:4px;">Helen Cho · Medical Intelligence</div>
                <div>Ask me anything about your health, medications, labs, or longevity strategy.</div>
              </div>
            </div>

            <!-- ── Input bar ── -->
            <div style="display:flex;gap:10px;padding:10px 14px;background:var(--surface-2);border-top:1px solid var(--border);">
              <input id="hchat-input" type="text" placeholder="Ask Helen Cho…"
                style="flex:1;background:var(--surface-1);border:1px solid var(--border);border-radius:8px;padding:9px 12px;font-size:12px;color:var(--text-1);outline:none;font-family:var(--font-sans);"
                onkeydown="if(event.key==='Enter'&&!event.shiftKey){{event.preventDefault();hchatSend();}}" />
              <button onclick="hchatSend()" id="hchat-send-btn"
                style="background:var(--hue);color:#fff;border:none;border-radius:8px;padding:9px 18px;font-size:12px;font-weight:600;cursor:pointer;white-space:nowrap;transition:opacity .2s;">
                Send ↑
              </button>
            </div>

          </div>
        </div>
      </div>

      <!-- Hidden: medical records dump (populated by mychartViewRecords) -->
      <div id="health-medical-records-section" style="display:none;">
        <div class="section-label" style="margin-bottom:8px;">Full Medical Records</div>
        <div class="card"><div class="card-inner" id="health-medical-records" style="padding:8px 0;"></div></div>
      </div>
      <div id="health-alerts" style="display:none;"></div>

    </div>
  </div><!-- end view-health -->

  <!-- ── HOME AUTOMATION ────────────────────────────────────── -->
  <div id="view-home" class="view" style="display:none;">
    <div class="view-header">
      <div class="view-title">HOME<div class="view-title-line"></div></div>
      <div class="view-subtitle">Smart Devices · Kasa Control · Scenes &amp; Rooms</div>
    </div>
    <div id="kasa-content">
      <div class="kasa-unavailable">
        <div class="kasa-unavailable-icon">🏠</div>
        <div>Scanning for devices…</div>
      </div>
    </div>
  </div>

  <!-- ── NAVIGATE ─────────────────────────────────────────── -->
  <div id="view-navigate" class="view" style="display:none; padding:0">
    <div class="nav-container">
      <!-- Aerial View destination modal -->
      <div id="nav-aerial-modal" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.92); z-index:9999; flex-direction:column; align-items:center; justify-content:center;">
        <div style="position:relative; width:min(800px,95vw);">
          <div id="nav-aerial-dest-name" style="color:#fff; font-size:22px; font-weight:700; margin-bottom:12px; text-align:center;"></div>
          <div id="nav-aerial-loading" style="display:flex; align-items:center; justify-content:center; min-height:240px; flex-direction:column; gap:16px;">
            <div style="width:48px; height:48px; border:3px solid rgba(0,212,255,0.2); border-top-color:#00D4FF; border-radius:50%; animation:spin 1s linear infinite;"></div>
            <div style="color:rgba(255,255,255,0.5); font-size:14px;">&#127916; Preparing aerial view&hellip;</div>
          </div>
          <video id="nav-aerial-video" autoplay loop muted playsinline style="display:none; width:100%; border-radius:16px; box-shadow:0 0 60px rgba(0,212,255,0.3);"></video>
          <img id="nav-aerial-fallback" style="display:none; width:100%; border-radius:16px;" alt="Destination">
          <div style="display:flex; gap:12px; margin-top:16px; justify-content:center;">
            <button onclick="startNavigation(); closeAerialModal();" style="padding:12px 32px; background:#00D4FF; color:#000; border:none; border-radius:8px; font-size:16px; font-weight:700; cursor:pointer;">&#9654; Start Navigation</button>
            <button onclick="closeAerialModal();" style="padding:12px 24px; background:rgba(255,255,255,0.1); color:#fff; border:1px solid rgba(255,255,255,0.2); border-radius:8px; font-size:16px; cursor:pointer;">&#10005; Close</button>
          </div>
        </div>
      </div>
      <!-- SIDEBAR (desktop) -->
      <div class="nav-sidebar" id="nav-sidebar">
        <div class="nav-route-inputs">
          <div style="display:flex; gap:6px; margin-bottom:6px;">
            <button class="nav-home-btn" onclick="navSetHome()" title="Set origin to Home">&#127968; Home</button>
            <button class="nav-home-btn" onclick="navUseCurrentLocation()" title="Use GPS location">&#128205; My Location</button>
          </div>
          <div class="nav-input-row">
            <span style="color:#4CAF50">&#9679;</span>
            <input id="nav-origin" class="nav-input" placeholder="Starting point..." oninput="navAutocomplete('nav-origin', 'nav-origin-results')">
            <div id="nav-origin-results" class="nav-autocomplete-results"></div>
          </div>
          <div class="nav-input-row">
            <span style="color:#F44336">&#9679;</span>
            <input id="nav-dest" class="nav-input" placeholder="Destination..." oninput="navAutocomplete('nav-dest', 'nav-dest-results')">
            <div id="nav-dest-results" class="nav-autocomplete-results"></div>
          </div>
          <div style="display:flex; gap:8px">
            <button class="nav-swap-btn" onclick="navSwapInputs()">&#8645;</button>
            <button class="nav-go-btn" onclick="navGetRoute()">Get Route</button>
          </div>
        </div>

        <div class="nav-poi-toggles" id="nav-poi-toggles">
          <button class="nav-poi-toggle active" data-cat="food" onclick="navTogglePOI('food')">&#127828; Food</button>
          <button class="nav-poi-toggle active" data-cat="starbucks" onclick="navTogglePOI('starbucks')">&#9749; Starbucks</button>
          <button class="nav-poi-toggle active" data-cat="parks" onclick="navTogglePOI('parks')">&#127794; Nat&apos;l Parks</button>
          <button class="nav-poi-toggle active" data-cat="historic" onclick="navTogglePOI('historic')">&#127963; Historic</button>
          <button class="nav-poi-toggle active" data-cat="family" onclick="navTogglePOI('family')">&#11088; Family</button>
          <button class="nav-poi-toggle" data-cat="gas" onclick="navTogglePOI('gas')">&#9981; Gas</button>
        </div>

        <!-- Parks & Historic distance slider -->
        <div class="nav-radius-row" id="nav-radius-row">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span style="font-size:11px; opacity:0.6; text-transform:uppercase; letter-spacing:0.5px;">&#127794; Parks &amp; Historic — search radius</span>
            <span id="nav-parks-radius-label" style="font-size:13px; font-weight:700; color:#4CAF50;">25 mi</span>
          </div>
          <input type="range" id="nav-parks-radius" class="nav-radius-slider"
            min="5" max="100" step="5" value="25"
            oninput="navUpdateParksRadius(this.value)"
            onchange="if(_navRouteData) loadNavPOIs(_navRouteData)">
          <div style="display:flex; justify-content:space-between; font-size:10px; opacity:0.4; margin-top:2px;">
            <span>5 mi</span><span>25 mi</span><span>50 mi</span><span>100 mi</span>
          </div>
        </div>

        <div class="nav-summary-bar" id="nav-summary-bar" style="display:none">
          <div class="nav-stat"><span id="nav-dist">--</span><label>Distance</label></div>
          <div class="nav-stat"><span id="nav-time">--</span><label>Drive Time</label></div>
          <div class="nav-stat"><span id="nav-eta">--</span><label>ETA</label></div>
        </div>

        <div id="nav-turns-section" style="display:none">
          <div class="nav-section-title">Turn by Turn</div>
          <div id="nav-turns-list"></div>
        </div>

        <!-- Street View turn preview -->
        <div id="nav-sv-panel" style="display:none; padding:12px;">
          <div class="nav-section-title">What to Expect</div>
          <div style="position:relative;">
            <img id="nav-sv-img" style="width:100%; border-radius:10px; min-height:120px; background:#1a1a2e;" alt="Street View" onerror="this.style.display='none'">
            <div id="nav-sv-caption" style="font-size:11px; opacity:0.6; margin-top:4px; text-align:center;"></div>
          </div>
        </div>

        <div id="nav-pois-section" style="display:none">
          <div class="nav-section-title">Along Your Route</div>
          <div id="nav-pois-list"></div>
        </div>
      </div>

      <!-- MAP PANE -->
      <div class="nav-map-pane">
        <div id="nav-map"></div>
        <!-- Mobile HUD (hidden on desktop) -->
        <div class="nav-hud" id="nav-hud" style="display:none">
          <div style="display:flex; align-items:center; gap:16px">
            <div id="nav-hud-arrow" class="nav-hud-turn">&#8593;</div>
            <div>
              <div class="nav-hud-distance" id="nav-hud-dist">--</div>
              <div class="nav-hud-instruction" id="nav-hud-instr">Calculating...</div>
            </div>
          </div>
        </div>
        <div class="nav-eta-strip" id="nav-eta-strip" style="display:none">
          <span id="nav-hud-eta">--</span> arrival &middot; <span id="nav-hud-remain">--</span> remaining
        </div>
        <div class="nav-poi-alert" id="nav-poi-alert">
          <span id="nav-poi-alert-icon">&#127828;</span>
          <div id="nav-poi-alert-text">Starbucks in 0.8 miles</div>
          <button onclick="dismissNavAlert()" style="background:none;border:none;color:var(--text-3);cursor:pointer;font-size:16px;margin-left:auto;">&#10005;</button>
        </div>
        <button class="nav-voice-btn" id="nav-voice-btn" onclick="navToggleVoice()" title="Toggle voice">&#128266;</button>
        <button class="nav-start-btn" id="nav-start-btn" onclick="startNavigation()" style="display:none">&#9654; Start Navigation</button>
        <button class="nav-stop-btn" id="nav-stop-btn" onclick="stopNavigation()" style="display:none">&#9632; Stop</button>
      </div>
    </div>
  </div>

  <!-- ── NEWS ──────────────────────────────────────────────── -->
  <div id="view-news" class="view" style="display:none;">
    <div class="view-header">
      <div class="view-title">NEWS<div class="view-title-line"></div></div>
      <div class="view-subtitle">Live headlines from BBC · Reuters · NYT · Al Jazeera · CNBC · MarketWatch</div>
    </div>
    <div style="padding:0 4px;">
      <div class="news-filter-bar">
        <button class="news-filter-btn active" id="news-filter-all" onclick="filterNews('all')">All</button>
        <button class="news-filter-btn" id="news-filter-world" onclick="filterNews('world')">🌍 World</button>
        <button class="news-filter-btn" id="news-filter-finance" onclick="filterNews('finance')">📈 Finance</button>
        <div class="news-refresh-info">
          <span id="news-last-fetched">—</span>
          <button class="btn-ghost" style="font-size:10px;padding:3px 8px;" onclick="loadNews(true)">↺ Refresh</button>
        </div>
      </div>
      <div id="news-content">
        <div class="news-grid" id="news-grid">
          <div style="color:var(--text-3);font-size:13px;padding:40px 0;text-align:center;grid-column:1/-1;">Loading headlines…</div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── JOURNEY ────────────────────────────────────────────────────── -->
  <div id="view-journey" class="view" style="display:none;">
    <div class="view-header">
      <div class="view-title">JOURNEY <div class="view-title-line"></div></div>
      <div class="view-subtitle" id="journey-subtitle">Your story with JARVIS</div>
    </div>

    <!-- Stats strip -->
    <div class="stats-strip" id="journey-stats-strip">
      <div class="card stat-tile"><div class="stat-label">This Month</div><div class="stat-value" id="journey-total">—</div><div class="stat-sub">events logged</div></div>
      <div class="card stat-tile accent"><div class="stat-label">Tasks Done</div><div class="stat-value" id="journey-tasks">—</div><div class="stat-sub">this month</div></div>
      <div class="card stat-tile gold-accent"><div class="stat-label">Ideas</div><div class="stat-value" id="journey-ideas">—</div><div class="stat-sub">captured</div></div>
      <div class="card stat-tile"><div class="stat-label">Briefs Read</div><div class="stat-value" id="journey-briefs">—</div><div class="stat-sub">this month</div></div>
    </div>

    <!-- Insights (Phase 6) -->
    <div class="card" id="journey-insights-card" style="margin-bottom:16px;display:none;">
      <div class="card-title">🧠 What JARVIS Has Learned</div>
      <div id="journey-insights-list" style="display:flex;flex-direction:column;gap:8px;margin-top:8px;"></div>
    </div>

    <!-- Timeline -->
    <div id="journey-timeline" style="display:flex;flex-direction:column;gap:12px;">
      <div style="color:rgba(255,255,255,0.3);font-size:13px;">Loading your journey...</div>
    </div>
    <div style="text-align:center;margin-top:20px;">
      <button class="glass-btn" onclick="loadJourneyMore()" id="journey-load-more" style="display:none;">Load more</button>
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
    <button class="cmd-chip cmd-chip-faith" onclick="openQuickCapture('gratitude')">🙏 Gratitude</button>
    <button class="cmd-chip cmd-chip-faith" onclick="openQuickCapture('prayer')">✦ Prayer</button>
    <button class="cmd-chip cmd-chip-faith" onclick="openQuickCapture('note')">📝 Note</button>
    <button class="cmd-chip cmd-chip-faith" onclick="openQuickCapture('milestone')">🏆 Milestone</button>
  </div>
  <div class="cmd-row">
    <input class="cmd-input" id="cmd-input" type="text" placeholder="Ask JARVIS to build, fix, or explain anything…" onkeydown="cmdKey(event)" onpaste="handleSmartPaste(event)">
    <button class="cmd-mic" id="cmd-mic" onclick="toggleMic()" title="Click to speak · Say 'Hey JARVIS' to activate hands-free">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="9" y="2" width="6" height="11" rx="3"/><path d="M5 10a7 7 0 0014 0"/><path d="M12 21v-4"/>
      </svg>
    </button>
    <button class="cmd-mic" id="cmd-tts" onclick="voiceToggleTts()" title="Toggle spoken responses" style="font-size:14px;">🔊</button>
    <button class="cmd-send" onclick="sendCmd()">SEND</button>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════════
     SETTINGS — FULL-SCREEN OVERLAY
══════════════════════════════════════════════════════════════════════ -->
<div class="hidden" id="settings-overlay" onclick="closeSettingsIfOuter(event)">
  <div id="settings-panel">

    <!-- Top bar -->
    <div id="settings-topbar">
      <div id="settings-topbar-title">Settings</div>
      <button class="modal-close" onclick="closeSettings()" style="width:32px;height:32px;">✕</button>
    </div>

    <div id="settings-body">

      <!-- Left nav -->
      <nav id="settings-nav">
        <div class="settings-nav-section-label">Display</div>
        <button class="settings-nav-pill active" data-section="interface" onclick="settingsNavTo('interface')">
          <span class="snp-icon">⬡</span> Interface
        </button>
        <div class="settings-nav-section-label">Connectivity</div>
        <button class="settings-nav-pill" data-section="accounts" onclick="settingsNavTo('accounts')">
          <span class="snp-icon">◈</span> Accounts
        </button>
        <button class="settings-nav-pill" data-section="voice" onclick="settingsNavTo('voice')">
          <span class="snp-icon">◉</span> Voice
        </button>
        <div class="settings-nav-section-label">Context</div>
        <button class="settings-nav-pill" data-section="location" onclick="settingsNavTo('location')">
          <span class="snp-icon">◎</span> Location
        </button>
        <button class="settings-nav-pill" data-section="family" onclick="settingsNavTo('family')">
          <span class="snp-icon">◈</span> Family
        </button>
        <button class="settings-nav-pill" data-section="devices" onclick="settingsNavTo('devices')">
          <span class="snp-icon">⬡</span> Devices
        </button>
        <button class="settings-nav-pill" data-section="costs" onclick="settingsNavTo('costs')">
          <span class="snp-icon">💸</span> Costs
        </button>
      </nav>

      <!-- Right content area — populated by settingsLoadSection() -->
      <div id="settings-content">
        <div id="settings-section-content"></div>
      </div>

    </div><!-- /#settings-body -->
  </div><!-- /#settings-panel -->
</div><!-- /#settings-overlay -->

<!-- Sam Wilson adherence history modal -->
<div class="sam-hist-overlay hidden" id="sam-hist-overlay" onclick="closeSamHistory(event)">
  <div class="sam-hist-modal">
    <!-- Header -->
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
      <div style="font-size:15px;font-weight:700;color:var(--text-1);">🦅 Sam's Log</div>
      <button onclick="closeSamHistory()" style="width:28px;height:28px;border-radius:8px;border:1px solid rgba(255,255,255,0.12);background:rgba(255,255,255,0.06);color:var(--text-2);cursor:pointer;font-size:13px;display:flex;align-items:center;justify-content:center;">✕</button>
    </div>
    <!-- Day navigator -->
    <div class="sam-hist-nav">
      <button class="sam-hist-nav-btn" id="sam-hist-prev" onclick="navSamHistory(-1)" title="Previous day">‹</button>
      <div class="sam-hist-date">
        <div class="sam-hist-date-label" id="sam-hist-date-label">—</div>
        <div class="sam-hist-date-rel" id="sam-hist-date-rel">—</div>
      </div>
      <button class="sam-hist-nav-btn" id="sam-hist-next" onclick="navSamHistory(+1)" title="Next day">›</button>
    </div>
    <!-- Adherence % -->
    <div class="sam-hist-pct">
      <div class="sam-hist-pct-num" id="sam-hist-pct-num">—%</div>
      <div class="sam-hist-pct-bar">
        <div class="sam-hist-pct-fill" id="sam-hist-pct-fill" style="width:0%"></div>
      </div>
      <div style="font-size:10px;color:var(--text-3);" id="sam-hist-pct-label">adherence</div>
    </div>
    <!-- 30-day dot streak -->
    <div class="sam-hist-streak" id="sam-hist-streak"></div>
    <!-- Checklist -->
    <div class="sam-hist-list" id="sam-hist-list"></div>
    <!-- Notes -->
    <textarea class="sam-hist-notes" id="sam-hist-notes" placeholder="Notes for this day…" rows="2"></textarea>
    <!-- Save -->
    <button class="sam-hist-save" id="sam-hist-save" onclick="saveSamHistoryDay()">Save Changes</button>
  </div>
</div>

<!-- Sam Daily Journal modal -->
<div id="sam-journal-overlay" class="hidden" style="position:fixed;inset:0;background:rgba(0,0,0,.6);backdrop-filter:blur(8px);z-index:1400;display:flex;align-items:flex-end;justify-content:center;">
  <div id="sam-journal-modal" style="width:100%;max-width:640px;height:85vh;background:var(--surface-1);border-radius:20px 20px 0 0;display:flex;flex-direction:column;overflow:hidden;">
    <!-- header -->
    <div style="padding:16px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-shrink:0;">
      <div>
        <div style="font-size:14px;font-weight:600;color:var(--text-1);">📓 Daily Journal</div>
        <div id="sj-date" style="font-size:11px;color:var(--text-3);"></div>
      </div>
      <button onclick="closeSamJournal()" style="background:none;border:none;font-size:18px;color:var(--text-3);cursor:pointer;">✕</button>
    </div>
    <!-- messages -->
    <div id="sj-messages" style="flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px;"></div>
    <!-- summary card (hidden until first entry) -->
    <div id="sj-summary" style="display:none;margin:0 16px 8px;padding:12px;background:var(--surface-2);border-radius:10px;border:1px solid var(--border);flex-shrink:0;">
      <div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-3);margin-bottom:8px;">Captured Today</div>
      <div id="sj-summary-content"></div>
    </div>
    <!-- input -->
    <div style="padding:12px 16px 20px;border-top:1px solid var(--border);flex-shrink:0;">
      <textarea id="sj-input" placeholder="Tell Sam about your day…" rows="3"
        style="width:100%;background:var(--surface-2);border:1px solid var(--border);border-radius:10px;padding:10px 12px;font-size:13px;color:var(--text-1);resize:none;outline:none;font-family:inherit;box-sizing:border-box;"
        onkeydown="if(event.key==='Enter'&&!event.shiftKey){{event.preventDefault();samJournalSend();}}"
        oninput="this.style.height='';this.style.height=Math.min(this.scrollHeight,140)+'px'"></textarea>
      <div style="display:flex;gap:8px;margin-top:8px;">
        <button class="btn-ghost" style="flex:1;font-size:12px;padding:8px;" onclick="samJournalSend()">Send to Sam →</button>
        <button class="btn-ghost" style="font-size:12px;padding:8px 14px;" onclick="closeSamJournal()">Done</button>
      </div>
    </div>
  </div>
</div>

<!-- Manual Vitals Entry modal -->
<div class="vitals-modal-overlay hidden" id="vitals-entry-overlay" onclick="closeVitalsEntry(event)">
  <div class="vitals-modal">
    <!-- Header -->
    <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:6px;">
      <div>
        <div style="font-size:16px;font-weight:700;color:var(--text-1);">📋 Log Vitals</div>
        <div style="font-size:11px;color:var(--text-3);margin-top:3px;">Enter any readings that Apple Watch missed</div>
      </div>
      <button onclick="closeVitalsEntry()" style="width:28px;height:28px;border-radius:8px;border:1px solid rgba(255,255,255,0.12);background:rgba(255,255,255,0.06);color:var(--text-2);cursor:pointer;font-size:13px;display:flex;align-items:center;justify-content:center;">✕</button>
    </div>
    <!-- Date selector -->
    <div class="vitals-date-row">
      <span>Date:</span>
      <input type="date" class="vitals-date-inp" id="vitals-date">
      <span style="margin-left:auto;font-size:10px;opacity:0.6;">Leave blank = today</span>
    </div>

    <!-- Sleep & Recovery -->
    <div class="vitals-section-label">😴 Sleep &amp; Recovery</div>
    <div class="vitals-grid">
      <div class="vitals-field">
        <div class="vitals-label">Sleep</div>
        <input type="number" class="vitals-inp" id="vi-sleep" placeholder="7.5" min="0" max="24" step="0.25">
        <div class="vitals-unit">hours</div>
      </div>
      <div class="vitals-field">
        <div class="vitals-label">HRV</div>
        <input type="number" class="vitals-inp" id="vi-hrv" placeholder="58" min="0" max="300" step="1">
        <div class="vitals-unit">ms</div>
      </div>
    </div>

    <!-- Heart & Circulation -->
    <div class="vitals-section-label">❤️ Heart &amp; Circulation</div>
    <div class="vitals-grid">
      <div class="vitals-field">
        <div class="vitals-label">Resting HR</div>
        <input type="number" class="vitals-inp" id="vi-rhr" placeholder="62" min="30" max="200" step="1">
        <div class="vitals-unit">bpm</div>
      </div>
      <div class="vitals-field">
        <div class="vitals-label">Blood Oxygen</div>
        <input type="number" class="vitals-inp" id="vi-spo2" placeholder="98" min="80" max="100" step="0.1">
        <div class="vitals-unit">% SpO₂</div>
      </div>
    </div>
    <!-- BP in its own row — 3 fields -->
    <div class="vitals-grid triple" style="margin-top:10px;">
      <div class="vitals-field">
        <div class="vitals-label">BP Systolic</div>
        <input type="number" class="vitals-inp" id="vi-sys" placeholder="118" min="60" max="240" step="1">
        <div class="vitals-unit">mmHg</div>
      </div>
      <div class="vitals-field">
        <div class="vitals-label">BP Diastolic</div>
        <input type="number" class="vitals-inp" id="vi-dia" placeholder="76" min="40" max="160" step="1">
        <div class="vitals-unit">mmHg</div>
      </div>
      <div class="vitals-field">
        <div class="vitals-label">Pulse</div>
        <input type="number" class="vitals-inp" id="vi-pulse" placeholder="68" min="30" max="200" step="1">
        <div class="vitals-unit">bpm</div>
      </div>
    </div>

    <!-- Body -->
    <div class="vitals-section-label">⚖️ Body</div>
    <div class="vitals-grid">
      <div class="vitals-field">
        <div class="vitals-label">Weight</div>
        <input type="number" class="vitals-inp" id="vi-weight" placeholder="195.0" min="50" max="500" step="0.1">
        <div class="vitals-unit">lbs</div>
      </div>
      <div class="vitals-field">
        <div class="vitals-label">Body Fat</div>
        <input type="number" class="vitals-inp" id="vi-bodyfat" placeholder="22.5" min="1" max="60" step="0.1">
        <div class="vitals-unit">%</div>
      </div>
    </div>

    <!-- Activity -->
    <div class="vitals-section-label">🏃 Activity</div>
    <div class="vitals-grid">
      <div class="vitals-field">
        <div class="vitals-label">Steps</div>
        <input type="number" class="vitals-inp" id="vi-steps" placeholder="8500" min="0" max="100000" step="100">
        <div class="vitals-unit">steps</div>
      </div>
      <div class="vitals-field">
        <div class="vitals-label">Active Cal</div>
        <input type="number" class="vitals-inp" id="vi-cal" placeholder="520" min="0" max="5000" step="10">
        <div class="vitals-unit">kcal</div>
      </div>
      <div class="vitals-field">
        <div class="vitals-label">Exercise</div>
        <input type="number" class="vitals-inp" id="vi-exercise" placeholder="45" min="0" max="600" step="5">
        <div class="vitals-unit">min</div>
      </div>
      <div class="vitals-field">
        <div class="vitals-label">Stand Hours</div>
        <input type="number" class="vitals-inp" id="vi-stand" placeholder="10" min="0" max="24" step="1">
        <div class="vitals-unit">hours</div>
      </div>
    </div>

    <button class="vitals-submit" id="vitals-submit-btn" onclick="submitVitals()">Save Vitals</button>
  </div>
</div>

<!-- Finance setup modal -->
<div class="finance-modal-overlay hidden" id="finance-setup-overlay" onclick="closeFinanceSetup(event)">
  <div class="finance-modal">
    <!-- Header -->
    <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:20px;">
      <div>
        <div style="font-size:16px;font-weight:700;color:var(--text-1);">💰 Financial Setup</div>
        <div style="font-size:11px;color:var(--text-3);margin-top:3px;">Enter your real balances — nothing connects to your bank</div>
      </div>
      <button onclick="closeFinanceSetup()" style="width:28px;height:28px;border-radius:8px;border:1px solid rgba(255,255,255,0.12);background:rgba(255,255,255,0.06);color:var(--text-2);cursor:pointer;font-size:13px;display:flex;align-items:center;justify-content:center;">✕</button>
    </div>
    <!-- Tabs -->
    <div class="finance-tabs" id="finance-tabs">
      <button class="finance-tab active" onclick="switchFinanceTab('accounts')">Accounts</button>
      <button class="finance-tab" onclick="switchFinanceTab('streams')">Passive Income</button>
      <button class="finance-tab" onclick="switchFinanceTab('goals')">Goals</button>
    </div>
    <!-- Accounts panel -->
    <div id="finance-panel-accounts" class="finance-panel active">
      <div id="finance-accounts-list"></div>
      <div class="finance-form">
        <div class="finance-form-title">Add Account</div>
        <div class="finance-inputs">
          <input class="finance-inp" id="fi-acct-name" placeholder="e.g. Chase Checking" autocomplete="off">
          <select class="finance-sel" id="fi-acct-type">
            <option value="checking">Checking</option>
            <option value="savings">Savings</option>
            <option value="investment">Investment / Brokerage</option>
            <option value="retirement">Retirement (401k / IRA)</option>
            <option value="credit">Credit Card</option>
            <option value="loan">Loan / Mortgage</option>
            <option value="other">Other</option>
          </select>
          <input class="finance-inp" id="fi-acct-institution" placeholder="Bank / Brokerage name" autocomplete="off">
          <input class="finance-inp" id="fi-acct-balance" type="number" step="0.01" placeholder="Balance ($)" autocomplete="off">
        </div>
        <button class="finance-add-btn" onclick="submitFinanceAccount()">＋ Add Account</button>
      </div>
    </div>
    <!-- Passive Income panel -->
    <div id="finance-panel-streams" class="finance-panel">
      <div id="finance-streams-list"></div>
      <div class="finance-form">
        <div class="finance-form-title">Add Income Stream</div>
        <div class="finance-inputs">
          <input class="finance-inp" id="fi-stream-name" placeholder="e.g. Book Royalties" autocomplete="off">
          <select class="finance-sel" id="fi-stream-type">
            <option value="book_royalty">Book Royalty</option>
            <option value="course_revenue">Course Revenue</option>
            <option value="dividend">Dividends</option>
            <option value="rental">Rental Income</option>
            <option value="affiliate">Affiliate</option>
            <option value="interest">Interest</option>
            <option value="consulting">Consulting</option>
            <option value="other">Other</option>
          </select>
          <input class="finance-inp" id="fi-stream-monthly" type="number" step="0.01" placeholder="Monthly avg ($)" autocomplete="off">
          <input class="finance-inp" id="fi-stream-platform" placeholder="Platform (optional)" autocomplete="off">
        </div>
        <button class="finance-add-btn" onclick="submitFinanceStream()">＋ Add Stream</button>
      </div>
    </div>
    <!-- Goals panel -->
    <div id="finance-panel-goals" class="finance-panel">
      <div id="finance-goals-list"></div>
      <div class="finance-form">
        <div class="finance-form-title">Add Goal</div>
        <div class="finance-inputs">
          <input class="finance-inp" id="fi-goal-title" placeholder="Goal name" autocomplete="off">
          <select class="finance-sel" id="fi-goal-type">
            <option value="savings">Savings</option>
            <option value="debt_payoff">Debt Payoff</option>
            <option value="investment">Investment</option>
            <option value="income_target">Income Target</option>
            <option value="emergency_fund">Emergency Fund</option>
          </select>
          <input class="finance-inp" id="fi-goal-target" type="number" step="0.01" placeholder="Target amount ($)" autocomplete="off">
          <input class="finance-inp" id="fi-goal-current" type="number" step="0.01" placeholder="Current amount ($)" autocomplete="off">
          <input class="finance-inp" id="fi-goal-date" type="date" placeholder="Target date" style="grid-column:1/-1;" autocomplete="off">
        </div>
        <button class="finance-add-btn" onclick="submitFinanceGoal()">＋ Add Goal</button>
      </div>
    </div>
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
// NOTE: AGENTS is seeded above as a fallback. loadAgentRoster() replaces it
// with the live unified roster from /api/agents/roster on every Agents tab visit.
// Any agent registered from Chronicle, Ghostwritr, Catalyst, or a future system
// will automatically appear here without code changes.

/* Domain → left-border CSS class
   Covers both the original PascalCase values (from the hardcoded array)
   and the lowercase values coming from life_agents.json / external_agents.json */
const DOMAIN_CLASS = {{
  // PascalCase (original hardcoded array)
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
  'Workflow':     'domain-operations',
  // Lowercase (life_agents.json domain values)
  'core':         'domain-command',
  'executive':    'domain-operations',
  'family':       'domain-chronicle',
  'formation':    'domain-chronicle',
  'finance':      'domain-finance',
  'security':     'domain-intelligence',
  'system':       'domain-engineering',
  'workshop':     'domain-workshop',
  'community':    'domain-publishing',
  'health':       'domain-power',
  'workflow':     'domain-operations',
  'publishing':   'domain-publishing',
  'intelligence': 'domain-intelligence',
  'engineering':  'domain-engineering',
  'analysis':     'domain-analysis',
}};

/* ── State ── */
let currentView    = 'overview';
let ws             = null;
let wsRetries      = 0;
let _cfIdentity    = null;
let _userProfile   = {{}};

async function loadCfIdentity() {{
  try {{
    const [meRes, profileRes] = await Promise.all([
      fetch('/api/identity/me'),
      fetch('/api/profile')
    ]);
    _cfIdentity = await meRes.json();
    _userProfile = await profileRes.json();
    applyUserProfile(_userProfile);
    // update greeting
    const nameEl = document.getElementById('nav-user-name');
    const name = _userProfile.greeting_name || _cfIdentity.display_name;
    if (nameEl && name) nameEl.textContent = name;
    const greetEl = document.getElementById('nav-greeting');
    if (greetEl && name) {{
      const hour = new Date().getHours();
      const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
      greetEl.textContent = greeting + ', ' + name;
    }}
  }} catch(e) {{
    _cfIdentity = {{user_id: 'chris', display_name: 'Chris'}};
    _userProfile = {{}};
  }}
}}

function applyUserProfile(profile) {{
  if (!profile) return;
  // Apply theme if different from current cookie
  const currentTheme = document.cookie.split(';').map(c=>c.trim()).find(c=>c.startsWith('jarvis-theme='));
  const cookieTheme = currentTheme ? currentTheme.split('=')[1] : 'glass';
  if (profile.theme && profile.theme !== cookieTheme) {{
    // Set cookie and reload to apply theme
    document.cookie = 'jarvis-theme=' + profile.theme + '; path=/; max-age=31536000';
    // Only reload if theme actually differs (avoid reload loop)
    const urlParams = new URLSearchParams(window.location.search);
    if (!urlParams.get('_theme_applied')) {{
      window.location.href = window.location.pathname + '?_theme_applied=1';
    }}
  }}
  // Update overview greeting
  const greetEl = document.getElementById('overview-greeting');
  if (greetEl) {{
    const name = profile.greeting_name || (_cfIdentity && _cfIdentity.display_name) || '';
    if (name) {{
      const hour = new Date().getHours();
      const salute = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
      greetEl.textContent = salute + ', ' + name + '.';
    }} else {{
      greetEl.textContent = '';
    }}
  }}
}}

// Returns a Set of card IDs that the current user's profile has hidden
/* ── User identity helpers ──────────────────────────────────────── */
function getCurrentUserId() {{
  return window.localStorage.getItem('jarvis-claimed-user-v1') || 'chris';
}}
function isChildUser() {{
  // All family members are treated as adults — no content filtering
  return false;
}}
function switchUser() {{
  window.localStorage.removeItem('jarvis-claimed-user-v1');
  window.sessionStorage.removeItem('jarvis-wau-skipped');
  wauShow();
}}

function toggleMobileNav() {{
  const nav = document.querySelector('.nav-bar');
  const overlay = document.getElementById('nav-drawer-overlay');
  const ham = document.getElementById('nav-hamburger');
  if (!nav) return;
  const isOpen = nav.classList.contains('mobile-open');
  if (isOpen) {{
    nav.classList.remove('mobile-open');
    if (overlay) overlay.classList.remove('active');
    if (ham) ham.textContent = '☰';
  }} else {{
    nav.classList.add('mobile-open');
    if (overlay) overlay.classList.add('active');
    if (ham) ham.textContent = '✕';
  }}
}}

function closeMobileNav() {{
  const nav = document.querySelector('.nav-bar');
  const overlay = document.getElementById('nav-drawer-overlay');
  const ham = document.getElementById('nav-hamburger');
  if (nav) nav.classList.remove('mobile-open');
  if (overlay) overlay.classList.remove('active');
  if (ham) ham.textContent = '☰';
}}

function _getHiddenCards() {{
  const dash = (_userProfile && _userProfile.dashboard) || {{}};
  const hidden = new Set();
  if (dash.show_health     === false) hidden.add('health');
  if (dash.show_chronicle  === false) hidden.add('chronicle');
  if (dash.show_dining     === false) hidden.add('dining');
  if (dash.show_publishing === false) hidden.add('publishing');
  if (dash.show_finance    === false) hidden.add('finance');
  // Child-safe mode: non-adult users see only family/school-relevant cards
  if (isChildUser()) {{
    ['briefing','approvals','health','email','agents','catalyst',
     'chronicle','jarvis_costs','maps_usage'].forEach(c => hidden.add(c));
  }}
  return hidden;
}}

async function profileSaveSettings() {{
  const msg = document.getElementById('profile-settings-msg');
  const greetingName = document.getElementById('profile-greeting-name')?.value.trim();
  const theme = document.getElementById('profile-theme')?.value;
  const timezone = document.getElementById('profile-timezone')?.value;
  const dashboard = {{
    show_health:     document.getElementById('profile-show-health')?.checked ?? true,
    show_chronicle:  document.getElementById('profile-show-chronicle')?.checked ?? true,
    show_dining:     document.getElementById('profile-show-dining')?.checked ?? true,
    show_publishing: document.getElementById('profile-show-publishing')?.checked ?? false,
    show_finance:    document.getElementById('profile-show-finance')?.checked ?? false,
  }};
  try {{
    const r = await fetch('/api/profile', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{greeting_name: greetingName, theme, timezone, dashboard}})
    }});
    const d = await r.json();
    if (d.ok) {{
      _userProfile = d.profile;
      if (msg) msg.textContent = '✓ Settings saved.';
      applyUserProfile(d.profile);
    }} else {{
      if (msg) msg.textContent = 'Error saving.';
    }}
  }} catch(e) {{
    if (msg) msg.textContent = 'Error: ' + e.message;
  }}
}}

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

function ensureDeviceId() {{
  /* Generate a stable device ID on first visit, register with server.
     Returns a Promise that resolves to the session response (or null on error). */
  let did = window.localStorage.getItem('jarvis-shell-device-id-v1') || '';
  if (!did) {{
    did = ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
      (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16));
    window.localStorage.setItem('jarvis-shell-device-id-v1', did);
  }}
  const fp = navigator.userAgent + '|' + navigator.language + '|' +
             screen.width + '|' + screen.height;
  return fetch('/api/identity/session', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{
      device_id:   did,
      fingerprint: fp,
      user_agent:  navigator.userAgent,
      device_type: /Mobi|Android/i.test(navigator.userAgent) ? 'mobile' : 'browser',
      last_host:   window.location.host,
      last_origin: window.location.origin,
    }})
  }})
  .then(r => r.ok ? r.json() : null)
  .then(d => {{
    if (d && d.device && d.device.device_id) {{
      window.localStorage.setItem('jarvis-shell-device-id-v1', d.device.device_id);
    }}
    return d;
  }})
  .catch(() => null);
}}

/* ── Who Are You overlay ──────────────────────────────────────────── */

function wauShow() {{
  const ov = document.getElementById('wau-overlay');
  if (ov) ov.classList.remove('hidden');
}}

function wauHide() {{
  const ov = document.getElementById('wau-overlay');
  if (ov) {{
    ov.style.animation = 'modal-overlay-in 0.2s ease reverse forwards';
    setTimeout(() => ov.classList.add('hidden'), 200);
  }}
}}

async function wauSelect(userId) {{
  const status = document.getElementById('wau-status');
  const grid   = document.getElementById('wau-grid');
  const sub    = document.getElementById('wau-subtitle');

  /* Highlight chosen card */
  if (grid) grid.querySelectorAll('.wau-card').forEach(c => {{
    c.style.opacity = c.getAttribute('onclick') === "wauSelect('" + userId + "')" ? '1' : '0.35';
    c.style.pointerEvents = 'none';
  }});
  if (sub)    sub.textContent  = 'Setting up your profile…';
  if (status) status.textContent = '';

  let deviceId = window.localStorage.getItem('jarvis-shell-device-id-v1') || '';
  if (!deviceId) {{
    /* shouldn't happen, but generate on the spot */
    deviceId = ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
      (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16));
    window.localStorage.setItem('jarvis-shell-device-id-v1', deviceId);
  }}

  const nameMap = {{chris:"Chris's Mac", rebekah:"Rebekah's Device",
                    caleb:"Caleb's Computer", anna:"Anna's Device"}};
  const displayMap = {{chris:"Chris", rebekah:"Rebekah", caleb:"Caleb", anna:"Anna"}};
  const greetMap   = {{chris:"Good to see you, Sir.",
                       rebekah:"Welcome back, Ma'am.",
                       caleb:"Hey Caleb! Ready to go?",
                       anna:"Hi Anna! Welcome to JARVIS."}};
  const deviceName = (nameMap[userId] || userId + "'s Device")
    .replace("Mac", navigator.userAgent.includes('iPhone') ? 'iPhone'
           : navigator.userAgent.includes('iPad') ? 'iPad'
           : navigator.userAgent.includes('Mac') ? 'Mac' : 'Device');

  try {{
    const r = await fetch('/api/identity/device', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        device_id:     deviceId,
        owner_user_id: userId,
        device_name:   deviceName,
        device_type:   'browser'
      }})
    }});
    const d = await r.json();
    if (d.ok) {{
      if (status) {{
        status.style.color = '#00D4FF';
        status.textContent = greetMap[userId] || 'Welcome!';
      }}
      /* Store claimed user so we never prompt again on this browser */
      window.localStorage.setItem('jarvis-claimed-user-v1', userId);
      setTimeout(() => {{
        wauHide();
        // Re-render overview to apply user-specific card filtering
        if (typeof loadLayoutState === 'function') loadLayoutState();
        if (typeof loadFamilyPresence === 'function') loadFamilyPresence();
      }}, 1200);
    }} else {{
      if (status) {{ status.style.color = '#f87171'; status.textContent = d.detail || 'Something went wrong — try again.'; }}
      if (grid) grid.querySelectorAll('.wau-card').forEach(c => {{
        c.style.opacity = '1'; c.style.pointerEvents = '';
      }});
    }}
  }} catch(e) {{
    if (status) {{ status.style.color = '#f87171'; status.textContent = 'Network error — try again.'; }}
    if (grid) grid.querySelectorAll('.wau-card').forEach(c => {{
      c.style.opacity = '1'; c.style.pointerEvents = '';
    }});
  }}
}}

function wauGuest() {{
  /* User doesn't want to identify — remember this choice for the session */
  window.sessionStorage.setItem('jarvis-wau-skipped', '1');
  wauHide();
}}

async function init() {{
  /* Register device then decide whether to show the "Who are you?" overlay.
     Show if: device has no claimed owner AND user hasn't skipped this session
     AND localStorage has no remembered claimed user. */
  const sessionData = await ensureDeviceId();
  const alreadyClaimed  = window.localStorage.getItem('jarvis-claimed-user-v1');
  const skippedThisSession = window.sessionStorage.getItem('jarvis-wau-skipped');
  const serverClaimed   = sessionData && sessionData.device && sessionData.device.owner_user_id;
  if (!alreadyClaimed && !skippedThisSession && !serverClaimed) {{
    wauShow();
  }}

  await loadCfIdentity();
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
  loadChronicleContext();
  loadOverviewAgents();
  loadOverviewCatalyst();
  loadOverviewChronicle();
  loadOverviewPublishing();
  loadOverviewReminders();
  loadJarvisTasks();
  loadIdeaInbox();
  // Voice system — wake word + TTS
  setTimeout(voiceInit, 1000); // slight delay so browser permissions settle
  loadOverviewHealth();
  loadLayoutState();
  loadDailyHealthScore();
  setInterval(checkAutoMode, 5 * 60 * 1000);
  updateModeBarClock();
  setInterval(updateModeBarClock, 60 * 1000);
  // Alert refresh every 90s when on overview
  setInterval(() => {{
    if (currentView === 'overview') {{
      fetch('/api/layout/state')
        .then(r => r.ok ? r.json() : null)
        .then(s => {{ if (s && s.alerts) applyAlertBanner(s.alerts); }})
        .catch(() => {{}});
    }}
  }}, 90000);

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

  // Close dropdowns on outside click
  document.addEventListener('click', () => {{
    hchatCloseDropdown();
  }});
}}

/* ═══════════════════════════════════════════════════════════════
   VIEW SWITCHING — CHROMATIC SHIFT LIVES HERE
═══════════════════════════════════════════════════════════════ */
function switchView(name) {{
  closeMobileNav();  // close drawer on mobile when navigating
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
    case 'overview':     loadLayoutState(); break;
    case 'forge':        forgeInit(); break;
    case 'agents':
      loadAgentRoster();   // populates AGENTS from /api/agents/roster
      loadLiveAgents();    // overlays runtime status
      // Auto-refresh every 30s while on this view
      _agentsRefreshTimer = setInterval(() => {{ loadLiveAgents(); }}, 30000);
      break;
    case 'huddle':       loadHuddle(); loadPassiveIncomePipeline(); loadDossiers(); loadPartyStatus(); loadIdeaInbox(); break;
    case 'notifications': loadNotificationCenter(); break;
    case 'publishing':   loadPublishing(); loadHomeProjects(); break;
    case 'intelligence': loadStatus(); break;
    case 'chronicle':    loadChronicle(); break;
    case 'faith':        loadFaith(); break;
    case 'email':        loadHomeEmail(); break;
    case 'calendar':     loadHomeCalendar(); break;
    case 'health':       loadHealth(); loadDailyHealthScore(); break;
    case 'workshop':     loadHomeTasks(); break;
    case 'catalyst':     loadWorkIntelligence(); break;
    case 'news':         loadNews(false); break;
    case 'home':         loadKasaDevices(); break;
    case 'navigate':     initNavView(); break;
    case 'dining':       loadDiningView(); break;
    case 'journey':      loadJourneyView(); break;
  }}
}}

/* ═══════════════════════════════════════════════════════════════
   JOURNEY TRACKING (Phase 5 + 6)
═══════════════════════════════════════════════════════════════ */
let _journeyDays = 30;
let _journeyAllEvents = [];

async function loadJourneyView() {{
  try {{
    const [journeyRes, statsRes, layoutRes] = await Promise.all([
      fetch('/api/journey?days=' + _journeyDays),
      fetch('/api/journey/stats?days=30'),
      fetch('/api/layout/state'),
    ]);
    const journey = await journeyRes.json();
    const stats   = await statsRes.json();
    const layout  = layoutRes.ok ? await layoutRes.json() : {{}};

    _journeyAllEvents = journey.events || [];

    // Stats strip
    const byType = stats.by_type || {{}};
    const setEl = (id, v) => {{ const el = document.getElementById(id); if(el) el.textContent = v ?? '—'; }};
    setEl('journey-total',  stats.total || 0);
    setEl('journey-tasks',  (byType.task_completed || 0));
    setEl('journey-ideas',  (byType.idea_captured  || 0));
    setEl('journey-briefs', (byType.brief_received || 0));

    // Update subtitle with user name
    const sub = document.getElementById('journey-subtitle');
    if (sub) {{
      const name = (_userProfile && _userProfile.greeting_name) || (_cfIdentity && _cfIdentity.display_name) || 'Your';
      sub.textContent = name + "'s story with JARVIS";
    }}

    // Insights (Phase 6)
    const insights = layout.insights || [];
    const insightsCard = document.getElementById('journey-insights-card');
    const insightsList = document.getElementById('journey-insights-list');
    if (insightsCard && insightsList) {{
      if (insights.length > 0) {{
        insightsCard.style.display = '';
        insightsList.innerHTML = insights.map(txt =>
          '<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:rgba(255,255,255,0.05);border-radius:8px;">' +
          '<span style="font-size:16px;">💡</span><span style="font-size:13px;color:rgba(255,255,255,0.75);">' + escHtml(txt) + '</span></div>'
        ).join('');
      }} else {{
        insightsCard.style.display = 'none';
      }}
    }}

    renderJourneyTimeline(_journeyAllEvents);

    // Show load-more button
    const loadMoreBtn = document.getElementById('journey-load-more');
    if (loadMoreBtn) loadMoreBtn.style.display = _journeyAllEvents.length >= 200 ? '' : 'none';
  }} catch(e) {{
    console.error('loadJourneyView failed', e);
  }}
}}

const EVENT_META = {{
  task_created:      {{ icon: '✅', label: 'Task created' }},
  task_completed:    {{ icon: '🏁', label: 'Task completed' }},
  task_deleted:      {{ icon: '🗑', label: 'Task removed' }},
  reminder_created:  {{ icon: '🔔', label: 'Reminder set' }},
  reminder_completed:{{ icon: '✓',  label: 'Reminder done' }},
  approval_actioned: {{ icon: '⚡', label: 'Approval actioned' }},
  brief_received:    {{ icon: '📋', label: 'Morning brief read' }},
  chronicle_entry:   {{ icon: '📖', label: 'Chronicle entry' }},
  agent_run:         {{ icon: '🤖', label: 'Agent activated' }},
  kdp_sync:          {{ icon: '📚', label: 'KDP data synced' }},
  idea_captured:     {{ icon: '💡', label: 'Idea captured' }},
  login:             {{ icon: '🌐', label: 'Session started' }},
}};

function renderJourneyTimeline(events) {{
  const container = document.getElementById('journey-timeline');
  if (!container) return;
  if (!events || events.length === 0) {{
    container.innerHTML = '<div style="color:rgba(255,255,255,0.3);font-size:13px;padding:20px 0;">No events yet — start using JARVIS to build your journey.</div>';
    return;
  }}

  let html = '';
  let lastDay = '';
  events.forEach(ev => {{
    const d = new Date(ev.ts);
    const dayKey = d.toLocaleDateString([], {{weekday:'long', month:'long', day:'numeric'}});
    if (dayKey !== lastDay) {{
      html += '<div class="journey-day-header">' + escHtml(dayKey) + '</div>';
      lastDay = dayKey;
    }}
    const meta = EVENT_META[ev.type] || {{ icon: '•', label: ev.type }};
    const timeStr = d.toLocaleTimeString([], {{hour:'2-digit', minute:'2-digit'}});
    const payloadText = ev.payload && (ev.payload.title || ev.payload.text || ev.payload.summary || '');
    html += '<div class="journey-event">' +
      '<span class="journey-event-icon">' + meta.icon + '</span>' +
      '<div class="journey-event-body">' +
        '<div class="journey-event-title">' + escHtml(meta.label) + '</div>' +
        (payloadText ? '<div class="journey-event-payload">' + escHtml(payloadText) + '</div>' : '') +
        '<div class="journey-event-time">' + timeStr + '</div>' +
      '</div>' +
    '</div>';
  }});
  container.innerHTML = html;
}}

function loadJourneyMore() {{
  _journeyDays += 30;
  loadJourneyView();
}}

/* ═══════════════════════════════════════════════════════════════
   KASA HOME AUTOMATION
═══════════════════════════════════════════════════════════════ */
let _kasaData = null;

function _deviceIcon(type) {{
  switch (type) {{
    case 'bulb':       return '💡';
    case 'color_bulb': return '🌈';
    case 'dimmer':     return '🔆';
    case 'camera':     return '📷';
    case 'strip':
    case 'plug':       return '🔌';
    default:           return '⚡';
  }}
}}

function renderKasaView(data) {{
  _kasaData = data;
  const el = document.getElementById('kasa-content');
  if (!el) return;
  if (!data.kasa_available || data.total === 0) {{
    el.innerHTML = '<div class="kasa-unavailable">'
      + '<div class="kasa-unavailable-icon">🏠</div>'
      + '<div>' + (data.total === 0 && data.kasa_available
          ? 'No Kasa devices found on your network.'
          : 'Kasa devices unavailable.') + '</div>'
      + '<button class="kasa-refresh-btn" onclick="loadKasaDevices(true)">↺ Scan Again</button></div>';
    return;
  }}
  const rooms = data.rooms || {{}};
  const scenes = data.scenes || [];
  const sceneHtml = scenes.map(function(s) {{
    return '<button class="kasa-scene-btn" id="kasa-scene-' + s.id + '" onclick="runKasaScene(&apos;' + s.id + '&apos;)">'
      + (s.icon || '✨') + ' ' + escHtml(s.name) + '</button>';
  }}).join('');
  const statsHtml =
    '<div class="kasa-stats">'
    + '<div class="kasa-stat"><div class="kasa-stat-val">' + data.total + '</div><div class="kasa-stat-label">Devices</div></div>'
    + '<div class="kasa-stat"><div class="kasa-stat-val on">' + data.on_count + '</div><div class="kasa-stat-label">On</div></div>'
    + '<div class="kasa-stat"><div class="kasa-stat-val">' + (data.total - data.on_count) + '</div><div class="kasa-stat-label">Off</div></div>'
    + '</div>';
  const roomsHtml = Object.entries(rooms).map(function(entry) {{
    const room = entry[0]; const devices = entry[1];
    return '<div class="kasa-room-section"><div class="kasa-room-label">' + room + '</div>'
      + '<div class="kasa-device-grid">' + devices.map(function(d) {{ return _kasaDeviceCard(d); }}).join('') + '</div></div>';
  }}).join('');
  el.innerHTML =
    '<div class="kasa-header-strip">' + statsHtml
    + '<button class="kasa-scene-btn" onclick="loadKasaDevices(true)" style="color:var(--text-3);">↺ Refresh</button></div>'
    + '<div class="kasa-scenes">' + sceneHtml + '</div>'
    + roomsHtml;
}}

let _hls = null;

async function startCameraStream(ip, cameraId) {{
  const btn = document.getElementById('cam-btn-' + cameraId);
  const vid = document.getElementById('cam-vid-' + cameraId);
  if (btn) {{ btn.textContent = '⏳ Starting…'; btn.disabled = true; }}

  try {{
    const res = await fetch('/api/kasa/stream/start', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ip: ip, camera_id: cameraId}}),
    }});
    const r = await res.json();
    if (!r.ok) {{
      if (btn) {{ btn.textContent = '▶ Live'; btn.disabled = false; }}
      alert('Stream failed: ' + r.error);
      return;
    }}

    if (vid) {{
      vid.style.display = 'block';
      if (typeof Hls !== 'undefined' && Hls.isSupported()) {{
        if (_hls) {{ _hls.destroy(); _hls = null; }}
        _hls = new Hls({{ lowLatencyMode: true }});
        _hls.loadSource(r.hls_url);
        _hls.attachMedia(vid);
        _hls.on(Hls.Events.MANIFEST_PARSED, function() {{ vid.play(); }});
      }} else if (vid.canPlayType('application/vnd.apple.mpegurl')) {{
        vid.src = r.hls_url;
        vid.play();
      }}
    }}
    if (btn) {{
      btn.textContent = '◼ Stop';
      btn.disabled = false;
      btn.onclick = function() {{ stopCameraStream(ip, cameraId); }};
    }}
  }} catch(e) {{
    if (btn) {{ btn.textContent = '▶ Live'; btn.disabled = false; }}
  }}
}}

async function stopCameraStream(ip, cameraId) {{
  const btn = document.getElementById('cam-btn-' + cameraId);
  const vid = document.getElementById('cam-vid-' + cameraId);
  if (_hls) {{ _hls.destroy(); _hls = null; }}
  if (vid) {{ vid.pause(); vid.src = ''; vid.style.display = 'none'; }}
  await fetch('/api/kasa/stream/stop', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{camera_id: cameraId}}),
  }});
  if (btn) {{
    btn.textContent = '▶ Live';
    btn.onclick = function() {{ startCameraStream(ip, cameraId); }};
  }}
}}

function _kasaDeviceCard(d) {{
  const uid = 'kd-' + (d.ip || d.alias).replace(/[^a-zA-Z0-9]/g, '_');

  if (d.device_type === 'camera') {{
    const cameraId = (d.ip || '').replace(/\\./g, '_');
    return '<div class="kasa-device-card kasa-camera-card" id="' + uid + '">'
      + '<div class="kasa-device-top">'
      + '<span class="kasa-device-icon">📷</span>'
      + '<div class="kasa-device-info"><div class="kasa-device-alias">' + escHtml(d.alias) + '</div>'
      + '<div class="kasa-device-model">' + escHtml(d.model || 'EC70') + ' · ' + escHtml(d.sw_ver || '') + '</div></div>'
      + '<button class="kasa-live-btn" id="cam-btn-' + cameraId + '" onclick="startCameraStream(&apos;' + d.ip + '&apos;,&apos;' + cameraId + '&apos;)">▶ Live</button></div>'
      + '<video id="cam-vid-' + cameraId + '" class="kasa-camera-video" controls muted playsinline style="display:none;width:100%;border-radius:8px;margin-top:8px;"></video>'
      + '</div>';
  }}

  const onCls = d.is_on ? 'device-on' : 'device-off';
  const checked = d.is_on ? 'checked' : '';
  const icon = _deviceIcon(d.device_type);
  let sliders = '';
  if (d.is_on && d.brightness != null) {{
    sliders +=
      '<div class="kasa-slider-row"><span class="kasa-slider-label">☀</span>'
      + '<input class="kasa-slider" type="range" min="1" max="100" value="' + d.brightness + '" id="' + uid + '-bright"'
      + ' oninput="document.getElementById(&apos;' + uid + '-bright-val&apos;).textContent=this.value+&apos;%&apos;"'
      + ' onchange="kasaSetBrightness(&apos;' + d.ip + '&apos;,&apos;' + d.alias + '&apos;,parseInt(this.value))">'
      + '<span class="kasa-slider-val" id="' + uid + '-bright-val">' + d.brightness + '%</span></div>';
  }}
  if (d.is_on && d.color_temp != null) {{
    sliders +=
      '<div class="kasa-slider-row"><span class="kasa-slider-label">K</span>'
      + '<input class="kasa-slider" type="range" min="2500" max="6500" value="' + d.color_temp + '" id="' + uid + '-ct"'
      + ' oninput="document.getElementById(&apos;' + uid + '-ct-val&apos;).textContent=this.value+&apos;K&apos;"'
      + ' onchange="kasaSetColorTemp(&apos;' + d.ip + '&apos;,&apos;' + d.alias + '&apos;,parseInt(this.value))">'
      + '<span class="kasa-slider-val" id="' + uid + '-ct-val">' + d.color_temp + 'K</span></div>';
  }}
  return '<div class="kasa-device-card ' + onCls + '" id="' + uid + '">'
    + '<div class="kasa-device-top">'
    + '<span class="kasa-device-icon">' + icon + '</span>'
    + '<div class="kasa-device-info"><div class="kasa-device-alias">' + escHtml(d.alias) + '</div>'
    + '<div class="kasa-device-model">' + escHtml(d.model || d.device_type) + '</div></div>'
    + '<label class="kasa-toggle"><input type="checkbox" ' + checked + ' onchange="kasaToggle(&apos;' + d.ip + '&apos;,&apos;' + d.alias + '&apos;)">'
    + '<div class="kasa-toggle-track"></div><div class="kasa-toggle-thumb"></div></label></div>'
    + sliders + '</div>';
}}

async function loadKasaDevices(force) {{
  const refresh = force ? '?refresh=true' : '';
  try {{
    const res = await fetch('/api/kasa/devices' + refresh);
    const data = await res.json();
    renderKasaView(data);
  }} catch(e) {{
    const el = document.getElementById('kasa-content');
    if (el) el.innerHTML = '<div class="kasa-unavailable"><div class="kasa-unavailable-icon">⚠️</div><div>Error loading devices</div></div>';
  }}
}}

async function kasaToggle(ip, alias) {{
  try {{
    const res = await fetch('/api/kasa/toggle', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ ip_or_alias: ip || alias }}),
    }});
    const r = await res.json();
    if (r.ok) setTimeout(function() {{ loadKasaDevices(false); }}, 500);
  }} catch(e) {{}}
}}

async function kasaSetBrightness(ip, alias, value) {{
  try {{
    await fetch('/api/kasa/set', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ ip_or_alias: ip || alias, brightness: value }}),
    }});
  }} catch(e) {{}}
}}

async function kasaSetColorTemp(ip, alias, value) {{
  try {{
    await fetch('/api/kasa/set', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ ip_or_alias: ip || alias, color_temp: value }}),
    }});
  }} catch(e) {{}}
}}

async function runKasaScene(sceneId) {{
  const btn = document.getElementById('kasa-scene-' + sceneId);
  if (btn) btn.classList.add('running');
  try {{
    const res = await fetch('/api/kasa/scene', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ scene_id: sceneId }}),
    }});
    const r = await res.json();
    if (r.ok) setTimeout(function() {{ loadKasaDevices(false); }}, 700);
  }} catch(e) {{}}
  setTimeout(function() {{ if (btn) btn.classList.remove('running'); }}, 1500);
}}

/* ═══════════════════════════════════════════════════════════════
   WORK INTELLIGENCE (CATALYST VIEW)
═══════════════════════════════════════════════════════════════ */
let _wiCurrentTab = 'overview';
let _wiBriefingData = null;

function switchWITab(btn, tabId) {{
  document.querySelectorAll('[data-wi-tab]').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.wi-pane').forEach(p => {{ p.style.display = 'none'; }});
  const pane = document.getElementById('wi-pane-' + tabId);
  if (pane) pane.style.display = '';
  _wiCurrentTab = tabId;
  if      (tabId === 'projects') wiLoadProjects();
  else if (tabId === 'tasks')    wiLoadTasks();
  else if (tabId === 'briefing') wiLoadBriefing();
  else if (tabId === 'signals')  wiLoadSignals();
}}

async function loadWorkIntelligence() {{
  wiLoadSummary();
  wiLoadCommitments();
  wiLoadWorkerStatus();
  wiLoadSurfaces();
}}

async function wiLoadSummary() {{
  try {{
    const res = await fetch('/api/wi/summary');
    if (!res.ok) return;
    const d = await res.json();
    const ps = document.getElementById('wi-stat-projects');
    const ts = document.getElementById('wi-stat-tasks');
    const os = document.getElementById('wi-stat-overdue');
    if (ps) ps.textContent = d.active_projects ?? '—';
    if (ts) ts.textContent = d.open_tasks ?? '—';
    if (os) os.textContent = d.overdue_commitments ?? '0';
    if (d.one_recommendation) {{
      const el = document.getElementById('wi-one-rec');
      if (el) el.innerHTML = '<p style="margin:0;">' + escHtml(d.one_recommendation) + '</p>';
    }}
  }} catch(e) {{ console.error('wiLoadSummary', e); }}
}}

async function wiLoadWorkerStatus() {{
  const el = document.getElementById('wi-stat-workers');
  if (!el) return;
  try {{
    const res = await fetch('/api/wi/workers/status');
    if (!res.ok) {{ el.textContent = '—'; return; }}
    const d = await res.json();
    const workers = d.workers || [];
    const running = workers.filter(w => w.status === 'running').length;
    el.innerHTML = workers.map(w => {{
      const cls = w.status === 'running' ? 'active' : w.status === 'error' ? 'error' : 'paused';
      return `<span class="wi-status-dot ${{cls}}"></span>`;
    }}).join('') + ` <span style="font-size:11px;color:var(--text-3);">${{running}}/${{workers.length}}</span>`;
  }} catch(e) {{ el.textContent = '—'; }}
}}

async function wiLoadCommitments() {{
  const el  = document.getElementById('wi-commitments');
  const cnt = document.getElementById('wi-commit-count');
  if (!el) return;
  try {{
    const res = await fetch('/api/wi/commitments');
    if (!res.ok) {{ el.innerHTML = '<div class="list-row"><div class="list-row-name" style="color:var(--text-3);">Unavailable</div></div>'; return; }}
    const d = await res.json();
    const items = d.commitments || [];
    if (cnt) cnt.textContent = items.length;
    if (!items.length) {{
      el.innerHTML = '<div class="list-row"><div class="list-row-name" style="color:var(--text-3);">No open commitments</div></div>';
      return;
    }}
    el.innerHTML = items.slice(0, 6).map(c => {{
      const isOverdue = (c.status || '').toLowerCase() === 'overdue';
      const statusCls = isOverdue ? 'overdue' : 'open';
      const dotCls    = isOverdue ? 'dot-error' : 'dot-gold';
      return `<div class="wi-commit-row">
        <span class="dot ${{dotCls}}" style="margin-top:3px;flex-shrink:0;"></span>
        <div class="wi-commit-text">${{escHtml(c.description || c.commitment_text || '—')}}</div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">
          <span class="wi-commit-status ${{statusCls}}">${{escHtml(c.status || 'open')}}</span>
          ${{c.due_date ? `<span class="wi-commit-due">${{fmtLocalTime(c.due_date, {{dateOnly:true}})}}</span>` : ''}}
        </div>
      </div>`;
    }}).join('');
    if (items.length > 6) {{
      el.innerHTML += `<div class="list-row" style="text-align:right;cursor:pointer;" onclick="switchWITab(document.querySelector('[data-wi-tab=tasks]'),'tasks')">
        <span style="font-size:11px;color:var(--hue);">${{items.length - 6}} more →</span></div>`;
    }}
  }} catch(e) {{ el.innerHTML = '<div class="list-row"><div class="list-row-name" style="color:var(--text-3);">Error loading commitments</div></div>'; }}
}}

async function wiLoadSurfaces() {{
  const el = document.getElementById('wi-surfaces');
  if (!el) return;
  try {{
    const res = await fetch('/api/wi/surface', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{}})
    }});
    if (!res.ok) {{ el.innerHTML = '<div style="color:var(--text-3);font-size:12px;">Nothing to surface right now.</div>'; return; }}
    const d = await res.json();
    const items = d.suggestions || d.surfaces || [];
    if (!items.length) {{ el.innerHTML = '<div style="color:var(--text-3);font-size:12px;">Nothing to surface right now.</div>'; return; }}
    el.innerHTML = items.slice(0, 4).map(s =>
      `<div class="wi-surface-item">
        <div class="wi-surface-title">${{escHtml(s.title || s.surface || '—')}}</div>
        ${{s.reason ? `<div class="wi-surface-reason">${{escHtml(s.reason)}}</div>` : ''}}
      </div>`
    ).join('');
  }} catch(e) {{ el.innerHTML = '<div style="color:var(--text-3);font-size:12px;">Nothing to surface right now.</div>'; }}
}}

async function wiLoadProjects() {{
  const el  = document.getElementById('wi-projects-list');
  const cnt = document.getElementById('wi-proj-count');
  if (!el) return;
  el.innerHTML = '<div class="list-row"><div class="list-row-name" style="color:var(--text-3);">Loading…</div></div>';
  try {{
    const res = await fetch('/api/wi/projects');
    if (!res.ok) {{ el.innerHTML = '<div class="list-row"><div class="list-row-name" style="color:var(--text-3);">Unavailable</div></div>'; return; }}
    const d = await res.json();
    const items = d.projects || [];
    if (cnt) cnt.textContent = items.length;
    if (!items.length) {{ el.innerHTML = '<div class="list-row"><div class="list-row-name" style="color:var(--text-3);">No projects yet</div></div>'; return; }}
    el.innerHTML = items.map(p => {{
      const health   = (p.health_status || p.status || 'active').toLowerCase().replace('_','-');
      const badgeCls = health === 'at-risk'   ? 'at-risk' :
                       health === 'on-track'  ? 'on-track' : 'active';
      const dotCls   = badgeCls === 'at-risk'  ? 'dot-gold' :
                       badgeCls === 'on-track' ? 'dot-success' : 'dot-active';
      return `<div class="wi-project-row">
        <span class="dot ${{dotCls}}" style="margin-top:3px;flex-shrink:0;"></span>
        <div class="wi-project-info">
          <div class="wi-project-name">${{escHtml(p.name || p.title || '—')}}</div>
          ${{p.description ? `<div class="wi-project-sub">${{escHtml(p.description.slice(0, 90))}}</div>` : ''}}
        </div>
        <span class="wi-project-badge ${{badgeCls}}">${{escHtml(health)}}</span>
      </div>`;
    }}).join('');
  }} catch(e) {{ el.innerHTML = '<div class="list-row"><div class="list-row-name" style="color:var(--crimson);">Error loading projects</div></div>'; }}
}}

async function wiLoadTasks() {{
  const el  = document.getElementById('wi-tasks-list');
  const cnt = document.getElementById('wi-tasks-count');
  if (!el) return;
  el.innerHTML = '<div class="list-row"><div class="list-row-name" style="color:var(--text-3);">Loading…</div></div>';
  try {{
    const res = await fetch('/api/wi/tasks');
    if (!res.ok) {{ el.innerHTML = '<div class="list-row"><div class="list-row-name" style="color:var(--text-3);">Unavailable</div></div>'; return; }}
    const d = await res.json();
    const items = (d.tasks || []).filter(t => t.status !== 'completed');
    if (cnt) cnt.textContent = items.length;
    if (!items.length) {{ el.innerHTML = '<div class="list-row"><div class="list-row-name" style="color:var(--text-3);">All clear — no open tasks ✓</div></div>'; return; }}
    el.innerHTML = items.map(t => {{
      const pri    = parseInt(t.priority) || 3;
      const priCls = pri <= 1 ? 'p1' : pri === 2 ? 'p2' : 'p3';
      return `<div class="list-row" id="wi-task-${{t.id}}">
        <span class="wi-priority-ring ${{priCls}}" style="margin-top:3px;flex-shrink:0;"></span>
        <div style="flex:1;min-width:0;">
          <div class="list-row-name">${{escHtml(t.title || t.task_title || '—')}}</div>
          ${{t.project_name ? `<div class="list-row-sub">${{escHtml(t.project_name)}}</div>` : ''}}
        </div>
        <button class="wi-complete-btn" onclick="wiCompleteTask(${{t.id}})">Done</button>
      </div>`;
    }}).join('');
  }} catch(e) {{ el.innerHTML = '<div class="list-row"><div class="list-row-name" style="color:var(--crimson);">Error loading tasks</div></div>'; }}
}}

async function wiLoadBriefing() {{
  const el   = document.getElementById('wi-briefing-content');
  const meta = document.getElementById('wi-briefing-meta');
  if (!el) return;
  if (_wiBriefingData) {{ _wiRenderBriefing(_wiBriefingData); return; }}
  el.innerHTML = '<div class="skel" style="height:10px;width:85%;margin-bottom:6px;"></div><div class="skel" style="height:10px;width:70%;margin-bottom:6px;"></div><div class="skel" style="height:10px;width:60%;"></div>';
  try {{
    const res = await fetch('/api/wi/summary');
    if (!res.ok) throw new Error(res.status);
    const d = await res.json();
    if (d.latest_briefing) {{
      _wiBriefingData = d.latest_briefing;
      _wiRenderBriefing(d.latest_briefing);
    }} else {{
      el.innerHTML = '<div style="color:var(--text-3);font-size:12px;text-align:center;padding:20px 0;">No briefing yet. Workers run daily at the configured hour, or click ↻ Refresh to generate now.</div>';
    }}
  }} catch(e) {{ el.innerHTML = '<div style="color:var(--text-3);font-size:12px;">Unable to load briefing.</div>'; }}
}}

async function wiRefreshBriefing() {{
  const el = document.getElementById('wi-briefing-content');
  if (el) el.innerHTML = '<div style="text-align:center;padding:20px 0;color:var(--hue);">Generating briefing… <span style="font-family:var(--font-mono);font-size:10px;">(~15s)</span></div>';
  _wiBriefingData = null;
  try {{
    const res = await fetch('/api/wi/briefing/generate', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{}})
    }});
    if (!res.ok) throw new Error(res.status);
    const d = await res.json();
    _wiBriefingData = d;
    _wiRenderBriefing(d);
    showToast('Briefing generated ✓', 'success');
  }} catch(e) {{
    if (el) el.innerHTML = '<div style="color:var(--crimson);font-size:12px;">Generation failed — check worker logs.</div>';
  }}
}}

function _wiRenderBriefing(d) {{
  const el   = document.getElementById('wi-briefing-content');
  const meta = document.getElementById('wi-briefing-meta');
  if (!el) return;
  const narrative = d.narrative || d.briefing_text || d.content || '';
  if (!narrative) {{ el.innerHTML = '<div style="color:var(--text-3);font-size:12px;">No briefing content available.</div>'; return; }}
  el.innerHTML = narrative.split('\\n').filter(l => l.trim()).map(line => {{
    if (/^#+\\s/.test(line))  return `<p style="font-weight:700;color:var(--text-1);margin:12px 0 4px;">${{escHtml(line.replace(/^#+\\s*/,''))}}</p>`;
    if (/^[-*]\\s/.test(line)) return `<p style="margin:3px 0 3px 10px;color:var(--text-2);">• ${{escHtml(line.replace(/^[-*]\\s*/,''))}}</p>`;
    return `<p style="margin:4px 0;">${{escHtml(line)}}</p>`;
  }}).join('');
  if (meta && d.generated_at) meta.textContent = 'Generated ' + fmtLocalTime(d.generated_at);
}}

async function wiLoadSignals() {{
  const el  = document.getElementById('wi-signals-list');
  const cnt = document.getElementById('wi-signals-count');
  if (!el) return;
  el.innerHTML = '<div class="list-row"><div class="list-row-name" style="color:var(--text-3);">Loading…</div></div>';
  try {{
    const res = await fetch('/api/wi/signals');
    if (!res.ok) {{ el.innerHTML = '<div class="list-row"><div class="list-row-name" style="color:var(--text-3);">Unavailable</div></div>'; return; }}
    const d = await res.json();
    const items = d.signals || [];
    if (cnt) cnt.textContent = items.length;
    if (!items.length) {{ el.innerHTML = '<div class="list-row"><div class="list-row-name" style="color:var(--text-3);">No recent signals</div></div>'; return; }}
    el.innerHTML = items.slice(0, 15).map(s => {{
      const crit   = (s.criticality || 'STANDARD').toUpperCase();
      const dotCls = crit === 'CRITICAL' ? 'dot-error' : crit === 'LOW' ? 'dot-standby' : 'dot-active';
      return `<div class="list-row">
        <span class="dot ${{dotCls}}" style="margin-top:3px;flex-shrink:0;"></span>
        <div style="flex:1;min-width:0;">
          <div class="list-row-name">${{escHtml((s.content || s.signal_text || '—').slice(0, 120))}}</div>
          <div class="list-row-sub">${{escHtml(s.signal_type || 'unknown')}} · ${{fmtLocalTime(s.created_at, {{short:true}})}}</div>
        </div>
        <span class="wi-signal-type">${{escHtml(crit)}}</span>
      </div>`;
    }}).join('');
  }} catch(e) {{ el.innerHTML = '<div class="list-row"><div class="list-row-name" style="color:var(--crimson);">Error loading signals</div></div>'; }}
}}

async function wiCompleteTask(taskId) {{
  const row = document.getElementById('wi-task-' + taskId);
  try {{
    const res = await fetch('/api/wi/tasks/' + taskId + '/complete', {{method: 'POST'}});
    if (res.ok) {{
      if (row) {{
        row.style.opacity = '0.4';
        row.style.transition = 'opacity 0.3s';
        setTimeout(() => row.remove(), 350);
      }}
      const cnt = document.getElementById('wi-tasks-count');
      if (cnt && cnt.textContent) cnt.textContent = Math.max(0, parseInt(cnt.textContent) - 1);
      const stat = document.getElementById('wi-stat-tasks');
      if (stat && stat.textContent) stat.textContent = Math.max(0, parseInt(stat.textContent) - 1);
      showToast('Task completed ✓', 'success');
    }} else {{ showToast('Could not complete task', 'warning'); }}
  }} catch(e) {{ showToast('Error completing task', 'error'); }}
}}

/* ═══════════════════════════════════════════════════════════════
   API CALLS
═══════════════════════════════════════════════════════════════ */
async function checkMcpStatus() {{
  const el = document.getElementById('mcp-status');
  try {{
    const res = await fetch('http://127.0.0.1:8788/', {{ signal: AbortSignal.timeout(2000) }});
    if (el) {{ el.textContent = 'connected ✓'; el.style.color = 'var(--green)'; }}
  }} catch {{
    if (el) {{ el.textContent = 'offline'; el.style.color = 'var(--red)'; }}
  }}
}}
// Check MCP status on load
setTimeout(checkMcpStatus, 3000);

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

async function loadNotificationCenter() {{
  const notifEl = document.getElementById('notification-center-list');
  const eventEl = document.getElementById('notification-event-list');
  const pendingEl = document.getElementById('notif-stat-pending');
  const activeEl = document.getElementById('notif-stat-active');
  const eventsEl = document.getElementById('notif-stat-events');
  if (!notifEl || !eventEl) return;

  try {{
    const [notifRes, eventRes] = await Promise.all([
      fetch('/api/apple/notifications'),
      fetch('/api/apple/events/recent?limit=20'),
    ]);
    if (!notifRes.ok || !eventRes.ok) {{
      throw new Error('notification center unavailable');
    }}
    const notifPayload = await notifRes.json();
    const eventPayload = await eventRes.json();
    const notifications = ((notifPayload || {{}}).data || {{}}).notifications || [];
    const events = ((eventPayload || {{}}).data || {{}}).events || [];

    const pendingCount = notifications.filter(n => (n.status || '') === 'pending').length;
    if (pendingEl) pendingEl.textContent = String(pendingCount);
    if (activeEl) activeEl.textContent = String(notifications.length);
    if (eventsEl) eventsEl.textContent = String(events.length);

    if (!notifications.length) {{
      notifEl.innerHTML = '<div class="list-row"><span class="dot dot-standby"></span><div><div class="list-row-name">No active notifications</div><div class="list-row-sub">JARVIS has no unresolved household attention items right now.</div></div></div>';
    }} else {{
      notifEl.innerHTML = notifications.map(item => {{
        const severity = String(item.severity || 'low').toLowerCase();
        const dotCls = severity === 'critical' ? 'dot-error' : severity === 'high' ? 'dot-active' : 'dot-standby';
        const actions = [];
        actions.push(`<button class="btn btn-navy btn-sm" onclick="notificationAction('${{item.id}}','seen')">Seen</button>`);
        actions.push(`<button class="btn btn-crimson btn-sm" onclick="notificationAction('${{item.id}}','dismiss')">Dismiss</button>`);
        actions.push(`<button class="btn btn-hue btn-sm" onclick="notificationAction('${{item.id}}','resolve')">Resolve</button>`);
        return `
          <div class="approval-item">
            <div style="display:flex;align-items:flex-start;gap:8px;">
              <span class="dot ${{dotCls}}" style="margin-top:5px;"></span>
              <div style="flex:1;min-width:0;">
                <div class="approval-title">${{escHtml(item.title || 'JARVIS Alert')}}</div>
                <div class="approval-meta">${{escHtml(String(item.category || 'system').toUpperCase())}} &nbsp;·&nbsp; ${{escHtml(String(item.status || 'pending').toUpperCase())}}</div>
                <div style="font-size:12px;color:var(--text-2);margin-top:6px;line-height:1.5;">${{escHtml(item.detail || item.body || '')}}</div>
                ${{item.why_now ? `<div style="font-size:10px;color:var(--gold);margin-top:6px;">${{escHtml(item.why_now)}}</div>` : ''}}
                <div class="approval-actions" style="margin-top:10px;">${{actions.join('')}}</div>
              </div>
            </div>
          </div>
        `;
      }}).join('');
    }}

    if (!events.length) {{
      eventEl.innerHTML = '<div class="list-row"><div class="list-row-name" style="color:var(--text-3);">No recent events</div></div>';
    }} else {{
      eventEl.innerHTML = events.slice(0, 12).map(item => {{
        const severity = String(item.severity || 'low').toLowerCase();
        const dotCls = severity === 'critical' ? 'dot-error' : severity === 'high' ? 'dot-active' : 'dot-standby';
        return `
          <div class="list-row">
            <span class="dot ${{dotCls}}" style="margin-top:3px;flex-shrink:0;"></span>
            <div style="flex:1;min-width:0;">
              <div class="list-row-name">${{escHtml(item.title || 'Event')}}</div>
              <div class="list-row-sub">${{escHtml(item.domain || 'system')}} · ${{fmtLocalTime(item.ts, {{short:true}})}}</div>
              ${{item.detail ? `<div style="font-size:11px;color:var(--text-2);margin-top:4px;line-height:1.5;">${{escHtml(item.detail)}}</div>` : ''}}
            </div>
          </div>
        `;
      }}).join('');
    }}
  }} catch (e) {{
    notifEl.innerHTML = '<div class="list-row"><div class="list-row-name" style="color:var(--crimson);">Could not load notifications</div></div>';
    eventEl.innerHTML = '<div class="list-row"><div class="list-row-name" style="color:var(--crimson);">Could not load event spine</div></div>';
  }}
}}

async function notificationAction(id, action) {{
  const endpoint = action === 'seen'
    ? 'seen'
    : action === 'dismiss'
      ? 'dismiss'
      : 'resolve';
  try {{
    const res = await fetch(`/api/apple/notifications/${{id}}/${{endpoint}}`, {{ method: 'POST' }});
    if (!res.ok) {{
      showToast('Notification action failed', 'error');
      return;
    }}
    showToast(`Notification ${{action}}`, action === 'resolve' ? 'success' : 'info');
    loadNotificationCenter();
  }} catch (e) {{
    showToast('No connection', 'error');
  }}
}}

async function loadPublishing() {{
  try {{
    const res = await fetch('/api/publishing/dashboard');
    if (!res.ok) {{ console.warn('loadPublishing', res.status); return; }}
    const data = await res.json();
    renderPublishing(data);
  }} catch(e) {{ console.error('loadPublishing failed', e); }}
  loadLaunchPanel();
  loadKdpView();
}}

// ── KDP / Amazon Publishing ────────────────────────────────────

async function loadKdpView() {{
  try {{
    const [statusRes, booksRes, salesRes] = await Promise.all([
      fetch('/api/kdp/status'),
      fetch('/api/kdp/books'),
      fetch('/api/kdp/sales')
    ]);
    const status = await statusRes.json();
    const booksData = await booksRes.json();
    const salesData = await salesRes.json();

    const notConfigured = document.getElementById('kdp-not-configured');
    const statsStrip = document.getElementById('kdp-stats-strip');
    const insightsEl = document.getElementById('kdp-insights');
    const booksSection = document.getElementById('kdp-books-section');
    const statusEl = document.getElementById('kdp-view-status');

    if (!status.configured || status.status === 'never_synced') {{
      if (notConfigured) notConfigured.style.display = '';
      if (statsStrip) statsStrip.style.display = 'none';
      return;
    }}

    if (notConfigured) notConfigured.style.display = 'none';
    if (statsStrip) statsStrip.style.display = '';

    // Update status text
    if (statusEl && status.last_synced_at) {{
      const ago = Math.round((Date.now() - new Date(status.last_synced_at)) / 60000);
      statusEl.textContent = 'Synced ' + (ago < 60 ? ago + 'm ago' : Math.round(ago/60) + 'h ago');
    }}

    // Stats
    const books = booksData.books || [];
    const latestSales = (salesData.history || []).slice(-1)[0] || {{}};
    document.getElementById('kdp-stat-books').textContent = books.length || '—';
    document.getElementById('kdp-stat-units').textContent = latestSales.units_sold ?? '—';
    document.getElementById('kdp-stat-kenp').textContent = latestSales.kenp_pages_read != null
      ? (latestSales.kenp_pages_read > 999 ? (latestSales.kenp_pages_read/1000).toFixed(1)+'K' : latestSales.kenp_pages_read)
      : '—';
    document.getElementById('kdp-stat-royalties').textContent = latestSales.royalties_usd != null
      ? '$' + latestSales.royalties_usd.toFixed(2) : '—';

    // Insights
    const insights = booksData.insights || [];
    if (insights.length && insightsEl) {{
      insightsEl.style.display = '';
      const colors = {{positive:'#4ade80', attention:'#fbbf24', info:'var(--text-2)'}};
      document.getElementById('kdp-insights-list').innerHTML = insights.map(i => `
        <div style="display:flex;align-items:flex-start;gap:10px;padding:10px 14px;background:var(--surface-2);border-radius:10px;border:1px solid var(--border);margin-bottom:8px;">
          <span style="color:${{colors[i.type]||'var(--text-2)'}};">${{i.type==='positive'?'↑':i.type==='attention'?'⚠':'ℹ'}}</span>
          <div>
            ${{i.book ? `<div style="font-size:11px;font-weight:600;color:var(--text-1);">${{escHtml(i.book)}}</div>` : ''}}
            <div style="font-size:12px;color:var(--text-2);">${{escHtml(i.message)}}</div>
          </div>
        </div>
      `).join('');
    }}

    // Books list
    if (books.length && booksSection) {{
      booksSection.style.display = '';
      document.getElementById('kdp-books-list').innerHTML = books.map(b => `
        <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 14px;background:var(--surface-2);border-radius:10px;border:1px solid var(--border);margin-bottom:8px;">
          <div style="flex:1;min-width:0;">
            <div style="font-size:13px;font-weight:600;color:var(--text-1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${{escHtml(b.title || 'Untitled')}}</div>
            <div style="font-size:11px;color:var(--text-3);font-family:var(--font-mono);">${{escHtml(b.asin || '')}} · ${{escHtml(b.status || '—')}}</div>
          </div>
          <span style="padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;background:${{b.status==='Live'?'rgba(74,222,128,.15)':'rgba(255,255,255,.06)'}}; color:${{b.status==='Live'?'#4ade80':'var(--text-3)'}};">${{escHtml(b.status||'—')}}</span>
        </div>
      `).join('');
    }}
  }} catch(e) {{
    console.error('KDP view error:', e);
  }}
}}

async function kdpViewSync() {{
  const btn = document.getElementById('kdp-sync-btn');
  const statusEl = document.getElementById('kdp-view-status');
  if (btn) btn.textContent = '⏳ Syncing…';
  if (statusEl) statusEl.textContent = 'Syncing with KDP…';
  try {{
    const r = await fetch('/api/kdp/sync', {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: '{{}}'}});
    const d = await r.json();
    if (statusEl) statusEl.textContent = d.ok ? 'Sync complete' : ('Error: ' + (d.error || 'unknown'));
    if (d.ok) loadKdpView();
  }} catch(e) {{
    if (statusEl) statusEl.textContent = 'Sync failed';
  }} finally {{
    if (btn) btn.textContent = '↻ Sync';
  }}
}}

// ── Book Launch Panel ──────────────────────────────────────────

let _launchCurrentSlug = '';
let _launchCurrentAssets = null;

async function loadLaunchPanel() {{
  const listEl  = document.getElementById('publishing-launch-books');
  const badgeEl = document.getElementById('launch-books-badge');
  if (listEl) listEl.innerHTML = '<div class="loading-state" style="padding:12px 0;font-size:12px;color:var(--text-3);">Scanning…</div>';
  try {{
    const res = await fetch('/api/publishing/launch-scan');
    const data = await res.json();
    if (!data.bridge_available) {{
      if (listEl) listEl.innerHTML = '<div style="font-size:12px;color:var(--text-3);padding:8px 0;">Ghostwritr not connected — start Ghostwritr to see your books.</div>';
      if (badgeEl) badgeEl.textContent = '—';
      return;
    }}
    const books = data.books || [];
    if (badgeEl) badgeEl.textContent = books.length + ' book' + (books.length !== 1 ? 's' : '');
    if (!books.length) {{
      if (listEl) listEl.innerHTML = '<div style="font-size:12px;color:var(--text-3);padding:8px 0;">No books found in Ghostwritr.</div>';
      return;
    }}
    if (listEl) listEl.innerHTML = books.map(b => {{
      const hasPill = b.has_assets
        ? '<span class="pill pill-green" style="font-size:9px;">Ready</span>'
        : (b.trigger ? '<span class="pill pill-gold" style="font-size:9px;">Generate</span>'
                     : '<span class="pill" style="font-size:9px;">—</span>');
      const genBtn = !b.has_assets
        ? `<button class="btn btn-hue btn-sm" style="font-size:10px;" onclick="generateLaunchAssets('${{escHtml(b.slug)}}', this)">Generate</button>`
        : '';
      const viewBtn = b.has_assets
        ? `<button class="btn btn-sm" style="font-size:10px;" onclick="viewLaunchAssets('${{escHtml(b.slug)}}')">View</button>`
        : '';
      const regenBtn = b.has_assets
        ? `<button class="btn btn-sm" style="font-size:10px;" onclick="generateLaunchAssets('${{escHtml(b.slug)}}', this, true)">↺</button>`
        : '';
      return `<div class="launch-book-row">
        <div>
          <div class="launch-book-title">${{escHtml(b.title || b.slug)}}</div>
          <div class="launch-book-stage">${{escHtml(b.book_status || '')}} · ${{escHtml(b.current_stage || '—')}}</div>
        </div>
        ${{hasPill}}
        <div style="margin-left:auto;display:flex;gap:6px;">${{genBtn}}${{viewBtn}}${{regenBtn}}</div>
      </div>`;
    }}).join('');
  }} catch(e) {{
    if (listEl) listEl.innerHTML = '<div style="font-size:12px;color:var(--text-3);">Scan failed: ' + escHtml(String(e)) + '</div>';
  }}
}}

async function generateLaunchAssets(slug, btn, force) {{
  if (btn) {{ btn.disabled = true; btn.textContent = '⏳'; }}
  showToast('Generating launch assets for ' + slug + '… this takes a few minutes.', 'info');
  try {{
    const res = await fetch('/api/publishing/launch/' + encodeURIComponent(slug) + '/generate', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ force: !!force, trigger: 'pre_launch' }}),
    }});
    if (res.ok) {{
      showToast('Generation started — refresh in a few minutes.', 'success');
      setTimeout(() => loadLaunchPanel(), 3000);
    }} else {{
      showToast('Failed to start generation', 'error');
      if (btn) {{ btn.disabled = false; btn.textContent = force ? '↺' : 'Generate'; }}
    }}
  }} catch(e) {{
    showToast('Error: ' + e, 'error');
    if (btn) {{ btn.disabled = false; btn.textContent = force ? '↺' : 'Generate'; }}
  }}
}}

async function viewLaunchAssets(slug) {{
  _launchCurrentSlug = slug;
  const panel = document.getElementById('publishing-launch-assets');
  const titleEl = document.getElementById('launch-asset-title');
  const contentEl = document.getElementById('launch-asset-content');
  if (panel) panel.style.display = '';
  if (contentEl) contentEl.innerHTML = '<div style="font-size:12px;color:var(--text-3);">Loading…</div>';
  try {{
    const res = await fetch('/api/publishing/launch/' + encodeURIComponent(slug));
    const data = await res.json();
    _launchCurrentAssets = data;
    if (titleEl) titleEl.textContent = (data.title || slug) + ' — Launch Assets';
    switchLaunchTab(document.querySelector('.launch-tab[data-tab="dispatch"]'), 'dispatch');
    panel.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  }} catch(e) {{
    if (contentEl) contentEl.innerHTML = '<div style="color:var(--red);">Failed to load: ' + escHtml(String(e)) + '</div>';
  }}
}}

async function regenerateLaunchAssets() {{
  if (!_launchCurrentSlug) return;
  await fetch('/api/publishing/launch/' + encodeURIComponent(_launchCurrentSlug), {{ method: 'DELETE' }});
  await generateLaunchAssets(_launchCurrentSlug, null, true);
}}

function switchLaunchTab(btnEl, tab) {{
  document.querySelectorAll('.launch-tab').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  const contentEl = document.getElementById('launch-asset-content');
  if (!contentEl || !_launchCurrentAssets) return;
  const a = _launchCurrentAssets.assets || {{}};
  let html = '';

  // Ghostwritr post-production agent tabs
  const agentLabels = {{
    dispatch: ['📣 Dispatch — Social Campaign', 'SOCIAL_CAMPAIGN'],
    bureau:   ['📰 Bureau — Press Kit',         'PRESS_KIT'],
    marquee:  ['🏷️ Marquee — Retail Listing',   'LAUNCH_LISTING'],
    studio:   ['🎙️ Studio — Audio Prep',         'AUDIO_PREP'],
    podium:   ['🎓 Podium — Course Design',      'COURSE_DESIGN'],
    lectern:  ['🎤 Lectern — Speaking Kit',      'SPEAKING_KIT'],
  }};
  if (tab in agentLabels) {{
    const [label, stageKey] = agentLabels[tab];
    const content = (a && a[tab]) ? a[tab] : null;
    if (!content) {{
      contentEl.innerHTML = `<div style="padding:20px;text-align:center;">
        <div style="font-size:13px;color:var(--text-3);margin-bottom:12px;">${{label}} — not yet generated</div>
        <div style="font-size:11px;color:var(--text-3);">Complete the <strong>${{stageKey}}</strong> stage in Ghostwritr to generate this asset.<br>It will appear here automatically when committed.</div>
      </div>`;
    }} else {{
      const encoded = encodeURIComponent(content);
      contentEl.innerHTML = `<div style="margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:11px;color:var(--text-3);">${{label}}</span>
        <button class="btn btn-sm launch-copy-btn" onclick="launchCopy(this,'${{encoded}}')" style="font-size:10px;">Copy All</button>
      </div>
      <pre style="white-space:pre-wrap;font-size:11px;line-height:1.6;color:var(--text-1);background:var(--surface-2);padding:16px;border-radius:6px;overflow-x:auto;">${{escHtml(content)}}</pre>`;
    }}
    return;
  }}

  if (tab === 'twitter') {{
    // Quick Social — combines twitter, linkedin, emails quick drafts
    const posts = a.twitter || [];
    const li = a.linkedin || [];
    const em = a.emails || [];
    if (!posts.length && !li.length && !em.length) {{
      contentEl.innerHTML = '<div style="padding:20px;text-align:center;font-size:12px;color:var(--text-3);">No quick social drafts yet. Click Generate to create draft assets, or complete the Dispatch stage in Ghostwritr for the full campaign.</div>';
      return;
    }}
    let html = '';
    if (posts.length) {{
      html += '<div style="font-size:11px;color:var(--text-3);margin-bottom:8px;font-weight:600;">𝕏 TWITTER / X</div>';
      html += posts.map(p => `<div class="launch-post-card"><div class="post-type-label">${{escHtml(p.type||'')}}</div><div>${{escHtml(p.text||'')}}</div><button class="launch-copy-btn" onclick="launchCopy(this,'${{encodeURIComponent(p.text||'')}}')" style="margin-top:6px;font-size:10px;">Copy</button></div>`).join('');
    }}
    if (li.length) {{
      html += '<div style="font-size:11px;color:var(--text-3);margin:16px 0 8px;font-weight:600;">LINKEDIN</div>';
      html += li.map(p => `<div class="launch-post-card"><div class="post-type-label">${{escHtml(p.type||'')}}</div><div>${{escHtml(p.text||'')}}</div><button class="launch-copy-btn" onclick="launchCopy(this,'${{encodeURIComponent(p.text||'')}}')" style="margin-top:6px;font-size:10px;">Copy</button></div>`).join('');
    }}
    if (em.length) {{
      html += '<div style="font-size:11px;color:var(--text-3);margin:16px 0 8px;font-weight:600;">EMAILS</div>';
      html += em.map(e => `<div class="launch-post-card"><div class="post-type-label">${{escHtml(e.type||'')}}</div>${{(e.subjects||[]).map(s=>`<div style="font-size:10px;color:var(--text-2);">Subject: ${{escHtml(s)}}</div>`).join('')}}<div style="margin-top:6px;">${{escHtml(e.body||'')}}</div></div>`).join('');
    }}
    contentEl.innerHTML = html;
    return;

  }} else if (tab === 'linkedin') {{
    const posts = a.linkedin || [];
    if (!posts.length) {{ html = '<div style="color:var(--text-3);font-size:12px;">No posts yet.</div>'; }}
    else html = posts.map(p => `
      <div class="launch-post-card">
        <div class="launch-post-body"><span style="font-size:9px;font-weight:700;color:var(--hue);text-transform:uppercase;letter-spacing:0.06em;">${{escHtml(p.type||'POST')}}</span><br>${{escHtml(p.text||'')}}</div>
        <button class="launch-copy-btn" onclick="launchCopy(this,'${{encodeURIComponent(p.text||'')}}')">Copy</button>
      </div>`).join('');

  }} else if (tab === 'press') {{
    const text = a.press_release || '';
    html = `<div class="launch-post-card" style="flex-direction:column;gap:8px;">
      <div style="display:flex;justify-content:flex-end;"><button class="launch-copy-btn" onclick="launchCopy(this,'${{encodeURIComponent(text)}}')">Copy All</button></div>
      <div class="launch-post-body">${{escHtml(text) || '<span style="color:var(--text-3);">Not yet generated.</span>'}}</div>
    </div>`;

  }} else if (tab === 'emails') {{
    const emails = a.emails || [];
    if (!emails.length) {{ html = '<div style="color:var(--text-3);font-size:12px;">No emails yet.</div>'; }}
    else html = emails.map(e => `
      <div class="launch-post-card" style="flex-direction:column;gap:8px;">
        <div style="display:flex;align-items:center;gap:8px;">
          <span style="font-size:9px;font-weight:700;color:var(--hue);text-transform:uppercase;">${{escHtml(e.type||'')}}</span>
          <button class="launch-copy-btn" style="margin-left:auto;" onclick="launchCopy(this,'${{encodeURIComponent(e.body||'')}}')">Copy Body</button>
        </div>
        ${{(e.subjects||[]).map(s => `<div style="font-size:11px;color:var(--text-2);"><strong>Subject:</strong> ${{escHtml(s)}}</div>`).join('')}}
        <div class="launch-post-body" style="margin-top:6px;">${{escHtml(e.body||'')}}</div>
        ${{e.cta ? `<div style="font-size:11px;color:var(--hue);">CTA: ${{escHtml(e.cta)}}</div>` : ''}}
      </div>`).join('');

  }} else if (tab === 'amazon') {{
    const am = a.amazon_copy || {{}};
    const desc   = am.description || '';
    const subs   = am.subtitles   || [];
    const kws    = am.keywords    || [];
    html = `
      <div class="launch-post-card" style="flex-direction:column;gap:8px;">
        <div style="display:flex;align-items:center;"><span style="font-size:10px;font-weight:700;color:var(--hue);">DESCRIPTION</span><button class="launch-copy-btn" style="margin-left:auto;" onclick="launchCopy(this,'${{encodeURIComponent(desc)}}')">Copy</button></div>
        <div class="launch-post-body">${{escHtml(desc) || '<span style="color:var(--text-3);">Not generated.</span>'}}</div>
      </div>
      <div class="launch-post-card" style="flex-direction:column;gap:6px;">
        <span style="font-size:10px;font-weight:700;color:var(--hue);">SUBTITLE OPTIONS</span>
        ${{subs.map((s,i) => `<div style="font-size:12px;display:flex;align-items:center;gap:8px;">${{i+1}}. ${{escHtml(s)}}<button class="launch-copy-btn" onclick="launchCopy(this,'${{encodeURIComponent(s)}}')">Copy</button></div>`).join('')}}
      </div>
      <div class="launch-post-card" style="flex-direction:column;gap:6px;">
        <span style="font-size:10px;font-weight:700;color:var(--hue);">KDP KEYWORDS</span>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">${{kws.map(k => `<span style="background:var(--glass-2);padding:3px 8px;border-radius:12px;font-size:11px;">${{escHtml(k)}}</span>`).join('')}}</div>
        <button class="launch-copy-btn" style="align-self:flex-start;" onclick="launchCopy(this,'${{encodeURIComponent(kws.join(', '))}}')">Copy All</button>
      </div>`;

  }} else if (tab === 'extended') {{
    const rows = [
      ['Goodreads Update',      a.goodreads           || ''],
      ['Podcast Pitch',         a.podcast_pitch        || ''],
      ['Podcast Talking Points',(a.podcast_talking_points||[]).join('\\n• ')],
      ['Newsletter Blurb',      a.newsletter_blurb     || ''],
      ['ARC Review Request',    a.review_request       || ''],
    ];
    html = rows.map(([label, text]) => `
      <div class="launch-post-card" style="flex-direction:column;gap:6px;">
        <div style="display:flex;align-items:center;"><span style="font-size:10px;font-weight:700;color:var(--hue);">${{escHtml(label)}}</span><button class="launch-copy-btn" style="margin-left:auto;" onclick="launchCopy(this,'${{encodeURIComponent(text)}}')">Copy</button></div>
        <div class="launch-post-body">${{escHtml(text) || '<span style="color:var(--text-3);">Not generated.</span>'}}</div>
      </div>`).join('');
  }}
  contentEl.innerHTML = html;
}}

function launchCopy(btn, encodedText) {{
  const text = decodeURIComponent(encodedText);
  navigator.clipboard.writeText(text).then(() => {{
    const orig = btn.textContent;
    btn.textContent = '✓';
    btn.style.background = 'var(--green, #4ade80)';
    btn.style.color = '#000';
    setTimeout(() => {{ btn.textContent = orig; btn.style.background = ''; btn.style.color = ''; }}, 1500);
  }}).catch(() => showToast('Copy failed', 'error'));
}}

/* ═══════════════════════════════════════════════════════════════
   ADAPTIVE LAYOUT ENGINE
═══════════════════════════════════════════════════════════════ */

// ---------------------------------------------------------------------------
// Card Registry — one entry per card with three render templates
// ---------------------------------------------------------------------------
const CARD_REGISTRY = {{

  briefing: {{
    id: 'briefing', title: 'Morning Brief', icon: '📋',
    load: () => loadBriefing(),
    heroRender: () => `
      <div class="card layout-card" id="lc-briefing" data-card="briefing"
           style="min-height:200px;" onclick="cardInteract('briefing','click')">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-title">Morning Brief</span>
            <span class="mono" style="font-size:10px;color:var(--text-3);" id="brief-date">—</span>
          </div>
          <div id="brief-text" style="font-size:13px;color:var(--text-2);line-height:1.65;max-height:320px;overflow:auto;">
            <div class="skel" style="height:10px;width:100%;margin-bottom:6px;"></div>
            <div class="skel" style="height:10px;width:88%;margin-bottom:6px;"></div>
            <div class="skel" style="height:10px;width:72%;"></div>
          </div>
        </div>
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-briefing" data-card="briefing"
           onclick="cardInteract('briefing','click')">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Brief</span>
            <span class="mono" style="font-size:10px;color:var(--text-3);" id="brief-date">—</span>
          </div>
          <div id="brief-text" style="font-size:12px;color:var(--text-2);line-height:1.5;max-height:160px;overflow:hidden;"></div>
        </div>
      </div>`,
    ambientRender: () => `<div class="ambient-tile" onclick="cardInteract('briefing','click')" data-card="briefing">📋 Brief</div>`,
  }},

  calendar: {{
    id: 'calendar', title: 'Calendar', icon: '📅',
    load: () => loadHomeDashboard(),
    heroRender: () => `
      <div class="card layout-card" id="lc-calendar" data-card="calendar"
           style="min-height:200px;cursor:pointer;"
           onclick="cardInteract('calendar','navigate');switchView('calendar')">
        <div class="card-hdr"><span class="card-icon">📅</span><span class="card-title">CALENDAR</span><span class="card-badge" id="calEventCount">—</span></div>
        <div class="card-body" style="padding:14px 18px;">
          <div class="card-row"><span class="lbl">TODAY</span><span class="val mono" id="overviewTodayEvents">—</span></div>
          <div id="overviewNextEvent" class="next-event-preview" style="margin-top:10px;font-size:13px;color:var(--text-2);">—</div>
          <div class="card-cta" style="margin-top:14px;">View full agenda →</div>
        </div>
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-calendar" data-card="calendar"
           style="cursor:pointer;"
           onclick="cardInteract('calendar','navigate');switchView('calendar')">
        <div class="card-hdr"><span class="card-icon">📅</span><span class="card-title">CALENDAR</span><span class="card-badge" id="calEventCount">—</span></div>
        <div class="card-body">
          <div class="card-row"><span class="lbl">TODAY</span><span class="val mono" id="overviewTodayEvents">—</span></div>
          <div id="overviewNextEvent" class="next-event-preview">—</div>
          <div class="card-cta">View agenda →</div>
        </div>
      </div>`,
    ambientRender: () => `
      <div class="ambient-tile" onclick="cardInteract('calendar','navigate');switchView('calendar')" data-card="calendar">
        📅 Calendar <span class="ambient-badge" id="calEventCount">—</span>
      </div>`,
  }},

  approvals: {{
    id: 'approvals', title: 'Needs You', icon: '⚡',
    load: () => loadApprovals(),
    heroRender: () => `
      <div class="card card-needs-you layout-card" id="lc-approvals" data-card="approvals"
           style="min-height:200px;" onclick="cardInteract('approvals','click')">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Needs You</span><span class="dot dot-gold"></span></div>
          <div id="approvals-list">
            <div class="list-row"><div style="flex:1"><div class="skel" style="height:12px;width:70%;margin-bottom:6px;"></div><div class="skel" style="height:10px;width:40%;"></div></div></div>
          </div>
        </div>
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-approvals" data-card="approvals"
           onclick="cardInteract('approvals','click')">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Needs You</span><span class="dot dot-gold"></span></div>
          <div id="approvals-list"><div class="list-row"><div class="skel" style="height:10px;width:70%;"></div></div></div>
        </div>
      </div>`,
    ambientRender: () => `<div class="ambient-tile" onclick="cardInteract('approvals','click')" data-card="approvals">⚡ Approvals <span class="ambient-badge" id="stat-approvals-amb">—</span></div>`,
  }},

  health: {{
    id: 'health', title: 'Health', icon: '♥',
    load: () => loadOverviewHealth(),
    heroRender: () => `
      <div class="card layout-card" id="lc-health" data-card="health"
           style="min-height:200px;cursor:pointer;"
           onclick="cardInteract('health','navigate');switchView('health')">
        <div class="card-hdr"><span class="card-icon">♥</span><span class="card-title">HEALTH</span><span class="card-badge" id="overview-health-badge">—</span></div>
        <div class="card-inner" id="overview-health-content" style="font-size:12px;color:var(--text-3);padding:14px 18px;">Loading…</div>
        <div style="padding:0 18px 10px 18px;">
          <div style="margin-top:8px;">
            <div style="font-size:10px; text-transform:uppercase; opacity:0.5; margin-bottom:4px;">Air Quality</div>
            <div id="env-air-quality" style="display:flex; align-items:center;">--</div>
          </div>
          <div style="margin-top:8px;">
            <div style="font-size:10px; text-transform:uppercase; opacity:0.5; margin-bottom:4px;">Pollen</div>
            <div id="env-pollen">--</div>
          </div>
        </div>
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-health" data-card="health"
           style="cursor:pointer;"
           onclick="cardInteract('health','navigate');switchView('health')">
        <div class="card-hdr"><span class="card-icon">♥</span><span class="card-title">HEALTH</span><span class="card-badge" id="overview-health-badge">—</span></div>
        <div class="card-inner" id="overview-health-content" style="font-size:11px;color:var(--text-3);">Loading…</div>
        <div style="padding:4px 14px 8px 14px;">
          <div style="margin-top:6px;">
            <div style="font-size:10px; text-transform:uppercase; opacity:0.5; margin-bottom:3px;">Air Quality</div>
            <div id="env-air-quality" style="display:flex; align-items:center;">--</div>
          </div>
          <div style="margin-top:6px;">
            <div style="font-size:10px; text-transform:uppercase; opacity:0.5; margin-bottom:3px;">Pollen</div>
            <div id="env-pollen">--</div>
          </div>
        </div>
      </div>`,
    ambientRender: () => `
      <div class="ambient-tile" onclick="cardInteract('health','navigate');switchView('health')" data-card="health">
        ♥ Health <span class="ambient-badge" id="overview-health-badge">—</span>
      </div>`,
  }},

  tasks: {{
    id: 'tasks', title: 'Tasks', icon: '✓',
    load: () => loadJarvisTasks(),
    heroRender: () => `
      <div class="card layout-card" id="lc-tasks" data-card="tasks"
           style="min-height:200px;grid-column:1/-1;" onclick="cardInteract('tasks','click')">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Tasks</span><span class="pill pill-hue" id="tasks-count">—</span></div>
          <div class="tasks-add-bar">
            <input id="task-title-input" type="text" placeholder="New task…"
                   onkeydown="if(event.key==='Enter')addJarvisTask()">
            <select id="task-domain-select">
              <option value="personal">Personal</option><option value="work">Work</option>
              <option value="family">Family</option><option value="home">Home</option>
              <option value="health">Health</option><option value="faith">Faith</option>
              <option value="finance">Finance</option><option value="workshop">Workshop</option>
            </select>
            <select id="task-priority-select">
              <option value="normal">Normal</option><option value="high">High</option><option value="low">Low</option>
            </select>
            <input id="task-due-input" type="date">
            <button onclick="addJarvisTask()" style="background:var(--hue);color:#fff;border:none;border-radius:6px;padding:5px 12px;font-size:12px;cursor:pointer;white-space:nowrap;">+ Add</button>
          </div>
          <div class="tasks-filter-bar" id="tasks-filter-bar">
            <span class="tasks-filter-pill active" data-filter="all" onclick="setTaskFilter('all')">All</span>
            <span class="tasks-filter-pill" data-filter="today" onclick="setTaskFilter('today')">Today</span>
            <span class="tasks-filter-pill" data-filter="week" onclick="setTaskFilter('week')">This Week</span>
            <span class="tasks-filter-pill" data-filter="domain" onclick="setTaskFilter('domain')">By Domain</span>
          </div>
          <div id="overview-tasks">
            <div class="list-row"><div class="skel" style="height:10px;width:75%;margin-bottom:5px;"></div></div>
          </div>
        </div>
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-tasks" data-card="tasks"
           onclick="cardInteract('tasks','click')">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Tasks</span><span class="pill pill-hue" id="tasks-count">—</span></div>
          <div id="overview-tasks"><div class="skel" style="height:10px;width:75%;"></div></div>
        </div>
      </div>`,
    ambientRender: () => `<div class="ambient-tile" onclick="cardInteract('tasks','click')" data-card="tasks">✓ Tasks <span class="ambient-badge" id="tasks-count">—</span></div>`,
  }},

  reminders: {{
    id: 'reminders', title: 'Reminders', icon: '🔔',
    load: () => loadOverviewReminders(),
    heroRender: () => `
      <div class="card layout-card" id="lc-reminders" data-card="reminders"
           style="min-height:200px;" onclick="cardInteract('reminders','click')">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Reminders</span><span class="pill pill-hue" id="reminders-count">—</span></div>
          <div id="overview-reminders"><div class="list-row"><div class="skel" style="height:10px;width:70%;"></div></div></div>
          <div style="margin-top:10px;display:flex;gap:6px;">
            <input id="reminder-input" type="text" placeholder="Add reminder…"
                   style="flex:1;background:rgba(255,255,255,.4);border:1px solid rgba(255,255,255,.5);border-radius:6px;padding:5px 8px;font-size:12px;color:var(--text-1);outline:none;"
                   onkeydown="if(event.key==='Enter')addReminder()">
            <button onclick="addReminder()" style="background:var(--hue);color:#fff;border:none;border-radius:6px;padding:5px 10px;font-size:12px;cursor:pointer;">+</button>
          </div>
        </div>
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-reminders" data-card="reminders"
           onclick="cardInteract('reminders','click')">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Reminders</span><span class="pill pill-hue" id="reminders-count">—</span></div>
          <div id="overview-reminders"><div class="list-row"><div class="skel" style="height:10px;width:70%;"></div></div></div>
        </div>
      </div>`,
    ambientRender: () => `<div class="ambient-tile" onclick="cardInteract('reminders','click')" data-card="reminders">🔔 Reminders <span class="ambient-badge" id="reminders-count">—</span></div>`,
  }},

  email: {{
    id: 'email', title: 'Email', icon: '✉',
    load: () => loadHomeDashboard(),
    heroRender: () => `
      <div class="card layout-card" id="lc-email" data-card="email"
           style="min-height:200px;cursor:pointer;"
           onclick="cardInteract('email','navigate');switchView('email')">
        <div class="card-hdr"><span class="card-icon">✉</span><span class="card-title">EMAIL</span><span class="card-badge" id="emailUnreadBadge">—</span></div>
        <div class="card-body" style="padding:14px 18px;">
          <div class="card-row"><span class="lbl">GMAIL</span><span class="val mono" id="overviewGmailUnread">—</span></div>
          <div class="card-row"><span class="lbl">OUTLOOK</span><span class="val mono" id="overviewOutlookUnread">—</span></div>
          <div class="card-cta" style="margin-top:14px;">Open inbox →</div>
        </div>
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-email" data-card="email"
           style="cursor:pointer;"
           onclick="cardInteract('email','navigate');switchView('email')">
        <div class="card-hdr"><span class="card-icon">✉</span><span class="card-title">EMAIL</span><span class="card-badge" id="emailUnreadBadge">—</span></div>
        <div class="card-body">
          <div class="card-row"><span class="lbl">GMAIL</span><span class="val mono" id="overviewGmailUnread">—</span></div>
          <div class="card-row"><span class="lbl">OUTLOOK</span><span class="val mono" id="overviewOutlookUnread">—</span></div>
          <div class="card-cta">Open inbox →</div>
        </div>
      </div>`,
    ambientRender: () => `<div class="ambient-tile" onclick="cardInteract('email','navigate');switchView('email')" data-card="email">✉ Email <span class="ambient-badge" id="emailUnreadBadge">—</span></div>`,
  }},

  agents: {{
    id: 'agents', title: 'Agents', icon: '🤖',
    load: () => loadOverviewAgents(),
    heroRender: () => `
      <div class="card layout-card" id="lc-agents" data-card="agents"
           style="min-height:200px;" onclick="cardInteract('agents','click')">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Active Agents</span><span class="pill pill-hue" id="active-agents-count">—</span></div>
          <div id="active-agents-list">
            <div class="list-row"><div class="skel" style="height:10px;width:60%;"></div></div>
          </div>
        </div>
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-agents" data-card="agents"
           onclick="cardInteract('agents','click')">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Active Agents</span><span class="pill pill-hue" id="active-agents-count">—</span></div>
          <div id="active-agents-list"><div class="list-row"><div class="skel" style="height:10px;width:60%;"></div></div></div>
        </div>
      </div>`,
    ambientRender: () => `<div class="ambient-tile" onclick="cardInteract('agents','click')" data-card="agents">🤖 Agents <span class="ambient-badge" id="active-agents-count">—</span></div>`,
  }},

  catalyst: {{
    id: 'catalyst', title: 'Catalyst', icon: '⚗️',
    load: () => loadOverviewCatalyst(),
    heroRender: () => `
      <div class="card layout-card" id="lc-catalyst" data-card="catalyst"
           style="min-height:200px;" onclick="cardInteract('catalyst','click')">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Catalyst</span><span class="pill pill-hue" id="catalyst-flows">—</span></div>
          <div id="overview-catalyst"><div class="list-row"><div class="skel" style="height:10px;width:75%;"></div></div></div>
        </div>
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-catalyst" data-card="catalyst"
           onclick="cardInteract('catalyst','click')">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Catalyst</span><span class="pill pill-hue" id="catalyst-flows">—</span></div>
          <div id="overview-catalyst"><div class="skel" style="height:10px;width:75%;"></div></div>
        </div>
      </div>`,
    ambientRender: () => `<div class="ambient-tile" onclick="cardInteract('catalyst','click')" data-card="catalyst">⚗️ Catalyst <span class="ambient-badge" id="catalyst-flows">—</span></div>`,
  }},

  chronicle: {{
    id: 'chronicle', title: 'Chronicle', icon: '📖',
    load: () => loadOverviewChronicle(),
    heroRender: () => `
      <div class="card layout-card" id="lc-chronicle" data-card="chronicle"
           style="min-height:200px;" onclick="cardInteract('chronicle','expand')">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Chronicle</span><span class="pill pill-navy" id="chronicle-count">—</span></div>
          <div id="overview-chronicle"><div class="skel" style="height:10px;width:80%;margin-bottom:6px;"></div></div>
        </div>
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-chronicle" data-card="chronicle"
           onclick="cardInteract('chronicle','expand')">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Chronicle</span><span class="pill pill-navy" id="chronicle-count">—</span></div>
          <div id="overview-chronicle"><div class="skel" style="height:10px;width:80%;"></div></div>
        </div>
      </div>`,
    ambientRender: () => `<div class="ambient-tile" onclick="cardInteract('chronicle','expand')" data-card="chronicle">📖 Chronicle <span class="ambient-badge" id="chronicle-count">—</span></div>`,
  }},

  publishing: {{
    id: 'publishing', title: 'Publishing', icon: '📚',
    load: () => loadOverviewPublishing(),
    heroRender: () => `
      <div class="card layout-card" id="lc-publishing" data-card="publishing"
           style="min-height:200px;" onclick="cardInteract('publishing','click')">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Publishing</span><span class="pill pill-gold">Stan Lee</span></div>
          <div id="overview-publishing"><div class="skel" style="height:10px;width:65%;margin-bottom:6px;"></div></div>
        </div>
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-publishing" data-card="publishing"
           onclick="cardInteract('publishing','click')">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Publishing</span><span class="pill pill-gold">Stan Lee</span></div>
          <div id="overview-publishing"><div class="skel" style="height:10px;width:65%;"></div></div>
        </div>
      </div>`,
    ambientRender: () => `<div class="ambient-tile" onclick="cardInteract('publishing','click')" data-card="publishing">📚 Publishing</div>`,
  }},

  forge: {{
    id: 'forge', title: '3D Forge', icon: '🔧',
    load: () => {{}},  // no live loader — static until print job active
    heroRender: () => `
      <div class="card layout-card" id="lc-forge" data-card="forge"
           style="min-height:200px;cursor:pointer;"
           onclick="cardInteract('forge','navigate');switchView('forge')">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">3D Forge</span><span class="pill pill-navy">Print Queue</span></div>
          <div id="overview-forge">
            <div class="list-row"><span class="dot dot-standby"></span><div><div class="list-row-name">No active print</div><div class="list-row-sub">Queue empty</div></div></div>
          </div>
        </div>
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-forge" data-card="forge"
           style="cursor:pointer;" onclick="cardInteract('forge','navigate');switchView('forge')">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">3D Forge</span><span class="pill pill-navy">Print Queue</span></div>
          <div id="overview-forge"><div class="list-row"><span class="dot dot-standby"></span><div class="list-row-name">No active print</div></div></div>
        </div>
      </div>`,
    ambientRender: () => `<div class="ambient-tile" onclick="cardInteract('forge','navigate');switchView('forge')" data-card="forge">🔧 Forge</div>`,
  }},

  vision: {{
    id: 'vision', title: 'Vision System', icon: '👁',
    load: () => {{}},
    heroRender: () => `
      <div class="card layout-card" id="lc-vision" data-card="vision" style="min-height:200px;">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Vision System</span><span class="pill pill-success">LIVE</span></div>
          <div id="overview-vision">
            <div class="list-row"><span class="dot dot-success"></span><div><div class="list-row-name">4 Cameras</div><div class="list-row-sub">No events in last 5m</div></div><div class="list-row-meta">SECURE</div></div>
          </div>
        </div>
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-vision" data-card="vision">
        <div class="card-inner">
          <div class="card-header"><span class="card-title">Vision System</span><span class="pill pill-success">LIVE</span></div>
          <div id="overview-vision"><div class="list-row"><span class="dot dot-success"></span><div class="list-row-name">4 Cameras — SECURE</div></div></div>
        </div>
      </div>`,
    ambientRender: () => `<div class="ambient-tile" data-card="vision">👁 Vision</div>`,
  }},

  idea_inbox: {{
    id: 'idea_inbox', title: 'Idea Inbox', icon: '💡',
    load: () => loadIdeaInbox(),
    heroRender: () => `
      <div class="card layout-card" id="lc-idea-inbox" data-card="idea_inbox"
           style="min-height:200px;grid-column:1/-1;" onclick="cardInteract('idea_inbox','click')">
        <div class="card-inner">
          <div class="card-header">
            <span class="card-icon">💡</span>
            <span class="card-title">IDEA INBOX</span>
            <span class="card-badge" id="idea-inbox-badge">—</span>
            <button class="btn-ghost" style="margin-left:auto;font-size:10px;" onclick="event.stopPropagation();switchView('huddle')">View All →</button>
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
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-idea-inbox" data-card="idea_inbox"
           onclick="cardInteract('idea_inbox','click')">
        <div class="card-inner">
          <div class="card-header"><span class="card-icon">💡</span><span class="card-title">IDEAS</span><span class="card-badge" id="idea-inbox-badge">—</span></div>
          <div id="idea-inbox-recent" style="display:flex;flex-wrap:wrap;gap:5px;margin-top:6px;"></div>
        </div>
      </div>`,
    ambientRender: () => `<div class="ambient-tile" onclick="cardInteract('idea_inbox','click')" data-card="idea_inbox">💡 Ideas <span class="ambient-badge" id="idea-inbox-badge">—</span></div>`,
  }},

  sam: {{
    id: 'sam', title: 'Sam Wilson', icon: '🦅',
    load: () => loadSamOverviewCard(),
    heroRender: () => `
      <div class="card layout-card" id="lc-sam" data-card="sam"
           style="min-height:200px;" onclick="cardInteract('sam','click')">
        <div class="card-hdr">
          <span class="card-icon">🦅</span>
          <span class="card-title">SAM WILSON</span>
          <span class="card-badge" id="sam-ov-streak-badge" style="display:none;"></span>
        </div>
        <div class="card-body" id="sam-ov-content" style="padding:14px 18px;">
          <div class="skel" style="height:10px;width:80%;margin-bottom:8px;"></div>
          <div class="skel" style="height:10px;width:60%;margin-bottom:8px;"></div>
          <div class="skel" style="height:10px;width:72%;"></div>
        </div>
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-sam" data-card="sam"
           onclick="cardInteract('sam','click')">
        <div class="card-hdr">
          <span class="card-icon">🦅</span>
          <span class="card-title">SAM</span>
          <span class="card-badge" id="sam-ov-streak-badge"></span>
        </div>
        <div class="card-body" id="sam-ov-content" style="padding:10px 14px;"></div>
      </div>`,
    ambientRender: () => `
      <div class="ambient-tile" onclick="cardInteract('sam','navigate');switchView('health')" data-card="sam">
        🦅 Sam <span class="ambient-badge" id="sam-ov-streak-badge">—</span>
      </div>`,
  }},

  dining: {{
    id: 'dining', title: 'Dining', icon: '🍽️',
    load: () => loadDiningCard(),
    heroRender: () => `
      <div class="card layout-card" id="lc-dining" data-card="dining"
           style="min-height:200px;" onclick="cardInteract('dining','click')">
        <div class="card-hdr">
          <span class="card-icon">🍽️</span>
          <span class="card-title">DINING</span>
          <button class="btn-ghost" style="margin-left:auto;font-size:10px;"
            onclick="event.stopPropagation();switchView('dining')">Explore →</button>
        </div>
        <div class="card-body" id="dining-ov-content" style="padding:14px 18px;">
          <div class="skel" style="height:10px;width:70%;margin-bottom:8px;"></div>
          <div class="skel" style="height:10px;width:55%;margin-bottom:8px;"></div>
          <div class="skel" style="height:10px;width:65%;"></div>
        </div>
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-dining" data-card="dining"
           onclick="cardInteract('dining','click')">
        <div class="card-hdr">
          <span class="card-icon">🍽️</span>
          <span class="card-title">DINING</span>
        </div>
        <div class="card-body" id="dining-ov-content" style="padding:10px 14px;"></div>
      </div>`,
    ambientRender: () => `
      <div class="ambient-tile" onclick="cardInteract('dining','click');switchView('dining')" data-card="dining">
        🍽️ Dining
      </div>`,
  }},

  finance: {{
    id: 'finance', title: 'Finance', icon: '💰',
    load: () => loadFiskCard(),
    heroRender: () => `
      <div class="card layout-card" id="lc-finance" data-card="finance"
           style="min-height:200px;" onclick="cardInteract('finance','click')">
        <div class="card-hdr">
          <span class="card-icon">💰</span>
          <span class="card-title">FINANCE</span>
          <span class="card-badge" id="fisk-health-badge">—</span>
        </div>
        <div class="card-body" id="fisk-ov-content" style="padding:14px 18px;">
          <div class="skel" style="height:10px;width:60%;margin-bottom:8px;"></div>
          <div class="skel" style="height:10px;width:80%;margin-bottom:8px;"></div>
          <div class="skel" style="height:10px;width:50%;"></div>
        </div>
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-finance" data-card="finance"
           onclick="cardInteract('finance','click')">
        <div class="card-hdr">
          <span class="card-icon">💰</span>
          <span class="card-title">FINANCE</span>
          <span class="card-badge" id="fisk-health-badge">—</span>
        </div>
        <div class="card-body" id="fisk-ov-content" style="padding:10px 14px;"></div>
      </div>`,
    ambientRender: () => `
      <div class="ambient-tile" onclick="cardInteract('finance','click')" data-card="finance">
        💰 Finance <span class="ambient-badge" id="fisk-health-badge">—</span>
      </div>`,
  }},

  maps_usage: {{
    id: 'maps_usage',
    title: 'Google APIs',
    icon: '🗺',
    load: () => loadOverviewMapsUsage(),
    heroRender: () => `
      <div class="card layout-card" id="lc-maps-usage" data-card="maps_usage"
           style="min-height:200px;" onclick="cardInteract('maps_usage','click')">
        <div class="card-hdr">
          <span class="card-icon">🗺</span>
          <span class="card-title">GOOGLE APIs</span>
          <span class="card-badge" id="maps-usage-badge">—</span>
        </div>
        <div class="card-body" id="maps-usage-content" style="padding:14px 18px;">
          <div class="skel" style="height:10px;width:70%;margin-bottom:8px;"></div>
          <div class="skel" style="height:10px;width:50%;"></div>
        </div>
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-maps-usage" data-card="maps_usage"
           onclick="cardInteract('maps_usage','click')">
        <div class="card-hdr">
          <span class="card-icon">🗺</span>
          <span class="card-title">GOOGLE APIs</span>
          <span class="card-badge" id="maps-usage-badge">—</span>
        </div>
        <div class="card-body" id="maps-usage-content" style="padding:10px 14px;"></div>
      </div>`,
    ambientRender: () => `
      <div class="ambient-tile" onclick="cardInteract('maps_usage','click')" data-card="maps_usage">
        🗺 Google APIs <span class="ambient-badge" id="maps-usage-badge">—</span>
      </div>`,
  }},

  jarvis_costs: {{
    id: 'jarvis_costs',
    title: 'JARVIS Costs',
    icon: '💸',
    load: () => loadOverviewCosts(),
    heroRender: () => `
      <div class="card layout-card" id="lc-jarvis-costs" data-card="jarvis_costs"
           style="min-height:200px;" onclick="cardInteract('jarvis_costs','click')">
        <div class="card-hdr">
          <span class="card-icon">💸</span>
          <span class="card-title">JARVIS COSTS</span>
          <span class="card-badge" id="jarvis-costs-badge">—</span>
        </div>
        <div class="card-body" id="jarvis-costs-content" style="padding:14px 18px;">
          <div class="skel" style="height:10px;width:70%;margin-bottom:8px;"></div>
          <div class="skel" style="height:10px;width:50%;"></div>
        </div>
      </div>`,
    priorityRender: () => `
      <div class="card card-tactical layout-card" id="lc-jarvis-costs" data-card="jarvis_costs"
           onclick="cardInteract('jarvis_costs','click')">
        <div class="card-hdr">
          <span class="card-icon">💸</span>
          <span class="card-title">JARVIS COSTS</span>
          <span class="card-badge" id="jarvis-costs-badge">—</span>
        </div>
        <div class="card-body" id="jarvis-costs-content" style="padding:10px 14px;"></div>
      </div>`,
    ambientRender: () => `
      <div class="ambient-tile" onclick="cardInteract('jarvis_costs','click')" data-card="jarvis_costs">
        💸 Costs <span class="ambient-badge" id="jarvis-costs-badge">—</span>
      </div>`,
  }},

}};

// ---------------------------------------------------------------------------
// Layout state
// ---------------------------------------------------------------------------
let _layoutState    = null;
let _activeAlert    = null;
let _alertDismissTimer = null;

// ---------------------------------------------------------------------------
// Core functions
// ---------------------------------------------------------------------------

async function loadLayoutState() {{
  try {{
    const res = await fetch('/api/layout/state');
    if (!res.ok) return;
    _layoutState = await res.json();
    applyModeBar(_layoutState);
    applyAlertBanner(_layoutState.alerts || []);
    applyLayout(_layoutState.layout || {{}}, _layoutState.alerts || [], true);
    _fireLayoutLoaders(_layoutState.layout || {{}});
    loadFamilyPresence();   // refresh who's online in the presence bar
  }} catch(e) {{ console.error('loadLayoutState failed', e); }}
}}

/* ── Family presence bar ────────────────────────────────────────── */
async function loadFamilyPresence() {{
  const bar = document.getElementById('overview-family-bar');
  if (!bar) return;
  try {{
    const r = await fetch('/api/connected-devices');
    const data = await r.json();
    const devices = data.devices || [];
    const now = Date.now();
    const THRESHOLD = 10 * 60 * 1000; // 10 minutes = "online"

    const FAMILY = {{
      chris:   {{name:'Chris',   avatar:'👨‍💼'}},
      rebekah: {{name:'Rebekah', avatar:'👩'}},
      caleb:   {{name:'Caleb',   avatar:'👦'}},
      anna:    {{name:'Anna',    avatar:'👧'}},
    }};

    const onlineUsers = new Set();
    devices.forEach(d => {{
      if (!d.owner_user_id || !d.last_seen_at) return;
      const age = now - new Date(d.last_seen_at).getTime();
      if (age < THRESHOLD) onlineUsers.add(d.owner_user_id);
    }});

    if (onlineUsers.size === 0) {{ bar.style.display = 'none'; return; }}

    const chips = [...onlineUsers].map(uid => {{
      const info = FAMILY[uid] || {{name: uid, avatar: '👤'}};
      return `<span style="display:inline-flex;align-items:center;gap:5px;padding:3px 10px;background:rgba(0,212,170,0.1);border:1px solid rgba(0,212,170,0.2);border-radius:20px;font-size:11px;color:var(--text-1);">
        <span style="width:6px;height:6px;border-radius:50%;background:#00d4aa;flex-shrink:0;"></span>
        ${{info.avatar}} ${{escHtml(info.name)}}
      </span>`;
    }}).join('');

    bar.innerHTML = `<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
      <span style="font-size:10px;color:var(--text-3);font-family:var(--font-mono);text-transform:uppercase;letter-spacing:.05em;white-space:nowrap;">Online Now</span>
      ${{chips}}
    </div>`;
    bar.style.display = 'block';
  }} catch(e) {{ bar.style.display = 'none'; }}
}}

function applyModeBar(state) {{
  const mode = state.mode || 'morning_brief';
  document.querySelectorAll('.mode-pill').forEach(pill => {{
    const isActive = pill.dataset.mode === mode;
    pill.classList.toggle('active', isActive);
    pill.classList.toggle('manual-override', isActive && state.manual_override);
  }});
  const chip = document.getElementById('mode-auto-chip');
  if (chip) {{
    chip.textContent = state.manual_override ? 'MANUAL' : 'AUTO';
    chip.classList.toggle('override', !!state.manual_override);
    if (state.manual_override && state.override_expires_at) {{
      const exp = new Date(state.override_expires_at);
      chip.title = 'Auto-resumes at ' + exp.toLocaleTimeString([], {{hour:'2-digit',minute:'2-digit'}});
    }} else {{
      chip.title = '';
    }}
  }}
  const sub = document.getElementById('overview-subtitle');
  if (sub) {{
    const modeInfo = (state.modes || {{}})[mode] || {{}};
    const icon  = modeInfo.icon  || '';
    const label = modeInfo.label || mode;
    sub.textContent = icon + ' ' + label + (state.manual_override ? ' · Manual Override' : ' · Auto Mode');
  }}
  // Refresh overview greeting in case profile just loaded
  applyUserProfile(_userProfile);

  // Show/hide user identity bar for non-Chris users
  const _uid = getCurrentUserId();
  const _userBar = document.getElementById('overview-user-bar');
  if (_userBar) {{
    if (_uid !== 'chris') {{
      const _nameMap  = {{chris:'Chris', rebekah:'Rebekah', caleb:'Caleb', anna:'Anna'}};
      const _emojiMap = {{chris:'👨‍💼', rebekah:'👩', caleb:'👦', anna:'👧'}};
      const _roleMap  = {{caleb:'Family member', anna:'Family member', rebekah:'Family member'}};
      document.getElementById('overview-user-avatar').textContent = _emojiMap[_uid] || '👤';
      document.getElementById('overview-user-name').textContent   = _nameMap[_uid]  || _uid;
      document.getElementById('overview-user-role').textContent   = _roleMap[_uid]  || '';
      _userBar.style.display = 'flex';
    }} else {{
      _userBar.style.display = 'none';
    }}
  }}
}}

function applyLayout(layout, alerts, animate) {{
  const alertedMap = {{}};
  (alerts || []).forEach(a => {{ alertedMap[a.card] = a.level; }});
  const hidden = _getHiddenCards();

  // FLIP Phase 1: snapshot current card positions before re-render
  const oldRects = {{}};
  if (animate) {{
    document.querySelectorAll('[data-card]').forEach(el => {{
      const id = el.dataset.card;
      if (id) oldRects[id] = el.getBoundingClientRect();
    }});
  }}

  function renderZone(containerId, cards, renderFn) {{
    const zone = document.getElementById(containerId);
    if (!zone) return;
    zone.innerHTML = '';
    (cards || []).forEach(cardId => {{
      if (hidden.has(cardId)) return;   // ← per-person dashboard filter
      const reg = CARD_REGISTRY[cardId];
      if (!reg) return;
      const tmp = document.createElement('div');
      tmp.innerHTML = renderFn(reg).trim();
      const el = tmp.firstElementChild;
      if (!el) return;
      if (alertedMap[cardId]) el.classList.add('alert-pulse-' + alertedMap[cardId]);
      zone.appendChild(el);
    }});
  }}

  renderZone('overview-hero-zone',      layout.hero     || [], r => r.heroRender());
  renderZone('overview-priority-strip', layout.priority || [], r => r.priorityRender());
  renderZone('overview-ambient-row',    layout.ambient  || [], r => r.ambientRender());

  if (!animate) return;

  // FLIP Phase 2: invert + play
  document.querySelectorAll('[data-card]').forEach(el => {{
    const id = el.dataset.card;
    const old = oldRects[id];

    if (!old) {{
      // New card — liquid glass entrance: fade + rise
      el.style.opacity = '0';
      el.style.transform = 'translateY(14px) scale(0.96)';
      el.style.transition = 'none';
      requestAnimationFrame(() => {{
        el.style.transition = 'opacity 0.4s ease, transform 0.45s cubic-bezier(0.34,1.56,0.64,1)';
        el.style.opacity = '1';
        el.style.transform = '';
      }});
      return;
    }}

    // Existing card — FLIP to new position
    const newRect = el.getBoundingClientRect();
    const dx = old.left - newRect.left;
    const dy = old.top  - newRect.top;
    const sx = old.width  / Math.max(newRect.width,  1);
    const sy = old.height / Math.max(newRect.height, 1);

    // Skip if barely moved
    if (Math.abs(dx) < 2 && Math.abs(dy) < 2 && Math.abs(sx - 1) < 0.02) return;

    // Invert: snap visually to old position/size
    el.style.transition = 'none';
    el.style.transform  = `translate(${{dx}}px,${{dy}}px) scale(${{sx}},${{sy}})`;
    el.style.transformOrigin = 'top left';
    el.style.opacity = '0.7';

    // Play: spring to natural position
    requestAnimationFrame(() => requestAnimationFrame(() => {{
      el.style.transition = [
        'transform 0.55s cubic-bezier(0.34,1.56,0.64,1)',
        'opacity 0.3s ease',
      ].join(',');
      el.style.transform  = '';
      el.style.transformOrigin = '';
      el.style.opacity = '';
    }}));
  }});
}}

function _fireLayoutLoaders(layout) {{
  const allCards = [
    ...(layout.hero     || []),
    ...(layout.priority || []),
    ...(layout.ambient  || []),
  ];
  // Deduplicate
  const seen = new Set();
  allCards.forEach(cardId => {{
    if (seen.has(cardId)) return;
    seen.add(cardId);
    const reg = CARD_REGISTRY[cardId];
    if (reg && typeof reg.load === 'function') {{
      try {{ reg.load(); }} catch(e) {{ console.warn('Layout loader failed for', cardId, e); }}
    }}
  }});
  // Always load stats (needed for stat strip)
  if (typeof loadApprovals === 'function') loadApprovals();
}}

function cardInteract(cardId, action) {{
  const mode = _layoutState ? _layoutState.mode : 'morning_brief';
  fetch('/api/layout/interact', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{card_id: cardId, action, mode}}),
  }}).catch(() => {{}});
  if (_activeAlert && _activeAlert.card === cardId) dismissAlertBanner();
}}

async function setLayoutMode(mode) {{
  try {{
    await fetch('/api/layout/mode', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{mode, manual: true}}),
    }});
    await loadLayoutState();
  }} catch(e) {{ console.error('setLayoutMode failed', e); }}
}}

async function checkAutoMode() {{
  if (!_layoutState || _layoutState.manual_override) return;
  try {{
    const res = await fetch('/api/layout/state');
    if (!res.ok) return;
    const newState = await res.json();
    if (newState.mode !== (_layoutState || {{}}).mode) {{
      _layoutState = newState;
      applyModeBar(newState);
      applyAlertBanner(newState.alerts || []);
      applyLayout(newState.layout || {{}}, newState.alerts || [], true);
      _fireLayoutLoaders(newState.layout || {{}});
      const modeInfo = (newState.modes || {{}})[newState.mode] || {{}};
      showToast((modeInfo.icon || '') + ' Switched to ' + (modeInfo.label || newState.mode), 'info');
    }}
  }} catch(e) {{}}
}}

function applyAlertBanner(alerts) {{
  const banner = document.getElementById('overview-alert-banner');
  if (!banner) return;
  if (!alerts || alerts.length === 0) {{
    _dismissAlertBannerEl(banner);
    return;
  }}
  const priority = {{red: 3, amber: 2, blue: 1}};
  const top = [...alerts].sort((a,b) => (priority[b.level]||0) - (priority[a.level]||0))[0];
  _activeAlert = top;
  banner.style.display = 'flex';
  requestAnimationFrame(() => {{
    banner.className = 'overview-alert-banner level-' + top.level + ' visible';
  }});
  const iconEl = document.getElementById('alert-banner-icon');
  const msgEl  = document.getElementById('alert-banner-msg');
  const btnEl  = document.getElementById('alert-banner-action-btn');
  if (iconEl) iconEl.textContent = top.level === 'red' ? '🚨' : top.level === 'blue' ? '🔔' : '⚠️';
  if (msgEl)  msgEl.textContent  = top.message || '';
  if (btnEl)  btnEl.dataset.card = top.card || '';
  if (_alertDismissTimer) clearTimeout(_alertDismissTimer);
  _alertDismissTimer = setTimeout(dismissAlertBanner, 30000);
}}

function dismissAlertBanner() {{
  _activeAlert = null;
  if (_alertDismissTimer) {{ clearTimeout(_alertDismissTimer); _alertDismissTimer = null; }}
  const banner = document.getElementById('overview-alert-banner');
  if (banner) _dismissAlertBannerEl(banner);
}}

function _dismissAlertBannerEl(banner) {{
  banner.classList.remove('visible');
  setTimeout(() => {{ if (banner) banner.style.display = 'none'; }}, 320);
}}

function alertBannerNavigate() {{
  const btn  = document.getElementById('alert-banner-action-btn');
  const card = btn ? btn.dataset.card : '';
  if (card) cardInteract(card, 'navigate');
  const viewMap = {{calendar:'calendar', health:'health', email:'email', agents:'agents'}};
  const target = viewMap[card];
  if (target) switchView(target);
  dismissAlertBanner();
}}

function updateModeBarClock() {{
  const el = document.getElementById('mode-clock');
  if (el) el.textContent = new Date().toLocaleTimeString([], {{hour:'2-digit', minute:'2-digit'}});
}}

/* ═══════════════════════════════════════════════════════════════
   NEWS
═══════════════════════════════════════════════════════════════ */

const _SOURCE_META = {{
  'BBC':         {{ color: '#BB1919', bg: '#fef2f2', icon: 'B' }},
  'NYT':         {{ color: '#111111', bg: '#f4f4f4', icon: 'N' }},
  'AP':          {{ color: '#CC0000', bg: '#fff0f0', icon: 'A' }},
  'ALJAZEERA':   {{ color: '#009FE3', bg: '#eff9ff', icon: 'A' }},
  'CNBC':        {{ color: '#003087', bg: '#eff3ff', icon: 'C' }},
  'MARKETWATCH': {{ color: '#0072CE', bg: '#eff8ff', icon: 'M' }},
  'BLOOMBERG':   {{ color: '#444444', bg: '#f5f5f5', icon: 'B' }},
}};

function _sourceMeta(name) {{
  const key = (name || '').toUpperCase().replace(/[^A-Z]/g,'').slice(0,10);
  for (const [k, v] of Object.entries(_SOURCE_META)) {{
    if (key.startsWith(k.slice(0,4))) return v;
  }}
  return {{ color: '#6B7280', bg: '#f3f4f6', icon: (name||'?')[0].toUpperCase() }};
}}

let _newsCache = null;
let _newsFilter = 'all';

async function loadNews(force) {{
  try {{
    if (!force && _newsCache) {{ renderNewsView(_newsCache); return; }}
    const grid = document.getElementById('news-grid');
    if (grid && force) {{
      grid.innerHTML = '<div style="color:var(--text-3);font-size:13px;padding:40px 0;text-align:center;grid-column:1/-1;">⏳ Fetching latest headlines + images…</div>';
    }}
    const res = await fetch(force ? '/api/news?force=1' : '/api/news');
    if (!res.ok) {{ console.warn('loadNews', res.status); return; }}
    const data = await res.json();
    _newsCache = data;
    renderNewsView(data);
  }} catch(e) {{ console.error('loadNews failed', e); }}
}}

function filterNews(cat) {{
  _newsFilter = cat;
  document.querySelectorAll('.news-filter-btn').forEach(b => b.classList.remove('active'));
  const btn = document.getElementById('news-filter-' + cat);
  if (btn) btn.classList.add('active');
  if (_newsCache) renderNewsView(_newsCache);
}}

function renderNewsView(data) {{
  const grid = document.getElementById('news-grid');
  const fetchedEl = document.getElementById('news-last-fetched');
  if (!grid) return;

  // Update fetched timestamp
  if (fetchedEl && data.fetched_at) {{
    const ago = Math.round((Date.now() - new Date(data.fetched_at + 'Z').getTime()) / 60000);
    fetchedEl.textContent = ago <= 1 ? 'Just now' : ago + ' min ago';
  }}

  // Merge and filter articles
  let world = (data.world || []).map(a => ({{...a, _cat:'world'}}));
  let finance = (data.finance || []).map(a => ({{...a, _cat:'finance'}}));
  let articles = _newsFilter === 'world' ? world
               : _newsFilter === 'finance' ? finance
               : [...world, ...finance];

  if (articles.length === 0) {{
    grid.innerHTML = '<div style="color:var(--text-3);font-size:13px;padding:40px 0;text-align:center;grid-column:1/-1;">' +
      (data.error ? 'Could not load news: ' + escHtml(data.error) : 'No headlines available.') + '</div>';
    return;
  }}

  const esc = s => escHtml(s || '');

  function makeSourceBadge(source, cat) {{
    const m = _sourceMeta(source);
    const catIcon = cat === 'finance' ? '📈 ' : '🌍 ';
    return `<span class="news-source-badge" style="background:${{m.bg}};color:${{m.color}};">
      <span class="news-source-icon" style="background:${{m.color}};">${{m.icon}}</span>
      ${{esc(source)}}
      <span style="opacity:.5;font-weight:400;margin-left:2px;">${{catIcon}}</span>
    </span>`;
  }}

  let html = '';

  // Featured story (first article) — only when showing All or a single category
  const featured = articles[0];
  const rest = articles.slice(1);
  const fm = _sourceMeta(featured.source);

  const featuredImgPanel = featured.image_url
    ? `<div class="news-featured-image">
         <img src="${{esc(featured.image_url)}}" alt="" loading="lazy"
              onerror="this.parentNode.style.background='linear-gradient(135deg,${{fm.color}}22,${{fm.color}}44)';this.remove();">
       </div>`
    : `<div class="news-featured-image" style="background:linear-gradient(135deg,${{fm.color}}22,${{fm.color}}44);">
         <span style="font-size:72px;opacity:.3;user-select:none;">${{fm.icon}}</span>
         <div style="position:absolute;bottom:16px;right:16px;font-size:28px;font-weight:900;color:${{fm.color}};opacity:.5;font-family:serif;">${{esc(featured.source)}}</div>
       </div>`;

  html += `<div class="news-featured" onclick="window.open(${{JSON.stringify(featured.link || '#')}}, '_blank')" style="cursor:pointer;">
    <div class="news-featured-body">
      ${{makeSourceBadge(featured.source, featured._cat)}}
      <div class="news-headline" style="margin-top:12px;">${{esc(featured.title)}}</div>
      <div class="news-summary" style="margin-top:8px;">${{esc((featured.summary || '').slice(0,220))}}</div>
      <div style="margin-top:16px;display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:10px;color:var(--text-3);">${{featured._cat === 'finance' ? '📈 Finance' : '🌍 World'}}</span>
        ${{featured.link ? `<a class="news-read-link" href="${{esc(featured.link)}}" target="_blank" onclick="event.stopPropagation()">Read full story →</a>` : ''}}
      </div>
    </div>
    ${{featuredImgPanel}}
  </div>`;

  // Section: remaining world articles
  if (_newsFilter !== 'finance') {{
    const worldRest = rest.filter(a => a._cat === 'world');
    if (worldRest.length > 0) {{
      html += `<div class="news-section-label" style="grid-column:1/-1;">🌍 World News</div>`;
      html += worldRest.map(a => {{
        const thumb = a.image_url
          ? `<div class="news-thumb"><img src="${{esc(a.image_url)}}" alt="" loading="lazy" onerror="this.parentNode.remove()"></div>`
          : '';
        return `<a class="${{a.image_url ? 'news-card news-card-has-thumb' : 'news-card'}}" href="${{esc(a.link || '#')}}" target="_blank">
          ${{thumb}}
          ${{makeSourceBadge(a.source, a._cat)}}
          <div class="news-headline">${{esc(a.title)}}</div>
          ${{a.summary ? `<div class="news-summary">${{esc(a.summary.slice(0,150))}}</div>` : ''}}
          ${{a.link ? `<span class="news-read-link">Read →</span>` : ''}}
        </a>`;
      }}).join('');
    }}
  }}

  // Section: remaining finance articles
  if (_newsFilter !== 'world') {{
    const financeRest = rest.filter(a => a._cat === 'finance');
    if (financeRest.length > 0) {{
      html += `<div class="news-section-label" style="grid-column:1/-1;">📈 Finance & Markets</div>`;
      html += financeRest.map(a => {{
        const thumb = a.image_url
          ? `<div class="news-thumb"><img src="${{esc(a.image_url)}}" alt="" loading="lazy" onerror="this.parentNode.remove()"></div>`
          : '';
        return `<a class="${{a.image_url ? 'news-card news-card-has-thumb' : 'news-card'}}" href="${{esc(a.link || '#')}}" target="_blank">
          ${{thumb}}
          ${{makeSourceBadge(a.source, a._cat)}}
          <div class="news-headline">${{esc(a.title)}}</div>
          ${{a.summary ? `<div class="news-summary">${{esc(a.summary.slice(0,150))}}</div>` : ''}}
          ${{a.link ? `<span class="news-read-link">Read →</span>` : ''}}
        </a>`;
      }}).join('');
    }}
  }}

  grid.innerHTML = html;
}}

async function loadBriefing() {{
  try {{
    const res = await fetch('/api/briefing');
    if (!res.ok) {{ console.warn('loadBriefing', res.status); return; }}
    const data = await res.json();
    renderBriefing(data);
  }} catch(e) {{ console.error('loadBriefing failed', e); }}
}}

/* ═══ FAITH AGENTS ═══════════════════════════════════════════════════════ */

let _faithAgents = [];
let _faithActiveAgent = null;
let _faithMessages = [];

async function loadFaith() {{
  // Load daily word
  try {{
    const dw = await fetch('/api/faith/daily-word').then(r => r.json());
    if (dw && dw.word) {{
      document.getElementById('faith-dw-agent').textContent = dw.agent_name + ' · ' + dw.agent_title;
      document.getElementById('faith-dw-body').textContent = dw.word;
      document.getElementById('faith-dw-passage').textContent = dw.passage || '';
      const banner = document.getElementById('faith-daily-word');
      if (banner) {{ banner.style.display = ''; banner.style.borderColor = dw.color || 'var(--hue)'; }}
    }}
  }} catch(e) {{ console.warn('faith daily word', e); }}

  // Load roster
  try {{
    const data = await fetch('/api/faith/agents').then(r => r.json());
    _faithAgents = data.agents || [];
    renderFaithRoster();
  }} catch(e) {{
    document.getElementById('faith-roster').innerHTML = '<div class="empty-state">Faith agents unavailable</div>';
  }}
}}

function renderFaithRoster() {{
  const el = document.getElementById('faith-roster');
  if (!el) return;
  if (!_faithAgents.length) {{
    el.innerHTML = '<div class="empty-state">No agents found</div>';
    return;
  }}
  el.innerHTML = _faithAgents.map(a => `
    <div class="faith-agent-card ${{_faithActiveAgent?.id === a.id ? 'active' : ''}}"
         style="--agent-color:${{a.color}}"
         onclick="openFaithChat('${{a.id}}')">
      <div class="faith-agent-avatar" style="background:${{a.color}}">${{a.initials}}</div>
      <div class="faith-agent-name">${{a.name}}</div>
      <div class="faith-agent-title">${{a.title}}</div>
      <div class="faith-agent-desc">${{a.description}}</div>
    </div>
  `).join('');
}}

function openFaithChat(agentId) {{
  const agent = _faithAgents.find(a => a.id === agentId);
  if (!agent) return;
  _faithActiveAgent = agent;
  _faithMessages = [];

  // Update card highlight
  renderFaithRoster();

  // Set header
  const avatar = document.getElementById('faith-chat-avatar');
  if (avatar) {{ avatar.textContent = agent.initials; avatar.style.background = agent.color; }}
  const nameEl = document.getElementById('faith-chat-name');
  if (nameEl) nameEl.textContent = agent.name + ' — ' + agent.title;
  const domainEl = document.getElementById('faith-chat-domain');
  if (domainEl) domainEl.textContent = agent.domain;

  // Show panel + clear messages
  const panel = document.getElementById('faith-chat-panel');
  if (panel) panel.style.display = '';
  faithRenderMessages();

  // Scroll to chat
  panel?.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
}}

function closeFaithChat() {{
  _faithActiveAgent = null;
  _faithMessages = [];
  const panel = document.getElementById('faith-chat-panel');
  if (panel) panel.style.display = 'none';
  renderFaithRoster();
}}

function faithRenderMessages() {{
  const el = document.getElementById('faith-chat-messages');
  if (!el) return;
  if (!_faithMessages.length) {{
    const a = _faithActiveAgent;
    el.innerHTML = `<div style="text-align:center;color:var(--text-3);font-size:12px;padding:40px 0;">
      Begin your conversation with ${{a?.name || 'your agent'}}.<br>
      <span style="font-size:11px;opacity:.6;">Ask about a passage, a question, or just say hello.</span>
    </div>`;
    return;
  }}
  el.innerHTML = _faithMessages.map(m => {{
    const body = m.role === 'user' ? m.content : faithMarkdownToHtml(m.content);
    return `<div class="faith-chat-bubble ${{m.role === 'user' ? 'user' : 'agent'}}">${{body}}</div>`;
  }}).join('');
  el.scrollTop = el.scrollHeight;
}}

function faithMarkdownToHtml(md) {{
  return md
    .replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>')
    .replace(/\\*(.+?)\\*/g, '<em>$1</em>')
    .replace(/^#{{1,3}} (.+)$/gm, '<strong>$1</strong>')
    .replace(/\\n{{2,}}/g, '</p><p>')
    .replace(/\\n/g, '<br>')
    .replace(/^(.+)$/, '<p>$1</p>');
}}

async function faithSend() {{
  const input = document.getElementById('faith-chat-input');
  const passage = document.getElementById('faith-chat-passage')?.value.trim() || '';
  const text = input?.value.trim();
  if (!text || !_faithActiveAgent) return;

  const btn = document.getElementById('faith-send-btn');
  if (btn) btn.disabled = true;
  if (input) {{ input.value = ''; input.disabled = true; }}

  _faithMessages.push({{ role: 'user', content: text }});
  faithRenderMessages();

  // Typing indicator
  const messagesEl = document.getElementById('faith-chat-messages');
  const typing = document.createElement('div');
  typing.className = 'faith-typing';
  typing.id = 'faith-typing';
  typing.innerHTML = '<div class="faith-typing-dot"></div><div class="faith-typing-dot"></div><div class="faith-typing-dot"></div>';
  messagesEl?.appendChild(typing);
  messagesEl && (messagesEl.scrollTop = messagesEl.scrollHeight);

  try {{
    const res = await fetch('/api/faith/chat', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        agent_id: _faithActiveAgent.id,
        passage,
        messages: _faithMessages.map(m => ({{ role: m.role, content: m.content }}))
      }})
    }});
    const data = await res.json();
    document.getElementById('faith-typing')?.remove();
    if (data.ok && data.reply) {{
      _faithMessages.push({{ role: 'assistant', content: data.reply }});
    }} else {{
      _faithMessages.push({{ role: 'assistant', content: data.detail || 'Something went wrong.' }});
    }}
  }} catch(e) {{
    document.getElementById('faith-typing')?.remove();
    _faithMessages.push({{ role: 'assistant', content: 'Faith agent unavailable right now.' }});
  }}

  faithRenderMessages();
  if (btn) btn.disabled = false;
  if (input) {{ input.disabled = false; input.focus(); }}
}}

/* ═══ QUICK CAPTURE (Phase 3) ═══════════════════════════════════════════ */

let _qcType = 'note';

const _QC_LABELS = {{
  note: '📝 Note',
  gratitude: '🙏 Gratitude',
  prayer: '✦ Prayer',
  milestone: '🏆 Milestone',
  reflection: '✍ Reflection',
  insight: '💡 Insight',
  study: '📖 Study',
}};

function openQuickCapture(type) {{
  _qcType = type || 'note';
  const label = _QC_LABELS[_qcType] || _qcType;
  const html = `
    <div class="qc-modal-backdrop" id="qc-modal" onclick="if(event.target===this)closeQcModal()">
      <div class="qc-modal">
        <div class="qc-modal-title">${{label}}</div>
        <textarea class="qc-modal-textarea" id="qc-text" rows="4"
          placeholder="What\'s on your heart?…"
          onkeydown="if(event.key==='Enter'&&event.metaKey)submitQuickCapture()"></textarea>
        <input class="qc-passage-input" id="qc-passage" type="text" placeholder="Passage (optional — e.g. Psalm 23:1)">
        <div class="qc-footer">
          <button class="btn btn-sm" onclick="closeQcModal()">Cancel</button>
          <button class="btn btn-hue btn-sm" onclick="submitQuickCapture()">Capture →</button>
        </div>
      </div>
    </div>`;
  document.body.insertAdjacentHTML('beforeend', html);
  setTimeout(() => document.getElementById('qc-text')?.focus(), 50);
}}

function closeQcModal() {{
  document.getElementById('qc-modal')?.remove();
}}

async function submitQuickCapture() {{
  const content = document.getElementById('qc-text')?.value.trim();
  const passage = document.getElementById('qc-passage')?.value.trim() || '';
  if (!content) {{ showToast('Nothing to capture', 'warning'); return; }}

  const btn = document.querySelector('#qc-modal .btn-hue');
  if (btn) btn.disabled = true;

  try {{
    const res = await fetch('/api/chronicle/quick-capture', {{
      method: 'POST',
      headers: {{'Content-Type':'application/json'}},
      body: JSON.stringify({{ type: _qcType, content, passage }})
    }});
    const data = await res.json();
    closeQcModal();
    if (data.ok) {{
      showToast(`${{_QC_LABELS[_qcType] || 'Entry'}} captured ✓`, 'success');
      // Refresh Chronicle view if active
      if (document.getElementById('view-chronicle')?.classList.contains('active')) loadChronicle();
    }} else {{
      showToast(data.detail || 'Capture failed', 'warning');
    }}
  }} catch(e) {{
    closeQcModal();
    showToast('Chronicle unavailable', 'warning');
  }}
}}

// Inline capture card in Chronicle view
let _chrCaptureType = 'note';

function setChrCaptureType(btn, type) {{
  _chrCaptureType = type;
  document.querySelectorAll('.chr-capture-type').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const input = document.getElementById('chr-capture-input');
  const placeholders = {{
    note: "What\'s on your heart? Press Enter to capture…",
    gratitude: 'What are you grateful for today?',
    prayer: 'What would you like to bring before the Lord?',
    insight: 'What did God show you?',
    milestone: 'What milestone are you marking?',
  }};
  if (input) input.placeholder = placeholders[type] || "What\'s on your heart?";
}}

async function chrQuickCapture() {{
  const content = document.getElementById('chr-capture-input')?.value.trim();
  const passage = document.getElementById('chr-capture-passage')?.value.trim() || '';
  if (!content) return;

  try {{
    const res = await fetch('/api/chronicle/quick-capture', {{
      method: 'POST',
      headers: {{'Content-Type':'application/json'}},
      body: JSON.stringify({{ type: _chrCaptureType, content, passage }})
    }});
    const data = await res.json();
    if (data.ok) {{
      document.getElementById('chr-capture-input').value = '';
      document.getElementById('chr-capture-passage').value = '';
      showToast('Captured ✓', 'success');
      loadChronicle();
    }} else {{
      showToast(data.detail || 'Capture failed', 'warning');
    }}
  }} catch(e) {{
    showToast('Chronicle unavailable', 'warning');
  }}
}}

/* ═══ SPIRITUAL CONTEXT (Phase 4) ═══════════════════════════════════════ */

let _chronicleContext = null;

async function loadChronicleContext() {{
  try {{
    const data = await fetch('/api/chronicle/context').then(r => r.json());
    if (!data.ok) return;
    _chronicleContext = data;
    injectSpiritualContext(data);
  }} catch(e) {{
    console.warn('loadChronicleContext', e);
  }}
}}

function injectSpiritualContext(ctx) {{
  // Inject into Morning Brief if the element is present
  const briefEl = document.getElementById('brief-text');
  if (!briefEl) return;

  // Check if spiritual context already injected
  if (briefEl.querySelector('.brief-spiritual-ctx')) return;

  const rows = [];

  if (ctx.study?.passage) {{
    rows.push(`
      <div class="brief-spiritual-row">
        <span class="brief-spiritual-icon">📖</span>
        <span class="brief-spiritual-text">Studying <strong>${{escHtml(ctx.study.passage)}}</strong>${{ctx.study.title ? ' — ' + escHtml(ctx.study.title) : ''}}</span>
        <button class="brief-chr-btn" onclick="openBibleStudyModal('${{escHtml(ctx.study.passage)}}')">Study →</button>
      </div>`);
  }}

  if (ctx.todays_rhythm?.name) {{
    rows.push(`
      <div class="brief-spiritual-row">
        <span class="brief-spiritual-icon">🌱</span>
        <span class="brief-spiritual-text">Today\'s rhythm: <strong>${{escHtml(ctx.todays_rhythm.name)}}</strong>${{ctx.todays_rhythm.description ? ' — ' + escHtml(ctx.todays_rhythm.description) : ''}}</span>
      </div>`);
  }}

  if (ctx.active_prayers?.length) {{
    const prayerText = ctx.active_prayers.map(p => escHtml(p.text)).join(' · ');
    rows.push(`
      <div class="brief-spiritual-row">
        <span class="brief-spiritual-icon">🙏</span>
        <span class="brief-spiritual-text">Praying for: ${{prayerText}}</span>
        <button class="brief-chr-btn" onclick="switchView('chronicle')">→ Chronicle</button>
      </div>`);
  }}

  if (!rows.length) return;

  const ctx_html = `<div class="brief-spiritual-ctx">${{rows.join('')}}</div>`;
  briefEl.insertAdjacentHTML('beforeend', ctx_html);
}}

async function loadPatterns() {{
  try {{
    const data = await fetch('/api/chronicle/patterns').then(r => r.json());
    if (!data.ok) return;
    renderPatterns(data);
  }} catch(e) {{ console.warn('loadPatterns', e); }}
}}

function renderPatterns(p) {{
  const el = document.getElementById('chr-patterns');
  if (!el) return;

  const typeIcons = {{
    insight:'💡', reflection:'✍', prayer:'🙏', gratitude:'🙏',
    study:'📖', note:'📝', milestone:'🏆'
  }};

  const typeBreakdown = Object.entries(p.entry_type_breakdown || {{}})
    .sort((a,b) => b[1]-a[1])
    .map(([t,c]) => `<div class="pattern-tile"><div class="pattern-tile-num">${{c}}</div><div class="pattern-tile-lbl">${{typeIcons[t]||''}} ${{t}}</div></div>`)
    .join('');

  const themes = (p.recurring_themes || [])
    .map(t => `<span class="pattern-theme-chip">${{escHtml(t.theme)}} <span style="opacity:.6;font-size:10px;">×${{t.count}}</span></span>`)
    .join('');

  el.innerHTML = `
    <div class="pattern-grid">
      <div class="pattern-tile">
        <div class="pattern-tile-num">${{p.writing_streak_days || 0}}</div>
        <div class="pattern-tile-lbl">Day Streak</div>
      </div>
      <div class="pattern-tile">
        <div class="pattern-tile-num">${{p.total_recent_entries || 0}}</div>
        <div class="pattern-tile-lbl">Last 30 Days</div>
      </div>
      <div class="pattern-tile">
        <div class="pattern-tile-num" style="color:#3ecf8e">${{p.prayer_arc?.answered_recent || 0}}</div>
        <div class="pattern-tile-lbl">Prayers Answered</div>
      </div>
      ${{typeBreakdown}}
    </div>
    ${{themes ? `<div style="margin-top:12px;">${{themes}}</div>` : ''}}`;
}}

async function loadChronicle() {{
  try {{
    const res = await fetch('/api/chronicle/recent');
    if (!res.ok) {{ console.warn('loadChronicle', res.status); return; }}
    const data = await res.json();
    renderChronicle(data);
    loadChronicleContext();
    loadPatterns();
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

/* ═══════════════════════════════════════════════════════════════
   UNIVERSAL AGENT ROSTER
   Fetches from /api/agents/roster which merges life_agents.json +
   external_agents.json (Chronicle, Ghostwritr, Catalyst, future).
   Any POST to /api/agents/register immediately appears here.
═══════════════════════════════════════════════════════════════ */
async function loadAgentRoster() {{
  try {{
    const res = await fetch('/api/agents/roster');
    if (!res.ok) {{ console.warn('loadAgentRoster', res.status); return; }}
    const d = await res.json();
    const incoming = d.agents || [];
    if (!incoming.length) return;

    // Normalize domain to a DOMAIN_CLASS key
    const domNorm = s => {{
      if (!s) return 'Operations';
      const mapped = DOMAIN_CLASS[s];
      if (mapped) return s;  // known key
      // Title-case fallback
      return s.charAt(0).toUpperCase() + s.slice(1);
    }};

    // Build a merged array: API data takes priority, fallback keeps existing
    const existingById = {{}};
    AGENTS.forEach(a => {{ existingById[a.id] = a; }});

    const merged = incoming.map(a => ({{
      id:     a.id,
      name:   a.name || a.id.toUpperCase(),
      title:  a.title || '',
      domain: domNorm(a.domain),
      tier:   a.tier || 'execution',
      status: existingById[a.id]?.status || a.status || 'standby',
      source: a.source || 'jarvis',
      purpose: a.purpose || '',
    }}));

    // Splice in any locally-known agents the API didn't return (graceful fallback)
    const mergedIds = new Set(merged.map(a => a.id));
    AGENTS.forEach(a => {{ if (!mergedIds.has(a.id)) merged.push(a); }});

    AGENTS.length = 0;
    merged.forEach(a => AGENTS.push(a));

    renderAgents(currentFilter);
    _updateRosterSourceBadge(d.count || AGENTS.length);
  }} catch(e) {{ console.error('loadAgentRoster failed', e); }}
}}

function _updateRosterSourceBadge(count) {{
  const el = document.getElementById('agent-roster-count');
  if (el) el.textContent = count + ' agents';
}}

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

function showIdeaAddModal() {{
  // The inline quick-capture bar is already visible — just focus it
  const inp = document.getElementById('huddle-idea-input');
  if (inp) {{ inp.focus(); inp.scrollIntoView({{ behavior: 'smooth', block: 'center' }}); }}
}}

async function huddleBulkImport(input) {{
  const file = input.files && input.files[0];
  if (!file) return;
  const statusEl = document.getElementById('huddle-bulk-status');
  const domain = document.getElementById('huddle-bulk-domain')?.value || 'general';
  if (statusEl) {{ statusEl.style.display = 'inline'; statusEl.textContent = 'Importing…'; }}
  const fd = new FormData();
  fd.append('file', file);
  fd.append('domain', domain);
  fd.append('source', 'import');
  try {{
    const res = await fetch('/api/ideas/bulk-import', {{ method: 'POST', body: fd }});
    const data = await res.json();
    if (res.ok) {{
      const msg = `✓ ${{data.imported}} idea${{data.imported !== 1 ? 's' : ''}} imported` +
        (data.skipped ? ` (${{data.skipped}} skipped)` : '');
      if (statusEl) {{ statusEl.textContent = msg; statusEl.style.color = 'var(--green, #4ade80)'; }}
      showToast(msg, 'success');
      loadIdeaInbox();
    }} else {{
      const err = data.detail || 'Import failed';
      if (statusEl) {{ statusEl.textContent = '✗ ' + err; statusEl.style.color = 'var(--red, #f87171)'; }}
      showToast('Import failed: ' + err, 'error');
    }}
  }} catch(e) {{
    if (statusEl) {{ statusEl.textContent = '✗ Network error'; }}
    showToast('Network error: ' + e, 'error');
  }}
  input.value = '';
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

async function loadOverviewMapsUsage() {{
  const content = document.getElementById('maps-usage-content');
  const badge   = document.getElementById('maps-usage-badge');
  if (!content) return;
  try {{
    const res = await fetch('/api/google/maps-usage');
    const d   = await res.json();
    if (d.error === 'not_configured') {{
      content.innerHTML = `<div style="font-size:12px;color:var(--text-3);padding:4px 0;">
        Set <code>GOOGLE_CLOUD_SA_KEY_PATH</code> and<br><code>GOOGLE_CLOUD_PROJECT_ID</code> to enable.
      </div>`;
      if (badge) badge.textContent = 'setup needed';
      return;
    }}
    if (d.error) {{
      content.innerHTML = `<div style="font-size:11px;color:rgba(255,80,80,0.8);">${{escHtml(d.error)}}</div>`;
      return;
    }}

    const pct   = d.pct_used || 0;
    const barW  = Math.min(100, pct);
    const barClr = pct > 80 ? '#ff4444' : pct > 50 ? '#FFD700' : '#00D4FF';

    if (badge) badge.textContent = '$' + d.estimated_cost.toFixed(2) + ' / $200';

    const rows = Object.entries(d.usage || {{}}).map(([name, info]) => {{
      const reqs = info.requests.toLocaleString();
      const cost = ((info.requests / 1000) * info.price_per_k).toFixed(3);
      return `<div style="display:flex;justify-content:space-between;align-items:center;
                          padding:2px 0;font-size:11px;color:var(--text-2);">
        <span>${{escHtml(name)}}</span>
        <span style="font-family:var(--font-mono);color:var(--text-3);">${{reqs}} req · $${{cost}}</span>
      </div>`;
    }}).join('');

    content.innerHTML = `
      <div style="margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;font-size:11px;
                    color:var(--text-3);margin-bottom:4px;">
          <span>${{escHtml(d.month)}} · ${{d.days_elapsed}}/${{d.days_in_month}} days</span>
          <span style="color:${{barClr}};font-weight:700;">${{pct}}% of free credit used</span>
        </div>
        <div style="height:6px;border-radius:3px;background:rgba(255,255,255,0.08);overflow:hidden;">
          <div style="height:100%;width:${{barW}}%;background:${{barClr}};
                      border-radius:3px;transition:width 0.6s;"></div>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:10px;
                    color:var(--text-3);margin-top:3px;">
          <span>${{d.remaining_credit.toFixed(2)}} remaining</span>
          <span>Projected: $${{d.projected_cost}}/mo</span>
        </div>
      </div>
      <div style="border-top:1px solid rgba(255,255,255,0.07);padding-top:8px;">
        ${{rows}}
      </div>`;
  }} catch(e) {{
    if (content) content.innerHTML = '<div style="font-size:11px;color:var(--text-3);">Unavailable</div>';
  }}
}}

async function loadOverviewCosts() {{
  const content = document.getElementById('jarvis-costs-content');
  const badge   = document.getElementById('jarvis-costs-badge');
  if (!content) return;
  try {{
    const res = await fetch('/api/costs/summary');
    if (!res.ok) throw new Error('fetch failed');
    const d = await res.json();

    // Net cost = what you actually owe after Google's $200/mo Maps credit
    const netTotal   = (d.net_total    || 0).toFixed(2);
    const today      = (d.today_llm    || 0).toFixed(3);
    const monthLLM   = (d.month_llm    || 0).toFixed(2);
    const mapsGross  = (d.month_maps   || 0).toFixed(2);
    const mapsNet    = (d.month_maps_net || 0).toFixed(2);
    const credit     = (d.maps_free_credit || 200).toFixed(0);
    const remaining  = (d.maps_remaining  || 200).toFixed(2);
    const mapsPct    = d.maps_pct_used || 0;

    if (badge) badge.textContent = '$' + netTotal + '/mo net';

    // Build per-model breakdown rows
    const models = d.by_model || {{}};
    const modelRows = Object.entries(models)
      .sort((a,b) => (b[1].cost||0) - (a[1].cost||0))
      .map(([name, info]) => {{
        const cost  = (info.cost || 0).toFixed(3);
        const calls = (info.calls || 0).toLocaleString();
        const back  = info.backend === 'ollama'
          ? '<span style="color:#4ade80;font-size:9px;margin-left:4px;">FREE</span>'
          : '<span style="color:#FFD700;font-size:9px;margin-left:4px;">PAID</span>';
        return `<div style="display:flex;justify-content:space-between;align-items:center;
                            padding:2px 0;font-size:11px;color:var(--text-2);">
          <span style="display:flex;align-items:center;">${{escHtml(name)}}${{back}}</span>
          <span style="font-family:var(--font-mono);color:var(--text-3);">${{calls}} calls · $${{cost}}</span>
        </div>`;
      }}).join('');

    const daysLeft  = (d.days_in_month || 30) - (d.days_elapsed || 0);
    const projected = d.days_elapsed > 0
      ? ((d.net_total / d.days_elapsed) * (d.days_in_month || 30)).toFixed(2)
      : '—';
    const tokens  = d.month_tokens || {{}};
    const tokStr  = tokens.input
      ? ((tokens.input + (tokens.output||0)) / 1000000).toFixed(2) + 'M tokens'
      : '';
    const barW    = Math.min(100, mapsPct);
    const barClr  = mapsPct > 80 ? '#ff4444' : mapsPct > 50 ? '#FFD700' : '#4ade80';

    content.innerHTML = `
      <!-- Net cost hero tile -->
      <div style="background:rgba(0,212,255,0.06);border:1px solid rgba(0,212,255,0.18);
                  border-radius:10px;padding:10px 14px;margin-bottom:12px;
                  display:flex;align-items:center;justify-content:space-between;">
        <div>
          <div style="font-size:11px;color:var(--text-3);margin-bottom:2px;">NET THIS MONTH</div>
          <div style="font-size:26px;font-weight:700;color:#00D4FF;font-family:var(--font-mono);line-height:1;">
            $${{netTotal}}
          </div>
          <div style="font-size:10px;color:var(--text-3);margin-top:3px;">
            after Google's $${{credit}} Maps credit
          </div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:10px;color:var(--text-3);">today</div>
          <div style="font-size:15px;font-weight:600;color:#00D4FF;font-family:var(--font-mono);">$${{today}}</div>
          <div style="font-size:10px;color:var(--text-3);margin-top:4px;">projected</div>
          <div style="font-size:13px;font-weight:600;color:var(--text-2);font-family:var(--font-mono);">$${{projected}}/mo</div>
        </div>
      </div>

      <!-- LLM + Maps row -->
      <div style="display:flex;gap:8px;margin-bottom:10px;">
        <div style="flex:1;background:rgba(255,255,255,0.04);border-radius:8px;padding:8px 10px;">
          <div style="font-size:10px;color:var(--text-3);margin-bottom:3px;">LLM (AI models)</div>
          <div style="font-size:16px;font-weight:700;color:#FFD700;font-family:var(--font-mono);">$${{monthLLM}}</div>
          <div style="font-size:9px;color:var(--text-3);margin-top:2px;">${{tokStr}}</div>
        </div>
        <div style="flex:1;background:rgba(255,255,255,0.04);border-radius:8px;padding:8px 10px;">
          <div style="font-size:10px;color:var(--text-3);margin-bottom:3px;">Google Maps API</div>
          <div style="font-size:16px;font-weight:700;color:${{mapsNet==='0.00'?'#4ade80':'#f87171'}};font-family:var(--font-mono);">
            ${{mapsNet === '0.00' ? 'FREE' : '$$'+mapsNet}}
          </div>
          <div style="font-size:9px;color:var(--text-3);margin-top:2px;">
            $${{mapsGross}} gross · $${{remaining}} credit left
          </div>
          <!-- Credit bar -->
          <div style="height:3px;border-radius:2px;background:rgba(255,255,255,0.08);
                      overflow:hidden;margin-top:5px;">
            <div style="height:100%;width:${{barW}}%;background:${{barClr}};
                        border-radius:2px;transition:width 0.6s;"></div>
          </div>
          <div style="font-size:9px;color:${{barClr}};margin-top:2px;">${{mapsPct}}% of $${{credit}} used</div>
        </div>
      </div>

      <!-- Per-model breakdown -->
      <div style="border-top:1px solid rgba(255,255,255,0.07);padding-top:8px;">
        <div style="font-size:9px;color:var(--text-3);margin-bottom:4px;text-transform:uppercase;
                    letter-spacing:0.08em;">Model Breakdown</div>
        ${{modelRows}}
        <div style="font-size:9px;color:var(--text-3);margin-top:6px;text-align:right;">
          ${{daysLeft}} days left in ${{escHtml(d.month||'')}}
        </div>
      </div>`;
  }} catch(e) {{
    if (content) content.innerHTML = '<div style="font-size:11px;color:var(--text-3);">Unavailable</div>';
  }}
}}

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
  if (next) {{
    const nextDate = next.start_time ? new Date(next.start_time).toLocaleDateString([], {{weekday:'short',month:'short',day:'numeric'}}) : '';
    const nextEl = document.getElementById('overviewNextEvent');
    if (nextEl) nextEl.innerHTML = '<b>' + escHtml(next.title) + '</b>' + (nextDate ? '<br><span style="opacity:0.7;font-size:11px;">' + escHtml(nextDate) + '</span>' : '');
    // Dining hint — show if next event is at a meal-time hour
    _maybeShowCalendarDiningHint(next);
  }} else {{
    setEl('overviewNextEvent', 'No upcoming events');
  }}
  if (d.projects) {{
    setEl('overviewActiveProjects', d.projects.active != null ? d.projects.active : '—');
  }}
}}

function setEl(id, val) {{
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}}

function _maybeShowCalendarDiningHint(event) {{
  // Show a dining chip if the next event falls during a meal window
  if (!event || !event.start_time) return;
  const h = new Date(event.start_time).getHours();
  const isMealTime = (h >= 11 && h <= 14) || (h >= 17 && h <= 20);
  if (!isMealTime) return;
  const mealLabel = h < 15 ? 'lunch' : 'dinner';
  // Inject hint chip into calendar card body (hero or priority render)
  ['lc-calendar', 'lc-calendar-priority'].forEach(function(id) {{
    const card = document.getElementById(id);
    if (!card) return;
    // Don't add twice
    if (card.querySelector('.dining-cal-hint')) return;
    const chip = document.createElement('div');
    chip.className = 'dining-cal-hint';
    chip.style.cssText = 'margin-top:10px;display:inline-flex;align-items:center;gap:6px;' +
      'background:rgba(99,102,241,0.12);border:1px solid rgba(99,102,241,0.25);' +
      'border-radius:8px;padding:5px 11px;cursor:pointer;font-size:11px;color:var(--hue);';
    chip.innerHTML = '🍽️ Find ' + mealLabel + ' spots nearby →';
    chip.onclick = function(e) {{ e.stopPropagation(); switchView('dining'); }};
    card.querySelector('.card-body, .card-hdr')?.insertAdjacentElement('afterend', chip) ||
    card.appendChild(chip);
  }});
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

/* ═══════════════════════════════════════════════════════════════════
   AGENT CONVERSATION STATE (multi-turn)
═══════════════════════════════════════════════════════════════════ */
let _agentMessages   = [];   // full message history for multi-turn
let _agentConvId     = '';   // stable conversation id for session save
let _agentStreaming  = false; // guard against concurrent sends

function _agentConversationId() {{
  if (!_agentConvId) _agentConvId = 'agent-' + Date.now().toString(36);
  return _agentConvId;
}}

/* ── Helper: escape HTML ── */
function _esc(s) {{ return escHtml ? escHtml(s) : s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }}

/* ── Helper: append a basic message row ── */
function _appendMsg(chatArea, role, content, meta) {{
  const row = document.createElement('div');
  row.className = 'msg-row ' + role;
  const avatarText = role === 'user' ? 'CB' : 'J';
  row.innerHTML = `
    <div class="msg-avatar">${{avatarText}}</div>
    <div>
      <div class="msg-bubble">${{_esc(content)}}</div>
      ${{meta ? `<div class="msg-meta">${{_esc(meta)}}</div>` : ''}}
    </div>`;
  chatArea.appendChild(row);
  chatArea.scrollTop = chatArea.scrollHeight;
  return row;
}}

/* ── Build a tool block element ── */
function _makeToolBlock(toolName, toolInput) {{
  const icons = {{ bash:'⚡', file_ops:'📄', web:'🌐', jarvis_api:'🔗', git:'🔀', memory:'🧠' }};
  const icon = icons[toolName] || '🔧';
  const inputStr = typeof toolInput === 'object' ? JSON.stringify(toolInput, null, 2) : String(toolInput);

  const block = document.createElement('div');
  block.className = 'tool-block';
  block.innerHTML = `
    <div class="tool-header" onclick="this.parentElement.querySelector('.tool-output-area').classList.toggle('expanded'); this.querySelector('.tool-chevron').classList.toggle('open');">
      <span class="tool-icon">${{icon}}</span>
      <span class="tool-name">${{_esc(toolName)}}</span>
      <span class="tool-status running">running…</span>
      <span class="tool-chevron">▶</span>
    </div>
    <div class="tool-input-line">${{_esc(inputStr.length > 200 ? inputStr.slice(0,200)+'…' : inputStr)}}</div>
    <div class="tool-output-area expanded"></div>`;
  return block;
}}

/* ── Build an approval card ── */
function _makeApprovalCard(approvalId, toolName, toolInput) {{
  const inputStr = typeof toolInput === 'object' ? JSON.stringify(toolInput, null, 2) : String(toolInput);
  const card = document.createElement('div');
  card.className = 'approval-card';
  card.dataset.approvalId = approvalId;
  card.innerHTML = `
    <div class="approval-title">⚠️ Approval needed — <strong>${{_esc(toolName)}}</strong></div>
    <div class="approval-detail">${{_esc(inputStr)}}</div>
    <div class="approval-btns">
      <button class="approval-btn approve" onclick="resolveApproval('${{approvalId}}', true, this.closest('.approval-card'))">✓ Approve</button>
      <button class="approval-btn decline" onclick="resolveApproval('${{approvalId}}', false, this.closest('.approval-card'))">✗ Decline</button>
    </div>`;
  return card;
}}

/* ── Resolve an approval ── */
async function resolveApproval(approvalId, approved, cardEl) {{
  try {{
    await fetch('/api/agent/approve', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ approval_id: approvalId, approved }})
    }});
    if (cardEl) {{
      cardEl.querySelector('.approval-btns').style.display = 'none';
      const msg = document.createElement('div');
      msg.className = 'approval-resolved';
      msg.textContent = approved ? '✓ Approved — running…' : '✗ Declined — skipped';
      cardEl.appendChild(msg);
    }}
  }} catch(e) {{
    console.warn('resolveApproval failed:', e);
  }}
}}

/* ══════════════════════════════════════════════════════════════════
   MAIN: sendCommand  — now uses the agentic streaming endpoint
══════════════════════════════════════════════════════════════════ */
async function sendCommand(text) {{
  if (!text || !text.trim()) return;
  if (_agentStreaming) {{ showToast('Agent is still working…', 'warning'); return; }}

  switchView('chat');
  const chatArea = document.getElementById('chat-area');
  const emptyEl  = document.getElementById('chat-empty');
  if (emptyEl) emptyEl.style.display = 'none';

  /* ── Append user message ── */
  const now = new Date().toLocaleTimeString([], {{hour:'2-digit', minute:'2-digit'}});
  _appendMsg(chatArea, 'user', text, now);
  _agentMessages.push({{ role: 'user', content: text }});

  /* ── Build the JARVIS response container ── */
  const jarvisRow = document.createElement('div');
  jarvisRow.className = 'msg-row jarvis';
  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.textContent = 'J';
  const bodyWrap = document.createElement('div');
  bodyWrap.style.minWidth = '0';
  bodyWrap.style.flex = '1';

  /* Streaming text bubble */
  const textBubble = document.createElement('div');
  textBubble.className = 'msg-bubble';
  const cursor = document.createElement('span');
  cursor.className = 'streaming-cursor';
  textBubble.appendChild(cursor);

  bodyWrap.appendChild(textBubble);
  jarvisRow.appendChild(avatar);
  jarvisRow.appendChild(bodyWrap);
  chatArea.appendChild(jarvisRow);
  chatArea.scrollTop = chatArea.scrollHeight;

  _agentStreaming = true;
  let accText = '';
  let activeToolBlocks = {{}};  /* tool_use_id → {{block, outputArea}} */

  try {{
    const res = await fetch('/api/agent/stream', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{
        message: text,
        conversation_id: _agentConversationId(),
        messages: _agentMessages.slice(0, -1)   /* prior turns only; server appends current */
      }})
    }});

    if (!res.ok) {{
      cursor.remove();
      textBubble.textContent = 'Agent endpoint error: ' + res.status;
      _agentStreaming = false;
      return;
    }}

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    while (true) {{
      const {{ done, value }} = await reader.read();
      if (done) break;
      buf += decoder.decode(value, {{ stream: true }});

      const lines = buf.split('\\n');
      buf = lines.pop();   /* keep incomplete line in buf */

      for (const line of lines) {{
        if (!line.startsWith('data: ')) continue;
        let evt;
        try {{ evt = JSON.parse(line.slice(6)); }} catch(_) {{ continue; }}

        const type = evt.type;

        /* ── Text streaming ── */
        if (type === 'text_delta') {{
          accText += evt.delta || '';
          /* Update bubble — keep cursor at end */
          textBubble.textContent = accText;
          textBubble.appendChild(cursor);
          chatArea.scrollTop = chatArea.scrollHeight;
        }}

        /* ── Tool call started ── */
        else if (type === 'tool_call') {{
          const block = _makeToolBlock(evt.tool, evt.input);
          const outputArea = block.querySelector('.tool-output-area');
          bodyWrap.appendChild(block);
          activeToolBlocks[evt.tool_use_id] = {{ block, outputArea }};
          chatArea.scrollTop = chatArea.scrollHeight;
        }}

        /* ── Tool result received ── */
        else if (type === 'tool_result') {{
          const entry = activeToolBlocks[evt.tool_use_id];
          if (entry) {{
            const statusEl = entry.block.querySelector('.tool-status');
            statusEl.textContent = evt.error ? 'error' : 'done';
            statusEl.className   = 'tool-status ' + (evt.error ? 'error' : 'done');
            entry.outputArea.textContent = evt.output || '';
            /* Auto-collapse successful tool outputs */
            if (!evt.error) entry.outputArea.classList.remove('expanded');
          }}
          chatArea.scrollTop = chatArea.scrollHeight;
        }}

        /* ── Approval needed ── */
        else if (type === 'approval_needed') {{
          const card = _makeApprovalCard(evt.approval_id, evt.tool, evt.input);
          bodyWrap.appendChild(card);
          chatArea.scrollTop = chatArea.scrollHeight;
        }}

        /* ── Tool skipped ── */
        else if (type === 'tool_skipped') {{
          /* Find the most recent approval card and mark it */
        }}

        /* ── Done ── */
        else if (type === 'done') {{
          cursor.remove();
          /* Finalize text */
          if (accText) textBubble.textContent = accText;
          else if (!textBubble.textContent) textBubble.textContent = '(no text response)';
          /* Add meta */
          const meta = document.createElement('div');
          meta.className = 'msg-meta';
          meta.textContent = (evt.model || 'qwen2.5:14b') + ' · ' + new Date().toLocaleTimeString([], {{hour:'2-digit', minute:'2-digit'}});
          bodyWrap.appendChild(meta);
          /* Save assistant turn in history */
          _agentMessages.push({{ role: 'assistant', content: accText }});
          /* Speak response if voice is active */
          voiceSpeak(accText);
        }}

        /* ── Error ── */
        else if (type === 'error') {{
          cursor.remove();
          textBubble.textContent = '⚠ ' + (evt.message || 'Unknown error');
        }}

        /* ── Max turns ── */
        else if (type === 'max_turns') {{
          cursor.remove();
          const notice = document.createElement('div');
          notice.className = 'msg-meta';
          notice.textContent = '(reached max turns — task may be incomplete)';
          bodyWrap.appendChild(notice);
        }}
      }}
    }}

  }} catch(e) {{
    cursor.remove();
    textBubble.textContent = 'Connection error: ' + e.message;
  }} finally {{
    _agentStreaming = false;
    chatArea.scrollTop = chatArea.scrollHeight;
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

async function approveDraft(reviewId) {{
  try {{
    const res = await fetch('/api/publishing/draft/approve', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ review_id: reviewId }})
    }});
    if (!res.ok) {{ showToast('Approve failed', 'error'); return; }}
    showToast('Draft approved ✓', 'success');
    loadPublishing();
  }} catch(e) {{ showToast('No connection', 'error'); }}
}}

async function reviseDraft(reviewId) {{
  const feedback = prompt('What needs to change?');
  if (feedback === null) return;
  try {{
    const res = await fetch('/api/publishing/draft/revise', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ review_id: reviewId, feedback: feedback || 'Needs revision' }})
    }});
    if (!res.ok) {{ showToast('Revise request failed', 'error'); return; }}
    showToast('Revision requested', 'info');
    loadPublishing();
  }} catch(e) {{ showToast('No connection', 'error'); }}
}}

/* ═══════════════════════════════════════════════════════════════
   RENDER FUNCTIONS
═══════════════════════════════════════════════════════════════ */
function renderApprovals(items) {{
  const el = document.getElementById('approvals-list');
  if (!el) return;
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

function briefingToHtml(text) {{
  // Parse briefing — skip [SOURCE] news lines (now in dedicated News view)
  const lines = text.split('\\n');
  let html = '';
  let i = 0;
  let skippedNewsCount = 0;
  const esc = s => escHtml(s.replace(/&#0*39;/g, "'").replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"'));
  while (i < lines.length) {{
    const line = lines[i].trim();
    if (!line || line === '---') {{ i++; continue; }}
    // ## Section heading — skip news section headers
    if (line.startsWith('## ')) {{
      const heading = line.slice(3).toLowerCase();
      if (heading.includes('news') || heading.includes('live')) {{ i++; continue; }}
      html += `<div style="font-size:10px;font-weight:700;letter-spacing:.08em;color:var(--text-3);text-transform:uppercase;margin:10px 0 6px;">${{esc(line.slice(3))}}</div>`;
      i++; continue;
    }}
    // [SOURCE] Title — skip, these are news items now in News view
    const srcMatch = line.match(/^\\[([^\\]]+)\\]\\s*(.+)$/);
    if (srcMatch) {{
      skippedNewsCount++;
      if (i + 1 < lines.length && lines[i+1].trim().startsWith('Brief:')) i++;
      i++; continue;
    }}
    if (line.startsWith('Brief:')) {{ i++; continue; }}
    html += `<div style="font-size:12px;color:var(--text-2);margin-bottom:5px;line-height:1.5;">${{esc(line)}}</div>`;
    i++;
  }}
  if (skippedNewsCount > 0) {{
    html += `<div style="margin-top:10px;padding-top:8px;border-top:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;">
      <span style="font-size:11px;color:var(--text-3);">📰 ${{skippedNewsCount}} headlines available</span>
      <button class="btn-ghost" style="font-size:10px;padding:3px 8px;" onclick="switchView('news')">View News →</button>
    </div>`;
  }}
  return html || '<span style="color:var(--text-3);font-style:italic;">No briefing available yet.</span>';
}}

function renderBriefing(data) {{
  const textEl = document.getElementById('brief-text');
  const dateEl = document.getElementById('brief-date');
  if (!data) return;
  const dateStr = data.date || new Date().toLocaleDateString([], {{weekday:'short', month:'short', day:'numeric'}});
  if (dateEl) dateEl.textContent = dateStr;
  if (!textEl) return;

  // Structured sections (new format)
  if (data.sections && data.sections.length) {{
    textEl.innerHTML = data.sections.map(renderBriefSection).join('');
    return;
  }}
  // Fallback: legacy plain-text briefing
  const raw = data.briefing || data.content || data.text || '';
  const text = typeof raw === 'string' ? raw : (raw[0] || '');
  textEl.innerHTML = text ? briefingToHtml(text) : '<span style="color:var(--text-3);font-style:italic;">No briefing available.</span>';
}}

function renderBriefSection(s) {{
  const icon  = s.icon  ? escHtml(s.icon)  + ' ' : '';
  const title = s.title ? escHtml(s.title) : '';
  const hdr   = `<div style="font-size:10px;font-weight:700;letter-spacing:.08em;color:var(--blue);text-transform:uppercase;margin:12px 0 5px;opacity:.9;">${{icon}}${{title}}</div>`;

  // Calendar — event list
  if (s.id === 'calendar' && s.items && s.items.length) {{
    const rows = s.items.map(ev => {{
      const dayEl  = ev.day  ? `<span style="color:var(--text-3);font-size:10px;min-width:72px;flex-shrink:0;">${{escHtml(ev.day)}}</span>` : '';
      const timeEl = ev.time ? `<span style="color:var(--text-3);font-size:10px;margin-left:4px;">${{escHtml(ev.time)}}</span>` : '';
      const calEl  = ev.calendar ? `<span style="opacity:.4;font-size:10px;margin-left:auto;white-space:nowrap;">${{escHtml(ev.calendar)}}</span>` : '';
      return `<div style="display:flex;align-items:baseline;gap:2px;margin-bottom:5px;font-size:12px;color:var(--text-2);">${{dayEl}}<span style="flex:1;">${{escHtml(ev.title)}}</span>${{timeEl}}${{calEl}}</div>`;
    }}).join('');
    return hdr + rows;
  }}

  // Tasks — stat pills
  if (s.id === 'tasks' && s.stats) {{
    const parts = [];
    if (s.stats.overdue)   parts.push(`<span style="color:var(--red);font-weight:600;">${{s.stats.overdue}} overdue</span>`);
    if (s.stats.due_today) parts.push(`<span style="color:var(--amber);font-weight:600;">${{s.stats.due_today}} due today</span>`);
    if (s.stats.due_week)  parts.push(`<span style="color:var(--text-2);">${{s.stats.due_week}} this week</span>`);
    const dot = `<span style="color:var(--border);margin:0 5px;">·</span>`;
    return hdr + `<div style="font-size:12px;line-height:1.8;">${{parts.join(dot)}}</div>`;
  }}

  // Email
  if (s.id === 'email' && s.stats) {{
    return hdr + `<div style="font-size:12px;color:var(--text-2);display:flex;align-items:center;gap:8px;">
      <b style="color:var(--text-1);">${{s.stats.total}}</b>&nbsp;unread
      <span style="color:var(--text-3);">Gmail ${{s.stats.gmail}} · Outlook ${{s.stats.outlook}}</span>
      <button class="btn-ghost" style="font-size:10px;padding:2px 8px;" onclick="switchView('email')">Open →</button>
    </div>`;
  }}

  // Approvals
  if (s.id === 'approvals' && s.count) {{
    return hdr + `<div style="font-size:12px;display:flex;align-items:center;gap:8px;">
      <span style="color:var(--amber);font-weight:600;">${{s.count}} item${{s.count !== 1 ? 's' : ''}} waiting</span>
      <button class="btn-ghost" style="font-size:10px;padding:2px 8px;" onclick="switchView('approvals')">Review →</button>
    </div>`;
  }}

  // Dining — Sam's meal picks
  if (s.id === 'dining' && s.items && s.items.length) {{
    const mealLabel = s.meal_type ? escHtml(s.meal_type) + ' picks' : 'picks';
    const rows = s.items.map(p => {{
      const openBadge = p.open_now === true
        ? '<span style="color:#4ade80;font-size:9px;font-weight:700;margin-left:4px;">OPEN</span>'
        : p.open_now === false ? '<span style="color:#f87171;font-size:9px;margin-left:4px;">CLOSED</span>' : '';
      const stars = p.rating ? `<span style="color:var(--hue);font-weight:700;">${{p.rating}}★</span> ` : '';
      const dist  = p.distance_mi ? `<span style="color:var(--text-3);font-size:10px;">${{p.distance_mi}} mi</span>` : '';
      const price = p.price ? `<span style="color:var(--text-3);font-size:10px;margin-left:4px;">${{escHtml(p.price)}}</span>` : '';
      return `<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;cursor:pointer;" onclick="switchView('dining')">
        <span style="font-size:12px;font-weight:600;color:var(--text-1);flex:1;">${{escHtml(p.name)}}</span>
        ${{stars}}${{dist}}${{price}}${{openBadge}}
      </div>`;
    }}).join('');
    return hdr + `<div style="font-size:11px;color:var(--text-3);margin-bottom:4px;">${{mealLabel}}</div>` + rows +
      `<button class="btn-ghost" style="font-size:10px;padding:2px 8px;margin-top:2px;" onclick="switchView('dining')">More spots →</button>`;
  }}

  // Situation / Health — prose
  if (s.text) {{
    const clean = escHtml(s.text).replace(/\\*\\*([^*]+)\\*\\*/g,'<b>$1</b>').replace(/\\*([^*]+)\\*/g,'<i>$1</i>');
    return hdr + `<div style="font-size:12px;color:var(--text-2);line-height:1.7;">${{clean}}</div>`;
  }}

  return '';
}}

function renderPublishing(data) {{
  if (!data) return;

  const books   = data.active_books || [];
  const reviews = data.pending_review_list || [];

  // ── Stat strip ─────────────────────────────────────────────────
  const _set = (id, v) => {{ const el = document.getElementById(id); if (el) el.textContent = v; }};
  _set('homeProjectsBadge',  books.length  || '0');
  _set('pub-review-count',   reviews.length || '0');
  _set('pub-review-count-badge', reviews.length || '0');
  _set('pub-inprogress-count', data.books_in_progress ?? '—');
  const gwEl = document.getElementById('pub-gw-status');
  if (gwEl) {{
    gwEl.textContent = data.ghostwritr_available ? '● Online' : '○ Offline';
    gwEl.style.color = data.ghostwritr_available ? '#3ecf8e' : 'var(--text-3)';
  }}

  // ── Pending Reviews ────────────────────────────────────────────
  const revSection = document.getElementById('pub-reviews-section');
  const revEl      = document.getElementById('publishing-reviews');
  if (revSection) revSection.style.display = reviews.length > 0 ? '' : 'none';
  if (revEl) {{
    if (reviews.length === 0) {{
      revEl.innerHTML = '';
    }} else {{
      revEl.innerHTML = reviews.map(r => {{
        const stageLabel = (r.stage_display || (r.stage_key || '').replace(/_/g,' ').replace(/\\b\\w/g, c => c.toUpperCase()));
        const wordCount  = r.word_count ? r.word_count.toLocaleString() + ' words' : '';
        const rawPrev    = (r.content_preview || '').trim();
        let preview = '';
        if (rawPrev.startsWith('{{')) {{
          try {{
            const parsed = JSON.parse(rawPrev);
            const parts = [];
            if (parsed.totalWords)    parts.push(parsed.totalWords.toLocaleString() + ' words');
            if (parsed.chapterCount)  parts.push(parsed.chapterCount + ' chapters');
            if (parsed.subtitle)      parts.push(parsed.subtitle.slice(0, 80));
            preview = parts.join(' · ');
          }} catch(e) {{ preview = ''; }}
        }} else {{
          preview = rawPrev.slice(0, 120);
        }}
        const rid = escHtml(r.review_id || r.id || '');
        return `<div class="pub-review-item">
          <div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px;">
            <div class="pub-review-book">${{escHtml(r.title || '—')}}</div>
            <div class="pub-review-stage">⚠ ${{escHtml(stageLabel)}}</div>
          </div>
          ${{wordCount ? `<div class="pub-review-meta">${{escHtml(wordCount)}}</div>` : ''}}
          ${{preview ? `<div class="pub-review-preview">"${{escHtml(preview)}}"</div>` : ''}}
          <div class="pub-review-actions">
            <button class="btn btn-hue btn-sm" onclick="approveDraft('${{rid}}')">✓ Approve</button>
            <button class="btn btn-crimson btn-sm" onclick="reviseDraft('${{rid}}')">↩ Needs Work</button>
            ${{r.slug ? `<a href="${{escHtml(data.ghostwritr_available ? 'http://localhost:3000/books/' + r.slug : '#')}}" target="_blank" class="pub-open-link" style="margin-left:auto;">Open ↗</a>` : ''}}
          </div>
        </div>`;
      }}).join('');
    }}
  }}

  // ── Book Pipeline ──────────────────────────────────────────────
  const STATUS_ICONS = {{
    committed:   {{ cls: 'committed',   tip: 'Committed' }},
    in_progress: {{ cls: 'in_progress', tip: 'In Progress' }},
    review:      {{ cls: 'review',      tip: 'Ready for Review' }},
    blocked:     {{ cls: 'blocked',     tip: 'Blocked' }},
    not_started: {{ cls: 'not_started', tip: 'Not Started' }},
  }};

  // Map stage status strings → dot class
  function stageStatusClass(status) {{
    if (status === 'COMMITTED')         return 'committed';
    if (status === 'IN_PROGRESS')       return 'in_progress';
    if (status === 'READY_FOR_REVIEW')  return 'review';
    if (status === 'BLOCKED')           return 'blocked';
    return 'not_started';
  }}

  const booksEl = document.getElementById('publishing-books');
  if (!booksEl) return;

  if (books.length === 0) {{
    booksEl.innerHTML = `<div class="pub-book-card" style="color:var(--text-3);font-size:13px;text-align:center;padding:32px;">
      No active books found in Ghostwritr. <a href="http://localhost:3000" target="_blank" class="pub-open-link">Open Studio ↗</a>
    </div>`;
    return;
  }}

  booksEl.innerHTML = books.map(book => {{
    const total  = book.total_stages || 19;
    const done   = Math.min(book.stages_complete || 0, total);
    const pct    = total > 0 ? Math.round((done / total) * 100) : 0;
    const ready  = (book.stages_ready_for_review || []);
    const hasReady = ready.length > 0;

    // Overall progress bar
    const progressHtml = `
      <div class="pub-progress-wrap">
        <div class="pub-progress-label">
          <span>${{done}} / ${{total}} stages complete</span>
          <span>${{pct}}%</span>
        </div>
        <div class="pub-progress-bar">
          <div class="pub-progress-fill" style="width:${{pct}}%"></div>
        </div>
      </div>`;

    // Stage groups
    const groups = book.stage_groups || [];
    const groupsHtml = groups.length > 0
      ? `<div class="pub-groups-grid">
          ${{groups.map(g => {{
            const allDone = g.complete === g.total;
            const dots = (g.stages || []).map(s => {{
              const cls = stageStatusClass(s.status);
              return `<div class="pub-stage-dot ${{cls}}" title="${{escHtml(s.display + ': ' + s.status.replace(/_/g,' '))}}"></div>`;
            }}).join('');
            const countCls = allDone ? 'all-done' : '';
            return `<div class="pub-group">
              <div class="pub-group-name">${{escHtml(g.name)}}</div>
              <div class="pub-stage-dots">${{dots}}</div>
              <div class="pub-group-count ${{countCls}}">${{g.complete}}/${{g.total}}${{allDone ? ' ✓' : ''}}</div>
            </div>`;
          }}).join('')}}
        </div>`
      : '';

    // Footer: current stage + review badge + link
    const curStage = book.current_stage
      ? book.current_stage.replace(/_/g,' ').replace(/\\b\\w/g, c => c.toUpperCase())
      : (pct >= 100 ? 'Complete' : '—');
    const reviewBadge = hasReady
      ? `<span class="pub-review-badge">⚠ ${{ready.length}} REVIEW${{ready.length > 1 ? 'S' : ''}}</span>` : '';
    const wordInfo = book.word_count
      ? `${{book.word_count.toLocaleString()}} words${{book.chapter_count ? ' · ' + book.chapter_count + ' ch' : ''}} · ` : '';
    const gwUrl = book.ghostwritr_url || ('#');

    return `<div class="pub-book-card">
      <div class="pub-book-header">
        <div>
          <div class="pub-book-title">${{escHtml(book.title || book.slug || '—')}}</div>
          ${{book.subtitle ? `<div class="pub-book-subtitle">${{escHtml(book.subtitle)}}</div>` : ''}}
        </div>
        <div class="pub-book-meta">
          ${{reviewBadge}}
          <span class="pill pill-hue" style="font-size:9px;">${{escHtml(book.workflow_type || 'NONFICTION')}}</span>
        </div>
      </div>
      ${{progressHtml}}
      ${{groupsHtml}}
      <div class="pub-book-footer">
        <div class="pub-current-stage">
          ${{wordInfo}}Current:<span class="stage-chip">${{escHtml(curStage)}}</span>
        </div>
        <a href="${{escHtml(gwUrl)}}" target="_blank" class="pub-open-link">Open in Ghostwritr ↗</a>
      </div>
    </div>`;
  }}).join('');
}}

/* ═══════════════════════════════════════════════════════════════
   CHRONICLE MODALS
═══════════════════════════════════════════════════════════════ */

// ── Entry Detail Modal ─────────────────────────────────────────
function openEntryModal(entry) {{
  const TYPE_LABELS = {{insight:'Insight',prayer:'Prayer',study:'Study',reflection:'Reflection',note:'Note'}};
  const typeLbl = TYPE_LABELS[entry.type] || entry.type || 'Note';
  const themes = (entry.themes || []).map(t => `<span class="chr-theme-tag">${{escHtml(t)}}</span>`).join('');
  const html = `
    <div class="chr-modal-backdrop" id="chr-entry-modal" onclick="if(event.target===this)closeChrModal('chr-entry-modal')">
      <div class="chr-modal">
        <div class="chr-modal-header">
          <span class="chr-entry-type-pill chr-type-${{escHtml(entry.type || 'note')}}">${{escHtml(typeLbl)}}</span>
          <span class="chr-modal-title">${{escHtml(entry.title || '—')}}</span>
          <button class="chr-modal-close" onclick="closeChrModal('chr-entry-modal')">✕</button>
        </div>
        <div class="chr-modal-body">
          ${{entry.passage ? `<div style="font-size:13px;color:var(--hue);font-weight:500;margin-bottom:12px;">${{escHtml(entry.passage)}}</div>` : ''}}
          ${{entry.body ? `<div style="font-size:13px;color:var(--text-2);line-height:1.65;margin-bottom:14px;white-space:pre-wrap;">${{escHtml(entry.body)}}</div>` : ''}}
          ${{themes ? `<div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:14px;">${{themes}}</div>` : ''}}
          <div style="font-size:11px;color:var(--text-3);">${{escHtml(entry.date || '')}}</div>
        </div>
        <div class="chr-modal-footer">
          <button class="btn btn-hue btn-sm" onclick="saveEntryToChronicle(${{JSON.stringify(entry).replace(/"/g,'&quot;')}})">Save to Chronicle ↗</button>
          <button class="btn btn-sm" style="margin-left:auto;" onclick="closeChrModal('chr-entry-modal')">Close</button>
        </div>
      </div>
    </div>`;
  document.body.insertAdjacentHTML('beforeend', html);
}}

// ── Prayer Item Modal ──────────────────────────────────────────
function openPrayerModal(prayer) {{
  const catLabels = {{people:'People',needs:'Needs',praise:'Praise',world:'World'}};
  const catLbl = catLabels[prayer.category] || prayer.category || '—';
  const isAnswered = prayer.answered;
  const prayed = prayer.timesPrayed || 0;
  const html = `
    <div class="chr-modal-backdrop" id="chr-prayer-modal" onclick="if(event.target===this)closeChrModal('chr-prayer-modal')">
      <div class="chr-modal">
        <div class="chr-modal-header">
          <span class="chr-prayer-cat chr-cat-${{escHtml(prayer.category || 'needs')}}">${{escHtml(catLbl)}}</span>
          <span class="chr-modal-title">${{escHtml(prayer.text || '—')}}</span>
          <button class="chr-modal-close" onclick="closeChrModal('chr-prayer-modal')">✕</button>
        </div>
        <div class="chr-modal-body">
          <div class="chr-prayer-meta-row">
            <div class="chr-prayer-stat">
              <div class="chr-prayer-stat-num">${{prayed}}</div>
              <div class="chr-prayer-stat-lbl">Times Prayed</div>
            </div>
            <div class="chr-prayer-stat">
              <div class="chr-prayer-stat-num" style="color:${{isAnswered?'#3ecf8e':'var(--text-3)'}}">
                ${{isAnswered ? '✓' : '—'}}
              </div>
              <div class="chr-prayer-stat-lbl">Answered</div>
            </div>
            <div class="chr-prayer-stat">
              <div class="chr-prayer-stat-num" style="font-size:13px;">${{escHtml(prayer.dateAdded || '—')}}</div>
              <div class="chr-prayer-stat-lbl">Added</div>
            </div>
            ${{prayer.lastPrayedAt ? `<div class="chr-prayer-stat"><div class="chr-prayer-stat-num" style="font-size:13px;">${{escHtml(prayer.lastPrayedAt)}}</div><div class="chr-prayer-stat-lbl">Last Prayed</div></div>` : ''}}
          </div>
          ${{prayer.answerSummary ? `<div style="background:rgba(62,207,142,0.08);border:1px solid rgba(62,207,142,0.20);border-radius:8px;padding:12px;font-size:12px;color:var(--text-2);margin-bottom:12px;">✓ ${{escHtml(prayer.answerSummary)}}</div>` : ''}}
          <div id="chr-prayer-notes" style="margin-top:8px;">
            <label style="font-size:11px;color:var(--text-3);display:block;margin-bottom:6px;">Add a note</label>
            <textarea id="chr-prayer-note-input" class="chr-chat-input" style="width:100%;height:80px;" placeholder="Record what happened, what you prayed, an answer…"></textarea>
          </div>
        </div>
        <div class="chr-modal-footer">
          <button class="btn btn-hue btn-sm" onclick="markPrayedChronicle('${{escHtml(prayer.id)}}', ${{prayed}})">🙏 Mark Prayed</button>
          ${{!isAnswered ? `<button class="btn btn-sm" style="background:rgba(62,207,142,0.15);color:#3ecf8e;" onclick="markAnsweredChronicle('${{escHtml(prayer.id)}}')">✓ Answered</button>` : ''}}
          <button class="btn btn-sm" style="margin-left:auto;" onclick="closeChrModal('chr-prayer-modal')">Close</button>
        </div>
      </div>
    </div>`;
  document.body.insertAdjacentHTML('beforeend', html);
}}

// ── Bible Study Modal — Faith Council ─────────────────────────
let _chrStudyMessages = [];
let _chrStudyAgent = 'ezra';

const _CHR_STUDY_ROSTER = [
  {{id:'ezra',    name:'Ezra',              initials:'EZ', color:'#C9A84C', title:'The Scribe'}},
  {{id:'david',   name:'David',             initials:'DV', color:'#8B5CF6', title:'The Psalmist'}},
  {{id:'solomon', name:'Solomon',           initials:'SL', color:'#10B981', title:'The Sage'}},
  {{id:'timothy', name:'Timothy',           initials:'TM', color:'#60A5FA', title:'The Shepherd'}},
  {{id:'corey',   name:'Corey Russell',     initials:'CR', color:'#F97316', title:'The Intercessor'}},
  {{id:'paul',    name:'Paul',              initials:'PA', color:'#EF4444', title:'The Apostle'}},
  {{id:'amos',    name:'Amos Yong',         initials:'AY', color:'#38BDF8', title:'The Theologian'}},
  {{id:'thomas',  name:'Thomas à Kempis',   initials:'TK', color:'#94A3B8', title:'The Contemplative'}},
  {{id:'wallace', name:'J. Warner Wallace', initials:'JW', color:'#3B82F6', title:'The Detective'}},
  {{id:'mcdowell',name:'Josh McDowell',     initials:'JM', color:'#F59E0B', title:'The Advocate'}},
  {{id:'graham',  name:'Billy Graham',      initials:'BG', color:'#FDE68A', title:'The Evangelist'}},
  {{id:'stanley', name:'Andy Stanley',      initials:'AS', color:'#84CC16', title:'The Communicator'}},
  {{id:'furtick', name:'Steven Furtick',    initials:'SF', color:'#EC4899', title:'The Preacher'}},
  {{id:'cahn',    name:'Jonathan Cahn',     initials:'JC', color:'#6366F1', title:'The Harbinger'}},
  {{id:'strobel', name:'Lee Strobel',       initials:'LS', color:'#0E7490', title:'The Investigator'}},
  {{id:'heiser',  name:'Michael Heiser',    initials:'MH', color:'#C084FC', title:'The Scholar'}},
];

function openBibleStudyModal(passage) {{
  _chrStudyMessages = [];
  const defaultPassage = passage || '';
  const roster = (_faithAgents && _faithAgents.length) ? _faithAgents : _CHR_STUDY_ROSTER;
  const activeAgent = roster.find(a => a.id === _chrStudyAgent) || roster[0];

  const agentPills = roster.map(a => `
    <button class="chr-agent-pill${{a.id === _chrStudyAgent ? ' active' : ''}}"
            data-agent="${{a.id}}"
            style="--pill-color:${{a.color}}"
            onclick="switchStudyAgent(this,'${{a.id}}')">
      <span class="chr-agent-pill-av" style="background:${{a.color}}">${{a.initials}}</span>
      ${{a.name}}
    </button>`).join('');

  const html = `
    <div class="chr-modal-backdrop" id="chr-study-modal" onclick="if(event.target===this)closeChrModal('chr-study-modal')">
      <div class="chr-modal chr-modal-wide" style="max-height:90vh;">
        <div class="chr-modal-header" style="padding-bottom:0;border-bottom:none;gap:10px;">
          <span class="chr-modal-title">✦ Bible Study</span>
          <input id="chr-study-passage" value="${{defaultPassage}}"
            style="font-size:12px;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:5px 10px;color:var(--text-1);width:160px;"
            placeholder="Passage (e.g. John 1:14)…">
          <button class="chr-modal-close" onclick="closeChrModal('chr-study-modal')">✕</button>
        </div>
        <div class="chr-agent-strip" id="chr-agent-strip">${{agentPills}}</div>
        <div class="chr-agent-label" id="chr-agent-label" style="border-color:${{activeAgent.color}}">
          <span class="chr-agent-pill-av" style="background:${{activeAgent.color}};width:22px;height:22px;font-size:9px;">${{activeAgent.initials}}</span>
          <span style="font-size:12px;font-weight:600;color:var(--text-1);">${{activeAgent.name}}</span>
          <span style="font-size:11px;color:var(--text-3);">— ${{activeAgent.title}}</span>
        </div>
        <div class="chr-modal-body" style="display:flex;flex-direction:column;gap:0;padding:14px 20px;">
          <div class="chr-chat-messages" id="chr-study-messages">
            <div style="text-align:center;color:var(--text-3);font-size:12px;padding:20px 0;">
              Choose your guide above, enter a passage, and begin.
            </div>
          </div>
          <div class="chr-chat-input-row">
            <textarea id="chr-study-input" class="chr-chat-input" rows="1"
              placeholder="Ask anything…"
              onkeydown="if(event.key==='Enter'&&!event.shiftKey){{event.preventDefault();chrStudySend();}}"
              oninput="this.style.height='auto';this.style.height=this.scrollHeight+'px'"></textarea>
            <button class="btn btn-hue btn-sm" onclick="chrStudySend()" id="chr-study-send-btn" style="height:38px;padding:0 14px;">Send</button>
          </div>
        </div>
        <div class="chr-modal-footer">
          <button class="btn btn-sm" onclick="chrStudySaveEntry()" style="font-size:11px;">💾 Save to Chronicle</button>
          <span style="font-size:10px;color:var(--text-3);margin-left:4px;">Saves this session as a Chronicle study entry</span>
          <button class="btn btn-sm" style="margin-left:auto;" onclick="closeChrModal('chr-study-modal')">Close</button>
        </div>
      </div>
    </div>`;
  document.body.insertAdjacentHTML('beforeend', html);
  document.getElementById('chr-study-input').focus();
}}

function switchStudyAgent(btn, agentId) {{
  _chrStudyAgent = agentId;
  _chrStudyMessages = [];
  document.querySelectorAll('.chr-agent-pill').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  const roster = (_faithAgents && _faithAgents.length) ? _faithAgents : _CHR_STUDY_ROSTER;
  const agent = roster.find(a => a.id === agentId) || {{name:agentId, initials:agentId.slice(0,2).toUpperCase(), title:'', color:'var(--hue)'}};
  const label = document.getElementById('chr-agent-label');
  if (label) {{
    label.style.borderColor = agent.color;
    label.innerHTML = `
      <span class="chr-agent-pill-av" style="background:${{agent.color}};width:22px;height:22px;font-size:9px;">${{agent.initials}}</span>
      <span style="font-size:12px;font-weight:600;color:var(--text-1);">${{agent.name}}</span>
      <span style="font-size:11px;color:var(--text-3);">— ${{agent.title}}</span>`;
  }}
  const msgs = document.getElementById('chr-study-messages');
  if (msgs) msgs.innerHTML = `<div style="text-align:center;color:var(--text-3);font-size:12px;padding:20px 0;">
    Now speaking with ${{agent.name}}. Enter a passage and ask anything.
  </div>`;
}}

async function chrStudySend() {{
  const input = document.getElementById('chr-study-input');
  const passageEl = document.getElementById('chr-study-passage');
  const text = (input?.value || '').trim();
  if (!text) return;
  const passage = passageEl?.value?.trim() || '';

  const btn = document.getElementById('chr-study-send-btn');
  if (btn) btn.disabled = true;
  if (input) {{ input.disabled = true; }}

  _chrStudyMessages.push({{role:'user', text}});
  input.value = '';
  input.style.height = 'auto';
  chrRenderMessages();

  const msgs = document.getElementById('chr-study-messages');
  const typing = document.createElement('div');
  typing.className = 'chr-chat-msg';
  typing.id = 'chr-typing';
  typing.innerHTML = `<div class="chr-chat-avatar">✦</div><div class="chr-chat-bubble"><span class="chr-typing-dot"></span><span class="chr-typing-dot"></span><span class="chr-typing-dot"></span></div>`;
  msgs?.appendChild(typing);
  msgs?.scrollTo(0, msgs.scrollHeight);

  try {{
    const res = await fetch('/api/faith/chat', {{
      method: 'POST',
      headers: {{'Content-Type':'application/json'}},
      body: JSON.stringify({{
        agent_id: _chrStudyAgent,
        passage,
        messages: _chrStudyMessages.map(m => ({{role: m.role === 'user' ? 'user' : 'assistant', content: m.text}})),
      }})
    }});
    const data = await res.json();
    const reply = data.reply || data.detail || 'No response.';
    _chrStudyMessages.push({{role:'assistant', text: reply}});
  }} catch(e) {{
    _chrStudyMessages.push({{role:'assistant', text:'Faith agent unavailable right now.'}});
  }}

  document.getElementById('chr-typing')?.remove();
  chrRenderMessages();
  if (btn) btn.disabled = false;
  if (input) {{ input.disabled = false; input.focus(); }}
}}

function chrRenderMessages() {{
  const msgs = document.getElementById('chr-study-messages');
  if (!msgs) return;
  if (_chrStudyMessages.length === 0) return;
  msgs.innerHTML = _chrStudyMessages.map(m => {{
    const isUser = m.role === 'user';
    const bubble = isUser
      ? `<div class="chr-chat-bubble user">${{escHtml(m.text)}}</div>`
      : `<div class="chr-chat-bubble">${{chrMarkdownToHtml(m.text)}}</div>`;
    const avatar = isUser ? '👤' : '✦';
    return `<div class="chr-chat-msg ${{isUser?'user':''}}">${{isUser?'':('<div class="chr-chat-avatar">'+avatar+'</div>')}}${{bubble}}${{isUser?('<div class="chr-chat-avatar">'+avatar+'</div>'):''}}
    </div>`;
  }}).join('');
  msgs.scrollTo(0, msgs.scrollHeight);
}}

function chrMarkdownToHtml(md) {{
  // Minimal markdown: **bold**, ### headings, bullets
  return md
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/\\*\\*(.+?)\\*\\*/g,'<strong>$1</strong>')
    .replace(/^###\\s+(.+)$/gm,'<h3>$1</h3>')
    .replace(/^##\\s+(.+)$/gm,'<h3>$1</h3>')
    .replace(/^#\\s+(.+)$/gm,'<h3>$1</h3>')
    .replace(/^\\*\\s+(.+)$/gm,'<li>$1</li>')
    .replace(/^-\\s+(.+)$/gm,'<li>$1</li>')
    .replace(/(<li>.*<\\/li>\\n?)+/g, s => '<ul>'+s+'</ul>')
    .replace(/\\n\\n+/g,'</p><p>')
    .replace(/^(?!<[hul])(.+)$/gm,'$1')
    .replace(/\\n/g,'<br>');
}}

async function chrStudySaveEntry() {{
  if (_chrStudyMessages.length === 0) {{ alert('No conversation to save yet.'); return; }}
  const passage = document.getElementById('chr-study-passage')?.value || 'Psalm 23';
  const body = _chrStudyMessages.map(m => (m.role==='user'?'You: ':'Chronicle AI: ') + m.text).join('\\n\\n');
  const entry = {{
    id: 'jarvis-study-' + Date.now(),
    date: new Date().toISOString().slice(0,10),
    type: 'study',
    title: `Bible Study — ${{passage}}`,
    body: body.slice(0, 2000),
    passage,
    themes: ['Study'],
    autoCapture: false,
  }};
  await saveEntryToChronicle(entry);
}}

// ── Shared write-back helpers ──────────────────────────────────
async function saveEntryToChronicle(entry) {{
  try {{
    const res = await fetch('/api/chronicle/write-entry', {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{entry}})
    }});
    const data = await res.json();
    if (data.ok) {{
      showToast('Saved to Chronicle ✓', 'success');
      // Refresh Chronicle view if active
      if (document.getElementById('view-chronicle')?.classList.contains('active')) loadChronicle();
    }} else {{
      showToast('Failed to save to Chronicle', 'warning');
    }}
  }} catch(e) {{
    showToast('Chronicle unavailable', 'warning');
  }}
}}

async function markPrayedChronicle(prayerId, currentCount) {{
  const note = document.getElementById('chr-prayer-note-input')?.value.trim() || '';
  const today = new Date().toISOString().slice(0,10);
  try {{
    const res = await fetch('/api/chronicle/update-prayer', {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{
        id: prayerId,
        timesPrayed: (currentCount || 0) + 1,
        lastPrayedAt: today,
      }})
    }});
    const data = await res.json();
    if (data.ok) {{
      showToast('Prayer recorded ✓', 'success');
      closeChrModal('chr-prayer-modal');
      if (note) {{
        // Save a note entry too
        await saveEntryToChronicle({{
          id: 'jarvis-prayer-note-' + Date.now(),
          date: today, type: 'prayer', title: 'Prayer note',
          body: note, themes: ['Prayer'], autoCapture: false,
        }});
      }}
      loadChronicle();
    }}
  }} catch(e) {{ showToast('Chronicle unavailable','warning'); }}
}}

async function markAnsweredChronicle(prayerId) {{
  const note = document.getElementById('chr-prayer-note-input')?.value.trim() || '';
  const today = new Date().toISOString().slice(0,10);
  try {{
    const res = await fetch('/api/chronicle/update-prayer', {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{
        id: prayerId, answered: true,
        dateAnswered: today,
        answerSummary: note || 'Marked answered.',
      }})
    }});
    const data = await res.json();
    if (data.ok) {{
      showToast('Prayer marked answered ✓ 🙌', 'success');
      closeChrModal('chr-prayer-modal');
      loadChronicle();
    }}
  }} catch(e) {{ showToast('Chronicle unavailable','warning'); }}
}}

function closeChrModal(id) {{
  const el = document.getElementById(id);
  if (el) el.remove();
}}

function renderChronicle(data) {{
  if (!data) return;

  const entries  = data.entries || [];
  const prayers  = data.prayer_items || [];
  const rhythms  = data.formation_rhythms || [];
  const tags     = data.tags || [];

  // ── Stats ────────────────────────────────────────────────────
  const _set = (id, v) => {{ const el = document.getElementById(id); if (el) el.textContent = v; }};
  _set('chronicle-total',      data.total ?? entries.length);
  _set('chr-active-prayers',   data.active_prayers ?? '—');
  _set('chr-answered-prayers', data.answered_prayers ?? '—');
  _set('chr-rhythms-count',    rhythms.length || '—');

  // ── Entry feed ────────────────────────────────────────────────
  const TYPE_LABELS = {{
    insight: 'Insight', prayer: 'Prayer', study: 'Study',
    reflection: 'Reflection', note: 'Note',
  }};
  const list = document.getElementById('chronicle-list');
  if (list) {{
    if (entries.length === 0) {{
      list.innerHTML = `<div class="chr-entry-card" style="text-align:center;color:var(--text-3);padding:32px;">
        No entries found.${{data.chronicle_available === false ? ' Chronicle snapshot not found.' : ''}}
      </div>`;
    }} else {{
      list.innerHTML = entries.map(e => {{
        const typeClass = 'chr-type-' + (e.type || 'note');
        const typeLbl   = TYPE_LABELS[e.type] || e.type || 'Note';
        const themes    = (e.themes || []).map(t => `<span class="chr-theme-tag">${{escHtml(t)}}</span>`).join('');
        const passage   = e.passage ? `<span class="chr-passage">${{escHtml(e.passage)}}</span>` : '';
        return `<div class="chr-entry-card ${{typeClass}}" onclick="openEntryModal(${{JSON.stringify(e).replace(/\'/g,'&apos;')}})" style="cursor:pointer;">
          <div class="chr-entry-type-bar"></div>
          <div class="chr-entry-header">
            <span class="chr-entry-type-pill">${{escHtml(typeLbl)}}</span>
            <span class="chr-entry-title">${{escHtml(e.title || '—')}}</span>
            <span class="chr-entry-date">${{escHtml(e.date || '')}}</span>
          </div>
          ${{e.body ? `<div class="chr-entry-body">${{escHtml(e.body)}}</div>` : ''}}
          ${{(passage || themes) ? `<div class="chr-entry-footer">${{passage}}${{themes}}</div>` : ''}}
        </div>`;
      }}).join('');
    }}
  }}

  // ── Prayer list ───────────────────────────────────────────────
  const prayerEl = document.getElementById('chr-prayer-list');
  if (prayerEl) {{
    if (prayers.length === 0) {{
      prayerEl.innerHTML = '<div style="padding:14px 16px;color:var(--text-3);font-size:12px;">No prayer items.</div>';
    }} else {{
      // Active first, then answered
      const sorted = [...prayers].sort((a, b) => (a.answered ? 1 : 0) - (b.answered ? 1 : 0));
      prayerEl.innerHTML = sorted.map(p => {{
        const catClass = 'chr-cat-' + (p.category || 'needs');
        const answered = p.answered ? 'chr-prayer-answered' : '';
        const count    = p.timesPrayed ? `${{p.timesPrayed}}×` : '';
        return `<div class="chr-prayer-item" onclick="openPrayerModal(${{JSON.stringify(p).replace(/\'/g,'&apos;')}})" style="cursor:pointer;">
          <span class="chr-prayer-cat ${{catClass}}">${{escHtml(p.category || '—')}}</span>
          <span class="chr-prayer-text ${{answered}}">${{escHtml(p.text || '—')}}</span>
          ${{count ? `<span class="chr-prayer-count">${{escHtml(count)}}</span>` : ''}}
        </div>`;
      }}).join('');
    }}
  }}

  // ── Formation rhythms ─────────────────────────────────────────
  const rhythmsEl = document.getElementById('chr-rhythms-list');
  if (rhythmsEl) {{
    if (rhythms.length === 0) {{
      rhythmsEl.innerHTML = '<div style="padding:14px 16px;color:var(--text-3);font-size:12px;">No rhythms configured.</div>';
    }} else {{
      rhythmsEl.innerHTML = rhythms.map(r => {{
        return `<div class="chr-rhythm-item">
          <div class="chr-rhythm-title">
            ${{escHtml(r.title || '—')}}
            <span class="chr-rhythm-cadence">${{escHtml(r.cadence || '')}}</span>
          </div>
          ${{r.focus ? `<div class="chr-rhythm-focus">${{escHtml(r.focus)}}</div>` : ''}}
          ${{r.relatedPassage ? `<div class="chr-rhythm-passage">${{escHtml(r.relatedPassage)}}</div>` : ''}}
        </div>`;
      }}).join('');
    }}
  }}

  // ── Tag cloud ─────────────────────────────────────────────────
  const cloud = document.getElementById('tag-cloud');
  if (cloud) {{
    if (tags.length === 0) {{
      cloud.innerHTML = '<span style="color:var(--text-3);font-size:12px;">No themes yet.</span>';
    }} else {{
      cloud.innerHTML = tags.map(t =>
        `<span class="tag-chip" onclick="searchChronicle('${{escHtml(t)}}')">${{escHtml(t)}}</span>`
      ).join('');
    }}
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
    return '<button class="forge-view-chip ' + cls + '" onclick="forgeUploadViewCapture(\\'' + v + '\\')" title="Upload ' + label + ' view">' + icon + '<span>' + escHtml(label) + '</span></button>';
  }}).join('');
  const buildBtn = document.getElementById('forge-build-3d-btn');
  if (buildBtn) {{
    const reqCaptured = [...required].filter(rv => captured.has(rv)).length;
    buildBtn.style.display = reqCaptured >= 3 ? '' : 'none';
  }}
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

async function forgeUploadViewCapture(viewType) {{
  if (!_forgeCurrentProjectId) {{ showToast('Select or create a project first.', 'warn'); return; }}
  const inp = document.getElementById('forge-view-capture-input');
  if (!inp) return;
  inp._pendingViewType = viewType;
  inp.value = '';
  inp.click();
}}

async function forgeHandleViewCaptureFiles(files, viewType) {{
  if (!_forgeCurrentProjectId) {{ showToast('Select a project first.', 'warn'); return; }}
  const arr = Array.from(files);
  if (!arr.length) return;
  const label = (viewType || 'view').replace('_reference','').replace('_',' ');
  showToast('Uploading ' + arr.length + ' ' + label + ' photo' + (arr.length > 1 ? 's' : '') + '...', 'info');
  let ok = 0, fail = 0;
  for (const file of arr) {{
    const fd = new FormData();
    fd.append('file', file);
    let uploadedFilename = null;
    try {{
      const res = await fetch('/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId) + '/upload', {{
        method: 'POST', body: fd,
      }});
      if (res.ok) {{
        const data = await res.json();
        uploadedFilename = data.filename || file.name;
        ok++;
      }} else {{ fail++; continue; }}
    }} catch(e) {{ fail++; continue; }}
    try {{
      await fetch('/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId) + '/capture-frame', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{ filename: uploadedFilename, view_type: viewType }}),
      }});
    }} catch(e) {{ /* non-fatal — frame registered on next load */ }}
  }}
  if (fail === 0) {{
    showToast(ok + ' ' + label + ' photo' + (ok > 1 ? 's' : '') + ' captured ✓', 'success');
  }} else {{
    showToast(ok + ' captured, ' + fail + ' failed', fail === arr.length ? 'error' : 'warn');
  }}
  forgeLoadProject(_forgeCurrentProjectId);
}}

async function forgeTriggerReconstruct() {{
  if (!_forgeCurrentProjectId) {{ showToast('Select a project first.', 'warn'); return; }}
  const btn = document.getElementById('forge-build-3d-btn');
  if (btn) {{ btn.disabled = true; btn.textContent = '⏳ Building...'; }}
  try {{
    const res = await fetch('/api/forge/reconstruct', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ project_id: _forgeCurrentProjectId }}),
    }});
    if (res.ok) {{
      showToast('3D reconstruction started! Check the model viewer in a few minutes.', 'success');
    }} else {{
      const err = await res.json().catch(() => ({{}}));
      showToast('Reconstruction failed: ' + (err.detail || res.status), 'error');
      if (btn) {{ btn.disabled = false; btn.textContent = '🧊 Build 3D Model'; }}
    }}
  }} catch(e) {{
    showToast('Network error: ' + e, 'error');
    if (btn) {{ btn.disabled = false; btn.textContent = '🧊 Build 3D Model'; }}
  }}
}}

// ── WoW Model Bridge ──────────────────────────────────────────

let _wowModels = [];   // cached model list from last refresh

function forgeWowToggle() {{
  const body = document.getElementById('forge-wow-body');
  if (!body) return;
  const opening = body.style.display === 'none';
  body.style.display = opening ? '' : 'none';
  if (opening) forgeWowRefresh();
}}

async function forgeWowRefresh() {{
  const statusRow  = document.getElementById('forge-wow-status-row');
  const countBadge = document.getElementById('forge-wow-count');
  const listEl     = document.getElementById('forge-wow-model-list');
  if (statusRow) statusRow.textContent = 'Refreshing…';
  try {{
    const [statusRes, modelsRes] = await Promise.all([
      fetch('/api/forge/wow/status'),
      fetch('/api/forge/wow/models'),
    ]);
    const status = statusRes.ok ? await statusRes.json() : {{}};
    const modelsData = modelsRes.ok ? await modelsRes.json() : {{}};
    // Endpoint returns {{models: [...]}} or a bare array
    const models = Array.isArray(modelsData) ? modelsData : (modelsData.models || []);
    _wowModels = models;

    // Status row
    const lines = [];
    lines.push('📁 ' + (status.export_folder || '—') +
               (status.export_folder_exists ? ' ✓' : ' ✗ (not found)'));
    if (status.wow_install_found) lines.push('🎮 WoW install found ✓');
    if (status.blender_found)     lines.push('🧊 Blender found ✓');
    if (!status.export_folder_exists) {{
      lines.push('');
      lines.push('💡 ' + (status.wow_export_setup_tip || 'Configure folder in Setup'));
    }}
    if (statusRow) statusRow.innerHTML = lines.map(l => escHtml(l)).join('<br>');
    if (countBadge) countBadge.textContent = models.length ? models.length + ' model' + (models.length !== 1 ? 's' : '') : '';

    forgeWowRenderList(_wowModels);
  }} catch(e) {{
    if (statusRow) statusRow.textContent = 'Error: ' + e;
  }}
}}

function forgeWowRenderList(models) {{
  const listEl = document.getElementById('forge-wow-model-list');
  if (!listEl) return;
  if (!models || models.length === 0) {{
    listEl.innerHTML = '<div style="font-size:11px;color:var(--text-3);padding:4px 0;">No models found. Export a character from wow.export first.</div>';
    return;
  }}
  listEl.innerHTML = models.map(m => {{
    const kb = Math.round(m.size_bytes / 1024);
    const size = kb > 1024 ? (kb/1024).toFixed(1) + ' MB' : kb + ' KB';
    return '<div style="display:flex;align-items:center;gap:6px;padding:4px 6px;border-radius:6px;background:var(--glass-1);font-size:11px;">' +
      '<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:var(--font-mono);" title="' + escHtml(m.filename) + '">' + escHtml(m.filename) + '</span>' +
      '<span style="color:var(--text-3);flex-shrink:0;">' + escHtml(size) + '</span>' +
      '<button class="forge-action-btn" style="padding:2px 8px;font-size:10px;flex-shrink:0;" ' +
        'onclick="forgeWowImport(' + JSON.stringify(m.filename) + ')">Import</button>' +
      '</div>';
  }}).join('');
}}

function forgeWowSearch(query) {{
  const q = query.trim().toLowerCase();
  const filtered = q ? _wowModels.filter(m => m.filename.toLowerCase().includes(q)) : _wowModels;
  forgeWowRenderList(filtered);
}}

async function forgeWowOpenSetup() {{
  // Load current config first
  try {{
    const res = await fetch('/api/forge/wow/config');
    const cfg = res.ok ? await res.json() : {{}};
    const f = document.getElementById('forge-wow-cfg-folder');
    const w = document.getElementById('forge-wow-cfg-wow');
    const b = document.getElementById('forge-wow-cfg-blender');
    if (f) f.value = cfg.export_folder    || '';
    if (w) w.value = cfg.wow_install_path || '';
    if (b) b.value = cfg.blender_path     || '';
  }} catch(e) {{ /* proceed with empty fields */ }}
  const modal = document.getElementById('forge-wow-setup-modal');
  if (modal) modal.classList.remove('hidden');
}}

async function forgeWowSaveConfig() {{
  const folder  = (document.getElementById('forge-wow-cfg-folder')  || {{}}).value || '';
  const wow     = (document.getElementById('forge-wow-cfg-wow')     || {{}}).value || '';
  const blender = (document.getElementById('forge-wow-cfg-blender') || {{}}).value || '';
  try {{
    const res = await fetch('/api/forge/wow/config', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ export_folder: folder, wow_install_path: wow, blender_path: blender }}),
    }});
    if (res.ok) {{
      showToast('WoW config saved ✓', 'success');
      const modal = document.getElementById('forge-wow-setup-modal');
      if (modal) modal.classList.add('hidden');
      forgeWowRefresh();
    }} else {{
      showToast('Failed to save config', 'error');
    }}
  }} catch(e) {{ showToast('Error: ' + e, 'error'); }}
}}

async function forgeWowImport(filename) {{
  if (!_forgeCurrentProjectId) {{
    showToast('Select or create a Forge project first.', 'warn');
    return;
  }}
  showToast('Importing ' + filename + '…', 'info');
  try {{
    const res = await fetch('/api/forge/wow/import', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ filename, project_id: _forgeCurrentProjectId }}),
    }});
    const data = await res.json();
    if (data.ok) {{
      showToast('Imported ' + filename + ' into project ✓', 'success');
      forgeLoadProject(_forgeCurrentProjectId);
    }} else {{
      showToast('Import failed: ' + (data.error || 'unknown error'), 'error');
    }}
  }} catch(e) {{ showToast('Network error: ' + e, 'error'); }}
}}

// ── Forge Convert ─────────────────────────────────────────────

function forgeConvertToggle() {{
  const body = document.getElementById('forge-convert-body');
  if (!body) return;
  body.style.display = body.style.display === 'none' ? '' : 'none';
  if (body.style.display !== 'none') forgeConvertPopulateFiles();
}}

function forgeConvertPopulateFiles() {{
  if (!_forgeCurrentProjectId) return;
  const selIds = ['forge-conv-src-file', 'forge-repair-src-file', 'forge-scale-src-file'];
  fetch('/api/forge/projects/' + encodeURIComponent(_forgeCurrentProjectId))
    .then(r => r.ok ? r.json() : null)
    .then(proj => {{
      if (!proj) return;
      const files3d = (proj.source_files || [])
        .filter(f => /[.](stl|obj|glb|gltf|ply)$/i.test(f.filename))
        .map(f => f.filename);
      selIds.forEach(id => {{
        const sel = document.getElementById(id);
        if (!sel) return;
        const cur = sel.value;
        sel.innerHTML = '<option value="">— pick project file —</option>' +
          files3d.map(fn =>
            '<option value="' + escHtml(fn) + '"' + (fn === cur ? ' selected' : '') + '>' + escHtml(fn) + '</option>'
          ).join('');
      }});
    }})
    .catch(() => {{}});
}}

async function forgeConvertFormat() {{
  if (!_forgeCurrentProjectId) {{ showToast('Select a project first.', 'warn'); return; }}
  const srcSel = document.getElementById('forge-conv-src-file');
  const fmtSel = document.getElementById('forge-conv-fmt');
  if (!srcSel || !srcSel.value) {{ showToast('Pick a source file first.', 'warn'); return; }}
  const fd = new FormData();
  fd.append('project_id', _forgeCurrentProjectId);
  fd.append('source_filename', srcSel.value);
  fd.append('target_format', fmtSel ? fmtSel.value : 'stl');
  showToast('Converting ' + srcSel.value + ' → ' + (fmtSel ? fmtSel.value.toUpperCase() : '') + '…', 'info');
  try {{
    const res = await fetch('/api/forge/convert/format', {{ method: 'POST', body: fd }});
    const data = await res.json();
    if (data.ok) {{
      showToast('Converted: ' + data.filename + ' ✓', 'success');
      forgeConvertPopulateFiles();
      forgeLoadProject(_forgeCurrentProjectId);
    }} else {{
      showToast('Convert failed: ' + (data.detail || data.error || 'unknown'), 'error');
    }}
  }} catch(e) {{ showToast('Network error: ' + e, 'error'); }}
}}

async function forgeConvertFormatFromUpload(input) {{
  if (!_forgeCurrentProjectId) {{ showToast('Select a project first.', 'warn'); return; }}
  const file = input.files && input.files[0];
  if (!file) return;
  const fmtSel = document.getElementById('forge-conv-fmt');
  const fd = new FormData();
  fd.append('project_id', _forgeCurrentProjectId);
  fd.append('target_format', fmtSel ? fmtSel.value : 'stl');
  fd.append('file', file);
  showToast('Uploading & converting ' + file.name + '…', 'info');
  try {{
    const res = await fetch('/api/forge/convert/format', {{ method: 'POST', body: fd }});
    const data = await res.json();
    if (data.ok) {{
      showToast('Converted: ' + data.filename + ' ✓', 'success');
      forgeConvertPopulateFiles();
      forgeLoadProject(_forgeCurrentProjectId);
    }} else {{
      showToast('Convert failed: ' + (data.detail || data.error || 'unknown'), 'error');
    }}
  }} catch(e) {{ showToast('Network error: ' + e, 'error'); }}
  input.value = '';
}}

async function forgeConvertCheckBlender() {{
  const resultDiv = document.getElementById('forge-conv-blender-result');
  if (resultDiv) {{ resultDiv.style.display = 'block'; resultDiv.textContent = 'Checking…'; }}
  try {{
    const res = await fetch('/api/forge/convert/blender-check');
    const data = await res.json();
    if (resultDiv) {{
      const lines = [];
      lines.push(data.blender_found
        ? '🧊 Blender: ' + (data.blender_version || 'found ✓')
        : '✗ Blender not found at configured path');
      lines.push(data.addon_found
        ? '✅ WoW Blender Studio: installed'
        : '⚠ WoW Blender Studio: NOT found');
      (data.details || []).slice(0, 5).forEach(d => lines.push('  ' + d));
      resultDiv.innerHTML = lines.map(l => escHtml(l)).join('<br>');
    }}
    if (!data.ok) showToast('Blender setup incomplete — see details below', 'warn');
    else showToast('Blender setup looks good ✓', 'success');
  }} catch(e) {{
    if (resultDiv) resultDiv.textContent = 'Check failed: ' + e;
    showToast('Network error: ' + e, 'error');
  }}
}}

async function forgeConvertRepair() {{
  if (!_forgeCurrentProjectId) {{ showToast('Select a project first.', 'warn'); return; }}
  const srcSel = document.getElementById('forge-repair-src-file');
  if (!srcSel || !srcSel.value) {{ showToast('Pick a source file first.', 'warn'); return; }}
  const resultDiv = document.getElementById('forge-conv-repair-result');
  if (resultDiv) {{ resultDiv.style.display = 'block'; resultDiv.textContent = 'Repairing…'; }}
  showToast('Running mesh repair on ' + srcSel.value + '…', 'info');
  try {{
    const res = await fetch('/api/forge/convert/repair', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        project_id:      _forgeCurrentProjectId,
        source_filename: srcSel.value,
        fix_normals:  !!(document.getElementById('forge-repair-normals')?.checked),
        fill_holes:   !!(document.getElementById('forge-repair-holes')?.checked),
        fix_winding:  !!(document.getElementById('forge-repair-winding')?.checked),
      }}),
    }});
    const data = await res.json();
    if (data.ok) {{
      showToast('Repair done: ' + data.filename + ' ✓', 'success');
      if (resultDiv) {{
        const wt = v => v ? '✓ watertight' : '✗ not watertight';
        resultDiv.innerHTML =
          escHtml('Ops: ' + (data.ops_applied || []).join(', ')) + '<br>' +
          escHtml('Before: ' + wt(data.was_watertight) + '  →  After: ' + wt(data.is_watertight)) + '<br>' +
          '<a href="' + escHtml(data.download_url || '') + '" download style="color:var(--hue);">⬇ Download repaired file</a>';
      }}
      forgeConvertPopulateFiles();
      forgeLoadProject(_forgeCurrentProjectId);
    }} else {{
      const msg = data.detail || data.error || 'unknown';
      showToast('Repair failed: ' + msg, 'error');
      if (resultDiv) resultDiv.textContent = 'Error: ' + msg;
    }}
  }} catch(e) {{
    showToast('Network error: ' + e, 'error');
    if (resultDiv) resultDiv.textContent = 'Network error: ' + e;
  }}
}}

function forgeConvertScaleOpChange(op) {{
  const opts = document.getElementById('forge-scale-rescale-opts');
  if (opts) opts.style.display = op === 'rescale' ? 'flex' : 'none';
}}

async function forgeConvertScale() {{
  if (!_forgeCurrentProjectId) {{ showToast('Select a project first.', 'warn'); return; }}
  const srcSel = document.getElementById('forge-scale-src-file');
  const opSel  = document.getElementById('forge-scale-op');
  if (!srcSel || !srcSel.value) {{ showToast('Pick a source file first.', 'warn'); return; }}
  const operation = opSel ? opSel.value : 'rescale';
  const resultDiv = document.getElementById('forge-conv-scale-result');
  if (resultDiv) {{ resultDiv.style.display = 'block'; resultDiv.textContent = 'Processing…'; }}
  const payload = {{
    project_id:      _forgeCurrentProjectId,
    source_filename: srcSel.value,
    operation,
    target_size:  parseFloat(document.getElementById('forge-scale-target-size')?.value  || '100'),
    target_unit:  document.getElementById('forge-scale-target-unit')?.value  || 'mm',
    current_unit: document.getElementById('forge-scale-current-unit')?.value || 'mm',
  }};
  showToast('Applying ' + operation + ' to ' + srcSel.value + '…', 'info');
  try {{
    const res = await fetch('/api/forge/convert/scale', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(payload),
    }});
    const data = await res.json();
    if (data.ok) {{
      showToast('Scale done: ' + data.filename + ' ✓', 'success');
      if (resultDiv) {{
        const fmt3 = v => Array.isArray(v) ? v.map(n => n.toFixed(2)).join(' × ') : '—';
        resultDiv.innerHTML =
          escHtml('Scale factor: ' + (data.scale_factor || 1).toFixed(6)) + '<br>' +
          escHtml('Before bbox: ' + fmt3(data.original_bbox_mm)) + '<br>' +
          escHtml('After bbox:  ' + fmt3(data.final_bbox_mm)) + '<br>' +
          '<a href="' + escHtml(data.download_url || '') + '" download style="color:var(--hue);">⬇ Download scaled file</a>';
      }}
      forgeConvertPopulateFiles();
      forgeLoadProject(_forgeCurrentProjectId);
    }} else {{
      const msg = data.detail || data.error || 'unknown';
      showToast('Scale failed: ' + msg, 'error');
      if (resultDiv) resultDiv.textContent = 'Error: ' + msg;
    }}
  }} catch(e) {{
    showToast('Network error: ' + e, 'error');
    if (resultDiv) resultDiv.textContent = 'Network error: ' + e;
  }}
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

/* ── Smart paste detection ────────────────────────────────────────────────
   When the user pastes into the command bar, detect:
   - Python/JS tracebacks → prepend "Diagnose this error:"
   - URLs → prepend "Fetch and summarize this URL:"
   - File paths → prepend "Read and summarize this file:"
─────────────────────────────────────────────────────────────────────────── */
function handleSmartPaste(e) {{
  const input = document.getElementById('cmd-input');
  if (!input) return;

  // Run detection after the paste event fills the input
  setTimeout(() => {{
    const text = input.value.trim();
    if (!text || text.length < 20) return;  // too short to classify

    // Already has a leading verb — don't double-wrap
    const looksLikeCommand = /^(what|how|why|when|who|show|list|run|build|fix|find|check|get|add|create|delete|update|help|diagnose|fetch|read|search)/i.test(text);
    if (looksLikeCommand) return;

    // Python/JS traceback
    if (/Traceback .most recent call last.|Error:|ReferenceError:|TypeError:|SyntaxError:|AttributeError:|ValueError:|KeyError:|ImportError:|ModuleNotFoundError:/.test(text)) {{
      input.value = 'Diagnose this error and fix it:\\n\\n' + text;
      return;
    }}

    // URL
    if (/^https?:[/][/]/.test(text) && !text.includes(' ')) {{
      input.value = 'Fetch and summarize this URL: ' + text;
      return;
    }}

    // Absolute file path
    if (/^[/][^ \\t\\n\\r]+[.](py|ts|tsx|js|json|md|yaml|yml|toml|txt|sh|env)$/.test(text)) {{
      input.value = 'Read this file and summarize what it does: ' + text;
      return;
    }}
  }}, 0);
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

  /* ── Slash command handling ── */
  if (text.startsWith('/')) {{
    const cmd = text.slice(1).split(' ')[0].toLowerCase();
    switch (cmd) {{
      case 'clear':
        _agentMessages = [];
        _agentConvId   = '';
        const ca = document.getElementById('chat-area');
        if (ca) ca.innerHTML = '<div class="chat-empty" id="chat-empty"><div class="chat-empty-icon">💬</div><div class="chat-empty-text">Conversation cleared — type to start fresh</div></div>';
        return;
      case 'memory':
        sendCommand('/memory — show all saved facts');
        return;
      case 'context':
        sendCommand('/context — show project context summary');
        return;
      case 'restart':
        sendCommand('Please restart the JARVIS server using the bash tool');
        return;
      case 'tools':
        sendCommand('/tools — list all available agent tools and what they do');
        return;
      case 'undo':
        sendCommand('Please undo the last file change using git checkout or git revert');
        return;
    }}
  }}

  sendCommand(text);
}}

/* ── Restart signal poller ────────────────────────────────────────────────
   Polls every 3 seconds when the agent is streaming. If the server signals a
   restart (e.g. agent wrote new code and requested a reload), the page reloads
   automatically after a short grace delay so the agent can finish its response.
─────────────────────────────────────────────────────────────────────────── */
(function _startRestartPoller() {{
  let _restartCheckTimer = null;
  let _reloadPending     = false;

  async function _checkRestart() {{
    if (_reloadPending) return;
    try {{
      const res = await fetch('/api/agent/restart-pending');
      if (!res.ok) return;
      const data = await res.json();
      if (data.pending) {{
        _reloadPending = true;
        showToast('JARVIS restarting — reloading in 3s…', 'info');
        setTimeout(() => location.reload(), 3000);
      }}
    }} catch(_) {{}}
  }}

  // Check every 5 seconds
  setInterval(_checkRestart, 5000);
}})();

/* ═══════════════════════════════════════════════════════════════
   VOICE SYSTEM — Wake Word · Auto-Send · TTS
   Say "Hey JARVIS" or click the mic to speak.
   JARVIS reads responses back when TTS is on (🔊).
═══════════════════════════════════════════════════════════════ */
let _vsr        = null;    // wake-word recognizer instance
let _vcsr       = null;    // command recognizer instance
let _vListening = false;   // currently capturing a command
let _vWakeOn    = false;   // wake-word loop is running
let _vTtsOn     = true;    // speak responses
let _vMuted     = false;   // user explicitly muted mic — blocks auto-restart

function _voiceUpdateMicBtn() {{
  const btn = document.getElementById('cmd-mic');
  if (!btn) return;
  if (_vMuted) {{
    btn.title   = 'Microphone muted — tap to unmute';
    btn.style.color       = '#ef4444';
    btn.style.opacity     = '0.55';
    btn.style.borderColor = '#ef4444';
  }} else {{
    btn.title   = 'Click to speak · Say "Hey JARVIS" to activate';
    btn.style.color       = '';
    btn.style.opacity     = '1';
    btn.style.borderColor = '';
  }}
}}

function voiceInit() {{
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const btn = document.getElementById('cmd-mic');
  if (!SR) {{
    if (btn) {{ btn.title = 'Voice not supported in this browser'; btn.style.opacity = '0.35'; }}
    return;
  }}
  // On mobile, start muted — user must tap to opt in (avoids constant iOS permission prompts)
  const isMobile = window.matchMedia('(max-width: 768px)').matches;
  if (isMobile) {{
    _vMuted = true;
    _voiceUpdateMicBtn();
    return;
  }}
  _voiceStartWake();
}}

function _voiceStartWake() {{
  if (_vMuted || _vWakeOn || _vListening) return;
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return;
  _vWakeOn = true;
  const r = new SR();
  r.continuous    = true;
  r.interimResults = true;
  r.lang          = 'en-US';
  _vsr = r;

  r.onresult = (e) => {{
    for (let i = e.resultIndex; i < e.results.length; i++) {{
      const t = e.results[i][0].transcript.toLowerCase().trim();
      if ((t.includes('hey jarvis') || t.includes('jarvis')) && !_vListening) {{
        _voiceActivate(true);
        return;
      }}
    }}
  }};
  r.onend   = () => {{ _vWakeOn = false; if (!_vListening && !_vMuted) setTimeout(_voiceStartWake, 800); }};
  r.onerror = () => {{ _vWakeOn = false; if (!_vMuted) setTimeout(_voiceStartWake, 2000); }};
  try {{ r.start(); }} catch(e) {{ _vWakeOn = false; }}
}}

function _voiceActivate(fromWake, isSecondChance) {{
  if (_vListening || _vMuted) return;
  if (_vsr) {{ try {{ _vsr.stop(); }} catch(e) {{}} }}
  _vWakeOn    = false;
  _vListening = true;

  const btn = document.getElementById('cmd-mic');
  if (btn) {{ btn.style.color = '#ef4444'; btn.style.borderColor = '#ef4444'; btn.style.opacity = '1'; btn.style.boxShadow = '0 0 0 3px rgba(239,68,68,0.25)'; }}
  if (fromWake && !isSecondChance) showToast('Hey JARVIS — listening…', 'info');

  const SR  = window.SpeechRecognition || window.webkitSpeechRecognition;
  const r   = new SR();
  r.continuous    = false;
  r.interimResults = true;
  r.lang          = 'en-US';
  _vcsr = r;

  r.onresult = (e) => {{
    let interim = '', final = '';
    for (let i = 0; i < e.results.length; i++) {{
      if (e.results[i].isFinal) final += e.results[i][0].transcript;
      else interim += e.results[i][0].transcript;
    }}
    const inp = document.getElementById('cmd-input');
    if (inp) inp.value = final || interim;
  }};

  r.onend = () => {{
    _vListening = false;
    if (btn) {{ btn.style.color = ''; btn.style.borderColor = ''; btn.style.boxShadow = ''; btn.style.opacity = '1'; }} _voiceUpdateMicBtn();
    const inp   = document.getElementById('cmd-input');
    const spoke = inp && inp.value.trim();
    if (spoke) {{
      // User said something — send it
      setTimeout(sendCmd, 150);
      setTimeout(_voiceStartWake, 400);
    }} else if (fromWake && !isSecondChance) {{
      // Wake word fired but nothing was said — greet & give one more chance
      _voiceGreetAndListen();
    }} else {{
      // Second silence or manual mic — go idle quietly
      setTimeout(_voiceStartWake, 400);
    }}
  }};

  r.onerror = () => {{
    _vListening = false;
    if (btn) {{ btn.style.color = ''; btn.style.borderColor = ''; btn.style.boxShadow = ''; btn.style.opacity = '1'; }} _voiceUpdateMicBtn();
    setTimeout(_voiceStartWake, 600);
  }};

  try {{ r.start(); }} catch(e) {{ _vListening = false; setTimeout(_voiceStartWake, 600); }}
}}

/* Pick a time-aware greeting and speak it, then re-listen once */
async function _voiceGreetAndListen() {{
  const h = new Date().getHours();
  let greetings;
  if (h < 12) {{
    greetings = [
      "Good morning. What can I do for you?",
      "Morning. Ready when you are.",
      "Good morning, sir. Go ahead.",
    ];
  }} else if (h < 17) {{
    greetings = [
      "Good afternoon. How can I help?",
      "At your service. What do you need?",
      "Standing by. Go ahead.",
    ];
  }} else {{
    greetings = [
      "Good evening. How can I assist?",
      "Evening. What's on your mind?",
      "At your service. Go ahead.",
    ];
  }}
  const line = greetings[Math.floor(Math.random() * greetings.length)];
  await voiceSpeak(line);
  // Give a short pause after audio ends, then open mic for second chance
  setTimeout(() => _voiceActivate(true, true), 400);
}}

function toggleMic() {{
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {{ showToast('Voice not supported in this browser', 'info'); return; }}

  if (_vMuted) {{
    // UNMUTE — restart wake-word listener
    _vMuted = false;
    _voiceUpdateMicBtn();
    _voiceStartWake();
    showToast('🎤 Microphone on', 'info');
  }} else if (_vListening) {{
    // Stop active command capture
    if (_vcsr) {{ try {{ _vcsr.stop(); }} catch(e) {{}} _vcsr = null; }}
    _vListening = false;
    _voiceUpdateMicBtn();
  }} else {{
    // MUTE — kill both wake-word AND command listeners entirely
    _vMuted = true;
    if (_vcsr) {{ try {{ _vcsr.stop(); }} catch(e) {{}} _vcsr = null; }}
    if (_vsr)  {{ try {{ _vsr.stop();  }} catch(e) {{}} _vsr  = null; }}
    _vListening = false;
    _vWakeOn    = false;
    _voiceUpdateMicBtn();
    showToast('🔇 Microphone off', 'info');
  }}
}}

function voiceToggleTts() {{
  _vTtsOn = !_vTtsOn;
  const btn = document.getElementById('cmd-tts');
  if (btn) {{
    btn.textContent = _vTtsOn ? '🔊' : '🔇';
    btn.title = _vTtsOn ? 'TTS on — click to mute' : 'TTS off — click to unmute';
    btn.style.opacity = _vTtsOn ? '1' : '0.4';
  }}
  if (!_vTtsOn) speechSynthesis.cancel();
  showToast(_vTtsOn ? 'JARVIS will speak responses' : 'Spoken responses muted', 'info');
}}

let _vAudio = null;
async function voiceSpeak(text) {{
  if (!_vTtsOn || !text) return;
  const clean = text.replace(/[*_`#~]/g, '').replace(/\\n+/g, ' ').trim().slice(0, 800);
  if (!clean) return;
  // Stop any currently playing audio
  if (_vAudio) {{ try {{ _vAudio.pause(); _vAudio = null; }} catch(_) {{}} }}
  // Returns a Promise that resolves when audio FINISHES (callers can await full playback)
  return new Promise(async (resolve) => {{
    try {{
      const res = await fetch('/api/tts', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{text: clean}})
      }});
      if (!res.ok) throw new Error('tts ' + res.status);
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      _vAudio = new Audio(url);
      _vAudio.onended = () => {{ URL.revokeObjectURL(url); _vAudio = null; resolve(); }};
      _vAudio.onerror = () => {{ _vAudio = null; resolve(); }};
      await _vAudio.play();
    }} catch(e) {{
      console.warn('ElevenLabs TTS failed, falling back:', e);
      if ('speechSynthesis' in window) {{
        speechSynthesis.cancel();
        const utt = new SpeechSynthesisUtterance(clean);
        utt.rate = 1.0; utt.pitch = 1.0; utt.volume = 1.0;
        utt.onend = () => resolve();
        utt.onerror = () => resolve();
        speechSynthesis.speak(utt);
      }} else {{
        resolve();
      }}
    }}
  }});
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
    case 'approvals_update':
      renderApprovals(pkt.data);
      if (currentView === 'notifications') loadNotificationCenter();
      break;
    case 'apple.focus':
    case 'apple.sound_alert':
    case 'apple.vision_scan':
    case 'apple.now_playing':
      if (currentView === 'notifications') loadNotificationCenter();
      break;
    case 'status_update':     renderStatus(pkt.data);      break;
    case 'briefing_update':   renderBriefing(pkt.data);    break;
    case 'toast':             showToast(pkt.message, pkt.level || 'info'); break;
    case 'layout.mode_changed': if (currentView === 'overview') loadLayoutState(); break;
    case 'layout.alert':
      if (currentView === 'notifications') loadNotificationCenter();
      if (currentView === 'overview') {{
        // Patch the live alert state and re-render banner + pulse rings in-place
        // without a full layout reload (cards don't move, just the banner updates)
        if (_layoutState) {{
          _layoutState.alerts = pkt.alerts || [];
          applyAlertBanner(_layoutState.alerts);
          // Re-apply pulse rings: clear old ones, set new
          document.querySelectorAll('[data-card]').forEach(el => {{
            el.classList.remove('alert-pulse-amber','alert-pulse-red','alert-pulse-blue');
          }});
          (_layoutState.alerts || []).forEach(a => {{
            const el = document.querySelector(`[data-card="${{a.card}}"]`);
            if (el) el.classList.add('alert-pulse-' + a.level);
          }});
        }}
        // If a new alert appeared, show a toast too
        if (pkt.alerts && pkt.alerts.length > 0) {{
          const top = pkt.alerts[0];
          showToast(top.message || 'Heads up', top.level === 'red' ? 'error' : 'warning');
        }}
      }} else if (pkt.alerts && pkt.alerts.some(a => a.level === 'red' || a.level === 'amber')) {{
        const top = pkt.alerts.find(a => a.level === 'red') || pkt.alerts[0];
        showToast(top.message || 'Action needed', top.level === 'red' ? 'error' : 'warning');
      }}
      break;
    case 'wi.daily_briefing.ready':
      if (currentView === 'catalyst') {{
        _wiBriefingData = null;
        if (_wiCurrentTab === 'briefing') wiLoadBriefing();
        showToast('Daily briefing ready 📋', 'info');
      }}
      break;
    case 'wi.email_sweep.completed':
      if (currentView === 'catalyst') {{
        wiLoadSummary();
        if (_wiCurrentTab === 'signals') wiLoadSignals();
      }}
      break;
    case 'wi.meeting_prep.ready':
      if (currentView === 'catalyst') {{
        showToast('Meeting prep ready 📅', 'info');
        if (_wiCurrentTab === 'briefing') wiLoadBriefing();
      }}
      break;
    case 'wi.commitments.updated':
      if (currentView === 'catalyst') {{
        wiLoadCommitments();
        wiLoadSummary();
        if (_wiCurrentTab === 'tasks') wiLoadTasks();
      }}
      break;
    case 'agent_roster_updated':
      // A new agent was registered from any external system — reload the roster
      if (currentView === 'agents') loadAgentRoster();
      break;
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
        if (typeof kdpLoadStatus === 'function') kdpLoadStatus();
        if (currentView === 'publishing') loadKdpView();
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
   SETTINGS — FULL-SCREEN OVERLAY
═══════════════════════════════════════════════════════════════ */
let _settingsSection = 'interface';

function closeSettings() {{
  const ov = document.getElementById('settings-overlay');
  if (ov) ov.classList.add('hidden');
}}

function closeSettingsIfOuter(e) {{
  if (e.target === document.getElementById('settings-overlay')) closeSettings();
}}

function openSettings() {{
  const ov = document.getElementById('settings-overlay');
  if (ov) ov.classList.remove('hidden');
  settingsNavTo(_settingsSection);
}}

function settingsNavTo(section) {{
  _settingsSection = section;
  // update pill active states
  document.querySelectorAll('.settings-nav-pill').forEach(p => {{
    p.classList.toggle('active', p.dataset.section === section);
  }});
  settingsLoadSection(section);
}}

async function settingsLoadSection(section) {{
  const container = document.getElementById('settings-section-content');
  if (!container) return;
  container.innerHTML = '<div style="color:var(--text-3);font-size:13px;padding:20px 0;">Loading…</div>';

  try {{
    if (section === 'interface') {{ container.innerHTML = settingsBuildInterface(); }}
    else if (section === 'accounts') {{ container.innerHTML = await settingsBuildAccounts(); setTimeout(kdpLoadStatus, 100); }}
    else if (section === 'voice')    {{ container.innerHTML = await settingsBuildVoice(); }}
    else if (section === 'location') {{ container.innerHTML = await settingsBuildLocation(); }}
    else if (section === 'family')   {{ container.innerHTML = await settingsBuildFamily(); }}
    else if (section === 'devices')  {{ container.innerHTML = await settingsBuildDevices(); }}
    else if (section === 'costs')    {{ container.innerHTML = await settingsBuildCosts(); }}
    else {{ container.innerHTML = '<p style="color:var(--text-3);">Unknown section.</p>'; }}
  }} catch(err) {{
    container.innerHTML = '<p style="color:#f87171;font-size:12px;">Error loading section: ' + escHtml(err.message) + '</p>';
  }}
}}

/* ── Interface ─────────────────────────────────────────────── */
function settingsBuildInterface() {{
  return `
    <p class="sset-section-hdr">Interface Theme</p>
    <div class="theme-cards" style="margin-bottom:20px;">
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
    <div class="sset-divider"></div>
    <p style="font-size:12px;color:var(--text-3);margin:12px 0 4px;">
      JARVIS Glass — Adaptive Chromatic Interface<br>
      Version 3.0 &nbsp;·&nbsp; S.H.I.E.L.D. Clearance Level 6
    </p>
    <p style="font-size:12px;color:var(--text-3);margin:20px 0 4px;font-family:var(--font-mono);letter-spacing:0.04em;text-transform:uppercase;">Session</p>
    <div style="font-size:12px;color:var(--text-2);display:flex;align-items:center;gap:8px;">
      <span id="settings-cf-identity">Loading…</span>
    </div>
    <div class="sset-divider"></div>
    <p class="sset-section-hdr">My Profile</p>
    <div class="sset-card" id="profile-settings-card">
      <div id="profile-identity-row" style="font-size:12px;color:var(--text-2);margin-bottom:12px;">Loading…</div>
      <div class="sset-row">
        <div class="sset-label">Preferred Name</div>
        <input id="profile-greeting-name" type="text" placeholder="How JARVIS addresses you" class="sset-select" style="flex:1;">
      </div>
      <div class="sset-row">
        <div class="sset-label">Theme</div>
        <select id="profile-theme" class="sset-select" style="flex:1;">
          <option value="glass">Glass — Surgical · Adaptive</option>
          <option value="classic">Classic — Dark Navy · Arc Blue</option>
          <option value="nexus">Nexus — Obsidian · Violet</option>
        </select>
      </div>
      <div class="sset-row">
        <div class="sset-label">Timezone</div>
        <select id="profile-timezone" class="sset-select" style="flex:1;">
          <option value="America/New_York">Eastern</option>
          <option value="America/Chicago">Central</option>
          <option value="America/Denver">Mountain</option>
          <option value="America/Los_Angeles">Pacific</option>
        </select>
      </div>
      <div class="sset-row" style="align-items:flex-start;">
        <div class="sset-label" style="padding-top:4px;">Dashboard Cards</div>
        <div style="display:flex;flex-direction:column;gap:6px;flex:1;">
          <label style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text-2);cursor:pointer;">
            <input type="checkbox" id="profile-show-health" style="accent-color:var(--accent);"> Health
          </label>
          <label style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text-2);cursor:pointer;">
            <input type="checkbox" id="profile-show-chronicle"> Chronicle / Faith
          </label>
          <label style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text-2);cursor:pointer;">
            <input type="checkbox" id="profile-show-dining"> Dining
          </label>
          <label style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text-2);cursor:pointer;">
            <input type="checkbox" id="profile-show-publishing"> Publishing / KDP
          </label>
          <label style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text-2);cursor:pointer;">
            <input type="checkbox" id="profile-show-finance"> Finance
          </label>
        </div>
      </div>
      <div style="margin-top:12px;display:flex;gap:8px;">
        <button class="sset-btn sset-btn-accent" onclick="profileSaveSettings()">Save My Settings</button>
      </div>
      <div id="profile-settings-msg" class="sset-msg"></div>
    </div>
  `;
  // Populate CF identity and profile after render
  (async () => {{
    try {{
      const me = _cfIdentity || await fetch('/api/identity/me').then(r=>r.json());
      const el = document.getElementById('settings-cf-identity');
      if (el) {{
        el.innerHTML = me.authenticated_via_cloudflare
          ? `<span style="color:#4ade80;">✓</span> Signed in as <strong>${{me.display_name}}</strong> <span style="color:var(--text-3);">(${{me.email}})</span>`
          : `<span style="color:var(--text-3);">Local session · </span><strong>${{me.display_name}}</strong>`;
      }}
    }} catch(e) {{}}
    // Load profile into My Profile form
    try {{
      const p = _userProfile || await fetch('/api/profile').then(r=>r.json());
      const idRow = document.getElementById('profile-identity-row');
      if (idRow) {{
        const name = _cfIdentity?.display_name || 'Unknown';
        const via = _cfIdentity?.authenticated_via_cloudflare ? ' · via Cloudflare' : ' · local session';
        idRow.innerHTML = `Signed in as <strong>${{name}}</strong><span style="color:var(--text-3);">${{via}}</span>`;
      }}
      if (p.greeting_name) {{ const el = document.getElementById('profile-greeting-name'); if(el) el.value = p.greeting_name; }}
      if (p.theme) {{ const el = document.getElementById('profile-theme'); if(el) el.value = p.theme; }}
      if (p.timezone) {{ const el = document.getElementById('profile-timezone'); if(el) el.value = p.timezone; }}
      const dash = p.dashboard || {{}};
      const checks = [['show-health','show_health'],['show-chronicle','show_chronicle'],['show-dining','show_dining'],['show-publishing','show_publishing'],['show-finance','show_finance']];
      checks.forEach(([domId, key]) => {{
        const el = document.getElementById('profile-' + domId);
        if (el) el.checked = dash[key] !== false;
      }});
    }} catch(e) {{}}
  }})();
}}

/* ── Accounts ──────────────────────────────────────────────── */
async function settingsBuildAccounts() {{
  // Fetch data in parallel
  let googleStatus = {{}}, accounts = [];
  try {{
    const r = await fetch('/api/google/client-secret');
    googleStatus = await r.json();
  }} catch(e) {{ googleStatus = {{error: true}}; }}
  try {{
    const r = await fetch('/api/accounts');
    const d = await r.json();
    accounts = d.accounts || [];
  }} catch(e) {{}}

  // Google status badge
  const gPresent = googleStatus.present;
  const gBadge = gPresent
    ? `<span class="sset-badge sset-badge-green">✓ JSON saved</span>`
    : `<span class="sset-badge sset-badge-grey">Not configured</span>`;
  const gDetail = gPresent
    ? `Type: ${{escHtml(googleStatus.client_type || '?')}} · ID: …${{escHtml(googleStatus.client_id_tail || '?')}}`
    : 'No client JSON saved yet.';

  // Personal accounts list
  const personalRows = accounts.map(a => {{
    const isConnected = a.status === 'connected' || a.auth_status === 'connected';
    const badge = isConnected
      ? `<span class="sset-badge sset-badge-green">Connected</span>`
      : `<span class="sset-badge sset-badge-grey">Planned</span>`;
    const connectBtn = isConnected
      ? ''
      : `<button class="sset-btn sset-btn-accent" onclick="settingsConnectAccount('${{escHtml(a.account_id)}}')">Connect</button>`;
    return `<div class="sset-row">
      <div class="sset-label">
        <strong style="color:var(--text-1);">${{escHtml(a.label || a.owner_display_name || a.account_id)}}</strong>
        <span style="color:var(--text-3);margin-left:6px;font-size:10px;font-family:var(--font-mono);">${{escHtml(a.provider || '')}} · ${{escHtml(a.login_hint || a.service_scope || '')}}</span>
      </div>
      ${{badge}} ${{connectBtn}}
    </div>`;
  }}).join('') || '<p style="font-size:12px;color:var(--text-3);">No accounts found.</p>';

  return `
    <p class="sset-section-hdr">Google Workspace</p>
    <div class="sset-card">
      <div class="sset-row">
        <div class="sset-label">${{gDetail}}</div>
        ${{gBadge}}
      </div>
      <textarea id="settings-google-json" class="sset-textarea" rows="4"
        placeholder="Paste your Google OAuth client JSON here (Google Cloud Console → Credentials → your Web client → Download JSON)"></textarea>
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <button class="sset-btn sset-btn-accent" onclick="settingsSaveGoogleJson()">Save Client JSON</button>
        <button id="settings-google-connect-btn" class="sset-btn" onclick="settingsConnectGoogle()">Connect Google Account</button>
      </div>
      <div id="settings-google-msg" class="sset-msg"></div>
    </div>

    <div class="sset-divider"></div>
    <p class="sset-section-hdr">Microsoft / Outlook</p>
    <div class="sset-card">
      <div class="sset-row">
        <div class="sset-label">Configure via <code style="font-family:var(--font-mono);font-size:11px;">.env</code>:
          JARVIS_MICROSOFT_CLIENT_ID, JARVIS_MICROSOFT_CLIENT_SECRET, JARVIS_MICROSOFT_TENANT_ID</div>
      </div>
      <button class="sset-btn" onclick="settingsConnectOutlook()">Connect Outlook</button>
      <div id="settings-outlook-msg" class="sset-msg"></div>
    </div>

    <div class="sset-divider"></div>
    <p class="sset-section-hdr">Personal Accounts</p>
    <div class="sset-card">
      ${{personalRows}}
    </div>

    <div class="sset-divider"></div>
    <p class="sset-section-hdr">KDP / Amazon</p>
    <div class="sset-card" id="kdp-settings-card">
      <div id="kdp-settings-status" style="font-size:12px;color:var(--text-2);margin-bottom:12px;">Checking…</div>
      <div class="sset-row">
        <div class="sset-label">Amazon Email</div>
        <input id="kdp-email" type="email" placeholder="your@amazon.com" class="sset-select" style="flex:1;">
      </div>
      <div class="sset-row">
        <div class="sset-label">Password</div>
        <input id="kdp-password" type="password" placeholder="Amazon password" class="sset-select" style="flex:1;">
      </div>
      <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">
        <button class="sset-btn sset-btn-accent" onclick="kdpSaveCredentials()">Save Credentials</button>
        <button class="sset-btn" onclick="kdpTriggerSync()">Sync Now</button>
      </div>
      <div id="kdp-settings-msg" class="sset-msg"></div>
      <div style="font-size:11px;color:var(--text-3);margin-top:8px;">Note: Requires Amazon account with KDP access. 2FA will require manual code entry on first sync.</div>
    </div>
  `;
}}

// load KDP status into the settings card
async function kdpLoadStatus() {{
  try {{
    const r = await fetch('/api/kdp/status');
    const d = await r.json();
    const el = document.getElementById('kdp-settings-status');
    if (!el) return;
    if (!d.configured) {{
      el.innerHTML = '<span style="color:var(--text-3);">Not configured — enter credentials below.</span>';
    }} else if (d.last_synced_at) {{
      const ago = Math.round((Date.now() - new Date(d.last_synced_at)) / 60000);
      el.innerHTML = `<span style="color:#4ade80;">✓ Configured</span> · ${{d.book_count || 0}} books · Last synced ${{ago < 60 ? ago + 'm ago' : Math.round(ago/60) + 'h ago'}}`;
    }} else {{
      el.innerHTML = '<span style="color:#fbbf24;">Credentials saved, never synced.</span>';
    }}
  }} catch(e) {{}}
}}

async function kdpSaveCredentials() {{
  const email = document.getElementById('kdp-email')?.value.trim();
  const password = document.getElementById('kdp-password')?.value;
  const msg = document.getElementById('kdp-settings-msg');
  if (!email || !password) {{ if (msg) msg.textContent = 'Enter both email and password.'; return; }}
  try {{
    const r = await fetch('/api/kdp/credentials', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{email, password}})
    }});
    const d = await r.json();
    if (msg) msg.textContent = d.detail || (d.ok ? 'Credentials saved.' : 'Error saving.');
    if (d.ok) {{ document.getElementById('kdp-email').value = ''; document.getElementById('kdp-password').value = ''; kdpLoadStatus(); }}
  }} catch(e) {{ if (msg) msg.textContent = 'Error: ' + e.message; }}
}}

async function kdpTriggerSync() {{
  const btn = document.getElementById('kdp-sync-btn');
  const msg = document.getElementById('kdp-settings-msg');
  if (btn) {{ btn.disabled = true; btn.textContent = '⏳ Starting…'; }}
  try {{
    const r = await fetch('/api/kdp/sync', {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: '{{}}'}});
    const d = await r.json();
    if (d.ok && d.started) {{
      if (msg) msg.textContent = '⏳ Sync running in background…';
      if (btn) btn.textContent = '⏳ Syncing…';
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

/* ── Voice ─────────────────────────────────────────────────── */
async function settingsBuildVoice() {{
  let opts = {{}}, current = {{}};
  try {{
    const [r1, r2] = await Promise.all([fetch('/api/voice-options'), fetch('/api/voice-settings')]);
    opts = await r1.json();
    current = await r2.json();
  }} catch(e) {{ opts = {{}}; }}

  const providers = opts.providers || [];
  const currentProvider = current.provider || 'elevenlabs';
  const currentVoice = current.voice_id || current.voice || '';

  const providerOptions = providers.map(p =>
    `<option value="${{p.id}}" ${{p.id === currentProvider ? 'selected' : ''}}>${{p.label || p.id}}</option>`
  ).join('') || '<option value="">No providers available</option>';

  const voiceList = opts[currentProvider] || [];
  const voiceOptions = voiceList.length
    ? voiceList.map(v => `<option value="${{v.id}}" ${{v.id === currentVoice ? 'selected' : ''}}>${{v.label || v.id}}</option>`).join('')
    : '<option value="">No voices for this provider</option>';

  return `
    <p class="sset-section-hdr">Voice Settings</p>
    <div class="sset-card">
      <div class="sset-row">
        <div class="sset-label">Provider</div>
        <select id="voice-provider" class="sset-select" onchange="settingsRefreshVoiceList(this.value)">${{providerOptions}}</select>
      </div>
      <div class="sset-row">
        <div class="sset-label">Voice / Model</div>
        <select id="voice-model" class="sset-select">${{voiceOptions}}</select>
      </div>
      <div style="margin-top:10px;">
        <button class="sset-btn sset-btn-accent" onclick="settingsSaveVoice()">Save Voice Settings</button>
      </div>
      <div id="settings-voice-msg" class="sset-msg"></div>
    </div>
  `;
}}

async function settingsRefreshVoiceList(provider) {{
  try {{
    const r = await fetch('/api/voice-options');
    const opts = await r.json();
    const voiceList = opts[provider] || [];
    const sel = document.getElementById('voice-model');
    if (!sel) return;
    sel.innerHTML = voiceList.length
      ? voiceList.map(v => `<option value="${{v.id}}">${{v.label || v.id}}</option>`).join('')
      : '<option value="">No voices for this provider</option>';
  }} catch(e) {{}}
}}

/* ── Location ──────────────────────────────────────────────── */
async function settingsBuildLocation() {{
  let locData = {{}};
  try {{
    const r = await fetch('/api/location-settings');
    locData = await r.json();
  }} catch(e) {{ locData = {{error: true}}; }}

  const locs = locData.locations || [];
  const locRows = locs.map(l => `
    <div class="sset-row">
      <div class="sset-label">
        <strong style="color:var(--text-1);">${{escHtml(l.label || 'Unnamed')}}</strong>
        <span style="color:var(--text-3);font-size:10px;font-family:var(--font-mono);display:block;">
          ${{l.lat != null ? l.lat.toFixed(4) : '?'}}, ${{l.lon != null ? l.lon.toFixed(4) : '?'}}
          ${{l.notes ? ' · ' + escHtml(l.notes) : ''}}
        </span>
      </div>
    </div>
  `).join('') || '<p style="font-size:12px;color:var(--text-3);">No saved locations.</p>';

  return `
    <p class="sset-section-hdr">Location</p>
    <div class="sset-card">
      ${{locRows}}
      <div style="margin-top:10px;">
        <button class="sset-btn" onclick="settingsUseCurrentLocation()">Use My Current Location</button>
      </div>
      <div id="settings-loc-msg" class="sset-msg"></div>
    </div>

    <div class="sset-divider"></div>
    <p class="sset-section-hdr">Add Location</p>
    <div class="sset-card">
      <div class="sset-row">
        <div class="sset-label">Label</div>
        <input id="loc-new-label" type="text" placeholder="e.g. Home" class="sset-select" style="flex:1;">
      </div>
      <div class="sset-row">
        <div class="sset-label">Address</div>
        <input id="loc-new-address" type="text" placeholder="123 Main St" class="sset-select" style="flex:1;">
      </div>
      <div class="sset-row">
        <div class="sset-label">City / State / ZIP</div>
        <div style="display:flex;gap:6px;flex:1;">
          <input id="loc-new-city" type="text" placeholder="City" class="sset-select" style="flex:2;">
          <input id="loc-new-state" type="text" placeholder="ST" class="sset-select" style="flex:1;max-width:60px;">
          <input id="loc-new-zip" type="text" placeholder="ZIP" class="sset-select" style="flex:1;max-width:80px;">
        </div>
      </div>
      <div class="sset-row">
        <div class="sset-label">Coordinates</div>
        <div style="display:flex;gap:6px;flex:1;align-items:center;">
          <input id="loc-new-lat" type="number" step="any" placeholder="Latitude" class="sset-select" style="flex:1;">
          <input id="loc-new-lon" type="number" step="any" placeholder="Longitude" class="sset-select" style="flex:1;">
          <button class="sset-btn" onclick="settingsGeocodeAddress()" title="Look up address">🔍</button>
          <button class="sset-btn" onclick="settingsGeolocateNewLocation()" title="Use GPS">📍</button>
        </div>
      </div>
      <div class="sset-row">
        <div class="sset-label">Notes</div>
        <input id="loc-new-notes" type="text" placeholder="Optional notes" class="sset-select" style="flex:1;">
      </div>
      <button class="sset-btn sset-btn-accent" onclick="settingsSaveLocation()" style="margin-top:6px;">Save Location</button>
      <div id="settings-loc-add-msg" class="sset-msg"></div>
    </div>
  `;
}}

/* ── Family ────────────────────────────────────────────────── */
async function settingsBuildFamily() {{
  const [identity, devData] = await Promise.all([
    fetch('/api/identity').then(r => r.json()).catch(() => ({{error: true}})),
    fetch('/api/connected-devices').then(r => r.json()).catch(() => ({{}})),
  ]);

  const members  = identity.members || identity.family_members || identity.users || [];
  const allDevices = devData.devices || [];
  const now = Date.now();
  const ONLINE_MS = 10 * 60 * 1000; // 10 minutes

  const EMOJI = {{chris:'👨‍💼', rebekah:'👩', caleb:'👦', anna:'👧'}};

  const rows = members.map(m => {{
    const uid = m.user_id || m.id || '';
    const memberDevs = allDevices.filter(d => d.owner_user_id === uid);
    const onlineDevs = memberDevs.filter(d => {{
      if (!d.last_seen_at) return false;
      return (now - new Date(d.last_seen_at).getTime()) < ONLINE_MS;
    }});
    const isOnline  = onlineDevs.length > 0;
    const hasDev    = memberDevs.length > 0;
    const activeDevice = onlineDevs[0] || memberDevs[0];
    const devLabel  = activeDevice ? (activeDevice.label || activeDevice.device_name || '') : '';
    const devSeen   = activeDevice && activeDevice.last_seen_at ? activeDevice.last_seen_at.slice(0,10) : '';

    const badgeClass = isOnline ? 'sset-badge-green' : (hasDev ? 'sset-badge-grey' : 'sset-badge-grey');
    const badgeLabel = isOnline ? '● Online' : (hasDev ? 'Offline' : 'No device');

    return `<div class="sset-row" style="padding:10px 0;">
      <div class="sset-label">
        <div style="display:flex;align-items:center;gap:6px;">
          <span style="font-size:16px;">${{EMOJI[uid] || '👤'}}</span>
          <strong style="color:var(--text-1);">${{escHtml(m.display_name || m.name || uid)}}</strong>
          ${{m.role ? `<span style="font-size:10px;color:var(--text-3);background:var(--surface-2);padding:1px 6px;border-radius:8px;">${{escHtml(m.role)}}</span>` : ''}}
        </div>
        ${{devLabel ? `<div style="color:var(--text-3);font-size:10px;margin-top:2px;margin-left:22px;">${{escHtml(devLabel)}}${{devSeen ? ' · ' + devSeen : ''}}</div>` : ''}}
        ${{!hasDev ? `<div style="color:var(--text-3);font-size:10px;margin-top:2px;margin-left:22px;">No device claimed yet</div>` : ''}}
      </div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:3px;">
        <span class="sset-badge ${{badgeClass}}">${{badgeLabel}}</span>
        ${{(m.permissions && m.permissions !== 'child') ? `<span style="font-size:9px;color:var(--text-3);">${{escHtml(m.permissions)}}</span>` : ''}}
      </div>
    </div>`;
  }}).join('') || `<div class="sset-row"><span style="color:var(--text-3);font-size:12px;">No family members configured.</span></div>`;

  return `
    <p class="sset-section-hdr">Family Roster</p>
    <div class="sset-card">${{rows}}</div>
    <p style="font-size:11px;color:var(--text-3);margin-top:8px;">🟢 Online = active in last 10 min &nbsp;·&nbsp; Device claimed = device registered to this person</p>
    ${{identity.error ? '<p style="font-size:11px;color:#f87171;margin-top:8px;">Could not load identity data.</p>' : ''}}
  `;
}}

/* ── Devices ───────────────────────────────────────────────── */
async function settingsBuildDevices() {{
  let devData = {{}};
  try {{
    const _did = window.localStorage.getItem('jarvis-shell-device-id-v1') || '';
    const r = await fetch('/api/connected-devices?current_device_id=' + encodeURIComponent(_did));
    devData = await r.json();
  }} catch(e) {{ devData = {{error: true}}; }}

  const devices = devData.devices || [];
  const currentId = devData.current_device_id || window.localStorage.getItem('jarvis-shell-device-id-v1') || '';
  const deviceRows = devices.filter(d => d.mapped || d.device_id === currentId).map(d => {{
    const isCurrent = d.device_id === currentId;
    const ownerName = d.owner_display_name || d.owner_user_id || '';
    const badgeLabel = isCurrent ? 'This device' : (ownerName || 'Unknown');
    const badgeClass = isCurrent ? 'sset-badge-amber' : (ownerName ? 'sset-badge-green' : 'sset-badge-grey');
    const badge = `<span class="sset-badge ${{badgeClass}}">${{escHtml(badgeLabel)}}</span>`;
    const label = d.label || d.device_name || d.device_id || 'Unknown';
    const lastSeen = d.last_seen_at ? d.last_seen_at.slice(0,10) : '';
    return `<div class="sset-row">
      <div class="sset-label">
        <strong style="color:var(--text-1);">${{escHtml(label)}}</strong>
        ${{lastSeen ? `<span style="color:var(--text-3);font-size:10px;display:block;">Last seen: ${{escHtml(lastSeen)}}</span>` : ''}}
      </div>
      ${{badge}}
    </div>`;
  }}).join('') || '<p style="font-size:12px;color:var(--text-3);">No claimed devices yet.</p>';

  const isClaimed = devices.some(d => d.device_id === currentId && (d.owner_user_id || d.owner_display_name));

  return `
    <p class="sset-section-hdr">Connected Devices</p>
    <div class="sset-card">
      ${{deviceRows}}
    </div>
    ${{!isClaimed ? `
    <div class="sset-divider"></div>
    <div class="sset-card">
      <p style="font-size:12px;color:var(--text-2);margin-bottom:10px;">This device is not claimed.</p>
      <button class="sset-btn sset-btn-accent" onclick="settingsClaimDevice()">Claim This Device</button>
      <div id="settings-device-msg" class="sset-msg"></div>
    </div>` : ''}}
    <div class="sset-divider"></div>
    <div class="sset-card" style="padding:12px 16px;">
      <button class="sset-btn" style="color:#f87171;border-color:#f87171;" onclick="settingsPruneDevices()">🗑 Prune Old Devices</button>
      <div style="font-size:11px;color:var(--text-3);margin-top:6px;">Removes unidentified devices older than 7 days.</div>
      <div id="settings-prune-msg" class="sset-msg"></div>
    </div>
    ${{devData.error ? '<p style="font-size:11px;color:#f87171;">Could not load device data.</p>' : ''}}
  `;
}}

/* ── Costs ─────────────────────────────────────────────────── */
async function settingsBuildCosts() {{
  let d = {{}};
  let mapsD = {{}};
  try {{
    const r = await fetch('/api/costs/summary');
    d = await r.json();
  }} catch(e) {{ d = {{error: true}}; }}
  try {{
    const r2 = await fetch('/api/google/maps-usage');
    mapsD = await r2.json();
  }} catch(e) {{}}

  if (d.error) return `<p style="font-size:12px;color:#f87171;">Could not load cost data.</p>`;

  const netTotal   = (d.net_total    || 0).toFixed(2);
  const today      = (d.today_llm    || 0).toFixed(3);
  const monthLLM   = (d.month_llm    || 0).toFixed(2);
  const mapsGross  = (d.month_maps   || 0).toFixed(2);
  const mapsNet    = (d.month_maps_net || 0).toFixed(2);
  const credit     = (d.maps_free_credit || 200).toFixed(0);
  const remaining  = (d.maps_remaining  || 200).toFixed(2);
  const mapsPct    = d.maps_pct_used || 0;
  const daysLeft   = (d.days_in_month || 30) - (d.days_elapsed || 0);
  const projected  = d.days_elapsed > 0
    ? ((d.net_total / d.days_elapsed) * (d.days_in_month || 30)).toFixed(2)
    : '—';
  const tokens     = d.month_tokens || {{}};
  const tokIn      = (tokens.input  || 0).toLocaleString();
  const tokOut     = (tokens.output || 0).toLocaleString();
  const alltime    = (d.alltime_llm || 0).toFixed(2);

  // Build model rows
  const models = d.by_model || {{}};
  const modelRows = Object.entries(models)
    .sort((a,b) => (b[1].cost||0) - (a[1].cost||0))
    .map(([name, info]) => {{
      const cost  = (info.cost  || 0).toFixed(4);
      const calls = (info.calls || 0).toLocaleString();
      const isFree = info.backend === 'ollama' || info.backend === 'groq';
      const tag = isFree
        ? `<span class="sset-badge sset-badge-green">FREE</span>`
        : `<span class="sset-badge sset-badge-amber">PAID</span>`;
      return `<div class="sset-row">
        <div class="sset-label">
          <strong style="color:var(--text-1);">${{escHtml(name)}}</strong>
          <span style="color:var(--text-3);font-size:10px;display:block;">${{escHtml(info.backend||'')}} · ${{calls}} calls this month</span>
        </div>
        <div style="text-align:right;">
          ${{tag}}
          <div style="font-size:12px;font-family:var(--font-mono);color:var(--text-2);margin-top:3px;">$${{cost}}</div>
        </div>
      </div>`;
    }}).join('') || '<p style="font-size:12px;color:var(--text-3);">No calls this month.</p>';

  // Maps API breakdown
  const mapsBarW = Math.min(100, mapsPct);
  const mapsBarClr = mapsPct > 80 ? '#f87171' : mapsPct > 50 ? '#FFD700' : '#4ade80';
  const mapsApiRows = Object.entries(mapsD.usage || {{}}).map(([name, info]) => {{
    const cost = ((info.requests / 1000) * info.price_per_k).toFixed(4);
    return `<div class="sset-row">
      <div class="sset-label">
        <strong style="color:var(--text-1);">${{escHtml(name)}}</strong>
        <span style="color:var(--text-3);font-size:10px;display:block;">${{info.requests.toLocaleString()}} requests</span>
      </div>
      <div style="font-size:12px;font-family:var(--font-mono);color:var(--text-2);">$${{cost}}</div>
    </div>`;
  }}).join('') || '<p style="font-size:12px;color:var(--text-3);">No Maps API usage data (cache may be stale).</p>';

  return `
    <!-- Net cost hero -->
    <div style="background:rgba(0,212,255,0.06);border:1px solid rgba(0,212,255,0.2);
                border-radius:12px;padding:16px 20px;margin-bottom:16px;
                display:flex;align-items:center;justify-content:space-between;">
      <div>
        <div style="font-size:11px;color:var(--text-3);text-transform:uppercase;
                    letter-spacing:0.08em;margin-bottom:4px;">Net cost this month</div>
        <div style="font-size:32px;font-weight:700;color:#00D4FF;
                    font-family:var(--font-mono);line-height:1;">$${{netTotal}}</div>
        <div style="font-size:11px;color:var(--text-3);margin-top:4px;">
          after Google's $${{credit}}/mo Maps credit
        </div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:10px;color:var(--text-3);">today</div>
        <div style="font-size:18px;font-weight:600;color:#00D4FF;font-family:var(--font-mono);">$${{today}}</div>
        <div style="font-size:10px;color:var(--text-3);margin-top:6px;">projected</div>
        <div style="font-size:16px;font-weight:600;color:var(--text-2);font-family:var(--font-mono);">$${{projected}}/mo</div>
        <div style="font-size:10px;color:var(--text-3);margin-top:4px;">
          ${{daysLeft}} days remaining · all-time $${{alltime}}
        </div>
      </div>
    </div>

    <!-- LLM section -->
    <p class="sset-section-hdr">AI Models (LLM)</p>
    <div class="sset-card">
      <div class="sset-row" style="margin-bottom:8px;">
        <div class="sset-label">This month</div>
        <div style="font-size:14px;font-weight:700;color:#FFD700;font-family:var(--font-mono);">$${{monthLLM}}</div>
      </div>
      <div class="sset-row">
        <div class="sset-label" style="font-size:11px;color:var(--text-3);">Tokens processed</div>
        <div style="font-size:11px;color:var(--text-3);font-family:var(--font-mono);">${{tokIn}} in · ${{tokOut}} out</div>
      </div>
    </div>

    <p class="sset-section-hdr" style="margin-top:16px;">Model Breakdown</p>
    <div class="sset-card">
      ${{modelRows}}
    </div>

    <!-- Google Maps section -->
    <p class="sset-section-hdr" style="margin-top:16px;">Google Maps API</p>
    <div class="sset-card">
      <div class="sset-row">
        <div class="sset-label">Gross usage</div>
        <div style="font-size:13px;font-family:var(--font-mono);color:var(--text-2);">$${{mapsGross}}</div>
      </div>
      <div class="sset-row">
        <div class="sset-label">Free credit applied</div>
        <div style="font-size:13px;font-family:var(--font-mono);color:#4ade80;">-$${{credit}}.00</div>
      </div>
      <div class="sset-row">
        <div class="sset-label"><strong>Net owed</strong></div>
        <div style="font-size:14px;font-weight:700;font-family:var(--font-mono);
                    color:${{mapsNet==='0.00'?'#4ade80':'#f87171'}};">
          ${{mapsNet === '0.00' ? 'FREE' : '$$'+mapsNet}}
        </div>
      </div>
      <!-- Credit bar -->
      <div style="margin-top:10px;">
        <div style="display:flex;justify-content:space-between;font-size:10px;
                    color:var(--text-3);margin-bottom:4px;">
          <span>$${{mapsGross}} used of $${{credit}} credit</span>
          <span style="color:${{mapsBarClr}};">${{mapsPct}}%</span>
        </div>
        <div style="height:5px;border-radius:3px;background:rgba(255,255,255,0.08);overflow:hidden;">
          <div style="height:100%;width:${{mapsBarW}}%;background:${{mapsBarClr}};
                      border-radius:3px;transition:width 0.6s;"></div>
        </div>
        <div style="font-size:10px;color:var(--text-3);margin-top:3px;">
          $${{remaining}} credit remaining this month
        </div>
      </div>
    </div>

    <p class="sset-section-hdr" style="margin-top:16px;">Maps API Breakdown</p>
    <div class="sset-card">
      ${{mapsApiRows}}
    </div>

    <div class="sset-divider"></div>
    <p style="font-size:11px;color:var(--text-3);text-align:center;padding:4px 0;">
      Data refreshes when you re-open this tab · Maps API cached for 6 hours
    </p>
  `;
}}

async function settingsPruneDevices() {{
  const msg = document.getElementById('settings-prune-msg');
  try {{
    const r = await fetch('/api/identity/devices/prune', {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{max_age_days: 7}})}});
    const d = await r.json();
    if (msg) msg.textContent = d.detail || (d.ok ? 'Old devices pruned.' : 'Error pruning.');
    if (d.ok) setTimeout(() => settingsLoadSection('devices'), 800);
  }} catch(e) {{
    if (msg) msg.textContent = 'Error: ' + e.message;
  }}
}}

/* ── Action helpers ────────────────────────────────────────── */
async function settingsSaveGoogleJson() {{
  const ta = document.getElementById('settings-google-json');
  const msg = document.getElementById('settings-google-msg');
  const raw = (ta?.value || '').trim();
  if (!raw) {{ if (msg) msg.textContent = 'Paste the JSON first.'; return; }}
  try {{
    const r = await fetch('/api/google/client-secret', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{client_secret_json: raw}})
    }});
    const d = await r.json();
    if (msg) msg.textContent = d.detail || (d.ok ? 'Saved!' : 'Error saving.');
    if (d.ok) {{ settingsLoadSection('accounts'); }}
  }} catch(e) {{
    if (msg) msg.textContent = 'Network error: ' + e.message;
  }}
}}

async function settingsConnectGoogle() {{
  const msg = document.getElementById('settings-google-msg');
  try {{
    const r = await fetch('/api/accounts');
    const data = await r.json();
    const acct = (data.accounts || []).find(a => a.provider === 'google' && a.owner_user_id === 'chris')
                 || (data.accounts || []).find(a => a.provider === 'google');
    if (!acct) {{ if (msg) msg.textContent = 'No Google account found.'; return; }}
    window.open('/accounts/' + acct.account_id + '/connect', '_blank');
    if (msg) msg.textContent = 'Google login opened in a new tab.';
  }} catch(e) {{
    if (msg) msg.textContent = 'Error: ' + e.message;
  }}
}}

async function settingsConnectOutlook() {{
  const msg = document.getElementById('settings-outlook-msg');
  try {{
    const r = await fetch('/api/accounts');
    const data = await r.json();
    const acct = (data.accounts || []).find(a => a.provider === 'outlook' || a.provider === 'microsoft');
    if (!acct) {{
      if (msg) msg.textContent = 'No Outlook account configured. Set JARVIS_MICROSOFT_* env vars first.';
      return;
    }}
    window.open('/accounts/' + acct.account_id + '/connect', '_blank');
    if (msg) msg.textContent = 'Outlook login opened in a new tab.';
  }} catch(e) {{
    if (msg) msg.textContent = 'Error: ' + e.message;
  }}
}}

async function settingsConnectAccount(accountId) {{
  window.open('/accounts/' + accountId + '/connect', '_blank');
}}

async function settingsSaveVoice() {{
  const msg = document.getElementById('settings-voice-msg');
  const provider = document.getElementById('voice-provider')?.value;
  const model = document.getElementById('voice-model')?.value;
  try {{
    const r = await fetch('/api/voice-settings', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{provider, model}})
    }});
    const d = await r.json();
    if (msg) msg.textContent = d.detail || (d.ok ? 'Voice settings saved.' : 'Error saving.');
  }} catch(e) {{
    if (msg) msg.textContent = 'Error: ' + e.message;
  }}
}}

function settingsUseCurrentLocation() {{
  const msg = document.getElementById('settings-loc-msg');
  if (!navigator.geolocation) {{ if (msg) msg.textContent = 'Geolocation not available.'; return; }}
  if (msg) msg.textContent = 'Requesting location…';
  navigator.geolocation.getCurrentPosition(async pos => {{
    const lat = pos.coords.latitude, lon = pos.coords.longitude;
    try {{
      const r = await fetch('/api/location-settings', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{label: 'Current Location', lat, lon}})
      }});
      const d = await r.json();
      if (msg) msg.textContent = d.detail || (d.ok ? `Saved: ${{lat.toFixed(4)}}, ${{lon.toFixed(4)}}` : 'Error saving.');
      if (d.ok) settingsLoadSection('location');
    }} catch(e) {{ if (msg) msg.textContent = 'Error: ' + e.message; }}
  }}, err => {{
    if (msg) msg.textContent = 'Location denied: ' + err.message;
  }});
}}

async function settingsSaveLocation() {{
  const label = document.getElementById('loc-new-label')?.value.trim();
  const notes = document.getElementById('loc-new-notes')?.value.trim();
  const latRaw = document.getElementById('loc-new-lat')?.value.trim();
  const lonRaw = document.getElementById('loc-new-lon')?.value.trim();
  const msg = document.getElementById('settings-loc-add-msg');
  if (!label) {{ if (msg) msg.textContent = 'Enter a label first.'; return; }}
  const lat = latRaw ? parseFloat(latRaw) : null;
  const lon = lonRaw ? parseFloat(lonRaw) : null;
  try {{
    const r = await fetch('/api/location-settings', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{label, notes, ...(lat !== null ? {{lat, lon}} : {{}})}})
    }});
    const d = await r.json();
    if (msg) msg.textContent = d.detail || (d.ok ? 'Location saved.' : 'Error saving.');
    if (d.ok) settingsLoadSection('location');
  }} catch(e) {{
    if (msg) msg.textContent = 'Error: ' + e.message;
  }}
}}

function settingsGeolocateNewLocation() {{
  if (!navigator.geolocation) {{ alert('Geolocation not available.'); return; }}
  navigator.geolocation.getCurrentPosition(pos => {{
    const latEl = document.getElementById('loc-new-lat');
    const lonEl = document.getElementById('loc-new-lon');
    if (latEl) latEl.value = pos.coords.latitude.toFixed(6);
    if (lonEl) lonEl.value = pos.coords.longitude.toFixed(6);
    const msg = document.getElementById('settings-loc-add-msg');
    if (msg) msg.textContent = 'Coordinates filled from GPS.';
  }}, err => {{ alert('Location denied: ' + err.message); }});
}}

async function settingsGeocodeAddress() {{
  const address = document.getElementById('loc-new-address')?.value.trim();
  const city    = document.getElementById('loc-new-city')?.value.trim();
  const state   = document.getElementById('loc-new-state')?.value.trim();
  const zip     = document.getElementById('loc-new-zip')?.value.trim();
  const msg     = document.getElementById('settings-loc-add-msg');
  const query   = [address, city, state, zip].filter(Boolean).join(', ');
  if (!query) {{ if (msg) msg.textContent = 'Enter an address first.'; return; }}
  if (msg) msg.textContent = 'Looking up address…';
  try {{
    const r = await fetch('/api/maps/geocode?q=' + encodeURIComponent(query));
    const d = await r.json();
    if (d.lat != null && d.lon != null) {{
      document.getElementById('loc-new-lat').value = d.lat.toFixed(6);
      document.getElementById('loc-new-lon').value = d.lon.toFixed(6);
      if (msg) msg.textContent = '✓ Found: ' + (d.formatted || query);
      // Auto-fill label if empty
      const labelEl = document.getElementById('loc-new-label');
      if (labelEl && !labelEl.value) labelEl.value = city || address || query;
    }} else {{
      if (msg) msg.textContent = 'Address not found. Try adding more detail.';
    }}
  }} catch(e) {{
    if (msg) msg.textContent = 'Geocode error: ' + e.message;
  }}
}}

async function settingsClaimDevice(ownerUserId) {{
  const msg = document.getElementById('settings-device-msg');

  /* Step 1 — if no owner chosen yet, show a family picker */
  if (!ownerUserId) {{
    if (msg) msg.innerHTML = `
      <div style="margin-top:10px;">
        <div style="font-size:12px;color:var(--text-2);margin-bottom:8px;">Who is using this device?</div>
        <div style="display:flex;flex-wrap:wrap;gap:8px;">
          <button class="sset-btn sset-btn-accent" onclick="settingsClaimDevice('chris')">Chris</button>
          <button class="sset-btn sset-btn-accent" onclick="settingsClaimDevice('rebekah')">Rebekah</button>
          <button class="sset-btn sset-btn-accent" onclick="settingsClaimDevice('caleb')">Caleb</button>
          <button class="sset-btn sset-btn-accent" onclick="settingsClaimDevice('anna')">Anna</button>
        </div>
      </div>`;
    return;
  }}

  /* Step 2 — ensure we have a device ID (generate one if missing) */
  let deviceId = window.localStorage.getItem('jarvis-shell-device-id-v1') || '';
  if (!deviceId) {{
    deviceId = ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
      (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16));
    window.localStorage.setItem('jarvis-shell-device-id-v1', deviceId);
  }}

  const name = navigator.userAgent.includes('iPhone') ? ownerUserId + "'s iPhone" :
               navigator.userAgent.includes('iPad')  ? ownerUserId + "'s iPad"   :
               navigator.userAgent.includes('Mac')   ? ownerUserId + "'s Mac"    :
               navigator.userAgent.includes('Android') ? ownerUserId + "'s Phone" :
               ownerUserId + "'s Browser";

  try {{
    if (msg) msg.textContent = 'Claiming…';
    const r = await fetch('/api/identity/device', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        device_id:     deviceId,
        owner_user_id: ownerUserId,
        device_name:   name,
        device_type:   'browser'
      }})
    }});
    const d = await r.json();
    if (msg) msg.textContent = d.ok
      ? '✓ Claimed as ' + name
      : (d.detail || 'Error claiming device.');
    if (d.ok) {{
      /* Persist claimed identity so WAU overlay never shows again on this browser */
      window.localStorage.setItem('jarvis-claimed-user-v1', ownerUserId);
      setTimeout(() => settingsLoadSection('devices'), 800);
    }}
  }} catch(e) {{
    if (msg) msg.textContent = 'Error: ' + e.message;
  }}
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

/**
 * Format a UTC timestamp string (ISO or "YYYY-MM-DD HH:MM:SS ±HH:MM") into
 * the user's local time. Falls back to the raw string if parsing fails.
 */
function fmtLocalTime(utcStr, {{dateOnly=false, short=false}}={{}}) {{
  if (!utcStr) return '—';
  try {{
    // Normalise: add Z if no timezone info and no offset present
    let s = String(utcStr).trim();
    // "2026-05-20 02:35:33 -0400"  →  "2026-05-20T02:35:33-04:00"
    s = s.replace(/^(\\d{{4}}-\\d{{2}}-\\d{{2}}) (\\d{{2}}:\\d{{2}}:\\d{{2}}) ([+-]\\d{{2}}):?(\\d{{2}})$/, '$1T$2$3:$4');
    // "2026-05-20 19:03:28" (space, no tz) → treat as UTC
    if (/^\\d{{4}}-\\d{{2}}-\\d{{2}} \\d{{2}}:\\d{{2}}:\\d{{2}}$/.test(s)) s = s.replace(' ', 'T') + 'Z';
    // "2026-05-20T19:03:28" (T, no tz) → treat as UTC
    if (/^\\d{{4}}-\\d{{2}}-\\d{{2}}T\\d{{2}}:\\d{{2}}:\\d{{2}}$/.test(s)) s += 'Z';
    const d = new Date(s);
    if (isNaN(d)) return utcStr;
    if (dateOnly) {{
      return d.toLocaleDateString('en-US', {{month:'short', day:'numeric', year:'numeric'}});
    }}
    if (short) {{
      return d.toLocaleTimeString('en-US', {{hour:'numeric', minute:'2-digit', hour12:true}}) +
             ' ' + d.toLocaleDateString('en-US', {{month:'short', day:'numeric'}});
    }}
    return d.toLocaleString('en-US', {{
      month:'short', day:'numeric', year:'numeric',
      hour:'numeric', minute:'2-digit', hour12:true
    }});
  }} catch(e) {{ return String(utcStr); }}
}}

// ── Health Intelligence (Helen Cho) ─────────────────────────────────────────

let _helenNarrativeExpanded = false;

async function loadHealth() {{
  // Fire all data loads in parallel
  const [sumRes, ecgRes, bpRes, omronRes, helenRes, dbRes] = await Promise.all([
    fetch('/api/health/summary').catch(() => null),
    fetch('/api/health/ecg').catch(() => null),
    fetch('/api/health/bp').catch(() => null),
    fetch('/api/health/omron/status').catch(() => null),
    fetch('/api/health/helen/analysis').catch(() => null),
    fetch('/api/health/db/summary').catch(() => null),
  ]);

  if (sumRes && sumRes.ok) {{
    const d = await sumRes.json();
    _renderHealthDashboard(d);
    _renderHealthMetricStrip(d, null);
  }}
  if (ecgRes && ecgRes.ok) {{
    const e = await ecgRes.json();
    _renderEcgList(e.readings || []);
  }}
  if (bpRes && bpRes.ok) {{
    const b = await bpRes.json();
    _renderBpPanel(b);
    // Also update metric strip BP
    if (sumRes && sumRes.ok) {{
      try {{ const d2 = await (sumRes.clone ? Promise.resolve(null) : fetch('/api/health/summary').then(r => r.json())); }} catch(e) {{}}
    }}
    _renderHealthMetricStrip({{metrics: {{}}}}, b);
  }}
  // Render sparklines (static lab data)
  _renderHealthSparklines();
  if (omronRes && omronRes.ok) {{
    const o = await omronRes.json();
    _renderOmronStatus(o);
  }}
  if (helenRes && helenRes.ok) {{
    const h = await helenRes.json();
    if (h.status === 'generating') {{
      // Poll for result
      _helenPollForAnalysis();
    }} else {{
      _renderHelenAnalysis(h);
    }}
  }}
  if (dbRes && dbRes.ok) {{
    const db = await dbRes.json();
    _renderConditions(db);
    _renderGoals(db);
    _renderLabAlerts(null, db);  // use DB data until Helen returns
  }}
  // Load next appointment date
  _loadNextApptDate();
  // Load longevity projection
  loadLongevityInHealth();
  // Load digital twin
  loadHealthTwin();
  // Load Sam Wilson check-in banner + daily protocol
  loadSamCheckin();
  loadSamProtocol();
  // Load today's food diary strip
  samLoadFoodLog();
  // Init health chat (load doctor roster)
  hchatInit();
}}

/* ═══ MANUAL VITALS ENTRY ════════════════════════════════════ */
function openVitalsEntry() {{
  const ov = document.getElementById('vitals-entry-overlay');
  if (!ov) return;
  // Default date to today
  const today = new Date().toISOString().slice(0, 10);
  const di = document.getElementById('vitals-date');
  if (di && !di.value) di.value = today;
  ov.classList.remove('hidden');
}}
function closeVitalsEntry(e) {{
  if (e && e.target !== document.getElementById('vitals-entry-overlay')) return;
  document.getElementById('vitals-entry-overlay')?.classList.add('hidden');
}}
async function submitVitals() {{
  const btn = document.getElementById('vitals-submit-btn');
  if (btn) {{ btn.disabled = true; btn.textContent = 'Saving…'; }}
  try {{
    const dateVal = document.getElementById('vitals-date')?.value ||
                    new Date().toISOString().slice(0,10);

    // Helper: parse a numeric field, return undefined if empty
    const num = id => {{
      const v = document.getElementById(id)?.value;
      if (v === '' || v == null) return undefined;
      return parseFloat(v);
    }};

    // Build daily metrics payload — skip undefined fields
    const metrics = {{ date: dateVal, source: 'manual' }};
    const set = (key, val) => {{ if (val !== undefined && !isNaN(val)) metrics[key] = val; }};
    set('sleep_hours',  num('vi-sleep'));
    set('hrv',          num('vi-hrv'));
    set('resting_hr',   num('vi-rhr'));
    set('blood_oxygen', num('vi-spo2'));
    set('weight',       num('vi-weight'));
    set('body_fat_pct', num('vi-bodyfat'));
    set('steps',        num('vi-steps'));
    set('active_cal',   num('vi-cal'));
    set('exercise_min', num('vi-exercise'));
    set('stand_hours',  num('vi-stand'));

    const sys = num('vi-sys');
    const dia = num('vi-dia');
    const pulse = num('vi-pulse');

    // Determine if we have any meaningful data
    const hasDailyMetrics = Object.keys(metrics).length > 2;  // more than just date+source
    const hasBP = sys !== undefined && dia !== undefined;

    if (!hasDailyMetrics && !hasBP) {{
      showToast('Enter at least one value', 'warn');
      return;
    }}

    const results = [];

    // POST daily metrics
    if (hasDailyMetrics) {{
      const res = await fetch('/api/health/ingest', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(metrics),
      }});
      if (res.ok) results.push('vitals');
      else {{
        const e = await res.json().catch(() => ({{}}));
        console.error('vitals ingest error', e);
      }}
    }}

    // POST blood pressure separately (goes to bp_readings table)
    if (hasBP) {{
      const bpPayload = {{
        systolic: sys,
        diastolic: dia,
        source: 'manual',
        reading_date: new Date(dateVal + 'T12:00:00').toISOString(),
      }};
      if (pulse !== undefined && !isNaN(pulse)) bpPayload.pulse = pulse;
      const res = await fetch('/api/health/bp/ingest', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(bpPayload),
      }});
      if (res.ok) results.push('blood pressure');
    }}

    if (results.length) {{
      showToast('Logged: ' + results.join(' + '), 'ok');
      // Clear all fields
      ['vi-sleep','vi-hrv','vi-rhr','vi-spo2','vi-weight','vi-bodyfat',
       'vi-steps','vi-cal','vi-exercise','vi-stand','vi-sys','vi-dia','vi-pulse']
        .forEach(id => {{ const el=document.getElementById(id); if(el) el.value=''; }});
      document.getElementById('vitals-entry-overlay')?.classList.add('hidden');
      // Refresh the health view if it's visible
      if (document.getElementById('view-health')?.style.display !== 'none') {{
        setTimeout(() => loadHealthView && loadHealthView(), 800);
      }}
    }} else {{
      showToast('Could not save — check console', 'warn');
    }}
  }} catch(e) {{
    console.error('submitVitals', e);
    showToast('Network error', 'warn');
  }} finally {{
    if (btn) {{ btn.disabled = false; btn.textContent = 'Save Vitals'; }}
  }}
}}
/* ════════════════════════════════════════════════════════════ */

async function helenRefresh() {{
  const btn = document.getElementById('helen-refresh-btn');
  if (btn) {{ btn.disabled = true; btn.textContent = '⟳ Analysing…'; }}
  document.getElementById('helen-headline').textContent = 'Helen is analysing your complete health record…';
  document.getElementById('helen-actions').innerHTML =
    '<div style="font-size:11px;color:var(--text-3);padding:8px 0;">Generating action plan…</div>';

  const res = await fetch('/api/health/helen/refresh', {{method:'POST'}}).catch(() => null);
  if (res && res.ok) {{
    const h = await res.json();
    _renderHelenAnalysis(h);
  }} else {{
    document.getElementById('helen-headline').textContent = 'Analysis failed — check LLM gateway status.';
  }}
  if (btn) {{ btn.disabled = false; btn.textContent = '↻ Refresh Analysis'; }}
}}

function _helenPollForAnalysis() {{
  const maxTries = 40;
  let tries = 0;
  const timer = setInterval(async () => {{
    tries++;
    if (tries > maxTries) {{ clearInterval(timer); return; }}
    const res = await fetch('/api/health/helen/analysis').catch(() => null);
    if (!res || !res.ok) return;
    const h = await res.json();
    if (h.status !== 'generating' && !h.error) {{
      clearInterval(timer);
      _renderHelenAnalysis(h);
    }}
  }}, 3000);
}}

function _renderHealthDashboard(d) {{
  // Readiness
  const r = d.readiness || {{}};
  const scoreEl = document.getElementById('health-readiness-score');
  const gradeEl = document.getElementById('health-readiness-grade');
  const msgEl   = document.getElementById('health-readiness-message');
  const facEl   = document.getElementById('health-readiness-factors');
  if (scoreEl) scoreEl.textContent = r.score != null ? r.score : '—';
  if (gradeEl) gradeEl.textContent = r.grade || '—';
  if (msgEl)   msgEl.textContent   = r.message || '';
  if (facEl && r.factors && r.factors.length) {{
    facEl.innerHTML = r.factors.map(f =>
      `<div style="display:flex;justify-content:space-between;font-size:10px;padding:2px 0;border-bottom:1px solid var(--border);">
        <span style="color:var(--text-2);">${{escHtml(f.label)}}</span>
        <span style="color:var(--amber);">${{f.value}} <span style="color:var(--text-3);">(score ${{f.score}})</span></span>
      </div>`
    ).join('');
  }}

  // Metrics grid
  const gridEl = document.getElementById('health-metrics-grid');
  if (gridEl) {{
    const LABELS = {{
      steps:'Steps', resting_hr:'Resting HR', hrv:'HRV',
      sleep_hours:'Sleep', blood_oxygen:'Blood O₂',
      active_calories:'Active Cal', exercise_minutes:'Exercise',
      weight:'Weight'
    }};
    const UNITS = {{
      steps:'', resting_hr:'bpm', hrv:'ms',
      sleep_hours:'hrs', blood_oxygen:'%',
      active_calories:'kcal', exercise_minutes:'min', weight:'lbs'
    }};
    const entries = d.metrics
      ? Object.entries(d.metrics).filter(([k,v]) => v !== null && v !== undefined)
      : [];
    gridEl.innerHTML = entries.map(([k,v]) =>
      `<div style="background:var(--surface-2);border-radius:6px;padding:8px 10px;">
        <div style="font-size:9px;color:var(--text-3);text-transform:uppercase;letter-spacing:0.5px;">${{LABELS[k]||k}}</div>
        <div style="font-size:18px;font-weight:600;color:var(--text-1);font-family:var(--font-mono);">${{typeof v==='number'?v.toLocaleString():v}}<span style="font-size:9px;color:var(--text-3);margin-left:2px;">${{UNITS[k]||''}}</span></div>
      </div>`
    ).join('') || '<div style="grid-column:1/-1;font-size:11px;color:var(--text-3);">No data — configure Health Auto Export</div>';
  }}

  // Header sync label
  const syncEl = document.getElementById('health-last-sync');
  if (syncEl) syncEl.textContent = d.has_data && d.date ? 'Data: ' + fmtLocalTime(d.date,{{dateOnly:true}}) : 'No wearable data';

  const appleBadge = document.getElementById('health-apple-badge');
  if (appleBadge) appleBadge.textContent = d.has_data ? 'Connected' : 'Not connected';
}}

// ── Helen Cho Analysis Renderers ─────────────────────────────────────────────

function _renderHelenAnalysis(h) {{
  if (!h || h.error || h.status === 'generating') return;

  const RISK_COLORS = {{
    critical: 'var(--red)', high: 'var(--red)', moderate: 'var(--amber)', low: 'var(--green)'
  }};
  const URGENCY_COLORS = {{
    critical:'#ef4444', high:'#f97316', moderate:'#f59e0b', low:'#10b981'
  }};

  // Score + grade
  const riskCol = RISK_COLORS[h.risk_level] || 'var(--amber)';
  const scoreEl = document.getElementById('helen-score');
  const gradeEl = document.getElementById('helen-grade');
  const riskBadge = document.getElementById('helen-risk-badge');
  if (scoreEl) {{ scoreEl.textContent = h.overall_score ?? '—'; scoreEl.style.color = riskCol; }}
  if (gradeEl) gradeEl.textContent = h.overall_grade || '—';
  if (riskBadge) {{
    riskBadge.textContent = (h.risk_level || '').toUpperCase() + ' RISK';
    riskBadge.style.background = (riskCol || 'var(--surface-2)') + '22';
    riskBadge.style.color = riskCol;
    riskBadge.style.border = '1px solid ' + riskCol + '44';
  }}

  // Headline
  const hlEl = document.getElementById('helen-headline');
  if (hlEl) hlEl.textContent = h.headline || '';

  // Narrative
  const narrativeEl = document.getElementById('helen-narrative-text');
  const fadeEl      = document.getElementById('helen-narrative-fade');
  const expandBtn   = document.getElementById('helen-expand-btn');
  if (narrativeEl && h.analysis_narrative) {{
    narrativeEl.innerHTML = h.analysis_narrative
      .split('\\n\\n').map(p => `<p style="margin:0 0 8px 0;">${{escHtml(p)}}</p>`).join('');
    setTimeout(() => {{
      const narWrap = document.getElementById('helen-narrative');
      if (narWrap && narrativeEl.scrollHeight > 125) {{
        if (fadeEl) fadeEl.style.display = 'block';
        if (expandBtn) expandBtn.style.display = 'block';
      }}
    }}, 50);
  }}

  // Positive findings strip
  const posEl = document.getElementById('helen-positives');
  if (posEl && h.positive_findings && h.positive_findings.length) {{
    posEl.style.display = 'block';
    posEl.innerHTML = '✓ ' + h.positive_findings.join(' &nbsp;·&nbsp; ✓ ');
  }}

  // Actions
  _renderActions(h.priority_actions || []);

  // Conditions analysis
  if (h.conditions_analysis && h.conditions_analysis.length) {{
    _renderConditionsAnalysis(h.conditions_analysis);
  }}

  // Lab alerts from Helen
  if (h.lab_alerts && h.lab_alerts.length) {{
    _renderLabAlerts(h.lab_alerts, null);
  }}

  // Medication insights
  const medEl = document.getElementById('helen-med-insights');
  if (medEl && h.medication_insights && h.medication_insights.length) {{
    const PRIORITY_COL = {{high:'var(--red)', medium:'var(--amber)', low:'var(--text-2)'}};
    medEl.innerHTML = h.medication_insights.map(m => `
      <div style="padding:5px 0;border-bottom:1px solid var(--border);">
        <div style="font-size:10px;font-weight:600;color:${{PRIORITY_COL[m.priority]||'var(--text-2)'}};">${{escHtml(m.medication)}}</div>
        <div style="font-size:10px;color:var(--text-2);line-height:1.5;margin-top:2px;">${{escHtml(m.observation)}}</div>
      </div>`
    ).join('');
  }}

  // Cardiovascular risk
  const cvEl = document.getElementById('helen-cv-risk');
  if (cvEl && h.cardiovascular_risk) {{
    const cv = h.cardiovascular_risk;
    const cvCol = (cv['10yr_risk_estimate']||'').includes('high') ? 'var(--red)' :
                  (cv['10yr_risk_estimate']||'').includes('intermediate') ? 'var(--amber)' : 'var(--text-2)';
    cvEl.innerHTML = `
      <div style="font-size:11px;font-weight:700;color:${{cvCol}};margin-bottom:4px;">${{escHtml(cv['10yr_risk_estimate']||'—')}}</div>
      <div style="font-size:10px;color:var(--text-3);line-height:1.5;">${{escHtml(cv.assessment||'')}}</div>
      ${{(cv.key_drivers||[]).length ? `<div style="margin-top:6px;">${{cv.key_drivers.map(d=>`<span style="font-size:9px;background:var(--surface-2);border-radius:8px;padding:2px 6px;margin:2px 2px 0 0;display:inline-block;color:var(--text-3);">${{escHtml(d)}}</span>`).join('')}}</div>` : ''}}
    `;
  }}

  // Diabetes complications risk
  const diabEl = document.getElementById('helen-diabetes-risk');
  if (diabEl && h.diabetes_complications_risk) {{
    const dr = h.diabetes_complications_risk;
    const RISK_C = {{high:'var(--red)',moderate:'var(--amber)',low:'var(--green)'}};
    const items = [
      ['Nephropathy', dr.nephropathy],
      ['Retinopathy', dr.retinopathy],
      ['Neuropathy',  dr.neuropathy],
      ['Cardiovascular', dr.cardiovascular],
    ];
    diabEl.innerHTML = items.map(([label,level]) => `
      <div style="display:flex;justify-content:space-between;font-size:10px;padding:3px 0;border-bottom:1px solid var(--border);">
        <span style="color:var(--text-2);">${{label}}</span>
        <span style="color:${{RISK_C[level]||'var(--text-3)'}}; font-weight:600;text-transform:uppercase;font-size:9px;">${{level||'—'}}</span>
      </div>`
    ).join('') + (dr.assessment ? `<div style="font-size:10px;color:var(--text-3);margin-top:6px;line-height:1.5;">${{escHtml(dr.assessment)}}</div>` : '');
  }}

  // Doctor questions
  const qEl = document.getElementById('helen-doctor-questions');
  if (qEl && h.doctor_questions && h.doctor_questions.length) {{
    qEl.innerHTML = h.doctor_questions.map((q,i) =>
      `<div style="display:flex;gap:8px;padding:5px 0;border-bottom:1px solid var(--border);font-size:11px;">
        <span style="color:var(--hue);font-weight:700;flex-shrink:0;">${{i+1}}.</span>
        <span style="color:var(--text-2);line-height:1.5;">${{escHtml(q)}}</span>
      </div>`
    ).join('');
  }}

  // Missing data
  const missingEl = document.getElementById('helen-missing-data');
  if (missingEl && h.missing_data && h.missing_data.length) {{
    missingEl.innerHTML = h.missing_data.map(m =>
      `<div style="font-size:10px;color:var(--text-3);padding:3px 0;">⬜ ${{escHtml(m)}}</div>`
    ).join('');
  }}

  // Key trends panel
  const trendsEl = document.getElementById('helen-key-trends');
  if (trendsEl && h.key_trends && h.key_trends.length) {{
    const TRAJ_ICON = {{improving:'↗', stable:'→', worsening:'↘', stalled:'↔'}};
    const TRAJ_COL  = {{improving:'var(--green)', stable:'var(--text-3)', worsening:'var(--red)', stalled:'var(--amber)'}};
    trendsEl.innerHTML = h.key_trends.map(t => {{
      const traj = (t.trajectory||'stable').toLowerCase();
      const icon = TRAJ_ICON[traj] || '→';
      const col  = TRAJ_COL[traj]  || 'var(--text-3)';
      return `
      <div style="padding:7px 0;border-bottom:1px solid var(--border);">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:11px;font-weight:600;color:var(--text-1);">${{escHtml(t.metric||'')}}</span>
          <span style="font-size:13px;color:${{col}};font-weight:700;">${{icon}} <span style="font-size:10px;">${{escHtml(t.latest_value||'')}}</span></span>
        </div>
        <div style="font-size:10px;color:var(--text-2);margin-top:2px;line-height:1.4;">${{escHtml(t.trend_summary||'')}}</div>
        <div style="font-size:9px;color:var(--text-3);margin-top:2px;font-style:italic;">${{escHtml(t.clinical_significance||'')}}</div>
      </div>`;
    }}).join('');
  }}

  // Trajectory summary
  const trajEl = document.getElementById('helen-trajectory');
  if (trajEl && h.trajectory_summary) {{
    trajEl.innerHTML = `<div style="font-size:11px;color:var(--text-2);line-height:1.6;padding:8px 10px;background:rgba(239,68,68,0.06);border-radius:6px;border-left:3px solid var(--red);">${{escHtml(h.trajectory_summary)}}</div>`;
  }}

  // Post-bariatric status
  const pbEl = document.getElementById('helen-post-bariatric');
  if (pbEl && h.post_bariatric_status) {{
    const pb = h.post_bariatric_status;
    pbEl.innerHTML = `
      <div style="font-size:10px;color:var(--text-3);line-height:1.5;">${{escHtml(pb.assessment||'')}}</div>
      ${{(pb.nutrition_gaps||[]).length ? `<div style="margin-top:6px;">${{(pb.nutrition_gaps||[]).map(g=>`<span style="font-size:9px;background:rgba(245,158,11,0.12);color:var(--amber);border-radius:8px;padding:2px 7px;margin:2px 2px 0 0;display:inline-block;">${{escHtml(g)}}</span>`).join('')}}</div>` : ''}}
    `;
  }}

  // Generated timestamp in header
  if (h._generated_utc) {{
    const syncEl = document.getElementById('health-last-sync');
    if (syncEl) syncEl.textContent = 'Analysed ' + fmtLocalTime(h._generated_utc, {{short:true}});
  }}
}}

function helenToggleNarrative() {{
  _helenNarrativeExpanded = !_helenNarrativeExpanded;
  const narWrap  = document.getElementById('helen-narrative');
  const fadeEl   = document.getElementById('helen-narrative-fade');
  const btn      = document.getElementById('helen-expand-btn');
  if (narWrap) narWrap.style.maxHeight = _helenNarrativeExpanded ? 'none' : '120px';
  if (fadeEl)  fadeEl.style.display    = _helenNarrativeExpanded ? 'none' : 'block';
  if (btn)     btn.textContent         = _helenNarrativeExpanded ? 'Show less ▴' : 'Show more ▾';
}}

function _renderActions(actions) {{
  const el = document.getElementById('helen-actions');
  const countEl = document.getElementById('helen-action-count');
  if (!el) return;
  if (!actions.length) {{ el.innerHTML = '<div style="font-size:11px;color:var(--text-3);">No actions generated.</div>'; return; }}
  if (countEl) countEl.textContent = '(' + actions.length + ' items)';

  const URGENCY_BG = {{
    critical: 'rgba(239,68,68,0.1)', high: 'rgba(249,115,22,0.08)',
    moderate: 'rgba(245,158,11,0.08)', low: 'rgba(16,185,129,0.06)'
  }};
  const URGENCY_BORDER = {{
    critical:'#ef4444', high:'#f97316', moderate:'#f59e0b', low:'#10b981'
  }};
  const URGENCY_LABEL = {{
    critical:'CRITICAL', high:'HIGH', moderate:'MODERATE', low:'LOW'
  }};

  el.innerHTML = actions.map(a => {{
    const urg = (a.urgency||'low').toLowerCase();
    const borderCol = URGENCY_BORDER[urg] || '#666';
    const bgCol     = URGENCY_BG[urg]     || 'var(--surface-2)';
    return `
    <div style="display:flex;gap:12px;padding:10px 14px;border-radius:8px;border-left:3px solid ${{borderCol}};background:${{bgCol}};">
      <div style="flex-shrink:0;text-align:center;min-width:28px;">
        <div style="font-size:14px;font-weight:800;color:${{borderCol}};font-family:var(--font-mono);">${{a.rank||''}}</div>
        <div style="font-size:8px;color:${{borderCol}};font-weight:700;letter-spacing:0.5px;">${{URGENCY_LABEL[urg]||urg}}</div>
      </div>
      <div style="flex:1;min-width:0;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;">
          <span style="font-size:9px;background:var(--surface-2);border-radius:8px;padding:1px 7px;color:var(--text-3);">${{escHtml(a.category||'')}}</span>
          <span style="font-size:9px;color:var(--text-3);">${{escHtml(a.timeline||'')}}</span>
        </div>
        <div style="font-size:12px;font-weight:600;color:var(--text-1);line-height:1.4;">${{escHtml(a.action||'')}}</div>
        <div style="font-size:11px;color:var(--text-3);margin-top:3px;line-height:1.5;">${{escHtml(a.why||'')}}</div>
        ${{a.expected_benefit ? `<div style="font-size:10px;color:var(--green);margin-top:4px;line-height:1.4;">→ ${{escHtml(a.expected_benefit)}}</div>` : ''}}
      </div>
    </div>`;
  }}).join('');
}}

function _renderConditions(db) {{
  const el = document.getElementById('helen-conditions');
  if (!el) return;
  const conds = db.conditions || [];
  if (!conds.length) {{ el.innerHTML = '<div style="font-size:11px;color:var(--text-3);">No conditions synced</div>'; return; }}
  el.innerHTML = conds.map(c =>
    `<div style="display:flex;align-items:center;gap:6px;padding:4px 0;border-bottom:1px solid var(--border);">
      <div style="width:7px;height:7px;border-radius:50%;background:var(--amber);flex-shrink:0;"></div>
      <span style="font-size:11px;color:var(--text-2);">${{escHtml(c)}}</span>
    </div>`
  ).join('');
}}

function _renderConditionsAnalysis(conditions) {{
  const el = document.getElementById('helen-conditions');
  if (!el) return;
  const STATUS_COL = {{
    controlled:'var(--green)', borderline:'var(--amber)', uncontrolled:'var(--red)',
    improving:'var(--green)', worsening:'var(--red)', stable:'var(--text-3)'
  }};
  const TRAJ_ICON = {{ improving:'↑', stable:'→', worsening:'↓' }};
  el.innerHTML = conditions.map(c => {{
    const col  = STATUS_COL[(c.status||'').toLowerCase()] || 'var(--text-2)';
    const traj = TRAJ_ICON[(c.trajectory||'').toLowerCase()] || '';
    return `
    <div style="padding:6px 0;border-bottom:1px solid var(--border);">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">
        <span style="font-size:11px;font-weight:600;color:var(--text-1);">${{escHtml(c.condition||'')}}</span>
        <span style="font-size:9px;font-weight:700;color:${{col}};text-transform:uppercase;">${{escHtml(c.status||'')}} ${{traj}}</span>
      </div>
      <div style="font-size:10px;color:var(--text-3);line-height:1.4;">${{escHtml(c.key_finding||'')}}</div>
      ${{c.complications_risk ? `<div style="font-size:9px;color:var(--amber);margin-top:2px;">Risk: ${{escHtml(c.complications_risk)}}</div>` : ''}}
    </div>`;
  }}).join('');
}}

function _renderGoals(db) {{
  const el = document.getElementById('helen-goals');
  if (!el) return;
  const goals = db.treatment_goals || [];
  if (!goals.length) {{ el.innerHTML = '<div style="font-size:11px;color:var(--text-3);">No goals synced</div>'; return; }}
  el.innerHTML = goals.map(g => {{
    const onTrack = g.on_track;
    const col     = onTrack ? 'var(--green)' : 'var(--red)';
    const icon    = onTrack ? '✓' : '✗';
    return `
    <div style="padding:5px 0;border-bottom:1px solid var(--border);">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:11px;color:var(--text-2);">${{escHtml(g.goal_name||'')}}</span>
        <span style="font-size:10px;font-weight:700;color:${{col}};">${{icon}}</span>
      </div>
      <div style="display:flex;gap:12px;font-size:10px;color:var(--text-3);margin-top:2px;">
        <span>Target: <b style="color:var(--text-2);">${{escHtml(g.target||'—')}}</b></span>
        <span>Now: <b style="color:${{col}};">${{escHtml(g.current_value||'—')}}</b></span>
      </div>
    </div>`;
  }}).join('');
}}

function _renderLabAlerts(helenAlerts, db) {{
  const el = document.getElementById('helen-lab-alerts');
  if (!el) return;

  // If Helen's alerts are available, use them
  if (helenAlerts && helenAlerts.length) {{
    el.innerHTML = helenAlerts.map(a => {{
      const isSerious = (a.significance||'').length > 0;
      return `
      <div style="padding:5px 0;border-bottom:1px solid var(--border);">
        <div style="font-size:10px;font-weight:600;color:var(--amber);">${{escHtml(a.test||'')}}</div>
        <div style="font-size:10px;color:var(--text-2);margin:2px 0;">${{escHtml(a.pattern||'')}}</div>
        <div style="font-size:9px;color:var(--text-3);line-height:1.4;">${{escHtml(a.significance||'')}}</div>
        ${{a.action ? `<div style="font-size:9px;color:var(--hue);margin-top:3px;">→ ${{escHtml(a.action)}}</div>` : ''}}
      </div>`;
    }}).join('');
    return;
  }}

  // Fallback: show abnormal results from DB
  if (db) {{
    const tests  = db.recent_tests || [];
    const abnormal = tests.filter(t => (t.status||'').toLowerCase() === 'abnormal');
    if (abnormal.length) {{
      el.innerHTML = abnormal.map(t =>
        `<div style="display:flex;justify-content:space-between;font-size:10px;padding:3px 0;border-bottom:1px solid var(--border);">
          <span style="color:var(--text-2);">${{escHtml(t.test_name||'').substring(0,40)}}</span>
          <span style="color:var(--red);font-weight:700;">ABNORMAL</span>
        </div>`
      ).join('');
    }} else {{
      el.innerHTML = '<div style="font-size:11px;color:var(--text-3);">No abnormal results found</div>';
    }}
  }}
}}

async function _loadNextApptDate() {{
  const el = document.getElementById('helen-appt-date');
  if (!el) return;
  const res = await fetch('/api/health/db/summary').catch(() => null);
  if (!res || !res.ok) return;
  const d = await res.json();
  if (d.next_appointment) {{
    el.textContent = '· Next: ' + escHtml(d.next_appointment.visit_date||'') +
                     ' with ' + escHtml(d.next_appointment.provider||'');
  }}
}}

// ── ECG list renderer ────────────────────────────────────────────────────────
function _renderEcgList(readings) {{
  const el = document.getElementById('health-ecg-list');
  if (!el) return;
  if (!readings || !readings.length) {{
    el.innerHTML = '<div style="font-size:11px;color:var(--text-3);">No ECG readings yet — your KardiaMobile recordings sync automatically via Health Auto Export.</div>';
    return;
  }}
  const _classColor = c => {{
    if (!c) return 'var(--text-3)';
    const cl = c.toLowerCase();
    if (cl.includes('sinus') || cl.includes('normal')) return 'var(--green)';
    if (cl.includes('afib') || cl.includes('fibrillation')) return 'var(--red)';
    if (cl.includes('unclassified') || cl.includes('possible')) return 'var(--amber)';
    return 'var(--text-2)';
  }};
  el.innerHTML = readings.map(r => `
    <div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--border);">
      <div style="width:8px;height:8px;border-radius:50%;background:${{_classColor(r.classification)}};flex-shrink:0;"></div>
      <div style="flex:1;min-width:0;">
        <div style="font-size:11px;font-weight:600;color:${{_classColor(r.classification)}};">${{escHtml(r.classification || 'Unknown')}}</div>
        <div style="font-size:10px;color:var(--text-3);">${{fmtLocalTime(r.reading_date, {{short:true}})}}</div>
      </div>
      <div style="text-align:right;flex-shrink:0;">
        <div style="font-size:13px;font-weight:600;color:var(--text-1);font-family:var(--font-mono);">${{r.avg_heart_rate ? r.avg_heart_rate + ' bpm' : '—'}}</div>
        <div style="font-size:9px;color:var(--text-3);">${{r.sample_count ? r.sample_count.toLocaleString() + ' samples' : ''}}</div>
      </div>
    </div>`
  ).join('');
  const badge = document.getElementById('health-ecg-badge');
  if (badge) badge.textContent = readings.length + ' reading' + (readings.length !== 1 ? 's' : '');
}}

// ── BP panel renderer ────────────────────────────────────────────────────────
function _renderBpPanel(data) {{
  const latest  = data.latest;
  const history = data.history || [];

  const valEl   = document.getElementById('health-bp-value');
  const pulseEl = document.getElementById('health-bp-pulse');
  const dateEl  = document.getElementById('health-bp-date');
  const histEl  = document.getElementById('health-bp-history');

  if (latest && latest.systolic) {{
    if (valEl)   valEl.textContent   = latest.systolic + '/' + latest.diastolic;
    if (pulseEl) pulseEl.textContent = latest.pulse ? latest.pulse + ' bpm' : '';
    if (dateEl)  dateEl.textContent  = fmtLocalTime(latest.reading_date, {{short:true}});

    // Color-code by AHA categories
    const sys = latest.systolic, dia = latest.diastolic;
    const cat = sys >= 180 || dia >= 120 ? {{label:'Crisis', col:'var(--red)'}}
              : sys >= 140 || dia >= 90  ? {{label:'High Stage 2', col:'var(--red)'}}
              : sys >= 130 || dia >= 80  ? {{label:'High Stage 1', col:'var(--amber)'}}
              : sys >= 120               ? {{label:'Elevated', col:'var(--amber)'}}
              :                           {{label:'Normal', col:'var(--green)'}};
    if (valEl) valEl.style.color = cat.col;
  }} else {{
    if (valEl) valEl.textContent = '—/—';
  }}

  if (histEl && history.length) {{
    histEl.innerHTML = history.map(r => {{
      const sys = r.systolic, dia = r.diastolic;
      const col = sys >= 140 || dia >= 90 ? 'var(--red)' : sys >= 130 ? 'var(--amber)' : 'var(--green)';
      return `<div style="display:flex;justify-content:space-between;font-size:10px;padding:2px 0;">
        <span style="color:${{col}};font-family:var(--font-mono);font-weight:600;">${{sys}}/${{dia}}</span>
        <span style="color:var(--text-3);">${{r.pulse ? r.pulse + ' bpm · ' : ''}}</span>
        <span style="color:var(--text-3);">${{fmtLocalTime(r.reading_date, {{short:true}})}}</span>
      </div>`;
    }}).join('');
  }} else if (histEl) {{
    histEl.innerHTML = '<div style="font-size:11px;color:var(--text-3);">No readings yet</div>';
  }}
}}

// ── Omron status renderer ────────────────────────────────────────────────────
function _renderOmronStatus(o) {{
  const badge   = document.getElementById('health-omron-badge');
  const btn     = document.getElementById('health-omron-btn');
  const section = document.getElementById('health-omron-connect-section');
  if (badge) {{
    badge.textContent  = o.connected ? 'Connected' : (o.configured ? 'Ready to connect' : 'Not configured');
    badge.style.color  = o.connected ? 'var(--green)' : o.configured ? 'var(--amber)' : 'var(--text-3)';
  }}
  if (btn && section) {{
    if (!o.configured) {{
      section.innerHTML = '<div style="font-size:10px;color:var(--text-3);">Add OMRON_CLIENT_ID + OMRON_CLIENT_SECRET to .env to enable</div>';
    }} else if (o.connected) {{
      section.innerHTML = `<div style="font-size:10px;color:var(--green);">✓ Connected${{o.last_sync ? ' · Last sync: ' + fmtLocalTime(o.last_sync, {{short:true}}) : ''}}</div>
        <button class="btn-ghost" onclick="omronSync()" style="font-size:10px;margin-top:4px;">Sync Now</button>`;
    }} else {{
      btn.textContent = o.expired ? 'Reconnect Omron' : 'Connect Omron Account';
    }}
  }}
}}

function omronConnect() {{
  window.open('/api/health/omron/connect', '_blank', 'width=600,height=700');
}}

async function omronSync() {{
  const res = await fetch('/api/health/omron/sync', {{method:'POST',
    headers:{{'Content-Type':'application/json'}}, body:'{{}}'}}).catch(() => null);
  if (res && res.ok) {{
    showToast('Omron sync started', 'success');
    setTimeout(loadHealth, 4000);
  }} else {{
    showToast('Omron sync failed', 'error');
  }}
}}


async function healthTestIngest() {{
  const sample = {{
    source: "test",
    steps: 8432,
    resting_hr: 58,
    hrv: 45,
    sleep_hours: 7.5,
    sleep_deep_hours: 1.8,
    sleep_rem_hours: 1.6,
    active_calories: 523,
    exercise_minutes: 42,
    stand_hours: 10,
    blood_oxygen: 98,
    weight_lbs: 185
  }};
  const res = await fetch('/api/health/ingest', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify(sample),
  }});
  if (res.ok) {{ showToast('Sample data ingested!', 'success'); loadHealth(); }}
  else showToast('Ingest failed', 'error');
}}

async function mychartStartSync() {{
  const btn      = document.getElementById('mychart-sync-btn');
  const status   = document.getElementById('mychart-sync-status');
  const badge    = document.getElementById('mychart-sync-badge');
  const progWrap = document.getElementById('mychart-progress-wrap');
  const progBar  = document.getElementById('mychart-progress-bar');

  if (btn) {{ btn.disabled = true; btn.textContent = '⟳ Starting…'; }}
  if (progWrap) progWrap.style.display = '';
  if (progBar)  progBar.style.width = '5%';
  if (status)   status.textContent = 'Launching Chromium…';
  if (badge)    badge.textContent  = 'syncing';

  // Kick off the server-side Playwright sync (opens Chromium window)
  const r = await fetch('/api/health/mychart/sync', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{headless: false}}),
  }});
  const d = await r.json();
  if (!d.ok && d.error !== 'Sync already running') {{
    if (status) status.textContent = 'Error: ' + (d.error || 'failed to start');
    if (btn)    {{ btn.disabled = false; btn.textContent = '⟳ Sync MyChart'; }}
    if (progWrap) progWrap.style.display = 'none';
    return;
  }}

  // Poll /api/health/mychart/sync-status every 1.5s
  let pollTimer = setInterval(async () => {{
    try {{
      const sr = await fetch('/api/health/mychart/sync-status');
      const s  = await sr.json();

      if (progBar)  progBar.style.width = s.progress + '%';
      if (status)   status.textContent  = s.step || '';

      if (s.needs_login) {{
        if (badge)  badge.textContent = 'login needed';
        if (status) status.textContent = 'Log into MyChart in the browser window that opened, then sync will continue automatically.';
      }}

      if (!s.running) {{
        clearInterval(pollTimer);
        if (s.progress >= 100) {{
          if (badge)  badge.textContent = s.pages_done.length + ' pages ✓';
          if (status) status.textContent = 'Sync complete — ' + s.pages_done.join(', ');
          mychartViewRecords();
        }} else if (s.error) {{
          if (badge)  badge.textContent = 'error';
          if (status) status.textContent = 'Sync failed: ' + s.error;
        }}
        if (btn)      {{ btn.disabled = false; btn.textContent = '⟳ Sync MyChart'; }}
        if (progWrap) progWrap.style.display = 'none';
      }}
    }} catch(e) {{
      clearInterval(pollTimer);
      if (btn) {{ btn.disabled = false; btn.textContent = '⟳ Sync MyChart'; }}
      if (progWrap) progWrap.style.display = 'none';
    }}
  }}, 1500);
}}

async function mychartViewRecords() {{
  const el = document.getElementById('health-medical-records');
  if (!el) return;
  // Prefer the structured DB summary; fall back to raw page summaries
  const [dbRes, rawRes] = await Promise.all([
    fetch('/api/health/db/summary').catch(() => null),
    fetch('/api/health/mychart/summary').catch(() => null),
  ]);

  const db  = dbRes  && dbRes.ok  ? await dbRes.json()  : {{}};
  const raw = rawRes && rawRes.ok ? await rawRes.json() : {{}};

  const pages    = raw.records  || {{}};
  const conds    = db.conditions || [];
  const meds     = db.medications || [];
  const tests    = db.recent_tests || [];
  const nextAppt = db.next_appointment;
  const goals    = db.treatment_goals || [];

  if (!Object.keys(pages).length && !conds.length && !meds.length) {{
    el.innerHTML = '<div style="font-size:11px;color:var(--text-3);">No records synced yet. Click Sync MyChart.</div>';
    return;
  }}

  let html = '';

  // Conditions block
  if (conds.length) {{
    html += `<div style="margin-bottom:12px;">
      <div style="font-size:10px;color:var(--amber);text-transform:uppercase;margin-bottom:4px;">Conditions</div>
      ${{conds.map(c => `<div style="font-size:11px;color:var(--text-2);padding:1px 0;">${{escHtml(c)}}</div>`).join('')}}
    </div>`;
  }}

  // Treatment goals block
  if (goals.length) {{
    html += `<div style="margin-bottom:12px;">
      <div style="font-size:10px;color:var(--amber);text-transform:uppercase;margin-bottom:4px;">Treatment Goals</div>`;
    for (const g of goals) {{
      const dot = g.on_track ? '🟢' : '🔴';
      html += `<div style="font-size:11px;color:var(--text-2);padding:2px 0;">
        ${{dot}} ${{escHtml(g.goal_name)}} — target ${{escHtml(g.target || '')}} · current ${{escHtml(g.current_value || '')}}
      </div>`;
    }}
    html += '</div>';
  }}

  // Medications block
  if (meds.length) {{
    html += `<div style="margin-bottom:12px;">
      <div style="font-size:10px;color:var(--amber);text-transform:uppercase;margin-bottom:4px;">Medications (${{meds.length}})</div>
      ${{meds.slice(0,8).map(m =>
        `<div style="font-size:11px;color:var(--text-2);padding:1px 0;">
          <b>${{escHtml(m.name || '')}}</b>
          <span style="color:var(--text-3);"> ${{escHtml(m.dosage || '')}}</span>
         </div>`
      ).join('')}}
      ${{meds.length > 8 ? `<div style="font-size:10px;color:var(--text-3);">+${{meds.length - 8}} more</div>` : ''}}
    </div>`;
  }}

  // Recent tests
  if (tests.length) {{
    html += `<div style="margin-bottom:12px;">
      <div style="font-size:10px;color:var(--amber);text-transform:uppercase;margin-bottom:4px;">Recent Labs</div>
      ${{tests.map(t => {{
        const flag = t.status === 'Abnormal' ? '<span style="color:var(--red);font-size:9px;"> ▲ ABNORMAL</span>' : '';
        return `<div style="font-size:11px;color:var(--text-2);padding:1px 0;">${{escHtml(t.test_name)}}${{flag}} <span style="color:var(--text-3);">${{escHtml(t.result_date || '')}}</span></div>`;
      }}).join('')}}
    </div>`;
  }}

  // Next appointment
  if (nextAppt) {{
    html += `<div style="margin-bottom:12px;">
      <div style="font-size:10px;color:var(--amber);text-transform:uppercase;margin-bottom:4px;">Next Appointment</div>
      <div style="font-size:11px;color:var(--text-2);">${{escHtml(nextAppt.visit_date || '')}} — ${{escHtml(nextAppt.provider || '')}}</div>
    </div>`;
  }}

  // Fallback: raw page previews if structured data sparse
  if (!conds.length && !meds.length && Object.keys(pages).length) {{
    for (const [key, rec] of Object.entries(pages)) {{
      const label = key.replace(/_/g,' ').replace(/\\b\\w/g, c => c.toUpperCase());
      const preview = (rec.content_preview || '').substring(0,150).replace(/</g,'&lt;');
      html += `<div style="margin-bottom:10px;">
        <div style="font-size:10px;color:var(--amber);text-transform:uppercase;margin-bottom:3px;">${{label}}</div>
        <div style="font-size:11px;color:var(--text-2);">${{preview}}…</div>
      </div>`;
    }}
  }}

  // Last sync time
  if (raw.last_updated) {{
    html += `<div style="font-size:10px;color:var(--text-3);margin-top:8px;">Last synced ${{fmtLocalTime(raw.last_updated)}}</div>`;
  }}

  el.innerHTML = html || '<div style="font-size:11px;color:var(--text-3);">No records found.</div>';
}}

async function loadLongevityInHealth() {{
  const el = document.getElementById('health-longevity-content');
  if (!el) return;
  try {{
    const [estRes, trajRes] = await Promise.all([
      fetch('/api/health/longevity/estimate').catch(() => null),
      fetch('/api/health/longevity/trajectory').catch(() => null),
    ]);
    if (!estRes || !estRes.ok) {{ el.innerHTML = '<div style="color:var(--text-3);">Unavailable</div>'; return; }}
    const est  = await estRes.json();
    const trajRaw = trajRes && trajRes.ok ? await trajRes.json() : [];
    // Trajectory is a plain array [{{date:"YYYY-MM", estimated_age:N, ...}}]
    const history = Array.isArray(trajRaw) ? trajRaw.map(p => {{
      const parts = (p.date||'2021-01').split('-');
      return {{year: parseFloat(parts[0]) + (parseFloat(parts[1]||1)-1)/12, life_expectancy: p.estimated_age, label: p.label}};
    }}) : (trajRaw.history || []);
    const ci = est.confidence_interval || {{}};
    const optimized = est.optimized_life_expectancy || 80.5;
    const remaining = est.years_remaining || 24;
    const le = est.estimated_life_expectancy || est.life_expectancy || 76;
    const trend = history.length >= 2
      ? (history[history.length-1].life_expectancy - history[history.length-2].life_expectancy)
      : 0;
    const trendArrow = trend > 0.2 ? '↑' : trend < -0.2 ? '↓' : '→';
    const trendColor = trend > 0.2 ? 'var(--green)' : trend < -0.2 ? 'var(--red)' : 'var(--amber)';

    // Risk & positive factor rows
    const risks = (est.risk_adjustments || []).filter(r => r.years < 0)
      .map(r => `<div style="display:flex;justify-content:space-between;font-size:10px;padding:2px 0;">
        <span style="color:var(--text-2);">${{r.factor}}</span>
        <span style="color:var(--red);font-family:var(--font-mono);">${{r.years}}yr</span></div>`).join('');
    const gains = (est.risk_adjustments || []).filter(r => r.years > 0)
      .map(r => `<div style="display:flex;justify-content:space-between;font-size:10px;padding:2px 0;">
        <span style="color:var(--text-2);">${{r.factor}}</span>
        <span style="color:var(--green);font-family:var(--font-mono);">+${{r.years}}yr</span></div>`).join('');

    // Build SVG graph
    const svgHtml = _buildLongevitySvg(history, le, optimized);

    el.innerHTML = `
      <div style="display:grid;grid-template-columns:auto 1fr;gap:20px;align-items:start;">
        <div style="min-width:160px;">
          <div style="font-size:11px;color:var(--text-3);margin-bottom:4px;">Life Expectancy</div>
          <div style="font-size:52px;font-weight:700;font-family:var(--font-mono);color:var(--amber);line-height:1;">
            ${{le}}<span style="font-size:18px;color:var(--text-3);">yr</span>
            <span style="font-size:20px;" style="color:${{trendColor}};">${{trendArrow}}</span>
          </div>
          <div style="font-size:10px;color:var(--text-3);margin-bottom:12px;">${{remaining}} years remaining · CI ${{ci.low||72}}–${{ci.high||80}}</div>
          <div style="font-size:9px;color:var(--text-3);margin-bottom:2px;">RISKS</div>
          ${{risks || '<div style="font-size:10px;color:var(--text-3);">None recorded</div>'}}
          <div style="font-size:9px;color:var(--text-3);margin:8px 0 2px;">GAINS</div>
          ${{gains || '<div style="font-size:10px;color:var(--text-3);">None recorded</div>'}}
          <div style="margin-top:10px;padding-top:8px;border-top:1px solid var(--border);font-size:9px;color:var(--text-3);">
            Optimized ceiling: <span style="color:var(--blue);font-family:var(--font-mono);">${{optimized}} yr</span>
          </div>
        </div>
        <div>${{svgHtml}}</div>
      </div>`;
  }} catch(e) {{
    if (el) el.innerHTML = '<div style="color:var(--text-3);">Unavailable</div>';
  }}
}}

function _buildLongevitySvg(history, currentLE, optimized) {{
  if (!history || history.length < 2) return '<div style="color:var(--text-3);font-size:11px;">Not enough history for graph</div>';
  const W = 480, H = 180, padL = 30, padR = 10, padT = 12, padB = 28;
  const iW = W - padL - padR, iH = H - padT - padB;
  const years = history.map(p => p.year || 2021);
  const vals  = history.map(p => p.life_expectancy || currentLE);
  const minYear = Math.min(...years), maxYear = 2031;
  const minVal  = Math.min(...vals, currentLE, optimized) - 2;
  const maxVal  = Math.max(...vals, currentLE, optimized, 80.5) + 2;
  const xS = y => padL + ((y - minYear) / (maxYear - minYear)) * iW;
  const yS = v => padT + (1 - (v - minVal) / (maxVal - minVal)) * iH;
  // Historical path
  const histPts = history.map(p => `${{xS(p.year)}},${{yS(p.life_expectancy)}}`).join(' ');
  const dots    = history.map(p => `<circle cx="${{xS(p.year)}}" cy="${{yS(p.life_expectancy)}}" r="3" fill="#4caf50"/>`).join('');
  // Current projection 2026→2031 (flat at currentLE)
  const nowX = xS(2026.4), endX = xS(2031);
  const nowY = yS(currentLE), optY = yS(optimized);
  // Grid lines
  const gridLines = [70, 75, 80].map(v => {{
    const gy = yS(v);
    return `<line x1="${{padL}}" y1="${{gy}}" x2="${{W-padR}}" y2="${{gy}}" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>
            <text x="${{padL-4}}" y="${{gy+3}}" font-size="7" fill="rgba(255,255,255,0.3)" text-anchor="end">${{v}}</text>`;
  }}).join('');
  // Year labels
  const yearLabels = [2021,2023,2025,2027,2029,2031].filter(y => y <= maxYear && y >= minYear).map(y =>
    `<text x="${{xS(y)}}" y="${{H-6}}" font-size="7" fill="rgba(255,255,255,0.3)" text-anchor="middle">${{y}}</text>`
  ).join('');
  // Actuarial reference
  const actY = yS(80.5);
  return `<svg width="${{W}}" height="${{H}}" viewBox="0 0 ${{W}} ${{H}}" style="width:100%;height:auto;">
    ${{gridLines}}
    <line x1="${{padL}}" y1="${{actY}}" x2="${{W-padR}}" y2="${{actY}}" stroke="rgba(100,149,237,0.3)" stroke-width="1" stroke-dasharray="4,3"/>
    <text x="${{W-padR}}" y="${{actY-3}}" font-size="7" fill="rgba(100,149,237,0.5)" text-anchor="end">Actuarial 80.5</text>
    <line x1="${{xS(2026.4)}}" y1="${{padT}}" x2="${{xS(2026.4)}}" y2="${{H-padB}}" stroke="rgba(255,255,255,0.15)" stroke-width="1" stroke-dasharray="2,2"/>
    <text x="${{xS(2026.4)+3}}" y="${{padT+9}}" font-size="7" fill="rgba(255,255,255,0.3)">TODAY</text>
    <polyline points="${{histPts}}" fill="none" stroke="#4caf50" stroke-width="2"/>
    ${{dots}}
    <line x1="${{nowX}}" y1="${{nowY}}" x2="${{endX}}" y2="${{nowY}}" stroke="#ffb300" stroke-width="1.5" stroke-dasharray="5,3"/>
    <line x1="${{nowX}}" y1="${{nowY}}" x2="${{endX}}" y2="${{optY}}" stroke="#64a0e8" stroke-width="1.5" stroke-dasharray="5,3"/>
    ${{yearLabels}}
    <circle cx="${{nowX}}" cy="${{nowY}}" r="4" fill="#ffb300"/>
    <g transform="translate(${{padL+4}},${{padT+4}})">
      <line x1="0" y1="0" x2="14" y2="0" stroke="#4caf50" stroke-width="2"/><text x="17" y="3" font-size="7" fill="rgba(255,255,255,0.5)">Historical</text>
      <line x1="0" y1="10" x2="14" y2="10" stroke="#ffb300" stroke-width="1.5" stroke-dasharray="4,2"/><text x="17" y="13" font-size="7" fill="rgba(255,255,255,0.5)">Current path</text>
      <line x1="0" y1="20" x2="14" y2="20" stroke="#64a0e8" stroke-width="1.5" stroke-dasharray="4,2"/><text x="17" y="23" font-size="7" fill="rgba(255,255,255,0.5)">Optimized</text>
    </g>
  </svg>`;
}}

// ─── Health Chat Console ────────────────────────────────────────────────────
let _hchatDoctor = 'helen-cho';
let _hchatHistory = [];
let _hchatDoctors = [];

async function hchatInit() {{
  // Load available doctors
  try {{
    const res = await fetch('/api/health/chat/doctors').catch(() => null);
    if (res && res.ok) {{
      const d = await res.json();
      _hchatDoctors = d.doctors || [];
      _hchatRenderDoctorBar();
    }}
  }} catch(e) {{}}
}}

function _hchatRenderDoctorBar() {{
  const grid = document.getElementById('hchat-dropdown-grid');
  if (!grid || !_hchatDoctors.length) return;
  grid.innerHTML = _hchatDoctors.map(d => {{
    const active = d.agent_id === _hchatDoctor ? ' active' : '';
    const domain = (d.title || '').split('·')[0].trim() || d.specialty || '';
    return `<button class="hchat-doc-btn${{active}}" data-doctor="${{d.agent_id}}"
      onclick="hchatSelectDoctor('${{d.agent_id}}')" title="${{escHtml(d.title||'')}}">
      <span class="hchat-doc-icon">${{d.icon||'⚕️'}}</span>
      <span class="hchat-doc-info">
        <span class="hchat-doc-name">${{escHtml(d.name)}}</span>
        <span class="hchat-doc-domain">${{escHtml(domain.slice(0,22))}}</span>
      </span>
    </button>`;
  }}).join('');
}}

function hchatToggleDropdown(e) {{
  e.stopPropagation();
  const pill = document.getElementById('hchat-active-pill');
  const dd   = document.getElementById('hchat-dropdown');
  if (!pill || !dd) return;
  const isOpen = dd.classList.contains('open');
  dd.classList.toggle('open', !isOpen);
  pill.classList.toggle('open', !isOpen);
}}

function hchatCloseDropdown() {{
  const pill = document.getElementById('hchat-active-pill');
  const dd   = document.getElementById('hchat-dropdown');
  if (pill) pill.classList.remove('open');
  if (dd) dd.classList.remove('open');
}}

function hchatSelectDoctor(doctorId) {{
  _hchatDoctor = doctorId;
  hchatCloseDropdown();
  // Highlight active button
  document.querySelectorAll('#hchat-dropdown-grid .hchat-doc-btn').forEach(b => {{
    b.classList.toggle('active', b.dataset.doctor === doctorId);
  }});
  // Update pill
  const doc = _hchatDoctors.find(d => d.agent_id === doctorId);
  const name  = doc ? doc.name  : 'Helen Cho';
  const icon  = doc ? (doc.icon || '⚕️') : '🧬';
  const title = doc ? doc.title : 'Chief Medical Intelligence Officer';
  const nameEl  = document.getElementById('hchat-active-name');
  const iconEl  = document.getElementById('hchat-active-icon');
  const titleEl = document.getElementById('hchat-active-title');
  if (nameEl)  nameEl.textContent  = name;
  if (iconEl)  iconEl.textContent  = icon;
  if (titleEl) titleEl.textContent = title;
  // Update placeholder
  const inp = document.getElementById('hchat-input');
  if (inp) inp.placeholder = `Ask ${{name}}…`;
  // Show doctor intro in chat if history is empty
  const msgs = document.getElementById('hchat-messages');
  if (msgs && _hchatHistory.length === 0) {{
    msgs.innerHTML = `<div style="text-align:center;color:var(--text-3);font-size:11px;padding:32px 20px;">
      <div style="font-size:24px;margin-bottom:8px;">${{icon}}</div>
      <div style="font-weight:600;color:var(--text-2);margin-bottom:4px;">${{escHtml(name)}}</div>
      <div style="font-size:10px;margin-bottom:8px;">${{escHtml(title)}}</div>
      <div>Ask me anything about your health, labs, medications, or longevity.</div>
    </div>`;
  }}
}}

async function hchatSend() {{
  const input = document.getElementById('hchat-input');
  const btn   = document.getElementById('hchat-send-btn');
  const msgs  = document.getElementById('hchat-messages');
  if (!input || !msgs) return;
  const message = input.value.trim();
  if (!message) return;

  // Disable input
  input.disabled = true;
  if (btn) {{ btn.disabled = true; btn.style.opacity = '.5'; }}
  input.value = '';

  // Append user message
  msgs.innerHTML += `<div class="hchat-msg-user">${{escHtml(message)}}</div>`;

  // Thinking indicator
  const thinkId = 'hchat-think-' + Date.now();
  const doc = _hchatDoctors.find(d => d.agent_id === _hchatDoctor);
  const docName = doc ? doc.name : 'Helen Cho';
  msgs.innerHTML += `<div class="hchat-thinking" id="${{thinkId}}">${{escHtml(docName)}} is thinking…</div>`;
  msgs.scrollTop = msgs.scrollHeight;

  try {{
    const res = await fetch('/api/health/chat', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{
        doctor: _hchatDoctor,
        message,
        history: _hchatHistory.slice(-10), // last 10 turns
      }}),
    }});

    const data = res.ok ? await res.json() : {{ error: 'Server error ' + res.status }};

    // Remove thinking indicator
    const thinkEl = document.getElementById(thinkId);
    if (thinkEl) thinkEl.remove();

    if (data.error) {{
      msgs.innerHTML += `<div class="hchat-msg-doctor"><div class="hchat-msg-doctor-name">⚠ System</div><div style="color:var(--red,#ef4444);">${{escHtml(data.error)}}</div></div>`;
    }} else {{
      const reply = data.reply || '';
      const icon = doc ? (doc.icon || '⚕️') : '🧬';
      msgs.innerHTML += `<div class="hchat-msg-doctor">
        <div class="hchat-msg-doctor-name">${{icon}} ${{escHtml(data.doctor_name || docName)}}</div>
        <div class="hchat-msg-body">${{mdToHtml(reply)}}</div>
      </div>`;
      // Update history
      _hchatHistory.push({{ role: 'user', content: message }});
      _hchatHistory.push({{ role: 'assistant', content: reply }});
    }}
  }} catch(e) {{
    const thinkEl = document.getElementById(thinkId);
    if (thinkEl) thinkEl.remove();
    msgs.innerHTML += `<div class="hchat-msg-doctor"><div class="hchat-msg-doctor-name">⚠ Error</div><div style="color:var(--red,#ef4444);">Connection failed — check service status.</div></div>`;
  }}

  msgs.scrollTop = msgs.scrollHeight;
  input.disabled = false;
  if (btn) {{ btn.disabled = false; btn.style.opacity = '1'; }}
  input.focus();
}}

// ─── Health Metric Strip ────────────────────────────────────────────────────
function _renderHealthMetricStrip(summary, bp) {{
  // Live data from API
  const m = summary.metrics || {{}};
  const r = summary.readiness || {{}};
  if (m.hrv) {{
    const el = document.getElementById('hm-hrv');
    if (el) el.textContent = Math.round(m.hrv);
  }}
  if (m.steps) {{
    const el = document.getElementById('hm-steps');
    if (el) el.textContent = Number(m.steps).toLocaleString();
  }}
  if (m.sleep_hours) {{
    const el = document.getElementById('hm-sleep');
    if (el) el.textContent = m.sleep_hours.toFixed(1);
  }}
  if (m.weight) {{
    const el = document.getElementById('hm-weight');
    if (el) el.textContent = Math.round(m.weight * 2.205); // kg → lbs
  }}
  // BP from bp readings
  if (bp && bp.latest) {{
    const bpEl = document.getElementById('hm-bp');
    const arrEl = document.getElementById('hm-bp-arrow');
    if (bpEl) {{
      bpEl.textContent = bp.latest.systolic + '/' + bp.latest.diastolic;
      const sys = bp.latest.systolic;
      const col = sys < 120 ? 'var(--green)' : sys < 130 ? 'var(--blue)' : sys < 140 ? 'var(--amber)' : 'var(--red,#ef4444)';
      bpEl.style.color = col;
      if (arrEl) {{ arrEl.textContent = sys < 130 ? '↓' : sys < 140 ? '→' : '↑'; arrEl.style.color = col; }}
    }}
  }}
}}

// ─── Health Sparklines ──────────────────────────────────────────────────────
function _buildHealthSparkline(points, color) {{
  if (!points || points.length < 2) return '<div style="height:50px;display:flex;align-items:center;justify-content:center;font-size:9px;color:var(--text-3);">Not enough data</div>';
  const vals = points.map(p => p.y);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const W = 200, H = 50, PAD = 6;
  const coords = points.map((p, i) => [
    PAD + (i / (points.length - 1)) * (W - PAD * 2),
    H - PAD - ((p.y - min) / range) * (H - PAD * 2)
  ]);
  const path = coords.map((c, i) => (i === 0 ? `M${{c[0]}},${{c[1]}}` : `L${{c[0]}},${{c[1]}}`)).join(' ');
  const area = `${{path}} L${{coords[coords.length-1][0]}},${{H}} L${{coords[0][0]}},${{H}} Z`;
  const labels = points.map((p, i) => `<text x="${{coords[i][0]}}" y="${{H+9}}" text-anchor="middle" font-size="7" fill="rgba(255,255,255,0.35)">${{p.x}}</text>`).join('');
  const last = coords[coords.length-1];
  const gid = 'sg' + color.replace('#','').replace('var(--','').replace(')','');
  return `<svg viewBox="0 0 ${{W}} ${{H+12}}" style="width:100%;height:60px;overflow:visible;">
    <defs>
      <linearGradient id="${{gid}}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${{color}}" stop-opacity=".2"/>
        <stop offset="100%" stop-color="${{color}}" stop-opacity=".02"/>
      </linearGradient>
    </defs>
    <path d="${{area}}" fill="url(#${{gid}})"/>
    <path d="${{path}}" fill="none" stroke="${{color}}" stroke-width="2" stroke-linejoin="round"/>
    <circle cx="${{last[0]}}" cy="${{last[1]}}" r="3.5" fill="${{color}}"/>
    ${{labels}}
  </svg>`;
}}

/* Compact 36px sparkline — just the trend, no labels */
function _buildMiniSparkline(points, color) {{
  if (!points || points.length < 2) return '';
  const vals = points.map(p => p.y);
  const min = Math.min(...vals), max = Math.max(...vals);
  const range = max - min || 1;
  const W = 200, H = 30, PAD = 3;
  const coords = points.map((p, i) => [
    PAD + (i / (points.length - 1)) * (W - PAD * 2),
    H - PAD - ((p.y - min) / range) * (H - PAD * 2)
  ]);
  const path = coords.map((c, i) => (i === 0 ? `M${{c[0]}},${{c[1]}}` : `L${{c[0]}},${{c[1]}}`)).join(' ');
  const area = `${{path}} L${{coords[coords.length-1][0]}},${{H}} L${{PAD}},${{H}} Z`;
  const last = coords[coords.length - 1];
  const gid  = 'ms' + (Math.random() * 1e6 | 0);
  return `<svg viewBox="0 0 ${{W}} ${{H}}" style="width:100%;height:36px;" preserveAspectRatio="none">
    <defs><linearGradient id="${{gid}}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${{color}}" stop-opacity=".3"/>
      <stop offset="100%" stop-color="${{color}}" stop-opacity=".02"/>
    </linearGradient></defs>
    <path d="${{area}}" fill="url(#${{gid}})"/>
    <path d="${{path}}" fill="none" stroke="${{color}}" stroke-width="1.8" stroke-linejoin="round"/>
    <circle cx="${{last[0]}}" cy="${{last[1]}}" r="2.5" fill="${{color}}"/>
  </svg>`;
}}

async function _renderHealthSparklines() {{
  // ── Static lab results (known historical values) ──
  const LAB_DATA = {{
    a1c:   {{ points: [{{y:10.2,x:"'21"}},{{y:7.1,x:"mid"}},{{y:6.3,x:"'23"}},{{y:5.9,x:"'24"}},{{y:7.3,x:"'26"}}], color: '#d29922' }},
    ldl:   {{ points: [{{y:99,x:"'21"}},{{y:138,x:"'24"}},{{y:146,x:"'25"}},{{y:156,x:"'26"}}], color: '#ef4444' }},
    egfr:  {{ points: [{{y:98,x:"'20"}},{{y:91,x:"'22"}},{{y:87,x:"'26"}}], color: '#d29922' }},
    kplus: {{ points: [{{y:5.4,x:"'25"}},{{y:4.5,x:"'26"}}], color: '#22c55e' }},
  }};
  // Metric strip (larger sparklines)
  Object.entries(LAB_DATA).forEach(([key, cfg]) => {{
    const el = document.getElementById('spark-' + (key === 'kplus' ? 'kplus' : key));
    if (el) el.innerHTML = _buildHealthSparkline(cfg.points, cfg.color);
  }});
  // Lab Trends compact sparklines (unique IDs — no collision with strip)
  Object.entries(LAB_DATA).forEach(([key, cfg]) => {{
    const el = document.getElementById('spark-lab-' + key);
    if (el) el.innerHTML = _buildMiniSparkline(cfg.points, cfg.color);
  }});

  // ── Live metrics from DB history (last 30 days) ──
  try {{
    const res = await fetch('/api/health/history?days=30').catch(() => null);
    if (!res || !res.ok) return;
    const {{history}} = await res.json();
    if (!history || !history.length) return;

    // Sort ascending by date
    const rows = [...history].sort((a, b) => (a.date || '').localeCompare(b.date || ''));

    // Helper: extract daily series for a column
    const series = (col) => rows
      .map((r, i) => ({{y: parseFloat(r[col]), x: r.date ? r.date.slice(5) : String(i)}}))
      .filter(p => !isNaN(p.y) && p.y > 0);

    const LIVE_SPARKS = {{
      'spark-hrv':    {{ s: series('hrv'),         color: '#3b82f6' }},
      'spark-steps':  {{ s: series('steps'),        color: '#3b82f6' }},
      'spark-sleep':  {{ s: series('sleep_hours'),  color: '#3b82f6' }},
      'spark-weight': {{ s: series('weight'),       color: '#22c55e' }},
    }};

/* ═══ FINANCE SETUP MODAL ═══════════════════════════════════ */
function openFinanceSetup() {{
  const ov = document.getElementById('finance-setup-overlay');
  if (!ov) return;
  ov.classList.remove('hidden');
  loadFinanceSetupData();
}}
function closeFinanceSetup(e) {{
  if (e && e.target !== document.getElementById('finance-setup-overlay')) return;
  document.getElementById('finance-setup-overlay')?.classList.add('hidden');
}}
function switchFinanceTab(tab) {{
  ['accounts','streams','goals'].forEach(t => {{
    document.getElementById('finance-panel-' + t)?.classList.toggle('active', t === tab);
  }});
  document.querySelectorAll('.finance-tab').forEach((btn,i) =>
    btn.classList.toggle('active', ['accounts','streams','goals'][i] === tab));
}}
async function loadFinanceSetupData() {{
  await Promise.all([_loadFiAccounts(), _loadFiStreams(), _loadFiGoals()]);
}}
async function _loadFiAccounts() {{
  const el = document.getElementById('finance-accounts-list');
  if (!el) return;
  try {{
    const accounts = await fetch('/api/finance/accounts').then(r=>r.json());
    if (!Array.isArray(accounts)||!accounts.length) {{ el.innerHTML='<div class="finance-empty">No accounts added yet.</div>'; return; }}
    const fmt = n=>'$'+parseFloat(n||0).toLocaleString('en-US',{{maximumFractionDigits:0}});
    const lbl = {{checking:'Checking',savings:'Savings',investment:'Investment',retirement:'Retirement',credit:'Credit Card',loan:'Loan',other:'Other'}};
    el.innerHTML = accounts.map(a=>`<div class="finance-row">
      <div style="flex:1;min-width:0;"><div class="finance-row-name">${{escHtml(a.name)}}</div>
      <div class="finance-row-sub">${{lbl[a.account_type]||a.account_type}}${{a.institution?' · '+escHtml(a.institution):''}}</div></div>
      <div class="finance-row-val" style="color:${{a.account_type==='credit'||a.account_type==='loan'?'var(--red)':'var(--text-1)'}}">${{fmt(a.balance)}}</div>
      <button class="finance-row-del" onclick="deleteFinanceAccount('${{a.account_id}}','${{escHtml(a.name).replace(/'/g,'')}}')" title="Remove">✕</button>
    </div>`).join('');
  }} catch(e) {{ el.innerHTML='<div class="finance-empty">Could not load accounts.</div>'; }}
}}
async function loadFinanceAccounts() {{ await _loadFiAccounts(); }}
async function submitFinanceAccount() {{
  const name=document.getElementById('fi-acct-name')?.value.trim();
  const type=document.getElementById('fi-acct-type')?.value;
  const inst=document.getElementById('fi-acct-institution')?.value.trim();
  const bal=parseFloat(document.getElementById('fi-acct-balance')?.value||'');
  if (!name||isNaN(bal)) {{ showToast('Name and balance are required','warn'); return; }}
  const res=await fetch('/api/finance/accounts',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{name,account_type:type,institution:inst,balance:bal}})}});
  if (!res.ok) {{ showToast((await res.json()).detail||'Error','warn'); return; }}
  ['fi-acct-name','fi-acct-institution','fi-acct-balance'].forEach(id=>{{ const el=document.getElementById(id); if(el) el.value=''; }});
  await _loadFiAccounts(); showToast('Account added','ok'); setTimeout(()=>loadFiskCard(),600);
}}
async function deleteFinanceAccount(id,name) {{
  if (!confirm('Remove "'+name+'"?')) return;
  await fetch('/api/finance/accounts/'+encodeURIComponent(id),{{method:'DELETE'}});
  await _loadFiAccounts(); showToast('Account removed','ok'); setTimeout(()=>loadFiskCard(),600);
}}
async function _loadFiStreams() {{
  const el=document.getElementById('finance-streams-list');
  if (!el) return;
  try {{
    const streams=await fetch('/api/finance/passive-income/streams').then(r=>r.json());
    if (!Array.isArray(streams)||!streams.length) {{ el.innerHTML='<div class="finance-empty">No passive income streams yet.</div>'; return; }}
    const fmt=n=>'$'+parseFloat(n||0).toLocaleString('en-US',{{maximumFractionDigits:0}});
    const lbl={{book_royalty:'Book Royalty',course_revenue:'Course',dividend:'Dividends',rental:'Rental',affiliate:'Affiliate',interest:'Interest',consulting:'Consulting',other:'Other'}};
    el.innerHTML=streams.map(s=>`<div class="finance-row">
      <div style="flex:1;min-width:0;"><div class="finance-row-name">${{escHtml(s.name)}}</div>
      <div class="finance-row-sub">${{lbl[s.stream_type]||s.stream_type}}${{s.platform?' · '+escHtml(s.platform):''}}</div></div>
      <div class="finance-row-val" style="color:var(--green)">${{fmt(s.monthly_average)}}<span style="font-size:9px;color:var(--text-3);">/mo</span></div>
      <button class="finance-row-del" onclick="deleteFinanceStream('${{s.stream_id}}','${{escHtml(s.name).replace(/'/g,'')}}')" title="Remove">✕</button>
    </div>`).join('');
  }} catch(e) {{ el.innerHTML='<div class="finance-empty">Could not load streams.</div>'; }}
}}
async function loadFinanceStreams() {{ await _loadFiStreams(); }}
async function submitFinanceStream() {{
  const name=document.getElementById('fi-stream-name')?.value.trim();
  const type=document.getElementById('fi-stream-type')?.value;
  const monthly=parseFloat(document.getElementById('fi-stream-monthly')?.value||'');
  const platform=document.getElementById('fi-stream-platform')?.value.trim();
  if (!name||isNaN(monthly)) {{ showToast('Name and monthly amount are required','warn'); return; }}
  const res=await fetch('/api/finance/passive-income/streams',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{name,stream_type:type,monthly_average:monthly,platform}})}});
  if (!res.ok) {{ showToast((await res.json()).detail||'Error','warn'); return; }}
  ['fi-stream-name','fi-stream-monthly','fi-stream-platform'].forEach(id=>{{ const el=document.getElementById(id); if(el) el.value=''; }});
  await _loadFiStreams(); showToast('Stream added','ok'); setTimeout(()=>loadFiskCard(),600);
}}
async function deleteFinanceStream(id,name) {{
  if (!confirm('Remove "'+name+'"?')) return;
  await fetch('/api/finance/passive-income/streams/'+encodeURIComponent(id),{{method:'DELETE'}});
  await _loadFiStreams(); showToast('Stream removed','ok'); setTimeout(()=>loadFiskCard(),600);
}}
async function _loadFiGoals() {{
  const el=document.getElementById('finance-goals-list');
  if (!el) return;
  try {{
    const d=await fetch('/api/finance/goals').then(r=>r.json());
    const goals=d.goals||d||[];
    if (!goals.length) {{ el.innerHTML='<div class="finance-empty">No goals added yet.</div>'; return; }}
    const fmt=n=>'$'+parseFloat(n||0).toLocaleString('en-US',{{maximumFractionDigits:0}});
    const pct=g=>g.target_amount>0?Math.round((g.current_amount/g.target_amount)*100):0;
    el.innerHTML=goals.map(g=>`<div class="finance-row" style="flex-direction:column;align-items:stretch;gap:6px;">
      <div style="display:flex;align-items:center;gap:8px;">
        <div style="flex:1;min-width:0;"><div class="finance-row-name">${{escHtml(g.title)}}</div>
        <div class="finance-row-sub">${{fmt(g.current_amount)}} of ${{fmt(g.target_amount)}}${{g.target_date?' · by '+g.target_date:''}}</div></div>
        <div class="finance-row-val">${{pct(g)}}%</div>
        <button class="finance-row-del" onclick="deleteFinanceGoal('${{g.goal_id}}','${{escHtml(g.title).replace(/'/g,'')}}')" title="Remove">✕</button>
      </div>
      <div style="height:3px;background:rgba(255,255,255,0.08);border-radius:2px;">
        <div style="height:100%;width:${{Math.min(pct(g),100)}}%;background:var(--blue);border-radius:2px;"></div>
      </div>
    </div>`).join('');
  }} catch(e) {{ el.innerHTML='<div class="finance-empty">Could not load goals.</div>'; }}
}}
async function loadFinanceGoals() {{ await _loadFiGoals(); }}
async function submitFinanceGoal() {{
  const title=document.getElementById('fi-goal-title')?.value.trim();
  const type=document.getElementById('fi-goal-type')?.value;
  const target=parseFloat(document.getElementById('fi-goal-target')?.value||'');
  const current=parseFloat(document.getElementById('fi-goal-current')?.value||'0');
  const date=document.getElementById('fi-goal-date')?.value;
  if (!title||isNaN(target)) {{ showToast('Title and target amount are required','warn'); return; }}
  const res=await fetch('/api/finance/goals',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{title,goal_type:type,target_amount:target,current_amount:current||0,target_date:date||''}})}});
  if (!res.ok) {{ showToast((await res.json()).detail||'Error','warn'); return; }}
  ['fi-goal-title','fi-goal-target','fi-goal-current','fi-goal-date'].forEach(id=>{{ const el=document.getElementById(id); if(el) el.value=''; }});
  await _loadFiGoals(); showToast('Goal added','ok'); setTimeout(()=>loadFiskCard(),600);
}}
async function deleteFinanceGoal(id,name) {{
  if (!confirm('Remove "'+name+'"?')) return;
  await fetch('/api/finance/goals/'+encodeURIComponent(id),{{method:'DELETE'}});
  await _loadFiGoals(); showToast('Goal removed','ok'); setTimeout(()=>loadFiskCard(),600);
}}
/* ════════════════════════════════════════════════════════════ */


    Object.entries(LIVE_SPARKS).forEach(([id, cfg]) => {{
      if (cfg.s.length < 2) return;
      const el = document.getElementById(id);
      if (el) el.innerHTML = _buildHealthSparkline(cfg.s, cfg.color);
    }});

    // BP sparkline — use systolic from bp_readings via /api/health/bp
    try {{
      const bpRes = await fetch('/api/health/bp').catch(() => null);
      if (bpRes && bpRes.ok) {{
        const bpData = await bpRes.json();
        const bpRows = (bpData.readings || []).slice(-20);
        if (bpRows.length >= 2) {{
          const bpPts = bpRows.map((r, i) => ({{
            y: r.systolic || 0,
            x: r.reading_date ? r.reading_date.slice(5, 10) : String(i),
          }})).filter(p => p.y > 0);
          const el = document.getElementById('spark-bp');
          if (el && bpPts.length >= 2)
            el.innerHTML = _buildHealthSparkline(bpPts, '#22c55e');
        }}
      }}
    }} catch(e) {{}}
  }} catch(e) {{}}
}}

// ─── Sam Wilson Daily Protocol ──────────────────────────────────────────────
let _samProtocol = null;
let _samHistory  = [];
let _samChecked  = new Set();
let _samChatMode         = 'chat';   // 'chat' | 'food' | 'interview'
let _samInterviewStep    = 0;
let _samFoodDate         = null;     // null = today

/* ─── SAM WILSON OVERVIEW CARD ─────────────────────────────────────── */
async function loadSamOverviewCard() {{
  const content = document.getElementById('sam-ov-content');
  const badge   = document.getElementById('sam-ov-streak-badge');
  if (!content) return;

  const isEvening = new Date().getHours() >= 16;
  try {{
    const [mRes, pRes] = await Promise.all([
      fetch('/api/health/sam/morning-checkin'),
      fetch('/api/health/sam/daily'),
    ]);
    const m  = mRes.ok  ? await mRes.json() : {{}};
    const pd = pRes.ok  ? await pRes.json() : {{}};
    const p  = pd.protocol || {{}};
    const streak = (m.streak || pd.streak || {{}}).streak || 0;

    if (badge) {{
      if (streak > 0) {{ badge.textContent = '🔥 ' + streak + 'd'; badge.style.display = ''; }}
      else badge.style.display = 'none';
    }}

    if (!isEvening) {{
      // ── Morning mode ───────────────────────────────────────────────
      const readiness = m.readiness != null ? m.readiness : null;
      const hrv = m.hrv;
      const sleep = m.sleep_hours != null ? parseFloat(m.sleep_hours).toFixed(1) : null;
      const mv = p.movement || {{}};
      const focus = mv.primary || m.focus_primary || 'Zone 2 cardio';
      const watch = (p.nutrition || {{}}).watch || m.nutrition_watch;

      content.innerHTML = `
        <div style="font-size:12px;font-style:italic;color:var(--blue);margin-bottom:10px;line-height:1.4;">
          "${{escHtml(p.greeting || m.greeting || 'On your left, brother.')}}"
        </div>
        ${{readiness || hrv || sleep ? `<div style="display:flex;gap:12px;margin-bottom:10px;">
          ${{readiness ? `<div style="text-align:center;">
            <div style="font-size:20px;font-weight:700;font-family:var(--font-mono);color:var(--amber);">${{readiness}}</div>
            <div style="font-size:8px;font-weight:700;text-transform:uppercase;color:var(--text-3);">Ready</div>
          </div><div style="width:1px;background:rgba(255,255,255,0.12);margin:0 2px;"></div>` : ''}}
          ${{hrv ? `<div style="text-align:center;">
            <div style="font-size:20px;font-weight:700;font-family:var(--font-mono);color:var(--text-1);">${{hrv}}</div>
            <div style="font-size:8px;font-weight:700;text-transform:uppercase;color:var(--text-3);">HRV ms</div>
          </div><div style="width:1px;background:rgba(255,255,255,0.12);margin:0 2px;"></div>` : ''}}
          ${{sleep ? `<div style="text-align:center;">
            <div style="font-size:20px;font-weight:700;font-family:var(--font-mono);color:var(--text-1);">${{sleep}}</div>
            <div style="font-size:8px;font-weight:700;text-transform:uppercase;color:var(--text-3);">Sleep h</div>
          </div>` : ''}}
        </div>` : ''}}
        <div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.10);border-radius:8px;padding:8px 10px;margin-bottom:8px;">
          <div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--text-3);margin-bottom:3px;">💪 Today</div>
          <div style="font-size:12px;font-weight:600;color:var(--text-1);">${{escHtml(focus)}}</div>
        </div>
        ${{watch ? `<div style="font-size:11px;color:var(--amber);background:rgba(217,119,6,.10);border:1px solid rgba(217,119,6,.25);border-radius:6px;padding:5px 8px;">⚠ ${{escHtml(watch)}}</div>` : ''}}
        <div style="margin-top:10px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
          <div id="sam-ov-score-row" style="margin-bottom:8px;display:none;">
          <span id="sam-ov-score-badge" style="font-family:var(--font-mono);font-size:13px;font-weight:800;"></span>
          <span id="sam-ov-score-label" style="font-size:10px;color:var(--text-3);margin-left:6px;"></span>
        </div>
        <div style="margin-top:10px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
          <button onclick="openSamJournal()"
            style="padding:6px 14px;border-radius:8px;background:rgba(99,102,241,0.20);border:1px solid rgba(99,102,241,0.40);
                   color:#a5b4fc;font-size:11px;font-weight:700;cursor:pointer;">
            📓 Journal Today
          </button>
          <span style="font-size:11px;color:var(--blue);cursor:pointer;" onclick="switchView('health')">Full protocol →</span>
        </div>
      `;
    }} else {{
      // ── Evening mode: Daily Journal is the primary CTA ─────────────
      // Check if journal was already done today
      const todayStr = _localDateStr();
      let journalDone = false;
      let journalSummary = null;
      try {{
        const jRes = await fetch('/api/health/sam/journal?days=1').catch(() => null);
        if (jRes && jRes.ok) {{
          const jData = await jRes.json();
          if (jData.length && jData[0].date === todayStr) {{
            journalDone = true;
            journalSummary = jData[0];
          }}
        }}
      }} catch(e) {{}}

      if (journalDone && journalSummary) {{
        // Show what was logged today
        const ex = (journalSummary.extracted || {{}}).exercise || [];
        const exLine = ex.length ? ex.map(e => `${{e.type||'exercise'}}${{e.duration_min?' '+e.duration_min+'min':''}}`).join(', ') : null;
        const protein = Math.round(journalSummary.total_protein_g || 0);
        const adh = (journalSummary.adherence_items || []).length;
        content.innerHTML = `
          <div style="font-size:11px;font-style:italic;color:var(--blue);margin-bottom:10px;line-height:1.4;">"Solid entry today, brother. Keep stacking."</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">
            <div style="background:rgba(255,255,255,0.05);border-radius:8px;padding:8px 10px;text-align:center;">
              <div style="font-size:18px;font-weight:700;font-family:var(--font-mono);color:var(--blue);">${{protein}}g</div>
              <div style="font-size:8px;text-transform:uppercase;letter-spacing:.06em;color:var(--text-3);">Protein</div>
            </div>
            <div style="background:rgba(255,255,255,0.05);border-radius:8px;padding:8px 10px;text-align:center;">
              <div style="font-size:18px;font-weight:700;font-family:var(--font-mono);color:var(--green);">${{adh}}/6</div>
              <div style="font-size:8px;text-transform:uppercase;letter-spacing:.06em;color:var(--text-3);">Protocol</div>
            </div>
          </div>
          ${{exLine ? `<div style="font-size:11px;color:var(--text-2);margin-bottom:8px;">💪 ${{escHtml(exLine)}}</div>` : ''}}
          <button onclick="openSamJournal()"
            style="width:100%;padding:7px;border-radius:8px;background:rgba(99,102,241,0.12);
                   border:1px solid rgba(99,102,241,0.30);color:#a5b4fc;font-size:11px;font-weight:700;cursor:pointer;">
            📓 Add More →
          </button>`;
      }} else {{
        content.innerHTML = `
          <div style="font-size:12px;font-style:italic;color:var(--blue);margin-bottom:12px;line-height:1.4;">"Tell me everything about today, brother."</div>
          <button onclick="openSamJournal()"
            style="width:100%;padding:10px;border-radius:10px;
                   background:linear-gradient(135deg,rgba(99,102,241,0.25),rgba(59,130,246,0.20));
                   border:1px solid rgba(99,102,241,0.45);
                   color:#a5b4fc;font-size:13px;font-weight:700;cursor:pointer;letter-spacing:.01em;">
            📓 Talk to Sam About Today
          </button>
          <div style="margin-top:10px;font-size:10px;color:var(--text-3);text-align:center;">
            exercise · food · water · mood · stress · sleep — everything
          </div>`;
      }}
    }}
  }} catch(e) {{
    if (content) content.innerHTML = '<div style="font-size:11px;color:var(--text-3);">On your left.</div>';
  }}
}}

function samOvToggle(label) {{
  const cb = label.querySelector('input[type=checkbox]');
  if (cb) cb.checked = !cb.checked;
  const txt = label.querySelector('span');
  if (txt) txt.style.textDecoration = cb && cb.checked ? 'line-through' : '';
}}

async function submitSamOvCheckin(btn) {{
  const checks = document.querySelectorAll('#sam-ov-list input[type=checkbox]');
  const labels = document.querySelectorAll('#sam-ov-list label span');
  const completed = [];
  checks.forEach((cb, i) => {{ if (cb.checked) completed.push(labels[i]?.textContent?.trim() || 'item'); }});
  if (btn) {{ btn.textContent = 'Logging…'; btn.disabled = true; }}
  try {{
    const res = await fetch('/api/health/sam/evening-checkin', {{
      method: 'POST',
      headers: {{'Content-Type':'application/json'}},
      body: JSON.stringify({{completed, notes: ''}}),
    }});
    const d = await res.json();
    const replyEl = document.getElementById('sam-ov-reply');
    if (replyEl) {{
      replyEl.textContent = d.reply || '';
      replyEl.style.display = 'block';
    }}
    const pct = d.adherence_pct || 0;
    if (btn) {{ btn.textContent = `✓ ${{pct}}% logged`; }}
  }} catch(e) {{
    if (btn) {{ btn.textContent = 'Log My Day →'; btn.disabled = false; }}
  }}
}}

/* ═══════════════════════════════════════════════════════════════════
   DINING VIEW
   ═══════════════════════════════════════════════════════════════════ */

let _diningLoaded = false;

function _diningStarColor(r) {{
  if (r >= 4.5) return '#4ade80';
  if (r >= 4.0) return '#facc15';
  return '#fb923c';
}}

function _diningPriceLabel(p) {{
  const map = {{'$':'Inexpensive','$$':'Moderate','$$$':'Pricey','$$$$':'Upscale'}};
  return map[p] || '';
}}

function _diningRestaurantCard(p) {{
  const starColor = _diningStarColor(p.rating || 0);
  const openBadge = p.open_now === true
    ? '<span style="font-size:10px;background:rgba(74,222,128,0.15);color:#4ade80;border:1px solid rgba(74,222,128,0.3);border-radius:6px;padding:2px 7px;">OPEN</span>'
    : p.open_now === false
    ? '<span style="font-size:10px;background:rgba(248,113,113,0.12);color:#f87171;border:1px solid rgba(248,113,113,0.25);border-radius:6px;padding:2px 7px;">CLOSED</span>'
    : '';
  const mapsUrl = 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(p.name + ' ' + p.address);
  return `
    <div class="card" style="cursor:pointer;" onclick="openDiningDetail('${{escHtml(p.place_id)}}','${{escHtml(p.name.replace(/'/g,"&#39;"))}}')">
      <div class="card-inner" style="padding:16px;">
        <div style="display:flex;align-items:flex-start;gap:12px;">
          <div style="flex:1;min-width:0;">
            <div style="font-size:14px;font-weight:700;color:var(--text-1);margin-bottom:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${{escHtml(p.name)}}</div>
            <div style="font-size:11px;color:var(--text-3);margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${{escHtml(p.address)}}</div>
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
              ${{openBadge}}
              <span style="font-size:11px;color:var(--text-3);">${{p.distance_mi}} mi away</span>
              ${{p.price ? '<span style="font-size:11px;color:var(--text-3);">' + escHtml(p.price) + ' · ' + escHtml(_diningPriceLabel(p.price)) + '</span>' : ''}}
            </div>
          </div>
          <div style="text-align:center;flex-shrink:0;">
            <div style="font-size:22px;font-weight:800;color:${{starColor}};">${{p.rating || '—'}}</div>
            <div style="font-size:10px;color:var(--text-3);">${{(p.review_count||0).toLocaleString()}} reviews</div>
            <button onclick="event.stopPropagation();toggleDiningFav('${{escHtml(p.place_id)}}','${{escHtml(p.name.replace(/'/g,"&#39;"))}}','${{escHtml(p.address.replace(/'/g,"&#39;"))}}','${{p.rating}}')"
              style="margin-top:6px;background:none;border:none;cursor:pointer;font-size:16px;color:var(--text-3);"
              id="fav-btn-${{p.place_id}}" title="Save favorite">♡</button>
          </div>
        </div>
      </div>
    </div>`;
}}

async function loadDiningView() {{
  if (_diningLoaded) return;
  _diningLoaded = true;
  await Promise.all([loadDiningSamPicks(), reloadDiningView()]);
}}

async function loadDiningSamPicks() {{
  const el = document.getElementById('dining-sam-picks');
  if (!el) return;
  try {{
    const d = await fetch('/api/dining/recommend?limit=3').then(r => r.json());
    const picks = d.recommendations || [];
    if (!picks.length) {{ el.innerHTML = '<span style="color:var(--text-3);font-size:12px;">No picks right now.</span>'; return; }}
    el.innerHTML = picks.map(p => `
      <div style="display:inline-flex;align-items:center;gap:8px;background:var(--surface-hi);border:1px solid var(--border);border-radius:10px;padding:8px 14px;margin:4px 8px 4px 0;cursor:pointer;"
           onclick="openDiningDetail('${{escHtml(p.place_id)}}','${{escHtml(p.name.replace(/'/g,"&#39;"))}}')">
        <span style="font-weight:600;font-size:13px;color:var(--text-1);">${{escHtml(p.name)}}</span>
        <span style="font-size:12px;color:var(--hue);">${{p.rating}}★</span>
        <span style="font-size:11px;color:var(--text-3);">${{p.distance_mi}} mi</span>
      </div>`).join('');
  }} catch(e) {{
    if (el) el.innerHTML = '<span style="color:var(--text-3);font-size:12px;">Could not load Sam picks.</span>';
  }}
}}

async function reloadDiningView() {{
  const el = document.getElementById('dining-results');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text-3);font-size:13px;padding:20px;text-align:center;">Loading restaurants…</div>';

  const cuisine    = document.getElementById('dining-cuisine-filter')?.value || 'any';
  const openNow    = document.getElementById('dining-open-now')?.checked || false;
  const radius     = document.getElementById('dining-radius-filter')?.value || '10';
  const minRating  = document.getElementById('dining-rating-filter')?.value || '4.0';

  try {{
    const params = new URLSearchParams({{cuisine, open_now: openNow, radius_miles: radius, min_rating: minRating, limit: 20}});
    const d = await fetch('/api/dining/nearby?' + params).then(r => r.json());
    const spots = d.restaurants || [];
    if (!spots.length) {{
      el.innerHTML = '<div style="color:var(--text-3);font-size:13px;padding:20px;text-align:center;">No restaurants found. Try relaxing the filters.</div>';
      return;
    }}
    el.innerHTML = spots.map(p => _diningRestaurantCard(p)).join('');
    // Mark existing favorites
    loadDiningFavBtns();
  }} catch(e) {{
    el.innerHTML = '<div style="color:var(--red);font-size:13px;padding:20px;">Failed to load restaurants: ' + escHtml(e.message) + '</div>';
  }}
}}

async function loadDiningFavBtns() {{
  try {{
    const d = await fetch('/api/dining/favorites').then(r => r.json());
    const ids = new Set((d.favorites || []).map(f => f.place_id));
    ids.forEach(id => {{
      const btn = document.getElementById('fav-btn-' + id);
      if (btn) {{ btn.textContent = '❤'; btn.style.color = '#f87171'; }}
    }});
  }} catch(e) {{}}
}}

async function toggleDiningFav(placeId, name, address, rating) {{
  try {{
    const d = await fetch('/api/dining/favorite', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{place_id: placeId, name, address, rating: parseFloat(rating)}})
    }}).then(r => r.json());
    const btn = document.getElementById('fav-btn-' + placeId);
    if (btn) {{
      btn.textContent = d.action === 'added' ? '❤' : '♡';
      btn.style.color = d.action === 'added' ? '#f87171' : 'var(--text-3)';
    }}
    showToast(d.action === 'added' ? 'Saved to favorites' : 'Removed from favorites');
  }} catch(e) {{ showToast('Could not update favorites'); }}
}}

async function loadDiningFavorites() {{
  const panel = document.getElementById('dining-favorites-panel');
  const list  = document.getElementById('dining-favorites-list');
  if (!panel || !list) return;
  panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
  if (panel.style.display === 'none') return;
  try {{
    const d = await fetch('/api/dining/favorites').then(r => r.json());
    const favs = d.favorites || [];
    if (!favs.length) {{ list.innerHTML = '<div style="color:var(--text-3);font-size:13px;padding:8px;">No favorites saved yet.</div>'; return; }}
    list.innerHTML = favs.map(f => `
      <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--border);">
        <div style="flex:1;">
          <div style="font-size:13px;font-weight:600;color:var(--text-1);">${{escHtml(f.name)}}</div>
          <div style="font-size:11px;color:var(--text-3);">${{escHtml(f.address)}}</div>
        </div>
        <span style="color:var(--hue);font-size:13px;">${{f.rating || ''}}★</span>
        <button onclick="toggleDiningFav('${{escHtml(f.place_id)}}','${{escHtml(f.name.replace(/'/g,"&#39;"))}}','${{escHtml(f.address.replace(/'/g,"&#39;"))}}','${{f.rating}}')"
          style="background:none;border:none;cursor:pointer;color:#f87171;font-size:16px;">❤</button>
      </div>`).join('');
  }} catch(e) {{ list.innerHTML = '<div style="color:var(--red);font-size:13px;">Failed to load favorites.</div>'; }}
}}

async function openDiningDetail(placeId, name) {{
  const sheet = document.getElementById('dining-detail-sheet');
  const inner = document.getElementById('dining-detail-inner');
  if (!sheet || !inner) return;
  inner.innerHTML = `<div style="text-align:center;padding:20px;color:var(--text-3);">Loading ${{escHtml(name)}}…</div>`;
  sheet.style.display = 'flex';
  cardInteract('dining', 'expand');
  try {{
    const d = await fetch('/api/dining/details/' + encodeURIComponent(placeId)).then(r => r.json());
    const hours = (d.opening_hours?.weekday_text || []).map(h => `<div style="font-size:12px;color:var(--text-2);">${{escHtml(h)}}</div>`).join('') || '<div style="font-size:12px;color:var(--text-3);">Hours unavailable</div>';
    const mapsUrl = 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent((d.name || name) + ' ' + (d.formatted_address || ''));
    inner.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px;">
        <div>
          <div style="font-size:20px;font-weight:800;color:var(--text-1);">${{escHtml(d.name || name)}}</div>
          <div style="font-size:12px;color:var(--text-3);margin-top:3px;">${{escHtml(d.formatted_address || '')}}</div>
        </div>
        <button onclick="closeDiningDetail()" style="background:none;border:none;cursor:pointer;font-size:20px;color:var(--text-3);">✕</button>
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px;">
        ${{d.rating ? '<span style="font-size:18px;font-weight:700;color:' + _diningStarColor(d.rating) + ';">' + d.rating + '★</span>' : ''}}
        ${{d.user_ratings_total ? '<span style="font-size:12px;color:var(--text-3);">' + d.user_ratings_total.toLocaleString() + ' reviews</span>' : ''}}
        ${{d.price_level ? '<span style="font-size:12px;color:var(--text-2);">' + '$'.repeat(d.price_level) + '</span>' : ''}}
      </div>
      ${{d.formatted_phone_number ? '<div style="margin-bottom:10px;"><a href="tel:' + escHtml(d.formatted_phone_number) + '" style="color:var(--hue);font-size:13px;">📞 ' + escHtml(d.formatted_phone_number) + '</a></div>' : ''}}
      ${{d.website ? '<div style="margin-bottom:14px;"><a href="' + escHtml(d.website) + '" target="_blank" rel="noopener" style="color:var(--hue);font-size:13px;">🌐 Visit Website</a></div>' : ''}}
      <div style="margin-bottom:14px;">
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:var(--text-3);margin-bottom:6px;">Hours</div>
        ${{hours}}
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap;">
        <a href="${{mapsUrl}}" target="_blank" rel="noopener" class="btn-primary" style="text-decoration:none;font-size:12px;">📍 Open in Maps</a>
        <button class="btn-ghost" style="font-size:12px;"
          onclick="navigateToDining('${{escHtml((d.name||name).replace(/'/g,'&#39;'))}}','${{escHtml((d.formatted_address||'').replace(/'/g,'&#39;'))}}')">
          🧭 Navigate</button>
        <button class="btn-ghost" style="font-size:12px;"
          onclick="toggleDiningFav('${{escHtml(placeId)}}','${{escHtml((d.name||name).replace(/'/g,'&#39;'))}}','${{escHtml((d.formatted_address||'').replace(/'/g,'&#39;'))}}','${{d.rating}}')"
          id="detail-fav-btn">♡ Save</button>
      </div>`;
  }} catch(e) {{
    inner.innerHTML = `<div style="color:var(--red);padding:20px;">Could not load details: ${{escHtml(e.message)}}</div>
      <button onclick="closeDiningDetail()" class="btn-ghost" style="margin:10px 0;">Close</button>`;
  }}
}}

function closeDiningDetail() {{
  const sheet = document.getElementById('dining-detail-sheet');
  if (sheet) sheet.style.display = 'none';
}}

function navigateToDining(name, address) {{
  closeDiningDetail();
  switchView('navigate');
  // Give the nav view a moment to render, then pre-fill destination
  setTimeout(function() {{
    var dest = document.getElementById('nav-dest');
    if (dest) {{
      dest.value = name + (address ? ', ' + address : '');
      dest.dispatchEvent(new Event('input'));
      // Auto-trigger route if start is already set
      var startEl = document.getElementById('nav-origin');
      if (startEl && startEl.value) {{
        navGetRoute();
      }}
    }}
  }}, 350);
  cardInteract('dining', 'navigate');
}}

/* ─── DINING CARD ─────────────────────────────────────────────────── */
async function loadDiningCard() {{
  const el = document.getElementById('dining-ov-content');
  if (!el) return;
  try {{
    const d = await fetch('/api/dining/recommend?limit=3').then(r => r.json());
    const picks = d.recommendations || [];
    if (!picks.length) {{
      el.innerHTML = '<div style="color:var(--text-3);font-size:12px;padding:4px 0;">No picks right now.</div>';
      return;
    }}
    const priceColor = p => p === '$$$$' ? '#f87171' : p === '$$$' ? '#fb923c' : '#4ade80';
    const rows = picks.map(p => `
      <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--border);">
        <div style="flex:1;min-width:0;">
          <div style="font-size:13px;font-weight:600;color:var(--text-1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${{escHtml(p.name)}}</div>
          <div style="font-size:11px;color:var(--text-3);">${{p.distance_mi}} mi &middot; ${{p.review_count}} reviews</div>
        </div>
        <div style="text-align:right;flex-shrink:0;">
          <div style="font-size:14px;font-weight:700;color:var(--hue);">${{p.rating}}★</div>
          <div style="font-size:10px;color:${{priceColor(p.price || '')}};">${{p.price || ''}}</div>
        </div>
      </div>`).join('');
    el.innerHTML = `
      <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.05em;color:var(--text-3);margin-bottom:4px;">
        Sam's ${{d.meal_type || 'dinner'}} picks
      </div>
      ${{rows}}
      <div style="text-align:right;margin-top:8px;">
        <button class="btn-ghost" style="font-size:10px;" onclick="switchView('dining')">More spots →</button>
      </div>`;
  }} catch(e) {{
    if (el) el.innerHTML = '<div style="color:var(--text-3);font-size:12px;">Could not load dining picks.</div>';
  }}
}}

/* ─── FISK FINANCIAL CARD ─────────────────────────────────────────── */
async function loadFiskCard() {{
  const content = document.getElementById('fisk-ov-content');
  const badge   = document.getElementById('fisk-health-badge');
  if (!content) return;
  try {{
    const res = await fetch('/api/finance/snapshot');
    if (!res.ok) {{
      if (content) content.innerHTML = `<div style="font-size:11px;color:var(--text-3);margin-bottom:8px;">Financial data unavailable.</div>`;
      return;
    }}
    const d = await res.json();
    const _emptyState = () => `
      <div style="font-size:12px;color:var(--text-3);margin-bottom:10px;">No accounts yet — add your balances to get started.</div>
      <button class="finance-setup-link" onclick="openFinanceSetup()">⚙ Set up accounts →</button>`;
    if (d.net_worth == null) {{
      if (content) content.innerHTML = _emptyState();
      return;
    }}

    const fmt = (n) => n == null ? '—' : '$' + Math.abs(n).toLocaleString('en-US', {{maximumFractionDigits:0}});
    const nw  = d.net_worth;
    const cf  = d.monthly_cashflow;
    const pi  = d.passive_income_monthly;
    const score = d.health_score;

    if (badge) {{
      badge.textContent = score != null ? score + '/10' : '—';
      badge.style.color = score >= 7 ? 'var(--green)' : score >= 4 ? 'var(--amber)' : 'var(--red)';
    }}

    const cfColor = cf == null ? 'var(--text-2)' : cf >= 0 ? 'var(--green)' : 'var(--red)';
    const cfSign  = cf == null ? '' : cf >= 0 ? '+' : '-';

    // Goals progress (top 2)
    const goals = (d.goals_progress || []).slice(0,2);
    const goalsHtml = goals.map(g => `
      <div style="margin-top:8px;">
        <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--text-3);margin-bottom:3px;">
          <span>${{escHtml(g.title)}}</span><span>${{g.percent_complete}}%</span>
        </div>
        <div style="height:3px;background:rgba(255,255,255,0.1);border-radius:2px;">
          <div style="height:100%;width:${{Math.min(g.percent_complete,100)}}%;background:var(--blue);border-radius:2px;"></div>
        </div>
      </div>`).join('');

    content.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">
        <div style="text-align:center;padding:8px;background:rgba(255,255,255,0.06);border-radius:8px;">
          <div style="font-size:16px;font-weight:700;font-family:var(--font-mono);color:var(--text-1);">${{fmt(nw)}}</div>
          <div style="font-size:8px;font-weight:700;text-transform:uppercase;color:var(--text-3);margin-top:2px;">Net Worth</div>
        </div>
        <div style="text-align:center;padding:8px;background:rgba(255,255,255,0.06);border-radius:8px;">
          <div style="font-size:16px;font-weight:700;font-family:var(--font-mono);color:${{cfColor}};">${{cfSign}}${{cf != null ? Math.abs(cf).toLocaleString('en-US',{{maximumFractionDigits:0}}) : '—'}}</div>
          <div style="font-size:8px;font-weight:700;text-transform:uppercase;color:var(--text-3);margin-top:2px;">Cashflow/mo</div>
        </div>
      </div>
      ${{pi > 0 ? `<div style="font-size:11px;color:var(--green);margin-bottom:8px;">💰 Passive: ${{fmt(pi)}}/mo</div>` : ''}}
      ${{d.fisk_assessment ? `<div style="font-size:10px;color:var(--text-3);font-style:italic;line-height:1.4;border-top:1px solid rgba(255,255,255,0.08);padding-top:8px;margin-bottom:6px;">"${{escHtml(d.fisk_assessment)}}"</div>` : ''}}
      ${{goalsHtml}}
      <div style="margin-top:10px;border-top:1px solid rgba(255,255,255,0.07);padding-top:8px;">
        <button class="finance-setup-link" onclick="openFinanceSetup()">⚙ Manage accounts</button>
      </div>
    `;
  }} catch(e) {{
    console.error('loadFiskCard', e);
    if (content) content.innerHTML = `<div style="font-size:11px;color:var(--text-3);">Financial data unavailable.</div>`;
  }}
}}

async function loadSamProtocol() {{
  try {{
    const res = await fetch('/api/health/sam/daily').catch(() => null);
    if (!res || !res.ok) return;
    const d = await res.json();
    _samProtocol = d.protocol || {{}};
    renderSamProtocol(_samProtocol, d.streak || {{}});
  }} catch(e) {{ console.error('loadSamProtocol', e); }}
}}

function renderSamProtocol(p, streak) {{
  const el = document.getElementById('sam-protocol-content');
  if (!el || !p) return;

  // Streak badge
  const sb = document.getElementById('sam-streak-badge');
  if (sb && streak.streak > 0) {{
    sb.textContent = '🔥 ' + streak.streak + ' day streak';
    sb.style.display = '';
  }}

  const t = p.targets || {{}};
  const mv = p.movement || {{}};
  const nu = p.nutrition || {{}};
  const hy = p.hydration || {{}};
  const rc = p.recovery  || {{}};

  el.innerHTML = `
    <!-- Greeting -->
    <div style="font-size:13px;font-weight:600;color:var(--blue);margin-bottom:12px;font-style:italic;">"${{escHtml(p.greeting || 'On your left.')}}"</div>

    <!-- Movement -->
    <div style="margin-bottom:10px;">
      <div style="font-size:9px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3);margin-bottom:5px;">💪 Movement</div>
      <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:4px;">
        <input type="checkbox" id="sc-movement" onchange="samCheck('movement',this.checked)" style="margin-top:2px;cursor:pointer;accent-color:var(--blue);">
        <div>
          <div style="font-size:12px;font-weight:600;color:var(--text-1);">${{escHtml(mv.primary || '—')}}</div>
          <div style="font-size:11px;color:var(--text-3);margin-top:1px;">${{escHtml(mv.details || '')}}</div>
          <div style="font-size:10px;color:var(--blue);margin-top:2px;">⏰ ${{escHtml(mv.timing || '')}}</div>
          ${{mv.alternative ? `<div style="font-size:10px;color:var(--text-3);margin-top:2px;">Alt: ${{escHtml(mv.alternative)}}</div>` : ''}}
        </div>
      </div>
    </div>

    <!-- Nutrition -->
    <div style="margin-bottom:10px;">
      <div style="font-size:9px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3);margin-bottom:5px;">🥗 Nutrition <span style="font-weight:400;text-transform:none;">&nbsp;·&nbsp;${{t.protein_g || 85}}g protein · ${{t.fiber_g || 35}}g fiber</span></div>
      ${{['breakfast','lunch','dinner'].map(meal => `
        <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:4px;">
          <input type="checkbox" id="sc-${{meal}}" onchange="samCheck('${{meal}}',this.checked)" style="margin-top:2px;cursor:pointer;accent-color:var(--blue);">
          <div>
            <span style="font-size:10px;font-weight:700;color:var(--text-3);text-transform:uppercase;">${{meal}}</span>
            <span style="font-size:12px;color:var(--text-2);margin-left:6px;">${{escHtml(nu[meal] || '—')}}</span>
          </div>
        </div>`).join('')}}
      ${{nu.watch ? `<div style="font-size:10px;color:var(--amber);margin-top:4px;padding:4px 8px;background:rgba(217,119,6,.1);border-radius:4px;">⚠ ${{escHtml(nu.watch)}}</div>` : ''}}
    </div>

    <!-- Hydration -->
    <div style="margin-bottom:10px;">
      <div style="font-size:9px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3);margin-bottom:5px;">💧 Hydration</div>
      <div style="display:flex;align-items:flex-start;gap:8px;">
        <input type="checkbox" id="sc-hydration" onchange="samCheck('hydration',this.checked)" style="margin-top:2px;cursor:pointer;accent-color:var(--blue);">
        <div>
          <div style="font-size:12px;color:var(--text-2);">${{hy.target_oz || 96}}oz · ${{escHtml(hy.schedule || '')}}</div>
          <div style="font-size:10px;color:var(--text-3);margin-top:2px;">${{escHtml(hy.why || '')}}</div>
        </div>
      </div>
    </div>

    <!-- Recovery -->
    <div style="margin-bottom:12px;">
      <div style="font-size:9px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3);margin-bottom:5px;">😴 Recovery</div>
      <div style="display:flex;align-items:flex-start;gap:8px;">
        <input type="checkbox" id="sc-recovery" onchange="samCheck('recovery',this.checked)" style="margin-top:2px;cursor:pointer;accent-color:var(--blue);">
        <div>
          <div style="font-size:12px;color:var(--text-2);">${{rc.sleep_target_h || 7.5}}h · Lights out ${{escHtml(rc.bedtime || '10:30 PM')}}</div>
          <div style="font-size:10px;color:var(--text-3);margin-top:2px;">${{escHtml(rc.tip || '')}}</div>
        </div>
      </div>
    </div>

    <!-- Sam Says -->
    <div style="border-top:1px solid var(--border);padding-top:10px;display:flex;align-items:flex-start;gap:8px;">
      <span style="font-size:18px;">🦅</span>
      <div style="font-size:11px;color:var(--text-2);font-style:italic;line-height:1.5;">"${{escHtml(p.sam_says || '')}}"</div>
    </div>
  `;
}}

function samCheck(item, checked) {{
  if (checked) _samChecked.add(item);
  else _samChecked.delete(item);
  // Auto-save after short delay
  clearTimeout(window._samSaveTimer);
  window._samSaveTimer = setTimeout(samSave, 2000);
}}

async function samSave() {{
  try {{
    await fetch('/api/health/sam/checkin', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{completed: [..._samChecked]}})
    }});
  }} catch(e) {{}}
}}

/* ─── SAM CHECK-IN BANNER ─────────────────────────────────────────── */
let _samCheckinItems = [];  // evening checklist state

async function loadSamCheckin() {{
  const isEvening = new Date().getHours() >= 16;
  if (isEvening) {{
    await renderSamEveningCheckin();
  }} else {{
    await renderSamMorningCheckin();
  }}
}}

async function renderSamMorningCheckin() {{
  const banner = document.getElementById('sam-checkin-banner');
  if (!banner) return;
  try {{
    const [mRes, pRes] = await Promise.all([
      fetch('/api/health/sam/morning-checkin'),
      fetch('/api/health/sam/daily'),
    ]);
    const m = mRes.ok ? await mRes.json() : {{}};
    const pd = pRes.ok ? await pRes.json() : {{}};
    const streak = m.streak || pd.streak || {{}};

    const readiness = m.readiness != null ? m.readiness : '—';
    const hrv = m.hrv != null ? m.hrv : '—';
    const sleep = m.sleep_hours != null ? parseFloat(m.sleep_hours).toFixed(1) : '—';
    const streakN = streak.streak || 0;

    banner.innerHTML = `
      <div class="sam-checkin-mode-chip morning">☀️ Morning Check-In</div>
      <div class="sam-checkin-greeting">"${{escHtml(m.greeting || 'On your left. Let\\'s work, brother.')}}"</div>

      <div class="sam-checkin-meta">
        ${{readiness !== '—' ? `<div class="sam-checkin-stat">
          <div class="sam-checkin-stat-val" style="color:var(--amber)">${{readiness}}</div>
          <div class="sam-checkin-stat-lbl">Readiness</div>
        </div><div class="sam-checkin-divider"></div>` : ''}}
        ${{hrv !== '—' ? `<div class="sam-checkin-stat">
          <div class="sam-checkin-stat-val">${{hrv}}</div>
          <div class="sam-checkin-stat-lbl">HRV ms</div>
        </div><div class="sam-checkin-divider"></div>` : ''}}
        ${{sleep !== '—' ? `<div class="sam-checkin-stat">
          <div class="sam-checkin-stat-val">${{sleep}}</div>
          <div class="sam-checkin-stat-lbl">Sleep h</div>
        </div>` : ''}}
        ${{streakN > 0 ? `<div class="sam-checkin-divider"></div>
          <div class="sam-checkin-streak">🔥 ${{streakN}} day${{streakN !== 1 ? 's' : ''}}</div>` : ''}}
      </div>

      <div class="sam-checkin-focus">
        <div class="sam-checkin-focus-label">💪 Today's Focus</div>
        <div class="sam-checkin-focus-primary">${{escHtml(m.focus_primary || 'Zone 2 cardio')}}</div>
        <div class="sam-checkin-focus-detail">${{escHtml(m.focus_details || '')}}
          ${{m.timing ? ` · <span style="color:var(--blue);">⏰ ${{escHtml(m.timing)}}</span>` : ''}}
        </div>
      </div>

      ${{m.nutrition_watch ? `<div class="sam-checkin-watch">⚠ ${{escHtml(m.nutrition_watch)}}</div>` : ''}}

      <div class="sam-checkin-actions">
        <button class="btn-ghost" style="font-size:11px;padding:6px 14px;"
          onclick="document.getElementById('sam-protocol-section').scrollIntoView({{behavior:'smooth'}})">
          View Full Protocol ↓
        </button>
        <button class="btn-ghost" style="font-size:11px;padding:6px 14px;"
          onclick="document.getElementById('sam-chat-input').focus();document.getElementById('sam-chat-input').scrollIntoView({{behavior:'smooth'}})">
          Talk to Sam 💬
        </button>
        <button class="btn-ghost" style="font-size:11px;padding:6px 14px;"
          onclick="openSamHistory()">
          📅 History
        </button>
      </div>
    `;
  }} catch(e) {{
    console.error('renderSamMorningCheckin', e);
    const banner = document.getElementById('sam-checkin-banner');
    if (banner) banner.innerHTML = '<div style="font-size:11px;color:var(--text-3);">On your left. Let\\'s work.</div>';
  }}
}}

async function renderSamEveningCheckin() {{
  const banner = document.getElementById('sam-checkin-banner');
  if (!banner) return;
  try {{
    const [pRes] = await Promise.all([fetch('/api/health/sam/daily')]);
    const pd = pRes.ok ? await pRes.json() : {{}};
    const protocol = pd.protocol || {{}};
    const streak = pd.streak || {{}};
    const streakN = streak.streak || 0;
    const mv = protocol.movement || {{}};
    const nu = protocol.nutrition || {{}};
    const hy = protocol.hydration || {{}};
    const rc = protocol.recovery || {{}};

    // Build checklist from today's protocol
    _samCheckinItems = [
      {{id:'workout',   icon:'🏃', label: mv.primary  || 'Zone 2 cardio'}},
      {{id:'breakfast', icon:'🥚', label: nu.breakfast || 'Clean breakfast'}},
      {{id:'lunch',     icon:'🥗', label: nu.lunch     || 'Clean lunch'}},
      {{id:'dinner',    icon:'🍽', label: nu.dinner    || 'Clean dinner'}},
      {{id:'hydration', icon:'💧', label: `${{hy.target_oz || 96}}oz water`}},
      {{id:'recovery',  icon:'😴', label: `Lights out by ${{rc.bedtime || '10:30 PM'}}`}},
    ];

    const itemsHtml = _samCheckinItems.map(item => `
      <label class="sam-evening-item" id="sei-${{item.id}}" onclick="samEveningToggle('${{item.id}}')">
        <input type="checkbox" id="sic-${{item.id}}" onclick="event.stopPropagation();samEveningToggle('${{item.id}}')">
        <span class="sam-evening-item-icon">${{item.icon}}</span>
        <span class="sam-evening-item-label">${{escHtml(item.label)}}</span>
      </label>
    `).join('');

    banner.innerHTML = `
      <div class="sam-checkin-mode-chip evening">🌙 Evening Check-In</div>
      <div class="sam-checkin-greeting">"How'd today go, brother?"</div>
      ${{streakN > 0 ? `<div class="sam-checkin-streak" style="margin-bottom:12px;">🔥 ${{streakN}} day${{streakN !== 1 ? 's' : ''}} — keep it going</div>` : ''}}

      <!-- Tell Sam section -->
      <div style="margin-bottom:12px;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:var(--text-3);margin-bottom:6px;">
          Tell Sam what you did today
        </div>
        <textarea id="sam-narrative-input"
          style="width:100%;box-sizing:border-box;resize:vertical;min-height:70px;padding:9px 11px;
                 font-size:12px;font-family:var(--font-body);background:rgba(255,255,255,0.06);
                 border:1px solid rgba(255,255,255,0.12);border-radius:9px;color:var(--text-1);
                 outline:none;transition:border-color 0.15s;margin-bottom:7px;"
          placeholder="e.g. Did a 40-min bike ride this morning, had eggs for breakfast, drank about 80oz of water, skipped lunch, dinner was grilled chicken and veggies. In bed by 10:30."
          rows="3"></textarea>
        <button id="sam-evaluate-btn"
          onclick="askSamToEvaluate()"
          style="width:100%;padding:8px;font-size:11px;font-weight:700;text-transform:uppercase;
                 letter-spacing:0.07em;border:none;border-radius:9px;cursor:pointer;
                 background:linear-gradient(135deg,rgba(99,179,237,0.7) 0%,rgba(129,140,248,0.7) 100%);
                 color:#fff;transition:opacity 0.15s;">
          🦅 Have Sam evaluate →
        </button>
        <div id="sam-eval-response" style="display:none;margin-top:10px;padding:10px 12px;
             background:rgba(255,255,255,0.05);border-radius:9px;border-left:3px solid var(--hue);">
          <div style="font-size:9px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3);margin-bottom:5px;">🦅 Sam's Read</div>
          <div id="sam-eval-text" style="font-size:12px;color:var(--text-1);line-height:1.5;font-style:italic;"></div>
        </div>
      </div>

      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:var(--text-3);margin-bottom:8px;">
        Or check off manually
      </div>
      <div class="sam-evening-list" id="sam-evening-list">${{itemsHtml}}</div>

      <textarea class="sam-evening-notes" id="sam-evening-notes"
        rows="2" placeholder="Any notes? Injuries, energy levels, what got in the way…"></textarea>

      <div class="sam-checkin-actions" style="margin-top:10px;">
        <button class="btn-accent" style="font-size:11px;padding:7px 18px;flex:1;"
          onclick="submitSamEveningCheckin()">
          Log My Day →
        </button>
        <button class="btn-ghost" style="font-size:11px;padding:7px 14px;"
          onclick="document.getElementById('sam-chat-input').focus();document.getElementById('sam-chat-input').scrollIntoView({{behavior:'smooth'}})">
          Talk to Sam 💬
        </button>
        <button class="btn-ghost" style="font-size:11px;padding:7px 14px;"
          onclick="openSamHistory()">
          📅 History
        </button>
      </div>

      <div class="sam-checkin-response" id="sam-checkin-response">
        <div style="font-size:9px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3);margin-bottom:6px;">🦅 Sam's Take</div>
        <div class="sam-checkin-response-text" id="sam-checkin-response-text"></div>
        <div class="sam-checkin-response-streak" id="sam-checkin-response-streak"></div>
      </div>
    `;
  }} catch(e) {{
    console.error('renderSamEveningCheckin', e);
  }}
}}

function samEveningToggle(id) {{
  const cb  = document.getElementById('sic-' + id);
  const row = document.getElementById('sei-' + id);
  if (!cb || !row) return;
  cb.checked = !cb.checked;
  row.classList.toggle('checked', cb.checked);
}}

async function askSamToEvaluate() {{
  const narrativeEl = document.getElementById('sam-narrative-input');
  const btn         = document.getElementById('sam-evaluate-btn');
  const respEl      = document.getElementById('sam-eval-response');
  const textEl      = document.getElementById('sam-eval-text');
  const narrative   = narrativeEl?.value.trim();
  if (!narrative) {{ showToast('Tell Sam what you did first', 'warn'); return; }}

  if (btn) {{ btn.disabled = true; btn.textContent = '🦅 Sam is reading your day…'; }}
  if (respEl) respEl.style.display = 'none';

  try {{
    const res = await fetch('/api/health/sam/evaluate', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ narrative }}),
    }});
    const d = await res.json();

    // Pre-fill the checkboxes based on Sam's evaluation
    const completed = new Set(d.completed || []);
    _samCheckinItems.forEach(item => {{
      const cb  = document.getElementById('sic-' + item.id);
      const row = document.getElementById('sei-' + item.id);
      if (!cb || !row) return;
      const shouldCheck = completed.has(item.id);
      cb.checked = shouldCheck;
      row.classList.toggle('checked', shouldCheck);
    }});

    // Show Sam's response
    if (textEl) textEl.textContent = d.reply || '';
    if (respEl) respEl.style.display = 'block';

    // Copy narrative into the notes field so it's saved with the log
    const notesEl = document.getElementById('sam-evening-notes');
    if (notesEl && !notesEl.value) notesEl.value = narrative;

    // Scroll checklist into view
    document.getElementById('sam-evening-list')?.scrollIntoView({{behavior:'smooth', block:'nearest'}});

    if (btn) {{ btn.textContent = `✓ ${{d.adherence_pct}}% — adjust & save below`; }}
  }} catch(e) {{
    console.error('askSamToEvaluate', e);
    showToast("Sam couldn't connect — try again", 'warn');
    if (btn) {{ btn.disabled = false; btn.textContent = '🦅 Have Sam evaluate →'; }}
  }}
}}

async function submitSamEveningCheckin() {{
  const completed = _samCheckinItems
    .filter(item => document.getElementById('sic-' + item.id)?.checked)
    .map(item => item.id);
  const notes = (document.getElementById('sam-evening-notes')?.value || '').trim();

  const btn = document.querySelector('.sam-checkin-actions .btn-accent');
  if (btn) {{ btn.textContent = 'Logging…'; btn.disabled = true; }}

  try {{
    const res = await fetch('/api/health/sam/evening-checkin', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{completed, notes}}),
    }});
    const d = await res.json();
    const pct = d.adherence_pct ?? 0;
    const streakN = (d.streak || {{}}).streak || 0;

    const respEl = document.getElementById('sam-checkin-response');
    const textEl = document.getElementById('sam-checkin-response-text');
    const strEl  = document.getElementById('sam-checkin-response-streak');
    if (respEl && textEl) {{
      textEl.textContent = d.reply || '';
      if (strEl) strEl.textContent = streakN > 0 ? `🔥 ${{streakN}} day streak · ${{pct}}% today` : `${{pct}}% today`;
      respEl.classList.add('visible');
      respEl.scrollIntoView({{behavior:'smooth', block:'nearest'}});
    }}
    if (btn) {{ btn.textContent = `✓ Logged (${{pct}}%)`; }}
  }} catch(e) {{
    console.error('submitSamEveningCheckin', e);
    if (btn) {{ btn.textContent = 'Log My Day →'; btn.disabled = false; }}
  }}
}}

/* ═══ SAM HISTORY MODAL ═══════════════════════════════════════ */

// Canonical 6 checklist items — labels used in history log view
const _SAM_HIST_ITEMS = [
  {{ id:'workout',   icon:'🏃', label:'Workout / Movement' }},
  {{ id:'breakfast', icon:'🥚', label:'Clean breakfast' }},
  {{ id:'lunch',     icon:'🥗', label:'Clean lunch' }},
  {{ id:'dinner',    icon:'🍽', label:'Clean dinner' }},
  {{ id:'hydration', icon:'💧', label:'Hydration goal' }},
  {{ id:'recovery',  icon:'😴', label:'Lights out on time' }},
];

let _samHistoryRecords = [];   // [{{date, completed[], notes, adherence_pct}}, …]
let _samHistoryIdx     = 0;    // which record we're currently viewing (0 = most recent)

async function openSamHistory() {{
  const ov = document.getElementById('sam-hist-overlay');
  if (!ov) return;
  ov.classList.remove('hidden');
  await _fetchSamHistory();
  _renderSamHistoryDay();
}}

function closeSamHistory(e) {{
  if (e && e.target !== document.getElementById('sam-hist-overlay')) return;
  document.getElementById('sam-hist-overlay')?.classList.add('hidden');
}}

async function _fetchSamHistory() {{
  try {{
    const res = await fetch('/api/health/sam/history?days=60');
    _samHistoryRecords = await res.json();
    // If today has no record yet, prepend an empty placeholder
    const today = new Date().toISOString().slice(0,10);
    if (!_samHistoryRecords.length || _samHistoryRecords[0].date !== today) {{
      _samHistoryRecords.unshift({{ date: today, completed: [], notes: '', adherence_pct: 0 }});
    }}
    _samHistoryIdx = 0;
  }} catch(e) {{
    console.error('_fetchSamHistory', e);
    _samHistoryRecords = [];
  }}
}}

function navSamHistory(delta) {{
  const newIdx = _samHistoryIdx + delta;
  if (newIdx < 0 || newIdx >= _samHistoryRecords.length) return;
  _samHistoryIdx = newIdx;
  _renderSamHistoryDay();
}}

function _renderSamHistoryDay() {{
  const rec = _samHistoryRecords[_samHistoryIdx] || {{ date:'', completed:[], notes:'', adherence_pct:0 }};
  const today = new Date().toISOString().slice(0,10);
  const yesterday = new Date(Date.now()-86400000).toISOString().slice(0,10);

  // Date label
  const [y,mo,d] = rec.date.split('-').map(Number);
  const dt = new Date(y, mo-1, d);
  const dayStr = dt.toLocaleDateString('en-US', {{weekday:'long', month:'long', day:'numeric'}});
  let relLabel = '';
  if (rec.date === today) relLabel = 'Today';
  else if (rec.date === yesterday) relLabel = 'Yesterday';
  else {{
    const diffDays = Math.round((new Date(today) - new Date(rec.date)) / 86400000);
    relLabel = diffDays + ' days ago';
  }}

  document.getElementById('sam-hist-date-label').textContent = dayStr;
  document.getElementById('sam-hist-date-rel').textContent   = relLabel;

  // Nav buttons
  document.getElementById('sam-hist-prev').disabled = (_samHistoryIdx >= _samHistoryRecords.length - 1);
  document.getElementById('sam-hist-next').disabled = (_samHistoryIdx <= 0);

  // Adherence %
  const pct = rec.adherence_pct ?? Math.round((rec.completed||[]).length / 6 * 100);
  const pctEl = document.getElementById('sam-hist-pct-num');
  const fillEl = document.getElementById('sam-hist-pct-fill');
  const lblEl  = document.getElementById('sam-hist-pct-label');
  if (pctEl) pctEl.textContent = pct + '%';
  if (pctEl) pctEl.style.color = pct >= 80 ? 'var(--green)' : pct >= 50 ? 'var(--amber)' : 'var(--red)';
  if (fillEl) fillEl.style.width = pct + '%';
  if (fillEl) fillEl.style.background = pct >= 80
    ? 'linear-gradient(90deg,var(--green),#34d399)'
    : pct >= 50 ? 'linear-gradient(90deg,var(--amber),#fbbf24)'
    : 'linear-gradient(90deg,var(--red),#f87171)';
  if (lblEl) lblEl.textContent = rec.date === today ? 'so far today' : 'adherence';

  // 30-day streak dots (most recent = rightmost)
  const streakEl = document.getElementById('sam-hist-streak');
  if (streakEl) {{
    const dots = _samHistoryRecords.slice(0, 30).reverse();
    streakEl.innerHTML = dots.map((r, i) => {{
      const isToday = r.date === today;
      const isDone  = (r.adherence_pct || 0) >= 50;
      const isCur   = r.date === rec.date;
      return `<div class="sam-hist-dot${{isDone?' done':''}}${{isToday?' today':''}}"
        style="${{isCur ? 'outline:2px solid rgba(255,255,255,0.5);outline-offset:2px;' : ''}}"
        title="${{r.date}}: ${{r.adherence_pct||0}}%"></div>`;
    }}).join('');
  }}

  // Checklist
  const listEl = document.getElementById('sam-hist-list');
  if (listEl) {{
    const done = new Set(rec.completed || []);
    listEl.innerHTML = _SAM_HIST_ITEMS.map(item => `
      <div class="sam-hist-item${{done.has(item.id) ? ' checked' : ''}}"
           id="shi-${{item.id}}" onclick="toggleSamHistItem('${{item.id}}')">
        <span class="sam-hist-item-icon">${{item.icon}}</span>
        <span class="sam-hist-item-label">${{escHtml(item.label)}}</span>
        <div class="sam-hist-cb">${{done.has(item.id) ? '✓' : ''}}</div>
      </div>`).join('');
  }}

  // Notes
  const notesEl = document.getElementById('sam-hist-notes');
  if (notesEl) notesEl.value = rec.notes || '';

  // Reset save button
  const saveBtn = document.getElementById('sam-hist-save');
  if (saveBtn) {{ saveBtn.disabled = false; saveBtn.textContent = 'Save Changes'; }}
}}

function toggleSamHistItem(id) {{
  const row = document.getElementById('shi-' + id);
  if (!row) return;
  const isChecked = row.classList.toggle('checked');
  const cb = row.querySelector('.sam-hist-cb');
  if (cb) cb.textContent = isChecked ? '✓' : '';
  // Update adherence display live
  const checkedCount = document.querySelectorAll('#sam-hist-list .sam-hist-item.checked').length;
  const pct = Math.round(checkedCount / 6 * 100);
  const pctEl = document.getElementById('sam-hist-pct-num');
  const fillEl = document.getElementById('sam-hist-pct-fill');
  if (pctEl) {{ pctEl.textContent = pct + '%'; pctEl.style.color = pct>=80?'var(--green)':pct>=50?'var(--amber)':'var(--red)'; }}
  if (fillEl) fillEl.style.width = pct + '%';
}}

async function saveSamHistoryDay() {{
  const rec = _samHistoryRecords[_samHistoryIdx];
  if (!rec) return;
  const saveBtn = document.getElementById('sam-hist-save');
  if (saveBtn) {{ saveBtn.disabled = true; saveBtn.textContent = 'Saving…'; }}
  try {{
    const completed = _SAM_HIST_ITEMS
      .filter(item => document.getElementById('shi-' + item.id)?.classList.contains('checked'))
      .map(item => item.id);
    const notes = (document.getElementById('sam-hist-notes')?.value || '').trim();
    const res = await fetch('/api/health/sam/history', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ date: rec.date, completed, notes }}),
    }});
    const d = await res.json();
    if (d.ok) {{
      // Update local record
      _samHistoryRecords[_samHistoryIdx] = {{ ...rec, completed, notes, adherence_pct: d.adherence_pct }};
      showToast('Saved · ' + d.adherence_pct + '% adherence', 'ok');
      if (saveBtn) {{ saveBtn.textContent = '✓ Saved'; }}
      setTimeout(() => _renderSamHistoryDay(), 1200);
    }} else {{
      showToast('Could not save', 'warn');
      if (saveBtn) {{ saveBtn.disabled = false; saveBtn.textContent = 'Save Changes'; }}
    }}
  }} catch(e) {{
    console.error('saveSamHistoryDay', e);
    showToast('Network error', 'warn');
    if (saveBtn) {{ saveBtn.disabled = false; saveBtn.textContent = 'Save Changes'; }}
  }}
}}

/* ════════════════════════════════════════════════════════════ */

// ─── Sam Chat helpers ────────────────────────────────────────────────────────
function samSwitchMode(mode) {{
  _samChatMode = mode;
  const modeBar = document.getElementById('sam-chat-mode-bar');
  const modeLabel = document.getElementById('sam-chat-mode-label');
  const inp = document.getElementById('sam-chat-input');
  if (mode === 'food') {{
    if (modeBar) {{ modeBar.style.display = 'flex'; }}
    if (modeLabel) modeLabel.textContent = '🍽 Food log mode — describe what you ate';
    if (inp) inp.placeholder = 'e.g. "I had grilled chicken breast and brown rice"';
    samLoadFoodLog();
  }} else if (mode === 'interview') {{
    if (modeBar) {{ modeBar.style.display = 'flex'; }}
    if (modeLabel) modeLabel.textContent = "🎤 Diet interview — answer Sam's questions";
    if (inp) inp.placeholder = 'Type your answer…';
  }} else {{
    if (modeBar) modeBar.style.display = 'none';
    if (inp) inp.placeholder = "Talk to Sam… or log food (e.g. 'I had eggs and toast')";
  }}
}}

function samCancelMode() {{
  _samChatMode = 'chat';
  _samInterviewStep = 0;
  samSwitchMode('chat');
}}

async function samStartInterview() {{
  _samChatMode = 'interview';
  _samInterviewStep = 0;
  samSwitchMode('interview');
  const msgs = document.getElementById('sam-chat-messages');
  if (msgs) msgs.style.display = '';
  // Send an empty answer to get the first question
  const msgs2 = document.getElementById('sam-chat-messages');
  if (msgs2) {{
    msgs2.innerHTML += `<div style="margin-bottom:6px;color:var(--text-3);font-style:italic;">Starting diet interview…</div>`;
    msgs2.scrollTop = msgs2.scrollHeight;
  }}
  try {{
    const res = await fetch('/api/health/sam/diet-interview', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{step: 0, answer: ''}})
    }});
    const d = await res.json();
    if (msgs2 && (d.reply || d.question)) {{
      msgs2.innerHTML += `<div style="margin-bottom:8px;"><b style="color:var(--blue);">Sam:</b> ${{escHtml(d.reply || d.question)}}</div>`;
      msgs2.scrollTop = msgs2.scrollHeight;
    }}
    _samInterviewStep = (d.step !== undefined) ? d.step : 1;
  }} catch(e) {{
    if (msgs2) msgs2.innerHTML += `<div style="color:var(--red);">Couldn't start interview — try again</div>`;
  }}
}}

async function samLoadFoodLog() {{
  const strip = document.getElementById('sam-food-strip');
  try {{
    const res = await fetch('/api/health/sam/food-log?date=' + _localDateStr()).catch(() => null);
    if (!res || !res.ok) return;
    const d = await res.json();
    const protein = Math.round(d.protein_g || 0);
    const target  = 87;  // midpoint of 85-90g CKD target
    const pct     = Math.min(100, Math.round(protein / target * 100));
    if (strip) strip.style.display = '';
    const bar   = document.getElementById('sam-food-protein-bar');
    const label = document.getElementById('sam-food-protein-label');
    const meals = document.getElementById('sam-food-meals');
    if (bar) bar.style.width = pct + '%';
    if (label) label.textContent = protein + 'g / ' + target + 'g protein';
    if (meals) {{
      const mealList = d.meals || [];
      if (mealList.length) {{
        meals.innerHTML = mealList.map(m =>
          `<span style="background:var(--surface-3);border-radius:10px;padding:2px 8px;">${{escHtml(m.name || '—')}}</span>`
        ).join('');
      }} else {{
        meals.innerHTML = '<span style="color:var(--text-3);">No meals logged yet today</span>';
      }}
    }}
  }} catch(e) {{}}
}}

// ─── Local date helper (avoids UTC-vs-local mismatch) ────────────────────────
function _localDateStr(d) {{
  const dt = d || new Date();
  return dt.getFullYear() + '-' +
    String(dt.getMonth() + 1).padStart(2, '0') + '-' +
    String(dt.getDate()).padStart(2, '0');
}}

// ─── Sam Daily Journal ───────────────────────────────────────────────────────
let _sjHistory = [];
let _sjDate = null;

async function openSamJournal() {{
  const ov = document.getElementById('sam-journal-overlay');
  if (!ov) return;
  ov.classList.remove('hidden');
  _sjHistory = [];
  _sjDate = _localDateStr();
  const dateEl = document.getElementById('sj-date');
  if (dateEl) dateEl.textContent = new Date().toLocaleDateString('en-US', {{weekday:'long', month:'long', day:'numeric'}});
  const msgs = document.getElementById('sj-messages');
  if (msgs) msgs.innerHTML = '';
  const summary = document.getElementById('sj-summary');
  if (summary) summary.style.display = 'none';
  _sjAppendMsg('sam', "Talk to me about your day — exercise, food, drinks, how you're feeling mentally, stress, sleep from last night. Everything. Just go.");
  document.getElementById('sj-input')?.focus();
}}

function closeSamJournal() {{
  document.getElementById('sam-journal-overlay')?.classList.add('hidden');
  samLoadFoodLog();
  // Refresh Sam overview card so summary shows up immediately
  if (typeof loadSamOverviewCard === 'function') loadSamOverviewCard();
  loadDailyHealthScore();
}}

function _sjAppendMsg(who, text, extraHtml) {{
  const msgs = document.getElementById('sj-messages');
  if (!msgs) return;
  const isUser = who === 'user';
  const bubble = `
    <div style="display:flex;flex-direction:column;align-items:${{isUser ? 'flex-end' : 'flex-start'}};">
      <div style="max-width:85%;padding:10px 14px;border-radius:${{isUser ? '14px 14px 4px 14px' : '14px 14px 14px 4px'}};
        background:${{isUser ? 'var(--blue)' : 'var(--surface-2)'}};color:${{isUser ? '#fff' : 'var(--text-1)'}};font-size:13px;line-height:1.5;">
        ${{escHtml(text)}}
      </div>
      ${{extraHtml || ''}}
    </div>`;
  msgs.innerHTML += bubble;
  msgs.scrollTop = msgs.scrollHeight;
}}

function _sjRenderSummary(extracted, logged_meals, adherence_items, daily_protein_g, protein_target_g) {{
  const summary = document.getElementById('sj-summary');
  const content = document.getElementById('sj-summary-content');
  if (!summary || !content) return;
  const parts = [];
  const pct = Math.min(100, Math.round((daily_protein_g || 0) / (protein_target_g || 87) * 100));
  parts.push(`
    <div style="margin-bottom:8px;">
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-3);margin-bottom:3px;">
        <span>Protein</span><span>${{daily_protein_g || 0}}g / ${{protein_target_g || 87}}g</span>
      </div>
      <div style="height:4px;background:var(--surface-3);border-radius:2px;overflow:hidden;">
        <div style="height:100%;width:${{pct}}%;background:var(--blue);border-radius:2px;"></div>
      </div>
    </div>`);
  if (logged_meals && logged_meals.length) {{
    parts.push(`<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px;">
      ${{logged_meals.map(m => `<span style="font-size:10px;background:var(--surface-3);border-radius:8px;padding:2px 8px;">🍽 ${{escHtml(m)}}</span>`).join('')}}
    </div>`);
  }}
  const ex = (extracted && extracted.exercise) || [];
  if (ex.length) {{
    parts.push(`<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px;">
      ${{ex.map(e => `<span style="font-size:10px;background:var(--surface-3);border-radius:8px;padding:2px 8px;">💪 ${{escHtml(e.type || 'exercise')}} ${{e.duration_min ? e.duration_min+'min' : ''}}</span>`).join('')}}
    </div>`);
  }}
  if (extracted && extracted.water_oz) {{
    parts.push(`<div style="font-size:11px;color:var(--text-2);">💧 ${{extracted.water_oz}}oz water</div>`);
  }}
  if (adherence_items && adherence_items.length) {{
    parts.push(`<div style="font-size:11px;color:var(--green);margin-top:4px;">✓ ${{adherence_items.join(' · ')}}</div>`);
  }}
  content.innerHTML = parts.join('');
  summary.style.display = '';
}}

async function samJournalSend() {{
  const inp = document.getElementById('sj-input');
  if (!inp) return;
  const text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  inp.style.height = '';
  _sjAppendMsg('user', text);
  _sjHistory.push({{role: 'user', content: text}});
  const msgs = document.getElementById('sj-messages');
  if (msgs) {{
    msgs.innerHTML += `<div id="sj-typing" style="color:var(--text-3);font-size:12px;font-style:italic;padding:4px 0;">Sam is processing…</div>`;
    msgs.scrollTop = msgs.scrollHeight;
  }}
  try {{
    const res = await fetch('/api/health/sam/journal', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        message: text,
        history: _sjHistory.slice(-10),
        date: _sjDate,
      }})
    }});
    const d = await res.json();
    document.getElementById('sj-typing')?.remove();
    _sjAppendMsg('sam', d.reply || '…');
    _sjHistory.push({{role: 'assistant', content: d.reply || ''}});
    _sjRenderSummary(d.extracted, d.logged_meals, d.adherence_items, d.daily_protein_g, d.protein_target_g);
    if (typeof voiceSpeak === 'function') voiceSpeak(d.reply);
  }} catch(e) {{
    document.getElementById('sj-typing')?.remove();
    if (msgs) msgs.innerHTML += `<div style="color:var(--red);font-size:12px;">Connection error — try again</div>`;
  }}
}}

// ─── Sam Chat ────────────────────────────────────────────────────────────────
async function samChat() {{
  const inp = document.getElementById('sam-chat-input');
  const msgs = document.getElementById('sam-chat-messages');
  if (!inp || !msgs) return;
  const text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  msgs.style.display = '';

  // ── Interview mode: route to diet-interview endpoint ────────────────────
  if (_samChatMode === 'interview') {{
    msgs.innerHTML += `<div style="margin-bottom:6px;"><b style="color:var(--text-3);">You:</b> ${{escHtml(text)}}</div>`;
    msgs.innerHTML += `<div id="sam-typing" style="margin-bottom:6px;color:var(--text-3);font-style:italic;">Sam is thinking…</div>`;
    msgs.scrollTop = msgs.scrollHeight;
    try {{
      const res = await fetch('/api/health/sam/diet-interview', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{step: _samInterviewStep, answer: text}})
      }});
      const d = await res.json();
      document.getElementById('sam-typing')?.remove();
      if (d.done) {{
        msgs.innerHTML += `<div style="margin-bottom:8px;"><b style="color:var(--blue);">Sam:</b> ${{escHtml(d.reply || d.question || 'Interview complete — preferences saved!')}}</div>`;
        samCancelMode();
      }} else {{
        msgs.innerHTML += `<div style="margin-bottom:8px;"><b style="color:var(--blue);">Sam:</b> ${{escHtml(d.reply || d.question || '…')}}</div>`;
        _samInterviewStep = (d.step !== undefined) ? d.step : (_samInterviewStep + 1);
      }}
      msgs.scrollTop = msgs.scrollHeight;
    }} catch(e) {{
      document.getElementById('sam-typing')?.remove();
      msgs.innerHTML += `<div style="color:var(--red);">Connection error</div>`;
    }}
    return;
  }}

  // ── Normal chat / food mode ──────────────────────────────────────────────
  msgs.innerHTML += `<div style="margin-bottom:6px;"><b style="color:var(--text-3);">You:</b> ${{escHtml(text)}}</div>`;
  msgs.innerHTML += `<div id="sam-typing" style="margin-bottom:6px;color:var(--text-3);font-style:italic;">Sam is thinking…</div>`;
  msgs.scrollTop = msgs.scrollHeight;
  _samHistory.push({{role:'user', content:text}});
  try {{
    const res = await fetch('/api/health/sam/chat', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        message: text,
        history: _samHistory.slice(-6),
        mode: _samChatMode,
        interview_step: _samInterviewStep,
        food_date: _samFoodDate || null,
      }})
    }});
    const d = await res.json();
    document.getElementById('sam-typing')?.remove();

    const reply = d.reply || '…';
    msgs.innerHTML += `<div style="margin-bottom:8px;"><b style="color:var(--blue);">Sam:</b> ${{escHtml(reply)}}</div>`;

    // If a meal was logged, show macro confirmation + refresh food strip
    if (d.logged && d.meal) {{
      const m = d.meal;
      const macroLine = [
        m.protein_g != null ? m.protein_g + 'g protein' : null,
        m.calories   != null ? m.calories + ' kcal'     : null,
      ].filter(Boolean).join(' · ');
      if (macroLine) {{
        msgs.innerHTML += `<div style="margin-bottom:8px;padding:5px 8px;background:var(--surface-3);border-radius:6px;font-size:11px;color:var(--text-2);">
          ✅ Logged: <b>${{escHtml(m.name || 'meal')}}</b>${{macroLine ? ' — ' + macroLine : ''}}</div>`;
      }}
      samLoadFoodLog();
    }}

    // Show any K+ or health warnings
    if (d.warnings && d.warnings.length) {{
      const warnHtml = d.warnings.map(w => `⚠️ ${{escHtml(w)}}`).join('<br>');
      msgs.innerHTML += `<div style="margin-bottom:8px;padding:5px 8px;background:rgba(251,191,36,.12);border:1px solid rgba(251,191,36,.3);border-radius:6px;font-size:11px;color:var(--amber);">${{warnHtml}}</div>`;
    }}

    // Switch to food mode automatically if backend detected food message
    if (d.mode === 'food' && _samChatMode === 'chat') {{
      samSwitchMode('food');
    }}

    msgs.scrollTop = msgs.scrollHeight;
    _samHistory.push({{role:'assistant', content:reply}});
    voiceSpeak(reply);
  }} catch(e) {{
    document.getElementById('sam-typing')?.remove();
    msgs.innerHTML += `<div style="color:var(--red);">Connection error</div>`;
  }}
}}

// ─── Health Digital Twin ────────────────────────────────────────────────────
async function loadHealthTwin() {{
  const grid = document.getElementById('health-twin-grid');
  if (!grid) return;
  try {{
    const res = await fetch('/api/health/twin/project?months=12').catch(() => null);
    if (!res || !res.ok) {{
      grid.innerHTML = _healthTwinFallback();
      return;
    }}
    const data = await res.json();
    const projs = data.projections || [];
    if (!projs.length) {{ grid.innerHTML = _healthTwinFallback(); return; }}
    grid.innerHTML = projs.map(p => {{
      const dir = p.direction || 'stable';
      const col = dir === 'improving' ? 'var(--green)' : dir === 'worsening' ? 'var(--red,#ef4444)' : 'var(--amber)';
      const arrow = dir === 'improving' ? '↑' : dir === 'worsening' ? '↓' : '→';
      return `<div style="background:var(--surface-2);border-radius:8px;padding:12px;border:1px solid var(--border);">
        <div style="font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-3);margin-bottom:6px;">${{p.metric || '—'}}</div>
        <div style="font-size:10px;color:var(--text-3);margin-bottom:4px;">Now: <b style="color:var(--text-1);">${{p.current_value || '—'}}</b></div>
        <div style="font-size:18px;font-weight:700;font-family:var(--font-mono);color:${{col}};">${{p.projected_value || '—'}} ${{arrow}}</div>
        <div style="font-size:9px;color:var(--text-3);margin-top:4px;">${{p.confidence_interval ? 'CI: ' + p.confidence_interval : '12-mo forecast'}}</div>
      </div>`;
    }}).join('');
  }} catch(e) {{
    grid.innerHTML = _healthTwinFallback();
  }}
}}

function _healthTwinFallback() {{
  const FALLBACK = [
    {{ metric:'A1c', now:'7.3%', proj:'7.1%', dir:'improving', note:'If GLP-1 + diet maintained' }},
    {{ metric:'LDL', now:'156', proj:'145', dir:'worsening', note:'Needs ezetimibe escalation' }},
    {{ metric:'SBP', now:'118', proj:'115', dir:'improving', note:'Olmesartan + current regimen' }},
    {{ metric:'HRV', now:'45ms', proj:'53ms', dir:'improving', note:'If CPAP initiated' }},
    {{ metric:'Weight', now:'247lb', proj:'229lb', dir:'improving', note:'GLP-1 + bariatric trajectory' }},
    {{ metric:'eGFR', now:'87', proj:'82', dir:'worsening', note:'CKD progression — monitor K+' }},
  ];
  return FALLBACK.map(p => {{
    const col = p.dir === 'improving' ? 'var(--green)' : p.dir === 'worsening' ? 'var(--red,#ef4444)' : 'var(--amber)';
    const arrow = p.dir === 'improving' ? '↑' : p.dir === 'worsening' ? '↓' : '→';
    return `<div style="background:var(--surface-2);border-radius:8px;padding:12px;border:1px solid var(--border);">
      <div style="font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-3);margin-bottom:6px;">${{p.metric}}</div>
      <div style="font-size:10px;color:var(--text-3);margin-bottom:4px;">Now: <b style="color:var(--text-1);">${{p.now}}</b></div>
      <div style="font-size:18px;font-weight:700;font-family:var(--font-mono);color:${{col}};">${{p.proj}} ${{arrow}}</div>
      <div style="font-size:9px;color:var(--text-3);margin-top:4px;">${{p.note}}</div>
    </div>`;
  }}).join('');
}}

async function loadOverviewHealth() {{
  const el    = document.getElementById('overview-health-content');
  const badge = document.getElementById('overview-health-badge');
  if (!el) return;
  loadEnvData();
  try {{
    const [res, lonRes] = await Promise.all([
      fetch('/api/health/summary').catch(() => null),
      fetch('/api/health/longevity/estimate').catch(() => null),
    ]);
    if (!res || !res.ok) return;
    const d = await res.json();
    const r = d.readiness || {{}};
    const m = d.metrics   || {{}};
    if (badge) badge.textContent = r.score != null ? r.grade || r.score : '—';

    if (!d.has_data) {{
      el.innerHTML = '<div style="color:var(--text-3);font-size:11px;">No data — configure Health Auto Export</div>';
      return;
    }}

    // ── Build Top 3 priority items ────────────────────────────────────────
    const items = [];

    // 1. Readiness — what today's energy budget looks like
    if (r.score != null) {{
      const sc  = r.score;
      const col = sc >= 80 ? 'var(--green)' : sc >= 60 ? 'var(--amber)' : 'var(--red,#ef4444)';
      const msg = sc >= 85 ? 'Green light — full capacity' :
                  sc >= 70 ? 'Moderate — manage intensity' :
                  sc >= 50 ? 'Recovery day recommended' : 'Rest priority today';
      items.push({{ icon: sc >= 80 ? '✓' : '!', label: 'Readiness', val: sc + '/100 ' + (r.grade || ''), note: msg, col }});
    }}

    // 2. Recovery quality — sleep + HRV together
    const sl  = m.sleep_hours, hrv = m.hrv, hr = m.resting_hr;
    if (sl || hrv) {{
      const parts = [];
      if (sl)  parts.push(sl + 'h sleep');
      if (hrv) parts.push('HRV ' + hrv + 'ms');
      if (hr)  parts.push(hr + 'bpm');
      const ok  = (sl >= 7) && (hrv >= 45);
      const col = ok ? 'var(--green)' : 'var(--amber)';
      items.push({{ icon: ok ? '✓' : '→', label: 'Recovery', val: parts.join(' · '), note: ok ? 'Well rested' : 'Sub-optimal recovery', col }});
    }}

    // 3. Priority watchpoint — anomaly if present, else K+/LDL safety note + LE
    const anom = d.anomalies || [];
    if (anom.length) {{
      const a   = anom[0];
      const col = 'var(--amber)';
      items.push({{ icon: '⚠', label: 'Alert', val: a.metric || 'Lab flag', note: (a.message || a.detail || '').slice(0,60), col }});
    }} else {{
      let leStr = '';
      if (lonRes && lonRes.ok) {{
        const lon = await lonRes.json();
        const le  = lon.estimated_life_expectancy || lon.life_expectancy;
        if (le) leStr = 'LE ' + le + 'yr · ' + (lon.years_remaining || (le - 52)) + ' remaining';
      }}
      items.push({{ icon: '→', label: 'Watch', val: 'K⁺  ·  LDL 156↑', note: leStr || 'Monitor: ARB + spiro · ezetimibe target', col: 'var(--text-2)' }});
    }}

    // ── Render ────────────────────────────────────────────────────────────
    el.innerHTML = items.slice(0, 3).map((it, i) => `
      <div style="${{i > 0 ? 'border-top:1px solid var(--border);margin-top:7px;padding-top:7px;' : ''}}display:flex;align-items:flex-start;gap:8px;">
        <span style="font-size:10px;color:${{it.col}};margin-top:2px;flex-shrink:0;">${{it.icon}}</span>
        <div style="min-width:0;flex:1;">
          <div style="display:flex;align-items:baseline;gap:6px;flex-wrap:wrap;">
            <span style="font-size:9px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--text-3);">${{it.label}}</span>
            <span style="font-size:12px;font-weight:600;color:${{it.col}};">${{escHtml(it.val)}}</span>
          </div>
          ${{it.note ? `<div style="font-size:10px;color:var(--text-3);margin-top:1px;">${{escHtml(it.note)}}</div>` : ''}}
        </div>
      </div>`).join('');
    // Sam's daily priority quote
    try {{
      const samRes = await fetch('/api/health/sam/daily').catch(() => null);
      if (samRes && samRes.ok) {{
        const sd = await samRes.json();
        const greeting = sd.protocol && sd.protocol.greeting;
        const move = sd.protocol && sd.protocol.movement && sd.protocol.movement.primary;
        if (greeting || move) {{
          el.innerHTML += `<div style="border-top:1px solid var(--border);margin-top:7px;padding-top:7px;display:flex;gap:8px;align-items:flex-start;">
            <span style="font-size:12px;">🦅</span>
            <div style="min-width:0;">
              ${{move ? `<div style="font-size:11px;font-weight:600;color:var(--blue);">${{escHtml(move)}}</div>` : ''}}
              ${{greeting ? `<div style="font-size:10px;color:var(--text-3);font-style:italic;">"${{escHtml(greeting.slice(0,60))}}${{greeting.length>60?'…':''}}"</div>` : ''}}
            </div>
          </div>`;
        }}
      }}
    }} catch(_) {{}}
  }} catch(e) {{
    if (el) el.innerHTML = '<div style="color:var(--text-3);">Unavailable</div>';
  }}
}}

/* ═══ DAILY HEALTH SCORE ═══ */

async function loadDailyHealthScore() {{
  try {{
    const [scoreRes, histRes] = await Promise.all([
      fetch('/api/health/score').catch(() => null),
      fetch('/api/health/score/history?days=30').catch(() => null),
    ]);
    if (scoreRes && scoreRes.ok) {{
      const d = await scoreRes.json();
      renderDailyScorePanel(d);
      renderSamOvScore(d);
    }}
    if (histRes && histRes.ok) {{
      const hist = await histRes.json();
      renderScoreSparkline(hist);
    }}
  }} catch(e) {{ console.warn("loadDailyHealthScore:", e); }}
}}

function renderDailyScorePanel(d) {{
  const score = d.score ?? null;
  const ring  = document.getElementById("dhs-ring");
  const sc    = document.getElementById("dhs-score");
  const gr    = document.getElementById("dhs-grade");
  const dt    = document.getElementById("dhs-date");
  const brk   = document.getElementById("dhs-breakdown");
  if (!sc) return;

  if (score === null) {{
    sc.textContent = "—";
    gr.textContent = "No data";
    return;
  }}

  const color = d.color || (score >= 75 ? "#10b981" : score >= 50 ? "#f59e0b" : "#ef4444");
  sc.textContent = score;
  sc.style.color = color;
  gr.textContent = d.grade || "—";
  if (dt) dt.textContent = d.date || "Today";

  // Animate ring (circumference = 2π×30 ≈ 188.5)
  if (ring) {{
    ring.style.stroke = color;
    ring.style.strokeDashoffset = String(188.5 - (score / 100) * 188.5);
  }}

  // Domain breakdown bars
  if (brk && d.breakdown) {{
    const domains = [
      {{ key: "sleep",      label: "Sleep",    max: 20 }},
      {{ key: "glycemic",   label: "Glycemic", max: 18 }},
      {{ key: "exercise",   label: "Exercise", max: 15 }},
      {{ key: "hydration",  label: "Hydration",max: 10 }},
      {{ key: "protein",    label: "Protein",  max: 10 }},
      {{ key: "mental",     label: "Mental",   max: 10 }},
      {{ key: "adherence",  label: "Protocol", max: 10 }},
      {{ key: "baseline",   label: "Baseline", max: 7  }},
    ];
    brk.innerHTML = domains.map(dom => {{
      const info = d.breakdown[dom.key] || {{}};
      const pts  = info.pts ?? 0;
      const pct  = Math.round((pts / dom.max) * 100);
      const col  = pct >= 75 ? "#10b981" : pct >= 50 ? "#f59e0b" : "#ef4444";
      return `<div class="score-domain-bar" title="${{escHtml(info.detail || "")}}">
        <span class="score-domain-label">${{dom.label}}</span>
        <div class="score-domain-track">
          <div class="score-domain-fill" style="width:${{pct}}%;background:${{col}};"></div>
        </div>
        <span class="score-domain-pts">${{pts}}/${{dom.max}}</span>
      </div>`;
    }}).join("");
  }}
}}

function renderSamOvScore(d) {{
  const row   = document.getElementById("sam-ov-score-row");
  const badge = document.getElementById("sam-ov-score-badge");
  const label = document.getElementById("sam-ov-score-label");
  if (!row || !badge) return;
  const score = d.score ?? null;
  if (score === null) return;
  const color = d.color || (score >= 75 ? "#10b981" : score >= 50 ? "#f59e0b" : "#ef4444");
  badge.textContent = score + "/100";
  badge.style.color = color;
  label.textContent = (d.grade || "") + " — " + (score >= 75 ? "Strong day" : score >= 50 ? "Average day" : "Tough day");
  row.style.display = "";
}}

function renderScoreSparkline(history) {{
  const svg = document.getElementById("dhs-sparkline");
  if (!svg) return;

  const valid = (history || []).filter(h => h.score !== null && h.score !== undefined);
  if (valid.length < 2) {{
    svg.innerHTML = '<text x="140" y="24" text-anchor="middle" fill="rgba(255,255,255,0.2)" font-size="10">Not enough data yet</text>';
    return;
  }}

  const W = 280, H = 44, PAD = 4;
  const scores = valid.map(h => h.score);
  const minS = Math.max(0,  Math.min(...scores) - 5);
  const maxS = Math.min(100, Math.max(...scores) + 5);
  const xStep = (W - PAD * 2) / (valid.length - 1);

  const pts = valid.map((h, i) => {{
    const x = PAD + i * xStep;
    const y = H - PAD - ((h.score - minS) / (maxS - minS + 1)) * (H - PAD * 2);
    return {{ x, y, score: h.score, date: h.date, color: h.color || "#f59e0b" }};
  }});

  const polyPts = pts.map(p => `${{p.x.toFixed(1)}},${{p.y.toFixed(1)}}`).join(" ");

  // gradient fill path
  const fillPath = "M " + pts[0].x.toFixed(1) + "," + H +
    " L " + pts.map(p => `${{p.x.toFixed(1)}},${{p.y.toFixed(1)}}`).join(" L ") +
    " L " + pts[pts.length-1].x.toFixed(1) + "," + H + " Z";

  // reference lines at 75 and 50
  const y75 = H - PAD - ((75 - minS) / (maxS - minS + 1)) * (H - PAD * 2);
  const y50 = H - PAD - ((50 - minS) / (maxS - minS + 1)) * (H - PAD * 2);

  // color the polyline segments
  const segLines = pts.slice(1).map((p, i) => {{
    const prev = pts[i];
    const col  = p.color || "#f59e0b";
    return `<line x1="${{prev.x.toFixed(1)}}" y1="${{prev.y.toFixed(1)}}" x2="${{p.x.toFixed(1)}}" y2="${{p.y.toFixed(1)}}" stroke="${{col}}" stroke-width="1.5" stroke-linecap="round"/>`;
  }}).join("");

  // dots for each data point
  const dotCircles = pts.map(p =>
    `<circle cx="${{p.x.toFixed(1)}}" cy="${{p.y.toFixed(1)}}" r="2" fill="${{p.color || "#f59e0b"}}" opacity="0.8">
      <title>${{p.date}}: ${{p.score}}</title>
    </circle>`
  ).join("");

  svg.innerHTML = `
    <defs>
      <linearGradient id="spark-grad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#10b981" stop-opacity="0.15"/>
        <stop offset="100%" stop-color="#10b981" stop-opacity="0"/>
      </linearGradient>
    </defs>
    ${{y75 > 0 && y75 < H ? `<line x1="${{PAD}}" y1="${{y75.toFixed(1)}}" x2="${{W-PAD}}" y2="${{y75.toFixed(1)}}" stroke="rgba(16,185,129,0.2)" stroke-width="1" stroke-dasharray="3,3"/>` : ""}}
    ${{y50 > 0 && y50 < H ? `<line x1="${{PAD}}" y1="${{y50.toFixed(1)}}" x2="${{W-PAD}}" y2="${{y50.toFixed(1)}}" stroke="rgba(245,158,11,0.2)" stroke-width="1" stroke-dasharray="3,3"/>` : ""}}
    <path d="${{fillPath}}" fill="url(#spark-grad)"/>
    ${{segLines}}
    ${{dotCircles}}
  `;
}}

/* ── Boot ── */
document.addEventListener('DOMContentLoaded', init);

/* ═══════════════════════════════════════════════════════════════
   NAVIGATION / WAZE
═══════════════════════════════════════════════════════════════ */
var _navMap = null;
var _navDirectionsRenderer = null;
var _navDirectionsService = null;
var _navMarkers = [];
var _navPOIMarkers = {{}};
var _navWatchId = null;
var _navSteps = [];
var _navCurrentStepIdx = 0;
var _navPOIs = [];
var _navVoiceOn = true;
var _navActivePOICategories = new Set(['food','starbucks','parks','historic','family']);
var _navUserMarker = null;
var _navRouteData = null;
var _navAlertTimer = null;
var _navLastAnnouncedPOI = null;
var _navGoogleMapsLoaded = false;
var _navParksRadius = 25;
var _navHomeAddress = '8384 Riley Rd, Alexandria, KY 41001';

function navSetHome() {{
    var el = document.getElementById('nav-origin');
    if (el) {{
        el.value = _navHomeAddress;
        document.getElementById('nav-origin-results').innerHTML = '';
    }}
}}

function navUseCurrentLocation() {{
    if (!navigator.geolocation) {{ showToast('Geolocation not available'); return; }}
    navigator.geolocation.getCurrentPosition(function(pos) {{
        var el = document.getElementById('nav-origin');
        if (el) el.value = pos.coords.latitude.toFixed(6) + ',' + pos.coords.longitude.toFixed(6);
    }}, function() {{ showToast('Could not get your location'); }});
}}

function navUpdateParksRadius(val) {{
    _navParksRadius = parseInt(val, 10);
    var lbl = document.getElementById('nav-parks-radius-label');
    if (lbl) lbl.textContent = _navParksRadius + ' mi';
    // Update slider gradient fill
    var slider = document.getElementById('nav-parks-radius');
    if (slider) {{
        var pct = ((_navParksRadius - 5) / 95 * 100).toFixed(1);
        slider.style.background = 'linear-gradient(to right, #4CAF50 0%, #4CAF50 ' + pct + '%, rgba(255,255,255,0.15) ' + pct + '%)';
    }}
}}

function initNavView() {{
    if (_navMap) return;
    // Load home address from server
    fetch('/api/nav/home').then(function(r) {{ return r.json(); }}).then(function(d) {{
        if (d.address) _navHomeAddress = d.address;
    }});
    if (!_navGoogleMapsLoaded) {{
        loadGoogleMapsScript();
    }}
}}

var _navMapsKey = '';

function loadGoogleMapsScript() {{
    fetch('/api/nav/maps-key').then(function(r) {{ return r.json(); }}).then(function(d) {{
        _navMapsKey = d.key || '';
        var s = document.createElement('script');
        s.src = 'https://maps.googleapis.com/maps/api/js?key=' + d.key + '&libraries=places&callback=onGoogleMapsReady';
        s.async = true;
        document.head.appendChild(s);
    }});
}}

function onGoogleMapsReady() {{
    _navGoogleMapsLoaded = true;
    _navMap = new google.maps.Map(document.getElementById('nav-map'), {{
        center: {{lat: 37.09, lng: -95.71}},
        zoom: 5,
        styles: _navDarkMapStyles(),
        disableDefaultUI: false,
        zoomControl: true
    }});
    _navDirectionsRenderer = new google.maps.DirectionsRenderer({{
        map: _navMap,
        suppressMarkers: false,
        polylineOptions: {{strokeColor: '#00D4FF', strokeWeight: 5}}
    }});
    if (navigator.geolocation) {{
        navigator.geolocation.getCurrentPosition(function(pos) {{
            _navMap.setCenter({{lat: pos.coords.latitude, lng: pos.coords.longitude}});
            _navMap.setZoom(12);
        }});
    }}
}}

function navAutocomplete(inputId, resultsId) {{
    var val = document.getElementById(inputId).value;
    if (val.length < 3) {{ document.getElementById(resultsId).innerHTML = ''; return; }}
    fetch('/api/nav/autocomplete?q=' + encodeURIComponent(val))
        .then(function(r) {{ return r.json(); }}).then(function(d) {{
            var html = '';
            (d.predictions || []).forEach(function(p) {{
                html += '<div class="nav-autocomplete-item" data-input="' + escHtml(inputId) + '" data-results="' + escHtml(resultsId) + '" data-desc="' + escHtml(p.description) + '" onclick="navSelectPlace(this.dataset.input,this.dataset.results,this.dataset.desc)">' + escHtml(p.description) + '</div>';
            }});
            document.getElementById(resultsId).innerHTML = html;
        }});
}}

function navSelectPlace(inputId, resultsId, desc) {{
    document.getElementById(inputId).value = desc;
    document.getElementById(resultsId).innerHTML = '';
}}

function navSwapInputs() {{
    var o = document.getElementById('nav-origin').value;
    var d = document.getElementById('nav-dest').value;
    document.getElementById('nav-origin').value = d;
    document.getElementById('nav-dest').value = o;
}}

function navGetRoute() {{
    var origin = document.getElementById('nav-origin').value;
    var dest = document.getElementById('nav-dest').value;
    if (!origin || !dest) {{ showToast('Enter origin and destination'); return; }}
    showToast('Getting route...');
    fetch('/api/nav/route', {{
        method: 'POST',
        headers: {{'Content-Type':'application/json'}},
        body: JSON.stringify({{origin: origin, destination: dest}})
    }}).then(function(r) {{ return r.json(); }}).then(function(data) {{
        if (data.error || !data.routes || !data.routes.length) {{
            showToast('Route not found'); return;
        }}
        _navRouteData = data;
        renderNavRoute(data);
        loadNavPOIs(data);
    }});
}}

function renderNavRoute(data) {{
    var route = data.routes[0];
    var leg = route.legs[0];
    _navSteps = leg.steps;
    _navCurrentStepIdx = 0;

    if (_navDirectionsRenderer) {{
        var request = {{
            origin: document.getElementById('nav-origin').value,
            destination: document.getElementById('nav-dest').value,
            travelMode: google.maps.TravelMode.DRIVING
        }};
        if (!_navDirectionsService) _navDirectionsService = new google.maps.DirectionsService();
        _navDirectionsService.route(request, function(result, status) {{
            if (status === 'OK') _navDirectionsRenderer.setDirections(result);
        }});
    }}

    document.getElementById('nav-dist').textContent = leg.distance.text;
    document.getElementById('nav-time').textContent = leg.duration.text;
    var eta = new Date(Date.now() + leg.duration.value * 1000);
    document.getElementById('nav-eta').textContent = eta.toLocaleTimeString([], {{hour:'2-digit',minute:'2-digit'}});
    document.getElementById('nav-summary-bar').style.display = 'flex';

    var html = '';
    leg.steps.forEach(function(step, i) {{
        var instr = step.html_instructions.replace(/<[^>]+>/g,' ').trim();
        var arrow = _navStepArrow(step.maneuver || '');
        html += '<div class="nav-turn-card">'
            + '<div class="nav-turn-icon">' + arrow + '</div>'
            + '<div><div style="font-weight:500">' + instr + '</div>'
            + '<div style="font-size:11px;opacity:0.6">' + step.distance.text + '</div></div>'
            + '</div>';
    }});
    document.getElementById('nav-turns-list').innerHTML = html;
    document.getElementById('nav-turns-section').style.display = 'block';
    document.getElementById('nav-start-btn').style.display = 'block';
    // Show aerial view of destination
    var dest = document.getElementById('nav-dest') ? document.getElementById('nav-dest').value : '';
    if (dest) showAerialView(dest);
    // Show street view of first turn
    updateStreetViewPreview(0);
}}

function _navStepArrow(maneuver) {{
    var map = {{
        'turn-left':'←', 'turn-right':'→',
        'turn-slight-left':'↖', 'turn-slight-right':'↗',
        'turn-sharp-left':'↰', 'turn-sharp-right':'↱',
        'uturn-left':'↩', 'uturn-right':'↪',
        'ramp-left':'↖', 'ramp-right':'↗',
        'merge':'↑', 'fork-left':'↖', 'fork-right':'↗',
        'ferry':'⛴', 'roundabout-left':'↺', 'roundabout-right':'↻',
        '':'↑'
    }};
    return map[maneuver] || '↑';
}}

function loadNavPOIs(data) {{
    var route = data.routes[0];
    var polyline = route.overview_polyline.points;
    var totalMiles = route.legs.reduce(function(sum, l) {{ return sum + l.distance.value; }}, 0) / 1609.34;
    var cats = Array.from(_navActivePOICategories);
    var waypoints = data.geocoded_waypoints || [];
    fetch('/api/nav/pois', {{
        method: 'POST',
        headers: {{'Content-Type':'application/json'}},
        body: JSON.stringify({{
            encoded_polyline: polyline,
            categories: cats,
            total_miles: totalMiles,
            geocoded_waypoints: waypoints,
            parks_radius_miles: _navParksRadius
        }})
    }}).then(function(r) {{ return r.json(); }}).then(function(d) {{
        renderNavPOIs(d.pois || {{}}, d.nps_parks || []);
    }});
}}

function renderNavPOIs(pois, npsParks) {{
    _navMarkers.forEach(function(m) {{ m.setMap(null); }});
    _navMarkers = [];

    var colors = {{food:'#FF6B35',starbucks:'#00704A',parks:'#2D6A4F',historic:'#C9A84C',family:'#7B2D8B',gas:'#2196F3'}};
    var emojis = {{food:'🍔',starbucks:'☕',parks:'🌲',historic:'🏛',family:'⭐',gas:'⛽'}};
    var allPOIs = [];

    Object.keys(pois).forEach(function(cat) {{
        if (!_navActivePOICategories.has(cat)) return;
        (pois[cat] || []).forEach(function(poi) {{
            allPOIs.push(Object.assign({{}}, poi, {{category: cat}}));
            if (!_navMap) return;
            var marker = new google.maps.Marker({{
                position: {{lat: poi.lat, lng: poi.lng}},
                map: _navMap,
                title: poi.name,
                icon: {{
                    path: google.maps.SymbolPath.CIRCLE,
                    fillColor: colors[cat] || '#888',
                    fillOpacity: 0.9,
                    strokeColor: '#fff',
                    strokeWeight: 2,
                    scale: 10
                }}
            }});
            var infoContent = '<div style="color:#000"><strong>' + poi.name + '</strong>'
                + (poi.rating ? '<br>⭐ ' + poi.rating : '')
                + (poi.address ? '<br>' + poi.address : '')
                + '<br><em>~' + (poi.route_mile_marker || '?') + ' mi mark</em></div>';
            var infoWindow = new google.maps.InfoWindow({{content: infoContent}});
            marker.addListener('click', function() {{ infoWindow.open(_navMap, marker); }});
            _navMarkers.push(marker);
        }});
    }});

    // Add NPS parks as enriched POIs with map markers
    npsParks.forEach(function(park) {{
        var plat = parseFloat(park.latitude || 0);
        var plng = parseFloat(park.longitude || 0);
        var npsPoi = {{
            name: park.fullName,
            category: 'parks',
            lat: plat,
            lng: plng,
            route_mile_marker: park.route_mile_marker || null,
            distance_from_route: park.distance_from_route || null,
            description: park.description || '',
            url: park.url || '',
            is_nps: true,
            states: park.states || ''
        }};
        allPOIs.push(npsPoi);
        if (!_navMap || !plat || !plng) return;
        var marker = new google.maps.Marker({{
            position: {{lat: plat, lng: plng}},
            map: _navMap,
            title: park.fullName,
            icon: {{
                path: google.maps.SymbolPath.CIRCLE,
                fillColor: '#2D6A4F',
                fillOpacity: 1.0,
                strokeColor: '#81C784',
                strokeWeight: 2,
                scale: 12
            }}
        }});
        var infoContent = '<div style="color:#000; max-width:260px">'
            + '<strong>' + park.fullName + '</strong>'
            + (park.distance_from_route ? '<br><em>' + park.distance_from_route + ' mi from route</em>' : '')
            + (park.description ? '<br><span style="font-size:11px">' + park.description + '</span>' : '')
            + (park.url ? '<br><a href="' + park.url + '" target="_blank">NPS Page &#8599;</a>' : '')
            + '</div>';
        var infoWindow = new google.maps.InfoWindow({{content: infoContent}});
        marker.addListener('click', function() {{ infoWindow.open(_navMap, marker); }});
        _navMarkers.push(marker);
    }});

    _navPOIs = allPOIs;

    // ── Sidebar list — NPS section first, then regular POIs ──
    var npsHtml = '';
    var regularHtml = '';
    var sorted = allPOIs.slice().sort(function(a,b) {{ return (a.route_mile_marker||0) - (b.route_mile_marker||0); }});

    sorted.forEach(function(poi) {{
        if (poi.is_nps) {{
            npsHtml += '<div class="nav-nps-card" data-url="' + (poi.url||'') + '" onclick="navOpenNPS(this)">'
                + '<div style="font-size:22px">&#127794;</div>'
                + '<div style="flex:1">'
                + '<div style="font-weight:600; font-size:13px">' + poi.name + '</div>'
                + (poi.description ? '<div style="font-size:11px;opacity:0.6;margin-top:2px;line-height:1.3">' + poi.description.substring(0,120) + '&hellip;</div>' : '')
                + '<div style="display:flex; gap:6px; margin-top:4px; flex-wrap:wrap;">'
                + (poi.route_mile_marker ? '<span class="nav-nps-badge">mi ' + poi.route_mile_marker + '</span>' : '')
                + (poi.distance_from_route ? '<span class="nav-nps-badge">&#8599; ' + poi.distance_from_route + ' mi off route</span>' : '')
                + (poi.states ? '<span class="nav-nps-badge">' + poi.states + '</span>' : '')
                + '</div>'
                + '</div>'
                + '</div>';
        }} else {{
            var e = emojis[poi.category] || '&#128205;';
            regularHtml += '<div class="nav-poi-card">'
                + '<div style="font-size:20px">' + e + '</div>'
                + '<div style="flex:1">'
                + '<div style="font-weight:500">' + poi.name + '</div>'
                + (poi.address ? '<div style="font-size:11px;opacity:0.6">' + poi.address + '</div>' : '')
                + '</div>'
                + (poi.route_mile_marker ? '<div class="nav-poi-distance-chip">mi ' + poi.route_mile_marker + '</div>' : '')
                + '</div>';
        }}
    }});

    var html = '';
    if (npsHtml) {{
        html += '<div class="nav-section-title" style="margin-top:12px;">&#127794; National Parks &amp; Historic Sites</div>' + npsHtml;
    }}
    if (regularHtml) {{
        html += '<div class="nav-section-title" style="margin-top:12px;">Nearby Stops</div>' + regularHtml;
    }}
    document.getElementById('nav-pois-list').innerHTML = html || '<div style="padding:16px;opacity:0.5">No POIs found. Try enabling more categories or increasing the parks radius.</div>';
    document.getElementById('nav-pois-section').style.display = 'block';
}}

function navOpenNPS(el) {{
    var url = el.getAttribute('data-url');
    if (url) window.open(url, '_blank');
}}

function navTogglePOI(cat) {{
    var btn = document.querySelector('.nav-poi-toggle[data-cat="' + cat + '"]');
    if (_navActivePOICategories.has(cat)) {{
        _navActivePOICategories.delete(cat);
        if (btn) btn.classList.remove('active');
    }} else {{
        _navActivePOICategories.add(cat);
        if (btn) btn.classList.add('active');
    }}
    if (_navRouteData) loadNavPOIs(_navRouteData);
}}

function startNavigation() {{
    if (!navigator.geolocation) {{ showToast('Geolocation not available'); return; }}
    document.getElementById('nav-start-btn').style.display = 'none';
    document.getElementById('nav-stop-btn').style.display = 'block';
    document.getElementById('nav-hud').style.display = 'block';
    document.getElementById('nav-eta-strip').style.display = 'flex';
    _navCurrentStepIdx = 0;
    _updateNavHUD();
    _navWatchId = navigator.geolocation.watchPosition(_navGPSUpdate, function(e) {{
        showToast('GPS error: ' + e.message);
    }}, {{enableHighAccuracy: true, maximumAge: 2000, timeout: 10000}});
    if (_navVoiceOn && _navSteps.length) {{
        var first = _navSteps[0].html_instructions.replace(/<[^>]+>/g,' ').trim();
        _navSpeak('Starting navigation. ' + first);
    }}
}}

function stopNavigation() {{
    if (_navWatchId !== null) {{ navigator.geolocation.clearWatch(_navWatchId); _navWatchId = null; }}
    document.getElementById('nav-hud').style.display = 'none';
    document.getElementById('nav-eta-strip').style.display = 'none';
    document.getElementById('nav-stop-btn').style.display = 'none';
    document.getElementById('nav-start-btn').style.display = 'block';
    if (_navUserMarker) {{ _navUserMarker.setMap(null); _navUserMarker = null; }}
}}

function _navGPSUpdate(pos) {{
    var lat = pos.coords.latitude, lng = pos.coords.longitude;
    if (_navMap) {{
        _navMap.setCenter({{lat: lat, lng: lng}});
        if (_navMap.getZoom() < 15) _navMap.setZoom(15);
        if (!_navUserMarker) {{
            _navUserMarker = new google.maps.Marker({{
                position: {{lat: lat, lng: lng}},
                map: _navMap,
                icon: {{path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW, scale: 6, fillColor: '#00D4FF', fillOpacity: 1, strokeColor: '#fff', strokeWeight: 2, rotation: pos.coords.heading || 0}}
            }});
        }} else {{
            _navUserMarker.setPosition({{lat: lat, lng: lng}});
            if (pos.coords.heading) {{
                _navUserMarker.setIcon(Object.assign({{}}, _navUserMarker.getIcon(), {{rotation: pos.coords.heading}}));
            }}
        }}
    }}
    if (_navSteps.length && _navCurrentStepIdx < _navSteps.length) {{
        var step = _navSteps[_navCurrentStepIdx];
        var stepLat = step.end_location.lat, stepLng = step.end_location.lng;
        var dist = _navHaversineJS(lat, lng, stepLat, stepLng);
        if (dist < 0.05) {{
            _navCurrentStepIdx++;
            if (_navCurrentStepIdx < _navSteps.length) {{
                _updateNavHUD();
                updateStreetViewPreview(_navCurrentStepIdx);
                if (_navVoiceOn) {{
                    var nextStep = _navSteps[_navCurrentStepIdx];
                    var instr = nextStep.html_instructions.replace(/<[^>]+>/g,' ').trim();
                    _navSpeak('In ' + nextStep.distance.text + ', ' + instr);
                }}
            }} else {{
                _navSpeak('You have arrived at your destination.');
                stopNavigation();
            }}
        }} else if (dist < 0.3 && _navCurrentStepIdx < _navSteps.length - 1) {{
            document.getElementById('nav-hud-dist').textContent = (dist * 5280).toFixed(0) + ' ft';
        }}
    }}
    _navCheckPOIAlert(lat, lng);
}}

function _updateNavHUD() {{
    if (_navCurrentStepIdx >= _navSteps.length) return;
    var step = _navSteps[_navCurrentStepIdx];
    var instr = step.html_instructions.replace(/<[^>]+>/g,' ').trim();
    var arrow = _navStepArrow(step.maneuver || '');
    document.getElementById('nav-hud-arrow').textContent = arrow;
    document.getElementById('nav-hud-dist').textContent = step.distance.text;
    document.getElementById('nav-hud-instr').textContent = instr;
    var remDist = 0, remTime = 0;
    for (var i = _navCurrentStepIdx; i < _navSteps.length; i++) {{
        remDist += _navSteps[i].distance.value;
        remTime += _navSteps[i].duration.value;
    }}
    var remMiles = (remDist / 1609.34).toFixed(1) + ' mi';
    var etaDate = new Date(Date.now() + remTime * 1000);
    var etaStr = etaDate.toLocaleTimeString([], {{hour:'2-digit',minute:'2-digit'}});
    document.getElementById('nav-hud-eta').textContent = etaStr;
    document.getElementById('nav-hud-remain').textContent = remMiles;
    updateStreetViewPreview(_navCurrentStepIdx);
}}

// ── AERIAL VIEW ──────────────────────────────────────────────────────────────
// ── Aerial View — browser-side polling (URLs are signed for the browser's IP) ─
function _aerialFallback(video, fallback, loadingEl) {{
    if (window._aerialFallbackShown) return;
    window._aerialFallbackShown = true;
    if (window._aerialHls) {{ window._aerialHls.destroy(); window._aerialHls = null; }}
    video.style.display = 'none';
    if (loadingEl) loadingEl.style.display = 'none';
    fallback.style.display = 'block';
    var destLat = 0, destLng = 0;
    if (_navRouteData && _navRouteData.routes && _navRouteData.routes[0]) {{
        var legs = _navRouteData.routes[0].legs;
        var lastLeg = legs[legs.length - 1];
        destLat = lastLeg.end_location.lat;
        destLng = lastLeg.end_location.lng;
    }}
    fallback.src = '/api/nav/streetview?lat=' + destLat + '&lng=' + destLng + '&heading=0&width=800&height=450';
    fallback.onerror = function() {{
        fallback.style.display = 'none';
        if (loadingEl) {{
            loadingEl.style.display = 'flex';
            loadingEl.innerHTML = '<div style="text-align:center;color:rgba(255,255,255,0.5)">&#127757; No aerial imagery available<br>for this destination</div>';
        }}
    }};
}}

function _aerialPlayVideo(d, video, fallback, loadingEl) {{
    if (loadingEl) loadingEl.style.display = 'none';
    // Extract landscape MP4 URL — browser-signed, CORS-enabled (acao=yes in URL)
    var mp4High = (d.uris && d.uris.MP4_HIGH && d.uris.MP4_HIGH.landscapeUri) || '';
    var mp4Med  = (d.uris && d.uris.MP4_MEDIUM && d.uris.MP4_MEDIUM.landscapeUri) || '';
    var mp4Low  = (d.uris && d.uris.MP4_LOW && d.uris.MP4_LOW.landscapeUri) || '';
    var hlsObj  = (d.uris && d.uris.HLS) || {{}};
    var hlsUri  = (typeof hlsObj === 'string') ? hlsObj : (hlsObj.landscapeUri || hlsObj.portraitUri || '');
    var videoUri = mp4High || mp4Med || mp4Low || d.videoUri || '';

    if (!hlsUri && !videoUri) {{
        _aerialFallback(video, fallback, loadingEl); return;
    }}
    video.style.display = 'block';
    fallback.style.display = 'none';
    // Safety net: if nothing plays after 15s, fall back to Street View
    var _safetyTimer = setTimeout(function() {{
        if (!window._aerialFallbackShown && (video.readyState === 0 || video.videoWidth === 0)) {{
            _aerialFallback(video, fallback, loadingEl);
        }}
    }}, 15000);

    function _onPlaySuccess() {{
        window._aerialFallbackShown = true; // cancel safety net from showing fallback
        clearTimeout(_safetyTimer);
    }}

    // Attempt 1: native HLS (Safari) or HLS.js with direct URL
    if (hlsUri) {{
        if (video.canPlayType('application/vnd.apple.mpegurl')) {{
            // Safari: native HLS support — direct URL works
            video.crossOrigin = 'anonymous';
            video.src = hlsUri;
            video.load();
            video.play().then(_onPlaySuccess).catch(function() {{
                video.muted = true;
                video.play().then(_onPlaySuccess).catch(function() {{ _aerialFallback(video, fallback, loadingEl); }});
            }});
            return;
        }}
        if (window.Hls && Hls.isSupported()) {{
            // Chrome/Firefox: use HLS.js with the direct URL (browser-signed → no 403)
            if (window._aerialHls) window._aerialHls.destroy();
            window._aerialHls = new Hls({{ maxBufferLength: 15, enableWorker: false, xhrSetup: function(xhr) {{ xhr.withCredentials = false; }} }});
            window._aerialHls.loadSource(hlsUri);
            window._aerialHls.attachMedia(video);
            window._aerialHls.on(Hls.Events.MANIFEST_PARSED, function() {{
                window._aerialFallbackShown = true;
                clearTimeout(_safetyTimer);
                video.muted = true; // ensure autoplay works
                video.play().catch(function() {{ _aerialFallback(video, fallback, loadingEl); }});
            }});
            window._aerialHls.on(Hls.Events.ERROR, function(ev, data) {{
                if (data.fatal) {{
                    // HLS.js failed — fall through to MP4
                    if (videoUri) {{
                        window._aerialHls.destroy(); window._aerialHls = null;
                        video.src = videoUri; video.crossOrigin = 'anonymous'; video.load();
                        video.muted = true;
                        video.play().then(_onPlaySuccess).catch(function() {{ _aerialFallback(video, fallback, loadingEl); }});
                    }} else {{
                        _aerialFallback(video, fallback, loadingEl);
                    }}
                }}
            }});
            return;
        }}
    }}
    // Attempt 2: direct MP4 (works in all modern browsers, CORS via acao=yes)
    if (videoUri) {{
        video.crossOrigin = 'anonymous';
        video.src = videoUri;
        video.load();
        video.muted = true;
        video.play().then(_onPlaySuccess).catch(function() {{ _aerialFallback(video, fallback, loadingEl); }});
        return;
    }}
    _aerialFallback(video, fallback, loadingEl);
}}

function showAerialView(destinationAddress) {{
    var modal = document.getElementById('nav-aerial-modal');
    var video = document.getElementById('nav-aerial-video');
    var fallback = document.getElementById('nav-aerial-fallback');
    var nameEl = document.getElementById('nav-aerial-dest-name');
    if (!modal) return;
    window._aerialFallbackShown = false;
    nameEl.textContent = destinationAddress;
    video.style.display = 'none';
    fallback.style.display = 'none';
    var loadingEl = document.getElementById('nav-aerial-loading');
    if (loadingEl) loadingEl.style.display = 'flex';
    modal.style.display = 'flex';

    if (!_navMapsKey) {{
        // Key not loaded yet — fall back to server proxy
        fetch('/api/nav/aerial?address=' + encodeURIComponent(destinationAddress))
            .then(function(r) {{ return r.json(); }})
            .then(function(d) {{ _aerialPlayVideo(d, video, fallback, loadingEl); }})
            .catch(function() {{ _aerialFallback(video, fallback, loadingEl); }});
        return;
    }}

    // Call Aerial View API directly from the browser — URLs are signed for the client IP
    var _aerialAttempt = 0;
    function _pollAerialDirect() {{
        fetch('https://aerialview.googleapis.com/v1/videos:lookupVideo?address='
              + encodeURIComponent(destinationAddress) + '&key=' + _navMapsKey)
            .then(function(r) {{ return r.json(); }})
            .then(function(d) {{
                var state = d.state || '';
                var hasVideo = d.videoUri || (d.uris && (d.uris.MP4_HIGH || d.uris.MP4_MEDIUM || d.uris.MP4_LOW || d.uris.HLS));
                if (hasVideo) {{
                    _aerialPlayVideo(d, video, fallback, loadingEl);
                }} else if (state === 'PROCESSING' && _aerialAttempt < 8) {{
                    _aerialAttempt++;
                    setTimeout(_pollAerialDirect, 2000);
                }} else {{
                    // No coverage or max attempts reached
                    _aerialFallback(video, fallback, loadingEl);
                }}
            }})
            .catch(function() {{ _aerialFallback(video, fallback, loadingEl); }});
    }}
    _pollAerialDirect();
}}

function closeAerialModal() {{
    var modal = document.getElementById('nav-aerial-modal');
    if (modal) modal.style.display = 'none';
    var video = document.getElementById('nav-aerial-video');
    if (video) {{ video.pause(); video.src = ''; }}
    if (window._aerialHls) {{ window._aerialHls.destroy(); window._aerialHls = null; }}
}}

// ── STREET VIEW TURN PREVIEW ─────────────────────────────────────────────────
function updateStreetViewPreview(stepIdx) {{
    if (!_navSteps || stepIdx >= _navSteps.length) return;
    var step = _navSteps[stepIdx];
    var lat = step.end_location.lat;
    var lng = step.end_location.lng;
    var heading = 0;
    var maneuverHeadings = {{
        'turn-right': 90, 'turn-sharp-right': 135, 'turn-slight-right': 45,
        'turn-left': 270, 'turn-sharp-left': 225, 'turn-slight-left': 315,
        'straight': 0, 'merge': 0
    }};
    if (step.maneuver && maneuverHeadings[step.maneuver] !== undefined) {{
        heading = maneuverHeadings[step.maneuver];
    }}
    var instr = (step.html_instructions || '').replace(/<[^>]+>/g, ' ').trim();
    var panel = document.getElementById('nav-sv-panel');
    var img = document.getElementById('nav-sv-img');
    var caption = document.getElementById('nav-sv-caption');
    if (!panel || !img) return;
    panel.style.display = 'block';
    img.src = '/api/nav/streetview?lat=' + lat + '&lng=' + lng + '&heading=' + heading;
    img.style.display = 'block';
    if (caption) caption.textContent = instr + ' (' + step.distance.text + ')';
}}

// ── ENV DATA (Air Quality + Pollen) ──────────────────────────────────────────
function loadEnvData() {{
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(function(pos) {{
        var lat = pos.coords.latitude;
        var lng = pos.coords.longitude;
        fetch('/api/env/air-quality?lat=' + lat + '&lng=' + lng)
            .then(function(r) {{ return r.json(); }})
            .then(function(d) {{ renderAirQuality(d); }});
        fetch('/api/env/pollen?lat=' + lat + '&lng=' + lng)
            .then(function(r) {{ return r.json(); }})
            .then(function(d) {{ renderPollen(d); }});
    }});
}}

function renderAirQuality(d) {{
    var el = document.getElementById('env-air-quality');
    if (!el) return;
    var indexes = d.indexes || [];
    if (!indexes.length) {{ el.innerHTML = '<span style="opacity:0.5">No data</span>'; return; }}
    var idx = indexes[0];
    var aqi = idx.aqi || '--';
    var cat = idx.category || '';
    var color = aqi <= 50 ? '#4CAF50' : aqi <= 100 ? '#FFC107' : aqi <= 150 ? '#FF9800' : '#F44336';
    el.innerHTML = '<span style="font-size:28px; font-weight:700; color:' + color + '">' + aqi + '</span>' +
        '<span style="font-size:12px; opacity:0.7; margin-left:8px">' + cat + '</span>';
}}

function renderPollen(d) {{
    var el = document.getElementById('env-pollen');
    if (!el) return;
    var days = d.dailyInfo || [];
    if (!days.length) {{ el.innerHTML = '<span style="opacity:0.5">No data</span>'; return; }}
    var day = days[0];
    var plants = day.plantInfo || [];
    var html = '';
    plants.slice(0, 4).forEach(function(p) {{
        var lvl = (p.indexInfo && p.indexInfo.value) || 0;
        var color = lvl <= 1 ? '#4CAF50' : lvl <= 2 ? '#FFC107' : lvl <= 3 ? '#FF9800' : '#F44336';
        html += '<div style="display:flex; align-items:center; gap:6px; margin-bottom:4px;">' +
            '<span style="width:8px; height:8px; border-radius:50%; background:' + color + '; display:inline-block;"></span>' +
            '<span style="font-size:12px">' + (p.displayName || p.plantTypeId || '') + '</span>' +
            '<span style="font-size:11px; opacity:0.6; margin-left:auto">' + (p.indexInfo && p.indexInfo.category || '') + '</span>' +
            '</div>';
    }});
    el.innerHTML = html || '<span style="opacity:0.5">No pollen data</span>';
}}

function _navCheckPOIAlert(lat, lng) {{
    var alert = document.getElementById('nav-poi-alert');
    var nearby = _navPOIs.filter(function(p) {{
        if (!p.lat || !p.lng) return false;
        return _navHaversineJS(lat, lng, p.lat, p.lng) < 1.0;
    }});
    if (!nearby.length) return;
    var closest = nearby.sort(function(a,b) {{
        return _navHaversineJS(lat, lng, a.lat, a.lng) - _navHaversineJS(lat, lng, b.lat, b.lng);
    }})[0];
    if (_navLastAnnouncedPOI === closest.name) return;
    _navLastAnnouncedPOI = closest.name;
    var dist = _navHaversineJS(lat, lng, closest.lat, closest.lng).toFixed(1);
    var emojiMap = {{food:'🍔',starbucks:'☕',parks:'🌲',historic:'🏛',family:'⭐',gas:'⛽'}};
    var em = emojiMap[closest.category] || '📍';
    document.getElementById('nav-poi-alert-icon').textContent = em;
    document.getElementById('nav-poi-alert-text').textContent = closest.name + ' in ' + dist + ' miles';
    alert.classList.add('visible');
    if (_navVoiceOn) _navSpeak(closest.name + ' in ' + dist + ' miles');
    if (_navAlertTimer) clearTimeout(_navAlertTimer);
    _navAlertTimer = setTimeout(dismissNavAlert, 8000);
}}

function dismissNavAlert() {{
    document.getElementById('nav-poi-alert').classList.remove('visible');
    _navLastAnnouncedPOI = null;
}}

function navToggleVoice() {{
    _navVoiceOn = !_navVoiceOn;
    document.getElementById('nav-voice-btn').textContent = _navVoiceOn ? '🔊' : '🔇';
    showToast(_navVoiceOn ? 'Voice on' : 'Voice off');
}}

function _navSpeak(text) {{
    if (!_navVoiceOn || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    var utt = new SpeechSynthesisUtterance(text);
    utt.rate = 1.0;
    utt.pitch = 1.0;
    window.speechSynthesis.speak(utt);
}}

function _navHaversineJS(lat1, lon1, lat2, lon2) {{
    var R = 3958.8;
    var dLat = (lat2-lat1)*Math.PI/180;
    var dLon = (lon2-lon1)*Math.PI/180;
    var a = Math.sin(dLat/2)*Math.sin(dLat/2) +
        Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)*Math.sin(dLon/2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}}

function _navDarkMapStyles() {{
    return [
        {{elementType:'geometry',stylers:[{{color:'#1a1a2e'}}]}},
        {{elementType:'labels.text.fill',stylers:[{{color:'#8ec3b0'}}]}},
        {{elementType:'labels.text.stroke',stylers:[{{color:'#1a3646'}}]}},
        {{featureType:'road',elementType:'geometry',stylers:[{{color:'#304a7d'}}]}},
        {{featureType:'road.highway',elementType:'geometry',stylers:[{{color:'#2c6291'}}]}},
        {{featureType:'water',elementType:'geometry',stylers:[{{color:'#0e3d54'}}]}},
        {{featureType:'poi.park',elementType:'geometry',stylers:[{{color:'#023e1f'}}]}}
    ];
}}
/* ═══ END NAVIGATION ═══ */
</script>

<!-- ── KDP 2FA Modal ─────────────────────────────────────────── -->
<div id="kdp-2fa-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:10000;align-items:center;justify-content:center;">
  <div style="background:var(--surface,rgba(20,22,35,0.97));border:1px solid rgba(255,255,255,0.12);border-radius:18px;padding:36px 40px;max-width:420px;width:90%;box-shadow:0 24px 80px rgba(0,0,0,0.6);">
    <div style="font-size:28px;margin-bottom:12px;">🔐</div>
    <div style="font-size:16px;font-weight:600;color:var(--text-1,rgba(255,255,255,0.9));margin-bottom:8px;">Amazon Verification Required</div>
    <div style="font-size:13px;color:var(--text-2,rgba(255,255,255,0.5));margin-bottom:24px;line-height:1.5;">
      Amazon is asking for a one-time verification code. Check your email or authenticator app and enter it below.
    </div>
    <input id="kdp-2fa-input" type="text" inputmode="numeric" pattern="[0-9]*" maxlength="8"
      placeholder="Enter code (e.g. 123456)"
      style="width:100%;box-sizing:border-box;background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.15);border-radius:10px;padding:12px 16px;font-size:18px;letter-spacing:0.2em;color:var(--text-1,#fff);outline:none;margin-bottom:16px;text-align:center;"
      onkeydown="if(event.key==='Enter') kdpSubmit2fa()">
    <div style="display:flex;gap:10px;">
      <button class="glass-btn" style="flex:1;padding:12px;" onclick="kdpSubmit2fa()">Submit Code</button>
      <button class="glass-btn" style="padding:12px 18px;opacity:0.6;" onclick="kdpCancel2fa()">Cancel</button>
    </div>
    <div id="kdp-2fa-msg" style="margin-top:12px;font-size:12px;color:rgba(255,255,200,0.6);min-height:16px;"></div>
  </div>
</div>

<!-- ═══ WHO ARE YOU — identity landing overlay ═══════════════════════ -->
<div id="wau-overlay" class="hidden">
  <div id="wau-box">
    <div class="wau-logo">⬡</div>
    <div class="wau-title">Welcome to JARVIS</div>
    <div class="wau-subtitle" id="wau-subtitle">Who's using this device?</div>
    <div class="wau-grid" id="wau-grid">
      <div class="wau-card" onclick="wauSelect('chris')">
        <div class="wau-card-avatar">👨</div>
        <div class="wau-card-name">Chris</div>
        <div class="wau-card-role">Director</div>
        <div class="wau-card-badge">Admin</div>
      </div>
      <div class="wau-card" onclick="wauSelect('rebekah')">
        <div class="wau-card-avatar">👩</div>
        <div class="wau-card-name">Rebekah</div>
        <div class="wau-card-role">Household</div>
      </div>
      <div class="wau-card" onclick="wauSelect('caleb')">
        <div class="wau-card-avatar">👦</div>
        <div class="wau-card-name">Caleb</div>
        <div class="wau-card-role">6th Grade</div>
      </div>
      <div class="wau-card" onclick="wauSelect('anna')">
        <div class="wau-card-avatar">👧</div>
        <div class="wau-card-name">Anna</div>
        <div class="wau-card-role">4th Grade</div>
      </div>
    </div>
    <button class="wau-guest" onclick="wauGuest()">Just browsing — don't save</button>
    <div class="wau-status" id="wau-status"></div>
  </div>
</div>

</body>
</html>"""
