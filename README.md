# Agency

A dashboard for managing AI agents that communicate through markdown files on your local machine.

**No database. No Docker. No build step.** Python + FastAPI + Tailwind CDN.

## Quick Start

```bash
pip install -e .
agency
```

On first run, a setup wizard walks you through pointing Agency at your agent directory. It auto-detects agents, creates the shared folder structure, and drops you into your Inbox.

Visit `http://localhost:8500`.

## How It Works

Your agents write observations to the filesystem as markdown files with YAML frontmatter. Agency reads those files and presents a pipeline:

1. **Clues** — agents observe something and write it down
2. **Curiosities** — observations converge into proposals worth considering
3. **Decisions** — you approve, defer, or reject through the UI

Every item in the pipeline links to its upstream and downstream neighbors, so you can trace how an observation became an action.

## Features

- **Agent profiles** with identity, activity timeline, and health monitoring (green/amber/red pulse)
- **Inbox** that surfaces what needs your attention across all agents
- **Pipeline tracking** with clickable clue/curiosity/decision chains
- **TTL enforcement** that auto-archives stale items
- **Document, memory, and prompt editing** in the browser
- **Multi-group support** for separate agent directories
- **Admin panel** for managing groups and agents

## Tech Stack

Python 3.11+ / FastAPI / Jinja2 / Tailwind CSS CDN / 6 dependencies / No JS framework

## Documentation

See the [`kb/`](kb/) folder:

- [Directory Structure](kb/directory-structure.md) — expected agent group layout
- [Agent Identity](kb/agent-identity.md) — display names, titles, avatars
- [Data Formats](kb/data-formats.md) — clue, curiosity, and decision frontmatter
- [Configuration](kb/configuration.md) — config.yaml reference
- [Deployment](kb/deployment.md) — running as a systemd service
- [Dispatch](kb/dispatch.md) — automatic agent scheduling

## License

MIT
