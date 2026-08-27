# Typewriter Appliance

A distraction-free Debian writing appliance that boots directly into a terminal-based text editor.

The current prototype provides automatic saving, battery status, spell checking, USB export, Google Drive export through `rclone`, and keyboard-controlled shutdown. The longer-term goal is to pair a low-memory client with an optional self-hosted Kubernetes language service that preserves a writer's individual style instead of normalizing every sentence into conventional professional prose.

> **Project status:** Early prototype. The appliance works on its original Debian laptop, but installation, permissions, destructive-action safeguards, and the cross-platform AI backend are still under development.

## Current features

- Full-screen terminal interface built with [Textual](https://textual.textualize.io/)
- Automatic saving to `~/.typewriter/note.txt`
- Word count and battery status
- Word-level spell checking
- USB export
- Google Drive text-file export using `rclone`
- Keyboard-controlled shutdown
- systemd-based startup on the original appliance
- Sanitized system and hardware snapshots under `docs/`

## Controls

| Shortcut | Action |
| --- | --- |
| `Ctrl+G` | Check the word under the cursor |
| `Ctrl+E` | Export the current note to USB |
| `Ctrl+D` | Upload the current note to Google Drive |
| `Ctrl+K` | Clear the current note |
| `Ctrl+X` | Save, exit, and power off |

### Safety warning

In the current prototype, `Ctrl+K` clears the note immediately and `Ctrl+X` requests an immediate shutdown. Use it only on a test appliance and keep external backups. Confirmation prompts and automatic revision recovery are planned before a stable release.

## Current architecture

```text
Debian appliance
├── systemd service on tty1
├── Python virtual environment
├── Textual editor
├── local note storage
├── pyspellchecker
├── removable USB export
└── rclone Google Drive export
```

The original reference machine runs Debian 13 on an Intel Core i7-7500U system. Captured system information is available in [`docs/`](docs/).

## Repository layout

```text
.
├── app.py                  # Current Textual application
├── requirements-full.txt   # Frozen prototype environment
├── systemd/
│   └── typewriter.service  # Captured service definition
└── docs/                   # Sanitized system and hardware information
```

## Run the prototype manually

The safest current way to evaluate the application is manually from a terminal rather than installing the captured systemd unit.

### Requirements

- Debian or another modern Linux distribution
- Python 3.10 or newer
- A terminal supporting Textual
- Optional: `rclone` for Google Drive export
- Optional: mount permissions for USB export

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

The repository does not contain an `rclone` configuration, Wi-Fi credentials, private keys, personal notes, or other secrets.

## Known limitations

- The captured systemd unit still contains the original machine's `/root/.typewriter` paths and root execution model.
- Its `[unit]` header must be corrected to `[Unit]`; current logs show that systemd ignored the lowercase section.
- The application performs privileged USB mounting and shutdown operations directly.
- Clear and shutdown actions do not yet require confirmation.
- Saving rewrites the note frequently instead of using atomic revisions.
- USB export selects the first removable partition and needs safer device handling.
- “Save to Google Docs” currently uploads a text file to Google Drive rather than creating a native Google Docs document.
- Installation is not yet reproducible across machines.
- There are no automated tests or packaged releases yet.

## Planned architecture

The intended platform separates the constrained writing appliance from expensive language-model inference:

```text
Low-memory client
Debian / Raspberry Pi
        │
        │ authenticated request
        ▼
User-owned backend
Windows / macOS / Linux
        │
        ▼
K3s or compatible local Kubernetes
├── request gateway
├── style-preserving grammar API
├── LLM inference service
├── ephemeral document-analysis Jobs
└── health and resource monitoring
```

The client remains useful offline. Kubernetes and the model run on a modern computer supplied by the user.

## Style-preserving language assistance

The planned language service is deliberately different from a conventional “professional tone” grammar checker. It should distinguish probable errors from intentional stylistic choices such as:

- Sentence fragments used for rhythm
- Long or recursive sentences
- Repetition for emphasis
- Sparse or unconventional punctuation
- Dialect and colloquial language
- Stream-of-consciousness structures

The service will return structured, minimal suggestions and will never silently rewrite the document.

```json
{
  "assessment": "probable_error",
  "confidence": 0.97,
  "original": "The characters motivation changes.",
  "suggestion": "The character's motivation changes.",
  "reason": "A possessive apostrophe appears to be missing."
}
```

Users will be able to accept, reject, or permanently preserve a construction in their personal style profile.

## Installation goal

The eventual user experience should require no Kubernetes knowledge:

```text
Modern computer:
    typewriter-server install
    → hardware detection
    → local Kubernetes setup
    → model recommendation
    → service deployment
    → pairing code

Writing appliance:
    typewriter-client install
    → enter pairing code
    → write offline or request private AI review
```

Linux backends can use native K3s. Windows and macOS will use a managed Linux/Kubernetes layer. CPU inference will be the portable baseline, with GPU acceleration treated as an optional platform-specific capability.

## Roadmap

### Appliance stabilization

- [ ] Correct and harden the systemd service
- [ ] Run the editor as an unprivileged user
- [ ] Implement atomic saving and timestamped revisions
- [ ] Add confirmation for clear and shutdown
- [ ] Make USB selection, verification, and unmounting safer
- [ ] Add installation, upgrade, rollback, and uninstall scripts
- [ ] Add automated tests

### Language service

- [ ] Add asynchronous paragraph review to the client
- [ ] Define versioned request and response schemas
- [ ] Run a local `llama.cpp` inference service
- [ ] Add offline fallback and request timeouts
- [ ] Add editable style profiles
- [ ] Build a style-preservation evaluation suite

### Kubernetes backend

- [ ] Containerize the grammar API and inference server
- [ ] Package the backend as a Helm chart
- [ ] Add probes, resource limits, and non-root security contexts
- [ ] Add node-aware model placement
- [ ] Add ephemeral Jobs for longer document analysis
- [ ] Add metrics, failure tests, and rollback
- [ ] Produce AMD64 and ARM64 images

### Open platform

- [ ] Define a versioned writing-service manifest
- [ ] Provide a reference grammar service
- [ ] Add manifest validation and contribution documentation
- [ ] Create a GitHub-hosted service catalog
- [ ] Build guided installers for Linux, Windows, and macOS
- [ ] Publish a reproducible 1 GB Raspberry Pi reference appliance

## Design principles

1. Writing must continue when the network or AI backend is unavailable.
2. The appliance should remain below a documented memory budget.
3. No model may modify a document without explicit user approval.
4. Private writing must not appear in logs.
5. Personal style preferences must be inspectable, exportable, and deletable.
6. Users provide their own compute; the project does not require a central paid service.
7. Advanced infrastructure should remain invisible to ordinary users.
8. Every release should be reproducible and recoverable.

## Contributing

The project is still defining its stable interfaces. Bug reports, hardware results, installation notes, accessibility feedback, and style-preservation examples are welcome through GitHub issues.

Please do not commit Wi-Fi credentials, `rclone` configuration, API tokens, SSH keys, personal notes, Kubernetes credentials, or model files without redistribution permission.

## License

A project license has not yet been selected. Until one is added, the source is publicly viewable but should not be assumed to grant permission for redistribution or derivative use.
