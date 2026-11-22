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

`status:ready`, `status:blocked`, `status:in-progress`, `needs-decision`, `tracking`. Epic: #1 (a container, never picked). Order of its children: #2, #7, #8, #3, #9, #4, #5, #6, #13, #10. If a child has sub-issues, they come right after that parent, in the order of `gh api repos/jortega0033/collaborative-design-canvas/issues/<n>/sub_issues`.

## Steps

1. **Refresh the queue.** `gh issue list --state open --limit 100` and `gh issue view` for the epic's children. A `status:blocked` ticket whose prerequisites (the "Depends on" column of the epic table) are all closed becomes `status:ready` (`gh issue edit <n> --add-label status:ready --remove-label status:blocked`). A parent (an issue labelled `tracking`, or one with at least one sub-issue) whose sub-issues are all closed is closed with a comment that names them. An issue with no sub-issues is never closed by this step.
2. **Pick a leaf.** A ticket labelled `tracking`, or with open sub-issues, is a container and is never picked. With an argument, take that issue if it is a leaf and `status:ready`; a `tracking` number or one with open sub-issues is refused with the list of its open sub-issues; any other non-ready issue stops the run with the reason. Without an argument, take the first `status:ready` leaf in the order above that is not `status:in-progress` and not `needs-decision`. If there is none, report that and stop.
3. **Claim.** Add `status:in-progress` to the ticket.
4. **Worktree and branch.** From the default branch (`main`, up to date) create a fresh worktree and a branch named `<issue-number>-<short-slug>`: `git worktree add ../collaborative-design-canvas-<number> -b <number>-<short-slug> main`. Work only there. Never work on `main`.
5. **Implement.** Run the `implement-ticket` playbook on the ticket, including the local checks. Do not widen scope. A criterion that needs a person (marked manual in the ticket) is done as far as an agent can, with the evidence; the rest goes under "Owner checks" in the pull request.
6. **Gates.** Before calling Code Reviewer and Reality Checker (they have no shell), write `git diff --stat origin/main...HEAD`, `git diff origin/main...HEAD` and the outputs of the local checks to `.claude/state/review/` in the ticket worktree and name those files in each request. Run Code Reviewer, then Reality Checker, both before any pull request exists.
7. **Open the pull request.** Use the pull request template and the evidence list in `CLAUDE.md`. Add the `CHANGELOG.md` line. Only after both gates passed, `git push -u origin <branch>` and `gh pr create --draft` with `Closes #<n>` and `Part of #1`. If this is the last open sub-issue of a parent, also write `Closes #<parent>`.
8. **Wait for CI without polling.** Bind the pull request to the session if the app offers it (the pull request tools of the desktop app), then end the turn with the line "Draft pull request #N is waiting for CI". Do not loop, sleep or watch. When the session is woken (a CI event, or the owner says "continue"), read `gh pr checks <N>` once. Red: fix inside the ticket's scope, re-run the local checks and both gates, push, and end the turn with the same line. Still running: end the turn with the same line. Green: `gh pr ready <N>` and comment on the issue with the pull request link, the CI run link and a one-paragraph summary.
9. **Stop.** Report the pull request link and anything not verified. Leave the merge, the label cleanup after merge and the next ticket to the owner.

## Stop conditions

An open owner decision with no stated default, a ticket whose prerequisite is open, a change that needs approval under the "Hard rules" in `CLAUDE.md`, or a failing gate that the ticket's scope cannot fix: stop, comment on the issue, and report. Do not guess.
