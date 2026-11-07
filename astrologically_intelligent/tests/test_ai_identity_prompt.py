from src import spec_router
from src.context_compactor import SELF_SUMMARY_SYSTEM_PROMPT

def test_default_agent_identity_is_non_human_software():
    assert spec_router._AGENT == "Astrologically Intelligent, a non-human software agent."
    assert "You are Astrologically Intelligent" in spec_router._CORE_PROMPT
    assert "not a human" in spec_router._CORE_PROMPT
    assert "Do not imitate human identity" in spec_router._CORE_PROMPT
    assert "Ajax" not in SELF_SUMMARY_SYSTEM_PROMPT
    assert "Odysseus" not in SELF_SUMMARY_SYSTEM_PROMPT
    assert "Astrologically Intelligent" in SELF_SUMMARY_SYSTEM_PROMPT
    assert "software, not a human" in SELF_SUMMARY_SYSTEM_PROMPT

def test_web_app_uses_astrologically_intelligent_branding():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    index = (root / "static" / "index.html").read_text(encoding="utf-8")
    manifest = (root / "static" / "manifest.json").read_text(encoding="utf-8")
    assert "<title>Astrologically Intelligent</title>" in index
    assert "\"name\": \"Astrologically Intelligent\"" in manifest
    assert "\"short_name\": \"Astrologically Intelligent\"" in manifest
    assert "<title>Odysseus Chat</title>" not in index

def test_login_page_uses_astrologically_intelligent_branding():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    login = (root / "static" / "login.html").read_text(encoding="utf-8")
    assert "<title>Astrologically Intelligent — Login</title>" in login
    assert "<span>Astrologically Intelligent</span>" in login
    assert "<title>Odysseus — Login</title>" not in login

def test_legacy_web_prompt_is_replaced_with_non_human_product_identity():
    legacy = [{"role": "system", "content": "You are Ajax, the assistant in Odysseus. Legacy tool manual."}]
    result = spec_router.trim_system_prompt(legacy, [])
    assert len(result) == 1
    assert "You are Astrologically Intelligent, a software agent, not a human" in result[0]["content"]
    assert "Ajax" not in result[0]["content"]
    assert "Odysseus" not in result[0]["content"]

def test_main_web_agent_and_specialized_prompts_use_non_human_product_identity():
    from src import agent_loop

    assert "You are Astrologically Intelligent, a non-human software agent" in agent_loop.AGENT_SYSTEM_PROMPT
    assert "Do not imitate human identity" in agent_loop.AGENT_SYSTEM_PROMPT
    assert "Odysseus" not in agent_loop.AGENT_SYSTEM_PROMPT
    assert "You are Odysseus" not in agent_loop.AGENT_SYSTEM_PROMPT

    user_message = [{"role": "user", "content": "Create a short document."}]
    document_prompt = agent_loop._minimal_odysseus_doc_messages(
        user_message, None, stream_create=True
    )[0]["content"]
    notes_prompt = agent_loop._minimal_odysseus_notes_messages(user_message)[0]["content"]
    fallback_prompt = agent_loop._minimal_odysseus_general_messages(user_message)[0]["content"]
    for prompt in (document_prompt, notes_prompt, fallback_prompt):
        assert "You are Astrologically Intelligent, a non-human software agent" in prompt
        assert "Odysseus" not in prompt

def test_current_web_prompt_is_compacted_by_spec_router():
    current = [{
        "role": "system",
        "content": "You are Astrologically Intelligent, a non-human software agent with tool access. " + ("Legacy tool manual. " * 20),
    }]
    result = spec_router.trim_system_prompt(current, [])
    assert len(result) == 1
    assert "You are Astrologically Intelligent, a software agent, not a human" in result[0]["content"]
    assert "Legacy tool manual" not in result[0]["content"]
