from __future__ import annotations

import html
import json
import subprocess
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .agent_registry_contract import load_contract_bundle
from .approvals import ApprovalQueue
from .config import AppConfig
from .integrations import IntegrationStatus
from .memory import MemoryStore
from .status import collect_status


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MEMORY_ROOT = REPO_ROOT / "data" / "memory"
DEFAULT_HTML_OUTPUT = REPO_ROOT / "artifacts" / "generated" / "jarvis-supervision-snapshot.html"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "artifacts" / "generated" / "jarvis-supervision-snapshot.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _approval_root(root: Path | None) -> Iterable[None]:
    previous = ApprovalQueue.ROOT
    if root is not None:
        ApprovalQueue.ROOT = root
    try:
        yield
    finally:
        ApprovalQueue.ROOT = previous


def _git_lines(*args: str) -> list[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def _git_summary() -> dict[str, Any]:
    branch = _git_lines("branch", "--show-current")
    head = _git_lines("rev-parse", "--short", "HEAD")
    dirty = _git_lines("status", "--short")
    recent = _git_lines("log", "--oneline", "-5")
    return {
        "branch": branch[0] if branch else "",
        "head": head[0] if head else "",
        "dirty_count": len(dirty),
        "dirty_sample": dirty[:8],
        "recent_commits": recent,
    }


def _registry_snapshot() -> dict[str, Any]:
    try:
        return load_contract_bundle(validate=True).snapshot()
    except Exception as exc:
        return {
            "registry_error": str(exc),
            "agent_count": 0,
            "domains": [],
            "authority_stages": [],
            "posture": {},
        }


def _serialize_integrations(statuses: list[IntegrationStatus]) -> list[dict[str, Any]]:
    return [
        {
            "name": item.name,
            "ok": item.ok,
            "detail": item.detail,
        }
        for item in statuses
    ]


def _attention_items(queue: ApprovalQueue) -> list[dict[str, Any]]:
    items = []
    for item in queue.get_pending():
        items.append(
            {
                "request_id": item.request_id,
                "title": item.title,
                "risk_tier": item.risk_tier,
                "agent_label": item.agent_label,
                "action_type": item.action_type,
                "actor_id": item.actor_id,
                "expires_at": item.expires_at,
                "requested_at": item.requested_at,
                "why_now": item.description,
                "actions": {
                    "approve": f"/api/approvals/{item.request_id}/approve",
                    "reject": f"/api/approvals/{item.request_id}/reject",
                    "cancel": f"/api/approvals/{item.request_id}/cancel",
                    "execute": f"/api/approvals/{item.request_id}/execute",
                },
            }
        )
    return items


def _memory_summary(store: MemoryStore) -> dict[str, Any]:
    entries = store.list_entries()
    proposals = store.list_proposals()
    facts = store.list_profile_facts()
    return {
        "entry_count": len(entries),
        "proposal_count": len(proposals),
        "fact_count": len(facts),
        "latest_entry_titles": [item.get("title", "") for item in entries[-3:]][::-1],
        "pending_proposals": [
            item.get("title", "")
            for item in proposals
            if str(item.get("status", "")).lower() not in {"accepted", "rejected", "archived"}
        ][:5],
    }


def _what_needs_me(
    approvals: list[dict[str, Any]],
    integrations: list[dict[str, Any]],
    memory_summary: dict[str, Any],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for approval in approvals[:5]:
        items.append(
            {
                "kind": "approval",
                "title": approval["title"],
                "detail": f"{approval['risk_tier']} request from {approval['agent_label']}",
            }
        )
    for status in integrations:
        if not status["ok"]:
            items.append(
                {
                    "kind": "integration",
                    "title": status["name"],
                    "detail": status["detail"],
                }
            )
    for title in memory_summary["pending_proposals"][:3]:
        items.append(
            {
                "kind": "memory",
                "title": title,
                "detail": "Pending memory proposal needs review",
            }
        )
    return items[:8]


def build_supervision_snapshot(
    *,
    memory_root: Path | None = None,
    approvals_root: Path | None = None,
    config: AppConfig | None = None,
    integration_statuses: list[IntegrationStatus] | None = None,
) -> dict[str, Any]:
    git_summary = _git_summary()
    memory_store = MemoryStore(memory_root or DEFAULT_MEMORY_ROOT)
    with _approval_root(approvals_root):
        queue = ApprovalQueue()
        approvals = _attention_items(queue)
    integrations = _serialize_integrations(
        integration_statuses if integration_statuses is not None else collect_status(config or AppConfig.from_env())
    )
    memory = _memory_summary(memory_store)
    registry = _registry_snapshot()
    needs_me = _what_needs_me(approvals, integrations, memory)
    return {
        "generated_at": _now_iso(),
        "lane": {
            "branch": git_summary["branch"],
            "head": git_summary["head"],
            "dirty_count": git_summary["dirty_count"],
            "recent_commits": git_summary["recent_commits"],
            "dirty_sample": git_summary["dirty_sample"],
        },
        "return_brief": {
            "summary": (
                f"{len(approvals)} approvals pending, "
                f"{sum(1 for item in integrations if not item['ok'])} integration issues, "
                f"{memory['proposal_count']} memory proposals, "
                f"{registry.get('agent_count', 0)} registered agents"
            ),
            "what_needs_me_count": len(needs_me),
        },
        "attention_queue": approvals,
        "memory": memory,
        "registry": registry,
        "integrations": integrations,
        "what_needs_me": needs_me,
        "proof_paths": {
            "doctrine": str(REPO_ROOT / "JARVIS_LEVEL9_DOCTRINE.md"),
            "command_center_model": str(REPO_ROOT / "docs" / "jarvis-desktop-command-center-model.md"),
            "generated_html": str(DEFAULT_HTML_OUTPUT),
            "generated_json": str(DEFAULT_JSON_OUTPUT),
            "served_page": "/supervision-snapshot",
            "approval_queue": "/approval-queue",
            "approval_queue_snapshot": "/api/approval-queue/snapshot",
        },
    }


def render_supervision_snapshot_html(snapshot: dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return html.escape(str(value))

    def list_items(items: list[dict[str, Any]], title_key: str, detail_key: str) -> str:
        if not items:
            return "<li class='empty'>Nothing pending right now.</li>"
        return "".join(
            f"<li><strong>{esc(item.get(title_key, ''))}</strong><span>{esc(item.get(detail_key, ''))}</span></li>"
            for item in items
        )

    def attention_cards(items: list[dict[str, Any]]) -> str:
        if not items:
            return "<li class='empty'>Nothing pending right now.</li>"
        cards = []
        for item in items:
            request_id = str(item.get("request_id", "") or "")
            actions = dict(item.get("actions") or {})
            if request_id:
                actions.setdefault("approve", f"/api/approvals/{request_id}/approve")
                actions.setdefault("reject", f"/api/approvals/{request_id}/reject")
                actions.setdefault("cancel", f"/api/approvals/{request_id}/cancel")
                actions.setdefault("execute", f"/api/approvals/{request_id}/execute")
            cards.append(
                f"""
                <li>
                  <strong>{esc(item.get('title', ''))}</strong>
                  <span>{esc(item.get('why_now', ''))}</span>
                  <div class="action-row">
                    <button type="button" data-endpoint="{esc(actions.get('approve', ''))}" data-method="POST">Approve</button>
                    <button type="button" data-endpoint="{esc(actions.get('reject', ''))}" data-method="POST" data-body='{{"reason":"Need a safer plan first"}}'>Reject</button>
                    <button type="button" data-endpoint="{esc(actions.get('cancel', ''))}" data-method="POST">Cancel</button>
                    <button type="button" data-endpoint="{esc(actions.get('execute', ''))}" data-method="POST">Execute</button>
                  </div>
                </li>
                """
            )
        return "".join(cards)

    integrations_html = "".join(
        f"<li class=\"{'ok' if item['ok'] else 'warn'}\"><strong>{esc(item['name'])}</strong><span>{esc(item['detail'])}</span></li>"
        for item in snapshot["integrations"]
    )
    dirty_lines = snapshot["lane"]["dirty_sample"]
    dirty_html = "".join(f"<li><code>{esc(line)}</code></li>" for line in dirty_lines) or "<li class='empty'>Clean sample unavailable.</li>"
    recent_html = "".join(f"<li><code>{esc(line)}</code></li>" for line in snapshot["lane"]["recent_commits"]) or "<li class='empty'>No recent commits.</li>"
    payload_json = esc(json.dumps(snapshot, indent=2))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Supervision Snapshot</title>
  <style>
    :root {{
      --bg: #061019;
      --panel: #0d1724;
      --line: rgba(143, 185, 255, 0.18);
      --text: #edf6fc;
      --muted: #8fa7bb;
      --cyan: #68d4df;
      --green: #66d89f;
      --amber: #f0b86d;
      --font-ui: "SF Pro Display", "Segoe UI", sans-serif;
      --font-mono: "SF Mono", "JetBrains Mono", monospace;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: linear-gradient(180deg, var(--bg) 0%, #02070d 100%);
      color: var(--text);
      font-family: var(--font-ui);
    }}
    .shell {{ width: min(1240px, calc(100% - 32px)); margin: 0 auto; padding: 28px 0 48px; }}
    .hero, .panel {{
      border: 1px solid var(--line);
      border-radius: 22px;
      background: linear-gradient(180deg, rgba(13, 23, 36, 0.98), rgba(8, 15, 24, 0.98));
      box-shadow: 0 24px 72px rgba(0, 0, 0, 0.34);
    }}
    .hero {{ padding: 26px; margin-bottom: 18px; }}
    .eyebrow {{
      display: inline-block;
      padding: 7px 10px;
      border-radius: 999px;
      border: 1px solid rgba(104, 212, 223, 0.28);
      background: rgba(104, 212, 223, 0.08);
      color: var(--cyan);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    h1, h2, p, ul {{ margin: 0; }}
    h1 {{ margin-top: 14px; font-size: clamp(34px, 5vw, 56px); line-height: 0.95; letter-spacing: -0.05em; max-width: 12ch; }}
    .hero p {{ margin-top: 14px; max-width: 82ch; color: var(--muted); line-height: 1.65; }}
    .stats {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-top: 20px; }}
    .stat {{ padding: 18px; border-radius: 18px; border: 1px solid var(--line); background: rgba(255,255,255,0.03); }}
    .stat strong {{ display: block; margin-bottom: 6px; font-size: 28px; font-variant-numeric: tabular-nums; }}
    .grid {{ display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 18px; }}
    .panel {{ padding: 22px; }}
    .panel h2 {{ margin-bottom: 12px; font-size: 21px; letter-spacing: -0.03em; }}
    .panel ul {{ list-style: none; padding: 0; display: grid; gap: 10px; }}
    .panel li {{ padding: 12px 14px; border-radius: 14px; border: 1px solid var(--line); background: rgba(255,255,255,0.03); }}
    .panel li strong {{ display: block; margin-bottom: 4px; }}
    .panel li span, .panel p {{ color: var(--muted); line-height: 1.6; }}
    .panel li.ok strong {{ color: var(--green); }}
    .panel li.warn strong {{ color: var(--amber); }}
    .mono {{ font-family: var(--font-mono); color: var(--cyan); }}
    .action-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 10px;
    }}
    button {{
      border: 1px solid var(--line);
      background: rgba(104, 212, 223, 0.12);
      color: var(--text);
      border-radius: 999px;
      padding: 9px 12px;
      font: inherit;
      cursor: pointer;
    }}
    button:hover {{ background: rgba(104, 212, 223, 0.2); }}
    .status-note {{
      margin-top: 10px;
      color: var(--muted);
      min-height: 1.2em;
    }}
    .link-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }}
    .link-row a {{
      display: inline-flex;
      align-items: center;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      color: var(--text);
      text-decoration: none;
      background: rgba(255,255,255,0.03);
    }}
    pre {{
      margin: 0;
      padding: 16px;
      overflow: auto;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: rgba(0,0,0,0.24);
      color: #d7f1ff;
      font-family: var(--font-mono);
      font-size: 12px;
      line-height: 1.55;
    }}
    .stack {{ display: grid; gap: 18px; }}
    .empty {{ color: var(--muted); }}
    @media (max-width: 920px) {{
      .stats, .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="eyebrow">Level 9 Proof Surface</div>
      <h1>JARVIS Supervision Snapshot</h1>
      <p>
        This is a live local supervision digest built from real approval, memory, registry,
        integration, and Git lane state. It is meant to answer what changed, what needs
        attention, and what Chris can inspect right now.
      </p>
      <div class="link-row">
        <a href="/approval-queue">Open Approval Queue</a>
        <a href="/api/approval-queue/snapshot">Approval Queue JSON</a>
        <a href="/api/supervision-snapshot">Supervision Snapshot JSON</a>
      </div>
      <div class="stats">
        <div class="stat"><strong>{esc(snapshot['lane']['branch'])}</strong>Current branch</div>
        <div class="stat"><strong>{esc(snapshot['lane']['head'])}</strong>Current head</div>
        <div class="stat"><strong>{esc(len(snapshot['attention_queue']))}</strong>Pending approvals</div>
        <div class="stat"><strong>{esc(snapshot['memory']['entry_count'])}</strong>Memory entries</div>
      </div>
    </section>

    <div class="grid">
      <div class="stack">
        <section class="panel">
          <h2>Return Brief</h2>
          <p>{esc(snapshot['return_brief']['summary'])}</p>
        </section>
        <section class="panel">
          <h2>What Needs Me</h2>
          <ul>{list_items(snapshot['what_needs_me'], 'title', 'detail')}</ul>
        </section>
        <section class="panel">
          <h2>Attention Queue</h2>
          <ul>{attention_cards(snapshot['attention_queue'])}</ul>
          <p class="status-note" id="status-note">Open this through the app to run live approval actions, or use the approval queue CLI and page for local file-based proof.</p>
        </section>
        <section class="panel">
          <h2>Memory Inspector</h2>
          <ul>
            <li><strong>Entries</strong><span>{esc(snapshot['memory']['entry_count'])} entries stored</span></li>
            <li><strong>Proposals</strong><span>{esc(snapshot['memory']['proposal_count'])} proposals tracked</span></li>
            <li><strong>Facts</strong><span>{esc(snapshot['memory']['fact_count'])} profile facts tracked</span></li>
            <li><strong>Latest titles</strong><span>{esc(', '.join(snapshot['memory']['latest_entry_titles']) or 'None yet')}</span></li>
          </ul>
        </section>
      </div>
      <div class="stack">
        <section class="panel">
          <h2>Registry Status</h2>
          <ul>
            <li><strong>Agent count</strong><span>{esc(snapshot['registry'].get('agent_count', 0))}</span></li>
            <li><strong>Domains</strong><span>{esc(', '.join(snapshot['registry'].get('domains', [])) or 'None')}</span></li>
            <li><strong>Authority stages</strong><span>{esc(', '.join(snapshot['registry'].get('authority_stages', [])) or 'None')}</span></li>
          </ul>
        </section>
        <section class="panel">
          <h2>Integration Status</h2>
          <ul>{integrations_html or "<li class='empty'>No integration statuses.</li>"}</ul>
        </section>
        <section class="panel">
          <h2>Lane Residue</h2>
          <ul>{dirty_html}</ul>
        </section>
        <section class="panel">
          <h2>Recent Seams</h2>
          <ul>{recent_html}</ul>
        </section>
      </div>
    </div>

    <section class="panel" style="margin-top: 18px;">
      <h2>Raw Snapshot JSON</h2>
      <pre>{payload_json}</pre>
    </section>
  </div>
  <script>
    const statusNote = document.getElementById("status-note");
    for (const button of document.querySelectorAll("button[data-endpoint]")) {{
      button.addEventListener("click", async () => {{
        const endpoint = button.getAttribute("data-endpoint");
        const method = button.getAttribute("data-method") || "POST";
        const rawBody = button.getAttribute("data-body");
        if (statusNote) statusNote.textContent = `Calling ${{endpoint}}...`;
        try {{
          const response = await fetch(endpoint, {{
            method,
            headers: rawBody ? {{ "Content-Type": "application/json" }} : undefined,
            body: rawBody || undefined,
          }});
          const payload = await response.json().catch(() => ({{}}));
          if (!response.ok) {{
            throw new Error(payload.detail || `HTTP ${{response.status}}`);
          }}
          if (statusNote) statusNote.textContent = `Success: ${{endpoint}}`;
          window.setTimeout(() => window.location.reload(), 250);
        }} catch (error) {{
          if (statusNote) statusNote.textContent = `Action failed: ${{String(error)}}`;
        }}
      }});
    }}
  </script>
</body>
</html>
"""


def write_supervision_snapshot(
    snapshot: dict[str, Any],
    *,
    html_output: Path = DEFAULT_HTML_OUTPUT,
    json_output: Path = DEFAULT_JSON_OUTPUT,
) -> dict[str, str]:
    html_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    html_output.write_text(render_supervision_snapshot_html(snapshot), encoding="utf-8")
    json_output.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    return {
        "html": str(html_output),
        "json": str(json_output),
    }
