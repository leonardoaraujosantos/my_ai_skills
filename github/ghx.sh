#!/usr/bin/env bash
# ghx — resilient GitHub helper.
#
# Why this exists: on some networks DNS hands out a GitHub *Azure edge* IP for
# api.github.com (e.g. 4.228.31.149) that is black-holed locally, while the
# classic anycast IPs (140.82.x.x) still work. `gh` has no per-call IP override,
# so its API calls hang. This wrapper detects that, falls back to
# `curl --resolve` against a known-good IP, and distinguishes a real GitHub
# outage (via githubstatus.com) from a local routing block.
#
# Subcommands:
#   ghx doctor                 Diagnose: github status + api reachability + chosen route
#   ghx status                 Just query githubstatus.com (is GitHub actually down?)
#   ghx api <path> [curl args] Resilient REST call (auto direct-or-fallback). e.g.
#                                ghx api repos/OWNER/REPO/issues/191
#                                ghx api repos/OWNER/REPO/issues -X POST -d '{"title":"x"}'
#   ghx run  <gh args...>      Run real `gh`, but first ensure the API route works;
#                                if only the fallback IP works, prints the /etc/hosts
#                                pin to make `gh` itself work and exits non-zero.
#
# Env overrides:
#   GHX_API_IPS   space-separated candidate IPs to try for api.github.com
#   GHX_TIMEOUT   per-probe/curl timeout seconds (default 10)
set -euo pipefail

API_HOST="api.github.com"
TIMEOUT="${GHX_TIMEOUT:-10}"
# Known-good GitHub API anycast IPs (tried in order). Override with GHX_API_IPS.
CANDIDATE_IPS="${GHX_API_IPS:-140.82.112.6 140.82.113.6 140.82.114.6 140.82.121.6 20.205.243.168 20.27.177.116}"

log() { printf '%s\n' "$*" >&2; }

token() {
  if command -v gh >/dev/null 2>&1 && gh auth token >/dev/null 2>&1; then
    gh auth token
  elif [ -n "${GITHUB_TOKEN:-}" ]; then printf '%s' "$GITHUB_TOKEN"
  elif [ -n "${GH_TOKEN:-}" ];     then printf '%s' "$GH_TOKEN"
  else log "ghx: no token (gh auth login, or set GITHUB_TOKEN)"; return 1; fi
}

# Is api.github.com reachable the normal way (current DNS, port 443)?
direct_ok() {
  curl -sS -m "$TIMEOUT" -o /dev/null \
    -H "Authorization: Bearer $(token)" \
    "https://${API_HOST}/rate_limit" 2>/dev/null
}

# First candidate IP that answers HTTPS for api.github.com (with SNI). Echoes IP.
working_ip() {
  for ip in $CANDIDATE_IPS; do
    if curl -sS -m "$TIMEOUT" -o /dev/null \
         --resolve "${API_HOST}:443:${ip}" \
         -H "Authorization: Bearer $(token)" \
         "https://${API_HOST}/rate_limit" 2>/dev/null; then
      printf '%s' "$ip"; return 0
    fi
  done
  return 1
}

gh_status() {
  # Prints "<indicator>|<description>"; indicator none=ok, minor/major/critical=degraded.
  curl -sS -m "$TIMEOUT" "https://www.githubstatus.com/api/v2/status.json" 2>/dev/null \
    | python3 -c 'import sys,json; d=json.load(sys.stdin)["status"]; print(d["indicator"]+"|"+d["description"])' \
    2>/dev/null || printf 'unknown|could not reach githubstatus.com'
}

cmd_status() {
  IFS='|' read -r ind desc <<<"$(gh_status)"
  echo "GitHub status: $desc (indicator: $ind)"
  [ "$ind" = "none" ]
}

cmd_doctor() {
  IFS='|' read -r ind desc <<<"$(gh_status)"
  echo "1) githubstatus.com : $desc (indicator=$ind)"
  if direct_ok; then
    echo "2) api.github.com   : reachable directly — no workaround needed."
    echo "=> Route: direct. gh and curl both fine."
    return 0
  fi
  echo "2) api.github.com   : NOT reachable directly."
  if [ "$ind" != "none" ] && [ "$ind" != "unknown" ]; then
    echo "=> GitHub itself is degraded ($desc). Wait it out; not a local issue."
    return 1
  fi
  echo "   (GitHub reports operational, so this is a LOCAL routing/firewall block.)"
  if ip="$(working_ip)"; then
    echo "3) fallback IP      : ${ip} works."
    echo "=> Route: curl --resolve via ${ip}. Use 'ghx api ...' for REST calls."
    echo "   For full 'gh' functionality, pin it permanently:"
    echo "     echo \"${ip}  ${API_HOST}\" | sudo tee -a /etc/hosts"
    return 0
  fi
  echo "3) fallback IP      : none of the candidates worked."
  echo "=> Cannot reach the GitHub API by any route. Check VPN/network."
  return 1
}

cmd_api() {
  [ $# -ge 1 ] || { log "usage: ghx api <path> [curl args...]"; return 2; }
  local path="$1"; shift
  path="${path#/}"
  local base_args=(-sS -m "$TIMEOUT"
    -H "Authorization: Bearer $(token)"
    -H "Accept: application/vnd.github+json"
    -H "X-GitHub-Api-Version: 2022-11-28")
  if direct_ok; then
    curl "${base_args[@]}" "$@" "https://${API_HOST}/${path}"
  else
    local ip
    ip="$(working_ip)" || { log "ghx: API unreachable by any route"; cmd_status >&2 || true; return 1; }
    log "ghx: api.github.com blocked locally; routing via ${ip}"
    curl "${base_args[@]}" --resolve "${API_HOST}:443:${ip}" "$@" "https://${API_HOST}/${path}"
  fi
}

cmd_run() {
  if direct_ok; then exec gh "$@"; fi
  IFS='|' read -r ind _ <<<"$(gh_status)"
  if [ "$ind" != "none" ] && [ "$ind" != "unknown" ]; then
    log "ghx: GitHub API is degraded right now — 'gh' will likely fail. Run 'ghx doctor'."
    return 1
  fi
  local ip
  if ip="$(working_ip)"; then
    log "ghx: api.github.com is blocked locally but ${ip} works."
    log "     'gh' can't be pointed at an IP per-call. Either:"
    log "       - use 'ghx api <path>' for REST calls, or"
    log "       - pin it once:  echo \"${ip}  ${API_HOST}\" | sudo tee -a /etc/hosts"
    return 1
  fi
  log "ghx: API unreachable by any route. Run 'ghx doctor'."
  return 1
}

case "${1:-}" in
  doctor) shift; cmd_doctor "$@";;
  status) shift; cmd_status "$@";;
  api)    shift; cmd_api "$@";;
  run)    shift; cmd_run "$@";;
  *) log "usage: ghx {doctor|status|api <path>|run <gh args>}"; exit 2;;
esac
