from __future__ import annotations

import json
import mimetypes
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .runtime import JarvisRuntime
from .settings import LocationSettingsStore, VoiceSettingsStore
from .voice_audio import generate_tts_audio
from .voice_ui import render_voice_shell


CATALYST_MOCKUP_ROOT = Path("/Users/chris/Desktop/CATALYST")
CATALYST_MOCKUP_PAGES = {
    "home": CATALYST_MOCKUP_ROOT / "mockup-command-center.html",
    "calendar": CATALYST_MOCKUP_ROOT / "mockup-calendar.html",
    "projects": CATALYST_MOCKUP_ROOT / "mockup-projects.html",
    "tasks": CATALYST_MOCKUP_ROOT / "mockup-tasks.html",
    "reports": CATALYST_MOCKUP_ROOT / "mockup-reports.html",
}
CATALYST_WORKSPACE_TABS = [
    ("home", "Home"),
    ("calendar", "Calendar"),
    ("meetings", "Meetings"),
    ("projects", "Projects"),
    ("tasks", "Tasks"),
    ("email", "Email"),
    ("contacts", "Contacts"),
    ("reports", "Reports"),
    ("settings", "Settings"),
]
AGENT_HIERARCHY_TIERS = [
    ("tier-0", "Tier 0", "Master Orchestrator", ["ambient-router"]),
    (
        "tier-1",
        "Tier 1",
        "Strategic Layer",
        ["executive-watch", "catalyst-personal", "chronicle-curator", "home-ops", "watchtower"],
    ),
    (
        "tier-2",
        "Tier 2",
        "Execution Layer",
        ["family-logistics", "workshop-watch", "memory-curator"],
    ),
]


def _catalyst_theme_overrides() -> str:
    route_map = ",".join(f'"{label.lower()}":"/catalyst/view/{page}"' for page, label in CATALYST_WORKSPACE_TABS)
    return f"""
<style>
  :root {{
    color-scheme: dark;
  }}
  body {{
    background:
      radial-gradient(circle at top, rgba(42, 170, 255, 0.12), transparent 38%),
      linear-gradient(180deg, #050b16 0%, #07111f 42%, #081624 100%) !important;
    color: #e7f4ff !important;
  }}
  .bg-gray-50 {{ background: transparent !important; }}
  .bg-white {{
    background: rgba(8, 20, 36, 0.86) !important;
    box-shadow: 0 18px 42px rgba(0, 0, 0, 0.28) !important;
  }}
  .border-gray-200 {{ border-color: rgba(111, 229, 255, 0.14) !important; }}
  .border-gray-100 {{ border-color: rgba(111, 229, 255, 0.1) !important; }}
  .bg-gray-100 {{ background: rgba(10, 26, 42, 0.9) !important; }}
  .bg-gray-200 {{ background: rgba(34, 61, 86, 0.9) !important; }}
  .text-gray-900, .text-slate-900 {{ color: #ecf8ff !important; }}
  .text-gray-800, .text-slate-800 {{ color: #d8eeff !important; }}
  .text-gray-700, .text-slate-700 {{ color: #bbdbf6 !important; }}
  .text-gray-600, .text-slate-600 {{ color: #99c1df !important; }}
  .text-gray-500, .text-gray-400, .text-slate-500, .text-slate-400 {{ color: #81accf !important; }}
  .bg-teal-600, .bg-teal-700, .bg-teal-500 {{
    background: linear-gradient(135deg, rgba(90, 202, 255, 0.92), rgba(56, 132, 255, 0.9)) !important;
    color: #03111f !important;
  }}
  .bg-teal-400 {{ background: rgba(90, 202, 255, 0.82) !important; }}
  .bg-teal-200 {{ background: rgba(176, 235, 255, 0.78) !important; }}
  .text-teal-600, .text-teal-700, .text-teal-500 {{ color: #72d7ff !important; }}
  .text-amber-800, .text-amber-700 {{ color: #ffd48a !important; }}
  .rounded-xl, .rounded-2xl, .rounded-lg {{
    border-radius: 8px !important;
  }}
  .shadow-sm, .shadow {{
    box-shadow: 0 16px 36px rgba(0, 0, 0, 0.22) !important;
  }}
  input, select, textarea {{
    background: rgba(8, 18, 32, 0.92) !important;
    border-color: rgba(111, 229, 255, 0.14) !important;
    color: #e7f4ff !important;
  }}
  a {{
    color: inherit;
  }}
  a:hover {{
    opacity: 0.96;
  }}
</style>
<script>
  document.addEventListener("DOMContentLoaded", () => {{
    const routeMap = {{{route_map}}};
    document.querySelectorAll('a[href="#"]').forEach((anchor) => {{
      const label = anchor.textContent.trim().toLowerCase();
      if (routeMap[label]) {{
        anchor.setAttribute("href", routeMap[label]);
      }}
    }});
  }});
</script>
"""


def _inject_catalyst_theme(html: str) -> str:
    if "</head>" in html:
        return html.replace("</head>", _catalyst_theme_overrides() + "\n</head>", 1)
    return _catalyst_theme_overrides() + html


def _render_catalyst_workspace_chrome(title: str, subtitle: str, body_html: str, active_page: str) -> str:
    nav = "".join(
        f'<a class="nav-pill{" active" if page == active_page else ""}" href="/catalyst/view/{page}">{label}</a>'
        for page, label in CATALYST_WORKSPACE_TABS
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Catalyst Workspace</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #07111f;
      --panel: rgba(10, 22, 36, 0.88);
      --panel-strong: rgba(9, 19, 31, 0.96);
      --line: rgba(111, 229, 255, 0.16);
      --ink: #e7f4ff;
      --muted: #86b2d3;
      --cyan: #74d8ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top, rgba(42, 170, 255, 0.12), transparent 40%),
        linear-gradient(180deg, #050b16 0%, var(--bg) 38%, #081624 100%);
      color: var(--ink);
    }}
    .shell {{
      min-height: 100vh;
      padding: 20px;
      display: grid;
      gap: 18px;
    }}
    .hero, .panel {{
      border: 1px solid var(--line);
      background: var(--panel);
      box-shadow: 0 18px 42px rgba(0,0,0,0.28);
    }}
    .hero {{
      padding: 18px 20px;
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 18px;
    }}
    .eyebrow {{
      color: var(--cyan);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.18em;
    }}
    h1 {{
      margin: 8px 0 4px;
      font-size: 28px;
      letter-spacing: 0.04em;
    }}
    .subtitle {{
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
      max-width: 72ch;
    }}
    .nav {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
      justify-content: flex-end;
    }}
    .nav-pill {{
      padding: 10px 14px;
      border: 1px solid var(--line);
      color: var(--muted);
      text-decoration: none;
      font-size: 13px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      background: rgba(7, 16, 27, 0.72);
    }}
    .nav-pill.active {{
      background: linear-gradient(135deg, rgba(111, 229, 255, 0.18), rgba(76, 160, 255, 0.18));
      color: var(--cyan);
      box-shadow: 0 0 20px rgba(111, 229, 255, 0.12);
    }}
    .panel {{
      padding: 18px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .card {{
      border: 1px solid var(--line);
      background: var(--panel-strong);
      padding: 16px;
    }}
    .card h2 {{
      margin: 0 0 10px;
      font-size: 13px;
      color: var(--cyan);
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }}
    .card p, .card li, .card div {{
      color: var(--ink);
      font-size: 14px;
      line-height: 1.55;
    }}
    .card ul {{
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 8px;
    }}
    .muted {{ color: var(--muted); }}
    .table {{
      display: grid;
      gap: 10px;
    }}
    .row {{
      border-top: 1px solid rgba(111, 229, 255, 0.12);
      padding-top: 10px;
    }}
    .row:first-child {{
      border-top: none;
      padding-top: 0;
    }}
    @media (max-width: 960px) {{
      .hero {{
        align-items: start;
        flex-direction: column;
      }}
      .nav {{
        justify-content: flex-start;
      }}
      .grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div>
        <div class="eyebrow">Catalyst Within JARVIS</div>
        <h1>{escape(title)}</h1>
        <div class="subtitle">{escape(subtitle)}</div>
      </div>
      <nav class="nav">{nav}</nav>
    </section>
    <section class="panel">
      {body_html}
    </section>
  </div>
</body>
</html>"""


def render_catalyst_workspace_page(runtime: JarvisRuntime, page: str) -> str:
    page = (page or "home").strip().lower()
    mockup = CATALYST_MOCKUP_PAGES.get(page)
    if mockup and mockup.exists():
        return _inject_catalyst_theme(mockup.read_text(encoding="utf-8"))

    overview = runtime.catalyst_overview()
    google = runtime.google_workspace_summary()
    accounts = runtime.account_registry_snapshot().get("accounts", [])
    google_accounts = google.get("accounts", [])
    unread_emails = [
        (entry.get("account", {}), email)
        for entry in google_accounts
        for email in entry.get("emails", [])
    ]
    upcoming_events = [
        (entry.get("account", {}), item)
        for entry in google_accounts
        for item in entry.get("calendar_events", [])
    ]
    latest_runs = overview.get("latest_runs", {})

    if page == "email":
        body = f"""
        <div class="grid">
          <div class="card">
            <h2>Connected Accounts</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(account.get("label") or account.get("owner_display_name") or "Account")}</strong><div class="muted">{escape(account.get("provider", "unknown"))} · {escape(account.get("service_scope", "mail"))}</div></div>' for account in accounts) or '<div class="muted">No personal accounts have been saved yet.</div>'}</div>
          </div>
          <div class="card">
            <h2>Email Triage</h2>
            <p>{escape(latest_runs.get("email_triage", {}).get("subject") or "No triage run has been captured yet. Once mail is connected, JARVIS can open this lane directly from voice or the Catalyst workspace.")}</p>
          </div>
          <div class="card" style="grid-column: 1 / -1;">
            <h2>Unread Mail</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(email.get("subject") or "(No subject)")}</strong><div class="muted">{escape(account.get("owner_display_name") or account.get("label") or "Account")} · {escape(email.get("from") or "Unknown sender")}</div></div>' for account, email in unread_emails) or '<div class="muted">No unread mail is loaded yet.</div>'}</div>
          </div>
        </div>"""
        return _render_catalyst_workspace_chrome("Email Workspace", "Personal inbox triage, drafts, and signal capture under the JARVIS shell.", body, page)

    if page == "meetings":
        body = f"""
        <div class="grid">
          <div class="card">
            <h2>Upcoming Meetings</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(event.get("summary") or "(Untitled event)")}</strong><div class="muted">{escape(account.get("owner_display_name") or account.get("label") or "Account")} · {escape(event.get("start") or "No start time")}</div></div>' for account, event in upcoming_events[:10]) or '<div class="muted">No upcoming meetings are loaded yet.</div>'}</div>
          </div>
          <div class="card">
            <h2>Meeting Prep</h2>
            <p>{escape(latest_runs.get("meeting_prep", {}).get("meeting_title") or "No meeting prep packet has been generated yet.")}</p>
          </div>
          <div class="card" style="grid-column: 1 / -1;">
            <h2>Extraction Brief</h2>
            <p>{escape(latest_runs.get("meeting_extraction", {}).get("problem_statement") or "No meeting extraction run is stored yet. When you ask JARVIS to prep or debrief a meeting, this lane will light up.")}</p>
          </div>
        </div>"""
        return _render_catalyst_workspace_chrome("Meetings Workspace", "Pre-meeting preparation, transcript extraction, and next-action capture.", body, page)

    if page == "contacts":
        body = f"""
        <div class="grid">
          <div class="card">
            <h2>Household Operators</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(user.display_name)}</strong><div class="muted">{escape(user.permissions)} permissions</div></div>' for user in runtime.household.users.values())}</div>
          </div>
          <div class="card">
            <h2>Connected Identities</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(account.get("owner_display_name") or account.get("label") or "Account")}</strong><div class="muted">{escape(account.get("provider", "unknown"))} · {escape(account.get("status", "planned"))}</div></div>' for account in accounts) or '<div class="muted">No linked accounts yet.</div>'}</div>
          </div>
        </div>"""
        return _render_catalyst_workspace_chrome("Contacts Workspace", "Who is connected, which identities are live, and how Catalyst is scoped by person.", body, page)

    if page == "settings":
        client_secret = google.get("client_secret", {})
        body = f"""
        <div class="grid">
          <div class="card">
            <h2>Provider Readiness</h2>
            <ul>
              <li>Google client: {escape(client_secret.get("detail") or "Not configured yet.")}</li>
              <li>Personal accounts: {escape(str(len(accounts)))}</li>
              <li>Voice provider: managed in the main JARVIS settings modal.</li>
            </ul>
          </div>
          <div class="card">
            <h2>Connectors</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(item.get("label", "Connector"))}</strong><div class="muted">{escape(item.get("status", "planned"))} · {escape(item.get("notes", ""))}</div></div>' for item in overview.get("connectors", []))}</div>
          </div>
        </div>"""
        return _render_catalyst_workspace_chrome("Workspace Settings", "Connection posture and Catalyst-specific configuration under the JARVIS theme.", body, page)

    return _render_catalyst_workspace_chrome(
        "Catalyst Workspace",
        "The full Catalyst surfaces now live inside JARVIS. Choose a lane above or ask JARVIS to open the one you need.",
        """
        <div class="grid">
          <div class="card">
            <h2>Available Lanes</h2>
            <ul>
              <li>Home command center</li>
              <li>Calendar and meetings</li>
              <li>Projects and tasks</li>
              <li>Email triage</li>
              <li>Reports, contacts, and settings</li>
            </ul>
          </div>
          <div class="card">
            <h2>Current Posture</h2>
            <p>Open any lane from the workspace navigation. JARVIS can also bring the relevant window forward when your request clearly points at calendar, email, meetings, projects, or reporting.</p>
          </div>
        </div>
        """,
        "home",
    )


def render_agent_hierarchy_page(runtime: JarvisRuntime) -> str:
    registry = runtime.agent_registry_snapshot().get("agents", [])
    status_snapshot = runtime.background_agent_status()
    statuses = {item.get("agent_id"): item for item in status_snapshot.get("statuses", [])}
    curator = runtime.memory_curator_snapshot()
    agents_by_id = {item.get("agent_id"): item for item in registry}

    def badge_for(state: str) -> str:
        state = (state or "idle").lower()
        label = {
            "awake": "Awake",
            "idle": "Idle",
            "blocked": "Blocked",
        }.get(state, state.title())
        return f'<span class="agent-badge {escape(state)}">{escape(label)}</span>'

    def card_for(agent_id: str) -> str:
        agent = agents_by_id.get(agent_id, {})
        status = statuses.get(agent_id, {})
        owns = "".join(f"<li>{escape(item)}</li>" for item in agent.get("owns", [])[:3])
        dependencies = ", ".join(agent.get("dependencies", [])) or "none"
        memory_scope = ", ".join(agent.get("memory_scope", [])) or "session"
        state = str(status.get("state", "idle"))
        reason = str(status.get("reason", agent.get("purpose", "")))
        cadence = str(agent.get("cadence_minutes", "--"))
        label = str(agent.get("label", agent_id.replace("-", " ").title()))
        return f"""
        <article class="agent-card">
          <div class="agent-card-head">
            <div>
              <div class="agent-name">{escape(label)}</div>
              <div class="agent-role">{escape(agent.get("purpose", ""))}</div>
            </div>
            {badge_for(state)}
          </div>
          <ul class="agent-list">{owns or "<li>No owned lanes defined yet.</li>"}</ul>
          <div class="agent-metrics">
            <span>Cadence {escape(cadence)} min</span>
            <span>Deps {escape(dependencies)}</span>
            <span>Memory {escape(memory_scope)}</span>
          </div>
          <div class="agent-reason">{escape(reason)}</div>
        </article>
        """

    tier_sections = []
    for tier_id, tier_label, tier_name, members in AGENT_HIERARCHY_TIERS:
        cards = "".join(card_for(agent_id) for agent_id in members if agent_id in agents_by_id)
        tier_sections.append(
            f"""
            <section class="tier-section">
              <div class="tier-rule"></div>
              <div class="tier-header">
                <span>{escape(tier_label)}</span>
                <strong>{escape(tier_name)}</strong>
              </div>
              <div class="agent-grid {escape(tier_id)}">{cards}</div>
            </section>
            """
        )

    candidate_cards = [
        (
            "Calendar Steward",
            "Own personal calendar conflict detection, free-window creation, and travel-aware timing once provider links are stable.",
        ),
        (
            "Inbox Adjutant",
            "Handle personal inbox triage, reply staging, and follow-up surfaces without bringing work assumptions into the house.",
        ),
        (
            "Home Presence Mesh",
            "Fuse phones, Kasa cameras, and Home Assistant presence into trustworthy arrival and watch transitions.",
        ),
        (
            "Voice Director",
            "Manage premium versus local voice lanes, interruptions, and room-aware output posture across the house.",
        ),
    ]
    candidates_markup = "".join(
        f"""
        <article class="candidate-card">
          <div class="candidate-name">{escape(name)}</div>
          <p>{escape(copy)}</p>
        </article>
        """
        for name, copy in candidate_cards
    )

    curation_rules = "".join(
        f"<li><strong>{escape(rule.get('label', 'Rule'))}</strong> · {escape(rule.get('capture_when', ''))}</li>"
        for rule in curator.get("rules", [])[:4]
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Agent Hierarchy</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #050b14;
      --bg-2: #09121f;
      --panel: rgba(7, 18, 30, 0.84);
      --panel-strong: rgba(8, 20, 34, 0.96);
      --line: rgba(111, 229, 255, 0.16);
      --line-strong: rgba(111, 229, 255, 0.28);
      --ink: #edf7ff;
      --muted: #90b7d4;
      --cyan: #71e2ff;
      --cyan-soft: rgba(113, 226, 255, 0.14);
      --ok: #7df0b3;
      --warn: #ffd27b;
      --alert: #ff8b8b;
      --shadow: 0 24px 64px rgba(0, 0, 0, 0.34);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top, rgba(65, 171, 255, 0.16), transparent 24%),
        linear-gradient(180deg, var(--bg) 0%, var(--bg-2) 52%, #08111d 100%);
    }}
    .shell {{
      max-width: 1600px;
      margin: 0 auto;
      padding: 24px 28px 40px;
      display: grid;
      gap: 18px;
    }}
    .hero {{
      display: grid;
      gap: 12px;
      justify-items: center;
      text-align: center;
      padding: 18px 20px 8px;
    }}
    .hero-mark {{
      color: var(--cyan);
      font-size: 28px;
      letter-spacing: 0.28em;
      text-transform: uppercase;
    }}
    .hero-sub {{
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.24em;
      text-transform: uppercase;
    }}
    .hero-note {{
      color: var(--muted);
      max-width: 76ch;
      font-size: 14px;
      line-height: 1.5;
    }}
    .top-stats {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }}
    .stat-card, .tier-section, .side-card, .candidate-card {{
      border: 1px solid var(--line);
      background: var(--panel);
      box-shadow: var(--shadow);
    }}
    .stat-card {{
      padding: 14px 16px;
    }}
    .stat-label {{
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}
    .stat-value {{
      margin-top: 8px;
      color: var(--cyan);
      font-size: 24px;
      letter-spacing: 0.04em;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 1.75fr 0.9fr;
      gap: 18px;
      align-items: start;
    }}
    .hierarchy {{
      display: grid;
      gap: 18px;
    }}
    .tier-section {{
      padding: 16px 18px 18px;
      position: relative;
      overflow: hidden;
    }}
    .tier-rule {{
      position: absolute;
      left: 0;
      right: 0;
      top: 48px;
      height: 1px;
      background: linear-gradient(90deg, transparent 0%, var(--line-strong) 18%, var(--line-strong) 82%, transparent 100%);
    }}
    .tier-header {{
      display: flex;
      align-items: baseline;
      gap: 14px;
      margin-bottom: 18px;
      position: relative;
      z-index: 1;
    }}
    .tier-header span {{
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 0.2em;
      text-transform: uppercase;
    }}
    .tier-header strong {{
      color: var(--cyan);
      font-size: 13px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}
    .agent-grid {{
      display: grid;
      gap: 16px;
      position: relative;
      z-index: 1;
    }}
    .agent-grid.tier-0 {{
      grid-template-columns: minmax(320px, 460px);
      justify-content: center;
    }}
    .agent-grid.tier-1 {{
      grid-template-columns: repeat(5, minmax(0, 1fr));
    }}
    .agent-grid.tier-2 {{
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }}
    .agent-card {{
      min-height: 232px;
      padding: 16px;
      border: 1px solid rgba(111, 229, 255, 0.24);
      background:
        linear-gradient(180deg, rgba(113, 226, 255, 0.06), transparent 22%),
        var(--panel-strong);
      position: relative;
    }}
    .agent-card::after {{
      content: "";
      position: absolute;
      inset: auto 18px -1px 18px;
      height: 2px;
      background: linear-gradient(90deg, rgba(113, 226, 255, 0.1), rgba(113, 226, 255, 0.78), rgba(113, 226, 255, 0.1));
    }}
    .agent-card-head {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: start;
      margin-bottom: 12px;
    }}
    .agent-name {{
      color: var(--cyan);
      font-size: 22px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .agent-role {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }}
    .agent-badge {{
      display: inline-flex;
      align-items: center;
      padding: 4px 10px;
      border: 1px solid var(--line);
      font-size: 11px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      white-space: nowrap;
    }}
    .agent-badge.awake {{ color: var(--ok); border-color: rgba(125, 240, 179, 0.32); }}
    .agent-badge.idle {{ color: var(--muted); }}
    .agent-badge.blocked {{ color: var(--alert); border-color: rgba(255, 139, 139, 0.28); }}
    .agent-list {{
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 8px;
      min-height: 84px;
      color: var(--ink);
      font-size: 13px;
      line-height: 1.45;
    }}
    .agent-metrics {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 14px;
    }}
    .agent-metrics span {{
      padding: 5px 8px;
      border: 1px solid rgba(111, 229, 255, 0.14);
      background: rgba(7, 16, 27, 0.8);
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .agent-reason {{
      margin-top: 12px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }}
    .sidebar {{
      display: grid;
      gap: 18px;
    }}
    .side-card {{
      padding: 18px;
    }}
    .side-card h2 {{
      margin: 0 0 12px;
      color: var(--cyan);
      font-size: 13px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }}
    .side-card p,
    .side-card li,
    .side-card div {{
      color: var(--ink);
      font-size: 14px;
      line-height: 1.55;
    }}
    .side-card ul {{
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 10px;
    }}
    .candidate-grid {{
      display: grid;
      gap: 12px;
    }}
    .candidate-card {{
      padding: 14px 16px;
      background: rgba(8, 20, 34, 0.9);
    }}
    .candidate-name {{
      color: var(--cyan);
      font-size: 14px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      margin-bottom: 8px;
    }}
    .back-link {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      border: 1px solid var(--line);
      background: rgba(7, 16, 27, 0.78);
      color: var(--ink);
      text-decoration: none;
      font-size: 13px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    @media (max-width: 1320px) {{
      .agent-grid.tier-1 {{
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }}
    }}
    @media (max-width: 1100px) {{
      .layout {{
        grid-template-columns: 1fr;
      }}
      .top-stats {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
    }}
    @media (max-width: 860px) {{
      .agent-grid.tier-1,
      .agent-grid.tier-2,
      .agent-grid.tier-0 {{
        grid-template-columns: 1fr;
      }}
      .top-stats {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="hero-mark">JARVIS</div>
      <div class="hero-sub">Agent Hierarchy · Expandable Orchestration Map</div>
      <div class="hero-note">A dedicated view for the household agent mesh. Use this page to decide what stays central, what deserves a strategic lane, and which new specialists should graduate into the stack.</div>
    </section>
    <section class="top-stats">
      <div class="stat-card"><div class="stat-label">Awake</div><div class="stat-value">{escape(str(status_snapshot.get("awake_count", 0)))}</div></div>
      <div class="stat-card"><div class="stat-label">Idle</div><div class="stat-value">{escape(str(status_snapshot.get("idle_count", 0)))}</div></div>
      <div class="stat-card"><div class="stat-label">Blocked</div><div class="stat-value">{escape(str(status_snapshot.get("blocked_count", 0)))}</div></div>
      <div class="stat-card"><div class="stat-label">Active Mode</div><div class="stat-value">{escape(str(status_snapshot.get("active_mode", "ambient-associate")).replace("-", " "))}</div></div>
    </section>
    <section class="layout">
      <div class="hierarchy">
        {''.join(tier_sections)}
      </div>
      <aside class="sidebar">
        <section class="side-card">
          <h2>Orchestrator Notes</h2>
          <p>The top card should remain the estate intelligence itself: routing, permissioning, and conversational coherence. Everything else should feel like a specialist beneath the shell, not a second personality fighting it.</p>
        </section>
        <section class="side-card">
          <h2>Memory Curator Rules</h2>
          <ul>{curation_rules}</ul>
        </section>
        <section class="side-card">
          <h2>Candidate Agent Lanes</h2>
          <div class="candidate-grid">{candidates_markup}</div>
        </section>
        <section class="side-card">
          <h2>Next Step</h2>
          <p>As you add agents, keep the ones with judgment at the strategic layer and the ones with execution or monitoring further down. That keeps the hierarchy legible instead of turning into a glowing bowl of spaghetti.</p>
          <a class="back-link" href="/">Return to JARVIS</a>
        </section>
      </aside>
    </section>
  </div>
</body>
</html>"""


def render_dashboard(runtime: JarvisRuntime) -> str:
    users = "".join(
        f'<option value="{user.display_name}">{user.display_name}</option>'
        for user in runtime.household.users.values()
    )
    child_users = "".join(
        f'<option value="{user.display_name}">{user.display_name}</option>'
        for user in runtime.household.users.values()
        if user.permissions == "child"
    )
    adult_users = "".join(
        f'<option value="{user.display_name}">{user.display_name}</option>'
        for user in runtime.household.users.values()
        if user.permissions == "adult"
    )
    rooms = "".join(
        f'<option value="{room.room_id}">{room.room_id}</option>'
        for room in runtime.household.rooms.values()
    )
    hero_modes = "".join(
        f'<span class="tag">{mode.replace("-", " ")}</span>'
        for mode in runtime.household.modes[:5]
    )
    mode_options = "".join(
        f'<option value="{mode}">{mode.replace("-", " ")}</option>'
        for mode in runtime.household.modes
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Household Command</title>
  <style>
    :root {{
      --bg: #eff1ea;
      --panel: rgba(255, 255, 252, 0.88);
      --panel-strong: rgba(255, 255, 255, 0.95);
      --ink: #14211c;
      --muted: #5d6a63;
      --line: rgba(20, 33, 28, 0.1);
      --accent: #1b4f44;
      --accent-soft: #dceae3;
      --accent-warm: #f2e9d7;
      --ok: #2d6b42;
      --warn: #8b611d;
      --shadow: 0 20px 45px rgba(18, 28, 23, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Iowan Old Style", "Palatino Linotype", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(27, 79, 68, 0.16), transparent 28%),
        radial-gradient(circle at top right, rgba(242, 233, 215, 0.9), transparent 26%),
        linear-gradient(180deg, #f6f7f2 0%, var(--bg) 100%);
    }}
    .shell {{
      max-width: 1360px;
      margin: 0 auto;
      padding: 22px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.6fr 1fr;
      gap: 18px;
      margin-bottom: 18px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(12px);
    }}
    .hero-main {{
      padding: 28px;
      min-height: 280px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      background:
        linear-gradient(135deg, rgba(27, 79, 68, 0.05), rgba(255, 255, 255, 0)),
        var(--panel-strong);
    }}
    .eyebrow {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      color: var(--muted);
    }}
    h1 {{
      margin: 12px 0;
      font-size: 58px;
      line-height: 0.92;
      font-weight: 700;
    }}
    .lede {{
      max-width: 60ch;
      color: var(--muted);
      font-size: 17px;
      line-height: 1.55;
    }}
    .tag-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 16px;
    }}
    .tag {{
      display: inline-flex;
      align-items: center;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(27, 79, 68, 0.08);
      border: 1px solid rgba(27, 79, 68, 0.1);
      color: var(--accent);
      font-size: 13px;
      white-space: nowrap;
    }}
    .hero-side {{
      padding: 22px;
      display: grid;
      gap: 14px;
      align-content: start;
    }}
    .hero-side .stat-label {{
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .hero-side .stat-value {{
      font-size: 20px;
      line-height: 1.2;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 1.6fr 1fr;
      gap: 18px;
    }}
    .column {{
      display: grid;
      gap: 18px;
      align-content: start;
    }}
    .card {{
      padding: 20px;
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 21px;
    }}
    h3 {{
      margin: 0 0 8px;
      font-size: 16px;
    }}
    p, li, label, input, select, textarea, button {{
      font-size: 15px;
      line-height: 1.45;
    }}
    .muted {{ color: var(--muted); }}
    .snapshot-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 14px;
    }}
    .snapshot {{
      border-radius: 8px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.68);
      padding: 16px;
      min-height: 175px;
    }}
    .snapshot .status {{
      display: inline-block;
      margin-bottom: 10px;
      padding: 5px 9px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .timeline {{
      display: grid;
      gap: 12px;
    }}
    .timeline-item {{
      display: grid;
      grid-template-columns: 84px 1fr;
      gap: 12px;
      padding: 12px 0;
      border-top: 1px solid var(--line);
    }}
    .timeline-item:first-child {{
      border-top: none;
      padding-top: 0;
    }}
    .segment {{
      display: inline-flex;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: rgba(255, 255, 255, 0.55);
    }}
    .segment button {{
      border: 0;
      border-radius: 0;
      background: transparent;
      padding: 10px 14px;
      color: var(--ink);
    }}
    .segment button.active {{
      background: var(--accent-soft);
      color: var(--accent);
    }}
    .time {{
      font-size: 13px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      padding-top: 2px;
    }}
    .focus-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
    }}
    .focus-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.62);
      padding: 14px;
    }}
    .focus-card ul, .snapshot ul, .watch-list {{
      margin: 10px 0 0;
      padding-left: 18px;
      color: var(--muted);
      display: grid;
      gap: 6px;
    }}
    .status-list, .approval-list, .activity-list {{
      display: grid;
      gap: 12px;
    }}
    .draft-list {{
      display: grid;
      gap: 12px;
    }}
    body.family-display .panel.executive-only,
    body.family-display .panel.admin-only {{
      display: none;
    }}
    .status-item, .approval-item, .activity-item, .output-box {{
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.7);
    }}
    .ok {{ color: var(--ok); }}
    .blocked {{ color: var(--warn); }}
    form {{
      display: grid;
      gap: 12px;
    }}
    input, select, textarea {{
      width: 100%;
      padding: 10px 12px;
      border-radius: 8px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.94);
      color: var(--ink);
    }}
    textarea {{
      min-height: 108px;
      resize: vertical;
    }}
    button {{
      border: none;
      border-radius: 8px;
      padding: 11px 14px;
      background: var(--accent);
      color: white;
      cursor: pointer;
    }}
    button.ghost {{
      background: transparent;
      color: var(--accent);
      border: 1px solid rgba(27, 79, 68, 0.18);
    }}
    .split {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }}
    .preset-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .preset {{
      padding: 8px 10px;
      border-radius: 999px;
      border: 1px solid rgba(27, 79, 68, 0.18);
      background: rgba(255,255,255,0.75);
      color: var(--accent);
      cursor: pointer;
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      font-family: "SFMono-Regular", Menlo, Consolas, monospace;
      font-size: 13px;
      line-height: 1.6;
    }}
    .subgrid {{
      display: grid;
      gap: 18px;
    }}
    @media (max-width: 1080px) {{
      .hero, .layout, .snapshot-grid, .focus-grid, .split {{
        grid-template-columns: 1fr;
      }}
      h1 {{
        font-size: 42px;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="panel hero-main">
        <div>
          <div class="eyebrow">Whole-Home Personal AI Associate</div>
          <h1>JARVIS</h1>
          <p class="lede">A private household intelligence layer with memory, permissions, family-specific context, and the manners to know when to prepare, when to ask, and when to stay quiet.</p>
          <div class="tag-row">{hero_modes}</div>
        </div>
        <div class="tag-row">
          <span class="tag">Reasoning: {runtime.config.openai_text_model}</span>
          <span class="tag">Routing: {runtime.config.openai_router_model}</span>
          <span class="tag">Voice: {runtime.config.openai_realtime_model}</span>
        </div>
      </div>
      <div class="panel hero-side">
        <div>
          <div class="stat-label">Household</div>
          <div class="stat-value">{runtime.household.household_name}</div>
        </div>
        <div>
          <div class="stat-label">Location</div>
          <div>{runtime.household.location_label}</div>
        </div>
        <div>
          <div class="stat-label">Quiet Hours</div>
          <div>{runtime.household.quiet_start} to {runtime.household.quiet_end}</div>
        </div>
        <div>
          <div class="stat-label">Operator Surface</div>
          <div>{runtime.config.openclaw_gateway_url}</div>
        </div>
        <div class="output-box">
          <strong>House Note</strong>
          <div id="house-note" class="muted">Loading household context…</div>
        </div>
      </div>
    </section>

    <section class="layout">
      <div class="column">
        <div class="panel card">
          <h2>Today</h2>
          <div class="muted" id="day-label">Loading day snapshot…</div>
          <div class="muted" id="weather-line" style="margin-top:4px;"></div>
          <div class="snapshot-grid" id="snapshot-grid" style="margin-top:16px;"></div>
        </div>

        <div class="panel card">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">
            <h2>Body Home Mission</h2>
            <div class="segment" id="display-mode">
              <button type="button" data-display="full" class="active">Full</button>
              <button type="button" data-display="family">Family</button>
            </div>
          </div>
          <div class="snapshot-grid" id="bhm-grid" style="margin-top:16px;"></div>
        </div>

        <div class="panel card">
          <h2>Command Center</h2>
          <div class="preset-row" id="preset-row">
            <button class="preset" data-preset="Give me Chris's executive morning brief.">Executive brief</button>
            <button class="preset" data-preset="Draft a calm family summary for tonight.">Calm family summary</button>
            <button class="preset" data-preset="Prepare a workshop plan for the Garden of Hope bracket prototype.">Workshop plan</button>
            <button class="preset" data-preset="Give me a devotional pause tied to stewardship under pressure.">Devotional pause</button>
          </div>
          <form id="plan-form" style="margin-top:16px;">
            <div class="split">
              <div>
                <label for="actor">Actor</label>
                <select id="actor">{users}</select>
              </div>
              <div>
                <label for="room">Room</label>
                <select id="room">{rooms}</select>
              </div>
            </div>
            <div>
              <label for="request">Request</label>
              <textarea id="request" placeholder="What does the family need to know this morning?"></textarea>
            </div>
            <div class="split">
              <button type="submit">Plan Request</button>
              <button type="button" class="ghost" id="respond-button">Respond as JARVIS</button>
            </div>
          </form>
          <div class="split" style="margin-top:14px;">
            <div class="output-box">
              <strong>Planner Output</strong>
              <pre id="plan-output">Awaiting request.</pre>
            </div>
            <div class="output-box">
              <strong>Response Output</strong>
              <pre id="respond-output">Awaiting response.</pre>
            </div>
          </div>
        </div>

        <div class="panel card executive-only">
          <h2>Executive Assistant</h2>
          <form id="executive-form">
            <div class="split">
              <div>
                <label for="executive-actor">Actor</label>
                <select id="executive-actor">{users}</select>
              </div>
              <div>
                <label for="executive-task">Executive Task</label>
                <select id="executive-task">
                  <option value="decision-framework">Decision framework</option>
                  <option value="ironclad-editor">Iron-Clad editor</option>
                  <option value="venture-brief">Venture brief</option>
                </select>
              </div>
            </div>
            <div>
              <label for="executive-topic">Topic</label>
              <input id="executive-topic" placeholder="agentic AI workflows">
            </div>
            <div>
              <label for="executive-primary">Primary Context</label>
              <textarea id="executive-primary" placeholder="Meeting notes, draft excerpt, or market notes..."></textarea>
            </div>
            <div>
              <label for="executive-secondary">Supporting Notes</label>
              <textarea id="executive-secondary" placeholder="Optional supporting notes or source summary..."></textarea>
            </div>
            <button type="submit">Run Executive Task</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="executive-output">Awaiting executive task.</pre>
          </div>
        </div>

        <div class="panel card">
          <h2>Chronicle</h2>
          <form id="chronicle-devotional-form">
            <div class="split">
              <div>
                <label for="chronicle-actor">Actor</label>
                <select id="chronicle-actor">{users}</select>
              </div>
              <div>
                <label for="chronicle-mode">Mode</label>
                <select id="chronicle-mode">
                  <option value="scripture">Scripture</option>
                  <option value="prayer">Prayer</option>
                  <option value="silence">Silence</option>
                </select>
              </div>
            </div>
            <div>
              <label for="chronicle-theme">Theme</label>
              <input id="chronicle-theme" placeholder="stewardship under pressure">
            </div>
            <button type="submit">Generate Devotional Pause</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="chronicle-devotional-output">Awaiting devotional request.</pre>
          </div>
          <form id="family-devotional-form" style="margin-top:16px;">
            <div>
              <label for="family-devotional-theme">Family Devotional Theme</label>
              <input id="family-devotional-theme" placeholder="leadership without striving">
            </div>
            <div>
              <label for="family-devotional-context">Context</label>
              <textarea id="family-devotional-context" placeholder="Prepare something suitable for tonight after a long day and troop meeting."></textarea>
            </div>
            <button type="submit">Prepare Family Devotional</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="family-devotional-output">Awaiting family devotional request.</pre>
          </div>
          <form id="chronicle-capture-form" style="margin-top:16px;">
            <div>
              <label for="chronicle-note">Chronicle Reflection Note</label>
              <textarea id="chronicle-note" placeholder="What happened today, and where did grace meet us?"></textarea>
            </div>
            <button type="submit">Capture Chronicle Note</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="chronicle-capture-output">Awaiting Chronicle note.</pre>
          </div>
          <div id="chronicle-theme-summary" class="status-list" style="margin-top:12px;"></div>
          <div id="chronicle-timeline" class="draft-list" style="margin-top:12px;"></div>
        </div>

        <div class="panel card">
          <h2>Household Timeline</h2>
          <div id="timeline" class="timeline"></div>
        </div>
      </div>

      <div class="column">
        <div class="panel card">
          <h2>Household Mode</h2>
          <div class="output-box">
            <pre id="mode-output">Loading mode state…</pre>
          </div>
        </div>

        <div class="panel card">
          <h2>Mode Playbooks</h2>
          <form id="mode-brief-form">
            <div>
              <label for="mode-brief-target">Mode</label>
              <select id="mode-brief-target">{mode_options}</select>
            </div>
            <button type="submit">Load Mode Brief</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="mode-brief-output">Loading mode brief…</pre>
          </div>
        </div>

        <div class="panel card">
          <h2>House Nervous System</h2>
          <form id="scene-form">
            <div class="split">
              <div>
                <label for="scene-actor">Actor</label>
                <select id="scene-actor">{adult_users}</select>
              </div>
              <div>
                <label for="scene-room">Room</label>
                <select id="scene-room">{rooms}</select>
              </div>
            </div>
            <div>
              <label for="scene-name">Scene</label>
              <input id="scene-name" value="Dinner Mode">
            </div>
            <button type="submit">Apply Room Scene</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="scene-output">Awaiting room scene request.</pre>
          </div>
          <form id="climate-form" style="margin-top:16px;">
            <div class="split">
              <div>
                <label for="climate-zone">Zone</label>
                <input id="climate-zone" value="main floor">
              </div>
              <div>
                <label for="climate-mode">Mode</label>
                <input id="climate-mode" value="heat_cool">
              </div>
            </div>
            <div>
              <label for="climate-target">Target Temperature</label>
              <input id="climate-target" value="71">
            </div>
            <button type="submit">Stage Climate Change</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="climate-output">Awaiting climate request.</pre>
          </div>
          <form id="garage-form" style="margin-top:16px;">
            <div>
              <label for="garage-target">Garage Target</label>
              <input id="garage-target" value="Main Garage Door">
            </div>
            <button type="submit">Run Safe-Close Check</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="garage-output">Awaiting garage safety check.</pre>
          </div>
          <form id="energy-form" style="margin-top:16px;">
            <div>
              <label for="energy-appliance">Appliance</label>
              <input id="energy-appliance" value="dishwasher">
            </div>
            <button type="submit">Recommend Energy Window</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="energy-output">Awaiting energy-window request.</pre>
          </div>
          <div id="home-summary" class="status-list" style="margin-top:12px;"></div>
          <div id="leak-summary" class="status-list" style="margin-top:12px;"></div>
          <div id="cold-storage-summary" class="status-list" style="margin-top:12px;"></div>
          <div class="output-box" style="margin-top:12px;">
            <pre id="outage-output">Loading outage readiness…</pre>
          </div>
        </div>

        <div class="panel card">
          <h2>Perception Mesh</h2>
          <form id="mic-form">
            <div class="split">
              <div>
                <label for="mic-name">Microphone</label>
                <input id="mic-name" value="Kitchen Alexa Dot">
              </div>
              <div>
                <label for="mic-actor-hint">Actor Hint</label>
                <input id="mic-actor-hint" value="Rebekah">
              </div>
            </div>
            <div>
              <label for="mic-transcript">Transcript</label>
              <textarea id="mic-transcript" placeholder="Jarvis, what does the family need to know this morning?"></textarea>
            </div>
            <button type="submit">Record Mic Ingress</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="mic-output">Awaiting microphone ingress.</pre>
          </div>

          <form id="presence-form" style="margin-top:16px;">
            <div class="split">
              <div>
                <label for="presence-sensor">Presence Sensor</label>
                <input id="presence-sensor" value="Kitchen Presence">
              </div>
              <div>
                <label for="presence-room">Room</label>
                <input id="presence-room" value="kitchen">
              </div>
            </div>
            <button type="submit">Mark Room Occupied</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="presence-output">Awaiting presence update.</pre>
          </div>

          <form id="phone-form" style="margin-top:16px;">
            <div class="split">
              <div>
                <label for="phone-actor">Actor</label>
                <select id="phone-actor">{users}</select>
              </div>
              <div>
                <label for="phone-state">Phone State</label>
                <input id="phone-state" value="arriving">
              </div>
            </div>
            <button type="submit">Record Phone Presence</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="phone-output">Awaiting phone-presence update.</pre>
          </div>

          <form id="camera-form" style="margin-top:16px;">
            <div class="split">
              <div>
                <label for="camera-name">Camera</label>
                <input id="camera-name" value="Porch Camera">
              </div>
              <div>
                <label for="camera-event-type">Event Type</label>
                <input id="camera-event-type" value="package">
              </div>
            </div>
            <div>
              <label for="camera-detail">Camera Detail</label>
              <textarea id="camera-detail" placeholder="Package dropped near the exposed edge during light rain."></textarea>
            </div>
            <button type="submit">Record Camera Event</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="camera-output">Awaiting camera event.</pre>
          </div>

          <div id="perception-summary" class="status-list" style="margin-top:12px;"></div>
          <div class="output-box" style="margin-top:12px;">
            <pre id="privacy-output">Loading privacy state…</pre>
          </div>
        </div>

        <div class="panel card">
          <h2>Memory Core</h2>
          <form id="memory-form">
            <div class="split">
              <div>
                <label for="memory-actor">Actor</label>
                <select id="memory-actor">{adult_users}</select>
              </div>
              <div>
                <label for="memory-type">Memory Type</label>
                <select id="memory-type">
                  <option value="household">household</option>
                  <option value="personal">personal</option>
                  <option value="project">project</option>
                  <option value="safety">safety</option>
                </select>
              </div>
            </div>
            <div class="split">
              <div>
                <label for="memory-scope">Scope</label>
                <select id="memory-scope">
                  <option value="household">household</option>
                  <option value="personal">personal</option>
                  <option value="project">project</option>
                  <option value="safety">safety</option>
                </select>
              </div>
              <div>
                <label for="memory-owner">Owner</label>
                <input id="memory-owner" value="Chris">
              </div>
            </div>
            <div>
              <label for="memory-project">Project</label>
              <input id="memory-project" placeholder="Chronicle, Scouts 95, Garden of Hope">
            </div>
            <div>
              <label for="memory-summary">Summary</label>
              <input id="memory-summary" placeholder="Chris prefers the executive brief after coffee.">
            </div>
            <div>
              <label for="memory-detail">Detail</label>
              <textarea id="memory-detail" placeholder="Useful continuity and why it matters."></textarea>
            </div>
            <div>
              <label for="memory-tags">Tags</label>
              <input id="memory-tags" placeholder="preference, morning, executive">
            </div>
            <div class="split">
              <div>
                <label for="memory-sensitivity">Sensitivity</label>
                <select id="memory-sensitivity">
                  <option value="normal">normal</option>
                  <option value="sensitive">sensitive</option>
                </select>
              </div>
              <div style="display:flex;align-items:end;">
                <button type="submit">Store Memory</button>
              </div>
            </div>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="memory-output">Awaiting memory input.</pre>
          </div>
          <div id="memory-summary-panel" class="status-list" style="margin-top:12px;"></div>
          <div id="memory-proposals" class="draft-list" style="margin-top:12px;"></div>
        </div>

        <div class="panel card">
          <h2>Family Focus</h2>
          <div id="family-focus" class="focus-grid"></div>
        </div>

        <div class="panel card">
          <h2>Family Logistics</h2>
          <form id="family-plan-form">
            <div>
              <label for="family-actor">Actor</label>
              <select id="family-actor">{users}</select>
            </div>
            <div>
              <label for="family-request">Request</label>
              <textarea id="family-request" placeholder="Give me the calm version of tonight."></textarea>
            </div>
            <button type="submit">Build Family Plan</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="family-plan-output">Awaiting family logistics request.</pre>
          </div>
          <form id="departure-plan-form" style="margin-top:16px;">
            <div>
              <label for="departure-actor">Actor</label>
              <select id="departure-actor">{adult_users}</select>
            </div>
            <div>
              <label for="departure-context">Departure Context</label>
              <textarea id="departure-context" placeholder="School drop-off, troop handoff, and lunch errand all touch the same morning."></textarea>
            </div>
            <button type="submit">Build Departure Plan</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="departure-plan-output">Loading departure choreography…</pre>
          </div>
          <div id="departure-runs" class="draft-list" style="margin-top:12px;"></div>
        </div>

        <div class="panel card">
          <h2>Rebekah Command Center</h2>
          <form id="rebekah-form">
            <div>
              <label for="rebekah-request">Coordination Request</label>
              <textarea id="rebekah-request" placeholder="Give me the calm version of tonight with troop logistics, groceries, and school prep."></textarea>
            </div>
            <button type="submit">Build Command Brief</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="rebekah-output">Awaiting coordination request.</pre>
          </div>
        </div>

        <div class="panel card">
          <h2>Staged Message Drafts</h2>
          <div id="message-drafts" class="draft-list"></div>
        </div>

        <div class="panel card">
          <h2>Troop and Grocery Support</h2>
          <form id="troop-form">
            <div>
              <label for="troop-request">Troop Planning Request</label>
              <textarea id="troop-request" placeholder="Plan tonight's troop meeting with rain risk, indoor backup, and parent message prep."></textarea>
            </div>
            <button type="submit">Build Troop Plan</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="troop-output">Awaiting troop-planning request.</pre>
          </div>
          <form id="grocery-form" style="margin-top:16px;">
            <div>
              <label for="grocery-request">Grocery and Meal Request</label>
              <textarea id="grocery-request" placeholder="Group the grocery pickup and suggest an easy dinner for a busy evening."></textarea>
            </div>
            <button type="submit">Build Grocery Plan</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="grocery-output">Awaiting grocery request.</pre>
          </div>
          <form id="meal-plan-form" style="margin-top:16px;">
            <div>
              <label for="meal-plan-actor">Actor</label>
              <select id="meal-plan-actor">{adult_users}</select>
            </div>
            <div>
              <label for="meal-plan-request">Meal Planning Request</label>
              <textarea id="meal-plan-request" placeholder="Group the pickup and keep dinner easy, warm, and fast."></textarea>
            </div>
            <button type="submit">Build Structured Meal Plan</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="meal-plan-output">Awaiting structured meal plan.</pre>
          </div>
          <div id="meal-plans" class="draft-list" style="margin-top:12px;"></div>
        </div>

        <div class="panel card">
          <h2>Vehicle and Weather Routing</h2>
          <form id="vehicle-plan-form">
            <div>
              <label for="vehicle-plan-actor">Actor</label>
              <select id="vehicle-plan-actor">{adult_users}</select>
            </div>
            <div>
              <label for="vehicle-plan-request">Vehicle Request</label>
              <textarea id="vehicle-plan-request" placeholder="Rebekah needs the van tonight, and I still need a lunch-window supply run."></textarea>
            </div>
            <button type="submit">Assign Vehicle and Route</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="vehicle-plan-output">Awaiting vehicle plan.</pre>
          </div>
          <form id="weather-plan-form" style="margin-top:16px;">
            <div>
              <label for="weather-plan-actor">Actor</label>
              <select id="weather-plan-actor">{adult_users}</select>
            </div>
            <div>
              <label for="weather-plan-request">Weather Contingency Request</label>
              <textarea id="weather-plan-request" placeholder="Light rain may affect school departure and troop arrival tonight."></textarea>
            </div>
            <button type="submit">Build Weather Contingency</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="weather-plan-output">Awaiting weather contingency.</pre>
          </div>
          <div id="vehicle-plans" class="draft-list" style="margin-top:12px;"></div>
          <div id="weather-plans" class="draft-list" style="margin-top:12px;"></div>
        </div>

        <div class="panel card">
          <h2>Parent Message Approval</h2>
          <form id="parent-message-form">
            <div class="split">
              <div>
                <label for="parent-audience">Audience</label>
                <input id="parent-audience" value="Troop parents">
              </div>
              <div>
                <label for="parent-purpose">Purpose</label>
                <input id="parent-purpose" value="Indoor backup update">
              </div>
            </div>
            <div>
              <label for="parent-context">Context</label>
              <textarea id="parent-context" placeholder="Rain may affect arrival, but the meeting is still on. Ask families to bring indoor shoes and confirm attendance."></textarea>
            </div>
            <button type="submit">Stage Parent Message</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="parent-message-output">Awaiting parent message request.</pre>
          </div>
        </div>

        <div class="panel card">
          <h2>Voice Note Follow-Ups</h2>
          <form id="voice-note-form">
            <div class="split">
              <div>
                <label for="voice-note-source">Source</label>
                <input id="voice-note-source" value="van">
              </div>
              <div>
                <label for="voice-note-actor">Actor</label>
                <select id="voice-note-actor">{users}</select>
              </div>
            </div>
            <div>
              <label for="voice-note-text">Voice Note</label>
              <textarea id="voice-note-text" placeholder="Permission forms, snack rotation, and summer camp shirt sizes."></textarea>
            </div>
            <button type="submit">Capture Voice Note</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="voice-note-output">Awaiting voice note.</pre>
          </div>
          <div id="voice-notes" class="draft-list" style="margin-top:12px;"></div>
        </div>

        <div class="panel card">
          <h2>Tutoring Coach</h2>
          <form id="tutor-form">
            <div class="split">
              <div>
                <label for="tutor-actor">Student</label>
                <select id="tutor-actor">{child_users}</select>
              </div>
              <div>
                <label for="tutor-subject">Subject</label>
                <input id="tutor-subject" placeholder="math, reading, presentation">
              </div>
            </div>
            <div>
              <label for="tutor-request">Tutoring Request</label>
              <textarea id="tutor-request" placeholder="Quiz me on fractions and help me explain my steps."></textarea>
            </div>
            <button type="submit">Coach Student</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="tutor-output">Awaiting tutoring request.</pre>
          </div>
        </div>

        <div class="panel card">
          <h2>Device Dock and Study Boundaries</h2>
          <form id="device-boundary-form">
            <div class="split">
              <div>
                <label for="boundary-actor">Student</label>
                <select id="boundary-actor">{child_users}</select>
              </div>
              <div>
                <label for="boundary-window">Window Label</label>
                <input id="boundary-window" placeholder="Evening dock">
              </div>
            </div>
            <button type="submit">Open Study Boundary Routine</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="device-boundary-output">Awaiting boundary routine.</pre>
          </div>
          <div id="device-boundaries" class="draft-list" style="margin-top:12px;"></div>
        </div>

        <div class="panel card">
          <h2>Workshop Copilot</h2>
          <form id="workshop-plan-form">
            <div>
              <label for="workshop-actor">Actor</label>
              <select id="workshop-actor">{users}</select>
            </div>
            <div>
              <label for="workshop-request">Workshop Request</label>
              <textarea id="workshop-request" placeholder="Prepare a prototype plan for the Garden of Hope bracket replacement."></textarea>
            </div>
            <button type="submit">Build Workshop Plan</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="workshop-plan-output">Awaiting workshop request.</pre>
          </div>
        </div>

        <div class="panel card">
          <h2>CAD and Material Prep</h2>
          <form id="material-form">
            <div class="split">
              <div>
                <label for="material-part">Part Name</label>
                <input id="material-part" value="Garden bench bracket">
              </div>
              <div>
                <label for="material-use-case">Use Case</label>
                <input id="material-use-case" value="Outdoor prototype and final fabrication decision">
              </div>
            </div>
            <div>
              <label for="material-requirements">Requirements</label>
              <textarea id="material-requirements" placeholder="Outdoor durability, drain path, moderate load, fast prototype iteration."></textarea>
            </div>
            <button type="submit">Recommend Material</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="material-output">Awaiting material recommendation.</pre>
          </div>
          <form id="cad-form" style="margin-top:16px;">
            <div>
              <label for="cad-part">Part Name</label>
              <input id="cad-part" value="Garden bench bracket">
            </div>
            <div>
              <label for="cad-dimensions">Dimensions</label>
              <textarea id="cad-dimensions" placeholder="hole spacing 110 mm, plate width 30 mm, thickness 8 mm, bend radius 12 mm"></textarea>
            </div>
            <div>
              <label for="cad-constraints">Constraints</label>
              <textarea id="cad-constraints" placeholder="Preserve hole pattern, add drain path, allow subtle Scout motif."></textarea>
            </div>
            <button type="submit">Generate CAD Package</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="cad-output">Awaiting CAD package request.</pre>
          </div>
          <div id="cad-packages" class="draft-list" style="margin-top:12px;"></div>
        </div>

        <div class="panel card">
          <h2>Morning Brief</h2>
          <div class="split">
            <div>
              <label for="briefing-actor">Actor</label>
              <select id="briefing-actor">{users}</select>
            </div>
            <div style="display:flex;align-items:end;">
              <button id="load-briefing">Generate Briefing</button>
            </div>
          </div>
          <div class="output-box" style="margin-top:12px;">
            <pre id="briefing-output">Select a household member to generate a briefing.</pre>
          </div>
        </div>

        <div class="panel card admin-only">
          <h2>Approvals</h2>
          <div id="approvals" class="approval-list"></div>
        </div>

        <div class="panel card admin-only">
          <h2>Integration Health</h2>
          <div id="status" class="status-list"></div>
        </div>

        <div class="panel card admin-only">
          <h2>Explainability</h2>
          <div class="output-box">
            <pre id="explainability-output">Loading explainability…</pre>
          </div>
          <div id="explainability-reasons" class="draft-list" style="margin-top:12px;"></div>
        </div>

        <div class="panel card admin-only">
          <h2>Watch Items</h2>
          <ul id="watch-items" class="watch-list"></ul>
        </div>

        <div class="panel card">
          <h2>Security and Watchtower</h2>
          <form id="security-event-form">
            <div class="split">
              <div>
                <label for="security-actor">Actor</label>
                <select id="security-actor">{users}</select>
              </div>
              <div>
                <label for="security-category">Event Type</label>
                <select id="security-category">
                  <option value="package">Package</option>
                  <option value="motion">Motion</option>
                </select>
              </div>
            </div>
            <div class="split">
              <div>
                <label for="security-location">Location</label>
                <input id="security-location" value="front porch">
              </div>
              <div>
                <label for="security-severity">Severity</label>
                <select id="security-severity">
                  <option value="watch">Watch</option>
                  <option value="elevated">Elevated</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
            </div>
            <div>
              <label for="security-detail">Detail</label>
              <textarea id="security-detail" placeholder="Package delivered near the rain-exposed edge of the porch."></textarea>
            </div>
            <button type="submit">Record Security Event</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="security-output">Awaiting security event.</pre>
          </div>
          <form id="hazard-form" style="margin-top:16px;">
            <div class="split">
              <div>
                <label for="hazard-type">Hazard</label>
                <select id="hazard-type">
                  <option value="smoke">Smoke</option>
                  <option value="co">CO</option>
                  <option value="leak">Leak</option>
                </select>
              </div>
              <div>
                <label for="hazard-source">Source</label>
                <input id="hazard-source" value="garage freezer area">
              </div>
            </div>
            <div>
              <label for="hazard-detail">Hazard Detail</label>
              <textarea id="hazard-detail" placeholder="Water pooling detected near the freezer line."></textarea>
            </div>
            <button type="submit">Escalate Hazard</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="hazard-output">Awaiting hazard escalation.</pre>
          </div>
          <form id="weather-alert-form" style="margin-top:16px;">
            <div>
              <label for="weather-context">Weather Timing Context</label>
              <textarea id="weather-context" placeholder="Troop meeting arrival and school departure both depend on a short rain break."></textarea>
            </div>
            <button type="submit">Generate Weather Advisory</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="weather-alert-output">Awaiting weather advisory.</pre>
          </div>
          <form id="arrival-form" style="margin-top:16px;">
            <div class="split">
              <div>
                <label for="arrival-actor">Child</label>
                <select id="arrival-actor">{child_users}</select>
              </div>
              <div>
                <label for="arrival-location">Arrival Location</label>
                <input id="arrival-location" value="front door">
              </div>
            </div>
            <div>
              <label for="arrival-detail">Arrival Detail</label>
              <textarea id="arrival-detail" placeholder="Backpack dropped by the mudroom door and snack requested immediately."></textarea>
            </div>
            <button type="submit">Record Arrival</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="arrival-output">Awaiting arrival event.</pre>
          </div>
          <form id="unlock-form" style="margin-top:16px;">
            <div class="split">
              <div>
                <label for="unlock-target">Unlock Target</label>
                <input id="unlock-target" value="front door">
              </div>
              <div>
                <label><input id="unlock-second-factor" type="checkbox"> Second factor present</label>
              </div>
            </div>
            <button type="submit">Check Unlock Policy</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="unlock-output">Awaiting unlock policy check.</pre>
          </div>
          <div class="output-box" style="margin-top:12px;">
            <strong>Overnight Review</strong>
            <pre id="overnight-review-output">Loading overnight watchtower review…</pre>
          </div>
          <div id="security-incidents" class="draft-list" style="margin-top:12px;"></div>
          <div id="arrival-events" class="draft-list" style="margin-top:12px;"></div>
        </div>

        <div class="panel card admin-only">
          <h2>Printer Status</h2>
          <div id="printer-status" class="status-list"></div>
        </div>

        <div class="panel card admin-only">
          <h2>Part Inspection</h2>
          <form id="inspection-form">
            <div class="split">
              <div>
                <label for="inspection-actor">Actor</label>
                <select id="inspection-actor">{users}</select>
              </div>
              <div>
                <label for="inspection-part">Part Name</label>
                <input id="inspection-part" placeholder="Garden bench bracket">
              </div>
            </div>
            <div>
              <label for="inspection-observations">Observations</label>
              <textarea id="inspection-observations" placeholder="Failed at bend radius, visible stress fracture, hole spacing unchanged."></textarea>
            </div>
            <div>
              <label for="inspection-goals">Goals</label>
              <textarea id="inspection-goals" placeholder="Increase durability, keep fit, and prototype quickly."></textarea>
            </div>
            <button type="submit">Inspect Part</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="inspection-output">Awaiting inspection input.</pre>
          </div>
          <div id="inspection-list" class="draft-list" style="margin-top:12px;"></div>
        </div>

        <div class="panel card admin-only">
          <h2>Vendor Prep</h2>
          <form id="vendor-prep-form">
            <div class="split">
              <div>
                <label for="vendor-actor">Actor</label>
                <select id="vendor-actor">{users}</select>
              </div>
              <div>
                <label for="vendor-part">Part Name</label>
                <input id="vendor-part" placeholder="Garden bench bracket">
              </div>
            </div>
            <div class="split">
              <div>
                <label for="vendor-target">Vendor Target</label>
                <input id="vendor-target" placeholder="carbon-fiber service bureau">
              </div>
              <div>
                <label for="vendor-process">Process</label>
                <input id="vendor-process" placeholder="CNC carbon-fiber nylon">
              </div>
            </div>
            <div>
              <label for="vendor-material">Material</label>
              <input id="vendor-material" placeholder="carbon-fiber nylon">
            </div>
            <div>
              <label for="vendor-notes">Notes</label>
              <textarea id="vendor-notes" placeholder="Outdoor use, drain paths, Scout motif optional if it stays strong."></textarea>
            </div>
            <button type="submit">Stage Vendor Package</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="vendor-prep-output">Awaiting vendor prep request.</pre>
          </div>
          <div id="vendor-preps" class="draft-list" style="margin-top:12px;"></div>
        </div>

        <div class="panel card admin-only">
          <h2>Print Handoff, Safety, and Inventory</h2>
          <form id="print-prep-form">
            <div class="split">
              <div>
                <label for="print-part">Part Name</label>
                <input id="print-part" value="Garden bench bracket">
              </div>
              <div>
                <label for="print-printer">Printer ID</label>
                <input id="print-printer" value="bambu-x1c">
              </div>
            </div>
            <div class="split">
              <div>
                <label for="print-material">Material</label>
                <input id="print-material" value="PETG-CF">
              </div>
              <div>
                <label for="print-profile">Profile</label>
                <input id="print-profile" value="functional-prototype">
              </div>
            </div>
            <div>
              <label for="print-notes">Notes</label>
              <textarea id="print-notes" placeholder="Orient to protect bend strength and confirm fit before load testing."></textarea>
            </div>
            <button type="submit">Stage Print Prep</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="print-output">Awaiting print-prep request.</pre>
          </div>
          <form id="safety-form" style="margin-top:16px;">
            <div>
              <label for="safety-operation">Operation</label>
              <input id="safety-operation" value="Cut and drill steel bracket replacement">
            </div>
            <div>
              <label for="safety-context">Context</label>
              <textarea id="safety-context" placeholder="Bench work, eye protection on, manual review before machine run."></textarea>
            </div>
            <button type="submit">Run Safety Check</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="safety-output">Awaiting safety check.</pre>
          </div>
          <div id="print-preps" class="draft-list" style="margin-top:12px;"></div>
          <div id="safety-checks" class="draft-list" style="margin-top:12px;"></div>
          <div id="inventory-summary" class="draft-list" style="margin-top:12px;"></div>
        </div>

        <div class="panel card">
          <h2>Parent Tutoring View</h2>
          <form id="tutoring-summary-form">
            <div class="split">
              <div>
                <label for="summary-viewer">Viewer</label>
                <select id="summary-viewer">{adult_users}</select>
              </div>
              <div>
                <label for="summary-child">Child</label>
                <select id="summary-child">
                  <option value="">All children</option>
                  {child_users}
                </select>
              </div>
            </div>
            <button type="submit">Refresh Parent View</button>
          </form>
          <div class="output-box" style="margin-top:12px;">
            <pre id="tutoring-summary-output">Loading tutoring summaries…</pre>
          </div>
          <div id="child-boundaries" class="status-list" style="margin-top:12px;"></div>
        </div>

        <div class="panel card admin-only">
          <h2>Recent Activity</h2>
          <div id="activity" class="activity-list"></div>
        </div>
      </div>
    </section>
  </div>

  <script>
    async function loadJSON(url, options) {{
      const response = await fetch(url, options);
      if (!response.ok) {{
        const text = await response.text();
        throw new Error(text || response.statusText);
      }}
      return response.json();
    }}

    function escapeHtml(text) {{
      return String(text).replace(/[&<>"]/g, (char) => ({{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;"}}[char]));
    }}

    async function refreshDashboard() {{
      const data = await loadJSON("/api/dashboard");
      document.getElementById("day-label").textContent = data.day_label;
      document.getElementById("weather-line").textContent = data.weather;
      document.getElementById("house-note").textContent = data.house_note;

      const snapshotGrid = document.getElementById("snapshot-grid");
      snapshotGrid.innerHTML = Object.values(data.cards).map((card) => `
        <div class="snapshot">
          <div class="status">${{escapeHtml(card.status)}}</div>
          <h3>${{escapeHtml(card.title)}}</h3>
          <div>${{escapeHtml(card.summary)}}</div>
          <ul>${{card.details.map((detail) => `<li>${{escapeHtml(detail)}}</li>`).join("")}}</ul>
        </div>
      `).join("");

      const bhmGrid = document.getElementById("bhm-grid");
      bhmGrid.innerHTML = (data.body_home_mission || []).map((card) => `
        <div class="snapshot">
          <div class="status">${{escapeHtml(card.status)}}</div>
          <h3>${{escapeHtml(card.title)}}</h3>
          <div>${{escapeHtml(card.summary)}}</div>
          <ul>${{(card.details || []).map((detail) => `<li>${{escapeHtml(detail)}}</li>`).join("")}}</ul>
        </div>
      `).join("");

      const timeline = document.getElementById("timeline");
      timeline.innerHTML = data.events.map((event) => `
        <div class="timeline-item">
          <div class="time">${{escapeHtml(event.time)}}</div>
          <div>
            <strong>${{escapeHtml(event.title)}}</strong><br>
            <span class="muted">${{escapeHtml(event.owner)}}</span>
            <div>${{escapeHtml(event.note)}}</div>
          </div>
        </div>
      `).join("");

      const familyFocus = document.getElementById("family-focus");
      familyFocus.innerHTML = Object.entries(data.family_focus).map(([name, items]) => `
        <div class="focus-card">
          <h3>${{escapeHtml(name)}}</h3>
          <ul>${{items.map((item) => `<li>${{escapeHtml(item)}}</li>`).join("")}}</ul>
        </div>
      `).join("");

      const watchItems = document.getElementById("watch-items");
      const departureItems = (data.departure_checklist || []).map((item) => `Departure: ${{item}}`);
      watchItems.innerHTML = [...data.watch_items, ...departureItems].map((item) => `<li>${{escapeHtml(item)}}</li>`).join("");

      const securityTarget = document.getElementById("security-incidents");
      securityTarget.innerHTML = (data.security_incidents || []).map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.headline)}}</strong> · ${{escapeHtml(item.severity)}}<br>
          <div class="muted">${{escapeHtml(item.category)}} · ${{escapeHtml(item.source)}}</div>
          <div style="margin-top:8px;">${{escapeHtml(item.detail)}}</div>
          <div class="muted" style="margin-top:8px;">${{escapeHtml(item.recommended_action)}}</div>
        </div>
      `).join("") || '<div class="approval-item muted">No security incidents logged.</div>';

      const arrivalTarget = document.getElementById("arrival-events");
      arrivalTarget.innerHTML = (data.arrival_events || []).map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.actor)}}</strong> · ${{escapeHtml(item.location)}} · ${{escapeHtml(item.status)}}<br>
          <div style="margin-top:8px;">${{escapeHtml(item.detail)}}</div>
          <ul>${{(item.next_steps || []).map((step) => `<li>${{escapeHtml(step)}}</li>`).join("")}}</ul>
        </div>
      `).join("") || '<div class="approval-item muted">No arrival events recorded.</div>';

      if ((data.weather_advisories || []).length && document.getElementById("weather-alert-output").textContent === "Awaiting weather advisory.") {{
        document.getElementById("weather-alert-output").textContent = JSON.stringify(data.weather_advisories[0], null, 2);
      }}
      if ((data.unlock_assessments || []).length && document.getElementById("unlock-output").textContent === "Awaiting unlock policy check.") {{
        document.getElementById("unlock-output").textContent = JSON.stringify(data.unlock_assessments[0], null, 2);
      }}
      document.getElementById("overnight-review-output").textContent = JSON.stringify(data.overnight_review || {{}}, null, 2);
      document.getElementById("outage-output").textContent = JSON.stringify(data.outage_readiness || {{}}, null, 2);
      document.getElementById("privacy-output").textContent = JSON.stringify((data.perception_overview || {{}}).privacy_state || {{}}, null, 2);

      const homeSummary = document.getElementById("home-summary");
      homeSummary.innerHTML = ((data.home_overview || {{}}).summary || []).map((item) => `
        <div class="status-item">${{escapeHtml(item)}}</div>
      `).join("") || '<div class="status-item muted">No home-control summary loaded.</div>';

      const leakSummary = document.getElementById("leak-summary");
      leakSummary.innerHTML = ((data.leak_monitor || {{}}).all_sensors || []).map((item) => `
        <div class="status-item">
          <strong>${{escapeHtml(item.name)}}</strong> · ${{escapeHtml(item.state)}}<br>
          <div class="muted">${{escapeHtml(item.location || "")}}</div>
        </div>
      `).join("") || '<div class="status-item muted">No leak sensors loaded.</div>';

      const coldStorageSummary = document.getElementById("cold-storage-summary");
      coldStorageSummary.innerHTML = ((data.cold_storage_monitor || {{}}).all_sensors || []).map((item) => `
        <div class="status-item">
          <strong>${{escapeHtml(item.name)}}</strong> · ${{escapeHtml(item.severity)}}<br>
          <div class="muted">${{escapeHtml(item.location || "")}} · variance ${{escapeHtml(String(item.variance_degrees))}}F</div>
        </div>
      `).join("") || '<div class="status-item muted">No cold-storage sensors loaded.</div>';

      if ((data.climate_status || []).length && document.getElementById("climate-output").textContent === "Awaiting climate request.") {{
        document.getElementById("climate-output").textContent = JSON.stringify(data.climate_status[0], null, 2);
      }}
      if ((data.garage_status || []).length && document.getElementById("garage-output").textContent === "Awaiting garage safety check.") {{
        document.getElementById("garage-output").textContent = JSON.stringify(data.garage_status[0], null, 2);
      }}

      const perceptionSummary = document.getElementById("perception-summary");
      perceptionSummary.innerHTML = ((data.perception_overview || {{}}).summary || []).map((item) => `
        <div class="status-item">${{escapeHtml(item)}}</div>
      `).join("") || '<div class="status-item muted">No perception summary loaded.</div>';

      const memoryOverview = data.memory_overview || {{}};
      const memorySummaryPanel = document.getElementById("memory-summary-panel");
      memorySummaryPanel.innerHTML = [
        `Visible entries: ${{escapeHtml(String((memoryOverview.counts || {{}}).visible_entries || 0))}}`,
        `Cloud excluded: ${{escapeHtml(String((memoryOverview.counts || {{}}).cloud_excluded_entries || 0))}}`,
        `Pending proposals: ${{escapeHtml(String((memoryOverview.counts || {{}}).pending_proposals || 0))}}`
      ].map((item) => `<div class="status-item">${{item}}</div>`).join("");

      const memoryProposals = document.getElementById("memory-proposals");
      memoryProposals.innerHTML = (memoryOverview.pending_proposals || []).map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.title)}}</strong> · ${{escapeHtml(item.memory_type)}} · ${{escapeHtml(item.status)}}<br>
          <div class="muted">${{escapeHtml(item.summary)}}</div>
          <div style="margin-top:8px;">${{escapeHtml(item.rationale || "")}}</div>
        </div>
      `).join("") || '<div class="approval-item muted">No pending memory proposals.</div>';

      const explainability = data.explainability || {{}};
      document.getElementById("explainability-output").textContent = JSON.stringify({{
        blocked_integrations: explainability.blocked_integrations || [],
        module_counts: explainability.module_counts || {{}},
        approval_history_count: (explainability.approval_history || []).length
      }}, null, 2);
      const explainabilityReasons = document.getElementById("explainability-reasons");
      explainabilityReasons.innerHTML = (explainability.latest_reasons || []).map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.actor)}}</strong> · ${{escapeHtml(item.module)}} · ${{escapeHtml(item.action_class)}}<br>
          <div>${{escapeHtml(item.request)}}</div>
          <div class="muted" style="margin-top:8px;">${{escapeHtml(item.rationale)}}</div>
        </div>
      `).join("") || '<div class="approval-item muted">No explainability records yet.</div>';

      document.getElementById("mode-output").textContent =
        `Mode: ${{data.active_mode.mode}}\nStatus: ${{data.active_mode.status}}\nReason: ${{data.active_mode.reason}}\nActor: ${{data.active_mode.actor}}`;
      document.getElementById("mode-brief-output").textContent = JSON.stringify(data.mode_brief || {{}}, null, 2);

      const departureTarget = document.getElementById("departure-runs");
      departureTarget.innerHTML = (data.departure_runs || []).map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.actor)}}</strong> · departure run<br>
          <div class="muted">${{escapeHtml(item.headline)}}</div>
          <div style="margin-top:8px;">${{escapeHtml(item.weather_hold)}}</div>
          <ul>${{(item.focus_calls || []).map((task) => `<li>${{escapeHtml(task)}}</li>`).join("")}}</ul>
        </div>
      `).join("") || '<div class="approval-item muted">No departure runs yet.</div>';

      const draftTarget = document.getElementById("message-drafts");
      if (!(data.message_drafts || []).length) {{
        draftTarget.innerHTML = '<div class="approval-item muted">No staged drafts.</div>';
      }} else {{
        draftTarget.innerHTML = data.message_drafts.map((draft) => `
          <div class="approval-item">
            <strong>${{escapeHtml(draft.audience)}}</strong> · ${{escapeHtml(draft.tone)}} · ${{escapeHtml(draft.status)}}<br>
            <div class="muted">${{escapeHtml(draft.purpose)}}</div>
            <div style="margin-top:8px;">${{escapeHtml(draft.body)}}</div>
          </div>
        `).join("");
      }}

      const boundaries = document.getElementById("child-boundaries");
      boundaries.innerHTML = (data.child_boundaries || []).map((item) => `
        <div class="status-item">
          <strong>${{escapeHtml(item.actor)}}</strong><br>
          <div class="muted">Allowed: ${{escapeHtml((item.allowed_modules || []).join(", "))}}</div>
          <div class="muted">Blocked: ${{escapeHtml((item.forbidden_modules || []).join(", "))}}</div>
        </div>
      `).join("") || '<div class="status-item muted">No child boundary profiles loaded.</div>';

      document.getElementById("tutoring-summary-output").textContent = JSON.stringify(data.tutoring_summaries || {{}}, null, 2);

      const printerTarget = document.getElementById("printer-status");
      printerTarget.innerHTML = (data.printer_status || []).map((item) => `
        <div class="status-item">
          <strong>${{escapeHtml(item.name)}}</strong> · ${{escapeHtml(item.status)}} · ${{escapeHtml(String(item.progress_percent))}}%<br>
          <div class="muted">${{escapeHtml(item.material)}} · ${{escapeHtml(item.active_job)}}</div>
          <div class="muted">${{escapeHtml(item.note)}}</div>
        </div>
      `).join("") || '<div class="status-item muted">No printer profile loaded.</div>';

      const vendorTarget = document.getElementById("vendor-preps");
      vendorTarget.innerHTML = (data.vendor_preps || []).map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.part_name)}}</strong> · ${{escapeHtml(item.vendor_target)}} · ${{escapeHtml(item.status)}}<br>
          <div class="muted">${{escapeHtml(item.process)}} · ${{escapeHtml(item.material)}}</div>
          <div style="margin-top:8px;">${{escapeHtml(item.package_summary)}}</div>
        </div>
      `).join("") || '<div class="approval-item muted">No staged vendor packages.</div>';

      const inspectionTarget = document.getElementById("inspection-list");
      inspectionTarget.innerHTML = (data.workshop_inspections || []).map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.part_name)}}</strong> · ${{escapeHtml(item.actor)}}<br>
          <div class="muted">${{escapeHtml(item.recommended_material)}}</div>
          <div style="margin-top:8px;">${{escapeHtml(item.diagnosis)}}</div>
        </div>
      `).join("") || '<div class="approval-item muted">No workshop inspections yet.</div>';

      const cadTarget = document.getElementById("cad-packages");
      cadTarget.innerHTML = (data.cad_packages || []).map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.part_name)}}</strong> · CAD package<br>
          <div class="muted">${{escapeHtml(item.summary)}}</div>
          <div style="margin-top:8px;">${{escapeHtml((item.parameters || []).join(", "))}}</div>
        </div>
      `).join("") || '<div class="approval-item muted">No CAD packages yet.</div>';

      const printPrepTarget = document.getElementById("print-preps");
      printPrepTarget.innerHTML = (data.print_preps || []).map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.part_name)}}</strong> · ${{escapeHtml(item.printer_id)}} · ${{escapeHtml(item.status)}}<br>
          <div class="muted">${{escapeHtml(item.material)}} · ${{escapeHtml(item.profile_name)}}</div>
          <div style="margin-top:8px;">${{escapeHtml(item.handoff_notes)}}</div>
        </div>
      `).join("") || '<div class="approval-item muted">No print-prep handoffs yet.</div>';

      const materialTarget = document.getElementById("material-output");
      if ((data.material_recommendations || []).length && materialTarget.textContent === "Awaiting material recommendation.") {{
        materialTarget.textContent = JSON.stringify(data.material_recommendations[0], null, 2);
      }}

      const safetyTarget = document.getElementById("safety-checks");
      safetyTarget.innerHTML = (data.safety_checks || []).map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.operation)}}</strong> · ${{item.allowed ? "allowed" : "blocked"}}<br>
          <div class="muted">${{escapeHtml(item.recommendation)}}</div>
          <ul>${{(item.warnings || []).map((warn) => `<li>${{escapeHtml(warn)}}</li>`).join("")}}</ul>
        </div>
      `).join("") || '<div class="approval-item muted">No safety checks yet.</div>';

      const inventoryTarget = document.getElementById("inventory-summary");
      inventoryTarget.innerHTML = (data.inventory_summary || []).map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.name)}}</strong> · ${{escapeHtml(item.status)}}<br>
          <div class="muted">${{escapeHtml(item.category)}} · ${{escapeHtml(item.quantity)}}</div>
          <div style="margin-top:8px;">${{escapeHtml(item.restock_note)}}</div>
        </div>
      `).join("") || '<div class="approval-item muted">No inventory items loaded.</div>';

      const voiceNoteTarget = document.getElementById("voice-notes");
      voiceNoteTarget.innerHTML = (data.voice_note_tasks || []).map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.source)}}</strong> · ${{escapeHtml(item.actor)}} · ${{escapeHtml(item.status)}}<br>
          <div class="muted">${{escapeHtml(item.note)}}</div>
          <ul>${{(item.tasks || []).map((task) => `<li>${{escapeHtml(task)}}</li>`).join("")}}</ul>
        </div>
      `).join("") || '<div class="approval-item muted">No captured voice notes.</div>';

      const mealPlanTarget = document.getElementById("meal-plans");
      mealPlanTarget.innerHTML = (data.meal_plans || []).map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.meal_suggestion)}}</strong> · meal plan<br>
          <div class="muted">${{escapeHtml(item.actor)}}</div>
          <div style="margin-top:8px;">${{escapeHtml(item.request)}}</div>
        </div>
      `).join("") || '<div class="approval-item muted">No meal plans yet.</div>';

      const vehiclePlanTarget = document.getElementById("vehicle-plans");
      vehiclePlanTarget.innerHTML = (data.vehicle_plans || []).map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.vehicle)}}</strong> · ${{escapeHtml(item.actor)}}<br>
          <div class="muted">${{escapeHtml((item.route_notes || []).join(" | "))}}</div>
          <div style="margin-top:8px;">${{escapeHtml(item.request)}}</div>
        </div>
      `).join("") || '<div class="approval-item muted">No vehicle plans yet.</div>';

      const weatherPlanTarget = document.getElementById("weather-plans");
      weatherPlanTarget.innerHTML = (data.weather_plans || []).map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.risk_level)}}</strong> weather posture<br>
          <div class="muted">${{escapeHtml(item.weather)}}</div>
          <ul>${{(item.actions || []).map((step) => `<li>${{escapeHtml(step)}}</li>`).join("")}}</ul>
        </div>
      `).join("") || '<div class="approval-item muted">No weather plans yet.</div>';

      const chronicleThemes = document.getElementById("chronicle-theme-summary");
      chronicleThemes.innerHTML = ((data.chronicle_theme_summary || {{}}).themes || []).map((item) => `
        <div class="status-item">
          <strong>${{escapeHtml(item.theme)}}</strong> · ${{escapeHtml(String(item.count))}}<br>
          <div class="muted">${{escapeHtml((item.recent_reflections || []).join(" | "))}}</div>
        </div>
      `).join("") || '<div class="status-item muted">No Chronicle themes yet.</div>';

      const chronicleTimeline = document.getElementById("chronicle-timeline");
      chronicleTimeline.innerHTML = (data.chronicle_timeline || []).map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.theme)}}</strong> · ${{escapeHtml(item.actor)}}<br>
          <div class="muted">${{escapeHtml(item.note)}}</div>
          <div style="margin-top:8px;">${{escapeHtml(item.reflection)}}</div>
        </div>
      `).join("") || '<div class="approval-item muted">No Chronicle entries yet.</div>';

      const boundaryTarget = document.getElementById("device-boundaries");
      boundaryTarget.innerHTML = (data.device_boundaries || []).map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.actor)}}</strong> · ${{escapeHtml(item.window_label)}} · ${{escapeHtml(item.status)}}<br>
          <div class="muted">${{escapeHtml(item.device_expectation)}}</div>
          <ul>${{(item.checklist || []).map((task) => `<li>${{escapeHtml(task)}}</li>`).join("")}}</ul>
        </div>
      `).join("") || '<div class="approval-item muted">No device-boundary routines yet.</div>';
    }}

    async function refreshStatus() {{
      const items = await loadJSON("/api/status");
      document.getElementById("status").innerHTML = items.map((item) => `
        <div class="status-item">
          <strong>${{escapeHtml(item.name)}}</strong><br>
          <span class="${{item.ok ? "ok" : "blocked"}}">${{item.ok ? "ok" : "blocked"}}</span>
          <div class="muted">${{escapeHtml(item.detail)}}</div>
        </div>
      `).join("");
    }}

    async function refreshApprovals() {{
      const items = await loadJSON("/api/approvals");
      const target = document.getElementById("approvals");
      if (!items.length) {{
        target.innerHTML = '<div class="approval-item muted">No pending approvals.</div>';
        return;
      }}
      target.innerHTML = items.map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.actor)}}</strong> · ${{escapeHtml(item.action_class)}}<br>
          <div>${{escapeHtml(item.request)}}</div>
          <div class="muted" style="margin:8px 0;">${{escapeHtml(item.rationale)}}</div>
          <div class="preset-row">
            <button data-id="${{item.request_id}}" data-status="approved">Approve</button>
            <button class="ghost" data-id="${{item.request_id}}" data-status="rejected">Reject</button>
          </div>
        </div>
      `).join("");
      target.querySelectorAll("button[data-id]").forEach((button) => {{
        button.addEventListener("click", async () => {{
          await loadJSON(`/api/approvals/${{button.dataset.id}}`, {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ status: button.dataset.status }})
          }});
          await refreshApprovals();
        }});
      }});
    }}

    async function refreshActivity() {{
      const items = await loadJSON("/api/activity");
      const target = document.getElementById("activity");
      if (!items.length) {{
        target.innerHTML = '<div class="activity-item muted">No actions logged yet.</div>';
        return;
      }}
      target.innerHTML = items.map((item) => `
        <div class="activity-item">
          <strong>${{escapeHtml(item.actor)}}</strong> · ${{escapeHtml(item.module)}} · ${{escapeHtml(item.model)}} · ${{escapeHtml(item.action_class || "")}}<br>
          <div>${{escapeHtml(item.request)}}</div>
          <div class="muted">${{escapeHtml(item.rationale || "")}}</div>
          <div class="muted">${{escapeHtml(item.timestamp || "")}}</div>
        </div>
      `).join("");
    }}

    function setDisplayMode(mode) {{
      const family = mode === "family";
      document.body.classList.toggle("family-display", family);
      document.querySelectorAll("#display-mode button").forEach((button) => {{
        button.classList.toggle("active", button.dataset.display === mode);
      }});
      window.localStorage.setItem("jarvis-display-mode", mode);
    }}

    async function loadBriefing() {{
      const actor = document.getElementById("briefing-actor").value;
      const data = await loadJSON(`/api/briefing?actor=${{encodeURIComponent(actor)}}`);
      document.getElementById("briefing-output").textContent = data.briefing;
    }}

    function currentPayload() {{
      return {{
        actor: document.getElementById("actor").value,
        room: document.getElementById("room").value,
        request: document.getElementById("request").value
      }};
    }}

    async function planRequest() {{
      const data = await loadJSON("/api/plan", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(currentPayload())
      }});
      document.getElementById("plan-output").textContent = JSON.stringify(data, null, 2);
      await refreshApprovals();
      await refreshActivity();
    }}

    async function respondRequest() {{
      const data = await loadJSON("/api/respond", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(currentPayload())
      }});
      document.getElementById("respond-output").textContent = data.output_text || "(No response text returned.)";
      await refreshActivity();
    }}

    async function familyPlanRequest() {{
      const data = await loadJSON("/api/family-plan", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("family-actor").value,
          request: document.getElementById("family-request").value
        }})
      }});
      document.getElementById("family-plan-output").textContent = data.output_text || "(No family plan returned.)";
    }}

    async function modeBriefRequest() {{
      const data = await loadJSON("/api/mode-brief", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          mode: document.getElementById("mode-brief-target").value
        }})
      }});
      document.getElementById("mode-brief-output").textContent = JSON.stringify(data, null, 2);
    }}

    async function departurePlanRequest() {{
      const data = await loadJSON("/api/departure-plan", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("departure-actor").value,
          context: document.getElementById("departure-context").value
        }})
      }});
      document.getElementById("departure-plan-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function rebekahRequest() {{
      const data = await loadJSON("/api/rebekah-center", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          request: document.getElementById("rebekah-request").value
        }})
      }});
      document.getElementById("rebekah-output").textContent = data.output_text || "(No command brief returned.)";
    }}

    async function troopRequest() {{
      const data = await loadJSON("/api/troop-plan", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: "Rebekah",
          request: document.getElementById("troop-request").value
        }})
      }});
      document.getElementById("troop-output").textContent = data.output_text || "(No troop plan returned.)";
    }}

    async function groceryRequest() {{
      const data = await loadJSON("/api/grocery-support", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: "Rebekah",
          request: document.getElementById("grocery-request").value
        }})
      }});
      document.getElementById("grocery-output").textContent = data.output_text || "(No grocery plan returned.)";
    }}

    async function mealPlanRequest() {{
      const data = await loadJSON("/api/meal-plan", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("meal-plan-actor").value,
          request: document.getElementById("meal-plan-request").value
        }})
      }});
      document.getElementById("meal-plan-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function vehiclePlanRequest() {{
      const data = await loadJSON("/api/vehicle-plan", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("vehicle-plan-actor").value,
          request: document.getElementById("vehicle-plan-request").value
        }})
      }});
      document.getElementById("vehicle-plan-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function weatherPlanRequest() {{
      const data = await loadJSON("/api/weather-contingency", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("weather-plan-actor").value,
          request: document.getElementById("weather-plan-request").value
        }})
      }});
      document.getElementById("weather-plan-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function parentMessageRequest() {{
      const data = await loadJSON("/api/parent-message", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: "Rebekah",
          audience: document.getElementById("parent-audience").value,
          purpose: document.getElementById("parent-purpose").value,
          context: document.getElementById("parent-context").value,
          tone: "warm"
        }})
      }});
      document.getElementById("parent-message-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
      await refreshApprovals();
    }}

    async function voiceNoteRequest() {{
      const data = await loadJSON("/api/voice-note", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("voice-note-actor").value,
          source: document.getElementById("voice-note-source").value,
          note: document.getElementById("voice-note-text").value
        }})
      }});
      document.getElementById("voice-note-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function sceneRequest() {{
      const data = await loadJSON("/api/room-scene", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("scene-actor").value,
          room: document.getElementById("scene-room").value,
          scene: document.getElementById("scene-name").value
        }})
      }});
      document.getElementById("scene-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function climateRequest() {{
      const data = await loadJSON("/api/climate-control", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("scene-actor").value,
          zone: document.getElementById("climate-zone").value,
          mode: document.getElementById("climate-mode").value,
          target_temp: Number(document.getElementById("climate-target").value || 0)
        }})
      }});
      document.getElementById("climate-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function garageRequest() {{
      const data = await loadJSON("/api/garage-check", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("scene-actor").value,
          target: document.getElementById("garage-target").value
        }})
      }});
      document.getElementById("garage-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function energyRequest() {{
      const data = await loadJSON("/api/energy-window", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          appliance: document.getElementById("energy-appliance").value
        }})
      }});
      document.getElementById("energy-output").textContent = JSON.stringify(data, null, 2);
    }}

    async function micRequest() {{
      const data = await loadJSON("/api/mic-ingress", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          microphone: document.getElementById("mic-name").value,
          transcript: document.getElementById("mic-transcript").value,
          wake_word: true,
          actor_hint: document.getElementById("mic-actor-hint").value
        }})
      }});
      document.getElementById("mic-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function presenceRequest() {{
      const data = await loadJSON("/api/presence-update", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          sensor: document.getElementById("presence-sensor").value,
          room: document.getElementById("presence-room").value,
          occupied: true,
          detail: "Occupied during dashboard test."
        }})
      }});
      document.getElementById("presence-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function phoneRequest() {{
      const data = await loadJSON("/api/phone-presence", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("phone-actor").value,
          state: document.getElementById("phone-state").value,
          detail: "Phone presence updated from dashboard.",
          zone: "home-boundary"
        }})
      }});
      document.getElementById("phone-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function cameraRequest() {{
      const data = await loadJSON("/api/camera-event", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          camera: document.getElementById("camera-name").value,
          event_type: document.getElementById("camera-event-type").value,
          detail: document.getElementById("camera-detail").value,
          object: document.getElementById("camera-event-type").value === "package" ? "package" : "bench bracket"
        }})
      }});
      document.getElementById("camera-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function memoryRequest() {{
      const data = await loadJSON("/api/memory-remember", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("memory-actor").value,
          type: document.getElementById("memory-type").value,
          scope: document.getElementById("memory-scope").value,
          owner: document.getElementById("memory-owner").value,
          project: document.getElementById("memory-project").value,
          summary: document.getElementById("memory-summary").value,
          detail: document.getElementById("memory-detail").value,
          tags: document.getElementById("memory-tags").value,
          sensitivity: document.getElementById("memory-sensitivity").value
        }})
      }});
      document.getElementById("memory-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function securityEventRequest() {{
      const data = await loadJSON("/api/security-event", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("security-actor").value,
          category: document.getElementById("security-category").value,
          location: document.getElementById("security-location").value,
          detail: document.getElementById("security-detail").value,
          severity: document.getElementById("security-severity").value
        }})
      }});
      document.getElementById("security-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
      await refreshActivity();
    }}

    async function hazardAlertRequest() {{
      const data = await loadJSON("/api/safety-alert", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("security-actor").value,
          hazard: document.getElementById("hazard-type").value,
          source: document.getElementById("hazard-source").value,
          detail: document.getElementById("hazard-detail").value,
          severity: "critical"
        }})
      }});
      document.getElementById("hazard-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
      await refreshActivity();
    }}

    async function weatherAlertRequest() {{
      const data = await loadJSON("/api/weather-alert", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("security-actor").value,
          context: document.getElementById("weather-context").value
        }})
      }});
      document.getElementById("weather-alert-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function arrivalRequest() {{
      const data = await loadJSON("/api/child-arrival", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("arrival-actor").value,
          location: document.getElementById("arrival-location").value,
          detail: document.getElementById("arrival-detail").value
        }})
      }});
      document.getElementById("arrival-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function unlockPolicyRequest() {{
      const data = await loadJSON("/api/unlock-policy", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("security-actor").value,
          target: document.getElementById("unlock-target").value,
          requested_by_voice: true,
          second_factor_present: document.getElementById("unlock-second-factor").checked
        }})
      }});
      document.getElementById("unlock-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function tutorRequest() {{
      const data = await loadJSON("/api/tutor", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("tutor-actor").value,
          request: document.getElementById("tutor-request").value,
          subject: document.getElementById("tutor-subject").value
        }})
      }});
      document.getElementById("tutor-output").textContent = data.response_text || JSON.stringify(data, null, 2);
      await refreshTutoringSummaries();
      await refreshActivity();
    }}

    async function refreshTutoringSummaries() {{
      const viewer = document.getElementById("summary-viewer").value;
      const child = document.getElementById("summary-child").value;
      const query = new URLSearchParams({{ viewer, child }});
      const data = await loadJSON(`/api/tutoring-summaries?${{query.toString()}}`);
      document.getElementById("tutoring-summary-output").textContent = JSON.stringify(data, null, 2);
    }}

    async function executiveTaskRequest() {{
      const data = await loadJSON("/api/executive-task", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("executive-actor").value,
          task: document.getElementById("executive-task").value,
          topic: document.getElementById("executive-topic").value,
          primary: document.getElementById("executive-primary").value,
          secondary: document.getElementById("executive-secondary").value
        }})
      }});
      document.getElementById("executive-output").textContent = data.output_text || "(No executive output returned.)";
    }}

    async function chronicleDevotionalRequest() {{
      const data = await loadJSON("/api/devotional-pause", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("chronicle-actor").value,
          theme: document.getElementById("chronicle-theme").value,
          mode: document.getElementById("chronicle-mode").value
        }})
      }});
      document.getElementById("chronicle-devotional-output").textContent = data.output_text || "(No devotional pause returned.)";
    }}

    async function familyDevotionalRequest() {{
      const data = await loadJSON("/api/family-devotional", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("chronicle-actor").value,
          theme: document.getElementById("family-devotional-theme").value,
          context: document.getElementById("family-devotional-context").value
        }})
      }});
      document.getElementById("family-devotional-output").textContent = data.output_text || "(No family devotional returned.)";
    }}

    async function chronicleCaptureRequest() {{
      const data = await loadJSON("/api/chronicle-capture", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("chronicle-actor").value,
          theme: document.getElementById("chronicle-theme").value,
          note: document.getElementById("chronicle-note").value
        }})
      }});
      document.getElementById("chronicle-capture-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function deviceBoundaryRequest() {{
      const data = await loadJSON("/api/device-boundary", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("boundary-actor").value,
          window: document.getElementById("boundary-window").value
        }})
      }});
      document.getElementById("device-boundary-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function workshopPlanRequest() {{
      const data = await loadJSON("/api/workshop-plan", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("workshop-actor").value,
          request: document.getElementById("workshop-request").value
        }})
      }});
      document.getElementById("workshop-plan-output").textContent = data.output_text || "(No workshop plan returned.)";
    }}

    async function inspectPartRequest() {{
      const data = await loadJSON("/api/inspect-part", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("inspection-actor").value,
          part: document.getElementById("inspection-part").value,
          observations: document.getElementById("inspection-observations").value,
          goals: document.getElementById("inspection-goals").value,
          request: "Inspect this part and recommend a prototype path."
        }})
      }});
      document.getElementById("inspection-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
      await refreshActivity();
    }}

    async function materialRecommendationRequest() {{
      const data = await loadJSON("/api/material-recommendation", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: "Chris",
          part: document.getElementById("material-part").value,
          use_case: document.getElementById("material-use-case").value,
          requirements: document.getElementById("material-requirements").value
        }})
      }});
      document.getElementById("material-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function cadPackageRequest() {{
      const data = await loadJSON("/api/cad-package", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: "Chris",
          part: document.getElementById("cad-part").value,
          dimensions: document.getElementById("cad-dimensions").value,
          constraints: document.getElementById("cad-constraints").value
        }})
      }});
      document.getElementById("cad-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function printPrepRequest() {{
      const data = await loadJSON("/api/print-prep", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: "Chris",
          part: document.getElementById("print-part").value,
          printer: document.getElementById("print-printer").value,
          material: document.getElementById("print-material").value,
          profile: document.getElementById("print-profile").value,
          notes: document.getElementById("print-notes").value
        }})
      }});
      document.getElementById("print-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function safetyCheckRequest() {{
      const data = await loadJSON("/api/safety-check", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: "Chris",
          operation: document.getElementById("safety-operation").value,
          context: document.getElementById("safety-context").value
        }})
      }});
      document.getElementById("safety-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function vendorPrepRequest() {{
      const data = await loadJSON("/api/vendor-prep", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: document.getElementById("vendor-actor").value,
          part: document.getElementById("vendor-part").value,
          vendor: document.getElementById("vendor-target").value,
          process: document.getElementById("vendor-process").value,
          material: document.getElementById("vendor-material").value,
          notes: document.getElementById("vendor-notes").value
        }})
      }});
      document.getElementById("vendor-prep-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
      await refreshApprovals();
      await refreshActivity();
    }}

    document.getElementById("load-briefing").addEventListener("click", () => {{
      loadBriefing().catch((error) => {{
        document.getElementById("briefing-output").textContent = error.message;
      }});
    }});

    document.getElementById("plan-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      planRequest().catch((error) => {{
        document.getElementById("plan-output").textContent = error.message;
      }});
    }});

    document.getElementById("respond-button").addEventListener("click", () => {{
      respondRequest().catch((error) => {{
        document.getElementById("respond-output").textContent = error.message;
      }});
    }});

    document.getElementById("family-plan-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      familyPlanRequest().catch((error) => {{
        document.getElementById("family-plan-output").textContent = error.message;
      }});
    }});

    document.getElementById("mode-brief-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      modeBriefRequest().catch((error) => {{
        document.getElementById("mode-brief-output").textContent = error.message;
      }});
    }});

    document.getElementById("departure-plan-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      departurePlanRequest().catch((error) => {{
        document.getElementById("departure-plan-output").textContent = error.message;
      }});
    }});

    document.getElementById("rebekah-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      rebekahRequest().catch((error) => {{
        document.getElementById("rebekah-output").textContent = error.message;
      }});
    }});

    document.getElementById("troop-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      troopRequest().catch((error) => {{
        document.getElementById("troop-output").textContent = error.message;
      }});
    }});

    document.getElementById("grocery-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      groceryRequest().catch((error) => {{
        document.getElementById("grocery-output").textContent = error.message;
      }});
    }});

    document.getElementById("meal-plan-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      mealPlanRequest().catch((error) => {{
        document.getElementById("meal-plan-output").textContent = error.message;
      }});
    }});

    document.getElementById("vehicle-plan-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      vehiclePlanRequest().catch((error) => {{
        document.getElementById("vehicle-plan-output").textContent = error.message;
      }});
    }});

    document.getElementById("weather-plan-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      weatherPlanRequest().catch((error) => {{
        document.getElementById("weather-plan-output").textContent = error.message;
      }});
    }});

    document.getElementById("parent-message-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      parentMessageRequest().catch((error) => {{
        document.getElementById("parent-message-output").textContent = error.message;
      }});
    }});

    document.getElementById("voice-note-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      voiceNoteRequest().catch((error) => {{
        document.getElementById("voice-note-output").textContent = error.message;
      }});
    }});

    document.getElementById("scene-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      sceneRequest().catch((error) => {{
        document.getElementById("scene-output").textContent = error.message;
      }});
    }});

    document.getElementById("climate-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      climateRequest().catch((error) => {{
        document.getElementById("climate-output").textContent = error.message;
      }});
    }});

    document.getElementById("garage-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      garageRequest().catch((error) => {{
        document.getElementById("garage-output").textContent = error.message;
      }});
    }});

    document.getElementById("energy-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      energyRequest().catch((error) => {{
        document.getElementById("energy-output").textContent = error.message;
      }});
    }});

    document.getElementById("mic-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      micRequest().catch((error) => {{
        document.getElementById("mic-output").textContent = error.message;
      }});
    }});

    document.getElementById("presence-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      presenceRequest().catch((error) => {{
        document.getElementById("presence-output").textContent = error.message;
      }});
    }});

    document.getElementById("phone-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      phoneRequest().catch((error) => {{
        document.getElementById("phone-output").textContent = error.message;
      }});
    }});

    document.getElementById("camera-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      cameraRequest().catch((error) => {{
        document.getElementById("camera-output").textContent = error.message;
      }});
    }});

    document.getElementById("memory-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      memoryRequest().catch((error) => {{
        document.getElementById("memory-output").textContent = error.message;
      }});
    }});

    document.getElementById("security-event-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      securityEventRequest().catch((error) => {{
        document.getElementById("security-output").textContent = error.message;
      }});
    }});

    document.getElementById("hazard-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      hazardAlertRequest().catch((error) => {{
        document.getElementById("hazard-output").textContent = error.message;
      }});
    }});

    document.getElementById("weather-alert-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      weatherAlertRequest().catch((error) => {{
        document.getElementById("weather-alert-output").textContent = error.message;
      }});
    }});

    document.getElementById("arrival-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      arrivalRequest().catch((error) => {{
        document.getElementById("arrival-output").textContent = error.message;
      }});
    }});

    document.getElementById("unlock-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      unlockPolicyRequest().catch((error) => {{
        document.getElementById("unlock-output").textContent = error.message;
      }});
    }});

    document.getElementById("tutor-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      tutorRequest().catch((error) => {{
        document.getElementById("tutor-output").textContent = error.message;
      }});
    }});

    document.getElementById("device-boundary-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      deviceBoundaryRequest().catch((error) => {{
        document.getElementById("device-boundary-output").textContent = error.message;
      }});
    }});

    document.getElementById("tutoring-summary-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      refreshTutoringSummaries().catch((error) => {{
        document.getElementById("tutoring-summary-output").textContent = error.message;
      }});
    }});

    document.getElementById("executive-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      executiveTaskRequest().catch((error) => {{
        document.getElementById("executive-output").textContent = error.message;
      }});
    }});

    document.getElementById("chronicle-devotional-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      chronicleDevotionalRequest().catch((error) => {{
        document.getElementById("chronicle-devotional-output").textContent = error.message;
      }});
    }});

    document.getElementById("family-devotional-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      familyDevotionalRequest().catch((error) => {{
        document.getElementById("family-devotional-output").textContent = error.message;
      }});
    }});

    document.getElementById("chronicle-capture-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      chronicleCaptureRequest().catch((error) => {{
        document.getElementById("chronicle-capture-output").textContent = error.message;
      }});
    }});

    document.getElementById("workshop-plan-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      workshopPlanRequest().catch((error) => {{
        document.getElementById("workshop-plan-output").textContent = error.message;
      }});
    }});

    document.getElementById("inspection-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      inspectPartRequest().catch((error) => {{
        document.getElementById("inspection-output").textContent = error.message;
      }});
    }});

    document.getElementById("material-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      materialRecommendationRequest().catch((error) => {{
        document.getElementById("material-output").textContent = error.message;
      }});
    }});

    document.getElementById("cad-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      cadPackageRequest().catch((error) => {{
        document.getElementById("cad-output").textContent = error.message;
      }});
    }});

    document.getElementById("print-prep-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      printPrepRequest().catch((error) => {{
        document.getElementById("print-output").textContent = error.message;
      }});
    }});

    document.getElementById("safety-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      safetyCheckRequest().catch((error) => {{
        document.getElementById("safety-output").textContent = error.message;
      }});
    }});

    document.getElementById("vendor-prep-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      vendorPrepRequest().catch((error) => {{
        document.getElementById("vendor-prep-output").textContent = error.message;
      }});
    }});

    document.querySelectorAll(".preset").forEach((button) => {{
      button.addEventListener("click", () => {{
        document.getElementById("request").value = button.dataset.preset;
      }});
    }});

    document.querySelectorAll("#display-mode button").forEach((button) => {{
      button.addEventListener("click", () => setDisplayMode(button.dataset.display));
    }});

    setDisplayMode(window.localStorage.getItem("jarvis-display-mode") || "full");

    Promise.all([
      refreshDashboard(),
      refreshStatus(),
      refreshApprovals(),
      refreshActivity(),
      refreshTutoringSummaries()
    ]).catch((error) => {{
      document.getElementById("plan-output").textContent = error.message;
    }});
  </script>
</body>
</html>
"""


def create_handler(runtime: JarvisRuntime) -> type[BaseHTTPRequestHandler]:
    asset_root = Path.cwd() / "assets"
    voice_settings = VoiceSettingsStore(runtime.config)
    location_settings = LocationSettingsStore(runtime.config)

    class JarvisHandler(BaseHTTPRequestHandler):
        def do_HEAD(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                return
            if parsed.path.startswith("/catalyst/view/"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                return
            if parsed.path == "/agents/hierarchy":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                return
            if parsed.path.startswith("/assets/"):
                candidate = (asset_root / parsed.path.removeprefix("/assets/")).resolve()
                try:
                    candidate.relative_to(asset_root.resolve())
                except ValueError:
                    self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
                    return
                if not candidate.exists() or not candidate.is_file():
                    self.send_error(HTTPStatus.NOT_FOUND, "Not found")
                    return
                content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(candidate.stat().st_size))
                self.end_headers()
                return
            if parsed.path.startswith("/accounts/") and parsed.path.endswith("/connect"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                return
            if parsed.path == "/google/connect":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                return
            if parsed.path.startswith("/api/"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_html(render_voice_shell(runtime))
                return
            if parsed.path.startswith("/catalyst/view/"):
                page = parsed.path.removeprefix("/catalyst/view/").strip("/") or "home"
                self._send_html(render_catalyst_workspace_page(runtime, page))
                return
            if parsed.path == "/agents/hierarchy":
                self._send_html(render_agent_hierarchy_page(runtime))
                return
            if parsed.path.startswith("/accounts/") and parsed.path.endswith("/connect"):
                account_id = parsed.path.split("/")[2]
                connect = runtime.google_connect_url(account_id, self._base_url())
                if not connect.get("ok"):
                    self._send_html(self._callback_page("Account connection unavailable", str(connect.get("detail", "Unable to start provider login.")), success=False))
                    return
                self._redirect(str(connect["authorization_url"]))
                return
            if parsed.path == "/google/connect":
                self._send_html(self._callback_page("Account required", "Select a specific account in Settings first. JARVIS now keeps personal accounts separated by user.", success=False))
                return
            if parsed.path == "/google/callback":
                params = parse_qs(parsed.query)
                code = params.get("code", [""])[0]
                state = params.get("state", [""])[0]
                result = runtime.google_handle_callback(self._base_url(), code, state)
                self._send_html(
                    self._callback_page(
                        "Google connected" if result.get("ok") else "Google connection failed",
                        str(result.get("detail", "Unknown Google callback state.")),
                        success=bool(result.get("ok")),
                    )
                )
                return
            if parsed.path.startswith("/assets/"):
                candidate = (asset_root / parsed.path.removeprefix("/assets/")).resolve()
                try:
                    candidate.relative_to(asset_root.resolve())
                except ValueError:
                    self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
                    return
                if not candidate.exists() or not candidate.is_file():
                    self.send_error(HTTPStatus.NOT_FOUND, "Not found")
                    return
                content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
                self._send_bytes(candidate.read_bytes(), content_type=content_type)
                return
            if parsed.path == "/api/summary":
                self._send_json(
                    {
                        "household": runtime.household.household_name,
                        "location": runtime.household.location_label,
                        "users": [u.display_name for u in runtime.household.users.values()],
                        "modes": runtime.household.modes,
                    }
                )
                return
            if parsed.path == "/api/dashboard":
                self._send_json(runtime.dashboard_snapshot())
                return
            if parsed.path == "/api/agents":
                self._send_json(runtime.background_agent_status())
                return
            if parsed.path == "/api/agent-registry":
                self._send_json(runtime.agent_registry_snapshot())
                return
            if parsed.path == "/api/memory-curator":
                self._send_json(runtime.memory_curator_snapshot())
                return
            if parsed.path == "/api/catalyst-overview":
                self._send_json(runtime.catalyst_overview())
                return
            if parsed.path == "/api/accounts":
                self._send_json(runtime.account_registry_snapshot())
                return
            if parsed.path == "/api/design-review-state":
                self._send_json(runtime.design_review_state())
                return
            if parsed.path == "/api/google/status":
                self._send_json(runtime.google_workspace_status())
                return
            if parsed.path == "/api/google/summary":
                self._send_json(runtime.google_workspace_summary())
                return
            if parsed.path.startswith("/api/google/account/"):
                account_id = parsed.path.rsplit("/", 1)[-1]
                self._send_json(runtime.google_account_snapshot(account_id))
                return
            if parsed.path == "/api/explainability":
                self._send_json(runtime.explainability_snapshot())
                return
            if parsed.path == "/api/approval-history":
                self._send_json(runtime.approval_history())
                return
            if parsed.path == "/api/mode":
                self._send_json(runtime.active_mode())
                return
            if parsed.path == "/api/message-drafts":
                self._send_json(runtime.list_message_drafts())
                return
            if parsed.path == "/api/voice-notes":
                self._send_json(runtime.list_voice_note_tasks())
                return
            if parsed.path == "/api/anomalies":
                self._send_json(runtime.anomaly_watch())
                return
            if parsed.path == "/api/security-incidents":
                self._send_json(runtime.list_security_incidents())
                return
            if parsed.path == "/api/overnight-review":
                self._send_json(runtime.overnight_review())
                return
            if parsed.path == "/api/home-overview":
                self._send_json(runtime.home_overview())
                return
            if parsed.path == "/api/leak-monitor":
                self._send_json(runtime.leak_monitor())
                return
            if parsed.path == "/api/cold-storage-monitor":
                self._send_json(runtime.cold_storage_monitor())
                return
            if parsed.path == "/api/outage-readiness":
                self._send_json(runtime.outage_readiness())
                return
            if parsed.path == "/api/perception-overview":
                self._send_json(runtime.perception_overview())
                return
            if parsed.path == "/api/privacy-state":
                self._send_json(runtime.privacy_state())
                return
            if parsed.path == "/api/memory-overview":
                viewer = parse_qs(parsed.query).get("viewer", ["Chris"])[0]
                self._send_json(runtime.memory_overview(viewer))
                return
            if parsed.path == "/api/memory-review":
                params = parse_qs(parsed.query)
                self._send_json(
                    runtime.review_memory(
                        params.get("viewer", ["Chris"])[0],
                        memory_type=params.get("type", [""])[0],
                        owner=params.get("owner", [""])[0],
                        project=params.get("project", [""])[0],
                    )
                )
                return
            if parsed.path == "/api/memory-proposals":
                status = parse_qs(parsed.query).get("status", [""])[0]
                self._send_json(runtime.memory_proposals(status=status))
                return
            if parsed.path == "/api/printer-status":
                self._send_json(runtime.printer_status())
                return
            if parsed.path == "/api/workshop-inspections":
                self._send_json(runtime.list_workshop_inspections())
                return
            if parsed.path == "/api/cad-packages":
                self._send_json(runtime.list_cad_packages())
                return
            if parsed.path == "/api/print-preps":
                self._send_json(runtime.list_print_preps())
                return
            if parsed.path == "/api/vendor-preps":
                self._send_json(runtime.list_vendor_preps())
                return
            if parsed.path == "/api/child-boundaries":
                actor = parse_qs(parsed.query).get("actor", [""])[0]
                self._send_json(runtime.child_boundaries(actor_name=actor or None))
                return
            if parsed.path == "/api/tutoring-summaries":
                params = parse_qs(parsed.query)
                viewer = params.get("viewer", ["Rebekah"])[0]
                child = params.get("child", [""])[0]
                limit = int(params.get("limit", ["10"])[0])
                self._send_json(runtime.tutoring_summaries(viewer, child_name=child, limit=limit))
                return
            if parsed.path == "/api/device-boundaries":
                params = parse_qs(parsed.query)
                child = params.get("child", [""])[0]
                limit = int(params.get("limit", ["10"])[0])
                self._send_json(runtime.list_device_boundaries(child_name=child, limit=limit))
                return
            if parsed.path == "/api/status":
                self._send_json(runtime.status())
                return
            if parsed.path == "/api/approvals":
                self._send_json(runtime.list_pending_approvals())
                return
            if parsed.path == "/api/activity":
                self._send_json(runtime.recent_activity())
                return
            if parsed.path == "/api/briefing":
                actor = parse_qs(parsed.query).get("actor", ["Chris"])[0]
                self._send_json({"actor": actor, "briefing": runtime.morning_brief(actor)})
                return
            if parsed.path == "/api/voice-settings":
                self._send_json(voice_settings.describe())
                return
            if parsed.path == "/api/voice-options":
                self._send_json(voice_settings.voice_options())
                return
            if parsed.path == "/api/location-settings":
                self._send_json(location_settings.describe())
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/tts":
                payload = self._read_json()
                text = str(payload.get("text", "")).strip()
                if not text:
                    self.send_error(HTTPStatus.BAD_REQUEST, "Text is required")
                    return
                try:
                    audio = generate_tts_audio(
                        runtime.config,
                        text,
                        voice_settings=voice_settings.load().to_dict(),
                    )
                except RuntimeError as exc:
                    self.send_error(HTTPStatus.BAD_GATEWAY, str(exc))
                    return
                self._send_bytes(
                    audio.data,
                    content_type=audio.content_type,
                    extra_headers={"X-Jarvis-Tts-Provider": audio.provider},
                )
                return
            if parsed.path == "/api/voice-settings":
                payload = self._read_json()
                settings = voice_settings.save(payload)
                self._send_json(
                    {
                        "message": "Voice settings updated.",
                        "settings": voice_settings.describe(),
                        "options": voice_settings.voice_options(),
                        "saved": settings.to_dict(),
                    }
                )
                return
            if parsed.path == "/api/location-settings":
                payload = self._read_json()
                action = str(payload.get("action", "")).strip()
                try:
                    if action == "add_location":
                        state = location_settings.add_location(payload)
                    elif action == "set_preferred":
                        state = location_settings.set_preferred_location(str(payload.get("location_id", "")).strip())
                    elif action == "save_device_location":
                        state = location_settings.save_device_location(payload)
                    else:
                        state = location_settings.save(payload)
                except ValueError as exc:
                    self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
                    return
                self._send_json({"ok": True, "state": location_settings.describe(), "saved": state})
                return
            if parsed.path == "/api/google/client-secret":
                payload = self._read_json()
                self._send_json(runtime.google_save_client_secret(str(payload.get("client_secret_json", ""))))
                return
            if parsed.path == "/api/accounts":
                payload = self._read_json()
                self._send_json(runtime.save_personal_account(payload))
                return
            if parsed.path == "/api/design-review-state":
                payload = self._read_json()
                self._send_json(runtime.save_design_review_state(payload))
                return
            if parsed.path == "/api/mode-transition":
                payload = self._read_json()
                self._send_json(
                    runtime.transition_mode(
                        str(payload.get("actor", "Chris")),
                        str(payload.get("mode", "ambient-associate")),
                        str(payload.get("reason", "Manual mode update from JARVIS shell.")),
                    )
                )
                return
            if parsed.path == "/api/google/disconnect":
                self._send_json(runtime.google_disconnect())
                return
            if parsed.path.startswith("/api/accounts/") and parsed.path.endswith("/disconnect"):
                account_id = parsed.path.split("/")[3]
                self._send_json(runtime.google_disconnect_account(account_id))
                return
            if parsed.path in {"/api/plan", "/api/respond", "/api/mode-brief", "/api/family-plan", "/api/departure-plan", "/api/rebekah-center", "/api/troop-plan", "/api/grocery-support", "/api/meal-plan", "/api/vehicle-plan", "/api/weather-contingency", "/api/message-draft", "/api/parent-message", "/api/voice-note", "/api/security-event", "/api/safety-alert", "/api/weather-alert", "/api/child-arrival", "/api/unlock-policy", "/api/tutor", "/api/device-boundary", "/api/workshop-plan", "/api/material-recommendation", "/api/cad-package", "/api/print-prep", "/api/safety-check", "/api/inspect-part", "/api/vendor-prep", "/api/executive-task", "/api/devotional-pause", "/api/family-devotional", "/api/chronicle-capture", "/api/room-scene", "/api/climate-control", "/api/access-control", "/api/garage-check", "/api/energy-window", "/api/mic-ingress", "/api/presence-update", "/api/phone-presence", "/api/camera-event", "/api/package-rule", "/api/object-recognition", "/api/environmental-anomaly", "/api/privacy-update", "/api/memory-remember", "/api/memory-forget", "/api/memory-approve", "/api/catalyst-signal", "/api/catalyst-email-triage", "/api/catalyst-meeting-prep", "/api/catalyst-meeting-extract", "/api/catalyst-briefing", "/api/catalyst-draft", "/api/catalyst-project-brief", "/api/catalyst-implementation-plan", "/api/catalyst-proactive"}:
                payload = self._read_json()
                actor = payload.get("actor", "Chris")
                room = payload.get("room", "office")
                request_text = payload.get("request", "")
                if parsed.path == "/api/plan":
                    plan = runtime.plan_request(actor, room, request_text)
                    self._send_json(
                        {
                            "request_id": plan.request_id,
                            "actor": plan.actor,
                            "room": plan.room,
                            "mode": plan.mode,
                            "module": plan.module,
                            "model": plan.model,
                            "allowed": plan.allowed,
                            "approval_required": plan.needs_approval,
                            "second_factor_required": plan.second_factor_required,
                            "action_class": plan.action_class.name,
                            "rationale": plan.rationale,
                        }
                    )
                    return
                if parsed.path == "/api/mode-brief":
                    self._send_json(runtime.family_mode_brief(payload.get("mode", "")))
                    return
                if parsed.path == "/api/family-plan":
                    self._send_json({"actor": actor, "output_text": runtime.family_plan(actor, request_text)})
                    return
                if parsed.path == "/api/departure-plan":
                    self._send_json(runtime.departure_plan(actor, payload.get("context", "")))
                    return
                if parsed.path == "/api/rebekah-center":
                    self._send_json({"actor": "Rebekah", "output_text": runtime.rebekah_command_center(request_text)})
                    return
                if parsed.path == "/api/troop-plan":
                    self._send_json({"actor": actor, "output_text": runtime.troop_plan(actor, request_text)})
                    return
                if parsed.path == "/api/grocery-support":
                    self._send_json({"actor": actor, "output_text": runtime.grocery_support(actor, request_text)})
                    return
                if parsed.path == "/api/meal-plan":
                    self._send_json(runtime.meal_plan(actor, request_text))
                    return
                if parsed.path == "/api/vehicle-plan":
                    self._send_json(runtime.vehicle_plan(actor, request_text))
                    return
                if parsed.path == "/api/weather-contingency":
                    self._send_json(runtime.weather_contingency(actor, request_text))
                    return
                if parsed.path == "/api/message-draft":
                    self._send_json(
                        runtime.draft_message(
                            actor,
                            payload["audience"],
                            payload["purpose"],
                            payload["context"],
                            payload.get("tone", "warm"),
                        )
                    )
                    return
                if parsed.path == "/api/parent-message":
                    self._send_json(
                        runtime.stage_parent_message(
                            actor,
                            payload["audience"],
                            payload["purpose"],
                            payload["context"],
                            payload.get("tone", "warm"),
                        )
                    )
                    return
                if parsed.path == "/api/voice-note":
                    self._send_json(
                        runtime.capture_voice_note(
                            actor,
                            payload.get("source", "van"),
                            payload.get("note", ""),
                        )
                    )
                    return
                if parsed.path == "/api/room-scene":
                    self._send_json(
                        runtime.room_scene(
                            actor,
                            payload.get("room", ""),
                            payload.get("scene", ""),
                            intent=payload.get("intent", ""),
                        )
                    )
                    return
                if parsed.path == "/api/climate-control":
                    self._send_json(
                        runtime.climate_control(
                            actor,
                            payload.get("zone", ""),
                            payload.get("mode", "heat_cool"),
                            target_temperature=payload.get("target_temp"),
                            context=payload.get("context", ""),
                        )
                    )
                    return
                if parsed.path == "/api/access-control":
                    self._send_json(
                        runtime.access_control(
                            actor,
                            payload.get("target", ""),
                            payload.get("state", ""),
                        )
                    )
                    return
                if parsed.path == "/api/garage-check":
                    self._send_json(
                        runtime.garage_safe_close(
                            actor,
                            payload.get("target", ""),
                        )
                    )
                    return
                if parsed.path == "/api/energy-window":
                    self._send_json(
                        runtime.energy_window(
                            payload.get("appliance", ""),
                            request_text=payload.get("request", ""),
                        )
                    )
                    return
                if parsed.path == "/api/mic-ingress":
                    self._send_json(
                        runtime.microphone_ingress(
                            payload.get("microphone", ""),
                            payload.get("transcript", ""),
                            wake_word_detected=payload.get("wake_word", False),
                            actor_hint=payload.get("actor_hint", ""),
                        )
                    )
                    return
                if parsed.path == "/api/presence-update":
                    self._send_json(
                        runtime.presence_update(
                            payload.get("sensor", ""),
                            payload.get("room", ""),
                            bool(payload.get("occupied", False)),
                            detail=payload.get("detail", ""),
                        )
                    )
                    return
                if parsed.path == "/api/phone-presence":
                    self._send_json(
                        runtime.phone_presence_update(
                            actor,
                            payload.get("device", ""),
                            payload.get("state", ""),
                            zone=payload.get("zone", ""),
                            detail=payload.get("detail", ""),
                        )
                    )
                    return
                if parsed.path == "/api/camera-event":
                    self._send_json(
                        runtime.camera_event(
                            payload.get("camera", ""),
                            payload.get("event_type", ""),
                            payload.get("detail", ""),
                            detected_object=payload.get("object", ""),
                            confidence=payload.get("confidence", "medium"),
                        )
                    )
                    return
                if parsed.path == "/api/package-rule":
                    self._send_json(
                        runtime.package_rule(
                            payload.get("zone", ""),
                            payload.get("preferred_drop", ""),
                            bool(payload.get("rain_sensitive", False)),
                            note=payload.get("note", ""),
                        )
                    )
                    return
                if parsed.path == "/api/object-recognition":
                    self._send_json(
                        runtime.object_recognition(
                            payload.get("source", ""),
                            payload.get("room", ""),
                            payload.get("object", ""),
                            detail=payload.get("detail", ""),
                            confidence=payload.get("confidence", "medium"),
                        )
                    )
                    return
                if parsed.path == "/api/environmental-anomaly":
                    self._send_json(
                        runtime.environmental_anomaly(
                            payload.get("category", ""),
                            payload.get("source", ""),
                            payload.get("reading", ""),
                            payload.get("baseline", ""),
                            severity=payload.get("severity", "watch"),
                            detail=payload.get("detail", ""),
                        )
                    )
                    return
                if parsed.path == "/api/privacy-update":
                    self._send_json(
                        runtime.update_privacy_state(
                            payload.get("kind", ""),
                            payload.get("target", ""),
                            enabled=payload.get("enabled"),
                            muted=payload.get("muted"),
                        )
                    )
                    return
                if parsed.path == "/api/memory-remember":
                    tags = [item.strip() for item in str(payload.get("tags", "")).split(",") if item.strip()]
                    self._send_json(
                        runtime.remember(
                            actor,
                            payload.get("type", "household"),
                            payload.get("scope", "household"),
                            payload.get("summary", ""),
                            payload.get("detail", ""),
                            owner=payload.get("owner", ""),
                            project=payload.get("project", ""),
                            tags=tags,
                            sensitivity=payload.get("sensitivity", "normal"),
                        )
                    )
                    return
                if parsed.path == "/api/memory-forget":
                    self._send_json(
                        runtime.forget_memory(
                            payload.get("viewer", "Chris"),
                            payload.get("entry_id", ""),
                        )
                    )
                    return
                if parsed.path == "/api/memory-approve":
                    self._send_json(
                        runtime.resolve_memory_proposal(
                            payload.get("proposal_id", ""),
                            payload.get("decision", "approved"),
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-signal":
                    tags = [item.strip() for item in str(payload.get("tags", "")).split(",") if item.strip()]
                    self._send_json(
                        runtime.catalyst_capture_signal(
                            actor,
                            payload.get("source", "manual"),
                            payload.get("title", ""),
                            payload.get("content", ""),
                            sender=payload.get("sender", ""),
                            tags=tags,
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-email-triage":
                    self._send_json(
                        runtime.catalyst_email_triage(
                            actor,
                            payload.get("subject", ""),
                            payload.get("body", ""),
                            payload.get("sender", ""),
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-meeting-prep":
                    self._send_json(
                        runtime.catalyst_meeting_prep(
                            actor,
                            payload.get("meeting_title", ""),
                            payload.get("open_commitments", []),
                            payload.get("recent_signals", []),
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-meeting-extract":
                    self._send_json(
                        runtime.catalyst_meeting_extraction(
                            actor,
                            payload.get("transcript", ""),
                            payload.get("context", ""),
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-briefing":
                    self._send_json(
                        runtime.catalyst_briefing(
                            actor,
                            payload.get("user_context", ""),
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-draft":
                    self._send_json(
                        runtime.catalyst_draft(
                            actor,
                            payload.get("intent", ""),
                            payload.get("context", ""),
                            payload.get("recipient", ""),
                            payload.get("tone", "professional"),
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-project-brief":
                    self._send_json(
                        runtime.catalyst_project_brief(
                            actor,
                            payload.get("project_name", ""),
                            payload.get("problem", ""),
                            payload.get("desired_outcome", ""),
                            payload.get("constraints", ""),
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-implementation-plan":
                    self._send_json(
                        runtime.catalyst_implementation_plan(
                            actor,
                            payload.get("project_name", ""),
                            payload.get("brief", ""),
                            payload.get("constraints", ""),
                        )
                    )
                    return
                if parsed.path == "/api/catalyst-proactive":
                    self._send_json(
                        runtime.catalyst_proactive_surfacing(
                            actor,
                            payload.get("horizon", "today"),
                            payload.get("context", ""),
                        )
                    )
                    return
                if parsed.path == "/api/security-event":
                    self._send_json(
                        runtime.package_or_motion_monitor(
                            actor,
                            payload.get("category", "motion"),
                            payload.get("location", ""),
                            payload.get("detail", ""),
                            severity=payload.get("severity", "watch"),
                        )
                    )
                    return
                if parsed.path == "/api/safety-alert":
                    self._send_json(
                        runtime.safety_escalation(
                            actor,
                            payload.get("hazard", "smoke"),
                            payload.get("source", ""),
                            payload.get("detail", ""),
                            severity=payload.get("severity", "critical"),
                        )
                    )
                    return
                if parsed.path == "/api/weather-alert":
                    self._send_json(
                        runtime.weather_advisory(
                            actor,
                            payload.get("context", ""),
                        )
                    )
                    return
                if parsed.path == "/api/child-arrival":
                    self._send_json(
                        runtime.child_arrival(
                            actor,
                            payload.get("location", "front door"),
                            payload.get("detail", ""),
                        )
                    )
                    return
                if parsed.path == "/api/unlock-policy":
                    self._send_json(
                        runtime.unlock_assessment(
                            actor,
                            payload.get("target", "front door"),
                            requested_by_voice=payload.get("requested_by_voice", True),
                            second_factor_present=payload.get("second_factor_present", False),
                        )
                    )
                    return
                if parsed.path == "/api/devotional-pause":
                    self._send_json(
                        {
                            "actor": actor,
                            "output_text": runtime.devotional_pause(
                                actor,
                                payload.get("theme", ""),
                                payload.get("mode", "scripture"),
                            ),
                        }
                    )
                    return
                if parsed.path == "/api/family-devotional":
                    self._send_json(
                        {
                            "actor": actor,
                            "output_text": runtime.family_devotional_prep(
                                actor,
                                payload.get("theme", ""),
                                payload.get("context", ""),
                            ),
                        }
                    )
                    return
                if parsed.path == "/api/chronicle-capture":
                    self._send_json(
                        runtime.chronicle_capture(
                            actor,
                            payload.get("theme", ""),
                            payload.get("note", ""),
                        )
                    )
                    return
                if parsed.path == "/api/tutor":
                    self._send_json(
                        runtime.tutor(
                            actor,
                            request_text,
                            subject=payload.get("subject", ""),
                        )
                    )
                    return
                if parsed.path == "/api/device-boundary":
                    self._send_json(
                        runtime.device_boundary_plan(
                            actor,
                            window_label=payload.get("window", ""),
                        )
                    )
                    return
                if parsed.path == "/api/workshop-plan":
                    self._send_json({"actor": actor, "output_text": runtime.workshop_plan(actor, request_text)})
                    return
                if parsed.path == "/api/material-recommendation":
                    self._send_json(
                        runtime.material_recommendation(
                            actor,
                            payload["part"],
                            payload["use_case"],
                            payload.get("requirements", ""),
                        )
                    )
                    return
                if parsed.path == "/api/cad-package":
                    self._send_json(
                        runtime.cad_package(
                            actor,
                            payload["part"],
                            payload.get("dimensions", ""),
                            payload.get("constraints", ""),
                        )
                    )
                    return
                if parsed.path == "/api/print-prep":
                    self._send_json(
                        runtime.print_prep(
                            actor,
                            payload["part"],
                            payload["printer"],
                            payload["material"],
                            payload.get("profile", "functional-prototype"),
                            payload.get("notes", ""),
                        )
                    )
                    return
                if parsed.path == "/api/safety-check":
                    self._send_json(
                        runtime.safety_check(
                            actor,
                            payload["operation"],
                            payload.get("context", ""),
                        )
                    )
                    return
                if parsed.path == "/api/inspect-part":
                    self._send_json(
                        runtime.inspect_part(
                            actor,
                            payload["part"],
                            request_text or "Inspect this part and recommend a prototype path.",
                            payload.get("observations", ""),
                            payload.get("goals", ""),
                            image_path=payload.get("image_path", ""),
                        )
                    )
                    return
                if parsed.path == "/api/vendor-prep":
                    self._send_json(
                        runtime.vendor_prep(
                            actor,
                            payload["part"],
                            payload["vendor"],
                            payload["process"],
                            payload["material"],
                            payload.get("notes", ""),
                        )
                    )
                    return
                if parsed.path == "/api/executive-task":
                    task = payload.get("task", "")
                    if task == "decision-framework":
                        self._send_json(
                            {
                                "actor": actor,
                                "task": task,
                                "output_text": runtime.decision_framework(actor, payload.get("primary", "")),
                            }
                        )
                        return
                    if task == "ironclad-editor":
                        self._send_json(
                            {
                                "actor": actor,
                                "task": task,
                                "output_text": runtime.iron_clad_editor(actor, payload.get("primary", "")),
                            }
                        )
                        return
                    if task == "venture-brief":
                        self._send_json(
                            {
                                "actor": actor,
                                "task": task,
                                "output_text": runtime.venture_brief(
                                    actor,
                                    payload.get("topic", "venture monitoring"),
                                    payload.get("secondary", "") or payload.get("primary", ""),
                                ),
                            }
                        )
                        return
                    self.send_error(HTTPStatus.BAD_REQUEST, "Unknown executive task")
                    return
                result = runtime.respond(actor, room, request_text)
                self._send_json({"provider": result.provider, "model": result.model, "output_text": result.output_text})
                return

            if parsed.path.startswith("/api/approvals/"):
                request_id = parsed.path.rsplit("/", 1)[-1]
                payload = self._read_json()
                updated = runtime.update_approval(request_id, payload.get("status", "pending"))
                if updated is None:
                    self.send_error(HTTPStatus.NOT_FOUND, "Approval request not found")
                    return
                self._send_json(updated)
                return

            if parsed.path.startswith("/api/message-drafts/"):
                draft_id = parsed.path.rsplit("/", 1)[-1]
                payload = self._read_json()
                updated = runtime.update_message_draft(draft_id, payload.get("status", "staged"))
                if updated is None:
                    self.send_error(HTTPStatus.NOT_FOUND, "Message draft not found")
                    return
                self._send_json(updated)
                return

            if parsed.path.startswith("/api/vendor-preps/"):
                prep_id = parsed.path.rsplit("/", 1)[-1]
                payload = self._read_json()
                updated = runtime.update_vendor_prep_status(prep_id, payload.get("status", "staged"))
                if updated is None:
                    self.send_error(HTTPStatus.NOT_FOUND, "Vendor prep not found")
                    return
                self._send_json(updated)
                return

            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return None

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            return json.loads(body)

        def _send_json(self, payload: object, status: int = 200) -> None:
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(data)

        def _send_html(self, html: str) -> None:
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(data)

        def _send_bytes(
            self,
            payload: bytes,
            content_type: str,
            status: int = 200,
            extra_headers: dict[str, str] | None = None,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            for name, value in (extra_headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(payload)

        def _redirect(self, location: str) -> None:
            self.send_response(302)
            self.send_header("Location", location)
            self.end_headers()

        def _base_url(self) -> str:
            host = self.headers.get("Host", "127.0.0.1:8787")
            return f"http://{host}"

        def _callback_page(self, title: str, detail: str, *, success: bool) -> str:
            safe_title = escape(title)
            safe_detail = escape(detail)
            accent = "#6cffaf" if success else "#ffcc70"
            return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #07111a;
      color: #eef7ff;
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
    }}
    .card {{
      width: min(560px, 92vw);
      padding: 28px;
      border: 1px solid rgba(111, 229, 255, 0.22);
      background: rgba(8, 18, 30, 0.92);
      box-shadow: 0 24px 72px rgba(0, 0, 0, 0.38);
      border-radius: 16px;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 28px;
      color: {accent};
    }}
    p {{
      margin: 0;
      line-height: 1.55;
      color: #bfd2e4;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{safe_title}</h1>
    <p>{safe_detail}</p>
  </div>
</body>
</html>"""

    return JarvisHandler


def serve(runtime: JarvisRuntime, host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), create_handler(runtime))
    print(f"JARVIS dashboard running on http://{host}:{port}")
    server.serve_forever()
