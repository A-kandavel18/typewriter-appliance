#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path

from spellchecker import SpellChecker
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView, Static, TextArea

from google_publish import GooglePublisher
from typewriter_core import Document, DocumentStore, safe_filename

LEGACY_NOTE = Path(os.environ.get("TYPEWRITER_LEGACY_NOTE", Path.home() / ".typewriter" / "note.txt"))
POWER_SUPPLY_PATH = Path("/sys/class/power_supply")


class ConfirmScreen(ModalScreen[bool]):
    def __init__(self, prompt: str):
        super().__init__()
        self.prompt = prompt

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.prompt)
            yield Button("Cancel", id="cancel")
            yield Button("Confirm", id="confirm", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")


class NameScreen(ModalScreen[str | None]):
    def __init__(self, prompt: str, value: str = ""):
        super().__init__()
        self.prompt, self.value = prompt, value

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.prompt)
            yield Input(value=self.value, id="name")
            yield Button("Cancel", id="cancel")
            yield Button("Save", id="save", variant="primary")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or "Untitled")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None if event.button.id == "cancel" else self.query_one(Input).value.strip() or "Untitled")


class LibraryScreen(ModalScreen[str | None]):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, documents: list[Document], active_id: str):
        super().__init__()
        self.documents, self.active_id = documents, active_id

    def compose(self) -> ComposeResult:
        with Vertical(id="library"):
            yield Label("Open document")
            yield ListView(*[ListItem(Label(("• " if item.id == self.active_id else "  ") + item.title), id=f"doc-{item.id}") for item in self.documents])
            yield Label("Enter: open    Esc: cancel")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.id.removeprefix("doc-") if event.item.id else None)


class TypewriterApp(App):
    USE_ALTERNATE_SCREEN = False
    CSS = """
    Screen { background: #0f1115; color: #e6e6e6; }
    #page { width: 100%; max-width: 120; padding: 1 2; }
    Static { height: auto; min-height: 1; content-align: center middle; }
    TextArea { background: #0f1115; color: #e6e6e6; border: none; scrollbar-size: 0 0; }
    #dialog { width: 60; height: auto; padding: 1 2; border: round #888; background: #171a20; }
    #library { width: 70; height: 70%; padding: 1 2; border: round #888; background: #171a20; }
    """
    BINDINGS = [
        Binding("ctrl+n", "new_document", "New", priority=True),
        Binding("ctrl+o", "open_document", "Open", priority=True),
        Binding("ctrl+s", "save_document", "Save", priority=True),
        Binding("ctrl+r", "rename_document", "Rename", priority=True),
        Binding("ctrl+e", "export_usb", "USB", priority=True),
        Binding("ctrl+d", "publish_google", "Google", priority=True),
        Binding("ctrl+g", "spell_check", "Spell", priority=True),
        Binding("ctrl+k", "clear_document", "Clear", priority=True),
        Binding("ctrl+x", "shutdown", "Shutdown", priority=True),
    ]

    def __init__(self):
        super().__init__()
        self.store = DocumentStore(legacy_note=LEGACY_NOTE)
        self.dirty = False
        self.last_revision = 0.0
        self.battery_path: Path | None = None
        self.battery_percent: str | None = None
        self.battery_status: str | None = None
        self.spell = SpellChecker()

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="page"):
                self.topbar = Static()
                yield self.topbar
                self.editor = TextArea()
                yield self.editor
                self.message = Static("")
                yield self.message
                self.status = Static()
                yield self.status

    def on_mount(self) -> None:
        self._load_active()
        self._detect_battery()
        self._update_battery()
        self.set_interval(1.0, self._autosave)
        self.set_interval(30.0, self._update_battery)

    def _load_active(self) -> None:
        self.editor.text = self.store.read()
        self.dirty = False
        self.topbar.update("TYPEWRITER | N New  O Open  S Save  R Rename  E USB  D Google  G Spell  K Clear  X Shutdown")
        self.message.update(f"Opened: {self.store.active.title}")
        self._update_status()
        self.editor.focus()

    def on_text_area_changed(self) -> None:
        self.dirty = True
        self._update_status()

    def on_key(self, event) -> None:
        if event.key == "tab":
            event.stop()
            self.editor.insert("    ")

    def _save(self, revision: bool = False) -> None:
        self.store.save(self.editor.text, make_revision=revision)
        self.dirty = False
        self._update_status()

    def _autosave(self) -> None:
        if self.dirty:
            now = time.time()
            revision = now - self.last_revision >= 300
            self._save(revision)
            if revision:
                self.last_revision = now

    def _update_status(self) -> None:
        state = "Unsaved" if self.dirty else "Saved"
        battery = f" | {self.battery_percent}% {'⚡' if self.battery_status == 'Charging' else '🔋'}" if self.battery_percent else ""
        self.status.update(f"{self.store.active.title} | {state} | {len(self.editor.text.split())} words{battery}")

    def action_save_document(self) -> None:
        self._save(True)
        self.message.update("Saved with revision")

    def action_new_document(self) -> None:
        self._save()
        self.push_screen(NameScreen("New document title"), self._finish_new)

    def _finish_new(self, title: str | None) -> None:
        if title:
            self.store.create(title)
            self._load_active()

    def action_open_document(self) -> None:
        self._save()
        self.push_screen(LibraryScreen(self.store.ordered(), self.store.active.id), self._finish_open)

    def _finish_open(self, document_id: str | None) -> None:
        if document_id:
            self.store.select(document_id)
            self._load_active()

    def action_rename_document(self) -> None:
        self.push_screen(NameScreen("Rename document", self.store.active.title), self._finish_rename)

    def _finish_rename(self, title: str | None) -> None:
        if title:
            self.store.rename(title)
            self._update_status()

    def action_clear_document(self) -> None:
        self.push_screen(ConfirmScreen(f"Clear '{self.store.active.title}'? A revision will be kept."), self._finish_clear)

    def _finish_clear(self, confirmed: bool) -> None:
        if confirmed:
            self._save(True)
            self.editor.text = ""
            self._save()
            self.message.update("Document cleared; previous text retained in revisions")

    def action_shutdown(self) -> None:
        self.push_screen(ConfirmScreen("Save and power off the appliance?"), self._finish_shutdown)

    def _finish_shutdown(self, confirmed: bool) -> None:
        if confirmed:
            self._save(True)
            subprocess.run(["sync"], check=False)
            result = subprocess.run(["sudo", "-n", "/usr/bin/systemctl", "poweroff"], capture_output=True)
            if result.returncode:
                self.message.update("Power-off permission failed; document is safely saved")

    def get_word_under_cursor(self) -> str | None:
        text = self.editor.text
        row, column = self.editor.cursor_location
        lines = text.splitlines(keepends=True)
        if row >= len(lines):
            return None
        cursor = sum(len(lines[index]) for index in range(row)) + column
        left, right = re.search(r"[A-Za-z']+$", text[:cursor]), re.match(r"^[A-Za-z']+", text[cursor:])
        word = (left.group() if left else "") + (right.group() if right else "")
        return word or None

    def action_spell_check(self) -> None:
        word = self.get_word_under_cursor()
        if not word:
            self.message.update("No word at cursor")
        elif word.lower() in self.spell:
            self.message.update(f"'{word}' is in the dictionary")
        else:
            self.message.update(f"{word} → {self.spell.correction(word) or 'no suggestion'}")

    def action_export_usb(self) -> None:
        self._save()
        try:
            result = subprocess.run(["lsblk", "-Jpo", "NAME,TYPE,RM"], capture_output=True, text=True, check=True)
            devices = [child["name"] for disk in json.loads(result.stdout)["blockdevices"] for child in disk.get("children", []) if child.get("type") == "part" and child.get("rm")]
        except (subprocess.SubprocessError, KeyError, TypeError, json.JSONDecodeError):
            devices = []
        if len(devices) != 1:
            self.message.update("Insert exactly one USB drive" if not devices else "Multiple USB drives detected")
            return
        mounted = subprocess.run(["udisksctl", "mount", "-b", devices[0], "--no-user-interaction"], capture_output=True, text=True)
        match = re.search(r" at (.+?)\.?\s*$", mounted.stdout)
        if mounted.returncode or not match:
            self.message.update("USB mount failed")
            return
        mount = Path(match.group(1).rstrip("."))
        try:
            destination = mount / "Typewriter"
            destination.mkdir(exist_ok=True)
            manifest, used = [], set()
            for document in self.store.ordered():
                base, counter = safe_filename(document.title), 2
                name = base
                while name.lower() in used:
                    name, counter = f"{base} ({counter})", counter + 1
                used.add(name.lower())
                (destination / f"{name}.txt").write_text(self.store.read(document.id), encoding="utf-8")
                manifest.append({"id": document.id, "title": document.title, "file": f"{name}.txt"})
            (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            subprocess.run(["sync"], check=False)
            self.message.update(f"Exported {len(manifest)} documents to USB")
        except OSError as error:
            self.message.update(f"USB export failed: {error.strerror}")
        finally:
            subprocess.run(["udisksctl", "unmount", "-b", devices[0], "--no-user-interaction"], capture_output=True)

    def action_publish_google(self) -> None:
        self._save()
        try:
            publisher = GooglePublisher.from_rclone("gdrive")
            file_id = publisher.publish(
                self.store.active.title,
                self.editor.text,
                self.store.active.google_file_id,
                self.store.active.id,
            )
            self.store.set_google_file_id(file_id)
            self.message.update(f"Published '{self.store.active.title}' to Google Docs")
        except Exception as error:
            self.log.error("Google publish failed", error)
            self.message.update(f"Google publish failed: {type(error).__name__}")

    def _detect_battery(self) -> None:
        if POWER_SUPPLY_PATH.exists():
            self.battery_path = next((item for item in POWER_SUPPLY_PATH.iterdir() if item.name.startswith("BAT")), None)

    def _update_battery(self) -> None:
        try:
            if self.battery_path:
                self.battery_percent = (self.battery_path / "capacity").read_text().strip()
                self.battery_status = (self.battery_path / "status").read_text().strip()
                self._update_status()
        except OSError:
            self.battery_percent = self.battery_status = None


if __name__ == "__main__":
    TypewriterApp().run()
