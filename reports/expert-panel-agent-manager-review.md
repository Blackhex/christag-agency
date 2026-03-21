# Expert Panel Review: Agency as a Standalone Agent Manager

**Date:** 2026-03-20
**Subject:** Agency — a filesystem-backed web dashboard for managing multiple groups of AI agents
**Lens:** Shipping to colleagues as a standalone tool. Evaluated for efficiency, user satisfaction, design quality — not profit.

---

## The Panel

1. **Simon Willison** — local-first data tools, filesystem-as-database architecture (Datasette creator)
2. **Maggie Appleton** — information design, mental models, and knowledge interfaces
3. **Guillermo Rauch** — developer experience, zero-config, deployment simplicity (Vercel CEO)
4. **Julie Zhuo** — product design for managers, utility and clarity (former VP Design, Facebook)
5. **Rasmus Andersson** — visual craft, systematic design, typographic precision (Figma designer, Inter creator)

---

## Synthesis

### Common Ground

**The filesystem-as-database choice is the project's strongest architectural decision.** Four of five panelists called this out positively. No migrations, no database setup, no Docker dependency — just point it at a directory of markdown files and go. For a tool you're handing to a colleague, this removes the single biggest adoption barrier. Simon Willison would call this "inspectable by default" — every piece of state is a file you can `cat`, `grep`, or version-control. This is a genuine differentiator against heavier agent management platforms.

**The information model (Clue → Curiosity → Decision) is interesting but not self-explanatory.** Every panelist flagged some version of this concern. The pipeline makes sense once you understand it, but a new user landing on the Inbox page will see "Open Clues" and "Floated Signals" without knowing what those mean, why they matter, or what action to take. The vocabulary is novel — that's a feature for expressiveness but a cost for onboarding.

**The app is impressively complete for its size.** ~1,100 lines of Python, 18 templates, no build step, no external services. The scope is well-controlled. The admin panel with Initialize/Autodetect is a thoughtful touch. Multiple panelists noted this as evidence of good product instinct — shipping something usable rather than something ambitious-but-broken.

### Points of Divergence

**How much onboarding scaffolding does it need?**

Guillermo Rauch would argue the tool should work with zero explanation — a new user should be able to `pip install agency && agency init` and understand everything from the UI alone. The current state requires reading CLAUDE.md or having someone explain the Clue/Curiosity/Decision model. Maggie Appleton, by contrast, would say the novel vocabulary is fine *if* the UI itself teaches it — inline definitions, progressive disclosure, a first-run state that explains the pipeline. She'd resist dumbing down the model; she'd invest in making it learnable.

**Single-file app vs. modular architecture?**

Simon Willison would keep the single `app.py` — it's a feature, not a bug. One file to read, one file to understand. Rasmus Andersson would push back: the templates are already separated, and the routes could benefit from grouping (admin, clues, documents) for contributor clarity. But for a tool at this scale, the single-file approach is defensible and the panel leans toward keeping it.

**How polished does the visual design need to be?**

Julie Zhuo and Rasmus Andersson diverge here. Julie would say the current Tailwind utility-class approach is perfectly adequate for an internal tool — clean, functional, not distracting. Rasmus would identify specific craft gaps: the sidebar navigation lacks visual hierarchy beyond text weight, the color-coded badges are functional but could be more systematic, and the empty states are plain. Both would agree it's well above the "ugly internal tool" bar, but they'd draw the "good enough" line differently.

### Actionable Takeaways

**1. Add a 30-second onboarding moment.** When a new user hits an empty group (or their first visit), show a brief explanation of the Clue → Curiosity → Decision pipeline. Not a tour — a single card or section that says "Here's how your agents communicate with you through this tool." This is the single highest-leverage change for colleague adoption.

**2. Make setup a one-liner.** Right now setup requires cloning the repo, creating a venv, installing deps, and understanding the config. Package it as a `pip install`-able CLI: `pip install agency-dashboard && agency init ~/my-agents && agency serve`. The `pyproject.toml` already has `[project.scripts]` — finish that path. Consider a `agency init` command that creates a sample config.yaml and one demo group with a few example clues so the user sees a populated UI immediately.

**3. Decouple the vocabulary from your specific agent framework.** The Clue/Curiosity/Decision pipeline is tightly coupled to a specific way of running agents (dispatch.sh, shared directories, YAML frontmatter). For colleagues with different agent setups, consider making the "observation → proposal → decision" pipeline the *documented abstraction* while keeping the file format flexible. At minimum, document what a minimal agent group looks like (just a directory with a CLAUDE.md) versus a fully-featured one.

**4. Add lightweight status/health signals.** Every panelist noted the absence of "is this agent actually running?" information. The Inbox shows what agents have *produced*, but not whether they're active, stale, or erroring. Even a simple "last seen" timestamp per agent (derived from log file dates) would give managers confidence that the system is working. This is the difference between a file browser and an agent *manager*.

**5. Polish the empty states and first-run experience.** The current "All clear / No items need your attention" empty state is fine for a returning user, but for a first-time user it reads as "nothing is here and I don't know what to do." Consider: sample data, getting-started prompts, or at minimum a link to documentation that explains what would appear here and how to make it happen.

---

## Full Expert-by-Expert Breakdown

### Simon Willison
*Filesystem-backed tools, inspectable data, and the power of keeping things simple*

This is exactly the kind of tool I love to see. No database, no migrations, no Docker compose file with five services — just a Python script that reads markdown files off disk. That's not a limitation, that's a *feature*. Every piece of state in this system is a file you can inspect with standard Unix tools, version with git, back up with rsync, and debug by reading. When something goes wrong, you `cat` the file. When you want to migrate, you copy a directory.

The YAML frontmatter + markdown body pattern is well-chosen. It's the same format used by Hugo, Jekyll, Obsidian, and dozens of other tools. Your colleagues' agents don't need to know anything about Agency — they just need to write markdown files with some YAML at the top. That's a protocol, not a dependency.

The path traversal protection (`fpath.resolve().relative_to(g["path"].resolve())`) is correctly implemented — I've seen too many file-serving tools get this wrong. The atomic config writes (temp file + `os.replace`) show someone who's thought about failure modes. These are the kind of details that matter when a tool is running as a long-lived service.

What I'd push on: **make it installable and self-documenting**. Right now I need to clone a repo and read a CLAUDE.md to understand what this does. If I could `pip install agency-dashboard` and run `agency --help`, and if the web UI had a `/docs` or `/api` endpoint that described the expected file format, adoption would be dramatically easier. Also consider adding a simple JSON API alongside the HTML routes — same data, `Accept: application/json` header. That lets people build on top of it without scraping HTML.

The `collect_documents` function with its hardcoded `skip_dirs` set is a minor smell — that should probably be configurable per group. But I say that as someone who's built a lot of these tools. At this stage, hardcoding is fine.

One more thing: the `markdown.Markdown` instance is created once at module level and reused via `.reset()`. That's the correct pattern — I've seen people create a new instance per render and wonder why it's slow. Good.

### Maggie Appleton
*Information architecture, mental models, and making complex systems learnable*

The Clue → Curiosity → Decision pipeline is genuinely interesting as an information model. It maps to something real: agents observe things (clues), those observations converge into proposals worth considering (curiosities), and a human makes a call (decisions). That's a good abstraction for human-in-the-loop agent management.

But — and this is a significant "but" — the vocabulary does real work that the interface doesn't explain. "Clue" is a metaphor borrowed from investigative contexts. "Curiosity" is being used in a specific technical sense (a converged proposal) that doesn't match its everyday meaning. "Float" as a verb for promoting a signal is evocative but non-obvious. A colleague opening this tool for the first time would understand "Inbox" and "Documents" immediately, but would need to construct a mental model for the rest.

The sidebar navigation tells me the *nouns* of the system (Clues, Curiosities, Decisions, Documents, Logs, Prompts, Memory) but not the *verbs* or the *flow*. I don't know from looking at the UI that clues can become curiosities, or that curiosities get decided on. The detail pages reveal this — the curiosity detail shows linked clues and has a decision form — but the list views don't hint at the pipeline.

My recommendation: don't change the vocabulary (it's expressive and memorable once learned), but invest in making the pipeline *visible*. A small diagram or flow indicator somewhere — even just in the Inbox — that shows "Agents observe → Clues appear → Some become Curiosities → You decide." The curiosity detail page already does this well with linked clues and the decision form inline. Bring that same connective tissue to the list views and the inbox.

The "Floated Signals" section in the Inbox is a nice touch — it's a priority layer on top of clues. But again, "floated" needs a tooltip or inline explanation. What makes something float? Who floats it? The agent? The system? The user?

One design pattern I'd borrow: Obsidian's approach to novel concepts. They introduce "backlinks," "graph view," and "canvas" — all non-obvious concepts — but each has a clear empty state that explains what it is and how to use it. The "All clear" empty state in Agency's Inbox is a missed opportunity to teach.

### Guillermo Rauch
*Zero-config, instant feedback, and removing every possible barrier to adoption*

First impression: this is a good tool that's currently trapped inside a repo. To ship this to colleagues, you need to remove every step between "I want to try this" and "I'm looking at my agents."

Right now the setup path is: clone repo → create venv → install deps → understand config.yaml format → point it at your agent directories → run the server. That's five steps too many. The goal is: `npx agency-dashboard` — or the Python equivalent — and you're running. If there's no config, create one interactively. If there's no agent directory, offer to scan common locations or create a demo.

The `pyproject.toml` already has `[project.scripts]` pointing to `app:main`. That's 80% of the way there. Finish it: publish to PyPI, add an `agency init` command that walks you through setup, and make the first run show a populated demo group so the UI isn't empty.

Performance-wise, the current approach of reading every file in a directory on each page load is fine at small scale but will feel sluggish once someone has hundreds of clues. You don't need a database — a simple in-memory cache with filesystem watching (or just a TTL) would keep the responsiveness high. `watchfiles` is already in the uvicorn dependency tree.

The Tailwind CDN include (`<script src="https://cdn.tailwindcss.com">`) is fine for development but wrong for production. It's 300KB+ of JavaScript that runs on every page load to process utility classes. For a shipped tool, run `tailwindcss` once at build time and ship the 5KB of CSS you actually use. This alone would make pages load noticeably faster, and it removes the CDN dependency for offline/airgapped use (relevant for colleagues running this on internal networks).

The group switcher (a `<select>` dropdown in the sidebar) is functional but feels like an afterthought. If the group is the primary organizational unit — and it is — it should feel more prominent. A top-bar with the current group name, or tabs, or a more visually distinct switcher.

One more thing: no loading states anywhere. Every navigation is a full page load with no visual feedback. For a server-rendered app this is usually fine, but if the file reads ever take >200ms (large directories, network-mounted filesystems), users will wonder if their click registered. Consider `<style> a:active { opacity: 0.5 } </style>` as a minimal affordance.

### Julie Zhuo
*Product utility, clarity of purpose, and the manager's perspective*

I'm evaluating this from the perspective of someone who would actually use it daily — a person managing multiple AI agents across different projects, trying to stay on top of what they're doing and whether they need intervention.

The Inbox page gets the core job right: here are the things that need your attention, ranked roughly by urgency. The stats row (open clues, needs action, decisions) gives a quick pulse check. The "Curiosities Needing Your Decision" section front-and-center is correct — that's the primary action a human takes in this system.

What's missing from a manager's perspective:

**Time context.** When did these clues arrive? How long have they been waiting? The date is buried in metadata. If a clue has been open for 3 days, that feels different from one that appeared 20 minutes ago. The `ttl_days` field exists in the data model but isn't surfaced in the UI — I should see "expires in 2 days" or "overdue" badges.

**Agent-level view.** I can filter clues by agent, but there's no "agent dashboard" — a page that shows me, for a given agent, its role, recent activity, memory state, and any outstanding items. Right now I piece this together by visiting Documents (to see its CLAUDE.md), Memory (to see its memory.md), Clues (filtered by agent), and Logs. An agent profile page would consolidate this.

**Batch operations.** If I have 15 open clues and want to dismiss 10 of them, I currently visit each one individually and change its status. A checkbox + bulk action on the list view would save significant time for active groups.

**Notification or digest.** The tool is purely pull-based — I have to remember to open it and check. For colleagues who are busy (all of them), a daily digest email or a webhook that pings Slack when a curiosity moves to "proposed" would dramatically increase engagement. Without this, the tool becomes something people forget to check.

The decision-making flow on the curiosity detail page is well-designed: approve/defer/reject with notes, inline and immediate. That's the right UX for a quick judgment call. But the decisions list page is just a chronological list — it should show the linked curiosity title, not just the decision slug, so I can understand what I decided without clicking through.

Overall: this is a strong v1 for personal use. To make it work for colleagues, the gap is less about features and more about **proactive communication** — the tool needs to come to the user, not wait for the user to come to it.

### Rasmus Andersson
*Visual systems, typographic precision, and the details that create quality*

The visual foundation is solid — clean white cards, appropriate use of whitespace, well-chosen border radii. The Tailwind utility classes are applied consistently, which avoids the "inconsistent spacing" problem I see in most internal tools. The mobile sidebar implementation (hamburger + overlay) is correctly done and the responsive breakpoints are reasonable.

What I'd refine:

**The sidebar typography is too uniform.** Every nav item is `text-sm font-medium text-gray-700`. The section dividers ("Resources," "Config," "Admin") use `text-xs font-semibold text-gray-400 uppercase tracking-wider` — that's good — but the items below them all look identical. The active state (`bg-indigo-50 text-indigo-700`) is subtle enough to miss on some monitors. Consider a stronger active indicator: a left border accent, a background that's more distinct from hover, or a dot/indicator. Navigation should never make me wonder "which page am I on?"

**The badge system is functional but not systematic.** Status badges use semantic colors (amber for open, purple for investigating, green for approved) — that's correct. But agent badges use a hardcoded color map in Python (`agent_badge` function at line 301-322). This means a new agent added by a colleague gets the fallback gray, which looks broken rather than intentional. Generate colors deterministically from the agent name (hash to hue) so every agent always has a distinct, consistent color without manual mapping.

**The code font rendering in the editor views is bare.** The `<textarea>` elements for editing memory, prompts, and documents use `font-mono text-sm` with no syntax highlighting, no line numbers, and no resize handle beyond the browser default. For a tool where editing markdown and YAML is a primary action, this feels under-invested. You don't need CodeMirror — even a `white-space: pre` with visible tab stops and a minimum height would improve the editing experience. Consider a monospace font stack that's more intentional: `'JetBrains Mono', 'Fira Code', 'SF Mono', ui-monospace, monospace`.

**Empty states lack visual weight.** The "No clues found" and "All clear" states are centered gray text in a white card. They're not ugly, but they're forgettable. An empty state is an opportunity — either to delight (a small illustration, a subtle pattern) or to instruct (next steps, how items appear here). Even a single line of secondary text explaining *how* clues get created would transform these from dead ends into waypoints.

**The color palette is safe but could have more personality.** Indigo as the primary action color, gray for structure, semantic colors for status — this is the Tailwind default palette and it reads as "generic dashboard." For a tool with a name like "Agency" and a concept model built around investigation metaphors (clues, curiosities), there's room for a more distinctive color identity. Even shifting the primary from indigo to a deep teal or a warm slate would make it feel less like a template and more like a product.

---

## Priority Matrix

| Change | Impact | Effort | Who Cares Most |
|--------|--------|--------|-----------------|
| Onboarding / first-run explanation | High | Low | Maggie, Julie |
| `pip install` + `agency init` CLI | High | Medium | Guillermo, Simon |
| Agent health / "last seen" indicator | High | Low | Julie, Simon |
| Replace Tailwind CDN with built CSS | Medium | Low | Guillermo, Rasmus |
| Deterministic agent badge colors | Medium | Low | Rasmus |
| Batch operations on clue list | Medium | Medium | Julie |
| Notification/digest system | High | High | Julie, Guillermo |
| Agent profile/dashboard page | Medium | Medium | Julie, Maggie |
| Inline pipeline explanation in UI | Medium | Low | Maggie |
| Stronger sidebar active states | Low | Low | Rasmus |

---

## Bottom Line

Agency is a surprisingly well-built internal tool — clean architecture, correct security patterns, thoughtful data model, and a UI that's well above the "developer side project" bar. The filesystem-as-database approach is its secret weapon for adoption: no infrastructure to deploy, no state to migrate, everything inspectable and version-controllable.

The gap between "Chris's personal tool" and "something colleagues adopt" is narrower than you might think. It's not a feature gap — it's an **onboarding and packaging gap**. The tool already does useful things; it just needs to explain itself better and be easier to start. A `pip install`, an `init` command, a first-run explanation card, and a "last seen" timestamp per agent would get you 80% of the way there.

The deeper question the panel surfaced: **is this a file browser for agent output, or is it an agent manager?** Right now it's closer to the former — it shows you what agents have produced but doesn't help you understand whether they're running, healthy, or doing what you expect. The "manager" part is the human reading files and making decisions. Pushing slightly toward real management (health indicators, batch operations, proactive notifications) would make it genuinely indispensable rather than merely useful.
