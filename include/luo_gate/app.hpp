#pragma once

#include "luo_gate/luo_index.hpp"
#include "luo_gate/search_index.hpp"

#include <atomic>
#include <cstdint>
#include <filesystem>
#include <map>
#include <mutex>
#include <optional>
#include <set>
#include <string>
#include <string_view>
#include <thread>
#include <vector>

namespace luo_gate {

using Timestamp = std::int64_t;

// ─── Consent ────────────────────────────────────────────────────────────────
struct ConsentFlags {
    bool accept_terms            = true;
    bool allow_local_storage     = true;
    bool allow_files             = true;
    bool allow_chat_history      = true;
    bool allow_project_execution = false;
    bool allow_device_links      = false;
    bool allow_analytics         = false;
};

// ─── Users ───────────────────────────────────────────────────────────────────
struct UserRecord {
    std::string  username;
    std::string  password_hash;
    std::string  email;
    ConsentFlags consent;
};

// ─── Agent system (steps 12-20) ─────────────────────────────────────────────
struct AgentSkill {
    std::string name;
    std::string level;   // "beginner" | "intermediate" | "expert"
    std::string domain;
};

struct AgentProfile {
    std::string              id;
    std::string              role;
    std::vector<std::string> expertise;
    int                      capacity    = 100;
    bool                     busy        = false;
    std::string              task_id;
    double                   reliability = 0.9;
    std::string              availability = "always"; // "always"|"daytime"|"on-demand"
    double                   cost_per_task = 1.0;
    Timestamp                last_active = 0;
    std::vector<AgentSkill>  skills;
    int                      load        = 0;   // active subtask count
    std::string              health      = "ok"; // "ok"|"degraded"|"stuck"
    Timestamp                stuck_since = 0;
};

// ─── Tasks ───────────────────────────────────────────────────────────────────
struct TaskStep {
    std::size_t index     = 0;
    std::string actor;
    std::string action;
    std::string detail;
    Timestamp   created_at = 0;
    std::string surface    = "computer";
    std::string status     = "pending"; // "pending"|"running"|"done"|"failed"
    std::string agent_id;               // agent that executed this step
    std::string output;                 // captured output/result
};

struct SubTask {
    std::string              id;
    std::string              parent_id;
    std::string              title;
    std::string              kind;
    std::string              status    = "queued";
    std::vector<std::string> depends_on;
    std::string              agent_id;
    Timestamp                created_at = 0;
    Timestamp                updated_at = 0;
};

struct TaskRecord {
    std::string              id;
    std::string              title;
    std::string              description;
    std::string              kind;
    std::string              status      = "queued";
    std::string              owner;
    std::vector<std::string> required_roles;
    std::vector<std::string> assigned_agents;
    std::vector<TaskStep>    plan;
    std::size_t              step_cursor  = 0;
    Timestamp                created_at   = 0;
    Timestamp                updated_at   = 0;
    std::vector<std::string> memory;
    std::size_t              memory_cursor = 0;
    std::string              current_agent_id;
    std::vector<SubTask>     subtasks;
    int                      priority     = 5;     // 1=highest, 10=lowest
    int                      budget_steps = 100;
    int                      budget_secs  = 3600;
    double                   confidence   = 0.0;
    std::string              cancel_reason;
    std::vector<std::string> replay_log;
    bool                     validated    = false;
};

// ─── Computer surface (steps 21-30) ─────────────────────────────────────────
struct WindowRecord {
    std::string id;
    std::string title;
    std::string surface; // "browser"|"terminal"|"files"|"editor"
    bool        focused = false;
    int         x = 0, y = 0, w = 800, h = 600;
};

struct BrowserSnapshot {
    std::string url;
    std::string title;
    std::string text_excerpt;
    Timestamp   captured_at = 0;
};

struct TerminalOutput {
    std::string command;
    std::string output;
    int         exit_code  = -1;
    Timestamp   created_at = 0;
};

struct ComputerRecord {
    std::string              id;
    std::string              label;
    std::string              os;
    std::vector<std::string> surfaces;
    bool                     active = true;
    std::vector<WindowRecord> windows;
};

struct ComputerAction {
    Timestamp   created_at  = 0;
    std::string computer_id;
    std::string agent_id;
    std::string surface;
    std::string verb;
    std::string target;
    std::string detail;
    bool        undone      = false;
    std::string undo_detail;
};

// ─── Memory & knowledge (steps 41-50) ────────────────────────────────────────
struct MemoryEntry {
    std::string id;
    std::string user;
    std::string kind;    // "chat"|"task"|"fact"|"summary"
    std::string content;
    std::string source;  // task_id or "user"
    Timestamp   created_at = 0;
    Timestamp   summarized_at = 0;
    bool        summarized = false;
    std::vector<std::string> tags;
    std::string provenance; // where the fact came from
};

struct KnowledgeEntry {
    std::string id;
    std::string title;
    std::string body;
    std::vector<std::string> tags;
    Timestamp   created_at = 0;
    Timestamp   updated_at = 0;
};

// ─── Files, projects, execution (steps 51-60) ────────────────────────────────
struct FileVersion {
    std::string content;
    Timestamp   saved_at   = 0;
    std::string saved_by;
};

struct FileDiff {
    std::string old_content;
    std::string new_content;
    std::string patch;
};

struct SecretRecord {
    std::string service;
    std::string value;
    std::string scope;
};

struct FileRecord {
    std::string              name;
    std::string              content;
    Timestamp                created_at = 0;
    std::vector<FileVersion> history;
    std::string              project_scope;
};

struct SkillRecord {
    std::string              name;
    std::string              description;
    std::vector<std::string> tags;
};

struct ProjectRun {
    int         exit_code = -1;
    std::string output;
    Timestamp   ran_at    = 0;
    std::string phase;    // "setup"|"run"|"teardown"
};

struct ProjectRecord {
    std::string              id;
    std::string              name;
    std::string              command;
    std::string              cwd;
    bool                     executable    = false;
    int                      last_exit_code = -1;
    std::string              last_output;
    std::vector<ProjectRun>  runs;
    std::string              template_kind; // "web"|"cli"|"data"|"automation"
    std::vector<std::string> dependencies;
};

struct DeviceLink {
    std::string              id;
    std::string              label;
    std::vector<std::string> scopes;
    bool                     approved   = false;
    Timestamp                linked_at  = 0;
    std::string              permission_level; // "read"|"write"|"admin"
};

// ─── Safety & trust (steps 61-70) ────────────────────────────────────────────
struct ApprovalRecord {
    std::string action;
    std::string detail;
    bool        granted      = false;
    Timestamp   recorded_at  = 0;
    Timestamp   granted_at   = 0;
};

struct PolicyRule {
    std::string id;
    std::string action_pattern;
    std::string decision;  // "allow"|"deny"|"require_approval"
    std::string reason;
};

// ─── Trace ───────────────────────────────────────────────────────────────────
struct TraceEvent {
    Timestamp   created_at = 0;
    std::string category;
    std::string actor;
    std::string action;
    std::string detail;
};

// ─── Agent messages ──────────────────────────────────────────────────────────
struct AgentMessage {
    std::string agent_id;
    std::string category;
    std::string content;
    Timestamp   created_at = 0;
};

// ─── Workspace ───────────────────────────────────────────────────────────────
struct Workspace {
    ConsentFlags              consent;
    std::vector<AgentProfile> agents;
    std::vector<TaskRecord>   tasks;
    std::vector<ComputerRecord> computers;
    std::string               active_computer_id;
    std::vector<ComputerAction> computer_log;
    std::vector<SecretRecord> secrets;
    std::vector<FileRecord>   files;
    std::vector<SkillRecord>  skills;
    std::vector<ProjectRecord> projects;
    std::vector<DeviceLink>   devices;
    std::vector<TraceEvent>   trace;
    std::vector<TraceEvent>   audit;
    std::vector<AgentMessage> inbox;
    std::vector<ApprovalRecord> approvals;
    std::vector<std::string>  pending_approvals;
    // Memory & knowledge
    std::vector<MemoryEntry>  memory_store;
    std::vector<KnowledgeEntry> knowledge;
    // Safety
    std::vector<PolicyRule>   policies;
    bool                      local_only_mode = true;
    // Terminal & browser history
    std::vector<TerminalOutput> terminal_history;
    std::vector<BrowserSnapshot> browser_history;
    // Windows
    std::vector<WindowRecord>  open_windows;
    // RBAC
    std::map<std::string, std::string> role_permissions; // user->role
};

// ─── Summary ─────────────────────────────────────────────────────────────────
struct Summary {
    std::size_t user_count    = 0;
    std::size_t agent_count   = 0;
    std::size_t task_count    = 0;
    std::size_t computer_count = 0;
    std::size_t secret_count  = 0;
    std::size_t file_count    = 0;
    std::size_t skill_count   = 0;
    std::size_t project_count = 0;
    std::size_t device_count  = 0;
    std::size_t audit_count   = 0;
    std::size_t memory_count  = 0;
    std::size_t knowledge_count = 0;
    std::string active_user;
    std::string platform;
    std::map<std::string, std::size_t> role_counts;
    std::string session_stage;
    bool        local_only_mode = true;
};

// ─── Session ─────────────────────────────────────────────────────────────────
enum class SessionStage { Idle, Starting, Running, Paused, Failed, Resumed };

struct SessionState {
    bool        resumed           = false;
    std::string title;
    std::string note;
    Timestamp   last_started_at   = 0;
    Timestamp   last_resumed_at   = 0;
    SessionStage stage            = SessionStage::Idle;
    std::string stage_detail;
    Timestamp   stage_updated_at  = 0;
};

// ─── App ─────────────────────────────────────────────────────────────────────
class App {
public:
    explicit App(std::filesystem::path data_root = {});
    ~App() { stop_tick_engine(); }

    bool load();
    bool save() const;

    // Auth
    bool has_user(std::string_view username) const;
    std::vector<std::string> users() const;
    bool register_user(std::string username, std::string password,
                       std::string email = {}, ConsentFlags consent = {});
    bool login(std::string_view username, std::string_view password);
    void logout();
    bool authenticated() const;
    std::string current_user() const;

    // Settings
    bool export_user_settings(const std::filesystem::path& destination) const;
    bool import_user_settings(const std::filesystem::path& source);
    bool reset_workspace();

    // Consent (step 61)
    ConsentFlags consent() const;
    bool set_consent(ConsentFlags consent);
    bool set_local_only_mode(bool enabled);
    bool local_only_mode() const;

    // Session (steps 1-4)
    bool start_session(std::string title, std::string note = {});
    bool resume_session();
    bool pause_session(std::string reason = "Paused by user");
    bool fail_session(std::string reason = "Session failed");
    void reset_session();
    SessionState session_state() const;

    // Agents (steps 12-20)
    bool add_agent(std::string id, std::string role,
                   std::vector<std::string> expertise = {}, int capacity = 100);
    bool update_agent_skills(std::string agent_id, std::vector<AgentSkill> skills);
    bool set_agent_availability(std::string agent_id, std::string availability);
    std::vector<AgentProfile> agents(std::size_t limit = 200) const;
    std::vector<AgentProfile> filter_agents(std::string_view role,
                                            std::string_view expertise,
                                            bool busy_only,
                                            std::string_view task_id) const;
    std::size_t agent_count() const;
    std::map<std::string, std::size_t> role_counts() const;
    bool send_agent_message(std::string agent_id, std::string category,
                            std::string content);
    bool add_agent_message(std::string agent_id, std::string category,
                           std::string content);
    std::vector<AgentMessage> agent_messages(std::string_view agent_id) const;
    bool kill_all_agents(); // step 63 - kill switch

    // Tasks (steps 9,31-40)
    bool create_task(std::string title, std::string description,
                     std::string kind = "general", int priority = 5);
    bool validate_task(std::string task_id);
    bool tick();
    bool reopen_task(std::string task_id);
    bool resume_task(std::string task_id);
    bool cancel_task(std::string task_id, std::string reason = {});
    bool pause_task(std::string task_id);
    bool retry_task_step(std::string task_id);
    bool set_task_priority(std::string task_id, int priority);
    bool add_subtask(std::string parent_id, std::string title,
                     std::string kind, std::vector<std::string> depends_on = {});
    std::vector<TaskRecord> tasks() const;
    std::vector<TaskRecord> tasks_filtered(std::string_view status,
                                           std::string_view kind,
                                           std::string_view search) const;
    std::vector<TaskStep>   trace(std::size_t limit = 120) const;
    std::vector<TraceEvent> trace_events(std::size_t limit = 120) const;
    std::optional<TaskRecord> get_task(std::string_view id) const;

    // Computer surface (steps 21-30)
    bool attach_computer(std::string id, std::string label,
                         std::string os = {},
                         std::vector<std::string> surfaces = {},
                         bool active = true);
    bool set_active_computer(std::string_view id);
    bool open_window(std::string computer_id, std::string title,
                     std::string surface);
    bool close_window(std::string computer_id, std::string window_id);
    bool focus_window(std::string computer_id, std::string window_id);
    bool navigate_browser(std::string computer_id, std::string url,
                          std::string title, std::string excerpt = {});
    bool run_terminal_command(std::string computer_id, std::string command,
                              std::string output, int exit_code);
    bool undo_computer_action(std::string computer_id);
    std::vector<ComputerRecord> computers() const;
    std::vector<ComputerAction> computer_log(std::size_t limit = 200) const;
    std::vector<BrowserSnapshot> browser_history(std::size_t limit = 50) const;
    std::vector<TerminalOutput> terminal_history(std::size_t limit = 50) const;
    std::string active_computer_id() const;
    bool record_computer_action(std::string computer_id, std::string agent_id,
                                std::string surface, std::string verb,
                                std::string target, std::string detail);

    // LUO OS index
    bool import_luo_os(std::filesystem::path source_root);
    bool rebuild_luo_index();
    std::vector<LuoIndexEntry> luo_index_entries(std::size_t limit = 200) const;
    std::vector<LuoIndexEntry> search_luo_os(std::string_view query,
                                              std::size_t limit = 20) const;

    // Memory & knowledge (steps 41-50)
    bool add_memory(std::string kind, std::string content,
                    std::string source = {}, std::vector<std::string> tags = {});
    bool summarize_old_memories(std::size_t keep_recent = 50);
    std::vector<MemoryEntry> memory_entries(std::size_t limit = 100) const;
    std::vector<MemoryEntry> search_memory(std::string_view query,
                                            std::size_t limit = 20) const;
    bool add_knowledge(std::string title, std::string body,
                       std::vector<std::string> tags = {});
    std::vector<KnowledgeEntry> knowledge_entries(std::size_t limit = 100) const;
    std::vector<KnowledgeEntry> search_knowledge(std::string_view query,
                                                  std::size_t limit = 20) const;
    bool export_workspace_snapshot(const std::filesystem::path& dest) const;
    bool import_workspace_snapshot(const std::filesystem::path& src);

    // Files & projects (steps 51-60)
    bool upload_file(std::string name, std::string content,
                     std::string project_scope = {});
    bool update_file(std::string name, std::string content);
    bool rollback_file(std::string name, std::size_t version_index);
    FileDiff diff_file(std::string name, std::string new_content) const;
    std::vector<FileRecord> files() const;
    std::vector<FileRecord> search_files(std::string_view query) const;

    bool set_secret(std::string service, std::string value,
                    std::string scope = "local");
    std::vector<SecretRecord> secrets() const;

    bool add_skill(std::string name, std::string description,
                   std::vector<std::string> tags = {});
    std::vector<SkillRecord> skills() const;

    bool add_project(std::string id, std::string name, std::string command,
                     std::string cwd = {}, bool executable = true,
                     std::string template_kind = {});
    bool run_project(std::string id); // step 51 - project runner
    std::vector<ProjectRecord> projects() const;

    bool link_device(std::string id, std::string label,
                     std::vector<std::string> scopes = {},
                     bool approved = false);
    bool approve_device(std::string id);
    std::vector<DeviceLink> devices() const;

    // Safety & trust (steps 61-70)
    bool require_approval(std::string action, std::string detail);
    bool approve_action(std::string action);
    std::vector<std::string> pending_approvals() const;
    bool add_policy(std::string id, std::string action_pattern,
                    std::string decision, std::string reason = {});
    std::vector<PolicyRule> policies() const;
    bool check_policy(std::string_view action) const;

    // Audit & privacy (steps 64,66,69)
    std::vector<TraceEvent> audit_log(std::size_t limit = 200) const;
    bool add_trace(std::string category, std::string actor,
                   std::string action, std::string detail);
    std::string redact_secrets(std::string text) const; // step 65

    // RBAC (step 67)
    bool set_user_role(std::string username, std::string role);
    std::string user_role(std::string_view username) const;
    bool user_can(std::string_view username, std::string_view action) const;

    // Background tick engine (P2)
    void start_tick_engine(int interval_ms = 2000);
    void stop_tick_engine();
    bool tick_engine_running() const;

    // Summary & state export
    Summary summary() const;
    std::string export_state() const;
    std::filesystem::path data_root() const;
    void rebuild_search_index();

    // Search across everything (step 44,60,73)
    struct SearchResult {
        std::string kind;   // "task"|"file"|"memory"|"knowledge"|"agent"|"log"
        std::string id;
        std::string title;
        std::string excerpt;
        double      score = 0.0;
    };
    std::vector<SearchResult> search_all(std::string_view query,
                                          std::size_t limit = 30) const;

private:
    void set_session_stage(SessionStage stage, std::string detail);
    void record_approval(std::string action, std::string detail, bool granted);
    bool has_approval(std::string action) const;
    friend struct StateIO;
    friend struct StateStore;

    Workspace&       workspace();
    const Workspace& workspace() const;
    UserRecord&       active_user_record();
    const UserRecord& active_user_record() const;

    void ensure_workspace_seeded();
    void seed_swarm(Workspace& ws);
    bool seed_agents_from_config(Workspace& ws);
    void seed_default_swarm(Workspace& ws);
    std::vector<std::string> roles_for_kind(std::string_view kind) const;
    std::vector<std::string> assign_agents(Workspace& ws,
                                            const std::vector<std::string>& roles,
                                            const std::string& task_id);
    AgentProfile* find_best_agent(Workspace& ws, std::string_view role);
    void check_agent_health(Workspace& ws);
    void release_agents(Workspace& ws, const TaskRecord& task);
    void record_trace(std::string category, std::string actor,
                      std::string action, std::string detail);
    void record_audit(std::string actor, std::string action, std::string detail);
    void remember_step(TaskRecord& task, TaskStep step);
    void touch();
    std::filesystem::path state_file() const;
    static Timestamp now();

    std::filesystem::path data_root_;
    std::filesystem::path luo_os_root_;
    LuoIndex              luo_os_index_;
    mutable SearchIndex   search_index_;
    bool                  search_index_dirty_ = true;
    // Tick engine
    std::atomic<bool>     tick_running_{false};
    std::thread           tick_thread_;
    mutable std::mutex    workspace_mutex_;
    SessionState          session_;
    std::map<std::string, UserRecord>  users_;
    std::map<std::string, Workspace>   workspaces_;
    std::string           active_user_;
    bool                  auto_save_ = true;
};

} // namespace luo_gate
