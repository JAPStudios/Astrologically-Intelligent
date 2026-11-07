import unittest

from astrologically_intelligent.orchestration import Orchestrator


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.org = Orchestrator(":memory:")

    def tearDown(self):
        self.org.close()

    def test_agent_goal_and_heartbeat(self):
        agent = self.org.register_agent("Researcher", "python", "local-model", heartbeat_seconds=60)
        self.assertEqual(agent["state"], "active")
        self.assertEqual(self.org.due_agents(now=1000)[0]["id"], agent["id"])
        self.org.mark_heartbeat(agent["id"], at=1000)
        self.assertEqual(self.org.due_agents(now=1059), [])
        self.assertEqual(self.org.due_agents(now=1060)[0]["id"], agent["id"])
        goal = self.org.create_goal("Ship release", owner_agent_id=agent["id"])
        self.assertEqual(goal["owner_agent_id"], agent["id"])

    def test_approval_requires_pending_state(self):
        agent = self.org.register_agent("Ops", "command")
        approval = self.org.request_approval("deploy", {"environment": "production"}, agent["id"])
        approved = self.org.decide_approval(approval["id"], "approved", "operator", "Reviewed")
        self.assertEqual(approved["status"], "approved")
        self.assertIsNone(self.org.decide_approval(approval["id"], "rejected", "operator"))

    def test_budget_enforced(self):
        agent = self.org.register_agent("Analyst", "api")
        budget = self.org.set_budget(10, "2026-11", agent["id"])
        self.assertEqual(budget["spent_amount"], 0)
        self.org.record_cost(6.5, "2026-11", agent["id"])
        with self.assertRaises(ValueError):
            self.org.record_cost(4, "2026-11", agent["id"])

    def test_organization_budget_upsert_updates_null_agent_row(self):
        first = self.org.set_budget(100, "2026-11", currency="USD")
        self.org.record_cost(25, "2026-11")
        updated = self.org.set_budget(60, "2026-11", currency="EUR")

        self.assertEqual(updated["id"], first["id"])
        self.assertEqual(updated["limit_amount"], 60)
        self.assertEqual(updated["spent_amount"], 25)
        self.assertEqual(updated["currency"], "EUR")
        budgets = [row for row in self.org.budgets() if row["agent_id"] is None]
        self.assertEqual(len(budgets), 1)

    def test_run_lifecycle(self):
        agent = self.org.register_agent("Worker", "local")
        run = self.org.start_run(agent["id"], input_data={"task": "test"})
        done = self.org.finish_run(run["id"], "succeeded", {"ok": True}, 0.25)
        self.assertEqual(done["status"], "succeeded")
        self.assertIsNone(self.org.finish_run(run["id"], "failed"))


if __name__ == "__main__":
    unittest.main()
