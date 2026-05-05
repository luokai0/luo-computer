#!/usr/bin/env python3
"""
LUOKAI MCP (Model Context Protocol) Integration
================================================
Implements the Model Context Protocol for tool and context integration.

MCP allows LUOKAI to:
- Discover and use tools from MCP servers
- Share context with other agents
- Access resources through standardized interfaces

Based on Anthropic's MCP specification.

Created by Luo Kai (luokai25) — Enhanced by Claude Code
"""
import json
import subprocess
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from pathlib import Path
import urllib.request
import urllib.error


@dataclass
class MCPTool:
    """A tool exposed by an MCP server."""
    name: str
    description: str
    input_schema: Dict
    server_name: str

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "server_name": self.server_name
        }


@dataclass
class MCPResource:
    """A resource exposed by an MCP server."""
    uri: str
    name: str
    description: str
    mime_type: Optional[str] = None
    server_name: str = ""


@dataclass
class MCPServer:
    """An MCP server connection."""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    tools: List[MCPTool] = field(default_factory=list)
    resources: List[MCPResource] = field(default_factory=list)
    _process: Any = field(default=None, repr=False)
    _connected: bool = False


class MCPClient:
    """
    Client for connecting to MCP servers and using their tools.

    MCP (Model Context Protocol) provides a standardized way for AI models
    to discover and use tools, access resources, and share context.

    Usage:
        client = MCPClient()
        client.connect_server("filesystem", "mcp-filesystem", ["/path/to/dir"])
        tools = client.list_tools()
        result = client.call_tool("filesystem", "read_file", {"path": "test.txt"})
    """

    def __init__(self, model: str = "mistral"):
        self.model = model
        self.servers: Dict[str, MCPServer] = {}
        self._lock = threading.Lock()

    def connect_server(
        self,
        name: str,
        command: str,
        args: List[str] = None,
        env: Dict[str, str] = None
    ) -> bool:
        """
        Connect to an MCP server.

        Args:
            name: Friendly name for the server
            command: Command to run (e.g., "mcp-filesystem")
            args: Arguments for the command
            env: Environment variables

        Returns:
            True if connection successful
        """
        try:
            server = MCPServer(
                name=name,
                command=command,
                args=args or [],
                env=env or {}
            )

            # Start the server process
            server._process = subprocess.Popen(
                [command] + (args or []),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**server.env}
            )

            # Initialize connection
            self._initialize_server(server)

            server._connected = True
            self.servers[name] = server

            print(f"[MCP] Connected to server: {name}")
            print(f"[MCP]   Tools: {len(server.tools)}")
            print(f"[MCP]   Resources: {len(server.resources)}")

            return True

        except Exception as e:
            print(f"[MCP] Failed to connect to {name}: {e}")
            return False

    def _initialize_server(self, server: MCPServer) -> None:
        """Initialize MCP server and discover tools/resources."""
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {}
                },
                "clientInfo": {
                    "name": "LUOKAI",
                    "version": "2.0"
                }
            }
        }

        response = self._send_request(server, init_request)

        # List tools
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        tools_response = self._send_request(server, tools_request)

        if tools_response and "result" in tools_response:
            for tool_data in tools_response["result"].get("tools", []):
                tool = MCPTool(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {}),
                    server_name=server.name
                )
                server.tools.append(tool)

        # List resources
        resources_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "resources/list"
        }
        resources_response = self._send_request(server, resources_request)

        if resources_response and "result" in resources_response:
            for res_data in resources_response["result"].get("resources", []):
                resource = MCPResource(
                    uri=res_data["uri"],
                    name=res_data.get("name", ""),
                    description=res_data.get("description", ""),
                    mime_type=res_data.get("mimeType"),
                    server_name=server.name
                )
                server.resources.append(resource)

    def _send_request(self, server: MCPServer, request: Dict) -> Optional[Dict]:
        """Send a JSON-RPC request to the server."""
        try:
            request_str = json.dumps(request) + "\n"
            server._process.stdin.write(request_str.encode())
            server._process.stdin.flush()

            # Read response
            response_line = server._process.stdout.readline().decode()
            return json.loads(response_line)

        except Exception as e:
            print(f"[MCP] Request error: {e}")
            return None

    def list_tools(self, server_name: str = None) -> List[MCPTool]:
        """List all available tools, optionally filtered by server."""
        if server_name and server_name in self.servers:
            return self.servers[server_name].tools

        all_tools = []
        for server in self.servers.values():
            all_tools.extend(server.tools)
        return all_tools

    def list_resources(self, server_name: str = None) -> List[MCPResource]:
        """List all available resources, optionally filtered by server."""
        if server_name and server_name in self.servers:
            return self.servers[server_name].resources

        all_resources = []
        for server in self.servers.values():
            all_resources.extend(server.resources)
        return all_resources

    def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """Call a tool on an MCP server."""
        if server_name not in self.servers:
            return {"error": f"Server {server_name} not connected"}

        server = self.servers[server_name]

        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        response = self._send_request(server, request)

        if response and "result" in response:
            return response["result"]

        return {"error": response.get("error", "Unknown error")}

    def read_resource(self, server_name: str, uri: str) -> Any:
        """Read a resource from an MCP server."""
        if server_name not in self.servers:
            return {"error": f"Server {server_name} not connected"}

        server = self.servers[server_name]

        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "resources/read",
            "params": {
                "uri": uri
            }
        }

        response = self._send_request(server, request)

        if response and "result" in response:
            return response["result"]

        return {"error": response.get("error", "Unknown error")}

    def disconnect_server(self, server_name: str) -> bool:
        """Disconnect from an MCP server."""
        if server_name not in self.servers:
            return False

        server = self.servers[server_name]

        try:
            if server._process:
                server._process.terminate()
                server._process.wait(timeout=5)
        except Exception:
            pass

        del self.servers[server_name]
        return True

    def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        for name in list(self.servers.keys()):
            self.disconnect_server(name)

    def get_tools_description(self) -> str:
        """Get a formatted description of all tools for LLM prompting."""
        lines = ["Available MCP Tools:"]

        for server_name, server in self.servers.items():
            for tool in server.tools:
                lines.append(f"  - {tool.name} ({server_name}): {tool.description}")

        return "\n".join(lines)

    def auto_call_tools(
        self,
        user_message: str,
        system_prompt: str = None
    ) -> str:
        """
        Automatically determine which tools to call based on user message,
        then call them and return results.

        This uses the LLM to analyze which tools are relevant.
        """
        # Get all tools
        tools = self.list_tools()
        if not tools:
            return user_message

        # Build tool descriptions
        tool_desc = "\n".join([
            f"- {t.name} ({t.server_name}): {t.description}"
            for t in tools
        ])

        # Ask LLM which tools to call
        analysis_prompt = f"""Given this user message and available tools, determine which tools should be called.

User message: {user_message}

Available tools:
{tool_desc}

If no tools are relevant, respond with: NONE
If tools are relevant, respond with JSON array of tool calls:
[{{"server": "server_name", "tool": "tool_name", "args": {{...}}}}]

Respond with ONLY the JSON array or NONE."""

        try:
            response = self._call_llm(analysis_prompt)

            if response.strip() == "NONE":
                return user_message

            # Parse tool calls
            import json
            tool_calls = json.loads(response)

            results = []
            for call in tool_calls:
                server = call.get("server")
                tool = call.get("tool")
                args = call.get("args", {})

                if server and tool:
                    result = self.call_tool(server, tool, args)
                    results.append(f"Tool {tool} result: {result}")

            # Augment user message with tool results
            if results:
                return f"{user_message}\n\nTool results:\n" + "\n".join(results)

        except Exception as e:
            print(f"[MCP] Auto-call error: {e}")

        return user_message

    def _call_llm(self, prompt: str, max_tokens: int = 256) -> str:
        """Call the LLM."""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": 0.3}
        }

        try:
            req = urllib.request.Request(
                "luokai://inference",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
                return data.get("message", {}).get("content", "").strip()
        except Exception as e:
            return f"Error: {e}"

    def status(self) -> Dict:
        """Get MCP client status."""
        return {
            "servers_connected": len(self.servers),
            "servers": {
                name: {
                    "connected": server._connected,
                    "tools": len(server.tools),
                    "resources": len(server.resources)
                }
                for name, server in self.servers.items()
            },
            "total_tools": sum(len(s.tools) for s in self.servers.values()),
            "total_resources": sum(len(s.resources) for s in self.servers.values())
        }


# Popular MCP server configurations
MCP_SERVER_CONFIGS = {
    "filesystem": {
        "command": "mcp-filesystem",
        "description": "File system operations"
    },
    "github": {
        "command": "mcp-github",
        "description": "GitHub API integration"
    },
    "postgres": {
        "command": "mcp-postgres",
        "description": "PostgreSQL database"
    },
    "sqlite": {
        "command": "mcp-sqlite",
        "description": "SQLite database"
    },
    "brave-search": {
        "command": "mcp-brave-search",
        "description": "Web search via Brave"
    },
    "puppeteer": {
        "command": "mcp-puppeteer",
        "description": "Browser automation"
    },
    "memory": {
        "command": "mcp-memory",
        "description": "Persistent memory"
    },
    "fetch": {
        "command": "mcp-fetch",
        "description": "HTTP requests"
    }
}


def create_mcp_client(model: str = "mistral") -> MCPClient:
    """Create an MCP client."""
    return MCPClient(model=model)


if __name__ == "__main__":
    print("LUOKAI MCP Client")
    print("=" * 50)

    client = MCPClient()
    print("\nMCP Server Configurations Available:")
    for name, config in MCP_SERVER_CONFIGS.items():
        print(f"  - {name}: {config['description']}")

    print("\nNote: Install MCP servers with: npm install -g mcp-server-name")
    print("\nExample usage:")
    print('  client.connect_server("filesystem", "mcp-filesystem", ["/path/to/dir"])')
    print('  tools = client.list_tools()')
    print('  result = client.call_tool("filesystem", "read_file", {"path": "test.txt"})')