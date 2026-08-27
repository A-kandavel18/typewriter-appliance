# Typewriter Appliance

A distraction-free Debian writing appliance that boots directly into a full-screen terminal editor.

The application provides a small, keyboard-controlled writing environment with local document management, crash-resistant saving, revision snapshots, removable-drive export, spell checking, and Google Docs publishing. No desktop environment is required.

## Features

- Full-screen terminal interface built with [Textual](https://textual.textualize.io/)
- Multiple named documents with a keyboard-controlled library
- Atomic autosaving only when text changes
- Five-minute recovery revisions and manual save revisions
- Migration of the original `~/.typewriter/note.txt`
- Live word count, battery status, and word-level spell checking
- Export of every document to a removable drive
- Conversion and publishing to editable Google documents through `rclone`
- Confirmation before clearing a document or powering off
- Automatic startup on TTY1 through systemd
- Operation as the unprivileged `writer` user

## Controls

| Shortcut | Action |
| --- | --- |
| `Ctrl+N` | Create a document |
| `Ctrl+O` | Open the document library |
| `Ctrl+S` | Save and create a revision |
| `Ctrl+R` | Rename the current document |
| `Ctrl+G` | Check the word under the cursor |
| `Ctrl+E` | Export all documents to USB |
| `Ctrl+D` | Publish or update the current Google document |
| `Ctrl+K` | Confirm and clear the current document |
| `Ctrl+X` | Confirm, save, and power off |

## Storage

Application data is stored under:

```text
~/.local/share/typewriter/
├── documents/       # UTF-8 text, one file per document ID
├── revisions/       # Timestamped recovery snapshots
├── exports/
└── library.json     # Titles, timestamps, active document, Google paths
```

Set `TYPEWRITER_DATA_DIR` to use an isolated location during testing. On first launch, the application can import the original `~/.typewriter/note.txt` as **Imported Note** and retain `note.txt.migrated` as an additional copy.

## Repository layout

```text
.
├── app.py                    # Textual interface and appliance actions
├── typewriter_core.py        # Document storage and atomic persistence
├── google_publish.py         # Editable Google-document publishing
├── requirements-full.txt     # Pinned Python dependencies
├── tests/                    # Storage, document, and UI tests
├── systemd/
│   ├── typewriter.service    # Non-root TTY1 service
│   └── typewriter-poweroff   # Narrow shutdown sudoers rule
└── docs/                     # Sanitized reference-system information
```

## Run manually

```bash
git clone https://github.com/A-kandavel18/typewriter-appliance.git
cd typewriter-appliance
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-full.txt
python app.py
```

Run the tests with:

```bash
python -m unittest discover -s tests -v
```

## USB export

`Ctrl+E` requires exactly one removable drive. The application mounts it through `udisksctl`, creates a `Typewriter` directory, writes every document with a safe human-readable filename, adds `manifest.json`, flushes pending writes, and unmounts the device. It never formats a drive.

## Google Docs publishing

Google publishing requires an `rclone` Drive remote named `gdrive`. The application creates a small DOCX representation locally and asks the Drive backend to import it as an editable Google document under `Typewriter/`. The stable remote path is retained per local document so later publishes update the same destination.

The repository never contains the `rclone` configuration, OAuth token, or other account credentials.

## systemd service

The supplied unit runs `/opt/typewriter/app.py` as `writer` on `/dev/tty1`. Documents remain under `/home/writer`, while application code and its virtual environment live under `/opt/typewriter`.

Only shutdown needs elevation. `systemd/typewriter-poweroff` permits `writer` to execute exactly `/usr/bin/systemctl poweroff`; it does not grant unrestricted passwordless sudo access.

Validate the unit and sudoers rule before installation:

```bash
sudo systemd-analyze verify systemd/typewriter.service
sudo visudo -cf systemd/typewriter-poweroff
```

## Reference system

The reference appliance uses Debian GNU/Linux 13 on x86-64 and runs the editor as a system service on TTY1. Sanitized CPU, memory, storage, kernel, service, and boot snapshots are available under [`docs/`](docs/).

## Safety and limitations

- Keep independent backups of important writing even though atomic saves and revisions are enabled.
- USB export intentionally refuses to choose when more than one removable drive is present.
- Google publishing requires network access and an authenticated `gdrive` remote.
- The program currently provides one-way publishing; edits made in Google Docs are not merged back locally.
- Revision snapshots are retained until manually archived or removed.
- A license has not yet been selected, so the source is viewable but no redistribution rights should be assumed.

## Sensitive information

Personal notes, Wi-Fi credentials, OAuth tokens, `rclone` configuration, SSH keys, and environment files are excluded from the repository.
