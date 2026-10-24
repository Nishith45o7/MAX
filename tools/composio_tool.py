"""
Composio 1,000+ App Connectors and OAuth Authorization Tool.
Integrates with Gmail, GitHub, Slack, Notion, Google Calendar, Linear, etc.
"""
import os
import json
import urllib.request
from typing import Dict, Any, Optional
from brigade_core.config import ConfigManager


class ComposioTool:
    """Manages app connectors via Composio Platform API."""

    def __init__(self, config_mgr: Optional[ConfigManager] = None):
        self.config_mgr = config_mgr or ConfigManager()

    def get_api_key(self) -> Optional[str]:
        cfg = self.config_mgr.load_resolved()
        key = cfg.get("connectors", {}).get("composio_api_key") or os.environ.get("COMPOSIO_API_KEY")
        if key and key.startswith("ak_"):
            return key
        return None

    def execute_action(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a Composio action using the platform key."""
        api_key = self.get_api_key()
        if not api_key:
            return {
                "error": "Composio platform API key not configured. Set COMPOSIO_API_KEY or configure connectors.composio_api_key (must start with 'ak_')."
            }

        url = f"https://api.composio.dev/v1/actions/{action_name}/execute"
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        data = json.dumps({"params": params}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                res_body = resp.read().decode("utf-8")
                return json.loads(res_body)
        except Exception as e:
            return {"error": f"Composio execution failed: {e}"}

    def initiate_oauth(self, app_name: str, redirect_url: Optional[str] = None) -> Dict[str, Any]:
        """Initiates OAuth authorization for an app (e.g. 'github', 'gmail', 'notion')."""
        api_key = self.get_api_key()
        if not api_key:
            return {
                "error": "Composio platform API key missing. Connect with an 'ak_' key first."
            }

        url = "https://api.composio.dev/v1/integrations/connect"
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        payload = json.dumps({"appName": app_name.lower(), "redirectUrl": redirect_url}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                res_body = resp.read().decode("utf-8")
                return json.loads(res_body)
        except Exception as e:
            return {"error": f"OAuth initiation failed: {e}"}
