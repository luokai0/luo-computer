#pragma once

#include <string>
#include <string_view>
#include <vector>

namespace luo_gate {

bool is_valid_username(std::string_view username);
bool is_valid_password(std::string_view password);
std::string password_hash(std::string_view username, std::string_view password);
std::string json_escape(std::string_view text);
std::string redacted(const std::string& value);
std::vector<std::string> split_csv(std::string_view text);
std::string join_csv(const std::vector<std::string>& values);

} // namespace luo_gate
