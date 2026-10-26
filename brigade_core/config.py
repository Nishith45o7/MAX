"""
Configuration management for Brigade & MAX.
Handles JSON5 / JSON with ${VAR} variable interpolation, rotating backups,
schema validation, and bridge to MAX's legacy api_keys.json.
"""
import os
import re
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
from brigade_core import get_state_dir

ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z0-9_]+)\}")

DEFAULT_CONFIG: Dict[str, Any] = {
    "version": 1,
    "storage": {
        "mode": "filesystem",  # "filesystem" or "convex"
        "encryption": False
    },
    "gateway": {
        "host": "127.0.0.1",
        "port": 7777,
        "tokens": []
    },
    "agents": {
        "defaults": {
            "model": "google/gemini-2.5-flash",
            "provider": "openrouter",
            "thinking": "medium"
        },
        "list": [
            {
                "id": "main",
                "name": "MAX (Chief Agent)",
                "description": "Primary desktop intelligence and coordinator",
                "workspace": "workspace",
                "model": "google/gemini-2.5-flash",
                "provider": "openrouter"
            }
        ]
    },
    "org": {
        "name": "Personal Crew",
        "departments": [
            {
                "id": "executive",
                "name": "Executive & Coordination",
                "lead": "main",
                "members": ["main"]
            }
        ]
    },
    "channels": {
        "telegram": {
            "enabled": True,
            "botToken": "${TELEGRAM_BOT_TOKEN}",
            "allowedUsers": []
        },
        "discord": {
            "enabled": False,
            "botToken": "${DISCORD_BOT_TOKEN}",
            "allowedUsers": []
        },
        "slack": {
            "enabled": False,
            "botToken": "${SLACK_BOT_TOKEN}",
            "appToken": "${SLACK_APP_TOKEN}"
        },
        "whatsapp": {
            "enabled": False,
            "sessionId": "default"
        },
        "bluebubbles": {
            "enabled": False,
            "serverUrl": "",
            "password": ""
        }
    },
    "cron": {
        "enabled": True,
        "jobs": []
    },
    "security": {
        "execApproval": "ask",  # "ask", "allow", "deny"
        "allowlistPatterns": [
            r"^python\s+",
            r"^git\s+status",
            r"^dir",
            r"^ls"
        ]
    }
}


class ConfigManager:
    """Manages brigade.json configuration lifecycle."""

    def __init__(self, config_path: Optional[Path] = None):
        self.state_dir = get_state_dir()
        self.config_path = config_path or (self.state_dir / "brigade.json")
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        """Creates default configuration if it does not exist."""
        if not self.config_path.exists():
            cfg = self._bootstrap_from_existing_keys(DEFAULT_CONFIG.copy())
            self.save(cfg, make_backup=False)

    def _bootstrap_from_existing_keys(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-migrates existing API keys from MAX's config/api_keys.json if present."""
        max_base = Path(__file__).resolve().parent.parent
        legacy_api_file = max_base / "config" / "api_keys.json"
        if legacy_api_file.exists():
            try:
                with open(legacy_api_file, "r", encoding="utf-8") as f:
                    keys = json.load(f)
                if "telegram_bot_token" in keys and keys["telegram_bot_token"]:
                    cfg.setdefault("channels", {}).setdefault("telegram", {})["botToken"] = keys["telegram_bot_token"]
                if "telegram_allowed_users" in keys and isinstance(keys["telegram_allowed_users"], list):
                    cfg.setdefault("channels", {}).setdefault("telegram", {})["allowedUsers"] = keys["telegram_allowed_users"]
                if "openrouter_api_key" in keys and keys["openrouter_api_key"]:
                    cfg.setdefault("providers", {})["openrouter_api_key"] = keys["openrouter_api_key"]
                if "gemini_api_key" in keys and keys["gemini_api_key"]:
                    cfg.setdefault("providers", {})["gemini_api_key"] = keys["gemini_api_key"]
                if "groq_api_key" in keys and keys["groq_api_key"]:
                    cfg.setdefault("providers", {})["groq_api_key"] = keys["groq_api_key"]
            except Exception:
                pass
        return cfg

    def load_raw(self) -> Dict[str, Any]:
        """Loads the raw configuration dict preserving ${VAR} expressions."""
        if not self.config_path.exists():
            return DEFAULT_CONFIG.copy()
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_resolved(self) -> Dict[str, Any]:
        """Loads configuration with all ${VAR} environment references resolved."""
        raw = self.load_raw()
        return self._resolve_vars(raw)

    def _resolve_vars(self, item: Any) -> Any:
        if isinstance(item, str):
            def replacer(m):
                var_name = m.group(1)
                return os.environ.get(var_name, m.group(0))
            return ENV_VAR_PATTERN.sub(replacer, item)
        elif isinstance(item, dict):
            return {k: self._resolve_vars(v) for k, v in item.items()}
        elif isinstance(item, list):
            return [self._resolve_vars(v) for v in item]
        return item

    def save(self, data: Dict[str, Any], make_backup: bool = True) -> None:
        """Saves configuration with rotating forensic backups and POSIX 0600 protection."""
        if make_backup and self.config_path.exists():
            self._rotate_backups()

        tmp_path = self.config_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Set permissions if supported
        try:
            os.chmod(tmp_path, 0o600)
        except Exception:
            pass

        shutil.move(str(tmp_path), str(self.config_path))

    def _rotate_backups(self) -> None:
        """Maintains rotating forensic backups: .bak, .bak.1, .bak.2, .bak.3, .bak.4."""
        for i in range(4, 0, -1):
            src = self.config_path.with_suffix(f".bak.{i-1}" if i > 1 else ".bak")
            dst = self.config_path.with_suffix(f".bak.{i}")
            if src.exists():
                shutil.copy2(str(src), str(dst))
        shutil.copy2(str(self.config_path), str(self.config_path.with_suffix(".bak")))

    def get(self, key_path: str, default: Any = None, resolved: bool = True) -> Any:
        """Retrieve dot-separated path (e.g. 'agents.defaults.provider')."""
        cfg = self.load_resolved() if resolved else self.load_raw()
        curr = cfg
        for part in key_path.split("."):
            if isinstance(curr, dict) and part in curr:
                curr = curr[part]
            else:
                return default
        return curr

    def set(self, key_path: str, value: Any) -> None:
        """Set dot-separated path and persist."""
        cfg = self.load_raw()
        parts = key_path.split(".")
        curr = cfg
        for part in parts[:-1]:
            if part not in curr or not isinstance(curr[part], dict):
                curr[part] = {}
            curr = curr[part]
        curr[parts[-1]] = value
        self.save(cfg)

    def validate(self) -> bool:
        """Validate schema integrity."""
        cfg = self.load_raw()
        required_keys = ["version", "storage", "gateway", "agents", "org"]
        for k in required_keys:
            if k not in cfg:
                raise ValueError(f"Missing required config key: '{k}'")
        return True
