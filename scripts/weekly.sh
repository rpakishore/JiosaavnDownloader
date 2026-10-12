#!/usr/bin/env bash
# Weekly cron job: pull, download the playlists in config.toml, then commit and push songs.jsonl.
#
# Optional environment:
#   BRANCH        branch to sync (default: main)
#   DB_FILE       cache file, relative to the repo root (default: songs.jsonl)
#   UV            uv executable (default: uv; cron's PATH is minimal, so an absolute path is safest)
#   LOCK_FILE     flock file (default: /tmp/jiosaavn-weekly.lock)
#   GOTIFY_URL    + GOTIFY_TOKEN: send a Gotify alert when the job fails
#   BOT_NAME      + BOT_EMAIL: commit identity
set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRANCH="${BRANCH:-main}"
DB_FILE="${DB_FILE:-songs.jsonl}"
UV="${UV:-uv}"
LOCK_FILE="${LOCK_FILE:-/tmp/jiosaavn-weekly.lock}"
BOT_NAME="${BOT_NAME:-jiosaavn-bot}"
BOT_EMAIL="${BOT_EMAIL:-jiosaavn-bot@users.noreply.github.com}"
STEP="startup"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') weekly: $*"; }

notify() {
    [[ -n "${GOTIFY_URL:-}" && -n "${GOTIFY_TOKEN:-}" ]] || return 0
    curl -fsS -m 15 -X POST "${GOTIFY_URL%/}/message" \
        -H "X-Gotify-Key: ${GOTIFY_TOKEN}" \
        -F "title=$1" -F "message=$2" -F "priority=8" >/dev/null \
        || log "could not send Gotify alert"
}

fail() {
    log "FAILED during: $STEP"
    notify "[Jiosaavn] weekly job failed" "Failed during: ${STEP} on $(uname -n)"
}
trap fail ERR

git_bot() { git -c user.name="$BOT_NAME" -c user.email="$BOT_EMAIL" "$@"; }

# Commit DB_FILE alone (never other files) if it changed. $1 is the message prefix.
commit_db() {
    git diff --quiet -- "$DB_FILE" && return 0
    local added
    added="$(git diff --numstat -- "$DB_FILE" | cut -f1)"
    git_bot commit --quiet -m "$1: +${added} songs ($(date +%F))" -- "$DB_FILE"
    log "committed ${added} new song(s)"
}

cd "$REPO_DIR"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    log "another run holds $LOCK_FILE, exiting"
    exit 0
fi

STEP="pre-flight checks"
[[ "$(git symbolic-ref --short HEAD)" == "$BRANCH" ]] || { log "not on $BRANCH"; false; }
if [[ -n "$(git status --porcelain --untracked-files=no -- . ":(exclude)$DB_FILE")" ]]; then
    log "tracked files other than $DB_FILE have local changes; refusing to run"
    false
fi

# A previous run may have died after downloading but before committing.
STEP="commit leftovers from a previous run"
commit_db "db (recovered)"

STEP="git pull"
git_bot pull --quiet --rebase origin "$BRANCH"

STEP="download playlists"
sync_rc=0
"$UV" run --frozen app sync || sync_rc=$?

# Commit whatever was downloaded, even if some playlists failed.
STEP="commit $DB_FILE"
commit_db "db"

STEP="git push"
if ! git push --quiet origin "$BRANCH"; then
    log "push rejected, rebasing onto origin/$BRANCH and retrying once"
    git_bot pull --quiet --rebase origin "$BRANCH"
    git push --quiet origin "$BRANCH"
fi

if [[ $sync_rc -ne 0 ]]; then
    STEP="download playlists (exit code $sync_rc; downloaded songs were still committed)"
    fail
    exit "$sync_rc"
fi
log "done"
