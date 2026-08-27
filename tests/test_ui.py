import asyncio
import os
import tempfile
import unittest


class InterfaceTests(unittest.TestCase):
    def test_create_and_open_document(self):
        with tempfile.TemporaryDirectory() as folder:
            os.environ["TYPEWRITER_DATA_DIR"] = folder
            from app import TypewriterApp

            async def exercise():
                app = TypewriterApp()
                async with app.run_test() as pilot:
                    await pilot.press("ctrl+n")
                    await pilot.pause()
                    await pilot.press("t", "e", "s", "t", "enter")
                    await pilot.pause()
                    self.assertEqual(len(app.store.documents), 2)
                    await pilot.press("ctrl+o")
                    await pilot.pause()
                    await pilot.press("escape")

            asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
