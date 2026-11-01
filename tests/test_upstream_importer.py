import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.import_upstream_orgs import existing_submodule_urls, import_repositories, list_repositories


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

    def test_existing_submodule_urls_are_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/".gitmodules").write_text(
                '[submodule "upstream/openai/skills"]\n\tpath = upstream/openai/skills\n'
                '\turl = https://github.com/openai/skills.git\n',encoding="utf-8")
            with patch("scripts.import_upstream_orgs.subprocess.run",
                       return_value=type("Result",(),{"returncode":0,"stdout":"submodule.upstream/openai/skills.url https://github.com/openai/skills.git\n","stderr":""})()):
                self.assertEqual(existing_submodule_urls(root),{"https://github.com/openai/skills"})


if __name__ == "__main__":
    unittest.main()
