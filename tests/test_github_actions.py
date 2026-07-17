from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def test_github_actions_runs_tests_builds_container_and_publishes_ghcr() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "pull_request:",
        "push:",
        "python -m pytest -v",
        "python demo/mock_repair_demo.py",
        "docker build",
        "curl --fail",
        "packages: write",
        "ghcr.io/${{ github.repository_owner }}/fr-harness",
        "docker/login-action",
        "docker/build-push-action",
    ):
        assert required in workflow


def test_image_publish_only_runs_for_main_after_verification() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "github.ref == 'refs/heads/main'" in workflow
    assert "needs: [unit-test, docker-build]" in workflow
    assert "password: ${{ secrets.GITHUB_TOKEN }}" in workflow
    assert "OPENAI_API_KEY=ci-placeholder" in workflow
    assert "grep -F \"ci-placeholder\"" in workflow


def test_dockerfile_links_image_to_public_source_repository() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert (
        'org.opencontainers.image.source="https://github.com/RippleOrApple/FR-Harness"'
        in dockerfile
    )
