# Security — Static Analysis & Review Checklist

Solidity is security-critical by default here. A security pass is **static analysis + a manual review against the checklist below + tests that encode the invariants** — not just running Slither and reading its output.

## Slither (static analysis)

Slither understands Foundry projects natively (via crytic-compile). Run from the project root:

```bash
slither .                              # analyse the whole project
slither src/Vault.sol                  # a single file
slither . --checklist                  # markdown checklist output (good for PRs)
slither . --print human-summary        # high-level per-contract summary
slither . --print contract-summary     # functions, state vars, modifiers
slither . --exclude-informational      # drop noise; keep medium/high
slither . --filter-paths "lib/|test/"  # ignore dependencies and tests
```

Triage every finding — do not blanket-suppress. To silence a *reviewed* false positive, either `slither.db.json` triage or an inline `// slither-disable-next-line <detector>` with a comment explaining why. Keep a `slither.config.json` for shared settings.

Detectors that map to real, high-impact bugs (never ignore without proof it's safe): `reentrancy-eth`, `reentrancy-no-eth`, `arbitrary-send-eth`, `arbitrary-send-erc20`, `unchecked-transfer`, `unprotected-upgrade`, `suicidal`, `delegatecall-loop`, `incorrect-equality` (strict `==` on balances), `tx-origin`, `uninitialized-state`, `weak-prng`.

Optional second tool: **Aderyn** (`cargo install aderyn` or `npm i -g @cyfrin/aderyn`) — `aderyn .` writes a `report.md`. Different detector set; useful as a cross-check, not a replacement.

## Manual review checklist

### Checks-Effects-Interactions & reentrancy
- [ ] State updated **before** external calls (CEI). No balance/accounting write after a `.call`/transfer/token move.
- [ ] External calls (ETH sends, ERC-20/721/1155 transfers, hooks, callbacks) identified — any of them can re-enter.
- [ ] Reentrancy guard (`nonReentrant`) on functions that move value and can't be fully CEI, incl. **cross-function** and **read-only** reentrancy (view functions read during a callback).
- [ ] ERC-777 / tokens with transfer hooks and ERC-721 `onERC721Received` considered as reentrancy vectors.

### Access control
- [ ] Every privileged function (`onlyOwner`/roles/`initializer`) actually carries the modifier — grep for state-changing externals without one.
- [ ] `initialize()` on upgradeable contracts is protected (`initializer`) and can't be front-run; implementation is disabled (`_disableInitializers()` in the constructor).
- [ ] No `tx.origin` for auth. Ownership transfer is two-step (`Ownable2Step`) where it matters.

### Arithmetic & value handling
- [ ] Solidity ≥0.8 overflow checks not defeated by an `unchecked` block that can actually overflow.
- [ ] Rounding direction favors the protocol; no division-before-multiplication precision loss.
- [ ] ETH transfers use `.call{value:}` with the return value checked (not `.transfer`/`.send`).
- [ ] ERC-20s handled with SafeERC20 (non-standard tokens: no return value, fee-on-transfer, rebasing) — balance checked by *delta*, not by the amount argument.

### External integrations & oracles
- [ ] Price/oracle reads are manipulation-resistant (no spot AMM reserves as a price; use TWAP/Chainlink with staleness + min/max checks).
- [ ] Return values of low-level calls checked; failure handled deliberately.
- [ ] Assumptions about a called contract's behavior hold under a malicious implementation.

### Denial of service & griefing
- [ ] No unbounded loops over user-controlled arrays in state-changing paths (gas-grief / block-stuffing).
- [ ] Pull-over-push for payments; one failing recipient can't brick the whole distribution.

### Upgradeability & storage
- [ ] Storage layout preserved across upgrades (no reordered/removed vars; use gaps or namespaced storage).
- [ ] `delegatecall` targets trusted; no user-controlled implementation.

### Hygiene (matches this repo's Solidity rule)
- [ ] Pragma **pinned** (`pragma solidity 0.8.24;`, not `^0.8.0`).
- [ ] Events emitted for every state change that off-chain systems track.
- [ ] Custom errors over `require` strings for gas + clarity; revert reasons meaningful.
- [ ] No leftover `console.log`, no hardcoded addresses/keys, no commented-out code.

## Turn findings into tests

For every real issue, add a test that fails on the vulnerable code and passes after the fix (regression test — required in the same PR by repo rules):

```solidity
// Proves the deposit/withdraw path resists reentrancy.
function test_WithdrawReentrancyBlocked() public {
    ReentrantAttacker atk = new ReentrantAttacker(vault);
    vm.deal(address(atk), 1 ether);
    atk.deposit{value: 1 ether}();
    vm.expectRevert();           // guard or CEI must stop the re-entrant call
    atk.attack();
    assertEq(address(vault).balance, 1 ether);   // nothing drained
}
```

Encode discovered invariants as `invariant_*` tests (see `references/testing.md`) so the property is checked against random call sequences, not just the one exploit you thought of.

## Reporting

When asked to "audit"/"review", produce per-finding: **severity** (critical/high/medium/low/informational), the affected `file:line`, why it's exploitable (a concrete scenario), a proof-of-concept test where feasible, and a concrete fix. Don't report a vulnerability you couldn't substantiate — say what you checked and what remains unverified.
