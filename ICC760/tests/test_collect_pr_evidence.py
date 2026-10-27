import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

from ICC760.scripts import collect_pr_evidence as collector


def issue(repo="dotnet/runtime", number=134305, **extra):
    return {"number": number, "html_url": f"https://github.com/{repo}/issues/{number}",
            "title": "Workflow diagnosis", "body": "Technical context, not a closure decision.", **extra}


def evidence(body=""):
    return {"pr": {"repository": "dotnet/runtime", "number": 134186,
                   "url": "https://github.com/dotnet/runtime/pull/134186", "body": body},
            "origin": {"run_id": 123}, "comments": [], "reviews": [], "review_comments": [],
            "ci": {"original": "preserved"}, "collection_errors": []}


def cross_reference(source_issue):
    return {"event": "cross-referenced", "created_at": "2026-09-20T13:21:24Z",
            "source": {"type": "issue", "issue": source_issue}}


class LinkedIssuesTests(unittest.TestCase):
    def collect(self, record, responses):
        def github(args):
            endpoint = args[-1]
            if endpoint not in responses:
                self.fail(f"Unexpected request: {args}")
            response = responses[endpoint]
            if isinstance(response, Exception):
                raise response
            return copy.deepcopy(response)

        with patch.object(collector, "gh_json", side_effect=github) as mock:
            collector.collect_linked_issues(record)
        return mock

    def test_runtime_timeline_relation_and_issue_content(self):
        record = evidence()
        original = copy.deepcopy(record)
        self.collect(record, {
            "repos/dotnet/runtime/issues/134186/timeline?per_page=100": [[cross_reference(issue())]],
            "repos/dotnet/runtime/issues/134305": issue(),
            "repos/dotnet/runtime/issues/134305/comments?per_page=100": [[{"body": "First page"}], [{"body": "Second page"}]],
        })
        linked = record["linked_issues"]
        self.assertEqual(len(linked), 1)
        self.assertEqual((linked[0]["repository"], linked[0]["number"]), ("dotnet/runtime", 134305))
        self.assertEqual(linked[0]["relations"][0]["type"], "cross-referenced")
        self.assertEqual(linked[0]["content"]["body"], issue()["body"])
        self.assertEqual(len(linked[0]["comments"]), 2)
        for key in original:
            self.assertEqual(record[key], original[key])

    def test_no_relationship_and_pull_request_references_are_excluded(self):
        for body in ("No references", "See #134306 and https://github.com/dotnet/runtime/pull/134307"):
            with self.subTest(body=body):
                record = evidence(body)
                self.collect(record, {
                    "repos/dotnet/runtime/issues/134186/timeline?per_page=100": [[cross_reference(issue(number=134308, pull_request={}))]],
                    "repos/dotnet/runtime/issues/134306": issue(number=134306, pull_request={}),
                })
                self.assertEqual(record["linked_issues"], [])
                self.assertEqual(record["linked_issues_collection"]["status"], "complete")
                self.assertIn("consulta manual", record["linked_issues_collection"]["limitations"][-1])

    def test_duplicate_sources_cross_repository_and_pagination(self):
        record = evidence("See #134305, DOTNET/runtime#134305 and https://github.com/other/project/issues/7")
        record["reviews"] = [{"html_url": "https://github.com/dotnet/runtime/pull/134186#review-1",
                              "body": "Also other/project\\#7"}]
        mock = self.collect(record, {
            "repos/dotnet/runtime/issues/134186/timeline?per_page=100": [[], [cross_reference(issue()), cross_reference(issue("other/project", 7))]],
            "repos/dotnet/runtime/issues/134305": issue(),
            "repos/dotnet/runtime/issues/134305/comments?per_page=100": [[]],
            "repos/other/project/issues/7": issue("other/project", 7),
            "repos/other/project/issues/7/comments?per_page=100": [[]],
        })
        self.assertEqual(len(record["linked_issues"]), 2)
        self.assertEqual(len(record["linked_issues"][0]["relations"]), 3)
        self.assertEqual(len(record["linked_issues"][1]["relations"]), 3)
        endpoints = [call.args[0][-1] for call in mock.call_args_list]
        self.assertEqual(endpoints.count("repos/dotnet/runtime/issues/134305"), 1)
        mock.assert_any_call(["api", "--paginate", "--slurp", "repos/dotnet/runtime/issues/134186/timeline?per_page=100"])

    def test_api_failures_are_traced_and_other_issues_continue(self):
        record = evidence("See #1 and #2")
        self.collect(record, {
            "repos/dotnet/runtime/issues/134186/timeline?per_page=100": collector.GitHubCLIError("403 forbidden"),
            "repos/dotnet/runtime/issues/1": collector.GitHubCLIError("404 not found"),
            "repos/dotnet/runtime/issues/2": issue(number=2),
            "repos/dotnet/runtime/issues/2/comments?per_page=100": collector.GitHubCLIError("503 unavailable"),
        })
        self.assertEqual([item["number"] for item in record["linked_issues"]], [2])
        self.assertEqual(len(record["collection_errors"]), 3)
        self.assertEqual(record["linked_issues_collection"]["status"], "partial")
        for error in record["collection_errors"]:
            self.assertIn("endpoint", error)
            self.assertIn("collected_at", error)
        self.assertEqual(record["collection_errors"][1]["relations"][0]["type"], "text_reference")

    def test_markdown_labels_do_not_create_false_local_relationships(self):
        record = evidence("See [#7](https://github.com/other/project/issues/7) "
                          "and [#8](https://github.com/other/project/pull/8).")
        self.collect(record, {
            "repos/dotnet/runtime/issues/134186/timeline?per_page=100": [[]],
            "repos/other/project/issues/7": issue("other/project", 7),
            "repos/other/project/issues/7/comments?per_page=100": [[]],
        })
        self.assertEqual([(item["repository"], item["number"]) for item in record["linked_issues"]],
                         [("other/project", 7)])

    def test_refresh_failure_preserves_previously_collected_issue(self):
        record = evidence("See #134305")
        responses = {
            "repos/dotnet/runtime/issues/134186/timeline?per_page=100": [[]],
            "repos/dotnet/runtime/issues/134305": issue(),
            "repos/dotnet/runtime/issues/134305/comments?per_page=100": [[{"body": "Keep this"}]],
        }
        self.collect(record, responses)
        original = copy.deepcopy(record["linked_issues"])
        responses["repos/dotnet/runtime/issues/134305"] = collector.GitHubCLIError("404")
        self.collect(record, responses)
        self.assertEqual(record["linked_issues"], original)
        responses["repos/dotnet/runtime/issues/134305"] = issue()
        responses["repos/dotnet/runtime/issues/134305/comments?per_page=100"] = collector.GitHubCLIError("403")
        self.collect(record, responses)
        self.assertEqual(record["linked_issues"][0]["comments"], original[0]["comments"])

    def test_resume_backfills_old_evidence_retries_partial_and_skips_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "input.json", Path(directory) / "output.json"
            source.write_text(json.dumps([{"target_repo": "dotnet/runtime", "pr_number": 134186},
                                          {"target_repo": "other/project", "pr_number": 10}]))
            original = evidence()
            target.write_text(json.dumps({"pull_requests": [original]}))
            args = ["collect", "--input", str(source), "--output", str(target), "--delay", "0"]
            with patch("sys.argv", args), redirect_stdout(io.StringIO()), \
                    patch.object(collector, "api", side_effect=collector.GitHubCLIError("403")), \
                    patch.object(collector, "fetch_pr_evidence", return_value={"pr": {"repository": "other/project", "number": 10}}) as fetch:
                self.assertEqual(collector.main(), 0)
                fetch.assert_called_once()
            saved = json.loads(target.read_text())["pull_requests"]
            self.assertEqual(len(saved), 2)
            self.assertEqual(saved[0]["pr"], original["pr"])
            self.assertEqual(saved[0]["ci"], original["ci"])
            self.assertEqual(saved[0]["linked_issues_collection"]["status"], "partial")
            with patch("sys.argv", args), redirect_stdout(io.StringIO()), patch.object(collector, "api", return_value=[]) as api:
                self.assertEqual(collector.main(), 0)
                self.assertEqual(api.call_count, 2)
            with patch("sys.argv", args), redirect_stdout(io.StringIO()), patch.object(collector, "gh_json") as gh:
                self.assertEqual(collector.main(), 0)
                gh.assert_not_called()
            self.assertFalse(target.with_name("output.json.tmp").exists())

    def test_corrupt_checkpoint_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "input.json", Path(directory) / "output.json"
            source.write_text("[]")
            target.write_text("{broken")
            with patch("sys.argv", ["collect", "--input", str(source), "--output", str(target)]), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    collector.main()
            self.assertEqual(target.read_text(), "{broken")

    def test_failed_pr_does_not_block_next_pr_and_is_retried_on_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "input.json", Path(directory) / "output.json"
            source.write_text(json.dumps([{"target_repo": "dotnet/runtime", "pr_number": 1},
                                          {"target_repo": "dotnet/runtime", "pr_number": 2}]))
            args = ["collect", "--input", str(source), "--output", str(target), "--delay", "0"]

            def github(args):
                if args[-1] == "repos/dotnet/runtime/pulls/1":
                    raise collector.GitHubCLIError("404")
                if args[-1] == "repos/dotnet/runtime/pulls/2":
                    return {"number": 2, "body": "No references", "state": "closed", "merged_at": None}
                return [[]]

            with patch("sys.argv", args), redirect_stdout(io.StringIO()), patch.object(collector, "gh_json", side_effect=github):
                self.assertEqual(collector.main(), 0)
            saved = json.loads(target.read_text())["pull_requests"]
            self.assertEqual(len(saved), 2)
            self.assertEqual(saved[0]["collection_errors"][0]["source"], "pull_request")
            self.assertEqual(saved[1]["linked_issues"], [])
            self.assertEqual(saved[1]["linked_issues_collection"]["status"], "complete")
            recovered = evidence()
            recovered["pr"].update({"number": 1, "url": "https://github.com/dotnet/runtime/pull/1"})
            with patch("sys.argv", args), redirect_stdout(io.StringIO()), \
                    patch.object(collector, "gh_json", return_value=[]), \
                    patch.object(collector, "fetch_pr_evidence", return_value=recovered) as fetch:
                self.assertEqual(collector.main(), 0)
                fetch.assert_called_once_with({"target_repo": "dotnet/runtime", "pr_number": 1})
            self.assertEqual(json.loads(target.read_text())["pull_requests"][1], saved[1])


if __name__ == "__main__":
    unittest.main()
