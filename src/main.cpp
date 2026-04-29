#include "luo_gate/app.hpp"
#include "luo_gate/server.hpp"
#include "luo_gate/startup.hpp"

#include <filesystem>
#include <iostream>

int main(int argc, char** argv) {
    using namespace luo_gate;
    App app;
    app.load();

    int port = 3000;
    if (argc > 1) {
        port = std::stoi(argv[1]);
    }
    StartupFlow flow(app);
    const auto exe_path = std::filesystem::absolute(argv[0]);
    const int status = flow.run(port, exe_path);
    std::cout << "Startup flow completed with status " << status << ".\n";
    return status;
}
