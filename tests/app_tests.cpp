#include "luo_gate/app.hpp"
#include "luo_gate/security.hpp"

#include <cassert>
#include <filesystem>
#include <iostream>

int main() {
    using namespace luo_gate;

    assert(is_valid_username("Luo"));
    assert(!is_valid_username("Kai77"));
    assert(!is_valid_username("ab"));
    assert(is_valid_password("Gate"));

    App app;
    assert(app.register_user("Luo", "Gate"));
    assert(app.login("Luo", "Gate"));

    assert(app.agent_count() == 10000);
    assert(app.computers().size() == 1);
    assert(app.attach_computer("desktop", "Desktop", "linux", {"computer", "browser", "terminal"}, true));
    assert(app.set_active_computer("desktop"));
    assert(app.import_luo_os(std::filesystem::path("luo_os")) == false);
    assert(app.create_task("Build swarm", "Break work into roles", "build"));
    assert(app.tick());

    assert(app.set_secret("search", "alpha-key"));
    assert(app.upload_file("brief.md", "task brief"));
    assert(app.add_skill("orchestrate", "swarm orchestration", {"agent", "task"}));
    assert(app.add_project("demo", "Demo", "echo demo"));
    assert(app.link_device("macbook", "MacBook", {"approved"}, true));

    const auto summary = app.summary();
    assert(summary.user_count == 1);
    assert(summary.agent_count >= 10000);
    assert(summary.task_count == 1);
    assert(summary.computer_count >= 1);
    assert(summary.secret_count == 1);
    assert(summary.file_count == 1);
    assert(summary.skill_count == 1);
    assert(summary.project_count == 1);
    assert(summary.device_count == 1);

    const auto state = app.export_state();
    assert(state.find("\"users\":1") != std::string::npos);
    assert(state.find("\"agents\":") != std::string::npos);
    assert(state.find("\"tasks\":1") != std::string::npos);
    assert(state.find("\"computers\":") != std::string::npos);

    std::cout << "luo-computer tests passed\n";
    return 0;
}
