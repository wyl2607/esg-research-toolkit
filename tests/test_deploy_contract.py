from __future__ import annotations

from pathlib import Path


def test_deploy_smoke_checks_public_routes_and_dashboard_shape() -> None:
    script = Path("scripts/deploy.sh").read_text(encoding="utf-8")

    assert "/report/dashboard/stats" in script
    assert "verify_dashboard_stats.py" in script
    # This route is admin-protected and must never be called as an unauthenticated smoke check.
    assert "/disclosures/pending" not in script


def test_deploy_workflow_can_verify_public_dashboard() -> None:
    workflow = Path(".github/workflows/deploy.yml").read_text(encoding="utf-8")

    assert "public_dashboard_url:" in workflow
    assert "verify_dashboard_stats.py" in workflow
    assert 'git fetch --depth=1 origin main "$GITHUB_SHA"' in workflow
