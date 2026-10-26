"""
Data schema for Tideline records, segments, tiers, and link graphs.
"""
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Literal

FactSegment = Literal[
    "identity",
    "preference",
    "correction",
    "relationship",
    "project",
    "knowledge",
    "context"
]

FactTier = Literal["short", "long", "permanent"]

PROTECTED_SEGMENTS = {"identity", "preference", "correction"}

TIER_HALF_LIVES = {
    "short": 3 * 86400,       # 3 days
    "long": 30 * 86400,      # 30 days
    "permanent": float("inf") # Never decays
}


@dataclass
class TypedLink:
    target_id: str
    relation: Literal["supersedes", "corrects", "relates", "supports", "contradicts"]


@dataclass
class FactRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    segment: FactSegment = "knowledge"
    tier: FactTier = "long"
    importance: float = 0.5  # 0.0 to 1.0
    origin: str = "owner"    # "owner" or peer channel identifier
    source: str = "user"     # "user", "tool", "web", "inferred"
    trust_score: float = 1.0 # 0.0 to 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    decay_rate: float = 1.0
    links: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactRecord":
        clean = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**clean)
