#!/usr/bin/env python3
"""
Luo OS AI Memory System
Luo AI remembers conversations across sessions
Created by Luo Kai (luokai25)
"""

import json
import os
from datetime import datetime

MEMORY_DIR = os.path.expanduser("~/.luo_memory")
MEMORY_FILE = os.path.join(MEMORY_DIR, "memory.json")
FACTS_FILE = os.path.join(MEMORY_DIR, "facts.json")
MAX_MEMORY = 1000

def init():
    os.makedirs(MEMORY_DIR, exist_ok=True)
    if not os.path.exists(MEMORY_FILE):
        save_memory([])
    if not os.path.exists(FACTS_FILE):
        save_facts({})

def load_memory():
    init()
    with open(MEMORY_FILE) as f:
        return json.load(f)

def save_memory(memory):
    os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def load_facts():
    init()
    with open(FACTS_FILE) as f:
        return json.load(f)

def save_facts(facts):
    os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(FACTS_FILE, "w") as f:
        json.dump(facts, f, indent=2)

def remember(user_input, ai_response, agent_id="luo_ai"):
    memory = load_memory()
    entry = {
        "id": len(memory) + 1,
        "time": datetime.now().isoformat(),
        "agent": agent_id,
        "user": user_input,
        "ai": ai_response
    }
    memory.append(entry)
    if len(memory) > MAX_MEMORY:
        memory = memory[-MAX_MEMORY:]
    save_memory(memory)
    return entry

def recall(query=None, limit=10):
    memory = load_memory()
    if query:
        memory = [m for m in memory if query.lower() in m["user"].lower() or query.lower() in m["ai"].lower()]
    return memory[-limit:]

def learn_fact(key, value):
    facts = load_facts()
    facts[key] = {"value": value, "learned": datetime.now().isoformat()}
    save_facts(facts)
    return facts[key]

def get_fact(key):
    facts = load_facts()
    return facts.get(key)

def get_all_facts():
    return load_facts()

def forget(entry_id):
    memory = load_memory()
    memory = [m for m in memory if m["id"] != entry_id]
    save_memory(memory)

def forget_all():
    save_memory([])
    save_facts({})

def get_context(limit=5):
    """Get recent memory as context string for AI"""
    memory = recall(limit=limit)
    if not memory:
        return ""
    lines = []
    for m in memory:
        lines.append(f"User: {m['user']}")
        lines.append(f"Luo AI: {m['ai']}")
    return "\n".join(lines)

def stats():
    memory = load_memory()
    facts = load_facts()
    return {
        "total_conversations": len(memory),
        "total_facts": len(facts),
        "oldest": memory[0]["time"] if memory else None,
        "newest": memory[-1]["time"] if memory else None,
        "memory_file": MEMORY_FILE
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "stats":
            print(json.dumps(stats(), indent=2))
        elif cmd == "recall":
            query = sys.argv[2] if len(sys.argv) > 2 else None
            for m in recall(query=query):
                print(f"[{m['time']}] You: {m['user']}")
                print(f"           AI: {m['ai']}\n")
        elif cmd == "facts":
            print(json.dumps(get_all_facts(), indent=2))
        elif cmd == "learn":
            key, val = sys.argv[2], sys.argv[3]
            learn_fact(key, val)
            print(f"Learned: {key} = {val}")
        elif cmd == "forget":
            forget_all()
            print("Memory cleared.")
    else:
        print("Usage: python3 memory.py [stats|recall|facts|learn|forget]")
