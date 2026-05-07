#include "luo_gate/ui.hpp"
#include "luo_gate/platform.hpp"
#include "luo_gate/security.hpp"

#include <sstream>
#include <algorithm>

namespace luo_gate {
namespace {

std::string html_escape(std::string_view text) {
    std::ostringstream out;
    for (char c : text) {
        switch (c) {
            case '&': out << "&amp;";  break;
            case '<': out << "&lt;";   break;
            case '>': out << "&gt;";   break;
            case '"': out << "&quot;"; break;
            case '\'':out << "&#39;";  break;
            default:  out << c;        break;
        }
    }
    return out.str();
}

std::string json_escape(std::string_view text) {
    std::ostringstream out;
    for (char c : text) {
        switch (c) {
            case '\\': out << "\\\\"; break;
            case '"':  out << "\\\""; break;
            case '\n': out << "\\n";  break;
            case '\r': out << "\\r";  break;
            case '\t': out << "\\t";  break;
            case '<':  out << "\\u003c"; break;
            case '>':  out << "\\u003e"; break;
            case '&':  out << "\\u0026"; break;
            default:   out << c;      break;
        }
    }
    return out.str();
}

// ─── Initial state JSON snapshot (hydrates the live UI on first load) ─────────
std::string initial_state_json(const App& app) {
    const auto s = app.summary();
    std::ostringstream o;
    o << "{";
    // summary
    o << "\"summary\":{"
      << "\"users\":"     << s.user_count    << ","
      << "\"agents\":"    << s.agent_count   << ","
      << "\"tasks\":"     << s.task_count    << ","
      << "\"computers\":" << s.computer_count<< ","
      << "\"files\":"     << s.file_count    << ","
      << "\"projects\":"  << s.project_count << ","
      << "\"memory\":"    << s.memory_count  << ","
      << "\"knowledge\":" << s.knowledge_count<< ","
      << "\"audit\":"     << s.audit_count   << ","
      << "\"active_user\":" << "\"" << json_escape(s.active_user) << "\","
      << "\"platform\":"     << "\"" << json_escape(s.platform)   << "\","
      << "\"session_stage\":" << "\"" << json_escape(s.session_stage) << "\","
      << "\"local_only\":" << (s.local_only_mode ? "true" : "false")
      << "},";

    // tasks
    o << "\"tasks\":[";
    bool first = true;
    for (const auto& t : app.tasks()) {
        if (!first) o << ",";
        first = false;
        o << "{"
          << "\"id\":\"" << json_escape(t.id) << "\","
          << "\"title\":\"" << json_escape(t.title) << "\","
          << "\"description\":\"" << json_escape(t.description) << "\","
          << "\"kind\":\"" << json_escape(t.kind) << "\","
          << "\"status\":\"" << json_escape(t.status) << "\","
          << "\"priority\":" << t.priority << ","
          << "\"step_cursor\":" << t.step_cursor << ","
          << "\"plan_size\":" << t.plan.size() << ","
          << "\"validated\":" << (t.validated ? "true" : "false") << ","
          << "\"confidence\":" << t.confidence << ","
          << "\"plan\":[";
        bool fp = true;
        for (const auto& step : t.plan) {
            if (!fp) o << ",";
            fp = false;
            o << "{\"actor\":\"" << json_escape(step.actor) << "\","
              << "\"action\":\"" << json_escape(step.action) << "\","
              << "\"detail\":\"" << json_escape(step.detail) << "\","
              << "\"status\":\"" << json_escape(step.status) << "\"}";
        }
        o << "],\"memory\":[";
        fp = true;
        for (const auto& m : t.memory) {
            if (!fp) o << ",";
            fp = false;
            o << "\"" << json_escape(m) << "\"";
        }
        o << "]}";
    }
    o << "],";

    // agents (first 100)
    o << "\"agents\":[";
    first = true;
    for (const auto& a : app.agents(100)) {
        if (!first) o << ",";
        first = false;
        o << "{"
          << "\"id\":\"" << json_escape(a.id) << "\","
          << "\"role\":\"" << json_escape(a.role) << "\","
          << "\"busy\":" << (a.busy ? "true" : "false") << ","
          << "\"health\":\"" << json_escape(a.health) << "\","
          << "\"reliability\":" << a.reliability << ","
          << "\"load\":" << a.load << ","
          << "\"task_id\":\"" << json_escape(a.task_id) << "\""
          << "}";
    }
    o << "],";

    // computer log
    o << "\"computer_log\":[";
    first = true;
    for (const auto& a : app.computer_log(50)) {
        if (!first) o << ",";
        first = false;
        o << "{"
          << "\"agent_id\":\"" << json_escape(a.agent_id) << "\","
          << "\"surface\":\"" << json_escape(a.surface) << "\","
          << "\"verb\":\"" << json_escape(a.verb) << "\","
          << "\"target\":\"" << json_escape(a.target) << "\","
          << "\"detail\":\"" << json_escape(a.detail.substr(0,80)) << "\","
          << "\"undone\":" << (a.undone ? "true" : "false")
          << "}";
    }
    o << "],";

    // pending approvals
    o << "\"pending_approvals\":[";
    first = true;
    for (const auto& p : app.pending_approvals()) {
        if (!first) o << ",";
        first = false;
        o << "\"" << json_escape(p) << "\"";
    }
    o << "]}";
    return o.str();
}

} // anonymous namespace

// ─────────────────────────────────────────────────────────────────────────────
// render_dashboard_html — single-page live dashboard
// ─────────────────────────────────────────────────────────────────────────────
std::string render_dashboard_html(const App& app) {
    const auto state_json = initial_state_json(app);
    const auto s = app.summary();

    std::ostringstream out;
    out << R"(<!doctype html><html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LUO COMPUTER</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#080d1a;--surface:#0f1629;--surface2:#162038;--border:#1e2d4d;
  --accent:#4c8eff;--accent2:#6ee7ff;--danger:#ff4d6a;--success:#3ddc84;
  --warn:#ffb84d;--text:#e6edf3;--muted:#5a6a8a;--radius:12px;
  --font:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  --mono:'JetBrains Mono','Fira Code',monospace;
}
body{font-family:var(--font);background:var(--bg);color:var(--text);min-height:100vh;font-size:13px;line-height:1.5}
h1,h2{font-size:1.3rem;font-weight:700;margin:0 0 4px}
h3{font-size:.9rem;font-weight:600;color:var(--accent2);margin:0 0 10px;text-transform:uppercase;letter-spacing:.05em}
p{color:var(--muted);margin:4px 0}
/* Topbar */
.topbar{background:var(--surface);border-bottom:1px solid var(--border);
  padding:8px 20px;display:flex;align-items:center;gap:12px;position:sticky;top:0;z-index:100}
.logo{font-weight:900;font-size:1rem;letter-spacing:.08em;color:var(--accent2);
  display:flex;align-items:center;gap:6px}
.logo-hex{font-size:1.2rem}
.topbar-right{margin-left:auto;display:flex;gap:6px;align-items:center}
/* Layout */
.shell{display:grid;grid-template-columns:200px 1fr;min-height:calc(100vh - 41px)}
.sidebar{background:var(--surface);border-right:1px solid var(--border);
  padding:12px 0;display:flex;flex-direction:column;gap:2px;overflow-y:auto}
.nav-item{padding:8px 16px;cursor:pointer;border-radius:0;font-size:.85rem;
  display:flex;align-items:center;gap:8px;color:var(--muted);border:none;
  background:none;width:100%;text-align:left;transition:all .1s}
.nav-item:hover{background:var(--surface2);color:var(--text)}
.nav-item.active{background:var(--surface2);color:var(--accent);border-right:2px solid var(--accent)}
.nav-sep{border-top:1px solid var(--border);margin:8px 12px}
.content{padding:20px;overflow-y:auto;max-height:calc(100vh - 41px)}
/* Cards */
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px}
.card+.card{margin-top:12px}
/* Stat row */
.stat-row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}
.stat{background:var(--surface);border:1px solid var(--border);border-radius:10px;
  padding:10px 16px;display:flex;flex-direction:column;align-items:center;min-width:80px;flex:1}
.stat-val{font-size:1.6rem;font-weight:800;color:var(--accent2);line-height:1}
.stat-lbl{font-size:.7rem;color:var(--muted);margin-top:2px;text-transform:uppercase;letter-spacing:.05em}
/* Buttons */
button,input,select,textarea{font-family:inherit;font-size:.84rem}
.btn{display:inline-flex;align-items:center;gap:5px;padding:6px 12px;
  border-radius:8px;border:1px solid var(--border);background:var(--surface2);
  color:var(--text);cursor:pointer;transition:all .12s;white-space:nowrap}
.btn:hover{border-color:var(--accent);background:var(--border)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
.btn.primary:hover{background:#3a7ae0}
.btn.danger{border-color:var(--danger);color:var(--danger)}
.btn.danger:hover{background:var(--danger);color:#fff}
.btn.success{border-color:var(--success);color:var(--success)}
.btn.sm{padding:3px 9px;font-size:.76rem;border-radius:6px}
.btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
/* Inputs */
.input{width:100%;padding:7px 10px;border-radius:8px;border:1px solid var(--border);
  background:var(--surface2);color:var(--text);outline:none}
.input:focus{border-color:var(--accent)}
/* Tags */
.tag{display:inline-block;padding:2px 7px;border-radius:4px;font-size:.7rem;font-weight:600}
.tag-running{background:rgba(76,142,255,.15);color:var(--accent)}
.tag-done{background:rgba(61,220,132,.12);color:var(--success)}
.tag-queued{background:rgba(90,106,138,.15);color:var(--muted)}
.tag-paused{background:rgba(255,184,77,.12);color:var(--warn)}
.tag-failed,.tag-cancelled{background:rgba(255,77,106,.12);color:var(--danger)}
/* Pills */
.pill{display:inline-flex;align-items:center;padding:4px 9px;border-radius:6px;
  background:var(--surface2);border:1px solid var(--border);font-size:.78rem;gap:5px}
.pill.ok{border-color:var(--success);color:var(--success)}
.pill.warn{border-color:var(--warn);color:var(--warn)}
.pill.err{border-color:var(--danger);color:var(--danger)}
/* Scrollable list */
.scroll-list{display:flex;flex-direction:column;gap:4px;max-height:340px;overflow-y:auto}
.scroll-list::-webkit-scrollbar{width:3px}
.scroll-list::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
/* Timeline */
.timeline{display:flex;flex-direction:column;gap:6px}
.tl-item{display:flex;gap:8px;align-items:flex-start}
.tl-dot{width:8px;height:8px;border-radius:50%;background:var(--muted);margin-top:5px;flex-shrink:0}
.tl-dot.done{background:var(--success)}
.tl-dot.active{background:var(--accent);box-shadow:0 0 6px var(--accent)}
.tl-dot.fail{background:var(--danger)}
/* Agent grid */
.agent-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:6px}
.agent-card{background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:8px;font-size:.78rem}
.agent-card.busy{border-color:var(--accent)}
.agent-card.stuck{border-color:var(--danger)}
.agent-card.degraded{border-color:var(--warn)}
/* Table */
.table{width:100%;border-collapse:collapse;font-size:.82rem}
.table th{text-align:left;padding:6px 8px;color:var(--muted);border-bottom:1px solid var(--border);font-weight:500}
.table td{padding:6px 8px;border-bottom:1px solid rgba(30,45,77,.5);vertical-align:middle}
.table tr:hover td{background:var(--surface2)}
/* Terminal */
.terminal{background:#020510;border-radius:8px;padding:10px;font-family:var(--mono);font-size:.78rem;max-height:200px;overflow-y:auto}
.terminal .cmd{color:var(--accent2)}
.terminal .out{color:var(--success)}
.terminal .err{color:var(--danger)}
/* Empty */
.empty{text-align:center;padding:28px;color:var(--muted)}
.empty-icon{font-size:1.8rem;margin-bottom:6px}
/* Badge */
.badge{display:inline-flex;align-items:center;justify-content:center;
  min-width:18px;height:18px;border-radius:9px;background:var(--danger);
  color:#fff;font-size:.68rem;font-weight:700;padding:0 5px}
/* Modal */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:500;
  align-items:center;justify-content:center}
.modal-overlay.open{display:flex}
.modal{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:20px;width:100%;max-width:480px;box-shadow:0 20px 60px rgba(0,0,0,.4)}
.modal h3{margin-bottom:14px}
.form-row{display:flex;flex-direction:column;gap:4px;margin-bottom:12px}
.form-row label{font-size:.78rem;color:var(--muted)}
/* Command palette */
.palette-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:999;
  align-items:flex-start;justify-content:center;padding-top:80px}
.palette-overlay.open{display:flex}
.palette{background:var(--surface);border:1px solid var(--accent);border-radius:14px;
  width:100%;max-width:540px;overflow:hidden;box-shadow:0 24px 80px rgba(0,0,0,.5)}
.palette input{width:100%;padding:14px 16px;background:transparent;border:none;
  color:var(--text);font-size:.95rem;outline:none}
.palette-list{border-top:1px solid var(--border);max-height:260px;overflow-y:auto}
.palette-item{padding:9px 16px;cursor:pointer;display:flex;gap:8px;align-items:center;font-size:.84rem}
.palette-item:hover,.palette-item.sel{background:var(--surface2)}
.palette-item-cat{font-size:.68rem;color:var(--muted);min-width:50px;text-transform:uppercase}
/* Toast */
.toast-area{position:fixed;bottom:20px;right:20px;display:flex;flex-direction:column;gap:6px;z-index:900}
.toast{background:var(--surface);border:1px solid var(--border);border-radius:8px;
  padding:10px 14px;font-size:.82rem;animation:slide-in .2s ease}
.toast.ok{border-color:var(--success);color:var(--success)}
.toast.err{border-color:var(--danger);color:var(--danger)}
@keyframes slide-in{from{transform:translateX(100%);opacity:0}to{transform:none;opacity:1}}
/* Live indicator */
.live-dot{width:7px;height:7px;border-radius:50%;background:var(--success);
  animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
/* Responsive */
@media(max-width:800px){.shell{grid-template-columns:1fr}.sidebar{display:none}}
</style>
</head><body>)";

    // ── Topbar ────────────────────────────────────────────────────────────────
    out << "<header class='topbar'>"
        << "<div class='logo'><span class='logo-hex'>⬡</span> LUO COMPUTER</div>"
        << "<span class='pill' id='tb-stage'>" << html_escape(s.session_stage) << "</span>"
        << "<span class='pill' style='gap:6px'><span class='live-dot'></span>live</span>"
        << "<div class='topbar-right'>"
        << "<button class='btn sm' onclick='openPalette()' title='Ctrl+K'>⌘ K</button>"
        << "<button class='btn sm primary' onclick='openNewTask()'>+ Task</button>"
        << "<span class='pill'>" << html_escape(s.active_user) << "</span>"
        << (s.local_only_mode ? "<span class='pill'>🔒 local</span>" : "")
        << "</div></header>";

    // ── Shell ─────────────────────────────────────────────────────────────────
    out << "<div class='shell'>";

    // Sidebar
    out << "<nav class='sidebar' role='navigation'>"
        << "<button class='nav-item active' onclick='nav(this,\"overview\")'>🏠 Overview</button>"
        << "<button class='nav-item' onclick='nav(this,\"tasks\")'>📋 Tasks"
        << "<span class='badge' id='nav-task-badge'>" << s.task_count << "</span></button>"
        << "<button class='nav-item' onclick='nav(this,\"agents\")'>🤖 Agents</button>"
        << "<button class='nav-item' onclick='nav(this,\"computer\")'>🖥 Computer</button>"
        << "<button class='nav-item' onclick='nav(this,\"terminal\")'>⌨ Terminal</button>"
        << "<button class='nav-item' onclick='nav(this,\"chat\")'>💬 Chat</button>"
        << "<div class='nav-sep'></div>"
        << "<button class='nav-item' onclick='nav(this,\"notes\")'>📝 Notes</button>"
        << "<button class='nav-item' onclick='nav(this,\"files\")'>📁 Files</button>"
        << "<button class='nav-item' onclick='nav(this,\"projects\")'>🚀 Projects</button>"
        << "<button class='nav-item' onclick='nav(this,\"datasets\")'>📊 Datasets</button>"
        << "<button class='nav-item' onclick='nav(this,\"memory\")'>🧠 Memory</button>"
        << "<button class='nav-item' onclick='nav(this,\"knowledge\")'>📚 Knowledge</button>"
        << "<div class='nav-sep'></div>"
        << "<button class='nav-item' onclick='nav(this,\"automations\")'>⏰ Automations</button>"
        << "<button class='nav-item' onclick='nav(this,\"personas\")'>🎭 Personas</button>"
        << "<button class='nav-item' onclick='nav(this,\"rules\")'>📜 Rules</button>"
        << "<button class='nav-item' onclick='nav(this,\"snapshots\")'>📸 Snapshots</button>"
        << "<button class='nav-item' onclick='nav(this,\"git\")'>🔀 Git</button>"
        << "<button class='nav-item' onclick='nav(this,\"system\")'>📡 System</button>"
        << "<div class='nav-sep'></div>"
        << "<button class='nav-item' onclick='nav(this,\"search\")'>🔍 Search</button>"
        << "<button class='nav-item' onclick='nav(this,\"notifications\")'>🔔 Notifications"
        << "<span class='badge' id='nav-notif-badge'></span></button>"
        << "<button class='nav-item' onclick='nav(this,\"audit\")'>📋 Audit</button>"
        << "<button class='nav-item' onclick='nav(this,\"settings\")'>⚙ Settings</button>"
        << "</nav>";

    // Content area - all panels defined in JS for live updates
    out << "<div class='content' id='content'>"
        << "<div id='loading' style='padding:40px;text-align:center;color:var(--muted)'>Loading...</div>"
        << "</div></div>";

    // Toast area
    out << "<div class='toast-area' id='toasts'></div>";

    // New Task modal
    out << R"(
<div class='modal-overlay' id='modal-new-task'>
<div class='modal'>
<h3>📋 New Task</h3>
<div class='form-row'><label>Title</label>
<input class='input' id='nt-title' placeholder='What needs to be done?'></div>
<div class='form-row'><label>Description</label>
<textarea class='input' id='nt-desc' rows='3' placeholder='Optional detail...'></textarea></div>
<div class='form-row'><label>Kind</label>
<select class='input' id='nt-kind'>
<option value='research'>Research</option>
<option value='build'>Build</option>
<option value='ops'>Ops</option>
<option value='ui'>UI</option>
<option value='general'>General</option>
</select></div>
<div class='form-row'><label>Priority (1=highest, 10=lowest)</label>
<input class='input' id='nt-priority' type='number' min='1' max='10' value='5'></div>
<div style='display:flex;gap:8px;justify-content:flex-end;margin-top:4px'>
<button class='btn' onclick='closeNewTask()'>Cancel</button>
<button class='btn primary' onclick='submitNewTask()'>Create Task</button>
</div></div></div>)";

    // Command palette
    out << R"(
<div class='palette-overlay' id='palette'>
<div class='palette'>
<input id='palette-input' placeholder='Command or search...' autocomplete='off'>
<div class='palette-list' id='palette-list'></div>
</div></div>)";

    // Embed initial state + JS app
    out << "<script>const __STATE=" << state_json << ";</script>";

    out << R"JS(<script>
// ─── State ───────────────────────────────────────────────────────────────────
let state = __STATE;
let currentPanel = 'overview';
let sseConnected = false;

// ─── API ─────────────────────────────────────────────────────────────────────
async function api(method, path, params={}) {
  try {
    let url = path;
    if (method === 'GET' && Object.keys(params).length) {
      url += '?' + new URLSearchParams(params).toString();
    }
    const opts = { method };
    if (method === 'POST' && Object.keys(params).length) {
      url += '?' + new URLSearchParams(params).toString();
    }
    const res = await fetch(url, opts);
    const data = await res.json();
    return data;
  } catch(e) {
    toast('Network error: ' + e.message, 'err');
    return null;
  }
}

async function refreshState() {
  const [summary, tasks, agents, log] = await Promise.all([
    api('GET', '/api/summary'),
    api('GET', '/api/tasks'),
    api('GET', '/api/agents'),
    api('GET', '/api/computer/log'),
  ]);
  if (summary) state.summary = summary;
  if (tasks)   state.tasks   = tasks;
  if (agents)  state.agents  = agents;
  if (log)     state.computer_log = log;
  updateTopbar();
  renderPanel(currentPanel);
}

// ─── SSE live updates ─────────────────────────────────────────────────────────
function connectSSE() {
  const es = new EventSource('/api/events');
  es.onmessage = (e) => {
    try {
      const d = JSON.parse(e.data);
      if (d.agents !== undefined) state.summary.agents = d.agents;
      if (d.tasks  !== undefined) state.summary.tasks  = d.tasks;
      if (d.stage  !== undefined) state.summary.session_stage = d.stage;
      if (d.audit  !== undefined) state.summary.audit  = d.audit;
      updateTopbar();
      // Full refresh every 10s via SSE cadence
      if (!sseConnected) { sseConnected = true; refreshState(); }
    } catch {}
  };
  es.onerror = () => { sseConnected = false; setTimeout(connectSSE, 3000); };
}

// ─── Topbar live ─────────────────────────────────────────────────────────────
function updateTopbar() {
  const el = document.getElementById('tb-stage');
  if (el) el.textContent = state.summary.session_stage || 'idle';
  const badge = document.getElementById('nav-task-badge');
  if (badge) badge.textContent = state.summary.tasks || 0;
}

// ─── Toast ───────────────────────────────────────────────────────────────────
function toast(msg, type='ok') {
  const area = document.getElementById('toasts');
  const el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  area.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ─── Navigation ──────────────────────────────────────────────────────────────
function nav(btn, panel) {
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentPanel = panel;
  renderPanel(panel);
}

function renderPanel(panel) {
  const content = document.getElementById('content');
  switch(panel) {
    case 'overview':    content.innerHTML = renderOverview();    break;
    case 'tasks':       content.innerHTML = renderTasks();       break;
    case 'agents':      content.innerHTML = renderAgents();      break;
    case 'computer':    content.innerHTML = renderComputer();    break;
    case 'chat':        content.innerHTML = renderChat();        break;
    case 'notes':       content.innerHTML = renderNotes();       break;
    case 'files':       content.innerHTML = renderFiles();       break;
    case 'projects':    content.innerHTML = renderProjects();    break;
    case 'datasets':    content.innerHTML = renderDatasets();    break;
    case 'memory':      content.innerHTML = renderMemory();      break;
    case 'knowledge':   content.innerHTML = renderKnowledge();   break;
    case 'automations': content.innerHTML = renderAutomations(); break;
    case 'personas':    content.innerHTML = renderPersonas();    break;
    case 'rules':       content.innerHTML = renderRules();       break;
    case 'snapshots':   content.innerHTML = renderSnapshots();   break;
    case 'system':      content.innerHTML = renderSystem();      break;
    case 'git':         content.innerHTML = renderGit();         break;
    case 'search':      content.innerHTML = renderSearch();      break;
    case 'notifications': content.innerHTML = renderNotifications(); break;
    case 'terminal':    content.innerHTML = renderTerminalPanel(); break;
    case 'audit':       content.innerHTML = renderAudit();       break;
    case 'settings':    content.innerHTML = renderSettings();    break;
    default:            content.innerHTML = renderOverview();
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function tag(status) {
  return `<span class="tag tag-${status}">${status}</span>`;
}

function escHtml(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ─── Overview panel ──────────────────────────────────────────────────────────
function renderOverview() {
  const s = state.summary;
  const stats = [
    ['🤖', s.agents,   'Agents'],
    ['📋', s.tasks,    'Tasks'],
    ['🖥', s.computers,'Computers'],
    ['📁', s.files,    'Files'],
    ['🚀', s.projects, 'Projects'],
    ['🧠', s.memory,   'Memory'],
    ['📚', s.knowledge,'Knowledge'],
    ['🔍', s.audit,    'Audit'],
  ];
  let h = '<div class="stat-row">';
  stats.forEach(([icon,val,lbl]) => {
    h += `<div class="stat"><div class="stat-val">${val??0}</div><div class="stat-lbl">${lbl}</div></div>`;
  });
  h += '</div>';

  // Recent tasks
  h += '<div class="card"><h3>Active Tasks</h3>';
  const active = (state.tasks||[]).filter(t => t.status === 'running' || t.status === 'queued');
  if (!active.length) h += '<div class="empty"><div class="empty-icon">📋</div>No active tasks</div>';
  else {
    h += '<div class="scroll-list">';
    active.forEach(t => {
      h += `<div style="display:flex;align-items:center;gap:8px;padding:8px;background:var(--surface2);border-radius:8px;cursor:pointer" onclick="navToTask('${escHtml(t.id)}')">
        ${tag(t.status)}
        <span style="flex:1;font-weight:600">${escHtml(t.title)}</span>
        <span style="color:var(--muted);font-size:.75rem">P${t.priority} · step ${t.step_cursor}/${t.plan_size}</span>
        <button class="btn sm" onclick="event.stopPropagation();tickTask('${escHtml(t.id)}')">▶ tick</button>
        <button class="btn sm danger" onclick="event.stopPropagation();cancelTask('${escHtml(t.id)}')">✕</button>
      </div>`;
    });
    h += '</div>';
  }
  h += '</div>';

  // Computer log preview
  h += '<div class="card" style="margin-top:12px"><h3>Computer Activity</h3>';
  const log = (state.computer_log||[]).slice(-8).reverse();
  if (!log.length) h += '<div class="empty"><div class="empty-icon">🖥</div>No activity</div>';
  else {
    h += '<div class="timeline">';
    log.forEach(a => {
      const cls = a.undone ? 'tl-dot' : 'tl-dot done';
      h += `<div class="tl-item">
        <div class="${cls}"></div>
        <div style="font-size:.8rem">
          <strong>${escHtml(a.agent_id)}</strong>
          <span class="pill" style="font-size:.7rem">${escHtml(a.verb)}</span>
          ${escHtml(a.target)}
          ${a.detail ? `<span style="color:var(--muted)"> — ${escHtml(a.detail)}</span>` : ''}
        </div>
      </div>`;
    });
    h += '</div>';
  }
  h += '</div>';

  return h;
}

// ─── Tasks panel ─────────────────────────────────────────────────────────────
function renderTasks() {
  const tasks = state.tasks || [];
  let h = `<div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
    <input class="input" id="task-search" placeholder="Search tasks..." style="max-width:200px" oninput="filterTaskList()">
    <select class="input" id="task-status-filter" onchange="filterTaskList()" style="max-width:130px">
      <option value="">All status</option>
      <option>queued</option><option>running</option><option>done</option>
      <option>paused</option><option>failed</option><option>cancelled</option>
    </select>
    <button class="btn primary" onclick="openNewTask()">+ New Task</button>
    <button class="btn" onclick="refreshState()">↻ Refresh</button>
  </div>
  <div style="display:grid;grid-template-columns:240px 1fr;gap:12px">
  <div class="scroll-list" id="task-list-col" style="max-height:calc(100vh - 180px)">`;

  tasks.forEach((t,i) => {
    h += `<div class="task-row" data-status="${escHtml(t.status)}" data-title="${escHtml(t.title)}"
      style="padding:10px;background:var(--surface);border:1px solid var(--border);border-radius:8px;cursor:pointer"
      onclick="showTaskDetail(${i})">
      <div style="display:flex;align-items:center;gap:6px">
        ${tag(t.status)}
        <span style="font-weight:600;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(t.title)}</span>
      </div>
      <div style="font-size:.72rem;color:var(--muted);margin-top:2px">${escHtml(t.kind)} · P${t.priority}</div>
    </div>`;
  });
  if (!tasks.length) h += '<div class="empty"><div class="empty-icon">📋</div>No tasks</div>';
  h += '</div>';

  // Detail panel
  h += '<div id="task-detail" class="card"><div class="empty"><div class="empty-icon">👆</div>Select a task</div></div>';
  h += '</div>';

  h += `<script>
window.filterTaskList = function() {
  const q = document.getElementById('task-search').value.toLowerCase();
  const st = document.getElementById('task-status-filter').value;
  document.querySelectorAll('.task-row').forEach(r => {
    const ok = (!q || r.dataset.title.toLowerCase().includes(q)) && (!st || r.dataset.status === st);
    r.style.display = ok ? '' : 'none';
  });
};
window.showTaskDetail = function(i) {
  const t = (state.tasks||[])[i];
  if (!t) return;
  const detail = document.getElementById('task-detail');
  if (!detail) return;
  let dh = \`<h3>\${escHtml(t.title)}</h3>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px">
      \${tag(t.status)}
      <span class="pill">\${escHtml(t.kind)}</span>
      <span class="pill">Priority \${t.priority}</span>
      \${t.validated ? "<span class='pill ok'>✓ validated</span>" : ""}
    </div>
    <p style="margin-bottom:12px">\${escHtml(t.description||'')}</p>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px">\`;
  if (t.status === 'queued' || t.status === 'running')
    dh += \`<button class="btn sm" onclick="tickTask('\${t.id}')">▶ Tick</button>
           <button class="btn sm" onclick="pauseTask('\${t.id}')">⏸ Pause</button>
           <button class="btn sm danger" onclick="cancelTask('\${t.id}')">✕ Cancel</button>\`;
  if (t.status === 'paused')
    dh += \`<button class="btn sm success" onclick="resumeTask('\${t.id}')">▶ Resume</button>
           <button class="btn sm danger" onclick="cancelTask('\${t.id}')">✕ Cancel</button>\`;
  if (t.status === 'cancelled' || t.status === 'failed' || t.status === 'done')
    dh += \`<button class="btn sm" onclick="reopenTask('\${t.id}')">↺ Reopen</button>\`;
  dh += \`<button class="btn sm" onclick="validateTask('\${t.id}')">✓ Validate</button></div>\`;

  // Plan steps
  dh += \`<h3>Plan (\${t.step_cursor}/\${t.plan_size} steps)</h3><div class="timeline">\`;
  (t.plan||[]).forEach((step, idx) => {
    const done = idx < t.step_cursor;
    const active = idx === t.step_cursor;
    const cls = done ? 'done' : active ? 'active' : '';
    dh += \`<div class="tl-item">
      <div class="tl-dot \${cls}"></div>
      <div style="font-size:.8rem"><strong>\${escHtml(step.actor)}</strong> \${escHtml(step.action)}
        \${step.detail ? \`<span style="color:var(--muted)"> — \${escHtml(step.detail)}</span>\` : ''}
        \${active ? '<span style="color:var(--accent);font-size:.72rem"> ▶ current</span>' : ''}
      </div>
    </div>\`;
  });
  dh += '</div>';

  if ((t.memory||[]).length) {
    dh += '<h3 style="margin-top:12px">Agent Memory</h3><div class="scroll-list" style="max-height:120px">';
    t.memory.forEach(m => { dh += \`<div class="pill" style="font-size:.75rem">\${escHtml(m)}</div>\`; });
    dh += '</div>';
  }
  detail.innerHTML = dh;
};
if ((state.tasks||[]).length) showTaskDetail(0);
</script>`;

  return h;
}

// ─── Agents panel ─────────────────────────────────────────────────────────────
function renderAgents() {
  const agents = state.agents || [];
  const busy = agents.filter(a => a.busy).length;
  const stuck = agents.filter(a => a.health === 'stuck').length;
  let h = `<div style="display:flex;gap:8px;align-items:center;margin-bottom:14px;flex-wrap:wrap">
    <span class="pill ok">${agents.length} loaded</span>
    <span class="pill ${busy ? 'warn' : ''}">${busy} busy</span>
    ${stuck ? `<span class="pill err">${stuck} stuck</span>` : ''}
    <span style="color:var(--muted);font-size:.78rem">Full swarm: ${state.summary.agents} agents</span>
    <button class="btn sm danger" style="margin-left:auto" onclick="killAgents()">🛑 Kill all</button>
    <button class="btn sm" onclick="refreshState()">↻ Refresh</button>
  </div>`;

  // Role summary
  const roleCounts = {};
  agents.forEach(a => { roleCounts[a.role] = (roleCounts[a.role]||0) + 1; });
  h += '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px">';
  Object.entries(roleCounts).forEach(([role, count]) => {
    h += `<span class="pill">${escHtml(role)} <strong>${count}</strong></span>`;
  });
  h += '</div>';

  h += '<div class="agent-grid">';
  agents.forEach(a => {
    const cls = a.health === 'stuck' ? 'stuck' : a.health === 'degraded' ? 'degraded' : a.busy ? 'busy' : '';
    h += `<div class="agent-card ${cls}">
      <div style="font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.8rem">${escHtml(a.id)}</div>
      <div style="color:var(--muted);font-size:.72rem">${escHtml(a.role)}</div>
      <div style="display:flex;gap:4px;margin-top:4px;flex-wrap:wrap">
        <span class="tag ${a.busy ? 'tag-running' : 'tag-done'}">${a.busy ? 'busy' : 'free'}</span>
        <span style="font-size:.68rem;color:var(--muted)">${Math.round(a.reliability*100)}%</span>
      </div>
      ${a.task_id ? `<div style="font-size:.68rem;color:var(--accent);margin-top:2px">${escHtml(a.task_id)}</div>` : ''}
    </div>`;
  });
  h += '</div>';
  return h;
}

// ─── Computer panel ───────────────────────────────────────────────────────────
function renderComputer() {
  const log = state.computer_log || [];
  let h = `<div style="display:flex;gap:8px;margin-bottom:12px">
    <button class="btn sm" onclick="undoComputer()">↩ Undo last</button>
    <button class="btn sm" onclick="refreshState()">↻ Refresh</button>
  </div>`;

  h += '<div class="card"><h3>Action Timeline</h3>';
  h += '<div class="scroll-list" style="max-height:400px">';
  if (!log.length) h += '<div class="empty"><div class="empty-icon">🖥</div>No computer actions yet</div>';
  [...log].reverse().forEach((a, i) => {
    const cls = a.undone ? 'tl-dot' : 'tl-dot done';
    h += `<div class="tl-item" style="${a.undone ? 'opacity:.4' : ''}">
      <div class="${cls}"></div>
      <div style="font-size:.8rem">
        <span style="color:var(--muted);font-size:.7rem">#${log.length - i} · ${escHtml(a.surface)}</span>
        <strong style="margin-left:4px">${escHtml(a.agent_id)}</strong>
        <span class="pill" style="font-size:.7rem;margin:0 4px">${escHtml(a.verb)}</span>
        ${escHtml(a.target)}
        ${a.detail ? `<span style="color:var(--muted)"> — ${escHtml(a.detail)}</span>` : ''}
        ${a.undone ? '<span style="color:var(--danger);font-size:.7rem"> [undone]</span>' : ''}
      </div>
    </div>`;
  });
  h += '</div></div>';

  // Browser nav form
  h += `<div class="card" style="margin-top:12px">
    <h3>Browser Navigation</h3>
    <div style="display:flex;gap:8px">
      <input class="input" id="browser-url" placeholder="https://..." style="flex:1">
      <input class="input" id="browser-title" placeholder="Page title" style="max-width:180px">
      <button class="btn primary" onclick="navigateBrowser()">Navigate</button>
    </div>
  </div>`;

  // Terminal form
  h += `<div class="card" style="margin-top:12px">
    <h3>Terminal</h3>
    <div style="display:flex;gap:8px;margin-bottom:8px">
      <input class="input" id="term-cmd" placeholder="Command..." style="flex:1" onkeydown="if(event.key==='Enter')runCmd()">
      <input class="input" id="term-out" placeholder="Output..." style="flex:1">
      <button class="btn primary" onclick="runCmd()">Run</button>
    </div>
  </div>`;

  return h;
}

// ─── Files panel ──────────────────────────────────────────────────────────────
async function renderFilesAsync() {
  const data = await api('GET', '/api/files');
  if (!data) return;
  const content = document.getElementById('content');
  let h = `<div style="display:flex;gap:8px;margin-bottom:12px">
    <input class="input" id="file-search" placeholder="Search files..." style="max-width:220px" oninput="liveSearchFiles()">
    <button class="btn" onclick="renderFilesAsync()">↻ Refresh</button>
  </div>
  <div class="card">
  <table class="table">
  <thead><tr><th>Name</th><th>Size</th><th>Versions</th><th>Scope</th></tr></thead>
  <tbody id="file-tbody">`;
  data.forEach(f => {
    h += `<tr>
      <td><code style="font-size:.8rem">${escHtml(f.name)}</code></td>
      <td style="color:var(--muted)">${f.size} B</td>
      <td style="color:var(--muted)">${f.version_count}</td>
      <td style="color:var(--muted)">${escHtml(f.project_scope||'—')}</td>
    </tr>`;
  });
  if (!data.length) h += '<tr><td colspan="4"><div class="empty">No files</div></td></tr>';
  h += '</tbody></table></div>';
  content.innerHTML = h;
}
function renderFiles() { setTimeout(renderFilesAsync, 0); return '<div class="empty">Loading files...</div>'; }
window.liveSearchFiles = async function() {
  const q = document.getElementById('file-search').value;
  if (!q) { renderFilesAsync(); return; }
  const data = await api('GET', '/api/files', {q});
  if (!data) return;
  const tbody = document.getElementById('file-tbody');
  if (!tbody) return;
  tbody.innerHTML = data.map(f => `<tr><td><code>${escHtml(f.name)}</code></td><td>${f.size} B</td></tr>`).join('');
};

// ─── Projects panel ───────────────────────────────────────────────────────────
async function renderProjectsAsync() {
  const data = await api('GET', '/api/projects');
  if (!data) return;
  let h = '<div class="scroll-list">';
  data.forEach(p => {
    const ok = p.last_exit_code === 0;
    const ran = p.last_exit_code >= 0;
    h += `<div class="card">
      <div style="display:flex;align-items:center;gap:8px">
        <strong>${escHtml(p.name)}</strong>
        ${p.template_kind ? `<span class="pill">${escHtml(p.template_kind)}</span>` : ''}
        ${ran ? `<span class="pill ${ok ? 'ok' : 'err'}">exit ${p.last_exit_code}</span>` : ''}
        <span style="color:var(--muted);font-size:.75rem">${p.run_count} runs</span>
        ${p.executable ? `<button class="btn sm primary" style="margin-left:auto" onclick="runProject('${escHtml(p.id)}')">▶ Run</button>` : ''}
      </div>
      <code style="display:block;font-size:.76rem;color:var(--muted);margin-top:6px">$ ${escHtml(p.command)}</code>
    </div>`;
  });
  if (!data.length) h += '<div class="empty"><div class="empty-icon">🚀</div>No projects</div>';
  h += '</div>';
  const content = document.getElementById('content');
  content.innerHTML = h;
}
function renderProjects() { setTimeout(renderProjectsAsync, 0); return '<div class="empty">Loading...</div>'; }

// ─── Memory panel ─────────────────────────────────────────────────────────────
async function renderMemoryAsync() {
  const data = await api('GET', '/api/memory');
  if (!data) return;
  let h = `<div style="display:flex;gap:8px;margin-bottom:12px">
    <input class="input" id="mem-search" placeholder="Search memory..." style="max-width:240px" oninput="searchMemory()">
    <div style="margin-left:auto;display:flex;gap:8px">
      <button class="btn sm" onclick="summarizeMemory()">Summarize old</button>
    </div>
  </div>
  <div class="card"><h3>Memory Store (${data.length})</h3>
  <div class="scroll-list" id="mem-list">`;
  data.forEach(m => {
    h += `<div class="pill" style="flex-direction:column;align-items:flex-start;padding:8px">
      <span class="tag tag-queued" style="margin-bottom:4px">${escHtml(m.kind)}</span>
      <span style="font-size:.8rem">${escHtml(m.content)}</span>
      ${m.summarized ? '<span style="font-size:.7rem;color:var(--warn)">[summarized]</span>' : ''}
    </div>`;
  });
  if (!data.length) h += '<div class="empty">No memory entries</div>';
  h += '</div></div>';
  document.getElementById('content').innerHTML = h;
}
function renderMemory() { setTimeout(renderMemoryAsync, 0); return '<div class="empty">Loading...</div>'; }
window.searchMemory = async function() {
  const q = document.getElementById('mem-search').value;
  if (!q) { renderMemoryAsync(); return; }
  const data = await api('GET', '/api/memory', {q});
  if (!data) return;
  const list = document.getElementById('mem-list');
  if (list) list.innerHTML = data.map(m => `<div class="pill" style="font-size:.8rem">${escHtml(m.content)}</div>`).join('');
};

// ─── Knowledge panel ──────────────────────────────────────────────────────────
async function renderKnowledgeAsync() {
  const data = await api('GET', '/api/knowledge');
  if (!data) return;
  let h = `<div style="display:flex;gap:8px;margin-bottom:12px">
    <input class="input" placeholder="Search knowledge..." style="max-width:240px" oninput="searchKB(this.value)">
    <button class="btn primary" onclick="addKnowledge()">+ Add</button>
  </div>
  <div class="card">
  <div class="scroll-list" id="kb-list">`;
  data.forEach(k => {
    h += `<div style="padding:10px;background:var(--surface2);border-radius:8px">
      <div style="font-weight:600">${escHtml(k.title)}</div>
      <div style="font-size:.78rem;color:var(--muted);margin-top:3px">${escHtml(k.body)}</div>
    </div>`;
  });
  if (!data.length) h += '<div class="empty"><div class="empty-icon">📚</div>No knowledge entries</div>';
  h += '</div></div>';
  document.getElementById('content').innerHTML = h;
}
function renderKnowledge() { setTimeout(renderKnowledgeAsync, 0); return '<div class="empty">Loading...</div>'; }
window.searchKB = async function(q) {
  if (!q) { renderKnowledgeAsync(); return; }
  const data = await api('GET', '/api/knowledge', {q});
  const list = document.getElementById('kb-list');
  if (list && data) list.innerHTML = data.map(k => `<div style="padding:8px;background:var(--surface2);border-radius:8px"><strong>${escHtml(k.title)}</strong><p>${escHtml(k.body)}</p></div>`).join('');
};

// ─── Audit panel ──────────────────────────────────────────────────────────────
async function renderAuditAsync() {
  const data = await api('GET', '/api/audit');
  if (!data) return;
  let h = `<div class="card"><h3>Audit Log (${data.length} events)</h3>
  <div class="scroll-list" style="max-height:500px">`;
  [...data].reverse().forEach(e => {
    h += `<div style="display:flex;gap:8px;padding:6px;font-size:.8rem;border-bottom:1px solid var(--border)">
      <span style="color:var(--muted);min-width:80px">${escHtml(e.actor)}</span>
      <strong>${escHtml(e.action)}</strong>
      <span style="color:var(--muted)">${escHtml(e.detail)}</span>
    </div>`;
  });
  if (!data.length) h += '<div class="empty">No audit events</div>';
  h += '</div></div>';
  document.getElementById('content').innerHTML = h;
}
function renderAudit() { setTimeout(renderAuditAsync, 0); return '<div class="empty">Loading...</div>'; }

// ─── Settings panel ───────────────────────────────────────────────────────────
function renderSettings() {
  const s = state.summary;
  return `<div class="card"><h3>Session</h3>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button class="btn" onclick="pauseSession()">⏸ Pause session</button>
      <button class="btn success" onclick="resumeSession()">▶ Resume session</button>
      <button class="btn" onclick="saveState()">💾 Save</button>
    </div>
  </div>
  <div class="card" style="margin-top:12px"><h3>Agent Control</h3>
    <div style="display:flex;gap:8px">
      <button class="btn danger" onclick="killAgents()">🛑 Kill all agents</button>
    </div>
  </div>
  <div class="card" style="margin-top:12px"><h3>Status</h3>
    <div style="font-size:.84rem;display:flex;flex-direction:column;gap:6px">
      <div>User: <strong>${escHtml(s.active_user)}</strong></div>
      <div>Platform: <strong>${escHtml(s.platform)}</strong></div>
      <div>Session: <strong>${escHtml(s.session_stage)}</strong></div>
      <div>Local only: <strong>${s.local_only ? 'yes' : 'no'}</strong></div>
    </div>
  </div>`;
}

// ─── Actions ─────────────────────────────────────────────────────────────────
async function tickTask(id) {
  const r = await api('POST', `/api/tasks/${id}/tick`);
  if (r?.ok) { toast('Task ticked'); await refreshState(); renderPanel(currentPanel); }
  else toast('Tick failed', 'err');
}
async function cancelTask(id) {
  if (!confirm('Cancel this task?')) return;
  const r = await api('POST', `/api/tasks/${id}/cancel`);
  if (r?.ok) { toast('Task cancelled'); await refreshState(); renderPanel(currentPanel); }
  else toast('Cancel failed', 'err');
}
async function pauseTask(id) {
  const r = await api('POST', `/api/tasks/${id}/pause`);
  if (r?.ok) { toast('Task paused'); await refreshState(); renderPanel(currentPanel); }
  else toast('Pause failed', 'err');
}
async function resumeTask(id) {
  const r = await api('POST', `/api/tasks/${id}/resume`);
  if (r?.ok) { toast('Task resumed'); await refreshState(); renderPanel(currentPanel); }
  else toast('Resume failed', 'err');
}
async function reopenTask(id) {
  const r = await api('POST', `/api/tasks/${id}/reopen`);
  if (r?.ok) { toast('Task reopened'); await refreshState(); renderPanel(currentPanel); }
  else toast('Reopen failed', 'err');
}
async function validateTask(id) {
  const r = await api('POST', `/api/tasks/${id}/validate`);
  if (r?.ok) { toast('Task validated ✓'); await refreshState(); renderPanel(currentPanel); }
  else toast('Validate failed', 'err');
}
async function killAgents() {
  if (!confirm('Kill all agents?')) return;
  const r = await api('POST', '/api/agents/kill');
  if (r?.ok) { toast('All agents killed', 'err'); await refreshState(); renderPanel(currentPanel); }
}
async function navigateBrowser() {
  const url = document.getElementById('browser-url').value;
  const title = document.getElementById('browser-title').value || url;
  if (!url) { toast('URL required', 'err'); return; }
  const r = await api('POST', '/api/computer/browser', {url, title});
  if (r?.ok) { toast('Browser navigated'); await refreshState(); }
  else toast('Failed', 'err');
}
async function runCmd() {
  const command = document.getElementById('term-cmd').value;
  const output = document.getElementById('term-out').value;
  if (!command) { toast('Command required', 'err'); return; }
  const r = await api('POST', '/api/computer/terminal', {command, output, exit_code: '0'});
  if (r?.ok) { toast('Command recorded'); document.getElementById('term-cmd').value = ''; document.getElementById('term-out').value = ''; }
  else toast('Failed', 'err');
}
async function undoComputer() {
  const r = await api('POST', '/api/computer/undo');
  if (r?.ok) { toast('Last action undone'); await refreshState(); renderPanel(currentPanel); }
  else toast('Nothing to undo', 'err');
}
async function runProject(id) {
  const r = await api('POST', `/api/projects/${id}/run`);
  if (r?.ok) { toast('Project run complete ✓'); renderProjectsAsync(); }
  else toast('Run failed', 'err');
}
async function pauseSession() {
  const r = await api('POST', '/api/session/pause');
  if (r?.ok) { toast('Session paused'); await refreshState(); }
}
async function resumeSession() {
  const r = await api('POST', '/api/session/resume');
  if (r?.ok) { toast('Session resumed ▶'); await refreshState(); }
}
async function saveState() {
  const r = await api('POST', '/api/save');
  if (r?.ok) toast('State saved 💾');
  else toast('Save failed', 'err');
}
async function summarizeMemory() {
  const r = await api('POST', '/api/memory/summarize');
  if (r?.ok) { toast('Memories summarized'); renderMemoryAsync(); }
}
async function addKnowledge() {
  const title = prompt('Knowledge title:');
  if (!title) return;
  const body = prompt('Body:') || '';
  const r = await api('POST', '/api/knowledge', {title, body});
  if (r?.ok) { toast('Knowledge added ✓'); renderKnowledgeAsync(); }
  else toast('Failed', 'err');
}

// ─── New Task modal ───────────────────────────────────────────────────────────
window.openNewTask = function() {
  document.getElementById('modal-new-task').classList.add('open');
  document.getElementById('nt-title').focus();
};
window.closeNewTask = function() {
  document.getElementById('modal-new-task').classList.remove('open');
};
window.submitNewTask = async function() {
  const title = document.getElementById('nt-title').value.trim();
  if (!title) { toast('Title required', 'err'); return; }
  const desc = document.getElementById('nt-desc').value;
  const kind = document.getElementById('nt-kind').value;
  const priority = document.getElementById('nt-priority').value;
  const r = await api('POST', '/api/tasks', {title, description: desc, kind, priority});
  if (r?.ok) {
    toast('Task created ✓');
    closeNewTask();
    await refreshState();
    nav(document.querySelector('.nav-item[onclick*="tasks"]'), 'tasks');
  } else toast('Failed to create task', 'err');
};
document.getElementById('modal-new-task').addEventListener('click', e => {
  if (e.target === e.currentTarget) closeNewTask();
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeNewTask(); });

// ─── Navigate to task detail ──────────────────────────────────────────────────
window.navToTask = function(id) {
  const idx = (state.tasks||[]).findIndex(t => t.id === id);
  nav(document.querySelector('.nav-item[onclick*="tasks"]'), 'tasks');
  setTimeout(() => { if (window.showTaskDetail) showTaskDetail(idx >= 0 ? idx : 0); }, 50);
};

// ─── Command palette ─────────────────────────────────────────────────────────
const COMMANDS = [
  {cat:'task',   label:'Create new task',         fn: () => openNewTask()},
  {cat:'task',   label:'Tick all tasks',           fn: async () => { const r = await api('POST','/api/tasks/__tick'); toast('Ticked'); await refreshState(); }},
  {cat:'agent',  label:'Kill all agents',          fn: () => killAgents()},
  {cat:'session',label:'Pause session',            fn: () => pauseSession()},
  {cat:'session',label:'Resume session',           fn: () => resumeSession()},
  {cat:'data',   label:'Save state',               fn: () => saveState()},
  {cat:'data',   label:'Summarize old memory',     fn: () => summarizeMemory()},
  {cat:'nav',    label:'Go to Overview',           fn: () => nav(document.querySelectorAll('.nav-item')[0], 'overview')},
  {cat:'nav',    label:'Go to Tasks',              fn: () => nav(document.querySelectorAll('.nav-item')[1], 'tasks')},
  {cat:'nav',    label:'Go to Agents',             fn: () => nav(document.querySelectorAll('.nav-item')[2], 'agents')},
  {cat:'nav',    label:'Go to Computer',           fn: () => nav(document.querySelectorAll('.nav-item')[3], 'computer')},
  {cat:'nav',    label:'Go to Chat',               fn: () => nav(document.querySelector('.nav-item[onclick*="chat"]'), 'chat')},
  {cat:'nav',    label:'Go to Files',              fn: () => nav(document.querySelector('.nav-item[onclick*="files"]'), 'files')},
  {cat:'nav',    label:'Go to Projects',           fn: () => nav(document.querySelector('.nav-item[onclick*="projects"]'), 'projects')},
  {cat:'nav',    label:'Go to Datasets',           fn: () => nav(document.querySelector('.nav-item[onclick*="datasets"]'), 'datasets')},
  {cat:'nav',    label:'Go to Memory',             fn: () => nav(document.querySelector('.nav-item[onclick*="memory"]'), 'memory')},
  {cat:'nav',    label:'Go to Knowledge',          fn: () => nav(document.querySelector('.nav-item[onclick*="knowledge"]'), 'knowledge')},
  {cat:'nav',    label:'Go to Automations',        fn: () => nav(document.querySelector('.nav-item[onclick*="automations"]'), 'automations')},
  {cat:'nav',    label:'Go to Personas',           fn: () => nav(document.querySelector('.nav-item[onclick*="personas"]'), 'personas')},
  {cat:'nav',    label:'Go to Rules',              fn: () => nav(document.querySelector('.nav-item[onclick*="rules"]'), 'rules')},
  {cat:'nav',    label:'Go to Snapshots',          fn: () => nav(document.querySelector('.nav-item[onclick*="snapshots"]'), 'snapshots')},
  {cat:'nav',    label:'Go to System Monitor',     fn: () => nav(document.querySelector('.nav-item[onclick*="system"]'), 'system')},
  {cat:'nav',    label:'Go to Audit',              fn: () => nav(document.querySelector('.nav-item[onclick*="audit"]'), 'audit')},
  {cat:'nav',    label:'Go to Settings',           fn: () => nav(document.querySelector('.nav-item[onclick*="settings"]'), 'settings')},
  {cat:'action', label:'Create Snapshot',          fn: () => createSnapshot()},
  {cat:'action', label:'New Automation',           fn: () => createAuto()},
  {cat:'action', label:'New Persona',              fn: () => createPersona()},
  {cat:'action', label:'New Rule',                 fn: () => createRule()},
  {cat:'action', label:'Import Dataset',           fn: () => createDataset()},
  {cat:'action', label:'Clear Chat History',       fn: async () => { if(confirm('Clear chat history?')) { await fetch('/api/chat/clear',{method:'POST'}); toast('Chat history cleared'); }}},
  {cat:'luo_os', label:'luo_os Status',            fn: async () => { const r = await fetch('/api/luo_os/status').then(r=>r.json()).catch(()=>({})); toast(JSON.stringify(r).substring(0,80)); }},
  {cat:'luo_os', label:'luo_os Skill Library',     fn: () => nav(document.querySelector('.nav-item[onclick*="knowledge"]'), 'knowledge')},
  {cat:'luo_os', label:'KAIROS Status',            fn: async () => { const r = await fetch('/api/luo_os/kairos').then(r=>r.json()).catch(()=>({})); toast(JSON.stringify(r).substring(0,80)); }},
];
let paletteSel = 0;
let paletteFiltered = [...COMMANDS];

window.openPalette = function() {
  document.getElementById('palette').classList.add('open');
  document.getElementById('palette-input').value = '';
  paletteSel = 0;
  paletteFiltered = [...COMMANDS];
  renderPaletteList();
  document.getElementById('palette-input').focus();
};
function closePalette() { document.getElementById('palette').classList.remove('open'); }
function renderPaletteList() {
  const list = document.getElementById('palette-list');
  list.innerHTML = paletteFiltered.map((c,i) =>
    `<div class="palette-item ${i===paletteSel?'sel':''}" onclick="runPaletteItem(${i})">
      <span class="palette-item-cat">${escHtml(c.cat)}</span>
      <span>${escHtml(c.label)}</span>
    </div>`
  ).join('');
}
window.runPaletteItem = function(i) {
  closePalette();
  paletteFiltered[i]?.fn();
};
document.getElementById('palette-input').addEventListener('input', e => {
  const q = e.target.value.toLowerCase();
  paletteSel = 0;
  paletteFiltered = COMMANDS.filter(c => c.label.toLowerCase().includes(q) || c.cat.includes(q));
  renderPaletteList();
});
document.getElementById('palette-input').addEventListener('keydown', e => {
  if (e.key === 'ArrowDown') { paletteSel = Math.min(paletteSel+1, paletteFiltered.length-1); renderPaletteList(); }
  if (e.key === 'ArrowUp')   { paletteSel = Math.max(paletteSel-1, 0); renderPaletteList(); }
  if (e.key === 'Enter')     { runPaletteItem(paletteSel); }
  if (e.key === 'Escape')    { closePalette(); }
});
document.getElementById('palette').addEventListener('click', e => {
  if (e.target === document.getElementById('palette')) closePalette();
});
document.addEventListener('keydown', e => {
  if ((e.ctrlKey||e.metaKey) && e.key === 'k') { e.preventDefault(); openPalette(); }
});

// ─── Auto-refresh every 8s ───────────────────────────────────────────────────
setInterval(() => { refreshState().then(() => renderPanel(currentPanel)); }, 8000);

// ─── Boot ────────────────────────────────────────────────────────────────────
connectSSE();
renderPanel('overview');

// ─── Chat panel ────────────────────────────────────────────────────────────────
function renderChat() {
  return `<div class="card" style="display:flex;flex-direction:column;height:calc(100vh - 120px)">
    <h3 style="margin-bottom:12px">💬 Chat with luo_os</h3>
    <div id="chat-msgs" style="flex:1;overflow-y:auto;padding:8px;background:var(--bg);border-radius:8px;margin-bottom:12px;font-size:.875rem"></div>
    <div style="display:flex;gap:8px">
      <input id="chat-input" type="text" placeholder="Message luo_os AI..." style="flex:1;padding:10px 14px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:.875rem" onkeydown="if(event.key==='Enter')sendChat()">
      <button class="btn" onclick="sendChat()">Send ▶</button>
    </div>
  </div>`;
}
async function sendChat() {
  const inp = document.getElementById('chat-input');
  const msg = inp.value.trim();
  if (!msg) return;
  inp.value = '';
  const msgs = document.getElementById('chat-msgs');
  msgs.innerHTML += `<div style="margin-bottom:8px"><span style="color:var(--accent);font-weight:600">You:</span> ${msg}</div>`;
  msgs.scrollTop = msgs.scrollHeight;
  const r = await fetch('/api/luo_os/chat', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})}).then(r=>r.json()).catch(()=>({}));
  const reply = r.response || r.error || 'No response';
  msgs.innerHTML += `<div style="margin-bottom:8px;padding:8px;background:var(--surface2);border-radius:6px"><span style="color:var(--muted);font-weight:600">luo_os:</span> <pre style="margin:4px 0;white-space:pre-wrap;font-size:.8rem">${reply}</pre></div>`;
  msgs.scrollTop = msgs.scrollHeight;
}

// ─── Snapshots panel ──────────────────────────────────────────────────────────
function renderSnapshots() {
  setTimeout(renderSnapshotsAsync, 0);
  return '<div class="empty">Loading snapshots...</div>';
}
async function renderSnapshotsAsync() {
  const snaps = await fetch('/api/snapshots').then(r=>r.json()).catch(()=>[]);
  const content = document.getElementById('content');
  let h = `<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
    <h3>📸 Snapshots (${snaps.length})</h3>
    <button class="btn" onclick="createSnapshot()">+ New Snapshot</button>
  </div>`;
  if (!snaps.length) h += '<div class="empty">No snapshots yet. Create one to save workspace state.</div>';
  else h += '<div class="scroll-list">' + snaps.map(s => `
    <div style="display:flex;align-items:center;gap:12px;padding:10px;background:var(--surface2);border-radius:8px">
      <div style="flex:1"><div style="font-weight:600">${s.label}</div>
        <div style="color:var(--muted);font-size:.75rem">${new Date(s.created_at*1000).toLocaleString()} · ${(s.size_bytes/1024).toFixed(1)}KB</div>
        <div style="color:var(--muted);font-size:.72rem;font-family:monospace">${JSON.stringify(s.data)}</div>
      </div>
      <button class="btn sm" onclick="restoreSnap('${s.id}')">↩ Restore</button>
      <button class="btn sm danger" onclick="deleteSnap('${s.id}')">🗑</button>
    </div>`).join('') + '</div>';
  h += '</div>';
  content.innerHTML = h;
}
async function createSnapshot() {
  const label = prompt('Snapshot label (optional):') || '';
  const r = await fetch('/api/snapshots',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({label})}).then(r=>r.json());
  if(r.ok){toast('Snapshot created');renderPanel('snapshots');}
}
async function restoreSnap(id) {
  if(!confirm('Restore this snapshot?')) return;
  const r = await fetch(`/api/snapshots/${id}/restore`,{method:'POST'}).then(r=>r.json());
  if(r.ok){toast('Snapshot restored');await refreshState();renderPanel('snapshots');}
}
async function deleteSnap(id) {
  if(!confirm('Delete snapshot?')) return;
  await fetch(`/api/snapshots/${id}`,{method:'DELETE'});
  renderPanel('snapshots');
}

// ─── Automations panel ────────────────────────────────────────────────────────
function renderAutomations() {
  setTimeout(renderAutomationsAsync, 0);
  return '<div class="empty">Loading automations...</div>';
}
async function renderAutomationsAsync() {
  const autos = await fetch('/api/automations').then(r=>r.json()).catch(()=>[]);
  const content = document.getElementById('content');
  let h = `<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
    <h3>⏰ Automations (${autos.length})</h3>
    <button class="btn" onclick="createAuto()">+ New Automation</button>
  </div>`;
  if (!autos.length) h += '<div class="empty">No automations yet. Schedule AI tasks to run automatically.</div>';
  else h += '<div class="scroll-list">' + autos.map(a => `
    <div style="padding:10px;background:var(--surface2);border-radius:8px;margin-bottom:8px">
      <div style="display:flex;align-items:center;gap:10px">
        <span style="font-size:1.2rem">${a.enabled ? '✅' : '⏸'}</span>
        <div style="flex:1">
          <div style="font-weight:600">${a.name}</div>
          <div style="color:var(--muted);font-size:.75rem">Schedule: ${a.schedule} · Delivery: ${a.delivery} · Runs: ${a.run_count}</div>
          <div style="color:var(--text);font-size:.8rem;margin-top:4px;font-style:italic">"${a.prompt}"</div>
          ${a.last_output?`<div style="color:var(--muted);font-size:.72rem;margin-top:4px;font-family:monospace">Last: ${a.last_output.substring(0,100)}</div>`:''}
        </div>
        <div style="display:flex;gap:6px;flex-direction:column">
          <button class="btn sm" onclick="runAutoNow('${a.id}')">▶ Run now</button>
          <button class="btn sm" onclick="toggleAuto('${a.id}',${!a.enabled})">${a.enabled?'Pause':'Enable'}</button>
          <button class="btn sm danger" onclick="deleteAuto('${a.id}')">🗑</button>
        </div>
      </div>
    </div>`).join('') + '</div>';
  h += '</div>';
  content.innerHTML = h;
}
async function createAuto() {
  const name = prompt('Automation name:'); if(!name) return;
  const prompt_text = prompt('What should the AI do?'); if(!prompt_text) return;
  const schedule = prompt('Schedule (cron expression, e.g. "0 9 * * 1-5" for 9am weekdays):') || '0 9 * * *';
  const delivery = prompt('Delivery: dashboard, email, sms, none') || 'dashboard';
  const r = await fetch('/api/automations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,prompt:prompt_text,schedule,delivery})}).then(r=>r.json());
  if(r.ok){toast('Automation created');renderPanel('automations');}
}
async function runAutoNow(id) {
  const r = await fetch(`/api/automations/${id}/run`,{method:'POST'}).then(r=>r.json());
  if(r.ok){toast('Automation ran ✓');renderPanel('automations');}else toast('Run failed','err');
}
async function toggleAuto(id, enabled) {
  await fetch(`/api/automations/${id}/toggle`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:String(enabled)})});
  renderPanel('automations');
}
async function deleteAuto(id) {
  if(!confirm('Delete automation?')) return;
  await fetch(`/api/automations/${id}`,{method:'DELETE'});
  renderPanel('automations');
}

// ─── Personas panel ────────────────────────────────────────────────────────────
function renderPersonas() {
  setTimeout(renderPersonasAsync, 0);
  return '<div class="empty">Loading personas...</div>';
}
async function renderPersonasAsync() {
  const personas = await fetch('/api/personas').then(r=>r.json()).catch(()=>[]);
  const content = document.getElementById('content');
  let h = `<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
    <h3>🎭 Personas (${personas.length})</h3>
    <button class="btn" onclick="createPersona()">+ New Persona</button>
  </div>`;
  if (!personas.length) h += '<div class="empty">No personas yet. Create named AI configs with different instructions and models.</div>';
  else h += '<div class="scroll-list">' + personas.map(p => `
    <div style="display:flex;align-items:center;gap:12px;padding:10px;background:var(--surface2);border-radius:8px;border:2px solid ${p.active?'var(--accent)':'transparent'}">
      <div style="font-size:1.5rem">🎭</div>
      <div style="flex:1">
        <div style="font-weight:600">${p.name} ${p.active?'<span style="color:var(--accent);font-size:.7rem">ACTIVE</span>':''}</div>
        <div style="color:var(--muted);font-size:.75rem">Model: ${p.model||'default'} · Tone: ${p.tone}</div>
        <div style="color:var(--text);font-size:.8rem;margin-top:4px">${p.instructions.substring(0,120)}${p.instructions.length>120?'...':''}</div>
      </div>
      <div style="display:flex;gap:6px;flex-direction:column">
        ${!p.active?`<button class="btn sm" onclick="activatePersona('${p.id}')">Activate</button>`:'<button class="btn sm" style="opacity:.4" disabled>Active</button>'}
        <button class="btn sm danger" onclick="deletePersona('${p.id}')">🗑</button>
      </div>
    </div>`).join('') + '</div>';
  h += '</div>';
  content.innerHTML = h;
}
async function createPersona() {
  const name = prompt('Persona name (e.g. "Code Expert"):'); if(!name) return;
  const instructions = prompt('System instructions for this persona:'); if(!instructions) return;
  const model = prompt('Model ID (leave blank for default):') || '';
  const tone = prompt('Tone: technical, friendly, concise, verbose') || 'technical';
  const r = await fetch('/api/personas',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,instructions,model,tone})}).then(r=>r.json());
  if(r.ok){toast('Persona created');renderPanel('personas');}
}
async function activatePersona(id) {
  const r = await fetch(`/api/personas/${id}/activate`,{method:'POST'}).then(r=>r.json());
  if(r.ok){toast('Persona activated');renderPanel('personas');}
}
async function deletePersona(id) {
  if(!confirm('Delete persona?')) return;
  await fetch(`/api/personas/${id}`,{method:'DELETE'});
  renderPanel('personas');
}

// ─── Rules panel ───────────────────────────────────────────────────────────────
function renderRules() {
  setTimeout(renderRulesAsync, 0);
  return '<div class="empty">Loading rules...</div>';
}
async function renderRulesAsync() {
  const rules = await fetch('/api/rules').then(r=>r.json()).catch(()=>[]);
  const content = document.getElementById('content');
  let h = `<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
    <h3>📜 Rules (${rules.length})</h3>
    <button class="btn" onclick="createRule()">+ New Rule</button>
  </div>
  <p style="color:var(--muted);font-size:.8rem;margin-bottom:12px">Rules are persistent AI behavior instructions injected into every agent interaction.</p>`;
  if (!rules.length) h += '<div class="empty">No rules yet. Add persistent instructions that always apply to AI responses.</div>';
  else h += '<div class="scroll-list">' + rules.map(r => `
    <div style="display:flex;align-items:center;gap:12px;padding:10px;background:var(--surface2);border-radius:8px;opacity:${r.enabled?1:0.5}">
      <div style="font-size:1.2rem">${r.enabled?'✅':'⏸'}</div>
      <div style="flex:1">
        <div style="font-weight:600">${r.title}</div>
        <div style="color:var(--muted);font-size:.75rem">Condition: ${r.condition}</div>
        <div style="color:var(--text);font-size:.8rem;margin-top:4px;font-style:italic">${r.instruction}</div>
      </div>
      <div style="display:flex;gap:6px">
        <button class="btn sm" onclick="toggleRule('${r.id}',${!r.enabled})">${r.enabled?'Disable':'Enable'}</button>
        <button class="btn sm danger" onclick="deleteRule('${r.id}')">🗑</button>
      </div>
    </div>`).join('') + '</div>';
  h += '</div>';
  content.innerHTML = h;
}
async function createRule() {
  const title = prompt('Rule title:'); if(!title) return;
  const condition = prompt('When does this apply? (e.g. "always", "when coding", "when writing"):') || 'always';
  const instruction = prompt('What should the AI do?'); if(!instruction) return;
  const r = await fetch('/api/rules',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,condition,instruction})}).then(r=>r.json());
  if(r.ok){toast('Rule created');renderPanel('rules');}
}
async function toggleRule(id, enabled) {
  await fetch(`/api/rules/${id}/toggle`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:String(enabled)})});
  renderPanel('rules');
}
async function deleteRule(id) {
  if(!confirm('Delete rule?')) return;
  await fetch(`/api/rules/${id}`,{method:'DELETE'});
  renderPanel('rules');
}

// ─── Datasets panel ────────────────────────────────────────────────────────────
function renderDatasets() {
  setTimeout(renderDatasetsAsync, 0);
  return '<div class="empty">Loading datasets...</div>';
}
async function renderDatasetsAsync() {
  const datasets = await fetch('/api/datasets').then(r=>r.json()).catch(()=>[]);
  const content = document.getElementById('content');
  let h = `<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
    <h3>📊 Datasets (${datasets.length})</h3>
    <button class="btn" onclick="createDataset()">+ Import Dataset</button>
  </div>`;
  if (!datasets.length) h += '<div class="empty">No datasets yet. Import CSV, JSON, or JSONL data.</div>';
  else h += '<div class="scroll-list">' + datasets.map(d => `
    <div style="padding:10px;background:var(--surface2);border-radius:8px;margin-bottom:8px">
      <div style="display:flex;align-items:center;gap:12px">
        <div style="font-size:1.4rem">📊</div>
        <div style="flex:1">
          <div style="font-weight:600">${d.name}</div>
          <div style="color:var(--muted);font-size:.75rem">${d.format.toUpperCase()} · ${d.row_count} rows · ${new Date(d.created_at*1000).toLocaleDateString()}</div>
          ${d.last_query?`<div style="color:var(--muted);font-size:.72rem;font-family:monospace;margin-top:4px">Last query: ${d.last_query}</div>`:''}
        </div>
        <div style="display:flex;gap:6px;flex-direction:column">
          <button class="btn sm" onclick="queryDataset('${d.id}')">Query</button>
          <button class="btn sm danger" onclick="deleteDataset('${d.id}')">🗑</button>
        </div>
      </div>
    </div>`).join('') + '</div>';
  h += '</div>';
  content.innerHTML = h;
}
async function createDataset() {
  const name = prompt('Dataset name:'); if(!name) return;
  const format = prompt('Format: csv, json, jsonl') || 'csv';
  const content_text = prompt('Paste data content (or leave blank):') || '';
  const r = await fetch('/api/datasets',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,format,content:content_text})}).then(r=>r.json());
  if(r.ok){toast('Dataset imported');renderPanel('datasets');}
}
async function queryDataset(id) {
  const sql = prompt('SQL query (e.g. SELECT * FROM data LIMIT 10):') || 'SELECT * FROM data LIMIT 10';
  const r = await fetch(`/api/datasets/${id}/query`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sql})}).then(r=>r.json()).catch(()=>({}));
  if (r.error) { alert('Error: ' + r.error); return; }
  // Build a readable table
  let out = `<b>Query:</b> ${sql}<br><br>`;
  if (r.columns && r.rows) {
    out += '<div style="overflow-x:auto"><table style="border-collapse:collapse;font-size:.8rem;width:100%">';
    out += '<tr>' + r.columns.map(c => `<th style="padding:6px 10px;background:var(--surface2);border:1px solid var(--border);text-align:left">${c}</th>`).join('') + '</tr>';
    r.rows.forEach(row => {
      out += '<tr>' + row.map(v => `<td style="padding:5px 10px;border:1px solid var(--border)">${v}</td>`).join('') + '</tr>';
    });
    out += '</table></div>';
    out += `<br><span style="color:var(--muted);font-size:.75rem">Showing ${r.returned} of ${r.total_rows} rows</span>`;
  } else {
    out += '<pre style="font-size:.75rem;overflow-x:auto">' + JSON.stringify(r, null, 2) + '</pre>';
  }
  // Show in a modal overlay
  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;display:flex;align-items:center;justify-content:center';
  overlay.innerHTML = `<div style="background:var(--surface);border-radius:12px;padding:24px;max-width:90vw;max-height:80vh;overflow:auto;min-width:400px">
    <div style="display:flex;justify-content:space-between;margin-bottom:16px">
      <h4 style="margin:0">Query Result</h4>
      <button class="btn sm" onclick="this.closest('[style*=fixed]').remove()">✕</button>
    </div>
    ${out}
  </div>`;
  document.body.appendChild(overlay);
}
async function deleteDataset(id) {
  if(!confirm('Delete dataset?')) return;
  await fetch(`/api/datasets/${id}`,{method:'DELETE'});
  renderPanel('datasets');
}

// ─── System monitor panel ──────────────────────────────────────────────────────
function renderSystem() {
  setTimeout(renderSystemAsync, 0);
  return '<div class="empty">Loading system stats...</div>';
}
async function renderSystemAsync() {
  const s = await fetch('/api/system').then(r=>r.json()).catch(()=>({}));
  const luo = await fetch('/api/luo_os/status').then(r=>r.json()).catch(()=>({}));
  const content = document.getElementById('content');
  const bar = (pct, color='var(--accent)') =>
    `<div style="height:8px;background:var(--surface2);border-radius:4px;overflow:hidden;margin-top:4px">
      <div style="height:100%;width:${Math.min(pct,100)}%;background:${pct>85?'#ef4444':pct>60?'#f59e0b':color};border-radius:4px;transition:width .3s"></div>
    </div>`;
  const fmtUptime = s => {
    if(!s) return 'unknown';
    const d=Math.floor(s/86400),h=Math.floor((s%86400)/3600),m=Math.floor((s%3600)/60);
    return d?`${d}d ${h}h ${m}m`:h?`${h}h ${m}m`:`${m}m`;
  };
  let h = `<div class="card"><h3 style="margin-bottom:20px">📡 System Monitor</h3>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:20px">
      <div style="background:var(--surface2);padding:16px;border-radius:10px">
        <div style="color:var(--muted);font-size:.75rem;margin-bottom:6px">CPU</div>
        <div style="font-size:1.6rem;font-weight:700;color:${s.cpu_pct>85?'#ef4444':s.cpu_pct>60?'#f59e0b':'var(--accent)'}">${s.cpu_pct??'–'}%</div>
        ${bar(s.cpu_pct)}
      </div>
      <div style="background:var(--surface2);padding:16px;border-radius:10px">
        <div style="color:var(--muted);font-size:.75rem;margin-bottom:6px">Memory</div>
        <div style="font-size:1.6rem;font-weight:700">${s.mem_pct??'–'}%</div>
        <div style="color:var(--muted);font-size:.72rem">${s.mem_used_mb??'–'} / ${s.mem_total_mb??'–'} MB</div>
        ${bar(s.mem_pct)}
      </div>
      <div style="background:var(--surface2);padding:16px;border-radius:10px">
        <div style="color:var(--muted);font-size:.75rem;margin-bottom:6px">Disk</div>
        <div style="font-size:1.6rem;font-weight:700">${s.disk_pct??'–'}%</div>
        <div style="color:var(--muted);font-size:.72rem">${Math.round((s.disk_used_mb??0)/1024)} / ${Math.round((s.disk_total_mb??0)/1024)} GB</div>
        ${bar(s.disk_pct)}
      </div>
      <div style="background:var(--surface2);padding:16px;border-radius:10px">
        <div style="color:var(--muted);font-size:.75rem;margin-bottom:6px">Uptime</div>
        <div style="font-size:1.3rem;font-weight:700;color:var(--accent)">${fmtUptime(s.uptime_secs)}</div>
      </div>
    </div>`;

  // luo_os subsystem status
  if (luo && luo.services) {
    h += `<h4 style="margin-bottom:12px">luo_os Services</h4>
    <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px">`;
    for (const [svc, ok] of Object.entries(luo.services)) {
      h += `<div style="padding:6px 12px;border-radius:6px;background:var(--surface2);font-size:.8rem">
        <span style="color:${ok?'#22c55e':'#ef4444'}">${ok?'●':'○'}</span> ${svc}</div>`;
    }
    h += '</div>';
    if (luo.skill_categories) {
      h += `<div style="color:var(--muted);font-size:.8rem">Skill library: ${luo.skill_categories} categories loaded</div>`;
    }
  }
  h += `<div style="margin-top:12px"><button class="btn sm" onclick="renderPanel('system')">↻ Refresh</button></div></div>`;
  content.innerHTML = h;
}

// ─── Notes panel ──────────────────────────────────────────────────────────────
let noteEditId = null;
function renderNotes() {
  setTimeout(renderNotesAsync, 0);
  return '<div class="empty">Loading notes...</div>';
}
async function renderNotesAsync() {
  const notes = await fetch('/api/notes').then(r=>r.json()).catch(()=>[]);
  const content = document.getElementById('content');
  let h = `<div style="display:grid;grid-template-columns:280px 1fr;gap:0;height:calc(100vh - 80px)">
    <div style="background:var(--surface);border-right:1px solid var(--border);overflow-y:auto;padding:12px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <span style="font-weight:700;font-size:.9rem">📝 Notes</span>
        <button class="btn sm" onclick="newNote()">+</button>
      </div>`;
  if (!notes.length) h += '<div class="empty" style="font-size:.8rem">No notes yet</div>';
  notes.forEach(n => {
    h += `<div onclick="openNote('${n.id}')" style="padding:10px;border-radius:8px;cursor:pointer;margin-bottom:6px;background:var(--surface2);border-left:3px solid ${n.pinned?'var(--accent)':'transparent'}">
      <div style="font-weight:600;font-size:.85rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${n.pinned?'📌 ':''}${n.title}</div>
      <div style="color:var(--muted);font-size:.72rem;margin-top:3px">${n.content.substring(0,60)}${n.content.length>60?'...':''}</div>
      <div style="color:var(--muted);font-size:.68rem;margin-top:4px">${new Date(n.updated_at*1000).toLocaleDateString()}</div>
    </div>`;
  });
  h += `</div>
    <div id="note-editor" style="display:flex;flex-direction:column;padding:24px">
      <div class="empty" style="margin:auto">Select a note or create a new one</div>
    </div>
  </div>`;
  content.innerHTML = h;
}
async function newNote() {
  const ed = document.getElementById('note-editor');
  if (!ed) return;
  noteEditId = null;
  ed.innerHTML = `<input id="note-title" type="text" placeholder="Note title..." style="font-size:1.2rem;font-weight:700;background:transparent;border:none;border-bottom:2px solid var(--accent);padding:8px 0;color:var(--text);width:100%;margin-bottom:16px;outline:none">
    <textarea id="note-content" placeholder="Write in markdown..." style="flex:1;background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:16px;color:var(--text);font-size:.9rem;resize:none;font-family:inherit;min-height:300px"></textarea>
    <div style="display:flex;gap:8px;margin-top:12px">
      <button class="btn" onclick="saveNote()">💾 Save</button>
    </div>`;
}
async function openNote(id) {
  const n = await fetch(`/api/notes/${id}`).then(r=>r.json()).catch(()=>null);
  if (!n) return;
  noteEditId = id;
  const ed = document.getElementById('note-editor');
  if (!ed) return;
  ed.innerHTML = `<input id="note-title" type="text" value="${n.title.replace(/"/g,'&quot;')}" style="font-size:1.2rem;font-weight:700;background:transparent;border:none;border-bottom:2px solid var(--accent);padding:8px 0;color:var(--text);width:100%;margin-bottom:16px;outline:none">
    <textarea id="note-content" style="flex:1;background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:16px;color:var(--text);font-size:.9rem;resize:none;font-family:inherit;min-height:300px">${n.content}</textarea>
    <div style="display:flex;gap:8px;margin-top:12px">
      <button class="btn" onclick="saveNote()">💾 Save</button>
      <button class="btn sm" onclick="pinNote('${id}',${!n.pinned})">${n.pinned?'Unpin':'📌 Pin'}</button>
      <button class="btn sm danger" onclick="deleteNoteId('${id}')">🗑 Delete</button>
    </div>`;
}
async function saveNote() {
  const title   = document.getElementById('note-title')?.value.trim();
  const content = document.getElementById('note-content')?.value;
  if (!title) { toast('Title required','err'); return; }
  if (noteEditId) {
    await fetch(`/api/notes/${noteEditId}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,content})});
    toast('Note saved');
  } else {
    const r = await fetch('/api/notes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,content})}).then(r=>r.json());
    noteEditId = r.id;
    toast('Note created');
  }
  renderNotesAsync();
}
async function pinNote(id, pinned) {
  await fetch(`/api/notes/${id}/pin`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pinned:String(pinned)})});
  renderNotesAsync();
}
async function deleteNoteId(id) {
  if (!confirm('Delete this note?')) return;
  await fetch(`/api/notes/${id}`,{method:'DELETE'});
  noteEditId = null;
  renderNotesAsync();
}

// ─── Terminal panel ────────────────────────────────────────────────────────────
let termHistory = [], termIdx = -1;
function renderTerminalPanel() {
  setTimeout(loadTermHistory, 0);
  return `<div style="display:flex;flex-direction:column;height:calc(100vh - 80px);font-family:monospace">
    <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:var(--surface2);border-bottom:1px solid var(--border)">
      <span style="font-weight:700">⌨ Terminal</span>
      <div style="display:flex;gap:8px">
        <input id="term-cwd" type="text" placeholder="Working dir (optional)" style="padding:4px 8px;background:var(--bg);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:.75rem;width:200px">
        <button class="btn sm" onclick="clearTerm()">Clear</button>
      </div>
    </div>
    <div id="term-output" style="flex:1;overflow-y:auto;padding:16px;background:#0d1117;color:#e6edf3;font-size:.85rem;line-height:1.6"></div>
    <div style="display:flex;gap:0;background:#0d1117;border-top:1px solid #30363d;padding:8px 12px">
      <span style="color:#7ee787;padding:8px 0;margin-right:8px">$</span>
      <input id="term-input" type="text" placeholder="Enter command..." style="flex:1;background:transparent;border:none;color:#e6edf3;font-size:.85rem;font-family:monospace;outline:none"
        onkeydown="handleTermKey(event)">
      <button onclick="execTerm()" style="background:#238636;color:#fff;border:none;border-radius:4px;padding:6px 14px;cursor:pointer;font-size:.8rem">Run</button>
    </div>
  </div>`;
}
async function loadTermHistory() {
  const hist = await fetch('/api/terminal/history?limit=100').then(r=>r.json()).catch(()=>[]);
  const out = document.getElementById('term-output');
  if (!out) return;
  out.innerHTML = hist.map(e =>
    `<div style="margin-bottom:10px"><span style="color:#7ee787">$ ${e.command}</span>${e.exit_code!==0?`<span style="color:#f85149;margin-left:8px">[exit ${e.exit_code}]</span>`:''}<pre style="margin:4px 0 0;color:#e6edf3;white-space:pre-wrap;font-size:.82rem">${e.output}</pre></div>`
  ).join('') + '<div id="term-cursor"></div>';
  out.scrollTop = out.scrollHeight;
}
function handleTermKey(e) {
  if (e.key === 'Enter') { execTerm(); return; }
  if (e.key === 'ArrowUp') {
    termIdx = Math.min(termIdx + 1, termHistory.length - 1);
    e.target.value = termHistory[termHistory.length - 1 - termIdx] || '';
  }
  if (e.key === 'ArrowDown') {
    termIdx = Math.max(termIdx - 1, -1);
    e.target.value = termIdx < 0 ? '' : termHistory[termHistory.length - 1 - termIdx];
  }
}
async function execTerm() {
  const inp = document.getElementById('term-input');
  const cmd = inp?.value.trim();
  if (!cmd) return;
  termHistory.push(cmd); termIdx = -1;
  inp.value = '';
  const out = document.getElementById('term-output');
  if (out) {
    const pending = document.createElement('div');
    pending.style.cssText = 'margin-bottom:10px;opacity:.6';
    pending.innerHTML = `<span style="color:#7ee787">$ ${cmd}</span> <span style="color:#8b949e">running...</span>`;
    out.appendChild(pending);
    out.scrollTop = out.scrollHeight;
  }
  const cwd = document.getElementById('term-cwd')?.value || '';
  const r = await fetch('/api/terminal/exec',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:cmd,cwd})}).then(r=>r.json()).catch(()=>({output:'[error]',exit_code:-1}));
  if (out) {
    out.innerHTML = out.innerHTML.replace(/<div[^>]*opacity.*?<\/div>/, '');
    const el = document.createElement('div');
    el.style.marginBottom = '10px';
    el.innerHTML = `<span style="color:#7ee787">$ ${cmd}</span>${r.exit_code!==0?`<span style="color:#f85149;margin-left:8px">[exit ${r.exit_code}]</span>`:''}<pre style="margin:4px 0 0;color:#e6edf3;white-space:pre-wrap;font-size:.82rem">${r.output}</pre>`;
    out.appendChild(el);
    out.scrollTop = out.scrollHeight;
  }
}
async function clearTerm() {
  await fetch('/api/terminal/clear',{method:'POST'});
  const out = document.getElementById('term-output');
  if (out) out.innerHTML = '<div id="term-cursor"></div>';
}

// ─── Git panel ────────────────────────────────────────────────────────────────
function renderGit() {
  setTimeout(renderGitAsync, 0);
  return '<div class="empty">Loading git status...</div>';
}
async function renderGitAsync() {
  const cwd = document.getElementById('git-cwd-input')?.value || '';
  const [gs, log] = await Promise.all([
    fetch(`/api/git/status${cwd?'?cwd='+encodeURIComponent(cwd):''}`).then(r=>r.json()).catch(()=>({})),
    fetch(`/api/git/log${cwd?'?cwd='+encodeURIComponent(cwd):''}&limit=15`).then(r=>r.json()).catch(()=>({}))
  ]);
  const content = document.getElementById('content');
  const statusColor = gs.branch ? 'var(--accent)' : '#ef4444';
  let h = `<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
    <h3>🔀 Git</h3>
    <div style="display:flex;gap:8px;align-items:center">
      <input id="git-cwd-input" type="text" value="${cwd}" placeholder="Repo path..." style="padding:6px 10px;background:var(--surface2);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;width:240px">
      <button class="btn sm" onclick="renderGit()">↻</button>
    </div>
  </div>
  ${gs.branch ? `<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px">
    <div style="padding:8px 14px;background:var(--surface2);border-radius:8px">
      <div style="color:var(--muted);font-size:.7rem">Branch</div>
      <div style="font-weight:700;color:${statusColor}">${gs.branch}</div>
    </div>
    <div style="padding:8px 14px;background:var(--surface2);border-radius:8px">
      <div style="color:var(--muted);font-size:.7rem">Ahead/Behind</div>
      <div style="font-weight:700">↑${gs.ahead} ↓${gs.behind}</div>
    </div>
    <div style="padding:8px 14px;background:var(--surface2);border-radius:8px">
      <div style="color:var(--muted);font-size:.7rem">Last commit</div>
      <div style="font-weight:600;font-size:.8rem">${gs.last_commit_msg?.substring(0,50)||'—'}</div>
    </div>
    <div style="display:flex;gap:6px;align-items:center">
      <button class="btn sm" onclick="gitPull()">↓ Pull</button>
      <button class="btn sm" onclick="gitPush()">↑ Push</button>
      <button class="btn sm" onclick="gitAddAll()">+ Add all</button>
      <button class="btn sm" onclick="gitCommitDialog()">✓ Commit</button>
    </div>
  </div>` : '<div class="empty">No git repo found at this path. Enter a repo path above.</div>'}`;

  if (gs.staged?.length || gs.unstaged?.length || gs.untracked?.length) {
    h += `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px">`;
    const col = (label, color, files) => `<div style="background:var(--surface2);border-radius:8px;padding:12px">
      <div style="color:${color};font-size:.75rem;font-weight:700;margin-bottom:8px">${label} (${files.length})</div>
      ${files.map(f=>`<div style="font-size:.75rem;font-family:monospace;color:var(--text);padding:2px 0">${f}</div>`).join('')}
    </div>`;
    h += col('● Staged','#22c55e', gs.staged||[]);
    h += col('○ Unstaged','#f59e0b', gs.unstaged||[]);
    h += col('? Untracked','var(--muted)', gs.untracked||[]);
    h += '</div>';
  }

  if (log.log) {
    h += `<h4 style="margin-bottom:10px">Commit Log</h4>
    <pre style="background:var(--bg);padding:14px;border-radius:8px;font-size:.78rem;overflow-x:auto;color:var(--text)">${log.log}</pre>`;
  }
  h += '</div>';
  content.innerHTML = h;
}
async function gitPull() {
  const cwd = document.getElementById('git-cwd-input')?.value||'';
  const r = await fetch('/api/git/pull',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cwd})}).then(r=>r.json());
  toast(r.output?.substring(0,80)||'Pulled'); renderGitAsync();
}
async function gitPush() {
  const cwd = document.getElementById('git-cwd-input')?.value||'';
  const r = await fetch('/api/git/push',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cwd})}).then(r=>r.json());
  toast(r.output?.substring(0,80)||'Pushed'); renderGitAsync();
}
async function gitAddAll() {
  const cwd = document.getElementById('git-cwd-input')?.value||'';
  await fetch('/api/git/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pattern:'.',cwd})});
  toast('Staged all changes'); renderGitAsync();
}
async function gitCommitDialog() {
  const msg = prompt('Commit message:'); if (!msg) return;
  const cwd = document.getElementById('git-cwd-input')?.value||'';
  const r = await fetch('/api/git/commit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg,cwd})}).then(r=>r.json());
  toast(r.output?.substring(0,80)||'Committed'); renderGitAsync();
}

// ─── Global search panel ──────────────────────────────────────────────────────
function renderSearch() {
  return `<div class="card" style="max-width:760px;margin:0 auto">
    <h3 style="margin-bottom:16px">🔍 Global Search</h3>
    <div style="display:flex;gap:8px;margin-bottom:20px">
      <input id="search-input" type="text" placeholder="Search tasks, files, notes, memory, agents..." autofocus
        style="flex:1;padding:12px 16px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:.95rem"
        oninput="debounceSearch(this.value)" onkeydown="if(event.key==='Enter')doSearch()">
      <button class="btn" onclick="doSearch()">Search</button>
    </div>
    <div id="search-results"></div>
  </div>`;
}
let searchTimer = null;
function debounceSearch(q) {
  clearTimeout(searchTimer);
  if (q.length < 2) { document.getElementById('search-results').innerHTML = ''; return; }
  searchTimer = setTimeout(() => doSearch(q), 300);
}
async function doSearch(q) {
  q = q ?? document.getElementById('search-input')?.value ?? '';
  if (!q) return;
  const r = await fetch(`/api/search?q=${encodeURIComponent(q)}&limit=30`).then(r=>r.json()).catch(()=>({results:[]}));
  const icons = {task:'📋',file:'📁',memory:'🧠',note:'📝',agent:'🤖',project:'🚀',knowledge:'📚'};
  const colors = {task:'var(--accent)',file:'#22c55e',memory:'#a78bfa',note:'#fb923c',agent:'#60a5fa',project:'#34d399',knowledge:'#f472b6'};
  const container = document.getElementById('search-results');
  if (!container) return;
  if (!r.results?.length) { container.innerHTML = `<div class="empty">No results for "${q}"</div>`; return; }
  container.innerHTML = `<div style="color:var(--muted);font-size:.8rem;margin-bottom:12px">${r.count} results</div>` +
    r.results.map(res => `
    <div style="display:flex;gap:12px;padding:12px;background:var(--surface2);border-radius:8px;margin-bottom:8px;cursor:pointer;border-left:3px solid ${colors[res.kind]||'var(--border)'}"
      onclick="searchNavigate('${res.kind}','${res.id}')">
      <span style="font-size:1.2rem">${icons[res.kind]||'📄'}</span>
      <div style="flex:1;min-width:0">
        <div style="font-weight:600;font-size:.9rem">${res.title}</div>
        <div style="color:var(--muted);font-size:.75rem;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${res.snippet}</div>
      </div>
      <span style="color:var(--muted);font-size:.7rem;white-space:nowrap;padding:2px 6px;background:var(--bg);border-radius:4px">${res.kind}</span>
    </div>`).join('');
}
function searchNavigate(kind, id) {
  const panelMap = {task:'tasks',file:'files',memory:'memory',note:'notes',agent:'agents',project:'projects',knowledge:'knowledge'};
  const panel = panelMap[kind];
  if (panel) nav(document.querySelector(`.nav-item[onclick*="${panel}"]`), panel);
}

// ─── Notifications panel ──────────────────────────────────────────────────────
function renderNotifications() {
  setTimeout(renderNotificationsAsync, 0);
  return '<div class="empty">Loading notifications...</div>';
}
async function renderNotificationsAsync() {
  const data = await fetch('/api/notifications').then(r=>r.json()).catch(()=>({unread:0,items:[]}));
  const content = document.getElementById('content');
  const kindIcon = {info:'ℹ️',success:'✅',warn:'⚠️',error:'❌'};
  const kindColor = {info:'#60a5fa',success:'#22c55e',warn:'#f59e0b',error:'#ef4444'};
  let h = `<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
    <h3>🔔 Notifications${data.unread>0?` <span style="background:var(--accent);color:#fff;border-radius:10px;padding:2px 8px;font-size:.7rem">${data.unread} new</span>`:''}</h3>
    ${data.unread>0?`<button class="btn sm" onclick="markAllRead()">Mark all read</button>`:''}
  </div>`;
  if (!data.items?.length) h += '<div class="empty">No notifications</div>';
  else h += '<div class="scroll-list">' + data.items.map(n => `
    <div style="display:flex;align-items:flex-start;gap:12px;padding:12px;background:var(--surface2);border-radius:8px;margin-bottom:8px;opacity:${n.read?0.6:1};border-left:3px solid ${kindColor[n.kind]||'var(--border)'}">
      <span style="font-size:1.2rem;margin-top:2px">${kindIcon[n.kind]||'•'}</span>
      <div style="flex:1">
        <div style="font-weight:600;font-size:.88rem">${n.title}</div>
        <div style="color:var(--muted);font-size:.78rem;margin-top:2px">${n.detail}</div>
        <div style="color:var(--muted);font-size:.7rem;margin-top:4px">${new Date(n.created_at*1000).toLocaleString()}</div>
      </div>
      <div style="display:flex;gap:4px">
        ${!n.read?`<button class="btn sm" onclick="markRead('${n.id}')">✓</button>`:''}
        <button class="btn sm danger" onclick="deleteNotif('${n.id}')">×</button>
      </div>
    </div>`).join('') + '</div>';
  h += '</div>';
  content.innerHTML = h;
  // Update badge
  const badge = document.getElementById('nav-notif-badge');
  if (badge) badge.textContent = data.unread > 0 ? String(data.unread) : '';
}
async function markRead(id) {
  await fetch(`/api/notifications/${id}/read`,{method:'POST'});
  renderNotificationsAsync();
}
async function markAllRead() {
  await fetch('/api/notifications/read-all',{method:'POST'});
  renderNotificationsAsync();
}
async function deleteNotif(id) {
  await fetch(`/api/notifications/${id}`,{method:'DELETE'});
  renderNotificationsAsync();
}

// ─── Update SSE handler to update notification badge ──────────────────────────
const _origSSEHandler = window._sseHandler;
async function pollNotifBadge() {
  const data = await fetch('/api/notifications?unread=1').then(r=>r.json()).catch(()=>({unread:0}));
  const badge = document.getElementById('nav-notif-badge');
  if (badge) badge.textContent = data.unread > 0 ? String(data.unread) : '';
}
setInterval(pollNotifBadge, 10000);
pollNotifBadge();


</script>)JS";

    out << "</body></html>";
    return out.str();
}

// ─── Status page (simple, for health checks) ──────────────────────────────────
std::string render_status_html(const App& app) {
    const auto s = app.summary();
    std::ostringstream out;
    out << "<!doctype html><html lang='en'><body><pre style='font-family:monospace;padding:20px'>"
        << "LUO COMPUTER STATUS\n===================\n"
        << "active_user="    << s.active_user    << "\n"
        << "session_stage="  << s.session_stage  << "\n"
        << "platform="       << s.platform       << "\n"
        << "local_only="     << (s.local_only_mode ? "true" : "false") << "\n"
        << "---\n"
        << "users="     << s.user_count     << "\n"
        << "agents="    << s.agent_count    << "\n"
        << "tasks="     << s.task_count     << "\n"
        << "computers=" << s.computer_count << "\n"
        << "files="     << s.file_count     << "\n"
        << "projects="  << s.project_count  << "\n"
        << "memory="    << s.memory_count   << "\n"
        << "knowledge=" << s.knowledge_count<< "\n"
        << "audit="     << s.audit_count    << "\n"
        << "</pre></body></html>";
    return out.str();
}

} // namespace luo_gate
