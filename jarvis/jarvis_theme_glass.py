"""JARVIS · Glass Theme — Surgical Glass · Marvel Aesthetic · Adaptive Chromatic"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runtime import JarvisRuntime


def render_glass_shell(runtime, initial_packet: str = "", *, inline_assets: bool = True) -> str:
    """Return the complete Glass theme HTML document string.

    inline_assets=True (default) embeds the full CSS/JS inline — the
    historical single-document behavior tests and programmatic consumers
    rely on. HTTP routes pass inline_assets=False to reference the CSS/JS
    as content-hashed, immutably-cached /glass-assets/ URLs instead,
    cutting every page load from ~2.2 MB to just the page's own HTML.
    Both modes compose from the same source of truth in glass_assets.py.
    """
    import json as _json
    import re as _re

    def _strip_ordered_html_titles(html: str) -> str:
        patterns = (
            r'(<h[1-6]\b[^>]*>\s*)\d+\.\s*',
            r'(<strong\b[^>]*>\s*)\d+\.\s*',
            r'(<div\b[^>]*class="[^"]*(?:card-number|card-title|panel-title|topbar-title|nav-title)[^"]*"[^>]*>\s*)\d+\.\s*',
            r'(<[^>]+\bid="[^"]*page-label[^"]*"[^>]*>\s*)\d+\.\s*',
        )
        for pattern in patterns:
            html = _re.sub(pattern, r"\1", html)
        return html

    try:
        user_name = runtime.config.your_name or "Chris"
    except Exception:
        user_name = "Chris"

    home_people_seed: list[dict[str, str]] = []
    home_location_label = "Kentucky Home"
    home_quiet_start = "21:30"
    home_quiet_end = "06:00"
    try:
        household = getattr(runtime, "household", None)
        if household is not None:
            home_location_label = getattr(household, "location_label", home_location_label) or home_location_label
            home_quiet_start = getattr(household, "quiet_start", home_quiet_start) or home_quiet_start
            home_quiet_end = getattr(household, "quiet_end", home_quiet_end) or home_quiet_end
            users = getattr(household, "users", {}) or {}
            role_space = {
                "director": "Office",
                "household-coordinator": "Kitchen",
                "student": "Study",
                }
            for user in list(users.values())[:5]:
                role = str(getattr(user, "role", "") or "").strip().lower()
                home_people_seed.append(
                    {
                        "name": str(getattr(user, "display_name", "Household Member") or "Household Member"),
                        "status": "Home",
                        "detail": role_space.get(role, "Home Base"),
                        "timing": "Now",
                    }
                )
    except Exception:
        pass

    _packet = _json.dumps(initial_packet)
    _user_name_js = _json.dumps(user_name)
    _home_people_seed_js = _json.dumps(home_people_seed)
    _home_location_label_js = _json.dumps(home_location_label)
    _home_quiet_start_js = _json.dumps(home_quiet_start)
    _home_quiet_end_js = _json.dumps(home_quiet_end)

    from .glass_assets import GLASS_CSS_HASH as _css_hash, GLASS_JS_HASH as _js_hash

    html = f"""<!DOCTYPE html>
<html lang="en" data-domain="overview">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>JARVIS · Glass</title>
  <link rel="icon" href="data:,">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/glass-assets/glass-{_css_hash}.css">
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

  <div class="nav-scroll">
    <div class="nav-tabs" id="nav-tabs">
      <div class="nav-tab-group">
        <div class="nav-tab-eyebrow">Command</div>
        <button class="nav-tab" data-view="overview" onclick="switchView('overview')">
          <svg viewBox="0 0 16 16" fill="currentColor"><rect x="1" y="1" width="6" height="6" rx="1"/><rect x="9" y="1" width="6" height="6" rx="1"/><rect x="1" y="9" width="6" height="6" rx="1"/><rect x="9" y="9" width="6" height="6" rx="1"/></svg>
          Daily Brief
        </button>
        <button class="nav-tab" data-view="chat" onclick="switchView('chat')">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 2h12v9H9l-3 3v-3H2z"/></svg>
          Command
        </button>
        <button class="nav-tab" data-view="notifications" onclick="switchView('notifications')">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 2a3 3 0 0 1 3 3v1.5c0 .8.3 1.5.8 2.1l.9 1V11H3.3V9.6l.9-1A3.2 3.2 0 0 0 5 6.5V5a3 3 0 0 1 3-3z"/><path d="M6.5 13a1.5 1.5 0 0 0 3 0"/></svg>
          Needs You
        </button>
      </div>

      <div class="nav-tab-group">
        <div class="nav-tab-eyebrow">Core</div>
        <button class="nav-tab" data-view="chronicle" onclick="switchView('chronicle')">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="12" height="12" rx="1"/><path d="M5 6h6M5 9h4"/></svg>
          Legacy
        </button>
        <button class="nav-tab" data-view="faith" onclick="switchView('faith')">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 2v12M2 8h12" stroke-linecap="round"/></svg>
          Faith
        </button>
        <button class="nav-tab" data-view="agents" onclick="switchView('agents')">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="6" cy="5" r="2.5"/><circle cx="11" cy="5" r="2"/><path d="M1 14c0-3 2-4.5 5-4.5s5 1.5 5 4.5"/><path d="M12 9.5c2 .5 3 1.5 3 3.5"/></svg>
          Agents
        </button>
        <button class="nav-tab" data-view="intelligence" onclick="switchView('intelligence')">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 2a5 5 0 100 12A5 5 0 008 2z"/><path d="M8 6v2l1.5 1.5"/></svg>
          Intel
        </button>
      </div>

      <div class="nav-tab-group">
        <div class="nav-tab-eyebrow">Build</div>
        <button class="nav-tab" data-view="forge" onclick="switchView('forge')">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 2v12M4 6l4-4 4 4M3 14h10"/></svg>
          Forge
        </button>
        <button class="nav-tab" data-view="catalyst" onclick="switchView('catalyst')">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 1L7 9h5L7 15"/></svg>
          Catalyst
        </button>
        <button class="nav-tab" data-view="foundry" onclick="switchView('foundry')">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 13h10M5 13V8l3-5 3 5v5"/><path d="M6.5 8h3"/></svg>
          Foundry
        </button>
        <button class="nav-tab" data-view="workshop" onclick="switchView('workshop')">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="9" width="12" height="5" rx="1"/><path d="M5 9V6a3 3 0 016 0v3"/><circle cx="8" cy="4" r="1.5"/></svg>
          Workshop
        </button>
        <button class="nav-tab" data-view="publishing" onclick="switchView('publishing')">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 1h8v14H4zM7 1v14"/></svg>
          Publishing
        </button>
        <button class="nav-tab" data-view="huddle" onclick="switchView('huddle')">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="4" cy="6" r="2"/><circle cx="12" cy="6" r="2"/><circle cx="8" cy="4" r="2"/><path d="M1 14c0-2 1.5-3 3-3h2m4 0h2c1.5 0 3 1 3 3"/><path d="M6 11c0-1.5 1-2.5 2-2.5s2 1 2 2.5"/></svg>
          Huddle
        </button>
      </div>

      <div class="nav-tab-group">
        <div class="nav-tab-eyebrow">Life</div>
        <button class="nav-tab" data-view="calendar" onclick="switchView('calendar')">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1" y="2" width="14" height="13" rx="1.5"/><path d="M5 1v3M11 1v3M1 7h14"/></svg>
          Calendar
        </button>
        <button class="nav-tab" data-view="email" onclick="switchView('email')">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1" y="3" width="14" height="10" rx="1.5"/><path d="M1 5l7 5 7-5"/></svg>
          Email
        </button>
        <button class="nav-tab" data-view="social" onclick="switchView('social')">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3h10a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2H8l-3.5 2V12H3a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><circle cx="5" cy="7.5" r=".75" fill="currentColor" stroke="none"/><circle cx="8" cy="7.5" r=".75" fill="currentColor" stroke="none"/><circle cx="11" cy="7.5" r=".75" fill="currentColor" stroke="none"/></svg>
          Social Media
        </button>
        <button class="nav-tab" data-view="health" onclick="switchView('health')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
          Health
        </button>
        <button class="nav-tab" data-view="home" onclick="switchView('home')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
          Home
        </button>
        <button class="nav-tab" data-view="dining" onclick="switchView('dining')">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M5 2v5a3 3 0 0 0 6 0V2M8 9v5M6 14h4"/></svg>
          Dining
        </button>
        <button class="nav-tab" data-view="navigate" onclick="switchView('navigate')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>
          Navigate
        </button>
        <button class="nav-tab" data-view="journey" onclick="switchView('journey')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12h18M3 6h18M3 18h18"/><circle cx="8" cy="12" r="2" fill="currentColor" stroke="none"/></svg>
          Journey
        </button>
        <button class="nav-tab" data-view="vision" onclick="switchView('vision')">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="2.5"/><path d="M1 8C2.5 4 5 2 8 2s5.5 2 7 6c-1.5 4-4 6-7 6S2.5 12 1 8z"/></svg>
          Vision
        </button>
        <button class="nav-tab" data-view="news" onclick="switchView('news')">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1" y="2" width="14" height="12" rx="1.5"/><path d="M4 6h8M4 9h5"/></svg>
          News
        </button>
      </div>
    </div>

    <div class="nav-section-label">Standalone Pages</div>
    <details class="nav-module-drawer">
      <summary class="nav-module-summary">Open direct web routes <span>Optional</span></summary>
      <div class="nav-route-links">
        <a class="nav-route-link" href="/briefing-center"><span>Daily Briefing</span><code>/briefing-center</code></a>
        <a class="nav-route-link" href="/command-center"><span>Command Center</span><code>/command-center</code></a>
        <a class="nav-route-link" href="/progress-center"><span>Progress Center</span><code>/progress-center</code></a>
        <a class="nav-route-link" href="/activity-center"><span>Activity Feed</span><code>/activity-center</code></a>
        <a class="nav-route-link" href="/recovery-center"><span>Recovery Center</span><code>/recovery-center</code></a>
        <a class="nav-route-link" href="/publish"><span>Publish</span><code>/publish</code></a>
        <a class="nav-route-link" href="/agent-ops-center"><span>Agent Ops</span><code>/agent-ops-center</code></a>
        <a class="nav-route-link" href="/mission-board"><span>Mission Board</span><code>/mission-board</code></a>
        <a class="nav-route-link" href="/approval-queue"><span>Approval Queue</span><code>/approval-queue</code></a>
        <a class="nav-route-link" href="/supervision-snapshot"><span>Supervision</span><code>/supervision-snapshot</code></a>
        <a class="nav-route-link" href="/settings-center"><span>Settings Center</span><code>/settings-center</code></a>
        <a class="nav-route-link" href="/health-center"><span>Health Center</span><code>/health-center</code></a>
        <a class="nav-route-link" href="/huddle-center"><span>Huddle Center</span><code>/huddle-center</code></a>
        <a class="nav-route-link" href="/chronicle-center"><span>Legacy Module</span><code>/chronicle-center</code></a>
        <a class="nav-route-link" href="/navigation-center"><span>Navigation Center</span><code>/navigation-center</code></a>
      </div>
    </details>
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
  <div id="view-chat" class="view command-view">
    <div class="command-header">
      <div>
        <div class="command-kicker">Desktop Experience</div>
        <div class="view-title">COMMAND<div class="view-title-line"></div></div>
        <div class="command-subtitle">Executive control, life operating posture, decision authority, and the real work that moves because you touched it. Command keeps the transcript alive, but the page now behaves like an actual desktop operating board.</div>
      </div>
      <div class="command-motto">
        <div class="command-motto-mark">✦</div>
        <div>
          <strong>Lead with wisdom. Act with clarity.</strong>
          <span>JARVIS protects what matters and moves what moves you.</span>
        </div>
      </div>
    </div>

    <div class="command-desktop-stage">
      <div class="command-desktop-shell">
        <aside class="command-sidebar">
          <div class="command-sidebar-orb">✦</div>
          <div class="command-sidebar-brand">
            <strong>JARVIS</strong>
            <span>Command</span>
          </div>
          <div class="command-sidebar-nav">
            <div class="command-sidebar-item active" onclick="switchView('chat')">⌂ Command</div>
            <div class="command-sidebar-item" onclick="switchView('overview')">☀ Daily Brief</div>
            <div class="command-sidebar-item" onclick="commandOpenCommandRoute('/mission-board')">▣ Mission Board</div>
            <div class="command-sidebar-item" onclick="switchView('agents')">◎ Agent Ops</div>
            <div class="command-sidebar-item" onclick="switchView('approvals')">☑ Approvals</div>
            <div class="command-sidebar-item" onclick="commandOpenCommandRoute('/supervision-snapshot')">⟡ Supervision</div>
            <div class="command-sidebar-item" onclick="switchView('workshop')">✦ Foundry</div>
            <div class="command-sidebar-item" onclick="switchView('publishing')">⇢ Publish</div>
            <div class="command-sidebar-item" onclick="switchView('chronicle')">❖ Legacy</div>
            <div class="command-sidebar-item" onclick="switchView('huddle')">⚑ Huddle</div>
            <div class="command-sidebar-item" onclick="switchView('navigate')">🧭 Navigation</div>
            <div class="command-sidebar-item" onclick="switchView('health')">♥ Health</div>
            <div class="command-sidebar-item" onclick="switchView('home')">⌂ Home</div>
            <div class="command-sidebar-item" onclick="commandOpenCommandRoute('/settings-center')">⚙ Systems</div>
            <div class="command-sidebar-item" onclick="switchView('forge')">⛭ Forge</div>
          </div>
          <div class="command-sidebar-foot">
            <div class="command-status-card">
              <strong>System Status</strong>
              <span id="command-system-status">Loading command posture…</span>
              <div class="command-mini-actions" style="margin-top:10px;">
                <button class="command-sequence-btn" id="command-refresh-button" onclick="refreshCommandDesktop()">Refresh</button>
                <button class="command-sequence-btn" id="command-live-button" onclick="refreshCommandLiveSignal()">Refresh Live</button>
              </div>
              <span id="command-runtime-note" style="display:block;margin-top:10px;color:rgba(255,255,255,0.58);font-size:11px;line-height:1.45;">Command posture is loading live data…</span>
              <div class="command-status-link" onclick="switchView('notifications')">System Overview →</div>
            </div>
          </div>
        </aside>

        <main class="command-main">
          <div class="command-topbar">
            <div class="command-chipbar">
              <div class="command-kicker">Executive Operating System</div>
              <strong>JARVIS <span>COMMAND</span></strong>
              <div class="command-chiprow">
                <div class="command-chip">Operational Mode <b id="command-mode-chip">Focus Block</b></div>
                <div class="command-chip">Interruption Posture <b id="command-interruption-chip">Low</b></div>
                <div class="command-chip">Trust Level <b id="command-trust-chip">Elevated</b></div>
                <div class="command-chip">Autonomy <b id="command-autonomy-chip">Bounded</b></div>
                <div class="command-chip">Watch State <b id="command-watch-chip">Normal</b></div>
              </div>
            </div>
            <div class="command-quote-card">
              <blockquote id="command-quote">“Lead with wisdom. Act with clarity.”</blockquote>
              <p id="command-quote-copy">JARVIS protects what matters and moves what moves you.</p>
            </div>
            <div class="command-profile-card">
              <div class="command-profile-avatar">👤</div>
              <div>
                <strong id="command-profile-name">Chris</strong>
                <span id="command-profile-role">Executive / Builder</span>
              </div>
            </div>
          </div>

          <div class="command-sequence-bar">
            <div class="command-sequence-copy">
              <div class="command-kicker">Desktop Sequence</div>
              <strong id="command-page-label">Command Board</strong>
              <span>One active desktop command board is in focus, with the shared navigation pattern preserved for consistency across the system.</span>
            </div>
            <div class="command-sequence-controls">
              <button class="command-sequence-btn" id="command-nav-prev" disabled aria-label="Previous command page">←</button>
              <div class="command-sequence-page" id="command-page-count">Page 1 of 1</div>
              <button class="command-sequence-btn" id="command-nav-next" disabled aria-label="Next command page">→</button>
            </div>
          </div>

          <div class="command-grid">
            <section class="command-card command-span-4"><div class="command-card-inner"><div class="command-card-header"><div><div class="command-card-number">1. Command Presence</div><h3>Know your state. Set your posture.</h3><p>Command starts with how you are entering the day, what lane you are protecting, and what interruption budget you are permitting.</p></div></div><div class="command-presence-grid"><div class="command-presence-ring">➤</div><div class="command-presence-copy"><strong id="command-presence-title">Focus Block Mode</strong><span id="command-presence-copy">Loading command presence…</span></div></div><div class="command-data-table"><div class="command-data-row"><label>Primary Lane</label><span id="command-presence-lane">—</span></div><div class="command-data-row"><label>Location</label><span id="command-presence-location">—</span></div><div class="command-data-row"><label>Time Window</label><span id="command-presence-window">—</span></div><div class="command-data-row"><label>Next Hard Stop</label><span id="command-presence-stop">—</span></div></div><button class="command-action-btn" onclick="switchView('overview')">Change Mode →</button></div></section>

            <section class="command-card command-span-4"><div class="command-card-inner"><div class="command-card-header"><div><div class="command-card-number">2. Truth Surface</div><h3>The real state of your world.</h3><p>Reality first. Command should surface what changed, what is blocked, and what is quietly moving without theatrics.</p></div></div><div class="command-truth-grid" id="command-truth-grid"></div><div class="command-summary-box"><strong>System Summary</strong><span id="command-truth-summary">Loading reality posture…</span></div><div class="command-section-link" onclick="window.location.href='/command-center'">Full reality map →</div></div></section>

            <section class="command-card command-span-4"><div class="command-card-inner"><div class="command-card-header"><div><div class="command-card-number">3. Decision Spine</div><h3>What requires your authority.</h3><p>Approvals, surfaced needs, and strategic choices should gather here without forcing you into ten different routes.</p></div></div><div class="command-decision-table" id="command-decision-list"></div><div class="command-section-link" onclick="switchView('approvals')">View all decision gates →</div></div></section>

            <section class="command-card command-span-3"><div class="command-card-inner"><div class="command-card-header"><div><div class="command-card-number">Command Actions</div><h3>Direct. Delegate. Override.</h3></div></div><div class="command-activity-list" id="command-actions-list"></div></div></section>

            <section class="command-card command-span-3"><div class="command-card-inner"><div class="command-card-header"><div><div class="command-card-number">4. Direct Action Console</div><h3>Move the world.</h3><p>Launch fast, useful work from the command deck without leaving the page.</p></div></div><div class="command-action-grid" id="command-direct-actions"></div><div class="command-section-link" onclick="switchView('workshop')">View all action lanes →</div></div></section>

            <section class="command-card command-span-3"><div class="command-card-inner"><div class="command-card-header"><div><div class="command-card-number">5. While You Were Away</div><h3>Continuity. Progress. Preparedness.</h3></div></div><div class="command-activity-list" id="command-away-list"></div><div class="command-section-link" onclick="window.location.href='/activity-center'">View full overnight report →</div></div></section>

            <section class="command-card command-span-3"><div class="command-card-inner"><div class="command-card-header"><div><div class="command-card-number">6. Movement & Route</div><h3>Your day in motion.</h3></div></div><div class="command-mini-grid"><div class="command-route-map"><svg viewBox="0 0 260 160" preserveAspectRatio="none"><path d="M28 136 C50 120 62 86 104 88 C142 90 154 54 184 46 C202 41 218 26 230 18" stroke="rgba(78,162,255,0.92)" stroke-width="4" fill="none" stroke-linecap="round" stroke-dasharray="8 9"></path><circle cx="28" cy="136" r="9" fill="#e7a64d"></circle><circle cx="230" cy="18" r="9" fill="#8ed6ff"></circle></svg></div><div class="command-mini-grid" style="grid-template-columns:1fr;"><div class="command-mini-card"><strong id="command-route-next">Next move</strong><span id="command-route-next-copy">Loading route posture…</span></div><div class="command-mini-card"><strong id="command-route-traffic">Traffic</strong><span id="command-route-weather">Loading conditions…</span></div></div></div><div class="command-section-link" onclick="switchView('navigate')">Open full navigation →</div></div></section>

            <section class="command-card command-span-3"><div class="command-card-inner"><div class="command-card-header"><div><div class="command-card-number">7. Family & Household</div><h3>What matters at home.</h3></div></div><div class="command-family-list" id="command-family-list"></div><div class="command-section-link" onclick="switchView('calendar')">View household hub →</div></div></section>

            <section class="command-card command-span-4"><div class="command-card-inner"><div class="command-card-header"><div><div class="command-card-number">8. Workshop & Creative Momentum</div><h3>Protect and prioritize your creative work.</h3></div></div><div class="command-split-grid" style="grid-template-columns:1.1fr .9fr;"><div class="command-activity-list" id="command-foundry-list"></div><div class="command-mini-card"><strong>Today's Creative Focus</strong><span id="command-foundry-focus">Loading high-leverage asset…</span><div class="command-section-link" style="margin-top:12px;" onclick="switchView('foundry')">Open Foundry dashboard →</div></div></div></div></section>

            <section class="command-card command-span-4"><div class="command-card-inner"><div class="command-card-header"><div><div class="command-card-number">9. Health & Recovery</div><h3>Protect the operator.</h3></div></div><div class="command-activity-list" id="command-health-list"></div><div class="command-section-link" onclick="switchView('health')">Open health dashboard →</div></div></section>

            <section class="command-card command-span-4"><div class="command-card-inner"><div class="command-card-header"><div><div class="command-card-number">10. Follow-Through Lane</div><h3>Keep today from dissolving.</h3></div></div><div class="command-follow-list" id="command-follow-list"></div><div class="command-section-link" onclick="switchView('notifications')">View all open loops →</div></div></section>

            <section class="command-card command-span-3"><div class="command-card-inner"><div class="command-card-header"><div><div class="command-card-number">11. Supervision & Trust</div><h3>Agents. Rules. Confidence.</h3></div></div><div class="command-supervision-box"><strong id="command-supervision-score">92%</strong><span id="command-supervision-copy">Overall command confidence</span></div><div class="command-mini-grid" id="command-supervision-grid"></div><div class="command-section-link" onclick="window.location.href='/supervision-snapshot'">Open supervision center →</div></div></section>

            <section class="command-card command-span-3"><div class="command-card-inner"><div class="command-card-header"><div><div class="command-card-number">12. Mode Shaper</div><h3>Set the tone. Shape the system.</h3></div></div><div class="command-action-grid" id="command-mode-grid"></div></div></section>

            <section class="command-card command-span-3"><div class="command-card-inner"><div class="command-card-header"><div><div class="command-card-number">13. Strategic Overview</div><h3>The long view, always in sight.</h3></div></div><div class="command-mini-grid" id="command-strategy-grid"></div><div class="command-section-link" onclick="window.location.href='/progress-center'">Open strategic cockpit →</div></div></section>

            <section class="command-card command-span-3"><div class="command-card-inner"><div class="command-card-header"><div><div class="command-card-number">14. Next Best Move</div><h3>If everything else fails away.</h3></div></div><div class="command-mini-card"><strong id="command-next-title">Loading next move…</strong><span id="command-next-copy">JARVIS is evaluating the best next step.</span><button class="command-action-btn" id="command-next-button" onclick="switchView('notifications')">Begin Now →</button></div></div></section>

            <section class="command-card command-span-12"><div class="command-card-inner"><div class="command-card-header"><div><div class="command-card-number">15. Command Reminder</div><h3>Anchor for the day.</h3></div></div><div class="command-mini-card"><strong id="command-reminder-title">Wisdom is knowing what matters.</strong><span id="command-reminder-copy">Courage is doing it anyway. Love is why you do it for.</span></div></div></section>
          </div>

          <div class="command-card command-trace-shell">
            <div class="command-card-inner">
              <div class="command-card-header">
                <div>
                  <div class="command-card-number">Live Command Trace</div>
                  <h3>Direct channel to JARVIS</h3>
                  <p>The desktop board sets posture. The transcript below keeps the actual work visible when you run commands.</p>
                </div>
              </div>
              <div id="chat-area" class="chat-area">
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
          </div>
        </main>
      </div>
    </div>
  </div>

  <!-- ── OVERVIEW ──────────────────────────────────────────────── -->
  <div id="view-overview" class="view">
    <div class="dailybrief-shell">
      <div class="dailybrief-masthead">
        <div class="dailybrief-brand">
          <div class="dailybrief-brand-mark">✦</div>
          <div class="dailybrief-brand-copy">
            <div class="dailybrief-kicker">JARVIS MORNING DESKTOP</div>
            <h1>JARVIS <span>DAILY BRIEF</span></h1>
            <p>Your day. Clarified. Aligned. Activated.</p>
          </div>
        </div>
        <div class="dailybrief-top-card dailybrief-greeting-card">
          <div class="dailybrief-kicker">Executive Posture</div>
          <h2 id="dailybrief-top-greeting">Good morning, Chris.</h2>
          <p id="brief-date">Loading your posture…</p>
        </div>
        <div class="dailybrief-top-card dailybrief-scripture-card">
          <div class="dailybrief-kicker">Faithful Center</div>
          <blockquote id="dailybrief-scripture-copy">Be strong and courageous. Do not be afraid; do not be discouraged, for the Lord your God will be with you wherever you go.</blockquote>
          <footer id="dailybrief-scripture-ref">Joshua 1:9</footer>
        </div>
        <div class="dailybrief-top-metrics">
          <div class="dailybrief-top-metric"><strong>Sleep Quality</strong><span id="dailybrief-top-sleep">—</span><small id="dailybrief-top-sleep-copy">Loading</small></div>
          <div class="dailybrief-top-metric"><strong>Readiness</strong><span id="dailybrief-top-readiness">—</span><small id="dailybrief-top-readiness-copy">Loading</small></div>
          <div class="dailybrief-top-metric"><strong>Focus Window</strong><span id="dailybrief-top-focus">—</span><small id="dailybrief-top-focus-copy">Loading</small></div>
          <div class="dailybrief-top-metric"><strong>Stress Level</strong><span id="dailybrief-top-stress">—</span><small id="dailybrief-top-stress-copy">Loading</small></div>
        </div>
        <div class="dailybrief-top-card dailybrief-profile-card">
          <div class="dailybrief-avatar">👤</div>
          <div class="dailybrief-profile-meta">
            <strong id="dailybrief-profile-name">Chris</strong>
            <span id="dailybrief-profile-role">Builder. Father. Executive. Steward.</span>
          </div>
        </div>
      </div>

      <div class="overview-mode-bar" id="overview-mode-bar">
        <button class="mode-pill" data-mode="morning_brief" onclick="setLayoutMode('morning_brief')">🌅 Morning Brief</button>
        <button class="mode-pill" data-mode="lunch_brief" onclick="setLayoutMode('lunch_brief')">☀️ Lunch Brief</button>
        <button class="mode-pill" data-mode="daily_recap" onclick="setLayoutMode('daily_recap')">🌙 Daily Recap</button>
        <span class="mode-auto-chip" id="mode-auto-chip">AUTO</span>
        <span class="mode-clock" id="mode-clock">—</span>
      </div>

      <div class="dailybrief-runtime-bar">
        <div class="dailybrief-runtime-controls">
          <select id="dailybrief-actor-select" class="dailybrief-select" aria-label="Daily brief actor" onchange="refreshDailyBriefDesktop(this.value)"></select>
          <button class="dailybrief-button secondary" id="dailybrief-refresh-button" onclick="refreshDailyBriefDesktop()">Refresh Brief</button>
          <button class="dailybrief-button secondary" id="dailybrief-livebrief-button" onclick="refreshDailyBriefLivePacket()">Refresh Live Brief</button>
        </div>
        <div class="dailybrief-runtime-note" id="dailybrief-runtime-note">Loading the live Daily Brief systems…</div>
      </div>

      <div class="overview-alert-banner" id="overview-alert-banner" style="display:none;">
        <span id="alert-banner-icon">⚠️</span>
        <span class="alert-banner-msg" id="alert-banner-msg"></span>
        <button class="alert-banner-action" id="alert-banner-action-btn" onclick="alertBannerNavigate()">View →</button>
        <button class="alert-banner-dismiss" onclick="dismissAlertBanner()">✕</button>
      </div>

      <div id="overview-user-bar" style="display:none;margin-bottom:0;padding:10px 14px;background:rgba(0,212,255,0.07);border:1px solid rgba(0,212,255,0.18);border-radius:16px;align-items:center;gap:10px;font-size:12px;">
        <span id="overview-user-avatar" style="font-size:20px;line-height:1;"></span>
        <div style="flex:1;min-width:0;">
          <div id="overview-user-name" style="font-weight:600;color:var(--text-1);"></div>
          <div id="overview-user-role" style="font-size:10px;color:var(--text-3);"></div>
        </div>
        <button onclick="switchUser()" style="background:none;border:1px solid rgba(255,255,255,0.2);border-radius:6px;color:var(--text-2);padding:4px 12px;font-size:11px;cursor:pointer;white-space:nowrap;">Switch User</button>
      </div>

      <div class="dailybrief-board">
        <section class="dailybrief-card"><div class="dailybrief-card-inner"><div class="dailybrief-card-header"><div><div class="dailybrief-card-number">1. First Light</div><p>Center your mind. Align your heart. Enter the day with purpose.</p></div></div><div class="dailybrief-hero-art"><span id="dailybrief-firstlight-scene">The day is opening in front of you.</span></div><div class="dailybrief-firstlight-grid"><div class="dailybrief-copy-block" id="dailybrief-firstlight-orientation">Loading your orientation…</div><div class="dailybrief-side-stack"><div class="dailybrief-tone-card"><strong>Today's Orientation</strong><span id="dailybrief-firstlight-direction">Loading…</span></div><div class="dailybrief-tone-card"><strong>Current Focus</strong><span id="dailybrief-firstlight-focus">Loading…</span></div></div></div><div class="dailybrief-pillars"><div class="dailybrief-pillar"><strong>Calling Focus</strong><span id="dailybrief-pillar-calling">Loading…</span></div><div class="dailybrief-pillar"><strong>Character Focus</strong><span id="dailybrief-pillar-character">Loading…</span></div><div class="dailybrief-pillar"><strong>Spiritual Rhythm</strong><span id="dailybrief-pillar-rhythm">Loading…</span></div></div></div></section>
        <section class="dailybrief-card"><div class="dailybrief-card-inner"><div class="dailybrief-card-header"><div><div class="dailybrief-card-number">2. What Matters Now</div><p>Your center of gravity for today.</p></div></div><div class="dailybrief-whatmatters-grid" id="dailybrief-whatmatters-list"></div><div class="dailybrief-one-thing"><div><strong>One Thing That Would Make Today Real</strong><span id="dailybrief-one-thing-copy">Loading…</span></div><button class="dailybrief-button" onclick="switchView('workshop')">Start First Focus →</button></div></div></section>
        <section class="dailybrief-card"><div class="dailybrief-card-inner"><div class="dailybrief-card-header"><div><div class="dailybrief-card-number">3. While You Were Away</div><p>Overnight summary from JARVIS and your agents.</p></div></div><div class="dailybrief-list" id="dailybrief-away-list"></div><div style="margin-top:14px;display:flex;justify-content:flex-end;"><button class="dailybrief-button" onclick="switchView('agents')">Review All Updates →</button></div></div></section>
        <section class="dailybrief-card"><div class="dailybrief-card-inner"><div class="dailybrief-card-header"><div><div class="dailybrief-card-number">4. Decision Gates</div><p>Items that need your decision.</p></div></div><div class="dailybrief-list" id="dailybrief-decision-list"></div><div style="margin-top:14px;display:flex;justify-content:flex-end;"><button class="dailybrief-button" onclick="switchView('approvals')">View All Decision Gates →</button></div></div></section>
        <section class="dailybrief-card"><div class="dailybrief-card-inner"><div class="dailybrief-card-header"><div><div class="dailybrief-card-number">5. Movement & Route</div><p>Your movement plan for the day.</p></div></div><div class="dailybrief-split"><div class="dailybrief-list" id="dailybrief-route-schedule"></div><div class="dailybrief-route-card"><div class="dailybrief-route-map"></div><div class="dailybrief-route-path"><svg viewBox="0 0 300 220" preserveAspectRatio="none"><path d="M24 188 C62 170 72 126 112 124 C168 121 160 65 216 58 C245 54 258 34 278 18" stroke="rgba(255,176,79,0.9)" stroke-width="4" fill="none" stroke-linecap="round" stroke-dasharray="7 8"></path><circle cx="24" cy="188" r="9" fill="#f7d49a"></circle><circle cx="278" cy="18" r="10" fill="#6ed89c"></circle><circle cx="112" cy="124" r="8" fill="#f1aa49"></circle><circle cx="214" cy="58" r="8" fill="#f1aa49"></circle></svg></div><div class="dailybrief-route-content"><div><div class="dailybrief-kicker">Travel & Route</div><div class="dailybrief-route-metrics"><strong id="dailybrief-route-time">—</strong><span id="dailybrief-route-destination">Loading route…</span></div></div><div class="dailybrief-copy-block" id="dailybrief-route-copy">No route-sensitive commitments are loaded yet.</div></div></div></div><div style="margin-top:14px;display:flex;justify-content:flex-end;"><button class="dailybrief-button" onclick="switchView('navigate')">Optimize Route →</button></div></div></section>
        <section class="dailybrief-card"><div class="dailybrief-card-inner"><div class="dailybrief-card-header"><div><div class="dailybrief-card-number">6. Family & Household Posture</div><p>What matters most at home.</p></div></div><div class="dailybrief-split"><div class="dailybrief-list" id="dailybrief-family-list"></div><div><div class="dailybrief-kicker">Today's Coordination</div><div class="dailybrief-checklist" id="dailybrief-family-checklist"></div></div></div><div style="margin-top:14px;display:flex;justify-content:flex-end;"><button class="dailybrief-button" onclick="switchView('calendar')">View Family Calendar →</button></div></div></section>
        <section class="dailybrief-card"><div class="dailybrief-card-inner"><div class="dailybrief-card-header"><div><div class="dailybrief-card-number">7. Workshop & Creative Momentum</div><p>Your highest leverage creative work.</p></div></div><div class="dailybrief-list" id="dailybrief-foundry-list"></div><div class="dailybrief-one-thing" style="margin-top:16px;"><div><strong>Today's Creative Focus</strong><span id="dailybrief-foundry-focus">Loading your best creation window…</span></div><button class="dailybrief-button" onclick="switchView('foundry')">Enter Foundry →</button></div></div></section>
        <section class="dailybrief-card"><div class="dailybrief-card-inner"><div class="dailybrief-card-header"><div><div class="dailybrief-card-number">8. Health & Recovery</div><p>Protect the operator.</p></div></div><div class="dailybrief-list" id="dailybrief-health-metrics"></div><div class="dailybrief-one-thing" style="margin-top:16px;"><div><strong>Today's Recommendation</strong><span id="dailybrief-health-recommendation">Loading Sam Wilson guidance…</span></div><button class="dailybrief-button" onclick="switchView('health')">View Health Dashboard →</button></div></div></section>
        <section class="dailybrief-card"><div class="dailybrief-card-inner"><div class="dailybrief-card-header"><div><div class="dailybrief-card-number">9. Follow-Through Lane</div><p>Keep today from dissolving.</p></div></div><div class="dailybrief-openloops"><div class="dailybrief-list" id="dailybrief-followthrough-list"></div><div><div class="dailybrief-loop-ring"><strong id="dailybrief-openloops-total">—</strong><span>Open Loops</span></div><div class="dailybrief-breakdown"><div><strong id="dailybrief-loop-high">0</strong>High</div><div><strong id="dailybrief-loop-medium">0</strong>Medium</div><div><strong id="dailybrief-loop-low">0</strong>Low</div></div></div></div><div style="margin-top:14px;display:flex;justify-content:flex-end;"><button class="dailybrief-button" onclick="switchView('notifications')">View All Open Loops →</button></div></div></section>
        <section class="dailybrief-card"><div class="dailybrief-card-inner"><div class="dailybrief-card-header"><div><div class="dailybrief-card-number">10. Today At A Glance</div><p>Your day in one place.</p></div></div><div class="dailybrief-timeline" id="dailybrief-timeline"></div></div></section>
        <section class="dailybrief-card"><div class="dailybrief-card-inner"><div class="dailybrief-card-header"><div><div class="dailybrief-card-number">11. Today's Briefing Summary</div><p>The executive summary.</p></div></div><div class="dailybrief-summary-grid"><div class="dailybrief-summary-copy" id="dailybrief-summary-copy">Loading your briefing summary…</div><div class="dailybrief-score-badge"><strong id="dailybrief-overall-score">—</strong><span id="dailybrief-overall-copy">Overall day readiness</span></div></div></div></section>
        <section class="dailybrief-card"><div class="dailybrief-card-inner"><div class="dailybrief-card-header"><div><div class="dailybrief-card-number">12. Next Decision Gate</div><p>Your next best move.</p></div></div><div class="dailybrief-list" id="dailybrief-nextgate-list"></div></div></section>
      </div>

      <div class="dailybrief-compat" aria-hidden="true">
        <div id="overview-greeting"></div>
        <div id="overview-subtitle"></div>
        <div id="overview-family-bar"></div>
        <div id="stat-agents"></div>
        <div id="stat-missions"></div>
        <div id="stat-approvals"></div>
        <div id="stat-memory"></div>
      </div>
    </div>
  </div>

  <!-- ── NOTIFICATIONS ───────────────────────────────────────── -->
  <div id="view-notifications" class="view needs-view" style="display:none;">
    <div class="needs-header">
      <div class="needs-brand">
        <div class="needs-brand-mark">
          <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
            <path d="M9.09 5.25a2.91 2.91 0 1 1 5.82 0c0 .71.26 1.39.73 1.93.92 1.05 1.86 2.61 1.86 4.82V15l1.13 1.5c.31.42.01 1-.52 1H5.89c-.53 0-.83-.58-.52-1L6.5 15v-3c0-2.21.94-3.77 1.86-4.82.47-.54.73-1.22.73-1.93Z"></path>
            <path d="M10 18a2 2 0 0 0 4 0"></path>
          </svg>
        </div>
        <div class="needs-brand-copy">
          <div class="needs-kicker">Authority, Presence & Conscience Engine</div>
          <div class="needs-title">JARVIS <span>NEEDS YOU</span></div>
          <div class="needs-subtitle">Only what truly requires your authority, judgment, presence, or conscience.</div>
          <div class="needs-brand-detail">Your wisdom is the threshold automation cannot cross.</div>
        </div>
      </div>

      <div class="needs-header-center">
        <div class="needs-stat-grid">
          <div class="needs-stat-shell"><div class="needs-stat-label">Total Needs You</div><div class="needs-stat-value" id="needs-stat-total">—</div><div class="needs-stat-sub" id="needs-stat-total-sub">Attention stack</div></div>
          <div class="needs-stat-shell"><div class="needs-stat-label">Decisions</div><div class="needs-stat-value" id="needs-stat-decisions">—</div><div class="needs-stat-sub" id="needs-stat-decisions-sub">High authority</div></div>
          <div class="needs-stat-shell"><div class="needs-stat-label">Presence</div><div class="needs-stat-value" id="needs-stat-presence">—</div><div class="needs-stat-sub" id="needs-stat-presence-sub">Human presence</div></div>
          <div class="needs-stat-shell"><div class="needs-stat-label">Escalations</div><div class="needs-stat-value" id="needs-stat-escalations">—</div><div class="needs-stat-sub" id="needs-stat-escalations-sub">Time sensitive</div></div>
          <div class="needs-stat-shell"><div class="needs-stat-label">Approvals</div><div class="needs-stat-value" id="needs-stat-approvals">—</div><div class="needs-stat-sub" id="needs-stat-approvals-sub">Awaiting you</div></div>
          <div class="needs-stat-shell"><div class="needs-stat-label">Waiting For You</div><div class="needs-stat-value" id="needs-stat-waiting">—</div><div class="needs-stat-sub" id="needs-stat-waiting-sub">Blocked without you</div></div>
        </div>
        <div class="needs-quote">
          <div class="needs-quote-mark">“</div>
          <div>
            <strong>Your wisdom is the threshold automation cannot cross.</strong>
            <span>JARVIS gathers the facts, preserves the context, and only surfaces the moments that truly require you.</span>
          </div>
        </div>
      </div>

      <div class="needs-profile">
        <div class="needs-profile-meta">
          <div class="needs-profile-avatar">CB</div>
          <div>
            <strong>Chris Binion</strong>
            <span>Executive Mode</span>
          </div>
        </div>
        <div style="display:grid;gap:4px;">
          <span id="needs-generated-at">Updated just now</span>
          <span id="needs-runtime-note">Needs You is live.</span>
        </div>
      </div>
    </div>

    <div class="needs-shell">
      <aside class="needs-sidebar">
        <div class="needs-side-title">Needs You Status</div>
        <div class="needs-side-list" id="needs-sidebar-list"></div>
        <button class="needs-side-cta" onclick="switchView('settings')">Needs You Settings →</button>
      </aside>

      <div class="needs-grid">
        <section class="needs-card needs-span-4">
          <div class="needs-card-inner">
            <div class="needs-card-header">
              <div>
                <div class="needs-card-number">1. Immediate Needs (Attention Now)</div>
                <h3>Requires your decision or presence today.</h3>
              </div>
              <button class="needs-header-action" onclick="loadNotificationCenter()">Refresh</button>
            </div>
            <div class="needs-list" id="needs-immediate-list"></div>
            <button class="needs-section-link" style="margin-top:14px;" onclick="switchView('command')">View all needs →</button>
          </div>
        </section>

        <section class="needs-card needs-span-4">
          <div class="needs-card-inner">
            <div class="needs-card-header">
              <div>
                <div class="needs-card-number">2. Why This Needs You</div>
                <h3>We’ve already analyzed and prepared the context.</h3>
              </div>
            </div>
            <div class="needs-lead-card" id="needs-lead-card"></div>
          </div>
        </section>

        <section class="needs-card needs-span-4">
          <div class="needs-card-inner">
            <div class="needs-card-header">
              <div>
                <div class="needs-card-number">3. Presence Requests</div>
                <h3>Moments that need you, not just a decision.</h3>
              </div>
              <button class="needs-header-action" onclick="switchView('home')">View All</button>
            </div>
            <div class="needs-list" id="needs-presence-list"></div>
          </div>
        </section>

        <section class="needs-card needs-span-4">
          <div class="needs-card-inner">
            <div class="needs-card-header">
              <div>
                <div class="needs-card-number">4. Escalations</div>
                <h3>Crossed important thresholds.</h3>
              </div>
              <button class="needs-header-action" onclick="switchView('supervision')">View All</button>
            </div>
            <div class="needs-list" id="needs-escalations-list"></div>
          </div>
        </section>

        <section class="needs-card needs-span-4">
          <div class="needs-card-inner">
            <div class="needs-card-header">
              <div>
                <div class="needs-card-number">5. Approvals Waiting</div>
                <h3>Decisions prepared, waiting on you.</h3>
              </div>
              <button class="needs-header-action" onclick="switchView('approvals')">View All</button>
            </div>
            <div class="needs-list" id="needs-approvals-list"></div>
          </div>
        </section>

        <section class="needs-card needs-span-4">
          <div class="needs-card-inner">
            <div class="needs-card-header">
              <div>
                <div class="needs-card-number">6. Context Summary</div>
                <h3>Everything you need to decide well.</h3>
              </div>
            </div>
            <div class="needs-summary-grid" id="needs-context-summary"></div>
            <div class="needs-context-split" style="margin-top:12px;">
              <div class="needs-context-col">
                <h4>Related Threads</h4>
                <div class="needs-bullet-list" id="needs-related-threads"></div>
              </div>
              <div class="needs-context-col">
                <h4>Relevant Agents</h4>
                <div class="needs-bullet-list" id="needs-relevant-agents"></div>
              </div>
            </div>
          </div>
        </section>

        <section class="needs-card needs-span-4">
          <div class="needs-card-inner">
            <div class="needs-card-header">
              <div>
                <div class="needs-card-number">7. Authority Map</div>
                <h3>What requires you vs. what can move without you.</h3>
              </div>
              <button class="needs-header-action" onclick="switchView('supervision')">Manage Boundaries</button>
            </div>
            <div class="needs-authority-wrap">
              <div class="needs-donut">
                <div class="needs-donut-center">
                  <div>
                    <strong id="needs-authority-score">64%</strong>
                    <span>Handled with your intervention</span>
                  </div>
                </div>
              </div>
              <div class="needs-authority-list" id="needs-authority-list"></div>
            </div>
          </div>
        </section>

        <section class="needs-card needs-span-4">
          <div class="needs-card-inner">
            <div class="needs-card-header">
              <div>
                <div class="needs-card-number">8. Decision Modes</div>
                <h3>Different needs, different actions.</h3>
              </div>
            </div>
            <div class="needs-modes-grid" id="needs-modes-grid"></div>
          </div>
        </section>

        <section class="needs-card needs-span-4">
          <div class="needs-card-inner">
            <div class="needs-card-header">
              <div>
                <div class="needs-card-number">9. Timing Intelligence</div>
                <h3>When JARVIS recommends you act.</h3>
              </div>
              <button class="needs-header-action" onclick="loadNotificationCenter()">Optimize Timing</button>
            </div>
            <div class="needs-timing-grid" id="needs-timing-grid"></div>
          </div>
        </section>

        <section class="needs-card needs-span-4">
          <div class="needs-card-inner">
            <div class="needs-card-header">
              <div>
                <div class="needs-card-number">10. What Happens After You Decide</div>
                <h3>The ripple effect of your decision.</h3>
              </div>
            </div>
            <div class="needs-impact-grid" id="needs-impact-grid"></div>
          </div>
        </section>

        <section class="needs-card needs-span-4">
          <div class="needs-card-inner">
            <div class="needs-card-header">
              <div>
                <div class="needs-card-number">11. Recent Decisions & Outcomes</div>
                <h3>How your decisions shaped results.</h3>
              </div>
              <button class="needs-header-action" onclick="switchView('activity')">View History</button>
            </div>
            <div class="needs-outcome-list" id="needs-outcome-list"></div>
          </div>
        </section>

        <section class="needs-card needs-span-4">
          <div class="needs-card-inner">
            <div class="needs-card-header">
              <div>
                <div class="needs-card-number">12. Coaching & Guardrails</div>
                <h3>Helping you decide with wisdom.</h3>
              </div>
            </div>
            <div class="needs-coaching-list" id="needs-coaching-list"></div>
          </div>
        </section>

        <section class="needs-footer-strip" id="needs-footer-strip"></section>
      </div>
    </div>
  </div>

  <!-- ── DINING ─────────────────────────────────────────────────── -->
  <div id="view-dining" class="view dining-view">
    <div class="dining-shell">
      <div class="dining-headline">
        <div>
          <div class="dining-kicker">Intelligent Dining Search & Experience</div>
          <h1>JARVIS <span>DINING</span></h1>
          <p>Search, shortlist, compare, and decide with a dining desktop that blends Sam's taste-aware recommendations, live nearby results, map context, and reservation confidence.</p>
        </div>
      </div>

      <div class="dining-topbar">
        <div class="dining-voice-prompt">
          <div class="dining-voice-copy">
            <strong>Tell me what you're in the mood for.</strong>
            <span>JARVIS finds the perfect place.</span>
          </div>
          <div class="dining-wave"></div>
          <button class="dining-voice-btn" onclick="runDiningSearch()">🎙</button>
        </div>
        <div class="dining-statbar">
          <div class="dining-stat"><strong id="dining-stat-restaurants">—</strong><span>Restaurants In Network</span></div>
          <div class="dining-stat"><strong id="dining-stat-cities">—</strong><span>Cities Covered</span></div>
          <div class="dining-stat"><strong id="dining-stat-reviews">—</strong><span>Reviews Verified</span></div>
          <div class="dining-stat"><strong id="dining-stat-match">—</strong><span>Match Rate</span></div>
        </div>
        <div class="dining-profile-card">
          <div class="dining-profile-avatar">CB</div>
          <div>
            <strong>Chris Binion</strong>
            <span>Premium Member · Local Explorer</span>
          </div>
        </div>
      </div>

      <div class="dining-sequence-bar">
        <div class="dining-sequence-copy">
          <div class="dining-kicker">Desktop Sequence</div>
          <strong id="dining-page-label">Dining Board</strong>
          <span>Dining is one integrated desktop board right now, with the same shared arrow and page-number pattern used across the other rebuilt modules.</span>
        </div>
        <div class="dining-sequence-controls">
          <button class="dining-sequence-btn" id="dining-nav-prev" disabled aria-label="Previous dining page">←</button>
          <div class="dining-sequence-page" id="dining-page-count">Page 1 of 1</div>
          <button class="dining-sequence-btn" id="dining-nav-next" disabled aria-label="Next dining page">→</button>
        </div>
      </div>

      <div class="dining-desktop-shell">
        <aside class="dining-sidebar">
          <div class="dining-sidebar-brand">
            <div class="dining-sidebar-orb">✦</div>
            <strong>JARVIS</strong>
            <span>Dining</span>
          </div>
          <div class="dining-side-nav">
            <button type="button" class="dining-side-link" data-dining-nav="home" onclick="diningSidebarAction('home')">⌂ Home</button>
            <button type="button" class="dining-side-link" data-dining-nav="map" onclick="diningSidebarAction('map')">🗺 Map</button>
            <button type="button" class="dining-side-link active" data-dining-nav="search" onclick="diningSidebarAction('search')">⌕ Search</button>
            <button type="button" class="dining-side-link" data-dining-nav="dining" onclick="diningSidebarAction('dining')">🍽 Dining</button>
            <button type="button" class="dining-side-link" data-dining-nav="trips" onclick="diningSidebarAction('trips')">🧳 Trips</button>
            <button type="button" class="dining-side-link" data-dining-nav="stops" onclick="diningSidebarAction('stops')">◎ Smart Stops</button>
            <button type="button" class="dining-side-link" data-dining-nav="weather" onclick="diningSidebarAction('weather')">☁ Weather</button>
            <button type="button" class="dining-side-link" data-dining-nav="favorites" onclick="diningSidebarAction('favorites')">♡ Favorites</button>
            <button type="button" class="dining-side-link" data-dining-nav="reservations" onclick="diningSidebarAction('reservations')">📅 Reservations</button>
            <button type="button" class="dining-side-link" data-dining-nav="history" onclick="diningSidebarAction('history')">↺ History</button>
            <button type="button" class="dining-side-link" data-dining-nav="preferences" onclick="diningSidebarAction('preferences')">⚙ Preferences</button>
            <button type="button" class="dining-side-link" data-dining-nav="settings" onclick="diningSidebarAction('settings')">☰ Settings</button>
          </div>
          <div class="dining-sidebar-foot">
            <div class="dining-status-card">
              <strong>JARVIS Dining Status</strong>
              <span id="dining-runtime-note">Loading dining network…</span>
            </div>
            <div class="dining-status-card">
              <strong>Saved Favorites</strong>
              <span id="dining-sidebar-favorites">No favorites loaded yet.</span>
            </div>
            <button class="dining-action-btn" id="dining-refresh-button" type="button" onclick="refreshDiningDesktop(true)">Refresh Dining</button>
          </div>
        </aside>

        <main class="dining-main">
          <div class="dining-grid">
            <section class="dining-card span-4">
              <div class="dining-card-inner">
                <div class="dining-card-header">
                  <div class="dining-card-number">1. What Are You Looking For?</div>
                  <h3>Describe your craving.</h3>
                  <p>JARVIS handles the rest.</p>
                </div>
                <div class="dining-search-row">
                  <input id="dining-query" class="dining-search-input" placeholder="Sushi with a great view and outdoor seating" value="Sushi with a great view and outdoor seating" onkeydown="if(event.key==='Enter') runDiningSearch()">
                  <button class="dining-action-btn" onclick="runDiningSearch()">Search</button>
                </div>
                <span class="dining-chip-label">Quick Filters</span>
                <div class="dining-chip-row">
                  <button class="dining-chip active" data-filter="best" onclick="setDiningQuickFilter('best')">Best Match</button>
                  <button class="dining-chip" data-filter="open" onclick="toggleDiningOpenNow()">Open Now</button>
                  <button class="dining-chip" onclick="applyDiningPrompt('Outdoor seating')">Outdoor Seating</button>
                  <button class="dining-chip" onclick="applyDiningPrompt('Date night')">Date Night</button>
                  <button class="dining-chip" onclick="applyDiningPrompt('Family friendly')">Family Friendly</button>
                  <button class="dining-chip" onclick="applyDiningPrompt('Fine dining')">Fine Dining</button>
                </div>
                <span class="dining-chip-label">Cuisine</span>
                <div class="dining-cuisine-row">
                  <button class="dining-cuisine-pill" data-cuisine="american" onclick="setDiningCuisine('american')">American</button>
                  <button class="dining-cuisine-pill" data-cuisine="italian" onclick="setDiningCuisine('italian')">Italian</button>
                  <button class="dining-cuisine-pill active" data-cuisine="japanese" onclick="setDiningCuisine('japanese')">Sushi</button>
                  <button class="dining-cuisine-pill" data-cuisine="steak" onclick="setDiningCuisine('steak')">Steakhouse</button>
                  <button class="dining-cuisine-pill" data-cuisine="mexican" onclick="setDiningCuisine('mexican')">Mexican</button>
                  <button class="dining-cuisine-pill" data-cuisine="seafood" onclick="setDiningCuisine('seafood')">Seafood</button>
                </div>
                <span class="dining-chip-label">Preferences</span>
                <div class="dining-pref-row">
                  <button class="dining-pref-pill active" data-pref="view" onclick="toggleDiningPref('view')">View</button>
                  <button class="dining-pref-pill" data-pref="$$$" onclick="toggleDiningPref('$$$')">$$$</button>
                  <button class="dining-pref-pill active" data-pref="4.0+" onclick="toggleDiningPref('4.0+')">4.0+ Rating</button>
                  <button class="dining-pref-pill" data-pref="healthy" onclick="toggleDiningPref('healthy')">Healthy Options</button>
                  <button class="dining-pref-pill active" data-pref="cocktails" onclick="toggleDiningPref('cocktails')">Cocktails</button>
                  <button class="dining-pref-pill" data-pref="valet" onclick="toggleDiningPref('valet')">Valet Parking</button>
                </div>
              </div>
            </section>

            <section class="dining-card span-4">
              <div class="dining-card-inner">
                <div class="dining-card-header">
                  <div class="dining-card-number">2. Smart Results</div>
                  <h3>AI-ranked recommendations just for you.</h3>
                  <p>Sam's picks and nearby spots converge here.</p>
                </div>
                <div id="dining-hero-card" class="dining-hero-card"></div>
                <div id="dining-results" class="dining-results-list"></div>
              </div>
            </section>

            <section class="dining-card span-4">
              <div class="dining-card-inner">
                <div class="dining-card-header">
                  <div class="dining-card-number">3. Map View</div>
                  <h3>Explore nearby options on the map.</h3>
                  <p>Filter the dining field without leaving the board.</p>
                </div>
                <div id="dining-map-board" class="dining-map-board">
                  <div class="dining-map-filter">
                    <strong>Filter</strong>
                    <span id="dining-map-filter-copy">Sushi · Open now · Great view</span>
                    <span id="dining-map-range-copy">Within 10 miles</span>
                  </div>
                  <div id="dining-map-overlay" class="dining-map-overlay"></div>
                </div>
                <div id="dining-map-list" class="dining-map-list"></div>
              </div>
            </section>

            <section class="dining-card span-4">
              <div class="dining-card-inner">
                <div class="dining-card-header">
                  <div class="dining-card-number">4. Restaurant Details</div>
                  <h3>Everything you need to decide.</h3>
                </div>
                <div id="dining-detail-preview"></div>
              </div>
            </section>

            <section class="dining-card span-4">
              <div class="dining-card-inner">
                <div class="dining-card-header">
                  <div class="dining-card-number">5. Menu & Insights</div>
                  <h3>AI insights to enhance your experience.</h3>
                </div>
                <div id="dining-menu-insights"></div>
              </div>
            </section>

            <section class="dining-card span-4">
              <div class="dining-card-inner">
                <div class="dining-card-header">
                  <div class="dining-card-number">6. Reservation & Availability</div>
                  <h3>Book with confidence.</h3>
                </div>
                <div id="dining-reservation-panel"></div>
              </div>
            </section>
          </div>

          <div id="dining-feature-strip" class="dining-feature-strip"></div>
          <div id="dining-recent-searches" class="dining-recent-grid"></div>

          <div id="dining-favorites-panel" class="dining-hidden-panel">
            <div class="dining-card"><div class="dining-card-inner">
              <div class="dining-card-header">
                <div class="dining-card-number">Saved Favorites</div>
                <h3>Your shortlist.</h3>
              </div>
              <div id="dining-favorites-list"></div>
            </div></div>
          </div>
        </main>
      </div>
    </div>

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

  <div id="view-forge" class="view forge-view">
    <div class="forge-header">
      <div>
        <div class="forge-kicker">Desktop Experience</div>
        <div class="view-title">JARVIS FORGE<div class="view-title-line"></div></div>
        <div class="forge-subtitle">Invention to reality engine for physical objects, AI-assisted product design, manufacturing, sourcing, print readiness, and long-term part memory. One desktop screen is active at a time, with arrows and a visible page count carrying the sequence.</div>
      </div>
      <div class="forge-motto">
        <strong>Ideas become objects. Objects become reality.</strong>
        <span>Capture the world, engineer with AI, validate the design, and carry each project from prototype to production.</span>
      </div>
    </div>

    <div class="forge-stage">
      <div class="forge-desktop-shell">
        <aside class="forge-sidebar">
          <div class="forge-brand-block">
            <div class="forge-brand-mark">⚒</div>
            <div class="forge-brand-title">JARVIS</div>
            <div class="forge-brand-sub">FORGE</div>
          </div>

          <div class="forge-side-nav">
            <div class="forge-side-link active">⌂ Forge Home</div>
            <div class="forge-side-link">◉ Capture Lab</div>
            <div class="forge-side-link">✎ Design Studio</div>
            <div class="forge-side-link">⚡ Design Council</div>
            <div class="forge-side-link">⇄ Build Pipeline</div>
            <div class="forge-side-link">▣ Project Library</div>
            <div class="forge-side-link">⬢ Parts Catalog</div>
            <div class="forge-side-link">⌘ Environments</div>
            <div class="forge-side-link">⋯ Vendors & Quotes</div>
            <div class="forge-side-link">↗ Analytics</div>
            <div class="forge-side-link">⚙ Settings</div>
          </div>

          <div class="forge-sidebar-status">
            <strong>Forge Status</strong>
            <div class="forge-status-row"><span>Project</span><span id="forge-sidebar-project">No project</span></div>
            <div class="forge-status-row"><span>Signal Health</span><span id="forge-sidebar-health">Syncing…</span></div>
            <div class="forge-status-row"><span>Recent Projects</span><span id="forge-sidebar-count">0</span></div>
            <div class="forge-status-row"><span>Runtime</span><span id="forge-runtime-note">Loading Forge context…</span></div>
            <button class="forge-action-btn" type="button" onclick="refreshForgeDesktop()" style="width:100%;margin-top:8px;">Refresh Forge</button>
            <button class="forge-action-btn" type="button" onclick="forgeNewProject()" style="width:100%;margin-top:8px;">Open New Forge Project</button>
          </div>
        </aside>

        <main class="forge-main">
          <div class="forge-topbar">
            <div>
              <div class="forge-topbar-kicker">Desktop Sequence</div>
              <div class="forge-topbar-title" id="forge-nav-title">1. Capture &amp; Understand</div>
              <div class="forge-topbar-subtitle" id="forge-nav-subtitle">See the physical world, turn it into a design brief, and gather enough measurements, views, and constraints to make the project buildable.</div>
            </div>
            <div class="forge-nav">
              <button class="forge-nav-btn" id="forge-nav-prev" onclick="advanceForgePage(-1)" aria-label="Previous Forge page">←</button>
              <div class="forge-nav-status">
                <div class="forge-nav-page" id="forge-page-count">Page 1 of 7</div>
                <div class="forge-nav-title" id="forge-page-label">Capture Lab</div>
              </div>
              <button class="forge-nav-btn" id="forge-nav-next" onclick="advanceForgePage(1)" aria-label="Next Forge page">→</button>
            </div>
          </div>

          <div class="forge-process-strip">
            <div class="forge-process-pill"><span>See It.</span><strong>Capture anything.</strong><small>Photos, scans, dimensions, references.</small></div>
            <div class="forge-process-pill"><span>Design It.</span><strong>Engineer with AI.</strong><small>Turn rough intent into a real part brief.</small></div>
            <div class="forge-process-pill"><span>Validate It.</span><strong>Review every angle.</strong><small>Multi-agent critique, fit, and stress.</small></div>
            <div class="forge-process-pill"><span>Build It.</span><strong>Prototype to production.</strong><small>Print, machine, source, and quote.</small></div>
            <div class="forge-process-pill"><span>Remember It.</span><strong>Learn, improve, repeat.</strong><small>Every revision becomes part memory.</small></div>
          </div>

          <div class="forge-page-deck">
            <section class="forge-page active" data-forge-page="1">
              <div class="forge-grid-two">
                <div class="forge-card-shell">
                  <div class="forge-card-heading">
                    <div class="forge-card-label">Capture &amp; Understand<strong>See the physical world. Turn it into a design brief.</strong><small>Start with a project, then upload geometry, photos, or view captures until the brief is strong enough to build from.</small></div>
                    <span class="forge-inline-chip" id="forge-project-status" style="display:none;">IDEA</span>
                  </div>

                  <div class="forge-command-grid">
                    <div class="forge-feature-card">
                      <span>Project</span>
                      <strong id="forge-brief-title">Select a Forge project</strong>
                      <p id="forge-brief-purpose">Choose a project to load its measurements, captures, and model history.</p>
                    </div>
                    <div class="forge-feature-card">
                      <span>Strategic Priority</span>
                      <strong id="forge-brief-priority">Capture the constraints clearly</strong>
                      <p id="forge-brief-priority-copy">Every good physical project starts with enough signal to remove the guesswork before fabrication begins.</p>
                    </div>
                  </div>

                  <div class="forge-brief-grid">
                    <div class="forge-thumb-card">⚒</div>
                    <div class="forge-brief-list">
                      <div class="forge-brief-row"><span>Purpose</span><strong id="forge-brief-purpose-row">Waiting for project</strong></div>
                      <div class="forge-brief-row"><span>Environment</span><strong id="forge-brief-environment">Garage / home / workshop</strong></div>
                      <div class="forge-brief-row"><span>Load</span><strong id="forge-brief-load">Unknown</strong></div>
                      <div class="forge-brief-row"><span>Constraints</span><strong id="forge-brief-constraints">Measurements, fit, materials</strong></div>
                      <div class="forge-brief-row"><span>Material</span><strong id="forge-brief-material">PETG / ASA / Aluminum</strong></div>
                      <div class="forge-brief-row"><span>Priority</span><strong id="forge-brief-priority-row">Strength, clean fit, easy install</strong></div>
                    </div>
                  </div>

                  <div class="forge-micro-grid">
                    <div class="forge-micro-card"><span>Measurements</span><strong id="forge-metric-measurements">0</strong><small id="forge-metric-measurements-sub">No dimensions yet</small></div>
                    <div class="forge-micro-card"><span>Capture Frames</span><strong id="forge-metric-captures">0</strong><small id="forge-metric-captures-sub">Need multiple angles</small></div>
                    <div class="forge-micro-card"><span>Generated Models</span><strong id="forge-metric-models">0</strong><small id="forge-metric-models-sub">Nothing built yet</small></div>
                    <div class="forge-micro-card"><span>Confidence</span><strong id="forge-metric-confidence">—</strong><small id="forge-metric-confidence-sub">Geometry / scale / print</small></div>
                  </div>
                </div>

                <div class="forge-grid-two">
                  <div class="forge-capture-panel" id="forge-capture-panel">
                    <div class="forge-panel-title">
                      <span>Capture Status</span>
                      <button class="forge-action-btn" style="font-size:10px;padding:5px 10px;" onclick="forgeCameraCapture()">+ Frame</button>
                    </div>
                    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
                      <select id="forge-project-select" onchange="forgeLoadProject(this.value)" style="flex:1;min-width:200px;padding:10px 12px;border:1px solid rgba(255,255,255,0.10);border-radius:12px;background:rgba(255,255,255,0.04);font-size:13px;color:var(--forge-ink);cursor:pointer;">
                        <option value="">— Select a project —</option>
                      </select>
                      <button class="forge-action-btn" onclick="document.getElementById('forge-file-input').click()">Upload 3D</button>
                      <button class="forge-action-btn" onclick="document.getElementById('forge-photo-input').click()">Upload Photos</button>
                    </div>
                    <div class="forge-capture-grid" id="forge-capture-grid">
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
                    <button id="forge-build-3d-btn" class="forge-action-btn primary" style="display:none;margin-top:12px;width:100%;font-size:12px;" onclick="forgeTriggerReconstruct()">Build 3D Model</button>
                  </div>

                  <div class="forge-measurements-panel">
                    <div class="forge-panel-title">
                      <span>Measurements</span>
                      <button class="forge-action-btn" style="font-size:10px;padding:5px 10px;" onclick="forgeAddMeasurement()">+ Add</button>
                    </div>
                    <div class="forge-meas-list" id="forge-meas-list">
                      <div style="color:var(--forge-ink-faint);font-size:11px;font-family:var(--font-mono);">No measurements yet.</div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section class="forge-page" data-forge-page="2">
              <div class="forge-grid-two">
                <div class="forge-card-shell">
                  <div class="forge-card-heading">
                    <div class="forge-card-label">Design Studio<strong>Design with AI like a world-class product engineer.</strong><small>The live viewer, uploads, camera capture, and downloadable model stay active here.</small></div>
                    <button class="forge-action-btn" onclick="forgeQuickDescribe()">Describe Part</button>
                  </div>
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
                        <button class="forge-action-btn" style="font-size:11px;padding:5px 12px;" onclick="event.stopPropagation();document.getElementById('forge-photo-input').click()">Upload Photos</button>
                        <button class="forge-action-btn" style="font-size:11px;padding:5px 12px;" onclick="event.stopPropagation();forgeCameraCapture()">Camera</button>
                      </div>
                    </div>
                    <input type="file" id="forge-file-input" style="display:none" accept=".stl,.obj,.glb,.3mf" onchange="forgeUploadFile(this.files[0])">
                    <input type="file" id="forge-photo-input" style="display:none" accept="image/*" multiple onchange="forgeUploadPhotos(this.files)">
                    <input type="file" id="forge-view-capture-input" style="display:none" accept="image/*" multiple onchange="forgeHandleViewCaptureFiles(this.files, this._pendingViewType)">
                  </div>
                </div>

                <div class="forge-chat-panel">
                  <div class="forge-panel-title" style="margin-bottom:6px;">
                    <span>JARVIS Forge</span>
                    <button class="forge-action-btn" style="font-size:10px;padding:5px 10px;" onclick="document.getElementById('forge-sketch-input').click()">Upload Sketch</button>
                  </div>
                  <div id="forge-chat-messages">
                    <div class="forge-msg-jarvis">Select a project to begin. Describe a part to generate it, upload a sketch to analyze it, or use Design Council for a full agent roundtable.</div>
                  </div>
                  <div class="forge-chat-input">
                    <input type="text" id="forge-chat-input" placeholder="Describe a part or ask Forge anything..." onkeydown="if(event.key==='Enter')forgeSendChat()">
                    <button class="forge-action-btn primary" onclick="forgeSendChat()">Send</button>
                  </div>
                  <div style="display:flex;align-items:center;gap:8px;margin-top:8px;flex-wrap:wrap;">
                    <span style="font-size:10px;color:var(--forge-ink-faint);font-weight:600;letter-spacing:0.05em;">SKETCH</span>
                    <input type="file" id="forge-sketch-input" accept="image/*" style="display:none;" onchange="forgeHandleSketchUpload(this)">
                    <button class="forge-action-btn" style="font-size:10px;padding:5px 10px;" onclick="document.getElementById('forge-sketch-input').click()">Upload Drawing</button>
                    <span id="forge-sketch-status" style="font-size:10px;color:var(--forge-ink-faint);font-family:var(--font-mono);"></span>
                  </div>
                  <div class="forge-project-strip" style="margin-top:14px;">
                    <div class="forge-project-chip"><strong>Option A — Strongest</strong><span id="forge-option-a-copy">Strength-first design direction with practical geometry.</span></div>
                    <div class="forge-project-chip"><strong>Option B — Fastest</strong><span id="forge-option-b-copy">Fastest to print and easiest to iterate in-house.</span></div>
                    <div class="forge-project-chip"><strong>Option C — Cleanest</strong><span id="forge-option-c-copy">Clean cable management and the clearest install path.</span></div>
                    <div class="forge-project-chip"><strong>Option D — Adjustable</strong><span id="forge-option-d-copy">Flexible mounting logic for multiple environments.</span></div>
                  </div>
                </div>
              </div>
            </section>

            <section class="forge-page" data-forge-page="3">
              <div class="forge-grid-two">
                <div class="forge-card-shell">
                  <div class="forge-card-heading">
                    <div class="forge-card-label">Design Council<strong>Multi-agent review. Every angle considered.</strong><small>Run the council, compare options, and watch the part move from rough idea to defended design direction.</small></div>
                    <button class="forge-action-btn primary" onclick="forgeRunDesignCouncil()">See Full Council Report</button>
                  </div>
                  <div class="forge-score-list">
                    <div class="forge-score-row"><span id="forge-score-a-label">Option A</span><div class="forge-score-track"><div class="forge-score-fill" id="forge-score-a-fill" style="width:92%;"></div></div><strong class="forge-score-value" id="forge-score-a-value">92</strong></div>
                    <div class="forge-score-row"><span id="forge-score-b-label">Option B</span><div class="forge-score-track"><div class="forge-score-fill" id="forge-score-b-fill" style="width:87%;"></div></div><strong class="forge-score-value" id="forge-score-b-value">87</strong></div>
                    <div class="forge-score-row"><span id="forge-score-c-label">Option C</span><div class="forge-score-track"><div class="forge-score-fill" id="forge-score-c-fill" style="width:89%;"></div></div><strong class="forge-score-value" id="forge-score-c-value">89</strong></div>
                    <div class="forge-score-row"><span id="forge-score-d-label">Option D</span><div class="forge-score-track"><div class="forge-score-fill" id="forge-score-d-fill" style="width:84%;"></div></div><strong class="forge-score-value" id="forge-score-d-value">84</strong></div>
                  </div>
                  <div class="forge-factor-list" id="forge-factor-list">
                    <div>Load capacity</div>
                    <div>Installation method</div>
                    <div>Failure points</div>
                    <div>Environment</div>
                    <div>Print orientation</div>
                    <div>Tolerances</div>
                    <div>Material performance</div>
                    <div>Cost to produce</div>
                  </div>
                </div>
                <div class="forge-card-shell">
                  <div class="forge-card-heading">
                    <div class="forge-card-label">Stress Analysis<strong>How the current concept is holding up</strong><small id="forge-stress-copy-top">Use the Council when you want the review to feed directly into model generation.</small></div>
                  </div>
                  <div class="forge-stress-panel">
                    <div class="forge-stress-copy" id="forge-stress-copy">Current model, if present, becomes the working artifact the council reasons about. Load, fit, and install logic all push the recommendation.</div>
                  </div>
                </div>
              </div>
            </section>

            <section class="forge-page" data-forge-page="4">
              <div class="forge-card-shell">
                <div class="forge-card-heading">
                  <div class="forge-card-label">Build Pipeline<strong>From CAD to machine-ready. Optimized for success.</strong><small>Inspect the current model, stage the slice, and decide whether this project is ready to move forward.</small></div>
                </div>
                <div class="forge-pipeline-row">
                  <div class="forge-pipeline-stage"><span>CAD</span><strong id="forge-stage-cad">Captured</strong></div>
                  <div class="forge-pipeline-stage"><span>Mesh Repair</span><strong id="forge-stage-repair">Validate</strong></div>
                  <div class="forge-pipeline-stage"><span>Optimize</span><strong id="forge-stage-optimize">Refine</strong></div>
                  <div class="forge-pipeline-stage"><span>Slice &amp; Sim</span><strong id="forge-stage-slice">Stage</strong></div>
                  <div class="forge-pipeline-stage"><span>Validate</span><strong id="forge-stage-validate">Inspect</strong></div>
                  <div class="forge-pipeline-stage"><span>Package</span><strong id="forge-stage-package">Approve</strong></div>
                </div>
                <div class="forge-detail-grid">
                  <div class="forge-readiness-panel">
                    <div class="forge-panel-title">
                      <span>Print Readiness</span>
                      <button class="forge-action-btn" style="font-size:10px;padding:5px 10px;" onclick="forgeInspectActive()">Inspect</button>
                    </div>
                    <div class="forge-readiness-list" id="forge-readiness-list">
                      <div style="color:var(--forge-ink-faint);font-size:11px;font-family:var(--font-mono);">No inspection yet. Upload a model and click Inspect.</div>
                    </div>
                    <div id="forge-readiness-verdict" style="margin-top:8px;font-size:12px;font-weight:600;color:var(--forge-ink-faint);font-family:var(--font-mono);">VERDICT: —</div>
                    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;">
                      <button class="forge-action-btn" onclick="forgeStageSlice()">Stage Slice</button>
                      <button class="forge-action-btn primary" onclick="forgeApprove()">Approve &amp; Send</button>
                      <button class="forge-action-btn" onclick="forgeShowTimeline()">View Timeline</button>
                    </div>
                  </div>
                  <div class="forge-card-shell">
                    <div class="forge-card-heading">
                      <div class="forge-card-label">Printer &amp; Machine Posture<strong>Current output lane</strong></div>
                    </div>
                    <div id="forge-printer-status-row" style="display:block;margin-bottom:12px;">
                      <span class="forge-printer-chip" id="forge-printer-chip">K2 Pro — checking...</span>
                    </div>
                    <div class="forge-spec-list">
                      <div class="forge-spec-row"><strong style="display:block;color:var(--forge-ink);font-size:13px;">Printer Setup</strong><span id="forge-printer-setup">Waiting for active model and slice report.</span></div>
                      <div class="forge-spec-row"><strong style="display:block;color:var(--forge-ink);font-size:13px;">Material</strong><span id="forge-material-posture">PETG for durability, ASA when heat and weather matter, aluminum when production economics justify it.</span></div>
                      <div class="forge-spec-row"><strong style="display:block;color:var(--forge-ink);font-size:13px;">Success Probability</strong><span id="forge-success-probability">Clear constraints and enough capture data keep the reprint loop small.</span></div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section class="forge-page" data-forge-page="5">
              <div class="forge-grid-two">
                <div class="forge-card-shell">
                  <div class="forge-card-heading">
                    <div class="forge-card-label">Project &amp; Part Memory<strong>Every project. Every revision. Every lesson learned.</strong><small>The timeline, model history, and capture trail stay attached to the project so the next version starts smarter.</small></div>
                  </div>
                  <div class="forge-memory-list" id="forge-memory-list">
                    <div class="forge-memory-row"><strong>No revisions yet</strong><span>Once a project starts generating captures, models, and inspections, they will appear here.</span></div>
                  </div>
                </div>
                <div class="forge-card-shell">
                  <div class="forge-card-heading">
                    <div class="forge-card-label">What We Learned<strong>Carry the lessons forward</strong></div>
                    <button class="forge-action-btn" onclick="forgeShowTimeline()">Open Timeline</button>
                  </div>
                  <div class="forge-learn-list" id="forge-learning-list">
                    <div class="forge-memory-row"><strong>Wait for active project</strong><span>Measurements, council outputs, repairs, and approvals will summarize here once the project is loaded.</span></div>
                  </div>
                </div>
              </div>
            </section>

            <section class="forge-page" data-forge-page="6">
              <div class="forge-grid-two">
                <div class="forge-card-shell">
                  <div class="forge-card-heading">
                    <div class="forge-card-label">Manufacture &amp; Sourcing<strong>Make it here. Make it anywhere. Scale if you want.</strong><small>Compare in-house print, machining, or quote pathways without losing the project context.</small></div>
                  </div>
                  <div class="forge-factory-tabs">
                    <div class="forge-factory-tab active">In-House</div>
                    <div class="forge-factory-tab">Local Makers</div>
                    <div class="forge-factory-tab">CNC / Laser</div>
                    <div class="forge-factory-tab">Injection Molding</div>
                    <div class="forge-factory-tab">Casting</div>
                  </div>
                  <div class="forge-estimate-list" id="forge-manufacture-plan">
                    <div class="forge-estimate-row"><strong style="display:block;color:var(--forge-ink);font-size:13px;">3D Print Prototype</strong><span>Use the current project brief to compare speed, cost, and risk before committing the design downstream.</span></div>
                    <div class="forge-estimate-row"><strong style="display:block;color:var(--forge-ink);font-size:13px;">Field Test</strong><span>Validate fit, real load, environmental exposure, and failure points before production scaling.</span></div>
                    <div class="forge-estimate-row"><strong style="display:block;color:var(--forge-ink);font-size:13px;">Finalize Design</strong><span>Repair, rescale, and convert tools stay attached so the artifact can cross fabrication methods cleanly.</span></div>
                  </div>
                </div>
                <div class="forge-card-shell">
                  <div class="forge-card-heading">
                    <div class="forge-card-label">Production Estimate<strong>Compare the output lanes</strong></div>
                  </div>
                  <div class="forge-estimate-list" id="forge-estimate-list">
                    <div class="forge-estimate-row"><strong style="display:block;color:var(--forge-ink);font-size:13px;">3D Print (In-House)</strong><span>Fastest path to prototype and a tight feedback loop for fit adjustments.</span></div>
                    <div class="forge-estimate-row"><strong style="display:block;color:var(--forge-ink);font-size:13px;">CNC Machining</strong><span>Higher precision and material durability when the geometry and volumes warrant it.</span></div>
                    <div class="forge-estimate-row"><strong style="display:block;color:var(--forge-ink);font-size:13px;">Batch Production</strong><span>Use once the design is stable and the cost curve justifies a wider run.</span></div>
                  </div>
                  <button class="forge-action-btn primary" style="margin-top:14px;width:100%;" onclick="forgeStageSlice()">Request Quotes</button>
                </div>
              </div>
            </section>

            <section class="forge-page" data-forge-page="7">
              <div class="forge-card-shell" style="margin-bottom:16px;">
                <div class="forge-card-heading">
                  <div class="forge-card-label">Environments &amp; Systems Design<strong>Design whole spaces, systems, and better ways of living.</strong><small>Forge is not only for one part. It is the physical systems layer for your garage, home, office, rigs, storage, and maker environment.</small></div>
                </div>
                <div class="forge-environment-row" id="forge-environment-row">
                  <div class="forge-environment-card"><strong>Garage Systems</strong><span>Mounts, charging, tools, and storage that reduce daily friction.</span></div>
                  <div class="forge-environment-card"><strong>Home Organization</strong><span>Physical products that tidy, protect, and improve movement.</span></div>
                  <div class="forge-environment-card"><strong>Office &amp; Workspaces</strong><span>Printer stands, cable paths, desks, and production rigs.</span></div>
                  <div class="forge-environment-card"><strong>Family Command</strong><span>Support the household with systems that actually get used.</span></div>
                  <div class="forge-environment-card"><strong>Creator Rigs</strong><span>Camera handles, shelves, docks, and modular setups.</span></div>
                  <div class="forge-environment-card"><strong>Mobile &amp; Vehicle</strong><span>Travel adapters, mounts, and in-motion utility pieces.</span></div>
                </div>
              </div>

              <div class="forge-grid-two">
                <div class="forge-card-shell">
                  <div class="forge-card-heading">
                    <div class="forge-card-label">Recent Projects<strong>What Forge has in memory</strong></div>
                    <button class="forge-action-btn" onclick="forgeNewProject()">+ New Project</button>
                  </div>
                  <div class="forge-project-strip" id="forge-recent-projects">
                    <div class="forge-project-chip"><strong>No Forge projects yet</strong><span>Create one to begin the object-to-reality pipeline.</span></div>
                  </div>
                </div>

                <div class="forge-grid-two">
                  <div class="forge-measurements-panel" id="forge-wow-panel">
                    <div class="forge-panel-title" style="cursor:pointer;" onclick="forgeWowToggle()">
                      <span>WoW Model Bridge</span>
                      <span id="forge-wow-count" style="font-size:10px;color:var(--forge-ink-faint);font-family:var(--font-mono);margin-left:6px;"></span>
                      <button class="forge-action-btn" style="font-size:10px;padding:5px 10px;margin-left:auto;" onclick="event.stopPropagation();forgeWowRefresh()">Refresh</button>
                    </div>
                    <div id="forge-wow-body" style="display:none;margin-top:6px;">
                      <div id="forge-wow-status-row" style="font-size:10px;font-family:var(--font-mono);color:var(--forge-ink-faint);margin-bottom:8px;line-height:1.6;"></div>
                      <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;">
                        <input type="text" id="forge-wow-search" placeholder="Search models..." style="flex:1;min-width:100px;padding:8px 10px;border:1px solid rgba(255,255,255,0.10);border-radius:10px;background:rgba(255,255,255,0.04);color:var(--forge-ink);font-size:11px;outline:none;" oninput="forgeWowSearch(this.value)">
                        <button class="forge-action-btn" style="font-size:10px;padding:5px 10px;" onclick="forgeWowOpenSetup()">Setup</button>
                      </div>
                      <div id="forge-wow-model-list" style="max-height:180px;overflow-y:auto;display:flex;flex-direction:column;gap:4px;">
                        <div style="color:var(--forge-ink-faint);font-size:11px;font-family:var(--font-mono);">Click Refresh to scan export folder.</div>
                      </div>
                    </div>
                  </div>

                  <div class="forge-measurements-panel" id="forge-convert-panel">
                    <div class="forge-panel-title" style="cursor:pointer;" onclick="forgeConvertToggle()">
                      <span>Convert Tools</span>
                      <button class="forge-action-btn" style="font-size:10px;padding:5px 10px;margin-left:auto;" onclick="event.stopPropagation();forgeConvertToggle()">▾</button>
                    </div>
                    <div id="forge-convert-body" style="display:none;margin-top:8px;">
                      <div style="margin-bottom:12px;">
                        <div style="font-size:10px;font-weight:700;color:var(--forge-ink-soft);text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px;">Format Converter</div>
                        <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:6px;">
                          <select id="forge-conv-src-file" style="flex:1;min-width:120px;padding:8px 10px;border:1px solid rgba(255,255,255,0.10);border-radius:10px;background:rgba(255,255,255,0.04);color:var(--forge-ink);font-size:11px;outline:none;">
                            <option value="">— pick project file —</option>
                          </select>
                          <select id="forge-conv-fmt" style="width:74px;padding:8px 8px;border:1px solid rgba(255,255,255,0.10);border-radius:10px;background:rgba(255,255,255,0.04);color:var(--forge-ink);font-size:11px;outline:none;">
                            <option value="glb">GLB</option>
                            <option value="obj">OBJ</option>
                            <option value="stl">STL</option>
                            <option value="ply">PLY</option>
                          </select>
                          <button class="forge-action-btn" style="font-size:10px;padding:6px 10px;" onclick="forgeConvertFormat()">Convert</button>
                        </div>
                        <div style="font-size:10px;color:var(--forge-ink-faint);margin-bottom:4px;">or upload a file to convert:</div>
                        <input type="file" id="forge-conv-upload-input" accept=".stl,.obj,.glb,.ply" style="display:none;" onchange="forgeConvertFormatFromUpload(this)">
                        <button class="forge-action-btn" style="font-size:10px;padding:6px 10px;width:100%;" onclick="document.getElementById('forge-conv-upload-input').click()">Upload &amp; Convert</button>
                      </div>

                      <div style="margin-bottom:12px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.07);">
                        <div style="font-size:10px;font-weight:700;color:var(--forge-ink-soft);text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px;">WoW Tools</div>
                        <div style="display:flex;gap:6px;flex-wrap:wrap;">
                          <a href="https://github.com/Kruithne/wow.export/releases/latest" target="_blank" class="forge-action-btn" style="font-size:10px;padding:6px 10px;text-decoration:none;">Download wow.export</a>
                          <button class="forge-action-btn" style="font-size:10px;padding:6px 10px;" onclick="forgeConvertCheckBlender()">Check Blender Setup</button>
                        </div>
                        <div id="forge-conv-blender-result" style="font-size:10px;font-family:var(--font-mono);color:var(--forge-ink-faint);margin-top:6px;line-height:1.6;display:none;"></div>
                      </div>

                      <div style="margin-bottom:12px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.07);">
                        <div style="font-size:10px;font-weight:700;color:var(--forge-ink-soft);text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px;">Mesh Repair</div>
                        <select id="forge-repair-src-file" style="width:100%;padding:8px 10px;border:1px solid rgba(255,255,255,0.10);border-radius:10px;background:rgba(255,255,255,0.04);color:var(--forge-ink);font-size:11px;outline:none;margin-bottom:6px;">
                          <option value="">— pick project file —</option>
                        </select>
                        <div style="display:flex;gap:10px;margin-bottom:8px;flex-wrap:wrap;">
                          <label style="font-size:10px;color:var(--forge-ink-soft);display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="checkbox" id="forge-repair-normals" checked> Fix Normals</label>
                          <label style="font-size:10px;color:var(--forge-ink-soft);display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="checkbox" id="forge-repair-holes" checked> Fill Holes</label>
                          <label style="font-size:10px;color:var(--forge-ink-soft);display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="checkbox" id="forge-repair-winding" checked> Fix Winding</label>
                        </div>
                        <button class="forge-action-btn primary" style="font-size:10px;padding:6px 12px;" onclick="forgeConvertRepair()">Repair Mesh</button>
                        <div id="forge-conv-repair-result" style="font-size:10px;font-family:var(--font-mono);color:var(--forge-ink-faint);margin-top:6px;line-height:1.6;display:none;"></div>
                      </div>

                      <div style="padding-top:10px;border-top:1px solid rgba(255,255,255,0.07);">
                        <div style="font-size:10px;font-weight:700;color:var(--forge-ink-soft);text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px;">Scale &amp; Units</div>
                        <select id="forge-scale-src-file" style="width:100%;padding:8px 10px;border:1px solid rgba(255,255,255,0.10);border-radius:10px;background:rgba(255,255,255,0.04);color:var(--forge-ink);font-size:11px;outline:none;margin-bottom:6px;">
                          <option value="">— pick project file —</option>
                        </select>
                        <select id="forge-scale-op" style="width:100%;padding:8px 10px;border:1px solid rgba(255,255,255,0.10);border-radius:10px;background:rgba(255,255,255,0.04);color:var(--forge-ink);font-size:11px;outline:none;margin-bottom:6px;" onchange="forgeConvertScaleOpChange(this.value)">
                          <option value="rescale">Rescale to target size</option>
                          <option value="normalize_bbox">Normalize bounding box (unit cube)</option>
                          <option value="center_origin">Center on origin</option>
                        </select>
                        <div id="forge-scale-rescale-opts" style="display:flex;gap:6px;margin-bottom:6px;flex-wrap:wrap;align-items:center;">
                          <input type="number" id="forge-scale-target-size" value="100" min="0.001" step="0.1" style="width:80px;padding:8px 10px;border:1px solid rgba(255,255,255,0.10);border-radius:10px;background:rgba(255,255,255,0.04);color:var(--forge-ink);font-size:11px;outline:none;">
                          <select id="forge-scale-target-unit" style="width:64px;padding:8px 8px;border:1px solid rgba(255,255,255,0.10);border-radius:10px;background:rgba(255,255,255,0.04);color:var(--forge-ink);font-size:11px;outline:none;">
                            <option value="mm">mm</option>
                            <option value="cm">cm</option>
                            <option value="in">in</option>
                            <option value="m">m</option>
                          </select>
                          <span style="font-size:10px;color:var(--forge-ink-faint);">src:</span>
                          <select id="forge-scale-current-unit" style="width:64px;padding:8px 8px;border:1px solid rgba(255,255,255,0.10);border-radius:10px;background:rgba(255,255,255,0.04);color:var(--forge-ink);font-size:11px;outline:none;">
                            <option value="mm">mm</option>
                            <option value="cm">cm</option>
                            <option value="in">in</option>
                            <option value="m">m</option>
                          </select>
                        </div>
                        <button class="forge-action-btn primary" style="font-size:10px;padding:6px 12px;" onclick="forgeConvertScale()">Apply Scale</button>
                        <div id="forge-conv-scale-result" style="font-size:10px;font-family:var(--font-mono);color:var(--forge-ink-faint);margin-top:6px;line-height:1.6;display:none;"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <div class="forge-footer-strip">
            <div class="forge-footer-pill"><strong>Reality Capture</strong><span>See everything. Preserve the details that matter.</span></div>
            <div class="forge-footer-pill"><strong>AI Engineering</strong><span>Design without limits, but keep the constraints honest.</span></div>
            <div class="forge-footer-pill"><strong>Design Council</strong><span>Review from multiple angles before you fabricate.</span></div>
            <div class="forge-footer-pill"><strong>Build Anywhere</strong><span>From print prototype to production run.</span></div>
            <div class="forge-footer-pill"><strong>Memory Engine</strong><span>Learn, improve, repeat across every revision.</span></div>
            <div class="forge-footer-pill"><strong>From One to Many</strong><span>Personal use can become a product line.</span></div>
            <div class="forge-footer-pill"><strong>Secure &amp; Private</strong><span>Your data. Your designs. Your manufacturing signal.</span></div>
          </div>

          <div class="forge-action-bar">
            <button class="forge-action-btn" style="background:linear-gradient(135deg,#7c3aed22,#06b6d422);border-color:#7c3aed66;color:var(--forge-amber);" onclick="forgeRunDesignCouncil()">⚡ Design Council</button>
            <button class="forge-action-btn" onclick="forgeStageSlice()">Stage Slice</button>
            <button class="forge-action-btn primary" onclick="forgeApprove()">Approve &amp; Send</button>
            <button class="forge-action-btn" onclick="forgeShowTimeline()">View Timeline</button>
            <button class="forge-action-btn" onclick="forgeArchive()">Archive</button>
            <span class="forge-printer-chip" id="forge-printer-chip-bar" style="display:none;margin-left:auto;">K2 Pro —</span>
          </div>

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

          <div id="forge-wow-setup-modal" class="forge-modal-overlay hidden">
            <div class="forge-modal" style="max-width:480px;">
              <div class="forge-modal-title">⚔️ WoW Model Bridge Setup</div>
              <div style="font-size:11px;color:var(--text-3);margin-bottom:14px;line-height:1.7;">
                <b>Step 1</b> — Download <a href="https://github.com/Kruithne/wow.export/releases/latest" target="_blank" style="color:var(--hue);">wow.export</a> (free, macOS ARM64 native)<br>
                <b>Step 2</b> — Open it, connect to your WoW install, search your character/model<br>
                <b>Step 3</b> — Export as GLB — files land in your export folder<br>
                <b>Step 4</b> — Hit Refresh in Forge and click Import next to the model
              </div>
              <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:14px;">
                <label style="font-size:11px;color:var(--text-2);font-weight:600;">Export Folder (where wow.export saves files)</label>
                <input type="text" id="forge-wow-cfg-folder" style="padding:6px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-hi);color:var(--text-1);font-size:11px;font-family:var(--font-mono);outline:none;width:100%;box-sizing:border-box;">
                <label style="font-size:11px;color:var(--text-2);font-weight:600;">WoW Install Path</label>
                <input type="text" id="forge-wow-cfg-wow" style="padding:6px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-hi);color:var(--text-1);font-size:11px;font-family:var(--font-mono);outline:none;width:100%;box-sizing:border-box;">
                <label style="font-size:11px;color:var(--text-2);font-weight:600;">Blender Path (optional — for M2→GLB conversion)</label>
                <input type="text" id="forge-wow-cfg-blender" style="padding:6px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-hi);color:var(--text-1);font-size:11px;font-family:var(--font-mono);outline:none;width:100%;box-sizing:border-box;">
              </div>
              <div style="display:flex;gap:8px;">
                <button class="forge-action-btn primary" onclick="forgeWowSaveConfig()">Save</button>
                <button class="forge-action-btn" onclick="document.getElementById('forge-wow-setup-modal').classList.add('hidden')">Cancel</button>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  </div>

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
  <div id="view-vision" class="view vision-view">
    <div class="vision-header">
      <div class="vision-brand">
        <div class="vision-brand-mark">
          <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
            <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6Z"></path>
            <circle cx="12" cy="12" r="3.2"></circle>
            <path d="M12 2v3M4.9 4.9l2.1 2.1M2 12h3M4.9 19.1 7 17M12 19v3M17 17l2.1 2.1M19 12h3M17 7l2.1-2.1"></path>
          </svg>
        </div>
        <div class="vision-brand-copy">
          <div class="vision-kicker">Visual Intelligence & Context Engine</div>
          <div class="vision-title">JARVIS <span>VISION</span></div>
          <div class="vision-subtitle">See clearly. Understand deeply. Act wisely.</div>
          <div class="vision-brand-detail">JARVIS sees what matters so you can focus on what counts.</div>
        </div>
      </div>

      <div class="vision-header-right">
        <div class="vision-header-stats">
          <div class="vision-stat-shell">
            <div class="vision-stat-label">Vision Status</div>
            <div class="vision-stat-value" id="vision-status-value">Active</div>
            <div class="vision-stat-sub" id="vision-status-sub">Continuously observing</div>
          </div>
          <div class="vision-stat-shell">
            <div class="vision-stat-label">Confidence Level</div>
            <div class="vision-stat-value" id="vision-confidence-score">92%</div>
            <div class="vision-stat-sub" id="vision-confidence-sub">High</div>
          </div>
          <div class="vision-stat-shell">
            <div class="vision-stat-label">Scenes Today</div>
            <div class="vision-stat-value" id="vision-scenes-today">0</div>
            <div class="vision-stat-sub" id="vision-scenes-sub">Fresh observations</div>
          </div>
          <div class="vision-stat-shell">
            <div class="vision-stat-label">Changes Detected</div>
            <div class="vision-stat-value" id="vision-changes-count">0</div>
            <div class="vision-stat-sub" id="vision-changes-sub">New differences found</div>
          </div>
          <div class="vision-stat-shell">
            <div class="vision-stat-label">Insights Generated</div>
            <div class="vision-stat-value" id="vision-insights-count">0</div>
            <div class="vision-stat-sub" id="vision-insights-sub">Routed to your systems</div>
          </div>
          <div class="vision-stat-shell">
            <div class="vision-stat-label">Memory Index</div>
            <div class="vision-stat-value" id="vision-memory-count">0</div>
            <div class="vision-stat-sub" id="vision-memory-sub">Visual memories</div>
          </div>
        </div>
        <div class="vision-quote">
          <div class="vision-quote-mark">“</div>
          <div>
            <strong>JARVIS sees what matters so you can focus on what counts.</strong>
            <span>Visual intelligence becomes context, memory, and better action across home, workshop, family, and work.</span>
          </div>
        </div>
      </div>

      <div class="vision-profile">
        <div class="vision-profile-meta">
          <div class="vision-profile-avatar">CB</div>
          <div>
            <strong>Chris Binion</strong>
            <span>Executive Mode</span>
          </div>
        </div>
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;justify-content:flex-end;">
          <span id="vision-runtime-note" style="font-size:12px;color:rgba(255,255,255,0.74);">Vision is live and connected.</span>
          <button class="vision-header-action" type="button" id="vision-refresh-button" onclick="refreshVisionDesktop()">Refresh Vision</button>
          <button class="vision-header-action" type="button" id="vision-privacy-button" onclick="visionApplyPrivacyToggle()">Pause Vision</button>
        </div>
        <span id="vision-generated-at">Updated just now</span>
      </div>
    </div>

    <div class="vision-shell">
      <aside class="vision-input-sidebar">
        <div class="vision-side-title">Vision Inputs</div>
        <div class="vision-side-list" id="vision-inputs-list"></div>
        <button class="vision-side-cta" onclick="visionOpenRoute('/settings-center', 'home', 'Open Vision Settings', 'Review privacy, connectors, and profile defaults that shape Vision.')">Vision Settings →</button>
      </aside>

      <div class="vision-grid">
        <section class="vision-card vision-span-5">
          <div class="vision-card-inner">
            <div class="vision-card-header">
              <div>
                <div class="vision-card-number">1. Live Scene Overview</div>
                <h3>What JARVIS is seeing right now.</h3>
                <p>Live scene context from recent captures, observations, and the last camera moments that matter.</p>
              </div>
            </div>
            <div class="vision-scene-stage">
              <div class="vision-scene-overlay">
                <div class="vision-scene-copy">
                  <div class="vision-scene-chip" id="vision-live-chip">Office · Live</div>
                  <strong id="vision-live-title">Awaiting scene</strong>
                  <span id="vision-live-copy">No current observation yet.</span>
                </div>
                <div class="vision-scene-chip" id="vision-live-time">Updated —</div>
              </div>
            </div>
            <div class="vision-thumb-row" id="vision-scene-thumbs"></div>
            <button class="vision-section-link" onclick="visionOpenRoute('/activity-center', 'journey', 'View All Scenes', 'Review the live continuity lane behind recent visual scenes.')" style="margin-top:14px;">View all scenes →</button>
          </div>
        </section>

        <section class="vision-card vision-span-4">
          <div class="vision-card-inner">
            <div class="vision-card-header">
              <div>
                <div class="vision-card-number">2. What JARVIS Noticed</div>
                <h3>Key observations and insights from what I see.</h3>
              </div>
              <button class="vision-header-action" onclick="refreshVisionDesktop()">Refresh</button>
            </div>
            <div class="vision-doc-list" id="vision-feed"></div>
          </div>
        </section>

        <section class="vision-card vision-span-3">
          <div class="vision-card-inner">
            <div class="vision-card-header">
              <div>
                <div class="vision-card-number">3. Change Detection</div>
                <h3>What has changed since last seen.</h3>
              </div>
              <button class="vision-header-action" onclick="visionOpenRoute('/activity-center', 'journey', 'View Vision Timeline', 'Inspect recent visual changes inside the shared activity timeline.')">View Timeline</button>
            </div>
            <div class="vision-change-grid" id="vision-changes-list"></div>
          </div>
        </section>

        <section class="vision-card vision-span-4">
          <div class="vision-card-inner">
            <div class="vision-card-header">
              <div>
                <div class="vision-card-number">4. Text & Document Intelligence</div>
                <h3>Extracted and interpreted from what I see.</h3>
              </div>
            </div>
            <div class="vision-doc-list" id="vision-docs-list"></div>
            <button class="vision-section-link" onclick="visionOpenRoute('/publish', 'publishing', 'Open Publishing', 'Review extracted text and document-adjacent visual context inside Publishing.')" style="margin-top:14px;">View all documents →</button>
          </div>
        </section>

        <section class="vision-card vision-span-4">
          <div class="vision-card-inner">
            <div class="vision-card-header">
              <div>
                <div class="vision-card-number">5. Memory Through Vision</div>
                <h3>Visual memories that build our shared understanding.</h3>
              </div>
            </div>
            <div class="vision-memory-grid" id="vision-memory-grid"></div>
            <button class="vision-section-link" onclick="visionOpenRoute('/chronicle-center', 'journey', 'Open Visual Memories', 'Inspect saved visual memories through Chronicle continuity.')" style="margin-top:14px;">Browse all visual memories →</button>
          </div>
        </section>

        <section class="vision-card vision-span-4">
          <div class="vision-card-inner">
            <div class="vision-card-header">
              <div>
                <div class="vision-card-number">6. Vision To Action Routing</div>
                <h3>How what I see connects to your systems.</h3>
              </div>
            </div>
            <div class="vision-route-list" id="vision-route-list"></div>
            <button class="vision-section-link" onclick="visionOpenRoute('/activity-center', 'command', 'Open Routed Items', 'Review the live downstream actions created from visual observations.')" style="margin-top:14px;">View all routed items →</button>
          </div>
        </section>

        <section class="vision-card vision-span-4">
          <div class="vision-card-inner">
            <div class="vision-card-header">
              <div>
                <div class="vision-card-number">7. Insight Categories</div>
                <h3>What JARVIS is learning to see better.</h3>
              </div>
            </div>
            <div class="vision-categories-grid" id="vision-categories-grid"></div>
            <button class="vision-section-link" onclick="visionOpenRoute('/agent-ops-center', 'agents', 'Open Analytics Dashboard', 'Inspect the live agent and analytics posture behind Vision categories.')" style="margin-top:14px;">View analytics dashboard →</button>
          </div>
        </section>

        <section class="vision-card vision-span-3">
          <div class="vision-card-inner">
            <div class="vision-card-header">
              <div>
                <div class="vision-card-number">8. Anomalies & Alerts</div>
                <h3>What looks unusual or needs attention.</h3>
              </div>
            </div>
            <div class="vision-alert-list" id="vision-alerts"></div>
            <button class="vision-section-link" onclick="visionOpenRoute('/health-center', 'health', 'Open Vision Alerts', 'Review health and anomaly alerts surfaced by Vision.')" style="margin-top:14px;">View all alerts →</button>
          </div>
        </section>

        <section class="vision-card vision-span-4">
          <div class="vision-card-inner">
            <div class="vision-card-header">
              <div>
                <div class="vision-card-number">9. Vision Input Center</div>
                <h3>Capture from anywhere. Understand everything.</h3>
              </div>
            </div>
            <div class="vision-quick-grid" id="vision-input-center"></div>
            <button class="vision-section-link" onclick="visionOpenRoute('/activity-center', 'chat', 'Open Capture Tools', 'Continue the capture and interpretation flow from a live Vision observation.')" style="margin-top:14px;">Open capture tools →</button>
          </div>
        </section>

        <section class="vision-card vision-span-4">
          <div class="vision-card-inner">
            <div class="vision-card-header">
              <div>
                <div class="vision-card-number">10. Pattern Recognition</div>
                <h3>Recurring visual patterns JARVIS has learned.</h3>
              </div>
            </div>
            <div class="vision-pattern-list" id="vision-pattern-list"></div>
            <button class="vision-section-link" onclick="visionOpenRoute('/activity-center', 'journey', 'Open Vision Patterns', 'Review recurring visual patterns in the shared continuity lane.')" style="margin-top:14px;">View all patterns →</button>
          </div>
        </section>

        <section class="vision-card vision-span-4">
          <div class="vision-card-inner">
            <div class="vision-card-header">
              <div>
                <div class="vision-card-number">11. Vision Health & Confidence</div>
                <h3>How well JARVIS sees and interprets.</h3>
              </div>
            </div>
            <div class="vision-health-grid" id="vision-health-grid"></div>
            <button class="vision-section-link" onclick="visionOpenRoute('/health-center', 'health', 'Open Improvement Plan', 'Review the live confidence and improvement posture behind Vision health.')" style="margin-top:14px;">View improvement plan →</button>
          </div>
        </section>

        <section class="vision-card vision-span-4">
          <div class="vision-card-inner">
            <div class="vision-card-header">
              <div>
                <div class="vision-card-number">12. Quick Vision Actions</div>
                <h3>Common actions from what I see.</h3>
              </div>
            </div>
            <div class="vision-action-list" id="vision-actions-list"></div>
          </div>
        </section>

        <section class="vision-footer-strip" id="vision-footer-strip"></section>
      </div>
    </div>
  </div>

  <!-- ── CATALYST / WORK INTELLIGENCE ───────────────────────── -->
  <div id="view-catalyst" class="view catalyst-view" data-domain="catalyst">
    <div class="catalyst-header">
      <div>
        <div class="catalyst-kicker">Desktop Experience</div>
        <div class="view-title">CATALYST<div class="view-title-line"></div></div>
        <div class="catalyst-subtitle" id="catalyst-subtitle">A real desktop execution workspace for workflow design, live agent orchestration, governed approval flow, and voice-led intervention. One screen is active at a time, with arrows and a page count guiding the board.</div>
      </div>
      <div class="catalyst-motto">
        <div class="catalyst-motto-mark">✦</div>
        <div>
          <strong>Intelligence becomes execution.</strong>
          <span>JARVIS orchestrates the work that moves your world.</span>
        </div>
      </div>
    </div>

    <div class="catalyst-desktop-stage">
      <div class="catalyst-desktop-shell">
        <aside class="catalyst-sidebar">
          <div class="catalyst-sidebar-top">
            <div class="catalyst-sidebar-brand">
              <strong>JARVIS</strong>
              <span>Catalyst</span>
            </div>
            <div class="catalyst-sidebar-mark">✦</div>
          </div>
          <div class="catalyst-sidebar-nav">
            <div class="catalyst-sidebar-item active" data-wi-tab="overview" onclick="switchWITab(this, 'overview')">⌂ Command Center</div>
            <div class="catalyst-sidebar-item" data-wi-tab="projects" onclick="switchWITab(this, 'projects')">⌘ Workflows</div>
            <div class="catalyst-sidebar-item" data-wi-tab="agents" onclick="switchWITab(this, 'agents')">✦ Agents</div>
            <div class="catalyst-sidebar-item" data-wi-tab="briefing" onclick="switchWITab(this, 'briefing')">▣ Executions</div>
            <div class="catalyst-sidebar-item" data-wi-tab="tasks" onclick="switchWITab(this, 'tasks')">☑ Approvals</div>
            <div class="catalyst-sidebar-item" data-wi-tab="signals" onclick="switchWITab(this, 'signals')">↺ Interventions</div>
            <div class="catalyst-sidebar-item" onclick="catalystOpenRoute('/command-center', 'chat', 'Open Command', 'Catalyst routed into Command.')">⌁ Resources</div>
            <div class="catalyst-sidebar-item" onclick="catalystOpenRoute('/activity-center', 'activity', 'Open Activity', 'Catalyst opened the activity lane.')">◌ Insights</div>
            <div class="catalyst-sidebar-item" onclick="catalystOpenRoute('/supervision-snapshot', 'chat', 'Open Audit Log', 'Catalyst opened the supervision and audit lane.')">☷ Audit Log</div>
            <div class="catalyst-sidebar-item" onclick="catalystOpenRoute('/settings-center', 'settings', 'Open Settings', 'Catalyst opened settings.')">⚙ Settings</div>
          </div>
          <div class="catalyst-sidebar-foot">
            <div class="catalyst-sidebar-user">
              <strong>Chris</strong>
              Executive Mode
            </div>
            <div class="catalyst-sidebar-user" id="catalyst-runtime-note" style="font-size:12px;line-height:1.5;">Loading live Catalyst workspace…</div>
            <button class="catalyst-action-btn" type="button" id="catalyst-refresh-button" onclick="refreshCatalystDesktop(true)">Refresh Catalyst</button>
          </div>
        </aside>

        <main class="catalyst-main">
          <div class="catalyst-topbar">
            <div>
              <div class="catalyst-topbar-kicker">Desktop Sequence</div>
              <div class="catalyst-topbar-title" id="catalyst-nav-title">1. Catalyst Operations Command Center</div>
              <div class="catalyst-topbar-subtitle" id="catalyst-nav-subtitle">Track live operations, staged actions, approvals, and the one recommendation that should move first.</div>
            </div>
            <div class="catalyst-nav">
              <button class="catalyst-nav-btn" id="catalyst-nav-prev" onclick="advanceCatalystPage(-1)" aria-label="Previous Catalyst page">←</button>
              <div class="catalyst-nav-status">
                <div class="catalyst-nav-page" id="catalyst-page-count">Page 1 of 6</div>
                <div class="catalyst-nav-title" id="catalyst-page-label">Command Center</div>
              </div>
              <button class="catalyst-nav-btn" id="catalyst-nav-next" onclick="advanceCatalystPage(1)" aria-label="Next Catalyst page">→</button>
            </div>
          </div>

          <div class="catalyst-page-deck">
            <section class="catalyst-page active" data-catalyst-page="1">
              <div class="catalyst-grid-hero">
                <div class="catalyst-card catalyst-hero-card">
                  <div class="catalyst-hero-visual">
                    <div class="catalyst-hero-overline" id="catalyst-hero-overline">Good morning, Chris. Your operations are orchestrated.</div>
                    <div>
                      <div class="catalyst-hero-title" id="catalyst-hero-title">Catalyst is already in motion.</div>
                      <div class="catalyst-hero-copy" id="catalyst-hero-copy">See active work, queued triggers, agent health, and the next high-leverage decision without leaving the desktop board.</div>
                    </div>
                    <div class="catalyst-stat-row">
                      <div class="catalyst-metric">
                        <span>Active Workflows</span>
                        <strong class="accent" id="wi-stat-projects">—</strong>
                        <em>Running now</em>
                      </div>
                      <div class="catalyst-metric">
                        <span>Staged Actions</span>
                        <strong id="wi-stat-tasks">—</strong>
                        <em>Ready to run</em>
                      </div>
                      <div class="catalyst-metric">
                        <span>Queued Automations</span>
                        <strong class="warn" id="wi-stat-overdue">—</strong>
                        <em>Awaiting triggers</em>
                      </div>
                      <div class="catalyst-metric">
                        <span>Approvals Needed</span>
                        <strong id="wi-stat-approvals">—</strong>
                        <em>High-impact gates</em>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="catalyst-home-side">
                  <div class="catalyst-panel">
                    <div class="catalyst-card-heading">
                      <div class="catalyst-card-label">System Health<strong>Agent fleet readiness</strong></div>
                    </div>
                    <div class="catalyst-ring" id="catalyst-system-health-score">97<span>Operational</span></div>
                    <div class="wi-status-dots" id="wi-stat-workers" style="margin-top:14px;">—</div>
                    <div class="wi-inline-stat" id="wi-worker-note" style="margin-top:10px;">Checking worker posture…</div>
                  </div>
                  <div class="catalyst-panel">
                    <div class="catalyst-card-heading">
                      <div class="catalyst-card-label">JARVIS Recommendation<strong>Move this board pack forward</strong></div>
                      <span class="catalyst-chip live" id="catalyst-recommendation-chip">Priority</span>
                    </div>
                    <div id="wi-one-rec" style="font-size:13px; line-height:1.7; color:var(--cat-copy-muted);">
                      <div class="skel" style="height:10px;width:90%;margin-bottom:6px;"></div>
                      <div class="skel" style="height:10px;width:70%;"></div>
                    </div>
                    <button class="catalyst-action-btn primary" type="button" style="margin-top:14px;" id="catalyst-review-button" onclick="catalystRunRecommendation()">Review Now</button>
                  </div>
                </div>
              </div>

              <div class="catalyst-governance-grid">
                <div class="catalyst-panel catalyst-list">
                  <div class="catalyst-card-heading">
                    <div class="catalyst-card-label">Live Operations<strong>What is actively moving</strong></div>
                    <span class="catalyst-chip" id="wi-commit-count">—</span>
                  </div>
                  <div id="wi-commitments">
                    <div class="list-row"><div class="list-row-name" style="color:var(--text-3);">Loading…</div></div>
                  </div>
                </div>
                <div class="catalyst-panel catalyst-list">
                  <div class="catalyst-card-heading">
                    <div class="catalyst-card-label">Recent Insights<strong>What the system is surfacing</strong></div>
                  </div>
                  <div id="wi-surfaces">
                    <div class="skel" style="height:10px;width:80%;margin-bottom:6px;"></div>
                    <div class="skel" style="height:10px;width:60%;"></div>
                  </div>
                </div>
                <div class="catalyst-side-stack">
                  <div class="catalyst-side-panel" id="catalyst-side-panel-finalizing">
                    <strong>Finalizing</strong>
                    <p>Q2 Board Pack is the next best candidate to push through executive review and packaging.</p>
                  </div>
                  <div class="catalyst-side-panel" id="catalyst-side-panel-window">
                    <strong>Intervention Window</strong>
                    <p>Finance and Comms are the two zones most likely to need a human nudge in the next 20 minutes.</p>
                  </div>
                </div>
              </div>
            </section>

            <section class="catalyst-page" data-catalyst-page="2">
              <div class="catalyst-project-grid">
                <div class="catalyst-panel">
                  <div class="catalyst-card-heading">
                    <div class="catalyst-card-label">Blocks<strong>Workflow primitives</strong></div>
                  </div>
                  <div class="catalyst-blocks-list" id="catalyst-blocks-list">
                    <div class="catalyst-block-item"><span class="catalyst-block-icon">↻</span>Trigger</div>
                    <div class="catalyst-block-item"><span class="catalyst-block-icon">⚡</span>Action</div>
                    <div class="catalyst-block-item"><span class="catalyst-block-icon">✦</span>Agent</div>
                    <div class="catalyst-block-item"><span class="catalyst-block-icon">◇</span>Condition</div>
                    <div class="catalyst-block-item"><span class="catalyst-block-icon">☑</span>Approval</div>
                    <div class="catalyst-block-item"><span class="catalyst-block-icon">⏱</span>Delay</div>
                    <div class="catalyst-block-item"><span class="catalyst-block-icon">⌁</span>Integration</div>
                    <div class="catalyst-block-item"><span class="catalyst-block-icon">✓</span>End</div>
                  </div>
                </div>

                <div class="catalyst-panel catalyst-flow-board">
                  <div class="catalyst-card-heading">
                    <div class="catalyst-card-label">Workflow Builder Studio<strong id="catalyst-builder-title">Q2 Board Pack Workflow</strong></div>
                    <span class="catalyst-chip warn" id="catalyst-builder-status">Draft</span>
                  </div>
                  <div class="catalyst-flow-layout" id="catalyst-builder-flow">
                    <div class="catalyst-node-column">
                      <div class="catalyst-node"><span>Trigger</span><strong>Board pack requested</strong><em>Manual kickoff</em></div>
                      <div class="catalyst-node"><span>Strategy Agent</span><strong>Gather key insights</strong><em>Assemble narrative</em></div>
                      <div class="catalyst-node"><span>Data Agent</span><strong>Assemble metrics</strong><em>Financial and risk data</em></div>
                    </div>
                    <div class="catalyst-node-column">
                      <div class="catalyst-node decision"><div><span>Condition</span><strong>Confidence &gt; 85</strong><em>Proceed</em></div></div>
                    </div>
                    <div class="catalyst-node-column">
                      <div class="catalyst-node"><span>Data Agent</span><strong>Fill gaps or re-run</strong><em>Route if confidence slips</em></div>
                      <div class="catalyst-node"><span>Comms Agent</span><strong>Draft narrative</strong><em>Executive language</em></div>
                      <div class="catalyst-node"><span>Finalize</span><strong>Package output</strong><em>Ready for review</em></div>
                    </div>
                  </div>
                </div>

                <div class="catalyst-panel">
                  <div class="catalyst-card-heading">
                    <div class="catalyst-card-label">Properties<strong>Selected node</strong></div>
                  </div>
                  <div class="catalyst-properties" id="catalyst-builder-properties">
                    <div class="catalyst-property-row"><span>Node</span><strong>Condition</strong><em>If confidence is high</em></div>
                    <div class="catalyst-property-row"><span>Expression</span><strong>Confidence Score &gt; 85</strong></div>
                    <div class="catalyst-property-row"><span>True Path</span><strong>Yes</strong></div>
                    <div class="catalyst-property-row"><span>False Path</span><strong>No</strong></div>
                  </div>
                  <div class="catalyst-action-column" style="margin-top:14px;" id="catalyst-builder-actions">
                    <button class="catalyst-action-btn primary" type="button">Save</button>
                    <button class="catalyst-action-btn" type="button">Validate</button>
                    <button class="catalyst-action-btn" type="button">Test Run</button>
                  </div>
                </div>
              </div>
            </section>

            <section class="catalyst-page" data-catalyst-page="3">
              <div class="catalyst-execution-grid">
                <div class="catalyst-panel">
                  <div class="catalyst-card-heading">
                    <div class="catalyst-card-label">Execution Flow<strong id="catalyst-execution-title">Q2 Board Pack</strong></div>
                  </div>
                  <div class="catalyst-stage-list" id="catalyst-execution-flow">
                    <div class="catalyst-stage-item"><strong>Trigger</strong><span>Board pack requested · 9:12 AM</span></div>
                    <div class="catalyst-stage-item"><strong>Strategy Agent</strong><span>Gather key insights · 9:13 AM</span></div>
                    <div class="catalyst-stage-item"><strong>Data Agent</strong><span>Assemble metrics · 9:14 AM</span></div>
                    <div class="catalyst-stage-item active"><strong>Approval</strong><span>Executive Review · In progress</span></div>
                    <div class="catalyst-stage-item"><strong>Comms Agent</strong><span>Draft narrative · Pending</span></div>
                    <div class="catalyst-stage-item"><strong>Finalize</strong><span>Package output · Pending</span></div>
                  </div>
                </div>

                <div class="catalyst-panel">
                  <div class="catalyst-card-heading">
                    <div class="catalyst-card-label">Now Running<strong id="catalyst-execution-headline">Approval: Executive Review</strong></div>
                    <span class="catalyst-chip live" id="catalyst-execution-chip">Waiting on 2 of 5</span>
                  </div>
                  <div class="catalyst-avatar-row" id="catalyst-execution-participants">
                    <div class="catalyst-avatar you">You</div>
                    <div class="catalyst-avatar">AL</div>
                    <div class="catalyst-avatar">JD</div>
                    <div class="catalyst-avatar">PR</div>
                    <div class="catalyst-avatar">MG</div>
                  </div>
                  <div class="catalyst-card-heading" style="margin-top:18px;">
                    <div class="catalyst-card-label">Agent Reasoning<strong>What Catalyst sees</strong></div>
                  </div>
                  <p id="catalyst-execution-reasoning">All metrics are within expected range. Revenue trend is steady. Risk exposure is low. Recommendation: approve to proceed with communications packaging.</p>
                  <div class="catalyst-wave" style="margin-top:14px;"></div>
                  <div class="catalyst-score-grid" style="margin-top:14px;" id="catalyst-execution-scores">
                    <div class="catalyst-score-card"><span>Confidence</span><strong>91%</strong></div>
                    <div class="catalyst-score-card"><span>Risk</span><strong>No blockers</strong></div>
                  </div>
                </div>

                <div class="catalyst-side-stack">
                  <div class="catalyst-side-panel" id="catalyst-execution-outputs">
                    <strong>Outputs So Far</strong>
                    <ul>
                      <li>Executive summary ready</li>
                      <li>Financial overview ready</li>
                      <li>Risk assessment ready</li>
                      <li>Market insights ready</li>
                    </ul>
                  </div>
                  <div class="catalyst-side-panel" id="catalyst-execution-nextup">
                    <strong>Next Up</strong>
                    <p>Comms Agent will draft the narrative as soon as executive review clears.</p>
                  </div>
                </div>
              </div>
            </section>

            <section class="catalyst-page" data-catalyst-page="4">
              <div class="catalyst-governance-grid">
                <div class="catalyst-panel catalyst-document-card">
                  <div class="catalyst-card-heading">
                    <div class="catalyst-card-label">Draft to Live<strong id="catalyst-governance-title">Q2 Board Pack</strong></div>
                    <span class="catalyst-chip warn" id="catalyst-governance-status">Staged</span>
                  </div>
                  <strong id="catalyst-governance-preview-title">Q2</strong>
                  <span id="catalyst-governance-preview">Board pack preview package. Review, policy check, then approval into live distribution.</span>
                </div>
                <div class="catalyst-panel catalyst-list">
                  <div class="catalyst-card-heading">
                    <div class="catalyst-card-label">Approval Required<strong>Live governance checks</strong></div>
                    <span class="catalyst-chip live">2 of 4</span>
                  </div>
                  <div class="catalyst-approval-stack" id="catalyst-governance-checks">
                    <div class="catalyst-approval-item"><strong>Trust Zone</strong><span>Standard · within governance boundary</span></div>
                    <div class="catalyst-approval-item"><strong>Policy Check</strong><span>Passed · all validations satisfied</span></div>
                    <div class="catalyst-approval-item"><strong>Data Sensitivity</strong><span>Internal · no restricted data</span></div>
                    <div class="catalyst-approval-item"><strong>Approver Set</strong><span>Jordan + Morgan still pending</span></div>
                  </div>
                </div>
                <div class="catalyst-side-stack">
                  <div class="catalyst-side-panel" id="catalyst-governance-notice">
                    <strong>JARVIS Notice</strong>
                    <p>AI checks passed. Recommend approval to promote this package to live.</p>
                  </div>
                  <div class="catalyst-action-column" id="catalyst-governance-actions">
                    <button class="catalyst-action-btn" type="button">Request Changes</button>
                    <button class="catalyst-action-btn primary" type="button">Promote to Live</button>
                  </div>
                </div>
              </div>
            </section>

            <section class="catalyst-page" data-catalyst-page="5">
              <div class="catalyst-pivot-grid">
                <div class="catalyst-panel catalyst-photo-panel">
                  <div class="catalyst-card-heading">
                    <div class="catalyst-card-label">Intervention Required<strong id="catalyst-intervention-title">High-impact discrepancy</strong></div>
                    <span class="catalyst-chip risk">High Impact</span>
                  </div>
                  <p id="catalyst-intervention-detail">Vendor API returned inconsistent pricing data for the board pack. Confidence slipped below threshold, so Catalyst is holding before the approval chain advances.</p>
                </div>
                <div class="catalyst-panel catalyst-list">
                  <div class="catalyst-card-heading">
                    <div class="catalyst-card-label">Recommended Actions<strong>What Catalyst would do next</strong></div>
                  </div>
                  <div id="wi-signals-list">
                    <div class="list-row"><div class="list-row-name" style="color:var(--text-3);">Loading…</div></div>
                  </div>
                </div>
                <div class="catalyst-side-stack">
                  <div class="catalyst-side-panel" id="catalyst-intervention-why">
                    <strong>Why This Matters</strong>
                    <p>This affects revenue projection accuracy, which is a key decision driver for the board.</p>
                  </div>
                  <div class="catalyst-side-panel" id="catalyst-intervention-confidence">
                    <strong>Confidence</strong>
                    <p>62% · low. Enough to recommend a path, not enough to auto-promote the package.</p>
                  </div>
                  <div class="catalyst-action-column" id="catalyst-intervention-actions">
                    <button class="catalyst-action-btn primary" type="button">Run Option A</button>
                    <button class="catalyst-action-btn" type="button">Ask for Input</button>
                  </div>
                </div>
              </div>
            </section>

            <section class="catalyst-page" data-catalyst-page="6">
              <div class="catalyst-voice-grid">
                <div class="catalyst-card catalyst-chat-card">
                  <div class="catalyst-chat-header">
                    <div class="catalyst-avatar you">JV</div>
                    <div>
                      <div style="font-size:15px;font-weight:700;color:var(--cat-copy);">JARVIS Voice</div>
                      <div style="font-size:11px;color:var(--cat-copy-muted);">Voice Catalyst Consultation</div>
                    </div>
                  </div>
                  <div class="catalyst-chat-messages" id="catalyst-voice-messages">
                    <div class="catalyst-chat-bubble user">Launch the Q2 board pack workflow and loop in Finance.</div>
                    <div class="catalyst-chat-bubble agent">Starting Q2 Board Pack workflow. I’m notifying Finance Agent and routing the package into executive review.</div>
                    <div class="catalyst-chat-bubble user">What’s the status of approvals?</div>
                    <div class="catalyst-chat-bubble agent">2 of 5 approvals are in. Jordan and Morgan are still pending. I can send a reminder now or keep monitoring and alert you when it clears.</div>
                    <div class="catalyst-chat-bubble agent">Reminders sent with high priority. I’ll stay on the workflow and nudge you when the review is complete.</div>
                  </div>
                  <div class="catalyst-chat-footer">
                    <input class="catalyst-chat-input" type="text" id="catalyst-voice-input" placeholder="Ask JARVIS to orchestrate...">
                    <button class="catalyst-action-btn primary" type="button" id="catalyst-voice-send" onclick="catalystSendVoicePrompt()">Send</button>
                  </div>
                </div>
                <div class="catalyst-side-stack">
                  <div class="catalyst-side-panel" id="catalyst-voice-context">
                    <strong>Context</strong>
                    <p>Workflow: Q2 Board Pack. Progress: 62%. Next step: executive review.</p>
                  </div>
                  <div class="catalyst-side-panel" id="catalyst-voice-actions">
                    <strong>Actions</strong>
                    <ul>
                      <li>Send reminder</li>
                      <li>View execution</li>
                      <li>Pause workflow</li>
                      <li>Add owner</li>
                    </ul>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <div class="catalyst-bottom-values">
            <div class="catalyst-mini-card"><strong>Intelligent Orchestration</strong><p>Plans, coordinates, and executes across agents and systems.</p></div>
            <div class="catalyst-mini-card"><strong>Trust & Guardrails</strong><p>Built-in policies, approvals, and trust zones keep work safe.</p></div>
            <div class="catalyst-mini-card"><strong>Agentic Execution</strong><p>Specialized agents do the work, think, and adapt in real time.</p></div>
            <div class="catalyst-mini-card"><strong>Human in the Loop</strong><p>You stay in control with context, clarity, and the final word.</p></div>
            <div class="catalyst-mini-card"><strong>Real-Time Intelligence</strong><p>Live signals, risk detection, and proactive interventions.</p></div>
            <div class="catalyst-mini-card"><strong>From Plan to Impact</strong><p>Ideas become action. Outcomes you can measure.</p></div>
          </div>

          <div style="display:none;">
            <div id="wi-projects-list"></div>
            <div id="wi-tasks-list"></div>
            <div id="wi-briefing-content"></div>
            <div id="wi-briefing-meta"></div>
            <div id="wi-proj-count"></div>
            <div id="wi-tasks-count"></div>
            <div id="wi-signals-count"></div>
            <div id="catalyst-live-operations"></div>
            <div id="catalyst-surfaced-insights"></div>
          </div>
        </main>
      </div>
    </div>
  </div>

  <!-- ── FAITH ──────────────────────────────────────────────── -->
  <div id="view-faith" class="view faith-view">
    <div class="faith-header">
      <div>
        <div class="faith-kicker">Desktop Experience</div>
        <div class="view-title">FAITH<div class="view-title-line"></div></div>
        <div class="faith-subtitle" id="faith-subtitle">A real desktop faith workspace for sanctuary, Scripture, prayer, family discipleship, and voice-guided spiritual counsel. One screen is active at a time, with arrows and a page count guiding the journey.</div>
      </div>
      <div class="faith-motto">
        <div class="faith-motto-mark">🕊</div>
        <div>
          <strong>Walk daily with wisdom.</strong>
          <span>Rooted in faith. Guided by love.</span>
        </div>
      </div>
    </div>

    <div class="faith-desktop-stage">
      <div class="faith-desktop-shell">
        <aside class="faith-sidebar">
          <div class="faith-sidebar-top">
            <div class="faith-sidebar-brand">
              <strong>JARVIS</strong>
              <span>Faith</span>
            </div>
            <div class="faith-sidebar-mark">✦</div>
          </div>
          <div class="faith-sidebar-nav">
            <div class="faith-sidebar-item active">⌂ Sanctuary</div>
            <div class="faith-sidebar-item">✞ Bible</div>
            <div class="faith-sidebar-item">♡ Prayer</div>
            <div class="faith-sidebar-item">✎ Journal</div>
            <div class="faith-sidebar-item">◉ Family</div>
            <div class="faith-sidebar-item">⌛ Liturgy</div>
            <div class="faith-sidebar-item">⌕ Discover</div>
            <div class="faith-sidebar-item">☷ Saved</div>
            <div class="faith-sidebar-item">⚙ Settings</div>
          </div>
          <div class="faith-sidebar-foot">
            <div class="faith-sidebar-user">
              <strong>Chris</strong>
              Child of God
            </div>
          </div>
        </aside>

        <main class="faith-main">
          <div class="faith-topbar">
            <div class="faith-topbar-copy">
              <div class="faith-topbar-kicker">Desktop Sequence</div>
              <div class="faith-topbar-title" id="faith-nav-title">1. Faith Sanctuary Hub</div>
              <div class="faith-topbar-subtitle" id="faith-nav-subtitle">Open the sanctuary: Scripture, focus, prayer rhythms, and the next faithful step for today.</div>
            </div>
            <div class="faith-nav">
              <button class="faith-nav-btn" id="faith-nav-prev" onclick="advanceFaithPage(-1)" aria-label="Previous Faith page">←</button>
              <div class="faith-nav-status">
                <div class="faith-nav-page" id="faith-page-count">Page 1 of 6</div>
                <div class="faith-nav-title" id="faith-page-label">Sanctuary Hub</div>
              </div>
              <button class="faith-nav-btn" id="faith-nav-next" onclick="advanceFaithPage(1)" aria-label="Next Faith page">→</button>
            </div>
          </div>

          <div class="faith-page-deck">
            <section class="faith-page active" data-faith-page="1">
              <div class="faith-sanctuary-grid">
                <div class="faith-card faith-hero-card">
                  <div class="faith-hero-visual">
                    <div class="faith-hero-overline" id="faith-hero-overline">Good evening, Chris. The Lord is near to the brokenhearted.</div>
                    <div>
                      <div class="faith-hero-title" id="faith-hero-title">Be still, and know that I am God.</div>
                      <div class="faith-hero-copy" id="faith-hero-copy">Let today open with presence, Scripture, prayer, and the grace to walk slowly enough to notice what God is doing.</div>
                    </div>
                    <div class="faith-hero-copy" id="faith-runtime-note" style="font-size:12px;opacity:.8;">Loading live Faith context…</div>
                    <div class="faith-hero-button" id="faith-hero-button" onclick="refreshFaithDesktop()">Read Full Chapter</div>
                  </div>
                </div>
                <div class="faith-side-stack">
                  <div class="faith-card">
                    <div class="faith-card-heading">
                      <div class="faith-card-label">Prayer Pulse<strong>Today’s spiritual cadence</strong></div>
                    </div>
                    <div class="faith-stat-stack">
                      <div class="faith-stat-card">
                        <span>Prayer Requests</span>
                        <strong id="faith-stat-requests">12</strong>
                        <em>Open requests for today</em>
                      </div>
                      <div class="faith-stat-card">
                        <span>Answered Prayer</span>
                        <strong id="faith-stat-answered">5</strong>
                        <em>Recent gratitude moments</em>
                      </div>
                      <div class="faith-stat-card">
                        <span>Spiritual Rhythm</span>
                        <strong id="faith-stat-streak">7</strong>
                        <em>Days in the Word</em>
                      </div>
                    </div>
                  </div>
                  <div class="faith-card faith-note-card">
                    <div class="faith-card-heading">
                      <div class="faith-card-label">JARVIS Encouragement<strong>Carry the day gently</strong></div>
                      <button class="faith-action-btn muted" type="button" onclick="refreshFaithDesktop()">Refresh</button>
                    </div>
                    <p id="faith-encouragement-copy">You’ve been carrying a lot. Let today be a day of rest, renewed focus, and small acts of obedience that keep your heart soft.</p>
                  </div>
                </div>
              </div>
              <div class="faith-focus-grid">
                <div class="faith-card faith-focus-card">
                  <div class="faith-card-heading">
                    <div class="faith-card-label">Today’s Focus<strong>Rest in God’s presence</strong></div>
                  </div>
                  <p id="faith-focus-copy">Take a slower pace, entrust what feels heavy, and let prayer frame the decisions ahead.</p>
                </div>
                <div class="faith-card faith-focus-card">
                  <div class="faith-card-heading">
                    <div class="faith-card-label">Devotion Prompt<strong>What is God inviting you to release?</strong></div>
                  </div>
                  <p id="faith-devotion-copy">Notice where anxiety is tightening your grip, then hand that concern over in prayer before acting.</p>
                </div>
                <div class="faith-card faith-focus-card">
                  <div class="faith-card-heading">
                    <div class="faith-card-label">Spiritual Rhythm<strong>Abide in the Word</strong></div>
                  </div>
                  <p id="faith-rhythm-copy">Keep a short prayer running through the day and revisit your passage before the evening closes.</p>
                </div>
              </div>
              <div class="faith-bridge-grid">
                <div class="faith-card faith-focus-card">
                  <strong>Chronicle Connection</strong>
                  <p id="faith-chronicle-status">Checking Chronicle app handoff…</p>
                </div>
                <div class="faith-card faith-focus-card">
                  <strong>Study Flow</strong>
                  <p id="faith-chronicle-study">—</p>
                </div>
                <div class="faith-card faith-focus-card">
                  <strong>Prayer Flow</strong>
                  <p id="faith-chronicle-prayer">—</p>
                </div>
                <div class="faith-card faith-focus-card">
                  <strong>Capture Flow</strong>
                  <p id="faith-chronicle-capture">—</p>
                </div>
              </div>
            </section>

            <section class="faith-page" data-faith-page="2">
              <div class="faith-brief-grid">
                <div class="faith-card faith-brief-player">
                  <div class="faith-card-heading">
                    <div class="faith-card-label">Morning Spiritual Brief<strong>JARVIS Morning Brief</strong></div>
                    <span class="faith-chip">Live</span>
                  </div>
                  <div class="faith-audio-halo">〰</div>
                  <div class="faith-player-meta">
                    <strong>Good morning, Chris.</strong>
                    <span>Let’s begin your day in God’s truth.</span>
                  </div>
                  <div class="faith-player-bar"></div>
                  <div class="faith-player-actions">
                    <div class="faith-player-btn">↺</div>
                    <div class="faith-player-btn">❚❚</div>
                    <div class="faith-player-btn">↻</div>
                  </div>
                  <div class="faith-card faith-daily-word" id="faith-daily-word" style="margin-top:22px;">
                    <div class="faith-card-heading">
                      <div class="faith-card-label">Today’s Word<strong>Carry this into the day</strong></div>
                    </div>
                    <div class="faith-dw-header">
                      <span class="faith-dw-agent" id="faith-dw-agent">—</span>
                      <span class="faith-dw-tag" id="faith-dw-tag">Daily Word</span>
                    </div>
                    <div class="faith-dw-body" id="faith-dw-body">—</div>
                    <div class="faith-dw-passage" id="faith-dw-passage"></div>
                  </div>
                  <div class="faith-focus-grid" style="margin-top:22px;">
                    <div class="faith-card faith-focus-card">
                      <strong>Today’s Scripture</strong>
                      <p id="faith-brief-scripture">Philippians 4:6-7. Bring your requests to God with thanksgiving.</p>
                    </div>
                    <div class="faith-card faith-focus-card">
                      <strong>Prayer Intention</strong>
                      <p id="faith-brief-intention">Peace over anxiety and wisdom in decisions.</p>
                    </div>
                    <div class="faith-card faith-focus-card">
                      <strong>Today’s Action</strong>
                      <p id="faith-brief-action">Take a 20-minute walk and thank God for three graces you almost missed.</p>
                    </div>
                  </div>
                  <div class="faith-action-row">
                    <button class="faith-action-btn primary" type="button" onclick="captureFaithPrayer()">Start Prayer in Chronicle</button>
                    <button class="faith-action-btn muted" type="button" onclick="openChronicleFromFaith('prayer')">Open Chronicle</button>
                  </div>
                </div>
                <div class="faith-card">
                  <div class="faith-card-heading">
                    <div class="faith-card-label">Overnight Summary<strong>How your heart arrived</strong></div>
                  </div>
                  <div class="faith-summary-list" id="faith-overnight-summary">
                    <div class="faith-summary-item"><span>Sleep</span><strong>7h 12m · Good recovery</strong><em>Ready</em></div>
                    <div class="faith-summary-item"><span>Reflection</span><strong>Psalm 46 · Peace in God</strong><em>Centered</em></div>
                    <div class="faith-summary-item"><span>Prayer</span><strong>3 answered · 2 new</strong><em>Held</em></div>
                    <div class="faith-summary-item"><span>Heart</span><strong>Gratitude rising</strong><em>Open</em></div>
                  </div>
                </div>
              </div>
            </section>

            <section class="faith-page" data-faith-page="3">
              <div class="faith-scripture-grid">
                <div class="faith-card faith-scripture-card">
                  <div class="faith-card-heading">
                    <div class="faith-card-label">Scripture Reflection Workspace<strong id="faith-scripture-title">Philippians 4:6-7</strong></div>
                    <span class="faith-chip" id="faith-scripture-translation">Reflection</span>
                  </div>
                  <div class="faith-scripture-body" id="faith-scripture-body">
                    <span class="verse-number">6</span>Do not be anxious about anything, but in everything by prayer and supplication with thanksgiving let your requests be made known to God.<br><br>
                    <span class="verse-number">7</span>And the peace of God, which surpasses all understanding, will guard your hearts and your minds in Christ Jesus.
                  </div>
                  <div class="faith-action-row">
                    <button class="faith-action-btn primary" type="button" onclick="queueFaithReflection()">Open Study in Chronicle</button>
                    <button class="faith-action-btn muted" type="button" onclick="openChronicleFromFaith('study')">Open Chronicle Study</button>
                  </div>
                </div>
                <div class="faith-side-stack">
                  <div class="faith-card faith-reflection-card">
                    <div class="faith-card-heading">
                      <div class="faith-card-label">JARVIS Insight<strong>Prayer shifts the focus</strong></div>
                    </div>
                    <p id="faith-insight-copy">Paul connects prayer with peace. Thanksgiving turns the heart from control toward trust.</p>
                  </div>
                  <div class="faith-card faith-reflection-card">
                    <div class="faith-card-heading">
                      <div class="faith-card-label">Reflection Prompts<strong>Carry these into prayer</strong></div>
                    </div>
                    <ul class="faith-reflection-list" id="faith-reflection-prompts">
                      <li>What are you anxious about right now?</li>
                      <li>How can prayer change your perspective?</li>
                      <li>What would peace from God look like today?</li>
                    </ul>
                  </div>
                </div>
              </div>
            </section>

            <section class="faith-page" data-faith-page="4">
              <div class="faith-journal-grid">
                <div class="faith-card faith-journal-card">
                  <div class="faith-card-heading">
                    <div class="faith-card-label">Prayer Journal<strong>Recent entries</strong></div>
                  </div>
                  <div class="faith-journal-list" id="faith-journal-list">
                    <div class="faith-journal-entry">
                      <strong>Peace for Emma’s exams</strong>
                      <span>Today · High</span>
                      <p>Lord, give her focus and calm.</p>
                    </div>
                    <div class="faith-journal-entry">
                      <strong>Wisdom in a decision</strong>
                      <span>Yesterday · Medium</span>
                      <p>Help me discern the right path.</p>
                    </div>
                    <div class="faith-journal-entry">
                      <strong>Strength for recovery</strong>
                      <span>May 23 · High</span>
                      <p>Healing and peace for the road ahead.</p>
                    </div>
                  </div>
                </div>
                <div class="faith-card faith-journal-card">
                  <div class="faith-card-heading">
                    <div class="faith-card-label">Entry Details<strong id="faith-journal-detail-title">Peace for Emma’s exams</strong></div>
                  </div>
                  <p id="faith-journal-detail-copy">Lord, give Emma clarity, calm, and strong focus as she prepares for her exams. Guard her heart from worry and fill her with confidence in You.</p>
                  <div class="faith-tag-row" id="faith-journal-tags">
                    <span class="faith-chip">Family</span>
                    <span class="faith-chip">Exams</span>
                    <span class="faith-chip">Peace</span>
                  </div>
                  <div class="faith-action-row" id="faith-journal-actions">
                    <button class="faith-action-btn muted" type="button">Journal actions unavailable</button>
                  </div>
                  <div class="faith-card" style="margin-top:18px;">
                    <div class="faith-card-heading">
                      <div class="faith-card-label">JARVIS Insight<strong>Patterns worth noticing</strong></div>
                    </div>
                    <p id="faith-journal-insight">You often pray for peace before important moments. Keep trusting God to meet your family in the pressure, not only after it passes.</p>
                  </div>
                </div>
                <div class="faith-card faith-journal-card">
                  <div class="faith-card-heading">
                    <div class="faith-card-label">Spiritual Patterns<strong>Last 30 days</strong></div>
                  </div>
                  <div class="faith-mini-list" id="faith-journal-patterns">
                    <div class="faith-mini-row"><span>Prayer consistency</span><strong>16-day rhythm</strong></div>
                    <div class="faith-mini-row"><span>Gratitude entries</span><strong>14</strong></div>
                    <div class="faith-mini-row"><span>Answered prayers</span><strong>7</strong></div>
                  </div>
                  <div class="faith-action-row">
                    <button class="faith-action-btn muted" type="button" onclick="captureFaithGratitude()">Send Gratitude to Chronicle</button>
                  </div>
                </div>
              </div>
            </section>

            <section class="faith-page" data-faith-page="5">
              <div class="faith-family-grid">
                <div class="faith-card faith-family-card">
                  <div class="faith-card-heading">
                    <div class="faith-card-label">Family Faith Center<strong>Household guidance</strong></div>
                  </div>
                  <p id="faith-family-summary">Strengthen the home with shared prayer, gentle reminders, and rhythms that keep Christ at the center of the week.</p>
                  <div class="faith-mini-list" style="margin-top:14px;" id="faith-family-meta">
                    <div class="faith-mini-row"><span>Prayer requests</span><strong>2 urgent · 4 steady</strong></div>
                    <div class="faith-mini-row"><span>Family devotion</span><strong>Tonight · 7:00 PM</strong></div>
                    <div class="faith-mini-row"><span>Household reminder</span><strong>Church together · Sunday</strong></div>
                  </div>
                </div>
                <div class="faith-card">
                  <div class="faith-card-heading">
                    <div class="faith-card-label">Your Council<strong>Choose a guide for the conversation</strong></div>
                  </div>
                  <div class="faith-roster" id="faith-roster">
                    <div class="skel" style="height:132px;border-radius:16px;"></div>
                    <div class="skel" style="height:132px;border-radius:16px;"></div>
                    <div class="skel" style="height:132px;border-radius:16px;"></div>
                  </div>
                </div>
                <div class="faith-card faith-family-card">
                  <div class="faith-card-heading">
                    <div class="faith-card-label">Household Liturgy<strong>What to nurture this week</strong></div>
                  </div>
                  <p id="faith-household-liturgy">Create one shared gratitude list, one short family prayer before dinner, and one Scripture moment that turns the evening toward peace.</p>
                  <div class="faith-action-row">
                    <button class="faith-action-btn muted" type="button" onclick="openChronicleFromFaith('formation')">Open Chronicle Formation Timeline</button>
                  </div>
                </div>
              </div>
            </section>

            <section class="faith-page" data-faith-page="6">
              <div class="faith-voice-grid">
                <div class="faith-chat-panel" id="faith-chat-panel" style="display:none;">
                  <div class="faith-chat-header">
                    <div class="faith-chat-avatar" id="faith-chat-avatar"></div>
                    <div>
                      <div class="faith-chat-name" id="faith-chat-name">—</div>
                      <div class="faith-chat-domain" id="faith-chat-domain">—</div>
                    </div>
                    <button class="faith-action-btn muted" type="button" style="margin-left:auto;" onclick="saveFaithConversationToChronicle()">Send to Chronicle</button>
                    <button class="btn btn-sm" type="button" onclick="closeFaithChat()">Close</button>
                  </div>
                  <div class="faith-chat-passage-row">
                    <input class="faith-chat-passage-input" id="faith-chat-passage" type="text" placeholder="Passage (optional — e.g. John 1:14)…">
                  </div>
                  <div class="faith-chat-messages" id="faith-chat-messages"></div>
                  <div class="faith-chat-input-row">
                    <textarea class="faith-chat-textarea" id="faith-chat-input" rows="3"
                      placeholder="Ask anything about your faith…"
                      onkeydown="if(event.key==='Enter'&&!event.shiftKey){{event.preventDefault();faithSend();}}"></textarea>
                    <button class="btn btn-hue btn-sm faith-send-btn" onclick="faithSend()" id="faith-send-btn">Send</button>
                  </div>
                </div>
                <div class="faith-chat-panel" id="faith-chat-shell-placeholder">
                  <div class="faith-chat-header">
                    <div class="faith-chat-avatar" style="background:#ddb37a;">✦</div>
                    <div>
                      <div class="faith-chat-name">Voice Faith Consultation</div>
                      <div class="faith-chat-domain">Select a guide from Your Council to begin.</div>
                    </div>
                  </div>
                  <div class="faith-chat-messages" style="height:430px;justify-content:center;">
                    <div style="text-align:center;color:var(--faith-muted);font-size:13px;line-height:1.7;max-width:420px;margin:auto;">
                      Open a conversation with a faith guide and ask about a passage, a prayer burden, or the question you are carrying today.
                    </div>
                  </div>
                </div>
                <div class="faith-side-stack">
                  <div class="faith-side-panel">
                    <strong>Context</strong>
                    <p id="faith-voice-context">Spiritual readiness: 82%. Recent focus: peace and trust. Prayer streak: 18 days.</p>
                  </div>
                  <div class="faith-side-panel">
                    <strong>Today’s Guidance</strong>
                    <p id="faith-voice-guidance">Breathe. Pray. Trust. God is with you in the concern, not only after it is resolved.</p>
                  </div>
                  <div class="faith-side-panel">
                    <strong>Related</strong>
                    <ul id="faith-voice-related">
                      <li>Verses on peace</li>
                      <li>Prayers for anxiety</li>
                      <li>Worship for rest</li>
                    </ul>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <div class="faith-focus-grid" style="margin-top:18px;">
            <div class="faith-card faith-focus-card"><strong>Scripture Centered</strong><p>Rooted in God’s Word. Guided by truth.</p></div>
            <div class="faith-card faith-focus-card"><strong>Prayer Driven</strong><p>Turn to God in every moment. He hears.</p></div>
            <div class="faith-card faith-focus-card"><strong>Family Focused</strong><p>Strengthen your home through faith together.</p></div>
          </div>
        </main>
      </div>
    </div>
  </div>

  <!-- ── CHRONICLE ──────────────────────────────────────────── -->
  <div id="view-chronicle" class="view legacy-view">
    <div class="legacy-header">
      <div>
        <div class="legacy-kicker">Desktop Experience</div>
        <div class="view-title">LEGACY<div class="view-title-line"></div></div>
        <div class="legacy-subtitle">The actual desktop workspace for memory, family history, reflection, and voice-guided story building. One screen is active at a time, with arrows and page count carrying the experience forward.</div>
      </div>
      <div class="legacy-motto">
        <div class="legacy-motto-mark">✒</div>
        <strong>Preserve the life behind the data.</strong>
        <span>Move from moments, to meaning, to a living family archive.</span>
      </div>
    </div>

    <div class="legacy-desktop-stage">
      <div class="legacy-desktop-shell">
        <aside class="legacy-sidebar">
          <div class="legacy-sidebar-top">
            <div class="legacy-sidebar-brand">
              <strong>JARVIS</strong>
              <span>Legacy</span>
            </div>
            <div class="legacy-sidebar-mark">✦</div>
          </div>
          <div class="legacy-sidebar-nav">
            <div class="legacy-sidebar-item active">⌂ Home</div>
            <div class="legacy-sidebar-item">◌ Timeline</div>
            <div class="legacy-sidebar-item">☰ Stories</div>
            <div class="legacy-sidebar-item">◍ People</div>
            <div class="legacy-sidebar-item">⌖ Places</div>
            <div class="legacy-sidebar-item">✒ Themes</div>
            <div class="legacy-sidebar-item">⌕ Search</div>
            <div class="legacy-sidebar-item">☷ Archive</div>
          </div>
          <div class="legacy-sidebar-foot">
            <div class="legacy-sidebar-user">
              <strong>Chris</strong>
              Pro Plan · Living story engine
            </div>
          </div>
        </aside>

        <main class="legacy-main">
          <div class="legacy-topbar">
            <div class="legacy-topbar-copy">
              <div class="legacy-topbar-kicker">Desktop Sequence</div>
              <div class="legacy-topbar-title" id="legacy-nav-title">1. Memory Hub</div>
              <div class="legacy-topbar-subtitle" id="legacy-nav-subtitle">Your story center with recent moments, living themes, and the next reflection worth preserving.</div>
            </div>
            <div class="legacy-nav">
              <button class="legacy-nav-btn" id="legacy-nav-prev" onclick="advanceLegacyPage(-1)" aria-label="Previous Legacy page">←</button>
              <div class="legacy-nav-status">
                <div class="legacy-nav-page" id="legacy-page-count">Page 1 of 6</div>
                <div class="legacy-nav-title" id="legacy-page-label">Memory Hub</div>
              </div>
              <button class="legacy-nav-btn" id="legacy-nav-next" onclick="advanceLegacyPage(1)" aria-label="Next Legacy page">→</button>
            </div>
          </div>

          <div class="legacy-page-deck">
            <section class="legacy-page active" data-legacy-page="1">
              <div class="legacy-home-grid">
                <div class="legacy-card legacy-hero-card">
                  <div class="legacy-hero-visual">
                    <div class="legacy-hero-overline" id="legacy-hero-overline">Good evening, Chris.</div>
                    <div>
                      <div class="legacy-hero-title" id="legacy-hero-title">Your story is still unfolding.</div>
                      <div class="legacy-hero-copy" id="legacy-hero-copy">Capture the moments that shaped today, then connect them to the people, places, and reflections that matter over time.</div>
                    </div>
                    <button class="legacy-hero-button" id="legacy-hero-button" type="button">Begin Reflection</button>
                  </div>
                </div>
                <div class="legacy-home-side">
                  <div class="legacy-stack-card">
                    <div class="legacy-card-heading">
                      <div class="legacy-card-label">Life Themes<strong>What keeps resurfacing</strong></div>
                    </div>
                    <div class="legacy-pill-row" id="legacy-theme-pills">
                      <span class="legacy-pill">Family</span>
                      <span class="legacy-pill">Faith</span>
                      <span class="legacy-pill">Adventure</span>
                      <span class="legacy-pill">Growth</span>
                      <span class="legacy-pill">Gratitude</span>
                    </div>
                  </div>
                  <div class="legacy-detail-card">
                    <div class="legacy-card-heading">
                      <div class="legacy-card-label">Prompt Lane<strong>Moments worth preserving</strong></div>
                    </div>
                    <p id="legacy-prompt-lane">You have open memory lanes around family trips, formative conversations, and the nights that brought clarity back into focus.</p>
                    <p id="legacy-runtime-note" style="margin-top:12px;font-size:11px;color:var(--legacy-copy-faint);"></p>
                  </div>
                </div>
              </div>
              <div class="legacy-metric-row">
                <div class="legacy-metric"><span>Entries</span><strong id="chronicle-total">—</strong></div>
                <div class="legacy-metric"><span>Active Prayer</span><strong class="accent" id="chr-active-prayers">—</strong></div>
                <div class="legacy-metric"><span>Answered</span><strong class="good" id="chr-answered-prayers">—</strong></div>
                <div class="legacy-metric"><span>Rhythms</span><strong class="soft" id="chr-rhythms-count">—</strong></div>
              </div>
            </section>

            <section class="legacy-page" data-legacy-page="2">
              <div class="legacy-capture-page">
                <div class="legacy-card legacy-dropzone">
                  <div class="legacy-dropzone-icon">☁</div>
                  <strong>Add the moment</strong>
                  <span>Drop photos, voice notes, or a few written lines. Legacy will organize the memory, themes, and relationships around it.</span>
                </div>
                <div class="legacy-capture-side">
                  <div class="legacy-input-card">
                    <div class="legacy-card-heading">
                      <div class="legacy-card-label">Capture Intake<strong>Bring the memory in cleanly</strong></div>
                    </div>
                    <div class="chr-capture-type-row" id="chr-capture-types">
                      <button class="chr-capture-type active" data-type="note" onclick="setChrCaptureType(this,'note')">Note</button>
                      <button class="chr-capture-type" data-type="gratitude" onclick="setChrCaptureType(this,'gratitude')">Gratitude</button>
                      <button class="chr-capture-type" data-type="prayer" onclick="setChrCaptureType(this,'prayer')">Prayer</button>
                      <button class="chr-capture-type" data-type="insight" onclick="setChrCaptureType(this,'insight')">Insight</button>
                      <button class="chr-capture-type" data-type="milestone" onclick="setChrCaptureType(this,'milestone')">Milestone</button>
                    </div>
                    <div>
                      <div class="legacy-field-label">Reflection</div>
                      <input class="chr-capture-input" id="chr-capture-input" type="text" placeholder="What happened, and why does it matter?" onkeydown="if(event.key==='Enter')chrQuickCapture()">
                    </div>
                    <div style="margin-top:10px;">
                      <div class="legacy-field-label">Scripture or anchor passage</div>
                      <input class="chr-capture-passage" id="chr-capture-passage" type="text" placeholder="Passage, place, or anchor thought">
                    </div>
                    <div class="legacy-actions">
                      <div style="flex:1;">
                        <div class="legacy-field-label">Intake Progress</div>
                        <div class="legacy-progress-track"><div class="legacy-progress-fill"></div></div>
                      </div>
                      <button class="legacy-button" onclick="chrQuickCapture()">Capture Memory</button>
                    </div>
                  </div>
                  <div class="legacy-copy-card">
                    <div class="legacy-card-heading">
                      <div class="legacy-card-label">What JARVIS Does<strong>Intake synthesis</strong></div>
                    </div>
                    <p id="legacy-capture-copy">The note is sorted into people, themes, places, and follow-up prompts so it can become part of a longer story instead of a disconnected entry.</p>
                  </div>
                </div>
              </div>
            </section>

            <section class="legacy-page" data-legacy-page="3">
              <div class="legacy-search-wrap">
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="6.5" cy="6.5" r="4"></circle><path d="M11 11l3 3"></path></svg>
                <input class="legacy-search-input" type="text" placeholder="Search stories, passages, places, and themes…" id="chronicle-search" oninput="searchChronicle(this.value)">
              </div>
              <div class="legacy-content-grid">
                <div class="legacy-panel-card">
                  <div class="legacy-card-heading">
                    <div class="legacy-card-label">Timeline<strong>Story Thread</strong></div>
                  </div>
                  <div class="legacy-list-wrap" id="chronicle-list">
                    <div class="chr-entry-card"><div class="skel" style="height:12px;width:60%;margin-bottom:8px;"></div><div class="skel" style="height:10px;width:85%;"></div></div>
                    <div class="chr-entry-card"><div class="skel" style="height:12px;width:45%;margin-bottom:8px;"></div><div class="skel" style="height:10px;width:70%;"></div></div>
                  </div>
                </div>
                <div class="legacy-info-card">
                  <div class="legacy-card-heading">
                    <div class="legacy-card-label">Context<strong>What the thread means</strong></div>
                  </div>
                  <div class="legacy-points" id="legacy-thread-points">
                    <div class="legacy-point"><strong>Story Themes</strong><span>Adventure, family bond, nature, gratitude, and the moments that slow life down enough to be felt.</span></div>
                    <div class="legacy-point"><strong>People in This Story</strong><span>Mom, Dad, Emma, Alex, and the family conversations that keep resurfacing.</span></div>
                    <div class="legacy-point"><strong>Story Summary</strong><span>Legacy is treating these entries as one connected chapter rather than several isolated notes.</span></div>
                  </div>
                </div>
              </div>
            </section>

            <section class="legacy-page" data-legacy-page="4">
              <div class="legacy-grid-two">
                <div class="legacy-panel-card">
                  <div class="legacy-card-heading">
                    <div class="legacy-card-label">Family Lines<strong>Open lanes and recurring signals</strong></div>
                  </div>
                  <div class="legacy-tag-cloud tag-cloud" id="tag-cloud">
                    <div class="skel" style="height:24px;width:60px;border-radius:99px;"></div>
                    <div class="skel" style="height:24px;width:80px;border-radius:99px;"></div>
                  </div>
                  <div class="legacy-points" id="legacy-archive-points" style="margin-top:14px;">
                    <div class="legacy-point"><strong>Missing origin stories</strong><span>Which milestones still need to be told by the people who lived them?</span></div>
                    <div class="legacy-point"><strong>Timeline gaps</strong><span>Where do place, date, and relationship threads still need evidence before they become part of the record?</span></div>
                    <div class="legacy-point"><strong>Faith continuity</strong><span>Which reflections from the Chronicle faith app should bridge into this wider family archive?</span></div>
                  </div>
                </div>
                <div class="legacy-panel-card legacy-pattern-wrap">
                  <div class="legacy-card-heading">
                    <div class="legacy-card-label">Evidence Ledger<strong>30-day patterning</strong></div>
                  </div>
                  <div id="chr-patterns">
                    <div class="skel" style="height:80px;border-radius:8px;"></div>
                  </div>
                </div>
              </div>
            </section>

            <section class="legacy-page" data-legacy-page="5">
              <div class="legacy-content-grid">
                <div class="legacy-info-card">
                  <div class="legacy-card-heading">
                    <div class="legacy-card-label">Narrative Synthesis<strong>A chapter emerges</strong></div>
                  </div>
                  <div class="legacy-points" id="legacy-synthesis-points">
                    <div class="legacy-point"><strong>Suggested Title</strong><span>A Place That Shaped Us</span></div>
                    <div class="legacy-point"><strong>This Chapter</strong><span>The mountain, the conversation, the quiet ride home, and the moment everything slowed down enough to be felt.</span></div>
                    <div class="legacy-point"><strong>Why It Matters</strong><span>Legacy is turning repeated moments into chapter candidates so meaning accumulates over time rather than disappearing into fragments.</span></div>
                  </div>
                </div>
                <div class="legacy-panel-card">
                  <div class="legacy-card-heading">
                    <div class="legacy-card-label">Formation Rhythms<strong>Recurring practices</strong></div>
                    <button class="legacy-button" type="button" onclick="openBibleStudyModal()">Open Study</button>
                  </div>
                  <div class="legacy-feed compact" id="chr-rhythms-list">
                    <div style="padding:16px;color:var(--text-3);font-size:12px;">Loading…</div>
                  </div>
                </div>
              </div>
            </section>

            <section class="legacy-page" data-legacy-page="6">
              <div class="legacy-content-grid">
                <div class="legacy-info-card">
                  <div class="legacy-card-heading">
                    <div class="legacy-card-label">Voice Consultation<strong>Legacy Voice</strong></div>
                  </div>
                  <div class="legacy-voice-thread" id="legacy-voice-thread">
                    <div class="legacy-bubble user">Tell me about the moments this family will still care about in ten years.</div>
                    <div class="legacy-bubble agent">I’m seeing a thread around shared trips, gratitude after hard seasons, and the conversations that made ordinary days feel formative. I can build a reflection, a story chapter, or a family archive entry from those signals.</div>
                    <div class="legacy-voice-footer">
                      <div class="legacy-wave"></div>
                      <div class="legacy-voice-chip">Listening</div>
                    </div>
                  </div>
                </div>
                <div class="legacy-panel-card">
                  <div class="legacy-card-heading">
                    <div class="legacy-card-label">Active Prayer &amp; Context<strong>Signals in motion</strong></div>
                  </div>
                  <div class="legacy-feed" id="chr-prayer-list">
                    <div style="padding:16px;color:var(--text-3);font-size:12px;">Loading…</div>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  </div>

  <!-- ── PUBLISHING ─────────────────────────────────────────── -->
  <div id="view-publishing" class="view publish-view">
    <div class="publish-header">
      <div>
        <div class="publish-kicker">Desktop Experience</div>
        <div class="view-title">PUBLISH<div class="view-title-line"></div></div>
        <div class="publish-subtitle" id="pub-subtitle">Ghostwritr publish handoff, chapter readiness, format packaging, and connected launch operations in one supervised desktop workflow.</div>
      </div>
      <div class="publish-motto">
        <strong>Meaningful data concept.</strong>
        <span>Prepare the manuscript, validate the handoff, package the formats, and supervise downstream launch surfaces from one place.</span>
      </div>
    </div>

    <div class="publish-desktop-stage">
      <div class="publish-desktop-shell">
        <aside class="publish-sidebar">
          <div class="publish-sidebar-brand">
            <strong>PUBLISH</strong>
            <span>Ghostwritr handoff</span>
          </div>
          <div class="publish-sidebar-nav">
            <button class="publish-sidebar-item active" type="button" data-publish-nav="1" onclick="setPublishPage(1)">⌂ Handoff Overview</button>
            <button class="publish-sidebar-item" type="button" data-publish-nav="2" onclick="setPublishPage(2)">☑ Validation Report</button>
            <button class="publish-sidebar-item" type="button" data-publish-nav="2" onclick="setPublishPage(2)">◎ Readiness</button>
            <button class="publish-sidebar-item" type="button" data-publish-nav="3" onclick="setPublishPage(3)">☷ Chapter Readiness</button>
            <button class="publish-sidebar-item" type="button" data-publish-nav="4" onclick="setPublishPage(4)">⬚ Assembly &amp; Export</button>
            <button class="publish-sidebar-item" type="button" data-publish-nav="5" onclick="setPublishPage(5)">☰ Format Profiles</button>
            <button class="publish-sidebar-item" type="button" data-publish-nav="6" onclick="setPublishPage(6)">⇢ Launch Ops</button>
            <button class="publish-sidebar-item" type="button" onclick="publishOpenRoute('/publish', 'publishing', 'Open Publish Module', 'Opened the dedicated Publish module route.')">◌ Audit &amp; Provenance</button>
            <button class="publish-sidebar-item" type="button" onclick="publishOpenRoute('/settings-center', 'publishing', 'Open Settings', 'Opened the publishing settings and connector boundary.')">⚙ Settings</button>
          </div>
          <div class="publish-sidebar-foot">
            <strong>Ghostwritr Workspace</strong>
            <div id="pub-side-workspace">Waiting for active book…</div>
            <div id="pub-runtime-note" style="margin-top:10px;font-size:11px;color:var(--text-3);line-height:1.5;">Publishing runtime is loading…</div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;">
              <button class="btn btn-sm" type="button" id="publish-refresh-button" style="font-size:10px;" onclick="refreshPublishingDesktop(true)">Refresh Publishing</button>
              <button class="btn btn-sm" type="button" style="font-size:10px;" onclick="publishCreateDraftProject()">Quick Draft Project</button>
            </div>
            <a href="http://localhost:3000" target="_blank" class="btn btn-sm" style="font-size:10px;text-decoration:none;margin-top:10px;display:inline-flex;">Open in Ghostwritr ↗</a>
          </div>
        </aside>

        <main class="publish-main">
          <div class="publish-topbar">
            <div class="publish-topbar-copy">
              <div class="publish-topbar-kicker">Desktop Sequence</div>
              <div class="publish-topbar-title" id="publish-nav-title">1. Handoff Overview</div>
              <div class="publish-topbar-subtitle" id="publish-nav-subtitle">Open the active manuscript, inspect handoff state, and see whether the package is truly ready to leave Ghostwritr.</div>
            </div>
            <div class="publish-nav">
              <button class="publish-nav-btn" id="publish-nav-prev" onclick="advancePublishPage(-1)" aria-label="Previous Publish page">←</button>
              <div class="publish-nav-status">
                <div class="publish-nav-page" id="publish-page-count">Page 1 of 6</div>
                <div class="publish-nav-title" id="publish-page-label">Handoff Overview</div>
              </div>
              <button class="publish-nav-btn" id="publish-nav-next" onclick="advancePublishPage(1)" aria-label="Next Publish page">→</button>
            </div>
          </div>

          <div class="publish-page-deck">
            <section class="publish-page active" data-publish-page="1">
              <div class="publish-hero-grid">
                <div class="publish-book-cover"></div>
                <div class="publish-card-shell">
                  <div class="publish-card-heading">
                    <div class="publish-card-label">Handoff Overview<strong id="pub-hero-title">Waiting for Ghostwritr…</strong></div>
                    <span class="publish-chip" id="pub-gw-status">—</span>
                  </div>
                  <div class="publish-kv-list" id="pub-hero-kv">
                    <div class="publish-kv-row"><span>Author</span><strong>—</strong></div>
                    <div class="publish-kv-row"><span>Workflow</span><strong>—</strong></div>
                    <div class="publish-kv-row"><span>Package State</span><strong>—</strong></div>
                    <div class="publish-kv-row"><span>Sync State</span><strong>—</strong></div>
                  </div>
                </div>
                <div class="publish-card-shell">
                  <div class="publish-card-heading">
                    <div class="publish-card-label">Source Provenance<strong>Artifact authority</strong></div>
                  </div>
                  <div class="publish-mini-list" id="pub-provenance-list">
                    <div class="publish-mini-row"><span>Current assembly</span><strong>—</strong></div>
                    <div class="publish-mini-row"><span>Package source</span><strong>—</strong></div>
                    <div class="publish-mini-row"><span>Last refreshed</span><strong>—</strong></div>
                  </div>
                </div>
              </div>
            </section>

            <section class="publish-page" data-publish-page="2">
              <div class="publish-grid-two">
                <div class="publish-card-shell">
                  <div class="publish-card-heading">
                    <div class="publish-card-label">Validation Report<strong>Pending reviews and gate checks</strong></div>
                    <span class="publish-chip" id="pub-review-count-badge">0</span>
                  </div>
                  <div id="pub-reviews-section" style="display:none;">
                    <div id="publishing-reviews"></div>
                  </div>
                  <div id="pub-validation-empty" class="publish-panel-shell">No blocking review items yet.</div>
                </div>
                <div class="publish-card-shell">
                  <div class="publish-card-heading">
                    <div class="publish-card-label">Readiness Metrics<strong>Package quality baseline</strong></div>
                  </div>
                  <div class="publish-grid-three">
                    <div class="publish-mini-shell"><strong id="homeProjectsBadge">—</strong><p>Books</p></div>
                    <div class="publish-mini-shell"><strong id="pub-review-count">—</strong><p>Reviews</p></div>
                    <div class="publish-mini-shell"><strong id="pub-inprogress-count">—</strong><p>In Progress</p></div>
                    <div class="publish-mini-shell"><strong id="pub-metric-committed">—</strong><p>Committed chapters</p></div>
                    <div class="publish-mini-shell"><strong id="pub-metric-words">—</strong><p>Committed words</p></div>
                    <div class="publish-mini-shell"><strong id="pub-metric-formats">—</strong><p>Export formats</p></div>
                  </div>
                </div>
              </div>
            </section>

            <section class="publish-page" data-publish-page="3">
              <div class="publish-card-shell">
                <div class="publish-card-heading">
                  <div class="publish-card-label">Chapter Readiness<strong>Book pipeline and stage groups</strong></div>
                </div>
                <div id="publishing-books">
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
              </div>
            </section>

            <section class="publish-page" data-publish-page="4">
              <div class="publish-grid-two">
                <div class="publish-card-shell">
                  <div class="publish-card-heading">
                    <div class="publish-card-label">Final Delivery Checklist<strong>What still stands between draft and handoff</strong></div>
                  </div>
                  <div class="publish-checklist" id="pub-delivery-checklist">
                    <div class="publish-check-row"><span>Waiting</span><strong>Load active manuscript</strong></div>
                  </div>
                </div>
                <div class="publish-card-shell">
                  <div class="publish-card-heading">
                    <div class="publish-card-label">Assembly &amp; Export<strong>Source and artifact notes</strong></div>
                  </div>
                  <div class="publish-mini-list" id="pub-assembly-notes">
                    <div class="publish-mini-row"><span>Assembly</span><strong>—</strong></div>
                    <div class="publish-mini-row"><span>Target pages</span><strong>—</strong></div>
                    <div class="publish-mini-row"><span>Last commit</span><strong>—</strong></div>
                  </div>
                </div>
              </div>
            </section>

            <section class="publish-page" data-publish-page="5">
              <div class="publish-grid-three">
                <div class="publish-card-shell">
                  <div class="publish-card-heading">
                    <div class="publish-card-label">Format Profiles<strong>Print</strong></div>
                  </div>
                  <div class="publish-mini-list" id="pub-format-print">
                    <div class="publish-mini-row"><span>Status</span><strong>Ready</strong></div>
                  </div>
                </div>
                <div class="publish-card-shell">
                  <div class="publish-card-heading">
                    <div class="publish-card-label">Format Profiles<strong>Ebook</strong></div>
                  </div>
                  <div class="publish-mini-list" id="pub-format-ebook">
                    <div class="publish-mini-row"><span>Status</span><strong>Ready</strong></div>
                  </div>
                </div>
                <div class="publish-card-shell">
                  <div class="publish-card-heading">
                    <div class="publish-card-label">Format Profiles<strong>Audio</strong></div>
                  </div>
                  <div class="publish-mini-list" id="pub-format-audio">
                    <div class="publish-mini-row"><span>Status</span><strong>Not requested</strong></div>
                  </div>
                </div>
              </div>
            </section>

            <section class="publish-page" data-publish-page="6">
              <div class="publish-launch-grid">
                <div class="publish-card-shell">
                  <div class="publish-card-heading">
                    <div class="publish-card-label">Connected Launch Ops<strong>Downstream release surfaces</strong></div>
                    <button class="card-badge" style="cursor:pointer;padding:3px 10px;font-size:10px;" onclick="loadLaunchPanel()">↺ Scan</button>
                  </div>
                  <div id="publishing-launch-books">
                    <div class="loading-state" style="text-align:left;padding:12px 0;font-size:12px;color:var(--text-3);">
                      Connect Ghostwritr and click Scan to see your books here.
                    </div>
                  </div>
                  <div id="publishing-launch-assets" style="display:none;margin-top:16px;">
                    <div class="publish-panel-shell">
                      <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
                        <strong id="launch-asset-title">Launch Assets</strong>
                        <div style="margin-left:auto;display:flex;gap:8px;">
                          <button class="btn btn-sm" style="font-size:10px;" onclick="regenerateLaunchAssets()">↺ Regenerate</button>
                          <button class="btn btn-sm" style="font-size:10px;" onclick="document.getElementById('publishing-launch-assets').style.display='none'">✕ Close</button>
                        </div>
                      </div>
                      <div style="display:flex;gap:2px;padding:0 0 12px;border-bottom:1px solid var(--border);overflow-x:auto;">
                        <button class="launch-tab active" data-tab="dispatch" onclick="switchLaunchTab(this,'dispatch')">📣 Dispatch</button>
                        <button class="launch-tab" data-tab="bureau" onclick="switchLaunchTab(this,'bureau')">📰 Bureau</button>
                        <button class="launch-tab" data-tab="marquee" onclick="switchLaunchTab(this,'marquee')">🏷️ Marquee</button>
                        <button class="launch-tab" data-tab="studio" onclick="switchLaunchTab(this,'studio')">🎙️ Studio</button>
                        <button class="launch-tab" data-tab="podium" onclick="switchLaunchTab(this,'podium')">🎓 Podium</button>
                        <button class="launch-tab" data-tab="lectern" onclick="switchLaunchTab(this,'lectern')">🎤 Lectern</button>
                        <button class="launch-tab" data-tab="twitter" onclick="switchLaunchTab(this,'twitter')">𝕏 Quick Social</button>
                        <button class="launch-tab" data-tab="amazon" onclick="switchLaunchTab(this,'amazon')">Quick Amazon</button>
                        <button class="launch-tab" data-tab="extended" onclick="switchLaunchTab(this,'extended')">Extended</button>
                      </div>
                      <div id="launch-asset-content" style="padding-top:16px;min-height:120px;"></div>
                    </div>
                  </div>
                </div>
                <div class="publish-card-shell">
                  <div class="publish-card-heading">
                    <div class="publish-card-label">JARVIS Supervisory Strip<strong>Who owns the downstream launch</strong></div>
                    <span class="publish-chip" id="launch-books-badge">—</span>
                  </div>
                  <div class="publish-launch-list" id="pub-launch-summary">
                    <div class="publish-launch-row"><span>Press Kit</span><strong>Waiting</strong></div>
                    <div class="publish-launch-row"><span>Speaking Kit</span><strong>Draft Ready</strong></div>
                    <div class="publish-launch-row"><span>Launch Listing</span><strong>Blocked</strong></div>
                    <div class="publish-launch-row"><span>Social Campaign</span><strong>Staged</strong></div>
                    <div class="publish-launch-row"><span>Retailer Manifest</span><strong>Pending</strong></div>
                  </div>
                  <button class="huddle-cta" type="button" onclick="loadLaunchPanel()">
                    <strong>Open Launch Ops Hub</strong>
                    <span>Scan the downstream Ghostwritr surfaces, refresh generated assets, and supervise the release package from one place.</span>
                  </button>
                </div>
              </div>
            </section>
          </div>

          <div class="publish-supervisor-strip">
            <div class="publish-supervisor-card"><strong>JARVIS</strong><span>Monitoring package integrity and handoff readiness.</span></div>
            <div class="publish-supervisor-card"><strong>Veronica</strong><span>Launch assets staged. Coordinating press kit and cover reveal.</span></div>
            <div class="publish-supervisor-card"><strong>Herald</strong><span>Speaking brief in review. Outline and key messages under evaluation.</span></div>
            <div class="publish-supervisor-card"><strong>Ghostwritr</strong><span>Source manuscript authority. Commits and versions remain the system of record.</span></div>
          </div>

          <div style="display:none;">
            <div class="view-section" style="margin-top:24px;">
              <div class="section-title-row">
                <h2 class="section-title">KDP · AMAZON PUBLISHING</h2>
                <div style="display:flex;gap:8px;align-items:center;">
                  <span id="kdp-view-status" style="font-size:11px;color:var(--text-3);">—</span>
                  <button class="card-action-btn" onclick="kdpViewSync()" id="kdp-sync-btn">↻ Sync</button>
                </div>
              </div>
              <div class="stats-strip" id="kdp-stats-strip">
                <div class="stat-tile"><div class="stat-value" id="kdp-stat-books">—</div><div class="stat-label">Books</div></div>
                <div class="stat-tile"><div class="stat-value" id="kdp-stat-units">—</div><div class="stat-label">Units Sold</div></div>
                <div class="stat-tile"><div class="stat-value" id="kdp-stat-kenp">—</div><div class="stat-label">KENP Reads</div></div>
                <div class="stat-tile"><div class="stat-value" id="kdp-stat-royalties">—</div><div class="stat-label">Royalties</div></div>
              </div>
              <div id="kdp-insights" style="margin:16px 0;display:none;"><div id="kdp-insights-list"></div></div>
              <div id="kdp-books-section" style="display:none;"><div id="kdp-books-list"></div></div>
              <div id="kdp-not-configured" style="text-align:center;padding:40px 20px;color:var(--text-3);">
                <div style="font-size:32px;margin-bottom:12px;">📚</div>
                <div style="font-size:14px;color:var(--text-2);margin-bottom:8px;">KDP not connected</div>
                <div style="font-size:12px;margin-bottom:16px;">Add your Amazon credentials in Settings → Accounts → KDP</div>
                <button class="card-action-btn" onclick="openSettings();settingsNavTo('accounts')">Open Settings</button>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  </div>

  <!-- ── FOUNDRY ────────────────────────────────────────────── -->
  <div id="view-foundry" class="view foundry-view">
    <div class="foundry-header">
      <div>
        <div class="foundry-kicker">Desktop Experience</div>
        <div class="view-title">JARVIS FOUNDRY<div class="view-title-line"></div></div>
        <div class="foundry-subtitle">A real creative and economic asset surface for active projects, publishing lanes, offers, audience signal, research dossiers, and launch readiness. One numbered Foundry page is active at a time, and every card now binds to live or honestly partial data.</div>
      </div>
      <div class="foundry-motto">
        <strong>Turn raw ideas into durable assets.</strong>
        <span>Shape. Ship. Compound trust and value without creating chaos.</span>
      </div>
    </div>

    <div class="foundry-stage">
      <div class="foundry-desktop-shell">
        <aside class="foundry-sidebar">
          <div class="foundry-brand-block">
            <div class="foundry-brand-mark">✦</div>
            <div>
              <div class="foundry-brand-title">JARVIS</div>
              <div class="foundry-brand-sub">Foundry</div>
            </div>
          </div>

          <div class="foundry-side-nav">
            <div class="foundry-side-link active" onclick="refreshFoundryDesktop(true)">⌂ Foundry Home</div>
            <div class="foundry-side-link" onclick="foundryCreateDraftProject()">＋ Quick Draft Project</div>
            <div class="foundry-side-link" onclick="foundryCreateIdea()">◉ Capture Idea</div>
            <div class="foundry-side-link" onclick="foundryOpenRoute('/publish', 'publishing', 'Open Publish', 'Foundry opened the publishing lane.')">✎ Publishing</div>
            <div class="foundry-side-link" onclick="foundryOpenRoute('/activity-center', 'journey', 'Open Activity', 'Foundry opened the activity timeline.')">◔ Activity</div>
            <div class="foundry-side-link" onclick="switchView('huddle')">◎ Huddle</div>
            <div class="foundry-side-link" onclick="switchView('workshop')">☼ Workshop</div>
            <div class="foundry-side-link" onclick="foundryOpenRoute('/chronicle-center', 'chronicle', 'Open Legacy', 'Foundry opened Legacy continuity.')">◍ Legacy</div>
            <div class="foundry-side-link" onclick="foundryOpenRoute('/settings-center', 'chat', 'Open Settings', 'Foundry opened settings.')">⚙ Settings</div>
          </div>

          <div class="foundry-sidebar-status">
            <strong>Foundry Status</strong>
            <div class="foundry-status-row"><span>Asset Health</span><span id="foundry-sidebar-health">Loading…</span></div>
            <div class="foundry-status-row"><span>Live Signal</span><span id="foundry-sidebar-signal">Loading…</span></div>
            <div class="foundry-status-row"><span>Last Update</span><span id="foundry-sidebar-refresh">Loading…</span></div>
            <div class="foundry-status-row"><span>Runtime Note</span><span id="foundry-runtime-note">Loading…</span></div>
            <button class="foundry-outline-btn" type="button" id="foundry-refresh-button" onclick="refreshFoundryDesktop(true)">Refresh Foundry ↻</button>
          </div>
        </aside>

        <main class="foundry-main">
          <div class="foundry-topbar">
            <div>
              <div class="foundry-topbar-kicker">Desktop Sequence</div>
              <div class="foundry-topbar-title" id="foundry-nav-title">1. Foundry Command Center</div>
              <div class="foundry-topbar-subtitle" id="foundry-nav-subtitle">Survey your creative and economic command center, see the highest-leverage work, and decide which asset deserves today’s making window.</div>
            </div>
            <div class="foundry-nav">
              <button class="foundry-nav-btn" id="foundry-nav-prev" onclick="advanceFoundryPage(-1)" aria-label="Previous Foundry page">←</button>
              <div class="foundry-nav-status">
                <div class="foundry-nav-page" id="foundry-page-count">Page 1 of 9</div>
                <div class="foundry-nav-title" id="foundry-page-label">Command Center</div>
              </div>
              <button class="foundry-nav-btn" id="foundry-nav-next" onclick="advanceFoundryPage(1)" aria-label="Next Foundry page">→</button>
            </div>
          </div>

          <div class="foundry-page-deck">
            <section class="foundry-page active">
              <div class="foundry-header-stats">
                <div class="foundry-stat-shell"><span>Active Assets</span><strong id="foundry-stat-assets">—</strong><small id="foundry-stat-assets-sub">Loading…</small></div>
                <div class="foundry-stat-shell"><span>Audience Reach</span><strong id="foundry-stat-reach">—</strong><small id="foundry-stat-reach-sub">Loading…</small></div>
                <div class="foundry-stat-shell"><span>Revenue Signal</span><strong id="foundry-stat-revenue">—</strong><small id="foundry-stat-revenue-sub">Loading…</small></div>
                <div class="foundry-stat-shell"><span>Shipped / Ready</span><strong id="foundry-stat-shipped">—</strong><small id="foundry-stat-shipped-sub">Loading…</small></div>
                <div class="foundry-profile-shell"><div class="foundry-profile-avatar">CB</div><div><strong>Chris Binion</strong><span>Founder Mode</span></div></div>
              </div>
              <div class="foundry-grid-two">
                <section class="foundry-card-shell">
                  <div class="foundry-card-heading">
                    <div class="foundry-card-label">Command Center<strong id="foundry-focus-title">Loading focus…</strong></div>
                    <button class="foundry-outline-btn" type="button" onclick="foundryOpenRoute('/command-center', 'chat', 'Open Command', 'Foundry opened the command deck.')">Open Command</button>
                  </div>
                  <div class="foundry-feature-card"><span>Lead Asset</span><strong id="foundry-focus-book">Foundry</strong><p id="foundry-focus-sub">Loading current asset lane…</p></div>
                  <div class="foundry-progress-row"><span>Progress</span><strong id="foundry-focus-pct">0%</strong></div>
                  <div class="foundry-progress-track"><div id="foundry-focus-bar" style="width:0%"></div></div>
                  <div class="foundry-quote-panel" id="foundry-command-narrative">Loading Foundry command narrative…</div>
                </section>
                <section class="foundry-card-shell">
                  <div class="foundry-card-heading">
                    <div class="foundry-card-label">Priority Lane<strong id="foundry-priority-title">Loading priority…</strong></div>
                    <button class="foundry-outline-btn" type="button" onclick="foundryOpenRoute('/publish', 'publishing', 'Open Publishing Hub', 'Foundry opened the publishing hub.')">Open Publishing Hub</button>
                  </div>
                  <div class="foundry-feature-card"><span>Why now</span><strong id="foundry-priority-date">Loading…</strong><p id="foundry-priority-copy">Loading priority context…</p></div>
                  <div class="foundry-progress-row"><span>Readiness</span><strong id="foundry-priority-pct">0%</strong></div>
                  <div class="foundry-progress-track"><div id="foundry-priority-bar" style="width:0%"></div></div>
                  <div class="foundry-side-stack">
                    <div class="foundry-micro-card"><span>Making Window</span><strong id="foundry-window-stat">—</strong></div>
                    <div class="foundry-micro-card"><span>Due Today</span><strong id="foundry-today-stat">—</strong><p id="foundry-today-sub">Loading…</p></div>
                    <div class="foundry-micro-card"><span>Incubator</span><strong id="foundry-idea-stat">—</strong><p id="foundry-idea-sub">Loading…</p></div>
                    <div class="foundry-micro-card"><span>Projects in Motion</span><strong id="foundry-progress-stat">—</strong><p id="foundry-progress-sub">Loading…</p></div>
                  </div>
                </section>
              </div>
              <div class="foundry-bottom-strip">
                <div class="foundry-bottom-pill"><strong>Economic Lens</strong><span id="foundry-economic-lens">Loading…</span></div>
                <div class="foundry-bottom-pill"><strong>Legacy Lens</strong><span id="foundry-legacy-lens">Loading…</span></div>
              </div>
            </section>

            <section class="foundry-page">
              <div class="foundry-grid-two">
                <section class="foundry-card-shell">
                  <div class="foundry-card-heading"><div class="foundry-card-label">Asset Pipeline<strong>From idea to compounding asset</strong></div></div>
                  <div class="foundry-pipeline-row">
                    <div class="foundry-pipeline-stage"><span>Idea</span><strong id="foundry-pipeline-idea">0</strong><small>Captured signals</small></div>
                    <div class="foundry-pipeline-arrow">→</div>
                    <div class="foundry-pipeline-stage"><span>Shape</span><strong id="foundry-pipeline-shape">0</strong><small>Research / structuring</small></div>
                    <div class="foundry-pipeline-arrow">→</div>
                    <div class="foundry-pipeline-stage"><span>Build</span><strong id="foundry-pipeline-build">0</strong><small>Active projects</small></div>
                    <div class="foundry-pipeline-arrow">→</div>
                    <div class="foundry-pipeline-stage"><span>Launch</span><strong id="foundry-pipeline-launch">0</strong><small>Review gates</small></div>
                    <div class="foundry-pipeline-arrow">→</div>
                    <div class="foundry-pipeline-stage"><span>Grow</span><strong id="foundry-pipeline-grow">0</strong><small>Revenue lanes</small></div>
                  </div>
                </section>
                <section class="foundry-card-shell">
                  <div class="foundry-card-heading"><div class="foundry-card-label">Asset Mix<strong>What is currently live</strong></div></div>
                  <div class="foundry-donut-shell">
                    <div class="foundry-donut-ring"><strong id="foundry-donut-total">0</strong><span>Assets</span></div>
                    <div class="foundry-type-list" id="foundry-asset-types"></div>
                  </div>
                </section>
              </div>
            </section>

            <section class="foundry-page">
              <div class="foundry-grid-two">
                <section class="foundry-card-shell">
                  <div class="foundry-card-heading"><div class="foundry-card-label">Portfolio Health<strong>Live posture, not guessed KPIs</strong></div></div>
                  <div class="foundry-score-shell">
                    <div class="foundry-score-ring"><strong id="foundry-health-score">—</strong><span id="foundry-health-copy">Loading…</span></div>
                    <div class="foundry-performance-list" id="foundry-health-strengths"></div>
                  </div>
                </section>
                <section class="foundry-card-shell">
                  <div class="foundry-card-heading"><div class="foundry-card-label">Performance Signals<strong>Actual published, revenue, and reach posture</strong></div></div>
                  <div class="foundry-performance-list" id="foundry-performance-list"></div>
                </section>
              </div>
            </section>

            <section class="foundry-page">
              <section class="foundry-card-shell">
                <div class="foundry-card-heading">
                  <div class="foundry-card-label">Active Projects<strong>What is already in motion</strong></div>
                  <button class="foundry-outline-btn" type="button" onclick="foundryCreateDraftProject()">Quick Draft Project</button>
                </div>
                <div class="foundry-project-list" id="foundry-projects-list"></div>
              </section>
            </section>

            <section class="foundry-page">
              <div class="foundry-grid-two">
                <section class="foundry-card-shell">
                  <div class="foundry-card-heading">
                    <div class="foundry-card-label">Content & Publishing Hub<strong>Books, drafts, and review gates</strong></div>
                    <button class="foundry-outline-btn" type="button" onclick="foundryOpenRoute('/publish', 'publishing', 'Open Publishing Workspace', 'Foundry opened the publishing workspace.')">Open Publishing</button>
                  </div>
                  <div class="foundry-publishing-list" id="foundry-publishing-list"></div>
                </section>
                <section class="foundry-card-shell">
                  <div class="foundry-card-heading"><div class="foundry-card-label">Repurposing Window<strong id="foundry-opportunity-title">Loading…</strong></div></div>
                  <div class="foundry-opportunity-panel"><strong>Next leverage move</strong><p id="foundry-opportunity-copy">Loading repurposing opportunity…</p></div>
                </section>
              </div>
            </section>

            <section class="foundry-page">
              <div class="foundry-grid-two">
                <section class="foundry-card-shell">
                  <div class="foundry-card-heading"><div class="foundry-card-label">Offers & Revenue Lab<strong>Economic lanes attached to the work</strong></div></div>
                  <div class="foundry-offers-list" id="foundry-offers-list"></div>
                </section>
                <section class="foundry-card-shell">
                  <div class="foundry-card-heading"><div class="foundry-card-label">Revenue Note<strong>Live monetization posture</strong></div></div>
                  <div class="foundry-opportunity-panel"><strong>Revenue context</strong><p id="foundry-offers-note">Loading revenue note…</p></div>
                </section>
              </div>
            </section>

            <section class="foundry-page">
              <div class="foundry-grid-two">
                <section class="foundry-card-shell">
                  <div class="foundry-card-heading"><div class="foundry-card-label">Audience Intelligence<strong>Live signal only</strong></div></div>
                  <div class="foundry-audience-hero"><strong id="foundry-audience-total">—</strong><span id="foundry-audience-growth">Loading audience signal…</span></div>
                </section>
                <section class="foundry-card-shell">
                  <div class="foundry-card-heading"><div class="foundry-card-label">Audience / Platform Segments<strong>Where signal is showing up</strong></div></div>
                  <div class="foundry-segment-list" id="foundry-segment-list"></div>
                </section>
              </div>
            </section>

            <section class="foundry-page">
              <div class="foundry-grid-two">
                <section class="foundry-card-shell">
                  <div class="foundry-card-heading">
                    <div class="foundry-card-label">Idea Incubator<strong>Raw material moving toward assets</strong></div>
                    <button class="foundry-outline-btn" type="button" onclick="foundryCreateIdea()">Capture Idea</button>
                  </div>
                  <div class="foundry-idea-list" id="foundry-idea-list"></div>
                </section>
                <section class="foundry-card-shell">
                  <div class="foundry-card-heading"><div class="foundry-card-label">Dossiers<strong>Research close to the build path</strong></div></div>
                  <div class="foundry-dossier-list" id="foundry-dossier-list"></div>
                </section>
              </div>
            </section>

            <section class="foundry-page">
              <div class="foundry-grid-two">
                <section class="foundry-card-shell">
                  <div class="foundry-card-heading">
                    <div class="foundry-card-label">Launch & Campaign Control<strong>What is close to shipping</strong></div>
                    <button class="foundry-outline-btn" type="button" onclick="foundryOpenRoute('/publish', 'publishing', 'Open Launch Control', 'Foundry opened launch control.')">Open Launch Control</button>
                  </div>
                  <div class="foundry-launch-list" id="foundry-launch-list"></div>
                </section>
                <section class="foundry-card-shell">
                  <div class="foundry-card-heading"><div class="foundry-card-label">Launch Readiness<strong id="foundry-launch-score">Loading…</strong></div></div>
                  <div class="foundry-opportunity-panel"><strong id="foundry-launch-copy">Loading launch posture…</strong></div>
                  <div class="foundry-performance-list" id="foundry-launch-checklist" style="margin-top:12px;"></div>
                </section>
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  </div>

  <!-- ── WORKSHOP ───────────────────────────────────────────── -->
  <div id="view-workshop" class="view foundry-view workshop-view">
    <div class="foundry-header">
      <div>
        <div class="foundry-kicker">Desktop Experience</div>
        <div class="view-title">JARVIS WORKSHOP<div class="view-title-line"></div></div>
        <div class="foundry-subtitle">Agentic task management and execution system. This is the operational work board for active tasks, delegated work orders, blockers, quick actions, resumption, and capacity shaping.</div>
      </div>
      <div class="foundry-motto">
        <strong>Well-ordered work creates freedom.</strong>
        <span>Chaos creates fatigue.</span>
      </div>
    </div>

    <div class="foundry-stage">
      <div class="foundry-desktop-shell">
        <aside class="foundry-sidebar">
          <div class="foundry-brand-block">
            <div class="foundry-brand-mark">☼</div>
            <div>
              <div class="foundry-brand-title">JARVIS</div>
              <div class="foundry-brand-sub">Workshop</div>
            </div>
          </div>

          <div class="foundry-side-nav">
            <div class="foundry-side-link active" onclick="refreshWorkshopDesktop(true)">⌂ Workshop Home</div>
            <div class="foundry-side-link" onclick="workshopOpenRoute('/command-center', 'chat', 'Open Command', 'Workshop opened the command lane.')">◈ Command</div>
            <div class="foundry-side-link" onclick="switchView('overview')">☰ Daily Brief</div>
            <div class="foundry-side-link" onclick="workshopOpenRoute('/mission-board', 'workshop', 'Open Mission Board', 'Workshop opened the mission board.')">◎ Mission Board</div>
            <div class="foundry-side-link" onclick="switchView('agents')">◉ Agents</div>
            <div class="foundry-side-link" onclick="workshopOpenRoute('/approval-queue', 'approvals', 'Open Approvals', 'Workshop opened the approval queue.')">↯ Approvals</div>
            <div class="foundry-side-link" onclick="workshopOpenRoute('/supervision-snapshot', 'supervision', 'Open Supervision', 'Workshop opened supervision.')">◌ Supervision</div>
            <div class="foundry-side-link" onclick="workshopOpenRoute('/activity-center', 'activity', 'Open Activity', 'Workshop opened the activity lane.')">◔ Activity</div>
            <div class="foundry-side-link" onclick="switchView('workshop')">✦ Foundry</div>
            <div class="foundry-side-link" onclick="switchView('publishing')">✎ Publish</div>
            <div class="foundry-side-link" onclick="switchView('chronicle')">◍ Legacy</div>
            <div class="foundry-side-link" onclick="workshopOpenRoute('/settings-center', 'chat', 'Open Settings', 'Workshop opened settings.')">⚙ Settings</div>
          </div>

          <div class="foundry-sidebar-status">
            <strong>Workshop Status</strong>
            <div class="foundry-status-row"><span>System Health</span><span id="workshop-sidebar-health">Loading…</span></div>
            <div class="foundry-status-row"><span>Queue Health</span><span id="workshop-sidebar-queue">Loading…</span></div>
            <div class="foundry-status-row"><span>Last Update</span><span id="workshop-sidebar-refresh">Loading…</span></div>
            <div class="foundry-status-row"><span>Runtime Note</span><span id="workshop-runtime-note">Loading…</span></div>
            <button class="foundry-outline-btn" type="button" onclick="refreshWorkshopDesktop(true)">Workshop Settings ↻</button>
          </div>
        </aside>

        <main class="foundry-main">
          <div class="foundry-topbar">
            <div class="foundry-topbar-copy">
              <div class="foundry-topbar-kicker">Desktop Sequence</div>
              <div class="foundry-topbar-title" id="workshop-nav-title">Workshop Board</div>
              <div class="foundry-topbar-subtitle" id="workshop-nav-subtitle">Overview all work across your world, organize by state, surface active orders, and keep today’s execution lane visible.</div>
            </div>
            <div class="foundry-nav">
              <button class="foundry-nav-btn" id="workshop-nav-prev" onclick="advanceWorkshopPage(-1)" aria-label="Previous Workshop page">←</button>
              <div class="foundry-nav-status">
                <div class="foundry-nav-page" id="workshop-page-count">Page 1 of 1</div>
                <div class="foundry-nav-title" id="workshop-page-label">Workshop Board</div>
              </div>
              <button class="foundry-nav-btn" id="workshop-nav-next" onclick="advanceWorkshopPage(1)" aria-label="Next Workshop page">→</button>
            </div>
          </div>

          <div class="workshop-header-stats">
            <div class="workshop-stat-shell"><span>Work In Progress</span><strong id="workshop-stat-wip">—</strong><small id="workshop-stat-wip-sub">Loading</small></div>
            <div class="workshop-stat-shell"><span>Completed Today</span><strong id="workshop-stat-completed">—</strong><small id="workshop-stat-completed-sub">Loading</small></div>
            <div class="workshop-stat-shell"><span>Awaiting Review</span><strong id="workshop-stat-review">—</strong><small id="workshop-stat-review-sub">Loading</small></div>
            <div class="workshop-stat-shell"><span>Blocked</span><strong id="workshop-stat-blocked">—</strong><small id="workshop-stat-blocked-sub">Loading</small></div>
            <div class="workshop-stat-shell"><span>Due Today</span><strong id="workshop-stat-due">—</strong><small id="workshop-stat-due-sub">Loading</small></div>
            <div class="workshop-quote-shell"><blockquote>“Well-ordered work creates freedom. Chaos creates fatigue.”</blockquote><p>Workshop turns the live task surface into a governed execution board.</p></div>
            <div class="workshop-profile-shell"><div class="workshop-profile-avatar">CB</div><div><strong>Chris Binion</strong><span>Executive Mode</span></div></div>
          </div>

          <div class="workshop-grid">
            <section class="workshop-card span-4">
              <div class="workshop-card-inner">
                <div class="workshop-card-header">
                  <div><div class="workshop-card-number">1. Workshop Command Center</div><h3>Overview of all work across your world.</h3></div>
                  <button class="workshop-outline-btn" type="button" onclick="workshopOpenRoute('/settings-center', 'chat', 'Customize Workshop', 'Workshop opened settings to customize this view.')">Customize View</button>
                </div>
                <div class="workshop-command-grid" id="workshop-command-grid"></div>
                <div class="workshop-mini-grid" id="workshop-balance-grid" style="margin-top:14px;"></div>
              </div>
            </section>

            <section class="workshop-card span-5">
              <div class="workshop-card-inner">
                <div class="workshop-card-header">
                  <div><div class="workshop-card-number">2. Work Board</div><h3>Work organized by state.</h3><p>Drag, drop, and move forward. The board is assembled from live tasks, missions, reviews, and open loops.</p></div>
                </div>
                <div class="workshop-board" id="workshop-board"></div>
              </div>
            </section>

            <section class="workshop-card span-3">
              <div class="workshop-card-inner">
                <div class="workshop-card-header">
                  <div><div class="workshop-card-number">3. Active Work Orders</div><h3>Deep view of major work threads.</h3></div>
                  <button class="workshop-view-link" type="button" onclick="workshopOpenRoute('/mission-board', 'workshop', 'Open Work Orders', 'Workshop opened the mission board work orders.')">View All</button>
                </div>
                <div class="workshop-work-orders" id="workshop-work-orders"></div>
              </div>
            </section>

            <section class="workshop-card span-4">
              <div class="workshop-card-inner">
                <div class="workshop-card-header">
                  <div><div class="workshop-card-number">4. Delegation Queue</div><h3>What your agents are working on.</h3></div>
                  <button class="workshop-view-link" type="button" onclick="switchView('agents')">View All Agents</button>
                </div>
                <div class="workshop-list-stack" id="workshop-delegation-list"></div>
              </div>
            </section>

            <section class="workshop-card span-3">
              <div class="workshop-card-inner">
                <div class="workshop-card-header">
                  <div><div class="workshop-card-number">5. Blockers & Escalations</div><h3>Items preventing movement.</h3></div>
                  <button class="workshop-view-link" type="button" onclick="workshopOpenRoute('/supervision-snapshot', 'supervision', 'Resolve Blockers', 'Workshop opened supervision for blocker resolution.')">Resolve All</button>
                </div>
                <div class="workshop-list-stack" id="workshop-blockers-list"></div>
              </div>
            </section>

            <section class="workshop-card span-3">
              <div class="workshop-card-inner">
                <div class="workshop-card-header">
                  <div><div class="workshop-card-number">6. Today&apos;s Execution Lane</div><h3>Your highest-leverage moves.</h3></div>
                  <button class="workshop-view-link" type="button" onclick="switchView('overview')">Optimize Day</button>
                </div>
                <div class="workshop-execution-lane" id="workshop-execution-lane"></div>
              </div>
            </section>

            <section class="workshop-card span-2">
              <div class="workshop-card-inner">
                <div class="workshop-card-header">
                  <div><div class="workshop-card-number">7. Task Intelligence</div><h3>Insights to help you work smarter.</h3></div>
                </div>
                <div class="workshop-list-stack" id="workshop-intelligence-list"></div>
              </div>
            </section>

            <section class="workshop-card span-4">
              <div class="workshop-card-inner">
                <div class="workshop-card-header">
                  <div><div class="workshop-card-number">8. Resumption Timeline</div><h3>What happened while you were away.</h3></div>
                </div>
                <div class="workshop-timeline" id="workshop-resumption-timeline"></div>
              </div>
            </section>

            <section class="workshop-card span-3">
              <div class="workshop-card-inner">
                <div class="workshop-card-header">
                  <div><div class="workshop-card-number">9. Quick Actions</div><h3>Common moves. One click.</h3></div>
                </div>
                <div class="workshop-quick-grid" id="workshop-quick-actions"></div>
              </div>
            </section>

            <section class="workshop-card span-3">
              <div class="workshop-card-inner">
                <div class="workshop-card-header">
                  <div><div class="workshop-card-number">10. Workload & Capacity</div><h3>Where capacity is tight or free.</h3></div>
                  <button class="workshop-view-link" type="button" onclick="switchView('health')">Optimize Day</button>
                </div>
                <div class="workshop-capacity-grid">
                  <div class="workshop-list-stack" id="workshop-capacity-list"></div>
                  <div class="workshop-panel">
                    <strong>Capacity Recommendation</strong>
                    <span id="workshop-capacity-recommendation">Loading capacity guidance…</span>
                    <button class="workshop-outline-btn" type="button" style="margin-top:12px;" onclick="switchView('command')">Rebalance Work</button>
                  </div>
                </div>
              </div>
            </section>

            <section class="workshop-card span-3">
              <div class="workshop-card-inner">
                <div class="workshop-card-header">
                  <div><div class="workshop-card-number">11. Workflow Templates</div><h3>Reusable systems for repeatable work.</h3></div>
                  <button class="workshop-view-link" type="button" onclick="switchView('forge')">View All</button>
                </div>
                <div class="workshop-templates" id="workshop-template-list"></div>
              </div>
            </section>
          </div>

          <div class="workshop-footer-strip" id="workshop-footer-strip"></div>
        </main>
      </div>
    </div>
  </div>

  <!-- ── HUDDLE ─────────────────────────────────────────────── -->
  <div id="view-huddle" class="view huddle-view">
    <div class="huddle-header">
      <div>
        <div class="huddle-kicker">Desktop Experience</div>
        <div class="view-title">HUDDLE INTELLIGENCE<div class="view-title-line"></div></div>
        <div class="huddle-subtitle">A real desktop Huddle workspace for council formation, party-mode problem solving, mission board review, and coordinated delegate-back execution. One screen is active at a time, with arrows and a page count carrying the sequence.</div>
      </div>
      <div class="huddle-motto">
        <strong>Bring the council together.</strong>
        <span>Surface the problem, orchestrate the agents, pressure-test the plan, and send the coordinated work back out.</span>
      </div>
    </div>

    <div class="huddle-desktop-stage">
      <div class="huddle-desktop-shell">
        <aside class="huddle-rail">
          <div class="huddle-rail-brand">✦</div>
          <div class="huddle-rail-stack">
            <button class="huddle-rail-icon active" type="button" data-huddle-nav="1" onclick="setHuddlePage(1)" aria-label="Open council chamber">⌂</button>
            <button class="huddle-rail-icon" type="button" data-huddle-nav="2" onclick="setHuddlePage(2)" aria-label="Open party mode">☰</button>
            <button class="huddle-rail-icon" type="button" data-huddle-nav="3" onclick="setHuddlePage(3)" aria-label="Open mission board">⚡</button>
            <button class="huddle-rail-icon" type="button" data-huddle-nav="4" onclick="setHuddlePage(4)" aria-label="Open delegate back out">◎</button>
            <div class="huddle-rail-icon">✎</div>
            <div class="huddle-rail-icon">⬡</div>
            <div class="huddle-rail-icon">⚙</div>
          </div>
          <div class="module-runtime-note" id="huddle-runtime-note">Loading Huddle surface…</div>
        </aside>

        <main class="huddle-main">
          <div class="huddle-topbar">
            <div class="huddle-topbar-copy">
              <div class="huddle-topbar-kicker">Desktop Sequence</div>
              <div class="huddle-topbar-title" id="huddle-nav-title">1. Agent Council Chamber</div>
              <div class="huddle-topbar-subtitle" id="huddle-nav-subtitle">Survey the council roster, see who is online, and convene the room before the problem-solving session begins.</div>
            </div>
            <div class="huddle-nav">
              <button class="huddle-nav-btn" id="huddle-nav-prev" onclick="advanceHuddlePage(-1)" aria-label="Previous Huddle page">←</button>
              <div class="huddle-nav-status">
                <div class="huddle-nav-page" id="huddle-page-count">Page 1 of 4</div>
                <div class="huddle-nav-title" id="huddle-page-label">Council Chamber</div>
              </div>
              <button class="huddle-nav-btn" id="huddle-nav-next" onclick="advanceHuddlePage(1)" aria-label="Next Huddle page">→</button>
            </div>
          </div>

          <div class="huddle-page-deck">
            <section class="huddle-page active" data-huddle-page="1">
              <div class="huddle-grid-hero">
                <div class="huddle-card-shell">
                  <div class="huddle-card-heading">
                    <div class="huddle-card-label">Council Roster<strong>Who is in the room</strong></div>
                    <button class="huddle-refresh-btn" id="huddle-refresh-button" onclick="refreshHuddleDesktop(true)">↺ Refresh Huddle</button>
                  </div>
                  <div class="huddle-council-roster" id="huddle-council-roster">
                    <div class="skel" style="height:58px;border-radius:14px;"></div>
                    <div class="skel" style="height:58px;border-radius:14px;"></div>
                    <div class="skel" style="height:58px;border-radius:14px;"></div>
                  </div>
                </div>
                <div class="huddle-card-shell">
                  <div class="huddle-card-heading">
                    <div class="huddle-card-label">Agent Council Chamber<strong>Convene the room</strong></div>
                    <span class="huddle-chip live" id="huddle-active-work">— active items</span>
                  </div>
                  <div class="huddle-council-core">
                    <div class="huddle-council-perimeter" id="huddle-council-perimeter"></div>
                    <div class="huddle-council-ring">
                      <strong>JARVIS</strong>
                      <span id="huddle-council-status">Council online</span>
                      <div class="huddle-council-wave"></div>
                    </div>
                  </div>
                  <div class="huddle-call-row">
                    <div style="font-size:24px;">◔</div>
                    <div style="flex:1;">
                      <strong>Call a Huddle</strong>
                      <span>Press to convene the council, begin party mode, and move the agents into coordinated reasoning.</span>
                    </div>
                    <button class="party-bar-btn" onclick="startPartyMode()">⚡ Wake the Agents</button>
                  </div>
                </div>
              </div>
            </section>

            <section class="huddle-page" data-huddle-page="2">
              <div class="huddle-party-grid">
                <div class="huddle-card-shell">
                  <div class="huddle-card-heading">
                    <div class="huddle-card-label">Party Mode: Problem Solve<strong id="huddle-party-problem-title">Active problem</strong></div>
                    <span class="huddle-chip warn" id="huddle-blockers-count">— blockers</span>
                  </div>
                  <div class="huddle-mini-shell" id="party-mode-bar" style="display:none">
                    <span class="party-bar-indicator"></span>
                    <span id="party-bar-text">Agents working...</span>
                    <button class="party-bar-btn" onclick="startPartyMode()">⚡ Wake the Agents</button>
                  </div>
                  <div class="huddle-panel-shell" id="huddle-party-problem-copy" style="margin-top:12px;">
                    Party mode is standing by. Pick an active approval, blocker, or dossier to give the council a central problem to solve.
                  </div>
                  <div class="huddle-problem-core">
                    <div class="huddle-council-ring">
                      <strong id="huddle-party-progress">73%</strong>
                      <span id="huddle-party-progress-copy">Converging solutions</span>
                      <div class="huddle-council-wave"></div>
                    </div>
                  </div>
                </div>
                <div class="huddle-card-shell">
                  <div class="huddle-card-heading">
                    <div class="huddle-card-label">Live Debate &amp; Dossiers<strong>Proposals under review</strong></div>
                    <span class="huddle-chip" id="huddle-approvals-count">— awaiting approval</span>
                  </div>
                  <div id="dossier-section">
                    <div id="huddle-dossier-grid" class="dossier-grid">
                      <div class="skeleton-block" style="height:120px;border-radius:8px;"></div>
                    </div>
                  </div>
                  <div id="huddle-approvals" style="margin-top:14px;display:none;">
                    <div id="huddle-approvals-list" class="huddle-approval-list"></div>
                  </div>
                </div>
                <div class="huddle-card-shell">
                  <div class="huddle-card-heading">
                    <div class="huddle-card-label">Synthesis Risks<strong>What could break the plan</strong></div>
                  </div>
                  <div class="huddle-party-risk-list" id="huddle-party-risk-list">
                    <div class="huddle-mini-row"><span>Waiting on party mode</span><strong>Standby</strong></div>
                  </div>
                </div>
              </div>
            </section>

            <section class="huddle-page" data-huddle-page="3">
              <div class="huddle-card-shell">
                <div class="huddle-card-heading">
                  <div class="huddle-card-label">Agent Report-In + Mission Board<strong>Standups, pipeline, and captured ideas</strong></div>
                  <span class="huddle-chip" id="idea-inbox-counts">—</span>
                </div>
                <div class="huddle-mission-columns" id="huddle-mission-columns">
                  <div class="huddle-mission-col"><h4>Completed</h4><span>Loading…</span></div>
                  <div class="huddle-mission-col"><h4>Watching</h4><span>Loading…</span></div>
                  <div class="huddle-mission-col"><h4>Needs You</h4><span>Loading…</span></div>
                  <div class="huddle-mission-col"><h4>Escalated</h4><span>Loading…</span></div>
                  <div class="huddle-mission-col"><h4>Ready to Deploy</h4><span>Loading…</span></div>
                </div>
              </div>

              <div class="huddle-grid-two">
                <div class="huddle-card-shell">
                  <div class="huddle-card-heading">
                    <div class="huddle-card-label">Passive Income Pipeline<strong>Workstreams moving in the background</strong></div>
                  </div>
                  <div id="huddle-pi-pipeline" class="pi-pipeline-grid">
                    <div class="skeleton-block" style="height:80px;border-radius:8px;"></div>
                  </div>
                </div>
                <div class="huddle-card-shell" id="idea-inbox-section">
                  <div class="huddle-card-heading">
                    <div class="huddle-card-label">Idea Inbox<strong>Capture or import a mission seed</strong></div>
                    <button class="party-bar-btn" onclick="showIdeaAddModal()">+ New Idea</button>
                  </div>
                  <div style="display:flex;gap:8px;margin-bottom:8px;">
                    <input type="text" id="huddle-idea-input"
                      placeholder="Describe an idea — JARVIS will research it and return a full dossier..."
                      style="flex:1;padding:10px 14px;border:1px solid var(--border);border-radius:8px;background:var(--surface-hi);font-size:13px;color:var(--text-1);outline:none;"
                      onkeydown="if(event.key==='Enter')huddleAddIdea()">
                    <button class="btn-primary" onclick="huddleAddIdea()">Capture</button>
                  </div>
                  <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap;">
                    <input type="file" id="huddle-bulk-import-input" accept=".docx,.txt,.md,.json,.csv"
                      style="display:none;" onchange="huddleBulkImport(this)">
                    <button class="party-bar-btn" style="font-size:11px;padding:4px 12px;"
                      onclick="document.getElementById('huddle-bulk-import-input').click()">📄 Import from File</button>
                    <select id="huddle-bulk-domain"
                      style="padding:4px 8px;border:1px solid var(--border);border-radius:6px;background:var(--surface-hi);color:var(--text-1);font-size:11px;outline:none;">
                      <option value="passive-income">Passive Income</option>
                      <option value="publishing">Publishing / Books</option>
                      <option value="software">Software</option>
                      <option value="creative">Creative</option>
                      <option value="personal">Personal</option>
                      <option value="general">General</option>
                    </select>
                    <div id="huddle-bulk-status" style="font-size:11px;color:var(--text-3);display:none;margin-left:4px;"></div>
                  </div>
                  <div style="display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap;" id="idea-filter-pills">
                    <button class="idea-filter-pill active" data-status="" onclick="setIdeaFilter(this,'')">All</button>
                    <button class="idea-filter-pill" data-status="captured" onclick="setIdeaFilter(this,'captured')">Captured</button>
                    <button class="idea-filter-pill" data-status="queued" onclick="setIdeaFilter(this,'queued')">Queued</button>
                    <button class="idea-filter-pill" data-status="researching" onclick="setIdeaFilter(this,'researching')">Researching</button>
                    <button class="idea-filter-pill" data-status="done" onclick="setIdeaFilter(this,'done')">Done ✓</button>
                    <button class="idea-filter-pill" data-status="passed" onclick="setIdeaFilter(this,'passed')">Passed</button>
                  </div>
                  <div id="idea-inbox-list" style="display:flex;flex-direction:column;gap:8px;">
                    <div style="color:var(--text-3);font-size:12px;padding:12px 0;">Loading ideas...</div>
                  </div>
                </div>
              </div>

              <div class="huddle-card-shell">
                <div class="huddle-card-heading">
                  <div class="huddle-card-label">Agent Standups<strong>What every agent said they did, need, and plan next</strong></div>
                </div>
                <div id="huddle-reports-grid" class="huddle-grid">
                  <div class="skeleton-block" style="height:140px;border-radius:8px;"></div>
                  <div class="skeleton-block" style="height:140px;border-radius:8px;"></div>
                  <div class="skeleton-block" style="height:140px;border-radius:8px;"></div>
                </div>
              </div>
            </section>

            <section class="huddle-page" data-huddle-page="4">
              <div class="huddle-resolution-grid">
                <div class="huddle-card-shell">
                  <div class="huddle-card-heading">
                    <div class="huddle-card-label">Resolution &amp; Delegate Back Out<strong>Coordinated plan</strong></div>
                    <span class="huddle-chip live" id="huddle-plan-confidence">Plan forming</span>
                  </div>
                  <div class="huddle-panel-shell" id="huddle-resolution-summary">
                    Coordinated summary will appear here as dossiers, approvals, and the active problem come into focus.
                  </div>
                  <div class="huddle-grid-three" style="margin-top:14px;">
                    <div class="huddle-mini-shell"><strong>Confidence</strong><p id="huddle-resolution-confidence">—</p></div>
                    <div class="huddle-mini-shell"><strong>Success Probability</strong><p id="huddle-resolution-success">—</p></div>
                    <div class="huddle-mini-shell"><strong>Collateral Risk</strong><p id="huddle-resolution-risk">—</p></div>
                  </div>
                  <div class="huddle-mini-list" id="huddle-plan-pillars" style="margin-top:14px;">
                    <div class="huddle-mini-row"><span>Waiting</span><strong>Bring the council together</strong></div>
                  </div>
                </div>
                <div class="huddle-card-shell">
                  <div class="huddle-card-heading">
                    <div class="huddle-card-label">Delegate Back to Agents<strong>Who owns the next move</strong></div>
                  </div>
                  <div class="huddle-delegate-list" id="huddle-delegate-list">
                    <div class="huddle-delegate-row"><span>Waiting for live roster</span><strong>Standby</strong></div>
                  </div>
                  <button class="huddle-cta" type="button" onclick="startPartyMode()">
                    <strong>Launch Coordinated Plan</strong>
                    <span>All systems synchronized. Wake the agents, generate the next dossier set, and move execution back into the field.</span>
                  </button>
                </div>
              </div>
              <div class="huddle-quick-status" id="huddle-quick-status">
                <div class="huddle-quick-pill"><strong>Loading…</strong><span>—</span></div>
              </div>
            </section>
          </div>

        </main>
      </div>
    </div>
  </div>

  <!-- ── AGENTS ─────────────────────────────────────────────── -->
  <div id="view-agents" class="view agents-view">
    <div class="agents-shell">
      <div class="agents-headline">
        <div>
          <div class="agents-kicker">Desktop Experience</div>
          <h1>JARVIS <span>AGENTS</span></h1>
          <p>Your intelligent staff. Working for your mission. The council, handoffs, supervision posture, and deploy surface now live together in one desktop board instead of a hidden runtime utility.</p>
        </div>
      </div>

      <div class="agents-topbar">
        <div class="agents-statbar">
          <div class="agents-stat"><strong id="agents-stat-active">—</strong><span>Agents Active</span></div>
          <div class="agents-stat"><strong id="agents-stat-tasks">—</strong><span>Tasks In Progress</span></div>
          <div class="agents-stat"><strong id="agents-stat-review">—</strong><span>Awaiting Your Review</span></div>
          <div class="agents-stat"><strong id="agents-stat-decisions">—</strong><span>Decisions Due Today</span></div>
          <div class="agents-stat"><strong id="agents-stat-health">—</strong><span>System Health</span></div>
        </div>
        <div class="agents-quote-card">
          <blockquote>“The right people. In the right place. At the right time.”</blockquote>
          <p>JARVIS keeps the staff organized, supervised, and delegated against your actual mission load.</p>
        </div>
        <div class="agents-profile-card">
          <div class="agents-profile-avatar">CB</div>
          <div>
            <strong>Chris Binion</strong>
            <span>Executive / Builder</span>
          </div>
        </div>
      </div>

      <div class="agents-sequence-bar">
            <div class="agents-sequence-copy">
              <strong id="agents-nav-title">Agents Board</strong>
              <span id="agents-nav-subtitle">Council, activity, trust, deployment, and staff performance are all visible in one desktop operating surface.</span>
            </div>
            <div class="agents-sequence-controls">
              <button id="agents-refresh-button" class="agents-sequence-btn" type="button" onclick="refreshAgentsDesktop()">↺</button>
              <button id="agents-nav-prev" class="agents-sequence-btn" type="button" onclick="advanceAgentsPage(-1)">←</button>
              <div class="agents-sequence-page">
                <div id="agents-page-count">Page 1 of 1</div>
                <div id="agents-page-label">Agents Board</div>
              </div>
          <button id="agents-nav-next" class="agents-sequence-btn" type="button" onclick="advanceAgentsPage(1)">→</button>
        </div>
      </div>

      <div class="agents-desktop-shell">
        <aside class="agents-sidebar">
          <div class="agents-sidebar-brand">
            <div class="agents-sidebar-orb">✦</div>
            <strong>JARVIS</strong>
            <span>AGENTS</span>
          </div>
          <div class="agents-side-nav">
            <div class="agents-side-link active" onclick="agentsOpenRoute('command', 'Open Command', 'Opening the command surface from Agents.')">Command</div>
            <div class="agents-side-link" onclick="agentsOpenRoute('overview', 'Open Daily Brief', 'Opening Daily Brief from Agents.')">Daily Brief</div>
            <div class="agents-side-link" onclick="agentsOpenRoute('mission', 'Open Mission Board', 'Opening Mission Board from Agents.')">Mission Board</div>
            <div class="agents-side-link" onclick="agentsOpenRoute('approvals', 'Open Approvals', 'Opening Approvals from Agents.')">Approvals</div>
            <div class="agents-side-link" onclick="agentsOpenRoute('supervision', 'Open Supervision', 'Opening Supervision from Agents.')">Supervision</div>
            <div class="agents-side-link" onclick="agentsOpenRoute('activity', 'Open Activity', 'Opening Activity from Agents.')">Activity</div>
            <div class="agents-side-link" onclick="agentsOpenRoute('workshop', 'Open Workshop', 'Opening Workshop from Agents.')">Workshop</div>
            <div class="agents-side-link" onclick="agentsOpenRoute('publish', 'Open Publish', 'Opening Publish from Agents.')">Publish</div>
            <div class="agents-side-link" onclick="agentsOpenRoute('chronicle', 'Open Legacy', 'Opening Legacy from Agents.')">Legacy</div>
            <div class="agents-side-link" onclick="agentsOpenRoute('navigation', 'Open Navigation', 'Opening Navigation from Agents.')">Navigation</div>
            <div class="agents-side-link" onclick="agentsOpenRoute('health', 'Open Health', 'Opening Health from Agents.')">Health</div>
            <div class="agents-side-link" onclick="agentsOpenRoute('settings', 'Open Settings', 'Opening Settings from Agents.')">Settings</div>
          </div>
          <div class="agents-sidebar-foot">
            <div class="agents-status-card">
              <strong>Agent System Status</strong>
              <span id="agent-roster-count">— agents online in the council roster.</span>
              <span id="agents-sidebar-sync">System sync loading…</span>
              <span id="agents-sidebar-updated">Last update: —</span>
              <span id="agents-runtime-note">Loading live Agents context…</span>
            </div>
            <div class="agents-status-card">
              <strong>Agent OS Overview</strong>
              <span>Bounded autonomy stays visible here: who is active, who is waiting, what needs your authority, and what is ready to deploy.</span>
            </div>
          </div>
        </aside>

        <main class="agents-main">
          <div class="agents-grid">
            <section class="agents-card span-8">
              <div class="agents-card-inner">
                <div class="agents-card-header">
                  <div class="agents-card-number">1. The Council</div>
                  <h3>Your executive staff.</h3>
                  <p>Specialized minds. Shared mission. Live runtime and mission-role context shape the council instead of a static card wall.</p>
                </div>
                <div class="agents-chip-row">
                  <div class="agents-status-chip"><strong id="agents-chip-active">—</strong><span>Active</span></div>
                  <div class="agents-status-chip"><strong id="agents-chip-watching">—</strong><span>Watching</span></div>
                  <div class="agents-status-chip"><strong id="agents-chip-waiting">—</strong><span>Waiting On You</span></div>
                  <div class="agents-status-chip"><strong id="agents-chip-blocked">—</strong><span>Blocked</span></div>
                  <div class="agents-status-chip"><strong id="agents-chip-offline">—</strong><span>Offline</span></div>
                </div>
                <div class="agents-council-grid" id="agents-council-grid"></div>
                <div class="agents-action-link" onclick="filterAgents('all')">View all agents →</div>
              </div>
            </section>

            <section class="agents-card span-4">
              <div class="agents-card-inner">
                <div class="agents-card-header">
                  <div class="agents-card-number">2. Agent Details</div>
                  <h3>Selected agent profile.</h3>
                  <p>The details view keeps one staff member in focus so you can see current recommendation, authority, and active work.</p>
                </div>
                <div class="agents-detail-layout">
                  <div class="agents-detail-hero">
                    <div class="agents-avatar" id="agents-detail-avatar">P</div>
                    <div class="agents-detail-copy">
                      <strong id="agents-detail-name">PEPPER</strong>
                      <span id="agents-detail-title">Chief of Staff</span>
                      <span id="agents-detail-status">Active</span>
                    </div>
                  </div>
                  <div class="agents-detail-quote" id="agents-detail-quote">“Keeping the system aligned, the team moving, and the operator focused on what only he can do.”</div>
                  <div class="agents-tab-row">
                    <div class="agents-tab active" data-agent-tab="overview" onclick="agentsSelectDetailTab('overview')">Overview</div>
                    <div class="agents-tab" data-agent-tab="capabilities" onclick="agentsSelectDetailTab('capabilities')">Capabilities</div>
                    <div class="agents-tab" data-agent-tab="boundaries" onclick="agentsSelectDetailTab('boundaries')">Boundaries</div>
                    <div class="agents-tab" data-agent-tab="relationship" onclick="agentsSelectDetailTab('relationship')">Relationship</div>
                    <div class="agents-tab" data-agent-tab="history" onclick="agentsSelectDetailTab('history')">History</div>
                  </div>
                  <div class="agents-detail-grid">
                    <div class="agents-detail-list agents-list-feed one-col" id="agents-detail-overview"></div>
                    <div class="agents-detail-card" style="padding:14px;">
                      <strong>Current Recommendation</strong>
                      <span id="agents-detail-recommendation">Loading recommendation…</span>
                      <div id="agents-detail-actions" style="display:flex;flex-wrap:wrap;gap:8px;margin-top:12px;"></div>
                      <div class="agents-action-link" onclick="filterAgents('Command')">View full profile →</div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section class="agents-card span-4">
              <div class="agents-card-inner">
                <div class="agents-card-header">
                  <div class="agents-card-number">3. Agent Activity Feed</div>
                  <h3>Live updates from your staff.</h3>
                  <p>Recent activity from command center, not just generic runtime pings.</p>
                </div>
                <div class="agents-list-feed one-col" id="agents-activity-feed"></div>
                <div class="agents-action-link" onclick="switchView('overview')">View full activity →</div>
              </div>
            </section>

            <section class="agents-card span-4">
              <div class="agents-card-inner">
                <div class="agents-card-header">
                  <div class="agents-card-number">4. Pending Requests & Handoffs</div>
                  <h3>Items awaiting your input.</h3>
                  <p>Approvals, decision gates, and intervention items are aggregated here.</p>
                </div>
                <div class="agents-list-feed one-col" id="agents-pending-list"></div>
                <div class="agents-action-link" onclick="switchView('approvals')">View all requests →</div>
              </div>
            </section>

            <section class="agents-card span-4">
              <div class="agents-card-inner">
                <div class="agents-card-header">
                  <div class="agents-card-number">5. Collaboration Map</div>
                  <h3>How your agents work together.</h3>
                  <p>Working together, handoffs, and active attention lanes all stay visible.</p>
                </div>
                <div class="agents-collab-layout">
                  <div class="agents-collab-map" id="agents-collab-map"></div>
                  <div class="agents-collab-legend" id="agents-collab-legend"></div>
                </div>
                <div class="agents-action-link" onclick="switchView('huddle')">View full map →</div>
              </div>
            </section>

            <section class="agents-card span-4">
              <div class="agents-card-inner">
                <div class="agents-card-header">
                  <div class="agents-card-number">6. Trust & Supervision</div>
                  <h3>Governance. Boundaries. Confidence.</h3>
                  <p>Supervision posture stays visible alongside the staff rather than buried in another route.</p>
                </div>
                <div class="agents-list-feed one-col" id="agents-trust-panel"></div>
                <div class="agents-action-link" onclick="switchView('supervision')">Supervision center →</div>
              </div>
            </section>

            <section class="agents-card span-5">
              <div class="agents-card-inner">
                <div class="agents-card-header">
                  <div class="agents-card-number">7. Agent Specializations</div>
                  <h3>Each agent has a lane.</h3>
                  <p>Together the council covers operations, planning, finance, health, family, publishing, memory, and design.</p>
                </div>
                <div class="agents-specialization-grid" id="agents-specializations"></div>
                <div class="agents-action-link" onclick="filterAgents('all')">Customize agent roles →</div>
              </div>
            </section>

            <section class="agents-card span-3">
              <div class="agents-card-inner">
                <div class="agents-card-header">
                  <div class="agents-card-number">8. Create & Deploy</div>
                  <h3>Bring new agents online.</h3>
                  <p>Use proven archetypes, clone strong performers, or import blueprints into the system.</p>
                </div>
                <div class="agents-create-grid" id="agents-create-panel"></div>
                <div class="agents-action-link" onclick="switchView('settings')">Agent lab →</div>
              </div>
            </section>

            <section class="agents-card span-4">
              <div class="agents-card-inner">
                <div class="agents-card-header">
                  <div class="agents-card-number">9. Agent Performance</div>
                  <h3>Your staff. Your systems. Your results.</h3>
                  <p>Performance is measured in completed work, responsiveness, decision flow, and delivered value.</p>
                </div>
                <div class="agents-performance-grid" id="agents-performance-panel"></div>
                <div class="agents-action-link" onclick="switchView('catalyst')">Performance dashboard →</div>
              </div>
            </section>
          </div>

          <div class="agents-footer-strip" id="agents-footer-strip"></div>
        </main>
      </div>
    </div>
  </div>

  <!-- ── INTELLIGENCE ───────────────────────────────────────── -->
  <div id="view-intelligence" class="view intel-view">
    <div class="intel-header">
      <div class="intel-brand">
        <div class="intel-brand-mark">
          <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
            <path d="M12 3a9 9 0 1 0 9 9"></path>
            <path d="M12 3v18M3 12h18"></path>
            <path d="M7.5 7.5c1.3 1 2.9 1.5 4.5 1.5s3.2-.5 4.5-1.5M7.5 16.5c1.3-1 2.9-1.5 4.5-1.5s3.2.5 4.5 1.5"></path>
          </svg>
        </div>
        <div class="intel-brand-copy">
          <div class="intel-kicker">Sensemaking Engine & Private Intelligence Floor</div>
          <div class="intel-title">JARVIS <span>INTEL</span></div>
          <div class="intel-subtitle">Perceive. Correlate. Understand. Escalate.</div>
          <div class="intel-brand-detail">Clarity is not more data. It’s better understanding.</div>
        </div>
      </div>

      <div class="intel-header-center">
        <div class="intel-stat-grid">
          <div class="intel-stat-shell"><div class="intel-stat-label">Signals Perceived</div><div class="intel-stat-value" id="intel-stat-signals">—</div><div class="intel-stat-sub" id="intel-stat-signals-sub">vs yesterday</div></div>
          <div class="intel-stat-shell"><div class="intel-stat-label">Correlations Made</div><div class="intel-stat-value" id="intel-stat-correlations">—</div><div class="intel-stat-sub" id="intel-stat-correlations-sub">linked across domains</div></div>
          <div class="intel-stat-shell"><div class="intel-stat-label">Truths Surfaced</div><div class="intel-stat-value" id="intel-stat-truths">—</div><div class="intel-stat-sub" id="intel-stat-truths-sub">high-value insights</div></div>
          <div class="intel-stat-shell"><div class="intel-stat-label">Escalations</div><div class="intel-stat-value" id="intel-stat-escalations">—</div><div class="intel-stat-sub" id="intel-stat-escalations-sub">raised upward</div></div>
          <div class="intel-stat-shell"><div class="intel-stat-label">Patterns Updated</div><div class="intel-stat-value" id="intel-stat-patterns">—</div><div class="intel-stat-sub" id="intel-stat-patterns-sub">learning refreshed</div></div>
          <div class="intel-stat-shell"><div class="intel-stat-label">Intel Confidence</div><div class="intel-stat-value" id="intel-stat-confidence">—</div><div class="intel-stat-sub" id="intel-stat-confidence-sub">High</div></div>
        </div>
        <div class="intel-quote">
          <div class="intel-quote-mark">“</div>
          <div>
            <strong>Clarity is not more data. It’s better understanding.</strong>
            <span>Intel connects service health, cross-domain friction, and live attention signals into one sensemaking floor.</span>
          </div>
        </div>
      </div>

      <div class="intel-profile">
        <div class="intel-profile-meta">
          <div class="intel-profile-avatar">CB</div>
          <div>
            <strong>Chris Binion</strong>
            <span>Executive Mode</span>
          </div>
        </div>
        <span id="intel-generated-at">Updated just now</span>
      </div>
    </div>

    <div class="intel-shell">
      <aside class="intel-sidebar">
        <div class="intel-side-title">Intel Engine Status</div>
        <div class="intel-side-list" id="intel-sidebar-list"></div>
        <button class="intel-side-cta" id="intel-refresh-button" onclick="refreshIntelDesktop()">Refresh Intel ↻</button>
        <button class="intel-side-cta" onclick="switchView('settings')">Intel Settings →</button>
        <div class="agents-status-card" style="margin-top:12px;">
          <strong>Runtime Note</strong>
          <span id="intel-runtime-note">Loading live Intel context…</span>
        </div>
      </aside>

      <div class="intel-grid">
        <section class="intel-card intel-span-4">
          <div class="intel-card-inner">
            <div class="intel-card-header">
              <div>
                <div class="intel-card-number">1. Signal Inflow (Live)</div>
                <h3>What JARVIS is perceiving right now.</h3>
              </div>
            </div>
            <div class="intel-signal-grid" id="intel-signal-grid"></div>
            <button class="intel-section-link" style="margin-top:14px;" onclick="switchView('vision')">View all signal sources →</button>
          </div>
        </section>

        <section class="intel-card intel-span-4">
          <div class="intel-card-inner">
            <div class="intel-card-header">
              <div>
                <div class="intel-card-number">2. Correlation Map</div>
                <h3>How signals connect across your domains.</h3>
              </div>
            </div>
            <div class="intel-correlation-map">
              <div class="intel-correlation-center">JARVIS<br>Intel</div>
              <div class="intel-correlation-node top" id="intel-node-top">Focus Load</div>
              <div class="intel-correlation-node right" id="intel-node-right">Calendar Drift</div>
              <div class="intel-correlation-node bottom" id="intel-node-bottom">Decision Risk</div>
              <div class="intel-correlation-node left" id="intel-node-left">Recovery Strain</div>
              <div class="intel-correlation-node tl" id="intel-node-tl">Signal Noise</div>
              <div class="intel-correlation-node br" id="intel-node-br">Household Drift</div>
            </div>
            <button class="intel-section-link" style="margin-top:14px;" onclick="switchView('journey')">Explore correlations →</button>
          </div>
        </section>

        <section class="intel-card intel-span-4">
          <div class="intel-card-inner">
            <div class="intel-card-header">
              <div>
                <div class="intel-card-number">3. Truth Compression</div>
                <h3>What matters most right now.</h3>
              </div>
            </div>
            <div class="intel-truth-list" id="intel-truth-list"></div>
            <button class="intel-section-link" style="margin-top:14px;" onclick="switchView('overview')">See full intel brief →</button>
          </div>
        </section>

        <section class="intel-card intel-span-3">
          <div class="intel-card-inner">
            <div class="intel-card-header">
              <div>
                <div class="intel-card-number">4. Escalation Routing</div>
                <h3>How Intel decides what reaches you.</h3>
              </div>
            </div>
            <div class="intel-route-list" id="intel-route-list"></div>
          </div>
        </section>

        <section class="intel-card intel-span-4">
          <div class="intel-card-inner">
            <div class="intel-card-header">
              <div>
                <div class="intel-card-number">5. Continuity Awareness</div>
                <h3>Why this matters in the bigger picture.</h3>
              </div>
            </div>
            <div class="intel-continuity-list" id="intel-continuity-list"></div>
            <button class="intel-section-link" style="margin-top:14px;" onclick="switchView('journey')">View continuity dossier →</button>
          </div>
        </section>

        <section class="intel-card intel-span-3">
          <div class="intel-card-inner">
            <div class="intel-card-header">
              <div>
                <div class="intel-card-number">6. Overnight Intel Summary</div>
                <h3>What JARVIS understood while you were away.</h3>
              </div>
            </div>
            <div class="intel-summary-grid" id="intel-summary-grid"></div>
            <button class="intel-section-link" style="margin-top:14px;" onclick="switchView('activity')">View while you were away →</button>
          </div>
        </section>

        <section class="intel-card intel-span-3">
          <div class="intel-card-inner">
            <div class="intel-card-header">
              <div>
                <div class="intel-card-number">7. Top Intel Insights</div>
                <h3>The truths you should know.</h3>
              </div>
            </div>
            <div class="intel-insight-list" id="intel-insight-list"></div>
            <button class="intel-section-link" style="margin-top:14px;" onclick="switchView('command')">View all insights →</button>
          </div>
        </section>

        <section class="intel-card intel-span-2">
          <div class="intel-card-inner">
            <div class="intel-card-header">
              <div>
                <div class="intel-card-number">8. Risk & Opportunity Radar</div>
                <h3>What could go wrong. What could go right.</h3>
              </div>
            </div>
            <div class="intel-radar">
              <div class="intel-radar-grid">
                <svg viewBox="0 0 220 220" preserveAspectRatio="xMidYMid meet">
                  <circle cx="110" cy="110" r="78" fill="none" stroke="rgba(255,255,255,0.08)"/>
                  <circle cx="110" cy="110" r="52" fill="none" stroke="rgba(255,255,255,0.08)"/>
                  <circle cx="110" cy="110" r="28" fill="none" stroke="rgba(255,255,255,0.08)"/>
                  <path d="M110 32 L188 110 L110 188 L32 110 Z" fill="rgba(55,167,255,0.08)" stroke="rgba(55,167,255,0.34)"/>
                  <path d="M110 52 L162 104 L134 150 L74 138 L58 94 Z" fill="rgba(231,164,79,0.12)" stroke="rgba(231,164,79,0.44)"/>
                  <path d="M110 68 L144 110 L118 142 L78 122 L84 86 Z" fill="rgba(93,190,120,0.12)" stroke="rgba(93,190,120,0.44)"/>
                </svg>
              </div>
            </div>
          </div>
        </section>

        <section class="intel-card intel-span-5">
          <div class="intel-card-inner">
            <div class="intel-card-header">
              <div>
                <div class="intel-card-number">9. Pattern Library (Updated)</div>
                <h3>New and updated patterns JARVIS is learning.</h3>
              </div>
            </div>
            <div class="intel-pattern-grid" id="intel-pattern-grid"></div>
            <button class="intel-section-link" style="margin-top:14px;" onclick="switchView('journey')">Browse all patterns →</button>
          </div>
        </section>

        <section class="intel-card intel-span-3">
          <div class="intel-card-inner">
            <div class="intel-card-header">
              <div>
                <div class="intel-card-number">10. Intel Timeline</div>
                <h3>A timeline of key signals and insights.</h3>
              </div>
            </div>
            <div class="intel-timeline-list" id="intel-timeline-list"></div>
            <button class="intel-section-link" style="margin-top:14px;" onclick="switchView('activity')">View full timeline →</button>
          </div>
        </section>

        <section class="intel-card intel-span-2">
          <div class="intel-card-inner">
            <div class="intel-card-header">
              <div>
                <div class="intel-card-number">11. Intel Doctrine & Learning</div>
                <h3>How JARVIS is getting smarter.</h3>
              </div>
            </div>
            <div class="intel-doctrine-list" id="intel-doctrine-list"></div>
          </div>
        </section>

        <section class="intel-card intel-span-2">
          <div class="intel-card-inner">
            <div class="intel-card-header">
              <div>
                <div class="intel-card-number">12. Teach JARVIS (Feedback Loop)</div>
                <h3>Help JARVIS understand you better.</h3>
              </div>
            </div>
            <div class="intel-teach-list" id="intel-teach-list"></div>
          </div>
        </section>

        <section class="intel-footer-strip" id="intel-footer-strip"></section>
      </div>
    </div>
  </div>

  <!-- ── EMAIL ─────────────────────────────────────────────── -->
  <div id="view-email" class="view email-view">
    <div class="email-header">
      <div>
        <div class="view-title">JARVIS <span>EMAIL</span><div class="view-title-line"></div></div>
        <div class="email-brand-subtitle">Your communication command center. Filter the noise, protect your focus, and surface the messages that actually move work, family, and mission forward.</div>
      </div>
      <div class="email-header-stats">
        <div class="email-header-stat"><strong id="emailStatUnread">—</strong><span>Inbox Focus</span><em id="emailStatUnreadSub">Needs review</em></div>
        <div class="email-header-stat"><strong id="emailStatPriority">—</strong><span>Priority</span><em id="emailStatPrioritySub">High priority</em></div>
        <div class="email-header-stat"><strong id="emailStatWaiting">—</strong><span>Waiting On</span><em id="emailStatWaitingSub">From others</em></div>
        <div class="email-header-stat"><strong id="emailStatSent">—</strong><span>Sent Today</span><em id="emailStatSentSub">Emails</em></div>
        <div class="email-header-stat"><strong id="emailStatTimeSaved">—</strong><span>Time Saved</span><em id="emailStatTimeSavedSub">This week</em></div>
        <div class="email-header-stat"><strong id="emailStatFocus">—</strong><span>Inbox Health</span><em id="emailStatFocusSub">Excellent</em></div>
      </div>
      <div class="email-profile-card">
        <div class="email-quote">“JARVIS handles the noise so you can focus on what matters.”</div>
        <div class="email-profile-mini">
          <div class="email-profile-avatar">CB</div>
          <div>
            <strong>Chris Binion</strong>
            <span>Executive Mode</span>
          </div>
        </div>
      </div>
    </div>

    <div class="email-shell">
      <div class="email-desktop">
        <aside class="email-sidebar">
          <div class="email-sidebar-brand">
            <div class="email-sidebar-brand-mark">✉</div>
            <strong>JARVIS</strong>
            <span>Email command</span>
          </div>
          <div class="email-sidebar-nav">
            <div class="email-sidebar-item active" onclick="emailSidebarAction('filter', {{ filter: 'focused' }})"><span>Inbox Priority</span><b id="emailUnreadBadge">0</b></div>
            <div class="email-sidebar-item" onclick="emailSidebarAction('selected')"><span>Selected Email</span><b id="emailSidebarSelected">—</b></div>
            <div class="email-sidebar-item" onclick="emailSidebarAction('threads')"><span>Threads In Focus</span><b id="emailSidebarThreads">0</b></div>
            <div class="email-sidebar-item" onclick="emailSidebarAction('pending')"><span>Pending Actions</span><b id="emailSidebarPending">0</b></div>
            <div class="email-sidebar-item" onclick="emailSidebarAction('sources')"><span>Accounts</span><b id="emailSidebarAccounts">2</b></div>
          </div>
          <div class="email-sidebar-status">
            <h4>Mail Status</h4>
            <div id="email-runtime-note" class="email-card-subtitle" style="margin-bottom:12px;">Email is live and connected.</div>
            <div id="emailSidebarStatus"></div>
            <button class="email-sidebar-btn" id="email-refresh-button" onclick="refreshEmailDesktop(true)">Refresh Email</button>
            <button class="email-sidebar-btn" onclick="emailOpenRoute('/settings-center', 'settings', 'Open Email Settings', 'Opening Email settings and connector controls.')">Email Settings →</button>
          </div>
        </aside>

        <main class="email-main">
          <div class="email-grid">
            <section class="email-card">
              <div class="email-card-header">
                <div>
                  <h3 class="email-card-title">1. Inbox Overview</h3>
                  <span class="email-card-subtitle">Your inbox at a glance.</span>
                </div>
                <button class="email-chip-btn" onclick="emailOpenRoute('/command-center', 'chat', 'Open Email Controls', 'Opening Email controls from the Inbox Overview card.')">Customize →</button>
              </div>
              <div class="email-overview-stats" id="emailOverviewStats"></div>
              <div class="email-progress-block">
                <div class="email-progress-top"><strong>Inbox Zero Progress</strong><span id="email-zero-score">0%</span></div>
                <div class="email-progress-bar"><i id="email-zero-bar" style="width:0%"></i></div>
                <div class="email-progress-note" id="email-zero-note">Loading inbox posture...</div>
              </div>
            </section>

            <section class="email-card">
              <div class="email-card-header">
                <div>
                  <h3 class="email-card-title">2. Priority Focus</h3>
                  <span class="email-card-subtitle">Messages that deserve your attention now.</span>
                </div>
                <button class="email-chip-btn" onclick="filterEmail('focused', document.querySelector('[data-email-filter=\"focused\"]'))">View Focused</button>
              </div>
              <div class="email-priority-list" id="emailPriorityFocus"></div>
            </section>

            <section class="email-card">
              <div class="email-card-header">
                <div>
                  <h3 class="email-card-title">3. Email Intelligence</h3>
                  <span class="email-card-subtitle">AI insights about your communications.</span>
                </div>
                <button class="email-chip-btn" onclick="emailOpenRoute('/activity-center', 'journey', 'Open Email Insights', 'Opening Email continuity and activity insight from the Email desktop.')">View Insights →</button>
              </div>
              <div class="email-intelligence-grid" id="emailIntelligenceGrid"></div>
            </section>
          </div>

          <div class="email-grid-secondary">
            <section class="email-card">
              <div class="email-card-header">
                <div>
                  <h3 class="email-card-title">4. Smart Inbox</h3>
                  <span class="email-card-subtitle">Organized by importance, not time.</span>
                </div>
              </div>
              <div class="email-filter-tabs">
                <button class="email-filter-tab active" data-email-filter="focused" onclick="filterEmail('focused', this)">Focused</button>
                <button class="email-filter-tab" data-email-filter="all" onclick="filterEmail('all', this)">All Mail</button>
                <button class="email-filter-tab" data-email-filter="unread" onclick="filterEmail('unread', this)">Unread</button>
                <button class="email-filter-tab" data-email-filter="updates" onclick="filterEmail('updates', this)">Updates</button>
                <button class="email-filter-tab" data-email-filter="newsletters" onclick="filterEmail('newsletters', this)">Newsletters</button>
                <button class="email-filter-tab" data-email-filter="waiting" onclick="filterEmail('waiting', this)">Waiting On</button>
              </div>
              <div id="emailList" class="email-list">
                <div class="loading-state">Loading email...</div>
              </div>
            </section>

            <section class="email-card email-preview-card">
              <div class="email-card-header">
                <div>
                  <h3 class="email-card-title">5. Selected Email</h3>
                  <span class="email-card-subtitle">Full context. AI enhanced.</span>
                </div>
                <div class="email-preview-toolbar">
                  <button onclick="emailHandleAction('reply-draft')">↩ Reply</button>
                  <button onclick="emailHandleAction('reply-all-boundary')">⤴ Reply All</button>
                  <button onclick="emailHandleAction('forward-boundary')">→ Forward</button>
                  <button onclick="emailHandleAction('delegate-route')">◎ Delegate</button>
                </div>
              </div>
              <div class="email-preview-header">
                <div>
                  <h3 id="emailPreviewSubject">Loading inbox…</h3>
                </div>
                <div id="emailPreviewPriority" class="email-pill info">Info</div>
              </div>
              <div class="email-preview-metadata" id="emailPreviewMeta"></div>
              <div class="email-preview-body" id="emailPreviewBody">JARVIS is assembling the selected message and the best next move.</div>
              <div class="email-preview-summary">
                <strong>JARVIS Intelligence</strong>
                <ul id="emailPreviewSummary"></ul>
              </div>
              <div class="email-preview-attachments" id="emailPreviewAttachments"></div>
              <div class="email-preview-cta">
                <button class="approve" onclick="emailHandleAction('reply-draft')">Approve & Reply</button>
                <button class="review" onclick="emailHandleAction('schedule-review')">Schedule Review</button>
                <button onclick="emailHandleAction('delegate-route')">Delegate Response</button>
                <button class="decline" onclick="emailHandleAction('mark-selected-read')">Archive</button>
              </div>
            </section>

            <section class="email-card">
              <div class="email-card-header">
                <div>
                  <h3 class="email-card-title">8. Quick Actions</h3>
                  <span class="email-card-subtitle">Powerful tools for your email workflow.</span>
                </div>
              </div>
              <div class="email-quick-grid">
                <button class="email-quick-btn" onclick="emailHandleAction('compose-draft')">Compose<span>Draft with JARVIS</span></button>
                <button class="email-quick-btn" onclick="emailSidebarAction('filter', {{ filter: 'unread' }})">Unread Only<span>Refresh focus</span></button>
                <button class="email-quick-btn" onclick="emailSidebarAction('filter', {{ filter: 'all' }})">All Mail<span>Reload inbox</span></button>
                <button class="email-quick-btn" onclick="filterEmail('focused', document.querySelector('[data-email-filter=\"focused\"]'))">Focus Mode<span>Protect deep work</span></button>
                <button class="email-quick-btn" onclick="filterEmail('newsletters', document.querySelector('[data-email-filter=\"newsletters\"]'))">Newsletters<span>Review later</span></button>
                <button class="email-quick-btn" onclick="emailHandleAction('templates-boundary')">Templates<span>Scale responses</span></button>
                <button class="email-quick-btn" onclick="emailHandleAction('rules-boundary')">Rules<span>Smart filtering</span></button>
                <button class="email-quick-btn" onclick="emailHandleAction('search-route')">Email Search<span>Find anything</span></button>
                <button class="email-quick-btn" onclick="emailHandleAction('sync-sources')">Sync Sources<span>Refresh connectors</span></button>
              </div>
            </section>
          </div>

          <div class="email-grid-tertiary">
            <section class="email-card">
              <div class="email-card-header">
                <div>
                  <h3 class="email-card-title">6. Communication Patterns</h3>
                  <span class="email-card-subtitle">Your email habits and insights.</span>
                </div>
              </div>
              <div class="email-pattern-layout">
                <div class="email-donut" id="emailPatternDonut">
                  <div class="email-donut-center"><div><strong id="emailPatternTime">0m</strong><span>Daily time</span></div></div>
                </div>
                <div class="email-pattern-list" id="emailPatternList"></div>
              </div>
            </section>

            <section class="email-card">
              <div class="email-card-header">
                <div>
                  <h3 class="email-card-title">7. Email Health</h3>
                  <span class="email-card-subtitle">Keeping your inbox healthy.</span>
                </div>
                <button class="email-chip-btn" onclick="emailOpenRoute('/activity-center', 'journey', 'Open Email Health Details', 'Opening Email health continuity details.')">View Details →</button>
              </div>
              <div class="email-health-list" id="emailHealthList"></div>
            </section>

            <section class="email-card">
              <div class="email-card-header">
                <div>
                  <h3 class="email-card-title">11. Email Sources</h3>
                  <span class="email-card-subtitle">Connected accounts and inbox load.</span>
                </div>
              </div>
              <div class="email-source-list" id="emailSourceList"></div>
            </section>

            <section class="email-card">
              <div class="email-card-header">
                <div>
                  <h3 class="email-card-title">12. Quick Email Actions</h3>
                  <span class="email-card-subtitle">Shortcuts for execution.</span>
                </div>
              </div>
              <div class="email-compose-grid">
                <button class="email-compose-chip" onclick="emailHandleAction('search-route')">Find an Email</button>
                <button class="email-compose-chip" onclick="emailHandleAction('search-person')">Search by Person</button>
                <button class="email-compose-chip" onclick="emailHandleAction('search-date')">Search by Date</button>
                <button class="email-compose-chip" onclick="emailHandleAction('search-attachments')">Attachments</button>
                <button class="email-compose-chip" onclick="emailHandleAction('boundary-unsubscribe')">Unsubscribe</button>
                <button class="email-compose-chip" onclick="emailHandleAction('boundary-block-sender')">Block Sender</button>
                <button class="email-compose-chip" onclick="emailHandleAction('boundary-create-rule')">Create Rule</button>
                <button class="email-compose-chip" onclick="emailHandleAction('boundary-export-thread')">Export Thread</button>
              </div>
            </section>
          </div>

          <div class="email-grid-tertiary">
            <section class="email-card">
              <div class="email-card-header">
                <div>
                  <h3 class="email-card-title">5. Email Categories</h3>
                  <span class="email-card-subtitle">Organized for speed and clarity.</span>
                </div>
                <button class="email-chip-btn" onclick="emailHandleAction('rules-boundary')">Manage Categories →</button>
              </div>
              <div class="email-category-list" id="emailCategoryList"></div>
            </section>

            <section class="email-card">
              <div class="email-card-header">
                <div>
                  <h3 class="email-card-title">6. Threads In Focus</h3>
                  <span class="email-card-subtitle">Active conversations that matter most.</span>
                </div>
                <button class="email-chip-btn" onclick="filterEmail('focused', document.querySelector('[data-email-filter=\"focused\"]'))">View Focused →</button>
              </div>
              <div class="email-thread-list" id="emailThreadList"></div>
            </section>

            <section class="email-card">
              <div class="email-card-header">
                <div>
                  <h3 class="email-card-title">9. Compose With JARVIS</h3>
                  <span class="email-card-subtitle">AI-assisted writing that sounds like you.</span>
                </div>
              </div>
              <div class="email-compose-grid">
                <button class="email-compose-chip" onclick="emailHandleAction('compose-draft')">New Email</button>
                <button class="email-compose-chip" onclick="emailHandleAction('reply-draft')">Quick Reply</button>
                <button class="email-compose-chip" onclick="emailHandleAction('follow-up-draft')">Follow Up</button>
                <button class="email-compose-chip" onclick="emailHandleAction('meeting-draft')">Meeting Invite</button>
                <button class="email-compose-chip" onclick="emailHandleAction('compose-draft')">Draft from Notes</button>
                <button class="email-compose-chip" onclick="emailHandleAction('boundary-tone')">Tone Assistant</button>
                <button class="email-compose-chip" onclick="emailHandleAction('boundary-grammar')">Grammar Check</button>
                <button class="email-compose-chip" onclick="emailHandleAction('boundary-improve')">AI Improve</button>
              </div>
            </section>

            <section class="email-card">
              <div class="email-card-header">
                <div>
                  <h3 class="email-card-title">10. Snoozed & Scheduled</h3>
                  <span class="email-card-subtitle">Emails you parked for the right time.</span>
                </div>
                <button class="email-chip-btn" onclick="emailHandleAction('snooze-boundary')">View All →</button>
              </div>
              <div class="email-pending-list" id="emailSnoozedList"></div>
            </section>
          </div>

          <div class="email-grid">
            <section class="email-card">
              <div class="email-card-header">
                <div>
                  <h3 class="email-card-title">4. Workflow & Automation</h3>
                  <span class="email-card-subtitle">JARVIS automates what should be automated.</span>
                </div>
                <button class="email-chip-btn" onclick="emailOpenRoute('/activity-center', 'journey', 'Open Email Automation Log', 'Opening Email automation continuity and operator activity.')">View Automation Log →</button>
              </div>
              <div class="email-automation-list" id="emailAutomationList"></div>
            </section>

            <section class="email-card">
              <div class="email-card-header">
                <div>
                  <h3 class="email-card-title">8. Pending Actions</h3>
                  <span class="email-card-subtitle">Emails that need your action.</span>
                </div>
                <button class="email-chip-btn" onclick="filterEmail('focused', document.querySelector('[data-email-filter=\"focused\"]'))">See All Actions →</button>
              </div>
              <div class="email-pending-list" id="emailPendingList"></div>
            </section>

            <section class="email-card">
              <div class="email-card-header">
                <div>
                  <h3 class="email-card-title">Engine Status</h3>
                  <span class="email-card-subtitle">Communication intelligence stays online and learns continuously.</span>
                </div>
              </div>
              <div class="email-engine-status">
                <div>
                  <strong style="display:block;color:var(--email-green);font-size:14px;">EMAIL ENGINE ONLINE</strong>
                  <span id="emailEngineStatusCopy" style="display:block;margin-top:5px;color:var(--email-ink-faint);font-size:12px;">All accounts synced</span>
                </div>
                <b></b>
              </div>
            </section>
          </div>

          <div class="email-footer-strip" id="emailFooterStrip"></div>
        </main>
      </div>
    </div>
  </div>

  <div id="view-social" class="view social-view" style="display:none">
    <div class="social-header">
      <div>
        <div class="view-title">JARVIS <span>SOCIAL MEDIA</span><div class="view-title-line"></div></div>
        <div class="social-subtitle">Your voice. Your mission. Amplified with purpose. Strategy, content, engagement, and platform intelligence in one live desktop command surface.</div>
        <div id="social-runtime-note" class="social-card-subtitle" style="margin-top:10px;">Social Media is loading live state.</div>
      </div>
      <div class="social-header-stats">
        <div class="social-header-stat"><strong id="social-stat-health">—</strong><span>Overall Health</span><em id="social-stat-health-sub">Loading</em></div>
        <div class="social-header-stat"><strong id="social-stat-engagement">—</strong><span>Engagement</span><em id="social-stat-engagement-sub">vs 7d</em></div>
        <div class="social-header-stat"><strong id="social-stat-followers">—</strong><span>New Followers</span><em id="social-stat-followers-sub">Loading</em></div>
        <div class="social-header-stat"><strong id="social-stat-impressions">—</strong><span>Impressions</span><em id="social-stat-impressions-sub">Loading</em></div>
        <div class="social-header-stat"><strong id="social-stat-visits">—</strong><span>Profile Visits</span><em id="social-stat-visits-sub">Loading</em></div>
        <div class="social-header-stat"><strong id="social-stat-reach">—</strong><span>Reach</span><em id="social-stat-reach-sub">Loading</em></div>
        <div class="social-header-stat"><strong id="social-stat-time">—</strong><span>Time Saved</span><em id="social-stat-time-sub">This week</em></div>
      </div>
      <div class="social-profile-card">
        <div class="social-profile-quote">“Use your platform for your purpose, not for your ego.”</div>
        <div class="social-profile-mini">
          <div class="social-profile-avatar">CB</div>
          <div>
            <strong>Chris Binion</strong>
            <span>Executive Mode</span>
          </div>
        </div>
      </div>
    </div>

    <div class="social-shell">
      <div class="social-desktop">
        <aside class="social-sidebar">
          <div class="social-sidebar-brand">
            <div class="social-sidebar-brand-mark">💬</div>
            <strong>JARVIS</strong>
            <span>Social command</span>
          </div>
          <div class="social-sidebar-nav">
            <button class="social-sidebar-item active" type="button" data-social-nav="1" onclick="socialSetPage(1)"><span>Overview</span><b id="social-side-overview">Live</b></button>
            <button class="social-sidebar-item" type="button" data-social-nav="4" onclick="socialSetPage(4)"><span>Inbox</span><b id="social-side-inbox">0</b></button>
            <button class="social-sidebar-item" type="button" data-social-nav="2" onclick="socialSetPage(2)"><span>Calendar</span><b id="social-side-calendar">0</b></button>
            <button class="social-sidebar-item" type="button" data-social-nav="5" onclick="socialSetPage(5)"><span>Workflow</span><b id="social-side-workflow">0%</b></button>
            <button class="social-sidebar-item" type="button" data-social-nav="12" onclick="socialSetPage(12)"><span>Accounts</span><b id="social-side-accounts">0</b></button>
          </div>
          <div class="social-sidebar-status">
            <h4>Social Status</h4>
            <div id="social-sidebar-status"></div>
            <button class="social-sidebar-btn" onclick="socialHandleAction('manage-accounts')">Social Settings →</button>
          </div>
        </aside>

        <main class="social-main">
          <div class="social-grid">
            <section class="social-card">
              <div class="social-card-header">
                <div>
                  <h3 class="social-card-title">1. Social Media Overview</h3>
                  <span class="social-card-subtitle">Your platforms at a glance.</span>
                </div>
              </div>
              <div class="social-platform-grid" id="social-platform-grid"></div>
              <div class="social-mini-stats" id="social-mini-stats"></div>
            </section>

            <section class="social-card">
              <div class="social-card-header">
                <div>
                  <h3 class="social-card-title">2. Content Calendar</h3>
                  <span class="social-card-subtitle">Planned and scheduled content.</span>
                </div>
                <div class="social-tabs">
                  <button class="social-tab active">Week</button>
                  <button class="social-tab" onclick="socialHandleAction('calendar-day-boundary')">Day</button>
                  <button class="social-tab" onclick="socialHandleAction('refresh-social')">↻</button>
                </div>
              </div>
              <div class="social-calendar-grid" id="social-calendar-grid"></div>
              <div class="social-calendar-foot" id="social-calendar-foot"></div>
            </section>

            <section class="social-card">
              <div class="social-card-header">
                <div>
                  <h3 class="social-card-title">3. Content Performance</h3>
                  <span class="social-card-subtitle">What is resonating with your audience.</span>
                </div>
                <button class="social-chip-btn" onclick="socialHandleAction('open-analytics')">View Analytics →</button>
              </div>
              <div class="social-tabs">
                <button class="social-tab active">Top Posts</button>
                <button class="social-tab" onclick="socialHandleAction('top-topics-boundary')">Top Topics</button>
                <button class="social-tab" onclick="socialHandleAction('top-formats-boundary')">Top Formats</button>
              </div>
              <div class="social-performance-list" id="social-performance-list"></div>
            </section>

            <section class="social-card">
              <div class="social-card-header">
                <div>
                  <h3 class="social-card-title">4. Engagement & Messages</h3>
                  <span class="social-card-subtitle">Conversations that need your attention.</span>
                </div>
              </div>
              <div class="social-tabs">
                <button class="social-tab active">Priority</button>
                <button class="social-tab" onclick="socialHandleAction('mentions-boundary')">Mentions</button>
                <button class="social-tab" onclick="socialHandleAction('comments-boundary')">Comments</button>
                <button class="social-tab" onclick="socialHandleAction('boundary-dms')">DMs</button>
              </div>
              <div class="social-inbox-list" id="social-inbox-list"></div>
            </section>
          </div>

          <div class="social-grid-secondary">
            <section class="social-card">
              <div class="social-card-header">
                <div>
                  <h3 class="social-card-title">5. Content Pipeline</h3>
                  <span class="social-card-subtitle">Ideas to publishing in one flow.</span>
                </div>
                <button class="social-chip-btn" onclick="socialHandleAction('open-publishing')">View Full Pipeline →</button>
              </div>
              <div class="social-workflow-list" id="social-pipeline-list"></div>
            </section>

            <section class="social-card">
              <div class="social-card-header">
                <div>
                  <h3 class="social-card-title">6. Audience Insights</h3>
                  <span class="social-card-subtitle">Who you are reaching and what they care about.</span>
                </div>
              </div>
              <div style="display:grid;grid-template-columns:1fr .9fr;gap:16px;align-items:center;">
                <div>
                  <div class="social-audience-ring">
                    <div class="social-ring-center"><div><strong id="social-audience-total">—</strong><span>Total Audience</span></div></div>
                  </div>
                  <div class="social-audience-list" id="social-audience-list"></div>
                </div>
                <div class="social-thread-list" id="social-audience-insights"></div>
              </div>
            </section>

            <section class="social-card">
              <div class="social-card-header">
                <div>
                  <h3 class="social-card-title">7. Content Themes & Impact</h3>
                  <span class="social-card-subtitle">The pillars driving your mission.</span>
                </div>
                <button class="social-chip-btn" onclick="socialHandleAction('open-command')">View Themes →</button>
              </div>
              <div class="social-thread-list" id="social-theme-list"></div>
            </section>
          </div>

          <div class="social-grid-tertiary">
            <section class="social-card">
              <div class="social-card-header">
                <div>
                  <h3 class="social-card-title">8. Status & Health</h3>
                  <span class="social-card-subtitle">Your social media health score.</span>
                </div>
              </div>
              <div style="display:grid;grid-template-columns:.9fr 1.1fr;gap:16px;align-items:center;">
                <div class="social-health-ring">
                  <div class="social-ring-center"><div><strong id="social-health-score">—</strong><span id="social-health-label">Healthy</span></div></div>
                </div>
                <div class="social-health-metrics" id="social-health-metrics"></div>
              </div>
            </section>

            <section class="social-card">
              <div class="social-card-header">
                <div>
                  <h3 class="social-card-title">9. Sentiment & Tone</h3>
                  <span class="social-card-subtitle">How the world feels about your content.</span>
                </div>
                <button class="social-chip-btn" onclick="socialHandleAction('view-trends-boundary')">View Trends →</button>
              </div>
              <div class="social-thread-list" id="social-sentiment-list"></div>
            </section>

            <section class="social-card">
              <div class="social-card-header">
                <div>
                  <h3 class="social-card-title">10. Quick Actions</h3>
                  <span class="social-card-subtitle">Create, publish, engage.</span>
                </div>
              </div>
              <div class="social-quick-grid">
                <button class="social-quick-btn" onclick="socialHandleAction('create-post')">Create Post<span>Draft with JARVIS</span></button>
                <button class="social-quick-btn" onclick="socialHandleAction('boundary-thread')">Write Thread<span>X / LinkedIn</span></button>
                <button class="social-quick-btn" onclick="socialHandleAction('boundary-video')">Upload Video<span>Short or long-form</span></button>
                <button class="social-quick-btn" onclick="socialHandleAction('schedule-post')">Schedule Post<span>Protect cadence</span></button>
                <button class="social-quick-btn" onclick="socialHandleAction('boundary-dms')">Respond to DMs<span>Priority inbox</span></button>
                <button class="social-quick-btn" onclick="socialHandleAction('open-analytics')">View Analytics<span>Performance readout</span></button>
                <button class="social-quick-btn" onclick="socialHandleAction('open-command')">Content Ideas<span>Generate concepts</span></button>
                <button class="social-quick-btn" onclick="socialHandleAction('refresh-social')">Refresh<span>Reload live state</span></button>
              </div>
            </section>
          </div>

          <div class="social-grid-bottom">
            <section class="social-card">
              <div class="social-card-header">
                <div>
                  <h3 class="social-card-title">11. What JARVIS Recommends</h3>
                  <span class="social-card-subtitle">AI-powered recommendations for you.</span>
                </div>
                <button class="social-chip-btn" onclick="socialHandleAction('open-analytics')">View All Recommendations →</button>
              </div>
              <div class="social-reco-list" id="social-reco-list"></div>
            </section>

            <section class="social-card">
              <div class="social-card-header">
                <div>
                  <h3 class="social-card-title">12. Account & Security</h3>
                  <span class="social-card-subtitle">Protect and manage your presence.</span>
                </div>
                <button class="social-chip-btn" onclick="socialHandleAction('manage-accounts')">Manage Accounts →</button>
              </div>
              <div class="social-security-list" id="social-security-list"></div>
            </section>

            <section class="social-card">
              <div class="social-card-header">
                <div>
                  <h3 class="social-card-title">This Week's Summary</h3>
                  <span class="social-card-subtitle">Your weekly social media recap.</span>
                </div>
              </div>
              <div class="social-summary-grid" id="social-summary-grid"></div>
              <div style="margin-top:16px;" class="social-settings-grid">
                <button class="social-mini-btn" onclick="socialHandleAction('execute-ready')">Auto-Publish</button>
                <button class="social-mini-btn" onclick="socialHandleAction('best-time-boundary')">Best Time</button>
                <button class="social-mini-btn" onclick="socialHandleAction('recycling-boundary')">Recycling</button>
                <button class="social-mini-btn" onclick="socialHandleAction('assistant-boundary')">Assistant</button>
              </div>
            </section>
          </div>

          <div class="social-footer-strip" id="social-footer-strip"></div>
        </main>
      </div>
    </div>
  </div>

  <!-- ── CALENDAR ───────────────────────────────────────────── -->
  <div id="view-calendar" class="view calendar-view" style="display:none">
    <div class="calendar-header">
      <div>
        <div class="view-title">JARVIS <span>CALENDAR</span><div class="view-title-line"></div></div>
        <div class="calendar-subtitle">Your time. Your priorities. Perfectly orchestrated. A protected desktop planning surface for focus blocks, family rhythm, route-sensitive commitments, and decision-ready schedule intelligence.</div>
      </div>
      <div class="calendar-summary-strip">
        <div class="calendar-summary-card focus">
          <strong>Today's Focus</strong>
          <span id="calendar-focus-title">Loading focus lane…</span>
          <em id="calendar-focus-sub">Finding the best protected block.</em>
        </div>
        <div class="calendar-summary-card">
          <strong>Scheduled</strong>
          <span id="calendar-stat-scheduled">—</span>
          <em id="calendar-stat-scheduled-sub">events</em>
        </div>
        <div class="calendar-summary-card">
          <strong>Focus Time</strong>
          <span id="calendar-stat-focus">—</span>
          <em id="calendar-stat-focus-sub">hours</em>
        </div>
        <div class="calendar-summary-card">
          <strong>Meeting Load</strong>
          <span id="calendar-stat-meetings">—</span>
          <em id="calendar-stat-meetings-sub">balanced</em>
        </div>
        <div class="calendar-summary-card">
          <strong>Travel Time</strong>
          <span id="calendar-stat-travel">—</span>
          <em id="calendar-stat-travel-sub">route-sensitive</em>
        </div>
        <div class="calendar-summary-card">
          <strong>Energy Outlook</strong>
          <span id="calendar-stat-energy">—</span>
          <em id="calendar-stat-energy-sub">peak window</em>
        </div>
        <div class="calendar-summary-card">
          <strong>Schedule Health</strong>
          <span id="calendar-stat-health">—</span>
          <em id="calendar-stat-health-sub">well balanced</em>
        </div>
      </div>
      <div class="calendar-motto">
        <strong>"A well-planned day protects your calling and your family."</strong>
        <span id="calendarDateLabel">Loading date…</span>
      </div>
    </div>

    <div class="calendar-desktop">
      <aside class="calendar-sidebar">
        <div class="calendar-sidebar-brand">
          <div>
            <strong>JARVIS</strong>
            <span>Calendar</span>
          </div>
          <div class="calendar-sidebar-mark">⌁</div>
        </div>
        <div class="calendar-sidebar-nav">
          <button class="calendar-sidebar-item active" type="button" data-calendar-nav="1" onclick="calendarSidebarAction('page', {{ page: 1 }})">⌂ Home</button>
          <button class="calendar-sidebar-item" type="button" data-calendar-route="briefing" onclick="calendarSidebarAction('route', {{ route: '/briefing-center', fallbackView: 'overview', action: 'Open Daily Brief', detail: 'Calendar opened Daily Brief for fuller agenda context.' }})">◷ Daily Brief</button>
          <button class="calendar-sidebar-item" type="button" data-calendar-route="mission" onclick="calendarSidebarAction('route', {{ route: '/mission-board', fallbackView: 'notifications', action: 'Open Mission Board', detail: 'Calendar opened Mission Board for linked execution pressure.' }})">◫ Mission Board</button>
          <button class="calendar-sidebar-item" type="button" data-calendar-route="navigate" onclick="calendarSidebarAction('route', {{ route: '/navigation-center', fallbackView: 'navigate', action: 'Open Travel & Route', detail: 'Calendar opened Navigation for route-sensitive commitments.' }})">⇄ Travel & Route</button>
          <button class="calendar-sidebar-item" type="button" data-calendar-nav="4" onclick="calendarSidebarAction('page', {{ page: 4 }})">◉ Family Calendar</button>
          <button class="calendar-sidebar-item" type="button" data-calendar-nav="2" onclick="calendarSidebarAction('page', {{ page: 2 }})">⧉ Focus Windows</button>
          <button class="calendar-sidebar-item" type="button" data-calendar-nav="5" onclick="calendarSidebarAction('page', {{ page: 5 }})">☰ Preparation Queue</button>
          <button class="calendar-sidebar-item" type="button" data-calendar-route="settings" onclick="calendarSidebarAction('route', {{ route: '/settings-center', fallbackView: 'home', action: 'Open Calendar Settings', detail: 'Calendar opened Settings because a dedicated calendar settings route is not exposed yet.' }})">⚙ Settings</button>
        </div>
        <div class="calendar-sidebar-status">
          <strong>Calendar Status</strong>
          <div class="calendar-sidebar-list">
            <div class="calendar-sidebar-row"><span>Sync Status</span><b id="calendar-sidebar-sync">Checking…</b></div>
            <div class="calendar-sidebar-row"><span>Sources</span><b id="calendar-sidebar-sources">0 connected</b></div>
            <div class="calendar-sidebar-row"><span>Conflicts</span><b id="calendar-sidebar-conflicts">0</b></div>
            <div class="calendar-sidebar-row"><span>Last Sync</span><b id="calendar-sidebar-last-sync">—</b></div>
          </div>
          <button class="calendar-sidebar-btn" onclick="calendarSidebarAction('route', {{ route: '/settings-center', fallbackView: 'home', action: 'Open Calendar Settings', detail: 'Calendar opened Settings because deeper calendar account controls live there today.' }})">Calendar Settings →</button>
        </div>
      </aside>

      <main class="calendar-main">
        <div class="calendar-desktop-topbar">
          <div class="calendar-nav-status">
            <div>
              <strong>Desktop Experience</strong>
              <span id="calendar-page-count">Page 1 of 1</span>
            </div>
            <div>
              <strong id="calendar-page-label">Week View</strong>
              <span>Live schedule intelligence</span>
            </div>
          </div>
          <div class="calendar-nav-actions">
            <button class="calendar-chip-btn" id="calendar-refresh-button" onclick="refreshCalendarDesktop(true)">Refresh Calendar</button>
            <button class="calendar-nav-btn" disabled aria-label="Previous calendar page">←</button>
            <button class="calendar-nav-btn" disabled aria-label="Next calendar page">→</button>
          </div>
        </div>
        <div class="calendar-subtitle" id="calendar-runtime-note" style="padding:0 4px 18px 4px;">Calendar is loading live schedule intelligence…</div>

        <div class="calendar-grid">
          <div style="display:flex;flex-direction:column;gap:16px;">
            <section class="calendar-panel">
              <div class="calendar-panel-header">
                <div>
                  <strong class="calendar-panel-title">1. Today At A Glance</strong>
                  <span class="calendar-panel-subtitle">The operating picture for the day.</span>
                </div>
                <button class="calendar-chip-btn" onclick="refreshCalendarDesktop(true)">Refresh</button>
              </div>
              <div class="calendar-today-list" id="calendarTodayList"></div>
            </section>

            <section class="calendar-panel">
              <div class="calendar-panel-header">
                <div>
                  <strong class="calendar-panel-title">2. Calendar Intelligence</strong>
                  <span class="calendar-panel-subtitle">Insights protecting the best version of your day.</span>
                </div>
              </div>
              <div class="calendar-insight-grid" id="calendarInsightGrid"></div>
            </section>
          </div>

          <section class="calendar-column">
            <div class="calendar-week-shell">
              <div class="calendar-week-topbar">
                <div>
                  <strong>3. Week View</strong>
                  <span id="calendarWeekLabel">Loading week…</span>
                </div>
                <div style="display:flex;gap:8px;align-items:center;">
                  <button class="calendar-chip-btn" onclick="calendarUnavailable('Day view is not wired as a distinct calendar surface yet in this runtime.')">Day</button>
                  <button class="calendar-chip-btn" onclick="calendarToast('Week view is active.', 'success')">Week</button>
                  <button class="calendar-chip-btn" onclick="calendarUnavailable('Month view is not wired as a distinct calendar surface yet in this runtime.')">Month</button>
                  <button class="calendar-chip-btn" onclick="calendarSidebarAction('route', {{ route: '/navigation-center', fallbackView: 'navigate', action: 'Open Travel & Route', detail: 'Calendar opened Navigation from the week view route control.' }})">Route</button>
                </div>
              </div>
              <div class="calendar-week-grid" id="calendarWeekGrid"></div>
            </div>
          </section>

          <div style="display:flex;flex-direction:column;gap:16px;">
            <section class="calendar-panel">
              <div class="calendar-panel-header">
                <div>
                  <strong class="calendar-panel-title">5. Attention Routing</strong>
                  <span class="calendar-panel-subtitle">What needs your attention and when.</span>
                </div>
                <button class="calendar-chip-btn" onclick="calendarSidebarAction('route', {{ route: '/approval-queue', fallbackView: 'notifications', action: 'Review Schedule Attention', detail: 'Calendar opened the approval and attention lane for deeper review.' }})">Review All Items →</button>
              </div>
              <div class="calendar-attention-list" id="calendarAttentionList"></div>
            </section>

            <section class="calendar-panel">
              <div class="calendar-panel-header">
                <div>
                  <strong class="calendar-panel-title">6. Calendar Health</strong>
                  <span class="calendar-panel-subtitle">How protected and balanced your schedule feels.</span>
                </div>
              </div>
              <div class="calendar-health-ring" id="calendarHealthRing">
                <div class="calendar-health-center">
                  <div>
                    <strong id="calendarHealthScore">—</strong>
                    <span id="calendarHealthGrade">Healthy</span>
                  </div>
                </div>
              </div>
              <div class="calendar-health-list" id="calendarHealthList"></div>
            </section>

            <section class="calendar-panel">
              <div class="calendar-panel-header">
                <div>
                  <strong class="calendar-panel-title">7. Quick Actions</strong>
                  <span class="calendar-panel-subtitle">Control the schedule without leaving the command surface.</span>
                </div>
              </div>
              <div class="calendar-quick-grid">
                <button class="calendar-quick-btn" onclick="calendarHandleAction('create-event')">Add Event<span>Create a commitment</span></button>
                <button class="calendar-quick-btn" onclick="calendarHandleAction('focus-block')">Focus Block<span>Protect deep work</span></button>
                <button class="calendar-quick-btn" onclick="calendarSidebarAction('route', {{ route: '/navigation-center', fallbackView: 'navigate', action: 'Open Travel Plan', detail: 'Calendar handed travel planning into Navigation.' }})">Travel Plan<span>Open routing intelligence</span></button>
                <button class="calendar-quick-btn" onclick="calendarHandleAction('find-time')">Find Time<span>Resolve the right slot</span></button>
                <button class="calendar-quick-btn" onclick="calendarHandleAction('reschedule')">Reschedule<span>Shift with context</span></button>
                <button class="calendar-quick-btn" onclick="calendarHandleAction('sync-sources')">Sync Sources<span>Refresh connected calendars</span></button>
              </div>
            </section>

            <section class="calendar-panel">
              <div class="calendar-panel-header">
                <div>
                  <strong class="calendar-panel-title">8. Calendar Sources</strong>
                  <span class="calendar-panel-subtitle">The calendars behind the orchestration.</span>
                </div>
              </div>
              <div class="calendar-source-list" id="calendarSourceList"></div>
            </section>
          </div>
        </div>

        <div class="calendar-bottom-grid">
          <section class="calendar-panel">
            <div class="calendar-panel-header">
              <div>
                <strong class="calendar-panel-title">4. Upcoming Highlights</strong>
                <span class="calendar-panel-subtitle">The next seven days at a glance.</span>
              </div>
              <button class="calendar-chip-btn" onclick="calendarSidebarAction('route', {{ route: '/activity-center', fallbackView: 'journey', action: 'Open Calendar Timeline', detail: 'Calendar opened the shared activity and continuity timeline for deeper review.' }})">View Full Timeline →</button>
            </div>
            <div class="calendar-highlight-strip" id="calendarHighlightStrip"></div>
          </section>

          <section class="calendar-panel">
            <div class="calendar-panel-header">
              <div>
                <strong class="calendar-panel-title">Preparation Queue</strong>
                <span class="calendar-panel-subtitle">What JARVIS can stage before the day gets noisy.</span>
              </div>
            </div>
            <div class="calendar-insight-list" id="calendarPrepQueue"></div>
          </section>
        </div>
      </main>
    </div>
  </div>

  <!-- ═══════════════════════════════════════════════════════ HEALTH VIEW ═══ -->
  <div id="view-health" class="view health-view">
    <div class="health-header">
      <div>
        <div class="health-kicker">Desktop Experience</div>
        <div class="view-title">HEALTH INTELLIGENCE<div class="view-title-line"></div></div>
        <div class="health-subtitle">A real desktop health workspace for readiness, vitals, care coordination, coaching, medication adherence, and physician-agent consultation. One screen is active at a time, with arrows and a page count guiding the flow.</div>
      </div>
      <div class="health-motto">
        <div class="health-motto-mark">∿</div>
        <div>
          <strong>Personalized. Proactive. Private.</strong>
          <span>JARVIS looks after the details so you can live your life.</span>
        </div>
      </div>
    </div>

    <div class="health-desktop-stage">
      <div class="health-desktop-shell">
        <aside class="health-sidebar">
          <div class="health-sidebar-top">
            <div class="health-sidebar-brand">
              <strong>JARVIS</strong>
              <span>Health</span>
            </div>
            <div class="health-sidebar-mark">✦</div>
          </div>
          <div class="health-sidebar-nav">
            <button class="health-sidebar-item active" type="button" data-health-nav="1" onclick="setHealthPage(1)">⌂ Command Center</button>
            <button class="health-sidebar-item" type="button" data-health-nav="2" onclick="setHealthPage(2)">◔ Vitals</button>
            <button class="health-sidebar-item" type="button" data-health-nav="3" onclick="setHealthPage(3)">⌁ Trends</button>
            <button class="health-sidebar-item" type="button" data-health-nav="4" onclick="setHealthPage(4)">✦ Coach</button>
            <button class="health-sidebar-item" type="button" data-health-nav="5" onclick="setHealthPage(5)">◉ Medications</button>
            <button class="health-sidebar-item" type="button" data-health-nav="6" onclick="setHealthPage(6)">♡ Care</button>
            <button class="health-sidebar-item" type="button" onclick="setHealthPage(4)">◫ Nutrition</button>
            <button class="health-sidebar-item" type="button" onclick="setHealthPage(4)">◌ Fitness</button>
            <button class="health-sidebar-item" type="button" onclick="setHealthPage(4)">◍ Mind Health</button>
            <button class="health-sidebar-item" type="button" onclick="setHealthPage(3)">☷ Labs</button>
            <button class="health-sidebar-item" type="button" onclick="openHealthDesktopExperience()">☰ Reports</button>
            <button class="health-sidebar-item" type="button" onclick="openHealthDesktopExperience()">⚙ Settings</button>
          </div>
          <div class="health-sidebar-runtime">
            <strong>Runtime</strong>
            <div id="health-runtime-note" class="health-sidebar-runtime-note">Health is loading live signals…</div>
          </div>
          <div class="health-sidebar-foot">
            <button class="health-sidebar-item" id="health-refresh-button" type="button" onclick="refreshHealthDesktop(true)">↻ Refresh Health</button>
            <div class="health-sidebar-user">
              <strong>Chris</strong>
              Personal profile
            </div>
          </div>
        </aside>

        <main class="health-main">
          <div class="health-topbar">
            <div class="health-topbar-copy">
              <div class="health-topbar-kicker">Desktop Sequence</div>
              <div class="health-topbar-title" id="health-nav-title">1. Health Command Center</div>
              <div class="health-topbar-subtitle" id="health-nav-subtitle">Open the health command center: readiness, sleep, blood pressure, Helen Cho guidance, and the next medically useful step.</div>
            </div>
            <div class="health-nav">
              <button class="health-nav-btn" id="health-nav-prev" onclick="advanceHealthPage(-1)" aria-label="Previous Health page">←</button>
              <div class="health-nav-status">
                <div class="health-nav-page" id="health-page-count">Page 1 of 6</div>
                <div class="health-nav-title" id="health-page-label">Command Center</div>
              </div>
              <button class="health-nav-btn" id="health-nav-next" onclick="advanceHealthPage(1)" aria-label="Next Health page">→</button>
            </div>
          </div>

          <div class="health-page-deck">
            <section class="health-page active" data-health-page="1">
              <div class="health-grid-hero">
                <div class="health-card">
                  <div class="health-card-heading">
                    <div class="health-card-label">Health Command Center<strong>Good morning, Chris.</strong></div>
                    <span id="health-last-sync">—</span>
                  </div>
                  <div class="health-stat-row">
                    <div class="health-panel">
                      <div class="health-card-label">Daily Readiness<strong>Today’s command signal</strong></div>
                      <div class="health-score-panel" id="daily-score-panel">
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
                        <div style="flex:1;min-width:0;">
                          <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:8px;">
                            <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--text-2);">Daily Health Score</div>
                            <div id="dhs-date" style="font-size:10px;color:var(--text-3);">Today</div>
                          </div>
                          <div id="dhs-breakdown" style="margin-bottom:10px;"></div>
                          <div>
                            <div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--text-3);margin-bottom:4px;">30-Day Trend</div>
                            <svg id="dhs-sparkline" class="sparkline-svg" viewBox="0 0 280 44" preserveAspectRatio="none">
                              <text x="140" y="24" text-anchor="middle" fill="rgba(255,255,255,0.2)" font-size="10">Loading…</text>
                            </svg>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div class="health-panel">
                      <div class="health-card-label">Helen Cho<strong>Medical intelligence summary</strong></div>
                      <div id="helen-assessment-card" style="border-left:3px solid var(--health-teal);padding-left:14px;">
                        <div style="display:flex;align-items:flex-start;gap:18px;">
                          <div style="text-align:center;flex-shrink:0;">
                            <div id="helen-score" style="font-size:52px;font-weight:800;color:var(--amber);font-family:var(--font-mono);line-height:1;">—</div>
                            <div id="helen-grade" style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--text-2);margin-top:2px;">Analysing…</div>
                            <div id="helen-risk-badge" style="margin-top:6px;display:inline-block;padding:2px 8px;border-radius:10px;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;background:var(--surface-2);color:var(--text-3);">—</div>
                          </div>
                          <div style="flex:1;min-width:0;">
                            <div style="font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--health-teal);margin-bottom:4px;">Helen Cho · Medical Intelligence</div>
                            <div id="helen-headline" style="font-size:14px;font-weight:600;color:var(--text-1);margin-bottom:8px;line-height:1.4;">Loading health analysis…</div>
                            <div id="helen-narrative" style="font-size:11px;color:var(--text-2);line-height:1.7;max-height:120px;overflow:hidden;position:relative;">
                              <div id="helen-narrative-text"></div>
                              <div id="helen-narrative-fade" style="position:absolute;bottom:0;left:0;right:0;height:30px;background:linear-gradient(transparent,var(--surface-1));display:none;"></div>
                            </div>
                            <button id="helen-expand-btn" onclick="helenToggleNarrative()" style="display:none;font-size:10px;color:var(--health-teal);background:none;border:none;cursor:pointer;padding:4px 0;margin-top:2px;">Show more ▾</button>
                          </div>
                        </div>
                        <div id="helen-positives" style="display:none;padding:8px 10px;background:rgba(16,185,129,0.08);border-radius:6px;border:1px solid rgba(16,185,129,0.2);font-size:10px;color:var(--green);margin-top:12px;"></div>
                      </div>
                    </div>
                  </div>
                  <div id="health-metrics-strip" class="health-grid-three">
                    <div class="health-mini-card">
                      <strong>A1c</strong>
                      <p><span id="hm-a1c">7.3</span>% · target &lt; 7.0</p>
                      <div id="spark-a1c" class="hm-sparkline"></div>
                    </div>
                    <div class="health-mini-card">
                      <strong>Blood Pressure</strong>
                      <p><span id="hm-bp">—/—</span> mmHg <span id="hm-bp-arrow">→</span></p>
                      <div id="spark-bp" class="hm-sparkline"></div>
                    </div>
                    <div class="health-mini-card">
                      <strong>Sleep Recovery</strong>
                      <p><span id="hm-sleep">—</span> hrs · <span id="hm-hrv">—</span> ms HRV</p>
                      <div id="spark-sleep" class="hm-sparkline"></div>
                    </div>
                    <div class="health-mini-card">
                      <strong>Resting Heart Rate</strong>
                      <p><span id="hm-egfr">—</span> eGFR watch · <span id="hm-weight">—</span> lbs</p>
                      <div id="spark-egfr" class="hm-sparkline"></div>
                    </div>
                    <div class="health-mini-card">
                      <strong>Movement</strong>
                      <p><span id="hm-steps">—</span> steps today</p>
                      <div id="spark-steps" class="hm-sparkline"></div>
                    </div>
                    <div class="health-mini-card">
                      <strong>Lipid Watch</strong>
                      <p><span id="hm-ldl">—</span> mg/dL LDL</p>
                      <div id="spark-ldl" class="hm-sparkline"></div>
                    </div>
                  </div>
                </div>
                <div class="health-side-stack">
                  <div class="health-card">
                    <div class="health-card-heading">
                      <div class="health-card-label">Physician Agents<strong>Your care intelligence circle</strong></div>
                    </div>
                    <div class="health-physician-grid" id="health-physician-roster">
                      <div class="skel" style="height:128px;border-radius:16px;"></div>
                      <div class="skel" style="height:128px;border-radius:16px;"></div>
                      <div class="skel" style="height:128px;border-radius:16px;"></div>
                    </div>
                  </div>
                  <div class="health-card">
                    <div class="health-card-heading">
                      <div class="health-card-label">Priority Actions<strong>What JARVIS wants you to address</strong></div>
                      <button class="btn btn-hue btn-sm" onclick="helenRefresh()" id="helen-refresh-btn" style="font-size:10px;">↻ Refresh Analysis</button>
                    </div>
                    <div id="helen-actions" style="display:flex;flex-direction:column;gap:6px;">
                      <div style="font-size:11px;color:var(--text-3);padding:8px 0;">Generating action plan…</div>
                    </div>
                    <div id="helen-action-count" style="display:none;"></div>
                  </div>
                  <div class="health-card">
                    <div class="health-card-heading">
                      <div class="health-card-label">Quick Controls<strong>Move directly to what matters</strong></div>
                    </div>
                    <div class="health-action-row">
                      <button class="faith-action-btn primary" type="button" onclick="setHealthPage(6)">Open Consultation</button>
                      <button class="faith-action-btn muted" type="button" onclick="openVitalsEntry()">Log vitals</button>
                      <button class="faith-action-btn muted" type="button" onclick="openHealthDesktopExperience()">Open full desktop page</button>
                    </div>
                    <div class="health-action-row" style="margin-top:8px;">
                      <button class="faith-action-btn muted" type="button" onclick="healthManualCheckin()">Manual check-in</button>
                      <button class="faith-action-btn muted" type="button" onclick="healthReviewLatestCheckin()">Review latest</button>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section class="health-page" data-health-page="2">
              <div class="health-grid-two">
                <div class="health-card">
                  <div class="health-card-heading">
                    <div class="health-card-label">Morning Health Brief<strong>JARVIS Morning Brief</strong></div>
                    <span class="faith-chip">Live</span>
                  </div>
                  <div class="health-audio-halo">∿</div>
                  <div class="health-panel">
                    <div class="health-card-label">Today’s Readiness<strong>How you woke up</strong></div>
                    <div class="health-values-row">
                      <div class="health-mini-card">
                        <strong id="health-readiness-score">—</strong>
                        <p id="health-readiness-grade">—</p>
                      </div>
                      <div class="health-mini-card">
                        <strong id="health-sleep-hours">—</strong>
                        <p>Hours slept</p>
                      </div>
                      <div class="health-mini-card">
                        <strong id="health-hrv-value">—</strong>
                        <p>HRV balanced</p>
                      </div>
                      <div class="health-mini-card">
                        <strong id="health-bp-value">—/—</strong>
                        <p>Blood pressure</p>
                      </div>
                      <div class="health-mini-card">
                        <strong id="health-bp-pulse">—</strong>
                        <p>Pulse</p>
                      </div>
                      <div class="health-mini-card">
                        <strong id="health-weight-value">—</strong>
                        <p>Weight</p>
                      </div>
                    </div>
                  </div>
                  <div class="health-panel">
                    <div class="health-card-label">Helen’s Morning Narrative<strong>What to watch first</strong></div>
                    <p id="health-readiness-message">Loading today’s guidance…</p>
                    <div id="health-readiness-factors"></div>
                  </div>
                </div>
                <div class="health-side-stack">
                  <div class="health-card">
                    <div class="health-card-heading">
                      <div class="health-card-label">Overnight Summary<strong>Context before you move</strong></div>
                    </div>
                    <div class="health-mini-list">
                      <div class="health-mini-row"><span>Sleep window</span><strong id="health-bp-date">—</strong></div>
                      <div class="health-mini-row"><span>Omron status</span><strong id="helen-omron-status-text">Not configured</strong></div>
                      <div class="health-mini-row"><span>Apple Health</span><strong id="health-apple-badge">—</strong></div>
                      <div class="health-mini-row"><span>Sync</span><strong id="mychart-sync-status">Waiting</strong></div>
                    </div>
                  </div>
                  <div class="health-card">
                    <div class="health-card-heading">
                      <div class="health-card-label">Today’s Recommendation<strong>Move more, stress less</strong></div>
                    </div>
                    <p>Use the coach, care, and physician pages below to decide whether today is a recovery day, a planning day, or a push day.</p>
                    <div class="health-action-row">
                      <button class="faith-action-btn primary" type="button" onclick="setHealthPage(4)">Open Coaching Studio</button>
                      <button class="faith-action-btn muted" type="button" onclick="setHealthPage(3)">Open Trends</button>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section class="health-page" data-health-page="3">
              <div class="health-vitals-grid">
                <div class="health-card">
                  <div class="health-card-heading">
                    <div class="health-card-label">Vitals &amp; Trends Analysis<strong>Today’s vitals</strong></div>
                    <span class="card-badge" id="health-omron-badge">Omron</span>
                  </div>
                  <div class="health-panel" id="health-metrics-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                    <div style="font-size:11px;color:var(--text-3);">No data yet</div>
                  </div>
                  <div class="health-grid-three" style="margin-top:18px;">
                    <div class="health-mini-card">
                      <strong>Blood Pressure</strong>
                      <p id="health-bp-history">No readings yet</p>
                      <div id="health-omron-connect-section" style="margin-top:8px;">
                        <button class="btn-ghost" onclick="omronConnect()" id="health-omron-btn" style="font-size:10px;">Connect Omron</button>
                      </div>
                    </div>
                    <div class="health-mini-card">
                      <strong>ECG</strong>
                      <div id="health-ecg-list" style="padding-top:6px;">
                        <div style="font-size:11px;color:var(--text-3);">Loading…</div>
                      </div>
                    </div>
                    <div class="health-mini-card">
                      <strong>Key Trends</strong>
                      <div id="helen-key-trends" style="padding-top:6px;display:grid;gap:8px;">
                        <div style="font-size:11px;color:var(--text-3);">Loading…</div>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="health-side-stack">
                  <div class="health-card">
                    <div class="health-card-heading">
                      <div class="health-card-label">Lab Trends<strong>High-level movement</strong></div>
                    </div>
                    <div class="health-grid-three">
                      <div class="health-mini-card"><strong>A1c</strong><div id="spark-lab-a1c" style="height:36px;"></div></div>
                      <div class="health-mini-card"><strong>LDL</strong><div id="spark-lab-ldl" style="height:36px;"></div></div>
                      <div class="health-mini-card"><strong>eGFR</strong><div id="spark-lab-egfr" style="height:36px;"></div></div>
                      <div class="health-mini-card"><strong>K+</strong><div id="spark-lab-kplus" style="height:36px;"></div></div>
                    </div>
                  </div>
                  <div class="health-card">
                    <div class="health-card-heading">
                      <div class="health-card-label">Lab Alerts<strong>Signals that need attention</strong></div>
                    </div>
                    <div id="helen-lab-alerts">
                      <div style="font-size:11px;color:var(--text-3);">Loading…</div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section class="health-page" data-health-page="4">
              <div class="health-grid-two">
                <div class="health-card">
                  <div class="health-card-heading">
                    <div class="health-card-label">Recovery &amp; Coaching Studio<strong>Sam Wilson daily check-in</strong></div>
                    <span id="sam-streak-badge" class="card-badge" style="display:none;">🔥 0 day streak</span>
                  </div>
                  <div id="sam-checkin-banner-wrap">
                    <div class="sam-checkin-banner" id="sam-checkin-banner">
                      <div style="font-size:11px;color:var(--text-3);">Loading check-in…</div>
                    </div>
                  </div>
                  <div class="health-panel" style="margin-top:18px;">
                    <div class="health-card-label">Recommended Protocol<strong>Today’s plan</strong></div>
                    <div id="sam-protocol-content" style="padding-top:8px;">
                      <div style="font-size:11px;color:var(--text-3);">Loading protocol…</div>
                    </div>
                  </div>
                  <div id="sam-food-strip" style="margin-top:12px;display:none;">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                      <span style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-3);">Today’s Food Log</span>
                      <span id="sam-food-protein-label" style="font-size:10px;color:var(--text-3);font-family:var(--font-mono);">—g protein</span>
                    </div>
                    <div style="height:4px;background:var(--surface-3);border-radius:2px;margin-bottom:8px;overflow:hidden;">
                      <div id="sam-food-protein-bar" style="height:100%;width:0%;background:var(--blue);border-radius:2px;transition:width .4s ease;"></div>
                    </div>
                    <div id="sam-food-meals" style="font-size:11px;color:var(--text-2);display:flex;flex-wrap:wrap;gap:4px;"></div>
                  </div>
                  <div style="margin-top:10px;">
                    <div id="sam-chat-mode-bar" style="display:none;margin-bottom:6px;padding:5px 10px;background:var(--surface-3);border-radius:6px;font-size:11px;color:var(--blue);align-items:center;justify-content:space-between;">
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
                    <div style="display:flex;gap:6px;margin-top:6px;flex-wrap:wrap;">
                      <button class="btn-ghost" style="font-size:10px;padding:4px 10px;" onclick="samStartInterview()">📋 Diet Interview</button>
                      <button class="btn-ghost" style="font-size:10px;padding:4px 10px;" onclick="samSwitchMode('food')">🍽 Log Food</button>
                      <button class="btn-ghost" style="font-size:10px;padding:4px 10px;" onclick="openSamJournal()">📓 Daily Journal</button>
                    </div>
                  </div>
                </div>
                <div class="health-side-stack">
                  <div class="health-card">
                    <div class="health-card-heading">
                      <div class="health-card-label">Longevity Projection<strong>Actuarial + risk adjusted</strong></div>
                    </div>
                    <div id="health-longevity-content">
                      <div style="font-size:11px;color:var(--text-3);">Loading…</div>
                    </div>
                  </div>
                  <div class="health-card">
                    <div class="health-card-heading">
                      <div class="health-card-label">Digital Twin<strong>12-month projections</strong></div>
                    </div>
                    <div id="health-twin-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;">
                      <div style="font-size:11px;color:var(--text-3);">Loading projections…</div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section class="health-page" data-health-page="5">
              <div class="health-care-grid">
                <div class="health-card">
                  <div class="health-card-heading">
                    <div class="health-card-label">Medication, Care &amp; Adherence Command<strong>Conditions and goals</strong></div>
                  </div>
                  <div class="health-panel">
                    <div class="health-card-label">Conditions<strong>Active conditions and watch items</strong></div>
                    <div id="helen-conditions">
                      <div style="font-size:11px;color:var(--text-3);">Loading…</div>
                    </div>
                  </div>
                  <div class="health-panel" style="margin-top:16px;">
                    <div class="health-card-label">Treatment Goals<strong>What the plan is trying to move</strong></div>
                    <div id="helen-goals">
                      <div style="font-size:11px;color:var(--text-3);">Loading…</div>
                    </div>
                  </div>
                </div>
                <div class="health-card">
                  <div class="health-card-heading">
                    <div class="health-card-label">Risk &amp; Adherence<strong>What matters over time</strong></div>
                  </div>
                  <div class="health-panel">
                    <div class="health-card-label">Cardiovascular Risk<strong>Current read</strong></div>
                    <div id="helen-cv-risk">
                      <div style="font-size:11px;color:var(--text-3);">Loading…</div>
                    </div>
                  </div>
                  <div class="health-panel" style="margin-top:16px;">
                    <div class="health-card-label">5-Year Trajectory<strong>Where this direction leads</strong></div>
                    <div id="helen-trajectory">
                      <div style="font-size:11px;color:var(--text-3);">Loading…</div>
                    </div>
                  </div>
                  <div class="health-panel" style="margin-top:16px;">
                    <div class="health-card-label">Medication Insights<strong>Optimization opportunities</strong></div>
                    <div id="helen-med-insights">
                      <div style="font-size:11px;color:var(--text-3);">Loading…</div>
                    </div>
                  </div>
                </div>
                <div class="health-side-stack">
                  <div class="health-card">
                    <div class="health-card-heading">
                      <div class="health-card-label">Specialty Profiles<strong>Deeper review surfaces</strong></div>
                    </div>
                    <div id="helen-diabetes-risk">
                      <div style="font-size:11px;color:var(--text-3);">Loading…</div>
                    </div>
                    <div id="helen-post-bariatric" style="margin-top:14px;">
                      <div style="font-size:11px;color:var(--text-3);">Loading…</div>
                    </div>
                  </div>
                  <div class="health-card">
                    <div class="health-card-heading">
                      <div class="health-card-label">Appointment Prep<strong>Questions and missing data</strong></div>
                    </div>
                    <div class="health-panel">
                      <div class="health-card-label">Questions for Dr. Wenk<strong id="helen-appt-date">Next visit</strong></div>
                      <div id="helen-doctor-questions">
                        <div style="font-size:11px;color:var(--text-3);">Loading…</div>
                      </div>
                    </div>
                    <div class="health-panel" style="margin-top:16px;">
                      <div class="health-card-label">Missing Data / Gaps<strong>Close these loops</strong></div>
                      <div id="helen-missing-data">
                        <div style="font-size:11px;color:var(--text-3);">Loading…</div>
                      </div>
                    </div>
                    <div class="health-action-row" style="margin-top:16px;">
                      <button class="faith-action-btn muted" type="button" onclick="healthSaveObjective()">Save Health Objective</button>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section class="health-page" data-health-page="6">
              <div class="health-voice-grid">
                <div class="health-card health-consult-card">
                  <div class="health-card-heading" style="padding:18px 18px 0;">
                    <div class="health-card-label">Voice &amp; Consultation<strong>Ask your medical team</strong></div>
                    <div class="health-action-row">
                      <button class="faith-action-btn muted" type="button" onclick="openVitalsEntry()">Log vitals</button>
                    </div>
                  </div>
                  <div class="hchat-wrap">
                    <div class="hchat-selector-bar">
                      <span class="hchat-selector-label">CONSULT WITH</span>
                      <div class="hchat-active-pill" id="hchat-active-pill" onclick="hchatToggleDropdown(event)">
                        <span class="hchat-active-pill-icon" id="hchat-active-icon">🧬</span>
                        <span class="hchat-active-pill-name" id="hchat-active-name">Helen Cho</span>
                        <span class="hchat-active-pill-arrow">▾</span>
                      </div>
                      <span class="hchat-active-pill-subtitle" id="hchat-active-title">Chief Medical Intelligence Officer</span>
                      <div class="hchat-dropdown" id="hchat-dropdown">
                        <div class="hchat-dropdown-label">Your Medical Team</div>
                        <div class="hchat-dropdown-grid" id="hchat-dropdown-grid"></div>
                      </div>
                    </div>
                    <div id="hchat-messages" style="flex:1;min-height:320px;max-height:420px;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px;scroll-behavior:smooth;">
                      <div style="text-align:center;color:var(--text-3);font-size:11px;padding:30px 20px;">
                        <div style="font-size:24px;margin-bottom:8px;">🧬</div>
                        <div style="font-weight:600;color:var(--text-2);margin-bottom:4px;">Helen Cho · Medical Intelligence</div>
                        <div>Ask me anything about your health, medications, labs, or longevity strategy.</div>
                      </div>
                    </div>
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
                <div class="health-side-stack">
                  <div class="health-card">
                    <div class="health-card-heading">
                      <div class="health-card-label">Physician Agents<strong>Direct access to Sam, Helen, and the rest</strong></div>
                    </div>
                    <div class="health-physician-grid" id="health-physician-roster-secondary">
                      <div class="skel" style="height:128px;border-radius:16px;"></div>
                      <div class="skel" style="height:128px;border-radius:16px;"></div>
                      <div class="skel" style="height:128px;border-radius:16px;"></div>
                    </div>
                  </div>
                  <div class="health-card">
                    <div class="health-card-heading">
                      <div class="health-card-label">Data Connections<strong>What the system can see</strong></div>
                    </div>
                    <div class="health-mini-list">
                      <div class="health-mini-row">
                        <span>Apple Health Auto Export</span>
                        <strong>Daily 7 AM</strong>
                      </div>
                      <div style="font-family:var(--font-mono);font-size:9px;background:var(--surface-2);padding:8px;border-radius:8px;color:var(--amber);word-break:break-all;">http://192.168.5.47:8787/api/health/ingest</div>
                      <div class="health-mini-row">
                        <span>MyChart Sync</span>
                        <strong id="mychart-sync-badge">Waiting</strong>
                      </div>
                      <div id="mychart-progress-wrap" style="display:none;margin-bottom:6px;">
                        <div style="background:var(--surface-2);border-radius:4px;height:4px;overflow:hidden;">
                          <div id="mychart-progress-bar" style="height:100%;background:var(--hue);width:0%;transition:width 0.4s;"></div>
                        </div>
                      </div>
                      <div class="health-action-row">
                        <button class="faith-action-btn muted" type="button" onclick="healthTestIngest()">Test ingest</button>
                        <button class="faith-action-btn muted" type="button" onclick="mychartStartSync()" id="mychart-sync-btn">Sync records</button>
                        <button class="faith-action-btn muted" type="button" onclick="mychartViewRecords()">View records</button>
                      </div>
                      <div class="health-action-row" style="margin-top:8px;">
                        <button class="faith-action-btn muted" type="button" onclick="healthRunTriage()">Symptom triage</button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <div style="display:none;">
            <div id="health-medical-records-section">
              <div id="health-medical-records"></div>
            </div>
            <div id="health-alerts"></div>
          </div>
        </main>
      </div>
    </div>
  </div><!-- end view-health -->

  <!-- ── HOME AUTOMATION ────────────────────────────────────── -->
  <div id="view-home" class="view" style="display:none; padding:0;">
    <div class="home-experience">
      <div class="home-headline">
        <div class="home-hero-title">
          <div class="home-kicker">Protect. Coordinate. Prepare. Restore.</div>
          <h1>JARVIS <span>HOME</span></h1>
          <p>The living operating picture of your household. Keep posture, systems, people, attention, and return-home readiness in one calm desktop workspace.</p>
        </div>
        <div class="home-quote">“A well-ordered home creates room for what matters most.”</div>
        <div class="home-profile-card">
          <div class="home-profile-avatar">{user_name[:1].upper()}</div>
          <div class="home-profile-meta">
            <strong>{user_name}</strong>
            <span id="home-profile-role">Executive Mode</span>
            <span id="home-profile-location">{home_location_label}</span>
          </div>
        </div>
      </div>

      <div class="home-top-metrics">
        <div class="home-stat-card">
          <div class="home-stat-label">Home Posture</div>
          <div class="home-stat-value" id="home-stat-posture">Calm &amp; Focused</div>
          <div class="home-stat-note good" id="home-stat-posture-note">Normal mode · low load</div>
        </div>
        <div class="home-stat-card">
          <div class="home-stat-label">Occupancy</div>
          <div class="home-stat-value" id="home-stat-occupancy">4 Home</div>
          <div class="home-stat-note" id="home-stat-occupancy-note">0 away · 0 arriving</div>
        </div>
        <div class="home-stat-card">
          <div class="home-stat-label">Home Mode</div>
          <div class="home-stat-value" id="home-stat-mode">Evening Wind-Down</div>
          <div class="home-stat-note" id="home-stat-mode-note">Quiet hours begin at 9:30 PM</div>
        </div>
        <div class="home-stat-card">
          <div class="home-stat-label">Environment</div>
          <div class="home-stat-value" id="home-stat-environment">72°F</div>
          <div class="home-stat-note" id="home-stat-environment-note">Comfort</div>
        </div>
        <div class="home-stat-card">
          <div class="home-stat-label">Safety Posture</div>
          <div class="home-stat-value" id="home-stat-safety">Secure</div>
          <div class="home-stat-note good" id="home-stat-safety-note">All clear</div>
        </div>
        <div class="home-stat-card">
          <div class="home-stat-label">Attention Load</div>
          <div class="home-stat-value" id="home-stat-load">Moderate</div>
          <div class="home-stat-note warn" id="home-stat-load-note">2 items to review</div>
        </div>
      </div>

      <div class="home-dashboard-grid">
        <section class="home-panel home-col-5">
          <div class="home-panel-header">
            <div>
              <h3>1. Household Posture</h3>
              <p>The current state of your home.</p>
            </div>
            <button type="button" class="home-action-link" id="home-refresh-button" onclick="refreshHomeView(true)">Refresh Home</button>
          </div>
          <div class="home-lifestyle-hero">
            <div class="home-lifestyle-overlay">
              <div class="home-posture-tags">
                <div class="home-posture-tag" id="home-tag-mode">Evening Wind-Down</div>
                <div class="home-posture-tag" id="home-tag-quiet">Quiet Hours {home_quiet_start} - {home_quiet_end}</div>
                <div class="home-posture-tag" id="home-tag-focus">Focus Mode</div>
              </div>
              <div class="home-posture-note" id="home-posture-note">House is calm and settling into evening. Minimal activity expected.</div>
            </div>
          </div>
          <div class="home-chip-grid" id="home-posture-metrics"></div>
        </section>

        <section class="home-panel home-col-4">
          <div class="home-panel-header">
            <div>
              <h3>2. Home Nervous System</h3>
              <p>Live status of critical systems.</p>
            </div>
            <button type="button" class="home-action-link" onclick="homeOpenRoute('/vision-center', 'vision', 'Opening live home system detail.')">View All Systems</button>
          </div>
          <div class="home-nerve-grid" id="home-system-grid"></div>
        </section>

        <section class="home-panel home-col-3">
          <div class="home-panel-header">
            <div>
              <h3>3. People At Home</h3>
              <p>Who’s home, away, and when.</p>
            </div>
            <button type="button" class="home-action-link" onclick="homeOpenRoute('/activity-center', 'activity', 'Opening shared continuity and presence activity.')">View All</button>
          </div>
          <div class="home-people-list" id="home-people-list"></div>
        </section>

        <section class="home-panel home-col-3">
          <div class="home-panel-header">
            <div>
              <h3>4. Today At Home</h3>
              <p>The day’s rhythm and pressures.</p>
            </div>
          </div>
          <div class="home-today-list" id="home-today-list"></div>
          <div class="home-attention-banner" style="margin-top:14px;">
            <strong id="home-attention-title">Attention Load: Moderate</strong>
            <span id="home-attention-copy">2 household items awaiting review.</span>
          </div>
        </section>

        <section class="home-panel home-col-4">
          <div class="home-panel-header">
            <div>
              <h3>5. Attention &amp; Household Queue</h3>
              <p>What needs review or action.</p>
            </div>
            <button type="button" class="home-action-link" onclick="homeOpenRoute('/workshop', 'workshop', 'Opening the shared task and execution lane.')">Review All</button>
          </div>
          <div class="home-queue-list" id="home-queue-list"></div>
        </section>

        <section class="home-panel home-col-4">
          <div class="home-panel-header">
            <div>
              <h3>6. While You Were Away</h3>
              <p>What happened while you were away.</p>
            </div>
            <button type="button" class="home-action-link" onclick="homeOpenRoute('/activity-center', 'activity', 'Opening the recent household continuity lane.')">Since Yesterday</button>
          </div>
          <div class="home-away-list" id="home-away-list"></div>
        </section>

        <section class="home-panel home-col-4">
          <div class="home-panel-header">
            <div>
              <h3>7. Trusted Home Actions</h3>
              <p>What JARVIS can do for your home.</p>
            </div>
            <button type="button" class="home-action-link" onclick="homeOpenRoute('/settings-center', 'settings', 'Opening settings for boundary and trust review.')">Manage Trust</button>
          </div>
          <div class="home-trusted-grid" id="home-trusted-grid"></div>
        </section>

        <section class="home-panel home-col-3">
          <div class="home-panel-header">
            <div>
              <h3>8. Home Health Score</h3>
              <p>Overall health of your household.</p>
            </div>
          </div>
          <div class="home-health-shell">
            <div class="home-ring" id="home-health-ring">
              <div class="home-ring-center">
                <strong id="home-health-score">87%</strong>
                <span id="home-health-score-note">Healthy</span>
              </div>
            </div>
            <div class="home-score-list" id="home-score-list"></div>
          </div>
        </section>

        <section class="home-panel home-col-5">
          <div class="home-panel-header">
            <div>
              <h3>9. Home Modes</h3>
              <p>One tap to set the right atmosphere.</p>
            </div>
            <button type="button" class="home-action-link" onclick="homeModeBoundaryNotice()">Customize Modes</button>
          </div>
          <div class="home-modes-grid" id="home-modes-grid"></div>
        </section>

        <section class="home-panel home-col-4">
          <div class="home-panel-header">
            <div>
              <h3>10. Spaces Overview</h3>
              <p>The state of key spaces in your home.</p>
            </div>
            <button type="button" class="home-action-link" onclick="homeOpenRoute('/vision-center', 'vision', 'Opening the vision and perception surface for space detail.')">View All Spaces</button>
          </div>
          <div class="home-spaces-grid" id="home-spaces-grid"></div>
        </section>

        <section class="home-panel home-col-3">
          <div class="home-panel-header">
            <div>
              <h3>11. Return Home Prep</h3>
              <p>Preparing you for a smooth return.</p>
            </div>
          </div>
          <div class="home-return-list" id="home-return-list"></div>
        </section>

        <section class="home-panel home-col-12">
          <div class="home-panel-header">
            <div>
              <h3>12. Home Insights</h3>
              <p>Insights to keep your home running well.</p>
            </div>
            <button type="button" class="home-action-link" onclick="homeOpenRoute('/command-center', 'chat', 'Opening command for broader household follow-through.')">See All Insights</button>
          </div>
          <div class="home-insight-list" id="home-insight-list"></div>
        </section>
      </div>

      <div class="home-footer-strip">
        <div class="home-footer-card"><strong>Safe &amp; Secure</strong><span>Protects what matters most.</span></div>
        <div class="home-footer-card"><strong>Calm by Design</strong><span>Creates peace, not noise.</span></div>
        <div class="home-footer-card"><strong>Anticipates Needs</strong><span>Prepares before you ask.</span></div>
        <div class="home-footer-card"><strong>Respects Boundaries</strong><span>Smart, not invasive.</span></div>
        <div class="home-footer-card"><strong>Acts Quietly</strong><span>Solves it so you don’t have to.</span></div>
        <div class="home-footer-card"><strong>Learns Continuously</strong><span>Gets smarter about your home and family.</span></div>
        <div class="home-footer-card live">
          <div>
            <strong>Home Engine Online</strong>
            <span id="home-footer-status">All systems operational</span>
            <span id="home-runtime-note">Home is loading live household posture.</span>
          </div>
          <div class="home-live-dot"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── NAVIGATE ─────────────────────────────────────────── -->
  <div id="view-navigate" class="view" style="display:none; padding:0">
    <div class="nav-experience">
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

      <div class="nav-headline">
        <div class="nav-hero-title">
          <div class="nav-kicker">Concept Storyboard</div>
          <h1>JARVIS <span>Navigation</span> Desktop Experience</h1>
          <p>Move from route planning to live guidance with a desktop shell that thinks in timing, smart stops, weather, household constraints, and voice-first consultation.</p>
        </div>
        <div class="nav-motto">
          <div class="nav-motto-icon">&#10022;</div>
          <div>
            <strong>Smarter routes. Better timing.</strong>
            <p>Fewer surprises. Coordinate stops, family constraints, traffic, and weather before the drive turns reactive.</p>
          </div>
        </div>
      </div>

      <div class="navigation-desktop-shell">
        <aside class="navigation-sidebar">
          <div class="navigation-brand">
            <div>
              <div class="navigation-brand-title">JARVIS</div>
              <div class="navigation-brand-sub">Navigation</div>
            </div>
            <div class="navigation-pulse">&#10148;</div>
          </div>
          <div class="navigation-side-nav">
            <button class="navigation-side-link active" type="button" data-navigation-page-link="1" onclick="setNavigationPage(1)">&#128506; Command Center</button>
            <button class="navigation-side-link" type="button" data-navigation-page-link="2" onclick="setNavigationPage(2)">&#128506; Map</button>
            <button class="navigation-side-link" type="button" data-navigation-page-link="3" onclick="setNavigationPage(3)">&#9733; Smart Stops</button>
            <button class="navigation-side-link" type="button" data-navigation-page-link="4" onclick="setNavigationPage(4)">&#128205; Stop Detail</button>
            <button class="navigation-side-link" type="button" data-navigation-page-link="5" onclick="setNavigationPage(5)">&#9729; Travel Plan</button>
            <button class="navigation-side-link" type="button" data-navigation-page-link="6" onclick="setNavigationPage(6)">&#128663; Voice</button>
            <button class="navigation-side-link" type="button" onclick="navigationSidebarAction('settings')">&#9881; Settings</button>
          </div>
          <div class="navigation-side-footer">
            <strong>Travel Context</strong>
            <p id="navigation-runtime-note">Navigation status is loading.</p>
            <div class="navigation-consult-actions" style="margin-top:12px;">
              <button type="button" id="navigation-refresh-button" onclick="refreshNavigateDesktop()">Refresh Navigation</button>
              <button type="button" onclick="navigationSidebarAction('module-route')">Open Navigation Center</button>
            </div>
          </div>
        </aside>

        <section class="navigation-main">
          <div class="navigation-topbar">
            <div class="navigation-title-block">
              <div class="navigation-title-row">
                <strong id="navigation-nav-title">1. Navigation Command Center</strong>
                <div class="navigation-title-line"></div>
              </div>
              <p id="navigation-nav-subtitle">Plan the route, understand the current window, and see which leave-time recommendation protects the rest of the schedule.</p>
            </div>
            <div class="navigation-storyboard-nav">
              <button class="navigation-nav-btn" id="navigation-nav-prev" onclick="advanceNavigationPage(-1)" aria-label="Previous Navigation page">&larr;</button>
              <div class="navigation-page-meta">
                <div class="navigation-nav-page" id="navigation-page-count">Page 1 of 6</div>
                <div class="navigation-page-label" id="navigation-page-label">Command Center</div>
              </div>
              <button class="navigation-nav-btn" id="navigation-nav-next" onclick="advanceNavigationPage(1)" aria-label="Next Navigation page">&rarr;</button>
            </div>
          </div>

          <div class="navigation-pages">
            <div class="navigation-page active" data-navigation-page="1">
              <div class="navigation-hero-grid">
                <div class="navigation-card">
                  <h3>Where do you want to go?</h3>
                  <div class="nav-route-inputs">
                    <div class="nav-home-actions">
                      <button class="nav-home-btn" onclick="navSetHome()" title="Set origin to Home">&#127968; Home</button>
                      <button class="nav-home-btn" onclick="navUseCurrentLocation()" title="Use GPS location">&#128205; My Location</button>
                    </div>
                    <div class="nav-input-row">
                      <div class="nav-input-pin">&#9679;</div>
                      <input id="nav-origin" class="nav-input" placeholder="Starting point..." oninput="navAutocomplete('nav-origin', 'nav-origin-results')">
                      <div id="nav-origin-results" class="nav-autocomplete-results"></div>
                    </div>
                    <div class="nav-input-row">
                      <div class="nav-input-pin" style="color:#e89b7e;">&#9679;</div>
                      <input id="nav-dest" class="nav-input" placeholder="Destination..." oninput="navAutocomplete('nav-dest', 'nav-dest-results')">
                      <div id="nav-dest-results" class="nav-autocomplete-results"></div>
                    </div>
                    <div class="nav-route-actions">
                      <button class="nav-swap-btn" onclick="navSwapInputs()">&#8645;</button>
                      <button class="nav-go-btn" onclick="navGetRoute()">Preview Route</button>
                    </div>
                  </div>
                  <div class="nav-summary-bar" id="nav-summary-bar" style="display:none">
                    <div class="nav-stat"><span id="nav-dist">--</span><label>Distance</label></div>
                    <div class="nav-stat"><span id="nav-time">--</span><label>Drive Time</label></div>
                    <div class="nav-stat"><span id="nav-eta">--</span><label>ETA</label></div>
                  </div>
                  <div class="navigation-insight-row" style="margin-top:16px;">
                    <div class="navigation-promo-card">
                      <strong>JARVIS Recommendation</strong>
                      <span id="nav-brief-recommendation">Preview a route to load shared route state and any live route intelligence this runtime can provide.</span>
                    </div>
                    <div class="navigation-promo-card">
                      <strong>Route Window</strong>
                      <span id="nav-brief-window">If live routing is unavailable here, JARVIS will say so plainly and keep the saved route context only.</span>
                    </div>
                  </div>
                </div>
                <div class="navigation-command-side">
                  <div class="navigation-card">
                    <h4>Active Route</h4>
                    <div class="navigation-hero-metrics">
                      <div class="navigation-metric"><strong id="nav-hero-eta">1h 24m</strong><span>Current drive estimate</span></div>
                      <div class="navigation-metric"><strong id="nav-hero-traffic">Light</strong><span>Traffic posture</span></div>
                      <div class="navigation-metric"><strong id="nav-hero-weather">72&deg;F</strong><span>Weather at departure</span></div>
                    </div>
                    <div class="navigation-route-overview" style="margin-top:14px;">
                      <div class="navigation-route-card">
                        <strong>Home</strong>
                        <span>Primary departure point for morning travel and family pickups.</span>
                      </div>
                      <div class="navigation-route-card">
                        <strong id="nav-overview-destination">Springfield, VA</strong>
                        <span id="nav-overview-destination-copy">Selected destination, recent arrival confidence 92%.</span>
                      </div>
                    </div>
                  </div>
                  <div class="navigation-card">
                    <h4>Recent Trips</h4>
                    <div class="navigation-recent-grid" id="navigation-recent-grid"></div>
                  </div>
                  <div class="navigation-card">
                    <h4>Saved Places</h4>
                    <div class="navigation-saved-grid" id="navigation-saved-grid"></div>
                  </div>
                </div>
              </div>
            </div>

            <div class="navigation-page" data-navigation-page="2">
              <div class="navigation-map-grid">
                <div class="navigation-map-frame">
                  <div class="nav-map-pane">
                    <div id="nav-map"></div>
                    <div class="nav-map-overlay">
                      <strong id="nav-map-eta-main">1h 24m</strong>
                      <span id="nav-map-distance-main">82 mi</span>
                      <span id="nav-map-risk-copy">Light traffic · low route risk</span>
                      <div class="nav-summary-chip" style="margin-top:10px;">Route context</div>
                    </div>
                    <div class="nav-map-tools">
                      <button class="nav-secondary-btn" onclick="navGetRoute()">Re-center</button>
                      <button class="nav-secondary-btn" onclick="advanceNavigationPage(3)">View Stops</button>
                    </div>
                  </div>
                </div>
                <div class="navigation-command-side">
                  <div class="navigation-card">
                    <h4>Route Overview</h4>
                    <div class="navigation-mini-grid">
                      <div class="navigation-mini-card"><strong id="nav-map-summary-home">Home</strong><span>Origin profile</span></div>
                      <div class="navigation-mini-card"><strong id="nav-map-summary-destination">Springfield</strong><span>Destination profile</span></div>
                      <div class="navigation-mini-card"><strong id="nav-map-summary-incidents">1</strong><span>Known incidents</span></div>
                      <div class="navigation-mini-card"><strong id="nav-map-summary-cost">2.75</strong><span>Estimated tolls</span></div>
                    </div>
                  </div>
                  <div class="navigation-card">
                    <h4>Upcoming</h4>
                    <div id="nav-turns-section" style="display:none">
                      <div id="nav-turns-list"></div>
                    </div>
                    <div id="nav-turns-placeholder">
                      <p>Once a route is loaded, the next guidance stack will appear here with mile markers and turning instructions.</p>
                    </div>
                  </div>
                  <div class="navigation-card">
                    <h4>Risk Signals</h4>
                    <div class="navigation-risks">
                      <div class="navigation-risk-card"><strong id="nav-risk-traffic">Low</strong><span>Traffic trend across the current corridor</span></div>
                      <div class="navigation-risk-card"><strong id="nav-risk-weather">Stable</strong><span>Weather effect during the drive window</span></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="navigation-page" data-navigation-page="3">
              <div class="navigation-stop-grid">
                <div class="navigation-card">
                  <h4>Filter route stops</h4>
                  <div class="nav-poi-toggles" id="nav-poi-toggles">
                    <button class="nav-poi-toggle active" data-cat="food" onclick="navTogglePOI('food')">&#127828; Food</button>
                    <button class="nav-poi-toggle active" data-cat="starbucks" onclick="navTogglePOI('starbucks')">&#9749; Starbucks</button>
                    <button class="nav-poi-toggle active" data-cat="parks" onclick="navTogglePOI('parks')">&#127794; Parks</button>
                    <button class="nav-poi-toggle active" data-cat="historic" onclick="navTogglePOI('historic')">&#127963; Historic</button>
                    <button class="nav-poi-toggle active" data-cat="family" onclick="navTogglePOI('family')">&#11088; Family</button>
                    <button class="nav-poi-toggle" data-cat="gas" onclick="navTogglePOI('gas')">&#9981; Gas</button>
                  </div>
                  <div class="nav-radius-row" id="nav-radius-row">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                      <span style="font-size:11px; opacity:0.7; text-transform:uppercase; letter-spacing:0.12em;">Parks and historic radius</span>
                      <span id="nav-parks-radius-label" style="font-size:13px; font-weight:700; color:#7ed391;">25 mi</span>
                    </div>
                    <input type="range" id="nav-parks-radius" class="nav-radius-slider"
                      min="5" max="100" step="5" value="25"
                      oninput="navUpdateParksRadius(this.value)"
                      onchange="if(_navRouteData) loadNavPOIs(_navRouteData)">
                    <div style="display:flex; justify-content:space-between; font-size:10px; opacity:0.45; margin-top:6px;">
                      <span>5 mi</span><span>25 mi</span><span>50 mi</span><span>100 mi</span>
                    </div>
                  </div>
                  <div id="nav-pois-section" style="display:none; margin-top:16px;">
                    <div id="nav-pois-list"></div>
                  </div>
                  <div id="nav-pois-placeholder" style="margin-top:16px;">
                    <p>Load a route to see Starbucks, food, scenic parks, family stops, and historic detours ranked along the drive.</p>
                  </div>
                </div>
                <div class="navigation-command-side">
                  <div class="navigation-card">
                    <h4>Stop Fit</h4>
                    <div class="navigation-mini-grid">
                      <div class="navigation-mini-card"><strong id="nav-stop-fit-fast">--</strong><span id="nav-stop-fit-fast-copy">Fast-stop posture will appear here.</span></div>
                      <div class="navigation-mini-card"><strong id="nav-stop-fit-meal">--</strong><span id="nav-stop-fit-meal-copy">Meal-stop posture will appear here.</span></div>
                      <div class="navigation-mini-card"><strong id="nav-stop-fit-scenic">--</strong><span id="nav-stop-fit-scenic-copy">Scenic-stop posture will appear here.</span></div>
                    </div>
                  </div>
                  <div class="navigation-card">
                    <h4>Optimization Note</h4>
                    <p id="nav-stop-optimizer-copy">Detours are approximate. JARVIS balances traffic, route confidence, fuel, and schedule preservation before adding any stop.</p>
                  </div>
                  <div class="navigation-card">
                    <h4>Route Memory</h4>
                    <div class="navigation-related-grid" id="navigation-related-grid"></div>
                  </div>
                </div>
              </div>
            </div>

            <div class="navigation-page" data-navigation-page="4">
              <div class="navigation-stop-grid">
                <div class="navigation-card">
                  <h4>Stop detail and route modification</h4>
                  <div class="nav-sv-shell">
                    <div id="nav-sv-panel" style="display:none;">
                      <img id="nav-sv-img" alt="Street View" onerror="this.style.display='none'">
                      <div class="nav-sv-caption" id="nav-sv-caption">Street-level preview will appear here when route steps are available.</div>
                    </div>
                    <div id="nav-sv-placeholder">
                      <p>Once a route is loaded, JARVIS will preview the next turn or stop area here so you know what the handoff looks like before you get there.</p>
                    </div>
                    <div class="navigation-detail-stats">
                      <div class="navigation-route-summary-grid">
                        <div class="navigation-mini-card"><strong id="nav-detail-detour">0.2 mi</strong><span>Detour distance</span></div>
                        <div class="navigation-mini-card"><strong id="nav-detail-time-impact">+1 min</strong><span>Time impact</span></div>
                        <div class="navigation-mini-card"><strong id="nav-detail-arrival">10:59 AM</strong><span>ETA after stop</span></div>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="navigation-command-side">
                  <div class="navigation-card">
                    <h4>Route Actions</h4>
                    <div class="navigation-stop-actions" id="navigation-stop-actions"></div>
                  </div>
                  <div class="navigation-card">
                    <h4>Compare Alternatives</h4>
                    <div class="navigation-alt-grid" id="navigation-alt-grid"></div>
                  </div>
                  <div class="navigation-card">
                    <h4>Why this stop works</h4>
                    <p id="nav-stop-fit-copy">Popular stop with fast service and predictable timing. JARVIS will highlight low-friction options first for travel days with tighter windows.</p>
                  </div>
                </div>
              </div>
            </div>

            <div class="navigation-page" data-navigation-page="5">
              <div class="navigation-plan-grid">
                <div class="navigation-card">
                  <h4>Travel orchestration and planning</h4>
                  <div class="navigation-route-summary-grid">
                    <div class="navigation-mini-card"><strong id="nav-plan-leave">9:38 AM</strong><span>Recommended departure</span></div>
                    <div class="navigation-mini-card"><strong id="nav-plan-arrive">10:58 AM</strong><span>Projected arrival</span></div>
                    <div class="navigation-mini-card"><strong id="nav-plan-distance">82 mi</strong><span>Distance</span></div>
                  </div>
                  <div class="navigation-card" style="margin-top:16px; padding:16px;">
                    <h4 style="margin-bottom:10px;">Trip timeline</h4>
                    <div class="navigation-timeline" id="navigation-plan-timeline"></div>
                  </div>
                </div>
                <div class="navigation-command-side">
                  <div class="navigation-card">
                    <h4>Travelers</h4>
                    <div class="navigation-travelers" id="navigation-travelers-card"></div>
                  </div>
                  <div class="navigation-card">
                    <h4>Constraints</h4>
                    <div class="navigation-constraints-grid" id="navigation-constraints-grid"></div>
                  </div>
                  <div class="navigation-card">
                    <h4>Weather Along Route</h4>
                    <div class="navigation-weather-grid" id="navigation-weather-grid"></div>
                  </div>
                </div>
              </div>
            </div>

            <div class="navigation-page" data-navigation-page="6">
              <div class="navigation-voice-grid">
                <div class="navigation-card">
                  <h4>Voice navigation consultation</h4>
                  <div class="navigation-chat" id="navigation-voice-chat"></div>
                  <div class="navigation-consult-actions">
                    <button type="button" onclick="navigationVoicePrompt('coffee')">Find coffee</button>
                    <button type="button" onclick="navigationVoicePrompt('weather')">Check weather</button>
                    <button type="button" onclick="navigationVoicePrompt('timing')">Leave-time advice</button>
                    <button type="button" onclick="navigationVoicePrompt('resume')">Resume route</button>
                  </div>
                  <div class="navigation-card" style="margin-top:16px; padding:0; background:transparent; border:none; box-shadow:none;">
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
                    <div class="navigation-voice-actions" style="margin-top:14px;">
                      <div class="navigation-stop-chip">
                        <strong>Voice Control</strong>
                        <span>Use spoken prompts for rerouting, stops, and timing.</span>
                      </div>
                      <div class="navigation-stop-chip" style="display:flex; align-items:center; justify-content:space-between; gap:12px;">
                        <div>
                          <strong>Controls</strong>
                          <span>Start or stop the live guidance session.</span>
                        </div>
                        <div style="display:flex; gap:10px; align-items:center;">
                          <button class="nav-voice-btn" id="nav-voice-btn" onclick="navToggleVoice()" title="Toggle voice">&#128266;</button>
                          <button class="nav-start-btn" id="nav-start-btn" onclick="startNavigation()" style="display:none">&#9654; Start Navigation</button>
                          <button class="nav-stop-btn" id="nav-stop-btn" onclick="stopNavigation()" style="display:none">&#9632; Stop</button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="navigation-command-side">
                  <div class="navigation-card">
                    <h4>Context</h4>
                    <div class="navigation-route-line"><span></span><div id="nav-voice-origin">Home</div></div>
                    <div class="navigation-route-line destination" style="margin-top:12px;"><span></span><div id="nav-voice-destination">Springfield</div></div>
                  </div>
                  <div class="navigation-card">
                    <h4>Trip Summary</h4>
                    <div class="navigation-mini-grid">
                      <div class="navigation-mini-card"><strong id="nav-voice-eta">10:58 AM</strong><span>Arrival</span></div>
                      <div class="navigation-mini-card"><strong id="nav-voice-distance">82 mi</strong><span>Distance</span></div>
                      <div class="navigation-mini-card"><strong id="nav-voice-traffic">Light</strong><span>Traffic</span></div>
                    </div>
                  </div>
                  <div class="navigation-card">
                    <h4>Recommended Next Action</h4>
                    <div class="navigation-promo-card">
                      <strong id="nav-voice-action-title">Preview route</strong>
                      <span id="nav-voice-action-copy">Best control point before the corridor starts adding uncertainty to the rest of the day.</span>
                    </div>
                  </div>
                  <div class="navigation-card">
                    <h4>Recent Route Continuity</h4>
                    <div class="navigation-related-grid" id="navigation-voice-activity"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>

  <!-- ── NEWS ──────────────────────────────────────────────── -->
  <div id="view-news" class="view" style="display:none; padding:0;">
    <div class="news-experience">
      <div class="news-desktop-headline">
        <div class="news-hero-title">
          <div class="news-kicker">Real news. Filtered. Contextualized. Actionable.</div>
          <h1>JARVIS <span>NEWS</span></h1>
          <p>Your personalized news intelligence engine. Understand the top stories, what matters to your world, where the risk sits, and what deserves attention instead of doom-scrolling.</p>
          <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:12px;">
            <span id="news-runtime-note" style="font-size:12px;color:var(--news-copy-muted);">News is live and connected.</span>
            <button class="news-link-chip" type="button" id="news-refresh-button" onclick="refreshNewsDesktop(true)">Refresh News</button>
          </div>
        </div>
        <div class="news-quote">“Stay informed, not overwhelmed. Understand. Discern. Act.”</div>
        <div class="news-profile-card">
          <div class="news-profile-avatar">{user_name[:1].upper()}</div>
          <div class="news-profile-meta">
            <strong>{user_name}</strong>
            <span>Executive Mode</span>
            <span id="news-profile-balance">Well balanced</span>
          </div>
        </div>
      </div>

      <div class="news-top-metrics">
        <div class="news-stat-card"><div class="news-stat-label">Top Stories</div><div class="news-stat-value" id="news-stat-top-stories">12</div><div class="news-stat-note good" id="news-stat-top-note">Fresh headlines</div></div>
        <div class="news-stat-card"><div class="news-stat-label">Breaking</div><div class="news-stat-value" id="news-stat-breaking">2</div><div class="news-stat-note warn" id="news-stat-breaking-note">Needs attention</div></div>
        <div class="news-stat-card"><div class="news-stat-label">Watching</div><div class="news-stat-value" id="news-stat-watching">8</div><div class="news-stat-note" id="news-stat-watching-note">Tracked themes</div></div>
        <div class="news-stat-card"><div class="news-stat-label">Sentiment Index</div><div class="news-stat-value" id="news-stat-sentiment">-0.18</div><div class="news-stat-note warn" id="news-stat-sentiment-note">Slightly negative</div></div>
        <div class="news-stat-card"><div class="news-stat-label">Information Quality</div><div class="news-stat-value" id="news-stat-quality">78%</div><div class="news-stat-note good" id="news-stat-quality-note">High</div></div>
        <div class="news-stat-card"><div class="news-stat-label">Time Saved</div><div class="news-stat-value" id="news-stat-time-saved">1h 24m</div><div class="news-stat-note" id="news-stat-time-note">vs. unfiltered news</div></div>
        <div class="news-stat-card"><div class="news-stat-label">News Balance</div><div class="news-stat-value" id="news-stat-balance">Well Balanced</div><div class="news-stat-note good" id="news-stat-balance-note">On target</div></div>
      </div>

      <div class="news-grid-desktop">
        <section class="news-panel news-col-4">
          <div class="news-panel-header">
            <div><h3>1. Top Stories</h3><p>The most important stories right now.</p></div>
            <button class="news-link-chip" type="button" onclick="newsHandleAction('open-top-stories')">View All</button>
          </div>
          <div class="news-story-hero" id="news-top-story"></div>
          <div class="news-list" id="news-top-story-list" style="margin-top:12px;"></div>
        </section>

        <section class="news-panel news-col-3">
          <div class="news-panel-header">
            <div><h3>2. News Briefing</h3><p>Your 2-minute intelligence brief.</p></div>
          </div>
          <div class="news-briefing-grid" id="news-briefing-grid"></div>
          <button class="news-link-chip" type="button" style="margin-top:12px; display:inline-flex;" onclick="newsHandleAction('open-briefing')">Read Full Briefing</button>
        </section>

        <section class="news-panel news-col-3">
          <div class="news-panel-header">
            <div><h3>3. Watchlist</h3><p>Stories and topics you’re tracking.</p></div>
            <button class="news-link-chip" type="button" onclick="newsHandleAction('manage-watchlist')">Manage</button>
          </div>
          <div class="news-watch-list" id="news-watch-list"></div>
        </section>

        <section class="news-panel news-col-2">
          <div class="news-panel-header">
            <div><h3>4. Sentiment &amp; Tone</h3><p>Overall tone of today’s news.</p></div>
          </div>
          <div class="news-sentiment-shell">
            <div class="news-sentiment-ring">
              <div class="news-sentiment-center">
                <strong id="news-sentiment-score">-0.18</strong>
                <span id="news-sentiment-label">Slightly Negative</span>
              </div>
            </div>
            <div class="news-sentiment-line"></div>
            <div class="news-sentiment-split" id="news-sentiment-split"></div>
          </div>
        </section>

        <section class="news-panel news-col-4">
          <div class="news-panel-header">
            <div><h3>5. News By Category</h3><p>Browse the news that matters to you.</p></div>
            <button class="news-link-chip" type="button" onclick="newsHandleAction('customize-feed')">Customize</button>
          </div>
          <div class="news-category-grid" id="news-category-grid"></div>
        </section>

        <section class="news-panel news-col-3">
          <div class="news-panel-header">
            <div><h3>6. Personalized Insights</h3><p>News insights tailored to your world.</p></div>
            <button class="news-link-chip" type="button" onclick="newsHandleAction('open-insights')">View All</button>
          </div>
          <div class="news-insight-list" id="news-insight-list"></div>
        </section>

        <section class="news-panel news-col-3">
          <div class="news-panel-header">
            <div><h3>7. Source Quality</h3><p>The sources behind your news.</p></div>
            <button class="news-link-chip" type="button" onclick="newsHandleAction('manage-sources')">Manage Sources</button>
          </div>
          <div class="news-source-list" id="news-source-list"></div>
        </section>

        <section class="news-panel news-col-2">
          <div class="news-panel-header">
            <div><h3>8. Local &amp; Weather</h3><p>What’s happening near you.</p></div>
            <button class="news-link-chip" type="button" onclick="newsHandleAction('open-weather')">View Details</button>
          </div>
          <div class="news-weather-list" id="news-weather-list"></div>
        </section>

        <section class="news-panel news-col-9">
          <div class="news-panel-header">
            <div><h3>9. Deep Dive Analysis</h3><p>In-depth analysis of the stories that matter most.</p></div>
          </div>
          <div class="news-deep-dive-grid" id="news-deep-dive-grid"></div>
        </section>

        <section class="news-panel news-col-3">
          <div class="news-panel-header">
            <div><h3>10. Quick Actions</h3><p>Tools to help you stay informed.</p></div>
          </div>
          <div class="news-actions-grid" id="news-actions-grid"></div>
        </section>
      </div>

      <div class="news-footer-strip">
        <div class="news-footer-card"><strong>Real News Only</strong><span>No opinion pieces unless requested.</span></div>
        <div class="news-footer-card"><strong>Balanced Perspective</strong><span>Multiple viewpoints. Clearly labeled bias.</span></div>
        <div class="news-footer-card"><strong>Time Intelligent</strong><span>Right news at the right time.</span></div>
        <div class="news-footer-card"><strong>Relevant To You</strong><span>Filtered for your life, work, and mission.</span></div>
        <div class="news-footer-card"><strong>Action Oriented</strong><span>What you can do with what you know.</span></div>
        <div class="news-footer-card"><strong>Privacy First</strong><span>Your interests stay private.</span></div>
        <div class="news-footer-card live"><div><strong>News Engine Online</strong><span id="news-footer-status">All systems operational</span></div><div class="news-live-dot"></div></div>
      </div>
    </div>
  </div>

  <!-- ── JOURNEY ────────────────────────────────────────────────────── -->
  <div id="view-journey" class="view journey-view" style="display:none;">
    <div class="view-header">
      <div>
        <div class="view-title">JARVIS JOURNEY<div class="view-title-line"></div></div>
        <div class="view-subtitle" id="journey-subtitle">The record of how JARVIS learns your world. Memory. Learning. Maturity. Impact.</div>
      </div>
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
        <span id="journey-runtime-note" style="font-size:12px;color:var(--journey-muted);">Journey is live and connected.</span>
        <button class="journey-btn" type="button" id="journey-refresh-button" onclick="refreshJourneyView()">Refresh Journey</button>
        <button class="journey-btn" type="button" onclick="journeyOpenRoute('/activity-center','journey','Open Activity Feed','Review the standalone Journey activity feed.')">Open Activity Feed</button>
      </div>
    </div>

    <div class="journey-header-stats">
      <div class="journey-stat-shell"><span>JARVIS Maturity Score</span><strong id="journey-maturity-score">—</strong><small id="journey-maturity-sub">Loading</small></div>
      <div class="journey-stat-shell"><span>Memory Depth</span><strong id="journey-memory-depth">—</strong><small id="journey-memory-sub">Loading</small></div>
      <div class="journey-stat-shell"><span>Preference Learning</span><strong id="journey-preference-score">—</strong><small id="journey-preference-sub">Loading</small></div>
      <div class="journey-stat-shell"><span>Agent Coordination</span><strong id="journey-agent-score">—</strong><small id="journey-agent-sub">Loading</small></div>
      <div class="journey-stat-shell"><span>Autonomy Trust</span><strong id="journey-autonomy-score">—</strong><small id="journey-autonomy-sub">Loading</small></div>
      <div class="journey-stat-shell"><span>System Health</span><strong id="journey-system-score">—</strong><small id="journey-system-sub">Loading</small></div>
      <div class="journey-quote-shell">
        <blockquote>“Intelligence grows with attention, context, and time.”</blockquote>
        <p>Journey turns memory, activity, trust, patterns, and learning posture into one readable operating record.</p>
      </div>
      <div class="journey-profile-shell">
        <div class="journey-profile-avatar">CB</div>
        <div><strong>Chris Binion</strong><span>Executive Mode</span></div>
      </div>
    </div>

    <div class="journey-grid">
      <section class="journey-card span-4">
        <div class="journey-card-inner">
          <div class="journey-card-header">
            <div><div class="journey-card-number">1. What JARVIS Learned</div><h3>Key insights and patterns discovered this week.</h3></div>
            <button class="journey-btn" type="button" onclick="journeyOpenRoute('/activity-center','journey','Open Activity Feed','Inspect the latest learning signals.')">View Activity Feed</button>
          </div>
          <div class="journey-list" id="journey-learned-list"></div>
        </div>
      </section>

      <section class="journey-card span-3">
        <div class="journey-card-inner">
          <div class="journey-card-header">
            <div><div class="journey-card-number">2. Accomplishments & Impact</div><h3>What JARVIS and your agents have done for you.</h3></div>
            <button class="journey-btn" type="button" onclick="journeyOpenRoute('/activity-center','journey','Open This Week','Review this week\\'s live Journey continuity.')">This Week</button>
          </div>
          <div class="journey-impact-grid" id="journey-impact-grid"></div>
        </div>
      </section>

      <section class="journey-card span-3">
        <div class="journey-card-inner">
          <div class="journey-card-header">
            <div><div class="journey-card-number">3. Agent Collaboration Intelligence</div><h3>How your agents are working together and creating value.</h3></div>
            <button class="journey-btn" type="button" onclick="journeyOpenRoute('/agent-ops-center','agents','Open Agent Network','Inspect live agent collaboration from Journey.')">Network View</button>
          </div>
          <div class="journey-collab-map" id="journey-collab-map"></div>
        </div>
      </section>

      <section class="journey-card span-2">
        <div class="journey-card-inner">
          <div class="journey-card-header">
            <div><div class="journey-card-number">4. Second Brain Map</div><h3>Your connected knowledge ecosystem.</h3></div>
            <button class="journey-btn" type="button" onclick="journeyOpenRoute('/chronicle-center','chronicle','Explore Memory Map','Inspect connected Chronicle continuity from Journey.')">Explore Map</button>
          </div>
          <div class="journey-brain-grid" id="journey-brain-grid"></div>
          <div class="journey-list-row" style="margin-top:12px;"><div><strong>Total Knowledge Nodes</strong><span id="journey-total-nodes">Loading…</span></div></div>
        </div>
      </section>

      <section class="journey-card span-4">
        <div class="journey-card-inner">
          <div class="journey-card-header">
            <div><div class="journey-card-number">5. Trust & Autonomy Development</div><h3>How JARVIS earns and expands your trust.</h3></div>
            <button class="journey-btn" type="button" onclick="journeyOpenRoute('/supervision-snapshot','chat','Manage Boundaries','Inspect supervision boundaries from Journey.')">Manage Boundaries</button>
          </div>
          <div class="journey-trust-grid" id="journey-trust-grid"></div>
        </div>
      </section>

      <section class="journey-card span-4">
        <div class="journey-card-inner">
          <div class="journey-card-header">
            <div><div class="journey-card-number">6. Pattern Library</div><h3>Reusable patterns JARVIS has discovered.</h3></div>
            <button class="journey-btn" type="button" onclick="journeyOpenRoute('/chronicle-center','chronicle','Open Chronicle','Inspect memory patterns from Journey.')">Open Chronicle</button>
          </div>
          <div class="journey-pattern-grid" id="journey-pattern-grid"></div>
        </div>
      </section>

      <section class="journey-card span-4">
        <div class="journey-card-inner">
          <div class="journey-card-header">
            <div><div class="journey-card-number">7. Memory Timeline</div><h3>Key moments in JARVIS’s learning journey.</h3></div>
            <button class="journey-btn" type="button" onclick="journeyOpenRoute('/activity-center','journey','Open Timeline','Inspect full Journey timeline.')">Open Timeline</button>
          </div>
          <div class="journey-timeline-list" id="journey-memory-timeline"></div>
          <div style="text-align:center;margin-top:14px;">
            <button class="journey-btn" onclick="loadJourneyMore()" id="journey-load-more" style="display:none;">Load more</button>
          </div>
        </div>
      </section>

      <section class="journey-card span-4">
        <div class="journey-card-inner">
          <div class="journey-card-header">
            <div><div class="journey-card-number">8. System Growth Over Time</div><h3>JARVIS maturity trend across key dimensions.</h3></div>
            <button class="journey-btn" type="button" onclick="journeyOpenRoute('/progress-center','activity','Open Progress','Review progress continuity from Journey.')">Open Progress</button>
          </div>
          <div class="journey-chart"><svg id="journey-growth-chart" viewBox="0 0 620 220" preserveAspectRatio="none"></svg></div>
        </div>
      </section>

      <section class="journey-card span-3">
        <div class="journey-card-inner">
          <div class="journey-card-header">
            <div><div class="journey-card-number">9. Opportunities To Teach JARVIS</div><h3>Help JARVIS learn you even better.</h3></div>
          </div>
          <div class="journey-opportunity-list" id="journey-opportunity-list"></div>
        </div>
      </section>

      <section class="journey-card span-3">
        <div class="journey-card-inner">
          <div class="journey-card-header">
            <div><div class="journey-card-number">10. Next Maturity Milestone</div><h3>What JARVIS is working to improve next.</h3></div>
          </div>
          <div class="journey-mini-card">
            <strong id="journey-next-milestone-title">Loading milestone…</strong>
            <span id="journey-next-milestone-copy">Reading remaining level-3 work.</span>
            <div class="journey-meter"><div id="journey-next-milestone-meter" style="width:0%;"></div></div>
            <span id="journey-next-milestone-progress" style="margin-top:10px;display:block;">Loading progress…</span>
          </div>
        </div>
      </section>

      <section class="journey-card span-3">
        <div class="journey-card-inner">
          <div class="journey-card-header">
            <div><div class="journey-card-number">11. Your Impact On JARVIS</div><h3>How your guidance shapes JARVIS.</h3></div>
          </div>
          <div class="journey-impact-grid" id="journey-user-impact-grid"></div>
        </div>
      </section>
    </div>

    <div class="journey-footer-strip" id="journey-footer-strip"></div>
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
        <div style="font-size:11px;color:var(--text-3);margin-top:3px;">Enter real balances manually or connect supported accounts with Plaid.</div>
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
      <div class="finance-form" style="margin-bottom:12px;">
        <div class="finance-form-title">Connected Accounts</div>
        <div id="finance-plaid-status" class="finance-empty">Checking Plaid status…</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <button class="finance-add-btn" type="button" onclick="connectFinancePlaid()">Connect Bank</button>
          <button class="finance-add-btn" type="button" onclick="syncFinancePlaid()">Refresh Linked Data</button>
        </div>
      </div>
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
const GLASS_EVENT_STREAM_PATH = '/ws/events';
const HOME_PEOPLE_SEED = {_home_people_seed_js};
const HOME_LOCATION_LABEL = {_home_location_label_js};
const HOME_QUIET_START = {_home_quiet_start_js};
const HOME_QUIET_END = {_home_quiet_end_js};
</script>
<script src="/glass-assets/glass-{_js_hash}.js"></script>
</body>
</html>"""
    if inline_assets:
        from .glass_assets import GLASS_CSS, GLASS_JS

        html = html.replace(
            f'<link rel="stylesheet" href="/glass-assets/glass-{_css_hash}.css">',
            f"<style>{GLASS_CSS}</style>",
            1,
        )
        html = html.replace(
            f'<script src="/glass-assets/glass-{_js_hash}.js"></script>',
            f"<script>{GLASS_JS}</script>",
            1,
        )
    return _strip_ordered_html_titles(html)
