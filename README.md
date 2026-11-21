# Collaborative Design Canvas

A local, offline workbench for arranging rectangle and text layers on a 640×400 canvas, with named projects saved to SQLite. Python 3.12 standard library only; static HTML/CSS/JS; no build step.

M1 implements single-user canvas editing. See the baseline verification below.

## Launch

Linux:

```
python3 -m design_canvas --data-dir ./data --port 8750
```

Windows:

```
python -m design_canvas --data-dir .\data --port 8750
```

Then open `http://127.0.0.1:8750/`. Use `--port 0` to pick a free port (the chosen URL is printed). The server binds to 127.0.0.1 only. Stop with Ctrl+C. An empty path, a path that is a file, or an unwritable directory exits with code 2.

## M1 smoke steps

1. Open the URL; `GET /api/v1/health` should return `{"status":"ok",...}`.
2. Type `Station` in **Document title**, click **Load fixture**: a rectangle (x=40, y=60, 120×72) and the text "Station signs" appear in the preview.
3. Select the rectangle layer, set **X** to `80`; the preview updates immediately.
4. Click **Move up** / **Move down** to change order; click **Add rectangle** / **Add text** to add layers; edit **Layer label**.
5. Click **Save**; the status line shows the new revision.
6. Stop the server, start it again with the same `--data-dir`, click `Station` in the **Project list**: X is still 80 and layer order is unchanged.
7. Stale-save check: open the project in two tabs, edit and save in one, then edit and save in the other; the second shows a revision conflict, keeps your edits, and offers **Reload server version**.

## Limits

- Scene fixed at 640×400; max 200 layers per project; titles 1–80 chars, unique ignoring case; layer labels ≤ 60, text ≤ 500 chars.
- Request bodies ≤ 256 KiB; loopback only; no sign-in, sync, or external services.
- Layers are moved and resized with numeric fields only (no dragging).
- Saves are explicit, whole-project, guarded by a revision number.

## Persistence

The SQLite file is `<data-dir>/design_canvas.sqlite3` (schema version 1, migrations applied on startup). The browser stores only the last opened project id in `localStorage`.

## Tests

```
python -m unittest discover -s tests -t .
```

(use `python3` on Linux). Tests use temporary directories and a server on a random port.

## Planned work (not built)

Reversible operation log and keyboard commands; two-tab collaboration with offline patches and visible conflict resolution; reusable components with instance overrides; deterministic auto-layout stacks; sanitized SVG-subset exchange. Details, API/schema contracts and acceptance criteria: [docs/PRD.md](docs/PRD.md).

## Baseline verification

- Windows with Python 3.13.14 and Ubuntu 24.04 WSL with Python 3.12.3 each passed 68 unit and API tests. WSL unit tests used temporary storage on tmpfs.
- Chrome 157 verified the main workflow with external requests blocked. A rendered fixture saved two layers and reopened with the edited X position and text after a server restart.
