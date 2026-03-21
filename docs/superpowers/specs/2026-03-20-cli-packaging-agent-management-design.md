# CLI Packaging + Agent Management Design

**Date:** 2026-03-20
**Status:** Draft

---

## Overview

Two features that transform Agency from a personal tool into something shippable to colleagues:

1. **CLI Packaging** — `pip install` + `agency` starts the server, first-run bootstrapping via GUI
2. **Agent Management** — agent list page, agent profile page with logs/clues/identity, cross-linking, subagent support, optional tmux config per group

Plus a bug fix: admin panel sidebar links are broken (render as `/clues` instead of `/{group}/clues`).

---

## Bug Fix: Admin Sidebar Links

**Problem:** When viewing admin pages, the sidebar nav links render as `/clues`, `/curiosities`, etc. instead of `/{group}/clues` because the `group` template variable is not set in admin route contexts.

**Fix:** The admin templates pass `groups` dict but not a current `group`. The sidebar should either:
- Hide the org-scoped nav items when on admin pages (since there's no selected group), OR
- Default `group` to the first available group key so links remain functional

**Decision:** Hide org-scoped nav items when `admin_active` is true. The admin page is about settings, not browsing a group's data. The group switcher dropdown should still appear, and selecting a group navigates to that group's inbox. This is the cleaner approach — the admin page has its own nav context.

**Implementation:** In `base.html`, wrap the org-scoped nav links (Inbox through Memory) in `{% if not admin_active %}`. The "Settings" link under "Admin" stays visible always.

---

## Feature 1: CLI Packaging

### Entry Point

Refactor `app.py:main()` to accept CLI arguments via `argparse`:

```
agency [--port PORT] [--host HOST]
```

- `--port`: default 8500
- `--host`: default 0.0.0.0

The existing `pyproject.toml` already declares `[project.scripts] agency = "app:main"`. No new files needed — just enhance `main()`.

### Config Location Strategy

Config is resolved from the **current working directory**, not relative to `__file__`. This is the correct behavior for a CLI tool — you run `agency` from your project directory, and it reads/creates `config.yaml` there.

```python
CONFIG_PATH = Path.cwd() / "config.yaml"
```

This means:
- When developing: `cd ~/dev/agency && agency` reads `~/dev/agency/config.yaml`
- When a colleague uses it: `cd ~/my-agents && agency` reads `~/my-agents/config.yaml`
- Templates still resolve via `Path(__file__).parent / "templates"` (they ship with the package)

**First-run:** If `config.yaml` does not exist in CWD on startup:
1. Create a default `config.yaml`:
   ```yaml
   agency:
     title: Agency
     default_group: ""
   groups: {}
   ```
2. Print to stdout: `First run — created config.yaml in {CWD}. Visit http://localhost:{port}/admin/ to set up your first agent group.`

**Empty groups guard:** Fix existing `get_agency_config()` to not crash on empty groups dict. The fallback `list(groups.keys())[0]` raises `IndexError` when groups is empty. Fix: return `""` as default_group when no groups exist.

### Packaging Structure

The project needs restructuring into a proper Python package for `pip install` to work:

```
agency/
├── agency/
│   ├── __init__.py        # empty
│   ├── app.py             # main app (moved from root)
│   └── templates/         # Jinja2 templates (moved from root)
├── pyproject.toml
├── CLAUDE.md
└── docs/
```

`pyproject.toml` updates:
```toml
[project.scripts]
agency = "agency.app:main"

[tool.setuptools.package-data]
agency = ["templates/*.html"]
```

Template resolution changes from `Path(__file__).parent / "templates"` — still works since templates move with `app.py`.

**Alternative (simpler, recommended):** Keep the flat structure and use `py_modules` instead of packages. `setuptools` supports `py_modules = ["app"]` for single-file modules. However, bundling templates requires the package approach. **Go with the package restructure** — it's a one-time cost and makes everything cleaner.

### What Does NOT Change

- No `agency init` subcommand — setup happens through the admin GUI.
- No wizard or interactive prompts at CLI level.
- No subcommands beyond the default (start server).
- Tailwind CDN stays for now (noted as future improvement).

---

## Feature 2: Agent Management

### 2.1 Agent Identity

**Storage:** YAML frontmatter in each agent's `CLAUDE.md`:

```yaml
---
display_name: "Eddy"
title: "Editorial Director"
emoji: "\U0001F4DD"
---
# Editorial Agent
...
```

**Fields:**
- `display_name` (string) — friendly name. Falls back to directory name.
- `title` (string) — one-line role, like a job title. Falls back to empty.
- `emoji` (string) — single emoji for lightweight avatar. Falls back to empty.

**Headshot:** Detected as `headshot.png`, `headshot.jpg`, or `headshot.webp` in the agent's directory. Not stored in frontmatter. Avatar priority: headshot file > emoji > first letter of display_name.

**CLAUDE.md Frontmatter Handling:**
- `parse_agent_identity(agent_dir: Path) -> dict` — reads CLAUDE.md, parses frontmatter, returns identity fields + body separately.
- **Saving identity fields:** Merges only the identity keys (`display_name`, `title`, `emoji`) into existing frontmatter, preserving any other frontmatter fields the agent may use. Does NOT replace all frontmatter.
- **Saving CLAUDE.md body:** Reconstructs file as existing frontmatter (unchanged) + new body. If no frontmatter existed, the body is written as-is (no frontmatter block added unless identity fields are also being set).

### 2.2 Subagent Detection

An agent is a subagent if:
- Its directory is under `{group_path}/_subagents/`, OR
- It has `subagent: true` in its CLAUDE.md frontmatter

**Subagent scanning:** The agent list page scans both `{group_path}/` (regular agents from config) and `{group_path}/_subagents/*/` (auto-detected subagents). Subagents found in `_subagents/` do not need to be in the config's `agents` list.

### 2.3 Agent List Page

**Route:** `GET /{group}/agents`

**Sidebar:** New "Agents" nav item placed between the group switcher and "Inbox" — it's the directory of agents, which provides context before diving into the inbox. Visually same weight as other nav items, not promoted above Inbox.

**Layout:**
- Grid of agent cards (responsive: 1 col mobile, 2 col tablet, 3 col desktop)
- Each card shows:
  - Avatar circle (headshot/emoji/letter fallback)
  - Display name (bold) + title (muted)
  - Last seen timestamp — derived from most recent log file. Shows relative time ("2h ago", "3 days ago"). Hover shows absolute datetime via `title` attribute. "No activity recorded" if no logs.
  - Open clues count — badge showing number of clues with `agent == this_agent` and `status == "open"`.
- Clicking any card navigates to `/{group}/agents/{agent}`.

**Subagent section:**
- Below the main grid, a `<details>` element: "Subagents ({count})"
- Collapsed by default
- Same card format but smaller/muted styling

**Performance strategy:**
- `list_clues(g)` is called once and the results are filtered per-agent in the template (not called per-agent).
- `get_agent_last_seen` scans log date directories in reverse chronological order and **stops at the first match**. This means for active agents, only the most recent date directory is scanned.

**Helper functions:**
- `get_agent_last_seen(g: dict, agent_name: str) -> datetime | None` — scans log date directories newest-first, returns mtime of first matching `{agent}-*` file found. Returns `None` if no match.
- `collect_agents_with_identity(g: dict) -> list[dict]` — returns agent info dicts with identity, last_seen, open_clue_count, is_subagent. Calls `list_clues` once internally.
- `relative_time(dt: datetime | None) -> str` — returns `"No activity recorded"` for `None`, `"Just now"` for < 1 minute, `"Xm ago"` / `"Xh ago"` / `"Xd ago"` for recent, and the absolute date string for > 30 days.

### 2.4 Agent Profile Page

**Route:** `GET /{group}/agents/{agent}`

**Agent resolution:** `resolve_agent_dir(g, agent_name)` checks `{group_path}/{agent}/` first, then `{group_path}/_subagents/{agent}/`. Returns the Path or raises 404. **Security:** validates that `agent_name` contains no path separators (`/`, `..`) before constructing paths. This prevents directory traversal via the URL parameter.

**Layout — top to bottom:**

#### Header Row
- Large avatar circle (headshot/emoji/letter)
- Display name (large, bold)
- Title (muted, below name)
- "Subagent" badge if applicable
- Subagent toggle — see section 2.5
- Last seen timestamp
- Upload headshot button (file input)

#### Identity Fields
- Display name, title, emoji as standard HTML form inputs (not inline-edit JS)
- Always visible, pre-filled with current values
- Standard HTML `<form>` with POST + 303 redirect pattern (matches codebase convention)
- Save button always visible; submits the form
- `POST /{group}/agents/{agent}/identity` saves fields into CLAUDE.md frontmatter (merge, not replace)

#### Collapsible: Agent Definition (CLAUDE.md body)
- Uses `<details>` / `<summary>` HTML elements — **no custom JavaScript required**
- **Collapsed by default** (`<details>` without `open` attribute)
- Summary text: "Agent Definition" with browser-native expand/collapse arrow
- Expands to:
  - `<textarea>` with CLAUDE.md body (frontmatter stripped)
  - Max-height ~400px via `style="max-height: 400px; overflow-y: auto"` on a wrapper div
  - Save / Discard buttons visible within the expanded section
  - Save: standard form POST to `/{group}/agents/{agent}/definition` with 303 redirect
  - Discard: a link/button that simply reloads the page (no JS state tracking needed)
- `POST /{group}/agents/{agent}/definition` saves the body back, preserving all existing frontmatter

#### Collapsible: Recent Logs
- Uses `<details open>` — **expanded by default**
- Summary text: "Recent Logs ({count})"
- Lists log files matching `{agent}-*` from `shared/logs/`, newest first
- Each entry: filename, date, file size
- Links to existing `/{group}/logs/view?path=` route
- Capped at 20 entries, "View all logs" link if more exist (links to `/{group}/logs`)
- Empty state: "No logs recorded for this agent."

#### Collapsible: Recent Clues
- Uses `<details open>` — **expanded by default**
- Summary text: "Recent Clues ({count})"
- Lists clues where `agent` field matches, newest first, capped at 10
- Each entry: status badge, title (slug humanized), date
- Links to existing `/{group}/clues/{slug}` route
- Empty state: "No clues from this agent."

#### Memory Link
- If `{agent_dir}/memory.md` exists: link to `/{group}/memory/view?path=...`
- If not: muted "No memory file" text

### 2.5 Subagent Toggle

A toggle on the agent profile page header area. Implemented as a small `<form>` with a single submit button ("Make Subagent" or "Make Regular Agent" depending on current state). Standard POST + 303 redirect.

**Toggle ON (make subagent):**
1. Check that `{group_path}/_subagents/{agent}/` does NOT already exist. If it does, redirect back with an error flash (name collision).
2. Create `{group_path}/_subagents/` if it doesn't exist
3. Move `{group_path}/{agent}/` to `{group_path}/_subagents/{agent}/` via `shutil.move`
4. Remove agent from `agents` list in config.yaml
5. Save config atomically, reload groups
6. Redirect to `/{group}/agents/{agent}` (route resolves new location)

**Toggle OFF (make regular agent):**
1. Check that `{group_path}/{agent}/` does NOT already exist. If it does, redirect back with an error flash (name collision).
2. Move `{group_path}/_subagents/{agent}/` to `{group_path}/{agent}/` via `shutil.move`
3. Add agent to `agents` list in config.yaml
4. Save config atomically, reload groups
5. Redirect to `/{group}/agents/{agent}`

**Note:** Toggling subagent status affects dispatch. Removing an agent from the config's `agents` list means dispatch scripts (like `dispatch.sh`) will no longer include it. This is expected behavior — subagents are called by other agents, not dispatched directly.

**Route:** `POST /{group}/agents/{agent}/toggle-subagent`

### 2.6 Headshot Upload

**Route:** `POST /{group}/agents/{agent}/upload-headshot`

- Accepts multipart file upload
- Validates: file extension must be `.png`, `.jpg`, `.jpeg`, or `.webp`. Size limit: < 2MB.
- **Saves with original extension** (no conversion, no Pillow dependency). If a previous headshot with a different extension exists, delete it first to avoid ambiguity.
- File is saved as `headshot.{ext}` in the agent's directory.
- Redirects back to profile page.
- **Security:** agent name validated same as profile route (no path separators).

**Serving headshots:**
- New route: `GET /{group}/agents/{agent}/headshot` — checks for `headshot.png`, `.jpg`, `.jpeg`, `.webp` in order, serves the first found with appropriate content-type via `FileResponse`.
- Returns 404 if no headshot exists (template handles fallback display).

**Headshot detection helper:**
```python
def find_headshot(agent_dir: Path) -> Path | None:
    for ext in ("png", "jpg", "jpeg", "webp"):
        p = agent_dir / f"headshot.{ext}"
        if p.exists():
            return p
    return None
```

### 2.7 Cross-Linking

**Agent badges become clickable links.** The `agent_badge` filter stays as-is (returns a `<span>`). In templates, wrap the badge call in an `<a>` tag pointing to the agent profile.

**Templates to modify** (exhaustive list):
- `home.html` — agent badges in open clues list (line 61), actionable curiosities (line 36), floated clues (line 79)
- `clues.html` — agent badge in clue list items (line 32)
- `clue_detail.html` — agent badge in detail header
- `curiosities.html` — origin_agent badge in list items
- `curiosity_detail.html` — origin_agent badge in detail header (line 13)

**Pattern in templates:**
```jinja
{# Before: #}
{{ c.get("agent", "") | agent_badge }}

{# After: #}
<a href="/{{ group }}/agents/{{ c.get('agent', '') }}">{{ c.get("agent", "") | agent_badge }}</a>
```

**Admin org edit page:**
- The agents textarea is free-form text, not a structured list. Adding "View profile" links here would require restructuring the form. **Deferred** — the agent list page serves this purpose. Admin edit stays focused on configuration.

### 2.8 Tmux Config Per Group

**Config addition:** Optional `tmux_config` key in each group's config.yaml entry:

```yaml
groups:
  newsletter:
    name: Newsletter Agents
    path: /path/to/agents
    agents: [...]
    tmux_config: /var/home/chris/dev/local-newsletter/scripts/tmux-agents.sh
```

**Admin org edit page:**
- New optional text input field: "Tmux Config Path"
- Below the agents textarea, before the submit button
- Saved to config.yaml alongside other group fields
- Help text: "Optional. Absolute path to a tmux session script for this group."

**Tmux config view/edit:**
- **Route:** `GET /{group}/tmux-config` — view/edit the tmux config file
- Reads the `tmux_config` path from config. If not set or file doesn't exist, returns 404.
- Renders content in a `<pre>` block (shell script) + toggle to textarea editor + save button
- **Route:** `POST /{group}/tmux-config/save` — save edits back to the file
- **Security:** The tmux_config path is set by the admin in config.yaml, not by URL params. The save route reads the path from config (not from the form) to prevent path injection. The admin is trusted to set valid paths.

**Sidebar:** When a group has `tmux_config` set, show a "Tmux Config" link in the sidebar under the "Config" section (after Prompts and Memory).

**Groups without tmux config:** No link in sidebar, route returns 404.

---

## New Routes Summary

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/{group}/agents` | Agent list page |
| GET | `/{group}/agents/{agent}` | Agent profile page |
| POST | `/{group}/agents/{agent}/identity` | Save identity fields to CLAUDE.md frontmatter |
| POST | `/{group}/agents/{agent}/definition` | Save CLAUDE.md body |
| POST | `/{group}/agents/{agent}/upload-headshot` | Upload headshot image |
| GET | `/{group}/agents/{agent}/headshot` | Serve headshot image file |
| POST | `/{group}/agents/{agent}/toggle-subagent` | Toggle subagent status (moves directory) |
| GET | `/{group}/tmux-config` | View/edit tmux config file |
| POST | `/{group}/tmux-config/save` | Save tmux config edits |

## New Templates

| Template | Purpose |
|----------|---------|
| `agents.html` | Agent list grid with cards |
| `agent_profile.html` | Agent profile with collapsible sections |
| `tmux_config.html` | Tmux config view/edit (shell script) |

## New Helper Functions

| Function | Purpose |
|----------|---------|
| `parse_agent_identity(agent_dir)` | Read CLAUDE.md, return identity fields dict + body string |
| `save_agent_identity(agent_dir, fields)` | Merge identity fields into CLAUDE.md frontmatter |
| `save_agent_definition(agent_dir, body)` | Write CLAUDE.md body preserving all frontmatter |
| `get_agent_last_seen(g, agent_name)` | Scan logs newest-first, return mtime of first match |
| `collect_agents_with_identity(g)` | Build full agent info list (identity, health, stats, subagent flag) |
| `resolve_agent_dir(g, agent_name)` | Find agent dir in root or _subagents, with path validation |
| `find_headshot(agent_dir)` | Find headshot file by checking extensions in order |
| `relative_time(dt)` | Format datetime as relative string, handle None |

## Modified Files

- `app.py` — new routes, helpers, CLI args in main(), first-run config, get_agency_config() empty-groups fix
- `pyproject.toml` — package structure, package-data for templates
- `templates/base.html` — add "Agents" nav item; hide org-scoped nav when admin_active; tmux config link when available
- `templates/admin_org_edit.html` — add tmux config path field
- `templates/home.html` — wrap agent badges in profile links
- `templates/clues.html` — wrap agent badges in profile links
- `templates/clue_detail.html` — wrap agent badge in profile link
- `templates/curiosities.html` — wrap agent badges in profile links
- `templates/curiosity_detail.html` — wrap agent badge in profile link
- Project root — restructure into `agency/` package directory
