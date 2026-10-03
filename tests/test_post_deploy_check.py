from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from urllib.error import URLError

import pytest


@pytest.fixture
def checker(monkeypatch):
    script = Path("scripts/qa/verify_post_deploy.py")
    monkeypatch.syspath_prepend(str(script.parent.resolve()))
    spec = importlib.util.spec_from_file_location("post_deploy_checker", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    return module


RESPONSES = json.loads(Path("tests/fixtures/post_deploy/responses.json").read_text())
SHA = RESPONSES["fingerprint"]["git_sha"]
BACKEND = "http://backend.test"
FRONTEND = "http://frontend.test/"


def replay(monkeypatch, checker, case):
    responses = {
        BACKEND + "/health": json.dumps(RESPONSES["health"]),
        BACKEND + "/health/deploy": json.dumps(RESPONSES["fingerprint"]),
        BACKEND + "/report/dashboard/stats": json.dumps(case["stats"]),
        BACKEND + "/report/companies?skip=0&limit=50": json.dumps(case["companies"]),
        FRONTEND: RESPONSES["frontend"],
        FRONTEND + "assets/index-recorded.js": "/* recorded frontend entrypoint */",
    }
    # No test can reach a network service: every URL must exist in this recording.
    monkeypatch.setattr(checker, "read_url", responses.__getitem__)
    return responses


@pytest.mark.parametrize("case", RESPONSES["cases"], ids=lambda case: case["name"])
def test_recorded_dashboard_responses(monkeypatch, checker, case):
    replay(monkeypatch, checker, case)
    if case["passes"]:
        checker.verify(BACKEND, FRONTEND, SHA)
    else:
        with pytest.raises(ValueError, match="null|source records"):
            checker.verify(BACKEND, FRONTEND, SHA)


@pytest.mark.parametrize("fingerprint", [{}, {"status": "ok"}, {"status": "ok", "git_sha": "a" * 40}, {"status": "bad", "git_sha": SHA}])
def test_rejects_missing_or_stale_deployed_sha(monkeypatch, checker, fingerprint):
    responses = replay(monkeypatch, checker, RESPONSES["cases"][0])
    responses[BACKEND + "/health/deploy"] = json.dumps(fingerprint)
    with pytest.raises(ValueError, match="deploy health|git_sha"):
        checker.verify(BACKEND, FRONTEND, SHA)


def test_detects_revision_swap_during_check(monkeypatch, checker):
    responses = replay(monkeypatch, checker, RESPONSES["cases"][0])
    fingerprints = iter([RESPONSES["fingerprint"], {"status": "ok", "git_sha": "a" * 40}])
    monkeypatch.setattr(checker, "read_url", lambda url: json.dumps(next(fingerprints)) if url.endswith("/health/deploy") else responses[url])
    with pytest.raises(ValueError, match="git_sha"):
        checker.verify(BACKEND, FRONTEND, SHA)


def test_reads_all_company_pages_including_zero_after_unknown_page(monkeypatch, checker):
    case = copy.deepcopy(RESPONSES["cases"][4])
    responses = replay(monkeypatch, checker, case)
    unknown = copy.deepcopy(RESPONSES["cases"][2]["companies"][0])
    responses[BACKEND + "/report/companies?skip=0&limit=50"] = json.dumps([unknown] * 50)
    responses[BACKEND + "/report/companies?skip=50&limit=50"] = json.dumps(case["companies"])
    checker.verify(BACKEND, FRONTEND, SHA)


@pytest.mark.parametrize("url,body", [("/health", '{"status":"bad"}'), ("/report/companies?skip=0&limit=50", "{}"), ("/report/dashboard/stats", "not json"), ("frontend", "<html>error</html>"), ("assets/index-recorded.js", "")])
def test_rejects_bad_service_responses(monkeypatch, checker, url, body):
    responses = replay(monkeypatch, checker, RESPONSES["cases"][0])
    responses[FRONTEND if url == "frontend" else FRONTEND + url if url.startswith("assets/") else BACKEND + url] = body
    with pytest.raises(ValueError):
        checker.verify(BACKEND, FRONTEND, SHA)


@pytest.mark.parametrize("missing", ["company_name", "renewable_energy_pct"])
def test_rejects_incomplete_source_records(checker, missing):
    case = copy.deepcopy(RESPONSES["cases"][4])
    del case["companies"][0][missing]
    with pytest.raises(ValueError, match="missing"):
        checker.validate_dashboard(case["stats"], case["companies"])


@pytest.mark.parametrize("fails", [False, True])
def test_cli_exit_status_and_safe_output(monkeypatch, checker, capsys, fails):
    replay(monkeypatch, checker, RESPONSES["cases"][0])
    monkeypatch.setattr(sys, "argv", ["check", "--backend-url", BACKEND, "--frontend-url", FRONTEND, "--expected-sha", SHA])
    if fails:
        def unavailable(url):
            raise URLError("private response must never be printed")
        monkeypatch.setattr(checker, "read_url", unavailable)
    assert checker.main() == int(fails)
    output = capsys.readouterr()
    assert "private response" not in output.err
    assert ("failed" in output.err) if fails else (SHA in output.out)


def test_deploy_script_wires_pinned_check_and_rollback():
    script = Path("scripts/deploy.sh").read_text()
    assert 'DEPLOY_SHA="$(git rev-parse HEAD)"' in script
    assert '"$DEPLOY_SHA" != "$GITHUB_SHA"' in script
    assert '--expected-sha "$DEPLOY_SHA"' in script
    check = script.split('if ! python3 "$REPO_DIR/scripts/qa/verify_post_deploy.py"')[1].split("fi", 1)[0]
    assert "--backend-url http://localhost:8001" in check
    assert "--frontend-url" not in check
    assert "https://" not in check
    assert 'rollback_and_exit "pinned dashboard post-deploy check failed"' in script


@pytest.mark.parametrize("average", ["avg_taxonomy_aligned", "avg_renewable_pct"])
def test_rejects_each_unknown_average_coerced_to_zero(checker, average):
    case = copy.deepcopy(RESPONSES["cases"][2])
    case["stats"][average] = 0
    with pytest.raises(ValueError, match=average):
        checker.validate_dashboard(case["stats"], case["companies"])


def test_rejects_missing_values_included_in_denominator(checker):
    case = copy.deepcopy(RESPONSES["cases"][-1])
    case["stats"]["avg_taxonomy_aligned"] = 10
    with pytest.raises(ValueError, match="avg_taxonomy_aligned"):
        checker.validate_dashboard(case["stats"], case["companies"])


def test_public_dashboard_workflow_also_pins_sha():
    workflow = Path(".github/workflows/deploy.yml").read_text()
    public_check = workflow.split("- name: Verify public dashboard stats")[1]
    assert "verify_post_deploy.py" in public_check
    assert '--expected-sha "$EXPECTED_GITHUB_SHA"' in public_check
    assert '--frontend-url "$frontend_url"' in public_check
    assert "rollback" not in public_check
    assert 'public deploy git_sha mismatch: expected {expected}, got {actual}' in workflow
    assert 'echo "$payload"' not in workflow


def test_cli_local_backend_only(monkeypatch, checker, capsys):
    responses = replay(monkeypatch, checker, RESPONSES["cases"][0])
    del responses[FRONTEND]
    del responses[FRONTEND + "assets/index-recorded.js"]
    monkeypatch.setattr(sys, "argv", ["check", "--backend-url", BACKEND, "--expected-sha", SHA])
    assert checker.main() == 0
    assert SHA in capsys.readouterr().out


@pytest.mark.parametrize("mismatch_count", [1, 2, 3])
@pytest.mark.parametrize("metric", ["total_companies", "avg_taxonomy_aligned", "avg_renewable_pct"])
def test_retries_comparison_with_fresh_responses(monkeypatch, checker, mismatch_count, metric):
    unknown = RESPONSES["cases"][2]
    zero = RESPONSES["cases"][4]
    responses = replay(monkeypatch, checker, unknown)
    changed_stats = copy.deepcopy(unknown["stats"])
    changed_stats[metric] = 2 if metric == "total_companies" else 0
    companies = iter([unknown["companies"]] * mismatch_count + [zero["companies"]])
    stats = iter([changed_stats] * mismatch_count + [zero["stats"]])
    calls = []
    sleeps = []

    def read(url):
        calls.append(url)
        if url.endswith("/report/companies?skip=0&limit=50"):
            return json.dumps(next(companies))
        if url.endswith("/report/dashboard/stats"):
            return json.dumps(next(stats))
        return responses[url]

    monkeypatch.setattr(checker, "read_url", read)
    monkeypatch.setattr(checker.time, "sleep", sleeps.append)
    if mismatch_count == 3:
        with pytest.raises(ValueError, match="source records"):
            checker.verify(BACKEND, FRONTEND, SHA)
    else:
        checker.verify(BACKEND, FRONTEND, SHA)
    attempts = min(mismatch_count + 1, 3)
    assert calls.count(BACKEND + "/report/companies?skip=0&limit=50") == attempts
    assert calls.count(BACKEND + "/report/dashboard/stats") == attempts
    assert sleeps == [1] * (attempts - 1)
