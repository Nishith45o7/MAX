import json
import os
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from openai import OpenAI

# ─────────────────────────────────────────────────────────────────────────────
# BASE DIRECTORY & CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

# Import memory persistence
try:
    from memory.db import (
        get_context_for_prompt,
        save_conversation_turn,
        get_recent_conversations
    )
except ImportError:
    def get_context_for_prompt(query: str = "", max_items: int = 5) -> str:
        return ""
    def save_conversation_turn(role: str, content: str, metadata: str = ""):
        pass
    def get_recent_conversations(limit: int = 10) -> list:
        return []

# Import Brigade Core, Tideline, Skills, Tools, and Agents
try:
    from brigade_core import get_state_dir
    from brigade_core.config import ConfigManager
    from brigade_core.storage import StorageManager
    from tideline.engine import TidelineEngine
    from skills.loader import SkillLoader
    from tools.registry import ToolRegistry
    from agents.registry import AgentRegistry
    from agents.org_chart import OrgChart
    from agents.subagent_runner import SubagentRunner
    from cron.scheduler import CronScheduler
    from security.anti_slop import AntiSlopDetector
    from security.injection_guard import InjectionGuard
    from agents.carrow import Carrow
    _BRIGADE_LOADED = True
except ImportError as _e:
    print(f"[MAX Brain] Brigade framework import notice: {_e}")
    _BRIGADE_LOADED = False

# Import OmniRoute Gateway manager
try:
    from gateway.omniroute_manager import (
        is_omniroute_alive,
        load_omniroute_config,
        get_available_models,
        start_omniroute_background,
        get_status_summary
    )
except ImportError:
    def is_omniroute_alive(*args, **kwargs) -> bool: return False
    def load_omniroute_config() -> dict: return {"enabled": True, "base_url": "http://localhost:20128/v1", "api_key": "omniroute", "model": "auto"}
    def get_available_models(*args, **kwargs) -> list: return []
    def start_omniroute_background() -> bool: return False
    def get_status_summary() -> dict: return {"online": False}

# Import tool implementations from local modules
try:
    from web_tool import search_web
except ImportError:
    def search_web(query: str) -> str:
        return f"Error: web_tool.py not found. Query '{query}' could not be executed."

try:
    from doc_tools import create_styled_presentation, create_pdf
except ImportError:
    def create_styled_presentation(title, theme, slides, filename="presentation.pptx"):
        return "Error: doc_tools.py not found. Presentation could not be created."
    def create_pdf(title, paragraphs, filename="document.pdf"):
        return "Error: doc_tools.py not found. PDF could not be created."

def generate_image(prompt: str, filename: Optional[str] = None) -> str:
    """Generates an image via AI (Pollinations Flux) and saves to Desktop."""
    import urllib.parse
    import requests
    import time
    try:
        clean_p = prompt.strip()
        encoded = urllib.parse.quote(clean_p)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            desktop = Path.home() / "Desktop"
            desktop.mkdir(parents=True, exist_ok=True)
            fname = filename or f"generated_{int(time.time())}.png"
            if not fname.endswith(".png") and not fname.endswith(".jpg"):
                fname += ".png"
            out_path = desktop / fname
            with open(out_path, "wb") as f:
                f.write(resp.content)
            return f"Image successfully generated and saved to {out_path.name} on Desktop."
        return f"Image generation failed with status code {resp.status_code}."
    except Exception as e:
        return f"Image generation error: {e}"

# Import bridged action modules
try:
    from actions.open_app import open_app
except ImportError:
    open_app = None

try:
    from actions.computer_settings import computer_settings
except ImportError:
    computer_settings = None

try:
    from actions.file_controller import file_controller, _resolve_path
except ImportError:
    file_controller = None
    _resolve_path = None

# Import public-apis zero-key tool integrations
try:
    from actions.public_api_tools import (
        get_live_weather,
        get_crypto_currency_rates,
        get_wikipedia_summary,
        get_top_tech_news,
        get_ip_geolocation
    )
except ImportError:
    get_live_weather = None
    get_crypto_currency_rates = None
    get_wikipedia_summary = None
    get_top_tech_news = None
    get_ip_geolocation = None


# ─────────────────────────────────────────────────────────────────────────────
# CREDENTIALS & INFERENCE CLIENT RESOLUTION (OMNIROUTE + FALLBACKS)
# ─────────────────────────────────────────────────────────────────────────────
def _load_groq_key() -> str:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if key and key != "YOUR_GROQ_API_KEY_HERE":
        return key

    if API_CONFIG_PATH.exists():
        try:
            with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            key = data.get("groq_api_key", "").strip()
            if key and key != "YOUR_GROQ_API_KEY_HERE":
                return key
        except Exception:
            pass
    return ""


def _load_openrouter_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key

    if API_CONFIG_PATH.exists():
        try:
            with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            key = data.get("openrouter_api_key", "").strip()
            if key:
                return key
        except Exception:
            pass
    return ""


DEFAULT_GROQ_MODELS = [
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant"
]


def _get_active_llm_client() -> Tuple[OpenAI, List[str], str]:
    """
    Dynamically resolves the active LLM client and ordered candidate models.
    Priority:
    1. OmniRoute AI Gateway (http://localhost:20128/v1 - 375+ providers, 1400+ models with auto-fallback)
    2. Direct Groq Cloud
    3. Direct OpenRouter Gateway
    """
    # 1. Check OmniRoute Local Gateway
    try:
        omni_cfg = load_omniroute_config()
        if omni_cfg.get("enabled", True) and is_omniroute_alive(omni_cfg["base_url"]):
            omni_client = OpenAI(
                base_url=omni_cfg["base_url"],
                api_key=omni_cfg.get("api_key") or "omniroute"
            )
            # Candidate models: start with configured model (default: "auto"), plus top tier models
            models = [omni_cfg.get("model") or "auto"]
            for m in ["auto", "gpt-4o", "claude-3-7-sonnet", "deepseek-chat", "gemini-2.5-flash", "llama-3.3-70b"]:
                if m not in models:
                    models.append(m)
            return omni_client, models, f"OmniRoute Gateway ({omni_cfg['base_url']})"
    except Exception as e:
        print(f"[MAX Brain] OmniRoute probe error: {e}")

    # 2. Check Groq
    groq_key = _load_groq_key()
    if groq_key:
        groq_client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_key
        )
        return groq_client, DEFAULT_GROQ_MODELS, "Groq Cloud"

    # 3. Check OpenRouter
    or_key = _load_openrouter_key()
    if or_key:
        or_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=or_key
        )
        or_models = [
            "openai/gpt-4o-mini",
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemini-2.0-flash-exp:free"
        ]
        return or_client, or_models, "OpenRouter AI"

    # 4. Default unconfigured fallback client
    default_client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key="YOUR_GROQ_API_KEY_HERE"
    )
    return default_client, DEFAULT_GROQ_MODELS, "Unconfigured"


# ─────────────────────────────────────────────────────────────────────────────
# AGENT TOOL DEFINITIONS (OPENAI FUNCTION-CALLING FORMAT)
# ─────────────────────────────────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Searches the live internet for recent events, research, articles, or real-time facts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Precise search keywords or query."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Generates AI artwork or realistic images from a descriptive prompt and saves them to Desktop (automatically sent to Telegram).",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Descriptive visual prompt for image generation."
                    }
                },
                "required": ["prompt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_styled_presentation",
            "description": "Generates a styled, multi-slide PowerPoint (.pptx) file directly on the user's Desktop using theme tokens.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Main title on the presentation cover slide."
                    },
                    "filename": {
                        "type": "string",
                        "description": "Filename ending with .pptx (e.g., 'Quantum_Computing.pptx')."
                    },
                    "theme": {
                        "type": "object",
                        "description": "Visual HEX palette matching the requested aesthetic.",
                        "properties": {
                            "bg_hex": {"type": "string", "description": "Slide background color HEX (e.g. '#0d1117')"},
                            "card_hex": {"type": "string", "description": "Card container HEX (e.g. '#161b22')"},
                            "accent_hex": {"type": "string", "description": "Primary accent/title HEX (e.g. '#58a6ff')"},
                            "text_hex": {"type": "string", "description": "Readable body text HEX (e.g. '#c9d1d9')"},
                            "font_name": {"type": "string", "description": "Font family (e.g. 'Segoe UI', 'Consolas', 'Arial')"}
                        },
                        "required": ["bg_hex", "card_hex", "accent_hex", "text_hex"]
                    },
                    "slides": {
                        "type": "array",
                        "description": "Array of slide objects to generate.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "Slide title"},
                                "layout": {
                                    "type": "string",
                                    "enum": ["card_stack", "columns"],
                                    "description": "Single wide card stack or multi-column card grid."
                                },
                                "bullets": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Bullet points for 'card_stack' layout."
                                },
                                "items": {
                                    "type": "array",
                                    "description": "Columns list for 'columns' layout.",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "header": {"type": "string"},
                                            "points": {"type": "array", "items": {"type": "string"}}
                                        },
                                        "required": ["header", "points"]
                                    }
                                }
                            },
                            "required": ["title", "layout"]
                        }
                    }
                },
                "required": ["title", "theme", "slides"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_pdf",
            "description": "Generates a structured PDF document saved directly to the user's Desktop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Document heading."
                    },
                    "paragraphs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of individual paragraphs/sections."
                    },
                    "filename": {
                        "type": "string",
                        "description": "Filename ending with .pdf (e.g., 'Report.pdf')."
                    }
                },
                "required": ["title", "paragraphs"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "launch_application",
            "description": "Launches a desktop application, browser, terminal, or system tool by name on the user's computer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the application to launch (e.g. 'chrome', 'notepad', 'calculator', 'vscode', 'spotify', 'terminal')."
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_computer_settings",
            "description": "Adjusts OS hardware settings or queries hardware metrics (volume control, mute, battery status, brightness, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "volume_up",
                            "volume_down",
                            "volume_mute",
                            "volume_unmute",
                            "volume_set",
                            "battery_status",
                            "sleep_display",
                            "dark_mode"
                        ],
                        "description": "The specific setting adjustment or hardware status query to perform."
                    },
                    "value": {
                        "type": "string",
                        "description": "Optional value for settings like 'volume_set' (e.g. '50' for 50%)."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_local_files",
            "description": "Performs file system operations such as listing directories, reading files, checking if files exist, creating/writing files, and organizing folders.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "read", "exists", "create_file", "write", "delete", "info"],
                        "description": "Action to perform on the file system."
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory or path target (e.g. 'desktop', 'downloads', 'documents', or full path). Defaults to 'desktop'."
                    },
                    "name": {
                        "type": "string",
                        "description": "File or folder name (e.g., 'notes.txt', 'project_data')."
                    },
                    "content": {
                        "type": "string",
                        "description": "Content string to write when creating or writing to a file."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_omniroute_gateway",
            "description": "Checks the operational status of the OmniRoute AI Gateway (port 20128), model count, latency, and connected providers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["status", "models", "start"],
                        "description": "Action to perform ('status' to check connectivity, 'models' to list models, 'start' to launch daemon)."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_live_weather",
            "description": "Fetches real-time weather conditions (temperature, humidity, wind, feel) and 3-day forecast for any city or current location via wttr.in (zero API keys).",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Name of the city (e.g. 'London', 'Tokyo', 'Mumbai', 'New York'). Leave empty or 'current' for local auto-detected weather."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_crypto_currency_rates",
            "description": "Retrieves live cryptocurrency prices (Bitcoin, Ethereum, Solana, etc. via CoinGecko) or converts fiat currencies (via Frankfurter API).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["crypto", "fiat"],
                        "description": "'crypto' for live cryptocurrency market prices, 'fiat' for currency conversion."
                    },
                    "crypto_symbols": {
                        "type": "string",
                        "description": "Comma-separated crypto coin IDs (e.g. 'bitcoin,ethereum,solana,dogecoin')."
                    },
                    "amount": {
                        "type": "number",
                        "description": "Amount to convert for fiat currencies."
                    },
                    "from_curr": {
                        "type": "string",
                        "description": "Source fiat currency code (e.g. 'USD', 'EUR', 'GBP')."
                    },
                    "to_curr": {
                        "type": "string",
                        "description": "Target fiat currency codes (e.g. 'INR,EUR,GBP,JPY')."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_wikipedia_summary",
            "description": "Fetches an authoritative, concise encyclopedia summary from Wikipedia for any person, technology, historical event, scientific concept, or place.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The concept, person, or topic to summarize."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_tech_news",
            "description": "Retrieves top trending technology, AI, and engineering headlines from Hacker News.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of top stories to retrieve (default 5, max 10)."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_ip_geolocation",
            "description": "Retrieves the host workstation's network location, city, country, timezone, public IP, and ISP information.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": "Queries Tideline long-term memory for facts, preferences, user identity, projects, or context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Memory query or search terms."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_memory",
            "description": "Writes a persistent fact or preference into Tideline memory under provenance safety rules.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Fact or preference to store."},
                    "segment": {"type": "string", "enum": ["identity", "preference", "correction", "relationship", "project", "knowledge", "context"]},
                    "tier": {"type": "string", "enum": ["short", "long", "permanent"]}
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_skill",
            "description": "Reads the full markdown instructions and workflow guide for any available extensible skill.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "Exact name of the skill (e.g. 'docx', 'pdf', 'xlsx', 'weather')."}
                },
                "required": ["skill_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "bash_command",
            "description": "Runs a terminal command under the Exec Approval security bridge.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command line to execute."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_media",
            "description": "Extracts text and understands PDF, Office docs (.docx, .xlsx, .pptx), images, audio, or video files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or workspace-relative path to document/media."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "spawn_agent",
            "description": "Delegates a sub-task to an isolated agent or specialized crew member on the org chart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Target agent ID (e.g. 'coder', 'researcher', 'main')."},
                    "task_prompt": {"type": "string", "description": "Clear instruction for the sub-agent."}
                },
                "required": ["agent_id", "task_prompt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_cron",
            "description": "Schedules, lists, or cancels autonomous recurring jobs (cron expression, interval, or timestamp).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "add", "remove"]},
                    "schedule_type": {"type": "string", "enum": ["cron", "every", "at"]},
                    "expression": {"type": "string", "description": "Cron pattern ('0 9 * * *'), interval ('1h', '30m'), or timestamp."},
                    "message": {"type": "string", "description": "Instruction or task to execute when triggered."},
                    "job_id": {"type": "string", "description": "Job ID for removal."}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "composio_execute",
            "description": "Executes an action via Composio 1,000+ app connectors (Gmail, GitHub, Slack, Notion, Calendar).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string", "description": "Composio action name (e.g. 'GMAIL_SEND_EMAIL', 'GITHUB_CREATE_ISSUE')."},
                    "params": {"type": "object", "description": "Action parameters."}
                },
                "required": ["action_name", "params"]
            }
        }
    }
]


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL TOOL DISPATCHER
# ─────────────────────────────────────────────────────────────────────────────
def _execute_tool_call(func_name: str, args: dict) -> str:
    """Executes a validated tool call and returns a string response."""
    try:
        if func_name == "search_web":
            query = args.get("query", "").strip()
            print(f"[System Tool]: Running search for: '{query}'")
            return search_web(query)

        elif func_name == "generate_image":
            prompt = args.get("prompt", "").strip()
            print(f"[System Tool]: Generating image for prompt: '{prompt}'")
            return generate_image(prompt)

        elif func_name == "create_styled_presentation":
            filename = args.get("filename", "Presentation.pptx")
            if not filename.endswith(".pptx"):
                filename += ".pptx"
            print(f"[System Tool]: Building PPTX: '{filename}'")
            return create_styled_presentation(
                title=args.get("title", "Presentation"),
                theme=args.get("theme", {}),
                slides=args.get("slides", []),
                filename=filename
            )

        elif func_name == "create_pdf":
            filename = args.get("filename", "Document.pdf")
            if not filename.endswith(".pdf"):
                filename += ".pdf"
            print(f"[System Tool]: Building PDF: '{filename}'")
            return create_pdf(
                title=args.get("title", "Document"),
                paragraphs=args.get("paragraphs", []),
                filename=filename
            )

        elif func_name == "launch_application":
            app_name = args.get("app_name", "").strip()
            if not app_name:
                return "Error: app_name is required to launch an application."
            print(f"[System Tool]: Launching application: '{app_name}'")
            
            if open_app:
                try:
                    res = open_app({"app_name": app_name})
                    if sys.platform == "win32" and ("couldn't confirm" in res.lower() or "failed" in res.lower()):
                        subprocess.Popen(f'start "" "{app_name}"', shell=True)
                        return f"Application '{app_name}' launched via Windows shell command."
                    return res
                except Exception as e:
                    if sys.platform == "win32":
                        subprocess.Popen(f'start "" "{app_name}"', shell=True)
                        return f"Application '{app_name}' launched via Windows shell fallback (error: {e})."
                    return f"Failed to launch '{app_name}': {e}"
            else:
                if sys.platform == "win32":
                    subprocess.Popen(f'start "" "{app_name}"', shell=True)
                    return f"Application '{app_name}' launched via direct shell command."
                return "Error: open_app module is not available."

        elif func_name == "adjust_computer_settings":
            action = args.get("action", "").strip()
            value = args.get("value", None)
            print(f"[System Tool]: Computer settings action: '{action}' value: '{value}'")

            if action == "battery_status":
                try:
                    import psutil
                    battery = psutil.sensors_battery()
                    if battery:
                        plugged = "plugged in" if battery.power_plugged else "on battery power"
                        secs = f", ~{battery.secsleft // 60} mins remaining" if battery.secsleft > 0 else ""
                        return f"Battery status: {battery.percent}% ({plugged}{secs})."
                    return "Battery sensors are not available on this system."
                except Exception as e:
                    return f"Could not query battery status: {e}"

            if computer_settings:
                try:
                    return computer_settings({"action": action, "value": value})
                except Exception as e:
                    return f"Settings adjustment error ({action}): {e}"
            else:
                return "Error: computer_settings module is not available."

        elif func_name == "manage_local_files":
            action = args.get("action", "").strip()
            path = args.get("path", "desktop")
            name = args.get("name", "")
            content = args.get("content", "")
            print(f"[System Tool]: File management action: '{action}' path: '{path}' name: '{name}'")

            if action in ("exists", "check_exists"):
                try:
                    base = _resolve_path(path) if _resolve_path else Path(path).expanduser()
                    target = base / name if name else base
                    exists = target.exists()
                    item_type = "directory" if (exists and target.is_dir()) else ("file" if exists else "item")
                    return f"{item_type.capitalize()} '{target.name or target}' exists: {exists}."
                except Exception as e:
                    return f"Error verifying file existence: {e}"

            if file_controller:
                try:
                    return file_controller({
                        "action": action,
                        "path": path,
                        "name": name,
                        "content": content
                    })
                except Exception as e:
                    return f"File controller execution error: {e}"
            else:
                return "Error: file_controller module is not available."

        elif func_name == "check_omniroute_gateway":
            action = args.get("action", "status")
            if action == "start":
                started = start_omniroute_background()
                return (
                    f"OmniRoute launch triggered. Running via npx on http://localhost:20128.\n"
                    f"Dashboard available at: http://localhost:20128/dashboard"
                )
            elif action == "models":
                models = get_available_models()
                if models:
                    return f"OmniRoute exposes {len(models)} models: " + ", ".join(models[:12]) + ("..." if len(models) > 12 else "")
                return "OmniRoute gateway is currently offline or loading. You can start it using start_omniroute.bat or npx -y omniroute."
            else:
                summary = get_status_summary()
                status_str = "ONLINE (Active)" if summary["online"] else "OFFLINE (Start via start_omniroute.bat or 'npx -y omniroute')"
                return (
                    f"OmniRoute AI Gateway:\n"
                    f"• Status: {status_str}\n"
                    f"• Endpoint: {summary['base_url']}\n"
                    f"• Dashboard: {summary['dashboard_url']}\n"
                    f"• Target Routing: {summary['target_model']} (Dynamic provider pool)\n"
                    f"• Connected Providers: 375+ supported (150+ free tiers)\n"
                    f"• Features: RTK+Caveman Token Compression (15-95% savings), Quota Auto-Fallback."
                )

        elif func_name == "get_live_weather":
            city = args.get("city", "")
            if get_live_weather:
                return get_live_weather(city)
            return "Live weather service is not available."

        elif func_name == "get_crypto_currency_rates":
            action = args.get("action", "crypto")
            symbols = args.get("crypto_symbols", "bitcoin,ethereum,solana")
            try:
                amt = float(args.get("amount", 1.0))
            except (ValueError, TypeError):
                amt = 1.0
            from_c = args.get("from_curr", "USD")
            to_c = args.get("to_curr", "EUR,INR,GBP")
            if get_crypto_currency_rates:
                return get_crypto_currency_rates(
                    action=action,
                    crypto_symbols=symbols,
                    amount=amt,
                    from_curr=from_c,
                    to_curr=to_c
                )
            return "Crypto & currency service is not available."

        elif func_name == "get_wikipedia_summary":
            query = args.get("query", "")
            if get_wikipedia_summary:
                return get_wikipedia_summary(query)
            return "Wikipedia summary service is not available."

        elif func_name == "get_top_tech_news":
            try:
                limit = int(args.get("limit", 5))
            except (ValueError, TypeError):
                limit = 5
            if get_top_tech_news:
                return get_top_tech_news(limit)
            return "Tech news service is not available."

        elif func_name == "get_ip_geolocation":
            if get_ip_geolocation:
                return get_ip_geolocation()
            return "Geolocation service is not available."

        # ── BRIGADE FRAMEWORK EXTENDED CAPABILITIES ──
        elif func_name == "recall_memory":
            q = args.get("query", "").strip()
            if _BRIGADE_LOADED:
                ws = get_state_dir() / "workspace"
                engine = TidelineEngine.open(ws, default_origin="owner")
                hits = engine.recall(q, top_k=5)
                return "\n".join([f"[{h[0].segment}] {h[0].content}" for h in hits]) or "No relevant memory found."
            return "Memory engine not available."

        elif func_name == "write_memory":
            content = args.get("content", "").strip()
            seg = args.get("segment", "knowledge")
            tier = args.get("tier", "long")
            if _BRIGADE_LOADED:
                ws = get_state_dir() / "workspace"
                engine = TidelineEngine.open(ws, default_origin="owner")
                try:
                    rec = engine.add(content, segment=seg, tier=tier, origin="owner", source="user")
                    return f"Memory stored in Tideline (ID: {rec.id})"
                except Exception as e:
                    return f"Write gate rejected: {e}"
            return "Memory engine not available."

        elif func_name == "read_skill":
            skill_name = args.get("skill_name", "").strip().lower()
            if _BRIGADE_LOADED:
                loader = SkillLoader()
                skills = loader.discover_skills()
                if skill_name in skills:
                    return f"# Skill: {skill_name}\n\n{skills[skill_name].instructions}"
                return f"Skill '{skill_name}' not found. Available: {', '.join(sorted(skills.keys()))}"
            return "Skill loader not available."

        elif func_name == "bash_command":
            cmd = args.get("command", "").strip()
            if _BRIGADE_LOADED:
                from tools.coding_tools import CodingTools
                tools = CodingTools()
                return tools.bash(cmd)
            return "Command execution not available."

        elif func_name == "analyze_media":
            media_path = args.get("path", "").strip()
            if _BRIGADE_LOADED:
                from tools.doc_tools import DocumentTools
                dt = DocumentTools()
                return json.dumps(dt.analyze_media(media_path), indent=2)
            return "Media analysis not available."

        elif func_name == "spawn_agent":
            tgt = args.get("agent_id", "main").strip()
            prompt = args.get("task_prompt", "").strip()
            if _BRIGADE_LOADED:
                runner = SubagentRunner()
                res = runner.spawn_agent(
                    parent_id="main",
                    target_agent=tgt,
                    prompt=prompt,
                    agent_executor=lambda a, p: run_agent(p, max_iterations=3, agent_id=a)
                )
                return json.dumps(res, indent=2)
            return "Sub-agent runner not available."

        elif func_name == "manage_cron":
            action = args.get("action", "list")
            if _BRIGADE_LOADED:
                cron = CronScheduler()
                if action == "list":
                    return json.dumps([j.__dict__ for j in cron.list_jobs()], indent=2)
                elif action == "add":
                    st = args.get("schedule_type", "every")
                    expr = args.get("expression", "1h")
                    msg = args.get("message", "Heartbeat")
                    job = cron.add_job(st, expr, msg)
                    return f"Created cron job '{job.id}'."
                elif action == "remove":
                    jid = args.get("job_id", "")
                    if cron.remove_job(jid):
                        return f"Removed job '{jid}'."
                    return f"Job '{jid}' not found."
            return "Cron engine not available."

        elif func_name == "composio_execute":
            act_name = args.get("action_name", "")
            params = args.get("params", {})
            if _BRIGADE_LOADED:
                from tools.composio_tool import ComposioTool
                ct = ComposioTool()
                return json.dumps(ct.execute_action(act_name, params), indent=2)
            return "Composio connectors not available."

        return f"Error: Tool '{func_name}' is not recognized."
    except Exception as e:
        return f"Error executing '{func_name}': {str(e)}"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN AGENT ORCHESTRATION PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
def run_agent(
    user_prompt: str,
    max_iterations: int = 5,
    session_id: str = "main",
    origin: str = "owner",
    agent_id: str = "main"
) -> str:
    """
    Autonomous multi-turn execution loop:
    1. Handles in-chat slash commands (/status, /org, /agents, /skills, /cron, /doctor).
    2. Retrieves persistent context & injects Tideline long-term memory.
    3. Injects prompt-resident extensible skills catalog.
    4. Resolves active LLM client (OmniRoute Gateway -> Groq -> OpenRouter).
    5. Runs requested tool calls iteratively.
    6. Re-injects outputs back into context.
    7. Saves interaction turn to SQLite database and JSONL session stream.
    """
    if not user_prompt or not user_prompt.strip():
        return "No prompt provided."

    user_prompt_clean = user_prompt.strip()

    # ── IN-CHAT SLASH COMMANDS ──
    if user_prompt_clean.startswith("/"):
        cmd = user_prompt_clean.split()[0].lower()
        if cmd == "/status" and _BRIGADE_LOADED:
            from cli.brigade_cli import cmd_status
            import io
            buf = io.StringIO()
            sys_stdout_orig = sys.stdout
            try:
                sys.stdout = buf
                class Args: json = False
                cmd_status(Args())
                return buf.getvalue().strip()
            finally:
                sys.stdout = sys_stdout_orig
        elif cmd == "/org" and _BRIGADE_LOADED:
            return OrgChart().render_tree()
        elif cmd == "/agents" and _BRIGADE_LOADED:
            agents = AgentRegistry().list_agents()
            return "\n".join([f"• {a.get('emoji', '🤖')} **{a['name']}** (`{a['id']}`): {a.get('description', '')}" for a in agents])
        elif cmd == "/skills" and _BRIGADE_LOADED:
            skills = SkillLoader().discover_skills(agent_id=agent_id)
            return SkillLoader().build_prompt_catalog(skills)
        elif cmd == "/cron" and _BRIGADE_LOADED:
            jobs = CronScheduler().list_jobs()
            return "\n".join([f"• [{ 'ENABLED' if j.enabled else 'DISABLED' }] `{j.id}`: {j.schedule_type} '{j.expression}' -> {j.message}" for j in jobs]) or "No cron jobs configured."
        elif cmd == "/doctor" and _BRIGADE_LOADED:
            issues = OrgChart().doctor()
            return "🩺 System Status: Healthy\nOrg lints:\n" + ("\n".join(issues) if issues else "None.")
        elif cmd == "/help":
            return (
                "🦁 **Brigade & MAX Command Shortcuts**:\n"
                "• `/status` - View system, gateway, and memory status\n"
                "• `/org` - View crew Org Chart & Pride hierarchy\n"
                "• `/agents` - List active agents\n"
                "• `/skills` - View extensible skills catalog\n"
                "• `/cron` - View scheduled cron jobs\n"
                "• `/doctor` - Run health checks\n"
                "• `/abort` - Abort active run"
            )

    # Sanitize user prompt for prompt injection
    if _BRIGADE_LOADED:
        has_threat, _ = InjectionGuard.scan(user_prompt_clean)
        if has_threat:
            user_prompt_clean = InjectionGuard.sanitize(user_prompt_clean)

    # Retrieve relevant persistent memory context
    memory_context = get_context_for_prompt(user_prompt_clean, max_items=5)
    tideline_context = ""
    skills_context = ""

    if _BRIGADE_LOADED:
        try:
            ws = get_state_dir() / "workspace" if agent_id == "main" else get_state_dir() / "agents" / agent_id / "workspace"
            engine = TidelineEngine.open(ws, default_origin=origin)
            tideline_context = engine.context(user_prompt_clean, max_chars=800, origin=origin)
        except Exception:
            pass

        try:
            loader = SkillLoader()
            skills = loader.discover_skills(agent_id=agent_id)
            skills_context = loader.build_prompt_catalog(skills)
        except Exception:
            pass

    system_instruction = (
        "You are M.A.X (Mark I-OR), an autonomous AI assistant and personal intelligence coordinator. "
        "You operate with authority, intelligence, precision, and decisive tool execution.\n\n"
        "Guidelines:\n"
        "- Proactively invoke tools when asked to execute tasks, create documents, or retrieve facts.\n"
        "- Synthesize tool results cleanly, factually, and thoroughly for the user.\n"
        "- When providing news, market updates, or search results, ALWAYS provide a comprehensive, well-structured SUMMARY with key highlights, context, and bullet points. NEVER just output raw links or headline lists unless specifically asked.\n"
        f"{memory_context}\n"
        f"{tideline_context}\n\n"
        f"{skills_context}"
    )

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt_clean}
    ]

    # Save incoming user message to SQLite conversation history
    save_conversation_turn("user", user_prompt_clean)
    if _BRIGADE_LOADED:
        StorageManager().append_session_turn(agent_id, session_id, "user", user_prompt_clean)

    # Resolve active client & models (OmniRoute prioritized, with fallback to Groq / OpenRouter)
    active_client, candidate_models, provider_name = _get_active_llm_client()
    print(f"[M.A.X Brain] ⚡ Inference Provider: {provider_name}")

    if provider_name == "Unconfigured":
        reply = (
            "M.A.X Brain Notice: No active LLM endpoint found. "
            "Please start the OmniRoute Gateway via 'start_omniroute.bat' or configure your API keys in config/api_keys.json."
        )
        save_conversation_turn("assistant", reply)
        return reply

    active_model = candidate_models[0]
    iterations = 0

    while iterations < max_iterations:
        iterations += 1

        try:
            response = active_client.chat.completions.create(
                model=active_model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto"
            )
        except Exception as e:
            err_str = str(e)
            print(f"[MAX Brain] Notice on model {active_model} ({provider_name}): {err_str}")

            # Attempt automatic fallback to secondary candidate models
            fallback_success = False
            for fallback_model in candidate_models[1:]:
                try:
                    print(f"[MAX Brain] Switching to fallback model: {fallback_model}")
                    active_model = fallback_model
                    response = active_client.chat.completions.create(
                        model=active_model,
                        messages=messages,
                        tools=TOOLS,
                        tool_choice="auto"
                    )
                    fallback_success = True
                    break
                except Exception as fb_err:
                    print(f"[MAX Brain] Fallback {fallback_model} failed: {fb_err}")

            if not fallback_success:
                reply = f"M.A.X Neural Engine encountered an error: {err_str}"
                save_conversation_turn("assistant", reply)
                return reply

        choice = response.choices[0].message

        # Case 1: Final natural language synthesis achieved
        if not choice.tool_calls:
            final_content = choice.content or "Task completed successfully."
            if _BRIGADE_LOADED:
                final_content = AntiSlopDetector.clean_openers(final_content)
                StorageManager().append_session_turn(agent_id, session_id, "assistant", final_content)
            save_conversation_turn("assistant", final_content)
            return final_content

        # Case 2: Tool execution cycle
        messages.append(choice)

        for tool_call in choice.tool_calls:
            func_name = tool_call.function.name

            # Defensive argument parsing
            try:
                raw_args = tool_call.function.arguments
                args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
            except Exception as parse_err:
                print(f"[MAX Brain] Warning: JSON parsing error for {func_name}: {parse_err}")
                args = {}

            tool_result = _execute_tool_call(func_name, args)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(tool_result)
            })

    # If loop concludes without terminal text, request final synthesis
    try:
        final_summary = active_client.chat.completions.create(
            model=active_model,
            messages=messages
        )
        reply = final_summary.choices[0].message.content or "Task completed with iterative actions."
    except Exception as e:
        reply = f"Completed actions with final synthesis notice: {e}"

    if _BRIGADE_LOADED:
        reply = AntiSlopDetector.clean_openers(reply)
        StorageManager().append_session_turn(agent_id, session_id, "assistant", reply)
    save_conversation_turn("assistant", reply)
    return reply


if __name__ == "__main__":
    print("[M.A.X Brain Self-Test]")
    client, models, prov = _get_active_llm_client()
    print(f"Active Provider: {prov} (Primary Model: {models[0]})")
    test_result = _execute_tool_call("check_omniroute_gateway", {"action": "status"})
    print("OmniRoute tool test:\n", test_result)