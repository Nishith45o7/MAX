"""
Tool Registry with Per-Call Ownership Gating and Schema Resolution.
Unifies coding, memory, documents, web research, connectors, subagents, and team collaboration.
"""
import json
from typing import Dict, Any, List, Optional, Callable
from tools.coding_tools import CodingTools
from tools.doc_tools import DocumentTools
from tools.web_tools import WebTools
from tools.composio_tool import ComposioTool


class ToolRegistry:
    """Central registry for all agent tools with ownership enforcement."""

    def __init__(self, coding_tools: Optional[CodingTools] = None, doc_tools: Optional[DocumentTools] = None):
        self.coding_tools = coding_tools or CodingTools()
        self.doc_tools = doc_tools or DocumentTools()
        self.web_tools = WebTools()
        self.composio_tool = ComposioTool()
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._register_builtins()

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable[..., Any],
        owner_only: bool = False
    ) -> None:
        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": handler,
            "owner_only": owner_only
        }

    def _register_builtins(self) -> None:
        # Coding Tools
        self.register(
            "read",
            "Reads lines from a file path with optional offset and limit.",
            {"type": "object", "properties": {"path": {"type": "string"}, "offset": {"type": "integer"}, "limit": {"type": "integer"}}, "required": ["path"]},
            self.coding_tools.read,
            owner_only=False
        )
        self.register(
            "write",
            "Writes text content to a file at path.",
            {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
            self.coding_tools.write,
            owner_only=True
        )
        self.register(
            "edit",
            "Replaces exact old_text with new_text in file at path.",
            {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]},
            self.coding_tools.edit,
            owner_only=True
        )
        self.register(
            "bash",
            "Runs a terminal/shell command under security approvals.",
            {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
            self.coding_tools.bash,
            owner_only=True
        )
        self.register(
            "ls",
            "Lists entries in a directory.",
            {"type": "object", "properties": {"directory": {"type": "string"}}},
            self.coding_tools.ls,
            owner_only=False
        )
        self.register(
            "find",
            "Searches for files matching glob pattern in a directory.",
            {"type": "object", "properties": {"directory": {"type": "string"}, "pattern": {"type": "string"}}},
            self.coding_tools.find,
            owner_only=False
        )

        # Web Tools
        self.register(
            "web_search",
            "Searches the web for information using search engine.",
            {"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer"}}, "required": ["query"]},
            self.web_tools.web_search,
            owner_only=False
        )
        self.register(
            "fetch_url",
            "Fetches and extracts clean markdown/text from a web page.",
            {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
            self.web_tools.fetch_url,
            owner_only=False
        )

        # Document Tools
        self.register(
            "analyze_media",
            "Understands and extracts content from PDF, Office docs (.docx, .xlsx, .pptx), images, audio, video.",
            {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            self.doc_tools.analyze_media,
            owner_only=False
        )
        self.register(
            "make_document",
            "Creates a Word (.docx), Presentation (.pptx), PDF, or text file.",
            {"type": "object", "properties": {"doc_type": {"type": "string", "enum": ["pdf", "pptx", "txt"]}, "path": {"type": "string"}, "title": {"type": "string"}, "content": {"type": "string"}}, "required": ["doc_type", "path", "title", "content"]},
            self.doc_tools.make_document,
            owner_only=True
        )

        # Composio Connector Tool
        self.register(
            "composio",
            "Executes an action via Composio 1,000+ app connectors (Gmail, GitHub, Slack, Notion, Calendar).",
            {"type": "object", "properties": {"action_name": {"type": "string"}, "params": {"type": "object"}}, "required": ["action_name", "params"]},
            self.composio_tool.execute_action,
            owner_only=True
        )

    def get_definitions(self, is_owner: bool = True) -> List[Dict[str, Any]]:
        """Returns tool schema definitions, filtering owner_only tools for peers."""
        defs = []
        for name, t in self._tools.items():
            if t["owner_only"] and not is_owner:
                continue
            defs.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"]
                }
            })
        return defs

    def execute(self, tool_name: str, args: Dict[str, Any], is_owner: bool = True) -> str:
        """Dispatches tool execution with ownership validation."""
        tool = self._tools.get(tool_name)
        if not tool:
            return f"Error: Tool '{tool_name}' not found."

        if tool["owner_only"] and not is_owner:
            return f"Permission Denied: Tool '{tool_name}' is restricted to the system owner."

        handler = tool["handler"]
        try:
            res = handler(**args)
            if isinstance(res, (dict, list)):
                return json.dumps(res, indent=2, ensure_ascii=False)
            return str(res)
        except Exception as e:
            return f"Error executing '{tool_name}': {e}"
