#!/usr/bin/env bash
# Copy data/raw to off-server storage. "copy" never deletes and --immutable refuses to change a
# file already stored, which keeps the backup as append-only as data/raw itself.
set -euo pipefail
: "${GEL_BACKUP_REMOTE:?set GEL_BACKUP_REMOTE in .env, for example gelbackup:gpu-econ-life}"
rclone copy /opt/gpu-econ-life/data/raw "${GEL_BACKUP_REMOTE}/data/raw" --immutable --transfers 4
