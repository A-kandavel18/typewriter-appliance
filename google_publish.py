from __future__ import annotations

import html
import subprocess
import tempfile
import zipfile
from pathlib import Path

from typewriter_core import safe_filename


def _runs(line: str) -> str:
    pieces = line.split("\t")
    runs: list[str] = []
    for index, piece in enumerate(pieces):
        if index:
            runs.append("<w:r><w:tab/></w:r>")
        runs.append(f'<w:r><w:t xml:space="preserve">{html.escape(piece)}</w:t></w:r>')
    return "".join(runs)


def make_docx(path: Path, content: str, title: str | None = None) -> None:
    paragraphs = content.splitlines() or [""]
    title_paragraph = ""
    if title:
        title_paragraph = (
            '<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr>'
            f'<w:r><w:t xml:space="preserve">{html.escape(title)}</w:t></w:r></w:p>'
        )
    body = title_paragraph + "".join(f"<w:p>{_runs(line)}</w:p>" for line in paragraphs)
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/fontTable.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"/>
<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
</Types>"""
    relationships = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    document_relationships = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable" Target="fontTable.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
</Relationships>"""
    styles = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Book Antiqua" w:hAnsi="Book Antiqua" w:eastAsia="Book Antiqua" w:cs="Book Antiqua"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:rPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="Book Antiqua" w:hAnsi="Book Antiqua"/><w:sz w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:jc w:val="center"/><w:spacing w:after="240"/></w:pPr><w:rPr><w:rFonts w:ascii="Book Antiqua" w:hAnsi="Book Antiqua"/><w:b/><w:sz w:val="28"/></w:rPr></w:style>
</w:styles>"""
    font_table = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:fonts xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:font w:name="Book Antiqua"><w:family w:val="roman"/><w:pitch w:val="variable"/></w:font></w:fonts>"""
    settings = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:defaultTabStop w:val="720"/></w:settings>"""
    document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{body}<w:sectPr><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document)
        archive.writestr("word/_rels/document.xml.rels", document_relationships)
        archive.writestr("word/styles.xml", styles)
        archive.writestr("word/fontTable.xml", font_table)
        archive.writestr("word/settings.xml", settings)


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
            make_docx(local, content, title)
            result = subprocess.run(
                ["rclone", "copyto", str(local), f"{self.remote}:{destination}",
                 "--drive-import-formats", "docx"],
                capture_output=True, text=True, timeout=120,
            )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "Google Docs upload failed")
        return destination
