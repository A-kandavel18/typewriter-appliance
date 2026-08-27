import tempfile
import unittest
import zipfile
from pathlib import Path

from google_publish import make_docx


class GooglePublishTests(unittest.TestCase):
    def test_generated_docx_contains_text(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.docx"
            make_docx(path, "one & two\n\tsecond line", "Chapter One")
            with zipfile.ZipFile(path) as archive:
                xml = archive.read("word/document.xml").decode()
                styles = archive.read("word/styles.xml").decode()
                settings = archive.read("word/settings.xml").decode()
            self.assertIn("one &amp; two", xml)
            self.assertIn("second line", xml)
            self.assertIn("Chapter One", xml)
            self.assertIn("<w:tab/>", xml)
            self.assertIn('w:ascii="Book Antiqua"', styles)
            self.assertIn('<w:sz w:val="24"/>', styles)
            self.assertIn('<w:jc w:val="center"/>', styles)
            self.assertIn('<w:defaultTabStop w:val="720"/>', settings)
            self.assertIn('<w:pgMar w:top="1440"', xml)


if __name__ == "__main__":
    unittest.main()
