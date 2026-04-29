#include "luo_gate/server.hpp"
#include "luo_gate/ui.hpp"

#include <fstream>
#include <sstream>
#include <thread>

namespace luo_gate {

int run_server(App& app, int port) {
    std::ostringstream fake;
    fake << "LUO COMPUTER server stub on port " << port << "\n";
    fake << render_dashboard_html(app);
    fake << render_status_html(app);
    std::ofstream(app.data_root() / "server.preview.html") << fake.str();
    return 0;
}

} // namespace luo_gate
