#include "luo_gate/ui.hpp"
#include "luo_gate/platform.hpp"
#include "luo_gate/security.hpp"

#include <sstream>

namespace luo_gate {
namespace {
std::string html_escape(std::string_view text) {
    std::ostringstream out;
    for (char c : text) {
        switch (c) {
            case '&': out << "&amp;"; break;
            case '<': out << "&lt;"; break;
            case '>': out << "&gt;"; break;
            case '"': out << "&quot;"; break;
            case '\'': out << "&#39;"; break;
            default: out << c; break;
        }
    }
    return out.str();
}

std::string json_escape(std::string_view text) {
    std::ostringstream out;
    for (char c : text) {
        switch (c) {
            case '\\': out << "\\\\"; break;
            case '"': out << "\\\""; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            case '<': out << "\\u003c"; break;
            case '>': out << "\\u003e"; break;
            case '&': out << "\\u0026"; break;
            default: out << c; break;
        }
    }
    return out.str();
}

std::string header(std::string_view title) {
    std::ostringstream out;
    out << "<h2>" << html_escape(title) << "</h2>";
    return out.str();
}

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
        out << "\"step_cursor\":" << task.step_cursor << ",";
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
            out << "\"surface\":\"" << json_escape(step.surface) << "\"";
            out << "}";
        }
        out << "]}";
    }
    out << "]";
    return out.str();
}

void append_summary(std::ostringstream& out, const App& app) {
    const auto s = app.summary();
    out << "<ul>"
        << "<li>users: " << s.user_count << "</li>"
        << "<li>agents: " << s.agent_count << "</li>"
        << "<li>tasks: " << s.task_count << "</li>"
        << "<li>computers: " << s.computer_count << "</li>"
        << "<li>files: " << s.file_count << "</li>"
        << "<li>skills: " << s.skill_count << "</li>"
        << "<li>projects: " << s.project_count << "</li>"
        << "<li>devices: " << s.device_count << "</li>"
        << "<li>platform: " << html_escape(s.platform) << "</li>"
        << "</ul>";
}

void append_tasks(std::ostringstream& out, const App& app) {
    out << "<div class='list task-list'>";
    const auto tasks = app.tasks();
    for (std::size_t i = 0; i < tasks.size(); ++i) {
        const auto& task = tasks[i];
        out << "<button type='button' class='pill task-btn' data-task-index='" << i << "'>"
            << html_escape(task.id) << " · " << html_escape(task.title) << " · " << html_escape(task.status)
            << "</button>";
    }
    if (tasks.empty()) {
        out << "<div class='pill'>No tasks yet.</div>";
    }
    out << "</div>";
}

void append_task_inspector(std::ostringstream& out, const App& app) {
    out << "<div class='task-shell'>"
        << "<div class='task-list-panel'>"
        << "<h3>Task list</h3>";
    append_tasks(out, app);
    out << "</div>"
        << "<div class='task-inspector-panel'>"
        << "<h3>Task inspector</h3>"
        << "<div id='task-inspector' class='inspector'>Select a task.</div>"
        << "</div>"
        << "</div>"
        << "<script id='task-data' type='application/json'>" << task_data_json(app) << "</script>"
        << "<script>(function(){"
        << "const data = JSON.parse(document.getElementById('task-data').textContent || '[]');"
        << "const inspector = document.getElementById('task-inspector');"
        << "function clear(node){while(node.firstChild)node.removeChild(node.firstChild);}"
        << "function addText(parent, tag, text, cls){const el=document.createElement(tag); if(cls) el.className=cls; el.textContent=text; parent.appendChild(el); return el;}"
        << "function render(task){clear(inspector); if(!task){addText(inspector,'div','No task selected.','pill'); return;}"
        << "addText(inspector,'div',task.id,'pill');"
        << "addText(inspector,'div',task.title,'pill');"
        << "addText(inspector,'div','Kind: '+task.kind);"
        << "addText(inspector,'div','Owner: '+task.owner);"
        << "addText(inspector,'div','Status: '+task.status);"
        << "addText(inspector,'div','Current step: '+(task.step_cursor < task.plan.length ? task.plan[task.step_cursor].action : 'done'));"
        << "addText(inspector,'p',task.description);"
        << "const agents = document.createElement('div'); agents.className='pill'; agents.textContent='Assigned agents: ' + (task.assigned_agents.length ? task.assigned_agents.join(', ') : 'none'); inspector.appendChild(agents);"
        << "const stepsTitle = document.createElement('h4'); stepsTitle.textContent = 'Plan'; inspector.appendChild(stepsTitle);"
        << "const list = document.createElement('div'); list.className='trace';"
        << "task.plan.forEach((step, idx) => { const row=document.createElement('div'); row.className='pill'; row.textContent = (idx === task.step_cursor ? '▶ ' : '') + step.index + ': ' + step.actor + ' · ' + step.action + ' — ' + step.detail; list.appendChild(row); });"
        << "inspector.appendChild(list); }"
        << "function selectTask(index){ render(data[index]); }"
        << "document.querySelectorAll('.task-btn').forEach(btn => btn.addEventListener('click', () => selectTask(parseInt(btn.dataset.taskIndex || '0', 10))));"
        << "if(data.length) selectTask(0);"
        << "window.selectTask = selectTask;"
        << "})();</script>";
}

void append_computers(std::ostringstream& out, const App& app) {
    out << "<div class='list'>";
    for (const auto& computer : app.computers()) {
        out << "<div class='pill'>" << html_escape(computer.label) << " · " << html_escape(computer.os) << "</div>";
    }
    out << "</div>";
}

void append_luo_index(std::ostringstream& out, const App& app) {
    out << "<div class='list'>";
    for (const auto& entry : app.luo_index_entries(20)) {
        out << "<div class='pill'>" << html_escape(entry.kind) << " · " << html_escape(entry.path) << "</div>";
    }
    out << "</div>";
}

void append_luo_tree(std::ostringstream& out, const App& app) {
    out << "<div class='list'>";
    const auto entries = app.search_luo_os("", 200);
    std::string last_group;
    for (const auto& entry : entries) {
        const auto slash = entry.path.find('/');
        const auto group = slash == std::string::npos ? entry.path : entry.path.substr(0, slash);
        if (group != last_group) {
            last_group = group;
            out << "<div class='pill group'>" << html_escape(group) << "</div>";
        }
    }
    if (entries.empty()) {
        out << "<div class='pill'>No LUO OS index loaded.</div>";
    }
    out << "</div>";
}

void append_trace(std::ostringstream& out, const App& app) {
    out << "<div class='trace'>";
    for (const auto& e : app.trace_events(24)) {
        out << "<div><strong>" << html_escape(e.actor) << "</strong> " << html_escape(e.action) << " — " << html_escape(e.detail) << "</div>";
    }
    out << "</div>";
}

void append_computer_playback(std::ostringstream& out, const App& app) {
    out << "<div class='trace'>";
    const auto log = app.computer_log(24);
    for (std::size_t i = 0; i < log.size(); ++i) {
        const auto& a = log[i];
        out << "<div class='pill'>Playback " << (i + 1) << ". " << html_escape(a.agent_id) << " on " << html_escape(a.surface)
            << " · " << html_escape(a.verb) << " " << html_escape(a.target) << " — " << html_escape(a.detail) << "</div>";
    }
    if (log.empty()) {
        out << "<div class='pill'>No computer activity yet.</div>";
    }
    out << "</div>";
}
}

std::string render_dashboard_html(const App& app) {
    const auto s = app.summary();
    std::ostringstream out;
    out << "<!doctype html><html><head><meta charset='utf-8'><title>LUO COMPUTER</title>"
        << "<style>body{font-family:system-ui;background:#0b1020;color:#e6edf3;margin:0;padding:24px}"
        << ".grid{display:grid;grid-template-columns:240px 1fr 340px;gap:16px;align-items:start}"
        << ".card{background:#121a33;border:1px solid #243155;border-radius:16px;padding:16px}"
        << ".pill{display:block;padding:8px 10px;border-radius:12px;background:#243155;margin:6px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border:none;color:#e6edf3;text-align:left;width:100%}"
        << ".task-shell{display:grid;grid-template-columns:1fr 1.2fr;gap:12px}"
        << ".task-list,.trace,.list{max-height:320px;overflow:auto}"
        << ".task-inspector-panel{background:#0f1730;border:1px solid #243155;border-radius:14px;padding:12px;min-height:280px}"
        << ".group{background:#2e6b8a}"
        << "</style></head><body>";
    out << header("LUO COMPUTER")
        << "<p>Platform: " << html_escape(operating_system_name()) << " · Active: " << html_escape(app.current_user()) << "</p>"
        << "<div class='grid'>"
        << "<section class='card'><h3>Swarm</h3><p>Agents: " << s.agent_count << "</p><p>Tasks: " << s.task_count << "</p><p>Roles: ";
    for (const auto& [role, count] : s.role_counts) out << "<span class='pill'>" << html_escape(role) << ": " << count << "</span>";
    out << "</p><p>Computer: " << s.computer_count << "</p><p>Imported LUO OS: active</p></section>"
        << "<section class='card'><h3>Tasks</h3>";
    append_task_inspector(out, app);
    out << "<h3>Computer surfaces</h3>";
    append_computers(out, app);
    out << "<h3>LUO OS tree</h3>";
    append_luo_tree(out, app);
    out << "<h3>LUO OS index</h3>";
    append_luo_index(out, app);
    out << "</section><section class='card'><h3>Vault</h3><p>Secrets: " << s.secret_count << "</p><p>Files: " << s.file_count << "</p><p>Skills: " << s.skill_count << "</p></section></div>";
    out << "<section class='card' style='margin-top:16px'><h3>Visible trace</h3>";
    append_trace(out, app);
    out << "<h3>Computer Playback</h3><p>computer actions timeline</p>";
    append_computer_playback(out, app);
    out << "</section></body></html>";
    return out.str();
}

std::string render_status_html(const App& app) {
    const auto s = app.summary();
    std::ostringstream out;
    out << "<!doctype html><html><body><pre>"
        << "users=" << s.user_count << "\n"
        << "agents=" << s.agent_count << "\n"
        << "tasks=" << s.task_count << "\n"
        << "computers=" << s.computer_count << "\n"
        << "files=" << s.file_count << "\n"
        << "skills=" << s.skill_count << "\n"
        << "projects=" << s.project_count << "\n"
        << "devices=" << s.device_count << "\n"
        << "platform=" << html_escape(s.platform) << "\n"
        << "</pre></body></html>";
    return out.str();
}

} // namespace luo_gate
