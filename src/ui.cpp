#include "luo_gate/ui.hpp"
#include "luo_gate/platform.hpp"
#include "luo_gate/security.hpp"

#include <sstream>
#include <algorithm>

namespace luo_gate {
namespace {

// ─── Helpers ─────────────────────────────────────────────────────────────────
std::string html_escape(std::string_view text) {
    std::ostringstream out;
    for (char c : text) {
        switch (c) {
            case '&': out << "&amp;";  break;
            case '<': out << "&lt;";   break;
            case '>': out << "&gt;";   break;
            case '"': out << "&quot;"; break;
            case '\'': out << "&#39;"; break;
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

// Step 78: CSS design system
const char* GLOBAL_CSS = R"CSS(
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0b1020;--surface:#121a33;--surface2:#1a2240;--border:#243155;
  --accent:#4c8eff;--accent2:#6ee7ff;--danger:#ff4d6a;--success:#3ddc84;
  --warn:#ffb84d;--text:#e6edf3;--muted:#7a8ba8;--radius:14px;
  --font:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  --mono:'JetBrains Mono','Fira Code','Cascadia Code',monospace;
}
body{font-family:var(--font);background:var(--bg);color:var(--text);
  margin:0;padding:0;min-height:100vh;font-size:14px;line-height:1.5}
h1,h2{font-size:1.4rem;font-weight:700;color:var(--text);margin:0 0 4px}
h3{font-size:1rem;font-weight:600;color:var(--accent2);margin:0 0 8px}
h4{font-size:.875rem;font-weight:600;color:var(--muted);margin:4px 0}
p{color:var(--muted);margin:4px 0}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
/* Layout */
.topbar{background:var(--surface);border-bottom:1px solid var(--border);
  padding:10px 24px;display:flex;align-items:center;gap:16px;position:sticky;top:0;z-index:100}
.topbar-logo{font-weight:800;font-size:1.1rem;letter-spacing:.05em;color:var(--accent2)}
.topbar-status{font-size:.8rem;color:var(--muted)}
.topbar-right{margin-left:auto;display:flex;gap:8px;align-items:center}
.main{padding:20px 24px;max-width:1600px;margin:0 auto}
.grid{display:grid;gap:16px}
.grid-3{grid-template-columns:260px 1fr 320px}
.grid-2{grid-template-columns:1fr 1fr}
.grid-auto{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
/* Cards */
.card{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius);padding:16px;overflow:hidden}
.card-sm{padding:12px}
/* Pills / chips */
.pill{display:inline-flex;align-items:center;padding:5px 10px;
  border-radius:8px;background:var(--surface2);border:1px solid var(--border);
  font-size:.8rem;color:var(--text);white-space:nowrap;gap:6px}
.pill-block{display:flex;width:100%;margin:4px 0}
.pill.success{border-color:var(--success);color:var(--success)}
.pill.danger{border-color:var(--danger);color:var(--danger)}
.pill.warn{border-color:var(--warn);color:var(--warn)}
.pill.accent{border-color:var(--accent);color:var(--accent)}
.pill.muted{color:var(--muted)}
/* Buttons */
button,input,select{font-family:inherit;font-size:.85rem}
.btn{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;
  border-radius:8px;border:1px solid var(--border);background:var(--surface2);
  color:var(--text);cursor:pointer;transition:all .15s;white-space:nowrap}
.btn:hover{background:var(--border);border-color:var(--accent)}
.btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
.btn.primary:hover{background:#3a7ae0}
.btn.danger{background:transparent;border-color:var(--danger);color:var(--danger)}
.btn.danger:hover{background:var(--danger);color:#fff}
.btn.sm{padding:4px 10px;font-size:.78rem;border-radius:6px}
/* Inputs */
.input{width:100%;padding:8px 12px;border-radius:8px;border:1px solid var(--border);
  background:var(--surface2);color:var(--text);outline:none}
.input:focus{border-color:var(--accent);box-shadow:0 0 0 2px rgba(76,142,255,.15)}
/* Lists */
.scroll-list{max-height:320px;overflow-y:auto;display:flex;flex-direction:column;gap:4px}
.scroll-list::-webkit-scrollbar{width:4px}
.scroll-list::-webkit-scrollbar-thumb{background:var(--border);border-radius:4px}
/* Tables */
.table{width:100%;border-collapse:collapse;font-size:.82rem}
.table th{text-align:left;padding:6px 10px;color:var(--muted);
  border-bottom:1px solid var(--border);font-weight:500}
.table td{padding:6px 10px;border-bottom:1px solid rgba(36,49,85,.5)}
.table tr:hover td{background:var(--surface2)}
/* Tags */
.tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.72rem;
  font-weight:600;letter-spacing:.03em}
.tag-running{background:rgba(76,142,255,.15);color:var(--accent)}
.tag-done{background:rgba(61,220,132,.12);color:var(--success)}
.tag-queued{background:rgba(122,139,168,.12);color:var(--muted)}
.tag-paused{background:rgba(255,184,77,.12);color:var(--warn)}
.tag-failed{background:rgba(255,77,106,.12);color:var(--danger)}
.tag-cancelled{background:rgba(255,77,106,.08);color:var(--danger)}
/* Task inspector */
.split{display:grid;grid-template-columns:220px 1fr;gap:12px;min-height:300px}
.inspector-panel{background:var(--surface2);border:1px solid var(--border);
  border-radius:12px;padding:14px;overflow-y:auto;max-height:400px}
/* Playback timeline */
.timeline{display:flex;flex-direction:column;gap:6px}
.timeline-item{display:flex;gap:10px;align-items:flex-start}
.timeline-dot{width:10px;height:10px;border-radius:50%;background:var(--accent);
  margin-top:4px;flex-shrink:0;border:2px solid var(--border)}
.timeline-dot.done{background:var(--success)}
.timeline-dot.fail{background:var(--danger)}
.timeline-body{flex:1}
/* Agent grid */
.agent-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px}
.agent-card{background:var(--surface2);border:1px solid var(--border);
  border-radius:10px;padding:10px;font-size:.8rem}
.agent-card.busy{border-color:var(--accent)}
.agent-card.degraded{border-color:var(--warn)}
.agent-card.stuck{border-color:var(--danger)}
/* Search */
.search-bar{display:flex;gap:8px;margin-bottom:12px}
.search-results{display:flex;flex-direction:column;gap:6px}
.search-result{background:var(--surface2);border:1px solid var(--border);
  border-radius:8px;padding:10px;font-size:.82rem}
.search-result-kind{font-size:.7rem;font-weight:600;color:var(--accent);text-transform:uppercase}
/* Command palette */
.palette-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);
  z-index:999;align-items:flex-start;justify-content:center;padding-top:80px}
.palette-overlay.open{display:flex}
.palette-box{background:var(--surface);border:1px solid var(--accent);
  border-radius:14px;width:100%;max-width:560px;overflow:hidden;box-shadow:0 24px 80px rgba(0,0,0,.5)}
.palette-input{width:100%;padding:14px 18px;background:transparent;border:none;
  color:var(--text);font-size:1rem;outline:none}
.palette-list{border-top:1px solid var(--border);max-height:280px;overflow-y:auto}
.palette-item{padding:10px 18px;cursor:pointer;display:flex;gap:10px;align-items:center}
.palette-item:hover,.palette-item.active{background:var(--surface2)}
.palette-item-kind{font-size:.72rem;color:var(--muted);min-width:60px}
/* Breadcrumbs */
.breadcrumb{display:flex;gap:6px;align-items:center;font-size:.8rem;color:var(--muted);margin-bottom:12px}
.breadcrumb-sep{color:var(--border)}
/* Empty state */
.empty{text-align:center;padding:32px;color:var(--muted)}
.empty-icon{font-size:2rem;margin-bottom:8px}
/* Loading */
.skeleton{background:linear-gradient(90deg,var(--surface2) 25%,var(--border) 50%,var(--surface2) 75%);
  background-size:200% 100%;animation:shimmer 1.5s infinite;border-radius:6px;height:14px}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}
/* Privacy / consent */
.consent-flag{display:flex;align-items:center;gap:8px;padding:6px 0;font-size:.83rem}
.consent-flag input[type=checkbox]{width:16px;height:16px;accent-color:var(--accent)}
/* Responsive */
@media(max-width:960px){.grid-3{grid-template-columns:1fr}.topbar{padding:10px 16px}}
@media(max-width:640px){.grid-2{grid-template-columns:1fr}.main{padding:12px}}
/* Accessibility */
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
[aria-label],[title]{cursor:help}
)CSS";

// ─── CSS tag helper
std::string status_tag(std::string_view status) {
    std::ostringstream o;
    o << "<span class='tag tag-" << html_escape(status) << "'>" << html_escape(status) << "</span>";
    return o.str();
}

// ─── Topbar (step 71)
void append_topbar(std::ostringstream& out, const App& app) {
    const auto s = app.summary();
    out << "<header class='topbar' role='banner'>"
        << "<span class='topbar-logo' aria-label='LUO COMPUTER'>⬡ LUO COMPUTER</span>"
        << "<span class='topbar-status pill'>" << html_escape(s.session_stage) << "</span>"
        << "<span class='topbar-status'>" << html_escape(s.platform) << "</span>";
    if (s.local_only_mode)
        out << "<span class='pill muted' title='No outbound network calls'>🔒 local-only</span>";
    out << "<div class='topbar-right'>"
        << "<button class='btn sm' onclick='openPalette()' title='Open command palette (Ctrl+K)' aria-label='Command palette'>⌘ Commands</button>"
        << "<span class='pill'>" << html_escape(s.active_user) << "</span>"
        << "</div></header>";
}

// ─── Summary cards (step 75)
void append_summary_cards(std::ostringstream& out, const App& app) {
    const auto s = app.summary();
    struct Card { const char* label; std::size_t val; const char* icon; };
    const Card cards[] = {
        {"Agents",   s.agent_count,    "🤖"},
        {"Tasks",    s.task_count,     "📋"},
        {"Computers",s.computer_count, "🖥"},
        {"Files",    s.file_count,     "📁"},
        {"Skills",   s.skill_count,    "⚡"},
        {"Projects", s.project_count,  "🚀"},
        {"Devices",  s.device_count,   "📱"},
        {"Memory",   s.memory_count,   "🧠"},
        {"KB",       s.knowledge_count,"📚"},
    };
    out << "<div class='grid grid-auto' style='margin-bottom:16px'>";
    for (const auto& c : cards) {
        out << "<div class='card card-sm' style='text-align:center'>"
            << "<div style='font-size:1.4rem'>" << c.icon << "</div>"
            << "<div style='font-size:1.5rem;font-weight:700;color:var(--accent2)'>"
            << c.val << "</div>"
            << "<div style='font-size:.75rem;color:var(--muted)'>" << c.label << "</div>"
            << "</div>";
    }
    out << "</div>";
}

// ─── Task data as JSON (step 2, 10, 39)
std::string task_data_json(const App& app) {
    std::ostringstream out;
    out << "[";
    const auto tasks = app.tasks();
    for (std::size_t i = 0; i < tasks.size(); ++i) {
        const auto& task = tasks[i];
        if (i) out << ",";
        out << "{";
        out << "\"id\":\"" << json_escape(task.id) << "\",";
        out << "\"title\":\"" << json_escape(task.title) << "\",";
        out << "\"description\":\"" << json_escape(task.description) << "\",";
        out << "\"kind\":\"" << json_escape(task.kind) << "\",";
        out << "\"status\":\"" << json_escape(task.status) << "\",";
        out << "\"owner\":\"" << json_escape(task.owner) << "\",";
        out << "\"priority\":" << task.priority << ",";
        out << "\"step_cursor\":" << task.step_cursor << ",";
        out << "\"confidence\":" << task.confidence << ",";
        out << "\"validated\":" << (task.validated ? "true" : "false") << ",";
        out << "\"assigned_agents\":[";
        for (std::size_t j = 0; j < task.assigned_agents.size(); ++j) {
            if (j) out << ",";
            out << "\"" << json_escape(task.assigned_agents[j]) << "\"";
        }
        out << "],\"plan\":[";
        for (std::size_t j = 0; j < task.plan.size(); ++j) {
            const auto& step = task.plan[j];
            if (j) out << ",";
            out << "{";
            out << "\"index\":" << step.index << ",";
            out << "\"actor\":\"" << json_escape(step.actor) << "\",";
            out << "\"action\":\"" << json_escape(step.action) << "\",";
            out << "\"detail\":\"" << json_escape(step.detail) << "\",";
            out << "\"surface\":\"" << json_escape(step.surface) << "\",";
            out << "\"status\":\"" << json_escape(step.status) << "\"";
            out << "}";
        }
        out << "],\"subtasks\":[";
        for (std::size_t j = 0; j < task.subtasks.size(); ++j) {
            const auto& sub = task.subtasks[j];
            if (j) out << ",";
            out << "{\"id\":\"" << json_escape(sub.id) << "\","
                << "\"title\":\"" << json_escape(sub.title) << "\","
                << "\"status\":\"" << json_escape(sub.status) << "\","
                << "\"kind\":\"" << json_escape(sub.kind) << "\"}";
        }
        out << "],\"memory\":[";
        for (std::size_t j = 0; j < task.memory.size(); ++j) {
            if (j) out << ",";
            out << "\"" << json_escape(task.memory[j]) << "\"";
        }
        out << "]}";
    }
    out << "]";
    return out.str();
}

// ─── Task inspector (step 2, 10) ─────────────────────────────────────────────
void append_task_history(std::ostringstream& out, const App& app);

void append_task_inspector(std::ostringstream& out, const App& app) {
    const auto tasks = app.tasks();
    out << "<div class='split'>"
        << "<div class='scroll-list'>";
    if (tasks.empty()) {
        out << "<div class='empty'><div class='empty-icon'>📋</div>"
               "<div>No tasks yet</div></div>";
    }
    for (std::size_t i = 0; i < tasks.size(); ++i) {
        const auto& task = tasks[i];
        out << "<button type='button' class='btn pill-block task-btn' data-task-index='" << i << "' "
            << "style='text-align:left;justify-content:flex-start;gap:8px'>"
            << status_tag(task.status)
            << "<span style='overflow:hidden;text-overflow:ellipsis'>"
            << html_escape(task.title) << "</span>"
            << "<span style='margin-left:auto;color:var(--muted);font-size:.7rem'>P" << task.priority << "</span>"
            << "</button>";
    }
    out << "</div>"
        << "<div class='inspector-panel' id='task-inspector' role='region' aria-label='Task details'>"
        << "<div class='empty'><div class='empty-icon'>👆</div><div>Select a task</div></div>"
        << "</div></div>"
        << "<script id='task-data' type='application/json'>" << task_data_json(app) << "</script>"
        << "<script>(function(){"
        << "const data=JSON.parse(document.getElementById('task-data').textContent||'[]');"
        << "const panel=document.getElementById('task-inspector');"
        << "const statusColors={running:'var(--accent)',done:'var(--success)',queued:'var(--muted)',paused:'var(--warn)',failed:'var(--danger)',cancelled:'var(--danger)'};"
        << "function render(t){"
        << "if(!t){panel.innerHTML='<div class=\"empty\">Select a task</div>';return;}"
        << "const color=statusColors[t.status]||'var(--muted)';"
        << "let h=`<div style='margin-bottom:10px'>`;"
        << "h+=`<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px'>`;"
        << "h+=`<span style='font-size:1rem;font-weight:700'>${t.title}</span>`;"
        << "h+=`<span class='tag tag-${t.status}'>${t.status}</span>`;"
        << "if(t.validated) h+=`<span class='pill success' style='font-size:.7rem'>✓ validated</span>`;"
        << "h+=`</div>`;"
        << "h+=`<div style='font-size:.78rem;color:var(--muted)'>${t.id} · ${t.kind} · Priority ${t.priority} · Confidence ${(t.confidence*100).toFixed(0)}%</div>`;"
        << "h+=`<p style='margin-top:6px'>${t.description}</p>`;"
        << "h+=`</div>`;"
        << "if(t.assigned_agents.length) h+=`<div class='pill' style='margin-bottom:8px'>Agents: ${t.assigned_agents.slice(0,3).join(', ')}${t.assigned_agents.length>3?' + more':''}</div>`;"
        << "h+=`<h4>Plan (step ${t.step_cursor}/${t.plan.length})</h4>`;"
        << "h+=`<div class='timeline'>`;"
        << "t.plan.forEach((step,idx)=>{"
        << "const active=idx===t.step_cursor;"
        << "const done=idx<t.step_cursor;"
        << "h+=`<div class='timeline-item'>`;"
        << "h+=`<div class='timeline-dot ${done?'done':''}${active?' active':''}'></div>`;"
        << "h+=`<div class='timeline-body'><strong>${step.actor}</strong> ${step.action}`;"
        << "if(step.detail) h+=` — <span style='color:var(--muted)'>${step.detail}</span>`;"
        << "if(active) h+=` <span style='color:var(--accent);font-size:.75rem'>▶ current</span>`;"
        << "h+=`</div></div>`;"
        << "});"
        << "h+=`</div>`;"
        << "if(t.subtasks.length){h+=`<h4 style='margin-top:10px'>Subtasks</h4>`;"
        << "t.subtasks.forEach(s=>{h+=`<div class='pill pill-block'><span class='tag tag-${s.status}'>${s.status}</span>${s.title}</div>`;});}"
        << "if(t.memory.length){h+=`<h4 style='margin-top:10px'>Memory</h4>`;"
        << "t.memory.forEach(m=>{h+=`<div class='pill pill-block' style='color:var(--muted);font-size:.78rem'>${m}</div>`;});}"
        << "panel.innerHTML=h;}"
        << "document.querySelectorAll('.task-btn').forEach(btn=>btn.addEventListener('click',()=>render(data[+btn.dataset.taskIndex])));"
        << "if(data.length)render(data[0]);"
        << "window.selectTask=i=>render(data[i]);"
        << "})();</script>";
    append_task_history(out, app);
}

// ─── Task history (step 10: filter/search/reopen) ────────────────────────────
void append_task_history(std::ostringstream& out, const App& app) {
    const auto tasks = app.tasks();
    out << "<div style='margin-top:16px'>"
        << "<h3>Task history</h3>"
        << "<div style='display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap'>"
        << "<input class='input' id='task-filter-text' placeholder='Search tasks...' style='max-width:200px' oninput='filterTasks()' aria-label='Search tasks'>"
        << "<select class='input' id='task-filter-status' onchange='filterTasks()' style='max-width:130px' aria-label='Filter by status'>"
        << "<option value=''>All status</option>"
        << "<option>queued</option><option>running</option><option>done</option>"
        << "<option>paused</option><option>failed</option><option>cancelled</option>"
        << "</select>"
        << "<select class='input' id='task-filter-kind' onchange='filterTasks()' style='max-width:130px' aria-label='Filter by kind'>"
        << "<option value=''>All kinds</option>"
        << "<option>build</option><option>research</option><option>ops</option>"
        << "<option>ui</option><option>demo</option>"
        << "</select></div>"
        << "<div class='scroll-list' id='task-history-list'>";
    for (const auto& task : tasks) {
        out << "<div class='search-result task-history-row' "
            << "data-status='" << html_escape(task.status) << "' "
            << "data-kind='" << html_escape(task.kind) << "' "
            << "data-title='" << html_escape(task.title) << "'>"
            << "<div style='display:flex;align-items:center;gap:6px'>"
            << status_tag(task.status)
            << "<strong>" << html_escape(task.title) << "</strong>"
            << "<span style='margin-left:auto;font-size:.75rem;color:var(--muted)'>"
            << html_escape(task.kind) << " · P" << task.priority << "</span>"
            << "</div>"
            << "<div style='font-size:.78rem;color:var(--muted);margin-top:2px'>"
            << html_escape(task.description.substr(0, 80)) << "</div>"
            << "</div>";
    }
    if (tasks.empty())
        out << "<div class='empty'><div class='empty-icon'>📋</div><div>No task history</div></div>";
    out << "</div></div>"
        << "<script>(function(){"
        << "window.filterTasks=function(){"
        << "const q=document.getElementById('task-filter-text').value.toLowerCase();"
        << "const st=document.getElementById('task-filter-status').value;"
        << "const kd=document.getElementById('task-filter-kind').value;"
        << "document.querySelectorAll('.task-history-row').forEach(row=>{"
        << "const title=row.dataset.title.toLowerCase();"
        << "const ok=(!q||title.includes(q))&&(!st||row.dataset.status===st)&&(!kd||row.dataset.kind===kd);"
        << "row.style.display=ok?'':'none';});};})();</script>";
}

// ─── Computer playback timeline (steps 21,29) ─────────────────────────────────
void append_computer_playback(std::ostringstream& out, const App& app) {
    const auto log = app.computer_log(50);
    out << "<div class='timeline' id='playback-timeline'>";
    if (log.empty()) {
        out << "<div class='empty'><div class='empty-icon'>🖥</div>"
               "<div>No computer activity yet</div></div>";
    }
    for (std::size_t i = 0; i < log.size(); ++i) {
        const auto& a = log[i];
        const bool is_undo = a.undone;
        out << "<div class='timeline-item' style='" << (is_undo ? "opacity:.4" : "") << "'>"
            << "<div class='timeline-dot " << (is_undo ? "" : "done") << "'></div>"
            << "<div class='timeline-body'>"
            << "<span style='font-size:.72rem;color:var(--muted)'>#" << (i+1) << " · " << html_escape(a.surface) << "</span> "
            << "<strong>" << html_escape(a.agent_id) << "</strong> "
            << "<span class='pill' style='font-size:.72rem'>" << html_escape(a.verb) << "</span> "
            << html_escape(a.target);
        if (!a.detail.empty())
            out << " <span style='color:var(--muted);font-size:.78rem'>— " << html_escape(a.detail.substr(0, 60)) << "</span>";
        if (is_undo)
            out << " <span style='color:var(--danger);font-size:.72rem'>[undone]</span>";
        out << "</div></div>";
    }
    out << "</div>";
}

// ─── LUO OS tree browser (step 1) ─────────────────────────────────────────────
void append_luo_tree(std::ostringstream& out, const App& app) {
    out << "<h3>LUO OS tree</h3>";
    const auto entries = app.search_luo_os("", 300);
    if (entries.empty()) {
        out << "<div class='empty'><div class='empty-icon'>🌲</div>"
               "<div>No LUO OS index loaded</div></div>";
        return;
    }
    out << "<div class='scroll-list'>";
    std::string last_group;
    for (const auto& entry : entries) {
        const auto slash = entry.path.find('/');
        const auto group = slash == std::string::npos ? entry.path : entry.path.substr(0, slash);
        if (group != last_group) {
            last_group = group;
            out << "<div class='pill' style='background:var(--border);color:var(--accent2);font-weight:600;margin-top:6px'>"
                << "📂 " << html_escape(group) << "</div>";
        }
        if (slash != std::string::npos) {
            out << "<div class='pill pill-block' style='padding-left:20px;font-size:.78rem'>"
                << (entry.kind == "dir" ? "📁 " : "📄 ")
                << html_escape(entry.path.substr(slash+1)) << "</div>";
        }
    }
    out << "</div>";
}

// ─── LUO OS index (step 9) ────────────────────────────────────────────────────
void append_luo_index(std::ostringstream& out, const App& app) {
    out << "<h3>LUO OS index</h3>";
    const auto entries = app.luo_index_entries(20);
    if (entries.empty()) {
        out << "<div class='empty' style='font-size:.82rem'>Index empty</div>";
        return;
    }
    out << "<div class='scroll-list'>";
    for (const auto& entry : entries) {
        out << "<div class='pill pill-block'>"
            << "<span class='tag' style='background:var(--surface);color:var(--accent)'>" << html_escape(entry.kind) << "</span>"
            << " " << html_escape(entry.path)
            << "</div>";
    }
    out << "</div>";
}

// ─── Agent roster (steps 12-20, 6) ────────────────────────────────────────────
void append_agents(std::ostringstream& out, const App& app) {
    const auto all_agents = app.agents(20);
    const auto counts = app.role_counts();
    out << "<div style='margin-bottom:10px;display:flex;gap:8px;flex-wrap:wrap'>";
    for (const auto& [role, count] : counts) {
        out << "<span class='pill'>" << html_escape(role) << " <strong>" << count << "</strong></span>";
    }
    out << "</div>"
        << "<div class='agent-grid'>";
    for (const auto& agent : all_agents) {
        const auto css = agent.health == "stuck" ? "stuck" :
                         agent.health == "degraded" ? "degraded" :
                         agent.busy ? "busy" : "";
        out << "<div class='agent-card " << css << "' role='article' aria-label='" << html_escape(agent.id) << "'>"
            << "<div style='font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap'>"
            << html_escape(agent.id) << "</div>"
            << "<div style='color:var(--muted);font-size:.75rem'>" << html_escape(agent.role) << "</div>"
            << "<div style='display:flex;gap:4px;margin-top:4px;flex-wrap:wrap'>";
        if (agent.busy)
            out << "<span class='tag tag-running'>busy</span>";
        else
            out << "<span class='tag tag-done'>free</span>";
        out << "<span class='pill' style='font-size:.68rem'>"
            << static_cast<int>(agent.reliability * 100) << "% reliable</span>";
        out << "</div></div>";
    }
    const auto total = app.agent_count();
    if (total > 20)
        out << "<div class='pill' style='grid-column:1/-1;color:var(--muted);font-size:.78rem'>+ "
            << (total - 20) << " more agents</div>";
    out << "</div>";
}

// ─── Browser history (step 23) ────────────────────────────────────────────────
void append_browser_history(std::ostringstream& out, const App& app) {
    const auto history = app.browser_history(10);
    if (history.empty()) {
        out << "<div class='empty' style='font-size:.82rem'>No browser history</div>";
        return;
    }
    out << "<div class='scroll-list'>";
    for (const auto& snap : history) {
        out << "<div class='search-result'>"
            << "<div style='font-weight:600;font-size:.82rem'>" << html_escape(snap.title) << "</div>"
            << "<div style='font-size:.75rem;color:var(--accent)'>" << html_escape(snap.url) << "</div>";
        if (!snap.text_excerpt.empty())
            out << "<div style='font-size:.75rem;color:var(--muted);margin-top:2px'>"
                << html_escape(snap.text_excerpt.substr(0, 80)) << "</div>";
        out << "</div>";
    }
    out << "</div>";
}

// ─── Terminal history (step 24) ────────────────────────────────────────────────
void append_terminal_history(std::ostringstream& out, const App& app) {
    const auto history = app.terminal_history(8);
    if (history.empty()) {
        out << "<div class='empty' style='font-size:.82rem'>No terminal history</div>";
        return;
    }
    out << "<div class='scroll-list'>";
    for (const auto& t : history) {
        const bool ok = t.exit_code == 0;
        out << "<div style='background:var(--surface2);border-radius:8px;padding:8px;font-family:var(--mono);font-size:.78rem;margin-bottom:4px'>"
            << "<div style='color:var(--accent2)'>$ " << html_escape(t.command) << "</div>"
            << "<div style='color:" << (ok ? "var(--success)" : "var(--danger)") << ";margin-top:2px'>"
            << html_escape(t.output.substr(0, 100)) << "</div>"
            << "<div style='color:var(--muted);font-size:.7rem'>exit " << t.exit_code << "</div>"
            << "</div>";
    }
    out << "</div>";
}

// ─── File browser (step 5, 25) ────────────────────────────────────────────────
void append_file_browser(std::ostringstream& out, const App& app) {
    const auto files = app.files();
    if (files.empty()) {
        out << "<div class='empty'><div class='empty-icon'>📁</div><div>No files</div></div>";
        return;
    }
    out << "<table class='table' role='grid' aria-label='Files'>"
        << "<thead><tr><th>Name</th><th>Size</th><th>Versions</th><th>Scope</th></tr></thead><tbody>";
    for (const auto& f : files) {
        out << "<tr>"
            << "<td><span style='font-family:var(--mono);font-size:.82rem'>" << html_escape(f.name) << "</span></td>"
            << "<td style='color:var(--muted)'>" << f.content.size() << " B</td>"
            << "<td style='color:var(--muted)'>" << f.history.size() << "</td>"
            << "<td style='color:var(--muted)'>" << html_escape(f.project_scope.empty() ? "—" : f.project_scope) << "</td>"
            << "</tr>";
    }
    out << "</tbody></table>";
}

// ─── Project runner (steps 51-57) ─────────────────────────────────────────────
void append_project_runner(std::ostringstream& out, const App& app) {
    const auto projects = app.projects();
    if (projects.empty()) {
        out << "<div class='empty'><div class='empty-icon'>🚀</div><div>No projects</div></div>";
        return;
    }
    out << "<div class='scroll-list'>";
    for (const auto& proj : projects) {
        const bool ok = proj.last_exit_code == 0;
        const bool ran = proj.last_exit_code >= 0;
        out << "<div class='card card-sm' style='margin-bottom:6px'>"
            << "<div style='display:flex;align-items:center;gap:8px'>"
            << "<strong>" << html_escape(proj.name) << "</strong>";
        if (!proj.template_kind.empty())
            out << "<span class='pill' style='font-size:.7rem'>" << html_escape(proj.template_kind) << "</span>";
        if (ran)
            out << "<span class='pill " << (ok ? "success" : "danger") << "' style='font-size:.7rem'>exit " << proj.last_exit_code << "</span>";
        out << "</div>"
            << "<div style='font-family:var(--mono);font-size:.75rem;color:var(--muted);margin-top:4px'>"
            << "$ " << html_escape(proj.command) << "</div>";
        if (!proj.last_output.empty())
            out << "<div style='font-family:var(--mono);font-size:.72rem;color:var(--success);margin-top:4px;max-height:60px;overflow:hidden'>"
                << html_escape(proj.last_output.substr(0, 200)) << "</div>";
        out << "</div>";
    }
    out << "</div>";
}

// ─── Knowledge base (step 47) ────────────────────────────────────────────────
void append_knowledge(std::ostringstream& out, const App& app) {
    const auto entries = app.knowledge_entries(20);
    if (entries.empty()) {
        out << "<div class='empty'><div class='empty-icon'>📚</div><div>No knowledge entries</div></div>";
        return;
    }
    out << "<div class='scroll-list'>";
    for (const auto& k : entries) {
        out << "<div class='search-result'>"
            << "<div style='font-weight:600'>" << html_escape(k.title) << "</div>"
            << "<div style='font-size:.78rem;color:var(--muted);margin-top:2px'>"
            << html_escape(k.body.substr(0, 80)) << "</div>"
            << "</div>";
    }
    out << "</div>";
}

// ─── Memory viewer (steps 41-50) ─────────────────────────────────────────────
void append_memory(std::ostringstream& out, const App& app) {
    const auto entries = app.memory_entries(15);
    if (entries.empty()) {
        out << "<div class='empty'><div class='empty-icon'>🧠</div><div>No memory entries</div></div>";
        return;
    }
    out << "<div class='scroll-list'>";
    for (const auto& m : entries) {
        out << "<div class='pill pill-block' style='flex-direction:column;align-items:flex-start'>"
            << "<span class='tag' style='background:var(--surface);color:var(--muted);margin-bottom:4px'>"
            << html_escape(m.kind) << "</span>"
            << "<span style='font-size:.8rem'>" << html_escape(m.content.substr(0, 80)) << "</span>";
        if (m.summarized)
            out << "<span style='font-size:.7rem;color:var(--warn)'>[summarized]</span>";
        out << "</div>";
    }
    out << "</div>";
}

// ─── Privacy dashboard (step 69) ─────────────────────────────────────────────
void append_privacy_dashboard(std::ostringstream& out, const App& app) {
    const auto c = app.consent();
    const auto s = app.summary();
    out << "<div style='font-size:.82rem'>"
        << "<div class='consent-flag'><input type='checkbox' " << (c.allow_local_storage ? "checked" : "") << " disabled> Local storage</div>"
        << "<div class='consent-flag'><input type='checkbox' " << (c.allow_files ? "checked" : "") << " disabled> File access</div>"
        << "<div class='consent-flag'><input type='checkbox' " << (c.allow_chat_history ? "checked" : "") << " disabled> Chat history</div>"
        << "<div class='consent-flag'><input type='checkbox' " << (c.allow_project_execution ? "checked" : "") << " disabled> Project execution</div>"
        << "<div class='consent-flag'><input type='checkbox' " << (c.allow_device_links ? "checked" : "") << " disabled> Device links</div>"
        << "<div class='consent-flag'><input type='checkbox' " << (c.allow_analytics ? "checked" : "") << " disabled> Analytics</div>"
        << "<div class='consent-flag'><input type='checkbox' " << (s.local_only_mode ? "checked" : "") << " disabled> 🔒 Local-only mode</div>"
        << "</div>"
        << "<div style='margin-top:8px;font-size:.75rem;color:var(--muted)'>"
        << "Stored: " << s.memory_count << " memories · " << s.audit_count << " audit events · "
        << s.file_count << " files · " << s.secret_count << " secrets"
        << "</div>";
}

// ─── Audit log (steps 64, 66) ────────────────────────────────────────────────
void append_audit_log(std::ostringstream& out, const App& app) {
    const auto log = app.audit_log(20);
    if (log.empty()) {
        out << "<div class='empty' style='font-size:.82rem'>No audit events</div>";
        return;
    }
    out << "<div class='scroll-list'>";
    for (const auto& e : log) {
        out << "<div class='pill pill-block' style='font-size:.78rem'>"
            << "<span style='color:var(--muted)'>[" << html_escape(e.actor) << "]</span> "
            << "<strong>" << html_escape(e.action) << "</strong>"
            << " — " << html_escape(e.detail)
            << "</div>";
    }
    out << "</div>";
}

// ─── Devices (step 8, 62) ────────────────────────────────────────────────────
void append_devices(std::ostringstream& out, const App& app) {
    const auto devices = app.devices();
    if (devices.empty()) {
        out << "<div class='empty' style='font-size:.82rem'>No devices linked</div>";
        return;
    }
    out << "<div class='scroll-list'>";
    for (const auto& dev : devices) {
        out << "<div class='pill pill-block'>"
            << (dev.approved ? "✅ " : "⏳ ")
            << html_escape(dev.label)
            << " <span style='margin-left:auto;color:var(--muted);font-size:.75rem'>"
            << html_escape(dev.id) << "</span>"
            << "</div>";
    }
    out << "</div>";
}

// ─── Pending approvals (step 62, 84) ─────────────────────────────────────────
void append_pending_approvals(std::ostringstream& out, const App& app) {
    const auto pending = app.pending_approvals();
    if (pending.empty()) return;
    out << "<div class='card' style='border-color:var(--warn);margin-top:12px'>"
        << "<h3 style='color:var(--warn)'>⚠ Pending Approvals</h3>";
    for (const auto& action : pending) {
        out << "<div class='pill pill-block warn'>"
            << "🔐 " << html_escape(action)
            << "<button class='btn sm danger' style='margin-left:auto'>Approve</button>"
            << "</div>";
    }
    out << "</div>";
}

// ─── Command palette (step 77) ────────────────────────────────────────────────
void append_command_palette(std::ostringstream& out, const App& app) {
    out << "<div class='palette-overlay' id='palette-overlay' role='dialog' aria-label='Command palette' aria-modal='true'>"
        << "<div class='palette-box'>"
        << "<input class='palette-input' id='palette-input' placeholder='Type a command or search...' autocomplete='off' aria-label='Command input'>"
        << "<div class='palette-list' id='palette-list'></div>"
        << "</div></div>"
        << "<script>(function(){"
        << "const commands=["
        << "{kind:'action',label:'Create task',icon:'📋'},"
        << "{kind:'action',label:'Kill all agents',icon:'🛑'},"
        << "{kind:'action',label:'Pause session',icon:'⏸'},"
        << "{kind:'action',label:'Resume session',icon:'▶'},"
        << "{kind:'action',label:'Export workspace',icon:'📦'},"
        << "{kind:'nav',label:'Go to Tasks',icon:'📋'},"
        << "{kind:'nav',label:'Go to Agents',icon:'🤖'},"
        << "{kind:'nav',label:'Go to Files',icon:'📁'},"
        << "{kind:'nav',label:'Go to Projects',icon:'🚀'},"
        << "{kind:'nav',label:'Go to Memory',icon:'🧠'},"
        << "{kind:'nav',label:'Go to Knowledge',icon:'📚'},"
        << "{kind:'nav',label:'Go to Audit log',icon:'🔍'},"
        << "];"
        << "const overlay=document.getElementById('palette-overlay');"
        << "const input=document.getElementById('palette-input');"
        << "const list=document.getElementById('palette-list');"
        << "let active=0;"
        << "function render(q){"
        << "const filtered=commands.filter(c=>c.label.toLowerCase().includes(q.toLowerCase()));"
        << "list.innerHTML=filtered.map((c,i)=>`<div class='palette-item ${i===active?'active':''}' data-idx='${i}'>"
        << "<span class='palette-item-kind'>${c.kind}</span>"
        << "<span>${c.icon} ${c.label}</span></div>`).join('');"
        << "}"
        << "window.openPalette=function(){"
        << "overlay.classList.add('open');input.value='';render('');input.focus();};"
        << "overlay.addEventListener('click',e=>{if(e.target===overlay)overlay.classList.remove('open');});"
        << "input.addEventListener('input',()=>{active=0;render(input.value);});"
        << "input.addEventListener('keydown',e=>{"
        << "if(e.key==='Escape'){overlay.classList.remove('open');}"
        << "if(e.key==='ArrowDown'){active++;render(input.value);}"
        << "if(e.key==='ArrowUp'){active=Math.max(0,active-1);render(input.value);}"
        << "});"
        << "document.addEventListener('keydown',e=>{"
        << "if((e.ctrlKey||e.metaKey)&&e.key==='k'){e.preventDefault();window.openPalette();}"
        << "});"
        << "})();</script>";
}

// ─── Tab navigation (step 77) ─────────────────────────────────────────────────
void append_tabs(std::ostringstream& out,
                 const std::vector<std::pair<std::string,std::string>>& tabs) {
    out << "<div style='display:flex;gap:4px;border-bottom:1px solid var(--border);margin-bottom:16px;overflow-x:auto' role='tablist'>";
    for (std::size_t i = 0; i < tabs.size(); ++i) {
        out << "<button type='button' class='btn" << (i==0?" primary":"") << "' "
            << "onclick='showTab(" << i << ")' "
            << "id='tab-btn-" << i << "' role='tab' "
            << "aria-selected='" << (i==0?"true":"false") << "' "
            << "aria-controls='tab-panel-" << i << "'>"
            << html_escape(tabs[i].first) << "</button>";
    }
    out << "</div>";
    for (std::size_t i = 0; i < tabs.size(); ++i) {
        out << "<div id='tab-panel-" << i << "' role='tabpanel' "
            << "aria-labelledby='tab-btn-" << i << "' "
            << (i==0?"":"style='display:none'") << ">"
            << tabs[i].second << "</div>";
    }
    out << "<script>(function(){"
        << "window.showTab=function(n){"
        << "document.querySelectorAll('[role=tabpanel]').forEach((p,i)=>p.style.display=i===n?'':'none');"
        << "document.querySelectorAll('[role=tab]').forEach((b,i)=>{"
        << "b.classList.toggle('primary',i===n);"
        << "b.setAttribute('aria-selected',i===n);});};"
        << "})();</script>";
}

// ─── Recent activity (step 8) ────────────────────────────────────────────────
void append_recent_activity(std::ostringstream& out, const App& app) {
    const auto traces = app.trace_events(12);
    const auto clog = app.computer_log(8);
    if (traces.empty() && clog.empty()) {
        out << "<div class='empty'><div class='empty-icon'>⚡</div><div>No activity yet</div></div>";
        return;
    }
    out << "<div class='scroll-list'>";
    for (const auto& e : traces) {
        out << "<div class='pill pill-block' style='font-size:.78rem'>"
            << "<span style='color:var(--muted)'>" << html_escape(e.actor) << "</span> "
            << "<strong>" << html_escape(e.action) << "</strong>"
            << " — " << html_escape(e.detail.substr(0, 60)) << "</div>";
    }
    if (!clog.empty()) {
        out << "<div style='border-top:1px solid var(--border);margin:8px 0'></div>";
        for (const auto& a : clog) {
            out << "<div class='pill pill-block' style='font-size:.78rem'>"
                << "🖥 " << html_escape(a.agent_id)
                << " · " << html_escape(a.verb)
                << " <span style='color:var(--muted)'>" << html_escape(a.target) << "</span>"
                << "</div>";
        }
    }
    out << "</div>";
}

// ─── Computers section (step 21, 22) ─────────────────────────────────────────
void append_computers(std::ostringstream& out, const App& app) {
    const auto computers = app.computers();
    if (computers.empty()) {
        out << "<div class='empty'><div class='empty-icon'>🖥</div><div>No computers</div></div>";
        return;
    }
    for (const auto& comp : computers) {
        out << "<div class='card card-sm' style='margin-bottom:8px'>"
            << "<div style='display:flex;align-items:center;gap:8px'>"
            << "<strong>" << html_escape(comp.label) << "</strong>"
            << "<span class='pill' style='font-size:.72rem'>" << html_escape(comp.os) << "</span>"
            << (comp.active ? "<span class='pill success' style='font-size:.72rem'>active</span>" : "")
            << "</div>"
            << "<div style='display:flex;gap:4px;margin-top:6px;flex-wrap:wrap'>";
        for (const auto& surf : comp.surfaces)
            out << "<span class='pill' style='font-size:.72rem'>" << html_escape(surf) << "</span>";
        out << "</div>";
        if (!comp.windows.empty()) {
            out << "<div style='margin-top:6px;font-size:.78rem;color:var(--muted)'>Windows: ";
            for (const auto& w : comp.windows)
                out << html_escape(w.title) << (w.focused ? " 🔵" : "") << " ";
            out << "</div>";
        }
        out << "</div>";
    }
}

} // anonymous namespace

// ─── Main dashboard (steps 71-80) ─────────────────────────────────────────────
std::string render_dashboard_html(const App& app) {
    std::ostringstream out;
    out << "<!doctype html><html lang='en'><head>"
        << "<meta charset='utf-8'>"
        << "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        << "<title>LUO COMPUTER</title>"
        << "<style>" << GLOBAL_CSS << "</style>"
        << "</head><body>";

    append_topbar(out, app);
    append_command_palette(out, app);
    append_pending_approvals(out, app);

    out << "<main class='main' role='main'>";
    append_summary_cards(out, app);

    // Build tab contents
    std::vector<std::pair<std::string,std::string>> tabs;

    // Tab: Overview
    {
        std::ostringstream t;
        t << "<div class='grid grid-3'>"
          << "<div style='display:flex;flex-direction:column;gap:12px'>"
          << "<div class='card'><h3>Recent activity</h3>";
        append_recent_activity(t, app);
        t << "</div>"
          << "<div class='card'><h3>Computers</h3>";
        append_computers(t, app);
        t << "</div>"
          << "<div class='card'><h3>Privacy</h3>";
        append_privacy_dashboard(t, app);
        t << "</div></div>"
          << "<div class='card'>"
          << "<h3>Tasks</h3>";
        append_task_inspector(t, app);
        t << "</div>"
          << "<div style='display:flex;flex-direction:column;gap:12px'>"
          << "<div class='card'><h3>LUO OS tree</h3>";
        append_luo_tree(t, app);
        t << "</div>"
          << "<div class='card'>";
        append_luo_index(t, app);
        t << "</div></div></div>";
        tabs.push_back({"🏠 Overview", t.str()});
    }

    // Tab: Agents
    {
        std::ostringstream t;
        t << "<div class='card'><h3>Agent roster (" << app.agent_count() << ")</h3>";
        append_agents(t, app);
        t << "</div>";
        tabs.push_back({"🤖 Agents", t.str()});
    }

    // Tab: Computer surface
    {
        std::ostringstream t;
        t << "<div class='grid grid-2'>"
          << "<div class='card'><h3>Playback timeline</h3>";
        append_computer_playback(t, app);
        t << "</div>"
          << "<div style='display:flex;flex-direction:column;gap:12px'>"
          << "<div class='card'><h3>Browser history</h3>";
        append_browser_history(t, app);
        t << "</div>"
          << "<div class='card'><h3>Terminal</h3>";
        append_terminal_history(t, app);
        t << "</div></div></div>";
        tabs.push_back({"🖥 Computer", t.str()});
    }

    // Tab: Files
    {
        std::ostringstream t;
        t << "<div class='card'><h3>File browser</h3>";
        append_file_browser(t, app);
        t << "</div>";
        tabs.push_back({"📁 Files", t.str()});
    }

    // Tab: Projects
    {
        std::ostringstream t;
        t << "<div class='card'><h3>Project runner</h3>";
        append_project_runner(t, app);
        t << "</div>";
        tabs.push_back({"🚀 Projects", t.str()});
    }

    // Tab: Memory & Knowledge
    {
        std::ostringstream t;
        t << "<div class='grid grid-2'>"
          << "<div class='card'><h3>Memory store</h3>";
        append_memory(t, app);
        t << "</div>"
          << "<div class='card'><h3>Knowledge base</h3>";
        append_knowledge(t, app);
        t << "</div></div>";
        tabs.push_back({"🧠 Memory", t.str()});
    }

    // Tab: Audit & Devices
    {
        std::ostringstream t;
        t << "<div class='grid grid-2'>"
          << "<div class='card'><h3>Audit log</h3>";
        append_audit_log(t, app);
        t << "</div>"
          << "<div class='card'><h3>Devices</h3>";
        append_devices(t, app);
        t << "</div></div>";
        tabs.push_back({"🔍 Audit", t.str()});
    }

    append_tabs(out, tabs);
    out << "</main></body></html>";
    return out.str();
}

std::string render_status_html(const App& app) {
    const auto s = app.summary();
    std::ostringstream out;
    out << "<!doctype html><html lang='en'><body><pre style='font-family:monospace;padding:20px'>"
        << "LUO COMPUTER STATUS\n"
        << "===================\n"
        << "active_user=" << s.active_user << "\n"
        << "session_stage=" << s.session_stage << "\n"
        << "platform=" << s.platform << "\n"
        << "local_only=" << (s.local_only_mode ? "true" : "false") << "\n"
        << "---\n"
        << "users=" << s.user_count << "\n"
        << "agents=" << s.agent_count << "\n"
        << "tasks=" << s.task_count << "\n"
        << "computers=" << s.computer_count << "\n"
        << "files=" << s.file_count << "\n"
        << "skills=" << s.skill_count << "\n"
        << "projects=" << s.project_count << "\n"
        << "devices=" << s.device_count << "\n"
        << "memory=" << s.memory_count << "\n"
        << "knowledge=" << s.knowledge_count << "\n"
        << "audit=" << s.audit_count << "\n"
        << "</pre></body></html>";
    return out.str();
}

} // namespace luo_gate
