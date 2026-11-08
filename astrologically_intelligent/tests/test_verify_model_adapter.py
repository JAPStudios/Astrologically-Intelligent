import json
import importlib.util
from pathlib import Path


def _load_script():
    path = Path(__file__).resolve().parents[1] / "scripts" / "verify_model_adapter.py"
    spec = importlib.util.spec_from_file_location("verify_model_adapter_under_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _Client:
    def __init__(self, *, candidate_delta=0.0, fail=False):
        self.candidate_delta = candidate_delta
        self.fail = fail
        self.requests = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, *, json, headers, timeout):
        self.requests.append((url, json, headers, timeout))
        if self.fail:
            return _Response({"choices": [{"message": {"content": "no logprobs"}}]})
        delta = self.candidate_delta if json["model"] == "candidate" else 0.0
        return _Response({
            "choices": [{
                "logprobs": {
                    "content": [{
                        "top_logprobs": [
                            {"token": "manage_notes", "logprob": -0.1 - delta},
                            {"token": "web_search", "logprob": -1.2 + delta},
                        ]
                    }]
                }
            }]
        })


def _args(tmp_path, *, minimum=2, minimum_probes=2):
    return [
        "--base-url", "http://base/v1",
        "--candidate-url", "http://candidate/v1",
        "--base-model", "base",
        "--candidate-model", "candidate",
        "--prompt", "List my notes",
        "--prompt", "Search the web",
        "--output", str(tmp_path / "report.json"),
        "--minimum-different-prompts", str(minimum),
        "--minimum-probes", str(minimum_probes),
    ]


def test_identical_logprob_distributions_flag_inactive_adapter(tmp_path, monkeypatch):
    module = _load_script()
    client = _Client()
    monkeypatch.setattr(module.httpx, "Client", lambda: client)

    result = module.main(_args(tmp_path))

    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert result == 1
    assert report["status"] == "inactive"
    assert report["identical_prompts"] == 2
    assert all(request[1]["chat_template_kwargs"] == {"enable_thinking": False} for request in client.requests)


def test_changed_logprobs_confirm_candidate_differs_from_base(tmp_path, monkeypatch):
    module = _load_script()
    client = _Client(candidate_delta=0.2)
    monkeypatch.setattr(module.httpx, "Client", lambda: client)

    result = module.main(_args(tmp_path))

    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert result == 0
    assert report["status"] == "different"
    assert report["different_prompts"] == 2


def test_mixed_probe_results_are_inconclusive_below_threshold(tmp_path, monkeypatch):
    module = _load_script()
    client = _Client(candidate_delta=0.2)
    calls = {"count": 0}
    original_post = client.post

    def one_difference(url, *, json, headers, timeout):
        calls["count"] += 1
        if calls["count"] > 2:
            json = dict(json)
            json["model"] = "base"
        return original_post(url, json=json, headers=headers, timeout=timeout)

    client.post = one_difference
    monkeypatch.setattr(module.httpx, "Client", lambda: client)

    result = module.main(_args(tmp_path, minimum=2))

    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert result == 2
    assert report["status"] == "inconclusive"
    assert report["different_prompts"] == 1


def test_missing_logprobs_fails_closed(tmp_path, monkeypatch, capsys):
    module = _load_script()
    client = _Client(fail=True)
    monkeypatch.setattr(module.httpx, "Client", lambda: client)

    result = module.main(_args(tmp_path))

    assert result == 3
    assert "omitted logprobs" in capsys.readouterr().err


def test_too_few_identical_probes_are_inconclusive(tmp_path, monkeypatch):
    module = _load_script()
    client = _Client()
    monkeypatch.setattr(module.httpx, "Client", lambda: client)
    args = _args(tmp_path, minimum_probes=3)
    second_prompt = args.index("--prompt", args.index("--prompt") + 1)
    del args[second_prompt:second_prompt + 2]

    result = module.main(args)

    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert result == 2
    assert report["status"] == "inconclusive"
    assert report["prompts_tested"] == 1
