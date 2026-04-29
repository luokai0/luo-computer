#include "luo_gate/app.hpp"
#include "luo_gate/security.hpp"

#include <algorithm>
#include <iomanip>
#include <sstream>
#include <utility>

namespace luo_gate {

bool App::register_user(const std::string& username, const std::string& password, const std::string& email) {
    if (!is_valid_username(username) || !is_valid_password(password)) {
        return false;
    }
    if (users_.contains(username)) {
        return false;
    }
    users_.emplace(username, User{username, password, email});
    if (active_user_.empty()) {
        active_user_ = username;
    }
    return true;
}

bool App::login(const std::string& username, const std::string& password) {
    const auto it = users_.find(username);
    if (it == users_.end() || it->second.password != password) {
        return false;
    }
    active_user_ = username;
    return true;
}

void App::logout() {
    active_user_.clear();
}

bool App::authenticated() const {
    return !active_user_.empty();
}

std::string App::current_user() const {
    return active_user_;
}

void App::create_thread(const std::string& thread_id, const std::string& title) {
    chats_.try_emplace(thread_id, ChatThread{thread_id, title, {}});
}

bool App::add_message(const std::string& thread_id, const std::string& author, const std::string& text) {
    auto it = chats_.find(thread_id);
    if (it == chats_.end()) {
        return false;
    }
    it->second.messages.push_back(ChatMessage{author, text});
    return true;
}

std::vector<ChatThread> App::threads() const {
    std::vector<ChatThread> out;
    out.reserve(chats_.size());
    for (const auto& [_, thread] : chats_) {
        out.push_back(thread);
    }
    std::sort(out.begin(), out.end(), [](const auto& a, const auto& b) { return a.id < b.id; });
    return out;
}

void App::set_api_key(const std::string& service, const std::string& key) {
    api_keys_[service] = key;
}

std::unordered_map<std::string, std::string> App::api_keys() const {
    return api_keys_; 
}

void App::upload_file(const std::string& name, const std::string& content) {
    files_.push_back(FileRecord{name, content});
}

std::vector<FileRecord> App::files() const {
    return files_;
}

void App::add_skill(const std::string& name, const std::string& description) {
    skills_.push_back(SkillRecord{name, description});
}

std::vector<SkillRecord> App::skills() const {
    return skills_;
}

std::string App::export_state() const {
    std::ostringstream out;
    out << "{\"user\":\"" << active_user_ << "\",";
    out << "\"users\":" << users_.size() << ",";
    out << "\"threads\":" << chats_.size() << ",";
    out << "\"files\":" << files_.size() << ",";
    out << "\"skills\":" << skills_.size() << "}";
    return out.str();
}

} // namespace luo_gate
