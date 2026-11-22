# Architecture and PRD reconciliation

This file records how the code is built today, one workflow traced from the command line to the database, the rules the code keeps, and where the PRD, the README, the backlog and the code differ. The product definition is [PRD.md](PRD.md); this file does not repeat it.

Line references are to commit `25aaa28` (the M1 baseline). Marks used below:

- **Implemented**: present in the code at that commit.
- **Planned**: described in the PRD or an issue, no code yet.
- **Needs verification**: claimed or expected, not reproduced during preparation.
- **Run**: observed during preparation on Windows 11 with Python 3.13.14 (2026-11-22). **Read**: taken from the source only.

## 1. Shape of the system

One Python process, standard library only. It serves a JSON API and three static files on `127.0.0.1` and stores everything in one SQLite file.

| Part | File | Job | Must not do |
|---|---|---|---|
| Command line | `design_canvas/__main__.py` | Parse `--data-dir` and `--port` (both required), open storage, start the server, map start-up failures to exit code 2 | Contain request or storage logic |
| HTTP | `design_canvas/server.py` | Routing, request guards (Host, Origin, body cap, media type, strict JSON), error envelope, static allowlist, security headers | Run SQL, validate domain fields |
| Domain | `design_canvas/model.py` | Constants, the fixture, strict validation that returns normalised values or raises `ValidationError` | Import `server` or `storage`, read the clock, touch files |
| Storage | `design_canvas/storage.py` | Schema migrations, transactions, queries; raises `NotFound`, `TitleTaken`, `RevisionConflict`, `StorageError` | Touch HTTP objects, validate request shape |
| Page | `design_canvas/static/index.html`, `app.js`, `styles.css` | One page, one script (an IIFE with a single `state` object), Canvas2D preview | Use inline script or style, `innerHTML`, external URLs |
| Tests | `tests/` | `unittest`: `test_model.py` (pure), `test_storage.py` (temporary directory), `test_api.py` (real server on port 0 over `http.client`, plus `main()`), `test_static_ui.py` (structure of the static files, no browser) | Use a fixed port, the network, or a real data directory |

Imports run one way: `__main__` imports `server` and `storage`; `server` imports `model` and the three storage exceptions (`server.py:13-14`); `storage` imports only `model.SCENE` (`storage.py:10`); `model` imports nothing from the package.

There is no package manifest, build step, lint step or CI.

## 2. Traced workflow: create the fixture, change X, save, restart, reopen

This is PRD section 7 and rows 3 to 5 of the acceptance matrix in PRD section 11.

1. **Start.** `main()` (`__main__.py:20-48`) builds `Storage(args.data_dir)` (`:28`). `Storage.__init__` (`storage.py:72-100`) rejects an empty path or a path that is a file, creates the directory, opens `design_canvas.sqlite3` with `isolation_level=None`, sets `busy_timeout` and `foreign_keys`, and runs `_migrate()` (`storage.py:108-125`), which applies the missing entries of `MIGRATIONS` inside one `BEGIN IMMEDIATE` transaction and refuses a database whose `user_version` is higher than the code knows. `CanvasServer(storage, port)` binds `127.0.0.1` (`server.py:292-296`). The address is printed (`__main__.py:40`) and `serve_forever()` runs until Ctrl+C; `server_close()` then joins the request threads (`server.py:311-317`).
2. **Create.** The page's "Load fixture" button (`app.js:491`) calls `createProject(true)` (`app.js:165-197`), which sends `POST /api/v1/projects` with `{"title", "fixture": true}`. Every request first passes `_check_host_origin` (`server.py:143-152`, called from `_dispatch` at `:200`). `_read_json` (`server.py:154-180`) enforces `Content-Length`, the 262144 byte cap, `application/json`, and rejects duplicate keys and `NaN`/`Infinity`. `_api` (`server.py:227-238`) validates with `model.validate_create` (`model.py:156-169`), takes `model.fixture_layers()` (`model.py:32-40`) and calls `Storage.create_project` (`storage.py:205-215`): one transaction inserts the project row at revision 1 and the layer rows, then reads the project back. A unique violation on `title_key` becomes `TitleTaken`, which the server returns as 409 `title_taken`.
3. **Edit.** Typing in the X field fires `bindNumber`'s `input` listener (`app.js:429-447`). It changes the layer object in `state.layers` and redraws (`changed()`, `app.js:423-427`; `draw()`, `app.js:382-419`). Nothing is sent. `isDirty()` (`app.js:52`) compares a JSON snapshot of title and layers with the one taken at the last load or save.
4. **Save.** `save()` (`app.js:199-234`) sends `PUT /api/v1/projects/{id}` with `{title, base_revision, layers}`. The server validates with `model.validate_update` (`model.py:172-187`) and calls `Storage.update_project` (`storage.py:217-234`): `UPDATE projects SET ... revision = revision + 1 ... WHERE id = ? AND revision = ?`; when no row matched it raises `NotFound` or `RevisionConflict(current)`; otherwise it deletes all layer rows of the project and inserts the new list with positions 0 to n-1. The server maps `RevisionConflict` to 409 `revision_conflict` with the current project in `error.current` (`server.py:252-256`). The page keeps the local edits on a 409, stores the server copy in `state.conflict` and shows "Reload server version" (`app.js:219-224`).
5. **Restart and reopen.** The page stores only the last project id in `localStorage` under `dc.lastProject` (`app.js:59-66`). On load it lists projects and opens that id (`app.js:552-559`). `GET /api/v1/projects/{id}` runs `Storage._load` (`storage.py:163-181`), which orders layers by `position`.

**Run** (saved outputs are listed in the preparation report, not in this repository):

- `python -m unittest discover -s tests -t .`: `Ran 68 tests in 15.341s`, `OK`.
- Server started with `--port 0` on a scratch directory: health 200 `{"status": "ok", "api": 1, "schema": 1}`; `GET /`, `/app.js`, `/styles.css` 200; fixture `POST` 201 at revision 1; `PUT` with `rect-1` x=80 on base revision 1 gave 200 at revision 2; the same `PUT` again on base revision 1 gave 409 `revision_conflict` with `current.revision` 2 and x still 80; a second title `STATION` gave 409 `title_taken`; a 262145 byte body gave 413; a foreign `Origin` on `POST` and a foreign `Host` on `GET` gave 403 `forbidden_origin`; `/../x`, `/%2e%2e/` and `/static/app.js` gave 404; x=2001 gave 422 with a field message.
- The server process was stopped and started again on the same directory: `GET` returned revision 2 with `rect-1` at x=80, y=60, w=120, h=72 at index 0 and `text-1` at index 1.
- `--data-dir` pointing at a file exited with code 2 and one line on stderr.
- Chrome 157 headless, one page load at 800x600 (`--dump-dom`): the page rendered under its CSP, `app.js` ran (status text "Ready. Enter a title and create a canvas, or open one from the list."), and the project list showed the project fetched from `/api/v1/projects`.

**Needs verification** (not reproduced during preparation): every click and keyboard path in the page (README smoke steps 2 to 7), canvas drawing, the two-tab stale-save step in a browser, the 800x600 layout, contrast and focus order, and anything on Python 3.12 or Linux. The README reports a Chrome 157 run and a Python 3.12.3 run on Ubuntu; those are the owner's records.

## 3. Rules the code keeps

Every change must keep these. Each has a baseline test.

| Rule | Where | Test |
|---|---|---|
| The server binds `127.0.0.1` only; `Host` must be `127.0.0.1:<port>` or `localhost:<port>`; a request that is not `GET` or `HEAD` with a foreign `Origin` is refused; no CORS header is ever sent | `server.py:136-152`, `:296` | `tests/test_api.py` `OriginTest`, `BasicsTest.test_health_and_security_headers` |
| Request bodies are capped at 262144 bytes, need `Content-Length` and `application/json`; duplicate JSON keys and non-finite numbers are rejected | `server.py:154-180` | `ValidationTest` |
| Static files come from a fixed dictionary of four paths; no part of the request path is used to build a file path | `server.py:21-29`, `:207-220` | `StaticTest` |
| Every response carries the CSP (`default-src 'self'; style-src 'self'; script-src 'self'; base-uri 'none'; form-action 'none'`), `nosniff` and `no-store` | `server.py:31-37`, `:82-97` | `BasicsTest`, `StaticTest` |
| Errors use the envelope `{"error": {"code", "message", ...}}`; a 500 never carries a traceback | `server.py:103-115`, `:193-195` | `BasicsTest.test_not_found_and_method_not_allowed`, `ValidationTest` |
| Validation is strict: exact types (`bool` and `float` are not integers), unknown fields rejected, at most 200 layers, unique layer ids, control characters refused | `model.py:43-140` | `tests/test_model.py` |
| A layer leaves the validator and the database with the key order `id, type, label, x, y, w, h, [text, font_size,] fill` | `model.py:114-119`, `storage.py:173-179` | `LayerTest.test_canonical_key_order` |
| A save is all or nothing and succeeds only on the current revision; with eight simultaneous saves on one base revision exactly one wins | `storage.py:217-234`, `:133-146` | `ConflictTest`, `ProjectTest` |
| `revision` and `updated_at` are set by the server; layer ids are chosen by the client and are stable | `storage.py:208-210`, `:221-224`; `model.py:19` | `PersistenceTest` |
| Titles are unique ignoring case | `storage.py:20`, `:67-68` | `ProjectTest.test_title_unique_case_insensitive` |
| The schema changes only by appending to `MIGRATIONS`; a database from a newer version is refused with exit code 2 | `storage.py:15-42`, `:108-125` | `SchemaTest`, `CliTest.test_newer_schema_exits_2` |
| Text reaches the page through `textContent` and `fillText` only; no inline script, style or event handler; no external URL in the static files | `app.js` throughout | `tests/test_static_ui.py` |

Data ownership: SQLite is the only durable state. The page holds a working copy (`state.layers`), the last server copy (`state.project`) and, after a 409, the server's newer copy (`state.conflict`) (`app.js:39-48`). Layer `x` and `y` may lie outside the 640 by 400 scene (range -2000 to 2000, `model.py:100-101`); the scene size is a constant (`model.py:10`).

Concurrency model: one SQLite connection shared by all request threads behind an `RLock`; every write runs in `BEGIN IMMEDIATE` and rolls back on any exception (`storage.py:133-146`). The handler speaks HTTP/1.0, one request per connection, with a 10 second socket timeout (`server.py:71-72`).

## 4. What a new feature has to change

These are facts about the baseline that the planned tickets run into. They are not defects.

- **Edits are local until Save.** The page sends nothing between saves, and a save replaces the whole layer list (`storage.py:232-233`). There is no record of individual edits anywhere. Undo, patches and conflict records all need new tables and new routes.
- **The layer type list is closed in three places:** `model.LAYER_TYPES` (`model.py:18`), the `CHECK (type IN ('rect', 'text'))` constraint on `layers` (`storage.py:28`) and the two branches of `draw()` (`app.js:390-404`). SQLite cannot alter a `CHECK` constraint, so a new layer type needs a migration that rebuilds the `layers` table.
- **Migrations have never been exercised beyond version 1.** `MIGRATIONS` has one entry. The first ticket that adds a second entry also needs the first test that opens a database created at version 1.
- **The health route reports the schema version as a literal.** `server.py:226` returns `"schema": 1` and `tests/test_api.py:99` asserts it. `SchemaTest.test_pragmas_and_version` (`tests/test_storage.py:25-31`) asserts `user_version` 1. A schema change updates all three on purpose.
- **The page is one script.** `tests/test_static_ui.py:139-148` requires every `<script>` to have `src="/app.js"`, `test_files_exist` and `test_no_external_urls` name the three files, and the static allowlist has four entries. A second script or stylesheet means changing the allowlist and these tests in the same pull request.
- **Number fields change the model on every keystroke** (`input` event, `app.js:430`). A feature that records one operation per edit has to pick a commit point (for example the `change` event).
- **`window.confirm` guards discarding unsaved edits** (`app.js:130`, `:175`). A headless or scripted browser check stops there unless it handles the dialog.
- **Time comes from the system clock** (`storage._now`, `storage.py:63-64`) and nothing takes a clock as a parameter. A feature with a time rule (the planned 30 second gap) needs an injected clock so that tests do not sleep.
- **Port reuse on Windows.** `allow_reuse_address` is off on Windows (`server.py:289`). Restarting on the same fixed port immediately after a stop can fail; use `--port 0` in scripts.

## 5. PRD capabilities against the code

| Capability (PRD section 2) | Status | Evidence |
|---|---|---|
| M1: title, 640 by 400 scene, rect and text layers (add, select, move, resize, reorder, delete) | Implemented. API and storage: Run. Page controls: Read, browser use needs verification | `app.js:253-312`, `index.html:41-93` |
| M1: Canvas2D preview | Implemented, Read. Drawing needs verification in a browser | `app.js:382-419` |
| M1: named SQLite projects, project list | Implemented, Run | `storage.py:185-215` |
| M1: revision-guarded save, 409 with the current project | Implemented, Run | `storage.py:217-234`, `server.py:243-257` |
| M1: API contract and error codes (PRD section 6) | Implemented, Run for the routes and codes listed in section 2 above | `server.py:222-262` |
| M1: request guards and static allowlist (PRD section 10) | Implemented, Run | `server.py:136-180`, `:207-220` |
| M1: responsiveness and accessibility (PRD section 8) | Implemented in markup and CSS, Read. Needs verification in a browser | `index.html`, `styles.css:40-69`, `:139-142` |
| DC-1: reversible operation log, keyboard command list | Planned. No operation table, no undo route; the only shortcut is Ctrl/Cmd+S (`app.js:538-543`) | Issue #2 |
| DC-2: two-tab collaboration, ordered offline patches, per-field conflicts | Planned. The only write is the whole-document `PUT`; the page has no client id, queue or polling | Issue #3 |
| DC-3: components and instance overrides | Planned. Layer types are `rect` and `text` only | Issue #4 |
| DC-4: auto-layout stack | Planned. No frame type or layout code | Issue #5 |
| DC-5: sanitized vector exchange | Planned. No SVG or XML code | Issue #6 |

## 6. Differences between the PRD, the README, the backlog and the code

Numbered so that issues can cite them. "Batch decision" means the epic (issue #1) settles the point for the planned tickets; the PRD text still has to be updated by the ticket named.

| # | Difference | Effect | Where it is handled |
|---|---|---|---|
| D1 | PRD section 6 says the contract "mirrors the build contract" and that element ids are "as in the build contract". That document is not in the repository (it lives in the ignored `.prep/` directory). | The element ids are fixed only by `tests/test_static_ui.py:9-30`. A reader of the PRD cannot find them. | Release check ticket: list the ids in PRD section 6 or point to the test |
| D2 | The health route's `"schema": 1` is a literal, not `storage.SCHEMA_VERSION` (`server.py:226`). | After the first migration the route would report the wrong version. | Issue #2 (first schema change) |
| D3 | "Canonical scene JSON" is required by DC-1 and DC-5 and by the epic ("byte-identically") but is defined nowhere. Issue #2 says "sorted keys, layers in z-order"; the API emits contract key order with default `json.dumps` escaping (`server.py:100`). | Byte equality cannot be tested until one function defines the bytes. | Issue #2 defines it; later tickets reuse it |
| D4 | PRD section 14 lists the offline queue storage and "polling interval vs. long-poll" as open. Issue #3 already says `localStorage` queue and polling. | The PRD and the issue disagree on whether these are decided. | Batch decision: `localStorage` and polling. Issue #3 updates PRD section 14 |
| D5 | README "Limits" says saves are explicit and whole-project. DC-1 and DC-2 need one recorded operation per edit. Nothing says what the Save button and the "unsaved changes" state mean afterwards. | Two engineers could build incompatible edit paths. | Batch decision in the epic: layer edits become operations sent when committed; the whole-document `PUT` stays for the title and as a logged `replace` |
| D6 | DC-5 depends on DC-1 and DC-3 (PRD section 3, issue #6). How a frame from DC-4 is exported is not stated anywhere. | Export of a scene with a frame is undefined. | Batch decision: the SVG ticket runs after the auto-layout ticket and defines it |
| D7 | PRD section 9 says that after a 409 the user "may press Save again after Reload server version and re-applying". "Reload server version" replaces the local edits with the server copy (`app.js:236-243`); there is no merge. | Wording only; the behaviour matches README smoke step 7. | Release check ticket |
| D8 | PRD section 8 says "at least 900 px three columns, below that stacked". The CSS has three layouts: three columns from 900 px, stage above two columns from 560 to 899 px, one column below 560 px (`styles.css:40-69`). | Wording only. | Release check ticket |
| D9 | PRD section 8 and matrix row 11 require no horizontal body overflow at 800x600. `body` has `overflow-x: hidden` (`styles.css:27`) and a test asserts that string (`tests/test_static_ui.py:174`). | A horizontal scrollbar cannot appear, so the manual check has to look for clipped content. Needs verification in a browser. | Release check ticket |
| D10 | PRD section 13 lists "static UI structure (labels, no inline script, no external URLs)" in the sentence about what tests do not cover. `tests/test_static_ui.py` covers it with 11 tests. | Wording only. | Release check ticket |
| D11 | PRD matrix row 12 says "two concurrent PUTs"; PRD section 13 and the test use eight (`tests/test_api.py:196-222`). | None; the test is the stronger form. | No action |
| D12 | PRD section 6 names the 409 codes and `forbidden_origin` but not the codes for the other statuses. The code uses `bad_request`, `not_found`, `method_not_allowed`, `length_required`, `payload_too_large`, `unsupported_media_type`, `validation_failed`, `internal_error` (`server.py:41-46`). | New tickets add codes; without a full list the contract drifts further. | Each ticket that adds a code lists it in PRD section 6; the release check ticket completes the table |
| D13 | README and PRD section 4 say layers are moved with numeric fields only. Clicking the canvas selects the top layer under the pointer (`app.js:523-536`); neither document mentions it. | None for the planned work. | Release check ticket |
| D14 | "Unique ignoring case" is `str.lower()` (`storage.py:67-68`), not Unicode case folding. | `Straße` and `STRASSE` are different titles. Matters for the `title_taken` rule of the SVG import. | Noted in issue #6; no change planned |
| D15 | The epic's acceptance text says the fixture "exports byte-identically". Export does not exist until DC-5. | The epic finish line has to say which ticket supplies each check. | Epic (issue #1) |
| D16 | PRD section 5 names Python 3.12. Preparation ran 3.13.14 only. | 3.12 behaviour is the owner's record (README), not reproduced. Needs verification. | Release check ticket |

## 7. Decisions still with the owner

PRD section 14 lists five open choices. The batch proceeds on these defaults; each is cheap to revisit before the ticket that uses it starts.

| Choice | Default used by the batch | First ticket affected |
|---|---|---|
| Offline queue storage | `localStorage`, as issue #3 already says | Issue #3 and the two-tab page ticket |
| Tab-to-tab delivery | Polling a revision-ordered feed; no long-poll, no event stream | Issue #3 |
| Component nesting | Not allowed (the PRD default) | Issue #4 |
| Transforms in SVG import | Rejected (the PRD default) | Issue #6 |
| Pointer drag and resize on the canvas | Out of the batch | None |
