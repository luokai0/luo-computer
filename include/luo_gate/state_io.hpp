#pragma once

namespace luo_gate {

class App;

struct StateIO {
    static bool load(App& app);
    static bool save(const App& app);
};

} // namespace luo_gate
