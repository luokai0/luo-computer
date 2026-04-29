#include "luo_gate/luo_index.hpp"

#include <algorithm>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <initializer_list>
#include <iterator>
#include <sstream>

namespace luo_gate {
namespace {
bool match_extension(const std::filesystem::path& path, const std::initializer_list<const char*>& exts) {
    auto ext = path.extension().string();
    std::transform(ext.begin(), ext.end(), ext.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    for (const auto* candidate : exts) {
        if (ext == candidate) return true;
    }
    return false;
}

std::string summarize_file(const std::filesystem::path& path, std::size_t max_chars = 200) {
    std::ifstream in(path);
    if (!in) return {};
    std::string text((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    if (text.size() > max_chars) text.resize(max_chars);
    return text;
}

std::string kind_for(const std::filesystem::path& path) {
    if (std::filesystem::is_directory(path)) return "dir";
    if (match_extension(path, {".py"})) return "python";
    if (match_extension(path, {".md", ".markdown"})) return "markdown";
    if (match_extension(path, {".ts", ".tsx", ".js", ".jsx"})) return "web";
    if (match_extension(path, {".cpp", ".cc", ".cxx", ".c", ".hpp", ".h"})) return "cpp";
    if (match_extension(path, {".json", ".yaml", ".yml"})) return "config";
    return "file";
}

bool contains_case_insensitive(std::string_view haystack, std::string_view needle) {
    if (needle.empty()) return true;
    auto it = std::search(haystack.begin(), haystack.end(), needle.begin(), needle.end(), [](char a, char b) {
        return std::tolower(static_cast<unsigned char>(a)) == std::tolower(static_cast<unsigned char>(b));
    });
    return it != haystack.end();
}
} // namespace

LuoIndex build_luo_index(const std::filesystem::path& root) {
    LuoIndex index;
    if (!std::filesystem::exists(root)) return index;
    for (const auto& entry : std::filesystem::recursive_directory_iterator(root)) {
        if (entry.path().filename() == ".git" || entry.path().string().find("/node_modules/") != std::string::npos) continue;
        const auto rel = std::filesystem::relative(entry.path(), root).string();
        std::string summary;
        if (entry.is_regular_file()) summary = summarize_file(entry.path());
        index.entries.push_back(LuoIndexEntry{rel, kind_for(entry.path()), summary});
    }
    return index;
}

std::vector<LuoIndexEntry> search_luo_index(const LuoIndex& index, std::string_view query, std::size_t limit) {
    std::vector<LuoIndexEntry> out;
    for (const auto& entry : index.entries) {
        if (contains_case_insensitive(entry.path, query) || contains_case_insensitive(entry.kind, query) || contains_case_insensitive(entry.summary, query)) {
            out.push_back(entry);
            if (out.size() >= limit) break;
        }
    }
    return out;
}

} // namespace luo_gate
