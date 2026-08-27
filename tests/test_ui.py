import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch


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

    def test_ctrl_x_opens_shutdown_confirmation(self):
        with tempfile.TemporaryDirectory() as folder:
            os.environ["TYPEWRITER_DATA_DIR"] = folder
            from app import ConfirmScreen, TypewriterApp

            async def exercise():
                app = TypewriterApp()
                async with app.run_test() as pilot:
                    app.editor.text = "this line must remain"
                    await pilot.press("ctrl+x")
                    await pilot.pause()
                    self.assertIsInstance(app.screen, ConfirmScreen)
                    self.assertEqual(app.editor.text, "this line must remain")
                    await pilot.press("escape")

            asyncio.run(exercise())

    def test_ctrl_d_publishes_active_document(self):
        with tempfile.TemporaryDirectory() as folder:
            os.environ["TYPEWRITER_DATA_DIR"] = folder
            from app import TypewriterApp

            async def exercise():
                app = TypewriterApp()
                with patch("app.GooglePublisher.from_rclone") as factory:
                    factory.return_value.publish.return_value = "Typewriter/unique.docx"
                    async with app.run_test() as pilot:
                        app.editor.text = "individual content"
                        await pilot.press("ctrl+d")
                        await pilot.pause()
                    factory.return_value.publish.assert_called_once_with(
                        app.store.active.title,
                        "individual content",
                        None,
                        app.store.active.id,
                    )

            asyncio.run(exercise())

    def test_tab_inserts_real_tab_character(self):
        with tempfile.TemporaryDirectory() as folder:
            os.environ["TYPEWRITER_DATA_DIR"] = folder
            from app import TypewriterApp

            async def exercise():
                app = TypewriterApp()
                async with app.run_test() as pilot:
                    await pilot.press("tab")
                    await pilot.pause()
                    self.assertTrue(app.editor.text.startswith("\t"))

            asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
