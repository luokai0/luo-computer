#!/usr/bin/env python3
"""
LuoOS Server — Main backend
Serves the full browser-based OS + LUOKAI AI API
Port 3000 (sandbox OS) + 7070 (LUOKAI API)

Enhanced with:
- Streaming responses (SSE)
- ReAct agent with planning and reflection
- Multi-model support
- Real skills library
"""
import sys, json, time, threading, subprocess, os, signal
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS

sys.path.insert(0, str(Path(__file__).parent))

# Load LuoOS config (set by start.py or setup_luoos.py)
_LUO_USER   = os.environ.get("LUO_USER_NAME", "User")
_LUO_MODEL  = os.environ.get("LUO_AI_MODEL",  "qwen2.5-1.5b")
_LUO_FEATS  = set(os.environ.get("LUO_FEATURES", "voice,coevo,neural,autolearn").split(","))

app     = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

# ── VS Code / code-server Configuration ─────────────────────────────
VSCODE_PORT      = 8080
VSCODE_PASSWORD  = os.environ.get("LUOOS_PASSWORD", "luoos2024")  # override: export LUOOS_PASSWORD=yourpass
VSCODE_WORKSPACE = Path.home() / "luo_workspace"
VSCODE_CONFIG    = Path.home() / ".config" / "code-server" / "config.yaml"
VSCODE_PID_FILE  = Path("/tmp/luo-code-server.pid")
VSCODE_LOG_FILE  = Path("/tmp/luo-code-server.log")
_vscode_proc     = None   # subprocess handle

# ── Configuration ───────────────────────────────────────────────────────
USE_REACT_AGENT = True  # Use enhanced ReAct agent
STREAMING_ENABLED = True  # Enable streaming responses

# ── Boot LUOKAI ──────────────────────────────────────────────────────
print("🚀 Booting LUOKAI Agent...")

agent = None
react_agent = None
AGENT_OK = False

# Try to load ReAct agent first (enhanced version)
if USE_REACT_AGENT:
    try:
        from luokai.core.react_agent import create_agent
        react_agent = create_agent(streaming=STREAMING_ENABLED)
        AGENT_OK = True
        print(f"✅ LUOKAI ReAct Agent ready (model: {react_agent.model})")
    except Exception as e:
        print(f"⚠️  ReAct agent error: {e}, falling back to basic agent")

# Fall back to basic agent if ReAct fails
if not AGENT_OK:
    try:
        from luokai.core.luokai_agent import LUOKAIAgent
        agent = LUOKAIAgent()
        AGENT_OK = True
        print("✅ LUOKAI Basic Agent ready")
    except Exception as e:
        print(f"⚠️  LUOKAI Agent error: {e}")
        AGENT_OK = False

# Use whichever agent is available
active_agent = react_agent or agent

# ── Routes ───────────────────────────────────────────────────────────
@app.route("/")
def index():
    ui = os.environ.get("LUO_UI", "classic")
    return send_from_directory(".", "index_3d.html" if ui == "3d" else "index.html")

@app.route("/3d")
def index_3d():
    return send_from_directory(".", "index_3d.html")

@app.route("/classic")
def index_classic():
    return send_from_directory(".", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)

@app.route("/api/chat", methods=["POST"])
def chat():
    """Standard chat endpoint (non-streaming)."""
    data = request.json or {}
    msg  = data.get("message","").strip()
    stream = data.get("stream", False)

    if not msg:
        return jsonify({"error": "empty"}), 400
    if not active_agent:
        return jsonify({"response": "LUOKAI offline — check requirements"}), 200

    # Handle streaming request
    if stream and STREAMING_ENABLED and react_agent:
        return Response(
            stream_with_context(generate_stream(msg)),
            mimetype='text/event-stream'
        )

    # Standard non-streaming response
    try:
        resp = active_agent.think(msg)
        return jsonify({"response": resp, "ok": True})
    except Exception as e:
        return jsonify({"response": f"Error: {e}", "ok": False})


@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    """Streaming chat endpoint using Server-Sent Events."""
    data = request.json or {}
    msg = data.get("message", "").strip()

    if not msg:
        return jsonify({"error": "empty"}), 400
    if not active_agent:
        return jsonify({"response": "LUOKAI offline"}), 200

    def generate():
        try:
            # Check if ReAct agent with streaming is available
            if react_agent and hasattr(react_agent, 'think_stream'):
                for token in react_agent.think_stream(msg):
                    yield f"data: {json.dumps({'token': token})}\n\n"
            else:
                # Fall back to regular think
                resp = active_agent.think(msg)
                yield f"data: {json.dumps({'token': resp})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


def generate_stream(msg):
    """Generator for streaming responses."""
    try:
        if react_agent and hasattr(react_agent, 'think_stream'):
            for token in react_agent.think_stream(msg):
                yield f"data: {json.dumps({'token': token})}\n\n"
        else:
            resp = active_agent.think(msg)
            yield f"data: {json.dumps({'token': resp})}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

@app.route("/api/status")
def status():
    """Get agent status."""
    if active_agent:
        return jsonify(active_agent.status())
    return jsonify({"ok": False, "error": "agent not loaded"})

@app.route("/api/models", methods=["GET"])
def list_models():
    """List available models."""
    if react_agent and hasattr(react_agent, '_available_models'):
        return jsonify({"models": react_agent._available_models, "current": react_agent.model})
    return jsonify({"models": [], "current": "unknown"})

@app.route("/api/models/switch", methods=["POST"])
def switch_model():
    """Switch to a different model."""
    data = request.json or {}
    model = data.get("model")
    if not model:
        return jsonify({"error": "model parameter required"}), 400
    if react_agent and hasattr(react_agent, 'model'):
        react_agent.model = model
        return jsonify({"ok": True, "model": model})
    return jsonify({"error": "cannot switch model"}), 400

@app.route("/api/execute", methods=["POST"])
def execute():
    data = request.json or {}
    code = data.get("code","")
    lang = data.get("language","python")
    if not active_agent:
        return jsonify({"output": "LUOKAI offline"}), 200
    if lang == "python":
        out = active_agent.run_python(code)
    else:
        out = active_agent.execute_command(code)
    return jsonify({"output": out, "ok": True})

@app.route("/api/search", methods=["POST"])
def search():
    q = (request.json or {}).get("query","")
    if active_agent:
        return jsonify({"results": active_agent.web_search(q)})
    return jsonify({"results": "Agent offline"})

@app.route("/api/voice/start", methods=["POST"])
def voice_start():
    if not active_agent: return jsonify({"ok": False})
    try:
        active_agent.start_voice()
        return jsonify({"ok": True, "msg": "Voice started - say 'Luo' to wake"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/voice/stop", methods=["POST"])
def voice_stop():
    if active_agent: active_agent.stop_voice()
    return jsonify({"ok": True})

@app.route("/api/voice/status")
def voice_status():
    if active_agent and hasattr(active_agent, '_voice') and active_agent._voice:
        return jsonify(active_agent._voice.status())
    return jsonify({"running": False})

@app.route("/api/evolution/start", methods=["POST"])
def evo_start():
    if not active_agent: return jsonify({"ok": False})
    try:
        active_agent.start_evolution()
        return jsonify({"ok": True, "msg": "Co-evolution started"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/evolution/stats")
def evo_stats():
    if active_agent and hasattr(active_agent, '_coevo') and active_agent._coevo:
        return jsonify(active_agent._coevo.stats())
    return jsonify({"running": False})

@app.route("/api/memory", methods=["GET"])
def get_memory():
    """Get agent memory."""
    if active_agent and hasattr(active_agent, '_memory'):
        return jsonify({"memory": active_agent._memory, "count": len(active_agent._memory)})
    return jsonify({"memory": {}, "count": 0})

@app.route("/api/memory/recall", methods=["POST"])
def recall_memory():
    """Semantic search through agent memory."""
    data = request.json or {}
    query = data.get("query", "")
    n = data.get("n", 5)
    if active_agent and hasattr(active_agent, 'semantic_recall'):
        results = active_agent.semantic_recall(query, n)
        return jsonify({"results": results})
    return jsonify({"results": []})

@app.route("/api/skills", methods=["GET"])
def list_skills():
    """All categories with skill counts + overall stats."""
    try:
        from luokai.skills import get_library
        lib  = get_library()
        stat = lib.stats()
        return jsonify({"ok": True, **stat})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/skills/search", methods=["GET", "POST"])
def skills_search():
    """Search skills. GET ?q=query&limit=20&category=  or  POST {query, limit, category}"""
    try:
        from luokai.skills import get_library
        lib = get_library()
        if request.method == "POST":
            body     = request.json or {}
            q        = body.get("query", body.get("q", ""))
            limit    = int(body.get("limit", 20))
            category = body.get("category", "")
        else:
            q        = request.args.get("q", "")
            limit    = int(request.args.get("limit", 20))
            category = request.args.get("category", "")
        results = lib.search(q, limit=limit, category=category)
        return jsonify({"results": results, "count": len(results), "query": q, "ok": True})
    except Exception as e:
        return jsonify({"results": [], "ok": False, "error": str(e)})

@app.route("/api/skills/categories", methods=["GET"])
def skills_categories():
    """List all skill categories."""
    try:
        from luokai.skills import get_library
        lib  = get_library()
        cats = lib.categories()
        return jsonify({"categories": cats, "count": len(cats), "ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/skills/category/<path:cat>", methods=["GET"])
def skills_by_category(cat):
    """Skills in a category. GET /api/skills/category/devops-and-cloud?limit=50"""
    try:
        from luokai.skills import get_library
        lib   = get_library()
        limit = int(request.args.get("limit", 50))
        skills = lib.list_category(cat, limit=limit)
        return jsonify({"skills": skills, "count": len(skills), "category": cat, "ok": True})
    except Exception as e:
        return jsonify({"skills": [], "ok": False, "error": str(e)})

@app.route("/api/skills/get/<path:slug>", methods=["GET"])
def skill_detail(slug):
    """Full skill detail by ID/slug."""
    try:
        from luokai.skills import get_library
        lib   = get_library()
        skill = lib.get(slug)
        if not skill:
            return jsonify({"ok": False, "error": f"Skill '{slug}' not found"}), 404
        return jsonify({"skill": skill, "ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/skills/stats", methods=["GET"])
def skills_stats_route():
    """Skills engine statistics."""
    try:
        from luokai.skills import get_library
        lib = get_library()
        return jsonify({"ok": True, **lib.stats()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/skills/random", methods=["GET"])
def skills_random():
    """Get random skills. GET ?n=5&category="""
    try:
        from luokai.skills import get_library
        lib      = get_library()
        n        = int(request.args.get("n", 5))
        category = request.args.get("category", "")
        skills   = lib.random_skills(n=n, category=category)
        return jsonify({"skills": skills, "ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/skills/<path:skill_name>", methods=["POST"])
def invoke_skill(skill_name):
    """Invoke a skill by name/ID — returns skill instructions for the agent."""
    try:
        from luokai.skills import get_library
        lib    = get_library()
        body   = request.json or {}
        ctx    = body.get("context", "")
        result = lib.invoke(skill_name, context=ctx)
        return jsonify({**result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/fs/read", methods=["POST"])
def fs_read():
    path = (request.json or {}).get("path","")
    try:
        content = Path(path).expanduser().read_text(errors="replace")[:50000]
        return jsonify({"ok": True, "content": content})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/fs/write", methods=["POST"])
def fs_write():
    data    = request.json or {}
    path    = data.get("path","")
    content = data.get("content","")
    try:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/fs/ls", methods=["POST"])
def fs_ls():
    path = (request.json or {}).get("path","~")
    try:
        p     = Path(path).expanduser()
        items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        result = [{"name":i.name,"type":"dir" if i.is_dir() else "file","size":i.stat().st_size if i.is_file() else 0} for i in items[:200]]
        return jsonify({"ok": True, "items": result, "path": str(p)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

# ── VS Code / code-server API ────────────────────────────────────────

def _vscode_is_running():
    """Check if code-server is listening on its port."""
    import socket
    try:
        with socket.create_connection(("127.0.0.1", VSCODE_PORT), timeout=1):
            return True
    except OSError:
        return False

def _ensure_vscode_config():
    """Write config.yaml if missing."""
    VSCODE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    VSCODE_WORKSPACE.mkdir(parents=True, exist_ok=True)
    if not VSCODE_CONFIG.exists():
        VSCODE_CONFIG.write_text(
            f"bind-addr: 127.0.0.1:{VSCODE_PORT}\n"
            f"auth: password\n"
            f"password: {VSCODE_PASSWORD}\n"
            f"cert: false\n"
        )

def _vscode_autostart():
    """Try to auto-start code-server if installed."""
    global _vscode_proc
    if _vscode_is_running():
        print("✅ code-server already running")
        return
    if not _find_code_server():
        print("⚠️  code-server not installed — VS Code app will show install prompt")
        return
    _ensure_vscode_config()
    try:
        global _vscode_log
        _vscode_log = open(VSCODE_LOG_FILE, "a")  # kept open for subprocess lifetime
        _vscode_proc = subprocess.Popen(
            ["code-server", "--config", str(VSCODE_CONFIG), str(VSCODE_WORKSPACE)],
            stdout=_vscode_log, stderr=_vscode_log, start_new_session=True
        )
        VSCODE_PID_FILE.write_text(str(_vscode_proc.pid))
        print(f"🖥️  code-server started (PID {_vscode_proc.pid}) on port {VSCODE_PORT}")
    except Exception as e:
        print(f"⚠️  code-server auto-start failed: {e}")

def _find_code_server():
    """Return path to code-server binary, or None."""
    import shutil
    return shutil.which("code-server")

@app.route("/api/vscode/status")
def vscode_status():
    running  = _vscode_is_running()
    installed = _find_code_server() is not None
    return jsonify({
        "ok":        True,
        "running":   running,
        "installed": installed,
        "port":      VSCODE_PORT,
        "url":       f"http://localhost:{VSCODE_PORT}",
        "workspace": str(VSCODE_WORKSPACE),
        "password":  VSCODE_PASSWORD,
    })

@app.route("/api/vscode/start", methods=["POST"])
def vscode_start():
    global _vscode_proc
    if _vscode_is_running():
        return jsonify({"ok": True, "running": True, "msg": "Already running",
                        "url": f"http://localhost:{VSCODE_PORT}"})
    if not _find_code_server():
        return jsonify({"ok": False, "running": False,
                        "msg": "code-server not installed. Run: bash vscode/install_code_server.sh"})
    _ensure_vscode_config()
    try:
        global _vscode_log
        _vscode_log = open(VSCODE_LOG_FILE, "a")  # kept open for subprocess lifetime
        _vscode_proc = subprocess.Popen(
            ["code-server", "--config", str(VSCODE_CONFIG), str(VSCODE_WORKSPACE)],
            stdout=_vscode_log, stderr=_vscode_log, start_new_session=True
        )
        VSCODE_PID_FILE.write_text(str(_vscode_proc.pid))
        # Wait up to 8 seconds for it to bind
        for _ in range(16):
            time.sleep(0.5)
            if _vscode_is_running():
                return jsonify({"ok": True, "running": True,
                                "msg": "code-server started",
                                "url": f"http://localhost:{VSCODE_PORT}",
                                "pid": _vscode_proc.pid})
        return jsonify({"ok": True, "running": False,
                        "msg": "Started but still initializing — try again in a moment",
                        "url": f"http://localhost:{VSCODE_PORT}"})
    except Exception as e:
        return jsonify({"ok": False, "running": False, "msg": str(e)})

@app.route("/api/vscode/stop", methods=["POST"])
def vscode_stop():
    global _vscode_proc
    stopped = False
    # Kill our tracked process
    if _vscode_proc:
        try:
            _vscode_proc.terminate()
            _vscode_proc.wait(timeout=5)
            stopped = True
        except Exception:
            try: _vscode_proc.kill()
            except Exception: pass
        _vscode_proc = None
    # Also kill by PID file
    if VSCODE_PID_FILE.exists():
        try:
            pid = int(VSCODE_PID_FILE.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            stopped = True
        except Exception: pass
        VSCODE_PID_FILE.unlink(missing_ok=True)
    return jsonify({"ok": True, "stopped": stopped,
                    "msg": "code-server stopped" if stopped else "Was not running"})

@app.route("/api/vscode/install", methods=["POST"])
def vscode_install():
    """Trigger install script in background."""
    script = Path(__file__).parent / "vscode" / "install_code_server.sh"
    if not script.exists():
        return jsonify({"ok": False, "msg": "Install script not found"})
    try:
        proc = subprocess.Popen(
            ["bash", str(script)],
            stdout=open("/tmp/code-server-install.log","w"),  # subprocess handles close
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        return jsonify({"ok": True, "msg": "Install started in background",
                        "pid": proc.pid,
                        "log": "/tmp/code-server-install.log"})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})

# ── Brain API ─────────────────────────────────────────────────────────

def _get_brain():
    a = active_agent
    if a and hasattr(a, "_brain") and a._brain:
        return a._brain
    return None

@app.route("/api/brain/status", methods=["GET"])
def brain_status():
    brain = _get_brain()
    if not brain:
        return jsonify({"ok": False, "error": "Brain not initialized"})
    return jsonify({"ok": True, **brain.status()})

@app.route("/api/brain/memory/store", methods=["POST"])
def brain_memory_store():
    body = request.json or {}
    content = body.get("content", "")
    if not content:
        return jsonify({"ok": False, "error": "content required"})
    brain = _get_brain()
    if not brain:
        return jsonify({"ok": False, "error": "brain offline"})
    brain.store(content, role=body.get("role","observation"),
                importance=float(body.get("importance",0.5)))
    return jsonify({"ok": True, "stored": content[:80]})

@app.route("/api/brain/memory/recall", methods=["GET", "POST"])
def brain_memory_recall():
    if request.method == "POST":
        body = request.json or {}
        query = body.get("query", "")
        limit = int(body.get("limit", 8))
    else:
        query = request.args.get("q", "")
        limit = int(request.args.get("limit", 8))
    brain = _get_brain()
    if not brain:
        return jsonify({"ok": False, "results": [], "error": "brain offline"})
    results = brain.recall(query=query, limit=limit)
    return jsonify({"ok": True, "results": results, "count": len(results), "query": query})

@app.route("/api/brain/memory/wake", methods=["GET"])
def brain_wake():
    brain = _get_brain()
    if not brain or not brain.memory:
        return jsonify({"ok": False, "context": "", "error": "brain/memory offline"})
    try:
        ctx = brain.memory.wake_up(max_tokens=1000)
        return jsonify({"ok": True, "context": ctx})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/brain/memory/dream", methods=["POST"])
def brain_dream():
    brain = _get_brain()
    if not brain or not brain.memory:
        return jsonify({"ok": False, "error": "brain/memory offline"})
    try:
        brain.memory.dream()
        return jsonify({"ok": True, "msg": "Dream consolidation triggered"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/brain/goals", methods=["GET"])
def brain_goals():
    brain = _get_brain()
    if not brain:
        return jsonify({"ok": False, "goals": [], "error": "brain offline"})
    return jsonify({"ok": True, "goals": brain.get_goals()})

@app.route("/api/brain/goals", methods=["POST"])
def brain_set_goal():
    body = request.json or {}
    desc = body.get("description", "")
    if not desc:
        return jsonify({"ok": False, "error": "description required"})
    brain = _get_brain()
    if not brain:
        return jsonify({"ok": False, "error": "brain offline"})
    brain.set_goal(desc, priority=int(body.get("priority", 5)))
    return jsonify({"ok": True, "set": desc})

@app.route("/api/brain/skills/learned", methods=["GET"])
def brain_learned_skills():
    brain = _get_brain()
    if not brain:
        return jsonify({"ok": False, "skills": [], "error": "brain offline"})
    return jsonify({"ok": True, "skills": brain.get_learned_skills()})

@app.route("/api/brain/fact", methods=["POST"])
def brain_learn_fact():
    body = request.json or {}
    key, value = body.get("key",""), body.get("value","")
    if not key or not value:
        return jsonify({"ok": False, "error": "key and value required"})
    brain = _get_brain()
    if not brain:
        return jsonify({"ok": False, "error": "brain offline"})
    brain.learn_fact(key, value, float(body.get("confidence", 0.9)))
    return jsonify({"ok": True, "learned": {key: value}})

@app.route("/api/brain/coevo/stats", methods=["GET"])
def brain_coevo_stats():
    brain = _get_brain()
    if not brain or not brain.coevo:
        return jsonify({"ok": False, "error": "coevo offline"})
    try:
        return jsonify({"ok": True, **brain.coevo.stats()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/config/key", methods=["POST"])
def config_save_key():
    """Save an API key to ~/.luo_os/config.json."""
    body = request.json or {}
    key, value = body.get("key",""), body.get("value","")
    if not key or not value:
        return jsonify({"ok": False, "error": "key and value required"})
    try:
        from setup_luoos import CONFIG_PATH, load_config
        import json as _json
        cfg = load_config()
        if "api_keys" not in cfg:
            cfg["api_keys"] = {}
        cfg["api_keys"][key] = value
        CONFIG_PATH.write_text(_json.dumps(cfg, indent=2))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/model/status", methods=["GET"])
def model_status():
    """Get local model engine status."""
    try:
        from luokai.core.model_engine import get_engine
        return jsonify({"ok": True, **get_engine().status()})
    except Exception as e:
        return jsonify({"ok": False, "ready": False, "loading": False, "error": str(e)})

@app.route("/api/model/list", methods=["GET"])
def model_list():
    """List available models."""
    try:
        from luokai.core.model_engine import get_engine
        return jsonify({"ok": True, "models": get_engine().list_available_models()})
    except Exception as e:
        return jsonify({"ok": False, "models": [], "error": str(e)})



@app.route("/api/browser/fetch", methods=["POST"])
def browser_fetch():
    """Server-side proxy — bypasses X-Frame-Options and CORS restrictions."""
    body = request.json or {}
    url  = body.get("url", "").strip()
    if not url:
        return jsonify({"ok": False, "error": "No URL"})
    if not url.startswith("http"):
        url = "https://" + url
    try:
        import urllib.request as ur, re
        from urllib.parse import urljoin, quote
        req = ur.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        with ur.urlopen(req, timeout=12) as resp:
            raw       = resp.read(2 * 1024 * 1024)
            ctype     = resp.headers.get("Content-Type", "text/html")
            final_url = resp.url
        charset = "utf-8"
        for p in ctype.split(";"):
            p = p.strip()
            if p.lower().startswith("charset="):
                charset = p.split("=", 1)[1].strip()
        html = raw.decode(charset, errors="replace")

        # Rewrite relative URLs to absolute using a simple approach
        def abs_url(val):
            if not val or val.startswith(("http", "data:", "mailto:", "javascript:", "#", "blob:")):
                return val
            return urljoin(final_url, val)

        # Replace src="..." href="..." action="..."
        def repl_attr(m):
            attr = m.group(1)
            q    = m.group(2)
            val  = m.group(3)
            return attr + "=" + q + abs_url(val) + q

        import re as _re
        # Use \x22 for " and \x27 for ' to avoid quote issues
        html = _re.sub(
            r'(src|href|action)=(\x22)([^\x22]*)(\x22)',
            lambda m: m.group(1)+"="+m.group(2)+abs_url(m.group(3))+m.group(4),
            html, flags=_re.IGNORECASE
        )
        html = _re.sub(
            r"(src|href|action)=(\x27)([^\x27]*)(\x27)",
            lambda m: m.group(1)+"="+m.group(2)+abs_url(m.group(3))+m.group(4),
            html, flags=_re.IGNORECASE
        )

        # Inject base tag
        html = _re.sub(r"(<head[^>]*>)", "<base href=\"" + final_url + "\">\\1", html, count=1, flags=_re.IGNORECASE)

        # Extract title
        tm    = _re.search(r"<title[^>]*>(.*?)</title>", html, _re.IGNORECASE | _re.DOTALL)
        title = tm.group(1).strip() if tm else final_url

        return jsonify({"ok": True, "html": html, "url": final_url, "title": title})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "url": url})


@app.route("/api/browser/search", methods=["POST"])
def browser_search():
    """Return DuckDuckGo search URL for client to proxy-fetch."""
    body  = request.json or {}
    query = body.get("query", "").strip()
    if not query:
        return jsonify({"ok": False, "error": "No query"})
    import urllib.parse
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    return jsonify({"ok": True, "redirect": url, "search_url": url})



@app.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"]  = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r

def _run_server():
    """Start the LuoOS server. Called by start.py or directly."""
    import atexit
    port = int(os.environ.get("LUO_PORT", 3000))

    def _shutdown():
        brain = _get_brain()
        if brain:
            brain.shutdown()
    atexit.register(_shutdown)

    # Boot LUOKAI model engine in background (uses model chosen during setup)
    try:
        from luokai.core.model_engine import boot_engine, set_active_model
        if _LUO_MODEL != "none":
            set_active_model(_LUO_MODEL)
        boot_engine()
    except Exception:
        pass

    threading.Thread(target=_vscode_autostart, daemon=True).start()
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True, use_reloader=False)

if __name__ == "__main__":
    _run_server()
