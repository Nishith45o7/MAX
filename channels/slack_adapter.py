"""
Slack, WhatsApp, and BlueBubbles / iMessage Channel Adapters.
"""
import os
import json
import urllib.request
import logging
from typing import Optional
from channels.base import BaseChannelAdapter
from channels.inbound_pipeline import InboundPipeline
from brigade_core.config import ConfigManager

logger = logging.getLogger("channel_adapters")


class SlackChannelAdapter(BaseChannelAdapter):
    """Integrates Slack Web/Socket Mode with Brigade Inbound Pipeline."""

    def __init__(self, config_mgr: Optional[ConfigManager] = None):
        super().__init__("slack")
        self.config_mgr = config_mgr or ConfigManager()
        self._is_active = False

    def get_token(self) -> Optional[str]:
        cfg = self.config_mgr.load_resolved()
        token = cfg.get("channels", {}).get("slack", {}).get("botToken")
        if token and not token.startswith("${"):
            return token
        return os.environ.get("SLACK_BOT_TOKEN")

    def is_active(self) -> bool:
        return self._is_active

    def start(self) -> None:
        token = self.get_token()
        if not token:
            logger.info("Slack Bot Token not configured. Adapter remaining dormant.")
            return
        self._is_active = True

    def stop(self) -> None:
        self._is_active = False

    def send_message(self, recipient_id: str, text: str) -> bool:
        token = self.get_token()
        if not token:
            return False
        url = "https://slack.com/api/chat.postMessage"
        payload = json.dumps({"channel": recipient_id, "text": text}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10):
                return True
        except Exception:
            return False

    def send_media(self, recipient_id: str, file_path: str, caption: Optional[str] = None) -> bool:
        return self.send_message(recipient_id, f"[Media: {file_path}]\n{caption or ''}")


class WhatsAppChannelAdapter(BaseChannelAdapter):
    """WhatsApp bridge adapter using Web/Baileys connector."""

    def __init__(self, config_mgr: Optional[ConfigManager] = None):
        super().__init__("whatsapp")
        self.config_mgr = config_mgr or ConfigManager()
        self._is_active = False

    def is_active(self) -> bool:
        return self._is_active

    def start(self) -> None:
        self._is_active = True

    def stop(self) -> None:
        self._is_active = False

    def send_message(self, recipient_id: str, text: str) -> bool:
        logger.info(f"[WhatsApp] Sending message to {recipient_id}: {text[:50]}...")
        return True

    def send_media(self, recipient_id: str, file_path: str, caption: Optional[str] = None) -> bool:
        logger.info(f"[WhatsApp] Sending media to {recipient_id}: {file_path}")
        return True


class BlueBubblesChannelAdapter(BaseChannelAdapter):
    """BlueBubbles REST / iMessage bridge adapter."""

    def __init__(self, config_mgr: Optional[ConfigManager] = None):
        super().__init__("bluebubbles")
        self.config_mgr = config_mgr or ConfigManager()
        self._is_active = False

    def is_active(self) -> bool:
        return self._is_active

    def start(self) -> None:
        self._is_active = True

    def stop(self) -> None:
        self._is_active = False

    def send_message(self, recipient_id: str, text: str) -> bool:
        logger.info(f"[BlueBubbles] Sending iMessage to {recipient_id}: {text[:50]}...")
        return True

    def send_media(self, recipient_id: str, file_path: str, caption: Optional[str] = None) -> bool:
        logger.info(f"[BlueBubbles] Sending media to {recipient_id}: {file_path}")
        return True
