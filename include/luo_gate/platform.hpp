#pragma once

#include <filesystem>
#include <string>

namespace luo_gate {

std::filesystem::path home_directory();
std::filesystem::path default_data_root();
std::string operating_system_name();

} // namespace luo_gate
