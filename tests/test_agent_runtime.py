import json
import unittest

from astrologically_intelligent.providers import OpenAICompatibleProvider, ProviderConfig
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
    def test_tool_call_and_session_persistence(self):
        result=self.runtime.chat("Remember my preferred name is Ada.","session-a")
        self.assertEqual(result["response"],"Memory saved.")
        self.assertEqual(self.store.recall("profile","preferred_name")[0]["value"],"Ada")
        self.assertEqual([m["role"] for m in self.store.history("session-a")],["user","assistant"])
    def test_work_item_lifecycle(self):
        task=self.store.create_task("Build an integration")
        self.assertEqual(task["status"],"open")
        updated=self.store.update_task(task["id"],"in_progress","agent-1")
        self.assertEqual(updated["assignee"],"agent-1")
    def test_provider_request_shape(self):
        provider=OpenAICompatibleProvider(ProviderConfig("http://localhost:1234/v1","","test-model"))
        self.assertEqual(provider.config.model,"test-model")
    def test_skill_tools_list_and_read(self):
        names=json.loads(self.runtime.tools.execute("skills.list","{}"))
        self.assertIn("astrology",[item["name"] for item in names])
        guide=json.loads(self.runtime.tools.execute("skills.read",{"name":"astrology"}))
        self.assertIn("Calculation integrity",guide["content"])
    def test_skill_tool_rejects_path_traversal(self):
        result=json.loads(self.runtime.tools.execute("skills.read",{"name":"../README"}))
        self.assertIn("error",result)
    def test_agent_and_governance_tools_are_registered(self):
        names={item["function"]["name"] for item in self.runtime.tools.definitions()}
        self.assertTrue({"agents.register","goals.create","approvals.request","budgets.set","runs.start","plugins.status"} <= names)
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
