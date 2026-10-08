# Scaffolding and Code Generation

Spelling is v29 (`ignite scaffold …`). On v30 use `ignite cosmos scaffold …` with the same flags. File lists below were captured on 2026-10-08 from a real v29.10.1 run on a chain named `demo` (module `demo`), committing between commands and reading `git status`.

**Always commit before scaffolding.** Ignite's own help recommends it: the diff is the only reliable record of what changed, and `git checkout . && git clean -fd` is the undo. Scaffolders edit around placeholder comments; if you have hand-edited those regions, the insert can land in the wrong place or be skipped.

## Field types

`name` alone is `string`; otherwise `name:type`. From `ignite scaffold type --help`:

| Type | Go type | CLI example |
|---|---|---|
| `string`, `bool`, `int` (int64), `uint` (uint64) | scalar | `xyz`, `true`, `111` |
| `address` | string with a `scalar` address annotation (v29.0.0, #4687) | `cosmos1…` |
| `bytes` | `[]byte` | `3,2,3,5` |
| `coin` / `array.coin` (`coins`) | `sdk.Coin` / `sdk.Coins` | `10token` / `20stake` |
| `dec.coin` / `array.dec.coin` | `sdk.DecCoin(s)` | |
| `array.string`, `array.int`, `array.uint` | slices | `abc,xyz` |
| `<CustomType>` | a type you scaffolded earlier with `scaffold type` | JSON on the CLI |

Only one `coins`/`dec.coins` field per message can take multiple CLI values (AutoCLI limitation, per the help text).

## `scaffold chain`

```bash
ignite scaffold chain github.com/acme/mychain \
  --address-prefix acme --default-denom uacme --coin-type 118 [--no-module] [--minimal] [--skip-git] [--skip-proto]
```

Flags (v29.10.1 and v30.0.0-rc.2 identical): `--address-prefix` (cosmos), `--coin-type` (118), `--default-denom` (stake), `--minimal`, `--module-configs`, `--no-module`, `--params`, `-p/--path`, `--proto-dir` (proto), `--skip-git`, `--skip-proto`, `--clear-cache`. The name becomes the Go module path; the binary is `<last-path-element>d`.

Layout produced: `app/` (`app.go`, `app_config.go`, `ibc.go`, `export.go`, `genesis*.go`, sim tests), `cmd/<name>d/`, `proto/<name>/<module>/v1/{genesis,params,query,tx}.proto`, `x/<module>/{keeper,module,types}/`, `docs/static/openapi.json`, `testutil/`, `buf.yaml`, `buf.lock`, `config.yml`, `Makefile`. The address prefix, coin type, and default denom are baked into code and `config.yml`; changing them later is a manual edit, so pick them now.

`docs.ignite.com` mentions `--consumer` for Interchain Security consumer chains; it is **not** in the `scaffold chain --help` flag list of either v29.10.1 or v30.0.0-rc.2 (unverified).

## `scaffold module`

```bash
ignite scaffold module escrow --dep bank            # --dep adds expected_keepers.go interfaces; it does not install modules
ignite scaffold module oracle --ibc --ordering unordered
ignite scaffold module fees --params rate:uint,enabled:bool --require-registration
```

Observed for `scaffold module escrow --dep bank`: **modified** `app/app.go` (keeper import, `EscrowKeeper` field, added to the `depinject.Inject` list) and `app/app_config.go` (blank import of `x/escrow/module`, appended to BeginBlockers / EndBlockers / InitGenesis order after the `// chain modules` comments, a module config entry, and a **module account with `Minter`, `Burner`, `Staking` permissions**); **added** `proto/<app>/escrow/{module/v1/module.proto, v1/*.proto}` and `x/escrow/{keeper,module,types}/…`.

Review that module-account line every time: a fresh module gets mint and burn rights by default. Trim the permissions to what the module needs before it ships.

`--require-registration` makes the command fail instead of silently skipping app wiring when the placeholders in `app.go` are gone.

## CRUD: `list`, `map`, `single`

```bash
ignite scaffold list post title body                     # key = auto-increment uint64 id
ignite scaffold map balance amount:uint --index owner     # key = user-supplied index field(s)
ignite scaffold single settings maxpost:uint              # one value per module (create/update/delete, no index)
# common flags: --module <name>, --signer <field> (default creator), --no-message (store + queries only), --no-simulation
```

Observed for `list post` (and the same shape for `map`, `single`): proto `post.proto` added and `genesis/query/tx.proto` edited; keeper `msg_server_post.go`, `query_post.go` plus their `_test.go` added; `keeper.go`, `genesis.go` edited; `module/autocli.go` and `module/simulation.go` edited; `simulation/post.go` added; `types/{codec,genesis,keys}.go` and all `*.pb.go` regenerated; `docs/static/openapi.json` regenerated. `map` additionally adds `types/key_balance.go`.

Resulting CLI (verified on the running chain): `demod tx demo create-post|update-post|delete-post`, `demod q demo list-post|get-post`, `list-balance|get-balance`, `get-settings`. The `scaffold map --help` text still shows `show-post`; the generated AutoCLI command is `get-…`.

## `message`, `query`, `type`, `params`, `configs`

```bash
ignite scaffold message add-pool amount:coin active:bool --response id:uint [--module dex] [--signer owner] [-d "description"]
ignite scaffold query pool-count --response count:uint [--paginated]
ignite scaffold type pool-info name:string weight:uint    # proto message + Go type only
ignite scaffold params maxtitle:uint                      # module Params field (genesis + MsgUpdateParams)
ignite scaffold configs foo baz:uint bar:bool                # module *config* (app_config wiring), not on-chain params
```

Observed:

- `message add-pool`: `tx.proto` edited, `keeper/msg_server_add_pool.go` added (put the logic in the `AddPool` handler), `module/autocli.go`, `module/simulation.go`, `types/codec.go` edited, `simulation/add_pool.go` added. No test file is generated for a plain message: write one.
- `query pool-count`: `query.proto` edited, `keeper/query_pool_count.go` added (stub returns an empty response), AutoCLI and gateway regenerated, `openapi.json` updated.
- `params maxtitle:uint`: `params.proto`, `types/params.go` (defaults + `Validate()`), `params.pb.go`, `openapi.json`. Fill in `Validate()`; the stub accepts anything.

Other scaffolders (from `--help`, not exercised): `packet` (IBC, needs a module scaffolded with `--ibc`), `migration <module>` (store migration boilerplate), `vue`, `react`, `chain-registry`.

## `generate`

```bash
ignite generate proto-go        # .proto -> *.pb.go / *.pb.gw.go via buf (also runs implicitly on build/serve unless --skip-proto)
ignite generate openapi         # docs/static/openapi.json (path from config.yml client.openapi.path); --exclude to drop protos
ignite generate ts-client       # ts-client/ by default, -o <dir> or config.yml client.typescript.path
ignite generate composables     # TS client + Vue 3 composables
# shared flags: --enable-proto-vendor (vendor missing buf deps), --clear-cache, -p/--path, -y
```

Generated files are overwritten on the next run; never hand-edit `*.pb.go`, `openapi.json`, or `ts-client/`. `ignite chain serve --generate-clients` regenerates the configured clients on every reload.

Verified: proto-go and openapi ran implicitly during every scaffold and `serve`. Not run as standalone commands on 2026-10-08: `generate ts-client`, `composables`.
