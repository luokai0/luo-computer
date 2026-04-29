#pragma once

#include "luo_gate/app.hpp"

#include <string>

namespace luo_gate {

std::string render_welcome_screen();
std::string render_login_screen();
std::string render_main_screen(const App& app);
std::string render_settings_screen(const App& app);
std::string render_api_screen(const App& app);

} // namespace luo_gate
