import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from astrologically_intelligent.tools import ToolRegistry


def test_herdr_upstream_skill_is_discoverable_and_keeps_its_safety_gate():
    repo_root = Path(__file__).resolve().parents[2]
    skill_path = ToolRegistry._resolve_skill_path("upstream/herdr", repo_root)

    assert skill_path == (repo_root / "skills/upstream/herdr/SKILL.md").resolve()
    content = skill_path.read_text(encoding="utf-8")
    assert "requires HERDR_ENV=1" in content
    assert "Do not inspect or control the focused Herdr session from outside Herdr." in content
    assert (repo_root / "skills/upstream/herdr/LICENSE").is_file()
