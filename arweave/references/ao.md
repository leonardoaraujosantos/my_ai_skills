# AO — hyperparallel compute on Arweave

**AO** = the protocol: isolated processes, message-passing only (actor model, think Erlang not EVM), every message persisted to Arweave, state derived from the ordered log, verifiability over global consensus. **aos** = the Lua CLI/REPL dev tool. **HyperBEAM** = the production AO-Core node implementation (Erlang/OTP); process state is readable over plain HTTP.

Costs are modular (storage + compute + operator services) — "execution is free" is wrong; budget per workload.

## aos quickstart (Node 20+; Lua 5.3 runtime)

```bash
npm i -g https://get_ao.arweave.net        # NOT get_ao.g8way.io (stale)
aos myprocess                               # spawn/reconnect; keyfile -> ~/.aos.json
aos myprocess --node https://push.forward.computer   # target a HyperBEAM node
```

REPL loop:

```
.load handlers.lua                 -- push local code into the process
Send({ Target = ao.id, Action = "Ping" })
Inbox[#Inbox]                      -- latest reply
.editor                            -- multiline input; .help for the rest
```

Everything a process does is public: source, messages, spawns — browse at https://ao.link/#/entity/<process-id>.

## Handlers (Lua)

```lua
Counter = Counter or 0                     -- top-level vars survive across messages

Handlers.add(
  "increment",
  Handlers.utils.hasMatchingTag("Action", "Increment"),
  function (msg)
    -- validate sender when it matters:
    -- if msg.From ~= Owner then return msg.reply({ Data = "forbidden" }) end
    Counter = Counter + 1
    msg.reply({ Data = tostring(Counter) })
  end
)
```

- Built-ins available in aos processes: `json`, `ao`, crypto, SQLite (`require("json")`, etc.).
- Lua gotchas for JS devs: 1-based indices, `..` concatenation, tables for everything, **undeclared variables are global**.
- Keep handlers **deterministic** (same log ⇒ same state); that is what makes AO verifiable.
- `Eval` messages hot-patch a live process (that's what `.load` sends) — great for prototyping, but remember every version is permanent history. Test locally first (plain Lua + busted for unit tests of handler functions; feed fake `msg` tables, test invalid JSON / missing tags / wrong sender).

## From JavaScript: `@permaweb/aoconnect`

```ts
import {
  spawn, message, result, results, dryrun, createDataItemSigner,
} from '@permaweb/aoconnect';

const signer = createDataItemSigner(window.arweaveWallet); // Wander; or JWK in Node

// create a process (module/scheduler ids from the AO cookbook)
const processId = await spawn({ module, scheduler, signer, tags: [] });

// signed write
const msgId = await message({
  process: processId,
  signer,
  tags: [{ name: 'Action', value: 'Increment' }],
  data: '',
});

// read the outcome of that message
const { Messages, Output, Error } = await result({ process: processId, message: msgId });

// free read (no persisted message)
const res = await dryrun({
  process: processId,
  tags: [{ name: 'Action', value: 'Get' }],
});
```

Rule of thumb: `result()` after a write, `dryrun()` for queries, HTTP for HyperBEAM-exposed state.

## HyperBEAM HTTP state reads (no SDK)

Process state as plain GETs against a HyperBEAM node — path segments compose "devices":

```
GET https://<node>/<process-id>~process@1.0/now        # compute up to now
GET https://<node>/<process-id>~process@1.0/now/<key>  # a specific state key
```

Fast (~100 ms hot) and cache-friendly; ideal for dashboards and reads that don't need a wallet. See https://hyperbeam.arweave.net for devices and node operation.

## Architecture context (teach/explain)

- **legacynet (2024–25)**: fixed MU (relay) / SU (order+persist) / CU (compute) pipeline — still the cleanest way to explain why the log is the source of truth.
- **HyperBEAM (now)**: modular devices (scheduling, compute, payment, security are pluggable); nodes choose services and pricing.
- **State**: logically determined by the message log; operationally served from caches/checkpoints — "everything replays on every read" is a myth (cold processes may re-materialize).
- **SmartWeave/Warp**: historical ancestor (lazy evaluation, contracts as data). Don't start new projects on it.

## Tokens (context, not advice)

AR pays for storage (endowment). AO token: 21M max supply, 100% fair launch (no presale/insider allocation), transferable since 2025-02-08; minting flows to AR holders (~36%) and bridged assets (~66%). Any token transfer/bridge = spending gate.
