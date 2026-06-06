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
      --jarvis-bg: #07111f;
      --jarvis-panel: rgba(10, 22, 36, 0.88);
      --jarvis-panel-strong: rgba(9, 19, 31, 0.96);
      --jarvis-panel-soft: rgba(12, 26, 42, 0.74);
      --jarvis-line: rgba(111, 229, 255, 0.16);
      --jarvis-line-strong: rgba(111, 229, 255, 0.3);
      --jarvis-ink: #e7f4ff;
      --jarvis-muted: #86b2d3;
      --jarvis-accent: #74d8ff;
      --jarvis-accent-soft: rgba(116, 216, 255, 0.14);
      --jarvis-accent-strong: #90e6ff;
      --jarvis-success: #87efb5;
      --jarvis-warn: #ffd48a;
      --jarvis-danger: #ff9c9c;
      --jarvis-shadow: 0 18px 42px rgba(0,0,0,0.28);
      --jarvis-radius: 10px;
      --jarvis-chip-radius: 999px;
      --jarvis-space-1: 6px;
      --jarvis-space-2: 10px;
      --jarvis-space-3: 14px;
      --jarvis-space-4: 18px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top, rgba(42, 170, 255, 0.12), transparent 40%),
        linear-gradient(180deg, #050b16 0%, var(--jarvis-bg) 38%, #081624 100%);
      color: var(--jarvis-ink);
    }}
    .shell {{
      min-height: 100vh;
      padding: 20px;
      display: grid;
      gap: 18px;
    }}
    .hero, .panel {{
      border: 1px solid var(--jarvis-line);
      background: var(--jarvis-panel);
      box-shadow: var(--jarvis-shadow);
    }}
    .hero {{
      padding: 18px 20px;
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 18px;
    }}
    .eyebrow {{
      color: var(--jarvis-accent);
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
      color: var(--jarvis-muted);
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
      border: 1px solid var(--jarvis-line);
      color: var(--jarvis-muted);
      text-decoration: none;
      font-size: 13px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      background: rgba(7, 16, 27, 0.72);
      border-radius: 8px;
    }}
    .nav-pill.active {{
      background: linear-gradient(135deg, rgba(111, 229, 255, 0.18), rgba(76, 160, 255, 0.18));
      color: var(--jarvis-accent);
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
      border: 1px solid var(--jarvis-line);
      background: var(--jarvis-panel-strong);
      padding: 16px;
      border-radius: 8px;
    }}
    .card h2 {{
      margin: 0 0 10px;
      font-size: 13px;
      color: var(--jarvis-accent);
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }}
    .card p, .card li, .card div {{
      color: var(--jarvis-ink);
      font-size: 14px;
      line-height: 1.55;
    }}
    .card ul {{
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 8px;
    }}
    .muted {{ color: var(--jarvis-muted); }}
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
    .field {{
      display: grid;
      gap: 8px;
    }}
    .field-label {{
      color: var(--jarvis-muted);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .stack-sm {{
      display: grid;
      gap: 8px;
    }}
    .cluster {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }}
    .btn {{
      appearance: none;
      border-radius: 999px;
      padding: 10px 14px;
      border: 1px solid var(--jarvis-line);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: background 160ms ease, border-color 160ms ease, color 160ms ease, transform 160ms ease;
    }}
    .btn:hover {{
      transform: translateY(-1px);
    }}
    .btn-primary {{
      background: linear-gradient(135deg, rgba(116, 216, 255, 0.26), rgba(76, 160, 255, 0.18));
      border-color: var(--jarvis-line-strong);
      color: var(--jarvis-accent-strong);
    }}
    .btn-secondary {{
      background: rgba(9, 19, 31, 0.96);
      color: var(--jarvis-ink);
    }}
    .btn-subtle {{
      background: transparent;
      color: var(--jarvis-muted);
    }}
    .btn-danger {{
      border-color: rgba(255, 156, 156, 0.28);
      color: var(--jarvis-danger);
      background: rgba(78, 18, 18, 0.18);
    }}
    .btn[disabled] {{
      opacity: 0.45;
      cursor: not-allowed;
      transform: none;
    }}
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .chip {{
      position: relative;
      display: inline-flex;
      align-items: center;
    }}
    .chip input {{
      position: absolute;
      opacity: 0;
      pointer-events: none;
    }}
    .chip span {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 36px;
      padding: 0 14px;
      border-radius: var(--jarvis-chip-radius);
      border: 1px solid var(--jarvis-line);
      background: var(--jarvis-panel-soft);
      color: var(--jarvis-muted);
      transition: border-color 140ms ease, background 140ms ease, color 140ms ease, box-shadow 140ms ease;
    }}
    .chip input:checked + span {{
      color: var(--jarvis-accent-strong);
      border-color: var(--jarvis-line-strong);
      background: linear-gradient(135deg, rgba(116, 216, 255, 0.22), rgba(76, 160, 255, 0.14));
      box-shadow: 0 0 0 1px rgba(116, 216, 255, 0.08) inset;
    }}
    .chip span::before {{
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: rgba(116, 216, 255, 0.18);
    }}
    .chip input:checked + span::before {{
      background: var(--jarvis-accent);
      box-shadow: 0 0 12px rgba(116, 216, 255, 0.48);
    }}
    input, select, textarea {{
      width: 100%;
      background: rgba(7, 16, 27, 0.72);
      color: var(--jarvis-ink);
      border: 1px solid var(--jarvis-line);
      border-radius: 8px;
      padding: 10px 12px;
    }}
    textarea {{
      resize: vertical;
    }}
    .status-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid var(--jarvis-line);
      color: var(--jarvis-muted);
      background: rgba(7, 16, 27, 0.72);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .status-pill.live {{
      color: var(--jarvis-success);
      border-color: rgba(135, 239, 181, 0.28);
      background: rgba(10, 55, 33, 0.18);
    }}
    .status-pill.exported {{
      color: var(--jarvis-warn);
      border-color: rgba(255, 212, 138, 0.24);
      background: rgba(92, 68, 18, 0.16);
    }}
    .inline-actions {{
      margin-top: 10px;
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .approval-block {{
      border: 1px solid var(--jarvis-line);
      border-radius: 8px;
      background: var(--jarvis-panel-soft);
      padding: 12px;
      display: grid;
      gap: 8px;
    }}
    .dialog-backdrop {{
      position: fixed;
      inset: 0;
      background: rgba(2, 8, 15, 0.72);
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px;
      z-index: 1000;
    }}
    .dialog-backdrop.open {{
      display: flex;
    }}
    .dialog {{
      width: min(560px, 100%);
      border: 1px solid var(--jarvis-line-strong);
      background: rgba(7, 16, 27, 0.98);
      border-radius: 12px;
      box-shadow: 0 30px 80px rgba(0, 0, 0, 0.42);
      padding: 18px;
      display: grid;
      gap: 14px;
    }}
    .dialog h3 {{
      margin: 0;
      color: var(--jarvis-accent-strong);
      letter-spacing: 0.05em;
      text-transform: uppercase;
      font-size: 14px;
    }}
    .dialog-copy {{
      color: var(--jarvis-ink);
      line-height: 1.6;
      white-space: pre-wrap;
    }}
    .dialog-meta {{
      color: var(--jarvis-muted);
      font-size: 13px;
      line-height: 1.5;
    }}
    .dialog-actions {{
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      flex-wrap: wrap;
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
  <div class="dialog-backdrop" id="jarvis-dialog-backdrop" aria-hidden="true">
    <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="jarvis-dialog-title">
      <h3 id="jarvis-dialog-title">Review Action</h3>
      <div class="dialog-copy" id="jarvis-dialog-copy">Action details will appear here.</div>
      <div class="dialog-meta" id="jarvis-dialog-meta"></div>
      <div class="dialog-actions">
        <button class="btn btn-subtle" id="jarvis-dialog-cancel" type="button">Cancel</button>
        <button class="btn btn-primary" id="jarvis-dialog-confirm" type="button">Confirm</button>
      </div>
    </div>
  </div>
  <script>
    window.JarvisUI = (() => {{
      const backdrop = document.getElementById("jarvis-dialog-backdrop");
      const title = document.getElementById("jarvis-dialog-title");
      const copy = document.getElementById("jarvis-dialog-copy");
      const meta = document.getElementById("jarvis-dialog-meta");
      const confirm = document.getElementById("jarvis-dialog-confirm");
      const cancel = document.getElementById("jarvis-dialog-cancel");
      let onConfirm = null;

      function closeDialog() {{
        backdrop.classList.remove("open");
        backdrop.setAttribute("aria-hidden", "true");
        onConfirm = null;
      }}

      cancel.addEventListener("click", closeDialog);
      backdrop.addEventListener("click", (event) => {{
        if (event.target === backdrop) closeDialog();
      }});
      confirm.addEventListener("click", async () => {{
        if (!onConfirm) {{
          closeDialog();
          return;
        }}
        confirm.disabled = true;
        try {{
          await onConfirm();
          closeDialog();
        }} finally {{
          confirm.disabled = false;
        }}
      }});

      async function postJson(url, payload) {{
        const response = await fetch(url, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload),
        }});
        if (!response.ok) throw new Error(await response.text());
        return response.json();
      }}

      function openApprovalDialog(config) {{
        title.textContent = config.title || "Review Action";
        copy.textContent = config.copy || "";
        meta.textContent = config.meta || "";
        confirm.textContent = config.confirmLabel || "Confirm";
        confirm.className = `btn ${{config.confirmClass || "btn-primary"}}`;
        onConfirm = config.onConfirm || null;
        backdrop.classList.add("open");
        backdrop.setAttribute("aria-hidden", "false");
      }}

      function escapeHtml(value) {{
        return String(value ?? "")
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;")
          .replaceAll('"', "&quot;")
          .replaceAll("'", "&#39;");
      }}

      return {{ closeDialog, openApprovalDialog, postJson, escapeHtml }};
    }})();
  </script>
</body>
</html>"""


def render_catalyst_workspace_page(runtime: JarvisRuntime, page: str) -> str:
    page = (page or "home").strip().lower()
    mockup = CATALYST_MOCKUP_PAGES.get(page)
    if mockup and mockup.exists() and page not in {"home", "calendar"}:
        return _inject_catalyst_theme(mockup.read_text(encoding="utf-8"))

    overview = runtime.catalyst_overview()
    google = runtime.google_workspace_summary()
    family_calendar = runtime.family_calendar_summary()
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
    family_upcoming_events = [
        (family_calendar.get("calendar", {}), item)
        for item in family_calendar.get("events", [])
    ]
    latest_runs = overview.get("latest_runs", {})
    gmail_diagnostics = [
        (entry.get("account", {}), str(entry.get("gmail_error", "")).strip())
        for entry in google_accounts
        if str(entry.get("gmail_error", "")).strip()
    ]
    calendar_diagnostics = [
        (entry.get("account", {}), str(entry.get("calendar_error", "")).strip())
        for entry in google_accounts
        if str(entry.get("calendar_error", "")).strip()
    ]

    def _short_google_error(detail: str) -> str:
        lowered = detail.lower()
        if "gmail api has not been used" in lowered or "accessnotconfigured" in lowered:
            return "Gmail API is disabled in Google Cloud for this project."
        if "google calendar api has not been used" in lowered or "calendar-json.googleapis.com" in lowered:
            return "Google Calendar API is disabled in Google Cloud for this project."
        return detail[:240] + ("..." if len(detail) > 240 else "")

    def _merged_upcoming(limit: int = 20) -> list[tuple[dict, dict]]:
        merged = list(upcoming_events) + list(family_upcoming_events)
        merged.sort(key=lambda entry: str(entry[1].get("start", "")))
        return merged[:limit]

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
          <div class="card">
            <h2>Mail Connection Status</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(account.get("owner_display_name") or account.get("label") or "Account")}</strong><div class="muted">{escape(_short_google_error(detail))}</div></div>' for account, detail in gmail_diagnostics) or '<div class="muted">Mail connectivity looks healthy.</div>'}</div>
          </div>
          <div class="card" style="grid-column: 1 / -1;">
            <h2>Unread Mail</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(email.get("subject") or "(No subject)")}</strong><div class="muted">{escape(account.get("owner_display_name") or account.get("label") or "Account")} · {escape(email.get("from") or "Unknown sender")}</div></div>' for account, email in unread_emails) or '<div class="muted">No unread mail is loaded yet.</div>'}</div>
          </div>
        </div>"""
        return _render_catalyst_workspace_chrome("Email Workspace", "Personal inbox triage, drafts, and signal capture under the JARVIS shell.", body, page)

    if page == "home":
        total_unread = sum(int(entry.get("counts", {}).get("unread_emails", 0)) for entry in google_accounts)
        total_events = sum(int(entry.get("counts", {}).get("upcoming_events", 0)) for entry in google_accounts)
        family_event_count = int(family_calendar.get("counts", {}).get("upcoming_events", 0))
        merged_events = _merged_upcoming(limit=6)
        body = f"""
        <div class="grid">
          <div class="card">
            <h2>Connected Accounts</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(account.get("label") or account.get("owner_display_name") or "Account")}</strong><div class="muted">{escape(account.get("provider", "unknown"))} · {escape(account.get("status", "planned"))}</div></div>' for account in accounts) or '<div class="muted">No personal accounts have been saved yet.</div>'}</div>
          </div>
          <div class="card">
            <h2>Live Summary</h2>
            <ul>
              <li><strong>{escape(str(total_unread))}</strong> unread emails across connected accounts</li>
              <li><strong>{escape(str(total_events))}</strong> Google calendar events in the next 30 days</li>
              <li><strong>{escape(str(family_event_count))}</strong> family shared calendar events in the next 30 days</li>
              <li><strong>{escape(str(overview.get("counts", {}).get("signals", 0)))}</strong> captured Catalyst signals</li>
            </ul>
          </div>
          <div class="card">
            <h2>Next Events</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(event.get("summary") or "(Untitled event)")}</strong><div class="muted">{escape(account.get("owner_display_name") or account.get("label") or account.get("source") or "Calendar")} · {escape(event.get("start") or "No start time")}</div></div>' for account, event in merged_events) or '<div class="muted">No upcoming events are loaded yet.</div>'}</div>
          </div>
          <div class="card">
            <h2>Unread Mail Snapshot</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(email.get("subject") or "(No subject)")}</strong><div class="muted">{escape(account.get("owner_display_name") or account.get("label") or "Account")} · {escape(email.get("from") or "Unknown sender")}</div></div>' for account, email in unread_emails[:6]) or '<div class="muted">No unread mail is loaded yet.</div>'}</div>
          </div>
        </div>"""
        return _render_catalyst_workspace_chrome("Catalyst Workspace", "Live personal workflow state inside JARVIS, with current mail and calendar context instead of mockup data.", body, page)

    if page == "calendar":
        merged_events = _merged_upcoming(limit=20)
        body = f"""
        <div class="grid">
          <div class="card" style="grid-column: 1 / -1;">
            <h2>Upcoming Calendar</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(event.get("summary") or "(Untitled event)")}</strong><div class="muted">{escape(account.get("owner_display_name") or account.get("label") or account.get("source") or "Calendar")} · {escape(event.get("start") or "No start time")}{(" · " + escape(event.get("location"))) if event.get("location") else ""}</div></div>' for account, event in merged_events) or '<div class="muted">No upcoming calendar events are loaded yet.</div>'}</div>
          </div>
          <div class="card">
            <h2>Calendar Connection Status</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(account.get("owner_display_name") or account.get("label") or "Account")}</strong><div class="muted">{escape(_short_google_error(detail))}</div></div>' for account, detail in calendar_diagnostics) or '<div class="muted">Google Calendar connectivity looks healthy.</div>'}</div>
          </div>
          <div class="card">
            <h2>Linked Sources</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(account.get("label") or account.get("owner_display_name") or "Account")}</strong><div class="muted">{escape(account.get("provider", "unknown"))} · {escape(account.get("status", "planned"))}</div></div>' for account in accounts if account.get("provider") == "google") or '<div class="muted">No Google calendar accounts have been saved yet.</div>'}<div class="row"><strong>{escape(family_calendar.get("calendar", {}).get("label", "Family Shared Calendar"))}</strong><div class="muted">{escape(family_calendar.get("detail", "Family shared calendar feed is not configured yet."))}</div></div></div>
          </div>
        </div>"""
        return _render_catalyst_workspace_chrome("Calendar Workspace", "Live upcoming events from connected personal calendars inside the Catalyst lane.", body, page)

    if page == "meetings":
        merged_events = _merged_upcoming(limit=10)
        body = f"""
        <div class="grid">
          <div class="card">
            <h2>Upcoming Meetings</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(event.get("summary") or "(Untitled event)")}</strong><div class="muted">{escape(account.get("owner_display_name") or account.get("label") or account.get("source") or "Calendar")} · {escape(event.get("start") or "No start time")}</div></div>' for account, event in merged_events) or '<div class="muted">No upcoming meetings are loaded yet.</div>'}</div>
          </div>
          <div class="card">
            <h2>Meeting Prep</h2>
            <p>{escape(latest_runs.get("meeting_prep", {}).get("meeting_title") or "No meeting prep packet has been generated yet.")}</p>
          </div>
          <div class="card">
            <h2>Calendar Connection Status</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(account.get("owner_display_name") or account.get("label") or "Account")}</strong><div class="muted">{escape(_short_google_error(detail))}</div></div>' for account, detail in calendar_diagnostics) or '<div class="muted">Calendar connectivity looks healthy.</div>'}</div>
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


def render_publish_module_page(payload: dict) -> str:
    raw_json = json.dumps(payload, indent=2)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Publish</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #060c14;
      --bg-2: #0a121c;
      --panel: rgba(11, 20, 31, 0.9);
      --panel-strong: rgba(15, 23, 35, 0.96);
      --line: rgba(221, 173, 94, 0.14);
      --text: #eaf6ff;
      --muted: #9bb7cd;
      --accent: #ddad5e;
      --accent-soft: rgba(221, 173, 94, 0.14);
      --cyan-soft: rgba(121, 216, 255, 0.1);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: "SF Pro Display", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(221, 173, 94, 0.14), transparent 24%),
        radial-gradient(circle at top right, rgba(121, 216, 255, 0.08), transparent 24%),
        linear-gradient(180deg, #03070d 0%, var(--bg) 42%, var(--bg-2) 100%);
      color: var(--text);
    }}
    .shell {{ max-width: 1440px; margin: 0 auto; padding: 24px 24px 60px; }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 18px;
      padding: 14px 18px;
      border: 1px solid var(--line);
      border-radius: 24px;
      background: rgba(7, 13, 21, 0.76);
      backdrop-filter: blur(18px);
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.22);
    }}
    .topbar strong {{
      display: block;
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
    }}
    .topbar span {{
      display: block;
      color: var(--muted);
      margin-top: 4px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
      gap: 18px;
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 30px;
      background: linear-gradient(180deg, rgba(10, 18, 28, 0.96), rgba(7, 14, 23, 0.94));
      box-shadow: 0 24px 56px rgba(0, 0, 0, 0.3);
    }}
    .eyebrow {{
      color: var(--accent);
      letter-spacing: 0.18em;
      text-transform: uppercase;
      font-size: 12px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid rgba(221, 173, 94, 0.2);
      background: rgba(221, 173, 94, 0.07);
    }}
    .eyebrow::before {{
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: currentColor;
      box-shadow: 0 0 14px currentColor;
    }}
    h1 {{ margin: 10px 0 12px; font-size: clamp(34px, 5vw, 56px); }}
    h2 {{ margin-top: 0; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .hero-side {{
      display: grid;
      gap: 12px;
      align-content: start;
    }}
    .hero-note {{
      padding: 18px;
      border-radius: 20px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.03);
    }}
    .hero-note strong {{
      display: block;
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      margin-bottom: 8px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 22px;
    }}
    .stat, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
    }}
    .stat span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .stat strong {{ display: block; margin-top: 6px; font-size: 24px; }}
    .layout {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .span-4 {{ grid-column: span 4; }}
    .span-6 {{ grid-column: span 6; }}
    .span-8 {{ grid-column: span 8; }}
    .span-12 {{ grid-column: span 12; }}
    ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    li {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
    }}
    li strong {{ display: block; margin-bottom: 4px; }}
    li span {{ color: var(--muted); display: block; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    a, button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(121, 216, 255, 0.12);
      color: var(--text);
      text-decoration: none;
      font: inherit;
      cursor: pointer;
    }}
    .rail {{
      background: var(--panel-strong);
    }}
    .rail-header {{
      padding-bottom: 12px;
      margin-bottom: 12px;
      border-bottom: 1px solid var(--line);
    }}
    .rail-label {{
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}
    input {{
      width: 100%;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: rgba(3, 10, 18, 0.92);
      color: var(--text);
      font: inherit;
    }}
    form {{ display: grid; gap: 12px; }}
    .form-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
    }}
    label {{ display: grid; gap: 6px; color: var(--muted); font-size: 13px; }}
    input, select {{
      width: 100%;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(4, 12, 20, 0.92);
      color: var(--text);
      padding: 12px 14px;
      font: inherit;
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      border-radius: 16px;
      padding: 14px;
      border: 1px solid var(--line);
      background: rgba(3, 10, 18, 0.9);
      color: #d7e8f4;
      overflow-x: auto;
    }}
    .status-note {{ min-height: 1.3em; color: var(--muted); margin-top: 10px; }}
    @media (max-width: 980px) {{
      .hero {{ grid-template-columns: 1fr; }}
      .span-4, .span-6, .span-8, .span-12 {{ grid-column: span 12; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="topbar">
      <div>
        <strong>JARVIS Publish</strong>
        <span>Ghostwritr Publish Handoff with live launch posture, editorial readiness, and downstream supervision continuity.</span>
      </div>
      <div class="actions">
        <a href="/command-center">Back to Command Center</a>
        <button type="button" id="refresh-publish">Refresh Publish State</button>
      </div>
    </section>
    <section class="hero">
      <div>
        <div class="eyebrow">Meaningful Data Concept</div>
        <h1>Launch Ops Hub</h1>
        <p>A publish workspace modeled after the handoff-style mockups: live project posture, readiness pressure, chapter and calendar flow, and connected launch operations without losing the real JARVIS/Ghostwritr data seam.</p>
        <div class="stats">
          <div class="stat"><span>Status</span><strong id="hero-status">Loading...</strong></div>
          <div class="stat"><span>Projects</span><strong id="hero-projects">0</strong></div>
          <div class="stat"><span>Pending Reviews</span><strong id="hero-reviews">0</strong></div>
          <div class="stat"><span>Scheduled Posts</span><strong id="hero-posts">0</strong></div>
        </div>
        <p class="status-note" id="publish-status-note">Loading publish module state…</p>
      </div>
      <div class="hero-side">
        <div class="hero-note">
          <strong>Handoff State</strong>
          <div id="handoff-state-copy">Publish continuity is hydrating from the live backend.</div>
        </div>
        <div class="hero-note">
          <strong>Connected Launch Ops</strong>
          <div id="launch-ops-copy">Ghostwritr package, social queue, and revenue signals will appear here once payload state hydrates.</div>
        </div>
      </div>
    </section>
    <div class="layout">
      <section class="panel rail span-4">
        <div class="rail-header">
          <div class="rail-label">Ghostwritr Workspace</div>
          <h2>Publish handoff rail</h2>
        </div>
        <ul id="module-status-list"></ul>
      </section>
      <section class="panel span-8">
        <h2>Launch Ops Lane</h2>
        <ul id="launch-control-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Validation &amp; Readiness</h2>
        <ul id="project-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Chapter &amp; Calendar Readiness</h2>
        <ul id="calendar-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Connected Launch Ops</h2>
        <ul id="social-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Supervisor Strip</h2>
        <ul id="revenue-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Quick Draft Project</h2>
        <form id="create-project-form">
          <div class="form-grid">
            <label>Title<input id="project-title" placeholder="Launch-ready book or campaign"></label>
            <label>Type
              <select id="project-type">
                <option value="book">Book</option>
                <option value="course">Course</option>
                <option value="social">Social</option>
              </select>
            </label>
            <label>Platform<input id="project-platform" placeholder="Amazon KDP, Gumroad, YouTube"></label>
          </div>
          <button type="submit">Create Draft Project</button>
        </form>
        <p class="status-note" id="create-project-note">Create a small draft to verify the module can write real publishing state.</p>
      </section>
      <section class="panel span-6">
        <h2>Recent Publish Continuity</h2>
        <ul id="recent-activity-list"></ul>
      </section>
      <section class="panel span-12">
        <h2>Payload Preview</h2>
        <pre id="payload-preview"></pre>
      </section>
    </div>
  </main>
  <script>
    const initialPayload = {raw_json};
    let currentPayload = initialPayload;
    const heroStatus = document.getElementById("hero-status");
    const heroProjects = document.getElementById("hero-projects");
    const heroReviews = document.getElementById("hero-reviews");
    const heroPosts = document.getElementById("hero-posts");
    const statusNote = document.getElementById("publish-status-note");
    const projectNote = document.getElementById("create-project-note");
    const launchControlList = document.getElementById("launch-control-list");
    const moduleStatusList = document.getElementById("module-status-list");
    const projectList = document.getElementById("project-list");
    const calendarList = document.getElementById("calendar-list");
    const socialList = document.getElementById("social-list");
    const revenueList = document.getElementById("revenue-list");
    const recentActivityList = document.getElementById("recent-activity-list");
    const payloadPreview = document.getElementById("payload-preview");

    function esc(value) {{
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function li(title, summary, detail = "") {{
      return `<li><strong>${{esc(title)}}</strong><span>${{esc(summary)}}</span>${{detail ? `<span>${{esc(detail)}}</span>` : ""}}</li>`;
    }}

    function missionRouteLinks(missions) {{
      return (Array.isArray(missions) ? missions : []).map((mission) => {{
        const route = String(mission.route || "/mission-board").trim() || "/mission-board";
        const label = String(mission.title || mission.mission_id || "Mission").trim() || "Mission";
        const lane = String(mission.lane || "next").trim() || "next";
        return `<a href="${{esc(route)}}">${{esc(`${{label}} · ${{lane}}`)}}</a>`;
      }}).join("");
    }}

    function render(payload) {{
      const launch = payload.launch_control || {{}};
      const activeProject = launch.active_project || null;
      const calendar = payload.calendar || {{}};
      const social = payload.social || {{}};
      const revenue = payload.revenue || {{}};
      const projects = Array.isArray(payload.projects) ? payload.projects : [];
      const upcoming = Array.isArray(calendar.upcoming) ? calendar.upcoming : [];
      const overdue = Array.isArray(calendar.overdue) ? calendar.overdue : [];
      const posts = Array.isArray(social.posts) ? social.posts : [];

      heroStatus.textContent = payload.status || "Stubbed";
      heroProjects.textContent = String(payload.project_count || 0);
      heroReviews.textContent = String(payload.review_count || 0);
      heroPosts.textContent = String(payload.scheduled_post_count || 0);
      statusNote.textContent = payload.summary || "No publish summary captured yet.";
      document.getElementById("handoff-state-copy").textContent = launch.next_action || payload.what_became_real || "No handoff signal yet.";
      document.getElementById("launch-ops-copy").textContent = payload.remains_partial || "Connected launch ops are fully live.";

      moduleStatusList.innerHTML = [
        li("Workspace Status", payload.available ? "Publishing data is live." : "Publishing data is unavailable; the screen is running in fallback mode."),
        li("What Became Real", payload.what_became_real || "No publish seam note recorded yet."),
        li("What Remains Partial", payload.remains_partial || "No partial work recorded."),
        li("Proof API", "/api/publish/module", "/api/publishing/status"),
      ].join("");

      launchControlList.innerHTML = [
        li("Active Project", activeProject ? activeProject.title || activeProject.project_id : "No active project selected yet.", activeProject ? `Phase: ${{activeProject.phase || "unknown"}} · Days to launch: ${{activeProject.days_to_launch ?? "n/a"}}` : ""),
        li("Next Action", launch.next_action || "No launch-control action recorded yet."),
        li("Pending Reviews", String(payload.review_count || 0), "Ghostwritr review pressure"),
        li("Scheduled Posts", String(payload.scheduled_post_count || 0), "Publishing queue pressure"),
      ].join("");

      projectList.innerHTML = projects.length
        ? projects.slice(0, 6).map((item) => li(item.title || "Untitled project", `${{item.project_type || "project"}} · ${{item.status || "draft"}}`, item.platform || "No platform")).join("")
        : '<li><strong>No projects yet.</strong><span>Create a draft project below to seed the publish workspace.</span></li>';

      calendarList.innerHTML = [
        ...upcoming.slice(0, 4).map((item) => li(item.title || "Calendar item", `${{item.content_type || "content"}} · ${{item.status || "planned"}}`, item.planned_date || "")),
        ...overdue.slice(0, 2).map((item) => li(item.title || "Overdue item", `Overdue · ${{item.status || "planned"}}`, item.planned_date || "")),
      ].join("") || '<li><strong>No calendar items yet.</strong><span>Publishing calendar is clear right now.</span></li>';

      socialList.innerHTML = posts.length
        ? posts.slice(0, 6).map((item) => li(item.platform || "Platform", item.status || "draft", String(item.content || "").slice(0, 120) || "No post content")).join("")
        : '<li><strong>No social queue yet.</strong><span>Draft or scheduled posts will appear here.</span></li>';

      revenueList.innerHTML = [
        li("Monthly Estimate", String(revenue.monthly_estimate_total ?? 0), "Revenue posture across active publishing streams"),
        li("Active Streams", String(revenue.active_stream_count ?? 0), "Live monetization channels under supervision"),
        li("Attention Flags", String(revenue.attention_count ?? 0), "Launch integrity or commercial pressure signals"),
      ].join("");
      recentActivityList.innerHTML = (Array.isArray(payload.recent_activity) ? payload.recent_activity : []).length
        ? payload.recent_activity.map((item) => li(item.title || "Publish action", item.subtitle || item.actor || "Operator continuity", item.detail || item.route_label || "")).join("")
        : '<li><strong>No publish continuity recorded yet.</strong><span>Create a draft project and publish-side activity will appear here.</span></li>';

      payloadPreview.textContent = JSON.stringify(payload, null, 2);
    }}

    async function recordOperatorAction(payload) {{
      await fetch("/api/activity/operator-action", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload),
      }});
    }}

    async function refreshPublishState() {{
      statusNote.textContent = "Refreshing publish module state…";
      try {{
        const response = await fetch("/api/publish/module");
        const payload = await response.json();
        render(payload);
        statusNote.textContent = payload.summary || "Publish module refreshed.";
      }} catch (error) {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }}
    }}

    async function createDraftProject(event) {{
      event.preventDefault();
      projectNote.textContent = "Creating draft project…";
      try {{
        const response = await fetch("/api/publishing/projects", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            title: document.getElementById("project-title").value,
            project_type: document.getElementById("project-type").value,
            platform: document.getElementById("project-platform").value,
            status: "draft",
          }}),
        }});
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.detail || payload.error || "Create project failed");
        }}
        await recordOperatorAction({{
          actor: "Chris",
          domain: "publish",
          action: "Create Draft Project",
          title: payload.title || payload.project_id || "Draft project",
          detail: `Created publish draft on ${{payload.platform || "unspecified platform"}}`,
          why_now: "Publish module created a draft handoff asset from the live route.",
          result_summary: "Publish continuity updated with a new draft project.",
          route: "/publish",
          route_label: "Open Publish",
          related_kind: "publishing-project",
          related_label: payload.title || payload.project_id || "Draft project",
          succeeded: true,
        }});
        projectNote.textContent = `Created draft project: ${{payload.title || payload.project_id || "project"}}.`;
        await refreshPublishState();
      }} catch (error) {{
        projectNote.textContent = `Create failed: ${{String(error)}}`;
      }}
    }}

    document.getElementById("refresh-publish").addEventListener("click", () => {{
      refreshPublishState().catch((error) => {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }});
    }});
    document.getElementById("create-project-form").addEventListener("submit", createDraftProject);
    render(initialPayload);
  </script>
</body>
</html>
"""


def render_agent_ops_module_page(payload: dict) -> str:
    raw_json = json.dumps(payload, indent=2)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Agent Operations</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #071019;
      --bg-2: #0a1623;
      --panel: rgba(10, 21, 34, 0.9);
      --line: rgba(121, 216, 255, 0.14);
      --text: #edf8ff;
      --muted: #97b5cb;
      --accent: #79d8ff;
      --ok: #94f0bf;
      --warn: #ffd48a;
      --risk: #ffb0b0;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "SF Pro Display", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top, rgba(121, 216, 255, 0.14), transparent 36%),
        linear-gradient(180deg, #040b12 0%, var(--bg) 44%, var(--bg-2) 100%);
      color: var(--text);
    }}
    .shell {{ max-width: 1440px; margin: 0 auto; padding: 36px 24px 60px; }}
    .hero {{
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 28px;
      background: linear-gradient(180deg, rgba(11, 24, 38, 0.94), rgba(7, 17, 28, 0.92));
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.28);
    }}
    .eyebrow {{ color: var(--accent); letter-spacing: 0.18em; text-transform: uppercase; font-size: 12px; }}
    h1 {{ margin: 10px 0 12px; font-size: clamp(34px, 5vw, 56px); }}
    h2 {{ margin: 0 0 14px; font-size: 18px; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    a, button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(121, 216, 255, 0.12);
      color: var(--text);
      text-decoration: none;
      font: inherit;
      cursor: pointer;
    }}
    button.alt {{
      background: rgba(255,255,255,0.04);
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 22px;
    }}
    .stat, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
    }}
    .stat span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .stat strong {{ display: block; margin-top: 6px; font-size: 24px; }}
    .layout {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .span-4 {{ grid-column: span 4; }}
    .span-5 {{ grid-column: span 5; }}
    .span-7 {{ grid-column: span 7; }}
    .span-8 {{ grid-column: span 8; }}
    ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    li {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
    }}
    li strong {{ display: block; margin-bottom: 4px; }}
    li span {{ color: var(--muted); display: block; }}
    .roster {{ display: grid; gap: 10px; }}
    .agent-card {{
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255,255,255,0.03);
      display: grid;
      gap: 10px;
    }}
    .agent-head {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: start;
    }}
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      padding: 5px 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      font-size: 12px;
      color: var(--muted);
      background: rgba(255,255,255,0.04);
    }}
    .chip.accepted {{ color: var(--ok); border-color: rgba(148,240,191,0.28); }}
    .chip.regressed {{ color: var(--risk); border-color: rgba(255,176,176,0.28); }}
    .chip.steady {{ color: var(--warn); border-color: rgba(255,212,138,0.28); }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
    }}
    .meta div {{
      padding: 10px 12px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.02);
    }}
    .meta label {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
    }}
    .detail-copy {{
      min-height: 1.3em;
      color: var(--muted);
      margin-top: 10px;
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      border-radius: 16px;
      padding: 14px;
      border: 1px solid var(--line);
      background: rgba(3, 10, 18, 0.9);
      color: #d7e8f4;
      overflow-x: auto;
    }}
    @media (max-width: 1080px) {{
      .span-4, .span-5, .span-7, .span-8 {{ grid-column: span 12; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="eyebrow">Level 3 Core Module</div>
      <h1>JARVIS Agent Operations</h1>
      <p>A dedicated operations surface for the live agent roster, runtime posture, and queue-run controls. This turns Agent Operations into a real app module instead of leaving it split between command-center summaries and hierarchy pages.</p>
      <div class="actions">
        <a href="/command-center">Back to Command Center</a>
        <a href="/agents/hierarchy">Open Agent Hierarchy</a>
        <button type="button" id="refresh-agent-ops">Refresh Agent Ops State</button>
      </div>
      <div class="stats">
        <div class="stat"><span>Status</span><strong id="hero-status">Loading...</strong></div>
        <div class="stat"><span>Visible Agents</span><strong id="hero-visible-agents">0</strong></div>
        <div class="stat"><span>Running</span><strong id="hero-running">0</strong></div>
        <div class="stat"><span>Blocked</span><strong id="hero-blocked">0</strong></div>
        <div class="stat"><span>Needs Attention</span><strong id="hero-attention">0</strong></div>
      </div>
      <p class="detail-copy" id="agent-ops-status-note">Loading agent operations state…</p>
    </section>
    <div class="layout">
      <section class="panel span-7">
        <h2>Agent Roster</h2>
        <div id="agent-roster" class="roster"></div>
      </section>
      <section class="panel span-5">
        <h2>Selected Agent Detail</h2>
        <div id="selected-agent-detail"></div>
        <p class="detail-copy" id="agent-action-note">Select an agent or queue a live run to inspect current posture.</p>
      </section>
      <section class="panel span-4">
        <h2>Scheduler Posture</h2>
        <ul id="scheduler-list"></ul>
      </section>
      <section class="panel span-4">
        <h2>Runtime Summary</h2>
        <ul id="runtime-list"></ul>
      </section>
      <section class="panel span-4">
        <h2>Proof Paths</h2>
        <ul id="proof-list"></ul>
      </section>
      <section class="panel span-4">
        <h2>Recent Agent Ops Continuity</h2>
        <ul id="agent-ops-activity-list"></ul>
      </section>
      <section class="panel span-8">
        <h2>Payload Preview</h2>
        <pre id="payload-preview"></pre>
      </section>
    </div>
  </main>
  <script>
    const initialPayload = {raw_json};
    let latestPayload = initialPayload;
    let selectedAgentId = "";

    const heroStatus = document.getElementById("hero-status");
    const heroVisibleAgents = document.getElementById("hero-visible-agents");
    const heroRunning = document.getElementById("hero-running");
    const heroBlocked = document.getElementById("hero-blocked");
    const heroAttention = document.getElementById("hero-attention");
    const rosterEl = document.getElementById("agent-roster");
    const detailEl = document.getElementById("selected-agent-detail");
    const schedulerEl = document.getElementById("scheduler-list");
    const runtimeEl = document.getElementById("runtime-list");
    const proofEl = document.getElementById("proof-list");
    const recentActivityEl = document.getElementById("agent-ops-activity-list");
    const payloadPreview = document.getElementById("payload-preview");
    const statusNote = document.getElementById("agent-ops-status-note");
    const actionNote = document.getElementById("agent-action-note");

    function esc(value) {{
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function item(title, summary, detail = "") {{
      return `<li><strong>${{esc(title)}}</strong><span>${{esc(summary)}}</span>${{detail ? `<span>${{esc(detail)}}</span>` : ""}}</li>`;
    }}

    function chip(label, klass = "") {{
      return `<span class="chip ${{esc(klass)}}">${{esc(label)}}</span>`;
    }}

    function rosterItems(payload) {{
      return Array.isArray((payload.agent_ops_roster || {{}}).items) ? payload.agent_ops_roster.items : [];
    }}

    async function recordAgentOpsActivity(payload) {{
      try {{
        const response = await fetch("/api/activity/operator-action", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload || {{}}),
        }});
        if (!response.ok) return false;
        await response.json().catch(() => ({{}}));
        return true;
      }} catch (_error) {{
        return false;
      }}
    }}

    function setSelectedAgent(agentId) {{
      selectedAgentId = agentId || "";
      render(latestPayload);
    }}

    async function queueAgentRun(agentId) {{
      actionNote.textContent = `Queueing agent run for ${{agentId}}…`;
      try {{
        const response = await fetch(`/api/scheduler/run/${{encodeURIComponent(agentId)}}`, {{
          method: "POST",
        }});
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.detail || payload.error || "Queue request failed");
        }}
        const recorded = await recordAgentOpsActivity({{
          actor: "Chris",
          domain: "agent-ops",
          action: "Queue Agent Run",
          title: agentId,
          status: String(payload.status || "queued"),
          detail: `Action succeeded: /api/scheduler/run/${{agentId}}`,
          why_now: `Agent Operations queued a live runtime cycle for ${{agentId}}.`,
          result_summary: `Agent run queued with item ${{String(payload.item_id || "unknown")}}.`,
          route: "/agent-ops-center",
          route_label: "Open Agent Ops",
          related_kind: "agent",
          related_label: agentId,
          succeeded: true,
        }});
        actionNote.textContent = recorded
          ? `Queued ${{agentId}} with item ${{payload.item_id || "unknown"}} and recorded it in shared activity.`
          : `Queued ${{agentId}} with item ${{payload.item_id || "unknown"}}.`;
        await refreshAgentOpsState();
      }} catch (error) {{
        const errorText = String(error);
        await recordAgentOpsActivity({{
          actor: "Chris",
          domain: "agent-ops",
          action: "Queue Agent Run",
          title: agentId,
          status: "failed",
          detail: `Action failed: /api/scheduler/run/${{agentId}}`,
          why_now: errorText,
          result_summary: `Queue Agent Run failed: ${{errorText}}`,
          route: "/agent-ops-center",
          route_label: "Open Agent Ops",
          related_kind: "agent",
          related_label: agentId,
          succeeded: false,
        }});
        actionNote.textContent = `Queue Agent Run failed: ${{errorText}}`;
      }}
    }}

    async function promoteTaskAgent(agent) {{
      if (!agent || !agent.is_task_agent || !agent.agent_id) return;
      const roleInput = document.getElementById("task-agent-role-name");
      const policyInput = document.getElementById("task-agent-policy-assignment");
      const memoryInput = document.getElementById("task-agent-memory-boundary");
      const draft = {{
        role_name: String(roleInput?.value || agent.name || "").trim(),
        policy_assignment: String(policyInput?.value || agent.assignment || "").trim(),
        memory_boundary: String(memoryInput?.value || agent.memory_boundary || "").trim(),
        force: true,
      }};
      actionNote.textContent = `Promoting task agent ${{agent.agent_id}}…`;
      try {{
        const response = await fetch(`/api/agents/${{encodeURIComponent(agent.agent_id)}}/promote`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(draft),
        }});
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.detail || payload.error || "Task agent promotion failed");
        }}
        const recorded = await recordAgentOpsActivity({{
          actor: "Chris",
          domain: "agent-ops",
          action: "Promote Task Agent",
          title: agent.name || agent.agent_id,
          status: String(payload.promotion_status || payload.status || "promoted"),
          detail: `Action succeeded: /api/agents/${{agent.agent_id}}/promote`,
          why_now: draft.policy_assignment || agent.assignment || `Task agent ${{agent.agent_id}} needed a durable role assignment.`,
          result_summary: `Task agent promotion status: ${{String(payload.promotion_status || payload.status || "promoted")}}`,
          route: "/agent-ops-center",
          route_label: "Open Agent Ops",
          related_kind: "agent",
          related_label: agent.name || agent.agent_id,
          succeeded: true,
        }});
        actionNote.textContent = recorded
          ? `Promoted ${{agent.agent_id}} and recorded the result in shared activity.`
          : `Promoted ${{agent.agent_id}}.`;
        await refreshAgentOpsState();
        selectedAgentId = agent.agent_id;
      }} catch (error) {{
        const errorText = String(error);
        await recordAgentOpsActivity({{
          actor: "Chris",
          domain: "agent-ops",
          action: "Promote Task Agent",
          title: agent.name || agent.agent_id,
          status: "failed",
          detail: `Action failed: /api/agents/${{agent.agent_id}}/promote`,
          why_now: errorText,
          result_summary: `Task agent promotion failed: ${{errorText}}`,
          route: "/agent-ops-center",
          route_label: "Open Agent Ops",
          related_kind: "agent",
          related_label: agent.name || agent.agent_id,
          succeeded: false,
        }});
        actionNote.textContent = `Promote Task Agent failed: ${{errorText}}`;
      }}
    }}

    async function retireTaskAgent(agent) {{
      if (!agent || !agent.is_task_agent || !agent.agent_id) return;
      actionNote.textContent = `Retiring task agent ${{agent.agent_id}}…`;
      try {{
        const response = await fetch(`/api/agents/${{encodeURIComponent(agent.agent_id)}}/retire`, {{
          method: "POST",
        }});
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.detail || payload.error || "Task agent retirement failed");
        }}
        const recorded = await recordAgentOpsActivity({{
          actor: "Chris",
          domain: "agent-ops",
          action: "Retire Task Agent",
          title: agent.name || agent.agent_id,
          status: String(payload.status || "retired"),
          detail: `Action succeeded: /api/agents/${{agent.agent_id}}/retire`,
          why_now: agent.assignment || agent.mission_id || `Task agent ${{agent.agent_id}} is being retired from active duty.`,
          result_summary: `Task agent retirement status: ${{String(payload.status || "retired")}}`,
          route: "/agent-ops-center",
          route_label: "Open Agent Ops",
          related_kind: "agent",
          related_label: agent.name || agent.agent_id,
          succeeded: true,
        }});
        actionNote.textContent = recorded
          ? `Retired ${{agent.agent_id}} and recorded the result in shared activity.`
          : `Retired ${{agent.agent_id}}.`;
        await refreshAgentOpsState();
        selectedAgentId = agent.agent_id;
      }} catch (error) {{
        const errorText = String(error);
        await recordAgentOpsActivity({{
          actor: "Chris",
          domain: "agent-ops",
          action: "Retire Task Agent",
          title: agent.name || agent.agent_id,
          status: "failed",
          detail: `Action failed: /api/agents/${{agent.agent_id}}/retire`,
          why_now: errorText,
          result_summary: `Task agent retirement failed: ${{errorText}}`,
          route: "/agent-ops-center",
          route_label: "Open Agent Ops",
          related_kind: "agent",
          related_label: agent.name || agent.agent_id,
          succeeded: false,
        }});
        actionNote.textContent = `Retire Task Agent failed: ${{errorText}}`;
      }}
    }}

    async function saveTaskAgentAssignment(agent) {{
      if (!agent || !agent.is_task_agent || !agent.agent_id) return;
      const missionSelect = document.getElementById("task-agent-mission-id");
      const rolesInput = document.getElementById("task-agent-mission-roles");
      const policyInput = document.getElementById("task-agent-policy-assignment");
      const purposeInput = document.getElementById("task-agent-purpose");
      const missionId = String(missionSelect?.value || agent.mission_id || "").trim();
      const missionRoles = String(rolesInput?.value || "").split(",").map((item) => item.trim()).filter(Boolean);
      const policyAssignment = String(policyInput?.value || agent.policy_assignment || "").trim();
      const purpose = String(purposeInput?.value || agent.purpose || "").trim();
      actionNote.textContent = `Saving assignment for ${{agent.agent_id}}…`;
      try {{
        const response = await fetch(`/api/agents/${{encodeURIComponent(agent.agent_id)}}/assignment`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            mission_id: missionId,
            mission_roles: missionRoles,
            policy_assignment: policyAssignment,
            purpose,
          }}),
        }});
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.detail || payload.error || "Assignment update failed");
        }}
        const recorded = await recordAgentOpsActivity({{
          actor: "Chris",
          domain: "agent-ops",
          action: "Update Task Agent Assignment",
          title: agent.name || agent.agent_id,
          status: String(payload.status || "active"),
          detail: `Action succeeded: /api/agents/${{agent.agent_id}}/assignment`,
          why_now: missionId || policyAssignment || `Task agent ${{agent.agent_id}} needed a mission-linked assignment update.`,
          result_summary: `Task agent assignment now points at ${{missionId || "the current mission posture"}}.`,
          route: "/agent-ops-center",
          route_label: "Open Agent Ops",
          related_kind: "agent",
          related_label: agent.name || agent.agent_id,
          succeeded: true,
        }});
        actionNote.textContent = recorded
          ? `Saved assignment for ${{agent.agent_id}} and recorded it in shared activity.`
          : `Saved assignment for ${{agent.agent_id}}.`;
        await refreshAgentOpsState();
        selectedAgentId = agent.agent_id;
      }} catch (error) {{
        const errorText = String(error);
        await recordAgentOpsActivity({{
          actor: "Chris",
          domain: "agent-ops",
          action: "Update Task Agent Assignment",
          title: agent.name || agent.agent_id,
          status: "failed",
          detail: `Action failed: /api/agents/${{agent.agent_id}}/assignment`,
          why_now: errorText,
          result_summary: `Task agent assignment failed: ${{errorText}}`,
          route: "/agent-ops-center",
          route_label: "Open Agent Ops",
          related_kind: "agent",
          related_label: agent.name || agent.agent_id,
          succeeded: false,
        }});
        actionNote.textContent = `Save Assignment failed: ${{errorText}}`;
      }}
    }}

    function renderDetail(agent) {{
      if (!agent) {{
        detailEl.innerHTML = "<p class=\\"detail-copy\\">No visible agent selected yet.</p>";
        return;
      }}
      const missionOptions = Array.isArray((latestPayload || {{}}).mission_options) ? latestPayload.mission_options : [];
      const review = ((latestPayload || {{}}).agent_reviews || {{}})[agent.agent_id || ""] || {{}};
      const roles = Array.isArray(agent.mission_roles) ? agent.mission_roles : [];
      const reviewDecisions = Array.isArray(review.recent_decisions) ? review.recent_decisions : [];
      const taskAgentControls = agent.is_task_agent ? `
        <div class="meta">
          <div><label>Source</label><strong>${{esc(agent.source_label || "Task Agent")}}</strong></div>
          <div><label>Mission</label><strong>${{esc(agent.mission_id || "not linked")}}</strong></div>
          <div><label>Template</label><strong>${{esc(agent.template_id || "not recorded")}}</strong></div>
          <div><label>Policy Assignment</label><strong>${{esc(agent.policy_assignment || "not assigned")}}</strong></div>
          <div><label>Memory Boundary</label><strong>${{esc(agent.memory_boundary || "not recorded")}}</strong></div>
          <div><label>Promotion Candidate</label><strong>${{esc(agent.promotion_candidate ? "eligible" : "not yet")}}</strong></div>
        </div>
        <div class="meta">
          <div>
            <label for="task-agent-role-name">Role Name</label>
            <input id="task-agent-role-name" value="${{esc(agent.name || "")}}" />
          </div>
          <div>
            <label for="task-agent-mission-id">Mission Assignment</label>
            <select id="task-agent-mission-id">
              ${{missionOptions.map((item) => `<option value="${{esc(item.mission_id || "")}}"${{String(item.mission_id || "") === String(agent.mission_id || "") ? " selected" : ""}}>${{esc((item.title || item.mission_id || "Mission") + " · " + (item.lane || "next"))}}</option>`).join("")}}
            </select>
          </div>
          <div>
            <label for="task-agent-mission-roles">Mission Roles</label>
            <input id="task-agent-mission-roles" value="${{esc(roles.join(", "))}}" />
          </div>
          <div>
            <label for="task-agent-policy-assignment">Policy Assignment</label>
            <input id="task-agent-policy-assignment" value="${{esc(agent.policy_assignment || agent.assignment || "")}}" />
          </div>
          <div>
            <label for="task-agent-purpose">Purpose</label>
            <input id="task-agent-purpose" value="${{esc(agent.purpose || "")}}" />
          </div>
          <div>
            <label for="task-agent-memory-boundary">Memory Boundary</label>
            <input id="task-agent-memory-boundary" value="${{esc(agent.memory_boundary || (agent.mission_id ? `mission:${{agent.mission_id}}` : ""))}}" />
          </div>
        </div>
      ` : "";
      const missionLinks = agent.mission_id ? `
        <a href="/mission-board">Open Mission Board</a>
        <a href="/api/missions/${{encodeURIComponent(agent.mission_id)}}">Open Mission API</a>
      ` : '<a href="/command-center">Open Command Center</a>';
      detailEl.innerHTML = `
        <div class="agent-card">
          <div class="agent-head">
            <div>
              <strong>${{esc(agent.name || agent.agent_id || "Agent")}}</strong>
              <p>${{esc(agent.purpose || "No purpose recorded.")}}</p>
            </div>
            <div class="chips">
              ${{chip(agent.status || "unknown", agent.status_class || "")}}
              ${{chip(agent.maturity || "Useful", agent.maturity_class || "")}}
            </div>
          </div>
          <div class="meta">
            <div><label>Assignment</label><strong>${{esc(agent.assignment || "unassigned")}}</strong></div>
            <div><label>Module</label><strong>${{esc(agent.module || "general")}}</strong></div>
            <div><label>Authority Stage</label><strong>${{esc(agent.authority_stage || "draft")}}</strong></div>
            <div><label>Heartbeat</label><strong>${{esc(agent.heartbeat_status || "unknown")}}</strong></div>
            <div><label>Last Activity</label><strong>${{esc(agent.last_activity || "not recorded")}}</strong></div>
            <div><label>Attention</label><strong>${{esc(agent.attention_reason || "No active attention reason recorded.")}}</strong></div>
          </div>
          ${{taskAgentControls}}
          <div class="chips">
            ${{chip(agent.source_label || "Agent", agent.is_task_agent ? "artifact" : "")}}
            ${{roles.length ? roles.map((role) => chip(role)).join("") : chip("No mission roles")}}
          </div>
          <div class="meta">
            <div><label>Outcome Review</label><strong>${{esc(review.success_rate || "No success rate yet")}}</strong></div>
            <div><label>Usage Count</label><strong>${{esc(review.usage_count ?? 0)}}</strong></div>
            <div><label>Success Count</label><strong>${{esc(review.success_count ?? 0)}}</strong></div>
            <div><label>Workspace Status</label><strong>${{esc(review.status || "not recorded")}}</strong></div>
            <div><label>Review Mission</label><strong>${{esc(review.mission_title || review.mission_id || "not linked")}}</strong></div>
            <div><label>Last Used</label><strong>${{esc(review.last_used_at || review.updated_at || "not recorded")}}</strong></div>
          </div>
          <div class="meta">
            <div><label>Current Focus</label><strong>${{esc(review.current_focus || "No current focus recorded.")}}</strong></div>
            <div><label>Pending Reviews</label><strong>${{esc(review.pending_reviews ?? 0)}}</strong></div>
            <div><label>Active Tasks</label><strong>${{esc(review.active_tasks ?? 0)}}</strong></div>
            <div><label>Blocked Tasks</label><strong>${{esc(review.blocked_tasks ?? 0)}}</strong></div>
            <div><label>Ownership Mode</label><strong>${{esc(review.ownership_mode || "supporting")}}</strong></div>
            <div><label>Last Handoff</label><strong>${{esc(review.last_handoff_at || "not recorded")}}</strong></div>
          </div>
          <ul>
            ${{reviewDecisions.length ? reviewDecisions.map((decision) => `<li><strong>${{esc(decision.summary || "Decision")}}</strong><span>${{esc(decision.rationale || "No rationale recorded.")}}</span><span>${{esc(decision.created_at || "")}}</span></li>`).join("") : '<li><strong>No recent decisions.</strong><span>This agent has not recorded recent outcome decisions yet.</span></li>'}}
          </ul>
          <div class="actions">
            <button type="button" data-queue-run="${{esc(agent.agent_id || "")}}">Queue Agent Run</button>
            <a href="/agents/workspace/${{encodeURIComponent(agent.agent_id || "")}}">Open Agent Workspace</a>
            ${{missionLinks}}
            ${{agent.is_task_agent && agent.status !== "retired" ? '<button type="button" data-save-selected-task-agent-assignment="1">Save Assignment</button>' : ""}}
            ${{agent.is_task_agent && agent.status !== "retired" ? '<button type="button" data-promote-selected-task-agent="1">Promote Task Agent</button>' : ""}}
            ${{agent.is_task_agent && agent.status !== "retired" ? '<button type="button" class="alt" data-retire-selected-task-agent="1">Retire Task Agent</button>' : ""}}
          </div>
        </div>
      `;
      document.querySelector("[data-save-selected-task-agent-assignment]")?.addEventListener("click", () => {{
        saveTaskAgentAssignment(agent).catch((error) => {{
          actionNote.textContent = `Save Assignment failed: ${{String(error)}}`;
        }});
      }});
    }}

    function render(payload) {{
      latestPayload = payload || {{}};
      const roster = payload.agent_ops_roster || {{}};
      const counts = roster.counts || {{}};
      const items = rosterItems(payload);
      const scheduler = payload.scheduler_status || {{}};
      const runtimeCounts = payload.runtime_counts || {{}};
      const proofs = payload.proof_paths || {{}};

      heroStatus.textContent = payload.status || "Stubbed";
      heroVisibleAgents.textContent = String(roster.item_count || items.length || 0);
      heroRunning.textContent = String(counts.running || 0);
      heroBlocked.textContent = String(counts.blocked || 0);
      heroAttention.textContent = String(counts.attention || 0);
      statusNote.textContent = payload.summary || "No agent operations summary recorded yet.";

      const currentSelection = items.find((item) => item.agent_id === selectedAgentId) || items[0] || null;
      if (!selectedAgentId && currentSelection) {{
        selectedAgentId = currentSelection.agent_id || "";
      }}

      rosterEl.innerHTML = items.length
        ? items.map((agent) => `
            <div class="agent-card">
              <div class="agent-head">
                <div>
                  <strong>${{esc(agent.name || agent.agent_id || "Agent")}}</strong>
                  <span>${{esc(agent.domain || "general")}} · ${{esc(agent.assignment || "unassigned")}}</span>
                </div>
                <div class="chips">
                  ${{chip(agent.source_label || "Agent", agent.is_task_agent ? "artifact" : "")}}
                  ${{chip(agent.status || "unknown", agent.status_class || "")}}
                  ${{chip(agent.maturity || "Useful", agent.maturity_class || "")}}
                </div>
              </div>
              <span>${{esc(agent.purpose || "No purpose recorded.")}}</span>
              <span>${{esc(agent.last_activity || "not recorded")}}</span>
              <div class="actions">
                <button type="button" class="alt" data-select-agent="${{esc(agent.agent_id || "")}}">Inspect Agent</button>
                <button type="button" data-queue-run="${{esc(agent.agent_id || "")}}">Queue Agent Run</button>
              </div>
            </div>
          `).join("")
        : '<div class="agent-card"><strong>No visible agents yet.</strong><span>The module is live, but no roster items are currently visible.</span></div>';

      renderDetail(currentSelection);

      schedulerEl.innerHTML = [
        item("Scheduler Running", scheduler.running ? "Scheduler is active." : "Scheduler is unavailable or not initialised."),
        item("Known Agents", String(scheduler.agent_count ?? scheduler.total_agents ?? 0)),
        item("Queued Items", String(scheduler.queued_count ?? scheduler.pending_count ?? 0)),
        item("Last Error", scheduler.error || "No scheduler error recorded."),
      ].join("");

      runtimeEl.innerHTML = [
        item("Registry Count", String(runtimeCounts.registry_count ?? 0)),
        item("Runtime Count", String(runtimeCounts.runtime_count ?? 0)),
        item("Background Agents", String(runtimeCounts.background_count ?? 0)),
        item("Task Agents", String(counts.task_agents ?? 0)),
        item("Promoted Agents", String(counts.promoted ?? 0)),
        item("What Became Real", payload.what_became_real || "No module note recorded yet."),
        item("What Remains Partial", payload.remains_partial || "No partial work recorded."),
      ].join("");

      proofEl.innerHTML = Object.entries(proofs).map(([key, value]) => item(key, value)).join("");
      recentActivityEl.innerHTML = (Array.isArray(payload.recent_activity) ? payload.recent_activity : []).length
        ? payload.recent_activity.map((item) => `<li><strong>${{esc(item.title || "Agent Ops action")}}</strong><span>${{esc(item.subtitle || item.actor || "Operator continuity")}}</span><span>${{esc(item.detail || item.route_label || "")}}</span></li>`).join("")
        : '<li><strong>No agent ops continuity recorded yet.</strong><span>Queue a run or update an assignment to start the route-level continuity trail.</span></li>';
      payloadPreview.textContent = JSON.stringify(payload, null, 2);

      document.querySelectorAll("[data-select-agent]").forEach((button) => {{
        button.addEventListener("click", () => setSelectedAgent(button.getAttribute("data-select-agent") || ""));
      }});
      document.querySelectorAll("[data-queue-run]").forEach((button) => {{
        button.addEventListener("click", () => {{
          const agentId = button.getAttribute("data-queue-run") || "";
          if (agentId) {{
            queueAgentRun(agentId).catch((error) => {{
              actionNote.textContent = `Queue Agent Run failed: ${{String(error)}}`;
            }});
          }}
        }});
      }});
      const selectedAgent = currentSelection;
      const promoteButton = document.querySelector("[data-promote-selected-task-agent]");
      if (promoteButton && selectedAgent) {{
        promoteButton.addEventListener("click", () => {{
          promoteTaskAgent(selectedAgent).catch((error) => {{
            actionNote.textContent = `Promote Task Agent failed: ${{String(error)}}`;
          }});
        }});
      }}
      const retireButton = document.querySelector("[data-retire-selected-task-agent]");
      if (retireButton && selectedAgent) {{
        retireButton.addEventListener("click", () => {{
          retireTaskAgent(selectedAgent).catch((error) => {{
            actionNote.textContent = `Retire Task Agent failed: ${{String(error)}}`;
          }});
        }});
      }}
    }}

    async function refreshAgentOpsState() {{
      statusNote.textContent = "Refreshing agent operations state…";
      try {{
        const response = await fetch("/api/agent-ops/module");
        const payload = await response.json();
        render(payload);
        statusNote.textContent = payload.summary || "Agent operations module refreshed.";
      }} catch (error) {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }}
    }}

    document.getElementById("refresh-agent-ops").addEventListener("click", () => {{
      refreshAgentOpsState().catch((error) => {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }});
    }});

    render(initialPayload);
  </script>
</body>
</html>
"""


def render_recovery_module_page(payload: dict) -> str:
    raw_json = json.dumps(payload, indent=2)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Failure and Recovery</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #071018;
      --bg-2: #091523;
      --panel: rgba(9, 20, 33, 0.92);
      --line: rgba(121, 216, 255, 0.14);
      --text: #edf7ff;
      --muted: #9eb8cb;
      --accent: #79d8ff;
      --ok: #94f0bf;
      --warn: #ffd48a;
      --risk: #ffb0b0;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "SF Pro Display", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top, rgba(121, 216, 255, 0.12), transparent 36%),
        linear-gradient(180deg, #040b12 0%, var(--bg) 44%, var(--bg-2) 100%);
      color: var(--text);
    }}
    .shell {{ max-width: 1460px; margin: 0 auto; padding: 36px 24px 60px; }}
    .hero {{
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 28px;
      background: linear-gradient(180deg, rgba(11, 24, 38, 0.94), rgba(7, 17, 28, 0.92));
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.28);
    }}
    .eyebrow {{ color: var(--accent); letter-spacing: 0.18em; text-transform: uppercase; font-size: 12px; }}
    h1 {{ margin: 10px 0 12px; font-size: clamp(34px, 5vw, 56px); }}
    h2 {{ margin: 0 0 14px; font-size: 18px; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    a, button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(121, 216, 255, 0.12);
      color: var(--text);
      text-decoration: none;
      font: inherit;
      cursor: pointer;
    }}
    button.alt {{ background: rgba(255,255,255,0.04); }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 22px;
    }}
    .stat, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
    }}
    .stat span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .stat strong {{ display: block; margin-top: 6px; font-size: 24px; }}
    .layout {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .span-4 {{ grid-column: span 4; }}
    .span-5 {{ grid-column: span 5; }}
    .span-7 {{ grid-column: span 7; }}
    .span-8 {{ grid-column: span 8; }}
    ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    li {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
    }}
    li strong {{ display: block; margin-bottom: 4px; }}
    li span {{ color: var(--muted); display: block; }}
    .detail-copy {{
      min-height: 1.3em;
      color: var(--muted);
      margin-top: 10px;
    }}
    .entry-card {{
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255,255,255,0.03);
      display: grid;
      gap: 10px;
    }}
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      padding: 5px 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      font-size: 12px;
      color: var(--muted);
      background: rgba(255,255,255,0.04);
    }}
    .chip.accepted {{ color: var(--ok); border-color: rgba(148,240,191,0.28); }}
    .chip.regressed {{ color: var(--risk); border-color: rgba(255,176,176,0.28); }}
    .chip.steady {{ color: var(--warn); border-color: rgba(255,212,138,0.28); }}
    .action-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
    }}
    .meta div {{
      padding: 10px 12px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.02);
    }}
    .meta label {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      border-radius: 16px;
      padding: 14px;
      border: 1px solid var(--line);
      background: rgba(3, 10, 18, 0.9);
      color: #d7e8f4;
      overflow-x: auto;
    }}
    @media (max-width: 1080px) {{
      .span-4, .span-5, .span-7, .span-8 {{ grid-column: span 12; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="eyebrow">Level 3 Working Surface</div>
      <h1>JARVIS Failure &amp; Recovery</h1>
      <p>A dedicated recovery workspace for current integration failures, approval-gated fixes, recent failure signals, and next recovery actions. This turns Failure &amp; Recovery into a real app module instead of leaving it inside progress and command-center summaries.</p>
      <div class="actions">
        <a href="/command-center">Back to Command Center</a>
        <a href="/supervision-snapshot">Open Supervision Snapshot</a>
        <button type="button" id="refresh-recovery">Refresh Failure State</button>
      </div>
      <div class="stats">
        <div class="stat"><span>Status</span><strong id="hero-status">Loading...</strong></div>
        <div class="stat"><span>Integration Issues</span><strong id="hero-issues">0</strong></div>
        <div class="stat"><span>Pending Recovery Gates</span><strong id="hero-approvals">0</strong></div>
        <div class="stat"><span>Recent Failure Signals</span><strong id="hero-failures">0</strong></div>
        <div class="stat"><span>Dirty Lane</span><strong id="hero-dirty">0</strong></div>
      </div>
      <p class="detail-copy" id="recovery-status-note">Loading failure and recovery state…</p>
    </section>
    <div class="layout">
      <section class="panel span-7">
        <h2>Recovery Actions</h2>
        <div id="recovery-actions-list"></div>
      </section>
      <section class="panel span-5">
        <h2>Selected Recovery Detail</h2>
        <div id="recovery-detail"></div>
        <p class="detail-copy" id="recovery-action-note">Select a recovery item or resolve a pending gate to inspect the latest posture.</p>
      </section>
      <section class="panel span-4">
        <h2>Pending Recovery Gates</h2>
        <div id="approval-list"></div>
      </section>
      <section class="panel span-4">
        <h2>Integration Failures</h2>
        <div id="integration-list"></div>
      </section>
      <section class="panel span-4">
        <h2>Recent Failure Signals</h2>
        <div id="failure-list"></div>
      </section>
      <section class="panel span-12">
        <h2>Recovery Cases</h2>
        <div id="recovery-case-list"></div>
      </section>
      <section class="panel span-12">
        <h2>Recovery Continuity</h2>
        <div id="recovery-bridge-list"></div>
      </section>
      <section class="panel span-12">
        <h2>Recovery Action Journal</h2>
        <div id="recovery-journal-list"></div>
      </section>
      <section class="panel span-8">
        <h2>Proof Paths</h2>
        <ul id="proof-list"></ul>
      </section>
      <section class="panel span-4">
        <h2>Payload Preview</h2>
        <pre id="payload-preview"></pre>
      </section>
    </div>
  </main>
  <script>
    const initialPayload = {raw_json};
    let currentPayload = initialPayload;
    let currentSelection = {{ kind: "action", index: 0 }};

    const heroStatus = document.getElementById("hero-status");
    const heroIssues = document.getElementById("hero-issues");
    const heroApprovals = document.getElementById("hero-approvals");
    const heroFailures = document.getElementById("hero-failures");
    const heroDirty = document.getElementById("hero-dirty");
    const recoveryActionsList = document.getElementById("recovery-actions-list");
    const approvalList = document.getElementById("approval-list");
    const integrationList = document.getElementById("integration-list");
    const failureList = document.getElementById("failure-list");
    const recoveryCaseList = document.getElementById("recovery-case-list");
    const recoveryBridgeList = document.getElementById("recovery-bridge-list");
    const recoveryJournalList = document.getElementById("recovery-journal-list");
    const proofList = document.getElementById("proof-list");
    const recoveryDetail = document.getElementById("recovery-detail");
    const payloadPreview = document.getElementById("payload-preview");
    const statusNote = document.getElementById("recovery-status-note");
    const actionNote = document.getElementById("recovery-action-note");

    function esc(value) {{
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function li(title, summary, detail = "") {{
      return `<li><strong>${{esc(title)}}</strong><span>${{esc(summary)}}</span>${{detail ? `<span>${{esc(detail)}}</span>` : ""}}</li>`;
    }}

    function chip(label, klass = "") {{
      return `<span class="chip ${{esc(klass)}}">${{esc(label)}}</span>`;
    }}

    function listOrEmpty(items, renderItem, emptyTitle, emptyDetail) {{
      return items.length
        ? items.map(renderItem).join("")
        : `<div class="entry-card"><strong>${{esc(emptyTitle)}}</strong><span>${{esc(emptyDetail)}}</span></div>`;
    }}

    function routeLinks(routes) {{
      const entries = Array.isArray(routes) ? routes : [];
      return entries.map((item) => `
        <a href="${{esc(item.route || "/command-center")}}">${{esc(item.label || "Open Route")}}</a>
      `).join("");
    }}

    async function recordRecoveryAction(entry) {{
      const response = await fetch("/api/recovery/action", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(entry || {{}}),
      }});
      if (!response.ok) {{
        const payload = await response.json().catch(() => ({{}}));
        throw new Error(payload.detail || payload.error || "Recovery action record failed");
      }}
      return response.json().catch(() => ({{}}));
    }}

    async function stageRecoveryAction(actionType, targetKind, targetLabel, detail, targetId = "") {{
      actionNote.textContent = `${{actionType === "retry" ? "Staging retry" : "Marking stabilized"}} for ${{targetLabel}}…`;
      try {{
        await recordRecoveryAction({{
          action_type: actionType,
          target_kind: targetKind,
          target_label: targetLabel,
          target_id: targetId,
          detail,
          route: "/recovery-center",
          status: actionType === "retry" ? "queued" : "stabilized",
        }});
        await fetch("/api/activity/operator-action", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            actor: "Chris",
            domain: "recovery",
            action: actionType === "retry" ? "Stage Recovery Retry" : "Mark Recovery Stabilized",
            title: targetLabel,
            status: actionType === "retry" ? "queued" : "stabilized",
            detail: "Action succeeded: /api/recovery/action",
            why_now: detail,
            result_summary: actionType === "retry"
              ? `Recovery retry staged for ${{targetLabel}}.`
              : `Recovery item marked stabilized for ${{targetLabel}}.`,
            route: "/recovery-center",
            route_label: "Open Recovery Center",
            related_kind: "recovery",
            related_label: targetLabel,
            succeeded: true,
          }}),
        }}).catch(() => null);
        actionNote.textContent = actionType === "retry"
          ? `Staged retry for ${{targetLabel}}.`
          : `Marked ${{targetLabel}} as stabilized.`;
        await refreshRecoveryState();
      }} catch (error) {{
        actionNote.textContent = `Recovery action failed: ${{String(error)}}`;
      }}
    }}

    async function executeRecoveryCase(caseId, actionType, detail, fallbackLabel = "Recovery case") {{
      if (!caseId) return;
      actionNote.textContent = `${{actionType === "retry" ? "Executing retry loop" : "Stabilizing"}} for ${{fallbackLabel}}…`;
      try {{
        const response = await fetch(`/api/recovery/cases/${{encodeURIComponent(caseId)}}/execute`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            actor: "Chris",
            action_type: actionType,
            note: detail,
          }}),
        }});
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.detail || payload.error || "Recovery execution failed");
        }}
        const updatedCase = payload.case || {{}};
        actionNote.textContent = actionType === "retry"
          ? `Recovery retry loop executed for ${{updatedCase.title || fallbackLabel}}.`
          : `Recovery case moved into watch for ${{updatedCase.title || fallbackLabel}}.`;
        await refreshRecoveryState();
      }} catch (error) {{
        actionNote.textContent = `Recovery execution failed: ${{String(error)}}`;
      }}
    }}

    function selectedItem(payload) {{
      const failure = payload.failure_recovery || {{}};
      const pending = Array.isArray(payload.pending_approvals) ? payload.pending_approvals : [];
      const actions = Array.isArray(failure.action_items) ? failure.action_items : [];
      const integrations = Array.isArray(failure.failing_integrations) ? failure.failing_integrations : [];
      const recent = Array.isArray(failure.recent_failures) ? failure.recent_failures : [];
      const cases = Array.isArray(payload.recovery_cases) ? payload.recovery_cases : [];
      if (currentSelection.kind === "approval") return pending[currentSelection.index] || pending[0] || null;
      if (currentSelection.kind === "case") return cases[currentSelection.index] || cases[0] || null;
      if (currentSelection.kind === "integration") return integrations[currentSelection.index] || integrations[0] || null;
      if (currentSelection.kind === "failure") return recent[currentSelection.index] || recent[0] || null;
      return actions[currentSelection.index] || actions[0] || null;
    }}

    function renderDetail(payload) {{
      const item = selectedItem(payload);
      const failure = payload.failure_recovery || {{}};
      if (!item) {{
        recoveryDetail.innerHTML = "<p class=\\"detail-copy\\">No recovery detail available right now.</p>";
        return;
      }}
      const title = item.title || item.name || item.request_id || "Recovery item";
      const summary = item.detail || item.description || item.summary || "No recovery detail recorded.";
      const route = item.route || (payload.proof_paths || {{}}).supervision_route || "/supervision-snapshot";
      const relatedRoutes = Array.isArray(item.related_routes) ? item.related_routes : [];
      recoveryDetail.innerHTML = `
        <div class="entry-card">
          <strong>${{esc(title)}}</strong>
          <span>${{esc(summary)}}</span>
          <div class="chips">
            ${{item.request_id ? chip("approval gate", "steady") : ""}}
            ${{item.case_id ? chip(item.status_label || item.status || "case", item.status === "resolved" ? "accepted" : item.status === "watch" ? "steady" : "regressed") : ""}}
            ${{item.name ? chip("integration", "regressed") : ""}}
            ${{item.timestamp ? chip(item.timestamp, "steady") : ""}}
            ${{item.risk_tier ? chip(item.risk_tier, "steady") : ""}}
          </div>
          <div class="meta">
            <div><label>Pending Approvals</label><strong>${{esc(String(failure.pending_approval_count || 0))}}</strong></div>
            <div><label>Integration Issues</label><strong>${{esc(String(failure.integration_issue_count || 0))}}</strong></div>
            <div><label>Recent Failures</label><strong>${{esc(String(failure.recent_failure_count || 0))}}</strong></div>
            <div><label>Dirty Lane</label><strong>${{esc(String(failure.dirty_count || 0))}}</strong></div>
          </div>
          <div class="action-row">
            <a href="${{esc(route)}}">Open Recovery View</a>
            ${{routeLinks(relatedRoutes)}}
            ${{item.request_id ? `<button type="button" data-approve-id="${{esc(item.request_id)}}">Approve Recovery Gate</button>` : ""}}
            ${{item.request_id ? `<button type="button" data-execute-id="${{esc(item.request_id)}}" data-execute-label="${{esc(title)}}" data-execute-detail="${{esc(summary)}}">Execute Recovery Gate</button>` : ""}}
            ${{item.request_id ? `<button type="button" class="alt" data-reject-id="${{esc(item.request_id)}}">Reject Recovery Gate</button>` : ""}}
            ${{item.case_id ? `<button type="button" data-case-status="investigating" data-case-id="${{esc(item.case_id)}}">Mark Investigating</button>` : ""}}
            ${{item.case_id ? `<button type="button" class="alt" data-case-status="watch" data-case-id="${{esc(item.case_id)}}">Mark Watch</button>` : ""}}
            ${{item.case_id ? `<button type="button" class="alt" data-case-status="resolved" data-case-id="${{esc(item.case_id)}}">Mark Resolved</button>` : ""}}
            ${{item.case_id ? `<button type="button" data-case-execute="retry" data-case-id="${{esc(item.case_id)}}" data-case-label="${{esc(title)}}" data-case-detail="${{esc(summary)}}">Execute Retry Loop</button>` : ""}}
            ${{item.case_id ? `<button type="button" class="alt" data-case-execute="stabilize" data-case-id="${{esc(item.case_id)}}" data-case-label="${{esc(title)}}" data-case-detail="${{esc(summary)}}">Stabilize Recovery Loop</button>` : ""}}
            <button type="button" data-recovery-action="retry" data-recovery-kind="${{esc(item.request_id ? "approval" : item.name ? "integration" : "failure")}}" data-recovery-label="${{esc(title)}}" data-recovery-detail="${{esc(summary)}}" data-recovery-target-id="${{esc(item.request_id || "")}}">Stage Retry</button>
            <button type="button" class="alt" data-recovery-action="stabilize" data-recovery-kind="${{esc(item.request_id ? "approval" : item.name ? "integration" : "failure")}}" data-recovery-label="${{esc(title)}}" data-recovery-detail="${{esc(summary)}}">Mark Stabilized</button>
          </div>
        </div>
      `;
      document.querySelectorAll("[data-approve-id]").forEach((button) => {{
        button.addEventListener("click", () => {{
          resolveApproval(button.getAttribute("data-approve-id") || "", "approve").catch((error) => {{
            actionNote.textContent = `Approve failed: ${{String(error)}}`;
          }});
        }});
      }});
      document.querySelectorAll("[data-reject-id]").forEach((button) => {{
        button.addEventListener("click", () => {{
          resolveApproval(button.getAttribute("data-reject-id") || "", "reject").catch((error) => {{
            actionNote.textContent = `Reject failed: ${{String(error)}}`;
          }});
        }});
      }});
      document.querySelectorAll("[data-execute-id]").forEach((button) => {{
        button.addEventListener("click", () => {{
          resolveApproval(
            button.getAttribute("data-execute-id") || "",
            "execute",
            button.getAttribute("data-execute-label") || "Recovery gate",
            button.getAttribute("data-execute-detail") || "Recovery execution requested."
          ).catch((error) => {{
            actionNote.textContent = `Execute failed: ${{String(error)}}`;
          }});
        }});
      }});
      document.querySelectorAll("[data-recovery-action]").forEach((button) => {{
        button.addEventListener("click", () => {{
          stageRecoveryAction(
            button.getAttribute("data-recovery-action") || "retry",
            button.getAttribute("data-recovery-kind") || "recovery",
            button.getAttribute("data-recovery-label") || "Recovery item",
            button.getAttribute("data-recovery-detail") || "Recovery action requested.",
            button.getAttribute("data-recovery-target-id") || ""
          ).catch((error) => {{
            actionNote.textContent = `Recovery action failed: ${{String(error)}}`;
          }});
        }});
      }});
      document.querySelectorAll("[data-case-status]").forEach((button) => {{
        button.addEventListener("click", () => {{
          updateRecoveryCase(
            button.getAttribute("data-case-id") || "",
            button.getAttribute("data-case-status") || "investigating",
          ).catch((error) => {{
            actionNote.textContent = `Recovery case update failed: ${{String(error)}}`;
          }});
        }});
      }});
      document.querySelectorAll("[data-case-execute]").forEach((button) => {{
        button.addEventListener("click", () => {{
          executeRecoveryCase(
            button.getAttribute("data-case-id") || "",
            button.getAttribute("data-case-execute") || "retry",
            button.getAttribute("data-case-detail") || "Recovery execution requested.",
            button.getAttribute("data-case-label") || "Recovery case",
          ).catch((error) => {{
            actionNote.textContent = `Recovery execution failed: ${{String(error)}}`;
          }});
        }});
      }});
    }}

    function render(payload) {{
      currentPayload = payload || {{}};
      const failure = payload.failure_recovery || {{}};
      const actions = Array.isArray(failure.action_items) ? failure.action_items : [];
      const pending = Array.isArray(payload.pending_approvals) ? payload.pending_approvals : [];
      const integrations = Array.isArray(failure.failing_integrations) ? failure.failing_integrations : [];
      const recent = Array.isArray(failure.recent_failures) ? failure.recent_failures : [];
      const cases = Array.isArray(payload.recovery_cases) ? payload.recovery_cases : [];
      const proofs = payload.proof_paths || {{}};

      heroStatus.textContent = payload.status || "Wired";
      heroIssues.textContent = String(failure.integration_issue_count || 0);
      heroApprovals.textContent = String(failure.pending_approval_count || 0);
      heroFailures.textContent = String(failure.recent_failure_count || 0);
      heroDirty.textContent = String(failure.dirty_count || 0);
      statusNote.textContent = payload.summary || "No recovery summary captured yet.";

      recoveryActionsList.innerHTML = listOrEmpty(
        actions,
        (item, index) => `
          <div class="entry-card">
            <strong>${{esc(item.title || "Recovery Action")}}</strong>
            <span>${{esc(item.detail || "No recovery detail recorded.")}}</span>
            <div class="action-row">
              <button type="button" data-select-kind="action" data-select-index="${{esc(String(index))}}">Inspect Recovery Item</button>
              ${{routeLinks(item.related_routes)}}
            </div>
          </div>
        `,
        "Recovery posture is stable.",
        "No active recovery actions are currently surfaced."
      );

      approvalList.innerHTML = listOrEmpty(
        pending,
        (item, index) => `
          <div class="entry-card">
            <strong>${{esc(item.title || item.request_id || "Pending Approval")}}</strong>
            <span>${{esc(item.description || "Approval-gated recovery action.")}}</span>
            <div class="chips">
              ${{chip(item.risk_tier || "pending", "steady")}}
              ${{item.agent_label ? chip(item.agent_label) : ""}}
            </div>
            <div class="action-row">
              <button type="button" data-select-kind="approval" data-select-index="${{esc(String(index))}}">Inspect Recovery Gate</button>
              <button type="button" data-approve-id="${{esc(item.request_id || "")}}">Approve Recovery Gate</button>
              <button type="button" data-execute-id="${{esc(item.request_id || "")}}" data-execute-label="${{esc(item.title || item.request_id || "Recovery Gate")}}" data-execute-detail="${{esc(item.description || "Recovery-gated execution requested.")}}">Execute Recovery Gate</button>
              <button type="button" class="alt" data-reject-id="${{esc(item.request_id || "")}}">Reject</button>
              ${{routeLinks(item.related_routes)}}
            </div>
          </div>
        `,
        "No pending recovery gates.",
        "Approvals that block recovery work will appear here."
      );

      integrationList.innerHTML = listOrEmpty(
        integrations,
        (item, index) => `
          <div class="entry-card">
            <strong>${{esc(item.name || "Integration")}}</strong>
            <span>${{esc(item.detail || "Integration needs review.")}}</span>
            <div class="action-row">
              <button type="button" data-select-kind="integration" data-select-index="${{esc(String(index))}}">Inspect Integration</button>
              ${{routeLinks(item.related_routes)}}
            </div>
          </div>
        `,
        "No active integration failures.",
        "Broken connectors and runtime integrations will surface here."
      );

      failureList.innerHTML = listOrEmpty(
        recent,
        (item, index) => `
          <div class="entry-card">
            <strong>${{esc(item.title || "Failure Signal")}}</strong>
            <span>${{esc(item.detail || "No failure detail recorded.")}}</span>
            <div class="chips">${{item.timestamp ? chip(item.timestamp, "steady") : ""}}</div>
            <div class="action-row">
              <button type="button" data-select-kind="failure" data-select-index="${{esc(String(index))}}">Inspect Failure Signal</button>
              <button type="button" data-recovery-action="retry" data-recovery-kind="failure" data-recovery-label="${{esc(item.title || "Failure Signal")}}" data-recovery-detail="${{esc(item.detail || "No failure detail recorded.")}}" data-recovery-target-id="">Stage Retry</button>
              ${{routeLinks(item.related_routes)}}
            </div>
          </div>
        `,
        "No recent failure signals.",
        "Recent runtime failures and rollback signals will appear here."
      );

      recoveryCaseList.innerHTML = listOrEmpty(
        cases,
        (item, index) => `
          <div class="entry-card">
            <strong>${{esc(item.title || "Recovery case")}}</strong>
            <span>${{esc(item.detail || "Durable recovery case is ready for review.")}}</span>
            <div class="chips">
              ${{chip(item.status_label || item.status || "Open", item.status === "resolved" ? "accepted" : item.status === "watch" ? "steady" : "regressed")}}
              ${{item.source_kind ? chip(item.source_kind.replaceAll("-", " ")) : ""}}
              ${{item.last_action_at ? chip(item.last_action_at, "steady") : ""}}
              ${{Number(item.execution_count || 0) > 0 ? chip(`executions ${{String(item.execution_count)}}`, "steady") : ""}}
            </div>
            <div class="action-row">
              <button type="button" data-select-kind="case" data-select-index="${{esc(String(index))}}">Inspect Case</button>
              <button type="button" data-case-status="investigating" data-case-id="${{esc(item.case_id || "")}}">Mark Investigating</button>
              <button type="button" class="alt" data-case-status="watch" data-case-id="${{esc(item.case_id || "")}}">Mark Watch</button>
              <button type="button" class="alt" data-case-status="resolved" data-case-id="${{esc(item.case_id || "")}}">Mark Resolved</button>
              <button type="button" data-case-execute="retry" data-case-id="${{esc(item.case_id || "")}}" data-case-label="${{esc(item.title || "Recovery case")}}" data-case-detail="${{esc(item.detail || "Recovery retry requested.")}}">Execute Retry Loop</button>
              <button type="button" class="alt" data-case-execute="stabilize" data-case-id="${{esc(item.case_id || "")}}" data-case-label="${{esc(item.title || "Recovery case")}}" data-case-detail="${{esc(item.detail || "Recovery stabilization requested.")}}">Stabilize Recovery Loop</button>
              <a href="${{esc(item.related_route || "/recovery-center")}}">Open Related Surface</a>
            </div>
          </div>
        `,
        "No durable recovery cases yet.",
        "Integration and failure signals will open durable recovery cases here."
      );

      const recoveryBridge = ((payload.recovery_actions || {{}}).recent) || [];
      recoveryBridgeList.innerHTML = listOrEmpty(
        recoveryBridge,
        (item) => `
          <div class="entry-card">
            <strong>${{esc(item.target_label || "Recovery continuity item")}}</strong>
            <span>${{esc(item.detail || "Recovery continuity recorded.")}}</span>
            <div class="chips">
              ${{chip(item.target_kind || "recovery", "steady")}}
              ${{chip(item.action_type || "review", "steady")}}
              ${{chip(item.status || "queued")}}
            </div>
            <div class="action-row">
              ${{item.target_kind === "approval" && item.target_id ? `<button type="button" data-execute-id="${{esc(item.target_id)}}" data-execute-label="${{esc(item.target_label || "Recovery Gate")}}" data-execute-detail="${{esc(item.detail || "Recovery execution requested.")}}">Execute Recovery Gate</button>` : ""}}
              ${{routeLinks(item.related_routes)}}
            </div>
          </div>
        `,
        "No recovery continuity recorded yet.",
        "Durable recovery actions will surface here with links back into the related approval, supervision, activity, and command-center routes."
      );

      const recoveryActions = ((payload.recovery_actions || {{}}).recent) || [];
      recoveryJournalList.innerHTML = listOrEmpty(
        recoveryActions,
        (item) => `
          <div class="entry-card">
            <strong>${{esc(item.target_label || "Recovery action")}}</strong>
            <span>${{esc(item.detail || "Recovery action recorded.")}}</span>
            <div class="chips">
              ${{chip(item.action_type || "review", "steady")}}
              ${{chip(item.status || "queued")}}
              ${{item.saved_at ? chip(item.saved_at, "steady") : ""}}
            </div>
            <div class="action-row">
              ${{item.target_kind === "approval" && item.target_id ? `<button type="button" data-execute-id="${{esc(item.target_id)}}" data-execute-label="${{esc(item.target_label || "Recovery Gate")}}" data-execute-detail="${{esc(item.detail || "Recovery execution requested.")}}">Execute Recovery Gate</button>` : ""}}
              ${{routeLinks(item.related_routes)}}
            </div>
          </div>
        `,
        "No recovery actions recorded yet.",
        "Stage retries or mark items stabilized to build a durable recovery execution history."
      );

      proofList.innerHTML = Object.entries(proofs).map(([key, value]) => li(key, value)).join("");
      payloadPreview.textContent = JSON.stringify(payload, null, 2);

      document.querySelectorAll("[data-select-kind]").forEach((button) => {{
        button.addEventListener("click", () => {{
          currentSelection = {{
            kind: button.getAttribute("data-select-kind") || "action",
            index: Number(button.getAttribute("data-select-index") || "0"),
          }};
          renderDetail(payload);
          actionNote.textContent = `Focused ${{currentSelection.kind}} detail for review.`;
        }});
      }});
      document.querySelectorAll("[data-approve-id]").forEach((button) => {{
        button.addEventListener("click", () => {{
          resolveApproval(button.getAttribute("data-approve-id") || "", "approve").catch((error) => {{
            actionNote.textContent = `Approve failed: ${{String(error)}}`;
          }});
        }});
      }});
      document.querySelectorAll("[data-reject-id]").forEach((button) => {{
        button.addEventListener("click", () => {{
          resolveApproval(button.getAttribute("data-reject-id") || "", "reject").catch((error) => {{
            actionNote.textContent = `Reject failed: ${{String(error)}}`;
          }});
        }});
      }});
      document.querySelectorAll("[data-execute-id]").forEach((button) => {{
        button.addEventListener("click", () => {{
          resolveApproval(
            button.getAttribute("data-execute-id") || "",
            "execute",
            button.getAttribute("data-execute-label") || "Recovery gate",
            button.getAttribute("data-execute-detail") || "Recovery execution requested."
          ).catch((error) => {{
            actionNote.textContent = `Execute failed: ${{String(error)}}`;
          }});
        }});
      }});
      document.querySelectorAll("[data-recovery-action]").forEach((button) => {{
        button.addEventListener("click", () => {{
          stageRecoveryAction(
            button.getAttribute("data-recovery-action") || "retry",
            button.getAttribute("data-recovery-kind") || "recovery",
            button.getAttribute("data-recovery-label") || "Recovery item",
            button.getAttribute("data-recovery-detail") || "Recovery action requested.",
            button.getAttribute("data-recovery-target-id") || ""
          ).catch((error) => {{
            actionNote.textContent = `Recovery action failed: ${{String(error)}}`;
          }});
        }});
      }});
      document.querySelectorAll("[data-case-status]").forEach((button) => {{
        button.addEventListener("click", () => {{
          updateRecoveryCase(
            button.getAttribute("data-case-id") || "",
            button.getAttribute("data-case-status") || "investigating",
          ).catch((error) => {{
            actionNote.textContent = `Recovery case update failed: ${{String(error)}}`;
          }});
        }});
      }});
      document.querySelectorAll("[data-case-execute]").forEach((button) => {{
        button.addEventListener("click", () => {{
          executeRecoveryCase(
            button.getAttribute("data-case-id") || "",
            button.getAttribute("data-case-execute") || "retry",
            button.getAttribute("data-case-detail") || "Recovery execution requested.",
            button.getAttribute("data-case-label") || "Recovery case",
          ).catch((error) => {{
            actionNote.textContent = `Recovery execution failed: ${{String(error)}}`;
          }});
        }});
      }});

      renderDetail(payload);
    }}

    async function refreshRecoveryState() {{
      statusNote.textContent = "Refreshing failure and recovery state…";
      try {{
        const response = await fetch("/api/recovery/module");
        const payload = await response.json();
        render(payload);
        statusNote.textContent = payload.summary || "Failure and recovery module refreshed.";
      }} catch (error) {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }}
    }}

    async function resolveApproval(requestId, action, targetLabel = "", targetDetail = "") {{
      if (!requestId) return;
      const actionVerb = action === "approve" ? "Approving" : action === "execute" ? "Executing" : "Rejecting";
      actionNote.textContent = `${{actionVerb}} recovery gate ${{requestId}}…`;
      const endpoint = action === "approve"
        ? `/api/approvals/${{encodeURIComponent(requestId)}}/approve`
        : action === "execute"
          ? `/api/approvals/${{encodeURIComponent(requestId)}}/execute`
          : `/api/approvals/${{encodeURIComponent(requestId)}}/reject`;
      const body = action === "approve"
        ? {{ approved_by: "Chris" }}
        : action === "reject"
          ? {{ reason: "Needs more recovery review", rejected_by: "Chris" }}
          : undefined;
      try {{
        const response = await fetch(endpoint, {{
          method: "POST",
          headers: body ? {{ "Content-Type": "application/json" }} : {{}},
          body: body ? JSON.stringify(body) : undefined,
        }});
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.detail || payload.error || `${{action}} failed`);
        }}
        const recoveryLabel = targetLabel || `Recovery gate ${{requestId}}`;
        const recoveryDetail = targetDetail || `Recovery gate ${{requestId}} ${{
          action === "execute" ? "execution requested" : action
        }}.`;
        const status = String(payload.status || action || "recorded");
        await recordRecoveryAction({{
          action_type: action,
          target_kind: "approval",
          target_label: recoveryLabel,
          target_id: requestId,
          detail: recoveryDetail,
          route: "/recovery-center",
          status,
        }});
        await fetch("/api/activity/operator-action", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            actor: "Chris",
            domain: "recovery",
            action: action === "approve"
              ? "Approve Recovery Gate"
              : action === "execute"
                ? "Execute Recovery Gate"
                : "Reject Recovery Gate",
            title: recoveryLabel,
            status,
            detail: `Action succeeded: ${{endpoint}}`,
            why_now: recoveryDetail,
            result_summary: action === "execute"
              ? `Recovery gate executed for ${{recoveryLabel}}.`
              : action === "approve"
                ? `Recovery gate approved for ${{recoveryLabel}}.`
                : `Recovery gate rejected for ${{recoveryLabel}}.`,
            route: "/recovery-center",
            route_label: "Open Recovery Center",
            related_kind: "recovery",
            related_label: recoveryLabel,
            succeeded: true,
          }}),
        }}).catch(() => null);
        actionNote.textContent = action === "approve"
          ? `Approved recovery gate ${{requestId}}.`
          : action === "execute"
            ? `Executed recovery gate ${{requestId}}.`
            : `Rejected recovery gate ${{requestId}}.`;
        await refreshRecoveryState();
      }} catch (error) {{
        actionNote.textContent = `${{action === "approve" ? "Approve" : action === "execute" ? "Execute" : "Reject"}} failed: ${{String(error)}}`;
      }}
    }}

    async function updateRecoveryCase(caseId, status) {{
      if (!caseId) return;
      actionNote.textContent = `Updating recovery case ${{caseId}} to ${{status}}…`;
      try {{
        const response = await fetch(`/api/recovery/cases/${{encodeURIComponent(caseId)}}`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            actor: "Chris",
            status,
            note: `Recovery case moved to ${{status}} from the Recovery Center.`,
          }}),
        }});
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.detail || payload.error || "Recovery case update failed");
        }}
        const updatedCase = payload.case || {{}};
        actionNote.textContent = `Recovery case ${{updatedCase.title || caseId}} is now ${{updatedCase.status_label || status}}.`;
        await refreshRecoveryState();
      }} catch (error) {{
        actionNote.textContent = `Recovery case update failed: ${{String(error)}}`;
      }}
    }}

    document.getElementById("refresh-recovery").addEventListener("click", () => {{
      refreshRecoveryState().catch((error) => {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }});
    }});

    render(initialPayload);
  </script>
</body>
</html>
"""


def render_mission_board_module_page(payload: dict) -> str:
    raw_json = json.dumps(payload, indent=2)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Mission and Task Board</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #071019;
      --bg-2: #0a1624;
      --panel: rgba(10, 21, 34, 0.9);
      --line: rgba(121, 216, 255, 0.14);
      --text: #edf8ff;
      --muted: #97b5cb;
      --accent: #79d8ff;
      --ok: #94f0bf;
      --warn: #ffd48a;
      --risk: #ffb0b0;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "SF Pro Display", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top, rgba(121, 216, 255, 0.14), transparent 36%),
        linear-gradient(180deg, #040b12 0%, var(--bg) 44%, var(--bg-2) 100%);
      color: var(--text);
    }}
    .shell {{ max-width: 1480px; margin: 0 auto; padding: 36px 24px 60px; }}
    .hero {{
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 28px;
      background: linear-gradient(180deg, rgba(11, 24, 38, 0.94), rgba(7, 17, 28, 0.92));
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.28);
    }}
    .eyebrow {{ color: var(--accent); letter-spacing: 0.18em; text-transform: uppercase; font-size: 12px; }}
    h1 {{ margin: 10px 0 12px; font-size: clamp(34px, 5vw, 56px); }}
    h2 {{ margin: 0 0 14px; font-size: 18px; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    a, button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(121, 216, 255, 0.12);
      color: var(--text);
      text-decoration: none;
      font: inherit;
      cursor: pointer;
    }}
    button.alt {{ background: rgba(255,255,255,0.04); }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 22px;
    }}
    .stat, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
    }}
    .stat span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .stat strong {{ display: block; margin-top: 6px; font-size: 24px; }}
    .layout {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .span-4 {{ grid-column: span 4; }}
    .span-5 {{ grid-column: span 5; }}
    .span-7 {{ grid-column: span 7; }}
    .span-8 {{ grid-column: span 8; }}
    .span-12 {{ grid-column: span 12; }}
    .board-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
    }}
    .lane {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: rgba(255,255,255,0.02);
      display: grid;
      gap: 10px;
      min-height: 220px;
    }}
    .lane h3 {{
      margin: 0;
      font-size: 14px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--accent);
    }}
    .mission-card {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
      display: grid;
      gap: 8px;
    }}
    .mission-card strong {{ display: block; }}
    .mission-card span {{ color: var(--muted); display: block; }}
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      padding: 5px 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      font-size: 12px;
      color: var(--muted);
      background: rgba(255,255,255,0.04);
    }}
    .chip.accepted {{ color: var(--ok); border-color: rgba(148,240,191,0.28); }}
    .chip.regressed {{ color: var(--risk); border-color: rgba(255,176,176,0.28); }}
    .chip.steady {{ color: var(--warn); border-color: rgba(255,212,138,0.28); }}
    .action-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
    }}
    .meta div {{
      padding: 10px 12px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.02);
    }}
    .meta label {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
    }}
    ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    li {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
    }}
    li strong {{ display: block; margin-bottom: 4px; }}
    li span {{ color: var(--muted); display: block; }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      border-radius: 16px;
      padding: 14px;
      border: 1px solid var(--line);
      background: rgba(3, 10, 18, 0.9);
      color: #d7e8f4;
      overflow-x: auto;
    }}
    .status-note {{
      min-height: 1.3em;
      color: var(--muted);
      margin-top: 10px;
    }}
    @media (max-width: 1180px) {{
      .board-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 980px) {{
      .span-4, .span-5, .span-7, .span-8, .span-12 {{ grid-column: span 12; }}
      .board-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="eyebrow">Level 3 Working Surface</div>
      <h1>JARVIS Mission &amp; Task Board</h1>
      <p>A dedicated mission workspace for live now/next/blocked/completed missions, selected-agent context, task-agent context, and mission lane changes. This turns the mission board into a real app module instead of leaving it only in the command center.</p>
      <div class="actions">
        <a href="/command-center">Back to Command Center</a>
        <button type="button" id="refresh-mission-board">Refresh Mission Board</button>
      </div>
      <div class="stats">
        <div class="stat"><span>Status</span><strong id="hero-status">Loading...</strong></div>
        <div class="stat"><span>Now</span><strong id="hero-now">0</strong></div>
        <div class="stat"><span>Next</span><strong id="hero-next">0</strong></div>
        <div class="stat"><span>Blocked</span><strong id="hero-blocked">0</strong></div>
        <div class="stat"><span>Completed</span><strong id="hero-completed">0</strong></div>
      </div>
      <p class="status-note" id="mission-status-note">Loading mission board state…</p>
    </section>
    <div class="layout">
      <section class="panel span-12">
        <h2>Mission Authoring</h2>
        <div id="mission-authoring"></div>
      </section>
      <section class="panel span-12">
        <h2>Mission Lanes</h2>
        <div id="mission-board" class="board-grid"></div>
      </section>
      <section class="panel span-7">
        <h2>Selected Mission Detail</h2>
        <div id="mission-detail"></div>
        <p class="status-note" id="mission-action-note">Select a mission or change its lane to inspect the current board posture.</p>
      </section>
      <section class="panel span-5">
        <h2>Mission Evidence</h2>
        <ul id="mission-evidence-list"></ul>
      </section>
      <section class="panel span-12">
        <h2>Mission Workspaces</h2>
        <div id="mission-workspaces" class="board-grid"></div>
      </section>
      <section class="panel span-12">
        <h2>Handoff Console</h2>
        <div id="mission-handoffs" class="board-grid"></div>
      </section>
      <section class="panel span-4">
        <h2>Recent Mission Continuity</h2>
        <ul id="mission-activity-list"></ul>
      </section>
      <section class="panel span-8">
        <h2>Mission API Proof</h2>
        <ul id="proof-list"></ul>
      </section>
      <section class="panel span-4">
        <h2>Payload Preview</h2>
        <pre id="payload-preview"></pre>
      </section>
    </div>
  </main>
  <script>
    const initialPayload = {raw_json};
    let currentPayload = initialPayload;
    let selectedMissionId = "";

    const heroStatus = document.getElementById("hero-status");
    const heroNow = document.getElementById("hero-now");
    const heroNext = document.getElementById("hero-next");
    const heroBlocked = document.getElementById("hero-blocked");
    const heroCompleted = document.getElementById("hero-completed");
    const authoringEl = document.getElementById("mission-authoring");
    const boardEl = document.getElementById("mission-board");
    const detailEl = document.getElementById("mission-detail");
    const evidenceEl = document.getElementById("mission-evidence-list");
    const workspacesEl = document.getElementById("mission-workspaces");
    const handoffsEl = document.getElementById("mission-handoffs");
    const missionActivityEl = document.getElementById("mission-activity-list");
    const proofEl = document.getElementById("proof-list");
    const payloadPreview = document.getElementById("payload-preview");
    const statusNote = document.getElementById("mission-status-note");
    const actionNote = document.getElementById("mission-action-note");

    function esc(value) {{
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function li(title, summary, detail = "") {{
      return `<li><strong>${{esc(title)}}</strong><span>${{esc(summary)}}</span>${{detail ? `<span>${{esc(detail)}}</span>` : ""}}</li>`;
    }}

    function chip(label, klass = "") {{
      return `<span class="chip ${{esc(klass)}}">${{esc(label)}}</span>`;
    }}

    function missions(payload) {{
      return Array.isArray((payload.mission_task_board || {{}}).items) ? payload.mission_task_board.items : [];
    }}

    function currentMission(payload) {{
      const items = missions(payload);
      return items.find((item) => item.mission_id === selectedMissionId) || items[0] || null;
    }}

    function currentMissionDetail(payload) {{
      const mission = currentMission(payload);
      if (!mission || !mission.mission_id) return null;
      const details = payload.mission_details || {{}};
      return details[mission.mission_id] || null;
    }}

    function missionAgentProfiles(detail) {{
      return Array.isArray(detail?.agent_profiles) ? detail.agent_profiles : [];
    }}

    function missionAgentOptions(detail, workState) {{
      const options = new Map();
      missionAgentProfiles(detail).forEach((profile) => {{
        const agentId = String(profile?.agent_id || profile?.id || "").trim();
        if (!agentId) return;
        const label = String(profile?.display_name || profile?.name || profile?.role || agentId).trim() || agentId;
        options.set(agentId, label);
      }});
      Object.entries((workState || {{}}).agent_work_states || {{}}).forEach(([agentId, workspace]) => {{
        const cleanId = String(agentId || "").trim();
        if (!cleanId || options.has(cleanId)) return;
        options.set(cleanId, String(workspace?.role || cleanId).trim() || cleanId);
      }});
      return Array.from(options.entries()).map(([value, label]) => ({{ value, label }}));
    }}

    function selectOptions(options, selected = "") {{
      return options.map((item) => {{
        const value = String(item?.value || "").trim();
        const label = String(item?.label || value).trim() || value;
        const isSelected = value && value === String(selected || "").trim() ? " selected" : "";
        return `<option value="${{esc(value)}}"${{isSelected}}>${{esc(label)}}</option>`;
      }}).join("");
    }}

    async function recordMissionActivity(payload) {{
      try {{
        const response = await fetch("/api/activity/operator-action", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload || {{}}),
        }});
        if (!response.ok) return false;
        await response.json().catch(() => ({{}}));
        return true;
      }} catch (_error) {{
        return false;
      }}
    }}

    async function updateAgentWorkspace(missionId, agentId, status, workspace) {{
      if (!missionId || !agentId) return;
      const focusInput = document.querySelector(`[data-workspace-focus="${{agentId}}"]`);
      const noteInput = document.querySelector(`[data-workspace-note="${{agentId}}"]`);
      const currentFocus = String(focusInput?.value || workspace?.current_focus || "").trim();
      const note = String(noteInput?.value || "").trim();
      actionNote.textContent = `Updating workspace for ${{agentId}}…`;
      try {{
        const response = await fetch(`/api/missions/${{encodeURIComponent(missionId)}}/agents/${{encodeURIComponent(agentId)}}/work-state`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            status,
            current_focus: currentFocus,
            note: note || `Updated from mission board workspace control to ${{status}}.`,
          }}),
        }});
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.detail || payload.error || "Mission workspace update failed");
        }}
        const recorded = await recordMissionActivity({{
          actor: "Chris",
          domain: "mission-board",
          action: "Update Mission Workspace",
          title: workspace?.role || agentId,
          status: status || "updated",
          detail: `Action succeeded: /api/missions/${{missionId}}/agents/${{agentId}}/work-state`,
          why_now: currentFocus || note || `Mission workspace for ${{agentId}} changed to ${{status}}.`,
          result_summary: `Workspace update result: ${{status || "updated"}}`,
          route: "/mission-board",
          route_label: "Open Mission Board",
          related_kind: "mission",
          related_label: missionId,
          succeeded: true,
        }});
        actionNote.textContent = recorded
          ? `Updated workspace for ${{agentId}} to ${{status}} and recorded it in shared activity.`
          : `Updated workspace for ${{agentId}} to ${{status}}.`;
        await refreshMissionBoard();
      }} catch (error) {{
        const errorText = String(error);
        await recordMissionActivity({{
          actor: "Chris",
          domain: "mission-board",
          action: "Update Mission Workspace",
          title: workspace?.role || agentId,
          status: "failed",
          detail: `Action failed: /api/missions/${{missionId}}/agents/${{agentId}}/work-state`,
          why_now: errorText,
          result_summary: `Workspace update failed: ${{errorText}}`,
          route: "/mission-board",
          route_label: "Open Mission Board",
          related_kind: "mission",
          related_label: missionId,
          succeeded: false,
        }});
        actionNote.textContent = `Mission workspace update failed: ${{errorText}}`;
      }}
    }}

    async function updateMissionStatus(missionId, status) {{
      if (!missionId) return;
      const mission = currentMission(currentPayload) || {{}};
      const actionLabel = {{
        active: "Move Mission to Now",
        blocked: "Mark Mission Blocked",
        completed: "Mark Mission Completed",
      }}[String(status || "").trim()] || "Update Mission Status";
      actionNote.textContent = `Updating mission ${{missionId}} to ${{status}}…`;
      try {{
        const response = await fetch(`/api/missions/${{encodeURIComponent(missionId)}}/status`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            status,
            note: `Updated from mission board module to ${{status}}`,
          }}),
        }});
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.detail || payload.error || "Mission status update failed");
        }}
        const recorded = await recordMissionActivity({{
          actor: "Chris",
          domain: "mission-board",
          action: actionLabel,
          title: mission.title || missionId,
          status: String(payload.status || payload.result || status || "ok"),
          detail: `Action succeeded: /api/missions/${{missionId}}/status`,
          why_now: mission.next_step || mission.brief || `Mission board changed ${{missionId}} to ${{status}}.`,
          result_summary: `Mission action result: ${{String(payload.status || payload.result || status || "ok")}}`,
          route: "/mission-board",
          route_label: "Open Mission Board",
          related_kind: "mission",
          related_label: mission.title || missionId,
          succeeded: true,
        }});
        actionNote.textContent = recorded
          ? `Mission ${{missionId}} updated to ${{status}} and recorded in shared activity.`
          : `Mission ${{missionId}} updated to ${{status}}.`;
        await refreshMissionBoard();
      }} catch (error) {{
        const errorText = String(error);
        await recordMissionActivity({{
          actor: "Chris",
          domain: "mission-board",
          action: actionLabel,
          title: mission.title || missionId,
          status: "failed",
          detail: `Action failed: ${{errorText}}`,
          why_now: `Mission board failed to change ${{missionId}} to ${{status}}.`,
          result_summary: "Mission action failed before the mission board refresh completed.",
          route: "/mission-board",
          route_label: "Open Mission Board",
          related_kind: "mission",
          related_label: mission.title || missionId,
          succeeded: false,
        }});
        actionNote.textContent = `Mission status update failed: ${{errorText}}`;
      }}
    }}

    async function updateMissionDetails(missionId) {{
      if (!missionId) return;
      const title = String(document.getElementById("mission-edit-title")?.value || "").trim();
      const brief = String(document.getElementById("mission-edit-brief")?.value || "").trim();
      const request = String(document.getElementById("mission-edit-request")?.value || "").trim();
      const nextStep = String(document.getElementById("mission-edit-next-step")?.value || "").trim();
      const note = String(document.getElementById("mission-edit-note")?.value || "").trim();
      if (!title && !brief && !request && !nextStep) {{
        actionNote.textContent = "Change at least one mission detail before saving edits.";
        return;
      }}
      actionNote.textContent = `Saving mission detail changes for ${{missionId}}…`;
      try {{
        const response = await fetch(`/api/missions/${{encodeURIComponent(missionId)}}/edit`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            title,
            brief,
            request,
            next_step: nextStep,
            note,
          }}),
        }});
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.detail || payload.error || "Mission detail update failed");
        }}
        const recorded = await recordMissionActivity({{
          actor: "Chris",
          domain: "mission-board",
          action: "Edit Mission Details",
          title: title || String(payload.title || missionId).trim() || missionId,
          status: String(payload.status || "updated").trim() || "updated",
          detail: `Action succeeded: /api/missions/${{missionId}}/edit`,
          why_now: note || brief || request || nextStep || "Mission detail changed from the Mission Board.",
          result_summary: `Mission ${{missionId}} detail is now updated in the shared mission substrate.`,
          route: "/mission-board",
          route_label: "Open Mission Board",
          related_kind: "mission",
          related_label: missionId,
          succeeded: true,
        }});
        actionNote.textContent = recorded
          ? `Saved mission detail changes for ${{missionId}} and recorded them in shared activity.`
          : `Saved mission detail changes for ${{missionId}}.`;
        await refreshMissionBoard();
      }} catch (error) {{
        const errorText = String(error);
        await recordMissionActivity({{
          actor: "Chris",
          domain: "mission-board",
          action: "Edit Mission Details",
          title: missionId,
          status: "failed",
          detail: `Action failed: /api/missions/${{missionId}}/edit`,
          why_now: errorText,
          result_summary: `Mission detail update failed: ${{errorText}}`,
          route: "/mission-board",
          route_label: "Open Mission Board",
          related_kind: "mission",
          related_label: missionId,
          succeeded: false,
        }});
        actionNote.textContent = `Mission detail update failed: ${{errorText}}`;
      }}
    }}

    async function createMissionHandoff(missionId) {{
      if (!missionId) return;
      const detail = currentMissionDetail(currentPayload) || {{}};
      const fromAgent = String(document.getElementById("handoff-from-agent")?.value || "").trim();
      const toAgent = String(document.getElementById("handoff-to-agent")?.value || "").trim();
      const taskTitle = String(document.getElementById("handoff-task-title")?.value || "").trim();
      const summary = String(document.getElementById("handoff-summary")?.value || "").trim();
      const partialWork = String(document.getElementById("handoff-partial-work")?.value || "").trim();
      const transferOwnership = Boolean(document.getElementById("handoff-transfer-ownership")?.checked);
      if (!fromAgent || !toAgent || !taskTitle || !summary) {{
        actionNote.textContent = "Choose from/to agents and provide both a task title and summary before creating a handoff.";
        return;
      }}
      if (fromAgent === toAgent) {{
        actionNote.textContent = "Handoffs need different source and receiving agents.";
        return;
      }}
      actionNote.textContent = `Creating handoff from ${{fromAgent}} to ${{toAgent}}…`;
      try {{
        const response = await fetch(`/api/missions/${{encodeURIComponent(missionId)}}/handoffs`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            from_agent: fromAgent,
            to_agent: toAgent,
            task_title: taskTitle,
            summary,
            partial_work: partialWork,
            context: String(document.getElementById("handoff-context")?.value || "").trim(),
            delegation_reason: String(document.getElementById("handoff-reason")?.value || "").trim(),
            expected_result: String(document.getElementById("handoff-expected-result")?.value || "").trim(),
            duplicate_key: String(document.getElementById("handoff-duplicate-key")?.value || "").trim(),
            transfer_ownership: transferOwnership,
          }}),
        }});
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.detail || payload.error || "Mission handoff creation failed");
        }}
        const recorded = await recordMissionActivity({{
          actor: "Chris",
          domain: "mission-board",
          action: transferOwnership ? "Transfer Mission Ownership" : "Create Mission Handoff",
          title: taskTitle,
          status: transferOwnership ? "pending-acceptance" : "pending",
          detail: `Action succeeded: /api/missions/${{missionId}}/handoffs`,
          why_now: summary,
          result_summary: `Handoff from ${{fromAgent}} to ${{toAgent}} is now live in the mission substrate.`,
          route: "/mission-board",
          route_label: "Open Mission Board",
          related_kind: "mission",
          related_label: missionId,
          succeeded: true,
        }});
        actionNote.textContent = recorded
          ? `Created the handoff from ${{fromAgent}} to ${{toAgent}} and recorded it in shared activity.`
          : `Created the handoff from ${{fromAgent}} to ${{toAgent}}.`;
        await refreshMissionBoard();
      }} catch (error) {{
        const errorText = String(error);
        await recordMissionActivity({{
          actor: "Chris",
          domain: "mission-board",
          action: "Create Mission Handoff",
          title: taskTitle || detail?.title || missionId,
          status: "failed",
          detail: `Action failed: /api/missions/${{missionId}}/handoffs`,
          why_now: errorText,
          result_summary: `Mission handoff creation failed: ${{errorText}}`,
          route: "/mission-board",
          route_label: "Open Mission Board",
          related_kind: "mission",
          related_label: missionId,
          succeeded: false,
        }});
        actionNote.textContent = `Mission handoff creation failed: ${{errorText}}`;
      }}
    }}

    async function createMission() {{
      const actor = String(document.getElementById("mission-author-actor")?.value || "Chris").trim() || "Chris";
      const room = String(document.getElementById("mission-author-room")?.value || "office").trim() || "office";
      const request = String(document.getElementById("mission-author-request")?.value || "").trim();
      if (!request) {{
        actionNote.textContent = "Add a mission request before creating a mission.";
        return;
      }}
      actionNote.textContent = "Creating a new mission from the Mission Board…";
      try {{
        const response = await fetch("/api/missions", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            actor,
            room,
            request,
          }}),
        }});
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.detail || payload.error || "Mission creation failed");
        }}
        selectedMissionId = String(payload.mission_id || "").trim();
        const recorded = await recordMissionActivity({{
          actor,
          domain: "mission-board",
          action: "Create Mission",
          title: String(payload.title || request).trim() || "New mission",
          status: String(payload.status || "created").trim() || "created",
          detail: "Action succeeded: /api/missions",
          why_now: request,
          result_summary: `Mission created in ${{room}} and added to the Mission Board.`,
          route: "/mission-board",
          route_label: "Open Mission Board",
          related_kind: "mission",
          related_label: String(payload.mission_id || payload.title || "mission").trim() || "mission",
          succeeded: true,
        }});
        actionNote.textContent = recorded
          ? `Created mission ${{selectedMissionId || payload.title || "detail"}} and recorded it in shared activity.`
          : `Created mission ${{selectedMissionId || payload.title || "detail"}}.`;
        await refreshMissionBoard();
      }} catch (error) {{
        const errorText = String(error);
        await recordMissionActivity({{
          actor,
          domain: "mission-board",
          action: "Create Mission",
          title: request.slice(0, 80) || "Mission request",
          status: "failed",
          detail: "Action failed: /api/missions",
          why_now: errorText,
          result_summary: `Mission creation failed: ${{errorText}}`,
          route: "/mission-board",
          route_label: "Open Mission Board",
          related_kind: "mission",
          related_label: "mission",
          succeeded: false,
        }});
        actionNote.textContent = `Mission creation failed: ${{errorText}}`;
      }}
    }}

    async function acknowledgeMissionHandoff(missionId, handoffId, receivingAgent, accepted) {{
      if (!missionId || !handoffId || !receivingAgent) return;
      const noteInput = document.querySelector(`[data-handoff-note="${{handoffId}}"]`);
      const note = String(noteInput?.value || "").trim();
      actionNote.textContent = `${{accepted ? "Accepting" : "Rejecting"}} handoff ${{handoffId}}…`;
      try {{
        const response = await fetch(`/api/missions/${{encodeURIComponent(missionId)}}/handoffs/${{encodeURIComponent(handoffId)}}/acknowledge`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            receiving_agent: receivingAgent,
            accepted,
            note,
          }}),
        }});
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.detail || payload.error || "Mission handoff acknowledgement failed");
        }}
        const recorded = await recordMissionActivity({{
          actor: "Chris",
          domain: "mission-board",
          action: accepted ? "Accept Mission Handoff" : "Reject Mission Handoff",
          title: handoffId,
          status: accepted ? "accepted" : "rejected",
          detail: `Action succeeded: /api/missions/${{missionId}}/handoffs/${{handoffId}}/acknowledge`,
          why_now: note || `Receiving agent ${{receivingAgent}} reviewed the mission handoff.`,
          result_summary: accepted
            ? `Handoff ${{handoffId}} was accepted by ${{receivingAgent}}.`
            : `Handoff ${{handoffId}} was rejected by ${{receivingAgent}}.`,
          route: "/mission-board",
          route_label: "Open Mission Board",
          related_kind: "mission",
          related_label: missionId,
          succeeded: true,
        }});
        actionNote.textContent = recorded
          ? `Handoff ${{handoffId}} ${{accepted ? "accepted" : "rejected"}} and recorded in shared activity.`
          : `Handoff ${{handoffId}} ${{accepted ? "accepted" : "rejected"}}.`;
        await refreshMissionBoard();
      }} catch (error) {{
        const errorText = String(error);
        await recordMissionActivity({{
          actor: "Chris",
          domain: "mission-board",
          action: accepted ? "Accept Mission Handoff" : "Reject Mission Handoff",
          title: handoffId,
          status: "failed",
          detail: `Action failed: /api/missions/${{missionId}}/handoffs/${{handoffId}}/acknowledge`,
          why_now: errorText,
          result_summary: `Mission handoff acknowledgement failed: ${{errorText}}`,
          route: "/mission-board",
          route_label: "Open Mission Board",
          related_kind: "mission",
          related_label: missionId,
          succeeded: false,
        }});
        actionNote.textContent = `Mission handoff acknowledgement failed: ${{errorText}}`;
      }}
    }}

    function renderDetail(payload) {{
      const mission = currentMission(payload);
      const detail = currentMissionDetail(payload) || {{}};
      const workState = detail.work_state || {{}};
      if (!mission) {{
        detailEl.innerHTML = "<p class=\\"status-note\\">No mission detail available right now.</p>";
        evidenceEl.innerHTML = "<li><strong>No mission evidence.</strong><span>Mission records will appear once the board is hydrated.</span></li>";
        workspacesEl.innerHTML = '<div class="mission-card"><strong>No mission workspaces.</strong><span>Mission work-state will appear once a selected mission is hydrated.</span></div>';
        handoffsEl.innerHTML = '<div class="mission-card"><strong>No mission handoffs.</strong><span>Choose a mission to author or acknowledge a handoff.</span></div>';
        return;
      }}
      selectedMissionId = mission.mission_id || "";
      const selectedAgents = Array.isArray(mission.selected_agents) ? mission.selected_agents : [];
      const taskAgents = Array.isArray(mission.task_agent_labels) ? mission.task_agent_labels : [];
      const summary = workState.summary || {{}};
      const relatedRoutes = Array.isArray(detail.related_routes) ? detail.related_routes : [];
      const relatedSeams = Array.isArray(detail.related_seams) ? detail.related_seams : [];
      const handoffs = Array.isArray(detail.handoffs) ? detail.handoffs : [];
      const pendingHandoffs = handoffs.filter((item) => {{
        const status = String(item?.status || "").trim().toLowerCase();
        return status === "pending" || status === "pending-acceptance";
      }});
      const ownershipTransfers = Array.isArray(detail.ownership_transfers) ? detail.ownership_transfers : [];
      const handoffOptions = missionAgentOptions(detail, workState);
      detailEl.innerHTML = `
        <div class="mission-card">
          <strong>${{esc(mission.title || mission.mission_id || "Mission")}}</strong>
          <span>${{esc(mission.brief || "No mission brief captured yet.")}}</span>
          <div class="chips">
            ${{chip(mission.lane || "next", mission.lane_class || "")}}
            ${{chip(mission.primary_domain || "general")}}
            ${{chip(mission.owner_agent || "jarvis-orchestrator")}}
          </div>
          <div class="meta">
            <div><label>Mission ID</label><strong>${{esc(mission.mission_id || "not recorded")}}</strong></div>
            <div><label>Next Step</label><strong>${{esc(mission.next_step || "Review mission brief")}}</strong></div>
            <div><label>Updated</label><strong>${{esc(mission.updated_at || "not recorded")}}</strong></div>
            <div><label>Subtasks</label><strong>${{esc(`${{mission.subtask_count || 0}} total / ${{mission.active_count || 0}} active / ${{mission.blocked_count || 0}} blocked / ${{mission.completed_count || 0}} completed`)}}</strong></div>
            <div><label>Workspace Agents</label><strong>${{esc(summary.agents || 0)}}</strong></div>
            <div><label>Pending Handoffs</label><strong>${{esc(summary.pending_handoffs || 0)}}</strong></div>
            <div><label>Pending Reviews</label><strong>${{esc(summary.pending_reviews || 0)}}</strong></div>
            <div><label>Duplicate Suppressions</label><strong>${{esc(summary.duplicate_suppressions || 0)}}</strong></div>
          </div>
          <div class="chips">
            ${{selectedAgents.length ? selectedAgents.map((item) => chip(item)).join("") : chip("No selected agents")}}
            ${{taskAgents.length ? taskAgents.map((item) => chip(item, "steady")).join("") : chip("No task agents", "steady")}}
          </div>
          <div class="action-row">
            <button type="button" data-mission-status="active">Move to Now</button>
            <button type="button" data-mission-status="blocked">Mark Blocked</button>
            <button type="button" data-mission-status="completed">Mark Completed</button>
            <a href="/agent-ops-center">Open Agent Ops</a>
            <a href="/activity-center">Open Activity Feed</a>
          </div>
          <div class="meta">
            <div>
              <label>Edit Title</label>
              <input id="mission-edit-title" value="${{esc(detail.title || mission.title || "")}}" />
            </div>
            <div>
              <label>Edit Brief</label>
              <input id="mission-edit-brief" value="${{esc(detail.brief || mission.brief || "")}}" />
            </div>
            <div>
              <label>Edit Request</label>
              <input id="mission-edit-request" value="${{esc(detail.request || "")}}" />
            </div>
            <div>
              <label>Edit Next Step</label>
              <input id="mission-edit-next-step" value="${{esc(mission.next_step || "")}}" />
            </div>
            <div>
              <label>Edit Note</label>
              <input id="mission-edit-note" value="" placeholder="Why is this mission changing?" />
            </div>
          </div>
          <div class="action-row">
            <button type="button" id="save-mission-detail-button">Save Mission Detail</button>
          </div>
        </div>
      `;
      document.querySelectorAll("[data-mission-status]").forEach((button) => {{
        button.addEventListener("click", () => {{
          updateMissionStatus(selectedMissionId, button.getAttribute("data-mission-status") || "").catch((error) => {{
            actionNote.textContent = `Mission status update failed: ${{String(error)}}`;
          }});
        }});
      }});
      document.getElementById("save-mission-detail-button")?.addEventListener("click", () => {{
        updateMissionDetails(selectedMissionId).catch((error) => {{
          actionNote.textContent = `Mission detail update failed: ${{String(error)}}`;
        }});
      }});

      evidenceEl.innerHTML = [
        li("What Became Real", mission.what_became_real || "Mission board record loaded from the local mission store."),
        li("What Remains Partial", mission.remains_partial || "No remaining mission detail captured."),
        li("Owner Agent", mission.owner_agent || "jarvis-orchestrator"),
        li("Selected Agents", selectedAgents.join(", ") || "none recorded"),
        li("Task Agents", taskAgents.join(", ") || "none recorded"),
        li("Pending Handoffs", String(summary.pending_handoffs || 0), String(summary.pending_transfers || 0) + " transfer(s) waiting"),
        li("Escalations", String(summary.escalations || 0), String(summary.duplicate_suppressions || 0) + " duplicate suppression record(s)"),
        ...relatedSeams.map((item) => li(`Related Seam: ${{item.name || "Seam"}}`, item.what_became_real || "No seam outcome captured yet.", `${{item.module || "Progress"}} · ${{item.status || "Wired"}} · ${{item.surface_path || "/command-center"}}`)),
        ...relatedRoutes.map((item) => li(item.label || "Related Route", item.href || "")),
      ].join("");

      const agentWorkStates = Object.entries(workState.agent_work_states || {{}});
      workspacesEl.innerHTML = agentWorkStates.length
        ? agentWorkStates.map(([agentId, workspace]) => {{
            const activeTasks = Array.isArray(workspace.active_tasks) ? workspace.active_tasks : [];
            const blockedTasks = Array.isArray(workspace.blocked_tasks) ? workspace.blocked_tasks : [];
            const pendingReviews = Array.isArray(workspace.pending_reviews) ? workspace.pending_reviews : [];
            return `
              <div class="mission-card">
                <strong>${{esc(workspace.role || agentId)}}</strong>
                <span>${{esc(workspace.current_focus || "No current focus recorded.")}}</span>
                <div class="chips">
                  ${{chip(agentId)}}
                  ${{chip(workspace.status || "unknown", workspace.status === "blocked" ? "regressed" : workspace.status === "active" ? "accepted" : "steady")}}
                  ${{chip(workspace.ownership_mode || "supporting")}}
                </div>
                <div class="meta">
                  <div><label>Active Tasks</label><strong>${{esc(activeTasks.length)}}</strong></div>
                  <div><label>Blocked Tasks</label><strong>${{esc(blockedTasks.length)}}</strong></div>
                  <div><label>Pending Reviews</label><strong>${{esc(pendingReviews.length)}}</strong></div>
                  <div><label>Last Handoff</label><strong>${{esc(workspace.last_handoff_at || "not recorded")}}</strong></div>
                </div>
                <div class="meta">
                  <div>
                    <label>Current Focus</label>
                    <input data-workspace-focus="${{esc(agentId)}}" value="${{esc(workspace.current_focus || "")}}" />
                  </div>
                  <div>
                    <label>Operator Note</label>
                    <input data-workspace-note="${{esc(agentId)}}" value="" placeholder="Add a quick note or instruction" />
                  </div>
                </div>
                <div class="action-row">
                  <button type="button" data-workspace-update="${{esc(agentId)}}" data-workspace-status="active">Mark Active</button>
                  <button type="button" data-workspace-update="${{esc(agentId)}}" data-workspace-status="ready">Mark Ready</button>
                  <button type="button" data-workspace-update="${{esc(agentId)}}" data-workspace-status="blocked">Mark Blocked</button>
                </div>
                <div class="chips">
                  ${{activeTasks.slice(0, 2).map((task) => chip(task.title || task.status || "task")).join("") || chip("No active tasks")}}
                  ${{pendingReviews.slice(0, 2).map((task) => chip(task.title || task.status || "review", "steady")).join("") || ""}}
                </div>
              </div>
            `;
          }}).join("")
        : '<div class="mission-card"><strong>No mission workspaces.</strong><span>This mission does not yet expose per-agent work-state.</span></div>';

      document.querySelectorAll("[data-workspace-update]").forEach((button) => {{
        button.addEventListener("click", () => {{
          const agentId = button.getAttribute("data-workspace-update") || "";
          const status = button.getAttribute("data-workspace-status") || "";
          const workspace = (workState.agent_work_states || {{}})[agentId] || {{}};
          if (agentId && selectedMissionId) {{
            updateAgentWorkspace(selectedMissionId, agentId, status, workspace).catch((error) => {{
              actionNote.textContent = `Mission workspace update failed: ${{String(error)}}`;
            }});
          }}
        }});
      }});

      const pendingCards = pendingHandoffs.length
        ? pendingHandoffs.map((item) => {{
            const handoffId = String(item?.handoff_id || "").trim();
            const transfer = ownershipTransfers.find((transferItem) => String(transferItem?.task_id || "").trim() === String(item?.task_id || "").trim());
            return `
              <div class="mission-card">
                <strong>${{esc(item.summary || item.task_id || "Mission handoff")}}</strong>
                <span>${{esc(item.from_agent || "unknown source")}} → ${{esc(item.to_agent || "unknown receiving agent")}}</span>
                <div class="chips">
                  ${{chip(item.handoff_kind || "delegation", item.requires_acceptance ? "steady" : "")}}
                  ${{chip(item.status || "pending", item.status === "pending-acceptance" ? "steady" : "accepted")}}
                  ${{transfer ? chip("ownership-transfer", "steady") : ""}}
                </div>
                <span>${{esc(item.partial_work || item.context || "No partial work or continuity notes recorded yet.")}}</span>
                <div class="meta">
                  <div><label>Created</label><strong>${{esc(item.created_at || "not recorded")}}</strong></div>
                  <div><label>Task ID</label><strong>${{esc(item.task_id || "not recorded")}}</strong></div>
                  <div><label>Duplicate Key</label><strong>${{esc(item.duplicate_key || "not recorded")}}</strong></div>
                </div>
                <div class="meta">
                  <div>
                    <label>Acknowledge Note</label>
                    <input data-handoff-note="${{esc(handoffId)}}" value="" placeholder="Add a quick acceptance or rejection note" />
                  </div>
                </div>
                <div class="action-row">
                  <button type="button" data-handoff-ack="${{esc(handoffId)}}" data-handoff-agent="${{esc(item.to_agent || "")}}" data-handoff-accepted="true">Accept Handoff</button>
                  <button type="button" data-handoff-ack="${{esc(handoffId)}}" data-handoff-agent="${{esc(item.to_agent || "")}}" data-handoff-accepted="false">Reject Handoff</button>
                </div>
              </div>
            `;
          }}).join("")
        : '<div class="mission-card"><strong>No pending handoffs.</strong><span>This mission does not currently need a receiving-agent acknowledgement.</span></div>';

      handoffsEl.innerHTML = `
        <div class="mission-card">
          <strong>Author New Handoff</strong>
          <span>Delegate work or transfer ownership between mission agents without leaving the mission board.</span>
          <div class="meta">
            <div>
              <label>From Agent</label>
              <select id="handoff-from-agent">
                <option value="">Choose source agent</option>
                ${{selectOptions(handoffOptions)}}
              </select>
            </div>
            <div>
              <label>To Agent</label>
              <select id="handoff-to-agent">
                <option value="">Choose receiving agent</option>
                ${{selectOptions(handoffOptions)}}
              </select>
            </div>
            <div>
              <label>Task Title</label>
              <input id="handoff-task-title" value="" placeholder="What is being handed off?" />
            </div>
            <div>
              <label>Summary</label>
              <input id="handoff-summary" value="" placeholder="Short handoff summary" />
            </div>
            <div>
              <label>Delegation Reason</label>
              <input id="handoff-reason" value="" placeholder="Why should this move?" />
            </div>
            <div>
              <label>Expected Result</label>
              <input id="handoff-expected-result" value="" placeholder="What should come back?" />
            </div>
            <div>
              <label>Partial Work</label>
              <input id="handoff-partial-work" value="" placeholder="Continuity notes or partial work" />
            </div>
            <div>
              <label>Context</label>
              <input id="handoff-context" value="" placeholder="Important context for the receiving agent" />
            </div>
            <div>
              <label>Duplicate Key</label>
              <input id="handoff-duplicate-key" value="" placeholder="Optional duplicate suppression key" />
            </div>
            <div>
              <label>Ownership Transfer</label>
              <input id="handoff-transfer-ownership" type="checkbox" />
            </div>
          </div>
          <div class="action-row">
            <button type="button" id="create-handoff-button">Create Handoff</button>
          </div>
        </div>
        ${{pendingCards}}
      `;

      document.getElementById("create-handoff-button")?.addEventListener("click", () => {{
        createMissionHandoff(selectedMissionId).catch((error) => {{
          actionNote.textContent = `Mission handoff creation failed: ${{String(error)}}`;
        }});
      }});
      document.querySelectorAll("[data-handoff-ack]").forEach((button) => {{
        button.addEventListener("click", () => {{
          const handoffId = button.getAttribute("data-handoff-ack") || "";
          const receivingAgent = button.getAttribute("data-handoff-agent") || "";
          const accepted = String(button.getAttribute("data-handoff-accepted") || "").trim() === "true";
          acknowledgeMissionHandoff(selectedMissionId, handoffId, receivingAgent, accepted).catch((error) => {{
            actionNote.textContent = `Mission handoff acknowledgement failed: ${{String(error)}}`;
          }});
        }});
      }});
    }}

    function render(payload) {{
      currentPayload = payload || {{}};
      const board = payload.mission_task_board || {{}};
      const counts = board.counts || {{}};
      const items = missions(payload);
      const lanes = [
        {{ key: "now", title: "Now" }},
        {{ key: "next", title: "Next" }},
        {{ key: "blocked", title: "Blocked" }},
        {{ key: "completed", title: "Completed" }},
      ];

      heroStatus.textContent = payload.status || "Wired";
      heroNow.textContent = String(counts.now || 0);
      heroNext.textContent = String(counts.next || 0);
      heroBlocked.textContent = String(counts.blocked || 0);
      heroCompleted.textContent = String(counts.completed || 0);
      statusNote.textContent = payload.summary || "No mission board summary captured yet.";
      authoringEl.innerHTML = `
        <div class="mission-card">
          <strong>Create Mission</strong>
          <span>Start a real mission from this standalone board so it immediately appears in the now/next workflow with seeded agents, subtasks, and mission state.</span>
          <div class="meta">
            <div>
              <label>Actor</label>
              <input id="mission-author-actor" value="Chris" />
            </div>
            <div>
              <label>Room</label>
              <select id="mission-author-room">
                <option value="office">office</option>
                <option value="family">family</option>
                <option value="workshop">workshop</option>
                <option value="travel">travel</option>
              </select>
            </div>
            <div>
              <label>Mission Request</label>
              <input id="mission-author-request" value="" placeholder="What should JARVIS take forward right now?" />
            </div>
          </div>
          <div class="action-row">
            <button type="button" id="create-mission-button">Create Mission</button>
            <a href="/api/missions">Open Missions API</a>
          </div>
        </div>
      `;
      document.getElementById("create-mission-button")?.addEventListener("click", () => {{
        createMission().catch((error) => {{
          actionNote.textContent = `Mission creation failed: ${{String(error)}}`;
        }});
      }});

      boardEl.innerHTML = lanes.map((lane) => {{
        const laneItems = items.filter((item) => String(item.lane || "next") === lane.key);
        const cards = laneItems.length
          ? laneItems.map((item) => `
              <div class="mission-card">
                <strong>${{esc(item.title || item.mission_id || "Mission")}}</strong>
                <span>${{esc(item.brief || "No mission brief captured yet.")}}</span>
                <div class="chips">
                  ${{chip(item.primary_domain || "general")}}
                  ${{chip(item.owner_agent || "jarvis-orchestrator")}}
                </div>
                <span>${{esc(item.next_step || "Review mission brief")}}</span>
                <div class="action-row">
                  <button type="button" data-select-mission="${{esc(item.mission_id || "")}}">Inspect Mission</button>
                </div>
              </div>
            `).join("")
          : `<div class="mission-card"><strong>No ${{esc(lane.title)}} missions.</strong><span>This lane is currently clear.</span></div>`;
        return `<div class="lane"><h3>${{esc(lane.title)}}</h3>${{cards}}</div>`;
      }}).join("");

      document.querySelectorAll("[data-select-mission]").forEach((button) => {{
        button.addEventListener("click", () => {{
          selectedMissionId = button.getAttribute("data-select-mission") || "";
          renderDetail(payload);
          actionNote.textContent = `Focused mission ${{selectedMissionId || "detail"}} for review.`;
        }});
      }});

      missionActivityEl.innerHTML = (Array.isArray(payload.recent_activity) ? payload.recent_activity : []).length
        ? payload.recent_activity.map((item) => `<li><strong>${{esc(item.title || "Mission action")}}</strong><span>${{esc(item.subtitle || item.actor || "Operator continuity")}}</span><span>${{esc(item.detail || item.route_label || "")}}</span></li>`).join("")
        : '<li><strong>No mission continuity recorded yet.</strong><span>Create a mission, move a lane, or hand off work to start the route-level continuity trail.</span></li>';
      proofEl.innerHTML = Object.entries(payload.proof_paths || {{}}).map(([key, value]) => li(key, value)).join("");
      payloadPreview.textContent = JSON.stringify(payload, null, 2);
      renderDetail(payload);
    }}

    async function refreshMissionBoard() {{
      statusNote.textContent = "Refreshing mission board state…";
      try {{
        const response = await fetch("/api/mission-board/module");
        const payload = await response.json();
        render(payload);
        statusNote.textContent = payload.summary || "Mission board refreshed.";
      }} catch (error) {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }}
    }}

    document.getElementById("refresh-mission-board").addEventListener("click", () => {{
      refreshMissionBoard().catch((error) => {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }});
    }});

    render(initialPayload);
  </script>
</body>
</html>
"""


def render_activity_module_page(payload: dict) -> str:
    raw_json = json.dumps(payload, indent=2)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Activity Feed</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #071019;
      --bg-2: #0a1624;
      --panel: rgba(10, 21, 34, 0.9);
      --line: rgba(121, 216, 255, 0.14);
      --text: #edf8ff;
      --muted: #97b5cb;
      --accent: #79d8ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "SF Pro Display", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top, rgba(121, 216, 255, 0.14), transparent 36%),
        linear-gradient(180deg, #040b12 0%, var(--bg) 44%, var(--bg-2) 100%);
      color: var(--text);
    }}
    .shell {{ max-width: 1480px; margin: 0 auto; padding: 36px 24px 60px; }}
    .hero {{
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 28px;
      background: linear-gradient(180deg, rgba(11, 24, 38, 0.94), rgba(7, 17, 28, 0.92));
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.28);
    }}
    .eyebrow {{ color: var(--accent); letter-spacing: 0.18em; text-transform: uppercase; font-size: 12px; }}
    h1 {{ margin: 10px 0 12px; font-size: clamp(34px, 5vw, 56px); }}
    h2 {{ margin: 0 0 14px; font-size: 18px; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    a, button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(121, 216, 255, 0.12);
      color: var(--text);
      text-decoration: none;
      font: inherit;
      cursor: pointer;
    }}
    button.alt {{ background: rgba(255,255,255,0.04); }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 22px;
    }}
    .stat, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
    }}
    .stat span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .stat strong {{ display: block; margin-top: 6px; font-size: 24px; }}
    .layout {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .span-4 {{ grid-column: span 4; }}
    .span-5 {{ grid-column: span 5; }}
    .span-7 {{ grid-column: span 7; }}
    .span-8 {{ grid-column: span 8; }}
    .span-12 {{ grid-column: span 12; }}
    .filter-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 14px;
    }}
    .entry-list {{
      display: grid;
      gap: 10px;
    }}
    .entry-card {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
      display: grid;
      gap: 8px;
    }}
    .entry-card strong {{ display: block; }}
    .entry-card span {{ color: var(--muted); display: block; }}
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      padding: 5px 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      font-size: 12px;
      color: var(--muted);
      background: rgba(255,255,255,0.04);
    }}
    .action-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
    }}
    .meta div {{
      padding: 10px 12px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.02);
    }}
    .meta label {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
    }}
    ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    li {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
    }}
    li strong {{ display: block; margin-bottom: 4px; }}
    li span {{ color: var(--muted); display: block; }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      border-radius: 16px;
      padding: 14px;
      border: 1px solid var(--line);
      background: rgba(3, 10, 18, 0.9);
      color: #d7e8f4;
      overflow-x: auto;
    }}
    .status-note {{
      min-height: 1.3em;
      color: var(--muted);
      margin-top: 10px;
    }}
    @media (max-width: 980px) {{
      .span-4, .span-5, .span-7, .span-8, .span-12 {{ grid-column: span 12; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="eyebrow">Level 3 Working Surface</div>
      <h1>JARVIS Activity Feed</h1>
      <p>A dedicated activity workspace for recent agent updates, failures, system notices, user actions, and journal context. This turns the activity stream into a navigable app surface instead of leaving it only inside the command center.</p>
      <div class="actions">
        <a href="/command-center">Back to Command Center</a>
        <button type="button" id="refresh-activity-feed">Refresh Activity Feed</button>
      </div>
      <div class="stats">
        <div class="stat"><span>Status</span><strong id="hero-status">Loading...</strong></div>
        <div class="stat"><span>Recent Events</span><strong id="hero-events">0</strong></div>
        <div class="stat"><span>Journal Actions</span><strong id="hero-journal">0</strong></div>
        <div class="stat"><span>Operator Actions</span><strong id="hero-operator">0</strong></div>
        <div class="stat"><span>Autonomous Actions</span><strong id="hero-autonomous">0</strong></div>
        <div class="stat"><span>Home Bridges</span><strong id="hero-home-bridges">0</strong></div>
      </div>
      <p class="status-note" id="activity-status-note">Loading activity feed state…</p>
    </section>
    <div class="layout">
      <section class="panel span-7">
        <h2>Recent Activity</h2>
        <div class="filter-row">
          <button type="button" data-filter="all">All Activity</button>
          <button type="button" class="alt" data-filter="failures">Failures</button>
          <button type="button" class="alt" data-filter="approvals">Approvals</button>
          <button type="button" class="alt" data-filter="system">System Notices</button>
        </div>
        <div id="activity-list" class="entry-list"></div>
      </section>
      <section class="panel span-5">
        <h2>Selected Event Detail</h2>
        <div id="activity-detail"></div>
        <p class="status-note" id="activity-action-note">Select an event or jump into a related surface to inspect the current activity context.</p>
      </section>
      <section class="panel span-7">
        <h2>Action Journal</h2>
        <div id="journal-list" class="entry-list"></div>
      </section>
      <section class="panel span-5">
        <h2>Activity Evidence</h2>
        <ul id="activity-evidence-list"></ul>
      </section>
      <section class="panel span-8">
        <h2>Proof Paths</h2>
        <ul id="proof-list"></ul>
      </section>
      <section class="panel span-4">
        <h2>Payload Preview</h2>
        <pre id="payload-preview"></pre>
      </section>
    </div>
  </main>
  <script>
    const initialPayload = {raw_json};
    let currentPayload = initialPayload;
    let currentSelection = {{ kind: "activity", index: 0 }};
    let currentFilter = "all";

    const heroStatus = document.getElementById("hero-status");
    const heroEvents = document.getElementById("hero-events");
    const heroJournal = document.getElementById("hero-journal");
    const heroOperator = document.getElementById("hero-operator");
    const heroAutonomous = document.getElementById("hero-autonomous");
    const heroHomeBridges = document.getElementById("hero-home-bridges");
    const activityList = document.getElementById("activity-list");
    const journalList = document.getElementById("journal-list");
    const detailEl = document.getElementById("activity-detail");
    const evidenceEl = document.getElementById("activity-evidence-list");
    const proofEl = document.getElementById("proof-list");
    const payloadPreview = document.getElementById("payload-preview");
    const statusNote = document.getElementById("activity-status-note");
    const actionNote = document.getElementById("activity-action-note");

    function esc(value) {{
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function li(title, summary, detail = "") {{
      return `<li><strong>${{esc(title)}}</strong><span>${{esc(summary)}}</span>${{detail ? `<span>${{esc(detail)}}</span>` : ""}}</li>`;
    }}

    function chip(label) {{
      return `<span class="chip">${{esc(label)}}</span>`;
    }}

    function filteredActivity(payload) {{
      const items = Array.isArray(payload.activity_feed) ? payload.activity_feed : [];
      if (currentFilter === "failures") {{
        return items.filter((item) => /fail|error|blocked|recover/i.test(`${{item.title || ""}} ${{item.result || ""}} ${{item.entry_type || ""}}`));
      }}
      if (currentFilter === "approvals") {{
        return items.filter((item) => /approval|review/i.test(`${{item.title || ""}} ${{item.subtitle || ""}} ${{item.entry_type || ""}}`));
      }}
      if (currentFilter === "system") {{
        return items.filter((item) => /assistant|runtime|system|notification/i.test(`${{item.title || ""}} ${{item.subtitle || ""}} ${{item.entry_type || ""}}`));
      }}
      return items;
    }}

    function selectedItem(payload) {{
      const activity = filteredActivity(payload);
      const journal = ((payload.action_journal || {{}}).entries) || [];
      if (currentSelection.kind === "journal") {{
        return journal[currentSelection.index] || journal[0] || null;
      }}
      return activity[currentSelection.index] || activity[0] || null;
    }}

    function renderDetail(payload) {{
      const item = selectedItem(payload);
      if (!item) {{
        detailEl.innerHTML = "<p class=\\"status-note\\">No activity detail available right now.</p>";
        evidenceEl.innerHTML = "<li><strong>No activity evidence.</strong><span>Activity evidence will appear once the feed is hydrated.</span></li>";
        return;
      }}
      const relatedRoute = item.related_route || "/command-center";
      detailEl.innerHTML = `
        <div class="entry-card">
          <strong>${{esc(item.title || "Activity Event")}}</strong>
          <span>${{esc(item.detail || item.result || item.subtitle || "No activity detail captured.")}}</span>
          <div class="chips">
            ${{chip(item.entry_type || item.kind || "activity")}}
            ${{item.timestamp ? chip(item.timestamp) : ""}}
            ${{item.actor ? chip(item.actor) : ""}}
          </div>
          <div class="meta">
            <div><label>Source</label><strong>${{esc(item.source_kind || item.entry_type || "activity")}}</strong></div>
            <div><label>Result</label><strong>${{esc(item.result || item.summary || "No result captured")}}</strong></div>
            <div><label>Related Surface</label><strong>${{esc(relatedRoute)}}</strong></div>
            <div><label>Review Time</label><strong>${{esc(item.timestamp || "recent")}}</strong></div>
          </div>
          <div class="action-row">
            <button type="button" data-related-route="${{esc(relatedRoute)}}">Jump to Related</button>
            <a href="/api/activity">Open Activity JSON</a>
          </div>
        </div>
      `;
      document.querySelectorAll("[data-related-route]").forEach((button) => {{
        button.addEventListener("click", () => {{
          const route = button.getAttribute("data-related-route") || "/command-center";
          window.location.href = route;
        }});
      }});
      evidenceEl.innerHTML = [
        li("What Became Real", payload.what_became_real || "No activity seam note recorded yet."),
        li("What Remains Partial", payload.remains_partial || "No remaining partials recorded."),
        li("Feed Summary", payload.summary || "No activity summary captured."),
        li("Journal Summary", ((payload.action_journal || {{}}).summary) || "No journal summary captured."),
        li(
          "Home Continuity",
          ((payload.home_action_result || {{}}).summary) || "No seeded home action bridge is currently attached.",
          ((payload.home_action_result || {{}}).detail) || "",
        ),
      ].join("");
    }}

    function render(payload) {{
      currentPayload = payload || {{}};
      const activity = filteredActivity(payload);
      const journal = Array.isArray((payload.action_journal || {{}}).entries) ? payload.action_journal.entries : [];
      const counts = payload.counts || {{}};

      heroStatus.textContent = payload.status || "Wired";
      heroEvents.textContent = String(counts.activity_count || 0);
      heroJournal.textContent = String(counts.journal_count || 0);
      heroOperator.textContent = String((payload.action_journal || {{}}).operator_count || 0);
      heroAutonomous.textContent = String((payload.action_journal || {{}}).autonomous_count || 0);
      heroHomeBridges.textContent = String(counts.home_bridge_count || 0);
      statusNote.textContent = payload.summary || "No activity summary captured yet.";

      activityList.innerHTML = activity.length
        ? activity.map((item, index) => `
            <div class="entry-card">
              <strong>${{esc(item.title || "Activity Event")}}</strong>
              <span>${{esc(item.subtitle || item.result || "No activity detail captured.")}}</span>
              <div class="chips">
                ${{chip(item.entry_type || "activity")}}
                ${{item.actor ? chip(item.actor) : ""}}
              </div>
              <div class="action-row">
                <button type="button" data-select-kind="activity" data-select-index="${{esc(String(index))}}">Inspect Event</button>
              </div>
            </div>
          `).join("")
        : `<div class="entry-card"><strong>No matching activity.</strong><span>The current filter does not have any visible events.</span></div>`;

      journalList.innerHTML = journal.length
        ? journal.map((item, index) => `
            <div class="entry-card">
              <strong>${{esc(item.title || "Journal Entry")}}</strong>
              <span>${{esc(item.detail || "No journal detail captured.")}}</span>
              <div class="chips">
                ${{chip(item.kind || "journal")}}
                ${{item.related_kind ? chip(item.related_kind) : ""}}
              </div>
              <div class="action-row">
                <button type="button" data-select-kind="journal" data-select-index="${{esc(String(index))}}">Inspect Journal Entry</button>
                ${{item.related_route ? `<button type="button" data-jump-route="${{esc(item.related_route)}}">Jump to Related</button>` : ""}}
              </div>
            </div>
          `).join("")
        : `<div class="entry-card"><strong>No journal entries yet.</strong><span>The action journal will appear here once recent activity is available.</span></div>`;

      document.querySelectorAll("[data-select-kind]").forEach((button) => {{
        button.addEventListener("click", () => {{
          currentSelection = {{
            kind: button.getAttribute("data-select-kind") || "activity",
            index: Number(button.getAttribute("data-select-index") || "0"),
          }};
          renderDetail(payload);
          actionNote.textContent = `Focused ${{currentSelection.kind}} detail for review.`;
        }});
      }});
      document.querySelectorAll("[data-jump-route]").forEach((button) => {{
        button.addEventListener("click", () => {{
          const route = button.getAttribute("data-jump-route") || "/command-center";
          window.location.href = route;
        }});
      }});

      proofEl.innerHTML = Object.entries(payload.proof_paths || {{}}).map(([key, value]) => li(key, value)).join("");
      payloadPreview.textContent = JSON.stringify(payload, null, 2);
      renderDetail(payload);
    }}

    async function refreshActivityFeed() {{
      statusNote.textContent = "Refreshing activity feed state…";
      try {{
        const response = await fetch("/api/activity/module");
        const payload = await response.json();
        render(payload);
        statusNote.textContent = payload.summary || "Activity feed refreshed.";
      }} catch (error) {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }}
    }}

    document.querySelectorAll("[data-filter]").forEach((button) => {{
      button.addEventListener("click", () => {{
        currentFilter = button.getAttribute("data-filter") || "all";
        render(currentPayload);
      }});
    }});
    document.getElementById("refresh-activity-feed").addEventListener("click", () => {{
      refreshActivityFeed().catch((error) => {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }});
    }});

    render(initialPayload);
  </script>
</body>
</html>
"""


def render_approval_module_page(payload: dict) -> str:
    raw_json = json.dumps(payload, indent=2)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Approval Queue</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #061019;
      --bg-2: #0a1624;
      --panel: rgba(10, 21, 34, 0.9);
      --line: rgba(121, 216, 255, 0.14);
      --text: #edf8ff;
      --muted: #97b5cb;
      --accent: #79d8ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "SF Pro Display", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top, rgba(121, 216, 255, 0.12), transparent 38%),
        linear-gradient(180deg, #040b12 0%, var(--bg) 44%, var(--bg-2) 100%);
      color: var(--text);
    }}
    .shell {{ max-width: 1480px; margin: 0 auto; padding: 36px 24px 60px; }}
    .hero {{
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 28px;
      background: linear-gradient(180deg, rgba(11, 24, 38, 0.94), rgba(7, 17, 28, 0.92));
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.28);
    }}
    .eyebrow {{ color: var(--accent); letter-spacing: 0.18em; text-transform: uppercase; font-size: 12px; }}
    h1 {{ margin: 10px 0 12px; font-size: clamp(34px, 5vw, 56px); }}
    h2 {{ margin: 0 0 14px; font-size: 18px; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    a, button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(121, 216, 255, 0.12);
      color: var(--text);
      text-decoration: none;
      font: inherit;
      cursor: pointer;
    }}
    button.alt {{ background: rgba(255,255,255,0.04); }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 22px;
    }}
    .stat, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
    }}
    .stat span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .stat strong {{ display: block; margin-top: 6px; font-size: 24px; }}
    .layout {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .span-4 {{ grid-column: span 4; }}
    .span-5 {{ grid-column: span 5; }}
    .span-7 {{ grid-column: span 7; }}
    .span-8 {{ grid-column: span 8; }}
    .span-12 {{ grid-column: span 12; }}
    .filter-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 14px;
    }}
    .entry-list {{
      display: grid;
      gap: 10px;
    }}
    .entry-card {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
      display: grid;
      gap: 8px;
    }}
    .entry-card strong {{ display: block; }}
    .entry-card span {{ color: var(--muted); display: block; }}
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      padding: 5px 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      font-size: 12px;
      color: var(--muted);
      background: rgba(255,255,255,0.04);
    }}
    .action-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
    }}
    .meta div {{
      padding: 10px 12px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.02);
    }}
    .meta label {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
    }}
    ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    li {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
    }}
    li strong {{ display: block; margin-bottom: 4px; }}
    li span {{ color: var(--muted); display: block; }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      border-radius: 16px;
      padding: 14px;
      border: 1px solid var(--line);
      background: rgba(3, 10, 18, 0.9);
      color: #d7e8f4;
      overflow-x: auto;
    }}
    .status-note {{
      min-height: 1.3em;
      color: var(--muted);
      margin-top: 10px;
    }}
    @media (max-width: 980px) {{
      .span-4, .span-5, .span-7, .span-8, .span-12 {{ grid-column: span 12; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="eyebrow">Level 3 Working Surface</div>
      <h1>JARVIS Approval Queue</h1>
      <p>A dedicated approval workspace for pending requests, decision history, trust-zone context, and direct review actions. This keeps approvals visible and testable as a real app surface instead of leaving them in an older standalone proof lane.</p>
      <div class="actions">
        <a href="/command-center">Back to Command Center</a>
        <button type="button" id="refresh-approval-queue">Refresh Approval Queue</button>
      </div>
      <div class="stats">
        <div class="stat"><span>Status</span><strong id="hero-status">Loading...</strong></div>
        <div class="stat"><span>Pending Requests</span><strong id="hero-pending">0</strong></div>
        <div class="stat"><span>Decision History</span><strong id="hero-history">0</strong></div>
        <div class="stat"><span>High Risk Pending</span><strong id="hero-risk">0</strong></div>
        <div class="stat"><span>Needs Review</span><strong id="hero-needs">0</strong></div>
      </div>
      <p class="status-note" id="approval-status-note">Loading approval queue state…</p>
    </section>
    <div class="layout">
      <section class="panel span-7">
        <h2>Pending Requests</h2>
        <div class="filter-row">
          <button type="button" data-filter="all">All Pending</button>
          <button type="button" class="alt" data-filter="high-risk">High Risk</button>
          <button type="button" class="alt" data-filter="approval-ready">Ready to Execute</button>
        </div>
        <div id="pending-list" class="entry-list"></div>
      </section>
      <section class="panel span-5">
        <h2>Selected Approval Detail</h2>
        <div id="approval-detail"></div>
        <p class="status-note" id="approval-action-note">Inspect a request or history entry, then use the direct approval controls if the current proof still matches intent.</p>
      </section>
      <section class="panel span-7">
        <h2>Decision History</h2>
        <div id="history-list" class="entry-list"></div>
      </section>
      <section class="panel span-5">
        <h2>Needs Review</h2>
        <ul id="needs-review-list"></ul>
      </section>
      <section class="panel span-12">
        <h2>Recovery Continuity</h2>
        <div id="recovery-bridge-list" class="entry-list"></div>
      </section>
      <section class="panel span-8">
        <h2>Recent Approval Continuity</h2>
        <ul id="recent-activity-list"></ul>
      </section>
      <section class="panel span-8">
        <h2>Proof Paths</h2>
        <ul id="proof-list"></ul>
      </section>
      <section class="panel span-4">
        <h2>Payload Preview</h2>
        <pre id="payload-preview"></pre>
      </section>
    </div>
  </main>
  <script>
    const initialPayload = {raw_json};
    let currentPayload = initialPayload;
    let currentSelection = {{ kind: "pending", index: 0 }};
    let currentFilter = "all";

    const heroStatus = document.getElementById("hero-status");
    const heroPending = document.getElementById("hero-pending");
    const heroHistory = document.getElementById("hero-history");
    const heroRisk = document.getElementById("hero-risk");
    const heroNeeds = document.getElementById("hero-needs");
    const pendingList = document.getElementById("pending-list");
    const historyList = document.getElementById("history-list");
    const detailEl = document.getElementById("approval-detail");
    const needsReviewEl = document.getElementById("needs-review-list");
    const recoveryBridgeEl = document.getElementById("recovery-bridge-list");
    const recentActivityEl = document.getElementById("recent-activity-list");
    const proofEl = document.getElementById("proof-list");
    const payloadPreview = document.getElementById("payload-preview");
    const statusNote = document.getElementById("approval-status-note");
    const actionNote = document.getElementById("approval-action-note");

    function esc(value) {{
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function li(title, summary, detail = "") {{
      return `<li><strong>${{esc(title)}}</strong><span>${{esc(summary)}}</span>${{detail ? `<span>${{esc(detail)}}</span>` : ""}}</li>`;
    }}

    function chip(label) {{
      return `<span class="chip">${{esc(label)}}</span>`;
    }}

    function routeLinks(routes) {{
      const entries = Array.isArray(routes) ? routes : [];
      return entries.map((item) => `<a href="${{esc(item.route || "/command-center")}}">${{esc(item.label || "Open Route")}}</a>`).join("");
    }}

    async function recordOperatorAction(payload) {{
      await fetch("/api/activity/operator-action", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload),
      }});
    }}

    function filteredPending(payload) {{
      const items = Array.isArray(payload.pending) ? payload.pending : [];
      if (currentFilter === "high-risk") {{
        return items.filter((item) => /high|critical/i.test(String(item.risk_tier || "")));
      }}
      if (currentFilter === "approval-ready") {{
        return items.filter((item) => /allow|approved/i.test(String((item.supervision_decision || {{}}).resolution || item.status || "")));
      }}
      return items;
    }}

    function selectedItem(payload) {{
      const pending = filteredPending(payload);
      const history = Array.isArray(payload.history) ? payload.history : [];
      if (currentSelection.kind === "history") {{
        return history[currentSelection.index] || history[0] || null;
      }}
      return pending[currentSelection.index] || pending[0] || null;
    }}

    function renderDetail(payload) {{
      const item = selectedItem(payload);
      if (!item) {{
        detailEl.innerHTML = "<p class=\\"status-note\\">No approval detail available right now.</p>";
        return;
      }}
      const supervision = item.supervision_decision || {{}};
      const relatedRoute = supervision.resolution === "deny" ? "/recovery-center" : "/command-center";
      const controls = currentSelection.kind === "pending"
        ? `
            <button type="button" data-request-action="approve" data-request-id="${{esc(item.request_id || "")}}">Approve</button>
            <button type="button" class="alt" data-request-action="reject" data-request-id="${{esc(item.request_id || "")}}">Reject</button>
            <button type="button" class="alt" data-request-action="cancel" data-request-id="${{esc(item.request_id || "")}}">Cancel</button>
            <button type="button" class="alt" data-request-action="execute" data-request-id="${{esc(item.request_id || "")}}">Execute</button>
          `
        : "";
      detailEl.innerHTML = `
        <div class="entry-card">
          <strong>${{esc(item.title || "Approval Request")}}</strong>
          <span>${{esc(item.description || item.rejection_reason || "No approval detail captured.")}}</span>
          <div class="chips">
            ${{chip(item.status || currentSelection.kind)}}
            ${{item.risk_tier ? chip(item.risk_tier) : ""}}
            ${{item.action_type ? chip(item.action_type) : ""}}
          </div>
          <div class="meta">
            <div><label>Agent</label><strong>${{esc(item.agent_label || item.agent_id || "Unknown agent")}}</strong></div>
            <div><label>Actor</label><strong>${{esc(item.actor_id || "Unknown actor")}}</strong></div>
            <div><label>Trust Zone</label><strong>${{esc(item.trust_zone_id || "unspecified")}}</strong></div>
            <div><label>Lane</label><strong>${{esc(item.lane_id || "unassigned")}}</strong></div>
            <div><label>Resolution</label><strong>${{esc(supervision.resolution || item.status || "unclassified")}}</strong></div>
            <div><label>Requested</label><strong>${{esc(item.requested_at || item.approved_at || item.executed_at || "recent")}}</strong></div>
          </div>
          <div class="action-row">
            ${{controls}}
            <a href="/api/approval-queue/snapshot">Open Legacy Snapshot</a>
            <button type="button" data-related-route="${{esc(relatedRoute)}}">Jump to Related</button>
          </div>
        </div>
      `;
      document.querySelectorAll("[data-related-route]").forEach((button) => {{
        button.addEventListener("click", () => {{
          const route = button.getAttribute("data-related-route") || "/command-center";
          window.location.href = route;
        }});
      }});
      document.querySelectorAll("[data-request-action]").forEach((button) => {{
        button.addEventListener("click", async () => {{
          const requestId = button.getAttribute("data-request-id") || "";
          const action = button.getAttribute("data-request-action") || "";
          if (!requestId || !action) return;
          const endpointMap = {{
            approve: `/api/approvals/${{encodeURIComponent(requestId)}}/approve`,
            reject: `/api/approvals/${{encodeURIComponent(requestId)}}/reject`,
            cancel: `/api/approvals/${{encodeURIComponent(requestId)}}/cancel`,
            execute: `/api/approvals/${{encodeURIComponent(requestId)}}/execute`,
          }};
          const body = action === "approve"
            ? {{ approved_by: "Chris" }}
            : action === "reject"
              ? {{ reason: "Need safer plan before execution", rejected_by: "Chris" }}
              : undefined;
          actionNote.textContent = `Running approval action: ${{action}}…`;
          try {{
            const response = await fetch(endpointMap[action], {{
              method: "POST",
              headers: body ? {{ "Content-Type": "application/json" }} : {{}},
              body: body ? JSON.stringify(body) : undefined,
            }});
            const result = await response.json();
            await recordOperatorAction({{
              actor: "Chris",
              domain: "approval",
              action: `${{action.charAt(0).toUpperCase() + action.slice(1)}} Approval Request`,
              title: item.title || "Approval Request",
              detail: result.status
                ? `Approval action ${{
                    action
                  }} recorded from the Approval Queue.`
                : `Approval action ${{
                    action
                  }} completed from the Approval Queue.`,
              why_now: "Approval Queue changed a live review item from the route-level operator flow.",
              result_summary: result.status
                ? `Approval action status: ${{result.status}}`
                : `Approval action completed: ${{action}}`,
              route: "/approval-queue",
              route_label: "Open Approval Queue",
              related_kind: "approval",
              related_label: item.title || item.request_id || "Approval Request",
              succeeded: response.ok,
            }});
            await refreshApprovalQueue();
            actionNote.textContent = result.status
              ? `Approval action recorded: ${{result.status}}.`
              : `Approval action completed: ${{action}}.`;
          }} catch (error) {{
            actionNote.textContent = `Approval action failed: ${{String(error)}}`;
          }}
        }});
      }});
    }}

    function render(payload) {{
      currentPayload = payload || {{}};
      const pending = filteredPending(payload);
      const history = Array.isArray(payload.history) ? payload.history : [];
      const counts = payload.counts || {{}};

      heroStatus.textContent = payload.status || "Wired";
      heroPending.textContent = String(counts.pending_count || 0);
      heroHistory.textContent = String(counts.history_count || 0);
      heroRisk.textContent = String(counts.high_risk_pending_count || 0);
      heroNeeds.textContent = String((payload.what_needs_me || []).length || 0);
      statusNote.textContent = payload.summary || "No approval summary captured yet.";

      pendingList.innerHTML = pending.length
        ? pending.map((item, index) => `
            <div class="entry-card">
              <strong>${{esc(item.title || "Approval Request")}}</strong>
              <span>${{esc(item.description || "No request detail captured.")}}</span>
              <div class="chips">
                ${{chip(item.risk_tier || "unspecified")}}
                ${{item.action_type ? chip(item.action_type) : ""}}
                ${{item.agent_label ? chip(item.agent_label) : ""}}
              </div>
              <div class="action-row">
                <button type="button" data-select-kind="pending" data-select-index="${{esc(String(index))}}">Inspect Request</button>
              </div>
            </div>
          `).join("")
        : `<div class="entry-card"><strong>No pending approvals.</strong><span>The queue is currently clear.</span></div>`;

      historyList.innerHTML = history.length
        ? history.map((item, index) => `
            <div class="entry-card">
              <strong>${{esc(item.title || "Decision History Entry")}}</strong>
              <span>${{esc(item.status || "No status captured")}} by ${{esc(item.approved_by || item.actor_id || "unknown actor")}}</span>
              <div class="chips">
                ${{chip(item.status || "history")}}
                ${{item.agent_label ? chip(item.agent_label) : ""}}
              </div>
              <div class="action-row">
                <button type="button" data-select-kind="history" data-select-index="${{esc(String(index))}}">Inspect Decision History</button>
              </div>
            </div>
          `).join("")
        : `<div class="entry-card"><strong>No decision history yet.</strong><span>Resolved approval records will appear here.</span></div>`;

      needsReviewEl.innerHTML = Array.isArray(payload.what_needs_me) && payload.what_needs_me.length
        ? payload.what_needs_me.map((item) => li(item.title || "Approval review", item.detail || "Needs operator review.", item.command || "")).join("")
        : `<li><strong>No urgent approval work.</strong><span>Nothing currently needs a human decision.</span></li>`;

      const recoveryBridge = ((payload.recovery_bridge || {{}}).recent) || [];
      recoveryBridgeEl.innerHTML = recoveryBridge.length
        ? recoveryBridge.map((item) => `
            <div class="entry-card">
              <strong>${{esc(item.target_label || "Recovery action")}}</strong>
              <span>${{esc(item.detail || "Recovery continuity recorded.")}}</span>
              <div class="chips">
                ${{chip(item.action_type || "review")}}
                ${{chip(item.status || "queued")}}
                ${{chip(item.target_kind || "approval")}}
              </div>
              <div class="action-row">
                ${{routeLinks(item.related_routes)}}
              </div>
            </div>
          `).join("")
        : `<div class="entry-card"><strong>No recovery continuity recorded.</strong><span>Recovery actions linked to approvals will surface here with routes back to the failure and supervision stack.</span></div>`;
      recentActivityEl.innerHTML = (Array.isArray(payload.recent_activity) ? payload.recent_activity : []).length
        ? payload.recent_activity.map((item) => li(item.title || "Approval action", item.subtitle || item.actor || "Operator continuity", item.detail || item.route_label || "")).join("")
        : `<li><strong>No approval continuity recorded yet.</strong><span>Approve, reject, cancel, or execute a request to begin the route-level continuity trail.</span></li>`;

      document.querySelectorAll("[data-select-kind]").forEach((button) => {{
        button.addEventListener("click", () => {{
          currentSelection = {{
            kind: button.getAttribute("data-select-kind") || "pending",
            index: Number(button.getAttribute("data-select-index") || "0"),
          }};
          renderDetail(payload);
          actionNote.textContent = `Focused ${{currentSelection.kind}} detail for review.`;
        }});
      }});

      proofEl.innerHTML = Object.entries(payload.proof_paths || {{}}).map(([key, value]) => li(key, value)).join("");
      payloadPreview.textContent = JSON.stringify(payload, null, 2);
      renderDetail(payload);
    }}

    async function refreshApprovalQueue() {{
      statusNote.textContent = "Refreshing approval queue state…";
      try {{
        const response = await fetch("/api/approval/module");
        const payload = await response.json();
        render(payload);
        statusNote.textContent = payload.summary || "Approval queue refreshed.";
      }} catch (error) {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }}
    }}

    document.querySelectorAll("[data-filter]").forEach((button) => {{
      button.addEventListener("click", () => {{
        currentFilter = button.getAttribute("data-filter") || "all";
        render(currentPayload);
      }});
    }});
    document.getElementById("refresh-approval-queue").addEventListener("click", () => {{
      refreshApprovalQueue().catch((error) => {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }});
    }});

    render(initialPayload);
  </script>
</body>
</html>
"""


def render_supervision_module_page(payload: dict) -> str:
    raw_json = json.dumps(payload, indent=2)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Supervision Snapshot</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #061019;
      --bg-2: #0a1624;
      --panel: rgba(10, 21, 34, 0.9);
      --line: rgba(121, 216, 255, 0.14);
      --text: #edf8ff;
      --muted: #97b5cb;
      --accent: #79d8ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "SF Pro Display", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top, rgba(121, 216, 255, 0.12), transparent 38%),
        linear-gradient(180deg, #040b12 0%, var(--bg) 44%, var(--bg-2) 100%);
      color: var(--text);
    }}
    .shell {{ max-width: 1480px; margin: 0 auto; padding: 36px 24px 60px; }}
    .hero {{
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 28px;
      background: linear-gradient(180deg, rgba(11, 24, 38, 0.94), rgba(7, 17, 28, 0.92));
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.28);
    }}
    .eyebrow {{ color: var(--accent); letter-spacing: 0.18em; text-transform: uppercase; font-size: 12px; }}
    h1 {{ margin: 10px 0 12px; font-size: clamp(34px, 5vw, 56px); }}
    h2 {{ margin: 0 0 14px; font-size: 18px; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    a, button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(121, 216, 255, 0.12);
      color: var(--text);
      text-decoration: none;
      font: inherit;
      cursor: pointer;
    }}
    button.alt {{ background: rgba(255,255,255,0.04); }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 22px;
    }}
    .stat, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
    }}
    .stat span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .stat strong {{ display: block; margin-top: 6px; font-size: 24px; }}
    .layout {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .span-4 {{ grid-column: span 4; }}
    .span-5 {{ grid-column: span 5; }}
    .span-7 {{ grid-column: span 7; }}
    .span-8 {{ grid-column: span 8; }}
    .span-12 {{ grid-column: span 12; }}
    .entry-list {{
      display: grid;
      gap: 10px;
    }}
    .entry-card {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
      display: grid;
      gap: 8px;
    }}
    .entry-card strong {{ display: block; }}
    .entry-card span {{ color: var(--muted); display: block; }}
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      padding: 5px 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      font-size: 12px;
      color: var(--muted);
      background: rgba(255,255,255,0.04);
    }}
    .action-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
    }}
    .meta div {{
      padding: 10px 12px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.02);
    }}
    .meta label {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
    }}
    ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    li {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
    }}
    li strong {{ display: block; margin-bottom: 4px; }}
    li span {{ color: var(--muted); display: block; }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      border-radius: 16px;
      padding: 14px;
      border: 1px solid var(--line);
      background: rgba(3, 10, 18, 0.9);
      color: #d7e8f4;
      overflow-x: auto;
    }}
    .status-note {{
      min-height: 1.3em;
      color: var(--muted);
      margin-top: 10px;
    }}
    @media (max-width: 980px) {{
      .span-4, .span-5, .span-7, .span-8, .span-12 {{ grid-column: span 12; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="eyebrow">Level 3 Working Surface</div>
      <h1>JARVIS Supervision Snapshot</h1>
      <p>A dedicated supervision workspace for lane posture, active approvals, failing integrations, memory review cues, and registry state. This upgrades supervision from an older proof surface into the newer app-module family while preserving the same live substrate.</p>
      <div class="actions">
        <a href="/command-center">Back to Command Center</a>
        <button type="button" id="refresh-supervision-state">Refresh Supervision State</button>
      </div>
      <div class="stats">
        <div class="stat"><span>Status</span><strong id="hero-status">Loading...</strong></div>
        <div class="stat"><span>Needs Review</span><strong id="hero-needs">0</strong></div>
        <div class="stat"><span>Pending Approvals</span><strong id="hero-approvals">0</strong></div>
        <div class="stat"><span>Integration Issues</span><strong id="hero-integrations">0</strong></div>
        <div class="stat"><span>Dirty Files</span><strong id="hero-dirty">0</strong></div>
      </div>
      <p class="status-note" id="supervision-status-note">Loading supervision state…</p>
    </section>
    <div class="layout">
      <section class="panel span-7">
        <h2>Attention Queue</h2>
        <div id="attention-list" class="entry-list"></div>
      </section>
      <section class="panel span-5">
        <h2>Selected Supervision Detail</h2>
        <div id="supervision-detail"></div>
        <p class="status-note" id="supervision-action-note">Inspect a supervision item, then use the route jump or direct approval controls if the current proof still matches intent.</p>
      </section>
      <section class="panel span-4">
        <h2>What Needs Me</h2>
        <ul id="needs-me-list"></ul>
      </section>
      <section class="panel span-4">
        <h2>Integration Status</h2>
        <div id="integration-list" class="entry-list"></div>
      </section>
      <section class="panel span-4">
        <h2>Lane Residue</h2>
        <ul id="lane-residue-list"></ul>
      </section>
      <section class="panel span-8">
        <h2>Registry and Memory</h2>
        <ul id="registry-memory-list"></ul>
      </section>
      <section class="panel span-4">
        <h2>Proof Paths</h2>
        <ul id="proof-list"></ul>
      </section>
      <section class="panel span-12">
        <h2>Recovery Continuity</h2>
        <div id="recovery-bridge-list" class="entry-list"></div>
      </section>
      <section class="panel span-12">
        <h2>Recent Supervision Continuity</h2>
        <ul id="recent-activity-list"></ul>
      </section>
      <section class="panel span-12">
        <h2>Payload Preview</h2>
        <pre id="payload-preview"></pre>
      </section>
    </div>
  </main>
  <script>
    const initialPayload = {raw_json};
    let currentPayload = initialPayload;
    let currentSelection = {{ kind: "attention", index: 0 }};

    const heroStatus = document.getElementById("hero-status");
    const heroNeeds = document.getElementById("hero-needs");
    const heroApprovals = document.getElementById("hero-approvals");
    const heroIntegrations = document.getElementById("hero-integrations");
    const heroDirty = document.getElementById("hero-dirty");
    const attentionList = document.getElementById("attention-list");
    const detailEl = document.getElementById("supervision-detail");
    const needsMeEl = document.getElementById("needs-me-list");
    const integrationList = document.getElementById("integration-list");
    const laneResidueEl = document.getElementById("lane-residue-list");
    const registryMemoryEl = document.getElementById("registry-memory-list");
    const recoveryBridgeEl = document.getElementById("recovery-bridge-list");
    const recentActivityEl = document.getElementById("recent-activity-list");
    const proofEl = document.getElementById("proof-list");
    const payloadPreview = document.getElementById("payload-preview");
    const statusNote = document.getElementById("supervision-status-note");
    const actionNote = document.getElementById("supervision-action-note");

    function esc(value) {{
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function li(title, summary, detail = "") {{
      return `<li><strong>${{esc(title)}}</strong><span>${{esc(summary)}}</span>${{detail ? `<span>${{esc(detail)}}</span>` : ""}}</li>`;
    }}

    function chip(label) {{
      return `<span class="chip">${{esc(label)}}</span>`;
    }}

    function routeLinks(routes) {{
      const entries = Array.isArray(routes) ? routes : [];
      return entries.map((item) => `<a href="${{esc(item.route || "/command-center")}}">${{esc(item.label || "Open Route")}}</a>`).join("");
    }}

    async function recordOperatorAction(payload) {{
      await fetch("/api/activity/operator-action", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload),
      }});
    }}

    function selectedAttention(payload) {{
      const items = Array.isArray(payload.attention_queue) ? payload.attention_queue : [];
      return items[currentSelection.index] || items[0] || null;
    }}

    function renderDetail(payload) {{
      const item = selectedAttention(payload);
      if (!item) {{
        detailEl.innerHTML = "<p class=\\"status-note\\">No active supervision detail available right now.</p>";
        return;
      }}
      const actions = item.actions || {{}};
      detailEl.innerHTML = `
        <div class="entry-card">
          <strong>${{esc(item.title || "Supervision Item")}}</strong>
          <span>${{esc(item.why_now || "No supervision detail captured.")}}</span>
          <div class="chips">
            ${{item.risk_tier ? chip(item.risk_tier) : ""}}
            ${{item.action_type ? chip(item.action_type) : ""}}
            ${{item.agent_label ? chip(item.agent_label) : ""}}
          </div>
          <div class="meta">
            <div><label>Actor</label><strong>${{esc(item.actor_id || "Unknown actor")}}</strong></div>
            <div><label>Requested</label><strong>${{esc(item.requested_at || "recent")}}</strong></div>
            <div><label>Expires</label><strong>${{esc(item.expires_at || "unspecified")}}</strong></div>
            <div><label>Request ID</label><strong>${{esc(item.request_id || "n/a")}}</strong></div>
          </div>
          <div class="action-row">
            ${{actions.approve ? `<button type="button" data-request-action="approve" data-endpoint="${{esc(actions.approve)}}">Approve</button>` : ""}}
            ${{actions.reject ? `<button type="button" class="alt" data-request-action="reject" data-endpoint="${{esc(actions.reject)}}" data-body='{{"reason":"Need a safer plan first"}}'>Reject</button>` : ""}}
            ${{actions.cancel ? `<button type="button" class="alt" data-request-action="cancel" data-endpoint="${{esc(actions.cancel)}}">Cancel</button>` : ""}}
            ${{actions.execute ? `<button type="button" class="alt" data-request-action="execute" data-endpoint="${{esc(actions.execute)}}">Execute</button>` : ""}}
            <button type="button" data-route-jump="/approval-queue">Open Approval Queue</button>
          </div>
        </div>
      `;
      document.querySelectorAll("[data-route-jump]").forEach((button) => {{
        button.addEventListener("click", () => {{
          window.location.href = button.getAttribute("data-route-jump") || "/command-center";
        }});
      }});
      document.querySelectorAll("[data-request-action]").forEach((button) => {{
        button.addEventListener("click", async () => {{
          const endpoint = button.getAttribute("data-endpoint") || "";
          const rawBody = button.getAttribute("data-body");
          const action = button.getAttribute("data-request-action") || "action";
          actionNote.textContent = `Running supervision action: ${{action}}…`;
          try {{
            const response = await fetch(endpoint, {{
              method: "POST",
              headers: rawBody ? {{ "Content-Type": "application/json" }} : {{}},
              body: rawBody || undefined,
            }});
            const result = await response.json().catch(() => ({{}}));
            if (!response.ok) {{
              throw new Error(result.detail || `HTTP ${{response.status}}`);
            }}
            await recordOperatorAction({{
              actor: "Chris",
              domain: "supervision",
              action: `${{action.charAt(0).toUpperCase() + action.slice(1)}} Supervision Item`,
              title: item.title || "Supervision Item",
              detail: result.status
                ? `Supervision action ${{
                    action
                  }} recorded from the Supervision Snapshot.`
                : `Supervision action ${{
                    action
                  }} completed from the Supervision Snapshot.`,
              why_now: "Supervision changed a live review item from the route-level operator flow.",
              result_summary: result.status
                ? `Supervision action status: ${{result.status}}`
                : `Supervision action completed: ${{action}}`,
              route: "/supervision-snapshot",
              route_label: "Open Supervision Snapshot",
              related_kind: "supervision-item",
              related_label: item.title || item.request_id || "Supervision Item",
              succeeded: true,
            }});
            await refreshSupervisionState();
            actionNote.textContent = result.status
              ? `Supervision action recorded: ${{result.status}}.`
              : `Supervision action completed: ${{action}}.`;
          }} catch (error) {{
            actionNote.textContent = `Supervision action failed: ${{String(error)}}`;
          }}
        }});
      }});
    }}

    function render(payload) {{
      currentPayload = payload || {{}};
      const counts = payload.counts || {{}};
      const attention = Array.isArray(payload.attention_queue) ? payload.attention_queue : [];
      const needs = Array.isArray(payload.what_needs_me) ? payload.what_needs_me : [];
      const integrations = Array.isArray(payload.integrations) ? payload.integrations : [];
      const lane = payload.lane || {{}};
      const memory = payload.memory || {{}};
      const registry = payload.registry || {{}};

      heroStatus.textContent = payload.status || "Wired";
      heroNeeds.textContent = String(counts.needs_review_count || 0);
      heroApprovals.textContent = String(counts.pending_approval_count || 0);
      heroIntegrations.textContent = String(counts.integration_issue_count || 0);
      heroDirty.textContent = String((lane.dirty_count || 0));
      statusNote.textContent = payload.summary || "No supervision summary captured yet.";

      attentionList.innerHTML = attention.length
        ? attention.map((item, index) => `
            <div class="entry-card">
              <strong>${{esc(item.title || "Supervision Item")}}</strong>
              <span>${{esc(item.why_now || "No supervision detail captured.")}}</span>
              <div class="chips">
                ${{item.risk_tier ? chip(item.risk_tier) : ""}}
                ${{item.agent_label ? chip(item.agent_label) : ""}}
              </div>
              <div class="action-row">
                <button type="button" data-select-index="${{esc(String(index))}}">Inspect Supervision Item</button>
              </div>
            </div>
          `).join("")
        : `<div class="entry-card"><strong>No active supervision items.</strong><span>The current supervision queue is clear.</span></div>`;

      needsMeEl.innerHTML = needs.length
        ? needs.map((item) => li(item.title || "Needs Review", item.detail || "No detail captured.", item.kind || "")).join("")
        : `<li><strong>No urgent review work.</strong><span>Nothing currently needs direct supervision review.</span></li>`;

      integrationList.innerHTML = integrations.length
        ? integrations.map((item) => `
            <div class="entry-card">
              <strong>${{esc(item.name || "Integration")}}</strong>
              <span>${{esc(item.detail || "No integration detail captured.")}}</span>
              <div class="chips">
                ${{chip(item.ok ? "ok" : "issue")}}
              </div>
            </div>
          `).join("")
        : `<div class="entry-card"><strong>No integration posture available.</strong><span>Integration state did not hydrate.</span></div>`;

      laneResidueEl.innerHTML = Array.isArray(lane.dirty_sample) && lane.dirty_sample.length
        ? lane.dirty_sample.map((line) => li("Dirty File", line)).join("")
        : `<li><strong>Clean sample unavailable.</strong><span>No dirty sample was captured.</span></li>`;

      registryMemoryEl.innerHTML = [
        li("Current Branch", lane.branch || "unknown", lane.head || "unknown head"),
        li("Recent Seams", Array.isArray(lane.recent_commits) ? lane.recent_commits.slice(0, 3).join(" | ") : "No recent commits"),
        li("Registered Agents", String(registry.agent_count || 0), Array.isArray(registry.domains) ? registry.domains.join(", ") : ""),
        li("Memory Entries", String(memory.entry_count || 0), Array.isArray(memory.latest_entry_titles) ? memory.latest_entry_titles.join(", ") : ""),
      ].join("");

      const recoveryBridge = ((payload.recovery_bridge || {{}}).recent) || [];
      recoveryBridgeEl.innerHTML = recoveryBridge.length
        ? recoveryBridge.map((item) => `
            <div class="entry-card">
              <strong>${{esc(item.target_label || "Recovery continuity item")}}</strong>
              <span>${{esc(item.detail || "Recovery continuity recorded.")}}</span>
              <div class="chips">
                ${{chip(item.target_kind || "recovery")}}
                ${{chip(item.action_type || "review")}}
                ${{chip(item.status || "queued")}}
              </div>
              <div class="action-row">
                ${{routeLinks(item.related_routes)}}
              </div>
            </div>
          `).join("")
        : `<div class="entry-card"><strong>No recovery continuity recorded.</strong><span>Retry and stabilization actions will surface here with links into the related routes once the failure stack is exercised.</span></div>`;
      recentActivityEl.innerHTML = (Array.isArray(payload.recent_activity) ? payload.recent_activity : []).length
        ? payload.recent_activity.map((item) => li(item.title || "Supervision action", item.subtitle || item.actor || "Operator continuity", item.detail || item.route_label || "")).join("")
        : `<li><strong>No supervision continuity recorded yet.</strong><span>Approve, reject, cancel, or execute a supervision item to begin the route-level continuity trail.</span></li>`;

      document.querySelectorAll("[data-select-index]").forEach((button) => {{
        button.addEventListener("click", () => {{
          currentSelection = {{ kind: "attention", index: Number(button.getAttribute("data-select-index") || "0") }};
          renderDetail(payload);
          actionNote.textContent = "Focused supervision detail for review.";
        }});
      }});

      proofEl.innerHTML = Object.entries(payload.proof_paths || {{}}).map(([key, value]) => li(key, value)).join("");
      payloadPreview.textContent = JSON.stringify(payload, null, 2);
      renderDetail(payload);
    }}

    async function refreshSupervisionState() {{
      statusNote.textContent = "Refreshing supervision state…";
      try {{
        const response = await fetch("/api/supervision/module");
        const payload = await response.json();
        render(payload);
        statusNote.textContent = payload.summary || "Supervision state refreshed.";
      }} catch (error) {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }}
    }}

    document.getElementById("refresh-supervision-state").addEventListener("click", () => {{
      refreshSupervisionState().catch((error) => {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }});
    }});

    render(initialPayload);
  </script>
</body>
</html>
"""


def render_progress_module_page(payload: dict) -> str:
    raw_json = json.dumps(payload, indent=2)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Progress</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #050d16;
      --bg-2: #091420;
      --panel: rgba(9, 20, 33, 0.92);
      --panel-2: rgba(11, 22, 36, 0.96);
      --line: rgba(121, 216, 255, 0.14);
      --text: #edf7ff;
      --muted: #9eb8cb;
      --accent: #52c9ff;
      --accent-soft: rgba(82, 201, 255, 0.1);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "SF Pro Display", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top, rgba(121, 216, 255, 0.12), transparent 36%),
        linear-gradient(180deg, #040b12 0%, var(--bg) 44%, var(--bg-2) 100%);
      color: var(--text);
    }}
    .shell {{ max-width: 1420px; margin: 0 auto; padding: 36px 24px 60px; }}
    .hero {{
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 28px;
      background: linear-gradient(180deg, rgba(10, 22, 35, 0.96), rgba(7, 16, 27, 0.92));
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.28);
    }}
    .eyebrow {{ color: #79d8ff; letter-spacing: 0.18em; text-transform: uppercase; font-size: 12px; }}
    h1 {{ margin: 10px 0 12px; font-size: clamp(34px, 5vw, 56px); }}
    h2 {{ margin-top: 0; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 22px;
    }}
    .stat, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
    }}
    .stat span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .stat strong {{ display: block; margin-top: 6px; font-size: 24px; }}
    .layout {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .span-4 {{ grid-column: span 4; }}
    .span-6 {{ grid-column: span 6; }}
    .span-8 {{ grid-column: span 8; }}
    .span-12 {{ grid-column: span 12; }}
    ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    li {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.03);
    }}
    li strong {{ display: block; margin-bottom: 4px; }}
    li span {{ color: var(--muted); display: block; }}
    li code {{ display: block; margin-top: 8px; color: #d7e8f4; }}
    .actions, .action-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    a, button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(121, 216, 255, 0.12);
      color: var(--text);
      text-decoration: none;
      font: inherit;
      cursor: pointer;
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      border-radius: 16px;
      padding: 14px;
      border: 1px solid var(--line);
      background: rgba(3, 10, 18, 0.9);
      color: #d7e8f4;
      overflow-x: auto;
    }}
    .status-note {{ min-height: 1.3em; color: var(--muted); margin-top: 10px; }}
    .readiness-chip {{
      display: inline-flex;
      padding: 4px 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      color: var(--muted);
      margin-top: 8px;
      width: fit-content;
    }}
    .route-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }}
    .controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }}
    input, select {{
      border-radius: 12px;
      border: 1px solid var(--line);
      background: rgba(4, 12, 20, 0.92);
      color: var(--text);
      padding: 10px 12px;
      font: inherit;
    }}
    @media (max-width: 980px) {{
      .span-4, .span-6, .span-8, .span-12 {{ grid-column: span 12; }}
      .controls {{ flex-direction: column; align-items: stretch; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="eyebrow">Level 3 Core Module</div>
      <h1>JARVIS Progress</h1>
      <p>A dedicated progress workspace inside JARVIS with live readiness rows, seam posture, lane status, failure signals, and concrete evidence for what became real versus what still needs another slice. This promotes Progress out of the command-center panel into a real module route.</p>
      <div class="actions">
        <a href="/command-center">Back to Command Center</a>
        <a href="#level3-checklist">Open Remaining Level 3 Checklist</a>
        <button type="button" id="refresh-progress">Refresh Progress State</button>
      </div>
      <div class="stats">
        <div class="stat"><span>Status</span><strong id="hero-status">Loading...</strong></div>
        <div class="stat"><span>Useful Modules</span><strong id="hero-useful">0</strong></div>
        <div class="stat"><span>Wired Modules</span><strong id="hero-wired">0</strong></div>
        <div class="stat"><span>Visible Seams</span><strong id="hero-seams">0</strong></div>
      </div>
      <p class="status-note" id="progress-status-note">Loading progress module state…</p>
      <div class="controls" style="margin-top:16px;">
        <select id="progress-focus-module"></select>
        <input id="progress-focus-reason" placeholder="Why this is the next Level 3 closure target" />
        <button type="button" id="save-progress-focus">Save Next Focus</button>
      </div>
      <p class="status-note" id="progress-focus-note">Persist the next Level 3 focus so progress history and shared activity stay aligned.</p>
    </section>
    <div class="layout">
      <section class="panel span-4">
        <h2>Module Status</h2>
        <ul id="module-status-list"></ul>
      </section>
      <section class="panel span-8">
        <h2>Progress Dashboard</h2>
        <ul id="progress-items-list"></ul>
      </section>
      <section class="panel span-12" id="level3-checklist">
        <h2>Remaining Level 3 Checklist</h2>
        <ul id="level3-checklist-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Readiness Detail</h2>
        <ul id="readiness-detail-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Seam Highlights</h2>
        <ul id="seam-highlights-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Lane & Failure Posture</h2>
        <ul id="lane-failure-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Hosted Readiness</h2>
        <ul id="hosted-readiness-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Durable Progress History</h2>
        <ul id="progress-history-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Core Module Links</h2>
        <ul id="module-links-list"></ul>
      </section>
      <section class="panel span-12">
        <h2>Payload Preview</h2>
        <pre id="payload-preview"></pre>
      </section>
    </div>
  </main>
  <script>
    const initialPayload = {raw_json};
    const heroStatus = document.getElementById("hero-status");
    const heroUseful = document.getElementById("hero-useful");
    const heroWired = document.getElementById("hero-wired");
    const heroSeams = document.getElementById("hero-seams");
    const statusNote = document.getElementById("progress-status-note");
    const focusSelect = document.getElementById("progress-focus-module");
    const focusReason = document.getElementById("progress-focus-reason");
    const focusNote = document.getElementById("progress-focus-note");
    const moduleStatusList = document.getElementById("module-status-list");
    const progressItemsList = document.getElementById("progress-items-list");
    const level3ChecklistList = document.getElementById("level3-checklist-list");
    const readinessDetailList = document.getElementById("readiness-detail-list");
    const seamHighlightsList = document.getElementById("seam-highlights-list");
    const laneFailureList = document.getElementById("lane-failure-list");
    const hostedReadinessList = document.getElementById("hosted-readiness-list");
    const progressHistoryList = document.getElementById("progress-history-list");
    const moduleLinksList = document.getElementById("module-links-list");
    const payloadPreview = document.getElementById("payload-preview");
    let currentPayload = initialPayload;
    let currentDetailIndex = 0;

    function esc(value) {{
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function li(title, summary, detail = "") {{
      return `<li><strong>${{esc(title)}}</strong><span>${{esc(summary)}}</span>${{detail ? `<span>${{esc(detail)}}</span>` : ""}}</li>`;
    }}

    function moduleOptionsMarkup(items, selected) {{
      return (Array.isArray(items) ? items : []).map((item) => {{
        const moduleName = String(item.module || item.title || "").trim() || "Progress";
        const chosen = moduleName === selected ? " selected" : "";
        return `<option value="${{esc(moduleName)}}"${{chosen}}>${{esc(moduleName)}}</option>`;
      }}).join("");
    }}

    function progressRow(item, index) {{
      return `
        <li>
          <strong>${{esc(item.module || "Progress Module")}}</strong>
          <span>${{esc(item.summary || "No progress summary captured yet.")}}</span>
          <span>${{esc(item.evidence || "No evidence captured yet.")}}</span>
          <code class="readiness-chip">${{esc(`${{item.roadmap_level || "Level 3"}} · ${{item.status_label || item.status || "wired"}}`)}}</code>
          <div class="action-row">
            <button type="button" data-progress-index="${{esc(String(index))}}">Inspect Readiness</button>
          </div>
        </li>
      `;
    }}

    function checklistRow(item) {{
      const files = Array.isArray(item.exact_files) ? item.exact_files : [];
      const routes = Array.isArray(item.proof_routes) ? item.proof_routes : [];
      return `
        <li>
          <strong>${{esc(item.title || "Remaining Slice")}}</strong>
          <span>${{esc(item.area || "Level 3")}}</span>
          <span>${{esc(item.why_open || "No remaining gap summary captured yet.")}}</span>
          <span>${{esc(item.live_signal || "No live signal captured yet.")}}</span>
          <code>Files: ${{esc(files.join(" | "))}}</code>
          <code>Next Recommended Slice: ${{esc(item.next_slice || "No next slice recorded yet.")}}</code>
          <div class="route-links">
            ${{routes.map((route) => `<a href="${{esc(route)}}">${{esc(route)}}</a>`).join("")}}
          </div>
        </li>
      `;
    }}

    function renderDetail(payload, index) {{
      const board = payload.progress_dashboard || {{}};
      const items = Array.isArray(board.items) ? board.items : [];
      const item = items[index] || items[0] || null;
      currentDetailIndex = item ? Math.max(0, index) : 0;
      readinessDetailList.innerHTML = item
        ? [
            li("Module", item.module || "Progress Module", item.roadmap_level || "Level 3"),
            li("Status", item.status || "Wired", item.status_label || ""),
            li("Summary", item.summary || "No summary captured."),
            li("Evidence", item.evidence || "No evidence captured."),
            li("Next Slice", payload.progress_next_focus || "No next focus recorded yet."),
          ].join("")
        : '<li><strong>No progress detail available.</strong><span>Select a readiness row to inspect it.</span></li>';
    }}

    function render(payload) {{
      currentPayload = payload;
      const board = payload.progress_dashboard || {{}};
      const counts = board.counts || {{}};
      const seamTracker = payload.seam_tracker || {{}};
      const laneProgress = payload.lane_progress || {{}};
      const failureRecovery = payload.failure_recovery || {{}};
      const hostedDeployment = payload.hosted_deployment || {{}};
      const progressPersistence = payload.progress_persistence || {{}};
      const focusControl = payload.focus_control || {{}};
      const latestFocus = focusControl.latest || {{}};
      const moduleLinks = Array.isArray((payload.core_modules || {{}}).items) ? payload.core_modules.items : [];

      heroStatus.textContent = payload.status || "Wired";
      heroUseful.textContent = String(counts.useful || 0);
      heroWired.textContent = String(counts.wired || 0);
      heroSeams.textContent = String(seamTracker.item_count || 0);
      statusNote.textContent = payload.summary || "No progress summary captured yet.";

      moduleStatusList.innerHTML = [
        li("What Became Real", payload.what_became_real || "No progress seam note recorded yet."),
        li("What Remains Partial", payload.remains_partial || "No remaining partials recorded."),
        li("Proof API", "/api/progress/module", "/api/command-center"),
        li("Seam Summary", seamTracker.summary || "No seam summary captured."),
        li("Current Next Focus", payload.progress_next_focus || "No next focus recorded yet.", latestFocus.reason || "No operator rationale recorded yet."),
      ].join("");

      focusSelect.innerHTML = moduleOptionsMarkup(board.items || [], payload.progress_next_focus || "");
      focusReason.value = latestFocus.reason || "";

      progressItemsList.innerHTML = (Array.isArray(board.items) ? board.items : []).map((item, index) => progressRow(item, index)).join("") || '<li><strong>No progress rows loaded.</strong><span>The dedicated progress module will surface readiness rows here.</span></li>';

      const checklist = payload.level3_checklist || {{}};
      level3ChecklistList.innerHTML = (Array.isArray(checklist.items) ? checklist.items : []).map((item) => checklistRow(item)).join("") || '<li><strong>No remaining Level 3 checklist loaded.</strong><span>The live progress module will surface remaining slices here.</span></li>';

      seamHighlightsList.innerHTML = (Array.isArray(seamTracker.items) ? seamTracker.items : []).slice(0, 4).map((item) => `
        <li>
          <strong>${{esc(item.name || "Seam")}}</strong>
          <span>${{esc(item.what_became_real || item.module || "No seam outcome recorded.")}}</span>
          <span>${{esc(item.remains_partial || item.commit_status || "")}}</span>
          <div class="route-links">${{missionRouteLinks(item.related_missions || [])}}</div>
        </li>
      `).join("") || '<li><strong>No seam highlights loaded.</strong><span>Seam tracker evidence will appear here.</span></li>';

      laneFailureList.innerHTML = [
        li("Lane Posture", `${{laneProgress.branch || "unknown branch"}} · ${{laneProgress.head || "unknown head"}}`, `${{laneProgress.dirty_count || 0}} local change(s)`),
        li("Recent Commit", (Array.isArray(laneProgress.recent_commits) ? laneProgress.recent_commits[0] : "") || "No recent commit captured."),
        li("Failure & Recovery", `${{failureRecovery.integration_issue_count || 0}} integration issue(s)`, `${{failureRecovery.pending_approval_count || 0}} pending approval gate(s)`),
      ].join("");

      hostedReadinessList.innerHTML = [
        li("Hosted URL", hostedDeployment.hosted_url || "https://jarvis.teambinion.org", hostedDeployment.edge_provider || "Hosted edge provider not captured."),
        li("Deploy Mode", hostedDeployment.deploy_mode || "unknown", hostedDeployment.remote_detail || "No deploy mode detail captured."),
        li("Deploy Proof", Array.isArray(hostedDeployment.proof_files) ? hostedDeployment.proof_files.join(" | ") : "No deploy proof files captured.", hostedDeployment.next_action || "No deploy next action recorded yet."),
      ].join("");

      progressHistoryList.innerHTML = [
        li("History Count", String(payload.counts?.history_count ?? progressPersistence.history_count ?? 0), payload.proof_paths?.progress_snapshot_history || "No history proof path recorded."),
        li("Latest Snapshot", progressPersistence.latest?.saved_at || "No snapshot recorded yet.", progressPersistence.latest?.next_focus || "No next focus recorded yet."),
        li("Focus History", String(payload.counts?.focus_history_count ?? focusControl.history_count ?? 0), payload.proof_paths?.progress_focus_history || "No focus history proof path recorded."),
        ...(Array.isArray(progressPersistence.recent) ? progressPersistence.recent.slice(0, 4).map((entry) => li(
          `${{entry.branch || "unknown branch"}} @ ${{entry.head || "unknown head"}}`,
          `Dirty: ${{entry.dirty_count ?? 0}} · Next Focus: ${{entry.next_focus || "none"}}`,
          `${{Object.entries(entry.progress_counts || {{}}).map(([key, value]) => `${{key}}=${{value}}`).join(" · ") || "No readiness counts"}}`
        )) : []),
        ...(Array.isArray(focusControl.recent) ? focusControl.recent.slice(0, 3).map((entry) => li(
          `Operator Focus: ${{entry.module || "Progress"}}`,
          entry.reason || "No operator rationale recorded.",
          `${{entry.actor || "Chris"}} · ${{entry.saved_at || "unknown time"}}`
        )) : []),
        ...(Array.isArray(progressPersistence.latest?.seam_items) ? progressPersistence.latest.seam_items.slice(0, 3).map((entry) => `
          <li>
            <strong>${{esc(`Seam History: ${{entry.name || "Seam"}}`)}}</strong>
            <span>${{esc(entry.what_became_real || entry.module || "No seam outcome recorded.")}}</span>
            <span>${{esc(entry.remains_partial || entry.status || "")}}</span>
            <div class="route-links">${{missionRouteLinks(entry.related_missions || [])}}</div>
          </li>
        `) : []),
      ].join("");

      moduleLinksList.innerHTML = moduleLinks.slice(0, 6).map((item) => li(
        item.title || "Module",
        item.screen_path || "/command-center",
        item.evidence || item.summary || ""
      )).join("") || '<li><strong>No module links loaded.</strong><span>Core module evidence will appear here.</span></li>';

      payloadPreview.textContent = JSON.stringify(payload, null, 2);
      renderDetail(payload, currentDetailIndex);
    }}

    async function saveProgressFocus() {{
      const module = String(focusSelect.value || "").trim();
      const reason = String(focusReason.value || "").trim();
      if (!module) {{
        focusNote.textContent = "Choose a module before saving the next focus.";
        return;
      }}
      focusNote.textContent = `Saving next focus for ${{module}}…`;
      try {{
        const response = await fetch("/api/progress/focus", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            actor: "Chris",
            module,
            reason: reason || `Progress focus moved to ${{module}}.`,
            route: "/progress-center",
          }}),
        }});
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.detail || payload.error || "Progress focus save failed");
        }}
        focusNote.textContent = `Next focus saved for ${{payload.focus?.module || module}}.`;
        await refreshProgressState();
      }} catch (error) {{
        focusNote.textContent = `Save failed: ${{String(error)}}`;
      }}
    }}

    async function refreshProgressState() {{
      statusNote.textContent = "Refreshing progress module state…";
      try {{
        const response = await fetch("/api/progress/module");
        const payload = await response.json();
        render(payload);
        statusNote.textContent = payload.summary || "Progress module refreshed.";
      }} catch (error) {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }}
    }}

    document.getElementById("refresh-progress").addEventListener("click", () => {{
      refreshProgressState().catch((error) => {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }});
    }});
    document.getElementById("save-progress-focus").addEventListener("click", () => {{
      saveProgressFocus().catch((error) => {{
        focusNote.textContent = `Save failed: ${{String(error)}}`;
      }});
    }});

    window.setInterval(() => {{
      refreshProgressState().catch(() => {{}});
    }}, 60000);

    progressItemsList.addEventListener("click", (event) => {{
      const button = event.target.closest("[data-progress-index]");
      if (!button) return;
      const index = Number(button.getAttribute("data-progress-index") || "0");
      renderDetail(currentPayload, index);
      statusNote.textContent = "Readiness detail updated from the live progress snapshot.";
    }});

    render(initialPayload);
  </script>
</body>
</html>
"""


def render_daily_brief_module_page(payload: dict) -> str:
    raw_json = json.dumps(payload, indent=2)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Daily Brief</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #071018;
      --bg-2: #091522;
      --panel: rgba(9, 20, 33, 0.92);
      --line: rgba(121, 216, 255, 0.14);
      --text: #edf7ff;
      --muted: #9eb8cb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "SF Pro Display", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top, rgba(121, 216, 255, 0.12), transparent 36%),
        linear-gradient(180deg, #040b12 0%, var(--bg) 44%, var(--bg-2) 100%);
      color: var(--text);
    }}
    .shell {{ max-width: 1420px; margin: 0 auto; padding: 36px 24px 60px; }}
    .hero {{
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 28px;
      background: linear-gradient(180deg, rgba(10, 22, 35, 0.96), rgba(7, 16, 27, 0.92));
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.28);
    }}
    .eyebrow {{ color: #79d8ff; letter-spacing: 0.18em; text-transform: uppercase; font-size: 12px; }}
    h1 {{ margin: 10px 0 12px; font-size: clamp(34px, 5vw, 56px); }}
    h2 {{ margin-top: 0; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 22px;
    }}
    .stat, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
    }}
    .stat span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .stat strong {{ display: block; margin-top: 6px; font-size: 24px; }}
    .layout {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .span-4 {{ grid-column: span 4; }}
    .span-6 {{ grid-column: span 6; }}
    .span-8 {{ grid-column: span 8; }}
    .span-12 {{ grid-column: span 12; }}
    ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    li {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.03);
    }}
    li strong {{ display: block; margin-bottom: 4px; }}
    li span {{ color: var(--muted); display: block; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    .controls {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }}
    a, button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(121, 216, 255, 0.12);
      color: var(--text);
      text-decoration: none;
      font: inherit;
      cursor: pointer;
    }}
    select, textarea, input {{
      width: 100%;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(4, 12, 20, 0.92);
      color: var(--text);
      padding: 12px 14px;
      font: inherit;
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      border-radius: 16px;
      padding: 14px;
      border: 1px solid var(--line);
      background: rgba(3, 10, 18, 0.9);
      color: #d7e8f4;
      overflow-x: auto;
    }}
    .status-note {{ min-height: 1.3em; color: var(--muted); margin-top: 10px; }}
    .loop-actions {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }}
    .loop-actions select {{ max-width: 220px; }}
    @media (max-width: 980px) {{
      .span-4, .span-6, .span-8, .span-12 {{ grid-column: span 12; }}
      .controls {{ flex-direction: column; align-items: stretch; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="eyebrow">Level 3 Core Module</div>
      <h1>JARVIS Daily Brief</h1>
      <p>A dedicated daily-brief workspace inside JARVIS with live briefing text, today-board priorities, calendar context, open-loop pressure, and inline follow-through actions. This promotes Daily Brief out of the shell packet into a real day-operations module.</p>
      <div class="controls">
        <select id="brief-actor"></select>
        <a href="/command-center">Back to Command Center</a>
        <button type="button" id="refresh-brief">Refresh Daily Brief</button>
        <button type="button" id="generate-live-brief">Generate Live Brief</button>
      </div>
      <div class="stats">
        <div class="stat"><span>Status</span><strong id="hero-status">Loading...</strong></div>
        <div class="stat"><span>Priorities</span><strong id="hero-priorities">0</strong></div>
        <div class="stat"><span>Waiting On You</span><strong id="hero-waiting">0</strong></div>
        <div class="stat"><span>Notifications</span><strong id="hero-notifications">0</strong></div>
      </div>
      <p class="status-note" id="brief-status-note">Loading daily brief module state…</p>
    </section>
    <div class="layout">
      <section class="panel span-4">
        <h2>Module Status</h2>
        <ul id="module-status-list"></ul>
      </section>
      <section class="panel span-8">
        <h2>Briefing Text</h2>
        <pre id="briefing-text"></pre>
      </section>
      <section class="panel span-6">
        <h2>Today Priorities</h2>
        <ul id="priorities-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Carry Forward</h2>
        <ul id="carry-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Calendar</h2>
        <ul id="calendar-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Live Brief Packet</h2>
        <pre id="live-brief-output">Generate a live brief packet to inspect the richer builder output.</pre>
      </section>
      <section class="panel span-12">
        <h2>Open Loops</h2>
        <ul id="open-loops-list"></ul>
        <p class="status-note" id="open-loop-note">Apply an open-loop action here to turn the daily brief into a real follow-through surface.</p>
      </section>
      <section class="panel span-6">
        <h2>Recent Brief Continuity</h2>
        <ul id="brief-activity-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Assistant Notifications</h2>
        <ul id="notifications-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Payload Preview</h2>
        <pre id="payload-preview"></pre>
      </section>
    </div>
  </main>
  <script>
    const initialPayload = {raw_json};
    const actorSelect = document.getElementById("brief-actor");
    const heroStatus = document.getElementById("hero-status");
    const heroPriorities = document.getElementById("hero-priorities");
    const heroWaiting = document.getElementById("hero-waiting");
    const heroNotifications = document.getElementById("hero-notifications");
    const statusNote = document.getElementById("brief-status-note");
    const moduleStatusList = document.getElementById("module-status-list");
    const briefingText = document.getElementById("briefing-text");
    const prioritiesList = document.getElementById("priorities-list");
    const carryList = document.getElementById("carry-list");
    const calendarList = document.getElementById("calendar-list");
    const notificationsList = document.getElementById("notifications-list");
    const openLoopsList = document.getElementById("open-loops-list");
    const briefActivityList = document.getElementById("brief-activity-list");
    const payloadPreview = document.getElementById("payload-preview");
    const liveBriefOutput = document.getElementById("live-brief-output");
    let currentPayload = initialPayload;

    function esc(value) {{
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function li(title, summary, detail = "") {{
      return `<li><strong>${{esc(title)}}</strong><span>${{esc(summary)}}</span>${{detail ? `<span>${{esc(detail)}}</span>` : ""}}</li>`;
    }}

    function actorOptionsMarkup(items, selectedId) {{
      return (Array.isArray(items) ? items : []).map((item) => {{
        const value = item.id || item.label || "Chris";
        const selected = value === selectedId ? " selected" : "";
        return `<option value="${{esc(value)}}"${{selected}}>${{esc(item.label || value)}}</option>`;
      }}).join("");
    }}

    function actionOptionsMarkup(actions) {{
      return (Array.isArray(actions) ? actions : []).map((action) => `<option value="${{esc(action.id || "")}}">${{esc(action.label || action.id || "Action")}}</option>`).join("");
    }}

    function render(payload) {{
      currentPayload = payload;
      const counts = payload.counts || {{}};
      const board = payload.today_board || {{}};
      const boardOpenLoops = (board.open_loops || {{}}).summary || {{}};
      const priorities = Array.isArray(board.priorities) ? board.priorities : [];
      const carry = Array.isArray(board.carry) ? board.carry : [];
      const calendar = Array.isArray(board.calendar) ? board.calendar : [];
      const notifications = Array.isArray(board.assistant_notifications) ? board.assistant_notifications : [];
      const openLoops = Array.isArray((payload.open_loops || {{}}).items) ? payload.open_loops.items : [];

      actorSelect.innerHTML = actorOptionsMarkup(payload.actor_options, payload.actor || "Chris");
      heroStatus.textContent = payload.status || "Stubbed";
      heroPriorities.textContent = String(counts.priority_count || priorities.length || 0);
      heroWaiting.textContent = String(counts.waiting_on_you || boardOpenLoops.waiting_on_you || 0);
      heroNotifications.textContent = String(counts.notification_count || notifications.length || 0);
      statusNote.textContent = payload.summary || "No daily brief summary captured yet.";

      moduleStatusList.innerHTML = [
        li("What Became Real", payload.what_became_real || "No brief seam note recorded yet."),
        li("What Remains Partial", payload.remains_partial || "No partial work recorded."),
        li("Proof API", "/api/briefing/module", "/api/briefing, /api/today-board, /api/open-loops"),
        li("Headline", payload.headline || "No briefing headline captured yet."),
        li("Needs Revisit", String(counts.needs_revisit || boardOpenLoops.needs_revisit || 0)),
      ].join("");

      briefingText.textContent = payload.briefing_text || "No briefing text captured yet.";
      prioritiesList.innerHTML = priorities.map((item) => li(
        item.title || "Priority",
        item.next_action || item.status || "No next action recorded.",
        item.owner_agent || ""
      )).join("") || '<li><strong>No priorities loaded.</strong><span>The today board will populate priorities here when available.</span></li>';
      carryList.innerHTML = carry.map((item, index) => li(`Carry ${{index + 1}}`, item)).join("") || '<li><strong>No carry-forward lines.</strong><span>The day is currently light.</span></li>';
      calendarList.innerHTML = calendar.map((item) => li(
        item.summary || "(Untitled event)",
        item.start || item.when || "No start time recorded.",
        item.source || ""
      )).join("") || '<li><strong>No calendar items loaded.</strong><span>Upcoming events will appear here.</span></li>';
      notificationsList.innerHTML = notifications.map((item) => li(
        item.title || item.summary || "Notification",
        item.summary || item.detail || "No detail recorded.",
        item.channel || item.urgency || ""
      )).join("") || '<li><strong>No unread assistant notifications.</strong><span>Fresh assistant notices will appear here.</span></li>';
      openLoopsList.innerHTML = openLoops.map((item) => `
        <li data-domain="${{esc(item.domain || "")}}" data-item-id="${{esc(item.item_id || "")}}" data-item-title="${{esc(item.title || "Open loop")}}" data-item-summary="${{esc(item.summary || item.next_action || "No summary recorded.")}}">
          <strong>${{esc(item.title || "Open loop")}}</strong>
          <span>${{esc(item.summary || item.next_action || "No summary recorded.")}}</span>
          <span>${{esc(`${{item.domain || "general"}} · ${{item.status || "open"}} · ${{item.owner_agent || "JARVIS"}}`)}}</span>
          <div class="loop-actions">
            <select class="open-loop-action">${{actionOptionsMarkup(item.available_actions)}}</select>
            <button type="button" class="apply-open-loop-action">Apply Action</button>
          </div>
        </li>
      `).join("") || '<li><strong>No open loops surfaced.</strong><span>The day currently has no visible follow-through pressure.</span></li>';
      briefActivityList.innerHTML = (Array.isArray(payload.recent_activity) ? payload.recent_activity : []).length
        ? payload.recent_activity.map((item) => li(item.title || "Brief action", item.subtitle || item.actor || "Operator continuity", item.detail || item.route_label || "")).join("")
        : '<li><strong>No brief continuity yet.</strong><span>Daily Brief actions will show up here once you move live open-loop work forward.</span></li>';
      payloadPreview.textContent = JSON.stringify(payload, null, 2);
    }}

    async function refreshBrief() {{
      const actor = actorSelect.value || "Chris";
      statusNote.textContent = `Refreshing daily brief for ${{actor}}…`;
      try {{
        const response = await fetch(`/api/briefing/module?actor=${{encodeURIComponent(actor)}}`);
        const payload = await response.json();
        render(payload);
        statusNote.textContent = payload.summary || "Daily brief refreshed.";
      }} catch (error) {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }}
    }}

    async function generateLiveBrief() {{
      const actor = actorSelect.value || "Chris";
      liveBriefOutput.textContent = `Generating live brief for ${{actor}}…`;
      try {{
        const response = await fetch(`/api/briefing/live?actor=${{encodeURIComponent(actor)}}`);
        const payload = await response.json();
        liveBriefOutput.textContent = JSON.stringify(payload, null, 2);
      }} catch (error) {{
        liveBriefOutput.textContent = `Live brief failed: ${{String(error)}}`;
      }}
    }}

    async function applyOpenLoopAction(button) {{
      const host = button.closest("li[data-domain]");
      if (!host) return;
      const actionSelect = host.querySelector(".open-loop-action");
      const actor = actorSelect.value || "Chris";
      const note = document.getElementById("open-loop-note");
      note.textContent = "Applying open-loop action…";
      try {{
        const response = await fetch("/api/open-loops/action", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            actor,
            domain: host.getAttribute("data-domain") || "",
            item_id: host.getAttribute("data-item-id") || "",
            action: actionSelect ? actionSelect.value : "",
            item_title: host.getAttribute("data-item-title") || "Open loop",
            item_summary: host.getAttribute("data-item-summary") || "",
            route: "/briefing-center",
            route_label: "Open Daily Brief",
            activity_domain: "briefing",
            why_now: "Daily Brief follow-through moved a live open-loop item forward.",
            result_summary: "Daily Brief continuity updated from an open-loop action.",
            related_kind: "open-loop",
            related_label: host.getAttribute("data-item-title") || "Open loop",
          }}),
        }});
        const payload = await response.json();
        note.textContent = payload.ok ? `Applied ${{payload.action || "action"}}.` : "Open-loop action returned a response.";
        await refreshBrief();
      }} catch (error) {{
        note.textContent = `Open-loop action failed: ${{String(error)}}`;
      }}
    }}

    document.getElementById("refresh-brief").addEventListener("click", () => {{
      refreshBrief().catch((error) => {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }});
    }});
    document.getElementById("generate-live-brief").addEventListener("click", () => {{
      generateLiveBrief().catch((error) => {{
        liveBriefOutput.textContent = `Live brief failed: ${{String(error)}}`;
      }});
    }});
    actorSelect.addEventListener("change", () => {{
      refreshBrief().catch((error) => {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }});
    }});
    openLoopsList.addEventListener("click", (event) => {{
      const button = event.target.closest(".apply-open-loop-action");
      if (!button) return;
      applyOpenLoopAction(button).catch((error) => {{
        document.getElementById("open-loop-note").textContent = `Open-loop action failed: ${{String(error)}}`;
      }});
    }});
    render(initialPayload);
  </script>
</body>
</html>
"""


def render_health_module_page(payload: dict) -> str:
    raw_json = json.dumps(payload, indent=2)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Health</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #050d14;
      --bg-2: #09131d;
      --panel: rgba(8, 18, 29, 0.92);
      --panel-2: rgba(13, 27, 39, 0.9);
      --line: rgba(133, 224, 187, 0.12);
      --line-strong: rgba(133, 224, 187, 0.24);
      --text: #ecf7ff;
      --muted: #9db7cc;
      --good: #9ce7bf;
      --warn: #ffd37d;
      --alert: #ff9d9d;
      --accent: #79e0ab;
      --accent-2: #8ee2ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "SF Pro Display", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(133, 224, 187, 0.18), transparent 22%),
        radial-gradient(circle at top right, rgba(142, 226, 255, 0.12), transparent 20%),
        radial-gradient(circle at 50% 100%, rgba(255, 211, 125, 0.08), transparent 24%),
        linear-gradient(180deg, #030910 0%, var(--bg) 42%, var(--bg-2) 100%);
      color: var(--text);
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background: linear-gradient(135deg, rgba(255,255,255,0.025), transparent 36%);
      opacity: 0.9;
    }}
    .shell {{ position: relative; max-width: 1360px; margin: 0 auto; padding: 24px 24px 60px; }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 18px;
      padding: 14px 18px;
      border: 1px solid var(--line);
      border-radius: 24px;
      background: rgba(7, 14, 23, 0.72);
      backdrop-filter: blur(18px);
      box-shadow: 0 16px 44px rgba(0, 0, 0, 0.22);
    }}
    .topbar strong {{
      display: block;
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
    }}
    .topbar span {{
      display: block;
      color: var(--muted);
      margin-top: 4px;
      line-height: 1.45;
    }}
    .topbar-links {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 10px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(300px, 0.85fr);
      gap: 18px;
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 30px;
      background: linear-gradient(180deg, rgba(10, 22, 34, 0.96), rgba(7, 15, 25, 0.92));
      box-shadow: 0 24px 56px rgba(0, 0, 0, 0.32);
      backdrop-filter: blur(18px);
    }}
    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 9px;
      color: var(--accent);
      letter-spacing: 0.18em;
      text-transform: uppercase;
      font-size: 12px;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid rgba(133, 224, 187, 0.22);
      background: rgba(133, 224, 187, 0.07);
    }}
    .eyebrow::before {{
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: currentColor;
      box-shadow: 0 0 16px currentColor;
    }}
    h1 {{ margin: 14px 0 12px; font-size: clamp(34px, 5vw, 60px); line-height: 0.95; letter-spacing: -0.05em; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .hero-copy p {{ max-width: 68ch; font-size: 1.02rem; }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
      margin-top: 22px;
    }}
    .stat, .panel {{
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
    }}
    .stat {{
      background:
        linear-gradient(180deg, rgba(13, 27, 39, 0.92), rgba(8, 18, 29, 0.98)),
        radial-gradient(circle at top right, rgba(142, 226, 255, 0.14), transparent 35%);
    }}
    .stat span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .stat strong {{ display: block; margin-top: 6px; font-size: 24px; }}
    .panel {{
      background: var(--panel);
      box-shadow: 0 18px 36px rgba(0, 0, 0, 0.22);
    }}
    .hero-side {{
      display: grid;
      gap: 14px;
      align-content: start;
    }}
    .hero-note {{
      padding: 18px;
      border-radius: 22px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
    }}
    .hero-note strong,
    .section-label {{
      display: block;
      margin-bottom: 8px;
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
    }}
    .hero-note p {{ margin: 0; color: var(--text); }}
    .hero-note ul {{ margin-top: 10px; }}
    .hero-note li {{
      background: rgba(255,255,255,0.025);
      border-radius: 16px;
    }}
    .glance-strip {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
    }}
    .glance-card {{
      padding: 16px;
      border-radius: 22px;
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(12, 23, 35, 0.9), rgba(7, 15, 25, 0.96));
    }}
    .glance-card strong {{
      display: block;
      margin-bottom: 8px;
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .glance-card span {{
      display: block;
      color: var(--muted);
      line-height: 1.55;
    }}
    .layout {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .span-4 {{ grid-column: span 4; }}
    .span-5 {{ grid-column: span 5; }}
    .span-6 {{ grid-column: span 6; }}
    .span-7 {{ grid-column: span 7; }}
    .span-8 {{ grid-column: span 8; }}
    h2 {{ margin: 0 0 12px; font-size: 1.2rem; letter-spacing: -0.03em; }}
    ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    li {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
    }}
    li strong {{ display: block; margin-bottom: 4px; }}
    li span {{ color: var(--muted); display: block; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    a, button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: linear-gradient(135deg, rgba(133, 224, 187, 0.16), rgba(142, 226, 255, 0.12));
      color: var(--text);
      text-decoration: none;
      font: inherit;
      cursor: pointer;
    }}
    a:hover, button:hover {{ border-color: var(--line-strong); }}
    .good {{ color: var(--good); }}
    .warn {{ color: var(--warn); }}
    .alert {{ color: var(--alert); }}
    form {{ display: grid; gap: 12px; }}
    label {{ display: grid; gap: 6px; color: var(--muted); font-size: 13px; }}
    textarea, input {{
      width: 100%;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(4, 12, 20, 0.92);
      color: var(--text);
      padding: 12px 14px;
      font: inherit;
    }}
    textarea {{ min-height: 120px; }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      border-radius: 16px;
      padding: 14px;
      border: 1px solid var(--line);
      background: rgba(3, 10, 18, 0.9);
      color: #d7e8f4;
      overflow-x: auto;
    }}
    .status-note {{ min-height: 1.3em; color: var(--muted); margin-top: 10px; }}
    @media (max-width: 980px) {{
      .hero,
      .glance-strip {{
        grid-template-columns: 1fr;
      }}
      .span-4, .span-5, .span-6, .span-7, .span-8 {{ grid-column: span 12; }}
      .topbar {{
        flex-direction: column;
        align-items: flex-start;
      }}
      .topbar-links {{
        justify-content: flex-start;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="topbar">
      <div>
        <strong>JARVIS Health Intelligence Desktop Experience</strong>
        <span>Live health command center with drift posture, triage, objectives, red-flag continuity, and room for Helen Cho and the health agent stack.</span>
      </div>
      <div class="topbar-links">
        <a href="/api/health/module">Module JSON</a>
        <a href="/api/health/drift/scan">Drift Scan API</a>
        <a href="/command-center">Command Center</a>
      </div>
    </section>
    <section class="hero">
      <div class="hero-copy">
        <div class="eyebrow">Level 3 Core Module</div>
        <h1>JARVIS Health</h1>
        <p>A dedicated health workspace inside JARVIS with live drift posture, baseline deviation evidence, current objectives, recovery coaching context, and symptom triage. This is now a real module surface, not a storyboard-only placeholder.</p>
        <div class="actions">
          <a href="/command-center">Back to Command Center</a>
          <button type="button" id="refresh-health">Refresh Health State</button>
        </div>
        <div class="stats">
          <div class="stat"><span>Status</span><strong id="hero-status">Loading...</strong></div>
          <div class="stat"><span>Signals</span><strong id="hero-signals">0</strong></div>
          <div class="stat"><span>Active Clusters</span><strong id="hero-clusters">0</strong></div>
          <div class="stat"><span>Objectives</span><strong id="hero-objectives">0</strong></div>
        </div>
        <p class="status-note" id="health-status-note">Loading health module state…</p>
      </div>
      <aside class="hero-side">
        <div class="hero-note">
          <strong>Health command center</strong>
          <p>The mockup direction is now anchored to the real product state: vitals and drift on the left, coaching and triage in the same operating surface, and room for future deeper care workflows.</p>
          <ul>
            <li><strong>Personalized and private</strong><span>State stays tied to the real module payload instead of decorative cards.</span></li>
            <li><strong>Family and care aware</strong><span>Designed to leave space for Helen Cho, care circles, and continuity-driven escalation.</span></li>
          </ul>
        </div>
        <div class="hero-note">
          <div class="section-label">Storyboards preserved, product made real</div>
          <ul>
            <li><strong>Vitals &amp; Trends</strong><span>Current signals and deviations render from live or seeded module state.</span></li>
            <li><strong>Recovery &amp; Coaching</strong><span>Objectives, red flags, and triage stay actionable from one view.</span></li>
          </ul>
        </div>
      </aside>
    </section>
    <section class="glance-strip">
      <div class="glance-card">
        <strong>Daily Readiness</strong>
        <span>Health posture, baseline drift, and one-next-action stay visible in the same command chamber.</span>
      </div>
      <div class="glance-card">
        <strong>Vitals &amp; Trends</strong>
        <span>Signal freshness and deviations are presented as operating context instead of buried JSON only.</span>
      </div>
      <div class="glance-card">
        <strong>Recovery &amp; Coaching</strong>
        <span>Objectives, flags, and triage keep the coaching thread connected to real state.</span>
      </div>
      <div class="glance-card">
        <strong>Family &amp; Care Circle</strong>
        <span>Leaves space for broader care workflows without losing the current Level 3 truth.</span>
      </div>
    </section>
    <div class="layout">
      <section class="panel span-8">
        <h2>Drift Overview</h2>
        <ul id="drift-overview-list"></ul>
      </section>
      <section class="panel span-4">
        <h2>Module Status</h2>
        <ul id="module-status-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Current Signals</h2>
        <ul id="signals-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Baseline Deviations</h2>
        <ul id="deviations-list"></ul>
      </section>
      <section class="panel span-5">
        <h2>Quarterly Objectives</h2>
        <ul id="objectives-list"></ul>
      </section>
      <section class="panel span-7">
        <h2>Personalized Red Flags</h2>
        <ul id="red-flags-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Symptom Triage</h2>
        <form id="triage-form">
          <label>Symptoms
            <textarea id="triage-symptoms" placeholder="Describe what is going on right now."></textarea>
          </label>
          <label>Duration
            <input id="triage-duration" placeholder="e.g. 2 hours, since yesterday">
          </label>
          <label>Context
            <input id="triage-context" placeholder="Medication change, workout, poor sleep, stress">
          </label>
          <button type="submit">Run Symptom Triage</button>
        </form>
        <p class="status-note" id="triage-note">Use this to test a real Health interaction against the live triage endpoint.</p>
        <pre id="triage-output">Awaiting symptom triage.</pre>
      </section>
      <section class="panel span-6">
        <h2>Save Health Objective</h2>
        <form id="objective-form">
          <label>Objective
            <input id="objective-title" placeholder="Lower A1c by improving post-meal glucose control">
          </label>
          <label>Domain
            <input id="objective-domain" placeholder="metabolic health">
          </label>
          <label>Why It Matters
            <textarea id="objective-why" placeholder="Connect this objective to current drift, quality of life, or long-term risk reduction."></textarea>
          </label>
          <label>Baseline
            <input id="objective-baseline" placeholder="A1c 7.3%, post-dinner walks inconsistent">
          </label>
          <label>Target
            <input id="objective-target" placeholder="A1c under 6.8% and post-dinner walk 5x/week">
          </label>
          <label>Weekly Actions
            <textarea id="objective-actions" placeholder="One action per line"></textarea>
          </label>
          <label>Measurement Plan
            <textarea id="objective-measurement" placeholder="How will progress be measured each week?"></textarea>
          </label>
          <button type="submit">Save Health Objective</button>
        </form>
        <p class="status-note" id="objective-note">Use this to persist a real health objective into the quarterly store.</p>
        <pre id="objective-output">Awaiting objective save.</pre>
      </section>
      <section class="panel span-6">
        <h2>Recent Health Continuity</h2>
        <ul id="recent-activity-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Payload Preview</h2>
        <pre id="payload-preview"></pre>
      </section>
    </div>
  </main>
  <script>
    const initialPayload = {raw_json};
    const heroStatus = document.getElementById("hero-status");
    const heroSignals = document.getElementById("hero-signals");
    const heroClusters = document.getElementById("hero-clusters");
    const heroObjectives = document.getElementById("hero-objectives");
    const statusNote = document.getElementById("health-status-note");
    const triageNote = document.getElementById("triage-note");
    const driftOverviewList = document.getElementById("drift-overview-list");
    const moduleStatusList = document.getElementById("module-status-list");
    const signalsList = document.getElementById("signals-list");
    const deviationsList = document.getElementById("deviations-list");
    const objectivesList = document.getElementById("objectives-list");
    const redFlagsList = document.getElementById("red-flags-list");
    const triageOutput = document.getElementById("triage-output");
    const objectiveNote = document.getElementById("objective-note");
    const objectiveOutput = document.getElementById("objective-output");
    const recentActivityList = document.getElementById("recent-activity-list");
    const payloadPreview = document.getElementById("payload-preview");

    function esc(value) {{
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function li(title, summary, detail = "") {{
      return `<li><strong>${{esc(title)}}</strong><span>${{esc(summary)}}</span>${{detail ? `<span>${{esc(detail)}}</span>` : ""}}</li>`;
    }}

    async function recordOperatorAction(payload) {{
      await fetch("/api/activity/operator-action", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload),
      }});
    }}

    function render(payload) {{
      currentPayload = payload || {{}};
      const drift = payload.drift_scan || {{}};
      const signals = payload.current_signals || {{}};
      const deviations = Array.isArray(payload.baseline_deviations) ? payload.baseline_deviations : [];
      const objectives = Array.isArray(payload.objectives) ? payload.objectives : [];
      const redFlags = payload.red_flags || {{}};
      const activeClusters = Array.isArray(drift.active_clusters) ? drift.active_clusters : [];

      heroStatus.textContent = payload.status || "Stubbed";
      heroSignals.textContent = String(payload.signal_count || 0);
      heroClusters.textContent = String(payload.active_cluster_count || 0);
      heroObjectives.textContent = String(payload.objective_count || 0);
      statusNote.textContent = payload.summary || "No health summary captured yet.";

      moduleStatusList.innerHTML = [
        li("Availability", payload.available ? "Health data is live." : "Health data fell back to safe defaults."),
        li("What Became Real", payload.what_became_real || "No health seam note recorded yet."),
        li("What Remains Partial", payload.remains_partial || "No partial work recorded."),
        li("Proof API", "/api/health/module", "/api/health/drift/scan"),
      ].join("");

      driftOverviewList.innerHTML = [
        li("Overall Drift Status", drift.overall_drift_status || "unknown"),
        li("One Next Action", drift.one_next_action || "No next action captured."),
        li("Oracle Review Needed", String(Boolean(drift.oracle_review_needed))),
        ...activeClusters.slice(0, 4).map((item) => li(item.name || item.cluster_id || "Cluster", `${{item.severity || "unknown"}} · ${{item.confidence || "unknown"}}`, (item.signals_present || []).join(", "))),
      ].join("");

      signalsList.innerHTML = Object.entries(signals).slice(0, 8).map(([key, value]) => {{
        const item = value || {{}};
        return li(key, `${{item.value ?? "n/a"}} ${{item.unit || ""}}`, `${{item.source || "unknown"}} · ${{item.date || "undated"}}`);
      }}).join("") || '<li><strong>No live signals yet.</strong><span>Signal loading did not return any current health metrics.</span></li>';

      deviationsList.innerHTML = deviations.slice(0, 8).map((item) => {{
        const pct = item.deviation_pct ?? 0;
        return li(item.metric || "metric", `${{item.current}} vs baseline ${{item.baseline}} (${{
          pct >= 0 ? "+" : ""
        }}${{pct}}%)`, `${{item.significant ? "significant" : "watch"}} · ${{item.source || "unknown"}}`);
      }}).join("") || '<li><strong>No deviations yet.</strong><span>Baseline comparison has no live deviations to show.</span></li>';

      objectivesList.innerHTML = objectives.slice(0, 6).map((item) => li(item.objective || "Objective", item.target || "No target", item.domain || "No domain")).join("")
        || '<li><strong>No saved objectives yet.</strong><span>Quarterly objectives will appear here once they are defined.</span></li>';

      const urgent = (redFlags.contact_clinician_urgently || {{}}).patient_specific || [];
      const emergency = (redFlags.go_to_er || {{}}).patient_specific || [];
      const critical = (redFlags.absolute_contraindications || []);
      redFlagsList.innerHTML = [
        ...urgent.slice(0, 3).map((item) => li("Urgent", item)),
        ...emergency.slice(0, 3).map((item) => li("ER", item)),
        ...critical.slice(0, 2).map((item) => li(item.trigger || "Contraindication", item.action || "Critical rule")),
      ].join("") || '<li><strong>No red flags loaded.</strong><span>Personalized health red flags are unavailable right now.</span></li>';
      recentActivityList.innerHTML = (Array.isArray(payload.recent_activity) ? payload.recent_activity : []).length
        ? payload.recent_activity.map((item) => li(item.title || "Health action", item.subtitle || item.actor || "Operator continuity", item.detail || item.route_label || "")).join("")
        : '<li><strong>No health continuity recorded yet.</strong><span>Run triage or save a health objective to begin the route-level continuity trail.</span></li>';

      payloadPreview.textContent = JSON.stringify(payload, null, 2);
    }}

    async function refreshHealthState() {{
      statusNote.textContent = "Refreshing health module state…";
      try {{
        const response = await fetch("/api/health/module");
        const payload = await response.json();
        render(payload);
        statusNote.textContent = payload.summary || "Health module refreshed.";
      }} catch (error) {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }}
    }}

    async function runTriage(event) {{
      event.preventDefault();
      triageNote.textContent = "Running symptom triage…";
      try {{
        const response = await fetch("/api/health/symptom/triage", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            symptoms: document.getElementById("triage-symptoms").value,
            duration: document.getElementById("triage-duration").value,
            context: document.getElementById("triage-context").value,
          }}),
        }});
        const payload = await response.json();
        triageOutput.textContent = JSON.stringify(payload, null, 2);
        await recordOperatorAction({{
          actor: "Chris",
          domain: "health",
          action: "Run Symptom Triage",
          title: document.getElementById("triage-symptoms").value || "Health triage",
          detail: payload.oracle_pathway
            ? `Health triage routed to ${{payload.oracle_pathway}}.`
            : "Health triage completed from the live route.",
          why_now: "Health route ran a real symptom triage directly from the operator flow.",
          result_summary: payload.oracle_pathway
            ? `Triage pathway: ${{payload.oracle_pathway}}`
            : "Health triage completed.",
          route: "/health-center",
          route_label: "Open Health",
          related_kind: "health-triage",
          related_label: document.getElementById("triage-symptoms").value || "Health triage",
          succeeded: true,
        }});
        triageNote.textContent = payload.oracle_pathway
          ? `Triage complete: ${{payload.oracle_pathway}}`
          : "Triage complete.";
        await refreshHealthState();
      }} catch (error) {{
        triageNote.textContent = `Triage failed: ${{String(error)}}`;
      }}
    }}

    async function saveObjective(event) {{
      event.preventDefault();
      objectiveNote.textContent = "Saving health objective…";
      try {{
        const existingObjectives = Array.isArray(currentPayload.objectives) ? [...currentPayload.objectives] : [];
        const newObjective = {{
          objective: document.getElementById("objective-title").value,
          domain: document.getElementById("objective-domain").value,
          why_it_matters: document.getElementById("objective-why").value,
          baseline: document.getElementById("objective-baseline").value,
          target: document.getElementById("objective-target").value,
          weekly_actions: document.getElementById("objective-actions").value.split("\\n").map((item) => item.trim()).filter(Boolean),
          measurement_plan: document.getElementById("objective-measurement").value,
        }};
        const objectives = [...existingObjectives, newObjective];
        const response = await fetch("/api/health/quarterly/objectives", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ objectives }}),
        }});
        const payload = await response.json();
        objectiveOutput.textContent = JSON.stringify(payload, null, 2);
        if (!response.ok || payload.ok === false) {{
          throw new Error((payload.errors || []).join(" | ") || payload.error || "Objective save failed");
        }}
        await recordOperatorAction({{
          actor: "Chris",
          domain: "health",
          action: "Save Health Objective",
          title: newObjective.objective || "Health objective",
          detail: "Health objective saved into the quarterly objective store.",
          why_now: "Health route persisted a real coaching objective directly from the operator flow.",
          result_summary: `Saved ${{payload.count || objectives.length}} health objective(s).`,
          route: "/health-center",
          route_label: "Open Health",
          related_kind: "health-objective",
          related_label: newObjective.objective || "Health objective",
          succeeded: true,
        }});
        objectiveNote.textContent = "Health objective saved.";
        document.getElementById("objective-form").reset();
        await refreshHealthState();
      }} catch (error) {{
        objectiveNote.textContent = `Objective save failed: ${{String(error)}}`;
      }}
    }}

    document.getElementById("refresh-health").addEventListener("click", () => {{
      refreshHealthState().catch((error) => {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }});
    }});
    document.getElementById("triage-form").addEventListener("submit", runTriage);
    document.getElementById("objective-form").addEventListener("submit", saveObjective);
    render(initialPayload);
  </script>
</body>
</html>
"""


def render_huddle_module_page(payload: dict) -> str:
    raw_json = json.dumps(payload, indent=2)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Huddle</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #050d16;
      --bg-2: #09131d;
      --panel: rgba(8, 20, 33, 0.92);
      --line: rgba(121, 216, 255, 0.14);
      --text: #edf7ff;
      --muted: #9eb8cb;
      --good: #9ce7bf;
      --warn: #ffd37d;
      --alert: #ff9d9d;
      --accent: #79d8ff;
      --amber: #ddb66a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "SF Pro Display", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top, rgba(121, 216, 255, 0.14), transparent 36%),
        linear-gradient(180deg, #040b12 0%, var(--bg) 44%, var(--bg-2) 100%);
      color: var(--text);
    }}
    .shell {{ max-width: 1480px; margin: 0 auto; padding: 24px 24px 60px; }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 18px;
      padding: 14px 18px;
      border: 1px solid var(--line);
      border-radius: 24px;
      background: rgba(7, 13, 21, 0.76);
      backdrop-filter: blur(18px);
      box-shadow: 0 16px 42px rgba(0, 0, 0, 0.22);
    }}
    .topbar strong {{
      display: block;
      color: var(--amber);
      font-size: 12px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
    }}
    .topbar span {{
      display: block;
      color: var(--muted);
      margin-top: 4px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(300px, 0.8fr);
      gap: 18px;
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 30px;
      background: linear-gradient(180deg, rgba(10, 22, 35, 0.96), rgba(7, 16, 27, 0.92));
      box-shadow: 0 24px 56px rgba(0, 0, 0, 0.3);
    }}
    .eyebrow {{
      color: var(--accent);
      letter-spacing: 0.18em;
      text-transform: uppercase;
      font-size: 12px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid rgba(121, 216, 255, 0.18);
      background: rgba(121, 216, 255, 0.08);
    }}
    .eyebrow::before {{
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: currentColor;
      box-shadow: 0 0 14px currentColor;
    }}
    h1 {{ margin: 10px 0 12px; font-size: clamp(34px, 5vw, 56px); }}
    h2 {{ margin-top: 0; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .hero-side {{
      display: grid;
      gap: 12px;
      align-content: start;
    }}
    .hero-note {{
      padding: 18px;
      border-radius: 20px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.03);
    }}
    .hero-note strong {{
      display: block;
      color: var(--amber);
      margin-bottom: 8px;
      font-size: 12px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 22px;
    }}
    .stat, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
    }}
    .stat span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .stat strong {{ display: block; margin-top: 6px; font-size: 24px; }}
    .layout {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .span-4 {{ grid-column: span 4; }}
    .span-5 {{ grid-column: span 5; }}
    .span-6 {{ grid-column: span 6; }}
    .span-7 {{ grid-column: span 7; }}
    .span-8 {{ grid-column: span 8; }}
    .span-12 {{ grid-column: span 12; }}
    ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    li {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.03);
    }}
    li strong {{ display: block; margin-bottom: 4px; }}
    li span {{ color: var(--muted); display: block; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    a, button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(121, 216, 255, 0.12);
      color: var(--text);
      text-decoration: none;
      font: inherit;
      cursor: pointer;
    }}
    form {{ display: grid; gap: 12px; }}
    label {{ display: grid; gap: 6px; color: var(--muted); font-size: 13px; }}
    textarea, input, select {{
      width: 100%;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(4, 12, 20, 0.92);
      color: var(--text);
      padding: 12px 14px;
      font: inherit;
    }}
    textarea {{ min-height: 110px; }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      border-radius: 16px;
      padding: 14px;
      border: 1px solid var(--line);
      background: rgba(3, 10, 18, 0.9);
      color: #d7e8f4;
      overflow-x: auto;
    }}
    .status-note {{ min-height: 1.3em; color: var(--muted); margin-top: 10px; }}
    @media (max-width: 980px) {{
      .hero {{ grid-template-columns: 1fr; }}
      .span-4, .span-5, .span-6, .span-7, .span-8, .span-12 {{ grid-column: span 12; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="topbar">
      <div>
        <strong>Desktop Huddle Intelligence</strong>
        <span>Agent chamber, party-mode problem solving, mission board pressure, and delegation continuity guided by the live Huddle state.</span>
      </div>
      <div class="actions">
        <a href="/command-center">Back to Command Center</a>
        <button type="button" id="refresh-huddle">Refresh Huddle State</button>
        <button type="button" id="start-party-mode">Start Overnight Research</button>
      </div>
    </section>
    <section class="hero">
      <div>
        <div class="eyebrow">Concept Storyboard</div>
        <h1>Agent Council Chamber</h1>
        <p>A Huddle command surface shaped by the mockup references: live standups, approvals and blockers, overnight research control, dossier readiness, and idea intake, all still backed by the real module payloads.</p>
        <div class="stats">
          <div class="stat"><span>Status</span><strong id="hero-status">Loading...</strong></div>
          <div class="stat"><span>Active Work</span><strong id="hero-active-work">0</strong></div>
          <div class="stat"><span>Approvals</span><strong id="hero-approvals">0</strong></div>
          <div class="stat"><span>Ready Dossiers</span><strong id="hero-dossiers">0</strong></div>
          <div class="stat"><span>Queued Ideas</span><strong id="hero-ideas">0</strong></div>
        </div>
        <p class="status-note" id="huddle-status-note">Loading huddle module state…</p>
      </div>
      <div class="hero-side">
        <div class="hero-note">
          <strong>Party Mode Problem Solve</strong>
          <div id="party-mode-copy">The live overnight research controller will surface here after payload hydration.</div>
        </div>
        <div class="hero-note">
          <strong>Delegate Back To Agents</strong>
          <div id="delegate-copy">Recent huddle continuity and delegation pressure will appear here once actions are recorded.</div>
        </div>
      </div>
    </section>
    <div class="layout">
      <section class="panel span-8">
        <h2>Agent Report-In &amp; Mission Board</h2>
        <ul id="reports-list"></ul>
      </section>
      <section class="panel span-4">
        <h2>Module &amp; Chamber Status</h2>
        <ul id="module-status-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Approvals Needed</h2>
        <ul id="approvals-list"></ul>
        <div style="height: 14px;"></div>
        <ul id="blockers-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Runtime &amp; Problem Solve</h2>
        <ul id="runtime-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Resolution &amp; Delegate Back Out</h2>
        <ul id="dossiers-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Idea Inbox</h2>
        <form id="idea-form">
          <label>Idea
            <textarea id="idea-text" placeholder="Capture something the Huddle should research next."></textarea>
          </label>
          <label>Domain
            <select id="idea-domain">
              <option value="passive-income">Passive Income</option>
              <option value="general">General</option>
              <option value="operations">Operations</option>
              <option value="family">Family</option>
            </select>
          </label>
          <button type="submit">Capture Huddle Idea</button>
        </form>
        <p class="status-note" id="idea-note">Use this to push a real idea into the live inbox.</p>
        <pre id="idea-output">Awaiting idea capture.</pre>
      </section>
      <section class="panel span-12">
        <h2>Recent Huddle Continuity</h2>
        <ul id="recent-activity-list"></ul>
      </section>
      <section class="panel span-12">
        <h2>Payload Preview</h2>
        <pre id="payload-preview"></pre>
      </section>
    </div>
  </main>
  <script>
    const initialPayload = {raw_json};
    const heroStatus = document.getElementById("hero-status");
    const heroActiveWork = document.getElementById("hero-active-work");
    const heroApprovals = document.getElementById("hero-approvals");
    const heroDossiers = document.getElementById("hero-dossiers");
    const heroIdeas = document.getElementById("hero-ideas");
    const statusNote = document.getElementById("huddle-status-note");
    const ideaNote = document.getElementById("idea-note");
    const reportsList = document.getElementById("reports-list");
    const moduleStatusList = document.getElementById("module-status-list");
    const approvalsList = document.getElementById("approvals-list");
    const blockersList = document.getElementById("blockers-list");
    const runtimeList = document.getElementById("runtime-list");
    const dossiersList = document.getElementById("dossiers-list");
    const recentActivityList = document.getElementById("recent-activity-list");
    const ideaOutput = document.getElementById("idea-output");
    const payloadPreview = document.getElementById("payload-preview");

    function esc(value) {{
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function li(title, summary, detail = "") {{
      return `<li><strong>${{esc(title)}}</strong><span>${{esc(summary)}}</span>${{detail ? `<span>${{esc(detail)}}</span>` : ""}}</li>`;
    }}

    function render(payload) {{
      const reports = Array.isArray(payload.reports) ? payload.reports : [];
      const approvals = Array.isArray(payload.approvals) ? payload.approvals : [];
      const blockers = Array.isArray(payload.blockers) ? payload.blockers : [];
      const dossiers = Array.isArray(payload.dossiers) ? payload.dossiers : [];
      const runtime = payload.runtime || {{}};
      const party = payload.party_mode || {{}};
      const inbox = payload.idea_inbox || {{}};
      const queuedIdeas = Number(inbox.queued_count || 0) + Number(inbox.captured_count || 0);

      heroStatus.textContent = payload.status || "Stubbed";
      heroActiveWork.textContent = String(payload.total_active_work || 0);
      heroApprovals.textContent = String(payload.approvals_count || 0);
      heroDossiers.textContent = String(payload.ready_dossier_count || 0);
      heroIdeas.textContent = String(queuedIdeas);
      statusNote.textContent = payload.summary || "No huddle summary captured yet.";
      document.getElementById("party-mode-copy").textContent = party.status ? `Party mode is ${{party.status}}.` : "Party mode is idle.";
      document.getElementById("delegate-copy").textContent = payload.highlights && payload.highlights.length
        ? payload.highlights.slice(0, 2).join(" | ")
        : "No delegation highlights have been surfaced yet.";

      moduleStatusList.innerHTML = [
        li("What Became Real", payload.what_became_real || "No huddle seam note recorded yet."),
        li("What Remains Partial", payload.remains_partial || "No partial work recorded."),
        li("Proof API", "/api/huddle/module", "/api/huddle and /api/party-mode/start"),
        li("Party Mode", party.status || "idle", party.last_log || ""),
      ].join("");

      reportsList.innerHTML = reports.slice(0, 8).map((item) => li(
        item.agent_name || item.agent_id || "Agent",
        item.summary || item.today || "No standup summary.",
        `${{item.domain || "general"}} · ${{item.status || "ok"}} · ${{item.active_work_count || 0}} active`
      )).join("") || '<li><strong>No standups loaded.</strong><span>Huddle payload did not return any agent reports.</span></li>';

      approvalsList.innerHTML = approvals.slice(0, 6).map((item) => li(
        item.title || "Approval",
        item.agent || item.agent_id || "Unknown agent",
        item.proposal || item.domain || ""
      )).join("") || '<li><strong>No approvals waiting.</strong><span>The huddle does not currently have queued approval proposals.</span></li>';

      blockersList.innerHTML = blockers.slice(0, 5).map((item) => li("Blocker", item)).join("")
        || '<li><strong>No blockers recorded.</strong><span>No agent escalations are currently asking for Chris.</span></li>';

      runtimeList.innerHTML = [
        li("Runtime Mode", runtime.active_mode || "unknown", `awake ${{runtime.awake_count || 0}} · blocked ${{runtime.blocked_count || 0}}`),
        li("Party Session", party.status || "idle", party.started_at || party.last_log || "No active session"),
        li("Highlights", (payload.highlights || []).slice(0, 2).join(" | ") || "No cross-agent highlights yet."),
      ].join("");

      dossiersList.innerHTML = dossiers.slice(0, 6).map((item) => li(
        item.title || "Dossier",
        item.executive_summary || item.first_action || "No summary available.",
        `confidence ${{item.confidence_score || 0}} · updated ${{item.updated_at || "unknown"}}`
      )).join("") || '<li><strong>No ready dossiers.</strong><span>Start overnight research or research an idea to generate dossier output.</span></li>';
      recentActivityList.innerHTML = (Array.isArray(payload.recent_activity) ? payload.recent_activity : []).length
        ? payload.recent_activity.map((item) => li(item.title || "Huddle action", item.subtitle || item.actor || "Operator continuity", item.detail || item.route_label || "")).join("")
        : '<li><strong>No huddle continuity recorded yet.</strong><span>Start overnight research or capture an idea to begin the continuity trail.</span></li>';

      payloadPreview.textContent = JSON.stringify(payload, null, 2);
    }}

    async function recordOperatorAction(payload) {{
      await fetch("/api/activity/operator-action", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload),
      }});
    }}

    async function refreshHuddleState() {{
      statusNote.textContent = "Refreshing huddle module state…";
      try {{
        const response = await fetch("/api/huddle/module");
        const payload = await response.json();
        render(payload);
        statusNote.textContent = payload.summary || "Huddle module refreshed.";
      }} catch (error) {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }}
    }}

    async function startPartyMode() {{
      statusNote.textContent = "Starting overnight research…";
      try {{
        const response = await fetch("/api/party-mode/start", {{ method: "POST" }});
        const payload = await response.json();
        await recordOperatorAction({{
          actor: "Chris",
          domain: "huddle",
          action: "Start Overnight Research",
          title: "Party Mode",
          detail: payload.status === "started" ? "Party mode started from Huddle." : "Party mode already running during Huddle action.",
          why_now: "Huddle module launched a real overnight research cycle.",
          result_summary: `Party mode status: ${{payload.status || "unknown"}}`,
          route: "/huddle-center",
          route_label: "Open Huddle",
          related_kind: "party-mode",
          related_label: "Overnight research",
          succeeded: true,
        }});
        statusNote.textContent = payload.status === "started"
          ? "Party mode started."
          : payload.status === "already_running"
            ? "Party mode is already running."
            : JSON.stringify(payload);
        await refreshHuddleState();
      }} catch (error) {{
        statusNote.textContent = `Party mode failed: ${{String(error)}}`;
      }}
    }}

    async function captureIdea(event) {{
      event.preventDefault();
      ideaNote.textContent = "Capturing idea…";
      try {{
        const response = await fetch("/api/ideas", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            text: document.getElementById("idea-text").value,
            domain: document.getElementById("idea-domain").value,
          }}),
        }});
        const payload = await response.json();
        await recordOperatorAction({{
          actor: "Chris",
          domain: "huddle",
          action: "Capture Huddle Idea",
          title: payload.idea ? payload.idea.text || "Idea captured" : "Idea capture",
          detail: payload.idea ? `Captured idea in ${{payload.idea.domain || "general"}} domain.` : "Idea capture returned without a full idea payload.",
          why_now: "Huddle module pushed a new idea into the live research inbox.",
          result_summary: "Huddle continuity updated with a captured idea.",
          route: "/huddle-center",
          route_label: "Open Huddle",
          related_kind: "idea",
          related_label: payload.idea ? payload.idea.text || payload.idea.id || "Idea" : "Idea",
          succeeded: true,
        }});
        ideaOutput.textContent = JSON.stringify(payload, null, 2);
        ideaNote.textContent = payload.idea ? "Idea captured in the live inbox." : "Idea capture returned without an idea payload.";
        document.getElementById("idea-text").value = "";
        await refreshHuddleState();
      }} catch (error) {{
        ideaNote.textContent = `Idea capture failed: ${{String(error)}}`;
      }}
    }}

    document.getElementById("refresh-huddle").addEventListener("click", () => {{
      refreshHuddleState().catch((error) => {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }});
    }});
    document.getElementById("start-party-mode").addEventListener("click", () => {{
      startPartyMode().catch((error) => {{
        statusNote.textContent = `Party mode failed: ${{String(error)}}`;
      }});
    }});
    document.getElementById("idea-form").addEventListener("submit", captureIdea);
    render(initialPayload);
  </script>
</body>
</html>
"""


def render_chronicle_module_page(payload: dict) -> str:
    raw_json = json.dumps(payload, indent=2)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Chronicle</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #060c14;
      --bg-2: #0a121b;
      --panel: rgba(10, 19, 30, 0.92);
      --panel-2: rgba(17, 26, 38, 0.9);
      --line: rgba(219, 178, 105, 0.14);
      --line-strong: rgba(219, 178, 105, 0.24);
      --text: #edf7ff;
      --muted: #9eb8cb;
      --accent: #dbb269;
      --accent-2: #a8d5ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "SF Pro Display", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(219, 178, 105, 0.16), transparent 22%),
        radial-gradient(circle at top right, rgba(168, 213, 255, 0.08), transparent 24%),
        radial-gradient(circle at 50% 100%, rgba(219, 178, 105, 0.06), transparent 28%),
        linear-gradient(180deg, #04080f 0%, var(--bg) 44%, var(--bg-2) 100%);
      color: var(--text);
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background: linear-gradient(135deg, rgba(255,255,255,0.025), transparent 36%);
      opacity: 0.9;
    }}
    .shell {{ position: relative; max-width: 1400px; margin: 0 auto; padding: 24px 24px 60px; }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 18px;
      padding: 14px 18px;
      border: 1px solid var(--line);
      border-radius: 24px;
      background: rgba(7, 13, 21, 0.72);
      backdrop-filter: blur(18px);
      box-shadow: 0 16px 44px rgba(0, 0, 0, 0.22);
    }}
    .topbar strong {{
      display: block;
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
    }}
    .topbar span {{
      display: block;
      color: var(--muted);
      margin-top: 4px;
      line-height: 1.45;
    }}
    .topbar-links {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 10px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(300px, 0.85fr);
      gap: 18px;
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 30px;
      background: linear-gradient(180deg, rgba(11, 20, 31, 0.96), rgba(8, 15, 24, 0.92));
      box-shadow: 0 24px 56px rgba(0, 0, 0, 0.3);
      backdrop-filter: blur(18px);
    }}
    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 9px;
      color: var(--accent);
      letter-spacing: 0.18em;
      text-transform: uppercase;
      font-size: 12px;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid rgba(219, 178, 105, 0.22);
      background: rgba(219, 178, 105, 0.07);
    }}
    .eyebrow::before {{
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: currentColor;
      box-shadow: 0 0 16px currentColor;
    }}
    h1 {{ margin: 14px 0 12px; font-size: clamp(34px, 5vw, 60px); line-height: 0.95; letter-spacing: -0.05em; }}
    h2 {{ margin: 0 0 12px; font-size: 1.2rem; letter-spacing: -0.03em; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .hero-copy p {{ max-width: 68ch; font-size: 1.02rem; }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 22px;
    }}
    .stat, .panel {{
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
    }}
    .stat {{
      background:
        linear-gradient(180deg, rgba(17, 26, 38, 0.92), rgba(10, 19, 30, 0.98)),
        radial-gradient(circle at top right, rgba(219, 178, 105, 0.12), transparent 35%);
    }}
    .stat span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .stat strong {{ display: block; margin-top: 6px; font-size: 24px; }}
    .panel {{
      background: var(--panel);
      box-shadow: 0 18px 36px rgba(0, 0, 0, 0.22);
    }}
    .hero-side {{
      display: grid;
      gap: 14px;
      align-content: start;
    }}
    .hero-note {{
      padding: 18px;
      border-radius: 22px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
    }}
    .hero-note strong,
    .section-label {{
      display: block;
      margin-bottom: 8px;
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
    }}
    .hero-note p {{ margin: 0; color: var(--text); }}
    .hero-note ul {{ margin-top: 10px; }}
    .hero-note li {{
      background: rgba(255,255,255,0.025);
      border-radius: 16px;
    }}
    .glance-strip {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
    }}
    .glance-card {{
      padding: 16px;
      border-radius: 22px;
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(12, 21, 32, 0.9), rgba(8, 15, 24, 0.96));
    }}
    .glance-card strong {{
      display: block;
      margin-bottom: 8px;
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .glance-card span {{
      display: block;
      color: var(--muted);
      line-height: 1.55;
    }}
    .layout {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .span-4 {{ grid-column: span 4; }}
    .span-5 {{ grid-column: span 5; }}
    .span-6 {{ grid-column: span 6; }}
    .span-7 {{ grid-column: span 7; }}
    .span-8 {{ grid-column: span 8; }}
    ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    li {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.03);
    }}
    li strong {{ display: block; margin-bottom: 4px; }}
    li span {{ color: var(--muted); display: block; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    a, button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: linear-gradient(135deg, rgba(219, 178, 105, 0.16), rgba(168, 213, 255, 0.1));
      color: var(--text);
      text-decoration: none;
      font: inherit;
      cursor: pointer;
    }}
    a:hover, button:hover {{ border-color: var(--line-strong); }}
    form {{ display: grid; gap: 12px; }}
    label {{ display: grid; gap: 6px; color: var(--muted); font-size: 13px; }}
    textarea, input, select {{
      width: 100%;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(4, 12, 20, 0.92);
      color: var(--text);
      padding: 12px 14px;
      font: inherit;
    }}
    textarea {{ min-height: 110px; }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      border-radius: 16px;
      padding: 14px;
      border: 1px solid var(--line);
      background: rgba(3, 10, 18, 0.9);
      color: #d7e8f4;
      overflow-x: auto;
    }}
    .status-note {{ min-height: 1.3em; color: var(--muted); margin-top: 10px; }}
    @media (max-width: 980px) {{
      .hero,
      .glance-strip {{
        grid-template-columns: 1fr;
      }}
      .span-4, .span-5, .span-6, .span-7, .span-8 {{ grid-column: span 12; }}
      .topbar {{
        flex-direction: column;
        align-items: flex-start;
      }}
      .topbar-links {{
        justify-content: flex-start;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="topbar">
      <div>
        <strong>JARVIS Chronicle Desktop Experience</strong>
        <span>Live Chronicle memory, devotional, reflection, and family-story continuity shaped by the new desktop storyboard language.</span>
      </div>
      <div class="topbar-links">
        <a href="/api/chronicle/module">Module JSON</a>
        <a href="/api/devotional-pause">Devotional API</a>
        <a href="/command-center">Command Center</a>
      </div>
    </section>
    <section class="hero">
      <div class="hero-copy">
        <div class="eyebrow">Level 3 Core Module</div>
        <h1>JARVIS Chronicle</h1>
        <p>A dedicated Chronicle workspace inside JARVIS with devotional generation, family-devotional prep, reflection capture, recurring theme visibility, morning formation context, and continuity status. This promotes Chronicle out of the shell packet into a real module surface.</p>
        <div class="actions">
          <a href="/command-center">Back to Command Center</a>
          <button type="button" id="refresh-chronicle">Refresh Chronicle State</button>
        </div>
        <div class="stats">
          <div class="stat"><span>Status</span><strong id="hero-status">Loading...</strong></div>
          <div class="stat"><span>Entries</span><strong id="hero-entries">0</strong></div>
          <div class="stat"><span>Themes</span><strong id="hero-themes">0</strong></div>
          <div class="stat"><span>Insights</span><strong id="hero-insights">0</strong></div>
          <div class="stat"><span>Pending Bridge</span><strong id="hero-pending">0</strong></div>
        </div>
        <p class="status-note" id="chronicle-status-note">Loading chronicle module state…</p>
      </div>
      <aside class="hero-side">
        <div class="hero-note">
          <strong>Living story engine</strong>
          <p>The Chronicle shell now follows the real mockup language: memory hub, family legacy, timeline studio, and voice consultation all orbit the actual module state and capture flows.</p>
          <ul>
            <li><strong>Family and faith</strong><span>Devotional and family-story work stay together instead of being scattered across fake surfaces.</span></li>
            <li><strong>Continuity over time</strong><span>Themes, insights, and entries remain wired to payload-backed continuity.</span></li>
          </ul>
        </div>
        <div class="hero-note">
          <div class="section-label">Chronicle tracks</div>
          <ul>
            <li><strong>Memory capture</strong><span>Reflection intake and notes append to the real Chronicle state.</span></li>
            <li><strong>Narrative synthesis</strong><span>Devotional outputs and bridge insights remain visible in one operating room.</span></li>
          </ul>
        </div>
      </aside>
    </section>
    <section class="glance-strip">
      <div class="glance-card">
        <strong>Memory Hub</strong>
        <span>Story, legacy, and living timeline surfaces are framed as an actual product workspace.</span>
      </div>
      <div class="glance-card">
        <strong>Devotional Intake</strong>
        <span>Prayer, scripture, and family-devotional generation stay directly executable from the screen.</span>
      </div>
      <div class="glance-card">
        <strong>Story Threads</strong>
        <span>Themes and timeline entries remain visible as real continuity data, not just storyboard copy.</span>
      </div>
      <div class="glance-card">
        <strong>Voice Chronicle</strong>
        <span>Leaves space for richer voice-guided Chronicle workflows while preserving today&apos;s live state.</span>
      </div>
    </section>
    <div class="layout">
      <section class="panel span-4">
        <h2>Module Status</h2>
        <ul id="module-status-list"></ul>
      </section>
      <section class="panel span-8">
        <h2>Morning Context</h2>
        <ul id="morning-context-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Devotional Pause</h2>
        <form id="chronicle-devotional-form">
          <label>Actor
            <input id="chronicle-actor" value="Chris">
          </label>
          <label>Mode
            <select id="chronicle-mode">
              <option value="scripture">Scripture</option>
              <option value="prayer">Prayer</option>
              <option value="silence">Silence</option>
            </select>
          </label>
          <label>Theme
            <input id="chronicle-theme" placeholder="stewardship under pressure">
          </label>
          <button type="submit">Generate Devotional Pause</button>
        </form>
        <p class="status-note" id="chronicle-devotional-note">Use this to request a live devotional pause.</p>
        <pre id="chronicle-devotional-output">Awaiting devotional request.</pre>
      </section>
      <section class="panel span-6">
        <h2>Family Devotional</h2>
        <form id="family-devotional-form">
          <label>Theme
            <input id="family-devotional-theme" placeholder="leadership without striving">
          </label>
          <label>Context
            <textarea id="family-devotional-context" placeholder="Prepare something suitable for tonight after a long day and troop meeting."></textarea>
          </label>
          <button type="submit">Prepare Family Devotional</button>
        </form>
        <p class="status-note" id="family-devotional-note">Use this to request a live family devotional prep.</p>
        <pre id="family-devotional-output">Awaiting family devotional request.</pre>
      </section>
      <section class="panel span-6">
        <h2>Capture Reflection</h2>
        <form id="chronicle-capture-form">
          <label>Theme
            <input id="chronicle-capture-theme" placeholder="gratitude in the middle of fatigue">
          </label>
          <label>Chronicle Reflection Note
            <textarea id="chronicle-note" placeholder="What happened today, and where did grace meet us?"></textarea>
          </label>
          <button type="submit">Capture Chronicle Note</button>
        </form>
        <p class="status-note" id="chronicle-capture-note">Use this to append a real Chronicle reflection entry.</p>
        <pre id="chronicle-capture-output">Awaiting Chronicle note.</pre>
      </section>
      <section class="panel span-6">
        <h2>Recurring Themes</h2>
        <ul id="themes-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Recent Timeline</h2>
        <ul id="timeline-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Recent Chronicle Continuity</h2>
        <ul id="recent-activity-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Insights</h2>
        <ul id="insights-list"></ul>
      </section>
      <section class="panel span-12">
        <h2>Payload Preview</h2>
        <pre id="payload-preview"></pre>
      </section>
    </div>
  </main>
  <script>
    const initialPayload = {raw_json};
    const heroStatus = document.getElementById("hero-status");
    const heroEntries = document.getElementById("hero-entries");
    const heroThemes = document.getElementById("hero-themes");
    const heroInsights = document.getElementById("hero-insights");
    const heroPending = document.getElementById("hero-pending");
    const statusNote = document.getElementById("chronicle-status-note");
    const moduleStatusList = document.getElementById("module-status-list");
    const morningContextList = document.getElementById("morning-context-list");
    const themesList = document.getElementById("themes-list");
    const timelineList = document.getElementById("timeline-list");
    const recentActivityList = document.getElementById("recent-activity-list");
    const insightsList = document.getElementById("insights-list");
    const payloadPreview = document.getElementById("payload-preview");

    function esc(value) {{
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function li(title, summary, detail = "") {{
      return `<li><strong>${{esc(title)}}</strong><span>${{esc(summary)}}</span>${{detail ? `<span>${{esc(detail)}}</span>` : ""}}</li>`;
    }}

    function render(payload) {{
      const timeline = Array.isArray(payload.timeline) ? payload.timeline : [];
      const themes = ((payload.theme_summary || {{}}).themes || []);
      const insights = Array.isArray(payload.insights) ? payload.insights : [];
      const morning = payload.morning_context || {{}};

      heroStatus.textContent = payload.status || "Stubbed";
      heroEntries.textContent = String(payload.entry_count || 0);
      heroThemes.textContent = String(themes.length);
      heroInsights.textContent = String(insights.length);
      heroPending.textContent = String(payload.pending_entry_count || 0);
      statusNote.textContent = payload.summary || "No chronicle summary captured yet.";

      moduleStatusList.innerHTML = [
        li("What Became Real", payload.what_became_real || "No chronicle seam note recorded yet."),
        li("What Remains Partial", payload.remains_partial || "No partial work recorded."),
        li("Proof API", "/api/chronicle/module", "/api/chronicle/status and /api/devotional-pause"),
        li("Bridge Status", payload.bridge_status || "unknown", payload.bridge_note || ""),
      ].join("");

      morningContextList.innerHTML = [
        li("Focus", morning.focus || morning.current_focus || "No morning focus available."),
        li("Prayer Count", String(morning.prayer_count || 0), String(morning.active_prayer_count || 0) + " active"),
        li("Guidance", (morning.guidance || []).slice(0, 2).join(" | ") || "No guidance lines available."),
      ].join("");

      themesList.innerHTML = themes.slice(0, 6).map((item) => li(
        item.theme || "Theme",
        `${{item.count || 0}} recurring entries`,
        (item.recent_reflections || []).slice(0, 2).join(" | ")
      )).join("") || '<li><strong>No Chronicle themes yet.</strong><span>Theme rollups will appear once entries are available.</span></li>';

      timelineList.innerHTML = timeline.slice(0, 8).map((item) => li(
        item.theme || "Reflection",
        item.reflection || item.note || "No reflection text available.",
        `${{item.actor || "unknown"}} · ${{item.timestamp || "undated"}}`
      )).join("") || '<li><strong>No Chronicle entries yet.</strong><span>Capture a note to seed the timeline.</span></li>';
      recentActivityList.innerHTML = (Array.isArray(payload.recent_activity) ? payload.recent_activity : []).length
        ? payload.recent_activity.map((item) => li(item.title || "Chronicle action", item.subtitle || item.actor || "Operator continuity", item.detail || item.route_label || "")).join("")
        : '<li><strong>No Chronicle continuity recorded yet.</strong><span>Generate a devotional, prepare a family devotional, or capture a note to start the route-level continuity trail.</span></li>';

      insightsList.innerHTML = insights.slice(0, 6).map((item) => li(
        item.title || item.theme || "Insight",
        item.summary || item.description || "No summary available.",
        item.status || item.insight_type || ""
      )).join("") || '<li><strong>No Chronicle insights yet.</strong><span>Bridge-derived formation insights will appear here when available.</span></li>';

      payloadPreview.textContent = JSON.stringify(payload, null, 2);
    }}

    async function refreshChronicleState() {{
      statusNote.textContent = "Refreshing chronicle module state…";
      try {{
        const response = await fetch("/api/chronicle/module");
        const payload = await response.json();
        render(payload);
        statusNote.textContent = payload.summary || "Chronicle module refreshed.";
      }} catch (error) {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }}
    }}

    async function recordOperatorAction(payload) {{
      await fetch("/api/activity/operator-action", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload),
      }});
    }}

    async function submitDevotional(event) {{
      event.preventDefault();
      const note = document.getElementById("chronicle-devotional-note");
      note.textContent = "Generating devotional pause…";
      try {{
        const response = await fetch("/api/devotional-pause", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            actor: document.getElementById("chronicle-actor").value,
            theme: document.getElementById("chronicle-theme").value,
            mode: document.getElementById("chronicle-mode").value,
          }}),
        }});
        const payload = await response.json();
        document.getElementById("chronicle-devotional-output").textContent = payload.output_text || "(No devotional pause returned.)";
        await recordOperatorAction({{
          actor: document.getElementById("chronicle-actor").value || "Chris",
          domain: "chronicle",
          action: "Generate Devotional Pause",
          title: document.getElementById("chronicle-theme").value || "Chronicle devotional",
          detail: payload.output_text ? "Chronicle devotional pause generated from the live module." : "Chronicle devotional request returned without devotional copy.",
          why_now: "Chronicle generated a devotional pause directly from the route-level operator flow.",
          result_summary: payload.output_text ? "Devotional pause generated." : "Devotional request completed without devotional copy.",
          route: "/chronicle-center",
          route_label: "Open Chronicle",
          related_kind: "devotional",
          related_label: document.getElementById("chronicle-theme").value || "Chronicle devotional",
          succeeded: true,
        }});
        note.textContent = "Devotional pause generated.";
        await refreshChronicleState();
      }} catch (error) {{
        note.textContent = `Devotional request failed: ${{String(error)}}`;
      }}
    }}

    async function submitFamilyDevotional(event) {{
      event.preventDefault();
      const note = document.getElementById("family-devotional-note");
      note.textContent = "Preparing family devotional…";
      try {{
        const response = await fetch("/api/family-devotional", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            actor: document.getElementById("chronicle-actor").value,
            theme: document.getElementById("family-devotional-theme").value,
            context: document.getElementById("family-devotional-context").value,
          }}),
        }});
        const payload = await response.json();
        document.getElementById("family-devotional-output").textContent = payload.output_text || "(No family devotional returned.)";
        await recordOperatorAction({{
          actor: document.getElementById("chronicle-actor").value || "Chris",
          domain: "chronicle",
          action: "Prepare Family Devotional",
          title: document.getElementById("family-devotional-theme").value || "Family devotional",
          detail: payload.output_text ? "Family devotional prepared from Chronicle." : "Family devotional request returned without devotional copy.",
          why_now: "Chronicle prepared a family devotional directly from the route-level operator flow.",
          result_summary: payload.output_text ? "Family devotional prepared." : "Family devotional request completed without devotional copy.",
          route: "/chronicle-center",
          route_label: "Open Chronicle",
          related_kind: "family-devotional",
          related_label: document.getElementById("family-devotional-theme").value || "Family devotional",
          succeeded: true,
        }});
        note.textContent = "Family devotional prepared.";
        await refreshChronicleState();
      }} catch (error) {{
        note.textContent = `Family devotional failed: ${{String(error)}}`;
      }}
    }}

    async function submitCapture(event) {{
      event.preventDefault();
      const note = document.getElementById("chronicle-capture-note");
      note.textContent = "Capturing Chronicle note…";
      try {{
        const response = await fetch("/api/chronicle-capture", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            actor: document.getElementById("chronicle-actor").value,
            theme: document.getElementById("chronicle-capture-theme").value,
            note: document.getElementById("chronicle-note").value,
          }}),
        }});
        const payload = await response.json();
        document.getElementById("chronicle-capture-output").textContent = JSON.stringify(payload, null, 2);
        await recordOperatorAction({{
          actor: document.getElementById("chronicle-actor").value || "Chris",
          domain: "chronicle",
          action: "Capture Chronicle Note",
          title: document.getElementById("chronicle-capture-theme").value || "Chronicle reflection",
          detail: "Chronicle reflection captured into the live timeline.",
          why_now: "Chronicle captured a reflection directly from the route-level operator flow.",
          result_summary: "Chronicle note captured.",
          route: "/chronicle-center",
          route_label: "Open Chronicle",
          related_kind: "chronicle-entry",
          related_label: document.getElementById("chronicle-capture-theme").value || "Chronicle reflection",
          succeeded: true,
        }});
        note.textContent = "Chronicle note captured.";
        document.getElementById("chronicle-note").value = "";
        await refreshChronicleState();
      }} catch (error) {{
        note.textContent = `Chronicle capture failed: ${{String(error)}}`;
      }}
    }}

    document.getElementById("refresh-chronicle").addEventListener("click", () => {{
      refreshChronicleState().catch((error) => {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }});
    }});
    document.getElementById("chronicle-devotional-form").addEventListener("submit", submitDevotional);
    document.getElementById("family-devotional-form").addEventListener("submit", submitFamilyDevotional);
    document.getElementById("chronicle-capture-form").addEventListener("submit", submitCapture);
    render(initialPayload);
  </script>
</body>
</html>
"""


def render_settings_module_page(payload: dict) -> str:
    raw_json = json.dumps(payload, indent=2)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Settings</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #071018;
      --bg-2: #091522;
      --panel: rgba(9, 20, 33, 0.92);
      --line: rgba(121, 216, 255, 0.14);
      --text: #edf7ff;
      --muted: #9eb8cb;
      --accent: #79d8ff;
      --success: #a7f3c8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "SF Pro Display", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top, rgba(121, 216, 255, 0.12), transparent 36%),
        linear-gradient(180deg, #040b12 0%, var(--bg) 44%, var(--bg-2) 100%);
      color: var(--text);
    }}
    .shell {{ max-width: 1420px; margin: 0 auto; padding: 36px 24px 60px; }}
    .hero {{
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 28px;
      background: linear-gradient(180deg, rgba(10, 22, 35, 0.96), rgba(7, 16, 27, 0.92));
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.28);
    }}
    .eyebrow {{ color: var(--accent); letter-spacing: 0.18em; text-transform: uppercase; font-size: 12px; }}
    h1 {{ margin: 10px 0 12px; font-size: clamp(34px, 5vw, 56px); }}
    h2 {{ margin-top: 0; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 22px;
    }}
    .stat, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
    }}
    .stat span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .stat strong {{ display: block; margin-top: 6px; font-size: 24px; }}
    .layout {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .span-4 {{ grid-column: span 4; }}
    .span-6 {{ grid-column: span 6; }}
    .span-8 {{ grid-column: span 8; }}
    .span-12 {{ grid-column: span 12; }}
    ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    li {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.03);
    }}
    li strong {{ display: block; margin-bottom: 4px; }}
    li span {{ color: var(--muted); display: block; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    a, button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(121, 216, 255, 0.12);
      color: var(--text);
      text-decoration: none;
      font: inherit;
      cursor: pointer;
    }}
    form {{ display: grid; gap: 12px; }}
    label {{ display: grid; gap: 6px; color: var(--muted); font-size: 13px; }}
    textarea, input, select {{
      width: 100%;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(4, 12, 20, 0.92);
      color: var(--text);
      padding: 12px 14px;
      font: inherit;
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      border-radius: 16px;
      padding: 14px;
      border: 1px solid var(--line);
      background: rgba(3, 10, 18, 0.9);
      color: #d7e8f4;
      overflow-x: auto;
    }}
    .status-note {{ min-height: 1.3em; color: var(--muted); margin-top: 10px; }}
    .ok {{ color: var(--success); }}
    @media (max-width: 980px) {{
      .span-4, .span-6, .span-8, .span-12 {{ grid-column: span 12; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="eyebrow">Level 3 Core Module</div>
      <h1>JARVIS Settings</h1>
      <p>A dedicated settings and permissions workspace inside JARVIS with live voice controls, location posture, account connectivity, and governance signals. This promotes Settings out of the shell packet into a real module route.</p>
      <div class="actions">
        <a href="/command-center">Back to Command Center</a>
        <button type="button" id="refresh-settings">Refresh Settings State</button>
      </div>
      <div class="stats">
        <div class="stat"><span>Status</span><strong id="hero-status">Loading...</strong></div>
        <div class="stat"><span>Accounts</span><strong id="hero-accounts">0</strong></div>
        <div class="stat"><span>Locations</span><strong id="hero-locations">0</strong></div>
        <div class="stat"><span>Insights</span><strong id="hero-insights">0</strong></div>
      </div>
      <p class="status-note" id="settings-status-note">Loading settings module state…</p>
    </section>
    <div class="layout">
      <section class="panel span-4">
        <h2>Module Status</h2>
        <ul id="module-status-list"></ul>
      </section>
      <section class="panel span-8">
        <h2>Accounts & Connectors</h2>
        <ul id="accounts-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Voice Controls</h2>
        <form id="voice-settings-form">
          <label>TTS Provider
            <select id="voice-provider"></select>
          </label>
          <label>ElevenLabs Voice
            <select id="voice-elevenlabs"></select>
          </label>
          <label>Piper Voice Model
            <select id="voice-piper"></select>
          </label>
          <label>Piper Speaker
            <input id="voice-speaker" placeholder="Optional speaker id">
          </label>
          <button type="submit">Save Voice Settings</button>
        </form>
        <p class="status-note" id="voice-note">Save live voice settings through the same runtime-backed store used by the shell.</p>
      </section>
      <section class="panel span-6">
        <h2>Location Controls</h2>
        <form id="location-settings-form">
          <label>Preferred Location
            <select id="location-preferred"></select>
          </label>
          <button type="submit">Save Location Settings</button>
        </form>
        <p class="status-note" id="location-note">Persist the preferred location through the live location store used by the shell.</p>
      </section>
      <section class="panel span-6">
        <h2>Permissions & Governance</h2>
        <ul id="permissions-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Identity & Devices</h2>
        <ul id="identity-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Saved Locations</h2>
        <ul id="locations-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Payload Preview</h2>
        <pre id="payload-preview"></pre>
      </section>
    </div>
  </main>
  <script>
    const initialPayload = {raw_json};
    const heroStatus = document.getElementById("hero-status");
    const heroAccounts = document.getElementById("hero-accounts");
    const heroLocations = document.getElementById("hero-locations");
    const heroInsights = document.getElementById("hero-insights");
    const statusNote = document.getElementById("settings-status-note");
    const moduleStatusList = document.getElementById("module-status-list");
    const accountsList = document.getElementById("accounts-list");
    const permissionsList = document.getElementById("permissions-list");
    const identityList = document.getElementById("identity-list");
    const locationsList = document.getElementById("locations-list");
    const payloadPreview = document.getElementById("payload-preview");

    function esc(value) {{
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function li(title, summary, detail = "") {{
      return `<li><strong>${{esc(title)}}</strong><span>${{esc(summary)}}</span>${{detail ? `<span>${{esc(detail)}}</span>` : ""}}</li>`;
    }}

    function optionMarkup(items, selectedId) {{
      const values = Array.isArray(items) ? items : [];
      return values.map((item) => {{
        const id = item.id ?? "";
        const label = item.label ?? id;
        const detail = item.detail ? ` · ${{item.detail}}` : "";
        const text = `${{label}}${{detail}}`;
        const selected = id === selectedId ? " selected" : "";
        return `<option value="${{esc(id)}}"${{selected}}>${{esc(text)}}</option>`;
      }}).join("");
    }}

    function connectedSummary(account) {{
      const connection = account.connection;
      if (typeof connection === "string") {{
        return connection;
      }}
      if (connection && typeof connection === "object") {{
        return connection.status || connection.state || connection.detail || "configured";
      }}
      return account.status || "unknown";
    }}

    function render(payload) {{
      const voice = payload.voice || {{}};
      const voiceOptions = payload.voice_options || {{}};
      const location = payload.location || {{}};
      const accounts = Array.isArray((payload.accounts || {{}}).accounts) ? payload.accounts.accounts : [];
      const permissions = payload.permissions || {{}};
      const identity = payload.identity || {{}};
      const savedLocations = Array.isArray(location.saved_locations) ? location.saved_locations : [];
      const insights = Array.isArray(permissions.insights) ? permissions.insights : [];
      const activeLocation = location.active_location || {{}};
      const deviceLocation = location.device_location || {{}};

      heroStatus.textContent = payload.status || "Stubbed";
      heroAccounts.textContent = String(accounts.length);
      heroLocations.textContent = String(savedLocations.length);
      heroInsights.textContent = String(insights.length);
      statusNote.textContent = payload.summary || "No settings summary captured yet.";

      document.getElementById("voice-provider").innerHTML = optionMarkup(voiceOptions.providers, voice.tts_provider);
      document.getElementById("voice-elevenlabs").innerHTML = `<option value="">No ElevenLabs voice selected</option>${{optionMarkup(voiceOptions.elevenlabs, voice.elevenlabs_voice)}}`;
      document.getElementById("voice-piper").innerHTML = `<option value="">No Piper model selected</option>${{optionMarkup(voiceOptions.piper, voice.piper_model_path)}}`;
      document.getElementById("voice-speaker").value = voice.piper_speaker || "";

      document.getElementById("location-preferred").innerHTML = savedLocations.map((item) => {{
        const selected = item.id === location.preferred_location_id ? " selected" : "";
        return `<option value="${{esc(item.id)}}"${{selected}}>${{esc(item.label || item.id)}}</option>`;
      }}).join("");
      const stackStatus = voice.stack_status || voiceOptions.stack_status || {{}};
      const clientSecret = (((payload.google || {{}}).client_secret) || {{}});
      moduleStatusList.innerHTML = [
        li("What Became Real", payload.what_became_real || "No settings seam note recorded yet."),
        li("What Remains Partial", payload.remains_partial || "No partial work recorded."),
        li("Proof API", "/api/settings/module", "/api/voice-settings and /api/location-settings"),
        li("Voice Stack", stackStatus.summary || voice.selected_provider_label || "No voice stack summary available."),
        li("Google Client Secret", clientSecret.configured ? "Configured" : "Missing", clientSecret.detail || ""),
      ].join("");

      accountsList.innerHTML = accounts.slice(0, 8).map((account) => li(
        account.label || account.account_id || "Account",
        `${{account.provider || "provider"}} · ${{connectedSummary(account)}}`,
        account.login_hint || account.service_scope || ""
      )).join("") || '<li><strong>No accounts configured.</strong><span>Saved Google or Outlook accounts will appear here.</span></li>';

      const governance = permissions.governance || {{}};
      const privacy = permissions.privacy || {{}};
      const notifications = permissions.notifications || {{}};
      permissionsList.innerHTML = [
        li("Governance", governance.enabled ? "Enabled" : "Paused", governance.review_required ? "Adult review required" : "No extra review flag"),
        li("Privacy", privacy.private_chronicle ? "Chronicle is private by default." : "Chronicle is shareable by default.", privacy.share_health_with_family ? "Health sharing enabled." : "Health sharing disabled."),
        li("Notifications", notifications.approvals ? "Approvals alerts enabled." : "Approvals alerts disabled.", notifications.health_alerts ? "Health alerts enabled." : "Health alerts disabled."),
        ...insights.slice(0, 3).map((item) => li(item.title || item.insight_id || "Insight", item.summary || "No summary.", item.status || "")),
      ].join("");

      const members = Array.isArray(identity.members) ? identity.members : [];
      const devices = Array.isArray(identity.devices) ? identity.devices : [];
      identityList.innerHTML = [
        li("Identity Members", `${{members.length}} member profile(s)`, members.slice(0, 2).map((item) => item.display_name).join(" | ") || "No members loaded."),
        li("Devices", `${{devices.length}} device record(s)`, devices.slice(0, 2).map((item) => item.label || item.device_id).join(" | ") || "No devices loaded."),
        li("Active Location", activeLocation.label || "Unknown", activeLocation.geography || ""),
      ].join("");

      locationsList.innerHTML = savedLocations.slice(0, 8).map((item) => li(
        item.label || "Location",
        item.geography || "No geography recorded.",
        item.source || item.notes || ""
      )).join("") || '<li><strong>No saved locations.</strong><span>Saved locations will appear here when available.</span></li>';

      payloadPreview.textContent = JSON.stringify(payload, null, 2);
    }}

    async function refreshSettingsState() {{
      statusNote.textContent = "Refreshing settings module state…";
      try {{
        const response = await fetch("/api/settings/module");
        const payload = await response.json();
        render(payload);
        statusNote.textContent = payload.summary || "Settings module refreshed.";
      }} catch (error) {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }}
    }}

    async function saveVoiceSettings(event) {{
      event.preventDefault();
      const note = document.getElementById("voice-note");
      note.textContent = "Saving voice settings…";
      try {{
        const response = await fetch("/api/voice-settings", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            tts_provider: document.getElementById("voice-provider").value,
            elevenlabs_voice: document.getElementById("voice-elevenlabs").value,
            piper_model_path: document.getElementById("voice-piper").value,
            piper_speaker: document.getElementById("voice-speaker").value,
          }}),
        }});
        const payload = await response.json();
        note.textContent = payload.message || "Voice settings updated.";
        await refreshSettingsState();
      }} catch (error) {{
        note.textContent = `Voice save failed: ${{String(error)}}`;
      }}
    }}

    async function saveLocationSettings(event) {{
      event.preventDefault();
      const note = document.getElementById("location-note");
      note.textContent = "Saving location settings…";
      try {{
        const response = await fetch("/api/location-settings", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            preferred_location_id: document.getElementById("location-preferred").value,
          }}),
        }});
        const payload = await response.json();
        note.textContent = payload.ok ? "Location settings updated." : "Location settings response received.";
        await refreshSettingsState();
      }} catch (error) {{
        note.textContent = `Location save failed: ${{String(error)}}`;
      }}
    }}

    document.getElementById("refresh-settings").addEventListener("click", () => {{
      refreshSettingsState().catch((error) => {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }});
    }});
    document.getElementById("voice-settings-form").addEventListener("submit", saveVoiceSettings);
    document.getElementById("location-settings-form").addEventListener("submit", saveLocationSettings);
    render(initialPayload);
  </script>
</body>
</html>
"""


def render_navigation_module_page(payload: dict) -> str:
    raw_json = json.dumps(payload, indent=2)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Navigation</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #071018;
      --bg-2: #091522;
      --panel: rgba(9, 20, 33, 0.92);
      --line: rgba(121, 216, 255, 0.14);
      --text: #edf7ff;
      --muted: #9eb8cb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "SF Pro Display", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top, rgba(121, 216, 255, 0.12), transparent 36%),
        linear-gradient(180deg, #040b12 0%, var(--bg) 44%, var(--bg-2) 100%);
      color: var(--text);
    }}
    .shell {{ max-width: 1480px; margin: 0 auto; padding: 24px 24px 60px; }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 18px;
      padding: 14px 18px;
      border: 1px solid var(--line);
      border-radius: 24px;
      background: rgba(7, 13, 21, 0.76);
      backdrop-filter: blur(18px);
      box-shadow: 0 16px 42px rgba(0, 0, 0, 0.22);
    }}
    .topbar strong {{
      display: block;
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
    }}
    .topbar span {{
      display: block;
      color: var(--muted);
      margin-top: 4px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1.18fr) minmax(300px, 0.82fr);
      gap: 18px;
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 30px;
      background: linear-gradient(180deg, rgba(10, 22, 35, 0.96), rgba(7, 16, 27, 0.92));
      box-shadow: 0 24px 56px rgba(0, 0, 0, 0.3);
    }}
    .eyebrow {{
      color: var(--accent);
      letter-spacing: 0.18em;
      text-transform: uppercase;
      font-size: 12px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid rgba(82, 201, 255, 0.18);
      background: rgba(82, 201, 255, 0.08);
    }}
    .eyebrow::before {{
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: currentColor;
      box-shadow: 0 0 14px currentColor;
    }}
    h1 {{ margin: 10px 0 12px; font-size: clamp(34px, 5vw, 56px); }}
    h2 {{ margin-top: 0; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .hero-side {{
      display: grid;
      gap: 12px;
      align-content: start;
    }}
    .hero-note {{
      padding: 18px;
      border-radius: 20px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.03);
    }}
    .hero-note strong {{
      display: block;
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      margin-bottom: 8px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 22px;
    }}
    .stat, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
    }}
    .stat span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .stat strong {{ display: block; margin-top: 6px; font-size: 24px; }}
    .layout {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .span-4 {{ grid-column: span 4; }}
    .span-6 {{ grid-column: span 6; }}
    .span-8 {{ grid-column: span 8; }}
    .span-12 {{ grid-column: span 12; }}
    ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    li {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.03);
    }}
    li strong {{ display: block; margin-bottom: 4px; }}
    li span {{ color: var(--muted); display: block; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    a, button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(121, 216, 255, 0.12);
      color: var(--text);
      text-decoration: none;
      font: inherit;
      cursor: pointer;
    }}
    form {{ display: grid; gap: 12px; }}
    label {{ display: grid; gap: 6px; color: var(--muted); font-size: 13px; }}
    textarea, input, select {{
      width: 100%;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(4, 12, 20, 0.92);
      color: var(--text);
      padding: 12px 14px;
      font: inherit;
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      border-radius: 16px;
      padding: 14px;
      border: 1px solid var(--line);
      background: rgba(3, 10, 18, 0.9);
      color: #d7e8f4;
      overflow-x: auto;
    }}
    .status-note {{ min-height: 1.3em; color: var(--muted); margin-top: 10px; }}
    @media (max-width: 980px) {{
      .hero {{ grid-template-columns: 1fr; }}
      .span-4, .span-6, .span-8, .span-12 {{ grid-column: span 12; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="topbar">
      <div>
        <strong>Navigation Desktop Experience</strong>
        <span>Command-center routing, smart stops, and voice consultation inspired by the desktop and phone JPG storyboards.</span>
      </div>
      <div class="actions">
        <a href="/command-center">Back to Command Center</a>
        <button type="button" id="refresh-navigation">Refresh Navigation State</button>
      </div>
    </section>
    <section class="hero">
      <div>
        <div class="eyebrow">Concept Storyboard</div>
        <h1>Navigation Command Center</h1>
        <p>A route-aware module with persisted state, live route-weather intelligence, smart stops, and voice-ready consultation, using the JPG look and feel while keeping the actual JARVIS navigation payloads and mutation flow underneath.</p>
        <div class="stats">
          <div class="stat"><span>Status</span><strong id="hero-status">Loading...</strong></div>
          <div class="stat"><span>Saved Locations</span><strong id="hero-locations">0</strong></div>
          <div class="stat"><span>Favorites</span><strong id="hero-favorites">0</strong></div>
          <div class="stat"><span>Recent Destinations</span><strong id="hero-recent">0</strong></div>
        </div>
        <p class="status-note" id="navigation-status-note">Loading navigation module state…</p>
      </div>
      <div class="hero-side">
        <div class="hero-note">
          <strong>Live Route Intelligence Workspace</strong>
          <div id="route-intel-copy">Persisted route posture and route-weather insight will appear here after hydration.</div>
        </div>
        <div class="hero-note">
          <strong>Voice Navigation Consultation</strong>
          <div id="voice-copy">Route continuity will feed the voice guidance summary once route previews are recorded.</div>
        </div>
      </div>
    </section>
    <div class="layout">
      <section class="panel span-4">
        <h2>Navigation Command Rail</h2>
        <ul id="module-status-list"></ul>
      </section>
      <section class="panel span-8">
        <h2>Saved Places &amp; Route Context</h2>
        <ul id="locations-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Live Route Intelligence Workspace</h2>
        <form id="navigation-route-form">
          <label>Origin
            <input id="navigation-origin" placeholder="Home">
          </label>
          <label>Destination
            <input id="navigation-destination" placeholder="Destination">
          </label>
          <label>Parks / Historic Radius (miles)
            <input id="navigation-radius" type="number" min="5" max="100" step="1" value="25">
          </label>
          <button type="submit">Preview Route Intelligence</button>
        </form>
        <p class="status-note" id="navigation-route-note">Use this to run a live route preview and persist the route state.</p>
        <pre id="navigation-route-output">Awaiting route preview.</pre>
      </section>
      <section class="panel span-6">
        <h2>Travel Orchestration &amp; Planning</h2>
        <ul id="state-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Smart Stops Along Route Studio</h2>
        <ul id="stops-list"></ul>
      </section>
      <section class="panel span-6">
        <h2>Recent Route Continuity</h2>
        <ul id="recent-activity-list"></ul>
      </section>
      <section class="panel span-12">
        <h2>Payload Preview</h2>
        <pre id="payload-preview"></pre>
      </section>
    </div>
  </main>
  <script>
    const initialPayload = {raw_json};
    const heroStatus = document.getElementById("hero-status");
    const heroLocations = document.getElementById("hero-locations");
    const heroFavorites = document.getElementById("hero-favorites");
    const heroRecent = document.getElementById("hero-recent");
    const statusNote = document.getElementById("navigation-status-note");
    const moduleStatusList = document.getElementById("module-status-list");
    const locationsList = document.getElementById("locations-list");
    const stateList = document.getElementById("state-list");
    const stopsList = document.getElementById("stops-list");
    const recentActivityList = document.getElementById("recent-activity-list");
    const payloadPreview = document.getElementById("payload-preview");

    function esc(value) {{
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function li(title, summary, detail = "") {{
      return `<li><strong>${{esc(title)}}</strong><span>${{esc(summary)}}</span>${{detail ? `<span>${{esc(detail)}}</span>` : ""}}</li>`;
    }}

    function render(payload) {{
      const state = payload.navigation_state || {{}};
      const locations = Array.isArray(payload.saved_locations) ? payload.saved_locations : [];
      const preview = payload.route_preview || {{}};

      heroStatus.textContent = payload.status || "Stubbed";
      heroLocations.textContent = String(locations.length);
      heroFavorites.textContent = String((state.favorite_destinations || []).length);
      heroRecent.textContent = String((state.recent_destinations || []).length);
      statusNote.textContent = payload.summary || "No navigation summary captured yet.";
      document.getElementById("route-intel-copy").textContent = preview.summary || "No live route preview is persisted yet.";
      document.getElementById("voice-copy").textContent = preview.hazard_active
        ? "Weather or hazard pressure is active on the current route."
        : "Voice guidance is clear for the current route posture.";

      document.getElementById("navigation-origin").value = (state.last_route || {{}}).origin || "";
      document.getElementById("navigation-destination").value = (state.last_route || {{}}).destination || "";
      document.getElementById("navigation-radius").value = String(state.parks_historic_radius_miles || 25);

      moduleStatusList.innerHTML = [
        li("What Became Real", payload.what_became_real || "No navigation seam note recorded yet."),
        li("What Remains Partial", payload.remains_partial || "No partial work recorded."),
        li("Proof API", "/api/navigation/module", "/api/navigation/module/route"),
        li("Last Route", `${{(state.last_route || {{}}).origin || "Unknown"}} -> ${{(state.last_route || {{}}).destination || "Unknown"}}`),
      ].join("");

      locationsList.innerHTML = locations.slice(0, 8).map((item) => li(
        item.label || "Location",
        item.address || item.geography || "No address available.",
        item.source || item.notes || ""
      )).join("") || '<li><strong>No saved locations.</strong><span>Saved family locations will appear here when available.</span></li>';

      stateList.innerHTML = [
        li("Origin Mode", state.selected_origin_mode || "home"),
        li("Favorite Destinations", (state.favorite_destinations || []).join(" | ") || "No favorites saved."),
        li("Recent Destinations", (state.recent_destinations || []).join(" | ") || "No recent destinations saved."),
      ].join("");

      stopsList.innerHTML = (preview.sections || []).slice(0, 6).map((section) => li(
        section.label || section.id || "Category",
        `${{(section.items || []).length}} stop suggestion(s)`,
        (section.items || []).slice(0, 2).map((item) => item.name).join(" | ")
      )).join("") || '<li><strong>No stop suggestions yet.</strong><span>Run a route preview to load along-route stops.</span></li>';
      recentActivityList.innerHTML = (Array.isArray(payload.recent_activity) ? payload.recent_activity : []).length
        ? payload.recent_activity.map((item) => li(item.title || "Navigation action", item.subtitle || item.actor || "Operator continuity", item.detail || item.route_label || "")).join("")
        : '<li><strong>No route continuity recorded yet.</strong><span>Preview a route and the live travel history will appear here.</span></li>';

      document.getElementById("navigation-route-output").textContent = JSON.stringify(preview, null, 2);
      payloadPreview.textContent = JSON.stringify(payload, null, 2);
    }}

    async function recordOperatorAction(payload) {{
      await fetch("/api/activity/operator-action", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload),
      }});
    }}

    async function refreshNavigationState() {{
      statusNote.textContent = "Refreshing navigation module state…";
      try {{
        const response = await fetch("/api/navigation/module");
        const payload = await response.json();
        render(payload);
        statusNote.textContent = payload.summary || "Navigation module refreshed.";
      }} catch (error) {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }}
    }}

    async function previewRoute(event) {{
      event.preventDefault();
      const note = document.getElementById("navigation-route-note");
      note.textContent = "Loading route preview…";
      try {{
        const response = await fetch("/api/navigation/module/route", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            origin: document.getElementById("navigation-origin").value,
            destination: document.getElementById("navigation-destination").value,
            parks_historic_radius_miles: document.getElementById("navigation-radius").value,
          }}),
        }});
        const payload = await response.json();
        await recordOperatorAction({{
          actor: "Chris",
          domain: "navigation",
          action: "Preview Route Intelligence",
          title: `${{payload.origin || "Origin"}} -> ${{payload.destination || "Destination"}}`,
          detail: payload.summary || "Route preview refreshed from Navigation Center.",
          why_now: "Navigation module persisted a fresh route preview and stop intelligence snapshot.",
          result_summary: `Smart stop sections: ${{Array.isArray(payload.sections) ? payload.sections.length : 0}}`,
          route: "/navigation-center",
          route_label: "Open Navigation",
          related_kind: "route-preview",
          related_label: payload.destination || "Route",
          succeeded: true,
        }});
        document.getElementById("navigation-route-output").textContent = JSON.stringify(payload, null, 2);
        note.textContent = payload.summary || "Route preview loaded.";
        await refreshNavigationState();
      }} catch (error) {{
        note.textContent = `Route preview failed: ${{String(error)}}`;
      }}
    }}

    document.getElementById("refresh-navigation").addEventListener("click", () => {{
      refreshNavigationState().catch((error) => {{
        statusNote.textContent = `Refresh failed: ${{String(error)}}`;
      }});
    }});
    document.getElementById("navigation-route-form").addEventListener("submit", previewRoute);
    render(initialPayload);
  </script>
</body>
</html>
"""


def render_agent_hierarchy_page(runtime: JarvisRuntime) -> str:
    system_registry = runtime.agent_registry_snapshot().get("agents", [])
    system_status = runtime.background_agent_status()
    life_snapshot = runtime.life_agent_snapshot()
    strategic_count = len(life_snapshot.get("tiers", {}).get("strategic", []))
    execution_count = len(life_snapshot.get("tiers", {}).get("execution", []))
    curator = runtime.memory_curator_snapshot()
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
      --bg: #040913;
      --bg-2: #08111f;
      --panel: rgba(7, 18, 30, 0.88);
      --panel-strong: rgba(8, 20, 34, 0.97);
      --line: rgba(111, 229, 255, 0.16);
      --line-strong: rgba(111, 229, 255, 0.28);
      --ink: #edf7ff;
      --muted: #90b7d4;
      --cyan: #71e2ff;
      --cyan-soft: rgba(113, 226, 255, 0.12);
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
    button, input, textarea, select {{
      font: inherit;
    }}
    .shell {{
      max-width: 1680px;
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
      max-width: 92ch;
      font-size: 14px;
      line-height: 1.5;
    }}
    .top-stats {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }}
    .stat-card, .tier-section, .side-card, .candidate-card, .studio-card, .party-card {{
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
      grid-template-columns: 1.55fr 0.95fr;
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
    .agent-grid.orchestrator {{ grid-template-columns: minmax(320px, 460px); justify-content: center; }}
    .agent-grid.strategic {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    .agent-grid.execution {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .agent-card {{
      min-height: 238px;
      padding: 16px;
      border: 1px solid rgba(111, 229, 255, 0.24);
      background:
        linear-gradient(180deg, rgba(113, 226, 255, 0.06), transparent 22%),
        var(--panel-strong);
      position: relative;
      cursor: pointer;
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
      font-size: 18px;
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
      min-height: 72px;
      color: var(--ink);
      font-size: 13px;
      line-height: 1.45;
    }}
    .agent-connections {{
      margin-top: 12px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .agent-connections span {{
      padding: 4px 8px;
      border: 1px solid rgba(111, 229, 255, 0.14);
      background: rgba(7, 16, 27, 0.8);
      color: var(--cyan);
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
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
    .workspace-mini {{
      display: inline-flex;
      margin-top: 12px;
      padding: 8px 10px;
      border: 1px solid rgba(111, 229, 255, 0.18);
      background: rgba(7, 16, 27, 0.86);
      color: var(--cyan);
      text-decoration: none;
      font-size: 11px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}
    .sidebar {{
      display: grid;
      gap: 18px;
    }}
    .side-card, .studio-card, .party-card {{
      padding: 18px;
    }}
    .side-card h2, .studio-card h2, .party-card h2 {{
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
    .studio-grid {{
      display: grid;
      grid-template-columns: 1.05fr 0.95fr;
      gap: 18px;
      align-items: start;
    }}
    .life-agents-panel {{
      display: grid;
      gap: 14px;
    }}
    .life-agents-toolbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }}
    .life-agents-toolbar .toolbar-note {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    .life-agents-list {{
      display: grid;
      gap: 12px;
    }}
    .life-agent-row {{
      padding: 14px;
      border: 1px solid rgba(111, 229, 255, 0.14);
      background: rgba(8, 20, 34, 0.9);
      display: grid;
      gap: 8px;
      cursor: pointer;
    }}
    .life-agent-row.active {{
      border-color: rgba(113, 226, 255, 0.42);
      box-shadow: inset 0 0 0 1px rgba(113, 226, 255, 0.18);
    }}
    .life-agent-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
    }}
    .life-agent-head strong {{
      color: var(--cyan);
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-size: 14px;
    }}
    .life-agent-head span {{
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}
    .life-agent-role {{
      color: var(--ink);
      font-size: 13px;
      line-height: 1.5;
    }}
    .studio-form {{
      display: grid;
      gap: 12px;
    }}
    .studio-form label {{
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}
    .studio-form input,
    .studio-form textarea,
    .studio-form select,
    .party-card textarea,
    .party-card select {{
      width: 100%;
      border: 1px solid rgba(111, 229, 255, 0.14);
      background: rgba(6, 13, 23, 0.94);
      color: var(--ink);
      padding: 11px 12px;
      resize: vertical;
    }}
    .studio-form textarea, .party-card textarea {{
      min-height: 92px;
    }}
    .form-row {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }}
    .button-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}
    button {{
      border: 1px solid rgba(111, 229, 255, 0.24);
      background: rgba(7, 16, 27, 0.82);
      color: var(--ink);
      padding: 10px 14px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
    }}
    button.primary {{
      color: #031019;
      background: linear-gradient(180deg, rgba(122, 236, 255, 0.98), rgba(85, 210, 255, 0.92));
      border-color: rgba(122, 236, 255, 0.84);
    }}
    button.danger {{
      color: #ffd3d3;
      border-color: rgba(255, 139, 139, 0.26);
    }}
    .connections-picker {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      border: 1px solid rgba(111, 229, 255, 0.12);
      padding: 10px;
      background: rgba(6, 13, 23, 0.72);
      max-height: 220px;
      overflow: auto;
    }}
    .schema-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }}
    .schema-stack {{
      display: grid;
      gap: 10px;
    }}
    .field-note {{
      color: var(--muted);
      font-size: 11px;
      line-height: 1.45;
      letter-spacing: 0;
      text-transform: none;
    }}
    .compact-textarea {{
      min-height: 74px !important;
    }}
    .validation-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 8px;
      border: 1px solid rgba(255, 139, 139, 0.24);
      background: rgba(36, 10, 16, 0.68);
      color: #ffd0d0;
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .connection-option {{
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--ink);
      font-size: 12px;
      text-transform: none;
      letter-spacing: 0;
    }}
    .party-agent-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin-top: 10px;
      margin-bottom: 12px;
    }}
    .party-result {{
      margin-top: 14px;
      display: grid;
      gap: 12px;
    }}
    .party-synthesis {{
      padding: 14px;
      border: 1px solid rgba(113, 226, 255, 0.18);
      background: rgba(8, 20, 34, 0.9);
      color: var(--ink);
      line-height: 1.6;
      white-space: pre-wrap;
    }}
    .party-participants {{
      display: grid;
      gap: 10px;
    }}
    .party-agent-response {{
      padding: 12px;
      border: 1px solid rgba(111, 229, 255, 0.12);
      background: rgba(7, 16, 27, 0.82);
      white-space: pre-wrap;
      line-height: 1.55;
    }}
    .party-agent-response strong {{
      color: var(--cyan);
      display: block;
      margin-bottom: 8px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-size: 12px;
    }}
    .muted {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
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
      .studio-grid {{ grid-template-columns: 1fr; }}
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
      .agent-grid.orchestrator,
      .agent-grid.strategic,
      .agent-grid.execution,
      .form-row,
      .schema-grid,
      .connections-picker,
      .party-agent-grid {{
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
      <div class="hero-sub">Life Agent Foundry · Party Mode Roundtable</div>
      <div class="hero-note">Build something like BMAD for your life: add agents with personalities, instructions, knowledge, and logic; decide how they interconnect; and ask the whole council for a response when you need more than one angle.</div>
    </section>
    <section class="top-stats">
      <div class="stat-card"><div class="stat-label">Life Agents</div><div class="stat-value" id="stat-life-agents">{escape(str(len(life_snapshot.get("agents", []))))}</div></div>
      <div class="stat-card"><div class="stat-label">Strategic Lanes</div><div class="stat-value" id="stat-strategic">{escape(str(strategic_count))}</div></div>
      <div class="stat-card"><div class="stat-label">Execution Lanes</div><div class="stat-value" id="stat-execution">{escape(str(execution_count))}</div></div>
      <div class="stat-card"><div class="stat-label">System Agents</div><div class="stat-value">{escape(str(len(system_registry)))}</div></div>
    </section>
    <section class="layout">
      <div class="hierarchy">
        <section class="tier-section">
          <div class="tier-rule"></div>
          <div class="tier-header">
            <span>Tier 0</span>
            <strong>Master Orchestrator</strong>
          </div>
          <div class="agent-grid orchestrator" id="tier-orchestrator"></div>
        </section>
        <section class="tier-section">
          <div class="tier-rule"></div>
          <div class="tier-header">
            <span>Tier 1</span>
            <strong>Strategic Layer</strong>
          </div>
          <div class="agent-grid strategic" id="tier-strategic"></div>
        </section>
        <section class="tier-section">
          <div class="tier-rule"></div>
          <div class="tier-header">
            <span>Tier 2</span>
            <strong>Execution Layer</strong>
          </div>
          <div class="agent-grid execution" id="tier-execution"></div>
        </section>
        <section class="studio-grid">
          <section class="studio-card">
            <h2>Agent Studio</h2>
            <div class="life-agents-panel">
              <div class="life-agents-toolbar">
                <div class="toolbar-note">Each block is an agent. Click any agent to tune it, or create a new one that belongs in your life stack.</div>
                <button type="button" id="new-agent-button">New Agent</button>
              </div>
              <div class="life-agents-list" id="life-agents-list"></div>
            </div>
          </section>
          <section class="studio-card">
            <h2>Agent Editor</h2>
            <form class="studio-form" id="agent-form">
              <div class="form-row">
                <label>Label
                  <input id="agent-label" required>
                </label>
                <label>Tier
                  <select id="agent-tier">
                    <option value="orchestrator">Orchestrator</option>
                    <option value="strategic">Strategic</option>
                    <option value="execution">Execution</option>
                  </select>
                </label>
              </div>
              <label>Purpose
                <textarea id="agent-purpose" class="compact-textarea"></textarea>
              </label>
              <label>Role
                <textarea id="agent-role"></textarea>
              </label>
              <label>Personality
                <textarea id="agent-personality"></textarea>
              </label>
              <label>Instructions
                <textarea id="agent-instructions"></textarea>
              </label>
              <label>Specific Information
                <textarea id="agent-knowledge"></textarea>
              </label>
              <label>Logic
                <textarea id="agent-logic"></textarea>
              </label>
              <div class="schema-grid">
                <label>Authority
                  <select id="agent-authority"></select>
                </label>
                <label>Party Mode Role
                  <textarea id="agent-party-role" class="compact-textarea"></textarea>
                </label>
                <label>Escalation Rules
                  <textarea id="agent-escalation-rules" class="compact-textarea" placeholder="One rule per line"></textarea>
                </label>
              </div>
              <div class="schema-stack">
                <label>Memory Read Lanes
                  <div class="connections-picker" id="memory-read-picker"></div>
                </label>
                <label>Memory Write Lanes
                  <div class="connections-picker" id="memory-write-picker"></div>
                </label>
                <label>Memory Blocked Lanes
                  <div class="connections-picker" id="memory-blocked-picker"></div>
                </label>
                <div class="field-note">These lane selections become the runtime memory access policy for the agent.</div>
              </div>
              <div class="schema-grid">
                <label>Allowed Tools
                  <textarea id="agent-tools-allowed" class="compact-textarea" placeholder="One tool or connector per line"></textarea>
                </label>
                <label>Blocked Tools
                  <textarea id="agent-tools-blocked" class="compact-textarea" placeholder="One blocked tool per line"></textarea>
                </label>
                <label>Validation
                  <div id="agent-validation" class="field-note">No validation issues.</div>
                </label>
              </div>
              <label>Connections
                <div class="connections-picker" id="connections-picker"></div>
              </label>
              <div class="button-row">
                <button type="submit" class="primary">Save Agent</button>
                <button type="button" id="clone-agent-button">Clone</button>
                <button type="button" class="danger" id="delete-agent-button">Delete</button>
              </div>
              <div class="muted" id="agent-editor-status">Select an agent to tune it.</div>
            </form>
          </section>
        </section>
      </div>
      <aside class="sidebar">
        <section class="side-card">
          <h2>Party Mode</h2>
          <div class="muted">Ask the council a question and let JARVIS synthesize the responses. This is the closest thing to BMAD for your life inside the current shell.</div>
          <div class="party-card" style="padding:0;border:none;box-shadow:none;background:transparent;">
            <div class="form-row" style="margin-top:12px;">
              <label>Actor
                <select id="party-actor">
                  <option>Chris</option>
                  <option>Rebekah</option>
                </select>
              </label>
              <label>Room
                <input id="party-room" value="office">
              </label>
            </div>
            <label style="display:grid;gap:8px;margin-top:12px;color:var(--muted);font-size:11px;letter-spacing:0.14em;text-transform:uppercase;">Question
              <textarea id="party-request" placeholder="What should tonight look like if I want to protect family calm and still make progress on work?"></textarea>
            </label>
            <div class="party-agent-grid" id="party-agent-grid"></div>
            <div class="button-row">
              <button type="button" class="primary" id="run-party-mode">Run Party Mode</button>
            </div>
            <div class="party-result" id="party-result">
              <div class="party-synthesis">No roundtable staged yet.</div>
            </div>
          </div>
        </section>
        <section class="side-card">
          <h2>Wealth And Leverage</h2>
          <div class="muted">A dedicated council lane for financial independence, passive-income ideas, leverage plays, and ROI-aware experiments. Black Panther, Shuri, and Rocket handle this one by default.</div>
          <div class="party-card" style="padding:0;border:none;box-shadow:none;background:transparent;">
            <div class="form-row" style="margin-top:12px;">
              <label>Actor
                <select id="wealth-actor">
                  <option>Chris</option>
                  <option>Rebekah</option>
                </select>
              </label>
              <label>Room
                <input id="wealth-room" value="office">
              </label>
            </div>
            <label style="display:grid;gap:8px;margin-top:12px;color:var(--muted);font-size:11px;letter-spacing:0.14em;text-transform:uppercase;">Focus
              <textarea id="wealth-request" placeholder="Evaluate the best next passive-income path for me right now. Weigh opportunity size, leverage, startup friction, and the next experiment worth running."></textarea>
            </label>
            <div class="button-row">
              <button type="button" class="primary" id="run-wealth-leverage">Run Wealth Workflow</button>
            </div>
            <div class="party-result" id="wealth-result">
              <div class="party-synthesis">No wealth-and-leverage sprint staged yet.</div>
            </div>
          </div>
        </section>
        <section class="side-card">
          <h2>System Mesh</h2>
          <ul>
            <li><strong>{escape(str(system_status.get("awake_count", 0)))}</strong> awake background agents</li>
            <li><strong>{escape(str(system_status.get("blocked_count", 0)))}</strong> blocked background agents</li>
            <li><strong>{escape(str(system_status.get("active_mode", "ambient-associate")).replace("-", " "))}</strong> active household posture</li>
          </ul>
        </section>
        <section class="side-card">
          <h2>Memory Curator Rules</h2>
          <ul>{curation_rules}</ul>
        </section>
        <section class="side-card">
          <h2>Design Rule</h2>
          <p>Keep judgment-heavy agents near the top, execution agents further down, and let the front-door JARVIS voice remain singular. The goal is orchestration, not personality drift.</p>
          <a class="back-link" href="/">Return to JARVIS</a>
        </section>
      </aside>
    </section>
  </div>
  <script>
    const initialLifeAgents = {json.dumps(life_snapshot)};
    const agentSchema = initialLifeAgents.schema || {{
      authority_levels: ["observe", "advise", "stage", "execute"],
      memory_domains: ["core", "family", "executive", "formation", "workshop", "community", "finance", "health", "security", "system"],
    }};
    let lifeState = initialLifeAgents;
    let selectedAgentId = (lifeState.agents[0] || {{}}).agent_id || "";

    function renderAgentCard(agent) {{
      const connections = (agent.connections || []).map((entry) => `<span>${{entry.replace(/-/g, " ")}}</span>`).join("");
      const metrics = [
        agent.authority_level || "advise",
        agent.domain || "core",
        agent.category || "strategist",
      ].map((entry) => `<span>${{entry.replace(/-/g, " ")}}</span>`).join("");
      const validation = (agent.validation_errors || []).length
        ? `<div class="validation-badge">${{agent.validation_errors.length}} validation issue${{agent.validation_errors.length === 1 ? "" : "s"}}</div>`
        : "";
      const workspaceIds = new Set(["ultron", "herald", "veronica", "nick-fury"]);
      const workspaceLink = workspaceIds.has(agent.agent_id)
        ? `<a class="workspace-mini" href="/agents/workspace/${{agent.agent_id}}" onclick="event.stopPropagation()">Open Workspace</a>`
        : "";
      return `
        <article class="agent-card" data-agent-card="${{agent.agent_id}}">
          <div class="agent-card-head">
            <div>
              <div class="agent-name">${{agent.label}}</div>
              <div class="agent-role">${{agent.role || "No role written yet."}}</div>
            </div>
            <span class="agent-badge ${{agent.enabled ? "awake" : "idle"}}">${{agent.enabled ? "Enabled" : "Paused"}}</span>
          </div>
          <ul class="agent-list">
            <li>${{agent.personality || "No personality set yet."}}</li>
            <li>${{agent.instructions || "No instructions set yet."}}</li>
          </ul>
          <div class="agent-metrics">${{metrics}}</div>
          <div class="agent-connections">${{connections || "<span>no links yet</span>"}}</div>
          ${{validation}}
          ${{workspaceLink}}
          <div class="agent-reason">${{agent.logic || "No logic block written yet."}}</div>
        </article>
      `;
    }}

    function renderLifeAgentRow(agent) {{
      const validation = (agent.validation_errors || []).length
        ? `<span class="validation-badge">${{agent.validation_errors.length}} issue${{agent.validation_errors.length === 1 ? "" : "s"}}</span>`
        : "";
      return `
        <article class="life-agent-row ${{agent.agent_id === selectedAgentId ? "active" : ""}}" data-life-agent="${{agent.agent_id}}">
          <div class="life-agent-head">
            <strong>${{agent.label}}</strong>
            <span>${{agent.tier}}</span>
          </div>
          <div class="life-agent-role">${{agent.role || "No role written yet."}}</div>
          ${{validation}}
        </article>
      `;
    }}

    function parseLineList(value) {{
      return String(value || "")
        .split(/\\n|,/)
        .map((entry) => entry.trim())
        .filter(Boolean);
    }}

    function formatLineList(entries) {{
      return (entries || []).join("\\n");
    }}

    function refreshTierColumns() {{
      const tiers = {{
        orchestrator: document.getElementById("tier-orchestrator"),
        strategic: document.getElementById("tier-strategic"),
        execution: document.getElementById("tier-execution"),
      }};
      Object.entries(tiers).forEach(([tier, node]) => {{
        node.innerHTML = lifeState.agents.filter((agent) => agent.tier === tier).map(renderAgentCard).join("");
      }});
      document.querySelectorAll("[data-agent-card]").forEach((card) => {{
        card.addEventListener("click", () => {{
          selectedAgentId = card.dataset.agentCard;
          syncEditor();
          refreshLists();
        }});
      }});
      document.getElementById("stat-life-agents").textContent = lifeState.agents.length;
      document.getElementById("stat-strategic").textContent = lifeState.agents.filter((agent) => agent.tier === "strategic").length;
      document.getElementById("stat-execution").textContent = lifeState.agents.filter((agent) => agent.tier === "execution").length;
    }}

    function refreshLists() {{
      document.getElementById("life-agents-list").innerHTML = lifeState.agents.map(renderLifeAgentRow).join("");
      document.querySelectorAll("[data-life-agent]").forEach((row) => {{
        row.addEventListener("click", () => {{
          selectedAgentId = row.dataset.lifeAgent;
          syncEditor();
          refreshLists();
        }});
      }});
      document.getElementById("party-agent-grid").innerHTML = lifeState.agents.map((agent) => `
        <label class="connection-option">
          <input type="checkbox" value="${{agent.agent_id}}" checked>
          <span>${{agent.label}}</span>
        </label>
      `).join("");
      refreshTierColumns();
    }}

    function selectedAgent() {{
      return lifeState.agents.find((agent) => agent.agent_id === selectedAgentId) || lifeState.agents[0] || null;
    }}

    function syncAuthorityOptions(selectedValue) {{
      const control = document.getElementById("agent-authority");
      control.innerHTML = (agentSchema.authority_levels || []).map((value) => `
        <option value="${{value}}" ${{value === selectedValue ? "selected" : ""}}>${{value}}</option>
      `).join("");
    }}

    function syncConnectionsPicker(agent) {{
      const currentId = agent ? agent.agent_id : "";
      const selectedConnections = new Set(agent ? (agent.connections || []) : []);
      document.getElementById("connections-picker").innerHTML = lifeState.agents
        .filter((entry) => entry.agent_id !== currentId)
        .map((entry) => `
          <label class="connection-option">
            <input type="checkbox" value="${{entry.agent_id}}" ${{selectedConnections.has(entry.agent_id) ? "checked" : ""}}>
            <span>${{entry.label}}</span>
          </label>
        `)
        .join("");
    }}

    function syncMemoryPicker(targetId, selectedEntries) {{
      const selected = new Set(selectedEntries || []);
      document.getElementById(targetId).innerHTML = (agentSchema.memory_domains || [])
        .map((entry) => `
          <label class="connection-option">
            <input type="checkbox" value="${{entry}}" ${{selected.has(entry) ? "checked" : ""}}>
            <span>${{entry}}</span>
          </label>
        `)
        .join("");
    }}

    function selectedMemoryValues(targetId) {{
      return Array.from(document.querySelectorAll(`#${{targetId}} input:checked`)).map((entry) => entry.value);
    }}

    function syncEditor() {{
      const agent = selectedAgent();
      if (!agent) {{
        return;
      }}
      document.getElementById("agent-label").value = agent.label || "";
      document.getElementById("agent-tier").value = agent.tier || "strategic";
      document.getElementById("agent-purpose").value = agent.purpose || "";
      document.getElementById("agent-role").value = agent.role || "";
      document.getElementById("agent-personality").value = agent.personality || "";
      document.getElementById("agent-instructions").value = agent.instructions || "";
      document.getElementById("agent-knowledge").value = agent.knowledge || "";
      document.getElementById("agent-logic").value = agent.logic || "";
      syncAuthorityOptions(agent.authority_level || "advise");
      document.getElementById("agent-party-role").value = agent.party_role || "";
      document.getElementById("agent-escalation-rules").value = formatLineList(agent.escalation_rules || []);
      document.getElementById("agent-tools-allowed").value = formatLineList(agent.tools_allowed || []);
      document.getElementById("agent-tools-blocked").value = formatLineList(agent.tools_blocked || []);
      const validation = agent.validation_errors || [];
      document.getElementById("agent-validation").innerHTML = validation.length
        ? validation.map((entry) => `<div class="validation-badge">${{entry}}</div>`).join("")
        : "No validation issues.";
      document.getElementById("agent-editor-status").textContent = `Editing ${{agent.label}}.`;
      syncMemoryPicker("memory-read-picker", agent.memory_read || []);
      syncMemoryPicker("memory-write-picker", agent.memory_write || []);
      syncMemoryPicker("memory-blocked-picker", agent.memory_blocked || []);
      syncConnectionsPicker(agent);
    }}

    function agentPayload(cloned = false) {{
      const agent = selectedAgent();
      const connections = Array.from(document.querySelectorAll("#connections-picker input:checked")).map((entry) => entry.value);
      return {{
        agent_id: cloned ? "" : (agent?.agent_id || ""),
        label: document.getElementById("agent-label").value.trim(),
        tier: document.getElementById("agent-tier").value,
        purpose: document.getElementById("agent-purpose").value.trim(),
        role: document.getElementById("agent-role").value.trim(),
        personality: document.getElementById("agent-personality").value.trim(),
        instructions: document.getElementById("agent-instructions").value.trim(),
        knowledge: document.getElementById("agent-knowledge").value.trim(),
        logic: document.getElementById("agent-logic").value.trim(),
        authority_level: document.getElementById("agent-authority").value,
        party_role: document.getElementById("agent-party-role").value.trim(),
        escalation_rules: parseLineList(document.getElementById("agent-escalation-rules").value),
        memory_read: selectedMemoryValues("memory-read-picker"),
        memory_write: selectedMemoryValues("memory-write-picker"),
        memory_blocked: selectedMemoryValues("memory-blocked-picker"),
        tools_allowed: parseLineList(document.getElementById("agent-tools-allowed").value),
        tools_blocked: parseLineList(document.getElementById("agent-tools-blocked").value),
        connections,
        enabled: true,
      }};
    }}

    async function postJson(url, payload) {{
      const response = await fetch(url, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload),
      }});
      if (!response.ok) {{
        throw new Error(await response.text());
      }}
      return response.json();
    }}

    async function saveAgent(cloned = false) {{
      const result = await postJson("/api/life-agents", agentPayload(cloned));
      lifeState = result.snapshot;
      selectedAgentId = result.agent.agent_id;
      refreshLists();
      syncEditor();
      document.getElementById("agent-editor-status").textContent = `Saved ${{result.agent.label}}.`;
    }}

    async function deleteAgent() {{
      const agent = selectedAgent();
      if (!agent) {{
        return;
      }}
      const result = await postJson("/api/life-agents/delete", {{ agent_id: agent.agent_id }});
      lifeState = result.snapshot;
      selectedAgentId = (lifeState.agents[0] || {{}}).agent_id || "";
      refreshLists();
      syncEditor();
      document.getElementById("agent-editor-status").textContent = `Removed ${{agent.label}}.`;
    }}

    function stageNewAgent() {{
      selectedAgentId = "";
      document.getElementById("agent-form").reset();
      document.getElementById("agent-tier").value = "strategic";
      syncAuthorityOptions("advise");
      syncMemoryPicker("memory-read-picker", []);
      syncMemoryPicker("memory-write-picker", []);
      syncMemoryPicker("memory-blocked-picker", []);
      document.getElementById("agent-validation").textContent = "No validation issues.";
      syncConnectionsPicker(null);
      document.getElementById("agent-editor-status").textContent = "Staging a new agent.";
      document.querySelectorAll(".life-agent-row").forEach((row) => row.classList.remove("active"));
    }}

    async function runPartyMode() {{
      const request = document.getElementById("party-request").value.trim();
      const selectedAgents = Array.from(document.querySelectorAll("#party-agent-grid input:checked")).map((entry) => entry.value);
      const result = await postJson("/api/life-party", {{
        actor: document.getElementById("party-actor").value,
        room: document.getElementById("party-room").value.trim() || "office",
        request,
        agents: selectedAgents,
      }});
      const participants = (result.participants || []).map((entry) => `
        <article class="party-agent-response">
          <strong>${{entry.label}}</strong>
          ${{entry.response}}
        </article>
      `).join("");
      document.getElementById("party-result").innerHTML = `
        <div class="party-synthesis">${{result.synthesis || "No synthesis returned."}}</div>
        <div class="party-participants">${{participants}}</div>
      `;
    }}

    async function runWealthLeverage() {{
      const result = await postJson("/api/wealth-leverage", {{
        actor: document.getElementById("wealth-actor").value,
        room: document.getElementById("wealth-room").value.trim() || "office",
        request: document.getElementById("wealth-request").value.trim(),
      }});
      const participants = (result.participants || []).map((entry) => `
        <article class="party-agent-response">
          <strong>${{entry.label}}</strong>
          ${{entry.response}}
        </article>
      `).join("");
      const focus = (result.focus_areas || []).map((entry) => `<span>${{entry}}</span>`).join("");
      document.getElementById("wealth-result").innerHTML = `
        <div class="party-synthesis">${{result.synthesis || "No synthesis returned."}}</div>
        <div class="agent-connections" style="margin-top:12px;">${{focus}}</div>
        <div class="party-participants">${{participants}}</div>
      `;
    }}

    document.getElementById("agent-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      saveAgent(false).catch((error) => {{
        document.getElementById("agent-editor-status").textContent = error.message;
      }});
    }});
    document.getElementById("clone-agent-button").addEventListener("click", () => {{
      saveAgent(true).catch((error) => {{
        document.getElementById("agent-editor-status").textContent = error.message;
      }});
    }});
    document.getElementById("delete-agent-button").addEventListener("click", () => {{
      deleteAgent().catch((error) => {{
        document.getElementById("agent-editor-status").textContent = error.message;
      }});
    }});
    document.getElementById("new-agent-button").addEventListener("click", stageNewAgent);
    document.getElementById("run-party-mode").addEventListener("click", () => {{
      runPartyMode().catch((error) => {{
        document.getElementById("party-result").innerHTML = `<div class="party-synthesis">${{error.message}}</div>`;
      }});
    }});
    document.getElementById("run-wealth-leverage").addEventListener("click", () => {{
      runWealthLeverage().catch((error) => {{
        document.getElementById("wealth-result").innerHTML = `<div class="party-synthesis">${{error.message}}</div>`;
      }});
    }});

    refreshLists();
    syncEditor();
  </script>
</body>
</html>"""


def render_agent_workspace_page(runtime: JarvisRuntime, agent_id: str) -> str:
    snapshot = runtime.life_agent_snapshot()
    agent = next((entry for entry in snapshot.get("agents", []) if entry.get("agent_id") == agent_id), None)
    if not agent:
        return _render_catalyst_workspace_chrome(
            "Agent Workspace",
            "Requested agent was not found in the active JARVIS mesh.",
            '<div class="card"><p class="muted">That workspace does not exist yet.</p><a class="nav-pill active" href="/agents/hierarchy">Return to Agent Hierarchy</a></div>',
            "home",
        )

    title = str(agent.get("label", "Agent Workspace"))
    subtitle = str(agent.get("role", agent.get("purpose", "Dedicated operator workspace.")))

    if agent_id == "herald":
        data = runtime.herald_workspace_snapshot()
        likely = data.get("likely_meetings", [])
        merged = data.get("merged_calendar", [])
        participant_suggestions = data.get("participant_suggestions", [])
        context_options = data.get("context_options", [])
        latest_prep = data.get("latest_meeting_prep", {})
        latest_extract = data.get("latest_meeting_extraction", {})
        latest_briefing = data.get("latest_briefing", {})
        options = "".join(
            f'<option value="{escape(str(item.get("id", "")))}">{escape(str(item.get("summary", "(Untitled event)")))} · {escape(str(item.get("start", "No start time")))}</option>'
            for item in (likely or merged[:8])
        )
        participant_options = "".join(
            f'<label class="chip"><input type="checkbox" value="{escape(str(item))}"><span>{escape(str(item))}</span></label>'
            for item in participant_suggestions
        )
        context_pills = "".join(
            f'<label class="chip"><input type="checkbox" value="{escape(str(item))}"><span>{escape(str(item))}</span></label>'
            for item in context_options
        )
        body = f"""
        <div class="grid">
          <article class="card">
            <h2>Meeting Radar</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(str(item.get("summary", "(Untitled event)")))}</strong><div class="muted">{escape(str(item.get("start", "No start time")))} · {escape(str(item.get("source_label", item.get("source", "calendar"))))}</div></div>' for item in (likely or merged[:8])) or '<div class="muted">No likely meetings detected yet.</div>'}</div>
          </article>
          <article class="card">
            <h2>Stage Packet</h2>
            <label class="field">
              <span class="field-label">Select Meeting</span>
              <select id="herald-event">{options or '<option value="">Use best guess</option>'}</select>
            </label>
            <label class="field" style="margin-top:12px;">
              <span class="field-label">Objective</span>
              <input id="herald-objective" value="Clarify objective, decisions needed, and follow-up posture.">
            </label>
            <div class="grid" style="grid-template-columns:1fr 1fr;margin-top:12px;">
              <div>
                <div class="field-label" style="margin-bottom:8px;">Participants</div>
                <div id="herald-participants" class="chips">{participant_options}</div>
              </div>
              <div>
                <div class="field-label" style="margin-bottom:8px;">Context Lanes</div>
                <div id="herald-contexts" class="chips">{context_pills}</div>
              </div>
            </div>
            <label class="field" style="margin-top:12px;">
              <span class="field-label">Context</span>
              <textarea id="herald-context" style="min-height:100px;">Prepare a disciplined brief, flag unclear objectives, and give me the clean agenda.</textarea>
            </label>
            <div class="cluster" style="margin-top:12px;">
              <button class="btn btn-primary" id="run-herald-packet" type="button">Stage Meeting Packet</button>
              <a class="btn btn-secondary" href="/catalyst/view/meetings">Open Catalyst Meetings</a>
            </div>
          </article>
          <article class="card">
            <h2>Latest Packet</h2>
            <div id="herald-result">
              <p><strong>{escape(str(latest_prep.get("meeting_title", "No packet staged yet.")))}</strong></p>
              <p class="muted">{escape(", ".join(latest_prep.get("participants", [])) or "No participants selected yet.")}</p>
              <ul>{''.join(f'<li>{escape(str(item))}</li>' for item in latest_prep.get("suggested_agenda", [])) or '<li class="muted">No agenda lines yet.</li>'}</ul>
            </div>
          </article>
          <article class="card">
            <h2>Extraction Memory</h2>
            <p>{escape(str(latest_extract.get("problem_statement", latest_briefing.get("recommendation", "No meeting extraction or briefing has been stored yet."))))}</p>
          </article>
        </div>
        <script>
          document.getElementById("run-herald-packet").addEventListener("click", async () => {{
            const participants = Array.from(document.querySelectorAll("#herald-participants input:checked")).map((entry) => entry.value);
            const contexts = Array.from(document.querySelectorAll("#herald-contexts input:checked")).map((entry) => entry.value);
            const result = await window.JarvisUI.postJson("/api/herald/prepare", {{
              actor: "Chris",
              event_id: document.getElementById("herald-event").value,
              objective: document.getElementById("herald-objective").value,
              participants,
              contexts,
              context: document.getElementById("herald-context").value,
            }});
            document.getElementById("herald-result").innerHTML = `
              <p><strong>${{result.meeting_title || "Upcoming meeting"}}</strong></p>
              <p class="muted">${{(result.participants || []).join(", ") || "No participants selected yet."}}</p>
              <ul>${{(result.suggested_agenda || []).map((item) => `<li>${{item}}</li>`).join("") || "<li>No agenda lines returned.</li>"}}</ul>
              <p class="muted">${{(result.watch_points || []).join(" ")}}</p>
            `;
          }});
        </script>
        """
        return _render_catalyst_workspace_chrome(title, subtitle, body, "meetings")

    if agent_id == "veronica":
        data = runtime.veronica_workspace_snapshot()
        latest_ideas = data.get("idea_runs", [])
        queue = data.get("queue", [])
        stats = data.get("stats", {})
        latest_run = latest_ideas[0] if latest_ideas else {}
        options_html = "".join(
            f"""
            <div class="row">
              <strong>{escape(str(option.get("title", "Untitled option")))}</strong>
              <div class="muted">{escape(str(option.get("hook", "")))}</div>
              <div class="muted">{escape(str(option.get("angle", "")))}</div>
              <div class="inline-actions">
                <button class="btn btn-primary approve-option" data-option-id="{escape(str(option.get("option_id", "")))}" type="button">Approve To Script</button>
              </div>
            </div>
            """
            for option in latest_run.get("options", [])
        )
        queue_rows: list[str] = []
        for item in queue[:8]:
            action_html = (
                (
                    f'<button class="btn btn-secondary export-package" data-queue-id="{escape(str(item.get("queue_id", "")))}" type="button">Export Package</button> '
                    f'<button class="btn btn-primary push-live" data-queue-id="{escape(str(item.get("queue_id", "")))}" type="button">Push Live</button>'
                )
                if str(item.get("status", "")).lower() not in {"live"}
                else f'<button class="btn btn-secondary export-package" data-queue-id="{escape(str(item.get("queue_id", "")))}" type="button">Export Package</button> <span class="status-pill live">Live</span>'
            )
            queue_rows.append(
                f'<div class="row"><strong>{escape(str(item.get("title", "Untitled script")))}</strong>'
                f'<div class="status-pill {"live" if str(item.get("status", "")).lower() == "live" else "exported" if str(item.get("status", "")).lower() == "exported" else ""}">{escape(str(item.get("status", "queued")).upper())} · {escape(str(item.get("channel", "YouTube")))}</div>'
                f'<div class="muted">{escape(str(item.get("hook", "")))}</div>'
                f'<div class="inline-actions">{action_html}</div></div>'
            )
        queue_html = "".join(queue_rows)
        body = f"""
        <div class="grid">
          <article class="card">
            <h2>Generate Topics</h2>
            <label class="field">
              <span class="field-label">Topic</span>
              <input id="veronica-topic" value="Markets, geopolitics, trade">
            </label>
            <label class="field" style="margin-top:12px;">
              <span class="field-label">Context</span>
              <textarea id="veronica-context" style="min-height:100px;">Compile today's intelligence report and give me four strong YouTube-ready angles with different hooks.</textarea>
            </label>
            <div class="cluster" style="margin-top:12px;">
              <button class="btn btn-primary" id="run-veronica-ideas" type="button">Generate Options</button>
            </div>
          </article>
          <article class="card">
            <h2>Approval Board</h2>
            <div id="veronica-options" class="table">{options_html or '<div class="muted">No idea run has been staged yet.</div>'}</div>
          </article>
          <article class="card">
            <h2>Queue</h2>
            <div class="muted">Queued: {escape(str(stats.get("queued", 0)))} · Live: {escape(str(stats.get("live", 0)))} · Idea Runs: {escape(str(stats.get("idea_runs", 0)))}</div>
            <div id="veronica-queue" class="table" style="margin-top:12px;">{queue_html or '<div class="muted">No scripts are queued yet.</div>'}</div>
          </article>
          <article class="card">
            <h2>Latest Script</h2>
            <div id="veronica-script">
              <p>{escape(str((queue[0] if queue else {}).get("script", "Approve an option to generate a script package.")))}</p>
            </div>
            <div id="veronica-export" class="muted" style="margin-top:12px;">Export a queued script into a usable package for production and upload handoff.</div>
          </article>
        </div>
        <script>
          async function refreshVeronica() {{
            const response = await fetch("/api/agent-workspace/veronica");
            const data = await response.json();
            const latestRun = (data.idea_runs || [])[0] || {{}};
            document.getElementById("veronica-options").innerHTML = (latestRun.options || []).map((option) => `
              <div class="row">
                <strong>${{option.title || "Untitled option"}}</strong>
                <div class="muted">${{option.hook || ""}}</div>
                <div class="muted">${{option.angle || ""}}</div>
                <div class="inline-actions">
                  <button class="btn btn-primary approve-option" data-option-id="${{option.option_id}}" type="button">Approve To Script</button>
                </div>
              </div>
            `).join("") || '<div class="muted">No idea run has been staged yet.</div>';
            document.getElementById("veronica-queue").innerHTML = (data.queue || []).map((item) => `
                <div class="row">
                  <strong>${{item.title || "Untitled script"}}</strong>
                  <div class="status-pill ${{String(item.status || "").toLowerCase() === "live" ? "live" : String(item.status || "").toLowerCase() === "exported" ? "exported" : ""}}">${{String(item.status || "queued").toUpperCase()}} · ${{item.channel || "YouTube"}}</div>
                  <div class="muted">${{item.hook || ""}}</div>
                  <div class="inline-actions">${{`<button class="btn btn-secondary export-package" data-queue-id="${{item.queue_id}}" type="button">Export Package</button>`}} ${{String(item.status || "").toLowerCase() === "live" ? '<span class="status-pill live">Live</span>' : `<button class="btn btn-primary push-live" data-queue-id="${{item.queue_id}}" type="button">Push Live</button>`}}</div>
                </div>
            `).join("") || '<div class="muted">No scripts are queued yet.</div>';
            document.getElementById("veronica-script").innerHTML = `<p>${{((data.queue || [])[0] || {{}}).script || "Approve an option to generate a script package."}}</p>`;
            const latest = ((data.queue || [])[0] || {{}});
            const manifest = latest.export_manifest || null;
            document.getElementById("veronica-export").innerHTML = manifest
              ? `<strong>Latest export:</strong> ${{manifest.files.map((entry) => entry.label).join(" · ")}}`
              : "Export a queued script into a usable package for production and upload handoff.";
            bindVeronicaActions();
          }}
          function bindVeronicaActions() {{
            document.querySelectorAll(".approve-option").forEach((button) => {{
              button.onclick = async () => {{
                window.JarvisUI.openApprovalDialog({{
                  title: "Approve To Script",
                  copy: "Promote this Veronica option into a production script draft and add it to the queue.",
                  meta: "This keeps a human checkpoint before a topic becomes a real content asset.",
                  confirmLabel: "Approve To Script",
                  confirmClass: "btn-primary",
                  onConfirm: async () => {{
                    await window.JarvisUI.postJson("/api/veronica/approve", {{ actor: "Chris", option_id: button.dataset.optionId }});
                    await refreshVeronica();
                  }},
                }});
              }};
            }});
            document.querySelectorAll(".push-live").forEach((button) => {{
              button.onclick = async () => {{
                window.JarvisUI.openApprovalDialog({{
                  title: "Push Live",
                  copy: "Mark this Veronica package as live and move it into the published lane.",
                  meta: "Use this after the content package is reviewed and ready for the public-facing channel flow.",
                  confirmLabel: "Push Live",
                  confirmClass: "btn-primary",
                  onConfirm: async () => {{
                    await window.JarvisUI.postJson("/api/veronica/push-live", {{ queue_id: button.dataset.queueId }});
                    await refreshVeronica();
                  }},
                }});
              }};
            }});
            document.querySelectorAll(".export-package").forEach((button) => {{
              button.onclick = async () => {{
                window.JarvisUI.openApprovalDialog({{
                  title: "Export Package",
                  copy: "Create a production-ready Veronica export package for handoff, review, or upload preparation.",
                  meta: "The export includes metadata, script, visual notes, and publish notes.",
                  confirmLabel: "Export",
                  confirmClass: "btn-secondary",
                  onConfirm: async () => {{
                    const result = await window.JarvisUI.postJson("/api/veronica/export", {{ queue_id: button.dataset.queueId }});
                    const manifest = (((result || {{}}).record || {{}}).export_manifest || null);
                    document.getElementById("veronica-export").innerHTML = manifest
                      ? `<strong>Exported:</strong> ${{window.JarvisUI.escapeHtml(manifest.root)}}`
                      : "Export completed.";
                    await refreshVeronica();
                  }},
                }});
              }};
            }});
          }}
          document.getElementById("run-veronica-ideas").addEventListener("click", async () => {{
            await window.JarvisUI.postJson("/api/veronica/options", {{
              actor: "Chris",
              topic: document.getElementById("veronica-topic").value,
              context: document.getElementById("veronica-context").value,
              channel: "YouTube",
            }});
            await refreshVeronica();
          }});
          bindVeronicaActions();
        </script>
        """
        return _render_catalyst_workspace_chrome(title, subtitle, body, "reports")

    if agent_id == "ultron":
        data = runtime.ultron_workspace_snapshot()
        incidents = data.get("security_incidents", [])
        anomalies = data.get("anomalies", [])
        privacy = data.get("privacy_state", {})
        statuses = data.get("status", [])
        body = f"""
        <div class="grid">
          <article class="card">
            <h2>Threat Scanner</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(str(item.get("category", "incident")).replace("-", " ").title())}</strong><div class="muted">{escape(str(item.get("detail", "")))}</div><div class="muted">{escape(str(item.get("timestamp", "")))}</div></div>' for item in incidents[:8]) or '<div class="muted">No security incidents logged yet.</div>'}</div>
          </article>
          <article class="card">
            <h2>Privacy Posture</h2>
            <pre class="muted" style="white-space:pre-wrap;">{escape(json.dumps(privacy, indent=2))}</pre>
          </article>
          <article class="card">
            <h2>System Alerts</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(str(item.get("name", "status")))}</strong><div class="muted">{escape(str(item.get("detail", "")))}</div></div>' for item in statuses if not item.get("ok", True)) or '<div class="muted">No degraded integrations right now.</div>'}</div>
          </article>
          <article class="card">
            <h2>Anomalies</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(str(item.get("category", "watch")).replace("-", " ").title())}</strong><div class="muted">{escape(str(item.get("detail", item.get("summary", ""))))}</div></div>' for item in anomalies[:8]) or '<div class="muted">No anomaly watch items are active.</div>'}</div>
          </article>
        </div>
        """
        return _render_catalyst_workspace_chrome(title, subtitle, body, "settings")

    if agent_id == "nick-fury":
        data = runtime.nick_fury_workspace_snapshot()
        calendar = data.get("calendar", [])
        approvals = data.get("approvals", [])
        wealth = data.get("wealth_summary", {})
        approval_rows = "".join(
            f"""
            <div class="approval-block">
              <strong>{escape(str(item.get("action_class", "approval")).replace("-", " ").title())}</strong>
              <div class="muted">{escape(str(item.get("request", "")))}</div>
              <div class="inline-actions">
                <button class="btn btn-primary review-approval" data-request-id="{escape(str(item.get("request_id", "")))}" data-status="approved" data-request-copy="{escape(str(item.get("request", "")))}" type="button">Approve</button>
                <button class="btn btn-danger review-approval" data-request-id="{escape(str(item.get("request_id", "")))}" data-status="rejected" data-request-copy="{escape(str(item.get("request", "")))}" type="button">Reject</button>
              </div>
            </div>
            """
            for item in approvals[:5]
        )
        body = f"""
        <div class="grid">
          <article class="card">
            <h2>Daily Strategic Brief</h2>
            <div id="nick-brief" style="white-space:pre-wrap;">{escape(str(data.get("brief", "No strategic brief generated yet.")))}</div>
            <div class="cluster" style="margin-top:12px;">
              <button class="btn btn-primary" id="refresh-nick-brief" type="button">Refresh Brief</button>
            </div>
          </article>
          <article class="card">
            <h2>Systems Note</h2>
            <div id="nick-systems" style="white-space:pre-wrap;">{escape(str(data.get("systems_note", "No systems note generated yet.")))}</div>
          </article>
          <article class="card">
            <h2>Command Context</h2>
            <div class="table">{''.join(f'<div class="row"><strong>{escape(str(item.get("summary", "(Untitled event)")))}</strong><div class="muted">{escape(str(item.get("start", "No start time")))}</div></div>' for item in calendar[:6]) or '<div class="muted">No near-term calendar pressure.</div>'}</div>
          </article>
          <article class="card">
            <h2>Approvals And Wealth Lane</h2>
            <div class="muted" style="margin-bottom:12px;">Pending approvals: {escape(str(len(approvals)))}</div>
            <div id="nick-approvals" class="stack-sm">{approval_rows or '<div class="muted">No approvals pending.</div>'}</div>
            <div class="muted" style="margin-top:14px;">Opportunity theses tracked: {escape(str(len(wealth.get("opportunity_theses", []))))}</div>
          </article>
        </div>
        <script>
          function bindNickApprovals() {{
            document.querySelectorAll(".review-approval").forEach((button) => {{
              button.onclick = async () => {{
                const decision = button.dataset.status;
                const isApproval = decision === "approved";
                window.JarvisUI.openApprovalDialog({{
                  title: isApproval ? "Approve Action" : "Reject Action",
                  copy: button.dataset.requestCopy || "Review the pending action.",
                  meta: isApproval ? "This will mark the request approved in Nick Fury's command lane." : "This will reject the request and keep it from advancing.",
                  confirmLabel: isApproval ? "Approve" : "Reject",
                  confirmClass: isApproval ? "btn-primary" : "btn-danger",
                  onConfirm: async () => {{
                    await window.JarvisUI.postJson(`/api/approvals/${{button.dataset.requestId}}`, {{ status: decision }});
                    const response = await fetch("/api/agent-workspace/nick-fury");
                    const data = await response.json();
                    renderNickApprovals(data.approvals || []);
                  }},
                }});
              }};
            }});
          }}
          function renderNickApprovals(items) {{
            const target = document.getElementById("nick-approvals");
            target.innerHTML = (items || []).map((item) => `
              <div class="approval-block">
                <strong>${{window.JarvisUI.escapeHtml(String(item.action_class || "approval").replaceAll("-", " "))}}</strong>
                <div class="muted">${{window.JarvisUI.escapeHtml(item.request || "")}}</div>
                <div class="inline-actions">
                  <button class="btn btn-primary review-approval" data-request-id="${{item.request_id}}" data-status="approved" data-request-copy="${{window.JarvisUI.escapeHtml(item.request || "")}}" type="button">Approve</button>
                  <button class="btn btn-danger review-approval" data-request-id="${{item.request_id}}" data-status="rejected" data-request-copy="${{window.JarvisUI.escapeHtml(item.request || "")}}" type="button">Reject</button>
                </div>
              </div>
            `).join("") || '<div class="muted">No approvals pending.</div>';
            bindNickApprovals();
          }}
          document.getElementById("refresh-nick-brief").addEventListener("click", async () => {{
            const response = await fetch("/api/agent-workspace/nick-fury");
            const data = await response.json();
            document.getElementById("nick-brief").textContent = data.brief || "No strategic brief generated yet.";
            document.getElementById("nick-systems").textContent = data.systems_note || "No systems note generated yet.";
            renderNickApprovals(data.approvals || []);
          }});
          bindNickApprovals();
        </script>
        """
        return _render_catalyst_workspace_chrome(title, subtitle, body, "home")

    body = f"""
    <div class="card">
      <h2>{escape(title)}</h2>
      <p>{escape(str(agent.get("purpose", "This agent does not have a dedicated operator room yet.")))}</p>
      <a class="nav-pill active" href="/agents/hierarchy">Return to Agent Hierarchy</a>
    </div>
    """
    return _render_catalyst_workspace_chrome(title, subtitle, body, "home")


def render_dashboard(runtime: JarvisRuntime) -> str:
    workshop_options_json = json.dumps(runtime.workshop_machine_options())
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
            <div class="split">
              <div>
                <label for="memory-subject-user">Subject Profile</label>
                <select id="memory-subject-user">
                  <option value="">Household / shared</option>
                  {adult_users}
                  <option value="caleb">Caleb</option>
                  <option value="anna">Anna</option>
                </select>
              </div>
              <div>
                <label for="memory-access-policy">Access Policy</label>
                <select id="memory-access-policy">
                  <option value="">Auto</option>
                  <option value="personal">personal</option>
                  <option value="shared">shared</option>
                  <option value="household">household</option>
                  <option value="restricted">restricted</option>
                </select>
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
              <div>
                <label for="memory-source-type">Source Type</label>
                <select id="memory-source-type">
                  <option value="user-stated">user-stated</option>
                  <option value="workflow-derived">workflow-derived</option>
                  <option value="system-observed">system-observed</option>
                  <option value="inferred-pattern">inferred-pattern</option>
                </select>
              </div>
            </div>
            <div class="split">
              <div>
                <label for="memory-confidence">Confidence</label>
                <select id="memory-confidence">
                  <option value="confirmed">confirmed</option>
                  <option value="inferred">inferred</option>
                  <option value="provisional">provisional</option>
                  <option value="stale">stale</option>
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
          <div id="memory-profile-facts" class="draft-list" style="margin-top:12px;"></div>
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
            <div class="split">
              <div>
                <label for="cad-family">Part Family</label>
                <select id="cad-family"></select>
              </div>
              <div>
                <label for="cad-printer">Machine Target</label>
                <select id="cad-printer"></select>
              </div>
            </div>
            <div class="split">
              <div>
                <label for="cad-profile">Print Profile</label>
                <select id="cad-profile"></select>
              </div>
              <div>
                <label for="cad-slicer">Slicer Handoff</label>
                <select id="cad-slicer"></select>
              </div>
            </div>
            <div id="cad-family-guidance" class="muted" style="margin:8px 0 10px 0;"></div>
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
            <button type="submit">Generate Model Forge Package</button>
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
    const workshopMachineOptions = {workshop_options_json};
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
        `Pending proposals: ${{escapeHtml(String((memoryOverview.counts || {{}}).pending_proposals || 0))}}`,
        `Profile facts: ${{escapeHtml(String((memoryOverview.counts || {{}}).visible_profile_facts || 0))}}`
      ].map((item) => `<div class="status-item">${{item}}</div>`).join("");

      const memoryFacts = document.getElementById("memory-profile-facts");
      memoryFacts.innerHTML = (memoryOverview.profile_facts || []).map((item) => `
        <div class="approval-item">
          <strong>${{escapeHtml(item.subject_display_name || "Household")}}</strong> · ${{escapeHtml(item.lane || "personal")}} · ${{escapeHtml(item.confidence || "confirmed")}}<br>
          <div>${{escapeHtml(item.summary || "")}}</div>
          <div class="muted" style="margin-top:8px;">${{escapeHtml((item.source_entry_ids || []).length)}} supporting memory entr${{(item.source_entry_ids || []).length === 1 ? "y" : "ies"}}</div>
        </div>
      `).join("") || '<div class="approval-item muted">No durable profile facts yet.</div>';

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
          <strong>${{escapeHtml(item.part_name)}}</strong> · ${{escapeHtml(item.export_status || "cad-package")}}<br>
          <div class="muted">${{escapeHtml(item.summary)}}</div>
          <div style="margin-top:8px;">${{escapeHtml((item.parameters || []).join(", "))}}</div>
          <div class="muted" style="margin-top:8px;">
            Family: ${{escapeHtml(item.family || "unspecified")}} ·
            Printer: ${{escapeHtml(item.printer_id || "unassigned")}} ·
            Profile: ${{escapeHtml(item.profile_name || "unassigned")}} ·
            Material: ${{escapeHtml(item.material || "unassigned")}}
          </div>
          <div class="muted" style="margin-top:8px;">${{escapeHtml(item.export_detail || "No export detail yet.")}}</div>
          <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;">
            <a class="btn btn-subtle" href="/api/model-forge/package/${{encodeURIComponent(item.package_id)}}/download/stl">Download STL</a>
            <a class="btn btn-subtle" href="/api/model-forge/package/${{encodeURIComponent(item.package_id)}}/download/step">Download STEP</a>
            <a class="btn btn-subtle" href="/api/model-forge/package/${{encodeURIComponent(item.package_id)}}/download/3mf">Download 3MF</a>
            <a class="btn btn-subtle" href="/api/model-forge/package/${{encodeURIComponent(item.package_id)}}/download/slicer-pack">Download Slicer Pack</a>
            <button type="button" class="btn btn-secondary cad-open-slicer" data-package-id="${{escapeHtml(item.package_id)}}">Open In Slicer</button>
          </div>
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
          <span class="${{item.ok ? "ok" : "blocked"}}">${{escapeHtml(item.state || (item.ok ? "ok" : "blocked"))}}</span>
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
          subject_user_id: document.getElementById("memory-subject-user").value,
          access_policy: document.getElementById("memory-access-policy").value,
          project: document.getElementById("memory-project").value,
          summary: document.getElementById("memory-summary").value,
          detail: document.getElementById("memory-detail").value,
          tags: document.getElementById("memory-tags").value,
          sensitivity: document.getElementById("memory-sensitivity").value,
          source_type: document.getElementById("memory-source-type").value,
          confidence: document.getElementById("memory-confidence").value
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

    function populateCadMachineControls() {{
      const familySelect = document.getElementById("cad-family");
      const printerSelect = document.getElementById("cad-printer");
      const profileSelect = document.getElementById("cad-profile");
      const slicerSelect = document.getElementById("cad-slicer");
      if (!familySelect || !printerSelect || !profileSelect || !slicerSelect) {{
        return;
      }}

      const familyOptions = workshopMachineOptions.families || [];
      familySelect.innerHTML = familyOptions.map((item) => `<option value="${{escapeHtml(item.id)}}">${{escapeHtml(item.label)}}</option>`).join("");
      if (!familySelect.value && familyOptions.length) {{
        familySelect.value = familyOptions[0].id;
      }}

      const printers = workshopMachineOptions.printers || [];
      printerSelect.innerHTML = printers.map((item) => `<option value="${{escapeHtml(item.id)}}">${{escapeHtml(item.name)}}</option>`).join("");
      if (workshopMachineOptions.default_printer_id) {{
        printerSelect.value = workshopMachineOptions.default_printer_id;
      }} else if (printers.length) {{
        printerSelect.value = printers[0].id;
      }}

      const slicers = workshopMachineOptions.slicers || [];
      const slicerOptions = [`<option value="">System default</option>`].concat(
        slicers.map((item) => `<option value="${{escapeHtml(item.id)}}">${{escapeHtml(item.label)}}</option>`)
      );
      slicerSelect.innerHTML = slicerOptions.join("");

      refreshCadProfileOptions();
      refreshCadFamilyGuidance();
    }}

    function refreshCadProfileOptions() {{
      const printerSelect = document.getElementById("cad-printer");
      const profileSelect = document.getElementById("cad-profile");
      if (!printerSelect || !profileSelect) {{
        return;
      }}
      const printers = workshopMachineOptions.printers || [];
      const printer = printers.find((item) => item.id === printerSelect.value) || printers[0];
      const profiles = Array.isArray(printer?.profiles) ? printer.profiles : [];
      profileSelect.innerHTML = profiles.map((item) => `<option value="${{escapeHtml(item)}}">${{escapeHtml(item)}}</option>`).join("");
      if (!profileSelect.value && profiles.length) {{
        profileSelect.value = profiles[0];
      }}
    }}

    function refreshCadFamilyGuidance() {{
      const family = document.getElementById("cad-family")?.value || "bracket";
      const guidance = document.getElementById("cad-family-guidance");
      const dimensions = document.getElementById("cad-dimensions");
      const constraints = document.getElementById("cad-constraints");
      const part = document.getElementById("cad-part");
      const profiles = {{
        bracket: {{
          label: "Bracket workflow",
          note: "Bias toward hole spacing, plate thickness, bend radius, and load path.",
          dimensions: "hole spacing 110 mm, plate width 30 mm, thickness 8 mm, bend radius 12 mm",
          constraints: "Preserve mounting geometry, add drainage, keep corners softened for fatigue resistance.",
          part: "Garden bench bracket",
        }},
        enclosure: {{
          label: "Enclosure workflow",
          note: "Bias toward outer size, wall thickness, lid fit, cable exits, and screw pattern.",
          dimensions: "outer length 120 mm, width 80 mm, height 40 mm, wall thickness 3 mm",
          constraints: "Keep lid printable, allow cable exit, leave room for fasteners and board clearance.",
          part: "Sensor enclosure",
        }},
        spacer: {{
          label: "Spacer workflow",
          note: "Bias toward exact height, inner diameter, outer diameter, and stable concentric geometry.",
          dimensions: "outer diameter 18 mm, inner diameter 6.2 mm, height 12 mm",
          constraints: "Maintain tight axial height, keep bore clean, no supports if possible.",
          part: "Fixture spacer",
        }},
        mount: {{
          label: "Mount workflow",
          note: "Bias toward footprint, riser height, hole pattern, and surface attachment.",
          dimensions: "base length 90 mm, width 40 mm, thickness 6 mm, riser height 35 mm",
          constraints: "Preserve fastener access, keep base stable, strengthen the riser-to-base transition.",
          part: "Camera mount",
        }},
      }};
      const selected = profiles[family] || profiles.bracket;
      if (guidance) {{
        guidance.textContent = `${{selected.label}}: ${{selected.note}}`;
      }}
      if (dimensions && (!dimensions.value || dimensions.dataset.autofill === "true")) {{
        dimensions.value = selected.dimensions;
        dimensions.dataset.autofill = "true";
      }}
      if (constraints && (!constraints.value || constraints.dataset.autofill === "true")) {{
        constraints.value = selected.constraints;
        constraints.dataset.autofill = "true";
      }}
      if (part && (!part.value || part.dataset.autofill === "true")) {{
        part.value = selected.part;
        part.dataset.autofill = "true";
      }}
    }}

    async function cadPackageRequest() {{
      const data = await loadJSON("/api/cad-package", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: "Chris",
          family: document.getElementById("cad-family").value,
          printer: document.getElementById("cad-printer").value,
          profile: document.getElementById("cad-profile").value,
          part: document.getElementById("cad-part").value,
          dimensions: document.getElementById("cad-dimensions").value,
          constraints: document.getElementById("cad-constraints").value
        }})
      }});
      document.getElementById("cad-output").textContent = JSON.stringify(data, null, 2);
      await refreshDashboard();
    }}

    async function openCadPackageInSlicer(packageId) {{
      const slicerSelect = document.getElementById("cad-slicer");
      const data = await loadJSON(`/api/model-forge/package/${{encodeURIComponent(packageId)}}/open-in-slicer`, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          slicer_app: slicerSelect ? slicerSelect.value : ""
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

    populateCadMachineControls();
    document.getElementById("cad-printer").addEventListener("change", refreshCadProfileOptions);
    document.getElementById("cad-family").addEventListener("change", refreshCadFamilyGuidance);
    ["cad-part", "cad-dimensions", "cad-constraints"].forEach((id) => {{
      const field = document.getElementById(id);
      field?.addEventListener("input", () => {{
        field.dataset.autofill = "false";
      }});
    }});

    document.getElementById("cad-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      cadPackageRequest().catch((error) => {{
        document.getElementById("cad-output").textContent = error.message;
      }});
    }});

    document.getElementById("cad-packages").addEventListener("click", (event) => {{
      const target = event.target;
      if (!(target instanceof HTMLElement)) {{
        return;
      }}
      const button = target.closest(".cad-open-slicer");
      if (!(button instanceof HTMLElement)) {{
        return;
      }}
      const packageId = button.dataset.packageId;
      if (!packageId) {{
        return;
      }}
      openCadPackageInSlicer(packageId).catch((error) => {{
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
