# Agency — Agent Management Dashboard

> **What this is:** A FastAPI web app that manages multiple groups of AI agents. It's the unified control plane for monitoring agent observations, reviewing proposals, editing memory/prompts, and managing agent infrastructure.

## Architecture

- **Framework:** FastAPI + Jinja2 + Tailwind CSS (CDN, no build step)
- **Database:** None — entirely filesystem-based. Reads markdown files with YAML frontmatter from agent directories.
- **Config:** `config.yaml` — defines agent groups, Agency settings. Written atomically (temp + rename).
- **Deployment:** User-level systemd service (`agency.service`) on port 8500.
- **Host:** Fedora Kinoite (immutable OS). Python venv at `.venv/`.

## Project Structure

```
~/dev/agency/
├── app.py                    # Main FastAPI app (~1100 lines)
├── config.yaml               # Group registry + Agency settings
├── pyproject.toml             # Dependencies
├── agency.service             # Systemd service unit (user-level)
├── templates/                 # 18 Jinja2 templates
│   ├── base.html              # Layout: sidebar + main content
│   ├── home.html              # Inbox (open clues, decisions)
│   ├── clues.html             # Clue list with filters
│   ├── clue_detail.html       # Single clue + status change
│   ├── curiosities.html       # Curiosity list
│   ├── curiosity_detail.html  # Curiosity + decide form
│   ├── decisions.html         # Decision list
│   ├── decision_detail.html   # Single decision
│   ├── documents.html         # Agent documents browser
│   ├── document_view.html     # View/edit markdown, CSV, HTML
│   ├── logs.html              # Execution logs by date
│   ├── log_view.html          # Single log file
│   ├── prompts.html           # Dispatch prompt list
│   ├── prompt_detail.html     # View/edit prompt
│   ├── memory.html            # Agent memory list
│   ├── memory_view.html       # View/edit memory
│   ├── admin.html             # Admin: Agency settings + org management
│   └── admin_org_edit.html    # Create/edit org form
├── .venv/                     # Python virtual environment
└── CLAUDE.md                  # This file
```

## Config Format

```yaml
agency:
  title: Agency                    # App title shown in sidebar + page titles
  default_group: newsletter        # Group to redirect to from /

groups:
  newsletter:
    name: Newsletter Agents        # Display name
    path: /path/to/agents          # Filesystem path to agent directories
    agents: [agent1, agent2, ...]  # List of agent directory names
  chrisos:
    name: ChrisOS Agents
    path: /path/to/agents
    agents: [agent1, agent2, ...]
```

The `agency` section is optional — missing keys fall back to defaults.

## How Agent Groups Work

Each group points to a directory containing agent subdirectories and a `shared/` folder:

```
{group_path}/
├── {agent-name}/
│   ├── CLAUDE.md          # Agent role definition
│   ├── memory.md          # Persistent agent knowledge
│   └── .mcp.json          # MCP config (optional)
├── shared/
│   ├── clues/             # Agent observations (markdown + frontmatter)
│   ├── curiosities/       # Converged proposals
│   ├── decisions/         # Chris's decisions
│   ├── prompts/           # Dispatch routine prompts
│   ├── logs/              # Execution logs (YYYY-MM-DD subdirs)
│   └── memory.md          # Cross-agent shared knowledge
└── (optional: dispatch.sh, _subagents/, etc.)
```

The "Initialize" button in admin creates this structure for new groups.

## Route Structure

All org-scoped routes use `/{group}/` prefix. Admin routes are at `/admin/`.

### Org-Scoped Routes

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/{group}/` | Inbox — open clues, floated signals, recent decisions |
| GET | `/{group}/clues` | Clue list with agent/status filters |
| GET | `/{group}/clues/{slug}` | Clue detail + status change form |
| POST | `/{group}/clues/{slug}/status` | Update clue status |
| GET | `/{group}/curiosities` | Curiosity list |
| GET | `/{group}/curiosities/{slug}` | Curiosity detail + decide form |
| POST | `/{group}/curiosities/{slug}/decide` | Create decision for curiosity |
| GET | `/{group}/decisions` | Decision list |
| GET | `/{group}/decisions/{slug}` | Decision detail |
| GET | `/{group}/documents` | Browse agent documents |
| GET | `/{group}/documents/view?path=` | View/edit document |
| POST | `/{group}/documents/save` | Save document edits |
| GET | `/{group}/logs` | Execution logs by date |
| GET | `/{group}/logs/view?path=` | View log file |
| GET | `/{group}/prompts` | Dispatch prompt list |
| GET | `/{group}/prompts/{slug}` | View/edit prompt |
| POST | `/{group}/prompts/{slug}/save` | Save prompt edits |
| GET | `/{group}/memory` | Agent memory file list |
| GET | `/{group}/memory/view?path=` | View/edit memory file |
| POST | `/{group}/memory/save` | Save memory edits |

### Admin Routes

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/admin/` | Settings dashboard — Agency settings + org list |
| POST | `/admin/settings` | Update Agency title, default group |
| GET | `/admin/orgs/new` | New org form |
| POST | `/admin/orgs/create` | Create org (writes config, optionally initializes) |
| GET | `/admin/orgs/{org}/edit` | Edit org form |
| POST | `/admin/orgs/{org}/save` | Save org changes |
| POST | `/admin/orgs/{org}/delete` | Remove org from config |
| POST | `/admin/orgs/{org}/initialize` | Create shared/ folder structure |
| POST | `/admin/orgs/{org}/autodetect` | Scan path for directories with CLAUDE.md |

### Other Routes

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Redirect to default group |

## Data Model

All data is markdown with YAML frontmatter. No SQL, no migrations.

### Clue Frontmatter

```yaml
agent: infrastructure          # Source agent
date: 2026-03-20T06:00:00-04:00
category: container-health     # Domain category
status: open                   # open, connected, dismissed, archived
float: false                   # true = promoted to "Floated Signals"
linked_clues: []               # Related clue filenames
linked_curiosity: ~            # Promoted curiosity filename
ttl_days: 14                   # Days before auto-archive
```

### Curiosity Frontmatter

```yaml
origin_agent: infrastructure
date: 2026-03-20
status: investigating          # investigating, feedback, proposed, approved, deferred, rejected
clues: [clue1.md, clue2.md]
feedback_requested: []         # Agents asked for input
feedback_received: []          # Agents that responded
ttl_days: 30
```

### Decision Frontmatter

```yaml
curiosity: slug.md             # Linked curiosity
decided_by: chris
date: 2026-03-20
decision: approved             # approved, deferred, rejected
```

## Key Implementation Details

### Config Management
- `load_config()` reads config.yaml fresh
- `save_config(config)` writes atomically (temp file + `os.replace`)
- `reload_groups()` updates the global `GROUPS` dict after changes
- `get_agency_config()` returns Agency settings with backward-compatible defaults

### Security
- Path traversal protection: `fpath.resolve().relative_to(g["path"].resolve())` — validates file access is within the specific group's directory
- No auth — assumes local network / trusted access
- Delete operations require JS confirm()

### Template Context
Every org-scoped template gets via `group_context(g)`:
- `group` — current group key
- `group_name` — display name
- `groups` — dict of all group keys → names (for switcher)
- `agency_title` — from config

### Initialize Workflow
Creates the standard agent group folder structure. Idempotent — only creates missing dirs/files:
- `shared/clues/`, `shared/curiosities/`, `shared/decisions/`, `shared/prompts/`, `shared/logs/`
- `shared/memory.md` with default header
- `shared/prompts/_clue-system-steps.md` (copies from first existing group that has one)
- Per-agent directories from the agents list

## Current Agent Groups

### Newsletter Agents
- **Path:** `/var/home/chris/dev/local-newsletter/agents`
- **10 agents:** product, editorial, design, sales, business-ops, growth, sources, investigative, engineering, infrastructure
- **Dispatch:** `agents/shared/dispatch.sh` — time-windowed event dispatcher triggered by `newsletter-agents.timer`
- **Focus:** Hyperlocal newsletter platform (3 newsletters covering Nassau County, Long Island)

### ChrisOS Agents
- **Path:** `~/.claude/agents`
- **5 user-facing agents:** life-manager (orchestrator), program-manager (chief of staff), infrastructure (system admin), home (smart home + household), personal-style (wardrobe + inventory)
- **4 subagents:** troubleshooter, gaming, calendar-advisor, obsidian-navigator (in `_subagents/`)
- **Dispatch:** `shared/dispatch.sh` — 2-hour systemd timer with scheduled windows + event conditions
- **Focus:** Chris's personal life management, system administration, and home automation

## Development

### Running Locally

```bash
cd ~/dev/agency
.venv/bin/python3 app.py
# Serves at http://127.0.0.1:8500
```

### Dependencies

```
fastapi, uvicorn[standard], jinja2, markdown, pyyaml, markupsafe
```

Install: `.venv/bin/pip install -r` or from pyproject.toml.

### Service Management

```bash
# Status
systemctl --user status agency.service

# Restart (after code changes)
systemctl --user restart agency.service

# Logs
journalctl --user -u agency.service -f

# Enable on boot
systemctl --user enable agency.service
```

### Adding Features

1. Add route in `app.py`
2. Create template in `templates/`
3. Add nav link in `base.html` sidebar (if top-level page)
4. Restart service

Templates use Tailwind CSS via CDN — no build step needed. Custom prose styles for markdown rendering are in `base.html` `<style>` block.

### Template Filters

Available in all templates:
- `{{ status | status_badge }}` — colored pill for clue/curiosity status
- `{{ agent | agent_badge }}` — colored pill for agent name
- `{{ text | render_md }}` — markdown → HTML

## Coding Conventions

- **Routes:** Async FastAPI handlers, grouped by feature (clues, curiosities, decisions, documents, logs, prompts, memory, admin)
- **Helpers:** Pure functions that take a group dict `g` and return data
- **Templates:** Jinja2 with Tailwind utility classes. All org-scoped links use `{{ group }}` prefix.
- **Forms:** Standard HTML forms with POST + 303 redirect pattern
- **Config writes:** Always atomic (temp + rename). Always call `reload_groups()` after.
- **Security:** Always validate file paths against group's root directory before reading/writing

## System Environment

- **OS:** Fedora Kinoite 43 (immutable, rpm-ostree)
- **Python:** System python in venv (no dnf/yum — this is immutable)
- **Systemd:** User-level services only (`~/.config/systemd/user/`). System-level services CANNOT access `/var/home/chris/` on Fedora Kinoite — always use user-level.
- **Port:** 8500 (hardcoded in `app.py main()`)

## Future Ideas

- Real-time updates (WebSocket or SSE for live clue/decision notifications)
- Unified inbox across all groups (`/all/` route)
- Agent health monitoring (last dispatch time, error rate, memory size)
- Clue analytics (trends over time, agent activity heatmaps)
- Dark mode toggle
- Mobile-optimized decision workflow
