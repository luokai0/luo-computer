#define CPPHTTPLIB_NO_EXCEPTIONS
#include "luo_gate/server.hpp"
#include "luo_gate/ui.hpp"

#ifdef _MSC_VER
#pragma warning(push, 0)
#endif
#include "../external/httplib.h"
#ifdef _MSC_VER
#pragma warning(pop)
#endif

#include <atomic>
#include <fstream>
#include <mutex>
#include <sstream>
#include <thread>

namespace luo_gate {
namespace {

// ─── JSON helpers ─────────────────────────────────────────────────────────────
std::string json_str(std::string_view s) {
    std::ostringstream o;
    o << '"';
    for (unsigned char c : s) {
        switch (c) {
            case '"':  o << "\\\""; break;
            case '\\': o << "\\\\"; break;
            case '\n': o << "\\n";  break;
            case '\r': o << "\\r";  break;
            case '\t': o << "\\t";  break;
            default:   o << c;      break;
        }
    }
    o << '"';
    return o.str();
}

std::string json_bool(bool b) { return b ? "true" : "false"; }

// escape_json: same as json_str but returns the inner string (without outer quotes)
std::string escape_json(std::string_view s) {
    std::ostringstream o;
    for (unsigned char c : s) {
        switch (c) {
            case '"':  o << "\\\""; break;
            case '\\': o << "\\\\"; break;
            case '\n': o << "\\n";  break;
            case '\r': o << "\\r";  break;
            case '\t': o << "\\t";  break;
            default:   o << c;      break;
        }
    }
    return o.str();
}

// Minimal JSON body parser: extracts top-level string values
// Handles: {"key":"value","key2":"value2","key3":true/false/number}
std::map<std::string, std::string> parse_json(const std::string& body) {
    std::map<std::string, std::string> out;
    // Walk through looking for "key":"value" or "key":value pairs
    std::size_t i = 0;
    auto skip_ws = [&]{ while (i < body.size() && std::isspace((unsigned char)body[i])) ++i; };
    auto read_str = [&]() -> std::string {
        if (i >= body.size() || body[i] != '"') return {};
        ++i; // skip opening "
        std::string r;
        while (i < body.size() && body[i] != '"') {
            if (body[i] == '\\' && i+1 < body.size()) { ++i; r += body[i]; }
            else r += body[i];
            ++i;
        }
        if (i < body.size()) ++i; // skip closing "
        return r;
    };
    while (i < body.size()) {
        skip_ws();
        if (i >= body.size() || body[i] == '}') break;
        if (body[i] == '{' || body[i] == ',') { ++i; continue; }
        if (body[i] != '"') { ++i; continue; }
        std::string key = read_str();
        skip_ws();
        if (i < body.size() && body[i] == ':') ++i;
        skip_ws();
        std::string val;
        if (i < body.size() && body[i] == '"') {
            val = read_str();
        } else {
            // bare value (number, true, false, null, nested)
            std::size_t start = i;
            while (i < body.size() && body[i] != ',' && body[i] != '}') ++i;
            val = body.substr(start, i - start);
            // trim whitespace
            while (!val.empty() && std::isspace((unsigned char)val.back())) val.pop_back();
        }
        if (!key.empty()) out[key] = val;
    }
    return out;
}


// ─── Summary JSON ─────────────────────────────────────────────────────────────
std::string summary_json(const App& app) {
    const auto s = app.summary();
    std::ostringstream o;
    o << '{'
      << "\"users\":"     << s.user_count     << ','
      << "\"agents\":"    << s.agent_count    << ','
      << "\"tasks\":"     << s.task_count     << ','
      << "\"computers\":" << s.computer_count << ','
      << "\"files\":"     << s.file_count     << ','
      << "\"projects\":"  << s.project_count  << ','
      << "\"memory\":"    << s.memory_count   << ','
      << "\"knowledge\":" << s.knowledge_count<< ','
      << "\"audit\":"     << s.audit_count    << ','
      << "\"active_user\":" << json_str(s.active_user) << ','
      << "\"platform\":"    << json_str(s.platform)    << ','
      << "\"session_stage\":" << json_str(s.session_stage) << ','
      << "\"local_only\":" << json_bool(s.local_only_mode)
      << '}';
    return o.str();
}

// ─── Task JSON (full detail) ──────────────────────────────────────────────────
std::string task_json(const TaskRecord& t) {
    std::ostringstream o;
    o << '{'
      << "\"id\":"          << json_str(t.id)          << ','
      << "\"title\":"       << json_str(t.title)       << ','
      << "\"description\":" << json_str(t.description) << ','
      << "\"kind\":"        << json_str(t.kind)        << ','
      << "\"status\":"      << json_str(t.status)      << ','
      << "\"owner\":"       << json_str(t.owner)       << ','
      << "\"priority\":"    << t.priority               << ','
      << "\"validated\":"   << json_bool(t.validated)  << ','
      << "\"step_cursor\":" << t.step_cursor            << ','
      << "\"budget_steps\":" << t.budget_steps          << ','
      << "\"confidence\":"  << t.confidence             << ','
      << "\"cancel_reason\":" << json_str(t.cancel_reason) << ','
      << "\"plan\":[";
    bool first = true;
    for (const auto& step : t.plan) {
        if (!first) o << ',';
        first = false;
        o << '{'
          << "\"index\":"   << step.index      << ','
          << "\"actor\":"   << json_str(step.actor)   << ','
          << "\"action\":"  << json_str(step.action)  << ','
          << "\"detail\":"  << json_str(step.detail)  << ','
          << "\"status\":"  << json_str(step.status)  << ','
          << "\"surface\":" << json_str(step.surface) << ','
          << "\"agent_id\":" << json_str(step.agent_id) << ','
          << "\"output\":"  << json_str(step.output)
          << '}';
    }
    o << "],\"subtasks\":[";
    first = true;
    for (const auto& st : t.subtasks) {
        if (!first) o << ',';
        first = false;
        o << '{'
          << "\"id\":"     << json_str(st.id)     << ','
          << "\"title\":"  << json_str(st.title)  << ','
          << "\"kind\":"   << json_str(st.kind)   << ','
          << "\"status\":" << json_str(st.status) << ','
          << "\"agent_id\":" << json_str(st.agent_id)
          << '}';
    }
    o << "],\"memory\":[";
    first = true;
    for (const auto& m : t.memory) {
        if (!first) o << ',';
        first = false;
        o << json_str(m);
    }
    o << "]}";
    return o.str();
}

// ─── Tasks list JSON ──────────────────────────────────────────────────────────
std::string tasks_json(const App& app) {
    std::ostringstream o;
    o << '[';
    bool first = true;
    for (const auto& t : app.tasks()) {
        if (!first) o << ',';
        first = false;
        o << '{'
          << "\"id\":"          << json_str(t.id)          << ','
          << "\"title\":"       << json_str(t.title)       << ','
          << "\"description\":" << json_str(t.description) << ','
          << "\"kind\":"        << json_str(t.kind)        << ','
          << "\"status\":"      << json_str(t.status)      << ','
          << "\"priority\":"    << t.priority               << ','
          << "\"validated\":"   << json_bool(t.validated)  << ','
          << "\"step_cursor\":" << t.step_cursor            << ','
          << "\"plan_size\":"   << t.plan.size()            << ','
          << "\"subtask_count\":" << t.subtasks.size()
          << '}';
    }
    o << ']';
    return o.str();
}

// ─── Agents JSON ──────────────────────────────────────────────────────────────
std::string agents_json(const App& app) {
    std::ostringstream o;
    o << '[';
    bool first = true;
    for (const auto& a : app.agents(100)) {
        if (!first) o << ',';
        first = false;
        o << '{'
          << "\"id\":"           << json_str(a.id)           << ','
          << "\"role\":"         << json_str(a.role)         << ','
          << "\"busy\":"         << json_bool(a.busy)        << ','
          << "\"health\":"       << json_str(a.health)       << ','
          << "\"reliability\":"  << a.reliability             << ','
          << "\"availability\":" << json_str(a.availability) << ','
          << "\"load\":"         << a.load                   << ','
          << "\"task_id\":"      << json_str(a.task_id)
          << '}';
    }
    o << ']';
    return o.str();
}

// ─── Files JSON ───────────────────────────────────────────────────────────────
std::string files_json(const App& app) {
    std::ostringstream o;
    o << '[';
    bool first = true;
    for (const auto& f : app.files()) {
        if (!first) o << ',';
        first = false;
        o << '{'
          << "\"name\":"          << json_str(f.name)         << ','
          << "\"project_scope\":" << json_str(f.project_scope)<< ','
          << "\"version_count\":" << f.history.size()         << ','
          << "\"size\":"          << f.content.size()
          << '}';
    }
    o << ']';
    return o.str();
}

// ─── Memory JSON ─────────────────────────────────────────────────────────────
std::string memory_json(const App& app) {
    std::ostringstream o;
    o << '[';
    bool first = true;
    for (const auto& m : app.memory_entries(100)) {
        if (!first) o << ',';
        first = false;
        o << '{'
          << "\"id\":"         << json_str(m.id)         << ','
          << "\"kind\":"       << json_str(m.kind)       << ','
          << "\"content\":"    << json_str(m.content)    << ','
          << "\"source\":"     << json_str(m.source)     << ','
          << "\"summarized\":" << json_bool(m.summarized)
          << '}';
    }
    o << ']';
    return o.str();
}

// ─── Knowledge JSON ───────────────────────────────────────────────────────────
std::string knowledge_json(const App& app) {
    std::ostringstream o;
    o << '[';
    bool first = true;
    for (const auto& k : app.knowledge_entries(100)) {
        if (!first) o << ',';
        first = false;
        o << '{'
          << "\"id\":"    << json_str(k.id)    << ','
          << "\"title\":" << json_str(k.title) << ','
          << "\"body\":"  << json_str(k.body)
          << '}';
    }
    o << ']';
    return o.str();
}

// ─── Audit JSON ──────────────────────────────────────────────────────────────
std::string audit_json(const App& app) {
    std::ostringstream o;
    o << '[';
    bool first = true;
    for (const auto& e : app.audit_log(200)) {
        if (!first) o << ',';
        first = false;
        o << '{'
          << "\"ts\":"       << e.created_at          << ','
          << "\"category\":" << json_str(e.category)  << ','
          << "\"actor\":"    << json_str(e.actor)      << ','
          << "\"action\":"   << json_str(e.action)     << ','
          << "\"detail\":"   << json_str(e.detail)
          << '}';
    }
    o << ']';
    return o.str();
}

// ─── Projects JSON ────────────────────────────────────────────────────────────
std::string projects_json(const App& app) {
    std::ostringstream o;
    o << '[';
    bool first = true;
    for (const auto& p : app.projects()) {
        if (!first) o << ',';
        first = false;
        o << '{'
          << "\"id\":"            << json_str(p.id)            << ','
          << "\"name\":"          << json_str(p.name)          << ','
          << "\"command\":"       << json_str(p.command)       << ','
          << "\"template_kind\":" << json_str(p.template_kind) << ','
          << "\"executable\":"    << json_bool(p.executable)   << ','
          << "\"last_exit_code\":" << p.last_exit_code         << ','
          << "\"run_count\":"     << p.runs.size()
          << '}';
    }
    o << ']';
    return o.str();
}

// ─── Browser history JSON ─────────────────────────────────────────────────────
std::string browser_json(const App& app) {
    std::ostringstream o;
    o << '[';
    bool first = true;
    for (const auto& b : app.browser_history(50)) {
        if (!first) o << ',';
        first = false;
        o << '{'
          << "\"url\":"     << json_str(b.url)          << ','
          << "\"title\":"   << json_str(b.title)        << ','
          << "\"excerpt\":" << json_str(b.text_excerpt) << ','
          << "\"ts\":"      << b.captured_at
          << '}';
    }
    o << ']';
    return o.str();
}

// ─── Terminal history JSON ────────────────────────────────────────────────────
std::string terminal_json(const App& app) {
    std::ostringstream o;
    o << '[';
    bool first = true;
    for (const auto& t : app.terminal_history(50)) {
        if (!first) o << ',';
        first = false;
        o << '{'
          << "\"command\":"   << json_str(t.command)    << ','
          << "\"output\":"    << json_str(t.output)     << ','
          << "\"exit_code\":" << t.exit_code             << ','
          << "\"ts\":"        << t.created_at
          << '}';
    }
    o << ']';
    return o.str();
}

// ─── Computer log JSON ────────────────────────────────────────────────────────
std::string computer_log_json(const App& app) {
    std::ostringstream o;
    o << '[';
    bool first = true;
    for (const auto& a : app.computer_log(100)) {
        if (!first) o << ',';
        first = false;
        o << '{'
          << "\"ts\":"          << a.created_at           << ','
          << "\"computer_id\":" << json_str(a.computer_id)<< ','
          << "\"agent_id\":"    << json_str(a.agent_id)   << ','
          << "\"surface\":"     << json_str(a.surface)    << ','
          << "\"verb\":"        << json_str(a.verb)       << ','
          << "\"target\":"      << json_str(a.target)     << ','
          << "\"detail\":"      << json_str(a.detail)     << ','
          << "\"undone\":"      << json_bool(a.undone)
          << '}';
    }
    o << ']';
    return o.str();
}

// ─── Search JSON ──────────────────────────────────────────────────────────────
std::string search_json(const App& app, const std::string& query) {
    std::ostringstream o;
    o << '[';
    bool first = true;
    for (const auto& r : app.search_all(query, 20)) {
        if (!first) o << ',';
        first = false;
        o << '{'
          << "\"kind\":"    << json_str(r.kind)    << ','
          << "\"id\":"      << json_str(r.id)      << ','
          << "\"title\":"   << json_str(r.title)   << ','
          << "\"excerpt\":" << json_str(r.excerpt) << ','
          << "\"score\":"   << r.score
          << '}';
    }
    o << ']';
    return o.str();
}

// ─── Parse query param ────────────────────────────────────────────────────────
std::string get_param(const httplib::Params& params, const std::string& key,
                      const std::string& def = {}) {
    const auto it = params.find(key);
    return it != params.end() ? it->second : def;
}

// ─── CORS + JSON helpers ──────────────────────────────────────────────────────
void set_cors(httplib::Response& res) {
    res.set_header("Access-Control-Allow-Origin", "*");
    res.set_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS");
    res.set_header("Access-Control-Allow-Headers", "Content-Type");
}

void json_ok(httplib::Response& res, const std::string& body) {
    set_cors(res);
    res.set_content(body, "application/json");
}

void json_err(httplib::Response& res, int status, const std::string& msg) {
    set_cors(res);
    res.status = status;
    res.set_content("{\"error\":" + json_str(msg) + "}", "application/json");
}

// ─── Locked helpers ───────────────────────────────────────────────────────────
// READ: lock before reading shared state (tick thread also writes)
#define READ_LOCK(app) std::lock_guard<std::mutex> _lg((app).mutex())
// WRITE: same mutex — one mutex covers all
#define WRITE_LOCK(app) std::lock_guard<std::mutex> _lg((app).mutex())

} // anonymous namespace

// ─── Main server ─────────────────────────────────────────────────────────────
int run_server(App& app, int port) {
    {
        READ_LOCK(app);
        const auto preview = render_dashboard_html(app);
        std::ofstream(app.data_root() / "server.preview.html") << preview;
        std::ofstream(app.data_root() / "server.port.txt") << port;
    }

    httplib::Server svr;

    // ── Dashboard ────────────────────────────────────────────────────────────
    svr.Get("/", [&](const httplib::Request&, httplib::Response& res) {
        READ_LOCK(app);
        set_cors(res);
        res.set_content(render_dashboard_html(app), "text/html; charset=utf-8");
    });

    svr.Get("/status", [&](const httplib::Request&, httplib::Response& res) {
        READ_LOCK(app);
        set_cors(res);
        res.set_content(render_status_html(app), "text/html; charset=utf-8");
    });

    // ── API: summary ─────────────────────────────────────────────────────────
    svr.Get("/api/summary", [&](const httplib::Request&, httplib::Response& res) {
        READ_LOCK(app);
        json_ok(res, summary_json(app));
    });

    // ── API: tasks list ───────────────────────────────────────────────────────
    svr.Get("/api/tasks", [&](const httplib::Request& req, httplib::Response& res) {
        READ_LOCK(app);
        const auto status = get_param(req.params, "status");
        const auto kind   = get_param(req.params, "kind");
        const auto search = get_param(req.params, "search");
        const auto filtered = app.tasks_filtered(status, kind, search);
        std::ostringstream o;
        o << '[';
        bool first = true;
        for (const auto& t : filtered) {
            if (!first) o << ',';
            first = false;
            o << "{\"id\":"       << json_str(t.id)
              << ",\"title\":"    << json_str(t.title)
              << ",\"status\":"   << json_str(t.status)
              << ",\"kind\":"     << json_str(t.kind)
              << ",\"priority\":" << t.priority << '}';
        }
        o << ']';
        json_ok(res, o.str());
    });

    // ── API: task detail ──────────────────────────────────────────────────────
    svr.Get("/api/tasks/:id", [&](const httplib::Request& req, httplib::Response& res) {
        READ_LOCK(app);
        const auto id = req.path_params.at("id");
        const auto task = app.get_task(id);
        if (!task) { json_err(res, 404, "task not found"); return; }
        json_ok(res, task_json(*task));
    });

    // ── API: create task ──────────────────────────────────────────────────────
    svr.Post("/api/tasks", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto title = get_param(req.params, "title");
        const auto desc  = get_param(req.params, "description");
        const auto kind  = get_param(req.params, "kind", "general");
        const auto pri_s = get_param(req.params, "priority", "5");
        if (title.empty()) { json_err(res, 400, "title required"); return; }
        int priority = 5;
        try { priority = std::clamp(std::stoi(pri_s.empty() ? "5" : pri_s), 1, 10); }
        catch (...) { priority = 5; }
        if (app.create_task(title, desc, kind, priority)) {
            app.tick();
            json_ok(res, "{\"ok\":true}");
        } else {
            json_err(res, 400, "create_task failed");
        }
    });

    svr.Post("/api/tasks/:id/cancel", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto id     = req.path_params.at("id");
        const auto reason = get_param(req.params, "reason");
        json_ok(res, app.cancel_task(id, reason) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Post("/api/tasks/:id/reopen", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto id = req.path_params.at("id");
        json_ok(res, app.reopen_task(id) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Post("/api/tasks/:id/pause", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto id = req.path_params.at("id");
        json_ok(res, app.pause_task(id) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Post("/api/tasks/:id/resume", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto id = req.path_params.at("id");
        json_ok(res, app.resume_task(id) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Post("/api/tasks/:id/retry", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto id = req.path_params.at("id");
        json_ok(res, app.retry_task_step(id) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Post("/api/tasks/:id/tick", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        (void)req;
        json_ok(res, app.tick() ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Post("/api/tasks/:id/priority", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto id  = req.path_params.at("id");
        const auto pri = get_param(req.params, "priority", "5");
        int pval = 5;
        try { pval = std::stoi(pri); } catch (...) { pval = 5; }
        json_ok(res, app.set_task_priority(id, pval) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Post("/api/tasks/:id/validate", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto id = req.path_params.at("id");
        json_ok(res, app.validate_task(id) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Post("/api/tasks/:id/subtask", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto id    = req.path_params.at("id");
        const auto title = get_param(req.params, "title");
        const auto kind  = get_param(req.params, "kind", "general");
        if (title.empty()) { json_err(res, 400, "title required"); return; }
        json_ok(res, app.add_subtask(id, title, kind) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── API: agents ───────────────────────────────────────────────────────────
    svr.Get("/api/agents", [&](const httplib::Request& req, httplib::Response& res) {
        READ_LOCK(app);
        const auto role   = get_param(req.params, "role");
        const auto health = get_param(req.params, "health");
        if (!role.empty() || !health.empty()) {
            // Filtered agent list
            std::ostringstream o;
            o << '[';
            bool first = true;
            for (const auto& a : app.agents(200)) {
                if (!role.empty() && a.role.find(role) == std::string::npos) continue;
                if (!health.empty() && a.health != health) continue;
                if (!first) o << ',';
                first = false;
                o << "{\"id\":"          << json_str(a.id)          << ','
                  << "\"role\":"         << json_str(a.role)        << ','
                  << "\"busy\":"         << json_bool(a.busy)       << ','
                  << "\"health\":"       << json_str(a.health)      << ','
                  << "\"reliability\":"  << a.reliability            << ','
                  << "\"availability\":" << json_str(a.availability)<< ','
                  << "\"load\":"         << a.load                  << ','
                  << "\"task_id\":"      << json_str(a.task_id)     << '}';
            }
            o << ']';
            json_ok(res, o.str());
        } else {
            json_ok(res, agents_json(app));
        }
    });

    svr.Post("/api/agents/kill", [&](const httplib::Request&, httplib::Response& res) {
        WRITE_LOCK(app);
        json_ok(res, app.kill_all_agents() ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Post("/api/agents/:id/message", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto id      = req.path_params.at("id");
        const auto content = get_param(req.params, "content");
        const auto cat     = get_param(req.params, "category", "instruction");
        if (content.empty()) { json_err(res, 400, "content required"); return; }
        json_ok(res, app.send_agent_message(id, cat, content) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── API: memory ───────────────────────────────────────────────────────────
    svr.Get("/api/memory", [&](const httplib::Request& req, httplib::Response& res) {
        READ_LOCK(app);
        const auto q = get_param(req.params, "q");
        if (!q.empty()) {
            std::ostringstream o;
            o << '[';
            bool first = true;
            for (const auto& m : app.search_memory(q, 30)) {
                if (!first) o << ',';
                first = false;
                o << "{\"id\":"      << json_str(m.id)      << ','
                  << "\"kind\":"     << json_str(m.kind)    << ','
                  << "\"content\":"  << json_str(m.content) << '}';
            }
            o << ']';
            json_ok(res, o.str());
        } else {
            json_ok(res, memory_json(app));
        }
    });

    svr.Post("/api/memory", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto kind    = get_param(req.params, "kind", "note");
        const auto content = get_param(req.params, "content");
        if (content.empty()) { json_err(res, 400, "content required"); return; }
        json_ok(res, app.add_memory(kind, content) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Post("/api/memory/summarize", [&](const httplib::Request&, httplib::Response& res) {
        WRITE_LOCK(app);
        json_ok(res, app.summarize_old_memories(50) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── API: knowledge ────────────────────────────────────────────────────────
    svr.Get("/api/knowledge", [&](const httplib::Request& req, httplib::Response& res) {
        READ_LOCK(app);
        const auto q = get_param(req.params, "q");
        if (!q.empty()) {
            std::ostringstream o;
            o << '[';
            bool first = true;
            for (const auto& k : app.search_knowledge(q, 20)) {
                if (!first) o << ',';
                first = false;
                o << "{\"id\":"    << json_str(k.id)    << ','
                  << "\"title\":"  << json_str(k.title) << ','
                  << "\"body\":"   << json_str(k.body)  << '}';
            }
            o << ']';
            json_ok(res, o.str());
        } else {
            json_ok(res, knowledge_json(app));
        }
    });

    svr.Post("/api/knowledge", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto title = get_param(req.params, "title");
        const auto body  = get_param(req.params, "body");
        if (title.empty()) { json_err(res, 400, "title required"); return; }
        json_ok(res, app.add_knowledge(title, body) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── API: files ────────────────────────────────────────────────────────────
    svr.Get("/api/files", [&](const httplib::Request& req, httplib::Response& res) {
        READ_LOCK(app);
        const auto q = get_param(req.params, "q");
        if (!q.empty()) {
            std::ostringstream o;
            o << '[';
            bool first = true;
            for (const auto& f : app.search_files(q)) {
                if (!first) o << ',';
                first = false;
                o << "{\"name\":"  << json_str(f.name)  << ','
                  << "\"size\":"   << f.content.size()  << '}';
            }
            o << ']';
            json_ok(res, o.str());
        } else {
            json_ok(res, files_json(app));
        }
    });

    svr.Get("/api/files/:name", [&](const httplib::Request& req, httplib::Response& res) {
        READ_LOCK(app);
        const auto name = req.path_params.at("name");
        for (const auto& f : app.files()) {
            if (f.name == name) {
                std::ostringstream o;
                o << "{\"name\":"          << json_str(f.name)         << ','
                  << "\"content\":"        << json_str(f.content)      << ','
                  << "\"project_scope\":"  << json_str(f.project_scope)<< ','
                  << "\"version_count\":"  << f.history.size()         << '}';
                json_ok(res, o.str());
                return;
            }
        }
        json_err(res, 404, "file not found");
    });

    svr.Post("/api/files", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto name    = get_param(req.params, "name");
        const auto content = req.body;
        if (name.empty()) { json_err(res, 400, "name required"); return; }
        json_ok(res, app.upload_file(name, content) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Post("/api/files/:name/rollback", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto name  = req.path_params.at("name");
        const auto ver_s = get_param(req.params, "version", "0");
        std::size_t ver  = 0;
        try { ver = static_cast<std::size_t>(std::stoul(ver_s)); } catch (...) { ver = 0; }
        json_ok(res, app.rollback_file(name, ver) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── API: projects ─────────────────────────────────────────────────────────
    svr.Get("/api/projects", [&](const httplib::Request&, httplib::Response& res) {
        READ_LOCK(app);
        json_ok(res, projects_json(app));
    });

    svr.Post("/api/projects/:id/run", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto id = req.path_params.at("id");
        json_ok(res, app.run_project(id) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── API: computer surface ─────────────────────────────────────────────────
    svr.Get("/api/computer/log", [&](const httplib::Request&, httplib::Response& res) {
        READ_LOCK(app);
        json_ok(res, computer_log_json(app));
    });

    svr.Get("/api/computer/browser", [&](const httplib::Request&, httplib::Response& res) {
        READ_LOCK(app);
        json_ok(res, browser_json(app));
    });

    svr.Post("/api/computer/browser", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto url     = get_param(req.params, "url");
        const auto title   = get_param(req.params, "title");
        const auto excerpt = get_param(req.params, "excerpt");
        if (url.empty()) { json_err(res, 400, "url required"); return; }
        const auto cid = app.active_computer_id();
        json_ok(res, app.navigate_browser(cid, url, title, excerpt) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Get("/api/computer/terminal", [&](const httplib::Request&, httplib::Response& res) {
        READ_LOCK(app);
        json_ok(res, terminal_json(app));
    });

    svr.Post("/api/computer/terminal", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto command = get_param(req.params, "command");
        const auto output  = get_param(req.params, "output");
        int exit_code = 0;
        try { exit_code = std::stoi(get_param(req.params, "exit_code", "0")); } catch (...) {}
        if (command.empty()) { json_err(res, 400, "command required"); return; }
        const auto cid = app.active_computer_id();
        json_ok(res, app.run_terminal_command(cid, command, output, exit_code) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Post("/api/computer/undo", [&](const httplib::Request&, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto cid = app.active_computer_id();
        json_ok(res, app.undo_computer_action(cid) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── API: session ──────────────────────────────────────────────────────────
    svr.Get("/api/session", [&](const httplib::Request&, httplib::Response& res) {
        READ_LOCK(app);
        const auto s = app.session_state();
        std::ostringstream o;
        o << '{'
          << "\"title\":"           << json_str(s.title)                  << ','
          << "\"stage\":"           << json_str([&s]{
                switch(s.stage){
                    case SessionStage::Starting: return "starting";
                    case SessionStage::Running:  return "running";
                    case SessionStage::Paused:   return "paused";
                    case SessionStage::Failed:   return "failed";
                    case SessionStage::Resumed:  return "resumed";
                    default:                     return "idle";
                }
            }())                                                           << ','
          << "\"stage_detail\":"    << json_str(s.stage_detail)           << ','
          << "\"last_started_at\":" << s.last_started_at                  << ','
          << "\"resumed\":"         << json_bool(s.resumed)
          << '}';
        json_ok(res, o.str());
    });

    svr.Post("/api/session/pause", [&](const httplib::Request&, httplib::Response& res) {
        WRITE_LOCK(app);
        json_ok(res, app.pause_session() ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Post("/api/session/resume", [&](const httplib::Request&, httplib::Response& res) {
        WRITE_LOCK(app);
        json_ok(res, app.resume_session() ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── API: approvals ────────────────────────────────────────────────────────
    svr.Get("/api/approvals", [&](const httplib::Request&, httplib::Response& res) {
        READ_LOCK(app);
        std::ostringstream o;
        o << '[';
        bool first = true;
        for (const auto& a : app.pending_approvals()) {
            if (!first) o << ',';
            first = false;
            o << json_str(a);
        }
        o << ']';
        json_ok(res, o.str());
    });

    svr.Post("/api/approvals/:action/approve", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto action = req.path_params.at("action");
        json_ok(res, app.approve_action(action) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── API: audit log ────────────────────────────────────────────────────────
    svr.Get("/api/audit", [&](const httplib::Request&, httplib::Response& res) {
        READ_LOCK(app);
        json_ok(res, audit_json(app));
    });

    // ── API: search ───────────────────────────────────────────────────────────
    svr.Get("/api/search", [&](const httplib::Request& req, httplib::Response& res) {
        READ_LOCK(app);
        const auto query = get_param(req.params, "q");
        if (query.empty()) { json_err(res, 400, "q required"); return; }
        json_ok(res, search_json(app, query));
    });

    // ── API: save ─────────────────────────────────────────────────────────────
    svr.Post("/api/save", [&](const httplib::Request&, httplib::Response& res) {
        READ_LOCK(app);  // save only reads state to write to disk
        json_ok(res, app.save() ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── API: policy ───────────────────────────────────────────────────────────
    svr.Get("/api/policies", [&](const httplib::Request&, httplib::Response& res) {
        READ_LOCK(app);
        std::ostringstream o;
        o << '[';
        bool first = true;
        for (const auto& p : app.policies()) {
            if (!first) o << ',';
            first = false;
            o << '{'
              << "\"id\":"              << json_str(p.id)             << ','
              << "\"action_pattern\":"  << json_str(p.action_pattern) << ','
              << "\"decision\":"        << json_str(p.decision)       << ','
              << "\"reason\":"          << json_str(p.reason)
              << '}';
        }
        o << ']';
        json_ok(res, o.str());
    });

    svr.Post("/api/policies", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        const auto id      = get_param(req.params, "id");
        const auto pattern = get_param(req.params, "action_pattern");
        const auto decision= get_param(req.params, "decision", "allow");
        const auto reason  = get_param(req.params, "reason");
        if (id.empty() || pattern.empty()) { json_err(res, 400, "id and action_pattern required"); return; }
        json_ok(res, app.add_policy(id, pattern, decision, reason) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── SSE: live events ──────────────────────────────────────────────────────
    // Streams a summary event every 2 seconds while the client is connected.
    svr.Get("/api/events", [&](const httplib::Request&, httplib::Response& res) {
        set_cors(res);
        res.set_header("Content-Type", "text/event-stream");
        res.set_header("Cache-Control", "no-cache");
        res.set_header("X-Accel-Buffering", "no");

        // httplib supports chunked streaming via set_chunked_content_provider
        res.set_chunked_content_provider(
            "text/event-stream",
            [&app](std::size_t /*offset*/, httplib::DataSink& sink) -> bool {
                // Send one snapshot and keep alive by re-registering
                std::string data;
                {
                    std::lock_guard<std::mutex> lock(app.mutex());
                    data = "data: " + [&app]() -> std::string {
                        const auto s = app.summary();
                        std::ostringstream o;
                        o << "{\"agents\":" << s.agent_count
                          << ",\"tasks\":"  << s.task_count
                          << ",\"stage\":"  << '"' << s.session_stage << '"'
                          << ",\"audit\":"  << s.audit_count << '}';
                        return o.str();
                    }() + "\n\n";
                }
                if (!sink.write(data.data(), data.size())) return false;
                std::this_thread::sleep_for(std::chrono::seconds(2));
                return true;  // keep connection alive
            }
        );
    });

    // ══════════════════════════════════════════════════════════════════════════
    // SNAPSHOTS (Zo-inspired)
    // ══════════════════════════════════════════════════════════════════════════

    svr.Get("/api/snapshots", [&](const httplib::Request&, httplib::Response& res) {
        WRITE_LOCK(app);
        std::string j = "[";
        for (const auto& s : app.snapshots()) {
            if (j.size() > 1) j += ",";
            j += "{\"id\":\"" + s.id + "\",\"label\":\"" + escape_json(s.label) +
                 "\",\"created_at\":" + std::to_string(s.created_at) +
                 ",\"size_bytes\":" + std::to_string(s.size_bytes) +
                 ",\"data\":" + s.data_json + "}";
        }
        j += "]";
        json_ok(res, j);
    });

    svr.Post("/api/snapshots", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        auto body = parse_json(req.body);
        std::string label = body.count("label") ? body["label"] : "";
        auto id = app.create_snapshot(label);
        json_ok(res, "{\"id\":\"" + id + "\",\"ok\":true}");
    });

    svr.Post("/api/snapshots/:id/restore", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        bool ok = app.restore_snapshot(req.path_params.at("id"));
        json_ok(res, ok ? "{\"ok\":true}" : "{\"ok\":false,\"error\":\"not found\"}");
    });

    svr.Delete("/api/snapshots/:id", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        bool ok = app.delete_snapshot(req.path_params.at("id"));
        json_ok(res, ok ? "{\"ok\":true}" : "{\"ok\":false,\"error\":\"not found\"}");
    });

    // ══════════════════════════════════════════════════════════════════════════
    // AUTOMATIONS (Zo-inspired)
    // ══════════════════════════════════════════════════════════════════════════

    svr.Get("/api/automations", [&](const httplib::Request&, httplib::Response& res) {
        WRITE_LOCK(app);
        std::string j = "[";
        for (const auto& a : app.automations()) {
            if (j.size() > 1) j += ",";
            j += "{\"id\":\"" + a.id + "\",\"name\":\"" + escape_json(a.name) +
                 "\",\"prompt\":\"" + escape_json(a.prompt) +
                 "\",\"schedule\":\"" + escape_json(a.schedule) +
                 "\",\"delivery\":\"" + a.delivery +
                 "\",\"enabled\":" + (a.enabled ? "true" : "false") +
                 ",\"last_ran\":" + std::to_string(a.last_ran) +
                 ",\"next_run\":" + std::to_string(a.next_run) +
                 ",\"run_count\":" + std::to_string(a.run_count) +
                 ",\"last_output\":\"" + escape_json(a.last_output) + "\"}";
        }
        j += "]";
        json_ok(res, j);
    });

    svr.Post("/api/automations", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        auto body = parse_json(req.body);
        if (!body.count("name") || !body.count("prompt") || !body.count("schedule")) {
            res.status = 400;
            json_ok(res, "{\"error\":\"name, prompt, schedule required\"}"); return;
        }
        auto id = app.create_automation(body["name"], body["prompt"],
                                        body["schedule"],
                                        body.count("delivery") ? body["delivery"] : "dashboard");
        json_ok(res, "{\"id\":\"" + id + "\",\"ok\":true}");
    });

    svr.Post("/api/automations/:id/toggle", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        auto body = parse_json(req.body);
        bool enabled = body.count("enabled") ? (body["enabled"] == "true") : true;
        bool ok = app.toggle_automation(req.path_params.at("id"), enabled);
        json_ok(res, ok ? "{\"ok\":true}" : "{\"ok\":false,\"error\":\"not found\"}");
    });

    svr.Post("/api/automations/:id/run", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        bool ok = app.run_automation_now(req.path_params.at("id"));
        json_ok(res, ok ? "{\"ok\":true}" : "{\"ok\":false,\"error\":\"not found\"}");
    });

    svr.Delete("/api/automations/:id", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        bool ok = app.delete_automation(req.path_params.at("id"));
        json_ok(res, ok ? "{\"ok\":true}" : "{\"ok\":false,\"error\":\"not found\"}");
    });

    // ══════════════════════════════════════════════════════════════════════════
    // PERSONAS (Zo-inspired)
    // ══════════════════════════════════════════════════════════════════════════

    svr.Get("/api/personas", [&](const httplib::Request&, httplib::Response& res) {
        WRITE_LOCK(app);
        std::string j = "[";
        for (const auto& p : app.personas()) {
            if (j.size() > 1) j += ",";
            j += "{\"id\":\"" + p.id + "\",\"name\":\"" + escape_json(p.name) +
                 "\",\"instructions\":\"" + escape_json(p.instructions) +
                 "\",\"model\":\"" + escape_json(p.model) +
                 "\",\"tone\":\"" + p.tone +
                 "\",\"active\":" + (p.active ? "true" : "false") + "}";
        }
        j += "]";
        json_ok(res, j);
    });

    svr.Post("/api/personas", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        auto body = parse_json(req.body);
        if (!body.count("name") || !body.count("instructions")) {
            res.status = 400;
            json_ok(res, "{\"error\":\"name and instructions required\"}"); return;
        }
        auto id = app.create_persona(body["name"], body["instructions"],
                                     body.count("model") ? body["model"] : "",
                                     body.count("tone")  ? body["tone"]  : "technical");
        json_ok(res, "{\"id\":\"" + id + "\",\"ok\":true}");
    });

    svr.Post("/api/personas/:id/activate", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        bool ok = app.activate_persona(req.path_params.at("id"));
        json_ok(res, ok ? "{\"ok\":true}" : "{\"ok\":false,\"error\":\"not found\"}");
    });

    svr.Delete("/api/personas/:id", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        bool ok = app.delete_persona(req.path_params.at("id"));
        json_ok(res, ok ? "{\"ok\":true}" : "{\"ok\":false,\"error\":\"not found\"}");
    });

    svr.Get("/api/personas/active", [&](const httplib::Request&, httplib::Response& res) {
        WRITE_LOCK(app);
        auto p = app.active_persona();
        if (p.id.empty()) { json_ok(res, "null"); return; }
        json_ok(res, "{\"id\":\"" + p.id + "\",\"name\":\"" + escape_json(p.name) +
                     "\",\"instructions\":\"" + escape_json(p.instructions) +
                     "\",\"model\":\"" + escape_json(p.model) + "\"}");
    });

    // ══════════════════════════════════════════════════════════════════════════
    // RULES (Zo-inspired)
    // ══════════════════════════════════════════════════════════════════════════

    svr.Get("/api/rules", [&](const httplib::Request&, httplib::Response& res) {
        WRITE_LOCK(app);
        std::string j = "[";
        for (const auto& r : app.rules()) {
            if (j.size() > 1) j += ",";
            j += "{\"id\":\"" + r.id + "\",\"title\":\"" + escape_json(r.title) +
                 "\",\"condition\":\"" + escape_json(r.condition) +
                 "\",\"instruction\":\"" + escape_json(r.instruction) +
                 "\",\"enabled\":" + (r.enabled ? "true" : "false") +
                 ",\"created_at\":" + std::to_string(r.created_at) + "}";
        }
        j += "]";
        json_ok(res, j);
    });

    svr.Post("/api/rules", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        auto body = parse_json(req.body);
        if (!body.count("title") || !body.count("instruction")) {
            res.status = 400;
            json_ok(res, "{\"error\":\"title and instruction required\"}"); return;
        }
        auto id = app.create_rule(body["title"],
                                  body.count("condition") ? body["condition"] : "always",
                                  body["instruction"]);
        json_ok(res, "{\"id\":\"" + id + "\",\"ok\":true}");
    });

    svr.Post("/api/rules/:id/toggle", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        auto body = parse_json(req.body);
        bool enabled = !body.count("enabled") || body["enabled"] == "true";
        bool ok = app.toggle_rule(req.path_params.at("id"), enabled);
        json_ok(res, ok ? "{\"ok\":true}" : "{\"ok\":false,\"error\":\"not found\"}");
    });

    svr.Delete("/api/rules/:id", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        bool ok = app.delete_rule(req.path_params.at("id"));
        json_ok(res, ok ? "{\"ok\":true}" : "{\"ok\":false,\"error\":\"not found\"}");
    });

    svr.Get("/api/rules/prompt", [&](const httplib::Request&, httplib::Response& res) {
        WRITE_LOCK(app);
        auto prompt = app.active_rules_prompt();
        json_ok(res, "{\"prompt\":\"" + escape_json(prompt) + "\"}");
    });

    // ══════════════════════════════════════════════════════════════════════════
    // DATASETS (Zo-inspired)
    // ══════════════════════════════════════════════════════════════════════════

    svr.Get("/api/datasets", [&](const httplib::Request&, httplib::Response& res) {
        WRITE_LOCK(app);
        std::string j = "[";
        for (const auto& d : app.datasets()) {
            if (j.size() > 1) j += ",";
            j += "{\"id\":\"" + d.id + "\",\"name\":\"" + escape_json(d.name) +
                 "\",\"format\":\"" + d.format +
                 "\",\"row_count\":" + std::to_string(d.row_count) +
                 ",\"col_count\":" + std::to_string(d.col_count) +
                 ",\"created_at\":" + std::to_string(d.created_at) +
                 ",\"last_query\":\"" + escape_json(d.last_query) + "\"}";
        }
        j += "]";
        json_ok(res, j);
    });

    svr.Post("/api/datasets", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        auto body = parse_json(req.body);
        if (!body.count("name") || !body.count("format")) {
            res.status = 400;
            json_ok(res, "{\"error\":\"name and format required\"}"); return;
        }
        auto id = app.create_dataset(body["name"], body["format"],
                                     body.count("content") ? body["content"] : "");
        json_ok(res, "{\"id\":\"" + id + "\",\"ok\":true}");
    });

    svr.Post("/api/datasets/:id/query", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        auto body = parse_json(req.body);
        std::string result;
        bool ok = app.query_dataset(req.path_params.at("id"),
                                    body.count("sql") ? body["sql"] : "",
                                    result);
        json_ok(res, ok ? result : "{\"error\":\"dataset not found\"}");
    });

    svr.Delete("/api/datasets/:id", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        bool ok = app.delete_dataset(req.path_params.at("id"));
        json_ok(res, ok ? "{\"ok\":true}" : "{\"ok\":false,\"error\":\"not found\"}");
    });

    // ══════════════════════════════════════════════════════════════════════════
    // SYSTEM MONITOR (Zo-inspired)
    // ══════════════════════════════════════════════════════════════════════════

    svr.Get("/api/system", [&](const httplib::Request&, httplib::Response& res) {
        READ_LOCK(app);
        auto s = app.system_stats();
        std::string j = "{";
        j += "\"cpu_pct\":"        + std::to_string((int)s.cpu_pct) + ",";
        j += "\"mem_used_mb\":"    + std::to_string(s.mem_used_mb) + ",";
        j += "\"mem_total_mb\":"   + std::to_string(s.mem_total_mb) + ",";
        j += "\"mem_pct\":"        + std::to_string(s.mem_total_mb > 0 ? (int)(100.0*s.mem_used_mb/s.mem_total_mb) : 0) + ",";
        j += "\"disk_used_mb\":"   + std::to_string(s.disk_used_mb) + ",";
        j += "\"disk_total_mb\":"  + std::to_string(s.disk_total_mb) + ",";
        j += "\"disk_pct\":"       + std::to_string(s.disk_total_mb > 0 ? (int)(100.0*s.disk_used_mb/s.disk_total_mb) : 0) + ",";
        j += "\"uptime_secs\":"    + std::to_string(s.uptime_secs) + ",";
        j += "\"sampled_at\":"     + std::to_string(s.sampled_at);
        j += "}";
        json_ok(res, j);
    });

    // ══════════════════════════════════════════════════════════════════════════
    // CHAT HISTORY (luo_os-inspired)
    // ══════════════════════════════════════════════════════════════════════════

    svr.Get("/api/chat", [&](const httplib::Request& req, httplib::Response& res) {
        READ_LOCK(app);
        std::size_t limit = 100;
        if (req.has_param("limit")) {
            try { limit = std::stoul(req.get_param_value("limit")); } catch (...) {}
        }
        std::string j = "[";
        for (const auto& m : app.chat_history(limit)) {
            if (j.size() > 1) j += ",";
            j += "{\"id\":\"" + m.id + "\",\"role\":\"" + m.role +
                 "\",\"content\":\"" + escape_json(m.content) +
                 "\",\"model\":\"" + escape_json(m.model) +
                 "\",\"created_at\":" + std::to_string(m.created_at) + "}";
        }
        j += "]";
        json_ok(res, j);
    });

    svr.Post("/api/chat", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        auto body = parse_json(req.body);
        if (!body.count("role") || !body.count("content")) {
            res.status = 400;
            json_ok(res, "{\"error\":\"role and content required\"}"); return;
        }
        auto id = app.add_chat_message(body["role"], body["content"],
                                       body.count("model") ? body["model"] : "");
        json_ok(res, "{\"id\":\"" + id + "\",\"ok\":true}");
    });

    svr.Post("/api/chat/clear", [&](const httplib::Request&, httplib::Response& res) {
        WRITE_LOCK(app);
        app.clear_chat_history();
        json_ok(res, "{\"ok\":true}");
    });

    // ══════════════════════════════════════════════════════════════════════════
    // MODELS (luo_os multi-model)
    // ══════════════════════════════════════════════════════════════════════════

    svr.Get("/api/models", [&](const httplib::Request&, httplib::Response& res) {
        READ_LOCK(app);
        std::string j = "[";
        for (const auto& m : app.available_models()) {
            if (j.size() > 1) j += ",";
            j += "{\"id\":\"" + m.id + "\",\"name\":\"" + escape_json(m.name) +
                 "\",\"provider\":\"" + m.provider +
                 "\",\"available\":" + (m.available ? "true" : "false") +
                 ",\"active\":" + (m.active ? "true" : "false") + "}";
        }
        j += "]";
        json_ok(res, j);
    });

    svr.Post("/api/models/:id/activate", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        bool ok = app.set_active_model(req.path_params.at("id"));
        json_ok(res, ok ? "{\"ok\":true}" : "{\"ok\":false,\"error\":\"not found\"}");
    });

    // ══════════════════════════════════════════════════════════════════════════
    // LUO_OS BRIDGE PROXY (luo_os features via Python)
    // ══════════════════════════════════════════════════════════════════════════

    svr.Post("/api/luo_os/chat", [&](const httplib::Request& req, httplib::Response& res) {
        WRITE_LOCK(app);
        auto body = parse_json(req.body);
        std::string msg = body.count("message") ? body["message"] : "";
        if (msg.empty()) { res.status = 400; json_ok(res, "{\"error\":\"message required\"}"); return; }

        // Store user message
        app.add_chat_message("user", msg);

        // Route to luo_os bridge
        std::string cmd = "python3 luo_os/bridge.py chat " + msg + " 2>/dev/null";
        FILE* pipe = popen(cmd.c_str(), "r");
        std::string out;
        if (pipe) { char buf[512]; while (fgets(buf, sizeof(buf), pipe)) out += buf; pclose(pipe); }

        // Store assistant response
        std::string response = out.empty() ? "luo_os bridge not available" : out;
        app.add_chat_message("assistant", response, "luo_os");
        json_ok(res, "{\"response\":\"" + escape_json(response) + "\",\"ok\":true}");
    });

    svr.Get("/api/luo_os/status", [&](const httplib::Request&, httplib::Response& res) {
        READ_LOCK(app);
        FILE* pipe = popen("python3 luo_os/bridge.py status 2>/dev/null", "r");
        std::string out;
        if (pipe) { char buf[512]; while (fgets(buf, sizeof(buf), pipe)) out += buf; pclose(pipe); }
        res.set_content(out.empty() ? "{\"error\":\"bridge unavailable\"}" : out, "application/json");
        set_cors(res);
    });

    svr.Get("/api/luo_os/skills", [&](const httplib::Request&, httplib::Response& res) {
        READ_LOCK(app);
        FILE* pipe = popen("python3 luo_os/bridge.py skills list 2>/dev/null", "r");
        std::string out;
        if (pipe) { char buf[512]; while (fgets(buf, sizeof(buf), pipe)) out += buf; pclose(pipe); }
        res.set_content(out.empty() ? "{\"error\":\"bridge unavailable\"}" : out, "application/json");
        set_cors(res);
    });

    svr.Get("/api/luo_os/memory", [&](const httplib::Request&, httplib::Response& res) {
        READ_LOCK(app);
        FILE* pipe = popen("python3 luo_os/bridge.py memory stats 2>/dev/null", "r");
        std::string out;
        if (pipe) { char buf[512]; while (fgets(buf, sizeof(buf), pipe)) out += buf; pclose(pipe); }
        res.set_content(out.empty() ? "{\"error\":\"bridge unavailable\"}" : out, "application/json");
        set_cors(res);
    });

    svr.Get("/api/luo_os/kairos", [&](const httplib::Request&, httplib::Response& res) {
        READ_LOCK(app);
        FILE* pipe = popen("python3 luo_os/bridge.py kairos status 2>/dev/null", "r");
        std::string out;
        if (pipe) { char buf[512]; while (fgets(buf, sizeof(buf), pipe)) out += buf; pclose(pipe); }
        res.set_content(out.empty() ? "{\"error\":\"bridge unavailable\"}" : out, "application/json");
        set_cors(res);
    });

    // ── CORS preflight ────────────────────────────────────────────────────────
    svr.Options(".*", [](const httplib::Request&, httplib::Response& res) {
        set_cors(res);
        res.status = 204;
    });

    // ── 404 ───────────────────────────────────────────────────────────────────
    svr.set_error_handler([](const httplib::Request& req, httplib::Response& res) {
        res.set_content("{\"error\":\"not found\",\"path\":\"" + req.path + "\"}",
                        "application/json");
    });

    // Write port file
    std::ofstream(app.data_root() / "server.port.txt") << port;

    // Start background tick engine (2 s interval)
    app.start_tick_engine(2000);

    // Blocking listen
    svr.listen("0.0.0.0", port);

    app.stop_tick_engine();
    return 0;
}

} // namespace luo_gate
