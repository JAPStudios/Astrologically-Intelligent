import json
import unittest
from unittest.mock import patch

from astrologically_intelligent.providers import (
    AnthropicMessagesProvider,
    GeminiGenerateContentProvider,
    ProviderConfig,
)


class ProviderAdapterTests(unittest.TestCase):
    def setUp(self):
        self.config = ProviderConfig("https://provider.invalid", "test-key", "test-model")

    def test_anthropic_maps_tool_calls_and_tool_results_without_losing_ids(self):
        messages = [
            {"role": "system", "content": "System instructions"},
            {"role": "user", "content": "Find a skill"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "tool-123",
                    "type": "function",
                    "function": {
                        "name": "skills.read",
                        "arguments": '{"name":"research"}',
                    },
                }],
            },
            {
                "role": "tool",
                "tool_call_id": "tool-123",
                "name": "skills.read",
                "content": '{"skill":"research"}',
            },
        ]

        system, converted = AnthropicMessagesProvider._messages(messages)

        self.assertEqual(system, "System instructions")
        self.assertEqual(converted[0], {"role": "user", "content": "Find a skill"})
        self.assertEqual(converted[1]["role"], "assistant")
        self.assertEqual(converted[1]["content"][0], {
            "type": "tool_use",
            "id": "tool-123",
            "name": "skills.read",
            "input": {"name": "research"},
        })
        self.assertEqual(converted[2]["role"], "user")
        self.assertEqual(converted[2]["content"][0], {
            "type": "tool_result",
            "tool_use_id": "tool-123",
            "content": '{"skill":"research"}',
        })

    def test_anthropic_response_maps_text_and_multiple_tool_uses(self):
        provider = AnthropicMessagesProvider(self.config)
        response = {
            "content": [
                {"type": "text", "text": "Checking."},
                {"type": "tool_use", "id": "one", "name": "skills.list", "input": {}},
                {"type": "tool_use", "id": "two", "name": "memory.recall",
                 "input": {"namespace": "preferences"}},
            ]
        }
        with patch("astrologically_intelligent.providers._post_json", return_value=response):
            result = provider.chat([{"role": "user", "content": "Check"}], [])

        self.assertEqual(result["content"], "Checking.")
        self.assertEqual([call["id"] for call in result["tool_calls"]], ["one", "two"])
        self.assertEqual(
            json.loads(result["tool_calls"][1]["function"]["arguments"]),
            {"namespace": "preferences"},
        )

    def test_gemini_preserves_original_model_content_for_followup_tool_turn(self):
        provider = GeminiGenerateContentProvider(self.config)
        original_content = {
            "role": "model",
            "parts": [
                {"functionCall": {
                    "name": GeminiGenerateContentProvider._tool_alias("skills.list"),
                    "args": {},
                    "id": "gemini-call-1",
                }},
                {"text": "signature-payload", "thoughtSignature": "opaque-signature"},
            ],
        }
        response = {
            "candidates": [{
                "content": original_content,
                "finishReason": "STOP",
            }]
        }
        with patch("astrologically_intelligent.providers._post_json", return_value=response):
            first = provider.chat(
                [{"role": "user", "content": "List skills"}],
                [{
                    "type": "function",
                    "function": {
                        "name": "skills.list",
                        "description": "List installed skills",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }],
            )

        self.assertEqual(first["tool_calls"][0]["function"]["name"], "skills.list")
        followup_messages = [
            {"role": "user", "content": "List skills"},
            first,
            {
                "role": "tool",
                "tool_call_id": "gemini-call-1",
                "name": "skills.list",
                "content": '{"skills":["research"]}',
            },
        ]
        _, contents = GeminiGenerateContentProvider._contents(followup_messages)

        self.assertEqual(contents[1], original_content)
        self.assertEqual(contents[2]["role"], "user")
        function_response = contents[2]["parts"][0]["functionResponse"]
        self.assertEqual(function_response["id"], "gemini-call-1")
        self.assertEqual(function_response["response"], {"skills": ["research"]})

    def test_gemini_rejects_function_calls_not_declared_to_the_model(self):
        provider = GeminiGenerateContentProvider(self.config)
        response = {
            "candidates": [{
                "content": {"parts": [{
                    "functionCall": {"name": "undeclared", "args": {}}
                }]}
            }]
        }
        with patch("astrologically_intelligent.providers._post_json", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "undeclared function"):
                provider.chat(
                    [{"role": "user", "content": "Do something"}],
                    [{
                        "type": "function",
                        "function": {
                            "name": "skills.list",
                            "parameters": {"type": "object", "properties": {}},
                        },
                    }],
                )



    def test_anthropic_rejects_malformed_tool_arguments_instead_of_erasing_them(self):
        messages = [{
            "role": "assistant",
            "tool_calls": [{
                "id": "tool-bad",
                "function": {"name": "skills.read", "arguments": "{invalid"},
            }],
        }]
        with self.assertRaisesRegex(RuntimeError, "malformed tool arguments"):
            AnthropicMessagesProvider._messages(messages)

    def test_anthropic_rejects_non_object_tool_arguments(self):
        messages = [{
            "role": "assistant",
            "tool_calls": [{
                "id": "tool-scalar",
                "function": {"name": "skills.read", "arguments": "[]"},
            }],
        }]
        with self.assertRaisesRegex(RuntimeError, "must be a JSON object"):
            AnthropicMessagesProvider._messages(messages)

    def test_anthropic_rejects_tool_calls_without_ids(self):
        messages = [{
            "role": "assistant",
            "tool_calls": [{
                "function": {"name": "skills.read", "arguments": "{}"},
            }],
        }]
        with self.assertRaisesRegex(RuntimeError, "without an ID"):
            AnthropicMessagesProvider._messages(messages)

if __name__ == "__main__":
    unittest.main()
