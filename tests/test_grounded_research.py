import json
import unittest
from pathlib import Path

from astrologically_intelligent.grounded_research import (
    GROUNDED_SYSTEM_PROMPT, INSUFFICIENT_EVIDENCE, answer_from_documents, build_messages,
    build_passages, select_passages, split_passages, validate_citations,
)

FIXTURE = json.loads((Path(__file__).parent / "fixtures/grounded_research/synthetic_eval.json").read_text())
DOCS = FIXTURE["documents"]


class RecordingProvider:
    def __init__(self, answer): self.answer, self.calls = answer, []
    def chat(self, messages, tools):
        self.calls.append((messages, tools))
        return {"role": "assistant", "content": self.answer}


class PassageTests(unittest.TestCase):
    def test_passage_ids_are_stable_and_ordered(self):
        first = [p.citation_id for p in build_passages(DOCS)]
        self.assertEqual(first, [p.citation_id for p in build_passages(DOCS)])
        self.assertEqual(first[:2], ["harbor-guide#p1", "harbor-guide#p2"])

    def test_long_paragraph_is_split_within_limit(self):
        text = " ".join(f"Sentence number {i} is here." for i in range(60))
        passages = split_passages("long", text, max_chars=200)
        self.assertGreater(len(passages), 1)
        self.assertTrue(all(len(p.text) <= 200 for p in passages))
        self.assertEqual(" ".join(p.text for p in passages), " ".join(text.split()))

    def test_rejects_bad_ids_empty_text_and_duplicates(self):
        for bad in ("", "has space", "a/b", "x" * 65, None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                split_passages(bad, "text")
        with self.assertRaises(ValueError):
            split_passages("ok", "   ")
        with self.assertRaises(ValueError):
            build_passages([{"id": "a", "text": "x"}, {"id": "a", "text": "y"}])
        with self.assertRaises(ValueError):
            build_passages([])


class ContextTests(unittest.TestCase):
    def test_selection_prefers_relevant_passages_and_drops_unrelated(self):
        selected = select_passages("When was the lighthouse built?", build_passages(DOCS))
        ids = [p.citation_id for p in selected]
        self.assertEqual(set(ids), {"harbor-guide#p1", "council-notes#p1"})

    def test_messages_contain_rules_ids_and_question_without_tools(self):
        passages = build_passages(DOCS)[:2]
        messages = build_messages("Ferry times?", passages)
        self.assertEqual(messages[0]["content"], GROUNDED_SYSTEM_PROMPT)
        self.assertIn("Never invent", GROUNDED_SYSTEM_PROMPT)
        self.assertIn(INSUFFICIENT_EVIDENCE, GROUNDED_SYSTEM_PROMPT)
        self.assertIn("[harbor-guide#p2]", messages[1]["content"])
        self.assertIn("QUESTION: Ferry times?", messages[1]["content"])

    def test_provider_receives_no_tools_and_only_selected_passages(self):
        provider = RecordingProvider("Every 40 minutes [harbor-guide#p2].")
        result = answer_from_documents(provider, "How often does the ferry depart?", DOCS)
        messages, tools = provider.calls[0]
        self.assertEqual(tools, [])
        self.assertNotIn("night market", messages[1]["content"])
        self.assertTrue(result["validation"]["ok"])

    def test_no_matching_passages_skips_provider_and_reports_insufficient(self):
        provider = RecordingProvider("should not be used")
        result = answer_from_documents(provider, "Quantum chromodynamics?", DOCS)
        self.assertEqual(provider.calls, [])
        self.assertTrue(result["validation"]["insufficient_evidence"])


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.passages = build_passages(DOCS)

    def test_unknown_citation_is_flagged(self):
        report = validate_citations("Fish are sold [market-flyer#p1]. Maps too [market-flyer#p9].", self.passages)
        self.assertEqual(report.unknown_citations, ["market-flyer#p9"])
        self.assertFalse(report.ok)

    def test_uncited_factual_sentence_is_flagged(self):
        report = validate_citations("The ferry runs every 40 minutes [harbor-guide#p2]. The town has 9000 residents.", self.passages)
        self.assertEqual(report.uncited_sentences, ["The town has 9000 residents."])

    def test_malformed_citation_is_flagged(self):
        report = validate_citations("The ferry runs often [harbor guide#p2].", self.passages)
        self.assertTrue(report.malformed_citations)
        self.assertFalse(report.ok)

    def test_insufficient_evidence_answer_is_valid_without_citations(self):
        report = validate_citations(f"{INSUFFICIENT_EVIDENCE}: population is not stated in the sources.", self.passages)
        self.assertTrue(report.ok and report.insufficient_evidence)


class SyntheticEvalTests(unittest.TestCase):
    def test_offline_eval_cases_pass(self):
        import importlib.util
        path = Path(__file__).resolve().parents[1] / "scripts/eval_grounded_research.py"
        spec = importlib.util.spec_from_file_location("eval_grounded_research", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        rows = module.run(live=False)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r["passed"] for r in rows), [r["case"] for r in rows if not r["passed"]])

    def test_default_chat_prompt_is_unchanged(self):
        from astrologically_intelligent.runtime import SYSTEM_PROMPT
        self.assertNotIn(INSUFFICIENT_EVIDENCE, SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
