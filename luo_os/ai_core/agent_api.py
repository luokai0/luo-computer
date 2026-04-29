#!/usr/bin/env python3
"""
Luo OS AI Agent API — Port 7070
Any AI agent in the world can connect and control Luo OS
Created by Luo Kai (luokai25)
"""

import json
import socket
import threading
import subprocess
import os
from datetime import datetime

HOST = "0.0.0.0"
PORT = 7070
VERSION = "0.1"

class LuoAgentAPI:
    def __init__(self):
        self.agents = {}
        self.log = []
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def handle_command(self, cmd, agent_id):
        """Process commands from AI agents"""
        action = cmd.get("action", "")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.append({"time": timestamp, "agent": agent_id, "action": action})

        if action == "ping":
            return {"status": "ok", "message": "Luo OS alive", "version": VERSION}

        elif action == "system_info":
            info = os.uname()
            return {
                "status": "ok",
                "os": "Luo OS",
                "version": VERSION,
                "kernel": info.release,
                "arch": info.machine,
                "creator": "Luo Kai (luokai25)"
            }

        elif action == "list_files":
            path = cmd.get("path", "/")
            try:
                files = os.listdir(path)
                return {"status": "ok", "path": path, "files": files}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "read_file":
            path = cmd.get("path", "")
            try:
                with open(path, "r") as f:
                    return {"status": "ok", "content": f.read()}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "write_file":
            path = cmd.get("path", "")
            content = cmd.get("content", "")
            try:
                with open(path, "w") as f:
                    f.write(content)
                return {"status": "ok", "message": f"Written to {path}"}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "run_command":
            command = cmd.get("command", "")
            try:
                result = subprocess.run(
                    command, shell=True,
                    capture_output=True, text=True, timeout=10
                )
                return {
                    "status": "ok",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "ask_ai":
            prompt = cmd.get("prompt", "")
            try:
                import urllib.request
                payload = json.dumps({
                    "model": "tinyllama",
                    "prompt": f"You are Luo AI. {prompt}",
                    "stream": False,
                    "options": {"num_predict": 80}
                }).encode()
                req = urllib.request.Request(
                    "http://127.0.0.1:3000/api/chat",
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=120) as r:
                    result = json.loads(r.read())
                    return {"status": "ok", "response": result.get("response", "").strip()}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "get_log":
            return {"status": "ok", "log": self.log[-20:]}

        elif action == "list_agents":
            return {"status": "ok", "agents": list(self.agents.keys())}

        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def handle_client(self, conn, addr):
        agent_id = f"agent_{addr[0]}_{addr[1]}"
        self.agents[agent_id] = {"addr": addr, "connected": datetime.now().isoformat()}
        print(f"[Luo API] Agent connected: {agent_id}")

        # Send welcome
        welcome = {
            "status": "connected",
            "message": "Welcome to Luo OS Agent API",
            "version": VERSION,
            "agent_id": agent_id,
            "actions": ["ping", "system_info", "list_files", "read_file",
                       "write_file", "run_command", "ask_ai", "get_log", "list_agents"]
        }
        conn.send((json.dumps(welcome) + "\n").encode())

        try:
            while True:
                data = conn.recv(4096).decode().strip()
                if not data:
                    break
                try:
                    cmd = json.loads(data)
                    response = self.handle_command(cmd, agent_id)
                    conn.send((json.dumps(response) + "\n").encode())
                except json.JSONDecodeError:
                    conn.send((json.dumps({"status": "error", "message": "Invalid JSON"}) + "\n").encode())
        except:
            pass
        finally:
            del self.agents[agent_id]
            conn.close()
            print(f"[Luo API] Agent disconnected: {agent_id}")

    def run(self):
        self.server.bind((HOST, PORT))
        self.server.listen(10)
        print(f"╔══════════════════════════════════════╗")
        print(f"║   Luo OS AI Agent API v{VERSION}           ║")
        print(f"║   Listening on port {PORT}            ║")
        print(f"║   Free for all AI Agents             ║")
        print(f"╚══════════════════════════════════════╝")
        while True:
            try:
                conn, addr = self.server.accept()
                thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                thread.daemon = True
                thread.start()
            except Exception as e:
                print(f"[Luo API] Error: {e}")

if __name__ == "__main__":
    api = LuoAgentAPI()
    api.run()
