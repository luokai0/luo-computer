#!/usr/bin/env python3
"""
LUOKAI ReAct Agent — Advanced Reasoning + Acting Agent
Implements the ReAct pattern with planning, reflection, and tool use.

This upgrades LUOKAI from a simple chatbot to an actual agent that:
1. Plans before acting
2. Reasons about problems step-by-step
3. Uses tools effectively
4. Reflects on results and self-corrects
5. Maintains coherent multi-turn conversations

Created by Luo Kai (luokai25) — Enhanced by Claude Code
"""
import json
import threading
import time
import re
import subprocess
import sys
import os
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Callable, Generator, Any
from dataclasses import dataclass, field
from enum import Enum

# Import vector memory
try:
    from luo_agent.memory.vector_memory import VectorMemory
    VECTOR_MEMORY_AVAILABLE = True
except ImportError:
    VECTOR_MEMORY_AVAILABLE = False
    VectorMemory = None

# Import tools
try:
    from luo_agent.tools.tools import ToolExecutor, TOOLS
    TOOLS_AVAILABLE = True
except ImportError:
    TOOLS_AVAILABLE = False
    ToolExecutor = None
    TOOLS = {}


class AgentState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    REASONING = "reasoning"
    ACTING = "acting"
    REFLECTING = "reflecting"
    ERROR = "error"


@dataclass
class Thought:
    """A single thought in the reasoning chain."""
    step: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict] = None
    observation: Optional[str] = None
    reflection: Optional[str] = None


@dataclass
class Plan:
    """A plan consisting of multiple steps."""
    goal: str
    steps: List[Dict[str, str]]
    current_step: int = 0
    completed: bool = False


class ReActAgent:
    """
    ReAct (Reasoning + Acting) Agent for LUOKAI.

    This agent follows the ReAct paradigm:
    1. Thought: Reason about the problem
    2. Action: Decide what tool/action to use
    3. Observation: See the result
    4. Repeat until done
    5. Final Answer: Synthesize a response

    Enhanced features:
    - Planning: Decompose complex tasks into steps
    - Reflection: Evaluate results and self-correct
    - Memory: Semantic search through past interactions
    - Streaming: Real-time token output
    """

    NAME = "LUOKAI-ReAct"
    VERSION = "2.0"

    # Maximum reasoning iterations before forcing an answer
    MAX_ITERATIONS = 10

    # System prompts for different modes
    SYSTEM_PROMPT_PLANNING = """You are LUOKAI, an advanced AI agent in LuoOS with planning capabilities.

When given a complex task, break it down into clear, sequential steps.
Each step should be actionable and have a clear success criterion.

Format your plan as:
STEP 1: [action] - [expected outcome]
STEP 2: [action] - [expected outcome]
...

Be concise but thorough. Consider dependencies between steps.
Identify potential issues and include fallback approaches."""

    SYSTEM_PROMPT_REACT = """You are LUOKAI, an advanced AI agent using the ReAct (Reasoning + Acting) framework.

Available tools:
{tools}

You must use this EXACT format:

Thought: [your reasoning about what to do]
Action: [tool_name]
Action Input: {{"param": "value"}}
Observation: [tool result - this is auto-filled]
... (repeat Thought/Action/Observation as needed)
Thought: [final reasoning]
Final Answer: [your complete answer to the user]

Guidelines:
- Be systematic and thorough
- Use tools when they would help accomplish the task
- If a tool fails, try a different approach
- Always explain your reasoning before acting
- Provide complete, helpful final answers
- Keep thoughts concise but clear

IMPORTANT: You must use the exact format above. Only use tools from the available list."""

    SYSTEM_PROMPT_REFLECTION = """You are LUOKAI reflecting on your work.

Task: {task}
Actions taken: {actions}
Result: {result}

Evaluate:
1. Did you fully accomplish the task?
2. What could have been done better?
3. What should the user know?

Be honest and constructive. If there were issues, acknowledge them and suggest improvements."""

    def __init__(
        self,
        model: str = "luokai-1.0",
        use_vector_memory: bool = True,
        use_tools: bool = True,
        streaming: bool = True,
        max_context_tokens: int = 8192,
        temperature: float = 0.7,
    ):
        self.model = model
        self.streaming = streaming
        self.max_context_tokens = max_context_tokens
        self.temperature = temperature

        self._history: List[Dict] = []
        self._memory: Dict = {}
        self._thoughts: List[Thought] = []
        self._current_plan: Optional[Plan] = None
        self._state = AgentState.IDLE
        self._lock = threading.RLock()

        # Conversation context
        self._context: List[Dict] = []
        self._session_summary: str = ""

        # LUOKAI uses his own inference engine
        self._available_models = [self.model]

        # Initialize vector memory
        self._vector_memory = None
        if use_vector_memory and VECTOR_MEMORY_AVAILABLE:
            try:
                self._vector_memory = VectorMemory(
                    agent_id="luokai_react",
                    persist_dir="~/.luo_os/chroma"
                )
            except Exception as e:
                print(f"[{self.NAME}] Vector memory init failed: {e}")

        # Initialize tools
        self._tools = None
        if use_tools and TOOLS_AVAILABLE:
            try:
                self._tools = ToolExecutor(auto_approve=True)  # Auto-approve for agent autonomy
            except Exception as e:
                print(f"[{self.NAME}] Tools init failed: {e}")

        # Initialize skills library
        self._skills = None
        try:
            from luokai.skills import get_library
            self._skills = get_library()
        except Exception as e:
            print(f"[{self.NAME}] Skills init failed: {e}")

        # ── Boot the LUOKAI Brain (wires luo_memory, coevo, kairos, ToT, self-improver)
        self._brain = None
        try:
            from luokai.core.brain import LuokaiBrain
            self._brain = LuokaiBrain(agent=self)
            self._brain.boot()
        except Exception as e:
            print(f"[{self.NAME}] Brain boot failed: {e}")

        # LUOKAI's mind — the native inference engine
        self._mind = None
        try:
            from luokai.core.inference import get_inference
            self._mind = get_inference()
        except Exception as e:
            print(f"[{self.NAME}] Mind init failed: {e}")

        # Memory persistence
        self._mem_dir = Path("~/.luo_os/luokai").expanduser()
        self._mem_dir.mkdir(parents=True, exist_ok=True)
        self._mem_file = self._mem_dir / "memory_react.json"
        self._load_memory()

        print(f"[{self.NAME}] v{self.VERSION} initialized")
        print(f"[{self.NAME}] Model: {self.model}")
        print(f"[{self.NAME}] Tools: {len(TOOLS) if TOOLS_AVAILABLE else 0}")
        print(f"[{self.NAME}] Skills: {self._skills.stats()['total']:,}" if self._skills else f"[{self.NAME}] Skills: off")
        print(f"[{self.NAME}] Vector Memory: {'active' if self._vector_memory and self._vector_memory.available else 'off'}")
        # brain status printed by LuokaiBrain.boot() itself

    # ── LUOKAI Mind — independent intelligence ──────────────────────────

    def _call_luokai(
        self,
        messages: List[Dict],
        max_tokens: int = 1024,
        stream: bool = None
    ) -> str:
        """Generate response using LUOKAI's own inference engine. No external model."""
        if self._mind:
            return self._mind.generate(
                messages,
                max_tokens=max_tokens,
                temperature=self.temperature
            )
        # Fallback — try to get engine fresh
        try:
            from luokai.core.inference import get_inference
            self._mind = get_inference()
            return self._mind.generate(messages, max_tokens=max_tokens)
        except Exception as e:
            user_msg = next((m["content"] for m in reversed(messages) if m.get("role")=="user"), "")
            return (f"I received: '{user_msg[:60]}'. "
                    f"LUOKAI inference starting up — try again in a moment.")

    # Legacy alias — _call_ollama routes to LUOKAI native inference
    _call_ollama = _call_luokai

    # ── ReAct Reasoning ─────────────────────────────────────────────────

    def think(
        self,
        user_input: str,
        max_tokens: int = 2048,
        stream: bool = None
    ) -> str:
        """
        Main reasoning function using ReAct pattern.

        This is the primary entry point for the agent.
        It will:
        1. Analyze the input
        2. Decide if planning is needed
        3. Use ReAct loop if tools would help
        4. Reflect and provide final answer
        """
        with self._lock:
            self._state = AgentState.REASONING
            self._thoughts = []

            # Add to history
            self._history.append({"role": "user", "content": user_input})

            # Build context
            messages = self._build_context_messages(user_input)

            # ── Fast path: simple conversational queries → direct to _mind ─────
            # Skip the full ReAct loop for conversational/knowledge queries
            _t0 = time.time()
            if self._mind and self._is_simple_query(user_input):
                response = self._mind.generate(
                    messages, max_tokens=max_tokens, temperature=self.temperature
                )
                self._history.append({"role": "assistant", "content": response})
                self._auto_remember(user_input, response)
                if self._brain:
                    try:
                        self._brain.post_think(
                            user_input=user_input, response=response,
                            tools_used=[], success=True,
                            duration_ms=(time.time()-_t0)*1000
                        )
                    except Exception:
                        pass
                self._state = AgentState.IDLE
                return response

            # ── Brain pre-think: inject living memory + kairos alerts + associations
            if self._brain:
                try:
                    brain_ctx = self._brain.pre_think(user_input)
                    if brain_ctx:
                        messages.insert(1, {"role": "system", "content": brain_ctx})
                except Exception as _be:
                    pass  # brain errors never block the agent

            # Check if this is a complex task requiring planning
            if self._needs_planning(user_input):
                self._state = AgentState.PLANNING
                plan = self._create_plan(user_input, messages)
                return self._execute_plan(plan, messages, max_tokens)

            # Check if tools would help
            if self._should_use_tools(user_input):
                return self._react_loop(user_input, messages, max_tokens, stream)

            # Simple response - no tools needed
            response = self._direct_response(user_input, messages, max_tokens, stream)

            # Add to history
            self._history.append({"role": "assistant", "content": response})

            # Auto-remember important things
            self._auto_remember(user_input, response)

            # ── Brain post-think: store exchange, log to self-improver, skill tracking
            if self._brain:
                try:
                    _duration = (time.time() - _t0) * 1000
                    self._brain.post_think(
                        user_input=user_input,
                        response=response,
                        tools_used=[],
                        success=True,
                        duration_ms=_duration,
                    )
                except Exception:
                    pass

            self._state = AgentState.IDLE
            return response

    def _is_simple_query(self, user_input: str) -> bool:
        """
        Returns True for conversational/knowledge queries that don't need
        the full ReAct loop — greetings, what/how/why questions, status,
        short messages. These go straight to _mind.generate().
        """
        u = user_input.strip().lower()
        # Short messages are always simple
        if len(user_input.split()) <= 6:
            return True
        # Question words without tool-needing content
        simple_starts = ("what is", "what are", "who is", "why is", "how does",
                         "how do", "tell me", "explain", "describe", "define",
                         "what's", "how's", "when did", "where is", "can you explain",
                         "i want to", "i need to", "i'm looking", "do you know",
                         "status", "your status", "what is your", "help", "hi ",
                         "hello", "hey ", "show me", "give me", "list ", "find ")
        if any(u.startswith(s) for s in simple_starts):
            return True
        # Tool-needing keywords → NOT simple
        tool_words = ("read file", "write file", "run ", "execute", "download",
                      "install", "create file", "delete", "bash", "terminal",
                      "web search", "browse", "open url", "fetch url")
        if any(t in u for t in tool_words):
            return False
        # Default: treat as simple if no tool words
        return True

    def _needs_planning(self, user_input: str) -> bool:
        """Determine if a task requires planning."""
        planning_keywords = [
            "plan", "create", "build", "implement", "develop", "design",
            "multiple", "steps", "comprehensive", "complete", "full",
            "and then", "followed by", "after that", "sequence",
            "project", "application", "system", "architecture"
        ]
        user_lower = user_input.lower()
        return any(kw in user_lower for kw in planning_keywords) and len(user_input.split()) > 10

    def _should_use_tools(self, user_input: str) -> bool:
        """Determine if tools would help with this input."""
        if not self._tools or not TOOLS_AVAILABLE:
            return False

        tool_keywords = [
            "file", "read", "write", "create", "delete", "list",
            "search", "web", "url", "fetch", "download",
            "run", "execute", "command", "bash", "python", "script",
            "analyze", "check", "find", "look", "show",
            "process", "system", "docker", "git", "code"
        ]
        user_lower = user_input.lower()
        return any(kw in user_lower for kw in tool_keywords)

    def _build_context_messages(self, user_input: str) -> List[Dict]:
        """Build messages with system prompt, memory, and history."""
        messages = []

        # System prompt with tools
        tools_desc = self._get_tools_description()
        system_prompt = self.SYSTEM_PROMPT_REACT.format(tools=tools_desc)
        messages.append({"role": "system", "content": system_prompt})

        # Add semantic memory context
        if self._vector_memory:
            mem_context = self._vector_memory.get_context(user_input, n=5)
            if mem_context:
                messages.append({"role": "system", "content": mem_context})

        # Add active goals from brain (if brain is up but pre_think hasn't run yet)
        if self._brain and self._brain.memory:
            try:
                goals = self._brain.get_goals()
                if goals:
                    goal_lines = [f"  [{g.get('priority',5)}] {g.get('description','')}"
                                  for g in goals[:3]]
                    messages.append({"role": "system",
                                     "content": "[active goals]\n" + "\n".join(goal_lines)})
            except Exception:
                pass

        # Add session summary if exists
        if self._session_summary:
            messages.append({"role": "system", "content": f"Session summary: {self._session_summary}"})

        # Add recent conversation history
        messages.extend(self._history[-20:])

        return messages

    def _get_tools_description(self) -> str:
        """Get formatted description of available tools."""
        if not TOOLS_AVAILABLE:
            return "No tools available."

        lines = []
        for name, info in list(TOOLS.items())[:15]:  # Limit to prevent context overflow
            desc = info.get("description", "No description")
            lines.append(f"- {name}: {desc}")

        if len(TOOLS) > 15:
            lines.append(f"... and {len(TOOLS) - 15} more tools")

        return "\n".join(lines)

    # ── Planning ────────────────────────────────────────────────────────

    def _create_plan(self, task: str, messages: List[Dict]) -> Plan:
        """Create a plan for a complex task."""
        planning_messages = messages.copy()
        planning_messages.insert(0, {"role": "system", "content": self.SYSTEM_PROMPT_PLANNING})
        planning_messages.append({"role": "user", "content": f"Create a step-by-step plan for: {task}"})

        plan_response = self._call_ollama(planning_messages, max_tokens=512)

        # Parse plan into steps
        steps = []
        for line in plan_response.split('\n'):
            line = line.strip()
            if re.match(r'(STEP|step|\d+)[\s:.]', line):
                steps.append({"description": line, "status": "pending"})

        if not steps:
            # Fallback to single step
            steps = [{"description": task, "status": "pending"}]

        return Plan(goal=task, steps=steps)

    def _execute_plan(self, plan: Plan, messages: List[Dict], max_tokens: int) -> str:
        """Execute a plan step by step."""
        results = []

        for i, step in enumerate(plan.steps):
            self._state = AgentState.ACTING
            step_desc = step["description"]

            # Execute each step
            if self._should_use_tools(step_desc):
                result = self._react_loop(step_desc, messages, max_tokens)
            else:
                result = self._direct_response(step_desc, messages, max_tokens)

            results.append(f"Step {i+1}: {step_desc}\nResult: {result}")
            step["status"] = "completed"

        # Reflect on overall plan execution
        self._state = AgentState.REFLECTING
        reflection = self._reflect_on_plan(plan, results, messages)

        return reflection

    # ── ReAct Loop ──────────────────────────────────────────────────────

    def _react_loop(
        self,
        user_input: str,
        messages: List[Dict],
        max_tokens: int,
        stream: bool = None
    ) -> str:
        """
        Execute the ReAct loop: Thought → Action → Observation → Repeat
        """
        iteration = 0
        scratchpad = []

        # Initial thought
        scratchpad.append(f"Question: {user_input}")

        while iteration < self.MAX_ITERATIONS:
            iteration += 1
            self._state = AgentState.REASONING

            # Generate thought and potential action
            prompt = "\n".join(scratchpad) + "\nThought:"
            thought_response = self._generate_thought(prompt, messages, max_tokens=256)

            # Parse thought and action
            thought, action, action_input = self._parse_thought_action(thought_response)

            scratchpad.append(f"Thought: {thought}")

            if action and self._tools:
                # Execute action
                self._state = AgentState.ACTING
                observation = self._execute_tool(action, action_input)
                scratchpad.append(f"Action: {action}")
                scratchpad.append(f"Action Input: {json.dumps(action_input)}")
                scratchpad.append(f"Observation: {observation[:500]}")  # Limit observation length

                # Check if we should continue
                if "FINAL_ANSWER:" in observation.upper() or "TASK_COMPLETE" in observation.upper():
                    break
            else:
                # No action needed, generate final answer
                break

        # Generate final answer
        self._state = AgentState.REFLECTING
        final_answer = self._generate_final_answer(scratchpad, messages, max_tokens)

        self._history.append({"role": "assistant", "content": final_answer})
        self._auto_remember(user_input, final_answer)

        # ── Brain post-think for tool-using path
        if self._brain:
            try:
                # Extract tool names from scratchpad
                import re as _re
                _tools_used = _re.findall(r'Action: ([\w_]+)', "\n".join(scratchpad))
                _duration = (time.time() - _t0) * 1000 if "_t0" in dir() else 0.0
                self._brain.post_think(
                    user_input=user_input,
                    response=final_answer,
                    tools_used=_tools_used,
                    success=True,
                    duration_ms=_duration,
                )
            except Exception:
                pass

        self._state = AgentState.IDLE
        return final_answer

    def _generate_thought(self, scratchpad: str, messages: List[Dict], max_tokens: int) -> str:
        """Generate the next thought and potential action."""
        prompt_messages = messages.copy()
        prompt_messages.append({
            "role": "user",
            "content": f"{scratchpad}\nGenerate your next Thought and Action if needed:"
        })
        return self._call_ollama(prompt_messages, max_tokens=max_tokens)

    def _parse_thought_action(self, response: str) -> tuple:
        """Parse thought and action from LLM response."""
        thought = ""
        action = None
        action_input = {}

        # Extract thought
        thought_match = re.search(r'Thought:\s*(.+?)(?=Action:|$)', response, re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip()

        # Extract action
        action_match = re.search(r'Action:\s*(\w+)', response)
        if action_match:
            action = action_match.group(1).strip()

        # Extract action input
        input_match = re.search(r'Action Input:\s*(\{.+?\}|\[.+?\]|".+?"|\S+)', response, re.DOTALL)
        if input_match:
            try:
                raw_input = input_match.group(1)
                if raw_input.startswith('{'):
                    action_input = json.loads(raw_input)
                elif raw_input.startswith('['):
                    try:
                        action_input = {"args": json.loads(raw_input)}
                    except (json.JSONDecodeError, ValueError):
                        action_input = {"args": raw_input}
                else:
                    action_input = {"input": raw_input.strip('"')}
            except json.JSONDecodeError:
                action_input = {"input": input_match.group(1)}

        return thought, action, action_input

    def _execute_tool(self, tool_name: str, args: Dict) -> str:
        """Execute a tool and return the result."""
        if not self._tools or tool_name not in TOOLS:
            return f"Error: Tool '{tool_name}' not available."

        try:
            result = self._tools.execute(tool_name, args)
            return str(result)
        except Exception as e:
            return f"Error executing {tool_name}: {e}"

    def _generate_final_answer(
        self,
        scratchpad: List[str],
        messages: List[Dict],
        max_tokens: int
    ) -> str:
        """Generate final answer from scratchpad."""
        prompt_messages = messages.copy()
        full_context = "\n".join(scratchpad)
        prompt_messages.append({
            "role": "user",
            "content": f"Based on this reasoning process:\n{full_context}\n\nProvide a clear, complete final answer:"
        })
        return self._call_ollama(prompt_messages, max_tokens=max_tokens)

    # ── Direct Response ─────────────────────────────────────────────────

    def _direct_response(
        self,
        user_input: str,
        messages: List[Dict],
        max_tokens: int,
        stream: bool = None
    ) -> str:
        """Generate a direct response without tools."""
        response = self._call_ollama(messages, max_tokens=max_tokens, stream=stream)

        # Handle streaming generator
        if isinstance(response, Generator):
            full_response = ""
            for token in response:
                full_response += token
            return full_response

        return response

    # ── Reflection ──────────────────────────────────────────────────────

    def _reflect_on_plan(self, plan: Plan, results: List[str], messages: List[Dict]) -> str:
        """Reflect on plan execution results."""
        reflection_prompt = self.SYSTEM_PROMPT_REFLECTION.format(
            task=plan.goal,
            actions="\n".join(results),
            result=results[-1] if results else "No results"
        )

        reflection_messages = messages.copy()
        reflection_messages.insert(0, {"role": "system", "content": reflection_prompt})

        return self._call_ollama(reflection_messages, max_tokens=512)

    # ── Memory ──────────────────────────────────────────────────────────

    def _load_memory(self):
        """Load persistent memory."""
        if self._mem_file.exists():
            try:
                self._memory = json.loads(self._mem_file.read_text())
            except Exception:
                self._memory = {}

    def _save_memory(self):
        """Save memory to disk."""
        self._mem_file.write_text(json.dumps(self._memory, indent=2))

    def remember(self, key: str, value: str, metadata: Dict = None):
        """Remember information."""
        self._memory[key] = {
            "value": value,
            "time": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self._save_memory()

        if self._vector_memory:
            self._vector_memory.add(f"{key}: {value}", metadata=metadata)

    def recall(self, key: str) -> Optional[str]:
        """Recall information."""
        entry = self._memory.get(key)
        return entry["value"] if entry else None

    def semantic_recall(self, query: str, n: int = 5) -> List[Dict]:
        """Semantic search through memories."""
        if self._vector_memory:
            return self._vector_memory.search(query, n=n)
        return []

    def _auto_remember(self, user_input: str, response: str):
        """Automatically extract and remember important information."""
        patterns = [
            (r"my name is (\w+)", "user_name"),
            (r"i am (?:a|an) ([\w\s]+)", "user_role"),
            (r"i work (?:as|at|with) ([\w\s]+)", "user_work"),
            (r"i live in ([\w\s]+)", "user_location"),
            (r"my favorite ([\w]+) is ([\w\s]+)", None),
            (r"remember that ([^.]+)", None),
        ]

        text = f"{user_input} {response}".lower()
        for pattern, key in patterns:
            match = re.search(pattern, text)
            if match:
                if key:
                    self.remember(key, match.group(1))
                elif len(match.groups()) >= 2:
                    self.remember(f"favorite_{match.group(1)}", match.group(2))

    def summarize_session(self) -> str:
        """Generate a summary of the current session."""
        if not self._history:
            return ""

        summary_messages = [
            {"role": "system", "content": "Summarize this conversation in 2-3 sentences, highlighting key topics and decisions."},
            {"role": "user", "content": "\n".join(f"{h['role']}: {h['content'][:200]}" for h in self._history[-10:])}
        ]

        self._session_summary = self._call_ollama(summary_messages, max_tokens=150)
        return self._session_summary

    # ── Status and Info ─────────────────────────────────────────────────

    def status(self) -> Dict:
        """Get agent status."""
        return {
            "name":               self.NAME,
            "version":            self.VERSION,
            "model":              "luokai-mind-v1",
            "independent":        True,
            "external_model":     None,
            "state":              self._state.value,
            "history_length":     len(self._history),
            "memory_entries":     len(self._memory),
            "vector_memory_count": self._vector_memory.count() if self._vector_memory else 0,
            "tools_available":    len(TOOLS) if TOOLS_AVAILABLE else 0,
            "skills_available":   self._skills.stats()["total"] if self._skills else 0,
            "current_plan":       self._current_plan.goal if self._current_plan else None,
            "mind":               self._mind.status() if self._mind else None,
            "brain":              self._brain.status() if self._brain else None,
        }

    def clear_history(self):
        """Clear conversation history."""
        self._history = []
        self._thoughts = []
        self._current_plan = None
        self._session_summary = ""


# ── Streaming Response Generator ────────────────────────────────────────

class StreamingReActAgent(ReActAgent):
    """ReAct Agent with enhanced streaming support."""

    def think_stream(self, user_input: str, max_tokens: int = 2048) -> Generator[str, None, None]:
        """Stream thoughts and responses in real-time."""
        with self._lock:
            self._state = AgentState.REASONING
            self._history.append({"role": "user", "content": user_input})

            messages = self._build_context_messages(user_input)

            # Check if tools needed
            if self._should_use_tools(user_input):
                # For tool-using responses, we can't stream as easily
                # but we yield progress updates
                yield "[Analyzing task...]\n"
                response = self._react_loop(user_input, messages, max_tokens, stream=False)
                for chunk in response.split('\n'):
                    if chunk.strip():
                        yield chunk + '\n'
            else:
                # Stream direct response
                for token in self._stream_thoughts(messages, max_tokens):
                    yield token

            self._state = AgentState.IDLE

    def _stream_thoughts(self, messages: List[Dict], max_tokens: int) -> Generator[str, None, None]:
        """Stream thoughts and response."""
        # Add thought indicator
        yield "💭 "

        # Stream the response
        response = self._call_ollama(messages, max_tokens=max_tokens, stream=True)
        full_response = ""

        if isinstance(response, Generator):
            for token in response:
                full_response += token
                yield token
        else:
            full_response = response
            yield response

        # Save to history
        self._history.append({"role": "assistant", "content": full_response})


# ── Factory function ───────────────────────────────────────────────────

def create_agent(
    streaming: bool = True,
    **kwargs
) -> ReActAgent:
    """Create LUOKAI — fully independent, no external model."""
    if streaming:
        return StreamingReActAgent(**kwargs)
    return ReActAgent(streaming=False, **kwargs)


# ── CLI Test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("LUOKAI ReAct Agent — Interactive Test")
    print("=" * 50)

    agent = create_agent()
    print(f"\nAgent status: {json.dumps(agent.status(), indent=2)}")

    print("\nType 'quit' to exit, 'status' for status\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() == 'quit':
                break
            if user_input.lower() == 'status':
                print(json.dumps(agent.status(), indent=2))
                continue
            if user_input.lower() == 'summary':
                print("Session summary:", agent.summarize_session())
                continue

            print("\nLUOKAI:")
            response = agent.think(user_input)
            print(response)
            print()
        except KeyboardInterrupt:
            break

    print("\nGoodbye!")