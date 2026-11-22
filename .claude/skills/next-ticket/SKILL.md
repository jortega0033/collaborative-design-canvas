---
name: next-ticket
description: Take the next ready ticket of epic #1 to a ready pull request. Started only by the owner; starting it is the go signal.
argument-hint: "[issue number]"
disable-model-invocation: true
---

# Next ticket

The owner starts this with `/next-ticket` or `/next-ticket <issue number>`. Starting it is the go signal for exactly one ticket. It never merges, never releases, and never starts another run by itself.

`CLAUDE.md` holds the rules, the commands and the evidence list. [`implement-ticket`](../implement-ticket/SKILL.md) is the playbook for the work itself.

## Labels

`status:ready`, `status:blocked`, `status:in-progress`, `needs-decision`. Epic: #1. Dependency order of its children: #2, #7, #8, #3, #9, #4, #5, #6, #10.

## Steps

1. **Refresh the queue.** `gh issue list --state open --limit 100` and `gh issue view` for the epic's children. A `status:blocked` ticket whose prerequisites (the "Depends on" column of the epic table) are all closed becomes `status:ready` (`gh issue edit <n> --add-label status:ready --remove-label status:blocked`).
2. **Pick.** With an argument, take that issue if it is `status:ready`; otherwise stop and say why. Without one, take the first `status:ready` ticket in the epic's dependency order that is not `status:in-progress` and not `needs-decision`. If there is none, report that and stop.
3. **Claim.** Add `status:in-progress` to the ticket.
4. **Worktree and branch.** From the default branch (`main`, up to date) create a fresh worktree and a branch named `<issue-number>-<short-slug>`: `git worktree add ../collaborative-design-canvas-<number> -b <number>-<short-slug> main`. Work only there. Never work on `main`.
5. **Implement.** Run the `implement-ticket` playbook on the ticket, including both gates (Code Reviewer, then Reality Checker). Do not widen scope.
6. **Open the pull request.** Use the pull request template and the evidence list in `CLAUDE.md`. Add the `CHANGELOG.md` line. Open it as a draft that names the issue (`Closes #<n>`, `Part of #1`).
7. **CI.** Watch `gh pr checks`. Fix failures inside the ticket's scope. When the gates have passed and CI is green, mark the pull request ready (`gh pr ready`) and comment on the issue with the pull request link and a one-paragraph summary.
8. **Stop.** Report the pull request link and anything not verified. Leave the merge, the label cleanup after merge and the next ticket to the owner.

## Stop conditions

An open owner decision with no stated default, a ticket whose prerequisite is open, a change that needs approval under the "Hard rules" in `CLAUDE.md`, or a failing gate that the ticket's scope cannot fix: stop, comment on the issue, and report. Do not guess.
