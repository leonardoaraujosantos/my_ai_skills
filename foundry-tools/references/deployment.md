# Deployment, Anvil & Keystores

> ⚠️ **Safety gate (from `SKILL.md`).** Anything that broadcasts a transaction or deploys a contract — `forge script --broadcast`, `forge create`, `cast send` — requires explicit user approval **in the conversation**. Everything below is written to rehearse on a local/fork sandbox first and broadcast only last, after a green simulation and a yes.

## Anvil — local sandbox chain (always safe)

```bash
anvil                                  # chain id 31337, 10 accounts each with 10000 ETH
anvil --fork-url "$ETH_RPC_URL"        # fork live mainnet state locally
anvil --fork-url "$ETH_RPC_URL" --fork-block-number 19000000
anvil --accounts 5 --balance 1000      # customise dev accounts
anvil --port 8545 --silent             # quiet, explicit port
```

Anvil prints its dev accounts *and their private keys* on startup — these are well-known test keys, fine for local use, never for real funds. Broadcasting **to anvil** is the correct way to rehearse a deploy end-to-end before touching a real network.

Useful anvil-only cheats via `cast rpc`:

```bash
cast rpc anvil_setBalance 0xADDR 0xDE0B6B3A7640000    # fund an address
cast rpc anvil_impersonateAccount 0xWHALE             # send as any address
cast rpc evm_increaseTime 3600 && cast rpc evm_mine   # advance time
cast rpc anvil_setStorageAt 0xADDR 0xSLOT 0xVALUE
```

## Deploy scripts (`forge script`) — the recommended path

Write a script in `script/*.s.sol` that inherits `forge-std/Script.sol`. Wrap the state-changing calls between `vm.startBroadcast()` and `vm.stopBroadcast()`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;
import {Script} from "forge-std/Script.sol";
import {Vault} from "../src/Vault.sol";

contract DeployVault is Script {
    function run() external returns (Vault vault) {
        vm.startBroadcast();          // uses the --account / sender you pass on the CLI
        vault = new Vault();
        vm.stopBroadcast();
    }
}
```

Run it in three escalating stages:

```bash
# 1. DRY RUN — simulate locally, no chain, no state written (ALWAYS ALLOWED)
forge script script/Deploy.s.sol:DeployVault

# 2. SIMULATE AGAINST A NETWORK — still no broadcast; checks nonces/gas against real state
forge script script/Deploy.s.sol:DeployVault --rpc-url "$ETH_RPC_URL"

# 3. BROADCAST — GATED. Only after approval. Signs from an encrypted keystore account:
forge script script/Deploy.s.sol:DeployVault \
  --rpc-url "$ETH_RPC_URL" --account my-deployer --broadcast
```

Add `--verify` to step 3 to verify on the block explorer in the same run (needs `[etherscan]` config / API key). Broadcast artifacts (addresses, tx hashes) are written under `broadcast/`.

Rehearse the whole thing on a fork first:

```bash
anvil --fork-url "$ETH_RPC_URL" &      # terminal 1
forge script script/Deploy.s.sol:DeployVault \
  --rpc-url http://localhost:8545 --account my-deployer --broadcast   # safe: local fork
```

## `forge create` — one-off deploy (also gated)

```bash
# GATED — needs approval. Prefer a script for anything repeatable/auditable.
forge create src/Vault.sol:Vault --rpc-url "$ETH_RPC_URL" --account my-deployer \
  --constructor-args 0xOWNER 100
```

## Keystores — never put a raw private key on the CLI

```bash
cast wallet import my-deployer --interactive     # paste the key once; stored encrypted
cast wallet list                                 # list keystore account names
cast wallet address --account my-deployer        # show its address
```

Then reference it everywhere with `--account my-deployer` (Foundry prompts for the password). This keeps keys out of shell history, env vars, and scripts. For CI, prefer a hardware wallet (`--ledger` / `--trezor`) or a scoped, short-lived key injected as a secret — and keep broadcasting out of untrusted CI entirely.

## Verification

```bash
# GATED (publishes source). Standalone verify of an already-deployed contract:
forge verify-contract 0xADDR src/Vault.sol:Vault \
  --chain mainnet --watch \
  --constructor-args $(cast abi-encode "constructor(address,uint256)" 0xOWNER 100)
```

## Pre-deploy checklist

Before requesting approval to broadcast, confirm:

- [ ] `forge test` green, including fuzz/invariant and a **fork test** of the deploy path
- [ ] `forge build --sizes` under the 24576-byte contract limit
- [ ] Slither run and findings triaged (`references/security.md`)
- [ ] Constructor args and `owner`/admin addresses double-checked (not a dev/anvil address)
- [ ] Pragma pinned; compiler version and optimizer settings in `foundry.toml` match what will be verified
- [ ] Deploy rehearsed on an anvil fork with `--broadcast` and the resulting state inspected
- [ ] The exact broadcast command shown to the user and explicitly approved
