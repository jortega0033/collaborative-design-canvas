# Agency Agents roles used in this repository

The Markdown files in `.claude/agents/` whose names start with `engineering-`, `security-` or `testing-` are copies of role definitions from Agency Agents. They are project-local Claude Code subagents. The file `loop-verifier.md` in the same folder is not from Agency Agents; it belongs to the Loop Engineering setup described in [`LOOP.md`](../../LOOP.md).

## Source and licence

- Upstream: https://github.com/msitarzewski/agency-agents
- Pinned revision: `8ae6164602c95ca78828b148b9052460ee426885` (upstream `main`, committed 2026-11-09)
- Licence: MIT, "Copyright (c) 2025 AgentLand Contributors". The upstream licence text at the pinned revision is kept unchanged in [`LICENSE`](LICENSE) next to this file (SHA-256 `9a45258434d5cedf0af73c9ad4771373701225038d246c49219026c33677f66f`). It covers only the copied role files, not the rest of this repository.
- Fetched with `gh api -H "Accept: application/vnd.github.raw" "repos/msitarzewski/agency-agents/contents/<path>?ref=<revision>"`.

## Installed roles

"Upstream SHA-256" is the hash of the file as fetched at the pinned revision (LF line endings). Reviewer roles have one added frontmatter line, `tools: Read, Grep, Glob`, so they cannot edit files or run commands. Nothing else in any file was changed.

| File in `.claude/agents/` | `name:` | Upstream path | Upstream SHA-256 | Local change |
|---|---|---|---|---|
| `engineering-software-architect.md` | Software Architect | `engineering/engineering-software-architect.md` | `b85121691776147bacde26673e68fbbacd6a7f0816d1ca8e203c264d25ce1d30` | added `tools: Read, Grep, Glob` |
| `engineering-code-reviewer.md` | Code Reviewer | `engineering/engineering-code-reviewer.md` | `7509fcc3ea1dda46511b2801996305bf3d4a125576f9655ff0b63df25602f446` | added `tools: Read, Grep, Glob` |
| `engineering-codebase-onboarding-engineer.md` | Codebase Onboarding Engineer | `engineering/engineering-codebase-onboarding-engineer.md` | `07aa548b45887c3ad768efad5fdbf6e57bea639df4f1b74c7e383142f454e2a1` | added `tools: Read, Grep, Glob` |
| `engineering-database-optimizer.md` | Database Optimizer | `engineering/engineering-database-optimizer.md` | `6d773003e3b9251068ab537be94d6827c118201e0e17c11d789cb29dc245bf99` | added `tools: Read, Grep, Glob` |
| `engineering-realtime-collaboration-engineer.md` | Realtime Collaboration Engineer | `engineering/engineering-realtime-collaboration-engineer.md` | `79b1fa3544a7f768ca3702b8b41f2969c9ea14ddb73c7fe349fc652219f91a75` | added `tools: Read, Grep, Glob` |
| `security-appsec-engineer.md` | Application Security Engineer | `security/security-appsec-engineer.md` | `a19f0bda46f4adca5737365dbc3c7ed93e9d93b71349536d92ff055dcf4e3b83` | added `tools: Read, Grep, Glob` |
| `testing-accessibility-auditor.md` | Accessibility Auditor | `testing/testing-accessibility-auditor.md` | `362935907af23839775b9c6162f38c0c5a740542ab4350cb5c5b5a0d9f9a4268` | added `tools: Read, Grep, Glob` |
| `testing-reality-checker.md` | Reality Checker | `testing/testing-reality-checker.md` | `6d32fcdb114233e13902ec6372d50293b120e85d490b5e81d372c29808f988a1` | added `tools: Read, Grep, Glob` |
| `engineering-backend-architect.md` | Backend Architect | `engineering/engineering-backend-architect.md` | `ac717bde4848d7663fff8a3c7edc711fd119256de6a7ce38c036619372f42c99` | none |
| `engineering-frontend-developer.md` | Frontend Developer | `engineering/engineering-frontend-developer.md` | `1ae4cc10b2e0163bd3ed921ad54080b865cd02e591becd8919b64b73fab06dad` | none |
| `testing-api-tester.md` | API Tester | `testing/testing-api-tester.md` | `ab91de9188d48bd9c417282c33673a37b066215e90e08c0f1b270d036084e3bb` | none |

## Why these roles

| Role | Use in this repository |
|---|---|
| Software Architect (read-only) | Review a ticket's design against the layering in [`docs/architecture.md`](../../docs/architecture.md) before code is written: where the operation log lives, how operations, undo and patches share one write path, how components and frames extend the closed layer type list. |
| Code Reviewer (read-only) | Review a diff for correctness, missed edge cases and broken rules (all-or-nothing writes, request guards on new routes, strict validation, no traceback in responses, text through `textContent` only). |
| Codebase Onboarding Engineer (read-only) | Trace a code path and report facts with file and line citations. |
| Database Optimizer (read-only) | Review schema changes, the first real migrations, table rebuilds for new layer types, indexes and transaction scope in `design_canvas/storage.py`. Four planned tickets add tables. |
| Realtime Collaboration Engineer (read-only) | Review the two-tab design of issue #3: per-client ordering, duplicate delivery, the gap rule, per-field last-writer-wins, reorder by anchors, offline replay. It reviews; it does not build. Its text prefers WebSockets and CRDTs, which this repository does not use (polling over loopback, server-arbitrated rules). |
| Application Security Engineer (read-only) | Review anything that parses outside input, above all the SVG import of issue #6 (DOCTYPE and entity rejection before parsing, element and attribute allowlists, size and depth caps), and any change to the request guards. |
| Accessibility Auditor (read-only) | Review keyboard operation, focus return, `aria-activedescendant`, labels and live regions. PRD section 8 makes these requirements, and the command list and the resolution panel carry them as acceptance criteria. |
| Reality Checker (read-only) | Compare claimed evidence with what was actually run before a ticket or the epic is called done. |
| Backend Architect | Implement work in `design_canvas/*.py` (HTTP layer, storage and migrations, validation, operations, layout, SVG). |
| Frontend Developer | Implement work in `design_canvas/static/`. |
| API Tester | Write the HTTP-level `unittest` cases in `tests/` for new and existing routes. |

Most of these roles are written for larger stacks. Backend Architect, Frontend Developer and API Tester mention frameworks, cloud services, Postman, k6 and Playwright; Database Optimizer is written around PostgreSQL and MySQL; Application Security Engineer mentions SAST and DAST pipelines. In this repository the rules in [`CLAUDE.md`](../../CLAUDE.md) win: Python standard library only, SQLite, native HTML, CSS and JavaScript, `unittest`, no pip or npm dependencies, no external requests.

Roles that were considered and left out: Performance Benchmarker (no performance requirement in the PRD), Test Automation Engineer and Evidence Collector (browser automation needs a dependency this repository does not allow; browser checks are manual and recorded), UI Designer and UX Architect (the page layout and labels are fixed by PRD section 6 and `tests/test_static_ui.py`), Technical Writer (documentation changes are part of each ticket).

## Name collision with user-level agents

A developer who has installed Agency Agents in `~/.claude/agents/` already has agents with the same `name:` values. Claude Code gives the project-level definition precedence, so inside this repository the copies here are used, including the read-only tool limits. The upstream names were kept on purpose so that the roles stay recognisable and can be compared with upstream.

A Claude Code session that was already running when these files were added keeps the definitions it loaded at start. Start a new session to pick up the project copies.

## Check that the roles load

From the repository root, in a new session:

```text
claude -p "Using only your loaded agent list, say for each of these names whether it is available and which tools it has: Software Architect; Code Reviewer; Codebase Onboarding Engineer; Database Optimizer; Realtime Collaboration Engineer; Application Security Engineer; Accessibility Auditor; Reality Checker; Backend Architect; Frontend Developer; API Tester; loop-verifier. Then run the Reality Checker subagent and ask it which tools it has."
```

The eight reviewer roles and `loop-verifier` must report exactly `Read, Grep, Glob`.

### What was observed, and what was not

Observed on 2026-11-22 with Claude Code 2.1.323, headless (`claude -p`, model requested: haiku, no MCP servers), from the repository root, on a machine that also has a user-level Agency Agents install:

- All twelve names were reported as available. Software Architect, Code Reviewer, Codebase Onboarding Engineer, Database Optimizer, Realtime Collaboration Engineer, Application Security Engineer, Accessibility Auditor, Reality Checker and `loop-verifier` were listed with `Read, Grep, Glob`. Backend Architect, Frontend Developer and API Tester were listed with all tools.
- A launched Reality Checker, a launched Application Security Engineer and a launched Realtime Collaboration Engineer each reported exactly `Read`, `Grep`, `Glob`. No user-level copy of the eight reviewer roles on that machine has a `tools:` line, so the tool limits show that the project copies were the ones loaded.
- The user-level copies of the three implementing roles on that machine are an older upstream revision with different example code. Each role was launched and asked to quote its own instructions, and each quoted text that exists only in the project copy: Backend Architect listed the tables `users`, `categories`, `products` (the user-level copy has no `categories` table), Frontend Developer quoted the comment "Renderable cell values and stable IDs keep the example self-contained.", and API Tester quoted `import { randomUUID } from 'node:crypto';`. This shows project precedence for these three on that machine.
- **Not shown:** behaviour in an interactive session, and behaviour on a machine without a user-level install (there the twelve names must simply be listed).
- The agent list gives names and tools only, not the file a definition comes from. Asked to list "the agents defined in this project", the model declined for that reason; asked about the twelve names, it answered as above. The statements about which copy was loaded rest on the tool limits and the quoted text.

## Updating

Fetch the same paths at a newer revision, re-apply the `tools:` line to the eight reviewer roles, and update the revision and hashes in this file in the same commit.

## Local change: automatic delegation (2026-11-22)

One sentence beginning "Use proactively" was appended to the `description:` line of every Agency Agents role in `.claude/agents/` (not to `loop-verifier`). Claude Code uses that field to decide when to delegate, so the roles now run during ticket work without being named. Nothing else in the role files changed at that step.

This supersedes any statement above that a role file is unmodified or that the `tools:` line is the only local change. To compare a role with the pinned upstream file, remove that sentence (and the `tools:` line where one was added) first, and also the section described next.

A section headed "In this repository" was then inserted directly after the frontmatter of every Agency Agents role (not `loop-verifier`), before the upstream text, so that it is the first thing the subagent reads. It is project-specific text written for this repository, not upstream text, and the upstream hashes above do not cover it. It states the stack and the hard rules that bind the role, the files the role owns or reviews, the commands it runs or the evidence it must be given, a checklist that cites `CLAUDE.md`, `docs/architecture.md`, `docs/PRD.md` and the epic, the parts of the upstream text that do not apply here, and what the role hands back. The frontmatter and the upstream text below the section were not changed.

Comparing a role with the pinned upstream file therefore requires removing that section as well: delete from the heading `## In this repository` up to and including the line "This section and CLAUDE.md override the generic text below wherever they differ.", and one of the two blank lines around the section. With the section, the "Use proactively" sentence (and the full stop added before it in the four descriptions that had none upstream: Reality Checker, Backend Architect, Frontend Developer, API Tester) and the added `tools:` line removed, each of the eleven files matched its upstream SHA-256 in the table above (checked 2026-11-22).

When a role is updated from upstream (see "Updating"), re-insert its section and check it against the current `CLAUDE.md` and architecture notes.

The steps at which each role runs are in `.claude/skills/implement-ticket/SKILL.md`.

Verification, 2026-11-22: after the sections were inserted, this was run once from the repository root with Claude Code 2.1.323, headless:

```text
claude -p "List every project subagent defined in .claude/agents with its exact name and tools, say for each whether its instructions begin with a section titled In this repository, and say whether a skill named implement-ticket is available. Plain list, no commentary." --model haiku
```

The answer listed all twelve files in `.claude/agents/` with their `name:` values. It gave `Read, Grep, Glob` for the eight reviewer roles and `loop-verifier`, and no `tools:` line (all tools inherited) for Backend Architect, Frontend Developer and API Tester. It reported the "In this repository" section at the start of the eleven Agency Agents roles and not in `loop-verifier`, and the skill `implement-ticket` as available in the session's skill list. Not shown by this run: a launched subagent quoting its section, and behaviour in an interactive session.

## Local change: SDLC kit (2026-11-22)

This pass added, without changing any runtime code or product test: the review gate hook (`.claude/hooks/role_gate.py`) and `.claude/settings.json`; `.github/` (CI workflow, pull request template, CODEOWNERS, ticket template, Dependabot); `SECURITY.md`, `CHANGELOG.md` and `docs/RELEASING.md`; the `next-ticket` skill; the `ui-ux-pro-max` and `unslop` skills; `docs/ui-quality.md` and `docs/owner-decisions.md`. In the role files it added one checklist line naming `docs/ui-quality.md` to Code Reviewer, Frontend Developer and Accessibility Auditor (UI Designer and UX Architect are not installed here). No other text of the role files changed.
