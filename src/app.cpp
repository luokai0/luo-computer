#include "luo_gate/app.hpp"
#include "luo_gate/platform.hpp"
#include "luo_gate/security.hpp"

#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <utility>

namespace luo_gate {
namespace {
std::vector<std::string> default_roles_for_kind(std::string_view kind) {
    if (kind == "build") return {"planner", "builder", "reviewer", "tester", "operator"};
    if (kind == "research") return {"researcher", "analyst", "writer"};
    if (kind == "ops") return {"operator", "monitor", "safety"};
    if (kind == "ui") return {"designer", "frontend", "tester"};
    return {"planner", "operator", "reviewer"};
}

std::string default_agent_id(std::size_t index) {
    return "agent-" + std::to_string(index + 1);
}

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

std::string default_computer_id() {
    return "local-computer";
}
} // namespace

App::App(std::filesystem::path data_root) : data_root_(data_root.empty() ? default_data_root() : std::move(data_root)) {
    ensure_workspace_seeded();
}

bool App::load() {
    ensure_workspace_seeded();
    std::ifstream in(state_file());
    if (!in) return false;
    std::string line;
    while (std::getline(in, line)) {
        if (line.rfind("active_user=", 0) == 0) active_user_ = line.substr(12);
        if (line.rfind("computer=", 0) == 0) workspace().active_computer_id = line.substr(9);
    }
    return true;
}

bool App::save() const {
    std::error_code ec;
    std::filesystem::create_directories(data_root_, ec);
    std::ofstream out(state_file());
    if (!out) return false;
    out << export_state();
    return true;
}

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

bool App::add_agent(std::string id, std::string role, std::vector<std::string> expertise, int capacity) {
    if (active_user_.empty()) return false;
    auto& agents = workspace().agents;
    if (std::any_of(agents.begin(), agents.end(), [&](const auto& a) { return a.id == id; })) return false;
    agents.push_back(AgentProfile{std::move(id), std::move(role), std::move(expertise), capacity, false, {}});
    touch();
    return true;
}

bool App::create_task(std::string title, std::string description, std::string kind) {
    if (active_user_.empty()) return false;
    auto& ws = workspace();
    TaskRecord task;
    task.id = "task-" + std::to_string(ws.tasks.size() + 1);
    task.title = std::move(title);
    task.description = std::move(description);
    task.kind = std::move(kind);
    task.owner = active_user_;
    task.created_at = now();
    task.updated_at = task.created_at;
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
        record_trace("task", step.actor, step.action, task.id + " -> " + step.detail);
        record_computer_action(ws.active_computer_id.empty() ? default_computer_id() : ws.active_computer_id, step.actor, step.surface, step.action, task.id, step.detail);
        task.step_cursor++;
        if (task.status == "done") release_agents(ws, task);
        progressed = true;
    }
    if (progressed) touch();
    return progressed;
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

bool App::record_computer_action(std::string computer_id, std::string agent_id, std::string surface, std::string verb, std::string target, std::string detail) {
    if (active_user_.empty()) return false;
    workspace().computer_log.push_back(ComputerAction{now(), std::move(computer_id), std::move(agent_id), std::move(surface), std::move(verb), std::move(target), std::move(detail)});
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

std::vector<SecretRecord> App::secrets() const {
    return active_user_.empty() ? std::vector<SecretRecord>{} : workspace().secrets;
}

bool App::upload_file(std::string name, std::string content) {
    if (active_user_.empty()) return false;
    workspace().files.push_back(FileRecord{std::move(name), std::move(content), now()});
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

bool App::add_project(std::string id, std::string name, std::string command, std::string cwd, bool executable) {
    if (active_user_.empty()) return false;
    auto& projects = workspace().projects;
    auto it = std::find_if(projects.begin(), projects.end(), [&](const auto& p) { return p.id == id; });
    ProjectRecord record{std::move(id), std::move(name), std::move(command), std::move(cwd), executable, -1, {}};
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
        s.role_counts = role_counts();
    }
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
        << "\"platform\":\"" << escape_json(s.platform) << "\","
        << "\"active_user\":\"" << escape_json(s.active_user) << "\"}";
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
    }
}

void App::seed_swarm(Workspace& ws) {
    const std::vector<std::pair<std::string, std::vector<std::string>>> seeds = {
        {"planner", {"planning", "decomposition"}},
        {"builder", {"implementation", "execution"}},
        {"reviewer", {"validation", "quality"}},
        {"tester", {"verification", "debugging"}},
        {"operator", {"orchestration", "delivery"}},
        {"researcher", {"research", "synthesis"}},
        {"designer", {"ux", "layout"}},
        {"writer", {"docs", "copy"}},
        {"monitor", {"telemetry", "watching"}},
        {"safety", {"consent", "policy"}},
    };
    for (std::size_t i = 0; i < 10000; ++i) {
        const auto& seed = seeds[i % seeds.size()];
        ws.agents.push_back(AgentProfile{default_agent_id(i), default_agent_role(i) + "-" + seed.first, seed.second, 100, false, {}});
    }
}

std::vector<std::string> App::roles_for_kind(std::string_view kind) const { return default_roles_for_kind(kind); }

std::vector<std::string> App::assign_agents(Workspace& ws, const std::vector<std::string>& roles, const std::string& task_id) {
    std::vector<std::string> assigned;
    for (const auto& role : roles) {
        auto it = std::find_if(ws.agents.begin(), ws.agents.end(), [&](const auto& a) { return !a.busy && a.role.find(role) != std::string::npos; });
        if (it == ws.agents.end()) it = std::find_if(ws.agents.begin(), ws.agents.end(), [&](const auto& a) { return !a.busy; });
        if (it != ws.agents.end()) {
            it->busy = true;
            it->task_id = task_id;
            assigned.push_back(it->id);
        }
    }
    return assigned;
}

void App::release_agents(Workspace& ws, const TaskRecord& task) {
    for (auto& agent : ws.agents) {
        if (agent.task_id == task.id) {
            agent.busy = false;
            agent.task_id.clear();
        }
    }
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
    if (auto_save_) save();
}

std::filesystem::path App::state_file() const { return data_root_ / "state.txt"; }

Timestamp App::now() {
    return static_cast<Timestamp>(std::chrono::system_clock::to_time_t(std::chrono::system_clock::now()));
}

bool App::add_trace(std::string category, std::string actor, std::string action, std::string detail) {
    record_trace(std::move(category), std::move(actor), std::move(action), std::move(detail));
    return true;
}

bool App::import_luo_os(std::filesystem::path source_root) {
    if (active_user_.empty()) return false;
    if (!std::filesystem::exists(source_root)) return false;

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
        create_task("LUO OS: " + title, "Import and understand " + source_root.string() + " as the live computer workspace", "research");
        record_trace("source", active_user_, "import", id + ":" + title);
    }

    for (const auto& entry : std::filesystem::directory_iterator(source_root)) {
        if (!entry.is_directory()) continue;
        const auto name = entry.path().filename().string();
        const auto description = "Inspect the LUO OS subsystem folder: " + name;
        create_task("Inspect " + name, description, "research");
        record_computer_action(ws.active_computer_id.empty() ? std::string{"local-computer"} : ws.active_computer_id, "planner", "computer", "inspect", name, description);
    }

    record_audit(active_user_, "import", "cloned LUO OS is now the live swarm workspace");
    touch();
    return true;
}

} // namespace luo_gate
