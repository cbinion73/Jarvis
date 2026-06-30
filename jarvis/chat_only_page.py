from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runtime import JarvisRuntime


def render_chat_only_shell(runtime: "JarvisRuntime") -> str:
    try:
        actor_name = runtime.config.your_name or "Chris"
    except Exception:
        actor_name = "Chris"

    actor_name_js = actor_name.replace("\\", "\\\\").replace('"', '\\"')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>JARVIS Chat</title>
  <link rel="icon" href="data:,">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #0b1020;
      --bg-soft: #11172a;
      --panel: #141b31;
      --panel-soft: #19213b;
      --border: rgba(255,255,255,0.08);
      --border-strong: rgba(255,255,255,0.14);
      --text: #f4f7fb;
      --text-soft: #a7b4ca;
      --accent: #10a7ff;
      --accent-soft: rgba(16,167,255,0.16);
      --user: #1f6feb;
      --shadow: 0 20px 48px rgba(0,0,0,0.28);
      --radius: 18px;
      --sidebar-w: 280px;
      --content-w: 860px;
    }}

    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; min-height: 100%; }}
    body {{
      font-family: 'Inter', system-ui, sans-serif;
      background:
        radial-gradient(circle at top, rgba(16,167,255,0.08), transparent 32%),
        linear-gradient(180deg, #0a0f1d 0%, #0b1020 100%);
      color: var(--text);
    }}

    .chat-shell {{
      display: grid;
      grid-template-columns: var(--sidebar-w) minmax(0, 1fr);
      min-height: 100vh;
    }}

    .chat-sidebar {{
      border-right: 1px solid var(--border);
      background: rgba(10, 15, 29, 0.9);
      backdrop-filter: blur(24px);
      padding: 18px 14px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}

    .chat-brand {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 8px 10px 2px;
    }}

    .chat-brand strong {{
      display: block;
      font-size: 22px;
      letter-spacing: 0.03em;
    }}

    .chat-brand span {{
      display: block;
      margin-top: 3px;
      color: var(--text-soft);
      font-size: 12px;
    }}

    .chat-brand-mark {{
      width: 36px;
      height: 36px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      color: var(--accent);
      background: rgba(255,255,255,0.03);
      border: 1px solid var(--border);
    }}

    .chat-sidebar-actions {{
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}

    .chat-button, .chat-link-button {{
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: rgba(255,255,255,0.03);
      color: var(--text);
      padding: 12px 14px;
      font: inherit;
      cursor: pointer;
      text-align: left;
    }}

    .chat-button:hover, .chat-link-button:hover {{
      border-color: var(--border-strong);
      background: rgba(255,255,255,0.05);
    }}

    .chat-button.primary {{
      background: linear-gradient(180deg, rgba(16,167,255,0.24), rgba(16,167,255,0.16));
      border-color: rgba(16,167,255,0.32);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
    }}

    .chat-sidebar-section {{
      display: flex;
      flex-direction: column;
      min-height: 0;
    }}

    .chat-sidebar-label {{
      padding: 0 10px 8px;
      color: var(--text-soft);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}

    .chat-thread-list {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      overflow-y: auto;
      padding-right: 4px;
    }}

    .chat-thread-item {{
      border: 1px solid transparent;
      border-radius: 14px;
      padding: 12px;
      background: transparent;
      color: inherit;
      cursor: pointer;
      text-align: left;
    }}

    .chat-thread-item:hover {{
      background: rgba(255,255,255,0.04);
      border-color: var(--border);
    }}

    .chat-thread-item.active {{
      background: var(--accent-soft);
      border-color: rgba(16,167,255,0.2);
    }}

    .chat-thread-item strong {{
      display: block;
      font-size: 13px;
      line-height: 1.35;
      margin-bottom: 4px;
    }}

    .chat-thread-item span {{
      display: block;
      color: var(--text-soft);
      font-size: 11px;
      line-height: 1.45;
    }}

    .chat-thread-empty {{
      padding: 12px;
      border: 1px dashed var(--border);
      border-radius: 14px;
      color: var(--text-soft);
      font-size: 12px;
      line-height: 1.5;
    }}

    .chat-sidebar-foot {{
      margin-top: auto;
      padding: 14px 10px 0;
      border-top: 1px solid var(--border);
      color: var(--text-soft);
      font-size: 12px;
      line-height: 1.55;
    }}

    .chat-main {{
      min-width: 0;
      display: flex;
      flex-direction: column;
      min-height: 100vh;
    }}

    .chat-topbar {{
      position: sticky;
      top: 0;
      z-index: 10;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 28px;
      border-bottom: 1px solid var(--border);
      background: rgba(11,16,32,0.72);
      backdrop-filter: blur(20px);
    }}

    .chat-topbar-copy strong {{
      display: block;
      font-size: 15px;
      margin-bottom: 4px;
    }}

    .chat-topbar-copy span {{
      color: var(--text-soft);
      font-size: 12px;
    }}

    .chat-topbar-actions {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .chat-main-scroll {{
      flex: 1;
      overflow-y: auto;
      padding: 24px 24px 180px;
    }}

    .chat-main-inner {{
      width: min(100%, var(--content-w));
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }}

    .chat-hero {{
      padding: 10vh 8px 0;
      text-align: center;
    }}

    .chat-hero h1 {{
      margin: 0 0 10px;
      font-size: clamp(34px, 6vw, 52px);
      letter-spacing: -0.04em;
    }}

    .chat-hero p {{
      max-width: 620px;
      margin: 0 auto;
      color: var(--text-soft);
      font-size: 15px;
      line-height: 1.7;
    }}

    .chat-suggestions {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-top: 26px;
    }}

    .chat-suggestion {{
      border: 1px solid var(--border);
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.015));
      color: var(--text);
      padding: 16px;
      text-align: left;
      cursor: pointer;
      box-shadow: var(--shadow);
    }}

    .chat-suggestion:hover {{
      border-color: var(--border-strong);
      transform: translateY(-1px);
    }}

    .chat-suggestion strong {{
      display: block;
      margin-bottom: 6px;
      font-size: 14px;
    }}

    .chat-suggestion span {{
      display: block;
      color: var(--text-soft);
      font-size: 12px;
      line-height: 1.5;
    }}

    .chat-conversation {{
      display: flex;
      flex-direction: column;
      gap: 22px;
      padding-top: 12px;
    }}

    .chat-row {{
      display: flex;
      gap: 14px;
      align-items: flex-start;
    }}

    .chat-row.user {{
      justify-content: flex-end;
    }}

    .chat-avatar {{
      width: 34px;
      height: 34px;
      border-radius: 50%;
      flex-shrink: 0;
      display: grid;
      place-items: center;
      font-size: 12px;
      font-weight: 700;
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.04);
      color: var(--text);
    }}

    .chat-avatar.user {{
      background: rgba(31,111,235,0.22);
      border-color: rgba(31,111,235,0.28);
    }}

    .chat-bubble-wrap {{
      max-width: min(78ch, calc(100% - 56px));
    }}

    .chat-meta {{
      color: var(--text-soft);
      font-size: 11px;
      margin-bottom: 7px;
    }}

    .chat-row.user .chat-meta {{
      text-align: right;
    }}

    .chat-bubble {{
      padding: 15px 17px;
      border-radius: 20px;
      background: rgba(255,255,255,0.04);
      border: 1px solid var(--border);
      box-shadow: var(--shadow);
      line-height: 1.72;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 15px;
    }}

    .chat-row.user .chat-bubble {{
      background: linear-gradient(180deg, rgba(31,111,235,0.24), rgba(31,111,235,0.14));
      border-color: rgba(31,111,235,0.28);
    }}

    .chat-bubble p {{
      margin: 0 0 10px;
    }}

    .chat-bubble p:last-child {{
      margin-bottom: 0;
    }}

    .chat-bubble ul, .chat-bubble ol {{
      margin: 8px 0 10px;
      padding-left: 20px;
    }}

    .chat-bubble li {{
      margin-bottom: 4px;
    }}

    .chat-bubble code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.92em;
      padding: 0.12em 0.35em;
      border-radius: 8px;
      background: rgba(255,255,255,0.08);
    }}

    .chat-typing {{
      color: var(--text-soft);
      font-size: 13px;
    }}

    .chat-composer-shell {{
      position: fixed;
      left: calc(var(--sidebar-w) + 24px);
      right: 24px;
      bottom: 0;
      padding: 18px 0 24px;
      background: linear-gradient(180deg, rgba(11,16,32,0), rgba(11,16,32,0.86) 24%, rgba(11,16,32,0.96) 100%);
      pointer-events: none;
    }}

    .chat-composer-inner {{
      width: min(calc(100% - 24px), var(--content-w));
      margin: 0 auto;
      pointer-events: auto;
    }}

    .chat-upload-strip {{
      display: none;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 10px;
    }}

    .chat-upload-strip.visible {{
      display: flex;
    }}

    .chat-upload-pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      border-radius: 999px;
      background: rgba(255,255,255,0.06);
      border: 1px solid var(--border);
      color: var(--text-soft);
      font-size: 12px;
    }}

    .chat-upload-pill button {{
      border: none;
      background: transparent;
      color: inherit;
      cursor: pointer;
      font: inherit;
    }}

    .chat-composer {{
      border: 1px solid var(--border);
      border-radius: 26px;
      background: rgba(20, 27, 49, 0.95);
      backdrop-filter: blur(18px);
      box-shadow: var(--shadow);
      padding: 12px;
    }}

    .chat-composer textarea {{
      width: 100%;
      min-height: 28px;
      max-height: 220px;
      resize: none;
      border: none;
      outline: none;
      background: transparent;
      color: var(--text);
      font: inherit;
      font-size: 15px;
      line-height: 1.6;
      padding: 4px 2px 12px;
    }}

    .chat-composer textarea::placeholder {{
      color: var(--text-soft);
    }}

    .chat-composer-actions {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }}

    .chat-composer-left, .chat-composer-right {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .chat-icon-button {{
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.03);
      color: var(--text-soft);
      border-radius: 999px;
      padding: 8px 12px;
      cursor: pointer;
      font: inherit;
    }}

    .chat-icon-button:hover {{
      color: var(--text);
      border-color: var(--border-strong);
      background: rgba(255,255,255,0.05);
    }}

    .chat-send-button {{
      border: none;
      border-radius: 999px;
      background: var(--accent);
      color: #fff;
      padding: 10px 16px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }}

    .chat-send-button:disabled {{
      opacity: 0.45;
      cursor: default;
    }}

    .chat-footer-note {{
      margin-top: 10px;
      text-align: center;
      color: var(--text-soft);
      font-size: 11px;
    }}

    .chat-status {{
      min-height: 18px;
      color: var(--text-soft);
      font-size: 12px;
    }}

    @media (max-width: 980px) {{
      :root {{
        --sidebar-w: 100%;
      }}

      .chat-shell {{
        grid-template-columns: 1fr;
      }}

      .chat-sidebar {{
        border-right: none;
        border-bottom: 1px solid var(--border);
      }}

      .chat-suggestions {{
        grid-template-columns: 1fr;
      }}

      .chat-composer-shell {{
        left: 0;
        right: 0;
        padding: 14px 14px 20px;
      }}

      .chat-main-scroll {{
        padding: 18px 14px 210px;
      }}

      .chat-topbar {{
        padding: 16px 14px;
      }}
    }}
  </style>
</head>
<body>
  <div class="chat-shell">
    <aside class="chat-sidebar">
      <div class="chat-brand">
        <div>
          <strong>JARVIS</strong>
          <span>Chat-only surface</span>
        </div>
        <div class="chat-brand-mark">✦</div>
      </div>

      <div class="chat-sidebar-actions">
        <button class="chat-button primary" id="new-chat-button" type="button">＋ New chat</button>
        <button class="chat-link-button" id="open-command-button" type="button">Open command center</button>
      </div>

      <div class="chat-sidebar-section">
        <div class="chat-sidebar-label">Recent chats</div>
        <div class="chat-thread-list" id="thread-list"></div>
      </div>

      <div class="chat-sidebar-foot">
        Chat-only mode keeps the experience conversational. The broader command, mission, health, and navigation interfaces stay separate.
      </div>
    </aside>

    <main class="chat-main">
      <div class="chat-topbar">
        <div class="chat-topbar-copy">
          <strong id="chat-title">Chat with JARVIS</strong>
          <span id="chat-subtitle">An ongoing conversation surface for {actor_name}.</span>
        </div>
        <div class="chat-topbar-actions">
          <div class="chat-status" id="chat-status">Loading conversation…</div>
        </div>
      </div>

      <div class="chat-main-scroll" id="chat-scroll">
        <div class="chat-main-inner">
          <section class="chat-hero" id="chat-hero">
            <h1>How can JARVIS help?</h1>
            <p>Use this page when you just want to talk. It keeps the shell out of the way and stays focused on the conversation.</p>
            <div class="chat-suggestions">
              <button class="chat-suggestion" type="button" data-prompt="Help me think through the most important thing I should focus on today.">
                <strong>Clarify my focus</strong>
                <span>Sort priorities, tension, and the one thing that matters most right now.</span>
              </button>
              <button class="chat-suggestion" type="button" data-prompt="Talk me through a decision I am stuck on and help me see the tradeoffs clearly.">
                <strong>Work through a decision</strong>
                <span>Use JARVIS as a thought partner instead of opening a full workflow surface.</span>
              </button>
              <button class="chat-suggestion" type="button" data-prompt="Draft a message with me and keep it natural, direct, and warm.">
                <strong>Draft with me</strong>
                <span>Stay in a conversational loop while shaping a note, email, or text.</span>
              </button>
              <button class="chat-suggestion" type="button" data-prompt="Give me a quick sense of what is waiting for me and where I should start.">
                <strong>Get oriented</strong>
                <span>Ask for a compact read of what matters without switching into the command center.</span>
              </button>
            </div>
          </section>

          <section class="chat-conversation" id="chat-conversation" hidden></section>
        </div>
      </div>

      <div class="chat-composer-shell">
        <div class="chat-composer-inner">
          <div class="chat-upload-strip" id="upload-strip"></div>
          <div class="chat-composer">
            <textarea id="chat-input" placeholder="Message JARVIS… Use /correct when a reply misses, /teach to make it stick, or /learn to turn it into a reusable skill." rows="1"></textarea>
            <div class="chat-composer-actions">
              <div class="chat-composer-left">
                <input id="chat-file-input" type="file" multiple hidden>
                <button class="chat-icon-button" id="attach-button" type="button">Attach</button>
                <button class="chat-icon-button" id="clear-button" type="button">Clear</button>
              </div>
              <div class="chat-composer-right">
                <span class="chat-status" id="composer-status"></span>
                <button class="chat-send-button" id="send-button" type="button">Send</button>
              </div>
            </div>
          </div>
          <div class="chat-footer-note">Enter sends. Shift+Enter adds a line break.</div>
        </div>
      </div>
    </main>
  </div>

  <script>
    const state = {{
      actor: "{actor_name_js}",
      room: "office",
      conversationId: "",
      recentConversations: [],
      turns: [],
      attachments: [],
      sending: false,
    }};

    const threadListEl = document.getElementById("thread-list");
    const chatTitleEl = document.getElementById("chat-title");
    const chatSubtitleEl = document.getElementById("chat-subtitle");
    const chatStatusEl = document.getElementById("chat-status");
    const composerStatusEl = document.getElementById("composer-status");
    const heroEl = document.getElementById("chat-hero");
    const conversationEl = document.getElementById("chat-conversation");
    const chatScrollEl = document.getElementById("chat-scroll");
    const inputEl = document.getElementById("chat-input");
    const sendButtonEl = document.getElementById("send-button");
    const fileInputEl = document.getElementById("chat-file-input");
    const uploadStripEl = document.getElementById("upload-strip");

    function storageKey() {{
      return `jarvis:chat-only:conversation:${{state.actor.toLowerCase()}}`;
    }}

    function saveConversationId() {{
      try {{
        if (state.conversationId) {{
          window.localStorage.setItem(storageKey(), state.conversationId);
        }} else {{
          window.localStorage.removeItem(storageKey());
        }}
      }} catch (_err) {{
        // noop
      }}
    }}

    function loadConversationId() {{
      try {{
        return window.localStorage.getItem(storageKey()) || "";
      }} catch (_err) {{
        return "";
      }}
    }}

    function escHtml(value) {{
      return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }}

    function markdownToHtml(value) {{
      let html = escHtml(value || "");
      html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
      html = html.replace(/\\*\\*([^*]+)\\*\\*/g, "<strong>$1</strong>");
      html = html.replace(/\\*([^*]+)\\*/g, "<em>$1</em>");
      const lines = html.split(/\\n/);
      const out = [];
      let listOpen = false;
      for (const rawLine of lines) {{
        const line = rawLine.trimEnd();
        if (!line.trim()) {{
          if (listOpen) {{
            out.push("</ul>");
            listOpen = false;
          }}
          continue;
        }}
        const bullet = line.match(/^[-*]\\s+(.*)$/);
        if (bullet) {{
          if (!listOpen) {{
            out.push("<ul>");
            listOpen = true;
          }}
          out.push(`<li>${{bullet[1]}}</li>`);
          continue;
        }}
        if (listOpen) {{
          out.push("</ul>");
          listOpen = false;
        }}
        out.push(`<p>${{line}}</p>`);
      }}
      if (listOpen) out.push("</ul>");
      return out.join("") || "<p></p>";
    }}

    function relativeTime(isoString) {{
      if (!isoString) return "Recent";
      const value = new Date(isoString);
      if (Number.isNaN(value.getTime())) return "Recent";
      const diff = Date.now() - value.getTime();
      const minutes = Math.max(1, Math.round(diff / 60000));
      if (minutes < 60) return `${{minutes}}m ago`;
      const hours = Math.round(minutes / 60);
      if (hours < 24) return `${{hours}}h ago`;
      const days = Math.round(hours / 24);
      return `${{days}}d ago`;
    }}

    function autoResizeInput() {{
      inputEl.style.height = "auto";
      inputEl.style.height = Math.min(inputEl.scrollHeight, 220) + "px";
    }}

    function setStatus(text, target = "top") {{
      if (target === "composer") {{
        composerStatusEl.textContent = text || "";
      }} else {{
        chatStatusEl.textContent = text || "";
      }}
    }}

    function renderThreads() {{
      if (!state.recentConversations.length) {{
        threadListEl.innerHTML = '<div class="chat-thread-empty">Your recent conversations will appear here once you start using the chat-only surface.</div>';
        return;
      }}
      threadListEl.innerHTML = state.recentConversations.map((item) => {{
        const active = item.conversation_id === state.conversationId ? " active" : "";
        const title = escHtml(item.title || item.latest_user_text || "New conversation");
        const summary = escHtml(item.summary || item.latest_assistant_text || item.latest_user_text || "Conversation ready");
        const stamp = escHtml(relativeTime(item.last_activity_at || item.updated_at || item.created_at));
        return `
          <button class="chat-thread-item${{active}}" type="button" data-conversation-id="${{escHtml(item.conversation_id || "")}}">
            <strong>${{title}}</strong>
            <span>${{summary.slice(0, 100)}}</span>
            <span style="margin-top:7px;">${{stamp}}</span>
          </button>
        `;
      }}).join("");
      Array.from(threadListEl.querySelectorAll("[data-conversation-id]")).forEach((button) => {{
        button.addEventListener("click", () => {{
          const conversationId = button.getAttribute("data-conversation-id") || "";
          if (conversationId) {{
            openConversation(conversationId);
          }}
        }});
      }});
    }}

    function renderUploads() {{
      if (!state.attachments.length) {{
        uploadStripEl.className = "chat-upload-strip";
        uploadStripEl.innerHTML = "";
        return;
      }}
      uploadStripEl.className = "chat-upload-strip visible";
      uploadStripEl.innerHTML = state.attachments.map((item, index) => `
        <div class="chat-upload-pill">
          <span>${{escHtml(item.filename || "Attachment")}}</span>
          <button type="button" data-remove-upload="${{index}}">✕</button>
        </div>
      `).join("");
      Array.from(uploadStripEl.querySelectorAll("[data-remove-upload]")).forEach((button) => {{
        button.addEventListener("click", () => {{
          const index = Number(button.getAttribute("data-remove-upload"));
          if (!Number.isNaN(index)) {{
            state.attachments.splice(index, 1);
            renderUploads();
          }}
        }});
      }});
    }}

    function renderConversation() {{
      const hasTurns = state.turns.length > 0;
      heroEl.hidden = hasTurns;
      conversationEl.hidden = !hasTurns;
      if (!hasTurns) {{
        chatTitleEl.textContent = "Chat with JARVIS";
        chatSubtitleEl.textContent = `An ongoing conversation surface for ${{state.actor}}.`;
        conversationEl.innerHTML = "";
        return;
      }}
      const active = state.recentConversations.find((item) => item.conversation_id === state.conversationId);
      chatTitleEl.textContent = active?.title || "Current conversation";
      chatSubtitleEl.textContent = active?.summary || "Conversation continuity is active on this thread.";
      conversationEl.innerHTML = state.turns.map((turn) => {{
        const role = String(turn.role || "").toLowerCase() === "assistant" ? "assistant" : "user";
        const label = role === "assistant" ? "JARVIS" : state.actor;
        const avatarClass = role === "assistant" ? "chat-avatar" : "chat-avatar user";
        const rowClass = role === "assistant" ? "chat-row" : "chat-row user";
        const body = role === "assistant" ? markdownToHtml(turn.text || turn.content || "") : markdownToHtml(turn.text || turn.content || "");
        const timestamp = escHtml(relativeTime(turn.created_at || turn.timestamp || ""));
        return `
          <div class="${{rowClass}}">
            ${{role === "assistant" ? `<div class="${{avatarClass}}">J</div>` : ""}}
            <div class="chat-bubble-wrap">
              <div class="chat-meta">${{label}} · ${{timestamp}}</div>
              <div class="chat-bubble">${{body}}</div>
            </div>
            ${{role === "user" ? `<div class="${{avatarClass}}">Y</div>` : ""}}
          </div>
        `;
      }}).join("");
    }}

    function scrollToBottom() {{
      requestAnimationFrame(() => {{
        chatScrollEl.scrollTop = chatScrollEl.scrollHeight;
      }});
    }}

    async function loadChatState(preferredConversationId = "") {{
      const params = new URLSearchParams({{ actor: state.actor, room: state.room }});
      if (preferredConversationId) {{
        params.set("conversation_id", preferredConversationId);
      }}
      const response = await fetch(`/api/chat-state?${{params.toString()}}`, {{ cache: "no-store" }});
      if (!response.ok) {{
        throw new Error(`Chat state failed (${{response.status}})`);
      }}
      const data = await response.json();
      state.conversationId = String(data.conversation_id || preferredConversationId || "");
      state.recentConversations = Array.isArray(data.recent_conversations) ? data.recent_conversations : [];
      const active = data.active_conversation || {{}};
      state.turns = Array.isArray(active.turns) ? active.turns : [];
      saveConversationId();
      renderThreads();
      renderConversation();
      scrollToBottom();
      return data;
    }}

    async function openConversation(conversationId) {{
      setStatus("Opening conversation…");
      try {{
        state.conversationId = conversationId;
        saveConversationId();
        const response = await fetch(`/api/conversations/${{encodeURIComponent(conversationId)}}?limit=24`, {{ cache: "no-store" }});
        if (!response.ok) {{
          throw new Error(`Conversation load failed (${{response.status}})`);
        }}
        const data = await response.json();
        state.turns = Array.isArray(data.turns) ? data.turns : [];
        if (!state.recentConversations.some((item) => item.conversation_id === conversationId)) {{
          state.recentConversations.unshift({{
            conversation_id: conversationId,
            title: data.title || "Conversation",
            summary: data.summary || "",
            last_activity_at: data.last_activity_at || data.updated_at || data.created_at || "",
          }});
        }}
        renderThreads();
        renderConversation();
        setStatus("Conversation ready.");
        scrollToBottom();
      }} catch (error) {{
        setStatus(error.message || "Could not open conversation.");
      }}
    }}

    function resetComposer() {{
      inputEl.value = "";
      autoResizeInput();
      state.attachments = [];
      renderUploads();
      composerStatusEl.textContent = "";
    }}

    function startNewChat() {{
      state.conversationId = "";
      state.turns = [];
      saveConversationId();
      renderThreads();
      renderConversation();
      resetComposer();
      setStatus("Started a fresh chat.");
      inputEl.focus();
    }}

    async function uploadFiles(files) {{
      if (!files || !files.length) return;
      const formData = new FormData();
      formData.set("actor", state.actor);
      formData.set("room", state.room);
      formData.set("conversation_id", state.conversationId || "");
      Array.from(files).slice(0, 8).forEach((file) => formData.append("files", file));
      composerStatusEl.textContent = "Uploading…";
      const response = await fetch("/api/chat-uploads", {{
        method: "POST",
        body: formData,
      }});
      if (!response.ok) {{
        throw new Error(`Upload failed (${{response.status}})`);
      }}
      const data = await response.json();
      const attachments = Array.isArray(data.attachments) ? data.attachments : [];
      state.attachments.push(...attachments);
      renderUploads();
      composerStatusEl.textContent = attachments.length ? `${{attachments.length}} attachment(s) ready.` : "";
    }}

    async function sendMessage() {{
      const request = inputEl.value.trim();
      if (!request || state.sending) return;
      state.sending = true;
      sendButtonEl.disabled = true;
      setStatus("JARVIS is thinking…", "composer");

      if (!state.turns.length) {{
        heroEl.hidden = true;
        conversationEl.hidden = false;
      }}

      state.turns.push({{
        role: "user",
        text: request,
        created_at: new Date().toISOString(),
      }});
      renderConversation();
      scrollToBottom();

      const pendingIndex = state.turns.push({{
        role: "assistant",
        text: "JARVIS is thinking…",
        created_at: new Date().toISOString(),
        pending: true,
      }}) - 1;
      renderConversation();
      scrollToBottom();

      const payload = {{
        actor: state.actor,
        room: state.room,
        request,
        conversation_id: state.conversationId || "",
        source: "chat-only",
        attachments: state.attachments,
      }};

      resetComposer();

      try {{
        const response = await fetch("/api/respond", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload),
        }});
        if (!response.ok) {{
          throw new Error(`Respond failed (${{response.status}})`);
        }}
        const data = await response.json();
        state.conversationId = String(data.conversation_id || state.conversationId || "");
        saveConversationId();
        state.turns[pendingIndex] = {{
          role: "assistant",
          text: data.output_text || data.response || data.text || "No response returned.",
          created_at: new Date().toISOString(),
        }};
        await loadChatState(state.conversationId);
        setStatus(data.model || data.provider || "JARVIS replied.");
      }} catch (error) {{
        state.turns[pendingIndex] = {{
          role: "assistant",
          text: `I hit a connection problem: ${{error.message || "Unknown error"}}`,
          created_at: new Date().toISOString(),
        }};
        renderConversation();
        setStatus("Response failed.", "composer");
      }} finally {{
        state.sending = false;
        sendButtonEl.disabled = false;
        scrollToBottom();
      }}
    }}

    inputEl.addEventListener("input", autoResizeInput);
    inputEl.addEventListener("keydown", (event) => {{
      if (event.key === "Enter" && !event.shiftKey) {{
        event.preventDefault();
        sendMessage();
      }}
    }});

    document.getElementById("new-chat-button").addEventListener("click", startNewChat);
    document.getElementById("open-command-button").addEventListener("click", () => {{
      window.location.href = "/command-center";
    }});
    document.getElementById("attach-button").addEventListener("click", () => fileInputEl.click());
    document.getElementById("clear-button").addEventListener("click", () => {{
      inputEl.value = "";
      autoResizeInput();
      inputEl.focus();
    }});
    sendButtonEl.addEventListener("click", sendMessage);
    fileInputEl.addEventListener("change", async () => {{
      const files = fileInputEl.files;
      fileInputEl.value = "";
      if (!files || !files.length) return;
      try {{
        await uploadFiles(files);
      }} catch (error) {{
        setStatus(error.message || "Upload failed.", "composer");
      }}
    }});

    Array.from(document.querySelectorAll("[data-prompt]")).forEach((button) => {{
      button.addEventListener("click", () => {{
        inputEl.value = button.getAttribute("data-prompt") || "";
        autoResizeInput();
        inputEl.focus();
      }});
    }});

    (async function init() {{
      autoResizeInput();
      const storedConversationId = loadConversationId();
      try {{
        await loadChatState(storedConversationId);
        setStatus("Conversation ready.");
      }} catch (error) {{
        setStatus(error.message || "Could not load chat state.");
      }}
    }})();
  </script>
</body>
</html>
"""
