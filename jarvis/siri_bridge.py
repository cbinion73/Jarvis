"""
JARVIS · Siri Bridge
Handles Siri Shortcut intents and natural-language queries routed from iOS.

Each intent returns a dict:
  reply      : str   — text Siri will speak aloud
  action     : str   — "none" | "open_url" | "maps"
  url        : str   — URL to open (Apple Maps deeplink, web URL, etc.)
  card_title : str   — short title for the Shortcuts widget display
  card_body  : str   — longer body for the widget
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

JARVIS_TAILSCALE_URL = "https://chriss-mac-mini.tail076511.ts.net"


# ---------------------------------------------------------------------------
# Named intents
# ---------------------------------------------------------------------------

async def handle_intent(name: str, param: str, runtime: Any) -> dict:
    """Route a named Siri intent to the right handler."""
    name = name.lower().strip()
    handlers = {
        "dinner":   _intent_dining,
        "lunch":    _intent_dining,
        "breakfast": _intent_dining,
        "dining":   _intent_dining,
        "food":     _intent_dining,
        "brief":    _intent_brief,
        "briefing": _intent_brief,
        "morning":  _intent_brief,
        "health":   _intent_health,
        "fitness":  _intent_health,
        "sam":      _intent_health,
        "status":   _intent_status,
        "tasks":    _intent_tasks,
        "calendar": _intent_calendar,
        "schedule": _intent_calendar,
        "weather":  _intent_weather,
    }
    handler = handlers.get(name, _intent_general)
    try:
        return await handler(param, runtime)
    except Exception as exc:
        logger.warning("siri_bridge.handle_intent(%s) failed: %s", name, exc)
        return _reply("JARVIS ran into a problem with that request. Try again in a moment.")


async def handle_query(query: str, runtime: Any) -> dict:
    """Handle a free-form natural-language query — route by detected intent."""
    q = query.lower()

    # Dining direction variants
    if any(w in q for w in ("dinner", "lunch", "breakfast", "restaurant", "eat", "food", "dining")):
        if any(w in q for w in ("direction", "navigate", "take me", "go to", "drive to", "route")):
            return await _intent_dining(query, runtime)
        # General food question → Sam
        return await _intent_sam_chat(query, runtime)

    if any(w in q for w in ("brief", "briefing", "morning", "what's happening", "update")):
        return await _intent_brief(query, runtime)

    if any(w in q for w in ("health", "fitness", "readiness", "hrv", "sleep", "steps", "sam")):
        return await _intent_health(query, runtime)

    if any(w in q for w in ("calendar", "schedule", "meeting", "appointment", "next event")):
        return await _intent_calendar(query, runtime)

    if any(w in q for w in ("task", "todo", "reminder", "what do i need")):
        return await _intent_tasks(query, runtime)

    if any(w in q for w in ("weather", "temperature", "rain", "forecast")):
        return await _intent_weather(query, runtime)

    # Default — route to JARVIS general AI
    return await _intent_general(query, runtime)


# ---------------------------------------------------------------------------
# Intent handlers
# ---------------------------------------------------------------------------

async def _intent_dining(param: str, runtime: Any) -> dict:
    """Get top restaurant pick and return Apple Maps navigation URL."""
    import asyncio
    from .dining import recommend_restaurants

    hour = datetime.now().hour
    if "lunch" in param.lower() or 11 <= hour < 15:
        meal = "lunch"
    elif "breakfast" in param.lower() or hour < 11:
        meal = "breakfast"
    else:
        meal = "dinner"

    try:
        rec = await asyncio.to_thread(recommend_restaurants, None, 1)
        picks = rec.get("recommendations") or []
        if not picks:
            return _reply(
                "I couldn't find open restaurants right now. "
                "Check the JARVIS Dining view for options.",
                action="open_url",
                url=f"{JARVIS_TAILSCALE_URL}/?view=dining",
            )

        place = picks[0]
        name    = place.get("name", "that restaurant")
        address = place.get("address", "")
        dist    = place.get("distance_mi", "?")
        rating  = place.get("rating", "")
        price   = place.get("price", "")

        # Apple Maps directions URL
        maps_query = f"{name}, {address}".replace(" ", "+")
        maps_url = f"maps://?daddr={maps_query}&dirflg=d"

        spoken = (
            f"Sam's top {meal} pick is {name}, "
            f"{dist} miles away"
            f"{', rated ' + str(rating) + ' stars' if rating else ''}"
            f"{', ' + _price_spoken(price) if price else ''}. "
            f"Opening directions now."
        )

        return _reply(
            spoken,
            action="maps",
            url=maps_url,
            card_title=name,
            card_body=f"{dist} mi · {rating}★ · {price}\n{address}",
        )
    except Exception as exc:
        logger.warning("_intent_dining failed: %s", exc)
        return _reply("Couldn't get dining recommendations right now.")


async def _intent_brief(param: str, runtime: Any) -> dict:
    """Condensed morning brief spoken summary."""
    try:
        import asyncio

        async def _fetch():
            import httpx
            r = httpx.get(f"http://127.0.0.1:8787/api/briefing", timeout=8)
            return r.json()

        data = await asyncio.wait_for(_fetch(), timeout=10)
        sections = data.get("sections") or []
        lines = [f"Good {'morning' if datetime.now().hour < 12 else 'evening'}, Chris. Here's your JARVIS brief."]

        for s in sections[:4]:
            sid = s.get("id")
            if sid == "calendar" and s.get("items"):
                ev = s["items"][0]
                t = ev.get("time", "")
                d = ev.get("day", "")
                lines.append(f"Next up: {ev['title']}{' at ' + t if t else ''}{' on ' + d if d and d != 'Today' else ''}.")
            elif sid == "tasks" and s.get("stats"):
                st = s["stats"]
                if st.get("overdue"):
                    lines.append(f"You have {st['overdue']} overdue task{'s' if st['overdue'] != 1 else ''}.")
                elif st.get("due_today"):
                    lines.append(f"{st['due_today']} task{'s' if st['due_today'] != 1 else ''} due today.")
            elif sid == "health" and s.get("text"):
                lines.append(s["text"][:200].rstrip(".") + ".")
            elif sid == "dining" and s.get("items"):
                p = s["items"][0]
                lines.append(f"Sam's {s.get('meal_type','dinner')} pick: {p['name']}, {p.get('distance_mi','?')} miles away.")
            elif sid == "strategic" and s.get("text"):
                lines.append(s["text"][:200].rstrip(".") + ".")

        spoken = " ".join(lines)
        return _reply(
            spoken,
            card_title="JARVIS Brief",
            card_body=spoken,
            action="open_url",
            url=f"{JARVIS_TAILSCALE_URL}/",
        )
    except Exception as exc:
        logger.warning("_intent_brief failed: %s", exc)
        return _reply("Your JARVIS brief isn't available right now.")


async def _intent_health(param: str, runtime: Any) -> dict:
    """Sam's health status summary."""
    try:
        import asyncio, httpx
        r = await asyncio.to_thread(
            lambda: httpx.get("http://127.0.0.1:8787/api/health/summary", timeout=8).json()
        )
        score   = r.get("readiness", {}).get("score", "?")
        grade   = r.get("readiness", {}).get("grade", "")
        metrics = r.get("metrics", {})
        hrv     = metrics.get("hrv", "?")
        sleep   = metrics.get("sleep_hours", "?")
        steps   = metrics.get("steps")
        anomalies = r.get("anomalies") or []

        spoken = f"Your readiness score is {score} out of 100"
        if grade:
            spoken += f", grade {grade}"
        spoken += "."
        if hrv and hrv != "?":
            spoken += f" HRV is {hrv} milliseconds."
        if sleep and sleep != "?":
            spoken += f" You got {sleep} hours of sleep."
        if steps:
            spoken += f" {int(steps):,} steps so far today."
        if anomalies:
            spoken += f" Sam flagged {len(anomalies)} anomal{'y' if len(anomalies) == 1 else 'ies'} — check JARVIS for details."

        return _reply(
            spoken,
            card_title=f"Readiness {score}/100",
            card_body=spoken,
            action="open_url",
            url=f"{JARVIS_TAILSCALE_URL}/?view=health",
        )
    except Exception as exc:
        logger.warning("_intent_health failed: %s", exc)
        return _reply("Health data isn't available right now.")


async def _intent_sam_chat(query: str, runtime: Any) -> dict:
    """Route a food/health question to Sam."""
    try:
        import asyncio, httpx
        payload = {"message": query, "history": [], "brief": True}
        r = await asyncio.to_thread(
            lambda: httpx.post(
                "http://127.0.0.1:8787/api/health/sam/chat",
                json=payload, timeout=15,
            ).json()
        )
        reply = r.get("reply", "Sam couldn't respond right now.")
        # Strip any markdown for spoken output
        import re
        reply = re.sub(r"\*+", "", reply)
        reply = re.sub(r"#+\s*", "", reply)
        return _reply(reply[:400], card_title="Sam Wilson", card_body=reply)
    except Exception as exc:
        logger.warning("_intent_sam_chat failed: %s", exc)
        return _reply("Sam isn't available right now. Check JARVIS on your phone.")


async def _intent_calendar(param: str, runtime: Any) -> dict:
    """Next calendar event summary."""
    try:
        import asyncio, httpx
        r = await asyncio.to_thread(
            lambda: httpx.get(
                "http://127.0.0.1:8787/api/home/calendar/upcoming?days=2",
                timeout=8
            ).json()
        )
        events = r.get("upcoming_3_days") or r.get("events") or []
        if not events:
            return _reply("You have no upcoming events on your calendar.")
        ev = events[0]
        title = ev.get("title", "an event")
        start = ev.get("start_time", "")
        time_str = ""
        if start:
            try:
                dt = datetime.fromisoformat(str(start))
                time_str = dt.strftime("%-I:%M %p on %A")
            except Exception:
                time_str = str(start)[:16]
        spoken = f"Your next event is {title}"
        if time_str:
            spoken += f" at {time_str}"
        spoken += "."
        if len(events) > 1:
            spoken += f" You have {len(events)} events coming up."
        return _reply(spoken, card_title="Calendar", card_body=spoken)
    except Exception as exc:
        logger.warning("_intent_calendar failed: %s", exc)
        return _reply("I couldn't load your calendar right now.")


async def _intent_tasks(param: str, runtime: Any) -> dict:
    """Overdue and due-today task summary."""
    try:
        import asyncio, httpx
        r = await asyncio.to_thread(
            lambda: httpx.get("http://127.0.0.1:8787/api/tasks", timeout=8).json()
        )
        tasks = r.get("tasks") or []
        overdue = [t for t in tasks if t.get("status") == "overdue"]
        today   = [t for t in tasks if t.get("due_today")]
        if not tasks:
            return _reply("You're clear — no tasks in JARVIS right now.")
        spoken = ""
        if overdue:
            spoken += f"{len(overdue)} overdue task{'s' if len(overdue) != 1 else ''}: {overdue[0].get('title', '')}."
        if today:
            spoken += f" {len(today)} due today."
        if not spoken:
            spoken = f"You have {len(tasks)} tasks. None overdue."
        return _reply(spoken.strip(), card_title="Tasks", card_body=spoken)
    except Exception as exc:
        logger.warning("_intent_tasks failed: %s", exc)
        return _reply("I couldn't load your tasks right now.")


async def _intent_weather(param: str, runtime: Any) -> dict:
    """Weather summary."""
    try:
        import asyncio, httpx
        r = await asyncio.to_thread(
            lambda: httpx.get("http://127.0.0.1:8787/api/weather", timeout=8).json()
        )
        current = r.get("current") or {}
        temp    = current.get("temp", "?")
        desc    = current.get("description", "")
        feels   = current.get("feels_like", "")
        spoken = f"It's {temp}°"
        if desc:
            spoken += f" and {desc}"
        if feels:
            spoken += f", feels like {feels}°"
        spoken += " near Alexandria."
        return _reply(spoken, card_title="Weather", card_body=spoken)
    except Exception as exc:
        logger.warning("_intent_weather failed: %s", exc)
        return _reply("Weather data isn't available right now.")


async def _intent_status(param: str, runtime: Any) -> dict:
    """JARVIS system status."""
    try:
        import asyncio, httpx
        services = await asyncio.to_thread(
            lambda: httpx.get("http://127.0.0.1:8787/api/status", timeout=5).json()
        )
        ok_count    = sum(1 for s in services if s.get("ok"))
        total_count = len(services)
        spoken = f"JARVIS is online. {ok_count} of {total_count} services are connected."
        for s in services:
            if not s.get("ok"):
                spoken += f" {s.get('name','Unknown')} is offline."
                break
        return _reply(spoken, card_title="JARVIS Status", card_body=spoken)
    except Exception:
        return _reply("JARVIS is online and running.")


async def _intent_general(query: str, runtime: Any) -> dict:
    """Fallback: send to JARVIS main AI via Sam chat (brief mode)."""
    if not query:
        return _reply(
            "JARVIS is ready. Open the app or use a specific command like "
            "'JARVIS dinner', 'JARVIS brief', or 'ask JARVIS' for a free question."
        )
    return await _intent_sam_chat(query, runtime)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reply(
    text: str,
    *,
    action: str = "none",
    url: str = "",
    card_title: str = "JARVIS",
    card_body: str = "",
) -> dict:
    return {
        "reply":      text,
        "action":     action,
        "url":        url,
        "card_title": card_title or "JARVIS",
        "card_body":  card_body or text,
        "spoken":     text,   # alias — some shortcut actions use this key
    }


def _price_spoken(price: str) -> str:
    map_ = {"$": "inexpensive", "$$": "moderate", "$$$": "pricey", "$$$$": "upscale"}
    return map_.get(price, "")


# ---------------------------------------------------------------------------
# Siri setup page HTML
# ---------------------------------------------------------------------------

JARVIS_URL = "https://chriss-mac-mini.tail076511.ts.net"

def siri_setup_page() -> str:
    """Return the HTML setup page served at /siri."""
    shortcuts = [
        {
            "name": "JARVIS Dinner",
            "phrase": "Hey Siri, JARVIS dinner",
            "description": "Gets Sam's top dinner pick and opens directions in Maps.",
            "endpoint": f"{JARVIS_URL}/api/siri/intent?name=dinner",
            "action": "open_url",
            "steps": [
                "Add a <b>Get Contents of URL</b> action — URL: <code>{JARVIS_URL}/api/siri/intent?name=dinner</code>",
                "Add a <b>Get Dictionary Value</b> action — Key: <code>reply</code>",
                "Add a <b>Speak Text</b> action — Input: Dictionary Value",
                "Add a <b>Get Dictionary Value</b> action — Key: <code>url</code>  (from the same first result)",
                "Add an <b>Open URL</b> action — Input: that Dictionary Value",
            ],
        },
        {
            "name": "Ask JARVIS",
            "phrase": "Hey Siri, ask JARVIS",
            "description": "Asks you what you want to know, sends it to JARVIS, and reads the reply.",
            "endpoint": f"{JARVIS_URL}/api/siri?q=",
            "action": "speak",
            "steps": [
                "Add an <b>Ask for Input</b> action — Prompt: <i>What do you want to ask JARVIS?</i>  Type: Text",
                'Add a <b>URL</b> action — set to <code>{JARVIS_URL}/api/siri?q=</code> then append the <i>Provided Input</i> variable',
                "Add a <b>Get Contents of URL</b> action",
                "Add a <b>Get Dictionary Value</b> action — Key: <code>reply</code>",
                "Add a <b>Speak Text</b> action — Input: Dictionary Value",
            ],
        },
        {
            "name": "JARVIS Brief",
            "phrase": "Hey Siri, JARVIS brief",
            "description": "Reads your condensed morning briefing: next event, tasks, health, and dining pick.",
            "endpoint": f"{JARVIS_URL}/api/siri/intent?name=brief",
            "action": "speak",
            "steps": [
                "Add a <b>Get Contents of URL</b> action — URL: <code>{JARVIS_URL}/api/siri/intent?name=brief</code>",
                "Add a <b>Get Dictionary Value</b> action — Key: <code>reply</code>",
                "Add a <b>Speak Text</b> action — Input: Dictionary Value",
            ],
        },
        {
            "name": "JARVIS Health",
            "phrase": "Hey Siri, JARVIS health",
            "description": "Sam reads your current readiness score, HRV, sleep, and any anomalies.",
            "endpoint": f"{JARVIS_URL}/api/siri/intent?name=health",
            "action": "speak",
            "steps": [
                "Add a <b>Get Contents of URL</b> action — URL: <code>{JARVIS_URL}/api/siri/intent?name=health</code>",
                "Add a <b>Get Dictionary Value</b> action — Key: <code>reply</code>",
                "Add a <b>Speak Text</b> action — Input: Dictionary Value",
            ],
        },
    ]

    cards = ""
    for i, s in enumerate(shortcuts):
        steps_html = "".join(f'<li style="margin-bottom:8px;">{step.replace("{JARVIS_URL}", JARVIS_URL)}</li>' for step in s["steps"])
        cards += f"""
        <div class="siri-card" id="card-{i}">
          <div class="siri-card-header" onclick="toggleCard({i})">
            <div>
              <div class="siri-phrase">🎙️ "{s['phrase']}"</div>
              <div class="siri-desc">{s['description']}</div>
            </div>
            <span class="chevron" id="chev-{i}">▸</span>
          </div>
          <div class="siri-steps" id="steps-{i}">
            <div class="steps-intro">Open the <b>Shortcuts</b> app → tap <b>+</b> → name it <b>"{s['name']}"</b>, then add these actions in order:</div>
            <ol style="margin:12px 0 0 20px;line-height:1.9;">{steps_html}</ol>
            <div style="margin-top:14px;">
              <a href="{s['endpoint'].replace('{JARVIS_URL}', JARVIS_URL)}" class="test-btn">Test endpoint ↗</a>
            </div>
          </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS · Siri Setup</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #0b0d14; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      padding: 24px 16px 48px; max-width: 600px; margin: 0 auto;
    }}
    .page-title {{
      font-size: 26px; font-weight: 800; color: #fff;
      margin-bottom: 4px; letter-spacing: -0.5px;
    }}
    .page-sub {{
      font-size: 13px; color: #64748b; margin-bottom: 28px; line-height: 1.5;
    }}
    .section-label {{
      font-size: 10px; text-transform: uppercase; letter-spacing: .1em;
      color: #4f46e5; font-weight: 700; margin-bottom: 14px;
    }}
    .siri-card {{
      background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
      border-radius: 14px; margin-bottom: 12px; overflow: hidden;
    }}
    .siri-card-header {{
      display: flex; justify-content: space-between; align-items: center;
      padding: 16px 18px; cursor: pointer; gap: 12px;
    }}
    .siri-phrase {{
      font-size: 15px; font-weight: 700; color: #a5b4fc; margin-bottom: 3px;
    }}
    .siri-desc {{ font-size: 12px; color: #64748b; line-height: 1.4; }}
    .chevron {{ font-size: 14px; color: #475569; transition: transform .2s; flex-shrink: 0; }}
    .chevron.open {{ transform: rotate(90deg); }}
    .siri-steps {{
      display: none; padding: 0 18px 18px; border-top: 1px solid rgba(255,255,255,0.06);
    }}
    .siri-steps.open {{ display: block; }}
    .steps-intro {{ font-size: 12px; color: #94a3b8; margin-top: 14px; line-height: 1.6; }}
    li {{ font-size: 13px; color: #cbd5e1; line-height: 1.6; }}
    code {{
      background: rgba(99,102,241,0.15); color: #a5b4fc; border-radius: 4px;
      padding: 1px 5px; font-size: 11px; word-break: break-all;
    }}
    .test-btn {{
      display: inline-block; padding: 7px 16px; border-radius: 8px;
      background: rgba(99,102,241,0.18); border: 1px solid rgba(99,102,241,0.35);
      color: #a5b4fc; font-size: 12px; text-decoration: none;
    }}
    .info-box {{
      background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.25);
      border-radius: 12px; padding: 14px 16px; margin-bottom: 24px; font-size: 13px;
      color: #94a3b8; line-height: 1.7;
    }}
    .info-box b {{ color: #c7d2fe; }}
    .url-chip {{
      display: inline-block; background: rgba(15,23,42,0.6);
      border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;
      padding: 8px 12px; font-size: 12px; color: #7c3aed; word-break: break-all;
      margin-top: 10px; font-family: monospace;
    }}
  </style>
</head>
<body>
  <div class="page-title">J·A·R·V·I·S · Siri</div>
  <div class="page-sub">Create these Shortcuts on your iPhone to control JARVIS with your voice.</div>

  <div class="info-box">
    <b>How it works:</b> You say "Hey Siri" + the shortcut name. Siri activates the Shortcut, which calls JARVIS, and Siri reads the reply back to you.<br><br>
    <b>Your JARVIS URL (already on Tailscale):</b>
    <div class="url-chip">{JARVIS_URL}</div>
  </div>

  <div class="section-label">Shortcuts to Create</div>
  {cards}

  <div style="margin-top:28px;padding:14px 16px;border:1px solid rgba(255,255,255,0.07);border-radius:12px;">
    <div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#475569;margin-bottom:8px;">Quick test</div>
    <p style="font-size:13px;color:#64748b;margin-bottom:10px;">
      Tap any "Test endpoint" link above to confirm JARVIS responds before building the Shortcut.
    </p>
    <a href="{JARVIS_URL}/api/siri/intent?name=status" class="test-btn">Test JARVIS connection ↗</a>
  </div>

  <script>
    function toggleCard(i) {{
      var steps = document.getElementById('steps-' + i);
      var chev  = document.getElementById('chev-' + i);
      var open  = steps.classList.toggle('open');
      chev.classList.toggle('open', open);
    }}
  </script>
</body>
</html>"""
