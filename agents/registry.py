"""
Agent Registry managing multi-agent identities, isolated workspaces,
routing bindings, and credential scoping.
"""
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from brigade_core.config import ConfigManager
from brigade_core.storage import StorageManager


class AgentRegistry:
    """Manages creation, deletion, and identity configuration of isolated agents."""

    def __init__(self, config_mgr: Optional[ConfigManager] = None, storage_mgr: Optional[StorageManager] = None):
        self.config_mgr = config_mgr or ConfigManager()
        self.storage_mgr = storage_mgr or StorageManager()

    def list_agents(self) -> List[Dict[str, Any]]:
        cfg = self.config_mgr.load_raw()
        return cfg.get("agents", {}).get("list", [])

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        for a in self.list_agents():
            if a["id"] == agent_id:
                return a
        return None

    def add_agent(
        self,
        agent_id: str,
        name: str,
        description: str = "",
        model: Optional[str] = None,
        provider: Optional[str] = None,
        bindings: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Creates an isolated agent, its workspace, and persists configuration."""
        agent_id = agent_id.strip().lower().replace(" ", "-")
        if self.get_agent(agent_id):
            raise ValueError(f"Agent with ID '{agent_id}' already exists.")

        cfg = self.config_mgr.load_raw()
        defaults = cfg.get("agents", {}).get("defaults", {})

        new_agent = {
            "id": agent_id,
            "name": name,
            "description": description,
            "workspace": f"agents/{agent_id}/workspace",
            "model": model or defaults.get("model", "google/gemini-2.5-flash"),
            "provider": provider or defaults.get("provider", "openrouter"),
            "theme": "dark",
            "emoji": "🤖",
            "bindings": bindings or []
        }

        # Initialize workspace
        self.storage_mgr.ensure_workspace(agent_id)

        cfg.setdefault("agents", {}).setdefault("list", []).append(new_agent)
        self.config_mgr.save(cfg)
        return new_agent

    def delete_agent(self, agent_id: str, force: bool = False) -> bool:
        if agent_id == "main":
            raise ValueError("The 'main' agent cannot be deleted.")
        if not force:
            raise ValueError("Deleting an agent requires explicit force=True.")

        cfg = self.config_mgr.load_raw()
        agent_list = cfg.get("agents", {}).get("list", [])
        updated = [a for a in agent_list if a["id"] != agent_id]
        if len(updated) == len(agent_list):
            return False

        cfg["agents"]["list"] = updated
        self.config_mgr.save(cfg)

        # Remove agent folder
        agent_dir = self.storage_mgr.get_agent_dir(agent_id)
        if agent_dir.exists():
            shutil.rmtree(str(agent_dir), ignore_errors=True)

        return True

    def set_identity(self, agent_id: str, **kwargs) -> Dict[str, Any]:
        """Updates identity fields (name, emoji, theme, avatar, description)."""
        cfg = self.config_mgr.load_raw()
        for a in cfg.get("agents", {}).get("list", []):
            if a["id"] == agent_id:
                for k in ["name", "emoji", "theme", "avatar", "description", "model", "provider"]:
                    if k in kwargs and kwargs[k] is not None:
                        a[k] = kwargs[k]
                self.config_mgr.save(cfg)
                return a
        raise ValueError(f"Agent '{agent_id}' not found.")

    def bind_channel(self, agent_id: str, channel_spec: str) -> bool:
        """Binds a channel account to an agent (e.g. 'telegram' or 'telegram:12345')."""
        cfg = self.config_mgr.load_raw()
        for a in cfg.get("agents", {}).get("list", []):
            if a["id"] == agent_id:
                bindings = a.setdefault("bindings", [])
                if channel_spec not in bindings:
                    bindings.append(channel_spec)
                    self.config_mgr.save(cfg)
                    return True
        return False
