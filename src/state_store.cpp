#include "luo_gate/state_store.hpp"
#include "luo_gate/state_io.hpp"

namespace luo_gate {

bool StateStore::load(App& app) {
    return StateIO::load(app);
}

bool StateStore::save(const App& app) {
    return StateIO::save(app);
}

} // namespace luo_gate
