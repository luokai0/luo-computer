#!/usr/bin/env python3
"""
Luo OS — Unified CLI Entry Point
Command-line interface for LUOKAI AI agent.

Usage:
    python3 luo_cli.py chat          # Interactive chat
    python3 luo_cli.py voice        # Start voice interface
    python3 luo_cli.py evolution    # Start co-evolution
    python3 luo_cli.py tools         # List available tools
    python3 luo_cli.py status        # Show system status
    python3 luo_cli.py server        # Start web server
    python3 luo_cli.py tui           # Rich terminal UI
"""
import sys
import os
import argparse
import json
import threading
import time
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

BANNER = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ██╗     ██╗   ██╗ ██████╗  ██████╗ ███████╗                     ║
║   ██║     ██║   ██║██╔═══██╗██╔════╝ ██╔════╝                     ║
║   ██║     ██║   ██║██║   ██║██║      █████╗                        ║
║   ██║     ██║   ██║██║   ██║██║      ██╔══╝                        ║
║   ███████╗╚██████╔╝╚██████╔╝╚██████╗ ███████╗                     ║
║   ╚══════╝ ╚═════╝  ╚═════╝  ╚═════╝ ╚══════╝                     ║
║                                                                   ║
║   OS v0.1 — Free AI Operating System                              ║
║   Created by Luo Kai (luokai25)                                  ║
╚═══════════════════════════════════════════════════════════════════╝
"""

class LuoCLI:
    """Unified CLI for Luo OS."""

    def __init__(self, model: str = None, luokai_url: str = None):
        self.model = model or os.environ.get("LUO_MODEL", "mistral")
        self.luokai_url = ollama_url or os.environ.get("LUOKAI_URL", "http://localhost:3000")
        self.agent = None

    def _init_agent(self):
        """Lazy-load the agent."""
        if self.agent is None:
            try:
                from luokai.core.luokai_agent import LUOKAIAgent
                self.agent = LUOKAIAgent(luokai_url=self.luokai_url, model=self.model)
            except Exception as e:
                print(f"[ERROR] Failed to initialize agent: {e}")
                sys.exit(1)
        return self.agent

    def cmd_chat(self, args):
        """Interactive chat mode."""
        print(BANNER)
        agent = self._init_agent()
        print(f"\n[LUOKAI] [URL: {self.luokai_url}]")
        print("Type your message and press Enter. Use /help for commands.\n")

        while True:
            try:
                user_input = input("\033[36myou ▸ \033[0m").strip()
                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    self._handle_slash_command(user_input, agent)
                    continue

                # Regular chat
                print("\033[32mluo ▸ \033[0m", end="", flush=True)
                response = agent.think(user_input)
                print(response)

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except EOFError:
                break

    def _handle_slash_command(self, cmd: str, agent):
        """Handle slash commands in chat."""
        cmd = cmd.lower().strip()

        if cmd in ["/help", "/?"]:
            print("""
Commands:
  /help          Show this help
  /status        Show agent status
  /memory        Show memory contents
  /tools         List available tools
  /model <name>  Switch model
  /clear         Clear conversation
  /quit          Exit

Tool usage:
  !<tool> <args>  Execute a tool (e.g., !web_search python tutorial)
""")
        elif cmd == "/status":
            status = agent.status()
            print(json.dumps(status, indent=2))
        elif cmd == "/memory":
            print(agent._get_memory_summary())
        elif cmd == "/tools":
            if agent._tools:
                print(agent._tools.list_tools())
            else:
                print("Tools not available")
        elif cmd.startswith("/model "):
            new_model = cmd.split(None, 1)[1]
            self.model = new_model
            agent.model = new_model
            print(f"Model switched to: {new_model}")
        elif cmd == "/clear":
            agent.clear_history()
            print("Conversation cleared.")
        elif cmd in ["/quit", "/exit"]:
            raise KeyboardInterrupt
        else:
            print(f"Unknown command: {cmd}. Use /help for available commands.")

    def cmd_voice(self, args):
        """Start voice interface."""
        print(BANNER)
        print("\n🎤 Starting 24/7 voice interface...")
        print("Say 'Luo' or 'LUOKAI' to wake me up.\n")

        agent = self._init_agent()
        agent.start_voice()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStopping voice...")
            agent.stop_voice()

    def cmd_evolution(self, args):
        """Start co-evolution engine."""
        print(BANNER)
        print(f"\n🔄 Starting co-evolution engine (interval: {args.interval}s)...\n")

        agent = self._init_agent()
        agent.start_evolution(interval=args.interval)

        try:
            while True:
                time.sleep(1)
                if agent._coevo:
                    stats = agent._coevo.stats()
                    print(f"\r[CoEvo] Score: {stats['ai_score']:.1f}/10 | "
                          f"Runs: {stats['total_runs']} | "
                          f"Focus: {stats['current_focus']}     ", end="", flush=True)
        except KeyboardInterrupt:
            print("\n\nStopping evolution...")

    def cmd_tools(self, args):
        """List or test tools."""
        print(BANNER)
        print("\n🔧 Available tools:\n")

        from luo_agent.tools.tools import TOOLS

        if args.tool:
            # Execute specific tool
            if args.tool not in TOOLS:
                print(f"Unknown tool: {args.tool}")
                return

            tool_info = TOOLS[args.tool]
            print(f"Tool: {args.tool}")
            print(f"Description: {tool_info['description']}")
            print(f"Requires permission: {tool_info['requires_permission']}")

            if args.args:
                import json
                try:
                    tool_args = json.loads(args.args)
                except:
                    tool_args = {"query": args.args}
                print(f"\nExecuting with args: {tool_args}")
                result = tool_info['fn'](**tool_args)
                print(f"\nResult:\n{result}")
        else:
            # List all tools
            for name, info in TOOLS.items():
                perm = " [perm]" if info["requires_permission"] else ""
                print(f"  {name}{perm}")
                print(f"    {info['description']}")
            print(f"\nTotal: {len(TOOLS)} tools")
            print("\nUse: python3 luo_cli.py tools <tool_name> '[args_json]'")

    def cmd_status(self, args):
        """Show system status."""
        print(BANNER)
        print("\n📊 Luo OS Status\n")

        # Check LUOKAI
        try:
            import urllib.request
            with urllib.request.urlopen(f"{self.luokai_url}/api/status", timeout=2) as r:
                models = json.loads(r.read()).get("models", [])
                print(f"✓ LUOKAI: Connected ({self.luokai_url})")
                print(f"  Models: {', '.join(m['name'] for m in models) or 'none'}")
        except:
            print(f"✗ LUOKAI: Not connected ({self.luokai_url})")
            print("  Start with: python3 start.py")

        # Check directories
        luo_dir = Path("~/.luo_os").expanduser()
        print(f"\n📁 Data directory: {luo_dir}")
        if luo_dir.exists():
            for item in luo_dir.iterdir():
                size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file()) if item.is_dir() else item.stat().st_size
                print(f"  {item.name}: {size:,} bytes")

        # Check Python version
        print(f"\n🐍 Python: {sys.version.split()[0]}")

        # Check optional dependencies
        print("\n📦 Optional dependencies:")
        deps = [
            ("chromadb", "Vector memory"),
            ("textual", "Rich TUI"),
            ("pyaudio", "Voice interface"),
            ("PIL", "Screenshots"),
        ]
        for dep, desc in deps:
            try:
                __import__(dep)
                print(f"  ✓ {dep} ({desc})")
            except ImportError:
                print(f"  ✗ {dep} ({desc}) — pip install {dep}")

    def cmd_server(self, args):
        """Start web server."""
        print(BANNER)
        print(f"\n🌐 Starting web server on port {args.port}...\n")

        # Import and run server
        import subprocess
        subprocess.run([sys.executable, "luo_server.py"])

    def cmd_tui(self, args):
        """Start rich terminal UI."""
        print(BANNER)
        print("\n📺 Starting Textual TUI...\n")

        try:
            from luo_agent.ui.tui import run_tui
            run_tui()
        except ImportError:
            print("[ERROR] Textual not installed. Run: pip install textual")
            print("Falling back to basic chat...")
            self.cmd_chat(args)

    def cmd_install(self, args):
        """Install dependencies."""
        print(BANNER)
        print("\n📦 Installing Luo OS dependencies...\n")

        req_file = Path(__file__).parent / "requirements.txt"
        if not req_file.exists():
            print("[ERROR] requirements.txt not found")
            return

        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("✓ Dependencies installed successfully")
            print("\nOptional dependencies for full features:")
            print("  pip install chromadb       # Vector memory")
            print("  pip install textual        # Rich TUI")
            print("  pip install pyaudio        # Voice interface")
            print("  pip install Pillow         # Screenshots")
            print("  pip install edge-tts       # High quality TTS")
            print("  pip install openai-whisper # Offline STT")
        else:
            print(f"[ERROR] Installation failed:\n{result.stderr}")

    def run(self):
        """Main entry point."""
        parser = argparse.ArgumentParser(
            description="Luo OS — Unified CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python3 luo_cli.py chat                    # Interactive chat
  python3 luo_cli.py chat --model tinyllama  # Use specific model
  python3 luo_cli.py voice                   # Voice interface
  python3 luo_cli.py evolution --interval 60 # Run evolution every 60s
  python3 luo_cli.py tools                   # List tools
  python3 luo_cli.py tools web_search        # Test web_search tool
  python3 luo_cli.py status                  # System status
  python3 luo_cli.py server --port 3000      # Web server
  python3 luo_cli.py install                 # Install dependencies
"""
        )

        parser.add_argument("--model", "-m", default=self.model, help="Model to use")
        parser.add_argument("--luokai-url", "-u", default=self.luokai_url, help="LUOKAI URL")

        subparsers = parser.add_subparsers(dest="command", help="Command to run")

        # Chat command
        chat_parser = subparsers.add_parser("chat", help="Interactive chat")

        # Voice command
        voice_parser = subparsers.add_parser("voice", help="Voice interface")

        # Evolution command
        evo_parser = subparsers.add_parser("evolution", help="Co-evolution engine")
        evo_parser.add_argument("--interval", "-i", type=int, default=300, help="Interval in seconds")

        # Tools command
        tools_parser = subparsers.add_parser("tools", help="List or test tools")
        tools_parser.add_argument("tool", nargs="?", help="Tool to execute")
        tools_parser.add_argument("args", nargs="?", help="Tool arguments (JSON or string)")

        # Status command
        status_parser = subparsers.add_parser("status", help="System status")

        # Server command
        server_parser = subparsers.add_parser("server", help="Web server")
        server_parser.add_argument("--port", "-p", type=int, default=3000, help="Port")

        # TUI command
        tui_parser = subparsers.add_parser("tui", help="Rich terminal UI")

        # Install command
        install_parser = subparsers.add_parser("install", help="Install dependencies")

        args = parser.parse_args()

        # Update config from args
        self.model = args.model
        self.luokai_url = args.luokai_url

        # Route to command
        if args.command is None:
            parser.print_help()
            return

        cmd_method = f"cmd_{args.command}"
        if hasattr(self, cmd_method):
            getattr(self, cmd_method)(args)
        else:
            print(f"Unknown command: {args.command}")
            parser.print_help()


if __name__ == "__main__":
    cli = LuoCLI()
    cli.run()