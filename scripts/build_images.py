"""Build locally or publish immutable images only after full vulnerability gates."""
import argparse
import json
import re
import subprocess
from pathlib import Path

from deploy import ROOT, sql, validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    config = validate(json.loads(Path(args.config).read_text()))
    if args.publish and not re.fullmatch(r"[a-f0-9]{40}", config["image_tag"]):
        raise ValueError("Publishing requires a full Git commit SHA as image_tag")
    for name, dockerfile in (("langflow", "docker/langflow/Dockerfile"), ("proxy", "proxy/Dockerfile")):
        tag = f'langflow-kit-{name}:{config["image_tag"]}'
        subprocess.run(["docker", "build", "--platform", "linux/amd64", "-f", str(ROOT / dockerfile),
                        "-t", tag, str(ROOT)], check=True)
        subprocess.run(["trivy", "image", "--scanners", "vuln", "--severity", "HIGH,CRITICAL",
                        "--exit-code", "1", tag], check=True)
    if args.publish:
        rows = sql(config, f"SHOW IMAGE REPOSITORIES IN SCHEMA {config['database']}.{config['schema']}")
        url = next(row["repository_url"] for row in rows if row["name"] == config["image_repository"])
        if not re.fullmatch(r"[a-zA-Z0-9.-]+\.registry\.snowflakecomputing\.(com|cn)/[a-zA-Z0-9_/]+", url):
            raise ValueError("Unexpected image repository URL")
        # Registry login is explicit and performed outside this script; never print its token.
        for name in ("langflow", "proxy"):
            source = f'langflow-kit-{name}:{config["image_tag"]}'
            target = f'{url}/{name}:{config["image_tag"]}'
            subprocess.run(["docker", "tag", source, target], check=True)
            subprocess.run(["docker", "push", target], check=True)


if __name__ == "__main__":
    main()