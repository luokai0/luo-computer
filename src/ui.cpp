#include "luo_gate/ui.hpp"
#include "luo_gate/platform.hpp"
#include "luo_gate/security.hpp"

#include <sstream>

namespace luo_gate {
namespace {
std::string header(std::string_view title) {
    std::ostringstream out;
    out << "<h2>" << title << "</h2>";
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
        << "<li>platform: " << s.platform << "</li>"
        << "</ul>";
}

void append_tasks(std::ostringstream& out, const App& app) {
    out << "<div class='list'>";
    for (const auto& task : app.tasks()) {
        out << "<div class='pill'>" << task.id << " · " << task.title << " · " << task.status << "</div>";
    }
    out << "</div>";
}

void append_computers(std::ostringstream& out, const App& app) {
    out << "<div class='list'>";
    for (const auto& computer : app.computers()) {
        out << "<div class='pill'>" << computer.label << " · " << computer.os << "</div>";
    }
    out << "</div>";
}

void append_luo_index(std::ostringstream& out, const App& app) {
    out << "<div class='list'>";
    for (const auto& entry : app.luo_index_entries(20)) {
        out << "<div class='pill'>" << entry.kind << " · " << entry.path << "</div>";
    }
    out << "</div>";
}

void append_trace(std::ostringstream& out, const App& app) {
    out << "<div class='trace'>";
    for (const auto& e : app.trace_events(24)) {
        out << "<div><strong>" << e.actor << "</strong> " << e.action << " — " << e.detail << "</div>";
    }
    out << "</div>";
}

void append_computer_log(std::ostringstream& out, const App& app) {
    out << "<div class='trace'>";
    for (const auto& a : app.computer_log(24)) {
        out << "<div><strong>" << a.agent_id << "</strong> on <em>" << a.surface << "</em> " << a.verb << " " << a.target << " — " << a.detail << "</div>";
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
        << ".pill{display:block;padding:8px 10px;border-radius:12px;background:#243155;margin:6px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}"
        << ".trace{max-height:320px;overflow:auto;font-size:14px;line-height:1.35}"
        << ".list{max-height:220px;overflow:auto}"
        << "</style></head><body>";
    out << header("LUO COMPUTER")
        << "<p>Platform: " << operating_system_name() << " · Active: " << app.current_user() << "</p>"
        << "<div class='grid'>"
        << "<section class='card'><h3>Swarm</h3><p>Agents: " << s.agent_count << "</p><p>Tasks: " << s.task_count << "</p><p>Roles: ";
    for (const auto& [role, count] : s.role_counts) out << "<span class='pill'>" << role << ": " << count << "</span>";
    out << "</p><p>Computer: " << s.computer_count << "</p><p>Imported LUO OS: active</p></section>"
        << "<section class='card'><h3>Tasks</h3>";
    append_tasks(out, app);
    out << "<h3>Computer surfaces</h3>";
    append_computers(out, app);
    out << "<h3>LUO OS index</h3>";
    append_luo_index(out, app);
    out << "</section><section class='card'><h3>Vault</h3><p>Secrets: " << s.secret_count << "</p><p>Files: " << s.file_count << "</p><p>Skills: " << s.skill_count << "</p></section></div>";
    out << "<section class='card' style='margin-top:16px'><h3>Visible trace</h3>";
    append_trace(out, app);
    out << "<h3>Computer actions</h3>";
    append_computer_log(out, app);
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
        << "platform=" << s.platform << "\n"
        << "</pre></body></html>";
    return out.str();
}

} // namespace luo_gate
