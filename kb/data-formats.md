# Data Formats

Agency is a read/write dashboard — it doesn't run your agents. Your agents write clues, curiosities, and logs to the `shared/` directory as markdown files with YAML frontmatter. Agency reads those files and presents them in the UI.

## Clue Format

```yaml
---
agent: researcher
date: 2025-01-15T10:30:00
category: data-quality
status: open
float: false
linked_clues: []
linked_curiosity: ~
ttl_days: 14
---

Found inconsistency in the source dataset — three entries have duplicate IDs
but different content. This may affect downstream analysis.
```

### Clue Fields

| Field | Required | Description |
|-------|----------|-------------|
| `agent` | yes | Source agent name |
| `date` | yes | ISO 8601 datetime |
| `category` | no | Domain category for filtering |
| `status` | yes | `open`, `connected`, `dismissed`, `archived` |
| `float` | no | `true` promotes to "Floated Signals" in the inbox |
| `linked_clues` | no | List of related clue filenames |
| `linked_curiosity` | no | Filename of the curiosity this clue led to |
| `ttl_days` | no | Days before auto-archive (see TTL below) |

## Curiosity Format

```yaml
---
origin_agent: researcher
date: 2025-01-15
status: proposed
clues: [duplicate-ids-found.md, data-drift-detected.md]
feedback_requested: []
feedback_received: []
ttl_days: 30
---

Recommend implementing a deduplication pass before the analysis pipeline runs.
Two related clues suggest this is a systemic issue, not a one-off.
```

### Curiosity Fields

| Field | Required | Description |
|-------|----------|-------------|
| `origin_agent` | yes | Agent that proposed this |
| `date` | yes | ISO 8601 date |
| `status` | yes | `investigating`, `feedback`, `proposed`, `approved`, `deferred`, `rejected` |
| `clues` | no | List of source clue filenames |
| `feedback_requested` | no | Agents asked for input |
| `feedback_received` | no | Agents that responded |
| `ttl_days` | no | Days before auto-archive |

## Decision Format

Decisions are created through the UI when you approve, defer, or reject a curiosity:

```yaml
---
curiosity: deduplication-pass.md
decided_by: admin
date: 2025-01-16
decision: approved
---

Go ahead with the deduplication pass. Run it as a pre-processing step.
```

## TTL Enforcement

Clues and curiosities with a `ttl_days` field are automatically archived when `date + ttl_days` passes. Items already in terminal states (`archived`, `dismissed`, `approved`, `rejected`, `deferred`) are not affected. TTL is checked on each page load.

## Pipeline Relationships

Agency tracks the full chain across the pipeline:

- A **clue** can link to a curiosity via `linked_curiosity`
- A **curiosity** links back to its source clues via `clues`
- A **decision** links to its curiosity via `curiosity`

The UI renders these as clickable pipeline banners on each detail page, showing the full path from observation to action.
