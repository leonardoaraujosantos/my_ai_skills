---
name: aminichain
description: Working in the AminiChain repository, a Cosmos SDK chain with an EVM (cosmos/evm) and native precompiles for oracles, jobs, compute, content, MDI and hosts. Covers orienting in the repo (AGENTS.md first), the Makefile build/test/lint/proto targets, running a single-validator localnet with scripts/local-node.sh or the docker compose localnet, stopping and resetting it, the precompile addresses and ABIs and how to call them with cast against a local node, reading module and EVM params, build-time inputs such as power reduction, and the repo's working conventions (tracer bullets, red-first tests, small PRs, signed commits). Broadcasting to any non-local network, real keys, and production genesis or ceremony files are gated behind explicit approval. Use when the user says "aminichain", "aminichaind", "run a localnet", "start the chain locally", "call the oracle/job/compute/content/mdi/host registry precompile", "precompile 0x1900/0x1908", "query chain params", "make localnet", "build aminichaind", or is working in a repo with cmd/aminichaind and precompiles/.
argument-hint: "[orient|build|localnet|precompiles|params|conventions] [topic]"
---

# AminiChain: Build, Localnet, Precompiles & Repo Conventions

AminiChain is a Cosmos SDK app-chain that embeds an Ethereum VM through [cosmos/evm](https://github.com/cosmos/evm). Every resource the chain manages (oracles, jobs, compute offers, content, MDI records, hosts) is reachable through **two doors**: a native Cosmos message server in `x/aminichain`, and a stateful EVM **precompile** at a fixed address, so Solidity contracts and EVM tooling (`cast`, viem, ethers) can use the chain directly. The daemon is `aminichaind`.

This skill assumes the user has the repository checked out. **It deliberately carries no project specifics that change over time.** Read them from the repo at runtime:

| Read first | Why |
|------------|-----|
| `AGENTS.md` | The repo's rules for agents and reviewers: two doors, precompile revert semantics, determinism, fail-closed, testing, PR and review conventions. Authoritative over this skill. |
| `go.mod` | Exact Cosmos SDK, CometBFT, cosmos/evm and ibc-go versions |
| `Makefile` | The build, test, lint, proto and docker targets that actually exist |
| `docs/` (start with `docs/LOCALNET.md`, `docs/PRECOMPILES.md`, `docs/*.CLI.md`) | Walkthroughs and per-precompile CLI docs |
| `deploy/docker/README.md` | The docker compose localnet and the `aminictl` CLI |

| Task | Reference file |
|------|----------------|
| Single-validator localnet, docker compose localnet, ports, stop and reset | `references/localnet.md` |
| Precompile addresses, ABIs, `cast` calls, params, build-time inputs | `references/precompiles-and-params.md` |

**How to use this skill:** read `AGENTS.md` before writing or reviewing code, then the matching reference file. Check versions in `go.mod` rather than trusting the snapshot below. Prefer the repo's own scripts over hand-rolled `init` sequences, because a bare `aminichaind init && start` does not boot (see `references/localnet.md`).

## Versions (snapshot, checked 2026-10-08; re-read `go.mod`)

| Component | Version |
|-----------|---------|
| Go | `go 1.25.0` directive in `go.mod` |
| Cosmos SDK | v0.53.6 |
| CometBFT | v0.38.21 |
| cosmos/evm | v0.6.3 |
| ibc-go | v10 (v10.7.0) |
| Ignite CLI (proto generation only) | v29.10.1 |

Ignite is used to regenerate protobuf code (`make proto-gen` runs `ignite generate proto-go --yes`), not to run the chain. For Ignite itself (install, the v29 vs v30 command split, `config.yml`, buf errors) use the **`ignite`** skill; do not duplicate it here. Do not install an unpinned Ignite: the installer can resolve to a release candidate with different command names.

## ⚠️ Safety gate: local only, throwaway keys, no production genesis

Everything this skill runs is a **throwaway local chain**. Keys come from the `test` keyring backend, genesis is generated on the spot, and the data directory is wiped on reset. Treat all of it as public.

**Blocked by default**; the user must confirm *in this conversation* first:

- any `aminichaind tx …` or `cast send` whose `--node` / `--rpc-url` is not `127.0.0.1` / `localhost`, or whose chain id is not a localnet one
- `cast send`, `forge script --broadcast`, `forge create` against anything but a local node you started in this session
- importing, pasting or exporting a real mnemonic or private key, or adding one to any keyring, `.env` or config file
- editing, generating or "fixing" production or shared-network genesis files, genesis ceremony inputs, production presets under `deploy/docker/config/presets/`, any `*-prod` make target, or `aminictl init prod-*`
- changing a governance parameter default or a build-time input (such as power reduction) in a way that would ship to a real network
- `make docker-clean-all` (removes volumes; it asks for confirmation for a reason)

Always allowed: `go build`, `go test`, `make test-unit`, `make lint`, `make localnet`, the docker **localnet** targets, `cast call` / `eth_call` and `aminichaind query` against a local node.

When a write is wanted, do it on the localnet, show the command and result, and never point the same command at another endpoint without approval.

## Quick start

```bash
# Orient
sed -n '1,60p' AGENTS.md
grep -E 'cosmos-sdk |cometbft |cosmos/evm |ibc-go' go.mod

# Build and test
make install                 # go install ./cmd/aminichaind with version ldflags
make test-unit               # go test -mod=readonly ./... (30m timeout)
make test                    # govet + govulncheck + test-unit
go test ./precompiles/...    # narrower loop
make lint                    # golangci-lint via `go tool`
make proto-gen               # ignite generate proto-go --yes (needs the pinned Ignite)

# Single-validator localnet on loopback-only, non-default ports (foreground; Ctrl-C stops it)
make localnet                # = bash scripts/local-node.sh --reset

# From another terminal: EVM JSON-RPC is up, and a precompile answers
cast chain-id --rpc-url http://127.0.0.1:18545
cast call 0x0000000000000000000000000000000000001900 "getOracleCount()(uint256)" \
  --rpc-url http://127.0.0.1:18545
```

## Routing table

| The user asks… | Go to |
|----------------|-------|
| "run a localnet", "start the chain", "multi-node / docker localnet", "stop / reset the chain", "port already in use" | `references/localnet.md` |
| "call the job / oracle / host precompile", "what's at 0x19xx", "decode this precompile call", "query params", "power reduction" | `references/precompiles-and-params.md` |
| "add a field / message / precompile method" | `AGENTS.md` (two doors, determinism, revert semantics), then the `ignite` skill for proto regeneration |
| "how do I open a PR here", "how many review rounds" | `AGENTS.md` sections on build order, testing, pull requests and review |

## Conventions an agent must follow in this repo

These are the repo's own rules, summarised; `AGENTS.md` has the authoritative wording and wins on any difference.

- **Read `AGENTS.md` first**, and apply it when reviewing as well as when writing.
- **Two doors, one behaviour.** A rule enforced on the native message server must be enforced on the precompile, and vice versa; stored state must be identical for the same logical action through either door. When you change one door, check its twin.
- **Determinism.** Anything on the consensus path (ID derivation, hashing, state writes) may use block height and block time, never wall clock, map iteration order, or randomness.
- **Tracer bullets.** Build one thin end-to-end slice and prove it before widening; this constrains the order of work inside a change.
- **Red first.** Write the failing test, watch it fail, then make the change. A test that cannot fail on the old code proves nothing.
- **Small PRs.** One concern per PR; every push triggers a full automated review round, so a large diff costs many rounds.
- **Signed commits with a work email.** Check `git config user.email` and `git log --show-signature -1` before pushing.
- **Fail closed.** Reject malformed input loudly; do not silently skip or default it.

## Environment notes

- Building needs Go with CGO enabled (cosmos/evm's EIP-712 path links `libsecp256k1`). `GOTOOLCHAIN=auto` lets Go fetch the toolchain `go.mod` asks for.
- `scripts/local-node.sh` needs `python3` (it patches genesis JSON) and `jq` is handy for the verification commands it prints.
- The docker localnet needs Docker 24+ and Compose v2.20+ (see `deploy/docker/README.md`).
- The repo has end-to-end scripts under `scripts/*-e2e.sh`; read them for working examples of write paths through both doors before inventing your own.
