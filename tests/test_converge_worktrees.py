import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "automation" / "converge_worktrees.sh"
GUARD_ARGS = ["--assert-no-lanes", "--assert-no-lane-artifacts"]


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True)


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT), "--repo", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _init_repo(tmp_path: Path) -> Path:
    main = tmp_path / "main"
    main.mkdir()
    _git(main, "init", "-q", "-b", "main")
    _git(main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init")
    return main.resolve()


def _add_worktree(main: Path, path: Path, branch: str) -> Path:
    _git(main, "worktree", "add", "-q", "-b", branch, str(path))
    return path.resolve()


def test_guard_passes_from_linked_worktree_without_other_lanes(tmp_path: Path) -> None:
    main = _init_repo(tmp_path)
    self_wt = _add_worktree(main, tmp_path / "self", "fix/self")
    # The invoking worktree's own heavy artifacts are not lane artifacts.
    (self_wt / "frontend" / "node_modules").mkdir(parents=True)

    result = _run(self_wt, *GUARD_ARGS)

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"repo: {main}" in result.stdout
    assert "not a git repository" not in result.stderr


def test_guard_from_linked_worktree_still_flags_other_lanes(tmp_path: Path) -> None:
    main = _init_repo(tmp_path)
    self_wt = _add_worktree(main, tmp_path / "self", "fix/self")
    other = _add_worktree(main, tmp_path / "other", "lane/other")

    result = _run(self_wt, "--assert-no-lanes")

    assert result.returncode == 1
    assert f"lane: {other}" in result.stderr
    assert f"lane: {self_wt}" not in result.stderr


def test_guard_from_main_repo_flags_lane(tmp_path: Path) -> None:
    main = _init_repo(tmp_path)
    lane = _add_worktree(main, tmp_path / "lane", "lane/a")

    result = _run(main, "--assert-no-lanes")

    assert result.returncode == 1
    assert f"lane: {lane}" in result.stderr


def test_guard_reports_lane_artifact_size(tmp_path: Path) -> None:
    main = _init_repo(tmp_path)
    lane = _add_worktree(main, tmp_path / "lane", "lane/a")
    dist = lane / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "blob").write_bytes(b"\0" * 2 * 1024 * 1024)

    result = _run(main, "--assert-no-lane-artifacts")

    assert result.returncode == 1
    assert "heavy artifacts (2.0MB)" in result.stderr
    assert "syntax error" not in result.stderr


def test_non_git_path_is_rejected(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()

    result = _run(plain, *GUARD_ARGS)

    assert result.returncode == 1
    assert "repo path is not a git repository" in result.stderr
