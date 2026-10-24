"""
Prompt-Resident Skill System for Brigade & MAX.
Discovers and loads SKILL.md folders across multiple priority roots with eligibility filters.
"""
from skills.loader import SkillLoader
from skills.parser import SkillDefinition

__all__ = ["SkillLoader", "SkillDefinition"]
