import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_action_refs_are_immutable():
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        workflow = yaml.safe_load(path.read_text())
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                if "uses" in step:
                    assert re.fullmatch(r"[^@]+@[a-f0-9]{40}", step["uses"])


def test_no_deployment_on_push():
    text = (ROOT / ".github/workflows/deploy.yml").read_text()
    # BaseLoader preserves the YAML 1.2 'on' key as a string.
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["jobs"]["deploy"]["environment"] == "production"


def test_security_gates_do_not_exclude_unfixed_or_upstream():
    for name in ("ci.yml", "deploy.yml"):
        content = (ROOT / ".github/workflows" / name).read_text()
        assert "continue-on-error" not in content
        assert "ignore-unfixed" not in content
        assert "skip-dirs" not in content


def test_markdown_local_links_resolve():
    for path in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]:
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if not target.startswith(("http:", "https:", "#")):
                assert (path.parent / target.split("#")[0]).exists(), (path.name, target)