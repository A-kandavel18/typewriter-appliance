from __future__ import annotations

import html
import subprocess
import tempfile
import zipfile
from pathlib import Path

from typewriter_core import safe_filename


def make_docx(path: Path, content: str) -> None:
    paragraphs = content.splitlines() or [""]
    body = "".join(
        f'<w:p><w:r><w:t xml:space="preserve">{html.escape(line)}</w:t></w:r></w:p>'
        for line in paragraphs
    )
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    relationships = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{body}<w:sectPr/></w:body></w:document>"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document)


class GooglePublisher:
    def __init__(self, remote: str):
        self.remote = remote

    @classmethod
    def from_rclone(cls, remote: str) -> "GooglePublisher":
        result = subprocess.run(["rclone", "about", f"{remote}:"], capture_output=True,
                                text=True, timeout=90)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "Google Drive is unavailable")
        return cls(remote)

    def publish(self, title: str, content: str, remote_path: str | None = None,
                document_id: str | None = None) -> str:
        suffix = f"--{document_id[:8]}" if document_id else ""
        destination = remote_path or f"Typewriter/{safe_filename(title)}{suffix}.docx"
        with tempfile.TemporaryDirectory() as folder:
            local = Path(folder) / "document.docx"
            make_docx(local, content)
            result = subprocess.run(
                ["rclone", "copyto", str(local), f"{self.remote}:{destination}",
                 "--drive-import-formats", "docx"],
                capture_output=True, text=True, timeout=120,
            )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "Google Docs upload failed")
        return destination
