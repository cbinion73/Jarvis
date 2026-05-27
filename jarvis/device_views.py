"""JARVIS · Device Views — Mobile, Tablet, TV, Echo Show, Watch, CarPlay"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Shared SSE chat JS — injected into every view that needs full chat
# ---------------------------------------------------------------------------

_CHAT_SSE_JS = """
var _convId = '';

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function scrollBottom(el) {
  if (el) el.scrollTop = el.scrollHeight;
}

function appendMsg(thread, role, text) {
  var div = document.createElement('div');
  div.className = 'msg msg-' + role;
  div.dataset.role = role;
  if (role === 'assistant') {
    div.innerHTML = '<span class="msg-bubble" id="mb-' + Date.now() + '">' + escHtml(text) + '</span>';
  } else {
    div.innerHTML = '<span class="msg-bubble">' + escHtml(text) + '</span>';
  }
  thread.appendChild(div);
  scrollBottom(thread);
  return div;
}

function appendToolChip(thread, name) {
  var div = document.createElement('div');
  div.className = 'tool-chip';
  div.textContent = '\\uD83D\\uDD27 ' + name;
  thread.appendChild(div);
  scrollBottom(thread);
  return div;
}

function appendApproval(thread, approvalId, toolName, description) {
  var div = document.createElement('div');
  div.className = 'approval-block';
  div.id = 'appr-' + approvalId;
  div.innerHTML =
    '<div class="approval-label">\\u26A0\\uFE0F Approval needed: <strong>' + escHtml(toolName) + '</strong></div>' +
    '<div class="approval-desc">' + escHtml(description) + '</div>' +
    '<div class="approval-btns">' +
      '<button class="btn-approve" onclick="doApprove(\'' + approvalId + '\', true)">Approve</button>' +
      '<button class="btn-skip" onclick="doApprove(\'' + approvalId + '\', false)">Skip</button>' +
    '</div>';
  thread.appendChild(div);
  scrollBottom(thread);
}

function doApprove(approvalId, approved) {
  var el = document.getElementById('appr-' + approvalId);
  if (el) el.innerHTML = '<em>' + (approved ? 'Approved' : 'Skipped') + '</em>';
  fetch('/api/agent/approve', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({approval_id: approvalId, approved: approved})
  }).catch(function(e) { console.error('approve error', e); });
}

function sendChat(thread, input, sendBtn) {
  var text = input.value.trim();
  if (!text) return;
  input.value = '';
  input.disabled = true;
  if (sendBtn) sendBtn.disabled = true;

  appendMsg(thread, 'user', text);

  var messages = [{role: 'user', content: text}];
  var body = JSON.stringify({messages: messages, conversation_id: _convId});

  fetch('/api/agent/stream', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: body
  }).then(function(resp) {
    var reader = resp.body.getReader();
    var decoder = new TextDecoder();
    var buf = '';
    var aDiv = null;
    var aBubble = null;

    function pump() {
      return reader.read().then(function(result) {
        if (result.done) {
          input.disabled = false;
          if (sendBtn) sendBtn.disabled = false;
          input.focus();
          return;
        }
        buf += decoder.decode(result.value, {stream: true});
        var lines = buf.split('\\n');
        buf = lines.pop();
        lines.forEach(function(line) {
          if (!line.startsWith('data: ')) return;
          var raw = line.slice(6).trim();
          if (!raw || raw === '[DONE]') return;
          var pkt;
          try { pkt = JSON.parse(raw); } catch(e) { return; }

          if (pkt.type === 'text_delta') {
            if (!aDiv) {
              aDiv = appendMsg(thread, 'assistant', '');
              aBubble = aDiv.querySelector('.msg-bubble');
            }
            aBubble.textContent += pkt.text;
            scrollBottom(thread);
          } else if (pkt.type === 'tool_call') {
            appendToolChip(thread, pkt.name || 'tool');
            aDiv = null; aBubble = null;
          } else if (pkt.type === 'tool_result') {
            aDiv = null; aBubble = null;
          } else if (pkt.type === 'approval_needed') {
            appendApproval(thread, pkt.approval_id, pkt.tool || '', pkt.description || '');
            aDiv = null; aBubble = null;
          } else if (pkt.type === 'done') {
            if (pkt.conversation_id) _convId = pkt.conversation_id;
            aDiv = null; aBubble = null;
          }
        });
        return pump();
      });
    }
    return pump();
  }).catch(function(err) {
    appendMsg(thread, 'assistant', 'Error: ' + err.message);
    input.disabled = false;
    if (sendBtn) sendBtn.disabled = false;
  });
}
"""

# ---------------------------------------------------------------------------
# Shared chat CSS
# ---------------------------------------------------------------------------

_CHAT_CSS = """
.chat-thread {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.msg { display: flex; }
.msg-user { justify-content: flex-end; }
.msg-assistant { justify-content: flex-start; }
.msg-bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 15px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg-user .msg-bubble {
  background: var(--hue);
  color: #000;
  border-bottom-right-radius: 4px;
}
.msg-assistant .msg-bubble {
  background: var(--surface-hi);
  color: var(--text-1);
  border-bottom-left-radius: 4px;
}
.tool-chip {
  align-self: flex-start;
  font-size: 12px;
  color: var(--text-2);
  background: var(--surface-hi);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 3px 10px;
}
.approval-block {
  background: rgba(210,153,34,0.12);
  border: 1px solid var(--amber);
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 13px;
}
.approval-label { color: var(--amber); margin-bottom: 4px; }
.approval-desc { color: var(--text-2); margin-bottom: 8px; font-size: 12px; }
.approval-btns { display: flex; gap: 8px; }
.btn-approve {
  background: var(--green);
  color: #000;
  border: none;
  border-radius: 6px;
  padding: 6px 14px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}
.btn-skip {
  background: var(--surface-hi);
  color: var(--text-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 14px;
  cursor: pointer;
  font-size: 13px;
}
.chat-input-row {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid var(--border);
  background: var(--surface);
}
.chat-input-row input[type=text] {
  flex: 1;
  background: var(--surface-hi);
  color: var(--text-1);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 15px;
  outline: none;
}
.chat-input-row input[type=text]:focus {
  border-color: var(--hue);
}
.chat-send-btn {
  background: var(--hue);
  color: #000;
  border: none;
  border-radius: 10px;
  padding: 10px 18px;
  font-weight: 700;
  cursor: pointer;
  font-size: 15px;
  white-space: nowrap;
}
.chat-send-btn:disabled { opacity: 0.5; cursor: default; }
"""

# ---------------------------------------------------------------------------
# Common dark CSS vars block (all device views share dark theme)
# ---------------------------------------------------------------------------

_DARK_VARS = """
:root {
  --bg: #0d1117;
  --surface: #161b22;
  --surface-hi: #1c2128;
  --border: rgba(255,255,255,0.08);
  --text-1: #e6edf3;
  --text-2: #8b949e;
  --text-3: #484f58;
  --hue: #58a6ff;
  --green: #3fb950;
  --amber: #d29922;
  --red: #f85149;
  --font-mono: 'SF Mono', 'Fira Code', monospace;
  --font-sans: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body {
  background: var(--bg);
  color: var(--text-1);
  font-family: var(--font-sans);
  height: 100%;
  overflow-x: hidden;
}
"""

_DESKTOP_LINK_CSS = """
.desktop-link {
  position: fixed;
  top: 8px;
  right: 10px;
  font-size: 11px;
  color: var(--text-3);
  text-decoration: none;
  z-index: 9999;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 3px 7px;
}
.desktop-link:hover { color: var(--text-2); }
"""


def _desktop_link(host_js: str = "window.location.hostname") -> str:
    """Return an anchor tag that links back to desktop JARVIS."""
    return (
        '<a class="desktop-link" href="javascript:void(0)" '
        'onclick="window.location=\'http://\'+' + host_js + '+\':8787/\'">&#8862; Desktop</a>'
    )


# ===========================================================================
# 1. MOBILE VIEW
# ===========================================================================

def mobile_view() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <title>JARVIS Mobile</title>
  <style>
""" + _DARK_VARS + _CHAT_CSS + _DESKTOP_LINK_CSS + """
body { display: flex; flex-direction: column; height: 100dvh; overflow: hidden; }

/* Tab bar */
.tab-bar {
  display: flex;
  background: var(--surface);
  border-top: 1px solid var(--border);
  height: 60px;
  flex-shrink: 0;
  order: 2;
}
.tab-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  border: none;
  background: none;
  color: var(--text-3);
  font-size: 10px;
  cursor: pointer;
  min-height: 48px;
  transition: color 0.15s;
}
.tab-btn .tab-icon { font-size: 20px; line-height: 1; }
.tab-btn.active { color: var(--hue); }

/* Panels */
.panels { flex: 1; order: 1; overflow: hidden; position: relative; }
.panel {
  position: absolute; inset: 0;
  display: none;
  flex-direction: column;
  overflow: hidden;
}
.panel.active { display: flex; }

/* Header bar inside panel */
.panel-header {
  padding: 12px 16px 8px;
  font-size: 20px;
  font-weight: 700;
  color: var(--text-1);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

/* Health panel */
.readiness-big {
  text-align: center;
  padding: 24px 0 12px;
}
.readiness-score {
  font-size: 72px;
  font-weight: 800;
  line-height: 1;
}
.readiness-grade {
  font-size: 18px;
  color: var(--text-2);
  margin-top: 4px;
}
.vitals-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 12px 16px;
}
.vital-card {
  background: var(--surface-hi);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px 12px;
  text-align: center;
}
.vital-value { font-size: 28px; font-weight: 700; color: var(--hue); }
.vital-label { font-size: 12px; color: var(--text-2); margin-top: 4px; }
.anomaly-alert {
  margin: 12px 16px;
  background: rgba(248,81,73,0.12);
  border: 1px solid var(--red);
  border-radius: 10px;
  padding: 12px;
  font-size: 13px;
  color: var(--red);
}

/* Brief panel */
.brief-scroll { flex: 1; overflow-y: auto; padding: 12px 16px; }
.news-card {
  background: var(--surface-hi);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 12px;
}
.news-source {
  font-size: 11px;
  text-transform: uppercase;
  color: var(--hue);
  font-weight: 600;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}
.news-title { font-size: 15px; font-weight: 600; color: var(--text-1); margin-bottom: 6px; }
.news-desc { font-size: 13px; color: var(--text-2); line-height: 1.5; }

/* Tasks panel */
.task-scroll { flex: 1; overflow-y: auto; padding: 12px 16px; }
.task-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--surface-hi);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 12px;
  margin-bottom: 10px;
  min-height: 48px;
}
.priority-dot {
  width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
}
.p-high { background: var(--red); }
.p-medium { background: var(--amber); }
.p-low { background: var(--green); }
.task-title { font-size: 15px; color: var(--text-1); flex: 1; }
.task-domain { font-size: 11px; color: var(--text-3); }

/* Loading state */
.loading-msg { color: var(--text-3); font-size: 14px; text-align: center; padding: 32px; }
  </style>
</head>
<body>

<a class="desktop-link" href="javascript:void(0)" onclick="window.location='http://'+window.location.hostname+':8787/'">&#8862; Desktop</a>

<div class="panels">

  <!-- CHAT TAB -->
  <div class="panel active" id="panel-chat">
    <div class="panel-header">Chat</div>
    <div class="chat-thread" id="chat-thread-main"></div>
    <div class="chat-input-row">
      <input type="text" id="chat-input-main" placeholder="Ask JARVIS..." autocomplete="off">
      <button class="chat-send-btn" id="chat-send-main">Send</button>
    </div>
  </div>

  <!-- HEALTH TAB -->
  <div class="panel" id="panel-health">
    <div class="panel-header">Health</div>
    <div id="health-content" style="flex:1;overflow-y:auto;">
      <div class="loading-msg">Loading health data...</div>
    </div>
  </div>

  <!-- BRIEF TAB -->
  <div class="panel" id="panel-brief">
    <div class="panel-header">Morning Brief</div>
    <div class="brief-scroll" id="brief-content">
      <div class="loading-msg">Loading briefing...</div>
    </div>
  </div>

  <!-- TASKS TAB -->
  <div class="panel" id="panel-tasks">
    <div class="panel-header">Tasks</div>
    <div class="task-scroll" id="tasks-content">
      <div class="loading-msg">Loading tasks...</div>
    </div>
  </div>

  <!-- INTEL TAB -->
  <div class="panel" id="panel-intel">
    <div class="panel-header">Intel Chat</div>
    <div class="chat-thread" id="chat-thread-intel"></div>
    <div class="chat-input-row">
      <input type="text" id="chat-input-intel" placeholder="Ask an intel question..." autocomplete="off">
      <button class="chat-send-btn" id="chat-send-intel">Send</button>
    </div>
  </div>

</div>

<!-- Tab bar -->
<div class="tab-bar">
  <button class="tab-btn active" onclick="switchTab('chat',this)">
    <span class="tab-icon">&#128172;</span>Chat
  </button>
  <button class="tab-btn" onclick="switchTab('health',this)">
    <span class="tab-icon">&#128154;</span>Health
  </button>
  <button class="tab-btn" onclick="switchTab('brief',this)">
    <span class="tab-icon">&#128240;</span>Brief
  </button>
  <button class="tab-btn" onclick="switchTab('tasks',this)">
    <span class="tab-icon">&#9989;</span>Tasks
  </button>
  <button class="tab-btn" onclick="switchTab('intel',this)">
    <span class="tab-icon">&#128202;</span>Intel
  </button>
</div>

<script>
""" + _CHAT_SSE_JS + """

var _intelConvId = '';

// Tab switching
function switchTab(name, btn) {
  document.querySelectorAll('.panel').forEach(function(p) { p.classList.remove('active'); });
  document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
  document.getElementById('panel-' + name).classList.add('active');
  btn.classList.add('active');
  if (name === 'health' && !window._healthLoaded) loadHealth();
  if (name === 'brief' && !window._briefLoaded) loadBrief();
  if (name === 'tasks' && !window._tasksLoaded) loadTasks();
}

// Chat — main
(function() {
  var thread = document.getElementById('chat-thread-main');
  var input  = document.getElementById('chat-input-main');
  var btn    = document.getElementById('chat-send-main');
  btn.addEventListener('click', function() { sendChat(thread, input, btn); });
  input.addEventListener('keydown', function(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(thread, input, btn); } });
})();

// Chat — intel (separate conversation id)
(function() {
  var thread = document.getElementById('chat-thread-intel');
  var input  = document.getElementById('chat-input-intel');
  var btn    = document.getElementById('chat-send-intel');
  var localConvId = '';

  function sendIntel() {
    var text = input.value.trim();
    if (!text) return;
    input.value = '';
    input.disabled = true;
    btn.disabled = true;
    appendMsg(thread, 'user', text);
    fetch('/api/agent/stream', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({messages: [{role:'user',content:text}], conversation_id: localConvId})
    }).then(function(resp) {
      var reader = resp.body.getReader();
      var decoder = new TextDecoder();
      var buf = '';
      var aDiv = null; var aBubble = null;
      function pump() {
        return reader.read().then(function(res) {
          if (res.done) { input.disabled=false; btn.disabled=false; input.focus(); return; }
          buf += decoder.decode(res.value, {stream:true});
          var lines = buf.split('\\n'); buf = lines.pop();
          lines.forEach(function(line) {
            if (!line.startsWith('data: ')) return;
            var raw = line.slice(6).trim(); if (!raw||raw==='[DONE]') return;
            var pkt; try{pkt=JSON.parse(raw);}catch(e){return;}
            if (pkt.type==='text_delta') {
              if (!aDiv) { aDiv=appendMsg(thread,'assistant',''); aBubble=aDiv.querySelector('.msg-bubble'); }
              aBubble.textContent += pkt.text; scrollBottom(thread);
            } else if (pkt.type==='done') { if(pkt.conversation_id) localConvId=pkt.conversation_id; aDiv=null; aBubble=null; }
          });
          return pump();
        });
      }
      return pump();
    }).catch(function(err) { appendMsg(thread,'assistant','Error: '+err.message); input.disabled=false; btn.disabled=false; });
  }

  btn.addEventListener('click', sendIntel);
  input.addEventListener('keydown', function(e) { if (e.key==='Enter'&&!e.shiftKey) { e.preventDefault(); sendIntel(); } });
})();

// Health
function loadHealth() {
  window._healthLoaded = true;
  fetch('/api/health/summary').then(function(r){return r.json();}).then(function(d) {
    var el = document.getElementById('health-content');
    var scoreColor = d.readiness && d.readiness.score >= 70 ? 'var(--green)' : d.readiness && d.readiness.score >= 40 ? 'var(--amber)' : 'var(--red)';
    var score = d.readiness ? d.readiness.score : '--';
    var grade = d.readiness ? d.readiness.grade : '';
    var m = d.metrics || {};
    var anomalies = d.anomalies || [];
    var aHtml = '';
    if (anomalies.length) {
      aHtml = '<div class="anomaly-alert"><strong>&#9888; Anomalies:</strong><br>' +
        anomalies.map(function(a){return escHtml(a.metric)+': '+escHtml(a.note);}).join('<br>') + '</div>';
    }
    el.innerHTML =
      '<div class="readiness-big">' +
        '<div class="readiness-score" style="color:'+scoreColor+'">'+escHtml(String(score))+'</div>' +
        '<div class="readiness-grade">Readiness &middot; Grade ' + escHtml(grade) + '</div>' +
      '</div>' +
      '<div class="vitals-grid">' +
        '<div class="vital-card"><div class="vital-value">'+(m.resting_hr||'--')+'</div><div class="vital-label">Resting HR</div></div>' +
        '<div class="vital-card"><div class="vital-value">'+(m.hrv||'--')+'</div><div class="vital-label">HRV ms</div></div>' +
        '<div class="vital-card"><div class="vital-value">'+(m.steps ? Number(m.steps).toLocaleString() : '--')+'</div><div class="vital-label">Steps</div></div>' +
        '<div class="vital-card"><div class="vital-value">'+(m.blood_oxygen||'--')+'%</div><div class="vital-label">SpO2</div></div>' +
      '</div>' + aHtml;
  }).catch(function() {
    document.getElementById('health-content').innerHTML = '<div class="loading-msg">Could not load health data.</div>';
  });
}

// Brief
function briefingToHtml(text) {
  if (!text) return '<div class="loading-msg">No briefing available.</div>';
  var sections = text.split(/\\n---+\\n/);
  return sections.map(function(sec) {
    var sourceMatch = sec.match(/\\[([^\\]]+)\\]\\s*(.+?)\\n/);
    var briefMatch = sec.match(/Brief:\\s*(.+)/s);
    var source = sourceMatch ? sourceMatch[1] : '';
    var title = sourceMatch ? sourceMatch[2].trim() : sec.split('\\n')[0].replace(/^#+\\s*/,'').trim();
    var desc = briefMatch ? briefMatch[1].trim() : '';
    if (!title) return '';
    return '<div class="news-card">' +
      (source ? '<div class="news-source">'+escHtml(source)+'</div>' : '') +
      '<div class="news-title">'+escHtml(title)+'</div>' +
      (desc ? '<div class="news-desc">'+escHtml(desc)+'</div>' : '') +
    '</div>';
  }).join('');
}

function loadBrief() {
  window._briefLoaded = true;
  fetch('/api/briefing').then(function(r){return r.json();}).then(function(d) {
    document.getElementById('brief-content').innerHTML = briefingToHtml(d.briefing || '');
  }).catch(function() {
    document.getElementById('brief-content').innerHTML = '<div class="loading-msg">Could not load briefing.</div>';
  });
}

// Tasks
function loadTasks() {
  window._tasksLoaded = true;
  fetch('/api/tasks').then(function(r){return r.json();}).then(function(d) {
    var tasks = d.tasks || [];
    if (!tasks.length) {
      document.getElementById('tasks-content').innerHTML = '<div class="loading-msg">No tasks found.</div>';
      return;
    }
    var html = tasks.map(function(t) {
      var pc = t.priority === 'high' ? 'p-high' : t.priority === 'medium' ? 'p-medium' : 'p-low';
      return '<div class="task-item">' +
        '<span class="priority-dot '+pc+'"></span>' +
        '<span class="task-title">'+escHtml(t.title||'')+'</span>' +
        (t.domain ? '<span class="task-domain">'+escHtml(t.domain)+'</span>' : '') +
      '</div>';
    }).join('');
    document.getElementById('tasks-content').innerHTML = html;
  }).catch(function() {
    document.getElementById('tasks-content').innerHTML = '<div class="loading-msg">Could not load tasks.</div>';
  });
}
</script>
</body>
</html>
"""


# ===========================================================================
# 2. TABLET VIEW
# ===========================================================================

def tablet_view() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <title>JARVIS Tablet</title>
  <style>
""" + _DARK_VARS + _CHAT_CSS + _DESKTOP_LINK_CSS + """
body { display: flex; height: 100dvh; overflow: hidden; }

/* Sidebar */
.sidebar {
  width: 200px;
  min-width: 200px;
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  transition: width 0.25s, min-width 0.25s;
  overflow: hidden;
}
.sidebar.collapsed { width: 56px; min-width: 56px; }
.sidebar-logo {
  padding: 16px 14px 12px;
  font-size: 16px;
  font-weight: 800;
  color: var(--hue);
  letter-spacing: 0.04em;
  display: flex;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
}
.sidebar-logo .logo-icon { font-size: 22px; flex-shrink: 0; }
.sidebar-toggle {
  background: none;
  border: none;
  color: var(--text-3);
  cursor: pointer;
  padding: 8px 14px;
  font-size: 18px;
  text-align: left;
  width: 100%;
}
.nav-items { flex: 1; overflow-y: auto; padding: 8px 0; }
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  cursor: pointer;
  color: var(--text-2);
  font-size: 14px;
  font-weight: 500;
  border-left: 3px solid transparent;
  transition: all 0.15s;
  min-height: 52px;
  white-space: nowrap;
}
.nav-item:hover { background: var(--surface-hi); color: var(--text-1); }
.nav-item.active { color: var(--hue); border-left-color: var(--hue); background: rgba(88,166,255,0.06); }
.nav-icon { font-size: 20px; flex-shrink: 0; }
.nav-label { overflow: hidden; }
.sidebar.collapsed .nav-label { display: none; }
.sidebar.collapsed .sidebar-logo span:last-child { display: none; }

/* Main area */
.main-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; position: relative; }
.main-header {
  padding: 14px 20px;
  font-size: 22px;
  font-weight: 700;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  color: var(--text-1);
}

/* Content panels */
.content-panel { display: none; flex: 1; overflow-y: auto; padding: 16px 20px; }
.content-panel.active { display: block; }

/* 2-column grid for overview */
.card-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
.card {
  background: var(--surface-hi);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px;
}
.card-title {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--hue);
  font-weight: 600;
  margin-bottom: 12px;
}
.card-body { color: var(--text-1); font-size: 14px; line-height: 1.6; }

/* Health vitals */
.vitals-grid-t {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.vital-card-t {
  background: var(--surface-hi);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px 10px;
  text-align: center;
}
.vital-value-t { font-size: 32px; font-weight: 700; color: var(--hue); }
.vital-label-t { font-size: 12px; color: var(--text-2); margin-top: 4px; }

/* Tasks list */
.task-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 12px;
  border-bottom: 1px solid var(--border);
  min-height: 56px;
}
.priority-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.p-high { background: var(--red); }
.p-medium { background: var(--amber); }
.p-low { background: var(--green); }
.task-title-t { flex: 1; font-size: 15px; color: var(--text-1); }
.task-domain-t { font-size: 12px; color: var(--text-3); }

/* News card */
.news-card-t {
  background: var(--surface-hi);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
}
.news-source-t { font-size: 11px; text-transform: uppercase; color: var(--hue); font-weight: 600; letter-spacing: 0.05em; margin-bottom: 4px; }
.news-title-t { font-size: 16px; font-weight: 600; color: var(--text-1); margin-bottom: 6px; }
.news-desc-t { font-size: 13px; color: var(--text-2); line-height: 1.5; }

/* Chat panel */
.chat-panel-overlay {
  position: absolute;
  top: 0; right: 0; bottom: 0;
  width: 400px;
  background: var(--surface);
  border-left: 1px solid var(--border);
  display: none;
  flex-direction: column;
  z-index: 100;
  box-shadow: -4px 0 24px rgba(0,0,0,0.4);
}
.chat-panel-overlay.open { display: flex; }
.chat-panel-header {
  padding: 14px 16px;
  font-weight: 700;
  font-size: 16px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.chat-close-btn {
  background: none;
  border: none;
  color: var(--text-3);
  font-size: 20px;
  cursor: pointer;
  padding: 4px 8px;
}
.chat-thread { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px; }

/* Readiness big */
.readiness-big-t { text-align: center; padding: 20px 0 12px; }
.readiness-score-t { font-size: 64px; font-weight: 800; line-height: 1; }
.readiness-grade-t { font-size: 16px; color: var(--text-2); margin-top: 4px; }
.anomaly-alert { margin: 0 0 16px; background: rgba(248,81,73,0.12); border: 1px solid var(--red); border-radius: 10px; padding: 12px; font-size: 13px; color: var(--red); }

.loading-msg { color: var(--text-3); font-size: 14px; text-align: center; padding: 40px; }
  </style>
</head>
<body>

<a class="desktop-link" href="javascript:void(0)" onclick="window.location='http://'+window.location.hostname+':8787/'">&#8862; Desktop</a>

<!-- Sidebar -->
<div class="sidebar" id="sidebar">
  <div class="sidebar-logo">
    <span class="logo-icon">&#9881;</span>
    <span>JARVIS</span>
  </div>
  <button class="sidebar-toggle" onclick="toggleSidebar()">&#9776;</button>
  <div class="nav-items">
    <div class="nav-item active" onclick="showView('overview',this)"><span class="nav-icon">&#128196;</span><span class="nav-label">Overview</span></div>
    <div class="nav-item" onclick="showView('chat',this)"><span class="nav-icon">&#128172;</span><span class="nav-label">Chat</span></div>
    <div class="nav-item" onclick="showView('health',this)"><span class="nav-icon">&#128154;</span><span class="nav-label">Health</span></div>
    <div class="nav-item" onclick="showView('publishing',this)"><span class="nav-icon">&#128221;</span><span class="nav-label">Publishing</span></div>
    <div class="nav-item" onclick="showView('chronicle',this)"><span class="nav-icon">&#128218;</span><span class="nav-label">Chronicle</span></div>
    <div class="nav-item" onclick="showView('intel',this)"><span class="nav-icon">&#128202;</span><span class="nav-label">Intel</span></div>
  </div>
</div>

<!-- Main area -->
<div class="main-area">
  <div class="main-header" id="main-header">Overview</div>

  <!-- Overview -->
  <div class="content-panel active" id="view-overview">
    <div class="card-grid-2" id="overview-grid">
      <div class="card"><div class="card-title">Health</div><div class="card-body" id="ov-health">Loading...</div></div>
      <div class="card"><div class="card-title">Tasks</div><div class="card-body" id="ov-tasks">Loading...</div></div>
      <div class="card"><div class="card-title">Calendar</div><div class="card-body" id="ov-calendar">Loading...</div></div>
      <div class="card"><div class="card-title">Weather</div><div class="card-body" id="ov-weather">Loading...</div></div>
    </div>
  </div>

  <!-- Chat (opens overlay panel) -->
  <div class="content-panel" id="view-chat">
    <div style="color:var(--text-2);font-size:15px;padding:20px 0;">Chat panel is open on the right &rarr;</div>
  </div>

  <!-- Health -->
  <div class="content-panel" id="view-health">
    <div id="health-detail-content"><div class="loading-msg">Loading health data...</div></div>
  </div>

  <!-- Publishing -->
  <div class="content-panel" id="view-publishing">
    <div class="loading-msg" id="publishing-content">Publishing workspace — open the full desktop view for authoring tools.</div>
  </div>

  <!-- Chronicle -->
  <div class="content-panel" id="view-chronicle">
    <div class="loading-msg" id="chronicle-content">Chronicle — narrative logs available in the desktop view.</div>
  </div>

  <!-- Intel -->
  <div class="content-panel" id="view-intel">
    <div style="height:100%;display:flex;flex-direction:column;">
      <div class="chat-thread" id="intel-thread" style="flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px;"></div>
      <div class="chat-input-row">
        <input type="text" id="intel-input" placeholder="Ask an intel question..." autocomplete="off">
        <button class="chat-send-btn" id="intel-send">Send</button>
      </div>
    </div>
  </div>

  <!-- Chat overlay panel -->
  <div class="chat-panel-overlay" id="chat-overlay">
    <div class="chat-panel-header">
      <span>&#128172; Chat</span>
      <button class="chat-close-btn" onclick="closeChat()">&#x2715;</button>
    </div>
    <div class="chat-thread" id="chat-thread-tablet"></div>
    <div class="chat-input-row">
      <input type="text" id="chat-input-tablet" placeholder="Ask JARVIS..." autocomplete="off">
      <button class="chat-send-btn" id="chat-send-tablet">Send</button>
    </div>
  </div>
</div>

<script>
""" + _CHAT_SSE_JS + """

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('collapsed');
}

function showView(name, el) {
  document.querySelectorAll('.content-panel').forEach(function(p) { p.classList.remove('active'); });
  document.querySelectorAll('.nav-item').forEach(function(n) { n.classList.remove('active'); });
  document.getElementById('view-' + name).classList.add('active');
  if (el) el.classList.add('active');
  var titles = {overview:'Overview',chat:'Chat',health:'Health',publishing:'Publishing',chronicle:'Chronicle',intel:'Intel'};
  document.getElementById('main-header').textContent = titles[name] || name;

  if (name === 'chat') {
    document.getElementById('chat-overlay').classList.add('open');
    setTimeout(function() { document.getElementById('chat-input-tablet').focus(); }, 100);
  } else {
    document.getElementById('chat-overlay').classList.remove('open');
  }

  if (name === 'health' && !window._healthDetailLoaded) loadHealthDetail();
  if (name === 'overview' && !window._overviewLoaded) loadOverview();
}

function closeChat() {
  document.getElementById('chat-overlay').classList.remove('open');
}

// Overview data
function loadOverview() {
  window._overviewLoaded = true;
  fetch('/api/health/summary').then(function(r){return r.json();}).then(function(d) {
    var sc = d.readiness ? d.readiness.score : '--';
    var gr = d.readiness ? d.readiness.grade : '';
    document.getElementById('ov-health').innerHTML =
      '<span style="font-size:36px;font-weight:800;color:var(--green)">'+escHtml(String(sc))+'</span>' +
      '<span style="color:var(--text-2);font-size:14px;"> / Grade '+escHtml(gr)+'</span>';
  }).catch(function(){document.getElementById('ov-health').textContent='Unavailable';});

  fetch('/api/tasks').then(function(r){return r.json();}).then(function(d) {
    var tasks = (d.tasks||[]).slice(0,4);
    document.getElementById('ov-tasks').innerHTML = tasks.map(function(t) {
      return '<div style="padding:4px 0;font-size:14px;color:var(--text-1)">&#8226; '+escHtml(t.title||'')+'</div>';
    }).join('') || 'No tasks';
  }).catch(function(){document.getElementById('ov-tasks').textContent='Unavailable';});

  fetch('/api/calendar/today').then(function(r){return r.json();}).then(function(d) {
    var events = (d.events||[]).slice(0,3);
    document.getElementById('ov-calendar').innerHTML = events.map(function(e) {
      return '<div style="padding:4px 0;font-size:14px;color:var(--text-1)">'+escHtml(e.start||'')+'&nbsp;'+escHtml(e.title||'')+'</div>';
    }).join('') || 'No events today';
  }).catch(function(){document.getElementById('ov-calendar').textContent='Unavailable';});

  fetch('/api/weather').then(function(r){return r.json();}).then(function(d) {
    var c = d.current || {};
    document.getElementById('ov-weather').innerHTML =
      '<div style="font-size:28px;font-weight:700;color:var(--text-1)">'+(c.icon||'')+'&nbsp;'+escHtml(String(c.temp||'--'))+'&deg;</div>' +
      '<div style="font-size:13px;color:var(--text-2)">'+escHtml(c.condition||'')+'</div>' +
      '<div style="font-size:12px;color:var(--text-3)">Feels like '+escHtml(String(c.feels_like||'--'))+'&deg;</div>';
  }).catch(function(){document.getElementById('ov-weather').textContent='Unavailable';});
}

// Health detail
function loadHealthDetail() {
  window._healthDetailLoaded = true;
  fetch('/api/health/summary').then(function(r){return r.json();}).then(function(d) {
    var el = document.getElementById('health-detail-content');
    var scoreColor = d.readiness && d.readiness.score >= 70 ? 'var(--green)' : d.readiness && d.readiness.score >= 40 ? 'var(--amber)' : 'var(--red)';
    var score = d.readiness ? d.readiness.score : '--';
    var grade = d.readiness ? d.readiness.grade : '';
    var m = d.metrics || {};
    var anomalies = d.anomalies || [];
    var aHtml = '';
    if (anomalies.length) {
      aHtml = '<div class="anomaly-alert"><strong>&#9888; Anomalies:</strong><br>' +
        anomalies.map(function(a){return escHtml(a.metric)+': '+escHtml(a.note);}).join('<br>') + '</div>';
    }
    el.innerHTML =
      '<div class="readiness-big-t">' +
        '<div class="readiness-score-t" style="color:'+scoreColor+'">'+escHtml(String(score))+'</div>' +
        '<div class="readiness-grade-t">Readiness &middot; Grade '+escHtml(grade)+'</div>' +
      '</div>' + aHtml +
      '<div class="vitals-grid-t">' +
        '<div class="vital-card-t"><div class="vital-value-t">'+(m.resting_hr||'--')+'</div><div class="vital-label-t">Resting HR</div></div>' +
        '<div class="vital-card-t"><div class="vital-value-t">'+(m.hrv||'--')+'</div><div class="vital-label-t">HRV ms</div></div>' +
        '<div class="vital-card-t"><div class="vital-value-t">'+(m.steps?Number(m.steps).toLocaleString():'--')+'</div><div class="vital-label-t">Steps</div></div>' +
        '<div class="vital-card-t"><div class="vital-value-t">'+(m.blood_oxygen||'--')+'%</div><div class="vital-label-t">SpO2</div></div>' +
      '</div>';
  }).catch(function() {
    document.getElementById('health-detail-content').innerHTML = '<div class="loading-msg">Could not load health data.</div>';
  });
}

// Chat overlay
(function() {
  var thread = document.getElementById('chat-thread-tablet');
  var input  = document.getElementById('chat-input-tablet');
  var btn    = document.getElementById('chat-send-tablet');
  btn.addEventListener('click', function() { sendChat(thread, input, btn); });
  input.addEventListener('keydown', function(e) { if (e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendChat(thread,input,btn);} });
})();

// Intel chat
(function() {
  var thread = document.getElementById('intel-thread');
  var input  = document.getElementById('intel-input');
  var btn    = document.getElementById('intel-send');
  var localConvId = '';
  function sendIntel() {
    var text = input.value.trim(); if (!text) return;
    input.value=''; input.disabled=true; btn.disabled=true;
    appendMsg(thread,'user',text);
    fetch('/api/agent/stream',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({messages:[{role:'user',content:text}],conversation_id:localConvId})
    }).then(function(resp){
      var reader=resp.body.getReader(); var decoder=new TextDecoder(); var buf='';
      var aDiv=null; var aBubble=null;
      function pump(){return reader.read().then(function(res){
        if(res.done){input.disabled=false;btn.disabled=false;input.focus();return;}
        buf+=decoder.decode(res.value,{stream:true});
        var lines=buf.split('\\n');buf=lines.pop();
        lines.forEach(function(line){
          if(!line.startsWith('data: '))return;
          var raw=line.slice(6).trim();if(!raw||raw==='[DONE]')return;
          var pkt;try{pkt=JSON.parse(raw);}catch(e){return;}
          if(pkt.type==='text_delta'){if(!aDiv){aDiv=appendMsg(thread,'assistant','');aBubble=aDiv.querySelector('.msg-bubble');}aBubble.textContent+=pkt.text;scrollBottom(thread);}
          else if(pkt.type==='done'){if(pkt.conversation_id)localConvId=pkt.conversation_id;aDiv=null;aBubble=null;}
          else if(pkt.type==='tool_call'){appendToolChip(thread,pkt.name||'tool');aDiv=null;aBubble=null;}
          else if(pkt.type==='approval_needed'){appendApproval(thread,pkt.approval_id,pkt.tool||'',pkt.description||'');aDiv=null;aBubble=null;}
        });
        return pump();
      });}
      return pump();
    }).catch(function(err){appendMsg(thread,'assistant','Error: '+err.message);input.disabled=false;btn.disabled=false;});
  }
  btn.addEventListener('click',sendIntel);
  input.addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendIntel();}});
})();

// Initial load
loadOverview();
</script>
</body>
</html>
"""


# ===========================================================================
# 3. TV VIEW
# ===========================================================================

def tv_view() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS TV</title>
  <style>
:root {
  --bg: #000000;
  --surface: #111111;
  --surface-hi: #1a1a1a;
  --border: rgba(255,255,255,0.10);
  --text-1: #f0f0f0;
  --text-2: #aaaaaa;
  --text-3: #555555;
  --hue: #58a6ff;
  --green: #3fb950;
  --amber: #d29922;
  --red: #f85149;
  --font-mono: 'SF Mono', 'Fira Code', monospace;
  --font-sans: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body {
  background: var(--bg);
  color: var(--text-1);
  font-family: var(--font-sans);
  height: 100%;
  overflow: hidden;
}

/* Top nav */
.tv-nav {
  display: flex;
  gap: 0;
  background: var(--surface);
  border-bottom: 2px solid var(--border);
  padding: 0 40px;
  height: 64px;
  align-items: center;
}
.tv-nav-item {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--text-2);
  padding: 0 24px;
  height: 64px;
  display: flex;
  align-items: center;
  cursor: pointer;
  border-bottom: 3px solid transparent;
  transition: all 0.15s;
  user-select: none;
}
.tv-nav-item:hover, .tv-nav-item:focus { color: var(--text-1); outline: none; }
.tv-nav-item.active { color: var(--hue); border-bottom-color: var(--hue); }

/* Panels */
.tv-panel { display: none; height: calc(100vh - 64px); overflow: hidden; }
.tv-panel.active { display: flex; flex-direction: column; }

/* Brief panel */
.tv-brief-grid {
  flex: 1;
  overflow-y: auto;
  padding: 32px 48px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  align-content: start;
}
.tv-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px 28px;
  outline: none;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.tv-card:focus, .tv-card.focused {
  border-color: var(--hue);
  background: var(--surface-hi);
  box-shadow: 0 0 0 3px rgba(88,166,255,0.25);
}
.tv-card-source { font-size: 14px; text-transform: uppercase; color: var(--hue); font-weight: 700; letter-spacing: 0.08em; margin-bottom: 8px; }
.tv-card-title { font-size: 22px; font-weight: 700; color: var(--text-1); margin-bottom: 10px; line-height: 1.3; }
.tv-card-desc { font-size: 18px; color: var(--text-2); line-height: 1.5; }

/* Chronicle panel */
.tv-chronicle-content {
  flex: 1; overflow-y: auto; padding: 32px 48px;
  font-size: 20px; line-height: 1.7; color: var(--text-1);
}
.tv-chronicle-content h2 { font-size: 28px; margin-bottom: 16px; color: var(--hue); }
.tv-chronicle-content p { margin-bottom: 16px; }

/* Calendar panel */
.tv-calendar-list { flex: 1; overflow-y: auto; padding: 32px 48px; }
.tv-event {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 22px 28px;
  margin-bottom: 16px;
  display: flex;
  gap: 28px;
  align-items: center;
  cursor: pointer;
  outline: none;
  transition: border-color 0.15s;
}
.tv-event:focus, .tv-event.focused { border-color: var(--hue); box-shadow: 0 0 0 3px rgba(88,166,255,0.25); }
.tv-event-time { font-size: 24px; font-weight: 700; color: var(--hue); min-width: 120px; }
.tv-event-title { font-size: 22px; font-weight: 600; color: var(--text-1); }
.tv-event-loc { font-size: 16px; color: var(--text-2); margin-top: 4px; }

/* Chat panel — full overlay triggered by nav */
.tv-chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0;
}
.tv-chat-thread {
  flex: 1;
  overflow-y: auto;
  padding: 28px 80px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.tv-msg { display: flex; }
.tv-msg-user { justify-content: flex-end; }
.tv-msg-assistant { justify-content: flex-start; }
.tv-msg-bubble {
  max-width: 70%;
  padding: 16px 22px;
  border-radius: 20px;
  font-size: 20px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.tv-msg-user .tv-msg-bubble { background: var(--hue); color: #000; border-bottom-right-radius: 5px; }
.tv-msg-assistant .tv-msg-bubble { background: var(--surface-hi); color: var(--text-1); border-bottom-left-radius: 5px; }
.tv-tool-chip {
  align-self: flex-start;
  font-size: 14px;
  color: var(--text-2);
  background: var(--surface-hi);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 5px 14px;
}
.tv-input-area {
  padding: 20px 80px 28px;
  display: flex;
  gap: 12px;
  border-top: 1px solid var(--border);
}
.tv-input-area input[type=text] {
  flex: 1;
  background: var(--surface-hi);
  color: var(--text-1);
  border: 2px solid var(--border);
  border-radius: 14px;
  padding: 16px 22px;
  font-size: 22px;
  outline: none;
  font-family: var(--font-sans);
}
.tv-input-area input[type=text]:focus { border-color: var(--hue); }
.tv-send-btn {
  background: var(--hue);
  color: #000;
  border: none;
  border-radius: 14px;
  padding: 16px 32px;
  font-size: 20px;
  font-weight: 800;
  cursor: pointer;
}
.tv-send-btn:disabled { opacity: 0.4; cursor: default; }

.loading-msg { color: var(--text-3); font-size: 20px; text-align: center; padding: 60px; }

.desktop-link {
  position: fixed; top: 10px; right: 14px;
  font-size: 13px; color: var(--text-3); text-decoration: none;
  z-index: 9999; background: var(--surface); border: 1px solid var(--border);
  border-radius: 6px; padding: 4px 9px;
}
  </style>
</head>
<body>

<a class="desktop-link" href="javascript:void(0)" onclick="window.location='http://'+window.location.hostname+':8787/'">&#8862; Desktop</a>

<div class="tv-nav" id="tv-nav">
  <div class="tv-nav-item active" tabindex="0" data-panel="brief" onclick="tvShowPanel('brief',0)">BRIEF</div>
  <div class="tv-nav-item" tabindex="0" data-panel="chronicle" onclick="tvShowPanel('chronicle',1)">CHRONICLE</div>
  <div class="tv-nav-item" tabindex="0" data-panel="calendar" onclick="tvShowPanel('calendar',2)">CALENDAR</div>
  <div class="tv-nav-item" tabindex="0" data-panel="chat" onclick="tvShowPanel('chat',3)">CHAT</div>
</div>

<!-- BRIEF -->
<div class="tv-panel active" id="tv-panel-brief">
  <div class="tv-brief-grid" id="brief-grid">
    <div class="loading-msg">Loading briefing...</div>
  </div>
</div>

<!-- CHRONICLE -->
<div class="tv-panel" id="tv-panel-chronicle">
  <div class="tv-chronicle-content" id="chronicle-content">
    <div class="loading-msg">Chronicle data loads here.</div>
  </div>
</div>

<!-- CALENDAR -->
<div class="tv-panel" id="tv-panel-calendar">
  <div class="tv-calendar-list" id="calendar-list">
    <div class="loading-msg">Loading calendar...</div>
  </div>
</div>

<!-- CHAT -->
<div class="tv-panel" id="tv-panel-chat">
  <div class="tv-chat-panel">
    <div class="tv-chat-thread" id="tv-chat-thread"></div>
    <div class="tv-input-area">
      <input type="text" id="tv-chat-input" placeholder="Ask JARVIS..." autocomplete="off">
      <button class="tv-send-btn" id="tv-send-btn">Send</button>
    </div>
  </div>
</div>

<script>
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function scrollBottom(el) { if (el) el.scrollTop = el.scrollHeight; }

var _tvConvId = '';
var _tvNavIdx = 0;
var _tvPanels = ['brief','chronicle','calendar','chat'];

function tvShowPanel(name, idx) {
  _tvNavIdx = idx;
  document.querySelectorAll('.tv-panel').forEach(function(p){p.classList.remove('active');});
  document.querySelectorAll('.tv-nav-item').forEach(function(n){n.classList.remove('active');});
  document.getElementById('tv-panel-' + name).classList.add('active');
  var items = document.querySelectorAll('.tv-nav-item');
  if (items[idx]) items[idx].classList.add('active');
  if (name === 'brief' && !window._tvBriefLoaded) tvLoadBrief();
  if (name === 'calendar' && !window._tvCalLoaded) tvLoadCalendar();
  if (name === 'chat') setTimeout(function(){document.getElementById('tv-chat-input').focus();}, 100);
}

// D-pad navigation
document.addEventListener('keydown', function(e) {
  var active = document.activeElement;
  if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
    if (active && active.closest('.tv-nav')) {
      var dir = e.key === 'ArrowRight' ? 1 : -1;
      var next = _tvNavIdx + dir;
      if (next >= 0 && next < _tvPanels.length) tvShowPanel(_tvPanels[next], next);
      var items = document.querySelectorAll('.tv-nav-item');
      if (items[Math.min(Math.max(_tvNavIdx,0),items.length-1)]) items[Math.min(Math.max(_tvNavIdx,0),items.length-1)].focus();
      e.preventDefault();
    }
  }
  if (e.key === 'Escape') {
    document.querySelectorAll('.tv-nav-item')[_tvNavIdx].focus();
  }
});

// Brief
function briefingToCards(text) {
  if (!text) return '<div class="loading-msg">No briefing available.</div>';
  var sections = text.split(/\\n---+\\n/);
  return sections.map(function(sec) {
    var sourceMatch = sec.match(/\\[([^\\]]+)\\]\\s*(.+?)\\n/);
    var briefMatch = sec.match(/Brief:\\s*(.+)/s);
    var source = sourceMatch ? sourceMatch[1] : '';
    var title = sourceMatch ? sourceMatch[2].trim() : sec.split('\\n')[0].replace(/^#+\\s*/,'').trim();
    var desc = briefMatch ? briefMatch[1].trim() : '';
    if (!title) return '';
    return '<div class="tv-card" tabindex="0">' +
      (source ? '<div class="tv-card-source">'+escHtml(source)+'</div>' : '') +
      '<div class="tv-card-title">'+escHtml(title)+'</div>' +
      (desc ? '<div class="tv-card-desc">'+escHtml(desc)+'</div>' : '') +
    '</div>';
  }).join('');
}

function tvLoadBrief() {
  window._tvBriefLoaded = true;
  fetch('/api/briefing').then(function(r){return r.json();}).then(function(d) {
    document.getElementById('brief-grid').innerHTML = briefingToCards(d.briefing || '');
  }).catch(function() {
    document.getElementById('brief-grid').innerHTML = '<div class="loading-msg">Could not load briefing.</div>';
  });
}

function tvLoadCalendar() {
  window._tvCalLoaded = true;
  fetch('/api/calendar/today').then(function(r){return r.json();}).then(function(d) {
    var events = d.events || [];
    if (!events.length) {
      document.getElementById('calendar-list').innerHTML = '<div class="loading-msg">No events today.</div>';
      return;
    }
    document.getElementById('calendar-list').innerHTML = events.map(function(ev) {
      return '<div class="tv-event" tabindex="0">' +
        '<div class="tv-event-time">'+escHtml(ev.start||'')+'</div>' +
        '<div><div class="tv-event-title">'+escHtml(ev.title||'')+'</div>' +
        (ev.location ? '<div class="tv-event-loc">'+escHtml(ev.location)+'</div>' : '')+
        '</div></div>';
    }).join('');
  }).catch(function() {
    document.getElementById('calendar-list').innerHTML = '<div class="loading-msg">Could not load calendar.</div>';
  });
}

// TV Chat SSE
(function() {
  var thread = document.getElementById('tv-chat-thread');
  var input  = document.getElementById('tv-chat-input');
  var btn    = document.getElementById('tv-send-btn');

  function tvAppendMsg(role, text) {
    var div = document.createElement('div');
    div.className = 'tv-msg tv-msg-' + role;
    var bub = document.createElement('div');
    bub.className = 'tv-msg-bubble';
    bub.textContent = text;
    div.appendChild(bub);
    thread.appendChild(div);
    scrollBottom(thread);
    return div;
  }

  function tvSend() {
    var text = input.value.trim(); if (!text) return;
    input.value = ''; input.disabled = true; btn.disabled = true;
    tvAppendMsg('user', text);
    fetch('/api/agent/stream', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({messages:[{role:'user',content:text}], conversation_id: _tvConvId})
    }).then(function(resp) {
      var reader = resp.body.getReader(); var decoder = new TextDecoder(); var buf = '';
      var aDiv = null; var aBubble = null;
      function pump() {
        return reader.read().then(function(res) {
          if (res.done) { input.disabled=false; btn.disabled=false; input.focus(); return; }
          buf += decoder.decode(res.value, {stream:true});
          var lines = buf.split('\\n'); buf = lines.pop();
          lines.forEach(function(line) {
            if (!line.startsWith('data: ')) return;
            var raw = line.slice(6).trim(); if (!raw||raw==='[DONE]') return;
            var pkt; try{pkt=JSON.parse(raw);}catch(e){return;}
            if (pkt.type==='text_delta') {
              if (!aDiv) { aDiv=tvAppendMsg('assistant',''); aBubble=aDiv.querySelector('.tv-msg-bubble'); }
              aBubble.textContent += pkt.text; scrollBottom(thread);
            } else if (pkt.type==='tool_call') {
              var chip=document.createElement('div'); chip.className='tv-tool-chip';
              chip.textContent='\\uD83D\\uDD27 '+escHtml(pkt.name||'tool');
              thread.appendChild(chip); scrollBottom(thread); aDiv=null; aBubble=null;
            } else if (pkt.type==='done') { if(pkt.conversation_id)_tvConvId=pkt.conversation_id; aDiv=null; aBubble=null; }
          });
          return pump();
        });
      }
      return pump();
    }).catch(function(err) { tvAppendMsg('assistant','Error: '+err.message); input.disabled=false; btn.disabled=false; });
  }

  btn.addEventListener('click', tvSend);
  input.addEventListener('keydown', function(e) { if(e.key==='Enter'){e.preventDefault();tvSend();} });
})();

tvLoadBrief();
document.querySelectorAll('.tv-nav-item')[0].focus();
</script>
</body>
</html>
"""


# ===========================================================================
# 4. ECHO SHOW / AMBIENT KIOSK VIEW
# ===========================================================================

def show_view() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Show</title>
  <style>
""" + _DARK_VARS + _CHAT_CSS + _DESKTOP_LINK_CSS + """
body {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  overflow: hidden;
  background: #0a0f14;
}

/* Clock area */
.clock-area {
  text-align: center;
  padding: 20px 0 8px;
  flex-shrink: 0;
}
.clock-time {
  font-size: 64px;
  font-weight: 200;
  letter-spacing: -0.02em;
  color: var(--text-1);
  line-height: 1;
}
.clock-date {
  font-size: 18px;
  color: var(--text-2);
  margin-top: 4px;
  font-weight: 300;
}

/* Cards row */
.cards-row {
  display: flex;
  gap: 12px;
  padding: 10px 16px;
  flex-shrink: 0;
}
.show-card {
  flex: 1;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 14px;
  cursor: pointer;
  transition: border-color 0.15s;
  min-height: 90px;
}
.show-card:active { border-color: var(--hue); }
.show-card-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--hue);
  font-weight: 600;
  margin-bottom: 6px;
}
.show-weather-temp { font-size: 36px; font-weight: 700; color: var(--text-1); }
.show-weather-cond { font-size: 14px; color: var(--text-2); margin-top: 2px; }
.show-event-time { font-size: 13px; color: var(--hue); margin-bottom: 3px; }
.show-event-title { font-size: 15px; font-weight: 600; color: var(--text-1); }

/* Headlines */
.headlines-section {
  flex: 1;
  overflow-y: auto;
  padding: 0 16px 6px;
}
.headline-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
}
.headline-num {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-3);
  min-width: 28px;
  flex-shrink: 0;
}
.headline-text { font-size: 17px; font-weight: 500; color: var(--text-1); line-height: 1.4; }
.headline-source { font-size: 12px; color: var(--text-3); margin-top: 2px; }

/* Chat bar at bottom */
.chat-input-row {
  flex-shrink: 0;
}

.loading-msg { color: var(--text-3); font-size: 14px; text-align: center; padding: 20px; }
  </style>
</head>
<body>

<a class="desktop-link" href="javascript:void(0)" onclick="window.location='http://'+window.location.hostname+':8787/'">&#8862; Desktop</a>

<!-- Clock -->
<div class="clock-area">
  <div class="clock-time" id="clock-time">--:--</div>
  <div class="clock-date" id="clock-date">Loading...</div>
</div>

<!-- Cards -->
<div class="cards-row">
  <div class="show-card" id="weather-card" onclick="speakCard('weather-card')">
    <div class="show-card-label">Weather</div>
    <div id="weather-content"><div class="loading-msg" style="padding:4px;font-size:13px;">Loading...</div></div>
  </div>
  <div class="show-card" id="event-card" onclick="speakCard('event-card')">
    <div class="show-card-label">Next Event</div>
    <div id="event-content"><div class="loading-msg" style="padding:4px;font-size:13px;">Loading...</div></div>
  </div>
</div>

<!-- Headlines -->
<div class="headlines-section" id="headlines-section">
  <div class="loading-msg">Loading briefing...</div>
</div>

<!-- Chat input always visible -->
<div class="chat-input-row">
  <input type="text" id="show-chat-input" placeholder="Ask JARVIS anything..." autocomplete="off" style="border-radius:0;border-left:none;border-right:none;">
  <button class="chat-send-btn" id="show-chat-send" style="display:none;">Send</button>
</div>
<!-- Simple send on Enter; responses spoken aloud -->

<script>
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// Clock
function updateClock() {
  var now = new Date();
  var h = now.getHours(), m = now.getMinutes();
  var ampm = h >= 12 ? 'PM' : 'AM';
  h = h % 12 || 12;
  document.getElementById('clock-time').textContent = h + ':' + (m < 10 ? '0'+m : m) + ' ' + ampm;
  var days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  var months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  document.getElementById('clock-date').textContent = days[now.getDay()] + ', ' + months[now.getMonth()] + ' ' + now.getDate();
}
updateClock();
setInterval(updateClock, 10000);

// Speech
function speak(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  var utt = new SpeechSynthesisUtterance(text);
  window.speechSynthesis.speak(utt);
}

function speakCard(id) {
  var el = document.getElementById(id);
  if (el) speak(el.innerText);
}

// Weather
function loadWeather() {
  fetch('/api/weather').then(function(r){return r.json();}).then(function(d) {
    var c = d.current || {};
    document.getElementById('weather-content').innerHTML =
      '<div class="show-weather-temp">'+(c.icon||'')+'&nbsp;'+escHtml(String(c.temp||'--'))+'&deg;</div>' +
      '<div class="show-weather-cond">'+escHtml(c.condition||'')+'</div>' +
      '<div style="font-size:13px;color:var(--text-3)">Feels '+escHtml(String(c.feels_like||'--'))+'&deg;</div>';
  }).catch(function(){document.getElementById('weather-content').innerHTML='<span style="color:var(--text-3);font-size:13px">Unavailable</span>';});
}

// Calendar — next event
function loadNextEvent() {
  fetch('/api/calendar/today').then(function(r){return r.json();}).then(function(d) {
    var events = d.events || [];
    var now = new Date();
    var next = events[0];
    if (!next) {
      document.getElementById('event-content').innerHTML = '<span style="color:var(--text-3);font-size:13px">No events today</span>';
      return;
    }
    document.getElementById('event-content').innerHTML =
      '<div class="show-event-time">'+escHtml(next.start||'')+'</div>' +
      '<div class="show-event-title">'+escHtml(next.title||'')+'</div>' +
      (next.location ? '<div style="font-size:12px;color:var(--text-3)">'+escHtml(next.location)+'</div>' : '');
  }).catch(function(){document.getElementById('event-content').innerHTML='<span style="color:var(--text-3);font-size:13px">Unavailable</span>';});
}

// Headlines
function briefingToHeadlines(text) {
  if (!text) return '<div class="loading-msg">No briefing available.</div>';
  var sections = text.split(/\\n---+\\n/).filter(function(s){return s.trim();}).slice(0,3);
  return sections.map(function(sec, i) {
    var sourceMatch = sec.match(/\\[([^\\]]+)\\]\\s*(.+?)\\n/);
    var source = sourceMatch ? sourceMatch[1] : '';
    var title = sourceMatch ? sourceMatch[2].trim() : sec.split('\\n')[0].replace(/^#+\\s*/,'').trim();
    if (!title) return '';
    return '<div class="headline-item" onclick="speak(\''+title.replace(/'/g,"\\'")+'\')">' +
      '<div class="headline-num">'+(i+1)+'</div>' +
      '<div><div class="headline-text">'+escHtml(title)+'</div>' +
      (source ? '<div class="headline-source">'+escHtml(source)+'</div>' : '') +
      '</div></div>';
  }).join('');
}

function loadBrief() {
  fetch('/api/briefing').then(function(r){return r.json();}).then(function(d) {
    document.getElementById('headlines-section').innerHTML = briefingToHeadlines(d.briefing || '');
  }).catch(function() {
    document.getElementById('headlines-section').innerHTML = '<div class="loading-msg">Could not load briefing.</div>';
  });
}

// Chat — simple: send and speak response
var _showConvId = '';
var _showInput = document.getElementById('show-chat-input');

_showInput.addEventListener('keydown', function(e) {
  if (e.key !== 'Enter') return;
  e.preventDefault();
  var text = _showInput.value.trim(); if (!text) return;
  _showInput.value = '';
  _showInput.disabled = true;
  fetch('/api/agent/stream', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({messages:[{role:'user',content:text}], conversation_id: _showConvId})
  }).then(function(resp) {
    var reader = resp.body.getReader(); var decoder = new TextDecoder(); var buf = '';
    var fullText = '';
    function pump() {
      return reader.read().then(function(res) {
        if (res.done) { _showInput.disabled=false; _showInput.focus(); speak(fullText); return; }
        buf += decoder.decode(res.value, {stream:true});
        var lines = buf.split('\\n'); buf = lines.pop();
        lines.forEach(function(line) {
          if (!line.startsWith('data: ')) return;
          var raw = line.slice(6).trim(); if (!raw||raw==='[DONE]') return;
          var pkt; try{pkt=JSON.parse(raw);}catch(e){return;}
          if (pkt.type==='text_delta') fullText += pkt.text;
          else if (pkt.type==='done' && pkt.conversation_id) _showConvId = pkt.conversation_id;
        });
        return pump();
      });
    }
    return pump();
  }).catch(function(err) { _showInput.disabled=false; _showInput.focus(); });
});

// Auto-refresh every 5 minutes
function loadAll() { loadWeather(); loadNextEvent(); loadBrief(); }
loadAll();
setInterval(loadAll, 300000);
</script>
</body>
</html>
"""


# ===========================================================================
# 5. WATCH VIEW
# ===========================================================================

def watch_view() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black">
  <title>JARVIS Watch</title>
  <style>
""" + _DARK_VARS + _DESKTOP_LINK_CSS + """
body {
  max-width: 390px;
  margin: 0 auto;
  padding: 12px 12px 16px;
  overflow-y: auto;
  min-height: 100dvh;
  background: #000;
}

.desktop-link { top: 6px; right: 6px; font-size: 10px; }

/* Readiness circle */
.readiness-ring-wrap {
  display: flex;
  justify-content: center;
  padding: 16px 0 8px;
}
.readiness-ring {
  width: 110px; height: 110px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 6px solid;
  position: relative;
}
.ring-score { font-size: 38px; font-weight: 800; line-height: 1; }
.ring-label { font-size: 11px; color: var(--text-2); margin-top: 2px; letter-spacing: 0.03em; }

/* Vitals row */
.vitals-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.vital-w {
  flex: 1;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 8px 6px;
  text-align: center;
}
.vital-w-val { font-size: 20px; font-weight: 700; color: var(--hue); }
.vital-w-lbl { font-size: 10px; color: var(--text-3); margin-top: 2px; }

/* Top task */
.top-task-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.top-task-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--amber); flex-shrink: 0; }
.top-task-title { font-size: 14px; color: var(--text-1); font-weight: 500; }

/* Chat thread compact */
.chat-thread-w {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 8px;
  margin-bottom: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 180px;
  overflow-y: auto;
}
.msg-w { display: flex; }
.msg-w-user { justify-content: flex-end; }
.msg-w-assistant { justify-content: flex-start; }
.msg-w-bubble {
  max-width: 85%;
  padding: 7px 10px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg-w-user .msg-w-bubble { background: var(--hue); color: #000; border-bottom-right-radius: 3px; }
.msg-w-assistant .msg-w-bubble { background: var(--surface-hi); color: var(--text-1); border-bottom-left-radius: 3px; }

/* Chat input */
.chat-input-w-row {
  display: flex;
  gap: 6px;
}
.chat-input-w-row input[type=text] {
  flex: 1;
  background: var(--surface);
  color: var(--text-1);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 9px 12px;
  font-size: 14px;
  outline: none;
}
.chat-input-w-row input[type=text]:focus { border-color: var(--hue); }
.chat-send-w {
  background: var(--hue);
  color: #000;
  border: none;
  border-radius: 10px;
  padding: 9px 14px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}
.chat-send-w:disabled { opacity: 0.4; }

.section-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-3);
  margin-bottom: 6px;
  font-weight: 600;
}
.loading-msg { color: var(--text-3); font-size: 12px; text-align: center; padding: 12px; }
  </style>
</head>
<body>

<a class="desktop-link" href="javascript:void(0)" onclick="window.location='http://'+window.location.hostname+':8787/'">&#8862; Desktop</a>

<!-- Readiness ring -->
<div id="readiness-section">
  <div class="readiness-ring-wrap">
    <div class="readiness-ring" id="readiness-ring" style="border-color:var(--text-3)">
      <span class="ring-score" id="ring-score">--</span>
      <span class="ring-label">Readiness</span>
    </div>
  </div>
</div>

<!-- Vitals -->
<div class="vitals-row" id="vitals-row">
  <div class="vital-w"><div class="vital-w-val" id="w-hr">--</div><div class="vital-w-lbl">HR</div></div>
  <div class="vital-w"><div class="vital-w-val" id="w-hrv">--</div><div class="vital-w-lbl">HRV</div></div>
  <div class="vital-w"><div class="vital-w-val" id="w-steps">--</div><div class="vital-w-lbl">Steps</div></div>
  <div class="vital-w"><div class="vital-w-val" id="w-spo2">--</div><div class="vital-w-lbl">SpO2</div></div>
</div>

<!-- Top task -->
<div class="section-label">Top Task</div>
<div class="top-task-card" id="top-task-card">
  <div class="top-task-dot"></div>
  <div class="top-task-title" id="top-task-title">Loading...</div>
</div>

<!-- Chat compact -->
<div class="section-label">Chat</div>
<div class="chat-thread-w" id="watch-thread"></div>
<div class="chat-input-w-row">
  <input type="text" id="watch-chat-input" placeholder="Message JARVIS..." autocomplete="off">
  <button class="chat-send-w" id="watch-chat-send">&#9658;</button>
</div>

<script>
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function scrollBottom(el) { if (el) el.scrollTop = el.scrollHeight; }

// Health
fetch('/api/health/summary').then(function(r){return r.json();}).then(function(d) {
  var score = d.readiness ? d.readiness.score : null;
  var m = d.metrics || {};
  if (score !== null) {
    var color = score >= 70 ? '#3fb950' : score >= 40 ? '#d29922' : '#f85149';
    document.getElementById('ring-score').textContent = score;
    document.getElementById('readiness-ring').style.borderColor = color;
    document.getElementById('ring-score').style.color = color;
  }
  document.getElementById('w-hr').textContent = m.resting_hr || '--';
  document.getElementById('w-hrv').textContent = m.hrv || '--';
  document.getElementById('w-steps').textContent = m.steps ? (m.steps >= 1000 ? (m.steps/1000).toFixed(1)+'k' : m.steps) : '--';
  document.getElementById('w-spo2').textContent = m.blood_oxygen ? m.blood_oxygen+'%' : '--';
}).catch(function(){});

// Tasks
fetch('/api/tasks').then(function(r){return r.json();}).then(function(d) {
  var tasks = d.tasks || [];
  var top = tasks[0];
  document.getElementById('top-task-title').textContent = top ? top.title : 'No tasks';
}).catch(function(){document.getElementById('top-task-title').textContent='Unavailable';});

// Watch chat — keeps last 3 messages visible
var _watchConvId = '';
var _watchMessages = [];

function watchAddMsg(role, text) {
  _watchMessages.push({role:role,text:text});
  if (_watchMessages.length > 6) _watchMessages = _watchMessages.slice(-6);
  renderWatchThread();
}

function renderWatchThread() {
  var thread = document.getElementById('watch-thread');
  var last3 = _watchMessages.slice(-3);
  thread.innerHTML = last3.map(function(m) {
    return '<div class="msg-w msg-w-'+m.role+'"><div class="msg-w-bubble">'+escHtml(m.text)+'</div></div>';
  }).join('');
  scrollBottom(thread);
}

(function() {
  var thread = document.getElementById('watch-thread');
  var input  = document.getElementById('watch-chat-input');
  var btn    = document.getElementById('watch-chat-send');

  function sendWatch() {
    var text = input.value.trim(); if (!text) return;
    input.value = ''; input.disabled = true; btn.disabled = true;
    watchAddMsg('user', text);
    fetch('/api/agent/stream', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({messages:[{role:'user',content:text}], conversation_id: _watchConvId})
    }).then(function(resp) {
      var reader = resp.body.getReader(); var decoder = new TextDecoder(); var buf = '';
      var fullText = '';
      function pump() {
        return reader.read().then(function(res) {
          if (res.done) {
            if (fullText) watchAddMsg('assistant', fullText);
            input.disabled=false; btn.disabled=false; input.focus(); return;
          }
          buf += decoder.decode(res.value, {stream:true});
          var lines = buf.split('\\n'); buf = lines.pop();
          lines.forEach(function(line) {
            if (!line.startsWith('data: ')) return;
            var raw = line.slice(6).trim(); if (!raw||raw==='[DONE]') return;
            var pkt; try{pkt=JSON.parse(raw);}catch(e){return;}
            if (pkt.type==='text_delta') fullText += pkt.text;
            else if (pkt.type==='done' && pkt.conversation_id) _watchConvId = pkt.conversation_id;
          });
          return pump();
        });
      }
      return pump();
    }).catch(function(err) { watchAddMsg('assistant','Error: '+err.message); input.disabled=false; btn.disabled=false; });
  }

  btn.addEventListener('click', sendWatch);
  input.addEventListener('keydown', function(e) { if(e.key==='Enter'){e.preventDefault();sendWatch();} });
})();
</script>
</body>
</html>
"""


# ===========================================================================
# 6. CARPLAY VIEW
# ===========================================================================

def carplay_view() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
  <title>JARVIS Drive</title>
  <style>
""" + _DARK_VARS + """
/* ===== Drive Mode Layout ===== */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

.drive-body {
  background: #000;
  height: 100dvh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  -webkit-tap-highlight-color: transparent;
  font-family: var(--font-sans);
  color: var(--text-1);
}

/* Header */
.drive-header {
  height: 64px;
  flex-shrink: 0;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 16px;
}
.drive-clock {
  font-size: 42px;
  font-weight: 200;
  letter-spacing: -0.02em;
  line-height: 1;
  flex-shrink: 0;
}
.drive-date {
  font-size: 16px;
  color: var(--text-2);
  flex-shrink: 0;
}
.drive-event-chip {
  flex: 1;
  min-width: 0;
  background: rgba(88,166,255,0.12);
  border: 1px solid var(--hue);
  border-radius: 9999px;
  font-size: 14px;
  padding: 5px 14px;
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-1);
}
.drive-header-spacer { flex: 1; }
.drive-desktop-link {
  flex-shrink: 0;
  font-size: 13px;
  color: var(--text-3);
  text-decoration: none;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid var(--border);
  white-space: nowrap;
}
.drive-desktop-link:active { background: var(--surface-hi); }

/* Main two-column area */
.drive-main {
  flex: 1;
  display: flex;
  flex-direction: row;
  overflow: hidden;
}

/* Left column 55% */
.drive-left {
  width: 55%;
  display: flex;
  flex-direction: column;
  padding: 12px;
  gap: 10px;
  border-right: 1px solid var(--border);
}

/* Map container */
.drive-map-container {
  flex: 1;
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  min-height: 0;
  background: #0d1117;
}
#drive-nav-map {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
/* Search bar overlay */
.drive-nav-bar {
  position: absolute;
  top: 12px;
  left: 12px;
  right: 12px;
  z-index: 10;
  display: flex;
  gap: 8px;
  background: rgba(13,17,23,0.92);
  border: 1px solid rgba(88,166,255,0.35);
  border-radius: 12px;
  padding: 6px 10px;
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
}
.drive-nav-input {
  flex: 1;
  background: transparent;
  color: #fff;
  border: none;
  outline: none;
  font-size: 18px;
  font-family: var(--font-sans);
}
.drive-nav-input::placeholder { color: rgba(255,255,255,0.4); }
.drive-nav-go {
  background: var(--hue);
  color: #000;
  border: none;
  border-radius: 8px;
  padding: 8px 18px;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  font-family: var(--font-sans);
}
/* Autocomplete dropdown */
.drive-nav-autocomplete {
  position: absolute;
  top: 70px;
  left: 12px;
  right: 12px;
  z-index: 11;
  background: rgba(13,17,23,0.97);
  border: 1px solid rgba(88,166,255,0.25);
  border-radius: 12px;
  overflow: hidden;
  display: none;
}
.drive-nav-ac-item {
  padding: 14px 16px;
  font-size: 16px;
  color: #fff;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  cursor: pointer;
}
.drive-nav-ac-item:last-child { border-bottom: none; }
.drive-nav-ac-item:active { background: rgba(88,166,255,0.15); }
/* Home quick-nav button */
.drive-nav-home-btn {
  position: absolute;
  bottom: 12px;
  left: 12px;
  z-index: 10;
  background: rgba(13,17,23,0.92);
  border: 1px solid rgba(88,166,255,0.35);
  color: #fff;
  border-radius: 12px;
  padding: 10px 18px;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  font-family: var(--font-sans);
}
.drive-nav-home-btn:active { background: rgba(88,166,255,0.2); }
/* Turn instruction HUD */
.drive-nav-hud {
  position: absolute;
  bottom: 12px;
  left: 130px;
  right: 60px;
  z-index: 10;
  background: rgba(13,17,23,0.92);
  border: 1px solid rgba(88,166,255,0.35);
  border-radius: 12px;
  padding: 8px 14px;
  display: none;
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
}
.drive-nav-hud-turn {
  font-size: 15px;
  font-weight: 700;
  color: #00D4FF;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.drive-nav-hud-dist { font-size: 12px; color: rgba(255,255,255,0.5); margin-top: 2px; }
/* Cancel route button */
.drive-nav-cancel {
  position: absolute;
  bottom: 12px;
  right: 12px;
  z-index: 12;
  background: rgba(180,40,40,0.9);
  border: none;
  border-radius: 10px;
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  padding: 10px 14px;
  cursor: pointer;
  display: none;
  font-family: var(--font-sans);
}
/* Map not loaded fallback */
.drive-map-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 12px;
  color: rgba(255,255,255,0.3);
  font-size: 15px;
  pointer-events: none;
}
.drive-map-loading-icon { font-size: 40px; }

/* SAM health strip */
.drive-sam-strip {
  height: 52px;
  flex-shrink: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 24px;
}
.drive-sam-metric {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.drive-sam-val { font-size: 18px; font-weight: 700; color: var(--hue); }
.drive-sam-lbl { font-size: 10px; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.05em; }
.drive-sam-divider { width: 1px; height: 28px; background: var(--border); flex-shrink: 0; }

/* Right column 45% */
.drive-right {
  width: 45%;
  display: flex;
  flex-direction: column;
  padding: 12px;
  gap: 10px;
}

/* Drive buttons */
.drive-btn {
  flex: 1;
  width: 100%;
  border: none;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  font-size: 22px;
  font-weight: 700;
  cursor: pointer;
  min-height: 80px;
  transition: all 0.15s;
  -webkit-tap-highlight-color: transparent;
  font-family: var(--font-sans);
  line-height: 1;
}
.drive-btn-icon { font-size: 28px; line-height: 1; }

/* Voice button */
.drive-btn-voice {
  background: rgba(88,166,255,0.15);
  border: 2px solid var(--hue);
  color: var(--hue);
}
.drive-btn-voice:active { background: rgba(88,166,255,0.25); }
.drive-btn-voice.listening {
  background: rgba(88,166,255,0.30);
  animation: pulse-listen 1s ease-in-out infinite;
}

/* Briefing button */
.drive-btn-brief {
  background: rgba(63,185,80,0.15);
  border: 2px solid var(--green);
  color: var(--green);
}
.drive-btn-brief:active { background: rgba(63,185,80,0.25); }
.drive-btn-brief.playing { background: rgba(63,185,80,0.30); }

/* Kasa buttons */
.drive-btn-kasa {
  background: var(--surface);
  border: 2px solid var(--border);
  color: var(--text-1);
}
.drive-btn-kasa:active { background: var(--surface-hi); }
.drive-btn-kasa.success {
  border-color: var(--green);
  color: var(--green);
}
.drive-btn-kasa.no-scene {
  opacity: 0.4;
  cursor: default;
}

/* ---- Navigation guidance panel (right column, nav-active state) ---- */
.drive-guidance-panel {
  flex-shrink: 0;
  background: rgba(0,212,255,0.05);
  border: 2px solid rgba(0,212,255,0.3);
  border-radius: 16px;
  padding: 16px 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.drive-guidance-top {
  display: flex;
  align-items: center;
  gap: 12px;
}
.drive-guidance-arrow {
  font-size: 68px;
  line-height: 1;
  flex-shrink: 0;
  width: 76px;
  text-align: center;
  filter: drop-shadow(0 0 14px rgba(0,212,255,0.6));
  transition: all 0.3s;
}
.drive-guidance-text {
  flex: 1;
  min-width: 0;
}
.drive-guidance-action {
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(0,212,255,0.7);
  margin-bottom: 3px;
}
.drive-guidance-street {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.15;
}
.drive-guidance-dist {
  font-size: 40px;
  font-weight: 200;
  color: #fff;
  text-align: center;
  letter-spacing: -0.02em;
  line-height: 1;
  padding: 4px 0;
}
.drive-guidance-divider {
  height: 1px;
  background: rgba(0,212,255,0.15);
  margin: 0 -4px;
}
.drive-guidance-eta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  color: rgba(255,255,255,0.55);
  padding-top: 2px;
}
.drive-guidance-eta-val {
  font-size: 16px;
  font-weight: 700;
  color: rgba(255,255,255,0.85);
}
/* End-route button */
.drive-btn-end-route {
  background: rgba(180,40,40,0.15);
  border: 2px solid rgba(180,40,40,0.6);
  color: #ff7070;
  flex: 0 0 auto !important;
  min-height: 60px !important;
}
.drive-btn-end-route:active { background: rgba(180,40,40,0.35); }

/* POI button grid */
.drive-poi-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 7px;
  flex-shrink: 0;
}
.drive-poi-btn {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  color: var(--text-2);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 8px 4px;
  min-height: 58px;
  font-family: var(--font-sans);
  position: relative;
  transition: all 0.15s;
  -webkit-tap-highlight-color: transparent;
}
.drive-poi-btn:active { background: var(--surface-hi); }
.drive-poi-btn.active {
  border-color: var(--hue);
  background: rgba(88,166,255,0.12);
  color: var(--hue);
}
.drive-poi-btn.loading { opacity: 0.6; }
.drive-poi-icon { font-size: 22px; line-height: 1; }
.drive-poi-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; line-height: 1; }
.drive-poi-badge {
  position: absolute;
  top: 5px;
  right: 6px;
  background: var(--hue);
  color: #000;
  font-size: 10px;
  font-weight: 700;
  border-radius: 9999px;
  min-width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 3px;
  display: none;
}

/* Wrapper groups for idle vs nav state */
#drive-idle-btns {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 10px;
}
#drive-nav-btns {
  display: none;
  flex-direction: column;
  flex: 1;
  gap: 10px;
}

/* Fallback voice input row */
.drive-voice-fallback {
  display: none;
  gap: 8px;
  flex-shrink: 0;
}
.drive-voice-fallback input {
  flex: 1;
  background: var(--surface-hi);
  color: var(--text-1);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 16px;
  font-family: var(--font-sans);
  outline: none;
}
.drive-voice-fallback input:focus { border-color: var(--hue); }
.drive-voice-fallback button {
  background: var(--hue);
  color: #000;
  border: none;
  border-radius: 10px;
  padding: 10px 16px;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  font-family: var(--font-sans);
}

@keyframes pulse-listen {
  0%   { box-shadow: 0 0 0 0 rgba(88,166,255,0.5); }
  50%  { box-shadow: 0 0 0 12px rgba(88,166,255,0); }
  100% { box-shadow: 0 0 0 0 rgba(88,166,255,0); }
}
  </style>
</head>
<body class="drive-body">

<!-- Header -->
<div class="drive-header">
  <div class="drive-clock" id="drive-clock">--:--</div>
  <div class="drive-date" id="drive-date">---</div>
  <div class="drive-event-chip" id="drive-event-chip" style="display:none"></div>
  <div class="drive-header-spacer"></div>
  <a class="drive-desktop-link" href="javascript:void(0)"
     onclick="window.location='http://'+window.location.hostname+':8787/'">&#8862; Desktop</a>
</div>

<!-- Main area -->
<div class="drive-main">

  <!-- Left: Map + SAM strip -->
  <div class="drive-left">
    <div class="drive-map-container" id="drive-map-container">
      <div id="drive-nav-map"></div>
      <!-- Loading fallback (shown until Maps API ready) -->
      <div class="drive-map-loading" id="drive-map-loading">
        <div class="drive-map-loading-icon">&#128739;</div>
        <div>Loading map&hellip;</div>
      </div>
      <!-- Destination search bar -->
      <div class="drive-nav-bar">
        <input class="drive-nav-input" id="drive-nav-dest"
               placeholder="Where to?" autocomplete="off"
               oninput="driveNavAutocomplete(this.value)"
               onkeydown="if(event.key==='Enter'){driveNavGo();}">
        <button class="drive-nav-go" onclick="driveNavGo()">Go</button>
      </div>
      <!-- Autocomplete results -->
      <div class="drive-nav-autocomplete" id="drive-nav-ac"></div>
      <!-- Home quick-nav -->
      <button class="drive-nav-home-btn" id="drive-nav-home-btn"
              onclick="driveNavHome()" style="display:none">
        &#127968; Home
      </button>
      <!-- Turn-by-turn HUD -->
      <div class="drive-nav-hud" id="drive-nav-hud">
        <div class="drive-nav-hud-turn" id="drive-nav-hud-turn">--</div>
        <div class="drive-nav-hud-dist" id="drive-nav-hud-dist">--</div>
      </div>
      <!-- Cancel route -->
      <button class="drive-nav-cancel" id="drive-nav-cancel"
              onclick="driveNavCancel()">&#10005;</button>
    </div>
    <div class="drive-sam-strip" id="drive-sam-strip">
      <div class="drive-sam-metric">
        <div class="drive-sam-val" id="sam-readiness">--</div>
        <div class="drive-sam-lbl">Readiness</div>
      </div>
      <div class="drive-sam-divider"></div>
      <div class="drive-sam-metric">
        <div class="drive-sam-val" id="sam-hrv">--</div>
        <div class="drive-sam-lbl">HRV ms</div>
      </div>
      <div class="drive-sam-divider"></div>
      <div class="drive-sam-metric">
        <div class="drive-sam-val" id="sam-sleep">--</div>
        <div class="drive-sam-lbl">Sleep hr</div>
      </div>
    </div>
  </div>

  <!-- Right: Navigation guidance panel + action buttons -->
  <div class="drive-right">

    <!-- Voice command: always visible at top -->
    <button class="drive-btn drive-btn-voice" id="drive-btn-voice" onclick="handleVoiceCommand()">
      <span class="drive-btn-icon">&#127897;</span>
      <span id="drive-voice-label">Voice Command</span>
    </button>
    <div class="drive-voice-fallback" id="drive-voice-fallback">
      <input type="text" id="drive-voice-input" placeholder="Type a command..." autocomplete="off">
      <button onclick="submitTextCommand()">Go</button>
    </div>

    <!-- NAV ACTIVE: Guidance panel + End Route button -->
    <div id="drive-nav-btns">
      <!-- Guidance card -->
      <div class="drive-guidance-panel" id="drive-guidance-panel">
        <div class="drive-guidance-top">
          <div class="drive-guidance-arrow" id="drive-guidance-arrow">&#8593;</div>
          <div class="drive-guidance-text">
            <div class="drive-guidance-action" id="drive-guidance-action">CONTINUE</div>
            <div class="drive-guidance-street" id="drive-guidance-street">--</div>
          </div>
        </div>
        <div class="drive-guidance-dist" id="drive-guidance-dist">--</div>
        <div class="drive-guidance-divider"></div>
        <div class="drive-guidance-eta-row">
          <span>ETA</span>
          <span class="drive-guidance-eta-val" id="drive-guidance-eta">--</span>
          <span id="drive-guidance-remain">--</span>
        </div>
      </div>
      <!-- POI quick-search grid -->
      <div class="drive-poi-grid" id="drive-poi-grid">
        <button class="drive-poi-btn" id="poi-btn-food"      onclick="driveTogglePoi('food')">
          <span class="drive-poi-icon">&#127828;</span>
          <span class="drive-poi-label">Food</span>
          <span class="drive-poi-badge" id="poi-badge-food"></span>
        </button>
        <button class="drive-poi-btn" id="poi-btn-starbucks" onclick="driveTogglePoi('starbucks')">
          <span class="drive-poi-icon">&#9749;</span>
          <span class="drive-poi-label">Starbucks</span>
          <span class="drive-poi-badge" id="poi-badge-starbucks"></span>
        </button>
        <button class="drive-poi-btn" id="poi-btn-parks"     onclick="driveTogglePoi('parks')">
          <span class="drive-poi-icon">&#127794;</span>
          <span class="drive-poi-label">Parks</span>
          <span class="drive-poi-badge" id="poi-badge-parks"></span>
        </button>
        <button class="drive-poi-btn" id="poi-btn-historic"  onclick="driveTogglePoi('historic')">
          <span class="drive-poi-icon">&#127963;</span>
          <span class="drive-poi-label">Historic</span>
          <span class="drive-poi-badge" id="poi-badge-historic"></span>
        </button>
        <button class="drive-poi-btn" id="poi-btn-family"    onclick="driveTogglePoi('family')">
          <span class="drive-poi-icon">&#11088;</span>
          <span class="drive-poi-label">Family</span>
          <span class="drive-poi-badge" id="poi-badge-family"></span>
        </button>
        <button class="drive-poi-btn" id="poi-btn-gas"       onclick="driveTogglePoi('gas')">
          <span class="drive-poi-icon">&#9981;</span>
          <span class="drive-poi-label">Gas</span>
          <span class="drive-poi-badge" id="poi-badge-gas"></span>
        </button>
      </div>

      <!-- End Route -->
      <button class="drive-btn drive-btn-end-route" onclick="driveNavCancel()">
        <span class="drive-btn-icon">&#11035;</span>
        <span>End Route</span>
      </button>
    </div>

    <!-- IDLE: SAM brief + home scenes -->
    <div id="drive-idle-btns">
      <button class="drive-btn drive-btn-brief" id="drive-btn-brief" onclick="readSamBrief()">
        <span class="drive-btn-icon">&#128203;</span>
        <span id="drive-brief-label">SAM Briefing</span>
      </button>
      <button class="drive-btn drive-btn-kasa no-scene" id="drive-btn-arrive"
              onclick="triggerKasaScene(_arriveSceneId, this)">
        <span class="drive-btn-icon">&#127968;</span>
        <span id="drive-arrive-label">Arrive Home</span>
      </button>
      <button class="drive-btn drive-btn-kasa no-scene" id="drive-btn-leave"
              onclick="triggerKasaScene(_leaveSceneId, this)">
        <span class="drive-btn-icon">&#128663;</span>
        <span id="drive-leave-label">Leave Home</span>
      </button>
    </div>

  </div>

</div>

<script>
// ---- State ----
var _driveConvId = '';
var _kasaScenes = [];
var _arriveSceneId = null;
var _leaveSceneId = null;
var _isSpeaking = false;
var _samData = null;

// ---- Utilities ----
function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ---- Clock ----
function updateClock() {
  var now = new Date();
  var h = now.getHours();
  var m = now.getMinutes();
  var ampm = h >= 12 ? 'PM' : 'AM';
  h = h % 12;
  if (h === 0) h = 12;
  var mm = m < 10 ? '0' + m : String(m);
  document.getElementById('drive-clock').textContent = h + ':' + mm + ' ' + ampm;

  var days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  document.getElementById('drive-date').textContent =
    days[now.getDay()] + ', ' + months[now.getMonth()] + ' ' + now.getDate();
}
updateClock();
setInterval(updateClock, 30000);

// ---- Next event chip ----
function loadNextEvent() {
  fetch('/api/calendar/today').then(function(r) { return r.json(); }).then(function(d) {
    var events = d.events || [];
    var now = new Date();
    var chip = document.getElementById('drive-event-chip');
    var next = null;
    for (var i = 0; i < events.length; i++) {
      var ev = events[i];
      var startStr = ev.start_iso || ev.start || '';
      if (!startStr) continue;
      var t = new Date(startStr);
      if (isNaN(t.getTime())) continue;
      if (t >= now) { next = {title: ev.title || '', time: t}; break; }
    }
    if (!next) { chip.style.display = 'none'; return; }
    var diffMs = next.time - now;
    var diffMin = Math.round(diffMs / 60000);
    var label;
    if (diffMin <= 0) {
      label = escHtml(next.title) + ' now';
    } else if (diffMin < 60) {
      label = escHtml(next.title) + ' in ' + diffMin + 'm';
    } else {
      var hrs = Math.floor(diffMin / 60);
      var mins = diffMin % 60;
      label = escHtml(next.title) + ' in ' + hrs + 'h' + (mins ? ' ' + mins + 'm' : '');
    }
    chip.innerHTML = label;
    chip.style.display = '';
  }).catch(function() {
    document.getElementById('drive-event-chip').style.display = 'none';
  });
}
loadNextEvent();
setInterval(loadNextEvent, 60000);

// ---- SAM health strip ----
function loadSamStrip() {
  fetch('/api/health/sam/morning-checkin').then(function(r) { return r.json(); }).then(function(d) {
    _samData = d;
    var r = d.readiness_score || d.readiness || '--';
    var hrv = d.hrv_ms || d.hrv || '--';
    var sleep = d.sleep_hours || d.sleep || '--';
    if (typeof r === 'number') r = Math.round(r) + '%';
    if (typeof hrv === 'number') hrv = Math.round(hrv);
    if (typeof sleep === 'number') sleep = sleep.toFixed(1);
    document.getElementById('sam-readiness').textContent = r;
    document.getElementById('sam-hrv').textContent = hrv;
    document.getElementById('sam-sleep').textContent = sleep;
  }).catch(function() {});
}
loadSamStrip();

// ---- Kasa scenes ----
function loadKasaScenes() {
  fetch('/api/kasa/scenes').then(function(r) { return r.json(); }).then(function(d) {
    _kasaScenes = d.scenes || d || [];
    _arriveSceneId = null;
    _leaveSceneId = null;
    var arriveRe = /home|arrive/i;
    var leaveRe = /leave|away|depart/i;
    for (var i = 0; i < _kasaScenes.length; i++) {
      var sc = _kasaScenes[i];
      var name = sc.name || sc.scene_name || '';
      if (!_arriveSceneId && arriveRe.test(name)) {
        _arriveSceneId = sc.id || sc.scene_id || null;
        document.getElementById('drive-arrive-label').textContent = name;
        document.getElementById('drive-btn-arrive').classList.remove('no-scene');
      }
      if (!_leaveSceneId && leaveRe.test(name)) {
        _leaveSceneId = sc.id || sc.scene_id || null;
        document.getElementById('drive-leave-label').textContent = name;
        document.getElementById('drive-btn-leave').classList.remove('no-scene');
      }
    }
    if (!_arriveSceneId) document.getElementById('drive-arrive-label').textContent = 'No Scene Set';
    if (!_leaveSceneId) document.getElementById('drive-leave-label').textContent = 'No Scene Set';
  }).catch(function() {});
}
loadKasaScenes();
driveLoadMapsScript();

// ---- TTS helper ----
function speak(text, onEnd) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  _isSpeaking = true;
  var utt = new SpeechSynthesisUtterance(text);
  utt.rate = 0.95;
  utt.onend = function() {
    _isSpeaking = false;
    if (onEnd) onEnd();
  };
  utt.onerror = function() {
    _isSpeaking = false;
    if (onEnd) onEnd();
  };
  window.speechSynthesis.speak(utt);
}

// ---- Voice Command ----
function handleVoiceCommand() {
  var SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  var btn = document.getElementById('drive-btn-voice');
  var lbl = document.getElementById('drive-voice-label');

  if (!SpeechRec) {
    var fb = document.getElementById('drive-voice-fallback');
    fb.style.display = fb.style.display === 'flex' ? 'none' : 'flex';
    return;
  }

  if (btn.classList.contains('listening')) return;

  var rec = new SpeechRec();
  rec.lang = 'en-US';
  rec.interimResults = false;
  rec.maxAlternatives = 1;

  btn.classList.add('listening');
  lbl.textContent = 'Listening…';

  rec.onresult = function(e) {
    var transcript = e.results[0][0].transcript;
    btn.classList.remove('listening');
    lbl.textContent = 'Processing…';
    sendVoiceText(transcript, btn, lbl);
  };

  rec.onerror = function() {
    btn.classList.remove('listening');
    lbl.textContent = 'Voice Command';
  };

  rec.onend = function() {
    if (btn.classList.contains('listening')) {
      btn.classList.remove('listening');
      lbl.textContent = 'Voice Command';
    }
  };

  rec.start();
}

function submitTextCommand() {
  var inp = document.getElementById('drive-voice-input');
  var text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  var btn = document.getElementById('drive-btn-voice');
  var lbl = document.getElementById('drive-voice-label');
  lbl.textContent = 'Processing…';
  sendVoiceText(text, btn, lbl);
}

function driveCheckNavIntent(text) {
  var lower = text.toLowerCase();
  var patterns = [
    /^navigate to (.+)$/i,
    /^take me to (.+)$/i,
    /^directions to (.+)$/i,
    /^go to (.+)$/i,
    /^drive to (.+)$/i
  ];
  for (var i = 0; i < patterns.length; i++) {
    var m = lower.match(patterns[i]);
    if (m) return m[1].trim();
  }
  return null;
}

function sendVoiceText(text, btn, lbl) {
  var navDest = driveCheckNavIntent(text);
  if (navDest) {
    btn.classList.remove('listening');
    lbl.textContent = 'Voice Command';
    document.getElementById('drive-nav-dest').value = navDest;
    driveNavGo();
    return;
  }
  fetch('/api/agent/stream', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({messages: [{role: 'user', content: text}], conversation_id: _driveConvId})
  }).then(function(resp) {
    var reader = resp.body.getReader();
    var decoder = new TextDecoder();
    var buf = '';
    var fullText = '';
    function pump() {
      return reader.read().then(function(res) {
        if (res.done) {
          lbl.textContent = 'Voice Command';
          if (fullText) {
            speak(fullText, function() { lbl.textContent = 'Voice Command'; });
          }
          return;
        }
        buf += decoder.decode(res.value, {stream: true});
        var lines = buf.split('\\n');
        buf = lines.pop();
        for (var i = 0; i < lines.length; i++) {
          var line = lines[i];
          if (!line.startsWith('data: ')) continue;
          var raw = line.slice(6).trim();
          if (!raw || raw === '[DONE]') continue;
          var pkt;
          try { pkt = JSON.parse(raw); } catch(e2) { continue; }
          if (pkt.type === 'text_delta') fullText += pkt.text;
          if (pkt.type === 'done' && pkt.conversation_id) _driveConvId = pkt.conversation_id;
        }
        return pump();
      });
    }
    return pump();
  }).catch(function() {
    lbl.textContent = 'Voice Command';
  });
}

// ---- SAM Briefing ----
function readSamBrief() {
  var btn = document.getElementById('drive-btn-brief');
  var lbl = document.getElementById('drive-brief-label');

  if (btn.classList.contains('playing')) {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    btn.classList.remove('playing');
    lbl.textContent = 'SAM Briefing';
    _isSpeaking = false;
    return;
  }

  btn.classList.add('playing');
  lbl.textContent = 'Loading…';

  fetch('/api/health/sam/morning-checkin').then(function(r) { return r.json(); }).then(function(d) {
    var readiness = d.readiness_score || d.readiness || '?';
    var hrv = d.hrv_ms || d.hrv || '?';
    var sleep = d.sleep_hours || d.sleep || '?';
    var focus = d.focus_primary || d.focus || '';
    var greeting = d.greeting || d.message || '';

    if (typeof readiness === 'number') readiness = Math.round(readiness);
    if (typeof hrv === 'number') hrv = Math.round(hrv);
    if (typeof sleep === 'number') sleep = sleep.toFixed(1);

    var tts = 'Good morning. Your readiness is ' + readiness + ' percent. ' +
              'HRV is ' + hrv + ' milliseconds. ' +
              'Sleep: ' + sleep + ' hours.';
    if (focus) tts += ' Focus: ' + focus + '.';
    if (greeting) tts += ' ' + greeting;

    lbl.textContent = 'Playing…';
    speak(tts, function() {
      btn.classList.remove('playing');
      lbl.textContent = 'SAM Briefing';
    });
  }).catch(function() {
    btn.classList.remove('playing');
    lbl.textContent = 'SAM Briefing';
  });
}

// ---- Navigation ----
var _driveNavMap = null;
var _driveNavMapsLoaded = false;
var _driveNavRenderer = null;
var _driveNavDirectionsService = null;
var _driveNavUserMarker = null;
var _driveNavAcTimer = null;
var _driveNavHomeAddr = '';
var _driveNavSteps = [];
var _driveNavCurrentStep = 0;
var _driveNavWatchId = null;
var _driveNavRouteLeg = null;

// Maneuver → Unicode arrow mapping
var MANEUVER_ARROWS = {
  'straight':          '&#8593;',
  'merge':             '&#8593;',
  'keep-left':         '&#8598;',
  'keep-right':        '&#8599;',
  'turn-slight-left':  '&#8598;',
  'turn-slight-right': '&#8599;',
  'turn-left':         '&#8592;',
  'turn-right':        '&#8594;',
  'turn-sharp-left':   '&#8629;',
  'turn-sharp-right':  '&#8631;',
  'ramp-left':         '&#8592;',
  'ramp-right':        '&#8594;',
  'fork-left':         '&#8598;',
  'fork-right':        '&#8599;',
  'uturn-left':        '&#8634;',
  'uturn-right':       '&#8635;',
  'roundabout-left':   '&#8634;',
  'roundabout-right':  '&#8635;',
  'arrive':            '&#11088;'
};

var _drivePendingDest = '';  // queued destination if Maps not ready yet

function driveLoadMapsScript() {
  fetch('/api/nav/maps-key').then(function(r) { return r.json(); }).then(function(d) {
    if (!d.key) {
      document.getElementById('drive-map-loading').innerHTML =
        '<div style="font-size:14px;padding:20px;text-align:center;color:rgba(255,100,100,0.8)">Maps API key not configured</div>';
      return;
    }
    var s = document.createElement('script');
    s.src = 'https://maps.googleapis.com/maps/api/js?key=' + d.key +
            '&loading=async&callback=driveOnMapsReady';
    s.async = true;
    s.onerror = function() {
      document.getElementById('drive-map-loading').innerHTML =
        '<div style="font-size:14px;padding:20px;text-align:center;color:rgba(255,100,100,0.8)">Map failed to load</div>';
    };
    document.head.appendChild(s);
  }).catch(function() {});
}

function driveOnMapsReady() {
  _driveNavMapsLoaded = true;
  var loading = document.getElementById('drive-map-loading');
  if (loading) loading.style.display = 'none';
  // Execute any route that was queued before Maps finished loading
  if (_drivePendingDest) {
    var dest = _drivePendingDest;
    _drivePendingDest = '';
    driveNavRoute('My Location', dest);
  }
  var darkStyles = [
    {elementType:'geometry', stylers:[{color:'#1a1a2e'}]},
    {elementType:'labels.text.fill', stylers:[{color:'#9e9e9e'}]},
    {elementType:'labels.text.stroke', stylers:[{color:'#212121'}]},
    {elementType:'labels.icon', stylers:[{visibility:'off'}]},
    {featureType:'road', elementType:'geometry', stylers:[{color:'#2c2c2c'}]},
    {featureType:'road.arterial', elementType:'labels.text.fill', stylers:[{color:'#757575'}]},
    {featureType:'road.highway', elementType:'geometry', stylers:[{color:'#3c3c3c'}]},
    {featureType:'road.highway', elementType:'labels.text.fill', stylers:[{color:'#ffffff'}]},
    {featureType:'water', elementType:'geometry', stylers:[{color:'#000000'}]},
    {featureType:'poi', elementType:'geometry', stylers:[{color:'#181818'}]},
    {featureType:'transit', elementType:'geometry', stylers:[{color:'#2f3948'}]},
    {featureType:'landscape', elementType:'geometry', stylers:[{color:'#0d1117'}]}
  ];
  _driveNavMap = new google.maps.Map(document.getElementById('drive-nav-map'), {
    center: {lat: 37.09, lng: -95.71},
    zoom: 5,
    styles: darkStyles,
    disableDefaultUI: true,
    gestureHandling: 'greedy'
  });
  _driveNavRenderer = new google.maps.DirectionsRenderer({
    map: _driveNavMap,
    suppressMarkers: false,
    polylineOptions: {strokeColor: '#00D4FF', strokeWeight: 5}
  });
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(function(pos) {
      var ll = {lat: pos.coords.latitude, lng: pos.coords.longitude};
      _driveNavMap.setCenter(ll);
      _driveNavMap.setZoom(14);
      _driveNavUserMarker = new google.maps.Marker({
        position: ll, map: _driveNavMap,
        icon: {
          path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
          scale: 6, fillColor: '#00D4FF', fillOpacity: 1,
          strokeColor: '#fff', strokeWeight: 2,
          rotation: pos.coords.heading || 0
        }, title: 'You'
      });
    }, function() {});
  }
  fetch('/api/nav/home').then(function(r) { return r.json(); }).then(function(d) {
    _driveNavHomeAddr = d.home_address || d.address || '';
    if (_driveNavHomeAddr) {
      var btn = document.getElementById('drive-nav-home-btn');
      if (btn) btn.style.display = 'flex';
    }
  }).catch(function() {});
}

function driveNavAutocomplete(val) {
  clearTimeout(_driveNavAcTimer);
  var ac = document.getElementById('drive-nav-ac');
  if (!val || val.length < 3) { ac.style.display = 'none'; return; }
  _driveNavAcTimer = setTimeout(function() {
    fetch('/api/nav/autocomplete?q=' + encodeURIComponent(val))
      .then(function(r) { return r.json(); }).then(function(d) {
        var preds = d.predictions || [];
        if (!preds.length) { ac.style.display = 'none'; return; }
        var html = '';
        for (var i = 0; i < Math.min(preds.length, 4); i++) {
          html += '<div class="drive-nav-ac-item" data-desc="' + escHtml(preds[i].description) +
                  '" onclick="driveNavSelect(this.dataset.desc)">' +
                  escHtml(preds[i].description) + '</div>';
        }
        ac.innerHTML = html;
        ac.style.display = 'block';
      }).catch(function() { ac.style.display = 'none'; });
  }, 280);
}

function driveNavSelect(desc) {
  document.getElementById('drive-nav-dest').value = desc;
  document.getElementById('drive-nav-ac').style.display = 'none';
  driveNavGo();
}

function driveNavGo() {
  var dest = document.getElementById('drive-nav-dest').value.trim();
  if (!dest) return;
  document.getElementById('drive-nav-ac').style.display = 'none';
  var goBtn = document.querySelector('.drive-nav-go');
  if (!_driveNavMapsLoaded) {
    // Queue it — will fire automatically once driveOnMapsReady() runs
    _drivePendingDest = dest;
    if (goBtn) goBtn.textContent = 'Loading…';
    return;
  }
  if (goBtn) goBtn.textContent = 'Routing…';
  driveNavRoute('My Location', dest);
}

function driveNavHome() {
  if (!_driveNavHomeAddr) return;
  document.getElementById('drive-nav-dest').value = _driveNavHomeAddr;
  var goBtn = document.querySelector('.drive-nav-go');
  if (goBtn) goBtn.textContent = 'Routing…';
  driveNavRoute('My Location', _driveNavHomeAddr);
}

function driveNavRoute(origin, dest) {
  if (!_driveNavMapsLoaded) {
    _drivePendingDest = dest;
    return;
  }
  if (!_driveNavDirectionsService) _driveNavDirectionsService = new google.maps.DirectionsService();
  if (origin === 'My Location' && navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      function(pos) {
        _driveDoRoute(new google.maps.LatLng(pos.coords.latitude, pos.coords.longitude), dest);
      },
      function() {
        // Geolocation denied or timed out — route from map center if available
        if (_driveNavMap) {
          _driveDoRoute(_driveNavMap.getCenter(), dest);
        } else {
          _driveDoRoute(dest, dest); // last resort: same place (Maps will show destination)
        }
      },
      {timeout: 5000, maximumAge: 30000, enableHighAccuracy: false}
    );
  } else {
    _driveDoRoute(origin, dest);
  }
}

function _driveDoRoute(origin, dest) {
  _driveNavDirectionsService.route({
    origin: origin, destination: dest,
    travelMode: google.maps.TravelMode.DRIVING
  }, function(result, status) {
    var goBtn = document.querySelector('.drive-nav-go');
    if (goBtn) goBtn.textContent = 'Go';
    if (status !== 'OK') {
      if (goBtn) { goBtn.textContent = 'No route'; setTimeout(function(){ goBtn.textContent='Go'; }, 2000); }
      return;
    }
    _driveNavRenderer.setDirections(result);
    _driveNavRouteLeg = result.routes[0].legs[0];
    _driveNavSteps = _driveNavRouteLeg.steps || [];
    _driveNavCurrentStep = 0;
    // Capture polyline + mileage for POI searches
    var route = result.routes[0];
    _drivePolyline = (route.overview_polyline && route.overview_polyline.points) ? route.overview_polyline.points : '';
    _driveTotalMiles = _driveNavRouteLeg.distance ? _driveNavRouteLeg.distance.value / 1609.34 : 0;
    _driveGeoWaypoints = result.geocoded_waypoints || [];
    driveClearAllPois();
    driveUpdateGuidance(_driveNavSteps[0], _driveNavRouteLeg);
    driveSetNavState(true);
    driveStartStepTracking();
  });
}

function driveUpdateGuidance(step, leg) {
  if (!step) return;
  var instr = step.instructions.replace(/<[^>]+>/g, '');
  var maneuver = step.maneuver || 'straight';
  var arrow = MANEUVER_ARROWS[maneuver] || '&#8593;';
  // Split instruction: "Turn left onto Oak Street" → action="Turn left", street="Oak Street"
  var action = instr;
  var street = '';
  var ontoMatch = instr.match(/^(.+?)\s+(?:onto|on|toward|to)\s+(.+)$/i);
  if (ontoMatch) { action = ontoMatch[1]; street = ontoMatch[2]; }
  // Compute ETA
  var now = new Date();
  var etaMs = now.getTime() + (leg.duration.value * 1000);
  var etaDate = new Date(etaMs);
  var h = etaDate.getHours(); var m = etaDate.getMinutes();
  var ampm = h >= 12 ? 'PM' : 'AM';
  h = h % 12; if (!h) h = 12;
  var etaStr = h + ':' + (m < 10 ? '0' : '') + m + ' ' + ampm;
  // Duration remaining
  var totalSec = leg.duration.value;
  var remain = totalSec >= 3600
    ? Math.floor(totalSec/3600) + 'h ' + Math.floor((totalSec%3600)/60) + 'm'
    : Math.floor(totalSec/60) + ' min';
  document.getElementById('drive-guidance-arrow').innerHTML = arrow;
  document.getElementById('drive-guidance-action').textContent = action;
  document.getElementById('drive-guidance-street').textContent = street || instr;
  document.getElementById('drive-guidance-dist').textContent = step.distance.text;
  document.getElementById('drive-guidance-eta').textContent = etaStr;
  document.getElementById('drive-guidance-remain').textContent = remain + ' remaining';
  // Also update map HUD strip
  var hud = document.getElementById('drive-nav-hud');
  document.getElementById('drive-nav-hud-turn').textContent = action + (street ? ' · ' + street : '');
  document.getElementById('drive-nav-hud-dist').textContent = step.distance.text + ' · ETA ' + etaStr;
  hud.style.display = 'block';
}

function driveSetNavState(active) {
  document.getElementById('drive-nav-btns').style.display = active ? 'flex' : 'none';
  document.getElementById('drive-idle-btns').style.display = active ? 'none' : 'flex';
  document.getElementById('drive-nav-cancel').style.display = active ? 'block' : 'none';
  document.getElementById('drive-nav-home-btn').style.display = active ? 'none' : (_driveNavHomeAddr ? 'flex' : 'none');
  document.getElementById('drive-nav-hud').style.display = active ? 'block' : 'none';
}

function driveStartStepTracking() {
  if (_driveNavWatchId !== null) navigator.geolocation.clearWatch(_driveNavWatchId);
  if (!navigator.geolocation || !_driveNavSteps.length) return;
  _driveNavWatchId = navigator.geolocation.watchPosition(function(pos) {
    if (!_driveNavSteps.length) return;
    var lat = pos.coords.latitude, lng = pos.coords.longitude;
    // Update user marker
    if (_driveNavUserMarker) {
      _driveNavUserMarker.setPosition({lat: lat, lng: lng});
      _driveNavUserMarker.setIcon({
        path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
        scale: 6, fillColor: '#00D4FF', fillOpacity: 1,
        strokeColor: '#fff', strokeWeight: 2,
        rotation: pos.coords.heading || 0
      });
    }
    // Check if close enough to advance to next step (within ~80m)
    var nextStep = _driveNavSteps[_driveNavCurrentStep + 1];
    if (nextStep && nextStep.start_location) {
      var dLat = lat - nextStep.start_location.lat();
      var dLng = lng - nextStep.start_location.lng();
      var dist = Math.sqrt(dLat*dLat + dLng*dLng) * 111000;
      if (dist < 80) {
        _driveNavCurrentStep++;
        driveUpdateGuidance(_driveNavSteps[_driveNavCurrentStep], _driveNavRouteLeg);
      }
    }
  }, function() {}, {enableHighAccuracy: true, maximumAge: 3000});
}

function driveNavCancel() {
  if (_driveNavWatchId !== null) {
    navigator.geolocation.clearWatch(_driveNavWatchId);
    _driveNavWatchId = null;
  }
  if (_driveNavRenderer) {
    _driveNavRenderer.setMap(null);
    if (_driveNavMap) _driveNavRenderer.setMap(_driveNavMap);
  }
  _driveNavSteps = [];
  _driveNavCurrentStep = 0;
  _driveNavRouteLeg = null;
  _drivePolyline = '';
  _driveTotalMiles = 0;
  driveClearAllPois();
  driveSetNavState(false);
  document.getElementById('drive-nav-dest').value = '';
}

// ---- POI along route ----
var _drivePolyline = '';
var _driveTotalMiles = 0;
var _driveGeoWaypoints = [];
var _drivePois = {};      // cat -> [{name,lat,lng,address,rating}, ...]
var _drivePoiMarkers = {}; // cat -> [google.maps.Marker, ...]
var _drivePoiActive = {}; // cat -> bool
var _drivePoiLoading = {}; // cat -> bool

var POI_COLORS = {
  food:      '#FF5722',
  starbucks: '#00704A',
  parks:     '#4CAF50',
  historic:  '#FF9800',
  family:    '#2196F3',
  gas:       '#9E9E9E'
};

function driveTogglePoi(cat) {
  var btn = document.getElementById('poi-btn-' + cat);
  if (!btn || !_driveNavMapsLoaded) return;
  if (_drivePoiLoading[cat]) return;

  if (_drivePoiActive[cat]) {
    // Hide markers
    var markers = _drivePoiMarkers[cat] || [];
    for (var i = 0; i < markers.length; i++) markers[i].setMap(null);
    _drivePoiActive[cat] = false;
    btn.classList.remove('active');
    return;
  }

  if (_drivePois[cat]) {
    // Already loaded — just re-show
    driveShowPoiMarkers(cat);
    return;
  }

  // Need to load — call API
  if (!_drivePolyline) return;
  _drivePoiLoading[cat] = true;
  btn.classList.add('loading');

  fetch('/api/nav/pois', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      encoded_polyline: _drivePolyline,
      categories: [cat],
      total_miles: _driveTotalMiles,
      geocoded_waypoints: _driveGeoWaypoints,
      parks_radius_miles: 25
    })
  }).then(function(r) { return r.json(); }).then(function(d) {
    _drivePoiLoading[cat] = false;
    btn.classList.remove('loading');
    var pois = (d.pois && d.pois[cat]) ? d.pois[cat] : [];
    // Merge NPS parks into parks category
    if (cat === 'parks' && d.nps_parks && d.nps_parks.length) {
      for (var j = 0; j < d.nps_parks.length; j++) {
        pois.push(d.nps_parks[j]);
      }
    }
    _drivePois[cat] = pois;
    var badge = document.getElementById('poi-badge-' + cat);
    if (badge) {
      badge.textContent = pois.length;
      badge.style.display = pois.length ? 'flex' : 'none';
    }
    driveShowPoiMarkers(cat);
  }).catch(function() {
    _drivePoiLoading[cat] = false;
    btn.classList.remove('loading');
  });
}

function driveShowPoiMarkers(cat) {
  if (!_driveNavMap) return;
  var pois = _drivePois[cat] || [];
  var existing = _drivePoiMarkers[cat] || [];
  for (var i = 0; i < existing.length; i++) existing[i].setMap(null);

  var color = POI_COLORS[cat] || '#ffffff';
  var markers = [];
  for (var k = 0; k < pois.length; k++) {
    var p = pois[k];
    var lat = p.lat || (p.geometry && p.geometry.location && p.geometry.location.lat);
    var lng = p.lng || (p.geometry && p.geometry.location && p.geometry.location.lng);
    if (!lat || !lng) continue;
    var marker = new google.maps.Marker({
      position: {lat: parseFloat(lat), lng: parseFloat(lng)},
      map: _driveNavMap,
      title: p.name || '',
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 9,
        fillColor: color,
        fillOpacity: 0.95,
        strokeColor: '#fff',
        strokeWeight: 1.5
      }
    });
    (function(marker, poi) {
      marker.addListener('click', function() {
        var iw = new google.maps.InfoWindow({
          content: '<div style="color:#000;font-size:13px;max-width:180px">' +
                   '<strong>' + escHtml(poi.name || '') + '</strong>' +
                   (poi.address ? '<br>' + escHtml(poi.address) : '') +
                   (poi.rating ? '<br>&#9733; ' + poi.rating : '') +
                   '</div>'
        });
        iw.open(_driveNavMap, marker);
      });
    })(marker, p);
    markers.push(marker);
  }
  _drivePoiMarkers[cat] = markers;
  _drivePoiActive[cat] = true;
  var btn = document.getElementById('poi-btn-' + cat);
  if (btn) btn.classList.add('active');
}

function driveClearAllPois() {
  var cats = ['food','starbucks','parks','historic','family','gas'];
  for (var i = 0; i < cats.length; i++) {
    var cat = cats[i];
    var markers = _drivePoiMarkers[cat] || [];
    for (var j = 0; j < markers.length; j++) markers[j].setMap(null);
    _drivePoiMarkers[cat] = [];
    _drivePoiActive[cat] = false;
    _drivePois[cat] = null;
    var btn = document.getElementById('poi-btn-' + cat);
    if (btn) { btn.classList.remove('active', 'loading'); }
    var badge = document.getElementById('poi-badge-' + cat);
    if (badge) badge.style.display = 'none';
  }
}

// ---- Kasa scene trigger ----
function triggerKasaScene(sceneId, btnEl) {
  if (!sceneId) return;
  if (btnEl.classList.contains('no-scene')) return;
  fetch('/api/kasa/scene', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({scene_id: sceneId})
  }).then(function() {
    btnEl.classList.add('success');
    var lblEl = btnEl.querySelector('span:last-child');
    var orig = lblEl.textContent;
    lblEl.textContent = '✓ Done';
    setTimeout(function() {
      btnEl.classList.remove('success');
      lblEl.textContent = orig;
    }, 2000);
  }).catch(function() {});
}
</script>
</body>
</html>
"""
