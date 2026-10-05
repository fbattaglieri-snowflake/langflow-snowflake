import io
import json
import threading
import urllib.error
import urllib.request
from unittest.mock import Mock

import pytest

from server import NoRedirect, load_catalog, make_server, normalize, ollama_base, prepare, snowflake_host


MODELS = {
    "test-cortex": {"backend": "cortex", "tools": True, "rename_max_tokens": True},
    "test-ollama": {"backend": "ollama", "tools": True},
}


def body(model="test-cortex"):
    return {"model": model, "messages": [{"role": "user", "content": "Synthetic test"}], "max_tokens": 20}


def test_cortex_only_rewrite():
    source = body()
    result, _ = prepare(source, MODELS)
    assert result["max_completion_tokens"] == 20 and "max_tokens" not in result
    assert "max_tokens" in source
    result, _ = prepare(body("test-ollama"), MODELS)
    assert result["max_tokens"] == 20


def test_preserve_parallel_tool_history():
    request = body()
    request["messages"].append({"role": "assistant", "tool_calls": [{"id": "first"}, {"id": "second"}]})
    result, _ = prepare(request, MODELS)
    assert result["messages"] == request["messages"]


@pytest.mark.parametrize("update", [{"stream": True}, {"model": "unknown"}, {"messages": []}])
def test_fail_closed(update):
    request = body()
    request.update(update)
    with pytest.raises(ValueError):
        prepare(request, MODELS)


def test_undeclared_tools():
    request = body()
    request["tools"] = [{"type": "function"}]
    with pytest.raises(ValueError):
        prepare(request, {"test-cortex": {"backend": "cortex"}})


def test_catalog_rejects_placeholder_and_unknown_backend(tmp_path):
    path = tmp_path / "models.json"
    for entry in [{"id": "REPLACE_MODEL", "backend": "cortex"}, {"id": "valid", "backend": "unknown"}]:
        path.write_text(json.dumps({"models": [entry]}))
        with pytest.raises(ValueError):
            load_catalog(path)


def test_host_guards():
    assert snowflake_host("example-account.snowflakecomputing.com")
    for value in ["https://example.com", "example.com", "a.snowflakecomputing.com/evil", "user@a.snowflakecomputing.com"]:
        with pytest.raises(ValueError):
            snowflake_host(value)
    with pytest.raises(ValueError):
        ollama_base("http://name:password@model.synthetic.svc.spcs.internal")


def test_upstream_redirects_are_not_followed():
    assert NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://example.com") is None


def test_normalization_is_opt_in_and_cortex_only():
    for backend, enabled, expected in [("cortex", True, "tool_calls"), ("cortex", False, ""), ("ollama", True, "")]:
        result = {"choices": [{"message": {"tool_calls": [{"id": "first"}]}, "finish_reason": ""}]}
        assert normalize(result, {"backend": backend, "normalize_finish_reason": enabled}, 20)["choices"][0]["finish_reason"] == expected


@pytest.fixture
def running(tmp_path):
    token = tmp_path / "session-token"
    token.write_text("synthetic-one")
    server = make_server(("127.0.0.1", 0), MODELS, "example-account.snowflakecomputing.com",
                         "http://model.synthetic.svc.spcs.internal:11434", str(token))
    server.opener = Mock()
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    yield server, token, f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join()


def response():
    return io.BytesIO(json.dumps({"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}).encode())


def post(url, request):
    with urllib.request.urlopen(urllib.request.Request(url + "/v1/chat/completions", data=json.dumps(request).encode()), timeout=5) as result:
        return json.load(result)


def test_oauth_rotation_and_ollama_no_token(running):
    server, token, url = running
    server.opener.open.side_effect = lambda *args, **kwargs: response()
    post(url, body())
    assert server.opener.open.call_args.args[0].get_header("Authorization") == "Bearer synthetic-one"
    token.write_text("synthetic-two")
    post(url, body())
    assert server.opener.open.call_args.args[0].get_header("Authorization") == "Bearer synthetic-two"
    post(url, body("test-ollama"))
    assert server.opener.open.call_args.args[0].get_header("Authorization") is None


def test_no_sql_route(running):
    server, _, url = running
    with pytest.raises(urllib.error.HTTPError) as failure:
        urllib.request.urlopen(urllib.request.Request(url + "/api/v2/statements", data=b"{}"))
    assert failure.value.code == 404
    server.opener.open.assert_not_called()


def test_upstream_error_redacted_and_not_retried(running):
    server, _, url = running
    server.opener.open.side_effect = urllib.error.HTTPError("hidden-url", 401, "hidden-detail", {}, io.BytesIO(b"private"))
    with pytest.raises(urllib.error.HTTPError) as failure:
        post(url, body())
    assert failure.value.code == 502
    raw = failure.value.read()
    assert b"private" not in raw and b"hidden" not in raw
    assert server.opener.open.call_count == 1