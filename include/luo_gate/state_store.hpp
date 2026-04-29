#pragma once

#include <filesystem>

namespace luo_gate {

class App;

struct StateStore {
    static bool load(App& app);
    static bool save(const App& app);
};

} // namespace luo_gate
