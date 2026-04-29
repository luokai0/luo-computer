#pragma once

#include <filesystem>
#include <string>
#include <string_view>
#include <vector>

namespace luo_gate {

struct LuoIndexEntry {
    std::string path;
    std::string kind;
    std::string summary;
};

struct LuoIndex {
    std::vector<LuoIndexEntry> entries;
};

LuoIndex build_luo_index(const std::filesystem::path& root);
std::vector<LuoIndexEntry> search_luo_index(const LuoIndex& index, std::string_view query, std::size_t limit = 50);

} // namespace luo_gate
