#include "luo_gate/app.hpp"
#include "luo_gate/server.hpp"

#include <filesystem>
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

    const std::filesystem::path exe_path = std::filesystem::absolute(argv[0]);
    const auto repo_root = exe_path.parent_path().parent_path();
    const auto luo_os_root = std::filesystem::exists(repo_root / "luo_os") ? (repo_root / "luo_os") : (std::filesystem::current_path() / "luo_os");
    app.import_luo_os(luo_os_root);
    app.create_task("Bootstrap swarm", "Create the first visible swarm with roles and jobs", "bootstrap");
    app.tick();
    app.save();

    int port = 3000;
    if (argc > 1) {
        port = std::stoi(argv[1]);
    }
    std::cout << "LUO COMPUTER is installed. Open the app, then click Start Session to begin.\n";
    std::cout << "LUO OS is embedded in the session workspace at: " << luo_os_root.string() << "\n";
    return run_server(app, port);
}
