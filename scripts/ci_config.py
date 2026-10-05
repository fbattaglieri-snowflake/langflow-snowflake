"""Validate GitHub environment variables without shell interpolation or secrets."""
import json
import os
import re
import sys
from pathlib import Path

from deploy import ROOT, validate


def main():
    config = json.loads(os.environ["DEPLOY_CONFIG_JSON"])
    config["image_tag"] = os.environ["IMAGE_TAG"]
    if not re.fullmatch(r"[a-f0-9]{40}", config["image_tag"]):
        raise ValueError("IMAGE_TAG must be a full commit SHA")
    validate(config)
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    (build / "config.json").write_text(json.dumps(config))
    (build / "models.json").write_text(os.environ["MODEL_CATALOG_JSON"])
    sys.path.insert(0, str(ROOT / "proxy"))
    from server import load_catalog
    load_catalog(build / "models.json")
    with Path(os.environ["GITHUB_ENV"]).open("a") as output:
        for key in ("account", "user", "role", "database", "schema", "warehouse"):
            output.write(f"SNOWFLAKE_{key.upper()}={config[key]}\n")


if __name__ == "__main__":
    main()