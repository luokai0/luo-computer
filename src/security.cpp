#include "luo_gate/security.hpp"

#include <algorithm>

namespace luo_gate {
namespace {
bool alpha_only(std::string_view s) {
    return !s.empty() && std::all_of(s.begin(), s.end(), [](unsigned char c) { return c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z'; });
}
} // namespace

bool is_valid_username(std::string_view username) {
    return username.size() >= 3 && username.size() <= 6 && alpha_only(username);
}

bool is_valid_password(std::string_view password) {
    return password.size() >= 3 && password.size() <= 6 && alpha_only(password);
}

std::string redacted(const std::string& value) {
    if (value.empty()) {
        return "";
    }
    return std::string(value.size(), '*');
}

} // namespace luo_gate
