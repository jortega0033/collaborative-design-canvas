# Loop Configuration: Issue Triage

Scaffolded with `npx --yes @cobusgreyling/loop@0.2.0 init . --pattern issue-triage --tool claude` ([Loop Engineering](https://github.com/cobusgreyling/loop-engineering), MIT). The generated `.grok/` and `.codex/` variants were removed; this repository uses the Claude Code files only. The scaffold generated no workflow file, and none was added.

## Active Loops

| Pattern | Cadence | Status | Command |
|---------|---------|--------|---------|
| Issue Triage | Manual, on request | L1 report-only | `/issue-triage` in a Claude Code session at the repository root |

## Operating level: L1 report-only

- The loop reads open issues with `gh issue list` and `gh issue view` and rewrites `issue-triage-state.md`. That file and `loop-run-log.md` are the only files it may change.
- It never applies labels, comments, closes or edits issues, edits source or tests, commits, pushes, opens pull requests or merges.
- No scheduler is configured. Do not wrap the skill in `/loop`, a cron entry, a scheduled task or a GitHub workflow. The "2h" cadence in the generated skill text describes the upstream pattern, not this repository.
- `loop doctor` prints its own readiness score. That score describes the scaffold, not the operating level. The operating level here stays L1 until the owner changes this file.

## Ticket work is not a loop run

Implementing a ticket is not a loop run. The owner starts it with `/next-ticket`, and it is governed by `CLAUDE.md`, the `implement-ticket` playbook, the review gate hook, CI and branch protection. The loop stays report-only and unscheduled at L1.

## Next manual triage run

From the repository root, in a new Claude Code session:

```text
/loop-constraints
/issue-triage
```

Headless equivalent:

```text
claude -p "Run the loop-constraints skill, then the issue-triage skill in L1 report-only mode. Update issue-triage-state.md and append one entry to loop-run-log.md. Make no GitHub writes and change no other file."
```

Review the diff of `issue-triage-state.md` afterwards. Committing it is a human decision.

## Health checks

```text
npx --yes @cobusgreyling/loop@0.2.0 doctor .
npx --yes @cobusgreyling/loop@0.2.0 status .
```

Doctor exit codes: 0 healthy, 1 warnings, 2 blocked.

## Human Gates

- Priority assignment (P0, P1): human only.
- Anything touching the request guards in `design_canvas/server.py` (loopback bind, Host and Origin checks, the body cap, the CSP and the other security headers, the static allowlist), the SQLite schema or its migrations in `design_canvas/storage.py`, the revision-guarded save transaction, input validation in `design_canvas/model.py`, or the public JSON API under `/api/v1`: always escalate.
- Anything about parsing files from outside (the planned SVG import): always escalate.
- Anything that would add a dependency, an external request or a non-loopback listener: always escalate. The product is offline by design ([docs/PRD.md](docs/PRD.md), sections 1, 3 and 10).
- Duplicate closure: human confirms.
- Stale issue closure: human confirms.
- Any change to this file, `loop-budget.md` or `loop-constraints.md`: human only.

## Verifier

`.claude/agents/loop-verifier.md` is the checker for a later maker/checker level. It is limited to `Read, Grep, Glob`, so it cannot run the tests itself and must answer `ESCALATE_HUMAN` when a verdict depends on a test run. It has no role at L1 because the loop proposes no changes.

## Budget

- Sub-agent spawns per run: 0 at L1.
- See `loop-budget.md`.

## MCP

MCP is not required for this pattern. The triage skill reads issues through the `gh` command line.

## Doctor suggestions that were not adopted

On 2026-11-22 `loop doctor` reported `HEALTHY (exit 0)` and suggested a `docs/safety.md`, issue and pull request templates with workflows, and worktree isolation notes. They were left out on purpose: the denylists and merge policy are in `loop-constraints.md`, a workflow would be the scheduler that L1 excludes, and an L1 run changes two state files only, so it needs no worktree. Doctor also printed "Could not parse loop-sync JSON output" and `Sync: n/a`; no sync is configured here.

## Links

- Pattern: https://github.com/cobusgreyling/loop-engineering/blob/main/patterns/issue-triage.md
- Repository instructions: [CLAUDE.md](CLAUDE.md)
- Backlog source of truth: [docs/PRD.md](docs/PRD.md) and the epic issue (#1)
