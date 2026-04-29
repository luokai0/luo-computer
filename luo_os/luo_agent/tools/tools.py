#!/usr/bin/env python3
"""
Luo OS — Tool System
Comprehensive tools for AI agent: file ops, shell, web, docker, code analysis, etc.
"""
import os, subprocess, json, shutil, urllib.request, urllib.parse, re, hashlib, time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

TOOLS = {}

def tool(name: str, desc: str, perm: bool = False):
    """Decorator to register a tool."""
    def dec(fn):
        TOOLS[name] = {"fn": fn, "description": desc, "requires_permission": perm}
        return fn
    return dec

# ═══════════════════════════════════════════════════════════════════
# FILE OPERATIONS
# ═══════════════════════════════════════════════════════════════════

@tool("read_file", "Read a file's contents")
def read_file(path: str, limit: int = 2000) -> str:
    """Read file contents with optional line limit."""
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"[ERROR] Not found: {path}"
        if p.stat().st_size > 10_000_000:
            return f"[ERROR] File too large: {p.stat().st_size} bytes"
        content = p.read_text(errors="replace")
        if len(content) > limit:
            return content[:limit] + f"\n... (truncated, {len(content)} total chars)"
        return content
    except Exception as e:
        return f"[ERROR] {e}"

@tool("write_file", "Write content to a file", perm=True)
def write_file(path: str, content: str) -> str:
    """Write content to file, creating directories if needed."""
    try:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"✓ Written {len(content)} chars to {path}"
    except Exception as e:
        return f"[ERROR] {e}"

@tool("append_file", "Append content to a file", perm=True)
def append_file(path: str, content: str) -> str:
    """Append content to existing file."""
    try:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a") as f:
            f.write(content)
        return f"✓ Appended {len(content)} chars to {path}"
    except Exception as e:
        return f"[ERROR] {e}"

@tool("edit_file", "Edit a file with search/replace", perm=True)
def edit_file(path: str, old: str, new: str, replace_all: bool = False) -> str:
    """Edit file by replacing old text with new text."""
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"[ERROR] Not found: {path}"
        content = p.read_text()
        if old not in content:
            return f"[ERROR] Pattern not found in file"
        count = content.count(old) if replace_all else 1
        new_content = content.replace(old, new, -1 if replace_all else 1)
        p.write_text(new_content)
        return f"✓ Replaced {count} occurrence(s) in {path}"
    except Exception as e:
        return f"[ERROR] {e}"

@tool("list_dir", "List directory contents")
def list_dir(path: str = ".", show_hidden: bool = False) -> str:
    """List directory contents with file types and sizes."""
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"[ERROR] Not found: {path}"
        if not p.is_dir():
            return f"[ERROR] Not a directory: {path}"
        items = []
        for i in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if not show_hidden and i.name.startswith('.'):
                continue
            if i.is_dir():
                items.append(f"📁 {i.name}/")
            else:
                size = i.stat().st_size
                size_str = f"{size:,}B" if size < 1024 else f"{size//1024:,}KB"
                items.append(f"📄 {i.name} ({size_str})")
        return "\n".join(items) or "(empty directory)"
    except Exception as e:
        return f"[ERROR] {e}"

@tool("delete_file", "Delete a file", perm=True)
def delete_file(path: str) -> str:
    """Delete a file or directory."""
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"[ERROR] Not found: {path}"
        if p.is_dir():
            shutil.rmtree(p)
            return f"✓ Deleted directory: {path}"
        else:
            p.unlink()
            return f"✓ Deleted file: {path}"
    except Exception as e:
        return f"[ERROR] {e}"

@tool("copy_file", "Copy a file", perm=True)
def copy_file(src: str, dst: str) -> str:
    """Copy file from src to dst."""
    try:
        s, d = Path(src).expanduser(), Path(dst).expanduser()
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)
        return f"✓ Copied {src} → {dst}"
    except Exception as e:
        return f"[ERROR] {e}"

@tool("move_file", "Move/rename a file", perm=True)
def move_file(src: str, dst: str) -> str:
    """Move file from src to dst."""
    try:
        s, d = Path(src).expanduser(), Path(dst).expanduser()
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(s, d)
        return f"✓ Moved {src} → {dst}"
    except Exception as e:
        return f"[ERROR] {e}"

@tool("file_exists", "Check if file exists")
def file_exists(path: str) -> str:
    """Check if file or directory exists."""
    p = Path(path).expanduser()
    if p.exists():
        return f"✓ EXISTS: {path} ({'directory' if p.is_dir() else f'file, {p.stat().st_size} bytes'})"
    return f"✗ NOT FOUND: {path}"

@tool("find_files", "Find files matching pattern")
def find_files(pattern: str, directory: str = ".", max_results: int = 50) -> str:
    """Find files matching a glob pattern."""
    try:
        p = Path(directory).expanduser()
        matches = list(p.glob(pattern))[:max_results]
        if not matches:
            return f"No files matching: {pattern}"
        return "\n".join(str(m.relative_to(p)) for m in matches)
    except Exception as e:
        return f"[ERROR] {e}"

@tool("grep_file", "Search for pattern in file")
def grep_file(path: str, pattern: str, ignore_case: bool = True) -> str:
    """Search for regex pattern in file."""
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"[ERROR] Not found: {path}"
        content = p.read_text(errors="replace")
        flags = re.IGNORECASE if ignore_case else 0
        matches = []
        for i, line in enumerate(content.split('\n'), 1):
            if re.search(pattern, line, flags):
                matches.append(f"{i}: {line[:100]}")
                if len(matches) >= 20:
                    matches.append("... (truncated)")
                    break
        return "\n".join(matches) or f"No matches for: {pattern}"
    except Exception as e:
        return f"[ERROR] {e}"

# ═══════════════════════════════════════════════════════════════════
# SHELL & EXECUTION
# ═══════════════════════════════════════════════════════════════════

@tool("bash", "Run a shell command", perm=True)
def bash(command: str, timeout: int = 30, cwd: str = None) -> str:
    """Execute a shell command."""
    try:
        r = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd
        )
        parts = []
        if r.stdout.strip():
            parts.append(f"STDOUT:\n{r.stdout.strip()[:2000]}")
        if r.stderr.strip():
            parts.append(f"STDERR:\n{r.stderr.strip()[:1000]}")
        if r.returncode != 0:
            parts.append(f"EXIT CODE: {r.returncode}")
        return "\n".join(parts) or "(no output)"
    except subprocess.TimeoutExpired:
        return f"[ERROR] Timeout after {timeout}s"
    except Exception as e:
        return f"[ERROR] {e}"

@tool("run_python", "Execute Python code", perm=True)
def run_python(code: str, timeout: int = 30) -> str:
    """Execute Python code and return output."""
    import tempfile
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            tmp = f.name
        r = subprocess.run(
            ["python3", tmp],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        parts = []
        if r.stdout.strip():
            parts.append(f"OUTPUT:\n{r.stdout.strip()[:2000]}")
        if r.stderr.strip():
            parts.append(f"ERRORS:\n{r.stderr.strip()[:1000]}")
        return "\n".join(parts) or "(no output)"
    except subprocess.TimeoutExpired:
        return f"[ERROR] Timeout after {timeout}s"
    except Exception as e:
        return f"[ERROR] {e}"
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)

@tool("run_script", "Run a script file", perm=True)
def run_script(path: str, args: str = "", timeout: int = 60) -> str:
    """Run a script file (Python, Bash, etc)."""
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"[ERROR] Not found: {path}"
        suffix = p.suffix.lower()
        if suffix == '.py':
            cmd = f"python3 {p} {args}"
        elif suffix in ['.sh', '.bash']:
            cmd = f"bash {p} {args}"
        else:
            cmd = f"{p} {args}"
        return bash(cmd, timeout=timeout)
    except Exception as e:
        return f"[ERROR] {e}"

# ═══════════════════════════════════════════════════════════════════
# WEB & NETWORK
# ═══════════════════════════════════════════════════════════════════

@tool("web_search", "Search the web via DuckDuckGo")
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web and return results."""
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")
        clean = lambda s: re.sub(r"<[^>]+>", "", s).strip()
        titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)[:max_results]
        snips = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)[:max_results]
        results = [f"{i+1}. {clean(t)}\n   {clean(s)}" for i, (t, s) in enumerate(zip(titles, snips))]
        return "\n\n".join(results) or "No results."
    except Exception as e:
        return f"[ERROR] {e}"

@tool("web_fetch", "Fetch content from URL")
def web_fetch(url: str, timeout: int = 30) -> str:
    """Fetch content from a URL."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            content = r.read().decode("utf-8", errors="replace")
            # Remove HTML tags for readability
            text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:3000] if len(text) > 3000 else text
    except Exception as e:
        return f"[ERROR] {e}"

@tool("http_request", "Make HTTP request", perm=True)
def http_request(url: str, method: str = "GET", headers: dict = None, data: str = None, timeout: int = 30) -> str:
    """Make HTTP request with custom method and headers."""
    try:
        headers = headers or {"User-Agent": "LuoOS-Agent/1.0"}
        req = urllib.request.Request(url, headers=headers, method=method)
        if data:
            req.data = data.encode() if isinstance(data, str) else data
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return f"Status: {r.status}\n{r.read().decode('utf-8', errors='replace')[:2000]}"
    except Exception as e:
        return f"[ERROR] {e}"

# ═══════════════════════════════════════════════════════════════════
# SYSTEM & INFO
# ═══════════════════════════════════════════════════════════════════

@tool("system_info", "Get system information")
def system_info() -> str:
    """Get comprehensive system information."""
    try:
        uname = subprocess.run(["uname", "-a"], capture_output=True, text=True).stdout.strip()
        cpu = subprocess.run(["nproc"], capture_output=True, text=True).stdout.strip()
        mem = subprocess.run(["free", "-h"], capture_output=True, text=True).stdout.strip()
        disk = subprocess.run(["df", "-h", "/"], capture_output=True, text=True).stdout.strip()
        return f"System: {uname}\nCPU cores: {cpu}\n\nMemory:\n{mem}\n\nDisk:\n{disk}"
    except Exception as e:
        return f"[ERROR] {e}"

@tool("process_list", "List running processes")
def process_list(filter_name: str = None) -> str:
    """List running processes, optionally filtered by name."""
    try:
        cmd = ["ps", "aux"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        lines = r.stdout.strip().split('\n')
        if filter_name:
            lines = [l for l in lines if filter_name.lower() in l.lower()]
        return '\n'.join(lines[:30]) or "No processes found"
    except Exception as e:
        return f"[ERROR] {e}"

@tool("kill_process", "Kill a process by PID", perm=True)
def kill_process(pid: int, signal: str = "TERM") -> str:
    """Kill a process by PID."""
    try:
        os.kill(pid, getattr(signal, signal, 15))
        return f"✓ Sent {signal} to PID {pid}"
    except Exception as e:
        return f"[ERROR] {e}"

@tool("get_datetime", "Get current date and time")
def get_datetime(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Get current date/time in specified format."""
    return datetime.now().strftime(format)

@tool("env_var", "Get environment variable")
def env_var(name: str) -> str:
    """Get environment variable value."""
    return os.environ.get(name, f"[NOT SET] {name}")

@tool("set_env_var", "Set environment variable", perm=True)
def set_env_var(name: str, value: str) -> str:
    """Set environment variable for current session."""
    os.environ[name] = value
    return f"✓ Set {name}={value}"

# ═══════════════════════════════════════════════════════════════════
# CODE ANALYSIS
# ═══════════════════════════════════════════════════════════════════

@tool("analyze_code", "Analyze code file for structure")
def analyze_code(path: str) -> str:
    """Analyze code file for functions, classes, imports."""
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"[ERROR] Not found: {path}"
        content = p.read_text(errors="replace")
        lines = content.count('\n') + 1
        chars = len(content)

        results = [f"📊 {path}: {lines} lines, {chars:,} chars"]

        # Python analysis
        if p.suffix == '.py':
            imports = re.findall(r'^(?:import|from)\s+(\S+)', content, re.MULTILINE)
            functions = re.findall(r'^def\s+(\w+)\s*\(', content, re.MULTILINE)
            classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
            results.append(f"\n📦 Imports ({len(imports)}): {', '.join(imports[:10])}")
            results.append(f"\n🔧 Functions ({len(functions)}): {', '.join(functions[:10])}")
            results.append(f"\n🏗️ Classes ({len(classes)}): {', '.join(classes[:10])}")

        # JavaScript analysis
        elif p.suffix in ['.js', '.ts']:
            functions = re.findall(r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()', content)
            imports = re.findall(r'(?:import|require)\s*\(?[\'"]([^\'"]+)[\'"]', content)
            results.append(f"\n📦 Imports: {', '.join(imports[:10])}")
            results.append(f"\n🔧 Functions: {', '.join([f[0] or f[1] for f in functions[:10]])}")

        return '\n'.join(results)
    except Exception as e:
        return f"[ERROR] {e}"

@tool("hash_file", "Calculate file hash")
def hash_file(path: str, algorithm: str = "sha256") -> str:
    """Calculate hash of file."""
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"[ERROR] Not found: {path}"
        h = hashlib.new(algorithm)
        with open(p, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return f"{algorithm}({path}) = {h.hexdigest()}"
    except Exception as e:
        return f"[ERROR] {e}"

# ═══════════════════════════════════════════════════════════════════
# DOCKER (if available)
# ═══════════════════════════════════════════════════════════════════

@tool("docker_ps", "List Docker containers")
def docker_ps(all: bool = False) -> str:
    """List Docker containers."""
    try:
        cmd = ["docker", "ps", "--format", "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Image}}"]
        if all:
            cmd.insert(2, "-a")
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.stdout.strip() or "No containers running"
    except Exception as e:
        return f"[ERROR] {e}"

@tool("docker_exec", "Execute command in Docker container", perm=True)
def docker_exec(container: str, command: str) -> str:
    """Execute command in Docker container."""
    try:
        r = subprocess.run(
            ["docker", "exec", container, "sh", "-c", command],
            capture_output=True, text=True, timeout=60
        )
        return r.stdout.strip() or r.stderr.strip() or "(no output)"
    except Exception as e:
        return f"[ERROR] {e}"

@tool("docker_logs", "Get Docker container logs")
def docker_logs(container: str, lines: int = 50) -> str:
    """Get logs from Docker container."""
    try:
        r = subprocess.run(
            ["docker", "logs", "--tail", str(lines), container],
            capture_output=True, text=True
        )
        return r.stdout.strip()[-2000:] or "(no logs)"
    except Exception as e:
        return f"[ERROR] {e}"

# ═══════════════════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════════════════

@tool("calculate", "Evaluate mathematical expression")
def calculate(expression: str) -> str:
    """Safely evaluate a mathematical expression."""
    try:
        # Only allow safe math operations
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in expression):
            return "[ERROR] Invalid characters in expression"
        result = eval(expression, {"__builtins__": {}}, {})
        return f"= {result}"
    except Exception as e:
        return f"[ERROR] {e}"

@tool("json_format", "Format JSON string")
def json_format(text: str, indent: int = 2) -> str:
    """Format/pretty-print JSON."""
    try:
        data = json.loads(text)
        return json.dumps(data, indent=indent, ensure_ascii=False)
    except Exception as e:
        return f"[ERROR] {e}"

@tool("base64_encode", "Encode string to base64")
def base64_encode(text: str) -> str:
    """Encode string to base64."""
    import base64
    return base64.b64encode(text.encode()).decode()

@tool("base64_decode", "Decode base64 string")
def base64_decode(text: str) -> str:
    """Decode base64 string."""
    import base64
    return base64.b64decode(text).decode()

@tool("uuid_gen", "Generate UUID")
def uuid_gen() -> str:
    """Generate a random UUID."""
    import uuid
    return str(uuid.uuid4())

# ═══════════════════════════════════════════════════════════════════
# TOOL EXECUTOR
# ═══════════════════════════════════════════════════════════════════

class ToolExecutor:
    """Execute tools with permission checking."""

    def __init__(self, auto_approve: bool = False):
        self.auto_approve = auto_approve
        self._permissions = {}  # Cache permissions

    def execute(self, name: str, args: dict, ask_permission: callable = None) -> str:
        """Execute a tool by name with given arguments."""
        if name not in TOOLS:
            return f"[ERROR] Unknown tool: {name}. Available: {', '.join(TOOLS.keys())}"

        tool_info = TOOLS[name]

        # Check permission
        if tool_info["requires_permission"] and not self.auto_approve:
            perm_key = f"{name}:{json.dumps(args, sort_keys=True)}"
            if perm_key in self._permissions:
                if not self._permissions[perm_key]:
                    return "[DENIED] (cached)"
            elif ask_permission:
                if not ask_permission(name, args):
                    self._permissions[perm_key] = False
                    return "[DENIED]"
            else:
                return f"[SKIPPED] {name} requires permission"

        # Execute tool
        try:
            result = tool_info["fn"](**args)
            return result
        except TypeError as e:
            return f"[ERROR] Invalid arguments for {name}: {e}"
        except Exception as e:
            return f"[ERROR] {e}"

    def list_tools(self, category: str = None) -> str:
        """List available tools, optionally filtered by category."""
        lines = ["Available tools:"]
        for name, info in TOOLS.items():
            perm = " [perm]" if info["requires_permission"] else ""
            lines.append(f"  {name}{perm} — {info['description']}")
        return "\n".join(lines)

    def get_tool_info(self, name: str) -> dict:
        """Get info about a specific tool."""
        return TOOLS.get(name, None)


# Export for convenience
__all__ = ["TOOLS", "ToolExecutor", "tool"]
