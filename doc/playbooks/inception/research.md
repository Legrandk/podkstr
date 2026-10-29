
# Podkstr — CLI Podcast Player

## Overview

A terminal-based podcast player that fetches, lists, and plays podcast episodes from configured sources. The initial sources are RTVE (Spanish public radio) podcast feeds. Users can browse episodes, play them, download them, and manage favorites — all from the CLI.

---

## Tech Stack

**Language: Python**

Python is the best fit here because:
- `rich` provides a polished TUI with tables, panels, progress bars, and images (via `rich-pixels` or `chafa`)
- `feedparser` handles RSS/Atom podcast feeds reliably
- `mpv` (via subprocess or `python-mpv`) is the best open-source audio player for podcasts; it supports streaming URLs directly
- `requests` / `httpx` for HTTP
- `sqlite3` (stdlib) for persisting favorites and download state locally

**Key dependencies:**
- `rich` — terminal UI rendering
- `feedparser` — RSS feed parsing
- `mpv` (system binary) — audio playback
- `httpx` — async HTTP for fetching feeds
- `click` or `textual` — CLI entrypoint / TUI framework

> Alternative: Use `textual` (by the makers of `rich`) as the full TUI framework for a more interactive, keyboard-driven app. Worth evaluating.

---

## Podcast Sources

Initial sources (RTVE):

**RTVE RSS feed format:** `http://www.rtve.es/api/programas/{program_id}/audios.rss`

Each RTVE show page has a share button that exposes the RSS URL, which follows the pattern above. The program ID must be looked up per show by visiting the page and using the share/RSS option.

| Name | Page URL | RSS Feed |
|------|----------|----------|
| 180 Grados | https://www.rtve.es/play/audios/180-grados/ | http://www.rtve.es/api/programas/22270/audios.rss |
| Nanana | https://www.rtve.es/play/audios/nanana/ | http://www.rtve.es/api/programas/77850/audios.rss |
| Como Lo Oyes | https://www.rtve.es/play/audios/como-lo-oyes/ | http://www.rtve.es/api/programas/22290/audios.rss |
| Bandeja de Entrada de Radio 3 | https://www.rtve.es/play/audios/bandeja-de-entrada-de-radio-3/ | http://www.rtve.es/api/programas/140591/audios.rss |
| Turbo 3 | https://www.rtve.es/play/audios/turbo-3/ | http://www.rtve.es/api/programas/60890/audios.rss |
| Cuando los Elefantes Suenan con la Música | https://www.rtve.es/play/audios/cuando-los-elefantes-suenan-con-la-musica/ | http://www.rtve.es/api/programas/1919/audios.rss |
| Videodrome | https://www.rtve.es/play/audios/videodrome/ | http://www.rtve.es/api/programas/20220/audios.rss |

> RSS URLs need to be collected for each show (visit the page, click the share icon, copy the RSS link). Once collected they go directly into `sources.json`.

Sources are stored in a config file (JSON or TOML) so new ones can be added without touching the code.

---

## Features

### 1. Browse Sources
- On launch, display a list of configured podcast sources
- User selects a source to view its episodes

### 2. Episode List
- Display episodes for the selected source in a table: title, date, duration
- Ordered from most recent to oldest
- Paginate when there are many episodes (configurable page size, e.g. 20 per page)
- Show source metadata (name, description, cover image if terminal supports it)

### 3. Playback
- User selects an episode to play
- Audio streams directly via `mpv` (no need to download first)
- While playing, show a visual indicator: progress bar with current position / total duration, episode title, playback controls hint
- Support basic controls: pause/resume, seek forward/back, stop

### 4. Favorites
- User can mark/unmark any episode as a favorite from the episode list
- Filter view to show only favorited episodes
- Favorites are persisted locally (SQLite)

### 5. Download
- User can select one or more episodes for download
- Downloads are saved to a configurable local directory
- Show download progress
- Track which episodes have been downloaded (persisted in SQLite)

---

## Architecture

```
podkstr/
├── main.py                  # Entrypoint
├── config.py                # Load sources from config file
├── sources.json             # Podcast source definitions
├── fetcher.py               # Fetch and parse RSS/API feeds
├── player.py                # mpv playback wrapper
├── downloader.py            # Episode download logic
├── db.py                    # SQLite persistence (favorites, downloads)
├── ui/
│   ├── source_list.py       # Source selection view
│   ├── episode_list.py      # Episode list + pagination view
│   └── player_bar.py        # Playback status bar
└── requirements.txt
```

---

## Tasks

### Phase 0 — Research (Blocker)
- [x] Investigate RTVE feed URLs: standard RSS feeds exist at `http://www.rtve.es/api/programas/{id}/audios.rss` — no scraping needed, `feedparser` works directly
- [x] Collect RSS URLs for all initial sources — all 7 feeds confirmed
- [x] Confirm audio stream URLs from the RSS `<enclosure>` tags are directly playable by `mpv` — see findings below
- [x] Decide between `click` + `rich` (simpler) vs `textual` (richer TUI) — **decision: `textual`** (see rationale below)

### Phases 1–5

Moved to `plan.md`.

---

## Phase 0 Findings

### Audio URL resolution

The RSS `<enclosure>` tags contain URLs in the form `https://ztnr.rtve.es/ztnr/{id}.mp3`. These are **not** direct public links — they go through a 3-step redirect chain:

1. `https://ztnr.rtve.es/ztnr/{id}.mp3` → requires `Referer: https://www.rtve.es/` header, returns 302
2. → `https://rtve-mediavod-lote3.rtve.es/resources/.../file.mp3?idasset={id}` → returns 302
3. → Same URL with a time-limited `download-token` query param → returns **200 audio/mpeg**

The final file is a standard MP3 (confirmed: `content-type: audio/mpeg`, `accept-ranges: bytes`).

**Implication for playback:** `mpv` handles HTTP redirects and custom headers natively. Invoking it as:
```
mpv --referrer="https://www.rtve.es/" <enclosure_url>
```
should resolve the full chain transparently. `mpv` must be installed (`brew install mpv`).

**Note:** `afplay` (macOS built-in) only plays local files — not usable for streaming. `mpv` is the right tool.

### TUI framework decision: `textual`

Given the feature set — navigable episode list, pagination, live playback bar, favorites toggle, download progress — `textual` is the right choice over `click` + `rich`:

- `textual` is event-driven and keyboard-first, matching the interaction model of a podcast player
- It handles layout (header, body, footer/player bar) natively via CSS-like composition
- Reactive state makes updating the playback progress bar and favorites indicator straightforward
- `click` + `rich` would require manually reimplementing focus, keyboard nav, and screen updates — essentially rebuilding what `textual` already provides

---

## Open Questions

1. ~~**RTVE RSS feeds**: Do they exist and are they public?~~ **Resolved**: Standard RSS feeds at `http://www.rtve.es/api/programas/{id}/audios.rss`. No scraping needed.
2. ~~**Audio stream URLs playable by mpv?**~~ **Resolved**: Yes — URLs resolve to standard MP3s via a 3-step redirect chain. `mpv --referrer="https://www.rtve.es/" <url>` handles it transparently.
3. ~~**`textual` vs `rich`**~~ **Resolved**: Using `textual`.
4. ~~**Playback controls**~~ **Resolved**: Start with simple subprocess (`subprocess.Popen`) to get playback working quickly. Migrate to `mpv` IPC socket when implementing the in-app playback bar (pause, seek, progress). See Phase 0 findings for details.
5. ~~**Image rendering**~~ **Resolved**: Show cover art using `chafa` (CLI tool, `brew install chafa`). It auto-detects the terminal protocol — iTerm2 inline images on iTerm2, sixel on Tabby, unicode block fallback on Alacritty. Covers all three target terminals with graceful degradation. Fetch the image URL from `<itunes:image>` in the RSS, download to a temp file, render with `chafa`.
