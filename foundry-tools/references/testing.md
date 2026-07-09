# Testing with Forge

Foundry tests are Solidity contracts (usually `test/*.t.sol`) that inherit `forge-std/Test.sol`. Test functions are `public`/`external` and named `test*`; a function that takes arguments is automatically **fuzzed**. Assertions come from `forge-std` (`assertEq`, `assertTrue`, `assertGt`, …). Cheatcodes come from `vm` (a special address the EVM intercepts).

## Running tests

```bash
forge test                          # everything
forge test --match-test testWithdraw        # by test-function name (regex)
forge test --match-contract VaultTest        # by contract name (regex)
forge test --match-path test/Vault.t.sol     # by file path
forge test --no-match-test invariant         # exclude by regex
forge test -vvv                     # verbosity: see below
forge test --watch                  # re-run on file change
forge test --fail-fast              # stop at first failing test
```

Verbosity ladder (each level adds more; failures print more than passes):

| Flag | Shows |
|------|-------|
| `-v` | nothing extra (default is already this) |
| `-vv` | `console.log` / emitted logs from tests |
| `-vvv` | + execution traces for **failing** tests |
| `-vvvv` | + execution traces for **all** tests, and setup traces |
| `-vvvvv` | + full state changes and storage accesses |

Reach for `-vvvv` when a test fails and you can't see why — it shows every call, its args, return data, and the revert reason.

## Cheatcodes you will use constantly

`vm.*` (from `forge-std/Vm.sol`) and helpers from `forge-std/Test.sol`:

| Cheatcode | Purpose |
|-----------|---------|
| `vm.prank(addr)` | next call is `msg.sender == addr` (one call) |
| `vm.startPrank(addr)` / `vm.stopPrank()` | all calls until stop are from `addr` |
| `vm.deal(addr, amount)` | set an address's ETH balance |
| `deal(token, addr, amount)` | (forge-std) set an ERC-20 balance by writing storage |
| `vm.warp(ts)` | set `block.timestamp` |
| `vm.roll(n)` | set `block.number` |
| `vm.expectRevert(bytes)` | assert the **next** call reverts (optionally with a specific error/selector) |
| `vm.expectEmit(...)` | assert the next call emits a specific event |
| `vm.mockCall(target, calldata, ret)` | stub an external call's return |
| `vm.load(addr, slot)` / `vm.store(addr, slot, val)` | read/write raw storage |
| `makeAddr("name")` | deterministic labeled address |
| `bound(x, lo, hi)` | (forge-std) constrain a fuzz input to a range — prefer over `vm.assume` for ranges |
| `vm.assume(cond)` | discard fuzz inputs that don't satisfy `cond` |

Minimal example:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;               // pinned pragma, per repo rule

import {Test} from "forge-std/Test.sol";
import {Vault} from "../src/Vault.sol";

contract VaultTest is Test {
    Vault vault;
    address alice = makeAddr("alice");

    function setUp() public {          // runs before EACH test
        vault = new Vault();
        vm.deal(alice, 10 ether);
    }

    function test_Deposit() public {
        vm.prank(alice);
        vault.deposit{value: 1 ether}();
        assertEq(vault.balanceOf(alice), 1 ether);
    }

    function test_WithdrawTooMuchReverts() public {
        vm.prank(alice);
        vm.expectRevert(Vault.InsufficientBalance.selector);
        vault.withdraw(1 ether);
    }
}
```

## Fuzz testing

Any test parameter is fuzzed (default 256 runs). Constrain inputs with `bound` (keeps the run) rather than `vm.assume` (discards it) when you need a range:

```solidity
function testFuzz_Deposit(uint256 amount) public {
    amount = bound(amount, 1, 100 ether);   // avoid 0 and overflow
    vm.deal(alice, amount);
    vm.prank(alice);
    vault.deposit{value: amount}();
    assertEq(vault.balanceOf(alice), amount);
}
```

Tune in `foundry.toml`: `[fuzz] runs = 1000`. A failing fuzz run prints the counterexample and stores it so re-runs replay it.

## Invariant testing

Invariants are properties that must hold after *any* sequence of calls. Name them `invariant_*`; Foundry calls random functions on "target" contracts between checks. Inherit `StdInvariant` and register targets in `setUp`.

```solidity
import {StdInvariant, Test} from "forge-std/Test.sol";

contract VaultInvariants is StdInvariant, Test {
    Vault vault;
    function setUp() public {
        vault = new Vault();
        targetContract(address(vault));
    }
    // total accounted balance can never exceed the contract's ETH
    function invariant_solvency() public view {
        assertLe(vault.totalDeposits(), address(vault).balance);
    }
}
```

Config: `[invariant] runs = 256, depth = 128`. Use **handler** contracts (a wrapper that bounds inputs and tracks ghost variables) for anything non-trivial, so the fuzzer spends calls on valid state transitions instead of reverts.

## Fork testing

Run tests against real on-chain state (live protocols, real token balances):

```solidity
function setUp() public {
    // pin a block for deterministic, cacheable results
    vm.createSelectFork(vm.rpcUrl("mainnet"), 19_000_000);
}
```

`vm.rpcUrl("mainnet")` resolves from `[rpc_endpoints]` in `foundry.toml`. Or from the CLI: `forge test --fork-url "$ETH_RPC_URL" --fork-block-number 19000000`. Forked RPC results are cached under `~/.foundry/cache`.

## Gas: reports and snapshots

```bash
forge test --gas-report              # per-function min/avg/median/max + call count
forge snapshot                       # writes .gas-snapshot (commit it)
forge snapshot --diff .gas-snapshot  # show gas delta vs the committed snapshot
forge snapshot --check               # fail if gas changed — good CI gate
```

Commit `.gas-snapshot` so gas regressions show up in review as a diff.

## Coverage

```bash
forge coverage                       # summary table (lines/statements/branches/funcs)
forge coverage --report lcov         # lcov.info for CI / codecov / genhtml
forge coverage --report debug        # show exactly which lines are uncovered
```

Coverage compiles without optimizations; if an unrelated "stack too deep" appears only under coverage, add `--ir-minimum`.

## Debugging a failure

1. Re-run the single test with `-vvvv` to get the full trace.
2. `forge test --debug testName` opens the interactive step debugger (opcode/stack/memory).
3. For a *revert without a reason*, check custom errors and `vm.expectRevert` selectors; add `console.log` (import `forge-std/console.sol`) and run at `-vv`.
4. For a mysterious on-chain tx, reproduce it with `cast run <txhash>` (see `references/cast.md`).

## CI recipe

```bash
forge fmt --check          # formatting gate
forge build --sizes        # fail if a contract exceeds the 24576-byte limit
forge test -vvv
forge snapshot --check     # gas regression gate (requires committed .gas-snapshot)
forge coverage --report lcov
```
