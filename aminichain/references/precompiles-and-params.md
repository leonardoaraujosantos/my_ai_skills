# Precompiles, params and build-time inputs

## Precompile addresses

The authoritative list is `staticPrecompileAddresses` in `app/evm.go`; each address constant lives in `precompiles/<name>/*.go` as `PrecompileAddress`, and each ABI in `precompiles/<name>/abi.json`. As of 2026-10-08:

| Address | Package | Purpose |
|---------|---------|---------|
| `0x0000000000000000000000000000000000001900` | `precompiles/registry` | Oracle registry: register, update, activate/deactivate oracles, rates, heartbeats |
| `0x0000000000000000000000000000000000001901` | `precompiles/job` | Job manager: create jobs, oracle ack, submit result, creator accepts result; list pending/leased jobs |
| `0x0000000000000000000000000000000000001902` | `precompiles/compute` | Compute registry: register, update, deactivate compute offers |
| `0x0000000000000000000000000000000000001903` | `precompiles/content` | Content registry: register and look up content records |
| `0x0000000000000000000000000000000000001904` | `precompiles/mdi` | MDI registry: register and look up MDI records |
| `0x0000000000000000000000000000000000001908` | `precompiles/hostregistry` | Host registry: register, heartbeat, deregister hosts; list hosts by owner |

The same list also activates the standard Ethereum precompiles (`0x01` to `0x0a`), P256 (`0x0100`) and Bech32 (`0x0400`). A precompile is only callable if its address is in the EVM module's `active_static_precompiles` param; the app's default genesis carries the list.

The list must stay lexicographically sorted (cosmos/evm rejects unsorted lists). Adding or removing an address changes consensus behaviour: follow `AGENTS.md`, and read the comments at the top of `app/evm.go` before touching it.

Per-precompile CLI docs: `docs/OracleRegistry.CLI.md`, `docs/JobManager.CLI.md`, `docs/ComputeRegistry.CLI.md`, `docs/ContentRegistry.CLI.md`, `docs/MdiRegistry.CLI.md`, plus `docs/PRECOMPILES.md`.

## Reading an ABI

```bash
# Every function with its signature and mutability
jq -r '(.abi // .)[] | select(.type=="function")
  | "\(.stateMutability)\t\(.name)(\([.inputs[].type]|join(",")))"' precompiles/job/abi.json

cast sig "listByOwner(address)"          # 4-byte selector, e.g. to match raw calldata
cast calldata-decode "getJob(string)" 0x...   # decode an input you captured
```

Most IDs are `string`; the host registry uses `bytes32` host IDs and `address` owners.

## Calling precompiles with `cast` (local node only)

Set the RPC once, and only ever to a node you started locally (see `references/localnet.md`):

```bash
export ETH_RPC_URL=http://127.0.0.1:18545   # scripts/local-node.sh default
```

Read-only calls (always allowed):

```bash
cast call 0x0000000000000000000000000000000000001900 "getOracleCount()(uint256)"
cast call 0x0000000000000000000000000000000000001900 "listOracles()(string[])"
cast call 0x0000000000000000000000000000000000001901 "getPendingJobs()(string[])"
cast call 0x0000000000000000000000000000000000001902 "listCompute()(string[])"
cast call 0x0000000000000000000000000000000000001903 "listContent()(string[])"
cast call 0x0000000000000000000000000000000000001904 "listMdi()(string[])"
cast call 0x0000000000000000000000000000000000001908 "listByOwner(address)(bytes32[])" 0x1111111111111111111111111111111111111111
```

A fresh chain returns `0` and empty arrays; that still proves the precompile is active. If a call returns no data or fails to decode, first check the address is in `active_static_precompiles` (see Params below) before debugging the call itself.

For getters that return a struct (`getJob`, `getOracle`, `getCompute`, `getContent`, `getMdi`, `get`), copy the exact tuple output type from `abi.json`, or call without an output type and decode the raw return with `cast abi-decode`.

Writes (`register*`, `createJob`, `ackJob`, `submitResult`, `heartbeat`, …) are transactions. On the localnet only, and with a key generated for that localnet, they follow normal `cast send` usage. Before writing your own, read the repo's `scripts/*-e2e.sh`: they exercise the write paths through both doors and show the argument shapes the keeper validates. Many inputs are validated strictly (fail closed), so a revert usually carries a specific reason; read it rather than retrying with different values.

## Params: governance values vs build-time inputs

Chain behaviour is set in two different ways, and the difference matters:

| Kind | Where it lives | How it changes | How to read it |
|------|----------------|----------------|----------------|
| Module params (`x/aminichain`) | `proto/aminichain/aminichain/v1/params.proto`; defaults in `x/aminichain/types/params.go` | genesis, then a governance proposal; no software upgrade | `aminichaind query aminichain params` |
| EVM params (cosmos/evm `x/vm`) | genesis `app_state.evm.params` | genesis, then governance | `aminichaind query evm params` |
| Fee market params | genesis `app_state.feemarket.params` | genesis, then governance | `aminichaind query feemarket params` |
| Power reduction | `app/config.go` (`powerReduction`) | **build time only**, via ldflags | `aminichaind version --long` (`power_reduction`) |

Against the local node from `scripts/local-node.sh`:

```bash
BIN=/tmp/aminichaind-localnet
NODE=tcp://127.0.0.1:36657
$BIN query aminichain params --node $NODE --output json | jq
$BIN query evm params --node $NODE --output json | jq '.params.active_static_precompiles'
$BIN version --long | grep power_reduction
```

**Power reduction is never a runtime setting.** The binary carries a default; a different value is baked in at build time:

```bash
make install POWER_REDUCTION=1000000
# equivalent: go build -ldflags "-X aminichain/app.powerReduction=1000000" ./cmd/aminichaind
```

Every node on one network must run a binary built with the same value, which is why `version --long` prints it. Do not add a flag, env var or config key for it.

When a genesis value needs to differ for a local experiment, change it in the localnet's own `genesis.json` (under the localnet home) before first start, or via the repo's genesis tooling for that localnet. Never edit a shared or production genesis, its ceremony inputs, or the defaults in code, without the user's explicit approval (see the safety gate in `SKILL.md`).
