# Zombieland

[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) ![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black) [![Release](https://img.shields.io/github/v/release/infinition/Zombieland?style=flat)](https://github.com/infinition/Zombieland/releases) [![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=flat&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/infinition)

A browser-based C2 dashboard frontend. Ships as a single HTML file with mock agent data and localStorage persistence so the UI can be explored and extended without a backend.

![Zombieland](https://github.com/user-attachments/assets/a160cd87-1661-44f7-9e44-53f804c229d5)

<img width="1117" height="1235" alt="Zombieland interface" src="https://github.com/user-attachments/assets/eb899d81-eafb-43a5-9514-8dd33b929903" />

The server and agent components are under active development and will be added in a future release.

For educational and authorized penetration testing research only.

---

## Features

**Agent management (mock)**
- Grid and list views with filters: OS (Linux / Windows / macOS), status (online / idle / busy / offline), free-text search.
- Multi-select, Select All / Clear, OS icons, status-colored card borders.

**Global console**
- Broadcast commands to selected agents (simulated).
- Prompt-style input with preset-based suggestions and Tab completion.
- TX/RX log stream with auto-scroll, Clear, and Fullscreen toggle.

**Presets and logs**
- Command presets: add/remove in Settings, insert from the Presets overlay.
- Session logs panel with one-click clear.

**UI**
- Panels arranged in rows with optional side-by-side splits.
- Compact mode on narrow widths.
- Hacker Mode: retro neon glow, scan lines, halo effects.
- Configurable server name, role, and app icon.

---

## Running

Open `zombieland.html` directly in a browser, or serve the folder statically:

```bash
npx serve .
```

CDN dependencies (Tailwind CSS, Lucide icons) require an internet connection unless vendored locally.

---

## Roadmap

- Backend API and cross-platform agents (Linux / Windows / macOS)
- Command preset categories and variable support
- Import/Export for presets and layouts
- RBAC and multi-user support

---

## Star History

<a href="https://www.star-history.com/?repos=infinition%2FZombieland&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=infinition/Zombieland&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=infinition/Zombieland&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=infinition/Zombieland&type=date&legend=top-left" />
 </picture>
</a>

---

## License

MIT. See [LICENSE](LICENSE).
