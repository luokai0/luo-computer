#include "luo_gate/ui.hpp"
#include "luo_gate/security.hpp"

#include <sstream>

namespace luo_gate {
namespace {
std::string header(const std::string& title) {
    std::ostringstream out;
    out << "=== " << title << " ===\n";
    return out.str();
}
} // namespace

std::string render_welcome_screen() {
    return header("LUO GATE") + "[ Start ]\n";
}

std::string render_login_screen() {
    return header("Sign in / Log in") + "username\npassword\nemail (optional)\n";
}

std::string render_main_screen(const App& app) {
    std::ostringstream out;
    out << header("Main")
        << "user: " << app.current_user() << "\n"
        << "left: settings | chats | api keys | logout\n"
        << "center: chat\n"
        << "right: uploads\n";
    return out.str();
}

std::string render_settings_screen(const App&) {
    return header("Settings") + "privacy, profile, security, device permissions\n";
}

std::string render_api_screen(const App& app) {
    std::ostringstream out;
    out << header("API Keys");
    for (const auto& [service, key] : app.api_keys()) {
        out << service << ": " << redacted(key) << "\n";
    }
    return out.str();
}

} // namespace luo_gate
