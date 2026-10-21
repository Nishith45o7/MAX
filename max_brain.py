import json
import os
import sys
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

        return f"Error: Tool '{func_name}' is not recognized."
    except Exception as e:
        return f"Error executing '{func_name}': {str(e)}"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN AGENT ORCHESTRATION PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
def run_agent(user_prompt: str, max_iterations: int = 5) -> str:
    """
    Autonomous multi-turn execution loop:
    1. Retrieves persistent context & injects memory.
    2. Resolves active LLM client (OmniRoute Gateway -> Groq -> OpenRouter).
    3. Runs requested tool calls iteratively.
    4. Re-injects outputs back into context.
    5. Saves interaction turn to SQLite database.
    """
    if not user_prompt or not user_prompt.strip():
        return "No prompt provided."

    user_prompt_clean = user_prompt.strip()

    # Retrieve relevant persistent memory context
    memory_context = get_context_for_prompt(user_prompt_clean, max_items=5)

    system_instruction = (
        "You are M.A.X (Mark I-OR), an autonomous AI assistant and digital companion. "
        "You operate with authority, intelligence, and precision.\n"
        "Available Capabilities:\n"
        "- 'search_web': Live search for recent news, events, or real-time research.\n"
        "- 'create_styled_presentation': Build customized .pptx decks with dynamic HEX palettes.\n"
        "- 'create_pdf': Generate formatted reports on the user's Desktop.\n"
        "- 'launch_application': Launch desktop apps (notepad, chrome, vscode, calc, etc.).\n"
        "- 'adjust_computer_settings': Control volume, check battery status, sleep display, etc.\n"
        "- 'manage_local_files': List folders, read files, check existence, or write files.\n"
        "- 'check_omniroute_gateway': Check status, view active models, or start OmniRoute local AI gateway.\n"
        "- 'get_live_weather': Live weather & 3-day forecast for any city or current location (wttr.in).\n"
        "- 'get_crypto_currency_rates': Real-time crypto prices (CoinGecko) and fiat conversions (Frankfurter).\n"
        "- 'get_wikipedia_summary': Instant encyclopedic summaries for concepts, people, science, or places.\n"
        "- 'get_top_tech_news': Trending technology & AI headlines from Hacker News.\n"
        "- 'get_ip_geolocation': Host network insights, current city, timezone, and ISP.\n"
        "Guidelines:\n"
        "- Proactively invoke tools when asked to execute tasks or retrieve facts.\n"
        "- Synthesize tool results cleanly and succinctly for the user.\n"
        f"{memory_context}"
    )

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt_clean}
    ]

    # Save incoming user message to SQLite conversation history
    save_conversation_turn("user", user_prompt_clean)

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

    save_conversation_turn("assistant", reply)
    return reply


if __name__ == "__main__":
    print("[M.A.X Brain Self-Test]")
    client, models, prov = _get_active_llm_client()
    print(f"Active Provider: {prov} (Primary Model: {models[0]})")
    test_result = _execute_tool_call("check_omniroute_gateway", {"action": "status"})
    print("OmniRoute tool test:\n", test_result)