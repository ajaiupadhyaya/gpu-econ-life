# Deploying the daily collector

Runs `gel.collect.live --all` at 06:10 UTC with a health check, backs up `data/raw/` at 06:50 UTC,
and sends an alert if either fails. The timers use `Persistent=true`, so a run missed while the host
was down fires when it comes back.

## What it needs

- **Host:** Ubuntu with systemd. One run took 17 seconds and peaked at about 400 MB on a Mac with
  the AWS files already downloaded. A first download of those files uses more, so allow 2 GB of RAM.
- **Disk:** `data/raw/live/` grows by about 2 MB a day, plus about 33 MB when AWS publishes a new
  price version, roughly monthly. Expect under 1 GB through April 2027.
- **Accounts:** S3-compatible storage for backups, and an alert URL. A private
  [ntfy](https://ntfy.sh) topic works and needs no account.

## Setup

Run these once as root on the host.

```bash
useradd --system --create-home --shell /usr/sbin/nologin gel
curl -LsSf https://astral.sh/uv/0.10.4/install.sh | env UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1 sh
apt-get install -y --no-install-recommends rclone
install -d -o gel -g gel /opt/gpu-econ-life
```

Then ship the code from your Mac. This sends only tracked files, so the host holds no repository
credentials, and run it again after any commit you want deployed:

```bash
deploy/push.sh ohcamel-root
```

On the host, create `/opt/gpu-econ-life/.env`, owned by `gel` with mode 600:

```bash
GEL_CONTACT_EMAIL=you@example.org
GEL_BACKUP_REMOTE=gelbackup:gpu-econ-life
GEL_ALERT_URL=https://ntfy.sh/a-long-private-topic-name
```

Configure the backup remote as the `gel` user, naming it `gelbackup`:

```bash
sudo -u gel -H rclone config
```

Enable the timers:

```bash
systemctl enable --now gel-collect.timer gel-backup.timer
```

The collection unit runs at low priority with a 1.5 GB memory cap and can write only to its own
directory, so it cannot starve or touch other work on a shared host.

## Confirm it works

Phase 1 is finished only when you have seen all four of these work on the host.

1. A collection run succeeds:

   ```bash
   systemctl start gel-collect.service
   journalctl -u gel-collect.service -n 20 --no-pager
   ```

   Expect four `ok` lines (azure, aws, lambda, skypilot) and `healthy`.

2. The backup reached storage:

   ```bash
   systemctl start gel-backup.service
   sudo -u gel -H rclone ls gelbackup:gpu-econ-life/data/raw | head
   ```

3. An alert arrives on your phone:

   ```bash
   systemctl start gel-alert@test.service
   ```

4. The timers are scheduled:

   ```bash
   systemctl list-timers 'gel-*'
   ```

## Routine care

- **Weekly:** nothing, unless an alert arrives. A run that fails or loses more than half a provider's
  rows sends one. The raw response is saved before parsing, so a failed parse loses no data.
- **Every six months:** run `uv run python -m gel.collect.getdeploying` by hand. It must stay
  manual, because that license grants no automated access. Each file keeps 53 trailing weeks.
- **If SkyPilot moves past catalog v8:** update `catalog_version` in `config/skus.yaml`.
- **Never** add a collector for Vast.ai, RunPod or Oracle without written permission.
