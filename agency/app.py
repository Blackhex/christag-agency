"""Agency Dashboard — multi-group agent management interface."""

import csv
import io
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import markdown
import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

import uvicorn

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path.cwd() / "config.yaml"


def load_config() -> dict:
    """Read config.yaml and return dict. Returns defaults if file doesn't exist."""
    if not CONFIG_PATH.exists():
        return {"agency": {"title": "Agency", "default_group": ""}, "groups": {}}
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f) or {}


def save_config(config: dict) -> None:
    """Atomically write config.yaml (temp file + rename)."""
    fd, tmp = tempfile.mkstemp(dir=CONFIG_PATH.parent, suffix=".yaml")
    try:
        with os.fdopen(fd, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        os.replace(tmp, CONFIG_PATH)
    except Exception:
        os.unlink(tmp)
        raise


def reload_groups() -> None:
    """Reload the global GROUPS dict from config."""
    global GROUPS, CONFIG
    CONFIG = load_config()
    GROUPS = CONFIG.get("groups", {})


CONFIG = load_config()
GROUPS = CONFIG.get("groups", {})


def get_agency_config() -> dict:
    """Return agency-level config with defaults."""
    agency = CONFIG.get("agency", {})
    return {
        "title": agency.get("title", "Agency"),
        "default_group": agency.get("default_group", "") or (list(GROUPS.keys())[0] if GROUPS else ""),
    }


app = FastAPI(title="Agency Dashboard")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

md = markdown.Markdown(extensions=["tables", "fenced_code", "meta", "nl2br"])


# ── Group Resolution ──────────────────────────────────────────────────────────


def get_group(group: str) -> dict:
    """Resolve a group key to its full config dict."""
    if group not in GROUPS:
        raise HTTPException(404, f"Unknown group: {group}")
    g = GROUPS[group]
    return {
        "key": group,
        "name": g["name"],
        "path": Path(g["path"]),
        "agents": g["agents"],
        "shared": Path(g["path"]) / "shared",
    }


def group_context(g: dict) -> dict:
    """Return standard template context for a group."""
    agency = get_agency_config()
    return {
        "group": g["key"],
        "group_name": g["name"],
        "groups": {k: v["name"] for k, v in GROUPS.items()},
        "agency_title": agency.get("title", "Agency"),
        "admin_active": False,
    }


# ── Helpers ──────────────────────────────────────────────────────────────────


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown text. Returns (meta, body)."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
                return meta, parts[2].strip()
            except yaml.YAMLError:
                pass
    return {}, text


def render_md(text: str) -> Markup:
    """Render markdown to HTML."""
    md.reset()
    return Markup(md.convert(text))


def read_file(path: Path) -> str:
    """Read a file, return empty string if missing."""
    try:
        return path.read_text()
    except FileNotFoundError:
        return ""


def parse_csv_to_rows(text: str) -> tuple[list[str], list[list[str]]]:
    """Parse CSV text to header + rows, skipping comment lines."""
    lines = [l for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
    if not lines:
        return [], []
    reader = csv.reader(io.StringIO("\n".join(lines)))
    rows = list(reader)
    return rows[0], rows[1:]


def list_clues(g: dict) -> list[dict]:
    """List all clue files with parsed frontmatter."""
    clues_dir = g["shared"] / "clues"
    if not clues_dir.exists():
        return []
    clues = []
    for f in sorted(clues_dir.glob("*.md"), reverse=True):
        raw = f.read_text()
        meta, body = parse_frontmatter(raw)
        meta["_filename"] = f.name
        meta["_body"] = body
        meta["_slug"] = f.stem
        clues.append(meta)
    return clues


def list_curiosities(g: dict) -> list[dict]:
    """List all curiosity files with parsed frontmatter."""
    curiosities_dir = g["shared"] / "curiosities"
    if not curiosities_dir.exists():
        return []
    items = []
    for f in sorted(curiosities_dir.glob("*.md"), reverse=True):
        raw = f.read_text()
        meta, body = parse_frontmatter(raw)
        meta["_filename"] = f.name
        meta["_body"] = body
        meta["_slug"] = f.stem
        items.append(meta)
    return items


def list_decisions(g: dict) -> list[dict]:
    """List all decision files with parsed frontmatter."""
    decisions_dir = g["shared"] / "decisions"
    if not decisions_dir.exists():
        return []
    items = []
    for f in sorted(decisions_dir.glob("*.md"), reverse=True):
        raw = f.read_text()
        meta, body = parse_frontmatter(raw)
        meta["_filename"] = f.name
        meta["_body"] = body
        meta["_slug"] = f.stem
        items.append(meta)
    return items


def collect_documents(g: dict) -> list[dict]:
    """Collect standalone documents from agent directories."""
    docs = []
    skip_dirs = {"clues", "curiosities", "decisions", "prompts", "logs", "archive",
                 "ad-skills", "social-posts", "templates", "dashboard"}

    for agent in g["agents"]:
        agent_dir = g["path"] / agent
        if not agent_dir.exists():
            continue
        for f in sorted(agent_dir.rglob("*")):
            if f.is_dir():
                continue
            if f.name.startswith(".") or f.name == "CLAUDE.md":
                continue
            rel = f.relative_to(agent_dir)
            if any(part in skip_dirs for part in rel.parts[:-1]):
                continue
            suffix = f.suffix.lower()
            if suffix in (".md", ".csv", ".html", ".txt", ".py"):
                docs.append({
                    "agent": agent,
                    "path": str(f),
                    "rel_path": str(rel),
                    "name": f.name,
                    "suffix": suffix,
                })

    # Also add shared standalone files
    shared = g["shared"]
    if shared.exists():
        for f in sorted(shared.iterdir()):
            if f.is_file() and f.suffix in (".md", ".html", ".csv") and f.name != "memory.md":
                docs.append({
                    "agent": "shared",
                    "path": str(f),
                    "rel_path": f.name,
                    "name": f.name,
                    "suffix": f.suffix.lower(),
                })

    return docs


def collect_logs(g: dict) -> dict[str, list[dict]]:
    """Collect log files grouped by date."""
    logs_dir = g["shared"] / "logs"
    if not logs_dir.exists():
        return {}
    result = {}
    for date_dir in sorted(logs_dir.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        entries = []
        for f in sorted(date_dir.iterdir(), reverse=True):
            if f.name.startswith("."):
                continue
            entries.append({
                "name": f.name,
                "path": str(f),
                "suffix": f.suffix,
                "size": f.stat().st_size,
            })
        if entries:
            result[date_dir.name] = entries
    return result


def collect_prompts(g: dict) -> list[dict]:
    """List prompt files."""
    prompts_dir = g["shared"] / "prompts"
    if not prompts_dir.exists():
        return []
    items = []
    for f in sorted(prompts_dir.glob("*.md")):
        items.append({
            "name": f.name,
            "path": str(f),
            "slug": f.stem,
        })
    return items


def collect_memory_files(g: dict) -> list[dict]:
    """Collect all memory.md files."""
    items = []
    # Shared memory
    sm = g["shared"] / "memory.md"
    if sm.exists():
        items.append({"agent": "shared", "path": str(sm), "name": "memory.md"})
    # Per-agent
    for agent in g["agents"]:
        mf = g["path"] / agent / "memory.md"
        if mf.exists():
            items.append({"agent": agent, "path": str(mf), "name": "memory.md"})
    return items


def status_badge(status: str) -> Markup:
    """Return a colored badge for clue/curiosity status."""
    colors = {
        "open": "bg-amber-100 text-amber-800",
        "connected": "bg-blue-100 text-blue-800",
        "investigating": "bg-purple-100 text-purple-800",
        "proposed": "bg-green-100 text-green-800",
        "approved": "bg-emerald-100 text-emerald-800",
        "dismissed": "bg-gray-100 text-gray-500",
        "archived": "bg-gray-100 text-gray-400",
    }
    cls = colors.get(status or "", "bg-gray-100 text-gray-600")
    return Markup(f'<span class="inline-block px-2 py-0.5 rounded-full text-xs font-medium {cls}">{status or "unknown"}</span>')


def agent_badge(agent: str) -> Markup:
    """Return a colored badge for agent name."""
    colors = {
        "editorial": "bg-rose-100 text-rose-700",
        "product": "bg-indigo-100 text-indigo-700",
        "engineering": "bg-sky-100 text-sky-700",
        "sources": "bg-teal-100 text-teal-700",
        "growth": "bg-lime-100 text-lime-700",
        "sales": "bg-orange-100 text-orange-700",
        "design": "bg-fuchsia-100 text-fuchsia-700",
        "business-ops": "bg-yellow-100 text-yellow-700",
        "investigative": "bg-violet-100 text-violet-700",
        "infrastructure": "bg-slate-100 text-slate-700",
        "shared": "bg-gray-100 text-gray-700",
        # ChrisOS agents
        "life-manager": "bg-cyan-100 text-cyan-700",
        "program-manager": "bg-indigo-100 text-indigo-700",
        "home": "bg-amber-100 text-amber-700",
        "personal-style": "bg-pink-100 text-pink-700",
    }
    cls = colors.get(agent or "", "bg-gray-100 text-gray-600")
    return Markup(f'<span class="inline-block px-2 py-0.5 rounded-full text-xs font-medium {cls}">{agent}</span>')


# Register template filters
templates.env.filters["status_badge"] = status_badge
templates.env.filters["agent_badge"] = agent_badge
templates.env.filters["render_md"] = render_md


# ── Routes ───────────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to the default group."""
    agency = get_agency_config()
    default = agency.get("default_group", list(GROUPS.keys())[0] if GROUPS else "")
    if default and default in GROUPS:
        return RedirectResponse(f"/{default}/", status_code=303)
    # Fallback to first group
    first = list(GROUPS.keys())[0] if GROUPS else ""
    if first:
        return RedirectResponse(f"/{first}/", status_code=303)
    return RedirectResponse("/admin/", status_code=303)


# ── Admin Routes ──────────────────────────────────────────────────────────────


@app.get("/admin/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin settings dashboard."""
    config = load_config()
    agency = config.get("agency", {"title": "Agency", "default_group": ""})
    groups = config.get("groups", {})

    # Build org info with initialization status
    orgs = []
    for key, g in groups.items():
        org_path = Path(g["path"])
        shared_exists = (org_path / "shared").exists()
        path_exists = org_path.exists()
        orgs.append({
            "key": key,
            "name": g["name"],
            "path": g["path"],
            "agents": g.get("agents", []),
            "agent_count": len(g.get("agents", [])),
            "initialized": shared_exists,
            "path_exists": path_exists,
        })

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "agency_title": agency.get("title", "Agency"),
        "default_group": agency.get("default_group", ""),
        "orgs": orgs,
        "groups": {k: v["name"] for k, v in groups.items()},
        "admin_active": True,
        "active": "admin",
    })


@app.post("/admin/settings", response_class=HTMLResponse)
async def admin_save_settings(request: Request):
    """Save agency-level settings."""
    form = await request.form()
    title = form.get("title", "Agency").strip()
    default_group = form.get("default_group", "").strip()

    config = load_config()
    if "agency" not in config:
        config["agency"] = {}
    config["agency"]["title"] = title or "Agency"
    if default_group:
        config["agency"]["default_group"] = default_group

    save_config(config)
    reload_groups()
    return RedirectResponse("/admin/", status_code=303)


@app.get("/admin/orgs/new", response_class=HTMLResponse)
async def admin_org_new(request: Request):
    """Create new org form."""
    agency = get_agency_config()
    config = load_config()
    return templates.TemplateResponse("admin_org_edit.html", {
        "request": request,
        "agency_title": agency.get("title", "Agency"),
        "admin_active": True,
        "active": "admin",
        "groups": {k: v["name"] for k, v in config.get("groups", {}).items()},
        "mode": "create",
        "org_key": "",
        "org_name": "",
        "org_path": "",
        "org_agents": "",
        "agent_infos": [],
        "warning": "",
    })


@app.post("/admin/orgs/create", response_class=HTMLResponse)
async def admin_org_create(request: Request):
    """Create a new org."""
    form = await request.form()
    key = form.get("key", "").strip().lower().replace(" ", "-")
    name = form.get("name", "").strip()
    path = form.get("path", "").strip()
    agents_raw = form.get("agents", "").strip()
    agents = [a.strip() for a in agents_raw.splitlines() if a.strip()]

    if not key or not name or not path:
        agency = get_agency_config()
        config = load_config()
        return templates.TemplateResponse("admin_org_edit.html", {
            "request": request,
            "agency_title": agency.get("title", "Agency"),
            "admin_active": True,
            "active": "admin",
            "groups": {k: v["name"] for k, v in config.get("groups", {}).items()},
            "mode": "create",
            "org_key": key,
            "org_name": name,
            "org_path": path,
            "org_agents": agents_raw,
            "agent_infos": [],
            "warning": "Key, name, and path are required.",
        })

    config = load_config()
    if "groups" not in config:
        config["groups"] = {}

    warning = ""
    if not Path(path).exists():
        warning = f"Warning: Path {path} does not exist on disk. You can create it later via Initialize."

    config["groups"][key] = {
        "name": name,
        "path": path,
        "agents": agents,
    }

    save_config(config)
    reload_groups()

    if warning:
        agency = get_agency_config()
        return templates.TemplateResponse("admin_org_edit.html", {
            "request": request,
            "agency_title": agency.get("title", "Agency"),
            "admin_active": True,
            "active": "admin",
            "groups": {k: v["name"] for k, v in config.get("groups", {}).items()},
            "mode": "edit",
            "org_key": key,
            "org_name": name,
            "org_path": path,
            "org_agents": "\n".join(agents),
            "agent_infos": [get_agent_info(Path(path), a) for a in agents] if Path(path).exists() else [],
            "warning": warning + " Org saved successfully.",
        })

    return RedirectResponse("/admin/", status_code=303)


@app.get("/admin/orgs/{org}/edit", response_class=HTMLResponse)
async def admin_org_edit(request: Request, org: str):
    """Edit org form."""
    config = load_config()
    groups = config.get("groups", {})
    if org not in groups:
        raise HTTPException(404, f"Unknown org: {org}")

    g = groups[org]
    agency = get_agency_config()
    base = Path(g["path"])

    # Build rich agent info
    agent_infos = [get_agent_info(base, a) for a in g.get("agents", [])]

    return templates.TemplateResponse("admin_org_edit.html", {
        "request": request,
        "agency_title": agency.get("title", "Agency"),
        "admin_active": True,
        "active": "admin",
        "groups": {k: v["name"] for k, v in groups.items()},
        "mode": "edit",
        "org_key": org,
        "org_name": g["name"],
        "org_path": g["path"],
        "org_agents": "\n".join(g.get("agents", [])),
        "agent_infos": agent_infos,
        "warning": "",
    })


@app.post("/admin/orgs/{org}/save", response_class=HTMLResponse)
async def admin_org_save(request: Request, org: str):
    """Save org changes."""
    form = await request.form()
    name = form.get("name", "").strip()
    path = form.get("path", "").strip()
    agents_raw = form.get("agents", "").strip()
    agents = [a.strip() for a in agents_raw.splitlines() if a.strip()]

    config = load_config()
    if org not in config.get("groups", {}):
        raise HTTPException(404, f"Unknown org: {org}")

    warning = ""
    if path and not Path(path).exists():
        warning = f"Warning: Path {path} does not exist on disk."

    config["groups"][org]["name"] = name or config["groups"][org]["name"]
    if path:
        config["groups"][org]["path"] = path
    config["groups"][org]["agents"] = agents

    save_config(config)
    reload_groups()

    if warning:
        agency = get_agency_config()
        return templates.TemplateResponse("admin_org_edit.html", {
            "request": request,
            "agency_title": agency.get("title", "Agency"),
            "admin_active": True,
            "active": "admin",
            "groups": {k: v["name"] for k, v in config.get("groups", {}).items()},
            "mode": "edit",
            "org_key": org,
            "org_name": config["groups"][org]["name"],
            "org_path": config["groups"][org]["path"],
            "org_agents": "\n".join(agents),
            "agent_infos": [get_agent_info(Path(config["groups"][org]["path"]), a) for a in agents],
            "warning": warning + " Changes saved.",
        })

    return RedirectResponse("/admin/", status_code=303)


@app.post("/admin/orgs/{org}/delete", response_class=HTMLResponse)
async def admin_org_delete(request: Request, org: str):
    """Remove org from config (does not delete files on disk)."""
    config = load_config()
    if org not in config.get("groups", {}):
        raise HTTPException(404, f"Unknown org: {org}")

    del config["groups"][org]

    # If the deleted group was the default, update default
    agency = config.get("agency", {})
    if agency.get("default_group") == org:
        remaining = list(config.get("groups", {}).keys())
        agency["default_group"] = remaining[0] if remaining else ""
        config["agency"] = agency

    save_config(config)
    reload_groups()
    return RedirectResponse("/admin/", status_code=303)


@app.post("/admin/orgs/{org}/initialize", response_class=HTMLResponse)
async def admin_org_initialize(request: Request, org: str):
    """Create the folder structure for an org. Idempotent."""
    config = load_config()
    if org not in config.get("groups", {}):
        raise HTTPException(404, f"Unknown org: {org}")

    g = config["groups"][org]
    base = Path(g["path"])

    # Create base dir if needed
    base.mkdir(parents=True, exist_ok=True)

    # Create shared structure
    shared = base / "shared"
    for subdir in ["clues", "curiosities", "decisions", "prompts", "logs"]:
        (shared / subdir).mkdir(parents=True, exist_ok=True)

    # Create shared memory.md if it doesn't exist
    memory_path = shared / "memory.md"
    if not memory_path.exists():
        memory_path.write_text(f"# {g['name']} — Shared Memory\n\nCollective knowledge and decisions.\n")

    # Copy _clue-system-steps.md from newsletter if it exists and target doesn't
    clue_steps_target = shared / "prompts" / "_clue-system-steps.md"
    if not clue_steps_target.exists():
        # Try to find an existing one to copy
        for other_key, other_g in config.get("groups", {}).items():
            if other_key == org:
                continue
            source = Path(other_g["path"]) / "shared" / "prompts" / "_clue-system-steps.md"
            if source.exists():
                shutil.copy2(source, clue_steps_target)
                break

    # Create agent directories
    for agent in g.get("agents", []):
        (base / agent).mkdir(exist_ok=True)

    return RedirectResponse("/admin/", status_code=303)


@app.post("/admin/orgs/{org}/autodetect", response_class=HTMLResponse)
async def admin_org_autodetect(request: Request, org: str):
    """Auto-detect agents by scanning for directories containing CLAUDE.md."""
    config = load_config()
    if org not in config.get("groups", {}):
        raise HTTPException(404, f"Unknown org: {org}")

    g = config["groups"][org]
    base = Path(g["path"])
    agency = get_agency_config()

    detected = []
    if base.exists():
        for d in sorted(base.iterdir()):
            if d.is_dir() and d.name != "shared" and not d.name.startswith("."):
                if (d / "CLAUDE.md").exists():
                    detected.append(d.name)

    # Update config with detected agents
    agent_names = detected if detected else g.get("agents", [])
    if detected:
        config["groups"][org]["agents"] = detected
        save_config(config)
        reload_groups()

    agent_infos = [get_agent_info(base, a) for a in agent_names]

    return templates.TemplateResponse("admin_org_edit.html", {
        "request": request,
        "agency_title": agency.get("title", "Agency"),
        "admin_active": True,
        "active": "admin",
        "groups": {k: v["name"] for k, v in config.get("groups", {}).items()},
        "mode": "edit",
        "org_key": org,
        "org_name": g["name"],
        "org_path": g["path"],
        "org_agents": "\n".join(agent_names),
        "agent_infos": agent_infos,
        "warning": f"Auto-detected {len(detected)} agents." if detected else "No agents with CLAUDE.md found in path.",
    })


# ── Agent CRUD Routes ────────────────────────────────────────────────────────


def get_agent_info(base: Path, agent_name: str) -> dict:
    """Gather filesystem info about an individual agent."""
    agent_dir = base / agent_name
    info = {
        "name": agent_name,
        "dir_exists": agent_dir.is_dir(),
        "has_claude_md": (agent_dir / "CLAUDE.md").exists(),
        "has_memory": (agent_dir / "memory.md").exists(),
        "has_mcp": (agent_dir / ".mcp.json").exists(),
        "files": [],
    }
    if agent_dir.is_dir():
        info["files"] = sorted(f.name for f in agent_dir.iterdir() if f.is_file())
    return info


@app.get("/admin/orgs/{org}/agents/{agent}", response_class=HTMLResponse)
async def admin_agent_detail(request: Request, org: str, agent: str):
    """View/edit an individual agent."""
    config = load_config()
    groups = config.get("groups", {})
    if org not in groups:
        raise HTTPException(404, f"Unknown org: {org}")

    g = groups[org]
    base = Path(g["path"])
    agency = get_agency_config()

    if agent not in g.get("agents", []):
        raise HTTPException(404, f"Agent '{agent}' not in group '{org}'")

    agent_info = get_agent_info(base, agent)
    agent_dir = base / agent

    # Read editable files
    claude_md = ""
    memory_md = ""
    if agent_dir.is_dir():
        claude_path = agent_dir / "CLAUDE.md"
        memory_path = agent_dir / "memory.md"
        if claude_path.exists():
            claude_md = claude_path.read_text()
        if memory_path.exists():
            memory_md = memory_path.read_text()

    return templates.TemplateResponse("admin_agent_detail.html", {
        "request": request,
        "agency_title": agency.get("title", "Agency"),
        "admin_active": True,
        "active": "admin",
        "groups": {k: v["name"] for k, v in groups.items()},
        "org_key": org,
        "org_name": g["name"],
        "agent": agent_info,
        "claude_md": claude_md,
        "memory_md": memory_md,
        "warning": "",
    })


@app.post("/admin/orgs/{org}/agents/{agent}/save", response_class=HTMLResponse)
async def admin_agent_save(request: Request, org: str, agent: str):
    """Save agent CLAUDE.md and/or memory.md."""
    config = load_config()
    groups = config.get("groups", {})
    if org not in groups:
        raise HTTPException(404, f"Unknown org: {org}")

    g = groups[org]
    base = Path(g["path"])
    agent_dir = base / agent

    # Security: validate path
    agent_dir.resolve().relative_to(base.resolve())

    form = await request.form()
    file_type = form.get("file_type", "claude_md")
    content = form.get("content", "")

    # Create agent dir if it doesn't exist
    agent_dir.mkdir(parents=True, exist_ok=True)

    if file_type == "claude_md":
        (agent_dir / "CLAUDE.md").write_text(content)
    elif file_type == "memory_md":
        (agent_dir / "memory.md").write_text(content)

    return RedirectResponse(f"/admin/orgs/{org}/agents/{agent}", status_code=303)


@app.post("/admin/orgs/{org}/agents/create", response_class=HTMLResponse)
async def admin_agent_create(request: Request, org: str):
    """Add a new agent to a group."""
    config = load_config()
    if org not in config.get("groups", {}):
        raise HTTPException(404, f"Unknown org: {org}")

    form = await request.form()
    agent_name = form.get("name", "").strip().lower().replace(" ", "-")
    agent_name = re.sub(r"[^a-z0-9\-]", "", agent_name)

    if not agent_name:
        return RedirectResponse(f"/admin/orgs/{org}/edit", status_code=303)

    g = config["groups"][org]
    agents = g.get("agents", [])

    if agent_name not in agents:
        agents.append(agent_name)
        config["groups"][org]["agents"] = agents
        save_config(config)
        reload_groups()

    # Create directory + scaffold
    base = Path(g["path"])
    agent_dir = base / agent_name
    agent_dir.mkdir(parents=True, exist_ok=True)
    claude_path = agent_dir / "CLAUDE.md"
    if not claude_path.exists():
        claude_path.write_text(f"# {agent_name.replace('-', ' ').title()} Agent\n\nRole definition goes here.\n")
    memory_path = agent_dir / "memory.md"
    if not memory_path.exists():
        memory_path.write_text(f"# {agent_name.replace('-', ' ').title()} Memory\n\n")

    return RedirectResponse(f"/admin/orgs/{org}/edit", status_code=303)


@app.post("/admin/orgs/{org}/agents/{agent}/rename", response_class=HTMLResponse)
async def admin_agent_rename(request: Request, org: str, agent: str):
    """Rename an agent (config + directory)."""
    config = load_config()
    if org not in config.get("groups", {}):
        raise HTTPException(404, f"Unknown org: {org}")

    form = await request.form()
    new_name = form.get("new_name", "").strip().lower().replace(" ", "-")
    new_name = re.sub(r"[^a-z0-9\-]", "", new_name)

    if not new_name or new_name == agent:
        return RedirectResponse(f"/admin/orgs/{org}/agents/{agent}", status_code=303)

    g = config["groups"][org]
    agents = g.get("agents", [])
    base = Path(g["path"])

    # Update config
    if agent in agents:
        idx = agents.index(agent)
        agents[idx] = new_name
        config["groups"][org]["agents"] = agents
        save_config(config)
        reload_groups()

    # Rename directory if it exists
    old_dir = base / agent
    new_dir = base / new_name
    if old_dir.is_dir() and not new_dir.exists():
        old_dir.rename(new_dir)

    return RedirectResponse(f"/admin/orgs/{org}/agents/{new_name}", status_code=303)


@app.post("/admin/orgs/{org}/agents/{agent}/delete", response_class=HTMLResponse)
async def admin_agent_delete(request: Request, org: str, agent: str):
    """Remove an agent from config. Optionally delete directory."""
    config = load_config()
    if org not in config.get("groups", {}):
        raise HTTPException(404, f"Unknown org: {org}")

    form = await request.form()
    delete_files = form.get("delete_files", "") == "true"

    g = config["groups"][org]
    agents = g.get("agents", [])

    # Remove from config
    if agent in agents:
        agents.remove(agent)
        config["groups"][org]["agents"] = agents
        save_config(config)
        reload_groups()

    # Optionally delete directory
    if delete_files:
        agent_dir = Path(g["path"]) / agent
        agent_dir.resolve().relative_to(Path(g["path"]).resolve())
        if agent_dir.is_dir():
            shutil.rmtree(agent_dir)

    return RedirectResponse(f"/admin/orgs/{org}/edit", status_code=303)


# ── Group Routes ──────────────────────────────────────────────────────────────


@app.get("/{group}/", response_class=HTMLResponse)
async def home(request: Request, group: str):
    """Dashboard home — inbox of items needing attention."""
    g = get_group(group)
    clues = list_clues(g)
    curiosities = list_curiosities(g)
    decisions = list_decisions(g)

    open_clues = [c for c in clues if c.get("status") in ("open",)]
    floated_clues = [c for c in clues if c.get("float")]
    actionable_curiosities = [c for c in curiosities if c.get("status") in ("proposed", "investigating")]

    return templates.TemplateResponse("home.html", {
        "request": request,
        **group_context(g),
        "open_clues": open_clues,
        "floated_clues": floated_clues,
        "actionable_curiosities": actionable_curiosities,
        "recent_decisions": decisions[:5],
        "total_clues": len(clues),
        "total_curiosities": len(curiosities),
        "total_decisions": len(decisions),
        "now": datetime.now().strftime("%B %d, %Y"),
    })


@app.get("/{group}/clues", response_class=HTMLResponse)
async def clues_list(request: Request, group: str, agent: str = "", status: str = ""):
    """List all clues with optional filtering."""
    g = get_group(group)
    clues = list_clues(g)
    if agent:
        clues = [c for c in clues if c.get("agent") == agent]
    if status:
        clues = [c for c in clues if c.get("status") == status]
    return templates.TemplateResponse("clues.html", {
        "request": request,
        **group_context(g),
        "clues": clues,
        "filter_agent": agent,
        "filter_status": status,
        "agents": g["agents"],
    })


@app.get("/{group}/clues/{slug}", response_class=HTMLResponse)
async def clue_detail(request: Request, group: str, slug: str):
    """View a single clue."""
    g = get_group(group)
    path = g["shared"] / "clues" / f"{slug}.md"
    if not path.exists():
        raise HTTPException(404, "Clue not found")
    raw = path.read_text()
    meta, body = parse_frontmatter(raw)
    return templates.TemplateResponse("clue_detail.html", {
        "request": request,
        **group_context(g),
        "meta": meta,
        "body_html": render_md(body),
        "body_raw": body,
        "slug": slug,
        "filename": path.name,
    })


@app.post("/{group}/clues/{slug}/status", response_class=HTMLResponse)
async def clue_update_status(request: Request, group: str, slug: str):
    """Update a clue's status via form submission."""
    g = get_group(group)
    path = g["shared"] / "clues" / f"{slug}.md"
    if not path.exists():
        raise HTTPException(404, "Clue not found")

    form = await request.form()
    new_status = form.get("status", "")
    if new_status not in ("open", "connected", "dismissed", "archived"):
        raise HTTPException(400, "Invalid status")

    raw = path.read_text()
    raw = re.sub(r'^(status:\s*).*$', f'\\1{new_status}', raw, count=1, flags=re.MULTILINE)
    path.write_text(raw)

    return RedirectResponse(f"/{group}/clues/{slug}", status_code=303)


@app.get("/{group}/curiosities", response_class=HTMLResponse)
async def curiosities_list(request: Request, group: str):
    """List all curiosities."""
    g = get_group(group)
    items = list_curiosities(g)
    return templates.TemplateResponse("curiosities.html", {
        "request": request,
        **group_context(g),
        "curiosities": items,
    })


@app.get("/{group}/curiosities/{slug}", response_class=HTMLResponse)
async def curiosity_detail(request: Request, group: str, slug: str):
    """View a single curiosity."""
    g = get_group(group)
    curiosities_dir = g["shared"] / "curiosities"
    clues_dir = g["shared"] / "clues"
    decisions_dir = g["shared"] / "decisions"

    path = curiosities_dir / f"{slug}.md"
    if not path.exists():
        raise HTTPException(404, "Curiosity not found")
    raw = path.read_text()
    meta, body = parse_frontmatter(raw)

    # Find linked clues
    linked = []
    for c in meta.get("clues", []):
        cpath = clues_dir / c
        if cpath.exists():
            linked.append({"filename": c, "slug": cpath.stem})

    # Find related decision
    decision = None
    if decisions_dir.exists():
        for d in decisions_dir.glob("*.md"):
            dtext = d.read_text()
            if slug in dtext:
                dmeta, dbody = parse_frontmatter(dtext)
                decision = {"filename": d.name, "slug": d.stem, "meta": dmeta, "body": dbody}
                break

    return templates.TemplateResponse("curiosity_detail.html", {
        "request": request,
        **group_context(g),
        "meta": meta,
        "body_html": render_md(body),
        "body_raw": body,
        "slug": slug,
        "linked_clues": linked,
        "decision": decision,
    })


@app.post("/{group}/curiosities/{slug}/decide", response_class=HTMLResponse)
async def curiosity_decide(request: Request, group: str, slug: str):
    """Create a decision for a curiosity."""
    g = get_group(group)
    decisions_dir = g["shared"] / "decisions"
    curiosities_dir = g["shared"] / "curiosities"

    form = await request.form()
    decision_text = form.get("decision", "approved")
    notes = form.get("notes", "")

    today = datetime.now().strftime("%Y-%m-%d")
    decision_content = f"""---
curiosity: {slug}.md
decided_by: chris
date: {today}
decision: {decision_text}
---

{notes}
"""
    decisions_dir.mkdir(exist_ok=True)
    decision_path = decisions_dir / f"{slug}.md"
    decision_path.write_text(decision_content)

    # Update curiosity status
    cpath = curiosities_dir / f"{slug}.md"
    if cpath.exists():
        raw = cpath.read_text()
        raw = re.sub(r'^(status:\s*).*$', f'\\1{decision_text}', raw, count=1, flags=re.MULTILINE)
        cpath.write_text(raw)

    return RedirectResponse(f"/{group}/curiosities/{slug}", status_code=303)


@app.get("/{group}/decisions", response_class=HTMLResponse)
async def decisions_list(request: Request, group: str):
    """List all decisions."""
    g = get_group(group)
    items = list_decisions(g)
    return templates.TemplateResponse("decisions.html", {
        "request": request,
        **group_context(g),
        "decisions": items,
    })


@app.get("/{group}/decisions/{slug}", response_class=HTMLResponse)
async def decision_detail(request: Request, group: str, slug: str):
    """View a single decision."""
    g = get_group(group)
    path = g["shared"] / "decisions" / f"{slug}.md"
    if not path.exists():
        raise HTTPException(404, "Decision not found")
    raw = path.read_text()
    meta, body = parse_frontmatter(raw)
    return templates.TemplateResponse("decision_detail.html", {
        "request": request,
        **group_context(g),
        "meta": meta,
        "body_html": render_md(body),
        "slug": slug,
    })


@app.get("/{group}/documents", response_class=HTMLResponse)
async def documents_list(request: Request, group: str, agent: str = ""):
    """Browse documents by agent."""
    g = get_group(group)
    docs = collect_documents(g)
    if agent:
        docs = [d for d in docs if d["agent"] == agent]
    by_agent = {}
    for d in docs:
        by_agent.setdefault(d["agent"], []).append(d)
    return templates.TemplateResponse("documents.html", {
        "request": request,
        **group_context(g),
        "by_agent": by_agent,
        "filter_agent": agent,
        "agents": g["agents"] + ["shared"],
    })


@app.get("/{group}/documents/view", response_class=HTMLResponse)
async def document_view(request: Request, group: str, path: str):
    """View a document file."""
    g = get_group(group)
    fpath = Path(path)
    # Security: must be under this group's agents dir
    try:
        fpath.resolve().relative_to(g["path"].resolve())
    except ValueError:
        raise HTTPException(403, "Access denied")
    if not fpath.exists():
        raise HTTPException(404, "File not found")

    raw = fpath.read_text()
    suffix = fpath.suffix.lower()

    content_html = ""
    is_csv = False
    csv_headers = []
    csv_rows = []

    if suffix == ".csv":
        is_csv = True
        csv_headers, csv_rows = parse_csv_to_rows(raw)
    elif suffix == ".html":
        content_html = raw
    elif suffix == ".md":
        _, body = parse_frontmatter(raw)
        content_html = render_md(body)
    else:
        content_html = f"<pre class='whitespace-pre-wrap text-sm'>{raw}</pre>"

    return templates.TemplateResponse("document_view.html", {
        "request": request,
        **group_context(g),
        "filename": fpath.name,
        "filepath": str(fpath),
        "raw": raw,
        "content_html": content_html,
        "is_csv": is_csv,
        "csv_headers": csv_headers,
        "csv_rows": csv_rows,
        "suffix": suffix,
        "is_editable": suffix in (".md", ".csv"),
    })


@app.post("/{group}/documents/save", response_class=HTMLResponse)
async def document_save(request: Request, group: str):
    """Save edits to a document."""
    g = get_group(group)
    form = await request.form()
    path = form.get("path", "")
    content = form.get("content", "")
    fpath = Path(path)

    try:
        fpath.resolve().relative_to(g["path"].resolve())
    except ValueError:
        raise HTTPException(403, "Access denied")

    fpath.write_text(content)
    return RedirectResponse(f"/{group}/documents/view?path={path}", status_code=303)


@app.get("/{group}/logs", response_class=HTMLResponse)
async def logs_list(request: Request, group: str):
    """Browse execution logs by date."""
    g = get_group(group)
    logs = collect_logs(g)
    return templates.TemplateResponse("logs.html", {
        "request": request,
        **group_context(g),
        "logs": logs,
    })


@app.get("/{group}/logs/view", response_class=HTMLResponse)
async def log_view(request: Request, group: str, path: str):
    """View a log file."""
    g = get_group(group)
    fpath = Path(path)
    logs_dir = g["shared"] / "logs"
    try:
        fpath.resolve().relative_to(logs_dir.resolve())
    except ValueError:
        raise HTTPException(403, "Access denied")
    if not fpath.exists():
        raise HTTPException(404, "Log not found")

    raw = fpath.read_text()
    content_html = render_md(raw) if fpath.suffix == ".out" else f"<pre class='whitespace-pre-wrap text-sm text-red-700'>{raw}</pre>"

    return templates.TemplateResponse("log_view.html", {
        "request": request,
        **group_context(g),
        "filename": fpath.name,
        "content_html": content_html,
        "raw": raw,
    })


@app.get("/{group}/prompts", response_class=HTMLResponse)
async def prompts_list(request: Request, group: str):
    """Browse and edit agent prompts."""
    g = get_group(group)
    items = collect_prompts(g)
    return templates.TemplateResponse("prompts.html", {
        "request": request,
        **group_context(g),
        "prompts": items,
    })


@app.get("/{group}/prompts/{slug}", response_class=HTMLResponse)
async def prompt_detail(request: Request, group: str, slug: str):
    """View/edit a prompt."""
    g = get_group(group)
    path = g["shared"] / "prompts" / f"{slug}.md"
    if not path.exists():
        raise HTTPException(404, "Prompt not found")
    raw = path.read_text()
    content_html = render_md(raw)
    return templates.TemplateResponse("prompt_detail.html", {
        "request": request,
        **group_context(g),
        "slug": slug,
        "raw": raw,
        "content_html": content_html,
    })


@app.post("/{group}/prompts/{slug}/save", response_class=HTMLResponse)
async def prompt_save(request: Request, group: str, slug: str):
    """Save edits to a prompt."""
    g = get_group(group)
    path = g["shared"] / "prompts" / f"{slug}.md"
    form = await request.form()
    content = form.get("content", "")
    path.write_text(content)
    return RedirectResponse(f"/{group}/prompts/{slug}", status_code=303)


@app.get("/{group}/memory", response_class=HTMLResponse)
async def memory_list(request: Request, group: str):
    """Browse and edit agent memory files."""
    g = get_group(group)
    items = collect_memory_files(g)
    return templates.TemplateResponse("memory.html", {
        "request": request,
        **group_context(g),
        "memory_files": items,
    })


@app.get("/{group}/memory/view", response_class=HTMLResponse)
async def memory_view(request: Request, group: str, path: str):
    """View/edit a memory file."""
    g = get_group(group)
    fpath = Path(path)
    try:
        fpath.resolve().relative_to(g["path"].resolve())
    except ValueError:
        raise HTTPException(403, "Access denied")
    if not fpath.exists():
        raise HTTPException(404, "Memory file not found")

    raw = fpath.read_text()
    content_html = render_md(raw)
    agent = fpath.parent.name

    return templates.TemplateResponse("memory_view.html", {
        "request": request,
        **group_context(g),
        "agent": agent,
        "path": str(fpath),
        "raw": raw,
        "content_html": content_html,
    })


@app.post("/{group}/memory/save", response_class=HTMLResponse)
async def memory_save(request: Request, group: str):
    """Save edits to a memory file."""
    g = get_group(group)
    form = await request.form()
    path = form.get("path", "")
    content = form.get("content", "")
    fpath = Path(path)

    try:
        fpath.resolve().relative_to(g["path"].resolve())
    except ValueError:
        raise HTTPException(403, "Access denied")

    fpath.write_text(content)
    return RedirectResponse(f"/{group}/memory/view?path={path}", status_code=303)


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


if __name__ == "__main__":
    main()
