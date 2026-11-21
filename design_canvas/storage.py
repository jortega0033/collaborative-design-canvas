"""SQLite persistence. One connection guarded by a lock; every write is an
explicit BEGIN IMMEDIATE transaction that is rolled back on any failure."""

import contextlib
import datetime
import os
import sqlite3
import threading

from .model import SCENE

DB_NAME = "design_canvas.sqlite3"

# Ordered migrations; index i brings user_version from i to i+1.
MIGRATIONS = [
    [
        """CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            title_key TEXT NOT NULL UNIQUE,
            revision INTEGER NOT NULL CHECK (revision >= 1),
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE layers (
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            position INTEGER NOT NULL,
            layer_id TEXT NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('rect', 'text')),
            label TEXT NOT NULL,
            x INTEGER NOT NULL,
            y INTEGER NOT NULL,
            w INTEGER NOT NULL,
            h INTEGER NOT NULL,
            fill TEXT NOT NULL,
            text TEXT,
            font_size INTEGER,
            PRIMARY KEY (project_id, position),
            UNIQUE (project_id, layer_id)
        )""",
    ],
]
SCHEMA_VERSION = len(MIGRATIONS)


class StorageError(Exception):
    """Data directory or database cannot be used (CLI exit code 2)."""


class NotFound(Exception):
    pass


class TitleTaken(Exception):
    pass


class RevisionConflict(Exception):
    def __init__(self, current):
        super().__init__("revision conflict")
        self.current = current


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _title_key(title):
    return title.lower()


class Storage:
    def __init__(self, data_dir):
        self._lock = threading.RLock()
        self._conn = None
        try:
            data_dir = os.fspath(data_dir)
        except TypeError:
            raise StorageError("data directory path is invalid")
        if not isinstance(data_dir, str) or not data_dir.strip():
            raise StorageError("data directory path must not be empty")
        path = os.path.abspath(data_dir)
        if os.path.exists(path) and not os.path.isdir(path):
            raise StorageError("data directory path is not a directory")
        try:
            os.makedirs(path, exist_ok=True)
        except (OSError, ValueError) as exc:
            raise StorageError("cannot create data directory: %s" % _oneline(exc))
        self.path = os.path.join(path, DB_NAME)
        try:
            self._conn = sqlite3.connect(
                self.path, check_same_thread=False, isolation_level=None)
            self._conn.execute("PRAGMA busy_timeout = 5000")
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._migrate()
        except StorageError:
            self._abort_open()
            raise
        except (sqlite3.Error, OSError, ValueError) as exc:
            self._abort_open()
            raise StorageError("cannot open database: %s" % _oneline(exc))

    def _abort_open(self):
        if self._conn is not None:
            with contextlib.suppress(Exception):
                self._conn.close()
            self._conn = None

    def _migrate(self):
        conn = self._conn
        conn.execute("BEGIN IMMEDIATE")
        try:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise StorageError(
                    "database schema version %d is newer than supported version %d"
                    % (version, SCHEMA_VERSION))
            for target in range(version, SCHEMA_VERSION):
                for stmt in MIGRATIONS[target]:
                    conn.execute(stmt)
                conn.execute("PRAGMA user_version = %d" % (target + 1))
            conn.execute("COMMIT")
        except BaseException:
            with contextlib.suppress(Exception):
                conn.execute("ROLLBACK")
            raise

    def close(self):
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    @contextlib.contextmanager
    def _tx(self):
        with self._lock:
            if self._conn is None:
                raise StorageError("database is closed")
            conn = self._conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.execute("COMMIT")
            except BaseException:
                with contextlib.suppress(Exception):
                    conn.execute("ROLLBACK")
                raise

    # -- helpers (call with lock held) ------------------------------------

    @staticmethod
    def _insert_layers(conn, pid, layers):
        rows = [
            (pid, pos, l["id"], l["type"], l["label"], l["x"], l["y"], l["w"],
             l["h"], l["fill"], l.get("text"), l.get("font_size"))
            for pos, l in enumerate(layers)
        ]
        conn.executemany(
            "INSERT INTO layers (project_id, position, layer_id, type, label,"
            " x, y, w, h, fill, text, font_size) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            rows)

    @staticmethod
    def _load(conn, pid):
        row = conn.execute(
            "SELECT id, title, revision, updated_at FROM projects WHERE id = ?",
            (pid,)).fetchone()
        if row is None:
            return None
        layers = []
        for r in conn.execute(
                "SELECT layer_id, type, label, x, y, w, h, fill, text, font_size"
                " FROM layers WHERE project_id = ? ORDER BY position", (pid,)):
            layer = {"id": r[0], "type": r[1], "label": r[2],
                     "x": r[3], "y": r[4], "w": r[5], "h": r[6]}
            if r[1] == "text":
                layer["text"] = r[8]
                layer["font_size"] = r[9]
            layer["fill"] = r[7]
            layers.append(layer)
        return {"id": row[0], "title": row[1], "revision": row[2],
                "updated_at": row[3], "scene": dict(SCENE), "layers": layers}

    # -- public API -------------------------------------------------------

    def list_projects(self):
        with self._lock:
            if self._conn is None:
                raise StorageError("database is closed")
            rows = self._conn.execute(
                "SELECT p.id, p.title, p.revision, p.updated_at,"
                " (SELECT COUNT(*) FROM layers l WHERE l.project_id = p.id)"
                " FROM projects p ORDER BY p.title_key, p.id").fetchall()
        return [{"id": r[0], "title": r[1], "revision": r[2],
                 "updated_at": r[3], "layer_count": r[4]} for r in rows]

    def get_project(self, pid):
        with self._lock:
            if self._conn is None:
                raise StorageError("database is closed")
            project = self._load(self._conn, pid)
        if project is None:
            raise NotFound()
        return project

    def create_project(self, title, layers):
        with self._tx() as conn:
            try:
                cur = conn.execute(
                    "INSERT INTO projects (title, title_key, revision, updated_at)"
                    " VALUES (?, ?, 1, ?)", (title, _title_key(title), _now()))
            except sqlite3.IntegrityError:
                raise TitleTaken()
            pid = cur.lastrowid
            self._insert_layers(conn, pid, layers)
            return self._load(conn, pid)

    def update_project(self, pid, title, base_revision, layers):
        with self._tx() as conn:
            try:
                cur = conn.execute(
                    "UPDATE projects SET title = ?, title_key = ?,"
                    " revision = revision + 1, updated_at = ?"
                    " WHERE id = ? AND revision = ?",
                    (title, _title_key(title), _now(), pid, base_revision))
            except sqlite3.IntegrityError:
                raise TitleTaken()
            if cur.rowcount == 0:
                current = self._load(conn, pid)
                if current is None:
                    raise NotFound()
                raise RevisionConflict(current)
            conn.execute("DELETE FROM layers WHERE project_id = ?", (pid,))
            self._insert_layers(conn, pid, layers)
            return self._load(conn, pid)


def _oneline(exc):
    return " ".join(str(exc).split()) or exc.__class__.__name__
