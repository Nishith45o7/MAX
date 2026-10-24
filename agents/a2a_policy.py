"""
Agent-to-Agent (A2A) Communication Policy Engine.
Governs which agents are permitted to send messages or delegate tasks to others.
"""
from typing import Tuple, Dict, Any, Optional
from agents.org_chart import OrgChart


class A2APolicy:
    """Enforces communication rules derived from org hierarchy and explicit rules."""

    def __init__(self, org_chart: Optional[OrgChart] = None):
        self.org_chart = org_chart or OrgChart()

    def can_message(self, from_agent: str, to_agent: str) -> Tuple[bool, str]:
        """
        Determines if from_agent may message or delegate to to_agent.
        Returns (allowed: bool, reason: str).
        """
        from_id = from_agent.strip().lower()
        to_id = to_agent.strip().lower()

        # 1. Self communication always allowed
        if from_id == to_id:
            return True, "Self-communication is always permitted"

        # 2. Executive lead / Chief agent (main) has universal reach
        if from_id == "main" or to_id == "main":
            return True, "Main coordinator has universal communication authority"

        org = self.org_chart.get_org()
        departments = org.get("departments", [])

        # Find departments for both agents
        from_depts = [d for d in departments if from_id in d.get("members", [])]
        to_depts = [d for d in departments if to_id in d.get("members", [])]

        if not from_depts:
            return False, f"Sender '{from_id}' belongs to no configured department"
        if not to_depts:
            return False, f"Recipient '{to_id}' belongs to no configured department"

        # 3. Same department membership
        common_depts = set(d.get("id") for d in from_depts).intersection(set(d.get("id") for d in to_depts))
        if common_depts:
            return True, f"Both agents are members of department(s): {', '.join(common_depts)}"

        # 4. Department lead contacting another department lead
        from_is_lead = any(d.get("lead") == from_id for d in from_depts)
        to_is_lead = any(d.get("lead") == to_id for d in to_depts)
        if from_is_lead and to_is_lead:
            return True, "Inter-department lead communication is permitted"

        return False, f"Cross-department communication denied between '{from_id}' and '{to_id}' (requires coordinator delegation)"
