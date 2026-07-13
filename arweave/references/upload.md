# Uploading to Arweave (permanent storage)

> Safety: apply the SKILL.md permanence + spending gates before any real upload.

## Recommended path: Turbo SDK (`@ardrive/turbo-sdk`)

Turbo bundles data items (ANS-104), gives signed receipts, retries, and card/crypto payment. Free tier covers small items (~≤100 KiB).

### Node/TypeScript

```ts
import { TurboFactory } from '@ardrive/turbo-sdk';
import fs from 'fs';

const jwk = JSON.parse(fs.readFileSync('./wallet.json', 'utf-8')); // never commit
const turbo = TurboFactory.authenticated({ privateKey: jwk });

// price check BEFORE uploading (winc = winston credits)
const [{ winc: cost }] = await (await turbo.getUploadCosts({ bytes: [size] }));

const { id, winc } = await turbo.uploadFile({
  file: './data.json',
  dataItemOpts: {
    tags: [
      { name: 'Content-Type', value: 'application/json' },
      { name: 'App-Name', value: 'MyApp' },        // your queryable schema
      { name: 'App-Version', value: '1.0.0' },
    ],
  },
});
console.log(`https://arweave.net/${id}`);
```

- `uploadFolder({ folderPath })` uploads a directory and auto-generates a path manifest.
- Browser: `TurboFactory.authenticated({ signer: new ArconnectSigner(window.arweaveWallet) })` (class name still says Arconnect; the wallet is Wander).
- Errors to handle: insufficient credits, network failures (SDK retries transient ones).

### CLI

```bash
npx @ardrive/turbo-sdk --help
turbo upload-file --file ./data.json --wallet-file ./wallet.json
turbo upload-folder --folder-path ./dist --wallet-file ./wallet.json
turbo top-up --value 10 --currency usd ...   # SPENDS MONEY — approval gate
```

### Payment options (July 2026)

Card via Stripe; crypto: AR, ARIO (mainnet+Base), ETH (mainnet+Base), SOL, USDC (Eth/Base/Polygon), POL, KYVE; **x402** (USDC-over-HTTP, pay-per-request — good for agents).

## Costs (July 2026 — re-check before quoting)

- Turbo bundled rate: **≈ $31/GiB** one-time (`GET https://payment.ardrive.io/v1/rates`)
- Base protocol: **≈ 10.5 AR/GiB** (`GET https://arweave.net/price/1073741824`, winston; 1 AR = 1e12 winston)
- Small uploads are cents; ≤100 KiB items typically free via Turbo.

## Size reality

The protocol has no hard cap, but practice does:
- **≤100 KiB**: single data item, often free
- **Many files**: ANS-104 bundle (what Turbo does automatically)
- **Very large files**: chunked upload (arweave-js `uploader` or Turbo multipart) — resumable

## Tags are the schema

Every data item carries up to 2 KiB of tags. Always set `Content-Type` (controls how gateways serve it). Add app-specific tags (`App-Name`, `Type`, ids) — they are the only way to find data later (see query.md). Tag names/values are strings.

## Low-level appendix: arweave-js (know how it works underneath)

```js
import Arweave from 'arweave';
const arweave = Arweave.init({ host: 'arweave.net', port: 443, protocol: 'https' });
const tx = await arweave.createTransaction({ data }, jwk);
tx.addTag('Content-Type', 'text/plain');
await arweave.transactions.sign(tx, jwk);
const uploader = await arweave.transactions.getUploader(tx);
while (!uploader.isComplete) await uploader.uploadChunk();
```

Direct L1 transactions pay protocol price and wait for block confirmation (~2 min). Use for base-layer needs; use Turbo for everything else.

## Wallets & funding

- **Dev/scripts/CI**: JWK keyfile JSON. Generate a fresh one: `npx -y @permaweb/wallet > wallet.json` or via arweave-js `arweave.wallets.generate()`. aos auto-creates `~/.aos.json`.
- **Browser users**: Wander extension (`window.arweaveWallet`); Beacon on mobile.
- Fund Turbo credits by card or tokens — removes the "buy AR on an exchange" onboarding wall.
- Address from keyfile: `arweave.wallets.jwkToAddress(jwk)`.

## Verify an upload

```bash
curl -I https://arweave.net/<txid>          # 200/202 once seeded
curl https://arweave.net/tx/<txid>/status   # L1 tx confirmation
```

Turbo receipts are signed — keep `id` + receipt for audit. Data propagates to gateways within seconds-to-minutes; L1 inclusion for direct txs takes a few blocks.
