---
name: unity
description: Manage Unity Editors, projects, builds, and tests with the standalone `unity` CLI, and wire the Unity Editor to AI agents over MCP. Use when the user wants to install/switch Unity Editor versions, create or open a Unity project, run a headless build or EditMode/PlayMode tests, drive a running Editor from the terminal, set up Unity CI, or connect Claude Code to the Unity Editor MCP server.
argument-hint: [command] [args...]
---

# Unity CLI Skill

Drive Unity from the terminal with the standalone `unity` CLI — no Unity Hub GUI required.

## Ground rule: trust the binary, not the docs site

Unity's published docs (`docs.unity.com/en-us/unity-cli/*`) lag the shipped CLI by several
releases. As of CLI `1.0.0-beta.3` the reference page documents only 11 of ~35 commands, omits
`build`/`test`/`run`/`mcp`/`pipeline`, lists an incomplete set of exit codes, and contains at
least one wrong example (`unity editors -a` is `--architecture <arch>`, not "combined list").

**Always resolve uncertainty locally, in this order:**

```bash
unity --help              # authoritative command list for the installed build
unity <cmd> --help        # authoritative flags — subcommands too: unity projects new --help
unity changelog           # what the installed version added; often the only docs for new flags
unity upgrade --check     # prints "<current>\t<latest>"
```

Only fall back to the docs site for conceptual material: module ID tables (on the *Hub* CLI
reference page), Hub log locations, and format auto-selection.

## Setup

```bash
curl -fsSL https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.sh | UNITY_CLI_CHANNEL=beta bash
unity --version
unity auth login          # browser flow; shares the OS keyring with Unity Hub
unity auth status
unity doctor              # environment snapshot when something looks wrong
```

Upgrades: `unity upgrade [--check|--dry-run|--channel stable|beta|--target <v>|--rollback]`.
AppImage installs are replaced in place with checksum verification.

## Scripting contract

Get this right and everything else follows.

| Concern | Rule |
|---|---|
| Format | `human` on a TTY, **`tsv` automatically when piped or redirected** — never plain text. Pass `--format json` (or `--json`) explicitly in scripts. `ndjson` streams progress events. |
| Streams | Data on stdout, errors and progress on stderr. JSON mode emits `{"error": "..."}` on stderr. |
| Prompts | `--non-interactive` (or `UNITY_NON_INTERACTIVE`) in CI. A missing required arg on a non-TTY is an error, not a prompt. |
| Progress | Animated bars are for humans. Never parse them; use `--format json`/`ndjson`. |

**Exit codes** — check these specifically, not just non-zero:

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | General error (see stderr) |
| `2` | Usage error — missing/invalid flags |
| `6` | `unity test` ran and tests **failed** (distinct from a broken run) |
| `130` | Cancelled (SIGINT) |

Environment variables: `UNITY_FORMAT`, `UNITY_NON_INTERACTIVE`, `UNITY_QUIET`, `UNITY_NO_BANNER`,
`UNITY_VERBOSE`, `UNITY_ARCHITECTURE`, `UNITY_PROJECT_PATH`, `UNITY_EDITOR_VERSION`,
`UNITY_TEST_TIMEOUT`, `UNITY_RUN_TIMEOUT`, `UNITY_PROXY`, `UNITY_CLI_CHANNEL`,
`UNITY_SERVICE_ACCOUNT_ID` / `UNITY_SERVICE_ACCOUNT_SECRET` (CI auth),
`UNITY_NO_CONSENT_PROMPT`, `UNITY_NO_CRASH_REPORT`.

## Editors

```bash
unity install lts -m android ios webgl --cm   # aliases: latest, lts, default, 6, 6.5, 2022
unity install 6000.3.7f1 -c 9b001d489a54      # changeset needed for archive versions
unity install lts --dry-run --accept-eula -y  # CI-safe preview / unattended
unity install-modules -e 6000.3.7f1 -l        # list installable modules
unity editors -i                              # installed (add -r for releases, --json to parse)
unity editors add /path/to/Unity              # register a manual install
unity editors default 6000.3.7f1
unity uninstall 6000.3.7f1
```

`--resume` recovers interrupted downloads; `--force` reinstalls; `--list-components` prints module
IDs with their `unity-downloader-cli` names.

## Projects

```bash
unity projects new MyGame --path ~/work --editor-version lts --template com.unity.template.3d
unity projects info .            # version, modules, cloud/VCS links
unity projects require .         # assert the right editor is installed, install if not
unity projects list --json
unity open ./MyGame              # or just: unity ./MyGame
unity projects upgrade ./MyGame --editor-version 6000.5.5f1
unity projects clone <repo-url>  # GitHub / GitLab / Unity Version Control
```

`unity projects new` is the non-interactive, CI-friendly form; `create` is the interactive one.
Templates: `unity templates list|info|create|edit|delete|location`.

## Build, test, run

**`unity build` requires `--execute-method`** — Unity has no built-in command-line build, so the
project must expose a static C# method that performs it. There is no way around this.

```bash
unity build ./MyGame --target StandaloneLinux64 \
  --execute-method Builder.PerformBuild -o ./out --allow-install

unity test ./MyGame --mode EditMode --output results.xml   # exit 6 == tests failed
unity test . --filter "MyNamespace.MyTests" --timeout 900

unity run ./MyGame -- -nographics -quit -executeMethod Foo.Bar
```

Android signing (`--android-export-type apk|aab|android-studio-project`,
`--android-keystore-base64`, `--android-keystore-password`, `--android-key-alias`,
`--android-target-sdk-version`, `--android-symbol-type`) — **secrets passed as CLI args land in
shell history and CI logs**; source them from the CI secret store and keep them out of committed
scripts. Versioning: `--versioning-strategy semantic|tag|custom|none` with `--build-version` for
`custom`; `--allow-dirty-build` skips the uncommitted-changes guard.

`unity build` streams the Editor log to stdout by default (`--no-tail` to suppress); logs default
to `<project>/Logs/build-<target>-<timestamp>.log`.

## Driving a live Editor (Pipeline)

The Pipeline package turns C# methods annotated `[CliCommand]` / `[CliArg]` into commands callable
from the CLI and MCP. Install once per project:

```bash
unity pipeline install            # com.unity.pipeline; --project-path, --force, --package-version
unity status                      # connected Editors: port, project, version, PID, state
unity list                        # commands the connected Editor exposes
unity command <name> [args...]    # run against a *running* Editor (--timeout 30)
unity run . --command my_build -- --target StandaloneLinux64   # headless: boots the Editor, runs, exits
```

`unity run --command` reuses an already-running Editor for the project if there is one (and leaves
it running); otherwise it starts one in batch mode and shuts it down afterward. Args after `--` are
parsed against the command's `[CliArg]` schema, so no manual `Environment.GetCommandLineArgs()`
parsing. `unity shell` keeps one warm process for many commands (`--protocol ndjson` for machines).

## MCP: connecting agents to the Editor

`unity mcp` **is** the MCP stdio server. Register it with Claude Code:

```bash
unity mcp configure claude-code --dry-run   # prints the exact command it will run
claude mcp add --scope user --transport stdio unity-editor-mcp unity mcp
```

`unity mcp configure --list` shows every supported client and its config path (claude, claude-code,
cursor, vscode, copilot-cli, windsurf, cline, codex, kiro, zed, continue, antigravity, trae,
openclaw, inspect). Use `--local` for project-scoped config where the client supports it, `--yes`
to overwrite without prompting, `--dry-run` to preview. Pin a server to one project with
`unity mcp --project-path /path/to/MyProject`.

**The tool list is dynamic and starts empty.** The server exposes the connected Editor's registered
Pipeline commands as MCP tools. With no Editor running — or a project without `com.unity.pipeline`
— `tools/list` returns `[]` and the agent sees nothing. Verified against `1.0.0-beta.3`:

```
{"result":{"tools":[]},"jsonrpc":"2.0","id":2}    # no Editor connected
```

So when MCP tools appear to be missing, the fix is upstream: `unity pipeline install`, open the
project, confirm with `unity status` and `unity list`, then reconnect the client. Debug the server
itself with `unity mcp configure inspect` (MCP Inspector) or the `mcp-client` skill.

## CI recipe

```bash
export UNITY_SERVICE_ACCOUNT_ID=... UNITY_SERVICE_ACCOUNT_SECRET=...   # from CI secrets
export UNITY_NON_INTERACTIVE=1 UNITY_NO_BANNER=1 UNITY_FORMAT=json

unity projects require . -y || exit 1                                  # install the pinned editor if missing
unity test . --mode EditMode --output results.xml
case $? in
  0) ;;                                     # passed
  6) echo "tests failed"; exit 1 ;;         # real failures — publish results.xml
  *) echo "test run broke"; exit 1 ;;       # infra/usage problem
esac
unity build . --target StandaloneLinux64 --execute-method Builder.PerformBuild -o ./out
```

Service-account env vars generate bearer tokens automatically — no `unity auth login` on agents.

## Troubleshooting

| Symptom | Move |
|---|---|
| Anything unexpected | `unity doctor` — environment snapshot (`unity diagnose` is proxy-only today) |
| Editor not responding to `command`/MCP | `unity status`, `unity list`, `unity pipeline list` |
| Install/download problems | `unity cache info`, `unity cache clean`, `unity install --resume` |
| Hub-side errors | `unity logs` (Linux: `~/.config/UnityHub/logs`; CLI's own: `cli-log.json`) |
| Behind a proxy | `unity config proxy`, `--proxy <url>`, `--proxy-disable`; `unity diagnose proxy` for a redacted report |
| Filing a bug | `unity bug --title ... --description ... --steps ... --reproducibility always` (non-interactive; exit 2 lists missing flags) |

Privacy: usage analytics are opt-in (`unity analytics status|opt-in|opt-out`), but anonymous Sentry
crash reporting is **on by default** — disable with `UNITY_NO_CRASH_REPORT`.
