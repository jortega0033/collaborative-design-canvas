## Ticket

Closes #

## What changed

<!-- One short paragraph. Name the files or modules. -->

## Evidence

<!-- Each command and its result, pasted from a real run. Include the test count before and after. -->

| Command | Result |
|---|---|
| `python -m unittest discover -s tests -t .` | |

## Agent roles run

<!-- Role, what it was asked, verdict. Code Reviewer and Reality Checker run on every ticket. -->

| Role | Asked to | Verdict |
|---|---|---|
| Code Reviewer | | |
| Reality Checker | | |

## Risks and rollback

<!-- What could go wrong, and how to undo this change. -->

## Checklist

- [ ] Each acceptance criterion maps to a test or a recorded manual step
- [ ] CI is green on this pull request
- [ ] `CHANGELOG.md` has a line under Unreleased
- [ ] UI changes checked against `docs/ui-quality.md`
- [ ] Copy, docs and this description passed the `unslop` skill
- [ ] No dependency, external URL or non-loopback listener added
