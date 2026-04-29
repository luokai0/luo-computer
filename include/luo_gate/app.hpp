#pragma once

#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace luo_gate {

struct User {
    std::string username;
    std::string password;
    std::string email;
};

struct ChatMessage {
    std::string author;
    std::string text;
};

struct ApiKeys {
    std::unordered_map<std::string, std::string> values;
};

struct ChatThread {
    std::string id;
    std::string title;
    std::vector<ChatMessage> messages;
};

struct FileRecord {
    std::string name;
    std::string content;
};

struct SkillRecord {
    std::string name;
    std::string description;
};

class App {
public:
    bool register_user(const std::string& username, const std::string& password, const std::string& email = {});
    bool login(const std::string& username, const std::string& password);
    void logout();

    [[nodiscard]] bool authenticated() const;
    [[nodiscard]] std::string current_user() const;

    void create_thread(const std::string& thread_id, const std::string& title);
    bool add_message(const std::string& thread_id, const std::string& author, const std::string& text);
    [[nodiscard]] std::vector<ChatThread> threads() const;

    void set_api_key(const std::string& service, const std::string& key);
    [[nodiscard]] std::unordered_map<std::string, std::string> api_keys() const;

    void upload_file(const std::string& name, const std::string& content);
    [[nodiscard]] std::vector<FileRecord> files() const;

    void add_skill(const std::string& name, const std::string& description);
    [[nodiscard]] std::vector<SkillRecord> skills() const;

    [[nodiscard]] std::string export_state() const;

private:
    static bool valid_username(std::string_view username);
    static bool valid_password(std::string_view password);

    std::unordered_map<std::string, User> users_;
    std::unordered_map<std::string, ChatThread> chats_;
    std::unordered_map<std::string, std::string> api_keys_;
    std::vector<FileRecord> files_;
    std::vector<SkillRecord> skills_;
    std::string active_user_;
};

} // namespace luo_gate
