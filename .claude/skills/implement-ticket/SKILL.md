---
name: implement-ticket
description: Playbook for implementing a GitHub issue in this repository from start to pull request, with the project subagents run at fixed steps. Use whenever asked to implement, start, continue or finish a ticket, an issue or an epic child, for example "implement #12" or "work on the next ticket".
argument-hint: "[issue number]"
---

# Implement a ticket

Use this playbook for every implementation ticket in this repository. `CLAUDE.md` holds the commands, the architecture boundaries, the Git workflow and the evidence rules; where this playbook and `CLAUDE.md` differ, `CLAUDE.md` wins.

The project subagents in `.claude/agents/` are part of the work. Delegate to them at the steps below without waiting to be asked. If a step names a role that is not installed, do that step yourself and say so in the pull request.

## Steps

1. **Read the ticket.** Work only on a leaf ticket: one labelled `tracking`, or with open sub-issues, is a container, so take its first open sub-issue instead; the pull request of a parent's last open sub-issue also says `Closes #<parent>`. Do not change agent configuration (`.claude/agents`, `skills`, `hooks`, `settings.json`) in a ticket, by any tool. `gh issue view <number>` and the epic it belongs to. Check that every prerequisite issue is closed and that no owner decision named in the ticket is still open. If the ticket is blocked, stop and say what blocks it.
2. **Read the rules.** `CLAUDE.md`, then the architecture notes it links to. For a ticket that changes the page, run the `ui-ux-pro-max` skill now (design-system search for the product type) and read `docs/ui-quality.md`.
3. **Orient and check the approach.** Delegate as the table "Before coding" says. Settle open design questions before writing code.
4. **Branch** as the Git workflow in `CLAUDE.md` says. Never work on the default branch.
5. **Implement** inside the ticket's stated scope. Delegate the work to the implementing role that matches the files being changed (table "While coding"). Do not widen scope; note anything else you find as a follow-up.
6. **Test.** Add or change tests for every acceptance criterion and material edge case, then run the checks listed in `CLAUDE.md`. Record each command and its result.
7. **Specialist review.** Run every role in the table "After coding" whose trigger matches the change.
8. **Check the UI.** For a UI ticket, check the changed screens against `docs/ui-quality.md` and record the result.
9. **Write it up.** Run the `unslop` skill on user-facing copy, documentation and the pull request text. Add one line to `CHANGELOG.md` under Unreleased.
10. **Review gate, always.** Write the diff and the local evidence to `.claude/state/review/` in the ticket worktree first (`git diff --stat origin/main...HEAD`, `git diff origin/main...HEAD`, the check outputs) and name those files in each request, because the reviewers have no shell. Run Code Reviewer on the full final diff. Fix every material finding, re-run the local checks, and have the reviewer look again until no material finding is left. Run it only after the local checks pass.
11. **Acceptance gate, always.** Run Reality Checker with the ticket's acceptance criteria and the recorded local evidence. It checks that the documented checks ran locally and passed and that CI is configured to run them; it does not confirm a CI result, because CI runs only on the draft pull request opened afterwards. Do not open the pull request unless it passes. A criterion that needs a person (marked manual in the ticket) is done as far as an agent can, with the evidence, and the rest is listed under "Owner checks" in the pull request; Reality Checker accepts that only when the ticket marks the step as manual.
12. **Hand off.** Capture the evidence `CLAUDE.md` asks for and open a draft pull request from the template in `.github/pull_request_template.md`, naming the issue, only after both gates passed on the final code. Do not poll for CI: end the turn with the line "Draft pull request #N is waiting for CI" and, when woken, read `gh pr checks` once. If CI fails, fix, re-run the local checks and both gates, and push. When CI is green, mark the pull request ready and comment on the issue with the CI run link. Never open or mark ready a pull request with a gate not run. Only the owner merges; do not merge.

## Roles

### Before coding

| Role | Access | Delegate to it |
|---|---|---|
| Codebase Onboarding Engineer | read-only reviewer | At the start of a ticket in an unfamiliar area, to trace the relevant code paths before anything is changed |
| Software Architect | read-only reviewer | Before implementing a ticket that adds or changes a module boundary, data model, storage schema, public API or dependency, to check the approach against the architecture notes |

### While coding

| Role | Access | Delegate to it |
|---|---|---|
| Backend Architect | can edit | When a ticket changes server-side code, HTTP routes, validation, persistence or data migrations |
| Database Optimizer | read-only reviewer | When a ticket changes SQL, the schema, indexes or query paths |
| Frontend Developer | can edit | When a ticket changes browser-side code such as pages, components, client state, styling or keyboard interaction |
| Realtime Collaboration Engineer | read-only reviewer | When a ticket touches multi-tab or multi-editor sync, patch ordering or conflict rules |

### After coding

| Role | Access | Delegate to it |
|---|---|---|
| Application Security Engineer | read-only reviewer | After a ticket touches input parsing, file upload or import, sanitization, origin and host checks, or any handling of untrusted data |
| Accessibility Auditor | read-only reviewer | After a ticket changes user-facing UI, keyboard handling, focus order or markup |
| API Tester | can edit | After a ticket adds or changes an HTTP endpoint, status code or request and response contract |

### Gates that run on every ticket

| Role | Access | Delegate to it |
|---|---|---|
| Code Reviewer | read-only reviewer | After implementing or changing code for a ticket, after the local checks pass and before the draft pull request is opened |
| Reality Checker | read-only reviewer | As the acceptance gate of every ticket, to check each acceptance criterion against the local evidence that was actually produced, after Code Reviewer and before the draft pull request is opened; it does not judge CI |

## Rules

- The session or role that wrote a change does not count as its reviewer.
- Read-only reviewers cannot run commands. Give them the diff, the acceptance criteria and the recorded command output.
- Where a role's general advice (frameworks, dependencies, cloud services) conflicts with `CLAUDE.md`, `CLAUDE.md` wins.
- In the pull request description, add a section "Agent roles run" listing each role that ran, what it was asked and its verdict, and any step you did yourself because a role was missing.
