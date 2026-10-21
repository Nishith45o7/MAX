import os
import sys
import json
import time
import subprocess
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    import requests
except ImportError:
    requests = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omniroute_manager")

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()
CONFIG_FILE = BASE_DIR / "config" / "api_keys.json"

DEFAULT_OMNIROUTE_URL = "http://localhost:20128/v1"
DEFAULT_DASHBOARD_URL = "http://localhost:20128/dashboard"
DEFAULT_PORT = 20128

_process: Optional[subprocess.Popen] = None


def load_omniroute_config() -> Dict[str, Any]:
    """Loads OmniRoute settings from config/api_keys.json or environment."""
    config = {
        "enabled": True,
        "base_url": os.environ.get("OMNIROUTE_BASE_URL", DEFAULT_OMNIROUTE_URL).strip(),
        "api_key": os.environ.get("OMNIROUTE_API_KEY", "omniroute").strip(),
        "model": os.environ.get("OMNIROUTE_MODEL", "auto").strip(),
        "dashboard_url": DEFAULT_DASHBOARD_URL,
    }

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if "use_omniroute" in data:
                config["enabled"] = bool(data["use_omniroute"])
            if "omniroute_base_url" in data and str(data["omniroute_base_url"]).strip():
                config["base_url"] = str(data["omniroute_base_url"]).strip()
            if "omniroute_api_key" in data and str(data["omniroute_api_key"]).strip():
                config["api_key"] = str(data["omniroute_api_key"]).strip()
            if "omniroute_model" in data and str(data["omniroute_model"]).strip():
                config["model"] = str(data["omniroute_model"]).strip()
        except Exception as e:
            logger.warning(f"Error reading api_keys.json for OmniRoute: {e}")

    return config


def is_omniroute_alive(base_url: Optional[str] = None, timeout: float = 0.8) -> bool:
    """Checks whether the OmniRoute OpenAI-compatible gateway is currently reachable."""
    if not requests:
        return False

    url = (base_url or load_omniroute_config()["base_url"]).rstrip("/")
    probe_url = f"{url}/models"

    try:
        res = requests.get(probe_url, timeout=timeout)
        return res.status_code in (200, 401, 403)
    except Exception:
        return False


def get_available_models(base_url: Optional[str] = None, api_key: Optional[str] = None) -> List[str]:
    """Retrieves list of active model IDs exposed by the local OmniRoute gateway."""
    if not requests:
        return []

    cfg = load_omniroute_config()
    url = (base_url or cfg["base_url"]).rstrip("/")
    key = api_key or cfg["api_key"]
    probe_url = f"{url}/models"

    try:
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        res = requests.get(probe_url, headers=headers, timeout=2.0)
        if res.status_code == 200:
            data = res.json()
            models = []
            for item in data.get("data", []):
                mid = item.get("id")
                if mid:
                    models.append(mid)
            return models
    except Exception as e:
        logger.debug(f"Failed to fetch OmniRoute models: {e}")
    return []


def start_omniroute_background() -> bool:
    """Launches OmniRoute as an asynchronous background daemon if not already running."""
    global _process
    if is_omniroute_alive():
        logger.info("OmniRoute is already running and accessible.")
        return True

    cmd = ["npx", "-y", "omniroute"]
    try:
        logger.info("Starting OmniRoute background process (npx -y omniroute)...")
        if sys.platform == "win32":
            # DETACHED_PROCESS flag on Windows
            creation_flags = 0x08000000 | subprocess.CREATE_NEW_PROCESS_GROUP
            _process = subprocess.Popen(
                cmd,
                creationflags=creation_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=True
            )
        else:
            _process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        return True
    except Exception as e:
        logger.error(f"Failed to start OmniRoute background process: {e}")
        return False


def get_status_summary() -> Dict[str, Any]:
    """Provides a complete status summary of the OmniRoute gateway."""
    cfg = load_omniroute_config()
    alive = is_omniroute_alive(cfg["base_url"])
    models = get_available_models(cfg["base_url"], cfg["api_key"]) if alive else []

    return {
        "installed": True,
        "enabled": cfg["enabled"],
        "online": alive,
        "base_url": cfg["base_url"],
        "dashboard_url": cfg["dashboard_url"],
        "target_model": cfg["model"],
        "models_count": len(models),
        "sample_models": models[:10] if models else ["auto"]
    }


if __name__ == "__main__":
    print("=== OmniRoute Gateway Diagnostic ===")
    status = get_status_summary()
    for k, v in status.items():
        print(f"  {k}: {v}")
