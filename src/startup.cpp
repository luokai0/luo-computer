#include "luo_gate/startup.hpp"
#include "luo_gate/platform.hpp"

#include <algorithm>
#include <array>
#include <cctype>
#include <iostream>

namespace luo_gate {

StartupFlow::StartupFlow(App& app, std::istream& in, std::ostream& out)
    : app_(app), in_(in), out_(out), first_run_(false) {}

int StartupFlow::run(int port, const std::filesystem::path& exe_path) {
    show_banner();
    show_capabilities();
    show_limitations();
    show_consent_notice();

    if (!ensure_authenticated()) {
        out_ << "Authentication failed.\n";
        return 1;
    }

    if (!ensure_session()) {
        out_ << "Unable to start or resume a session.\n";
        return 2;
    }

    const auto luo_os_root = locate_luo_os_root(exe_path);
    if (luo_os_root.empty()) {
        out_ << "Could not locate the embedded luo_os/ tree.\n";
        return 3;
    }

    if (!prepare_workspace(luo_os_root)) {
        out_ << "Workspace preparation failed.\n";
        return 4;
    }

    if (first_run_) {
        offer_demo_mode();
        first_run_ = false;
    }

    out_ << "Launching LUO COMPUTER on port " << port << "...\n";
    return run_server(app_, port);
}

bool StartupFlow::ensure_authenticated() {
    while (true) {
        const auto username = prompt_line("Username", "Luo");
        const auto password = prompt_line("Password", "Gate");

        if (app_.login(username, password)) {
            out_ << "Logged in as " << username << "\n";
            return true;
        }

        if (!app_.has_user(username) && confirm("No such user. Create account?")) {
            if (app_.register_user(username, password, {}, ConsentFlags{})) {
                app_.login(username, password);
                out_ << "Account created for " << username << "\n";
                return true;
            }
        }

        out_ << "Login failed. Try again.\n";
    }
}

bool StartupFlow::ensure_session() {
    const auto state = app_.session_state();
    if (state.last_started_at == 0) {
        out_ << "Starting a fresh session.\n";
        return app_.start_session("LUO COMPUTER session", "Auto-started by launch flow");
    }

    if (state.resumed) {
        out_ << "Resuming session '" << state.title << "'.\n";
        return true;
    }

    const auto choice = confirm("Resume last session '" + state.title + "'?", true);
    if (choice) {
        return app_.resume_session();
    }

    return app_.start_session("LUO COMPUTER session", "Auto-started by launch flow");
}

bool StartupFlow::prepare_workspace(const std::filesystem::path& exe_path) {
    if (!app_.import_luo_os(exe_path)) {
        out_ << "Failed to import LUO OS.\n";
        return false;
    }

    first_run_ = app_.tasks().empty();
    if (first_run_) {
        app_.create_task("Bootstrap swarm", "Create the first visible swarm", "bootstrap");
        app_.tick();
    }
    app_.save();
    out_ << "Workspace seeded at " << app_.data_root() << "\n";
    return true;
}

std::string StartupFlow::prompt_line(std::string_view label, std::string default_value) {
    out_ << label;
    if (!default_value.empty()) {
        out_ << " [" << default_value << "]";
    }
    out_ << ": " << std::flush;

    std::string value;
    std::getline(in_, value);
    if (value.empty()) {
        return default_value;
    }
    return value;
}

bool StartupFlow::confirm(std::string_view label, bool default_yes) {
    out_ << label << " (" << (default_yes ? "Y/n" : "y/N") << "): " << std::flush;
    std::string answer;
    std::getline(in_, answer);
    if (answer.empty()) return default_yes;
    const auto lower = std::string(answer);
    std::transform(lower.begin(), lower.end(), lower.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return lower == "y" || lower == "yes";
}

std::filesystem::path StartupFlow::locate_luo_os_root(const std::filesystem::path& exe_path) {
    const auto repo_root = exe_path.parent_path().parent_path();
    if (std::filesystem::exists(repo_root / "luo_os")) return repo_root / "luo_os";
    const auto cwd = std::filesystem::current_path();
    if (std::filesystem::exists(cwd / "luo_os")) return cwd / "luo_os";
    return {};
}

void StartupFlow::show_banner() {
    out_ << "LUO COMPUTER" << "\n";
    out_ << "==============" << "\n";
    out_ << "A visible swarm runtime powered by the LUO OS tree." << "\n";
    out_ << "" << "\n";
}

void StartupFlow::show_capabilities() {
    out_ << "Capabilities:\n";
    out_ << "- Visible swarm of seeded agents coordinating tasks in real time\n";
    out_ << "- Auditable timeline of computer actions, tasks, and agent plans\n";
    out_ << "- Self-hosted LUO OS tree with browser, terminal, files, and project runner support\n";
    out_ << "- Structured session state so you can pause/resume, inspect, and replay\n";
    out_ << "" << "\n";
}

void StartupFlow::show_limitations() {
    out_ << "Limitations:\n";
    out_ << "- Local-only data; no outbound network actions unless explicitly allowed\n";
    out_ << "- No stealth monitoring—every computer action is logged and visible\n";
    out_ << "- Agents follow deterministic roles; there is no unpredictable autonomy yet\n";
    out_ << "" << "\n";
}

void StartupFlow::show_consent_notice() {
    out_ << "Consent info:\n";
    out_ << "- You can toggle consent for history, files, devices, and analytics anytime\n";
    out_ << "- Sensitive actions require explicit approval before running\n";
    out_ << "- All secrets and logs stay in your workspace; nothing is shared externally\n";
    out_ << "\n";
}

bool StartupFlow::offer_demo_mode() {
    if (!confirm("Run the first-run demo with sample agents, tasks, and actions?", true)) {
        return false;
    }
    const auto computer = app_.active_computer_id();
    const std::array<std::pair<const char*, const char*>, 2> demos = {
        std::pair{"Demo research task", "Walk through the LUO OS tree and gather context"},
        std::pair{"Demo project task", "Launch a safe project execution to show artifacts"},
    };
    int created = 0;
    for (const auto& [title, desc] : demos) {
        if (app_.create_task(title, desc, "demo")) {
            created++;
            app_.tick();
        }
    }
    app_.record_computer_action(computer, "demo-agent", "computer", "inspect", "demo", "Demo tasks created");
    app_.record_computer_action(computer, "demo-agent", "computer", "deliver", "demo", "Sample playback available");
    out_ << "Demo mode created " << created << " tasks and logged two computer events.\n";
    return created > 0;
}

} // namespace luo_gate
