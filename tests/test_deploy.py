import copy
import json
from unittest.mock import patch

import pytest

from deploy import ROOT, bootstrap, deploy_service, specification, validate


@pytest.fixture
def config():
    return json.loads((ROOT / "infrastructure/config.example.json").read_text())


@pytest.mark.parametrize("database,schema,account", [
    ("APP_A", "DEV", "EXAMPLE-ACCOUNT_A"), ("APP_B", "PROD", "EXAMPLE-ACCOUNT_B"),
])
def test_portable_render(config, database, schema, account):
    config.update(database=database, schema=schema, account=account)
    validate(config)
    assert f"CREATE DATABASE IF NOT EXISTS {database}" in bootstrap(config)
    app = specification(config, "app", "proxy.synthetic.svc.spcs.internal")
    container = app["spec"]["containers"][0]
    assert container["image"].startswith(f"/{database}/{schema}/".lower())
    assert container["secrets"][0]["snowflakeSecret"].startswith(f"{database}.{schema}.")
    assert app["spec"]["volumes"][0]["source"] == "block"
    assert specification(config, "proxy")["spec"]["endpoints"][0]["public"] is False


@pytest.mark.parametrize("field,value", [
    ("database", "DB; DROP DATABASE X"), ("schema", "bad/name"),
    ("role", "ACCOUNTADMIN"), ("image_tag", "$(command)"),
    ("account", "x\ny"), ("volume_size_gib", True),
    ("a2a_enabled", "false"), ("ollama_url", "https://example.com"),
    ("pgvector_secret", "invalid.name"),
])
def test_invalid_settings_rejected(config, field, value):
    config[field] = value
    with pytest.raises(ValueError):
        validate(config)


def test_pgvector_optional(config):
    app = specification(config, "app", "proxy.synthetic.svc.spcs.internal")
    assert len(app["spec"]["containers"][0]["secrets"]) == 3
    config.update(pgvector_secret="VECTOR_URL", external_access_integrations=["VECTOR_EAI"])
    validate(config)
    assert len(specification(config, "app", "proxy.synthetic.svc.spcs.internal")["spec"]["containers"][0]["secrets"]) == 4


def test_first_create_requires_permission(config):
    with patch("deploy.sql", return_value=[]), pytest.raises(ValueError, match="allow-create"):
        deploy_service(config, "proxy", specification(config, "proxy"), False)


def test_upgrade_preserves_service(config):
    spec = specification(config, "app", "proxy.synthetic.svc.spcs.internal")
    rows = [[{"name": config["service"]}], [{"spec": json.dumps(spec)}], [], [{"dns_name": "test"}]]
    with patch("deploy.sql", side_effect=rows) as query, patch("deploy.wait_ready"):
        deploy_service(config, "app", spec, False)
    statements = [call.args[1] for call in query.call_args_list]
    assert any(statement.startswith("ALTER SERVICE") for statement in statements)
    assert all("DROP" not in statement and "CREATE SERVICE" not in statement for statement in statements)


def test_volume_resize_rejected(config):
    spec = specification(config, "app", "proxy.synthetic.svc.spcs.internal")
    old = copy.deepcopy(spec)
    old["spec"]["volumes"][0]["size"] = "40Gi"
    with patch("deploy.sql", side_effect=[[{"name": config["service"]}], [{"spec": json.dumps(old)}]]):
        with pytest.raises(ValueError, match="volume"):
            deploy_service(config, "app", spec, False)