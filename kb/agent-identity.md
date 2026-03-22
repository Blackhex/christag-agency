# Agent Identity

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

All identity fields are optional. If omitted, the directory name is used as the display name.

## Headshots

Upload a headshot image (PNG, JPG, or WebP, max 2MB) through the agent profile page. The image is saved as `headshot.{ext}` in the agent's directory and appears on the agent list and profile views.

## Editing Identity

Identity fields can be edited from the agent profile page in the UI. Changes are written back to the `CLAUDE.md` frontmatter, preserving the rest of the file.

## Health Pulse

The agent list shows a color-coded dot next to each agent's "last seen" time:

- **Green** — active within the last 24 hours
- **Amber** — 24-48 hours since last activity
- **Red** — 48+ hours or no recorded activity

Health is derived from log file timestamps — no configuration needed.
