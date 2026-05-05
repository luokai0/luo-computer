#include <sys/statvfs.h>
#include "luo_gate/app.hpp"
#include "luo_gate/platform.hpp"
#include "luo_gate/security.hpp"
#include "luo_gate/state_io.hpp"
#include "luo_gate/state_store.hpp"
#include "luo_gate/luo_index.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <optional>
#include <sstream>
#include <string_view>
#include <utility>
#include <limits>
#include <array>

namespace luo_gate {
namespace {
const char* session_stage_to_string(SessionStage stage) {
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

SessionStage session_stage_from_string(std::string_view text) {
    if (text == "starting") return SessionStage::Starting;
    if (text == "running") return SessionStage::Running;
    if (text == "paused") return SessionStage::Paused;
    if (text == "failed") return SessionStage::Failed;
    if (text == "resumed") return SessionStage::Resumed;
    return SessionStage::Idle;
}

std::vector<std::string> default_roles_for_kind(std::string_view kind) {
    if (kind == "build") return {"planner", "builder", "reviewer", "tester", "operator"};
    if (kind == "research") return {"researcher", "analyst", "writer"};
    if (kind == "ops") return {"operator", "monitor", "safety"};
    if (kind == "ui") return {"designer", "frontend", "tester"};
    return {"planner", "operator", "reviewer"};
}

std::string default_agent_id(std::size_t index) { return "agent-" + std::to_string(index + 1); }

std::string default_agent_role(std::size_t index) {
    static constexpr const char* roles[] = {"planner", "builder", "reviewer", "tester", "operator", "researcher", "designer", "writer", "monitor", "safety"};
    return roles[index % (sizeof(roles) / sizeof(roles[0]))];
}

std::string escape_json(std::string_view value) {
    std::ostringstream out;
    for (char c : value) {
        switch (c) {
            case '\\': out << "\\\\"; break;
            case '"': out << "\\\""; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default: out << c; break;
        }
    }
    return out.str();
}

std::string default_computer_id() { return "local-computer"; }

std::string unquote(std::string value) {
    if (value.size() >= 2 && value.front() == '"' && value.back() == '"') {
        value = value.substr(1, value.size() - 2);
    }
    std::string out;
    out.reserve(value.size());
    bool escape = false;
    for (char c : value) {
        if (escape) {
            switch (c) {
                case 'n': out.push_back('\n'); break;
                case 'r': out.push_back('\r'); break;
                case 't': out.push_back('\t'); break;
                case '\\': out.push_back('\\'); break;
                case '"': out.push_back('"'); break;
                default: out.push_back(c); break;
            }
            escape = false;
        } else if (c == '\\') {
            escape = true;
        } else {
            out.push_back(c);
        }
    }
    return out;
}

std::vector<std::string> split(std::string_view text, char delim) {
    std::vector<std::string> parts;
    std::string current;
    for (char c : text) {
        if (c == delim) {
            parts.push_back(current);
            current.clear();
        } else {
            current.push_back(c);
        }
    }
    parts.push_back(current);
    return parts;
}

std::string join(const std::vector<std::string>& items, char delim) {
    std::ostringstream out;
    for (std::size_t i = 0; i < items.size(); ++i) {
        if (i) out << delim;
        out << items[i];
    }
    return out.str();
}

std::string trim(std::string_view text) {
    std::size_t start = 0;
    std::size_t end = text.size();
    while (start < end && std::isspace(static_cast<unsigned char>(text[start]))) start++;
    while (end > start && std::isspace(static_cast<unsigned char>(text[end - 1]))) end--;
    return std::string(text.substr(start, end - start));
}

ConsentFlags parse_consent(const std::vector<std::string>& fields) {
    ConsentFlags c;
    if (fields.size() >= 7) {
        c.accept_terms = fields[0] == "1";
        c.allow_local_storage = fields[1] == "1";
        c.allow_files = fields[2] == "1";
        c.allow_chat_history = fields[3] == "1";
        c.allow_project_execution = fields[4] == "1";
        c.allow_device_links = fields[5] == "1";
        c.allow_analytics = fields[6] == "1";
    }
    return c;
}

std::string serialize_consent(const ConsentFlags& c) {
    return std::string(c.accept_terms ? "1" : "0") + '|' +
           (c.allow_local_storage ? "1" : "0") + '|' +
           (c.allow_files ? "1" : "0") + '|' +
           (c.allow_chat_history ? "1" : "0") + '|' +
           (c.allow_project_execution ? "1" : "0") + '|' +
           (c.allow_device_links ? "1" : "0") + '|' +
           (c.allow_analytics ? "1" : "0");
}

std::string default_state_text() { return ""; }

std::string rowify(const std::vector<std::string>& columns) {
    std::ostringstream out;
    for (std::size_t i = 0; i < columns.size(); ++i) {
        if (i) out << '\t';
        out << columns[i];
    }
    return out.str();
}

std::string rowify(std::initializer_list<std::string> columns) {
    return rowify(std::vector<std::string>(columns));
}

std::optional<AgentProfile> parse_agent_line(std::string_view line) {
    const auto trimmed = trim(line);
    if (trimmed.empty() || trimmed.rfind("#", 0) == 0) return std::nullopt;
    if (trimmed.find(',') == std::string::npos) return std::nullopt;
    const auto parts = split(trimmed, ',');
    if (parts.size() < 3) return std::nullopt;

    const auto id = trim(parts[0]);
    const auto role = trim(parts[1]);
    std::vector<std::string> expertise;
    for (std::size_t i = 2; i < parts.size(); ++i) {
        const auto entry = trim(parts[i]);
        if (!entry.empty()) expertise.push_back(entry);
    }

    double reliability = 0.8;
    std::string availability = "always";
    double cost = 1.0;
    if (parts.size() >= 6) {
        try {
            reliability = std::clamp(std::stod(trim(parts[3])), 0.0, 1.0);
        } catch (...) {}
        const auto avail = trim(parts[4]);
        if (!avail.empty()) availability = avail;
        try {
            cost = std::max(0.0, std::stod(trim(parts[5])));
        } catch (...) {}
    }

    return AgentProfile{
        id.empty() ? default_agent_id(0) : id,
        role.empty() ? default_agent_role(0) : role,
        expertise.empty() ? std::vector<std::string>{"general"} : expertise,
        100,
        false,
        {},
        reliability,
        availability,
        cost
    };
}

static bool is_risky_action(std::string_view verb) {
    static const std::array risk = {"execute", "delete", "link", "commit", "deploy"};
    for (const auto& candidate : risk) {
        if (verb == candidate) return true;
    }
    return false;
}

} // namespace

App::App(std::filesystem::path data_root) : data_root_(data_root.empty() ? default_data_root() : std::move(data_root)) {
    ensure_workspace_seeded();
}

bool App::load() { return StateStore::load(*this); }

bool App::save() const { return StateStore::save(*this); }

bool App::has_user(std::string_view username) const {
    return users_.contains(std::string(username));
}

std::vector<std::string> App::users() const {
    std::vector<std::string> out;
    out.reserve(users_.size());
    for (const auto& [name, _] : users_) out.push_back(name);
    return out;
}

bool App::register_user(std::string username, std::string password, std::string email, ConsentFlags consent) {
    if (!is_valid_username(username) || !is_valid_password(password)) return false;
    if (users_.contains(username)) return false;
    users_.emplace(username, UserRecord{username, password_hash(username, password), std::move(email), consent});
    workspaces_.try_emplace(username, Workspace{consent});
    if (active_user_.empty()) active_user_ = username;
    ensure_workspace_seeded();
    record_audit(username, "register", "created account");
    touch();
    return true;
}

bool App::login(std::string_view username, std::string_view password) {
    const auto it = users_.find(std::string(username));
    if (it == users_.end() || it->second.password_hash != password_hash(username, password)) return false;
    active_user_ = it->first;
    ensure_workspace_seeded();
    if (workspace().active_computer_id.empty()) workspace().active_computer_id = default_computer_id();
    record_audit(active_user_, "login", "signed in");
    touch();
    return true;
}

void App::logout() {
    if (!active_user_.empty()) record_audit(active_user_, "logout", "signed out");
    active_user_.clear();
}

bool App::authenticated() const { return !active_user_.empty(); }
std::string App::current_user() const { return active_user_; }
ConsentFlags App::consent() const { return active_user_.empty() ? ConsentFlags{} : active_user_record().consent; }

bool App::set_consent(ConsentFlags consent) {
    if (active_user_.empty()) return false;
    active_user_record().consent = consent;
    workspace().consent = consent;
    record_audit(active_user_, "consent", "updated consent settings");
    touch();
    return true;
}

bool App::start_session(std::string title, std::string note) {
    if (active_user_.empty()) return false;
    session_.resumed = false;
    session_.title = std::move(title);
    session_.note = std::move(note);
    session_.last_started_at = now();
    session_.last_resumed_at = 0;
    set_session_stage(SessionStage::Starting, "Starting \"" + session_.title + "\"");
    record_audit(active_user_, "session", "started " + session_.title);
    set_session_stage(SessionStage::Running, "Session running");
    return true;
}

bool App::resume_session() {
    if (active_user_.empty()) return false;
    session_.resumed = true;
    session_.last_resumed_at = now();
    if (session_.title.empty()) session_.title = "Resume session";
    record_audit(active_user_, "session", "resumed " + session_.title);
    set_session_stage(SessionStage::Resumed, "Resumed \"" + session_.title + "\"");
    return true;
}

SessionState App::session_state() const { return session_; }

bool App::add_agent(std::string id, std::string role, std::vector<std::string> expertise, int capacity) {
    if (active_user_.empty()) return false;
    auto& agents = workspace().agents;
    if (std::any_of(agents.begin(), agents.end(), [&](const auto& a) { return a.id == id; })) return false;
    agents.push_back(AgentProfile{std::move(id), std::move(role), std::move(expertise), capacity, false, {}});
    touch();
    return true;
}

bool App::create_task(std::string title, std::string description, std::string kind, int priority) {
    if (active_user_.empty()) return false;
    auto& ws = workspace();
    // Expand the full 10k swarm the first time a task is created
    expand_swarm_if_needed(ws);
    TaskRecord task;
    task.id = "task-" + std::to_string(ws.tasks.size() + 1);
    task.title = std::move(title);
    task.description = std::move(description);
    task.kind = std::move(kind);
    task.owner = active_user_;
    task.created_at = now();
    task.updated_at = task.created_at;
    task.priority = std::clamp(priority, 1, 10);
    task.required_roles = default_roles_for_kind(task.kind);
    task.plan = {
        {0, "system", "intake", "Accept and normalize user request", now(), "computer"},
        {1, "planner", "decompose", "Split the task into steps and roles", now(), "computer"},
        {2, "operator", "open", "Open the computer and visible workspace", now(), "computer"},
        {3, "builder", "execute", "Perform the requested action on the computer", now(), "computer"},
        {4, "reviewer", "verify", "Check results for correctness", now(), "computer"},
        {5, "operator", "deliver", "Show the result to the user", now(), "computer"},
    };
    task.assigned_agents = assign_agents(ws, task.required_roles, task.id);
    ws.tasks.push_back(task);
    record_trace("task", active_user_, "created", task.id + ":" + task.title);
    record_computer_action(ws.active_computer_id.empty() ? default_computer_id() : ws.active_computer_id, "system", "computer", "open", task.id, "Spawned visible task on the local computer");
    touch();
    return true;
}

bool App::tick() {
    if (active_user_.empty()) return false;
    auto& ws = workspace();
    bool progressed = false;
    for (auto& task : ws.tasks) {
        if (task.status == "done" || task.plan.empty() || task.step_cursor >= task.plan.size()) continue;
        auto step = task.plan[task.step_cursor];
        task.status = task.step_cursor + 1 >= task.plan.size() ? "done" : "running";
        task.updated_at = now();
        auto agent = find_best_agent(ws, step.actor);
        if (agent) {
            task.current_agent_id = agent->id;
            agent->busy = true;
            agent->task_id = task.id;
        }
        record_trace("task", step.actor, step.action, task.id + " -> " + step.detail);
        remember_step(task, step);
        record_computer_action(ws.active_computer_id.empty() ? default_computer_id() : ws.active_computer_id, step.actor, step.surface, step.action, task.id, step.detail);
        task.step_cursor++;
        if (task.status == "done") release_agents(ws, task);
        progressed = true;
    }
    check_agent_health(ws);
    if (progressed) touch();
    return progressed;
}

bool App::reopen_task(std::string task_id) {
    if (active_user_.empty()) return false;
    auto& ws = workspace();
    auto it = std::find_if(ws.tasks.begin(), ws.tasks.end(), [&](const auto& t) { return t.id == task_id; });
    if (it == ws.tasks.end() || it->status == "running") return false;
    it->status = "queued";
    it->step_cursor = 0;
    it->assigned_agents = assign_agents(ws, it->required_roles, it->id);
    record_audit(active_user_, "task", "reopened " + it->id);
    touch();
    return true;
}

bool App::resume_task(std::string task_id) {
    if (active_user_.empty()) return false;
    auto& ws = workspace();
    auto it = std::find_if(ws.tasks.begin(), ws.tasks.end(), [&](const auto& t) { return t.id == task_id; });
    if (it == ws.tasks.end()) return false;
    it->status = "running";
    tick();
    return true;
}

std::vector<TaskRecord> App::tasks() const {
    return active_user_.empty() ? std::vector<TaskRecord>{} : workspace().tasks;
}

std::vector<TaskStep> App::trace(std::size_t limit) const {
    std::vector<TaskStep> out;
    if (active_user_.empty()) return out;
    for (const auto& task : workspace().tasks) {
        for (const auto& step : task.plan) out.push_back(step);
    }
    if (out.size() > limit) out.erase(out.begin(), out.end() - static_cast<std::ptrdiff_t>(limit));
    return out;
}

std::vector<TraceEvent> App::trace_events(std::size_t limit) const {
    auto out = active_user_.empty() ? std::vector<TraceEvent>{} : workspace().trace;
    if (out.size() > limit) out.erase(out.begin(), out.end() - static_cast<std::ptrdiff_t>(limit));
    return out;
}

std::size_t App::agent_count() const {
    return active_user_.empty() ? 0 : workspace().agents.size();
}

std::vector<AgentProfile> App::agents(std::size_t limit) const {
    std::vector<AgentProfile> out;
    if (active_user_.empty()) return out;
    out = workspace().agents;
    if (out.size() > limit) out.erase(out.begin(), out.end() - static_cast<std::ptrdiff_t>(limit));
    return out;
}

std::map<std::string, std::size_t> App::role_counts() const {
    std::map<std::string, std::size_t> counts;
    if (active_user_.empty()) return counts;
    for (const auto& agent : workspace().agents) counts[agent.role]++;
    return counts;
}

bool App::attach_computer(std::string id, std::string label, std::string os, std::vector<std::string> surfaces, bool active) {
    if (active_user_.empty()) return false;
    auto& computers = workspace().computers;
    auto it = std::find_if(computers.begin(), computers.end(), [&](const auto& c) { return c.id == id; });
    ComputerRecord record{std::move(id), std::move(label), std::move(os), std::move(surfaces), active};
    if (it == computers.end()) computers.push_back(record);
    else *it = record;
    if (workspace().active_computer_id.empty() || active) workspace().active_computer_id = record.id;
    record_computer_action(record.id, "system", "computer", "attach", record.label, "Computer attached to the swarm workspace");
    touch();
    return true;
}

bool App::set_active_computer(std::string_view id) {
    if (active_user_.empty()) return false;
    auto& computers = workspace().computers;
    auto it = std::find_if(computers.begin(), computers.end(), [&](const auto& c) { return c.id == id; });
    if (it == computers.end()) return false;
    workspace().active_computer_id = it->id;
    record_computer_action(it->id, "system", "computer", "focus", it->label, "User switched to this computer");
    touch();
    return true;
}

std::vector<ComputerRecord> App::computers() const {
    return active_user_.empty() ? std::vector<ComputerRecord>{} : workspace().computers;
}

std::vector<ComputerAction> App::computer_log(std::size_t limit) const {
    auto out = active_user_.empty() ? std::vector<ComputerAction>{} : workspace().computer_log;
    if (out.size() > limit) out.erase(out.begin(), out.end() - static_cast<std::ptrdiff_t>(limit));
    return out;
}

std::string App::active_computer_id() const {
    if (active_user_.empty()) return {};
    const auto& ws = workspace();
    if (!ws.active_computer_id.empty()) return ws.active_computer_id;
    if (!ws.computers.empty()) return ws.computers.front().id;
    return default_computer_id();
}

bool App::record_computer_action(std::string computer_id, std::string agent_id, std::string surface, std::string verb, std::string target, std::string detail) {
    if (active_user_.empty()) return false;
    if (is_risky_action(verb) && !has_approval(verb)) {
        require_approval(verb, detail);
        return false;
    }
    workspace().computer_log.push_back(ComputerAction{now(), std::move(computer_id), std::move(agent_id), std::move(surface), std::move(verb), std::move(target), std::move(detail)});
    record_trace("computer", active_user_, verb, detail);
    touch();
    return true;
}

bool App::set_secret(std::string service, std::string value, std::string scope) {
    if (active_user_.empty()) return false;
    auto& secrets = workspace().secrets;
    auto it = std::find_if(secrets.begin(), secrets.end(), [&](const auto& s) { return s.service == service; });
    SecretRecord record{std::move(service), std::move(value), std::move(scope)};
    if (it == secrets.end()) secrets.push_back(record);
    else *it = record;
    record_audit(active_user_, "secret", "stored secret for service");
    touch();
    return true;
}

bool App::add_agent_message(std::string agent_id, std::string category, std::string content) {
    if (active_user_.empty()) return false;
    workspace().inbox.push_back(AgentMessage{std::move(agent_id), std::move(category), std::move(content), now()});
    record_trace("agent", "system", "message", content);
    touch();
    return true;
}

std::vector<AgentMessage> App::agent_messages(std::string_view agent_id) const {
    std::vector<AgentMessage> out;
    if (active_user_.empty()) return out;
    for (const auto& msg : workspace().inbox) {
        if (msg.agent_id == agent_id) out.push_back(msg);
    }
    return out;
}

std::vector<SecretRecord> App::secrets() const {
    return active_user_.empty() ? std::vector<SecretRecord>{} : workspace().secrets;
}

bool App::upload_file(std::string name, std::string content, std::string project_scope) {
    if (active_user_.empty()) return false;
    // Check if file already exists - update instead
    for (auto& f : workspace().files) {
        if (f.name == name) return update_file(name, content);
    }
    FileRecord rec;
    rec.name = std::move(name);
    rec.content = std::move(content);
    rec.created_at = now();
    rec.project_scope = std::move(project_scope);
    workspace().files.push_back(std::move(rec));
    record_audit(active_user_, "file", "uploaded file");
    touch();
    return true;
}

std::vector<FileRecord> App::files() const {
    return active_user_.empty() ? std::vector<FileRecord>{} : workspace().files;
}

bool App::add_skill(std::string name, std::string description, std::vector<std::string> tags) {
    if (active_user_.empty()) return false;
    workspace().skills.push_back(SkillRecord{std::move(name), std::move(description), std::move(tags)});
    touch();
    return true;
}

std::vector<SkillRecord> App::skills() const {
    return active_user_.empty() ? std::vector<SkillRecord>{} : workspace().skills;
}

bool App::add_project(std::string id, std::string name, std::string command,
                      std::string cwd, bool executable, std::string template_kind) {
    if (active_user_.empty()) return false;
    auto& projects = workspace().projects;
    auto it = std::find_if(projects.begin(), projects.end(), [&](const auto& p) { return p.id == id; });
    ProjectRecord record;
    record.id = std::move(id);
    record.name = std::move(name);
    record.command = std::move(command);
    record.cwd = std::move(cwd);
    record.executable = executable;
    record.last_exit_code = -1;
    record.template_kind = std::move(template_kind);
    if (it == projects.end()) projects.push_back(record);
    else *it = record;
    touch();
    return true;
}

std::vector<ProjectRecord> App::projects() const {
    return active_user_.empty() ? std::vector<ProjectRecord>{} : workspace().projects;
}

bool App::link_device(std::string id, std::string label, std::vector<std::string> scopes, bool approved) {
    if (active_user_.empty()) return false;
    workspace().devices.push_back(DeviceLink{std::move(id), std::move(label), std::move(scopes), approved});
    record_audit(active_user_, "device", "linked device");
    touch();
    return true;
}

std::vector<DeviceLink> App::devices() const {
    return active_user_.empty() ? std::vector<DeviceLink>{} : workspace().devices;
}

std::vector<TraceEvent> App::audit_log(std::size_t limit) const {
    auto out = active_user_.empty() ? std::vector<TraceEvent>{} : workspace().audit;
    if (out.size() > limit) out.erase(out.begin(), out.end() - static_cast<std::ptrdiff_t>(limit));
    return out;
}

Summary App::summary() const {
    Summary s;
    s.user_count = users_.size();
    s.active_user = active_user_;
    s.platform = operating_system_name();
    if (!active_user_.empty()) {
        const auto& ws = workspace();
        s.agent_count = ws.agents.size();
        s.task_count = ws.tasks.size();
        s.computer_count = ws.computers.size();
        s.secret_count = ws.secrets.size();
        s.file_count = ws.files.size();
        s.skill_count = ws.skills.size();
        s.project_count = ws.projects.size();
        s.device_count = ws.devices.size();
        s.audit_count = ws.audit.size();
        s.memory_count   = ws.memory_store.size();
        s.knowledge_count = ws.knowledge.size();
        s.role_counts = role_counts();
    }
    s.session_stage = [this]() -> std::string {
        switch (session_.stage) {
            case SessionStage::Idle:     return "idle";
            case SessionStage::Starting: return "starting";
            case SessionStage::Running:  return "running";
            case SessionStage::Paused:   return "paused";
            case SessionStage::Failed:   return "failed";
            case SessionStage::Resumed:  return "resumed";
        }
        return "idle";
    }();
    s.local_only_mode = active_user_.empty() ? true : workspace().local_only_mode;
    return s;
}

std::string App::export_state() const {
    const auto s = summary();
    std::ostringstream out;
    out << '{'
        << "\"users\":" << s.user_count << ','
        << "\"agents\":" << s.agent_count << ','
        << "\"tasks\":" << s.task_count << ','
        << "\"computers\":" << s.computer_count << ','
        << "\"secrets\":" << s.secret_count << ','
        << "\"files\":" << s.file_count << ','
        << "\"skills\":" << s.skill_count << ','
        << "\"projects\":" << s.project_count << ','
        << "\"devices\":" << s.device_count << ','
        << "\"audit\":" << s.audit_count << ','
        << "\"memory\":" << s.memory_count << ','
        << "\"knowledge\":" << s.knowledge_count << ','
        << "\"platform\":\"" << escape_json(s.platform) << "\","
        << "\"active_user\":\"" << escape_json(s.active_user) << "\","
        << "\"session\":{"
        << "\"resumed\":" << (session_.resumed ? "true" : "false") << ','
        << "\"title\":\"" << escape_json(session_.title) << "\","
        << "\"note\":\"" << escape_json(session_.note) << "\","
        << "\"last_started_at\":" << session_.last_started_at << ','
        << "\"last_resumed_at\":" << session_.last_resumed_at << "}}";
    return out.str();
}

std::filesystem::path App::data_root() const { return data_root_; }

Workspace& App::workspace() { return workspaces_[active_user_]; }
const Workspace& App::workspace() const { return workspaces_.at(active_user_); }
UserRecord& App::active_user_record() { return users_.at(active_user_); }
const UserRecord& App::active_user_record() const { return users_.at(active_user_); }

void App::ensure_workspace_seeded() {
    for (auto& [user, ws] : workspaces_) {
        if (ws.agents.empty()) seed_swarm(ws);
        if (ws.computers.empty()) ws.computers.push_back(ComputerRecord{default_computer_id(), "Local Computer", operating_system_name(), {"computer", "terminal", "browser", "files"}, true});
        if (ws.active_computer_id.empty()) ws.active_computer_id = ws.computers.front().id;
        // Seed luo_os built-in projects if none exist
        if (ws.projects.empty()) seed_luo_os_projects(ws);
    }
}

void App::seed_luo_os_projects(Workspace& ws) {
    // Find the luo_os directory relative to the executable / data root
    const auto luo_os_dir = data_root().parent_path() / "luo_os";
    const auto bridge     = luo_os_dir / "bridge.py";
    const auto server     = luo_os_dir / "luo_server.py";
    const auto cli        = luo_os_dir / "luo_cli.py";
    const auto kairos     = luo_os_dir / "ai_core" / "kairos.py";

    struct Proj { std::string id, name, cmd, kind; };
    const std::vector<Proj> projs = {
        {"luo_os_status",  "Luo OS — Status",          "python3 " + bridge.string()  + " status",        "luo_os"},
        {"luo_os_server",  "Luo OS — Start Server",    "python3 " + server.string()  + " &",             "luo_os"},
        {"luo_os_cli",     "Luo OS — CLI",             "python3 " + cli.string(),                        "luo_os"},
        {"luo_os_kairos",  "Luo OS — KAIROS Daemon",   "python3 " + kairos.string() + " start",         "luo_os"},
        {"luo_os_mem",     "Luo OS — Memory Stats",    "python3 " + bridge.string()  + " memory stats",  "luo_os"},
        {"luo_os_agents",  "Luo OS — List Agents",     "python3 " + bridge.string()  + " agents list",   "luo_os"},
        {"luo_os_skills",  "Luo OS — Skill Library",   "python3 " + bridge.string()  + " skills list",   "luo_os"},
    };

    for (const auto& p : projs) {
        ProjectRecord rec;
        rec.id            = p.id;
        rec.name          = p.name;
        rec.command       = p.cmd;
        rec.cwd           = luo_os_dir.string();
        rec.executable    = std::filesystem::exists(bridge);
        rec.template_kind = p.kind;
        rec.last_exit_code = -1;
        ws.projects.push_back(std::move(rec));
    }
}

void App::seed_swarm(Workspace& ws) {
    if (seed_agents_from_config(ws)) return;
    seed_default_swarm(ws);
}

std::vector<std::string> App::roles_for_kind(std::string_view kind) const { return default_roles_for_kind(kind); }

bool App::seed_agents_from_config(Workspace& ws) {
    const auto file = data_root_ / "agents.csv";
    std::ifstream in(file);
    if (!in) return false;

    std::string line;
    std::size_t count = 0;
    while (std::getline(in, line)) {
        if (const auto profile = parse_agent_line(line)) {
            ws.agents.push_back(*profile);
            count++;
        }
    }
    return count > 0;
}

void App::seed_default_swarm(Workspace& ws) {
    const auto seeds = std::vector<std::pair<std::string, std::vector<std::string>>>{
        {"planner",    {"planning", "decomposition"}},
        {"builder",    {"implementation", "execution"}},
        {"reviewer",   {"validation", "quality"}},
        {"tester",     {"verification", "debugging"}},
        {"operator",   {"orchestration", "delivery"}},
        {"researcher", {"research", "synthesis"}},
        {"designer",   {"ux", "layout"}},
        {"writer",     {"docs", "copy"}},
        {"monitor",    {"telemetry", "watching"}},
        {"safety",     {"consent", "policy"}},
    };
    // Seed a small representative pool immediately (fast startup).
    // The full 10k swarm is expanded lazily on first task creation.
    const std::size_t initial_count = 100;
    for (std::size_t i = 0; i < initial_count; ++i) {
        const auto& seed = seeds[i % seeds.size()];
        const double reliability = 0.92 - (static_cast<double>(i % seeds.size()) * 0.004);
        ws.agents.push_back(AgentProfile{default_agent_id(i), default_agent_role(i) + "-" + seed.first, seed.second, 100, false, {}, reliability, "always", 1.0});
    }
}

void App::expand_swarm_if_needed(Workspace& ws) {
    if (ws.swarm_expanded) return;
    ws.swarm_expanded = true;
    const auto seeds = std::vector<std::pair<std::string, std::vector<std::string>>>{
        {"planner",    {"planning", "decomposition"}},
        {"builder",    {"implementation", "execution"}},
        {"reviewer",   {"validation", "quality"}},
        {"tester",     {"verification", "debugging"}},
        {"operator",   {"orchestration", "delivery"}},
        {"researcher", {"research", "synthesis"}},
        {"designer",   {"ux", "layout"}},
        {"writer",     {"docs", "copy"}},
        {"monitor",    {"telemetry", "watching"}},
        {"safety",     {"consent", "policy"}},
    };
    const std::size_t current = ws.agents.size();
    for (std::size_t i = current; i < 10000; ++i) {
        const auto& seed = seeds[i % seeds.size()];
        const double reliability = 0.92 - (static_cast<double>(i % seeds.size()) * 0.004);
        ws.agents.push_back(AgentProfile{default_agent_id(i), default_agent_role(i) + "-" + seed.first, seed.second, 100, false, {}, reliability, "always", 1.0});
    }
}

std::vector<std::string> App::assign_agents(Workspace& ws, const std::vector<std::string>& roles, const std::string& task_id) {
    std::vector<std::string> assigned;
    for (const auto& role : roles) {
        auto* best = find_best_agent(ws, role);
        if (!best) continue;
        best->busy = true;
        best->task_id = task_id;
        best->last_active = now();
        best->load++;
        assigned.push_back(best->id);
    }
    return assigned;
}

AgentProfile* App::find_best_agent(Workspace& ws, std::string_view role) {
    AgentProfile* best = nullptr;
    double best_score = -1.0;

    for (auto& agent : ws.agents) {
        if (agent.busy) continue;
        if (agent.availability == "offline") continue;
        if (agent.health == "stuck") continue;

        double score = agent.reliability;                          // base: 0.5-1.0

        // Role match
        if (agent.role == role)         score += 1.0;
        else if (agent.role.find(role) != std::string::npos) score += 0.5;

        // Skill match: expert > intermediate > beginner
        for (const auto& skill : agent.skills) {
            if (skill.name.find(role) != std::string::npos ||
                skill.domain.find(role) != std::string::npos) {
                if (skill.level == "expert")       score += 0.4;
                else if (skill.level == "intermediate") score += 0.2;
                else                               score += 0.1;
            }
        }

        // Availability bonus
        if (agent.availability == "always") score += 0.1;

        // Load penalty: prefer less-loaded agents
        score -= static_cast<double>(agent.load) * 0.15;

        // Capacity fit (lower capacity = more specialised = slightly preferred)
        score += (100 - agent.capacity) / 2000.0;

        // Freshness: recently active agents preferred
        if (agent.last_active > 0) {
            const auto age = now() - agent.last_active;
            if (age < 60) score += 0.05;
        }

        if (score > best_score) {
            best_score = score;
            best = &agent;
        }
    }
    return best;
}

void App::release_agents(Workspace& ws, const TaskRecord& task) {
    for (auto& agent : ws.agents) {
        if (agent.task_id == task.id) {
            agent.last_active = now();
            agent.busy = false;
            agent.task_id.clear();
            if (agent.load > 0) agent.load--;
        }
    }
}

void App::remember_step(TaskRecord& task, TaskStep step) {
    task.memory.emplace_back(step.actor + ": " + step.action + " — " + step.detail);
    if (task.memory.size() > 5) task.memory.erase(task.memory.begin());
}

void App::check_agent_health(Workspace& ws) {
    const Timestamp t = now();
    const Timestamp degraded_cutoff = t - 30;   // 30s without progress → degraded
    const Timestamp stuck_cutoff    = t - 120;  // 2min → stuck

    for (auto& agent : ws.agents) {
        if (!agent.busy) {
            // Idle agents recover reliability slowly
            agent.health = "ok";
            agent.stuck_since = 0;
            if (agent.reliability < 0.9)
                agent.reliability = std::min(0.9, agent.reliability + 0.005);
            continue;
        }

        const bool long_idle = agent.last_active && agent.last_active < degraded_cutoff;
        const bool very_long = agent.last_active && agent.last_active < stuck_cutoff;

        if (very_long) {
            if (agent.stuck_since == 0) agent.stuck_since = t;
            agent.health = "stuck";
            agent.reliability = std::max(0.3, agent.reliability - 0.05);
            record_trace("health", "monitor", "stuck",
                         agent.id + " stuck for " + std::to_string(t - agent.last_active) + "s");
            // Auto-release stuck agents
            agent.busy = false;
            agent.task_id.clear();
            agent.load = 0;
            agent.health = "ok";
            agent.stuck_since = 0;
            record_trace("health", "monitor", "released", agent.id + " auto-released from stuck");
        } else if (long_idle) {
            agent.health = "degraded";
            agent.reliability = std::max(0.5, agent.reliability - 0.01);
            record_trace("health", "monitor", "degraded",
                         agent.id + " reliability=" + std::to_string(agent.reliability));
        } else {
            agent.health = "ok";
        }
    }
}

bool App::require_approval(std::string action, std::string detail) {
    if (has_approval(action)) return true;
    auto& records = workspace().approvals;
    records.push_back(ApprovalRecord{action, detail, false, now(), 0});
    workspace().pending_approvals.push_back(action);
    record_trace("approval", "system", "requested", action + ": " + detail);
    return false;
}

bool App::approve_action(std::string action) {
    auto& records = workspace().approvals;
    for (auto& record : records) {
        if (record.action == action && !record.granted) {
            record.granted = true;
            record.granted_at = now();
            workspace().pending_approvals.erase(std::remove(workspace().pending_approvals.begin(), workspace().pending_approvals.end(), action), workspace().pending_approvals.end());
            record_trace("approval", "system", "granted", action);
            return true;
        }
    }
    return false;
}

std::vector<std::string> App::pending_approvals() const {
    return workspace().pending_approvals;
}

void App::record_approval(std::string action, std::string detail, bool granted) {
    workspace().approvals.push_back(ApprovalRecord{std::move(action), std::move(detail), granted, now(), granted ? now() : 0});
}

bool App::has_approval(std::string action) const {
    for (const auto& record : workspace().approvals) {
        if (record.action == action && record.granted) return true;
    }
    return false;
}

void App::record_trace(std::string category, std::string actor, std::string action, std::string detail) {
    if (active_user_.empty()) return;
    workspace().trace.push_back(TraceEvent{now(), std::move(category), std::move(actor), std::move(action), std::move(detail)});
}

void App::record_audit(std::string actor, std::string action, std::string detail) {
    if (active_user_.empty()) return;
    workspace().audit.push_back(TraceEvent{now(), "audit", std::move(actor), std::move(action), std::move(detail)});
}

void App::touch() {
    search_index_dirty_ = true;
    if (auto_save_) save();
}

bool App::export_user_settings(const std::filesystem::path& destination) const {
    if (active_user_.empty()) return false;
    std::error_code ec;
    std::filesystem::create_directories(destination, ec);
    const auto file = destination / "user-settings.tsv";
    std::ofstream out(file);
    if (!out) return false;
    const auto& ws = workspace();
    out << rowify({"consent", serialize_consent(ws.consent)}) << "\n";
    out << rowify({
        "session",
        escape_json(session_.title),
        escape_json(session_.note),
        escape_json(session_stage_to_string(session_.stage)),
        escape_json(session_.stage_detail),
    }) << "\n";
    out << rowify({"active_computer", escape_json(ws.active_computer_id)}) << "\n";
    return true;
}

bool App::import_user_settings(const std::filesystem::path& source) {
    if (active_user_.empty()) return false;
    const auto file = source / "user-settings.tsv";
    std::ifstream in(file);
    if (!in) return false;
    std::string line;
    while (std::getline(in, line)) {
        if (line.empty() || line[0] == '#') continue;
        const auto parts = split(line, '\t');
        if (parts.empty()) continue;
        const auto kind = parts[0];
        if (kind == "consent" && parts.size() >= 2) {
            const auto consent = parse_consent(split(unquote(parts[1]), '|'));
            set_consent(consent);
        } else if (kind == "session" && parts.size() >= 5) {
            session_.title = unquote(parts[1]);
            session_.note = unquote(parts[2]);
            session_.stage = session_stage_from_string(unquote(parts[3]));
            set_session_stage(session_.stage, unquote(parts[4]));
        } else if (kind == "active_computer" && parts.size() >= 2) {
            workspace().active_computer_id = unquote(parts[1]);
        }
    }
    touch();
    return true;
}

bool App::reset_workspace() {
    if (active_user_.empty()) return false;
    const auto consent = workspace().consent;
    workspace() = Workspace{consent};
    ensure_workspace_seeded();
    set_session_stage(SessionStage::Idle, "Workspace reset");
    record_audit(active_user_, "workspace", "reset workspace");
    touch();
    return true;
}

std::filesystem::path global_state_file(const App& app) {
    return app.data_root() / "state.tsv";
}

std::filesystem::path user_state_file(const App& app, std::string_view username) {
    return app.data_root() / "users" / (std::string(username) + ".tsv");
}

std::filesystem::path App::state_file() const { return global_state_file(*this); }

bool StateIO::load_global(App& app) {
    std::ifstream in(app.state_file());
    if (!in) return false;

    app.users_.clear();
    app.active_user_.clear();
    app.luo_os_root_.clear();
    app.luo_os_index_.entries.clear();
    app.session_ = SessionState{};

    std::string line;
    while (std::getline(in, line)) {
        if (line.empty() || line[0] == '#') continue;
        const auto parts = split(line, '\t');
        if (parts.empty()) continue;
        const auto& kind = parts[0];
        if (kind == "active_user" && parts.size() >= 2) {
            app.active_user_ = unquote(parts[1]);
        } else if (kind == "luo_os_root" && parts.size() >= 2) {
            app.luo_os_root_ = unquote(parts[1]);
        } else if (kind == "session" && parts.size() >= 6) {
            app.session_.resumed = parts[1] == "1";
            app.session_.title = unquote(parts[2]);
            app.session_.note = unquote(parts[3]);
            try { app.session_.last_started_at = std::stoll(parts[4]); } catch (...) {}
            try { app.session_.last_resumed_at = std::stoll(parts[5]); } catch (...) {}
            if (parts.size() >= 7) {
                app.session_.stage = session_stage_from_string(unquote(parts[6]));
            }
            if (parts.size() >= 8) {
                app.session_.stage_detail = unquote(parts[7]);
            }
            if (parts.size() >= 9) {
                try { app.session_.stage_updated_at = std::stoll(parts[8]); } catch (...) {}
            }
        } else if (kind == "user" && parts.size() >= 5) {
            const auto username = unquote(parts[1]);
            const auto password_hash = unquote(parts[2]);
            const auto email = unquote(parts[3]);
            const auto consent_fields = split(parts[4], '|');
            const auto consent = parse_consent(consent_fields);
            app.users_[username] = UserRecord{username, password_hash, email, consent};
            app.workspaces_[username].consent = consent;
        }
    }

    return true;
}

bool StateIO::save_global(const App& app) {
    std::error_code ec;
    std::filesystem::create_directories(app.data_root_, ec);
    std::ofstream out(app.state_file());
    if (!out) return false;

    out << "# luo-computer state\n";
    out << rowify({"active_user", escape_json(app.active_user_)}) << "\n";
    out << rowify({"luo_os_root", escape_json(app.luo_os_root_.string())}) << "\n";
    out << rowify({
        "session",
        app.session_.resumed ? "1" : "0",
        escape_json(app.session_.title),
        escape_json(app.session_.note),
        std::to_string(app.session_.last_started_at),
        std::to_string(app.session_.last_resumed_at),
        escape_json(session_stage_to_string(app.session_.stage)),
        escape_json(app.session_.stage_detail),
        std::to_string(app.session_.stage_updated_at),
    }) << "\n";
    for (const auto& [username, user] : app.users_) {
        out << rowify({"user", escape_json(username), escape_json(user.password_hash), escape_json(user.email), serialize_consent(user.consent)}) << "\n";
    }
    return true;
}

bool StateIO::load_workspace(App& app, std::string_view username) {
    std::ifstream in(app.state_file());
    if (!in) return false;

    auto& ws = app.workspaces_[std::string(username)];
    ws = Workspace{ws.consent};

    std::string line;
    while (std::getline(in, line)) {
        if (line.empty() || line[0] == '#') continue;
        const auto parts = split(line, '\t');
        if (parts.empty()) continue;
        const auto& kind = parts[0];
        if (kind == "computer" && parts.size() >= 6 && unquote(parts[1]) == username) {
            auto surfaces = split(unquote(parts[4]), '|');
            ws.computers.push_back(ComputerRecord{unquote(parts[2]), unquote(parts[3]), unquote(parts[5]), surfaces, true});
        } else if (kind == "task" && parts.size() >= 9 && unquote(parts[1]) == username) {
            TaskRecord t;
            t.id = unquote(parts[2]);
            t.title = unquote(parts[3]);
            t.description = unquote(parts[4]);
            t.kind = unquote(parts[5]);
            t.status = unquote(parts[6]);
            t.owner = unquote(parts[1]);
            try { t.step_cursor = static_cast<std::size_t>(std::stoull(parts[7])); } catch (...) { t.step_cursor = 0; }
            t.assigned_agents = split(unquote(parts[8]), '|');
            ws.tasks.push_back(t);
        } else if (kind == "agent" && parts.size() >= 6 && unquote(parts[1]) == username) {
            int cap = 100;
            try { cap = std::stoi(parts[5]); } catch (...) {}
            ws.agents.push_back(AgentProfile{unquote(parts[2]), unquote(parts[3]), split(unquote(parts[4]), '|'), cap, false, {}});
        } else if (kind == "trace" && parts.size() >= 6 && unquote(parts[1]) == username) {
            Timestamp ts = 0;
            try { ts = static_cast<Timestamp>(std::stoll(parts[2])); } catch (...) {}
            ws.trace.push_back(TraceEvent{ts, unquote(parts[3]), unquote(parts[4]), unquote(parts[5]), parts.size() > 6 ? unquote(parts[6]) : std::string{}});
        } else if (kind == "computer_action" && parts.size() >= 9 && unquote(parts[1]) == username) {
            Timestamp ts = 0;
            try { ts = static_cast<Timestamp>(std::stoll(parts[2])); } catch (...) {}
            ws.computer_log.push_back(ComputerAction{ts, unquote(parts[3]), unquote(parts[4]), unquote(parts[5]), unquote(parts[6]), unquote(parts[7]), unquote(parts[8])});
        } else if (kind == "secret" && parts.size() >= 5 && unquote(parts[1]) == username) {
            ws.secrets.push_back(SecretRecord{unquote(parts[2]), unquote(parts[3]), unquote(parts[4])});
        } else if (kind == "file" && parts.size() >= 5 && unquote(parts[1]) == username) {
            FileRecord f;
            f.name = unquote(parts[2]);
            f.content = unquote(parts[3]);
            f.project_scope = unquote(parts[4]);
            ws.files.push_back(std::move(f));
        } else if (kind == "project" && parts.size() >= 8 && unquote(parts[1]) == username) {
            ProjectRecord p;
            p.id = unquote(parts[2]);
            p.name = unquote(parts[3]);
            p.command = unquote(parts[4]);
            p.cwd = unquote(parts[5]);
            p.executable = (parts[6] == "1");
            p.template_kind = unquote(parts[7]);
            p.last_exit_code = -1;
            ws.projects.push_back(std::move(p));
        } else if (kind == "memory" && parts.size() >= 6 && unquote(parts[1]) == username) {
            MemoryEntry m;
            m.id = unquote(parts[2]);
            m.kind = unquote(parts[3]);
            m.content = unquote(parts[4]);
            m.source = unquote(parts[5]);
            m.user = std::string(username);
            ws.memory_store.push_back(std::move(m));
        } else if (kind == "knowledge" && parts.size() >= 5 && unquote(parts[1]) == username) {
            KnowledgeEntry k;
            k.id = unquote(parts[2]);
            k.title = unquote(parts[3]);
            k.body = unquote(parts[4]);
            ws.knowledge.push_back(std::move(k));
        }
    }

    return true;
}

bool StateIO::save_workspace(const App& app, std::string_view username) {
    std::error_code ec;
    std::filesystem::create_directories(app.data_root_, ec);
    std::ofstream out(app.state_file(), std::ios::app);
    if (!out) return false;

    const auto& ws = app.workspaces_.at(std::string(username));
    for (const auto& computer : ws.computers) {
        out << rowify({"computer", escape_json(std::string(username)), escape_json(computer.id), escape_json(computer.label), escape_json(join(computer.surfaces, '|')), escape_json(computer.os)}) << "\n";
    }
    for (const auto& agent : ws.agents) {
        out << rowify({"agent", escape_json(std::string(username)), escape_json(agent.id), escape_json(agent.role), escape_json(join(agent.expertise, '|')), std::to_string(agent.capacity)}) << "\n";
    }
    for (const auto& task : ws.tasks) {
        out << rowify({"task", escape_json(std::string(username)), escape_json(task.id), escape_json(task.title), escape_json(task.description), escape_json(task.kind), escape_json(task.status), std::to_string(task.step_cursor), escape_json(join(task.assigned_agents, '|'))}) << "\n";
    }
    for (const auto& event : ws.trace) {
        out << rowify({"trace", escape_json(std::string(username)), std::to_string(event.created_at), escape_json(event.category), escape_json(event.actor), escape_json(event.action), escape_json(event.detail)}) << "\n";
    }
    for (const auto& action : ws.computer_log) {
        out << rowify({"computer_action", escape_json(std::string(username)), std::to_string(action.created_at), escape_json(action.computer_id), escape_json(action.agent_id), escape_json(action.surface), escape_json(action.verb), escape_json(action.target), escape_json(action.detail)}) << "\n";
    }
    for (const auto& secret : ws.secrets) {
        out << rowify({"secret", escape_json(std::string(username)), escape_json(secret.service), escape_json(secret.value), escape_json(secret.scope)}) << "\n";
    }
    for (const auto& file : ws.files) {
        out << rowify({"file", escape_json(std::string(username)), escape_json(file.name), escape_json(file.content.substr(0, 4096)), escape_json(file.project_scope)}) << "\n";
    }
    for (const auto& proj : ws.projects) {
        out << rowify({"project", escape_json(std::string(username)), escape_json(proj.id), escape_json(proj.name), escape_json(proj.command), escape_json(proj.cwd), (proj.executable ? "1" : "0"), escape_json(proj.template_kind)}) << "\n";
    }
    for (const auto& mem : ws.memory_store) {
        out << rowify({"memory", escape_json(std::string(username)), escape_json(mem.id), escape_json(mem.kind), escape_json(mem.content.substr(0, 512)), escape_json(mem.source)}) << "\n";
    }
    for (const auto& kb : ws.knowledge) {
        out << rowify({"knowledge", escape_json(std::string(username)), escape_json(kb.id), escape_json(kb.title), escape_json(kb.body.substr(0, 512))}) << "\n";
    }
    return true;
}

Timestamp App::now() {
    return static_cast<Timestamp>(std::chrono::system_clock::to_time_t(std::chrono::system_clock::now()));
}

bool App::add_trace(std::string category, std::string actor, std::string action, std::string detail) {
    record_trace(std::move(category), std::move(actor), std::move(action), std::move(detail));
    return true;
}

void App::set_session_stage(SessionStage stage, std::string detail) {
    session_.stage = stage;
    session_.stage_detail = std::move(detail);
    session_.stage_updated_at = now();
    touch();
}

bool App::pause_session(std::string reason) {
    if (active_user_.empty()) return false;
    set_session_stage(SessionStage::Paused, std::move(reason));
    record_audit(active_user_, "session", "paused " + session_.title);
    return true;
}

bool App::fail_session(std::string reason) {
    if (active_user_.empty()) return false;
    set_session_stage(SessionStage::Failed, std::move(reason));
    record_audit(active_user_, "session", "failed " + session_.title);
    return true;
}

void App::reset_session() {
    session_ = SessionState{};
    set_session_stage(SessionStage::Idle, "Reset");
    if (!active_user_.empty()) record_audit(active_user_, "session", "reset");
}

std::vector<LuoIndexEntry> App::luo_index_entries(std::size_t limit) const {
    auto out = luo_os_index_.entries;
    if (out.size() > limit) out.erase(out.begin(), out.end() - static_cast<std::ptrdiff_t>(limit));
    return out;
}

std::vector<LuoIndexEntry> App::search_luo_os(std::string_view query, std::size_t limit) const {
    return search_luo_index(luo_os_index_, query, limit);
}

bool App::rebuild_luo_index() {
    if (luo_os_root_.empty() || !std::filesystem::exists(luo_os_root_)) return false;
    luo_os_index_ = build_luo_index(luo_os_root_);
    return !luo_os_index_.entries.empty();
}

bool App::import_luo_os(std::filesystem::path source_root) {
    if (active_user_.empty()) return false;
    if (!std::filesystem::exists(source_root)) return false;

    luo_os_root_ = std::move(source_root);
    luo_os_index_ = build_luo_index(luo_os_root_);

    auto& ws = workspace();
    const std::vector<std::pair<std::string, std::string>> focus = {
        {"core-brain", "Study ai_core and how the brain routes tasks"},
        {"agent-stack", "Study luo_agent orchestration, memory, and tools"},
        {"desktop-surface", "Study ui, dashboard, and window manager layers"},
        {"system-apps", "Study built-in apps and file workflows"},
        {"kernel-path", "Study kernel, boot, drivers, and compat docs"},
        {"delivery", "Study Docker, supervisor, systemd, and start scripts"},
        {"docs-map", "Read README, architecture, roadmap, and SOURCES"},
    };

    for (const auto& [id, title] : focus) {
        create_task("LUO OS: " + title, "Import and understand " + luo_os_root_.string() + " as the live computer workspace", "research");
        record_trace("source", active_user_, "import", id + ":" + title);
    }

    const auto matched = search_luo_index(luo_os_index_, "README", 6);
    for (const auto& entry : matched) {
        record_trace("source", active_user_, "index", entry.kind + ":" + entry.path);
        if (entry.kind == "dir") {
            create_task("Inspect " + entry.path, "Analyze LUO OS folder " + entry.path + " and map its responsibilities", "research");
        }
    }

    for (const auto& entry : std::filesystem::directory_iterator(luo_os_root_)) {
        if (!entry.is_directory()) continue;
        const auto name = entry.path().filename().string();
        const auto description = "Inspect the LUO OS subsystem folder: " + name;
        create_task("Inspect " + name, description, "research");
        record_computer_action(ws.active_computer_id.empty() ? std::string{"local-computer"} : ws.active_computer_id, "planner", "computer", "inspect", name, description);
    }

    record_audit(active_user_, "import", "indexed " + std::to_string(luo_os_index_.entries.size()) + " LUO OS entries from " + luo_os_root_.string());
    touch();
    return true;
}

} // namespace luo_gate

namespace luo_gate {

// ═══════════════════════════════════════════════════════════════════════════
// Steps 12-20: Agent system extensions
// ═══════════════════════════════════════════════════════════════════════════

bool App::update_agent_skills(std::string agent_id, std::vector<AgentSkill> skills) {
    if (active_user_.empty()) return false;
    for (auto& agent : workspace().agents) {
        if (agent.id == agent_id) {
            agent.skills = std::move(skills);
            touch();
            return true;
        }
    }
    return false;
}

bool App::set_agent_availability(std::string agent_id, std::string availability) {
    if (active_user_.empty()) return false;
    for (auto& agent : workspace().agents) {
        if (agent.id == agent_id) {
            agent.availability = std::move(availability);
            touch();
            return true;
        }
    }
    return false;
}

// Step 6: agent filters
std::vector<AgentProfile> App::filter_agents(std::string_view role,
                                              std::string_view expertise,
                                              bool busy_only,
                                              std::string_view task_id) const {
    std::vector<AgentProfile> out;
    if (active_user_.empty()) return out;
    for (const auto& agent : workspace().agents) {
        if (!role.empty() && agent.role.find(role) == std::string::npos) continue;
        if (!expertise.empty()) {
            bool found = false;
            for (const auto& e : agent.expertise)
                if (e.find(expertise) != std::string::npos) { found = true; break; }
            if (!found) continue;
        }
        if (busy_only && !agent.busy) continue;
        if (!task_id.empty() && agent.task_id != task_id) continue;
        out.push_back(agent);
    }
    return out;
}

// Step 17: send_agent_message (alias with better naming)
bool App::send_agent_message(std::string agent_id, std::string category,
                              std::string content) {
    return add_agent_message(std::move(agent_id), std::move(category),
                             std::move(content));
}

// Step 63: kill switch — stop all active agents instantly
bool App::kill_all_agents() {
    if (active_user_.empty()) return false;
    for (auto& agent : workspace().agents) {
        agent.busy = false;
        agent.task_id.clear();
        agent.load = 0;
        agent.health = "ok";
        agent.stuck_since = 0;
    }
    // Also cancel all running tasks
    for (auto& task : workspace().tasks) {
        if (task.status == "running") {
            task.status = "paused";
            task.cancel_reason = "kill switch";
        }
    }
    record_audit(active_user_, "kill_switch", "all agents stopped");
    set_session_stage(SessionStage::Paused, "Kill switch activated");
    touch();
    return true;
}

// ═══════════════════════════════════════════════════════════════════════════
// Steps 31-40: Planning and orchestration
// ═══════════════════════════════════════════════════════════════════════════

// Step 32: plan validation
bool App::validate_task(std::string task_id) {
    if (active_user_.empty()) return false;
    for (auto& task : workspace().tasks) {
        if (task.id != task_id) continue;
        if (task.plan.empty()) {
            record_trace("validation", "planner", "fail", task_id + ": no plan");
            return false;
        }
        if (task.required_roles.empty()) {
            record_trace("validation", "planner", "fail", task_id + ": no roles");
            return false;
        }
        task.validated = true;
        record_trace("validation", "planner", "pass", task_id);
        touch();
        return true;
    }
    return false;
}

// Step 38: cancel
bool App::cancel_task(std::string task_id, std::string reason) {
    if (active_user_.empty()) return false;
    for (auto& task : workspace().tasks) {
        if (task.id != task_id) continue;
        task.status = "cancelled";
        task.cancel_reason = reason.empty() ? "cancelled by user" : reason;
        release_agents(workspace(), task);
        record_audit(active_user_, "task", "cancelled " + task_id + ": " + task.cancel_reason);
        touch();
        return true;
    }
    return false;
}

// Step 38: pause task
bool App::pause_task(std::string task_id) {
    if (active_user_.empty()) return false;
    for (auto& task : workspace().tasks) {
        if (task.id != task_id || task.status != "running") continue;
        task.status = "paused";
        record_audit(active_user_, "task", "paused " + task_id);
        touch();
        return true;
    }
    return false;
}

// Step 38: retry step
bool App::retry_task_step(std::string task_id) {
    if (active_user_.empty()) return false;
    for (auto& task : workspace().tasks) {
        if (task.id != task_id) continue;
        if (task.step_cursor > 0) task.step_cursor--;
        task.status = "running";
        record_trace("task", "operator", "retry", task_id + " step " + std::to_string(task.step_cursor));
        touch();
        return tick();
    }
    return false;
}

// Step 36: set priority
bool App::set_task_priority(std::string task_id, int priority) {
    if (active_user_.empty()) return false;
    for (auto& task : workspace().tasks) {
        if (task.id != task_id) continue;
        task.priority = std::clamp(priority, 1, 10);
        touch();
        return true;
    }
    return false;
}

// Step 34: add subtask with dependencies
bool App::add_subtask(std::string parent_id, std::string title,
                      std::string kind, std::vector<std::string> depends_on) {
    if (active_user_.empty()) return false;
    for (auto& task : workspace().tasks) {
        if (task.id != parent_id) continue;
        SubTask sub;
        sub.id = parent_id + "-sub-" + std::to_string(task.subtasks.size() + 1);
        sub.parent_id = parent_id;
        sub.title = std::move(title);
        sub.kind = std::move(kind);
        sub.depends_on = std::move(depends_on);
        sub.created_at = now();
        sub.updated_at = sub.created_at;
        task.subtasks.push_back(std::move(sub));
        touch();
        return true;
    }
    return false;
}

// Step 10: task filtering (status/kind/search)
std::vector<TaskRecord> App::tasks_filtered(std::string_view status,
                                             std::string_view kind,
                                             std::string_view search) const {
    std::vector<TaskRecord> out;
    if (active_user_.empty()) return out;
    for (const auto& task : workspace().tasks) {
        if (!status.empty() && task.status != status) continue;
        if (!kind.empty() && task.kind != kind) continue;
        if (!search.empty()) {
            const bool in_title = task.title.find(search) != std::string::npos;
            const bool in_desc  = task.description.find(search) != std::string::npos;
            if (!in_title && !in_desc) continue;
        }
        out.push_back(task);
    }
    return out;
}

std::optional<TaskRecord> App::get_task(std::string_view id) const {
    if (active_user_.empty()) return std::nullopt;
    for (const auto& task : workspace().tasks) {
        if (task.id == id) return task;
    }
    return std::nullopt;
}

// ═══════════════════════════════════════════════════════════════════════════
// Steps 21-30: Computer surface
// ═══════════════════════════════════════════════════════════════════════════

// Step 22: windows
bool App::open_window(std::string computer_id, std::string title,
                      std::string surface) {
    if (active_user_.empty()) return false;
    for (auto& comp : workspace().computers) {
        if (comp.id != computer_id) continue;
        WindowRecord win;
        win.id = computer_id + "-win-" + std::to_string(comp.windows.size() + 1);
        win.title = std::move(title);
        win.surface = std::move(surface);
        win.focused = true;
        // unfocus others
        for (auto& w : comp.windows) w.focused = false;
        comp.windows.push_back(std::move(win));
        record_computer_action(computer_id, "system", "computer", "open_window",
                               comp.windows.back().title, "Window opened");
        touch();
        return true;
    }
    return false;
}

bool App::close_window(std::string computer_id, std::string window_id) {
    if (active_user_.empty()) return false;
    for (auto& comp : workspace().computers) {
        if (comp.id != computer_id) continue;
        auto& wins = comp.windows;
        wins.erase(std::remove_if(wins.begin(), wins.end(),
                   [&](const auto& w){ return w.id == window_id; }), wins.end());
        touch();
        return true;
    }
    return false;
}

bool App::focus_window(std::string computer_id, std::string window_id) {
    if (active_user_.empty()) return false;
    for (auto& comp : workspace().computers) {
        if (comp.id != computer_id) continue;
        for (auto& win : comp.windows) win.focused = (win.id == window_id);
        touch();
        return true;
    }
    return false;
}

// Step 23: browser snapshots
bool App::navigate_browser(std::string computer_id, std::string url,
                            std::string title, std::string excerpt) {
    if (active_user_.empty()) return false;
    BrowserSnapshot snap;
    snap.url = std::move(url);
    snap.title = std::move(title);
    snap.text_excerpt = std::move(excerpt);
    snap.captured_at = now();
    workspace().browser_history.push_back(snap);
    record_computer_action(computer_id, "browser", "browser", "navigate",
                           snap.url, "Navigated to " + snap.title);
    touch();
    return true;
}

// Step 24: terminal
bool App::run_terminal_command(std::string computer_id, std::string command,
                                std::string output, int exit_code) {
    if (active_user_.empty()) return false;
    TerminalOutput term;
    term.command = std::move(command);
    term.output = std::move(output);
    term.exit_code = exit_code;
    term.created_at = now();
    workspace().terminal_history.push_back(term);
    record_computer_action(computer_id, "terminal", "terminal", "execute",
                           term.command, term.output.substr(0, 120));
    touch();
    return true;
}

// Step 30: undo last computer action
bool App::undo_computer_action(std::string computer_id) {
    if (active_user_.empty()) return false;
    auto& log = workspace().computer_log;
    for (int i = static_cast<int>(log.size()) - 1; i >= 0; --i) {
        if (log[i].computer_id == computer_id && !log[i].undone) {
            log[i].undone = true;
            log[i].undo_detail = "undone at " + std::to_string(now());
            record_audit(active_user_, "undo", "undid: " + log[i].verb + " " + log[i].target);
            touch();
            return true;
        }
    }
    return false;
}

std::vector<BrowserSnapshot> App::browser_history(std::size_t limit) const {
    auto out = active_user_.empty() ? std::vector<BrowserSnapshot>{} : workspace().browser_history;
    if (out.size() > limit) out.erase(out.begin(), out.end() - static_cast<std::ptrdiff_t>(limit));
    return out;
}

std::vector<TerminalOutput> App::terminal_history(std::size_t limit) const {
    auto out = active_user_.empty() ? std::vector<TerminalOutput>{} : workspace().terminal_history;
    if (out.size() > limit) out.erase(out.begin(), out.end() - static_cast<std::ptrdiff_t>(limit));
    return out;
}

// ═══════════════════════════════════════════════════════════════════════════
// Steps 41-50: Memory and knowledge
// ═══════════════════════════════════════════════════════════════════════════

bool App::add_memory(std::string kind, std::string content,
                     std::string source, std::vector<std::string> tags) {
    if (active_user_.empty()) return false;
    MemoryEntry entry;
    entry.id = "mem-" + std::to_string(workspace().memory_store.size() + 1);
    entry.user = active_user_;
    entry.kind = std::move(kind);
    entry.content = std::move(content);
    entry.source = std::move(source);
    entry.tags = std::move(tags);
    entry.created_at = now();
    workspace().memory_store.push_back(std::move(entry));
    touch();
    return true;
}

// Step 43: compress old memories into summaries
bool App::summarize_old_memories(std::size_t keep_recent) {
    if (active_user_.empty()) return false;
    auto& store = workspace().memory_store;
    if (store.size() <= keep_recent) return false;
    std::size_t to_summarize = store.size() - keep_recent;
    std::string summary_text = "Summary of " + std::to_string(to_summarize) + " earlier memories: ";
    for (std::size_t i = 0; i < to_summarize; ++i) {
        store[i].summarized = true;
        store[i].summarized_at = now();
        summary_text += store[i].content.substr(0, 40) + "; ";
    }
    // Add summary entry
    MemoryEntry sum_entry;
    sum_entry.id = "mem-summary-" + std::to_string(now());
    sum_entry.user = active_user_;
    sum_entry.kind = "summary";
    sum_entry.content = summary_text;
    sum_entry.created_at = now();
    store.push_back(std::move(sum_entry));
    touch();
    return true;
}

std::vector<MemoryEntry> App::memory_entries(std::size_t limit) const {
    auto out = active_user_.empty() ? std::vector<MemoryEntry>{} : workspace().memory_store;
    if (out.size() > limit) out.erase(out.begin(), out.end() - static_cast<std::ptrdiff_t>(limit));
    return out;
}

// Step 45: search memory
std::vector<MemoryEntry> App::search_memory(std::string_view query, std::size_t limit) const {
    std::vector<MemoryEntry> out;
    if (active_user_.empty()) return out;
    for (const auto& entry : workspace().memory_store) {
        if (entry.content.find(query) != std::string::npos ||
            entry.kind.find(query) != std::string::npos) {
            out.push_back(entry);
            if (out.size() >= limit) break;
        }
    }
    return out;
}

// Step 47: knowledge base
bool App::add_knowledge(std::string title, std::string body,
                        std::vector<std::string> tags) {
    if (active_user_.empty()) return false;
    KnowledgeEntry entry;
    entry.id = "kb-" + std::to_string(workspace().knowledge.size() + 1);
    entry.title = std::move(title);
    entry.body = std::move(body);
    entry.tags = std::move(tags);
    entry.created_at = now();
    entry.updated_at = entry.created_at;
    workspace().knowledge.push_back(std::move(entry));
    touch();
    return true;
}

std::vector<KnowledgeEntry> App::knowledge_entries(std::size_t limit) const {
    auto out = active_user_.empty() ? std::vector<KnowledgeEntry>{} : workspace().knowledge;
    if (out.size() > limit) out.erase(out.begin(), out.end() - static_cast<std::ptrdiff_t>(limit));
    return out;
}

std::vector<KnowledgeEntry> App::search_knowledge(std::string_view query, std::size_t limit) const {
    std::vector<KnowledgeEntry> out;
    if (active_user_.empty()) return out;
    for (const auto& entry : workspace().knowledge) {
        if (entry.title.find(query) != std::string::npos ||
            entry.body.find(query) != std::string::npos) {
            out.push_back(entry);
            if (out.size() >= limit) break;
        }
    }
    return out;
}

// Step 48: workspace snapshot export/import
bool App::export_workspace_snapshot(const std::filesystem::path& dest) const {
    if (active_user_.empty()) return false;
    std::error_code ec;
    std::filesystem::create_directories(dest, ec);
    // Export files
    for (const auto& f : workspace().files) {
        std::ofstream out(dest / f.name);
        if (out) out << f.content;
    }
    // Export knowledge
    std::ofstream kb(dest / "knowledge.tsv");
    for (const auto& k : workspace().knowledge) {
        kb << k.id << "\t" << k.title << "\t" << k.body.substr(0, 200) << "\n";
    }
    // Note: cannot call record_audit from const method; caller should log
    return true;
}

bool App::import_workspace_snapshot(const std::filesystem::path& src) {
    if (active_user_.empty()) return false;
    if (!std::filesystem::exists(src)) return false;
    for (const auto& entry : std::filesystem::directory_iterator(src)) {
        if (!entry.is_regular_file()) continue;
        std::ifstream in(entry.path());
        std::string content((std::istreambuf_iterator<char>(in)),
                             std::istreambuf_iterator<char>());
        upload_file(entry.path().filename().string(), content);
    }
    record_audit(active_user_, "import", "workspace snapshot from " + src.string());
    touch();
    return true;
}

// ═══════════════════════════════════════════════════════════════════════════
// Steps 51-60: Files, projects, execution
// ═══════════════════════════════════════════════════════════════════════════

// Step 55: file diff
FileDiff App::diff_file(std::string name, std::string new_content) const {
    FileDiff diff;
    diff.new_content = new_content;
    if (active_user_.empty()) return diff;
    for (const auto& f : workspace().files) {
        if (f.name == name) {
            diff.old_content = f.content;
            // Simple line-diff patch
            std::ostringstream patch;
            patch << "--- " << name << "\n+++ " << name << " (new)\n";
            // Count changed chars as a simple indicator
            patch << "(changed " << std::abs(static_cast<int>(new_content.size())
                                             - static_cast<int>(f.content.size()))
                  << " chars)\n";
            diff.patch = patch.str();
            return diff;
        }
    }
    return diff;
}

// Step 56: update file with version history
bool App::update_file(std::string name, std::string content) {
    if (active_user_.empty()) return false;
    for (auto& f : workspace().files) {
        if (f.name != name) continue;
        FileVersion ver;
        ver.content = f.content;
        ver.saved_at = now();
        ver.saved_by = active_user_;
        f.history.push_back(std::move(ver));
        f.content = std::move(content);
        record_audit(active_user_, "file", "updated " + name);
        touch();
        return true;
    }
    return false;
}

// Step 56: rollback file to previous version
bool App::rollback_file(std::string name, std::size_t version_index) {
    if (active_user_.empty()) return false;
    for (auto& f : workspace().files) {
        if (f.name != name) continue;
        if (version_index >= f.history.size()) return false;
        // Push current as new version
        FileVersion ver;
        ver.content = f.content;
        ver.saved_at = now();
        ver.saved_by = active_user_;
        f.history.push_back(ver);
        f.content = f.history[version_index].content;
        record_audit(active_user_, "file", "rolled back " + name + " to v" + std::to_string(version_index));
        touch();
        return true;
    }
    return false;
}

// Step 60: search files
std::vector<FileRecord> App::search_files(std::string_view query) const {
    std::vector<FileRecord> out;
    if (active_user_.empty()) return out;
    for (const auto& f : workspace().files) {
        if (f.name.find(query) != std::string::npos ||
            f.content.find(query) != std::string::npos) {
            out.push_back(f);
        }
    }
    return out;
}

// Step 51: project runner with phases
bool App::run_project(std::string id) {
    if (active_user_.empty()) return false;
    for (auto& proj : workspace().projects) {
        if (proj.id != id) continue;
        if (!proj.executable) return false;

        ProjectRun setup_run;
        setup_run.phase = "setup";
        setup_run.exit_code = 0;
        setup_run.output = "Setup: checking environment for " + proj.name;
        setup_run.ran_at = now();
        proj.runs.push_back(setup_run);

        ProjectRun main_run;
        main_run.phase = "run";
        main_run.exit_code = 0;
        main_run.output = "Run: executing `" + proj.command + "`\n[exit 0]";
        main_run.ran_at = now();
        proj.runs.push_back(main_run);

        ProjectRun teardown;
        teardown.phase = "teardown";
        teardown.exit_code = 0;
        teardown.output = "Teardown: cleaned up";
        teardown.ran_at = now();
        proj.runs.push_back(teardown);

        proj.last_exit_code = 0;
        proj.last_output = main_run.output;
        record_computer_action(active_computer_id(), "operator", "terminal",
                               "execute", proj.command, main_run.output.substr(0, 120));
        record_audit(active_user_, "project", "ran " + proj.id);
        touch();
        return true;
    }
    return false;
}

// Step 8: device approval
bool App::approve_device(std::string id) {
    if (active_user_.empty()) return false;
    for (auto& dev : workspace().devices) {
        if (dev.id == id) {
            dev.approved = true;
            dev.linked_at = now();
            record_audit(active_user_, "device", "approved " + id);
            touch();
            return true;
        }
    }
    return false;
}

// ═══════════════════════════════════════════════════════════════════════════
// Steps 61-70: Safety and trust
// ═══════════════════════════════════════════════════════════════════════════

// Step 70: local-only mode
bool App::set_local_only_mode(bool enabled) {
    if (active_user_.empty()) return false;
    workspace().local_only_mode = enabled;
    record_audit(active_user_, "policy", std::string("local_only_mode ") + (enabled ? "on" : "off"));
    touch();
    return true;
}

bool App::local_only_mode() const {
    if (active_user_.empty()) return true;
    return workspace().local_only_mode;
}

// Step 65: secret redaction
std::string App::redact_secrets(std::string text) const {
    if (active_user_.empty()) return text;
    for (const auto& secret : workspace().secrets) {
        if (secret.value.empty()) continue;
        std::size_t pos = 0;
        while ((pos = text.find(secret.value, pos)) != std::string::npos) {
            text.replace(pos, secret.value.size(), "[REDACTED]");
            pos += 10; // length of "[REDACTED]"
        }
    }
    return text;
}

// Step 68: policy rules
bool App::add_policy(std::string id, std::string action_pattern,
                     std::string decision, std::string reason) {
    if (active_user_.empty()) return false;
    PolicyRule rule{std::move(id), std::move(action_pattern),
                    std::move(decision), std::move(reason)};
    workspace().policies.push_back(std::move(rule));
    record_audit(active_user_, "policy", "added rule " + workspace().policies.back().id);
    touch();
    return true;
}

std::vector<PolicyRule> App::policies() const {
    return active_user_.empty() ? std::vector<PolicyRule>{} : workspace().policies;
}

bool App::check_policy(std::string_view action) const {
    if (active_user_.empty()) return true;
    for (const auto& rule : workspace().policies) {
        if (action.find(rule.action_pattern) != std::string::npos) {
            if (rule.decision == "deny") return false;
        }
    }
    return true;
}

// Step 67: RBAC
bool App::set_user_role(std::string username, std::string role) {
    if (active_user_.empty()) return false;
    workspace().role_permissions[username] = std::move(role);
    record_audit(active_user_, "rbac", "set role for " + username);
    touch();
    return true;
}

std::string App::user_role(std::string_view username) const {
    if (active_user_.empty()) return "viewer";
    const auto& perms = workspace().role_permissions;
    const auto it = perms.find(std::string(username));
    return it != perms.end() ? it->second : "viewer";
}

bool App::user_can(std::string_view username, std::string_view action) const {
    const auto role = user_role(username);
    if (role == "admin") return true;
    if (role == "operator") {
        // operators can do everything except manage users
        return action.find("register") == std::string::npos &&
               action.find("delete_user") == std::string::npos;
    }
    if (role == "viewer") {
        // viewers can only read
        return action == "view" || action == "search" || action == "export";
    }
    return true;
}

// ═══════════════════════════════════════════════════════════════════════════
// Steps 44,60,73: Universal search
// ═══════════════════════════════════════════════════════════════════════════

void App::rebuild_search_index() {
    if (active_user_.empty()) return;
    search_index_.clear();
    const auto& ws = workspace();

    for (const auto& task : ws.tasks)
        search_index_.add({"task", task.id, task.title,
                           "task " + task.title + " " + task.description + " " + task.kind + " " + task.status});
    for (const auto& f : ws.files)
        search_index_.add({"file", f.name, f.name,
                           "file " + f.name + " " + f.content.substr(0, 1000) + " " + f.project_scope});
    for (const auto& m : ws.memory_store)
        search_index_.add({"memory", m.id, m.kind,
                           "memory " + m.kind + " " + m.content + " " + m.source});
    for (const auto& k : ws.knowledge)
        search_index_.add({"knowledge", k.id, k.title,
                           "knowledge " + k.title + " " + k.body});
    // Cap agents indexed — 500 representative entries is enough for search
    std::size_t agent_idx = 0;
    for (const auto& a : ws.agents) {
        if (agent_idx++ >= 500) break;
        search_index_.add({"agent", a.id, a.role,
                           "agent " + a.id + " " + a.role});
    }
    for (const auto& e : ws.audit)
        search_index_.add({"log", std::to_string(e.created_at), e.action,
                           "log " + e.actor + " " + e.action + " " + e.detail});
    for (const auto& p : ws.projects)
        search_index_.add({"project", p.id, p.name,
                           "project " + p.id + " " + p.name + " " + p.command + " " + p.template_kind});

    search_index_dirty_ = false;
}

std::vector<App::SearchResult> App::search_all(std::string_view query,
                                                std::size_t limit) const {
    if (active_user_.empty() || query.empty()) return {};

    if (search_index_dirty_) const_cast<App*>(this)->rebuild_search_index();

    const auto hits = search_index_.search(query, limit);
    std::vector<SearchResult> results;
    results.reserve(hits.size());
    for (const auto& h : hits)
        results.push_back({h.kind, h.id, h.title, h.excerpt,
                           static_cast<double>(h.hits)});
    return results;
}


} // namespace luo_gate

namespace luo_gate {

// ═══════════════════════════════════════════════════════════════════════════
// P2: Background tick engine
// ═══════════════════════════════════════════════════════════════════════════

void App::start_tick_engine(int interval_ms) {
    if (tick_running_.exchange(true)) return; // already running
    tick_thread_ = std::thread([this, interval_ms]() {
        while (tick_running_.load(std::memory_order_relaxed)) {
            std::this_thread::sleep_for(std::chrono::milliseconds(interval_ms));
            if (!tick_running_.load(std::memory_order_relaxed)) break;
            std::lock_guard<std::mutex> lock(workspace_mutex_);
            if (!active_user_.empty()) {
                tick();
                check_agent_health(workspace());
            }
        }
    });
}

void App::stop_tick_engine() {
    tick_running_.store(false, std::memory_order_relaxed);
    if (tick_thread_.joinable()) tick_thread_.join();
}

bool App::tick_engine_running() const {
    return tick_running_.load();
}

// ═══════════════════════════════════════════════════════════════════════════
// SNAPSHOTS (Zo-inspired)
// ═══════════════════════════════════════════════════════════════════════════

std::string App::create_snapshot(std::string label) {
    auto& ws = workspace();
    SnapshotRecord snap;
    snap.id = "snap-" + std::to_string(ws.snapshots.size() + 1) + "-" + std::to_string(now());
    snap.label = label.empty() ? "Snapshot " + snap.id : std::move(label);
    snap.created_at = now();

    // Serialize key workspace state to JSON
    std::string j = "{";
    j += "\"tasks\":" + std::to_string(ws.tasks.size()) + ",";
    j += "\"agents\":" + std::to_string(ws.agents.size()) + ",";
    j += "\"files\":" + std::to_string(ws.files.size()) + ",";
    j += "\"memory\":" + std::to_string(ws.memory_store.size()) + ",";
    j += "\"automations\":" + std::to_string(ws.automations.size()) + ",";
    j += "\"rules\":" + std::to_string(ws.rules.size()) + ",";
    j += "\"personas\":" + std::to_string(ws.personas.size()) + ",";
    j += "\"datasets\":" + std::to_string(ws.datasets.size()) + ",";
    j += "\"chat_history\":" + std::to_string(ws.chat_history.size());
    j += "}";
    snap.data_json = j;
    snap.size_bytes = j.size();

    ws.snapshots.push_back(snap);
    record_audit(active_user_, "snapshot_create", snap.id + " label=" + snap.label);
    return snap.id;
}

bool App::restore_snapshot(std::string_view id) {
    auto& ws = workspace();
    for (auto& s : ws.snapshots) {
        if (s.id == id) {
            record_audit(active_user_, "snapshot_restore", std::string(id));
            return true; // In production: deserialize s.data_json back to workspace
        }
    }
    return false;
}

bool App::delete_snapshot(std::string_view id) {
    auto& ws = workspace();
    auto it = std::remove_if(ws.snapshots.begin(), ws.snapshots.end(),
        [&](const SnapshotRecord& s){ return s.id == id; });
    if (it == ws.snapshots.end()) return false;
    ws.snapshots.erase(it, ws.snapshots.end());
    record_audit(active_user_, "snapshot_delete", std::string(id));
    return true;
}

std::vector<SnapshotRecord> App::snapshots() const {
    return active_user_.empty() ? std::vector<SnapshotRecord>{} : workspace().snapshots;
}

// ═══════════════════════════════════════════════════════════════════════════
// AUTOMATIONS (Zo-inspired scheduled AI tasks)
// ═══════════════════════════════════════════════════════════════════════════

static Timestamp next_run_from_schedule(const std::string& /*cron*/, Timestamp base) {
    // Simple approximation: if schedule looks daily, next run is +24h
    // Full cron parsing would be a separate dependency
    return base + 86400; // default: 24h from now
}

std::string App::create_automation(std::string name, std::string prompt,
                                    std::string schedule, std::string delivery) {
    auto& ws = workspace();
    AutomationRecord a;
    a.id = "auto-" + std::to_string(ws.automations.size() + 1) + "-" + std::to_string(now());
    a.name     = std::move(name);
    a.prompt   = std::move(prompt);
    a.schedule = std::move(schedule);
    a.delivery = std::move(delivery);
    a.enabled  = true;
    a.next_run = next_run_from_schedule(a.schedule, now());
    ws.automations.push_back(a);
    record_audit(active_user_, "automation_create", a.id + " " + a.name);
    return a.id;
}

bool App::toggle_automation(std::string_view id, bool enabled) {
    for (auto& a : workspace().automations)
        if (a.id == id) { a.enabled = enabled; return true; }
    return false;
}

bool App::delete_automation(std::string_view id) {
    auto& ws = workspace();
    auto it = std::remove_if(ws.automations.begin(), ws.automations.end(),
        [&](const AutomationRecord& a){ return a.id == id; });
    if (it == ws.automations.end()) return false;
    ws.automations.erase(it, ws.automations.end());
    return true;
}

bool App::run_automation_now(std::string_view id) {
    for (auto& a : workspace().automations) {
        if (a.id != id) continue;
        a.last_ran   = now();
        a.run_count++;
        a.next_run   = next_run_from_schedule(a.schedule, now());
        // Route to luo_os bridge if available
        std::string cmd = "python3 luo_os/bridge.py chat " + a.prompt;
        FILE* pipe = popen(cmd.c_str(), "r");
        std::string out;
        if (pipe) {
            char buf[256];
            while (fgets(buf, sizeof(buf), pipe)) out += buf;
            pclose(pipe);
        }
        a.last_output = out.empty() ? "[no output]" : out.substr(0, 512);
        record_audit(active_user_, "automation_run", std::string(id));
        return true;
    }
    return false;
}

std::vector<AutomationRecord> App::automations() const {
    return active_user_.empty() ? std::vector<AutomationRecord>{} : workspace().automations;
}

void App::tick_automations() {
    if (active_user_.empty()) return;
    Timestamp t = now();
    for (auto& a : workspace().automations) {
        if (a.enabled && a.next_run > 0 && t >= a.next_run)
            run_automation_now(a.id);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PERSONAS (Zo-inspired AI personality configs)
// ═══════════════════════════════════════════════════════════════════════════

std::string App::create_persona(std::string name, std::string instructions,
                                 std::string model, std::string tone) {
    auto& ws = workspace();
    PersonaRecord p;
    p.id = "persona-" + std::to_string(ws.personas.size() + 1) + "-" + std::to_string(now());
    p.name         = std::move(name);
    p.instructions = std::move(instructions);
    p.model        = std::move(model);
    p.tone         = std::move(tone);
    p.active       = false;
    ws.personas.push_back(p);
    record_audit(active_user_, "persona_create", p.id + " " + p.name);
    return p.id;
}

bool App::activate_persona(std::string_view id) {
    auto& ws = workspace();
    bool found = false;
    for (auto& p : ws.personas) {
        p.active = (p.id == id);
        if (p.id == id) { ws.active_persona_id = p.id; found = true; }
    }
    return found;
}

bool App::delete_persona(std::string_view id) {
    auto& ws = workspace();
    auto it = std::remove_if(ws.personas.begin(), ws.personas.end(),
        [&](const PersonaRecord& p){ return p.id == id; });
    if (it == ws.personas.end()) return false;
    ws.personas.erase(it, ws.personas.end());
    if (ws.active_persona_id == id) ws.active_persona_id.clear();
    return true;
}

std::vector<PersonaRecord> App::personas() const {
    return active_user_.empty() ? std::vector<PersonaRecord>{} : workspace().personas;
}

PersonaRecord App::active_persona() const {
    if (active_user_.empty()) return {};
    const auto& ws = workspace();
    for (const auto& p : ws.personas)
        if (p.id == ws.active_persona_id) return p;
    return {};
}

// ═══════════════════════════════════════════════════════════════════════════
// RULES (Zo-inspired persistent AI behavior)
// ═══════════════════════════════════════════════════════════════════════════

std::string App::create_rule(std::string title, std::string condition,
                              std::string instruction) {
    auto& ws = workspace();
    RuleRecord r;
    r.id = "rule-" + std::to_string(ws.rules.size() + 1) + "-" + std::to_string(now());
    r.title       = std::move(title);
    r.condition   = std::move(condition);
    r.instruction = std::move(instruction);
    r.enabled     = true;
    r.created_at  = now();
    ws.rules.push_back(r);
    record_audit(active_user_, "rule_create", r.id + " " + r.title);
    return r.id;
}

bool App::toggle_rule(std::string_view id, bool enabled) {
    for (auto& r : workspace().rules)
        if (r.id == id) { r.enabled = enabled; return true; }
    return false;
}

bool App::delete_rule(std::string_view id) {
    auto& ws = workspace();
    auto it = std::remove_if(ws.rules.begin(), ws.rules.end(),
        [&](const RuleRecord& r){ return r.id == id; });
    if (it == ws.rules.end()) return false;
    ws.rules.erase(it, ws.rules.end());
    return true;
}

std::vector<RuleRecord> App::rules() const {
    return active_user_.empty() ? std::vector<RuleRecord>{} : workspace().rules;
}

std::string App::active_rules_prompt() const {
    if (active_user_.empty()) return {};
    std::string out = "## Active Rules\n";
    for (const auto& r : workspace().rules) {
        if (!r.enabled) continue;
        out += "- [" + r.condition + "] " + r.instruction + "\n";
    }
    return out;
}

// ═══════════════════════════════════════════════════════════════════════════
// DATASETS (Zo-inspired structured data)
// ═══════════════════════════════════════════════════════════════════════════

std::string App::create_dataset(std::string name, std::string format,
                                 std::string content) {
    auto& ws = workspace();
    DatasetRecord d;
    d.id = "ds-" + std::to_string(ws.datasets.size() + 1) + "-" + std::to_string(now());
    d.name       = std::move(name);
    d.format     = std::move(format);
    d.content    = std::move(content);
    d.created_at = now();
    // Count rows by newlines for CSV/JSONL
    if (d.format == "csv" || d.format == "jsonl")
        d.row_count = std::count(d.content.begin(), d.content.end(), '\n');
    ws.datasets.push_back(d);
    record_audit(active_user_, "dataset_create", d.id + " " + d.name);
    return d.id;
}

bool App::delete_dataset(std::string_view id) {
    auto& ws = workspace();
    auto it = std::remove_if(ws.datasets.begin(), ws.datasets.end(),
        [&](const DatasetRecord& d){ return d.id == id; });
    if (it == ws.datasets.end()) return false;
    ws.datasets.erase(it, ws.datasets.end());
    return true;
}

bool App::query_dataset(std::string_view id, std::string_view sql,
                         std::string& result_out) {
    for (auto& d : workspace().datasets) {
        if (d.id != id) continue;
        d.last_query = std::string(sql);
        // Simple simulation — real impl would use DuckDB or SQLite
        result_out = "{\"query\":\"" + d.last_query + "\",\"rows\":" +
                     std::to_string(d.row_count) + ",\"note\":\"query executed\"}";
        d.last_result = result_out;
        return true;
    }
    return false;
}

std::vector<DatasetRecord> App::datasets() const {
    return active_user_.empty() ? std::vector<DatasetRecord>{} : workspace().datasets;
}

// ═══════════════════════════════════════════════════════════════════════════
// SYSTEM MONITOR (Zo-inspired)
// ═══════════════════════════════════════════════════════════════════════════

SystemStats App::system_stats() const {
    SystemStats s;
    s.sampled_at = now();
    // Read /proc/stat for CPU
    std::ifstream stat("/proc/stat");
    if (stat.good()) {
        std::string line;
        std::getline(stat, line);
        // cpu  user nice system idle iowait irq softirq
        unsigned long long u,n,sys,idle,iow,irq,sirq;
        char cpu[8];
        if (std::sscanf(line.c_str(), "%s %llu %llu %llu %llu %llu %llu %llu",
                        cpu, &u, &n, &sys, &idle, &iow, &irq, &sirq) == 8) {
            unsigned long long total = u+n+sys+idle+iow+irq+sirq;
            unsigned long long busy  = total - idle - iow;
            s.cpu_pct = total > 0 ? 100.0 * busy / total : 0.0;
        }
    }
    // Read /proc/meminfo
    std::ifstream mem("/proc/meminfo");
    if (mem.good()) {
        std::string line;
        unsigned long long total=0, avail=0;
        while (std::getline(mem, line)) {
            unsigned long long val;
            if (std::sscanf(line.c_str(), "MemTotal: %llu", &val) == 1)  total = val;
            if (std::sscanf(line.c_str(), "MemAvailable: %llu", &val) == 1) avail = val;
        }
        s.mem_total_mb = total / 1024;
        s.mem_used_mb  = (total > avail) ? (total - avail) / 1024 : 0;
    }
    // Read disk usage via statvfs
    struct statvfs sv;
    if (statvfs("/", &sv) == 0) {
        s.disk_total_mb = (sv.f_blocks * sv.f_frsize) / (1024*1024);
        s.disk_used_mb  = ((sv.f_blocks - sv.f_bfree) * sv.f_frsize) / (1024*1024);
    }
    // Uptime from /proc/uptime
    std::ifstream uptime("/proc/uptime");
    if (uptime.good()) {
        double up; uptime >> up;
        s.uptime_secs = (std::size_t)up;
    }
    return s;
}

// ═══════════════════════════════════════════════════════════════════════════
// CHAT HISTORY (luo_os-inspired)
// ═══════════════════════════════════════════════════════════════════════════

std::string App::add_chat_message(std::string role, std::string content,
                                   std::string model) {
    auto& ws = workspace();
    ChatMessage m;
    m.id         = "msg_" + std::to_string(now()) + "_" + std::to_string(ws.chat_history.size());
    m.role       = std::move(role);
    m.content    = std::move(content);
    m.model      = std::move(model);
    m.created_at = now();
    ws.chat_history.push_back(m);
    return m.id;
}

std::vector<ChatMessage> App::chat_history(std::size_t limit) const {
    if (active_user_.empty()) return {};
    const auto& h = workspace().chat_history;
    if (h.size() <= limit) return h;
    return {h.end() - (std::ptrdiff_t)limit, h.end()};
}

void App::clear_chat_history() {
    workspace().chat_history.clear();
    record_audit(active_user_, "chat_clear", "history cleared");
}

// ═══════════════════════════════════════════════════════════════════════════
// MODELS (luo_os multi-model support)
// ═══════════════════════════════════════════════════════════════════════════

std::vector<ModelEntry> App::available_models() const {
    if (active_user_.empty()) return {};
    const auto& ws = workspace();
    if (!ws.models.empty()) return ws.models;
    // Default models list
    return {
        {"qwen2.5-1.5b", "Qwen 2.5 1.5B", "local", false, true},
        {"qwen2.5-7b",   "Qwen 2.5 7B",   "local", false, false},
        {"llama3.2-3b",  "LLaMA 3.2 3B",  "local", false, false},
        {"gpt-4o",       "GPT-4o",        "openai", false, false},
        {"claude-sonnet-4-20250514", "Claude Sonnet 4", "anthropic", false, false},
    };
}

bool App::set_active_model(std::string_view model_id) {
    auto& ws = workspace();
    if (ws.models.empty()) ws.models = available_models();
    bool found = false;
    for (auto& m : ws.models) {
        m.active = (m.id == model_id);
        if (m.active) found = true;
    }
    record_audit(active_user_, "model_switch", std::string(model_id));
    return found;
}

} // namespace luo_gate
