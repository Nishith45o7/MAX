"""
Org / Pride Hierarchy Chart Engine.
Defines organizational structures, reporting trees, and org linting.
"""
from typing import Dict, Any, List, Optional
from brigade_core.config import ConfigManager


class OrgChart:
    """Manages the crew organizational chart and hierarchy."""

    def __init__(self, config_mgr: Optional[ConfigManager] = None):
        self.config_mgr = config_mgr or ConfigManager()

    def get_org(self) -> Dict[str, Any]:
        cfg = self.config_mgr.load_raw()
        return cfg.get("org", {
            "name": "Personal Crew",
            "departments": [
                {
                    "id": "executive",
                    "name": "Executive & Coordination",
                    "lead": "main",
                    "members": ["main"]
                }
            ]
        })

    def render_tree(self) -> str:
        """Renders an ASCII Pride chart of the organization."""
        org = self.get_org()
        lines = [
            f"🦁 {org.get('name', 'Crew Organization')}",
            "═" * 40
        ]
        departments = org.get("departments", [])
        for i, dept in enumerate(departments):
            is_last_dept = (i == len(departments) - 1)
            dept_branch = "└──" if is_last_dept else "├──"
            lines.append(f"{dept_branch} 📁 Department: {dept.get('name')} (Lead: {dept.get('lead')})")
            
            members = dept.get("members", [])
            for j, mem in enumerate(members):
                is_last_mem = (j == len(members) - 1)
                sub_prefix = "    " if is_last_dept else "│   "
                mem_branch = "└──" if is_last_mem else "├──"
                role_tag = "👑 Lead" if mem == dept.get("lead") else "👤 Member"
                lines.append(f"{sub_prefix}{mem_branch} {role_tag}: {mem}")

        return "\n".join(lines)

    def doctor(self) -> List[str]:
        """Runs lints on the org structure."""
        issues = []
        org = self.get_org()
        departments = org.get("departments", [])
        if not departments:
            issues.append("Org has no configured departments.")

        seen_leads = set()
        for dept in departments:
            dept_id = dept.get("id")
            lead = dept.get("lead")
            members = dept.get("members", [])
            if not lead:
                issues.append(f"Department '{dept_id}' has no designated lead.")
            elif lead not in members:
                issues.append(f"Lead '{lead}' of department '{dept_id}' is not listed in its members.")
            if len(members) <= 1:
                issues.append(f"Department '{dept_id}' has only 1 member (single-member department).")

        return issues
