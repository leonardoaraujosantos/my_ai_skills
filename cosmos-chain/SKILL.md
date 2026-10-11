---
name: cosmos-chain
description: Build, run and debug any Cosmos SDK app-chain, with or without an embedded EVM (cosmos/evm, "Cosmos EVM"). Covers orienting in an unfamiliar chain repo (go.mod, Makefile, app wiring, cmd/<appd>), building and testing the daemon, bringing up a throwaway single-validator localnet from the binary's own init/genesis/start commands or the repo's script, the standard cosmos/evm precompile addresses (0x0100 P256, 0x0400 Bech32, 0x0800-0x0807 staking/distribution/ICS20/bank/gov/slashing/ICS02) and custom ones, calling precompiles with cast against a local node, reading module/EVM/fee-market params, the evm_denom + denom_metadata boot panic, and conventions for consensus-critical code (determinism, parity between a Cosmos message and its EVM precompile). Scaffolding and proto generation defer to the ignite skill. Broadcasting to any non-local network, real keys, and production or shared genesis files are gated behind explicit approval. Use when the user says "cosmos sdk chain", "cosmos evm", "app-chain", "appd start", "run a localnet", "start the chain locally", "simd/evmd/<name>d", "call the staking/bank/gov precompile", "precompile 0x0800", "active_static_precompiles", "query chain params", "evm_denom", "denom metadata could not be found", "gentx/collect-gentxs", or is working in a repo with cmd/<name>d, app/app.go and x/ modules.
argument-hint: "[orient|build|localnet|precompiles|params|conventions] [topic]"
---

# Cosmos SDK & Cosmos EVM Chains: Build, Localnet, Precompiles & Conventions

Playbooks for working inside **any** Cosmos SDK app-chain repository: a plain SDK chain (`simd`-style), or a chain that embeds an Ethereum VM through [cosmos/evm](https://github.com/cosmos/evm) and exposes Cosmos modules to Solidity through **precompiles** at fixed addresses. The skill is project-agnostic on purpose: binary names, denoms, ports, chain ids, Makefile targets and custom precompile addresses are **read from the repo at runtime**, never assumed.

| Task | Reference file |
|------|----------------|
| Bring up a one-validator localnet (binary `init` → `genesis` → `start`, repo scripts, cosmos/evm `local_node.sh`, docker testnets), ports, stop and reset, boot failures | `references/localnet.md` |
| Standard and custom precompile addresses, ABIs, `cast` calls, module / EVM / fee-market params, genesis vs governance vs build-time values | `references/precompiles-and-params.md` |

**Related skills.** Use **`ignite`** for scaffolding chains, modules, messages and queries, for `ignite chain serve`, and for `generate proto-go`. Use **`foundry-tools`** / **`hardhat-tools`** for Solidity contracts deployed *onto* an EVM chain. This skill is about the chain itself.

## Orient first (every repo is different)

Run these before answering anything project-specific, and quote what they say instead of this skill's examples:

```bash
ls cmd/                                                   # the daemon: cmd/<name>d
grep -E 'cosmos-sdk |cometbft |cosmos/evm |ibc-go/v|^go ' go.mod
grep -E '^[a-zA-Z0-9_-]+:' Makefile | cut -d: -f1 | sort -u # targets that actually exist
ls app/ x/ precompiles/ 2>/dev/null                        # app wiring, custom modules, custom precompiles
ls AGENTS.md CONTRIBUTING.md docs/ scripts/ 2>/dev/null    # repo rules and existing localnet scripts
```

If the repo has an `AGENTS.md` or `CONTRIBUTING.md`, it is authoritative over this skill. If it has a localnet script (`scripts/*.sh`, `local_node.sh`, a `localnet` make target, or an Ignite `config.yml`), use that instead of a hand-rolled `init` sequence.

## Version matrix (snapshot, checked 2026-10-11; re-read `go.mod`)

| cosmos/evm | Cosmos SDK | CometBFT | ibc-go | Go | Notes |
|-----------|------------|----------|--------|----|-------|
| v0.7.x (latest v0.7.3) | v0.54.x | v0.39.x | v11 | 1.25 | Krakatoa app-side mempool, optional BlockSTM, ICS-02 precompile at `0x0807`, strict `abi.json` |
| v0.6.x (latest v0.6.3) | v0.53.x | v0.38.x | v10 | 1.23+ | ERC20 conversion only via the ICS20 precompile |
| no EVM | v0.50 / v0.53 / v0.54 | v0.38 / v0.39 | v8 / v10 / v11 | per `go.mod` | Ignite v28 scaffolds v0.50, v29 → v0.53, v30 → v0.55 (see `ignite` skill) |

Both cosmos/evm lines receive patch releases on the same day; a chain picks its line by SDK major. Migration guides live in cosmos/evm `docs/migrations/`.

## ⚠️ Safety gate: local only, throwaway keys, no production genesis

Everything this skill runs is a **throwaway local chain**: keys in the `test` keyring backend, genesis generated on the spot, data directory wiped on reset. Treat all of it as public.

**Blocked by default**; the user must confirm *in this conversation* first:

- any `<appd> tx …` or `cast send` whose `--node` / `--rpc-url` is not `127.0.0.1` / `localhost`, or whose `--chain-id` belongs to a shared testnet or mainnet
- `cast send`, `forge script --broadcast`, `forge create` against anything but a local node started in this session
- importing, pasting or exporting a real mnemonic or private key, or adding one to any keyring, `.env` or config file
- editing, generating or "fixing" a production or shared-network genesis, genesis ceremony inputs, validator keys, or any deploy preset or make target that is not clearly local
- changing a governance parameter default, a precompile list, or a build-time input in a way that would ship to a real network
- anything that removes docker volumes or data directories that are not the localnet home you created

Always allowed: `go build`, `go test`, `make build/install/test/lint`, the binary's `init`/`genesis`/`start` on `127.0.0.1`, `<appd> query …`, `cast call` / `eth_call` against a local node.

## Quick start

```bash
# Build
APPD=$(ls cmd | head -1)                 # e.g. simd, evmd, mychaind
make install 2>/dev/null || go install ./cmd/$APPD
$APPD version --long | head -20          # confirms SDK/CometBFT versions baked into the binary

# Test
go test ./x/... ./app/...                # narrow loop; `make test` for the repo's full suite
go test ./precompiles/... 2>/dev/null    # only on chains with custom precompiles

# Localnet (prefer the repo's own script if one exists; see references/localnet.md)
ls scripts/ local_node.sh config.yml 2>/dev/null

# Verify a running local node
$APPD status --node tcp://127.0.0.1:26657 | jq .sync_info.latest_block_height
cast chain-id --rpc-url http://127.0.0.1:8545                       # EVM chains only
cast call 0x0000000000000000000000000000000000000804 \
  "balances(address)((address,uint256)[])" 0x0000000000000000000000000000000000000001 \
  --rpc-url http://127.0.0.1:8545                                   # bank precompile answers => EVM is live
```

Ports above are the Cosmos defaults (RPC 26657, P2P 26656, gRPC 9090, REST 1317) and cosmos/evm defaults (JSON-RPC 8545, WS 8546). Repos often move them; read `app.toml`/`config.toml` in the localnet home.

## Routing table

| The user asks… | Go to |
|----------------|-------|
| "run a localnet", "start the chain", "init + start panics", "denom metadata could not be found", "stop / reset the chain", "port already in use", "multi-node testnet" | `references/localnet.md` |
| "call the staking / bank / gov / ICS20 precompile", "what's at 0x08xx", "our custom precompile at 0x…", "decode this precompile call", "query params", "which values are genesis vs build time" | `references/precompiles-and-params.md` |
| "scaffold a module / message / query", "regenerate protos", "ignite chain serve" | `ignite` skill |
| "deploy / test this Solidity contract on the chain" | `foundry-tools` or `hardhat-tools`, with `--rpc-url` pointing at the local node |
| "upgrade cosmos/evm from v0.6 to v0.7" | cosmos/evm `docs/migrations/v0.6.x_to_v0.7.0.md` (and the v0.5→v0.6 guide first if skipping) |

## Conventions for consensus-critical code

These apply to every Cosmos SDK chain; a repo's own `AGENTS.md`/`CONTRIBUTING.md` wins on any difference.

- **Determinism.** Anything on the consensus path (keepers, `BeginBlock`/`EndBlock`, ID derivation, hashing, precompile execution) may use block height and block time, never wall clock, map iteration order, randomness, floating point, or network calls.
- **Two doors, one behaviour.** When a resource is reachable both as a Cosmos message and as an EVM precompile, every validation rule and state write must be identical through either door. Change one, check its twin, test both.
- **Precompile revert semantics.** A precompile error must surface as an EVM revert with a reason; it must not panic the node or half-apply state. Follow the error handling in cosmos/evm's own `precompiles/` as the model.
- **State-breaking vs API-breaking.** Store layout, params, precompile list, gas costs and message validation are state-breaking and need a coordinated upgrade (`x/upgrade` handler, new binary for every validator). Query/CLI changes are not. Label PRs accordingly.
- **Red first.** Write the failing test, watch it fail, then make the change. Keeper tests and precompile integration tests both.
- **Fail closed.** Reject malformed input loudly; never silently skip or default it on the consensus path.
- **Small, reviewable PRs.** One concern per PR; consensus code gets reviewed line by line.
- **Signed commits** if the repo requires them: check `git config user.email` and `git log --show-signature -1` before pushing.

## Environment notes

- Building a cosmos/evm chain needs Go with **CGO enabled** (the EIP-712 and secp256k1 paths link C code). `GOTOOLCHAIN=auto` lets Go fetch the toolchain the `go.mod` asks for.
- Localnet scripts typically need `jq` (genesis patching); some use `python3` or `yq`. Verification examples use `jq` and Foundry's `cast`.
- Docker-based multi-node testnets need Docker 24+ and Compose v2.
- Many repos keep end-to-end scripts (`scripts/*e2e*.sh`, `tests/`); read them for working examples of write paths before inventing your own.
