from __future__ import annotations

import json

from .runtime import JarvisRuntime


def render_voice_shell(runtime: JarvisRuntime) -> str:
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
    packet_presets = json.dumps(
        [
            {"id": "today", "label": "Today"},
            {"id": "review", "label": "Review"},
            
            {"id": "briefing", "label": "Briefing"},
            {"id": "brains", "label": "Brains"},
            {"id": "agents", "label": "Agents"},
            {"id": "connected-devices", "label": "Devices"},
            {"id": "vision", "label": "Vision"},
            {"id": "model-forge", "label": "Model Forge"},
            {"id": "home", "label": "Home"},
            {"id": "family", "label": "Family"},
            {"id": "security", "label": "Security"},
            {"id": "chronicle", "label": "Chronicle"},
            {"id": "workshop", "label": "Workshop"},
            {"id": "catalyst", "label": "Catalyst"},
            {"id": "tasks", "label": "Tasks"},
            {"id": "approvals", "label": "Approvals"},
        ]
    )
    available_modes = json.dumps(modes)
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
      --shadow: 0 30px 80px rgba(0, 0, 0, 0.42);
      --energy: 0.45;
      --motion-rate: 1;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ height: 100%; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: #03060b url("/assets/Chamber.jpg") center center / cover no-repeat;
      overflow: hidden;
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
      min-height: 100%;
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
      background: rgba(10, 20, 34, 0.5);
      color: var(--ink);
    }}
    .meta-chip,
    .signal-chip {{
      padding: 6px 12px;
      white-space: nowrap;
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
      place-items: center;
      min-height: 0;
      overflow: hidden;
    }}
    .signal-rail-toggle {{
      position: absolute;
      right: 0;
      top: 22px;
      z-index: 5;
      min-width: 122px;
      border-radius: 999px;
      border: 1px solid rgba(111, 229, 255, 0.28);
      background: rgba(7, 16, 27, 0.76);
      color: var(--cyan);
      box-shadow: 0 0 20px rgba(111, 229, 255, 0.12);
    }}
    .signal-rail-toggle.hidden {{
      opacity: 0;
      pointer-events: none;
    }}
    .signal-rail {{
      position: absolute;
      right: 0;
      top: 22px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      align-items: end;
      max-width: min(36vw, 560px);
      transition: opacity 180ms ease, transform 180ms ease;
    }}
    .signal-rail.collapsed {{
      display: none;
      opacity: 0;
      pointer-events: none;
      transform: translateY(10px) scale(0.98);
    }}
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
      position: absolute;
      left: 0;
      top: 88px;
      width: min(196px, 18vw);
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
      width: min(72vw, 820px);
      aspect-ratio: 1;
      display: grid;
      place-items: center;
      transform: translateY(14px);
    }}
    body.modal-open .core-stage {{
      position: fixed;
      top: 18px;
      left: 18px;
      width: min(72vw, 820px);
      transform: scale(0.1);
      transform-origin: top left;
      z-index: 24;
      pointer-events: none;
      opacity: 0.96;
    }}
    .core-backdrop,
    .holo-core-shell,
    .core-label {{
      position: absolute;
      inset: 0;
    }}
    .core-backdrop {{
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
      position: absolute;
      inset: 0;
      pointer-events: none;
      background:
        radial-gradient(circle at center, rgba(103, 226, 255, 0.06) 0%, rgba(103, 226, 255, 0.02) 22%, rgba(4, 8, 14, 0) 56%),
        radial-gradient(circle at center, rgba(4, 8, 14, 0) 42%, rgba(4, 8, 14, 0.22) 74%, rgba(4, 8, 14, 0.44) 100%);
      opacity: 0.96;
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
      z-index: 3;
      display: grid;
      place-content: center;
      gap: 10px;
      inset: 36% 31% 34% 31%;
      pointer-events: none;
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
      position: absolute;
      left: 0;
      bottom: 148px;
      width: min(360px, 32vw);
      display: grid;
      gap: 12px;
      transition: opacity 180ms ease, transform 180ms ease, width 180ms ease;
    }}
    body[data-transcript-empty="true"] .transcript-rail {{
      width: min(280px, 24vw);
      opacity: 0.44;
      transform: translateY(6px);
    }}
    .transcript-bubble {{
      padding: 16px 18px;
      border: 1px solid var(--line-soft);
      background: rgba(6, 16, 28, 0.55);
      color: var(--ink);
      backdrop-filter: blur(18px);
      clip-path: polygon(0 0, calc(100% - 16px) 0, 100% 16px, 100% 100%, 0 100%);
      transition: opacity 180ms ease, border-color 180ms ease, background 180ms ease;
    }}
    body[data-transcript-empty="true"] .transcript-bubble {{
      border-color: rgba(111, 229, 255, 0.08);
      background: rgba(6, 16, 28, 0.34);
      opacity: 0.78;
    }}
    .transcript-bubble .speaker {{
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--cyan);
      margin-bottom: 10px;
    }}
    .transcript-bubble.user .speaker {{
      color: var(--amber);
    }}
    .packet-strip {{
      position: fixed;
      right: 22px;
      bottom: 170px;
      z-index: 6;
      display: flex;
      flex-direction: column;
      gap: 10px;
      align-items: end;
      transition: opacity 180ms ease, transform 180ms ease;
    }}
    .packet-strip.collapsed {{
      display: none;
      opacity: 0;
      pointer-events: none;
      transform: translateY(10px) scale(0.98);
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
      border-radius: 999px;
      border: 1px solid rgba(111, 229, 255, 0.36);
      background: linear-gradient(135deg, rgba(111, 229, 255, 0.16), rgba(76, 160, 255, 0.18));
      color: var(--cyan);
      box-shadow:
        0 0 24px rgba(111, 229, 255, 0.18),
        inset 0 0 18px rgba(111, 229, 255, 0.08);
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
    .packet-button.active {{
      color: var(--cyan);
      border-color: rgba(111, 229, 255, 0.62);
      box-shadow: 0 0 18px rgba(111, 229, 255, 0.16);
    }}
    .dock {{
      align-items: end;
      grid-template-columns: 1fr;
    }}
    .input-cluster {{
      display: grid;
      grid-template-columns: auto 1fr auto auto;
      gap: 12px;
      align-items: center;
      width: min(860px, 100%);
      justify-self: center;
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
    }}
    .dock-button.primary {{
      background: linear-gradient(135deg, rgba(111, 229, 255, 0.18), rgba(76, 160, 255, 0.18));
      color: var(--cyan);
      box-shadow: 0 0 22px rgba(111, 229, 255, 0.16);
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
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(7, 16, 27, 0.78);
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
    .modal-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 18px;
    }}
    .modal-head h2 {{
      margin: 0;
      font-size: 24px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #e8f5ff;
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
    .packet-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }}
    .packet-block {{
      border: 1px solid var(--line-soft);
      padding: 16px 18px;
      background: rgba(10, 22, 36, 0.56);
      min-height: 108px;
    }}
    .packet-block h3 {{
      margin: 0 0 10px;
      font-size: 13px;
      letter-spacing: 0.18em;
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
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid var(--line-soft);
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      background: rgba(8, 18, 32, 0.82);
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
      border: 1px solid var(--line-soft);
      background: rgba(5, 12, 22, 0.92);
      min-height: 72vh;
      overflow: hidden;
    }}
    .workspace-frame iframe {{
      width: 100%;
      height: 72vh;
      border: 0;
      background: transparent;
      display: block;
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
      grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
      gap: 18px;
    }}
    .model-forge-stage {{
      min-height: 420px;
      border-radius: 22px;
      border: 1px solid rgba(111, 229, 255, 0.18);
      background:
        linear-gradient(180deg, rgba(11, 22, 38, 0.92), rgba(5, 11, 18, 0.96)),
        radial-gradient(circle at top, rgba(111, 229, 255, 0.16), transparent 48%);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02), 0 24px 60px rgba(0, 0, 0, 0.35);
      overflow: hidden;
      position: relative;
    }}
    .model-forge-viewer {{
      width: 100%;
      height: 100%;
      min-height: 420px;
    }}
    .model-forge-empty {{
      position: absolute;
      inset: 0;
      display: grid;
      place-items: center;
      text-align: center;
      color: var(--muted);
      padding: 28px;
      pointer-events: none;
    }}
    .model-forge-panel {{
      display: grid;
      gap: 14px;
      align-content: start;
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
      padding: 14px 16px;
      border-radius: 18px;
      border: 1px solid rgba(111, 229, 255, 0.14);
      background: rgba(8, 17, 28, 0.88);
    }}
    .model-forge-meta .metric {{
      display: grid;
      gap: 4px;
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
    @media (max-width: 1080px) {{
      .topbar {{
        grid-template-columns: 1fr;
        justify-items: center;
      }}
      .meta-rail,
      .wordmark {{
        justify-self: center;
      }}
      .transcript-rail,
      .packet-strip,
      .signal-rail,
      .signal-rail-toggle {{
        position: static;
        width: 100%;
        align-items: stretch;
      }}
      .brain-graph-panel {{
        position: static;
        width: 100%;
      }}
      .brains-layout {{
        grid-template-columns: 1fr;
      }}
      .viewport {{
        gap: 18px;
        grid-auto-rows: max-content;
      }}
      .core-stage {{
        width: min(92vw, 720px);
      }}
      .input-cluster {{
        grid-template-columns: 1fr;
      }}
      .packet-grid {{
        grid-template-columns: 1fr;
      }}
      .vision-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body data-voice-state="idle">
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
        <span class="meta-chip" id="meta-time">--:--</span>
        <span class="meta-chip hidden" id="runtime-freshness">Live</span>
        <button class="meta-icon-button" id="mode-toggle" type="button" title="Household mode">⌂</button>
        <button class="ghost-toggle" id="open-settings" type="button">Settings</button>
      </div>
    </header>
    <div class="mode-panel" id="mode-panel" aria-hidden="true">
      <div class="mode-panel-head">
        <div class="mode-panel-title">Household Mode</div>
        <button class="close-button" id="mode-panel-close" type="button" aria-label="Close">×</button>
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
      <button class="signal-rail-toggle" id="signal-rail-toggle" type="button">Status</button>
      <div class="signal-rail" id="signal-rail"></div>
      <div class="brain-graph-panel">
        <div class="brain-graph-head">
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
      </div>

      <div class="transcript-rail">
        <div class="transcript-bubble user">
          <div class="speaker">You</div>
          <div id="last-user-text">Awaiting command.</div>
        </div>
        <div class="transcript-bubble">
          <div class="speaker">JARVIS</div>
          <div id="last-jarvis-text">Standing by.</div>
        </div>
      </div>

      <div class="core-stage">
        <div class="core-backdrop"></div>
        <div class="holo-core-shell" id="holo-core-shell">
          <div class="holo-core-fallback" aria-hidden="true">
            <div class="holo-core-fallback-dust"></div>
            <div class="holo-core-fallback-ring tight" style="--ring-size: 52; --ring-speed: 26s; --ring-opacity: 0.98;">
              <span class="holo-core-fallback-dot" style="--dot-angle: 18; --dot-radius: 26;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 76; --dot-radius: 26;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 108; --dot-radius: 26;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 162; --dot-radius: 26;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 214; --dot-radius: 26;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 258; --dot-radius: 26;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 302; --dot-radius: 26;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 336; --dot-radius: 26;"></span>
            </div>
            <div class="holo-core-fallback-ring tight reverse" style="--ring-size: 68; --ring-speed: 34s; --ring-opacity: 0.88;">
              <span class="holo-core-fallback-dot" style="--dot-angle: 24; --dot-radius: 34;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 64; --dot-radius: 34;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 112; --dot-radius: 34;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 160; --dot-radius: 34;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 206; --dot-radius: 34;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 248; --dot-radius: 34;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 296; --dot-radius: 34;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 332; --dot-radius: 34;"></span>
            </div>
            <div class="holo-core-fallback-ring" style="--ring-size: 84; --ring-speed: 44s; --ring-opacity: 0.74;">
              <span class="holo-core-fallback-dot" style="--dot-angle: 18; --dot-radius: 42;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 66; --dot-radius: 42;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 114; --dot-radius: 42;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 162; --dot-radius: 42;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 210; --dot-radius: 42;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 258; --dot-radius: 42;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 306; --dot-radius: 42;"></span>
              <span class="holo-core-fallback-dot" style="--dot-angle: 342; --dot-radius: 42;"></span>
            </div>
            <div class="holo-core-fallback-core"></div>
          </div>
          <canvas class="holo-core-canvas" id="holo-core-canvas" aria-hidden="true"></canvas>
          <div class="holo-core-overlay"></div>
          <div class="beam-column"></div>
          <div class="emitter-disc"></div>
        </div>
        <div class="core-label">
          <div class="name">JARVIS</div>
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
      </div>

      <button class="packet-strip-toggle" id="packet-strip-toggle" type="button">Packets</button>
      <div class="packet-strip collapsed" id="packet-strip"></div>
    </main>

    <footer class="dock">
      <div class="input-cluster">
        <button class="dock-icon-button" id="open-context-controls" type="button" title="Actor and room controls">≡</button>
        <input id="command-input" class="dock-input" placeholder="Tap or speak a command. Example: Jarvis, show me the calm version of tonight." />
        <button class="dock-button" id="voice-command" title="Speak to JARVIS">Talk</button>
        <button class="dock-button primary" id="send-command">Send</button>
      </div>
    </footer>
  </div>

  <div class="context-panel" id="context-panel" aria-hidden="true">
    <div class="context-panel-head">
      <div class="context-panel-title">Command Context</div>
      <button class="close-button" id="context-panel-close" type="button" aria-label="Close">×</button>
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
      <div class="modal-head">
        <h2 id="modal-title">Packet</h2>
        <button class="close-button" id="close-modal" aria-label="Close">×</button>
      </div>
      <div class="packet-body" id="modal-body"></div>
    </div>
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

    const packetPresets = {packet_presets};
    const availableModes = {available_modes};
    const state = {{
      dashboard: null,
      lastBriefing: "",
      packet: "",
      packetHydrationToken: 0,
      packetHydrationPending: "",
      speechEnabled: true,
      speakingTimer: null,
      energyTimer: null,
      currentAudio: null,
      currentAudioUrl: "",
      recognizer: null,
      recognizing: false,
      alwaysOnMicEnabled: true,
      wakeWord: "hey jarvis",
      followUpWindowMs: 60000,
      followUpUntil: 0,
      recognitionRestartTimer: null,
      energyCurrent: 0.35,
      energyTarget: 0.35,
      catalystPage: "home",
      packetStripExpanded: false,
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
      shellDeviceId: "",
      firstLight: null,
      sessionActorOverride: "",
      lastAssistantSurfaceKey: "",
      browserAlertsEnabled: false,
      browserAlertsPermission: "default",
      autonomyTickTimer: null,
      autonomyBackgroundTimer: null,
    }};

    const VISION_CALIBRATION_KEY = "jarvis-vision-calibration-v1";
    const SHELL_DEVICE_ID_KEY = "jarvis-shell-device-id-v1";
    const SESSION_ACTOR_OVERRIDE_KEY = "jarvis-session-actor-override-v1";
    const ASSISTANT_SURFACE_KEY = "jarvis-assistant-surface-last-v1";
    const BROWSER_ALERTS_ENABLED_KEY = "jarvis-browser-alerts-enabled-v1";

    function escapeHtml(value) {{
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }}

    function browserAlertsSupported() {{
      return typeof window !== "undefined" && "Notification" in window;
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
      const retryable =
        typeof url === "string" &&
        (
          url.includes("/api/assistant-core/notifications/") ||
          url.includes("/api/assistant-core/background-run")
        );
      const attempts = retryable ? 3 : 1;
      let lastError = null;
      for (let attempt = 1; attempt <= attempts; attempt += 1) {{
        try {{
          const response = await fetch(url, options);
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
          return payload;
        }} catch (error) {{
          lastError = error;
          if (attempt >= attempts) {{
            throw error;
          }}
          const delay = 200 * attempt;
          await new Promise((resolve) => window.setTimeout(resolve, delay));
        }}
      }}
      throw lastError || new Error(`${{method}} request failed.`);
    }}

    function freshnessInfo(payload) {{
      return payload?.freshness || {{}};
    }}

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
        today_board: next.today_board || previous.today_board || null,
        cadence_review: next.cadence_review || previous.cadence_review || null,
        open_loops: next.open_loops || previous.open_loops || null,
        cognitive: next.cognitive || previous.cognitive || null,
        assistant_notifications: next.assistant_notifications || previous.assistant_notifications || null,
      }};
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
      scene.background = new THREE.Color(0x08111b);
      const camera = new THREE.PerspectiveCamera(44, 1, 0.1, 2000);
      const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      mount.innerHTML = "";
      mount.appendChild(renderer.domElement);

      const ambient = new THREE.AmbientLight(0xc7f7ff, 1.6);
      const key = new THREE.DirectionalLight(0x8de8ff, 1.8);
      key.position.set(140, 180, 120);
      const fill = new THREE.DirectionalLight(0x5f8dff, 0.7);
      fill.position.set(-120, 90, -60);
      scene.add(ambient, key, fill);

      const grid = new THREE.GridHelper(220, 22, 0x4ca0ff, 0x163245);
      grid.position.y = -0.01;
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
      const details = document.getElementById("model-forge-details");
      const script = document.getElementById("model-forge-script");
      const status = document.getElementById("model-forge-viewer-status");
      const placeholder = document.getElementById("model-forge-empty");
      if (!packageId || !details || !script || !status) return;
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
        <div class="inline-actions" style="margin-top:10px;flex-wrap:wrap;">
          <a href="/api/model-forge/package/${{encodeURIComponent(packageId)}}/download/stl">Download STL</a>
          <a href="/api/model-forge/package/${{encodeURIComponent(packageId)}}/download/step">Download STEP</a>
          <a href="/api/model-forge/package/${{encodeURIComponent(packageId)}}/download/3mf">Download 3MF</a>
          <a href="/api/model-forge/package/${{encodeURIComponent(packageId)}}/download/slicer-pack">Download Slicer Pack</a>
          <button type="button" id="model-forge-open-slicer" data-package-id="${{escapeHtml(packageId)}}">Open In Slicer</button>
        </div>
      `;
      script.textContent = pkg.openscad_stub || "No OpenSCAD source recorded.";
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
      if (!select) return;

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
      populateModelForgeControls().catch((error) => {{
        if (output) output.textContent = error.message;
      }});
      family?.addEventListener("change", refreshModelForgeFamilyGuidance);
      printer?.addEventListener("change", refreshModelForgeProfileOptions);
      ["model-forge-part", "model-forge-dimensions", "model-forge-constraints"].forEach((id) => {{
        const field = document.getElementById(id);
        field?.addEventListener("input", () => {{
          field.dataset.autofill = "false";
        }});
      }});
      select.addEventListener("change", loadSelected);
      refresh?.addEventListener("click", loadSelected);
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
        if (status) status.textContent = "Measured the selected span using the saved ruler calibration.";
        renderVisionCalibrationSummary("Measurement ready.");
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
      return /\\bhey\\s+jarvis\\b[\\s,.:;-]*/i;
    }}

    function conversationWindowActive() {{
      return Date.now() < state.followUpUntil;
    }}

    function extendConversationWindow() {{
      state.followUpUntil = Date.now() + state.followUpWindowMs;
    }}

    function clearRecognitionRestartTimer() {{
      if (state.recognitionRestartTimer) {{
        clearTimeout(state.recognitionRestartTimer);
        state.recognitionRestartTimer = null;
      }}
    }}

    function refreshMicButton() {{
      if (state.recognizing) {{
        setTalkButton(true, conversationWindowActive() ? "Listening..." : "Wake Listening");
        return;
      }}
      if (state.alwaysOnMicEnabled) {{
        setTalkButton(true, "Mic On");
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
        startVoiceCommand({{ automatic: true }}).catch((error) => {{
          console.debug("Always-on microphone restart failed", error);
          refreshMicButton();
        }});
      }}, delay);
      refreshMicButton();
    }}

    function disableAlwaysOnMic(detail = "Microphone is off.") {{
      state.alwaysOnMicEnabled = false;
      state.followUpUntil = 0;
      clearRecognitionRestartTimer();
      stopRecognition();
      setVoiceState("idle", detail);
      refreshMicButton();
    }}

    function enableAlwaysOnMic(detail = 'Standing by for "Hey Jarvis".') {{
      state.alwaysOnMicEnabled = true;
      setVoiceState("idle", detail);
      queueAlwaysOnListening(60);
      refreshMicButton();
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
        setVoiceState("idle", 'Standing by for "Hey Jarvis".');
        if (ambientSubtitle) {{
          ambientSubtitle.textContent = 'Standing by for "Hey Jarvis".';
        }}
        queueAlwaysOnListening();
        return;
      }}

      const request = heardWakeWord ? normalized.replace(wakePattern, "").trim() : normalized;
      extendConversationWindow();

      if (!request) {{
        setVoiceState("listening", "Wake word heard. Go ahead.");
        if (ambientSubtitle) {{
          ambientSubtitle.textContent = "Wake word heard. Go ahead.";
        }}
        queueAlwaysOnListening();
        return;
      }}

      document.getElementById("last-user-text").textContent = request;
      document.getElementById("command-input").value = request;
      if (ambientSubtitle) ambientSubtitle.textContent = request;
      syncTranscriptRail();
      await sendCommand(true);
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

    function fillPacketStrip() {{
      const target = document.getElementById("packet-strip");
      const toggle = document.getElementById("packet-strip-toggle");
      if (!target || !toggle) {{
        return;
      }}
      target.classList.toggle("collapsed", !state.packetStripExpanded);
      toggle.classList.toggle("hidden", state.packetStripExpanded);
      target.innerHTML = `
        <button class="packet-button" data-packet-collapse="true">Hide</button>
      ` + packetPresets.map((packet) => `
        <button class="packet-button ${{state.packet === packet.id ? "active" : ""}}" data-packet="${{packet.id}}">${{escapeHtml(packet.label)}}</button>
      `).join("");
      const collapse = target.querySelector("[data-packet-collapse]");
      if (collapse) {{
        collapse.addEventListener("click", () => togglePacketStrip(false));
      }}
      target.querySelectorAll("[data-packet]").forEach((button) => {{
        button.addEventListener("click", () => openPacket(button.dataset.packet));
      }});
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
      document.getElementById("mode-panel-current").textContent =
        `Current mode: ${{(current.mode || "ambient-associate").replaceAll("-", " ")}}`;
      document.getElementById("mode-select").value = current.mode || availableModes[0] || "ambient-associate";
      document.getElementById("mode-panel-status").textContent =
        current.reason ? `Current reason: ${{current.reason}}` : "Choose a new mode and apply it.";
      panel.classList.add("open");
      panel.setAttribute("aria-hidden", "false");
    }}

    function closeModePanel() {{
      const panel = document.getElementById("mode-panel");
      if (!panel) {{
        return;
      }}
      panel.classList.remove("open");
      panel.setAttribute("aria-hidden", "true");
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
      panel.classList.add("open");
      panel.setAttribute("aria-hidden", "false");
      syncContextPanelCopy();
    }}

    function closeContextPanel() {{
      const panel = document.getElementById("context-panel");
      if (!panel) {{
        return;
      }}
      panel.classList.remove("open");
      panel.setAttribute("aria-hidden", "true");
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
      root.add(core);

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
      [
        [1.34, 0x6fe5ff, 0.22, 0.0018, 0.0, 0.0],
        [1.72, 0x56b6ff, -0.18, -0.0022, Math.PI / 3, Math.PI / 7],
        [2.05, 0x9cf1ff, 0.42, 0.0012, Math.PI / 2.4, -Math.PI / 5],
      ].forEach(([radius, color, tilt, speed, rx, rz]) => {{
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
      [
        [1.54, 0xe8, 110, 0x86f2ff],
        [1.92, 0xc4, 82, 0x5fb8ff],
        [2.2, 0xa8, 96, 0x87deff],
      ].forEach(([radius, startDeg, spanDeg, color]) => {{
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
      root.add(particles);

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

    function syncTranscriptRail() {{
      const userText = (document.getElementById("last-user-text")?.textContent || "").trim();
      const jarvisText = (document.getElementById("last-jarvis-text")?.textContent || "").trim();
      const emptyUser = userText === "" || userText === "Awaiting command.";
      const emptyJarvis = jarvisText === "" || jarvisText === "Standing by.";
      document.body.dataset.transcriptEmpty = emptyUser && emptyJarvis ? "true" : "false";
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
      refreshVoiceSettings()
        .then(() => openPacket("settings"))
        .catch((error) => {{
          document.getElementById("last-jarvis-text").textContent = error.message;
          setVoiceState("idle", "Settings are unavailable right now.");
        }});
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
      const platform = navigator.userAgentData?.platform || navigator.platform || "Unknown platform";
      const label = `${{platform}} browser`;
      const fingerprint = [navigator.userAgent || "", navigator.language || "", String(window.screen?.width || 0), String(window.screen?.height || 0)].join("|");
      return {{
        device_id: deviceId,
        label,
        device_type: "browser",
        room: document.getElementById("room")?.value || "office",
        user_agent: navigator.userAgent || "",
        fingerprint,
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
      return data;
    }}

    function preferredActorLabel() {{
      return (
        state.sessionIdentity?.resolved_actor_label ||
        document.getElementById("actor")?.value ||
        "Chris"
      );
    }}

    function wireCatalystWorkspace() {{
      const frame = document.getElementById("catalyst-workspace-frame");
      const tabs = Array.from(document.querySelectorAll("[data-catalyst-page]"));
      if (!frame || tabs.length === 0) {{
        return;
      }}

      const setPage = (page) => {{
        state.catalystPage = page || "home";
        frame.setAttribute("src", `/catalyst/view/${{state.catalystPage}}`);
        tabs.forEach((tab) => {{
          tab.classList.toggle("active", tab.dataset.catalystPage === state.catalystPage);
        }});
      }};

      tabs.forEach((tab) => {{
        tab.addEventListener("click", () => setPage(tab.dataset.catalystPage));
      }});

      setPage(state.catalystPage || "home");
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
        state.settingsMessage = `Saved. Current source: ${{data.settings.selected_provider_label}}.`;
        openPacket("settings");
        document.getElementById("last-jarvis-text").textContent = "Voice settings updated.";
        syncTranscriptRail();
        if (preview) {{
          const previewText = document.getElementById("settings-preview-text")?.value?.trim() || "Good evening, sir. Voice calibration complete.";
          await speakText(previewText);
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

    function openPacket(packetId) {{
      if (packetId !== "vision") {{
        stopVisionPreview();
      }}
      state.packet = packetId;
      state.packetStripExpanded = true;
      document.body.classList.add("modal-open");
      fillPacketStrip();
      const modal = document.getElementById("modal-layer");
      const title = document.getElementById("modal-title");
      const body = document.getElementById("modal-body");
      const data = state.dashboard || {{}};
      const needsDashboardHydration =
        !state.dashboard ||
        (packetId === "today" && !data.today_board) ||
        (packetId === "review" && !data.cadence_review) ||
        (packetId === "tasks" && !data.open_loops);
      let heading = "Packet";
      let content = "";

      if (needsDashboardHydration) {{
        if (state.packetHydrationPending === packetId) {{
          setModalVisibility(true);
          return;
        }}
        title.textContent =
          packetId === "today"
            ? "Today Board"
            : packetId === "review"
              ? "Cadence Review"
              : packetId === "tasks"
                ? "Assistant Core"
                : "Packet";
        body.innerHTML = `<div class="packet-grid"><div class="metric">${{
          packetId === "today"
            ? "Loading Today Board..."
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
        const hydrate = packetId === "today"
          ? loadJSON(`/api/today-board?actor=${{encodeURIComponent(actor)}}`).then((todayBoard) => {{
              mergeDashboardState({{
                today_board: todayBoard,
                cognitive: todayBoard?.cognition || state.dashboard?.cognitive || null,
                assistant_notifications: todayBoard?.assistant_notifications || state.dashboard?.assistant_notifications || null,
              }});
            }})
          : packetId === "review"
            ? loadJSON(`/api/cadence-review?actor=${{encodeURIComponent(actor)}}`).then((reviewPacket) => {{
                mergeDashboardState({{
                  cadence_review: reviewPacket,
                }});
              }})
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

      if (packetId === "briefing") {{
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
                packetBlock("Home", `<p>${{escapeHtml(data.cards?.home?.summary || "")}}</p>${{renderList((data.cards?.home?.details || []).map((item) => `<div>${{escapeHtml(item)}}</div>`))}}`)
              }}
              ${{
                packetBlock("Mission", `<p>${{escapeHtml(data.cards?.mission?.summary || "")}}</p>${{renderList((data.cards?.mission?.details || []).map((item) => `<div>${{escapeHtml(item)}}</div>`))}}`)
              }}
              ${{
                packetBlock("Briefing", `<p>${{escapeHtml(state.lastBriefing || "Use the Brief button or ask JARVIS for a briefing.")}}</p>`)
              }}
            </div>`;
        }}
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
                  <div class="metric"><strong>Growth pressure</strong> ${{escapeHtml(board.cognition?.growth_state?.summary?.pressure || "quiet")}} · signals ${{escapeHtml(String(board.cognition?.growth_state?.summary?.tracked_signal_count || 0))}}</div>
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
                "Growth Lanes",
                `
                  <div class="metric"><strong>Overall</strong> ${{escapeHtml(board.growth?.summary?.pressure || board.cognition?.growth_state?.summary?.pressure || "quiet")}}</div>
                  <div class="metric"><strong>Tracked signals</strong> ${{escapeHtml(String(board.growth?.summary?.tracked_signal_count || board.cognition?.growth_state?.summary?.tracked_signal_count || 0))}}</div>
                  <div class="metric"><strong>Domains</strong> ${{escapeHtml(String(board.growth?.summary?.tracked_domain_count || board.cognition?.growth_state?.summary?.tracked_domain_count || 0))}} · live adapters ${{escapeHtml(String(board.growth?.summary?.live_adapter_count || board.cognition?.growth_state?.summary?.live_adapter_count || 0))}}</div>
                  <div class="metric"><strong>Active review</strong> ${{escapeHtml(board.growth_guidance?.label || "Growth Watch")}} · ${{escapeHtml(board.growth_guidance?.pressure || "quiet")}}</div>
                  <div class="metric"><strong>Review note</strong> ${{escapeHtml(board.growth_guidance?.summary || "No strong growth review is staged right now.")}}</div>
                  ${{renderList(((board.growth?.lanes || board.cognition?.growth_state?.lanes || [])).map((item) => `
                    <div>
                      <strong>${{escapeHtml(item.label || "Growth lane")}}</strong> · ${{escapeHtml(item.pressure || "quiet")}} · ${{escapeHtml(item.confidence || "low")}}
                      <br>${{escapeHtml(item.summary || "")}}
                      <br><span class="muted">${{escapeHtml(item.latest || "")}}</span>
                    </div>
                  `))}}
                  ${{renderList(((board.growth?.adapters || board.cognition?.growth_state?.adapters || [])).slice(0, 4).map((item) => `
                    <div>
                      <strong>${{escapeHtml(item.label || "Adapter")}}</strong> · ${{escapeHtml(item.status || "planned")}} · ${{escapeHtml(item.live ? "live" : "inferred")}}
                      <br><span class="muted">${{escapeHtml(item.note || "")}}</span>
                    </div>
                  `))}}
                  ${{renderList((board.growth?.top_signals || board.cognition?.growth_state?.top_signals || []).slice(0, 4).map((item) => `<div><strong>Signal</strong><br>${{escapeHtml(item)}}</div>`))}}
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
              (review.sections || []).map((section) => packetBlock(
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
                </div>
                <div class="settings-note" id="connected-devices-status">Loading connected devices…</div>
              `)
            }}
            ${{
              packetBlock("Summary", `<div class="stack" id="connected-devices-summary"><div class="metric">Loading device summary…</div></div>`)
            }}
            ${{
              packetBlock("Registry", `<div class="stack" id="connected-devices-list"><div class="metric">Loading device registry…</div></div>`)
            }}
          </div>`;
      }} else if (packetId === "home") {{
        heading = "House Packet";
        content = `
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
          </div>`;
      }} else if (packetId === "family") {{
        heading = "Family Packet";
        content = `
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
            ${{
              packetBlock("Tonight", `
                <div class="stack">
                  <div class="metric"><strong>Meal</strong> ${{escapeHtml(data.meal_plans?.[0]?.meal_suggestion || "Not staged")}}</div>
                  <div class="metric"><strong>Vehicle</strong> ${{escapeHtml(data.vehicle_plans?.[0]?.vehicle || "Not assigned")}}</div>
                  <div class="metric"><strong>Weather</strong> ${{escapeHtml(data.weather_plans?.[0]?.risk_level || data.weather || "--")}}</div>
                </div>`)
            }}
          </div>`;
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
                <div class="model-forge-viewer" id="model-forge-viewer"></div>
                <div class="model-forge-empty" id="model-forge-empty">Choose a generated model package to inspect its STL here.</div>
              </div>
              <div class="model-forge-panel">
                <div class="model-forge-meta">
                  <div class="metric"><strong>Create Package</strong></div>
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
                <label>
                  Model package
                  <select id="model-forge-package">
                    ${{packages.map((item, index) => `<option value="${{escapeHtml(item.package_id)}}"
                      ${{index === 0 ? "selected" : ""}}>${{escapeHtml(item.part_name)}} · ${{escapeHtml(item.export_status || "cad-package")}}</option>`).join("")}}
                  </select>
                </label>
                <div class="model-forge-actions">
                  <button id="model-forge-refresh" type="button">Load Model</button>
                </div>
                <div class="model-forge-meta" id="model-forge-details">
                  <div class="metric">Select a package to see its export details.</div>
                </div>
                <div class="vision-status" id="model-forge-viewer-status">${{packages.length ? "Ready to load the latest generated package." : "No model forge packages yet. Generate one from the Workshop packet first."}}</div>
                <div class="model-forge-meta">
                  <div class="metric"><strong>OpenSCAD Source</strong></div>
                  <pre class="model-forge-script" id="model-forge-script">No source loaded yet.</pre>
                </div>
              </div>
            </div>
          </div>`;
      }} else if (packetId === "chronicle") {{
        heading = "Chronicle Packet";
        content = `
          <div class="packet-grid">
            ${{
              packetBlock("Themes", renderList((data.chronicle_theme_summary?.themes || []).map((item) => `<div><strong>${{escapeHtml(item.theme)}}</strong> · ${{escapeHtml(String(item.count))}}</div>`)))
            }}
            ${{
              packetBlock("Timeline", renderList((data.chronicle_timeline || []).map((item) => `<div><strong>${{escapeHtml(item.theme)}}</strong><br>${{escapeHtml(item.note)}}</div>`)))
            }}
            ${{
              packetBlock("Current Reflection", `<p>${{escapeHtml((data.chronicle_timeline || [])[0]?.reflection || "No Chronicle reflection loaded yet.")}}</p>`)
            }}
            ${{
              packetBlock("Formation Note", `<p>${{escapeHtml(data.cards?.mission?.summary || "No formation note available.")}}</p>`)
            }}
          </div>`;
      }} else if (packetId === "workshop") {{
        heading = "Workshop Packet";
        content = `
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
      }} else if (packetId === "catalyst") {{
        heading = "Catalyst Workspace";
        const catalyst = data.catalyst_overview || {{}};
        const googleWorkspace = catalyst.google_workspace || data.google_workspace || {{}};
        const googleAccounts = googleWorkspace.accounts || [];
        const tabs = [
          ["home", "Home"],
          ["calendar", "Calendar"],
          ["meetings", "Meetings"],
          ["projects", "Projects"],
          ["tasks", "Tasks"],
          ["email", "Email"],
          ["contacts", "Contacts"],
          ["reports", "Reports"],
          ["settings", "Settings"],
        ];
        content = `
          <div class="workspace-shell">
            <div class="workspace-summary">
              <span class="tag">Accounts ${{escapeHtml(String(googleWorkspace.count ?? 0))}}</span>
              <span class="tag">Connected ${{escapeHtml(String(googleAccounts.filter((item) => item.status?.connected).length))}}</span>
              <span class="tag">Signals ${{escapeHtml(String(catalyst.counts?.signals ?? 0))}}</span>
              <span class="tag">Triages ${{escapeHtml(String(catalyst.counts?.email_triage ?? 0))}}</span>
              <span class="tag">Meetings ${{escapeHtml(String(catalyst.counts?.meeting_extractions ?? 0))}}</span>
              <span class="tag">Projects ${{escapeHtml(String(catalyst.counts?.project_briefs ?? 0))}}</span>
            </div>
            <div class="workspace-tabs">
              ${{tabs.map(([page, label]) => `<button type="button" class="workspace-tab" data-catalyst-page="${{page}}">${{label}}</button>`).join("")}}
            </div>
            <div class="workspace-frame">
              <iframe id="catalyst-workspace-frame" title="Catalyst Workspace" src="/catalyst/view/home"></iframe>
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
                <div class="metric"><strong>Staged</strong> ${{escapeHtml(String(summary.staged || 0))}}</div>
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
              packetBlock("Voice Output", `
                <div class="settings-grid">
                  <label>
                    Preferred voice source
                    <select id="settings-tts-provider">
                      ${{renderSelectOptions(options.providers || [], settings.tts_provider || "auto")}}
                    </select>
                  </label>
                  <label>
                    ElevenLabs voice
                    <select id="settings-elevenlabs-voice">
                      ${{renderSelectOptions(options.elevenlabs || [], settings.elevenlabs_voice || "", "No ElevenLabs voices found")}}
                    </select>
                  </label>
                  <label>
                    Piper voice
                    <select id="settings-piper-model">
                      ${{renderSelectOptions(options.piper || [], settings.piper_model_path || "", "No Piper voices found")}}
                    </select>
                  </label>
                  <label>
                    Piper speaker
                    <input id="settings-piper-speaker" value="${{escapeHtml(settings.piper_speaker || "")}}" placeholder="Default speaker">
                  </label>
                  <label>
                    Preview phrase
                    <input id="settings-preview-text" value="Good evening, sir. Voice calibration complete.">
                  </label>
                  <div class="inline-actions">
                    <button id="save-voice-settings" type="button">Save</button>
                    <button id="preview-voice-settings" class="ghost-toggle" type="button">Save + Preview</button>
                  </div>
                  <div class="settings-note" id="voice-settings-status">${{escapeHtml(state.settingsMessage || "Pick a source, save it, and preview the result here.")}}</div>
                </div>`)
            }}
            ${{
              packetBlock("Current Selection", `
                <div class="stack">
                  <div class="metric"><strong>Source</strong> ${{escapeHtml(settings.selected_provider_label || "--")}}</div>
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
                    JARVIS should live as infrastructure. Track the primary host, LAN name, and whether boot-time launch and watchdog behavior are in place.
                  </div>
                  <div class="stack">
                    <div class="metric"><strong>Host</strong> ${{escapeHtml(identityService.host_label || "Primary JARVIS host")}}</div>
                    <div class="metric"><strong>LAN URL</strong> ${{escapeHtml(identityService.lan_url || window.location.origin)}}</div>
                    <div class="metric"><strong>Hostname</strong> ${{escapeHtml(identityService.hostname || "jarvis.local")}}</div>
                    <div class="metric"><strong>Launch on boot</strong> ${{identityService.launch_on_boot ? "enabled" : "not yet"}}</div>
                  </div>
                  <div class="stack" id="runtime-service-status">
                    <div class="metric">Runtime service status is loading…</div>
                  </div>
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
                  <div class="inline-actions">
                    <button id="save-identity-service" type="button">Save Service Plan</button>
                  </div>
                  <div class="settings-note" id="identity-service-status">Track the host plan here, then use <code>ops/install_launchd_services.sh</code> to install it for real.</div>
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
                    Each household member can have separate mail and calendar identities. Chris and Rebekah do not need to share a provider or a login.
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
                              <button class="account-connect" type="button" data-account-id="${{escapeHtml(account.account_id)}}">${{account.provider === "google" ? "Connect" : "Provider Setup Pending"}}</button>
                              <button class="ghost-toggle account-disconnect" type="button" data-account-id="${{escapeHtml(account.account_id)}}"${{account.provider === "google" ? "" : " disabled"}}>Disconnect</button>
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
                  <div class="settings-note" id="account-settings-status">Create one account per person per provider.</div>
                </div>`)
            }}
          </div>`;
      }}

      title.textContent = heading;
      body.innerHTML = content;
      modal.querySelector(".modal").classList.toggle("workspace-modal", packetId === "catalyst");
      modal.querySelector(".modal").classList.toggle("brains-modal", packetId === "brains");
      if (packetId === "settings") {{
        wireVoiceSettingsForm();
        wirePageReviewSettingsForm();
        wireLocationSettingsForm();
        wireGoogleSettingsForm();
        wireAccountSettingsForm();
        wireIdentitySettingsForm();
      }} else if (packetId === "connected-devices") {{
        wireConnectedDevicesAdmin();
      }} else if (packetId === "today") {{
        wireTodayBoardActions();
        wireAssistantInboxActions("today");
      }} else if (packetId === "review") {{
        wireReviewActions();
        wireAssistantInboxActions("review");
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
      syncDesignReviewPanel();
    }}

    function closePacket() {{
      stopVisionPreview();
      destroyModelForgeScene();
      state.packetHydrationToken += 1;
      state.packetHydrationPending = "";
      state.packet = "";
      document.body.classList.remove("modal-open");
      fillPacketStrip();
      const modal = document.getElementById("modal-layer");
      document.getElementById("modal-title").textContent = "Packet";
      document.getElementById("modal-body").innerHTML = "";
      setModalVisibility(false);
      modal.querySelector(".modal").classList.remove("workspace-modal");
      modal.querySelector(".modal").classList.remove("brains-modal");
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
      const list = document.getElementById("connected-devices-list");
      const status = document.getElementById("connected-devices-status");
      const refreshButton = document.getElementById("connected-devices-refresh");
      const bindCurrentButton = document.getElementById("connected-devices-bind-current");

      if (!summary || !list || !status) {{
        return;
      }}

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
        return `
          <div class="metric" data-device-card="${{escapeHtml(device.device_id || "")}}">
            <strong>${{escapeHtml(device.label || "Unnamed device")}}</strong> · ${{escapeHtml(device.device_type || "device")}} · ${{escapeHtml(sharedLabel)}} · ${{escapeHtml(device.posture || "unassigned")}}
            <br>
            Mapped to: ${{escapeHtml(mappedLabel)}} · Trust: ${{escapeHtml(device.trust_level || "trusted")}}
            <br>
            Last actor: ${{escapeHtml(lastActor)}} · Suggested default: ${{escapeHtml(suggested)}}
            <br>
            Last seen: ${{escapeHtml(device.last_seen_at || "never")}} · Fingerprint: ${{escapeHtml(fingerprintLabel)}}
            ${{currentBadge}}
            <div class="settings-grid" style="margin-top:12px;">
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
        list.innerHTML = `<div class="metric">Loading device registry…</div>`;
        try {{
          const data = await loadJSON("/api/connected-devices");
          state.connectedDevices = data;
          renderSummary(data);
          const devices = data.devices || [];
          list.innerHTML = devices.length
            ? devices.map((device) => renderDeviceCard(device, data)).join("")
            : `<div class="metric">No device sessions have been registered yet. Open JARVIS on the device and bind the current browser first.</div>`;
          wireDeviceButtons(data);
          status.textContent = devices.length
            ? `Showing ${{devices.length}} known device sessions. Unassigned devices can be mapped directly here.`
            : "No device sessions have been registered yet.";
        }} catch (error) {{
          summary.innerHTML = `<div class="metric">Connected device summary unavailable.</div>`;
          list.innerHTML = `<div class="metric">Connected device registry unavailable: ${{escapeHtml(error.message || "request failed")}}</div>`;
          status.textContent = error.message || "Connected device refresh failed.";
        }}
      }}

      refreshButton?.addEventListener("click", refreshDevices);
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
          const host = data.service_plan || {{}};
          container.innerHTML = `
            <div class="metric"><strong>JARVIS launch agent</strong> ${{jarvis.installed ? (jarvis.loaded ? "installed and loaded" : "installed but not loaded") : "not installed"}}</div>
            <div class="metric"><strong>OpenViking launch agent</strong> ${{openviking.installed ? (openviking.loaded ? "installed and loaded" : "installed but not loaded") : "not installed"}}</div>
            <div class="metric"><strong>LAN URL</strong> ${{escapeHtml(data.lan_url || host.lan_url || window.location.origin)}}</div>
            <div class="metric"><strong>Hostname</strong> ${{escapeHtml(data.hostname || host.hostname || "jarvis.local")}}</div>
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
            host_label: document.getElementById("identity-service-host-label")?.value || "",
            host_type: document.getElementById("identity-service-host-type")?.value || "",
            lan_url: document.getElementById("identity-service-lan-url")?.value || "",
            hostname: document.getElementById("identity-service-hostname")?.value || "",
            notes: document.getElementById("identity-service-notes")?.value || "",
            always_on_enabled: !!document.getElementById("identity-service-always-on")?.checked,
            launch_on_boot: !!document.getElementById("identity-service-launch-on-boot")?.checked,
            watchdog_enabled: !!document.getElementById("identity-service-watchdog")?.checked,
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

    async function refreshDashboard() {{
      const actor = preferredActorLabel();
      const data = mergeDashboardState(await loadJSON(`/api/dashboard?actor=${{encodeURIComponent(actor)}}`));
      const activeLocationRecord = state.locationSettings?.active_location || null;
      const activeLocationLabel = activeLocationRecord?.label || data.location || "";
      const activeLocation = /^QA Location \\d+$/i.test(activeLocationLabel)
        ? (activeLocationRecord?.geography || "")
        : activeLocationLabel;
      const purpose = data.mode_brief?.purpose || "Standing by for voice or typed command.";
      updateRuntimeFreshness(data);
      fillSignalRail(data);
      fillBrainGraph(data);
      fillPacketStrip();
      const assistantSurface = data.assistant_surface || {{}};
      const surfaceKey = assistantSurface.surface_key || "";
      const suggestedPacket = assistantSurface.auto_open_packet || "";
      if (
        suggestedPacket &&
        surfaceKey &&
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
        return;
      }}
      if (state.packet && state.packetHydrationPending !== state.packet) {{
        openPacket(state.packet);
      }}
      if (await maybeAutoOpenCadenceReview(data.assistant_notifications || {{}})) {{
        return;
      }}
      await deliverAssistantBrowserAlerts().catch((error) => console.warn("Assistant browser alerts failed", error));
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
        fillSignalRail(state.dashboard);
        fillPacketStrip();
      }}
      const surfaceKey = tick.assistant_surface?.surface_key || "";
      const suggestedPacket = tick.assistant_surface?.auto_open_packet || "";
      if (
        tick.should_surface &&
        suggestedPacket &&
        surfaceKey &&
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
      await deliverAssistantBrowserAlerts().catch((error) => console.warn("Assistant browser alerts failed", error));
      return tick;
    }}

    function scheduleAssistantAutonomy() {{
      if (state.autonomyTickTimer) {{
        window.clearInterval(state.autonomyTickTimer);
      }}
      state.autonomyTickTimer = window.setInterval(() => {{
        runAssistantAutonomySweep().catch((error) => console.warn("Assistant autonomy sweep failed", error));
      }}, 120000);
    }}

    async function runAssistantBackgroundAutonomy() {{
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
      setVoiceState("idle", "Standing by for voice or typed command.");
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
          extendConversationWindow();
          setVoiceState("idle", 'Standing by for "Hey Jarvis".');
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

    async function speakText(text) {{
      if (!text) {{
        setVoiceState("idle", "Standing by for voice or typed command.");
        return;
      }}
      stopSpeaking();
      if (!state.speechEnabled) {{
        setVoiceState("speaking", "JARVIS is speaking.");
        const duration = Math.min(6000, Math.max(1800, text.length * 42));
        state.speakingTimer = window.setTimeout(() => setVoiceState("idle", "Standing by for voice or typed command."), duration);
        return;
      }}
      try {{
        stopRecognition();
        const response = await fetch("/api/tts", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ text }})
        }});
        if (!response.ok) {{
          throw new Error(`Voice output unavailable (${{response.status}})`);
        }}
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        state.currentAudio = audio;
        state.currentAudioUrl = audioUrl;
        audio.onplay = () => {{
          startAudioReactivePulse(audio);
          setVoiceState("speaking", "JARVIS is speaking.");
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
          extendConversationWindow();
          setVoiceState("idle", 'Standing by for "Hey Jarvis".');
          queueAlwaysOnListening();
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
    }}

    function setTalkButton(active, label = "Talk") {{
      const button = document.getElementById("voice-command");
      button.textContent = label;
      button.classList.toggle("primary", active);
    }}

    async function startVoiceCommand(options = {{}}) {{
      const automatic = Boolean(options.automatic);
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
      if (!automatic && state.alwaysOnMicEnabled) {{
        disableAlwaysOnMic("Always-on microphone disabled.");
        return;
      }}
      if (!state.alwaysOnMicEnabled) {{
        state.alwaysOnMicEnabled = true;
      }}
      if (state.recognizing || state.recognizer) {{
        return;
      }}

      stopSpeaking();
      const recognizer = new Recognition();
      clearRecognitionRestartTimer();
      state.recognizer = recognizer;
      recognizer.lang = "en-US";
      recognizer.interimResults = true;
      recognizer.continuous = false;
      recognizer.maxAlternatives = 1;
      let transcript = "";
      let finalTranscript = "";

      recognizer.onstart = () => {{
        state.recognizing = true;
        refreshMicButton();
        setVoiceState(
          "listening",
          conversationWindowActive() ? "Listening for your follow-up." : 'Listening for "Hey Jarvis".'
        );
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
        if (spoken) {{
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
          setVoiceState("idle", conversationWindowActive() ? "Listening for your follow-up." : 'Standing by for "Hey Jarvis".');
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
        refreshMicButton();
        if (spoken) {{
          handleRecognizedSpeech(spoken).catch((error) => {{
            document.getElementById("last-jarvis-text").textContent = error.message;
            syncTranscriptRail();
            setVoiceState("idle", "Command failed. Standing by.");
            queueAlwaysOnListening();
          }});
        }} else {{
          setVoiceState("idle", conversationWindowActive() ? "Listening for your follow-up." : 'Standing by for "Hey Jarvis".');
          queueAlwaysOnListening();
        }}
      }};

      recognizer.start();
    }}

    function packetFromRequest(request) {{
      const lowered = request.toLowerCase();
      if (lowered.includes("today board") || lowered.includes("run my day") || lowered.includes("what needs my attention")) return "today";
      if (lowered.includes("brief") || lowered.includes("agenda") || lowered.includes("today")) return "briefing";
      if (lowered.includes("home") || lowered.includes("garage") || lowered.includes("weather") || lowered.includes("freezer")) return "home";
      if (lowered.includes("family") || lowered.includes("dinner") || lowered.includes("grocery") || lowered.includes("calm version")) return "family";
      if (lowered.includes("security") || lowered.includes("door") || lowered.includes("arrival")) return "security";
      if (lowered.includes("camera") || lowered.includes("look at") || lowered.includes("look on") || lowered.includes("see this") || lowered.includes("desk")) return "vision";
      if (lowered.includes("chronicle") || lowered.includes("scripture") || lowered.includes("prayer")) return "chronicle";
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
      const request = document.getElementById("command-input").value.trim();
      if (!request) return;
      if (fromSpeech || state.alwaysOnMicEnabled) {{
        extendConversationWindow();
      }}
      stopRecognition();
      document.getElementById("last-user-text").textContent = request;
      syncTranscriptRail();
      setVoiceState("responding", "JARVIS is reasoning.");
      const data = await loadJSON("/api/respond", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ actor, room, request }})
      }});
      updateSourceIndicator(data.provider || "standby", data.model || "");
      const output = data.output_text || "No response returned.";
      document.getElementById("last-jarvis-text").textContent = output;
      syncTranscriptRail();
      const ambientSubtitle = document.getElementById("ambient-subtitle");
      if (ambientSubtitle) ambientSubtitle.textContent = output;
      await refreshDashboard();
      const suggestedPacket = packetFromRequest(request);
      if (suggestedPacket) {{
        if (suggestedPacket === "catalyst") {{
          state.catalystPage = catalystPageFromRequest(request);
        }}
        openPacket(suggestedPacket);
      }}
      await speakText(output);
    }}

    document.getElementById("send-command").addEventListener("click", () => {{
      sendCommand().catch((error) => {{
        document.getElementById("last-jarvis-text").textContent = error.message;
        syncTranscriptRail();
        setVoiceState("idle", "Command failed. Standing by.");
      }});
    }});

    document.getElementById("voice-command").addEventListener("click", () => {{
      startVoiceCommand({{ automatic: false }}).catch((error) => {{
        document.getElementById("last-jarvis-text").textContent = error.message;
        syncTranscriptRail();
        setVoiceState("idle", "Voice command failed.");
      }});
    }});

    document.getElementById("mode-toggle").addEventListener("click", () => {{
      const panel = document.getElementById("mode-panel");
      if (panel.classList.contains("open")) {{
        closeModePanel();
      }} else {{
        openModePanel();
      }}
    }});

    document.getElementById("mode-panel-close").addEventListener("click", closeModePanel);
    document.getElementById("mode-panel-cancel").addEventListener("click", closeModePanel);
    document.getElementById("mode-panel-apply").addEventListener("click", () => {{
      applyModeTransition().catch((error) => {{
        document.getElementById("mode-panel-status").textContent = error.message;
      }});
    }});
    document.querySelector(".brain-graph-panel")?.addEventListener("click", () => {{
      openPacket("brains");
    }});
    document.getElementById("open-context-controls").addEventListener("click", () => {{
      const panel = document.getElementById("context-panel");
      if (panel.classList.contains("open")) {{
        closeContextPanel();
      }} else {{
        openContextPanel();
      }}
    }});
    document.getElementById("context-panel-close").addEventListener("click", closeContextPanel);
    document.getElementById("context-panel-done").addEventListener("click", closeContextPanel);
    document.getElementById("actor").addEventListener("change", syncContextPanelCopy);
    document.getElementById("room").addEventListener("change", syncContextPanelCopy);

    document.getElementById("packet-strip-toggle").addEventListener("click", () => {{
      togglePacketStrip(true);
    }});

    document.getElementById("signal-rail-toggle").addEventListener("click", () => {{
      toggleSignalRail(true);
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
      if (event.key === "Enter") {{
        event.preventDefault();
        sendCommand().catch((error) => {{
          document.getElementById("last-jarvis-text").textContent = error.message;
          syncTranscriptRail();
          setVoiceState("idle", "Command failed. Standing by.");
        }});
      }}
    }});

    document.getElementById("open-settings").addEventListener("click", () => {{
      openSettings();
    }});

    document.getElementById("close-modal").addEventListener("click", closePacket);
    document.getElementById("modal-layer").addEventListener("click", (event) => {{
      if (event.target.id === "modal-layer") {{
        closePacket();
      }}
    }});

    window.addEventListener("keydown", (event) => {{
      if (event.key === "Escape") {{
        closeContextPanel();
        closeModePanel();
        closePacket();
      }}
    }});

    function connectEventStream() {{
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const socket = new WebSocket(`${{protocol}}://${{window.location.host}}/ws/events`);
      socket.addEventListener("message", (event) => {{
        try {{
          const payload = JSON.parse(event.data);
          if (payload.dashboard || payload.refresh) {{
            refreshDashboard().catch((error) => console.warn("Dashboard refresh from event stream failed", error));
          }}
        }} catch (error) {{
          console.warn("JARVIS event stream parse error", error);
        }}
      }});
      socket.addEventListener("close", () => {{
        window.setTimeout(connectEventStream, 1500);
      }});
    }}

    updateClock();
    window.setInterval(updateClock, 1000);
    state.browserAlertsEnabled = loadBrowserAlertsEnabled();
    state.browserAlertsPermission = browserAlertsSupported() ? Notification.permission : "unsupported";
    connectEventStream();
    scheduleAssistantAutonomy();
    scheduleAssistantBackgroundRun();
    state.lastAssistantSurfaceKey = loadAssistantSurfaceKey();
    loadDesignReviewState().finally(() => {{
      ensureHoloCore();
      syncDesignReviewPanel();
    }});
    refreshVoiceSettings()
      .then(() => bindShellIdentity().catch(() => null))
      .then(() => refreshDashboard())
      .then(() => checkFirstLight().catch(() => null))
      .catch((error) => {{
        document.getElementById("last-jarvis-text").textContent = error.message;
        syncTranscriptRail();
      }});
    window.addEventListener("beforeunload", () => {{
      clearRecognitionRestartTimer();
      stopRecognition();
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
    enableAlwaysOnMic('Standing by for "Hey Jarvis".');
  </script>
</body>
</html>"""
