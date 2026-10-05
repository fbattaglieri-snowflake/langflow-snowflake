"""Private, explicit-catalog Chat Completions adapter. No SQL or arbitrary URLs."""
import copy
import json
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_BODY = 2 * 1024 * 1024
MAX_RESPONSE = 16 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def snowflake_host(value):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]*\.snowflakecomputing\.(?:com|cn)", value):
        raise ValueError("SNOWFLAKE_HOST must be an account hostname, not a URL")
    return value


def ollama_base(value):
    if not value:
        return ""
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme != "http" or not parsed.hostname
            or not parsed.hostname.endswith(".svc.spcs.internal")
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/")):
        raise ValueError("Ollama must use an explicit private SPCS HTTP endpoint")
    return value.rstrip("/")


def load_catalog(path):
    data = json.loads(Path(path).read_text())
    entries = data.get("models")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Configure at least one explicitly verified chat model")
    models = {}
    for entry in entries:
        name = entry.get("id")
        if (not isinstance(name, str) or not name or len(name) > 200
                or "REPLACE_" in name or name in models):
            raise ValueError("Invalid, placeholder or duplicate model ID")
        if entry.get("backend") not in ("cortex", "ollama"):
            raise ValueError("Unsupported backend")
        for key in ("tools", "rename_max_tokens", "normalize_finish_reason"):
            if key in entry and type(entry[key]) is not bool:
                raise ValueError("Catalog capability flags must be booleans")
        models[name] = entry
    return models


def prepare(body, models):
    if not isinstance(body, dict) or body.get("model") not in models:
        raise ValueError("Select a configured model")
    if body.get("stream"):
        raise ValueError("Streaming is not supported by this adapter; set stream=false")
    entry = models[body["model"]]
    if body.get("tools") and not entry.get("tools", False):
        raise ValueError("Tool calling has not been enabled for this model")
    if not isinstance(body.get("messages"), list) or not body["messages"]:
        raise ValueError("A non-empty messages array is required")
    payload = copy.deepcopy(body)
    if entry["backend"] == "cortex" and entry.get("rename_max_tokens", False):
        if "max_tokens" in payload:
            payload.setdefault("max_completion_tokens", payload.pop("max_tokens"))
    # Preserve all tool calls and results. Never collapse history or change model.
    return payload, entry


def normalize(result, entry, requested_max):
    if entry["backend"] != "cortex" or not entry.get("normalize_finish_reason", False):
        return result
    for choice in result.get("choices", []):
        if not choice.get("finish_reason"):
            if choice.get("message", {}).get("tool_calls"):
                choice["finish_reason"] = "tool_calls"
            elif requested_max and result.get("usage", {}).get("completion_tokens", 0) >= requested_max:
                choice["finish_reason"] = "length"
            else:
                choice["finish_reason"] = "stop"
    return result


class Handler(BaseHTTPRequestHandler):
    # Close each request. The adapter deliberately does not expose streaming.
    protocol_version = "HTTP/1.0"

    def log_message(self, *args):
        pass

    def reply(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if self.path == "/health":
            self.reply(200, {"status": "ok"})
        elif self.path == "/v1/models":
            self.reply(200, {"object": "list", "data": [
                {"id": name, "object": "model", "created": 0, "owned_by": entry["backend"]}
                for name, entry in self.server.models.items()
            ]})
        else:
            self.reply(404, {"error": "Route not available"})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.reply(404, {"error": "Only Chat Completions is exposed"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY or self.headers.get("Transfer-Encoding"):
                raise ValueError("Invalid body length")
            self.connection.settimeout(30)
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("Incomplete request")
            payload, entry = prepare(json.loads(raw), self.server.models)
        except (ValueError, TypeError, socket.timeout):
            self.reply(400, {"error": "Invalid request or unsupported model/capability; see configuration"})
            return
        try:
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            if entry["backend"] == "cortex":
                # Read again for every request so SPCS rotation is respected.
                token = Path(self.server.token_path).read_text().strip()
                if not token:
                    raise ValueError("Empty service token")
                headers.update({"Authorization": "Bearer " + token,
                                "X-Snowflake-Authorization-Token-Type": "OAUTH"})
                url = "https://" + self.server.sf_host + "/api/v2/cortex/v1/chat/completions"
            else:
                if not self.server.ollama:
                    raise ValueError("Ollama endpoint not configured")
                url = self.server.ollama + "/v1/chat/completions"
            req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
            with self.server.opener.open(req, timeout=120) as response:
                raw = response.read(MAX_RESPONSE + 1)
                if len(raw) > MAX_RESPONSE:
                    raise ValueError("Response too large")
                result = json.loads(raw)
            if not isinstance(result, dict) or not isinstance(result.get("choices"), list):
                raise ValueError("Invalid upstream response")
            self.reply(200, normalize(result, entry, payload.get("max_completion_tokens")))
        except urllib.error.HTTPError as exc:
            # Never return upstream bodies, prompts, headers, credentials or URLs.
            self.reply(502, {"error": "Upstream rejected request", "upstream_status": exc.code})
        except Exception:
            self.reply(502, {"error": "Upstream request failed; check service configuration"})


def make_server(address, models, host, ollama="", token_path="/snowflake/session/token"):
    server = ThreadingHTTPServer(address, Handler)
    server.models = models
    server.sf_host = snowflake_host(host)
    server.ollama = ollama_base(ollama)
    server.token_path = token_path
    server.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect)
    return server


if __name__ == "__main__":
    configured = load_catalog(os.environ.get("MODEL_CATALOG", "/models/models.json"))
    make_server(("0.0.0.0", 8080), configured, os.environ["SNOWFLAKE_HOST"],
                os.environ.get("OLLAMA_BASE_URL", "")).serve_forever()