"""
Unit tests for the Skill System.
"""
import unittest
from skills.loader import SkillLoader


class TestSkillsSuite(unittest.TestCase):

    def setUp(self):
        self.loader = SkillLoader()

    def test_bundled_skills_discovery(self):
        skills = self.loader.discover_skills()
        self.assertTrue(len(skills) > 0, "Should discover bundled skills")
        # Check known skills like 'docx', 'pdf', 'xlsx', 'weather', etc.
        self.assertTrue("docx" in skills or "pdf" in skills or "weather" in skills)

        catalog = self.loader.build_prompt_catalog(skills)
        self.assertIn("[Available Extensible Skills]", catalog)


if __name__ == "__main__":
    unittest.main()
