#pragma once

#include <string>
#include <string_view>

namespace luo_gate {

bool is_valid_username(std::string_view username);
bool is_valid_password(std::string_view password);
std::string redacted(const std::string& value);

} // namespace luo_gate
