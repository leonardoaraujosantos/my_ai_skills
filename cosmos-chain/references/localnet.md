# Running a Cosmos SDK / Cosmos EVM chain locally

Three ways to get a throwaway single-validator chain, in order of preference:

| Path | When | Notes |
|------|------|-------|
| The repo's own script or make target (`scripts/*.sh`, `local_node.sh`, `make localnet`) | It exists | Encodes the chain's denom, EVM chain id, genesis patches and ports. Always read it first. |
| `ignite chain serve` (`config.yml` at repo root) | Chain still fits the Ignite template | See the `ignite` skill. Hot reload, faucet, dev accounts. |
| Hand-rolled `init` → `genesis` → `start` (below) | Neither of the above, or you need to understand what the script does | Works on every SDK chain; cosmos/evm chains need the extra genesis patches. |

`<appd>` below is whatever lives in `cmd/` (`simd`, `evmd`, `mychaind`, …). Use an isolated `--home` so you never touch a real node's data.

## Hand-rolled single validator (any Cosmos SDK ≥ v0.50 chain)

```bash
APPD=mychaind                         # from ls cmd/
HOME_DIR=/tmp/$APPD-localnet
CHAIN_ID=localnet-1                   # cosmos/evm ≥ v0.5: any string; the EVM chain id is set separately (below)
DENOM=stake                           # read the repo: default_denom in config.yml, or bond_denom in app/ or scripts
KR=test                               # throwaway, unencrypted keyring

rm -rf "$HOME_DIR"
$APPD init localnode --chain-id "$CHAIN_ID" --home "$HOME_DIR" --default-denom "$DENOM"   # --default-denom exists on SDK ≥ v0.50
$APPD config set client chain-id "$CHAIN_ID" --home "$HOME_DIR"
$APPD config set client keyring-backend "$KR" --home "$HOME_DIR"

$APPD keys add validator --keyring-backend "$KR" --home "$HOME_DIR"       # EVM chains: add --algo eth_secp256k1
$APPD genesis add-genesis-account validator 100000000000000000000000000$DENOM --keyring-backend "$KR" --home "$HOME_DIR"
$APPD genesis gentx validator 1000000000000000000000$DENOM --chain-id "$CHAIN_ID" --keyring-backend "$KR" --home "$HOME_DIR"
$APPD genesis collect-gentxs --home "$HOME_DIR"
$APPD genesis validate-genesis --home "$HOME_DIR"

$APPD start --home "$HOME_DIR" --minimum-gas-prices 0$DENOM     # foreground; Ctrl-C stops it
```

On SDK v0.47 the genesis subcommands are top-level (`add-genesis-account`, `gentx`, `collect-gentxs`, `validate-genesis`) and `--default-denom` does not exist: edit `bond_denom`, `mint_denom` and `min_deposit` in `genesis.json` with `jq` instead.

Faster blocks for dev loops (`config.toml`): `timeout_commit = "1s"`; shorter governance for testing proposals (`genesis.json`): `voting_period`, `expedited_voting_period`, `max_deposit_period`.

## Extra steps for a cosmos/evm chain

A bare `init` + `start` on a cosmos/evm chain usually **panics at boot**:

```
denom metadata <evm_denom> could not be found
```

The EVM module's `InitGenesis` looks up `bank.denom_metadata` for `evm.params.evm_denom`, and a fresh `init` leaves cosmos/evm's own default denom there with no metadata. Patch genesis before first start (this is what every chain's localnet script does; cosmos/evm's reference `local_node.sh` is the model):

```bash
G=$HOME_DIR/config/genesis.json; T=$G.tmp
jq --arg d "$DENOM" '.app_state.evm.params.evm_denom=$d
  | .app_state.staking.params.bond_denom=$d
  | .app_state.mint.params.mint_denom=$d
  | .app_state.gov.params.min_deposit[0].denom=$d
  | .app_state.gov.params.expedited_min_deposit[0].denom=$d' "$G" > "$T" && mv "$T" "$G"

# 18-decimal metadata; use the chain's real display denom/symbol and exponent
jq --arg d "$DENOM" '.app_state.bank.denom_metadata=[{
  "description":"Native token","base":$d,"display":"token","name":"Token","symbol":"TOKEN",
  "denom_units":[{"denom":$d,"exponent":0,"aliases":[]},{"denom":"token","exponent":18,"aliases":[]}],
  "uri":"","uri_hash":""}]' "$G" > "$T" && mv "$T" "$G"

# Which precompiles are live (sorted; see references/precompiles-and-params.md)
jq '.app_state.evm.params.active_static_precompiles=[
  "0x0000000000000000000000000000000000000100","0x0000000000000000000000000000000000000400",
  "0x0000000000000000000000000000000000000800","0x0000000000000000000000000000000000000801",
  "0x0000000000000000000000000000000000000802","0x0000000000000000000000000000000000000804",
  "0x0000000000000000000000000000000000000805","0x0000000000000000000000000000000000000806",
  "0x0000000000000000000000000000000000000807"]' "$G" > "$T" && mv "$T" "$G"

# Native token as an ERC20 (WERC20 at the 0xEeee… sentinel), and a fee-free dev chain
jq --arg d "$DENOM" '.app_state.erc20.native_precompiles=["0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"]
  | .app_state.erc20.token_pairs=[{contract_owner:1,erc20_address:"0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",denom:$d,enabled:true}]
  | .app_state.feemarket.params.no_base_fee=true
  | .app_state.feemarket.params.base_fee="0"
  | .app_state.feemarket.params.min_gas_price="0"' "$G" > "$T" && mv "$T" "$G"
```

Then set the EVM chain id and enable JSON-RPC in `app.toml` (section names vary slightly by version; `grep -n 'evm-chain-id\|\[json-rpc\]' $HOME_DIR/config/app.toml`):

```toml
[evm]
evm-chain-id = 9001            # the numeric id wallets and cast see; cosmos/evm's example uses 9001 / 262144

[json-rpc]
enable = true
address = "127.0.0.1:8545"
ws-address = "127.0.0.1:8546"
api = "eth,net,web3,txpool,debug"
```

Start with `--json-rpc.enable --json-rpc.api eth,txpool,net,debug,web3` if you prefer flags. cosmos/evm's example chain (`evmd`) ships `local_node.sh` at the repo root: flags `-y` (overwrite data), `-n` (keep), `--no-install`, `--remote-debugging`; it uses `$HOME/.evmd`, keyring `test`, key algo `eth_secp256k1`, denom `atest`, and fixed dev mnemonics that are **public** and must never be funded on a real network.

## Ports and verification

| Listener | Default | Where to change |
|----------|---------|-----------------|
| CometBFT RPC | `tcp://127.0.0.1:26657` | `config.toml` `[rpc] laddr` |
| P2P | `tcp://0.0.0.0:26656` | `config.toml` `[p2p] laddr` (set to `127.0.0.1` for a private localnet) |
| gRPC | `localhost:9090` | `app.toml` `[grpc] address` |
| REST / gRPC-gateway | `tcp://localhost:1317` | `app.toml` `[api]` (`enable`, `address`) |
| EVM JSON-RPC | `127.0.0.1:8545` | `app.toml` `[json-rpc] address` |
| EVM WebSocket | `127.0.0.1:8546` | `app.toml` `[json-rpc] ws-address` |

Repos frequently move these so two chains can coexist (for IBC tests) or to avoid clashing with a default node. **Read the home's `config.toml` and `app.toml`** rather than assuming.

```bash
$APPD status --node tcp://127.0.0.1:26657 | jq .sync_info.latest_block_height
$APPD query bank balances $($APPD keys show validator -a --keyring-backend test --home $HOME_DIR) --node tcp://127.0.0.1:26657
cast chain-id --rpc-url http://127.0.0.1:8545                  # EVM chains
cast block-number --rpc-url http://127.0.0.1:8545
```

`eth_getCode` returns `0x` for static precompiles even when active; use `eth_call` / `cast call` as the liveness probe (see `references/precompiles-and-params.md`).

## Stop, reset, pitfalls

- **Stop:** Ctrl-C in the foreground terminal. If backgrounded, find it with `pgrep -af "$APPD start"` and stop only the process whose `--home` is your localnet; never kill an unrelated daemon.
- **Reset:** stop, then `rm -rf "$HOME_DIR"` (or `$APPD comet unsafe-reset-all --home $HOME_DIR` to keep keys and config but wipe state). Re-run the init sequence.
- **"address already in use":** another node owns the port. Stop it or move this chain's ports; do not edit a shared script in place.
- **Keyring:** `--keyring-backend test` stores keys unencrypted under `$HOME_DIR/keyring-test`. That is fine for a localnet and nothing else.
- **EVM key algo:** accounts that will sign EVM transactions need `--algo eth_secp256k1`; a `secp256k1` key cannot be used from MetaMask or `cast`.
- **Mnemonic hygiene:** dev scripts print mnemonics to the terminal and sometimes write them to a file in the home dir; keep those out of git and logs.

## Multi-node and docker testnets

- Most SDK chains expose `<appd> testnet init-files --validator-count N --output-dir … --chain-id … --keyring-backend test` (sometimes `testnet multi-node`), which generates N homes plus a `docker-compose.yml`. cosmos/evm's `Makefile` wraps this as `make localnet-start` / `localnet-stop` (4 validators, images from `contrib/images`).
- Published ports in generated compose files are usually `"host:container"`, which Docker binds on **all interfaces**. On a shared network that exposes a dev chain with public dev keys; add a compose override that binds `127.0.0.1:<port>:<port>` if that matters.
- Generated compose files and genesis directories are build artifacts: regenerate them rather than hand-editing, and never reuse them for a real network.
- Ignite also offers `ignite testnet multi-node` / `in-place`; both are behind the `ignite` skill's safety gate when they start from live-network state.

## IBC between two local chains

Run two localnets with different chain ids, homes and ports, then relay with Hermes or the Go relayer (`rly`). Keep both chains local; a relayer config that points at a public RPC is a non-local broadcast and needs approval.
