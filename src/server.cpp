#include "luo_gate/server.hpp"
#include "luo_gate/ui.hpp"

#include <fstream>

namespace luo_gate {

int run_server(App& app, int port) {
    const auto dashboard = render_dashboard_html(app);
    const auto status = render_status_html(app);
    std::ofstream(app.data_root() / "server.preview.html") << dashboard << "\n" << status;
    std::ofstream(app.data_root() / "server.port.txt") << port;
    return 0;
}

} // namespace luo_gate
