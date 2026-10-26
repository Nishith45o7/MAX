"""
Base Channel Adapter Contract and Data Models.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time


@dataclass
class ChannelMessage:
    channel: str
    account_id: str
    sender_id: str
    sender_name: str
    message_id: str
    text: str
    attachments: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class InboundResult:
    status: str  # "allowed", "pairing_required", "aborted", "duplicate", "ignored"
    response_text: Optional[str] = None
    session_key: Optional[str] = None
    target_agent: str = "main"
    is_owner: bool = False


class BaseChannelAdapter(ABC):
    """Abstract interface for messaging channel adapters."""

    def __init__(self, channel_name: str):
        self.channel_name = channel_name

    @abstractmethod
    def start(self) -> None:
        """Starts listening or polling for incoming messages."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops the channel adapter."""
        pass

    @abstractmethod
    def send_message(self, recipient_id: str, text: str) -> bool:
        """Sends an outbound message to a peer or room."""
        pass

    @abstractmethod
    def send_media(self, recipient_id: str, file_path: str, caption: Optional[str] = None) -> bool:
        """Sends an outbound media/document file."""
        pass

    @abstractmethod
    def is_active(self) -> bool:
        """Returns True if the adapter is running and connected."""
        pass
