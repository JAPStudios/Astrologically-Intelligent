from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_web_application_uses_astrologically_intelligent_branding():
    index = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    manifest = (ROOT / "static" / "manifest.json").read_text(encoding="utf-8")
    assert "Astrologically Intelligent" in index
    assert "Odysseus" not in index
    assert "Astrologically Intelligent" in manifest
    assert "Odysseus" not in manifest
    assert "Astrologically Intelligent" in (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
