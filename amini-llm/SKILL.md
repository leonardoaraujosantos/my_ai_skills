---
name: amini-llm
description: Use the AminiLLM gateway - a self-hosted, OpenAI-compatible LiteLLM proxy serving Qwen3 models on-prem (text chat, reasoning, vision/multimodal, OCR, embeddings). Use when the user wants to call the internal LLM, run inference without sending data to a third-party API, embed text locally, OCR a document, or troubleshoot the gateway. Triggers - "amini llm", "our LLM", "internal LLM", "the qwen model", "chat-v1", "vision-v1", "embed-v1", "litellm gateway", "on-prem inference".
argument-hint: "[command] [args...]"
---

# AminiLLM Gateway

A self-hosted **LiteLLM** proxy fronting **vLLM** backends on the GPU host. It speaks the
OpenAI API, so any OpenAI SDK, LangChain, LlamaIndex, or plain `curl` works by changing
only the base URL and key. Nothing leaves the internal network.

```
Base URL   http://10.10.20.4:4000/v1      (Twingate required)
Auth       Bearer <LiteLLM virtual key>   (from $AMINI_LLM_API_KEY - never hardcode)
```

## Setup

The key is a secret and is **not** stored in this repo. Export both variables — get the
key from the gateway owner or your team's secret store:

```bash
export AMINI_LLM_BASE_URL="http://10.10.20.4:4000/v1"   # optional, this is the default
export AMINI_LLM_API_KEY="<your-litellm-virtual-key>"
```

Access is gated by **Twingate**: your account must be in a group holding the resource
covering `10.10.20.4:4000`. Without it, every call hangs and then times out.

Verify the whole path in one command:

```bash
python3 ~/.claude/skills/amini-llm/amini_llm_cli.py doctor
```

## Models

Five aliases. Use the **alias**, never the raw Hugging Face name — the gateway maps
aliases onto upstreams, and raw names are rejected.

| Alias | Purpose | Context | Vision | Tools | Notes |
|---|---|---|---|---|---|
| `chat-v1` | General text chat | **262,144** | ✅ yes | ✅ | The default workhorse. Thinking disabled. |
| `chat-think-v1` | Same weights, reasoning on | **262,144** | ✅ yes | ✅ | Emits `reasoning_content`. Needs a large budget. |
| `vision-v1` | Vision / multimodal | **131,072** | ✅ multi-image | ✅ | Qwen3-VL-30B-A3B-Instruct-FP8. |
| `ocr-v1` | Verbatim transcription | **16,384** | ✅ | ❌ | Small context — one page at a time. |
| `embed-v1` | Embeddings | **2,048** | — | — | **4096 dims**. Batches of 256+ fine. |

`chat-v1` and `chat-think-v1` are **one container** (`vllm-chat`, tensor-parallel across
2 GPUs) differing only by `chat_template_kwargs.enable_thinking`. They fail and recover
together — if one is down, so is the other.

Relative cost per 1M tokens (gateway-reported, for budgeting only):
`chat` $0.08 in / $0.28 out · `vision` $0.13 / $0.90 · `ocr` $0.10 / $0.40 · `embed` $0.07 in.

### Verified capabilities

Confirmed by live probe, not inferred from docs:

- **Streaming** (`"stream": true`) — standard SSE `data:` frames ending in `[DONE]`.
- **Tool / function calling** — on `chat-v1`, `chat-think-v1`, `vision-v1`; returns
  `finish_reason: "tool_calls"` with a populated `tool_calls` array. **Not on `ocr-v1`**
  (that backend was started without `--enable-auto-tool-choice`).
- **Structured output** — both `response_format: {"type":"json_object"}` and a full
  `{"type":"json_schema", ...}` work and honor the schema.
- **Multi-image** — several `image_url` parts in one message, answered in order.
- **Embeddings** — OpenAI shape: `data[]` of `{embedding, index, object}`, batch-ordered.

## CLI

```bash
CLI=~/.claude/skills/amini-llm/amini_llm_cli.py

python3 $CLI models                       # list aliases + context sizes
python3 $CLI health                       # per-backend up/down
python3 $CLI doctor                       # network + auth + live probe of all five

python3 $CLI chat "Capital of Barbados?"
python3 $CLI chat "Write a haiku" --stream
python3 $CLI chat "Return JSON with key capital" --json
python3 $CLI think "If a train leaves 9:15 and takes 95 min, when does it arrive?"
python3 $CLI vision "What is the total?" --image invoice.png
python3 $CLI ocr --image scan.png
python3 $CLI embed "first text" "second text"

python3 $CLI bench                        # single-stream tok/s + TTFT
python3 $CLI bench --all                  # every mode below
python3 $CLI bench --rtt                  # tunnel round-trip floor
python3 $CLI bench --concurrency          # aggregate tok/s at 1/2/4/8 streams
python3 $CLI bench --prefill              # prompt-processing rate at 2k/8k/24k
python3 $CLI bench --embed                # embedding throughput at batch 1/32/256
python3 $CLI bench --model vision-v1 --runs 6
```

Use `bench` rather than writing throughput code by hand — it already handles the
methodology traps: a per-run nonce defeats vLLM prefix caching (without it you measure
a cache hit), the clock starts *before* the request so TTFT includes the tunnel, and
decode rate excludes TTFT so prefill does not inflate it.

Flags: `--model`, `--max-tokens`, `--system`, `--temperature`, `--stream`, `--json`,
`--raw` (full JSON), `--image` (repeatable; local path or URL).

## Direct use

### curl

```bash
curl "$AMINI_LLM_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $AMINI_LLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"chat-v1","messages":[{"role":"user","content":"hello"}]}'
```

### Python (OpenAI SDK)

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url=os.environ.get("AMINI_LLM_BASE_URL", "http://10.10.20.4:4000/v1"),
    api_key=os.environ["AMINI_LLM_API_KEY"],
)

print(client.chat.completions.create(
    model="chat-v1",
    messages=[{"role": "user", "content": "hello"}],
).choices[0].message.content)
```

### Reasoning model

The chain of thought arrives in a **separate field**, not in `content`:

```python
r = client.chat.completions.create(
    model="chat-think-v1",
    messages=[{"role": "user", "content": "Is 91 prime? Explain briefly."}],
    max_tokens=2048,                       # see the gotcha below
)
msg = r.choices[0].message
print(msg.model_extra.get("reasoning_content"))   # the thinking
print(msg.content)                                # the answer
```

You can also force thinking **on** for `chat-v1`, or off for `chat-think-v1`, by passing
the template flag through:

```python
extra_body={"chat_template_kwargs": {"enable_thinking": True}}
```

### Vision and OCR

Prefer **base64 data URLs** over remote `http(s)` URLs (see gotchas):

```python
import base64, pathlib

b64 = base64.b64encode(pathlib.Path("invoice.png").read_bytes()).decode()
r = client.chat.completions.create(
    model="vision-v1",
    messages=[{"role": "user", "content": [
        {"type": "text", "text": "What is the invoice number and amount due?"},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
    ]}],
    max_tokens=512,
)
```

Which model for an image?

- **`ocr-v1`** for a faithful transcription — it returns the text and nothing else.
- **`vision-v1`** to *reason* about an image — answer questions, extract fields, describe.
- **`chat-v1`** also accepts images and has 2x the context, so it is the better choice for
  a long document plus images in one conversation.

### Embeddings

```python
r = client.embeddings.create(model="embed-v1", input=["first text", "second text"])
vectors = [d.embedding for d in r.data]     # 4096 dims each, input order preserved
```

Size vector columns at **4096** (e.g. `vector(4096)` in pgvector).

## Performance baseline

Measured with `bench --all` (2026-09-09). Re-run it to compare rather than trusting
these numbers indefinitely.

| Model | Decode | TTFT |
|---|---|---|
| `chat-v1` | **~205 tok/s** | ~580 ms |
| `chat-think-v1` | ~205 tok/s | ~580 ms |
| `vision-v1` | ~164 tok/s | ~500 ms |
| `ocr-v1` | ~143 tok/s | ~480 ms |

Single-stream decode is fast because these are A3B mixture-of-experts models — only
~3B parameters are active per token — served tensor-parallel across 2 GPUs.

**The tunnel is the latency floor.** A round-trip to the gateway is ~320 ms on a pooled
connection and ~480 ms on a fresh one. Traefik on `:8080` on the same host measures
identically, so this is network, not gateway overhead. Roughly half of the ~580 ms TTFT
is transport. Two consequences:

- **Reuse one client.** A new connection per request wastes ~160 ms. The OpenAI SDK pools
  by default, so build the client once and keep it.
- Nothing you do to the prompt will get you under the floor for a single short call.

**Concurrency scales well** — batch work rather than serializing it:

| Streams | Aggregate | Per-stream |
|---|---|---|
| 1 | 127 tok/s | 127 |
| 2 | 217 tok/s | 109 |
| 4 | **417 tok/s** | 105 |
| 8 | 480 tok/s | 79 |

Near-linear to 4 (3.3x aggregate for a 20% per-stream cost), with the knee at 8.

**Prefill is cheap and improves with size** — 3.2k tok/s at a 2.3k prompt, 7.9k at 9k,
**15.4k tok/s at 27k tokens** (the fixed round-trip amortizes away). Stuffing 27k tokens
of context costs under 2 seconds, so long-context RAG on `chat-v1` is affordable.

**Embeddings must be batched** — batch 1 is 1.2 texts/s, batch 32 is 13.1, batch 256 is
~15-19. That is a **13x speedup**; a single-text embed is almost entirely round-trip.
Never embed in a per-item loop.

## Gotchas

These each cost real debugging time:

1. **`embed-v1` context is only 2,048 tokens** — far smaller than the chat models. Chunk
   before embedding or you get `ContextWindowExceededError`.
2. **Empty `content` with `finish_reason: "length"` means reasoning ate the budget.**
   The output budget covers reasoning *plus* the answer, so a low ceiling gets spent
   thinking and truncated before any answer is emitted. For `chat-think-v1` use **512
   minimum**, 2048+ for real problems — 800 tokens was still not enough for a
   three-step word problem in testing.

   This bites `chat-v1` too. Despite `enable_thinking: False`, it **intermittently**
   emits a thinking preamble — observed in roughly 1-3 of 8 identical calls at default
   temperature. With a tight budget that produces empty `content`; with ~256 tokens of
   headroom it recovers and answers normally. So: give `chat-v1` at least 256 tokens
   even for one-word answers, use `temperature: 0` when you need short deterministic
   replies, and always handle an empty `content` rather than assuming it cannot happen.
3. **`ocr-v1` has a 16,384-token context** and no tool calling. One page per request.
4. **No fallbacks are configured** (`Available Model Group Fallbacks=None`). A dead
   backend is a hard 500 to the caller, not a silent downgrade — handle it client-side.
5. **`stream_timeout` is 30s** while the request timeout is 600s. Long reasoning streams
   can be cut off mid-flight even though the same call would succeed non-streamed.
6. **Remote image URLs are fetched by the GPU host, not by you.** Egress works, but the
   remote site sees a datacenter IP and may return 403 (Wikimedia does). Base64 the bytes.
7. **Use `/v1/chat/completions`, not `/v1/completions`.** The legacy endpoint answers but
   leaks raw chat-template tokens like `<think>` into the text.
8. **The key is enforced.** No header or a wrong key is a 401 — it is a weak shared
   secret, not an absent one. Never commit it.

## Troubleshooting

The three failure modes are distinguishable at a glance:

| Symptom | Cause | Fix |
|---|---|---|
| Hangs, then connect timeout | Twingate down, or your account lacks the resource | Connect Twingate; ask to be added to the group covering `10.10.20.4` |
| `401 token_not_found_in_db` | Missing or wrong key | Check `$AMINI_LLM_API_KEY` |
| `500 ... Connection error` + `Model Group=<alias>` | That alias's vLLM container is down | See below |
| `ContextWindowExceededError` | Input over that model's limit | Chunk (especially `embed-v1`) |
| Empty `content`, `finish_reason: length` | Reasoning ate the budget | Raise `max_tokens` |

For a 500, find out **which** backend died:

```bash
python3 ~/.claude/skills/amini-llm/amini_llm_cli.py health
```

Unhealthy entries report a `socket.gaierror: Name or service not known` on their
`api_base` hostname (`vllm-chat`, `vllm-embed`, ...). That is a **DNS** failure inside the
LiteLLM container: Docker's embedded DNS only holds names for running, attached
containers. So the backend is stopped, crash-looping, or on the wrong network — it is not
"still loading" (that would resolve and refuse the connection instead).

Two open endpoints need no key and separate "gateway is broken" from "a model is down":

```bash
curl http://10.10.20.4:4000/health/liveliness    # "I'm alive!"
curl http://10.10.20.4:4000/health/readiness     # {"status":"healthy","db":"connected"}
```

If those are healthy but a model 500s, the gateway is fine and only that vLLM container
needs restarting on the GPU host:

```bash
docker ps -a --format '{{.Names}}\t{{.Status}}' | grep vllm   # Restarting = crash loop, Exited 137 = OOM
docker logs --tail 80 vllm-chat
nvidia-smi                                                     # VRAM already fully claimed?
```

A plausible failure pattern: after a host restart the larger backends grab their
`gpu_memory_utilization` pools first and the rest crash-loop on startup with no VRAM left.
