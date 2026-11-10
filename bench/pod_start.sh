#!/usr/bin/env bash
# Pod entrypoint: install the account's SSH keys (Runpod injects them as PUBLIC_KEY, or
# SSH_PUBLIC_KEY as a per-pod override), start sshd, then idle. The benchmark is started by hand
# over SSH (inside tmux) so a dropped connection cannot kill it.
set -euo pipefail
mkdir -p /root/.ssh && chmod 700 /root/.ssh
for k in "${PUBLIC_KEY:-}" "${SSH_PUBLIC_KEY:-}"; do
  [[ -n "$k" ]] && printf '%s\n' "$k" >> /root/.ssh/authorized_keys
done
[[ -f /root/.ssh/authorized_keys ]] && chmod 600 /root/.ssh/authorized_keys
ssh-keygen -A >/dev/null
/usr/sbin/sshd
echo "[pod_start] sshd up; benchmark: cd /opt/gel && ./bench/run_all.sh <GPU_LABEL> <PRICE> runpod secure"
exec sleep infinity
