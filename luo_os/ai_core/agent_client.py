#!/usr/bin/env python3
"""
Luo OS Agent Client — Example of how any AI agent connects to Luo OS
Created by Luo Kai (luokai25)
"""

import socket
import json

class LuoAgentClient:
    def __init__(self, host="127.0.0.1", port=7070):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.sock.connect((self.host, self.port))
        welcome = json.loads(self.sock.recv(4096).decode())
        print(f"Connected to Luo OS: {welcome['message']}")
        print(f"Agent ID: {welcome['agent_id']}")
        return welcome

    def send(self, action, **kwargs):
        cmd = {"action": action, **kwargs}
        self.sock.send((json.dumps(cmd) + "\n").encode())
        response = json.loads(self.sock.recv(4096).decode())
        return response

    def disconnect(self):
        self.sock.close()

# Example usage
if __name__ == "__main__":
    client = LuoAgentClient()
    client.connect()

    # Ping
    print(client.send("ping"))

    # Get system info
    print(client.send("system_info"))

    # List files
    print(client.send("list_files", path="/"))

    # Ask Luo AI a question
    print(client.send("ask_ai", prompt="What is Luo OS?"))

    client.disconnect()
