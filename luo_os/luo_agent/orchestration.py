#!/usr/bin/env python3
"""
LuoOS Multi-Agent Orchestration System
======================================
Specialized agents that can collaborate on complex tasks.

Agents:
- Planner: Breaks down complex tasks into steps
- Researcher: Gathers information and analyzes
- Coder: Writes and debugs code
- Reviewer: Reviews outputs for quality
- Executor: Executes tasks and reports results

Created by Luo Kai (luokai25) — Enhanced by Claude Code
"""
import json
import threading
import time
import urllib.request
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class AgentRole(Enum):
    PLANNER = "planner"
    RESEARCHER = "researcher"
    CODER = "coder"
    REVIEWER = "reviewer"
    EXECUTOR = "executor"
    GENERALIST = "generalist"


@dataclass
class Task:
    """A task to be processed by an agent."""
    id: str
    description: str
    role: AgentRole = AgentRole.GENERALIST
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[str] = None
    assigned_to: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


@dataclass
class AgentState:
    """State of an agent."""
    id: str
    role: AgentRole
    status: str = "idle"  # idle, busy, waiting
    current_task: Optional[str] = None
    completed_tasks: int = 0
    history: List[Dict] = field(default_factory=list)


class SpecialistAgent:
    """
    A specialist agent with a specific role.
    """

    ROLE_PROMPTS = {
        AgentRole.PLANNER: """You are a Planning Agent. Your role is to:
1. Analyze complex tasks
2. Break them into clear, sequential steps
3. Identify dependencies between steps
4. Estimate difficulty and time for each step
5. Consider potential blockers

Output format:
STEP 1: [action] - [expected outcome]
STEP 2: [action] - [expected outcome]
...

Be thorough and consider edge cases.""",

        AgentRole.RESEARCHER: """You are a Research Agent. Your role is to:
1. Search for relevant information
2. Analyze findings
3. Synthesize key insights
4. Cite sources when possible
5. Identify knowledge gaps

Be thorough and provide evidence-based conclusions.""",

        AgentRole.CODER: """You are a Coding Agent. Your role is to:
1. Write clean, efficient code
2. Follow best practices
3. Include error handling
4. Add appropriate comments
5. Consider edge cases

Write working code that is readable and maintainable.""",

        AgentRole.REVIEWER: """You are a Review Agent. Your role is to:
1. Analyze outputs for correctness
2. Check for edge cases and bugs
3. Evaluate code quality
4. Suggest improvements
5. Verify requirements are met

Be constructive and specific in feedback.""",

        AgentRole.EXECUTOR: """You are an Execution Agent. Your role is to:
1. Execute tasks precisely
2. Report results clearly
3. Handle errors gracefully
4. Track progress
5. Confirm completion

Be reliable and thorough in execution.""",

        AgentRole.GENERALIST: """You are a General Agent. Your role is to:
1. Handle a variety of tasks
2. Adapt your approach to the task
3. Provide clear responses
4. Ask clarifying questions when needed
5. Deliver quality results

Be flexible and capable across domains.""",
    }

    def __init__(
        self,
        role: AgentRole,
        luokai_url: str = "http://localhost:3000",
        model: str = None,
        agent_id: str = None
    ):
        self.id = agent_id or str(uuid.uuid4())[:8]
        self.role = role
        self.luokai_url = luokai_url
        self.model = model or "mistral"
        self.state = AgentState(id=self.id, role=role)
        self._lock = threading.Lock()

        print(f"[Agent {self.id}] Created as {role.value}")

    def process(self, task: Task) -> str:
        """Process a task and return the result."""
        with self._lock:
            self.state.status = "busy"
            self.state.current_task = task.id

        try:
            # Build prompt based on role
            system_prompt = self.ROLE_PROMPTS.get(self.role, self.ROLE_PROMPTS[AgentRole.GENERALIST])
            full_prompt = f"{system_prompt}\n\nTask: {task.description}"

            # Call the LLM
            result = self._call_luokai(full_prompt)

            # Record in history
            self.state.history.append({
                "task_id": task.id,
                "task": task.description,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            self.state.completed_tasks += 1

            return result

        finally:
            with self._lock:
                self.state.status = "idle"
                self.state.current_task = None

    def _call_luokai(self, prompt: str, max_tokens: int = 1024) -> str:
        """Call LUOKAI native inference."""
        messages = [
            {"role": "system", "content": self.ROLE_PROMPTS.get(self.role, "")},
            {"role": "user", "content": prompt}
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": 0.7}
        }

        try:
            req = urllib.request.Request(
                f"{self.luokai_url}/api/chat",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                try:
                    data = json.loads(r.read())
                except (json.JSONDecodeError, ValueError):
                    data = {}
                return data.get("message", {}).get("content", "").strip()
        except Exception as e:
            return f"[ERROR] {e}"


class MultiAgentOrchestrator:
    """
    Orchestrates multiple specialized agents working together.
    """

    def __init__(self, luokai_url: str = "http://localhost:3000", model: str = None):
        self.luokai_url = luokai_url
        self.model = model
        self.agents: Dict[str, SpecialistAgent] = {}
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[Task] = []
        self.results: Dict[str, str] = {}
        self._lock = threading.Lock()

        # Create default agents
        self._create_default_agents()

        print(f"[Orchestrator] Initialized with {len(self.agents)} agents")

    def _create_default_agents(self):
        """Create the default set of specialist agents."""
        for role in AgentRole:
            agent = SpecialistAgent(
                role=role,
                luokai_url=self.luokai_url,
                model=self.model
            )
            self.agents[agent.id] = agent

    def create_task(
        self,
        description: str,
        role: AgentRole = AgentRole.GENERALIST,
        dependencies: List[str] = None
    ) -> Task:
        """Create a new task."""
        task = Task(
            id=str(uuid.uuid4())[:8],
            description=description,
            role=role,
            dependencies=dependencies or []
        )
        self.tasks[task.id] = task
        return task

    def assign_task(self, task: Task) -> str:
        """Assign a task to the best available agent."""
        # Find agent with matching role
        for agent_id, agent in self.agents.items():
            if agent.role == task.role and agent.state.status == "idle":
                task.assigned_to = agent_id
                task.status = "in_progress"
                return agent_id

        # Fall back to generalist
        for agent_id, agent in self.agents.items():
            if agent.role == AgentRole.GENERALIST and agent.state.status == "idle":
                task.assigned_to = agent_id
                task.status = "in_progress"
                return agent_id

        return None  # No available agent

    def execute_task(self, task_id: str) -> str:
        """Execute a specific task."""
        task = self.tasks.get(task_id)
        if not task:
            return f"[ERROR] Task {task_id} not found"

        # Check dependencies
        for dep_id in task.dependencies:
            if dep_id not in self.results:
                return f"[ERROR] Dependency {dep_id} not completed"

        # Assign to agent
        agent_id = self.assign_task(task)
        if not agent_id:
            return "[ERROR] No available agent"

        agent = self.agents[agent_id]
        result = agent.process(task)

        # Record result
        task.result = result
        task.status = "completed"
        task.completed_at = datetime.now().isoformat()
        self.results[task.id] = result

        return result

    def execute_parallel(self, task_ids: List[str]) -> Dict[str, str]:
        """Execute multiple tasks in parallel."""
        results = {}
        threads = []

        def run_task(tid):
            results[tid] = self.execute_task(tid)

        for task_id in task_ids:
            t = threading.Thread(target=run_task, args=(task_id,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        return results

    def plan_and_execute(self, goal: str) -> Dict[str, Any]:
        """
        Plan and execute a complex goal using specialist agents.

        This is the main entry point for complex multi-step tasks.
        """
        print(f"[Orchestrator] Planning execution for: {goal}")

        # 1. Planner breaks down the goal
        planner_id = self._get_agent_by_role(AgentRole.PLANNER)
        if not planner_id:
            return {"error": "No planner available"}

        planner = self.agents[planner_id]
        plan_task = self.create_task(
            description=f"Create a detailed plan to: {goal}",
            role=AgentRole.PLANNER
        )

        plan_result = planner.process(plan_task)
        print(f"[Orchestrator] Plan created:\n{plan_result[:500]}...")

        # 2. Parse plan into tasks
        tasks = self._parse_plan_to_tasks(plan_result)

        # 3. Execute tasks in order (respecting dependencies)
        execution_results = []
        for task in tasks:
            print(f"[Orchestrator] Executing: {task.description[:50]}...")
            result = self.execute_task(task.id)
            execution_results.append({
                "task": task.description,
                "role": task.role.value,
                "result": result
            })

        # 4. Reviewer checks results
        reviewer_id = self._get_agent_by_role(AgentRole.REVIEWER)
        if reviewer_id:
            reviewer = self.agents[reviewer_id]
            review_task = self.create_task(
                description=f"Review these execution results for completeness and quality:\n{json.dumps(execution_results, indent=2)}",
                role=AgentRole.REVIEWER
            )
            review_result = reviewer.process(review_task)
        else:
            review_result = "No reviewer available"

        return {
            "goal": goal,
            "plan": plan_result,
            "execution": execution_results,
            "review": review_result,
            "success": all(r["result"] and not r["result"].startswith("[ERROR]") for r in execution_results)
        }

    def _get_agent_by_role(self, role: AgentRole) -> Optional[str]:
        """Get an agent ID by role."""
        for agent_id, agent in self.agents.items():
            if agent.role == role:
                return agent_id
        return None

    def _parse_plan_to_tasks(self, plan: str) -> List[Task]:
        """Parse a plan text into tasks."""
        tasks = []
        lines = plan.strip().split('\n')

        for line in lines:
            # Look for numbered steps
            if line.strip() and (line.strip().startswith(('STEP', 'Step', '1.', '2.', '3.', '4.', '5.', '-'))):
                description = line.strip()

                # Infer role from content
                role = AgentRole.GENERALIST
                lower_desc = description.lower()
                if 'research' in lower_desc or 'find' in lower_desc or 'search' in lower_desc:
                    role = AgentRole.RESEARCHER
                elif 'code' in lower_desc or 'write' in lower_desc or 'implement' in lower_desc:
                    role = AgentRole.CODER
                elif 'review' in lower_desc or 'check' in lower_desc or 'verify' in lower_desc:
                    role = AgentRole.REVIEWER
                elif 'execute' in lower_desc or 'run' in lower_desc or 'perform' in lower_desc:
                    role = AgentRole.EXECUTOR

                task = self.create_task(description=description, role=role)
                tasks.append(task)

        return tasks if tasks else [self.create_task(description=plan, role=AgentRole.GENERALIST)]

    def get_status(self) -> Dict:
        """Get status of all agents."""
        return {
            "agents": {
                agent_id: {
                    "role": agent.role.value,
                    "status": agent.state.status,
                    "completed_tasks": agent.state.completed_tasks
                }
                for agent_id, agent in self.agents.items()
            },
            "total_tasks": len(self.tasks),
            "completed_tasks": len(self.results),
            "pending_tasks": len([t for t in self.tasks.values() if t.status == "pending"])
        }


# Convenience function
def create_orchestrator(luokai_url: str = "http://localhost:3000", model: str = None) -> MultiAgentOrchestrator:
    """Create a multi-agent orchestrator."""
    return MultiAgentOrchestrator(luokai_url=luokai_url, model=model)


if __name__ == "__main__":
    # Test the orchestrator
    orch = create_orchestrator()

    print("\nOrchestrator status:")
    print(json.dumps(orch.get_status(), indent=2))

    # Test a simple task
    print("\nTesting task assignment...")
    task = orch.create_task(
        description="Explain what makes a good API design",
        role=AgentRole.GENERALIST
    )
    result = orch.execute_task(task.id)
    print(f"Result: {result[:200]}...")