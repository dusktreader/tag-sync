"""Fixtures and shared step definitions for BDD integration tests.

Fixture design
--------------
session-scoped:
  tag_sync_bin  -- path to the tag-sync executable installed in a dedicated
                   venv (created once for the whole test session via uv).

function-scoped (one fresh pair per scenario):
  upstream_repo -- a non-bare git repo in tmp_path/upstream with a
                   pyproject.toml and an initial commit.  Acts as the
                   authoritative remote origin.
  local_repo    -- a `git clone` of upstream into tmp_path/local.  This is
                   where the CLI runs from (passed as cwd= to subprocess).

No monkeypatching.  No CliRunner.  The CLI is invoked as a real subprocess
with cwd set to the local clone, exactly as a user would run it.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
from git import Repo
from pytest_bdd import given, parsers, then


# ---------------------------------------------------------------------------
# Result wrapper
# ---------------------------------------------------------------------------


@dataclass
class CLIResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        """Combined stdout + stderr for convenience in assertions."""
        return self.stdout + self.stderr


# ---------------------------------------------------------------------------
# Session-scoped: install tag-sync into a dedicated venv once
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def tag_sync_bin(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """
    Install tag-sync into a throwaway venv and return the path to its binary.

    Created once per test session so all integration tests share the same
    installation without repeated installs.  Uses uv to create the venv
    since the project uses a uv-managed Python that does not support ensurepip.
    """
    venv_dir = tmp_path_factory.mktemp("tag-sync-venv", numbered=False)
    project_root = Path(__file__).parents[2]  # tests/features/ -> project root
    subprocess.run(["uv", "venv", str(venv_dir)], check=True, capture_output=True)
    subprocess.run(
        ["uv", "pip", "install", "-e", str(project_root), "--python", str(venv_dir / "bin" / "python")],
        check=True,
        capture_output=True,
    )
    return venv_dir / "bin" / "tag-sync"


# ---------------------------------------------------------------------------
# Function-scoped: upstream repo (acts as origin)
# ---------------------------------------------------------------------------


@pytest.fixture
def upstream_repo(tmp_path: Path) -> Repo:
    """
    A non-bare git repo in tmp_path/upstream.

    Contains a minimal pyproject.toml (version = "0.1.0") and an initial
    commit.  The local_repo fixture clones from this.
    """
    upstream_path = tmp_path / "upstream"
    upstream_path.mkdir()
    repo = Repo.init(upstream_path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()

    (upstream_path / "pyproject.toml").write_text('[project]\nname = "test-project"\nversion = "0.1.0"\n')
    repo.index.add(["pyproject.toml"])
    repo.index.commit("Initial commit")
    return repo


# ---------------------------------------------------------------------------
# Function-scoped: local clone (where the CLI runs)
# ---------------------------------------------------------------------------


@pytest.fixture
def local_repo(tmp_path: Path, upstream_repo: Repo) -> Repo:
    """
    A git clone of upstream_repo into tmp_path/local.

    The CLI is invoked with cwd=local_repo.working_dir so that
    Repo(search_parent_directories=True) and Path("pyproject.toml") both
    resolve inside this clone.
    """
    local_path = tmp_path / "local"
    repo = upstream_repo.clone(str(local_path))
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    return repo


# ---------------------------------------------------------------------------
# Helper fixture: set pyproject.toml version in the local clone
# ---------------------------------------------------------------------------


@pytest.fixture
def set_project_version(local_repo: Repo):
    """
    Return a callable that rewrites pyproject.toml in the local clone with
    the given version string and commits the change.
    """

    def _set(version: str) -> None:
        repo_path = Path(local_repo.working_dir)
        pyproject = repo_path / "pyproject.toml"
        pyproject.write_text(f'[project]\nname = "test-project"\nversion = "{version}"\n')
        local_repo.index.add(["pyproject.toml"])
        local_repo.index.commit(f"Bump version to {version}")

    return _set


@pytest.fixture
def set_npm_version(local_repo: Repo):
    """
    Return a callable that writes a package.json in the local clone with
    the given version string and commits the change.
    """

    def _set(version: str) -> None:
        repo_path = Path(local_repo.working_dir)
        package_json = repo_path / "package.json"
        package_json.write_text(f'{{"name": "test-project", "version": "{version}"}}\n')
        local_repo.index.add(["package.json"])
        local_repo.index.commit(f"Bump version to {version}")

    return _set


# ---------------------------------------------------------------------------
# Helper: run tag-sync as a real subprocess inside the local clone
# ---------------------------------------------------------------------------


@pytest.fixture
def run_tag_sync(tag_sync_bin: Path, local_repo: Repo):
    """
    Return a callable that invokes tag-sync with the given args as a
    subprocess inside the local clone directory.

    Returns a CLIResult with returncode, stdout, and stderr.
    """
    cwd = local_repo.working_dir

    def _run(*args: str, input: str | None = None) -> CLIResult:
        result = subprocess.run(
            [str(tag_sync_bin), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            input=input,
        )
        return CLIResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    return _run


# ---------------------------------------------------------------------------
# BDD shared state
# ---------------------------------------------------------------------------


@pytest.fixture
def bdd_context() -> dict:
    """Mutable dict shared across all steps in a single scenario."""
    return {}


# ---------------------------------------------------------------------------
# Shared Given steps
# ---------------------------------------------------------------------------


@given(parsers.parse('a git repository with version "{version}" in pyproject.toml'))
def repo_with_version(version: str, set_project_version) -> None:
    set_project_version(version)


@given(parsers.parse('a git repository with version "{version}" in package.json'))
def repo_with_npm_version(version: str, set_npm_version, local_repo: Repo) -> None:
    pyproject = Path(local_repo.working_dir) / "pyproject.toml"
    if pyproject.exists():
        pyproject.unlink()
        local_repo.index.remove(["pyproject.toml"])
        local_repo.index.commit("Remove pyproject.toml")
    set_npm_version(version)


@given(parsers.parse('the tag "{tag}" exists on the upstream'))
def tag_exists_on_upstream(tag: str, upstream_repo: Repo, local_repo: Repo) -> None:
    upstream_repo.create_tag(tag)
    local_repo.remotes["origin"].fetch()


@given(parsers.parse('the tag "{tag}" exists locally'))
def tag_exists_locally(tag: str, local_repo: Repo) -> None:
    local_repo.create_tag(tag)


@given(parsers.parse('the tag "{tag}" exists locally and on the upstream'))
def tag_exists_locally_and_upstream(tag: str, upstream_repo: Repo, local_repo: Repo) -> None:
    local_repo.create_tag(tag)
    local_repo.remotes["origin"].push(tag)


@given("no tags exist on the upstream")
def no_tags_on_upstream() -> None:
    pass  # fresh repos have no tags by default


# ---------------------------------------------------------------------------
# Shared Then steps
# ---------------------------------------------------------------------------


@then("the command succeeds")
def command_succeeds(bdd_context: dict) -> None:
    result = bdd_context["result"]
    assert result.returncode == 0, (
        f"Expected exit code 0, got {result.returncode}.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


@then("the command fails")
def command_fails(bdd_context: dict) -> None:
    result = bdd_context["result"]
    assert result.returncode != 0, (
        f"Expected non-zero exit code, got {result.returncode}.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


@then(parsers.parse('the output contains "{text}"'))
def output_contains(text: str, bdd_context: dict) -> None:
    result = bdd_context["result"]
    assert text in result.output, f"Expected {text!r} in output.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"


@then(parsers.parse('the tag "{tag}" exists locally'))
def assert_tag_exists_locally(tag: str, local_repo: Repo) -> None:
    local_repo.git.fetch("--tags")
    names = [t.name for t in local_repo.tags]
    assert tag in names, f"Expected tag {tag!r} locally. Found: {names}"


@then(parsers.parse('the tag "{tag}" does not exist locally'))
def assert_tag_not_exists_locally(tag: str, local_repo: Repo) -> None:
    local_repo.git.fetch("--tags")
    names = [t.name for t in local_repo.tags]
    assert tag not in names, f"Expected tag {tag!r} to NOT exist locally. Found: {names}"


@then(parsers.parse('the tag "{tag}" exists on the upstream'))
def assert_tag_exists_on_upstream(tag: str, upstream_repo: Repo) -> None:
    names = [t.name for t in upstream_repo.tags]
    assert tag in names, f"Expected tag {tag!r} on upstream. Found: {names}"


@then(parsers.parse('the tag "{tag}" does not exist on the upstream'))
def assert_tag_not_exists_on_upstream(tag: str, upstream_repo: Repo) -> None:
    names = [t.name for t in upstream_repo.tags]
    assert tag not in names, f"Expected tag {tag!r} to NOT exist on upstream. Found: {names}"
