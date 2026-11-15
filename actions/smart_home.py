"""
actions/smart_home.py
Home Assistant integration + smart home control — inspired by home-assistant/core, HeyGemini.
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("smart_home")
TIMEOUT = 5.0


def _config_path() -> Path:
    p = Path(__file__).resolve().parent.parent / "memory" / "smart_home_config.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_config() -> dict:
    p = _config_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "ha_url": "http://homeassistant.local:8123",
        "ha_token": "",
        "configured": False,
        "demo_mode": True,
    }


def _save_config(cfg: dict):
    _config_path().write_text(json.dumps(cfg, indent=2), encoding="utf-8")


DEMO_DEVICES = [
    {"entity_id": "light.living_room", "state": "on", "type": "light", "friendly_name": "Living Room Light", "brightness": 180},
    {"entity_id": "light.bedroom", "state": "off", "type": "light", "friendly_name": "Bedroom Light", "brightness": 0},
    {"entity_id": "switch.kitchen_plug", "state": "on", "type": "switch", "friendly_name": "Kitchen Smart Plug"},
    {"entity_id": "climate.thermostat", "state": "heat", "type": "climate", "friendly_name": "Main Thermostat", "temperature": 22},
    {"entity_id": "sensor.temperature", "state": "23.5", "type": "sensor", "friendly_name": "Indoor Temperature", "unit": "°C"},
    {"entity_id": "sensor.humidity", "state": "45", "type": "sensor", "friendly_name": "Humidity", "unit": "%"},
    {"entity_id": "lock.front_door", "state": "locked", "type": "lock", "friendly_name": "Front Door Lock"},
    {"entity_id": "media_player.speaker", "state": "paused", "type": "media_player", "friendly_name": "Smart Speaker"},
    {"entity_id": "camera.doorbell", "state": "idle", "type": "camera", "friendly_name": "Doorbell Camera"},
    {"entity_id": "binary_sensor.motion", "state": "off", "type": "binary_sensor", "friendly_name": "Motion Sensor"},
]

DEMO_SCENES = [
    {"entity_id": "scene.movie_night", "friendly_name": "Movie Night"},
    {"entity_id": "scene.good_morning", "friendly_name": "Good Morning"},
    {"entity_id": "scene.sleep_mode", "friendly_name": "Sleep Mode"},
    {"entity_id": "scene.away_from_home", "friendly_name": "Away From Home"},
]


def _ha_request(method: str, endpoint: str, cfg: dict, data: dict = None) -> dict:
    """Make authenticated request to Home Assistant API."""
    import requests
    url = f"{cfg['ha_url'].rstrip('/')}/api/{endpoint}"
    headers = {
        "Authorization": f"Bearer {cfg['ha_token']}",
        "Content-Type": "application/json",
    }
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        else:
            resp = requests.post(url, headers=headers, json=data or {}, timeout=TIMEOUT)
        if resp.status_code in (200, 201):
            return {"ok": True, "data": resp.json()}
        return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def smart_home(parameters: dict, player=None) -> str:
    """Home Assistant smart home controller."""
    action = (parameters.get("action") or "status").strip().lower()
    aliases = {
        "list": "list_devices", "devices": "list_devices", "scenes": "scene",
        "trigger_scene": "scene", "automations": "automation_list"
    }
    action = aliases.get(action, action)
    cfg = _load_config()
    demo = cfg.get("demo_mode", True) or not cfg.get("ha_token")

    if action == "configure":
        url = parameters.get("url") or parameters.get("ha_url", "")
        token = parameters.get("token") or parameters.get("ha_token", "")
        if url:
            cfg["ha_url"] = url.strip()
        if token:
            cfg["ha_token"] = token.strip()
            cfg["configured"] = True
            cfg["demo_mode"] = False
        _save_config(cfg)
        return f"✅ Home Assistant configured.\n  URL: {cfg['ha_url']}\n  Token: {'set' if cfg['ha_token'] else 'not set'}\n  Mode: {'Live' if not cfg['demo_mode'] else 'Demo'}"

    elif action == "status":
        if demo:
            on_count = sum(1 for d in DEMO_DEVICES if d["state"] in ("on", "heat", "locked"))
            return (
                f"🏠 Smart Home Status (Demo Mode):\n"
                f"  • Devices: {len(DEMO_DEVICES)}\n"
                f"  • Active/On: {on_count}\n"
                f"  • Scenes: {len(DEMO_SCENES)}\n\n"
                f"  ℹ️ Running in demo mode. Use 'configure' with your HA URL and token for real control."
            )
        result = _ha_request("GET", "", cfg)
        if result["ok"]:
            return f"🏠 Home Assistant is online!\n  URL: {cfg['ha_url']}\n  Message: {result['data'].get('message', 'Connected')}"
        return f"❌ Cannot reach Home Assistant: {result['error']}"

    elif action == "list_devices":
        if demo:
            lines = ["🏠 Smart Home Devices (Demo):\n"]
            for d in DEMO_DEVICES:
                state_icon = "🟢" if d["state"] in ("on", "heat", "locked") else "⚪"
                extra = ""
                if "brightness" in d and d.get("state") == "on":
                    extra = f" (brightness: {d['brightness']})"
                if "temperature" in d and d["type"] == "climate":
                    extra = f" (set: {d['temperature']}°C)"
                if d["type"] == "sensor":
                    extra = f" ({d['state']}{d.get('unit', '')})"
                lines.append(f"  {state_icon} {d['friendly_name']} — {d['state']}{extra}")
            return "\n".join(lines)
        result = _ha_request("GET", "states", cfg)
        if result["ok"]:
            entities = result["data"]
            lines = [f"🏠 Devices ({len(entities)}):\n"]
            for e in entities[:30]:
                name = e.get("attributes", {}).get("friendly_name", e["entity_id"])
                lines.append(f"  • {name} — {e['state']}")
            return "\n".join(lines)
        return f"Failed: {result['error']}"

    elif action == "toggle":
        entity = (parameters.get("entity") or parameters.get("device", "")).strip()
        if not entity:
            return "Entity ID or device name is required."
        if demo:
            for d in DEMO_DEVICES:
                if entity.lower() in d["entity_id"].lower() or entity.lower() in d["friendly_name"].lower():
                    old = d["state"]
                    d["state"] = "off" if old in ("on", "heat", "locked") else "on"
                    return f"✅ Toggled {d['friendly_name']}: {old} → {d['state']}"
            return f"Device '{entity}' not found in demo mode."
        domain = entity.split(".")[0] if "." in entity else "homeassistant"
        result = _ha_request("POST", f"services/{domain}/toggle", cfg, {"entity_id": entity})
        return f"✅ Toggled {entity}" if result["ok"] else f"Failed: {result['error']}"

    elif action == "set_brightness":
        entity = (parameters.get("entity") or parameters.get("device", "")).strip()
        brightness = int(parameters.get("brightness") or parameters.get("value", 128))
        if not entity:
            return "Entity ID is required."
        if demo:
            for d in DEMO_DEVICES:
                if entity.lower() in d["entity_id"].lower() or entity.lower() in d["friendly_name"].lower():
                    d["brightness"] = brightness
                    d["state"] = "on"
                    return f"💡 Set {d['friendly_name']} brightness to {brightness}/255"
            return f"Device '{entity}' not found."
        result = _ha_request("POST", "services/light/turn_on", cfg, {"entity_id": entity, "brightness": brightness})
        return f"💡 Brightness set to {brightness}" if result["ok"] else f"Failed: {result['error']}"

    elif action == "set_temperature":
        entity = (parameters.get("entity") or "climate.thermostat").strip()
        temp = float(parameters.get("temperature") or parameters.get("value", 22))
        if demo:
            for d in DEMO_DEVICES:
                if entity.lower() in d["entity_id"].lower():
                    d["temperature"] = temp
                    return f"🌡️ Set {d['friendly_name']} to {temp}°C"
            return f"Thermostat '{entity}' not found."
        result = _ha_request("POST", "services/climate/set_temperature", cfg, {"entity_id": entity, "temperature": temp})
        return f"🌡️ Temperature set to {temp}°C" if result["ok"] else f"Failed: {result['error']}"

    elif action == "set_color":
        entity = (parameters.get("entity") or "").strip()
        color = (parameters.get("color") or "white").strip().lower()
        if not entity:
            return "Entity ID is required."
        color_map = {
            "red": [255, 0, 0], "green": [0, 255, 0], "blue": [0, 0, 255],
            "white": [255, 255, 255], "warm": [255, 200, 100], "cool": [200, 220, 255],
            "purple": [128, 0, 255], "orange": [255, 165, 0], "yellow": [255, 255, 0],
            "pink": [255, 105, 180], "cyan": [0, 255, 255],
        }
        rgb = color_map.get(color, [255, 255, 255])
        if demo:
            return f"🎨 Set {entity} color to {color} (RGB: {rgb})"
        result = _ha_request("POST", "services/light/turn_on", cfg, {"entity_id": entity, "rgb_color": rgb})
        return f"🎨 Color set to {color}" if result["ok"] else f"Failed: {result['error']}"

    elif action == "scene":
        scene = (parameters.get("scene") or parameters.get("name", "")).strip()
        if not scene:
            if demo:
                return "🎬 Available Scenes:\n" + "\n".join(f"  • {s['friendly_name']}" for s in DEMO_SCENES)
            result = _ha_request("GET", "states", cfg)
            if result["ok"]:
                scenes = [e for e in result["data"] if e["entity_id"].startswith("scene.")]
                return "🎬 Scenes:\n" + "\n".join(f"  • {s['attributes'].get('friendly_name', s['entity_id'])}" for s in scenes[:20])
            return f"Failed: {result['error']}"
        if demo:
            for s in DEMO_SCENES:
                if scene.lower() in s["friendly_name"].lower() or scene.lower() in s["entity_id"].lower():
                    return f"🎬 Activated scene: {s['friendly_name']}"
            return f"Scene '{scene}' not found."
        entity = scene if scene.startswith("scene.") else f"scene.{scene.lower().replace(' ', '_')}"
        result = _ha_request("POST", "services/scene/turn_on", cfg, {"entity_id": entity})
        return f"🎬 Scene activated" if result["ok"] else f"Failed: {result['error']}"

    elif action == "automation_list":
        if demo:
            return "⚙️ Automations (Demo):\n  • Lights off at midnight\n  • Motion-triggered hallway light\n  • Morning thermostat warmup\n  • Door lock auto-engage"
        result = _ha_request("GET", "states", cfg)
        if result["ok"]:
            autos = [e for e in result["data"] if e["entity_id"].startswith("automation.")]
            lines = [f"⚙️ Automations ({len(autos)}):\n"]
            for a in autos[:20]:
                name = a["attributes"].get("friendly_name", a["entity_id"])
                lines.append(f"  • {name} — {a['state']}")
            return "\n".join(lines)
        return f"Failed: {result['error']}"

    else:
        return (
            f"Unknown action '{action}'. Available: status, list_devices, toggle, "
            "set_brightness, set_temperature, set_color, scene, automation_list, configure"
        )


if __name__ == "__main__":
    print(smart_home({"action": "status"}))
    print(smart_home({"action": "list_devices"}))

