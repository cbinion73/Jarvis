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
            {"id": "briefing", "label": "Briefing"},
            {"id": "brains", "label": "Brains"},
            {"id": "agents", "label": "Agents"},
            {"id": "home", "label": "Home"},
            {"id": "family", "label": "Family"},
            {"id": "security", "label": "Security"},
            {"id": "chronicle", "label": "Chronicle"},
            {"id": "workshop", "label": "Workshop"},
            {"id": "catalyst", "label": "Catalyst"},
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
    body[data-voice-state="idle"] {{ --energy: 0.35; }}
    body[data-voice-state="listening"] {{ --energy: 0.8; --motion-rate: 1.35; }}
    body[data-voice-state="responding"] {{ --energy: 0.6; --motion-rate: 1.15; }}
    body[data-voice-state="speaking"] {{ --energy: 1; --motion-rate: 1.75; }}
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
      border-radius: 50%;
      background:
        radial-gradient(circle at center, rgba(112, 233, 255, 0.12) 0%, rgba(64, 192, 255, 0.08) 20%, rgba(5, 10, 18, 0.92) 34%, rgba(4, 9, 16, 0.54) 50%, rgba(4, 9, 16, 0.10) 63%, transparent 74%),
        radial-gradient(circle at center, rgba(3, 7, 14, 0.98) 0%, rgba(3, 8, 14, 0.94) 18%, rgba(4, 9, 16, 0.58) 36%, rgba(4, 9, 16, 0.12) 56%, transparent 68%);
      filter: blur(0.5px);
      transform: scale(0.965);
      box-shadow:
        inset 0 0 70px rgba(110, 235, 255, 0.08),
        0 0 90px rgba(63, 175, 255, 0.12);
      z-index: 0;
    }}
    .holo-core-shell {{
      z-index: 1;
      display: grid;
      place-items: center;
      transform: translateY(-10px);
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
      position: absolute;
      left: 50%;
      bottom: 8.8%;
      transform: translateX(-50%);
      width: 40%;
      aspect-ratio: 1;
      border-radius: 50%;
      background:
        radial-gradient(circle at center, rgba(116, 232, 255, calc(0.16 + (var(--energy) * 0.12))) 0%, rgba(116, 232, 255, 0.06) 24%, rgba(8, 18, 30, 0) 58%),
        radial-gradient(circle at center, rgba(8, 18, 30, 0) 54%, rgba(95, 215, 255, 0.16) 62%, rgba(8, 18, 30, 0) 70%);
      box-shadow:
        0 0 42px rgba(103, 226, 255, 0.18),
        0 0 90px rgba(59, 147, 255, 0.12);
      z-index: 1;
      pointer-events: none;
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
      position: absolute;
      right: 0;
      bottom: 148px;
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
      position: absolute;
      right: 0;
      bottom: 148px;
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
      </div>
      <div class="meta-rail">
        <span class="meta-chip" id="meta-time">--:--</span>
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

  <script type="module">
    import * as THREE from "https://unpkg.com/three@0.174.0/build/three.module.js";

    const packetPresets = {packet_presets};
    const availableModes = {available_modes};
    const state = {{
      dashboard: null,
      lastBriefing: "",
      packet: "",
      speechEnabled: true,
      speakingTimer: null,
      energyTimer: null,
      currentAudio: null,
      currentAudioUrl: "",
      recognizer: null,
      recognizing: false,
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
      locationSettings: null,
      settingsMessage: "",
      brainMeshScenes: new Map(),
      holoCoreScene: null,
      audioContext: null,
      audioAnalyser: null,
      audioSourceNode: null,
      audioReactiveFrame: null,
      audioReactive: false,
    }};

    function escapeHtml(value) {{
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }}

    async function loadJSON(url, options = undefined) {{
      const response = await fetch(url, options);
      if (!response.ok) {{
        throw new Error(`Request failed: ${{response.status}}`);
      }}
      return response.json();
    }}

    function browserSpeechRecognition() {{
      return window.SpeechRecognition || window.webkitSpeechRecognition || null;
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
      state.energyTarget =
        nextState === "speaking"
          ? (state.audioReactive ? state.energyTarget : 0.88)
          : nextState === "listening"
            ? 0.68
            : nextState === "responding"
              ? 0.54
              : 0.35;
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
        const buffer = new Uint8Array(analyser.frequencyBinCount);
        const tick = () => {{
          if (!state.audioReactive || !state.audioAnalyser) {{
            return;
          }}
          analyser.getByteFrequencyData(buffer);
          let sum = 0;
          for (let i = 0; i < buffer.length; i += 1) {{
            sum += buffer[i];
          }}
          const avg = sum / Math.max(buffer.length, 1);
          const normalized = Math.min(1.15, 0.28 + avg / 140);
          state.energyTarget = normalized;
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
      const background = data.background_agents || {{}};
      const packets = [
        ["House", data.home_overview?.summary?.[0] || "House profile standing by"],
        ["Weather", data.weather || "Weather standing by"],
        ["Mission", data.cards?.mission?.summary || "Mission context ready"],
        ["Agents", `${{background.awake_count ?? 0}} awake · ${{background.idle_count ?? 0}} idle · ${{background.blocked_count ?? 0}} blocked`],
        ["Watch", data.cold_storage_monitor?.recommended_action || data.overnight_review?.summary || "No watch item loaded"],
      ];
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

    async function refreshVoiceSettings() {{
      const [settings, options, accounts, locations] = await Promise.all([
        loadJSON("/api/voice-settings"),
        loadJSON("/api/voice-options"),
        loadJSON("/api/accounts"),
        loadJSON("/api/location-settings")
      ]);
      state.voiceSettings = settings;
      state.voiceOptions = options;
      state.accountRegistry = accounts;
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
      state.packet = packetId;
      state.packetStripExpanded = true;
      document.body.classList.add("modal-open");
      fillPacketStrip();
      const modal = document.getElementById("modal-layer");
      const title = document.getElementById("modal-title");
      const body = document.getElementById("modal-body");
      const data = state.dashboard || {{}};
      let heading = "Packet";
      let content = "";

      if (packetId === "briefing") {{
        heading = "Morning Brief";
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
              packetBlock("Scheduler Status", `
                <div class="stack">
                  <div class="metric"><strong>Awake</strong> ${{escapeHtml(String(background.awake_count ?? 0))}}</div>
                  <div class="metric"><strong>Idle</strong> ${{escapeHtml(String(background.idle_count ?? 0))}}</div>
                  <div class="metric"><strong>Blocked</strong> ${{escapeHtml(String(background.blocked_count ?? 0))}}</div>
                  <div class="metric"><strong>Mode</strong> ${{escapeHtml((background.active_mode || "ambient-associate").replaceAll("-", " "))}}</div>
                </div>`)
            }}
            ${{
              packetBlock("Awake Now", renderList(statuses.filter((item) => item.state === "awake").map((item) => `<div><strong>${{escapeHtml(item.label)}}</strong> · ${{escapeHtml(item.reason)}}</div>`)) || `<div class="empty">No agents are currently awake.</div>`)
            }}
            ${{
              packetBlock("Blocked", renderList(statuses.filter((item) => item.state === "blocked").map((item) => `<div><strong>${{escapeHtml(item.label)}}</strong> · waiting on ${{escapeHtml((item.blocked_dependencies || []).join(", ") || "dependency")}}</div>`)) || `<div class="empty">Nothing is blocked at the moment.</div>`)
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
          </div>`;
      }} else if (packetId === "settings") {{
        heading = "Settings";
        const settings = state.voiceSettings || {{}};
        const options = state.voiceOptions || {{}};
        const accountRegistry = state.accountRegistry || {{}};
        const locationSettings = state.locationSettings || {{}};
        const stackStatus = options.stack_status || settings.stack_status || {{}};
        const googleWorkspace = data.google_workspace || {{}};
        const googleClientSecret = googleWorkspace.client_secret || {{}};
        const personalAccounts = accountRegistry.accounts || [];
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
      }} else if (packetId === "agents") {{
        document.getElementById("open-agent-hierarchy")?.addEventListener("click", () => {{
          window.open("/agents/hierarchy", "_blank", "noopener,noreferrer");
        }});
      }} else if (packetId === "catalyst") {{
        wireCatalystWorkspace();
      }} else if (packetId === "brains") {{
        const graph = data.brain_graph || {{}};
        const activeNodes = new Set(graph.active_nodes || []);
        renderBrainMesh("brain-mesh-modal", graph, activeNodes);
      }}
      modal.classList.add("open");
      modal.setAttribute("aria-hidden", "false");
      syncDesignReviewPanel();
    }}

    function closePacket() {{
      state.packet = "";
      document.body.classList.remove("modal-open");
      fillPacketStrip();
      const modal = document.getElementById("modal-layer");
      modal.classList.remove("open");
      modal.setAttribute("aria-hidden", "true");
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

    async function refreshDashboard() {{
      const data = await loadJSON("/api/dashboard");
      state.dashboard = data;
      const activeLocationRecord = state.locationSettings?.active_location || null;
      const activeLocationLabel = activeLocationRecord?.label || data.location || "";
      const activeLocation = /^QA Location \\d+$/i.test(activeLocationLabel)
        ? (activeLocationRecord?.geography || "")
        : activeLocationLabel;
      const purpose = data.mode_brief?.purpose || "Standing by for voice or typed command.";
      fillSignalRail(data);
      fillBrainGraph(data);
      fillPacketStrip();
      if (state.packet) {{
        openPacket(state.packet);
      }}
    }}

    async function loadBriefing() {{
      const actor = document.getElementById("actor").value || "Chris";
      const data = await loadJSON(`/api/briefing?actor=${{encodeURIComponent(actor)}}`);
      state.lastBriefing = data.briefing || "";
      document.getElementById("last-jarvis-text").textContent = state.lastBriefing || "Briefing unavailable.";
      syncTranscriptRail();
      openPacket("briefing");
      await speakText(state.lastBriefing);
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
    }}

    function speakWithBrowserFallback(text) {{
      if ("speechSynthesis" in window) {{
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.92;
        utterance.pitch = 0.9;
        utterance.onstart = () => setVoiceState("speaking", "JARVIS fallback voice is speaking.");
        utterance.onend = () => setVoiceState("idle", "Standing by for voice or typed command.");
        utterance.onerror = () => setVoiceState("idle", "Voice output unavailable. Standing by.");
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
          setVoiceState("idle", "Standing by for voice or typed command.");
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
          }}
        }};
        await audio.play();
      }} catch (error) {{
        console.error(error);
        if (!speakWithBrowserFallback(text)) {{
          setVoiceState("idle", "Voice output unavailable. Standing by.");
        }}
      }}
    }}

    function stopRecognition() {{
      if (state.recognizer && state.recognizing) {{
        state.recognizer.stop();
      }}
    }}

    function setTalkButton(active, label = "Talk") {{
      const button = document.getElementById("voice-command");
      button.textContent = label;
      button.classList.toggle("primary", active);
    }}

    async function startVoiceCommand() {{
      const Recognition = browserSpeechRecognition();
      if (!Recognition) {{
        document.getElementById("last-jarvis-text").textContent =
          "This browser does not expose speech recognition. Use typed input here, or we can wire server-side microphone capture next.";
        syncTranscriptRail();
        setVoiceState("idle", "No browser microphone recognition is available.");
        return;
      }}
      if (state.recognizing) {{
        stopRecognition();
        return;
      }}

      stopSpeaking();
      const recognizer = new Recognition();
      state.recognizer = recognizer;
      recognizer.lang = "en-US";
      recognizer.interimResults = true;
      recognizer.continuous = false;
      recognizer.maxAlternatives = 1;

      recognizer.onstart = () => {{
        state.recognizing = true;
        setTalkButton(true, "Listening");
        setVoiceState("listening", "Listening for your command.");
      }};

      recognizer.onresult = (event) => {{
        let transcript = "";
        let finalTranscript = "";
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
        setTalkButton(false, "Talk");
        const code = event?.error || "unknown";
        if (code === "not-allowed" || code === "service-not-allowed") {{
          document.getElementById("last-jarvis-text").textContent =
            "Microphone access was blocked. Allow microphone permission for this page and try again.";
          syncTranscriptRail();
          setVoiceState("idle", "Microphone permission is required.");
          return;
        }}
        if (code === "no-speech") {{
          setVoiceState("idle", "No speech detected. Try again.");
          return;
        }}
        document.getElementById("last-jarvis-text").textContent = `Voice recognition error: ${{code}}`;
        syncTranscriptRail();
        setVoiceState("idle", "Voice recognition failed.");
      }};

      recognizer.onend = () => {{
        const spoken = document.getElementById("command-input").value.trim();
        state.recognizing = false;
        setTalkButton(false, "Talk");
        state.recognizer = null;
        if (spoken) {{
          sendCommand().catch((error) => {{
            document.getElementById("last-jarvis-text").textContent = error.message;
            syncTranscriptRail();
            setVoiceState("idle", "Command failed. Standing by.");
          }});
        }} else {{
          setVoiceState("idle", "Standing by for voice or typed command.");
        }}
      }};

      recognizer.start();
    }}

    function packetFromRequest(request) {{
      const lowered = request.toLowerCase();
      if (lowered.includes("brief") || lowered.includes("agenda") || lowered.includes("today")) return "briefing";
      if (lowered.includes("home") || lowered.includes("garage") || lowered.includes("weather") || lowered.includes("freezer")) return "home";
      if (lowered.includes("family") || lowered.includes("dinner") || lowered.includes("grocery") || lowered.includes("calm version")) return "family";
      if (lowered.includes("security") || lowered.includes("door") || lowered.includes("arrival")) return "security";
      if (lowered.includes("chronicle") || lowered.includes("scripture") || lowered.includes("prayer")) return "chronicle";
      if (lowered.includes("workshop") || lowered.includes("printer") || lowered.includes("prototype")) return "workshop";
      if (lowered.includes("email") || lowered.includes("meeting") || lowered.includes("project plan") || lowered.includes("catalyst")) return "catalyst";
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

    async function sendCommand() {{
      const actor = document.getElementById("actor").value;
      const room = document.getElementById("room").value;
      const request = document.getElementById("command-input").value.trim();
      if (!request) return;
      document.getElementById("last-user-text").textContent = request;
      syncTranscriptRail();
      setVoiceState("responding", "JARVIS is reasoning.");
      const data = await loadJSON("/api/respond", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ actor, room, request }})
      }});
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
      startVoiceCommand().catch((error) => {{
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

    updateClock();
    window.setInterval(updateClock, 1000);
    loadDesignReviewState().finally(() => {{
      ensureHoloCore();
      syncDesignReviewPanel();
    }});
    refreshVoiceSettings()
      .then(() => refreshDashboard())
      .catch((error) => {{
        document.getElementById("last-jarvis-text").textContent = error.message;
        syncTranscriptRail();
      }});
    window.addEventListener("beforeunload", () => {{
      stopAudioReactivePulse();
      if (state.holoCoreScene) {{
        if (state.holoCoreScene.frame) cancelAnimationFrame(state.holoCoreScene.frame);
        if (state.holoCoreScene.observer) state.holoCoreScene.observer.disconnect();
        state.holoCoreScene.renderer.dispose();
      }}
      if (state.audioContext) {{
        state.audioContext.close().catch(() => null);
      }}
    }});
    setVoiceState("idle", "Standing by for voice or typed command.");
    syncTranscriptRail();
    syncContextPanelCopy();
  </script>
</body>
</html>"""
