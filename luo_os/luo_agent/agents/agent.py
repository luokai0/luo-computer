import json, re, os, sys
from typing import Optional, Callable
from core.llm import OllamaClient  # LUOKAI compat
from core.config import LuoConfig
from tools.tools import ToolExecutor

# luo_memory — living cell memory system
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "memory"))
from luo_memory import LuoMemorySync

SYS = """You are Luo, an autonomous AI agent inside Luo OS.
To use a tool respond with:
```tool
{{"tool":"name","args":{{"key":"value"}}}}
```
Tools:
{tools}

{memory}

Be concise. Use tools when needed. Confirm destructive actions."""

class LuoAgentCore:
    def __init__(self, config, memory=None):
        self.config = config
        self.llm = OllamaClient()
        self.tools = ToolExecutor()
        self.conversation = []

        # boot luo_memory cell network
        palace = os.path.expanduser(
            os.environ.get("LUO_PALACE_PATH", "~/.luo_memory/palace")
        )
        self.mem = LuoMemorySync(palace_path=palace)
        self.mem.start()

        # load hot context (facts + recent episodes)
        self._hot_context = self.mem.wake_up()

    def _sys(self):
        return SYS.format(
            tools=self.tools.list_tools(),
            memory=self._hot_context,
        )

    def _extract_tool(self, text):
        m = re.search(r"```tool\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            try: return json.loads(m.group(1))
            except: pass
        return None

    def _perm(self, name, args):
        print(f"\n⚠  Luo wants: {name} | args: {args}")
        return input("Allow? [y/N]: ").strip().lower() in ("y", "yes")

    def chat(self, user_input, stream_callback=None):
        self.conversation.append({"role": "user", "content": user_input})
        messages = [{"role": "system", "content": self._sys()}] + self.conversation
        final = ""; loops = 0

        while loops < 8:
            if stream_callback:
                resp = ""
                for tok in self.llm.stream_chat(
                    messages, temperature=self.config.get("temperature", 0.7)
                ):
                    resp += tok; stream_callback(tok)
            else:
                resp = self.llm.chat(
                    messages, temperature=self.config.get("temperature", 0.7)
                )
            if not resp or resp.startswith("[ERROR]"):
                final = resp or "[ERROR]"; break

            call = self._extract_tool(resp)
            if call:
                name = call.get("tool", ""); args = call.get("args", {})
                result = self.tools.execute(name, args, ask_permission=self._perm)

                # tell skill cell about every tool execution
                self.mem.tool_executed(name, args=args,
                                       result_summary=str(result)[:200],
                                       success=not str(result).startswith("[ERROR]"))

                self.conversation.append({"role": "assistant", "content": resp})
                self.conversation.append({"role": "user", "content": f"[Tool:{name}]\n{result}"})
                messages = [{"role": "system", "content": self._sys()}] + self.conversation
                if stream_callback:
                    stream_callback(f"\n[🔧{name}]→{result[:150]}\n")
                loops += 1; continue

            final = resp; break

        self.conversation.append({"role": "assistant", "content": final})

        # store the exchange in luo_memory
        exchange = f"User: {user_input}\nLuo: {final[:400]}"
        self.mem.store(exchange, role="exchange")

        # refresh hot context after storing
        self._hot_context = self.mem.wake_up()
        return final

    def end_session(self, goal: str = "", success: bool = True):
        """Call at end of session to crystallize skills and flush working memory."""
        self.mem.task_completed(goal=goal, success=success)
        self.mem.stop()

    def reset_conversation(self):
        self.conversation = []

    def save_conversation(self, sid):
        # persist via luo_memory instead of flat file
        self.mem.store(
            f"[session_save:{sid}] {json.dumps(self.conversation[-6:])}",
            role="session_archive",
        )

    def load_conversation(self, sid):
        results = self.mem.recall(query=f"session_save:{sid}", limit=1)
        if results:
            try:
                raw = results[0]["content"].split("] ", 1)[1]
                self.conversation = json.loads(raw)
            except Exception:
                self.conversation = []
