import unittest
from unittest.mock import patch

from astrologically_intelligent.integrations import N8nClient, PaperclipClient, PerplexityClient, OpenClawClient


class N8nClientTests(unittest.TestCase):
    def setUp(self):
        self.client = N8nClient("http://localhost:5678", "test-key")

    def test_list_workflows_uses_pagination(self):
        with patch.object(self.client, "_request", return_value={"data": []}) as request:
            self.client.list_workflows(limit=25, cursor="next")
        request.assert_called_once_with("GET", "/api/v1/workflows", {"limit": 25, "cursor": "next"})

    def test_workflow_read_and_activation(self):
        with patch.object(self.client, "_request", return_value={"id": "wf-1"}) as request:
            self.client.get_workflow("wf-1")
            self.assertEqual(request.call_args.args, ("GET", "/api/v1/workflows/wf-1"))
            self.client.set_workflow_active("wf-1", True)
            self.assertEqual(request.call_args.args, ("POST", "/api/v1/workflows/wf-1/activate"))
            self.client.set_workflow_active("wf-1", False)
            self.assertEqual(request.call_args.args, ("POST", "/api/v1/workflows/wf-1/deactivate"))

    def test_rejects_unsafe_ids_and_public_http_credentials(self):
        with self.assertRaises(ValueError):
            self.client.get_workflow("../secrets")
        with self.assertRaises(ValueError):
            N8nClient("http://example.com", "secret")

    def test_execution_listing_applies_filters_and_pagination(self):
        with patch.object(self.client, "_request", return_value={"data": []}) as request:
            self.client.list_executions(
                limit=40, cursor="next", workflow_id="wf-1", status="error",
                started_after="2026-01-01T00:00:00Z", include_data=True,
            )
        request.assert_called_once_with(
            "GET", "/api/v1/executions",
            {"limit": 40, "cursor": "next", "workflowId": "wf-1",
             "status": "error", "startedAfter": "2026-01-01T00:00:00Z",
             "includeData": "true"},
        )

    def test_execution_detail_defaults_to_metadata_only(self):
        with patch.object(self.client, "_request", return_value={"id": "ex-1"}) as request:
            self.client.get_execution("ex-1")
            request.assert_called_once_with("GET", "/api/v1/executions/ex-1", None)
            self.client.get_execution("ex-1", include_data=True)
            request.assert_called_once_with(
                "GET", "/api/v1/executions/ex-1", {"includeData": "true"}
            )

    def test_execution_queries_validate_ids_filters_and_bounds(self):
        with self.assertRaises(ValueError):
            self.client.get_execution("../secrets")
        with self.assertRaises(ValueError):
            self.client.list_executions(status="mystery")
        with self.assertRaises(ValueError):
            self.client.list_executions(limit=251)
        with self.assertRaises(ValueError):
            self.client.list_executions(workflow_id="../secrets")


class PaperclipClientTests(unittest.TestCase):
    def setUp(self):
        self.client = PaperclipClient("http://localhost:3100", "test-token")

    def test_company_scoped_issue_list_and_create(self):
        with patch.object(self.client.http, "request", return_value={"id": "issue-1"}) as request:
            self.client.list_issues("company-1", status="todo,in_progress")
            request.assert_called_once_with("GET", "/api/companies/company-1/issues",
                                            query={"status": "todo,in_progress"})
            self.client.create_issue("company-1", "Implement integration", priority="high")
            self.assertEqual(request.call_args.args,
                             ("POST", "/api/companies/company-1/issues",
                              {"title":"Implement integration","description":"","status":"todo","priority":"high"}))

    def test_agent_goal_approval_routes(self):
        with patch.object(self.client.http, "request", return_value=[]) as request:
            self.client.list_agents("co-1")
            self.assertEqual(request.call_args.args, ("GET", "/api/companies/co-1/agents"))
            self.client.list_approvals("co-1", "pending")
            self.assertEqual(request.call_args.kwargs["query"], {"status":"pending"})
            self.client.create_goal("co-1", "Ship release")
            self.assertEqual(request.call_args.args,
                             ("POST", "/api/companies/co-1/goals",
                              {"title":"Ship release","description":""}))

    def test_rejects_unsafe_company_ids_and_public_http_credentials(self):
        with self.assertRaises(ValueError):
            self.client.list_agents("../private")
        with self.assertRaises(ValueError):
            PaperclipClient("http://example.com", "secret")



class PerplexityClientTests(unittest.TestCase):
    def test_search_uses_documented_search_endpoint(self):
        client = PerplexityClient("test-key")
        with patch.object(client.http, "request", return_value={"results": []}) as request:
            client.search("AI agent frameworks", max_results=7)
        request.assert_called_once_with("POST", "/search",
                                       {"query":"AI agent frameworks","max_results":7})

    def test_search_validates_query_and_result_limit(self):
        client = PerplexityClient("test-key")
        with self.assertRaises(ValueError):
            client.search(" ")
        with self.assertRaises(ValueError):
            client.search("test", max_results=21)




class OpenClawClientTests(unittest.TestCase):
    def test_sessions_list_uses_read_only_tool_invoke(self):
        client = OpenClawClient("http://127.0.0.1:18789", "operator-token")
        with patch.object(client.http, "request", return_value={"ok": True}) as request:
            client.list_sessions("main")
        request.assert_called_once_with("POST", "/tools/invoke",
                                        {"tool":"sessions_list","args":{},"sessionKey":"main"})

    def test_sessions_list_rejects_invalid_session_key(self):
        client = OpenClawClient("http://127.0.0.1:18789", "operator-token")
        with self.assertRaises(ValueError):
            client.list_sessions("../../secrets")



if __name__ == "__main__":
    unittest.main()
