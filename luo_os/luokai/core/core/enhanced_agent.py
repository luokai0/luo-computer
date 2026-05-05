#!/usr/bin/env python3
"""
LUOKAI Enhanced Agent Integration
===================================
Combines all enhanced capabilities into a unified agent.

Modules integrated:
- ReAct reasoning (react_agent.py)
- Tree of Thought (thought.py)
- MCP integration (mcp.py)
- Self-improvement (self_improve.py)
- Skills library (skills/)
- Model management (luo_agent/core/models.py)
- Benchmark library (evolution/benchmarks.py)

Created by Luo Kai (luokai25) — Enhanced by Claude Code
"""
import json
import time
import threading
from typing import Dict, List, Optional, Generator, Any
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

# Import core modules
from luokai.core.luokai_agent import LUOKAIAgent
from luokai.core.react_agent import ReActAgent, StreamingReActAgent, AgentState
from luokai.core.thought import TreeOfThought, solve_with_tot
from luokai.core.self_improve import SelfImprovementEngine

# Import optional modules
try:
    from luokai.core.mcp import MCPClient, MCP_SERVER_CONFIGS
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    MCPClient = None

try:
    from luo_agent.core.models import ModelManager, get_best_available_model
    MODEL_MANAGER_AVAILABLE = True
except ImportError:
    MODEL_MANAGER_AVAILABLE = False
    ModelManager = None

try:
    from luokai.skills import registry as skill_registry
    SKILLS_AVAILABLE = True
except ImportError:
    SKILLS_AVAILABLE = False


@dataclass
class AgentConfig:
    """Configuration for the enhanced agent."""
    model: str = None  # Auto-detect if None
    use_react: bool = True
    use_tot_for_complex: bool = True
    use_self_improve: bool = True
    use_mcp: bool = True
    use_streaming: bool = True
    max_history: int = 50
    data_dir: str = "~/.luo_os"


class EnhancedLUOKAIAgent:
    """
    Enhanced LUOKAI agent combining all advanced capabilities.

    Features:
    - ReAct-style reasoning with tool use
    - Tree of Thought for complex problems
    - Self-improvement and pattern learning
    - MCP tool integration
    - Smart model selection
    - Skills library
    - Streaming responses
    """

    VERSION = "2.0"

    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()

        # Initialize model manager
        self.model_manager = None
        if MODEL_MANAGER_AVAILABLE:
            self.model_manager = ModelManager("luokai-native")
            if not self.config.model:
                self.config.model = self.model_manager.select_best_model()

        # Initialize ReAct agent
        self.react_agent = None
        if self.config.use_react:
            try:
                agent_class = StreamingReActAgent if self.config.use_streaming else ReActAgent
                self.react_agent = agent_class(
                                        model=self.config.model,
                    streaming=self.config.use_streaming
                )
                print(f"[EnhancedLUOKAI] ReAct agent initialized (model: {self.config.model})")
            except Exception as e:
                print(f"[EnhancedLUOKAI] ReAct agent failed: {e}")

        # Fall back to basic agent
        self.basic_agent = None
        if not self.react_agent:
            try:
                self.basic_agent = LUOKAIAgent(
                                        model=self.config.model or "mistral"
                )
                print(f"[EnhancedLUOKAI] Basic agent initialized")
            except Exception as e:
                print(f"[EnhancedLUOKAI] Basic agent failed: {e}")

        # Initialize Tree of Thought
        self.tot = None
        if self.config.use_tot_for_complex:
            try:
                self.tot = TreeOfThought(
                                        model=self.config.model or "mistral"
                )
                print("[EnhancedLUOKAI] Tree of Thought initialized")
            except Exception as e:
                print(f"[EnhancedLUOKAI] ToT failed: {e}")

        # Initialize self-improvement
        self.self_improve = None
        if self.config.use_self_improve:
            try:
                self.self_improve = SelfImprovementEngine(
                    data_dir=Path(self.config.data_dir) / "self_improve",
                                        model=self.config.model or "mistral"
                )
                print("[EnhancedLUOKAI] Self-improvement initialized")
            except Exception as e:
                print(f"[EnhancedLUOKAI] Self-improvement failed: {e}")

        # Initialize MCP client
        self.mcp_client = None
        if self.config.use_mcp and MCP_AVAILABLE:
            try:
                self.mcp_client = MCPClient(
                                        model=self.config.model or "mistral"
                )
                print("[EnhancedLUOKAI] MCP client initialized")
            except Exception as e:
                print(f"[EnhancedLUOKAI] MCP client failed: {e}")

        # History tracking
        self._history: List[Dict] = []
        self._history_lock = threading.Lock()

        # Active agent reference
        self._active_agent = self.react_agent or self.basic_agent

        print(f"[EnhancedLUOKAI] v{self.VERSION} ready")
        print(f"[EnhancedLUOKAI]   ReAct: {self.react_agent is not None}")
        print(f"[EnhancedLUOKAI]   ToT: {self.tot is not None}")
        print(f"[EnhancedLUOKAI]   Self-improve: {self.self_improve is not None}")
        print(f"[EnhancedLUOKAI]   MCP: {self.mcp_client is not None}")
        print(f"[EnhancedLUOKAI]   Skills: {skill_registry.SKILL_COUNT if SKILLS_AVAILABLE else 0}")

    def think(
        self,
        user_input: str,
        use_tot: bool = None,
        stream: bool = None
    ) -> str:
        """
        Main thinking function with enhanced capabilities.

        Args:
            user_input: The user's input
            use_tot: Force use Tree of Thought (auto-detected if None)
            stream: Use streaming response

        Returns:
            The agent's response
        """
        start_time = time.time()

        # Record interaction start
        interaction_id = None
        if self.self_improve:
            interaction_id = hashlib.md5(f"{user_input}{time.time()}".encode()).hexdigest()[:8]

        # Determine if ToT should be used
        if use_tot is None:
            use_tot = self._should_use_tot(user_input)

        # Get optimized prompt from self-improvement
        optimized_input = user_input
        if self.self_improve:
            optimized_input = self.self_improve.get_optimized_prompt(user_input)

        # Use Tree of Thought for complex problems
        if use_tot and self.tot:
            response = self._think_with_tot(user_input)
        # Use ReAct agent
        elif self.react_agent:
            response = self.react_agent.think(optimized_input)
        # Fall back to basic agent
        elif self.basic_agent:
            response = self.basic_agent.think(optimized_input)
        else:
            response = "[ERROR] No agent available"

        # Record interaction for learning
        if self.self_improve:
            response_time = time.time() - start_time
            self.self_improve.record_interaction(
                user_input=user_input,
                response=response,
                response_time=response_time
            )

        # Add to history
        with self._history_lock:
            self._history.append({
                "timestamp": datetime.now().isoformat(),
                "user": user_input,
                "assistant": response[:500],  # Truncate for storage
                "used_tot": use_tot
            })
            # Keep history bounded
            if len(self._history) > self.config.max_history:
                self._history = self._history[-self.config.max_history:]

        return response

    def think_stream(self, user_input: str) -> Generator[str, None, None]:
        """Stream response tokens."""
        if self.react_agent and hasattr(self.react_agent, 'think_stream'):
            for token in self.react_agent.think_stream(user_input):
                yield token
        else:
            # Fall back to non-streaming
            response = self.think(user_input)
            for word in response.split():
                yield word + " "

    def _should_use_tot(self, user_input: str) -> bool:
        """Determine if Tree of Thought should be used."""
        complex_keywords = [
            "explain why", "compare", "analyze", "evaluate",
            "pros and cons", "step by step", "multiple approaches",
            "which is better", "should I", "what if",
            "solve", "find the best", "optimize"
        ]

        input_lower = user_input.lower()
        return any(kw in input_lower for kw in complex_keywords)

    def _think_with_tot(self, user_input: str) -> str:
        """Use Tree of Thought for complex reasoning."""
        try:
            final_answer, path = solve_with_tot(
                problem=user_input,
                                model=self.config.model or "mistral"
            )
            return final_answer
        except Exception as e:
            # Fall back to regular thinking
            if self.react_agent:
                return self.react_agent.think(user_input)
            elif self.basic_agent:
                return self.basic_agent.think(user_input)
            return f"[ERROR] ToT failed: {e}"

    def provide_feedback(self, interaction_id: str, success: bool, feedback: str = None):
        """Provide feedback on an interaction for learning."""
        if self.self_improve:
            self.self_improve.record_feedback(interaction_id, success, feedback)

    def use_skill(self, skill_name: str, **kwargs) -> str:
        """Use a skill from the skills library."""
        if not SKILLS_AVAILABLE:
            return "[ERROR] Skills not available"

        try:
            result = skill_registry.execute(skill_name, **kwargs)
            return str(result)
        except Exception as e:
            return f"[ERROR] Skill execution failed: {e}"

    def list_skills(self) -> List[str]:
        """List all available skills."""
        if SKILLS_AVAILABLE:
            return [s.name for s in skill_registry.list_skills()]
        return []

    def connect_mcp_server(self, name: str, command: str, args: List[str] = None) -> bool:
        """Connect to an MCP server."""
        if not self.mcp_client:
            return False

        return self.mcp_client.connect_server(name, command, args)

    def list_mcp_tools(self) -> List[Dict]:
        """List all MCP tools."""
        if not self.mcp_client:
            return []

        return [t.to_dict() for t in self.mcp_client.list_tools()]

    def get_status(self) -> Dict:
        """Get comprehensive agent status."""
        status = {
            "version": self.VERSION,
            "model": self.config.model,
            "react_enabled": self.react_agent is not None,
            "tot_enabled": self.tot is not None,
            "self_improve_enabled": self.self_improve is not None,
            "mcp_enabled": self.mcp_client is not None,
            "skills_available": skill_registry.SKILL_COUNT if SKILLS_AVAILABLE else 0,
            "history_length": len(self._history),
        }

        # Add self-improvement stats
        if self.self_improve:
            metrics = self.self_improve.analyze_performance()
            status["self_improve"] = metrics

        # Add MCP status
        if self.mcp_client:
            status["mcp"] = self.mcp_client.status()

        # Add agent state
        if self.react_agent:
            status["agent_state"] = self.react_agent._state.value

        return status

    def get_performance_report(self) -> str:
        """Get a human-readable performance report."""
        if not self.self_improve:
            return "Self-improvement module not enabled."

        metrics = self.self_improve.analyze_performance()
        suggestions = self.self_improve.get_improvement_suggestions()

        lines = [
            "LUOKAI Performance Report",
            "=" * 40,
            "",
            "Interactions:",
            f"  Total: {metrics.get('total_interactions', 0)}",
            f"  Successful: {metrics.get('successful', 0)}",
            f"  Failed: {metrics.get('failed', 0)}",
            f"  Success Rate: {metrics.get('success_rate', 0):.1%}",
            "",
            "Response:",
            f"  Avg Response Time: {metrics.get('avg_response_time', 0):.2f}s",
            "",
            "Learning:",
            f"  Learned Patterns: {metrics.get('learned_patterns', 0)}",
            f"  Effective Patterns: {metrics.get('effective_patterns', 0)}",
            f"  Training Examples: {metrics.get('training_examples_available', 0)}",
            "",
            "Tools Used:"
        ]

        for tool, count in metrics.get('most_used_tools', []):
            lines.append(f"  - {tool}: {count}")

        if suggestions:
            lines.append("")
            lines.append("Suggestions:")
            for suggestion in suggestions:
                lines.append(f"  - {suggestion}")

        return "\n".join(lines)

    def export_training_data(self, output_file: str = None) -> str:
        """Export training data for fine-tuning."""
        if not self.self_improve:
            return "Self-improvement module not enabled."

        return self.self_improve.export_for_finetuning(output_file)


# Import hashlib for interaction ID
import hashlib


def create_enhanced_agent(
    model: str = None,
    **kwargs
) -> EnhancedLUOKAIAgent:
    """Factory function to create an enhanced agent."""
    config = AgentConfig(model=model, **kwargs)
    return EnhancedLUOKAIAgent(config)


if __name__ == "__main__":
    print("LUOKAI Enhanced Agent")
    print("=" * 50)

    # Create agent
    agent = create_enhanced_agent()

    # Show status
    print("\nAgent Status:")
    status = agent.get_status()
    for key, value in status.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")

    # Test thinking
    print("\nTesting thinking...")
    response = agent.think("What is the capital of France?")
    print(f"Response: {response[:200]}...")

    # Show performance
    print("\n" + agent.get_performance_report())