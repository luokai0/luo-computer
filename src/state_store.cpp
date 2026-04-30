#include "luo_gate/state_store.hpp"
#include "luo_gate/state_io.hpp"
#include <string_view>

namespace luo_gate {

bool StateStore::load(App& app) {
    if (!StateIO::load_global(app)) return false;
    app.rebuild_luo_index();  // Restore in-memory index from persisted root path
    if (!app.current_user().empty()) {
        return StateIO::load_workspace(app, app.current_user());
    }
    return true;
}

bool StateStore::save(const App& app) {
    if (!StateIO::save_global(app)) return false;
    if (!app.current_user().empty()) {
        return StateIO::save_workspace(app, app.current_user());
    }
    return true;
}

} // namespace luo_gate
