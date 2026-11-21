import os
import sqlite3
import tempfile
import unittest

from design_canvas import model
from design_canvas.storage import (DB_NAME, NotFound, RevisionConflict,
                                   Storage, StorageError, TitleTaken)


class StorageTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = tmp.name
        self.store = self.open()

    def open(self, path=None):
        s = Storage(path or self.dir)
        self.addCleanup(s.close)
        return s


class SchemaTest(StorageTestCase):
    def test_pragmas_and_version(self):
        self.store.close()
        conn = sqlite3.connect(os.path.join(self.dir, DB_NAME))
        try:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 1)
        finally:
            conn.close()

    def test_creates_missing_data_dir(self):
        nested = os.path.join(self.dir, "a", "b")
        self.open(nested)
        self.assertTrue(os.path.isfile(os.path.join(nested, DB_NAME)))

    def test_reopen_keeps_schema(self):
        p = self.store.create_project("One", [])
        self.store.close()
        again = self.open()
        self.assertEqual(again.get_project(p["id"])["title"], "One")

    def test_newer_schema_refused(self):
        self.store.close()
        conn = sqlite3.connect(os.path.join(self.dir, DB_NAME))
        conn.execute("PRAGMA user_version = 99")
        conn.close()
        with self.assertRaises(StorageError):
            Storage(self.dir)

    def test_bad_data_dirs(self):
        file_path = os.path.join(self.dir, "plain-file")
        with open(file_path, "w") as fh:
            fh.write("x")
        for bad in ("", "   ", file_path, os.path.join(file_path, "child")):
            with self.subTest(path=bad):
                with self.assertRaises(StorageError) as cm:
                    Storage(bad)
                self.assertNotIn("\n", str(cm.exception))

    def test_not_a_database(self):
        sub = os.path.join(self.dir, "junk")
        os.makedirs(sub)
        with open(os.path.join(sub, DB_NAME), "wb") as fh:
            fh.write(b"this is not a sqlite database" * 20)
        with self.assertRaises(StorageError):
            Storage(sub)


class ProjectTest(StorageTestCase):
    def test_create_empty_and_fixture(self):
        a = self.store.create_project("Empty", [])
        self.assertEqual((a["revision"], a["layers"]), (1, []))
        self.assertEqual(a["scene"], {"width": 640, "height": 400})
        b = self.store.create_project("Fx", model.fixture_layers())
        self.assertEqual(b["layers"], model.fixture_layers())

    def test_list_sorted_case_insensitive(self):
        self.store.create_project("banana", [])
        self.store.create_project("Apple", model.fixture_layers())
        self.store.create_project("cherry", [])
        listing = self.store.list_projects()
        self.assertEqual([p["title"] for p in listing], ["Apple", "banana", "cherry"])
        self.assertEqual(listing[0]["layer_count"], 2)

    def test_title_unique_case_insensitive(self):
        self.store.create_project("Plan", [])
        with self.assertRaises(TitleTaken):
            self.store.create_project("PLAN", [])
        self.assertEqual(len(self.store.list_projects()), 1)

    def test_update_persists_position_and_order(self):
        p = self.store.create_project("P", model.fixture_layers())
        layers = model.fixture_layers()
        layers[0]["x"] = 80
        layers.reverse()
        u = self.store.update_project(p["id"], "P", 1, layers)
        self.assertEqual(u["revision"], 2)
        self.store.close()
        again = self.open()
        got = again.get_project(p["id"])
        self.assertEqual([l["id"] for l in got["layers"]], ["text-1", "rect-1"])
        self.assertEqual(got["layers"][1]["x"], 80)
        self.assertEqual(got["layers"], layers)

    def test_conflict_writes_nothing_and_returns_current(self):
        p = self.store.create_project("P", model.fixture_layers())
        self.store.update_project(p["id"], "P", 1, [])
        before = self.store.get_project(p["id"])
        with self.assertRaises(RevisionConflict) as cm:
            self.store.update_project(p["id"], "Renamed", 1, model.fixture_layers())
        self.assertEqual(cm.exception.current, before)
        self.assertEqual(self.store.get_project(p["id"]), before)

    def test_title_taken_on_update_rolls_back(self):
        a = self.store.create_project("A", model.fixture_layers())
        self.store.create_project("B", [])
        with self.assertRaises(TitleTaken):
            self.store.update_project(a["id"], "b", 1, [])
        self.assertEqual(self.store.get_project(a["id"]), a)

    def test_rename_to_own_title_case_change(self):
        a = self.store.create_project("abc", [])
        u = self.store.update_project(a["id"], "ABC", 1, [])
        self.assertEqual(u["title"], "ABC")

    def test_conflict_wins_over_title_taken(self):
        a = self.store.create_project("A", [])
        self.store.create_project("B", [])
        with self.assertRaises(RevisionConflict):
            self.store.update_project(a["id"], "B", 5, [])

    def test_not_found(self):
        with self.assertRaises(NotFound):
            self.store.get_project(404)
        with self.assertRaises(NotFound):
            self.store.update_project(404, "x", 1, [])

    def test_update_removes_old_layers(self):
        p = self.store.create_project("P", model.fixture_layers())
        u = self.store.update_project(p["id"], "P", 1, model.fixture_layers()[:1])
        self.assertEqual(len(u["layers"]), 1)
        self.assertEqual(self.store.list_projects()[0]["layer_count"], 1)


if __name__ == "__main__":
    unittest.main()
