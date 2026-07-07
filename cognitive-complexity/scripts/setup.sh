#!/usr/bin/env bash
# One-time installer for the cognitive-complexity toolchain.
# Idempotent: re-run to repair/upgrade. The skill calls this only when a tool
# is missing — it does NOT reinstall on every analysis.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ok()   { printf '  ✓ %s\n' "$1"; }
miss() { printf '  ✗ %s\n' "$1"; }

echo "Setting up cognitive-complexity tools..."

# Python — complexipy (cognitive), lizard (cyclomatic fallback / C-C++ fallback)
if command -v complexipy >/dev/null 2>&1 && command -v lizard >/dev/null 2>&1; then
  ok "complexipy + lizard"
else
  PIP="$(command -v pip3 || command -v pip)"
  if [ -n "$PIP" ]; then "$PIP" install -q --upgrade complexipy lizard && ok "complexipy + lizard installed"
  else miss "pip not found — install Python first"; fi
fi

# Go — gocognit (cognitive)
if [ -x "${GOPATH:-$HOME/go}/bin/gocognit" ] || command -v gocognit >/dev/null 2>&1; then
  ok "gocognit"
elif command -v go >/dev/null 2>&1; then
  go install github.com/uudashr/gocognit/cmd/gocognit@latest && ok "gocognit installed"
else
  miss "go not found — Go files will be skipped"
fi

# TS/JS — eslint + eslint-plugin-sonarjs (cognitive)
if [ -x "$HERE/ts/node_modules/.bin/eslint" ]; then
  ok "eslint + sonarjs"
elif command -v npm >/dev/null 2>&1; then
  ( cd "$HERE/ts" && npm install --silent --no-fund --no-audit ) && ok "eslint + sonarjs installed"
else
  miss "npm not found — JS/TS files will be skipped"
fi

# Solidity — solhint code-complexity rule (cyclomatic)
if [ -x "$HERE/solidity/node_modules/.bin/solhint" ] || command -v solhint >/dev/null 2>&1; then
  ok "solhint"
elif command -v npm >/dev/null 2>&1; then
  ( cd "$HERE/solidity" && npm install --silent --no-fund --no-audit ) && ok "solhint installed"
else
  miss "npm not found — Solidity files will be skipped"
fi

# SystemVerilog — scc (per-FILE cyclomatic-style estimate; no per-function
# SV complexity tool exists in open source — verible has no complexity rule).
if command -v scc >/dev/null 2>&1; then
  ok "scc"
elif command -v brew >/dev/null 2>&1 && brew install scc >/dev/null 2>&1; then
  ok "scc installed"
elif command -v go >/dev/null 2>&1 && go install github.com/boyter/scc/v3@latest >/dev/null 2>&1; then
  ok "scc installed (go)"
else
  miss "scc not found — SystemVerilog files will be skipped (brew install scc)"
fi

# C/C++ — clang-tidy (cognitive). Cannot auto-install; advise.
if command -v clang-tidy >/dev/null 2>&1; then
  ok "clang-tidy"
else
  miss "clang-tidy not found (C/C++ will fall back to lizard = cyclomatic)."
  echo "      macOS:  brew install llvm   (then add llvm/bin to PATH)"
  echo "      Debian: apt-get install clang-tidy"
fi

echo "Done."
