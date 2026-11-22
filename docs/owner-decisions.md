# Owner decisions

Decisions the owner made for this repository on 2026-11-22. Changing any entry needs the owner. An agent that finds a decision blocking a ticket stops and says so.

Entry 11 of the owner's list (Rust is verified in CI only) does not apply: this repository has no Rust. The numbering below keeps the owner's numbers.

| # | Date | Decision | Implemented in |
|---|---|---|---|
| 1 | 2026-11-22 | The instructions, tooling and playbook live on the default branch (`main`), not on a preparation branch. | `CLAUDE.md`, `.claude/`, `.github/`, `docs/` as merged to `main` |
| 2 | 2026-11-22 | Persona agents run automatically during ticket work and carry instructions tailored to this project. | `.claude/agents/` ("In this repository" sections and "Use proactively" descriptions), `.claude/agency-agents/README.md` |
| 3 | 2026-11-22 | Every open ticket is about application implementation. Tooling is installed, not ticketed. | `.github/ISSUE_TEMPLATE/implementation-ticket.md`, epic #1 |
| 4 | 2026-11-22 | Agents may take a ticket up to a ready pull request. Only the owner merges and releases. | `.claude/skills/next-ticket/SKILL.md`, `.claude/skills/implement-ticket/SKILL.md`, `.claude/settings.json` (deny rules), `docs/RELEASING.md` |
| 5 | 2026-11-22 | No scheduler. Ticket work starts only on the owner's go signal (`/next-ticket`), because the repository is used to train AI models. | `.claude/skills/next-ticket/SKILL.md` (`disable-model-invocation: true`), `LOOP.md` |
| 6 | 2026-11-22 | A review gate hook blocks opening or readying a pull request until Code Reviewer and Reality Checker have run after the last code edit. | `.claude/hooks/role_gate.py`, `.claude/settings.json` (`hooks`), `.gitignore` (`.claude/state/`) |
| 7 | 2026-11-22 | Loop Engineering stays at L1: report-only and unscheduled. | `LOOP.md`, `loop-constraints.md` |
| 8 | 2026-11-22 | Continuous integration runs on Linux and Windows; the default branch requires a pull request and green checks. | `.github/workflows/ci.yml`; branch protection is set on GitHub by the owner's setup, not by a file |
| 9 | 2026-11-22 | Permission rules: documented commands are allowed; force pushes, pushes to the default branch, merges, releases and reads of secrets are denied; edits to CI, agent configuration and Loop files ask first. | `.claude/settings.json` (`permissions`) |
| 10 | 2026-11-22 | Open decisions on tickets are settled with the ticket's stated default. Listed below. | Epic #1, "Decisions shared by all tickets", item 10 |
| 12 | 2026-11-22 | The ten UI rules are binding. The `ui-ux-pro-max` and `unslop` skills are installed in the repository and used for UI work and for copy. | `docs/ui-quality.md`, `.claude/skills/ui-ux-pro-max/`, `.claude/skills/unslop/`, `.claude/skills/implement-ticket/SKILL.md` |

## Entry 10: decisions settled by a stated default

| Issue | Decision | Settled with |
|---|---|---|
| #1 (decision 10) | Where the offline queue lives | `localStorage` |
| #1 (decision 10) | How tabs learn about each other's edits | Polling of the operations feed (no long-poll, event stream or WebSocket) |
| #1 (decision 10) | Whether components nest | They do not nest |
| #1 (decision 10) | SVG import and transforms | Import rejects transforms |
| #1 (decision 10) | Pointer drag on the canvas | Not in this batch |
| #10 | Whether to add browser automation or CI in the release check | Neither is added by the ticket; the ticket states no default, so the conservative option applies (flag in issue). CI itself is installed by the tooling pass (entry 8). |

No other open owner decision with a missing default was found in the epic's children (#2 to #10) on 2026-11-22.
