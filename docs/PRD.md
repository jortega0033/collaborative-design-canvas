# Collaborative Design Canvas — PRD and Technical Spec

Status legend: **[Implemented baseline]** = implemented in M1 (see [baseline verification](../README.md#baseline-verification)); **[Planned]** = future work, not built.

## 1. User and workflow

**User:** a frontend designer working alone on one machine who wants to arrange layout components on a fixed canvas and check that several local editors (browser tabs) can change a layout independently without clobbering each other.

**Workflow:** start the local server → create or load a named canvas → add rectangle and text layers → adjust position, size, color and order with numeric controls → save → close the server → restart → reopen the same project with identical positions and order. Later milestones add undo, two-tab editing, components, auto-layout and vector exchange.

Scope: offline, single-person, loopback only. No sign-in, remote sync, paid services, media, or model integration. This is a layout/component tool, not a UX journey graph, media composition tool, or a clone of any existing interface.

## 2. Milestones

| Milestone | Content | Status |
|---|---|---|
| M1 | Project title, 640×400 scene, rect/text layers (add, select, move, resize, reorder, delete), Canvas2D preview, named SQLite projects, revision-guarded save, project list | [Implemented baseline] |
| DC-1 | Reversible operation log, keyboard command selection | [Planned] |
| DC-2 | Two-tab collaboration, ordered offline patches, per-field conflicts | [Planned] |
| DC-3 | Components and instance overrides | [Planned] |
| DC-4 | Auto-layout stack | [Planned] |
| DC-5 | Sanitized vector exchange | [Planned] |

## 3. Epic and future issues

**Epic: Safe multi-editor layout canvas with reusable components.** Done when DC-1…DC-5 below are merged, the M1 fixture still round-trips byte-identically across restart, and nothing outside the Python 3.12 stdlib or a non-loopback listener is introduced.
### DC-1 (P1) Reversible operation log and keyboard commands — depends on: M1
Stories: as a designer I can undo/redo any layout edit, and run commands from the keyboard.
Acceptance:
- 100 seeded (seed 7) operations on the fixture, all undone, give canonical scene JSON byte-equal to the initial fixture; redo reproduces the post-100 scene.
- Undo works after server restart (operations persisted, sequence monotonic).
- Command list opens with Ctrl/Cmd+K, filter input focused, Arrow/Enter/Escape work, focus returns on close, `aria-activedescendant` set.

### DC-2 (P2) Two-tab collaboration — depends on: DC-1
Stories: as a designer I edit in two tabs (also while one is offline) and both converge with visible resolution.
Acceptance:
- A sets rect-1 x=80, B sets x=100 and y=70: later arrival wins x, y=70, one conflict shown, both tabs identical.
- Same (client_id, client_seq) submitted 3× changes revision once.
- Patches 1..5 delivered as 3,1,5,2,4 are held until the gap closes and apply as 1..5, converging with in-order delivery (a gap older than 30 s is rejected with a visible error). Each tab uses its own `client_id` kept in `sessionStorage`; the offline queue is keyed by it. The M1 whole-document PUT stays available.
- Two reorders from different bases converge with no duplicate/missing IDs; losing text recoverable from the panel.

### DC-3 (P3) Components and instance overrides — depends on: DC-1
Acceptance:
- Master label 'Station signs', 3 instances, instance 2 overrides to 'Exit'; renaming master to 'Platform signs' updates instances 1 and 3, instance 2 keeps 'Exit'.
- Instance IDs and component_id stable across save/restart.
- Detach freezes resolved values; deleting a master with 2 live instances → 409 `component_in_use`, nothing written.

### DC-4 (P4) Auto-layout stack — depends on: DC-1
Acceptance:
- Horizontal frame w=296, padding 16, gap 16, three children width 76 → x = 16, 108, 200.
- Horizontal frame h=120, padding 8, child h=40, cross-axis alignment start/center/end → y = 8 / 40 / 72. Odd remainders for center round down (floor).
- Empty frame → empty flag, no children; 3×120 children in w=296 (padding/gap 16) → overflow_px=128, children unshrunk.
- Layout is deterministic; reordering changes only positions.

### DC-5 (P5) Sanitized vector exchange — depends on: DC-1, DC-3
Acceptance:
- Fixture export then import gives identical canonical scene (rect-1 at 40,60,120,72; text-1 'Station signs').
- script, event attributes, foreignObject, image, use, external href, DOCTYPE/entities, >262144 bytes → 422 with specific code, no project created.
- `<`, `>`, `&`, quotes in text round-trip unchanged; cancelling preview changes nothing.
- Allowed elements `svg, g, rect, text`; allowed attributes `id, x, y, width, height, fill, font-size, data-label, data-w, data-h` (text boxes carry their size in `data-w`/`data-h`, labels in `data-label`). More than 8 nesting levels or 200 elements → 422. An imported title that already exists → 409 `title_taken`.

Any later external package or reference must be offline-plannable and approved before it is staged; none is required.

## 4. Scope boundaries (M1)
In: items in §2 M1. Out: realtime sync, undo, components, auto-layout, SVG, multi-select, drag-to-move on canvas (numeric controls only), images, authentication, accounts, deployment.

## 5. System stack [Implemented baseline]
Python 3.12 stdlib: `http.server.ThreadingHTTPServer` bound to 127.0.0.1, `sqlite3`, `unittest`. Static HTML/CSS/native JS served from an allowlist (`/`, `/index.html`, `/app.js`, `/styles.css`). No build tooling, no packages. Launch: `python -m design_canvas --data-dir <path> --port <port>` (Windows) / `python3 -m ...` (Linux).

## 6. Contracts [Implemented baseline]
The authoritative request/response contract is below (mirrors the build contract).

**Layer:** `id` (`^[A-Za-z0-9_-]{1,40}$`, unique per project, client-assigned, stable), `type` `rect|text`, `label` 1–60, `x`,`y` int −2000..2000, `w`,`h` int 1..2000, `fill` `#rrggbb`; text adds `text` 0–500 and `font_size` 8..96. Unknown fields → 422.

**Project:** `{id, title, revision, updated_at, scene:{width:640,height:400}, layers[]}`; array order is z-order, index 0 is back.

| Endpoint | Behavior |
|---|---|
| GET `/api/v1/health` | 200 `{"status":"ok","api":1,"schema":1}` |
| GET `/api/v1/projects` | list `{id,title,revision,updated_at,layer_count}`, case-insensitive title order |
| POST `/api/v1/projects` | `{title, fixture?}` → 201, revision 1 |
| GET `/api/v1/projects/{id}` | 200 / 404 |
| PUT `/api/v1/projects/{id}` | `{title, base_revision, layers}` → 200 revision+1; 409 `revision_conflict` includes `current` |

Errors: `{"error":{"code","message","details?","current?"}}` with 400, 403 `forbidden_origin`, 404, 405, 409 (`revision_conflict`, `title_taken`), 411, 413 (>262144 bytes), 415, 422, 500.

**Schema (user_version 1):** `projects(id PK, title, title_key UNIQUE NOT NULL, revision INT NOT NULL CHECK(>=1), updated_at)`; `layers(project_id FK ON DELETE CASCADE, position INT, layer_id, type CHECK in (rect,text), label, x,y,w,h, fill, text, font_size, PRIMARY KEY(project_id,position), UNIQUE(project_id,layer_id))`. Migrations are an ordered list applied in a transaction; a newer database is refused.

**Save algorithm:** one transaction: `UPDATE projects SET revision=revision+1 … WHERE id=? AND revision=?`; zero rows → 409 and nothing written; otherwise delete and reinsert layers with positions 0..n−1.

**UI contract:** labels `Document title`, `New canvas`, `Add rectangle`, `Add text`, `Layer label`, `X`, `Y`, `Width`, `Height`, `Fill`, `Save`, `Project list`; element ids as in the build contract; `role=status` live region; all user text drawn via `fillText` / `textContent`.

## 7. Deterministic fixture (M1)
`POST /api/v1/projects {"title":"Station","fixture":true}` creates revision 1 with:
1. `rect-1` rect "Platform block" x=40 y=60 w=120 h=72 fill #2f6f9f
2. `text-1` text "Station signs" x=40 y=160 w=240 h=32 font_size 24 fill #1f2933

Expected: change `rect-1` x to 80, save → revision 2; after restart GET returns rect-1 x=80 (y=60,w=120,h=72) at index 0, text-1 at index 1.

## 8. Responsiveness and accessibility [Implemented baseline]
At 800×600 no horizontal body overflow; ≥900 px three columns, below that stacked. Every input has an associated `<label>`; `:focus-visible` outline ≥2 px; text contrast ≥4.5:1; system fonts; the layer list is the accessible equivalent of the canvas; status messages are announced politely. Everything is operable by keyboard.

## 9. Errors, retry, restart, concurrency
- Stale save: 409 keeps all local edits; user may press Save again after `Reload server version` and re-applying, or reload explicitly. Text is never discarded automatically.
- Validation: 422 field messages in the status area. Unreachable server: edits kept, Save stays enabled to retry.
- Restart: all state is in SQLite; the browser remembers only the last-opened project id.
- Concurrency: optimistic revision check inside a transaction; with two simultaneous PUTs on the same base revision exactly one succeeds.

## 10. Versioning and security
API prefix `/api/v1`; schema via `PRAGMA user_version`. Bind 127.0.0.1 only; Host must be `127.0.0.1:<port>` or `localhost:<port>`; mutations with a foreign Origin → 403; no CORS headers; body cap 262144 bytes; JSON shape and length validation; CSP `default-src 'self'`; static path allowlist (no URL-derived file paths); per-connection socket timeout; parameterized SQL only; generic 500 messages.

## 11. Acceptance matrix (M1)

| # | Check | Expected |
|---|---|---|
| 1 | GET /api/v1/health | 200 status ok |
| 2 | GET / | HTML with all required labels |
| 3 | Create fixture, PUT x=80 | revision 2, exact x=80 |
| 4 | Restart, GET project | x=80, order rect-1 then text-1 |
| 5 | PUT with stale base_revision | 409, current returned, DB unchanged |
| 6 | Duplicate title (any case) | 409 title_taken |
| 7 | Body >262144 bytes | 413 |
| 8 | Foreign Host / Origin on POST | 403 |
| 9 | GET /../x, /%2e%2e/ | 404 |
| 10 | Bad --data-dir (file, unwritable) | exit 2 |
| 11 | 800×600 viewport | no body horizontal scroll |
| 12 | Two concurrent PUTs same base | exactly one 200, one 409 |

## 12. Sample demo
Start the server, open the URL, set Document title `Station`, click Load fixture, set X to 80 for `Platform block`, Save (status shows revision 2), stop and restart the server on the same data dir, click `Station` in the project list; X is 80.

## 13. Test plan
`python -m unittest discover -s tests -t .`: model validation, storage (migrations, constraints, transactions, restart persistence), API (status codes, origin/host, caps, static allowlist, 8 concurrent PUTs on one base revision, lifecycle on port 0 with temporary directories). Not covered by tests: CLI subprocess output and Ctrl+C, unwritable data directory, slow-client timeout; the 800×600 no-overflow check is manual, static UI structure (labels, no inline script, no external URLs). Manual browser smoke steps are in README. Browser rendering and layout checks at 800×600 are manual until a no-dependency approach is chosen.

## 14. Open choices
- Offline patch queue storage (localStorage vs. IndexedDB) for DC-2.
- Polling interval vs. long-poll for tab-to-tab delivery.
- Whether components allow nesting (default: no).
- Whether SVG import should accept transforms (default: no).
- Pointer drag/resize on canvas as a convenience after keyboard-first controls.
