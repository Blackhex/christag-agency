# Agency — Agent Management Dashboard

> **What this is:** A FastAPI web app that manages multiple groups of AI agents across any LLM tool. It's the unified control plane for monitoring agent observations, reviewing proposals, editing memory/prompts, and managing agent infrastructure — regardless of whether your agents use Claude Code, Codex, Gemini, Aider, Goose, or custom scripts.

## Architecture

- **Framework:** FastAPI + Jinja2 + Tailwind CSS (CDN, no build step)
- **Database:** None — entirely filesystem-based. Reads markdown files with YAML frontmatter from agent directories.
- **Config:** `config.yaml` — defines agent groups, Agency settings. Written atomically (temp + rename).
- **Integrations:** Plugin system (`agency/integrations/`) translates between LLM tools and Agency's internal model. Each agent declares which integration it uses.
- **Dispatch:** Python-based scheduler (`agency/dispatch/run.py`) with platform-native timers (systemd on Linux, launchd on macOS).
- **Deployment:** User-level systemd service (`agency.service`) on port 8500.

## Project Structure

```
~/dev/agency/
├── agency/                    # Python package
│   ├── app.py                 # Main FastAPI app (~2500 lines)
│   ├── cli.py                 # CLI interface (agency inbox, status, decide, etc.)
│   ├── config.py              # Shared config utilities (normalize_agents, agent_names)
│   ├── __init__.py
│   ├── integrations/          # LLM integration plugin system
│   │   ├── __init__.py        # BaseIntegration, registry, config-driven loading
│   │   ├── integrations.yaml  # Which integrations are loaded (managed by admin UI)
│   │   ├── _template.py       # Scaffolding for new integrations
│   │   ├── agency/            # Official integrations
│   │   │   ├── claude_code.py
│   │   │   ├── codex.py
│   │   │   ├── gemini.py
│   │   │   ├── aider.py
│   │   │   ├── goose.py
│   │   │   ├── script.py
│   │   │   └── sdk.py
│   │   └── {author}/          # Community integrations
│   ├── dispatch/              # Dispatch system
│   │   ├── run.py             # Python dispatch runner (replaces dispatch.sh)
│   │   ├── install.py         # Platform-native timer installer
│   │   └── __init__.py
│   ├── workspaces/            # Workspace plugin system
│   │   ├── __init__.py        # BaseWorkspace, REGISTRY, migration
│   │   ├── tmux.py            # tmux session layout
│   │   ├── cursor.py          # Cursor IDE
│   │   ├── superset.py        # Superset.sh orchestrator
│   │   ├── ide.py             # Generic IDE (VS Code, Windsurf, JetBrains)
│   │   ├── chat.py            # Chat platforms (Slack, Mattermost, Discord)
│   │   └── custom.py          # Custom config file
│   └── templates/             # 27 Jinja2 templates
│       ├── base.html          # Layout: sidebar + main content
│       ├── home.html          # Mission control dashboard (fleet, pipeline, attention queue, activity)
│       ├── agents.html        # Agent list with health dots + integration badges
│       ├── agent_profile.html # Agent profile: identity, integration, timeline, schedule
│       ├── observations.html   # Observation list with filters
│       ├── observation_detail.html # Single observation + pipeline chain + status change
│       ├── proposals.html     # Proposal list
│       ├── proposal_detail.html # Proposal + pipeline chain + decide form
│       ├── decisions.html     # Decision list
│       ├── decision_detail.html # Single decision + pipeline chain
│       ├── documents.html     # Agent documents browser
│       ├── document_view.html # View/edit markdown, CSV, HTML
│       ├── logs.html          # Execution logs by date
│       ├── log_view.html      # Single log file
│       ├── prompts.html       # Dispatch prompts with agent assignments + schedule editing
│       ├── prompt_detail.html # View/edit prompt content
│       ├── memory.html        # Agent memory list
│       ├── memory_view.html   # View/edit memory
│       ├── admin.html         # Admin: redirects to settings
│       ├── admin_settings.html # Admin: app settings + installed integrations table
│       ├── admin_integrations.html # Admin: integration management + registration
│       ├── admin_dispatch.html # Admin: dispatch timer management
│       ├── admin_groups.html  # Admin: agent group list + management
│       ├── admin_org_edit.html # Create/edit org + dispatch schedule + default integration
│       ├── admin_agent_detail.html # Admin agent detail view
│       ├── setup.html         # First-run wizard
│       ├── setup_complete.html # Post-setup "touch grass" finale page
│       ├── workspaces.html        # Workspace list — runtime frontend configs
│       └── workspace_detail.html  # Workspace config file viewer/editor
├── tests/                     # Test suite (98 tests)
│   ├── conftest.py            # Shared fixtures
│   ├── test_integrations.py   # Registry, detection, base classes
│   ├── test_integration_claude_code.py
│   ├── test_integration_sidecar.py  # Codex, Gemini, Aider, Goose
│   ├── test_integration_script.py
│   ├── test_integration_sdk.py
│   ├── test_config_normalization.py
│   ├── test_dispatch_run.py
│   ├── test_dispatch_install.py
│   ├── test_display_titles.py       # Display title extraction
│   ├── test_needs_action.py         # Needs action metric
│   ├── test_dashboard.py            # Dashboard helpers (pipeline stats, activity feed)
│   └── test_cli.py                  # CLI interface
├── kb/                        # User-facing documentation
├── docs/                      # Specs and plans
├── config.yaml                # Group registry + Agency settings
├── pyproject.toml             # Dependencies
├── .venv/                     # Python virtual environment
└── CLAUDE.md                  # This file
```

## Integration System

Agency uses a plugin system to support multiple LLM tools. Each integration is a Python class that handles:

1. **Execution** — how to invoke the tool, pass a prompt, capture output
2. **Identity translation** — map the tool's native file to Agency's agent identity model
3. **Detection** — identify whether an agent directory belongs to this tool
4. **AI backbone** — optionally provide LLM access for Agency's own AI features

Integrations are organized by author namespace: official integrations live in `agency/integrations/agency/`, and community integrations live in `agency/integrations/{author}/`. Which integrations are loaded is controlled by `agency/integrations/integrations.yaml`, managed through the admin UI at `/admin/integrations`.

### Shipped Integrations

| Integration | Native File | Detect Signal | Execution | AI Backend |
|-------------|------------|---------------|-----------|------------|
| `claude-code` | `CLAUDE.md` | CLAUDE.md exists | `claude -p` | Yes |
| `codex` | `AGENTS.md` | AGENTS.md exists | `codex exec --yolo` | Yes |
| `gemini` | `GEMINI.md` | GEMINI.md exists | `gemini -p` | Yes |
| `aider` | `CONVENTIONS.md` | .aider.conf.yml exists | `aider --message-file` | No |
| `goose` | `.goosehints` | .goosehints exists | `goose run` | Yes |
| `script` | `agent.md` | Never (explicit config) | User command template | No |
| `sdk` | `agent.md` | agent.md exists (fallback) | None (external) | No |

### Integration Resolution

When Agency needs to interact with an agent, it resolves the integration in this order:

1. **Filesystem detection** — check what identity file exists on disk (CLAUDE.md, AGENTS.md, etc.)
2. **Config** — fall back to the agent's `integration` field in config.yaml
3. **Group default** — fall back to the group's `default_integration`
4. **Global default** — fall back to `claude-code`

This ensures an agent with CLAUDE.md is always handled correctly, even if the group default is different.

Only integrations listed in `integrations.yaml` are loaded at startup. The admin UI at `/admin/integrations` lets you register or unregister integrations without editing files directly.

### Sidecar Metadata

Tools whose native files don't support YAML frontmatter (Codex, Gemini, Aider, Goose) store Agency metadata in `.agency-meta.yaml`:

```yaml
display_name: Product Manager
title: Content Strategy Lead
emoji: "📦"
```

### Adding New Integrations

1. Copy `agency/integrations/_template.py` to `agency/integrations/{author}/{your_tool}.py`
2. Fill in all methods following the template's inline guidance
3. Register the integration via the admin UI at `/admin/integrations`

See `kb/contributing-integrations.md` for a complete walkthrough.

## Workspace System

Workspaces represent how users visualize and interact with their agent groups at runtime — tmux grids, IDE windows, chat channels, dedicated UIs, etc. The system is extensible via plugins, modeled after the integration system.

### Shipped Workspace Plugins

| Plugin | Description | Key Config | Launch | Detect |
|--------|------------|------------|--------|--------|
| `tmux` | Terminal multiplexer session | `script_path` | Yes | `tmux-*.sh` |
| `cursor` | Cursor IDE with rules | `project_path` | Yes | `.cursor/rules/` |
| `superset` | Superset.sh orchestrator | `project_path` | Yes | `.superset/config.json` |
| `ide` | Generic IDE (VS Code, etc.) | `ide_name`, `project_path` | Yes | No |
| `chat` | Chat platform (Slack, etc.) | `platform`, `channel_url` | No | No |
| `custom` | Any config file | `config_path`, `language` | Yes | No |

### Adding New Workspace Plugins

1. Create `agency/workspaces/your_plugin.py`
2. Subclass `BaseWorkspace`, implement methods
3. Call `_register(YourPlugin())` at module level
4. Import in `agency/workspaces/__init__.py`

### Config Migration

superseded `tmux_config` (single path string) is auto-migrated to the `workspaces` list at config load time. The migration is in-memory only — config.yaml is not rewritten until the user saves from admin.

## Config Format

```yaml
agency:
  title: Agency                    # App title shown in sidebar + page titles
  default_group: newsletter        # Group to redirect to from /
  ai_backend: claude-code          # Integration Agency uses for its own AI features
  dispatch:
    installed: true                # Set after first dispatch init
    interval: 15                   # Heartbeat interval in minutes

groups:
  newsletter:
    name: Newsletter Agents        # Display name
    path: /path/to/agents          # Filesystem path to agent directories
    default_integration: claude-code  # Default integration for agents in this group
    agents:                        # List of agents (string shorthand or dict form)
    - product                      # Shorthand: inherits group default_integration
    - editorial
    - name: custom-bot             # Dict form: explicit integration
      integration: script
      integration_config:
        command: "./run.sh {prompt_file}"
    workspaces:                        # How users interact with this group at runtime
      - name: Terminal Grid
        type: tmux
        config:
          script_path: /path/to/tmux-agents.sh
    dispatch:                      # Per-group dispatch config (optional)
      enabled: true
      timeout: 300                 # Seconds per agent run
      daily_limit: 20              # Max runs per day for this group
      agents:                      # Per-agent schedule rules
        product:
          - prompt: morning.md
            at: "09:00"
          - prompt: routine.md
            every: 6h
          - prompt: quality-gate.md
            at: "06:00"
            condition: pre-send    # Code-triggered (read-only in UI)
```

The `agency`, `dispatch`, `default_integration`, and `ai_backend` sections are optional — missing keys fall back to defaults.

### Agent List Format

Agents can be specified as bare strings (shorthand) or dicts (full form):

- `"product"` → `{"name": "product", "integration": "<group default>"}`
- `{"name": "bot", "integration": "script", "integration_config": {...}}` → explicit integration
- `{"name": "pm", "path": "/shared/agents/pm"}` → shared agent with external path

Config normalization happens at load time. The shorthand is never rewritten to disk.

Agents with a `path` override resolve their directory from the configured path instead of `{group_path}/{name}`. This allows the same agent directory to be shared across multiple groups — useful for program-manager-style agents that span projects. All groups that reference the agent can read and edit its files.

### Dispatch Rule Fields

| Field | Required | Description |
|-------|----------|-------------|
| `prompt` | Yes | Filename in `shared/prompts/` |
| `at` | One of at/every | Daily time (HH:MM) |
| `every` | One of at/every | Recurring interval (e.g., `6h`, `30m`) |
| `condition` | No | Code condition name — makes rule read-only in UI, skipped by Python dispatcher |

Rules with `condition` are skipped by the Python dispatcher with an info log. Groups that need condition-based dispatch can provide their own `shared/dispatch.sh` script, run independently.

## How Agent Groups Work

Each group points to a directory containing agent subdirectories and a `shared/` folder:

```
{group_path}/
├── {agent-name}/
│   ├── <identity-file>    # Tool-specific: CLAUDE.md, AGENTS.md, GEMINI.md, agent.md, etc.
│   ├── memory.md          # Persistent agent knowledge
│   └── .mcp.json          # MCP config (optional)
├── shared/
│   ├── observations/      # Agent observations (markdown + frontmatter)
│   ├── proposals/         # Converged proposals
│   ├── decisions/         # User decisions
│   ├── prompts/           # Dispatch routine prompts
│   ├── logs/              # Execution logs (YYYY-MM-DD subdirs)
│   └── memory.md          # Cross-agent shared knowledge
└── (optional: _subagents/, etc.)
```

The identity file depends on the agent's integration. Agency auto-detects it from the filesystem.

The "Initialize" button in admin creates this structure for new groups.

## Route Structure

All org-scoped routes use `/{group}/` prefix. Admin routes are at `/admin/`.

### Org-Scoped Routes

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/{group}/` | Mission control — fleet status, pipeline pulse, attention queue, activity feed |
| GET | `/{group}/observations` | Observation list with agent/status filters |
| GET | `/{group}/observations/{slug}` | Observation detail + status change form |
| POST | `/{group}/observations/{slug}/status` | Update observation status |
| GET | `/{group}/proposals` | Proposal list |
| GET | `/{group}/proposals/{slug}` | Proposal detail + decide form |
| POST | `/{group}/proposals/{slug}/decide` | Create decision for proposal |
| GET | `/{group}/decisions` | Decision list |
| GET | `/{group}/decisions/{slug}` | Decision detail |
| POST | `/{group}/decisions/{slug}/retry` | Retry execution of approved decision |
| GET | `/{group}/documents` | Browse agent documents |
| GET | `/{group}/documents/view?path=` | View/edit document |
| POST | `/{group}/documents/save` | Save document edits |
| GET | `/{group}/logs` | Execution logs by date |
| GET | `/{group}/logs/view?path=` | View log file |
| GET | `/{group}/prompts` | Dispatch prompts with agent assignments |
| GET | `/{group}/prompts/{slug}` | View/edit prompt content |
| POST | `/{group}/prompts/{slug}/save` | Save prompt content edits |
| POST | `/{group}/prompts/dispatch` | Save dispatch assignments from prompts page |
| GET | `/{group}/memory` | Agent memory file list |
| GET | `/{group}/memory/view?path=` | View/edit memory file |
| POST | `/{group}/memory/save` | Save memory edits |
| GET | `/{group}/workspaces` | Workspace list — runtime frontend configs |
| GET | `/{group}/workspaces/{idx}/file` | View/edit workspace config file |
| POST | `/{group}/workspaces/{idx}/file/save` | Save workspace file edits |

### Agent Routes

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/{group}/agents` | Agent list with health dots + integration badges |
| GET | `/{group}/agents/{agent}` | Agent profile: identity, integration, timeline, schedule |
| POST | `/{group}/agents/{agent}/identity` | Save identity fields (display name, title, emoji) |
| POST | `/{group}/agents/{agent}/definition` | Save agent definition body |
| POST | `/{group}/agents/{agent}/upload-headshot` | Upload agent avatar |
| GET | `/{group}/agents/{agent}/headshot` | Serve headshot image |
| POST | `/{group}/agents/{agent}/toggle-subagent` | Toggle regular/subagent status |

### Admin Routes

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/admin/` | Admin settings page + installed integrations table |
| GET | `/admin/dispatch` | Dispatch timer management page |
| GET | `/admin/groups` | Agent group list + management |
| POST | `/admin/settings` | Update Agency title, default group, AI backend, dispatch interval |
| POST | `/admin/dispatch/install` | Install platform-native dispatch timer |
| GET | `/admin/orgs/new` | New org form |
| POST | `/admin/orgs/create` | Create org (writes config, optionally initializes) |
| GET | `/admin/orgs/{org}/edit` | Edit org form + dispatch schedule + default integration |
| POST | `/admin/orgs/{org}/save` | Save org changes (including default_integration) |
| POST | `/admin/orgs/{org}/dispatch` | Save dispatch config for group |
| POST | `/admin/orgs/{org}/delete` | Remove org from config |
| POST | `/admin/orgs/{org}/initialize` | Create shared/ folder structure |
| POST | `/admin/orgs/{org}/autodetect` | Scan path for directories with recognized definition files |
| GET | `/admin/orgs/{org}/agents/{agent}` | Admin agent detail view |
| POST | `/admin/orgs/{org}/agents/{agent}/save` | Save agent definition + per-agent integration |
| POST | `/admin/orgs/{org}/agents/create` | Create new agent in org |
| POST | `/admin/orgs/{org}/agents/{agent}/rename` | Rename agent directory |
| POST | `/admin/orgs/{org}/agents/{agent}/delete` | Delete agent from org |
| GET | `/admin/integrations` | Integration management page |
| POST | `/admin/integrations/register` | Register an available integration |
| POST | `/admin/integrations/unregister` | Unregister an installed integration |
| POST | `/admin/integrations/restart` | Restart service to apply changes |

### Other Routes

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Redirect to default group |
| GET | `/setup` | First-run setup wizard |
| POST | `/setup` | Process setup wizard |
| POST | `/tips/dismiss` | Dismiss a single tip |
| POST | `/tips/hide-all` | Hide all tips |
| GET | `/setup/complete/{group}` | Post-setup "touch grass" page |

## Data Model

All data is markdown with YAML frontmatter. No SQL, no migrations.

### Observation Frontmatter

```yaml
agent: infrastructure          # Source agent
date: 2026-03-20T06:00:00-04:00
category: container-health     # Domain category
status: open                   # open, connected, dismissed, archived
float: false                   # true = promoted to "Floated Signals"
linked_observations: []        # Related observation filenames
linked_proposal: ~             # Promoted proposal filename
ttl_days: 14                   # Days before auto-archive
```

### Proposal Frontmatter

```yaml
origin_agent: infrastructure
date: 2026-03-20
status: proposed              # investigating, proposed, decided, archived
observations: [obs1.md, obs2.md]
feedback_requested: []         # Agents asked for input
feedback_received: []          # Agents that responded
ttl_days: 30
questions:
  - id: approve
    type: boolean
    prompt: "Approve this proposal?"
```

### Decision Frontmatter

```yaml
proposal: slug.md              # Linked proposal
decided_by: admin
date: 2026-03-20
answers:
  approve: approved
  color: "Blue"
execution_status: pending      # pending, running, complete, failed
execution_summary: ~
```

## Key Implementation Details

### Config Management
- `load_config()` reads config.yaml fresh
- `save_config(config)` writes atomically (temp file + `os.replace`)
- `reload_groups()` updates the global `GROUPS` dict after changes, normalizes agent lists
- `get_agency_config()` returns Agency settings with backward-compatible defaults
- `normalize_agents()` (in `agency/config.py`) converts bare string agent lists to dicts with integration info
- `get_agent_dir(g, agent_name)` (in `agency/config.py`) resolves agent directory — checks for `path` override in config, falls back to `g["path"] / name`
- `get_allowed_roots(g)` (in `agency/config.py`) returns allowed filesystem roots for path validation — group path + any external agent paths

### Integration System
- `agency/integrations/__init__.py` — `BaseIntegration` base class, `REGISTRY`, `get_integration()`, `detect_integration()`
- `get_agent_integration(g, agent_name)` — resolves integration: filesystem detection first, then config, then group default
- `parse_agent_identity(agent_dir, integration)` — reads identity via integration's native file
- `save_agent_identity()` / `save_agent_definition()` — writes via integration, preserving native format
- Identity files are filtered from the document browser automatically

### Dispatch System
- Python dispatcher at `agency/dispatch/run.py` — called by OS-native timer
- Platform installer at `agency/dispatch/install.py` — supports systemd (Linux) and launchd (macOS)
- `get_dispatch_status()` checks platform-native timer state
- `install_dispatch()` delegates to the platform installer
- Schedule rules: `at` (daily at specific time) and `every` (recurring interval)
- Condition rules are skipped by the Python dispatcher (require per-group scripts)
- TTL-style marker files for dedup: `.event-*` for `at` rules, `.last-*` for `every` rules

### Agent Profiles
- `build_agent_timeline()` interleaves logs and observations chronologically
- `agent_health_status()` returns green/amber/red based on last seen time
- Schedule pills shown from `config.dispatch.agents.{name}` rules
- Integration badge shown next to agent name

### Mission Control Dashboard
- `build_pipeline_stats()` computes per-stage counts, 7-day sparkline buckets, and flow health (healthy/bottleneck)
- `build_activity_feed()` merges observations and proposals into a chronological cross-agent feed
- `extract_display_title()` extracts first `**bold text**` from markdown body as display title, falls back to slug
- Dashboard has four zones: fleet status bar, pipeline pulse, attention queue (with inline decide actions), activity feed
- Inline proposal actions use the existing `proposal_decide()` route via form POST

### CLI Interface
- `agency/cli.py` — terminal interface using argparse, imports helpers from `app.py`
- Entry point: `agency` (via pyproject.toml `[project.scripts]`)
- Subcommands: `serve`, `inbox`, `status`, `observations`, `proposals`, `decisions`, `decide`, `agents`
- `--group` flag defaults to `agency.default_group` from config.yaml
- `--json` flag on list commands for scripting
- ANSI color output (auto-detected)

### Pipeline Relationships
- Observation detail resolves `linked_proposal` → proposal → decision chain
- Proposal detail shows originating observations + resulting decision
- Decision detail traces back through proposal to source observations
- All rendered as clickable pipeline banners with color-coded steps

### TTL Enforcement
- `check_ttl_expired()` and `enforce_ttl()` auto-archive stale items
- Called from `list_observations()` and `list_proposals()` on every page load
- Rewrites status to "archived" in the markdown file frontmatter
- Skips items already in terminal states

### Security
- Path traversal protection: `fpath.resolve().relative_to(g["path"].resolve())` — validates file access is within the specific group's directory
- No auth — assumes local network / trusted access. Use a reverse proxy (Traefik, nginx) for auth.
- Delete operations require JS confirm()

### Template Context
Every org-scoped template gets via `group_context(g)`:
- `group` — current group key
- `group_name` — display name
- `groups` — dict of all group keys → names (for switcher)
- `agency_title` — from config
- `nav_open_observations`, `nav_actionable`, `nav_agent_count` — sidebar counts
- `workspaces` — list of workspace dicts for the group
- `workspaces_available` — bool, whether any workspaces are configured

### Initialize Workflow
Creates the standard agent group folder structure. Idempotent — only creates missing dirs/files:
- `shared/observations/`, `shared/proposals/`, `shared/decisions/`, `shared/prompts/`, `shared/logs/`
- `shared/memory.md` with default header
- `shared/prompts/_observation-system-steps.md` (copies from first existing group that has one)
- Per-agent directories from the agents list

## Development

### Running Locally

```bash
# Web dashboard
cd ~/dev/agency
.venv/bin/python3 -m agency.app
# Serves at http://127.0.0.1:8500

# CLI
.venv/bin/python3 -m agency.cli status
.venv/bin/python3 -m agency.cli inbox --group newsletter
```

Or via the installed entry point:
```bash
agency serve          # Web dashboard
agency inbox          # What needs attention
agency status         # Fleet overview
agency decide <slug>  # Submit answers for a proposal
```

### Dependencies

```
fastapi<0.116, starlette<1.0, uvicorn[standard], jinja2, markdown, pyyaml, markupsafe, python-multipart
```

Install: `.venv/bin/pip install -e .` from pyproject.toml.

### Running Tests

```bash
.venv/bin/python -m pytest tests/ -v
```

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
- `{{ status | status_badge }}` — colored pill for observation/proposal status
- `{{ agent | agent_badge }}` — colored pill for agent name
- `{{ name | integration_badge }}` — colored pill for integration name
- `{{ text | render_md }}` — markdown → HTML
- `{{ dt | relative_time }}` — datetime to "5m ago", "2h ago", etc.

## Coding Conventions

- **Routes:** Async FastAPI handlers, grouped by feature (observations, proposals, decisions, documents, logs, prompts, memory, admin)
- **Helpers:** Pure functions that take a group dict `g` and return data
- **Integrations:** Each integration is a Python class in `agency/integrations/` implementing `BaseIntegration`
- **Templates:** Jinja2 with Tailwind utility classes. All org-scoped links use `{{ group }}` prefix.
- **Forms:** Standard HTML forms with POST + 303 redirect pattern
- **Config writes:** Always atomic (temp + rename). Always call `reload_groups()` after.
- **Security:** Always validate file paths against group's root directory before reading/writing
- **Identity resolution:** Always detect from filesystem first, fall back to config

## System Environment

- **OS:** Fedora Kinoite 43 (immutable, rpm-ostree) — but Agency runs on any OS with Python 3.11+
- **Python:** System python in venv (no dnf/yum — this is immutable)
- **Systemd:** User-level services only (`~/.config/systemd/user/`). System-level services cannot access user home directories on Fedora Kinoite — always use user-level.
- **Port:** 8500 (hardcoded in `app.py main()`)

## Future Ideas

- Real-time updates (WebSocket or SSE for live observation/decision notifications)
- Unified inbox across all groups (`/all/` route)
- Event-based dispatch conditions (`if` rules — e.g., "run if unread email > 20")
- Observation analytics (trends over time, agent activity heatmaps)
- MCP config viewing/editing on agent profile page
- Skills CRUD + SkillsMCP marketplace integration
- Per-agent integration change from profile page dropdown
- Windows Task Scheduler support for dispatch
- Dashboard Phase 2: Keyboard navigation (j/k movement, a/d/x hotkeys)
- Dashboard Phase 3: Auto-refresh (poll JSON endpoint every 30-60s)
- Dashboard Phase 4: Activity heatmap (48h agent activity grid)
