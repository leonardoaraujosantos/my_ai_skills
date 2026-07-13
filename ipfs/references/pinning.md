# Keeping data alive (pinning & Filecoin)

**The honest model:** nobody is paid by the protocol to store your data. Unpinned content is garbage-collected; if every provider goes offline the content is unreachable (the CID stays valid — re-add the bytes and it resolves again). Persistence is a service you arrange. Budget for pinning like you budget for hosting.

## Options, roughly in order of effort

1. **Your own always-on node(s)** — `ipfs pin add` on a VPS; IPFS Cluster for replicated pinsets. Free + your ops.
2. **Remote pinning service** — paid, zero ops (below). ← default recommendation for apps.
3. **Filecoin deals** — cryptographically proven long-term storage (below).

## Pinning Service API (vendor-neutral — prefer this)

The IPFS Pinning Service API (spec v1.0.0) is implemented by Pinata, Filebase, 4EVERLAND and others; Kubo speaks it natively, so apps don't couple to one vendor:

```bash
ipfs pin remote service add mysvc https://api.provider.tld/psa $TOKEN
ipfs pin remote add --service=mysvc --name=myapp-v1 <CID>
ipfs pin remote ls --service=mysvc --status=pinned,pinning
```

## Services (July 2026 — verify before recommending, this market moves)

| Service | Model | Notes |
|---|---|---|
| **Pinata** | Paid tiers, dedicated gateways | Public + Private IPFS; current SDK is the `pinata` npm package (`pinata-web3` is legacy). Free tier ~500 files/1 GB |
| **Storacha** | UCAN-authorized, Filecoin-backed | Successor of web3.storage (legacy API sunset Jan 2024). CLI: `npm i -g @storacha/cli` → `storacha login/space create/up` |
| **Filebase** | S3-compatible API | Familiar for AWS teams; geo-redundant |
| **4EVERLAND** | Web3 hosting + pinning | Site deploys, ENS integration |

Gone or changed — do not recommend: **web3.storage** (→ Storacha), **free NFT.Storage** (now a paid Lighthouse-operated product), **Infura IPFS** (closed to new users), **Estuary** (defunct), Cloudflare's public gateway (gone).

Pinata SDK upload (current):

```ts
import { PinataSDK } from "pinata";
const pinata = new PinataSDK({ pinataJwt: process.env.PINATA_JWT! });
const upload = await pinata.upload.public.file(file);   // -> { cid, ... }, pinned
```

## Filecoin (the incentive layer)

- Separate blockchain, same CIDs/libp2p family: **storage providers earn FIL** for deals and must submit ongoing cryptographic proofs (PoRep for sealed archival; **PDP** since 2025 for hot unsealed data).
- 2026: **Filecoin Onchain Cloud** is live on mainnet — Warm Storage (PDP-backed, from ~$2.50/TiB/mo/copy), Filecoin Pay, and the TypeScript **Synapse SDK** (docs.filecoin.cloud).
- Practical guidance: developers rarely make deals by hand — Storacha and similar broker Filecoin persistence behind simple APIs. Saturn (retrieval CDN) is dead (2024); don't cite it.

## Verifying persistence

```bash
ipfs routing findprovs <CID>          # are there providers besides you?
# kill your local daemon, then from another machine / verified client:
#   fetch the CID — if it resolves, remote persistence works
```

Also useful: https://check.ipfs.network (IPFS Check) to debug retrievability of a CID.
