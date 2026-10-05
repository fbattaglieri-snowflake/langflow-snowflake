"""Offline image smoke: actual login and SQLite state across a container restart."""
import argparse
import json
import secrets
import subprocess
import time
import uuid


def docker(*args):
    return subprocess.run(["docker", *args], check=True, capture_output=True, text=True).stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="langflow-public-app:test")
    args = parser.parse_args()
    identifier = "langflow-kit-smoke-" + uuid.uuid4().hex[:12]
    volume = identifier + "-data"
    password = secrets.token_urlsafe(32)
    key = secrets.token_urlsafe(48)
    docker("volume", "create", volume)
    try:
        for index in range(2):
            docker("run", "-d", "--name", identifier, "--network", "none", "--platform", "linux/amd64",
                   "-v", volume + ":/persist", "-e", "LANGFLOW_SUPERUSER=synthetic-admin",
                   "-e", "LANGFLOW_SUPERUSER_PASSWORD=" + password, "-e", "LANGFLOW_SECRET_KEY=" + key,
                   args.image)
            try:
                for _ in range(90):
                    result = subprocess.run(["docker", "exec", identifier, "/app/.venv/bin/python", "-c",
                        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/health',timeout=3)"],
                        capture_output=True, timeout=10)
                    if result.returncode == 0:
                        break
                    time.sleep(3)
                else:
                    raise TimeoutError("Offline Langflow readiness failed")
                code = (
                    "import os,json,urllib.request,urllib.parse,sqlite3; "
                    "data=urllib.parse.urlencode({'username':os.environ['LANGFLOW_SUPERUSER'],"
                    "'password':os.environ['LANGFLOW_SUPERUSER_PASSWORD']}).encode(); "
                    "response=json.load(urllib.request.urlopen(urllib.request.Request("
                    "'http://127.0.0.1:7860/api/v1/login',data=data),timeout=10)); "
                    "assert response.get('access_token'); "
                    "db=sqlite3.connect('/persist/langflow.db'); "
                    "assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'; "
                    "print(json.dumps({'login':True,'integrity':'ok','tables':"
                    "db.execute(\"SELECT COUNT(*) FROM sqlite_master WHERE type='table'\").fetchone()[0]}))"
                )
                result = json.loads(docker("exec", identifier, "/app/.venv/bin/python", "-c", code))
                if index == 0:
                    docker("exec", identifier, "/app/.venv/bin/python", "-c",
                           "from pathlib import Path; Path('/persist/storage/synthetic-marker').write_text('persisted')")
                else:
                    docker("exec", identifier, "/app/.venv/bin/python", "-c",
                           "from pathlib import Path; assert Path('/persist/storage/synthetic-marker').read_text()=='persisted'")
                print(json.dumps({"boot": index + 1, **result}), flush=True)
            finally:
                docker("rm", "-f", identifier)
    finally:
        docker("volume", "rm", volume)


if __name__ == "__main__":
    main()