from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_builtin_personas_do_not_claim_human_or_character_identity():
    frontend = (ROOT / "static" / "js" / "presets.js").read_text(encoding="utf-8")
    backend = (ROOT / "src" / "reminder_personas.py").read_text(encoding="utf-8")
    for source in (frontend, backend):
        assert "You are Spark" not in source
        assert "You are Odysseus" not in source
        assert "personal experiences" in source


def test_marketing_site_uses_project_brand_and_repository():
    website = (ROOT / "website" / "index.html").read_text(encoding="utf-8")
    assert "Astrologically Intelligent" in website
    assert "github.com/JAPStudios/Astrologically-Intelligent" in website
    assert "odysseus-dev/odysseus" not in website
    assert "Odysseus" not in website
