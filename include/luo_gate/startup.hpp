#pragma once

#include "luo_gate/app.hpp"

#include <filesystem>
#include <iosfwd>

namespace luo_gate {

class StartupFlow {
public:
    StartupFlow(App& app, std::istream& in = std::cin, std::ostream& out = std::cout);
    int run(int port, const std::filesystem::path& exe_path);

private:
    bool ensure_authenticated();
    bool ensure_session();
    bool prepare_workspace(const std::filesystem::path& exe_path);

    std::string prompt_line(std::string_view label, std::string default_value = {});
    bool confirm(std::string_view label, bool default_yes = true);
    std::filesystem::path locate_luo_os_root(const std::filesystem::path& exe_path);
    void show_banner();

    App& app_;
    std::istream& in_;
    std::ostream& out_;
};

} // namespace luo_gate
