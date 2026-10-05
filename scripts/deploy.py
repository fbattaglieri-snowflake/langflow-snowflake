"""Render bootstrap or deploy reviewed images; never load a default connection."""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENTIFIER = re.compile(r"[A-Z][A-Z0-9_]{0,127}\Z")
NAMES = ("user", "role", "database", "schema", "warehouse", "compute_pool",
         "image_repository", "stage", "service", "proxy_service", "encryption_secret", "login_secret")


def validate(config):
    allowed = set(json.loads((ROOT / "infrastructure/config.example.json").read_text()))
    if set(config) != allowed:
        raise ValueError("Configuration must contain exactly the example configuration keys")
    for name in NAMES:
        if not isinstance(config[name], str) or not IDENTIFIER.fullmatch(config[name]):
            raise ValueError(f"{name}: use an unquoted uppercase Snowflake identifier")
    if config["role"] in {"ACCOUNTADMIN", "SECURITYADMIN", "SYSADMIN", "PUBLIC"}:
        raise ValueError("Use a dedicated runtime role")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{2,200}", config["account"]):
        raise ValueError("Use an organization-account identifier")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,100}", config["image_tag"]):
        raise ValueError("Invalid image tag")
    if not re.fullmatch(r"CPU_[A-Z0-9_]+", config["instance_family"]):
        raise ValueError("Select an available CPU instance family")
    if type(config["volume_size_gib"]) is not int or not 20 <= config["volume_size_gib"] <= 16384:
        raise ValueError("Block volume size must be 20..16384 GiB")
    if type(config["a2a_enabled"]) is not bool:
        raise ValueError("a2a_enabled must be boolean")
    if config["pgvector_secret"] and not IDENTIFIER.fullmatch(config["pgvector_secret"]):
        raise ValueError("Invalid pgvector secret name")
    integrations = config["external_access_integrations"]
    if not isinstance(integrations, list) or any(not IDENTIFIER.fullmatch(item) for item in integrations):
        raise ValueError("Invalid external access integrations")
    if config["pgvector_secret"] and not integrations:
        raise ValueError("pgVector requires an explicit external access integration")
    sys.path.insert(0, str(ROOT / "proxy"))
    from server import ollama_base
    ollama_base(config["ollama_url"])
    if config["service"] == config["proxy_service"]:
        raise ValueError("Application and proxy must have different service names")
    for prefix in ("app", "proxy"):
        for resource in ("cpu", "memory"):
            suffix = "_gib" if resource == "memory" else ""
            request = config[f"{prefix}_{resource}_request{suffix}"]
            limit = config[f"{prefix}_{resource}_limit{suffix}"]
            if (type(request) not in (int, float) or type(limit) not in (int, float)
                    or not 0 < request <= limit <= 128):
                raise ValueError("Resource requests and limits must be positive and ordered")
    return config


def fqn(config, name):
    return f'{config["database"]}.{config["schema"]}.{config[name]}'


def bootstrap(config):
    role, database, schema = config["role"], config["database"], config["schema"]
    return f"""-- Review as an administrator; this file contains no credentials.
USE ROLE USERADMIN;
CREATE ROLE IF NOT EXISTS {role};
USE ROLE SYSADMIN;
CREATE DATABASE IF NOT EXISTS {database};
CREATE SCHEMA IF NOT EXISTS {database}.{schema};
CREATE WAREHOUSE IF NOT EXISTS {config['warehouse']} WAREHOUSE_SIZE=XSMALL AUTO_SUSPEND=60 INITIALLY_SUSPENDED=TRUE;
CREATE COMPUTE POOL IF NOT EXISTS {config['compute_pool']} MIN_NODES=1 MAX_NODES=1 INSTANCE_FAMILY={config['instance_family']} INITIALLY_SUSPENDED=TRUE AUTO_RESUME=TRUE;
CREATE IMAGE REPOSITORY IF NOT EXISTS {fqn(config, 'image_repository')};
CREATE STAGE IF NOT EXISTS {fqn(config, 'stage')} ENCRYPTION=(TYPE='SNOWFLAKE_SSE');
USE ROLE SECURITYADMIN;
GRANT USAGE ON DATABASE {database} TO ROLE {role};
GRANT USAGE ON SCHEMA {database}.{schema} TO ROLE {role};
GRANT CREATE SERVICE ON SCHEMA {database}.{schema} TO ROLE {role};
GRANT USAGE ON WAREHOUSE {config['warehouse']} TO ROLE {role};
GRANT USAGE ON COMPUTE POOL {config['compute_pool']} TO ROLE {role};
GRANT READ, WRITE ON IMAGE REPOSITORY {fqn(config, 'image_repository')} TO ROLE {role};
GRANT READ, WRITE ON STAGE {fqn(config, 'stage')} TO ROLE {role};
GRANT BIND SERVICE ENDPOINT ON ACCOUNT TO ROLE {role};
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_REST_API_USER TO ROLE {role};
GRANT ROLE {role} TO USER {config['user']};
-- Provision the encryption and login secrets separately; do not commit their values.
"""


def secret(config, key, field, env):
    return {"snowflakeSecret": fqn(config, key), "secretKeyRef": field, "envVarName": env}


def resources(config, prefix):
    return {plural: {"cpu": config[f"{prefix}_cpu_{singular}"],
                     "memory": f'{config[f"{prefix}_memory_{singular}_gib"]}Gi'}
            for plural, singular in (("requests", "request"), ("limits", "limit"))}


def specification(config, kind, proxy_dns=""):
    repo = f'/{config["database"]}/{config["schema"]}/{config["image_repository"]}'.lower()
    if kind == "proxy":
        return {"spec": {
            "containers": [{"name": "proxy", "image": f'{repo}/proxy:{config["image_tag"]}',
                            "env": {"MODEL_CATALOG": "/models/models.json", "OLLAMA_BASE_URL": config["ollama_url"]},
                            "volumeMounts": [{"name": "models", "mountPath": "/models"}],
                            "readinessProbe": {"port": 8080, "path": "/health"},
                            "resources": resources(config, "proxy")}],
            "endpoints": [{"name": "api", "port": 8080, "protocol": "TCP", "public": False}],
            "volumes": [{"name": "models", "source": "@" + fqn(config, "stage") + "/models",
                         "uid": 1000, "gid": 1000}]
        }}
    if not re.fullmatch(r"[a-z0-9.-]+\.svc\.spcs\.internal", proxy_dns):
        raise ValueError("Resolve the deployed proxy DNS before rendering the application")
    secrets = [secret(config, "encryption_secret", "secret_string", "LANGFLOW_SECRET_KEY"),
               secret(config, "login_secret", "username", "LANGFLOW_SUPERUSER"),
               secret(config, "login_secret", "password", "LANGFLOW_SUPERUSER_PASSWORD")]
    if config["pgvector_secret"]:
        secrets.append(secret(config, "pgvector_secret", "secret_string", "PGVECTOR_CONNECTION_STRING"))
    return {"spec": {
        "containers": [{"name": "langflow", "image": f'{repo}/langflow:{config["image_tag"]}',
                        "env": {"LANGFLOW_SSRF_ALLOWED_HOSTS": proxy_dns,
                                "LANGFLOW_A2A_ENABLED": str(config["a2a_enabled"]).lower(),
                                "LANGFLOW_LOG_LEVEL": "INFO"},
                        "secrets": secrets,
                        "volumeMounts": [{"name": "data", "mountPath": "/persist"}],
                        "readinessProbe": {"port": 7860, "path": "/health"},
                        "resources": resources(config, "app")}],
        "endpoints": [{"name": "ui", "port": 7860, "protocol": "HTTP", "public": True}],
        "volumes": [{"name": "data", "source": "block", "size": f'{config["volume_size_gib"]}Gi',
                     "blockConfig": {"snapshotOnDelete": True, "snapshotDeleteAfter": "7d"}}]
    }}


def connection_env(config):
    env = os.environ.copy()
    env.update({"SNOWFLAKE_ACCOUNT": config["account"], "SNOWFLAKE_USER": config["user"],
                "SNOWFLAKE_ROLE": config["role"], "SNOWFLAKE_DATABASE": config["database"],
                "SNOWFLAKE_SCHEMA": config["schema"], "SNOWFLAKE_WAREHOUSE": config["warehouse"]})
    return env


def snow(config, *args):
    command = ["snow", *args, "-x"]
    result = subprocess.run(command, env=connection_env(config), capture_output=True, text=True, check=False)
    if result.returncode:
        # Error messages can contain account metadata. Keep public CI logs minimal.
        raise RuntimeError(f"Snowflake CLI command failed (exit {result.returncode}); inspect securely")
    return result.stdout


def sql(config, statement):
    result = json.loads(snow(config, "sql", "--query", statement, "--format", "JSON", "--silent"))
    if not isinstance(result, list):
        raise ValueError("Unexpected CLI result shape")
    return [{str(key).lower(): value for key, value in row.items()} for row in result]


def wait_ready(config, name):
    for _ in range(60):
        rows = sql(config, f"SELECT SYSTEM$GET_SERVICE_STATUS('{name}') AS STATUS")
        states = json.loads(rows[0]["status"])
        if states and all(item.get("status") == "READY" for item in states):
            return
        if any(item.get("status") == "FAILED" for item in states):
            raise RuntimeError("Container failed; inspect private service logs")
        time.sleep(10)
    raise TimeoutError("Service readiness deadline exceeded")


def deploy_service(config, kind, spec, allow_create):
    name = fqn(config, "proxy_service" if kind == "proxy" else "service")
    found = sql(config, f"SHOW SERVICES IN SCHEMA {config['database']}.{config['schema']}")
    exists = any(row.get("name") == name.split(".")[-1] for row in found)
    if not exists and not allow_create:
        raise ValueError("Service absent; first deployment requires --allow-create")
    if exists:
        rows = sql(config, f"DESCRIBE SERVICE {name}")
        import yaml
        current = yaml.safe_load(rows[0]["spec"])
        if kind == "app":
            actual = current["spec"].get("volumes", [])
            expected = spec["spec"]["volumes"][0]
            volume = next((item for item in actual if item.get("name") == "data"), None)
            if not volume or volume.get("source") != "block" or volume.get("size") != expected["size"]:
                raise ValueError("Existing volume differs; refusing destructive or incompatible update")
            if config["external_access_integrations"]:
                sql(config, f"ALTER SERVICE {name} SET EXTERNAL_ACCESS_INTEGRATIONS=("
                    + ",".join(config["external_access_integrations"]) + ")")
        statement = f"ALTER SERVICE {name} FROM SPECIFICATION $$" + json.dumps(spec) + "$$"
    else:
        integrations = config["external_access_integrations"] if kind == "app" else []
        eai = " EXTERNAL_ACCESS_INTEGRATIONS=(" + ",".join(integrations) + ")" if integrations else ""
        statement = (f"CREATE SERVICE {name} IN COMPUTE POOL {config['compute_pool']} "
                     f"MIN_INSTANCES=1 MAX_INSTANCES=1 AUTO_RESUME=TRUE{eai} FROM SPECIFICATION $$"
                     + json.dumps(spec) + "$$")
    sql(config, statement)
    wait_ready(config, name)
    # Never remove integrations implicitly: removing one needs a reviewed operator change.
    return sql(config, f"DESCRIBE SERVICE {name}")[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["bootstrap", "render", "deploy", "registry"])
    parser.add_argument("--config", required=True)
    parser.add_argument("--catalog")
    parser.add_argument("--proxy-dns")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allow-create", action="store_true")
    args = parser.parse_args()
    config = validate(json.loads(Path(args.config).read_text()))
    if args.action == "bootstrap":
        print(bootstrap(config))
    elif args.action == "render":
        print(json.dumps({"proxy": specification(config, "proxy"),
                          "application": specification(config, "app", args.proxy_dns)}, indent=2))
    elif args.action == "registry":
        rows = sql(config, f"SHOW IMAGE REPOSITORIES IN SCHEMA {config['database']}.{config['schema']}")
        row = next(item for item in rows if item["name"] == config["image_repository"])
        print(row["repository_url"])
    else:
        if not args.apply or not args.catalog:
            parser.error("deploy requires --apply and --catalog; never deploy implicitly")
        sys.path.insert(0, str(ROOT / "proxy"))
        from server import load_catalog
        load_catalog(args.catalog)
        path = Path(args.catalog).resolve()
        if not re.fullmatch(r"[a-zA-Z0-9_./-]+", str(path)):
            raise ValueError("Catalog path must not contain whitespace or shell metacharacters")
        if path.name != "models.json":
            raise ValueError("Catalog filename must be models.json")
        snow(config, "stage", "copy", str(path), "@" + fqn(config, "stage") + "/models/", "--overwrite")
        proxy = deploy_service(config, "proxy", specification(config, "proxy"), args.allow_create)
        dns = proxy["dns_name"]
        deploy_service(config, "app", specification(config, "app", dns), args.allow_create)
        print("Services READY. Configure Langflow OpenAI Compatible base URL:")
        print(f"http://{dns}:8080/v1")
        endpoints = sql(config, f"SHOW ENDPOINTS IN SERVICE {fqn(config, 'service')}")
        print(json.dumps(endpoints))


if __name__ == "__main__":
    main()