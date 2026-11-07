import unittest

from src.reminder_personas import PERSONAS, synthesis_system_prompt


class ReminderPersonaTests(unittest.TestCase):
    def test_personas_define_styles_without_human_impersonation(self):
        for persona_id, prompt in PERSONAS.items():
            with self.subTest(persona=persona_id):
                self.assertIn("Do not claim", prompt)
                self.assertNotIn("You are ", prompt)

    def test_frontend_style_presets_do_not_claim_human_identity(self):
        from pathlib import Path
        presets = (Path(__file__).resolve().parents[1] / "static" / "js" / "presets.js").read_text(encoding="utf-8")
        self.assertNotIn("You are Spark", presets)
        self.assertNotIn("You are Odysseus", presets)
        self.assertIn("Do not claim to be a human or a named persona", presets)

    def test_legacy_odysseus_setting_resolves_to_non_human_strategist_style(self):
        prompt = synthesis_system_prompt("odysseus")
        self.assertIn("strategic, composed, analytical", prompt)
        self.assertIn("Do not claim to be Odysseus", prompt)
        self.assertNotIn("king of Ithaca", prompt)


if __name__ == "__main__":
    unittest.main()
