#!/usr/bin/env python3
"""
Amini LLM CLI — thin wrapper around the AminiLLM gateway (LiteLLM, OpenAI-compatible).

Reads configuration from the environment; no credentials are stored in this file.

    AMINI_LLM_BASE_URL   default http://10.10.20.4:4000/v1
    AMINI_LLM_API_KEY    required (LiteLLM virtual key)

Usage:
    python3 amini_llm_cli.py <command> [args...]

Commands:
    models                              List served model aliases
    health                              Per-model upstream health (needs key)
    doctor                              Full triage: network, auth, every alias
    chat <prompt>                       Text chat (chat-v1)
    think <prompt>                      Reasoning variant (chat-think-v1)
    vision <prompt> --image <path|url>  Multimodal (repeatable --image)
    ocr --image <path>                  Verbatim text transcription
    embed <text> [<text>...]            Embeddings (4096 dims)

Options:
    --model <alias>      Override the alias for chat/think/vision/ocr/embed
    --max-tokens <n>     Output budget (defaults per command)
    --system <text>      System prompt
    --stream             Stream tokens to stdout as they arrive
    --json               Force a JSON object response
    --temperature <f>    Sampling temperature
    --raw                Print the full JSON response instead of just content
"""

import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "http://10.10.20.4:4000/v1"
TIMEOUT = 300

MODELS = {
    "chat": "chat-v1",
    "think": "chat-think-v1",
    "vision": "vision-v1",
    "ocr": "ocr-v1",
    "embed": "embed-v1",
}
CONTEXT = {
    "chat-v1": 262144,
    "chat-think-v1": 262144,
    "vision-v1": 131072,
    "ocr-v1": 16384,
    "embed-v1": 2048,
}


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def base_url():
    return os.environ.get("AMINI_LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def root_url():
    """The gateway root, for endpoints that sit beside /v1 rather than under it."""
    return base_url().rsplit("/v1", 1)[0]


def api_key():
    key = os.environ.get("AMINI_LLM_API_KEY")
    if not key:
        die("AMINI_LLM_API_KEY is not set. Export the LiteLLM virtual key first.")
    return key


def request(path, payload=None, method=None, stream=False):
    """Call a /v1 endpoint. Returns parsed JSON, or the raw response when streaming."""
    return call(base_url() + path, payload, method, stream)


def call(url, payload=None, method=None, stream=False):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Authorization": f"Bearer {api_key()}"}
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        return resp if stream else json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise SystemExit(explain_http_error(exc.code, body))
    except OSError as exc:
        # URLError subclasses OSError; a bare connect timeout raises TimeoutError.
        raise SystemExit(explain_network_error(exc))


def explain_http_error(code, body):
    hints = {
        401: "401 — the API key was rejected. Check AMINI_LLM_API_KEY.",
        429: "429 — rate limited by the gateway; retry with backoff.",
        500: "500 — the gateway reached but an upstream vLLM backend is down.\n"
             "      Run `doctor` to see which alias, then restart that container.",
    }
    hint = hints.get(code, f"HTTP {code}")
    return f"{hint}\n  response: {body[:600]}"


def explain_network_error(exc):
    reason = getattr(exc, "reason", exc)
    return (
        f"cannot reach {base_url()} ({reason}).\n"
        "  A timeout here almost always means the Twingate tunnel is down or your\n"
        "  account lacks the resource covering this host. Connect Twingate and retry."
    )


# ---------------------------------------------------------------- image input

def to_data_url(source):
    """Base64-encode a local image. Remote URLs are passed through unchanged."""
    if source.startswith(("http://", "https://")):
        return source
    if not os.path.isfile(source):
        die(f"image not found: {source}")
    mime = mimetypes.guess_type(source)[0] or "image/png"
    with open(source, "rb") as handle:
        return f"data:{mime};base64," + base64.b64encode(handle.read()).decode()


def build_content(prompt, images):
    if not images:
        return prompt
    parts = [{"type": "text", "text": prompt}]
    parts += [{"type": "image_url", "image_url": {"url": to_data_url(i)}} for i in images]
    return parts


# ------------------------------------------------------------------ commands

def cmd_models(_opts):
    data = request("/models")
    for entry in data.get("data", []):
        alias = entry["id"]
        ctx = CONTEXT.get(alias)
        print(f"{alias:<16} context={ctx if ctx else '?':<8}")


def cmd_health(_opts):
    data = call(root_url() + "/health")
    for bucket, label in (("healthy_endpoints", "UP"), ("unhealthy_endpoints", "DOWN")):
        for entry in data.get(bucket, []):
            note = ""
            if label == "DOWN":
                note = "  <- upstream unreachable (container stopped or off-network)"
            print(f"[{label:<4}] {entry.get('model'):<22} {entry.get('api_base')}{note}")
    print(f"\nhealthy={data.get('healthy_count')} unhealthy={data.get('unhealthy_count')}")


def cmd_doctor(_opts):
    print(f"gateway: {base_url()}")
    print("key:     %s\n" % ("set" if os.environ.get("AMINI_LLM_API_KEY") else "MISSING"))
    cmd_health(_opts)
    print("\nlive probes:")
    for alias in ("chat-v1", "chat-think-v1", "vision-v1", "ocr-v1"):
        probe_chat_alias(alias)
    probe_embed_alias("embed-v1")


def probe_chat_alias(alias):
    payload = {
        "model": alias,
        "max_tokens": 512 if "think" in alias else 32,
        "messages": [{"role": "user", "content": "Reply with exactly: ok"}],
    }
    try:
        out = request("/chat/completions", payload)
        content = (out["choices"][0]["message"].get("content") or "").strip()
        print(f"  {alias:<16} OK   {content[:40]!r}")
    except SystemExit as exc:
        print(f"  {alias:<16} FAIL {str(exc).splitlines()[0]}")


def probe_embed_alias(alias):
    try:
        out = request("/embeddings", {"model": alias, "input": "ok"})
        print(f"  {alias:<16} OK   dims={len(out['data'][0]['embedding'])}")
    except SystemExit as exc:
        print(f"  {alias:<16} FAIL {str(exc).splitlines()[0]}")


def chat_payload(opts, model, images=()):
    messages = []
    if opts.get("system"):
        messages.append({"role": "system", "content": opts["system"]})
    messages.append({"role": "user", "content": build_content(opts["prompt"], images)})
    payload = {"model": model, "messages": messages, "max_tokens": opts["max_tokens"]}
    if opts.get("temperature") is not None:
        payload["temperature"] = opts["temperature"]
    if opts.get("json"):
        payload["response_format"] = {"type": "json_object"}
    return payload


def run_chat(opts, default_model, images=(), default_budget=1024):
    opts.setdefault("max_tokens", default_budget)
    model = opts.get("model") or default_model
    payload = chat_payload(opts, model, images)
    if opts.get("stream"):
        return stream_chat(payload)
    out = request("/chat/completions", payload)
    if opts.get("raw"):
        print(json.dumps(out, indent=2))
        return
    print_message(out["choices"][0])


def print_message(choice):
    message = choice["message"]
    reasoning = message.get("reasoning_content")
    if reasoning:
        print("--- reasoning ---")
        print(reasoning.strip())
        print("--- answer ---")
    content = message.get("content")
    if content:
        print(content.strip())
    elif choice.get("finish_reason") == "length":
        print("(empty content: the output budget was spent on reasoning — raise --max-tokens)",
              file=sys.stderr)
    for call in message.get("tool_calls") or []:
        print(f"[tool_call] {call['function']['name']}({call['function']['arguments']})")


def stream_chat(payload):
    payload["stream"] = True
    resp = request("/chat/completions", payload, stream=True)
    for line in resp:
        text = line.decode(errors="replace").strip()
        if not text.startswith("data:"):
            continue
        blob = text[5:].strip()
        if blob == "[DONE]":
            break
        delta = json.loads(blob)["choices"][0].get("delta", {})
        sys.stdout.write(delta.get("content") or "")
        sys.stdout.flush()
    print()


def cmd_chat(opts):
    run_chat(opts, MODELS["chat"])


def cmd_think(opts):
    opts.setdefault("max_tokens", 2048)
    run_chat(opts, MODELS["think"], default_budget=2048)


def cmd_vision(opts):
    if not opts["images"]:
        die("vision needs at least one --image")
    run_chat(opts, MODELS["vision"], images=opts["images"])


def cmd_ocr(opts):
    if not opts["images"]:
        die("ocr needs --image")
    opts.setdefault("prompt", "Transcribe all text in this image exactly.")
    if not opts["prompt"]:
        opts["prompt"] = "Transcribe all text in this image exactly."
    run_chat(opts, MODELS["ocr"], images=opts["images"], default_budget=4096)


def cmd_embed(opts):
    inputs = opts["args"]
    if not inputs:
        die("embed needs at least one text argument")
    model = opts.get("model") or MODELS["embed"]
    out = request("/embeddings", {"model": model, "input": inputs})
    if opts.get("raw"):
        print(json.dumps(out, indent=2))
        return
    for item in out["data"]:
        vec = item["embedding"]
        preview = ", ".join(f"{v:.4f}" for v in vec[:4])
        print(f"[{item['index']}] dims={len(vec)}  [{preview}, ...]")
    print(f"usage: {out.get('usage')}")


COMMANDS = {
    "models": cmd_models,
    "health": cmd_health,
    "doctor": cmd_doctor,
    "chat": cmd_chat,
    "think": cmd_think,
    "vision": cmd_vision,
    "ocr": cmd_ocr,
    "embed": cmd_embed,
}

FLAGS_WITH_VALUE = {
    "--model": ("model", str),
    "--max-tokens": ("max_tokens", int),
    "--system": ("system", str),
    "--temperature": ("temperature", float),
    "--image": ("images", str),
}


def parse_args(argv):
    opts = {"images": [], "args": []}
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in FLAGS_WITH_VALUE:
            key, cast = FLAGS_WITH_VALUE[token]
            index += 1
            if index >= len(argv):
                die(f"{token} needs a value")
            value = cast(argv[index])
            opts["images"].append(value) if key == "images" else opts.update({key: value})
        elif token in ("--stream", "--json", "--raw"):
            opts[token.lstrip("-")] = True
        elif token.startswith("--"):
            die(f"unknown flag: {token}")
        else:
            opts["args"].append(token)
        index += 1
    opts["prompt"] = " ".join(opts["args"])
    return opts


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return
    command = argv[0]
    if command not in COMMANDS:
        die(f"unknown command: {command}\n{__doc__}")
    COMMANDS[command](parse_args(argv[1:]))


if __name__ == "__main__":
    main()
