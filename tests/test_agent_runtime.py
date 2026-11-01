import json
import unittest

from astrologically_intelligent.providers import OpenAICompatibleProvider, ProviderConfig
from astrologically_intelligent.runtime import AgentRuntime, RuntimeConfig
from astrologically_intelligent.storage import Store


class FakeProvider:
    def __init__(self):
        self.calls = 0

    def chat(self, messages, tools):
        self.calls += 1
        if self.calls == 1:
            return {"role": "assistant", "content": None, "tool_calls": [{
                "id": "call-1", "type": "function",
                "function": {"name": "memory.remember",
                             "arguments": json.dumps({"namespace": "profile", "key": "preferred_name", "value": "Ada"})}
            }]}
        return {"role": "assistant", "content": "Memory saved."}


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        self.runtime = AgentRuntime(provider=FakeProvider(), store=self.store,
                                    config=RuntimeConfig(max_tool_rounds=2))

    def tearDown(self):
        self.store.close()

    def test_tool_call_and_session_persistence(self):
        result = self.runtime.chat("Remember my preferred name is Ada.", "session-a")
        self.assertEqual(result["response"], "Memory saved.")
        self.assertEqual(self.store.recall("profile", "preferred_name")[0]["value"], "Ada")
        history = self.store.history("session-a")
        self.assertEqual([m["role"] for m in history], ["user", "assistant"])

    def test_work_item_lifecycle(self):
        task = self.store.create_task("Build ephemeris integration")
        self.assertEqual(task["status"], "open")
        updated = self.store.update_task(task["id"], "in_progress", "agent-astro")
        self.assertEqual(updated["status"], "in_progress")
        self.assertEqual(updated["assignee"], "agent-astro")

    def test_provider_request_shape(self):
        provider = OpenAICompatibleProvider(ProviderConfig("http://localhost:1234/v1", "", "test-model"))
        self.assertEqual(provider.config.model, "test-model")

    def test_empty_message_rejected(self):
        with self.assertRaises(ValueError):
            self.runtime.chat("  ")


if __name__ == "__main__":
    unittest.main()
