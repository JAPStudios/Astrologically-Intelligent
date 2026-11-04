import unittest

from astrologically_intelligent.tools import ToolRegistry


class SkillSummaryTests(unittest.TestCase):
    def test_reads_single_line_description_from_frontmatter(self):
        body = """---
name: example
description: A useful skill description.
---

# Example
Longer instructions.
"""
        self.assertEqual(
            ToolRegistry._skill_summary(body),
            "A useful skill description.",
        )

    def test_reads_folded_description_from_frontmatter(self):
        body = """---
name: example
description: >-
  First part of the description
  continues on this line.
---

# Example
"""
        self.assertEqual(
            ToolRegistry._skill_summary(body),
            "First part of the description continues on this line.",
        )

    def test_falls_back_to_markdown_heading(self):
        body = """---
name: example
---

# Example skill
Instructions follow.
"""
        self.assertEqual(ToolRegistry._skill_summary(body), "Example skill")


if __name__ == "__main__":
    unittest.main()
