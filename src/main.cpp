#include "luo_gate/app.hpp"
#include "luo_gate/server.hpp"

#include <iostream>

int main(int argc, char** argv) {
    using namespace luo_gate;
    App app;
    app.load();
    if (!app.has_user("Luo")) {
        app.register_user("Luo", "Gate", {}, ConsentFlags{});
    }
    app.login("Luo", "Gate");
    app.attach_computer("local", "Local Computer", "luo-os", {"computer", "browser", "terminal", "files"}, true);
    app.create_task("Bootstrap swarm", "Create the first visible swarm with roles and jobs", "bootstrap");
    app.tick();
    app.save();

    int port = 3000;
    if (argc > 1) {
        port = std::stoi(argv[1]);
    }
    std::cout << "LUO COMPUTER starting on port " << port << "\n";
    return run_server(app, port);
}
