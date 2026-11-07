import io
import json
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import patch

from scripts.import_upstream_orgs import existing_submodule_urls, import_repositories, list_repositories, fetch_commit_sha


class UpstreamImporterTests(unittest.TestCase):
    def test_listing_includes_all_public_repo_types_and_paginates(self):
        first = [{"name": f"repo{i}", "owner": {"login":"anthropics"},
                  "private":False,"clone_url":f"https://github.com/anthropics/repo{i}.git",
                  "default_branch":"main","size":10,"archived":i == 0,"fork":i == 1}
                 for i in range(100)]
        second = [{"name":"last","owner":{"login":"anthropics"},"private":False,
                   "clone_url":"https://github.com/anthropics/last.git","default_branch":"main"}]
        with patch("scripts.import_upstream_orgs.fetch_page", side_effect=[first, second]):
            repos = list_repositories(("anthropics",))
        self.assertEqual(len(repos), 101)
        self.assertTrue(repos[0]["archived"])
        self.assertTrue(repos[1]["fork"])

    def test_import_is_resumable_and_dry_run_does_not_clone(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("scripts.import_upstream_orgs.existing_submodule_urls", return_value=set()):
                repo = {"org":"openai","name":"skills","branch":"main",
                        "clone_url":"https://github.com/openai/skills.git"}
                with patch("scripts.import_upstream_orgs.fetch_commit_sha", return_value="a"*40):
                    with patch("scripts.import_upstream_orgs.subprocess.run") as run:
                        added, skipped = import_repositories(root,[repo],dry_run=True)
                run.assert_not_called()
                self.assertEqual((added,skipped),(1,0))

    def test_empty_repositories_are_skipped_without_git_operations(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            empty={"org":"anthropics","name":"empty","branch":"main",
                   "clone_url":"https://github.com/anthropics/empty.git","empty":True}
            with patch("scripts.import_upstream_orgs.existing_submodule_urls", return_value=set()):
                with patch("scripts.import_upstream_orgs.subprocess.run") as run:
                    added,skipped=import_repositories(root,[empty])
            run.assert_not_called()
            self.assertEqual((added,skipped),(0,1))

    def test_gitlink_import_records_url_branch_and_commit_without_cloning(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            repo={"org":"openai","name":"skills","branch":"main",
                  "clone_url":"https://github.com/openai/skills.git","empty":False}
            calls=[]
            def fake_run(command, **kwargs):
                calls.append(command)
                return type("Result",(),{"returncode":0,"stdout":"","stderr":""})()
            with patch("scripts.import_upstream_orgs.existing_submodule_urls", return_value=set()):
                with patch("scripts.import_upstream_orgs.fetch_commit_sha", return_value="b"*40):
                    with patch("scripts.import_upstream_orgs.subprocess.run", side_effect=fake_run):
                        added,skipped=import_repositories(root,[repo])
            self.assertEqual((added,skipped),(1,0))
            self.assertTrue(any("160000,"+"b"*40+",upstream/openai/skills" in " ".join(c) for c in calls))
            self.assertTrue(any("submodule.upstream/openai/skills.url" in c for c in calls))
            self.assertTrue(any("submodule.upstream/openai/skills.branch" in c for c in calls))

    def test_existing_submodule_urls_are_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/".gitmodules").write_text(
                '[submodule "upstream/openai/skills"]\n\tpath = upstream/openai/skills\n'
                '\turl = https://github.com/openai/skills.git\n',encoding="utf-8")
            with patch("scripts.import_upstream_orgs.subprocess.run",
                       return_value=type("Result",(),{"returncode":0,"stdout":"submodule.upstream/openai/skills.url https://github.com/openai/skills.git\n","stderr":""})()):
                self.assertEqual(existing_submodule_urls(root),{"https://github.com/openai/skills"})


    def test_requested_organization_scope_includes_all_twenty_organizations(self):
        from scripts.import_upstream_orgs import ORGANIZATIONS, AI_QUERY_ORGANIZATIONS

        self.assertEqual(len(ORGANIZATIONS), 20)
        self.assertTrue({
            "apple", "aws", "brave", "cursor", "deepseek-ai", "google",
            "herdrdev", "kagisearch", "lukalabs", "meta-llama", "microsoft",
            "n8n-io", "NousResearch", "odysseus-dev", "openai", "openclaw",
            "paperclipai", "perplexityai", "xai-org", "anthropics",
        }.issubset(set(ORGANIZATIONS)))
        self.assertEqual(
            AI_QUERY_ORGANIZATIONS,
            {"apple", "aws", "brave", "google", "kagisearch", "microsoft"},
        )

    def test_ai_query_organizations_use_search_results_not_full_org_listing(self):
        item = {
            "name": "ml-project",
            "owner": {"login": "apple"},
            "private": False,
            "clone_url": "https://github.com/apple/ml-project.git",
            "default_branch": "main",
            "size": 10,
        }
        with patch("scripts.import_upstream_orgs.fetch_search_page", return_value=([item], 1)) as search:
            with patch("scripts.import_upstream_orgs.fetch_page") as listing:
                repos = list_repositories(("apple",))
        self.assertEqual([repo["name"] for repo in repos], ["ml-project"])
        search.assert_called_once_with("apple", 1, None)
        listing.assert_not_called()

    def test_ai_search_uses_the_requested_org_query(self):
        from scripts.import_upstream_orgs import fetch_search_page

        response = io.BytesIO(json.dumps({"items": []}).encode("utf-8"))
        with patch("scripts.import_upstream_orgs.urllib.request.urlopen", return_value=response) as open_url:
            self.assertEqual(fetch_search_page("apple", 1, "test-token"), ([], 0))
        request = open_url.call_args.args[0]
        parsed = urllib.parse.urlparse(request.full_url)
        self.assertEqual(parsed.path, "/search/repositories")
        self.assertEqual(urllib.parse.parse_qs(parsed.query)["q"], ["org:apple AI"])
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")

    def test_non_query_organizations_still_import_all_public_repositories(self):
        item = {
            "name": "repo",
            "owner": {"login": "cursor"},
            "private": False,
            "clone_url": "https://github.com/cursor/repo.git",
            "default_branch": "main",
            "size": 10,
        }
        with patch("scripts.import_upstream_orgs.fetch_page", side_effect=[[item]]) as listing:
            with patch("scripts.import_upstream_orgs.fetch_search_page") as search:
                repos = list_repositories(("cursor",))
        self.assertEqual([repo["name"] for repo in repos], ["repo"])
        listing.assert_called_once_with("cursor", 1, None)
        search.assert_not_called()

    def test_ai_search_stops_at_github_search_limit_and_reports_truncation(self):
        pages = []
        for page in range(10):
            pages.append(([{
                "name": f"repo-{page}-{index}",
                "owner": {"login": "microsoft"},
                "private": False,
                "clone_url": f"https://github.com/microsoft/repo-{page}-{index}.git",
                "default_branch": "main",
                "size": 10,
            } for index in range(100)], 1200))
        with patch("scripts.import_upstream_orgs.fetch_search_page", side_effect=pages) as search:
            with patch("builtins.print") as output:
                repos = list_repositories(("microsoft",))
        self.assertEqual(len(repos), 1000)
        self.assertEqual(search.call_count, 10)
        output.assert_called_once()
        self.assertIn("first 1,000", output.call_args.args[0])

if __name__ == "__main__":
    unittest.main()
