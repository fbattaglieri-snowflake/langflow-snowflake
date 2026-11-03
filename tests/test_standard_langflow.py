from unittest.mock import patch

import pytest

import standard_langflow as runtime


def test_refresh_tracks_changes_without_replacement():
    config = {"model_id": {"value": "removed", "options": ["old"]}}
    with patch.object(runtime, "catalog", return_value=["new"]):
        assert runtime.refresh(config, "chat")["model_id"]["options"] == ["new"]
        assert config["model_id"]["value"] == "removed"
    with patch.object(runtime, "catalog", side_effect=RuntimeError()):
        with pytest.raises(ValueError, match="DISCOVERY_UNAVAILABLE"):
            runtime.refresh(config, "chat")
        assert config["model_id"]["options"] == []


def test_resolve_reasoning_options_across_protocols():
    chat_luna = runtime.resolve_reasoning_options("chat", "openai-gpt-6-luna")
    assert chat_luna == {"max_tokens": 2048, "extra_body": {"reasoning_effort": "none"}}

    chat_grok = runtime.resolve_reasoning_options("chat", "grok-4.7", reasoning="high")
    assert chat_grok == {"max_tokens": 2048, "extra_body": None}

    resp_terra = runtime.resolve_reasoning_options("responses", "openai-gpt-6.1-terra", reasoning_effort="low")
    assert resp_terra["store"] is False
    assert resp_terra["include"] == ["reasoning.encrypted_content"]
    assert resp_terra["output_version"] == "responses/v1"
    assert resp_terra["extra_body"] == {"reasoning": {"effort": "low", "summary": "auto"}}

    msg_think = runtime.resolve_reasoning_options(
        "messages", "claude-sonnet-5-5", max_tokens=1024, extended_thinking="enabled", thinking_budget_tokens=2048
    )
    assert msg_think == {
        "max_tokens": 3072,
        "thinking": {"type": "enabled", "budget_tokens": 2048},
    }


def test_validation_guards():
    with patch.object(runtime, "catalog", return_value=[]):
        with pytest.raises(ValueError, match="SELECTED_MODEL_UNAVAILABLE"):
            runtime.build("chat", "revoked")
    with pytest.raises(ValueError, match="STREAM_BOOLEAN_REQUIRED"):
        runtime.build("responses", "fixture", stream="yes")
    with pytest.raises(ValueError, match="TOKEN_LIMIT_OUT_OF_RANGE"):
        runtime.build("chat", "fixture", max_tokens=200000)


def test_build_models_for_all_protocols():
    fake_clients = lambda _url: {  # noqa: E731
        "http_client": runtime._DummyHttpClient() if hasattr(runtime, "_DummyHttpClient") else object(),
        "http_async_client": runtime._DummyHttpClient() if hasattr(runtime, "_DummyHttpClient") else object(),
    }
    for proto, model_id in [
        ("chat", "openai-gpt-6-luna"),
        ("responses", "openai-gpt-6.1-terra"),
        ("messages", "claude-sonnet-5-5"),
        ("ollama", "muse-glimmer:latest"),
    ]:
        with (
            patch.object(runtime, "catalog", return_value=[model_id]),
            patch.object(runtime, "provider_httpx_clients", side_effect=fake_clients),
            patch.object(runtime, "close_clients"),
        ):
            built = runtime.build(proto, model_id)
            assert built.model == model_id
            assert built.max_retries == 0
            assert built.base_url == runtime.BASES[proto]
