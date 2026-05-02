#define CPPHTTPLIB_NO_EXCEPTIONS
#include "luo_gate/server.hpp"
#include "luo_gate/ui.hpp"

// Use httplib for a real HTTP server
#ifdef _MSC_VER
#pragma warning(push, 0)
#endif
#include "../external/httplib.h"
#ifdef _MSC_VER
#pragma warning(pop)
#endif

#include <atomic>
#include <fstream>
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
std::string json_num(auto n)  { return std::to_string(n); }

// ─── Summary JSON ─────────────────────────────────────────────────────────────
std::string summary_json(const App& app) {
    const auto s = app.summary();
    std::ostringstream o;
    o << '{'
      << "\"users\":"    << s.user_count    << ','
      << "\"agents\":"   << s.agent_count   << ','
      << "\"tasks\":"    << s.task_count    << ','
      << "\"computers\":" << s.computer_count << ','
      << "\"files\":"    << s.file_count    << ','
      << "\"projects\":" << s.project_count << ','
      << "\"memory\":"   << s.memory_count  << ','
      << "\"knowledge\":" << s.knowledge_count << ','
      << "\"audit\":"    << s.audit_count   << ','
      << "\"active_user\":" << json_str(s.active_user) << ','
      << "\"platform\":"    << json_str(s.platform)    << ','
      << "\"session_stage\":" << json_str(s.session_stage) << ','
      << "\"local_only\":" << json_bool(s.local_only_mode)
      << '}';
    return o.str();
}

// ─── Tasks JSON ───────────────────────────────────────────────────────────────
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
          << "\"load\":"         << a.load
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

// ─── Parse query param ─────────────────────────────────────────────────────────
std::string get_param(const httplib::Params& params, const std::string& key,
                      const std::string& def = {}) {
    const auto it = params.find(key);
    return it != params.end() ? it->second : def;
}

// ─── CORS + JSON headers ──────────────────────────────────────────────────────
void set_cors(httplib::Response& res) {
    res.set_header("Access-Control-Allow-Origin", "*");
    res.set_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
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

} // anonymous namespace

// ─── Main server ─────────────────────────────────────────────────────────────
int run_server(App& app, int port) {
    // Always write a preview regardless
    {
        const auto preview = render_dashboard_html(app);
        std::ofstream(app.data_root() / "server.preview.html") << preview;
        std::ofstream(app.data_root() / "server.port.txt") << port;
    }

    httplib::Server svr;

    // ── Dashboard ────────────────────────────────────────────────────────────
    svr.Get("/", [&](const httplib::Request&, httplib::Response& res) {
        set_cors(res);
        res.set_content(render_dashboard_html(app), "text/html; charset=utf-8");
    });

    svr.Get("/status", [&](const httplib::Request&, httplib::Response& res) {
        set_cors(res);
        res.set_content(render_status_html(app), "text/html; charset=utf-8");
    });

    // ── API: summary ─────────────────────────────────────────────────────────
    svr.Get("/api/summary", [&](const httplib::Request&, httplib::Response& res) {
        json_ok(res, summary_json(app));
    });

    // ── API: tasks ────────────────────────────────────────────────────────────
    svr.Get("/api/tasks", [&](const httplib::Request& req, httplib::Response& res) {
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
            o << "{\"id\":" << json_str(t.id)
              << ",\"title\":" << json_str(t.title)
              << ",\"status\":" << json_str(t.status)
              << ",\"kind\":" << json_str(t.kind)
              << ",\"priority\":" << t.priority << '}';
        }
        o << ']';
        json_ok(res, o.str());
    });

    svr.Post("/api/tasks", [&](const httplib::Request& req, httplib::Response& res) {
        const auto title = get_param(req.params, "title");
        const auto desc  = get_param(req.params, "description");
        const auto kind  = get_param(req.params, "kind", "general");
        const auto pri_s = get_param(req.params, "priority", "5");
        if (title.empty()) { json_err(res, 400, "title required"); return; }
        const int priority = std::clamp(std::stoi(pri_s.empty() ? "5" : pri_s), 1, 10);
        if (app.create_task(title, desc, kind, priority)) {
            app.tick();
            json_ok(res, "{\"ok\":true}");
        } else {
            json_err(res, 400, "create_task failed");
        }
    });

    svr.Post("/api/tasks/:id/cancel", [&](const httplib::Request& req, httplib::Response& res) {
        const auto id = req.path_params.at("id");
        json_ok(res, app.cancel_task(id) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Post("/api/tasks/:id/tick", [&](const httplib::Request& req, httplib::Response& res) {
        (void)req;
        json_ok(res, app.tick() ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Post("/api/tasks/:id/priority", [&](const httplib::Request& req, httplib::Response& res) {
        const auto id  = req.path_params.at("id");
        const auto pri = get_param(req.params, "priority", "5");
        const bool ok  = app.set_task_priority(id, std::stoi(pri));
        json_ok(res, ok ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── API: agents ───────────────────────────────────────────────────────────
    svr.Get("/api/agents", [&](const httplib::Request&, httplib::Response& res) {
        json_ok(res, agents_json(app));
    });

    svr.Post("/api/agents/kill", [&](const httplib::Request&, httplib::Response& res) {
        json_ok(res, app.kill_all_agents() ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── API: memory ───────────────────────────────────────────────────────────
    svr.Post("/api/memory", [&](const httplib::Request& req, httplib::Response& res) {
        const auto kind    = get_param(req.params, "kind", "note");
        const auto content = get_param(req.params, "content");
        if (content.empty()) { json_err(res, 400, "content required"); return; }
        json_ok(res, app.add_memory(kind, content) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Post("/api/memory/summarize", [&](const httplib::Request&, httplib::Response& res) {
        json_ok(res, app.summarize_old_memories(50) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── API: files ────────────────────────────────────────────────────────────
    svr.Post("/api/files", [&](const httplib::Request& req, httplib::Response& res) {
        const auto name    = get_param(req.params, "name");
        const auto content = req.body;
        if (name.empty()) { json_err(res, 400, "name required"); return; }
        json_ok(res, app.upload_file(name, content) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Post("/api/files/:name/rollback", [&](const httplib::Request& req, httplib::Response& res) {
        const auto name    = req.path_params.at("name");
        const auto ver_s   = get_param(req.params, "version", "0");
        const std::size_t ver = static_cast<std::size_t>(std::stoul(ver_s));
        json_ok(res, app.rollback_file(name, ver) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── API: projects ─────────────────────────────────────────────────────────
    svr.Post("/api/projects/:id/run", [&](const httplib::Request& req, httplib::Response& res) {
        const auto id = req.path_params.at("id");
        json_ok(res, app.run_project(id) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── API: session ──────────────────────────────────────────────────────────
    svr.Post("/api/session/pause", [&](const httplib::Request&, httplib::Response& res) {
        json_ok(res, app.pause_session() ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    svr.Post("/api/session/resume", [&](const httplib::Request&, httplib::Response& res) {
        json_ok(res, app.resume_session() ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── API: approvals ────────────────────────────────────────────────────────
    svr.Get("/api/approvals", [&](const httplib::Request&, httplib::Response& res) {
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
        const auto action = req.path_params.at("action");
        json_ok(res, app.approve_action(action) ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── API: search ───────────────────────────────────────────────────────────
    svr.Get("/api/search", [&](const httplib::Request& req, httplib::Response& res) {
        const auto query = get_param(req.params, "q");
        if (query.empty()) { json_err(res, 400, "q required"); return; }
        json_ok(res, search_json(app, query));
    });

    // ── API: save ─────────────────────────────────────────────────────────────
    svr.Post("/api/save", [&](const httplib::Request&, httplib::Response& res) {
        json_ok(res, app.save() ? "{\"ok\":true}" : "{\"ok\":false}");
    });

    // ── SSE: live events (P5) ─────────────────────────────────────────────────
    svr.Get("/api/events", [&](const httplib::Request&, httplib::Response& res) {
        set_cors(res);
        res.set_header("Content-Type", "text/event-stream");
        res.set_header("Cache-Control", "no-cache");
        res.set_header("X-Accel-Buffering", "no");

        // Emit a snapshot immediately, then the connection stays open via chunked
        std::string data = "data: " + summary_json(app) + "\n\n";
        res.set_content(data, "text/event-stream");
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

    // Write port file so external tools can find the server
    std::ofstream(app.data_root() / "server.port.txt") << port;

    // Start background tick engine (2s interval)
    app.start_tick_engine(2000);

    // Start listening (blocking)
    svr.listen("0.0.0.0", port);

    app.stop_tick_engine();
    return 0;
}

} // namespace luo_gate
