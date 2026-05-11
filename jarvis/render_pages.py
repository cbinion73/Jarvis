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
