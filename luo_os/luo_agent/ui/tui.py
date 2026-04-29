#!/usr/bin/env python3
"""
Luo OS — Textual Terminal UI
Rich, animated terminal interface powered by Textual.
Falls back to basic terminal if Textual not available.
"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
    from textual.widgets import Header, Footer, Input, RichLog, Static, Button, Label, Select
    from textual.binding import Binding
    from textual import events
    TEXTUAL = True
except ImportError:
    TEXTUAL = False

from datetime import datetime

if TEXTUAL:
    class LuoAgentTUI(App):
        """Luo Agent — Rich Terminal UI powered by Textual"""

        CSS = """
        Screen { background: #0a0a1a; }

        #header-bar {
            height: 3;
            background: #7c3aed;
            color: white;
            content-align: center middle;
            text-style: bold;
        }

        #chat-log {
            border: solid #00d4ff;
            height: 1fr;
            margin: 1 1 0 1;
            scrollbar-color: #7c3aed;
        }

        #status-bar {
            height: 1;
            background: #0f0f2a;
            color: #64748b;
            margin: 0 1;
        }

        #input-row {
            height: 3;
            margin: 0 1 1 1;
        }

        #msg-input {
            border: solid #7c3aed;
            background: #0f0f2a;
            color: #e2e8f0;
            width: 1fr;
        }

        #send-btn {
            background: #7c3aed;
            color: white;
            width: 10;
            border: none;
        }

        #model-select {
            width: 22;
            background: #0f0f2a;
            border: solid #00d4ff;
            color: #00d4ff;
        }

        #sidebar {
            width: 28;
            border: solid #1e1e3a;
            background: #0f0f2a;
            margin: 1 0 1 1;
            padding: 1;
        }

        .sidebar-title {
            color: #00d4ff;
            text-style: bold;
        }

        .sidebar-item {
            color: #64748b;
        }

        #main-area {
            width: 1fr;
        }
        """

        BINDINGS = [
            Binding("ctrl+c", "quit", "Quit"),
            Binding("ctrl+l", "clear_chat", "Clear"),
            Binding("ctrl+s", "save_session", "Save"),
            Binding("f1",     "show_memory",  "Memory"),
            Binding("f2",     "show_agents",  "Agents"),
        ]

        def __init__(self, config=None):
            super().__init__()
            self.config      = config
            self.model       = "tinyllama"
            self.conversation = []
            self.session_id  = datetime.now().strftime("session_%Y%m%d_%H%M%S")

        def compose(self) -> ComposeResult:
            yield Static(
                "⚡ Luo Agent — Luo OS v0.1  |  Free for Humans & AI Agents",
                id="header-bar"
            )
            with Horizontal():
                with Vertical(id="sidebar"):
                    yield Static("MODELS", classes="sidebar-title")
                    yield Select(
                        [("tinyllama","tinyllama"),("phi3:mini","phi3:mini"),
                         ("gemma2:2b","gemma2:2b"),("qwen2.5:1.5b","qwen2.5:1.5b"),
                         ("mistral","mistral")],
                        value="tinyllama", id="model-select"
                    )
                    yield Static("")
                    yield Static("COMMANDS", classes="sidebar-title")
                    for cmd in ["/memory","/dream","/status","/save","/clear","/exit"]:
                        yield Static(cmd, classes="sidebar-item")
                    yield Static("")
                    yield Static("SESSION", classes="sidebar-title")
                    yield Static(self.session_id[:18], classes="sidebar-item")

                with Vertical(id="main-area"):
                    yield RichLog(id="chat-log", highlight=True, markup=True, wrap=True)
                    yield Static("", id="status-bar")
                    with Horizontal(id="input-row"):
                        yield Input(placeholder="Type a message or /command...", id="msg-input")
                        yield Button("Send", id="send-btn", variant="primary")

            yield Footer()

        def on_mount(self):
            log = self.query_one("#chat-log", RichLog)
            log.write("[bold cyan]Luo Agent ready.[/] Type a message or /help")
            log.write(f"[dim]Model: {self.model} | Session: {self.session_id}[/]")
            log.write("")
            self.query_one("#msg-input").focus()

        def on_select_changed(self, event: Select.Changed):
            if event.select.id == "model-select":
                self.model = str(event.value)
                self.query_one("#status-bar").update(f"Model: {self.model}")

        def on_button_pressed(self, event: Button.Pressed):
            if event.button.id == "send-btn":
                self._send()

        def on_input_submitted(self, event: Input.Submitted):
            self._send()

        def _send(self):
            inp = self.query_one("#msg-input", Input)
            msg = inp.value.strip()
            if not msg: return
            inp.value = ""
            log = self.query_one("#chat-log", RichLog)

            if msg.startswith("/"):
                self._handle_cmd(msg, log); return

            log.write(f"[bold cyan]you ▸[/] {msg}")
            self.query_one("#status-bar").update("Luo is thinking...")

            import threading
            def _run():
                try:
                    import json, urllib.request
                    payload = json.dumps({
                        "model": self.model,
                        "messages": [
                            {"role":"system","content":"You are Luo, the AI core of Luo OS. Be concise."},
                            *self.conversation,
                            {"role":"user","content":msg}
                        ],
                        "stream": False,
                        "options": {"num_predict": 512}
                    }).encode()
                    req = urllib.request.Request(
                        "http://localhost:3000/api/chat", data=payload,
                        headers={"Content-Type":"application/json"}
                    )
                    with urllib.request.urlopen(req, timeout=120) as r:
                        result = json.loads(r.read())
                    resp = result.get("message",{}).get("content","").strip()
                    self.conversation.append({"role":"user","content":msg})
                    self.conversation.append({"role":"assistant","content":resp})
                    self.call_from_thread(log.write, f"[bold green]luo  ▸[/] {resp}")
                    self.call_from_thread(log.write, "")
                    self.call_from_thread(self.query_one("#status-bar").update, f"Model: {self.model}")
                except Exception as e:
                    self.call_from_thread(log.write, f"[bold red]error[/] {e}")
                    self.call_from_thread(self.query_one("#status-bar").update, "Error — is LUOKAI running?")
            threading.Thread(target=_run, daemon=True).start()

        def _handle_cmd(self, cmd: str, log):
            if cmd == "/clear" or cmd == "/c":
                log.clear(); self.conversation = []
                log.write("[dim]Cleared.[/]")
            elif cmd == "/exit" or cmd == "/quit":
                self.exit()
            elif cmd == "/memory":
                mem_file = Path("~/.luo_agent/MEMORY.md").expanduser()
                content  = mem_file.read_text() if mem_file.exists() else "(no memory yet)"
                log.write(f"[bold cyan]── Memory ──[/]\n{content}")
            elif cmd == "/status":
                log.write(f"[bold cyan]── Status ──[/]")
                log.write(f"Model    : {self.model}")
                log.write(f"Messages : {len(self.conversation)}")
                log.write(f"Session  : {self.session_id}")
            elif cmd == "/save":
                path = Path(f"~/.luo_agent/sessions/{self.session_id}.txt").expanduser()
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(str(self.conversation))
                log.write(f"[green]Saved: {self.session_id}[/]")
            elif cmd == "/dream":
                log.write("[yellow]autoDream: run python3 luo_agent.py and use /dream[/]")
            elif cmd.startswith("/model "):
                self.model = cmd.split(None,1)[1].strip()
                log.write(f"[green]Model → {self.model}[/]")
            else:
                log.write(f"[dim]Commands: /clear /exit /memory /status /save /model <n>[/]")

        def action_clear_chat(self):   self._handle_cmd("/clear", self.query_one("#chat-log", RichLog))
        def action_save_session(self): self._handle_cmd("/save",  self.query_one("#chat-log", RichLog))
        def action_show_memory(self):  self._handle_cmd("/memory",self.query_one("#chat-log", RichLog))
        def action_show_agents(self):
            log = self.query_one("#chat-log", RichLog)
            log.write("[bold cyan]── Agents ──[/]")
            try:
                import json, urllib.request
                with urllib.request.urlopen("http://localhost:8080/agents", timeout=3) as r:
                    data = json.loads(r.read())
                for a in data.get("agents",[]):
                    log.write(f"  {a['id']} — {a['name']} ({a['model']})")
            except Exception:
                log.write("[dim]Agent API offline. Run: python3 luo_init.py[/]")

    def run_tui(config=None):
        app = LuoAgentTUI(config=config)
        app.run()

else:
    def run_tui(config=None):
        print("Textual not installed. Run: pip install textual")
        print("Falling back to basic terminal...")
        from ui.terminal import LuoTerminal
        from core.config import LuoConfig
        LuoTerminal(config or LuoConfig()).run()

if __name__ == "__main__":
    run_tui()
