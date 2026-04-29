#pragma once

#include "luo_gate/app.hpp"

#include <filesystem>
#include <string>
#include <vector>

namespace luo_gate {

class App;

struct StateIO {
    static bool load_global(App& app);
    static bool save_global(const App& app);
    static bool load_workspace(App& app, std::string_view username);
    static bool save_workspace(const App& app, std::string_view username);
};

} // namespace luo_gate
