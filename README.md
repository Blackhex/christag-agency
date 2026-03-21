# Agency

A lightweight dashboard for managing multiple groups of AI agents across your machine. Monitor what your agents are observing, review their proposals, edit their memory and prompts, and manage their infrastructure — all from a single web UI.

**No database. No Docker. No build step.** Just a Python server that reads markdown files off disk.

## What It Does

Agency gives you a control plane for AI agents that communicate through the filesystem. Each agent group is a directory of agents that share observations (clues), proposals (curiosities), and decisions through markdown files with YAML frontmatter.

**Agent Profiles** — See each agent's identity, role definition, recent activity logs, and outstanding observations. Upload headshots, set display names, and toggle agents between primary and subagent roles.

**Inbox** — A prioritized view of what needs your attention: open clues from agents, proposals waiting for your decision, and recent decisions you've made.

**Clue/Curiosity/Decision Pipeline** — Agents observe things (clues). Observations converge into proposals worth considering (curiosities). You make the call (decisions). Agency surfaces this pipeline and lets you act on it.

**Document & Memory Editor** — Browse and edit agent documents, shared memory files, and dispatch prompts directly in the browser.

**Execution Logs** — View agent execution logs organized by date, filterable by agent.

**Multi-Group Support** — Manage separate agent groups (e.g., one for a project, another for personal automation) with a group switcher in the sidebar.

**Admin Panel** — Add, edit, and initialize new agent groups. Auto-detect agents by scanning directories for `CLAUDE.md` files. Optionally link a tmux session script per group for viewing/editing.

## Quick Start

```bash
# Install
pip install -e .

# Run (from any directory — config.yaml is created in your working directory)
agency

# Or with options
agency --port 8500 --host 0.0.0.0
```

On first run, Agency creates a default `config.yaml` and directs you to `http://localhost:8500/admin/` to set up your first agent group.

### Setting Up an Agent Group

1. Go to **Settings** in the sidebar
2. Click **+ Add New Group**
3. Give it a name and point it to a directory containing your agent subdirectories
4. Click **Initialize** to create the shared folder structure (`shared/clues/`, `shared/curiosities/`, etc.)
5. Use **Auto-detect Agents** to scan for directories containing a `CLAUDE.md`

### Expected Directory Structure

Agency expects each agent group to follow this layout:

```
your-agents/
├── agent-one/
│   ├── CLAUDE.md          # Agent role definition
│   ├── memory.md          # Persistent agent knowledge
│   └── headshot.png       # Optional avatar
├── agent-two/
│   └── CLAUDE.md
├── _subagents/            # Optional — agents called by other agents
│   └── helper-agent/
│       └── CLAUDE.md
└── shared/
    ├── clues/             # Agent observations (markdown + YAML frontmatter)
    ├── curiosities/       # Converged proposals
    ├── decisions/         # Your decisions
    ├── prompts/           # Dispatch routine prompts
    ├── logs/              # Execution logs (YYYY-MM-DD subdirectories)
    └── memory.md          # Cross-agent shared knowledge
```

The **Initialize** button in admin creates the `shared/` structure for you.

## Agent Identity

Agents can have display names, titles, and emoji avatars stored as YAML frontmatter in their `CLAUDE.md`:

```yaml
---
display_name: "Researcher"
title: "Senior Research Analyst"
emoji: "🔍"
---
# Research Agent

Your agent's role definition goes here...
```

You can also upload a headshot image through the agent profile page. These appear in the agent list and profile views.

## Configuration

Agency uses a `config.yaml` file in your working directory:

```yaml
agency:
  title: Agency                    # App title shown in sidebar
  default_group: my-project        # Group to show on startup
  decided_by: admin                # Default name for decisions

groups:
  my-project:
    name: My Project Agents
    path: /path/to/your/agents
    agents:
    - researcher
    - writer
    - reviewer
    tmux_config: /path/to/tmux-session.sh  # Optional
```

See `config.yaml.example` for a full template.

## Running as a Service

A systemd user service template is provided at `agency.service.example`. Copy and customize it:

```bash
cp agency.service.example ~/.config/systemd/user/agency.service
# Edit the file to set your paths

systemctl --user daemon-reload
systemctl --user enable --now agency.service
```

## Tech Stack

- **Python 3.11+** with FastAPI + Jinja2
- **Tailwind CSS** via CDN (no build step)
- **No database** — all state is markdown files on disk
- **No JavaScript framework** — vanilla HTML forms, `<details>` for collapsible sections
- **6 dependencies:** `fastapi`, `uvicorn`, `jinja2`, `markdown`, `pyyaml`, `markupsafe`

## How Agents Write Data

Agency is a read/write dashboard — it doesn't run your agents. Your agents write clues, curiosities, and logs to the `shared/` directory as markdown files with YAML frontmatter. Agency reads those files and presents them in the UI.

### Clue Format

```yaml
---
agent: researcher
date: 2025-01-15T10:30:00
category: data-quality
status: open
float: false
ttl_days: 14
---

Found inconsistency in the source dataset — three entries have duplicate IDs
but different content. This may affect downstream analysis.
```

### Curiosity Format

```yaml
---
origin_agent: researcher
date: 2025-01-15
status: proposed
clues: [duplicate-ids-found.md, data-drift-detected.md]
ttl_days: 30
---

Recommend implementing a deduplication pass before the analysis pipeline runs.
Two related clues suggest this is a systemic issue, not a one-off.
```

Agency lets you **approve**, **defer**, or **reject** curiosities through the UI, creating decision records that your agents can read.

## Screenshots

*Coming soon*

## License

MIT
