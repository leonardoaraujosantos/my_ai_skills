---
name: arweave
description: Operate Arweave and AO as a developer — permanent storage uploads (Turbo SDK/CLI, arweave-js), GraphQL queries by tags, permaweb site deploys (manifests, ArNS, ario-deploy/@permaweb/deploy), and AO hyperparallel compute (aos REPL, Lua handlers, aoconnect, HyperBEAM HTTP state reads). Includes wallet/keyfile handling, cost estimation, and privacy rules for immutable public storage. Use when the user says "upload to arweave", "permaweb", "permanent storage", "deploy to arweave/ArNS", "AO process", "aos", "aoconnect", "HyperBEAM", "Turbo credits", "query arweave", or "SmartWeave".
argument-hint: [upload|query|deploy|ao] [topic]
---

# Arweave & AO — Developer Operations

Playbooks for the 2026 Arweave/AO toolchain. Facts and commands verified against official docs on **2026-07-13** — tooling churns fast; when in doubt re-check the docs listed at the bottom.

| Task | Reference file |
|------|----------------|
| Upload files/data permanently (Turbo SDK/CLI, tags, costs, arweave-js) | `references/upload.md` |
| Find and fetch data (GraphQL, tags, gateways) | `references/query.md` |
| Deploy a site to the permaweb (manifests, ArNS, CI) | `references/deploy.md` |
| AO compute: aos REPL, Lua handlers, aoconnect, HyperBEAM | `references/ao.md` |

**How to use this skill:** identify the task, read the matching reference file before answering, then run/write code against the user's project. Prefer the modern flow (Turbo, bundles, GraphQL, HyperBEAM) — `arkb`, ArQL, and raw legacynet-era tutorials are historical.

## ⚠️ Safety gates

**Permanence gate — uploads cannot be undone.** Anything uploaded to Arweave is public, immutable, and permanent. Before any real upload:
1. Show the user exactly which files/data will be uploaded and ask for confirmation.
2. Check content for PII/secrets first (names, e-mails, keys, tokens, health data). Encryption is access control, **not deletion** — GDPR/LGPD erasure is impossible. Store hashes/ciphertext instead of raw sensitive data, or keep sensitive data off-chain.

**Spending gate — these cost real money; require explicit approval in the conversation:**
- Uploads beyond trivial size (Turbo free tier covers roughly ≤100 KiB items; rate ≈ **$31/GiB**, July 2026)
- Buying Turbo credits (`turbo top-up`, Stripe/crypto)
- Buying or leasing **ArNS names** (paid in ARIO)
- Any AR/AO/ARIO token transfer, swap, or bridge

**Key material — never leak wallets:**
- Never print, commit, or upload wallet keyfiles (`wallet.json`, `~/.aos.json`). Add them to `.gitignore` immediately when a project uses one.
- Pass keys via env/`base64` (e.g. `DEPLOY_KEY=$(base64 -i wallet.json)`) only into trusted CLIs; never into logs or third-party services.
- Generating a throwaway dev wallet is cheap and free — prefer it over reusing a funded wallet for experiments.

## Core mental model (30 seconds)

- **Arweave** = blockchain specialized in permanent data. Pay once (endowment model), store forever. Miners prove access to random historical chunks (SPoRA); storage is the work.
- **Permaweb** = sites/apps stored on Arweave, addressed by transaction ID, served over HTTP by ~600 **ar.io gateways** (`https://<gateway>/<txid>`). **ArNS** names are the mutable pointers; content itself never changes.
- **AO** = the compute protocol: independent processes, message-passing only, every message persisted to Arweave, state derived from the log. **aos** (lowercase) = the Lua CLI/REPL dev tool — not the same thing.
- **HyperBEAM** = the production AO-Core implementation (Erlang/OTP). Process state is readable over plain HTTP.
- Everything is tagged; **tags are the schema** and GraphQL is the index.

## Known-stale traps (do not recommend)

| Stale (pre-2025 tutorials) | Current (July 2026) |
|---|---|
| `npm i -g https://get_ao.g8way.io` | `npm i -g https://get_ao.arweave.net` (or `@permaweb/aos`) |
| `arkb` for deploys | `@ar.io/deploy` (ario-deploy) or `@permaweb/deploy` |
| ArQL queries | GraphQL + tags |
| "AO = Arweave Operating System" | AO is a protocol; aos is the tool |
| "Execution on AO is free" | Costs are modular: storage + compute + services |
| ArConnect wallet | Rebranded **Wander**; Beacon for mobile |

## Official docs (current)

- Arweave Cookbook — https://cookbook.arweave.net
- AO Cookbook — https://cookbook_ao.arweave.net
- HyperBEAM — https://hyperbeam.arweave.net
- ar.io (gateways, ArNS, deploys) — https://docs.ar.io
- Turbo — https://docs.ardrive.io · rates: https://payment.ardrive.io/v1/rates
- Explorer — https://ao.link · viewblock.io/arweave
