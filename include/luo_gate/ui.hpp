#pragma once

#include "luo_gate/app.hpp"

#include <string>

namespace luo_gate {

std::string render_dashboard_html(const App& app);
std::string render_status_html(const App& app);

} // namespace luo_gate
