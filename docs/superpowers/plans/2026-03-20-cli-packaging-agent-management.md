# CLI Packaging + Agent Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Agency pip-installable and add agent profile/management pages with health indicators, logs, identity, and cross-linking.

**Architecture:** Restructure into a Python package (`agency/`), add agent management routes and templates to the existing FastAPI app, use `<details>`/`<summary>` for collapsible UI, filesystem scanning for agent health data.

**Tech Stack:** Python 3.11+, FastAPI, Jinja2, Tailwind CSS (CDN), PyYAML, setuptools

**Spec:** `docs/superpowers/specs/2026-03-20-cli-packaging-agent-management-design.md`

---

## File Structure

### Files to Create
- `agency/__init__.py` — empty package marker
- `agency/app.py` — moved from root `app.py`
- `agency/templates/*.html` — moved from root `templates/`
- `agency/templates/agents.html` — agent list grid
- `agency/templates/agent_profile.html` — agent profile with collapsible sections
- `agency/templates/tmux_config.html` — tmux config view/edit

### Files to Modify
- `pyproject.toml` — package structure, entry point, package-data
- `agency/app.py` — new helpers, routes, CLI args, bug fixes
- `agency/templates/base.html` — sidebar: Agents nav, admin fix, tmux config link
- `agency/templates/admin_org_edit.html` — tmux config path field
- `agency/templates/home.html` — agent badge cross-links
- `agency/templates/clues.html` — agent badge cross-links
- `agency/templates/clue_detail.html` — agent badge cross-link
- `agency/templates/curiosities.html` — agent badge cross-links
- `agency/templates/curiosity_detail.html` — agent badge cross-link

### Files to Delete (after move)
- Root `app.py` — replaced by `agency/app.py`
- Root `templates/` — replaced by `agency/templates/`

---

## Task 1: Package Restructure

**Files:**
- Create: `agency/__init__.py`
- Move: `app.py` → `agency/app.py`
- Move: `templates/` → `agency/templates/`
- Modify: `pyproject.toml`

- [ ] **Step 1: Create the package directory**

```bash
mkdir -p agency
```

- [ ] **Step 2: Create empty `__init__.py`**

Create `agency/__init__.py` as an empty file.

- [ ] **Step 3: Move `app.py` into the package**

```bash
mv app.py agency/app.py
```

- [ ] **Step 4: Move templates into the package**

```bash
mv templates agency/templates
```

- [ ] **Step 5: Update `CONFIG_PATH` in `agency/app.py`**

Change:
```python
CONFIG_PATH = Path(__file__).parent / "config.yaml"
```
To:
```python
CONFIG_PATH = Path.cwd() / "config.yaml"
```

Template resolution stays as `Path(__file__).parent / "templates"` — this is correct since templates moved with `app.py`.

- [ ] **Step 6: Update `pyproject.toml`**

```toml
[project]
name = "agency"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "jinja2",
    "markdown",
    "pyyaml",
    "markupsafe",
]

[project.scripts]
agency = "agency.app:main"

[tool.setuptools.package-data]
agency = ["templates/*.html"]
```

- [ ] **Step 7: Update `agency.service` systemd unit**

Update the service file with the correct module path and user-level target:

```ini
[Unit]
Description=Agency Dashboard
After=network-online.target

[Service]
Type=simple
ExecStart=/var/home/chris/dev/agency/.venv/bin/python3 -m agency.app
Restart=always
WorkingDirectory=/var/home/chris/dev/agency
Environment=HOME=/var/home/chris

[Install]
WantedBy=default.target
```

Key changes: `ExecStart` now uses `-m agency.app` (package module path), and `WantedBy` changed from `multi-user.target` to `default.target` (correct for user-level systemd).

- [ ] **Step 8: Verify the app starts**

```bash
cd ~/dev/agency && .venv/bin/python -m agency.app
```

Confirm it serves at http://localhost:8500 and pages load correctly.

- [ ] **Step 9: Commit**

```bash
git add agency/ pyproject.toml agency.service
git rm app.py
git commit -m "refactor: restructure into agency/ Python package for pip installability"
```

---

## Task 2: CLI Entry Point + First-Run + Empty Groups Fix

**Files:**
- Modify: `agency/app.py` (lines 1079-1084, lines 55-62)

- [ ] **Step 1: Fix `load_config()` and `get_agency_config()` for first-run safety**

In `agency/app.py`, update `load_config()` to handle missing config gracefully:

```python
def load_config() -> dict:
    """Read config.yaml and return dict. Returns defaults if file doesn't exist."""
    if not CONFIG_PATH.exists():
        return {"agency": {"title": "Agency", "default_group": ""}, "groups": {}}
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f) or {}
```

Update `get_agency_config()` to use per-key defaults (not whole-dict fallback):

```python
def get_agency_config() -> dict:
    """Return agency-level config with defaults."""
    agency = CONFIG.get("agency", {})
    return {
        "title": agency.get("title", "Agency"),
        "default_group": agency.get("default_group", "") or (list(GROUPS.keys())[0] if GROUPS else ""),
    }
```

Note: Uses module-level `CONFIG` and `GROUPS` globals (refreshed by `reload_groups()` after every config change) instead of re-reading `config.yaml` from disk on every request.

This handles: empty `agency` key, missing `title`, empty `default_group`, and empty `groups` dict.

- [ ] **Step 2: Add CLI argument parsing and first-run config creation to `main()`**

Replace the existing `main()`:

```python
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agency — Agent Management Dashboard")
    parser.add_argument("--port", type=int, default=8500, help="Port to serve on (default: 8500)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    args = parser.parse_args()

    # First-run: create default config
    if not CONFIG_PATH.exists():
        save_config({"agency": {"title": "Agency", "default_group": ""}, "groups": {}})
        print(f"First run — created config.yaml in {CONFIG_PATH.parent}")
        print(f"Visit http://localhost:{args.port}/admin/ to set up your first agent group.")

    reload_groups()
    uvicorn.run(app, host=args.host, port=args.port)
```

**Important:** First-run config creation happens ONLY in `main()`, never at module level. The module-level `CONFIG = load_config()` is safe because `load_config()` now returns defaults when the file is missing.

- [ ] **Step 3: Verify first-run behavior**

```bash
cd /tmp && mkdir test-agency && cd test-agency
python -m agency.app --port 8501
```

Confirm: config.yaml is created, server starts, `/` redirects to `/admin/`.

- [ ] **Step 4: Commit**

```bash
git add agency/app.py
git commit -m "feat: add CLI args, first-run config bootstrap, fix empty groups crash"
```

---

## Task 3: Bug Fix — Admin Sidebar Links

**Files:**
- Modify: `agency/templates/base.html`

- [ ] **Step 1: Wrap org-scoped nav items in admin_active check**

In `base.html`, wrap the org-scoped navigation links (Agents, Inbox, Clues, Curiosities, Decisions, Documents, Logs, Prompts, Memory) in `{% if not admin_active %}`:

```html
{% if not admin_active %}
<div class="space-y-0.5" onclick="...">
  <a href="/{{ group }}/" class="...{% if active == 'home' %}active{% endif %}">Inbox</a>
  <a href="/{{ group }}/clues" class="...">Clues</a>
  <!-- ... all org-scoped links ... -->
</div>
{% endif %}
```

Keep the group switcher dropdown visible (it navigates to a group's inbox on change). Keep the "Settings" link under "Admin" visible always.

- [ ] **Step 2: Verify admin page**

Restart server, navigate to `/admin/`. Confirm:
- Sidebar shows only the group switcher and Settings link
- No broken `/clues`-style links
- Selecting a group in the switcher navigates to that group's inbox
- Group pages still show full navigation

- [ ] **Step 3: Commit**

```bash
git add agency/templates/base.html
git commit -m "fix: hide org-scoped nav links on admin pages where group context is missing"
```

---

## Task 4: Agent Helper Functions

**Files:**
- Modify: `agency/app.py` — add new helper functions after existing helpers section (~line 284)

- [ ] **Step 1: Add `resolve_agent_dir`**

```python
def resolve_agent_dir(g: dict, agent_name: str) -> Path:
    """Find an agent's directory, checking root and _subagents/. Raises 404 if not found."""
    if "/" in agent_name or ".." in agent_name:
        raise HTTPException(400, "Invalid agent name")
    # Check root
    agent_dir = g["path"] / agent_name
    if agent_dir.is_dir():
        return agent_dir
    # Check _subagents
    sub_dir = g["path"] / "_subagents" / agent_name
    if sub_dir.is_dir():
        return sub_dir
    raise HTTPException(404, f"Agent not found: {agent_name}")
```

- [ ] **Step 2: Add `parse_agent_identity`**

```python
def parse_agent_identity(agent_dir: Path) -> dict:
    """Read CLAUDE.md and return identity fields + body."""
    claude_md = agent_dir / "CLAUDE.md"
    if not claude_md.exists():
        return {
            "display_name": agent_dir.name,
            "title": "",
            "emoji": "",
            "body": "",
            "frontmatter": {},
        }
    raw = claude_md.read_text()
    meta, body = parse_frontmatter(raw)
    return {
        "display_name": meta.get("display_name", agent_dir.name),
        "title": meta.get("title", ""),
        "emoji": meta.get("emoji", ""),
        "body": body,
        "frontmatter": meta,
    }
```

- [ ] **Step 3: Add `save_agent_identity`**

```python
def save_agent_identity(agent_dir: Path, fields: dict) -> None:
    """Merge identity fields into CLAUDE.md frontmatter, preserving other fields."""
    claude_md = agent_dir / "CLAUDE.md"
    if claude_md.exists():
        raw = claude_md.read_text()
        meta, body = parse_frontmatter(raw)
    else:
        meta, body = {}, ""
    # Merge only identity keys
    for key in ("display_name", "title", "emoji"):
        if key in fields and fields[key]:
            meta[key] = fields[key]
        elif key in fields and not fields[key] and key in meta:
            del meta[key]  # Remove empty fields
    # Reconstruct file
    if meta:
        front = yaml.dump(meta, default_flow_style=False, sort_keys=False).strip()
        claude_md.write_text(f"---\n{front}\n---\n\n{body}")
    else:
        claude_md.write_text(body)
```

- [ ] **Step 4: Add `save_agent_definition`**

```python
def save_agent_definition(agent_dir: Path, new_body: str) -> None:
    """Write CLAUDE.md body preserving all existing frontmatter."""
    claude_md = agent_dir / "CLAUDE.md"
    if claude_md.exists():
        raw = claude_md.read_text()
        meta, _ = parse_frontmatter(raw)
    else:
        meta = {}
    if meta:
        front = yaml.dump(meta, default_flow_style=False, sort_keys=False).strip()
        claude_md.write_text(f"---\n{front}\n---\n\n{new_body}")
    else:
        claude_md.write_text(new_body)
```

- [ ] **Step 5: Add `find_headshot`**

```python
def find_headshot(agent_dir: Path) -> Path | None:
    """Find headshot file by checking extensions in order."""
    for ext in ("png", "jpg", "jpeg", "webp"):
        p = agent_dir / f"headshot.{ext}"
        if p.exists():
            return p
    return None
```

- [ ] **Step 6: Add `get_agent_last_seen`**

```python
def get_agent_last_seen(g: dict, agent_name: str) -> datetime | None:
    """Scan log date directories newest-first, return mtime of first matching file."""
    logs_dir = g["shared"] / "logs"
    if not logs_dir.exists():
        return None
    for date_dir in sorted(logs_dir.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        for f in sorted(date_dir.iterdir(), reverse=True):
            if f.name.startswith(f"{agent_name}-") and f.suffix in (".out", ".err"):
                return datetime.fromtimestamp(f.stat().st_mtime)
    return None
```

- [ ] **Step 7: Add `relative_time`**

```python
def relative_time(dt: datetime | None) -> str:
    """Format datetime as relative string."""
    if dt is None:
        return "No activity recorded"
    now = datetime.now()
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "Just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days <= 30:
        return f"{days}d ago"
    return dt.strftime("%Y-%m-%d")
```

Register `relative_time` as a template filter alongside the existing filters:

```python
templates.env.filters["relative_time"] = relative_time
```

- [ ] **Step 8: Add `collect_agents_with_identity`**

```python
def collect_agents_with_identity(g: dict) -> tuple[list[dict], list[dict]]:
    """Build full agent info lists. Returns (agents, subagents)."""
    clues = list_clues(g)
    agents = []
    subagents = []

    # Regular agents from config
    for agent_name in g["agents"]:
        agent_dir = g["path"] / agent_name
        if not agent_dir.is_dir():
            continue
        identity = parse_agent_identity(agent_dir)
        open_count = sum(1 for c in clues if c.get("agent") == agent_name and c.get("status") == "open")
        info = {
            "name": agent_name,
            "dir": agent_dir,
            **identity,
            "last_seen": get_agent_last_seen(g, agent_name),
            "open_clues": open_count,
            "is_subagent": identity["frontmatter"].get("subagent", False),
            "has_headshot": find_headshot(agent_dir) is not None,
        }
        if info["is_subagent"]:
            subagents.append(info)
        else:
            agents.append(info)

    # Auto-detect subagents from _subagents/ directory
    subagents_dir = g["path"] / "_subagents"
    if subagents_dir.is_dir():
        for d in sorted(subagents_dir.iterdir()):
            if not d.is_dir() or d.name.startswith("."):
                continue
            # Skip if already in list (e.g., also in config)
            if any(s["name"] == d.name for s in subagents):
                continue
            identity = parse_agent_identity(d)
            open_count = sum(1 for c in clues if c.get("agent") == d.name and c.get("status") == "open")
            subagents.append({
                "name": d.name,
                "dir": d,
                **identity,
                "last_seen": get_agent_last_seen(g, d.name),
                "open_clues": open_count,
                "is_subagent": True,
                "has_headshot": find_headshot(d) is not None,
            })

    return agents, subagents
```

- [ ] **Step 9: Add `get_agent_logs`**

Helper to get recent log files for a specific agent (used by the profile page):

```python
def get_agent_logs(g: dict, agent_name: str, limit: int = 20) -> list[dict]:
    """Get recent log files for an agent, newest first."""
    logs_dir = g["shared"] / "logs"
    if not logs_dir.exists():
        return []
    results = []
    for date_dir in sorted(logs_dir.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        for f in sorted(date_dir.iterdir(), reverse=True):
            if f.name.startswith(f"{agent_name}-") and f.suffix in (".out", ".err"):
                results.append({
                    "name": f.name,
                    "path": str(f),
                    "date": date_dir.name,
                    "size": f.stat().st_size,
                    "suffix": f.suffix,
                })
                if len(results) >= limit:
                    return results
    return results
```

- [ ] **Step 10: Commit**

```bash
git add agency/app.py
git commit -m "feat: add agent identity, resolution, health, and log helper functions"
```

---

## Task 5: Agent List Page

**Files:**
- Modify: `agency/app.py` — add agent list route
- Create: `agency/templates/agents.html`
- Modify: `agency/templates/base.html` — add Agents nav item

- [ ] **Step 1: Add the agent list route**

Add to `agency/app.py` in the Group Routes section, before the existing `/{group}/` home route:

```python
@app.get("/{group}/agents", response_class=HTMLResponse)
async def agents_list(request: Request, group: str):
    """List all agents with identity and health info."""
    g = get_group(group)
    agents, subagents = collect_agents_with_identity(g)
    return templates.TemplateResponse("agents.html", {
        "request": request,
        **group_context(g),
        "agents": agents,
        "subagents": subagents,
    })
```

**Important:** This route MUST be registered before the `/{group}/` catch-all home route, otherwise `/{group}/agents` would match `/{group}/` with `group="agents"` — wait, actually FastAPI matches by specificity so `/{group}/agents` (literal `agents` segment) will match first. But to be safe, register it before the generic `/{group}/` route.

Actually, since FastAPI routes match in registration order and `/{group}/agents` has a literal `agents` path segment, this is not a problem. The `/{group}/` route has a trailing slash, so `/agents` without slash won't match it. Keep the route where it makes sense in the code.

- [ ] **Step 2: Create `agency/templates/agents.html`**

```html
{% extends "base.html" %}
{% set active = "agents" %}

{% block title %}Agents - {{ group_name }}{% endblock %}

{% block content %}
<div class="flex items-baseline justify-between mb-6">
  <h1 class="text-2xl font-bold text-gray-900">Agents</h1>
  <span class="text-sm text-gray-500">{{ agents|length }} agent{{ 's' if agents|length != 1 else '' }}</span>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
  {% for a in agents %}
  <a href="/{{ group }}/agents/{{ a.name }}" class="block bg-white rounded-xl border border-gray-200 p-5 hover:border-indigo-300 hover:shadow-sm transition-all">
    <div class="flex items-center gap-3 mb-3">
      <div class="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center shrink-0 overflow-hidden">
        {% if a.has_headshot %}
        <img src="/{{ group }}/agents/{{ a.name }}/headshot" class="w-full h-full object-cover" alt="">
        {% elif a.emoji %}
        <span class="text-lg">{{ a.emoji }}</span>
        {% else %}
        <span class="text-sm font-bold text-gray-400">{{ a.display_name[0]|upper }}</span>
        {% endif %}
      </div>
      <div class="min-w-0">
        <div class="font-semibold text-gray-900 truncate">{{ a.display_name }}</div>
        {% if a.title %}
        <div class="text-xs text-gray-500 truncate">{{ a.title }}</div>
        {% endif %}
      </div>
    </div>
    <div class="flex items-center gap-3 text-xs text-gray-400">
      <span title="{{ a.last_seen.strftime('%Y-%m-%d %H:%M') if a.last_seen else '' }}">{{ a.last_seen | relative_time }}</span>
      {% if a.open_clues > 0 %}
      <span class="inline-flex items-center px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 font-medium">{{ a.open_clues }} open</span>
      {% endif %}
    </div>
  </a>
  {% endfor %}
</div>

{% if not agents %}
<div class="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-500 mb-8">No agents configured.</div>
{% endif %}

{% if subagents %}
<details class="mb-8">
  <summary class="cursor-pointer text-sm font-semibold text-gray-500 hover:text-gray-700 mb-3">
    Subagents ({{ subagents|length }})
  </summary>
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mt-3">
    {% for a in subagents %}
    <a href="/{{ group }}/agents/{{ a.name }}" class="block bg-gray-50 rounded-lg border border-gray-200 p-4 hover:border-indigo-300 transition-colors">
      <div class="flex items-center gap-2.5 mb-2">
        <div class="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center shrink-0 overflow-hidden">
          {% if a.has_headshot %}
          <img src="/{{ group }}/agents/{{ a.name }}/headshot" class="w-full h-full object-cover" alt="">
          {% elif a.emoji %}
          <span class="text-sm">{{ a.emoji }}</span>
          {% else %}
          <span class="text-xs font-bold text-gray-400">{{ a.display_name[0]|upper }}</span>
          {% endif %}
        </div>
        <div class="min-w-0">
          <div class="text-sm font-medium text-gray-700 truncate">{{ a.display_name }}</div>
          {% if a.title %}
          <div class="text-xs text-gray-400 truncate">{{ a.title }}</div>
          {% endif %}
        </div>
      </div>
      <div class="text-xs text-gray-400">
        <span class="inline-block px-1.5 py-0.5 rounded-full bg-gray-200 text-gray-500 text-xs font-medium mr-1">subagent</span>
        {{ a.last_seen | relative_time }}
      </div>
    </a>
    {% endfor %}
  </div>
</details>
{% endif %}
{% endblock %}
```

- [ ] **Step 3: Add "Agents" nav item to sidebar in `base.html`**

In `agency/templates/base.html`, inside the `{% if not admin_active %}` block (added in Task 3), add the Agents link as the first item before Inbox:

```html
<a href="/{{ group }}/agents" class="block px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 {% if active == 'agents' %}active{% endif %}">
  Agents
</a>
```

- [ ] **Step 4: Verify the agents list page**

Restart server. Navigate to `/{group}/agents`. Confirm:
- Agent cards display with names
- Last seen shows timestamps or "No activity recorded"
- Subagents section appears collapsed (if _subagents/ exists)
- Cards link to `/{group}/agents/{agent}` (will 404 for now — expected)
- Sidebar highlights "Agents" as active

- [ ] **Step 5: Commit**

```bash
git add agency/app.py agency/templates/agents.html agency/templates/base.html
git commit -m "feat: add agent list page with identity cards, health indicators, subagent section"
```

---

## Task 6: Agent Profile Page

**Files:**
- Modify: `agency/app.py` — add profile route
- Create: `agency/templates/agent_profile.html`

- [ ] **Step 1: Add the agent profile route**

```python
@app.get("/{group}/agents/{agent}", response_class=HTMLResponse)
async def agent_profile(request: Request, group: str, agent: str):
    """View an agent's profile with identity, logs, clues, and memory."""
    g = get_group(group)
    agent_dir = resolve_agent_dir(g, agent)
    identity = parse_agent_identity(agent_dir)
    is_subagent = (g["path"] / "_subagents" / agent).is_dir() or identity["frontmatter"].get("subagent", False)
    last_seen = get_agent_last_seen(g, agent)
    logs = get_agent_logs(g, agent)
    clues = [c for c in list_clues(g) if c.get("agent") == agent][:10]
    has_headshot = find_headshot(agent_dir) is not None
    has_memory = (agent_dir / "memory.md").exists()
    memory_path = str(agent_dir / "memory.md") if has_memory else ""

    return templates.TemplateResponse("agent_profile.html", {
        "request": request,
        **group_context(g),
        "agent": agent,
        "identity": identity,
        "is_subagent": is_subagent,
        "last_seen": last_seen,
        "logs": logs,
        "clues": clues,
        "has_headshot": has_headshot,
        "has_memory": has_memory,
        "memory_path": memory_path,
    })
```

- [ ] **Step 2: Create `agency/templates/agent_profile.html`**

```html
{% extends "base.html" %}
{% set active = "agents" %}

{% block title %}{{ identity.display_name }} - Agents{% endblock %}

{% block content %}
<div class="mb-4">
  <a href="/{{ group }}/agents" class="text-sm text-indigo-600 hover:text-indigo-800">&larr; Back to agents</a>
</div>

<!-- Header -->
<div class="bg-white rounded-xl border border-gray-200 p-6 mb-6">
  <div class="flex flex-wrap items-start gap-4">
    <!-- Avatar -->
    <div class="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center shrink-0 overflow-hidden">
      {% if has_headshot %}
      <img src="/{{ group }}/agents/{{ agent }}/headshot" class="w-full h-full object-cover" alt="">
      {% elif identity.emoji %}
      <span class="text-2xl">{{ identity.emoji }}</span>
      {% else %}
      <span class="text-xl font-bold text-gray-400">{{ identity.display_name[0]|upper }}</span>
      {% endif %}
    </div>

    <div class="flex-1 min-w-0">
      <div class="flex flex-wrap items-center gap-2 mb-1">
        <h1 class="text-xl font-bold text-gray-900">{{ identity.display_name }}</h1>
        {% if is_subagent %}
        <span class="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-gray-200 text-gray-600">subagent</span>
        {% endif %}
      </div>
      {% if identity.title %}
      <div class="text-sm text-gray-500 mb-2">{{ identity.title }}</div>
      {% endif %}
      <div class="text-xs text-gray-400" title="{{ last_seen.strftime('%Y-%m-%d %H:%M:%S') if last_seen else '' }}">
        Last seen: {{ last_seen | relative_time }}
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-2 shrink-0">
      <!-- Subagent toggle -->
      <form method="POST" action="/{{ group }}/agents/{{ agent }}/toggle-subagent"
            onsubmit="return confirm('{{ 'Make this a regular agent? It will be added to the dispatch list.' if is_subagent else 'Make this a subagent? It will be removed from the dispatch list.' }}')">
        <button type="submit" class="px-3 py-1.5 text-xs font-medium rounded-lg border {{ 'border-gray-300 text-gray-600 hover:bg-gray-50' if is_subagent else 'border-amber-300 text-amber-700 hover:bg-amber-50' }}">
          {{ 'Make Regular Agent' if is_subagent else 'Make Subagent' }}
        </button>
      </form>

      <!-- Upload headshot -->
      <form method="POST" action="/{{ group }}/agents/{{ agent }}/upload-headshot" enctype="multipart/form-data" class="inline">
        <label class="px-3 py-1.5 text-xs font-medium text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer inline-block">
          Upload Photo
          <input type="file" name="headshot" accept="image/png,image/jpeg,image/webp" class="hidden"
                 onchange="this.form.submit()">
        </label>
      </form>
    </div>
  </div>
</div>

<!-- Identity Fields -->
<div class="bg-white rounded-xl border border-gray-200 p-6 mb-6">
  <h2 class="text-sm font-semibold text-gray-700 mb-4">Identity</h2>
  <form method="POST" action="/{{ group }}/agents/{{ agent }}/identity">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
      <div>
        <label for="display_name" class="block text-xs font-medium text-gray-500 mb-1">Display Name</label>
        <input type="text" name="display_name" id="display_name" value="{{ identity.display_name }}"
               class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500">
      </div>
      <div>
        <label for="title" class="block text-xs font-medium text-gray-500 mb-1">Title</label>
        <input type="text" name="title" id="title" value="{{ identity.title }}" placeholder="e.g. Editorial Director"
               class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500">
      </div>
      <div>
        <label for="emoji" class="block text-xs font-medium text-gray-500 mb-1">Emoji</label>
        <input type="text" name="emoji" id="emoji" value="{{ identity.emoji }}" placeholder="e.g. &#x1F4DD;"
               class="w-full max-w-[80px] px-3 py-2 border border-gray-300 rounded-lg text-sm text-center focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500">
      </div>
    </div>
    <button type="submit" class="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors">
      Save Identity
    </button>
  </form>
</div>

<!-- Agent Definition (collapsible, collapsed by default) -->
<details class="bg-white rounded-xl border border-gray-200 mb-6">
  <summary class="px-6 py-4 cursor-pointer text-sm font-semibold text-gray-700 hover:text-gray-900">
    Agent Definition (CLAUDE.md)
  </summary>
  <div class="px-6 pb-6">
    <form method="POST" action="/{{ group }}/agents/{{ agent }}/definition">
      <div style="max-height: 400px; overflow-y: auto;" class="mb-3">
        <textarea name="body" rows="20" class="w-full font-mono text-sm border border-gray-300 rounded-lg p-3 bg-gray-50">{{ identity.body }}</textarea>
      </div>
      <div class="flex gap-2">
        <button type="submit" class="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700">Save Definition</button>
        <a href="/{{ group }}/agents/{{ agent }}" class="px-4 py-2 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200">Discard</a>
      </div>
    </form>
  </div>
</details>

<!-- Recent Logs (collapsible, expanded by default) -->
<details open class="bg-white rounded-xl border border-gray-200 mb-6">
  <summary class="px-6 py-4 cursor-pointer text-sm font-semibold text-gray-700 hover:text-gray-900">
    Recent Logs ({{ logs|length }}{% if logs|length >= 20 %}+{% endif %})
  </summary>
  <div class="px-6 pb-6">
    {% if logs %}
    <div class="space-y-1.5">
      {% for log in logs %}
      <a href="/{{ group }}/logs/view?path={{ log.path }}" class="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-gray-50 text-sm group">
        <div class="flex items-center gap-2 min-w-0">
          <span class="text-xs font-mono text-gray-400 shrink-0">{{ log.date }}</span>
          <span class="text-gray-700 truncate group-hover:text-indigo-600">{{ log.name }}</span>
        </div>
        <span class="text-xs text-gray-400 shrink-0 ml-2">{{ (log.size / 1024)|round(1) }}KB</span>
      </a>
      {% endfor %}
    </div>
    {% if logs|length >= 20 %}
    <div class="mt-3">
      <a href="/{{ group }}/logs" class="text-sm text-indigo-600 hover:text-indigo-800">View all logs &rarr;</a>
    </div>
    {% endif %}
    {% else %}
    <div class="text-sm text-gray-400 py-2">No logs recorded for this agent.</div>
    {% endif %}
  </div>
</details>

<!-- Recent Clues (collapsible, expanded by default) -->
<details open class="bg-white rounded-xl border border-gray-200 mb-6">
  <summary class="px-6 py-4 cursor-pointer text-sm font-semibold text-gray-700 hover:text-gray-900">
    Recent Clues ({{ clues|length }})
  </summary>
  <div class="px-6 pb-6">
    {% if clues %}
    <div class="space-y-2">
      {% for c in clues %}
      <a href="/{{ group }}/clues/{{ c._slug }}" class="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-50 text-sm">
        {{ c.get("status", "") | status_badge }}
        <span class="text-gray-700">{{ c._slug | replace("-", " ") }}</span>
        <span class="text-xs text-gray-400 ml-auto shrink-0">{{ c.get("date", "")|string }}</span>
      </a>
      {% endfor %}
    </div>
    {% else %}
    <div class="text-sm text-gray-400 py-2">No clues from this agent.</div>
    {% endif %}
  </div>
</details>

<!-- Memory -->
<div class="bg-white rounded-xl border border-gray-200 p-6">
  <h2 class="text-sm font-semibold text-gray-700 mb-2">Memory</h2>
  {% if has_memory %}
  <a href="/{{ group }}/memory/view?path={{ memory_path }}" class="text-sm text-indigo-600 hover:text-indigo-800">View memory.md &rarr;</a>
  {% else %}
  <div class="text-sm text-gray-400">No memory file</div>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 3: Verify agent profile page**

Restart server. Navigate to `/{group}/agents/{agent}` for an agent that exists. Confirm:
- Header shows agent name, title area, last seen
- Identity fields are pre-filled (with defaults for agents without frontmatter)
- CLAUDE.md section is collapsed, expands on click
- Logs section shows any matching logs (or empty state)
- Clues section shows any matching clues (or empty state)
- Memory link works (or shows "No memory file")
- Subagent toggle and upload photo buttons render

- [ ] **Step 4: Commit**

```bash
git add agency/app.py agency/templates/agent_profile.html
git commit -m "feat: add agent profile page with identity, logs, clues, and memory sections"
```

---

## Task 7: Agent Identity + Definition Save Routes

**Files:**
- Modify: `agency/app.py` — add POST routes

- [ ] **Step 1: Add identity save route**

```python
@app.post("/{group}/agents/{agent}/identity", response_class=HTMLResponse)
async def agent_save_identity(request: Request, group: str, agent: str):
    """Save identity fields to CLAUDE.md frontmatter."""
    g = get_group(group)
    agent_dir = resolve_agent_dir(g, agent)
    form = await request.form()
    fields = {
        "display_name": form.get("display_name", "").strip(),
        "title": form.get("title", "").strip(),
        "emoji": form.get("emoji", "").strip(),
    }
    save_agent_identity(agent_dir, fields)
    return RedirectResponse(f"/{group}/agents/{agent}", status_code=303)
```

- [ ] **Step 2: Add definition save route**

```python
@app.post("/{group}/agents/{agent}/definition", response_class=HTMLResponse)
async def agent_save_definition(request: Request, group: str, agent: str):
    """Save CLAUDE.md body preserving frontmatter."""
    g = get_group(group)
    agent_dir = resolve_agent_dir(g, agent)
    form = await request.form()
    body = form.get("body", "")
    save_agent_definition(agent_dir, body)
    return RedirectResponse(f"/{group}/agents/{agent}", status_code=303)
```

- [ ] **Step 3: Verify identity save**

Navigate to an agent's profile. Change the display name. Click Save Identity. Confirm:
- Page redirects back to profile
- New display name is shown
- Check the CLAUDE.md file on disk — frontmatter should have `display_name` field
- Other frontmatter fields (if any existed) are preserved

- [ ] **Step 4: Verify definition save**

Expand the Agent Definition section. Make a small edit to the text. Click Save Definition. Confirm:
- Page redirects back to profile
- Expanding the section again shows the updated text
- Frontmatter in CLAUDE.md is unchanged

- [ ] **Step 5: Commit**

```bash
git add agency/app.py
git commit -m "feat: add agent identity and definition save routes"
```

---

## Task 8: Headshot Upload + Serve

**Files:**
- Modify: `agency/app.py` — add upload and serve routes

- [ ] **Step 1: Add headshot upload route**

```python
from fastapi import UploadFile, File
from fastapi.responses import FileResponse

@app.post("/{group}/agents/{agent}/upload-headshot", response_class=HTMLResponse)
async def agent_upload_headshot(request: Request, group: str, agent: str):
    """Upload a headshot image for an agent."""
    g = get_group(group)
    agent_dir = resolve_agent_dir(g, agent)
    form = await request.form()
    upload = form.get("headshot")
    if not upload or not hasattr(upload, 'filename') or not upload.filename:
        return RedirectResponse(f"/{group}/agents/{agent}", status_code=303)

    # Validate extension
    ext = Path(upload.filename).suffix.lower().lstrip(".")
    if ext not in ("png", "jpg", "jpeg", "webp"):
        raise HTTPException(400, "Invalid image format. Use PNG, JPG, or WebP.")

    # Read and validate size
    content = await upload.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(400, "Image too large. Maximum 2MB.")

    # Remove any existing headshots
    for old_ext in ("png", "jpg", "jpeg", "webp"):
        old = agent_dir / f"headshot.{old_ext}"
        if old.exists():
            old.unlink()

    # Save new headshot
    (agent_dir / f"headshot.{ext}").write_bytes(content)
    return RedirectResponse(f"/{group}/agents/{agent}", status_code=303)
```

- [ ] **Step 2: Add headshot serve route**

```python
@app.get("/{group}/agents/{agent}/headshot")
async def agent_headshot(group: str, agent: str):
    """Serve an agent's headshot image."""
    g = get_group(group)
    agent_dir = resolve_agent_dir(g, agent)
    headshot = find_headshot(agent_dir)
    if not headshot:
        raise HTTPException(404, "No headshot")
    return FileResponse(headshot)
```

Add `FileResponse` to the imports at the top if not already there:
```python
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
```

- [ ] **Step 3: Verify headshot upload**

Navigate to an agent profile. Click "Upload Photo" and select a small PNG. Confirm:
- Page redirects back to profile
- Avatar now shows the uploaded image
- File exists on disk as `headshot.png` in the agent's directory
- Agent list page also shows the headshot in the card

- [ ] **Step 4: Commit**

```bash
git add agency/app.py
git commit -m "feat: add headshot upload and serve routes for agent profiles"
```

---

## Task 9: Subagent Toggle

**Files:**
- Modify: `agency/app.py` — add toggle route

- [ ] **Step 1: Add the toggle route**

```python
@app.post("/{group}/agents/{agent}/toggle-subagent", response_class=HTMLResponse)
async def agent_toggle_subagent(request: Request, group: str, agent: str):
    """Toggle an agent between regular and subagent status."""
    g = get_group(group)
    if "/" in agent or ".." in agent:
        raise HTTPException(400, "Invalid agent name")

    root_dir = g["path"] / agent
    sub_dir = g["path"] / "_subagents" / agent
    is_currently_subagent = sub_dir.is_dir()

    config = load_config()
    group_config = config["groups"][g["key"]]

    if is_currently_subagent:
        # Make regular agent
        if root_dir.exists():
            raise HTTPException(409, f"Cannot move: {root_dir} already exists")
        shutil.move(str(sub_dir), str(root_dir))
        # Add to agents list
        if agent not in group_config.get("agents", []):
            group_config.setdefault("agents", []).append(agent)
    else:
        # Make subagent
        if not root_dir.is_dir():
            raise HTTPException(404, f"Agent directory not found: {agent}")
        if sub_dir.exists():
            raise HTTPException(409, f"Cannot move: {sub_dir} already exists")
        (g["path"] / "_subagents").mkdir(exist_ok=True)
        shutil.move(str(root_dir), str(sub_dir))
        # Remove from agents list
        if agent in group_config.get("agents", []):
            group_config["agents"].remove(agent)

    save_config(config)
    reload_groups()
    return RedirectResponse(f"/{group}/agents/{agent}", status_code=303)
```

- [ ] **Step 2: Verify subagent toggle**

Navigate to a regular agent's profile. Click "Make Subagent." Confirm:
- Agent directory moved to `_subagents/`
- Agent removed from config.yaml `agents` list
- Profile page still loads (resolves from new location)
- Badge shows "subagent"
- Button now says "Make Regular Agent"

Toggle back. Confirm reverse operation works.

**Warning:** Test this on a non-critical agent first. This moves directories on disk.

- [ ] **Step 3: Commit**

```bash
git add agency/app.py
git commit -m "feat: add subagent toggle that moves agent directories and updates config"
```

---

## Task 10: Cross-Linking Agent Badges

**Files:**
- Modify: `agency/templates/home.html`
- Modify: `agency/templates/clues.html`
- Modify: `agency/templates/clue_detail.html`
- Modify: `agency/templates/curiosities.html`
- Modify: `agency/templates/curiosity_detail.html`

- [ ] **Step 1: Update `home.html`**

Wrap agent badges in profile links. Three locations:

In the actionable curiosities section (around line 36):
```html
<!-- Before -->
{{ c.get("origin_agent", "") | agent_badge }}
<!-- After -->
<a href="/{{ group }}/agents/{{ c.get('origin_agent', '') }}">{{ c.get("origin_agent", "") | agent_badge }}</a>
```

In the open clues section (around line 60):
```html
<!-- Before -->
{{ c.get("agent", "") | agent_badge }}
<!-- After -->
<a href="/{{ group }}/agents/{{ c.get('agent', '') }}">{{ c.get("agent", "") | agent_badge }}</a>
```

In the floated clues section (around line 79):
```html
<!-- Before -->
{{ c.get("agent", "") | agent_badge }}
<!-- After -->
<a href="/{{ group }}/agents/{{ c.get('agent', '') }}">{{ c.get("agent", "") | agent_badge }}</a>
```

- [ ] **Step 2: Update `clues.html`**

Around line 32:
```html
<!-- Before -->
{{ c.get("agent", "") | agent_badge }}
<!-- After -->
<a href="/{{ group }}/agents/{{ c.get('agent', '') }}">{{ c.get("agent", "") | agent_badge }}</a>
```

- [ ] **Step 3: Update `clue_detail.html`**

Find the agent badge in the detail header and wrap it:
```html
<a href="/{{ group }}/agents/{{ meta.get('agent', '') }}">{{ meta.get("agent", "") | agent_badge }}</a>
```

- [ ] **Step 4: Update `curiosities.html`**

Find agent badges in the curiosity list items and wrap them:
```html
<a href="/{{ group }}/agents/{{ c.get('origin_agent', '') }}">{{ c.get("origin_agent", "") | agent_badge }}</a>
```

- [ ] **Step 5: Update `curiosity_detail.html`**

Around line 13:
```html
<!-- Before -->
{{ meta.get("origin_agent", "") | agent_badge }}
<!-- After -->
<a href="/{{ group }}/agents/{{ meta.get('origin_agent', '') }}">{{ meta.get("origin_agent", "") | agent_badge }}</a>
```

- [ ] **Step 6: Verify cross-linking**

Navigate to the inbox, clue list, clue detail, curiosity list, and curiosity detail pages. Confirm:
- Agent badges are clickable
- Clicking navigates to the agent profile page
- Badge styling is preserved (the `<a>` wrapping doesn't break visual appearance)

- [ ] **Step 7: Commit**

```bash
git add agency/templates/home.html agency/templates/clues.html agency/templates/clue_detail.html agency/templates/curiosities.html agency/templates/curiosity_detail.html
git commit -m "feat: make agent badges clickable links to agent profile pages"
```

---

## Task 11: Tmux Config

**Files:**
- Modify: `agency/app.py` — add tmux config routes
- Modify: `agency/templates/admin_org_edit.html` — add tmux config path field
- Create: `agency/templates/tmux_config.html` — view/edit template
- Modify: `agency/templates/base.html` — conditional tmux config sidebar link

- [ ] **Step 1: Add tmux config path field to admin org edit**

In `agency/templates/admin_org_edit.html`, add a new field after the agents textarea and before the submit button:

```html
<div>
  <label for="tmux_config" class="block text-sm font-medium text-gray-700 mb-1">Tmux Config Path</label>
  <input type="text" name="tmux_config" id="tmux_config" value="{{ org_tmux_config|default('') }}"
         placeholder="/path/to/scripts/tmux-agents.sh"
         class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500">
  <p class="mt-1 text-xs text-gray-400">Optional. Absolute path to a tmux session script for this group.</p>
</div>
```

- [ ] **Step 2: Update admin routes to handle tmux_config**

In `agency/app.py`, update the admin org create and save routes to read/write `tmux_config`:

In `admin_org_create`:
```python
tmux_config = form.get("tmux_config", "").strip()
# Add to config
config["groups"][key] = {
    "name": name,
    "path": path,
    "agents": agents,
}
if tmux_config:
    config["groups"][key]["tmux_config"] = tmux_config
```

In `admin_org_save`:
```python
tmux_config = form.get("tmux_config", "").strip()
if tmux_config:
    config["groups"][org]["tmux_config"] = tmux_config
elif "tmux_config" in config["groups"][org]:
    del config["groups"][org]["tmux_config"]
```

Update the `admin_org_edit` GET route and `admin_org_new` to pass `org_tmux_config` to the template:
```python
"org_tmux_config": g.get("tmux_config", ""),
```

Also update `admin_org_create` POST redirect-with-warning path to include `org_tmux_config`.

- [ ] **Step 3: Add tmux config view/edit routes**

```python
@app.get("/{group}/tmux-config", response_class=HTMLResponse)
async def tmux_config_view(request: Request, group: str):
    """View/edit the tmux config file for a group."""
    g = get_group(group)
    tmux_path = GROUPS.get(group, {}).get("tmux_config", "")
    if not tmux_path:
        raise HTTPException(404, "No tmux config set for this group")
    fpath = Path(tmux_path)
    if not fpath.exists():
        raise HTTPException(404, f"Tmux config file not found: {tmux_path}")
    raw = fpath.read_text()
    return templates.TemplateResponse("tmux_config.html", {
        "request": request,
        **group_context(g),
        "raw": raw,
        "filepath": tmux_path,
    })


@app.post("/{group}/tmux-config/save", response_class=HTMLResponse)
async def tmux_config_save(request: Request, group: str):
    """Save edits to the tmux config file."""
    g = get_group(group)
    tmux_path = GROUPS.get(group, {}).get("tmux_config", "")
    if not tmux_path:
        raise HTTPException(404, "No tmux config set for this group")
    form = await request.form()
    content = form.get("content", "")
    Path(tmux_path).write_text(content)
    return RedirectResponse(f"/{group}/tmux-config", status_code=303)
```

- [ ] **Step 4: Create `agency/templates/tmux_config.html`**

```html
{% extends "base.html" %}
{% set active = "tmux_config" %}

{% block title %}Tmux Config - {{ group_name }}{% endblock %}

{% block content %}
<div class="flex items-baseline justify-between mb-4">
  <h1 class="text-2xl font-bold text-gray-900">Tmux Config</h1>
  <button onclick="document.getElementById('editor').classList.toggle('hidden'); document.getElementById('rendered').classList.toggle('hidden')"
          class="px-3 py-1 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
    Edit
  </button>
</div>

<div class="bg-white rounded-lg border border-gray-200 p-4 md:p-6">
  <div class="text-xs text-gray-400 font-mono mb-4 break-all">{{ filepath }}</div>

  <div id="rendered">
    <pre class="whitespace-pre-wrap text-sm bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto"><code>{{ raw }}</code></pre>
  </div>

  <div id="editor" class="hidden">
    <form method="POST" action="/{{ group }}/tmux-config/save">
      <textarea name="content" rows="30" class="w-full font-mono text-sm border border-gray-300 rounded-lg p-3 bg-gray-50">{{ raw }}</textarea>
      <div class="mt-3 flex justify-end">
        <button type="submit" class="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700">Save</button>
      </div>
    </form>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 5: Add conditional tmux config link to sidebar**

In `agency/templates/base.html`, in the "Config" section of the sidebar, after the Memory link, add:

```html
{% if tmux_config_available %}
<a href="/{{ group }}/tmux-config" class="block px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 {% if active == 'tmux_config' %}active{% endif %}">
  Tmux Config
</a>
{% endif %}
```

Update `group_context()` in `agency/app.py` to include `tmux_config_available`. Use the already-loaded `GROUPS` global instead of re-reading config from disk:

```python
def group_context(g: dict) -> dict:
    """Return standard template context for a group."""
    agency = get_agency_config()
    group_cfg = GROUPS.get(g["key"], {})
    return {
        "group": g["key"],
        "group_name": g["name"],
        "groups": {k: v["name"] for k, v in GROUPS.items()},
        "agency_title": agency.get("title", "Agency"),
        "admin_active": False,
        "tmux_config_available": bool(group_cfg.get("tmux_config")),
    }
```

- [ ] **Step 6: Verify tmux config**

1. Edit newsletter group in admin, add the tmux config path: `/var/home/chris/dev/local-newsletter/scripts/tmux-agents.sh`
2. Confirm "Tmux Config" link appears in sidebar for newsletter group
3. Click it — confirm the shell script renders in a code block
4. Click Edit, make a small change, save — confirm it persists
5. Switch to chrisos group — confirm no "Tmux Config" link in sidebar

- [ ] **Step 7: Commit**

```bash
git add agency/app.py agency/templates/tmux_config.html agency/templates/admin_org_edit.html agency/templates/base.html
git commit -m "feat: add optional tmux config view/edit per group with sidebar integration"
```

---

## Task 12: Final Verification + Install Test

- [ ] **Step 1: Full smoke test**

Restart the server. Walk through every new feature:
1. `/admin/` — sidebar shows only Settings + group switcher (no broken links)
2. `/{group}/agents` — agent cards with names, health, clue counts
3. `/{group}/agents/{agent}` — profile with all sections
4. Save identity fields — verify CLAUDE.md frontmatter merge
5. Expand/collapse all `<details>` sections
6. Click agent badges on clue/curiosity pages — navigates to profile
7. Tmux config view/edit (newsletter group)

- [ ] **Step 2: Test pip install**

```bash
cd ~/dev/agency
.venv/bin/pip install -e .
cd /tmp
agency --port 8501
```

Confirm: config.yaml created in /tmp, server starts, `/admin/` loads.

Clean up:
```bash
rm /tmp/config.yaml
```

- [ ] **Step 3: Restart the production service**

```bash
systemctl --user restart agency.service
systemctl --user status agency.service
```

Confirm service is running on port 8500.

- [ ] **Step 4: Final commit if any loose changes**

```bash
git status
# If anything is unstaged:
git add -A
git commit -m "chore: final cleanup after CLI packaging and agent management features"
```
