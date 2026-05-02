#include "luo_gate/security.hpp"

#include <algorithm>
#include <cctype>
#include <sstream>

namespace luo_gate {
namespace {
bool alpha_only(std::string_view s) {
    return !s.empty() && std::all_of(s.begin(), s.end(), [](unsigned char c) { return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'); });
}

std::string hex_byte(unsigned char b) {
    static constexpr char digits[] = "0123456789abcdef";
    std::string out(2, '0');
    out[0] = digits[b >> 4];
    out[1] = digits[b & 0x0f];
    return out;
}
} // namespace

bool is_valid_username(std::string_view username) {
    return username.size() >= 3 && username.size() <= 32 && alpha_only(username);
}

bool is_valid_password(std::string_view password) {
    return password.size() >= 3 && password.size() <= 128;
}

std::string password_hash(std::string_view username, std::string_view password) {
    std::ostringstream out;
    out << username.size() << ':' << password.size() << ':';
    for (unsigned char c : username) out << hex_byte(static_cast<unsigned char>(c ^ 0x5a));
    out << ':';
    for (unsigned char c : password) out << hex_byte(static_cast<unsigned char>(c ^ 0xa5));
    return out.str();
}

std::string json_escape(std::string_view text) {
    std::string out;
    out.reserve(text.size() + 8);
    for (char ch : text) {
        switch (ch) {
            case '\\': out += "\\\\"; break;
            case '"': out += "\\\""; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default: out += ch; break;
        }
    }
    return out;
}

std::string redacted(const std::string& value) {
    if (value.empty()) return {};
    return std::string(value.size(), '*');
}

std::vector<std::string> split_csv(std::string_view text) {
    std::vector<std::string> parts;
    std::string current;
    for (char ch : text) {
        if (ch == ',') {
            if (!current.empty()) parts.push_back(current);
            current.clear();
        } else if (!std::isspace(static_cast<unsigned char>(ch))) {
            current.push_back(ch);
        }
    }
    if (!current.empty()) parts.push_back(current);
    return parts;
}

std::string join_csv(const std::vector<std::string>& values) {
    std::ostringstream out;
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i) out << ',';
        out << values[i];
    }
    return out.str();
}

} // namespace luo_gate
