# Precompiles, params and build-time inputs

## Standard cosmos/evm precompile addresses

Source of truth: `x/vm/types/precompiles.go` in cosmos/evm (`AvailableStaticPrecompiles`). Verified against tag v0.7.3; the addresses have been stable since v0.4.

| Address | Precompile | What it exposes to Solidity |
|---------|-----------|-----------------------------|
| `0x…0100` | P256 | secp256r1 signature verification (RIP-7212) |
| `0x…0400` | Bech32 | `bech32ToHex(string)`, `hexToBech32(address,string)` |
| `0x…0800` | Staking | `delegate`, `undelegate`, `redelegate`, `createValidator`, `validators(status,page)`, `delegation(addr,val)` |
| `0x…0801` | Distribution | `withdrawDelegatorRewards`, `claimRewards`, `setWithdrawAddress`, `delegationRewards`, `communityPool()` |
| `0x…0802` | ICS20 | IBC `transfer(...)`, `denom(hash)`, `denoms(page)` (ERC20 ↔ IBC conversion goes only through here since v0.6) |
| `0x…0803` | Vesting | constant still reserved; the precompile is not shipped in current `precompiles/` |
| `0x…0804` | Bank | `balances(address)`, `supplyOf(address)`, `totalSupply()` (ERC20-address keyed) |
| `0x…0805` | Gov | `submitProposal`, `vote`, `voteWeighted`, `deposit`, `getProposal(s)`, `getParams()`, `getTallyResult` |
| `0x…0806` | Slashing | `getSigningInfo(s)`, `getParams()`, `unjail` |
| `0x…0807` | ICS02 (v0.7+) | IBC light-client ops: `getClientState`, `updateClient`, `verifyMembership` |
| `0xEeee…EEeE` | WERC20 for the native token | ERC20 view of the bank balance, plus `deposit()` / `withdraw()`; configured in `erc20.native_precompiles` and `erc20.token_pairs` |

`0x…` is 30 zero nibbles, e.g. `0x0000000000000000000000000000000000000800`. Standard Ethereum precompiles (`0x01`–`0x0a`, plus Prague additions) are always active.

A precompile is only callable if its address is in the EVM module's `active_static_precompiles` param, and that list **must stay lexicographically sorted** (cosmos/evm rejects unsorted lists at genesis and in param changes). `erc20.dynamic_precompiles` / `native_precompiles` govern the ERC20 ones.

## Custom precompiles in the chain you are in

Chains add their own precompiles for app-specific modules. Find them from the repo, never from memory:

```bash
grep -rn 'PrecompileAddress\s*=' --include=*.go precompiles/ x/ app/ 2>/dev/null   # address constants
grep -rn 'active_static_precompiles\|AvailableStaticPrecompiles\|WithStaticPrecompiles' app/ 2>/dev/null
find . -name abi.json -path '*precompile*' | sort                                   # one ABI per precompile
```

Conventions you will see: addresses in a dedicated range above the standard ones (e.g. `0x…1000+`), an `abi.json` next to the Go package (v0.7 requires it to match the methods exactly), and a twin Cosmos `MsgServer` in `x/<module>` for the same actions. When you add or move one: keep the list sorted, add it to the default genesis, and treat it as a consensus-breaking change.

## Reading an ABI

```bash
# Every function with its signature and mutability (works for cosmos/evm's and custom abi.json)
jq -r '(.abi // .)[] | select(.type=="function")
  | "\(.stateMutability)\t\(.name)(\([.inputs[].type]|join(",")))"' precompiles/bank/abi.json

cast sig "delegate(address,string,uint256)"        # 4-byte selector, to match raw calldata
cast calldata-decode "delegate(address,string,uint256)" 0x…   # decode an input you captured
```

Struct-returning getters need the exact tuple type (copy it from `abi.json`), or call without an output type and decode with `cast abi-decode`.

## Calling precompiles with `cast` (local node only)

```bash
export ETH_RPC_URL=http://127.0.0.1:8545      # a node you started; see references/localnet.md
```

Read-only probes (always allowed). Signatures taken from the v0.7.3 ABIs:

```bash
cast call 0x0000000000000000000000000000000000000804 "totalSupply()((address,uint256)[])"
cast call 0x0000000000000000000000000000000000000804 "balances(address)((address,uint256)[])" 0x<hex account>
cast call 0x0000000000000000000000000000000000000400 "hexToBech32(address,string)(string)" 0x<hex account> cosmos   # prefix from the repo
cast call 0x0000000000000000000000000000000000000801 "communityPool()((string,uint256,uint8)[])"
cast call 0x0000000000000000000000000000000000000805 "getParams()" | cast abi-decode "getParams()((int64,(string,uint256)[],int64,string,string,string,string,string,string,int64,string,(string,uint256)[],bool,bool,bool,string))" -
cast call 0x0000000000000000000000000000000000000800 \
  "validators(string,(bytes,uint64,uint64,bool,bool))" "BOND_STATUS_BONDED" "(0x,0,10,false,false)"
```

A fresh chain returns zeros and empty arrays; that still proves the precompile is active. `eth_getCode` on a static precompile returns `0x`, so never use it as a liveness check. If a call returns no data or fails to decode, first check the address is in `active_static_precompiles` (below) before debugging the call.

Writes (`delegate`, `vote`, `transfer`, custom `register*` / `create*`) are transactions: on the localnet only, from a key generated for that localnet (`--algo eth_secp256k1`), with normal `cast send` usage. Precompile errors come back as reverts with a reason string; read it rather than retrying with different values. Many chains keep e2e scripts that exercise write paths through both the Cosmos and EVM door; read those first.

Note `msg.sender` semantics: staking/distribution/gov precompiles take the delegator/voter address as an explicit first argument and check it equals the caller (or an approved contract). Calling them *from a contract* requires the user to have authorized that contract.

## Params: genesis vs governance vs build time

| Kind | Where it lives | How it changes | How to read it |
|------|----------------|----------------|----------------|
| Custom module params (`x/<module>`) | `proto/<module>/…/params.proto`, defaults in `x/<module>/types/params.go` | genesis, then `MsgUpdateParams` via governance | `<appd> query <module> params` |
| Standard SDK module params (staking, gov, mint, slashing, distribution) | same pattern inside the SDK | genesis, then governance | `<appd> query staking params`, `… gov params`, … |
| EVM params (cosmos/evm `x/vm`) | genesis `app_state.evm.params` (`evm_denom`, `active_static_precompiles`, `access_control`, `extra_eips`, `evm_channels`) | genesis, then governance | `<appd> query evm params` |
| ERC20 params and token pairs (`x/erc20`) | genesis `app_state.erc20` | governance proposals (`RegisterERC20`, `ToggleConversion`) | `<appd> query erc20 params`, `… erc20 token-pairs` |
| Fee market (`x/feemarket`) | genesis `app_state.feemarket.params` (`no_base_fee`, `base_fee`, `min_gas_price`, elasticity) | genesis, then governance | `<appd> query feemarket params` |
| Consensus params (block gas, evidence, validator pubkey types) | genesis `consensus.params` | governance (`x/consensus` `MsgUpdateParams`) | `<appd> query consensus params` |
| Build-time inputs (version, commit, power reduction, chain-specific `ldflags -X` values) | `Makefile` `ldflags` / `app/*.go` package vars | **only by building a new binary**; every validator must run the same one | `<appd> version --long` |
| Node config (ports, pruning, min gas price, JSON-RPC APIs, EVM chain id) | `config.toml`, `app.toml`, `client.toml` in the home | per node, restart required; not consensus | read the files |

Against a local node:

```bash
NODE=tcp://127.0.0.1:26657
$APPD query evm params --node $NODE -o json | jq '.params.active_static_precompiles, .params.evm_denom'
$APPD query feemarket params --node $NODE -o json | jq .params
$APPD query erc20 token-pairs --node $NODE -o json | jq .
$APPD query staking params --node $NODE -o json | jq .params.bond_denom
$APPD query consensus params --node $NODE -o json | jq .params.block
$APPD version --long | sed -n '1,30p'
```

Rules:

- A value that must be identical on every validator (anything in genesis or baked at build time) is consensus state. Changing it on one node forks that node.
- Build-time values are fixed with `go build -ldflags "-X <module>/app.someVar=<value>"`; the `Makefile` shows which names exist. Do not add a flag, env var or config key for something that must be consensus-wide.
- Decimals: 18-decimal chains are the simple path. 6-decimal base denoms work in cosmos/evm but involve a conversion layer (`x/precisebank` through v0.6, dropped in v0.7 for 18-decimal chains) and change what `balances()` and gas prices look like; read the chain's `evm_denom` and `denom_metadata` before reasoning about amounts.
- EVM chain id (`evm-chain-id` in `app.toml`, cosmos/evm ≥ v0.5) is distinct from the Cosmos `chain-id` string; EIP-712 signing uses the numeric one.

For a local experiment, change genesis under the localnet home before first start. Never edit a shared or production genesis, its ceremony inputs, or defaults in code that would ship to a real network, without the user's explicit approval (safety gate in `SKILL.md`).
