# Cast — Chain Interaction & Encoding

`cast` is Foundry's Swiss-army knife for talking to a chain and for offline encoding/decoding. Offline helpers (sig/keccak/abi/unit conversion) need no network. Read commands need `--rpc-url` (or the `ETH_RPC_URL` env var). **Sending commands are gated — see the safety gate in `SKILL.md`.**

## Offline helpers (always safe, no network)

```bash
cast sig "transfer(address,uint256)"        # -> 0xa9059cbb  (4-byte selector)
cast 4byte 0xa9059cbb                        # reverse-lookup a selector via 4byte.directory
cast keccak "hello"                          # keccak256 hash
cast abi-encode "f(uint256,address)" 42 0x...   # ABI-encode args
cast calldata "transfer(address,uint256)" 0xTo 1000   # full calldata (selector + args)
cast abi-decode "balanceOf(address)(uint256)" 0x...   # decode return data
cast --to-unit 1000000000000000000 ether     # wei -> ether  (=> 1)
cast --from-wei 1000000000000000000          # => 1
cast --to-wei 1.5 ether                       # => 1500000000000000000
cast --to-hex 255 / cast --to-dec 0xff        # base conversion
cast --to-checksum 0xabc...                    # EIP-55 checksum an address
cast max-uint / cast max-int                   # boundary values for tests
```

## Reading chain state (needs --rpc-url)

```bash
export ETH_RPC_URL="https://..."             # or pass --rpc-url each time
cast block-number
cast chain-id
cast balance 0xADDR                          # wei; add --ether for ether
cast nonce 0xADDR
cast code 0xADDR                             # deployed bytecode (0x = EOA/empty)
cast storage 0xADDR 3                         # raw value at storage slot 3
cast call 0xADDR "balanceOf(address)(uint256)" 0xHOLDER   # view/pure call, no tx
cast call 0xADDR "totalSupply()(uint256)"
cast estimate 0xADDR "transfer(address,uint256)" 0xTo 1   # gas estimate (no send)
cast tx 0xTXHASH                              # decode a transaction
cast receipt 0xTXHASH                         # its receipt (status, gas, logs)
cast run 0xTXHASH                             # re-execute a tx locally with a full trace
cast run 0xTXHASH --quick                     # trace without fetching all state
cast logs "Transfer(address,address,uint256)" --from-block 19000000  # event logs
```

`cast call` and `cast run` are the read/simulate workhorses — use them to verify behavior *before* ever sending anything.

## Storage inspection

```bash
cast storage 0xADDR <slot>                    # single slot
cast storage 0xADDR                           # (on a verified/local contract) full layout
cast index address 0xHOLDER 3                 # compute mapping slot: mapping at slot 3, key = holder
```

`cast index <keyType> <key> <mappingSlot>` computes where `mapping[key]` lives, so you can `cast storage` an ERC-20 balance directly.

## Sending transactions — GATED

`cast send` and `cast publish` sign and broadcast. **Do not run without explicit user approval** (see `SKILL.md`). When approved, sign from a keystore account, never a raw key on the CLI:

```bash
# Simulate first (always allowed):
cast call 0xADDR "transfer(address,uint256)" 0xTo 1000 --from 0xME

# Then, only after approval, send from an encrypted keystore account:
cast send 0xADDR "transfer(address,uint256)" 0xTo 1000 \
  --account my-deployer --rpc-url "$ETH_RPC_URL"
```

`--account <name>` prompts for the keystore password (set up via `cast wallet import`, see `references/deployment.md`). Prefer `--rpc-url` to a local anvil/fork when rehearsing.

## Wallet utilities

```bash
cast wallet new                               # generate a fresh keypair (dev only)
cast wallet address --account my-deployer     # show the address for a keystore account
cast wallet sign --account my-deployer "msg"  # GATED: signing — needs approval
```

## Handy conversions for tests & debugging

```bash
cast to-bytes32 0x1                            # left-pad to 32 bytes
cast parse-bytes32-string 0x...               # bytes32 -> string
cast format-bytes32-string "SYMBOL"
cast decode-error 0x<selector+data>           # decode a custom error revert
cast pretty-calldata 0x<calldata>             # human-readable calldata breakdown
```
