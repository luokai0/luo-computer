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
    assert(app.create_task("Build swarm", "Break work into roles", "build"));
    assert(app.tick());

    const auto repo_root = std::filesystem::current_path().parent_path();
    const auto luo_os_root = repo_root / "luo_os";
    assert(std::filesystem::exists(luo_os_root));
    assert(app.import_luo_os(luo_os_root));
    assert(!app.luo_index_entries().empty());
    assert(!app.search_luo_os("README").empty());

    assert(app.set_secret("search", "alpha-key"));
    assert(app.upload_file("brief.md", "task brief"));
    assert(app.add_skill("orchestrate", "swarm orchestration", {"agent", "task"}));
    assert(app.add_project("demo", "Demo", "echo demo"));
    assert(app.link_device("macbook", "MacBook", {"approved"}, true));

    const auto summary = app.summary();
    assert(summary.user_count == 1);
    assert(summary.agent_count >= 10000);
    assert(summary.task_count >= 1);
    assert(summary.computer_count >= 1);
    assert(summary.secret_count == 1);
    assert(summary.file_count == 1);
    assert(summary.skill_count == 1);
    assert(summary.project_count == 1);
    assert(summary.device_count == 1);

    const auto state = app.export_state();
    assert(state.find("\"users\":1") != std::string::npos);
    assert(state.find("\"agents\":") != std::string::npos);
    assert(state.find("\"tasks\":") != std::string::npos);
    assert(state.find("\"computers\":") != std::string::npos);

    const auto temp_root = std::filesystem::temp_directory_path() / "luo-computer-state-test";
    std::filesystem::remove_all(temp_root);
    {
        App saved(temp_root);
        assert(saved.register_user("Luo", "Gate"));
        assert(saved.login("Luo", "Gate"));
        assert(saved.attach_computer("desk", "Desk", "linux", {"computer", "browser"}, true));
        assert(saved.import_luo_os(luo_os_root));
        assert(saved.create_task("Persist", "Save and reload", "build"));
        assert(saved.tick());
        assert(saved.save());
    }
    {
        App loaded(temp_root);
        assert(loaded.load());
        assert(loaded.has_user("Luo"));
        assert(loaded.login("Luo", "Gate"));
        assert(loaded.computers().size() >= 1);
        assert(loaded.tasks().size() >= 1);
        assert(!loaded.luo_index_entries().empty());
        assert(!loaded.search_luo_os("README").empty());
    }
    std::filesystem::remove_all(temp_root);

    std::cout << "luo-computer tests passed\n";
    return 0;
}
