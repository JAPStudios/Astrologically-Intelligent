import unittest
from unittest.mock import patch

from astrologically_intelligent.providers import (
    ChatCompletionsProvider,
    ProviderConfig,
    provider_from_env,
)


class LocalProviderTests(unittest.TestCase):
    def test_only_local_provider_can_be_selected(self):
        with patch.dict("os.environ", {
            "ASTRO_AI_PROVIDER": "local",
            "ASTRO_AI_MODEL": "test-model",
        }, clear=True):
            provider = provider_from_env()
        self.assertIsInstance(provider, ChatCompletionsProvider)
        self.assertEqual(provider.config.base_url, "http://127.0.0.1:11434/v1")

    def test_remote_provider_selection_is_rejected(self):
        for name in ("openai", "anthropic", "gemini", "xai", "deepseek", "azure", "perplexity"):
            with self.subTest(provider=name), patch.dict("os.environ", {
                "ASTRO_AI_PROVIDER": name,
                "ASTRO_AI_MODEL": "test-model",
            }, clear=True):
                with self.assertRaisesRegex(RuntimeError, "third-party model providers are disabled"):
                    provider_from_env()

    def test_remote_endpoint_is_rejected_even_with_local_provider_name(self):
        with self.assertRaisesRegex(RuntimeError, "Remote model endpoints are disabled"):
            ChatCompletionsProvider(ProviderConfig(
                "https://api.openai.com/v1", "key", "test-model"
            ))

    def test_loopback_hostnames_and_addresses_are_allowed(self):
        for endpoint in (
            "http://localhost:11434/v1",
            "http://127.0.0.1:11434/v1",
            "http://[::1]:11434/v1",
        ):
            with self.subTest(endpoint=endpoint):
                provider = ChatCompletionsProvider(ProviderConfig(endpoint, "", "test-model"))
                self.assertEqual(provider.config.base_url, endpoint)

    def test_malformed_endpoint_is_rejected(self):
        for endpoint in ("file:///tmp/model", "http:///v1", "http://user:pass@localhost/v1",
                         "http://localhost/v1?target=remote"):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(RuntimeError):
                    ChatCompletionsProvider(ProviderConfig(endpoint, "", "test-model"))

    def test_chat_request_preserves_tool_definitions(self):
        provider = ChatCompletionsProvider(ProviderConfig(
            "http://127.0.0.1:11434/v1", "", "test-model"
        ))
        tool = {"type": "function", "function": {
            "name": "memory.recall",
            "description": "Read memory",
            "parameters": {"type": "object", "properties": {}},
        }}
        response_payload = {"choices": [{"message": {
            "role": "assistant", "content": "Done",
        }}]}
        with patch("astrologically_intelligent.providers._post_json", return_value=response_payload) as post:
            result = provider.chat([{"role": "user", "content": "hello"}], [tool])
        self.assertEqual(result["content"], "Done")
        self.assertEqual(post.call_args.args[0], "http://127.0.0.1:11434/v1/chat/completions")
        self.assertEqual(post.call_args.args[1]["tools"], [tool])
        self.assertEqual(post.call_args.args[1]["tool_choice"], "auto")


if __name__ == "__main__":
    unittest.main()
