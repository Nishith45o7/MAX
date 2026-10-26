"""
Parser for SKILL.md files.
Extracts YAML frontmatter (metadata, name, description, eligibility) and markdown instructions
without external dependencies.
"""
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class SkillDefinition:
    name: str
    description: str
    instructions: str
    path: Path
    eligibility_os: List[str] = field(default_factory=list)
    eligibility_binaries: List[str] = field(default_factory=list)
    eligibility_env: List[str] = field(default_factory=list)
    enabled: bool = True


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extracts simple key-value YAML frontmatter and remaining markdown body."""
    meta: Dict[str, Any] = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body = parts[2].strip()

            current_key = None
            for line in fm_text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if v.startswith("[") and v.endswith("]"):
                        items = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
                        meta[k] = items
                    else:
                        meta[k] = v
                    current_key = k
                elif line.startswith("- ") and current_key:
                    val = line[2:].strip().strip('"').strip("'")
                    if not isinstance(meta.get(current_key), list):
                        meta[current_key] = []
                    meta[current_key].append(val)

    return meta, body


class SkillParser:
    """Parses a SKILL.md file into a SkillDefinition."""

    @classmethod
    def parse_file(cls, skill_file: Path) -> Optional[SkillDefinition]:
        if not skill_file.exists() or skill_file.name != "SKILL.md":
            return None

        try:
            content = skill_file.read_text(encoding="utf-8", errors="ignore")
            meta, body = parse_frontmatter(content)
            name = meta.get("name", skill_file.parent.name)
            desc = meta.get("description", "")

            # If no description in frontmatter, find first paragraph in body
            if not desc:
                for line in body.splitlines():
                    clean = line.strip()
                    if clean and not clean.startswith("#"):
                        desc = clean[:120]
                        break

            return SkillDefinition(
                name=name,
                description=desc,
                instructions=body,
                path=skill_file.parent,
                eligibility_os=meta.get("os", []),
                eligibility_binaries=meta.get("binaries", []),
                eligibility_env=meta.get("env", [])
            )
        except Exception:
            return None
