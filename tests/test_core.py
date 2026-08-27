import tempfile
import unittest
from pathlib import Path

from typewriter_core import DocumentStore, atomic_write, safe_filename


class CoreTests(unittest.TestCase):
    def test_atomic_write_replaces_content(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "note.txt"
            atomic_write(path, "first")
            atomic_write(path, "second")
            self.assertEqual(path.read_text(), "second")

    def test_migrates_legacy_note_and_keeps_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            legacy = root / "note.txt"
            legacy.write_text("existing work")
            store = DocumentStore(root / "data", legacy)
            self.assertEqual(store.active.title, "Imported Note")
            self.assertEqual(store.read(), "existing work")
            self.assertEqual((root / "note.txt.migrated").read_text(), "existing work")

    def test_multiple_documents_survive_reload(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = DocumentStore(root)
            first = store.active.id
            store.save("one")
            second = store.create("Second", "two")
            store.rename("Renamed")
            reloaded = DocumentStore(root)
            self.assertEqual(len(reloaded.documents), 2)
            self.assertEqual(reloaded.active.id, second.id)
            self.assertEqual(reloaded.read(), "two")
            reloaded.select(first)
            self.assertEqual(reloaded.read(), "one")

    def test_safe_filename(self):
        self.assertEqual(safe_filename("../Draft: One?"), "Draft One")


if __name__ == "__main__":
    unittest.main()
