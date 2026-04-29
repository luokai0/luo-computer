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
}

std::string render_dashboard_html(const App& app) {
    const auto s = app.summary();
    std::ostringstream out;
    out << "<!doctype html><html><head><meta charset='utf-8'><title>LUO COMPUTER</title>"
        << "<style>body{font-family:system-ui;background:#0b1020;color:#e6edf3;margin:0;padding:24px}"
        << ".grid{display:grid;grid-template-columns:240px 1fr 340px;gap:16px;align-items:start}"
        << ".card{background:#121a33;border:1px solid #243155;border-radius:16px;padding:16px}"
        << ".pill{display:inline-block;padding:4px 8px;border-radius:999px;background:#243155;margin:4px 6px 0 0}"
        << ".trace{max-height:320px;overflow:auto;font-size:14px;line-height:1.35}"
        << "</style></head><body>";
    out << header("LUO COMPUTER")
        << "<p>Platform: " << operating_system_name() << " · Active: " << app.current_user() << "</p>"
        << "<div class='grid'>"
        << "<section class='card'><h3>Swarm</h3><p>Agents: " << s.agent_count << "</p><p>Tasks: " << s.task_count << "</p><p>Roles: ";
    for (const auto& [role, count] : s.role_counts) out << "<span class='pill'>" << role << ": " << count << "</span>";
    out << "</p><p>Computer: " << s.computer_count << "</p></section>"
        << "<section class='card'><h3>Tasks</h3>";
    for (const auto& t : app.tasks()) {
        out << "<div class='pill'>" << t.title << " · " << t.status << "</div><br/>";
    }
    out << "<h3>Computer surfaces</h3>";
    for (const auto& c : app.computers()) {
        out << "<div class='pill'>" << c.label << " · " << c.os << "</div>";
    }
    out << "</section><section class='card'><h3>Vault</h3><p>Secrets: " << s.secret_count << "</p><p>Files: " << s.file_count << "</p><p>Skills: " << s.skill_count << "</p></section></div>";
    out << "<section class='card' style='margin-top:16px'><h3>Visible trace</h3><div class='trace'>";
    for (const auto& e : app.trace_events(24)) {
        out << "<div><strong>" << e.actor << "</strong> " << e.action << " — " << e.detail << "</div>";
    }
    out << "<h3>Computer actions</h3>";
    for (const auto& a : app.computer_log(24)) {
        out << "<div><strong>" << a.agent_id << "</strong> on <em>" << a.surface << "</em> " << a.verb << " " << a.target << " — " << a.detail << "</div>";
    }
    out << "</div></section></body></html>";
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
