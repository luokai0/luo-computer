#pragma once

#include "luo_gate/luo_index.hpp"

#include <cstdint>
#include <filesystem>
#include <map>
#include <string>
#include <string_view>
#include <vector>

namespace luo_gate {

using Timestamp = std::int64_t;

struct ConsentFlags {
    bool accept_terms = true;
    bool allow_local_storage = true;
    bool allow_files = true;
    bool allow_chat_history = true;
    bool allow_project_execution = false;
    bool allow_device_links = false;
    bool allow_analytics = false;
};

struct UserRecord {
    std::string username;
    std::string password_hash;
    std::string email;
    ConsentFlags consent;
};

struct AgentProfile {
    std::string id;
    std::string role;
    std::vector<std::string> expertise;
    int capacity = 100;
    bool busy = false;
    std::string task_id;
    double reliability = 0.9;
    std::string availability = "always";
    double cost_per_task = 1.0;
};

struct TaskStep {
    std::size_t index = 0;
    std::string actor;
    std::string action;
    std::string detail;
    Timestamp created_at = 0;
    std::string surface = "computer";
};

struct TaskRecord {
    std::string id;
    std::string title;
    std::string description;
    std::string kind;
    std::string status = "queued";
    std::string owner;
    std::vector<std::string> required_roles;
    std::vector<std::string> assigned_agents;
    std::vector<TaskStep> plan;
    std::size_t step_cursor = 0;
    Timestamp created_at = 0;
    Timestamp updated_at = 0;
    std::vector<std::string> memory;
    std::size_t memory_cursor = 0;
    std::string current_agent_id;
};

struct ComputerRecord {
    std::string id;
    std::string label;
    std::string os;
    std::vector<std::string> surfaces;
    bool active = true;
};

struct ComputerAction {
    Timestamp created_at = 0;
    std::string computer_id;
    std::string agent_id;
    std::string surface;
    std::string verb;
    std::string target;
    std::string detail;
};

struct SecretRecord {
    std::string service;
    std::string value;
    std::string scope;
};

struct FileRecord {
    std::string name;
    std::string content;
    Timestamp created_at = 0;
};

struct SkillRecord {
    std::string name;
    std::string description;
    std::vector<std::string> tags;
};

struct ProjectRecord {
    std::string id;
    std::string name;
    std::string command;
    std::string cwd;
    bool executable = false;
    int last_exit_code = -1;
    std::string last_output;
};

struct DeviceLink {
    std::string id;
    std::string label;
    std::vector<std::string> scopes;
    bool approved = false;
};

struct TraceEvent {
    Timestamp created_at = 0;
    std::string category;
    std::string actor;
    std::string action;
    std::string detail;
};

struct ApprovalRecord {
    std::string action;
    std::string detail;
    bool granted = false;
    Timestamp recorded_at = 0;
    Timestamp granted_at = 0;
};

struct Workspace {
    ConsentFlags consent;
    std::vector<AgentProfile> agents;
    std::vector<TaskRecord> tasks;
    std::vector<ComputerRecord> computers;
    std::string active_computer_id;
    std::vector<ComputerAction> computer_log;
    std::vector<SecretRecord> secrets;
    std::vector<FileRecord> files;
    std::vector<SkillRecord> skills;
    std::vector<ProjectRecord> projects;
    std::vector<DeviceLink> devices;
    std::vector<TraceEvent> trace;
    std::vector<TraceEvent> audit;
    std::vector<ApprovalRecord> approvals;
    std::vector<std::string> pending_approvals;
};

struct Summary {
    std::size_t user_count = 0;
    std::size_t agent_count = 0;
    std::size_t task_count = 0;
    std::size_t computer_count = 0;
    std::size_t secret_count = 0;
    std::size_t file_count = 0;
    std::size_t skill_count = 0;
    std::size_t project_count = 0;
    std::size_t device_count = 0;
    std::size_t audit_count = 0;
    std::string active_user;
    std::string platform;
    std::map<std::string, std::size_t> role_counts;
};

enum class SessionStage { Idle, Starting, Running, Paused, Failed, Resumed };

inline const char* session_stage_to_string(SessionStage stage) {
    switch (stage) {
        case SessionStage::Idle: return "idle";
        case SessionStage::Starting: return "starting";
        case SessionStage::Running: return "running";
        case SessionStage::Paused: return "paused";
        case SessionStage::Failed: return "failed";
        case SessionStage::Resumed: return "resumed";
    }
    return "idle";
}

inline SessionStage session_stage_from_string(std::string_view text) {
    if (text == "starting") return SessionStage::Starting;
    if (text == "running") return SessionStage::Running;
    if (text == "paused") return SessionStage::Paused;
    if (text == "failed") return SessionStage::Failed;
    if (text == "resumed") return SessionStage::Resumed;
    return SessionStage::Idle;
}

struct SessionState {
    bool resumed = false;
    std::string title;
    std::string note;
    Timestamp last_started_at = 0;
    Timestamp last_resumed_at = 0;
    SessionStage stage = SessionStage::Idle;
    std::string stage_detail;
    Timestamp stage_updated_at = 0;
};

class App {
public:
    explicit App(std::filesystem::path data_root = {});

    bool load();
    bool save() const;

    bool has_user(std::string_view username) const;
    std::vector<std::string> users() const;

    bool register_user(std::string username, std::string password, std::string email = {}, ConsentFlags consent = {});
    bool login(std::string_view username, std::string_view password);
    bool export_user_settings(const std::filesystem::path& destination) const;
    bool import_user_settings(const std::filesystem::path& source);
    bool reset_workspace();

    // New workspace APIs

    ConsentFlags consent() const;
    bool set_consent(ConsentFlags consent);

    bool start_session(std::string title, std::string note = {});
    bool resume_session();
    bool pause_session(std::string reason = "Paused by user");
    bool fail_session(std::string reason = "Session failed");
    void reset_session();
    SessionState session_state() const;

    bool add_agent(std::string id, std::string role, std::vector<std::string> expertise = {}, int capacity = 100);
    bool create_task(std::string title, std::string description, std::string kind = "general");
    bool tick();
    bool reopen_task(std::string task_id);
    bool resume_task(std::string task_id);
    std::vector<TaskRecord> tasks() const;
    std::vector<TaskStep> trace(std::size_t limit = 120) const;
    std::vector<TraceEvent> trace_events(std::size_t limit = 120) const;

    std::size_t agent_count() const;
    std::vector<AgentProfile> agents(std::size_t limit = 200) const;
    std::map<std::string, std::size_t> role_counts() const;

    bool attach_computer(std::string id, std::string label, std::string os = {}, std::vector<std::string> surfaces = {}, bool active = true);
    bool set_active_computer(std::string_view id);
    bool import_luo_os(std::filesystem::path source_root);
    std::vector<ComputerRecord> computers() const;
    std::vector<ComputerAction> computer_log(std::size_t limit = 200) const;
    std::string active_computer_id() const;
    bool record_computer_action(std::string computer_id, std::string agent_id, std::string surface, std::string verb, std::string target, std::string detail);

    std::vector<LuoIndexEntry> luo_index_entries(std::size_t limit = 200) const;
    std::vector<LuoIndexEntry> search_luo_os(std::string_view query, std::size_t limit = 20) const;

    bool set_secret(std::string service, std::string value, std::string scope = "local");
    std::vector<SecretRecord> secrets() const;

    bool upload_file(std::string name, std::string content);
    std::vector<FileRecord> files() const;

    bool add_skill(std::string name, std::string description, std::vector<std::string> tags = {});
    std::vector<SkillRecord> skills() const;

    bool add_project(std::string id, std::string name, std::string command, std::string cwd = {}, bool executable = true);
    std::vector<ProjectRecord> projects() const;

    bool link_device(std::string id, std::string label, std::vector<std::string> scopes = {}, bool approved = false);
    std::vector<DeviceLink> devices() const;

    std::vector<TraceEvent> audit_log(std::size_t limit = 200) const;
    bool add_trace(std::string category, std::string actor, std::string action, std::string detail);
    Summary summary() const;

    bool require_approval(std::string action, std::string detail);
    bool approve_action(std::string action);
    std::vector<std::string> pending_approvals() const;

    std::string export_state() const;
    std::filesystem::path data_root() const;

private:
    void set_session_stage(SessionStage stage, std::string detail);
    void record_approval(std::string action, std::string detail, bool granted);
    bool has_approval(std::string action) const;
    friend struct StateIO;
    friend struct StateStore;

    Workspace& workspace();
    const Workspace& workspace() const;
    UserRecord& active_user_record();
    const UserRecord& active_user_record() const;

    void ensure_workspace_seeded();
    void seed_swarm(Workspace& ws);
    bool seed_agents_from_config(Workspace& ws);
    void seed_default_swarm(Workspace& ws);
    std::vector<std::string> roles_for_kind(std::string_view kind) const;
    std::vector<std::string> assign_agents(Workspace& ws, const std::vector<std::string>& roles, const std::string& task_id);
    AgentProfile* find_best_agent(Workspace& ws, std::string_view role);
    void release_agents(Workspace& ws, const TaskRecord& task);
    void record_trace(std::string category, std::string actor, std::string action, std::string detail);
    void record_audit(std::string actor, std::string action, std::string detail);
    void remember_step(TaskRecord& task, TaskStep step);
    void touch();
    std::filesystem::path state_file() const;
    static Timestamp now();

    std::filesystem::path data_root_;
    std::filesystem::path luo_os_root_;
    LuoIndex luo_os_index_;
    SessionState session_;
    std::map<std::string, UserRecord> users_;
    std::map<std::string, Workspace> workspaces_;
    std::string active_user_;
    bool auto_save_ = true;
};

} // namespace luo_gate
