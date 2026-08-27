from __future__ import annotations

import json
import os
import re
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


def data_directory() -> Path:
    override = os.environ.get("TYPEWRITER_DATA_DIR")
    return Path(override).expanduser() if override else Path.home() / ".local" / "share" / "typewriter"


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def safe_filename(title: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "", title).strip(" .")
    return (cleaned or "Untitled")[:100]


@dataclass
class Document:
    id: str
    title: str
    created_at: float
    modified_at: float
    google_file_id: str | None = None


class DocumentStore:
    def __init__(self, root: Path | None = None, legacy_note: Path | None = None):
        self.root = root or data_directory()
        self.documents_dir = self.root / "documents"
        self.revisions_dir = self.root / "revisions"
        self.exports_dir = self.root / "exports"
        self.library_path = self.root / "library.json"
        for directory in (self.documents_dir, self.revisions_dir, self.exports_dir):
            directory.mkdir(parents=True, exist_ok=True)
        self.documents: dict[str, Document] = {}
        self.active_id: str | None = None
        self._load()
        if not self.documents:
            self._migrate_or_create(legacy_note)

    def _load(self) -> None:
        if self.library_path.exists():
            payload = json.loads(self.library_path.read_text(encoding="utf-8"))
            self.documents = {item["id"]: Document(**item) for item in payload.get("documents", [])}
            self.active_id = payload.get("active_id")
        if self.active_id not in self.documents:
            self.active_id = next(iter(self.documents), None)

    def _persist_library(self) -> None:
        payload = {"version": 1, "active_id": self.active_id,
                   "documents": [asdict(item) for item in self.documents.values()]}
        atomic_write(self.library_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def _migrate_or_create(self, legacy_note: Path | None) -> None:
        content, title = "", "Untitled"
        if legacy_note and legacy_note.exists():
            content, title = legacy_note.read_text(encoding="utf-8"), "Imported Note"
        document = self.create(title, content)
        if legacy_note and legacy_note.exists():
            migrated = legacy_note.with_suffix(legacy_note.suffix + ".migrated")
            if not migrated.exists():
                atomic_write(migrated, content)
        self.active_id = document.id
        self._persist_library()

    @property
    def active(self) -> Document:
        if not self.active_id or self.active_id not in self.documents:
            raise RuntimeError("No active document")
        return self.documents[self.active_id]

    def path_for(self, document_id: str) -> Path:
        return self.documents_dir / f"{document_id}.txt"

    def read(self, document_id: str | None = None) -> str:
        target = document_id or self.active.id
        path = self.path_for(target)
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def save(self, content: str, *, make_revision: bool = False) -> None:
        document = self.active
        atomic_write(self.path_for(document.id), content)
        document.modified_at = time.time()
        if make_revision:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            atomic_write(self.revisions_dir / document.id / f"{stamp}.txt", content)
        self._persist_library()

    def create(self, title: str = "Untitled", content: str = "") -> Document:
        now = time.time()
        document = Document(uuid.uuid4().hex, title.strip() or "Untitled", now, now)
        self.documents[document.id] = document
        self.active_id = document.id
        atomic_write(self.path_for(document.id), content)
        self._persist_library()
        return document

    def select(self, document_id: str) -> Document:
        if document_id not in self.documents:
            raise KeyError(document_id)
        self.active_id = document_id
        self._persist_library()
        return self.active

    def rename(self, title: str) -> None:
        self.active.title = title.strip() or "Untitled"
        self.active.modified_at = time.time()
        self._persist_library()

    def set_google_file_id(self, file_id: str) -> None:
        self.active.google_file_id = file_id
        self._persist_library()

    def ordered(self) -> list[Document]:
        return sorted(self.documents.values(), key=lambda item: item.modified_at, reverse=True)
