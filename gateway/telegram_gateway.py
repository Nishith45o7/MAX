import os
import sys
import json
import time
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Set

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
DESKTOP_DIR = Path.home() / "Desktop"

import max_brain
from memory.db import save_conversation_turn

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("telegram_gateway")

try:
    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        ContextTypes,
        filters
    )
    _TELEGRAM_AVAILABLE = True
except ImportError:
    _TELEGRAM_AVAILABLE = False


def _load_telegram_config() -> tuple[str, Set[int]]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    allowed_ids: Set[int] = set()

    env_ids = os.environ.get("TELEGRAM_ALLOWED_USERS", "")
    if env_ids:
        for x in env_ids.split(","):
            if x.strip().isdigit():
                allowed_ids.add(int(x.strip()))

    if API_CONFIG_PATH.exists():
        try:
            with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not token:
                token = data.get("telegram_bot_token", "").strip()
            conf_ids = data.get("telegram_allowed_users", [])
            if isinstance(conf_ids, list):
                for uid in conf_ids:
                    if str(uid).isdigit():
                        allowed_ids.add(int(uid))
        except Exception as e:
            logger.warning(f"Error reading api_keys.json: {e}")

    return token, allowed_ids


def _is_user_authorized(user_id: int, allowed_ids: Set[int]) -> bool:
    if not allowed_ids:
        # If no allowlist is configured, permit first user or log warning
        return True
    return user_id in allowed_ids


def _get_recent_desktop_files(since_timestamp: float) -> List[Path]:
    """Finds newly created .pptx, .pdf, or doc files on Desktop since execution started."""
    results = []
    try:
        if DESKTOP_DIR.exists():
            for f in DESKTOP_DIR.iterdir():
                if f.is_file() and f.suffix.lower() in [".pptx", ".pdf", ".docx", ".png", ".jpg"]:
                    try:
                        if f.stat().st_mtime >= since_timestamp:
                            results.append(f)
                    except Exception:
                        pass
    except Exception as e:
        logger.warning(f"Error checking recent desktop files: {e}")
    return results


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = (
        f"🤖 *MARK I-OR (M.A.X) Mobile Gateway*\n\n"
        f"Greetings, {user.first_name if user else 'Sir'}!\n"
        f"I am connected to your host workstation. You can send text commands or voice messages to execute actions, run searches, and control the computer."
    )
    if update.message:
        await update.message.reply_text(msg, parse_mode="Markdown")


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        batt = psutil.sensors_battery()
        batt_str = f"{batt.percent}% ({'Plugged In' if batt.power_plugged else 'Battery'})" if batt else "N/A"
        
        status_msg = (
            f"⚡ *Workstation Status (M.A.X)*\n"
            f"• CPU Usage: `{cpu:.1f}%`\n"
            f"• Memory: `{ram:.1f}%`\n"
            f"• Battery: `{batt_str}`\n"
            f"• State: `ACTIVE / READY`"
        )
    except Exception as e:
        status_msg = f"Status error: {e}"

    if update.message:
        await update.message.reply_text(status_msg, parse_mode="Markdown")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    token, allowed_ids = _load_telegram_config()
    if not _is_user_authorized(user_id, allowed_ids):
        await update.message.reply_text("⛔ Access denied: You are not authorized on this host.")
        return

    user_text = update.message.text.strip()
    logger.info(f"Received text command from {user_id}: {user_text}")

    # Visual feedback: Send initial status
    status_msg = await update.message.reply_text("🧠 *M.A.X is thinking...*", parse_mode="Markdown")
    start_time = time.time()

    # Run agent in background executor to prevent event-loop block
    loop = asyncio.get_running_loop()
    try:
        reply = await loop.run_in_executor(None, max_brain.run_agent, user_text)
    except Exception as e:
        reply = f"Execution error in M.A.X Brain: {e}"

    # Update status message with result
    try:
        await status_msg.edit_text(reply)
    except Exception:
        await update.message.reply_text(reply)

    # Check if files were generated during this run and send them
    new_files = _get_recent_desktop_files(start_time - 2)
    for nf in new_files:
        try:
            with open(nf, "rb") as doc_f:
                await update.message.reply_document(document=doc_f, caption=f"Generated: {nf.name}")
        except Exception as fe:
            logger.error(f"Error sending file {nf}: {fe}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.voice:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    token, allowed_ids = _load_telegram_config()
    if not _is_user_authorized(user_id, allowed_ids):
        await update.message.reply_text("⛔ Access denied: You are not authorized on this host.")
        return

    status_msg = await update.message.reply_text("🎙 *Transcribing voice message...*", parse_mode="Markdown")
    
    # Download voice file
    voice_file = await update.message.voice.get_file()
    temp_dir = BASE_DIR / "gateway" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"voice_{int(time.time())}.oga"
    await voice_file.download_to_drive(str(temp_path))

    transcription = ""
    # Transcribe using Groq Whisper API
    try:
        groq_key = max_brain._load_api_key()
        if groq_key and groq_key != "YOUR_GROQ_API_KEY_HERE":
            from openai import OpenAI
            whisper_client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key
            )
            with open(temp_path, "rb") as af:
                trans_obj = whisper_client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=af
                )
                transcription = trans_obj.text.strip()
    except Exception as e:
        logger.warning(f"Groq Whisper transcription failed: {e}")

    # Clean up temp file
    try:
        temp_path.unlink()
    except Exception:
        pass

    if not transcription:
        await status_msg.edit_text("❌ Could not transcribe voice note. Please ensure audio is clear or GROQ_API_KEY is configured.")
        return

    await status_msg.edit_text(f"🗣 *Voice Transcription:*\n\"{transcription}\"\n\n🧠 *Executing...*", parse_mode="Markdown")

    start_time = time.time()
    loop = asyncio.get_running_loop()
    try:
        reply = await loop.run_in_executor(None, max_brain.run_agent, transcription)
    except Exception as e:
        reply = f"Execution error in M.A.X Brain: {e}"

    await update.message.reply_text(reply)

    # Check if files were generated during this run and send them
    new_files = _get_recent_desktop_files(start_time - 2)
    for nf in new_files:
        try:
            with open(nf, "rb") as doc_f:
                await update.message.reply_document(document=doc_f, caption=f"Generated: {nf.name}")
        except Exception as fe:
            logger.error(f"Error sending file {nf}: {fe}")


def run_telegram_daemon():
    """Starts the Telegram Bot long-polling daemon."""
    if not _TELEGRAM_AVAILABLE:
        print("[Telegram Gateway] Error: python-telegram-bot is not installed.")
        return

    token, allowed_ids = _load_telegram_config()
    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("[Telegram Gateway] Info: TELEGRAM_BOT_TOKEN is not configured in environment or config/api_keys.json.")
        print("[Telegram Gateway] Set 'telegram_bot_token' in config/api_keys.json to enable remote mobile access.")
        return

    print(f"[Telegram Gateway] Starting M.A.X Telegram Gateway daemon...")
    if allowed_ids:
        print(f"[Telegram Gateway] Authorized user IDs: {allowed_ids}")
    else:
        print("[Telegram Gateway] Warning: No allowed user IDs restricted. Anyone with the bot link can send commands.")

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("status", status_cmd))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    application.run_polling()


if __name__ == "__main__":
    run_telegram_daemon()
