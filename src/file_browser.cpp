#include "luo_gate/file_browser.hpp"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <sstream>

namespace luo_gate {
namespace {
std::string html_escape(std::string_view text) {
    std::ostringstream out;
    for (char c : text) {
        switch (c) {
            case '&': out << "&amp;"; break;
            case '<': out << "&lt;"; break;
            case '>': out << "&gt;"; break;
            case '"': out << "&quot;"; break;
            case '\'': out << "&#39;"; break;
            default: out << c; break;
        }
    }
    return out.str();
}

std::string preview_file(const std::filesystem::path& path, std::size_t max_chars = 120) {
    std::ifstream in(path);
    if (!in) return {};
    std::string text((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    if (text.size() > max_chars) text.resize(max_chars);
    return text;
}

} // namespace

std::vector<FileBrowserEntry> browse_files(const std::filesystem::path& root, std::size_t limit) {
    std::vector<FileBrowserEntry> out;
    if (!std::filesystem::exists(root)) return out;

    for (const auto& entry : std::filesystem::recursive_directory_iterator(root)) {
        if (out.size() >= limit) break;
        const auto rel = std::filesystem::relative(entry.path(), root).string();
        if (rel.rfind(".git", 0) == 0) continue;
        if (entry.is_directory()) {
            out.push_back(FileBrowserEntry{rel, true, {}});
        } else if (entry.is_regular_file()) {
            out.push_back(FileBrowserEntry{rel, false, preview_file(entry.path())});
        }
    }

    std::sort(out.begin(), out.end(), [](const auto& a, const auto& b) {
        if (a.is_directory != b.is_directory) return a.is_directory > b.is_directory;
        return a.path < b.path;
    });
    return out;
}

std::string render_file_browser_html(const App& app) {
    std::ostringstream out;
    out << "<section class='card'><h3>File browser</h3>";
    out << "<div class='file-browser-grid'>";
    out << "<div><h4>Workspace</h4><div class='list'>";
    for (const auto& entry : browse_files(app.data_root(), 80)) {
        out << "<div class='pill'>" << html_escape(entry.path) << (entry.is_directory ? " /" : "") << "</div>";
    }
    out << "</div></div>";
    out << "<div><h4>LUO OS</h4><div class='list'>";
    if (!app.luo_index_entries().empty()) {
        for (const auto& entry : app.luo_index_entries(80)) {
            out << "<div class='pill'>" << html_escape(entry.path) << "</div>";
        }
    } else {
        out << "<div class='pill'>No LUO OS files loaded.</div>";
    }
    out << "</div></div>";
    out << "</div></section>";
    return out.str();
}

} // namespace luo_gate
