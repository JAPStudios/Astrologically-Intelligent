import unittest

from astrologically_intelligent.runtime import AgentRuntime, RuntimeConfig
from astrologically_intelligent.storage import Store


class FakeProvider:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0
        self.tool_arguments = []

    def chat(self, messages, tools):
        self.calls += 1
        self.tool_arguments.append(tools)
        return next(self.responses)


def tool_call(name="skills.list"):
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call-1",
            "type": "function",
            "function": {"name": name, "arguments": "{}"},
        }],
    }


class AgentRuntimeToolLimitTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")

    def tearDown(self):
        self.store.close()

    def test_executes_one_tool_round_then_requests_final_answer_without_tools(self):
        provider = FakeProvider([
            tool_call(),
            {"role": "assistant", "content": "Completed using the available result."},
        ])
        runtime = AgentRuntime(
            provider=provider,
            store=self.store,
            config=RuntimeConfig(max_tool_rounds=1),
        )
        executed = []
        runtime.tools.execute = lambda name, arguments: executed.append(name) or '{"ok": true}'

        result = runtime.chat("Run the tool.")

        self.assertEqual(result["response"], "Completed using the available result.")
        self.assertEqual(provider.calls, 2)
        self.assertEqual(executed, ["skills.list"])
        self.assertEqual(provider.tool_arguments[1], [])
        self.assertEqual(
            self.store.history(result["session_id"]),
            [
                {"role": "user", "content": "Run the tool."},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": tool_call()["tool_calls"],
                },
                {
                    "role": "tool",
                    "content": '{"ok": true}',
                    "tool_call_id": "call-1",
                    "name": "skills.list",
                },
                {"role": "assistant", "content": "Completed using the available result."},
            ],
        )
        runtime.tools.close()

    def test_does_not_execute_a_tool_batch_beyond_the_configured_limit(self):
        provider = FakeProvider([
            tool_call(),
            {"role": "assistant", "content": None, "tool_calls": [tool_call()["tool_calls"][0]]},
        ])
        runtime = AgentRuntime(
            provider=provider,
            store=self.store,
            config=RuntimeConfig(max_tool_rounds=1),
        )
        executed = []
        runtime.tools.execute = lambda name, arguments: executed.append(name) or '{"ok": true}'

        result = runtime.chat("Keep calling tools.")

        self.assertIn("tool execution limit", result["response"].lower())
        self.assertEqual(provider.calls, 2)
        self.assertEqual(executed, ["skills.list"])
        self.assertEqual(provider.tool_arguments[1], [])
        runtime.tools.close()

    def test_rejects_malformed_provider_tool_calls(self):
        provider = FakeProvider([{
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "bad", "function": None}],
        }])
        runtime = AgentRuntime(
            provider=provider,
            store=self.store,
            config=RuntimeConfig(max_tool_rounds=1),
        )

        with self.assertRaisesRegex(RuntimeError, "without a function"):
            runtime.chat("Run a malformed tool call.")
        runtime.tools.close()

    def test_rejects_negative_tool_round_limit(self):
        runtime = AgentRuntime(
            provider=FakeProvider([]),
            store=self.store,
            config=RuntimeConfig(max_tool_rounds=-1),
        )
        with self.assertRaisesRegex(ValueError, "non-negative"):
            runtime.chat("Hello.")
        runtime.tools.close()


if __name__ == "__main__":
    unittest.main()
