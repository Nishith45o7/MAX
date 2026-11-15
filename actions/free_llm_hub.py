"""
actions/free_llm_hub.py
Multi-provider free LLM API hub — discover, test, and benchmark 15+ free inference
endpoints.  Inspired by awesome-freellm-apis, MiniCPM, OmniVoice, granite-speech.
"""

import json
import time
import logging
import requests
from pathlib import Path
from typing import Optional

logger = logging.getLogger("free_llm_hub")
USER_AGENT = "MAX-MARK-I/1.0 (Autonomous Assistant)"
TIMEOUT = 6.0

# ── Provider Database ────────────────────────────────────────────────────────
PROVIDERS = {
    "groq": {
        "name": "Groq Cloud",
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it"],
        "free": True, "rps": 30, "context": 131072,
        "notes": "Ultra-fast inference on custom LPUs. Free tier with generous limits.",
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "models": [
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemma-3-27b-it:free",
            "google/gemma-4-31b-it:free",
            "qwen/qwen3-coder:free",
            "minimax/minimax-m2.5:free",
        ],
        "free": True, "context": 131072,
        "notes": "Aggregator with 20+ free-tier models. Best variety.",
    },
    "google_gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "models": ["gemini-2.5-flash", "gemini-2.0-flash"],
        "free": True, "rpm": 15, "context": 1048576,
        "notes": "1M context, native tool-calling, multimodal. 15 RPM free.",
    },
    "cerebras": {
        "name": "Cerebras",
        "base_url": "https://api.cerebras.ai/v1",
        "models": ["llama-3.3-70b", "llama-3.1-8b"],
        "free": True, "context": 8192,
        "notes": "Fastest open-model inference. Free developer tier.",
    },
    "sambanova": {
        "name": "SambaNova",
        "base_url": "https://api.sambanova.ai/v1",
        "models": ["Meta-Llama-3.3-70B-Instruct", "DeepSeek-R1-Distill-Llama-70B"],
        "free": True, "context": 8192,
        "notes": "Custom RDU chip. Free community tier.",
    },
    "deepinfra": {
        "name": "DeepInfra",
        "base_url": "https://api.deepinfra.com/v1/openai",
        "models": ["meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen2.5-72B-Instruct"],
        "free": False, "context": 32768,
        "notes": "Pay-per-token with free credits on signup.",
    },
    "together": {
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "models": ["meta-llama/Llama-3.3-70B-Instruct-Turbo", "deepseek-ai/DeepSeek-R1"],
        "free": False, "context": 131072,
        "notes": "$5 free credits on signup. Fast serverless.",
    },
    "novita": {
        "name": "Novita AI",
        "base_url": "https://api.novita.ai/v3/openai",
        "models": ["meta-llama/llama-3.1-8b-instruct"],
        "free": True, "context": 8192,
        "notes": "Free tier for small models.",
    },
    "glhf": {
        "name": "GLHF Chat",
        "base_url": "https://glhf.chat/api/openai/v1",
        "models": ["hf:meta-llama/Llama-3.3-70B-Instruct"],
        "free": True, "context": 16384,
        "notes": "Free HuggingFace model hosting with OpenAI-compat API.",
    },
    "chutes": {
        "name": "Chutes AI",
        "base_url": "https://llm.chutes.ai/v1",
        "models": ["deepseek-ai/DeepSeek-V3-0324"],
        "free": True, "context": 65536,
        "notes": "Free DeepSeek hosting.",
    },
    "huggingface": {
        "name": "HuggingFace Inference",
        "base_url": "https://api-inference.huggingface.co",
        "models": ["meta-llama/Llama-3.3-70B-Instruct", "mistralai/Mistral-7B-Instruct-v0.3"],
        "free": True, "context": 8192,
        "notes": "Free serverless inference. Rate-limited per model.",
    },
    "omniroute_local": {
        "name": "OmniRoute Local Gateway",
        "base_url": "http://localhost:20128/v1",
        "models": ["auto"],
        "free": True, "local": True, "context": 131072,
        "notes": "Local gateway routing to 375+ providers. Start via start_omniroute.bat.",
    },
    "pollinations": {
        "name": "Pollinations AI",
        "base_url": "https://text.pollinations.ai/openai",
        "models": ["openai", "mistral", "llama"],
        "free": True, "context": 8192,
        "notes": "Fully free text + image generation. No API key needed.",
    },
    "lepton": {
        "name": "Lepton AI",
        "base_url": "https://llama3-3-70b.lepton.run/api/v1",
        "models": ["llama3-3-70b"],
        "free": False, "context": 8192,
        "notes": "Fast serverless with free trial credits.",
    },
}


def _ping_endpoint(url: str, timeout: float = 4.0) -> dict:
    """Quick HEAD/GET ping to check if an endpoint is reachable."""
    try:
        start = time.perf_counter()
        resp = requests.head(url, timeout=timeout, headers={"User-Agent": USER_AGENT}, allow_redirects=True)
        latency = round((time.perf_counter() - start) * 1000, 1)
        return {"reachable": resp.status_code < 500, "status": resp.status_code, "latency_ms": latency}
    except requests.exceptions.Timeout:
        return {"reachable": False, "status": 0, "latency_ms": timeout * 1000, "error": "timeout"}
    except Exception as e:
        return {"reachable": False, "status": 0, "latency_ms": 0, "error": str(e)}


def free_llm_hub(parameters: dict, player=None) -> str:
    """Multi-provider free LLM API hub."""
    action = (parameters.get("action") or "list_providers").strip().lower()
    aliases = {
        "list": "list_providers", "providers": "list_providers", "test": "test_provider",
        "discover": "discover_models", "models": "discover_models", "info": "provider_info"
    }
    action = aliases.get(action, action)

    if action == "list_providers":
        lines = ["🌐 Free LLM API Providers (MAX Hub):\n"]
        for pid, p in PROVIDERS.items():
            free_tag = "✅ FREE" if p.get("free") else "💰 Credits"
            local_tag = " 🏠 LOCAL" if p.get("local") else ""
            ctx = p.get("context", "?")
            models_str = ", ".join(p["models"][:3])
            lines.append(
                f"  • {p['name']} ({pid}){local_tag} [{free_tag}]\n"
                f"    Models: {models_str}\n"
                f"    Context: {ctx:,} tokens | {p.get('notes', '')}"
            )
        lines.append(f"\nTotal: {len(PROVIDERS)} providers | "
                      f"{sum(1 for p in PROVIDERS.values() if p.get('free'))} free-tier")
        return "\n".join(lines)

    elif action == "test_provider":
        provider_id = (parameters.get("provider") or "").strip().lower()
        if provider_id not in PROVIDERS:
            return f"Unknown provider '{provider_id}'. Use action 'list_providers' to see available ones."
        p = PROVIDERS[provider_id]
        result = _ping_endpoint(p["base_url"])
        status = "🟢 Online" if result["reachable"] else "🔴 Offline"
        return (
            f"Provider Test: {p['name']}\n"
            f"• Endpoint: {p['base_url']}\n"
            f"• Status: {status} (HTTP {result['status']})\n"
            f"• Latency: {result['latency_ms']}ms\n"
            f"• Models: {', '.join(p['models'])}"
        )

    elif action == "benchmark":
        results = []
        for pid, p in PROVIDERS.items():
            if p.get("local") and pid == "omniroute_local":
                res = _ping_endpoint(p["base_url"], timeout=2.0)
            else:
                res = _ping_endpoint(p["base_url"], timeout=5.0)
            tag = "🟢" if res["reachable"] else "🔴"
            results.append((pid, p["name"], res["latency_ms"], res["reachable"], tag))
        results.sort(key=lambda x: (not x[3], x[2]))
        lines = ["⚡ LLM Provider Benchmark (by latency):\n"]
        for i, (pid, name, lat, up, tag) in enumerate(results, 1):
            lines.append(f"  {i:2d}. {tag} {name:<25s}  {lat:>7.1f}ms")
        online = sum(1 for r in results if r[3])
        lines.append(f"\n{online}/{len(results)} providers online")
        return "\n".join(lines)

    elif action == "discover_models":
        provider_id = (parameters.get("provider") or "").strip().lower()
        if provider_id not in PROVIDERS:
            return f"Unknown provider '{provider_id}'."
        p = PROVIDERS[provider_id]
        models_url = p["base_url"].rstrip("/") + "/models"
        try:
            resp = requests.get(models_url, timeout=TIMEOUT,
                                headers={"User-Agent": USER_AGENT})
            if resp.status_code == 200:
                data = resp.json()
                model_list = data.get("data", data.get("models", []))
                if isinstance(model_list, list):
                    names = [m.get("id", m.get("name", str(m))) for m in model_list[:30]]
                    return (
                        f"Models on {p['name']} ({len(names)} shown):\n"
                        + "\n".join(f"  • {n}" for n in names)
                    )
            return f"Could not discover models from {p['name']} (HTTP {resp.status_code}). Listed models: {', '.join(p['models'])}"
        except Exception as e:
            return f"Discovery failed for {p['name']}: {e}. Known models: {', '.join(p['models'])}"

    elif action == "provider_info":
        provider_id = (parameters.get("provider") or "").strip().lower()
        if provider_id not in PROVIDERS:
            return f"Unknown provider '{provider_id}'."
        p = PROVIDERS[provider_id]
        free_tag = "Yes" if p.get("free") else "No (credits/paid)"
        return (
            f"📋 {p['name']} Details:\n"
            f"• Endpoint: {p['base_url']}\n"
            f"• Free Tier: {free_tag}\n"
            f"• Context Window: {p.get('context', 'Unknown'):,} tokens\n"
            f"• Models: {', '.join(p['models'])}\n"
            f"• Notes: {p.get('notes', 'N/A')}"
        )

    else:
        return (
            f"Unknown action '{action}'. Available: "
            "list_providers, test_provider, benchmark, discover_models, provider_info"
        )


if __name__ == "__main__":
    print(free_llm_hub({"action": "list_providers"}))
    print("\n" + free_llm_hub({"action": "test_provider", "provider": "groq"}))
    print("\n" + free_llm_hub({"action": "provider_info", "provider": "google_gemini"}))

