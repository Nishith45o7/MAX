"""
Shared Inbound Messaging Pipeline.
Handles message deduplication, abort triggers, pairing code challenges,
allowlist enforcement, and channel-to-agent session resolution.
"""
import time
import json
import secrets
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from channels.base import ChannelMessage, InboundResult
from brigade_core import get_state_dir
from brigade_core.config import ConfigManager


class InboundPipeline:
    """Processes incoming channel messages through security, pairing, and routing gates."""

    def __init__(self, config_mgr: Optional[ConfigManager] = None):
        self.config_mgr = config_mgr or ConfigManager()
        self.state_dir = get_state_dir()
        self.seen_messages: Dict[str, float] = {}  # msg_id -> timestamp
        self.active_turn_aborts: Dict[str, bool] = {}  # session_key -> abort_flag
        self.pending_pairings: Dict[str, Dict[str, Any]] = {}  # code -> pairing_info
        self._load_pairings()

    def _pairings_file(self) -> Path:
        p = self.state_dir / "channels" / "pairings.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _load_pairings(self) -> None:
        pf = self._pairings_file()
        if pf.exists():
            try:
                with open(pf, "r", encoding="utf-8") as f:
                    self.pending_pairings = json.load(f)
            except Exception:
                self.pending_pairings = {}

    def _save_pairings(self) -> None:
        with open(self._pairings_file(), "w", encoding="utf-8") as f:
            json.dump(self.pending_pairings, f, indent=2)

    def process_inbound(self, msg: ChannelMessage) -> InboundResult:
        now = time.time()

        # 1. Deduplication
        dedup_key = f"{msg.channel}:{msg.message_id}"
        if dedup_key in self.seen_messages:
            if now - self.seen_messages[dedup_key] < 300:
                return InboundResult(status="duplicate")
        self.seen_messages[dedup_key] = now

        # Derive isolated session key
        session_key = f"{msg.channel}_{msg.sender_id}"

        # 2. Abort trigger check
        clean_text = msg.text.strip().lower()
        if clean_text in ["/abort", "/stop", "!stop", "!abort"]:
            self.active_turn_aborts[session_key] = True
            return InboundResult(
                status="aborted",
                response_text="🛑 Active turn aborted.",
                session_key=session_key
            )

        # 3. Access control & Pairing check
        cfg = self.config_mgr.load_raw()
        channel_cfg = cfg.get("channels", {}).get(msg.channel, {})
        allowed_users = channel_cfg.get("allowedUsers", [])
        channel_owner = channel_cfg.get("ownerId")

        sender_str = str(msg.sender_id)
        is_owner = (channel_owner == sender_str) or (len(allowed_users) == 0 and not channel_owner)

        # First sender becomes owner if none configured
        if is_owner and not channel_owner:
            channel_cfg["ownerId"] = sender_str
            if sender_str not in allowed_users:
                allowed_users.append(sender_str)
            channel_cfg["allowedUsers"] = allowed_users
            self.config_mgr.save(cfg)

        # Check if sender is admitted
        if not is_owner and sender_str not in allowed_users:
            # Generate or retrieve pairing code
            existing_code = None
            for code, info in self.pending_pairings.items():
                if info.get("channel") == msg.channel and str(info.get("sender_id")) == sender_str:
                    existing_code = code
                    break

            if not existing_code:
                existing_code = secrets.token_hex(3).upper()  # 6-char code
                self.pending_pairings[existing_code] = {
                    "code": existing_code,
                    "channel": msg.channel,
                    "sender_id": sender_str,
                    "sender_name": msg.sender_name,
                    "created_at": now
                }
                self._save_pairings()

            challenge = (
                f"🔒 *Access Restricted*\n\n"
                f"Greetings! Your pairing code is: `{existing_code}`\n\n"
                f"Please ask the bot owner to approve your access:\n"
                f"`brigade pairing approve {existing_code} --channel {msg.channel}`\n"
                f"or in Telegram/Discord chat: `/approve {existing_code}`"
            )
            return InboundResult(
                status="pairing_required",
                response_text=challenge,
                session_key=session_key,
                is_owner=False
            )

        # 4. Resolve Target Agent
        target_agent = "main"
        # Check if message targets agent explicitly (e.g. /agent coder or @coder)
        if clean_text.startswith("/agent "):
            parts = clean_text.split()
            if len(parts) > 1:
                target_agent = parts[1]

        return InboundResult(
            status="allowed",
            session_key=session_key,
            target_agent=target_agent,
            is_owner=is_owner
        )

    def approve_pairing(self, code: str, channel: Optional[str] = None) -> Tuple[bool, str]:
        """Approves a waiting sender and adds them to the channel allowlist."""
        code = code.strip().upper()
        info = self.pending_pairings.get(code)
        if not info:
            return False, f"No pending pairing code '{code}' found."

        ch = info["channel"]
        sender_id = info["sender_id"]

        cfg = self.config_mgr.load_raw()
        channel_cfg = cfg.setdefault("channels", {}).setdefault(ch, {})
        allowed = channel_cfg.setdefault("allowedUsers", [])

        if sender_id not in allowed:
            allowed.append(sender_id)
            self.config_mgr.save(cfg)

        del self.pending_pairings[code]
        self._save_pairings()
        return True, f"Successfully approved {info.get('sender_name', sender_id)} ({sender_id}) for channel '{ch}'."

    def deny_pairing(self, code: str) -> bool:
        code = code.strip().upper()
        if code in self.pending_pairings:
            del self.pending_pairings[code]
            self._save_pairings()
            return True
        return False
