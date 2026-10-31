#!/usr/bin/env bash
# Post a one-line alert to GEL_ALERT_URL, for example a private ntfy.sh topic.
set -euo pipefail
: "${GEL_ALERT_URL:?set GEL_ALERT_URL in .env}"
curl -fsS -m 30 -d "gpu-econ-life: $1 failed on $(hostname) at $(date -u +%FT%TZ)" "$GEL_ALERT_URL"
