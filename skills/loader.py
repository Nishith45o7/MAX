"""
Skill Loader discovering skills across 6 precedence roots with eligibility filters.
"""
import os
import sys
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from brigade_core import get_state_dir
from skills.parser import SkillParser, SkillDefinition


class SkillLoader:
    """Discovers, validates, and manages prompt-resident skills."""

    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = state_dir or get_state_dir()
        self.base_dir = Path(__file__).resolve().parent.parent
        self.bundled_dir = self.base_dir / "skills" / "bundled"

    def get_discovery_roots(self, agent_id: str, workspace_dir: Optional[Path] = None) -> List[Path]:
        """Returns the 6 discovery roots in descending priority order."""
        roots = []
        # 1. Agent workspace skills
        if workspace_dir:
            roots.append(workspace_dir / "skills")
        # 2. Agent state skills
        roots.append(self.state_dir / "agents" / agent_id / "skills")
        # 3. Global user skills
        roots.append(self.state_dir / "skills")
        # 4. Project custom skills
        roots.append(self.base_dir / "skills" / "custom")
        # 5. Bundled skills
        roots.append(self.bundled_dir)
        return roots

    def is_eligible(self, skill: SkillDefinition) -> bool:
        """Verifies OS, required binaries, and environment variables."""
        # 1. OS check
        if skill.eligibility_os:
            current_os = sys.platform
            if not any(target in current_os for target in skill.eligibility_os):
                return False

        # 2. Binary check
        if skill.eligibility_binaries:
            for b in skill.eligibility_binaries:
                if not shutil.which(b):
                    return False

        # 3. Env check
        if skill.eligibility_env:
            for env_var in skill.eligibility_env:
                if not os.environ.get(env_var):
                    return False

        return True

    def discover_skills(self, agent_id: str = "main", workspace_dir: Optional[Path] = None) -> Dict[str, SkillDefinition]:
        """Discovers and merges skills in precedence order."""
        skills: Dict[str, SkillDefinition] = {}
        roots = self.get_discovery_roots(agent_id, workspace_dir)

        # Iterate in reverse precedence so higher priority overwrites lower priority
        for root in reversed(roots):
            if not root.exists() or not root.is_dir():
                continue
            for item in root.iterdir():
                if item.is_dir():
                    skill_file = item / "SKILL.md"
                    if skill_file.exists():
                        defn = SkillParser.parse_file(skill_file)
                        if defn and self.is_eligible(defn):
                            skills[defn.name] = defn

        return skills

    def build_prompt_catalog(self, skills: Dict[str, SkillDefinition]) -> str:
        """Creates a compact prompt-resident summary catalog."""
        if not skills:
            return ""

        lines = ["[Available Extensible Skills]"]
        for name, defn in sorted(skills.items()):
            lines.append(f"- {name}: {defn.description}")
        lines.append("Call read_skill(skill_name) to inspect detailed instructions for any skill on demand.")
        return "\n".join(lines)
