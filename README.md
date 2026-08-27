# Typewriter Appliance

A distraction-free Debian writing appliance that boots directly into a full-screen terminal text editor.

The project turns a laptop into a dedicated writing machine. It stores a single continuously saved note, exposes only a small set of keyboard controls, and can export writing to removable storage or Google Drive.

## Features

- Full-screen terminal interface built with [Textual](https://textual.textualize.io/)
- Automatic saving to `~/.typewriter/note.txt`
- Persistent writing between restarts
- Live word count
- Battery percentage and charging status
- Word-level spell checking
- USB export
- Google Drive text-file export through `rclone`
- Keyboard-controlled shutdown
- Automatic startup on TTY1 through systemd
- No desktop environment required

## Controls

| Shortcut | Action |
| --- | --- |
| `Ctrl+G` | Check the word under the cursor |
| `Ctrl+E` | Export the current note to USB |
| `Ctrl+D` | Upload the current note to Google Drive |
| `Ctrl+K` | Clear the current note |
| `Ctrl+X` | Save, exit, and power off |

## How it works

```text
Debian boots
    ↓
systemd starts typewriter.service on TTY1
    ↓
Python virtual environment runs app.py
    ↓
Textual presents the full-screen editor
    ↓
The note is continuously saved to ~/.typewriter/note.txt
```

The application runs directly in the Linux console. The original appliance uses a systemd service that claims `/dev/tty1` and starts the Python application from `/root/.typewriter`.

## Repository layout

```text
.
├── app.py                  # Textual writing application
├── requirements-full.txt   # Frozen Python environment
├── systemd/
│   └── typewriter.service  # Captured systemd service
└── docs/                   # Sanitized system and hardware information
```

## Run manually

Manual execution is the safest way to evaluate the current code without changing a machine's boot configuration.

### Requirements

- Debian or another modern Linux distribution
- Python 3.10 or newer
- A compatible terminal
- Optional: `rclone` for Google Drive export
- Optional: permission to mount removable storage for USB export

### Setup

```bash
git clone https://github.com/A-kandavel18/typewriter-appliance.git
cd typewriter-appliance

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-full.txt

python app.py
```

The note is created automatically at:

```text
~/.typewriter/note.txt
```

## USB export

Pressing `Ctrl+E`:

1. Searches for the first removable block-device partition.
2. Mounts it at `/mnt/usb`.
3. Copies `note.txt` to the mounted device.
4. Calls `sync`.
5. Unmounts the device.

The application must have sufficient permission to mount and unmount the device.

## Google Drive export

Pressing `Ctrl+D` writes the current text to a temporary file and runs:

```bash
rclone copyto TEMPORARY_FILE gdrive:Typewriter/TypewriterDoc.txt
```

This requires a separately configured `rclone` remote named `gdrive`. The repository does not include that configuration or any account credentials.

This feature uploads a plain-text file to Google Drive; it does not create a native Google Docs document.

## Spell checking

Pressing `Ctrl+G` checks the word under the cursor using `pyspellchecker`. The result or suggested spelling appears in the message bar without automatically changing the document.

## Reference system

The captured appliance runs:

- Debian GNU/Linux 13
- Linux on x86-64
- Intel Core i7-7500U
- 12 GiB of installed RAM
- A 238.5 GB storage device
- Python inside a dedicated virtual environment
- The application as a system service on TTY1

Additional sanitized information is available under [`docs/`](docs/), including CPU, memory, storage, kernel, service state, and boot configuration snapshots.

## Important safety notes

- `Ctrl+K` immediately clears the editor and overwrites the saved note.
- `Ctrl+X` saves the note and requests an immediate system power-off.
- The captured service runs the application as `root`.
- USB export mounts the first removable partition it finds.
- Keep external backups while using the prototype.
- Test the application manually before enabling it as a boot service on another computer.

## Known limitations

- The captured systemd unit contains paths specific to the original machine.
- Its `[unit]` header is lowercase; systemd expects `[Unit]` and reports that it ignored the existing section.
- Clear and shutdown actions do not ask for confirmation.
- The note is rewritten frequently rather than saved through an atomic replacement operation.
- There is no built-in revision history or deleted-note recovery.
- USB selection is ambiguous when multiple removable partitions are connected.
- USB and shutdown operations depend on elevated system permissions.
- There is no automated installer, test suite, or packaged release.
- The service definition should not be installed unchanged on another system.

## Sensitive information

The repository intentionally excludes:

- Personal notes
- Wi-Fi credentials
- `rclone` configuration
- API tokens
- SSH keys
- Environment files
- Other machine credentials

See [`.gitignore`](.gitignore) for the current exclusions.

## License

A license has not yet been selected. Until one is added, the source is publicly viewable but should not be assumed to grant permission for redistribution or derivative use.
