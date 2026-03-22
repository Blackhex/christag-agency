# Directory Structure

Agency expects each agent group to follow this layout:

```
your-agents/
├── agent-one/
│   ├── CLAUDE.md          # Agent role definition
│   ├── memory.md          # Persistent agent knowledge
│   └── headshot.png       # Optional avatar (png, jpg, webp)
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

The **Initialize** button in the admin panel creates the `shared/` structure for you. Agent directories are created automatically when you add agents through the admin panel or auto-detect them.

## Subagents

Agents in the `_subagents/` directory are treated as secondary — they appear in a collapsible section on the agents page and are excluded from dispatch lists. You can toggle any agent between regular and subagent status from its profile page.

## Logs

Execution logs are organized by date in `shared/logs/YYYY-MM-DD/` subdirectories. Log files are expected to follow the naming pattern `{agent-name}-{description}.out` or `.err`. Agency uses these to determine when an agent was last active and to build per-agent activity timelines.
