---
name: ignite
description: Cosmos SDK app-chain scaffolding and local development with Ignite CLI. Covers installing a pinned release, which Ignite major matches which Cosmos SDK version, the v30 split (top-level commands now target gno.land, Cosmos tooling moved under `ignite cosmos`), scaffolding chains/modules/messages/queries/list/map/single/type/params and what files each touches, proto/OpenAPI/TS client generation, `chain serve` hot reload, `chain build`/`init`, the `config.yml` reference (accounts, validators, genesis overrides, faucet), and debugging buf/proto, Go toolchain, and depinject/app_config.go wiring failures. Broadcasting to non-local networks and real keys are gated behind explicit approval. Use when the user says "ignite scaffold", "ignite chain serve", "scaffold a cosmos chain/module/message", "add a query/list/map to my module", "regenerate protos", "config.yml for ignite", "faucet", "why won't my ignite chain build", "upgrade ignite", or has a Cosmos SDK project with a config.yml at its root.
argument-hint: "[scaffold|serve|config|debug|upgrade] [topic]"
---

# Ignite CLI — Cosmos SDK Chain Scaffolding & Local Development

Playbooks for [Ignite CLI](https://github.com/ignite/cli) (docs: https://docs.ignite.com), the code generator and dev runner for Cosmos SDK app-chains. Ignite writes the boilerplate (protos, keepers, msg servers, AutoCLI, genesis, app wiring) and runs a throwaway single-validator chain with hot reload. **It is a scaffolder and a dev loop, not a production launcher**: `chain serve` / `chain init` are explicitly "ONLY FOR DEVELOPMENT PURPOSES" in Ignite's own help.

| Task | Reference file |
|------|----------------|
| Install a pinned release, Ignite to Cosmos SDK version map, v29 vs v30 command names, upgrading | `references/install-and-versions.md` |
| `scaffold chain/module/message/query/list/map/single/type/params`, files each touches, `generate proto-go/openapi/ts-client` | `references/scaffolding.md` |
| `chain serve/build/init/faucet`, `config.yml` reference, ports, data dir, genesis overrides | `references/running-and-config.md` |
| Tests, proto/buf errors, Go toolchain mismatches, module wiring in `app_config.go`, outgrowing Ignite | `references/troubleshooting.md` |

**How to use this skill:** first run `ignite version` and read `go.mod` (Cosmos SDK line) to know which Ignite major and SDK you are on, because **v30 renamed the Cosmos commands** (see below). Read the matching reference file before answering. Commit (or stash) before every `scaffold` command so the diff shows exactly what Ignite wrote. Default to the local `chain serve` loop; never point anything at a public network without approval.

## Which command name? (check first)

| `ignite version` says | Cosmos SDK commands are | Top-level `ignite scaffold` / `ignite chain` mean |
|---|---|---|
| v28.x / v29.x | `ignite scaffold …`, `ignite chain …`, `ignite generate …`, `ignite doctor` | Cosmos SDK |
| v30.x (RC as of 2026-10-08) | `ignite cosmos scaffold …`, `ignite cosmos chain …`, `ignite cosmos generate …`, `ignite cosmos doctor` | **gno.land** (realms/packages, gno dev chain) |

So on v30, `ignite chain serve` starts a **gno.land** dev chain, not your Cosmos chain. Examples in this skill use v29 spelling; on v30 insert `cosmos` after `ignite`. Heads-up: the official installer currently resolves "latest" to `v30.0.0-rc.2`, because GitHub marks that RC as Latest (checked 2026-10-08). Pin a version (see Quick start).

## ⚠️ Safety gate — local chains only, no real keys, no broadcast without approval

Ignite's dev loop deliberately uses throwaway keys. Treat everything it generates as public:

- The `accounts:` in `config.yml` (default `alice`, `bob`) get **fresh mnemonics on every reset, printed in plain text** to the terminal and to any `--output-file` log. Any `mnemonic:` pinned in `config.yml` is committed to git. **Never fund, reuse, or import these keys on a public network.**
- `config.yml` genesis balances, bonded amounts, `default_denom`, and `genesis:` overrides describe a **dev genesis**. They are not a production genesis, token distribution, or launch plan.
- The faucet binds to **all interfaces** (observed `http://0.0.0.0:4500`-style URL), so anyone on the LAN can draw from it while `serve` runs.

**Blocked by default**; the user must confirm *in this conversation* first:

- any `<appd> tx …` with `--node` pointing at a non-local RPC, or any `--chain-id` of a shared testnet/mainnet
- importing a real mnemonic or hardware/production key into the chain keyring, or putting one in `config.yml`
- `ignite testnet in-place` / `multi-node` (v30: `ignite cosmos testnet …`) run on state copied from a live network, and `ignite relayer` (an Ignite App that connects to other chains)
- publishing a release (`ignite chain build --release` is fine locally; uploading the artifacts or tagging is not)

Always allowed: `ignite scaffold …`, `ignite generate …`, `ignite chain build`, `ignite chain serve` / `init` on localhost, `go test ./...`, queries and txs against `127.0.0.1`.

## Quick start

```bash
# Install a pinned release into the current directory (no "!" = no /usr/local/bin write), then move it yourself
curl https://get.ignite.com/cli@v29.10.1 | bash      # Cosmos SDK v0.53.x line
./ignite version                                     # prints Ignite + Cosmos SDK version
go version                                           # current docs require Go >= 1.26.7 (see install reference)

# New chain (git-commit before every later scaffold)
ignite scaffold chain github.com/acme/mychain --address-prefix acme --default-denom uacme
cd mychain
ignite scaffold list post title body                 # CRUD stored as an auto-incrementing list
ignite scaffold message add-pool amount:coin active:bool --response id:uint
ignite scaffold query pool-count --response count:uint

# Run it: build + init + start one validator, rebuild on every file change
ignite chain serve                                    # --reset-once to wipe state once; -f to wipe on every change
mychaind q mychain list-post                          # binary lands in $(go env GOPATH)/bin
mychaind tx mychain create-post hello world --from alice --chain-id mychain -y

# Tests (scaffolded keeper/types tests)
go test ./x/...
```

## Routing table

| The user asks… | Go to |
|----------------|-------|
| "install/upgrade ignite", "which SDK version", "ignite chain serve starts gno?", "migrate to v30" | `references/install-and-versions.md` |
| "scaffold a module/message/query/list/map", "what did that command change", "regenerate protos/openapi/ts client" | `references/scaffolding.md` |
| "serve", "config.yml", "add an account/validator", "change chain-id/denom/genesis", "faucet", "ports in use" | `references/running-and-config.md` (mind the safety gate) |
| "build fails", "buf error", "go toolchain", "module not registered", "depinject panic", "tests fail", "should we stop using ignite" | `references/troubleshooting.md` |

## Environment notes

- Verified 2026-10-08 against the released binaries `v29.10.1` and `v30.0.0-rc.2` (linux/amd64, `--help` output), plus a real `scaffold chain` → `scaffold list/map/single/message/query/params/module` → `chain serve` → tx/query → `go test` → `chain build` run on v29.10.1 with Go 1.26.8.
- Ignite needs Go on `PATH`; it calls `go`, `buf` (as a Go tool from the chain's `go.mod`), and the chain binary it builds. It does not need Docker or Node (Node only if you use the generated TS client / Vue / React).
- Version map and RC status come from https://github.com/ignite/cli/blob/main/changelog.md and the GitHub releases page; re-check both before advising an upgrade.
