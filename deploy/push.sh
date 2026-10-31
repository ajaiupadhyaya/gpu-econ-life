#!/usr/bin/env bash
# Ship the committed code to the host and refresh its environment. Run from a clean checkout.
# Only tracked files travel, so .env and data/ stay where they are, and the host needs no
# credentials for the repository.
#
#   deploy/push.sh [ssh-host]
set -euo pipefail
HOST="${1:-ohcamel-root}"
TARGET=/opt/gpu-econ-life
cd "$(git rev-parse --show-toplevel)"
if [ -n "$(git status --porcelain)" ]; then
  echo "Commit your changes first, so the host runs a known version." >&2
  exit 1
fi
COMMIT="$(git rev-parse HEAD)"
git archive --format=tar HEAD | ssh "$HOST" "tar -x --no-same-owner -C $TARGET"
ssh "$HOST" bash -s <<REMOTE
set -euo pipefail
echo "$COMMIT" > $TARGET/DEPLOYED_COMMIT
chown -R gel:gel $TARGET
sudo -u gel -H bash -c 'cd $TARGET && UV_CACHE_DIR=$TARGET/.uv-cache /usr/local/bin/uv sync --no-dev --frozen --quiet'
cp $TARGET/deploy/*.service $TARGET/deploy/*.timer /etc/systemd/system/
systemctl daemon-reload
REMOTE
echo "deployed ${COMMIT:0:7} to $HOST"
