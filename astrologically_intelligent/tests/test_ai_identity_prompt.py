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
