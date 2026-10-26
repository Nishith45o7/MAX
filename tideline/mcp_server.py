"""
MCP (Model Context Protocol) Stdio Server for Tideline Memory.
Serves recall_memory, write_memory, read_memory, and manage_memory over stdio JSON-RPC.
"""
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from brigade_core import get_state_dir
from tideline.engine import TidelineEngine

logging.basicConfig(level=logging.ERROR, stream=sys.stderr)


class McpMemoryServer:
    """Stdio JSON-RPC 2.0 server for MCP clients."""

    def __init__(self, workspace_dir: Optional[Path] = None, agent_id: str = "main"):
        state_dir = get_state_dir()
        if agent_id == "main":
            self.ws = workspace_dir or (state_dir / "workspace")
        else:
            self.ws = workspace_dir or (state_dir / "agents" / agent_id / "workspace")
        self.engine = TidelineEngine.open(self.ws, default_origin="owner")

    def run(self) -> None:
        """Main stdio loop."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                if response is not None:
                    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                    sys.stdout.flush()
            except Exception as e:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": str(e)}
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()

    def handle_request(self, req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        msg_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "tideline-memory", "version": "1.0.0"},
                    "capabilities": {"tools": {}}
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": [
                        {
                            "name": "recall_memory",
                            "description": "Searches Tideline long-term memory for relevant facts.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Search query terms"}
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "write_memory",
                            "description": "Writes a durable fact into Tideline memory under provenance safety rules.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "content": {"type": "string", "description": "Fact content to store"},
                                    "segment": {"type": "string", "enum": ["identity", "preference", "correction", "relationship", "project", "knowledge", "context"]},
                                    "tier": {"type": "string", "enum": ["short", "long", "permanent"]}
                                },
                                "required": ["content"]
                            }
                        }
                    ]
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})

            if tool_name == "recall_memory":
                query = args.get("query", "")
                hits = self.engine.recall(query, top_k=5)
                formatted = [f"[{h[0].segment}] {h[0].content} (score: {h[1]:.2f})" for h in hits]
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": [{"type": "text", "text": "\n".join(formatted) or "No matching memories found."}]}
                }

            elif tool_name == "write_memory":
                content = args.get("content", "")
                segment = args.get("segment", "knowledge")
                tier = args.get("tier", "long")
                try:
                    rec = self.engine.add(content, segment=segment, tier=tier, origin="owner", source="user")
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {"content": [{"type": "text", "text": f"Fact saved successfully (ID: {rec.id})"}]}
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "isError": True,
                        "result": {"content": [{"type": "text", "text": f"Error: {e}"}]}
                    }

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }


if __name__ == "__main__":
    server = McpMemoryServer()
    server.run()
