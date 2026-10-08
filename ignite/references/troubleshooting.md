# Testing and Troubleshooting

## Tests

```bash
go test ./x/...                       # keeper/types unit tests Ignite scaffolds (verified green on a fresh v29.10.1 chain)
go test ./app/...                     # app wiring + simulation tests (sim_test.go, sim_bench_test.go); slower
ignite chain simulate                 # simulation testing via Ignite (from --help; not exercised)
ignite chain lint                     # golangci-lint (from --help; not exercised)
```

Scaffolded tests cover genesis round-trips, CRUD msg servers, queries, and params. `scaffold message` and `scaffold query` generate **no test file**: add one next to the new `msg_server_*.go` / `query_*.go`. Simulation stubs (`simulation/*.go`) are generated per message; real handlers often need them updated or the app simulation fails (`--no-simulation` skips them).

End-to-end smoke test against `serve` (verified):

```bash
<app>d tx <module> create-post hello world --from alice --chain-id <chain> -y
sleep 6 && <app>d q <module> list-post -o json
```

## Common failures

| Symptom | Cause | Fix |
|---|---|---|
| `go: github.com/bufbuild/buf@vX requires go >= 1.26.7 (running go 1.25.2; GOTOOLCHAIN=local+path)` during `scaffold chain` | Go older than what the newest `buf` tool needs. Ignite pins `GOTOOLCHAIN=local+path`, so Go will not auto-download a newer toolchain. | Install a current Go (docs: ≥ 1.26.7) and rerun. Verified fix with Go 1.26.8. |
| `unknown block type: tool` when Ignite reads `go.mod` | Ignite ≤ v28 predates the Go 1.24 `tool` directive. | Use Ignite v29+, or build the chain with `go build ./cmd/<app>d`. |
| On v30, `ignite chain serve` starts a gno chain / `ignite chain build` prints gno help | v30 moved Cosmos commands under `ignite cosmos`. | `ignite cosmos chain serve`, or pin `v29.10.1`. |
| Proto changes not reflected in Go | Generation skipped (`--skip-proto`) or edits to generated files. | `ignite generate proto-go`; never edit `*.pb.go`. |
| buf cannot resolve an import (`cosmos/...`, `gogoproto`, a third-party proto) | Missing dependency in `buf.yaml`/`buf.lock` or offline BSR. | Add the dep to `buf.yaml` `deps`, `buf dep update` (older buf: `buf mod update`), or retry with `--enable-proto-vendor`. `ignite doctor` repairs known buf config drift. |
| Weird caching after switching branches or Ignite versions | Stale build/proto cache. | Rerun with `--clear-cache`. |
| Address/port already in use | Another node, or a previous `serve`, still bound to 26657/1317/9090/4500. | Stop only your own stale process, or move ports via `validators[0].app/config` and `faucet.port`. |
| New module compiles but is missing at runtime: queries 404, `unknown message`, genesis not initialised | Module not in `app_config.go` (blank import, module config entry, `InitGenesis`/`BeginBlockers`/`EndBlockers` order) or keeper not in the `depinject.Inject` call in `app.go`. Happens when the scaffolder could not find its placeholders. | Compare against a fresh scaffold of the same Ignite version and copy the wiring. Use `scaffold module --require-registration` so this fails loudly. |
| depinject error at startup (wording varies; not reproduced here) | A keeper field asked for in `app.go` that no module provides, or a module's `depinject.go` `ModuleInputs` wants a keeper not wired (e.g. the `--dep bank` interface without bank's keeper exposed). | Read `x/<module>/module/depinject.go` `ModuleInputs`/`ModuleOutputs`; make sure each input is provided by a module listed in `app_config.go`. |
| `bonded` errors at init | Validator `bonded` is < 1000000 or more than that account's balance, or wrong denom after changing `bond_denom`. | Fix balances in `accounts`, or the genesis `bond_denom`. |
| Map help says `q <module> show-post` but there is no such command | Help text is older than the AutoCLI templates. | Generated query commands are `get-<name>` and `list-<name>`; check `<app>d q <module> --help`. |
| A scaffolded module can mint and burn | `scaffold module` gives the new module account `Minter`, `Burner`, `Staking` in `app_config.go`. | Trim the permissions in the `moduleAccPerms` list before shipping. |

`ignite doctor` (v30: `ignite cosmos doctor`) checks the chain `config.yml`, the buf config version, and legacy plugin config files. On a fresh v29 chain all three report OK (verified).

## When the chain outgrows Ignite

Ignite is strongest at day 0 to day N of a chain built from its template. Signs you have outgrown it:

- The app wiring has been rewritten (custom ante handlers, EVM, non-template keepers), so scaffolders can no longer find their placeholders and every scaffold needs manual repair.
- Builds and local nets already run through `go build`, a `Makefile`, docker-compose, or scripts, and `chain serve` is a second, unmaintained path.
- The chain needs an SDK version the current Ignite major does not target yet.

Then: keep Ignite only for what still works (often `generate proto-go`/`openapi`, or scaffolding into a fresh scratch chain and copying the files across), build with plain Go, and run nodes with the binary's own `init` / `genesis` / `start`. Document which path is canonical so new contributors do not start with a `chain serve` that no longer matches production. Example: a production Cosmos EVM chain that started from `ignite scaffold chain` now builds with `go build` and keeps `ignite chain serve` as an optional path, because an older Ignite failed with `unknown block type: tool` on its `go.mod`.
