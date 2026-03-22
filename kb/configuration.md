# Configuration

Agency uses a `config.yaml` file in your working directory:

```yaml
agency:
  title: Agency                    # App title shown in sidebar
  default_group: my-project        # Group to show on startup
  decided_by: admin                # Default name for decisions
  dispatch:
    installed: true                # Set after first dispatch init
    interval: 15                   # Heartbeat interval in minutes

groups:
  my-project:
    name: My Project Agents
    path: /path/to/your/agents
    agents:
    - researcher
    - writer
    - reviewer
    tmux_config: /path/to/tmux-session.sh  # Optional
    dispatch:                      # Optional — see kb/dispatch.md
      enabled: true
      timeout: 300
      daily_limit: 20
      agents:
        researcher:
          - prompt: morning-scan.md
            at: "09:00"
```

## Agency Settings

| Key | Default | Description |
|-----|---------|-------------|
| `title` | `Agency` | App title in sidebar and page titles |
| `default_group` | first group | Group to redirect to from `/` |
| `decided_by` | `admin` | Default name attached to decisions |
| `dispatch.installed` | `false` | Set automatically after dispatch init |
| `dispatch.interval` | `15` | Heartbeat interval in minutes (5-120) |

## Group Settings

| Key | Required | Description |
|-----|----------|-------------|
| `name` | yes | Display name for the group |
| `path` | yes | Filesystem path to the agent directory |
| `agents` | yes | List of agent directory names |
| `tmux_config` | no | Path to a tmux session script for this group |
| `dispatch.enabled` | no | Enable dispatch scheduling for this group |
| `dispatch.timeout` | no | Seconds per agent run (default 300) |
| `dispatch.daily_limit` | no | Max agent runs per day (default 20) |
| `dispatch.agents` | no | Per-agent schedule rules (see [Dispatch](dispatch.md)) |

## Managing Groups

Groups can be added, edited, and removed from the admin panel at `/admin/`. The admin panel also provides:

- **Initialize** — creates the `shared/` folder structure for a group
- **Auto-detect Agents** — scans the group path for directories containing a `CLAUDE.md` file
- **Agent CRUD** — create, rename, and delete individual agents

Config writes are atomic (temp file + rename) and the group registry is reloaded after every change.
