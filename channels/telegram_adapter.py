"""
Telegram Messaging Adapter with Inbound Pipeline, Pairing Codes, and Interactive Approvals.
"""
import os
import json
import logging
from typing import Optional, Set
from channels.base import BaseChannelAdapter, ChannelMessage
from channels.inbound_pipeline import InboundPipeline
from brigade_core.config import ConfigManager

logger = logging.getLogger("telegram_adapter")


class TelegramChannelAdapter(BaseChannelAdapter):
    """Integrates Telegram Bot API with Brigade Inbound Pipeline and MAX Brain."""

    def __init__(self, config_mgr: Optional[ConfigManager] = None, pipeline: Optional[InboundPipeline] = None):
        super().__init__("telegram")
        self.config_mgr = config_mgr or ConfigManager()
        self.pipeline = pipeline or InboundPipeline(self.config_mgr)
        self.app = None
        self._is_active = False

    def get_token(self) -> Optional[str]:
        cfg = self.config_mgr.load_resolved()
        token = cfg.get("channels", {}).get("telegram", {}).get("botToken")
        if token and not token.startswith("${"):
            return token
        return os.environ.get("TELEGRAM_BOT_TOKEN")

    def is_active(self) -> bool:
        return self._is_active

    def start(self) -> None:
        token = self.get_token()
        if not token:
            logger.warning("Telegram Bot Token not configured. Adapter remaining dormant.")
            return

        try:
            from telegram.ext import Application, CommandHandler, MessageHandler, filters
            from telegram import Update
            from telegram.ext import ContextTypes

            self.app = Application.builder().token(token).build()

            async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
                if not update.effective_message or not update.effective_user:
                    return

                msg_text = update.effective_message.text or ""
                sender_id = str(update.effective_user.id)
                sender_name = update.effective_user.first_name or "User"

                ch_msg = ChannelMessage(
                    channel="telegram",
                    account_id="default",
                    sender_id=sender_id,
                    sender_name=sender_name,
                    message_id=str(update.effective_message.message_id),
                    text=msg_text
                )

                # Process through pipeline
                res = self.pipeline.process_inbound(ch_msg)

                if res.status == "duplicate":
                    return

                if res.status in ["pairing_required", "aborted"] and res.response_text:
                    await update.effective_message.reply_text(res.response_text, parse_mode="Markdown")
                    return

                if res.status == "allowed":
                    # Check owner management commands
                    if res.is_owner and msg_text.startswith("/approve "):
                        code = msg_text.split(maxsplit=1)[1]
                        ok, text = self.pipeline.approve_pairing(code, "telegram")
                        await update.effective_message.reply_text(text)
                        return

                    if res.is_owner and msg_text.startswith("/pending"):
                        pairings = [f"- `{c}`: {info.get('sender_name')} ({info.get('sender_id')})" for c, info in self.pipeline.pending_pairings.items()]
                        reply = "Pending Requests:\n" + ("\n".join(pairings) if pairings else "None.")
                        await update.effective_message.reply_text(reply, parse_mode="Markdown")
                        return

                    # Normal turn: run agent
                    from max_brain import run_agent
                    await update.effective_message.reply_chat_action("typing")
                    output = run_agent(msg_text, session_id=res.session_key, origin=f"telegram:{sender_id}")
                    await update.effective_message.reply_text(output)

            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            self.app.add_handler(CommandHandler(["start", "help", "pending", "approve", "abort", "agent"], handle_message))

            self._is_active = True
            logger.info("Telegram Channel Adapter initialized.")
        except Exception as e:
            logger.error(f"Failed to start Telegram adapter: {e}")
            self._is_active = False

    def stop(self) -> None:
        self._is_active = False
        if self.app:
            try:
                self.app.stop()
            except Exception:
                pass

    def send_message(self, recipient_id: str, text: str) -> bool:
        token = self.get_token()
        if not token:
            return False
        import urllib.request
        import urllib.parse
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({"chat_id": recipient_id, "text": text, "parse_mode": "Markdown"}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10):
                return True
        except Exception:
            return False

    def send_media(self, recipient_id: str, file_path: str, caption: Optional[str] = None) -> bool:
        # Document sending via Telegram API
        return self.send_message(recipient_id, f"[Media Attachment: {file_path}]\n{caption or ''}")
