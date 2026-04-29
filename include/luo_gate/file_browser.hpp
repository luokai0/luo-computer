#pragma once

#include "luo_gate/app.hpp"

#include <filesystem>
#include <string>
#include <vector>

namespace luo_gate {

struct FileBrowserEntry {
    std::string path;
    bool is_directory = false;
    std::string preview;
};

std::vector<FileBrowserEntry> browse_files(const std::filesystem::path& root, std::size_t limit = 200);
std::string render_file_browser_html(const App& app);

} // namespace luo_gate
