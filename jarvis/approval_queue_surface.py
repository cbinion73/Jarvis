from __future__ import annotations

import html
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .approvals import ApprovalQueue, ApprovalRequest


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HTML_OUTPUT = REPO_ROOT / "artifacts" / "generated" / "jarvis-approval-queue.html"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "artifacts" / "generated" / "jarvis-approval-queue.json"


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


def _command_hints(request_id: str) -> dict[str, str]:
    base = f"python3 scripts/manage_approval_queue.py"
    return {
        "show": f"{base} show {request_id}",
        "approve": f"{base} approve {request_id}",
        "reject": f'{base} reject {request_id} --reason "why this is not safe yet"',
        "cancel": f"{base} cancel {request_id}",
        "execute": f"{base} execute {request_id}",
    }


def _serialize_item(item: ApprovalRequest) -> dict[str, Any]:
    decision = dict(item.supervision_decision or {})
    return {
        "request_id": item.request_id,
        "title": item.title,
        "description": item.description,
        "status": item.status,
        "risk_tier": item.risk_tier,
        "agent_id": item.agent_id,
        "agent_label": item.agent_label,
        "actor_id": item.actor_id,
        "action_type": item.action_type,
        "priority": item.priority,
        "requested_at": item.requested_at,
        "expires_at": item.expires_at,
        "approved_by": item.approved_by,
        "approved_at": item.approved_at,
        "executed_at": item.executed_at,
        "rejection_reason": item.rejection_reason,
        "trust_zone_id": item.trust_zone_id,
        "lane_id": item.lane_id,
        "arena_id": item.arena_id,
        "requested_outcome": item.requested_outcome,
        "requires_confirmation": item.requires_confirmation,
        "confirmation_phrase": item.confirmation_phrase,
        "tags": list(item.tags or []),
        "supervision_decision": decision,
        "commands": _command_hints(item.request_id),
        "actions": {
            "approve": f"/api/approvals/{item.request_id}/approve",
            "reject": f"/api/approvals/{item.request_id}/reject",
            "cancel": f"/api/approvals/{item.request_id}/cancel",
            "execute": f"/api/approvals/{item.request_id}/execute",
        },
    }


def _what_needs_me(pending: list[dict[str, Any]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for item in pending[:6]:
        detail = f"{item['risk_tier']} risk {item['action_type']} for {item['actor_id']}"
        if item["supervision_decision"].get("resolution"):
            detail += f" ({item['supervision_decision']['resolution']})"
        items.append(
            {
                "title": item["title"],
                "detail": detail,
                "command": item["commands"]["show"],
            }
        )
    return items


def build_approval_queue_snapshot(*, approvals_root: Path | None = None, history_limit: int = 12) -> dict[str, Any]:
    with _approval_root(approvals_root):
        queue = ApprovalQueue()
        pending = [_serialize_item(item) for item in queue.get_pending()]
        history = [_serialize_item(item) for item in queue.get_history(limit=history_limit)]

    return {
        "generated_at": _now_iso(),
        "pending_count": len(pending),
        "history_count": len(history),
        "pending": pending,
        "history": history,
        "what_needs_me": _what_needs_me(pending),
        "proof_paths": {
            "generated_html": str(DEFAULT_HTML_OUTPUT),
            "generated_json": str(DEFAULT_JSON_OUTPUT),
            "script": str(REPO_ROOT / "scripts" / "manage_approval_queue.py"),
        },
    }


def render_approval_queue_html(snapshot: dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return html.escape(str(value))

    pending = snapshot["pending"]
    history = snapshot["history"]

    def pending_cards(items: list[dict[str, Any]]) -> str:
        if not items:
            return "<article class='empty-card'>No pending approvals right now.</article>"
        cards = []
        for item in items:
            supervision = item["supervision_decision"].get("resolution", "unclassified")
            tags = "".join(f"<span class='pill'>{esc(tag)}</span>" for tag in item["tags"])
            cards.append(
                f"""
                <article class="approval-card">
                  <header>
                    <div>
                      <h3>{esc(item['title'])}</h3>
                      <p>{esc(item['description'])}</p>
                    </div>
                    <div class="risk risk-{esc(item['risk_tier'])}">{esc(item['risk_tier'])}</div>
                  </header>
                  <dl class="meta">
                    <div><dt>Agent</dt><dd>{esc(item['agent_label'])}</dd></div>
                    <div><dt>Action</dt><dd>{esc(item['action_type'])}</dd></div>
                    <div><dt>Actor</dt><dd>{esc(item['actor_id'])}</dd></div>
                    <div><dt>Lane</dt><dd>{esc(item['lane_id'] or 'unassigned')}</dd></div>
                    <div><dt>Trust</dt><dd>{esc(item['trust_zone_id'] or 'unspecified')}</dd></div>
                    <div><dt>Resolution</dt><dd>{esc(supervision)}</dd></div>
                    <div><dt>Requested</dt><dd>{esc(item['requested_at'])}</dd></div>
                    <div><dt>Expires</dt><dd>{esc(item['expires_at'])}</dd></div>
                  </dl>
      <div class="tags">{tags or "<span class='pill muted'>No tags</span>"}</div>
                  <div class="action-row">
                    <button type="button" data-endpoint="{esc(item['actions']['approve'])}" data-method="POST">Approve</button>
                    <button type="button" data-endpoint="{esc(item['actions']['reject'])}" data-method="POST" data-body='{{"reason":"Need a safer plan first"}}'>Reject</button>
                    <button type="button" data-endpoint="{esc(item['actions']['cancel'])}" data-method="POST">Cancel</button>
                    <button type="button" data-endpoint="{esc(item['actions']['execute'])}" data-method="POST">Execute</button>
                  </div>
                  <div class="commands">
                    <code>{esc(item['commands']['show'])}</code>
                    <code>{esc(item['commands']['approve'])}</code>
                    <code>{esc(item['commands']['reject'])}</code>
                    <code>{esc(item['commands']['execute'])}</code>
                  </div>
                </article>
                """
            )
        return "".join(cards)

    def history_rows(items: list[dict[str, Any]]) -> str:
        if not items:
            return "<tr><td colspan='5' class='empty'>No decision history yet.</td></tr>"
        rows = []
        for item in items:
            rows.append(
                f"""
                <tr>
                  <td>{esc(item['status'])}</td>
                  <td>{esc(item['title'])}</td>
                  <td>{esc(item['agent_label'])}</td>
                  <td>{esc(item['approved_by'] or '-')}</td>
                  <td>{esc(item['approved_at'] or item['executed_at'] or item['requested_at'])}</td>
                </tr>
                """
            )
        return "".join(rows)

    needs_me = "".join(
        f"<li><strong>{esc(item['title'])}</strong><span>{esc(item['detail'])}</span><code>{esc(item['command'])}</code></li>"
        for item in snapshot["what_needs_me"]
    ) or "<li class='empty'>Nothing needs a decision right now.</li>"

    raw_json = esc(json.dumps(snapshot, indent=2))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Approval Queue</title>
  <style>
    :root {{
      --bg: #061019;
      --panel: #0d1724;
      --panel-2: #142334;
      --line: rgba(143, 185, 255, 0.16);
      --text: #edf6fc;
      --muted: #95aabb;
      --cyan: #76d7df;
      --green: #74d9a5;
      --amber: #e7b25c;
      --red: #ef8f8f;
      --font-ui: "SF Pro Display", "Segoe UI", sans-serif;
      --font-mono: "SF Mono", "JetBrains Mono", monospace;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: radial-gradient(circle at top, #10243a 0%, var(--bg) 42%, #03070d 100%);
      color: var(--text);
      font-family: var(--font-ui);
    }}
    .shell {{ width: min(1240px, calc(100% - 32px)); margin: 0 auto; padding: 28px 0 48px; }}
    .hero, .panel {{
      background: rgba(13, 23, 36, 0.92);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: 0 24px 64px rgba(0, 0, 0, 0.28);
    }}
    .hero {{ padding: 24px; display: grid; gap: 18px; }}
    .hero h1 {{ margin: 0; font-size: clamp(2rem, 4vw, 3.2rem); }}
    .hero p {{ margin: 0; color: var(--muted); max-width: 70ch; }}
    .hero-grid {{ display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }}
    .metric {{ background: var(--panel-2); border: 1px solid var(--line); border-radius: 18px; padding: 14px; }}
    .metric strong {{ display: block; color: var(--cyan); font-size: 1.7rem; }}
    .layout {{ display: grid; gap: 18px; grid-template-columns: 1.5fr 1fr; margin-top: 18px; }}
    .panel {{ padding: 22px; }}
    .panel h2 {{ margin: 0 0 12px; font-size: 1.1rem; }}
    .needs-list, .guide-list {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 12px; }}
    .needs-list li, .guide-list li {{ border: 1px solid var(--line); border-radius: 16px; background: rgba(255,255,255,0.02); padding: 12px; display: grid; gap: 8px; }}
    .needs-list strong, .guide-list strong {{ display: block; }}
    .needs-list span, .guide-list span {{ color: var(--muted); }}
    .needs-list code, .guide-list code, .commands code, pre {{
      font-family: var(--font-mono);
      background: rgba(3, 10, 18, 0.82);
      border: 1px solid rgba(143, 185, 255, 0.16);
      border-radius: 12px;
      padding: 10px 12px;
      display: block;
      overflow-x: auto;
    }}
    .approval-grid {{ display: grid; gap: 14px; }}
    .approval-card, .empty-card {{
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 18px;
      background: rgba(255, 255, 255, 0.02);
    }}
    .approval-card header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
    }}
    .approval-card h3 {{ margin: 0 0 8px; }}
    .approval-card p {{ margin: 0; color: var(--muted); }}
    .risk {{
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      border: 1px solid currentColor;
    }}
    .risk-low {{ color: var(--green); }}
    .risk-medium {{ color: var(--amber); }}
    .risk-high, .risk-critical {{ color: var(--red); }}
    .meta {{
      margin: 14px 0;
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    }}
    .meta dt {{ color: var(--muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em; }}
    .meta dd {{ margin: 6px 0 0; }}
    .tags {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }}
    .pill {{ border: 1px solid var(--line); border-radius: 999px; padding: 6px 10px; font-size: 0.8rem; }}
    .pill.muted {{ color: var(--muted); }}
    .commands {{ display: grid; gap: 10px; }}
    .action-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 12px;
    }}
    button {{
      border: 1px solid var(--line);
      background: rgba(104, 212, 223, 0.12);
      color: var(--text);
      border-radius: 999px;
      padding: 10px 14px;
      font: inherit;
      cursor: pointer;
    }}
    button:hover {{ background: rgba(104, 212, 223, 0.2); }}
    .status-note {{
      margin-top: 12px;
      color: var(--muted);
      min-height: 1.2em;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid var(--line); vertical-align: top; }}
    th {{ color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; }}
    .empty {{ color: var(--muted); }}
    @media (max-width: 960px) {{
      .layout {{ grid-template-columns: 1fr; }}
      .approval-card header {{ flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div>
        <h1>JARVIS Approval Queue</h1>
        <p>Real local operator surface over the approval substrate. Use it to see what needs consent, inspect supervision context, and run the exact commands that move a request forward.</p>
      </div>
      <div class="hero-grid">
        <div class="metric"><span>Pending</span><strong>{esc(snapshot['pending_count'])}</strong></div>
        <div class="metric"><span>History</span><strong>{esc(snapshot['history_count'])}</strong></div>
        <div class="metric"><span>Generated</span><strong>{esc(snapshot['generated_at'])}</strong></div>
      </div>
    </section>
    <section class="layout">
      <div class="panel">
        <h2>Needs Me Now</h2>
        <ul class="needs-list">{needs_me}</ul>
      </div>
      <div class="panel">
        <h2>Operator Guide</h2>
        <ul class="guide-list">
          <li><strong>List queue</strong><span>Print current pending items as JSON.</span><code>python3 scripts/manage_approval_queue.py list</code></li>
          <li><strong>Render surface</strong><span>Generate this HTML and its JSON payload from live queue data.</span><code>python3 scripts/manage_approval_queue.py render</code></li>
          <li><strong>Served mode</strong><span>When this page is opened through the JARVIS app, the action buttons call the live approval APIs directly.</span><code>GET /approval-queue and POST /api/approvals/&lt;request_id&gt;/*</code></li>
        </ul>
        <p class="status-note" id="status-note">Open this through the app for live actions, or use the CLI commands below from a local file.</p>
      </div>
    </section>
    <section class="panel" style="margin-top: 18px;">
      <h2>Pending Queue</h2>
      <div class="approval-grid">{pending_cards(pending)}</div>
    </section>
    <section class="panel" style="margin-top: 18px;">
      <h2>Decision History</h2>
      <table>
        <thead>
          <tr><th>Status</th><th>Request</th><th>Agent</th><th>Actor</th><th>When</th></tr>
        </thead>
        <tbody>{history_rows(history)}</tbody>
      </table>
    </section>
    <section class="panel" style="margin-top: 18px;">
      <h2>Raw Snapshot JSON</h2>
      <pre>{raw_json}</pre>
    </section>
  </main>
  <script>
    const statusNote = document.getElementById("status-note");
    for (const button of document.querySelectorAll("button[data-endpoint]")) {{
      button.addEventListener("click", async () => {{
        const endpoint = button.getAttribute("data-endpoint");
        const method = button.getAttribute("data-method") || "POST";
        const rawBody = button.getAttribute("data-body");
        statusNote.textContent = `Calling ${{endpoint}}...`;
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
          statusNote.textContent = `Success: ${{endpoint}}`;
          window.setTimeout(() => window.location.reload(), 250);
        }} catch (error) {{
          statusNote.textContent = `Action failed: ${{String(error)}}`;
        }}
      }});
    }}
  </script>
</body>
</html>
"""


def write_approval_queue_snapshot(
    snapshot: dict[str, Any],
    *,
    html_output: Path = DEFAULT_HTML_OUTPUT,
    json_output: Path = DEFAULT_JSON_OUTPUT,
) -> dict[str, str]:
    html_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    html_output.write_text(render_approval_queue_html(snapshot), encoding="utf-8")
    json_output.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    return {"html": str(html_output), "json": str(json_output)}
