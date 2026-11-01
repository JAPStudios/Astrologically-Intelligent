import unittest
from unittest.mock import patch

from astrologically_intelligent.integrations import N8nClient


class N8nClientTests(unittest.TestCase):
    def setUp(self):
        self.client = N8nClient("http://localhost:5678", "test-key")

    def test_list_workflows_uses_api_key_and_pagination(self):
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


if __name__ == "__main__":
    unittest.main()
