# Running AminiChain locally

Two supported paths, both from the repo's own tooling. Pick the single-validator script for day-to-day work; use the docker compose localnet only when you need several nodes.

| Path | Nodes | Binds to | Use for |
|------|-------|----------|---------|
| `scripts/local-node.sh` (or `make localnet`) | 1 validator | `127.0.0.1` only, non-default ports | precompile calls, contract tests, quick e2e |
| docker compose localnet (`deploy/docker/`) | seed + validators + fullnodes | Docker published ports on the host | multi-node behaviour, genesis ceremony flow |

Read `docs/LOCALNET.md` (annotated walkthrough) and `deploy/docker/README.md` for the current details; the values below are the defaults in the scripts as of 2026-10-08.

## Why a bare `init` + `start` does not boot

A fresh `aminichaind init` leaves cosmos/evm's own default `evm_denom` (`aatom`) in genesis and an empty `bank.denom_metadata`. At boot the EVM module's `InitGenesis` looks up denom metadata for `evm_denom` and panics:

```
denom metadata aatom could not be found
```

`scripts/local-node.sh` fixes this by pointing `evm_denom` at the chain's own token `aamini` (display `AMINI`, 18 decimals) and seeding its metadata, and it also zeroes the fee market for a fee-free dev chain. Use the script rather than reproducing the patch by hand.

## Path 1: single validator with `scripts/local-node.sh`

```bash
make localnet                       # wipe and start fresh (= scripts/local-node.sh --reset)
scripts/local-node.sh               # reuse the existing home if its genesis parses, else init
LOCALNET_RESET=1 scripts/local-node.sh   # same as --reset
```

What it does:

1. Builds `./cmd/aminichaind` to a temp binary (or uses `AMINICHAIND_BIN` if set).
2. Uses an isolated home (default `/tmp/aminichain-localnet`, override with `LOCALNET_HOME`), chain id `aminichain-localnet-1` (`LOCALNET_CHAIN_ID`), a validator key in the **`test` keyring** (throwaway, unencrypted).
3. Funds and self-delegates the validator, patches genesis (denom metadata, `evm_denom`, zero fee market), sets the EVM chain id in `app.toml`, runs `validate-genesis`.
4. `exec`s `aminichaind start` **in the foreground**, with every listener on loopback and on ports chosen not to collide with a default node:

| Listener | Address |
|----------|---------|
| CometBFT RPC | `tcp://127.0.0.1:36657` |
| P2P | `tcp://127.0.0.1:36656` |
| ABCI proxy | `tcp://127.0.0.1:36658` |
| gRPC | `127.0.0.1:19090` |
| EVM JSON-RPC | `http://127.0.0.1:18545` |
| EVM WebSocket | `ws://127.0.0.1:18546` |
| REST API | disabled |

EVM chain id is `1000000`. The script prints the exact verification commands when it starts; prefer those over the examples here if they differ.

Verify from a second terminal:

```bash
BIN=/tmp/aminichaind-localnet           # the binary the script built; or $(which aminichaind)
$BIN status --node tcp://127.0.0.1:36657 | jq .sync_info.latest_block_height
cast chain-id --rpc-url http://127.0.0.1:18545
cast block-number --rpc-url http://127.0.0.1:18545
```

**Stop:** Ctrl-C in the terminal running it. If it was backgrounded, stop that process only (find it with `pgrep -af 'aminichain-localnet'`); never kill an unrelated `aminichaind`. **Reset:** run with `--reset` or `make localnet`; or delete the home directory while it is stopped.

Pitfalls:

- A plain run (no `--reset`) is idempotent on purpose: it keeps keys and state. If the home has a genesis but no `validator` key, it stops and tells you to use `--reset`.
- `eth_getCode` can return `0x` for static precompiles even when they are active. Use `eth_call` / `cast call` as the liveness probe.
- "address already in use": another localnet is running on the same ports. Stop it, or change the ports in a copy of the script rather than editing a shared one.

## Path 2: docker compose localnet

```bash
make docker-build-all                          # base + role images
./deploy/docker/aminictl init localnet --apply # generate compose, run genesis init, start
./deploy/docker/aminictl check                 # health checks
./deploy/docker/aminictl test-tx               # one tx through each door
./deploy/docker/aminictl stop
```

Make equivalents: `make docker-run-localnet`, `make docker-status-localnet`, `make docker-logs-localnet`, `make docker-stop-localnet`, and `make docker-clean-localnet` (also removes volumes, so the next start runs a fresh genesis). The default topology is 1 seed, 2 validators, 2 fullnodes; change it with `aminictl init localnet --validators N --fullnodes N`.

**Ports and exposure.** The generated compose file publishes the standard ports (RPC 26657, REST 1317, gRPC 9090, EVM JSON-RPC 8545, and offsets for a second fullnode) in `"host:container"` form, which Docker binds on **all host interfaces**. On a shared network that exposes a dev chain with dev keys. If that matters, add a local override that publishes as `127.0.0.1:<port>:<port>`, or use Path 1. These ports also collide with any other Cosmos or EVM node on the host.

**Do not hand-edit** `deploy/docker/compose/docker-compose.yml`: it is generated by `deploy/docker/scripts/generate-compose.sh` and CI fails if it drifts (`make docker-compose-check`). Regenerate with `make docker-generate-compose`.

Production-oriented commands (`*-prod` make targets, `aminictl init prod-*`, production presets) are behind the safety gate in `SKILL.md`.

## IBC between two local chains

A two-chain IBC tracer script (`scripts/ibc-tracer.sh`) is proposed but was not on the default branch as of 2026-10-08. When present, read its header for prerequisites (it relays one ICS-20 transfer between two localnets) and run it only against local chains.
