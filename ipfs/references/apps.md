# Building apps on IPFS

The JS stack is **Helia** (js-ipfs and ipfs-http-client are archived — flag any tutorial using them). Go apps embed **Boxo** (the library suite Kubo is built on).

## Helia in Node (or the browser)

```bash
npm install helia @helia/unixfs
```

```ts
import { createHelia } from 'helia';
import { unixfs } from '@helia/unixfs';

const helia = await createHelia();          // a full node in your runtime
const fs = unixfs(helia);

const cid = await fs.addBytes(new TextEncoder().encode('hello ipfs'));
for await (const chunk of fs.cat(cid)) process.stdout.write(chunk);
```

- Modular data layers: `@helia/unixfs` (files/dirs), `@helia/json`, `@helia/dag-cbor`, `@helia/strings`.
- In browsers, libp2p uses WebTransport / WebRTC / WSS (AutoTLS nodes) — no local daemon needed.
- Persistence: default is in-memory; pass a blockstore (e.g. `blockstore-fs`, `blockstore-idb`) for durability. A Helia tab is not a pinning strategy — still remote-pin.
- Examples: https://github.com/ipfs-examples/helia-examples

## Verified retrieval in the browser (replaces "just hit a gateway")

```bash
npm install @helia/verified-fetch
```

```ts
import { verifiedFetch } from '@helia/verified-fetch';

// drop-in fetch() that hash-verifies every block client-side
const res = await verifiedFetch('ipfs://bafybei…/photo.jpg');
const blob = await res.blob();

const doc = await verifiedFetch('ipns://docs.example.com/spec.json');
```

Why: a plain gateway is trusted (it could serve tampered bytes); verified fetch pulls raw blocks from trustless gateways/peers and verifies against the CID. This is the official post-public-gateway migration path for apps.

## Talking to a Kubo node from code

- Local node RPC (port 5001): **kubo-rpc-client** (`import { create } from 'kubo-rpc-client'`) — only against nodes you control; the RPC port must never be public.
- Reading only? Prefer verified fetch or the node's 8080 gateway.

## Upload via pinning provider SDKs

```ts
// Pinata — current package is `pinata` (pinata-web3 is legacy)
import { PinataSDK } from "pinata";
const pinata = new PinataSDK({ pinataJwt: process.env.PINATA_JWT! });
const { cid } = await pinata.upload.public.file(file);
```

```bash
# Storacha CLI (successor of web3.storage's w3)
npm i -g @storacha/cli
storacha login you@example.com && storacha space create Docs
storacha up ./dist          # -> root CID, Filecoin-backed
```

## Architecture patterns

- **CID on-chain, content on IPFS** — contracts/NFTs store the small pointer, not megabytes. Standard for NFT metadata (`ipfs://<cid>/metadata.json`).
- **Encrypt before adding** for anything sensitive: the network is public and deletion is impossible once others pin. Keys stay with users.
- **Immutable releases + mutable pointer** — every deploy is a CID; DNSLink/IPNS/ENS points at the current one; rollback = repoint.
- **Dedup for free** — re-adding identical blocks (datasets, model checkpoints, package mirrors) costs nothing new.
- What does NOT belong: hot mutable state, latency-critical serving paths, private data in plaintext.

## Testing an integration

1. Add content → assert CIDv1 shape and determinism (same bytes ⇒ same CID).
2. Fetch through a second, independent path (another node or verified fetch), not the node that added it.
3. Kill the origin daemon; confirm remote pin still serves — that's the persistence test.
4. For sites: check deep links and 404 fallback via a subdomain gateway.
