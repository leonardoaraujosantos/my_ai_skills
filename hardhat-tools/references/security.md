# Security on a Hardhat Project

The security discipline is identical to `foundry-tools/references/security.md` — this file covers the Hardhat-specific *tooling*; the review substance (checks-effects-interactions, reentrancy, access control) is the same and summarized below so this skill is self-contained. A security pass is **static analysis + manual review against the checklist + tests that encode the invariants**, not just running a tool.

## Slither on a Hardhat project

Slither compiles via crytic-compile, which understands Hardhat. Run from the project root:

```bash
slither .                          # analyse the whole project (uses hardhat to compile)
slither . --checklist              # markdown output for a PR
slither . --print human-summary
slither . --filter-paths "node_modules/|test/"   # ignore deps and tests
slither contracts/Vault.sol        # a single file
```

If Slither can't pick the compiler, pin solc for the project (`solc-select install 0.8.28 && solc-select use 0.8.28`) so it matches `hardhat.config`'s `solidity.version`. On failures, `npx hardhat compile` first — if Hardhat can't compile, Slither can't either.

High-impact detectors to never dismiss without proof it's safe: `reentrancy-eth`, `reentrancy-no-eth`, `arbitrary-send-eth`, `arbitrary-send-erc20`, `unchecked-transfer`, `unprotected-upgrade`, `suicidal`, `delegatecall-loop`, `incorrect-equality`, `tx-origin`, `uninitialized-state`, `weak-prng`. Triage the rest; suppress only a reviewed false positive with an inline `// slither-disable-next-line <detector>` and a reason.

Optional cross-check: **Aderyn** (`aderyn .` → `report.md`) — a different detector set, runs on Hardhat projects too.

## Manual review checklist (condensed)

- **CEI / reentrancy:** state updated **before** external calls; `nonReentrant` where value moves and CEI isn't possible; consider cross-function and read-only reentrancy; token transfer hooks (ERC-777/721/1155) are reentrancy vectors.
- **Access control:** every privileged function carries its modifier; `initialize()` is `initializer`-guarded and the implementation `_disableInitializers()`; no `tx.origin` auth; two-step ownership.
- **Arithmetic & value:** no unsafe `unchecked`; rounding favors the protocol; ETH via checked `.call{value:}`; ERC-20 via SafeERC20 with **delta** balance checks (fee-on-transfer/rebasing/no-return tokens).
- **Oracles/integrations:** no spot-AMM price as truth (TWAP/Chainlink with staleness + bounds); low-level call returns checked; safe under a malicious callee.
- **DoS:** no unbounded loops over user arrays in state-changing paths; pull-over-push payments.
- **Upgrade/storage:** layout preserved across upgrades; `delegatecall` targets trusted.
- **Hygiene (repo rule):** pragma **pinned**; events for tracked state changes; custom errors; no leftover `console.log`, hardcoded addresses, or keys.

Full explanations and PoC patterns: `foundry-tools/references/security.md`.

## Turn findings into tests (required by repo rules)

Every real issue gets a regression test in the same PR — one that fails on the vulnerable code and passes after the fix:

```ts
it("blocks re-entrant withdraw", async function () {
  const { ethers } = await network.getOrCreate("default");     // HH3; HH2: const { ethers } = require("hardhat")
  const vault = await ethers.deployContract("Vault");
  const attacker = await ethers.deployContract("ReentrantAttacker", [await vault.getAddress()]);
  await attacker.seed({ value: ethers.parseEther("1") });
  await expect(attacker.attack()).to.be.reverted;              // guard/CEI stops the re-entry
  expect(await ethers.provider.getBalance(await vault.getAddress())).to.equal(ethers.parseEther("1"));
});
```

Where a property must hold across arbitrary call sequences, prefer **Solidity invariant tests** (`hardhat test solidity`, Foundry-style) over a single scripted exploit — see `foundry-tools/references/testing.md`.

## Hardhat ↔ Foundry interop

Install `@nomicfoundation/hardhat-foundry` to share one project between both toolchains: Foundry-style `forge test` for fast in-EVM unit/fuzz/invariant tests, Hardhat for TS integration tests, forking, and Ignition deployment. This lets you use `foundry-tools` (fuzz/invariant/gas snapshots) and `hardhat-tools` (Ignition, TS/viem, verify) on the same contracts. Keep remappings and `solidity.version` consistent across `foundry.toml` and `hardhat.config` so both compile identically.

## Reporting

When asked to "audit"/"review", report per finding: **severity** (critical/high/medium/low/informational), the affected `file:line`, a concrete exploit scenario, a PoC test where feasible, and a concrete fix. Don't assert a vulnerability you couldn't substantiate — state what you checked and what remains unverified.
