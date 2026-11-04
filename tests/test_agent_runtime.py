import json
import unittest
import urllib.error
from io import BytesIO
from unittest.mock import patch

from astrologically_intelligent.providers import (
    AnthropicMessagesProvider, GeminiGenerateContentProvider, OpenAICompatibleProvider, ProviderConfig, _post_json, provider_from_env,
)
from astrologically_intelligent.runtime import AgentRuntime, RuntimeConfig
from astrologically_intelligent.storage import Store


class FakeProvider:
    def __init__(self): self.calls=0
    def chat(self,messages,tools):
        self.calls+=1
        if self.calls==1:
            return {"role":"assistant","content":None,"tool_calls":[{"id":"call-1","type":"function",
                "function":{"name":"memory.remember","arguments":json.dumps({"namespace":"profile","key":"preferred_name","value":"Ada"})}}]}
        return {"role":"assistant","content":"Memory saved."}


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.store=Store(":memory:")
        self.runtime=AgentRuntime(provider=FakeProvider(),store=self.store,config=RuntimeConfig(max_tool_rounds=2))
    def tearDown(self):
        self.runtime.close()
    def test_system_prompt_enforces_non_human_respectful_behavior(self):
        from astrologically_intelligent.runtime import SYSTEM_PROMPT
        self.assertIn("You are software, not a human", SYSTEM_PROMPT)
        self.assertIn("Do not insult, harass, threaten, or demean users", SYSTEM_PROMPT)
        self.assertIn("Save personal memory only when the user explicitly asks", SYSTEM_PROMPT)

    def test_tool_call_and_session_persistence(self):
        result=self.runtime.chat("Remember my preferred name is Ada.","session-a")
        self.assertEqual(result["response"],"Memory saved.")
        self.assertEqual(self.store.recall("profile","preferred_name")[0]["value"],"Ada")
        self.assertEqual([m["role"] for m in self.store.history("session-a")],["user","assistant"])
    def test_tool_handler_exceptions_are_contained_and_redacted(self):
        def fail():
            raise RuntimeError("sensitive connector response")

        self.runtime.tools.register("test.failure", "Test a failing handler.", {
            "type": "object", "properties": {}, "additionalProperties": False,
        }, fail)
        result = json.loads(self.runtime.tools.execute("test.failure", {}))
        self.assertEqual(result, {
            "error": "Tool execution failed",
            "type": "RuntimeError",
        })
        self.assertNotIn("sensitive connector response", json.dumps(result))

    def test_memory_forget_deletes_only_the_exact_namespace_and_key(self):
        self.store.remember("profile", "preferred_name", "Ada")
        self.store.remember("profile", "timezone", "UTC")
        self.store.remember("preferences", "preferred_name", "Grace")

        result = json.loads(self.runtime.tools.execute(
            "memory.forget", {"namespace": "profile", "key": "preferred_name"}))

        self.assertEqual(result, {"deleted": True})
        self.assertEqual(self.store.recall("profile", "preferred_name"), [])
        self.assertEqual(self.store.recall("profile", "timezone")[0]["value"], "UTC")
        self.assertEqual(self.store.recall("preferences", "preferred_name")[0]["value"], "Grace")

    def test_memory_forget_requires_both_exact_identifiers(self):
        for arguments in ({"namespace": "profile"}, {"key": "preferred_name"},
                          {"namespace": "", "key": "preferred_name"}):
            result = json.loads(self.runtime.tools.execute("memory.forget", arguments))
            self.assertIn("error", result)
        self.store.remember("profile", "preferred_name", "Ada")
        result = json.loads(self.runtime.tools.execute(
            "memory.forget", {"namespace": "profile", "key": "missing"}))
        self.assertEqual(result, {"deleted": False})
        self.assertEqual(self.store.recall("profile", "preferred_name")[0]["value"], "Ada")

    def test_work_item_lifecycle(self):
        task=self.store.create_task("Build an integration")
        self.assertEqual(task["status"],"open")
        updated=self.store.update_task(task["id"],"in_progress","agent-1")
        self.assertEqual(updated["assignee"],"agent-1")
    def test_vendor_provider_defaults(self):
        with patch.dict("os.environ", {
            "ASTRO_AI_PROVIDER":"xai", "XAI_API_KEY":"xai-test",
        }, clear=True):
            xai=provider_from_env()
        self.assertEqual(xai.config.base_url,"https://api.x.ai/v1")
        self.assertEqual(xai.config.api_key,"xai-test")
        with patch.dict("os.environ", {
            "ASTRO_AI_PROVIDER":"perplexity", "PERPLEXITY_API_KEY":"pplx-test",
        }, clear=True):
            perplexity=provider_from_env()
        self.assertEqual(perplexity.config.base_url,"https://api.perplexity.ai")
        self.assertEqual(perplexity.config.model,"sonar")

    def test_external_platform_tools_are_registered(self):
        names={item["function"]["name"] for item in self.runtime.tools.definitions()}
        expected={
            "n8n.workflows.list","n8n.workflows.get","n8n.workflows.activate","n8n.workflows.deactivate",
            "paperclip.agents.list","paperclip.issues.list","paperclip.issues.create",
            "paperclip.goals.create","paperclip.approvals.list","perplexity.search","openclaw.sessions.list",
        }
        self.assertTrue(expected <= names)

    def test_provider_http_error_body_is_not_exposed(self):
        error = urllib.error.HTTPError(
            "https://provider.example/v1/chat/completions", 401, "Unauthorized", {},
            BytesIO(b'{"error":"secret-provider-response"}'),
        )
        with patch("astrologically_intelligent.providers.urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "Provider returned HTTP 401") as raised:
                _post_json("https://provider.example/v1/chat/completions", {}, {}, 5)
        self.assertNotIn("secret-provider-response", str(raised.exception))

    def test_provider_connection_error_details_are_not_exposed(self):
        error = urllib.error.URLError("secret-endpoint-detail")
        with patch("astrologically_intelligent.providers.urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, r"Provider connection failed \(URLError\)") as raised:
                _post_json("https://provider.example/v1/chat/completions", {}, {}, 5)
        self.assertNotIn("secret-endpoint-detail", str(raised.exception))

    def test_provider_request_shape(self):
        provider=OpenAICompatibleProvider(ProviderConfig("http://localhost:1234/v1","","test-model"))
        self.assertEqual(provider.config.model,"test-model")
    def test_gemini_provider_defaults_and_tool_schema_translation(self):
        with patch.dict("os.environ", {"ASTRO_AI_PROVIDER":"gemini", "GEMINI_API_KEY":"gemini-test"}, clear=True):
            provider = provider_from_env()
        self.assertIsInstance(provider, GeminiGenerateContentProvider)
        self.assertEqual(provider.config.base_url, "https://generativelanguage.googleapis.com/v1beta")
        self.assertEqual(provider.config.model, "gemini-3.8-flash")
        system, converted = GeminiGenerateContentProvider._contents([
            {"role":"system", "content":"system rules"},
            {"role":"user", "content":"hello"},
        ])
        self.assertEqual(system, "system rules")
        self.assertEqual(converted, [{"role":"user", "parts":[{"text":"hello"}]}])

    def test_gemini_function_call_round_trip_preserves_signature_and_ids(self):
        provider = GeminiGenerateContentProvider(ProviderConfig(
            "https://generativelanguage.googleapis.com/v1beta", "gemini-test", "gemini-3.8-flash"))
        tools = [{"type":"function", "function": {
            "name":"memory.remember", "description":"Save approved memory.",
            "parameters":{"type":"object", "properties": {
                "value":{"type":["string", "null"]}}, "additionalProperties":False},
        }}]
        alias = provider._tool_alias("memory.remember")
        model_content = {"role":"model", "parts":[{
            "functionCall":{"id":"gemini-call-1", "name":alias, "args":{"value":"Ada"}},
            "thoughtSignature":"opaque-signature"
        }]}
        with patch("astrologically_intelligent.providers._post_json", return_value={
            "candidates":[{"content":model_content, "finishReason":"STOP"}]
        }) as post:
            response = provider.chat([{"role":"system", "content":"rules"},
                                      {"role":"user", "content":"remember Ada"}], tools)
        self.assertEqual(response["tool_calls"][0]["id"], "gemini-call-1")
        self.assertEqual(response["tool_calls"][0]["function"]["name"], "memory.remember")
        sent = post.call_args.args[1]
        self.assertEqual(sent["systemInstruction"]["parts"][0]["text"], "rules")
        declaration = sent["tools"][0]["functionDeclarations"][0]
        self.assertEqual(declaration["name"], alias)
        self.assertEqual(declaration["parameters"]["properties"]["value"], {"type":"STRING", "nullable":True})
        next_messages = [{"role":"user", "content":"remember Ada"}, response, {
            "role":"tool", "tool_call_id":"gemini-call-1", "name":"memory.remember",
            "content":json.dumps({"saved":True})
        }]
        _, converted = provider._contents(next_messages)
        self.assertEqual(converted[1], model_content)
        self.assertEqual(converted[2]["parts"][0]["functionResponse"], {
            "name":alias, "id":"gemini-call-1", "response":{"saved":True}
        })

    def test_gemini_rejects_undeclared_function_call(self):
        provider = GeminiGenerateContentProvider(ProviderConfig(
            "https://generativelanguage.googleapis.com/v1beta", "key", "gemini-3.8-flash"))
        with patch("astrologically_intelligent.providers._post_json", return_value={
            "candidates":[{"content":{"parts":[{"functionCall":{"name":"unknown", "args":{}}}]}}]
        }):
            with self.assertRaisesRegex(RuntimeError, "undeclared function"):
                provider.chat([{"role":"user", "content":"run"}], [])
    def test_anthropic_message_translation_preserves_tool_cycle(self):
        messages=[
            {"role":"system","content":"system rules"},
            {"role":"user","content":"calculate"},
            {"role":"assistant","content":None,"tool_calls":[{"id":"tool-1","type":"function","function":{"name":"calc","arguments":"{\"x\":2}"}}]},
            {"role":"tool","tool_call_id":"tool-1","name":"calc","content":"4"},
        ]
        system, converted=AnthropicMessagesProvider._messages(messages)
        self.assertEqual(system,"system rules")
        self.assertEqual(converted[1]["role"],"assistant")
        self.assertEqual(converted[1]["content"][0]["name"],"calc")
        self.assertEqual(converted[2]["content"][0]["type"],"tool_result")
        self.assertEqual(converted[2]["content"][0]["content"],"4")
    def test_anthropic_tool_response_translation(self):
        provider=AnthropicMessagesProvider(ProviderConfig("https://api.anthropic.com","key","claude-sonnet-4-5"))
        with patch("astrologically_intelligent.providers._post_json",return_value={
            "content":[{"type":"text","text":"Calling tool"},{"type":"tool_use","id":"u1","name":"weather","input":{"city":"NYC"}}]
        }) as post:
            response=provider.chat([{"role":"user","content":"weather"}],[{"type":"function","function":{"name":"weather","description":"Get weather","parameters":{"type":"object","properties":{"city":{"type":"string"}}}}}])
        self.assertEqual(response["tool_calls"][0]["function"]["name"],"weather")
        self.assertEqual(json.loads(response["tool_calls"][0]["function"]["arguments"]),{"city":"NYC"})
        self.assertEqual(post.call_args.args[0],"https://api.anthropic.com/v1/messages")
        self.assertEqual(post.call_args.args[1]["tools"][0]["name"],"weather")
    def test_skill_tools_list_and_read(self):
        names=json.loads(self.runtime.tools.execute("skills.list","{}"))
        self.assertIn("astrology",[item["name"] for item in names])
        guide=json.loads(self.runtime.tools.execute("skills.read",{"name":"astrology"}))
        self.assertIn("Calculation integrity",guide["content"])
    def test_upstream_skill_submodules_are_discovered(self):
        names = {item["name"] for item in json.loads(self.runtime.tools.execute("skills.list", "{}"))}
        self.assertIn("upstream/anthropics-skills/skills/skill-creator", names)
        imported = json.loads(self.runtime.tools.execute(
            "skills.read", {"name":"upstream/anthropics-skills/skills/skill-creator"}))
        self.assertIn("# Skill Creator", imported["content"])

    def test_upstream_skill_with_dot_directory_can_be_read(self):
        names = {item["name"] for item in json.loads(self.runtime.tools.execute("skills.list", "{}"))}
        name = "upstream/openai-skills/skills/.curated/chatgpt-apps"
        self.assertIn(name, names)
        result = json.loads(self.runtime.tools.execute("skills.read", {"name":name}))
        self.assertIn("#", result["content"])

    def test_skill_tool_rejects_path_traversal(self):
        result=json.loads(self.runtime.tools.execute("skills.read",{"name":"../README"}))
        self.assertIn("error",result)
    def test_agent_and_governance_tools_are_registered(self):
        names={item["function"]["name"] for item in self.runtime.tools.definitions()}
        self.assertTrue({"agents.register","agents.execute","goals.create","approvals.request","budgets.set","runs.start","plugins.status"} <= names)
    def test_model_agent_executes_prompt_and_persists_result(self):
        class AgentProvider:
            def chat(self, messages, tools):
                self.messages = messages
                self.tools = tools
                return {"role": "assistant", "content": "Task completed."}

        provider = AgentProvider()
        self.runtime.tools.provider = provider
        agent = json.loads(self.runtime.tools.execute(
            "agents.register", {"name":"Researcher","adapter":"llm","role":"researcher",
                                "config":{"system_prompt":"Research carefully."}}))
        result = json.loads(self.runtime.tools.execute(
            "agents.execute", {"agent_id":agent["id"],"prompt":"Summarize the topic."}))
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["output"], "Task completed.")
        self.assertEqual(provider.messages[0]["content"], "Research carefully.")
        self.assertEqual(provider.messages[1]["content"], "Summarize the topic.")
        self.assertEqual(provider.tools, [])
        run = self.runtime.tools.orchestration.get_run(result["run_id"])
        self.assertEqual(run["status"], "succeeded")
        self.assertEqual(run["output"]["text"], "Task completed.")

    def test_model_agent_execution_rejects_paused_or_unsupported_agents(self):
        agent = json.loads(self.runtime.tools.execute(
            "agents.register", {"name":"Paused","adapter":"llm"}))
        self.runtime.tools.execute("agents.set_state", {"agent_id":agent["id"],"state":"paused"})
        paused = json.loads(self.runtime.tools.execute(
            "agents.execute", {"agent_id":agent["id"],"prompt":"Run this."}))
        self.assertIn("error", paused)
        unsupported = json.loads(self.runtime.tools.execute(
            "agents.register", {"name":"Other","adapter":"shell"}))
        rejected = json.loads(self.runtime.tools.execute(
            "agents.execute", {"agent_id":unsupported["id"],"prompt":"Run this."}))
        self.assertIn("error", rejected)

    def test_model_agent_failure_is_recorded(self):
        class FailingProvider:
            def chat(self, messages, tools):
                raise RuntimeError("provider failure")

        self.runtime.tools.provider = FailingProvider()
        agent = json.loads(self.runtime.tools.execute(
            "agents.register", {"name":"Failing","adapter":"llm"}))
        result = json.loads(self.runtime.tools.execute(
            "agents.execute", {"agent_id":agent["id"],"prompt":"Run this."}))
        self.assertIn("error", result)
        run_rows = self.runtime.tools.orchestration.db.execute(
            "SELECT status, output FROM org_runs WHERE agent_id=?", (agent["id"],)).fetchall()
        self.assertEqual(run_rows[0]["status"], "failed")
        self.assertEqual(json.loads(run_rows[0]["output"]), {"error_type":"RuntimeError"})

    def test_tool_orchestration_budget_and_approval(self):
        agent=json.loads(self.runtime.tools.execute("agents.register",{"name":"Worker","adapter":"local"}))
        budget=json.loads(self.runtime.tools.execute("budgets.set",{"limit_amount":2,"period":"2026-11","agent_id":agent["id"]}))
        spent=json.loads(self.runtime.tools.execute("budgets.record_cost",{"amount":1.5,"period":"2026-11","agent_id":agent["id"]}))
        self.assertEqual(spent["spent_amount"],1.5)
        rejected=json.loads(self.runtime.tools.execute("budgets.record_cost",{"amount":1,"period":"2026-11","agent_id":agent["id"]}))
        self.assertIn("error",rejected)
        approval=json.loads(self.runtime.tools.execute("approvals.request",{"action":"deploy","details":{"env":"prod"},"agent_id":agent["id"]}))
        decided=json.loads(self.runtime.tools.execute("approvals.decide",{"approval_id":approval["id"],"decision":"approved","decided_by":"operator"}))
        self.assertEqual(decided["status"],"approved")
    def test_empty_message_rejected(self):
        with self.assertRaises(ValueError): self.runtime.chat("  ")


if __name__=="__main__": unittest.main()
