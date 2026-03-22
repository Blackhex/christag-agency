# Dispatch

Dispatch is Agency's built-in agent scheduler. It runs as a systemd user timer that wakes up on a regular heartbeat, evaluates schedule rules for each group, and runs qualifying agents sequentially.

## Setup

Go to **Settings** (`/admin/`) and click **Install Dispatch**. This installs three things into your user session:

- `~/.config/agency/dispatch.sh` — the dispatcher script
- `~/.config/agency/dispatch.conf` — points the script at your config.yaml and Python venv
- `~/.config/systemd/user/agency-dispatch.service` + `agency-dispatch.timer` — systemd units

The timer is enabled and started immediately. Default heartbeat is every 15 minutes. You can change the interval on the Settings page after installation.

## Enabling per Group

Dispatch is configured per group in the group edit form (`/admin/orgs/{group}/edit`):

- **Enable/disable** — checkbox to opt the group into dispatch
- **Timeout** — max seconds per agent run (default 300)
- **Daily limit** — max total agent runs per day for the group (default 20)

Each agent in the group can have one or more schedule rules. Rules are added inline on the group edit page, per agent.

## Schedule Rules

Each rule has a **prompt** (a file from `shared/prompts/`) and a timing condition:

### `at` — run once per day at a specific time

```yaml
- prompt: morning-report.md
  at: "09:00"
```

The agent runs when the heartbeat fires within the window around the target time. Once it runs, a marker file prevents it from running again that day.

### `every` — run on a recurring interval

```yaml
- prompt: check-health.md
  every: "6h"
```

Valid units are `m` (minutes) and `h` (hours). The dispatcher checks a marker file's mtime to determine whether enough time has elapsed since the last run.

An agent can have multiple rules with different prompts and schedules.

## How It Works

1. The systemd timer fires every N minutes (default 15, configurable in Settings).
2. `dispatch.sh` reads `config.yaml` and finds groups with `dispatch.enabled: true`.
3. For each enabled group, it iterates agents and their schedule rules.
4. For `at` rules: checks if the current time is within the heartbeat window of the target. Skips if an event marker exists for today.
5. For `every` rules: checks if enough time has elapsed since the last-run marker's mtime.
6. Qualifying agents are run sequentially — `claude --dangerously-skip-permissions` with the prompt file's contents, executed from the agent's directory.
7. Output goes to `shared/logs/YYYY-MM-DD/{agent}-{prompt}-{HHMMSS}.out` (and `.err`).
8. After each run, the daily limit is re-checked. If reached, the group stops.

## Config Format

Dispatch settings live in two places in `config.yaml`:

```yaml
agency:
  dispatch:
    installed: true
    interval: 15          # Heartbeat interval in minutes

groups:
  my-project:
    dispatch:
      enabled: true
      timeout: 300
      daily_limit: 20
      agents:
        researcher:
          - prompt: morning-scan.md
            at: "09:00"
          - prompt: check-feeds.md
            every: "6h"
        writer:
          - prompt: draft-review.md
            at: "14:00"
```

## Installed Files

| File | Purpose |
|------|---------|
| `~/.config/agency/dispatch.sh` | Main dispatcher script |
| `~/.config/agency/dispatch.conf` | Config path and venv Python path |
| `~/.config/systemd/user/agency-dispatch.service` | Systemd service unit |
| `~/.config/systemd/user/agency-dispatch.timer` | Systemd timer unit |

## Monitoring

- **Agent list** — a green pulse dot appears next to agents with active dispatch schedules. Gray dot if dispatch is disabled for the group.
- **Agent profile** — schedule pills show each rule (`at 09:00`, `every 6h`) with the associated prompt.
- **Logs** — dispatch output lands in the Logs section under the run date, one file per agent per run.
- **Settings** — shows whether the timer is active and the current heartbeat interval.
