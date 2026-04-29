#include "luo_gate/platform.hpp"

#include <cstdlib>

namespace luo_gate {

std::filesystem::path home_directory() {
    if (const char* home = std::getenv("HOME")) return home;
    if (const char* userprofile = std::getenv("USERPROFILE")) return userprofile;
    return std::filesystem::current_path();
}

std::filesystem::path default_data_root() {
    return home_directory() / ".luo-computer";
}

std::string operating_system_name() {
#if defined(_WIN32)
    return "windows";
#elif defined(__APPLE__)
    return "macos";
#elif defined(__linux__)
    return "linux";
#else
    return "unknown";
#endif
}

} // namespace luo_gate
