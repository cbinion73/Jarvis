from __future__ import annotations

import json

from .runtime import JarvisRuntime

HARD_CENTER_DESIGN = {
    "name": "jarvis-center-cinematic-v1",
    "core_backdrop": False,
    "hologram_overlay_haze": False,
    "wireframe_core": True,
    "outer_particle_shell": True,
    "orbits": [
        [1.34, 0x6FE5FF, 0.22, 0.0018, 0.0, 0.0],
        [1.72, 0x56B6FF, -0.18, -0.0022, 3.141592653589793 / 3, 3.141592653589793 / 7],
        [2.05, 0x9CF1FF, 0.42, 0.0012, 3.141592653589793 / 2.4, -3.141592653589793 / 5],
    ],
    "shell_arcs": [
        [1.54, 232, 110, 0x86F2FF],
        [1.92, 196, 82, 0x5FB8FF],
        [2.2, 168, 96, 0x87DEFF],
    ],
}


def render_voice_shell(runtime: JarvisRuntime, initial_packet: str = "") -> str:
    users = [user.display_name for user in runtime.household.users.values()]
    adults = [user.display_name for user in runtime.household.users.values() if user.permissions == "adult"]
    modes = runtime.household.modes
    actor_options = "".join(f'<option value="{name}">{name}</option>' for name in users)
    focus_actor_options = "".join(f'<option value="{name}">{name}</option>' for name in adults)
    mode_options = "".join(
        f'<option value="{mode}">{mode.replace("-", " ").title()}</option>' for mode in modes
    )
    room_options = "".join(
        f'<option value="{room.room_id}">{room.room_id.replace("-", " ")}</option>'
        for room in runtime.household.rooms.values()
    )
    allowed_initial_packets = {
        "briefing",
        "triage",
        "today",
        "review",
        "tasks",
        "mission-control",
        "storm",
        "home",
        "family",
        "security",
        "vision",
        "chronicle",
        "workshop",
        "model-forge",
        "catalyst",
        "settings",
        "brains",
        "approvals",
        "agents",
        "finance-review",
        "wealth",
    }
    initial_packet_key = initial_packet.strip().lower()
    if initial_packet_key not in allowed_initial_packets:
        initial_packet_key = ""
    initial_packet_json = json.dumps(initial_packet_key)
    packet_tree_presets = json.dumps(
        [
            {
                "id": "scene-day",
                "label": "Day",
                "description": "Today, reviews, approvals, and executive flow.",
                "children": [
                    {"id": "scene-day-triage", "label": "Triage Window", "description": "Open the core triage and transition modal.", "packet": "triage"},
                    {"id": "scene-day-open", "label": "Open Day Scene", "description": "Focus the shell on today's operating picture.", "scene": "day"},
                    {"id": "scene-day-review", "label": "Cadence Review", "description": "Inspect rhythm, drift, and timing pressure.", "packet": "review"},
                    {"id": "scene-day-tasks", "label": "Assistant Core", "description": "Open the task and open-loops queue.", "packet": "tasks"},
                    {"id": "scene-day-mission-control", "label": "Mission Control", "description": "Inspect delegated family missions, dossiers, and approvals.", "packet": "mission-control"},
                    {"id": "scene-day-approvals", "label": "Approvals", "description": "Review actions waiting for release.", "packet": "approvals"},
                    {"id": "scene-day-wealth", "label": "Fisk Review", "description": "Inspect truthful wealth workstreams and finance signals.", "packet": "wealth"},
                    {"id": "scene-day-catalyst", "label": "Catalyst Workspace", "description": "Hand work into Catalyst.", "packet": "catalyst", "catalystPage": "home"},
                ],
            },
            {
                "id": "scene-home",
                "label": "Home",
                "description": "House state, environment, and defensive posture.",
                "children": [
                    {"id": "scene-home-open", "label": "Open Home Scene", "description": "Focus the shell on live house state.", "scene": "home"},
                    {"id": "scene-home-security", "label": "Security", "description": "Inspect incidents, arrivals, and approvals.", "packet": "security"},
                    {"id": "scene-home-vision", "label": "Vision", "description": "Run on-demand visual inspection.", "packet": "vision"},
                    {"id": "scene-home-storm", "label": "Storm", "description": "Open the dedicated weather surface.", "packet": "storm"},
                ],
            },
            {
                "id": "scene-family",
                "label": "Family",
                "description": "Household routines, mode, and coordination.",
                "children": [
                    {"id": "scene-family-open", "label": "Open Family Scene", "description": "Focus the shell on household coordination.", "scene": "family"},
                    {"id": "scene-family-briefing", "label": "First Light", "description": "Open the morning briefing surface.", "packet": "briefing"},
                    {"id": "scene-family-devices", "label": "Connected Devices", "description": "Inspect and manage household devices.", "packet": "connected-devices"},
                ],
            },
            {
                "id": "scene-build",
                "label": "Build",
                "description": "Workshop, fabrication, and model tools.",
                "children": [
                    {"id": "scene-build-open", "label": "Open Build Scene", "description": "Focus the shell on workshop and maker work.", "scene": "build"},
                    {"id": "scene-build-forge", "label": "Model Forge", "description": "Open the dedicated model and geometry surface.", "packet": "model-forge"},
                ],
            },
            {
                "id": "scene-faith",
                "label": "Faith",
                "description": "Chronicle handoff and formation continuity.",
                "children": [
                    {"id": "scene-faith-open", "label": "Open Faith Scene", "description": "Focus the shell on Chronicle continuity.", "scene": "faith"},
                ],
            },
            {
                "id": "scene-system",
                "label": "System",
                "description": "Runtime posture, providers, and shell controls.",
                "children": [
                    {"id": "scene-system-open", "label": "Open System Scene", "description": "Focus the shell on runtime and settings posture.", "scene": "system"},
                    {"id": "scene-system-brains", "label": "Brain Mesh", "description": "Inspect reasoning topology and provider status.", "packet": "brains"},
                    {"id": "scene-system-agents", "label": "Agents", "description": "Inspect specialist agent activity.", "packet": "agents"},
                ],
            },
        ]
    )
    available_modes = json.dumps(modes)
    center_design = json.dumps(HARD_CENTER_DESIGN)
    core_backdrop_css = (
        """display: none;"""
        if not HARD_CENTER_DESIGN["core_backdrop"]
        else """
      inset: 15%;
      border-radius: 50%;
      background:
        radial-gradient(circle at center, rgba(112, 233, 255, 0.14) 0%, rgba(64, 192, 255, 0.08) 18%, rgba(5, 10, 18, 0.68) 34%, rgba(4, 9, 16, 0.18) 54%, transparent 72%),
        radial-gradient(circle at center, rgba(3, 7, 14, 0.94) 0%, rgba(3, 8, 14, 0.74) 20%, rgba(4, 9, 16, 0.28) 42%, rgba(4, 9, 16, 0.06) 58%, transparent 74%);
      filter: blur(8px);
      transform: none;
      box-shadow:
        inset 0 0 44px rgba(110, 235, 255, 0.06),
        0 0 64px rgba(63, 175, 255, 0.1);
      z-index: 0;
      pointer-events: none;
"""
    )
    hologram_overlay_css = (
        """display: none;"""
        if not HARD_CENTER_DESIGN["hologram_overlay_haze"]
        else """
      position: absolute;
      inset: 0;
      pointer-events: none;
      background:
        radial-gradient(circle at center, rgba(103, 226, 255, 0.06) 0%, rgba(103, 226, 255, 0.02) 22%, rgba(4, 8, 14, 0) 56%),
        radial-gradient(circle at center, rgba(4, 8, 14, 0) 42%, rgba(4, 8, 14, 0.22) 74%, rgba(4, 8, 14, 0.44) 100%);
      opacity: 0.96;
"""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Voice Shell</title>
  <style>
    :root {{
      --bg: #050a12;
      --bg-2: #09111d;
      --ink: #f1f7ff;
      --muted: #8ca5bf;
      --line: rgba(111, 207, 255, 0.22);
      --line-soft: rgba(93, 150, 194, 0.14);
      --cyan: #6fe5ff;
      --teal: #52c7d9;
      --blue: #4ca0ff;
      --amber: #f2c870;
      --ok: #6cffaf;
      --warn: #ffcc70;
      --alert: #ff7b7b;
      --panel: rgba(7, 16, 27, 0.74);
      --panel-strong: rgba(10, 22, 36, 0.92);
      --glass-fill: linear-gradient(180deg, rgba(16, 28, 45, 0.34), rgba(6, 14, 24, 0.2));
      --glass-fill-strong: linear-gradient(180deg, rgba(16, 30, 48, 0.46), rgba(6, 14, 24, 0.28));
      --glass-edge: rgba(207, 239, 255, 0.18);
      --glass-edge-soft: rgba(111, 229, 255, 0.1);
      --glass-highlight: rgba(255, 255, 255, 0.08);
      --glass-glow: rgba(111, 229, 255, 0.18);
      --glass-shadow: 0 26px 60px rgba(0, 0, 0, 0.22);
      --glass-blur: blur(22px) saturate(150%);
      --shadow: 0 30px 80px rgba(0, 0, 0, 0.42);
      --energy: 0.45;
      --motion-rate: 1;
      /* === Living Briefing warm-study palette === */
      --warm: #c8a97e;
      --warm-dim: rgba(200, 169, 126, 0.12);
      --wood: rgba(180, 140, 90, 0.08);
      --zone-bg: rgba(6, 13, 22, 0.72);
      --zone-border: rgba(200, 169, 126, 0.14);
      --zone-glow: rgba(111, 229, 255, 0.06);
      --briefing-accent: rgba(242, 200, 112, 0.7);
      --already-accent: rgba(82, 199, 217, 0.7);
      --needs-accent: rgba(76, 160, 255, 0.7);
      --drift-accent: rgba(255, 123, 123, 0.7);
      --speak-accent: rgba(111, 229, 255, 0.5);
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ min-height: 100%; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: #03060b url("/assets/Chamber.jpg") center center / cover no-repeat;
      overflow-x: hidden;
      overflow-y: auto;
    }}
    body::before,
    body::after {{
      display: none;
    }}
    body[data-voice-state="idle"] {{ --energy: 0.35; --motion-rate: 1; }}
    body[data-voice-state="listening"] {{ --energy: 0.35; --motion-rate: 1; }}
    body[data-voice-state="responding"] {{ --energy: 0.35; --motion-rate: 1; }}
    body[data-voice-state="speaking"] {{ --energy: 0.35; --motion-rate: 1; }}
    .shell {{
      position: relative;
      display: grid;
      grid-template-rows: auto 1fr auto;
      min-height: 100vh;
      padding: 18px 22px 22px;
      gap: 18px;
    }}
    .topbar,
    .dock {{
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
      gap: 16px;
    }}
    .wordmark {{
      font-size: 16px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: #d5e9ff;
      justify-self: start;
    }}
    .state-cluster {{
      display: grid;
      justify-items: center;
      gap: 8px;
    }}
    .wave-strip {{
      display: flex;
      align-items: end;
      gap: 4px;
      height: 30px;
    }}
    .wave-strip span {{
      width: 3px;
      border-radius: 999px;
      background: linear-gradient(180deg, rgba(111, 229, 255, 0.14), var(--cyan));
      height: calc(8px + (var(--energy) * 18px));
      animation: equalize 1.1s ease-in-out infinite;
      animation-delay: calc(var(--i) * 0.05s);
      opacity: 0.9;
      box-shadow: 0 0 18px rgba(111, 229, 255, 0.34);
    }}
    .state-label {{
      font-size: 12px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--cyan);
    }}
    .state-source-indicator {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 18px;
      padding: 0 8px;
      border-radius: 999px;
      border: 1px solid rgba(108, 214, 255, 0.16);
      background: rgba(8, 16, 28, 0.34);
      color: rgba(210, 243, 255, 0.72);
      font-size: 10px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      line-height: 1;
      white-space: nowrap;
    }}
    .state-source-indicator::before {{
      content: "";
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: rgba(108, 214, 255, 0.5);
      box-shadow: 0 0 10px rgba(108, 214, 255, 0.28);
      flex: 0 0 auto;
    }}
    .state-source-indicator[data-provider="ollama"]::before {{
      background: rgba(124, 244, 198, 0.62);
      box-shadow: 0 0 10px rgba(124, 244, 198, 0.3);
    }}
    .state-source-indicator[data-provider="openai"]::before {{
      background: rgba(108, 214, 255, 0.62);
    }}
    .state-source-indicator[data-provider="fallback"]::before,
    .state-source-indicator[data-provider="policy"]::before {{
      background: rgba(255, 206, 109, 0.62);
      box-shadow: 0 0 10px rgba(255, 206, 109, 0.26);
    }}
    .meta-rail {{
      justify-self: end;
      display: flex;
      align-items: center;
      gap: 10px;
      color: var(--muted);
      font-size: 13px;
    }}
    .meta-triage,
    .meta-weather {{
      appearance: none;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 0;
      border: none;
      background: transparent;
      color: var(--ink);
      font: inherit;
      cursor: pointer;
    }}
    .meta-triage[disabled],
    .meta-weather[disabled] {{
      cursor: default;
      opacity: 0.72;
    }}
    .meta-triage-icon {{
      font-size: 14px;
      line-height: 1;
      color: rgba(214, 241, 255, 0.9);
    }}
    .meta-weather-icon,
    .meta-weather-temp {{
      font-size: 13px;
      line-height: 1;
      color: #d5e9ff;
    }}
    .meta-dashboard {{
      appearance: none;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 0;
      border: none;
      background: transparent;
      color: var(--ink);
      font: inherit;
      cursor: pointer;
    }}
    .meta-dashboard[disabled] {{
      cursor: default;
      opacity: 0.72;
    }}
    .meta-dashboard-icon {{
      font-size: 14px;
      line-height: 1;
      color: rgba(214, 241, 255, 0.9);
    }}
    .meta-dashboard-count {{
      min-width: 22px;
      min-height: 22px;
      padding: 0 7px;
      display: inline-grid;
      place-items: center;
      border-radius: 999px;
      border: 1px solid rgba(211, 241, 255, 0.18);
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.06), rgba(8, 18, 32, 0.16));
      color: rgba(227, 244, 255, 0.92);
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.08em;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
      backdrop-filter: blur(16px) saturate(145%);
    }}
    .meta-chip,
    .signal-chip,
    .packet-button,
    .dock-button,
    .ghost-toggle,
    select,
    input,
    textarea,
    button {{
      border-radius: 999px;
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(22, 36, 58, 0.28), rgba(9, 18, 31, 0.16));
      color: var(--ink);
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.06),
        0 10px 24px rgba(0, 0, 0, 0.12);
      backdrop-filter: blur(16px) saturate(145%);
    }}
    .meta-chip,
    .signal-chip {{
      padding: 6px 12px;
      white-space: nowrap;
    }}
    #meta-time,
    #open-settings,
    #mode-toggle,
    .signal-rail-toggle,
    .packet-strip-toggle,
    .packet-button {{
      border: none;
      border-radius: 0;
      background: transparent;
      box-shadow: none;
    }}
    .meta-chip.hidden {{
      display: none;
    }}
    .meta-chip.warn {{
      color: var(--warn);
      border-color: rgba(255, 204, 112, 0.4);
      background: rgba(48, 34, 10, 0.46);
    }}
    .meta-chip.alert {{
      color: var(--alert);
      border-color: rgba(255, 123, 123, 0.42);
      background: rgba(54, 16, 16, 0.5);
    }}
    .freshness-banner {{
      margin-bottom: 12px;
      padding: 10px 12px;
      border-radius: 14px;
      border: 1px solid rgba(255, 204, 112, 0.24);
      background: rgba(48, 34, 10, 0.34);
      color: rgba(255, 236, 198, 0.92);
      font-size: 13px;
      line-height: 1.45;
    }}
    .freshness-banner strong {{
      color: var(--warn);
    }}
    .viewport {{
      position: relative;
      display: grid;
      grid-template-columns: minmax(900px, 1180px);
      grid-template-areas:
        "core"
        "chat"
        "scene";
      align-items: start;
      justify-content: center;
      gap: 24px;
      min-height: 0;
      overflow: visible;
    }}
    .layout-editable-panel {{
      position: relative;
    }}
    .core-cluster {{
      grid-area: core;
      position: relative;
      display: grid;
      justify-items: center;
      align-content: start;
      gap: 20px;
      width: min(100%, 1120px);
      place-self: center;
      z-index: 1;
    }}
    body[data-shell-layout="quiet-home"]:not([data-work-focus="true"]):not([data-layout-edit="true"]) .core-cluster {{
      gap: 26px;
    }}
    .layout-editable-panel.floating {{
      position: fixed !important;
      z-index: 22;
      margin: 0;
      justify-self: auto;
      align-self: auto;
    }}
    body[data-layout-edit="true"] .layout-editable-panel {{
      outline: 1px dashed rgba(111, 229, 255, 0.2);
      outline-offset: 4px;
    }}
    .layout-panel-handle {{
      display: none;
      position: absolute;
      top: 10px;
      left: 10px;
      z-index: 3;
      padding: 5px 10px;
      border-radius: 999px;
      border: 1px solid rgba(111, 229, 255, 0.2);
      background: rgba(5, 14, 24, 0.82);
      color: rgba(214, 232, 255, 0.82);
      font-size: 11px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      user-select: none;
      cursor: grab;
    }}
    body[data-layout-edit="true"] .layout-panel-handle {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .layout-resize-handle {{
      display: none;
      position: absolute;
      right: 10px;
      bottom: 10px;
      width: 18px;
      height: 18px;
      z-index: 4;
      border-right: 2px solid rgba(111, 229, 255, 0.56);
      border-bottom: 2px solid rgba(111, 229, 255, 0.56);
      border-bottom-right-radius: 5px;
      opacity: 0.9;
      cursor: nwse-resize;
      background: linear-gradient(135deg, transparent 48%, rgba(111, 229, 255, 0.12) 48%);
    }}
    body[data-layout-edit="true"] .layout-resize-handle {{
      display: block;
    }}
    body.dragging-layout .layout-panel-handle,
    body.resizing-layout .layout-resize-handle {{
      cursor: grabbing;
    }}
    body[data-core-dock="corner"] .viewport {{
      grid-template-columns: minmax(900px, 1180px);
      grid-template-areas:
        "core"
        "chat"
        "scene";
    }}
    .signal-rail-toggle {{
      display: none;
    }}
    .signal-rail-toggle.hidden {{
      opacity: 0;
      pointer-events: none;
    }}
    .signal-rail-shell {{
      position: static;
      grid-area: status;
      width: auto;
    }}
    body[data-shell-layout="quiet-home"]:not([data-layout-edit="true"]) .signal-rail-shell,
    body[data-shell-layout="quiet-home"]:not([data-layout-edit="true"]) .signal-rail-toggle,
    body[data-shell-layout="quiet-home"]:not([data-layout-edit="true"]) .brain-graph-panel {{
      display: none !important;
    }}
    .signal-rail {{
      position: static;
      display: flex;
      flex-direction: column;
      gap: 10px;
      align-items: stretch;
      max-width: none;
      width: 100%;
      height: 100%;
      transition: opacity 180ms ease, transform 180ms ease;
    }}
    .signal-rail.collapsed {{
      display: none;
      opacity: 0;
      pointer-events: none;
      transform: translateY(10px) scale(0.98);
    }}
    body.modal-open .signal-rail-shell,
    body.modal-open .signal-rail,
    body.modal-open .signal-rail-toggle {{
      display: none;
      opacity: 0;
      pointer-events: none;
    }}
    .signal-chip strong {{
      color: var(--cyan);
      font-weight: 600;
    }}
    .brain-graph-panel {{
      position: static;
      grid-area: brain;
      width: auto;
      display: grid;
      gap: 8px;
      padding: 12px 12px 10px;
      border: 1px solid rgba(111, 229, 255, 0.10);
      background: rgba(6, 16, 28, 0.24);
      backdrop-filter: blur(10px);
      clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%);
      box-shadow: 0 0 24px rgba(0, 0, 0, 0.14);
      opacity: 0.84;
      cursor: pointer;
      transition: border-color 160ms ease, transform 160ms ease, background 160ms ease;
    }}
    body[data-layout-edit="true"] .brain-graph-panel {{
      cursor: default;
    }}
    .brain-graph-panel:hover {{
      border-color: rgba(111, 229, 255, 0.28);
      background: rgba(8, 20, 34, 0.34);
      transform: translateY(-1px);
    }}
    .brain-graph-head {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 10px;
    }}
    body[data-layout-edit="true"] .brain-graph-head {{
      cursor: grab;
      user-select: none;
    }}
    .brain-graph-head strong {{
      color: rgba(227, 244, 255, 0.9);
      font-size: 12px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
    }}
    .brain-graph-head span {{
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}
    .brain-mesh-stage,
    .brain-mesh-modal-stage {{
      position: relative;
      width: 100%;
      overflow: hidden;
      border: 1px solid rgba(111, 229, 255, 0.12);
      background:
        radial-gradient(circle at center, rgba(76, 160, 255, 0.08), transparent 48%),
        linear-gradient(180deg, rgba(5, 12, 22, 0.88), rgba(5, 10, 18, 0.94));
      box-shadow:
        inset 0 0 48px rgba(111, 229, 255, 0.06),
        0 0 32px rgba(0, 0, 0, 0.2);
    }}
    .brain-mesh-stage {{
      aspect-ratio: 1.12;
      border-radius: 18px;
    }}
    .brain-mesh-modal-stage {{
      min-height: 340px;
      border-radius: 22px;
    }}
    .brain-mesh-canvas {{
      width: 100%;
      height: 100%;
      display: block;
    }}
    .brain-mesh-overlay {{
      position: absolute;
      inset: 0;
      pointer-events: none;
      background:
        radial-gradient(circle at center, transparent 0%, transparent 52%, rgba(4, 8, 14, 0.14) 76%, rgba(4, 8, 14, 0.46) 100%),
        linear-gradient(180deg, rgba(111, 229, 255, 0.06), transparent 18%, transparent 82%, rgba(76, 160, 255, 0.08));
      mix-blend-mode: screen;
    }}
    .brain-mesh-caption {{
      position: absolute;
      left: 14px;
      right: 14px;
      bottom: 12px;
      display: flex;
      justify-content: space-between;
      gap: 10px;
      font-size: 10px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: rgba(215, 233, 255, 0.62);
      pointer-events: none;
    }}
    .brain-graph-meta {{
      display: grid;
      gap: 2px;
      color: var(--muted);
      font-size: 10px;
      opacity: 0.74;
    }}
    .brain-graph-meta strong {{
      color: var(--cyan);
      font-weight: 600;
    }}
    .core-stage {{
      position: relative;
      width: min(100%, 760px);
      aspect-ratio: 1;
      display: grid;
      place-items: center;
      transform: none;
      z-index: 1;
      opacity: 0.92;
    }}
    body[data-shell-layout="quiet-home"]:not([data-work-focus="true"]):not([data-layout-edit="true"]) .core-stage {{
      width: min(100%, 700px);
      margin-top: clamp(240px, 34vh, 420px);
      opacity: 0.74;
    }}
    .core-stage.floating {{
      transform: none !important;
      pointer-events: auto !important;
      opacity: 1 !important;
      filter: none !important;
      z-index: 23 !important;
    }}
    .core-stage::before {{
      content: "";
      position: absolute;
      inset: 8%;
      border-radius: 30px;
      border: 1px solid rgba(111, 229, 255, 0.18);
      box-shadow:
        0 0 0 1px rgba(111, 229, 255, 0.04),
        0 0 34px rgba(111, 229, 255, 0.12);
      background: radial-gradient(circle at center, rgba(111, 229, 255, 0.03), transparent 72%);
      pointer-events: none;
      z-index: 0;
    }}
    body[data-core-dock="corner"]:not(.modal-open) .core-cluster {{
      position: fixed;
      top: 92px;
      left: 22px;
      width: min(44vw, 620px);
      z-index: 15;
      filter: drop-shadow(0 18px 32px rgba(0, 0, 0, 0.32));
    }}
    body[data-core-dock="corner"]:not(.modal-open) .core-cluster .core-stage {{
      transform: scale(0.92);
      transform-origin: top left;
      pointer-events: none;
      opacity: 0.94;
    }}
    body[data-core-dock="corner"]:not(.modal-open) .core-home-summary {{
      position: relative;
      left: auto;
      bottom: auto;
      width: 100%;
      margin-top: 8px;
      transform: none;
      z-index: 16;
      pointer-events: auto;
    }}
    body.modal-open .core-cluster {{
      position: fixed;
      top: 18px;
      left: 18px;
      width: min(84vw, 1180px);
      z-index: 24;
    }}
    body.modal-open .core-cluster .core-stage {{
      transform: scale(0.1);
      transform-origin: top left;
      pointer-events: none;
      opacity: 0.96;
    }}
    body.modal-open .core-home-summary {{
      opacity: 0;
      pointer-events: none;
      transform: translateY(8px);
    }}
    .core-backdrop,
    .holo-core-shell,
    .core-label {{
      position: absolute;
      inset: 0;
    }}
    .core-backdrop {{
      {core_backdrop_css}
    }}
    .holo-core-shell {{
      z-index: 1;
      display: grid;
      place-items: center;
      transform: translateY(-10px);
      border-radius: 50%;
      -webkit-mask-image: radial-gradient(circle at center, #000 0 44%, rgba(0, 0, 0, 0.98) 58%, rgba(0, 0, 0, 0.88) 68%, rgba(0, 0, 0, 0.46) 78%, transparent 88%);
      mask-image: radial-gradient(circle at center, #000 0 44%, rgba(0, 0, 0, 0.98) 58%, rgba(0, 0, 0, 0.88) 68%, rgba(0, 0, 0, 0.46) 78%, transparent 88%);
      filter:
        drop-shadow(0 0 18px rgba(111, 229, 255, 0.18))
        drop-shadow(0 0 36px rgba(111, 229, 255, 0.14))
        drop-shadow(0 0 72px rgba(76, 160, 255, 0.16));
    }}
    .holo-core-shell:not(.holo-live) {{
      transform: translateY(0);
    }}
    .holo-core-fallback {{
      position: absolute;
      inset: 7% 7% 11% 7%;
      display: grid;
      place-items: center;
      pointer-events: none;
      opacity: 0.985;
      transition: opacity 220ms ease;
    }}
    .holo-core-shell.holo-live .holo-core-fallback {{
      opacity: 0;
    }}
    .holo-core-fallback-core {{
      position: absolute;
      width: 28%;
      aspect-ratio: 1;
      border-radius: 50%;
      background:
        radial-gradient(circle at center, rgba(238, 252, 255, 0.98) 0%, rgba(172, 241, 255, 0.9) 12%, rgba(104, 214, 255, 0.44) 28%, rgba(56, 168, 255, 0.16) 46%, rgba(8, 18, 30, 0) 68%);
      box-shadow:
        0 0 44px rgba(124, 229, 255, 0.62),
        0 0 110px rgba(72, 170, 255, 0.32);
      animation: breathe calc(4.8s / var(--motion-rate)) ease-in-out infinite;
    }}
    .holo-core-fallback-core::before {{
      content: "";
      position: absolute;
      inset: -14%;
      border-radius: 50%;
      border: 1px solid rgba(133, 234, 255, 0.26);
      box-shadow: inset 0 0 24px rgba(121, 232, 255, 0.1);
    }}
    .holo-core-fallback-ring {{
      position: absolute;
      left: 50%;
      top: 50%;
      width: calc(var(--ring-size) * 1%);
      aspect-ratio: 1;
      transform: translate(-50%, -50%) rotate(0deg);
      border-radius: 50%;
      animation: holoOrbit calc(var(--ring-speed) / var(--motion-rate)) linear infinite;
      opacity: var(--ring-opacity, 0.92);
    }}
    .holo-core-fallback-ring::before {{
      content: "";
      position: absolute;
      inset: 0;
      border-radius: 50%;
      background:
        repeating-conic-gradient(
          from 0deg,
          rgba(136, 236, 255, 0.00) 0deg 10deg,
          rgba(136, 236, 255, 0.55) 10deg 13deg,
          rgba(136, 236, 255, 0.06) 13deg 15deg,
          rgba(136, 236, 255, 0.00) 15deg 22deg
        );
      -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 2px), #000 calc(100% - 1px));
      mask: radial-gradient(farthest-side, transparent calc(100% - 2px), #000 calc(100% - 1px));
      box-shadow:
        inset 0 0 24px rgba(96, 218, 255, 0.10),
        0 0 24px rgba(96, 218, 255, 0.12);
    }}
    .holo-core-fallback-ring::after {{
      content: "";
      position: absolute;
      inset: 2.5%;
      border-radius: 50%;
      background:
        repeating-conic-gradient(
          from 12deg,
          rgba(196, 248, 255, 0.00) 0deg 16deg,
          rgba(196, 248, 255, 0.72) 16deg 17.8deg,
          rgba(126, 226, 255, 0.16) 17.8deg 19deg,
          rgba(196, 248, 255, 0.00) 19deg 28deg
        );
      -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 1px), #000 100%);
      mask: radial-gradient(farthest-side, transparent calc(100% - 1px), #000 100%);
      opacity: 0.9;
    }}
    .holo-core-fallback-ring.reverse {{
      animation-direction: reverse;
    }}
    .holo-core-fallback-ring.tight::before,
    .holo-core-fallback-ring.tight::after {{
      opacity: 1;
      filter: saturate(1.16);
    }}
    .holo-core-fallback-dot {{
      position: absolute;
      left: 50%;
      top: 50%;
      width: 9px;
      height: 9px;
      margin-left: -4.5px;
      margin-top: -4.5px;
      border-radius: 50%;
      background: radial-gradient(circle at center, rgba(230, 250, 255, 0.96) 0%, rgba(118, 232, 255, 0.84) 36%, rgba(78, 180, 255, 0.22) 74%, transparent 100%);
      box-shadow:
        0 0 14px rgba(132, 236, 255, 0.5),
        0 0 28px rgba(74, 172, 255, 0.28);
      transform:
        rotate(calc(var(--dot-angle) * 1deg))
        translateY(calc(var(--dot-radius) * -1%))
        scale(calc(0.8 + (var(--energy) * 0.22)));
      animation: fallbackDotPulse calc(3.4s + (var(--dot-angle) * 0.02s)) ease-in-out infinite;
    }}
    .holo-core-fallback-dust {{
      position: absolute;
      inset: 14%;
      border-radius: 50%;
      background:
        radial-gradient(circle at 50% 50%, rgba(108, 227, 255, 0.08) 0 1px, transparent 1px 100%),
        radial-gradient(circle at 56% 44%, rgba(135, 238, 255, 0.12) 0 1px, transparent 1px 100%),
        radial-gradient(circle at 42% 58%, rgba(98, 205, 255, 0.08) 0 1px, transparent 1px 100%);
      filter: blur(0.2px);
      opacity: calc(0.68 + (var(--energy) * 0.28));
      animation: drift calc(14s / var(--motion-rate)) linear infinite;
    }}
    .holo-core-shell::before,
    .holo-core-shell::after {{
      content: "";
      position: absolute;
      border-radius: 50%;
      pointer-events: none;
      mix-blend-mode: screen;
    }}
    .holo-core-shell::before {{
      inset: 18%;
      background:
        radial-gradient(circle at center, rgba(98, 224, 255, calc(0.08 + (var(--energy) * 0.12))) 0%, rgba(98, 224, 255, 0.04) 28%, rgba(6, 16, 28, 0) 72%);
      filter: blur(14px);
      opacity: 0.94;
      animation: breathe calc(7s / var(--motion-rate)) ease-in-out infinite;
    }}
    .holo-core-shell::after {{
      inset: 24%;
      border: 1px solid rgba(117, 229, 255, 0.18);
      box-shadow:
        inset 0 0 24px rgba(99, 218, 255, 0.09),
        0 0 28px rgba(79, 174, 255, 0.18);
      opacity: calc(0.34 + (var(--energy) * 0.32));
    }}
    .holo-core-canvas {{
      width: 100%;
      height: 100%;
      display: block;
      mix-blend-mode: screen;
    }}
    .holo-core-overlay {{
      {hologram_overlay_css}
    }}
    .holo-core-shell:not(.holo-live) .holo-core-overlay,
    .holo-core-shell:not(.holo-live) .beam-column,
    .holo-core-shell:not(.holo-live) .emitter-disc,
    .holo-core-shell:not(.holo-live) .holo-core-canvas,
    .holo-core-shell:not(.holo-live)::after {{
      opacity: 0;
    }}
    .holo-core-shell:not(.holo-live) .beam-column,
    .holo-core-shell:not(.holo-live) .emitter-disc {{
      display: none;
    }}
    .holo-core-shell:not(.holo-live)::before {{
      inset: 18%;
      opacity: 0.72;
      filter: blur(20px);
    }}
    .beam-column {{
      position: absolute;
      left: 50%;
      transform: translateX(-50%);
      width: 10px;
      bottom: 4%;
      top: 62%;
      border-radius: 999px;
      background: linear-gradient(180deg, rgba(111, 229, 255, 0), rgba(111, 229, 255, calc(0.12 + (var(--energy) * 0.12))) 30%, rgba(111, 229, 255, calc(0.54 + (var(--energy) * 0.28))) 100%);
      box-shadow:
        0 0 18px rgba(111, 229, 255, 0.28),
        0 0 44px rgba(70, 172, 255, 0.18);
      opacity: calc(0.5 + (var(--energy) * 0.42));
    }}
    .beam-column::before,
    .beam-column::after {{
      content: "";
      position: absolute;
      left: 50%;
      transform: translateX(-50%);
      border-radius: 999px;
      background: rgba(127, 232, 255, 0.22);
      filter: blur(1px);
    }}
    .beam-column::before {{
      inset: 0 -7px 0 -7px;
      opacity: 0.44;
    }}
    .beam-column::after {{
      inset: 0 -15px 0 -15px;
      opacity: 0.18;
    }}
    .emitter-disc {{
      display: none;
    }}
    .core-label {{
      text-align: center;
      z-index: 7;
      display: grid;
      place-content: center;
      gap: 10px;
      inset: 36% 31% 34% 31%;
      pointer-events: auto;
      cursor: pointer;
      transition: transform 180ms ease, filter 180ms ease;
    }}
    .core-label:hover {{
      transform: scale(1.02);
      filter: brightness(1.06);
    }}
    .core-label::before {{
      content: "";
      position: absolute;
      inset: 16% 12%;
      border-radius: 50%;
      background: radial-gradient(circle at center, rgba(6, 18, 30, 0.88) 0%, rgba(6, 18, 30, 0.62) 42%, rgba(6, 18, 30, 0.12) 72%, transparent 100%);
      filter: blur(10px);
      z-index: -1;
    }}
    .core-label .name {{
      font-size: clamp(42px, 5.8vw, 74px);
      letter-spacing: 0.22em;
      color: rgba(248, 252, 255, 1);
      font-weight: 500;
      text-transform: uppercase;
      text-shadow:
        0 0 16px rgba(202, 240, 255, 0.3),
        0 0 32px rgba(111, 229, 255, 0.26),
        0 0 64px rgba(76, 160, 255, 0.16);
    }}
    .core-label .mode {{
      font-size: 13px;
      letter-spacing: 0.18em;
      color: var(--cyan);
      text-transform: uppercase;
    }}
    .core-label .hint {{
      font-size: 13px;
      color: var(--muted);
      text-shadow: 0 0 16px rgba(9, 16, 28, 0.8);
    }}
    .core-home-summary {{
      order: -1;
      position: relative;
      z-index: 6;
      width: min(980px, 98%);
      display: grid;
      gap: 10px;
      padding: 18px 22px 16px;
      border: 1px solid rgba(209, 241, 255, 0.14);
      border-radius: 20px;
      background:
        radial-gradient(circle at 16% 0%, rgba(255, 255, 255, 0.12), transparent 24%),
        radial-gradient(circle at 78% 14%, rgba(111, 229, 255, 0.12), transparent 26%),
        linear-gradient(135deg, rgba(255, 255, 255, 0.05), transparent 28%),
        var(--glass-fill-strong);
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.09),
        inset 0 -1px 0 rgba(111, 229, 255, 0.05),
        var(--glass-shadow);
      backdrop-filter: var(--glass-blur);
      clip-path: polygon(0 0, calc(100% - 24px) 0, 100% 24px, 100% 100%, 0 100%);
      transition: opacity 180ms ease, transform 180ms ease;
    }}
    .core-home-summary.floating {{
      position: fixed;
      width: min(360px, calc(100vw - 32px));
      margin-top: 0;
      z-index: 26;
    }}
    .core-home-summary::before {{
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      border-radius: 20px;
      background:
        linear-gradient(90deg, rgba(255, 255, 255, 0.12), transparent 18%),
        linear-gradient(180deg, rgba(255, 255, 255, 0.08), transparent 22%),
        radial-gradient(circle at 84% 12%, rgba(111, 229, 255, 0.16), transparent 18%);
      clip-path: polygon(0 0, calc(100% - 24px) 0, 100% 24px, 100% 100%, 0 100%);
      opacity: 0.68;
    }}
    .core-home-kicker {{
      font-size: 11px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: rgba(173, 227, 243, 0.76);
    }}
    .core-home-head {{
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 10px;
      cursor: grab;
      user-select: none;
    }}
    .core-home-head-copy {{
      display: grid;
      gap: 4px;
      min-width: 0;
      flex: 1 1 auto;
    }}
    .core-home-line {{
      color: rgba(239, 247, 255, 0.96);
      font-size: 19px;
      line-height: 1.42;
      max-width: 54ch;
    }}
    .core-home-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.1fr) minmax(340px, 0.9fr);
      gap: 14px 16px;
      align-items: start;
    }}
    .core-home-grid.route-mobile,
    .core-home-grid.route-family {{
      grid-template-columns: 1fr;
      gap: 10px;
    }}
    .core-home-grid.route-tablet {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    .core-home-grid.route-desktop {{
      grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
      gap: 14px 16px;
    }}
    .core-home-span-two {{
      grid-column: 1 / -1;
    }}
    .core-home-block {{
      display: grid;
      gap: 6px;
      min-width: 0;
    }}
    .core-home-block.quiet {{
      opacity: 0.82;
    }}
    .core-home-label {{
      color: rgba(173, 227, 243, 0.72);
      font-size: 10px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
    }}
    .core-home-list {{
      display: grid;
      gap: 7px;
    }}
    .core-home-item {{
      padding: 9px 12px 9px 13px;
      border-radius: 13px;
      border: 1px solid rgba(211, 241, 255, 0.12);
      border-left: 2px solid rgba(179, 236, 255, 0.24);
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent 42%),
        linear-gradient(180deg, rgba(14, 26, 41, 0.26), rgba(7, 16, 27, 0.1));
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
      color: rgba(220, 238, 248, 0.86);
      font-size: 13px;
      line-height: 1.4;
    }}
    .core-home-item strong {{
      color: #eef8ff;
    }}
    .core-home-item.quiet {{
      border-color: rgba(211, 241, 255, 0.08);
      border-left-color: rgba(179, 236, 255, 0.14);
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.025), transparent 42%),
        linear-gradient(180deg, rgba(10, 20, 33, 0.18), rgba(6, 14, 24, 0.08));
      color: rgba(198, 219, 232, 0.76);
    }}
    .core-home-item.quiet strong {{
      color: rgba(229, 240, 248, 0.88);
    }}
    .core-home-item.approval {{
      border-color: rgba(255, 204, 112, 0.08);
      border-left-color: rgba(255, 204, 112, 0.42);
      background: linear-gradient(180deg, rgba(46, 32, 10, 0.26), rgba(26, 18, 8, 0.1));
    }}
    .core-home-hero {{
      display: grid;
      gap: 10px;
      padding: 14px 15px 13px;
      border-radius: 16px;
      border: 1px solid rgba(111, 229, 255, 0.14);
      background:
        radial-gradient(circle at 88% 0%, rgba(111, 229, 255, 0.14), transparent 22%),
        linear-gradient(180deg, rgba(13, 28, 43, 0.48), rgba(7, 16, 27, 0.16));
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.06),
        0 10px 28px rgba(2, 8, 18, 0.14);
    }}
    .core-home-hero-kicker {{
      color: rgba(173, 227, 243, 0.78);
      font-size: 10px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
    }}
    .core-home-hero-title {{
      color: rgba(244, 250, 255, 0.98);
      font-size: 18px;
      line-height: 1.28;
      font-weight: 600;
      max-width: 34ch;
    }}
    .core-home-hero-body {{
      color: rgba(209, 228, 241, 0.84);
      font-size: 13px;
      line-height: 1.45;
      max-width: 52ch;
    }}
    .core-home-hero-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
    }}
    .core-home-hero-chip {{
      padding: 4px 8px;
      border-radius: 999px;
      border: 1px solid rgba(111, 229, 255, 0.1);
      background: rgba(111, 229, 255, 0.035);
      color: rgba(219, 237, 250, 0.74);
      font-size: 9.5px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      white-space: nowrap;
    }}
    .core-home-hero.family {{
      border-color: rgba(190, 236, 199, 0.14);
      background:
        radial-gradient(circle at 88% 0%, rgba(129, 216, 152, 0.12), transparent 24%),
        linear-gradient(180deg, rgba(12, 28, 22, 0.42), rgba(7, 16, 27, 0.16));
    }}
    .core-home-hero.family .core-home-hero-kicker {{
      color: rgba(194, 234, 203, 0.82);
    }}
    .core-home-hero.mobile .core-home-hero-title {{
      font-size: 17px;
      max-width: 26ch;
    }}
    .core-home-overflow {{
      color: rgba(173, 227, 243, 0.54);
      font-size: 11px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      padding: 2px 2px 0;
    }}
    .core-home-status {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .core-home-footer {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 10px 12px;
      padding-top: 8px;
      border-top: 1px solid rgba(211, 241, 255, 0.08);
    }}
    .core-home-footer .core-home-status {{
      flex: 1 1 420px;
      min-width: 0;
    }}
    .core-home-chip {{
      padding: 4px 9px;
      border-radius: 999px;
      border: 1px solid rgba(111, 229, 255, 0.08);
      background: rgba(111, 229, 255, 0.03);
      color: rgba(214, 232, 255, 0.8);
      font-size: 9.5px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      white-space: nowrap;
    }}
    .core-home-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
      flex: 0 1 auto;
    }}
    .core-home-actions .dock-button {{
      min-height: 32px;
      padding: 7px 10px;
      font-size: 11.5px;
    }}
    #core-home-speak-action {{
      display: none;
    }}
    body[data-interface-route="mobile-remote-briefing"] .core-home-footer,
    body[data-interface-route="mobile-companion"] .core-home-footer {{
      position: fixed;
      left: 50%;
      transform: translateX(-50%);
      bottom: max(10px, calc(env(safe-area-inset-bottom, 0px) + 8px));
      width: min(100vw - 14px, 620px);
      align-items: stretch;
      gap: 8px;
      padding: 10px 10px calc(10px + env(safe-area-inset-bottom, 0px));
      border-radius: 22px;
      border: 1px solid rgba(211, 241, 255, 0.12);
      background:
        radial-gradient(circle at 14% 0%, rgba(255, 255, 255, 0.08), transparent 18%),
        linear-gradient(180deg, rgba(9, 18, 29, 0.82), rgba(5, 12, 20, 0.94));
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.05),
        0 16px 38px rgba(0, 0, 0, 0.26);
      backdrop-filter: blur(18px) saturate(145%);
      z-index: 32;
    }}
    body[data-interface-route="mobile-remote-briefing"] .core-home-footer .core-home-status,
    body[data-interface-route="mobile-companion"] .core-home-footer .core-home-status {{
      flex: 1 1 100%;
    }}
    body[data-interface-route="mobile-remote-briefing"] .core-home-actions,
    body[data-interface-route="mobile-companion"] .core-home-actions {{
      width: 100%;
      justify-content: stretch;
    }}
    body[data-interface-route="mobile-remote-briefing"] .core-home-actions .dock-button,
    body[data-interface-route="mobile-companion"] .core-home-actions .dock-button {{
      flex: 1 1 0;
      justify-content: center;
      min-height: 42px;
      padding: 10px 10px;
      font-size: 11px;
      border-radius: 14px;
    }}
    body[data-interface-route="mobile-remote-briefing"] #core-home-speak-action,
    body[data-interface-route="mobile-companion"] #core-home-speak-action {{
      display: inline-flex;
    }}
    body[data-interface-route="mobile-remote-briefing"] .core-home-summary,
    body[data-interface-route="mobile-companion"] .core-home-summary {{
      padding-bottom: calc(132px + env(safe-area-inset-bottom, 0px));
    }}
    body[data-interface-route="mobile-remote-briefing"] .transcript-rail,
    body[data-interface-route="mobile-companion"] .transcript-rail {{
      margin-bottom: calc(112px + env(safe-area-inset-bottom, 0px));
    }}
    body[data-interface-route="mobile-remote-briefing"][data-mobile-variant="child-safe-remote"] .core-home-hero,
    body[data-interface-route="mobile-companion"][data-mobile-variant="child-safe-remote"] .core-home-hero {{
      border-color: rgba(190, 236, 199, 0.16);
      background:
        radial-gradient(circle at 88% 0%, rgba(129, 216, 152, 0.12), transparent 22%),
        linear-gradient(180deg, rgba(12, 28, 22, 0.42), rgba(7, 16, 27, 0.16));
    }}
    body[data-interface-route="mobile-remote-briefing"][data-mobile-variant="child-safe-remote"] .core-home-hero-kicker,
    body[data-interface-route="mobile-companion"][data-mobile-variant="child-safe-remote"] .core-home-hero-kicker {{
      color: rgba(194, 234, 203, 0.82);
    }}
    body[data-interface-route="family-display"] .core-home-status {{
      justify-content: center;
    }}
    .core-home-empty {{
      color: rgba(173, 227, 243, 0.62);
      font-size: 13px;
      line-height: 1.45;
    }}
    .core-command-trigger {{
      appearance: none;
      border: none;
      background: transparent;
      color: inherit;
      font: inherit;
      padding: 0;
      margin: 0;
      text-align: center;
      width: 100%;
      height: 100%;
      display: grid;
      place-content: center;
      gap: 10px;
      cursor: pointer;
    }}
    .core-command-trigger:focus-visible {{
      outline: 2px solid rgba(111, 229, 255, 0.7);
      outline-offset: 10px;
      border-radius: 24px;
    }}
    .core-command-ring {{
      position: absolute;
      inset: 6% 8% 10%;
      z-index: 5;
      pointer-events: none;
      opacity: 0;
      transform: scale(0.92);
      transition: opacity 220ms ease, transform 220ms ease;
    }}
    .core-command-ring.open {{
      opacity: 1;
      transform: scale(1);
      pointer-events: auto;
    }}
    .core-command-ring-shell {{
      position: absolute;
      inset: 0;
      pointer-events: auto;
    }}
    .core-command-svg {{
      width: 100%;
      height: 100%;
      overflow: visible;
      filter: drop-shadow(0 18px 28px rgba(0, 0, 0, 0.22));
    }}
    .core-radial-item {{
      cursor: pointer;
    }}
    .core-radial-item path {{
      fill: rgba(19, 45, 82, 0.84);
      stroke: rgba(196, 236, 255, 0.58);
      stroke-width: 2.2;
      transition: fill 180ms ease, stroke 180ms ease, filter 180ms ease, opacity 180ms ease;
    }}
    .core-radial-item.branch path {{
      fill:
        rgba(34, 54, 118, 0.86);
    }}
    .core-radial-item.leaf path {{
      fill: rgba(23, 79, 136, 0.9);
      stroke: rgba(164, 223, 255, 0.7);
    }}
    .core-radial-item.active path {{
      fill: rgba(129, 109, 232, 0.92);
      stroke: rgba(236, 233, 255, 0.92);
      filter: drop-shadow(0 0 16px rgba(133, 173, 255, 0.2));
    }}
    .core-radial-item:hover path {{
      fill: rgba(58, 85, 168, 0.96);
      stroke: rgba(236, 246, 255, 0.9);
    }}
    .core-radial-label {{
      fill: rgba(245, 251, 255, 0.96);
      font-size: 21px;
      font-weight: 500;
      text-anchor: middle;
      pointer-events: none;
    }}
    .core-radial-label.small {{
      font-size: 17px;
    }}
    .core-radial-kind {{
      fill: rgba(176, 228, 245, 0.82);
      font-size: 10px;
      letter-spacing: 0.24em;
      text-anchor: middle;
      pointer-events: none;
    }}
    .core-command-path {{
      position: absolute;
      left: 50%;
      top: 3.5%;
      transform: translateX(-50%);
      display: flex;
      gap: 6px;
      align-items: center;
      justify-content: center;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(4, 11, 19, 0.64);
      border: 1px solid rgba(111, 229, 255, 0.12);
      box-shadow: 0 0 26px rgba(0, 0, 0, 0.22);
      backdrop-filter: blur(12px);
      max-width: min(460px, 70vw);
      flex-wrap: wrap;
      pointer-events: none;
      z-index: 8;
    }}
    .core-command-chip {{
      padding: 5px 9px;
      border-radius: 999px;
      border: 1px solid rgba(111, 229, 255, 0.18);
      font-size: 10px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: rgba(210, 239, 247, 0.88);
      background: rgba(8, 18, 32, 0.74);
    }}
    .core-command-meta {{
      position: absolute;
      left: 50%;
      bottom: 10%;
      transform: translateX(-50%);
      padding: 9px 14px;
      border-radius: 999px;
      border: 1px solid rgba(111, 229, 255, 0.14);
      background: rgba(5, 12, 20, 0.66);
      color: rgba(187, 228, 243, 0.84);
      font-size: 11px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      backdrop-filter: blur(12px);
      pointer-events: none;
    }}
    .core-command-ring.open + .core-label {{
      inset: 42% 36% 40% 36%;
      transform: scale(0.82);
      opacity: 0.9;
      z-index: 6;
    }}
    .core-command-ring.open + .core-label::before {{
      inset: 22% 18%;
      filter: blur(8px);
    }}
    .core-command-ring.open + .core-label .core-command-trigger {{
      gap: 4px;
    }}
    .core-command-ring.open + .core-label .name {{
      font-size: clamp(30px, 4.2vw, 56px);
      letter-spacing: 0.18em;
    }}
    .core-command-ring.open ~ .core-home-summary {{
      opacity: 0;
      transform: translateX(-50%) translateY(8px);
      pointer-events: none;
    }}
    body[data-active-scene="true"] .core-home-summary {{
      opacity: 0;
      transform: translateX(-50%) translateY(8px);
      pointer-events: none;
    }}
    .scene-stage {{
      position: relative;
      grid-area: scene;
      display: grid;
      width: min(100%, 1120px);
      min-height: 0;
      justify-self: center;
      margin-top: -34px;
      padding-top: 34px;
      animation: sceneDockIn 260ms ease;
    }}
    .scene-stage::before {{
      content: "";
      position: absolute;
      left: 50%;
      top: -26px;
      width: min(54vw, 520px);
      height: 96px;
      transform: translateX(-50%);
      background:
        radial-gradient(ellipse at center, rgba(111, 229, 255, 0.26) 0%, rgba(111, 229, 255, 0.08) 22%, rgba(111, 229, 255, 0.02) 44%, transparent 72%);
      filter: blur(18px);
      opacity: 0.92;
      pointer-events: none;
    }}
    .scene-stage::after {{
      content: "";
      position: absolute;
      left: 50%;
      top: -4px;
      width: min(44vw, 360px);
      height: 1px;
      transform: translateX(-50%);
      background: linear-gradient(90deg, transparent, rgba(111, 229, 255, 0.54), transparent);
      box-shadow:
        0 0 20px rgba(111, 229, 255, 0.36),
        0 0 34px rgba(76, 160, 255, 0.18);
      pointer-events: none;
    }}
    .scene-stage.hidden {{
      display: none;
    }}
    .scene-shell {{
      position: relative;
      display: grid;
      gap: 18px;
      padding: 20px 22px 22px;
      border: 1px solid rgba(209, 241, 255, 0.12);
      border-radius: 20px;
      background:
        radial-gradient(circle at 12% 0%, rgba(255, 255, 255, 0.14), transparent 18%),
        radial-gradient(circle at 18% 8%, rgba(111, 229, 255, 0.18), transparent 20%),
        radial-gradient(circle at 82% 14%, rgba(133, 173, 255, 0.12), transparent 22%),
        linear-gradient(135deg, rgba(255, 255, 255, 0.04), transparent 22%),
        var(--glass-fill-strong);
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.11),
        inset 0 -1px 0 rgba(111, 229, 255, 0.06),
        0 32px 68px rgba(0, 0, 0, 0.2),
        0 0 0 1px rgba(255, 255, 255, 0.02);
      backdrop-filter: blur(26px) saturate(155%);
      clip-path: polygon(0 0, calc(100% - 28px) 0, 100% 28px, 100% 100%, 0 100%);
      overflow: hidden;
    }}
    .scene-shell::before {{
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background:
        linear-gradient(90deg, rgba(255, 255, 255, 0.14), transparent 18%),
        linear-gradient(180deg, rgba(255, 255, 255, 0.09), transparent 16%),
        linear-gradient(135deg, transparent calc(100% - 34px), rgba(111, 229, 255, 0.26) calc(100% - 34px), rgba(111, 229, 255, 0.08) 100%);
      opacity: 0.72;
    }}
    .scene-shell::after {{
      content: "";
      position: absolute;
      inset: 22px 24px auto 24px;
      height: 1px;
      background: linear-gradient(90deg, rgba(111, 229, 255, 0.42), rgba(111, 229, 255, 0.08), transparent 72%);
      pointer-events: none;
    }}
    body[data-active-scene="true"] .core-stage::after {{
      opacity: calc(0.48 + (var(--energy) * 0.24));
      filter: blur(18px);
    }}
    .scene-shell-head {{
      display: flex;
      justify-content: space-between;
      align-items: start;
      gap: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid rgba(111, 229, 255, 0.04);
      cursor: grab;
      user-select: none;
    }}
    .scene-shell-copy {{
      display: grid;
      gap: 8px;
    }}
    .scene-shell-kicker {{
      color: rgba(173, 227, 243, 0.72);
      font-size: 11px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
    }}
    .scene-shell-title {{
      color: #eef8ff;
      font-size: 30px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      text-shadow: 0 0 24px rgba(111, 229, 255, 0.14);
    }}
    .scene-shell-summary {{
      color: rgba(214, 232, 255, 0.68);
      font-size: 14px;
      line-height: 1.5;
      max-width: 60ch;
    }}
    .scene-shell-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      justify-content: flex-end;
    }}
    .scene-shell-body {{
      display: grid;
      gap: 18px;
    }}
    .design-review-panel {{
      position: absolute;
      left: 50%;
      bottom: 5%;
      transform: translateX(-50%);
      z-index: 4;
      width: min(520px, 84%);
      display: grid;
      gap: 10px;
      padding: 14px 16px;
      border: 1px solid rgba(255, 98, 98, 0.24);
      background: rgba(7, 16, 27, 0.84);
      box-shadow: 0 0 28px rgba(255, 76, 76, 0.1);
      backdrop-filter: blur(14px);
    }}
    .design-review-panel.hidden {{
      display: none;
    }}
    .design-review-panel.collapsed {{
      width: auto;
      min-width: 0;
      padding: 0;
      border: none;
      background: transparent;
      box-shadow: none;
      backdrop-filter: none;
    }}
    .design-review-launcher {{
      display: none;
      align-items: center;
      gap: 10px;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid rgba(111, 229, 255, 0.18);
      background: rgba(6, 16, 28, 0.68);
      color: #d7e9fb;
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      box-shadow:
        0 0 18px rgba(72, 164, 255, 0.14),
        inset 0 0 18px rgba(111, 229, 255, 0.04);
      backdrop-filter: blur(14px);
    }}
    .design-review-panel.collapsed .design-review-launcher {{
      display: inline-flex;
    }}
    .design-review-panel.collapsed .design-review-body {{
      display: none;
    }}
    body.modal-open .design-review-panel,
    body[data-work-focus="true"] .design-review-panel {{
      opacity: 0;
      pointer-events: none;
      transform: translateY(10px);
    }}
    .design-review-launcher strong {{
      color: var(--cyan);
      font-weight: 600;
    }}
    .design-review-launcher .review-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: rgba(111, 229, 255, 0.74);
      box-shadow:
        0 0 12px rgba(111, 229, 255, 0.34),
        0 0 22px rgba(76, 160, 255, 0.22);
    }}
    .design-review-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      color: rgba(255, 227, 227, 0.92);
      font-size: 12px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}
    .design-review-head strong {{
      color: #ff8484;
      font-weight: 600;
    }}
    .design-review-copy {{
      color: #d7e9fb;
      font-size: 13px;
      line-height: 1.55;
      min-height: 2.8em;
    }}
    .design-review-field {{
      width: 100%;
      min-height: 78px;
      padding: 10px 12px;
      border-radius: 8px;
      border: 1px solid rgba(111, 229, 255, 0.16);
      background: rgba(6, 16, 28, 0.92);
      color: var(--ink);
      resize: vertical;
      font: inherit;
      line-height: 1.45;
    }}
    .design-review-saved {{
      color: #9cc8e8;
      font-size: 12px;
      line-height: 1.5;
      min-height: 1.4em;
    }}
    .design-review-actions {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .design-review-actions button.review-danger {{
      background: linear-gradient(135deg, rgba(255, 120, 120, 0.22), rgba(255, 78, 78, 0.18));
      color: #ffd0d0;
      border-color: rgba(255, 116, 116, 0.38);
    }}
    .design-review-actions button[disabled] {{
      opacity: 0.42;
      cursor: default;
    }}
    .transcript-rail {{
      position: relative;
      top: auto;
      grid-area: chat;
      width: min(100%, 980px);
      justify-self: center;
      display: grid;
      grid-template-rows: minmax(0, 1fr) auto;
      gap: 12px;
      height: clamp(320px, 42vh, 520px);
      min-height: 320px;
      max-height: 520px;
      padding: 16px 16px 14px;
      border: 1px solid rgba(211, 241, 255, 0.14);
      border-radius: 28px;
      background:
        radial-gradient(circle at 10% 0%, rgba(255, 255, 255, 0.12), transparent 18%),
        radial-gradient(circle at top left, rgba(111, 229, 255, 0.1), transparent 34%),
        radial-gradient(circle at 86% 16%, rgba(133, 173, 255, 0.08), transparent 22%),
        var(--glass-fill-strong);
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.1),
        inset 0 -1px 0 rgba(111, 229, 255, 0.05),
        0 20px 48px rgba(0, 0, 0, 0.2);
      backdrop-filter: blur(24px) saturate(155%);
      transition: opacity 180ms ease, transform 180ms ease;
      overflow: hidden;
    }}
    body[data-shell-layout="quiet-home"]:not([data-work-focus="true"]):not([data-layout-edit="true"]) .transcript-rail {{
      width: min(860px, 88vw);
      height: clamp(210px, 26vh, 300px);
      min-height: 210px;
      max-height: 300px;
      padding: 12px 12px 10px;
      border-radius: 24px;
      border-color: rgba(211, 241, 255, 0.1);
      background:
        radial-gradient(circle at 10% 0%, rgba(255, 255, 255, 0.08), transparent 18%),
        radial-gradient(circle at top left, rgba(111, 229, 255, 0.06), transparent 30%),
        linear-gradient(180deg, rgba(8, 16, 26, 0.52), rgba(5, 12, 20, 0.68));
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.06),
        0 14px 34px rgba(0, 0, 0, 0.16);
      opacity: 0.94;
    }}
    body[data-work-focus="true"] .transcript-rail {{
      position: fixed;
      left: 50%;
      right: auto;
      top: auto;
      bottom: 18px;
      transform: translateX(-50%);
      width: min(1040px, calc(100vw - 28px));
      max-width: calc(100vw - 28px);
      height: auto;
      min-height: 0;
      max-height: none;
      grid-template-rows: auto;
      padding: 10px 12px 12px;
      border-radius: 24px;
      z-index: 18;
      justify-self: auto;
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.12),
        0 24px 54px rgba(0, 0, 0, 0.24),
        0 0 0 1px rgba(255, 255, 255, 0.02);
    }}
    body.modal-open .chat-window,
    body.modal-open .transcript-empty-state {{
      display: none;
    }}
    body.modal-open .chat-interface {{
      padding: 0;
      border: none;
      background: transparent;
      box-shadow: none;
      backdrop-filter: none;
    }}
    body.modal-open .attachment-tray {{
      display: none;
    }}
    .transcript-rail.floating {{
      position: fixed;
      top: 120px;
      left: calc(100vw - min(760px, calc(100vw - 32px)) - 20px);
      width: min(760px, calc(100vw - 32px));
      max-width: calc(100vw - 32px);
      z-index: 22;
      justify-self: auto;
    }}
    .chat-window {{
      min-height: 0;
      display: grid;
      grid-template-rows: auto auto minmax(0, 1fr);
      gap: 10px;
      padding: 10px 10px 0;
      border: 1px solid rgba(211, 241, 255, 0.1);
      border-radius: 22px;
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent 28%),
        linear-gradient(180deg, rgba(10, 20, 33, 0.24), rgba(7, 16, 27, 0.12));
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
      overflow: hidden;
    }}
    body[data-shell-layout="quiet-home"]:not([data-work-focus="true"]):not([data-layout-edit="true"]) .chat-window {{
      gap: 8px;
      padding: 8px 8px 0;
      border-color: rgba(211, 241, 255, 0.08);
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.025), transparent 24%),
        linear-gradient(180deg, rgba(8, 16, 26, 0.18), rgba(5, 12, 20, 0.14));
    }}
    body[data-work-focus="true"] .chat-window,
    body[data-work-focus="true"] .transcript-empty-state {{
      display: none;
    }}
    .chat-interface {{
      display: grid;
      gap: 10px;
      padding: 12px 10px 8px;
      border: 1px solid rgba(211, 241, 255, 0.12);
      border-radius: 22px;
      background:
        radial-gradient(circle at 8% 0%, rgba(255, 255, 255, 0.06), transparent 18%),
        linear-gradient(180deg, rgba(13, 24, 38, 0.2), rgba(7, 16, 27, 0.56));
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.07),
        0 -18px 28px rgba(2, 6, 14, 0.24);
      backdrop-filter: blur(20px) saturate(150%);
    }}
    body[data-shell-layout="quiet-home"]:not([data-work-focus="true"]):not([data-layout-edit="true"]) .chat-interface {{
      gap: 8px;
      padding: 9px 8px 7px;
      border-color: rgba(211, 241, 255, 0.08);
      border-radius: 18px;
      background:
        radial-gradient(circle at 8% 0%, rgba(255, 255, 255, 0.04), transparent 16%),
        linear-gradient(180deg, rgba(10, 18, 29, 0.12), rgba(5, 12, 20, 0.48));
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.04),
        0 -12px 22px rgba(2, 6, 14, 0.18);
    }}
    body[data-interface-route="mobile-remote-briefing"] .signal-rail-shell,
    body[data-interface-route="mobile-remote-briefing"] .signal-rail-toggle,
    body[data-interface-route="mobile-remote-briefing"] .brain-graph-panel,
    body[data-interface-route="mobile-remote-briefing"] .core-stage,
    body[data-interface-route="mobile-companion"] .signal-rail-shell,
    body[data-interface-route="mobile-companion"] .signal-rail-toggle,
    body[data-interface-route="mobile-companion"] .brain-graph-panel,
    body[data-interface-route="mobile-companion"] .core-stage,
    body[data-interface-route="tablet-chamber"] .core-stage,
    body[data-interface-route="family-display"] .core-stage {{
      display: none;
    }}
    body[data-interface-route="mobile-remote-briefing"] .core-cluster,
    body[data-interface-route="mobile-companion"] .core-cluster {{
      max-width: min(100vw - 14px, 620px);
      gap: 10px;
      padding-inline: 0;
    }}
    body[data-interface-route="mobile-remote-briefing"] .core-home-summary,
    body[data-interface-route="mobile-companion"] .core-home-summary {{
      width: min(100vw - 14px, 620px);
      padding: 14px 14px 12px;
      border-radius: 24px;
    }}
    body[data-interface-route="mobile-remote-briefing"] .core-home-opening,
    body[data-interface-route="mobile-companion"] .core-home-opening {{
      font-size: 17px;
      line-height: 1.35;
      margin-bottom: 8px;
    }}
    body[data-interface-route="mobile-remote-briefing"] .core-home-grid,
    body[data-interface-route="mobile-companion"] .core-home-grid {{
      grid-template-columns: 1fr;
      gap: 8px;
    }}
    body[data-interface-route="mobile-remote-briefing"] .transcript-rail,
    body[data-interface-route="mobile-companion"] .transcript-rail {{
      width: min(100vw - 14px, 620px);
      max-width: calc(100vw - 14px);
      border-radius: 20px;
    }}
    body[data-interface-route="mobile-remote-briefing"] .chat-window,
    body[data-interface-route="mobile-companion"] .chat-window {{
      padding: 8px 8px 0;
      gap: 8px;
    }}
    body[data-interface-route="tablet-chamber"] .core-cluster {{
      max-width: min(100vw - 26px, 860px);
      gap: 14px;
    }}
    body[data-interface-route="tablet-chamber"] .core-home-summary,
    body[data-interface-route="tablet-chamber"] .transcript-rail {{
      width: min(860px, calc(100vw - 26px));
      max-width: calc(100vw - 26px);
    }}
    body[data-interface-route="tablet-chamber"] .core-home-grid {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    body[data-interface-route="desktop-command"] .core-cluster,
    body[data-interface-route="desktop-remote-command"] .core-cluster {{
      max-width: 1240px;
      gap: 18px;
    }}
    body[data-interface-route="desktop-command"] .core-home-summary,
    body[data-interface-route="desktop-remote-command"] .core-home-summary,
    body[data-interface-route="desktop-command"] .transcript-rail,
    body[data-interface-route="desktop-remote-command"] .transcript-rail {{
      width: min(1120px, calc(100vw - 48px));
      max-width: calc(100vw - 48px);
    }}
    body[data-interface-route="desktop-command"] .core-stage,
    body[data-interface-route="desktop-remote-command"] .core-stage {{
      display: grid;
      width: min(1120px, calc(100vw - 48px));
      margin-top: 240px;
      opacity: 0.68;
    }}
    body[data-interface-route="family-display"] .transcript-rail,
    body[data-interface-route="family-display"] .signal-rail-shell,
    body[data-interface-route="family-display"] .signal-rail-toggle,
    body[data-interface-route="family-display"] .packet-strip,
    body[data-interface-route="family-display"] .context-stack,
    body[data-interface-route="family-display"] .controls,
    body[data-interface-route="family-display"] .quick-actions,
    body[data-interface-route="family-display"] .composer-tools {{
      display: none !important;
    }}
    body[data-interface-route="family-display"] .core-cluster {{
      max-width: min(100vw - 40px, 1120px);
      gap: 16px;
    }}
    body[data-interface-route="family-display"] .core-home-summary {{
      width: min(1120px, calc(100vw - 40px));
      padding: 22px 22px 18px;
      border-radius: 28px;
    }}
    body[data-interface-route="family-display"] .core-home-grid {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    body[data-interface-route="family-display"] .core-home-action-row {{
      display: none;
    }}
    body[data-work-focus="true"] .chat-interface {{
      padding: 0;
      border: none;
      background: transparent;
      box-shadow: none;
      backdrop-filter: none;
    }}
    body[data-work-focus="true"] .attachment-tray {{
      display: none;
    }}
    body[data-layout-edit="true"] .chat-window,
    body[data-layout-edit="true"] .chat-interface {{
      border-color: rgba(111, 229, 255, 0.24);
      box-shadow: inset 0 0 0 1px rgba(111, 229, 255, 0.08);
    }}
    body[data-transcript-empty="true"] .transcript-rail {{
      opacity: 0.88;
      transform: translateY(2px);
      height: auto;
      min-height: 260px;
      max-height: none;
    }}
    body[data-transcript-empty="true"] .chat-window {{
      grid-template-rows: auto auto minmax(0, 0fr);
      padding-bottom: 10px;
    }}
    body[data-transcript-empty="true"] .transcript-history {{
      display: none;
    }}
    body[data-transcript-empty="true"] .transcript-copy {{
      text-align: left;
    }}
    .transcript-head {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
      padding: 4px 6px 12px;
      border-bottom: 1px solid rgba(111, 229, 255, 0.08);
      cursor: default;
      user-select: none;
    }}
    body[data-layout-edit="true"] .transcript-head {{
      cursor: grab;
    }}
    body.dragging-layout .transcript-head {{
      cursor: grabbing;
    }}
    .transcript-title {{
      color: #e6f4ff;
      font-size: 17px;
      font-weight: 600;
      letter-spacing: 0.01em;
    }}
    .transcript-copy {{
      color: rgba(214, 232, 255, 0.58);
      font-size: 12px;
      line-height: 1.4;
      text-align: right;
    }}
    .transcript-history {{
      display: block;
      overflow-y: auto;
      padding: 0 6px 6px 2px;
      min-height: 0;
      scrollbar-gutter: stable;
    }}
    .transcript-stack {{
      min-height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
      gap: 12px;
    }}
    .transcript-history::-webkit-scrollbar {{
      width: 6px;
    }}
    .transcript-history::-webkit-scrollbar-thumb {{
      background: rgba(111, 229, 255, 0.22);
      border-radius: 999px;
    }}
    .transcript-row {{
      display: flex;
      width: 100%;
    }}
    .transcript-row.user {{
      justify-content: flex-end;
    }}
    .transcript-row.assistant {{
      justify-content: flex-start;
    }}
    .transcript-bubble {{
      max-width: min(82%, 430px);
      padding: 13px 15px 11px;
      border: 1px solid var(--line-soft);
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent 34%),
        linear-gradient(180deg, rgba(10, 22, 36, 0.38), rgba(7, 18, 30, 0.24));
      color: var(--ink);
      backdrop-filter: blur(18px) saturate(150%);
      border-radius: 20px;
      transition: opacity 180ms ease, border-color 180ms ease, background 180ms ease;
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.06),
        0 10px 24px rgba(0, 0, 0, 0.14);
    }}
    .transcript-bubble.user {{
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent 34%),
        linear-gradient(180deg, rgba(98, 72, 24, 0.34), rgba(53, 37, 14, 0.2));
      border-color: rgba(255, 191, 92, 0.18);
      border-bottom-right-radius: 8px;
    }}
    .transcript-bubble.assistant {{
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent 34%),
        linear-gradient(180deg, rgba(12, 30, 46, 0.34), rgba(7, 18, 30, 0.22));
      border-color: rgba(111, 229, 255, 0.14);
      border-bottom-left-radius: 8px;
    }}
    body[data-transcript-empty="true"] .transcript-bubble {{
      border-color: rgba(111, 229, 255, 0.08);
      background: rgba(6, 16, 28, 0.34);
      opacity: 0.78;
    }}
    .transcript-bubble .speaker {{
      font-size: 11px;
      letter-spacing: 0.04em;
      color: var(--cyan);
      margin-bottom: 7px;
      font-weight: 600;
    }}
    .transcript-bubble.user .speaker {{
      color: var(--amber);
    }}
    .transcript-bubble.assistant .speaker {{
      color: var(--cyan);
    }}
    .transcript-bubble .content {{
      white-space: pre-wrap;
      line-height: 1.52;
    }}
    .transcript-bubble .timestamp {{
      margin-top: 7px;
      font-size: 11px;
      letter-spacing: 0.08em;
      color: rgba(214, 232, 255, 0.48);
    }}
    .transcript-artifact {{
      margin-top: 11px;
      display: grid;
      gap: 8px;
      padding: 12px 13px;
      border-radius: 16px;
      border: 1px solid rgba(111, 229, 255, 0.18);
      background:
        linear-gradient(180deg, rgba(7, 22, 34, 0.92), rgba(5, 16, 27, 0.86));
      box-shadow: inset 0 1px 0 rgba(160, 240, 255, 0.04);
    }}
    .transcript-artifact-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }}
    .transcript-artifact-label {{
      font-size: 10px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--cyan);
      font-weight: 700;
    }}
    .transcript-artifact-kind {{
      font-size: 10px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: rgba(214, 232, 255, 0.54);
    }}
    .transcript-artifact-title {{
      color: #eaf8ff;
      font-size: 13px;
      line-height: 1.45;
      font-weight: 600;
    }}
    .transcript-artifact-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .transcript-artifact-chip {{
      padding: 5px 8px;
      border-radius: 999px;
      border: 1px solid rgba(111, 229, 255, 0.14);
      background: rgba(111, 229, 255, 0.08);
      color: rgba(214, 232, 255, 0.78);
      font-size: 10px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .transcript-artifact-summary {{
      color: rgba(214, 232, 255, 0.72);
      font-size: 12px;
      line-height: 1.5;
    }}
    .transcript-artifact-history {{
      display: grid;
      gap: 8px;
      margin-top: 4px;
      padding-top: 10px;
      border-top: 1px solid rgba(111, 229, 255, 0.12);
    }}
    .transcript-artifact-actions,
    .work-item-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .transcript-artifact-actions {{
      margin-top: 8px;
      padding-top: 10px;
      border-top: 1px solid rgba(111, 229, 255, 0.12);
    }}
    .work-item-action-button,
    .work-item-artifact-open {{
      padding: 7px 10px;
      border-radius: 999px;
      border: 1px solid rgba(111, 229, 255, 0.14);
      background: rgba(9, 20, 31, 0.74);
      color: rgba(222, 239, 255, 0.88);
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      transition: background 160ms ease, border-color 160ms ease, transform 160ms ease;
    }}
    .work-item-action-button[data-variant="primary"] {{
      background: rgba(23, 67, 94, 0.92);
      border-color: rgba(111, 229, 255, 0.28);
      color: #eff8ff;
    }}
    .work-item-action-button[data-variant="danger"] {{
      background: rgba(78, 23, 30, 0.86);
      border-color: rgba(255, 121, 143, 0.22);
      color: #ffd9df;
    }}
    .work-item-action-button:hover,
    .work-item-artifact-open:hover {{
      background: rgba(18, 39, 58, 0.86);
      border-color: rgba(111, 229, 255, 0.24);
      transform: translateY(-1px);
    }}
    .work-item-action-button[disabled],
    .work-item-artifact-open[disabled] {{
      opacity: 0.48;
      cursor: default;
      transform: none;
    }}
    .transcript-artifact-details {{
      border-top: 1px solid rgba(111, 229, 255, 0.12);
      margin-top: 4px;
      padding-top: 10px;
    }}
    .transcript-artifact-details > summary {{
      list-style: none;
      cursor: pointer;
      color: rgba(145, 219, 238, 0.82);
      font-size: 11px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}
    .transcript-artifact-details > summary::-webkit-details-marker {{
      display: none;
    }}
    .transcript-artifact-details[open] > summary {{
      margin-bottom: 10px;
    }}
    .transcript-artifact-history-label,
    .work-history-label {{
      font-size: 10px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: rgba(145, 219, 238, 0.7);
    }}
    .history-timeline {{
      display: grid;
      gap: 8px;
    }}
    .history-step {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px 12px;
      align-items: start;
      padding: 9px 10px;
      border-radius: 14px;
      border: 1px solid rgba(111, 229, 255, 0.1);
      background: rgba(8, 18, 29, 0.58);
    }}
    .history-step-main {{
      min-width: 0;
    }}
    .history-step-top {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px 8px;
      align-items: center;
      margin-bottom: 3px;
    }}
    .history-step-stage {{
      color: #eff8ff;
      font-size: 12px;
      font-weight: 600;
    }}
    .history-step-status {{
      color: rgba(111, 229, 255, 0.82);
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .history-step-summary {{
      color: rgba(214, 232, 255, 0.7);
      font-size: 11px;
      line-height: 1.45;
    }}
    .history-step-time {{
      color: rgba(182, 209, 229, 0.62);
      font-size: 10px;
      white-space: nowrap;
      padding-top: 2px;
    }}
    .transcript-empty-state {{
      padding: 14px 16px;
      border: 1px dashed rgba(111, 229, 255, 0.12);
      border-radius: 16px;
      background: rgba(6, 16, 28, 0.34);
      color: rgba(214, 232, 255, 0.6);
      font-size: 12px;
      line-height: 1.45;
      margin: 0 6px 0 2px;
    }}
    .transcript-status-store {{
      display: none;
    }}
    .chat-composer {{
      display: grid;
      gap: 10px;
      padding: 0;
    }}
    .attachment-tray {{
      display: none;
      gap: 8px;
      align-content: start;
    }}
    .attachment-tray.active {{
      display: grid;
    }}
    .attachment-dropzone {{
      display: grid;
      gap: 6px;
      padding: 12px 14px;
      border: 1px dashed rgba(111, 229, 255, 0.18);
      border-radius: 18px;
      background: rgba(7, 16, 27, 0.56);
      color: rgba(214, 232, 255, 0.74);
      transition: border-color 160ms ease, background 160ms ease, transform 160ms ease;
    }}
    .attachment-dropzone.active {{
      border-color: rgba(111, 229, 255, 0.42);
      background: rgba(10, 24, 38, 0.8);
      transform: translateY(-1px);
    }}
    .attachment-dropzone strong {{
      color: #e6f4ff;
      font-size: 13px;
    }}
    .attachment-dropzone span {{
      font-size: 12px;
      line-height: 1.45;
    }}
    .attachment-list {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .attachment-chip {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      align-items: start;
      min-width: 0;
      padding: 10px 12px;
      border-radius: 16px;
      border: 1px solid rgba(111, 229, 255, 0.14);
      background: rgba(7, 16, 27, 0.72);
    }}
    .attachment-chip strong {{
      display: block;
      color: #e6f4ff;
      font-size: 12px;
      line-height: 1.35;
      word-break: break-word;
    }}
    .attachment-chip span {{
      display: block;
      margin-top: 3px;
      color: rgba(214, 232, 255, 0.56);
      font-size: 11px;
      line-height: 1.35;
    }}
    .attachment-chip button {{
      padding: 6px 8px;
      min-height: 32px;
      font-size: 11px;
    }}
    .packet-strip {{
      position: static;
      grid-area: packets;
      z-index: 1;
      display: flex;
      flex-direction: column;
      gap: 12px;
      align-items: stretch;
      width: 100%;
      transition: opacity 180ms ease, transform 180ms ease;
    }}
    .packet-tree {{
      position: relative;
      display: grid;
      gap: 12px;
      padding: 16px 16px 18px;
      border: 1px solid rgba(111, 229, 255, 0.14);
      border-radius: 22px;
      background:
        radial-gradient(circle at top right, rgba(112, 232, 255, 0.08), transparent 36%),
        linear-gradient(180deg, rgba(8, 17, 28, 0.96), rgba(5, 12, 20, 0.94));
      box-shadow:
        inset 0 1px 0 rgba(160, 240, 255, 0.05),
        0 20px 44px rgba(0, 0, 0, 0.34);
      backdrop-filter: blur(16px);
      overflow: hidden;
    }}
    .packet-tree::before {{
      content: "";
      position: absolute;
      inset: 14px 14px auto;
      height: 1px;
      background: linear-gradient(90deg, rgba(111, 229, 255, 0), rgba(111, 229, 255, 0.34), rgba(111, 229, 255, 0));
    }}
    .packet-tree-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid rgba(111, 229, 255, 0.1);
    }}
    .packet-tree-title {{
      font-size: 11px;
      letter-spacing: 0.26em;
      text-transform: uppercase;
      color: var(--cyan);
    }}
    .packet-tree-copy {{
      margin-top: 4px;
      font-size: 12px;
      line-height: 1.5;
      color: var(--muted);
    }}
    .packet-tree-root {{
      position: relative;
      display: grid;
      gap: 10px;
      padding-left: 20px;
    }}
    .packet-tree-root::before {{
      content: "";
      position: absolute;
      left: 5px;
      top: 18px;
      bottom: 8px;
      width: 1px;
      background: linear-gradient(180deg, rgba(111, 229, 255, 0.16), rgba(111, 229, 255, 0.42), rgba(111, 229, 255, 0.08));
    }}
    .packet-tree-level-label {{
      font-size: 10px;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      color: rgba(173, 220, 232, 0.74);
    }}
    .packet-tree-branch {{
      position: relative;
      display: grid;
      gap: 10px;
    }}
    .packet-tree-branch.depth-0 {{
      margin-left: 0;
    }}
    .packet-tree-branch.depth-1,
    .packet-tree-branch.depth-2,
    .packet-tree-branch.depth-3,
    .packet-tree-branch.depth-4 {{
      margin-left: 18px;
      padding-left: 18px;
    }}
    .packet-tree-branch.depth-1::before,
    .packet-tree-branch.depth-2::before,
    .packet-tree-branch.depth-3::before,
    .packet-tree-branch.depth-4::before {{
      content: "";
      position: absolute;
      left: 4px;
      top: -8px;
      bottom: 10px;
      width: 1px;
      background: linear-gradient(180deg, rgba(111, 229, 255, 0.1), rgba(111, 229, 255, 0.3), rgba(111, 229, 255, 0.06));
    }}
    .packet-tree-node-wrap {{
      position: relative;
      display: grid;
      gap: 10px;
    }}
    .packet-tree-node-wrap.depth-1::before,
    .packet-tree-node-wrap.depth-2::before,
    .packet-tree-node-wrap.depth-3::before,
    .packet-tree-node-wrap.depth-4::before {{
      content: "";
      position: absolute;
      left: -14px;
      top: 26px;
      width: 14px;
      height: 1px;
      background: rgba(111, 229, 255, 0.24);
    }}
    .packet-tree-node-wrap.active-path::before {{
      background: rgba(111, 229, 255, 0.62);
      box-shadow: 0 0 10px rgba(111, 229, 255, 0.12);
    }}
    .packet-tree-node {{
      position: relative;
      width: 100%;
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 12px;
      align-items: center;
      padding: 11px 13px;
      border-radius: 14px;
      border: 1px solid rgba(111, 229, 255, 0.14);
      background: linear-gradient(180deg, rgba(9, 18, 29, 0.86), rgba(8, 16, 26, 0.78));
      text-align: left;
      overflow: hidden;
    }}
    .packet-tree-node::before {{
      content: "";
      position: absolute;
      left: -18px;
      top: 50%;
      width: 16px;
      height: 1px;
      background: rgba(111, 229, 255, 0.2);
      transform: translateY(-50%);
    }}
    .packet-tree-node:hover {{
      border-color: rgba(111, 229, 255, 0.34);
      background: linear-gradient(180deg, rgba(12, 24, 38, 0.94), rgba(9, 20, 32, 0.9));
    }}
    .packet-tree-node.active {{
      border-color: rgba(111, 229, 255, 0.52);
      background:
        linear-gradient(90deg, rgba(111, 229, 255, 0.08), transparent 26%),
        linear-gradient(180deg, rgba(14, 30, 46, 0.96), rgba(10, 22, 35, 0.92));
      box-shadow:
        inset 0 0 0 1px rgba(111, 229, 255, 0.16),
        0 0 0 1px rgba(111, 229, 255, 0.04),
        0 14px 24px rgba(0, 0, 0, 0.18);
    }}
    .packet-tree-node.leaf {{
      border-color: rgba(76, 160, 255, 0.18);
      background: linear-gradient(180deg, rgba(8, 21, 34, 0.94), rgba(8, 17, 28, 0.94));
    }}
    .packet-tree-node.leaf.active {{
      border-color: rgba(76, 160, 255, 0.52);
      background:
        linear-gradient(90deg, rgba(84, 170, 255, 0.12), transparent 30%),
        linear-gradient(135deg, rgba(13, 34, 54, 0.98), rgba(8, 20, 33, 0.98));
      box-shadow:
        inset 0 0 0 1px rgba(106, 188, 255, 0.16),
        0 0 26px rgba(63, 143, 255, 0.12);
    }}
    .packet-tree-node-sigil {{
      width: 11px;
      height: 11px;
      border-radius: 999px;
      border: 1px solid rgba(111, 229, 255, 0.46);
      background: rgba(11, 25, 38, 0.96);
      box-shadow: 0 0 0 3px rgba(111, 229, 255, 0.05);
      transition: transform 180ms ease, box-shadow 180ms ease, background 180ms ease;
    }}
    .packet-tree-node.branch .packet-tree-node-sigil {{
      background:
        radial-gradient(circle at 50% 50%, rgba(111, 229, 255, 0.36), rgba(111, 229, 255, 0.12) 55%, rgba(7, 20, 31, 0.96) 56%);
    }}
    .packet-tree-node.leaf .packet-tree-node-sigil {{
      border-color: rgba(88, 172, 255, 0.52);
      background:
        radial-gradient(circle at 50% 50%, rgba(88, 172, 255, 0.5), rgba(88, 172, 255, 0.16) 52%, rgba(7, 19, 31, 0.98) 54%);
    }}
    .packet-tree-node.active .packet-tree-node-sigil {{
      transform: scale(1.08);
      box-shadow: 0 0 0 4px rgba(111, 229, 255, 0.08), 0 0 16px rgba(111, 229, 255, 0.16);
    }}
    .packet-tree-children {{
      position: relative;
      display: grid;
      gap: 10px;
      padding-left: 18px;
      margin-left: 10px;
    }}
    .packet-tree-children::before {{
      content: "";
      position: absolute;
      left: 3px;
      top: -4px;
      bottom: 8px;
      width: 1px;
      background: linear-gradient(180deg, rgba(111, 229, 255, 0.2), rgba(111, 229, 255, 0.56), rgba(111, 229, 255, 0.08));
      box-shadow: 0 0 12px rgba(111, 229, 255, 0.08);
    }}
    .packet-tree-node-label {{
      display: grid;
      gap: 4px;
    }}
    .packet-tree-node-title {{
      font-size: 13px;
      color: var(--ink);
    }}
    .packet-tree-node-copy {{
      font-size: 11px;
      line-height: 1.45;
      color: rgba(174, 205, 218, 0.8);
    }}
    .packet-tree-node-kind {{
      font-size: 10px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: rgba(121, 199, 219, 0.72);
    }}
    .packet-tree-node-caret {{
      font-size: 14px;
      color: var(--cyan);
      opacity: 0.9;
    }}
    .packet-strip.collapsed {{
      display: none;
      opacity: 0;
      pointer-events: none;
      transform: translateY(10px) scale(0.98);
    }}
    .packet-strip-toggle {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }}
    body.modal-open .packet-strip,
    body.modal-open .packet-strip-toggle {{
      display: none;
      opacity: 0;
      pointer-events: none;
      transform: translateY(10px) scale(0.98);
    }}
    .packet-strip-toggle {{
      position: fixed;
      right: 22px;
      bottom: 170px;
      z-index: 4;
      min-width: 132px;
      border: none;
      background: transparent;
      color: var(--cyan);
      box-shadow: none;
    }}
    .packet-strip-toggle.hidden {{
      opacity: 0;
      pointer-events: none;
    }}
    .packet-button,
    .dock-button,
    .ghost-toggle,
    button {{
      appearance: none;
      cursor: pointer;
      padding: 10px 16px;
      color: var(--ink);
      transition: border-color 140ms ease, transform 140ms ease, background 140ms ease;
    }}
    .packet-button:hover,
    .dock-button:hover,
    .ghost-toggle:hover,
    button:hover {{
      border-color: rgba(111, 229, 255, 0.45);
      background: rgba(14, 30, 48, 0.8);
      transform: translateY(-1px);
    }}
    .meta-weather,
    .meta-dashboard,
    .meta-weather:hover,
    .meta-dashboard:hover {{
      padding: 0;
      min-width: auto;
      min-height: auto;
      border: none;
      background: transparent;
      box-shadow: none;
      transform: none;
    }}
    #meta-time:hover,
    #open-settings:hover,
    #mode-toggle:hover,
    .signal-rail-toggle:hover,
    .packet-strip-toggle:hover,
    .packet-button:hover {{
      border-color: transparent;
      background: transparent;
      box-shadow: none;
    }}
    .packet-button.active {{
      color: var(--cyan);
      border-color: transparent;
      box-shadow: none;
    }}
    .dock {{
      align-items: end;
      grid-template-columns: 1fr;
    }}
    body[data-work-focus="true"] .shell {{
      padding-bottom: 138px;
    }}
    .input-cluster {{
      display: grid;
      grid-template-columns: auto minmax(0, 1fr);
      grid-template-areas:
        "context composer"
        "actions actions";
      gap: 10px;
      align-items: end;
      width: 100%;
      justify-self: stretch;
    }}
    .input-cluster > .dock-icon-button {{
      grid-area: context;
    }}
    .composer-shell {{
      grid-area: composer;
      display: grid;
      gap: 8px;
      padding: 12px 14px 10px;
      border-radius: 22px;
      border: 1px solid rgba(111, 229, 255, 0.22);
      background:
        radial-gradient(circle at top left, rgba(111, 229, 255, 0.1), transparent 32%),
        linear-gradient(180deg, rgba(8, 17, 28, 0.98), rgba(5, 12, 20, 0.96));
      box-shadow:
        inset 0 1px 0 rgba(160, 240, 255, 0.06),
        0 20px 44px rgba(0, 0, 0, 0.28);
    }}
    .composer-hint {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      color: rgba(214, 232, 255, 0.5);
      font-size: 10px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    .composer-actions {{
      grid-area: actions;
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .context-action-dock {{
      grid-area: actions;
      display: none;
      justify-content: flex-start;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 2px;
    }}
    .context-action-dock.visible {{
      display: flex;
    }}
    .context-action-chip {{
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid rgba(211, 241, 255, 0.14);
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.06), rgba(8, 18, 32, 0.16));
      color: rgba(229, 244, 255, 0.9);
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.08),
        0 10px 20px rgba(0, 0, 0, 0.12);
      backdrop-filter: blur(16px) saturate(145%);
    }}
    .context-action-chip.primary {{
      border-color: rgba(111, 229, 255, 0.24);
      color: var(--cyan);
    }}
    .dock-select,
    .dock-input {{
      min-height: 48px;
      padding: 0 16px;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: rgba(7, 16, 27, 0.78);
      color: var(--ink);
      outline: none;
    }}
    .dock-input {{
      width: 100%;
      min-height: 64px;
      max-height: 180px;
      padding: 13px 15px;
      border-radius: 18px;
      border-color: rgba(111, 229, 255, 0.24);
      resize: none;
      line-height: 1.5;
      font: inherit;
    }}
    .dock-input::placeholder {{
      color: rgba(214, 232, 255, 0.58);
    }}
    .dock-input:focus {{
      border-color: rgba(111, 229, 255, 0.42);
      box-shadow: 0 0 0 1px rgba(111, 229, 255, 0.18), 0 0 24px rgba(111, 229, 255, 0.08);
    }}
    .dock-button.primary {{
      background: linear-gradient(135deg, rgba(111, 229, 255, 0.18), rgba(76, 160, 255, 0.18));
      color: var(--cyan);
      box-shadow: 0 0 22px rgba(111, 229, 255, 0.16);
    }}
    .dock-button[disabled],
    .dock-icon-button[disabled] {{
      opacity: 0.55;
      cursor: default;
    }}
    .ghost-toggle {{
      padding: 10px 14px;
      color: var(--muted);
    }}
    .meta-icon-button {{
      min-width: 44px;
      min-height: 44px;
      padding: 0;
      display: inline-grid;
      place-items: center;
      border-radius: 0;
      border: none;
      background: transparent;
      color: var(--cyan);
      font-size: 18px;
      line-height: 1;
    }}
    .dock-icon-button {{
      min-width: 48px;
      min-height: 48px;
      padding: 0;
      display: inline-grid;
      place-items: center;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: rgba(7, 16, 27, 0.78);
      color: var(--cyan);
      font-size: 18px;
      line-height: 1;
      box-shadow: inset 0 0 18px rgba(111, 229, 255, 0.06);
    }}
    .mode-panel {{
      position: fixed;
      top: 82px;
      right: 120px;
      z-index: 30;
      width: min(320px, calc(100vw - 32px));
      padding: 16px;
      border: 1px solid rgba(111, 229, 255, 0.24);
      background: rgba(6, 16, 28, 0.94);
      box-shadow: var(--shadow);
      display: none;
      gap: 12px;
      clip-path: polygon(0 0, calc(100% - 20px) 0, 100% 20px, 100% 100%, 0 100%);
      backdrop-filter: blur(18px);
    }}
    .mode-panel.floating,
    .context-panel.floating,
    .core-home-summary.floating {{
      right: auto;
      bottom: auto;
    }}
    .window-controls {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      flex: 0 0 auto;
    }}
    .window-control {{
      width: 12px;
      height: 12px;
      padding: 0;
      border: none;
      border-radius: 50%;
      box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.24), 0 0 0 1px rgba(0, 0, 0, 0.18);
      cursor: pointer;
    }}
    .window-control.close {{
      background: #ff5f57;
    }}
    .window-control.minimize {{
      background: #febc2e;
    }}
    .window-control.maximize {{
      background: #28c840;
    }}
    .window-head-main {{
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
      flex: 1 1 auto;
    }}
    .context-panel {{
      position: fixed;
      right: 22px;
      bottom: 96px;
      z-index: 30;
      width: min(300px, calc(100vw - 32px));
      padding: 16px;
      border: 1px solid rgba(111, 229, 255, 0.24);
      background: rgba(6, 16, 28, 0.94);
      box-shadow: var(--shadow);
      display: none;
      gap: 12px;
      clip-path: polygon(0 0, calc(100% - 20px) 0, 100% 20px, 100% 100%, 0 100%);
      backdrop-filter: blur(18px);
    }}
    .context-panel.open {{
      display: grid;
    }}
    .context-panel-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      cursor: grab;
      user-select: none;
    }}
    .context-panel-title {{
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--cyan);
    }}
    .context-panel-copy {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }}
    .context-panel label {{
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .context-panel-actions {{
      display: flex;
      justify-content: flex-end;
      gap: 10px;
    }}
    .mode-panel.open {{
      display: grid;
    }}
    .mode-panel-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      cursor: grab;
      user-select: none;
    }}
    .mode-panel-title {{
      font-size: 12px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--cyan);
    }}
    .mode-panel-current {{
      color: var(--ink);
      font-size: 14px;
      line-height: 1.5;
    }}
    .mode-panel label {{
      display: grid;
      gap: 8px;
      color: var(--muted);
      font-size: 13px;
    }}
    .mode-panel select,
    .mode-panel input {{
      min-height: 44px;
      padding: 0 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(7, 16, 27, 0.84);
      color: var(--ink);
      outline: none;
    }}
    .mode-panel-actions {{
      display: flex;
      gap: 10px;
      justify-content: flex-end;
    }}
    .mode-panel-status {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }}
    .modal-layer {{
      position: fixed;
      inset: 0;
      background: rgba(1, 5, 10, 0.6);
      display: none;
      place-items: center;
      padding: 28px;
      z-index: 20;
      backdrop-filter: blur(18px);
    }}
    .modal-layer.open {{ display: grid; }}
    body.modal-open .scene-stage {{
      opacity: 0.16;
      transform: translateY(12px) scale(0.985);
      filter: blur(12px);
      pointer-events: none;
    }}
    .modal-layer.layout-free {{
      place-items: start;
    }}
    .modal {{
      width: min(920px, 92vw);
      max-height: 86vh;
      overflow: auto;
      background: linear-gradient(180deg, rgba(6, 16, 28, 0.98), rgba(8, 22, 36, 0.94));
      border: 1px solid rgba(111, 229, 255, 0.24);
      box-shadow: var(--shadow);
      padding: 24px 24px 28px;
      clip-path: polygon(0 0, calc(100% - 28px) 0, 100% 28px, 100% 100%, 0 100%);
    }}
    .modal.floating {{
      position: fixed;
      margin: 0;
      inset: auto;
      z-index: 30;
    }}
    .modal-resize-handle {{
      z-index: 31;
    }}
    body[data-layout-edit="true"] .modal-head {{
      cursor: grab;
      user-select: none;
    }}
    body.dragging-layout .modal-head {{
      cursor: grabbing;
    }}
    body.dragging-layout .mode-panel-head,
    body.dragging-layout .context-panel-head {{
      cursor: grabbing;
    }}
    .modal.workspace-modal {{
      width: min(1440px, 96vw);
      max-height: 92vh;
      padding-bottom: 22px;
    }}
    .modal.brains-modal {{
      width: min(1380px, 96vw);
      max-height: 92vh;
      padding-bottom: 22px;
    }}
    .modal.storm-modal {{
      width: min(1560px, 98vw);
      max-height: 94vh;
      padding-bottom: 22px;
    }}
    .modal.model-forge-modal {{
      width: min(1720px, 98vw);
      max-height: 94vh;
      padding-bottom: 22px;
    }}
    .modal-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 18px;
      cursor: grab;
      user-select: none;
    }}
    .modal-head h2 {{
      margin: 0;
      font-size: 24px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #e8f5ff;
    }}
    .mode-panel.minimized > :not(.mode-panel-head),
    .context-panel.minimized > :not(.context-panel-head),
    .core-home-summary.minimized > :not(.core-home-head),
    .scene-shell.minimized > :not(.scene-shell-head),
    .modal.minimized > :not(.modal-head) {{
      display: none;
    }}
    .mode-panel.minimized,
    .context-panel.minimized,
    .core-home-summary.minimized,
    .scene-shell.minimized {{
      width: min(320px, calc(100vw - 32px));
    }}
    .modal.minimized {{
      width: min(360px, calc(100vw - 32px));
      max-height: none;
      padding-bottom: 18px;
    }}
    .mode-panel.maximized,
    .context-panel.maximized,
    .core-home-summary.maximized,
    .scene-shell.maximized {{
      left: 12px !important;
      top: 12px !important;
      right: 12px !important;
      bottom: auto !important;
      width: calc(100vw - 24px) !important;
      max-width: none;
      min-height: calc(100vh - 24px);
      max-height: calc(100vh - 24px);
    }}
    .scene-shell.floating {{
      position: fixed;
      width: min(100%, 820px);
      z-index: 72;
    }}
    .core-home-summary.hidden-window {{
      display: none;
    }}
    .modal.maximized {{
      position: fixed;
      inset: 12px !important;
      width: auto !important;
      height: auto !important;
      max-height: none;
      margin: 0;
    }}
    .close-button {{
      border-radius: 999px;
      min-width: 42px;
      min-height: 42px;
      padding: 0;
      font-size: 20px;
      line-height: 1;
    }}
    .packet-body {{
      display: grid;
      gap: 18px;
    }}
    .storm-frame {{
      display: block;
      width: 100%;
      height: min(84vh, 920px);
      min-height: 720px;
      border: none;
      border-radius: 22px;
      background: transparent;
    }}
    .packet-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }}
    .packet-block {{
      position: relative;
      border: 1px solid rgba(211, 241, 255, 0.12);
      border-left: 1px solid rgba(211, 241, 255, 0.16);
      padding: 16px 18px 18px;
      background:
        radial-gradient(circle at 10% 0%, rgba(255, 255, 255, 0.08), transparent 18%),
        radial-gradient(circle at 84% 12%, rgba(111, 229, 255, 0.1), transparent 18%),
        linear-gradient(180deg, rgba(13, 27, 43, 0.26), rgba(6, 14, 24, 0.1));
      min-height: 108px;
      border-radius: 18px;
      clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%);
      overflow: hidden;
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.08),
        0 18px 32px rgba(0, 0, 0, 0.14);
      backdrop-filter: blur(18px) saturate(145%);
    }}
    .packet-block::before {{
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background:
        linear-gradient(90deg, rgba(255, 255, 255, 0.12), transparent 16%),
        linear-gradient(180deg, rgba(255, 255, 255, 0.06), transparent 14%);
      opacity: 0.66;
    }}
    .packet-block h3 {{
      margin: 0 0 10px;
      font-size: 12px;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--cyan);
    }}
    .packet-block p,
    .packet-block li {{
      margin: 0;
      color: #d9e7f7;
      line-height: 1.55;
      font-size: 14px;
    }}
    .packet-block ul {{
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 8px;
    }}
    .work-items-grid {{
      display: grid;
      gap: 12px;
    }}
    .work-item-card {{
      display: grid;
      gap: 10px;
      padding: 14px 14px 12px;
      border-radius: 18px;
      border: 1px solid rgba(211, 241, 255, 0.12);
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent 34%),
        linear-gradient(180deg, rgba(10, 22, 36, 0.26), rgba(7, 18, 29, 0.12));
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
      backdrop-filter: blur(18px) saturate(145%);
    }}
    .work-item-head {{
      display: flex;
      justify-content: space-between;
      align-items: start;
      gap: 10px;
    }}
    .work-item-title {{
      color: #eef8ff;
      font-size: 15px;
      font-weight: 600;
      line-height: 1.35;
    }}
    .work-item-stage {{
      color: rgba(111, 229, 255, 0.84);
      font-size: 11px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      white-space: nowrap;
    }}
    .work-item-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .work-item-chip {{
      padding: 4px 9px;
      border-radius: 999px;
      border: 1px solid rgba(111, 229, 255, 0.12);
      background: rgba(9, 19, 30, 0.7);
      color: rgba(221, 238, 255, 0.8);
      font-size: 11px;
      line-height: 1;
    }}
    .work-item-rationale {{
      color: rgba(221, 236, 250, 0.82);
      font-size: 12px;
      line-height: 1.55;
    }}
    .work-item-details {{
      border: 1px solid rgba(211, 241, 255, 0.12);
      border-radius: 18px;
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent 34%),
        linear-gradient(180deg, rgba(10, 22, 36, 0.24), rgba(7, 18, 29, 0.12));
      backdrop-filter: blur(18px) saturate(145%);
      overflow: hidden;
    }}
    .work-item-details > summary {{
      list-style: none;
      cursor: pointer;
      padding: 14px 14px 12px;
    }}
    .work-item-details > summary::-webkit-details-marker {{
      display: none;
    }}
    .work-item-details[open] > summary {{
      border-bottom: 1px solid rgba(111, 229, 255, 0.1);
      background: rgba(8, 20, 31, 0.64);
    }}
    .work-item-expanded {{
      display: grid;
      gap: 12px;
      padding: 14px;
    }}
    .work-item-section {{
      display: grid;
      gap: 8px;
    }}
    .work-item-section-title {{
      font-size: 10px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: rgba(145, 219, 238, 0.7);
    }}
    .work-item-artifacts {{
      display: grid;
      gap: 8px;
    }}
    .work-item-artifact-row {{
      display: grid;
      gap: 4px;
      padding: 9px 10px;
      border-radius: 14px;
      border: 1px solid rgba(111, 229, 255, 0.1);
      background: rgba(8, 18, 29, 0.58);
    }}
    .work-item-artifact-row-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }}
    .work-item-artifact-row strong {{
      color: #eff8ff;
      font-size: 12px;
    }}
    .work-item-artifact-row span {{
      color: rgba(214, 232, 255, 0.68);
      font-size: 11px;
      line-height: 1.45;
    }}
    .lifecycle-toast {{
      position: fixed;
      right: 24px;
      bottom: 28px;
      z-index: 160;
      max-width: min(420px, calc(100vw - 32px));
      padding: 12px 14px;
      border-radius: 16px;
      border: 1px solid rgba(111, 229, 255, 0.18);
      background: linear-gradient(180deg, rgba(8, 19, 31, 0.96), rgba(7, 17, 28, 0.92));
      color: #eaf7ff;
      box-shadow: 0 18px 42px rgba(0, 0, 0, 0.38);
      backdrop-filter: blur(18px);
      display: grid;
      gap: 4px;
      opacity: 0;
      pointer-events: none;
      transform: translateY(10px);
      transition: opacity 180ms ease, transform 180ms ease;
    }}
    .lifecycle-toast.show {{
      opacity: 1;
      transform: translateY(0);
    }}
    .lifecycle-toast strong {{
      font-size: 11px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--cyan);
    }}
    .lifecycle-toast span {{
      font-size: 13px;
      line-height: 1.5;
      color: rgba(230, 241, 250, 0.84);
    }}
    .inspector-grid {{
      display: grid;
      gap: 14px;
    }}
    .inspector-header {{
      display: grid;
      gap: 8px;
    }}
    .inspector-title {{
      margin: 0;
      color: #eff8ff;
      font-size: 1.08rem;
    }}
    .inspector-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .inspector-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding-top: 4px;
    }}
    .inspector-columns {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 14px;
    }}
    .inspector-panel {{
      display: grid;
      gap: 10px;
      padding: 14px;
      border-radius: 18px;
      border: 1px solid rgba(111, 229, 255, 0.12);
      background: rgba(7, 18, 29, 0.58);
    }}
    .inspector-panel h3 {{
      margin: 0;
      font-size: 0.86rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: rgba(145, 219, 238, 0.76);
    }}
    .inspector-kv {{
      display: grid;
      gap: 8px;
    }}
    .inspector-kv-row {{
      display: grid;
      gap: 2px;
    }}
    .inspector-kv-row strong {{
      font-size: 11px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: rgba(181, 214, 235, 0.64);
    }}
    .inspector-kv-row span,
    .inspector-kv-row div {{
      color: #eef8ff;
      line-height: 1.5;
    }}
    .inspector-artifact-list {{
      display: grid;
      gap: 8px;
    }}
    .inspector-artifact-item {{
      display: grid;
      gap: 6px;
      padding: 10px 12px;
      border-radius: 14px;
      border: 1px solid rgba(111, 229, 255, 0.1);
      background: rgba(8, 18, 29, 0.56);
    }}
    .inspector-artifact-item.active {{
      border-color: rgba(111, 229, 255, 0.24);
      background: rgba(14, 29, 43, 0.76);
    }}
    .inspector-artifact-viewer {{
      display: grid;
      gap: 10px;
    }}
    .inspector-artifact-pre {{
      margin: 0;
      padding: 14px;
      border-radius: 16px;
      background: rgba(5, 13, 22, 0.82);
      border: 1px solid rgba(111, 229, 255, 0.08);
      color: #dbecf8;
      overflow: auto;
      max-height: 420px;
      font-size: 12px;
      line-height: 1.55;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .recent-action-trail {{
      display: grid;
      gap: 8px;
    }}
    .recent-action-item {{
      display: grid;
      gap: 4px;
      padding: 10px 12px;
      border-radius: 14px;
      border: 1px solid rgba(111, 229, 255, 0.08);
      background: rgba(8, 18, 29, 0.44);
    }}
    @media (max-width: 980px) {{
      .inspector-columns {{
        grid-template-columns: 1fr;
      }}
    }}
    .stack {{
      display: grid;
      gap: 12px;
    }}
    .line-list {{
      display: grid;
      gap: 10px;
    }}
    .line-item {{
      padding: 12px 0;
      border-top: 1px solid rgba(111, 229, 255, 0.12);
    }}
    .line-item:first-child {{
      border-top: none;
      padding-top: 0;
    }}
    .metric {{
      display: inline-flex;
      gap: 10px;
      align-items: center;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 8px;
    }}
    .connected-device-card {{
      display: block;
      width: 100%;
    }}
    .connected-device-meta {{
      display: block;
      white-space: normal;
      line-height: 1.45;
      overflow-wrap: anywhere;
    }}
    .connected-device-form {{
      grid-template-columns: minmax(0, 1fr);
      width: 100%;
    }}
    .connected-device-form label,
    .connected-device-form input,
    .connected-device-form select,
    .connected-device-form textarea {{
      min-width: 0;
      width: 100%;
      box-sizing: border-box;
    }}
    .metric strong {{
      color: var(--cyan);
      font-weight: 600;
    }}
    .settings-grid {{
      display: grid;
      gap: 14px;
    }}
    .settings-grid label {{
      display: grid;
      gap: 8px;
      color: #d9e7f7;
      font-size: 13px;
      letter-spacing: 0.04em;
    }}
    .inline-actions {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .settings-note {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }}
    .empty {{
      color: var(--muted);
      font-size: 14px;
    }}
    .workspace-shell {{
      display: grid;
      gap: 14px;
    }}
    .workspace-summary {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .workspace-summary .tag {{
      padding: 6px 11px;
      border-radius: 999px;
      border: 1px solid rgba(211, 241, 255, 0.12);
      color: var(--muted);
      font-size: 10px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(8, 18, 32, 0.18));
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
      backdrop-filter: blur(16px) saturate(145%);
    }}
    .workspace-tabs {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .workspace-tab {{
      padding: 10px 14px;
      border: 1px solid var(--line-soft);
      color: var(--muted);
      background: rgba(8, 18, 32, 0.82);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 12px;
    }}
    .workspace-tab.active {{
      color: var(--cyan);
      background: linear-gradient(135deg, rgba(111, 229, 255, 0.18), rgba(76, 160, 255, 0.18));
      box-shadow: 0 0 20px rgba(111, 229, 255, 0.12);
    }}
    .workspace-frame {{
      border: 1px solid rgba(211, 241, 255, 0.14);
      border-radius: 18px;
      background:
        radial-gradient(circle at 10% 0%, rgba(255, 255, 255, 0.1), transparent 18%),
        radial-gradient(circle at 86% 14%, rgba(111, 229, 255, 0.1), transparent 20%),
        linear-gradient(135deg, rgba(255, 255, 255, 0.04), transparent 20%),
        linear-gradient(180deg, rgba(13, 24, 38, 0.3), rgba(5, 12, 22, 0.18));
      min-height: 72vh;
      overflow: hidden;
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.1),
        inset 0 -1px 0 rgba(111, 229, 255, 0.05),
        0 16px 34px rgba(0, 0, 0, 0.16);
      backdrop-filter: blur(22px) saturate(150%);
      clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%);
    }}
    .workspace-frame iframe {{
      width: 100%;
      height: 72vh;
      border: 0;
      background: transparent;
      display: block;
    }}
    .chronicle-workspace-shell {{
      display: grid;
      gap: 14px;
    }}
    .chronicle-handoff-bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      padding: 12px 14px;
      border: 1px solid rgba(211, 241, 255, 0.12);
      border-left: 2px solid rgba(211, 241, 255, 0.18);
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent 34%),
        linear-gradient(180deg, rgba(10, 22, 36, 0.24), rgba(7, 16, 27, 0.12));
      border-radius: 16px;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
      backdrop-filter: blur(18px) saturate(145%);
    }}
    .chronicle-handoff-copy {{
      display: grid;
      gap: 4px;
    }}
    .chronicle-handoff-copy strong {{
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--cyan);
    }}
    .chronicle-handoff-copy span {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }}
    .chronicle-handoff-actions {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .vision-shell {{
      display: grid;
      gap: 14px;
    }}
    .vision-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.25fr) minmax(280px, 0.75fr);
      gap: 14px;
      align-items: start;
    }}
    .vision-stage,
    .vision-preview-card {{
      display: grid;
      gap: 10px;
    }}
    .vision-measure-panel {{
      display: grid;
      gap: 10px;
      padding: 12px;
      border: 1px solid rgba(111, 229, 255, 0.12);
      background: rgba(8, 18, 32, 0.68);
    }}
    .vision-measure-grid {{
      display: grid;
      grid-template-columns: minmax(120px, 0.8fr) minmax(0, 1fr);
      gap: 10px;
      align-items: end;
    }}
    .vision-measure-grid input,
    .vision-measure-grid select {{
      width: 100%;
    }}
    .vision-measure-summary {{
      color: #d7e8fa;
      font-size: 13px;
      line-height: 1.5;
      min-height: 38px;
    }}
    .vision-controls {{
      display: grid;
      gap: 10px;
    }}
    .vision-stage label,
    .vision-preview-card label,
    .vision-controls label {{
      display: grid;
      gap: 6px;
      font-size: 13px;
      color: var(--muted);
    }}
    .vision-feed {{
      position: relative;
      overflow: hidden;
      border: 1px solid rgba(111, 229, 255, 0.16);
      background: rgba(5, 12, 22, 0.92);
      min-height: 320px;
      display: grid;
      place-items: center;
    }}
    .vision-feed video,
    .vision-feed img {{
      width: 100%;
      height: min(62vh, 520px);
      object-fit: cover;
      display: block;
      background: #02060b;
    }}
    .vision-crop-box {{
      position: absolute;
      border: 2px solid rgba(111, 229, 255, 0.9);
      box-shadow: 0 0 0 9999px rgba(2, 8, 15, 0.28);
      pointer-events: none;
      display: none;
    }}
    .vision-crop-box.active {{
      display: block;
    }}
    .model-forge-shell {{
      display: grid;
      gap: 18px;
    }}
    .model-forge-grid {{
      display: grid;
      grid-template-columns: minmax(0, 3fr) minmax(340px, 1fr);
      gap: 20px;
      align-items: start;
    }}
    .model-forge-stage {{
      min-height: 620px;
      border-radius: 24px;
      border: 1px solid rgba(111, 229, 255, 0.18);
      background:
        linear-gradient(180deg, rgba(6, 12, 22, 0.98), rgba(3, 8, 16, 0.98)),
        radial-gradient(circle at 50% 0%, rgba(84, 193, 255, 0.14), transparent 42%),
        radial-gradient(circle at 50% 100%, rgba(58, 124, 255, 0.08), transparent 38%);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02), 0 24px 60px rgba(0, 0, 0, 0.35);
      overflow: hidden;
      position: relative;
      display: grid;
      grid-template-rows: auto 1fr auto;
    }}
    .model-forge-stage::before {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(rgba(125, 221, 255, 0.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(125, 221, 255, 0.06) 1px, transparent 1px);
      background-size: 34px 34px;
      opacity: 0.16;
      mask-image: linear-gradient(180deg, rgba(0,0,0,0.2), rgba(0,0,0,0.9) 34%, rgba(0,0,0,0.94) 74%, rgba(0,0,0,0.18));
      pointer-events: none;
    }}
    .model-forge-stage::after {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        radial-gradient(circle at center, rgba(90, 214, 255, 0.16), transparent 30%),
        radial-gradient(circle at 50% 72%, rgba(70, 155, 255, 0.12), transparent 38%);
      pointer-events: none;
      mix-blend-mode: screen;
    }}
    .model-forge-stage-head {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 20px 0;
      position: relative;
      z-index: 2;
      pointer-events: none;
    }}
    .model-forge-stage-copy {{
      display: grid;
      gap: 8px;
      max-width: 420px;
    }}
    .model-forge-stage-copy h3 {{
      margin: 0;
      font-size: 1.02rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #eff8ff;
    }}
    .model-forge-stage-copy p {{
      margin: 0;
      color: rgba(220, 235, 246, 0.8);
      font-size: 0.92rem;
      line-height: 1.5;
    }}
    .model-forge-stage-badges {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }}
    .model-forge-stage-badges .tag {{
      background: rgba(6, 18, 32, 0.72);
      border-color: rgba(111, 229, 255, 0.14);
    }}
    .model-forge-viewer {{
      width: 100%;
      height: 100%;
      min-height: 520px;
      position: relative;
      z-index: 1;
    }}
    .model-forge-empty {{
      position: absolute;
      inset: 88px 0 68px;
      display: grid;
      place-items: center;
      text-align: center;
      color: var(--muted);
      padding: 28px;
      pointer-events: none;
    }}
    .model-forge-overlay {{
      position: absolute;
      left: 20px;
      bottom: 20px;
      z-index: 3;
      width: min(420px, calc(100% - 40px));
      display: grid;
      gap: 12px;
      padding: 16px 18px;
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(5, 12, 21, 0.88), rgba(6, 14, 24, 0.78));
      border: 1px solid rgba(111, 229, 255, 0.16);
      box-shadow: 0 16px 42px rgba(0, 0, 0, 0.3);
      backdrop-filter: blur(16px);
    }}
    .model-forge-overlay-head {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 14px;
    }}
    .model-forge-overlay-title {{
      display: grid;
      gap: 4px;
      min-width: 0;
    }}
    .model-forge-overlay-title strong {{
      color: #f2f8ff;
      font-size: 1rem;
      font-weight: 600;
    }}
    .model-forge-overlay-title span {{
      color: rgba(205, 226, 241, 0.76);
      font-size: 0.8rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
    }}
    .model-forge-overlay-status {{
      justify-self: end;
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid rgba(111, 229, 255, 0.14);
      background: rgba(13, 32, 54, 0.6);
      color: #d8f1ff;
      font-size: 0.74rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      white-space: nowrap;
    }}
    .model-forge-overlay-copy {{
      color: rgba(215, 232, 244, 0.78);
      font-size: 0.9rem;
      line-height: 1.5;
    }}
    .model-forge-overlay-copy:empty {{
      display: none;
    }}
    .model-forge-overlay-stats {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }}
    .model-forge-overlay-stat {{
      display: grid;
      gap: 4px;
      padding: 10px 12px;
      border-radius: 14px;
      background: rgba(11, 25, 42, 0.58);
      border: 1px solid rgba(111, 229, 255, 0.1);
    }}
    .model-forge-overlay-stat span {{
      font-size: 0.68rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: rgba(184, 215, 234, 0.7);
    }}
    .model-forge-overlay-stat strong {{
      color: #f2f8ff;
      font-size: 0.86rem;
      font-weight: 600;
      word-break: break-word;
    }}
    .model-forge-stage-foot {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 0 20px 18px;
      position: relative;
      z-index: 2;
    }}
    .model-forge-stage-status {{
      color: rgba(220, 235, 246, 0.78);
      font-size: 0.9rem;
      line-height: 1.45;
    }}
    .model-forge-stage-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .model-forge-panel {{
      display: grid;
      gap: 14px;
      align-content: start;
      min-width: 0;
    }}
    .model-forge-tabs {{
      display: inline-flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 6px;
      border-radius: 16px;
      border: 1px solid rgba(111, 229, 255, 0.12);
      background: rgba(6, 14, 24, 0.8);
    }}
    .model-forge-tab {{
      appearance: none;
      border: 1px solid transparent;
      background: transparent;
      color: rgba(194, 219, 235, 0.72);
      font: inherit;
      font-size: 0.8rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      padding: 9px 12px;
      border-radius: 12px;
      cursor: pointer;
      transition: background 140ms ease, color 140ms ease, border-color 140ms ease;
    }}
    .model-forge-tab.active {{
      background: rgba(14, 34, 58, 0.9);
      border-color: rgba(111, 229, 255, 0.16);
      color: #eff8ff;
    }}
    .model-forge-tab-panel {{
      display: none;
      gap: 14px;
    }}
    .model-forge-tab-panel.active {{
      display: grid;
    }}
    .model-forge-panel label {{
      display: grid;
      gap: 8px;
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .model-forge-panel select,
    .model-forge-panel textarea,
    .model-forge-panel input {{
      width: 100%;
    }}
    .model-forge-meta {{
      display: grid;
      gap: 10px;
      padding: 16px 18px;
      border-radius: 18px;
      border: 1px solid rgba(111, 229, 255, 0.14);
      background: rgba(8, 17, 28, 0.88);
    }}
    .model-forge-meta.hero {{
      gap: 14px;
      background:
        linear-gradient(180deg, rgba(10, 22, 38, 0.96), rgba(8, 17, 28, 0.92)),
        radial-gradient(circle at top left, rgba(111, 229, 255, 0.1), transparent 42%);
      border-color: rgba(111, 229, 255, 0.18);
      box-shadow: 0 18px 48px rgba(0, 0, 0, 0.22);
    }}
    .model-forge-meta .metric {{
      display: grid;
      gap: 4px;
    }}
    .model-forge-meta-head {{
      display: grid;
      gap: 6px;
    }}
    .model-forge-meta-head h3 {{
      margin: 0;
      font-size: 1rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #eef8ff;
    }}
    .model-forge-meta-head p {{
      margin: 0;
      color: rgba(220, 235, 246, 0.74);
      font-size: 0.9rem;
      line-height: 1.45;
    }}
    .model-forge-concept-layout {{
      display: grid;
      gap: 14px;
    }}
    .model-forge-silhouette-card {{
      display: grid;
      gap: 12px;
      padding: 14px;
      border-radius: 18px;
      border: 1px solid rgba(111, 229, 255, 0.16);
      background:
        linear-gradient(180deg, rgba(14, 32, 54, 0.9), rgba(8, 17, 29, 0.9)),
        radial-gradient(circle at top left, rgba(111, 229, 255, 0.1), transparent 42%);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
    }}
    .model-forge-silhouette-head {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
    }}
    .model-forge-silhouette-copy {{
      display: grid;
      gap: 4px;
    }}
    .model-forge-silhouette-copy strong {{
      color: #f2f8ff;
      font-size: 0.95rem;
      letter-spacing: 0.02em;
    }}
    .model-forge-silhouette-copy span {{
      color: rgba(194, 219, 235, 0.74);
      font-size: 0.8rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .model-forge-silhouette-badge {{
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid rgba(111, 229, 255, 0.16);
      background: rgba(5, 15, 28, 0.72);
      color: #d8f1ff;
      font-size: 0.72rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      white-space: nowrap;
    }}
    .model-forge-silhouette-stage {{
      position: relative;
      min-height: 132px;
      border-radius: 16px;
      border: 1px solid rgba(111, 229, 255, 0.1);
      background:
        radial-gradient(circle at 50% 50%, rgba(91, 214, 255, 0.12), transparent 34%),
        linear-gradient(180deg, rgba(7, 18, 31, 0.96), rgba(4, 10, 19, 0.96));
      overflow: hidden;
    }}
    .model-forge-silhouette-stage::before {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(rgba(125, 221, 255, 0.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(125, 221, 255, 0.06) 1px, transparent 1px);
      background-size: 24px 24px;
      opacity: 0.2;
      pointer-events: none;
    }}
    .model-forge-silhouette-art {{
      position: absolute;
      inset: 14px 16px 18px;
      background-position: center;
      background-repeat: no-repeat;
      background-size: contain;
      filter: drop-shadow(0 10px 24px rgba(65, 180, 255, 0.22));
    }}
    .model-forge-silhouette-description {{
      color: rgba(221, 236, 250, 0.82);
      font-size: 0.88rem;
      line-height: 1.55;
    }}
    .model-forge-silhouette-metrics {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }}
    .model-forge-silhouette-metric {{
      display: grid;
      gap: 4px;
      padding: 10px 12px;
      border-radius: 14px;
      background: rgba(6, 16, 28, 0.7);
      border: 1px solid rgba(111, 229, 255, 0.08);
    }}
    .model-forge-silhouette-metric span {{
      font-size: 0.68rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: rgba(184, 215, 234, 0.66);
    }}
    .model-forge-silhouette-metric strong {{
      color: #eef8ff;
      font-size: 0.84rem;
      font-weight: 600;
    }}
    .model-forge-variant-strip {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }}
    .model-forge-variant-card {{
      display: grid;
      gap: 8px;
      padding: 12px;
      border-radius: 16px;
      border: 1px solid rgba(111, 229, 255, 0.1);
      background: rgba(7, 18, 30, 0.76);
      cursor: pointer;
      transition: border-color 140ms ease, background 140ms ease, transform 140ms ease;
    }}
    .model-forge-variant-card:hover {{
      border-color: rgba(111, 229, 255, 0.22);
      transform: translateY(-1px);
    }}
    .model-forge-variant-card.active {{
      border-color: rgba(111, 229, 255, 0.26);
      background: linear-gradient(180deg, rgba(12, 30, 52, 0.88), rgba(8, 18, 30, 0.86));
      box-shadow: 0 12px 28px rgba(0, 0, 0, 0.18);
    }}
    .model-forge-variant-card strong {{
      color: #eef8ff;
      font-size: 0.88rem;
      font-weight: 600;
    }}
    .model-forge-variant-meta {{
      color: rgba(190, 218, 236, 0.72);
      font-size: 0.72rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
    }}
    .model-forge-variant-pitch {{
      color: rgba(221, 236, 250, 0.8);
      font-size: 0.84rem;
      line-height: 1.5;
    }}
    .model-forge-variant-foot {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      color: rgba(184, 215, 234, 0.68);
      font-size: 0.74rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    .model-forge-chat-thread {{
      display: grid;
      gap: 12px;
    }}
    .model-forge-chat-bubble {{
      display: grid;
      gap: 8px;
      padding: 12px 14px;
      border-radius: 16px;
      border: 1px solid rgba(111, 229, 255, 0.1);
      background: rgba(7, 18, 30, 0.78);
    }}
    .model-forge-chat-bubble.user {{
      margin-left: 18px;
      border-color: rgba(111, 229, 255, 0.14);
      background: linear-gradient(180deg, rgba(12, 30, 52, 0.88), rgba(8, 18, 30, 0.82));
    }}
    .model-forge-chat-bubble.assistant {{
      margin-right: 18px;
      background: linear-gradient(180deg, rgba(10, 22, 38, 0.94), rgba(8, 16, 28, 0.9));
    }}
    .model-forge-chat-bubble.system {{
      border-style: dashed;
      background: rgba(7, 16, 27, 0.66);
    }}
    .model-forge-chat-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      color: rgba(190, 218, 236, 0.74);
      font-size: 0.72rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}
    .model-forge-chat-head strong {{
      color: #eff8ff;
      font-size: 0.74rem;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}
    .model-forge-chat-bubble p {{
      margin: 0;
      color: #e7f2fb;
      font-size: 0.92rem;
      line-height: 1.58;
      white-space: pre-wrap;
    }}
    .model-forge-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .model-forge-script {{
      max-height: 240px;
      overflow: auto;
      white-space: pre-wrap;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      font-size: 0.84rem;
      line-height: 1.45;
    }}
    @media (max-width: 1180px) {{
      .model-forge-grid {{
        grid-template-columns: 1fr;
      }}
      .model-forge-stage {{
        min-height: 520px;
      }}
      .model-forge-overlay {{
        width: calc(100% - 32px);
        left: 16px;
        bottom: 16px;
      }}
      .model-forge-overlay-stats {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .model-forge-stage-head,
      .model-forge-stage-foot {{
        padding-left: 16px;
        padding-right: 16px;
      }}
    }}
    .vision-helper {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }}
    .vision-feed canvas {{
      display: none;
    }}
    .vision-status,
    .vision-note {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }}
    .vision-preview-card img {{
      width: 100%;
      min-height: 140px;
      border: 1px solid rgba(111, 229, 255, 0.16);
      background: rgba(5, 12, 22, 0.92);
      object-fit: cover;
    }}
    .brains-shell {{
      display: grid;
      gap: 16px;
    }}
    .brains-summary {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .brains-summary .tag {{
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid var(--line-soft);
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      background: rgba(8, 18, 32, 0.82);
    }}
    .brains-layout {{
      display: grid;
      grid-template-columns: minmax(0, 1.75fr) minmax(280px, 0.9fr);
      gap: 16px;
      align-items: start;
    }}
    .brain-network-shell {{
      border: 1px solid var(--line-soft);
      padding: 16px;
      background: rgba(9, 20, 34, 0.68);
    }}
    .brain-network-head {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: baseline;
      margin-bottom: 14px;
    }}
    .brain-network-head strong {{
      color: var(--cyan);
      letter-spacing: 0.16em;
      text-transform: uppercase;
      font-size: 13px;
    }}
    .brain-network-head span {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .brain-mesh-modal-stage.hero {{
      min-height: 620px;
      border-radius: 12px;
      background:
        radial-gradient(circle at center, rgba(111, 229, 255, 0.05), transparent 32%),
        linear-gradient(180deg, rgba(8, 18, 30, 0.94), rgba(6, 12, 22, 0.98));
    }}
    .brains-sidebar {{
      display: grid;
      gap: 14px;
    }}
    .brains-sidecard {{
      border: 1px solid var(--line-soft);
      padding: 16px;
      background: rgba(10, 22, 36, 0.56);
      min-height: 112px;
    }}
    .brains-sidecard h3 {{
      margin: 0 0 10px;
      font-size: 13px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--cyan);
    }}
    .brain-route {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .brain-route span,
    .brain-legend span {{
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid var(--line-soft);
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      background: rgba(8, 18, 32, 0.82);
    }}
    .brain-legend {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .brain-side-list {{
      display: grid;
      gap: 10px;
    }}
    .brain-side-row {{
      padding-top: 10px;
      border-top: 1px solid rgba(111, 229, 255, 0.1);
      color: #d9e7f7;
      font-size: 13px;
      line-height: 1.45;
    }}
    .brain-side-row:first-child {{
      border-top: none;
      padding-top: 0;
    }}
    @keyframes spin-slow {{
      from {{ transform: rotate(0deg); }}
      to {{ transform: rotate(360deg); }}
    }}
    @keyframes spin-reverse {{
      from {{ transform: rotate(360deg); }}
      to {{ transform: rotate(0deg); }}
    }}
    @keyframes pulse-core {{
      0%, 100% {{ transform: scale(calc(0.995 + (var(--energy) * 0.008))); }}
      50% {{ transform: scale(calc(1.006 + (var(--energy) * 0.018))); }}
    }}
    @keyframes equalize {{
      0%, 100% {{ transform: scaleY(0.45); opacity: 0.42; }}
      50% {{ transform: scaleY(calc(0.6 + var(--energy))); opacity: 1; }}
    }}
    @keyframes holoOrbit {{
      from {{ transform: translate(-50%, -50%) rotate(0deg); }}
      to {{ transform: translate(-50%, -50%) rotate(360deg); }}
    }}
    @keyframes breathe {{
      0%, 100% {{ transform: scale(0.985); opacity: 0.78; }}
      50% {{ transform: scale(1.02); opacity: 1; }}
    }}
    @keyframes drift {{
      from {{ transform: rotate(0deg) scale(0.985); }}
      to {{ transform: rotate(360deg) scale(1.015); }}
    }}
    @keyframes fallbackDotPulse {{
      0%, 100% {{ opacity: 0.62; }}
      50% {{ opacity: 1; }}
    }}
    @keyframes atmosphere {{
      0% {{ transform: translate3d(-1%, 0, 0); }}
      50% {{ transform: translate3d(1.5%, -1%, 0); }}
      100% {{ transform: translate3d(-1%, 0, 0); }}
    }}
    @keyframes sceneDockIn {{
      0% {{
        opacity: 0;
        transform: translateY(18px) scale(0.985);
      }}
      100% {{
        opacity: 1;
        transform: translateY(0) scale(1);
      }}
    }}
    @media (max-width: 1080px) {{
      body[data-core-dock="corner"] .viewport {{
        grid-template-columns: 1fr;
        grid-template-areas:
          "core"
          "scene"
          "chat";
      }}
      .topbar {{
        grid-template-columns: 1fr;
        justify-items: center;
      }}
      .meta-rail,
      .wordmark {{
        justify-self: center;
      }}
      .viewport {{
        grid-template-columns: 1fr;
        grid-template-areas:
          "core"
          "scene"
          "chat";
        gap: 18px;
        grid-auto-rows: max-content;
      }}
      .transcript-rail,
      .packet-strip,
      .signal-rail-shell,
      .signal-rail,
      .signal-rail-toggle {{
        position: static;
        width: 100%;
        align-items: stretch;
      }}
      .transcript-rail {{
        height: auto;
        min-height: 300px;
        max-height: none;
      }}
      .brain-graph-panel {{
        position: static;
        width: 100%;
      }}
      .brains-layout {{
        grid-template-columns: 1fr;
      }}
      .core-stage {{
        width: min(92vw, 720px);
      }}
      .core-home-summary {{
        position: relative;
        left: auto;
        bottom: auto;
        transform: none;
        width: 100%;
        margin-top: 18px;
      }}
      .core-home-grid {{
        grid-template-columns: 1fr;
      }}
      .scene-shell-head {{
        grid-template-columns: 1fr;
        display: grid;
      }}
      .scene-shell-actions {{
        justify-content: start;
      }}
      body[data-core-dock="corner"]:not(.modal-open) .core-stage {{
        position: relative;
        top: auto;
        left: auto;
        width: min(92vw, 720px);
        transform: none;
        z-index: 1;
        pointer-events: auto;
        opacity: 1;
        filter: none;
      }}
      .input-cluster {{
        grid-template-columns: 1fr;
        grid-template-areas:
          "context"
          "composer"
          "actions";
      }}
      .composer-actions {{
        justify-content: stretch;
      }}
      .packet-grid {{
        grid-template-columns: 1fr;
      }}
      .vision-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    /* Override viewport to stretch chamber to full available width */
    .viewport:has(.chamber) {{
      grid-template-columns: 1fr;
      grid-template-areas: none;
      max-width: none;
      justify-content: stretch;
      min-height: calc(100vh - 180px);
    }}
    .chamber {{
      grid-column: 1;
      align-self: stretch;
    }}

    /* ============================================================
       LIVING BRIEFING — 5-ZONE CHAMBER GRID
       ============================================================ */
    .chamber {{
      display: grid;
      grid-template-columns: 1fr 320px;
      grid-template-rows: 1fr 1fr auto;
      gap: 14px;
      height: 100%;
      min-height: 0;
      padding: 0 4px;
    }}
    .zone-briefing {{
      grid-column: 1;
      grid-row: 1 / 3;
    }}
    .zone-already {{
      grid-column: 2;
      grid-row: 1;
    }}
    .zone-needs {{
      grid-column: 2;
      grid-row: 2;
    }}
    .zone-drift {{
      grid-column: 1;
      grid-row: 3;
    }}
    .zone-speak {{
      grid-column: 2;
      grid-row: 3;
    }}
    .zone {{
      background: var(--zone-bg);
      border: 1px solid var(--zone-border);
      border-radius: 12px;
      padding: 18px 20px 16px;
      backdrop-filter: blur(20px) saturate(130%);
      box-shadow: 0 2px 40px var(--zone-glow), inset 0 1px 0 rgba(255,255,255,0.04);
      display: flex;
      flex-direction: column;
      gap: 12px;
      overflow: hidden;
      position: relative;
    }}
    .zone::before {{
      content: '';
      position: absolute;
      top: 0; left: 20px; right: 20px;
      height: 1px;
    }}
    .zone-briefing::before {{ background: var(--briefing-accent); }}
    .zone-already::before  {{ background: var(--already-accent);  }}
    .zone-needs::before    {{ background: var(--needs-accent);    }}
    .zone-drift::before    {{ background: var(--drift-accent);    }}
    .zone-speak::before    {{ background: var(--speak-accent);    }}
    .zone-launch::before   {{ background: var(--warm);            }}
    .zone-launch {{ border-left: 3px solid var(--warm); }}
    .launch-project-header {{ font-size: 1.1em; font-weight: 600; margin-bottom: 8px; color: var(--warm); }}
    .launch-tracks {{ display: flex; gap: 12px; margin-bottom: 10px; flex-wrap: wrap; }}
    .launch-track {{ flex: 1; min-width: 120px; }}
    .launch-track-label {{ font-size: 0.75em; opacity: 0.7; text-transform: uppercase; letter-spacing: 0.05em; }}
    .launch-track-progress {{ height: 4px; background: rgba(255,255,255,0.15); border-radius: 2px; margin-top: 4px; }}
    .launch-track-fill {{ height: 100%; background: var(--warm); border-radius: 2px; transition: width 0.5s ease; }}
    .launch-reviews {{ padding: 8px 0; border-top: 1px solid rgba(255,255,255,0.08); }}
    .launch-queue {{ padding: 8px 0; border-top: 1px solid rgba(255,255,255,0.08); font-size: 0.9em; opacity: 0.85; }}
    .launch-performance {{ padding: 8px 0; border-top: 1px solid rgba(255,255,255,0.08); }}
    .launch-perf-row {{ display: flex; gap: 16px; flex-wrap: wrap; }}
    .launch-perf-item {{ font-size: 0.85em; }}
    .launch-perf-value {{ font-size: 1.1em; font-weight: 600; color: var(--warm); }}
    .launch-next-action {{ margin-top: 8px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 6px; border-left: 3px solid var(--warm); font-size: 0.9em; }}
    .launch-action-btn {{ display: inline-block; margin-top: 6px; padding: 4px 12px; background: var(--warm); color: #1a1612; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85em; font-weight: 600; }}
    .zone-label {{
      font-size: 9px;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      color: var(--muted);
      opacity: 0.7;
      flex-shrink: 0;
    }}
    .zone-label-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }}
    /* Zone item components */
    .zone-empty {{
      color: var(--muted);
      font-size: 13px;
      font-style: italic;
      opacity: 0.6;
      margin: auto 0;
    }}
    .briefing-items {{
      overflow-y: auto;
      flex: 1;
    }}
    .briefing-item {{
      display: flex;
      gap: 10px;
      align-items: flex-start;
      padding: 6px 0;
      border-bottom: 1px solid rgba(111, 207, 255, 0.06);
    }}
    .briefing-dot {{
      width: 6px; height: 6px; border-radius: 50%;
      background: var(--briefing-accent);
      flex-shrink: 0;
      margin-top: 5px;
      box-shadow: 0 0 8px var(--briefing-accent);
    }}
    .briefing-text {{ font-size: 13px; line-height: 1.5; color: var(--ink); }}
    .briefing-sub  {{ font-size: 11px; color: var(--muted); margin-top: 2px; }}
    .briefing-item[data-priority="high"] .briefing-dot {{ background: var(--amber); box-shadow: 0 0 8px var(--amber); }}
    .working-items, .needs-items, .drift-items {{
      overflow-y: auto;
      flex: 1;
    }}
    .working-item {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 5px 0;
      border-bottom: 1px solid rgba(111, 207, 255, 0.06);
    }}
    .working-agent {{ font-size: 11px; color: var(--teal); letter-spacing: 0.06em; }}
    .working-action {{ font-size: 12px; color: var(--muted); max-width: 60%; text-align: right; }}
    .needs-item {{ padding: 8px 0; border-bottom: 1px solid rgba(111, 207, 255, 0.06); }}
    .needs-text {{ font-size: 13px; color: var(--ink); margin-bottom: 6px; }}
    .needs-actions {{ display: flex; gap: 6px; }}
    .needs-btn {{ font-size: 11px; padding: 3px 10px; border-radius: 999px; cursor: pointer; border: 1px solid; }}
    .needs-approve {{ border-color: var(--ok); color: var(--ok); background: rgba(108, 255, 175, 0.06); }}
    .needs-dismiss {{ border-color: var(--muted); color: var(--muted); background: transparent; }}
    .needs-badge {{ font-size: 10px; padding: 1px 6px; border-radius: 999px; background: var(--needs-accent); color: #050a12; margin-left: 6px; }}
    .drift-item {{ display: flex; gap: 8px; align-items: center; padding: 4px 0; }}
    .drift-indicator {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
    .drift-item[data-severity="warn"] .drift-indicator {{ background: var(--warn); }}
    .drift-item[data-severity="alert"] .drift-indicator {{ background: var(--alert); }}
    .drift-text {{ font-size: 12px; color: var(--ink); }}
    .drift-ok {{ display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--ok); }}
    .drift-ok-dot {{ width: 8px; height: 8px; border-radius: 50%; background: var(--ok); box-shadow: 0 0 8px var(--ok); flex-shrink: 0; }}
    /* Speak Freely zone — chat composer embedded */
    .zone-speak .zone-speak-composer {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      flex: 1;
    }}
    .zone-speak .zone-speak-input {{
      width: 100%;
      min-height: 52px;
      max-height: 120px;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid rgba(111, 229, 255, 0.22);
      background: rgba(5, 12, 22, 0.72);
      color: var(--ink);
      font: inherit;
      font-size: 13px;
      line-height: 1.5;
      resize: none;
      outline: none;
    }}
    .zone-speak .zone-speak-input::placeholder {{
      color: rgba(140, 165, 191, 0.5);
    }}
    .zone-speak .zone-speak-input:focus {{
      border-color: rgba(111, 229, 255, 0.40);
      box-shadow: 0 0 0 1px rgba(111, 229, 255, 0.14);
    }}
    .zone-speak .zone-speak-actions {{
      display: flex;
      gap: 6px;
      justify-content: flex-end;
      flex-wrap: wrap;
    }}
    /* Shimmer skeleton for loading states */
    @keyframes zone-shimmer {{
      0%   {{ background-position: -200% 0; }}
      100% {{ background-position: 200% 0; }}
    }}
    .zone-skeleton {{
      height: 12px;
      border-radius: 6px;
      background: linear-gradient(90deg, rgba(111,229,255,0.04) 25%, rgba(111,229,255,0.10) 50%, rgba(111,229,255,0.04) 75%);
      background-size: 200% 100%;
      animation: zone-shimmer 1.6s ease-in-out infinite;
    }}
    .zone-skeleton + .zone-skeleton {{ margin-top: 8px; }}
    /* Mobile responsive */
    @media (max-width: 768px) {{
      .chamber {{
        grid-template-columns: 1fr;
        grid-template-rows: auto;
        height: auto;
      }}
      .zone-briefing, .zone-already, .zone-needs, .zone-drift, .zone-launch, .zone-speak {{
        grid-column: 1;
        grid-row: auto;
      }}
      .zone-briefing {{ min-height: 220px; }}
    }}
  </style>
</head>
<body data-voice-state="idle" data-shell-layout="quiet-home">
  <div class="shell">
    <header class="topbar">
      <div class="wordmark">JARVIS</div>
      <div class="state-cluster">
        <div class="wave-strip" id="wave-strip">
          {''.join(f'<span style="--i:{index};"></span>' for index in range(24))}
        </div>
        <div class="state-label" id="state-label">Idle</div>
        <div class="state-source-indicator" id="state-source-indicator" data-provider="standby" title="Response source standby">Standby</div>
      </div>
      <div class="meta-rail">
        <button class="meta-triage" id="triage-summary-launcher" type="button" title="Open triage sidecar">
          <span class="meta-triage-icon">◈</span>
        </button>
        <button class="meta-weather" id="storm-weather-button" type="button" title="Live weather from Storm">
          <span class="meta-weather-icon" id="storm-weather-icon">--</span>
          <span class="meta-weather-temp" id="storm-weather-temp">--°</span>
        </button>
        <button class="meta-dashboard" id="finance-review-launcher" type="button" title="Open Family Finance Review">
          <span class="meta-dashboard-icon" id="finance-review-launcher-icon">$</span>
          <span class="meta-dashboard-count" id="finance-review-launcher-count">--</span>
        </button>
        <button class="meta-dashboard" id="wealth-launcher" type="button" title="Open Wealth Review">
          <span class="meta-dashboard-icon" id="wealth-launcher-icon">₿</span>
          <span class="meta-dashboard-count" id="wealth-launcher-count">--</span>
        </button>
        <button class="meta-dashboard" id="dashboard-launcher" type="button" title="Open dashboard report">
          <span class="meta-dashboard-icon" id="dashboard-launcher-icon">◉</span>
          <span class="meta-dashboard-count" id="dashboard-launcher-count">--</span>
        </button>
        <span class="meta-chip" id="meta-time">--:--</span>
        <span class="meta-chip hidden" id="runtime-freshness">Live</span>
        <button class="meta-icon-button" id="mode-toggle" type="button" title="Household mode">⌂</button>
        <button class="ghost-toggle" id="open-settings" type="button">Settings</button>
      </div>
    </header>
    <div class="mode-panel" id="mode-panel" aria-hidden="true">
      <div class="mode-panel-head">
        <div class="window-head-main">
          <div class="window-controls" aria-label="Window controls">
            <button class="window-control close" id="mode-window-close" type="button" aria-label="Close Household Mode"></button>
            <button class="window-control minimize" id="mode-window-minimize" type="button" aria-label="Minimize Household Mode"></button>
            <button class="window-control maximize" id="mode-window-maximize" type="button" aria-label="Maximize Household Mode"></button>
          </div>
          <div class="mode-panel-title">Household Mode</div>
        </div>
      </div>
      <div class="mode-panel-current" id="mode-panel-current">Current mode: --</div>
      <label>
        Switch as
        <select id="mode-actor">{actor_options}</select>
      </label>
      <label>
        Mode
        <select id="mode-select">{mode_options}</select>
      </label>
      <label>
        Reason
        <input id="mode-reason" value="Manual mode update from JARVIS shell.">
      </label>
      <div class="mode-panel-actions">
        <button class="ghost-toggle" id="mode-panel-cancel" type="button">Cancel</button>
        <button class="dock-button primary" id="mode-panel-apply" type="button">Apply</button>
      </div>
      <div class="mode-panel-status" id="mode-panel-status">Right now, you can also change it from the CLI with `python -m jarvis mode-transition --actor Chris --mode family-morning --reason "..."`.</div>
    </div>

    <main class="viewport">
      <!-- Packet strip and signal rail kept for existing JS compatibility -->
      <button class="packet-strip-toggle" id="packet-strip-toggle" type="button">Packets</button>
      <div class="packet-strip collapsed" id="packet-strip" aria-hidden="true"></div>
      <button class="signal-rail-toggle" id="signal-rail-toggle" type="button">Status</button>
      <div class="signal-rail-shell layout-editable-panel" id="status-panel">
        <div class="layout-panel-handle" id="status-drag-handle" data-layout-drag="status" title="Drag status panel when layout edit mode is on">Status</div>
        <div class="signal-rail" id="signal-rail"></div>
        <div class="layout-resize-handle" data-layout-resize="status" title="Resize status panel when layout edit mode is on"></div>
      </div>
      <div class="brain-graph-panel layout-editable-panel" id="brain-panel">
        <div class="brain-graph-head" id="brain-drag-handle" data-layout-drag="brain" title="Drag brain panel when layout edit mode is on">
          <strong>Brain Mesh</strong>
          <span id="brain-graph-provider">Standby</span>
        </div>
        <div class="brain-mesh-stage" id="brain-mesh-panel">
          <canvas class="brain-mesh-canvas" id="brain-mesh-panel-canvas" aria-hidden="true"></canvas>
          <div class="brain-mesh-overlay"></div>
          <div class="brain-mesh-caption">
            <span>Ambient topology</span>
            <span id="brain-mesh-caption-state">standby</span>
          </div>
        </div>
        <div class="brain-graph-meta" id="brain-graph-meta"></div>
        <div class="layout-resize-handle" data-layout-resize="brain" title="Resize brain panel when layout edit mode is on"></div>
      </div>

      <!-- Hidden transcript rail kept for JS compatibility (transcript-history, last-user-text, last-jarvis-text) -->
      <div class="transcript-rail layout-editable-panel" id="chat-panel" style="display:none;" aria-hidden="true">
        <div class="chat-window">
          <div class="transcript-head" id="chat-drag-handle" data-layout-drag="chat" title="Drag chat panel when layout edit mode is on">
            <div class="transcript-title">Jarvis</div>
            <div class="transcript-copy">Online and keeping the thread warm</div>
          </div>
          <div class="transcript-empty-state" id="transcript-empty-state">
            Start talking naturally. This thread is meant to feel like an ongoing conversation, not a fresh form every time.
          </div>
          <div class="transcript-history" id="transcript-history"></div>
        </div>
        <div class="transcript-status-store" aria-hidden="true">
          <div id="last-user-text">Awaiting command.</div>
          <div id="last-jarvis-text">Standing by.</div>
        </div>
        <div class="layout-resize-handle" data-layout-resize="chat" title="Resize chat panel when layout edit mode is on"></div>
      </div>

      <!-- Hidden orb/core cluster kept for JS that references holo-core-canvas, core-command-ring, etc. -->
      <div class="core-cluster" id="core-cluster" style="display:none;" aria-hidden="true">
        <div class="core-stage layout-editable-panel" id="core-panel">
          <div class="layout-panel-handle" id="core-drag-handle" data-layout-drag="core" title="Drag core panel when layout edit mode is on">Core</div>
          <div class="core-backdrop"></div>
          <div class="holo-core-shell" id="holo-core-shell">
            <div class="holo-core-fallback" aria-hidden="true">
              <div class="holo-core-fallback-dust"></div>
              <div class="holo-core-fallback-core"></div>
            </div>
            <canvas class="holo-core-canvas" id="holo-core-canvas" aria-hidden="true"></canvas>
            <div class="holo-core-overlay"></div>
            <div class="beam-column"></div>
            <div class="emitter-disc"></div>
          </div>
          <div class="core-command-ring" id="core-command-ring" aria-hidden="true"></div>
          <div class="core-label" id="core-label">
            <button class="core-command-trigger" id="core-command-trigger" type="button" aria-label="Open JARVIS command tree" aria-expanded="false" onclick="toggleCoreCommandTree()">
              <div class="name">JARVIS</div>
            </button>
          </div>
          <div class="design-review-panel collapsed" id="design-review-panel">
            <button class="design-review-launcher" id="design-review-launcher" type="button">
              <span class="review-dot"></span>
              <span>Page Review</span>
              <strong id="design-review-launcher-state">Ready</strong>
            </button>
            <div class="design-review-body">
              <div class="design-review-head">
                <span>Center Review</span>
                <strong id="design-review-name">Not active</strong>
              </div>
              <div class="design-review-copy" id="design-review-copy">Start design review to highlight one center-animation element at a time in red, then choose whether to keep or remove it.</div>
              <textarea class="design-review-field" id="design-review-input" placeholder="Describe the change you want for this highlighted element. Example: make it thinner, slower, brighter, or smaller." disabled></textarea>
              <div class="design-review-saved" id="design-review-saved">No feedback captured yet.</div>
              <div class="design-review-actions">
                <button class="dock-button" id="design-review-start" type="button">Start Review</button>
                <button class="dock-button primary" id="design-review-apply" type="button" disabled>Apply Feedback</button>
                <button class="dock-button primary" id="design-review-save" type="button" disabled>Save Changes</button>
                <button class="dock-button" id="design-review-keep" type="button" disabled>Keep</button>
                <button class="dock-button review-danger" id="design-review-remove" type="button" disabled>Remove</button>
                <button class="dock-button" id="design-review-next" type="button" disabled>Next</button>
                <button class="dock-button" id="design-review-stop" type="button" disabled>Done</button>
              </div>
            </div>
          </div>
          <div class="layout-resize-handle" data-layout-resize="core" title="Resize core panel when layout edit mode is on"></div>
        </div>
        <section class="core-home-summary" id="core-home-summary" aria-label="Home summary">
          <div class="core-home-head" id="core-home-head">
            <div class="window-head-main">
              <div class="window-controls" aria-label="Window controls">
                <button class="window-control close" id="triage-summary-close" type="button" aria-label="Close triage sidecar"></button>
                <button class="window-control minimize" id="triage-summary-minimize" type="button" aria-label="Minimize triage sidecar"></button>
                <button class="window-control maximize" id="triage-summary-maximize" type="button" aria-label="Maximize triage sidecar"></button>
              </div>
              <div class="core-home-head-copy">
                <div class="core-home-kicker" id="core-home-kicker">Private Intelligence Chamber</div>
              </div>
            </div>
          </div>
          <div class="core-home-line" id="core-home-line">You are not carrying this alone.</div>
          <div class="core-home-list" id="core-home-preview">
            <div class="core-home-empty">The chamber is warming up.</div>
          </div>
          <div class="core-home-footer">
            <div class="core-home-status" id="core-home-status"></div>
            <div class="core-home-actions">
              <button class="dock-button primary" id="core-home-primary-action" type="button" data-home-open-packet="briefing">Open Briefing</button>
              <button class="dock-button" id="core-home-secondary-action" type="button" data-home-open-packet="approvals">Needs You</button>
              <button class="dock-button" id="core-home-tertiary-action" type="button" data-home-open-packet="catalyst">Resume Work</button>
              <button class="dock-button" id="core-home-speak-action" type="button" data-home-action="focus-speak">Speak</button>
            </div>
          </div>
        </section>
      </div>

      <!-- ===================================================
           LIVING BRIEFING — 5-ZONE CHAMBER
           =================================================== -->
      <div class="chamber" id="chamber">

        <!-- Zone 1: The Briefing — heart of the screen -->
        <div class="zone zone-briefing" id="zone-briefing">
          <div class="zone-label-row">
            <span class="zone-label">The Briefing</span>
          </div>
          <div class="briefing-items" id="briefing-items">
            <p class="zone-empty">I've been watching. Here's what matters.</p>
          </div>
        </div>

        <!-- Zone 2: Already Working — background agent preparation -->
        <div class="zone zone-already" id="zone-already">
          <div class="zone-label">Already Working</div>
          <div class="working-items" id="working-items">
            <p class="zone-empty">Agents standing by.</p>
          </div>
        </div>

        <!-- Zone 3: Needs You — decisions and approvals -->
        <div class="zone zone-needs" id="zone-needs">
          <div class="zone-label-row">
            <span class="zone-label">Needs You</span>
            <span class="needs-badge" id="needs-badge" style="display:none;">0</span>
          </div>
          <div class="needs-items" id="needs-items">
            <p class="zone-empty">Nothing waiting.</p>
          </div>
        </div>

        <!-- Zone 4: Drift / Risk — gentle alerts -->
        <div class="zone zone-drift" id="zone-drift">
          <div class="zone-label">Drift / Risk</div>
          <div class="drift-items" id="drift-items">
            <div class="drift-ok"><span class="drift-ok-dot"></span> On course.</div>
          </div>
        </div>

        <!-- Zone 5: Launch Control — publishing project dashboard -->
        <div class="zone zone-launch" id="zone-launch" style="display:none">
          <div class="zone-label">LAUNCH CONTROL</div>
          <div id="launch-project-header" class="launch-project-header"></div>
          <div id="launch-tracks" class="launch-tracks"></div>
          <div id="launch-reviews" class="launch-reviews"></div>
          <div id="launch-queue" class="launch-queue"></div>
          <div id="launch-performance" class="launch-performance"></div>
          <div id="launch-next-action" class="launch-next-action"></div>
        </div>

        <!-- Zone 6: Speak Freely — conversational input -->
        <div class="zone zone-speak" id="zone-speak">
          <div class="zone-label">Speak freely.</div>
          <div class="zone-speak-composer">
            <!-- Attachment tray kept for existing JS -->
            <div class="attachment-tray" id="attachment-tray">
              <div class="attachment-dropzone" id="attachment-dropzone">
                <strong>Drop files into chat</strong>
                <span>PDF, PowerPoint, Word, text, spreadsheets, and similar files can be staged here for the next message.</span>
              </div>
              <div class="attachment-list" id="attachment-list"></div>
            </div>
            <textarea id="command-input" class="zone-speak-input" rows="1" placeholder="Say anything. Use /correct to redirect Jarvis, /teach to make it stick, or /learn to turn it into a reusable skill."></textarea>
            <div class="context-action-dock" id="context-action-dock" aria-label="Context actions"></div>
            <div class="zone-speak-actions">
              <input id="chat-file-input" type="file" multiple hidden />
              <button class="dock-button" id="add-attachment" type="button" title="Attach files">Attach</button>
              <button class="dock-button" id="toggle-speech-output" type="button" title="Toggle JARVIS voice output">Voice On</button>
              <button class="dock-button" id="voice-command" title="Speak to JARVIS">Talk</button>
              <button class="dock-button" id="open-context-controls" type="button" title="Actor and room controls">Context</button>
              <button class="dock-button primary" id="send-command">Send</button>
            </div>
          </div>
        </div>

      </div>
      <!-- /chamber -->

      <section class="scene-stage hidden" id="scene-stage" aria-live="polite">
        <div class="scene-shell">
          <div class="scene-shell-head">
            <div class="window-head-main">
              <div class="window-controls" aria-label="Window controls">
                <button class="window-control close" id="scene-window-close" type="button" aria-label="Close Scene"></button>
                <button class="window-control minimize" id="scene-window-minimize" type="button" aria-label="Minimize Scene"></button>
                <button class="window-control maximize" id="scene-window-maximize" type="button" aria-label="Maximize Scene"></button>
              </div>
              <div class="scene-shell-copy">
                <div class="scene-shell-kicker" id="scene-shell-kicker">Focused Scene</div>
                <div class="scene-shell-title" id="scene-shell-title">Scene</div>
                <div class="scene-shell-summary" id="scene-shell-summary">Select a domain to focus the shell on one scene at a time.</div>
              </div>
            </div>
            <div class="scene-shell-actions">
              <button class="dock-button" id="scene-shell-refresh" type="button">Refresh</button>
            </div>
          </div>
          <div class="scene-shell-body" id="scene-shell-body"></div>
        </div>
      </section>

    </main>

    <footer class="dock"></footer>
  </div>

  <div class="context-panel" id="context-panel" aria-hidden="true">
    <div class="context-panel-head">
      <div class="window-head-main">
        <div class="window-controls" aria-label="Window controls">
          <button class="window-control close" id="context-window-close" type="button" aria-label="Close Command Context"></button>
          <button class="window-control minimize" id="context-window-minimize" type="button" aria-label="Minimize Command Context"></button>
          <button class="window-control maximize" id="context-window-maximize" type="button" aria-label="Maximize Command Context"></button>
        </div>
        <div class="context-panel-title">Command Context</div>
      </div>
    </div>
    <div class="context-panel-copy" id="context-panel-copy">Choose who is speaking and which room JARVIS should treat as active.</div>
    <label>
      Actor
      <select id="actor" class="dock-select">{actor_options}</select>
    </label>
    <label>
      Room
      <select id="room" class="dock-select">{room_options}</select>
    </label>
    <div class="context-panel-actions">
      <button class="ghost-toggle" id="context-panel-done" type="button">Done</button>
    </div>
  </div>

    <div class="modal-layer" id="modal-layer" aria-hidden="true">
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <div class="modal-head" id="modal-drag-handle" data-layout-modal-drag="true" title="Drag modal when layout edit mode is on">
          <div class="window-head-main">
            <div class="window-controls" aria-label="Window controls">
              <button class="window-control close" id="modal-window-close" type="button" aria-label="Close window"></button>
              <button class="window-control minimize" id="modal-window-minimize" type="button" aria-label="Minimize window"></button>
              <button class="window-control maximize" id="modal-window-maximize" type="button" aria-label="Maximize window"></button>
            </div>
            <h2 id="modal-title">Packet</h2>
          </div>
        </div>
        <div class="packet-body" id="modal-body"></div>
        <div class="layout-resize-handle modal-resize-handle" data-layout-modal-resize="true" title="Resize modal when layout edit mode is on"></div>
      </div>
    </div>
    <div class="lifecycle-toast" id="lifecycle-toast" aria-live="polite" aria-atomic="true">
      <strong id="lifecycle-toast-title">Lifecycle Update</strong>
      <span id="lifecycle-toast-body">Ready.</span>
    </div>
  <script type="importmap">
    {{
      "imports": {{
        "three": "https://unpkg.com/three@0.174.0/build/three.module.js"
      }}
    }}
  </script>
  <script type="module">
    import * as THREE from "https://unpkg.com/three@0.174.0/build/three.module.js";
    import {{ STLLoader }} from "https://unpkg.com/three@0.174.0/examples/jsm/loaders/STLLoader.js";

    const packetTreePresets = {packet_tree_presets};
    const availableModes = {available_modes};
    const hardCenterDesign = {center_design};
    const state = {{
      dashboard: null,
      currentDevice: null,
      financeReview: null,
      wealthReview: null,
      wealthRunsByLane: {{}},
      wealthAgent: null,
      wealthSelectedLane: "passive-income",
      wealthSelectedItemId: "",
      lastBriefing: "",
      conversationId: "",
      transcriptTurns: [],
      pendingAttachments: [],
      uploadingAttachments: false,
      attachmentDragActive: false,
      layoutEditMode: false,
      panelLayouts: {{}},
      chatPlacement: {{ floating: false, left: null, top: null }},
      modalPlacements: {{}},
      windowPlacements: {{
        triageSummary: {{ left: null, top: null, width: null, height: null }},
        scene: {{ left: null, top: null, width: null, height: null }},
        mode: {{ left: null, top: null, width: null, height: null }},
        context: {{ left: null, top: null, width: null, height: null }},
      }},
      windowStates: {{
        triageSummary: {{ minimized: false, maximized: false }},
        scene: {{ minimized: false, maximized: false }},
        modal: {{ minimized: false, maximized: false }},
        mode: {{ minimized: false, maximized: false }},
        context: {{ minimized: false, maximized: false }},
      }},
      triageSummaryVisible: true,
      activeWindowId: "",
      windowZCounter: 40,
      dragState: null,
      manualPacketIntentUntil: 0,
      packet: "",
      packetHydrationToken: 0,
      packetHydrationPending: "",
      lifecycleInspector: null,
      lifecycleActionTrail: [],
      lifecycleToastTimer: null,
      speechEnabled: true,
      speakingTimer: null,
      energyTimer: null,
      currentAudio: null,
      currentAudioUrl: "",
      recognizer: null,
      recognizing: false,
      alwaysOnMicEnabled: true,
      recognitionMode: "idle",
      wakeWord: "hey jarvis",
      followUpWindowMs: 120000,
      followUpUntil: 0,
      awaitingImmediateReply: false,
      recognitionRestartTimer: null,
      clapStream: null,
      clapSourceNode: null,
      clapAnalyser: null,
      clapMonitorFrame: null,
      clapData: null,
      clapPeaks: [],
      clapCooldownUntil: 0,
      clapNoiseFloor: 6,
      dashboardRefreshPromise: null,
      dashboardRefreshQueued: false,
      lastDashboardRefreshAt: 0,
      shellStateRefreshPromise: null,
      lastShellStateRefreshAt: 0,
      energyCurrent: 0.35,
      energyTarget: 0.35,
      catalystPage: "home",
      missionControl: null,
      activeMissionId: "",
      activeScene: "",
      activeOverlay: {{ type: "", payload: null }},
      coreCommandOpen: false,
      packetStripExpanded: false,
      packetTreePath: [],
      initialPacketOverride: {initial_packet_json},
      packetUrlOverrideConsumed: false,
      signalRailExpanded: false,
      holoReview: {{
        active: false,
        expanded: false,
        pageId: "shell",
        index: 0,
        activePage: "shell",
        pageSettings: {{
          shell: {{ enabled: true }},
        }},
        pages: {{
          shell: {{
            removed: new Set(),
            notes: new Map(),
            overrides: new Map(),
          }},
        }},
      }},
      voiceSettings: null,
      voiceOptions: null,
      accountRegistry: null,
      identity: null,
      connectedDevices: null,
      sessionIdentity: null,
      locationSettings: null,
      settingsMessage: "",
      brainMeshScenes: new Map(),
      holoCoreScene: null,
      audioContext: null,
      audioAnalyser: null,
      audioSourceNode: null,
      audioReactiveFrame: null,
      audioReactive: false,
      visionStream: null,
      visionDeviceId: "",
      visionDevices: [],
      lastVisionCapture: null,
      visionCropEnabled: false,
      visionCropRect: null,
      visionDragStart: null,
      visionCalibration: null,
      modelForgeScene: null,
      modelForgeOptions: null,
      modelForgeCreativeProfile: "",
      modelForgeConceptSessionId: "",
      modelForgeConceptVariants: [],
      modelForgeSelectedVariantIndex: 0,
      modelForgeVisionHints: null,
      pendingModelForgeConceptLaunch: null,
      shellDeviceId: "",
      firstLight: null,
      sessionActorOverride: "",
      lastAssistantSurfaceKey: "",
      browserAlertsEnabled: false,
      browserAlertsPermission: "default",
      autonomyTickTimer: null,
      autonomyBackgroundTimer: null,
      storm: {{
        available: false,
        loading: false,
        temperature: "--",
        icon: "--",
        summary: "Live weather unavailable.",
        timestamp: "",
        lastFetchedAt: 0,
        refreshPromise: null,
      }},
      brainGraphSignature: "",
    }};

    const VISION_CALIBRATION_KEY = "jarvis-vision-calibration-v1";
    const SPEECH_OUTPUT_ENABLED_KEY = "jarvis-speech-output-enabled-v1";
    const PANEL_LAYOUTS_KEY = "jarvis-panel-layouts-v1";
    const CHAT_LAYOUT_KEY = "jarvis-chat-layout-v1";
    const MODAL_LAYOUTS_KEY = "jarvis-modal-layouts-v1";
    const LAYOUT_EDIT_ENABLED_KEY = "jarvis-layout-edit-enabled-v1";
    const SHELL_DEVICE_ID_KEY = "jarvis-shell-device-id-v1";
    const SESSION_ACTOR_OVERRIDE_KEY = "jarvis-session-actor-override-v1";
    const ASSISTANT_SURFACE_KEY = "jarvis-assistant-surface-last-v1";
    const BROWSER_ALERTS_ENABLED_KEY = "jarvis-browser-alerts-enabled-v1";
    const STORM_LAT = 38.9595;
    const STORM_LON = -84.3877;
    const CATALYST_API_BASE_URL = "http://127.0.0.1:3001";
    const CATALYST_APP_BASE_URL = "http://127.0.0.1:5173";
    const CHRONICLE_APP_BASE_URL = "http://127.0.0.1:5175";
    const SHELL_EVENT_STREAM_PATH = "/ws/events";

    function escapeHtml(value) {{
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }}

    function shellEventStreamEnabled() {{
      return window.__JARVIS_ENABLE_EVENT_STREAM === true;
    }}

    function formatAttachmentBytes(value = 0) {{
      const size = Number(value || 0);
      if (!Number.isFinite(size) || size <= 0) return "0 B";
      const units = ["B", "KB", "MB", "GB"];
      let current = size;
      let index = 0;
      while (current >= 1024 && index < units.length - 1) {{
        current /= 1024;
        index += 1;
      }}
      const digits = current >= 10 || index === 0 ? 0 : 1;
      return `${{current.toFixed(digits)}} ${{units[index]}}`;
    }}

    function browserAlertsSupported() {{
      return typeof window !== "undefined" && "Notification" in window;
    }}

    function loadSpeechOutputEnabled() {{
      try {{
        const saved = window.localStorage.getItem(SPEECH_OUTPUT_ENABLED_KEY);
        if (saved == null) {{
          return true;
        }}
        return saved === "true";
      }} catch (error) {{
        return true;
      }}
    }}

    function saveSpeechOutputEnabled(value) {{
      state.speechEnabled = !!value;
      try {{
        window.localStorage.setItem(SPEECH_OUTPUT_ENABLED_KEY, value ? "true" : "false");
      }} catch (error) {{
        console.warn("Failed to persist speech output setting", error);
      }}
      renderSpeechOutputToggle();
    }}

    function loadLayoutEditMode() {{
      try {{
        return window.localStorage.getItem(LAYOUT_EDIT_ENABLED_KEY) === "true";
      }} catch (error) {{
        return false;
      }}
    }}

    function loadPanelLayouts() {{
      try {{
        const raw = window.localStorage.getItem(PANEL_LAYOUTS_KEY);
        const parsed = raw ? JSON.parse(raw) : {{}};
        const layouts = parsed && typeof parsed === "object" ? parsed : {{}};
        if (!layouts.chat) {{
          const legacyChat = loadChatPlacement();
          if (legacyChat?.floating) {{
            layouts.chat = {{
              floating: true,
              left: Number.isFinite(legacyChat.left) ? Number(legacyChat.left) : null,
              top: Number.isFinite(legacyChat.top) ? Number(legacyChat.top) : null,
            }};
          }}
        }}
        return layouts;
      }} catch (error) {{
        return {{}};
      }}
    }}

    function savePanelLayouts() {{
      try {{
        window.localStorage.setItem(PANEL_LAYOUTS_KEY, JSON.stringify(state.panelLayouts || {{}}));
      }} catch (error) {{
        console.warn("Failed to persist panel layouts", error);
      }}
    }}

    function saveLayoutEditMode(value) {{
      state.layoutEditMode = !!value;
      document.body.dataset.layoutEdit = value ? "true" : "false";
      try {{
        window.localStorage.setItem(LAYOUT_EDIT_ENABLED_KEY, value ? "true" : "false");
      }} catch (error) {{
        console.warn("Failed to persist layout edit mode", error);
      }}
    }}

    function loadChatPlacement() {{
      try {{
        const raw = window.localStorage.getItem(CHAT_LAYOUT_KEY);
        if (!raw) return {{ floating: false, left: null, top: null }};
        const parsed = JSON.parse(raw);
        return {{
          floating: !!parsed?.floating,
          left: Number.isFinite(parsed?.left) ? Number(parsed.left) : null,
          top: Number.isFinite(parsed?.top) ? Number(parsed.top) : null,
        }};
      }} catch (error) {{
        return {{ floating: false, left: null, top: null }};
      }}
    }}

    function saveChatPlacement() {{
      try {{
        window.localStorage.setItem(CHAT_LAYOUT_KEY, JSON.stringify(state.chatPlacement));
      }} catch (error) {{
        console.warn("Failed to persist chat placement", error);
      }}
    }}

    function loadModalPlacements() {{
      try {{
        const raw = window.localStorage.getItem(MODAL_LAYOUTS_KEY);
        const parsed = raw ? JSON.parse(raw) : {{}};
        return parsed && typeof parsed === "object" ? parsed : {{}};
      }} catch (error) {{
        return {{}};
      }}
    }}

    function saveModalPlacements() {{
      try {{
        window.localStorage.setItem(MODAL_LAYOUTS_KEY, JSON.stringify(state.modalPlacements || {{}}));
      }} catch (error) {{
        console.warn("Failed to persist modal placements", error);
      }}
    }}

    function renderSpeechOutputToggle() {{
      const button = document.getElementById("toggle-speech-output");
      if (!button) {{
        return;
      }}
      const enabled = !!state.speechEnabled;
      button.textContent = enabled ? "Voice On" : "Voice Off";
      button.classList.toggle("primary", enabled);
      button.setAttribute("aria-pressed", enabled ? "true" : "false");
      button.title = enabled
        ? "JARVIS voice replies are on. Click to mute speech and stay in text chat."
        : "JARVIS voice replies are muted. Click to turn speech back on.";
    }}

    function loadBrowserAlertsEnabled() {{
      try {{
        return window.localStorage.getItem(BROWSER_ALERTS_ENABLED_KEY) === "true";
      }} catch (error) {{
        return false;
      }}
    }}

    function saveBrowserAlertsEnabled(value) {{
      state.browserAlertsEnabled = !!value;
      try {{
        window.localStorage.setItem(BROWSER_ALERTS_ENABLED_KEY, value ? "true" : "false");
      }} catch (error) {{
        console.warn("Failed to persist browser alert setting", error);
      }}
    }}

    function browserAlertsReady() {{
      return browserAlertsSupported() && state.browserAlertsEnabled && state.browserAlertsPermission === "granted";
    }}

    async function loadJSON(url, options = undefined) {{
      const method = String(options?.method || "GET").toUpperCase();
      const timeoutMs = Number(options?.timeoutMs || 0);
      const fetchOptions = options ? {{ ...options }} : {{}};
      delete fetchOptions.timeoutMs;
      const retryable =
        typeof url === "string" &&
        (
          url.includes("/api/assistant-core/notifications/") ||
          url.includes("/api/assistant-core/background-run")
        );
      const attempts = retryable ? 3 : 1;
      let lastError = null;
      for (let attempt = 1; attempt <= attempts; attempt += 1) {{
        const controller = timeoutMs > 0 ? new AbortController() : null;
        if (controller) {{
          fetchOptions.signal = controller.signal;
        }}
        const timeoutId =
          controller && timeoutMs > 0
            ? window.setTimeout(() => controller.abort(new Error(`Timed out after ${{timeoutMs}}ms`)), timeoutMs)
            : 0;
        try {{
          const response = await fetch(url, fetchOptions);
          const text = await response.text();
          let payload = null;
          try {{
            payload = text ? JSON.parse(text) : null;
          }} catch (_error) {{
            payload = null;
          }}
          if (!response.ok) {{
            const detail = payload?.detail || text || `Request failed: ${{response.status}}`;
            throw new Error(String(detail));
          }}
          if (timeoutId) {{
            window.clearTimeout(timeoutId);
          }}
          return payload;
        }} catch (error) {{
          if (timeoutId) {{
            window.clearTimeout(timeoutId);
          }}
          if (error?.name === "AbortError") {{
            lastError = new Error(`Request timed out after ${{timeoutMs}}ms.`);
          }} else {{
            lastError = error;
          }}
          if (attempt >= attempts) {{
            throw lastError;
          }}
          const delay = 200 * attempt;
          await new Promise((resolve) => window.setTimeout(resolve, delay));
        }}
      }}
      throw lastError || new Error(`${{method}} request failed.`);
    }}

    function stormIconForCondition(text = "") {{
      const lowered = String(text || "").toLowerCase();
      if (lowered.includes("thunder") || lowered.includes("lightning")) return "⛈";
      if (lowered.includes("snow") || lowered.includes("blizzard")) return "❄";
      if (lowered.includes("freezing")) return "❄";
      if (lowered.includes("rain") || lowered.includes("showers")) return "☂";
      if (lowered.includes("fog") || lowered.includes("mist") || lowered.includes("haze") || lowered.includes("smoke")) return "〰";
      if (lowered.includes("cloud")) return "☁";
      if (lowered.includes("clear") || lowered.includes("sunny")) return "☀";
      return "⛅";
    }}

    function updateStormShellWidget() {{
      const button = document.getElementById("storm-weather-button");
      const icon = document.getElementById("storm-weather-icon");
      const temp = document.getElementById("storm-weather-temp");
      if (!button || !icon || !temp) {{
        return;
      }}
      icon.textContent = state.storm.icon || "--";
      temp.textContent = state.storm.temperature || "--°";
      button.title = state.storm.available
        ? `Storm live weather · ${{state.storm.summary || "Live weather"}}`
        : "Storm live weather unavailable";
      button.disabled = false;
    }}

    function dashboardLauncherSummary(data = state.dashboard || {{}}) {{
      const unread = Number(data.assistant_notifications?.summary?.unread || 0);
      const priorities = Number((data.today_board?.priorities || []).length || 0);
      const approvals = Number((data.explainability?.approval_history || []).filter((item) => item.status === "pending").length || 0);
      const total = unread + priorities + approvals;
      return {{
        unread,
        priorities,
        approvals,
        total,
      }};
    }}

    function wealthLauncherSummary(review = state.wealthReview || {{}}) {{
      const summary = review.summary || {{}};
      const tracked = Number(summary.tracked_items || 0);
      const staged = Number(summary.staged_items || 0);
      const researched = Number(summary.researched_items || 0);
      const total = staged || researched || tracked;
      return {{
        tracked,
        staged,
        researched,
        total,
      }};
    }}

    function updateDashboardLauncher(data = state.dashboard || {{}}) {{
      const button = document.getElementById("dashboard-launcher");
      const icon = document.getElementById("dashboard-launcher-icon");
      const count = document.getElementById("dashboard-launcher-count");
      if (!button || !icon || !count) {{
        return;
      }}
      const summary = dashboardLauncherSummary(data);
      const displayCount = summary.total > 99 ? "99+" : String(summary.total || 0);
      icon.textContent = summary.total > 0 ? "◎" : "◌";
      count.textContent = displayCount;
      button.title = summary.total > 0
        ? `Dashboard report · ${{summary.priorities}} priorities, ${{summary.approvals}} approvals, ${{summary.unread}} assistant item(s)`
        : "Dashboard report · No active items are waiting right now.";
      button.disabled = false;
    }}

    function updateWealthLauncher(review = state.wealthReview || {{}}) {{
      const button = document.getElementById("wealth-launcher");
      const icon = document.getElementById("wealth-launcher-icon");
      const count = document.getElementById("wealth-launcher-count");
      if (!button || !icon || !count) {{
        return;
      }}
      const summary = wealthLauncherSummary(review);
      const displayCount = summary.total > 99 ? "99+" : String(summary.total || 0);
      icon.textContent = summary.staged > 0 ? "₿" : summary.researched > 0 ? "ƒ" : "⟡";
      count.textContent = displayCount;
      button.title = summary.total > 0
        ? `Wealth review · ${{summary.staged}} staged, ${{summary.researched}} researching, ${{summary.tracked}} tracked`
        : "Wealth review · No staged Fisk items are waiting right now.";
      button.disabled = false;
    }}

    async function refreshStormWeather(force = false) {{
      const now = Date.now();
      if (state.storm.refreshPromise) {{
        return state.storm.refreshPromise;
      }}
      if (!force && state.storm.lastFetchedAt && now - state.storm.lastFetchedAt < 300000) {{
        return state.storm;
      }}
      state.storm.loading = true;
      state.storm.refreshPromise = (async () => {{
        try {{
          const payload = await loadJSON(force ? "/api/storm-weather?force=true" : "/api/storm-weather");
          const current = payload?.current || {{}};
          const tempF = current?.temperature_f;
          const condition = String(current?.condition || payload?.summary || "Unavailable");
          state.storm = {{
            available: Boolean(payload?.available),
            loading: false,
            temperature: Number.isFinite(tempF) ? `${{tempF}}°` : "--°",
            icon: String(current?.icon || stormIconForCondition(condition) || "--"),
            summary: condition,
            timestamp: String(current?.timestamp || payload?.fetched_at || ""),
            lastFetchedAt: Date.now(),
            refreshPromise: null,
          }};
        }} catch (error) {{
          state.storm = {{
            ...state.storm,
            available: false,
            loading: false,
            temperature: "--°",
            icon: "--",
            summary: "Live weather unavailable.",
            timestamp: "",
            refreshPromise: null,
          }};
          console.warn("Storm weather unavailable", error);
        }}
        updateStormShellWidget();
        return state.storm;
      }})();
      return state.storm.refreshPromise;
    }}

    function chronicleRouteForCapability(capability = "spiritual_timeline") {{
      if (capability === "study_passage") return "/bible";
      if (capability === "prayer_session") return "/prayer";
      return "/chronicle";
    }}

    function chronicleSummaryForCapability(capability = "spiritual_timeline", context = {{}}) {{
      if (capability === "study_passage") {{
        return context.passage
          ? `Sent to Chronicle for study in ${{context.passage}}.`
          : "Sent to Chronicle for passage study.";
      }}
      if (capability === "prayer_session") {{
        return "Sent to Chronicle for prayer.";
      }}
      if (capability === "formation_memory_lookup") {{
        return "Sent to Chronicle to trace the formation thread.";
      }}
      return "Sent to Chronicle to continue the formation thread.";
    }}

    function chroniclePacketContext() {{
      const timeline = state.dashboard?.chronicle_timeline || [];
      const topTheme = state.dashboard?.chronicle_theme_summary?.themes?.[0]?.theme || "";
      const latest = timeline[0] || {{}};
      return {{
        range: "90d",
        theme: topTheme || latest.theme || "",
        prompt: latest.reflection || latest.note || "Continue the formation thread.",
        passage: latest.passage || "",
      }};
    }}

    async function createChronicleLaunchSpec() {{
      const context = chroniclePacketContext();
      let capability = "spiritual_timeline";
      let intentFamily = "faith.formation";
      if (context.passage) {{
        capability = "study_passage";
        intentFamily = "faith.study";
      }}
      if (String(context.prompt || "").toLowerCase().includes("pray")) {{
        capability = "prayer_session";
        intentFamily = "faith.prayer";
      }}
      let requestId = "";
      try {{
        const payload = await loadJSON("/api/chronicle/handoff", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            source_system: "jarvis",
            actor: {{
              actor_id: preferredActorLabel(),
              role: "primary_user",
            }},
            intent_family: intentFamily,
            capability,
            mode: "launch",
            context,
          }}),
        }});
        requestId = String(payload?.request_id || "");
      }} catch (error) {{
        console.warn("Chronicle handoff session unavailable", error);
      }}
      const params = new URLSearchParams();
      params.set("jarvis", "1");
      params.set("jarvisCapability", capability);
      params.set("jarvisSummary", chronicleSummaryForCapability(capability, context));
      params.set("jarvisReturnUrl", window.location.origin);
      params.set("jarvisReturnPacket", "chronicle");
      if (requestId) {{
        params.set("jarvisRequestId", requestId);
      }}
      if (context.passage) params.set("passage", context.passage);
      if (context.theme) params.set("theme", context.theme);
      if (context.prompt) params.set("prompt", context.prompt);
      if (context.range) params.set("range", context.range);
      const path = chronicleRouteForCapability(capability);
      return {{
        requestId,
        capability,
        context,
        summary: chronicleSummaryForCapability(capability, context),
        url: `${{CHRONICLE_APP_BASE_URL}}${{path}}?${{params.toString()}}`,
      }};
    }}

    async function wireChronicleWorkspace() {{
      const frame = document.getElementById("chronicle-workspace-frame");
      const summary = document.getElementById("chronicle-handoff-summary");
      const sendButton = document.getElementById("chronicle-send-button");
      const openButton = document.getElementById("chronicle-open-app");
      if (!frame || !sendButton || !openButton) {{
        return;
      }}

      const applySpec = async (launchExternal = false) => {{
        summary.textContent = "Preparing Chronicle…";
        const spec = await createChronicleLaunchSpec();
        summary.textContent = spec.summary;
        frame.src = spec.url;
        sendButton.textContent = "Sent to Chronicle";
        if (launchExternal) {{
          window.open(spec.url, "_blank", "noopener,noreferrer");
        }}
      }};

      sendButton.addEventListener("click", () => {{
        applySpec(false).catch((error) => {{
          summary.textContent = error?.message || "Chronicle handoff failed.";
        }});
      }});

      openButton.addEventListener("click", () => {{
        applySpec(true).catch((error) => {{
          summary.textContent = error?.message || "Chronicle launch failed.";
        }});
      }});

      await applySpec(false);
    }}

    function freshnessInfo(payload) {{
      return payload?.freshness || {{}};
    }}

    function homeConnectorLive(data = {{}}) {{
      if (typeof data.truth?.home_live === "boolean") {{
        return data.truth.home_live;
      }}
      const adapters = data.environment_status?.adapters || [];
      const home = adapters.find((item) => item.id === "home-assistant");
      return !!home && home.available === true && String(home.mode || "") === "live";
    }}

    function googleConnectorLive(data = {{}}) {{
      const accounts = data.google_workspace?.accounts || data.catalyst_overview?.google_workspace?.accounts || [];
      if (!accounts.length) {{
        return true;
      }}
      return accounts.some((item) => item?.status?.connected === true);
    }}

    function packetVisible(packetId, data = {{}}) {{
      if (packetId === "home") return homeConnectorLive(data);
      if (packetId === "catalyst") return googleConnectorLive(data);
      return true;
    }}

    function treeNodeVisible(node, data = state.dashboard || {{}}) {{
      if (node.scene) return true;
      if (node.packet) return packetVisible(node.packet, data);
      return true;
    }}

    function filteredPacketTree(nodes = packetTreePresets, data = state.dashboard || {{}}) {{
      return nodes.map((node) => {{
        if (Array.isArray(node.children) && node.children.length) {{
          const children = filteredPacketTree(node.children, data);
          if (!children.length) {{
            return null;
          }}
          return {{ ...node, children }};
        }}
        if (!treeNodeVisible(node, data)) {{
          return null;
        }}
        return {{ ...node }};
      }}).filter(Boolean);
    }}

    function findPacketTreePath(nodes, matcher, trail = []) {{
      for (const node of nodes || []) {{
        const nextTrail = [...trail, node.id];
        if (
          node.scene === matcher.scene &&
          matcher.scene
        ) {{
          return nextTrail;
        }}
        if (
          node.packet === matcher.packet &&
          (!matcher.catalystPage || String(node.catalystPage || "") === String(matcher.catalystPage || ""))
        ) {{
          return nextTrail;
        }}
        if (Array.isArray(node.children) && node.children.length) {{
          const nested = findPacketTreePath(node.children, matcher, nextTrail);
          if (nested.length) {{
            return nested;
          }}
        }}
      }}
      return [];
    }}

    function syncPacketTreeToTarget(packetId, options = {{}}) {{
      const path = findPacketTreePath(
        filteredPacketTree(),
        options.scene
          ? {{
              scene: options.scene,
              packet: packetId,
              catalystPage: options.catalystPage || "",
            }}
          : {{
              packet: packetId,
              catalystPage: options.catalystPage || "",
            }}
      );
      if (path.length) {{
        state.packetTreePath = path;
        renderCoreCommandRing();
      }}
    }}

    function packetTreeLevels() {{
      const tree = filteredPacketTree();
      const levels = [{{ title: "Command Root", nodes: tree }}];
      let branch = tree;
      for (let depth = 0; depth < state.packetTreePath.length; depth += 1) {{
        const selectedId = state.packetTreePath[depth];
        const selected = (branch || []).find((node) => node.id === selectedId);
        if (!selected || !Array.isArray(selected.children) || !selected.children.length) {{
          break;
        }}
        levels.push({{ title: selected.label, nodes: selected.children }});
        branch = selected.children;
      }}
      return levels;
    }}

    function visiblePacketPresets() {{
      const data = state.dashboard || {{}};
      return filteredPacketTree(packetTreePresets, data);
    }}

    function renderPacketTreeBranch(nodes = [], depth = 0) {{
      return (nodes || []).map((node) => {{
        const active = state.packetTreePath[depth] === node.id;
        const leaf = !Array.isArray(node.children) || !node.children.length;
        const kind = leaf ? "Launch Surface" : (depth === 0 ? "Domain" : "Route");
        const caret = leaf ? "↗" : (active ? "▾" : "▸");
        const hasActiveChildren = active && !leaf;
        return `
          <div class="packet-tree-node-wrap depth-${{depth}} ${{active ? "active-path" : ""}}">
            <button
              type="button"
              class="packet-tree-node ${{leaf ? "leaf" : "branch"}} ${{active ? "active" : ""}}"
              data-tree-depth="${{depth}}"
              data-tree-node="${{escapeHtml(node.id)}}"
              ${{node.packet ? `data-packet="${{escapeHtml(node.packet)}}"` : ""}}
              ${{node.catalystPage ? `data-catalyst-page="${{escapeHtml(node.catalystPage)}}"` : ""}}
            >
              <span class="packet-tree-node-sigil" aria-hidden="true"></span>
              <span class="packet-tree-node-label">
                <span class="packet-tree-node-title">${{escapeHtml(node.label)}}</span>
                ${{node.description ? `<span class="packet-tree-node-copy">${{escapeHtml(node.description)}}</span>` : ""}}
                <span class="packet-tree-node-kind">${{escapeHtml(kind)}}</span>
              </span>
              <span class="packet-tree-node-caret">${{caret}}</span>
            </button>
            ${{
              hasActiveChildren
                ? `
                  <div class="packet-tree-children">
                    <div class="packet-tree-level-label">${{escapeHtml(node.label)}}</div>
                    <div class="packet-tree-branch depth-${{Math.min(depth + 1, 4)}}">
                      ${{renderPacketTreeBranch(node.children, depth + 1)}}
                    </div>
                  </div>
                `
                : ""
            }}
          </div>
        `;
      }}).join("");
    }}

    function packetTreeRings() {{
      const tree = filteredPacketTree();
      const rings = [{{ title: "Command Root", nodes: tree, depth: 0 }}];
      let branch = tree;
      for (let depth = 0; depth < state.packetTreePath.length; depth += 1) {{
        const selectedId = state.packetTreePath[depth];
        const selected = (branch || []).find((node) => node.id === selectedId);
        if (!selected || !Array.isArray(selected.children) || !selected.children.length) {{
          break;
        }}
        rings.push({{ title: selected.label, nodes: selected.children, depth: depth + 1 }});
        branch = selected.children;
      }}
      return rings;
    }}

    function radialPolarPoint(radius, angleDegrees) {{
      const radians = (angleDegrees - 90) * (Math.PI / 180);
      return {{
        x: 500 + (radius * Math.cos(radians)),
        y: 500 + (radius * Math.sin(radians)),
      }};
    }}

    function radialSectorPath(innerRadius, outerRadius, startAngle, endAngle) {{
      const outerStart = radialPolarPoint(outerRadius, startAngle);
      const outerEnd = radialPolarPoint(outerRadius, endAngle);
      const innerEnd = radialPolarPoint(innerRadius, endAngle);
      const innerStart = radialPolarPoint(innerRadius, startAngle);
      const largeArc = endAngle - startAngle > 180 ? 1 : 0;
      return [
        `M ${{outerStart.x.toFixed(2)}} ${{outerStart.y.toFixed(2)}}`,
        `A ${{outerRadius}} ${{outerRadius}} 0 ${{largeArc}} 1 ${{outerEnd.x.toFixed(2)}} ${{outerEnd.y.toFixed(2)}}`,
        `L ${{innerEnd.x.toFixed(2)}} ${{innerEnd.y.toFixed(2)}}`,
        `A ${{innerRadius}} ${{innerRadius}} 0 ${{largeArc}} 0 ${{innerStart.x.toFixed(2)}} ${{innerStart.y.toFixed(2)}}`,
        "Z",
      ].join(" ");
    }}

    function radialLabelLines(label = "") {{
      const words = String(label || "").trim().split(/\\s+/).filter(Boolean);
      if (!words.length) return [""];
      if (words.length === 1) return words;
      const midpoint = Math.ceil(words.length / 2);
      return [words.slice(0, midpoint).join(" "), words.slice(midpoint).join(" ")].filter(Boolean);
    }}

    function radialLabelMarkup(label, kind, angle, radius) {{
      const point = radialPolarPoint(radius, angle);
      const lines = radialLabelLines(label);
      const lineOffset = lines.length > 1 ? -9 : -2;
      const small = label.length > 14 ? " small" : "";
      return `
        <text class="core-radial-label${{small}}" x="${{point.x.toFixed(2)}}" y="${{point.y.toFixed(2)}}">
          ${{
            lines.map((line, index) => `<tspan x="${{point.x.toFixed(2)}}" dy="${{index === 0 ? lineOffset : 18}}">${{escapeHtml(line)}}</tspan>`).join("")
          }}
        </text>
        <text class="core-radial-kind" x="${{point.x.toFixed(2)}}" y="${{(point.y + 24).toFixed(2)}}">${{escapeHtml(kind)}}</text>
      `;
    }}

    function renderCoreCommandRing() {{
      const target = document.getElementById("core-command-ring");
      const trigger = document.getElementById("core-command-trigger");
      if (!target || !trigger) {{
        return;
      }}
      const open = state.coreCommandOpen;
      target.classList.toggle("open", open);
      target.setAttribute("aria-hidden", open ? "false" : "true");
      trigger.setAttribute("aria-expanded", open ? "true" : "false");
      if (!open) {{
        target.innerHTML = "";
        return;
      }}
      const rings = packetTreeRings().slice(0, 4);
      const ringLayouts = [];
      let branchAngle = -90;
      rings.forEach((ring, ringIndex) => {{
        const nodes = ring.nodes || [];
        const sweep = ringIndex === 0
          ? 320
          : Math.min(164, Math.max(86, nodes.length * 30));
        const start = ringIndex === 0 ? -250 : branchAngle - (sweep / 2);
        const step = nodes.length ? sweep / nodes.length : sweep;
        const innerRadius = 142 + (ringIndex * 108);
        const outerRadius = innerRadius + 92;
        const segments = nodes.map((node, nodeIndex) => {{
          const segmentStart = start + (step * nodeIndex) + 2.4;
          const segmentEnd = start + (step * (nodeIndex + 1)) - 2.4;
          const centerAngle = (segmentStart + segmentEnd) / 2;
          if (state.packetTreePath[ring.depth] === node.id) {{
            branchAngle = centerAngle;
          }}
          return {{
            node,
            centerAngle,
            innerRadius,
            outerRadius,
            startAngle: segmentStart,
            endAngle: segmentEnd,
          }};
        }});
        ringLayouts.push({{ depth: ring.depth, segments }});
      }});
      target.innerHTML = `
        <div class="core-command-ring-shell">
          <svg class="core-command-svg" viewBox="0 0 1000 1000" aria-hidden="true">
            <circle cx="500" cy="500" r="82" fill="rgba(111, 229, 255, 0.08)"></circle>
            ${{
              ringLayouts.map((layout) => layout.segments.map((segment) => {{
                const active = state.packetTreePath[layout.depth] === segment.node.id;
                const leaf = !Array.isArray(segment.node.children) || !segment.node.children.length;
                const kind = leaf
                  ? (segment.node.scene ? "Scene" : "Launch")
                  : (layout.depth === 0 ? "Domain" : "Route");
                return `
                  <g
                    class="core-radial-item ${{leaf ? "leaf" : "branch"}} ${{active ? "active" : ""}}"
                    onclick="coreCommandSvgSelect(${{layout.depth}}, '${{escapeHtml(segment.node.id)}}', '${{escapeHtml(segment.node.packet || "")}}', '${{escapeHtml(segment.node.catalystPage || "")}}', '${{escapeHtml(segment.node.scene || "")}}')"
                  >
                    <path d="${{radialSectorPath(segment.innerRadius, segment.outerRadius, segment.startAngle, segment.endAngle)}}"></path>
                    ${{radialLabelMarkup(segment.node.label, kind, segment.centerAngle, segment.innerRadius + ((segment.outerRadius - segment.innerRadius) * 0.54))}}
                  </g>
                `;
              }}).join("")).join("")
            }}
          </svg>
        </div>
      `;
      const shell = target.querySelector(".core-command-ring-shell");
      if (shell) {{
        shell.insertAdjacentHTML("beforeend", `<div class="core-command-meta">Tap a sector to expand the next ring</div>`);
      }}
    }}

    function toggleCoreCommandTree(forceOpen = null) {{
      state.coreCommandOpen = forceOpen === null ? !state.coreCommandOpen : !!forceOpen;
      if (state.coreCommandOpen) {{
        closeShellOverlays("core-command");
        setActiveOverlay("core-command", {{ path: [...state.packetTreePath] }});
      }} else if (state.activeOverlay?.type === "core-command") {{
        setActiveOverlay("");
      }}
      renderCoreCommandRing();
    }}

    function closeCoreCommandTree() {{
      if (!state.coreCommandOpen) {{
        return;
      }}
      state.coreCommandOpen = false;
      if (state.activeOverlay?.type === "core-command") {{
        setActiveOverlay("");
      }}
      renderCoreCommandRing();
    }}

    function coreCommandTreeSelect(button) {{
      if (!button) {{
        return;
      }}
      const depth = Number.parseInt(button.dataset.treeDepth || "0", 10);
      const nodeId = button.dataset.treeNode || "";
      const packet = button.dataset.packet || "";
      const scene = button.dataset.scene || "";
      const catalystPage = button.dataset.catalystPage || "";
      if (packet || scene) {{
        state.packetTreePath = [...state.packetTreePath.slice(0, depth), nodeId];
        renderCoreCommandRing();
        openPacketTarget({{ packet, catalystPage, scene }});
        return;
      }}
      const currentId = state.packetTreePath[depth] || "";
      if (currentId === nodeId) {{
        state.packetTreePath = state.packetTreePath.slice(0, depth);
      }} else {{
        state.packetTreePath = [...state.packetTreePath.slice(0, depth), nodeId];
      }}
      renderCoreCommandRing();
    }}
    function coreCommandSvgSelect(depth, nodeId, packet = "", catalystPage = "", scene = "") {{
      coreCommandTreeSelect({{
        dataset: {{
          treeDepth: String(depth),
          treeNode: nodeId || "",
          packet: packet || "",
          catalystPage: catalystPage || "",
          scene: scene || "",
        }},
      }});
    }}
    window.toggleCoreCommandTree = toggleCoreCommandTree;
    window.closeCoreCommandTree = closeCoreCommandTree;
    window.coreCommandTreeSelect = coreCommandTreeSelect;
    window.coreCommandSvgSelect = coreCommandSvgSelect;
    window.renderCoreCommandRing = renderCoreCommandRing;

    function degradedInfo(payload) {{
      return payload?.degraded || null;
    }}

    function renderFreshnessBanner(payload, label = "Assistant surface") {{
      const degraded = degradedInfo(payload);
      const freshness = freshnessInfo(payload);
      if (!degraded?.active && !freshness?.fallback) {{
        return "";
      }}
      const age = Number.isFinite(Number(freshness.age_seconds)) ? Number(freshness.age_seconds) : 0;
      const ageLabel = age >= 60 ? `${{Math.round(age / 60)}} min old` : `${{Math.round(age)}} sec old`;
      return `
        <div class="freshness-banner">
          <strong>${{escapeHtml(label)}} is running in degraded mode.</strong><br>
          ${{escapeHtml(degraded?.reason || "JARVIS fell back to the last good snapshot.")}}
          ${{degraded?.detail ? `<br>${{escapeHtml(degraded.detail)}}` : ""}}
          <br>Snapshot age: ${{escapeHtml(ageLabel)}}.
        </div>
      `;
    }}

    function updateRuntimeFreshness(data) {{
      const chip = document.getElementById("runtime-freshness");
      if (!chip) {{
        return;
      }}
      const degraded = degradedInfo(data);
      const freshness = freshnessInfo(data);
      chip.className = "meta-chip hidden";
      chip.textContent = "Live";
      chip.removeAttribute("title");
      if (degraded?.active || freshness?.fallback) {{
        const age = Number.isFinite(Number(freshness.age_seconds)) ? Number(freshness.age_seconds) : 0;
        chip.className = "meta-chip warn";
        chip.textContent = age >= 60 ? `Stale ${{Math.round(age / 60)}}m` : `Stale ${{Math.round(age)}}s`;
        chip.title = degraded?.detail || degraded?.reason || "JARVIS is using the last good snapshot.";
      }} else if (freshness?.cached) {{
        chip.className = "meta-chip";
        chip.textContent = "Cached";
        chip.title = "JARVIS is serving a recent cached summary.";
      }}
      if (chip.textContent === "Live") {{
        chip.classList.add("hidden");
      }}
    }}

    function loadVisionCalibration() {{
      try {{
        const raw = window.localStorage.getItem(VISION_CALIBRATION_KEY);
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        if (!parsed || !Number.isFinite(parsed.pixelsPerUnit) || parsed.pixelsPerUnit <= 0) {{
          return null;
        }}
        return parsed;
      }} catch (_error) {{
        return null;
      }}
    }}

    function saveVisionCalibration(calibration) {{
      state.visionCalibration = calibration;
      try {{
        if (calibration) {{
          window.localStorage.setItem(VISION_CALIBRATION_KEY, JSON.stringify(calibration));
        }} else {{
          window.localStorage.removeItem(VISION_CALIBRATION_KEY);
        }}
      }} catch (_error) {{
        return;
      }}
    }}

    function loadAssistantSurfaceKey() {{
      try {{
        return window.localStorage.getItem(ASSISTANT_SURFACE_KEY) || "";
      }} catch (_error) {{
        return "";
      }}
    }}

    function saveAssistantSurfaceKey(value) {{
      state.lastAssistantSurfaceKey = value || "";
      try {{
        if (value) {{
          window.localStorage.setItem(ASSISTANT_SURFACE_KEY, value);
        }} else {{
          window.localStorage.removeItem(ASSISTANT_SURFACE_KEY);
        }}
      }} catch (_error) {{
        return;
      }}
    }}

    function mergeDashboardState(nextData) {{
      const previous = state.dashboard || {{}};
      const next = nextData || {{}};
      state.dashboard = {{
        ...previous,
        ...next,
        chamber_home: next.chamber_home || previous.chamber_home || null,
        today_board: next.today_board || previous.today_board || null,
        cadence_review: next.cadence_review || previous.cadence_review || null,
        open_loops: next.open_loops || previous.open_loops || null,
        cognitive: next.cognitive || previous.cognitive || null,
        assistant_notifications: next.assistant_notifications || previous.assistant_notifications || null,
        mission_control: next.mission_control || previous.mission_control || null,
      }};
      state.missionControl = state.dashboard.mission_control || null;
      if (!state.activeMissionId) {{
        const firstMission = Array.isArray(state.missionControl?.active_missions) ? state.missionControl.active_missions[0] : null;
        state.activeMissionId = firstMission?.mission_id || "";
      }}
      return state.dashboard;
    }}

    function setModalVisibility(isOpen) {{
      const modal = document.getElementById("modal-layer");
      if (!modal) {{
        return;
      }}
      modal.classList.toggle("open", !!isOpen);
      modal.setAttribute("aria-hidden", isOpen ? "false" : "true");
    }}

    function setActiveOverlay(type = "", payload = null) {{
      state.activeOverlay = type
        ? {{ type, payload: payload || {{}} }}
        : {{ type: "", payload: null }};
      document.body.dataset.activeOverlay = state.activeOverlay.type || "none";
    }}

    function closeShellOverlays(except = "") {{
      if (except !== "modal" && state.packet) {{
        closePacket();
      }}
      if (except !== "scene" && state.activeScene) {{
        closeScene();
      }}
      if (except !== "mode") {{
        closeModePanel();
      }}
      if (except !== "context") {{
        closeContextPanel();
      }}
      if (except !== "core-command") {{
        closeCoreCommandTree();
      }}
    }}

    function chamberHomeModeActive() {{
      return document.body.dataset.shellLayout === "quiet-home" && !state.layoutEditMode;
    }}

    function packetStripAllowed() {{
      return Boolean(state.packet);
    }}

    function triageSummaryCanFloat() {{
      return !chamberHomeModeActive();
    }}

    function defaultTriageSummaryPlacement() {{
      const shell = document.getElementById("core-home-summary");
      const cluster = document.getElementById("core-cluster");
      const width = chamberHomeModeActive()
        ? Math.min(980, Math.max(760, Number(shell?.offsetWidth || 900)))
        : Math.min(360, Math.max(320, Number(shell?.offsetWidth || 360)));
      const height = Math.min(420, Math.max(220, Number(shell?.offsetHeight || 290)));
      let left = 28;
      let top = 168;
      if (chamberHomeModeActive()) {{
        return {{
          left: null,
          top: null,
          width,
          height: null,
        }};
      }}
      if (document.body.dataset.coreDock === "corner" && cluster) {{
        const rect = cluster.getBoundingClientRect();
        left = rect.left;
        top = rect.bottom + 12;
      }} else if (cluster) {{
        const rect = cluster.getBoundingClientRect();
        left = Math.max(24, rect.left - width - 24);
        top = Math.max(92, rect.top + 44);
      }}
      return {{
        ...clampFloatingBox(left, top, width, height),
        width,
        height,
      }};
    }}

    function applyTriageSummaryVisibility() {{
      const shell = document.getElementById("core-home-summary");
      const launcher = document.getElementById("triage-summary-launcher");
      if (!shell) return;
      shell.classList.toggle("hidden-window", !state.triageSummaryVisible);
      shell.setAttribute("aria-hidden", state.triageSummaryVisible ? "false" : "true");
      if (launcher) {{
        launcher.classList.toggle("active", state.triageSummaryVisible);
        launcher.setAttribute("aria-pressed", state.triageSummaryVisible ? "true" : "false");
        launcher.title = state.triageSummaryVisible ? "Hide triage sidecar" : "Open triage sidecar";
      }}
    }}

    function openTriageSummary() {{
      state.triageSummaryVisible = true;
      if (chamberHomeModeActive()) {{
        state.windowPlacements.triageSummary = defaultTriageSummaryPlacement();
      }} else if (!state.windowPlacements.triageSummary?.left && !state.windowPlacements.triageSummary?.top) {{
        state.windowPlacements.triageSummary = defaultTriageSummaryPlacement();
      }}
      state.windowStates.triageSummary.minimized = false;
      applyTriageSummaryVisibility();
      applyWindowFrame("triageSummary");
      bringWindowToFront("triageSummary");
    }}

    function closeTriageSummary() {{
      state.triageSummaryVisible = false;
      applyTriageSummaryVisibility();
      if (state.activeWindowId === "triageSummary") {{
        state.activeWindowId = "";
      }}
    }}

    function ensureFloatingModalPlacement(packetId = "", options = {{}}) {{
      const modal = document.querySelector("#modal-layer .modal");
      if (!modal || !packetId || window.innerWidth <= 1080) {{
        return;
      }}
      const existing = state.modalPlacements?.[packetId];
      if (existing?.left != null && existing?.top != null && !options.force) {{
        return;
      }}
      const rect = modal.getBoundingClientRect();
      const width = Math.min(Math.max(520, Number(options.width || rect.width || 920)), window.innerWidth - 32);
      const height = Math.min(Math.max(340, Number(options.height || rect.height || 640)), window.innerHeight - 96);
      const defaultLeft = Number.isFinite(options.left)
        ? Number(options.left)
        : Math.max(24, Math.round(window.innerWidth * 0.54) - Math.round(width * 0.5));
      const defaultTop = Number.isFinite(options.top)
        ? Number(options.top)
        : Math.max(88, Math.round(window.innerHeight * 0.16));
      const next = clampFloatingBox(defaultLeft, defaultTop, width, height);
      state.modalPlacements[packetId] = {{
        left: next.left,
        top: next.top,
        width,
        height,
      }};
    }}

    function getWindowShell(windowId) {{
      if (windowId === "triageSummary") return document.getElementById("core-home-summary");
      if (windowId === "scene") return document.querySelector("#scene-stage .scene-shell");
      if (windowId === "mode") return document.getElementById("mode-panel");
      if (windowId === "context") return document.getElementById("context-panel");
      if (windowId === "modal") return document.querySelector("#modal-layer .modal");
      return null;
    }}

    function getWindowLayer(windowId) {{
      if (windowId === "scene") return document.getElementById("scene-stage");
      if (windowId === "modal") return document.getElementById("modal-layer");
      return getWindowShell(windowId);
    }}

    function bringWindowToFront(windowId = "") {{
      const shell = getWindowShell(windowId);
      if (!shell) return;
      state.activeWindowId = windowId;
      state.windowZCounter += 2;
      const base = state.windowZCounter;
      if (windowId === "modal" || windowId === "scene") {{
        const layer = getWindowLayer(windowId);
        if (layer) layer.style.zIndex = String(base);
        shell.style.zIndex = String(base + 1);
      }} else {{
        shell.style.zIndex = String(base + 1);
      }}
    }}

    function applyWindowFrame(windowId = "") {{
      const shell = getWindowShell(windowId);
      if (!shell) return;
      const windowState = state.windowStates?.[windowId] || {{}};
      shell.classList.toggle("minimized", !!windowState.minimized);
      shell.classList.toggle("maximized", !!windowState.maximized);
      if (windowId === "triageSummary" || windowId === "mode" || windowId === "context" || windowId === "scene") {{
        const placement = state.windowPlacements?.[windowId] || {{}};
        const shouldFloat =
          !windowState.maximized &&
          Number.isFinite(Number(placement.left)) &&
          Number.isFinite(Number(placement.top)) &&
          (windowId !== "triageSummary" || (state.triageSummaryVisible && triageSummaryCanFloat()));
        shell.classList.toggle("floating", shouldFloat);
        if (shouldFloat) {{
          shell.style.left = `${{Number(placement.left)}}px`;
          shell.style.top = `${{Number(placement.top)}}px`;
          shell.style.width = placement.width ? `${{Number(placement.width)}}px` : "";
          if ((windowId === "scene" || windowId === "triageSummary") && placement.height) {{
            shell.style.height = `${{Number(placement.height)}}px`;
          }}
        }} else if (!windowState.maximized) {{
          shell.classList.remove("floating");
          shell.style.removeProperty("left");
          shell.style.removeProperty("top");
          if (windowId !== "triageSummary" || triageSummaryCanFloat()) {{
            shell.style.removeProperty("width");
          }}
          if (windowId === "scene" || windowId === "triageSummary") {{
            shell.style.removeProperty("height");
          }}
        }}
      }} else if (windowId === "modal") {{
        applyModalPlacement();
      }}
    }}

    function toggleWindowMinimized(windowId = "") {{
      if (!state.windowStates?.[windowId]) return;
      state.windowStates[windowId].minimized = !state.windowStates[windowId].minimized;
      applyWindowFrame(windowId);
      bringWindowToFront(windowId);
    }}

    function toggleWindowMaximized(windowId = "") {{
      if (!state.windowStates?.[windowId]) return;
      state.windowStates[windowId].maximized = !state.windowStates[windowId].maximized;
      if (state.windowStates[windowId].maximized) {{
        state.windowStates[windowId].minimized = false;
      }}
      applyWindowFrame(windowId);
      bringWindowToFront(windowId);
    }}

    function startWindowInteraction(windowId, event) {{
      if (event.button !== 0) return;
      const shell = getWindowShell(windowId);
      if (!shell) return;
      if (event.target.closest("button, input, select, textarea, summary, a, [role='button']")) return;
      const windowState = state.windowStates?.[windowId] || {{}};
      if (windowState.maximized) {{
        bringWindowToFront(windowId);
        return;
      }}
      const rect = shell.getBoundingClientRect();
      if (windowId === "modal" && state.packet) {{
        state.modalPlacements[state.packet] = {{ left: rect.left, top: rect.top, width: rect.width, height: rect.height }};
        applyModalPlacement();
      }} else if (windowId === "triageSummary" || windowId === "mode" || windowId === "context" || windowId === "scene") {{
        state.windowPlacements[windowId] = {{ left: rect.left, top: rect.top, width: rect.width, height: rect.height }};
      }}
      bringWindowToFront(windowId);
      state.dragState = {{
        target: "window",
        windowId,
        mode: "drag",
        originX: event.clientX,
        originY: event.clientY,
        left: rect.left,
        top: rect.top,
        width: rect.width,
        height: rect.height,
      }};
      document.body.classList.add("dragging-layout");
      event.preventDefault();
      event.stopPropagation();
    }}

    async function maybeAutoOpenCadenceReview(notificationsPayload) {{
      const notifications = notificationsPayload || state.dashboard?.assistant_notifications || {{}};
      const items = Array.isArray(notifications.items) ? notifications.items : [];
      const reviewItem = items.find((item) =>
        (item.packet || "") === "review" &&
        ["unseen", "surfaced"].includes((item.status || "unseen")) &&
        (item.priority_class || "normal") !== "quiet" &&
        (item.surface_key || "") &&
        state.lastAssistantSurfaceKey !== (item.surface_key || "")
      );
      if (!reviewItem) {{
        return false;
      }}
      if (document.body.classList.contains("modal-open") || state.packet) {{
        return false;
      }}
      const actor = preferredActorLabel();
      saveAssistantSurfaceKey(reviewItem.surface_key || "");
      state.lastBriefing = reviewItem.detail || "JARVIS prepared the next review loop.";
      document.getElementById("last-jarvis-text").textContent = state.lastBriefing;
      syncTranscriptRail();
      openPacket("review");
      if (reviewItem.notification_id) {{
        loadJSON(`/api/assistant-core/notifications/${{encodeURIComponent(reviewItem.notification_id)}}`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ actor, status: "opened" }}),
        }}).catch(() => null);
      }}
      return true;
    }}

    function formatMeasurement(value, unit) {{
      if (!Number.isFinite(value)) return `-- ${{unit}}`;
      const precision = value >= 10 ? 1 : 2;
      return `${{value.toFixed(precision)}} ${{unit}}`;
    }}

    function getVisionSelectionMetrics(video) {{
      if (!video || !state.visionCropRect) return null;
      const width = video.videoWidth || 0;
      const height = video.videoHeight || 0;
      const displayWidth = video.clientWidth || width;
      const displayHeight = video.clientHeight || height;
      if (!width || !height || !displayWidth || !displayHeight) return null;
      const scaleX = width / displayWidth;
      const scaleY = height / displayHeight;
      const pixelWidth = Math.max(1, state.visionCropRect.width * scaleX);
      const pixelHeight = Math.max(1, state.visionCropRect.height * scaleY);
      const majorAxisPixels = Math.max(pixelWidth, pixelHeight);
      const diagonalPixels = Math.hypot(pixelWidth, pixelHeight);
      return {{
        pixelWidth,
        pixelHeight,
        majorAxisPixels,
        diagonalPixels,
      }};
    }}

    function renderVisionCalibrationSummary(extraMessage = "") {{
      const summary = document.getElementById("vision-calibration-summary");
      if (!summary) return;
      const calibration = state.visionCalibration;
      if (!calibration) {{
        summary.textContent = extraMessage || "No calibration yet. Place a ruler on the stage, turn crop on, drag across a known span, then calibrate.";
        return;
      }}
      const detail = `Calibrated at ${{calibration.referenceLength}} ${{calibration.unit}} across ${{Math.round(calibration.referencePixels)}} px (${{calibration.pixelsPerUnit.toFixed(2)}} px per ${{calibration.unit}}).`;
      summary.textContent = extraMessage ? `${{detail}} ${{extraMessage}}` : detail;
    }}

    function stopVisionPreview() {{
      if (state.visionStream) {{
        state.visionStream.getTracks().forEach((track) => track.stop());
        state.visionStream = null;
      }}
      const video = document.getElementById("vision-live-video");
      if (video) {{
        video.srcObject = null;
      }}
      const crop = document.getElementById("vision-crop-box");
      if (crop) {{
        crop.classList.remove("active");
      }}
    }}

    function destroyModelForgeScene() {{
      const sceneState = state.modelForgeScene;
      if (!sceneState) return;
      if (sceneState.raf) cancelAnimationFrame(sceneState.raf);
      if (sceneState.resizeObserver) sceneState.resizeObserver.disconnect();
      if (sceneState.renderer) sceneState.renderer.dispose();
      if (sceneState.mount) sceneState.mount.innerHTML = "";
      state.modelForgeScene = null;
    }}

    function initModelForgeScene(mountId) {{
      destroyModelForgeScene();
      const mount = document.getElementById(mountId);
      if (!mount) return null;
      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0x03070d);
      const camera = new THREE.PerspectiveCamera(44, 1, 0.1, 2000);
      const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      mount.innerHTML = "";
      mount.appendChild(renderer.domElement);

      const ambient = new THREE.AmbientLight(0xc7f7ff, 1.3);
      const key = new THREE.DirectionalLight(0x8de8ff, 1.55);
      key.position.set(140, 180, 120);
      const fill = new THREE.DirectionalLight(0x5f8dff, 0.42);
      fill.position.set(-120, 90, -60);
      const rim = new THREE.DirectionalLight(0x66dbff, 0.34);
      rim.position.set(0, 60, -140);
      scene.add(ambient, key, fill, rim);

      const grid = new THREE.GridHelper(220, 22, 0x285f83, 0x102130);
      grid.position.y = -0.01;
      if (Array.isArray(grid.material)) {{
        grid.material.forEach((material) => {{
          material.transparent = true;
          material.opacity = 0.28;
        }});
      }} else if (grid.material) {{
        grid.material.transparent = true;
        grid.material.opacity = 0.28;
      }}
      scene.add(grid);

      const modelGroup = new THREE.Group();
      scene.add(modelGroup);

      let pointerDown = false;
      let lastX = 0;
      let lastY = 0;
      let orbitTheta = 0.85;
      let orbitPhi = 0.88;
      let orbitRadius = 180;
      const target = new THREE.Vector3(0, 26, 0);

      function clampOrbit() {{
        orbitPhi = Math.max(0.15, Math.min(Math.PI - 0.15, orbitPhi));
        orbitRadius = Math.max(40, Math.min(420, orbitRadius));
      }}

      function positionCamera() {{
        clampOrbit();
        camera.position.set(
          target.x + orbitRadius * Math.sin(orbitPhi) * Math.sin(orbitTheta),
          target.y + orbitRadius * Math.cos(orbitPhi),
          target.z + orbitRadius * Math.sin(orbitPhi) * Math.cos(orbitTheta),
        );
        camera.lookAt(target);
      }}

      function resize() {{
        const width = mount.clientWidth || 640;
        const height = mount.clientHeight || 420;
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
      }}

      mount.addEventListener("pointerdown", (event) => {{
        pointerDown = true;
        lastX = event.clientX;
        lastY = event.clientY;
      }});
      window.addEventListener("pointerup", () => {{
        pointerDown = false;
      }});
      window.addEventListener("pointermove", (event) => {{
        if (!pointerDown || state.modelForgeScene?.mount !== mount) return;
        const dx = event.clientX - lastX;
        const dy = event.clientY - lastY;
        lastX = event.clientX;
        lastY = event.clientY;
        orbitTheta -= dx * 0.01;
        orbitPhi += dy * 0.01;
        positionCamera();
      }});
      mount.addEventListener("wheel", (event) => {{
        event.preventDefault();
        orbitRadius += event.deltaY * 0.08;
        positionCamera();
      }}, {{ passive: false }});

      const resizeObserver = new ResizeObserver(() => resize());
      resizeObserver.observe(mount);

      function animate() {{
        renderer.render(scene, camera);
        if (state.modelForgeScene?.mount === mount) {{
          state.modelForgeScene.raf = requestAnimationFrame(animate);
        }}
      }}

      resize();
      positionCamera();
      state.modelForgeScene = {{ mount, scene, camera, renderer, modelGroup, resizeObserver, raf: requestAnimationFrame(animate), target }};
      return state.modelForgeScene;
    }}

    async function loadModelForgePackage(packageId) {{
      const details = document.getElementById("model-forge-details-content");
      const downloads = document.getElementById("model-forge-details-actions");
      const script = document.getElementById("model-forge-script");
      const status = document.getElementById("model-forge-viewer-status");
      const placeholder = document.getElementById("model-forge-empty");
      const overlayName = document.getElementById("model-forge-overlay-name");
      const overlayKind = document.getElementById("model-forge-overlay-kind");
      const overlayStatus = document.getElementById("model-forge-overlay-status");
      const overlayCopy = document.getElementById("model-forge-overlay-copy");
      const overlayFamily = document.getElementById("model-forge-overlay-family");
      const overlayPrinter = document.getElementById("model-forge-overlay-printer");
      const overlayProfile = document.getElementById("model-forge-overlay-profile");
      const overlayMaterial = document.getElementById("model-forge-overlay-material");
      if (!packageId || !details || !downloads || !script || !status) return;
      status.textContent = "Loading model forge package…";
      const response = await fetch(`/api/model-forge/package/${{encodeURIComponent(packageId)}}`, {{ cache: "no-store" }});
      if (!response.ok) {{
        const error = await response.json().catch(() => ({{ detail: "Failed to load package." }}));
        status.textContent = error.detail || "Failed to load package.";
        return;
      }}
      const pkg = await response.json();
      details.innerHTML = `
        <div class="metric"><strong>${{escapeHtml(pkg.part_name || "Part")}}</strong></div>
        <div class="metric"><span class="tag">${{escapeHtml(pkg.export_status || "cad-package")}}</span></div>
        <div class="metric">${{escapeHtml(pkg.export_detail || "No export detail available.")}}</div>
        <div class="metric"><strong>Family</strong><span class="muted">${{escapeHtml(pkg.family || "unspecified")}}</span></div>
        <div class="metric"><strong>Printer</strong><span class="muted">${{escapeHtml(pkg.printer_id || "unassigned")}}</span></div>
        <div class="metric"><strong>Profile</strong><span class="muted">${{escapeHtml(pkg.profile_name || "unassigned")}}</span></div>
        <div class="metric"><strong>Material</strong><span class="muted">${{escapeHtml(pkg.material || "unassigned")}}</span></div>
        <div class="metric"><strong>Artifact Dir</strong><span class="muted">${{escapeHtml(pkg.artifact_dir || "Not recorded")}}</span></div>
      `;
      downloads.innerHTML = `
        <a href="/api/model-forge/package/${{encodeURIComponent(packageId)}}/download/stl">Download STL</a>
        <a href="/api/model-forge/package/${{encodeURIComponent(packageId)}}/download/step">Download STEP</a>
        <a href="/api/model-forge/package/${{encodeURIComponent(packageId)}}/download/3mf">Download 3MF</a>
        <a href="/api/model-forge/package/${{encodeURIComponent(packageId)}}/download/slicer-pack">Download Slicer Pack</a>
        <button type="button" id="model-forge-open-slicer" data-package-id="${{escapeHtml(packageId)}}">Open In Slicer</button>
      `;
      script.textContent = pkg.openscad_stub || "No OpenSCAD source recorded.";
      if (overlayName) overlayName.textContent = pkg.part_name || "Unnamed package";
      if (overlayKind) overlayKind.textContent = pkg.export_status || "cad-package";
      if (overlayStatus) overlayStatus.textContent = pkg.model_path ? "Model ready" : "Metadata only";
      if (overlayCopy) overlayCopy.textContent = pkg.export_detail || "Generated package metadata is available. Export and slicer handoff will show up here as assets become ready.";
      if (overlayFamily) overlayFamily.textContent = pkg.family || "unspecified";
      if (overlayPrinter) overlayPrinter.textContent = pkg.printer_id || "unassigned";
      if (overlayProfile) overlayProfile.textContent = pkg.profile_name || "unassigned";
      if (overlayMaterial) overlayMaterial.textContent = pkg.material || "unassigned";
      if (!pkg.model_path) {{
        destroyModelForgeScene();
        if (placeholder) placeholder.style.display = "grid";
        status.textContent = "This package has source and metadata, but no exported STL yet.";
        return;
      }}
      const sceneState = initModelForgeScene("model-forge-viewer");
      if (!sceneState) return;
      if (placeholder) placeholder.style.display = "none";
      status.textContent = "Loading STL…";
      const loader = new STLLoader();
      loader.load(
        `/api/model-forge/package/${{encodeURIComponent(packageId)}}/model`,
        (geometry) => {{
          const material = new THREE.MeshPhysicalMaterial({{
            color: 0x78f0ff,
            metalness: 0.08,
            roughness: 0.3,
            transmission: 0.02,
            clearcoat: 0.6,
            clearcoatRoughness: 0.3,
          }});
          while (sceneState.modelGroup.children.length) {{
            const child = sceneState.modelGroup.children.pop();
            if (child?.geometry) child.geometry.dispose?.();
            if (child?.material) child.material.dispose?.();
          }}
          geometry.computeBoundingBox();
          geometry.computeVertexNormals();
          geometry.center();
          const mesh = new THREE.Mesh(geometry, material);
          sceneState.modelGroup.add(mesh);
          const bounds = geometry.boundingBox;
          const size = new THREE.Vector3();
          bounds.getSize(size);
          const maxDim = Math.max(size.x, size.y, size.z, 1);
          const distance = maxDim * 2.4;
          sceneState.target.set(0, Math.max(size.y * 0.15, 6), 0);
          sceneState.camera.position.set(distance * 0.8, distance * 0.65, distance);
          sceneState.camera.lookAt(sceneState.target);
          status.textContent = `Viewing STL · ${{size.x.toFixed(1)}} x ${{size.y.toFixed(1)}} x ${{size.z.toFixed(1)}} mm`;
        }},
        undefined,
        (error) => {{
          console.error(error);
          if (placeholder) placeholder.style.display = "grid";
          status.textContent = "STL failed to load.";
        }},
      );
    }}

    function wireModelForgePacket() {{
      const select = document.getElementById("model-forge-package");
      const refresh = document.getElementById("model-forge-refresh");
      const family = document.getElementById("model-forge-family");
      const printer = document.getElementById("model-forge-printer");
      const profile = document.getElementById("model-forge-profile");
      const slicer = document.getElementById("model-forge-slicer");
      const generate = document.getElementById("model-forge-generate");
      const output = document.getElementById("model-forge-generation-output");
      const conceptType = document.getElementById("model-forge-concept-type");
      const conceptSilhouette = document.getElementById("model-forge-concept-silhouette");
      const conceptGoals = document.getElementById("model-forge-concept-goals");
      const conceptConstraints = document.getElementById("model-forge-concept-constraints");
      const conceptCapture = document.getElementById("model-forge-concept-capture");
      const conceptReference = document.getElementById("model-forge-concept-reference");
      const conceptPrompt = document.getElementById("model-forge-concept-prompt");
      const conceptSend = document.getElementById("model-forge-concept-send");
      const conceptApply = document.getElementById("model-forge-concept-apply");
      const conceptStatus = document.getElementById("model-forge-concept-status");
      const conceptBrief = document.getElementById("model-forge-concept-brief");
      const conceptTranscript = document.getElementById("model-forge-concept-transcript");
      const variantStrip = document.getElementById("model-forge-variant-strip");
      const silhouetteName = document.getElementById("model-forge-silhouette-name");
      const silhouetteBadge = document.getElementById("model-forge-silhouette-badge");
      const silhouetteArt = document.getElementById("model-forge-silhouette-art");
      const silhouetteDescription = document.getElementById("model-forge-silhouette-description");
      const silhouettePrint = document.getElementById("model-forge-silhouette-print");
      const silhouetteUse = document.getElementById("model-forge-silhouette-use");
      const silhouetteCharacter = document.getElementById("model-forge-silhouette-character");
      const tabs = Array.from(document.querySelectorAll(".model-forge-tab"));
      const panels = Array.from(document.querySelectorAll(".model-forge-tab-panel"));
      if (!select) return;

      const silhouetteCatalog = {{
        "calm-spiral": {{
          label: "Calm spiral",
          badge: "Sculpture",
          description: "A balanced rising gesture with an easy center of gravity. Good for sculptures and decor that want motion without drama.",
          print: "Stable base, low support",
          use: "Sculpture / decor",
          character: "Calm",
          art: `url("data:image/svg+xml,${{encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 180'><path d='M124 18c-32 22-54 44-52 73 1 18 13 35 30 44 24 12 58 8 76-10 16-16 12-40-5-55-10-9-27-14-41-11-12 3-18 14-15 23 4 11 19 15 30 12 10-3 18-12 21-22' fill='none' stroke='rgba(190,243,255,0.92)' stroke-width='10' stroke-linecap='round'/><path d='M118 128c-4 12-11 21-20 30' fill='none' stroke='rgba(105,210,255,0.78)' stroke-width='8' stroke-linecap='round'/></svg>`)}}")`,
        }},
        "tense-twist": {{
          label: "Tense twist",
          badge: "Sculpture",
          description: "A sharper torsion language with a taut spine. Good when the form should feel energetic, athletic, or slightly dangerous.",
          print: "Moderate support",
          use: "Sculpture / statement object",
          character: "Tense",
          art: `url("data:image/svg+xml,${{encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 180'><path d='M118 18c28 24 36 46 19 70-16 23-43 31-49 53-4 14 1 26 14 38' fill='none' stroke='rgba(194,244,255,0.92)' stroke-width='12' stroke-linecap='round'/><path d='M96 24c-20 20-26 42-16 63 9 19 29 28 37 45 9 18 5 31-10 43' fill='none' stroke='rgba(95,201,255,0.78)' stroke-width='8' stroke-linecap='round'/></svg>`)}}")`,
        }},
        "split-ribbon": {{
          label: "Split ribbon",
          badge: "Custom form",
          description: "Two coordinated ribbons that separate and rejoin visually. Strong for sculptural centerpieces and expressive object studies.",
          print: "Balanced segments",
          use: "Sculpture / hero object",
          character: "Expressive",
          art: `url("data:image/svg+xml,${{encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 180'><path d='M88 150c12-18 10-42 4-60-6-20-17-39-9-68' fill='none' stroke='rgba(194,244,255,0.92)' stroke-width='11' stroke-linecap='round'/><path d='M150 150c-10-18-11-36-6-55 6-24 18-41 11-73' fill='none' stroke='rgba(95,201,255,0.84)' stroke-width='10' stroke-linecap='round'/><path d='M94 78c18-9 36-8 52 5' fill='none' stroke='rgba(230,250,255,0.62)' stroke-width='5' stroke-linecap='round'/></svg>`)}}")`,
        }},
        monolith: {{
          label: "Monolith",
          badge: "Display form",
          description: "A grounded vertical mass with restrained curvature. Good for props, decor, and symbolic pieces that need authority more than flourish.",
          print: "Low risk print",
          use: "Prop / decor",
          character: "Solid",
          art: `url("data:image/svg+xml,${{encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 180'><path d='M104 20h32c8 0 14 6 14 14v104c0 13-10 22-26 22s-26-9-26-22V34c0-8 6-14 14-14z' fill='rgba(190,243,255,0.84)'/><path d='M124 20v140' stroke='rgba(255,255,255,0.45)' stroke-width='3'/></svg>`)}}")`,
        }},
        "racket-frame": {{
          label: "Racket frame",
          badge: "Prototype sport",
          description: "A printable sports-frame concept with a believable handle, throat, and head language. Good for prototype sporting goods and display mockups.",
          print: "Sectioned assembly",
          use: "Sporting good",
          character: "Athletic",
          art: `url("data:image/svg+xml,${{encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 180'><ellipse cx='132' cy='66' rx='46' ry='34' fill='none' stroke='rgba(194,244,255,0.92)' stroke-width='10'/><path d='M112 90l-18 56M152 90l18 56' stroke='rgba(95,201,255,0.88)' stroke-width='8' stroke-linecap='round'/><rect x='108' y='146' width='44' height='14' rx='6' fill='rgba(190,243,255,0.84)'/></svg>`)}}")`,
        }},
        "organic-shell": {{
          label: "Organic shell",
          badge: "Organic object",
          description: "A hollowed protective volume that feels grown more than machined. Good for nature-derived forms and wrapped reconstructions.",
          print: "Shell thickness critical",
          use: "Organic reconstruction",
          character: "Natural",
          art: `url("data:image/svg+xml,${{encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 180'><path d='M68 108c0-42 28-70 68-70 24 0 48 14 60 38-6 44-38 76-86 76-24 0-42-16-42-44z' fill='rgba(190,243,255,0.84)'/><path d='M108 54c18 8 35 24 45 46' fill='none' stroke='rgba(255,255,255,0.46)' stroke-width='4' stroke-linecap='round'/></svg>`)}}")`,
        }},
        "display-prop": {{
          label: "Display prop",
          badge: "Prop / decor",
          description: "A staged hero form meant to read well on a shelf or in hand. Good for decor, cosplay pieces, and symbolic objects that need clean silhouette first.",
          print: "Chunky safe print",
          use: "Prop / decor",
          character: "Iconic",
          art: `url("data:image/svg+xml,${{encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 180'><path d='M78 146l28-102h28l28 102h-84z' fill='rgba(190,243,255,0.84)'/><path d='M100 102h40' stroke='rgba(255,255,255,0.45)' stroke-width='4' stroke-linecap='round'/></svg>`)}}")`,
        }},
        "organic-reconstruction": {{
          label: "Organic reconstruction",
          badge: "Reconstruction",
          description: "A rebuilt object language guided by observed contours, asymmetry, and proportion. Best when Vision gives us a real-world form to reinterpret faithfully.",
          print: "Support varies by overhang",
          use: "Observed form",
          character: "Reconstructed",
          art: `url("data:image/svg+xml,${{encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 180'><path d='M66 110c4-34 28-58 62-66 30-8 56 2 74 28-4 34-26 60-58 70-36 12-70 0-78-32z' fill='rgba(190,243,255,0.84)'/><path d='M94 78c12 2 24 10 34 20 11 11 18 25 20 39' fill='none' stroke='rgba(255,255,255,0.44)' stroke-width='4' stroke-linecap='round'/></svg>`)}}")`,
        }},
      }};

      const familyProfiles = {{
        bracket: {{
          label: "Bracket workflow",
          note: "Bias toward hole spacing, plate thickness, bend radius, and load path.",
          part: "Garden bench bracket",
          dimensions: "hole spacing 110 mm, plate width 30 mm, thickness 8 mm, bend radius 12 mm",
          constraints: "Preserve mounting geometry, add drainage, keep corners softened for fatigue resistance.",
        }},
        enclosure: {{
          label: "Enclosure workflow",
          note: "Bias toward outer size, wall thickness, lid fit, cable exits, and screw pattern.",
          part: "Sensor enclosure",
          dimensions: "outer length 120 mm, width 80 mm, height 40 mm, wall thickness 3 mm",
          constraints: "Keep lid printable, allow cable exit, leave room for fasteners and board clearance.",
        }},
        spacer: {{
          label: "Spacer workflow",
          note: "Bias toward exact height, inner diameter, outer diameter, and stable concentric geometry.",
          part: "Fixture spacer",
          dimensions: "outer diameter 18 mm, inner diameter 6.2 mm, height 12 mm",
          constraints: "Maintain tight axial height, keep bore clean, no supports if possible.",
        }},
        mount: {{
          label: "Mount workflow",
          note: "Bias toward footprint, riser height, hole pattern, and surface attachment.",
          part: "Camera mount",
          dimensions: "base length 90 mm, width 40 mm, thickness 6 mm, riser height 35 mm",
          constraints: "Preserve fastener access, keep base stable, strengthen the riser-to-base transition.",
        }},
        "custom-form": {{
          label: "Custom-form workflow",
          note: "Bias toward silhouette, stance, balance, and printability rather than fastener geometry.",
          part: "Concept object",
          dimensions: "overall height 120 mm, width 70 mm, depth 45 mm, base height 10 mm, ribbon thickness 6 mm",
          constraints: "Keep the base stable, protect thin sections, and bias toward elegant print-safe transitions.",
        }},
      }};

      async function ensureModelForgeOptions() {{
        if (state.modelForgeOptions) return state.modelForgeOptions;
        const response = await fetch("/api/workshop-machine-options", {{ cache: "no-store" }});
        if (!response.ok) {{
          throw new Error("Failed to load machine options.");
        }}
        state.modelForgeOptions = await response.json();
        return state.modelForgeOptions;
      }}

      function refreshModelForgeProfileOptions() {{
        if (!printer || !profile || !state.modelForgeOptions) return;
        const printers = state.modelForgeOptions.printers || [];
        const selectedPrinter = printers.find((item) => item.id === printer.value) || printers[0];
        const profiles = Array.isArray(selectedPrinter?.profiles) ? selectedPrinter.profiles : [];
        profile.innerHTML = profiles.map((item) => `<option value="${{escapeHtml(item)}}">${{escapeHtml(item)}}</option>`).join("");
        if (!profile.value && profiles.length) {{
          profile.value = profiles[0];
        }}
      }}

      function refreshModelForgeFamilyGuidance() {{
        const partField = document.getElementById("model-forge-part");
        const dimensionsField = document.getElementById("model-forge-dimensions");
        const constraintsField = document.getElementById("model-forge-constraints");
        const guidance = document.getElementById("model-forge-guidance");
        const selected = familyProfiles[family?.value || "bracket"] || familyProfiles.bracket;
        if (guidance) guidance.textContent = `${{selected.label}}: ${{selected.note}}`;
        if (partField && (!partField.value || partField.dataset.autofill === "true")) {{
          partField.value = selected.part;
          partField.dataset.autofill = "true";
        }}
        if (dimensionsField && (!dimensionsField.value || dimensionsField.dataset.autofill === "true")) {{
          dimensionsField.value = selected.dimensions;
          dimensionsField.dataset.autofill = "true";
        }}
        if (constraintsField && (!constraintsField.value || constraintsField.dataset.autofill === "true")) {{
          constraintsField.value = selected.constraints;
          constraintsField.dataset.autofill = "true";
        }}
      }}

      async function populateModelForgeControls() {{
        const options = await ensureModelForgeOptions();
        if (family) {{
          family.innerHTML = (options.families || []).map((item) => `<option value="${{escapeHtml(item.id)}}">${{escapeHtml(item.label)}}</option>`).join("");
        }}
        if (printer) {{
          printer.innerHTML = (options.printers || []).map((item) => `<option value="${{escapeHtml(item.id)}}">${{escapeHtml(item.name)}}</option>`).join("");
          if (options.default_printer_id) printer.value = options.default_printer_id;
        }}
        if (slicer) {{
          slicer.innerHTML = [`<option value="">System default</option>`]
            .concat((options.slicers || []).map((item) => `<option value="${{escapeHtml(item.id)}}">${{escapeHtml(item.label)}}</option>`))
            .join("");
        }}
        refreshModelForgeProfileOptions();
        refreshModelForgeFamilyGuidance();
      }}

      async function refreshModelForgePackages(selectedId = "") {{
        const response = await fetch("/api/cad-packages", {{ cache: "no-store" }});
        if (!response.ok) {{
          throw new Error("Failed to refresh model forge packages.");
        }}
        const packages = await response.json();
        select.innerHTML = packages.map((item, index) => `<option value="${{escapeHtml(item.package_id)}}" ${{(selectedId ? item.package_id === selectedId : index === 0) ? "selected" : ""}}>${{escapeHtml(item.part_name)}} · ${{escapeHtml(item.export_status || "cad-package")}}</option>`).join("");
        if (select.value) {{
          await loadModelForgePackage(select.value);
        }}
      }}

      async function generateModelForgePackage() {{
        const payload = {{
          actor: "Chris",
          family: family?.value || "",
          printer: printer?.value || "",
          profile: profile?.value || "",
          creative_profile: state.modelForgeCreativeProfile || "",
          part: document.getElementById("model-forge-part")?.value || "",
          dimensions: document.getElementById("model-forge-dimensions")?.value || "",
          constraints: document.getElementById("model-forge-constraints")?.value || "",
        }};
        const response = await fetch("/api/cad-package", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload),
        }});
        if (!response.ok) {{
          throw new Error("Failed to generate model forge package.");
        }}
        const result = await response.json();
        if (output) output.textContent = JSON.stringify(result, null, 2);
        await refreshModelForgePackages(result.package_id);
      }}

      function applyConceptToCreate(session) {{
        const selectedVariant = Array.isArray(state.modelForgeConceptVariants)
          ? state.modelForgeConceptVariants[state.modelForgeSelectedVariantIndex] || null
          : null;
        const payload = selectedVariant?.apply_payload || session?.apply_payload || {{
          family: session?.suggested_family || (session?.suggested_silhouette ? "custom-form" : ""),
          part: session?.suggested_part_name || "",
          dimensions: session?.suggested_dimensions || "",
          constraints: session?.suggested_constraints || "",
          creative_profile: session?.suggested_silhouette || "",
        }};
        if (payload.family && family) {{
          family.value = payload.family;
          refreshModelForgeFamilyGuidance();
        }}
        state.modelForgeCreativeProfile = payload.creative_profile || "";
        if (payload.part) {{
          const field = document.getElementById("model-forge-part");
          if (field) field.value = payload.part;
        }}
        if (payload.dimensions) {{
          const field = document.getElementById("model-forge-dimensions");
          if (field) field.value = payload.dimensions;
        }}
        if (payload.constraints) {{
          const field = document.getElementById("model-forge-constraints");
          if (field) field.value = payload.constraints;
        }}
        setModelForgeTab("create");
        if (output) output.textContent = JSON.stringify(payload, null, 2);
      }}

      function renderVariantStrip(session) {{
        if (!variantStrip) return;
        const variants = Array.isArray(session?.variants) ? session.variants : [];
        state.modelForgeConceptVariants = variants;
        if (!variants.length) {{
          state.modelForgeSelectedVariantIndex = 0;
          variantStrip.innerHTML = `
            <div class="model-forge-variant-card">
              <strong>Forge will generate options</strong>
              <div class="model-forge-variant-pitch">Discuss the concept once and we’ll surface 2 to 3 directions here before package generation.</div>
            </div>
          `;
          return;
        }}
        if (state.modelForgeSelectedVariantIndex >= variants.length) {{
          state.modelForgeSelectedVariantIndex = 0;
        }}
        variantStrip.innerHTML = variants.map((variant, index) => `
          <button
            type="button"
            class="model-forge-variant-card ${{index === state.modelForgeSelectedVariantIndex ? "active" : ""}}"
            data-variant-index="${{index}}"
          >
            <div class="model-forge-variant-meta">${{escapeHtml(variant.label || `Variant ${{index + 1}}`)}} · ${{escapeHtml(String(variant.silhouette || "open").replace(/-/g, " "))}}</div>
            <strong>${{escapeHtml(variant.name || "Concept direction")}}</strong>
            <div class="model-forge-variant-pitch">${{escapeHtml(variant.pitch || "Compare this direction before package generation.")}}</div>
            <div class="model-forge-variant-foot">
              <span>${{escapeHtml(variant.print_posture || "Prototype first")}}</span>
              <span>${{escapeHtml(String(variant.object_type || "").replace(/-/g, " "))}}</span>
            </div>
          </button>
        `).join("");
      }}

      function renderSilhouettePreview(session) {{
        const variant = Array.isArray(state.modelForgeConceptVariants)
          ? state.modelForgeConceptVariants[state.modelForgeSelectedVariantIndex] || null
          : null;
        const key = variant?.silhouette || session?.suggested_silhouette || session?.silhouette_preference || "";
        const profile = silhouetteCatalog[key] || null;
        if (silhouetteName) silhouetteName.textContent = profile?.label || "Waiting for direction";
        if (silhouetteBadge) silhouetteBadge.textContent = profile?.badge || "Unchosen";
        if (silhouetteDescription) {{
          silhouetteDescription.textContent = profile?.description || "Forge will surface a silhouette direction before the concept becomes a package.";
        }}
        if (silhouettePrint) silhouettePrint.textContent = profile?.print || "--";
        if (silhouetteUse) silhouetteUse.textContent = profile?.use || "--";
        if (silhouetteCharacter) silhouetteCharacter.textContent = profile?.character || "--";
        if (silhouetteArt) {{
          silhouetteArt.style.backgroundImage = profile?.art || "none";
        }}
      }}

      function renderConceptTranscript(session) {{
        if (!conceptTranscript) return;
        const transcript = Array.isArray(session?.transcript) ? session.transcript : [];
        if (!transcript.length) {{
          conceptTranscript.textContent = "Your design dialogue with Forge will appear here.";
          return;
        }}
        conceptTranscript.innerHTML = `
          <div class="model-forge-chat-thread">
            ${{
              transcript.map((item, index) => {{
                const role = String(item.role || "user").toLowerCase();
                const tone = role === "assistant" ? "assistant" : role === "system" ? "system" : "user";
                const label = tone === "assistant" ? "Forge" : tone === "system" ? "System" : "You";
                const caption = tone === "assistant"
                  ? "design response"
                  : tone === "system"
                    ? "session update"
                    : "design prompt";
                return `
                  <div class="model-forge-chat-bubble ${{tone}}">
                    <div class="model-forge-chat-head">
                      <strong>${{label}}</strong>
                      <span>Turn ${{index + 1}} · ${{caption}}</span>
                    </div>
                    <p>${{escapeHtml(item.content || "")}}</p>
                  </div>
                `;
              }}).join("")
            }}
          </div>
        `;
      }}

      function renderConceptSession(session) {{
        if (!session) return;
        state.modelForgeConceptSessionId = session.session_id || "";
        state.modelForgeVisionHints = {{
          objectLabel: session.vision_object_label || "",
          contourConfidence: session.vision_contour_confidence || "",
          asymmetryHint: session.vision_asymmetry_hint || "",
          dimensionSeed: session.vision_dimension_seed || "",
        }};
        if (conceptGoals && session.goals) conceptGoals.value = session.goals;
        if (conceptConstraints && session.constraints) conceptConstraints.value = session.constraints;
        if (conceptType && session.object_type) conceptType.value = session.object_type;
        if (conceptSilhouette) conceptSilhouette.value = session.suggested_silhouette || session.silhouette_preference || "";
        state.modelForgeCreativeProfile = session.suggested_silhouette || "";
        const variants = Array.isArray(session.variants) ? session.variants : [];
        const preferredKey = session.suggested_silhouette || session.silhouette_preference || "";
        const matchedIndex = variants.findIndex((item) => String(item.silhouette || "") === preferredKey);
        state.modelForgeSelectedVariantIndex = matchedIndex >= 0 ? matchedIndex : 0;
        renderVariantStrip(session);
        renderSilhouettePreview(session);
        if (conceptBrief) {{
          const questions = Array.isArray(session.questions) ? session.questions : [];
          conceptBrief.innerHTML = `
            <strong>${{escapeHtml(session.title || "Concept session")}}</strong><br>
            ${{escapeHtml(session.concept_summary || "No summary yet.")}}<br><br>
            <strong>Direction</strong><br>
            ${{escapeHtml(session.design_direction || "No direction yet.")}}<br><br>
            <strong>Silhouette</strong><br>
            ${{escapeHtml(session.suggested_silhouette || session.silhouette_preference || "Not locked yet.")}}<br><br>
            <strong>Print Strategy</strong><br>
            ${{escapeHtml(session.print_strategy || "No print strategy yet.")}}<br><br>
            <strong>Next Step</strong><br>
            ${{escapeHtml(session.next_step || "Keep refining the concept.")}}
            ${{questions.length ? `<br><br><strong>Questions</strong><br>${{questions.map((item) => `- ${{escapeHtml(item)}}`).join("<br>")}}` : ""}}
          `;
        }}
        renderConceptTranscript(session);
        if (conceptStatus) {{
          conceptStatus.textContent = session.image_path
            ? "Concept session is using a Vision reference. Keep refining, then send the best direction into Create."
            : "Concept session is active. Keep shaping the object until the geometry feels ready.";
        }}
      }}

      async function loadConceptVisionReferences() {{
        if (!conceptCapture) return;
        const response = await fetch(`/api/vision-state?actor=Chris`, {{ cache: "no-store" }});
        if (!response.ok) return;
        const vision = await response.json();
        const captures = Array.isArray(vision.recent_captures) ? vision.recent_captures : [];
        conceptCapture.innerHTML = [`<option value="">No photo reference</option>`]
          .concat(captures.map((item, index) => {{
            const summary = item.analysis || item.mode || `Capture ${{index + 1}}`;
            const label = summary.split("\\n")[0].slice(0, 90);
            const measurement = escapeHtml(JSON.stringify(item.measurement || {{}}));
            return `<option value="${{escapeHtml(item.image_path || "")}}" data-capture-id="${{escapeHtml(item.capture_id || "")}}" data-analysis="${{escapeHtml(summary)}}" data-measurement="${{measurement}}">${{escapeHtml(label || `Capture ${{index + 1}}`)}}</option>`;
          }}))
          .join("");
      }}

      async function hydrateLatestConceptSession() {{
        const response = await fetch("/api/concept-studio/sessions?limit=1", {{ cache: "no-store" }});
        if (!response.ok) return;
        const sessions = await response.json();
        if (Array.isArray(sessions) && sessions.length) {{
          renderConceptSession(sessions[0]);
        }}
      }}

      async function sendConceptMessage() {{
        const selectedOption = conceptCapture?.selectedOptions?.[0] || null;
        const visionHints = readConceptVisionHintsFromSelection();
        const payload = {{
          actor: "Chris",
          session_id: state.modelForgeConceptSessionId || "",
          object_type: conceptType?.value || "custom object",
          silhouette_preference: conceptSilhouette?.value || "",
          goals: conceptGoals?.value || "",
          constraints: conceptConstraints?.value || "",
          prompt: conceptPrompt?.value || "",
          image_path: conceptCapture?.value || "",
          capture_id: selectedOption?.dataset?.captureId || "",
          reference_note: conceptReference?.value || "",
          vision_object_label: visionHints.objectLabel || "",
          vision_contour_confidence: visionHints.contourConfidence || "",
          vision_asymmetry_hint: visionHints.asymmetryHint || "",
          vision_dimension_seed: visionHints.dimensionSeed || "",
        }};
        if (conceptStatus) conceptStatus.textContent = "Forge is thinking through the concept…";
        const response = await fetch("/api/concept-studio/chat", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload),
        }});
        if (!response.ok) {{
          const error = await response.json().catch(() => ({{ detail: "Concept Studio failed." }}));
          throw new Error(error.detail || "Concept Studio failed.");
        }}
        const session = await response.json();
        renderConceptSession(session);
      }}

      function formatVisionConceptDimensions(measurement) {{
        if (!measurement || typeof measurement !== "object") return "";
        const unit = String(measurement.unit || "cm").trim() || "cm";
        const parts = [];
        const width = Number(measurement.width);
        const height = Number(measurement.height);
        const diagonal = Number(measurement.diagonal);
        if (Number.isFinite(width)) parts.push(`observed width ${{width.toFixed(2)}} ${{unit}}`);
        if (Number.isFinite(height)) parts.push(`observed height ${{height.toFixed(2)}} ${{unit}}`);
        if (Number.isFinite(diagonal)) parts.push(`observed diagonal ${{diagonal.toFixed(2)}} ${{unit}}`);
        return parts.join(", ");
      }}

      function inferVisionHintsFromAnalysis(analysisText, measurement) {{
        const normalized = String(analysisText || "").trim();
        const firstLine = normalized.split("\\n")[0].trim();
        const lower = normalized.toLowerCase();
        const objectLabel = firstLine && !firstLine.startsWith("Measured selection")
          ? firstLine.replace(/^i see\\s+/i, "").replace(/^looks like\\s+/i, "").slice(0, 80)
          : (measurement ? "Measured object" : "");
        let contourConfidence = "medium";
        if (measurement) {{
          contourConfidence = "high";
        }} else if (/(unclear|hard to tell|blurry|obstructed)/i.test(lower)) {{
          contourConfidence = "low";
        }} else if (/(appears|likely|probably|seems)/i.test(lower)) {{
          contourConfidence = "medium";
        }} else if (normalized) {{
          contourConfidence = "high";
        }}
        let asymmetryHint = "";
        if (/(asymmetr|lopsided|irregular)/i.test(lower)) {{
          asymmetryHint = "Observed asymmetry looks meaningful. Preserve it unless we intentionally normalize the form.";
        }} else if (/(symmetr|balanced|even on both sides)/i.test(lower)) {{
          asymmetryHint = "The observed form reads mostly symmetric.";
        }} else if (measurement) {{
          asymmetryHint = "Respect the observed proportions first, then decide whether to stylize asymmetry.";
        }}
        return {{
          objectLabel,
          contourConfidence,
          asymmetryHint,
          dimensionSeed: formatVisionConceptDimensions(measurement),
        }};
      }}

      function readConceptVisionHintsFromSelection() {{
        const selectedOption = conceptCapture?.selectedOptions?.[0];
        if (!selectedOption) return state.modelForgeVisionHints || {{}};
        let measurement = null;
        try {{
          measurement = selectedOption.dataset.measurement ? JSON.parse(selectedOption.dataset.measurement) : null;
        }} catch (_error) {{
          measurement = null;
        }}
        const analysisText = selectedOption.dataset.analysis || "";
        return {{
          ...(state.modelForgeVisionHints || {{}}),
          ...inferVisionHintsFromAnalysis(analysisText, measurement),
        }};
      }}

      function maybeLaunchPendingVisionConcept() {{
        const pending = state.pendingModelForgeConceptLaunch;
        if (!pending) return;
        if (conceptCapture && pending.imagePath) {{
          conceptCapture.value = pending.imagePath;
        }}
        if (conceptType && pending.objectType) conceptType.value = pending.objectType;
        if (conceptSilhouette && pending.silhouette) conceptSilhouette.value = pending.silhouette;
        if (conceptGoals && pending.goals) conceptGoals.value = pending.goals;
        if (conceptConstraints && pending.constraints) conceptConstraints.value = pending.constraints;
        if (conceptReference && pending.referenceNote) conceptReference.value = pending.referenceNote;
        if (conceptPrompt && pending.prompt) conceptPrompt.value = pending.prompt;
        state.modelForgeVisionHints = pending.visionHints || null;
        if (conceptStatus) conceptStatus.textContent = "Vision reference is loaded into Concept Studio. Start the design discussion when you are ready.";
        renderSilhouettePreview({{ silhouette_preference: pending.silhouette || "" }});
        setModelForgeTab("concept");
        state.pendingModelForgeConceptLaunch = null;
      }}

      async function openSelectedPackageInSlicer(packageId) {{
        const response = await fetch(`/api/model-forge/package/${{encodeURIComponent(packageId)}}/open-in-slicer`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ slicer_app: slicer?.value || "" }}),
        }});
        if (!response.ok) {{
          throw new Error("Failed to open package in slicer.");
        }}
        const result = await response.json();
        if (output) output.textContent = JSON.stringify(result, null, 2);
      }}

      const loadSelected = () => {{
        loadModelForgePackage(select.value).catch((error) => {{
          const status = document.getElementById("model-forge-viewer-status");
          if (status) status.textContent = error.message || "Failed to load model forge package.";
        }});
      }};
      const setModelForgeTab = (tabId) => {{
        tabs.forEach((tab) => {{
          const active = tab.dataset.modelForgeTab === tabId;
          tab.classList.toggle("active", active);
          tab.setAttribute("aria-selected", active ? "true" : "false");
        }});
        panels.forEach((panel) => {{
          panel.classList.toggle("active", panel.dataset.modelForgePanel === tabId);
        }});
      }};
      populateModelForgeControls().catch((error) => {{
        if (output) output.textContent = error.message;
      }});
      loadConceptVisionReferences()
        .then(() => maybeLaunchPendingVisionConcept())
        .catch((error) => {{
          if (conceptStatus) conceptStatus.textContent = error.message || "Failed to load Vision references.";
        }});
      hydrateLatestConceptSession().catch(() => {{}});
      renderSilhouettePreview({{ silhouette_preference: conceptSilhouette?.value || "" }});
      tabs.forEach((tab) => {{
        tab.addEventListener("click", () => setModelForgeTab(tab.dataset.modelForgeTab || "create"));
      }});
      family?.addEventListener("change", refreshModelForgeFamilyGuidance);
      printer?.addEventListener("change", refreshModelForgeProfileOptions);
      conceptSilhouette?.addEventListener("change", () => {{
        renderSilhouettePreview({{ silhouette_preference: conceptSilhouette.value || "" }});
      }});
      conceptCapture?.addEventListener("change", () => {{
        state.modelForgeVisionHints = readConceptVisionHintsFromSelection();
      }});
      ["model-forge-part", "model-forge-dimensions", "model-forge-constraints"].forEach((id) => {{
        const field = document.getElementById(id);
        field?.addEventListener("input", () => {{
          field.dataset.autofill = "false";
        }});
      }});
      select.addEventListener("change", loadSelected);
      refresh?.addEventListener("click", loadSelected);
      conceptSend?.addEventListener("click", () => {{
        sendConceptMessage().catch((error) => {{
          if (conceptStatus) conceptStatus.textContent = error.message || "Concept Studio failed.";
        }});
      }});
      conceptApply?.addEventListener("click", () => {{
        if (!state.modelForgeConceptSessionId) {{
          if (conceptStatus) conceptStatus.textContent = "Start a concept session first so Forge has something real to send into Create.";
          return;
        }}
        fetch(`/api/concept-studio/session/${{encodeURIComponent(state.modelForgeConceptSessionId)}}`, {{ cache: "no-store" }})
          .then((response) => response.ok ? response.json() : Promise.reject(new Error("Failed to reload concept session.")))
          .then((session) => applyConceptToCreate(session))
          .catch((error) => {{
            if (conceptStatus) conceptStatus.textContent = error.message || "Failed to send the concept into Create.";
          }});
      }});
      variantStrip?.addEventListener("click", (event) => {{
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;
        const card = target.closest("[data-variant-index]");
        if (!(card instanceof HTMLElement)) return;
        const nextIndex = Number(card.dataset.variantIndex || "0");
        if (!Number.isFinite(nextIndex)) return;
        state.modelForgeSelectedVariantIndex = nextIndex;
        renderVariantStrip({{ variants: state.modelForgeConceptVariants }});
        renderSilhouettePreview({{ suggested_silhouette: state.modelForgeConceptVariants[nextIndex]?.silhouette || "" }});
        const selectedVariant = state.modelForgeConceptVariants[nextIndex];
        if (conceptSilhouette && selectedVariant?.silhouette) conceptSilhouette.value = selectedVariant.silhouette;
        if (conceptStatus && selectedVariant) {{
          conceptStatus.textContent = `${{selectedVariant.label || `Variant ${{nextIndex + 1}}`}} is selected. Keep refining, or send this direction into Create.`;
        }}
      }});
      generate?.addEventListener("click", () => {{
        generateModelForgePackage().catch((error) => {{
          if (output) output.textContent = error.message;
        }});
      }});
      document.getElementById("model-forge-details")?.addEventListener("click", (event) => {{
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;
        const button = target.closest("#model-forge-open-slicer");
        if (!(button instanceof HTMLElement)) return;
        const packageId = button.dataset.packageId;
        if (!packageId) return;
        openSelectedPackageInSlicer(packageId).catch((error) => {{
          if (output) output.textContent = error.message;
        }});
      }});
      if (select.value) loadSelected();
    }}

    async function listVisionDevices() {{
      if (!navigator.mediaDevices?.enumerateDevices) {{
        return [];
      }}
      const devices = await navigator.mediaDevices.enumerateDevices();
      return devices.filter((device) => device.kind === "videoinput");
    }}

    async function populateVisionDevicePicker() {{
      const select = document.getElementById("vision-device");
      if (!select) {{
        return;
      }}
      state.visionDevices = await listVisionDevices();
      const devices = state.visionDevices.length ? state.visionDevices : [{{ deviceId: "", label: "Default camera" }}];
      select.innerHTML = devices.map((device, index) => {{
        const label = device.label || `Camera ${{index + 1}}`;
        const selected = device.deviceId && device.deviceId === state.visionDeviceId ? "selected" : "";
        return `<option value="${{escapeHtml(device.deviceId || "")}}" ${{selected}}>${{escapeHtml(label)}}</option>`;
      }}).join("");
    }}

    async function startVisionPreview(deviceId = "") {{
      const status = document.getElementById("vision-status");
      const video = document.getElementById("vision-live-video");
      if (!video) {{
        return;
      }}
      if (!navigator.mediaDevices?.getUserMedia) {{
        if (status) status.textContent = "This browser does not expose camera access.";
        return;
      }}
      stopVisionPreview();
      if (status) status.textContent = "Requesting camera access…";
      const constraints = deviceId
        ? {{ video: {{ deviceId: {{ exact: deviceId }} }}, audio: false }}
        : {{ video: true, audio: false }};
      try {{
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        state.visionStream = stream;
        video.srcObject = stream;
        await video.play();
        const track = stream.getVideoTracks()[0];
        const settings = track?.getSettings?.() || {{}};
        state.visionDeviceId = String(settings.deviceId || deviceId || "");
        await populateVisionDevicePicker();
        if (status) {{
          status.textContent = "Live preview active. JARVIS is not monitoring in the background; capture only happens when you press Capture Frame.";
        }}
      }} catch (error) {{
        if (status) status.textContent = error.message || "Camera access failed.";
      }}
    }}

    async function captureVisionFrame() {{
      const video = document.getElementById("vision-live-video");
      const canvas = document.getElementById("vision-canvas");
      const preview = document.getElementById("vision-preview");
      const analysis = document.getElementById("vision-analysis");
      const status = document.getElementById("vision-status");
      const prompt = document.getElementById("vision-prompt")?.value || "";
      const actor = document.getElementById("actor")?.value || "Chris";
      const deviceSelect = document.getElementById("vision-device");
      const mode = document.getElementById("vision-mode")?.value || "describe";
      if (!video || !canvas) {{
        return;
      }}
      if (!state.visionStream) {{
        await startVisionPreview(deviceSelect?.value || "");
      }}
      const width = video.videoWidth || 1280;
      const height = video.videoHeight || 720;
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d");
      if (!context) {{
        if (status) status.textContent = "Camera capture context unavailable.";
        return;
      }}
      if (mode === "measure") {{
        const metrics = getVisionSelectionMetrics(video);
        if (!state.visionCalibration) {{
          if (analysis) analysis.textContent = "Calibrate first: place a ruler on the stage, turn crop on, select a known span, and use Calibrate Selection.";
          if (status) status.textContent = "Measure mode needs calibration before it can estimate size.";
          return;
        }}
        if (!metrics) {{
          if (analysis) analysis.textContent = "Turn crop on and drag across the object span you want to measure.";
          if (status) status.textContent = "Measure mode needs a selected span on the live preview.";
          return;
        }}
        const unit = state.visionCalibration.unit || "cm";
        const measuredWidth = metrics.pixelWidth / state.visionCalibration.pixelsPerUnit;
        const measuredHeight = metrics.pixelHeight / state.visionCalibration.pixelsPerUnit;
        const measuredDiagonal = metrics.diagonalPixels / state.visionCalibration.pixelsPerUnit;
        canvas.width = width;
        canvas.height = height;
        context.drawImage(video, 0, 0, width, height, 0, 0, width, height);
        const imageDataUrl = canvas.toDataURL("image/jpeg", 0.92);
        if (preview) {{
          preview.src = imageDataUrl;
          preview.hidden = false;
        }}
        if (analysis) {{
          analysis.textContent = [
            `Measured selection:`,
            `Width: ${{formatMeasurement(measuredWidth, unit)}}`,
            `Height: ${{formatMeasurement(measuredHeight, unit)}}`,
            `Diagonal: ${{formatMeasurement(measuredDiagonal, unit)}}`,
            `Calibration: ${{state.visionCalibration.referenceLength}} ${{unit}} across ${{Math.round(state.visionCalibration.referencePixels)}} px`,
          ].join("\\n");
        }}
        const selectedOption = deviceSelect?.selectedOptions?.[0];
        try {{
          const result = await loadJSON("/api/vision/measure", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{
              actor,
              image_data_url: imageDataUrl,
              camera_label: selectedOption?.textContent || "Desk Camera",
              calibration: state.visionCalibration,
              measurement: {{
                width: measuredWidth,
                height: measuredHeight,
                diagonal: measuredDiagonal,
                unit,
              }},
              detail: analysis?.textContent || "Measured the selected span using the saved ruler calibration.",
              selection: metrics,
            }}),
          }});
          state.lastVisionCapture = {{
            ...(result.capture || {{}}),
            measurement: result.capture?.measurement || {{
              width: measuredWidth,
              height: measuredHeight,
              diagonal: measuredDiagonal,
              unit,
            }},
          }};
          if (status) status.textContent = "Measured the selected span and saved it as a real Vision reference.";
          renderVisionCalibrationSummary("Measurement ready.");
          if (sendToConceptButton) sendToConceptButton.disabled = false;
        }} catch (error) {{
          if (status) status.textContent = error.message || "Measurement save failed.";
        }}
        return;
      }}
      if (mode === "compare" && !state.lastVisionCapture?.capture_id) {{
        if (analysis) analysis.textContent = "Capture a baseline frame first, then switch to compare mode.";
        if (status) status.textContent = "Compare mode needs one earlier frame to compare against.";
        return;
      }}
      let sx = 0;
      let sy = 0;
      let sw = width;
      let sh = height;
      if (state.visionCropEnabled && state.visionCropRect) {{
        const displayWidth = video.clientWidth || width;
        const displayHeight = video.clientHeight || height;
        const scaleX = width / displayWidth;
        const scaleY = height / displayHeight;
        sx = Math.max(0, Math.round(state.visionCropRect.x * scaleX));
        sy = Math.max(0, Math.round(state.visionCropRect.y * scaleY));
        sw = Math.max(1, Math.round(state.visionCropRect.width * scaleX));
        sh = Math.max(1, Math.round(state.visionCropRect.height * scaleY));
        canvas.width = sw;
        canvas.height = sh;
      }}
      context.drawImage(video, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
      const imageDataUrl = canvas.toDataURL("image/jpeg", 0.92);
      if (preview) {{
        preview.src = imageDataUrl;
        preview.hidden = false;
      }}
      if (status) status.textContent = "Analyzing captured frame…";
      if (analysis) analysis.textContent = "JARVIS is analyzing this frame.";
      try {{
        const selectedOption = deviceSelect?.selectedOptions?.[0];
        const result = await loadJSON("/api/vision/analyze", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            actor,
            prompt,
            mode,
            image_data_url: imageDataUrl,
            camera_label: selectedOption?.textContent || "Desk Camera",
            compare_to_capture_id: mode === "compare" ? (state.lastVisionCapture?.capture_id || "") : "",
          }}),
        }});
        state.lastVisionCapture = result;
        if (analysis) analysis.textContent = result.analysis || "No analysis returned.";
        if (status) status.textContent = `Captured one frame from ${{result.camera_label || "Desk Camera"}}. No continuous monitoring is active.`;
        if (sendToConceptButton) sendToConceptButton.disabled = false;
      }} catch (error) {{
        if (analysis) analysis.textContent = error.message || "Vision analysis failed.";
        if (status) status.textContent = "Capture succeeded, but analysis failed.";
      }}
    }}

    function wireVisionPacket() {{
      const startButton = document.getElementById("vision-start");
      const captureButton = document.getElementById("vision-capture");
      const retakeButton = document.getElementById("vision-retake");
      const cropToggle = document.getElementById("vision-toggle-crop");
      const deviceSelect = document.getElementById("vision-device");
      const modeSelect = document.getElementById("vision-mode");
      const video = document.getElementById("vision-live-video");
      const cropBox = document.getElementById("vision-crop-box");
      const preview = document.getElementById("vision-preview");
      const analysis = document.getElementById("vision-analysis");
      const status = document.getElementById("vision-status");
      const promptField = document.getElementById("vision-prompt");
      const sendToConceptButton = document.getElementById("vision-send-to-concept");
      const calibrateButton = document.getElementById("vision-calibrate");
      const clearCalibrationButton = document.getElementById("vision-clear-calibration");
      const calibrationLengthField = document.getElementById("vision-calibration-length");
      const calibrationUnitField = document.getElementById("vision-calibration-unit");

      function renderCropBox() {{
        if (!cropBox || !state.visionCropRect || !state.visionCropEnabled) {{
          cropBox?.classList.remove("active");
          return;
        }}
        cropBox.classList.add("active");
        cropBox.style.left = `${{state.visionCropRect.x}}px`;
        cropBox.style.top = `${{state.visionCropRect.y}}px`;
        cropBox.style.width = `${{state.visionCropRect.width}}px`;
        cropBox.style.height = `${{state.visionCropRect.height}}px`;
      }}

      function resetVisionCaptureState(preserveHistory = true) {{
        if (!preserveHistory) {{
          state.lastVisionCapture = null;
        }}
        state.visionCropRect = null;
        state.visionDragStart = null;
        if (preview) {{
          preview.hidden = true;
          preview.removeAttribute("src");
        }}
        if (analysis) analysis.textContent = "No frame captured yet.";
        if (status) {{
          status.textContent = preserveHistory && state.lastVisionCapture?.capture_id
            ? "Retake ready. Your previous frame is still available for compare mode."
            : "Live preview active. JARVIS is not monitoring in the background; capture only happens when you press Capture Frame.";
        }}
        renderCropBox();
      }}

      function calibrateVisionSelection() {{
        const metrics = getVisionSelectionMetrics(video);
        const rawLength = Number(calibrationLengthField?.value || "");
        const unit = calibrationUnitField?.value || "cm";
        if (!metrics) {{
          if (analysis) analysis.textContent = "Turn crop on and drag across a known ruler span before calibrating.";
          if (status) status.textContent = "Calibration needs a selected ruler span.";
          return;
        }}
        if (!Number.isFinite(rawLength) || rawLength <= 0) {{
          if (analysis) analysis.textContent = "Enter the real ruler length for the selected span before calibrating.";
          if (status) status.textContent = "Calibration length must be a positive number.";
          return;
        }}
        const calibration = {{
          pixelsPerUnit: metrics.majorAxisPixels / rawLength,
          referencePixels: metrics.majorAxisPixels,
          referenceLength: rawLength,
          unit,
          updatedAt: new Date().toISOString(),
        }};
        saveVisionCalibration(calibration);
        renderVisionCalibrationSummary("Selection is now calibrated for measure mode.");
        if (analysis) {{
          analysis.textContent = `Calibration saved: ${{rawLength}} ${{unit}} across ${{Math.round(metrics.majorAxisPixels)}} px.`;
        }}
        if (status) status.textContent = "Vision measure mode is calibrated and ready.";
      }}

      startButton?.addEventListener("click", () => {{
        startVisionPreview(deviceSelect?.value || "").catch((error) => {{
          if (status) status.textContent = error.message || "Camera start failed.";
        }});
      }});
      captureButton?.addEventListener("click", () => {{
        captureVisionFrame().catch((error) => {{
          if (analysis) analysis.textContent = error.message || "Vision capture failed.";
          if (status) status.textContent = "Capture failed.";
        }});
      }});
      retakeButton?.addEventListener("click", () => {{
        resetVisionCaptureState();
      }});
      calibrateButton?.addEventListener("click", () => {{
        calibrateVisionSelection();
      }});
      clearCalibrationButton?.addEventListener("click", () => {{
        saveVisionCalibration(null);
        renderVisionCalibrationSummary("Calibration cleared.");
        if (status) status.textContent = "Vision calibration cleared.";
      }});
      sendToConceptButton?.addEventListener("click", () => {{
        if (!state.lastVisionCapture) {{
          if (status) status.textContent = "Capture something first so Vision has a real reference to hand off.";
          return;
        }}
        const capture = state.lastVisionCapture.capture || state.lastVisionCapture;
        const analysisText = analysis?.textContent || capture?.analysis || capture?.detail || "";
        const firstLine = String(analysisText).split("\\n")[0].trim();
        const measurement = state.lastVisionCapture.measurement || capture?.measurement || null;
        const dimensionSeed = formatVisionConceptDimensions(measurement);
        const visionHints = inferVisionHintsFromAnalysis(analysisText, measurement);
        state.pendingModelForgeConceptLaunch = {{
          imagePath: capture?.image_path || "",
          captureId: capture?.capture_id || "",
          objectType: measurement ? "functional object" : "custom object",
          silhouette: measurement ? "organic-reconstruction" : "",
          goals: measurement
            ? "Use this measured Vision reference to shape a printable object that respects the observed proportions."
            : "Use this Vision reference to shape a unique printable object.",
          constraints: dimensionSeed
            ? `${{dimensionSeed}}. Preserve the measured proportions unless we decide to stylize them on purpose.`
            : "",
          referenceNote: dimensionSeed
            ? `${{firstLine || "Use this captured frame as the visual reference."}} Observed dimensions: ${{dimensionSeed}}.`
            : (firstLine || "Use this captured frame as the visual reference."),
          prompt: measurement
            ? "Use this measured capture as the starting point, keep the observed proportions in play, and help me design the object before we generate geometry."
            : "Use this captured image as inspiration and help me build a printable concept around it.",
          visionHints,
        }};
        openPacket("model-forge");
      }});
      cropToggle?.addEventListener("click", () => {{
        state.visionCropEnabled = !state.visionCropEnabled;
        cropToggle.classList.toggle("primary", state.visionCropEnabled);
        cropToggle.textContent = state.visionCropEnabled ? "Crop On" : "Crop Before Analyze";
        if (!state.visionCropEnabled) {{
          state.visionCropRect = null;
        }}
        renderCropBox();
      }});
      modeSelect?.addEventListener("change", () => {{
        const mode = modeSelect.value;
        if (mode === "text") {{
          if (promptField) {{
            promptField.value ||= "Read any visible text exactly. If it is unclear, say so.";
          }}
        }} else if (mode === "compare") {{
          if (promptField) {{
            promptField.value ||= "Compare this frame to the previous one and tell me what changed.";
          }}
          if (status && !state.lastVisionCapture?.capture_id) {{
            status.textContent = "Compare mode is ready, but you need one earlier capture first.";
          }}
        }} else if (mode === "measure") {{
          state.visionCropEnabled = true;
          cropToggle?.classList.add("primary");
          if (cropToggle) cropToggle.textContent = "Selection On";
          if (promptField && !promptField.value.trim()) {{
            promptField.value = "Measure the selected item using the saved ruler calibration.";
          }}
          renderVisionCalibrationSummary();
          if (status) {{
            status.textContent = state.visionCalibration
              ? "Measure mode ready. Drag across the item span you want to measure, then capture."
              : "Measure mode ready. Place a ruler on the stage, select a known span, and calibrate first.";
          }}
        }} else if (status) {{
          status.textContent = state.lastVisionCapture?.capture_id
            ? "Live preview active. A previous frame is available if you want compare mode."
            : "Live preview active. JARVIS is not monitoring in the background; capture only happens when you press Capture Frame.";
        }}
      }});
      deviceSelect?.addEventListener("change", () => {{
        startVisionPreview(deviceSelect.value).catch((error) => {{
          if (status) status.textContent = error.message || "Camera switch failed.";
        }});
      }});
      video?.addEventListener("pointerdown", (event) => {{
        if (!state.visionCropEnabled || !video) return;
        const rect = video.getBoundingClientRect();
        state.visionDragStart = {{
          x: Math.max(0, Math.min(rect.width, event.clientX - rect.left)),
          y: Math.max(0, Math.min(rect.height, event.clientY - rect.top)),
        }};
        state.visionCropRect = {{ x: state.visionDragStart.x, y: state.visionDragStart.y, width: 1, height: 1 }};
        renderCropBox();
      }});
      video?.addEventListener("pointermove", (event) => {{
        if (!state.visionCropEnabled || !state.visionDragStart || !video) return;
        const rect = video.getBoundingClientRect();
        const currentX = Math.max(0, Math.min(rect.width, event.clientX - rect.left));
        const currentY = Math.max(0, Math.min(rect.height, event.clientY - rect.top));
        const x = Math.min(state.visionDragStart.x, currentX);
        const y = Math.min(state.visionDragStart.y, currentY);
        const width = Math.abs(currentX - state.visionDragStart.x);
        const height = Math.abs(currentY - state.visionDragStart.y);
        state.visionCropRect = {{ x, y, width, height }};
        renderCropBox();
      }});
      if (!window.__jarvisVisionPointerUpBound) {{
        window.addEventListener("pointerup", () => {{
          state.visionDragStart = null;
        }});
        window.__jarvisVisionPointerUpBound = true;
      }}
      populateVisionDevicePicker()
        .then(() => startVisionPreview(state.visionDeviceId || deviceSelect?.value || ""))
        .catch((error) => {{
          if (status) status.textContent = error.message || "Camera preview unavailable.";
        }});
      state.visionCalibration = loadVisionCalibration();
      renderVisionCalibrationSummary();
      if (sendToConceptButton) sendToConceptButton.disabled = !state.lastVisionCapture;
    }}

    function browserSpeechRecognition() {{
      return window.SpeechRecognition || window.webkitSpeechRecognition || null;
    }}

    function formatSourceIndicator(provider, model = "") {{
      const normalized = String(provider || "standby").trim().toLowerCase();
      if (normalized === "ollama") return "Local";
      if (normalized === "openai") return "OpenAI";
      if (normalized === "policy") return "Policy";
      if (normalized === "fallback") return "Fallback";
      return "Standby";
    }}

    function updateSourceIndicator(provider, model = "") {{
      const indicator = document.getElementById("state-source-indicator");
      if (!indicator) {{
        return;
      }}
      const normalized = String(provider || "standby").trim().toLowerCase();
      indicator.dataset.provider = normalized || "standby";
      indicator.textContent = formatSourceIndicator(normalized, model);
      indicator.title = model
        ? `Response source: ${{formatSourceIndicator(normalized, model)}} · ${{model}}`
        : `Response source: ${{formatSourceIndicator(normalized, model)}}`;
    }}

    function wakeWordPattern() {{
      return /^(?:hey[\\s,]+jarvis|hi[\\s,]+jarvis|ok(?:ay)?[\\s,]+jarvis|jarvis)\\b[\\s,.:;-]*/i;
    }}

    function conversationWindowActive() {{
      if (!state.awaitingImmediateReply) {{
        return false;
      }}
      if (Date.now() >= state.followUpUntil) {{
        state.awaitingImmediateReply = false;
        state.followUpUntil = 0;
        return false;
      }}
      return true;
    }}

    function extendConversationWindow() {{
      state.awaitingImmediateReply = true;
      state.followUpUntil = Date.now() + state.followUpWindowMs;
    }}

    function clearConversationWindow() {{
      state.awaitingImmediateReply = false;
      state.followUpUntil = 0;
    }}

    function isImmediateQuestion(text) {{
      const normalized = String(text || "").trim();
      if (!normalized) {{
        return false;
      }}
      if (/[?]\\s*$/.test(normalized)) {{
        return true;
      }}
      return /\\b(would you like|do you want|should i|shall i|can you|could you|is there|are you|will you)\\b/i.test(normalized);
    }}

    function armImmediateReplyWindow(text) {{
      extendConversationWindow();
      if (isImmediateQuestion(text)) {{
        state.followUpUntil = Date.now() + Math.max(state.followUpWindowMs, 180000);
      }}
    }}

    function clearRecognitionRestartTimer() {{
      if (state.recognitionRestartTimer) {{
        clearTimeout(state.recognitionRestartTimer);
        state.recognitionRestartTimer = null;
      }}
    }}

    function refreshMicButton() {{
      if (state.recognizing) {{
        const label = state.recognitionMode === "wake-guard"
          ? "Wake Guard"
          : conversationWindowActive()
            ? "Reply Window"
            : "Listening...";
        setTalkButton(true, label);
        return;
      }}
      if (state.alwaysOnMicEnabled) {{
        setTalkButton(true, "Guard On");
        return;
      }}
      setTalkButton(false, "Mic Off");
    }}

    function queueAlwaysOnListening(delay = 320) {{
      clearRecognitionRestartTimer();
      if (!state.alwaysOnMicEnabled || state.recognizing || state.recognizer) {{
        refreshMicButton();
        return;
      }}
      if (state.currentAudio || (window.speechSynthesis && window.speechSynthesis.speaking)) {{
        refreshMicButton();
        return;
      }}
      state.recognitionRestartTimer = window.setTimeout(() => {{
        state.recognitionRestartTimer = null;
        const mode = conversationWindowActive() ? "command" : "wake-guard";
        startVoiceCommand({{ automatic: true, mode }}).catch((error) => {{
          console.debug("Microphone guard restart failed", error);
          refreshMicButton();
        }});
      }}, delay);
      refreshMicButton();
    }}

    function disableAlwaysOnMic(detail = "Microphone is off.") {{
      state.alwaysOnMicEnabled = false;
      clearConversationWindow();
      clearRecognitionRestartTimer();
      stopDoubleClapGuard();
      stopRecognition();
      setVoiceState("idle", detail);
      refreshMicButton();
    }}

    function enableAlwaysOnMic(detail = 'Standing by for "Hey Jarvis", "Jarvis", or a double clap.') {{
      state.alwaysOnMicEnabled = true;
      setVoiceState("idle", detail);
      startDoubleClapGuard().catch((error) => {{
        console.debug("Double-clap guard unavailable", error);
      }});
      queueAlwaysOnListening(60);
      refreshMicButton();
    }}

    function stopDoubleClapGuard() {{
      if (state.clapMonitorFrame) {{
        cancelAnimationFrame(state.clapMonitorFrame);
        state.clapMonitorFrame = null;
      }}
      if (state.clapSourceNode) {{
        try {{
          state.clapSourceNode.disconnect();
        }} catch (error) {{
          console.debug(error);
        }}
        state.clapSourceNode = null;
      }}
      if (state.clapAnalyser) {{
        try {{
          state.clapAnalyser.disconnect();
        }} catch (error) {{
          console.debug(error);
        }}
        state.clapAnalyser = null;
      }}
      if (state.clapStream) {{
        state.clapStream.getTracks().forEach((track) => track.stop());
        state.clapStream = null;
      }}
      state.clapData = null;
      state.clapPeaks = [];
      state.clapNoiseFloor = 6;
    }}

    async function startDoubleClapGuard() {{
      if (!state.alwaysOnMicEnabled || state.clapStream || !navigator.mediaDevices?.getUserMedia) {{
        return;
      }}
      const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextCtor) {{
        return;
      }}
      const stream = await navigator.mediaDevices.getUserMedia({{
        audio: {{
          channelCount: 1,
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        }},
        video: false,
      }});
      if (!state.alwaysOnMicEnabled) {{
        stream.getTracks().forEach((track) => track.stop());
        return;
      }}
      if (!state.audioContext) {{
        state.audioContext = new AudioContextCtor();
      }}
      const context = state.audioContext;
      if (context.state === "suspended") {{
        await context.resume().catch(() => null);
      }}
      const source = context.createMediaStreamSource(stream);
      const analyser = context.createAnalyser();
      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = 0.02;
      source.connect(analyser);
      state.clapStream = stream;
      state.clapSourceNode = source;
      state.clapAnalyser = analyser;
      state.clapData = new Uint8Array(analyser.fftSize);
      state.clapPeaks = [];
      state.clapNoiseFloor = 6;

      const detect = () => {{
        if (!state.alwaysOnMicEnabled || !state.clapAnalyser || !state.clapData) {{
          return;
        }}
        state.clapAnalyser.getByteTimeDomainData(state.clapData);
        let maxDeviation = 0;
        let sumSquares = 0;
        for (let index = 0; index < state.clapData.length; index += 1) {{
          const deviation = Math.abs(state.clapData[index] - 128);
          if (deviation > maxDeviation) {{
            maxDeviation = deviation;
          }}
          sumSquares += deviation * deviation;
        }}
        const rms = Math.sqrt(sumSquares / state.clapData.length);
        if (maxDeviation < 20) {{
          state.clapNoiseFloor = (state.clapNoiseFloor * 0.94) + (rms * 0.06);
        }}

        const now = Date.now();
        const recentPeaks = state.clapPeaks.filter((peak) => now - peak < 900);
        state.clapPeaks = recentPeaks;
        const lastPeak = recentPeaks[recentPeaks.length - 1] || 0;
        const dynamicPeakThreshold = Math.max(18, state.clapNoiseFloor * 2.8);
        const dynamicRmsThreshold = Math.max(8, state.clapNoiseFloor * 1.85);
        const clapCandidate =
          maxDeviation >= dynamicPeakThreshold ||
          (maxDeviation >= dynamicPeakThreshold * 0.82 && rms >= dynamicRmsThreshold) ||
          rms >= dynamicRmsThreshold * 1.15;
        if (clapCandidate && now - lastPeak > 90) {{
          recentPeaks.push(now);
          state.clapPeaks = recentPeaks;
          if (
            recentPeaks.length >= 2 &&
            now - recentPeaks[recentPeaks.length - 2] >= 110 &&
            now - recentPeaks[recentPeaks.length - 2] <= 760 &&
            now >= state.clapCooldownUntil &&
            !state.recognizing &&
            !state.recognizer &&
            !state.currentAudio &&
            !(window.speechSynthesis && window.speechSynthesis.speaking)
          ) {{
            state.clapCooldownUntil = now + 1800;
            state.clapPeaks = [];
            clearConversationWindow();
            runImmediateStatusUpdate("double-clap").catch((error) => {{
              console.debug("Double-clap status update failed", error);
              document.getElementById("last-jarvis-text").textContent = error.message || "Status update failed.";
              syncTranscriptRail();
              setVoiceState("idle", 'Standing by for "Hey Jarvis", "Jarvis", or a double clap.');
              queueAlwaysOnListening(420);
            }});
            return;
          }}
        }}
        state.clapMonitorFrame = requestAnimationFrame(detect);
      }};

      state.clapMonitorFrame = requestAnimationFrame(detect);
    }}

    async function handleRecognizedSpeech(spoken) {{
      const normalized = spoken.replace(/\\s+/g, " ").trim();
      if (!normalized) {{
        if (state.alwaysOnMicEnabled) {{
          queueAlwaysOnListening();
        }}
        return;
      }}

      const ambientSubtitle = document.getElementById("ambient-subtitle");
      const wakePattern = wakeWordPattern();
      const heardWakeWord = wakePattern.test(normalized);
      const activeConversation = conversationWindowActive();

      if (!activeConversation && !heardWakeWord) {{
        setVoiceState("idle", 'Standing by for "Hey Jarvis", "Jarvis", or a double clap.');
        if (ambientSubtitle) {{
          ambientSubtitle.textContent = 'Standing by for "Hey Jarvis", "Jarvis", or a double clap.';
        }}
        queueAlwaysOnListening();
        return;
      }}

      const request = heardWakeWord ? normalized.replace(wakePattern, "").trim() : normalized;
      clearConversationWindow();

      if (!request) {{
        extendConversationWindow();
        setVoiceState("listening", "Wake word heard. Go ahead.");
        if (ambientSubtitle) {{
          ambientSubtitle.textContent = "Wake word heard. Go ahead.";
        }}
        queueAlwaysOnListening(80);
        return;
      }}

      document.getElementById("last-user-text").textContent = request;
      document.getElementById("command-input").value = request;
      autosizeCommandInput();
      if (ambientSubtitle) ambientSubtitle.textContent = request;
      syncTranscriptRail();
      await submitCommand(true);
    }}

    function updateClock() {{
      const now = new Date();
      document.getElementById("meta-time").textContent = now.toLocaleTimeString([], {{ hour: "numeric", minute: "2-digit" }});
    }}

    function setVoiceState(nextState, detail = "") {{
      document.body.dataset.voiceState = nextState;
      document.getElementById("state-label").textContent = nextState;
      const ambientSubtitle = document.getElementById("ambient-subtitle");
      if (detail && ambientSubtitle) {{
        ambientSubtitle.textContent = detail;
      }}
      if (state.energyTimer) {{
        clearInterval(state.energyTimer);
        state.energyTimer = null;
      }}
      state.energyTarget = 0.35;
    }}

    function stopAudioReactivePulse() {{
      state.audioReactive = false;
      if (state.audioReactiveFrame) {{
        cancelAnimationFrame(state.audioReactiveFrame);
        state.audioReactiveFrame = null;
      }}
      if (state.audioSourceNode) {{
        try {{
          state.audioSourceNode.disconnect();
        }} catch (error) {{
          console.debug(error);
        }}
        state.audioSourceNode = null;
      }}
      if (state.audioAnalyser) {{
        try {{
          state.audioAnalyser.disconnect();
        }} catch (error) {{
          console.debug(error);
        }}
        state.audioAnalyser = null;
      }}
    }}

    function startAudioReactivePulse(audio) {{
      stopAudioReactivePulse();
      const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextCtor) {{
        return;
      }}
      try {{
        if (!state.audioContext) {{
          state.audioContext = new AudioContextCtor();
        }}
        const context = state.audioContext;
        if (context.state === "suspended") {{
          context.resume().catch(() => null);
        }}
        const source = context.createMediaElementSource(audio);
        const analyser = context.createAnalyser();
        analyser.fftSize = 256;
        analyser.smoothingTimeConstant = 0.82;
        source.connect(analyser);
        analyser.connect(context.destination);
        state.audioSourceNode = source;
        state.audioAnalyser = analyser;
        state.audioReactive = true;
        const tick = () => {{
          if (!state.audioReactive || !state.audioAnalyser) {{
            return;
          }}
          state.energyTarget = 0.35;
          state.audioReactiveFrame = requestAnimationFrame(tick);
        }};
        tick();
      }} catch (error) {{
        console.debug("Audio reactive pulse unavailable", error);
        state.audioReactive = false;
      }}
    }}

    function fillSignalRail(data) {{
      const rail = document.getElementById("signal-rail");
      const toggle = document.getElementById("signal-rail-toggle");
      if (!rail || !toggle) {{
        return;
      }}
      rail.classList.toggle("collapsed", !state.signalRailExpanded);
      toggle.classList.toggle("hidden", state.signalRailExpanded);
      if (!state.signalRailExpanded) {{
        rail.innerHTML = "";
        return;
      }}
      const truth = data.truth || {{}};
      const packets = [];
      if (truth.home_live) {{
        packets.push(["House", data.home_overview?.summary?.[0] || "Home state available"]);
      }}
      if (truth.watch_live) {{
        packets.push(["Watch", data.cold_storage_monitor?.recommended_action || data.overnight_review?.summary || "No watch item loaded"]);
      }}
      if ((data.assistant_notifications?.summary?.unread || 0) > 0) {{
        packets.push(["Inbox", `${{data.assistant_notifications.summary.unread}} assistant item(s) waiting`]);
      }}
      if (degradedInfo(data)?.active) {{
        packets.push(["Status", "Degraded mode: last good snapshot"]);
      }}
      for (const [label, value] of (data.assistant_surface?.signal_chips || [])) {{
        if (/(weather|growth|finance|pipeline|marketing)/i.test(String(label || ""))) {{
          continue;
        }}
        packets.push([label, value]);
      }}
      rail.innerHTML = `<button class="packet-button" data-signal-collapse="true">Hide</button>` + packets.map(([label, value]) => `
        <div class="signal-chip"><strong>${{escapeHtml(label)}}:</strong> ${{escapeHtml(value)}}</div>
      `).join("");
      const collapse = rail.querySelector("[data-signal-collapse]");
      if (collapse) {{
        collapse.addEventListener("click", () => toggleSignalRail(false));
      }}
    }}

    function toggleSignalRail(forceOpen = !state.signalRailExpanded) {{
      state.signalRailExpanded = forceOpen;
      if (state.dashboard) {{
        fillSignalRail(state.dashboard);
      }}
    }}

    function syncShellFocusMode() {{
      const focused = Boolean(state.packet || state.activeScene);
      document.body.dataset.workFocus = focused ? "true" : "false";
      document.body.dataset.primarySurface = state.packet ? "modal" : state.activeScene ? "scene" : "home";
    }}

    function contextActionSpecs() {{
      if (state.packet === "dashboard") {{
        return [
          {{ label: "Open Day", packet: "today", primary: true }},
          {{ label: "Catalyst", packet: "catalyst" }},
          {{ label: "Storm", packet: "storm" }},
        ];
      }}
      if (state.packet === "storm") {{
        return [
          {{ label: "Dashboard", packet: "dashboard", primary: true }},
          {{ label: "Day", packet: "today" }},
        ];
      }}
      if (state.packet === "catalyst") {{
        return [
          {{ label: "Dashboard", packet: "dashboard", primary: true }},
          {{ label: "Day", packet: "today" }},
          {{ label: "Settings", packet: "settings" }},
        ];
      }}
      if (state.packet === "chronicle") {{
        return [
          {{ label: "Faith Scene", scene: "faith", primary: true }},
          {{ label: "Dashboard", packet: "dashboard" }},
        ];
      }}
      if (state.packet === "approvals") {{
        return [
          {{ label: "Dashboard", packet: "dashboard", primary: true }},
          {{ label: "Day", packet: "today" }},
        ];
      }}
      if (state.activeScene === "day") {{
        return [
          {{ label: "Approvals", packet: "approvals", primary: true }},
          {{ label: "Catalyst", packet: "catalyst" }},
          {{ label: "Dashboard", packet: "dashboard" }},
        ];
      }}
      if (state.activeScene === "home") {{
        return [
          {{ label: "Storm", packet: "storm", primary: true }},
          {{ label: "Dashboard", packet: "dashboard" }},
          {{ label: "Family", scene: "family" }},
        ];
      }}
      if (state.activeScene === "family") {{
        return [
          {{ label: "Day", scene: "day", primary: true }},
          {{ label: "Mode", action: "mode" }},
          {{ label: "Dashboard", packet: "dashboard" }},
        ];
      }}
      if (state.activeScene === "build") {{
        return [
          {{ label: "Model Forge", packet: "model-forge", primary: true }},
          {{ label: "Dashboard", packet: "dashboard" }},
        ];
      }}
      if (state.activeScene === "faith") {{
        return [
          {{ label: "Chronicle", packet: "chronicle", primary: true }},
          {{ label: "Dashboard", packet: "dashboard" }},
        ];
      }}
      if (state.activeScene === "system") {{
        return [
          {{ label: "Dashboard", packet: "dashboard", primary: true }},
          {{ label: "Settings", packet: "settings" }},
          {{ label: "Mode", action: "mode" }},
        ];
      }}
      return [];
    }}

    function renderContextActionDock() {{
      const dock = document.getElementById("context-action-dock");
      if (!dock) return;
      const actions = contextActionSpecs().slice(0, 3);
      if (!actions.length) {{
        dock.innerHTML = "";
        dock.classList.remove("visible");
        return;
      }}
      dock.innerHTML = actions.map((item) => `
        <button
          type="button"
          class="context-action-chip ${{item.primary ? "primary" : ""}}"
          ${{item.packet ? `data-context-packet="${{escapeHtml(item.packet)}}"` : ""}}
          ${{item.scene ? `data-context-scene="${{escapeHtml(item.scene)}}"` : ""}}
          ${{item.action ? `data-context-action="${{escapeHtml(item.action)}}"` : ""}}
        >${{escapeHtml(item.label)}}</button>
      `).join("");
      dock.classList.add("visible");
      dock.querySelectorAll("[data-context-packet], [data-context-scene], [data-context-action]").forEach((button) => {{
        button.addEventListener("click", () => {{
          const packet = button.getAttribute("data-context-packet") || "";
          const scene = button.getAttribute("data-context-scene") || "";
          const action = button.getAttribute("data-context-action") || "";
          if (packet) {{
            state.manualPacketIntentUntil = Date.now() + 5000;
            openPacket(packet);
            return;
          }}
          if (scene) {{
            state.manualPacketIntentUntil = Date.now() + 5000;
            openScene(scene);
            return;
          }}
          if (action === "mode") {{
            openModePanel();
          }}
        }});
      }});
    }}

    const SCENE_PACKET_MAP = {{
      day: "today",
      home: "home",
      family: "family",
      build: "workshop",
      faith: "chronicle",
      system: "settings",
    }};

    const PACKET_SCENE_MAP = Object.fromEntries(
      Object.entries(SCENE_PACKET_MAP).map(([sceneId, packetId]) => [packetId, sceneId])
    );

    function packetIdForScene(sceneId = "") {{
      return SCENE_PACKET_MAP[String(sceneId || "").trim().toLowerCase()] || "";
    }}

    function sceneIdForPacket(packetId = "") {{
      return PACKET_SCENE_MAP[String(packetId || "").trim().toLowerCase()] || "";
    }}

    function sceneMeta(sceneId = "") {{
      return {{
        day: {{
          kicker: "Day Scene",
          title: "Today",
          summary: "Priorities, schedule pressure, and the current executive operating picture.",
        }},
        home: {{
          kicker: "Home Scene",
          title: "Home",
          summary: "Live house state, environment, and practical household signals.",
        }},
        family: {{
          kicker: "Family Scene",
          title: "Family",
          summary: "Household mode, routines, and family coordination surfaces.",
        }},
        build: {{
          kicker: "Build Scene",
          title: "Build",
          summary: "Workshop state, fabrication readiness, and current maker work.",
        }},
        faith: {{
          kicker: "Faith Scene",
          title: "Faith",
          summary: "Chronicle-focused spiritual formation handoff and continuity.",
        }},
        system: {{
          kicker: "System Scene",
          title: "System",
          summary: "Shell posture, runtime status, provider readiness, and configuration access.",
        }},
      }}[String(sceneId || "").trim().toLowerCase()] || {{
        kicker: "Focused Scene",
        title: "Scene",
        summary: "Focused shell view.",
      }};
    }}

    function chamberHomeSectionMarkup(items = [], label = "", options = {{}}) {{
      const approval = !!options.approval;
      const quiet = !!options.quiet;
      const maxItems = Math.max(1, Number(options.maxItems || items.length || 1));
      const visibleItems = items.slice(0, maxItems);
      const overflowCount = Math.max(0, items.length - visibleItems.length);
      const extraClass = String(options.className || "").trim();
      const blockClass = `core-home-block${{quiet ? " quiet" : ""}}${{extraClass ? ` ${{extraClass}}` : ""}}`;
      const itemClass = `core-home-item${{approval ? " approval" : ""}}${{quiet ? " quiet" : ""}}`;
      if (!items.length) {{
        return `
          <div class="${{blockClass}}">
            <div class="core-home-label">${{escapeHtml(label)}}</div>
            <div class="core-home-list">
              <div class="core-home-empty">${{escapeHtml(options.emptyLabel || "Nothing is waiting here right now.")}}</div>
            </div>
          </div>
        `;
      }}
      return `
        <div class="${{blockClass}}">
          <div class="core-home-label">${{escapeHtml(label)}}</div>
          <div class="core-home-list">
            ${{
              visibleItems.map((item) => `
                <div class="${{itemClass}}">
                  <strong>${{escapeHtml(item.title || label)}}</strong><br>
                  ${{escapeHtml(item.body || "")}}
                </div>
              `).join("")
            }}
            ${{
              overflowCount > 0
                ? `<div class="core-home-overflow">${{escapeHtml(`+${{overflowCount}} more waiting`)}}</div>`
                : ""
            }}
          </div>
        </div>
      `;
    }}

    function chamberRouteId(chamber = {{}}) {{
      const routeId = chamber?.device_context?.route?.route_id
        || state.currentDevice?.interface_route?.route_id
        || document.body.dataset.interfaceRoute
        || "";
      return String(routeId || "").trim().toLowerCase() || "standard-chamber";
    }}

    function chamberHeroMarkup(chamber = {{}}, routeId = "standard-chamber") {{
      const recommendation = chamber.recommendation || {{}};
      const summary = chamber.summary || {{}};
      const mobileVariant = chamber?.device_context?.mobile_remote_variant || state.currentDevice?.mobile_remote_variant || {{}};
      const isChildSafeRemote = mobileVariant.variant_id === "child-safe-remote";
      const heroClass = routeId === "family-display"
        ? "family"
        : (routeId === "mobile-remote-briefing" || routeId === "mobile-companion" ? "mobile" : "");
      const meta = [
        Number(summary.needs_you_count || 0) > 0 ? `${{summary.needs_you_count}} decision${{Number(summary.needs_you_count) === 1 ? "" : "s"}}` : "",
        Number(summary.already_working_count || 0) > 0 ? `${{summary.already_working_count}} prepared` : "",
        routeId === "family-display" ? "household-safe view" : "",
        routeId === "mobile-remote-briefing" ? "remote quick brief" : "",
        isChildSafeRemote ? "simple safe view" : "",
      ].filter(Boolean);
      return `
        <div class="core-home-hero core-home-span-two ${{heroClass}}">
          <div class="core-home-hero-kicker">${{escapeHtml(
            routeId === "family-display"
              ? "Household view"
              : isChildSafeRemote
                ? "What matters next"
                : "Recommended next move"
          )}}</div>
          <div class="core-home-hero-title">${{escapeHtml(recommendation.label || "Start with a calm briefing")}}</div>
          <div class="core-home-hero-body">${{escapeHtml(recommendation.body || "JARVIS has the next move ready.")}}</div>
          ${{
            meta.length
              ? `<div class="core-home-hero-meta">${{meta.map((item) => `<div class="core-home-hero-chip">${{escapeHtml(item)}}</div>`).join("")}}</div>`
              : ""
          }}
        </div>
      `;
    }}

    function whileYouWereAwayCards(report = {{}}, maxItems = 2) {{
      const rows = [];
      const laneReports = Array.isArray(report.lane_reports) ? report.lane_reports : [];
      const stewardshipLanes = Array.isArray(report.stewardship_lanes) ? report.stewardship_lanes : [];
      if (laneReports.length) {{
        rows.push({{
          title: report.headline || "While You Were Away",
          body: laneReports.slice(0, 2).map((item) => item.summary || item.title || "").filter(Boolean).join(" ")
            || report.summary
            || "JARVIS kept several lanes moving while you were away.",
        }});
      }}
      stewardshipLanes.slice(0, 2).forEach((lane) => {{
        const summary = Array.isArray(lane.report_summaries) && lane.report_summaries.length
          ? lane.report_summaries[0]?.summary || lane.summary || ""
          : lane.summary || "";
        const chips = [
          `Prepared ${{Array.isArray(lane.prepared_work) ? lane.prepared_work.length : 0}}`,
          `Decisions ${{Array.isArray(lane.decision_cards) ? lane.decision_cards.length : 0}}`,
        ];
        rows.push({{
          title: lane.title || "Stewardship lane",
          body: [summary, chips.join(" · ")].filter(Boolean).join(" · "),
        }});
      }});
      [["quiet_completions", "Quiet completion"], ["prepared_work", "Prepared"], ["blocked_work", "Blocked"]].forEach(([key, label]) => {{
        const item = Array.isArray(report[key]) ? report[key][0] : null;
        if (!item) {{
          return;
        }}
        rows.push({{
          title: `${{label}} · ${{item.title || item.lane || "Update"}}`,
          body: [item.agent, item.summary].filter(Boolean).join(" · "),
        }});
      }});
      if (report.recommendation) {{
        rows.push({{
          title: report.recommendation.title || "Recommendation",
          body: report.recommendation.summary || report.recommendation.action || "",
        }});
      }}
      return rows.slice(0, maxItems);
    }}

    function chamberCommandCards(chamber = {{}}, maxItems = 2) {{
      const aggregate = chamber.home_aggregate || {{}};
      const items = Array.isArray(aggregate.command_items) ? aggregate.command_items : [];
      return items.slice(0, maxItems).map((item) => ({{
        title: item.title || "Command",
        body: [item.detail, item.priority === "high" ? "High priority" : ""].filter(Boolean).join(" · "),
      }}));
    }}

    function deriveChamberHomeSignalModel(data = {{}}) {{
      const chamber = data.chamber_home || null;
      if (!chamber) {{
        const summary = triageSummaryModel(data);
        return {{
          chamber: null,
          routeId: "triage",
          summary,
          recommendationCards: [],
          whileAwayCards: [],
          commandCards: [],
          briefingItems: [],
          needsYou: [],
          alreadyWorking: [],
          chips: summary.chips || [],
        }};
      }}
      return {{
        chamber,
        routeId: chamberRouteId(chamber),
        summary: chamber.summary || {{}},
        recommendationCards: (chamber.drift_risk || []).concat(
          chamber.recommendation
            ? [{{ title: chamber.recommendation.label || "Recommended next move", body: chamber.recommendation.body || "" }}]
            : []
        ),
        whileAwayCards: whileYouWereAwayCards(chamber.while_you_were_away || {{}}, 3),
        commandCards: chamberCommandCards(chamber, 2),
        briefingItems: chamber.briefing_items || [],
        needsYou: chamber.needs_you || [],
        alreadyWorking: chamber.already_working || [],
        chips: chamber.chips || [],
      }};
    }}

    function applyCoreHomeActions(chamber = {{}}) {{
      const primary = document.getElementById("core-home-primary-action");
      const secondary = document.getElementById("core-home-secondary-action");
      const tertiary = document.getElementById("core-home-tertiary-action");
      const speak = document.getElementById("core-home-speak-action");
      const recommendation = chamber.recommendation || {{}};
      const routeId = chamberRouteId(chamber);
      const mobileVariant = chamber?.device_context?.mobile_remote_variant || state.currentDevice?.mobile_remote_variant || {{}};
      const isChildSafeRemote = mobileVariant.variant_id === "child-safe-remote";
      if (primary) {{
        primary.textContent =
          routeId === "mobile-remote-briefing" || routeId === "mobile-companion"
            ? "Next"
            : routeId === "desktop-command"
            ? (recommendation.label || "Open Command Brief")
            : routeId === "family-display"
              ? "Open Household View"
              : (recommendation.label || "Open Briefing");
        primary.setAttribute("data-home-open-packet", recommendation.packet || "briefing");
      }}
      if (secondary) {{
        secondary.textContent =
          routeId === "family-display"
            ? "Family"
            : isChildSafeRemote
              ? ((chamber.needs_you || []).length ? "Needs You" : "Today")
            : (chamber.needs_you || []).length
              ? (routeId === "desktop-command" ? "Decision Queue" : "Needs You")
              : "Open Day";
        secondary.setAttribute("data-home-open-packet", (chamber.needs_you || []).length ? "approvals" : "today");
      }}
      if (tertiary) {{
        tertiary.textContent =
          routeId === "family-display"
            ? "Watchlist"
            : routeId === "mobile-remote-briefing" || routeId === "mobile-companion"
              ? ((chamber.already_working || []).length ? "Prepared" : "Ready")
            : (chamber.already_working || []).length
              ? (routeId === "desktop-command" ? "Prepared Work" : "See Prepared Work")
              : "Resume Work";
        tertiary.setAttribute("data-home-open-packet", (chamber.already_working || [])[0]?.packet || "catalyst");
      }}
      if (speak) {{
        speak.textContent = isChildSafeRemote ? "Ask" : "Speak";
      }}
    }}

    function renderCoreHomeSummary(data = {{}}) {{
      const kicker = document.getElementById("core-home-kicker");
      const line = document.getElementById("core-home-line");
      const preview = document.getElementById("core-home-preview");
      const status = document.getElementById("core-home-status");
      if (!line || !preview || !status) {{
        return;
      }}
      const signals = deriveChamberHomeSignalModel(data);
      const chamber = signals.chamber;
      const compactLaptopHome = window.innerHeight <= 940;
      if (!chamber) {{
        const summary = signals.summary;
        if (kicker) kicker.textContent = "Triage And Transition";
        line.textContent = summary.line;
        const previewItems = summary.priorityItems.slice(0, 1).map((item) => `
          <div class="core-home-item">
            <strong>${{escapeHtml(item.title || "Priority")}}</strong><br>
            ${{escapeHtml(item.next_action || item.status || "Needs attention")}}
          </div>
        `).concat(summary.resumeItems.slice(0, 1).map((item) => `
          <div class="core-home-item${{item.approval ? " approval" : ""}}">
            <strong>${{escapeHtml(item.title || "Resume")}}</strong><br>
            ${{escapeHtml(item.body || "Return to the active thread.")}}
          </div>
        `));
        preview.innerHTML = previewItems.length
          ? previewItems.join("")
          : `<div class="core-home-empty">No approvals or resume targets are waiting.</div>`;
        status.innerHTML = summary.chips.map((chip) => `<div class="core-home-chip">${{escapeHtml(chip)}}</div>`).join("");
        return;
      }}
      if (kicker) {{
        kicker.textContent = chamber.kicker || "Private Intelligence Chamber";
      }}
      const routeId = chamberRouteId(chamber);
      preview.dataset.route = routeId;
      const mobileVariant = chamber?.device_context?.mobile_remote_variant || state.currentDevice?.mobile_remote_variant || {{}};
      const isChildSafeRemote = mobileVariant.variant_id === "child-safe-remote";
      const greetingText = String(chamber.greeting || "").trim();
      const stateLineText = String(chamber.state_line || "").trim();
      const normalizedStateLine = /^good\\s+(morning|afternoon|evening)\\b/i.test(stateLineText)
        ? stateLineText.replace(/^good\\s+(morning|afternoon|evening)\\s*,?\\s+[^.?!]+[.?!-:]\\s*/i, "").trim()
        : stateLineText;
      line.textContent = [greetingText, normalizedStateLine].filter(Boolean).join(" ");
      const whileAwayCards = signals.whileAwayCards.slice(0, compactLaptopHome ? 2 : 3);
      const commandCards = signals.commandCards.slice(0, compactLaptopHome ? 1 : 2);
      const recommendationCards = signals.recommendationCards;
      let previewMarkup = "";
      if (routeId === "mobile-remote-briefing" || routeId === "mobile-companion") {{
        previewMarkup = `
          <div class="core-home-grid route-mobile">
            ${{chamberHeroMarkup(chamber, routeId)}}
            ${{
              chamberHomeSectionMarkup(chamber.needs_you || [], isChildSafeRemote ? "Today" : "Needs You", {{
                emptyLabel: isChildSafeRemote
                  ? "Nothing hard is waiting on you right now."
                  : "No approvals or decisions are waiting right now.",
                approval: true,
                maxItems: isChildSafeRemote ? 1 : 2,
              }})
            }}
            ${{
              chamberHomeSectionMarkup(chamber.briefing_items || [], isChildSafeRemote ? "For Today" : "Briefing", {{
                emptyLabel: isChildSafeRemote
                  ? "JARVIS has a calm day view ready."
                  : "No major briefing items are pressing right now.",
                maxItems: 1,
              }})
            }}
            ${{
              chamberHomeSectionMarkup(
                (chamber.already_working || []).length ? (chamber.already_working || []) : recommendationCards,
                isChildSafeRemote
                  ? ((chamber.already_working || []).length ? "Ready" : "Keep In View")
                  : ((chamber.already_working || []).length ? "Prepared" : "Keep In View"),
                {{
                  emptyLabel: isChildSafeRemote
                    ? "JARVIS has nothing extra waiting in the background."
                    : "JARVIS is quiet in the background at the moment.",
                  quiet: true,
                  maxItems: 1,
                }}
              )
            }}
          </div>
        `;
      }} else if (routeId === "tablet-chamber") {{
        previewMarkup = `
          <div class="core-home-grid route-tablet">
            ${{chamberHeroMarkup(chamber, routeId)}}
            ${{
              chamberHomeSectionMarkup(chamber.briefing_items || [], "Briefing", {{
                emptyLabel: "No major briefing items are pressing right now.",
                maxItems: 2,
              }})
            }}
            ${{
              chamberHomeSectionMarkup(chamber.needs_you || [], "Needs You", {{
                emptyLabel: "No approvals or decisions are waiting right now.",
                approval: true,
                maxItems: 2,
              }})
            }}
            ${{
              chamberHomeSectionMarkup(chamber.already_working || [], "Prepared Work", {{
                emptyLabel: "JARVIS is quiet in the background at the moment.",
                quiet: true,
                maxItems: compactLaptopHome ? 1 : 2,
              }})
            }}
            ${{
              whileAwayCards.length
                ? chamberHomeSectionMarkup(whileAwayCards, "While You Were Away", {{
                    emptyLabel: "No absence summary is ready yet.",
                    quiet: true,
                    maxItems: compactLaptopHome ? 1 : 2,
                  }})
                : chamberHomeSectionMarkup(commandCards, "Command Board", {{
                    emptyLabel: "No command lanes are active right now.",
                    quiet: true,
                    maxItems: compactLaptopHome ? 1 : 2,
                  }})
            }}
            ${{
              chamberHomeSectionMarkup(recommendationCards, "Watchlist And Next", {{
                emptyLabel: "The chamber is calm right now.",
                quiet: true,
                maxItems: compactLaptopHome ? 1 : 2,
              }})
            }}
          </div>
        `;
      }} else if (routeId === "family-display") {{
        previewMarkup = `
          <div class="core-home-grid route-family">
            ${{chamberHeroMarkup(chamber, routeId)}}
            ${{
              chamberHomeSectionMarkup(chamber.briefing_items || [], "Household Watch", {{
                emptyLabel: "No household pressure is surfacing right now.",
                maxItems: 2,
              }})
            }}
            ${{
              chamberHomeSectionMarkup(chamber.already_working || [], "Quietly In Motion", {{
                emptyLabel: "Nothing household-facing is being staged right now.",
                quiet: true,
                maxItems: 1,
              }})
            }}
            ${{
              chamberHomeSectionMarkup(recommendationCards, "Keep In View", {{
                emptyLabel: "The household picture is calm right now.",
                quiet: true,
                maxItems: 1,
              }})
            }}
          </div>
        `;
      }} else {{
        previewMarkup = `
          <div class="core-home-grid route-desktop">
            ${{chamberHeroMarkup(chamber, routeId)}}
            ${{
              chamberHomeSectionMarkup(chamber.briefing_items || [], "Briefing", {{
                emptyLabel: "No major briefing items are pressing right now.",
                maxItems: compactLaptopHome ? 2 : 2,
              }})
            }}
            ${{
              chamberHomeSectionMarkup(chamber.needs_you || [], "Decision Queue", {{
                emptyLabel: "No approvals or decisions are waiting right now.",
                approval: true,
                maxItems: compactLaptopHome ? 2 : 2,
              }})
            }}
            ${{
              chamberHomeSectionMarkup(chamber.already_working || [], "Prepared Work", {{
                emptyLabel: "JARVIS is quiet in the background at the moment.",
                quiet: true,
                maxItems: compactLaptopHome ? 1 : 2,
              }})
            }}
            ${{
              whileAwayCards.length
                ? chamberHomeSectionMarkup(whileAwayCards, "While You Were Away", {{
                    emptyLabel: "No absence summary is ready yet.",
                    quiet: true,
                    maxItems: compactLaptopHome ? 1 : 2,
                  }})
                : chamberHomeSectionMarkup(commandCards, "Command Board", {{
                    emptyLabel: "No command lanes are active right now.",
                    quiet: true,
                    maxItems: compactLaptopHome ? 1 : 2,
                  }})
            }}
            ${{
              chamberHomeSectionMarkup(recommendationCards, "Watchlist And Next", {{
                emptyLabel: "The chamber is calm right now.",
                quiet: true,
                maxItems: compactLaptopHome ? 1 : 2,
              }})
            }}
          </div>
        `;
      }}
      preview.innerHTML = previewMarkup;
      const visibleChips = routeId === "family-display"
        ? (chamber.chips || []).slice(0, 2)
        : isChildSafeRemote
          ? (chamber.chips || []).slice(0, 2)
        : (routeId === "mobile-remote-briefing" || routeId === "mobile-companion"
            ? (chamber.chips || []).slice(0, 3)
            : (chamber.chips || []));
      status.innerHTML = visibleChips.map((chip) => `<div class="core-home-chip">${{escapeHtml(chip)}}</div>`).join("");
      applyCoreHomeActions(chamber);
      const input = document.getElementById("command-input");
      if (input && chamber.speak_freely?.placeholder) {{
        input.setAttribute("placeholder", chamber.speak_freely.placeholder);
      }}
    }}

    function formatVoiceStateLabel(value, fallback = "not checked yet") {{
      if (!value) {{
        return fallback;
      }}
      return String(value).replace(/_/g, " ");
    }}

    function compactVoiceDiagnostic(value, fallback = "--") {{
      const text = String(value || "").trim();
      if (!text) {{
        return fallback;
      }}
      return text.length > 140 ? `${{text.slice(0, 137)}}...` : text;
    }}

    function selectedVoiceConfiguredReadiness(stackStatus = {{}}) {{
      if (stackStatus.selected_tts_provider_ready === true) {{
        return "ready";
      }}
      return formatVoiceStateLabel(stackStatus.selected_tts_provider_state, "not ready");
    }}

    function selectedVoiceLiveReadiness(stackStatus = {{}}) {{
      if (stackStatus.selected_tts_provider_live_ready === true) {{
        return "live";
      }}
      return formatVoiceStateLabel(stackStatus.selected_tts_provider_live_state, "not checked yet");
    }}

    function selectedVoiceLiveBlocker(stackStatus = {{}}) {{
      if (stackStatus.selected_tts_provider_live_ready === false) {{
        return compactVoiceDiagnostic(stackStatus.selected_tts_provider_live_reason, "live blocker recorded");
      }}
      return "none recorded";
    }}

    function selectedVoiceLiveFallback(stackStatus = {{}}) {{
      return stackStatus.last_live_effective_tts_provider || "none recorded";
    }}

    function sceneSettingsMarkup(data = {{}}) {{
      const settings = state.voiceSettings || {{}};
      const stackStatus = state.voiceOptions?.stack_status || settings.stack_status || {{}};
      const googleWorkspace = data.google_workspace || {{}};
      const runtimeSummary = `
        <div class="metric"><strong>Configured source</strong> ${{escapeHtml(settings.selected_provider_label || "--")}}</div>
        <div class="metric"><strong>Configured readiness</strong> ${{escapeHtml(selectedVoiceConfiguredReadiness(stackStatus))}}</div>
        <div class="metric"><strong>Last live readiness</strong> ${{escapeHtml(selectedVoiceLiveReadiness(stackStatus))}}</div>
        <div class="metric"><strong>Last live blocker</strong> ${{escapeHtml(selectedVoiceLiveBlocker(stackStatus))}}</div>
        <div class="metric"><strong>Last live fallback</strong> ${{escapeHtml(selectedVoiceLiveFallback(stackStatus))}}</div>
        <div class="metric"><strong>TTS order</strong> ${{escapeHtml((stackStatus.tts_order || []).join(" → ") || "--")}}</div>
      `;
      const workspaceSummary = `
        <div class="metric"><strong>Google client</strong> ${{googleWorkspace.client_secret?.present ? "saved" : "missing"}}</div>
        <div class="metric"><strong>Accounts</strong> ${{escapeHtml(String((googleWorkspace.accounts || []).length))}}</div>
        <div class="metric"><strong>Bridge</strong> ${{googleWorkspace.default_account_status?.connected ? "connected" : "needs attention"}}</div>
      `;
      return `
        <div class="packet-grid">
          ${{packetBlock("Runtime Posture", `
            <div class="stack">
              <div class="metric"><strong>Voice state</strong> ${{escapeHtml(document.body.dataset.voiceState || "idle")}}</div>
              <div class="metric"><strong>Shell layout</strong> ${{escapeHtml(document.body.dataset.shellLayout || "quiet-home")}}</div>
              <div class="metric"><strong>Scene mode</strong> focused primary panel</div>
            </div>
          `)}}
          ${{packetBlock("Provider Readiness", `<div class="stack">${{runtimeSummary}}</div>`)}}
          ${{packetBlock("Workspace Identity", `<div class="stack">${{workspaceSummary}}</div>`)}}
          ${{packetBlock("Configuration", `
            <div class="stack">
              <p>Use this scene for posture and readiness. Reach approvals or household mode changes directly from here while we keep the shell in focused-scene mode.</p>
              <div class="inline-actions">
                <button type="button" id="scene-open-full-settings">Open Full Settings</button>
                <button type="button" id="scene-open-mode-panel">Open Household Mode</button>
                <button type="button" id="scene-open-approvals">Open Approvals</button>
              </div>
            </div>
          `)}}
        </div>
      `;
    }}

    function renderHomePacketMarkup(data = {{}}) {{
      return homeConnectorLive(data) ? `
        <div class="packet-grid">
          ${{
            packetBlock("House Summary", renderList((data.home_overview?.summary || []).map((item) => `<div>${{escapeHtml(item)}}</div>`)))
          }}
          ${{
            packetBlock("Climate and Garage", `
              <div class="stack">
                <div class="metric"><strong>Climate</strong> ${{escapeHtml(data.climate_status?.[0]?.attributes?.targetTemperature || "--")}}° target</div>
                <div class="metric"><strong>Garage</strong> ${{escapeHtml(data.garage_status?.[0]?.state || "--")}}</div>
                <div class="metric"><strong>Home Mode</strong> ${{escapeHtml(data.home_overview?.mode || "--")}}</div>
              </div>`)
          }}
          ${{
            packetBlock("Leak Watch", renderList((data.leak_monitor?.all_sensors || []).map((item) => `<div>${{escapeHtml(item.name)}} · ${{escapeHtml(item.state)}}</div>`)))
          }}
          ${{
            packetBlock("Cold Storage", renderList((data.cold_storage_monitor?.all_sensors || []).map((item) => `<div>${{escapeHtml(item.name)}} · ${{escapeHtml(item.severity)}} · variance ${{escapeHtml(String(item.variance_degrees))}}F</div>`)))
          }}
        </div>` : `
        <div class="packet-grid">
          ${{
            packetBlock("Home Assistant Unavailable", `<p>Live home state is unavailable until Home Assistant is connected. Staged house data is hidden.</p>`)
          }}
        </div>`;
    }}

    function renderFamilyPacketMarkup(data = {{}}) {{
      return `
        <div class="packet-grid">
          ${{
            packetBlock("Mode Brief", `<p>${{escapeHtml(data.mode_brief?.summary || "")}}</p>${{renderList((data.mode_brief?.actions || []).map((item) => `<div>${{escapeHtml(item)}}</div>`))}}`)
          }}
          ${{
            packetBlock("Departure", renderList((data.departure_runs?.[0]?.checklist || data.departure_checklist || []).map((item) => `<div>${{escapeHtml(item)}}</div>`)))
          }}
          ${{
            packetBlock("Household Focus", renderList(Object.entries(data.family_focus || {{}}).map(([name, items]) => `<div><strong>${{escapeHtml(name)}}:</strong> ${{escapeHtml((items || []).join(", "))}}</div>`)))
          }}
        </div>`;
    }}

    function renderWorkshopPacketMarkup(data = {{}}) {{
      return `
        <div class="packet-grid">
          ${{
            packetBlock("Printer Status", renderList((data.printer_status || []).map((item) => `<div><strong>${{escapeHtml(item.name)}}</strong> · ${{escapeHtml(item.status)}} · ${{escapeHtml(String(item.progress_percent))}}%</div>`)))
          }}
          ${{
            packetBlock("Vendor Prep", renderList((data.vendor_preps || []).map((item) => `<div><strong>${{escapeHtml(item.part_name)}}</strong> · ${{escapeHtml(item.status)}}</div>`)))
          }}
          ${{
            packetBlock("Inspections", renderList((data.workshop_inspections || []).map((item) => `<div><strong>${{escapeHtml(item.part_name)}}</strong><br>${{escapeHtml(item.diagnosis)}}</div>`)))
          }}
          ${{
            packetBlock("Safety", renderList((data.safety_checks || []).map((item) => `<div><strong>${{escapeHtml(item.operation)}}</strong> · ${{item.allowed ? "allowed" : "blocked"}}</div>`)))
          }}
          ${{
            packetBlock("Model Forge", `
              <div class="stack">
                <div class="metric"><strong>Latest</strong> ${{escapeHtml(data.cad_packages?.[0]?.part_name || "No model package yet")}}</div>
                <div class="metric"><strong>Status</strong> ${{escapeHtml(data.cad_packages?.[0]?.export_status || "--")}}</div>
                <div class="inline-actions" style="margin-top:10px;">
                  <button type="button" id="open-model-forge-packet">Open Viewer</button>
                </div>
              </div>`)
          }}
        </div>`;
    }}

    function renderChroniclePacketMarkup() {{
      return `
        <div class="chronicle-workspace-shell">
          <div class="chronicle-handoff-bar">
            <div class="chronicle-handoff-copy">
              <strong>Sent to Chronicle</strong>
              <span id="chronicle-handoff-summary">Preparing Chronicle…</span>
            </div>
            <div class="chronicle-handoff-actions">
              <button type="button" id="chronicle-send-button">Send to Chronicle</button>
              <button type="button" class="ghost-toggle" id="chronicle-open-app">Open Chronicle App</button>
            </div>
          </div>
          <div class="workspace-frame">
            <iframe id="chronicle-workspace-frame" title="Chronicle Workspace" src="about:blank"></iframe>
          </div>
        </div>`;
    }}

    function triageSummaryModel(data = {{}}) {{
      const board = data.today_board || {{}};
      const assistantSurface = data.assistant_surface || {{}};
      const approvalHistory = (data.explainability?.approval_history || []).filter((item) => item.status === "pending");
      const priorityItems = (board.priorities || []).slice(0, 5);
      const resumeItems = [];
      if (assistantSurface.auto_open_packet) {{
        const packetName = String(assistantSurface.auto_open_packet || "today")
          .replaceAll("-", " ")
          .replace(/\\b\\w/g, (char) => char.toUpperCase());
        resumeItems.push({{
          title: "Resume",
          body: `Return to ${{packetName}}.`,
          packet: assistantSurface.auto_open_packet,
        }});
      }}
      approvalHistory.slice(0, 3).forEach((item) => {{
        resumeItems.unshift({{
          title: String(item.actor || "Approval"),
          body: String(item.request || "Pending approval"),
          approval: true,
          packet: "approvals",
        }});
      }});
      const briefingLine =
        String((assistantSurface.briefing_lines || [])[0] || "").trim() ||
        String(board.summary || "").trim() ||
        String(data.last_briefing || "").trim();
      const chips = [];
      const activeMode = String(data.active_mode?.mode || "").trim();
      if (activeMode) {{
        chips.push(`Mode: ${{activeMode.replaceAll("-", " ")}}`);
      }}
      chips.push(degradedInfo(data)?.active ? "Cached" : "Live");
      if ((data.truth || {{}}).home_live) {{
        chips.push("Home Connected");
      }}
      if ((data.truth || {{}}).watch_live) {{
        chips.push("Watch Live");
      }}
      if (approvalHistory.length) {{
        chips.push(`${{approvalHistory.length}} approval${{approvalHistory.length === 1 ? "" : "s"}} pending`);
      }}
      if (priorityItems.length) {{
        chips.push(priorityItems.length === 1 ? "1 priority active" : `${{priorityItems.length}} priorities active`);
      }}
      return {{
        line: briefingLine || `Watching ${{priorityItems.length}} priority signal(s) and ${{approvalHistory.length}} approval item(s).`,
        priorityItems,
        resumeItems,
        chips,
      }};
    }}

    function renderTriagePacketMarkup(data = {{}}) {{
      const summary = triageSummaryModel(data);
      return `
        <div class="packet-grid">
          ${{
            packetBlock(
              "Triage Posture",
              `
                <p>${{escapeHtml(summary.line)}}</p>
                <div class="core-home-status">
                  ${{
                    summary.chips.length
                      ? summary.chips.map((chip) => `<span>${{escapeHtml(chip)}}</span>`).join("")
                      : `<span>Standby</span>`
                  }}
                </div>
              `
            )
          }}
          ${{
            packetBlock(
              "Priority Signals",
              summary.priorityItems.length
                ? renderList(summary.priorityItems.map((item) => `
                    <div>
                      <strong>${{escapeHtml(item.title || "Priority")}}</strong>
                      <br>${{escapeHtml(item.owner_agent || "JARVIS")}} · ${{escapeHtml(item.next_action || item.status || "Needs attention")}}
                    </div>
                  `))
                : `<div class="core-home-empty">No active priority signals are loaded.</div>`
            )
          }}
          ${{
            packetBlock(
              "Approvals And Resume",
              summary.resumeItems.length
                ? renderList(summary.resumeItems.map((item) => `
                    <div class="${{item.approval ? "core-home-item approval" : "core-home-item"}}">
                      <strong>${{escapeHtml(item.title || "Resume")}}</strong>
                      <br>${{escapeHtml(item.body || "Return to the active thread.")}}
                    </div>
                  `))
                : `<div class="core-home-empty">No approvals or resume targets are waiting.</div>`
            )
          }}
          ${{
            packetBlock(
              "Transition Actions",
              `
                <div class="inline-actions">
                  <button type="button" id="triage-open-day">Open Day</button>
                  <button type="button" id="triage-open-approvals" class="ghost-toggle">Open Approvals</button>
                  <button type="button" id="triage-open-catalyst" class="ghost-toggle">Resume Work</button>
                </div>
              `
            )
          }}
        </div>`;
    }}

    function scenePacketMarkup(packetId, data = {{}}) {{
      if (packetId === "today") {{
        const board = data.today_board || {{}};
        const notifications = board.assistant_notifications || {{}};
        const notificationPolicy = board.notification_policy || {{}};
        const quietWindow = notificationPolicy.quiet_window || {{}};
        const browserAlertStatus = !browserAlertsSupported()
          ? "Browser alerts are not supported on this device."
          : state.browserAlertsPermission === "granted" && state.browserAlertsEnabled
            ? "Browser alerts are active for assistant follow-up."
            : state.browserAlertsPermission === "denied"
              ? "Browser alerts are blocked by the browser for this device."
              : "Browser alerts are available but not enabled yet.";
        return `
          <div class="packet-grid">
            ${{renderFreshnessBanner(board, "Today Board")}}
            ${{
              packetBlock("Priorities", renderList((board.priorities || []).map((item) => `
                <div>
                  <strong>${{escapeHtml(item.title || "Priority")}}</strong>
                  <br>${{escapeHtml(item.owner_agent || "JARVIS")}} · ${{escapeHtml(item.next_action || "follow up")}} · ${{escapeHtml(item.status || "open")}}
                </div>
              `)))
            }}
            ${{
              packetBlock("Carry Today", renderList((board.carry || []).map((item) => `<div>${{escapeHtml(item)}}</div>`)))
            }}
            ${{
              packetBlock("Calendar Pressure", renderList((board.calendar || []).map((item) => `<div><strong>${{escapeHtml(item.summary || "(Untitled event)")}}</strong><br>${{escapeHtml(item.start || "")}}</div>`)))
            }}
            ${{
              packetBlock("Autonomy Boundary", renderList((board.autonomy || []).map((item) => `<div>${{escapeHtml(item)}}</div>`)))
            }}
            ${{
              packetBlock(
                "Assistant Inbox",
                `
                  <p>${{escapeHtml(browserAlertStatus)}}</p>
                  <div class="inline-actions" style="margin:0 0 10px 0;">
                    <button class="btn btn-secondary" id="enable-browser-alerts" type="button">Enable Browser Alerts</button>
                    <button class="btn btn-subtle" id="disable-browser-alerts" type="button">Mute Browser Alerts</button>
                  </div>
                  <div class="metric"><strong>Delivery policy</strong> ${{
                    notificationPolicy.quiet_hours_active
                      ? `Quiet hours active · ${{escapeHtml(quietWindow.start || "22:00")}} to ${{escapeHtml(quietWindow.end || "06:00")}}`
                      : `Active hours · browser-eligible items may interrupt`
                  }}</div>
                  <div class="metric"><strong>Inbox state</strong> unseen ${{escapeHtml(String(notifications.summary?.by_status?.unseen || 0))}} · surfaced ${{escapeHtml(String(notifications.summary?.by_status?.surfaced || 0))}} · opened ${{escapeHtml(String(notifications.summary?.by_status?.opened || 0))}}</div>
                  ${{
                    notifications.summary?.unread
                      ? renderAssistantInboxItems(notifications.items || [])
                      : "<p>No unread assistant nudges are waiting right now.</p>"
                  }}
                `
              )
            }}
          </div>`;
      }}
      if (packetId === "home") return renderHomePacketMarkup(data);
      if (packetId === "family") {{
        return renderFamilyPacketMarkup(data);
      }}
      if (packetId === "workshop") {{
        return renderWorkshopPacketMarkup(data);
      }}
      if (packetId === "chronicle") {{
        return renderChroniclePacketMarkup();
      }}
      if (packetId === "settings") {{
        return sceneSettingsMarkup(data);
      }}
      return `<div class="packet-grid"><div class="metric">Scene unavailable.</div></div>`;
    }}

    function renderDaySceneMarkup(data = {{}}, signals = {{}}) {{
      const board = data.today_board || {{}};
      const priorities = Array.isArray(board.priorities) ? board.priorities : [];
      const needsYou = (signals.needsYou || []).slice(0, 3);
      const prepared = (signals.alreadyWorking || []).slice(0, 3);
      const whileAway = (signals.whileAwayCards || []).slice(0, 2);
      return `
        <div class="packet-grid">
          ${{
            packetBlock(
              "Priorities",
              priorities.length
                ? renderList(priorities.map((item) => `
                    <div>
                      <strong>${{escapeHtml(item.title || "Priority")}}</strong>
                      <br>${{escapeHtml(item.next_action || item.status || "Needs attention")}}
                    </div>
                  `))
                : `<div class="core-home-empty">No major priorities are pressing right now.</div>`
            )
          }}
          ${{
            packetBlock(
              "Decision Queue",
              needsYou.length
                ? renderList(needsYou.map((item) => `
                    <div class="core-home-item approval">
                      <strong>${{escapeHtml(item.title || "Decision")}}</strong>
                      <br>${{escapeHtml(item.body || "Review the next decision.")}}
                    </div>
                  `))
                : `<div class="core-home-empty">No approvals or decisions are waiting right now.</div>`
            )
          }}
          ${{
            packetBlock(
              "Prepared Work",
              prepared.length
                ? renderList(prepared.map((item) => `
                    <div class="core-home-item quiet">
                      <strong>${{escapeHtml(item.title || "Prepared")}}</strong>
                      <br>${{escapeHtml(item.body || "JARVIS has something ready.")}}
                    </div>
                  `))
                : `<div class="core-home-empty">Nothing is quietly queued right now.</div>`
            )
          }}
          ${{
            packetBlock(
              "Carry Forward",
              whileAway.length
                ? renderList(whileAway.map((item) => `<div><strong>${{escapeHtml(item.title || "Update")}}</strong><br>${{escapeHtml(item.body || "")}}</div>`))
                : renderList((board.carry || []).map((item) => `<div>${{escapeHtml(item)}}</div>`))
            )
          }}
        </div>`;
    }}

    function renderHomeSceneMarkup(data = {{}}, signals = {{}}) {{
      const routeSummary = signals.chamber?.state_line || "Household state is available.";
      const commands = (signals.commandCards || []).slice(0, 2);
      return homeConnectorLive(data) ? `
        <div class="packet-grid">
          ${{
            packetBlock("House Summary", `
              <p>${{escapeHtml(routeSummary)}}</p>
              ${{renderList((data.home_overview?.summary || []).map((item) => `<div>${{escapeHtml(item)}}</div>`))}}
            `)
          }}
          ${{
            packetBlock("Climate and Garage", `
              <div class="stack">
                <div class="metric"><strong>Climate</strong> ${{escapeHtml(data.climate_status?.[0]?.attributes?.targetTemperature || "--")}}° target</div>
                <div class="metric"><strong>Garage</strong> ${{escapeHtml(data.garage_status?.[0]?.state || "--")}}</div>
                <div class="metric"><strong>Home Mode</strong> ${{escapeHtml(data.home_overview?.mode || "--")}}</div>
              </div>`)
          }}
          ${{
            packetBlock("Leak Watch", renderList((data.leak_monitor?.all_sensors || []).map((item) => `<div>${{escapeHtml(item.name)}} · ${{escapeHtml(item.state)}}</div>`)))
          }}
          ${{
            packetBlock(
              "Command Board",
              commands.length
                ? renderList(commands.map((item) => `<div><strong>${{escapeHtml(item.title || "Command")}}</strong><br>${{escapeHtml(item.body || "")}}</div>`))
                : `<div class="core-home-empty">No command lanes are active right now.</div>`
            )
          }}
        </div>` : `
        <div class="packet-grid">
          ${{
            packetBlock("Home Assistant Unavailable", `<p>Live home state is unavailable until Home Assistant is connected. Staged house data is hidden.</p>`)
          }}
        </div>`;
    }}

    function renderFamilySceneMarkup(data = {{}}, signals = {{}}) {{
      const recommendation = (signals.recommendationCards || [])[0];
      return `
        <div class="packet-grid">
          ${{
            packetBlock("Mode Brief", `<p>${{escapeHtml(data.mode_brief?.summary || signals.chamber?.state_line || "")}}</p>${{renderList((data.mode_brief?.actions || []).map((item) => `<div>${{escapeHtml(item)}}</div>`))}}`)
          }}
          ${{
            packetBlock("Departure", renderList((data.departure_runs?.[0]?.checklist || data.departure_checklist || []).map((item) => `<div>${{escapeHtml(item)}}</div>`)))
          }}
          ${{
            packetBlock("Household Focus", renderList(Object.entries(data.family_focus || {{}}).map(([name, items]) => `<div><strong>${{escapeHtml(name)}}:</strong> ${{escapeHtml((items || []).join(", "))}}</div>`)))
          }}
          ${{
            packetBlock(
              "Keep In View",
              recommendation
                ? `<div class="core-home-item quiet"><strong>${{escapeHtml(recommendation.title || "Next move")}}</strong><br>${{escapeHtml(recommendation.body || "")}}</div>`
                : `<div class="core-home-empty">The household picture is calm right now.</div>`
            )
          }}
        </div>`;
    }}

    function renderBuildSceneMarkup(data = {{}}, signals = {{}}) {{
      const prepared = (signals.alreadyWorking || []).slice(0, 2);
      return `
        <div class="packet-grid">
          ${{
            packetBlock("Printer Status", renderList((data.printer_status || []).map((item) => `<div><strong>${{escapeHtml(item.name)}}</strong> · ${{escapeHtml(item.status)}} · ${{escapeHtml(String(item.progress_percent))}}%</div>`)))
          }}
          ${{
            packetBlock("Vendor Prep", renderList((data.vendor_preps || []).map((item) => `<div><strong>${{escapeHtml(item.part_name)}}</strong> · ${{escapeHtml(item.status)}}</div>`)))
          }}
          ${{
            packetBlock("Inspections", renderList((data.workshop_inspections || []).map((item) => `<div><strong>${{escapeHtml(item.part_name)}}</strong><br>${{escapeHtml(item.diagnosis)}}</div>`)))
          }}
          ${{
            packetBlock(
              "Prepared Work",
              prepared.length
                ? renderList(prepared.map((item) => `<div><strong>${{escapeHtml(item.title || "Prepared")}}</strong><br>${{escapeHtml(item.body || "")}}</div>`))
                : `
                    <div class="stack">
                      <div class="metric"><strong>Latest</strong> ${{escapeHtml(data.cad_packages?.[0]?.part_name || "No model package yet")}}</div>
                      <div class="metric"><strong>Status</strong> ${{escapeHtml(data.cad_packages?.[0]?.export_status || "--")}}</div>
                      <div class="inline-actions" style="margin-top:10px;">
                        <button type="button" id="open-model-forge-packet">Open Viewer</button>
                      </div>
                    </div>
                  `
            )
          }}
        </div>`;
    }}

    function renderFaithSceneMarkup(data = {{}}, signals = {{}}) {{
      const whileAway = (signals.whileAwayCards || []).slice(0, 2);
      return `
        <div class="packet-grid">
          ${{
            packetBlock(
              "Formation Continuity",
              whileAway.length
                ? renderList(whileAway.map((item) => `<div><strong>${{escapeHtml(item.title || "Carry forward")}}</strong><br>${{escapeHtml(item.body || "")}}</div>`))
                : `<div class="core-home-empty">No spiritual carry-forward summary is ready yet.</div>`
            )
          }}
          <div class="chronicle-workspace-shell">
            <div class="chronicle-handoff-bar">
              <div class="chronicle-handoff-copy">
                <strong>Sent to Chronicle</strong>
                <span id="chronicle-handoff-summary">Preparing Chronicle…</span>
              </div>
              <div class="chronicle-handoff-actions">
                <button type="button" id="chronicle-send-button">Send to Chronicle</button>
                <button type="button" class="ghost-toggle" id="chronicle-open-app">Open Chronicle App</button>
              </div>
            </div>
            <div class="workspace-frame">
              <iframe id="chronicle-workspace-frame" title="Chronicle Workspace" src="about:blank"></iframe>
            </div>
          </div>
        </div>`;
    }}

    function renderSystemSceneMarkup(data = {{}}, signals = {{}}) {{
      const activeMode = data.active_mode || {{}};
      const recommendation = (signals.recommendationCards || [])[0];
      return `
        <div class="packet-grid">
          ${{
            packetBlock("Shell Posture", `
              <div class="metric"><strong>Mode</strong> ${{escapeHtml(activeMode.mode || "--")}}</div>
              <div class="metric"><strong>Status</strong> ${{escapeHtml(activeMode.status || "--")}}</div>
              <p>${{escapeHtml(activeMode.reason || signals.chamber?.state_line || "System posture is available.")}}</p>
            `)
          }}
          ${{
            packetBlock(
              "Governance And Next",
              recommendation
                ? `<div class="core-home-item quiet"><strong>${{escapeHtml(recommendation.title || "Recommendation")}}</strong><br>${{escapeHtml(recommendation.body || "")}}</div>`
                : `<div class="core-home-empty">No governance recommendation is surfaced right now.</div>`
            )
          }}
          ${{
            packetBlock(
              "Controls",
              `
                <div class="inline-actions">
                  <button type="button" id="scene-open-full-settings">Open Full Settings</button>
                  <button type="button" class="ghost-toggle" id="scene-open-mode-panel">Open Household Mode</button>
                  <button type="button" class="ghost-toggle" id="scene-open-approvals">Open Approvals</button>
                </div>
              `
            )
          }}
        </div>`;
    }}

    function renderSceneMarkup(sceneId, data = {{}}) {{
      const signals = deriveChamberHomeSignalModel(data);
      if (sceneId === "day") return renderDaySceneMarkup(data, signals);
      if (sceneId === "home") return renderHomeSceneMarkup(data, signals);
      if (sceneId === "family") return renderFamilySceneMarkup(data, signals);
      if (sceneId === "build") return renderBuildSceneMarkup(data, signals);
      if (sceneId === "faith") return renderFaithSceneMarkup(data, signals);
      if (sceneId === "system") return renderSystemSceneMarkup(data, signals);
      return `<div class="packet-grid"><div class="metric">Scene unavailable.</div></div>`;
    }}

    function wireScenePacket(packetId) {{
      if (packetId === "today") {{
        wireTodayBoardActions();
        wireAssistantInboxActions("today");
      }} else if (packetId === "workshop") {{
        document.getElementById("open-model-forge-packet")?.addEventListener("click", () => {{
          openPacket("model-forge");
        }});
      }} else if (packetId === "chronicle") {{
        wireChronicleWorkspace().catch((error) => {{
          const summary = document.getElementById("chronicle-handoff-summary");
          if (summary) {{
            summary.textContent = error?.message || "Chronicle workspace unavailable.";
          }}
        }});
      }} else if (packetId === "settings") {{
        document.getElementById("scene-open-full-settings")?.addEventListener("click", () => {{
          openPacket("settings", {{ bypassScene: true }});
        }});
        document.getElementById("scene-open-mode-panel")?.addEventListener("click", () => {{
          openModePanel();
        }});
        document.getElementById("scene-open-approvals")?.addEventListener("click", () => {{
          openPacket("approvals");
        }});
      }}
    }}

    function closeScene() {{
      state.activeScene = "";
      state.windowStates.scene.minimized = false;
      state.windowStates.scene.maximized = false;
      document.body.dataset.activeScene = "false";
      if (state.activeOverlay?.type === "scene") {{
        setActiveOverlay("");
      }}
      const stage = document.getElementById("scene-stage");
      const body = document.getElementById("scene-shell-body");
      if (stage) stage.classList.add("hidden");
      const shell = document.querySelector("#scene-stage .scene-shell");
      if (shell) {{
        shell.classList.remove("floating", "minimized", "maximized");
        shell.style.removeProperty("left");
        shell.style.removeProperty("top");
        shell.style.removeProperty("width");
        shell.style.removeProperty("height");
      }}
      if (body) body.innerHTML = "";
      syncShellFocusMode();
      renderContextActionDock();
    }}

    function renderActiveScene() {{
      const stage = document.getElementById("scene-stage");
      const title = document.getElementById("scene-shell-title");
      const kicker = document.getElementById("scene-shell-kicker");
      const summary = document.getElementById("scene-shell-summary");
      const body = document.getElementById("scene-shell-body");
      const sceneId = state.activeScene || "";
      const packetId = packetIdForScene(sceneId);
      if (!stage || !title || !kicker || !summary || !body) {{
        return;
      }}
      if (!sceneId || !packetId) {{
        closeScene();
        return;
      }}
      const meta = sceneMeta(sceneId);
      const data = state.dashboard || {{}};
      const needsDashboardHydration =
        !state.dashboard ||
        (packetId === "today" && !data.today_board);
      title.textContent = meta.title;
      kicker.textContent = meta.kicker;
      summary.textContent = meta.summary;
      stage.classList.remove("hidden");
      document.body.dataset.activeScene = "true";
      applyWindowFrame("scene");
      bringWindowToFront("scene");
      if (needsDashboardHydration) {{
        body.innerHTML = `<div class="packet-grid"><div class="metric">Loading ${{escapeHtml(meta.title)}}…</div></div>`;
        refreshDashboard({{ minIntervalMs: 10000 }})
          .then(() => {{
            if (state.activeScene === sceneId) {{
              renderActiveScene();
            }}
          }})
          .catch((error) => {{
            if (state.activeScene === sceneId) {{
              body.innerHTML = `<div class="packet-grid"><div class="metric">${{escapeHtml(error?.message || "Failed to load scene.")}}</div></div>`;
            }}
          }});
        return;
      }}
      body.innerHTML = renderSceneMarkup(sceneId, data);
      wireScenePacket(packetId);
    }}

    function openScene(sceneIdOrPacket = "") {{
      const sceneId = packetIdForScene(sceneIdOrPacket)
        ? String(sceneIdOrPacket || "").trim().toLowerCase()
        : sceneIdForPacket(sceneIdOrPacket);
      if (!sceneId) {{
        return;
      }}
      const packetId = packetIdForScene(sceneId);
      closeShellOverlays("scene");
      syncPacketTreeToTarget(packetId, {{ catalystPage: state.catalystPage, scene: sceneId }});
      state.activeScene = sceneId;
      state.windowStates.scene.minimized = false;
      setActiveOverlay("scene", {{ sceneId, packetId }});
      renderActiveScene();
      syncShellFocusMode();
      renderContextActionDock();
    }}

    function fillPacketStrip() {{
      const strip = document.getElementById("packet-strip");
      const toggle = document.getElementById("packet-strip-toggle");
      if (!strip || !toggle) {{
        state.packetStripExpanded = false;
        return;
      }}
      const allowed = packetStripAllowed();
      const packetButtons = [
        ["approvals", "Approvals"],
        ["tasks", "Tasks"],
        ["today", "Today"],
        ["review", "Review"],
        ["home", "House"],
        ["vision", "Vision"],
        ["finance", "Finance"],
        ["marketing", "Marketing"],
        ["pipeline", "Pipeline"],
        ["connected-devices", "Connected Devices"],
        ["catalyst", "Catalyst"],
        ["model-forge", "Model Forge"],
        ["settings", "Settings"],
      ];
      strip.innerHTML = packetButtons
        .map(([packet, label]) => `<button type="button" class="ghost-toggle" data-packet="${{packet}}">${{label}}</button>`)
        .join("");
      strip.classList.toggle("collapsed", !allowed || !state.packetStripExpanded);
      strip.setAttribute("aria-hidden", allowed && state.packetStripExpanded ? "false" : "true");
      toggle.classList.toggle("hidden", !allowed);
      toggle.textContent = state.packetStripExpanded ? "Hide Packets" : "Packets";
    }}

    function openPacketTarget(target) {{
      if (!target?.packet && !target?.scene) {{
        return;
      }}
      if (target.scene) {{
        openScene(target.scene);
        return;
      }}
      const sceneId = sceneIdForPacket(target.packet);
      if (sceneId) {{
        openScene(sceneId);
        return;
      }}
      if (target.packet === "catalyst" && target.catalystPage) {{
        state.catalystPage = target.catalystPage;
      }}
      syncPacketTreeToTarget(target.packet, {{ catalystPage: target.catalystPage || state.catalystPage }});
      openPacket(target.packet);
    }}

    function togglePacketStrip(forceExpanded = null) {{
      state.packetStripExpanded = forceExpanded === null ? !state.packetStripExpanded : !!forceExpanded;
      fillPacketStrip();
    }}

    function openModePanel() {{
      const panel = document.getElementById("mode-panel");
      const current = state.dashboard?.active_mode || null;
      if (!panel || !current) {{
        return;
      }}
      closeShellOverlays("mode");
      document.getElementById("mode-panel-current").textContent =
        `Current mode: ${{(current.mode || "ambient-associate").replaceAll("-", " ")}}`;
      document.getElementById("mode-select").value = current.mode || availableModes[0] || "ambient-associate";
      document.getElementById("mode-panel-status").textContent =
        current.reason ? `Current reason: ${{current.reason}}` : "Choose a new mode and apply it.";
      panel.classList.add("open");
      panel.setAttribute("aria-hidden", "false");
      setActiveOverlay("mode", {{ mode: current.mode || "" }});
      applyWindowFrame("mode");
      bringWindowToFront("mode");
    }}

    function closeModePanel() {{
      const panel = document.getElementById("mode-panel");
      if (!panel) {{
        return;
      }}
      panel.classList.remove("open");
      panel.setAttribute("aria-hidden", "true");
      if (state.activeOverlay?.type === "mode") {{
        setActiveOverlay("");
      }}
    }}

    function syncContextPanelCopy() {{
      const actor = document.getElementById("actor")?.value || "Chris";
      const room = (document.getElementById("room")?.value || "home").replaceAll("-", " ");
      const copy = document.getElementById("context-panel-copy");
      const launcher = document.getElementById("open-context-controls");
      if (copy) {{
        copy.textContent = `${{actor}} is active in the ${{room}}.`;
      }}
      if (launcher) {{
        launcher.title = `Actor: ${{actor}} | Room: ${{room}}`;
      }}
    }}

    function openContextPanel() {{
      const panel = document.getElementById("context-panel");
      if (!panel) {{
        return;
      }}
      closeShellOverlays("context");
      panel.classList.add("open");
      panel.setAttribute("aria-hidden", "false");
      syncContextPanelCopy();
      setActiveOverlay("context", {{
        actor: document.getElementById("actor")?.value || "Chris",
        room: document.getElementById("room")?.value || "home",
      }});
      applyWindowFrame("context");
      bringWindowToFront("context");
    }}

    function closeContextPanel() {{
      const panel = document.getElementById("context-panel");
      if (!panel) {{
        return;
      }}
      panel.classList.remove("open");
      panel.setAttribute("aria-hidden", "true");
      if (state.activeOverlay?.type === "context") {{
        setActiveOverlay("");
      }}
    }}

    function packetOverrideFromUrl() {{
      const params = new URLSearchParams(window.location.search || "");
      const packet = String(params.get("packet") || "").trim().toLowerCase();
      const allowed = new Set([
        "briefing",
        "today",
        "review",
        "tasks",
        "storm",
        "home",
        "family",
        "security",
        "vision",
        "chronicle",
        "workshop",
        "model-forge",
        "catalyst",
        "settings",
        "brains",
        "approvals",
        "agents",
      ]);
      return allowed.has(packet) ? packet : "";
    }}

    function applyPacketOverrideFromUrl() {{
      if (state.packetUrlOverrideConsumed) {{
        return false;
      }}
      const packet = packetOverrideFromUrl();
      if (!packet) {{
        return false;
      }}
      state.packetUrlOverrideConsumed = true;
      const url = new URL(window.location.href);
      url.searchParams.delete("packet");
      window.history.replaceState({{}}, "", url.toString());
      openPacket(packet);
      return true;
    }}

    function queueInitialPacketOpen() {{
      if (!state.initialPacketOverride || state.packetUrlOverrideConsumed) {{
        return;
      }}
      const packet = String(state.initialPacketOverride || "").trim().toLowerCase();
      if (!packet) {{
        return;
      }}
      const attemptOpen = (triesRemaining = 8) => {{
        const modalLayer = document.getElementById("modal-layer");
        if (!modalLayer) {{
          if (triesRemaining > 0) {{
            window.setTimeout(() => attemptOpen(triesRemaining - 1), 180);
          }}
          return;
        }}
        state.manualPacketIntentUntil = Date.now() + 30000;
        state.packetUrlOverrideConsumed = true;
        state.initialPacketOverride = "";
        const url = new URL(window.location.href);
        url.searchParams.delete("packet");
        window.history.replaceState({{}}, "", url.toString());
        openPacket(packet);
      }};
      window.setTimeout(() => attemptOpen(), 120);
    }}

    async function applyModeTransition() {{
      const actor = document.getElementById("mode-actor").value || "Chris";
      const mode = document.getElementById("mode-select").value || availableModes[0] || "ambient-associate";
      const reason = document.getElementById("mode-reason").value.trim() || "Manual mode update from JARVIS shell.";
      const result = await loadJSON("/api/mode-transition", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ actor, mode, reason }})
      }});
      document.getElementById("mode-panel-status").textContent =
        `Mode set to ${{result.mode.replaceAll("-", " ")}} by ${{result.actor}}.`;
      await refreshDashboard();
      closeModePanel();
    }}

    function fillBrainGraph(data) {{
      const graph = data.brain_graph || {{}};
      const activeNodes = new Set(graph.active_nodes || []);
      const signature = JSON.stringify({{
        provider: graph.active_provider || "",
        model: graph.active_model || "",
        secondary_provider: graph.secondary_brain?.provider || "",
        secondary_model: graph.secondary_brain?.model || "",
        secondary_ready: !!graph.secondary_brain?.model_available,
        active_nodes: graph.active_nodes || [],
      }});
      updateSourceIndicator(graph.active_provider || "standby", graph.active_model || "");
      document.getElementById("brain-graph-provider").textContent =
        graph.active_provider ? String(graph.active_provider).toUpperCase() : "STANDBY";
      document.getElementById("brain-mesh-caption-state").textContent =
        graph.active_provider ? `${{String(graph.active_provider).toUpperCase()}} ACTIVE` : "STANDBY";
      document.getElementById("brain-graph-meta").innerHTML = `
        <div><strong>Primary</strong> OpenAI</div>
        <div><strong>Second</strong> ${{escapeHtml(graph.secondary_brain?.provider || "ollama")}} · ${{graph.secondary_brain?.model_available ? "ready" : (graph.secondary_brain?.healthy ? "loading" : "standby")}}</div>
        <div><strong>Model</strong> ${{escapeHtml(graph.active_model || graph.secondary_brain?.model || "--")}}</div>
      `;
      if (state.brainGraphSignature === signature) {{
        return;
      }}
      state.brainGraphSignature = signature;
      renderBrainMesh("brain-mesh-panel", graph, activeNodes);
      const modalStage = document.getElementById("brain-mesh-modal");
      if (modalStage) {{
        renderBrainMesh("brain-mesh-modal", graph, activeNodes);
      }}
    }}

    function brainMeshBlueprint(graph) {{
      const statuses = Object.fromEntries((graph.nodes || []).map((item) => [item.id, item.status]));
      const primary = graph.active_provider === "ollama" ? "second-brain" : "primary-brain";
      const nodes = [
        {{ id: "router", label: "Router", cluster: "core", position: [0, 0.9, 0], size: 1.45 }},
        {{ id: "primary-brain", label: "Primary", cluster: "primary", position: [-1.9, 0.2, 1.05], size: 1.3 }},
        {{ id: "second-brain", label: "Second", cluster: "secondary", position: [1.95, 0.2, 1.0], size: 1.25 }},
        {{ id: "memory-core", label: "Memory", cluster: "memory", position: [0, -0.1, -0.4], size: 1.38 }},
        {{ id: "household-associate", label: "Ambient", cluster: "ambient", position: [-2.65, -1.18, -0.55], size: 1.08 }},
        {{ id: "family-logistics", label: "Family", cluster: "family", position: [-0.95, -1.55, 0.72], size: 1.05 }},
        {{ id: "faith-and-formation", label: "Chronicle", cluster: "chronicle", position: [0.92, -1.48, 0.86], size: 1.02 }},
        {{ id: "workshop-copilot", label: "Workshop", cluster: "workshop", position: [2.65, -1.12, -0.45], size: 1.08 }},
        {{ id: "executive-work", label: "Executive", cluster: "executive", position: [0, -2.08, -1.1], size: 1.08 }},
        {{ id: "permissions", label: "Permissions", cluster: "core", position: [-0.55, 0.35, -1.45], size: 0.68 }},
        {{ id: "wake-word", label: "Wake Word", cluster: "core", position: [0.58, 0.48, -1.4], size: 0.6 }},
        {{ id: "web-search", label: "Web", cluster: "primary", position: [-2.85, 0.8, 1.95], size: 0.55 }},
        {{ id: "realtime-voice", label: "Realtime", cluster: "primary", position: [-1.45, 1.05, 1.95], size: 0.58 }},
        {{ id: "local-routing", label: "Ambient", cluster: "secondary", position: [1.55, 1.0, 1.9], size: 0.56 }},
        {{ id: "local-speech", label: "Local Speech", cluster: "secondary", position: [2.95, 0.82, 1.85], size: 0.52 }},
        {{ id: "household-memory", label: "House", cluster: "memory", position: [-1.05, -0.72, -1.7], size: 0.58 }},
        {{ id: "project-memory", label: "Projects", cluster: "memory", position: [1.15, -0.68, -1.82], size: 0.58 }},
        {{ id: "safety-memory", label: "Safety", cluster: "memory", position: [0, -1.0, -2.08], size: 0.56 }},
        {{ id: "garage", label: "Garage", cluster: "ambient", position: [-3.35, -1.75, 0.6], size: 0.5 }},
        {{ id: "climate", label: "Climate", cluster: "ambient", position: [-3.32, -0.95, -1.4], size: 0.48 }},
        {{ id: "lights", label: "Lighting", cluster: "ambient", position: [-2.2, -0.62, -1.75], size: 0.5 }},
        {{ id: "school-rhythm", label: "School", cluster: "family", position: [-1.75, -2.05, 1.48], size: 0.48 }},
        {{ id: "meals", label: "Meals", cluster: "family", position: [-0.32, -1.92, 1.8], size: 0.48 }},
        {{ id: "troop", label: "Troop", cluster: "family", position: [-0.98, -2.38, 0.2], size: 0.46 }},
        {{ id: "devotionals", label: "Devotionals", cluster: "chronicle", position: [0.18, -2.18, 1.72], size: 0.46 }},
        {{ id: "timeline", label: "Timeline", cluster: "chronicle", position: [1.76, -2.08, 1.28], size: 0.48 }},
        {{ id: "prayers", label: "Prayers", cluster: "chronicle", position: [1.18, -2.42, 0.18], size: 0.46 }},
        {{ id: "printer", label: "Printer", cluster: "workshop", position: [3.28, -1.82, 0.42], size: 0.5 }},
        {{ id: "materials", label: "Materials", cluster: "workshop", position: [2.22, -0.56, -1.75], size: 0.48 }},
        {{ id: "safety", label: "Safety", cluster: "workshop", position: [3.18, -0.94, -1.28], size: 0.48 }},
        {{ id: "meetings", label: "Meetings", cluster: "executive", position: [-0.82, -2.95, -0.76], size: 0.48 }},
        {{ id: "writing", label: "Writing", cluster: "executive", position: [0.76, -2.95, -0.7], size: 0.48 }},
        {{ id: "research", label: "Research", cluster: "executive", position: [0, -3.18, -1.86], size: 0.5 }},
      ].map((node) => ({{
        ...node,
        status: statuses[node.id] || "ready",
        active: (graph.active_nodes || []).includes(node.id) || (node.id === primary && (graph.active_nodes || []).includes(primary)),
      }}));

      const edges = [
        ["router", "primary-brain"], ["router", "second-brain"], ["router", "memory-core"], ["router", "permissions"], ["router", "wake-word"],
        ["primary-brain", "web-search"], ["primary-brain", "realtime-voice"], ["second-brain", "local-routing"], ["second-brain", "local-speech"],
        ["memory-core", "household-memory"], ["memory-core", "project-memory"], ["memory-core", "safety-memory"],
        ["memory-core", "household-associate"], ["memory-core", "family-logistics"], ["memory-core", "faith-and-formation"], ["memory-core", "workshop-copilot"], ["memory-core", "executive-work"],
        ["household-associate", "garage"], ["household-associate", "climate"], ["household-associate", "lights"],
        ["family-logistics", "school-rhythm"], ["family-logistics", "meals"], ["family-logistics", "troop"],
        ["faith-and-formation", "devotionals"], ["faith-and-formation", "timeline"], ["faith-and-formation", "prayers"],
        ["workshop-copilot", "printer"], ["workshop-copilot", "materials"], ["workshop-copilot", "safety"],
        ["executive-work", "meetings"], ["executive-work", "writing"], ["executive-work", "research"],
        ["household-associate", "family-logistics"], ["executive-work", "faith-and-formation"], ["workshop-copilot", "executive-work"], ["family-logistics", "household-associate"],
      ];
      return {{ nodes, edges }};
    }}

    function brainClusterColor(cluster) {{
      return {{
        core: 0x9cf1ff,
        primary: 0x56b6ff,
        secondary: 0x74ffbb,
        memory: 0xc19cff,
        ambient: 0x5be2ff,
        family: 0xffc96a,
        chronicle: 0xe6a5ff,
        workshop: 0xff8c47,
        executive: 0x8aa7ff,
      }}[cluster] || 0xa7dbff;
    }}

    function ensureBrainMesh(mountId, view = "panel") {{
      const mount = document.getElementById(mountId);
      if (!mount) {{
        return null;
      }}
      const existing = state.brainMeshScenes.get(mountId);
      if (existing && existing.mount === mount) {{
        return existing;
      }}
      if (existing && existing.mount !== mount) {{
        disposeBrainMesh(mountId);
      }}

      const canvas = mount.querySelector("canvas");
      const renderer = new THREE.WebGLRenderer({{
        canvas,
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
      }});
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.outputColorSpace = THREE.SRGBColorSpace;

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(view === "modal" ? 42 : 48, 1, 0.1, 100);
      camera.position.set(0, 0.4, view === "modal" ? 10.2 : 8.4);

      const root = new THREE.Group();
      scene.add(root);

      const glowLight = new THREE.PointLight(0x69dcff, 6.5, 30, 2);
      glowLight.position.set(0, 1.2, 5.6);
      scene.add(glowLight);
      scene.add(new THREE.AmbientLight(0x6ea8ff, 0.72));

      const starGeometry = new THREE.BufferGeometry();
      const starCount = view === "modal" ? 180 : 90;
      const starPositions = new Float32Array(starCount * 3);
      for (let i = 0; i < starCount; i += 1) {{
        starPositions[i * 3 + 0] = (Math.random() - 0.5) * 13;
        starPositions[i * 3 + 1] = (Math.random() - 0.5) * 9;
        starPositions[i * 3 + 2] = (Math.random() - 0.5) * 8 - 2;
      }}
      starGeometry.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
      const stars = new THREE.Points(
        starGeometry,
        new THREE.PointsMaterial({{
          color: 0x75dfff,
          size: view === "modal" ? 0.06 : 0.05,
          transparent: true,
          opacity: 0.28,
        }})
      );
      scene.add(stars);

      const mesh = {{
        mount,
        renderer,
        scene,
        camera,
        root,
        lines: null,
        haloLines: null,
        nodes: new Map(),
        labels: new Map(),
        starField: stars,
        view,
        frame: null,
        resizeObserver: null,
      }};

      const resize = () => {{
        const width = Math.max(mount.clientWidth, 10);
        const height = Math.max(mount.clientHeight, 10);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height, false);
      }};
      resize();
      const observer = new ResizeObserver(resize);
      observer.observe(mount);
      mesh.resizeObserver = observer;

      const animate = (time) => {{
        const seconds = time * 0.001;
        root.rotation.y = seconds * 0.08;
        root.rotation.x = Math.sin(seconds * 0.33) * 0.08;
        stars.rotation.y = -seconds * 0.02;
        for (const entry of mesh.nodes.values()) {{
          const pulse = 0.88 + Math.sin(seconds * entry.speed + entry.phase) * 0.08;
          entry.core.scale.setScalar(entry.baseScale * (entry.active ? 1.08 + (pulse - 0.88) * 0.9 : pulse));
          entry.glow.material.opacity = entry.active ? 0.36 + Math.sin(seconds * entry.speed * 1.2 + entry.phase) * 0.12 : 0.09;
        }}
        renderer.render(scene, camera);
        mesh.frame = requestAnimationFrame(animate);
      }};
      mesh.frame = requestAnimationFrame(animate);

      state.brainMeshScenes.set(mountId, mesh);
      return mesh;
    }}

    function disposeBrainMesh(mountId) {{
      const mesh = state.brainMeshScenes.get(mountId);
      if (!mesh) return;
      if (mesh.frame) cancelAnimationFrame(mesh.frame);
      if (mesh.resizeObserver) mesh.resizeObserver.disconnect();
      if (mesh.lines) {{
        mesh.lines.geometry.dispose();
        mesh.lines.material.dispose();
      }}
      if (mesh.haloLines) {{
        mesh.haloLines.geometry.dispose();
        mesh.haloLines.material.dispose();
      }}
      for (const entry of mesh.nodes.values()) {{
        entry.core.geometry.dispose();
        entry.core.material.dispose();
        entry.glow.geometry.dispose();
        entry.glow.material.dispose();
        entry.group.traverse((child) => {{
          if (child.isSprite && child.material) {{
            child.material.map?.dispose?.();
            child.material.dispose?.();
          }}
        }});
      }}
      mesh.starField.geometry.dispose();
      mesh.starField.material.dispose();
      mesh.renderer.dispose();
      state.brainMeshScenes.delete(mountId);
    }}

    function renderBrainMesh(mountId, graph, activeNodes) {{
      const view = mountId === "brain-mesh-modal" ? "modal" : "panel";
      const mesh = ensureBrainMesh(mountId, view);
      if (!mesh) {{
        return;
      }}
      const blueprint = brainMeshBlueprint(graph);
      const byId = Object.fromEntries(blueprint.nodes.map((node) => [node.id, node]));

      if (mesh.lines) {{
        mesh.root.remove(mesh.lines);
        mesh.lines.geometry.dispose();
        mesh.lines.material.dispose();
      }}
      if (mesh.haloLines) {{
        mesh.root.remove(mesh.haloLines);
        mesh.haloLines.geometry.dispose();
        mesh.haloLines.material.dispose();
      }}
      for (const entry of mesh.nodes.values()) {{
        mesh.root.remove(entry.group);
        entry.core.geometry.dispose();
        entry.core.material.dispose();
        entry.glow.geometry.dispose();
        entry.glow.material.dispose();
      }}
      mesh.nodes.clear();

      const linePositions = [];
      const lineColors = [];
      const haloPositions = [];
      const haloColors = [];

      for (const [fromId, toId] of blueprint.edges) {{
        const from = byId[fromId];
        const to = byId[toId];
        if (!from || !to) continue;
        linePositions.push(...from.position, ...to.position);
        const hot = activeNodes.has(fromId) && activeNodes.has(toId);
        const base = hot ? new THREE.Color(0x84efff) : new THREE.Color(0x25445e);
        lineColors.push(base.r, base.g, base.b, base.r, base.g, base.b);
        if (hot) {{
          haloPositions.push(...from.position, ...to.position);
          const glow = new THREE.Color(from.cluster === "secondary" || to.cluster === "secondary" ? 0x7fffc1 : 0x8ff2ff);
          haloColors.push(glow.r, glow.g, glow.b, glow.r, glow.g, glow.b);
        }}
      }}

      const lineGeometry = new THREE.BufferGeometry();
      lineGeometry.setAttribute("position", new THREE.Float32BufferAttribute(linePositions, 3));
      lineGeometry.setAttribute("color", new THREE.Float32BufferAttribute(lineColors, 3));
      mesh.lines = new THREE.LineSegments(
        lineGeometry,
        new THREE.LineBasicMaterial({{
          vertexColors: true,
          transparent: true,
          opacity: view === "modal" ? 0.34 : 0.26,
        }})
      );
      mesh.root.add(mesh.lines);

      if (haloPositions.length) {{
        const haloGeometry = new THREE.BufferGeometry();
        haloGeometry.setAttribute("position", new THREE.Float32BufferAttribute(haloPositions, 3));
        haloGeometry.setAttribute("color", new THREE.Float32BufferAttribute(haloColors, 3));
        mesh.haloLines = new THREE.LineSegments(
          haloGeometry,
          new THREE.LineBasicMaterial({{
            vertexColors: true,
            transparent: true,
            opacity: 0.82,
            blending: THREE.AdditiveBlending,
          }})
        );
        mesh.root.add(mesh.haloLines);
      }}

      for (const node of blueprint.nodes) {{
        const color = brainClusterColor(node.cluster);
        const active = activeNodes.has(node.id) || node.active;
        const group = new THREE.Group();
        group.position.set(...node.position);

        const glow = new THREE.Mesh(
          new THREE.SphereGeometry(node.size * (view === "modal" ? 0.48 : 0.42), 16, 16),
          new THREE.MeshBasicMaterial({{
            color,
            transparent: true,
            opacity: active ? 0.32 : 0.08,
            blending: THREE.AdditiveBlending,
          }})
        );
        group.add(glow);

        const core = new THREE.Mesh(
          new THREE.SphereGeometry(node.size * (view === "modal" ? 0.18 : 0.16), 24, 24),
          new THREE.MeshStandardMaterial({{
            color,
            emissive: active ? color : 0x0a1b2a,
            emissiveIntensity: active ? 1.15 : 0.18,
            metalness: 0.1,
            roughness: 0.24,
            transparent: true,
            opacity: node.status === "offline" ? 0.34 : 0.95,
          }})
        );
        group.add(core);

        if (node.size >= 1 || active || view === "modal") {{
          const sprite = buildBrainLabel(node.label, active, color);
          sprite.position.set(0, node.size * 0.22 + 0.12, 0);
          sprite.scale.set(view === "modal" ? 1.15 : 0.95, view === "modal" ? 0.34 : 0.3, 1);
          group.add(sprite);
        }}

        mesh.root.add(group);
        mesh.nodes.set(node.id, {{
          group,
          glow,
          core,
          active,
          baseScale: 1,
          speed: 0.8 + Math.random() * 1.2,
          phase: Math.random() * Math.PI * 2,
        }});
      }}
    }}

    function makeDomReviewTarget(id, label, selector, describe) {{
      return {{
        id,
        label,
        describe: () => describe,
        apply(active, removed, override = null) {{
          const nodes = Array.from(document.querySelectorAll(selector));
          const opacityScale = override?.opacityScale ?? 1;
          const scaleBoost = override?.scale ?? 1;
          nodes.forEach((node) => {{
            node.dataset.reviewTargetId = id;
            node.style.transition = "opacity 180ms ease, transform 180ms ease, filter 180ms ease, outline-color 180ms ease, box-shadow 180ms ease";
            node.style.opacity = removed ? "0.08" : String(Math.max(0.16, Math.min(1, opacityScale)));
            node.style.transform = scaleBoost !== 1 ? `scale(${{scaleBoost}})` : "";
            node.style.filter = active
              ? "drop-shadow(0 0 14px rgba(255, 88, 88, 0.44))"
              : removed
                ? "saturate(0.55)"
                : "";
            node.style.outline = active ? "1px solid rgba(255, 88, 88, 0.86)" : "";
            node.style.outlineOffset = active ? "6px" : "";
            node.style.boxShadow = active ? "0 0 0 1px rgba(255, 88, 88, 0.24), 0 0 24px rgba(255, 88, 88, 0.18)" : "";
            if (removed) {{
              node.style.outline = "";
              node.style.outlineOffset = "";
              node.style.boxShadow = "";
            }}
            if (!active) {{
              node.style.outline = "";
              node.style.outlineOffset = "";
              node.style.boxShadow = "";
            }}
          }});
        }},
      }};
    }}

    function getReviewTargetsForPage(pageId = currentReviewPageId()) {{
      if (pageId === "shell") {{
        const sceneTargets = state.holoCoreScene?.reviewTargets || [];
        return [
          ...sceneTargets,
          makeDomReviewTarget("shell-wordmark", "Wordmark rail", ".wordmark", "The JARVIS wordmark in the upper-left corner."),
          makeDomReviewTarget("shell-topbar", "Top status bar", ".topbar", "The top status rail with clock, mode, weather, and settings."),
          makeDomReviewTarget("shell-brain-mesh", "Brain Mesh panel", ".brain-graph, #brain-mesh, .brain-mesh-panel", "The Brain Mesh panel on the left side of the shell."),
          makeDomReviewTarget("shell-transcript", "Transcript rail", ".transcript-rail", "The conversation rail showing You and JARVIS."),
          makeDomReviewTarget("shell-review-panel", "Review panel", ".design-review-panel", "The review panel beneath the core."),
          makeDomReviewTarget("shell-packet-strip", "Packet strip", ".packet-strip", "The dock of packet buttons beneath the chamber."),
        ];
      }}

      const pageMap = {{
        briefing: [
          makeDomReviewTarget("briefing-header", "Modal header", "#modal-title", "The title and top edge of the Morning Brief modal."),
          makeDomReviewTarget("briefing-grid", "Packet grid", ".packet-grid", "The overall Morning Brief packet grid."),
          makeDomReviewTarget("briefing-blocks", "Briefing blocks", ".packet-block", "The Morning Brief content blocks."),
        ],
        brains: [
          makeDomReviewTarget("brains-header", "Modal header", "#modal-title", "The title and top edge of the Brains modal."),
          makeDomReviewTarget("brains-grid", "Packet grid", ".packet-grid", "The overall Brains packet grid."),
          makeDomReviewTarget("brains-blocks", "Brain blocks", ".packet-block", "The Brain packet content blocks."),
          makeDomReviewTarget("brains-mesh", "Modal brain mesh", ".brain-mesh-modal-stage", "The large 3D brain mesh stage in the modal."),
        ],
        agents: [
          makeDomReviewTarget("agents-header", "Modal header", "#modal-title", "The title and top edge of the Agents modal."),
          makeDomReviewTarget("agents-grid", "Packet grid", ".packet-grid", "The overall Agents packet grid."),
          makeDomReviewTarget("agents-blocks", "Agent blocks", ".packet-block", "The agent and curation content blocks."),
        ],
        home: [
          makeDomReviewTarget("house-header", "Modal header", "#modal-title", "The title and top edge of the House packet."),
          makeDomReviewTarget("house-grid", "Packet grid", ".packet-grid", "The overall House packet grid."),
          makeDomReviewTarget("house-blocks", "House blocks", ".packet-block", "The House packet content blocks."),
        ],
        family: [
          makeDomReviewTarget("family-header", "Modal header", "#modal-title", "The title and top edge of the Family packet."),
          makeDomReviewTarget("family-grid", "Packet grid", ".packet-grid", "The overall Family packet grid."),
          makeDomReviewTarget("family-blocks", "Family blocks", ".packet-block", "The Family packet content blocks."),
        ],
        security: [
          makeDomReviewTarget("security-header", "Modal header", "#modal-title", "The title and top edge of the Security packet."),
          makeDomReviewTarget("security-grid", "Packet grid", ".packet-grid", "The overall Security packet grid."),
          makeDomReviewTarget("security-blocks", "Security blocks", ".packet-block", "The Security packet content blocks."),
        ],
        chronicle: [
          makeDomReviewTarget("chronicle-header", "Modal header", "#modal-title", "The title and top edge of the Chronicle packet."),
          makeDomReviewTarget("chronicle-grid", "Packet grid", ".packet-grid", "The overall Chronicle packet grid."),
          makeDomReviewTarget("chronicle-blocks", "Chronicle blocks", ".packet-block", "The Chronicle content blocks."),
        ],
        workshop: [
          makeDomReviewTarget("workshop-header", "Modal header", "#modal-title", "The title and top edge of the Workshop packet."),
          makeDomReviewTarget("workshop-grid", "Packet grid", ".packet-grid", "The overall Workshop packet grid."),
          makeDomReviewTarget("workshop-blocks", "Workshop blocks", ".packet-block", "The Workshop content blocks."),
        ],
        catalyst: [
          makeDomReviewTarget("catalyst-header", "Modal header", "#modal-title", "The title and top edge of the Catalyst workspace."),
          makeDomReviewTarget("catalyst-summary", "Workspace summary", ".workspace-summary", "The Catalyst workspace summary tags."),
          makeDomReviewTarget("catalyst-tabs", "Workspace tabs", ".workspace-tabs", "The Catalyst workspace tab rail."),
          makeDomReviewTarget("catalyst-frame", "Workspace frame", ".workspace-frame", "The embedded Catalyst workspace frame."),
        ],
        approvals: [
          makeDomReviewTarget("approvals-header", "Modal header", "#modal-title", "The title and top edge of the Approvals packet."),
          makeDomReviewTarget("approvals-grid", "Packet grid", ".packet-grid", "The overall Approvals packet grid."),
          makeDomReviewTarget("approvals-blocks", "Approval blocks", ".packet-block", "The Approvals content blocks."),
        ],
        settings: [
          makeDomReviewTarget("settings-header", "Modal header", "#modal-title", "The title and top edge of the Settings modal."),
          makeDomReviewTarget("settings-grid", "Packet grid", ".packet-grid", "The overall Settings packet grid."),
          makeDomReviewTarget("settings-blocks", "Settings blocks", ".packet-block", "The Settings content blocks."),
          makeDomReviewTarget("settings-voice", "Voice controls", "#save-voice-settings, #preview-voice-settings, #settings-tts-provider", "The voice settings controls."),
          makeDomReviewTarget("settings-page-review", "Page review controls", "#page-review-status, .page-review-toggle-row", "The page-review controls inside Settings."),
        ],
      }};
      return pageMap[pageId] || [];
    }}

    function buildBrainLabel(text, active, colorHex) {{
      const canvas = document.createElement("canvas");
      canvas.width = 256;
      canvas.height = 72;
      const ctx = canvas.getContext("2d");
      const color = `#${{new THREE.Color(colorHex).getHexString()}}`;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "rgba(6, 16, 28, 0.78)";
      ctx.strokeStyle = active ? color : "rgba(111, 229, 255, 0.18)";
      ctx.lineWidth = 2;
      roundRect(ctx, 8, 12, 240, 48, 14);
      ctx.fill();
      ctx.stroke();
      ctx.font = "600 21px Inter, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = active ? "#f3fbff" : "rgba(213, 233, 255, 0.78)";
      ctx.fillText(text.toUpperCase(), canvas.width / 2, canvas.height / 2 + 1);
      const texture = new THREE.CanvasTexture(canvas);
      texture.needsUpdate = true;
      const material = new THREE.SpriteMaterial({{
        map: texture,
        transparent: true,
        depthWrite: false,
      }});
      return new THREE.Sprite(material);
    }}

    function roundRect(ctx, x, y, width, height, radius) {{
      ctx.beginPath();
      ctx.moveTo(x + radius, y);
      ctx.lineTo(x + width - radius, y);
      ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
      ctx.lineTo(x + width, y + height - radius);
      ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
      ctx.lineTo(x + radius, y + height);
      ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
      ctx.lineTo(x, y + radius);
      ctx.quadraticCurveTo(x, y, x + radius, y);
      ctx.closePath();
    }}

    function ensureHoloCore() {{
      const mount = document.getElementById("holo-core-shell");
      const canvas = document.getElementById("holo-core-canvas");
      if (!mount || !canvas) {{
        return null;
      }}
      if (state.holoCoreScene && state.holoCoreScene.mount === mount) {{
        return state.holoCoreScene;
      }}

      let renderer = null;
      try {{
        renderer = new THREE.WebGLRenderer({{
          canvas,
          antialias: true,
          alpha: true,
          powerPreference: "high-performance",
        }});
      }} catch (error) {{
        console.warn("JARVIS hologram renderer unavailable; using fallback core.", error);
        return null;
      }}
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.outputColorSpace = THREE.SRGBColorSpace;

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
      camera.position.set(0, 0.1, 9.8);

      const root = new THREE.Group();
      root.rotation.x = -0.08;
      scene.add(root);

      scene.add(new THREE.AmbientLight(0x58cfff, 0.78));
      const key = new THREE.PointLight(0x85f3ff, 5.2, 30, 2);
      key.position.set(0, 0, 7);
      scene.add(key);
      const rim = new THREE.PointLight(0x2f76ff, 2.4, 28, 2);
      rim.position.set(-3, 1.2, -2);
      scene.add(rim);

      const core = new THREE.Mesh(
        new THREE.IcosahedronGeometry(0.78, 6),
        new THREE.MeshBasicMaterial({{
          color: 0x7cedff,
          transparent: true,
          opacity: 0.16,
          wireframe: true,
          blending: THREE.AdditiveBlending,
        }})
      );
      if (hardCenterDesign.wireframe_core) {{
        root.add(core);
      }}

      const pulseCore = new THREE.Mesh(
        new THREE.SphereGeometry(0.28, 28, 28),
        new THREE.MeshBasicMaterial({{
          color: 0x94f6ff,
          transparent: true,
          opacity: 0.28,
          blending: THREE.AdditiveBlending,
        }})
      );
      root.add(pulseCore);

      const coreParticleCount = 10000;
      const coreParticlePositions = new Float32Array(coreParticleCount * 3);
      const coreParticleColors = new Float32Array(coreParticleCount * 3);
      const coreParticleSizes = new Float32Array(coreParticleCount);
      const coreParticleSeeds = [];
      for (let i = 0; i < coreParticleCount; i += 1) {{
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos((Math.random() * 2) - 1);
        const radius = 0.14 + Math.random() * 0.34;
        const x = radius * Math.sin(phi) * Math.cos(theta);
        const y = radius * Math.cos(phi);
        const z = radius * Math.sin(phi) * Math.sin(theta);
        coreParticlePositions[i * 3] = x;
        coreParticlePositions[i * 3 + 1] = y;
        coreParticlePositions[i * 3 + 2] = z;
        const color = new THREE.Color(i % 3 === 0 ? 0xc3fbff : i % 2 === 0 ? 0x87deff : 0x5ce7ff);
        coreParticleColors[i * 3] = color.r;
        coreParticleColors[i * 3 + 1] = color.g;
        coreParticleColors[i * 3 + 2] = color.b;
        coreParticleSizes[i] = 0.7 + Math.random() * 1.7;
        coreParticleSeeds.push({{
          theta,
          phi,
          radius,
          speed: 0.18 + Math.random() * 0.22,
          phase: Math.random() * Math.PI * 2,
        }});
      }}

      const coreParticleGeometry = new THREE.BufferGeometry();
      coreParticleGeometry.setAttribute("position", new THREE.BufferAttribute(coreParticlePositions, 3));
      coreParticleGeometry.setAttribute("color", new THREE.BufferAttribute(coreParticleColors, 3));
      coreParticleGeometry.setAttribute("size", new THREE.BufferAttribute(coreParticleSizes, 1));
      const coreParticleMaterial = new THREE.ShaderMaterial({{
        uniforms: {{
          uPixelRatio: {{ value: Math.min(window.devicePixelRatio || 1, 2) }},
          uEnergy: {{ value: 0.35 }},
        }},
        vertexShader: `
          attribute float size;
          varying vec3 vColor;
          uniform float uPixelRatio;
          uniform float uEnergy;
          void main() {{
            vColor = color;
            vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
            gl_Position = projectionMatrix * mvPosition;
            gl_PointSize = size * uPixelRatio * (5.2 + (uEnergy * 5.0)) / max(1.0, -mvPosition.z * 0.4);
          }}
        `,
        fragmentShader: `
          varying vec3 vColor;
          void main() {{
            vec2 uv = gl_PointCoord - vec2(0.5);
            float dist = length(uv);
            float alpha = smoothstep(0.54, 0.0, dist);
            gl_FragColor = vec4(vColor, alpha);
          }}
        `,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        vertexColors: true,
      }});
      const coreParticles = new THREE.Points(coreParticleGeometry, coreParticleMaterial);
      root.add(coreParticles);

      const pulseGlow = new THREE.Mesh(
        new THREE.SphereGeometry(0.42, 28, 28),
        new THREE.MeshBasicMaterial({{
          color: 0x69dcff,
          transparent: true,
          opacity: 0.2,
          blending: THREE.AdditiveBlending,
        }})
      );
      root.add(pulseGlow);

      const orbits = [];
      hardCenterDesign.orbits.forEach(([radius, color, tilt, speed, rx, rz]) => {{
        const count = 12000;
        const orbitPositions = new Float32Array(count * 3);
        const orbitColors = new Float32Array(count * 3);
        const orbitSizes = new Float32Array(count);
        const orbitSeeds = [];
        const orbitColor = new THREE.Color(color);
        for (let i = 0; i < count; i += 1) {{
          const angle = (i / count) * Math.PI * 2;
          const jitter = (Math.random() - 0.5) * 0.024;
          orbitPositions[i * 3] = Math.cos(angle) * (radius + jitter);
          orbitPositions[i * 3 + 1] = Math.sin(angle) * (radius + jitter);
          orbitPositions[i * 3 + 2] = (Math.random() - 0.5) * 0.036;
          const bandColor = orbitColor.clone().offsetHSL(0, 0, (Math.random() - 0.5) * 0.045);
          orbitColors[i * 3] = bandColor.r;
          orbitColors[i * 3 + 1] = bandColor.g;
          orbitColors[i * 3 + 2] = bandColor.b;
          orbitSizes[i] = 0.48 + Math.random() * 0.92;
          orbitSeeds.push({{
            angle,
            jitter,
            z: orbitPositions[i * 3 + 2],
            wobble: 0.003 + Math.random() * 0.007,
            phase: Math.random() * Math.PI * 2,
          }});
        }}
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute("position", new THREE.BufferAttribute(orbitPositions, 3));
        geometry.setAttribute("color", new THREE.BufferAttribute(orbitColors, 3));
        geometry.setAttribute("size", new THREE.BufferAttribute(orbitSizes, 1));
        const material = new THREE.ShaderMaterial({{
          uniforms: {{
            uPixelRatio: {{ value: Math.min(window.devicePixelRatio || 1, 2) }},
            uEnergy: {{ value: 0.35 }},
            uReviewMix: {{ value: 0.0 }},
            uReviewColor: {{ value: new THREE.Color(0xff5757) }},
            uOpacity: {{ value: 0.62 }},
          }},
          vertexShader: `
            attribute float size;
            varying vec3 vColor;
            uniform float uPixelRatio;
            uniform float uEnergy;
            void main() {{
              vColor = color;
              vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
              gl_Position = projectionMatrix * mvPosition;
              gl_PointSize = size * uPixelRatio * (4.2 + (uEnergy * 2.4)) / max(1.0, -mvPosition.z * 0.34);
            }}
          `,
          fragmentShader: `
            varying vec3 vColor;
            uniform float uReviewMix;
            uniform vec3 uReviewColor;
            uniform float uOpacity;
            void main() {{
              vec2 uv = gl_PointCoord - vec2(0.5);
              float dist = length(uv);
              float alpha = smoothstep(0.52, 0.0, dist);
              vec3 mixedColor = mix(vColor, uReviewColor, uReviewMix);
              gl_FragColor = vec4(mixedColor, alpha * uOpacity);
            }}
          `,
          transparent: true,
          depthWrite: false,
          blending: THREE.AdditiveBlending,
          vertexColors: true,
        }});
        const ring = new THREE.Points(geometry, material);
        ring.rotation.x = rx;
        ring.rotation.z = rz;
        root.add(ring);
        orbits.push({{ mesh: ring, geometry, seeds: orbitSeeds, radius, baseTilt: tilt, speed, rx, rz }});
      }});

      const shellArcs = [];
      hardCenterDesign.shell_arcs.forEach(([radius, startDeg, spanDeg, color]) => {{
        const curve = new THREE.EllipseCurve(0, 0, radius, radius, (startDeg * Math.PI) / 180, ((startDeg + spanDeg) * Math.PI) / 180, false, 0);
        const points = curve.getPoints(140).map((point) => new THREE.Vector3(point.x, point.y, 0));
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const line = new THREE.Line(
          geometry,
          new THREE.LineBasicMaterial({{
            color,
            transparent: true,
            opacity: 0.9,
            blending: THREE.AdditiveBlending,
          }})
        );
        line.rotation.x = Math.PI / 2.8;
        line.rotation.y = Math.random() * Math.PI;
        root.add(line);
        shellArcs.push(line);
      }});

      const particleCount = 980;
      const positions = new Float32Array(particleCount * 3);
      const colors = new Float32Array(particleCount * 3);
      const sizes = new Float32Array(particleCount);
      const seeds = [];
      const sphereRadius = 2.15;
      for (let i = 0; i < particleCount; i += 1) {{
        const u = Math.random();
        const v = Math.random();
        const theta = 2 * Math.PI * u;
        const phi = Math.acos(2 * v - 1);
        const radius = sphereRadius * (0.72 + Math.random() * 0.35);
        const jitter = (Math.random() - 0.5) * 0.16;
        const x = (radius + jitter) * Math.sin(phi) * Math.cos(theta);
        const y = (radius + jitter) * Math.cos(phi) * 0.88;
        const z = (radius + jitter) * Math.sin(phi) * Math.sin(theta);
        positions[i * 3] = x;
        positions[i * 3 + 1] = y;
        positions[i * 3 + 2] = z;
        const color = new THREE.Color(i % 4 === 0 ? 0x9cf1ff : i % 3 === 0 ? 0x66cfff : 0x5ce7ff);
        colors[i * 3] = color.r;
        colors[i * 3 + 1] = color.g;
        colors[i * 3 + 2] = color.b;
        sizes[i] = 0.9 + Math.random() * 1.8;
        seeds.push({{
          theta,
          phi,
          radius,
          speed: 0.12 + Math.random() * 0.22,
          wobble: 0.02 + Math.random() * 0.05,
          phase: Math.random() * Math.PI * 2,
        }});
      }}

      const particleGeometry = new THREE.BufferGeometry();
      particleGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
      particleGeometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
      particleGeometry.setAttribute("size", new THREE.BufferAttribute(sizes, 1));

      const particleMaterial = new THREE.ShaderMaterial({{
        uniforms: {{
          uPixelRatio: {{ value: Math.min(window.devicePixelRatio || 1, 2) }},
          uEnergy: {{ value: 0.35 }},
          uReviewMix: {{ value: 0.0 }},
          uReviewColor: {{ value: new THREE.Color(0xff5757) }},
        }},
        vertexShader: `
          attribute float size;
          varying vec3 vColor;
          uniform float uPixelRatio;
          uniform float uEnergy;
          void main() {{
            vColor = color;
            vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
            gl_Position = projectionMatrix * mvPosition;
            gl_PointSize = size * uPixelRatio * (4.8 + (uEnergy * 4.0)) / max(1.0, -mvPosition.z * 0.32);
          }}
        `,
        fragmentShader: `
          varying vec3 vColor;
          uniform float uReviewMix;
          uniform vec3 uReviewColor;
          void main() {{
            vec2 uv = gl_PointCoord - vec2(0.5);
            float dist = length(uv);
            float alpha = smoothstep(0.52, 0.0, dist);
            vec3 mixedColor = mix(vColor, uReviewColor, uReviewMix);
            gl_FragColor = vec4(mixedColor, alpha * 0.9);
          }}
        `,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        vertexColors: true,
      }});
      const particles = new THREE.Points(particleGeometry, particleMaterial);
      if (hardCenterDesign.outer_particle_shell) {{
        root.add(particles);
      }}

      const lineCount = 180;
      const linePositions = new Float32Array(lineCount * 6);
      const lineGeometry = new THREE.BufferGeometry();
      lineGeometry.setAttribute("position", new THREE.BufferAttribute(linePositions, 3));
      const lineField = new THREE.LineSegments(
        lineGeometry,
        new THREE.LineBasicMaterial({{
          color: 0x6ee3ff,
          transparent: true,
          opacity: 0.18,
          blending: THREE.AdditiveBlending,
        }})
      );
      root.add(lineField);
      lineField.visible = false;

      function resize() {{
        const width = Math.max(mount.clientWidth, 10);
        const height = Math.max(mount.clientHeight, 10);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height, false);
      }}
      resize();
      const observer = new ResizeObserver(resize);
      observer.observe(mount);

      const sceneState = {{
        mount,
        renderer,
        scene,
        camera,
        root,
        core,
        pulseCore,
        coreParticles,
        coreParticleGeometry,
        coreParticleMaterial,
        coreParticleSeeds,
        pulseGlow,
        particles,
        particleGeometry,
        particleMaterial,
        lineField,
        lineGeometry,
        linePositions,
        particleSeeds: seeds,
        basePositions: positions.slice(),
        orbits,
        shellArcs,
        observer,
        frame: null,
        ready: false,
      }};

      const reviewRed = 0xff5757;
      sceneState.reviewTargets = [
        {{
          id: "core-wireframe",
          label: "Core wireframe shell",
          describe: () => "Keep or remove the geometric wireframe sphere around the center core.",
          apply(active, removed, override = null) {{
            const opacityScale = override?.opacityScale ?? 1;
            core.visible = !removed;
            core.material.color.setHex(active ? reviewRed : 0x7cedff);
            core.material.opacity = removed ? 0 : (active ? 0.42 : 0.16) * opacityScale;
            const scaleBoost = override?.scale ?? 1;
            core.scale.setScalar((1 + state.energyCurrent * 0.08) * scaleBoost);
          }},
        }},
        {{
          id: "pulse-core",
          label: "Pulse core",
          describe: () => "Keep or remove the bright inner nucleus that swells with speech energy.",
          apply(active, removed, override = null) {{
            const opacityScale = override?.opacityScale ?? 1;
            pulseCore.visible = !removed;
            pulseCore.material.color.setHex(active ? reviewRed : 0x94f6ff);
            pulseCore.material.opacity = removed ? 0 : (active ? 1 : 0.95) * opacityScale;
          }},
        }},
        {{
          id: "pulse-glow",
          label: "Pulse glow halo",
          describe: () => "Keep or remove the soft glow around the center pulse core.",
          apply(active, removed, override = null) {{
            const opacityScale = override?.opacityScale ?? 1;
            pulseGlow.visible = !removed;
            pulseGlow.material.color.setHex(active ? reviewRed : 0x69dcff);
            pulseGlow.material.opacity = removed ? 0 : (active ? 0.44 : 0.2) * opacityScale;
          }},
        }},
        ...orbits.map((orbit, index) => {{
          const original = index === 0 ? 0x6fe5ff : index === 1 ? 0x56b6ff : 0x9cf1ff;
          return {{
            id: `orbit-${{index + 1}}`,
            label: `Orbit ring ${{index + 1}}`,
            describe: () => `Keep or remove orbit ring ${{index + 1}} from the center hologram.`,
            apply(active, removed, override = null) {{
              const opacityScale = override?.opacityScale ?? 1;
              const scaleBoost = override?.scale ?? 1;
              orbit.mesh.visible = !removed;
              orbit.mesh.material.uniforms.uReviewMix.value = removed ? 0 : active ? 1 : 0;
              orbit.mesh.material.uniforms.uOpacity.value = removed ? 0 : (active ? 0.92 : 0.62) * opacityScale;
              orbit.mesh.scale.setScalar(scaleBoost);
            }},
          }};
        }}),
        {{
          id: "shell-arcs",
          label: "Outer shell arcs",
          describe: () => "Keep or remove the broken arc traces that sweep around the hologram shell.",
          apply(active, removed, override = null) {{
            const opacityScale = override?.opacityScale ?? 1;
            shellArcs.forEach((arc, index) => {{
              const original = index === 0 ? 0x86f2ff : index === 1 ? 0x5fb8ff : 0x87deff;
              arc.visible = !removed;
              arc.material.color.setHex(active ? reviewRed : original);
              arc.material.opacity = removed ? 0 : (active ? 1 : 0.9) * opacityScale;
            }});
          }},
        }},
        {{
          id: "particle-cloud",
          label: "Circling dot cloud",
          describe: () => "Keep or remove the circling dot cloud around JARVIS.",
          apply(active, removed, override = null) {{
            particles.visible = !removed;
            particleMaterial.uniforms.uReviewMix.value = removed ? 0 : active ? 1 : 0;
            const drawCount = Math.max(12, Math.min(particleCount, Math.floor(particleCount * (override?.density ?? 1))));
            particleGeometry.setDrawRange(0, removed ? 0 : drawCount);
          }},
        }},
        {{
          id: "link-lines",
          label: "Link lines",
          describe: () => "Keep or remove the faint connective lines between the moving dots.",
          apply(active, removed, override = null) {{
            const opacityScale = override?.opacityScale ?? 1;
            lineField.visible = !removed;
            lineField.material.color.setHex(active ? reviewRed : 0x6ee3ff);
            lineField.material.opacity = removed ? 0 : (active ? 0.65 : 0.18) * opacityScale;
          }},
        }},
      ];

      function animate(time) {{
        const seconds = time * 0.001;
        state.energyCurrent += (state.energyTarget - state.energyCurrent) * 0.08;
        const energy = state.energyCurrent;
        document.documentElement.style.setProperty("--energy", energy.toFixed(3));
        const review = currentReviewPageState("shell");
        const coreOverride = review.overrides.get("core-wireframe") || null;
        const pulseCoreOverride = review.overrides.get("pulse-core") || null;
        const pulseGlowOverride = review.overrides.get("pulse-glow") || null;
        const shellArcOverride = review.overrides.get("shell-arcs") || null;
        const particleOverride = review.overrides.get("particle-cloud") || null;
        const lineOverride = review.overrides.get("link-lines") || null;
        particleMaterial.uniforms.uEnergy.value = energy;

        root.rotation.y = seconds * (0.12 + energy * 0.1);
        root.rotation.x = Math.sin(seconds * 0.4) * 0.08;

        core.rotation.y = -seconds * 0.34 * (coreOverride?.speedScale ?? 1);
        core.rotation.x = seconds * 0.17 * (coreOverride?.speedScale ?? 1);
        core.scale.setScalar((1 + energy * 0.08) * (coreOverride?.scale ?? 1));

        pulseCore.scale.setScalar((0.82 + energy * 0.2) * (pulseCoreOverride?.scale ?? 1));
        pulseGlow.scale.setScalar((1.2 + energy * 0.72) * (pulseGlowOverride?.scale ?? 1));
        pulseGlow.material.opacity = (0.12 + energy * 0.22) * (pulseGlowOverride?.opacityScale ?? 1);
        pulseGlow.visible = false;

        coreParticleMaterial.uniforms.uEnergy.value = energy;
        const corePositionAttr = coreParticleGeometry.getAttribute("position");
        for (let i = 0; i < coreParticleSeeds.length; i += 1) {{
          const seed = coreParticleSeeds[i];
          const angle = seed.theta + seconds * seed.speed * (pulseCoreOverride?.speedScale ?? 1);
          const radius = seed.radius * (pulseCoreOverride?.scale ?? 1) + Math.sin(seconds * (1.6 + seed.speed) + seed.phase) * 0.03;
          corePositionAttr.array[i * 3] = radius * Math.sin(seed.phi) * Math.cos(angle);
          corePositionAttr.array[i * 3 + 1] = radius * Math.cos(seed.phi);
          corePositionAttr.array[i * 3 + 2] = radius * Math.sin(seed.phi) * Math.sin(angle);
        }}
        corePositionAttr.needsUpdate = true;

        orbits.forEach((orbit, index) => {{
          const orbitOverride = review.overrides.get(`orbit-${{index + 1}}`) || null;
          const orbitPositionAttr = orbit.geometry.getAttribute("position");
          const orbitBandTightness = 1 + (energy * 0.018);
          for (let i = 0; i < orbit.seeds.length; i += 1) {{
            const seed = orbit.seeds[i];
            const angle = seed.angle + seconds * orbit.speed * (orbitOverride?.speedScale ?? 1) + Math.sin(seconds * 0.18 + seed.phase) * seed.wobble;
            const radius = (orbit.radius + (seed.jitter * orbitBandTightness));
            orbitPositionAttr.array[i * 3] = Math.cos(angle) * radius;
            orbitPositionAttr.array[i * 3 + 1] = Math.sin(angle) * radius;
            orbitPositionAttr.array[i * 3 + 2] = seed.z + Math.sin(seconds * 0.22 + seed.phase) * 0.008;
          }}
          orbitPositionAttr.needsUpdate = true;
          const orbitRate = orbitOverride?.speedScale ?? 1;
          orbit.mesh.rotation.x = orbit.rx + (seconds * (0.22 + index * 0.05) * orbitRate * (index % 2 === 0 ? 1 : -1));
          orbit.mesh.rotation.y = (seconds * (0.17 + index * 0.04) * orbitRate * (index % 2 === 0 ? -1 : 1));
          orbit.mesh.rotation.z = orbit.rz + Math.sin(seconds * (0.28 + index * 0.07) * orbitRate) * orbit.baseTilt;
          orbit.mesh.material.uniforms.uEnergy.value = energy;
        }});

        shellArcs.forEach((arc, index) => {{
          arc.rotation.z = seconds * (0.15 + index * 0.06) * (shellArcOverride?.speedScale ?? 1) * (index % 2 === 0 ? 1 : -1);
          arc.material.opacity = (0.22 + energy * 0.45) * (shellArcOverride?.opacityScale ?? 1);
        }});

        const positionAttr = particleGeometry.getAttribute("position");
        const speechBreath = 1;
        for (let i = 0; i < seeds.length; i += 1) {{
          const seed = seeds[i];
          const orbitTheta = seed.theta + seconds * seed.speed;
          const orbitPhi = seed.phi + Math.sin(seconds * seed.speed + seed.phase) * seed.wobble;
          const radiusScale = particleOverride?.scale ?? 1;
          const speedScale = particleOverride?.speedScale ?? 1;
          const radius = ((seed.radius * radiusScale) * speechBreath) + Math.sin(seconds * speedScale * (0.9 + seed.speed) + seed.phase) * (0.06 + energy * 0.08);
          positionAttr.array[i * 3] = radius * Math.sin(orbitPhi) * Math.cos(orbitTheta);
          positionAttr.array[i * 3 + 1] = radius * Math.cos(orbitPhi) * 0.88;
          positionAttr.array[i * 3 + 2] = radius * Math.sin(orbitPhi) * Math.sin(orbitTheta);
        }}
        positionAttr.needsUpdate = true;

        const maxLines = Math.min(lineCount, seeds.length - 2);
        for (let i = 0; i < maxLines; i += 1) {{
          const a = (i * 5 + Math.floor(seconds * 16)) % seeds.length;
          const b = (a + 17 + i) % seeds.length;
          const ax = positionAttr.array[a * 3];
          const ay = positionAttr.array[a * 3 + 1];
          const az = positionAttr.array[a * 3 + 2];
          const bx = positionAttr.array[b * 3];
          const by = positionAttr.array[b * 3 + 1];
          const bz = positionAttr.array[b * 3 + 2];
          linePositions[i * 6] = ax;
          linePositions[i * 6 + 1] = ay;
          linePositions[i * 6 + 2] = az;
          linePositions[i * 6 + 3] = bx;
          linePositions[i * 6 + 4] = by;
          linePositions[i * 6 + 5] = bz;
        }}
        lineGeometry.attributes.position.needsUpdate = true;
        lineField.material.opacity = (0.08 + energy * 0.22) * (lineOverride?.opacityScale ?? 1);
        applyHoloReviewState(sceneState);

        renderer.render(scene, camera);
        if (!sceneState.ready) {{
          sceneState.ready = true;
          mount.classList.add("holo-live");
        }}
        sceneState.frame = requestAnimationFrame(animate);
      }}

      applyHoloReviewState(sceneState);
      sceneState.frame = requestAnimationFrame(animate);
      state.holoCoreScene = sceneState;
      return sceneState;
    }}

    function applyHoloReviewState(sceneState = state.holoCoreScene) {{
      if (!sceneState) {{
        return;
      }}
      const pageId = currentReviewPageId();
      const review = state.holoReview;
      const reviewState = currentReviewPageState(pageId);
      const targets = getReviewTargetsForPage(pageId);
      const current = review.active && review.pageId === pageId ? targets[review.index] : null;
      targets.forEach((target) => {{
        const removed = reviewState.removed.has(target.id);
        const active = current?.id === target.id;
        const override = reviewState.overrides.get(target.id) || null;
        target.apply(active, removed, override);
      }});
    }}

    function parseDesignFeedback(targetId, note) {{
      const lowered = note.toLowerCase();
      const override = {{
        opacityScale: 1,
        speedScale: 1,
        scale: 1,
        density: 1,
      }};

      if (/(remove|hide|get rid of|take off|delete)/.test(lowered)) {{
        override.remove = true;
      }}
      if (/(brighter|more visible|stronger|more intense|boost)/.test(lowered)) {{
        override.opacityScale *= 1.35;
      }}
      if (/(dimmer|softer|fainter|less visible|subtle)/.test(lowered)) {{
        override.opacityScale *= 0.72;
      }}
      if (/(smaller|shrink|tighter|reduce size)/.test(lowered)) {{
        override.scale *= 0.88;
      }}
      if (/(larger|bigger|wider|expand)/.test(lowered)) {{
        override.scale *= 1.12;
      }}
      if (/(slower|calmer|gentler|less motion)/.test(lowered)) {{
        override.speedScale *= 0.72;
      }}
      if (/(faster|quicker|more motion|more energetic)/.test(lowered)) {{
        override.speedScale *= 1.28;
      }}
      if (/(less busy|cleaner|fewer|sparser)/.test(lowered)) {{
        override.density *= 0.62;
        override.opacityScale *= 0.82;
      }}
      if (/(more busy|denser|more dots|fuller)/.test(lowered)) {{
        override.density *= 1.22;
        override.opacityScale *= 1.12;
      }}
      if (/(more glow|more holographic|glassier|glowier)/.test(lowered)) {{
        override.opacityScale *= 1.22;
      }}
      if (/(less glow|less holographic|flatter)/.test(lowered)) {{
        override.opacityScale *= 0.82;
      }}
      return override;
    }}

    function buildDesignReviewPayload() {{
      return serializeDesignReviewState();
    }}

    async function persistDesignReviewState(options = {{}}) {{
      const {{
        announce = false,
        successMessage = "Saved. Your center-animation changes will persist after refresh.",
        failureMessage = "Save failed in this browser session.",
      }} = options;
      const saved = document.getElementById("design-review-saved");
      try {{
        const payload = buildDesignReviewPayload();
        window.localStorage.setItem(HOLO_REVIEW_STORAGE_KEY, JSON.stringify(payload));
        await loadJSON("/api/design-review-state", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload),
        }});
        if (saved && successMessage) {{
          saved.textContent = successMessage;
        }}
        if (announce) {{
          document.getElementById("last-jarvis-text").textContent = "Center animation changes saved.";
          const ambientSubtitle = document.getElementById("ambient-subtitle");
          if (ambientSubtitle) ambientSubtitle.textContent = "Saved center-animation review changes.";
        }}
        return true;
      }} catch (error) {{
        console.error(error);
        if (saved) {{
          saved.textContent = failureMessage;
        }}
        return false;
      }}
    }}

    function saveDesignReviewState() {{
      return persistDesignReviewState({{
        announce: true,
      }});
    }}

    async function loadDesignReviewState() {{
      try {{
        const remote = await loadJSON("/api/design-review-state").catch(() => null);
        const raw = window.localStorage.getItem(HOLO_REVIEW_STORAGE_KEY);
        const parsed = raw ? JSON.parse(raw) : (remote || {{}});
        if (remote && !raw) {{
          window.localStorage.setItem(HOLO_REVIEW_STORAGE_KEY, JSON.stringify(remote));
        }}
        if (raw) {{
          loadJSON("/api/design-review-state", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: raw,
          }}).catch((error) => console.error(error));
        }}
        hydrateDesignReviewState(parsed);
      }} catch (error) {{
        console.error(error);
      }}
    }}

    function syncDesignReviewPanel() {{
      const pageId = currentReviewPageId();
      ensureReviewPage(pageId);
      const review = state.holoReview;
      review.pageId = pageId;
      const reviewState = currentReviewPageState(pageId);
      const targets = getReviewTargetsForPage(pageId);
      const current = review.active && review.pageId === pageId ? targets[review.index] : null;
      const name = document.getElementById("design-review-name");
      const copy = document.getElementById("design-review-copy");
      const start = document.getElementById("design-review-start");
      const apply = document.getElementById("design-review-apply");
      const save = document.getElementById("design-review-save");
      const keep = document.getElementById("design-review-keep");
      const remove = document.getElementById("design-review-remove");
      const next = document.getElementById("design-review-next");
      const stop = document.getElementById("design-review-stop");
      const input = document.getElementById("design-review-input");
      const saved = document.getElementById("design-review-saved");
      const panel = document.getElementById("design-review-panel");
      const launcherState = document.getElementById("design-review-launcher-state");
      if (!name || !copy || !start || !apply || !save || !keep || !remove || !next || !stop || !input || !saved || !panel || !launcherState) {{
        return;
      }}
      const shouldCollapse = !review.expanded && !review.active;
      const reviewEnabled = isReviewEnabledForPage(pageId);
      panel.classList.toggle("hidden", !reviewEnabled && shouldCollapse);
      panel.classList.toggle("collapsed", shouldCollapse);
      launcherState.textContent = review.active ? "Live" : reviewState.notes.size || reviewState.removed.size ? "Saved" : "Ready";
      if (!reviewEnabled) {{
        name.textContent = "Disabled";
        copy.textContent = "Page review is disabled for this page. Open Settings and turn it on for the current page when you want to critique individual elements here.";
        input.value = "";
        input.disabled = true;
        saved.textContent = "Review is currently off for this page.";
        start.disabled = true;
        apply.disabled = true;
        save.disabled = false;
        keep.disabled = true;
        remove.disabled = true;
        next.disabled = true;
        stop.disabled = true;
      }} else if (!targets.length) {{
        name.textContent = "Unavailable";
        copy.textContent = "There are no registered review targets for this page yet.";
        input.value = "";
        input.disabled = true;
        saved.textContent = "Nothing reviewable is registered on this page yet.";
        start.disabled = true;
        apply.disabled = true;
        save.disabled = false;
        keep.disabled = true;
        remove.disabled = true;
        next.disabled = true;
        stop.disabled = true;
      }} else if (!review.active || !current) {{
        name.textContent = "Not active";
        copy.textContent = `Start review for ${{REVIEWABLE_PAGES.find(([id]) => id === pageId)?.[1] || "this page"}} to highlight one element at a time in red, then tell me what you want changed.`;
        input.value = "";
        input.disabled = true;
        saved.textContent = reviewState.removed.size || reviewState.notes.size
          ? "Saved changes are loaded. Start review to continue refining them."
          : "No feedback captured yet.";
        start.disabled = false;
        apply.disabled = true;
        save.disabled = false;
        keep.disabled = true;
        remove.disabled = true;
        next.disabled = true;
        stop.disabled = true;
      }} else {{
        name.textContent = current.label;
        copy.textContent = `${{current.describe()}} It is highlighted in red right now. Tell me what you want changed, then apply it or move on.`;
        input.disabled = false;
        input.value = reviewState.notes.get(current.id) || "";
        saved.textContent = reviewState.notes.get(current.id)
          ? `Saved feedback: ${{reviewState.notes.get(current.id)}}`
          : "No feedback captured for this element yet.";
        start.disabled = true;
        apply.disabled = false;
        save.disabled = false;
        keep.disabled = false;
        remove.disabled = false;
        next.disabled = false;
        stop.disabled = false;
      }}
      applyHoloReviewState();
    }}

    function formatTranscriptTimestamp(timestamp) {{
      if (!timestamp) return "";
      const date = new Date(timestamp);
      if (Number.isNaN(date.getTime())) return "";
      return date.toLocaleTimeString([], {{ hour: "numeric", minute: "2-digit" }});
    }}

    function catalystCaptureFromTurn(turn) {{
      const metadata = turn && typeof turn === "object" && turn.metadata && typeof turn.metadata === "object"
        ? turn.metadata
        : {{}};
      const capture = metadata.catalyst_capture && typeof metadata.catalyst_capture === "object"
        ? metadata.catalyst_capture
        : null;
      return capture && capture.ok ? capture : null;
    }}

    function transcriptDisplayText(turn) {{
      const base = String(turn?.text || "").trim();
      const capture = catalystCaptureFromTurn(turn);
      if (!capture) return base;
      const summary = String(capture.summary || "").trim();
      if (!summary || !base.endsWith(summary)) return base;
      const trimmed = base.slice(0, Math.max(0, base.length - summary.length)).replace(/\\s+$/, "");
      return trimmed.replace(/\\n{{3,}}$/g, "\\n\\n").trim() || base;
    }}

    function formatLifecycleStage(stage) {{
      return String(stage || "signal")
        .replace(/-/g, " ")
        .replace(/\\b\\w/g, (letter) => letter.toUpperCase());
    }}

    function formatLifecycleStatus(status) {{
      return String(status || "open")
        .replace(/-/g, " ")
        .replace(/\\b\\w/g, (letter) => letter.toUpperCase());
    }}

    function formatLifecycleTimestamp(timestamp) {{
      if (!timestamp) return "";
      const date = new Date(timestamp);
      if (Number.isNaN(date.getTime())) return "";
      return date.toLocaleString([], {{
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }});
    }}

    function transitionAgentLabel(step, fallback = "") {{
      const metadata = step && typeof step.metadata === "object" ? step.metadata : {{}};
      return String(step?.owner_agent || metadata.source_agent || metadata.owner_agent || fallback || "JARVIS").trim();
    }}

    function lifecycleAvailableActions(item) {{
      if (!item || typeof item !== "object") return [];
      const stage = String(item.stage || item.current_stage || "signal").trim().toLowerCase() || "signal";
      if (stage === "signal" || stage === "hypothesis") {{
        return [
          {{ id: "promote-to-brief", label: "Promote to Brief", variant: "primary" }},
          {{ id: "archive", label: "Archive", variant: "quiet", confirm: "Archive this work item?" }},
        ];
      }}
      if (stage === "project-brief") {{
        return [
          {{ id: "build-plan", label: "Build Plan", variant: "primary" }},
          {{ id: "archive", label: "Archive", variant: "quiet", confirm: "Archive this brief?" }},
        ];
      }}
      if (stage === "implementation-plan" || stage === "staged-action" || stage === "review") {{
        return [
          {{ id: "mark-succeeded", label: "Mark Succeeded", variant: "primary" }},
          {{ id: "mark-deferred", label: "Mark Deferred", variant: "quiet" }},
          {{ id: "mark-learned", label: "Mark Learned", variant: "quiet" }},
          {{ id: "mark-failed", label: "Mark Failed", variant: "danger", confirm: "Mark this work item as failed?" }},
          {{ id: "mark-abandoned", label: "Mark Abandoned", variant: "danger", confirm: "Mark this work item as abandoned?" }},
        ];
      }}
      if (stage === "outcome") {{
        return [
          {{ id: "reopen", label: "Reopen", variant: "primary" }},
          {{ id: "clone-forward", label: "Clone Forward", variant: "quiet" }},
        ];
      }}
      return [];
    }}

    function pushLifecycleActionTrail(entry) {{
      if (!entry || typeof entry !== "object") return;
      state.lifecycleActionTrail = [entry, ...(Array.isArray(state.lifecycleActionTrail) ? state.lifecycleActionTrail : [])].slice(0, 10);
    }}

    function showLifecycleToast(title, body) {{
      const toast = document.getElementById("lifecycle-toast");
      const titleNode = document.getElementById("lifecycle-toast-title");
      const bodyNode = document.getElementById("lifecycle-toast-body");
      if (!toast || !titleNode || !bodyNode) return;
      titleNode.textContent = String(title || "Lifecycle Update");
      bodyNode.textContent = String(body || "Update complete.");
      toast.classList.add("show");
      if (state.lifecycleToastTimer) {{
        window.clearTimeout(state.lifecycleToastTimer);
      }}
      state.lifecycleToastTimer = window.setTimeout(() => {{
        toast.classList.remove("show");
      }}, 2800);
    }}

    function lifecycleRecordsFromData(sourceData = null) {{
      const pools = [
        sourceData?.pipeline_state?.work_lifecycle?.records,
        sourceData?.work_lifecycle?.records,
        state.dashboard?.pipeline_state?.work_lifecycle?.records,
        state.dashboard?.work_lifecycle?.records,
      ];
      for (const pool of pools) {{
        if (Array.isArray(pool) && pool.length) {{
          return pool.filter((item) => item && typeof item === "object");
        }}
      }}
      return [];
    }}

    function findLifecycleRecord(workId, sourceData = null) {{
      const target = String(workId || "").trim();
      if (!target) return null;
      return lifecycleRecordsFromData(sourceData).find((item) => String(item.work_id || "").trim() === target) || null;
    }}

    function renderRecentLifecycleActions() {{
      const trail = Array.isArray(state.lifecycleActionTrail) ? state.lifecycleActionTrail : [];
      if (!trail.length) {{
        return `<div class="empty">No lifecycle actions have been taken in this session yet.</div>`;
      }}
      return `
        <div class="recent-action-trail">
          ${{trail.map((item) => `
            <div class="recent-action-item">
              <strong>${{escapeHtml(String(item.label || item.action || "Action").replace(/-/g, " "))}}</strong>
              <span>${{escapeHtml(item.title || "Work item")}}</span>
              <span>${{escapeHtml(formatLifecycleTimestamp(item.timestamp || new Date().toISOString()))}}</span>
            </div>
          `).join("")}}
        </div>
      `;
    }}

    function lifecycleTransitions(record, limit = 6) {{
      if (!record || typeof record !== "object") return [];
      const transitions = Array.isArray(record.transitions) ? record.transitions.filter((item) => item && typeof item === "object") : [];
      return transitions.slice(-Math.max(1, limit));
    }}

    function buildHistoryTimelineNode(transitions, options = {{}}) {{
      const steps = Array.isArray(transitions) ? transitions.filter((item) => item && typeof item === "object") : [];
      if (!steps.length) return null;
      const timeline = document.createElement("div");
      timeline.className = "history-timeline";
      for (const step of steps) {{
        const row = document.createElement("div");
        row.className = "history-step";

        const main = document.createElement("div");
        main.className = "history-step-main";

        const top = document.createElement("div");
        top.className = "history-step-top";
        const stage = document.createElement("div");
        stage.className = "history-step-stage";
        stage.textContent = formatLifecycleStage(step.stage);
        const status = document.createElement("div");
        status.className = "history-step-status";
        status.textContent = formatLifecycleStatus(step.status);
        top.appendChild(stage);
        top.appendChild(status);
        main.appendChild(top);

        const summary = document.createElement("div");
        summary.className = "history-step-summary";
        const summaryParts = [
          String(step.rationale || step.source || "").trim() || "Lifecycle transition recorded.",
          transitionAgentLabel(step, options.fallbackAgent || ""),
        ].filter(Boolean);
        summary.textContent = summaryParts[0];
        if (summaryParts[1]) {{
          summary.textContent = `${{summary.textContent}}`;
          const movedBy = document.createElement("div");
          movedBy.className = "history-step-summary";
          movedBy.textContent = `Moved by ${{summaryParts[1]}}`;
          main.appendChild(summary);
          main.appendChild(movedBy);
        }} else {{
          main.appendChild(summary);
        }}

        const time = document.createElement("div");
        time.className = "history-step-time";
        time.textContent = formatLifecycleTimestamp(step.timestamp);

        row.appendChild(main);
        row.appendChild(time);
        timeline.appendChild(row);
      }}
      return timeline;
    }}

    function renderHistoryTimeline(transitions, options = {{}}) {{
      const steps = Array.isArray(transitions) ? transitions.filter((item) => item && typeof item === "object") : [];
      if (!steps.length) {{
        return `<div class="empty">${{escapeHtml(options.emptyLabel || "No transition history yet.")}}</div>`;
      }}
      return `
        <div class="history-timeline">
          ${{steps.map((step) => `
            <div class="history-step">
              <div class="history-step-main">
                <div class="history-step-top">
                  <div class="history-step-stage">${{escapeHtml(formatLifecycleStage(step.stage))}}</div>
                  <div class="history-step-status">${{escapeHtml(formatLifecycleStatus(step.status))}}</div>
                </div>
                <div class="history-step-summary">${{escapeHtml(step.rationale || step.source || "Lifecycle transition recorded.")}}</div>
                <div class="history-step-summary">${{escapeHtml(`Moved by ${{transitionAgentLabel(step, options.fallbackAgent || "")}}`)}}</div>
              </div>
              <div class="history-step-time">${{escapeHtml(formatLifecycleTimestamp(step.timestamp))}}</div>
            </div>
          `).join("")}}
        </div>
      `;
    }}

    function renderLifecycleActionControls(item) {{
      if (!item || typeof item !== "object" || !item.work_id) {{
        return "";
      }}
      const actions = lifecycleAvailableActions(item);
      return `
        <div class="work-item-actions">
          ${{actions.map((action) => `
            <button
              type="button"
              class="work-item-action-button"
              data-work-action="${{escapeHtml(action.id || "")}}"
              data-work-id="${{escapeHtml(item.work_id || "")}}"
              data-variant="${{escapeHtml(action.variant || "quiet")}}"
              ${{action.confirm ? `data-confirm-message="${{escapeHtml(action.confirm)}}"` : ""}}
            >${{escapeHtml(action.label || action.id || "Action")}}</button>
          `).join("")}}
          <button type="button" class="work-item-action-button" data-work-action="inspect" data-work-id="${{escapeHtml(item.work_id || "")}}" data-variant="quiet">Open Inspector</button>
        </div>
      `;
    }}

    function renderArtifactRefs(artifactRefs, workId = "") {{
      const refs = Array.isArray(artifactRefs) ? artifactRefs.filter((item) => item && typeof item === "object") : [];
      if (!refs.length) {{
        return `<div class="empty">No linked artifacts yet.</div>`;
      }}
      return `
        <div class="work-item-artifacts">
          ${{refs.map((ref) => `
            <div class="work-item-artifact-row">
              <div class="work-item-artifact-row-head">
                <strong>${{escapeHtml(formatLifecycleStage(ref.stage || ref.artifact_type || "artifact"))}}</strong>
                ${{workId && ref.record_id ? `<button type="button" class="work-item-artifact-open" data-work-id="${{escapeHtml(workId)}}" data-record-id="${{escapeHtml(ref.record_id || "")}}">Open Linked Artifact</button>` : ""}}
              </div>
              <span>${{escapeHtml(String(ref.artifact_type || "artifact").replace(/-/g, " "))}} · ${{escapeHtml(ref.record_id || "No record id")}}</span>
              <span>${{escapeHtml(formatLifecycleTimestamp(ref.timestamp))}}</span>
            </div>
          `).join("")}}
        </div>
      `;
    }}

    function buildArtifactRefsNode(artifactRefs, workId = "") {{
      const refs = Array.isArray(artifactRefs) ? artifactRefs.filter((item) => item && typeof item === "object") : [];
      if (!refs.length) return null;
      const wrapper = document.createElement("div");
      wrapper.className = "work-item-artifacts";
      for (const ref of refs) {{
        const row = document.createElement("div");
        row.className = "work-item-artifact-row";
        const head = document.createElement("div");
        head.className = "work-item-artifact-row-head";
        const title = document.createElement("strong");
        title.textContent = formatLifecycleStage(ref.stage || ref.artifact_type || "artifact");
        head.appendChild(title);
        if (workId && ref.record_id) {{
          const openButton = document.createElement("button");
          openButton.type = "button";
          openButton.className = "work-item-artifact-open";
          openButton.dataset.workId = String(workId || "");
          openButton.dataset.recordId = String(ref.record_id || "");
          openButton.textContent = "Open Linked Artifact";
          head.appendChild(openButton);
        }}
        const meta = document.createElement("span");
        meta.textContent = `${{String(ref.artifact_type || "artifact").replace(/-/g, " ")}} · ${{String(ref.record_id || "No record id")}}`;
        const time = document.createElement("span");
        time.textContent = formatLifecycleTimestamp(ref.timestamp);
        row.appendChild(head);
        row.appendChild(meta);
        row.appendChild(time);
        wrapper.appendChild(row);
      }}
      return wrapper;
    }}

    function renderLifecycleWorkItems(records, options = {{}}) {{
      const rows = Array.isArray(records) ? records.filter((item) => item && typeof item === "object") : [];
      if (!rows.length) {{
        return `<div class="empty">${{escapeHtml(options.emptyLabel || "No tracked work items yet.")}}</div>`;
      }}
      return `
        <div class="work-items-grid">
          ${{rows.map((item) => `
            <details class="work-item-details">
              <summary>
                <div class="work-item-card">
              <div class="work-item-head">
                <div class="work-item-title">${{escapeHtml(item.title || "Untitled work item")}}</div>
                <div class="work-item-stage">${{escapeHtml(formatLifecycleStage(item.stage || item.current_stage || "signal"))}}</div>
              </div>
              <div class="work-item-meta">
                ${{item.lane ? `<div class="work-item-chip">${{escapeHtml(String(item.lane || "").replace(/-/g, " "))}}</div>` : ""}}
                ${{item.status ? `<div class="work-item-chip">${{escapeHtml(formatLifecycleStatus(item.status))}}</div>` : ""}}
                ${{item.owner_agent ? `<div class="work-item-chip">${{escapeHtml(item.owner_agent)}}</div>` : ""}}
              </div>
              ${{item.rationale ? `<div class="work-item-rationale">${{escapeHtml(item.rationale)}}</div>` : ""}}
                </div>
              </summary>
              <div class="work-item-expanded">
              <div class="work-item-section">
                  <div class="work-item-section-title">Transition History</div>
                  ${{renderHistoryTimeline(lifecycleTransitions(item, options.transitionLimit || 12), {{ emptyLabel: "No transition history yet.", fallbackAgent: item.owner_agent || "" }})}}
                </div>
                ${{renderLifecycleActionControls(item)}}
                <div class="work-item-section">
                  <div class="work-item-section-title">Linked Artifacts</div>
                  ${{renderArtifactRefs(item.artifact_refs || [], item.work_id || "")}}
                </div>
              </div>
            </details>
          `).join("")}}
        </div>
      `;
    }}

    function buildCatalystArtifactCard(capture) {{
      if (!capture || !capture.ok) return null;
      const record = capture.record && typeof capture.record === "object" ? capture.record : {{}};
      const lifecycle = findLifecycleRecord(capture.work_id || record.work_id || "");
      const card = document.createElement("div");
      card.className = "transcript-artifact";

      const head = document.createElement("div");
      head.className = "transcript-artifact-head";
      const label = document.createElement("div");
      label.className = "transcript-artifact-label";
      label.textContent = "Catalyst Capture";
      const kind = document.createElement("div");
      kind.className = "transcript-artifact-kind";
      kind.textContent = String(capture.kind || "artifact").replace(/-/g, " ");
      head.appendChild(label);
      head.appendChild(kind);
      card.appendChild(head);

      const title = document.createElement("div");
      title.className = "transcript-artifact-title";
      title.textContent = String(record.project_name || record.focus || record.opportunity || capture.title || "Captured item").trim();
      card.appendChild(title);

      const meta = document.createElement("div");
      meta.className = "transcript-artifact-meta";
      if (capture.lane) {{
        const laneChip = document.createElement("div");
        laneChip.className = "transcript-artifact-chip";
        laneChip.textContent = String(capture.lane || "").replace(/-/g, " ");
        meta.appendChild(laneChip);
      }}
      if (capture.kind) {{
        const kindChip = document.createElement("div");
        kindChip.className = "transcript-artifact-chip";
        kindChip.textContent = String(capture.kind || "").replace(/-/g, " ");
        meta.appendChild(kindChip);
      }}
      if (meta.childElementCount) {{
        card.appendChild(meta);
      }}

      const summary = document.createElement("div");
      summary.className = "transcript-artifact-summary";
      summary.textContent = String(capture.summary || record.recommendation || record.objective || "").trim();
      if (summary.textContent) {{
        card.appendChild(summary);
      }}

      if (lifecycle) {{
        const details = document.createElement("details");
        details.className = "transcript-artifact-details";
        const summaryToggle = document.createElement("summary");
        summaryToggle.textContent = "Inspect Full Work Trail";
        details.appendChild(summaryToggle);

        const history = document.createElement("div");
        history.className = "transcript-artifact-history";
        const historyLabel = document.createElement("div");
        historyLabel.className = "transcript-artifact-history-label";
        historyLabel.textContent = "Transition History";
        history.appendChild(historyLabel);
        const timeline = buildHistoryTimelineNode(lifecycleTransitions(lifecycle, 8), {{
          fallbackAgent: lifecycle.owner_agent || "",
        }});
        if (timeline) {{
          history.appendChild(timeline);
        }}
        details.appendChild(history);

        const actions = document.createElement("div");
        actions.className = "transcript-artifact-actions";
        actions.innerHTML = renderLifecycleActionControls(lifecycle);
        details.appendChild(actions);

        const artifactSection = document.createElement("div");
        artifactSection.className = "work-item-section";
        const artifactLabel = document.createElement("div");
        artifactLabel.className = "work-item-section-title";
        artifactLabel.textContent = "Linked Artifacts";
        artifactSection.appendChild(artifactLabel);
        const artifactRefs = buildArtifactRefsNode(lifecycle.artifact_refs || [], lifecycle.work_id || "");
        artifactSection.appendChild(artifactRefs || document.createElement("div"));
        if (!artifactRefs) {{
          artifactSection.lastChild.className = "empty";
          artifactSection.lastChild.textContent = "No linked artifacts yet.";
        }}
        details.appendChild(artifactSection);

        card.appendChild(details);
      }}

      return card;
    }}

    function conversationStorageKey(actor = "") {{
      const normalized = String(actor || document.getElementById("actor")?.value || "Chris").trim().toLowerCase() || "chris";
      return `jarvis:conversation:${{normalized}}`;
    }}

    function loadStoredConversationId(actor = "") {{
      try {{
        return window.localStorage.getItem(conversationStorageKey(actor)) || "";
      }} catch (error) {{
        return "";
      }}
    }}

    function saveStoredConversationId(conversationId, actor = "") {{
      try {{
        if (!conversationId) {{
          window.localStorage.removeItem(conversationStorageKey(actor));
          return;
        }}
        window.localStorage.setItem(conversationStorageKey(actor), conversationId);
      }} catch (error) {{
        console.debug("Conversation persistence unavailable", error);
      }}
    }}

    function renderTranscriptHistory() {{
      const rail = document.getElementById("transcript-history");
      const emptyState = document.getElementById("transcript-empty-state");
      if (!rail || !emptyState) return;
      rail.innerHTML = "";
      const stack = document.createElement("div");
      stack.className = "transcript-stack";
      rail.appendChild(stack);
      const turns = Array.isArray(state.transcriptTurns) ? state.transcriptTurns.slice(-18) : [];
      for (const turn of turns) {{
        const row = document.createElement("div");
        const bubble = document.createElement("div");
        const role = String(turn.role || "assistant").toLowerCase() === "user" ? "user" : "assistant";
        row.className = `transcript-row ${{role}}`;
        bubble.className = `transcript-bubble ${{role}}`;
        const speaker = document.createElement("div");
        speaker.className = "speaker";
        speaker.textContent = role === "user" ? "You" : "JARVIS";
        const content = document.createElement("div");
        content.className = "content";
        content.textContent = transcriptDisplayText(turn);
        const timestamp = document.createElement("div");
        timestamp.className = "timestamp";
        timestamp.textContent = formatTranscriptTimestamp(turn.created_at);
        bubble.appendChild(speaker);
        bubble.appendChild(content);
        const artifactCard = role === "assistant" ? buildCatalystArtifactCard(catalystCaptureFromTurn(turn)) : null;
        if (artifactCard) {{
          bubble.appendChild(artifactCard);
        }}
        if (timestamp.textContent) {{
          bubble.appendChild(timestamp);
        }}
        row.appendChild(bubble);
        stack.appendChild(row);
      }}
      const hasTurns = turns.length > 0;
      emptyState.style.display = hasTurns ? "none" : "block";
      const stickToBottom = () => {{
        rail.scrollTop = rail.scrollHeight;
      }};
      stickToBottom();
      window.requestAnimationFrame(() => stickToBottom());
      document.body.dataset.transcriptEmpty = hasTurns ? "false" : "true";
    }}

    function syncTranscriptRail() {{
      const userText = (document.getElementById("last-user-text")?.textContent || "").trim();
      const jarvisText = (document.getElementById("last-jarvis-text")?.textContent || "").trim();
      const emptyUser = userText === "" || userText === "Awaiting command.";
      const emptyJarvis = jarvisText === "" || jarvisText === "Standing by.";
      if ((!Array.isArray(state.transcriptTurns) || !state.transcriptTurns.length) && !(emptyUser && emptyJarvis)) {{
        document.body.dataset.transcriptEmpty = "false";
      }} else if (!Array.isArray(state.transcriptTurns) || !state.transcriptTurns.length) {{
        document.body.dataset.transcriptEmpty = "true";
      }}
      renderTranscriptHistory();
    }}

    function applyConversationSnapshot(thread) {{
      const active = thread && typeof thread === "object" ? thread : {{}};
      state.conversationId = String(active.conversation_id || state.conversationId || "");
      if (state.conversationId) {{
        saveStoredConversationId(state.conversationId, preferredActorLabel());
      }}
      state.transcriptTurns = Array.isArray(active.turns) ? active.turns.map((turn) => ({{ ...turn }})) : [];
      const userTurns = state.transcriptTurns.filter((turn) => String(turn.role || "").toLowerCase() === "user");
      const assistantTurns = state.transcriptTurns.filter((turn) => String(turn.role || "").toLowerCase() !== "user");
      const latestUser = userTurns.length ? String(userTurns[userTurns.length - 1].text || "").trim() : "Awaiting command.";
      const latestAssistant = assistantTurns.length ? transcriptDisplayText(assistantTurns[assistantTurns.length - 1]) : "Standing by.";
      document.getElementById("last-user-text").textContent = latestUser || "Awaiting command.";
      document.getElementById("last-jarvis-text").textContent = latestAssistant || "Standing by.";
      renderTranscriptHistory();
    }}

    async function refreshChatState(options = {{}}) {{
      const actor = options.actor || document.getElementById("actor")?.value || "Chris";
      const room = options.room || document.getElementById("room")?.value || "office";
      const params = new URLSearchParams({{ actor, room }});
      if (state.conversationId) {{
        params.set("conversation_id", state.conversationId);
      }}
      const data = await loadJSON(`/api/chat-state?${{params.toString()}}`, {{
        timeoutMs: Number(options.timeoutMs || 2500),
      }});
      if (data.conversation_id) {{
        state.conversationId = data.conversation_id;
        saveStoredConversationId(state.conversationId, actor);
      }}
      applyConversationSnapshot(data.active_conversation || {{}});
      return data;
    }}

    async function refreshLifecycleSurfaceState() {{
      await refreshDashboard({{ force: true }});
      await refreshChatState({{ actor: preferredActorLabel(), timeoutMs: 2500 }}).catch((error) => {{
        console.warn("Chat state refresh after lifecycle action failed", error);
      }});
      if (state.lifecycleInspector?.work_id) {{
        await loadLifecycleInspector(state.lifecycleInspector.work_id, {{ preserveSelection: true }}).catch((error) => {{
          console.warn("Lifecycle inspector refresh failed", error);
        }});
      }}
      if (state.packet) {{
        openPacket(state.packet);
      }} else {{
        renderTranscriptHistory();
      }}
    }}

    async function loadLifecycleInspector(workId, options = {{}}) {{
      const normalizedWorkId = String(workId || "").trim();
      if (!normalizedWorkId) return null;
      const actor = preferredActorLabel();
      const snapshot = await loadJSON(`/api/work-lifecycle/${{encodeURIComponent(normalizedWorkId)}}/inspector?actor=${{encodeURIComponent(actor)}}`, {{
        timeoutMs: 4000,
      }});
      const existingRecordId = options.preserveSelection
        ? String(state.lifecycleInspector?.selectedRecordId || "").trim()
        : "";
      const firstArtifact = Array.isArray(snapshot.artifacts) ? snapshot.artifacts.find((item) => item?.record_id) : null;
      state.lifecycleInspector = {{
        ...snapshot,
        selectedRecordId: existingRecordId || String(options.recordId || "").trim() || String(firstArtifact?.record_id || "").trim(),
      }};
      return state.lifecycleInspector;
    }}

    function selectedLifecycleArtifact(inspector = state.lifecycleInspector) {{
      const artifacts = Array.isArray(inspector?.artifacts) ? inspector.artifacts : [];
      const selected = String(inspector?.selectedRecordId || "").trim();
      return artifacts.find((item) => String(item?.record_id || "").trim() === selected) || artifacts[0] || null;
    }}

    function artifactViewerText(bundle) {{
      if (!bundle || typeof bundle !== "object") return "No artifact selected.";
      const artifact = bundle.artifact && typeof bundle.artifact === "object" ? bundle.artifact : null;
      if (!artifact) {{
        return bundle.message || "Artifact payload is unavailable.";
      }}
      return JSON.stringify(artifact, null, 2);
    }}

    function renderLifecycleInspectorMarkup() {{
      const inspector = state.lifecycleInspector;
      if (!inspector || !inspector.item) {{
        return `<div class="packet-grid"><div class="metric">Select a work item to inspect.</div></div>`;
      }}
      const item = inspector.item || {{}};
      const origin = inspector.origin || {{}};
      const posture = inspector.policy_posture || {{}};
      const artifacts = Array.isArray(inspector.artifacts) ? inspector.artifacts : [];
      const selectedArtifact = selectedLifecycleArtifact(inspector);
      return `
        <div class="inspector-grid">
          <div class="inspector-header">
            <div class="inspector-meta">
              <div class="work-item-chip">${{escapeHtml(formatLifecycleStage(item.stage || item.current_stage || "signal"))}}</div>
              ${{item.lane ? `<div class="work-item-chip">${{escapeHtml(String(item.lane || "").replace(/-/g, " "))}}</div>` : ""}}
              ${{item.status ? `<div class="work-item-chip">${{escapeHtml(formatLifecycleStatus(item.status))}}</div>` : ""}}
              ${{item.owner_agent ? `<div class="work-item-chip">${{escapeHtml(item.owner_agent)}}</div>` : ""}}
            </div>
            <h3 class="inspector-title">${{escapeHtml(item.title || "Untitled work item")}}</h3>
            ${{item.rationale ? `<div class="work-item-rationale">${{escapeHtml(item.rationale)}}</div>` : ""}}
          </div>
          <div class="inspector-actions">
            ${{renderLifecycleActionControls(item)}}
          </div>
          <div class="inspector-columns">
            <div class="inspector-panel">
              <h3>Transition Trail</h3>
              ${{renderHistoryTimeline(lifecycleTransitions(item, 18), {{ emptyLabel: "No transition history yet.", fallbackAgent: item.owner_agent || "" }})}}
            </div>
            <div class="inspector-panel">
              <h3>Operating Posture</h3>
              <div class="inspector-kv">
                <div class="inspector-kv-row"><strong>Origin</strong><div>${{escapeHtml(origin.source || "manual")}} · ${{escapeHtml(origin.owner_agent || item.owner_agent || "JARVIS")}}</div></div>
                <div class="inspector-kv-row"><strong>Origin Time</strong><span>${{escapeHtml(formatLifecycleTimestamp(origin.timestamp))}}</span></div>
                <div class="inspector-kv-row"><strong>Policy</strong><div>${{escapeHtml(posture.review_level || item.review_level || "review-as-needed")}}</div></div>
                <div class="inspector-kv-row"><strong>Approval Posture</strong><div>${{escapeHtml(posture.approval_summary || "No additional policy note.")}}</div></div>
                <div class="inspector-kv-row"><strong>Contributors</strong><div>${{escapeHtml((inspector.contributors || []).join(", ") || item.owner_agent || "JARVIS")}}</div></div>
              </div>
            </div>
          </div>
          <div class="inspector-columns">
            <div class="inspector-panel">
              <h3>Linked Artifacts</h3>
              ${{artifacts.length ? `
                <div class="inspector-artifact-list">
                  ${{artifacts.map((bundle) => `
                    <div class="inspector-artifact-item ${{String(bundle.record_id || "") === String(inspector.selectedRecordId || "") ? "active" : ""}}">
                      <strong>${{escapeHtml(formatLifecycleStage(bundle.artifact_type || "artifact"))}}</strong>
                      <span>${{escapeHtml(bundle.record_id || "No record id")}}</span>
                      <div class="work-item-actions">
                        <button type="button" class="work-item-action-button" data-work-action="select-artifact" data-work-id="${{escapeHtml(item.work_id || "")}}" data-record-id="${{escapeHtml(bundle.record_id || "")}}" data-variant="quiet">View Artifact</button>
                      </div>
                    </div>
                  `).join("")}}
                </div>
              ` : `<div class="empty">No linked artifacts yet.</div>`}}
            </div>
            <div class="inspector-panel">
              <h3>Artifact Viewer</h3>
              <div class="inspector-artifact-viewer">
                <div class="inspector-kv-row"><strong>Selected</strong><div>${{escapeHtml(selectedArtifact?.artifact_type || "None")}}</div></div>
                <pre class="inspector-artifact-pre">${{escapeHtml(artifactViewerText(selectedArtifact))}}</pre>
              </div>
            </div>
          </div>
          <div class="inspector-panel">
            <h3>Recent Action Trail</h3>
            ${{renderRecentLifecycleActions()}}
          </div>
        </div>
      `;
    }}

    async function performWorkLifecycleAction(workId, action) {{
      const normalizedWorkId = String(workId || "").trim();
      const normalizedAction = String(action || "").trim();
      if (!normalizedWorkId || !normalizedAction) {{
        return;
      }}
      const result = await loadJSON(`/api/work-lifecycle/${{encodeURIComponent(normalizedWorkId)}}/action`, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor: preferredActorLabel(),
          action: normalizedAction,
        }}),
      }});
      const workTitle =
        String(result?.work_item?.title || state.lifecycleInspector?.item?.title || findLifecycleRecord(normalizedWorkId)?.title || "Work item").trim();
      pushLifecycleActionTrail({{
        workId: normalizedWorkId,
        title: workTitle,
        action: normalizedAction,
        label: String(normalizedAction || "").replace(/-/g, " "),
        timestamp: new Date().toISOString(),
      }});
      await refreshLifecycleSurfaceState();
      const message = `Lifecycle updated: ${{normalizedAction.replace(/-/g, " ")}}.`;
      document.getElementById("last-jarvis-text").textContent = message;
      showLifecycleToast("Lifecycle Update", message);
      syncTranscriptRail();
      return result;
    }}

    async function openWorkLifecycleArtifact(workId, recordId) {{
      const normalizedWorkId = String(workId || "").trim();
      const normalizedRecordId = String(recordId || "").trim();
      if (!normalizedWorkId || !normalizedRecordId) {{
        return;
      }}
      await loadLifecycleInspector(normalizedWorkId, {{ recordId: normalizedRecordId }});
      openPacket("lifecycle-inspector", {{ bypassScene: true }});
    }}

    function scheduleChatStateWarmup(options = {{}}) {{
      const delayMs = Number(options.delayMs ?? 180);
      const actor = options.actor || document.getElementById("actor")?.value || "Chris";
      const room = options.room || document.getElementById("room")?.value || "office";
      const warm = () => {{
        refreshChatState({{
          actor,
          room,
          timeoutMs: Number(options.timeoutMs || 2500),
        }}).catch((error) => {{
          console.warn("Chat state warmup failed", error);
        }});
      }};
      if (typeof window.requestIdleCallback === "function") {{
        window.requestIdleCallback(() => warm(), {{
          timeout: Math.max(delayMs * 4, 1200),
        }});
        return;
      }}
      window.setTimeout(warm, delayMs);
    }}

    function commandInputElement() {{
      return document.getElementById("command-input");
    }}

    function focusSpeakComposer() {{
      const rail = document.getElementById("chat-panel");
      const input = commandInputElement();
      if (rail) {{
        rail.scrollIntoView({{ behavior: "smooth", block: "nearest" }});
      }}
      if (input) {{
        input.focus();
        const length = String(input.value || "").length;
        try {{
          input.setSelectionRange(length, length);
        }} catch (_error) {{
          // noop
        }}
      }}
    }}

    function autosizeCommandInput() {{
      const input = commandInputElement();
      if (!input) return;
      input.style.height = "0px";
      const nextHeight = Math.min(Math.max(input.scrollHeight, 58), 160);
      input.style.height = `${{nextHeight}}px`;
    }}

    function resetCommandInput() {{
      const input = commandInputElement();
      if (!input) return;
      input.value = "";
      autosizeCommandInput();
    }}

    function setComposerBusy(isBusy) {{
      const input = commandInputElement();
      const sendButton = document.getElementById("send-command");
      const talkButton = document.getElementById("voice-command");
      const attachButton = document.getElementById("add-attachment");
      if (input) input.disabled = !!isBusy;
      if (sendButton) sendButton.disabled = !!isBusy;
      if (talkButton) talkButton.disabled = !!isBusy;
      if (attachButton) attachButton.disabled = !!isBusy || !!state.uploadingAttachments;
    }}

    function renderAttachmentTray() {{
      const tray = document.getElementById("attachment-tray");
      const list = document.getElementById("attachment-list");
      const dropzone = document.getElementById("attachment-dropzone");
      const attachButton = document.getElementById("add-attachment");
      if (!tray || !list || !dropzone) return;
      const attachments = Array.isArray(state.pendingAttachments) ? state.pendingAttachments : [];
      tray.classList.toggle("active", attachments.length > 0 || state.attachmentDragActive || state.uploadingAttachments);
      dropzone.classList.toggle("active", !!state.attachmentDragActive);
      dropzone.querySelector("span").textContent = state.uploadingAttachments
        ? "Uploading attachments for this message..."
        : "PDF, PowerPoint, Word, text, spreadsheets, and similar files can be staged here for the next message.";
      list.innerHTML = attachments
        .map((item, index) => `
          <div class="attachment-chip">
            <div>
              <strong>${{escapeHtml(item.filename || "Attachment")}}</strong>
              <span>${{escapeHtml(item.content_type || "file")}} · ${{escapeHtml(formatAttachmentBytes(item.size_bytes || 0))}}</span>
            </div>
            <button type="button" class="ghost-toggle" data-remove-attachment="${{index}}">Remove</button>
          </div>
        `)
        .join("");
      list.querySelectorAll("[data-remove-attachment]").forEach((button) => {{
        button.addEventListener("click", () => {{
          const index = Number(button.getAttribute("data-remove-attachment") || "-1");
          if (index < 0) return;
          state.pendingAttachments = state.pendingAttachments.filter((_, itemIndex) => itemIndex !== index);
          renderAttachmentTray();
        }});
      }});
      if (attachButton) {{
        attachButton.disabled = !!state.uploadingAttachments;
      }}
    }}

    async function uploadChatFiles(fileList) {{
      const files = Array.from(fileList || []).filter(Boolean);
      if (!files.length) return;
      const actor = document.getElementById("actor")?.value || "Chris";
      const room = document.getElementById("room")?.value || "office";
      const formData = new FormData();
      formData.set("actor", actor);
      formData.set("room", room);
      formData.set("conversation_id", state.conversationId || "");
      files.slice(0, 8).forEach((file) => formData.append("files", file));
      state.uploadingAttachments = true;
      renderAttachmentTray();
      try {{
        const response = await fetch("/api/chat-uploads", {{
          method: "POST",
          body: formData,
        }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok) {{
          throw new Error(String(payload?.detail || "Attachment upload failed."));
        }}
        const uploaded = Array.isArray(payload.attachments) ? payload.attachments : [];
        state.pendingAttachments = [...state.pendingAttachments, ...uploaded];
        renderAttachmentTray();
      }} finally {{
        state.uploadingAttachments = false;
        renderAttachmentTray();
      }}
    }}

    function moveDesignReview(delta = 1) {{
      const pageId = currentReviewPageId();
      const targets = getReviewTargetsForPage(pageId);
      if (!targets.length || !isReviewEnabledForPage(pageId)) {{
        return;
      }}
      state.holoReview.active = true;
      state.holoReview.pageId = pageId;
      const total = targets.length;
      state.holoReview.index = (state.holoReview.index + delta + total) % total;
      syncDesignReviewPanel();
    }}

    function startDesignReview() {{
      const pageId = currentReviewPageId();
      const targets = getReviewTargetsForPage(pageId);
      if (!targets.length || !isReviewEnabledForPage(pageId)) {{
        return;
      }}
      state.holoReview.expanded = true;
      state.holoReview.active = true;
      state.holoReview.pageId = pageId;
      state.holoReview.index = 0;
      syncDesignReviewPanel();
    }}

    function applyDesignFeedback() {{
      const pageId = currentReviewPageId();
      const targets = getReviewTargetsForPage(pageId);
      if (!targets.length || !state.holoReview.active) {{
        return;
      }}
      const reviewState = currentReviewPageState(pageId);
      const current = targets[state.holoReview.index];
      const input = document.getElementById("design-review-input");
      const saved = document.getElementById("design-review-saved");
      const note = (input?.value || "").trim();
      if (!current || !saved) {{
        return;
      }}
      if (!note) {{
        saved.textContent = "Add a change note first.";
        return;
      }}
      reviewState.notes.set(current.id, note);
      const override = parseDesignFeedback(current.id, note);
      reviewState.overrides.set(current.id, override);
      if (override.remove) {{
        reviewState.removed.add(current.id);
      }} else {{
        reviewState.removed.delete(current.id);
      }}
      applyHoloReviewState();
      saved.textContent = `Saved feedback: ${{note}}`;
      document.getElementById("last-user-text").textContent = `Design feedback for ${{current.label}}: ${{note}}`;
      document.getElementById("last-jarvis-text").textContent = `Applied live for ${{current.label}}.`;
      const ambientSubtitle = document.getElementById("ambient-subtitle");
      if (ambientSubtitle) ambientSubtitle.textContent = `Live change applied to ${{current.label}}.`;
      syncTranscriptRail();
      persistDesignReviewState({{
        successMessage: `Saved feedback: ${{note}}`,
        failureMessage: "Live change applied, but the save did not reach the server yet.",
      }});
    }}

    function keepCurrentDesignElement() {{
      moveDesignReview(1);
    }}

    function removeCurrentDesignElement() {{
      const pageId = currentReviewPageId();
      const targets = getReviewTargetsForPage(pageId);
      if (!targets.length) {{
        return;
      }}
      const reviewState = currentReviewPageState(pageId);
      const current = targets[state.holoReview.index];
      if (current) {{
        reviewState.removed.add(current.id);
        reviewState.overrides.set(current.id, {{
          opacityScale: 0,
          speedScale: 1,
          scale: 1,
          density: 0,
          remove: true,
        }});
      }}
      applyHoloReviewState();
      persistDesignReviewState({{
        successMessage: current ? `${{current.label}} removed and saved.` : "Removal saved.",
        failureMessage: "Element removed locally, but the save did not reach the server yet.",
      }});
      moveDesignReview(1);
    }}

    function stopDesignReview() {{
      state.holoReview.active = false;
      state.holoReview.expanded = false;
      syncDesignReviewPanel();
    }}

    function toggleDesignReviewPanel(forceExpanded = null) {{
      if (typeof forceExpanded === "boolean") {{
        state.holoReview.expanded = forceExpanded;
      }} else {{
        state.holoReview.expanded = !state.holoReview.expanded;
      }}
      syncDesignReviewPanel();
    }}

    function renderList(items) {{
      if (!items || !items.length) {{
        return '<div class="empty">No packet data yet.</div>';
      }}
      return `<div class="line-list">${{items.map((item) => `<div class="line-item">${{item}}</div>`).join("")}}</div>`;
    }}

    function renderFirstLightSection(section) {{
      const details = Array.isArray(section?.details) ? section.details : [];
      const truth = section?.truth_state ? `<div class="muted" style="margin-bottom:8px; text-transform:uppercase; letter-spacing:0.12em;">${{escapeHtml(section.truth_state)}}</div>` : "";
      return packetBlock(
        section?.title || "Section",
        `
          ${{truth}}
          <p>${{escapeHtml(section?.summary || "")}}</p>
          ${{renderList(details.map((item) => `<div>${{escapeHtml(item)}}</div>`))}}
        `
      );
    }}

    const HOLO_REVIEW_STORAGE_KEY = "jarvis-holo-review-v2";
    const REVIEWABLE_PAGES = [
      ["shell", "Home Shell"],
      ["briefing", "Morning Brief"],
      ["brains", "Brains"],
      ["agents", "Agents"],
      ["home", "House"],
      ["family", "Family"],
      ["security", "Security"],
      ["chronicle", "Chronicle"],
      ["workshop", "Workshop"],
      ["catalyst", "Catalyst"],
      ["approvals", "Approvals"],
      ["settings", "Settings"],
    ];

    function currentReviewPageId() {{
      return state.packet || "shell";
    }}

    function ensureReviewPage(pageId = currentReviewPageId()) {{
      if (!state.holoReview.pages[pageId]) {{
        state.holoReview.pages[pageId] = {{
          removed: new Set(),
          notes: new Map(),
          overrides: new Map(),
        }};
      }}
      if (!state.holoReview.pageSettings[pageId]) {{
        state.holoReview.pageSettings[pageId] = {{ enabled: pageId === "shell" }};
      }}
      return state.holoReview.pages[pageId];
    }}

    function currentReviewPageState(pageId = currentReviewPageId()) {{
      return ensureReviewPage(pageId);
    }}

    function isReviewEnabledForPage(pageId = currentReviewPageId()) {{
      return !!ensureReviewPage(pageId) && !!state.holoReview.pageSettings[pageId]?.enabled;
    }}

    function serializeDesignReviewState() {{
      const pages = Object.fromEntries(
        Object.entries(state.holoReview.pages).map(([pageId, page]) => [
          pageId,
          {{
            removed: Array.from(page.removed || []),
            notes: Object.fromEntries((page.notes || new Map()).entries()),
            overrides: Object.fromEntries((page.overrides || new Map()).entries()),
          }},
        ])
      );
      return {{
        active_page: currentReviewPageId(),
        page_settings: state.holoReview.pageSettings,
        pages,
      }};
    }}

    function hydrateDesignReviewState(parsed) {{
      state.holoReview.activePage = parsed?.active_page || "shell";
      state.holoReview.pageSettings = parsed?.page_settings && typeof parsed.page_settings === "object"
        ? parsed.page_settings
        : {{ shell: {{ enabled: true }} }};
      const rawPages = parsed?.pages && typeof parsed.pages === "object"
        ? parsed.pages
        : {{
            shell: {{
              removed: Array.isArray(parsed?.removed) ? parsed.removed : [],
              notes: parsed?.notes && typeof parsed.notes === "object" ? parsed.notes : {{}},
              overrides: parsed?.overrides && typeof parsed.overrides === "object" ? parsed.overrides : {{}},
            }},
          }};
      state.holoReview.pages = Object.fromEntries(
        Object.entries(rawPages).map(([pageId, page]) => [
          pageId,
          {{
            removed: new Set(Array.isArray(page?.removed) ? page.removed : []),
            notes: new Map(Object.entries(page?.notes && typeof page.notes === "object" ? page.notes : {{}})),
            overrides: new Map(Object.entries(page?.overrides && typeof page.overrides === "object" ? page.overrides : {{}})),
          }},
        ])
      );
      ensureReviewPage("shell");
      REVIEWABLE_PAGES.forEach(([pageId]) => ensureReviewPage(pageId));
    }}

    function renderSelectOptions(options, selectedId, emptyLabel = "No options available") {{
      if (!options || !options.length) {{
        return `<option value="">${{escapeHtml(emptyLabel)}}</option>`;
      }}
      return options.map((item) => {{
        const detail = item.detail ? ` · ${{item.detail}}` : "";
        const selected = item.id === selectedId ? "selected" : "";
        return `<option value="${{escapeHtml(item.id)}}" ${{selected}}>${{escapeHtml(`${{item.label}}${{detail}}`)}}</option>`;
      }}).join("");
    }}

    function packetBlock(title, inner) {{
      return `<section class="packet-block"><h3>${{escapeHtml(title)}}</h3>${{inner}}</section>`;
    }}

    function financeReviewLauncherSummary(review = state.financeReview || {{}}) {{
      const weekly = review.weekly_review || {{}};
      const scorecard = review.scorecard || {{}};
      if (weekly.due) {{
        return {{
          count: "!",
          title: "Family finance review is due now.",
        }};
      }}
      if (scorecard.score !== undefined && scorecard.score !== null && String(scorecard.score).trim() !== "") {{
        return {{
          count: String(scorecard.score),
          title: String(review.summary || "Family finance review is ready.").trim() || "Family finance review is ready.",
        }};
      }}
      return {{
        count: "--",
        title: "Family finance review is standing by.",
      }};
    }}

    function updateFinanceReviewLauncher(review = state.financeReview || {{}}) {{
      const button = document.getElementById("finance-review-launcher");
      const icon = document.getElementById("finance-review-launcher-icon");
      const count = document.getElementById("finance-review-launcher-count");
      if (!button || !icon || !count) {{
        return;
      }}
      const summary = financeReviewLauncherSummary(review);
      count.textContent = summary.count;
      icon.textContent = review.weekly_review?.due ? "!" : "$";
      button.title = summary.title;
    }}

    function renderFinanceReviewMarkup(review = state.financeReview || {{}}) {{
      const sections = Array.isArray(review.sections) ? review.sections : [];
      const adjacentWealth = review.adjacent_wealth_lane || {{}};
      return `
        <div class="packet-grid">
          ${{
            packetBlock(
              "Family Finance",
              `
                <div class="metric"><strong>Summary</strong> ${{escapeHtml(review.summary || "Family finance review is standing by.")}}</div>
                <div class="metric"><strong>Boundary</strong> Household stewardship only · passive-income capital stays ring-fenced</div>
                <div class="metric"><strong>Next Move</strong> ${{escapeHtml(review.recommended_next_move || "Capture household cash, burn, and obligations.")}}</div>
              `
            )
          }}
          ${{
            sections.map((section) => packetBlock(
              section.title || "Section",
              `
                <p>${{escapeHtml(section.summary || "")}}</p>
                ${{renderList((section.details || []).map((item) => `<div>${{escapeHtml(item)}}</div>`))}}
              `
            )).join("")
          }}
          ${{
            packetBlock(
              "Separate Wealth Lane",
              `
                <div class="metric"><strong>Summary</strong> ${{escapeHtml(adjacentWealth.summary || "Wealth experiments remain separate from family operating cash.")}}</div>
                <div class="metric"><strong>Staged Wealth Items</strong> ${{escapeHtml(String(adjacentWealth.staged_items ?? 0))}}</div>
                <div class="metric"><strong>Recent Wealth Runs</strong> ${{escapeHtml(String(adjacentWealth.recent_runs ?? 0))}}</div>
                <div class="metric"><strong>Wealth Next Move</strong> ${{escapeHtml(adjacentWealth.next_move || "Open Wealth Review for Fisk's ring-fenced workstream.")}}</div>
                <div class="inline-actions" style="margin-top:10px;">
                  <button type="button" class="ghost-toggle finance-open-wealth">Open Wealth Review</button>
                </div>
              `
            )
          }}
        </div>
      `;
    }}

    async function refreshFinanceReview(options = {{}}) {{
      const force = Boolean(options.force);
      if (state.financeReview && !force) {{
        updateFinanceReviewLauncher(state.financeReview);
        return state.financeReview;
      }}
      const actor = preferredActorLabel();
      state.financeReview = await loadJSON(`/api/finance-review?actor=${{encodeURIComponent(actor)}}`);
      updateFinanceReviewLauncher(state.financeReview);
      return state.financeReview;
    }}

    function wealthLaneLabel(laneId = "") {{
      const normalized = String(laneId || "").trim().toLowerCase();
      if (normalized === "passive-income") return "Passive Income";
      if (normalized === "market-intelligence") return "Market Intelligence";
      return normalized ? normalized.replace(/-/g, " ").replace(/\\b\\w/g, (char) => char.toUpperCase()) : "Lane";
    }}

    function wealthCandidateTypeLabel(candidateType = "") {{
      return String(candidateType || "").trim().replace(/-/g, " ").replace(/\\b\\w/g, (char) => char.toUpperCase()) || "Candidate";
    }}

    function wealthTruthStateLabel(value = "") {{
      const normalized = String(value || "").trim();
      return normalized ? normalized.replace(/_/g, " ").replace(/-/g, " ").replace(/\\b\\w/g, (char) => char.toUpperCase()) : "Unknown";
    }}

    function wealthRunsSummary(laneId = "") {{
      return Array.isArray(state.wealthRunsByLane?.[laneId]) ? state.wealthRunsByLane[laneId] : [];
    }}

    function wealthPendingQueue(review = state.wealthReview || {{}}, laneId = "") {{
      const rows = Array.isArray(review.queue) ? review.queue : [];
      return rows.filter((item) => {{
        const status = String(item.status || "").trim().toLowerCase();
        if (status === "closed" || status === "approved" || status === "dismissed") return false;
        if (!laneId) return true;
        return String(item.lane_id || "") === String(laneId || "");
      }});
    }}

    function wealthArtifactsForItem(item = {{}}, review = state.wealthReview || {{}}) {{
      const itemArtifacts = Array.isArray(item.artifacts) ? item.artifacts : [];
      if (itemArtifacts.length) return itemArtifacts;
      const artifacts = Array.isArray(review.artifacts) ? review.artifacts : [];
      return artifacts.filter((artifact) => String(artifact.item_id || "") === String(item.item_id || ""));
    }}

    function wealthApprovalsForItem(item = {{}}, review = state.wealthReview || {{}}) {{
      const approvals = Array.isArray(review.approvals) ? review.approvals : [];
      return approvals.filter((approval) => String(approval.item_id || "") === String(item.item_id || ""));
    }}

    function wealthLaneItemCounts(items = []) {{
      const counts = {{}};
      items.forEach((item) => {{
        const key = String(item.status || "unknown").trim().toLowerCase() || "unknown";
        counts[key] = Number(counts[key] || 0) + 1;
      }});
      return counts;
    }}

    function wealthReviewerStatus(item = {{}}, reviewer = {{}}) {{
      const reviews = Array.isArray(item.guardrail_reviews) ? item.guardrail_reviews : [];
      const label = String(reviewer.label || "").trim().toLowerCase();
      const latest = reviews
        .filter((entry) => String(entry.reviewer || "").trim().toLowerCase() === label)
        .sort((left, right) => String(right.timestamp || "").localeCompare(String(left.timestamp || "")))[0];
      if (!latest) {{
        return {{
          label: "Pending",
          note: "No guardrail review recorded yet.",
        }};
      }}
      const status = String(latest.status || "").trim().toLowerCase();
      if (status === "approved") {{
        return {{ label: "Approved", note: String(latest.note || "").trim() || "Reviewer approved this item." }};
      }}
      if (status === "dismissed" || status === "rejected") {{
        return {{ label: "Dismissed", note: String(latest.note || "").trim() || "Reviewer dismissed this item." }};
      }}
      return {{
        label: "Reviewed",
        note: String(latest.note || "").trim() || "Reviewer left a progress note.",
      }};
    }}

    function wealthReviewerMatrix(item = {{}}) {{
      const reviewers = Array.isArray(item.required_reviewers) ? item.required_reviewers : [];
      if (!reviewers.length) {{
        return `<div class="empty">No guardrail reviewers are attached to this item yet.</div>`;
      }}
      return `
        <div class="stack">
          ${{
            reviewers.map((reviewer) => {{
              const status = wealthReviewerStatus(item, reviewer);
              return `
                <div class="metric">
                  <strong>${{escapeHtml(reviewer.label || "Reviewer")}}</strong> · ${{escapeHtml(status.label)}}
                  <br><span class="muted">${{escapeHtml(reviewer.role || "")}}</span>
                  <br><span class="muted">${{escapeHtml(status.note)}}</span>
                </div>
              `;
            }}).join("")
          }}
        </div>
      `;
    }}

    function wealthTruthBucketsMarkup(item = {{}}) {{
      const sections = [
        ["Observed", item.observed || []],
        ["Inferred", item.inferred || []],
        ["Prepared", item.prepared || []],
        ["Recommended", item.recommended || []],
        ["Requires Approval", item.requires_approval || []],
        ["Not Done", item.not_done || []],
      ];
      return sections.map(([label, values]) => packetBlock(
        label,
        Array.isArray(values) && values.length
          ? renderList(values.map((entry) => `<div>${{escapeHtml(entry)}}</div>`))
          : `<div class="empty">No ${{
              String(label).toLowerCase()
            }} entries recorded for this item.</div>`
      )).join("");
    }}

    function wealthSummaryText(review = state.wealthReview || {{}}) {{
      const runs = Array.isArray(review.recent_runs) ? review.recent_runs : [];
      const items = Array.isArray(review.items) ? review.items : [];
      const queue = wealthPendingQueue(review);
      const staged = queue.length || items.filter((item) => item.approval_required === true).length;
      const blockedRuns = Array.isArray(review.blocked_runs) ? review.blocked_runs : [];
      if (!runs.length && !items.length) {{
        return "Fisk has not staged any truthful wealth work yet. The lane is quiet until new reviewable records exist.";
      }}
      const mostRecentRun = runs[0] || null;
      if (mostRecentRun) {{
        const laneLabel = wealthLaneLabel(mostRecentRun.lane_id || "");
        const count = Number(mostRecentRun.items_staged || 0);
        const status = String(mostRecentRun.status || "").trim().toLowerCase();
        if (status === "skipped" || status === "failed" || String(mostRecentRun.blocked_reason || "").trim()) {{
          const why = String(mostRecentRun.blocked_reason || "blocked").trim().replace(/-/g, " ");
          return `Fisk most recently checked ${{laneLabel}}, but it did not run because ${{why}}. ${{staged ? `${{staged}} queue item(s) still need review.` : "No new execution was claimed."}}`;
        }}
        return `Fisk most recently ran ${{laneLabel}} and staged ${{count}} reviewable item(s). ${{staged ? `${{staged}} still need approval or guardrail review.` : "Nothing here claims execution beyond research and staging."}}`;
      }}
      return `Fisk is currently holding ${{items.length}} tracked wealth item(s), with ${{staged}} still requiring explicit review posture and ${{blockedRuns.length}} blocked or skipped run(s) recorded.`;
    }}

    function selectedWealthItem(review = state.wealthReview || {{}}) {{
      const items = Array.isArray(review.items) ? review.items : [];
      const selected = items.find((item) => String(item.item_id || "") === String(state.wealthSelectedItemId || ""));
      if (selected) {{
        return selected;
      }}
      const laneItems = items.filter((item) => String(item.lane_id || "") === String(state.wealthSelectedLane || ""));
      return laneItems[0] || items[0] || null;
    }}

    function wealthReportDetailMarkup(item = null) {{
      if (!item) {{
        return `<div class="empty">Select a staged Fisk item to inspect its structured report.</div>`;
      }}
      const artifacts = wealthArtifactsForItem(item);
      const approvals = wealthApprovalsForItem(item);
      const approval = approvals[0] || null;
      const opportunity = item.opportunity_report || null;
      const market = item.market_report || null;
      const reportSummary = opportunity
        ? `
            <div class="metric"><strong>Opportunity</strong> ${{escapeHtml(opportunity.opportunity || item.title || "Opportunity")}}</div>
            <div class="metric"><strong>Category</strong> ${{escapeHtml(opportunity.category || wealthCandidateTypeLabel(item.candidate_type || ""))}}</div>
            <div class="metric"><strong>Fisk Recommendation</strong> ${{escapeHtml(opportunity.fisk_recommendation || item.recommended_action || "Review")}}</div>
            <div class="metric"><strong>Approval Needed</strong> ${{opportunity.approval_needed ? "yes" : "no"}}</div>
            <p>${{escapeHtml(opportunity.summary || item.summary || "")}}</p>
            <div class="metric"><strong>Leverage Point</strong> ${{escapeHtml(opportunity.leverage_point || "Not yet bounded.")}}</div>
            <div class="metric"><strong>Where Money Flows</strong> ${{escapeHtml(opportunity.where_money_flows || "Not yet bounded.")}}</div>
            <div class="metric"><strong>Hidden Labor</strong> ${{escapeHtml(opportunity.risk?.hidden_labor || "Not recorded yet.")}}</div>
          `
        : market
          ? `
              <div class="metric"><strong>Ticker / Asset</strong> ${{escapeHtml(market.ticker_or_asset || item.title || "Asset")}}</div>
              <div class="metric"><strong>Time Horizon</strong> ${{escapeHtml(market.time_horizon || "Not set")}}</div>
              <div class="metric"><strong>Recommendation</strong> ${{escapeHtml(market.recommendation || item.recommended_action || "Review")}}</div>
              <div class="metric"><strong>Approval Required</strong> ${{market.approval_required ? "yes" : "no"}}</div>
              <p>${{escapeHtml(market.thesis || item.summary || "")}}</p>
              <div class="metric"><strong>Base Case</strong> ${{escapeHtml(market.prediction?.base_case || "Not recorded yet.")}}</div>
              <div class="metric"><strong>Bull / Bear</strong> ${{escapeHtml(market.prediction?.bull_case || "Not recorded")}} · ${{escapeHtml(market.prediction?.bear_case || "Not recorded")}}</div>
              <div class="metric"><strong>What Changes The View</strong> ${{escapeHtml(market.prediction?.what_would_change_the_view || "Not recorded yet.")}}</div>
            `
          : `<div class="metric"><strong>Summary</strong> ${{escapeHtml(item.summary || "No structured report is attached yet.")}}</div>`;
      return `
        <div class="packet-grid">
          ${{
            packetBlock(
              "Structured Report",
              `
                <div class="metric"><strong>Truth State</strong> ${{escapeHtml(wealthTruthStateLabel(item.truth_state || item.status || ""))}}</div>
                <div class="metric"><strong>Owner</strong> ${{escapeHtml(item.owner_agent || "Fisk")}}</div>
                <div class="metric"><strong>Lane</strong> ${{escapeHtml(wealthLaneLabel(item.lane_id || ""))}}</div>
                <div class="metric"><strong>Candidate Type</strong> ${{escapeHtml(wealthCandidateTypeLabel(item.candidate_type || ""))}}</div>
                ${{reportSummary}}
              `
            )
          }}
          ${{
            packetBlock(
              "Decision Controls",
              `
                <div class="metric"><strong>Approval Status</strong> ${{escapeHtml(item.approval_status || approval?.status || (item.approval_required ? "pending" : "not required"))}}</div>
                <div class="metric"><strong>Recommended Action</strong> ${{escapeHtml(item.recommended_action || item.next_action || "Review")}}</div>
                <div class="inline-actions" style="margin-top:10px; flex-wrap:wrap;">
                  <button type="button" class="ghost-toggle wealth-item-action" data-wealth-action="approve" data-wealth-item-id="${{escapeHtml(item.item_id || "")}}">Approve</button>
                  <button type="button" class="ghost-toggle wealth-item-action" data-wealth-action="dismiss" data-wealth-item-id="${{escapeHtml(item.item_id || "")}}">Dismiss</button>
                  <button type="button" class="ghost-toggle wealth-item-action" data-wealth-action="route" data-wealth-route="Nebula" data-wealth-item-id="${{escapeHtml(item.item_id || "")}}">Route Nebula</button>
                  <button type="button" class="ghost-toggle wealth-item-action" data-wealth-action="route" data-wealth-route="Pepper" data-wealth-item-id="${{escapeHtml(item.item_id || "")}}">Route Pepper</button>
                  <button type="button" class="ghost-toggle wealth-item-action" data-wealth-action="route" data-wealth-route="deeper-research" data-wealth-item-id="${{escapeHtml(item.item_id || "")}}">Deeper Research</button>
                </div>
              `
            )
          }}
          ${{
            packetBlock("Guardrail Reviewers", wealthReviewerMatrix(item))
          }}
          ${{
            packetBlock(
              "Kernel Records",
              `
                <div class="metric"><strong>Queue Entries</strong> ${{escapeHtml(String(Array.isArray(item.queue_entries) ? item.queue_entries.length : 0))}}</div>
                <div class="metric"><strong>Approvals</strong> ${{escapeHtml(String(approvals.length))}}</div>
                <div class="metric"><strong>Artifacts</strong> ${{escapeHtml(String(artifacts.length))}}</div>
                ${{artifacts.length ? renderList(artifacts.slice(0, 5).map((artifact) => `<div><strong>${{escapeHtml(artifact.artifact_type || "artifact")}}</strong><br>${{escapeHtml(artifact.summary || artifact.title || "")}}</div>`)) : `<div class="empty">No artifact records are attached yet.</div>`}}
              `
            )
          }}
          ${{
            wealthTruthBucketsMarkup(item)
          }}
        </div>
      `;
    }}

    function renderWealthReviewMarkup(review = state.wealthReview || {{}}) {{
      const lanes = Array.isArray(review.lanes) ? review.lanes : [];
      const items = Array.isArray(review.items) ? review.items : [];
      const queue = wealthPendingQueue(review);
      const blockedRuns = Array.isArray(review.blocked_runs) ? review.blocked_runs : [];
      const recentRuns = Array.isArray(review.recent_runs) ? review.recent_runs : [];
      const selectedItem = selectedWealthItem(review);
      const fisk = state.wealthAgent || {{}};
      const capital = review.capital_posture || {{}};
      const laneCards = lanes.filter((lane) => ["passive-income", "market-intelligence"].includes(String(lane.lane_id || "")));
      const laneMarkup = laneCards.map((lane) => {{
        const laneId = String(lane.lane_id || "");
        const laneItems = items.filter((item) => String(item.lane_id || "") === laneId);
        const laneQueue = wealthPendingQueue(review, laneId);
        const counts = wealthLaneItemCounts(laneItems);
        const runs = wealthRunsSummary(laneId);
        const recommended = laneQueue[0]?.recommended_action || laneItems.find((item) => String(item.recommended_action || "").trim())?.recommended_action || "Review";
        const active = laneId === String(state.wealthSelectedLane || "");
        const stagedCount = Number(counts.staged_for_approval || 0) + Number(counts.experiment_planned || 0) + Number(counts.buy_candidate || 0) + Number(counts.trim_candidate || 0) + Number(counts.exit_candidate || 0);
        return `
          <div class="packet-block">
            <h3>${{escapeHtml(wealthLaneLabel(laneId))}}</h3>
            <div class="metric"><strong>Mission</strong> ${{escapeHtml(lane.objective || lane.summary || "No mission loaded.")}}</div>
            <div class="metric"><strong>Cadence</strong> ${{escapeHtml(lane.cadence || "background + on demand")}}</div>
            <div class="metric"><strong>Tracked</strong> ${{escapeHtml(String(laneItems.length))}} · <strong>Staged</strong> ${{escapeHtml(String(stagedCount))}}</div>
            <div class="metric"><strong>Researching</strong> ${{escapeHtml(String(counts.researching || 0))}} · <strong>Runs</strong> ${{escapeHtml(String(runs.length))}}</div>
            <div class="metric"><strong>Queue</strong> ${{escapeHtml(String(laneQueue.length))}} · <strong>Last status</strong> ${{escapeHtml(wealthTruthStateLabel(runs[0]?.truth_state || runs[0]?.status || ""))}}</div>
            <div class="metric"><strong>Next Move</strong> ${{escapeHtml(recommended)}}</div>
            <div class="inline-actions" style="margin-top:10px;">
              <button type="button" class="${{active ? "ghost-toggle" : ""}} wealth-lane-select" data-wealth-lane="${{escapeHtml(laneId)}}">${{active ? "Viewing" : "Open Lane"}}</button>
            </div>
          </div>
        `;
      }}).join("");
      const queueMarkup = queue.length
        ? renderList(queue.map((entry) => `
            <div>
              <strong>${{escapeHtml(entry.title || "Queue item")}}</strong>
              <br>${{escapeHtml(wealthLaneLabel(entry.lane_id || ""))}} · ${{escapeHtml(entry.queue_type || "review")}} · ${{escapeHtml(entry.approval_status || "pending")}}
              <br><span class="muted">${{escapeHtml(entry.summary || "")}}</span>
              <div class="inline-actions" style="margin-top:10px; flex-wrap:wrap;">
                <button type="button" class="ghost-toggle wealth-item-select" data-wealth-item-id="${{escapeHtml(entry.item_id || "")}}" data-wealth-item-lane="${{escapeHtml(entry.lane_id || "")}}">Inspect</button>
                <button type="button" class="ghost-toggle wealth-item-action" data-wealth-action="approve" data-wealth-item-id="${{escapeHtml(entry.item_id || "")}}">Approve</button>
                <button type="button" class="ghost-toggle wealth-item-action" data-wealth-action="dismiss" data-wealth-item-id="${{escapeHtml(entry.item_id || "")}}">Dismiss</button>
                <button type="button" class="ghost-toggle wealth-item-action" data-wealth-action="route" data-wealth-route="Nebula" data-wealth-item-id="${{escapeHtml(entry.item_id || "")}}">Route Nebula</button>
                <button type="button" class="ghost-toggle wealth-item-action" data-wealth-action="route" data-wealth-route="deeper-research" data-wealth-item-id="${{escapeHtml(entry.item_id || "")}}">Deeper Research</button>
              </div>
            </div>
          `))
        : `<div class="empty">No pending wealth decisions are waiting right now.</div>`;
      const runLedgerMarkup = recentRuns.length
        ? renderList(recentRuns.slice(0, 8).map((run) => `
            <div>
              <strong>${{escapeHtml(wealthLaneLabel(run.lane_id || ""))}}</strong> · ${{escapeHtml(wealthTruthStateLabel(run.status || run.truth_state || ""))}}
              <br><span class="muted">${{escapeHtml(run.summary || "")}}</span>
              <br><span class="muted">Outcome: ${{escapeHtml(wealthTruthStateLabel(run.truth_state || run.action_status || ""))}} · Verification: ${{escapeHtml(wealthTruthStateLabel(run.verification_status || ""))}}</span>
              ${{run.blocked_reason ? `<br><span class="muted">Blocked: ${{escapeHtml(String(run.blocked_reason || "").replace(/-/g, " "))}}</span>` : ""}}
            </div>
          `))
        : `<div class="empty">No workstream runs are recorded yet.</div>`;
      const laneItems = items.filter((item) => {{
        const selectedLane = String(state.wealthSelectedLane || "");
        return !selectedLane || String(item.lane_id || "") === selectedLane;
      }});
      const stagedMarkup = laneItems.length
        ? renderList(laneItems.map((item) => {{
            const selected = String(item.item_id || "") === String(selectedItem?.item_id || "");
            const reviewState = Array.isArray(item.required_reviewers) && item.required_reviewers.length
              ? item.required_reviewers.map((reviewer) => `${{reviewer.label}}: ${{wealthReviewerStatus(item, reviewer).label}}`).join(" · ")
              : "No guardrail reviewers attached yet.";
            return `
              <div>
                <strong>${{escapeHtml(item.title || "Wealth item")}}</strong>
                <br>${{escapeHtml(wealthLaneLabel(item.lane_id || ""))}} · ${{escapeHtml(wealthTruthStateLabel(item.truth_state || item.status || ""))}} · ${{escapeHtml(item.owner_agent || "Fisk")}}
                <br><span class="muted">${{escapeHtml(item.summary || "")}}</span>
                <br><span class="muted">Recommendation: ${{escapeHtml(item.recommended_action || "Review")}} · Approval: ${{item.approval_required ? "required" : "not required"}}</span>
                <br><span class="muted">${{escapeHtml(reviewState)}}</span>
                <div class="inline-actions" style="margin-top:10px;">
                  <button type="button" class="${{selected ? "ghost-toggle" : ""}} wealth-item-select" data-wealth-item-id="${{escapeHtml(item.item_id || "")}}" data-wealth-item-lane="${{escapeHtml(item.lane_id || "")}}">${{selected ? "Inspecting" : "Inspect Report"}}</button>
                  ${{item.work_id ? `<button type="button" class="work-item-action-button" data-work-action="inspect" data-work-id="${{escapeHtml(item.work_id)}}" data-variant="quiet">Open Lifecycle</button>` : ""}}
                </div>
              </div>
            `;
          }}))
        : `<div class="empty">No staged work exists for this lane yet.</div>`;
      return `
        <div class="packet-grid">
          ${{
            packetBlock(
              "Fisk",
              `
                <div class="metric"><strong>${{escapeHtml(fisk.name || fisk.label || "Fisk")}}</strong> · ${{escapeHtml(fisk.title || "Market Power & Capital Growth Agent")}}</div>
                <p>${{escapeHtml(review.doctrine || "Find leverage. Quantify risk. Reject fantasy. Route the opportunity.")}}</p>
                <p>${{escapeHtml(wealthSummaryText(review))}}</p>
                <div class="metric"><strong>Boundary</strong> ${{escapeHtml(review.family_boundary || "Wealth experimentation is ring-fenced from family operating cash.")}}</div>
                <div class="metric"><strong>Review posture</strong> research and staged recommendations only · no money movement · no live trading</div>
                <div class="metric"><strong>Blocked / skipped runs</strong> ${{escapeHtml(String(blockedRuns.length))}} · <strong>Pending queue</strong> ${{escapeHtml(String(queue.length))}}</div>
              `
            )
          }}
          ${{
            packetBlock(
              "Wealth Capital Posture",
              `
                <div class="metric"><strong>Available</strong> ${{escapeHtml(String(capital.wealth_account_available ?? "unknown"))}}</div>
                <div class="metric"><strong>Reserved</strong> ${{escapeHtml(String(capital.wealth_account_reserved ?? "unknown"))}}</div>
                <div class="metric"><strong>Transfer Policy</strong> ${{escapeHtml(capital.transfer_policy_note || "Passive-income capital stays separate until an explicit transfer workflow exists.")}}</div>
                ${{Array.isArray(capital.wealth_account_notes) && capital.wealth_account_notes.length ? renderList(capital.wealth_account_notes.map((item) => `<div>${{escapeHtml(item)}}</div>`)) : `<div class="empty">No wealth-account notes are recorded yet.</div>`}}
              `
            )
          }}
          ${{
            packetBlock(
              "Lane Summary",
              laneMarkup || `<div class="empty">No wealth lanes are available yet.</div>`
            )
          }}
          ${{
            packetBlock(
              "Decision Queue",
              queueMarkup
            )
          }}
          ${{
            packetBlock(
              "Staged Work",
              stagedMarkup
            )
          }}
          ${{
            packetBlock(
              "Run Ledger",
              runLedgerMarkup
            )
          }}
          ${{
            packetBlock(
              "Report Detail",
              wealthReportDetailMarkup(selectedItem)
            )
          }}
        </div>
      `;
    }}

    async function refreshWealthReview(options = {{}}) {{
      const force = Boolean(options.force);
      if (state.wealthReview && !force) {{
        updateWealthLauncher(state.wealthReview);
        return state.wealthReview;
      }}
      const actor = preferredActorLabel();
      const [wealthReview, workstreams] = await Promise.all([
        loadJSON(`/api/wealth-review?actor=${{encodeURIComponent(actor)}}`),
        loadJSON(`/api/workstreams?actor=${{encodeURIComponent(actor)}}`),
      ]);
      state.wealthReview = {{
        ...wealthReview,
        lanes: Array.isArray(workstreams?.lanes) ? workstreams.lanes.filter((lane) => ["passive-income", "market-intelligence"].includes(String(lane.lane_id || ""))) : [],
        items: Array.isArray(workstreams?.items) ? workstreams.items.filter((item) => ["passive-income", "market-intelligence"].includes(String(item.lane_id || ""))) : [],
        recent_runs: Array.isArray(workstreams?.recent_runs) ? workstreams.recent_runs.filter((item) => ["passive-income", "market-intelligence"].includes(String(item.lane_id || ""))) : [],
        queue: Array.isArray(workstreams?.queue) ? workstreams.queue.filter((item) => ["passive-income", "market-intelligence"].includes(String(item.lane_id || ""))) : [],
        approvals: Array.isArray(workstreams?.approvals) ? workstreams.approvals.filter((item) => ["passive-income", "market-intelligence"].includes(String(item.lane_id || ""))) : [],
        artifacts: Array.isArray(workstreams?.artifacts) ? workstreams.artifacts.filter((item) => ["passive-income", "market-intelligence"].includes(String(item.lane_id || ""))) : [],
        lane_readiness: Array.isArray(workstreams?.lane_readiness) ? workstreams.lane_readiness.filter((item) => ["passive-income", "market-intelligence"].includes(String(item.lane_id || ""))) : [],
        blocked_runs: Array.isArray(wealthReview?.blocked_runs)
          ? wealthReview.blocked_runs
          : (Array.isArray(workstreams?.recent_runs) ? workstreams.recent_runs.filter((item) => ["skipped", "failed"].includes(String(item.status || "").trim().toLowerCase()) || String(item.blocked_reason || "").trim()) : []),
        status_counts: workstreams?.status_counts || wealthReview?.status_counts || {{}},
        summary: {{
          ...(wealthReview?.summary || {{}}),
          ...(workstreams?.summary || {{}}),
        }},
      }};
      state.wealthRunsByLane = {{
        "passive-income": Array.isArray(state.wealthReview?.recent_runs)
          ? state.wealthReview.recent_runs.filter((item) => String(item.lane_id || "") === "passive-income")
          : [],
        "market-intelligence": Array.isArray(state.wealthReview?.recent_runs)
          ? state.wealthReview.recent_runs.filter((item) => String(item.lane_id || "") === "market-intelligence")
          : [],
      }};
      state.wealthAgent = state.wealthReview?.agent || null;
      state.wealthReview.summary_text = wealthSummaryText(state.wealthReview);
      const items = Array.isArray(state.wealthReview.items) ? state.wealthReview.items : [];
      if (!items.find((item) => String(item.item_id || "") === String(state.wealthSelectedItemId || ""))) {{
        const preferred = items.find((item) => String(item.lane_id || "") === String(state.wealthSelectedLane || "")) || items[0] || null;
        state.wealthSelectedItemId = String(preferred?.item_id || "");
        state.wealthSelectedLane = String(preferred?.lane_id || state.wealthSelectedLane || "passive-income");
      }}
      updateWealthLauncher(state.wealthReview);
      return state.wealthReview;
    }}

    async function runWealthItemAction(action = "", itemId = "", routeTo = "") {{
      const actor = preferredActorLabel();
      const normalizedAction = String(action || "").trim().toLowerCase();
      const normalizedItemId = String(itemId || "").trim();
      if (!normalizedAction || !normalizedItemId) {{
        return null;
      }}
      let url = "";
      let payload = {{ actor }};
      if (normalizedAction === "approve") {{
        url = `/api/workstreams/items/${{encodeURIComponent(normalizedItemId)}}/approve`;
        payload.note = "Approved from Wealth Review.";
      }} else if (normalizedAction === "dismiss") {{
        url = `/api/workstreams/items/${{encodeURIComponent(normalizedItemId)}}/dismiss`;
        payload.note = "Dismissed from Wealth Review.";
      }} else if (normalizedAction === "route") {{
        url = `/api/workstreams/items/${{encodeURIComponent(normalizedItemId)}}/route`;
        payload.route_to = String(routeTo || "").trim() || "deeper-research";
        payload.note = payload.route_to === "deeper-research"
          ? "Requested deeper research from Wealth Review."
          : `Routed to ${{payload.route_to}} from Wealth Review.`;
      }} else {{
        return null;
      }}
      await loadJSON(url, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload),
      }});
      await refreshWealthReview({{ force: true }});
      openPacket("wealth");
      return true;
    }}

    function renderAssistantInboxItems(items, emptyLabel = "No unread assistant nudges are waiting right now.") {{
      const rows = Array.isArray(items) ? items : [];
      if (!rows.length) {{
        return `<p>${{escapeHtml(emptyLabel)}}</p>`;
      }}
      return renderList(rows.map((item) => `
        <div>
          <strong>${{escapeHtml(item.title || "Assistant item")}}</strong>
          <br>${{escapeHtml(item.detail || "")}}
          <br><span class="muted">Priority: ${{escapeHtml(item.priority_class || "normal")}} · State: ${{escapeHtml(item.status || "opened")}}</span>
          <br><span class="muted">Why this surfaced: ${{escapeHtml(item.why_this_surfaced || item.delivery_policy_summary || "JARVIS judged that this deserved attention.")}}</span>
          <div class="inline-actions" style="margin-top:8px;">
            ${{item.packet ? `<button type="button" class="ghost-toggle assistant-inbox-open" data-notification-id="${{escapeHtml(item.notification_id || "")}}" data-packet="${{escapeHtml(item.packet || "today")}}">Open</button>` : ""}}
            <button type="button" class="ghost-toggle assistant-inbox-ignore" data-notification-id="${{escapeHtml(item.notification_id || "")}}">Ignore</button>
          </div>
        </div>
      `));
    }}

    async function refreshVoiceSettings() {{
      const [settings, options, accounts, identity, locations] = await Promise.all([
        loadJSON("/api/voice-settings"),
        loadJSON("/api/voice-options"),
        loadJSON("/api/accounts"),
        loadJSON("/api/identity"),
        loadJSON("/api/location-settings")
      ]);
      state.voiceSettings = settings;
      state.voiceOptions = options;
      state.accountRegistry = accounts;
      state.identity = identity;
      state.locationSettings = locations;
    }}

    function openSettings() {{
      state.manualPacketIntentUntil = Date.now() + 5000;
      refreshVoiceSettings()
        .then(() => openPacket("settings", {{ bypassScene: true }}))
        .catch((error) => {{
          document.getElementById("last-jarvis-text").textContent = error.message;
          setVoiceState("idle", "Settings are unavailable right now.");
        }});
    }}

    function wireLayoutSettingsForm() {{
      const toggle = document.getElementById("layout-edit-mode");
      const saveButton = document.getElementById("save-layout-settings");
      const resetButton = document.getElementById("reset-layout-placements");
      const status = document.getElementById("layout-settings-status");
      if (!toggle || !saveButton || !resetButton || !status) return;
      saveButton.addEventListener("click", () => {{
        saveLayoutEditMode(!!toggle.checked);
        status.textContent = toggle.checked
          ? "Layout freedom is on. Drag or resize the visible shell panels and open modals. Saved layouts will return when the window is large enough."
          : "Layout freedom is off. Saved layouts are preserved and will still reappear on larger windows until you reset them.";
      }});
      resetButton.addEventListener("click", () => {{
        resetLayoutPlacements();
        status.textContent = "Saved chat and modal positions were reset.";
      }});
    }}

    function detectShellClientProfile() {{
      const ua = navigator.userAgent || "";
      const lowered = ua.toLowerCase();
      let osName = "Unknown";
      if (lowered.includes("iphone") || lowered.includes("ipad") || lowered.includes("cpu iphone os") || lowered.includes("cpu os")) {{
        osName = "iOS";
      }} else if (lowered.includes("android")) {{
        osName = "Android";
      }} else if (lowered.includes("macintosh") || lowered.includes("mac os x")) {{
        osName = "macOS";
      }} else if (lowered.includes("windows nt")) {{
        osName = "Windows";
      }} else if (lowered.includes("linux")) {{
        osName = "Linux";
      }}

      let browserName = "Unknown browser";
      if (lowered.includes("edg/")) {{
        browserName = "Microsoft Edge";
      }} else if (lowered.includes("opr/") || lowered.includes("opera")) {{
        browserName = "Opera";
      }} else if (lowered.includes("fxios") || lowered.includes("firefox")) {{
        browserName = "Firefox";
      }} else if (lowered.includes("crios") || lowered.includes("chrome/")) {{
        browserName = "Chrome";
      }} else if (lowered.includes("safari/") && !lowered.includes("chrome/") && !lowered.includes("crios")) {{
        browserName = "Safari";
      }}

      let deviceType = "browser";
      let hardwareLabel = "Browser";
      if (lowered.includes("iphone")) {{
        deviceType = "phone";
        hardwareLabel = "iPhone";
      }} else if (lowered.includes("ipad")) {{
        deviceType = "tablet";
        hardwareLabel = "iPad";
      }} else if (lowered.includes("android") && lowered.includes("mobile")) {{
        deviceType = "phone";
        hardwareLabel = "Android phone";
      }} else if (lowered.includes("android")) {{
        deviceType = "tablet";
        hardwareLabel = "Android tablet";
      }} else if (lowered.includes("macintosh") || lowered.includes("mac os x")) {{
        deviceType = "desktop";
        hardwareLabel = "Mac";
      }} else if (lowered.includes("windows nt")) {{
        deviceType = "desktop";
        hardwareLabel = "Windows PC";
      }} else if (lowered.includes("linux")) {{
        deviceType = "desktop";
        hardwareLabel = "Linux device";
      }}

      return {{
        os_name: osName,
        browser_name: browserName,
        device_type: deviceType,
        hardware_label: hardwareLabel,
      }};
    }}

    function getShellDeviceIdentity() {{
      let deviceId = "";
      try {{
        deviceId = window.localStorage.getItem(SHELL_DEVICE_ID_KEY) || "";
        if (!deviceId) {{
          deviceId = (window.crypto?.randomUUID?.() || `jarvis-device-${{Date.now()}}-${{Math.random().toString(16).slice(2)}}`);
          window.localStorage.setItem(SHELL_DEVICE_ID_KEY, deviceId);
        }}
      }} catch (error) {{
        deviceId = `jarvis-device-${{Date.now()}}`;
      }}
      state.shellDeviceId = deviceId;
      const clientProfile = detectShellClientProfile();
      const label = `${{clientProfile.hardware_label}} browser`;
      const fingerprint = [navigator.userAgent || "", navigator.language || "", String(window.screen?.width || 0), String(window.screen?.height || 0)].join("|");
      return {{
        device_id: deviceId,
        label,
        device_type: clientProfile.device_type || "browser",
        room: document.getElementById("room")?.value || "office",
        user_agent: navigator.userAgent || "",
        fingerprint,
        last_host: window.location.host || "",
        last_origin: window.location.origin || "",
      }};
    }}

    function applyResolvedActor(actorId) {{
      if (!actorId) return;
      const actor = document.getElementById("actor");
      const modeActor = document.getElementById("mode-actor");
      if (actor && Array.from(actor.options).some((option) => option.value === actorId)) {{
        actor.value = actorId;
      }}
      if (modeActor && Array.from(modeActor.options).some((option) => option.value === actorId)) {{
        modeActor.value = actorId;
      }}
      syncContextPanelCopy();
    }}

    function loadSessionActorOverride() {{
      try {{
        return window.localStorage.getItem(SESSION_ACTOR_OVERRIDE_KEY) || "";
      }} catch (_error) {{
        return "";
      }}
    }}

    function saveSessionActorOverride(actorId) {{
      state.sessionActorOverride = actorId || "";
      try {{
        if (actorId) {{
          window.localStorage.setItem(SESSION_ACTOR_OVERRIDE_KEY, actorId);
        }} else {{
          window.localStorage.removeItem(SESSION_ACTOR_OVERRIDE_KEY);
        }}
      }} catch (_error) {{
        // noop
      }}
    }}

    async function bindShellIdentity() {{
      const payload = getShellDeviceIdentity();
      payload.session_actor_id = state.sessionActorOverride || loadSessionActorOverride() || "";
      const data = await loadJSON("/api/identity/session", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload),
      }});
      state.identity = data.identity || state.identity;
      state.sessionIdentity = data;
      if (data.resolved_actor_id) {{
        applyResolvedActor(data.resolved_actor_id || "");
        if (data.actor_source === "session-override") {{
          saveSessionActorOverride(data.resolved_actor_id || "");
        }}
      }}
      await refreshCurrentDeviceProfile().catch(() => null);
      return data;
    }}

    function applyCurrentDeviceRouting(data = null) {{
      const normalized = data?.normalized_device || {{}};
      const profile = data?.device_profile || {{}};
      const route = data?.interface_route || {{}};
      const binding = data?.user_profile_binding || {{}};
      const mobileVariant = data?.mobile_remote_variant || {{}};
      const setValue = (key, value, fallback = "unknown") => {{
        document.body.dataset[key] = String(value || fallback)
          .trim()
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, "-")
          .replace(/^-+|-+$/g, "") || fallback;
      }};
      setValue("deviceProfile", profile.device_profile_id, "general-browser-session");
      setValue("interfaceRoute", route.route_id, "standard-chamber");
      setValue("interfaceType", normalized.interface_type, "device");
      setValue("accessMethod", normalized.access_method, "unknown");
      setValue("boundProfile", binding.user_id || binding.source, "unassigned");
      setValue("mobileVariant", mobileVariant.variant_id, "standard");
    }}

    async function refreshCurrentDeviceProfile() {{
      if (!state.shellDeviceId) {{
        state.currentDevice = null;
        applyCurrentDeviceRouting(null);
        return null;
      }}
      const data = await loadJSON(`/api/current-device?device_id=${{encodeURIComponent(state.shellDeviceId || "")}}`);
      state.currentDevice = data;
      applyCurrentDeviceRouting(data);
      return data;
    }}

    function preferredActorLabel() {{
      return (
        state.sessionIdentity?.resolved_actor_label ||
        document.getElementById("actor")?.value ||
        "Chris"
      );
    }}

    function catalystRouteForPage(page = "home") {{
      const map = {{
        home: "/home",
        calendar: "/calendar",
        meetings: "/meetings",
        projects: "/projects",
        tasks: "/tasks",
        email: "/email",
        contacts: "/contacts",
        reports: "/reports",
        settings: "/settings",
      }};
      return map[page] || "/home";
    }}

    function catalystCapabilityForPage(page = "home") {{
      if (page === "meetings" || page === "calendar") return "meeting_prep";
      if (page === "reports" || page === "projects") return "decision_support";
      return "signal_triage";
    }}

    function catalystSummaryForPage(page = "home") {{
      if (page === "calendar") return "Sent to Catalyst for live calendar review.";
      if (page === "meetings") return "Sent to Catalyst for meeting prep and follow-through.";
      if (page === "projects") return "Sent to Catalyst for project execution and portfolio review.";
      if (page === "tasks") return "Sent to Catalyst for task execution.";
      if (page === "email") return "Sent to Catalyst for live email triage.";
      if (page === "contacts") return "Sent to Catalyst for stakeholder context.";
      if (page === "reports") return "Sent to Catalyst for reporting and decision support.";
      if (page === "settings") return "Sent to Catalyst settings.";
      return "Sent to Catalyst to continue the operational thread.";
    }}

    function catalystPacketContext() {{
      const live = state.dashboard?.catalyst_overview?.live_workspace || {{}};
      return {{
        calendar_count: Number(live.calendar?.items?.length || 0),
        email_count: Number(live.email?.items?.length || 0),
        open_task_count: Number(live.tasks?.stats?.openCount || 0),
        page: state.catalystPage || "home",
        project_count: Number(live.projects?.items?.length || 0),
      }};
    }}

    async function createCatalystLaunchSpec() {{
      const context = catalystPacketContext();
      const page = context.page || "home";
      const capability = catalystCapabilityForPage(page);
      let requestId = "";
      try {{
        const payload = await loadJSON(`${{CATALYST_API_BASE_URL}}/api/catalyst/handoff`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            actor: {{
              actor_id: preferredActorLabel(),
              role: "primary_user",
            }},
            capability,
            context,
            intent_family: capability === "meeting_prep" ? "day.calendar" : capability === "decision_support" ? "exec.decision" : "day.review",
            mode: "embed",
            source_system: "jarvis",
          }}),
        }});
        requestId = String(payload?.request_id || "");
      }} catch (error) {{
        console.warn("Catalyst handoff session unavailable", error);
      }}
      const params = new URLSearchParams();
      params.set("jarvis", "1");
      params.set("jarvisCapability", capability);
      params.set("jarvisSummary", catalystSummaryForPage(page));
      params.set("jarvisReturnUrl", window.location.origin);
      params.set("jarvisReturnPacket", "catalyst");
      if (requestId) {{
        params.set("jarvisRequestId", requestId);
      }}
      return {{
        capability,
        context,
        requestId,
        summary: catalystSummaryForPage(page),
        url: `${{CATALYST_APP_BASE_URL}}${{catalystRouteForPage(page)}}?${{params.toString()}}`,
      }};
    }}

    async function wireCatalystWorkspace() {{
      const frame = document.getElementById("catalyst-workspace-frame");
      const summary = document.getElementById("catalyst-handoff-summary");
      const sendButton = document.getElementById("catalyst-send-button");
      const openButton = document.getElementById("catalyst-open-app");
      if (!frame || !summary || !sendButton || !openButton) {{
        return;
      }}

      const applySpec = async (launchExternal = false) => {{
        summary.textContent = "Preparing Catalyst…";
        const spec = await createCatalystLaunchSpec();
        summary.textContent = spec.summary;
        frame.src = spec.url;
        sendButton.textContent = "Sent to Catalyst";
        if (launchExternal) {{
          window.open(spec.url, "_blank", "noopener,noreferrer");
        }}
      }};

      sendButton.addEventListener("click", () => {{
        applySpec(false).catch((error) => {{
          summary.textContent = error?.message || "Catalyst handoff failed.";
        }});
      }});

      openButton.addEventListener("click", () => {{
        applySpec(true).catch((error) => {{
          summary.textContent = error?.message || "Catalyst launch failed.";
        }});
      }});

      await applySpec(false);
    }}

    function wireVoiceSettingsForm() {{
      const saveButton = document.getElementById("save-voice-settings");
      const previewButton = document.getElementById("preview-voice-settings");
      if (!saveButton || !previewButton) {{
        return;
      }}

      async function submit(preview = false) {{
        const payload = {{
          tts_provider: document.getElementById("settings-tts-provider").value,
          elevenlabs_voice: document.getElementById("settings-elevenlabs-voice").value,
          piper_model_path: document.getElementById("settings-piper-model").value,
          piper_speaker: document.getElementById("settings-piper-speaker").value,
        }};
        const data = await loadJSON("/api/voice-settings", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload),
        }});
        state.voiceSettings = data.settings;
        state.voiceOptions = data.options;
        state.settingsMessage = `Saved. Configured voice source: ${{data.settings.selected_provider_label}}.`;
        openPacket("settings");
        document.getElementById("last-jarvis-text").textContent = "Voice settings updated.";
        syncTranscriptRail();
        if (preview) {{
          const target = document.getElementById("voice-settings-status");
          if (target) {{
            target.textContent = "Configured voice source saved. Running preview through the current voice route…";
          }}
          const previewText = document.getElementById("settings-preview-text")?.value?.trim() || "Good evening, sir. Voice calibration complete.";
          await speakText(previewText, {{
            onResult: (result) => {{
              const liveTarget = document.getElementById("voice-settings-status");
              if (liveTarget) {{
                liveTarget.textContent = result?.message || "Preview route completed.";
              }}
            }},
            onError: (detail) => {{
              const liveTarget = document.getElementById("voice-settings-status");
              if (liveTarget) {{
                liveTarget.textContent = `Preview failed: ${{detail}}`;
              }}
            }},
          }});
        }}
      }}

      saveButton.addEventListener("click", () => {{
        submit(false).catch((error) => {{
          const target = document.getElementById("voice-settings-status");
          if (target) {{
            target.textContent = error.message;
          }}
        }});
      }});

      previewButton.addEventListener("click", () => {{
        submit(true).catch((error) => {{
          const target = document.getElementById("voice-settings-status");
          if (target) {{
            target.textContent = error.message;
          }}
        }});
      }});
    }}

    function wirePageReviewSettingsForm() {{
      const status = document.getElementById("page-review-status");
      document.querySelectorAll(".page-review-toggle").forEach((button) => {{
        button.addEventListener("click", async () => {{
          const pageId = button.dataset.reviewPage || "";
          if (!pageId) return;
          ensureReviewPage(pageId);
          const nextEnabled = !(state.holoReview.pageSettings?.[pageId]?.enabled);
          state.holoReview.pageSettings[pageId] = {{ enabled: nextEnabled }};
          if (pageId === currentReviewPageId() && !nextEnabled) {{
            state.holoReview.active = false;
          }}
          const ok = await persistDesignReviewState({{
            successMessage: `${{REVIEWABLE_PAGES.find(([id]) => id === pageId)?.[1] || pageId}} review ${{nextEnabled ? "enabled" : "disabled"}}.`,
            failureMessage: "The page review toggle did not save cleanly.",
          }});
          if (status) {{
            status.textContent = ok
              ? `${{REVIEWABLE_PAGES.find(([id]) => id === pageId)?.[1] || pageId}} review is now ${{nextEnabled ? "enabled" : "disabled"}}.`
              : "The page review toggle changed locally, but did not save cleanly.";
          }}
          syncDesignReviewPanel();
          openPacket("settings");
        }});
      }});
    }}

    function wireLocationSettingsForm() {{
      const status = document.getElementById("location-settings-status");
      const save = document.getElementById("save-location");
      if (save) {{
        save.addEventListener("click", async () => {{
          try {{
            const payload = {{
              action: "add_location",
              label: document.getElementById("location-label")?.value || "",
              geography: document.getElementById("location-geography")?.value || "",
              latitude: document.getElementById("location-latitude")?.value || "",
              longitude: document.getElementById("location-longitude")?.value || "",
              notes: document.getElementById("location-notes")?.value || "",
              make_preferred: true,
            }};
            const data = await loadJSON("/api/location-settings", {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify(payload),
            }});
            state.locationSettings = data.state;
            if (status) status.textContent = "Location saved.";
            await refreshDashboard();
            openPacket("settings");
          }} catch (error) {{
            if (status) status.textContent = error.message || "Location save failed.";
          }}
        }});
      }}

      document.querySelectorAll(".location-use").forEach((button) => {{
        button.addEventListener("click", async () => {{
          try {{
            const data = await loadJSON("/api/location-settings", {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify({{ action: "set_preferred", location_id: button.dataset.locationId || "" }}),
            }});
            state.locationSettings = data.state;
            if (status) status.textContent = "Active location updated.";
            await refreshDashboard();
            openPacket("settings");
          }} catch (error) {{
            if (status) status.textContent = error.message || "Location update failed.";
          }}
        }});
      }});

      const device = document.getElementById("use-device-location");
      if (device) {{
        device.addEventListener("click", async () => {{
          if (!navigator.geolocation) {{
            if (status) status.textContent = "This browser does not expose location services.";
            return;
          }}
          if (status) status.textContent = "Requesting current location…";
          navigator.geolocation.getCurrentPosition(async (position) => {{
            try {{
              const data = await loadJSON("/api/location-settings", {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{
                  action: "save_device_location",
                  label: "Current Device Location",
                  geography: `Lat ${{position.coords.latitude.toFixed(4)}}, Lon ${{position.coords.longitude.toFixed(4)}}`,
                  latitude: position.coords.latitude,
                  longitude: position.coords.longitude,
                  timestamp: new Date().toISOString(),
                  save_as_location: true,
                  make_preferred: true,
                }}),
              }});
              state.locationSettings = data.state;
              if (status) status.textContent = "Current location captured.";
              await refreshDashboard();
              openPacket("settings");
            }} catch (error) {{
              if (status) status.textContent = error.message || "Device location save failed.";
            }}
          }}, (error) => {{
            if (status) status.textContent = error.message || "Location permission was denied.";
          }}, {{ enableHighAccuracy: true, timeout: 10000 }});
        }});
      }}
    }}

    function openPacket(packetId, options = {{}}) {{
      const routedSceneId = !options.bypassScene ? sceneIdForPacket(packetId) : "";
      if (routedSceneId) {{
        openScene(routedSceneId);
        return;
      }}
      if (packetId !== "vision") {{
        stopVisionPreview();
      }}
      closeShellOverlays("modal");
      syncPacketTreeToTarget(packetId, {{ catalystPage: state.catalystPage }});
      state.packet = packetId;
      state.windowStates.modal.minimized = false;
      state.windowStates.modal.maximized = false;
      if (packetId === "triage") {{
        ensureFloatingModalPlacement("triage");
      }}
      state.packetStripExpanded = true;
      document.body.classList.add("modal-open");
      setActiveOverlay("modal", {{ packetId }});
      syncShellFocusMode();
      renderContextActionDock();
      fillPacketStrip();
      const modal = document.getElementById("modal-layer");
      const title = document.getElementById("modal-title");
      const body = document.getElementById("modal-body");
      const data = state.dashboard || {{}};
      if (packetId === "lifecycle-inspector") {{
        state.packetHydrationPending = "";
        heading = "Work Item Inspector";
        title.textContent = heading;
        body.innerHTML = renderLifecycleInspectorMarkup();
        setModalVisibility(true);
        return;
      }}
      const needsDashboardHydration =
        ((packetId === "dashboard" || packetId === "triage" || packetId === "today" || packetId === "review" || packetId === "tasks") && !state.dashboard) ||
        (packetId === "dashboard" && !data.assistant_notifications) ||
        (packetId === "triage" && !data.today_board) ||
        (packetId === "today" && !data.today_board) ||
        (packetId === "review" && !data.cadence_review) ||
        (packetId === "tasks" && !data.open_loops) ||
        (packetId === "finance-review" && !state.financeReview) ||
        (packetId === "wealth" && !state.wealthReview);
      let heading = "Packet";
      let content = "";

      if (needsDashboardHydration) {{
        if (state.packetHydrationPending === packetId) {{
          setModalVisibility(true);
          return;
        }}
        title.textContent =
          packetId === "triage"
            ? "Triage And Transition"
            :
          packetId === "today"
            ? "Today Board"
            : packetId === "wealth"
              ? "Wealth Review"
            : packetId === "finance-review"
              ? "Family Finance Review"
            : packetId === "review"
              ? "Cadence Review"
              : packetId === "tasks"
                ? "Assistant Core"
                : "Packet";
        body.innerHTML = `<div class="packet-grid"><div class="metric">${{
          packetId === "triage"
            ? "Loading Triage And Transition..."
          :
          packetId === "today"
            ? "Loading Today Board..."
            : packetId === "wealth"
              ? "Loading Wealth Review..."
            : packetId === "finance-review"
              ? "Loading Family Finance Review..."
            : packetId === "dashboard"
              ? "Loading Dashboard Report..."
            : packetId === "review"
              ? "Loading Cadence Review..."
              : packetId === "tasks"
                ? "Loading Assistant Core..."
                : "Loading live assistant state..."
        }}</div></div>`;
        state.packetHydrationPending = packetId;
        const hydrationToken = ++state.packetHydrationToken;
        setModalVisibility(true);
        const actor = preferredActorLabel();
        const hydrate = packetId === "triage" || packetId === "today" || packetId === "review" || packetId === "dashboard"
          ? refreshDashboard({{ minIntervalMs: 10000 }})
          : packetId === "finance-review"
            ? refreshFinanceReview({{ force: true }})
          : packetId === "wealth"
            ? refreshWealthReview({{ force: true }})
          : packetId === "tasks"
            ? loadJSON(`/api/open-loops?actor=${{encodeURIComponent(actor)}}&limit=18`).then((openLoops) => {{
                mergeDashboardState({{
                  open_loops: openLoops,
                }});
              }})
            : refreshDashboard();
        hydrate
          .then(() => {{
            if (state.packet === packetId && state.packetHydrationToken === hydrationToken) {{
              state.packetHydrationPending = "";
              openPacket(packetId);
            }}
          }})
          .catch((error) => {{
            if (state.packet === packetId && state.packetHydrationToken === hydrationToken) {{
              state.packetHydrationPending = "";
              body.innerHTML = `<div class="packet-grid"><div class="metric">${{escapeHtml(error?.message || "Failed to load packet data.")}}</div></div>`;
            }}
          }});
        return;
      }}

      if (state.packetHydrationPending === packetId) {{
        state.packetHydrationPending = "";
      }}

      if (packetId === "dashboard") {{
        heading = "Dashboard Report";
        const dashboardSummary = dashboardLauncherSummary(data);
        const todayBoard = data.today_board || {{}};
        const cadence = data.cadence_review || {{}};
        const liveWorkspace = data.catalyst_overview?.live_workspace || {{}};
        const adapters = data.environment_status?.adapters || [];
        const activeMode = data.active_mode || {{}};
        content = `
          <div class="packet-grid">
            ${{
              packetBlock(
                "Action Load",
                `
                  <div class="metric"><strong>Total</strong> ${{escapeHtml(String(dashboardSummary.total))}} active item(s)</div>
                  <div class="metric"><strong>Priorities</strong> ${{escapeHtml(String(dashboardSummary.priorities))}}</div>
                  <div class="metric"><strong>Approvals</strong> ${{escapeHtml(String(dashboardSummary.approvals))}}</div>
                  <div class="metric"><strong>Assistant inbox</strong> ${{escapeHtml(String(dashboardSummary.unread))}}</div>
                  <p>${{escapeHtml(todayBoard.summary || cadence.summary || "No broad summary is loaded right now.")}}</p>
                `
              )
            }}
            ${{
              packetBlock(
                "Executive Surface",
                `
                  <div class="metric"><strong>Mode</strong> ${{escapeHtml(activeMode.mode || "watch")}}</div>
                  <div class="metric"><strong>Calendar</strong> ${{escapeHtml(String(liveWorkspace.calendar?.items?.length || 0))}} item(s)</div>
                  <div class="metric"><strong>Email</strong> ${{escapeHtml(String(liveWorkspace.email?.items?.length || 0))}} item(s)</div>
                  <div class="metric"><strong>Tasks</strong> ${{escapeHtml(String(liveWorkspace.tasks?.stats?.openCount || 0))}} open</div>
                  <div class="inline-actions" style="margin-top:10px;">
                    <button class="ghost-toggle" type="button" data-dashboard-open="today">Open Day Board</button>
                    <button class="ghost-toggle" type="button" data-dashboard-open="catalyst">Open Catalyst</button>
                  </div>
                `
              )
            }}
            ${{
              packetBlock(
                "System Health",
                renderList(adapters.slice(0, 6).map((adapter) => `
                  <div>
                    <strong>${{escapeHtml(adapter.label || adapter.id || "Adapter")}}</strong><br>
                    ${{escapeHtml(adapter.status || adapter.mode || "unknown")}} · ${{escapeHtml(adapter.detail || "No detail")}}
                  </div>
                `))
              )
            }}
            ${{
              packetBlock(
                "Assistant Inbox",
                renderAssistantInboxItems(data.assistant_notifications?.items || [], "No unread assistant items are waiting right now.")
              )
            }}
          </div>`;
      }} else if (packetId === "briefing") {{
        const firstLight = state.firstLight || null;
        heading = firstLight ? "First Light" : "Morning Brief";
        if (firstLight) {{
          content = `
            <div class="packet-grid">
              ${{renderFreshnessBanner(firstLight, "First Light")}}
              ${{
                packetBlock("Opening", `<p>${{escapeHtml(firstLight.opening || state.lastBriefing || "")}}</p>${{renderList((firstLight.what_changed || []).map((item) => `<div>${{escapeHtml(item)}}</div>`))}}`)
              }}
              ${{
                packetBlock("First 20 Minutes", renderList((firstLight.first_20_minutes || []).map((item) => `<div>${{escapeHtml(item)}}</div>`)))
              }}
              ${{
                packetBlock("Watch", `<p>${{escapeHtml(firstLight.watch_line || "")}}</p>`)
              }}
              ${{
                packetBlock("Formation", `<p>${{escapeHtml(firstLight.formation_cue || "")}}</p>`)
              }}
              ${{(firstLight.sections || []).map((section) => renderFirstLightSection(section)).join("")}}
            </div>`;
        }} else {{
          content = `
            <div class="packet-grid">
              ${{
                packetBlock("Body", `<p>${{escapeHtml(data.cards?.body?.summary || "")}}</p>${{renderList((data.cards?.body?.details || []).map((item) => `<div>${{escapeHtml(item)}}</div>`))}}`)
              }}
              ${{
                homeConnectorLive(data)
                  ? packetBlock("Home", `<p>${{escapeHtml(data.cards?.home?.summary || "")}}</p>${{renderList((data.cards?.home?.details || []).map((item) => `<div>${{escapeHtml(item)}}</div>`))}}`)
                  : packetBlock("Home", `<p>Live home state is unavailable until Home Assistant is connected. Staged house data is hidden.</p>`)
              }}
              ${{
                packetBlock("Mission", `<p>${{escapeHtml(data.cards?.mission?.summary || "")}}</p>${{renderList((data.cards?.mission?.details || []).map((item) => `<div>${{escapeHtml(item)}}</div>`))}}`)
              }}
              ${{
                packetBlock("Briefing", `<p>${{escapeHtml(state.lastBriefing || "Use the Brief button or ask JARVIS for a briefing.")}}</p>`)
              }}
            </div>`;
        }}
      }} else if (packetId === "triage") {{
        heading = "Triage And Transition";
        content = renderTriagePacketMarkup(data);
      }} else if (packetId === "today") {{
        heading = "Today Board";
        const board = data.today_board || {{}};
        const notifications = board.assistant_notifications || {{}};
        const notificationPolicy = board.notification_policy || {{}};
        const quietWindow = notificationPolicy.quiet_window || {{}};
        const browserAlertStatus = !browserAlertsSupported()
          ? "Browser alerts are not supported on this device."
          : state.browserAlertsPermission === "granted" && state.browserAlertsEnabled
            ? "Browser alerts are active for assistant follow-up."
            : state.browserAlertsPermission === "denied"
              ? "Browser alerts are blocked by the browser for this device."
              : "Browser alerts are available but not enabled yet.";
        content = `
          <div class="packet-grid">
            ${{renderFreshnessBanner(board, "Today Board")}}
            ${{
              packetBlock("Priorities", renderList((board.priorities || []).map((item) => `
                <div>
                  <strong>${{escapeHtml(item.title || "Priority")}}</strong>
                  <br>${{escapeHtml(item.owner_agent || "JARVIS")}} · ${{escapeHtml(item.next_action || "follow up")}} · ${{escapeHtml(item.status || "open")}}
                </div>
              `)))
            }}
            ${{
              packetBlock("Carry Today", renderList((board.carry || []).map((item) => `<div>${{escapeHtml(item)}}</div>`)))
            }}
            ${{
              packetBlock("Calendar Pressure", renderList((board.calendar || []).map((item) => `<div><strong>${{escapeHtml(item.summary || "(Untitled event)")}}</strong><br>${{escapeHtml(item.start || "")}}</div>`)))
            }}
            ${{
              packetBlock("Autonomy Boundary", renderList((board.autonomy || []).map((item) => `<div>${{escapeHtml(item)}}</div>`)))
            }}
            ${{
              packetBlock(
                "Cognitive Posture",
                `
                  <div class="metric"><strong>Mode</strong> ${{escapeHtml(board.cognition?.deliberation?.mode || "watch")}}</div>
                  <div class="metric"><strong>Decision</strong> ${{escapeHtml(board.cognition?.deliberation?.decision || "hold")}}</div>
                  <div class="metric"><strong>Cadence</strong> ${{escapeHtml(board.cognition?.cadence?.phase || "watch")}} · ${{escapeHtml(board.cognition?.cadence?.suggested_loop || "autonomy-sweep")}}</div>
                  <div class="metric"><strong>Active loop</strong> ${{escapeHtml((board.cognition?.cadence?.loops || []).find((item) => item.state === "active")?.label || "Autonomy Sweep")}}</div>
                  <div class="metric"><strong>World state</strong> ${{escapeHtml(board.cognition?.world_state?.pressure || "steady")}} · tasks ${{escapeHtml(String(board.cognition?.world_state?.summary?.tasks || 0))}} · notifications ${{escapeHtml(String(board.cognition?.world_state?.summary?.notifications || 0))}}</div>
                  <div class="metric"><strong>Goal pull</strong> ${{escapeHtml((board.cognition?.goal_stack?.immediate || [])[0] || "No strong immediate pull")}}</div>
                  ${{renderList((board.cognition?.deliberation?.reasoning || []).map((item) => `<div>${{escapeHtml(item)}}</div>`))}}
                  <div class="metric" style="margin-top:10px;"><strong>Council consensus</strong> ${{escapeHtml(board.cognition?.internal_council?.consensus || "hold")}}</div>
                  ${{renderList((board.cognition?.internal_council?.members || []).slice(0, 3).map((item) => `<div><strong>${{escapeHtml(item.role || "council")}}</strong> · ${{escapeHtml(item.vote || "queue")}}<br>${{escapeHtml(item.recommendation || "")}}</div>`))}}
                  ${{renderList((board.cognition?.world_state?.delta?.added_labels || []).slice(0, 3).map((item) => `<div><strong>New signal</strong><br>${{escapeHtml(item)}}</div>`))}}
                `
              )
            }}
            ${{
              packetBlock(
                "Assistant Inbox",
                `
                  <p>${{escapeHtml(browserAlertStatus)}}</p>
                  <div class="inline-actions" style="margin:0 0 10px 0;">
                    <button class="btn btn-secondary" id="enable-browser-alerts" type="button">Enable Browser Alerts</button>
                    <button class="btn btn-subtle" id="disable-browser-alerts" type="button">Mute Browser Alerts</button>
                  </div>
                  <div class="metric"><strong>Delivery policy</strong> ${{
                    notificationPolicy.quiet_hours_active
                      ? `Quiet hours active · ${{escapeHtml(quietWindow.start || "22:00")}} to ${{escapeHtml(quietWindow.end || "06:00")}}`
                      : `Active hours · browser-eligible items may interrupt`
                  }}</div>
                  <div class="metric"><strong>Inbox state</strong> unseen ${{escapeHtml(String(notifications.summary?.by_status?.unseen || 0))}} · surfaced ${{escapeHtml(String(notifications.summary?.by_status?.surfaced || 0))}} · opened ${{escapeHtml(String(notifications.summary?.by_status?.opened || 0))}}</div>
                  <div class="metric"><strong>Priority mix</strong> quiet ${{escapeHtml(String(notifications.summary?.by_priority?.quiet || 0))}} · normal ${{escapeHtml(String(notifications.summary?.by_priority?.normal || 0))}} · interrupt-worthy ${{escapeHtml(String(notifications.summary?.by_priority?.["interrupt-worthy"] || 0))}}</div>
                  ${{
                    notifications.summary?.unread
                      ? renderAssistantInboxItems(notifications.items || [])
                      : "<p>No unread assistant nudges are waiting right now.</p>"
                  }}
                `
              )
            }}
          </div>`;
      }} else if (packetId === "review") {{
        const review = data.cadence_review || {{}};
        const recommendedAction = review.recommended_action || null;
        const reviewSections = (review.sections || []).filter((section) => !/(growth|finance|marketing|pipeline)/i.test(String(section.title || "")));
        heading = review.title || "Cadence Review";
        content = `
          <div class="packet-grid">
            ${{renderFreshnessBanner(review, "Cadence Review")}}
            ${{
              packetBlock(
                "Cadence",
                `
                  <div class="metric"><strong>Phase</strong> ${{escapeHtml(review.phase || "watch")}}</div>
                  <div class="metric"><strong>Active loop</strong> ${{escapeHtml(review.active_loop || "Autonomy Sweep")}}</div>
                  <p>${{escapeHtml(review.summary || "No cadence summary is available yet.")}}</p>
                  <p><strong>Digest</strong><br>${{escapeHtml(review.digest || "No digest is available yet.")}}</p>
                  <p><strong>Why this surfaced</strong><br>${{escapeHtml(review.why_this_surfaced || review.digest || review.summary || "JARVIS judged that this review deserved attention now.")}}</p>
                  ${{recommendedAction?.action_id ? `
                    <div class="inline-actions" style="margin-top:10px;">
                      <button
                        type="button"
                        class="ghost-toggle review-action-button"
                        data-domain="${{escapeHtml(recommendedAction.domain || "")}}"
                        data-item-id="${{escapeHtml(recommendedAction.item_id || "")}}"
                        data-action="${{escapeHtml(recommendedAction.action_id || "")}}"
                      >${{escapeHtml(recommendedAction.label || "Act Now")}}</button>
                    </div>
                  ` : ""}}
                `
              )
            }}
            ${{
              reviewSections.map((section) => packetBlock(
                section.title || "Section",
                `
                  <p>${{escapeHtml(section.summary || "")}}</p>
                  ${{renderList((section.details || []).map((item) => `<div>${{escapeHtml(item)}}</div>`))}}
                `
              )).join("")
            }}
            ${{
              (data.assistant_notifications?.items || []).length
                ? packetBlock("Inbox Actions", renderAssistantInboxItems(data.assistant_notifications.items || []))
                : ""
            }}
          </div>`;
      }} else if (packetId === "finance-review") {{
        heading = "Family Finance Review";
        content = renderFinanceReviewMarkup(state.financeReview || {{}});
      }} else if (packetId === "wealth") {{
        heading = "Wealth Review";
        content = renderWealthReviewMarkup(state.wealthReview || {{}});
      }} else if (packetId === "storm") {{
        heading = "Storm Weather Dashboard";
        content = `
          <iframe
            class="storm-frame"
            id="storm-dashboard-frame"
            title="Storm Weather Dashboard"
            src="/storm-dashboard"
          ></iframe>
        `;
      }} else if (packetId === "brains") {{
        heading = "Brain Packet";
        const graph = data.brain_graph || {{}};
        const activeRoute = (graph.active_nodes || []).map((item) => `<span>${{escapeHtml(item.replaceAll("-", " "))}}</span>`).join("");
        const meshStatus = (graph.nodes || []).map((item) => `
          <div class="brain-side-row">
            <strong>${{escapeHtml(item.label)}}</strong> · ${{escapeHtml(item.status)}}
          </div>
        `).join("");
        content = `
          <div class="brains-shell">
            <div class="brains-summary">
              <span class="tag">Active ${{escapeHtml(graph.active_provider || "standby")}}</span>
              <span class="tag">Model ${{escapeHtml(graph.active_model || graph.secondary_brain?.model || "--")}}</span>
              <span class="tag">Last Module ${{escapeHtml(graph.last_module || "--")}}</span>
              <span class="tag">Second Brain ${{escapeHtml(graph.secondary_brain?.provider || "--")}}</span>
            </div>
            <div class="brains-layout">
              <div class="brain-network-shell">
                <div class="brain-network-head">
                  <strong>Cognitive Topology</strong>
                  <span>Live orchestrator view</span>
                </div>
                <div class="brain-mesh-modal-stage hero" id="brain-mesh-modal">
                  <canvas class="brain-mesh-canvas" aria-hidden="true"></canvas>
                  <div class="brain-mesh-overlay"></div>
                  <div class="brain-mesh-caption"><span>Clustered skills and live reasoning paths</span><span>${{escapeHtml(graph.active_provider || "standby")}}</span></div>
                </div>
              </div>
              <div class="brains-sidebar">
                <div class="brains-sidecard">
                  <h3>Active Route</h3>
                  <div class="brain-route">${{activeRoute || '<span>standby</span>'}}</div>
                </div>
                <div class="brains-sidecard">
                  <h3>Provider Stack</h3>
                  <div class="brain-side-list">
                    <div class="brain-side-row"><strong>Primary</strong> OpenAI · ${{escapeHtml(graph.active_provider === "ollama" ? "standby" : (graph.active_model || "--"))}}</div>
                    <div class="brain-side-row"><strong>Second</strong> ${{escapeHtml(graph.secondary_brain?.provider || "--")}} · ${{escapeHtml(graph.secondary_brain?.model || "--")}}</div>
                    <div class="brain-side-row"><strong>Health</strong> ${{escapeHtml(String(graph.secondary_brain?.healthy ?? false))}} · loaded ${{escapeHtml(String(graph.secondary_brain?.model_available ?? false))}}</div>
                  </div>
                </div>
                <div class="brains-sidecard">
                  <h3>Mesh Status</h3>
                  <div class="brain-side-list">${{meshStatus}}</div>
                </div>
                <div class="brains-sidecard">
                  <h3>Legend</h3>
                  <div class="brain-legend">
                    <span>Core</span>
                    <span>Primary</span>
                    <span>Second</span>
                    <span>Memory</span>
                    <span>Family</span>
                    <span>Chronicle</span>
                    <span>Workshop</span>
                    <span>Executive</span>
                  </div>
                </div>
              </div>
            </div>
          </div>`;
      }} else if (packetId === "agents") {{
        heading = "Agent Registry";
        const background = data.background_agents || {{}};
        const statuses = background.statuses || [];
        const registry = data.agent_registry?.agents || [];
        const curator = data.memory_curator || {{}};
        const liveExecution = background.live_execution === true;
        content = `
          <div class="packet-grid">
            ${{
              packetBlock("Hierarchy View", `
                <p>Open the dedicated agent hierarchy page for a full command-map view and future specialist planning.</p>
                <div class="inline-actions">
                  <button type="button" id="open-agent-hierarchy">Open Agent Hierarchy</button>
                </div>`)
            }}
            ${{
              packetBlock("Scheduler Status", liveExecution ? `
                <div class="stack">
                  <div class="metric"><strong>Awake</strong> ${{escapeHtml(String(background.awake_count ?? 0))}}</div>
                  <div class="metric"><strong>Idle</strong> ${{escapeHtml(String(background.idle_count ?? 0))}}</div>
                  <div class="metric"><strong>Blocked</strong> ${{escapeHtml(String(background.blocked_count ?? 0))}}</div>
                  <div class="metric"><strong>Mode</strong> ${{escapeHtml((background.active_mode || "ambient-associate").replaceAll("-", " "))}}</div>
                </div>` : `
                <p>Background role counts are hidden until JARVIS has real live execution-state tracking instead of scheduler posture.</p>
                <div class="metric"><strong>Mode</strong> ${{escapeHtml((background.active_mode || "ambient-associate").replaceAll("-", " "))}}</div>
              `)
            }}
            ${{
              packetBlock("Awake Now", liveExecution ? (renderList(statuses.filter((item) => item.state === "awake").map((item) => `<div><strong>${{escapeHtml(item.label)}}</strong> · ${{escapeHtml(item.reason)}}</div>`)) || `<div class="empty">No agents are currently awake.</div>`) : `<div class="empty">Live execution-state tracking is not enabled yet.</div>`)
            }}
            ${{
              packetBlock("Blocked", liveExecution ? (renderList(statuses.filter((item) => item.state === "blocked").map((item) => `<div><strong>${{escapeHtml(item.label)}}</strong> · waiting on ${{escapeHtml((item.blocked_dependencies || []).join(", ") || "dependency")}}</div>`)) || `<div class="empty">Nothing is blocked at the moment.</div>`) : `<div class="empty">Blocked counts are hidden until live execution-state tracking exists.</div>`)
            }}
            ${{
              packetBlock("Memory Curator", `
                <p>${{escapeHtml(curator.summary || "The curator is standing by.")}}</p>
                ${{renderList((curator.candidates || []).map((item) => `<div><strong>${{escapeHtml(item.proposed_type)}}</strong> · ${{escapeHtml(item.request)}}<br>${{escapeHtml(item.note || "")}}</div>`))}}
              `)
            }}
            ${{
              packetBlock("Registry", renderList(registry.map((item) => `<div><strong>${{escapeHtml(item.label)}}</strong> · every ${{escapeHtml(String(item.cadence_minutes))}} min<br>${{escapeHtml(item.purpose)}}</div>`)))
            }}
            ${{
              packetBlock("Curation Rules", renderList((curator.rules || []).map((item) => `<div><strong>${{escapeHtml(item.label)}}</strong> · ${{escapeHtml(item.capture_when)}}</div>`)))
            }}
          </div>`;
      }} else if (packetId === "connected-devices") {{
        heading = "Connected Devices";
        content = `
          <div class="packet-grid">
            ${{
              packetBlock("Admin View", `
                <p>See every registered phone, tablet, browser, and display JARVIS knows about, then map each one to the right family member without guessing. This is app-level identity only: device ids, session fingerprints, and last-seen posture, not MAC or IMEI numbers.</p>
                <div class="inline-actions">
                  <button type="button" id="connected-devices-refresh">Refresh Devices</button>
                  <button type="button" id="connected-devices-bind-current">Bind Current Browser</button>
                  <button type="button" id="connected-devices-prune" class="ghost-toggle">Prune Old Browser Sessions</button>
                </div>
                <label class="toggle-row" style="margin-top:10px;">
                  <input type="checkbox" id="connected-devices-hide-stale" checked>
                  Hide stale and test-like browser sessions
                </label>
                <div class="settings-note" id="connected-devices-status">Loading connected devices…</div>
              `)
            }}
            ${{
              packetBlock("Summary", `<div class="stack" id="connected-devices-summary"><div class="metric">Loading device summary…</div></div>`)
            }}
            ${{
              packetBlock("Current Connection", `<div class="stack" id="connected-device-current"><div class="metric">Loading current device…</div></div>`)
            }}
            ${{
              packetBlock("Registry", `<div class="stack" id="connected-devices-list"><div class="metric">Loading device registry…</div></div>`)
            }}
          </div>`;
      }} else if (packetId === "home") {{
        heading = "House Packet";
        content = renderHomePacketMarkup(data);
      }} else if (packetId === "family") {{
        heading = "Family Packet";
        content = renderFamilyPacketMarkup(data);
      }} else if (packetId === "security") {{
        heading = "Security Packet";
        content = `
          <div class="packet-grid">
            ${{
              packetBlock("Incidents", renderList((data.security_incidents || []).slice(0, 5).map((item) => `<div><strong>${{escapeHtml(item.headline)}}</strong><br>${{escapeHtml(item.recommended_action)}}</div>`)))
            }}
            ${{
              packetBlock("Overnight Review", `<p>${{escapeHtml(data.overnight_review?.summary || "")}}</p>${{renderList((data.overnight_review?.carry_forward || []).map((item) => `<div>${{escapeHtml(item)}}</div>`))}}`)
            }}
            ${{
              packetBlock("Arrivals", renderList((data.arrival_events || []).map((item) => `<div><strong>${{escapeHtml(item.actor)}}</strong> · ${{escapeHtml(item.location)}} · ${{escapeHtml(item.status)}}</div>`)))
            }}
            ${{
              packetBlock("Approvals", renderList((data.explainability?.approval_history || []).filter((item) => item.status === "pending").map((item) => `<div>${{escapeHtml(item.request)}}</div>`)))
            }}
          </div>`;
      }} else if (packetId === "vision") {{
        heading = "Vision";
        content = `
          <div class="vision-shell">
            <div class="vision-note">Live preview only while this modal is open. JARVIS does not continuously monitor your desk. Capture happens only when you press <strong>Capture Frame</strong>.</div>
            <div class="vision-grid">
              <div class="vision-stage">
                <div class="workspace-summary">
                  <span class="tag">On-demand only</span>
                  <span class="tag">No background watching</span>
                  <span class="tag">Single-frame analysis</span>
                </div>
                <div class="vision-controls">
                  <label>
                    Analysis mode
                    <select id="vision-mode">
                      <option value="describe">General scene</option>
                      <option value="text">Read text only</option>
                      <option value="compare">Compare to previous frame</option>
                      <option value="measure">Measure with calibration</option>
                    </select>
                  </label>
                  <div class="vision-helper">For zoom crop or measurement, turn crop on and drag across the live preview before you capture.</div>
                </div>
                <div class="vision-feed">
                  <video id="vision-live-video" autoplay playsinline muted></video>
                  <canvas id="vision-canvas"></canvas>
                  <div class="vision-crop-box" id="vision-crop-box"></div>
                </div>
                <div class="inline-actions">
                  <button id="vision-start" type="button">Start Camera</button>
                  <button id="vision-toggle-crop" type="button">Crop Before Analyze</button>
                  <button id="vision-capture" class="ghost-toggle" type="button">Capture Frame</button>
                  <button id="vision-retake" type="button">Retake</button>
                </div>
                <div class="vision-status" id="vision-status">Open this modal to request a live preview. Capture only happens when you ask for it.</div>
              </div>
              <div class="vision-preview-card">
                <label>
                  Camera
                  <select id="vision-device">
                    <option value="">Default camera</option>
                  </select>
                </label>
                <label>
                  Ask JARVIS what to look for
                  <textarea id="vision-prompt" placeholder="What do you see on my desk? Read the label on this box. Is my notebook open?"></textarea>
                </label>
                <div class="vision-measure-panel">
                  <div class="metric"><strong>Measure Mode</strong></div>
                  <div class="vision-helper">Place a ruler on the stage, turn crop on, and drag across a known span. Then calibrate once and reuse it.</div>
                  <div class="vision-measure-grid">
                    <label>
                      Known length
                      <input id="vision-calibration-length" type="number" min="0.1" step="0.1" value="1">
                    </label>
                    <label>
                      Units
                      <select id="vision-calibration-unit">
                        <option value="cm">cm</option>
                        <option value="mm">mm</option>
                        <option value="in">in</option>
                      </select>
                    </label>
                  </div>
                  <div class="inline-actions">
                    <button id="vision-calibrate" type="button">Calibrate Selection</button>
                    <button id="vision-clear-calibration" type="button">Clear Calibration</button>
                  </div>
                  <div class="vision-measure-summary" id="vision-calibration-summary">No calibration yet.</div>
                </div>
                <img id="vision-preview" alt="Captured frame preview" hidden>
                <div class="metric"><strong>Analysis</strong></div>
                <div class="output-box" id="vision-analysis">No frame captured yet.</div>
                <div class="inline-actions" style="margin-top:10px;">
                  <button id="vision-send-to-concept" type="button">Send to Concept Studio</button>
                </div>
              </div>
            </div>
          </div>`;
      }} else if (packetId === "model-forge") {{
        heading = "Model Forge";
        const packages = data.cad_packages || [];
        content = `
          <div class="model-forge-shell">
            <div class="workspace-summary">
              <span class="tag">Packages ${{escapeHtml(String(packages.length))}}</span>
              <span class="tag">Source-first</span>
              <span class="tag">Fit-check STL when possible</span>
            </div>
            <div class="model-forge-grid">
              <div class="model-forge-stage">
                <div class="model-forge-stage-head">
                  <div class="model-forge-stage-copy">
                    <h3>Live 3D Workbench</h3>
                    <p>Inspect the generated package at full scale, orbit the STL, and keep the geometry center stage while Forge controls stay off to the side.</p>
                  </div>
                  <div class="model-forge-stage-badges">
                    <span class="tag">Wide Viewer</span>
                    <span class="tag">Scene First</span>
                    <span class="tag">Package Preview</span>
                  </div>
                </div>
                <div class="model-forge-viewer" id="model-forge-viewer"></div>
                <div class="model-forge-empty" id="model-forge-empty">Choose a generated model package to inspect its STL here.</div>
                <div class="model-forge-overlay" id="model-forge-overlay">
                  <div class="model-forge-overlay-head">
                    <div class="model-forge-overlay-title">
                      <strong id="model-forge-overlay-name">No package loaded</strong>
                      <span id="model-forge-overlay-kind">Waiting for package selection</span>
                    </div>
                    <div class="model-forge-overlay-status" id="model-forge-overlay-status">Idle</div>
                  </div>
                  <div class="model-forge-overlay-copy" id="model-forge-overlay-copy">Load a package to surface printer, profile, material, and export posture directly in the viewer.</div>
                  <div class="model-forge-overlay-stats">
                    <div class="model-forge-overlay-stat">
                      <span>Family</span>
                      <strong id="model-forge-overlay-family">--</strong>
                    </div>
                    <div class="model-forge-overlay-stat">
                      <span>Printer</span>
                      <strong id="model-forge-overlay-printer">--</strong>
                    </div>
                    <div class="model-forge-overlay-stat">
                      <span>Profile</span>
                      <strong id="model-forge-overlay-profile">--</strong>
                    </div>
                    <div class="model-forge-overlay-stat">
                      <span>Material</span>
                      <strong id="model-forge-overlay-material">--</strong>
                    </div>
                  </div>
                </div>
                <div class="model-forge-stage-foot">
                  <div class="model-forge-stage-status" id="model-forge-viewer-status">${{packages.length ? "Ready to load the latest generated package." : "No model forge packages yet. Generate one from the Workshop packet first."}}</div>
                  <div class="model-forge-stage-actions">
                    <button id="model-forge-refresh" type="button">Load Model</button>
                  </div>
                </div>
              </div>
              <div class="model-forge-panel">
                <div class="model-forge-tabs" role="tablist" aria-label="Model Forge panel modes">
                  <button type="button" class="model-forge-tab active" data-model-forge-tab="concept">Concept</button>
                  <button type="button" class="model-forge-tab" data-model-forge-tab="create">Create</button>
                  <button type="button" class="model-forge-tab" data-model-forge-tab="details">Details</button>
                  <button type="button" class="model-forge-tab" data-model-forge-tab="source">Source</button>
                </div>
                <div class="model-forge-tab-panel active" data-model-forge-panel="concept">
                  <div class="model-forge-meta hero">
                    <div class="model-forge-meta-head">
                      <h3>Concept Studio</h3>
                      <p>Talk through unique objects, use a Vision capture as reference, and only move into package generation once the design direction feels right.</p>
                    </div>
                    <div class="stack" style="gap:10px;">
                      <label>
                        Creative object type
                        <select id="model-forge-concept-type">
                          <option value="sculpture">Sculpture</option>
                          <option value="sporting good">Sporting good</option>
                          <option value="prop or decor">Prop or decor</option>
                          <option value="organic reconstruction">Organic reconstruction</option>
                          <option value="functional object">Functional object</option>
                          <option value="custom object" selected>Custom object</option>
                        </select>
                      </label>
                      <label>
                        Concept silhouette
                        <select id="model-forge-concept-silhouette">
                          <option value="">Let Forge choose</option>
                          <option value="calm-spiral">Calm spiral</option>
                          <option value="tense-twist">Tense twist</option>
                          <option value="split-ribbon">Split ribbon</option>
                          <option value="monolith">Monolith</option>
                          <option value="racket-frame">Racket frame</option>
                          <option value="organic-shell">Organic shell</option>
                          <option value="display-prop">Display prop</option>
                          <option value="organic-reconstruction">Organic reconstruction</option>
                        </select>
                      </label>
                      <label>
                        Goals
                        <textarea id="model-forge-concept-goals" rows="3" placeholder="What are we trying to create, who is it for, and what should it feel like?"></textarea>
                      </label>
                      <label>
                        Constraints
                        <textarea id="model-forge-concept-constraints" rows="3" placeholder="Size limits, strength, print-bed limits, style constraints, assembly rules..."></textarea>
                      </label>
                      <label>
                        Vision reference
                        <select id="model-forge-concept-capture">
                          <option value="">No photo reference</option>
                        </select>
                      </label>
                      <label>
                        Reference note
                        <textarea id="model-forge-concept-reference" rows="2" placeholder="What should JARVIS pay attention to in the reference image?"></textarea>
                      </label>
                      <label>
                        Let&apos;s build
                        <textarea id="model-forge-concept-prompt" rows="4" placeholder="Design a printable tennis racket concept with a strong futuristic frame and a believable print strategy."></textarea>
                      </label>
                      <div class="inline-actions">
                        <button id="model-forge-concept-send" type="button">Discuss Concept</button>
                        <button id="model-forge-concept-apply" type="button">Send to Create</button>
                      </div>
                      <div class="vision-status" id="model-forge-concept-status">Start a concept thread, or bring in a recent Vision capture as a reference.</div>
                      <div class="model-forge-concept-layout">
                        <div class="model-forge-silhouette-card" id="model-forge-silhouette-card">
                          <div class="model-forge-silhouette-head">
                            <div class="model-forge-silhouette-copy">
                              <span>Silhouette preview</span>
                              <strong id="model-forge-silhouette-name">Waiting for direction</strong>
                            </div>
                            <div class="model-forge-silhouette-badge" id="model-forge-silhouette-badge">Unchosen</div>
                          </div>
                          <div class="model-forge-silhouette-stage">
                            <div class="model-forge-silhouette-art" id="model-forge-silhouette-art"></div>
                          </div>
                          <div class="model-forge-silhouette-description" id="model-forge-silhouette-description">Forge will surface a silhouette direction before the concept becomes a package.</div>
                          <div class="model-forge-silhouette-metrics">
                            <div class="model-forge-silhouette-metric">
                              <span>Print posture</span>
                              <strong id="model-forge-silhouette-print">--</strong>
                            </div>
                            <div class="model-forge-silhouette-metric">
                              <span>Use case</span>
                              <strong id="model-forge-silhouette-use">--</strong>
                            </div>
                            <div class="model-forge-silhouette-metric">
                              <span>Character</span>
                              <strong id="model-forge-silhouette-character">--</strong>
                            </div>
                          </div>
                        </div>
                        <div class="metric">
                          <strong>Compare Directions</strong>
                        </div>
                        <div class="model-forge-variant-strip" id="model-forge-variant-strip">
                          <div class="model-forge-variant-card">
                            <strong>Forge will generate options</strong>
                            <div class="model-forge-variant-pitch">Discuss the concept once and we’ll surface 2 to 3 directions here before package generation.</div>
                          </div>
                        </div>
                        <div class="metric">
                          <strong>Design Brief</strong>
                        </div>
                        <div class="output-box" id="model-forge-concept-brief">No concept session yet.</div>
                        <div class="metric">
                          <strong>Conversation</strong>
                        </div>
                        <div class="output-box" id="model-forge-concept-transcript">Your design dialogue with Forge will appear here.</div>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="model-forge-tab-panel" data-model-forge-panel="create">
                  <div class="model-forge-meta hero">
                    <div class="model-forge-meta-head">
                      <h3>Create Package</h3>
                      <p>Shape the next part, target the machine, and generate a fresh package without leaving the viewer context.</p>
                    </div>
                    <div class="stack" style="gap:10px;">
                      <label>
                        Part family
                        <select id="model-forge-family"></select>
                      </label>
                      <label>
                        Machine target
                        <select id="model-forge-printer"></select>
                      </label>
                      <label>
                        Print profile
                        <select id="model-forge-profile"></select>
                      </label>
                      <label>
                        Slicer handoff
                        <select id="model-forge-slicer"></select>
                      </label>
                      <div class="vision-status" id="model-forge-guidance">Choose a family to prefill the working geometry.</div>
                      <label>
                        Part name
                        <input id="model-forge-part" type="text" value="Garden bench bracket">
                      </label>
                      <label>
                        Dimensions
                        <textarea id="model-forge-dimensions" rows="4" placeholder="hole spacing 110 mm, plate width 30 mm, thickness 8 mm"></textarea>
                      </label>
                      <label>
                        Constraints
                        <textarea id="model-forge-constraints" rows="3" placeholder="Preserve mounting geometry and strengthen the fatigue path."></textarea>
                      </label>
                      <div class="model-forge-actions">
                        <button id="model-forge-generate" type="button">Generate Package</button>
                      </div>
                      <pre class="model-forge-script" id="model-forge-generation-output">Awaiting generation request.</pre>
                    </div>
                  </div>
                </div>
                <div class="model-forge-tab-panel" data-model-forge-panel="details">
                  <div class="model-forge-meta" id="model-forge-details">
                    <div class="model-forge-meta-head">
                      <h3>Package Details</h3>
                      <p>Choose a generated package, inspect export readiness, and move directly into slicer handoff when the geometry checks out.</p>
                    </div>
                    <label>
                      Model package
                      <select id="model-forge-package">
                        ${{packages.map((item, index) => `<option value="${{escapeHtml(item.package_id)}}"
                          ${{index === 0 ? "selected" : ""}}>${{escapeHtml(item.part_name)}} · ${{escapeHtml(item.export_status || "cad-package")}}</option>`).join("")}}
                      </select>
                    </label>
                    <div class="stack" id="model-forge-details-content">
                      <div class="metric">Select a package to see its export details.</div>
                    </div>
                    <div class="inline-actions" id="model-forge-details-actions" style="margin-top:10px;flex-wrap:wrap;"></div>
                  </div>
                </div>
                <div class="model-forge-tab-panel" data-model-forge-panel="source">
                  <div class="model-forge-meta">
                    <div class="model-forge-meta-head">
                      <h3>OpenSCAD Source</h3>
                      <p>Keep the generated source visible for quick review, prompt tuning, and handoff into downstream fabrication steps.</p>
                    </div>
                    <pre class="model-forge-script" id="model-forge-script">No source loaded yet.</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>`;
      }} else if (packetId === "chronicle") {{
        heading = "Chronicle";
        content = renderChroniclePacketMarkup();
      }} else if (packetId === "workshop") {{
        heading = "Workshop Packet";
        content = renderWorkshopPacketMarkup(data);
      }} else if (packetId === "mission-control") {{
        heading = "Mission Control";
        const missionControl = data.mission_control || state.missionControl || {{}};
        const missions = Array.isArray(missionControl.active_missions) ? missionControl.active_missions : [];
        const selectedMission = missions.find((item) => item.mission_id === state.activeMissionId) || missions[0] || null;
        if (selectedMission?.mission_id) {{
          state.activeMissionId = selectedMission.mission_id;
        }}
        const summary = missionControl.summary || {{}};
        const missionCards = missions.length ? renderList(missions.map((item) => `
          <button
            type="button"
            class="ghost-toggle mission-control-select ${{item.mission_id === state.activeMissionId ? "active" : ""}}"
            data-mission-id="${{escapeHtml(item.mission_id || "")}}"
          >
            <strong>${{escapeHtml(item.title || "Mission")}}</strong>
            <br>${{escapeHtml(item.primary_domain || "general")}} · ${{escapeHtml(item.status || "active")}}
            <br><span class="muted">${{escapeHtml(item.brief || "")}}</span>
          </button>
        `)) : `<div class="empty">No active missions yet. Create one from this console.</div>`;
        const selectedActions = Array.isArray(selectedMission?.action_decisions) ? selectedMission.action_decisions : [];
        const selectedSubtasks = Array.isArray(selectedMission?.subtasks) ? selectedMission.subtasks : [];
        const selectedEvidence = Array.isArray(selectedMission?.evidence) ? selectedMission.evidence : [];
        const selectedApprovals = Array.isArray(selectedMission?.approvals_detail) ? selectedMission.approvals_detail : [];
        const selectedAgents = Array.isArray(selectedMission?.agent_profiles) ? selectedMission.agent_profiles : [];
        const selectedOutputs = Array.isArray(selectedMission?.outputs) ? selectedMission.outputs : [];
        const agentSociety = missionControl.agent_society || {{}};
        const societySummary = agentSociety.summary || {{}};
        const societyAgents = Array.isArray(agentSociety.agents) ? agentSociety.agents.slice(0, 6) : [];
        const societyLanes = Array.isArray(agentSociety.lanes) ? agentSociety.lanes.slice(0, 6) : [];
        content = `
          <div class="stack">
            <div class="packet-grid">
              ${{
                packetBlock("Mission Engine", `
                  <div class="metric"><strong>Active missions</strong> ${{escapeHtml(String(summary.active_missions || 0))}}</div>
                  <div class="metric"><strong>Pending approvals</strong> ${{escapeHtml(String(summary.pending_approvals || 0))}}</div>
                  <div class="metric"><strong>Task agents</strong> ${{escapeHtml(String(summary.task_agents || 0))}}</div>
                  <div class="metric"><strong>Promoted agents</strong> ${{escapeHtml(String(summary.promoted_agents || 0))}}</div>
                  <div class="settings-grid" style="margin-top: 14px;">
                    <label>
                      New family mission
                      <textarea id="mission-control-request" placeholder="Example: Keep the family ahead of tomorrow's storms, morning schedule, and outbound messages."></textarea>
                    </label>
                    <div class="inline-actions">
                      <button id="mission-control-create" type="button">Create Mission</button>
                    </div>
                  </div>
                `)
              }}
              ${{
                packetBlock("Agent Society", `
                  <div class="metric"><strong>Active agents</strong> ${{escapeHtml(String(societySummary.active_agents || 0))}}</div>
                  <div class="metric"><strong>Lead agents</strong> ${{escapeHtml(String(societySummary.lead_agents || 0))}}</div>
                  <div class="metric"><strong>Blocked agents</strong> ${{escapeHtml(String(societySummary.blocked_agents || 0))}}</div>
                  <div class="metric"><strong>Pending review agents</strong> ${{escapeHtml(String(societySummary.pending_review_agents || 0))}}</div>
                  <div class="metric"><strong>Inbox / outbox</strong> ${{escapeHtml(String(societySummary.inbox_items || 0))}} / ${{escapeHtml(String(societySummary.outbox_items || 0))}}</div>
                  <div class="metric"><strong>Hypotheses</strong> ${{escapeHtml(String(societySummary.hypotheses || 0))}}</div>
                  ${{societyAgents.length ? renderList(societyAgents.map((item) => `
                    <div>
                      <strong>${{escapeHtml(item.label || item.agent_id || "Agent")}}</strong>
                      <br>${{escapeHtml(item.primary_domain || "general")}} · lead ${{escapeHtml(String(item.lead_missions || 0))}}
                      <br><span class="muted">active ${{escapeHtml(String(item.active_tasks || 0))}} · blocked ${{escapeHtml(String(item.blocked_tasks || 0))}} · review ${{escapeHtml(String(item.pending_reviews || 0))}}</span>
                    </div>
                  `)) : `<div class="empty">No society activity is visible yet.</div>`}}
                `)
              }}
              ${{
                packetBlock("Stewardship Lanes", societyLanes.length ? renderList(societyLanes.map((item) => `
                  <div>
                    <strong>${{escapeHtml(item.name || item.lane_id || "Lane")}}</strong>
                    <br>agents ${{escapeHtml(String(item.total_agents || 0))}} · lead ${{escapeHtml(String(item.lead_agents || 0))}}
                    <br><span class="muted">active ${{escapeHtml(String(item.active_tasks || 0))}} · blocked ${{escapeHtml(String(item.blocked_tasks || 0))}} · review ${{escapeHtml(String(item.pending_reviews || 0))}}</span>
                  </div>
                `)) : `<div class="empty">No stewardship lanes are active right now.</div>`)
              }}
              ${{
                packetBlock("Active Dossiers", missionCards)
              }}
              ${{
                packetBlock("Trust Zones", renderList((missionControl.trust_zones || []).slice(0, 5).map((zone) => `
                  <div>
                    <strong>${{escapeHtml(zone.name || zone.zone_id || "Trust zone")}}</strong>
                    <br>${{escapeHtml(zone.approval_mode || "bounded-autonomy")}} · ${{escapeHtml(zone.status || "active")}}
                    <br><span class="muted">${{escapeHtml(zone.description || "")}}</span>
                  </div>
                `)))
              }}
              ${{
                packetBlock("Promotion Queue", (() => {{
                  const items = Array.isArray(data.governance?.promotion_recommendations) ? data.governance.promotion_recommendations : [];
                  if (!items.length) return `<div class="empty">No promotion recommendations are surfaced right now.</div>`;
                  return renderList(items.slice(0, 5).map((item) => `
                    <div>
                      <strong>${{escapeHtml(item.title || item.subject_id || "Recommendation")}}</strong>
                      <br>${{escapeHtml(item.current_stage || "observe")}} → ${{escapeHtml(item.target_stage || "stage_alert")}} · ${{escapeHtml(item.decision || "hold")}}
                      <br><span class="muted">${{escapeHtml(item.reason || item.summary || "")}}</span>
                    </div>
                  `));
                }})())
              }}
            </div>
            ${{
              selectedMission ? `
                <div class="packet-grid">
                  ${{
                    packetBlock("Selected Dossier", `
                      <div class="metric"><strong>${{escapeHtml(selectedMission.title || "Mission")}}</strong></div>
                      <div class="metric"><strong>Status</strong> ${{escapeHtml(selectedMission.status || "active")}}</div>
                      <div class="metric"><strong>Domain</strong> ${{escapeHtml(selectedMission.primary_domain || "general")}}</div>
                      <div class="metric"><strong>Trust zone</strong> ${{escapeHtml(selectedMission.trust_zone || "family-bmad.personal-local")}}</div>
                      <div class="metric"><strong>Autonomy</strong> ${{escapeHtml(selectedMission.autonomy_posture || "bounded-autonomy")}}</div>
                      <div class="metric"><strong>Family impact</strong> ${{escapeHtml((selectedMission.family_impact || []).join(" · ") || "No direct impact noted yet.")}}</div>
                      <div class="inline-actions" style="margin-top:10px;">
                        <button class="ghost-toggle mission-status-action" type="button" data-mission-id="${{escapeHtml(selectedMission.mission_id || "")}}" data-status="active">Set Active</button>
                        <button class="ghost-toggle mission-status-action" type="button" data-mission-id="${{escapeHtml(selectedMission.mission_id || "")}}" data-status="completed">Mark Complete</button>
                        <button class="ghost-toggle mission-status-action" type="button" data-mission-id="${{escapeHtml(selectedMission.mission_id || "")}}" data-status="blocked">Mark Blocked</button>
                      </div>
                    `)
                  }}
                  ${{
                    packetBlock("Delegated Agents", selectedAgents.length ? renderList(selectedAgents.map((item) => `
                      <div>
                        <strong>${{escapeHtml(item.label || item.agent_id || "Agent")}}</strong>
                        <br>${{escapeHtml(item.class_type || item.agent_class || "agent")}} · ${{escapeHtml(item.primary_domain || item.domain || "general")}}
                        <br><span class="muted">${{escapeHtml((item.mission_roles || []).join(", ") || item.purpose || "")}}</span>
                      </div>
                    `)) : `<div class="empty">No delegated agents recorded.</div>`)
                  }}
                  ${{
                    packetBlock("Action Resolutions", selectedActions.length ? renderList(selectedActions.map((item) => `
                      <div>
                        <strong>${{escapeHtml(item.action_type || "action")}}</strong> · ${{escapeHtml(item.resolution || "review")}}
                        <br>${{escapeHtml(item.trust_zone || "")}}
                        <br><span class="muted">${{escapeHtml(item.rationale || "")}}</span>
                      </div>
                    `)) : `<div class="empty">No action decisions recorded.</div>`)
                  }}
                  ${{
                    packetBlock("Subtasks", selectedSubtasks.length ? renderList(selectedSubtasks.map((item) => `
                      <div>
                        <strong>${{escapeHtml(item.title || "Subtask")}}</strong> · ${{escapeHtml(item.status || "active")}}
                        <br>${{escapeHtml(item.owner_agent || "JARVIS")}} · ${{escapeHtml(item.domain || "general")}}
                        <br><span class="muted">${{escapeHtml(item.description || "")}}</span>
                      </div>
                    `)) : `<div class="empty">No subtasks recorded yet.</div>`)
                  }}
                  ${{
                    packetBlock("Evidence", selectedEvidence.length ? renderList(selectedEvidence.slice(0, 8).map((item) => `
                      <div>
                        <strong>${{escapeHtml(item.title || "Evidence")}}</strong>
                        <br>${{escapeHtml(item.source_agent || item.source_system || "source")}} · ${{escapeHtml(item.kind || "signal")}}
                        <br><span class="muted">${{escapeHtml(item.summary || item.detail || "")}}</span>
                      </div>
                    `)) : `<div class="empty">No evidence captured yet.</div>`)
                  }}
                  ${{
                    packetBlock("Approvals + Outputs", `
                      <div class="metric"><strong>Approvals</strong> ${{escapeHtml(String(selectedApprovals.length || 0))}}</div>
                      ${{selectedApprovals.length ? renderList(selectedApprovals.map((item) => `
                        <div><strong>${{escapeHtml(item.status || "pending")}}</strong><br>${{escapeHtml(item.request || "")}}</div>
                      `)) : `<div class="empty">No approvals are attached to this mission.</div>`}}
                      <div class="metric" style="margin-top:12px;"><strong>Outputs</strong> ${{escapeHtml(String(selectedOutputs.length || 0))}}</div>
                      ${{selectedOutputs.length ? renderList(selectedOutputs.map((item) => `
                        <div><strong>${{escapeHtml(item.title || item.kind || "Output")}}</strong><br>${{escapeHtml(item.summary || "")}}</div>
                      `)) : `<div class="empty">No outputs have been committed yet.</div>`}}
                    `)
                  }}
                </div>
              ` : `` 
            }}
          </div>`;
      }} else if (packetId === "catalyst") {{
        heading = "Catalyst";
        const catalystLive = data.catalyst_overview?.live_workspace || {{}};
        const lifecycle = data.pipeline_state?.work_lifecycle || data.work_lifecycle || {{}};
        const recentWork = Array.isArray(lifecycle.records) ? lifecycle.records.slice(0, 6) : [];
        const reviewInbox = Array.isArray(data.pipeline_state?.review_inbox) ? data.pipeline_state.review_inbox.slice(0, 6) : [];
        const liveSummary = [
          catalystLive.calendar?.items?.length ? `Calendar ${{catalystLive.calendar.items.length}}` : "",
          catalystLive.email?.stats?.total ? `Email ${{catalystLive.email.stats.total}}` : "",
          catalystLive.tasks?.stats?.openCount ? `Tasks ${{catalystLive.tasks.stats.openCount}} open` : "",
          catalystLive.projects?.stats?.totalCount ? `Projects ${{catalystLive.projects.stats.totalCount}}` : "",
        ].filter(Boolean).join(" · ");
        content = `
          <div class="stack">
            <div class="packet-grid">
              ${{
                packetBlock(
                  "Work Lifecycle",
                  `
                    <div class="metric"><strong>Open reviews</strong> ${{escapeHtml(String(lifecycle.summary?.open_reviews || 0))}}</div>
                    <div class="metric"><strong>Staged hypotheses</strong> ${{escapeHtml(String(lifecycle.summary?.staged_hypotheses || 0))}}</div>
                    <div class="metric"><strong>Ready plans</strong> ${{escapeHtml(String(lifecycle.summary?.ready_plans || 0))}}</div>
                    <div class="metric"><strong>Recent outcomes</strong> ${{escapeHtml(String(lifecycle.summary?.recent_outcomes || 0))}}</div>
                    ${{renderLifecycleWorkItems(recentWork, {{ transitionLimit: 5, emptyLabel: "No Catalyst work has moved through the lifecycle yet." }})}}
                  `
                )
              }}
              ${{
                packetBlock(
                  "Review Queue",
                  reviewInbox.length
                    ? renderList(reviewInbox.map((item) => `
                      <div>
                        <strong>${{escapeHtml(item.title || "Work item")}}</strong>
                        <br>${{escapeHtml(formatLifecycleStage(item.stage || "review"))}} · ${{escapeHtml(formatLifecycleStatus(item.status || "pending"))}}
                        <br><span class="muted">${{escapeHtml(item.owner_agent || "JARVIS")}} · ${{escapeHtml(String(item.lane || "").replace(/-/g, " "))}}</span>
                      </div>
                    `))
                    : `<div class="empty">No items are waiting in the review queue right now.</div>`
                )
              }}
              ${{
                packetBlock(
                  "Recent Lifecycle Actions",
                  renderRecentLifecycleActions()
                )
              }}
            </div>
            <div class="chronicle-workspace-shell">
            <div class="chronicle-handoff-bar">
              <div class="chronicle-handoff-copy">
                <strong>Sent to Catalyst</strong>
                <span id="catalyst-handoff-summary">${{escapeHtml(liveSummary || "Preparing Catalyst…")}}</span>
              </div>
              <div class="chronicle-handoff-actions">
                <button type="button" id="catalyst-send-button">Send to Catalyst</button>
                <button type="button" class="ghost-toggle" id="catalyst-open-app">Open Catalyst App</button>
              </div>
            </div>
            <div class="workspace-frame">
              <iframe id="catalyst-workspace-frame" title="Catalyst Workspace" src="about:blank"></iframe>
            </div>
          </div>
          </div>`;
      }} else if (packetId === "approvals") {{
        heading = "Approval Queue";
        content = `
          <div class="packet-grid">
            ${{
              packetBlock("Pending", renderList((data.explainability?.approval_history || []).filter((item) => item.status === "pending").map((item) => `<div><strong>${{escapeHtml(item.actor)}}</strong><br>${{escapeHtml(item.request)}}</div>`)))
            }}
            ${{
              packetBlock("Explainability", renderList((data.explainability?.latest_reasons || []).map((item) => `<div><strong>${{escapeHtml(item.module)}}</strong><br>${{escapeHtml(item.rationale)}}</div>`)))
            }}
            ${{
              packetBlock("Autonomy Audit", `
                <div class="metric"><strong>Total actions</strong> ${{escapeHtml(String(data.explainability?.assistant_action_summary?.total || 0))}}</div>
                <div class="metric"><strong>Automatic</strong> ${{escapeHtml(String(data.explainability?.assistant_action_summary?.automatic || 0))}} · successful ${{escapeHtml(String(data.explainability?.assistant_action_summary?.successful || 0))}}</div>
                ${{renderList((data.explainability?.assistant_actions || []).slice(0, 6).map((item) => `<div><strong>${{escapeHtml(item.action_class || item.action || "action")}}</strong> · ${{escapeHtml(item.domain || "general")}} · ${{escapeHtml(item.confidence || "medium")}} confidence<br>${{escapeHtml(item.why_now || item.policy_basis || "")}}<br><span class="muted">${{escapeHtml(item.result_summary || "")}}</span></div>`)) || `<div class="empty">No recent autonomous actions have been recorded yet.</div>`}}
              `)
            }}
          </div>`;
      }} else if (packetId === "tasks") {{
        heading = "Assistant Core";
        const openLoops = data.open_loops || {{}};
        const queueItems = openLoops.items || [];
        const proactive = openLoops.proactive_surface || [];
        const lanes = openLoops.task_lanes || [];
        const summary = openLoops.summary || {{}};
        const renderTaskActions = (item) => {{
          const actions = item.available_actions || [];
          if (!actions.length) return `<div class="empty">No direct action available yet.</div>`;
          return `<div class="inline-actions">${{actions.map((action) => `
            <button
              type="button"
              class="ghost-toggle task-queue-action"
              data-domain="${{escapeHtml(item.domain || "")}}"
              data-item-id="${{escapeHtml(item.item_id || "")}}"
              data-action="${{escapeHtml(action.id || "")}}"
            >${{escapeHtml(action.label || action.id || "Act")}}</button>
          `).join("")}}</div>`;
        }};
        content = `
          <div class="packet-grid">
            ${{
              packetBlock("Open Loops", `
                <div class="metric"><strong>Total</strong> ${{escapeHtml(String(summary.total || 0))}}</div>
                <div class="metric"><strong>Waiting on you</strong> ${{escapeHtml(String(summary.waiting_on_you || 0))}}</div>
                <div class="metric"><strong>Queued</strong> ${{escapeHtml(String(summary.staged || 0))}}</div>
                <div class="metric"><strong>Needs revisit</strong> ${{escapeHtml(String(summary.needs_revisit || 0))}}</div>
                <div class="metric"><strong>Deferred</strong> ${{escapeHtml(String(summary.hidden_deferred || 0))}}</div>
                ${{renderList(queueItems.slice(0, 8).map((item) => `
                  <div>
                    <strong>${{escapeHtml(item.title || item.kind || "Open loop")}}</strong>
                    <br>${{escapeHtml(item.domain || "general")}} · ${{escapeHtml(item.status || "open")}} · ${{escapeHtml(item.owner_agent || "JARVIS")}}
                    <br><span class="muted">${{escapeHtml(item.next_action || "")}}</span>
                    <br><span class="muted">Review by: ${{escapeHtml(item.next_review_at || "not scheduled")}}</span>
                    <br><span class="muted">Autonomy: ${{escapeHtml(item.auto_execution?.summary || "Review required.")}}</span>
                    ${{renderTaskActions(item)}}
                  </div>
                `))}}
              `)
            }}
            ${{
              packetBlock("Proactive Surface", renderList(proactive.map((item) => `
                <div>
                  <strong>${{escapeHtml(item.title || "Open loop")}}</strong>
                  <br>${{escapeHtml(item.proactive_reason || item.summary || "")}}
                </div>
              `)) || `<div class="empty">No immediate resurfacing items.</div>`)
            }}
            ${{
              packetBlock("Task Lanes", renderList(lanes.map((item) => `
                <div>
                  <strong>${{escapeHtml(item.owner_agent || "JARVIS")}}</strong> · ${{escapeHtml(item.domain || "general")}}
                  <br>${{escapeHtml(item.lane || "")}}
                  <br><span class="muted">${{escapeHtml(item.approval_threshold?.summary || "")}}</span>
                </div>
              `)))
            }}
            ${{
              packetBlock("Autonomy Audit", `
                <div class="metric"><strong>Recent autonomous actions</strong> ${{escapeHtml(String(data.explainability?.assistant_action_summary?.total || 0))}}</div>
                <div class="metric"><strong>Automatic</strong> ${{escapeHtml(String(data.explainability?.assistant_action_summary?.automatic || 0))}} · successful ${{escapeHtml(String(data.explainability?.assistant_action_summary?.successful || 0))}}</div>
                ${{renderList((data.explainability?.assistant_actions || []).slice(0, 5).map((item) => `<div><strong>${{escapeHtml(item.action_class || item.action || "action")}}</strong> · ${{escapeHtml(item.domain || "general")}} · ${{escapeHtml(item.cadence_phase || "watch")}}<br>${{escapeHtml(item.policy_basis || item.detail || "")}}<br><span class="muted">${{escapeHtml(item.result_summary || "")}}</span></div>`)) || `<div class="empty">No recent autonomous actions have been recorded yet.</div>`}}
              `)
            }}
          </div>`;
      }} else if (packetId === "settings") {{
        heading = "Settings";
        const settings = state.voiceSettings || {{}};
        const options = state.voiceOptions || {{}};
        const accountRegistry = state.accountRegistry || {{}};
        const identity = state.identity || {{}};
        const locationSettings = state.locationSettings || {{}};
        const stackStatus = options.stack_status || settings.stack_status || {{}};
        const googleWorkspace = data.google_workspace || {{}};
        const googleClientSecret = googleWorkspace.client_secret || {{}};
        const personalAccounts = accountRegistry.accounts || [];
        const identityMembers = identity.members || [];
        const identityDevices = identity.devices || [];
        const identityService = identity.service || {{}};
        const savedLocations = locationSettings.saved_locations || [];
        const activeLocation = locationSettings.active_location || {{}};
        const deviceLocation = locationSettings.device_location || null;
        const activeCoordinates = activeLocation.latitude != null && activeLocation.longitude != null
          ? `${{activeLocation.latitude}}, ${{activeLocation.longitude}}`
          : "--";
        const savedLocationsMarkup = savedLocations.length ? savedLocations.map((item) => `
          <div class="metric">
            <strong>${{escapeHtml(item.label || item.geography || "Location")}}</strong><br>
            ${{escapeHtml(item.geography || "")}}
            <div class="inline-actions" style="margin-top:8px;">
              <button class="location-use" type="button" data-location-id="${{escapeHtml(item.id)}}">${{item.id === locationSettings.preferred_location_id ? "Active" : "Use"}}</button>
            </div>
          </div>
        `).join("") : '<div class="metric">No saved locations yet.</div>';
        content = `
          <div class="packet-grid">
            ${{
              packetBlock("Layout Freedom", `
                <div class="settings-grid">
                  <label class="toggle-row">
                    <input id="layout-edit-mode" type="checkbox" ${{state.layoutEditMode ? "checked" : ""}}>
                    Allow dragging and resizing the main shell panels and open modals
                  </label>
                  <div class="settings-note" id="layout-settings-status">
                    Turn this on to move and resize the visible shell. Saved layouts collapse back to the responsive default on smaller windows, then return when the window is large enough again.
                  </div>
                  <div class="inline-actions">
                    <button id="save-layout-settings" type="button">Save Layout Mode</button>
                    <button id="reset-layout-placements" class="ghost-toggle" type="button">Reset Saved View</button>
                  </div>
                </div>
              `)
            }}
            ${{
              packetBlock("Voice Output", `
                <div class="settings-grid">
                  <label>
                    TTS Provider
                    <select id="settings-tts-provider">
                      ${{renderSelectOptions(options.providers || [], settings.tts_provider || "auto")}}
                    </select>
                  </label>
                  <label>
                    ElevenLabs Voice
                    <select id="settings-elevenlabs-voice">
                      ${{renderSelectOptions(options.elevenlabs || [], settings.elevenlabs_voice || "", "No ElevenLabs voices found")}}
                    </select>
                  </label>
                  <label>
                    Piper Voice Model
                    <select id="settings-piper-model">
                      ${{renderSelectOptions(options.piper || [], settings.piper_model_path || "", "No Piper voices found")}}
                    </select>
                  </label>
                  <label>
                    Piper Speaker
                    <input id="settings-piper-speaker" value="${{escapeHtml(settings.piper_speaker || "")}}" placeholder="Default speaker">
                  </label>
                  <label>
                    Preview Phrase
                    <input id="settings-preview-text" value="Good evening, sir. Voice calibration complete.">
                  </label>
                  <div class="inline-actions">
                    <button id="save-voice-settings" type="button">Save Voice Settings</button>
                    <button id="preview-voice-settings" class="ghost-toggle" type="button">Save + Preview</button>
                  </div>
                  <div class="settings-note" id="voice-settings-status">${{escapeHtml(state.settingsMessage || "Save voice settings here, then preview through the current voice route.")}}</div>
                </div>`)
            }}
            ${{
              packetBlock("Current Selection", `
                <div class="stack">
                  <div class="metric"><strong>Configured source</strong> ${{escapeHtml(settings.selected_provider_label || "--")}}</div>
                  <div class="metric"><strong>Configured readiness</strong> ${{escapeHtml(selectedVoiceConfiguredReadiness(stackStatus))}}</div>
                  <div class="metric"><strong>Last live readiness</strong> ${{escapeHtml(selectedVoiceLiveReadiness(stackStatus))}}</div>
                  <div class="metric"><strong>Last live blocker</strong> ${{escapeHtml(selectedVoiceLiveBlocker(stackStatus))}}</div>
                  <div class="metric"><strong>Last live fallback</strong> ${{escapeHtml(selectedVoiceLiveFallback(stackStatus))}}</div>
                  <div class="metric"><strong>ElevenLabs</strong> ${{escapeHtml(settings.selected_elevenlabs_label || "--")}}</div>
                  <div class="metric"><strong>Piper</strong> ${{escapeHtml(settings.selected_piper_label || "--")}}</div>
                  <div class="metric"><strong>Order</strong> ${{escapeHtml((stackStatus.tts_order || []).join(" → ") || "--")}}</div>
                </div>`)
            }}
            ${{
              packetBlock("Locations", `
                <div class="settings-grid">
                  <div class="settings-note" id="location-settings-status">Save geography for weather and context, or capture your current device location.</div>
                  <div class="stack">
                    <div class="metric"><strong>Active</strong> ${{escapeHtml(activeLocation.label || "--")}}</div>
                    <div class="metric"><strong>Geography</strong> ${{escapeHtml(activeLocation.geography || "--")}}</div>
                    <div class="metric"><strong>Coordinates</strong> ${{escapeHtml(activeCoordinates)}}</div>
                    <div class="metric"><strong>Device</strong> ${{escapeHtml(deviceLocation ? (deviceLocation.geography || deviceLocation.label || "--") : "Not captured yet")}}</div>
                  </div>
                  <div class="stack">
                    ${{savedLocationsMarkup}}
                  </div>
                  <label>
                    Label
                    <input id="location-label" placeholder="Alexandria Home">
                  </label>
                  <label>
                    Geography
                    <input id="location-geography" placeholder="Alexandria, KY">
                  </label>
                  <label>
                    Latitude
                    <input id="location-latitude" placeholder="38.9598">
                  </label>
                  <label>
                    Longitude
                    <input id="location-longitude" placeholder="-84.3877">
                  </label>
                  <label>
                    Notes
                    <input id="location-notes" placeholder="Use for weather and timing.">
                  </label>
                  <div class="inline-actions">
                    <button id="save-location" type="button">Save Location</button>
                    <button id="use-device-location" class="ghost-toggle" type="button">Use Current Location</button>
                  </div>
                </div>`)
            }}
            ${{
              packetBlock("Provider Readiness", `
                <div class="stack">
                  <div class="metric"><strong>Piper Binary</strong> ${{stackStatus.piper_binary_ready ? "ready" : "missing"}}</div>
                  <div class="metric"><strong>Piper Model</strong> ${{stackStatus.piper_ready ? "ready" : "not ready"}}</div>
                  <div class="metric"><strong>LocalAI</strong> ${{stackStatus.localai_healthy ? "healthy" : "standby"}}</div>
                  <div class="metric"><strong>ElevenLabs</strong> ${{stackStatus.elevenlabs_ready ? "ready" : "missing key"}}</div>
                </div>`)
            }}
            ${{
              packetBlock("Piper Assets", renderList((options.piper || []).map((item) => `<div><strong>${{escapeHtml(item.label)}}</strong><br>${{escapeHtml(item.detail || item.path || "")}}</div>`)))
            }}
            ${{
              packetBlock("Page Review", `
                <div class="settings-grid">
                  <div class="settings-note" id="page-review-status">
                    Review the active page one element at a time, capture feedback, and keep those notes with the page they belong to.
                  </div>
                  <div class="stack">
                    <div class="metric"><strong>Active Page</strong> ${{escapeHtml(REVIEWABLE_PAGES.find(([id]) => id === currentReviewPageId())?.[1] || currentReviewPageId())}}</div>
                    <div class="metric"><strong>Review State</strong> ${{isReviewEnabledForPage(currentReviewPageId()) ? "enabled" : "disabled"}}</div>
                  </div>
                  <div class="stack">
                    ${{
                      REVIEWABLE_PAGES.map(([pageId, label]) => `
                        <div class="metric page-review-toggle-row">
                          <strong>${{escapeHtml(label)}}</strong>
                          <br>
                          <button
                            type="button"
                            class="${{state.holoReview.pageSettings?.[pageId]?.enabled ? "ghost-toggle" : ""}} page-review-toggle"
                            data-review-page="${{escapeHtml(pageId)}}"
                            data-review-enabled="${{state.holoReview.pageSettings?.[pageId]?.enabled ? "true" : "false"}}"
                          >
                            ${{state.holoReview.pageSettings?.[pageId]?.enabled ? "Review On" : "Review Off"}}
                          </button>
                        </div>
                      `).join("")
                    }}
                  </div>
                </div>`)
            }}
            ${{
              packetBlock("Family Identity", `
                <div class="settings-grid">
                  <div class="settings-note">
                    Give each person a distinct long-lived profile so JARVIS can learn preferences, tone, and anticipation patterns without flattening the household into one blob.
                  </div>
                  <div class="stack">
                    ${{
                      identityMembers.length
                        ? identityMembers.map((member) => `
                          <div class="metric">
                            <strong>${{escapeHtml(member.display_name)}}</strong>
                            · ${{escapeHtml(member.trust_level || "standard")}}
                            · ${{escapeHtml(member.privacy_boundary || "personal")}}
                            <br>
                            Tone: ${{escapeHtml(member.preferred_tone || "--")}}
                            <br>
                            Voice: ${{escapeHtml(member.preferred_voice || "--")}} · Aliases: ${{escapeHtml((member.voice_aliases || []).join(", ") || "none")}}
                            <br>
                            Rooms: ${{escapeHtml((member.primary_rooms || []).join(", ") || "--")}} · Morning: ${{escapeHtml(member.morning_room || "--")}}
                            <br>
                            Devices: ${{escapeHtml((member.device_ids || []).length ? member.device_ids.join(", ") : "none bound")}}
                          </div>
                        `).join("")
                        : `<div class="metric">No household identity profiles loaded.</div>`
                    }}
                  </div>
                  <label>
                    Person
                    <select id="identity-member-user-id">
                      ${{renderSelectOptions(identity.owners || [], "", "No household users found")}}
                    </select>
                  </label>
                  <label>
                    Preferred tone
                    <input id="identity-member-tone" placeholder="calm and direct">
                  </label>
                  <label>
                    Briefing style
                    <input id="identity-member-briefing-style" placeholder="first-light">
                  </label>
                  <label>
                    Anticipation style
                    <input id="identity-member-anticipation-style" placeholder="quietly proactive">
                  </label>
                  <label>
                    Preferred voice
                    <input id="identity-member-voice" placeholder="elevenlabs, piper, calm-low">
                  </label>
                  <label>
                    Voice aliases
                    <input id="identity-member-voice-aliases" placeholder="dad, daddy, mom, rebekah">
                  </label>
                  <label>
                    Primary rooms
                    <input id="identity-member-primary-rooms" placeholder="office, kitchen, workshop">
                  </label>
                  <label>
                    Morning room
                    <input id="identity-member-morning-room" placeholder="kitchen">
                  </label>
                  <label>
                    Privacy boundary
                    <input id="identity-member-boundary" placeholder="personal, child, shared">
                  </label>
                  <label>
                    Trust level
                    <select id="identity-member-trust">
                      ${{renderSelectOptions(identity.trust_levels || [], "trusted")}}
                    </select>
                  </label>
                  <label>
                    Notes
                    <textarea id="identity-member-notes" placeholder="What should JARVIS learn carefully about this person?"></textarea>
                  </label>
                  <div class="inline-actions">
                    <button id="save-identity-member" type="button">Save Person Profile</button>
                    <button id="refresh-persona-snapshot" class="ghost-toggle" type="button">Refresh Persona Snapshot</button>
                  </div>
                  <div class="stack" id="identity-member-adaptation">
                    <div class="metric">Select a person to see the current adaptive persona snapshot.</div>
                  </div>
                  <div class="stack" id="identity-member-learning-review">
                    <div class="metric">Learning review will appear here for the selected person.</div>
                  </div>
                  <div class="settings-note" id="identity-member-status">Each family member should have a separate adaptive profile.</div>
                </div>`)
            }}
            ${{
              packetBlock("Device Registry", `
                <div class="settings-grid">
                  <div class="settings-note">
                    Bind each phone, tablet, display, or browser to a person or mark it shared. This is the lock-in layer that lets JARVIS know who it is serving before the conversation starts.
                  </div>
                  <div class="stack">
                    ${{
                      identityDevices.length
                        ? identityDevices.map((device) => `
                          <div class="metric">
                            <strong>${{escapeHtml(device.label)}}</strong>
                            · ${{escapeHtml(device.device_type || "device")}}
                            · ${{device.shared ? "shared" : escapeHtml(device.owner_user_id || "unassigned")}}
                            <br>
                            Trust: ${{escapeHtml(device.trust_level || "trusted")}} · Room: ${{escapeHtml(device.room || "--")}}
                            <br>
                            Last actor: ${{escapeHtml(device.last_actor_id || "--")}} · Source: ${{escapeHtml(device.last_actor_source || "--")}}
                            <br>
                            Suggested default: ${{escapeHtml(device.suggested_default_actor_id || "--")}}
                            <br>
                            Last seen: ${{escapeHtml(device.last_seen_at || "never")}}
                          </div>
                        `).join("")
                        : `<div class="metric">No devices registered yet.</div>`
                    }}
                  </div>
                  <label>
                    Device id
                    <input id="identity-device-id" value="${{escapeHtml(state.sessionIdentity?.device?.device_id || state.shellDeviceId || "")}}" placeholder="browser or hardware id">
                  </label>
                  <label>
                    Label
                    <input id="identity-device-label" value="${{escapeHtml(state.sessionIdentity?.device?.label || "")}}" placeholder="Chris iPad">
                  </label>
                  <label>
                    Device type
                    <select id="identity-device-type">
                      ${{renderSelectOptions(identity.device_types || [], "browser")}}
                    </select>
                  </label>
                  <label>
                    Owner
                    <select id="identity-device-owner">
                      ${{renderSelectOptions([{{ id: "", label: "Unassigned" }}].concat(identity.owners || []), state.sessionIdentity?.device?.owner_user_id || "")}}
                    </select>
                  </label>
                  <label>
                    Default actor
                    <select id="identity-device-default-actor">
                      ${{renderSelectOptions([{{ id: "", label: "No default" }}].concat(identity.owners || []), state.sessionIdentity?.device?.default_actor_id || "")}}
                    </select>
                  </label>
                  <label>
                    Trust level
                    <select id="identity-device-trust">
                      ${{renderSelectOptions(identity.trust_levels || [], state.sessionIdentity?.device?.trust_level || "trusted")}}
                    </select>
                  </label>
                  <label>
                    Room
                    <input id="identity-device-room" value="${{escapeHtml(state.sessionIdentity?.device?.room || document.getElementById("room")?.value || "")}}" placeholder="office">
                  </label>
                  <label>
                    Notes
                    <textarea id="identity-device-notes" placeholder="Personal, shared, child-safe, kitchen display, workshop tablet..."></textarea>
                  </label>
                  <label class="toggle-row">
                    <input id="identity-device-shared" type="checkbox" ${{state.sessionIdentity?.device?.shared ? "checked" : ""}}>
                    Shared device
                  </label>
                  <label class="toggle-row">
                    <input id="identity-device-always-available" type="checkbox" ${{state.sessionIdentity?.device?.always_available ? "checked" : ""}}>
                    Always available endpoint
                  </label>
                  <div class="inline-actions">
                    <button id="save-identity-device" type="button">Save Device Binding</button>
                    <button id="bind-current-device" class="ghost-toggle" type="button">Bind Current Browser</button>
                  </div>
                  <label>
                    Shared-device actor for this session
                    <select id="identity-session-actor">
                      ${{renderSelectOptions([{{ id: "", label: "Choose person for this session" }}].concat(identity.owners || []), state.sessionActorOverride || state.sessionIdentity?.resolved_actor_id || "")}}
                    </select>
                  </label>
                  <div class="inline-actions">
                    <button id="apply-session-actor" class="ghost-toggle" type="button">Use For This Session</button>
                    <button id="clear-session-actor" class="ghost-toggle" type="button">Clear Session Override</button>
                  </div>
                  <div class="settings-note" id="identity-device-status">Bind this browser or device to a person, or mark it shared.</div>
                </div>`)
            }}
            ${{
              packetBlock("Always-On Service", `
                <div class="settings-grid">
                  <div class="settings-note">
                    JARVIS should live as infrastructure. Track the local household host, the Hetzner and Cloudflare edge, and whether boot-time launch plus watchdog behavior are really in place.
                  </div>
                  <div class="stack">
                    <div class="metric"><strong>Deployment</strong> ${{escapeHtml(identityService.mode_label || "Hybrid household plus hosted edge")}}</div>
                    <div class="metric"><strong>Host</strong> ${{escapeHtml(identityService.host_label || "Primary JARVIS host")}}</div>
                    <div class="metric"><strong>LAN URL</strong> ${{escapeHtml(identityService.lan_url || window.location.origin)}}</div>
                    <div class="metric"><strong>Hostname</strong> ${{escapeHtml(identityService.hostname || "jarvis.local")}}</div>
                    <div class="metric"><strong>Hosted URL</strong> ${{escapeHtml(identityService.hosted_base_url || "https://jarvis.teambinion.org")}}</div>
                    <div class="metric"><strong>Edge</strong> ${{escapeHtml(identityService.edge_provider || "Cloudflare Tunnel")}} · ${{identityService.cloudflare_access_enabled !== false ? "Access protected" : "open"}}</div>
                    <div class="metric"><strong>Launch on boot</strong> ${{identityService.launch_on_boot ? "enabled" : "not yet"}}</div>
                  </div>
                  <div class="stack" id="runtime-service-status">
                    <div class="metric">Runtime service status is loading…</div>
                  </div>
                  <label>
                    Deployment mode
                    <select id="identity-service-deployment-mode">
                      ${{renderSelectOptions([
                        {{ id: "hybrid", label: "Hybrid household + hosted edge" }},
                        {{ id: "local", label: "Local household only" }},
                        {{ id: "hosted", label: "Hosted edge only" }},
                      ], identityService.deployment_mode || "hybrid")}}
                    </select>
                  </label>
                  <label>
                    Host label
                    <input id="identity-service-host-label" value="${{escapeHtml(identityService.host_label || "Primary JARVIS host")}}">
                  </label>
                  <label>
                    Host type
                    <input id="identity-service-host-type" value="${{escapeHtml(identityService.host_type || "desktop")}}" placeholder="desktop, mac-mini, server">
                  </label>
                  <label>
                    LAN URL
                    <input id="identity-service-lan-url" value="${{escapeHtml(identityService.lan_url || window.location.origin)}}">
                  </label>
                  <label>
                    Hostname
                    <input id="identity-service-hostname" value="${{escapeHtml(identityService.hostname || "jarvis.local")}}">
                  </label>
                  <label>
                    Hosted host label
                    <input id="identity-service-hosted-host-label" value="${{escapeHtml(identityService.hosted_host_label || "Hetzner family stack")}}">
                  </label>
                  <label>
                    Hosted provider
                    <input id="identity-service-hosted-provider" value="${{escapeHtml(identityService.hosted_provider || "Hetzner")}}">
                  </label>
                  <label>
                    Hosted base URL
                    <input id="identity-service-hosted-base-url" value="${{escapeHtml(identityService.hosted_base_url || "https://jarvis.teambinion.org")}}">
                  </label>
                  <label>
                    Remote admin host
                    <input id="identity-service-remote-admin-host" value="${{escapeHtml(identityService.remote_admin_host || "")}}" placeholder="root@server or host only">
                  </label>
                  <label>
                    Remote admin user
                    <input id="identity-service-remote-admin-user" value="${{escapeHtml(identityService.remote_admin_user || "root")}}">
                  </label>
                  <label>
                    Edge provider
                    <input id="identity-service-edge-provider" value="${{escapeHtml(identityService.edge_provider || "Cloudflare Tunnel")}}">
                  </label>
                  <label>
                    Compose project
                    <input id="identity-service-compose-project" value="${{escapeHtml(identityService.compose_project || "jarvis-family")}}">
                  </label>
                  <label>
                    Notes
                    <textarea id="identity-service-notes" placeholder="How should this host behave as an always-on service?">${{escapeHtml(identityService.notes || "")}}</textarea>
                  </label>
                  <label class="toggle-row">
                    <input id="identity-service-always-on" type="checkbox" ${{identityService.always_on_enabled ? "checked" : ""}}>
                    Always-on host enabled
                  </label>
                  <label class="toggle-row">
                    <input id="identity-service-launch-on-boot" type="checkbox" ${{identityService.launch_on_boot ? "checked" : ""}}>
                    Launch on boot
                  </label>
                  <label class="toggle-row">
                    <input id="identity-service-watchdog" type="checkbox" ${{identityService.watchdog_enabled ? "checked" : ""}}>
                    Watchdog enabled
                  </label>
                  <label class="toggle-row">
                    <input id="identity-service-cloudflare-access" type="checkbox" ${{identityService.cloudflare_access_enabled !== false ? "checked" : ""}}>
                    Cloudflare Access enforced
                  </label>
                  <label class="toggle-row">
                    <input id="identity-service-tunnel-enabled" type="checkbox" ${{identityService.tunnel_enabled !== false ? "checked" : ""}}>
                    Tunnel enabled
                  </label>
                  <div class="inline-actions">
                    <button id="save-identity-service" type="button">Save Service Plan</button>
                  </div>
                  <div class="settings-note" id="identity-service-status">Track the hybrid host plan here, then use <code>ops/install_launchd_services.sh</code> for local boot posture and <code>deploy/deploy.sh</code> for the Hetzner and Cloudflare hosted edge.</div>
                </div>`)
            }}
            ${{
              packetBlock("Google Workspace", `
                <div class="settings-grid">
                  <div class="settings-note">
                    Gmail and Google Calendar use Google OAuth, not an email password or a simple API key. Save the shared OAuth client once, then connect each person's Google account separately.
                  </div>
                  <div class="stack">
                    <div class="metric"><strong>Client JSON</strong> ${{googleClientSecret.present ? "saved" : "missing"}}</div>
                    <div class="metric"><strong>Client Type</strong> ${{escapeHtml(googleClientSecret.client_type || "--")}}</div>
                    <div class="metric"><strong>Client Id Tail</strong> ${{escapeHtml(googleClientSecret.client_id_tail || "--")}}</div>
                  </div>
                  <label>
                    Google OAuth client JSON
                    <textarea id="google-client-secret-json" placeholder='{{ "installed": {{ ... }} }} or {{ "web": {{ ... }} }}'></textarea>
                  </label>
                  <div class="inline-actions">
                    <button id="save-google-client-secret" type="button">Save Google Client</button>
                    <button id="launch-google-connect" class="ghost-toggle" type="button">${{googleClientSecret.present ? "Open Google Login" : "Save Then Connect"}}</button>
                  </div>
                  <div class="settings-note" id="google-settings-status">Paste the client JSON once, then continue to Google login.</div>
                </div>`)
            }}
            ${{
              packetBlock("Personal Accounts", `
                <div class="settings-grid">
                  <div class="settings-note">
                    Each household member can have separate mail and calendar identities. Google is wired through Google OAuth. Outlook is wired through Microsoft Graph once the JARVIS_MICROSOFT_* values are present in your local .env.
                  </div>
                  <div class="stack">
                    ${{
                      personalAccounts.length
                        ? personalAccounts.map((account) => `
                          <div class="metric">
                            <strong>${{escapeHtml(account.label || account.owner_display_name)}}</strong>
                            · ${{escapeHtml(account.owner_display_name || "")}}
                            · ${{escapeHtml(account.provider || "")}}
                            · ${{escapeHtml(account.service_scope || "")}}
                            <br>
                            ${{escapeHtml(account.login_hint || "No login hint saved")}}
                            <br>
                            Status: ${{escapeHtml(account.connection?.detail || account.status || "planned")}}
                            <div class="inline-actions" style="margin-top:8px;">
                              <button class="account-connect" type="button" data-account-id="${{escapeHtml(account.account_id)}}">${{account.provider === "google" ? "Connect Google" : (account.provider === "outlook" ? "Connect Outlook" : "Provider Setup Pending")}}</button>
                              <button class="ghost-toggle account-disconnect" type="button" data-account-id="${{escapeHtml(account.account_id)}}"${{account.provider === "google" || account.provider === "outlook" ? "" : " disabled"}}>Disconnect</button>
                            </div>
                          </div>
                        `).join("")
                        : `<div class="metric">No personal accounts saved yet.</div>`
                    }}
                  </div>
                  <label>
                    Owner
                    <select id="account-owner-user-id">
                      ${{renderSelectOptions(accountRegistry.owners || [], "", "No household users found")}}
                    </select>
                  </label>
                  <label>
                    Provider
                    <select id="account-provider">
                      ${{renderSelectOptions(accountRegistry.providers || [], "google")}}
                    </select>
                  </label>
                  <label>
                    Services
                    <select id="account-service-scope">
                      ${{renderSelectOptions(accountRegistry.services || [], "mail_calendar")}}
                    </select>
                  </label>
                  <label>
                    Label
                    <input id="account-label" placeholder="Chris Gmail">
                  </label>
                  <label>
                    Login hint
                    <input id="account-login-hint" placeholder="name@example.com">
                  </label>
                  <label>
                    Notes
                    <textarea id="account-notes" placeholder="Optional provider note or setup reminder."></textarea>
                  </label>
                  <div class="inline-actions">
                    <button id="save-personal-account" type="button">Save Account</button>
                  </div>
                  <div class="settings-note" id="account-settings-status">You can connect multiple accounts per person and provider when JARVIS needs a separate mailbox or calendar identity.</div>
                </div>`)
            }}
          </div>`;
      }}

      title.textContent = heading;
      body.innerHTML = content;
      body.scrollTop = 0;
      modal.scrollTop = 0;
      modal.querySelector(".modal").classList.toggle("workspace-modal", packetId === "catalyst" || packetId === "chronicle");
      modal.querySelector(".modal").classList.toggle("model-forge-modal", packetId === "model-forge");
      modal.querySelector(".modal").classList.toggle("brains-modal", packetId === "brains");
      modal.querySelector(".modal").classList.toggle("storm-modal", packetId === "storm");
      if (packetId === "settings") {{
        wireLayoutSettingsForm();
        wireVoiceSettingsForm();
        wirePageReviewSettingsForm();
        wireLocationSettingsForm();
        wireGoogleSettingsForm();
        wireAccountSettingsForm();
        wireIdentitySettingsForm();
      }} else if (packetId === "connected-devices") {{
        wireConnectedDevicesAdmin();
      }} else if (packetId === "dashboard") {{
        document.querySelectorAll("[data-dashboard-open]").forEach((button) => {{
          button.addEventListener("click", () => {{
            const nextPacket = button.getAttribute("data-dashboard-open") || "";
            if (nextPacket) {{
              openPacket(nextPacket);
            }}
          }});
        }});
      }} else if (packetId === "triage") {{
        document.getElementById("triage-open-day")?.addEventListener("click", () => {{
          openPacket("today");
        }});
        document.getElementById("triage-open-approvals")?.addEventListener("click", () => {{
          openPacket("approvals");
        }});
        document.getElementById("triage-open-catalyst")?.addEventListener("click", () => {{
          openPacket("catalyst");
        }});
      }} else if (packetId === "today") {{
        wireTodayBoardActions();
        wireAssistantInboxActions("today");
      }} else if (packetId === "review") {{
        wireReviewActions();
        wireAssistantInboxActions("review");
      }} else if (packetId === "mission-control") {{
        document.getElementById("mission-control-create")?.addEventListener("click", async () => {{
          const request = (document.getElementById("mission-control-request")?.value || "").trim();
          if (!request) return;
          const actor = preferredActorLabel();
          const room = document.getElementById("room")?.value || "office";
          try {{
            const created = await loadJSON("/api/missions", {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify({{ actor, room, request }}),
            }});
            state.activeMissionId = created.mission_id || "";
            await refreshDashboard({{ force: true, reopenPacket: false }});
            openPacket("mission-control");
          }} catch (error) {{
            console.warn("Mission creation failed", error);
          }}
        }});
        document.querySelectorAll(".mission-control-select").forEach((button) => {{
          button.addEventListener("click", () => {{
            state.activeMissionId = button.getAttribute("data-mission-id") || "";
            openPacket("mission-control");
          }});
        }});
        document.querySelectorAll(".mission-status-action").forEach((button) => {{
          button.addEventListener("click", async () => {{
            const missionId = button.getAttribute("data-mission-id") || "";
            const status = button.getAttribute("data-status") || "active";
            if (!missionId) return;
            try {{
              await loadJSON(`/api/missions/${{encodeURIComponent(missionId)}}/status`, {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{
                  status,
                  note: status === "completed"
                    ? "Mission closed from Mission Control."
                    : status === "blocked"
                      ? "Mission blocked and waiting for intervention."
                      : "Mission returned to active work.",
                }}),
              }});
              await refreshDashboard({{ force: true, reopenPacket: false }});
              openPacket("mission-control");
            }} catch (error) {{
              console.warn("Mission status update failed", error);
            }}
          }});
        }});
      }} else if (packetId === "finance-review") {{
        document.querySelectorAll(".finance-open-wealth").forEach((button) => {{
          button.addEventListener("click", () => {{
            openPacket("wealth");
          }});
        }});
      }} else if (packetId === "wealth") {{
        document.querySelectorAll(".wealth-lane-select").forEach((button) => {{
          button.addEventListener("click", () => {{
            state.wealthSelectedLane = button.getAttribute("data-wealth-lane") || "passive-income";
            const laneItems = (state.wealthReview?.items || []).filter((item) => String(item.lane_id || "") === String(state.wealthSelectedLane || ""));
            state.wealthSelectedItemId = String(laneItems[0]?.item_id || "");
            openPacket("wealth");
          }});
        }});
        document.querySelectorAll(".wealth-item-select").forEach((button) => {{
          button.addEventListener("click", () => {{
            state.wealthSelectedItemId = button.getAttribute("data-wealth-item-id") || "";
            state.wealthSelectedLane = button.getAttribute("data-wealth-item-lane") || state.wealthSelectedLane || "passive-income";
            openPacket("wealth");
          }});
        }});
        document.querySelectorAll(".wealth-item-action").forEach((button) => {{
          button.addEventListener("click", async () => {{
            const action = button.getAttribute("data-wealth-action") || "";
            const itemId = button.getAttribute("data-wealth-item-id") || "";
            const routeTo = button.getAttribute("data-wealth-route") || "";
            button.setAttribute("disabled", "disabled");
            try {{
              await runWealthItemAction(action, itemId, routeTo);
            }} catch (error) {{
              console.warn("Wealth action failed", error);
              document.getElementById("last-jarvis-text").textContent = error?.message || "Wealth action failed.";
              syncTranscriptRail();
            }} finally {{
              button.removeAttribute("disabled");
            }}
          }});
        }});
      }} else if (packetId === "tasks") {{
        wireTaskQueueActions();
      }} else if (packetId === "workshop") {{
        document.getElementById("open-model-forge-packet")?.addEventListener("click", () => {{
          openPacket("model-forge");
        }});
      }} else if (packetId === "agents") {{
        document.getElementById("open-agent-hierarchy")?.addEventListener("click", () => {{
          window.open("/agents/hierarchy", "_blank", "noopener,noreferrer");
        }});
      }} else if (packetId === "catalyst") {{
        wireCatalystWorkspace();
      }} else if (packetId === "chronicle") {{
        wireChronicleWorkspace().catch((error) => {{
          const summary = document.getElementById("chronicle-handoff-summary");
          if (summary) {{
            summary.textContent = error?.message || "Chronicle workspace unavailable.";
          }}
        }});
      }} else if (packetId === "vision") {{
        wireVisionPacket();
      }} else if (packetId === "model-forge") {{
        wireModelForgePacket();
      }} else if (packetId === "brains") {{
        const graph = data.brain_graph || {{}};
        const activeNodes = new Set(graph.active_nodes || []);
        renderBrainMesh("brain-mesh-modal", graph, activeNodes);
      }}
      setModalVisibility(true);
      applyModalPlacement();
      bringWindowToFront("modal");
      syncDesignReviewPanel();
    }}
    window.__jarvisOpenPacket = async (packetId, options = {{}}) => {{
      openPacket(packetId, options);
      for (let attempt = 0; attempt < 120; attempt += 1) {{
        const pendingForPacket = state.packetHydrationPending === packetId;
        const modalOpen = document.getElementById("modal-layer")?.classList.contains("open");
        const bodyText = (document.getElementById("modal-body")?.textContent || "").trim();
        if (!pendingForPacket && modalOpen && bodyText && !/^Loading\\b/i.test(bodyText)) {{
          return true;
        }}
        await new Promise((resolve) => window.setTimeout(resolve, 50));
      }}
      return false;
    }};

    function closePacket() {{
      stopVisionPreview();
      destroyModelForgeScene();
      state.packetHydrationToken += 1;
      state.packetHydrationPending = "";
      state.packet = "";
      state.packetStripExpanded = false;
      state.windowStates.modal.minimized = false;
      state.windowStates.modal.maximized = false;
      document.body.classList.remove("modal-open");
      if (state.activeOverlay?.type === "modal") {{
        setActiveOverlay("");
      }}
      syncShellFocusMode();
      renderContextActionDock();
      fillPacketStrip();
      const modal = document.getElementById("modal-layer");
      document.getElementById("modal-title").textContent = "Packet";
      const modalBody = document.getElementById("modal-body");
      modalBody.innerHTML = "";
      modalBody.scrollTop = 0;
      modal.scrollTop = 0;
      setModalVisibility(false);
      const modalCard = modal.querySelector(".modal");
      modal.classList.remove("layout-free");
      modalCard.classList.remove("workspace-modal", "model-forge-modal", "brains-modal", "storm-modal", "floating");
      modalCard.style.removeProperty("left");
      modalCard.style.removeProperty("top");
      modalCard.style.removeProperty("width");
      modalCard.style.removeProperty("height");
      syncDesignReviewPanel();
    }}

    async function saveGoogleClientSecret() {{
      const textarea = document.getElementById("google-client-secret-json");
      const status = document.getElementById("google-settings-status");
      const raw = (textarea?.value || "").trim();
      if (!raw) {{
        if (status) status.textContent = "Paste the Google OAuth client JSON first.";
        return {{ ok: false }};
      }}
      const data = await loadJSON("/api/google/client-secret", {{
        method: "POST",
        body: JSON.stringify({{ client_secret_json: raw }}),
      }});
      if (status) {{
        status.textContent = data.detail || "Google client saved.";
      }}
      await refreshDashboard();
      return data;
    }}

    function wireGoogleSettingsForm() {{
      const save = document.getElementById("save-google-client-secret");
      if (save) {{
        save.addEventListener("click", async () => {{
          try {{
            await saveGoogleClientSecret();
          }} catch (error) {{
            const status = document.getElementById("google-settings-status");
            if (status) status.textContent = error.message || "Google client save failed.";
          }}
        }});
      }}

      const connect = document.getElementById("launch-google-connect");
      if (connect) {{
        connect.addEventListener("click", async () => {{
          try {{
            const textarea = document.getElementById("google-client-secret-json");
            if ((textarea?.value || "").trim()) {{
              const result = await saveGoogleClientSecret();
              if (!result?.ok) {{
                return;
              }}
            }}
            window.location.href = "/google/connect";
          }} catch (error) {{
            const status = document.getElementById("google-settings-status");
            if (status) status.textContent = error.message || "Google connect launch failed.";
          }}
        }});
      }}

      const disconnect = document.getElementById("disconnect-google-workspace");
      if (disconnect) {{
        disconnect.addEventListener("click", async () => {{
          try {{
            const result = await loadJSON("/api/google/disconnect", {{ method: "POST" }});
            const status = document.getElementById("google-settings-status");
            if (status) status.textContent = result.message || "Google disconnected.";
            await refreshDashboard();
            openPacket("settings");
          }} catch (error) {{
            const status = document.getElementById("google-settings-status");
            if (status) status.textContent = error.message || "Google disconnect failed.";
          }}
        }});
      }}
    }}

    function wireAccountSettingsForm() {{
      const save = document.getElementById("save-personal-account");
      if (save) {{
        save.addEventListener("click", async () => {{
          const payload = {{
            owner_user_id: document.getElementById("account-owner-user-id")?.value || "",
            provider: document.getElementById("account-provider")?.value || "google",
            service_scope: document.getElementById("account-service-scope")?.value || "mail_calendar",
            label: document.getElementById("account-label")?.value || "",
            login_hint: document.getElementById("account-login-hint")?.value || "",
            notes: document.getElementById("account-notes")?.value || "",
            status: "planned",
          }};
          try {{
            const data = await loadJSON("/api/accounts", {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify(payload),
            }});
            state.accountRegistry = data.registry;
            const status = document.getElementById("account-settings-status");
            if (status) status.textContent = data.message || "Account saved.";
            await refreshDashboard();
            openPacket("settings");
          }} catch (error) {{
            const status = document.getElementById("account-settings-status");
            if (status) status.textContent = error.message || "Account save failed.";
          }}
        }});
      }}

      document.querySelectorAll(".account-connect").forEach((button) => {{
        button.addEventListener("click", () => {{
          const providerSelect = document.getElementById("account-provider");
          const accountId = button.dataset.accountId || "";
          if (!accountId) return;
          window.location.href = `/accounts/${{encodeURIComponent(accountId)}}/connect`;
        }});
      }});

      document.querySelectorAll(".account-disconnect").forEach((button) => {{
        button.addEventListener("click", async () => {{
          const accountId = button.dataset.accountId || "";
          if (!accountId) return;
          try {{
            const data = await loadJSON(`/api/accounts/${{encodeURIComponent(accountId)}}/disconnect`, {{
              method: "POST",
            }});
            const status = document.getElementById("account-settings-status");
            if (status) status.textContent = data.message || "Account disconnected.";
            await refreshVoiceSettings();
            await refreshDashboard();
            openPacket("settings");
          }} catch (error) {{
            const status = document.getElementById("account-settings-status");
            if (status) status.textContent = error.message || "Account disconnect failed.";
          }}
        }});
      }});
    }}

    function wireConnectedDevicesAdmin() {{
      const summary = document.getElementById("connected-devices-summary");
      const current = document.getElementById("connected-device-current");
      const list = document.getElementById("connected-devices-list");
      const status = document.getElementById("connected-devices-status");
      const refreshButton = document.getElementById("connected-devices-refresh");
      const bindCurrentButton = document.getElementById("connected-devices-bind-current");
      const pruneButton = document.getElementById("connected-devices-prune");
      const hideStaleToggle = document.getElementById("connected-devices-hide-stale");

      if (!summary || !current || !list || !status) {{
        return;
      }}

      const isStaleOrTestLike = (device) => {{
        const ua = String(device.user_agent || "").toLowerCase();
        const label = String(device.label || "").toLowerCase();
        const host = String(device.last_host || "").toLowerCase();
        const mapped = !!(device.owner_user_id || device.default_actor_id || device.suggested_default_actor_id);
        const shared = !!device.shared;
        const alwaysAvailable = !!device.always_available;
        const seen = Date.parse(String(device.last_seen_at || ""));
        const ageDays = Number.isFinite(seen) ? ((Date.now() - seen) / 86400000) : 9999;
        const testLike = ua.includes("headlesschrome") || ua.includes("electron") || ua.includes("codex/") || label === "macintel browser";
        const stale = ageDays >= 7 && !mapped && !shared && !alwaysAvailable && !host.endsWith(".ts.net");
        return testLike || stale;
      }};

      const renderSummary = (data) => {{
        const counts = data.summary || {{}};
        summary.innerHTML = `
          <div class="metric"><strong>Total known devices</strong> ${{escapeHtml(String(counts.total || 0))}}</div>
          <div class="metric"><strong>Mapped</strong> ${{escapeHtml(String(counts.mapped || 0))}} · <strong>Unassigned</strong> ${{escapeHtml(String(counts.unassigned || 0))}}</div>
          <div class="metric"><strong>Shared</strong> ${{escapeHtml(String(counts.shared || 0))}} · <strong>Personal</strong> ${{escapeHtml(String(counts.personal || 0))}}</div>
          <div class="metric"><strong>Suggested defaults</strong> ${{escapeHtml(String(counts.suggested_defaults || 0))}}</div>
          <div class="metric"><strong>Current browser</strong> ${{escapeHtml(state.shellDeviceId || "--")}}</div>
        `;
      }};

      const renderCurrentConnection = (data) => {{
        const device = data.current_device || {{}};
        const normalized = device.normalized_device || {{}};
        const profile = device.device_profile || {{}};
        const route = device.interface_route || {{}};
        const binding = device.user_profile_binding || {{}};
        if (!device.device_id) {{
          current.innerHTML = `<div class="metric">Current browser has not been bound yet. Use <strong>Bind Current Browser</strong> first.</div>`;
          return;
        }}
        const mappedTo = device.owner_display_name || device.default_actor_display_name || normalized.likely_actor_display_name || "unassigned";
        current.innerHTML = `
          <div class="metric"><strong>Device</strong> ${{escapeHtml(normalized.hardware_label || device.label || "Unknown device")}}</div>
          <div class="metric"><strong>OS</strong> ${{escapeHtml(normalized.os_name || "Unknown")}} · <strong>Browser</strong> ${{escapeHtml(normalized.browser_name || "Unknown browser")}}</div>
          <div class="metric"><strong>Interface</strong> ${{escapeHtml(device.device_type || normalized.interface_type || "device")}} · <strong>Access</strong> ${{escapeHtml(normalized.access_label || "Unknown path")}}</div>
          <div class="metric"><strong>Device profile</strong> ${{escapeHtml(profile.device_profile_label || "General Browser Session")}}</div>
          <div class="metric"><strong>Interface route</strong> ${{escapeHtml(route.route_label || "Standard Chamber")}} · <strong>Chat</strong> ${{escapeHtml(route.chat_mode || "lower-rail")}}</div>
          <div class="metric"><strong>Mapped to</strong> ${{escapeHtml(mappedTo)}} · <strong>Confidence</strong> ${{escapeHtml((device.owner_confidence || {{}}).confidence || normalized.owner_confidence || "low")}}</div>
          <div class="metric"><strong>User profile binding</strong> ${{escapeHtml(binding.display_name || binding.user_id || binding.source || "unassigned")}} · <strong>Source</strong> ${{escapeHtml(binding.source || "unassigned")}}</div>
          <div class="settings-note">${{escapeHtml(profile.summary || "")}}</div>
          <div class="settings-note">${{escapeHtml(binding.summary || "")}}</div>
          <div class="metric"><strong>Host</strong> ${{escapeHtml(normalized.host || "--")}}</div>
          <div class="settings-note">${{escapeHtml(device.device_id || "")}}</div>
        `;
      }};

      const renderDeviceCard = (device, data) => {{
        const ownerOptions = renderSelectOptions([{{ id: "", label: "Unassigned" }}].concat(data.owners || []), device.owner_user_id || "", "No household users found");
        const actorOptions = renderSelectOptions([{{ id: "", label: "No default" }}].concat(data.owners || []), device.default_actor_id || "", "No household users found");
        const trustOptions = renderSelectOptions(data.trust_levels || [], device.trust_level || "trusted");
        const typeOptions = renderSelectOptions(data.device_types || [], device.device_type || "browser");
        const currentBadge = device.device_id === state.shellDeviceId ? `<div class="metric"><strong>This browser</strong> yes</div>` : "";
        const fingerprintLabel = device.has_fingerprint ? "present" : "missing";
        const mappedLabel = device.owner_display_name || device.default_actor_display_name || "unassigned";
        const lastActor = device.last_actor_display_name || device.last_actor_id || "--";
        const suggested = device.suggested_default_actor_id || "--";
        const sharedLabel = device.shared ? "shared" : "personal";
        const normalized = device.normalized_device || {{}};
        const profile = device.device_profile || {{}};
        const route = device.interface_route || {{}};
        const binding = device.user_profile_binding || {{}};
        return `
          <div class="metric connected-device-card" data-device-card="${{escapeHtml(device.device_id || "")}}">
            <div class="connected-device-meta">
              <strong>${{escapeHtml(device.label || "Unnamed device")}}</strong> · ${{escapeHtml(device.device_type || "device")}} · ${{escapeHtml(sharedLabel)}} · ${{escapeHtml(device.posture || "unassigned")}}
              <br>
              Mapped to: ${{escapeHtml(mappedLabel)}} · Trust: ${{escapeHtml(device.trust_level || "trusted")}}
              <br>
              OS: ${{escapeHtml(normalized.os_name || "Unknown")}} · Browser: ${{escapeHtml(normalized.browser_name || "Unknown browser")}} · Access: ${{escapeHtml(normalized.access_label || "Unknown path")}}
              <br>
              Profile: ${{escapeHtml(profile.device_profile_label || "General Browser Session")}} · Route: ${{escapeHtml(route.route_label || "Standard Chamber")}}
              <br>
              Suggested user: ${{escapeHtml(binding.display_name || binding.user_id || binding.source || "unassigned")}} · Source: ${{escapeHtml(binding.source || "unassigned")}}
              <br>
              Last actor: ${{escapeHtml(lastActor)}} · Suggested default: ${{escapeHtml(suggested)}}
              <br>
              Last seen: ${{escapeHtml(device.last_seen_at || "never")}} · Fingerprint: ${{escapeHtml(fingerprintLabel)}}
            </div>
            ${{currentBadge}}
            <div class="inline-actions" style="margin-top:10px; margin-bottom:8px;">
              <button class="connected-device-save" type="button" data-device-id="${{escapeHtml(device.device_id || "")}}">Save Mapping</button>
            </div>
            <div class="settings-grid connected-device-form" style="margin-top:12px;">
              <label>
                Label
                <input data-field="label" value="${{escapeHtml(device.label || "")}}">
              </label>
              <label>
                Type
                <select data-field="device_type">${{typeOptions}}</select>
              </label>
              <label>
                Owner
                <select data-field="owner_user_id">${{ownerOptions}}</select>
              </label>
              <label>
                Default actor
                <select data-field="default_actor_id">${{actorOptions}}</select>
              </label>
              <label>
                Trust
                <select data-field="trust_level">${{trustOptions}}</select>
              </label>
              <label>
                Room
                <input data-field="room" value="${{escapeHtml(device.room || "")}}" placeholder="office, kitchen, workshop">
              </label>
              <label>
                Notes
                <textarea data-field="notes" placeholder="Personal phone, shared iPad, workshop display...">${{escapeHtml(device.notes || "")}}</textarea>
              </label>
              <label class="toggle-row">
                <input data-field="shared" type="checkbox" ${{device.shared ? "checked" : ""}}>
                Shared device
              </label>
              <label class="toggle-row">
                <input data-field="always_available" type="checkbox" ${{device.always_available ? "checked" : ""}}>
                Always available endpoint
              </label>
            </div>
            <div class="inline-actions" style="margin-top:10px;">
              <button class="connected-device-save" type="button" data-device-id="${{escapeHtml(device.device_id || "")}}">Save Mapping</button>
            </div>
            <div class="settings-note" style="margin-top:8px;">${{escapeHtml(device.device_id || "")}}</div>
          </div>
        `;
      }};

      const wireDeviceButtons = (data) => {{
        list.querySelectorAll(".connected-device-save").forEach((button) => {{
          button.addEventListener("click", async () => {{
            const deviceId = button.dataset.deviceId || "";
            const card = button.closest("[data-device-card]");
            if (!deviceId || !card) return;
            const readValue = (field) => card.querySelector(`[data-field="${{field}}"]`);
            const payload = {{
              device_id: deviceId,
              label: readValue("label")?.value || "",
              device_type: readValue("device_type")?.value || "browser",
              owner_user_id: readValue("owner_user_id")?.value || "",
              default_actor_id: readValue("default_actor_id")?.value || "",
              trust_level: readValue("trust_level")?.value || "trusted",
              room: readValue("room")?.value || "",
              notes: readValue("notes")?.value || "",
              shared: !!readValue("shared")?.checked,
              always_available: !!readValue("always_available")?.checked,
            }};
            try {{
              const result = await loadJSON("/api/identity/device", {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify(payload),
              }});
              state.identity = result.identity || state.identity;
              status.textContent = `Saved mapping for ${{result.device?.label || deviceId}}.`;
              await refreshDevices();
            }} catch (error) {{
              status.textContent = error.message || "Failed to save the device mapping.";
            }}
          }});
        }});
      }};

      async function refreshDevices() {{
        status.textContent = "Refreshing connected devices…";
        summary.innerHTML = `<div class="metric">Loading device summary…</div>`;
        current.innerHTML = `<div class="metric">Loading current device…</div>`;
        list.innerHTML = `<div class="metric">Loading device registry…</div>`;
        try {{
          const data = await loadJSON(`/api/connected-devices?current_device_id=${{encodeURIComponent(state.shellDeviceId || "")}}`);
          state.connectedDevices = data;
          state.currentDevice = data.current_device || state.currentDevice || null;
          applyCurrentDeviceRouting(state.currentDevice);
          renderSummary(data);
          renderCurrentConnection(data);
          const allDevices = data.devices || [];
          const hideStale = !!hideStaleToggle?.checked;
          const devices = hideStale ? allDevices.filter((device) => !isStaleOrTestLike(device)) : allDevices;
          list.innerHTML = devices.length
            ? devices.map((device) => renderDeviceCard(device, data)).join("")
            : `<div class="metric">No device sessions have been registered yet. Open JARVIS on the device and bind the current browser first.</div>`;
          wireDeviceButtons(data);
          const hiddenCount = Math.max(0, allDevices.length - devices.length);
          status.textContent = devices.length
            ? `Showing ${{devices.length}} device session(s)${{hiddenCount ? ` · ${{hiddenCount}} hidden as stale/test-like` : ""}}. Unassigned devices can be mapped directly here.`
            : "No device sessions have been registered yet.";
        }} catch (error) {{
          summary.innerHTML = `<div class="metric">Connected device summary unavailable.</div>`;
          current.innerHTML = `<div class="metric">Current device unavailable: ${{escapeHtml(error.message || "request failed")}}</div>`;
          list.innerHTML = `<div class="metric">Connected device registry unavailable: ${{escapeHtml(error.message || "request failed")}}</div>`;
          status.textContent = error.message || "Connected device refresh failed.";
        }}
      }}

      refreshButton?.addEventListener("click", refreshDevices);
      hideStaleToggle?.addEventListener("change", refreshDevices);
      bindCurrentButton?.addEventListener("click", async () => {{
        try {{
          const data = await bindShellIdentity();
          status.textContent = data.resolved_actor_label
            ? `Current browser bound and resolved to ${{data.resolved_actor_label}}.`
            : "Current browser bound. Map it to a person below if it is still unassigned.";
          await refreshDevices();
        }} catch (error) {{
          status.textContent = error.message || "Failed to bind the current browser.";
        }}
      }});
      pruneButton?.addEventListener("click", async () => {{
        status.textContent = "Pruning old browser sessions…";
        try {{
          const result = await loadJSON("/api/identity/devices/prune", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ stale_days: 7, prune_test_like: true }}),
          }});
          state.identity = result.identity || state.identity;
          status.textContent = `Pruned ${{result.removed_count || 0}} old browser session(s).`;
          await refreshDevices();
        }} catch (error) {{
          status.textContent = error.message || "Failed to prune old browser sessions.";
        }}
      }});

      refreshDevices();
    }}

    function wireTaskQueueActions() {{
      const statusTarget = document.getElementById("last-jarvis-text");
      document.querySelectorAll(".task-queue-action").forEach((button) => {{
        button.addEventListener("click", async () => {{
          const action = button.dataset.action || "";
          const domain = button.dataset.domain || "";
          const itemId = button.dataset.itemId || "";
          if (!action || !domain || !itemId) return;
          button.disabled = true;
          try {{
            const payload = {{
              actor: state.sessionIdentity?.resolved_actor_label || document.getElementById("actor")?.value || "Chris",
              action,
              domain,
              item_id: itemId,
            }};
            const result = await loadJSON("/api/open-loops/action", {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify(payload),
            }});
            if (statusTarget) {{
              statusTarget.textContent = `Assistant Core updated ${{domain}} with action "${{action}}".`;
            }}
            await refreshDashboard();
            openPacket("tasks");
          }} catch (error) {{
            if (statusTarget) {{
              statusTarget.textContent = error.message || "Failed to update the assistant core queue.";
            }}
          }} finally {{
            button.disabled = false;
          }}
        }});
      }});
    }}

    function wireIdentitySettingsForm() {{
      async function refreshRuntimeServiceStatus() {{
        const container = document.getElementById("runtime-service-status");
        if (!container) return;
        container.innerHTML = `<div class="metric">Runtime service status is loading…</div>`;
        try {{
          const data = await loadJSON("/api/runtime-service");
          const jarvis = data.runtime || {{}};
          const openviking = data.openviking || {{}};
          const assistant = data.assistant_autonomy || {{}};
          const host = data.service_plan || {{}};
          const routes = Array.isArray(data.public_routes) ? data.public_routes : [];
          const composeServices = Array.isArray(data.compose_services) ? data.compose_services : [];
          const hostedProbe = data.hosted_probe || {{}};
          const hostedStatus = hostedProbe.status_code
            ? `${{hostedProbe.status_code}}${{hostedProbe.headers?.www_authenticate ? " · Access protected" : ""}}`
            : (hostedProbe.detail || "not probed");
          const routeLine = routes.length
            ? routes.slice(0, 3).map((route) => `${{escapeHtml(route.domain || route.url || "")}} → ${{escapeHtml(route.upstream || route.service_id || "")}}`).join("<br>")
            : "No public routes discovered from deploy/nginx.conf.";
          container.innerHTML = `
            <div class="metric"><strong>Deployment mode</strong> ${{escapeHtml(data.mode_label || host.mode_label || "Hybrid household plus hosted edge")}}</div>
            <div class="metric"><strong>JARVIS launch agent</strong> ${{jarvis.installed ? (jarvis.loaded ? "installed and loaded" : "installed but not loaded") : "not installed"}}</div>
            <div class="metric"><strong>OpenViking launch agent</strong> ${{openviking.installed ? (openviking.loaded ? "installed and loaded" : "installed but not loaded") : "not installed"}}</div>
            <div class="metric"><strong>Assistant autonomy</strong> ${{assistant.installed ? (assistant.loaded ? "installed and loaded" : "installed but not loaded") : "not installed"}}</div>
            <div class="metric"><strong>LAN URL</strong> ${{escapeHtml(data.lan_url || host.lan_url || window.location.origin)}}</div>
            <div class="metric"><strong>Hostname</strong> ${{escapeHtml(data.hostname || host.hostname || "jarvis.local")}}</div>
            <div class="metric"><strong>Hosted URL</strong> ${{escapeHtml(data.hosted_base_url || host.hosted_base_url || "https://jarvis.teambinion.org")}}</div>
            <div class="metric"><strong>Hosted edge</strong> ${{escapeHtml(data.hosted_provider || host.hosted_provider || "Hetzner")}} via ${{escapeHtml(data.edge_provider || host.edge_provider || "Cloudflare Tunnel")}}</div>
            <div class="metric"><strong>Access posture</strong> ${{data.cloudflare_access_enabled === false ? "Cloudflare edge without Access policy" : "Cloudflare Access protected"}} · ${{data.tunnel_enabled === false ? "tunnel disabled" : "tunnel enabled"}}</div>
            <div class="metric"><strong>Remote admin</strong> ${{escapeHtml((data.remote_admin_user || host.remote_admin_user || "root") + ((data.remote_admin_host || host.remote_admin_host) ? `@${{data.remote_admin_host || host.remote_admin_host}}` : ""))}}</div>
            <div class="metric"><strong>Compose services</strong> ${{composeServices.length ? composeServices.map((item) => escapeHtml(item.id || item.label || "")).join(", ") : "Not discovered"}}</div>
            <div class="metric"><strong>Public routes</strong><br>${{routeLine}}</div>
            <div class="metric"><strong>Hosted probe</strong> ${{escapeHtml(hostedStatus)}}</div>
          `;
        }} catch (error) {{
          container.innerHTML = `<div class="metric">Runtime service status unavailable: ${{escapeHtml(error.message || "request failed")}}</div>`;
        }}
      }}

      async function refreshPersonaSnapshot(forceRefresh = false) {{
        const userId = document.getElementById("identity-member-user-id")?.value || "";
        const container = document.getElementById("identity-member-adaptation");
        if (!userId || !container) return;
        container.innerHTML = `<div class="metric">Loading adaptive persona snapshot…</div>`;
        try {{
          const params = new URLSearchParams({{
            actor: userId,
            device_id: state.shellDeviceId || "",
            refresh: forceRefresh ? "true" : "false",
          }});
          const data = await loadJSON(`/api/persona-snapshot?${{params.toString()}}`);
          const voice = data.voice_identity || {{}};
          const presence = data.presence_identity || {{}};
          const digitalTwin = data.digital_twin || {{}};
          const morning = data.morning_pattern || {{}};
          const signals = data.signal_counts || {{}};
          container.innerHTML = `
            <div class="metric"><strong>Headline</strong><br>${{escapeHtml(digitalTwin.headline || "No adaptive headline yet.")}}</div>
            <div class="metric"><strong>Voice identity</strong><br>Voice: ${{escapeHtml(voice.preferred_voice || "--")}} · Aliases: ${{escapeHtml((voice.voice_aliases || []).join(", ") || "none")}}</div>
            <div class="metric"><strong>Presence</strong><br>Rooms: ${{escapeHtml((presence.primary_rooms || []).join(", ") || "--")}} · Morning: ${{escapeHtml(presence.morning_room || "--")}} · Presence: ${{escapeHtml(presence.actor_presence || "unknown")}}</div>
            <div class="metric"><strong>Morning pattern</strong><br>${{escapeHtml(morning.briefing_style || "first-light")}} · ${{escapeHtml(morning.anticipation_style || "quietly proactive")}}</div>
            <div class="metric"><strong>Likely next needs</strong><br>${{escapeHtml((digitalTwin.likely_next_needs || []).join(" | ") || "Still learning.")}}</div>
            <div class="metric"><strong>Signals</strong><br>Facts: ${{escapeHtml(String(signals.profile_facts || 0))}} · First Light runs: ${{escapeHtml(String(signals.first_light_runs || 0))}} · Devices: ${{escapeHtml(String(signals.owned_devices || 0))}}</div>
          `;
        }} catch (error) {{
          container.innerHTML = `<div class="metric">Adaptive persona snapshot unavailable: ${{escapeHtml(error.message || "request failed")}}</div>`;
        }}
      }}

      async function refreshLearningReview() {{
        const userId = document.getElementById("identity-member-user-id")?.value || "";
        const container = document.getElementById("identity-member-learning-review");
        if (!userId || !container) return;
        container.innerHTML = `<div class="metric">Loading learning review…</div>`;
        try {{
          const viewer = state.sessionIdentity?.resolved_actor_label || "Chris";
          const params = new URLSearchParams({{
            viewer,
            subject_user_id: userId,
          }});
          const data = await loadJSON(`/api/learning-review?${{params.toString()}}`);
          const proposals = data.pending_proposals || [];
          const facts = data.profile_facts || [];
          const governance = data.governance || {{}};
          const history = data.first_light_history || [];
          const proposalSummary = proposals.length
            ? proposals.map((item) => `${{escapeHtml(item.summary || "")}} [${{escapeHtml(item.confidence || "confirmed")}}]`).join(" | ")
            : "No pending learning proposals.";
          const factSummary = facts.length
            ? facts.map((item) => escapeHtml(item.summary || "")).join(" | ")
            : "No active durable facts yet.";
          const historySummary = history.length
            ? history.map((item) => escapeHtml(item.local_time || item.generated_at || "")).join(" | ")
            : "No First Light history yet.";
          const proposalButtons = proposals.slice(0, 3).map((item) =>
            `<button class="ghost-toggle learning-proposal-action" data-proposal-id="${{escapeHtml(item.proposal_id || "")}}" data-decision="approved" type="button">Approve ${{escapeHtml(item.title || "proposal")}}</button><button class="ghost-toggle learning-proposal-action" data-proposal-id="${{escapeHtml(item.proposal_id || "")}}" data-decision="rejected" type="button">Reject</button>`
          ).join("");
          const factButtons = facts.slice(0, 3).map((item) =>
            `<button class="ghost-toggle learning-fact-action" data-fact-id="${{escapeHtml(item.fact_id || "")}}" data-status="retired" type="button">Retire fact</button>`
          ).join("");
          container.innerHTML = `
            <div class="metric"><strong>Learning governance</strong><br>Approve proposals: ${{governance.can_approve_proposals ? "yes" : "no"}} · Retire facts: ${{governance.can_retire_facts ? "yes" : "no"}} · Child-safe boundary: ${{data.child_safe_boundary ? "on" : "off"}}</div>
            <div class="metric"><strong>Pending proposals</strong><br>${{proposalSummary}}</div>
            <div class="metric"><strong>Durable facts</strong><br>${{factSummary}}</div>
            <div class="metric"><strong>Recent First Light runs</strong><br>${{historySummary}}</div>
            <div class="inline-actions">
              ${{proposalButtons}}
              ${{factButtons}}
            </div>
          `;
          container.querySelectorAll(".learning-proposal-action").forEach((button) => {{
            button.addEventListener("click", async () => {{
              const proposalId = button.dataset.proposalId || "";
              const decision = button.dataset.decision || "approved";
              if (!proposalId) return;
              try {{
                await loadJSON(`/api/learning/proposals/${{encodeURIComponent(proposalId)}}`, {{
                  method: "POST",
                  headers: {{ "Content-Type": "application/json" }},
                  body: JSON.stringify({{ decision }}),
                }});
                const status = document.getElementById("identity-member-status");
                if (status) status.textContent = `Learning proposal ${{decision}} for ${{data.subject_display_name || userId}}.`;
                await refreshPersonaSnapshot(true);
                await refreshLearningReview();
              }} catch (error) {{
                const status = document.getElementById("identity-member-status");
                if (status) status.textContent = error.message || "Failed to update learning proposal.";
              }}
            }});
          }});
          container.querySelectorAll(".learning-fact-action").forEach((button) => {{
            button.addEventListener("click", async () => {{
              const factId = button.dataset.factId || "";
              const statusValue = button.dataset.status || "retired";
              if (!factId) return;
              try {{
                await loadJSON(`/api/learning/facts/${{encodeURIComponent(factId)}}`, {{
                  method: "POST",
                  headers: {{ "Content-Type": "application/json" }},
                  body: JSON.stringify({{
                    viewer: state.sessionIdentity?.resolved_actor_label || "Chris",
                    status: statusValue,
                  }}),
                }});
                const status = document.getElementById("identity-member-status");
                if (status) status.textContent = `Learning fact updated for ${{data.subject_display_name || userId}}.`;
                await refreshPersonaSnapshot(true);
                await refreshLearningReview();
              }} catch (error) {{
                const status = document.getElementById("identity-member-status");
                if (status) status.textContent = error.message || "Failed to update learning fact.";
              }}
            }});
          }});
        }} catch (error) {{
          container.innerHTML = `<div class="metric">Learning review unavailable: ${{escapeHtml(error.message || "request failed")}}</div>`;
        }}
      }}

      const syncSelectedMember = () => {{
        const userId = document.getElementById("identity-member-user-id")?.value || "";
        const member = (state.identity?.members || []).find((item) => item.user_id === userId);
        if (!member) return;
        const setValue = (id, value) => {{
          const el = document.getElementById(id);
          if (el) el.value = value || "";
        }};
        setValue("identity-member-tone", member.preferred_tone);
        setValue("identity-member-briefing-style", member.briefing_style);
        setValue("identity-member-anticipation-style", member.anticipation_style);
        setValue("identity-member-voice", member.preferred_voice);
        setValue("identity-member-voice-aliases", (member.voice_aliases || []).join(", "));
        setValue("identity-member-primary-rooms", (member.primary_rooms || []).join(", "));
        setValue("identity-member-morning-room", member.morning_room);
        setValue("identity-member-boundary", member.privacy_boundary);
        setValue("identity-member-notes", member.notes);
        const trust = document.getElementById("identity-member-trust");
        if (trust) trust.value = member.trust_level || "trusted";
        refreshPersonaSnapshot(false);
        refreshLearningReview();
      }};

      document.getElementById("identity-member-user-id")?.addEventListener("change", syncSelectedMember);
      syncSelectedMember();
      refreshRuntimeServiceStatus();

      const saveMember = document.getElementById("save-identity-member");
      if (saveMember) {{
        saveMember.addEventListener("click", async () => {{
          const userId = document.getElementById("identity-member-user-id")?.value || "";
          const existing = (state.identity?.members || []).find((item) => item.user_id === userId) || {{}};
          const payload = {{
            user_id: userId,
            display_name: existing.display_name || userId,
            role: existing.role || "",
            permissions: existing.permissions || "",
            trust_level: document.getElementById("identity-member-trust")?.value || existing.trust_level || "trusted",
            privacy_boundary: document.getElementById("identity-member-boundary")?.value || existing.privacy_boundary || "personal",
            preferred_tone: document.getElementById("identity-member-tone")?.value || existing.preferred_tone || "",
            briefing_style: document.getElementById("identity-member-briefing-style")?.value || existing.briefing_style || "",
            anticipation_style: document.getElementById("identity-member-anticipation-style")?.value || existing.anticipation_style || "",
            preferred_voice: document.getElementById("identity-member-voice")?.value || existing.preferred_voice || "",
            voice_aliases: String(document.getElementById("identity-member-voice-aliases")?.value || "").split(",").map((item) => item.trim()).filter(Boolean),
            primary_rooms: String(document.getElementById("identity-member-primary-rooms")?.value || "").split(",").map((item) => item.trim()).filter(Boolean),
            morning_room: document.getElementById("identity-member-morning-room")?.value || existing.morning_room || "",
            notes: document.getElementById("identity-member-notes")?.value || existing.notes || "",
            priorities: existing.priorities || [],
            active: existing.active !== false,
          }};
          try {{
            const data = await loadJSON("/api/identity/member", {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify(payload),
            }});
            state.identity = data.identity;
            const status = document.getElementById("identity-member-status");
            if (status) status.textContent = `Saved profile for ${{data.member?.display_name || userId}}.`;
            await refreshPersonaSnapshot(true);
            await refreshLearningReview();
            openPacket("settings");
          }} catch (error) {{
            const status = document.getElementById("identity-member-status");
            if (status) status.textContent = error.message || "Failed to save family identity profile.";
          }}
        }});
      }}

      const refreshPersona = document.getElementById("refresh-persona-snapshot");
      if (refreshPersona) {{
        refreshPersona.addEventListener("click", async () => {{
          await refreshPersonaSnapshot(true);
          await refreshLearningReview();
          const status = document.getElementById("identity-member-status");
          if (status) status.textContent = "Adaptive persona snapshot refreshed from First Light, memory, and device signals.";
        }});
      }}

      const saveDevice = document.getElementById("save-identity-device");
      if (saveDevice) {{
        saveDevice.addEventListener("click", async () => {{
          const payload = {{
            device_id: document.getElementById("identity-device-id")?.value || "",
            label: document.getElementById("identity-device-label")?.value || "",
            device_type: document.getElementById("identity-device-type")?.value || "browser",
            owner_user_id: document.getElementById("identity-device-owner")?.value || "",
            default_actor_id: document.getElementById("identity-device-default-actor")?.value || "",
            trust_level: document.getElementById("identity-device-trust")?.value || "trusted",
            room: document.getElementById("identity-device-room")?.value || "",
            notes: document.getElementById("identity-device-notes")?.value || "",
            shared: !!document.getElementById("identity-device-shared")?.checked,
            always_available: !!document.getElementById("identity-device-always-available")?.checked,
            user_agent: navigator.userAgent || "",
          }};
          try {{
            const data = await loadJSON("/api/identity/device", {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify(payload),
            }});
            state.identity = data.identity;
            const status = document.getElementById("identity-device-status");
            if (status) status.textContent = `Saved device binding for ${{data.device?.label || payload.device_id}}.`;
            openPacket("settings");
          }} catch (error) {{
            const status = document.getElementById("identity-device-status");
            if (status) status.textContent = error.message || "Failed to save device binding.";
          }}
        }});
      }}

      const bindCurrent = document.getElementById("bind-current-device");
      if (bindCurrent) {{
        bindCurrent.addEventListener("click", async () => {{
          try {{
            const data = await bindShellIdentity();
            const status = document.getElementById("identity-device-status");
            if (status) status.textContent = data.resolved_actor_label
              ? `Current browser bound to ${{data.resolved_actor_label}}.`
              : "Current browser bound. Mark it shared or assign a default actor if needed.";
            openPacket("settings");
          }} catch (error) {{
            const status = document.getElementById("identity-device-status");
            if (status) status.textContent = error.message || "Failed to bind current browser.";
          }}
        }});
      }}

      const applySessionActor = document.getElementById("apply-session-actor");
      if (applySessionActor) {{
        applySessionActor.addEventListener("click", async () => {{
          const actorId = document.getElementById("identity-session-actor")?.value || "";
          saveSessionActorOverride(actorId);
          try {{
            const data = await bindShellIdentity();
            const status = document.getElementById("identity-device-status");
            if (status) status.textContent = data.resolved_actor_label
              ? `Using ${{data.resolved_actor_label}} for this shared-device session.`
              : "Session override cleared. Device defaults are active again.";
            openPacket("settings");
          }} catch (error) {{
            const status = document.getElementById("identity-device-status");
            if (status) status.textContent = error.message || "Failed to apply the shared-device session actor.";
          }}
        }});
      }}

      const clearSessionActor = document.getElementById("clear-session-actor");
      if (clearSessionActor) {{
        clearSessionActor.addEventListener("click", async () => {{
          saveSessionActorOverride("");
          try {{
            const data = await bindShellIdentity();
            const status = document.getElementById("identity-device-status");
            if (status) status.textContent = data.resolved_actor_label
              ? `Session override cleared. Current actor is now ${{data.resolved_actor_label}}.`
              : "Session override cleared. Device defaults are active again.";
            openPacket("settings");
          }} catch (error) {{
            const status = document.getElementById("identity-device-status");
            if (status) status.textContent = error.message || "Failed to clear the shared-device session actor.";
          }}
        }});
      }}

      const saveService = document.getElementById("save-identity-service");
      if (saveService) {{
        saveService.addEventListener("click", async () => {{
          const payload = {{
            deployment_mode: document.getElementById("identity-service-deployment-mode")?.value || "hybrid",
            host_label: document.getElementById("identity-service-host-label")?.value || "",
            host_type: document.getElementById("identity-service-host-type")?.value || "",
            lan_url: document.getElementById("identity-service-lan-url")?.value || "",
            hostname: document.getElementById("identity-service-hostname")?.value || "",
            hosted_host_label: document.getElementById("identity-service-hosted-host-label")?.value || "",
            hosted_provider: document.getElementById("identity-service-hosted-provider")?.value || "",
            hosted_base_url: document.getElementById("identity-service-hosted-base-url")?.value || "",
            remote_admin_host: document.getElementById("identity-service-remote-admin-host")?.value || "",
            remote_admin_user: document.getElementById("identity-service-remote-admin-user")?.value || "",
            edge_provider: document.getElementById("identity-service-edge-provider")?.value || "",
            compose_project: document.getElementById("identity-service-compose-project")?.value || "",
            notes: document.getElementById("identity-service-notes")?.value || "",
            always_on_enabled: !!document.getElementById("identity-service-always-on")?.checked,
            launch_on_boot: !!document.getElementById("identity-service-launch-on-boot")?.checked,
            watchdog_enabled: !!document.getElementById("identity-service-watchdog")?.checked,
            cloudflare_access_enabled: !!document.getElementById("identity-service-cloudflare-access")?.checked,
            tunnel_enabled: !!document.getElementById("identity-service-tunnel-enabled")?.checked,
          }};
          try {{
            const data = await loadJSON("/api/identity/service", {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify(payload),
            }});
            state.identity = data.identity;
            const status = document.getElementById("identity-service-status");
            if (status) status.textContent = "Always-on service plan saved.";
            await refreshRuntimeServiceStatus();
            openPacket("settings");
          }} catch (error) {{
            const status = document.getElementById("identity-service-status");
            if (status) status.textContent = error.message || "Failed to save service plan.";
          }}
        }});
      }}
    }}

    async function refreshLaunchZone() {{
      const now = Date.now();
      if (state._launchZoneRefreshedAt && (now - state._launchZoneRefreshedAt) < 60000) {{
        return;
      }}
      state._launchZoneRefreshedAt = now;
      try {{
        const data = await loadJSON('/api/publishing/launch-control');
        populateLaunchZone(data);
      }} catch (err) {{
        // Silently hide zone if endpoint unavailable
        populateLaunchZone(null);
      }}
    }}

    async function applyShellChrome(data, options = {{}}) {{
      if (options.refreshStorm !== false && (!state.storm.lastFetchedAt || (Date.now() - state.storm.lastFetchedAt) > 900000)) {{
        refreshStormWeather().catch((error) => console.warn("Storm shell refresh failed", error));
      }}
      refreshLaunchZone().catch((error) => console.warn("Launch zone refresh failed", error));
      updateRuntimeFreshness(data);
      if (state.currentDevice) {{
        applyCurrentDeviceRouting(state.currentDevice);
      }}
      updateDashboardLauncher(data);
      renderCoreHomeSummary(data);
      syncShellFocusMode();
      renderContextActionDock();
      if (state.activeScene) {{
        renderActiveScene();
      }}
      if (state.signalRailExpanded) {{
        fillSignalRail(data);
      }}
      fillBrainGraph(data);
      if (state.packetStripExpanded) {{
        fillPacketStrip();
      }}
      if (state.coreCommandOpen) {{
        renderCoreCommandRing();
      }}
      const assistantSurface = data.assistant_surface || {{}};
      const surfaceKey = assistantSurface.surface_key || "";
      const suggestedPacket = assistantSurface.auto_open_packet || "";
      const manualPacketIntentActive = Number(state.manualPacketIntentUntil || 0) > Date.now();
      const initialPacketIntentActive = Boolean(state.initialPacketOverride);
      if (
        suggestedPacket &&
        surfaceKey &&
        !manualPacketIntentActive &&
        !initialPacketIntentActive &&
        !document.body.classList.contains("modal-open") &&
        !state.packet &&
        state.lastAssistantSurfaceKey !== surfaceKey
      ) {{
        saveAssistantSurfaceKey(surfaceKey);
        document.getElementById("last-jarvis-text").textContent =
          (assistantSurface.briefing_lines && assistantSurface.briefing_lines[0]) ||
          "JARVIS has work that should come back to you now.";
        syncTranscriptRail();
        openPacket(suggestedPacket);
        return data;
      }}
      if (options.reopenPacket !== false && state.packet && state.packetHydrationPending !== state.packet) {{
        openPacket(state.packet);
      }}
      if (await maybeAutoOpenCadenceReview(data.assistant_notifications || {{}})) {{
        return data;
      }}
      if (options.deliverAlerts !== false) {{
        await deliverAssistantBrowserAlerts().catch((error) => console.warn("Assistant browser alerts failed", error));
      }}
      return data;
    }}

    async function refreshShellState(options = {{}}) {{
      const force = Boolean(options.force);
      const minIntervalMs = Number.isFinite(options.minIntervalMs) ? options.minIntervalMs : 0;
      const now = Date.now();
      if (!force && state.dashboardRefreshPromise) {{
        return state.dashboardRefreshPromise;
      }}
      if (!force && state.shellStateRefreshPromise) {{
        return state.shellStateRefreshPromise;
      }}
      if (!force && state.dashboard && minIntervalMs > 0 && (now - state.lastShellStateRefreshAt) < minIntervalMs) {{
        return state.dashboard;
      }}
      const actor = preferredActorLabel();
      const deviceParam = `&device_id=${{encodeURIComponent(state.shellDeviceId || "")}}`;
      state.shellStateRefreshPromise = (async () => {{
        const data = mergeDashboardState(await loadJSON(`/api/shell-state?actor=${{encodeURIComponent(actor)}}${{deviceParam}}`));
        state.lastShellStateRefreshAt = Date.now();
        return applyShellChrome(data, options);
      }})();
      try {{
        return await state.shellStateRefreshPromise;
      }} finally {{
        state.shellStateRefreshPromise = null;
      }}
    }}

    async function refreshDashboard(options = {{}}) {{
      const force = Boolean(options.force);
      const minIntervalMs = Number.isFinite(options.minIntervalMs) ? options.minIntervalMs : 0;
      const now = Date.now();
      if (!force && state.dashboardRefreshPromise) {{
        return state.dashboardRefreshPromise;
      }}
      if (!force && state.dashboard && minIntervalMs > 0 && (now - state.lastDashboardRefreshAt) < minIntervalMs) {{
        return state.dashboard;
      }}
      const actor = preferredActorLabel();
      const deviceParam = `&device_id=${{encodeURIComponent(state.shellDeviceId || "")}}`;
      state.dashboardRefreshPromise = (async () => {{
        const data = mergeDashboardState(await loadJSON(`/api/dashboard?actor=${{encodeURIComponent(actor)}}${{deviceParam}}`));
        state.lastDashboardRefreshAt = Date.now();
        state.lastShellStateRefreshAt = state.lastDashboardRefreshAt;
        return applyShellChrome(data, options);
      }})();
      try {{
        return await state.dashboardRefreshPromise;
      }} finally {{
        state.dashboardRefreshPromise = null;
      }}
    }}

    function spokenStatusSummary(data = {{}}) {{
      const cards = data.cards || {{}};
      const assistantSurface = data.assistant_surface || {{}};
      const activeMode = data.active_mode || {{}};
      const bodySummary = String(cards.body?.summary || "").trim();
      const homeSummary = homeConnectorLive(data) ? String(cards.home?.summary || "").trim() : "";
      const missionSummary = String(cards.mission?.summary || "").trim();
      const topLine = String((assistantSurface.briefing_lines || [])[0] || "").trim();
      const modeLine = [activeMode.mode, activeMode.status].filter(Boolean).join(" ");
      const worldPressure = String(data.world_state?.pressure || data.cognitive?.world_state?.pressure || "").trim();
      const parts = [
        topLine,
        bodySummary,
        homeSummary,
        missionSummary,
        modeLine ? `Mode is ${{modeLine}}.` : "",
        worldPressure ? `World pressure is ${{worldPressure}}.` : "",
      ]
        .map((item) => String(item || "").trim())
        .filter(Boolean);
      if (!parts.length) {{
        return "Status update complete. No urgent changes are surfaced right now.";
      }}
      return parts.slice(0, 4).join(" ");
    }}

    async function runImmediateStatusUpdate(trigger = "manual") {{
      clearConversationWindow();
      stopRecognition();
      stopSpeaking();
      setVoiceState("responding", trigger === "double-clap" ? "Storm front acknowledged. Running status now." : "Running status update.");
      const data = await refreshShellState();
      const spoken = spokenStatusSummary(data);
      document.getElementById("last-jarvis-text").textContent = spoken;
      syncTranscriptRail();
      const packet = data.assistant_surface?.auto_open_packet || "today";
      openPacket(packet);
      await speakText(spoken);
    }}

    async function enableBrowserAlerts() {{
      if (!browserAlertsSupported()) {{
        throw new Error("Browser notifications are not supported on this device.");
      }}
      if (Notification.permission === "granted") {{
        state.browserAlertsPermission = "granted";
        saveBrowserAlertsEnabled(true);
        return true;
      }}
      const permission = await Notification.requestPermission();
      state.browserAlertsPermission = permission;
      if (permission === "granted") {{
        saveBrowserAlertsEnabled(true);
        return true;
      }}
      saveBrowserAlertsEnabled(false);
      return false;
    }}

    function disableBrowserAlerts() {{
      saveBrowserAlertsEnabled(false);
    }}

    async function deliverAssistantBrowserAlerts() {{
      if (!browserAlertsReady()) {{
        return [];
      }}
      const actor = preferredActorLabel();
      const params = new URLSearchParams({{
        actor,
        device_id: state.shellDeviceId || "",
        limit: "3",
      }});
      const payload = await loadJSON(`/api/assistant-core/browser-alerts?${{params.toString()}}`);
      const items = Array.isArray(payload.items) ? payload.items : [];
      for (const item of items) {{
        const title = item.title || "Assistant item";
        const detail = item.detail || item.why_this_surfaced_now || "JARVIS has something ready for you.";
        const packet = item.packet || "today";
        const notification = new Notification(title, {{
          body: detail,
          tag: item.notification_id || item.surface_key || title,
          renotify: false,
        }});
        notification.onclick = () => {{
          window.focus();
          state.lastBriefing = detail;
          document.getElementById("last-jarvis-text").textContent = detail;
          syncTranscriptRail();
          openPacket(packet);
          loadJSON(`/api/assistant-core/notifications/${{encodeURIComponent(item.notification_id)}}`, {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ actor, status: "opened" }}),
          }}).catch(() => null);
          notification.close();
        }};
        await loadJSON(`/api/assistant-core/notifications/${{encodeURIComponent(item.notification_id)}}/delivered`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ actor, device_id: state.shellDeviceId || "" }}),
        }});
      }}
      return items;
    }}

    async function runAssistantAutonomySweep() {{
      if (!state.browserAlertsEnabled && !state.signalRailExpanded && !state.packet) {{
        return null;
      }}
      const actor = preferredActorLabel();
      const tick = await loadJSON(`/api/assistant-core/tick?actor=${{encodeURIComponent(actor)}}`);
      if (tick.assistant_surface) {{
        state.dashboard = {{
          ...(state.dashboard || {{}}),
          open_loops: tick.open_loops || state.dashboard?.open_loops || null,
          today_board: tick.today_board || state.dashboard?.today_board || null,
          cognitive: tick.cognitive || state.dashboard?.cognitive || null,
          assistant_surface: tick.assistant_surface,
        }};
        if (state.signalRailExpanded) {{
          fillSignalRail(state.dashboard);
        }}
        if (state.packetStripExpanded) {{
          fillPacketStrip();
        }}
      }}
      const surfaceKey = tick.assistant_surface?.surface_key || "";
      const suggestedPacket = tick.assistant_surface?.auto_open_packet || "";
      const manualPacketIntentActive = Number(state.manualPacketIntentUntil || 0) > Date.now();
      const initialPacketIntentActive = Boolean(state.initialPacketOverride);
      if (
        tick.should_surface &&
        suggestedPacket &&
        surfaceKey &&
        !manualPacketIntentActive &&
        !initialPacketIntentActive &&
        !document.body.classList.contains("modal-open") &&
        !state.packet &&
        state.lastAssistantSurfaceKey !== surfaceKey
      ) {{
        saveAssistantSurfaceKey(surfaceKey);
        document.getElementById("last-jarvis-text").textContent =
          (tick.assistant_surface.briefing_lines && tick.assistant_surface.briefing_lines[0]) ||
          "JARVIS has resurfaced work that matters now.";
        syncTranscriptRail();
        openPacket(suggestedPacket);
      }}
      if (await maybeAutoOpenCadenceReview(state.dashboard?.assistant_notifications || {{}})) {{
        return tick;
      }}
      if (state.browserAlertsEnabled) {{
        await deliverAssistantBrowserAlerts().catch((error) => console.warn("Assistant browser alerts failed", error));
      }}
      return tick;
    }}

    function scheduleAssistantAutonomy() {{
      if (state.autonomyTickTimer) {{
        window.clearInterval(state.autonomyTickTimer);
      }}
      state.autonomyTickTimer = window.setInterval(() => {{
        runAssistantAutonomySweep().catch((error) => console.warn("Assistant autonomy sweep failed", error));
      }}, 600000);
    }}

    async function runAssistantBackgroundAutonomy() {{
      if (!state.browserAlertsEnabled) {{
        return null;
      }}
      const actor = preferredActorLabel();
      const result = await loadJSON("/api/assistant-core/background-run", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ actors: [actor] }}),
      }});
      await refreshDashboard();
      if (await maybeAutoOpenCadenceReview(state.dashboard?.assistant_notifications || {{}})) {{
        return result;
      }}
      await deliverAssistantBrowserAlerts().catch((error) => console.warn("Assistant browser alerts failed", error));
      return result;
    }}

    function wireTodayBoardActions() {{
      const enable = document.getElementById("enable-browser-alerts");
      if (enable) {{
        enable.addEventListener("click", async () => {{
          try {{
            const enabled = await enableBrowserAlerts();
            document.getElementById("last-jarvis-text").textContent = enabled
              ? "Browser alerts are live. JARVIS can now nudge this device when assistant work crosses a threshold."
              : "Browser alerts were not enabled.";
            syncTranscriptRail();
            openPacket("today");
            await deliverAssistantBrowserAlerts().catch(() => null);
          }} catch (error) {{
            document.getElementById("last-jarvis-text").textContent = error.message || "Browser alerts are unavailable.";
            syncTranscriptRail();
          }}
        }});
      }}
      const disable = document.getElementById("disable-browser-alerts");
      if (disable) {{
        disable.addEventListener("click", () => {{
          disableBrowserAlerts();
          document.getElementById("last-jarvis-text").textContent = "Browser alerts are muted for this device.";
          syncTranscriptRail();
          openPacket("today");
        }});
      }}
    }}

    function wireReviewActions() {{
      document.querySelectorAll(".review-action-button").forEach((button) => {{
        button.addEventListener("click", async () => {{
          const actor = preferredActorLabel();
          const domain = button.dataset.domain || "";
          const itemId = button.dataset.itemId || "";
          const action = button.dataset.action || "";
          if (!domain || !itemId || !action) {{
            return;
          }}
          try {{
            await loadJSON("/api/open-loops/action", {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify({{
                actor,
                domain,
                item_id: itemId,
                action,
                note: "review-packet",
              }}),
            }});
            await refreshDashboard();
            openPacket("review");
          }} catch (error) {{
            document.getElementById("last-jarvis-text").textContent = error.message || "Review action failed.";
            syncTranscriptRail();
          }}
        }});
      }});
    }}

    function wireAssistantInboxActions(returnPacket = "today") {{
      document.querySelectorAll(".assistant-inbox-open").forEach((button) => {{
        button.addEventListener("click", async () => {{
          const actor = preferredActorLabel();
          const notificationId = button.dataset.notificationId || "";
          const packet = button.dataset.packet || "today";
          try {{
            if (notificationId) {{
              await loadJSON(`/api/assistant-core/notifications/${{encodeURIComponent(notificationId)}}`, {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{ actor, status: "opened" }}),
              }});
            }}
            await refreshDashboard();
            openPacket(packet);
          }} catch (error) {{
            document.getElementById("last-jarvis-text").textContent = error.message || "Assistant inbox action failed.";
            syncTranscriptRail();
          }}
        }});
      }});

      document.querySelectorAll(".assistant-inbox-ignore").forEach((button) => {{
        button.addEventListener("click", async () => {{
          const actor = preferredActorLabel();
          const notificationId = button.dataset.notificationId || "";
          if (!notificationId) {{
            return;
          }}
          try {{
            await loadJSON(`/api/assistant-core/notifications/${{encodeURIComponent(notificationId)}}`, {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify({{ actor, status: "ignored" }}),
            }});
            await refreshDashboard();
            openPacket(returnPacket);
          }} catch (error) {{
            document.getElementById("last-jarvis-text").textContent = error.message || "Assistant inbox ignore failed.";
            syncTranscriptRail();
          }}
        }});
      }});
    }}

    function scheduleAssistantBackgroundRun() {{
      if (state.autonomyBackgroundTimer) {{
        window.clearInterval(state.autonomyBackgroundTimer);
      }}
      state.autonomyBackgroundTimer = window.setInterval(() => {{
        runAssistantBackgroundAutonomy().catch((error) => console.warn("Assistant background autonomy run failed", error));
      }}, 600000);
    }}

    async function loadBriefing() {{
      const actor = document.getElementById("actor").value || "Chris";
      const firstLight = await checkFirstLight(true).catch(() => null);
      if (firstLight?.eligible) {{
        return;
      }}
      const data = await loadJSON(`/api/briefing?actor=${{encodeURIComponent(actor)}}`);
      state.firstLight = null;
      state.lastBriefing = data.briefing || "";
      document.getElementById("last-jarvis-text").textContent = state.lastBriefing || "Briefing unavailable.";
      syncTranscriptRail();
      openPacket("briefing");
      await speakText(state.lastBriefing);
    }}

    async function checkFirstLight(force = false) {{
      const preferredActor =
        state.sessionIdentity?.resolved_actor_label ||
        document.getElementById("actor")?.value ||
        "Chris";
      const timezoneName = Intl.DateTimeFormat().resolvedOptions().timeZone || "America/New_York";
      const params = new URLSearchParams({{
        actor: preferredActor,
        device_id: state.shellDeviceId || "",
        timezone_name: timezoneName,
        force: force ? "true" : "false",
      }});
      const data = await loadJSON(`/api/first-light?${{params.toString()}}`);
      if (!data.eligible || !data.packet) {{
        return data;
      }}
      state.firstLight = data.packet;
      state.lastBriefing = data.packet.spoken_summary || data.packet.opening || "";
      document.getElementById("last-jarvis-text").textContent = state.lastBriefing || "First Light ready.";
      syncTranscriptRail();
      openPacket("briefing");
      return data;
    }}

    function stopSpeaking() {{
      stopAudioReactivePulse();
      if (window.speechSynthesis) {{
        window.speechSynthesis.cancel();
      }}
      if (state.currentAudio) {{
        state.currentAudio.pause();
        state.currentAudio.src = "";
        state.currentAudio = null;
      }}
      if (state.currentAudioUrl) {{
        URL.revokeObjectURL(state.currentAudioUrl);
        state.currentAudioUrl = "";
      }}
      if (state.speakingTimer) {{
        clearTimeout(state.speakingTimer);
        state.speakingTimer = null;
      }}
      setVoiceState("idle", 'Standing by for "Hey Jarvis", "Jarvis", or a double clap.');
      if (state.alwaysOnMicEnabled) {{
        queueAlwaysOnListening();
      }}
    }}

    function speakWithBrowserFallback(text) {{
      if ("speechSynthesis" in window) {{
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.92;
        utterance.pitch = 0.9;
        utterance.onstart = () => {{
          stopRecognition();
          setVoiceState("speaking", "JARVIS fallback voice is speaking.");
        }};
        utterance.onend = () => {{
          armImmediateReplyWindow(text);
          setVoiceState("idle", conversationWindowActive() ? "Awaiting your answer." : 'Standing by for "Hey Jarvis", "Jarvis", or a double clap.');
          queueAlwaysOnListening();
        }};
        utterance.onerror = () => {{
          setVoiceState("idle", "Voice output unavailable. Standing by.");
          queueAlwaysOnListening();
        }};
        window.speechSynthesis.speak(utterance);
        return true;
      }}
      return false;
    }}

    function voiceHeaderValue(headers, names) {{
      for (const name of names) {{
        const value = headers?.get?.(name);
        if (value) {{
          return value;
        }}
      }}
      return "";
    }}

    function compactPreviewReason(value, fallback = "") {{
      const text = String(value || "").trim();
      if (!text) {{
        return fallback;
      }}
      return text.length > 160 ? `${{text.slice(0, 157)}}...` : text;
    }}

    function summarizeVoicePreviewResult(response) {{
      const headers = response?.headers;
      const requested = voiceHeaderValue(headers, [
        "X-Jarvis-Voice-Requested-Provider",
        "X-Jarvis-Tts-Requested-Provider",
      ]) || "auto";
      const effective = voiceHeaderValue(headers, [
        "X-Jarvis-Voice-Effective-Provider",
        "X-Jarvis-Tts-Effective-Provider",
        "X-Jarvis-Voice-Provider",
        "X-Jarvis-Tts-Provider",
      ]) || "unknown";
      const fallbackFrom = voiceHeaderValue(headers, ["X-Jarvis-Voice-Fallback-From"]);
      const blocker = compactPreviewReason(
        voiceHeaderValue(headers, [
          "X-Jarvis-Voice-Fallback-Reason",
          "X-Jarvis-Tts-Fallback-Reason",
        ]),
        "",
      );
      if (fallbackFrom || (requested && effective && requested !== effective && requested !== "auto")) {{
        return {{
          requested,
          effective,
          blocker,
          message: blocker
            ? `Preview requested ${{requested}}, but playback used ${{effective}}. Live blocker: ${{blocker}}`
            : `Preview requested ${{requested}}, but playback used ${{effective}}.`,
        }};
      }}
      return {{
        requested,
        effective,
        blocker,
        message: `Preview requested ${{requested}} and played with ${{effective}}.`,
      }};
    }}

    async function voiceErrorDetail(response) {{
      const fallback = `Voice output unavailable (${{response?.status || "unknown"}})`;
      if (!response) {{
        return fallback;
      }}
      try {{
        const clone = response.clone();
        const contentType = String(clone.headers?.get?.("Content-Type") || "").toLowerCase();
        if (contentType.includes("application/json")) {{
          const payload = await clone.json();
          return String(payload?.detail || payload?.error || fallback);
        }}
        const text = String(await clone.text()).trim();
        return text || fallback;
      }} catch (_error) {{
        return fallback;
      }}
    }}

    async function speakText(text, options = {{}}) {{
      if (!text) {{
        setVoiceState("idle", 'Standing by for "Hey Jarvis", "Jarvis", or a double clap.');
        return;
      }}
      stopSpeaking();
      if (!state.speechEnabled) {{
        setVoiceState("idle", "Voice output is muted. Reply window is still open.");
        const duration = Math.min(6000, Math.max(1800, text.length * 42));
        state.speakingTimer = window.setTimeout(() => {{
          armImmediateReplyWindow(text);
          setVoiceState("idle", conversationWindowActive() ? "Awaiting your answer." : 'Standing by for "Hey Jarvis", "Jarvis", or a double clap.');
          if (state.alwaysOnMicEnabled) {{
            queueAlwaysOnListening();
          }}
        }}, duration);
        return;
      }}
      try {{
        stopRecognition();
        // Epic 7: Use /api/voice/synthesize (FridayPersona text cleaning + provider cascade)
        // Falls back gracefully to /api/tts if voice pipeline is unavailable.
        const currentActorId = (typeof actor !== "undefined" ? actor : "") || "chris";
        const response = await fetch("/api/voice/synthesize", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ text, actor_id: currentActorId }})
        }}).catch(() =>
          // Fallback to legacy /api/tts if voice pipeline endpoint is unavailable
          fetch("/api/tts", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ text }})
          }})
        );
        if (!response.ok) {{
          const detail = await voiceErrorDetail(response);
          if (typeof options.onError === "function") {{
            options.onError(detail);
          }}
          throw new Error(detail);
        }}
        if (typeof options.onResult === "function") {{
          options.onResult(summarizeVoicePreviewResult(response));
        }}
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        state.currentAudio = audio;
        state.currentAudioUrl = audioUrl;
        audio.onplay = () => {{
          startAudioReactivePulse(audio);
          setVoiceState("speaking", "JARVIS is speaking.");
          // Notify server of speaking state for voice state tracking
          fetch("/api/voice/state", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ state: "speaking" }})
          }}).catch(() => {{}});
        }};
        audio.onended = () => {{
          stopAudioReactivePulse();
          if (state.currentAudio === audio) {{
            state.currentAudio = null;
          }}
          if (state.currentAudioUrl === audioUrl) {{
            URL.revokeObjectURL(audioUrl);
            state.currentAudioUrl = "";
          }}
          armImmediateReplyWindow(text);
          setVoiceState("idle", conversationWindowActive() ? "Awaiting your answer." : 'Standing by for "Hey Jarvis", "Jarvis", or a double clap.');
          queueAlwaysOnListening();
          // Notify server playback finished
          fetch("/api/voice/state", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ state: "idle" }})
          }}).catch(() => {{}});
        }};
        audio.onerror = () => {{
          stopAudioReactivePulse();
          if (state.currentAudio === audio) {{
            state.currentAudio = null;
          }}
          if (state.currentAudioUrl === audioUrl) {{
            URL.revokeObjectURL(audioUrl);
            state.currentAudioUrl = "";
          }}
          if (!speakWithBrowserFallback(text)) {{
            setVoiceState("idle", "Voice output unavailable. Standing by.");
            queueAlwaysOnListening();
          }}
          fetch("/api/voice/state", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ state: "idle" }})
          }}).catch(() => {{}});
        }};
        await audio.play();
      }} catch (error) {{
        console.error(error);
        if (!speakWithBrowserFallback(text)) {{
          setVoiceState("idle", "Voice output unavailable. Standing by.");
          queueAlwaysOnListening();
        }}
      }}
    }}

    function stopRecognition() {{
      clearRecognitionRestartTimer();
      if (state.recognizer && state.recognizing) {{
        state.recognizer.stop();
      }}
      if (!state.recognizer) {{
        state.recognitionMode = "idle";
      }}
    }}

    function setTalkButton(active, label = "Talk") {{
      const button = document.getElementById("voice-command");
      button.textContent = label;
      button.classList.toggle("primary", active);
    }}

    async function startVoiceCommand(options = {{}}) {{
      const automatic = Boolean(options.automatic);
      const mode = options.mode || (conversationWindowActive() ? "command" : "wake-guard");
      const wakeGuardMode = mode === "wake-guard";
      const Recognition = browserSpeechRecognition();
      if (!Recognition) {{
        document.getElementById("last-jarvis-text").textContent =
          "This browser does not expose speech recognition. Use typed input here, or we can wire server-side microphone capture next.";
        syncTranscriptRail();
        setVoiceState("idle", "No browser microphone recognition is available.");
        state.alwaysOnMicEnabled = false;
        refreshMicButton();
        return;
      }}
      if (!automatic) {{
        if (state.alwaysOnMicEnabled) {{
          disableAlwaysOnMic("Microphone guard disabled.");
        }} else {{
          enableAlwaysOnMic('Standing by for "Hey Jarvis", "Jarvis", or a double clap.');
        }}
        return;
      }}
      if (!state.alwaysOnMicEnabled) {{
        enableAlwaysOnMic('Standing by for "Hey Jarvis", "Jarvis", or a double clap.');
        return;
      }}
      if (state.recognizing || state.recognizer) {{
        return;
      }}

      stopSpeaking();
      const recognizer = new Recognition();
      clearRecognitionRestartTimer();
      state.recognizer = recognizer;
      state.recognitionMode = mode;
      recognizer.lang = "en-US";
      recognizer.interimResults = true;
      recognizer.continuous = false;
      recognizer.maxAlternatives = 1;
      let transcript = "";
      let finalTranscript = "";

      recognizer.onstart = () => {{
        state.recognizing = true;
        refreshMicButton();
        const detail = wakeGuardMode
          ? 'Standing by for "Hey Jarvis", "Jarvis", or a double clap.'
          : conversationWindowActive()
            ? "Listening for your answer."
            : "Listening now.";
        setVoiceState("listening", detail);
      }};

      recognizer.onresult = (event) => {{
        transcript = "";
        finalTranscript = "";
        for (let index = event.resultIndex; index < event.results.length; index += 1) {{
          const chunk = event.results[index][0]?.transcript || "";
          transcript += chunk;
          if (event.results[index].isFinal) {{
            finalTranscript += chunk;
          }}
        }}
        const spoken = (finalTranscript || transcript).trim();
        if (spoken && !wakeGuardMode) {{
          document.getElementById("last-user-text").textContent = spoken;
          document.getElementById("command-input").value = spoken;
          const ambientSubtitle = document.getElementById("ambient-subtitle");
          if (ambientSubtitle) ambientSubtitle.textContent = spoken;
          syncTranscriptRail();
        }}
      }};

      recognizer.onerror = (event) => {{
        state.recognizing = false;
        state.recognizer = null;
        state.recognitionMode = "idle";
        refreshMicButton();
        const code = event?.error || "unknown";
        if (code === "not-allowed" || code === "service-not-allowed") {{
          document.getElementById("last-jarvis-text").textContent =
            "Microphone access was blocked. Allow microphone permission for this page and try again.";
          syncTranscriptRail();
          disableAlwaysOnMic("Microphone permission is required.");
          return;
        }}
        if (code === "no-speech") {{
          setVoiceState("idle", conversationWindowActive() ? "Awaiting your answer." : 'Standing by for "Hey Jarvis", "Jarvis", or a double clap.');
          queueAlwaysOnListening();
          return;
        }}
        document.getElementById("last-jarvis-text").textContent = `Voice recognition error: ${{code}}`;
        syncTranscriptRail();
        setVoiceState("idle", "Voice recognition failed.");
        queueAlwaysOnListening(900);
      }};

      recognizer.onend = () => {{
        const spoken = (finalTranscript || transcript || "").trim();
        state.recognizing = false;
        state.recognizer = null;
        state.recognitionMode = "idle";
        refreshMicButton();
        if (spoken) {{
          handleRecognizedSpeech(spoken).catch((error) => {{
            document.getElementById("last-jarvis-text").textContent = error.message;
            syncTranscriptRail();
            setVoiceState("idle", "Command failed. Standing by.");
            queueAlwaysOnListening();
          }});
        }} else {{
          setVoiceState("idle", conversationWindowActive() ? "Awaiting your answer." : 'Standing by for "Hey Jarvis", "Jarvis", or a double clap.');
          queueAlwaysOnListening();
        }}
      }};

      recognizer.start();
    }}

    function packetFromRequest(request) {{
      const lowered = request.toLowerCase();
      if (lowered.includes("i want to") || lowered.includes("let's build") || lowered.includes("help me build") || lowered.includes("goal") || lowered.includes("plan for")) return "mission-control";
      if (lowered.includes("dashboard") || lowered.includes("full report")) return "dashboard";
      if (lowered.includes("finance review for passive income") || lowered.includes("wealth") || lowered.includes("fisk") || lowered.includes("passive income") || lowered.includes("market intelligence")) return "wealth";
      if (lowered.includes("family finances") || lowered.includes("family finance") || lowered.includes("spending") || lowered.includes("budget") || lowered.includes("cash") || lowered.includes("runway") || lowered.includes("finance review") || lowered.includes("finance")) return "finance-review";
      if (lowered.includes("today board") || lowered.includes("run my day") || lowered.includes("what needs my attention")) return "today";
      if (lowered.includes("mission control") || lowered.includes("mission") || lowered.includes("dossier") || lowered.includes("orchestrate")) return "mission-control";
      if (lowered.includes("brief") || lowered.includes("agenda") || lowered.includes("today")) return "briefing";
      if (lowered.includes("weather")) return "storm";
      if (lowered.includes("home") || lowered.includes("garage") || lowered.includes("freezer")) return "home";
      if (lowered.includes("family") || lowered.includes("dinner") || lowered.includes("grocery") || lowered.includes("calm version")) return "family";
      if (lowered.includes("security") || lowered.includes("door") || lowered.includes("arrival")) return "security";
      if (lowered.includes("camera") || lowered.includes("look at") || lowered.includes("look on") || lowered.includes("see this") || lowered.includes("desk")) return "vision";
      if (lowered.includes("chronicle") || lowered.includes("scripture") || lowered.includes("prayer")) return "chronicle";
      if (lowered.includes("model forge") || lowered.includes("forge viewer") || lowered.includes("forge")) return "model-forge";
      if (lowered.includes("workshop") || lowered.includes("printer") || lowered.includes("prototype")) return "workshop";
      if (lowered.includes("email") || lowered.includes("meeting") || lowered.includes("project plan") || lowered.includes("catalyst")) return "catalyst";
      if (lowered.includes("task") || lowered.includes("open loop") || lowered.includes("follow up")) return "tasks";
      if (lowered.includes("approve") || lowered.includes("approval")) return "approvals";
      return "";
    }}

    function catalystPageFromRequest(request) {{
      const lowered = request.toLowerCase();
      if (lowered.includes("calendar")) return "calendar";
      if (lowered.includes("meeting")) return "meetings";
      if (lowered.includes("project")) return "projects";
      if (lowered.includes("task")) return "tasks";
      if (lowered.includes("email") || lowered.includes("inbox") || lowered.includes("mail")) return "email";
      if (lowered.includes("contact")) return "contacts";
      if (lowered.includes("report")) return "reports";
      if (lowered.includes("setting") || lowered.includes("account")) return "settings";
      return "home";
    }}

    async function sendCommand(fromSpeech = false) {{
      const actor = document.getElementById("actor").value;
      const room = document.getElementById("room").value;
      const input = commandInputElement();
      const request = (input?.value || "").trim();
      if (!request) return;
      const attachmentsSnapshot = Array.isArray(state.pendingAttachments) ? state.pendingAttachments.map((item) => ({{ ...item }})) : [];
      setComposerBusy(true);
      if (!fromSpeech) {{
        resetCommandInput();
      }}
      clearConversationWindow();
      stopRecognition();
      document.getElementById("last-user-text").textContent = request;
      state.transcriptTurns = [
        ...(Array.isArray(state.transcriptTurns) ? state.transcriptTurns : []),
        {{
          role: "user",
          text: request,
          created_at: new Date().toISOString(),
        }},
      ];
      syncTranscriptRail();
      setVoiceState("responding", "JARVIS is reasoning.");
      const data = await loadJSON("/api/respond", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          actor,
          room,
          request,
          attachments: attachmentsSnapshot,
          conversation_id: state.conversationId || "",
          source: fromSpeech ? "voice" : "shell"
        }})
      }});
      updateSourceIndicator(data.provider || "standby", data.model || "");
      const output = data.output_text || "No response returned.";
      if (data.conversation_id) {{
        state.conversationId = data.conversation_id;
      }}
      if (data.active_conversation) {{
        applyConversationSnapshot(data.active_conversation);
      }} else {{
        document.getElementById("last-jarvis-text").textContent = output;
        syncTranscriptRail();
      }}
      const ambientSubtitle = document.getElementById("ambient-subtitle");
      if (ambientSubtitle) ambientSubtitle.textContent = output;
      refreshShellState({{ minIntervalMs: 10000 }}).catch((error) => console.warn("Shell state refresh failed", error));
      if (data.requested_packet) {{
        if (data.requested_packet === "catalyst" && data.requested_catalyst_page) {{
          state.catalystPage = data.requested_catalyst_page;
        }}
        openPacket(data.requested_packet);
      }}
      state.pendingAttachments = [];
      renderAttachmentTray();
      setComposerBusy(false);
      if (input) {{
        input.focus();
        autosizeCommandInput();
      }}
      await speakText(output);
    }}

    async function submitCommand(fromSpeech = false) {{
      const input = commandInputElement();
      const draft = String(input?.value || "");
      const attachmentDraft = Array.isArray(state.pendingAttachments) ? state.pendingAttachments.map((item) => ({{ ...item }})) : [];
      try {{
        await sendCommand(fromSpeech);
      }} catch (error) {{
        if (!fromSpeech && input && !input.value.trim() && draft.trim()) {{
          input.value = draft;
          autosizeCommandInput();
          input.focus();
        }}
        if (!state.pendingAttachments.length && attachmentDraft.length) {{
          state.pendingAttachments = attachmentDraft;
          renderAttachmentTray();
        }}
        document.getElementById("last-jarvis-text").textContent = error.message;
        syncTranscriptRail();
        setVoiceState("idle", fromSpeech ? "Voice command failed." : "Command failed. Standing by.");
        throw error;
      }} finally {{
        setComposerBusy(false);
      }}
    }}

    document.getElementById("send-command").addEventListener("click", () => {{
      submitCommand().catch(() => null);
    }});

    document.addEventListener("click", (event) => {{
      const actionButton = event.target instanceof Element ? event.target.closest(".work-item-action-button") : null;
      if (actionButton) {{
        event.preventDefault();
        const workId = actionButton.getAttribute("data-work-id") || "";
        const action = actionButton.getAttribute("data-work-action") || "";
        const recordId = actionButton.getAttribute("data-record-id") || "";
        const confirmMessage = actionButton.getAttribute("data-confirm-message") || "";
        if (!workId || !action) {{
          return;
        }}
        if (action === "inspect") {{
          loadLifecycleInspector(workId)
            .then(() => openPacket("lifecycle-inspector", {{ bypassScene: true }}))
            .catch((error) => {{
              document.getElementById("last-jarvis-text").textContent = error?.message || "Inspector failed to load.";
              syncTranscriptRail();
            }});
          return;
        }}
        if (action === "select-artifact") {{
          openWorkLifecycleArtifact(workId, recordId).catch((error) => {{
            document.getElementById("last-jarvis-text").textContent = error?.message || "Artifact failed to load.";
            syncTranscriptRail();
          }});
          return;
        }}
        if (confirmMessage && !window.confirm(confirmMessage)) {{
          return;
        }}
        actionButton.setAttribute("disabled", "disabled");
        performWorkLifecycleAction(workId, action)
          .catch((error) => {{
            document.getElementById("last-jarvis-text").textContent = error?.message || "Lifecycle action failed.";
            showLifecycleToast("Lifecycle Action Failed", error?.message || "Lifecycle action failed.");
            syncTranscriptRail();
          }})
          .finally(() => {{
            actionButton.removeAttribute("disabled");
          }});
        return;
      }}

      const artifactButton = event.target instanceof Element ? event.target.closest(".work-item-artifact-open") : null;
      if (artifactButton) {{
        event.preventDefault();
        const workId = artifactButton.getAttribute("data-work-id") || artifactButton.dataset.workId || "";
        const recordId = artifactButton.getAttribute("data-record-id") || artifactButton.dataset.recordId || "";
        openWorkLifecycleArtifact(workId, recordId).catch((error) => {{
          document.getElementById("last-jarvis-text").textContent = error?.message || "Artifact failed to load.";
          showLifecycleToast("Artifact Load Failed", error?.message || "Artifact failed to load.");
          syncTranscriptRail();
        }});
      }}
    }});

    document.getElementById("add-attachment").addEventListener("click", () => {{
      document.getElementById("chat-file-input").click();
    }});

    document.getElementById("chat-file-input").addEventListener("change", (event) => {{
      uploadChatFiles(event.target.files).catch((error) => {{
        document.getElementById("last-jarvis-text").textContent = error.message;
        syncTranscriptRail();
      }}).finally(() => {{
        event.target.value = "";
      }});
    }});

    document.getElementById("voice-command").addEventListener("click", () => {{
      startVoiceCommand({{ automatic: false }}).catch((error) => {{
        document.getElementById("last-jarvis-text").textContent = error.message;
        syncTranscriptRail();
        setVoiceState("idle", "Voice command failed.");
      }});
    }});

    document.getElementById("toggle-speech-output").addEventListener("click", () => {{
      const next = !state.speechEnabled;
      saveSpeechOutputEnabled(next);
      if (!next) {{
        stopSpeaking();
        document.getElementById("last-jarvis-text").textContent = "Voice output muted. JARVIS will stay in text unless you turn speech back on.";
      }} else {{
        document.getElementById("last-jarvis-text").textContent = "Voice output restored. JARVIS can speak again.";
      }}
      syncTranscriptRail();
    }});

    document.getElementById("mode-toggle").addEventListener("click", () => {{
      const panel = document.getElementById("mode-panel");
      if (panel.classList.contains("open")) {{
        closeModePanel();
      }} else {{
        openModePanel();
      }}
    }});
    document.getElementById("storm-weather-button").addEventListener("click", async () => {{
      try {{
        await refreshStormWeather(true);
      }} catch (error) {{
        console.warn("Storm shell refresh before modal open failed", error);
      }}
      openPacket("storm");
    }});
    document.getElementById("triage-summary-launcher")?.addEventListener("click", () => {{
      if (!state.triageSummaryVisible) {{
        openTriageSummary();
        return;
      }}
      state.windowStates.triageSummary.minimized = false;
      applyWindowFrame("triageSummary");
      bringWindowToFront("triageSummary");
    }});
    document.getElementById("dashboard-launcher")?.addEventListener("click", () => {{
      state.manualPacketIntentUntil = Date.now() + 5000;
      refreshDashboard({{ minIntervalMs: 10000 }})
        .catch(() => state.dashboard)
        .finally(() => openPacket("dashboard"));
    }});
    document.getElementById("finance-review-launcher")?.addEventListener("click", () => {{
      state.manualPacketIntentUntil = Date.now() + 5000;
      refreshFinanceReview({{ force: true }})
        .catch(() => state.financeReview)
        .finally(() => openPacket("finance-review"));
    }});
    document.getElementById("wealth-launcher")?.addEventListener("click", () => {{
      state.manualPacketIntentUntil = Date.now() + 5000;
      refreshWealthReview({{ force: true }})
        .catch(() => state.wealthReview)
        .finally(() => openPacket("wealth"));
    }});

    document.getElementById("mode-window-close").addEventListener("click", closeModePanel);
    document.getElementById("mode-window-minimize").addEventListener("click", () => toggleWindowMinimized("mode"));
    document.getElementById("mode-window-maximize").addEventListener("click", () => toggleWindowMaximized("mode"));
    document.getElementById("mode-panel-cancel").addEventListener("click", closeModePanel);
    document.getElementById("mode-panel-apply").addEventListener("click", () => {{
      applyModeTransition().catch((error) => {{
        document.getElementById("mode-panel-status").textContent = error.message;
      }});
    }});
    document.querySelector(".brain-graph-panel")?.addEventListener("click", () => {{
      if (state.layoutEditMode) {{
        return;
      }}
      openPacket("brains");
    }});
    document.getElementById("core-command-ring").addEventListener("pointerdown", (event) => {{
      event.stopPropagation();
    }});
    document.getElementById("core-command-ring").addEventListener("click", (event) => {{
      event.stopPropagation();
    }});
    document.getElementById("open-context-controls").addEventListener("click", () => {{
      const panel = document.getElementById("context-panel");
      if (panel.classList.contains("open")) {{
        closeContextPanel();
      }} else {{
        openContextPanel();
      }}
    }});
    document.getElementById("context-window-close").addEventListener("click", closeContextPanel);
    document.getElementById("context-window-minimize").addEventListener("click", () => toggleWindowMinimized("context"));
    document.getElementById("context-window-maximize").addEventListener("click", () => toggleWindowMaximized("context"));
    document.getElementById("context-panel-done").addEventListener("click", closeContextPanel);
    document.getElementById("triage-summary-close")?.addEventListener("click", closeTriageSummary);
    document.getElementById("triage-summary-minimize")?.addEventListener("click", () => toggleWindowMinimized("triageSummary"));
    document.getElementById("triage-summary-maximize")?.addEventListener("click", () => toggleWindowMaximized("triageSummary"));
    document.getElementById("core-home-summary")?.addEventListener("pointerdown", () => {{
      if (state.triageSummaryVisible) {{
        bringWindowToFront("triageSummary");
      }}
    }});
    document.getElementById("core-home-head")?.addEventListener("pointerdown", (event) => {{
      startWindowInteraction("triageSummary", event);
    }});
    document.getElementById("core-home-head")?.addEventListener("dblclick", () => {{
      toggleWindowMaximized("triageSummary");
    }});
    document.getElementById("mode-panel")?.addEventListener("pointerdown", () => bringWindowToFront("mode"));
    document.getElementById("context-panel")?.addEventListener("pointerdown", () => bringWindowToFront("context"));
    document.querySelector("#modal-layer .modal")?.addEventListener("pointerdown", () => bringWindowToFront("modal"));
    document.getElementById("mode-panel")?.querySelector(".mode-panel-head")?.addEventListener("pointerdown", (event) => {{
      startWindowInteraction("mode", event);
    }});
    document.getElementById("context-panel")?.querySelector(".context-panel-head")?.addEventListener("pointerdown", (event) => {{
      startWindowInteraction("context", event);
    }});
    document.querySelector("#modal-layer .modal-head")?.addEventListener("pointerdown", (event) => {{
      startWindowInteraction("modal", event);
    }});
    document.getElementById("mode-panel")?.querySelector(".mode-panel-head")?.addEventListener("dblclick", () => {{
      toggleWindowMaximized("mode");
    }});
    document.getElementById("context-panel")?.querySelector(".context-panel-head")?.addEventListener("dblclick", () => {{
      toggleWindowMaximized("context");
    }});
    document.querySelector("#modal-layer .modal-head")?.addEventListener("dblclick", () => {{
      toggleWindowMaximized("modal");
    }});
    document.getElementById("actor").addEventListener("change", () => {{
      state.conversationId = loadStoredConversationId(document.getElementById("actor")?.value || "Chris");
      state.transcriptTurns = [];
      renderTranscriptHistory();
      scheduleChatStateWarmup({{ actor: document.getElementById("actor")?.value || "Chris", delayMs: 80 }});
      syncContextPanelCopy();
    }});
    document.getElementById("room").addEventListener("change", syncContextPanelCopy);

    document.getElementById("signal-rail-toggle").addEventListener("click", () => {{
      toggleSignalRail(true);
    }});
    document.querySelectorAll("[data-home-open-packet]").forEach((button) => {{
      button.addEventListener("click", () => {{
        const packet = button.getAttribute("data-home-open-packet") || "";
        if (packet) {{
          openPacket(packet);
        }}
      }});
    }});
    document.querySelectorAll("[data-home-action='focus-speak']").forEach((button) => {{
      button.addEventListener("click", () => {{
        focusSpeakComposer();
      }});
    }});
    document.querySelector("#scene-stage .scene-shell-head")?.addEventListener("pointerdown", (event) => {{
      startWindowInteraction("scene", event);
    }});
    document.querySelector("#scene-stage .scene-shell-head")?.addEventListener("dblclick", () => {{
      toggleWindowMaximized("scene");
    }});
    document.getElementById("scene-window-close")?.addEventListener("click", () => {{
      closeScene();
    }});
    document.getElementById("scene-window-minimize")?.addEventListener("click", () => {{
      toggleWindowMinimized("scene");
    }});
    document.getElementById("scene-window-maximize")?.addEventListener("click", () => {{
      toggleWindowMaximized("scene");
    }});
    document.getElementById("scene-shell-refresh")?.addEventListener("click", () => {{
      const packetId = packetIdForScene(state.activeScene || "");
      const refresher = packetId === "today" ? refreshDashboard : refreshShellState;
      refresher({{ force: true }}).catch((error) => console.warn("Scene refresh failed", error));
    }});

    document.getElementById("design-review-launcher").addEventListener("click", () => {{
      toggleDesignReviewPanel();
    }});

    document.getElementById("design-review-start").addEventListener("click", () => {{
      startDesignReview();
    }});

    document.getElementById("design-review-apply").addEventListener("click", () => {{
      applyDesignFeedback();
    }});

    document.getElementById("design-review-save").addEventListener("click", () => {{
      saveDesignReviewState();
    }});

    document.getElementById("design-review-input").addEventListener("input", (event) => {{
      const pageId = currentReviewPageId();
      const targets = getReviewTargetsForPage(pageId);
      if (!state.holoReview.active || !targets.length) {{
        return;
      }}
      const reviewState = currentReviewPageState(pageId);
      const current = targets[state.holoReview.index];
      if (!current) {{
        return;
      }}
      reviewState.notes.set(current.id, event.target.value);
      try {{
        window.localStorage.setItem(HOLO_REVIEW_STORAGE_KEY, JSON.stringify(buildDesignReviewPayload()));
      }} catch (error) {{
        console.error(error);
      }}
    }});

    document.getElementById("design-review-keep").addEventListener("click", () => {{
      keepCurrentDesignElement();
    }});

    document.getElementById("design-review-remove").addEventListener("click", () => {{
      removeCurrentDesignElement();
    }});

    document.getElementById("design-review-next").addEventListener("click", () => {{
      moveDesignReview(1);
    }});

    document.getElementById("design-review-stop").addEventListener("click", () => {{
      stopDesignReview();
    }});

    document.getElementById("command-input").addEventListener("keydown", (event) => {{
      if (event.key === "Enter" && !event.shiftKey) {{
        event.preventDefault();
        submitCommand().catch(() => null);
      }}
    }});
    document.getElementById("command-input").addEventListener("input", () => {{
      autosizeCommandInput();
    }});
    document.querySelectorAll("[data-layout-drag]").forEach((node) => {{
      node.addEventListener("pointerdown", (event) => {{
        startLayoutInteraction("panel", "drag", node.getAttribute("data-layout-drag"), event);
      }});
    }});
    document.querySelectorAll("[data-layout-resize]").forEach((node) => {{
      node.addEventListener("pointerdown", (event) => {{
        startLayoutInteraction("panel", "resize", node.getAttribute("data-layout-resize"), event);
      }});
    }});
    document.querySelectorAll("[data-layout-modal-drag]").forEach((node) => {{
      node.addEventListener("pointerdown", (event) => {{
        startLayoutInteraction("modal", "drag", state.packet || "", event);
      }});
    }});
    document.querySelectorAll("[data-layout-modal-resize]").forEach((node) => {{
      node.addEventListener("pointerdown", (event) => {{
        startLayoutInteraction("modal", "resize", state.packet || "", event);
      }});
    }});
    window.addEventListener("pointermove", (event) => {{
      updateLayoutInteraction(event);
    }});
    window.addEventListener("pointerup", () => {{
      endLayoutInteraction();
    }});
    ["dragenter", "dragover"].forEach((eventName) => {{
      document.getElementById("attachment-dropzone").addEventListener(eventName, (event) => {{
        event.preventDefault();
        state.attachmentDragActive = true;
        renderAttachmentTray();
      }});
      document.getElementById("command-input").addEventListener(eventName, (event) => {{
        event.preventDefault();
        state.attachmentDragActive = true;
        renderAttachmentTray();
      }});
    }});
    ["dragleave", "dragend"].forEach((eventName) => {{
      document.getElementById("attachment-dropzone").addEventListener(eventName, () => {{
        state.attachmentDragActive = false;
        renderAttachmentTray();
      }});
    }});
    ["drop"].forEach((eventName) => {{
      document.getElementById("attachment-dropzone").addEventListener(eventName, (event) => {{
        event.preventDefault();
        state.attachmentDragActive = false;
        renderAttachmentTray();
        uploadChatFiles(event.dataTransfer?.files || []).catch((error) => {{
          document.getElementById("last-jarvis-text").textContent = error.message;
          syncTranscriptRail();
        }});
      }});
      document.getElementById("command-input").addEventListener(eventName, (event) => {{
        event.preventDefault();
        state.attachmentDragActive = false;
        renderAttachmentTray();
        uploadChatFiles(event.dataTransfer?.files || []).catch((error) => {{
          document.getElementById("last-jarvis-text").textContent = error.message;
          syncTranscriptRail();
        }});
      }});
    }});

    document.getElementById("open-settings").addEventListener("click", () => {{
      openSettings();
    }});

    document.getElementById("modal-window-close").id = "close-modal";
    document.getElementById("close-modal").addEventListener("click", closePacket);
    document.getElementById("packet-strip-toggle")?.addEventListener("click", () => {{
      togglePacketStrip();
    }});
    document.getElementById("packet-strip")?.addEventListener("click", (event) => {{
      const button = event.target instanceof Element ? event.target.closest("[data-packet]") : null;
      if (!button) {{
        return;
      }}
      openPacketTarget({{
        packet: button.getAttribute("data-packet") || "",
      }});
    }});
    document.getElementById("modal-window-minimize").addEventListener("click", () => toggleWindowMinimized("modal"));
    document.getElementById("modal-window-maximize").addEventListener("click", () => toggleWindowMaximized("modal"));
    document.getElementById("modal-layer").addEventListener("click", (event) => {{
      if (event.target.id === "modal-layer") {{
        closePacket();
      }}
    }});

    window.addEventListener("keydown", (event) => {{
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "m" && state.activeWindowId) {{
        event.preventDefault();
        toggleWindowMinimized(state.activeWindowId);
        return;
      }}
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "f" && state.activeWindowId) {{
        event.preventDefault();
        toggleWindowMaximized(state.activeWindowId);
        return;
      }}
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "w") {{
        if (state.activeWindowId === "triageSummary") {{
          event.preventDefault();
          closeTriageSummary();
          return;
        }}
        if (state.activeWindowId === "scene") {{
          event.preventDefault();
          closeScene();
          return;
        }}
        if (state.activeWindowId === "modal") {{
          event.preventDefault();
          closePacket();
          return;
        }}
        if (state.activeWindowId === "mode") {{
          event.preventDefault();
          closeModePanel();
          return;
        }}
        if (state.activeWindowId === "context") {{
          event.preventDefault();
          closeContextPanel();
          return;
        }}
      }}
      if (event.key === "Escape") {{
        state.coreCommandOpen = false;
        renderCoreCommandRing();
        closeContextPanel();
        closeModePanel();
        if (!document.body.classList.contains("modal-open")) {{
          closeScene();
        }}
        closePacket();
      }}
    }});
    document.addEventListener("pointerdown", (event) => {{
      if (!state.coreCommandOpen) {{
        return;
      }}
      const path = typeof event.composedPath === "function" ? event.composedPath() : [];
      const clickedInsideMenu = path.some((node) => node?.id === "core-command-ring" || node?.id === "core-command-trigger");
      if (clickedInsideMenu) {{
        return;
      }}
      closeCoreCommandTree();
    }}, true);

    function connectEventStream() {{
      if (!shellEventStreamEnabled()) {{
        return;
      }}
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const socket = new WebSocket(`${{protocol}}://${{window.location.host}}${{SHELL_EVENT_STREAM_PATH}}`);
      socket.addEventListener("message", (event) => {{
        try {{
          const payload = JSON.parse(event.data);
          if (String(payload.type || "") === "finance-review.completed" && (state.packet === "finance-review" || state.financeReview)) {{
            refreshFinanceReview({{ force: true }})
              .then(() => {{
                if (state.packet === "finance-review") {{
                  openPacket("finance-review");
                }}
              }})
              .catch((error) => console.warn("Finance review refresh from event stream failed", error));
          }}
          if (String(payload.type || "").startsWith("autonomous-workstream.") && (state.packet === "wealth" || state.wealthReview)) {{
            refreshWealthReview({{ force: true }})
              .then(() => {{
                if (state.packet === "wealth") {{
                  openPacket("wealth");
                }}
              }})
              .catch((error) => console.warn("Wealth review refresh from event stream failed", error));
          }}
          if (payload.dashboard) {{
            mergeDashboardState(payload.dashboard);
            applyShellChrome(state.dashboard).catch((error) => console.warn("Dashboard event apply failed", error));
            return;
          }}
          if (payload.shell_state) {{
            mergeDashboardState(payload.shell_state);
            applyShellChrome(state.dashboard, {{ reopenPacket: false }}).catch((error) => console.warn("Shell state event apply failed", error));
            return;
          }}
          if (payload.refresh) {{
            const refresher = state.packet ? refreshDashboard : refreshShellState;
            refresher().catch((error) => console.warn("Refresh from event stream failed", error));
          }}
        }} catch (error) {{
          console.warn("JARVIS event stream parse error", error);
        }}
      }});
      socket.addEventListener("close", () => {{
        window.setTimeout(connectEventStream, 1500);
      }});
    }}

    function updateCoreDockMode() {{
      const mobileStack = window.innerWidth <= 1080;
      const compactThreshold = 1480;
      const quietHome = chamberHomeModeActive();
      const shouldDockCorner = !quietHome && !mobileStack && window.innerWidth < compactThreshold;
      document.body.dataset.coreDock = shouldDockCorner ? "corner" : "center";
      if (quietHome) {{
        state.windowPlacements.triageSummary = defaultTriageSummaryPlacement();
      }}
      applyPanelLayouts();
      applyModalPlacement();
    }}

    function clampFloatingBox(left, top, width, height) {{
      const margin = 16;
      const maxLeft = Math.max(margin, window.innerWidth - width - margin);
      const maxTop = Math.max(78, window.innerHeight - height - margin);
      return {{
        left: Math.min(Math.max(margin, left), maxLeft),
        top: Math.min(Math.max(78, top), maxTop),
      }};
    }}

    function panelCanFloat(panelId) {{
      if (window.innerWidth <= 1080) return false;
      if (document.body.dataset.coreDock === "corner") return false;
      return true;
    }}

    function getPanelMeta(panelId) {{
      return {{
        status: {{ selector: "#status-panel", minWidth: 220, minHeight: 160, maxWidth: 520, maxHeight: 720 }},
        brain: {{ selector: "#brain-panel", minWidth: 220, minHeight: 220, maxWidth: 520, maxHeight: 720 }},
        chat: {{ selector: "#chat-panel", minWidth: 420, minHeight: 480, maxWidth: 900, maxHeight: 860 }},
        core: {{ selector: "#core-panel", minWidth: 320, minHeight: 320, maxWidth: 880, maxHeight: 880, aspectRatio: 1 }},
      }}[panelId] || null;
    }}

    function getPanelElement(panelId) {{
      const meta = getPanelMeta(panelId);
      return meta ? document.querySelector(meta.selector) : null;
    }}

    function clampFloatingSize(panelId, width, height) {{
      const meta = getPanelMeta(panelId) || {{}};
      const minWidth = meta.minWidth || 220;
      const minHeight = meta.minHeight || 180;
      const maxWidth = Math.min(meta.maxWidth || window.innerWidth - 32, window.innerWidth - 32);
      const maxHeight = Math.min(meta.maxHeight || window.innerHeight - 96, window.innerHeight - 96);
      let nextWidth = Math.min(Math.max(minWidth, width), Math.max(minWidth, maxWidth));
      let nextHeight = Math.min(Math.max(minHeight, height), Math.max(minHeight, maxHeight));
      if (meta.aspectRatio) {{
        nextHeight = nextWidth / meta.aspectRatio;
        if (nextHeight > maxHeight) {{
          nextHeight = maxHeight;
          nextWidth = nextHeight * meta.aspectRatio;
        }}
      }}
      return {{ width: nextWidth, height: nextHeight }};
    }}

    function defaultPanelLayout(panelId, element) {{
      const rect = element?.getBoundingClientRect();
      const meta = getPanelMeta(panelId) || {{}};
      const baseWidth = rect?.width || meta.minWidth || 320;
      const baseHeight = rect?.height || meta.minHeight || 220;
      const size = clampFloatingSize(panelId, baseWidth, baseHeight);
      const defaultLeft = panelId === "chat"
        ? window.innerWidth - size.width - 20
        : (panelId === "core"
          ? Math.max(16, (window.innerWidth - size.width) / 2)
          : (rect?.left || 20));
      const defaultTop = panelId === "core"
        ? Math.max(92, (window.innerHeight - size.height) / 2)
        : (rect?.top || 110);
      const position = clampFloatingBox(defaultLeft, defaultTop, size.width, size.height);
      return {{
        floating: false,
        left: position.left,
        top: position.top,
        width: size.width,
        height: size.height,
      }};
    }}

    function applyPanelLayout(panelId) {{
      const element = getPanelElement(panelId);
      if (!element) return;
      const saved = state.panelLayouts?.[panelId] || defaultPanelLayout(panelId, element);
      const shouldFloat = !!saved.floating && panelCanFloat(panelId);
      element.classList.toggle("floating", shouldFloat);
      if (!shouldFloat) {{
        element.style.left = "";
        element.style.top = "";
        element.style.width = "";
        element.style.height = "";
        return;
      }}
      const size = clampFloatingSize(panelId, Number(saved.width || element.offsetWidth || 0), Number(saved.height || element.offsetHeight || 0));
      const position = clampFloatingBox(
        Number.isFinite(saved.left) ? Number(saved.left) : 20,
        Number.isFinite(saved.top) ? Number(saved.top) : 110,
        size.width,
        size.height
      );
      element.style.left = `${{position.left}}px`;
      element.style.top = `${{position.top}}px`;
      element.style.width = `${{size.width}}px`;
      if (panelId === "core") {{
        element.style.height = `${{size.height}}px`;
      }} else {{
        element.style.height = `${{size.height}}px`;
      }}
    }}

    function applyPanelLayouts() {{
      ["status", "brain", "chat", "core"].forEach((panelId) => applyPanelLayout(panelId));
    }}

    function applyModalPlacement() {{
      const modalLayer = document.getElementById("modal-layer");
      const modal = modalLayer?.querySelector(".modal");
      if (!modalLayer || !modal) return;
      const windowState = state.windowStates?.modal || {{}};
      const packetId = state.packet || "";
      const saved = packetId ? state.modalPlacements?.[packetId] : null;
      modal.classList.toggle("minimized", !!windowState.minimized);
      modal.classList.toggle("maximized", !!windowState.maximized);
      if (windowState.maximized) {{
        modalLayer.classList.add("layout-free");
        modal.classList.add("floating");
        modal.style.removeProperty("left");
        modal.style.removeProperty("top");
        modal.style.removeProperty("width");
        modal.style.removeProperty("height");
        return;
      }}
      const shouldFloat = !!saved && window.innerWidth > 1080;
      modalLayer.classList.toggle("layout-free", shouldFloat);
      modal.classList.toggle("floating", shouldFloat);
      if (!shouldFloat) {{
        modal.style.left = "";
        modal.style.top = "";
        modal.style.width = "";
        modal.style.height = "";
        return;
      }}
      const rect = modal.getBoundingClientRect();
      const width = Math.min(Math.max(520, Number(saved.width || rect.width || 920)), window.innerWidth - 32);
      const height = Math.min(Math.max(340, Number(saved.height || rect.height || 640)), window.innerHeight - 96);
      const next = clampFloatingBox(saved.left || rect.left, saved.top || rect.top, width, height);
      modal.style.left = `${{next.left}}px`;
      modal.style.top = `${{next.top}}px`;
      modal.style.width = `${{width}}px`;
      modal.style.height = `${{height}}px`;
    }}

    function resetLayoutPlacements() {{
      state.panelLayouts = {{}};
      state.chatPlacement = {{ floating: false, left: null, top: null }};
      state.modalPlacements = {{}};
      savePanelLayouts();
      saveChatPlacement();
      saveModalPlacements();
      applyPanelLayouts();
      applyModalPlacement();
    }}

    function startLayoutInteraction(target, mode, id, event) {{
      if (!state.layoutEditMode) return;
      if (target === "panel") {{
        const panelId = String(id || "");
        const element = getPanelElement(panelId);
        if (!element || !panelCanFloat(panelId)) return;
        const rect = element.getBoundingClientRect();
        state.panelLayouts[panelId] = {{
          floating: true,
          left: rect.left,
          top: rect.top,
          width: rect.width,
          height: rect.height,
        }};
        applyPanelLayout(panelId);
        state.dragState = {{
          target,
          panelId,
          mode,
          originX: event.clientX,
          originY: event.clientY,
          left: rect.left,
          top: rect.top,
          width: rect.width,
          height: rect.height,
        }};
      }} else if (target === "modal") {{
        const modal = document.querySelector("#modal-layer .modal");
        if (!modal || !state.packet) return;
        const rect = modal.getBoundingClientRect();
        state.modalPlacements[state.packet] = {{ left: rect.left, top: rect.top, width: rect.width, height: rect.height }};
        applyModalPlacement();
        state.dragState = {{
          target,
          mode,
          packetId: state.packet,
          originX: event.clientX,
          originY: event.clientY,
          left: rect.left,
          top: rect.top,
          width: rect.width,
          height: rect.height,
        }};
      }}
      if (state.dragState) {{
        document.body.classList.toggle("dragging-layout", mode === "drag");
        document.body.classList.toggle("resizing-layout", mode === "resize");
        event.stopPropagation();
        event.preventDefault();
      }}
    }}

    function updateLayoutInteraction(event) {{
      if (!state.dragState) return;
      const dx = event.clientX - state.dragState.originX;
      const dy = event.clientY - state.dragState.originY;
      if (state.dragState.target === "panel") {{
        const panelId = state.dragState.panelId;
        if (!panelId) return;
        if (state.dragState.mode === "drag") {{
          const next = clampFloatingBox(
            state.dragState.left + dx,
            state.dragState.top + dy,
            state.dragState.width,
            state.dragState.height
          );
          state.panelLayouts[panelId] = {{
            ...(state.panelLayouts[panelId] || {{}}),
            floating: true,
            left: next.left,
            top: next.top,
            width: state.dragState.width,
            height: state.dragState.height,
          }};
        }} else {{
          const size = clampFloatingSize(panelId, state.dragState.width + dx, state.dragState.height + dy);
          state.panelLayouts[panelId] = {{
            ...(state.panelLayouts[panelId] || {{}}),
            floating: true,
            left: state.dragState.left,
            top: state.dragState.top,
            width: size.width,
            height: size.height,
          }};
        }}
        applyPanelLayout(panelId);
      }} else if (state.dragState.target === "modal" && state.dragState.packetId) {{
        if (state.dragState.mode === "drag") {{
          const next = clampFloatingBox(
            state.dragState.left + dx,
            state.dragState.top + dy,
            state.dragState.width,
            state.dragState.height
          );
          state.modalPlacements[state.dragState.packetId] = {{
            ...(state.modalPlacements[state.dragState.packetId] || {{}}),
            left: next.left,
            top: next.top,
            width: state.dragState.width,
            height: state.dragState.height,
          }};
        }} else {{
          const width = Math.min(Math.max(520, state.dragState.width + dx), window.innerWidth - 32);
          const height = Math.min(Math.max(340, state.dragState.height + dy), window.innerHeight - 96);
          state.modalPlacements[state.dragState.packetId] = {{
            ...(state.modalPlacements[state.dragState.packetId] || {{}}),
            left: state.dragState.left,
            top: state.dragState.top,
            width,
            height,
          }};
        }}
        applyModalPlacement();
      }} else if (state.dragState.target === "window" && state.dragState.windowId) {{
        const windowId = state.dragState.windowId;
        const shell = getWindowShell(windowId);
        if (!shell) return;
        const next = clampFloatingBox(
          state.dragState.left + dx,
          state.dragState.top + dy,
          state.dragState.width,
          state.dragState.height
        );
        if (windowId === "modal" && state.packet) {{
          state.modalPlacements[state.packet] = {{
            ...(state.modalPlacements[state.packet] || {{}}),
            left: next.left,
            top: next.top,
            width: state.dragState.width,
            height: state.dragState.height,
          }};
          applyModalPlacement();
        }} else if (windowId === "triageSummary" || windowId === "mode" || windowId === "context" || windowId === "scene") {{
          state.windowPlacements[windowId] = {{
            ...(state.windowPlacements[windowId] || {{}}),
            left: next.left,
            top: next.top,
            width: state.dragState.width,
            height: state.dragState.height,
          }};
          applyWindowFrame(windowId);
        }}
      }}
    }}

    function endLayoutInteraction() {{
      if (!state.dragState) return;
      if (state.dragState.target === "panel") {{
        savePanelLayouts();
        if (state.panelLayouts.chat) {{
          state.chatPlacement = {{
            floating: !!state.panelLayouts.chat.floating,
            left: state.panelLayouts.chat.left ?? null,
            top: state.panelLayouts.chat.top ?? null,
          }};
        }}
        saveChatPlacement();
      }} else if (state.dragState.target === "modal") {{
        saveModalPlacements();
      }} else if (state.dragState.target === "window" && state.dragState.windowId === "modal") {{
        saveModalPlacements();
      }}
      state.dragState = null;
      document.body.classList.remove("dragging-layout", "resizing-layout");
    }}

    window.addEventListener("message", (event) => {{
      const data = event?.data || {{}};
      if (data.type === "chronicle:return-to-jarvis" || data.type === "catalyst:return-to-jarvis") {{
        const payload = data.payload || {{}};
        const summary = String(
          payload.summary ||
          (data.type === "chronicle:return-to-jarvis"
            ? "Chronicle sent a handoff back to JARVIS."
            : "Catalyst sent a handoff back to JARVIS.")
        );
        document.getElementById("last-jarvis-text").textContent = summary;
        state.transcriptTurns = [
          ...(Array.isArray(state.transcriptTurns) ? state.transcriptTurns : []),
          {{
            role: "assistant",
            text: summary,
            created_at: new Date().toISOString(),
          }},
        ];
        syncTranscriptRail();
        closePacket();
        setVoiceState(
          "idle",
          data.type === "chronicle:return-to-jarvis"
            ? "Chronicle handed the thread back to JARVIS."
            : "Catalyst handed the thread back to JARVIS."
        );
      }}
    }});

    // ============================================================
    // LIVING BRIEFING — Zone population functions
    // ============================================================
    function populateBriefingZone(items) {{
      const el = document.querySelector('.briefing-items');
      if (!el) return;
      if (!items || items.length === 0) {{
        el.innerHTML = '<p class="zone-empty">I\\'ve been watching. Here\\'s what matters.</p>';
        return;
      }}
      el.innerHTML = items.map(item => `
        <div class="briefing-item" data-priority="${{item.priority || 'normal'}}">
          <span class="briefing-dot"></span>
          <div class="briefing-content">
            <div class="briefing-text">${{item.text || item.message || item.summary || ''}}</div>
            ${{item.sub ? `<div class="briefing-sub">${{item.sub}}</div>` : ''}}
          </div>
        </div>
      `).join('');
    }}

    function populateAlreadyZone(items) {{
      const el = document.querySelector('.working-items');
      if (!el) return;
      if (!items || items.length === 0) {{
        el.innerHTML = '<p class="zone-empty">Agents standing by.</p>';
        return;
      }}
      el.innerHTML = items.slice(0, 4).map(item => `
        <div class="working-item">
          <span class="working-agent">${{item.agent || item.label || 'JARVIS'}}</span>
          <span class="working-action">${{item.action || item.text || ''}}</span>
        </div>
      `).join('');
    }}

    function populateNeedsZone(items) {{
      const el = document.querySelector('.needs-items');
      if (!el) return;
      const badge = document.getElementById('needs-badge');
      if (!items || items.length === 0) {{
        el.innerHTML = '<p class="zone-empty">Nothing waiting.</p>';
        if (badge) {{ badge.style.display = 'none'; badge.textContent = '0'; }}
        return;
      }}
      if (badge) {{ badge.style.display = 'inline'; badge.textContent = String(items.length); }}
      el.innerHTML = items.map(item => `
        <div class="needs-item" data-id="${{item.id || ''}}">
          <div class="needs-text">${{item.text || item.message || ''}}</div>
          <div class="needs-actions">
            <button class="needs-btn needs-approve" onclick="approveNeedsItem('${{item.id || ''}}')">Approve</button>
            <button class="needs-btn needs-dismiss" onclick="dismissNeedsItem('${{item.id || ''}}')">Dismiss</button>
          </div>
        </div>
      `).join('');
    }}

    function populateDriftZone(items) {{
      const el = document.querySelector('.drift-items');
      if (!el) return;
      if (!items || items.length === 0) {{
        el.innerHTML = '<div class="drift-ok"><span class="drift-ok-dot"></span> On course.</div>';
        return;
      }}
      el.innerHTML = items.map(item => `
        <div class="drift-item" data-severity="${{item.severity || 'warn'}}">
          <span class="drift-indicator"></span>
          <span class="drift-text">${{item.text || item.message || ''}}</span>
        </div>
      `).join('');
    }}

    function populateLaunchZone(data) {{
      if (!data || !data.active_project) {{
        document.getElementById('zone-launch').style.display = 'none';
        return;
      }}
      document.getElementById('zone-launch').style.display = '';

      const p = data.active_project;

      // Header
      const daysToLaunch = p.days_to_launch >= 0
        ? `${{p.days_to_launch}}d to launch`
        : `${{Math.abs(p.days_to_launch)}}d post-launch`;
      document.getElementById('launch-project-header').innerHTML =
        `<span>${{p.title}}</span> <span style="opacity:0.6;font-size:0.85em;font-weight:400">${{p.phase}} · ${{daysToLaunch}}</span>`;

      // Tracks
      const tracks = [
        {{ label: 'Book',     done: p.book_chapters_done     || 0, total: p.book_chapters_total     || 0 }},
        {{ label: 'Workbook', done: p.workbook_chapters_done || 0, total: p.workbook_chapters_total || 0 }},
        {{ label: 'Course',   done: p.course_modules_done    || 0, total: p.course_modules_total    || 0 }},
      ];
      document.getElementById('launch-tracks').innerHTML = tracks.map(t => {{
        const pct = t.total > 0 ? Math.round((t.done / t.total) * 100) : 0;
        return `<div class="launch-track">
          <div class="launch-track-label">${{t.label}} · ${{t.done}}/${{t.total}}</div>
          <div class="launch-track-progress"><div class="launch-track-fill" style="width:${{pct}}%"></div></div>
        </div>`;
      }}).join('');

      // Reviews
      const reviewCount = data.pending_reviews || 0;
      document.getElementById('launch-reviews').innerHTML = reviewCount > 0
        ? `<span style="color:var(--warm)">📄 ${{reviewCount}} draft${{reviewCount > 1 ? 's' : ''}} waiting for your review</span> <button class="launch-action-btn" onclick="openReviews()">Review</button>`
        : `<span style="opacity:0.6">No drafts pending review</span>`;

      // Queue
      const queueTotal   = data.posts_scheduled         || 0;
      const queuePending = data.posts_pending_approval  || 0;
      document.getElementById('launch-queue').innerHTML =
        `📱 ${{queueTotal}} posts scheduled · <span style="color:var(--warm)">${{queuePending}} awaiting approval</span>`;

      // Performance (post-launch)
      const perf = data.performance || {{}};
      if (perf.amazon_rank || perf.coursera_enrollments || perf.top_post_engagement) {{
        document.getElementById('launch-performance').innerHTML = `<div class="launch-perf-row">
          ${{perf.amazon_rank          ? `<div class="launch-perf-item">Amazon Rank <div class="launch-perf-value">#${{perf.amazon_rank}}</div></div>` : ''}}
          ${{perf.coursera_enrollments ? `<div class="launch-perf-item">Enrollments <div class="launch-perf-value">${{perf.coursera_enrollments}}</div></div>` : ''}}
          ${{perf.top_post_engagement  ? `<div class="launch-perf-item">Top Post <div class="launch-perf-value">${{perf.top_post_engagement}} engagements</div></div>` : ''}}
        </div>`;
      }} else {{
        document.getElementById('launch-performance').innerHTML = '';
      }}

      // Next action
      const next = data.next_action || 'All caught up.';
      document.getElementById('launch-next-action').innerHTML = `<strong>Next:</strong> ${{next}}`;
    }}

    function openReviews() {{
      fetch('/api/publishing/reviews/pending')
        .then(r => r.json())
        .then(d => {{
          const reviews = d.reviews || d.pending || d || [];
          alert('Pending reviews:\n' + reviews.map(r => `• ${{r.title}} (${{r.track_type}} ch.${{r.chapter_number}})`).join('\n'));
        }})
        .catch(err => console.warn('openReviews fetch failed', err));
    }}

    function approveNeedsItem(id) {{
      if (!id) return;
      const item = document.querySelector(`.needs-item[data-id="${{id}}"]`);
      if (item) item.remove();
      const remaining = document.querySelectorAll('.needs-item').length;
      if (remaining === 0) populateNeedsZone([]);
      else {{ const badge = document.getElementById('needs-badge'); if (badge) badge.textContent = String(remaining); }}
    }}

    function dismissNeedsItem(id) {{
      if (!id) return;
      const item = document.querySelector(`.needs-item[data-id="${{id}}"]`);
      if (item) item.remove();
      const remaining = document.querySelectorAll('.needs-item').length;
      if (remaining === 0) populateNeedsZone([]);
      else {{ const badge = document.getElementById('needs-badge'); if (badge) badge.textContent = String(remaining); }}
    }}

    // Initialize zones with empty states on load
    populateBriefingZone([]);
    populateAlreadyZone([]);
    populateNeedsZone([]);
    populateDriftZone([]);
    populateLaunchZone(null);
    // ============================================================

    updateClock();
    window.setInterval(updateClock, 1000);
    saveLayoutEditMode(loadLayoutEditMode());
    state.panelLayouts = loadPanelLayouts();
    state.chatPlacement = loadChatPlacement();
    state.modalPlacements = loadModalPlacements();
    applyTriageSummaryVisibility();
    updateCoreDockMode();
    openTriageSummary();
    window.addEventListener("resize", () => {{
      updateCoreDockMode();
      applyWindowFrame("triageSummary");
      applyWindowFrame("scene");
      applyWindowFrame("mode");
      applyWindowFrame("context");
    }});
    state.speechEnabled = loadSpeechOutputEnabled();
    renderSpeechOutputToggle();
    state.browserAlertsEnabled = loadBrowserAlertsEnabled();
    state.browserAlertsPermission = browserAlertsSupported() ? Notification.permission : "unsupported";
    if (shellEventStreamEnabled()) {{
      connectEventStream();
    }}
    scheduleAssistantAutonomy();
    scheduleAssistantBackgroundRun();
    state.lastAssistantSurfaceKey = loadAssistantSurfaceKey();
    loadDesignReviewState().finally(() => {{
      ensureHoloCore();
      syncDesignReviewPanel();
    }});
    refreshVoiceSettings()
      .then(() => bindShellIdentity().catch(() => null))
      .then(() => refreshShellState())
      .then(() => {{
        state.conversationId = loadStoredConversationId(preferredActorLabel());
        scheduleChatStateWarmup({{ delayMs: 120 }});
        applyPacketOverrideFromUrl();
      }})
      .then(() => checkFirstLight().catch(() => null))
      .catch((error) => {{
        document.getElementById("last-jarvis-text").textContent = error.message;
        syncTranscriptRail();
      }})
      .finally(() => {{
        queueInitialPacketOpen();
      }});
    window.setTimeout(() => {{
      queueInitialPacketOpen();
    }}, 900);
    window.addEventListener("load", () => {{
      queueInitialPacketOpen();
    }});
    window.addEventListener("beforeunload", () => {{
      clearRecognitionRestartTimer();
      stopRecognition();
      stopDoubleClapGuard();
      stopAudioReactivePulse();
      if (state.holoCoreScene) {{
        if (state.holoCoreScene.frame) cancelAnimationFrame(state.holoCoreScene.frame);
        if (state.holoCoreScene.observer) state.holoCoreScene.observer.disconnect();
        state.holoCoreScene.renderer.dispose();
      }}
      if (state.audioContext) {{
        state.audioContext.close().catch(() => null);
      }}
      if (state.autonomyTickTimer) {{
        window.clearInterval(state.autonomyTickTimer);
      }}
      if (state.autonomyBackgroundTimer) {{
        window.clearInterval(state.autonomyBackgroundTimer);
      }}
    }});
    syncTranscriptRail();
    syncContextPanelCopy();
    autosizeCommandInput();
    renderAttachmentTray();
    fillPacketStrip();
    setActiveOverlay("");
    renderCoreCommandRing();
    enableAlwaysOnMic('Standing by for "Hey Jarvis", "Jarvis", or a double clap.');
  </script>
</body>
</html>"""
