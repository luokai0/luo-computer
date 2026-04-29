#!/usr/bin/env python3
"""
Luo OS Multi-Agent System
AI agents can spawn, manage and communicate with sub-agents
Created by Luo Kai (luokai25)
"""

import json
import threading
import time
import uuid
import urllib.request
from datetime import datetime

class LuoAgent:
    def __init__(self, name, role, parent=None):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.role = role
        self.parent = parent
        self.children = []
        self.memory = []
        self.status = "idle"
        self.created = datetime.now().isoformat()

    def think(self, prompt):
        self.status = "thinking"
        try:
            full_prompt = f"You are {self.name}, a {self.role} agent in Luo OS. {prompt}"
            payload = json.dumps({
                "model": "tinyllama",
                "prompt": full_prompt,
                "stream": False,
                "options": {"num_predict": 60}
            }).encode()
            req = urllib.request.Request(
                "http://127.0.0.1:3000/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                result = json.loads(r.read())
                response = result.get("response", "").strip()
                self.memory.append({"prompt": prompt, "response": response, "time": datetime.now().isoformat()})
                self.status = "idle"
                return response
        except Exception as e:
            self.status = "error"
            return f"Error: {e}"

    def spawn_child(self, name, role):
        child = LuoAgent(name, role, parent=self.id)
        self.children.append(child)
        print(f"[{self.name}] Spawned sub-agent: {name} ({role})")
        return child

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "parent": self.parent,
            "children": [c.id for c in self.children],
            "memory_count": len(self.memory),
            "created": self.created
        }

class LuoAgentManager:
    def __init__(self):
        self.agents = {}
        self.root = self.create_agent("Luo Prime", "orchestrator")
        print(f"[Multi-Agent] System initialized — Root: {self.root.name} ({self.root.id})")

    def create_agent(self, name, role, parent_id=None):
        agent = LuoAgent(name, role, parent=parent_id)
        self.agents[agent.id] = agent
        return agent

    def spawn_agent(self, parent_id, name, role):
        parent = self.agents.get(parent_id)
        if not parent:
            return None
        child = parent.spawn_child(name, role)
        self.agents[child.id] = child
        return child

    def get_agent(self, agent_id):
        return self.agents.get(agent_id)

    def list_agents(self):
        return [a.to_dict() for a in self.agents.values()]

    def broadcast(self, prompt):
        """Send same prompt to all idle agents"""
        results = {}
        threads = []

        def ask(agent):
            results[agent.name] = agent.think(prompt)

        for agent in self.agents.values():
            if agent.status == "idle":
                t = threading.Thread(target=ask, args=(agent,))
                threads.append(t)
                t.start()

        for t in threads:
            t.join(timeout=130)

        return results

    def run_demo(self):
        print("\n[Multi-Agent] Running demo...\n")

        # Root spawns sub-agents
        researcher = self.spawn_agent(self.root.id, "Researcher", "research and analysis")
        builder = self.spawn_agent(self.root.id, "Builder", "code writing and building")
        monitor = self.spawn_agent(self.root.id, "Monitor", "system monitoring")

        print(f"\nAgents created: {len(self.agents)}")
        for a in self.list_agents():
            print(f"  - {a['name']} ({a['role']}) [{a['id']}]")

        print(f"\n[Demo] Asking all agents: 'What is your role in Luo OS?'")
        results = self.broadcast("What is your role in Luo OS? Answer in one sentence.")

        print("\n[Responses]")
        for name, response in results.items():
            print(f"  {name}: {response}\n")

if __name__ == "__main__":
    manager = LuoAgentManager()
    manager.run_demo()
