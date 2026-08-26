#!/usr/bin/env python3

from textual.app import App, ComposeResult
from textual.widgets import TextArea, Static
from textual.containers import Center, Vertical
from textual.reactive import reactive
from pathlib import Path
from spellchecker import SpellChecker
import re
import subprocess
import os
import tempfile
import shutil
import json
import time

NOTE_PATH = Path.home() / ".typewriter" / "note.txt"
NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
NOTE_PATH.touch(exist_ok=True)

POWER_SUPPLY_PATH = Path("/sys/class/power_supply")


class TopBar(Static):
    pass


class StatusBar(Static):
    pass


class MessageBar(Static):
    pass


class TypewriterApp(App):
    USE_ALTERNATE_SCREEN = False

    # -------------------- STYLE --------------------
    CSS = """
    Screen {
        background: #0f1115;
        color: #e6e6e6;
    }

    #page {
        width: 100%;
	max-width: 120;
        padding: 1 2;
    }

    TopBar {
        height: auto;
	min-height: 1;
        color: #aaaaaa;
        content-align: center middle;
    }

    TextArea {
        background: #0f1115;
        color: #e6e6e6;
        border: none;
        scrollbar-size: 0 0;
    }

    MessageBar {
        height: auto;
	min-height: 1;
        color: #ffaa88;
        content-align: center middle;
    }

    StatusBar {
        height: auto;
	min-height: 1;
        color: #888888;
        content-align: center middle;
    }
    """

    # -------------------- KEY BINDINGS --------------------
    BINDINGS = [
        ("ctrl+x", "quit_app", "Quit"),
        ("ctrl+e", "export_usb", "USB"),
        ("ctrl+g", "spell_check", "Spell"),
        ("ctrl+d", "export_gdocs", "Docs"),
        ("ctrl+k", "clear_note", "Clear"),
    ]

    saved = reactive(True)


    # Battery state
    battery_path = None
    battery_percent = None
    battery_status = None

    spell = SpellChecker()


    # -------------------- UI --------------------
    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="page"):
                self.topbar = TopBar()
                yield self.topbar

                self.editor = TextArea()
                yield self.editor

                self.message = MessageBar("")
                yield self.message

                self.status = StatusBar()
                yield self.status

    async def on_mount(self) -> None:
        self.editor.text = NOTE_PATH.read_text()
        self.editor.focus()

        self.detect_battery()
        self.update_battery()

        self.update_topbar()
        self.update_status()

        self.set_interval(0.5, self.auto_save)
        self.set_interval(30, self.update_battery)

    # -------------------- TOP BAR --------------------
    def update_topbar(self) -> None:
        self.topbar.update(
                "TYPEWRITER | Ctrl+G SpellCheck | Ctrl+E USB | Ctrl+X Exit | Ctrl+D Save to G-docs | Ctrl+K Clear File"
            )

    # -------------------- STATUS --------------------
    def update_status(self) -> None:
        words = len(self.editor.text.split())
        state = "Saved" if self.saved else "Saving..."

        battery = ""
        if self.battery_percent is not None:
            icon = "⚡" if self.battery_status == "Charging" else "🔋"
            battery = f" | {self.battery_percent}% {icon}"

        self.status.update(f"{state} | {words} words{battery}")

    async def auto_save(self) -> None:
        NOTE_PATH.write_text(self.editor.text)
        self.saved = True
        self.update_status()

    def on_text_area_changed(self) -> None:
        self.saved = False
        self.update_status()

    # -------------------- GLOBAL KEY HANDLING --------------------
    def on_key(self, event) -> None:
        if event.key == "tab":
            event.stop()
            self.editor.insert("            ")
            self.saved = False
            self.update_status()
            return
        if event.key == "ctrl+d":
            event.stop()
            self.action_export_gdocs()
        elif event.key == "ctrl+e":
            event.stop()
            self.action_export_usb()
        elif event.key == "ctrl+g":
            event.stop()
            self.action_spell_check()
        elif event.key == "ctrl+k":
            event.stop()
            self.action_clear_note()
        elif event.key == "ctrl+x":
            event.stop()
            self.action_quit_app()

    def get_word_under_cursor(self) -> str | None:
        text = self.editor.text
        row, column = self.editor.cursor_location
        lines = text.splitlines(keepends=True)
        if row >= len(lines):
            return None
        cursor = sum(len(lines[i]) for i in range(row)) + column


        if cursor > len(text):
            return None
        left = text[:cursor]
        right = text[cursor:]
        left_match = re.search(r"[A-Za-z']+$", left)
        right_match = re.match(r"^[A-Za-z']+", right)
        word = ""
        if left_match:
            word += left_match.group()
        if right_match:
            word += right_match.group()
        return word if word else None
    def action_spell_check(self) -> None:
        word = self.get_word_under_cursor()
        if not word:
            self.message.update("No word selected")
            return
        if word.lower() in self.spell:
            self.message.update(f"'{word}' is correct")
            return
        suggestion = self.spell.correction(word)
        if suggestion:
            self.message.update(f"{word} -> {suggestion}")
        else:
            self.message.update(f"No suggestion for '{word}'")
        self.message.refresh()

    # -------------------- EXIT --------------------
    def action_quit_app(self) -> None:
        NOTE_PATH.write_text(self.editor.text)
        self.exit()
        os.system("sync")
        os.system("systemctl poweroff")


    def action_clear_note(self) -> None:
        self.editor.text = " "
        NOTE_PATH.write_text(" ")
        self.saved = True
        self.message.update("Note Cleared")
        self.message.refresh()
        self.update_status()
    # -------------------- BATTERY --------------------
    def detect_battery(self) -> None:
        if not POWER_SUPPLY_PATH.exists():
            return

        for item in POWER_SUPPLY_PATH.iterdir():
            if item.name.startswith("BAT"):
                self.battery_path = item
                return

    def update_battery(self) -> None:
        if not self.battery_path:
            return

        try:
            capacity = (self.battery_path / "capacity").read_text().strip()
            status = (self.battery_path / "status").read_text().strip()

            self.battery_percent = capacity
            self.battery_status = status

            self.update_status()
        except Exception:
            self.battery_percent = None
            self.battery_status = None

    # -------------------- USB EXPORT --------------------
    def action_export_usb(self) -> None:
        mount_point = Path("/mnt/usb")
        mount_point.mkdir(exist_ok=True)

        result = subprocess.run(
            ["lsblk", "-rpno", "NAME,TYPE,RM"],
            capture_output=True,
            text=True
        )

        device = None
        for line in result.stdout.splitlines():
            name, typ, rm = line.split()
            if rm == "1" and typ == "part":
                device = name
                break

        if not device:
            self.message.update("No USB detected")
            self.message.refresh()
            return

        mount_result = subprocess.run(
            ["mount", device, str(mount_point)],
            capture_output=True,
            text=True
        )

        if mount_result.returncode != 0:
            self.message.update("USB mount failed")
            self.message.refresh()
            return

        try:
            subprocess.run(
                ["cp", str(NOTE_PATH), str(mount_point)],
                check=True
            )
            subprocess.run(["sync"], check=False)
            self.message.update("Exported to USB")
            self.message.refresh()
        finally:
            subprocess.run(["umount", str(mount_point)], check=False)

    def action_export_gdocs(self) -> None:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
            tmp.write(self.editor.text)
            tmp_path = tmp.name
        try:
            result = subprocess.run(
                [
                    "rclone",
                    "copyto",
                    tmp_path,
                    "gdrive:Typewriter/TypewriterDoc.txt",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                self.message.update("Uploaded to Google Docs")
            else:
                self.message.update("Upload failed X")
        finally:
            os.unlink(tmp_path)
        self.message.refresh()


if __name__ == "__main__":
    TypewriterApp().run()
