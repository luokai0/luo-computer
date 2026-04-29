#include "luo_gate/startup.hpp"
#include "luo_gate/platform.hpp"

#include <algorithm>
#include <cctype>
#include <iostream>

namespace luo_gate {

StartupFlow::StartupFlow(App& app, std::istream& in, std::ostream& out)
    : app_(app), in_(in), out_(out) {}

int StartupFlow::run(int port, const std::filesystem::path& exe_path) {
    show_banner();

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

    if (app_.tasks().empty()) {
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

} // namespace luo_gate
