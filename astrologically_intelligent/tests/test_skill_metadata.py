import tempfile
import unittest
from pathlib import Path

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

    def test_resolves_native_and_upstream_skill_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            native = root / "skills" / "native-skill" / "SKILL.md"
            upstream = root / "upstream" / "project" / "skill" / "SKILL.md"
            native.parent.mkdir(parents=True)
            upstream.parent.mkdir(parents=True)
            native.write_text("# Native skill\\n", encoding="utf-8")
            upstream.write_text("# Upstream skill\\n", encoding="utf-8")

            self.assertEqual(
                ToolRegistry._resolve_skill_path("native-skill", root), native.resolve()
            )
            self.assertEqual(
                ToolRegistry._resolve_skill_path("upstream/project/skill", root),
                upstream.resolve(),
            )

    def test_skill_path_rejects_traversal_and_unknown_skills(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ("../outside", "upstream/../../outside", "missing"):
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        ToolRegistry._resolve_skill_path(name, Path(directory))


if __name__ == "__main__":
    unittest.main()
