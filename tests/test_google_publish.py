import tempfile
import unittest
import zipfile
from pathlib import Path

from google_publish import make_docx


class GooglePublishTests(unittest.TestCase):
    def test_generated_docx_contains_text(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.docx"
            make_docx(path, "one & two\nsecond line")
            with zipfile.ZipFile(path) as archive:
                xml = archive.read("word/document.xml").decode()
            self.assertIn("one &amp; two", xml)
            self.assertIn("second line", xml)


if __name__ == "__main__":
    unittest.main()
