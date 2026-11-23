# CLAUDE.md

Working instructions for this repository. Read this file first, then the documents it links to. It does not repeat them.

## What this is

A local, offline workbench for arranging rectangle and text layers on a fixed 640 by 400 canvas. One Python package, standard library only, serving a JSON API and a static page on `127.0.0.1`, with one SQLite file as storage. M1 (single-user editing with a revision-guarded whole-document save) is implemented. DC-1 to DC-5 (undo, two-tab editing, components, auto-layout, SVG exchange) are planned and tracked in the epic, issue #1.

## Sources of truth

| Topic | Document |
|---|---|
| Product scope, milestones, contracts, fixture, acceptance matrix | [docs/PRD.md](docs/PRD.md) |
| How the code is built, the traced save workflow, the rules the code keeps, differences between the PRD and the code | [docs/architecture.md](docs/architecture.md) |
| Launch, smoke steps, limits, baseline verification | [README.md](README.md) |
| Backlog | Epic issue #1 and its sub-issues on GitHub, in dependency order: #2, #7, #8, #3, #9, #4, #5, #6, #10. The epic lists them with estimates and records the decisions shared by all tickets. |
| Loop setup and its limits | [LOOP.md](LOOP.md), [loop-constraints.md](loop-constraints.md) |
| Ticket playbook and the agent roles it runs | [.claude/skills/implement-ticket/SKILL.md](.claude/skills/implement-ticket/SKILL.md) and the section "Agent roles and ticket work" below |
| Delivery tooling, UI rules, owner decisions | [docs/ui-quality.md](docs/ui-quality.md), [docs/owner-decisions.md](docs/owner-decisions.md), section "Delivery workflow" below |
| Origin, licence and local changes of the role files | [.claude/agency-agents/README.md](.claude/agency-agents/README.md) |

When the PRD and the code disagree, the code is the baseline and [docs/architecture.md](docs/architecture.md) records the difference. A ticket that changes a contract updates PRD section 6 in the same pull request.

## Setup

Python 3.12 or newer. Nothing to install: there is no package manifest, no virtual environment requirement, no build step and no lint step. On Windows the interpreter is `python`; on Linux it is `python3`.

## Commands

Both were run during preparation on Windows 11 with Python 3.13.14, from the repository root.

Run the tests (68 tests, about 15 seconds):

```
python -m unittest discover -s tests -t .
```

Run the server (binds `127.0.0.1` only; both arguments are required; the data directory is created if missing; stop with Ctrl+C):

```
python -m design_canvas --data-dir ./data --port 8750
```

`--port 0` picks a free port and prints `Serving on http://127.0.0.1:<port>/`. Use it in scripts: on Windows a fixed port can be refused for a short time after the previous server stopped. `data/` and `*.sqlite*` are ignored by Git; use a scratch directory outside the repository for experiments and delete it afterwards.

Quick check that a running server answers:

```
curl -s http://127.0.0.1:8750/api/v1/health
```

Expected at the baseline: `{"status":"ok","api":1,"schema":1}`.

The `curl` lines here and in the issues are written for Git Bash or `cmd.exe`. In Windows PowerShell 5.1 `curl` is an alias of `Invoke-WebRequest` and `\"` quoting inside `-d` breaks: use `curl.exe` there and pass a JSON body from a UTF-8 file with `--data-binary @file`. `>` in PowerShell 5.1 writes UTF-16, so let the program write the file itself.

A single test: `python -m unittest tests.test_api.ConflictTest.test_concurrent_puts_same_base_revision`.

## Hard rules

These come from PRD sections 1, 3, 5 and 10. A change that breaks one needs the owner's approval first, not a pull request.

- Standard library only, in the application and in the tests. No pip or npm dependency, no build tooling, no CDN, font, image or script from another host.
- Loopback only. The server binds `127.0.0.1`. No CORS headers. No outgoing request from the server, the page or the tests.
- No sign-in, accounts, remote sync, paid services, media or model integration.
- Tests use a temporary directory and port 0. No fixed port, no real data directory, no `sleep` to wait for time to pass: a rule that depends on time takes an injected clock.
- User text reaches the page through `textContent`, form values and `fillText` only, never `innerHTML`. No inline script, style or event handler (the CSP forbids them and `tests/test_static_ui.py` checks).
- Static files are served from the fixed allowlist in `design_canvas/server.py`. Request input is never joined into a file path. A new static file is a new allowlist entry plus its tests.
- SQL is parameterised. Error responses use the envelope `{"error": {"code", "message"}}` and never contain a traceback.

## Architecture boundaries

Details and line references are in [docs/architecture.md](docs/architecture.md). The short form:

- `design_canvas/__main__.py`: command line only. Parses arguments, maps start-up failures to exit code 2.
- `design_canvas/server.py`: HTTP only. Routing, request guards (Host, Origin, body cap, media type, strict JSON), the error envelope, the static allowlist, security headers. It never runs SQL and never checks domain fields itself.
- `design_canvas/model.py`: pure domain rules. Constants, the fixture, strict validation. No I/O, no clock, no imports from `server` or `storage`.
- `design_canvas/storage.py`: SQLite only. Schema migrations by `PRAGMA user_version`, one connection behind a lock, every write inside one `BEGIN IMMEDIATE` transaction. It raises its own exceptions (`NotFound`, `TitleTaken`, `RevisionConflict`, `StorageError`); the server maps them to status codes.
- `design_canvas/static/`: one page, native JavaScript, no framework. It talks to the server through `/api/v1` only.
- `tests/`: `unittest`. `test_model.py` is pure, `test_storage.py` drives storage on a temporary directory, `test_api.py` drives a real server on port 0 over `http.client` and calls `main()`, `test_static_ui.py` checks the structure of the static files without a browser.

Keep new code on the correct side of these lines. A new pure module is the right place for a new set of rules (operations and their inverses, the layout function, the SVG sanitizer); `server.py` and `storage.py` call it.

Rules that every change must keep (the full table with tests is in [docs/architecture.md](docs/architecture.md), section 3):

- A write is all or nothing and succeeds only against the revision it names. `revision` and `updated_at` are set by the server.
- Layer ids are chosen by the client, unique per project and stable. Array order is z-order, index 0 is the back.
- Existing databases open under new code. A schema change is a new entry appended to `MIGRATIONS`, never an edit of an old one, with a test that opens a database made by the previous version. The health route and its test report the schema version and change with it.
- Every route checks Host; every route that is not `GET` or `HEAD` checks Origin, `Content-Length`, the body cap and the media type through the existing helpers.
- The M1 fixture and the whole-document `PUT` keep working exactly as PRD sections 6 and 7 describe.

## Git workflow

- `main` is the default branch. CI runs on pull requests (see "Delivery workflow"). Checks are also run locally and reported with their output.
- One branch per issue. The repository has no naming rule yet; `<issue-number>-<short-slug>` is the suggested form. Small commits with imperative subjects and a type prefix, as in the existing history (`feat:`, and by extension `fix:`, `docs:`, `test:`, `chore:`).
- Order: local checks, then Code Reviewer and Reality Checker on the full diff and the recorded local output, then a draft pull request that names the issue (`Part of #1`, `Closes #n`), then CI, then `gh pr ready` only when CI is green (do not poll: end the turn with "Draft pull request #N is waiting for CI" and read `gh pr checks` once when woken). Do not merge your own pull request and do not push to `main`.
- Never commit a data directory, a SQLite file, `.env*`, or `.prep/`.
- Do not change `.claude/agents/`, `LOOP.md`, `loop-constraints.md` or `loop-budget.md` as part of a feature ticket.

## Evidence before a ticket is called done

Items 1 to 5 and 7 to 9 are recorded locally and given to both gates before the draft pull request is opened; put them in the pull request description. Item 6 comes after the draft is open: CI runs on it, and the pull request is marked ready only when CI is green. Paste real output; do not summarise a run you did not make.

1. The full output tail of `python -m unittest discover -s tests -t .` from a clean checkout, with the Python version and the operating system. State the test count before and after the change (68 at the baseline). Name every baseline test whose expectation was changed on purpose.
2. For each acceptance criterion of the issue: the name of the test that proves it, or the exact manual step and what was observed.
3. For a schema change: the test that opens a database created by the previous schema version, the new `user_version`, and the health response.
4. For a new or changed route: one request and response pair per success and per error code, taken from a server started with `--port 0` on a scratch data directory, and the PRD section 6 diff.
5. For a change under `design_canvas/static/`: a browser run on `http://127.0.0.1:<port>/` with the browser name and version, the viewport sizes checked (800x600 and one width below 560 px), keyboard-only operation of the changed controls, and the console free of errors and of blocked or external requests. Browser checks are manual: the repository has no approved browser automation (PRD section 13).
6. CI green on the draft pull request, with the link to the run. This is a condition for marking the pull request ready, checked by the driver; Reality Checker does not judge it.
7. `git status` showing no stray files, and confirmation that no dependency, external URL or non-loopback listener was added.
8. Anything not verified, said plainly.
9. The section "Agent roles run", as described under "Agent roles and ticket work".

A step that needs a person (marked manual in the ticket) is done by the agent as far as it can, with the evidence, and the rest is listed under "Owner checks" in the pull request.

## Agent roles and ticket work

When asked to implement, continue or finish a GitHub issue, follow the playbook [`.claude/skills/implement-ticket/SKILL.md`](.claude/skills/implement-ticket/SKILL.md). Claude Code loads it on its own for ticket work; `/implement-ticket <issue number>` starts it by hand.

The roles are project-local subagents in `.claude/agents/`. Every role file except `loop-verifier.md` starts with a section "In this repository", written for this project: the constraints that bind the role, the files it owns or reviews, the commands it runs or the evidence it must be given, its checklist, and what it hands back. The text below that section is generic upstream text written for larger stacks; the section and this file override it. Sources, licence, local changes and the name collision with a user-level install are in [.claude/agency-agents/README.md](.claude/agency-agents/README.md).

Delegate to the roles without waiting to be asked. Each role's `description` ends with a "Use proactively ..." sentence, which is what makes Claude Code do so.

| When | Role | Runs when |
|---|---|---|
| Before coding | Codebase Onboarding Engineer | the ticket is in an unfamiliar area |
| Before coding | Software Architect | the ticket adds or changes a module boundary, data model, schema, API or dependency |
| While coding | Backend Architect, Frontend Developer | implementing server-side files, or files under `design_canvas/static/` |
| While coding | Database Optimizer, Realtime Collaboration Engineer | reviewing SQL and schema changes, or two-tab sync, patch order and conflict rules |
| After coding | Application Security Engineer, Accessibility Auditor, API Tester | the change touches untrusted input or request guards, the page, or a route or contract |
| Gate on every ticket | Code Reviewer, then Reality Checker | always: the review gate on the full diff, then the acceptance gate on the acceptance criteria and the evidence |

- Both gates run on every ticket, however small, after the local checks pass and before the draft pull request is opened. A ticket is not done until both pass and CI on the draft pull request is green.
- Backend Architect, Frontend Developer and API Tester can edit files and run commands. Every other role, `loop-verifier` included, is limited to `Read, Grep, Glob`: give it the diff, the acceptance criteria and the recorded command output.
- The session or role that wrote a change does not count as its reviewer.
- List each role that ran, what it was asked and its verdict in the pull request description under "Agent roles run".

## Delivery workflow

How a ticket gets from the backlog to the owner. Each piece is described in its own file; this part only links them.

- **Start and playbook.** The owner starts a run with `/next-ticket` ([skill](.claude/skills/next-ticket/SKILL.md)); that is the go signal for one leaf ticket (a `tracking` ticket or one with open sub-issues is never picked; the last sub-issue's pull request also closes the parent). The reviewers get the diff and evidence as files under `.claude/state/review/`. The work follows [implement-ticket](.claude/skills/implement-ticket/SKILL.md). Ticket labels: `status:ready`, `status:blocked`, `status:in-progress`, `needs-decision`.
- **Review gate hook.** [`.claude/hooks/role_gate.py`](.claude/hooks/role_gate.py) blocks `gh pr create` and `gh pr ready` until Code Reviewer and Reality Checker ran after the last code edit, so the draft is opened only after both gates and the pull request is marked ready only after both gates ran again on the final code. `ROLE_GATE=off` in the environment Claude Code is started from switches it off for that session; only the owner does that.
- **Permission rules.** [`.claude/settings.json`](.claude/settings.json): documented commands are allowed, merges, force pushes, pushes to `main` and releases are denied, edits to CI, agent configuration and Loop files ask first.
- **CI.** [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs the suite and the hook self-test on Linux and Windows. It runs on the draft pull request, and the pull request is marked ready only when it is green.
- **Pull request.** Use the [template](.github/pull_request_template.md). Add one line to [CHANGELOG.md](CHANGELOG.md) under Unreleased.
- **UI and copy.** [docs/ui-quality.md](docs/ui-quality.md) holds the ten UI rules; UI tickets start with the `ui-ux-pro-max` skill and copy goes through `unslop` before the pull request. Colours come from the Pipenzo tokens in `design_canvas/static/tokens.css` ([docs/design-tokens.md](docs/design-tokens.md)): new UI uses them and adds no colour literals.
- **Owner only.** Merging and releasing ([docs/RELEASING.md](docs/RELEASING.md)). Decisions behind all of this: [docs/owner-decisions.md](docs/owner-decisions.md). Security reports: [SECURITY.md](SECURITY.md).

## Loop

Issue triage runs at L1: report-only, started by hand, no scheduler, no GitHub writes. See [LOOP.md](LOOP.md).
