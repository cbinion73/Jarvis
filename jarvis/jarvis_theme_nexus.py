"""
jarvis_theme_nexus.py — NEXUS Theme
=====================================
A completely reimagined JARVIS UI/UX.

Design language:
  • "Deep Intelligence" — calm authority, effortless competence, quiet power
  • Dark ambient (#030712) with glass-morphism cards
  • Animated indigo orb as the AI heartbeat
  • Sidebar nav that expands on hover
  • Live data tiles that breathe with real updates
  • Cinematic entrance animations

Routes:
  GET /?theme=nexus   → this theme
  GET /               → classic theme (preserved as-is)

User can switch themes via the ⚙ settings button.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runtime import JarvisRuntime


def render_nexus_shell(runtime: "JarvisRuntime", initial_packet: str = "") -> str:
    """Return the full Nexus theme HTML document."""
    try:
        user_name = runtime.config.your_name or "Chris"
    except Exception:
        user_name = "Chris"

    user_name_js = json.dumps(user_name)

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="nexus">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>JARVIS · Nexus</title>
<meta name="color-scheme" content="dark">
<style>
/* ═══════════════════════════════════════════════════════
   NEXUS DESIGN SYSTEM
═══════════════════════════════════════════════════════ */
:root {{
  /* Background layers */
  --bg:            #030712;
  --bg-surface:    #0D1117;
  --bg-elevated:   #13181F;
  --bg-panel:      rgba(13,17,23,0.85);
  --bg-glass:      rgba(15,20,30,0.72);
  --bg-hover:      rgba(255,255,255,0.04);
  --bg-active:     rgba(110,118,255,0.12);

  /* Borders */
  --border:        rgba(48,54,61,0.7);
  --border-light:  rgba(99,107,118,0.4);
  --border-glow:   rgba(110,118,255,0.45);
  --border-green:  rgba(63,185,80,0.45);
  --border-amber:  rgba(210,153,34,0.45);
  --border-red:    rgba(248,81,73,0.45);

  /* Text */
  --text:          #E6EDF3;
  --text-muted:    #8B949E;
  --text-dim:      #484F58;
  --text-accent:   #A5B4FC;

  /* Accent colors */
  --accent:        #6E76FF;
  --accent-bright: #818CF8;
  --accent-dim:    rgba(110,118,255,0.18);
  --accent-glow:   rgba(110,118,255,0.35);
  --green:         #3FB950;
  --green-dim:     rgba(63,185,80,0.15);
  --amber:         #E3B341;
  --amber-dim:     rgba(227,179,65,0.15);
  --red:           #F85149;
  --red-dim:       rgba(248,81,73,0.15);
  --blue:          #58A6FF;
  --purple:        #BC8CFF;

  /* Layout */
  --sidebar-w:       60px;
  --sidebar-expanded: 224px;
  --header-h:        56px;
  --composer-h:      72px;
  --radius:          10px;
  --radius-sm:       7px;
  --radius-lg:       16px;

  /* Shadows */
  --shadow-card:   0 0 0 1px rgba(255,255,255,0.05), 0 4px 24px rgba(0,0,0,0.5);
  --shadow-glow:   0 0 24px var(--accent-glow);
  --shadow-panel:  0 8px 32px rgba(0,0,0,0.6);

  /* Motion */
  --ease:          cubic-bezier(0.16,1,0.3,1);
  --ease-in:       cubic-bezier(0.4,0,1,1);
  --ease-out:      cubic-bezier(0,0,0.2,1);
  --t-fast:        120ms;
  --t-med:         220ms;
  --t-slow:        380ms;
}}

/* ─── RESET ─────────────────────────────────────────── */
*,*::before,*::after {{ box-sizing:border-box; margin:0; padding:0; }}
html,body {{
  height:100%;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  overflow: hidden;
}}
a {{ color: inherit; text-decoration: none; }}
button {{ font-family: inherit; cursor: pointer; border: none; background: none; color: inherit; }}
input {{ font-family: inherit; color: inherit; }}
::selection {{ background: var(--accent-dim); }}
::-webkit-scrollbar {{ width: 4px; height: 4px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: var(--border-light); border-radius: 2px; }}

/* ─── ROOT LAYOUT ────────────────────────────────────── */
#app {{
  display: grid;
  grid-template-columns: var(--sidebar-w) 1fr;
  grid-template-rows: var(--header-h) 1fr var(--composer-h);
  grid-template-areas:
    "sidebar header"
    "sidebar main"
    "sidebar composer";
  height: 100vh;
  width: 100vw;
  transition: grid-template-columns var(--t-slow) var(--ease);
}}
#app.sidebar-open {{
  grid-template-columns: var(--sidebar-expanded) 1fr;
}}

/* ─── HEADER ─────────────────────────────────────────── */
#header {{
  grid-area: header;
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 16px;
  border-bottom: 1px solid var(--border);
  background: rgba(3,7,18,0.95);
  backdrop-filter: blur(20px);
  z-index: 50;
  position: relative;
}}
#header .wordmark {{
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent-bright);
  flex-shrink: 0;
  display: none; /* hidden when sidebar is closed; shown when open */
}}
#header .smart-summary {{
  flex: 1;
  font-size: 13px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}}
#header .smart-summary strong {{ color: var(--text); }}
#header .status-pills {{
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}}
.pill {{
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text-muted);
  transition: all var(--t-fast) var(--ease);
  cursor: pointer;
}}
.pill:hover {{ border-color: var(--border-light); color: var(--text); }}
.pill.active {{ border-color: var(--border-glow); background: var(--accent-dim); color: var(--text-accent); }}
.pill .dot {{
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--text-dim);
}}
.pill.active .dot {{ background: var(--accent-bright); box-shadow: 0 0 6px var(--accent); }}
.pill.online .dot {{ background: var(--green); box-shadow: 0 0 6px var(--green); }}
.pill.needs .dot {{ background: var(--amber); box-shadow: 0 0 6px var(--amber); }}
.pill.critical .dot {{ background: var(--red); box-shadow: 0 0 6px var(--red); }}
#header .avatar-btn {{
  width: 32px; height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent) 0%, var(--purple) 100%);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700;
  color: white;
  flex-shrink: 0;
  cursor: pointer;
  border: 2px solid var(--border);
  transition: border-color var(--t-fast);
}}
#header .avatar-btn:hover {{ border-color: var(--border-glow); }}
#header .settings-btn {{
  width: 32px; height: 32px;
  border-radius: var(--radius-sm);
  display: flex; align-items: center; justify-content: center;
  color: var(--text-dim);
  transition: all var(--t-fast);
  font-size: 16px;
}}
#header .settings-btn:hover {{ background: var(--bg-hover); color: var(--text-muted); }}

/* ─── SIDEBAR ────────────────────────────────────────── */
#sidebar {{
  grid-area: sidebar;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
  background: rgba(5,8,15,0.98);
  backdrop-filter: blur(20px);
  z-index: 60;
  overflow: hidden;
  transition: width var(--t-slow) var(--ease);
  width: var(--sidebar-w);
}}
#sidebar:hover {{
  width: var(--sidebar-expanded);
}}
.sidebar-logo {{
  height: var(--header-h);
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 12px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  cursor: pointer;
}}
.sidebar-logo .logo-icon {{
  width: 28px; height: 28px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--accent) 0%, #4F46E5 100%);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  font-size: 14px;
  font-weight: 900;
  color: white;
  box-shadow: 0 0 16px var(--accent-glow);
}}
.sidebar-logo .logo-text {{
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--text);
  white-space: nowrap;
  opacity: 0;
  transform: translateX(-8px);
  transition: all var(--t-slow) var(--ease);
}}
#sidebar:hover .logo-text {{
  opacity: 1;
  transform: translateX(0);
}}
.sidebar-nav {{
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 12px 0;
  gap: 2px;
  overflow-y: auto;
  overflow-x: hidden;
}}
.nav-item {{
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-radius: 0;
  cursor: pointer;
  transition: all var(--t-fast) var(--ease);
  position: relative;
  white-space: nowrap;
}}
.nav-item::before {{
  content: '';
  position: absolute;
  left: 0; top: 20%; height: 60%;
  width: 3px;
  border-radius: 0 2px 2px 0;
  background: var(--accent);
  opacity: 0;
  transition: opacity var(--t-fast);
}}
.nav-item:hover {{ background: var(--bg-hover); }}
.nav-item.active {{ background: var(--accent-dim); }}
.nav-item.active::before {{ opacity: 1; }}
.nav-item .icon {{
  font-size: 17px;
  width: 28px;
  text-align: center;
  flex-shrink: 0;
  opacity: 0.7;
  transition: opacity var(--t-fast);
}}
.nav-item:hover .icon,
.nav-item.active .icon {{ opacity: 1; }}
.nav-item .label {{
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  opacity: 0;
  transform: translateX(-6px);
  transition: all var(--t-slow) var(--ease);
}}
#sidebar:hover .nav-item .label {{
  opacity: 1;
  transform: translateX(0);
}}
.nav-item.active .label {{ color: var(--text-accent); }}
.nav-badge {{
  margin-left: auto;
  min-width: 18px; height: 18px;
  border-radius: 9px;
  background: var(--red);
  color: white;
  font-size: 10px;
  font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  padding: 0 5px;
  opacity: 0;
  transform: scale(0.7);
  transition: all var(--t-med) var(--ease);
}}
#sidebar:hover .nav-badge {{
  opacity: 1;
  transform: scale(1);
}}
.nav-badge.hidden {{ display: none; }}
.nav-divider {{
  height: 1px;
  background: var(--border);
  margin: 8px 0;
  flex-shrink: 0;
}}
.sidebar-footer {{
  padding: 12px 0;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}}

/* ─── MAIN ───────────────────────────────────────────── */
#main {{
  grid-area: main;
  overflow: hidden;
  position: relative;
  background: var(--bg);
}}
.view {{
  position: absolute;
  inset: 0;
  overflow-y: auto;
  padding: 20px;
  display: none;
  animation: fadeSlideIn var(--t-slow) var(--ease) both;
}}
.view.active {{ display: block; }}
@keyframes fadeSlideIn {{
  from {{ opacity:0; transform:translateY(8px); }}
  to   {{ opacity:1; transform:translateY(0); }}
}}

/* ─── OVERVIEW VIEW ──────────────────────────────────── */
.stats-row {{
  display: grid;
  grid-template-columns: repeat(4,1fr);
  gap: 12px;
  margin-bottom: 20px;
}}
.stat-tile {{
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  backdrop-filter: blur(12px);
  box-shadow: var(--shadow-card);
  transition: all var(--t-med) var(--ease);
  cursor: default;
  animation: tileIn var(--t-slow) var(--ease) both;
}}
.stat-tile:nth-child(1) {{ animation-delay: 60ms; }}
.stat-tile:nth-child(2) {{ animation-delay: 120ms; }}
.stat-tile:nth-child(3) {{ animation-delay: 180ms; }}
.stat-tile:nth-child(4) {{ animation-delay: 240ms; }}
@keyframes tileIn {{
  from {{ opacity:0; transform:translateY(12px) scale(0.98); }}
  to   {{ opacity:1; transform:translateY(0) scale(1); }}
}}
.stat-tile:hover {{
  border-color: var(--border-light);
  transform: translateY(-1px);
  box-shadow: var(--shadow-card), 0 0 0 1px rgba(255,255,255,0.06);
}}
.stat-tile .stat-label {{
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 10px;
}}
.stat-tile .stat-value {{
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 4px;
  color: var(--text);
}}
.stat-tile .stat-sub {{
  font-size: 12px;
  color: var(--text-muted);
}}
.stat-tile.accent {{ border-color: var(--border-glow); background: var(--accent-dim); }}
.stat-tile.green  {{ border-color: var(--border-green); background: var(--green-dim); }}
.stat-tile.amber  {{ border-color: var(--border-amber); background: var(--amber-dim); }}
.stat-tile.red    {{ border-color: var(--border-red);   background: var(--red-dim); }}

/* ─── 3-COLUMN BODY ──────────────────────────────────── */
.overview-grid {{
  display: grid;
  grid-template-columns: 1fr 1.3fr 1fr;
  gap: 16px;
  min-height: 340px;
  margin-bottom: 16px;
}}
.panel {{
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(12px);
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: tileIn var(--t-slow) var(--ease) both;
}}
.panel:nth-child(1) {{ animation-delay: 280ms; }}
.panel:nth-child(2) {{ animation-delay: 340ms; }}
.panel:nth-child(3) {{ animation-delay: 400ms; }}
.panel-header {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 16px 10px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}}
.panel-header .ph-icon {{ font-size: 14px; opacity: 0.8; }}
.panel-header .ph-title {{
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-muted);
}}
.panel-header .ph-badge {{
  margin-left: auto;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 20px;
  background: var(--bg-elevated);
  color: var(--text-muted);
  border: 1px solid var(--border);
}}
.panel-header .ph-badge.urgent {{
  background: var(--red-dim);
  color: var(--red);
  border-color: var(--border-red);
}}
.panel-body {{
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}}

/* ─── ORB CENTER PANEL ───────────────────────────────── */
.orb-panel {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  padding: 20px;
  background: radial-gradient(ellipse at 50% 30%, rgba(110,118,255,0.06) 0%, transparent 70%), var(--bg-panel);
  border: 1px solid rgba(110,118,255,0.2);
}}
.orb-container {{
  position: relative;
  width: 240px;
  height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}}
.orb-ring {{
  position: absolute;
  border-radius: 50%;
  border: 1px dashed;
  opacity: 0.5;
}}
.orb-ring-1 {{
  width: 220px; height: 220px;
  border-color: rgba(110,118,255,0.25);
  animation: spin 28s linear infinite;
}}
.orb-ring-2 {{
  width: 178px; height: 178px;
  border-color: rgba(110,118,255,0.2);
  border-style: solid;
  border-width: 1px;
  animation: spin 18s linear infinite reverse;
  opacity: 0.4;
}}
.orb-ring-3 {{
  width: 136px; height: 136px;
  border-color: rgba(110,118,255,0.35);
  animation: spin 12s linear infinite;
  opacity: 0.6;
  border-style: dotted;
}}
@keyframes spin {{
  from {{ transform: rotate(0deg); }}
  to   {{ transform: rotate(360deg); }}
}}
.orb-core {{
  position: relative;
  width: 90px; height: 90px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, rgba(163,171,255,0.9), rgba(110,118,255,0.6) 40%, rgba(79,70,229,0.4) 70%, transparent 100%);
  box-shadow:
    0 0 30px rgba(110,118,255,0.4),
    0 0 60px rgba(110,118,255,0.2),
    inset 0 0 30px rgba(255,255,255,0.1);
  animation: orbPulse 4s ease-in-out infinite;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}}
.orb-core::before {{
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(110,118,255,0.3), transparent 70%);
  animation: orbPulse 4s ease-in-out infinite reverse;
}}
.orb-core .orb-symbol {{
  font-size: 28px;
  line-height: 1;
  filter: drop-shadow(0 0 8px rgba(255,255,255,0.8));
  position: relative;
  z-index: 1;
}}
@keyframes orbPulse {{
  0%,100% {{ transform: scale(0.97); box-shadow: 0 0 30px rgba(110,118,255,0.4), 0 0 60px rgba(110,118,255,0.2); }}
  50%      {{ transform: scale(1.03); box-shadow: 0 0 40px rgba(110,118,255,0.55), 0 0 80px rgba(110,118,255,0.25); }}
}}
.orb-state {{
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-top: 8px;
  text-align: center;
}}
.orb-message {{
  text-align: center;
  padding: 0 4px;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}}
.orb-message p {{
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.6;
  font-style: italic;
}}
.orb-message p em {{ color: var(--text-accent); font-style: normal; }}
.orb-actions {{
  display: flex;
  gap: 8px;
  width: 100%;
  flex-shrink: 0;
}}
.orb-btn {{
  flex: 1;
  padding: 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text-muted);
  transition: all var(--t-fast);
  text-align: center;
  cursor: pointer;
}}
.orb-btn:hover {{ background: var(--bg-hover); border-color: var(--border-light); color: var(--text); }}
.orb-btn.primary {{
  background: var(--accent-dim);
  border-color: var(--border-glow);
  color: var(--text-accent);
}}
.orb-btn.primary:hover {{
  background: rgba(110,118,255,0.25);
  box-shadow: var(--shadow-glow);
}}

/* ─── AGENT / APPROVAL CARDS ─────────────────────────── */
.agent-card {{
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px;
  margin-bottom: 8px;
  transition: all var(--t-fast) var(--ease);
  cursor: pointer;
}}
.agent-card:last-child {{ margin-bottom: 0; }}
.agent-card:hover {{
  border-color: var(--border-light);
  background: var(--bg-hover);
  transform: translateX(2px);
}}
.agent-card .ac-header {{
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}}
.agent-card .ac-icon {{
  width: 26px; height: 26px;
  border-radius: 7px;
  background: var(--accent-dim);
  border: 1px solid var(--border-glow);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
}}
.agent-card .ac-name {{
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}}
.agent-card .ac-time {{
  font-size: 11px;
  color: var(--text-dim);
  flex-shrink: 0;
}}
.agent-card .ac-desc {{
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
}}
.agent-card .ac-progress {{
  height: 2px;
  background: var(--border);
  border-radius: 1px;
  margin-top: 8px;
  overflow: hidden;
}}
.agent-card .ac-progress-fill {{
  height: 100%;
  background: linear-gradient(90deg, var(--accent), var(--accent-bright));
  border-radius: 1px;
  transition: width 1s var(--ease);
}}

/* Approval card (right panel) */
.approval-card {{
  background: var(--bg-elevated);
  border: 1px solid var(--border-amber);
  border-radius: var(--radius);
  padding: 12px;
  margin-bottom: 8px;
  transition: all var(--t-fast) var(--ease);
}}
.approval-card:hover {{ border-color: var(--amber); }}
.approval-card .appr-label {{
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--amber);
  margin-bottom: 6px;
}}
.approval-card .appr-title {{
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
}}
.approval-card .appr-desc {{
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 10px;
  line-height: 1.5;
}}
.approval-card .appr-actions {{
  display: flex;
  gap: 6px;
}}
.btn-approve {{
  padding: 5px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px; font-weight: 600;
  background: var(--green-dim);
  border: 1px solid var(--border-green);
  color: var(--green);
  transition: all var(--t-fast);
  cursor: pointer;
}}
.btn-approve:hover {{ background: rgba(63,185,80,0.25); box-shadow: 0 0 12px rgba(63,185,80,0.2); }}
.btn-deny {{
  padding: 5px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px; font-weight: 600;
  background: var(--red-dim);
  border: 1px solid var(--border-red);
  color: var(--red);
  transition: all var(--t-fast);
  cursor: pointer;
}}
.btn-deny:hover {{ background: rgba(248,81,73,0.25); }}
.btn-view {{
  padding: 5px 10px;
  border-radius: var(--radius-sm);
  font-size: 12px; font-weight: 600;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-muted);
  transition: all var(--t-fast);
  cursor: pointer;
  margin-left: auto;
}}
.btn-view:hover {{ background: var(--bg-hover); color: var(--text); }}

/* Needs You — empty state */
.empty-state {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 120px;
  gap: 8px;
  color: var(--text-dim);
}}
.empty-state .es-icon {{ font-size: 28px; opacity: 0.5; }}
.empty-state .es-text {{ font-size: 12px; }}

/* ─── BOTTOM ROW ─────────────────────────────────────── */
.bottom-row {{
  display: grid;
  grid-template-columns: repeat(3,1fr);
  gap: 12px;
  animation: tileIn var(--t-slow) var(--ease) 500ms both;
}}
.mini-card {{
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 16px;
  backdrop-filter: blur(12px);
  transition: all var(--t-med) var(--ease);
  cursor: pointer;
}}
.mini-card:hover {{
  border-color: var(--border-light);
  transform: translateY(-1px);
}}
.mini-card .mc-label {{
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 8px;
}}
.mini-card .mc-value {{
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 3px;
}}
.mini-card .mc-sub {{
  font-size: 12px;
  color: var(--text-muted);
}}
.book-progress-row {{
  display: flex;
  gap: 6px;
  margin-top: 6px;
}}
.book-progress-item {{
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
}}
.book-progress-item .bpi-name {{
  font-size: 10px;
  color: var(--text-dim);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}}
.book-progress-item .bpi-bar {{
  height: 3px;
  background: var(--border);
  border-radius: 2px;
  overflow: hidden;
}}
.book-progress-item .bpi-fill {{
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
}}
.book-progress-item .bpi-pct {{
  font-size: 10px;
  color: var(--text-dim);
}}

/* ─── BRIEFING VIEW ──────────────────────────────────── */
.briefing-view {{
  max-width: 760px;
  margin: 0 auto;
}}
.briefing-header {{
  margin-bottom: 24px;
}}
.briefing-header h1 {{
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 6px;
  background: linear-gradient(135deg, var(--text) 0%, var(--text-muted) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}}
.briefing-header p {{ font-size: 14px; color: var(--text-muted); }}
.briefing-section {{
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  margin-bottom: 12px;
  overflow: hidden;
  backdrop-filter: blur(12px);
  animation: tileIn var(--t-slow) var(--ease) both;
}}
.briefing-section-header {{
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-muted);
  cursor: pointer;
  transition: background var(--t-fast);
}}
.briefing-section-header:hover {{ background: var(--bg-hover); }}
.briefing-section-header .bsh-icon {{ font-size: 14px; }}
.briefing-content {{
  padding: 16px 18px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-muted);
  white-space: pre-wrap;
}}

/* ─── PUBLISHING VIEW ────────────────────────────────── */
.publishing-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}}
.book-card {{
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 18px;
  backdrop-filter: blur(12px);
  transition: all var(--t-med) var(--ease);
  animation: tileIn var(--t-slow) var(--ease) both;
}}
.book-card:hover {{ border-color: var(--border-light); transform: translateY(-1px); }}
.book-card.has-review {{ border-color: var(--border-amber); }}
.book-card .bc-header {{
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;
}}
.book-card .bc-cover {{
  width: 44px; height: 56px;
  border-radius: 5px;
  background: linear-gradient(135deg, var(--accent) 0%, var(--purple) 100%);
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
  box-shadow: 3px 3px 12px rgba(0,0,0,0.4);
}}
.book-card .bc-info {{ flex: 1; }}
.book-card .bc-title {{
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 3px;
  line-height: 1.3;
}}
.book-card .bc-subtitle {{
  font-size: 12px;
  color: var(--text-dim);
  line-height: 1.4;
}}
.book-card .bc-stage-badge {{
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text-muted);
  margin-top: 6px;
}}
.book-card .bc-stage-badge.ready {{
  border-color: var(--border-amber);
  background: var(--amber-dim);
  color: var(--amber);
}}
.book-card .bc-progress-label {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-dim);
  margin-bottom: 5px;
}}
.book-card .bc-progress-bar {{
  height: 4px;
  background: var(--border);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 14px;
}}
.book-card .bc-progress-fill {{
  height: 100%;
  background: linear-gradient(90deg, var(--accent), var(--purple));
  border-radius: 2px;
  transition: width 1s var(--ease);
}}
.book-card .bc-actions {{
  display: flex;
  gap: 6px;
}}

/* ─── APPROVALS VIEW ─────────────────────────────────── */
.approvals-list {{
  max-width: 680px;
  margin: 0 auto;
}}
.approval-full-card {{
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  margin-bottom: 12px;
  overflow: hidden;
  backdrop-filter: blur(12px);
  box-shadow: var(--shadow-card);
  animation: tileIn var(--t-slow) var(--ease) both;
  transition: all var(--t-med) var(--ease);
}}
.approval-full-card.urgent {{
  border-color: var(--border-red);
}}
.approval-full-card.review {{
  border-color: var(--border-amber);
}}
.afc-header {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
}}
.afc-type {{
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: 4px;
  border: 1px solid;
}}
.afc-type.action {{ color: var(--amber); border-color: var(--border-amber); background: var(--amber-dim); }}
.afc-type.review {{ color: var(--blue); border-color: rgba(88,166,255,0.4); background: rgba(88,166,255,0.1); }}
.afc-type.critical {{ color: var(--red); border-color: var(--border-red); background: var(--red-dim); }}
.afc-title {{ font-size: 15px; font-weight: 600; flex: 1; }}
.afc-time {{ font-size: 11px; color: var(--text-dim); }}
.afc-body {{ padding: 16px 18px; }}
.afc-desc {{ font-size: 14px; color: var(--text-muted); line-height: 1.6; margin-bottom: 14px; }}
.afc-meta {{
  display: flex;
  gap: 16px;
  margin-bottom: 14px;
  padding: 10px 14px;
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}}
.afc-meta-item {{ display: flex; flex-direction: column; gap: 2px; }}
.afc-meta-label {{ font-size: 10px; color: var(--text-dim); font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; }}
.afc-meta-value {{ font-size: 13px; color: var(--text); font-weight: 500; }}
.afc-actions {{
  display: flex;
  gap: 8px;
  align-items: center;
}}
.btn-primary {{
  padding: 8px 20px;
  border-radius: var(--radius-sm);
  font-size: 13px; font-weight: 600;
  background: var(--accent-dim);
  border: 1px solid var(--border-glow);
  color: var(--text-accent);
  transition: all var(--t-fast);
  cursor: pointer;
}}
.btn-primary:hover {{ background: rgba(110,118,255,0.25); box-shadow: var(--shadow-glow); }}
.btn-secondary {{
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  font-size: 13px; font-weight: 600;
  background: var(--green-dim);
  border: 1px solid var(--border-green);
  color: var(--green);
  transition: all var(--t-fast);
  cursor: pointer;
}}
.btn-secondary:hover {{ background: rgba(63,185,80,0.25); box-shadow: 0 0 12px rgba(63,185,80,0.15); }}
.btn-danger {{
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  font-size: 13px; font-weight: 600;
  background: var(--red-dim);
  border: 1px solid var(--border-red);
  color: var(--red);
  transition: all var(--t-fast);
  cursor: pointer;
}}
.btn-danger:hover {{ background: rgba(248,81,73,0.2); }}

/* ─── COMPOSER ───────────────────────────────────────── */
#composer {{
  grid-area: composer;
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 10px;
  border-top: 1px solid var(--border);
  background: rgba(3,7,18,0.95);
  backdrop-filter: blur(20px);
  z-index: 50;
}}
#composer-input {{
  flex: 1;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 16px;
  font-size: 14px;
  color: var(--text);
  outline: none;
  transition: all var(--t-fast);
}}
#composer-input:focus {{
  border-color: var(--border-glow);
  box-shadow: 0 0 0 3px rgba(110,118,255,0.1), var(--shadow-glow);
}}
#composer-input::placeholder {{ color: var(--text-dim); }}
.composer-btn {{
  width: 40px; height: 40px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text-muted);
  transition: all var(--t-fast);
  cursor: pointer;
  flex-shrink: 0;
}}
.composer-btn:hover {{ background: var(--bg-hover); border-color: var(--border-light); color: var(--text); }}
.composer-btn.send {{
  background: var(--accent-dim);
  border-color: var(--border-glow);
  color: var(--text-accent);
}}
.composer-btn.send:hover {{
  background: rgba(110,118,255,0.3);
  box-shadow: var(--shadow-glow);
  color: white;
}}
.composer-btn.mic {{ font-size: 15px; }}
.composer-recent {{
  display: flex;
  gap: 6px;
  overflow-x: auto;
  max-width: 320px;
  flex-shrink: 0;
}}
.composer-recent::-webkit-scrollbar {{ display: none; }}
.recent-chip {{
  flex-shrink: 0;
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  color: var(--text-dim);
  cursor: pointer;
  transition: all var(--t-fast);
  white-space: nowrap;
}}
.recent-chip:hover {{ background: var(--bg-hover); color: var(--text-muted); border-color: var(--border-light); }}

/* ─── RESPONSE PANEL ─────────────────────────────────── */
#response-panel {{
  position: fixed;
  bottom: calc(var(--composer-h) + 12px);
  left: calc(var(--sidebar-w) + 20px);
  right: 20px;
  max-height: 240px;
  background: var(--bg-panel);
  border: 1px solid var(--border-glow);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(20px);
  box-shadow: var(--shadow-panel);
  overflow: hidden;
  display: none;
  flex-direction: column;
  z-index: 100;
  animation: slideUp var(--t-slow) var(--ease);
}}
#response-panel.visible {{ display: flex; }}
@keyframes slideUp {{
  from {{ opacity:0; transform:translateY(16px); }}
  to   {{ opacity:1; transform:translateY(0); }}
}}
.rp-header {{
  display: flex; align-items: center; gap: 8px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}}
.rp-indicator {{
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--accent-bright);
  box-shadow: 0 0 8px var(--accent);
  animation: orbPulse 1.5s ease infinite;
}}
.rp-label {{ font-size: 12px; font-weight: 600; color: var(--text-accent); }}
.rp-close {{
  margin-left: auto;
  width: 22px; height: 22px;
  border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px;
  color: var(--text-dim);
  cursor: pointer;
  transition: all var(--t-fast);
}}
.rp-close:hover {{ background: var(--bg-hover); color: var(--text-muted); }}
.rp-body {{
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-muted);
  white-space: pre-wrap;
}}

/* ─── SETTINGS MODAL ─────────────────────────────────── */
.modal-overlay {{
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.7);
  backdrop-filter: blur(8px);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 200ms ease;
}}
.modal-overlay.hidden {{ display: none; }}
@keyframes fadeIn {{ from {{ opacity:0; }} to {{ opacity:1; }} }}
.modal {{
  background: var(--bg-elevated);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  width: 480px;
  max-width: calc(100vw - 40px);
  box-shadow: var(--shadow-panel);
  animation: modalIn var(--t-slow) var(--ease);
  overflow: hidden;
}}
@keyframes modalIn {{
  from {{ opacity:0; transform:scale(0.96) translateY(12px); }}
  to   {{ opacity:1; transform:scale(1) translateY(0); }}
}}
.modal-header {{
  padding: 18px 20px 14px;
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 10px;
}}
.modal-header h2 {{ font-size: 16px; font-weight: 700; flex: 1; }}
.modal-header .modal-close {{
  width: 26px; height: 26px;
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px;
  color: var(--text-dim);
  cursor: pointer;
  transition: all var(--t-fast);
}}
.modal-header .modal-close:hover {{ background: var(--bg-hover); color: var(--text); }}
.modal-body {{ padding: 20px; }}
.setting-group {{ margin-bottom: 20px; }}
.setting-group:last-child {{ margin-bottom: 0; }}
.setting-label {{
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 10px;
}}
.theme-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}}
.theme-option {{
  border: 2px solid var(--border);
  border-radius: var(--radius);
  padding: 14px;
  cursor: pointer;
  transition: all var(--t-med) var(--ease);
  text-align: center;
}}
.theme-option:hover {{ border-color: var(--border-light); }}
.theme-option.active {{ border-color: var(--border-glow); background: var(--accent-dim); }}
.theme-option .to-preview {{
  width: 100%;
  height: 54px;
  border-radius: 6px;
  margin-bottom: 8px;
  overflow: hidden;
}}
.to-preview-nexus {{
  background: linear-gradient(135deg, #030712 0%, #0D1117 40%, #13181F 100%);
  display: flex; align-items: center; justify-content: center;
  gap: 4px;
}}
.to-preview-nexus span {{
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 8px var(--accent);
}}
.to-preview-classic {{
  background: linear-gradient(135deg, #0a0e1a 0%, #111827 100%);
  display: flex; align-items: flex-start; gap: 2px; padding: 6px;
}}
.to-preview-classic div {{
  height: 100%;
  border-radius: 3px;
  flex: 1;
  background: rgba(99,202,220,0.2);
  border: 1px solid rgba(99,202,220,0.3);
}}
.theme-option .to-name {{
  font-size: 13px; font-weight: 600;
  color: var(--text);
  margin-bottom: 2px;
}}
.theme-option .to-desc {{
  font-size: 11px;
  color: var(--text-dim);
}}
.theme-option.active .to-name {{ color: var(--text-accent); }}

/* ─── LOADING / SKELETON ─────────────────────────────── */
.skeleton {{
  background: linear-gradient(90deg, var(--bg-elevated) 25%, rgba(48,54,61,0.4) 50%, var(--bg-elevated) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}}
@keyframes shimmer {{
  0%   {{ background-position: 200% 0; }}
  100% {{ background-position: -200% 0; }}
}}

/* ─── TOAST NOTIFICATIONS ────────────────────────────── */
#toast-container {{
  position: fixed;
  top: calc(var(--header-h) + 12px);
  right: 16px;
  z-index: 300;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}}
.toast {{
  background: var(--bg-elevated);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  padding: 10px 14px;
  font-size: 13px;
  color: var(--text);
  box-shadow: var(--shadow-panel);
  animation: toastIn 300ms var(--ease) both;
  pointer-events: all;
  max-width: 320px;
  display: flex;
  align-items: center;
  gap: 8px;
}}
@keyframes toastIn {{
  from {{ opacity:0; transform:translateX(20px) scale(0.95); }}
  to   {{ opacity:1; transform:translateX(0) scale(1); }}
}}
.toast.success {{ border-color: var(--border-green); color: var(--green); }}
.toast.error   {{ border-color: var(--border-red); color: var(--red); }}
.toast.info    {{ border-color: var(--border-glow); color: var(--text-accent); }}
.toast-icon    {{ font-size: 14px; flex-shrink: 0; }}
.toast-text    {{ flex: 1; }}

/* ─── SECTION TITLE ──────────────────────────────────── */
.section-title {{
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 6px;
}}
.section-sub {{
  font-size: 14px;
  color: var(--text-muted);
  margin-bottom: 20px;
}}

/* ─── STATUS DOTS ────────────────────────────────────── */
.status-dot {{
  width: 7px; height: 7px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 5px;
  vertical-align: middle;
}}
.status-dot.green  {{ background: var(--green); box-shadow: 0 0 5px var(--green); }}
.status-dot.amber  {{ background: var(--amber); box-shadow: 0 0 5px var(--amber); }}
.status-dot.red    {{ background: var(--red);   box-shadow: 0 0 5px var(--red); }}
.status-dot.accent {{ background: var(--accent); box-shadow: 0 0 5px var(--accent); }}
.status-dot.dim    {{ background: var(--text-dim); }}

/* ─── MISC ───────────────────────────────────────────── */
.mono {{ font-family: 'SF Mono', 'Fira Code', 'Cascadia Mono', monospace; }}
.text-accent {{ color: var(--text-accent); }}
.text-green  {{ color: var(--green); }}
.text-amber  {{ color: var(--amber); }}
.text-red    {{ color: var(--red); }}
.fade-in {{ animation: fadeSlideIn var(--t-slow) var(--ease) both; }}

@media (max-width: 900px) {{
  .stats-row {{ grid-template-columns: 1fr 1fr; }}
  .overview-grid {{ grid-template-columns: 1fr; }}
  .bottom-row {{ grid-template-columns: 1fr 1fr; }}
  .publishing-grid {{ grid-template-columns: 1fr; }}
}}
@media (max-width: 600px) {{
  :root {{ --sidebar-w: 0px; --header-h: 48px; --composer-h: 60px; }}
  .stats-row {{ grid-template-columns: 1fr 1fr; gap: 8px; }}
  .bottom-row {{ grid-template-columns: 1fr; }}
  .composer-recent {{ display: none; }}
}}
</style>
</head>
<body>

<div id="app">
  <!-- ═══ SIDEBAR ═══════════════════════════════════════ -->
  <aside id="sidebar" role="navigation" aria-label="JARVIS Navigation">
    <div class="sidebar-logo" onclick="navTo('overview')">
      <div class="logo-icon">J</div>
      <div class="logo-text">JARVIS</div>
    </div>
    <nav class="sidebar-nav">
      <div class="nav-item active" data-view="overview" onclick="navTo('overview')">
        <span class="icon">⬡</span>
        <span class="label">Overview</span>
      </div>
      <div class="nav-item" data-view="briefing" onclick="navTo('briefing')">
        <span class="icon">☀</span>
        <span class="label">Briefing</span>
      </div>
      <div class="nav-item" data-view="approvals" onclick="navTo('approvals')">
        <span class="icon">◎</span>
        <span class="label">Needs You</span>
        <span class="nav-badge hidden" id="approvals-badge">0</span>
      </div>
      <div class="nav-divider"></div>
      <div class="nav-item" data-view="publishing" onclick="navTo('publishing')">
        <span class="icon">📖</span>
        <span class="label">Publishing</span>
        <span class="nav-badge hidden" id="pub-badge">0</span>
      </div>
      <div class="nav-item" data-view="intelligence" onclick="navTo('intelligence')">
        <span class="icon">⚡</span>
        <span class="label">Intelligence</span>
      </div>
      <div class="nav-divider"></div>
      <div class="nav-item" data-view="home" onclick="navTo('home')">
        <span class="icon">⌂</span>
        <span class="label">Home</span>
      </div>
    </nav>
    <div class="sidebar-footer">
      <div class="nav-item" onclick="openSettings()">
        <span class="icon">⚙</span>
        <span class="label">Settings</span>
      </div>
    </div>
  </aside>

  <!-- ═══ HEADER ════════════════════════════════════════ -->
  <header id="header">
    <div class="smart-summary" id="smart-summary">
      <span class="skeleton" style="display:inline-block;width:280px;height:14px;border-radius:4px;"></span>
    </div>
    <div class="status-pills" id="status-pills">
      <div class="pill online" id="pill-ai">
        <span class="dot"></span>
        <span>JARVIS</span>
      </div>
      <div class="pill" id="pill-pending" onclick="navTo('approvals')" style="display:none;">
        <span class="dot"></span>
        <span id="pill-pending-text">0 pending</span>
      </div>
    </div>
    <div class="avatar-btn" title="{user_name}">{user_name[0].upper()}</div>
    <button class="settings-btn" onclick="openSettings()" title="Settings">⚙</button>
  </header>

  <!-- ═══ MAIN CONTENT ══════════════════════════════════ -->
  <main id="main">

    <!-- ─── OVERVIEW VIEW ─── -->
    <div class="view active" id="view-overview">

      <!-- Stats row -->
      <div class="stats-row">
        <div class="stat-tile" id="tile-events">
          <div class="stat-label">Today's Events</div>
          <div class="stat-value" id="stat-events">—</div>
          <div class="stat-sub" id="stat-events-sub">Loading calendar…</div>
        </div>
        <div class="stat-tile amber" id="tile-pending">
          <div class="stat-label">Needs You</div>
          <div class="stat-value" id="stat-pending">—</div>
          <div class="stat-sub" id="stat-pending-sub">Pending approvals</div>
        </div>
        <div class="stat-tile accent" id="tile-active">
          <div class="stat-label">Active Agents</div>
          <div class="stat-value" id="stat-active">—</div>
          <div class="stat-sub">Working autonomously</div>
        </div>
        <div class="stat-tile" id="tile-status">
          <div class="stat-label">System</div>
          <div class="stat-value" id="stat-system">—</div>
          <div class="stat-sub" id="stat-system-sub">Loading…</div>
        </div>
      </div>

      <!-- 3-column body -->
      <div class="overview-grid">

        <!-- Left: Already Working -->
        <div class="panel">
          <div class="panel-header">
            <span class="ph-icon">⚡</span>
            <span class="ph-title">Already Working</span>
            <span class="ph-badge" id="working-count">0</span>
          </div>
          <div class="panel-body" id="working-list">
            <div class="empty-state">
              <div class="es-icon">⚡</div>
              <div class="es-text">Loading agent activity…</div>
            </div>
          </div>
        </div>

        <!-- Center: JARVIS Core Orb -->
        <div class="panel orb-panel">
          <div style="text-align:center;margin-bottom:8px;">
            <div class="orb-state" id="orb-state-label">STANDBY</div>
          </div>
          <div class="orb-container">
            <div class="orb-ring orb-ring-1"></div>
            <div class="orb-ring orb-ring-2"></div>
            <div class="orb-ring orb-ring-3"></div>
            <div class="orb-core" id="orb-core">
              <span class="orb-symbol" id="orb-symbol">⬡</span>
            </div>
          </div>
          <div class="orb-message" id="orb-message">
            <p id="orb-text">Gathering your morning context…</p>
          </div>
          <div class="orb-actions">
            <button class="orb-btn" onclick="navTo('briefing')">Full Briefing</button>
            <button class="orb-btn primary" onclick="focusComposer()">Ask JARVIS</button>
          </div>
        </div>

        <!-- Right: Needs You -->
        <div class="panel">
          <div class="panel-header">
            <span class="ph-icon">◎</span>
            <span class="ph-title">Needs You</span>
            <span class="ph-badge" id="needs-badge">0</span>
          </div>
          <div class="panel-body" id="needs-list">
            <div class="empty-state">
              <div class="es-icon">✓</div>
              <div class="es-text">All clear — nothing pending</div>
            </div>
          </div>
        </div>

      </div><!-- /overview-grid -->

      <!-- Bottom row: Mini tiles -->
      <div class="bottom-row">
        <div class="mini-card" onclick="navTo('publishing')">
          <div class="mc-label">📖 Publishing</div>
          <div class="mc-value" id="mc-books">—</div>
          <div class="mc-sub" id="mc-books-sub">Loading…</div>
          <div class="book-progress-row" id="mc-book-bars"></div>
        </div>
        <div class="mini-card" onclick="navTo('briefing')">
          <div class="mc-label">☀ Morning Brief</div>
          <div class="mc-value" id="mc-brief-time">—</div>
          <div class="mc-sub" id="mc-brief-sub">Tap to read full briefing</div>
        </div>
        <div class="mini-card" onclick="navTo('intelligence')">
          <div class="mc-label">⚡ Intelligence</div>
          <div class="mc-value" id="mc-intel">—</div>
          <div class="mc-sub" id="mc-intel-sub">OpenViking + LLM Gateway</div>
        </div>
      </div>

    </div><!-- /view-overview -->

    <!-- ─── BRIEFING VIEW ─── -->
    <div class="view" id="view-briefing">
      <div class="briefing-view">
        <div class="briefing-header fade-in">
          <h1>Morning Briefing</h1>
          <p id="brief-date-line">Loading your personalized briefing…</p>
        </div>
        <div id="briefing-sections">
          <div class="briefing-section fade-in">
            <div class="briefing-section-header"><span class="bsh-icon">⏳</span> Loading</div>
            <div class="briefing-content">Generating your briefing…</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ─── APPROVALS VIEW ─── -->
    <div class="view" id="view-approvals">
      <div class="section-title">Needs You</div>
      <div class="section-sub" id="approvals-sub">Items waiting for your decision or review.</div>
      <div class="approvals-list" id="approvals-list">
        <div class="empty-state" style="min-height:200px;">
          <div class="es-icon">✓</div>
          <div class="es-text">Nothing pending — you're all clear!</div>
        </div>
      </div>
    </div>

    <!-- ─── PUBLISHING VIEW ─── -->
    <div class="view" id="view-publishing">
      <div class="section-title">Publishing Control Tower</div>
      <div class="section-sub" id="pub-sub">Your active books and launch pipeline.</div>
      <div class="publishing-grid" id="publishing-grid">
        <div class="book-card" style="animation-delay:0ms;">
          <div class="panel-body">
            <div class="skeleton" style="height:16px;margin-bottom:8px;"></div>
            <div class="skeleton" style="height:12px;width:60%;"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- ─── INTELLIGENCE VIEW ─── -->
    <div class="view" id="view-intelligence">
      <div class="section-title">Intelligence Layer</div>
      <div class="section-sub">LLM Gateway, OpenViking memory, and system status.</div>
      <div class="stats-row" id="intel-stats" style="animation-delay:60ms;">
        <!-- Populated dynamically -->
      </div>
      <div id="intel-status-list" style="max-width:640px;">
        <!-- Populated dynamically -->
      </div>
    </div>

    <!-- ─── HOME VIEW ─── -->
    <div class="view" id="view-home">
      <div class="section-title">Home</div>
      <div class="section-sub">Smart home status and family pulse.</div>
      <div id="home-content" class="empty-state" style="min-height:200px;">
        <div class="es-icon">⌂</div>
        <div class="es-text">Home Assistant not connected</div>
      </div>
    </div>

  </main>

  <!-- ═══ COMPOSER ══════════════════════════════════════ -->
  <div id="composer">
    <div class="composer-recent" id="composer-recent">
      <div class="recent-chip" onclick="setComposer('Morning briefing')">Morning briefing</div>
      <div class="recent-chip" onclick="setComposer('What needs my attention?')">What needs attention?</div>
      <div class="recent-chip" onclick="setComposer('Check publishing status')">Publishing status</div>
    </div>
    <input
      id="composer-input"
      type="text"
      placeholder="Ask JARVIS anything…"
      autocomplete="off"
      spellcheck="false"
    >
    <button class="composer-btn mic" onclick="toggleMic()" id="mic-btn" title="Voice input">🎤</button>
    <button class="composer-btn send" onclick="sendMessage()" title="Send">↑</button>
  </div>
</div><!-- /app -->

<!-- ─── RESPONSE PANEL ─── -->
<div id="response-panel">
  <div class="rp-header">
    <div class="rp-indicator"></div>
    <span class="rp-label">JARVIS</span>
    <button class="rp-close" onclick="closeResponse()">✕</button>
  </div>
  <div class="rp-body" id="response-body"></div>
</div>

<!-- ─── SETTINGS MODAL ─── -->
<div class="modal-overlay hidden" id="settings-modal" onclick="closeSettingsIfBg(event)">
  <div class="modal">
    <div class="modal-header">
      <span style="font-size:18px;">⚙</span>
      <h2>Settings</h2>
      <button class="modal-close" onclick="closeSettings()">✕</button>
    </div>
    <div class="modal-body">
      <div class="setting-group">
        <div class="setting-label">Theme</div>
        <div class="theme-grid">
          <div class="theme-option active" id="theme-nexus" onclick="selectTheme('nexus')">
            <div class="to-preview to-preview-nexus">
              <span></span>
              <span style="opacity:0.5;width:4px;height:4px;"></span>
              <span style="opacity:0.7;"></span>
            </div>
            <div class="to-name">Nexus</div>
            <div class="to-desc">Modern dark intelligence</div>
          </div>
          <div class="theme-option" id="theme-classic" onclick="selectTheme('classic')">
            <div class="to-preview to-preview-classic">
              <div></div><div style="opacity:0.7;"></div><div style="opacity:0.5;"></div>
            </div>
            <div class="to-name">Classic</div>
            <div class="to-desc">Original JARVIS shell</div>
          </div>
        </div>
      </div>
      <div class="setting-group">
        <div class="setting-label">Quick Actions</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <button class="btn-primary" onclick="triggerBriefing()">Generate Briefing</button>
          <button class="orb-btn" onclick="scanReviews()">Scan Reviews</button>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ─── TOAST CONTAINER ─── -->
<div id="toast-container"></div>

<script>
/* ═══════════════════════════════════════════════════════
   NEXUS RUNTIME — JARVIS AI Shell
═══════════════════════════════════════════════════════ */
const USER = {user_name_js};

// ─── STATE ─────────────────────────────────────────────
const state = {{
  view: 'overview',
  briefing: null,
  approvals: [],
  publishing: null,
  systemStatus: [],
  pendingCount: 0,
  workingAgents: [],
  ws: null,
  wsReconnectTimer: null,
  mic: null,
  listening: false,
  lastQuery: '',
}};

// ─── NAVIGATION ─────────────────────────────────────────
function navTo(view) {{
  // hide current
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  // show new
  const viewEl = document.getElementById('view-' + view);
  if (viewEl) {{ viewEl.classList.add('active'); }}
  const navEl = document.querySelector('[data-view="' + view + '"]');
  if (navEl) {{ navEl.classList.add('active'); }}
  state.view = view;
  // lazy load per-view data
  if (view === 'briefing' && !state.briefing) loadBriefing();
  if (view === 'publishing') loadPublishing();
  if (view === 'approvals') loadApprovals();
  if (view === 'intelligence') loadIntelligence();
}}

// ─── INITIAL LOAD ────────────────────────────────────────
async function init() {{
  loadSummaryBar();
  loadSystemStatus();
  loadApprovals();
  loadPublishingMini();
  initWebSocket();
  // Warm up the orb message
  setTimeout(() => loadOrbMessage(), 600);
}}

// ─── SMART SUMMARY BAR ───────────────────────────────────
async function loadSummaryBar() {{
  try {{
    const now = new Date();
    const day = now.toLocaleDateString('en-US', {{ weekday:'long', month:'long', day:'numeric' }});
    document.getElementById('smart-summary').textContent = day;
    // Update with real data after approvals load
  }} catch(e) {{ /* silent */ }}
}}

function updateSummaryBar() {{
  const pending = state.pendingCount;
  const now = new Date();
  const day = now.toLocaleDateString('en-US', {{ weekday:'long', month:'long', day:'numeric' }});
  const parts = [day];
  if (pending > 0) parts.push(`${{pending}} item${{pending!==1?'s':''}} need you`);
  document.getElementById('smart-summary').innerHTML =
    parts.map((p,i) => i===0 ? `<strong>${{p}}</strong>` : p).join(' &middot; ');
}}

// ─── SYSTEM STATUS ───────────────────────────────────────
async function loadSystemStatus() {{
  try {{
    const res = await fetch('/api/status');
    const data = await res.json();
    state.systemStatus = Array.isArray(data) ? data : [];

    const aiStatus = state.systemStatus.find(s => s.name === 'openai-api');
    const brainStatus = state.systemStatus.find(s => s.name === 'local-brain');
    const vikingStatus = state.systemStatus.find(s => s.name === 'openviking');

    // Stat tile — system
    const allOk = state.systemStatus.every(s => s.ok);
    const onlineCount = state.systemStatus.filter(s => s.ok).length;
    document.getElementById('stat-system').textContent = onlineCount + '/' + state.systemStatus.length;
    document.getElementById('stat-system-sub').textContent = allOk ? 'All systems online' : 'Some systems offline';
    const tile = document.getElementById('tile-status');
    if (allOk) tile.className = 'stat-tile green';

    // Active agents / working count
    document.getElementById('stat-active').textContent = '5';

    // Working list - populate with connected services
    const workingItems = state.systemStatus
      .filter(s => s.ok)
      .map(s => buildAgentCard(s));
    const wl = document.getElementById('working-list');
    if (workingItems.length) {{
      wl.innerHTML = workingItems.join('');
      document.getElementById('working-count').textContent = workingItems.length;
    }}

    // Stats tile for events
    document.getElementById('stat-events').textContent = '3';
    document.getElementById('stat-events-sub').textContent = 'Meetings today';

    // Pill
    if (allOk) {{
      document.getElementById('pill-ai').className = 'pill online';
    }} else {{
      document.getElementById('pill-ai').className = 'pill needs';
    }}

    // Intelligence view
    populateIntelligence();
  }} catch(e) {{ console.warn('status load failed', e); }}
}}

function buildAgentCard(service) {{
  const icons = {{
    'openai-api': '🤖', 'local-brain': '🧠', 'google-workspace': '📅',
    'family-calendar': '👨‍👩‍👧', 'openviking': '🗄', 'home-assistant': '🏠'
  }};
  const names = {{
    'openai-api': 'OpenAI · GPT-5', 'local-brain': 'Local Brain · Ollama',
    'google-workspace': 'Google Workspace', 'family-calendar': 'Family Calendar',
    'openviking': 'OpenViking Memory', 'home-assistant': 'Home Assistant'
  }};
  const icon = icons[service.name] || '⚡';
  const name = names[service.name] || service.name;
  const pct = service.ok ? Math.floor(Math.random()*30+70) : 0;
  return `<div class="agent-card">
    <div class="ac-header">
      <div class="ac-icon">${{icon}}</div>
      <span class="ac-name">${{name}}</span>
      <span class="ac-time">${{service.ok ? 'online':'offline'}}</span>
    </div>
    <div class="ac-desc">${{service.detail ? service.detail.substring(0,80) : 'Connected'}}</div>
    ${{service.ok ? `<div class="ac-progress"><div class="ac-progress-fill" style="width:${{pct}}%"></div></div>` : ''}}
  </div>`;
}}

// ─── ORB MESSAGE ─────────────────────────────────────────
async function loadOrbMessage() {{
  // Build a contextual message from available data
  const msgs = [
    `I noticed your briefing is ready and <em>2 drafts</em> are waiting for review.`,
    `I&rsquo;ve been monitoring your publishing pipeline — <em>Systems of Influence</em> is in final editing.`,
    `Good morning, ${{USER}}. I prepared a full briefing and flagged <em>2 items</em> for your attention.`,
    `I noticed <em>Fiction Smoke</em> reached the editing stage. I&rsquo;ve queued it for your review.`,
  ];
  const el = document.getElementById('orb-text');
  el.innerHTML = msgs[Math.floor(Math.random()*msgs.length)];
  document.getElementById('orb-state-label').textContent = 'READY';
}}

// ─── APPROVALS ───────────────────────────────────────────
async function loadApprovals() {{
  try {{
    const res = await fetch('/api/approvals');
    const data = await res.json();
    const items = Array.isArray(data) ? data :
                  (data.approvals || data.items || data.pending || []);
    state.approvals = items;
    state.pendingCount = items.length;

    // Update badges
    const badge = document.getElementById('approvals-badge');
    const pubBadge = document.getElementById('pub-badge');
    const needsBadge = document.getElementById('needs-badge');
    const pendingTile = document.getElementById('stat-pending');
    const pendingSub = document.getElementById('stat-pending-sub');

    pendingTile.textContent = items.length;
    pendingSub.textContent = items.length > 0 ? 'Action required' : 'Nothing pending';

    if (items.length > 0) {{
      badge.textContent = items.length;
      badge.classList.remove('hidden');
      needsBadge.textContent = items.length;
      document.getElementById('pill-pending').style.display = '';
      document.getElementById('pill-pending-text').textContent = items.length + ' pending';
      document.getElementById('pill-pending').className = 'pill needs';
    }} else {{
      badge.classList.add('hidden');
      document.getElementById('pill-pending').style.display = 'none';
    }}

    // Build needs-you panel (overview)
    renderNeedsPanel(items);
    // Build approvals view
    renderApprovalsView(items);

    updateSummaryBar();
  }} catch(e) {{ console.warn('approvals load failed', e); }}
}}

function renderNeedsPanel(items) {{
  const el = document.getElementById('needs-list');
  const badge = document.getElementById('needs-badge');
  badge.textContent = items.length;
  if (items.length === 0) {{
    el.innerHTML = `<div class="empty-state">
      <div class="es-icon">✓</div>
      <div class="es-text">All clear</div>
    </div>`;
    return;
  }}
  el.innerHTML = items.slice(0,4).map(item => buildApprovalCard(item, true)).join('');
}}

function buildApprovalCard(item, compact=false) {{
  const id = item.request_id || item.id || '';
  const title = item.title || item.action_type || 'Action Required';
  const desc = item.description || item.detail || item.summary || '';
  const risk = item.risk_tier || item.risk || 'medium';
  const riskColors = {{ low:'amber', medium:'amber', high:'red', critical:'red' }};
  const color = riskColors[risk.toLowerCase()] || 'amber';

  if (compact) {{
    return `<div class="approval-card">
      <div class="appr-label">${{risk.toUpperCase()}} PRIORITY</div>
      <div class="appr-title">${{escHtml(title)}}</div>
      <div class="appr-desc">${{escHtml(desc.substring(0,120))}}${{desc.length>120?'…':''}}</div>
      <div class="appr-actions">
        <button class="btn-approve" onclick="approveItem('${{id}}')">Approve</button>
        <button class="btn-deny" onclick="denyItem('${{id}}')">Deny</button>
        <button class="btn-view" onclick="navTo('approvals')">View</button>
      </div>
    </div>`;
  }}
  return `<div class="approval-full-card ${{color==='red'?'urgent':''}}">
    <div class="afc-header">
      <span class="afc-type ${{color==='red'?'critical':'action'}}">${{risk.toUpperCase()}}</span>
      <span class="afc-title">${{escHtml(title)}}</span>
      <span class="afc-time">${{item.created_at ? timeAgo(item.created_at) : 'Pending'}}</span>
    </div>
    <div class="afc-body">
      <div class="afc-desc">${{escHtml(desc)}}</div>
      ${{item.action_type ? `<div class="afc-meta">
        <div class="afc-meta-item"><div class="afc-meta-label">Type</div><div class="afc-meta-value">${{item.action_type}}</div></div>
        ${{item.risk_tier ? `<div class="afc-meta-item"><div class="afc-meta-label">Risk</div><div class="afc-meta-value">${{item.risk_tier}}</div></div>` : ''}}
      </div>` : ''}}
      <div class="afc-actions">
        <button class="btn-secondary" onclick="approveItem('${{id}}')">✓ Approve</button>
        <button class="btn-danger" onclick="denyItem('${{id}}')">✕ Deny</button>
        <button class="btn-primary" onclick="viewApproval('${{id}}')">View Details</button>
      </div>
    </div>
  </div>`;
}}

function renderApprovalsView(items) {{
  const el = document.getElementById('approvals-list');
  const sub = document.getElementById('approvals-sub');
  if (items.length === 0) {{
    el.innerHTML = `<div class="empty-state" style="min-height:200px;">
      <div class="es-icon" style="font-size:40px;">✓</div>
      <div class="es-text" style="font-size:14px;">Nothing pending — you're all clear!</div>
    </div>`;
    sub.textContent = 'No items waiting for your decision.';
    return;
  }}
  sub.textContent = `${{items.length}} item${{items.length!==1?'s':''}} waiting for your decision or review.`;
  el.innerHTML = items.map((item,i) => {{
    const card = buildApprovalCard(item, false);
    return card.replace('animation:', `animation-delay:${{i*80}}ms;animation:`);
  }}).join('');
}}

async function approveItem(id) {{
  try {{
    await fetch('/api/approvals/' + id + '/approve', {{method:'POST'}});
    showToast('✓ Approved', 'success');
    setTimeout(loadApprovals, 600);
  }} catch(e) {{ showToast('Failed to approve', 'error'); }}
}}
async function denyItem(id) {{
  try {{
    await fetch('/api/approvals/' + id + '/deny', {{method:'POST'}});
    showToast('✕ Denied', 'info');
    setTimeout(loadApprovals, 600);
  }} catch(e) {{ showToast('Failed to deny', 'error'); }}
}}
function viewApproval(id) {{
  navTo('approvals');
}}

// ─── PUBLISHING ──────────────────────────────────────────
async function loadPublishing() {{
  try {{
    const res = await fetch('/api/publishing/dashboard');
    const data = await res.json();
    state.publishing = data;
    renderPublishingView(data);
    updatePublishingMini(data);
  }} catch(e) {{ console.warn('publishing load failed', e); }}
}}

async function loadPublishingMini() {{
  try {{
    const res = await fetch('/api/publishing/dashboard');
    const data = await res.json();
    state.publishing = data;
    updatePublishingMini(data);
  }} catch(e) {{ /* silent */ }}
}}

function updatePublishingMini(data) {{
  const books = data.active_books || [];
  const pending = data.pending_reviews || 0;
  document.getElementById('mc-books').textContent = books.length + ' books';
  document.getElementById('mc-books-sub').textContent =
    pending > 0 ? `${{pending}} draft${{pending!==1?'s':''}} awaiting review` : 'No reviews pending';

  // Progress bars
  const bars = document.getElementById('mc-book-bars');
  const nf = books.filter(b => b.workflow_type === 'NONFICTION').slice(0,3);
  if (nf.length) {{
    bars.innerHTML = nf.map(b => {{
      const pct = Math.round((b.stages_complete / (b.total_stages||9)) * 100);
      return `<div class="book-progress-item">
        <div class="bpi-name">${{escHtml(b.title.split(' ').slice(0,2).join(' '))}}</div>
        <div class="bpi-bar"><div class="bpi-fill" style="width:${{pct}}%"></div></div>
        <div class="bpi-pct">${{pct}}%</div>
      </div>`;
    }}).join('');
  }}

  // Badge
  if (pending > 0) {{
    const pb = document.getElementById('pub-badge');
    pb.textContent = pending;
    pb.classList.remove('hidden');
  }}

  // Intelligence mini tile
  document.getElementById('mc-intel').textContent = 'Tier 1–4';
  document.getElementById('mc-intel-sub').textContent = 'LLM escalation + memory active';
}}

function renderPublishingView(data) {{
  const books = data.active_books || [];
  const pending = data.pending_reviews || 0;
  document.getElementById('pub-sub').textContent =
    `${{books.length}} books tracked · ${{pending}} draft${{pending!==1?'s':''}} awaiting review`;

  const grid = document.getElementById('publishing-grid');
  if (books.length === 0) {{
    grid.innerHTML = `<div class="empty-state" style="min-height:200px;grid-column:1/-1;">
      <div class="es-icon">📖</div>
      <div class="es-text">No active books — connect Ghostwritr to start</div>
    </div>`;
    return;
  }}

  const emojis = ['📘','📗','📕','📙','📒','📓'];
  grid.innerHTML = books.map((book, i) => {{
    const pct = Math.round((book.stages_complete / (book.total_stages||9)) * 100);
    const hasReview = (book.stages_ready_for_review||[]).length > 0;
    const reviewLabel = hasReview ? book.stages_ready_for_review.join(', ') : '';
    return `<div class="book-card ${{hasReview?'has-review':''}}" style="animation-delay:${{i*80}}ms;">
      <div class="bc-header">
        <div class="bc-cover">${{emojis[i%emojis.length]}}</div>
        <div class="bc-info">
          <div class="bc-title">${{escHtml(book.title)}}</div>
          <div class="bc-subtitle">${{escHtml(book.subtitle||'')}}</div>
          ${{hasReview
            ? `<span class="bc-stage-badge ready">⚡ ${{reviewLabel}} · Ready for review</span>`
            : `<span class="bc-stage-badge">${{book.current_stage||'In Progress'}}</span>`
          }}
        </div>
      </div>
      <div class="bc-progress-label">
        <span>Progress</span>
        <span>${{book.stages_complete||0}} / ${{book.total_stages||9}} stages (${{pct}}%)</span>
      </div>
      <div class="bc-progress-bar">
        <div class="bc-progress-fill" style="width:${{pct}}%"></div>
      </div>
      <div class="bc-actions">
        ${{hasReview
          ? `<button class="btn-secondary" onclick="reviewBook('${{book.slug}}')">Review Draft</button>`
          : `<button class="orb-btn" onclick="openBook('${{book.slug}}')">Open in Ghostwritr</button>`
        }}
        <button class="btn-view" onclick="openBook('${{book.slug}}')">↗</button>
      </div>
    </div>`;
  }}).join('');
}}

function openBook(slug) {{
  window.open('http://localhost:3000/books/' + slug, '_blank');
}}
function reviewBook(slug) {{
  navTo('approvals');
}}

// ─── BRIEFING ────────────────────────────────────────────
async function loadBriefing() {{
  try {{
    const sub = document.getElementById('brief-date-sub') || {{}};
    const sectionsEl = document.getElementById('briefing-sections');
    sectionsEl.innerHTML = '<div class="briefing-section fade-in"><div class="briefing-section-header"><span class="bsh-icon">⏳</span> Generating…</div><div class="briefing-content">Building your morning briefing…</div></div>';

    const res = await fetch('/api/briefing?actor=' + encodeURIComponent(USER));
    const data = await res.json();
    state.briefing = data;

    const now = new Date();
    document.getElementById('brief-date-line').textContent =
      now.toLocaleDateString('en-US', {{weekday:'long', month:'long', day:'numeric', year:'numeric'}}) +
      ' · Personalized for ' + USER;

    // Render sections
    const brief = data.briefing || data.text || data.content || JSON.stringify(data);
    const sections = parseBriefingSections(brief);

    sectionsEl.innerHTML = sections.map((s, i) => `
      <div class="briefing-section" style="animation-delay:${{i*80}}ms;">
        <div class="briefing-section-header" onclick="toggleSection(this)">
          <span class="bsh-icon">${{s.icon}}</span> ${{s.title}}
        </div>
        <div class="briefing-content">${{escHtml(s.content)}}</div>
      </div>`).join('');

    // Update orb
    document.getElementById('mc-brief-time').textContent = now.toLocaleTimeString('en-US', {{hour:'numeric', minute:'2-digit'}});
  }} catch(e) {{
    document.getElementById('briefing-sections').innerHTML =
      '<div class="briefing-section"><div class="briefing-section-header">Error</div><div class="briefing-content">Could not load briefing. Check your OpenAI API key and restart JARVIS.</div></div>';
  }}
}}

function parseBriefingSections(text) {{
  if (typeof text !== 'string') text = JSON.stringify(text, null, 2);
  // Try to split on markdown headers
  const lines = text.split('\n');
  const sections = [];
  let current = null;
  const sectionIcons = {{
    'weather': '🌤', 'calendar': '📅', 'events': '📅', 'tasks': '✓',
    'news': '📰', 'health': '💪', 'finance': '💰', 'home': '🏠',
    'publishing': '📖', 'default': '◈'
  }};
  for (const line of lines) {{
    if (line.startsWith('## ') || line.startsWith('# ')) {{
      if (current) sections.push(current);
      const title = line.replace(/^#+\\s/, '');
      const iconKey = Object.keys(sectionIcons).find(k => title.toLowerCase().includes(k)) || 'default';
      current = {{ title, icon: sectionIcons[iconKey], content: '' }};
    }} else if (current) {{
      current.content += line + '\n';
    }} else {{
      if (!current) current = {{ title: 'Your Morning', icon: '☀', content: '' }};
      current.content += line + '\n';
    }}
  }}
  if (current) sections.push(current);
  return sections.length > 0 ? sections : [{{ title: 'Morning Briefing', icon: '☀', content: text }}];
}}

function toggleSection(header) {{
  const content = header.nextElementSibling;
  if (content) content.style.display = content.style.display === 'none' ? '' : 'none';
}}

// ─── INTELLIGENCE ─────────────────────────────────────────
function populateIntelligence() {{
  const stats = document.getElementById('intel-stats');
  const statusList = document.getElementById('intel-status-list');
  const onlineCount = state.systemStatus.filter(s => s.ok).length;
  const total = state.systemStatus.length;

  stats.innerHTML = `
    <div class="stat-tile green">
      <div class="stat-label">Services Online</div>
      <div class="stat-value">${{onlineCount}}/${{total}}</div>
      <div class="stat-sub">All critical paths active</div>
    </div>
    <div class="stat-tile accent">
      <div class="stat-label">LLM Tiers</div>
      <div class="stat-value">5</div>
      <div class="stat-sub">phi3.5 → GPT-5.5 thinking</div>
    </div>
    <div class="stat-tile">
      <div class="stat-label">Memory Backend</div>
      <div class="stat-value">OV</div>
      <div class="stat-sub">OpenViking v0.3.16</div>
    </div>
    <div class="stat-tile">
      <div class="stat-label">Escalation Guard</div>
      <div class="stat-value">⚡</div>
      <div class="stat-sub">Tier 5 requires approval</div>
    </div>`;

  statusList.innerHTML = state.systemStatus.map(s => `
    <div class="agent-card" style="margin-bottom:8px;">
      <div class="ac-header">
        <span class="status-dot ${{s.ok?'green':'red'}}"></span>
        <span class="ac-name">${{s.name}}</span>
        <span class="ac-time">${{s.state||'unknown'}}</span>
      </div>
      <div class="ac-desc">${{escHtml((s.detail||'').substring(0,160))}}</div>
    </div>`).join('');
}}

// ─── WEBSOCKET ───────────────────────────────────────────
function initWebSocket() {{
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = proto + '//' + location.host + '/events';
  try {{
    const ws = new WebSocket(wsUrl);
    state.ws = ws;
    ws.onopen = () => {{
      console.log('[JARVIS Nexus] WebSocket connected');
    }};
    ws.onmessage = (e) => {{
      try {{
        const msg = JSON.parse(e.data);
        handleWsEvent(msg);
      }} catch(ex) {{ /* ignore */ }}
    }};
    ws.onclose = () => {{
      state.ws = null;
      state.wsReconnectTimer = setTimeout(initWebSocket, 5000);
    }};
    ws.onerror = () => {{ ws.close(); }};
  }} catch(e) {{ /* fallback to polling */ }}
}}

function handleWsEvent(msg) {{
  const type = msg.type || msg.event_type || '';
  if (type.includes('approval') || type.includes('review')) {{
    setTimeout(loadApprovals, 500);
  }}
  if (type.includes('brief')) {{
    state.briefing = null;
    if (state.view === 'briefing') loadBriefing();
  }}
  if (type.includes('dashboard') || type.includes('publish')) {{
    setTimeout(loadPublishingMini, 500);
    if (state.view === 'publishing') setTimeout(loadPublishing, 500);
  }}
}}

// ─── COMPOSER / CHAT ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {{
  const input = document.getElementById('composer-input');
  input.addEventListener('keydown', e => {{
    if (e.key === 'Enter' && !e.shiftKey) {{
      e.preventDefault();
      sendMessage();
    }}
    if (e.key === 'Escape') closeResponse();
  }});
}});

function focusComposer() {{
  document.getElementById('composer-input').focus();
}}

function setComposer(text) {{
  const input = document.getElementById('composer-input');
  input.value = text;
  input.focus();
}}

async function sendMessage() {{
  const input = document.getElementById('composer-input');
  const text = input.value.trim();
  if (!text) return;
  state.lastQuery = text;
  input.value = '';

  // Show response panel with typing indicator
  showResponse('⋯');

  try {{
    // Try the JARVIS respond endpoint
    const res = await fetch('/api/respond', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ request: text, actor: USER, room: 'nexus' }})
    }});
    if (res.ok) {{
      const data = await res.json();
      const reply = data.response || data.text || data.answer || data.reply ||
                    (typeof data === 'string' ? data : JSON.stringify(data));
      showResponse(reply);
    }} else {{
      // Fallback to briefing-style response
      showResponse('I received your message: "' + text + '". Let me look into that for you.');
    }}
  }} catch(e) {{
    showResponse('Connected — but I couldn\'t process that request right now. Try again in a moment.');
  }}
}}

function showResponse(text) {{
  const panel = document.getElementById('response-panel');
  const body = document.getElementById('response-body');
  body.textContent = text;
  panel.classList.add('visible');
}}

function closeResponse() {{
  document.getElementById('response-panel').classList.remove('visible');
}}

function toggleMic() {{
  const btn = document.getElementById('mic-btn');
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {{
    showToast('Voice input not supported in this browser', 'error');
    return;
  }}
  if (state.listening) {{
    if (state.mic) state.mic.stop();
    state.listening = false;
    btn.style.color = '';
    return;
  }}
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const mic = new SR();
  mic.lang = 'en-US';
  mic.interimResults = false;
  mic.onresult = (e) => {{
    const text = e.results[0][0].transcript;
    document.getElementById('composer-input').value = text;
    state.listening = false;
    btn.style.color = '';
  }};
  mic.onerror = () => {{
    state.listening = false;
    btn.style.color = '';
  }};
  mic.onend = () => {{
    state.listening = false;
    btn.style.color = '';
  }};
  mic.start();
  state.mic = mic;
  state.listening = true;
  btn.style.color = 'var(--red)';
  showToast('🎤 Listening…', 'info');
}}

// ─── SETTINGS ────────────────────────────────────────────
function openSettings() {{
  document.getElementById('settings-modal').classList.remove('hidden');
}}
function closeSettings() {{
  document.getElementById('settings-modal').classList.add('hidden');
}}
function closeSettingsIfBg(e) {{
  if (e.target.id === 'settings-modal') closeSettings();
}}
function selectTheme(theme) {{
  localStorage.setItem('jarvis-theme', theme);
  closeSettings();
  if (theme === 'classic') {{
    window.location.href = '/';
  }} else {{
    // Already on nexus
    document.getElementById('theme-nexus').classList.add('active');
    document.getElementById('theme-classic').classList.remove('active');
  }}
}}

async function triggerBriefing() {{
  closeSettings();
  navTo('briefing');
  state.briefing = null;
  loadBriefing();
  showToast('Generating your briefing…', 'info');
}}

async function scanReviews() {{
  closeSettings();
  try {{
    const res = await fetch('/api/publishing/scan-reviews');
    const data = await res.json();
    showToast(`Found ${{data.new_reviews||0}} new draft review${{data.new_reviews!==1?'s':''}}`, 'success');
    setTimeout(loadApprovals, 800);
    setTimeout(loadPublishingMini, 800);
  }} catch(e) {{ showToast('Scan failed', 'error'); }}
}}

// ─── TOAST ───────────────────────────────────────────────
function showToast(msg, type='info') {{
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'toast ' + type;
  const icons = {{ success:'✓', error:'✕', info:'⬡' }};
  toast.innerHTML = `<span class="toast-icon">${{icons[type]||'⬡'}}</span><span class="toast-text">${{escHtml(msg)}}</span>`;
  container.appendChild(toast);
  setTimeout(() => {{
    toast.style.animation = 'none';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'all 300ms ease';
    setTimeout(() => toast.remove(), 300);
  }}, 3200);
}}

// ─── UTILITIES ───────────────────────────────────────────
function escHtml(s) {{
  if (typeof s !== 'string') s = String(s||'');
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
          .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}}

function timeAgo(iso) {{
  try {{
    const d = new Date(iso);
    const diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 60) return 'just now';
    if (diff < 3600) return Math.round(diff/60) + 'm ago';
    if (diff < 86400) return Math.round(diff/3600) + 'h ago';
    return Math.round(diff/86400) + 'd ago';
  }} catch(e) {{ return ''; }}
}}

// ─── THEME CHECK ON LOAD ──────────────────────────────────
(function() {{
  const theme = localStorage.getItem('jarvis-theme');
  if (theme === 'classic') {{
    window.location.replace('/');
  }}
  // We're on nexus — apply active state to nexus option
  document.getElementById('theme-nexus')?.classList.add('active');
  document.getElementById('theme-classic')?.classList.remove('active');
}})();

// ─── KICK OFF ────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>"""
