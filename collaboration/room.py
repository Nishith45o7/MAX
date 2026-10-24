"""
Durable Collaboration Rooms and Messaging for Team Mode.
Supports persistent rooms, threads, replies, explicit agent mentions, and attachments.
"""
import time
import json
import uuid
import re
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from brigade_core import get_state_dir


@dataclass
class RoomMessage:
    id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}")
    room_id: str = ""
    sender: str = "main"
    content: str = ""
    thread_id: Optional[str] = None
    mentions: List[str] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass
class TeamRoom:
    id: str
    name: str
    topic: str = ""
    members: List[str] = field(default_factory=lambda: ["main"])
    archived: bool = False
    created_at: float = field(default_factory=time.time)


class TeamRoomManager:
    """Manages persistent rooms and message streams."""

    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = state_dir or get_state_dir()
        self.collab_dir = self.state_dir / "collaboration" / "rooms"
        self.collab_dir.mkdir(parents=True, exist_ok=True)

    def _room_file(self, room_id: str) -> Path:
        return self.collab_dir / f"{room_id}.json"

    def _messages_file(self, room_id: str) -> Path:
        return self.collab_dir / f"{room_id}_messages.jsonl"

    def create_room(self, name: str, topic: str = "", members: Optional[List[str]] = None) -> TeamRoom:
        room_id = f"room_{uuid.uuid4().hex[:6]}"
        room = TeamRoom(
            id=room_id,
            name=name,
            topic=topic,
            members=members or ["main"]
        )
        with open(self._room_file(room_id), "w", encoding="utf-8") as f:
            json.dump(asdict(room), f, indent=2)
        return room

    def get_room(self, room_id: str) -> Optional[TeamRoom]:
        rf = self._room_file(room_id)
        if not rf.exists():
            return None
        with open(rf, "r", encoding="utf-8") as f:
            return TeamRoom(**json.load(f))

    def list_rooms(self) -> List[TeamRoom]:
        rooms = []
        for f in self.collab_dir.glob("room_*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    rooms.append(TeamRoom(**json.load(fp)))
            except Exception:
                pass
        return rooms

    def post_message(
        self,
        room_id: str,
        sender: str,
        content: str,
        thread_id: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> RoomMessage:
        """Posts a message to the room and auto-extracts @mentions."""
        room = self.get_room(room_id)
        if not room:
            raise ValueError(f"Room '{room_id}' not found.")
        if room.archived:
            raise ValueError(f"Cannot post to archived room '{room_id}'.")

        # Extract @mentions
        mentions = re.findall(r"@([a-zA-Z0-9_-]+)", content)

        msg = RoomMessage(
            room_id=room_id,
            sender=sender,
            content=content,
            thread_id=thread_id,
            mentions=mentions,
            attachments=attachments or []
        )

        with open(self._messages_file(room_id), "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(msg), ensure_ascii=False) + "\n")

        return msg

    def get_messages(self, room_id: str, thread_id: Optional[str] = None, limit: int = 50) -> List[RoomMessage]:
        mf = self._messages_file(room_id)
        if not mf.exists():
            return []
        msgs = []
        with open(mf, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        m = RoomMessage(**json.loads(line))
                        if thread_id is None or m.thread_id == thread_id:
                            msgs.append(m)
                    except Exception:
                        pass
        return msgs[-limit:]
