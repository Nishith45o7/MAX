"""
Discord Messaging Adapter for Brigade & MAX.
Supports Discord bot token, DM / server / thread routing, and approvals.
"""
import os
import json
import urllib.request
import logging
from typing import Optional
from channels.base import BaseChannelAdapter, ChannelMessage
from channels.inbound_pipeline import InboundPipeline
from brigade_core.config import ConfigManager

logger = logging.getLogger("discord_adapter")


class DiscordChannelAdapter(BaseChannelAdapter):
    """Integrates Discord Gateway/REST API with Brigade Inbound Pipeline."""

    def __init__(self, config_mgr: Optional[ConfigManager] = None, pipeline: Optional[InboundPipeline] = None):
        super().__init__("discord")
        self.config_mgr = config_mgr or ConfigManager()
        self.pipeline = pipeline or InboundPipeline(self.config_mgr)
        self._is_active = False

    def get_token(self) -> Optional[str]:
        cfg = self.config_mgr.load_resolved()
        token = cfg.get("channels", {}).get("discord", {}).get("botToken")
        if token and not token.startswith("${"):
            return token
        return os.environ.get("DISCORD_BOT_TOKEN")

    def is_active(self) -> bool:
        return self._is_active

    def start(self) -> None:
        token = self.get_token()
        if not token:
            logger.info("Discord Bot Token not configured. Adapter remaining dormant.")
            return
        self._is_active = True
        logger.info("Discord Channel Adapter active.")

    def stop(self) -> None:
        self._is_active = False

    def send_message(self, recipient_id: str, text: str) -> bool:
        token = self.get_token()
        if not token:
            return False
        url = f"https://discord.com/api/v10/channels/{recipient_id}/messages"
        payload = json.dumps({"content": text}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bot {token}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10):
                return True
        except Exception as e:
            logger.error(f"Failed to send Discord message: {e}")
            return False

    def send_media(self, recipient_id: str, file_path: str, caption: Optional[str] = None) -> bool:
        return self.send_message(recipient_id, f"[Media: {file_path}]\n{caption or ''}")
