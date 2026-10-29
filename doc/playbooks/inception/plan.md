# Podkstr — Implementation Plan

## Prerequisites

Install system dependencies before starting:

```bash
brew install mpv chafa
```

Python dependencies (`requirements.txt`):

```
textual
feedparser
httpx
```

---

## Project Structure

```
podkstr/
├── main.py                  # Entrypoint — launches the Textual app
├── sources.json             # Podcast source definitions (name + RSS URL)
├── requirements.txt
├── podkstr/
│   ├── config.py            # Load/save sources from sources.json
│   ├── fetcher.py           # Fetch and parse RSS feeds
│   ├── player.py            # mpv subprocess wrapper
│   ├── downloader.py        # Episode download logic
│   ├── db.py                # SQLite persistence
│   ├── user_config.py       # User config (~/.config/podkstr/config.json)
│   └── ui/
│       ├── app.py           # Textual App class, screen routing
│       ├── source_screen.py # Source list screen
│       ├── episode_screen.py# Episode list screen (with pagination)
│       ├── player_bar.py    # Playback status widget (footer)
│       └── add_source_modal.py # Modal form to add a new source
├── tests/
│   ├── test_config.py       # Tests for config.py
│   ├── test_fetcher.py      # Tests for fetcher.py
│   ├── test_db.py           # Tests for db.py
│   ├── test_player.py       # Tests for player.py
│   ├── test_downloader.py   # Tests for downloader.py
│   ├── test_user_config.py  # Tests for user_config.py
│   └── ui/
│       ├── test_app.py      # Tests for app.py
│       ├── test_source_screen.py   # Tests for source_screen.py
│       ├── test_episode_screen.py  # Tests for episode_screen.py
│       └── test_player_bar.py      # Tests for player_bar.py
└── data/
    └── podkstr.db           # SQLite database (gitignored)
```

---

## Testing Policy

**Every module must have a corresponding test file.** Tests are written alongside each phase — not deferred to the end.

### Scope

- **Backend modules** (`config`, `fetcher`, `db`, `player`, `downloader`, `user_config`): full unit tests covering the public interface, happy paths, edge cases, and error cases.
- **UI modules** (`app`, screens, widgets): use Textual's headless `run_test` / `Pilot` API to test navigation, key bindings, and state changes without a real terminal.

### Test runner

```bash
pip install pytest pytest-asyncio
pytest tests/
```

Add `pytest` and `pytest-asyncio` to `requirements.txt`.

### Conventions

- Fixtures that produce fixed data are prefixed `fixture_`
- Helpers that build objects are prefixed `build_`
- Mocks/patches are set up per-test, not globally
- External I/O (network, filesystem, subprocesses) is always mocked in unit tests
- Tests that require network access are marked `@pytest.mark.integration` and skipped by default

---

## Phase 1 — Foundation ✅

Goal: data layer working end-to-end, no UI yet. Verifiable via Python REPL or simple print scripts.

### 1.1 Project scaffold ✅
### 1.2 `sources.json` ✅
### 1.3 `config.py` ✅
### 1.4 `fetcher.py` ✅
### 1.5 `db.py` ✅

## Phase 1.5 — Tests for Phase 1 modules ✅

- [x] Add `pytest` and `pytest-asyncio` to `requirements.txt`, set up `tests/` folder
- [x] `tests/test_config.py` — `load_sources`, `add_source`
- [x] `tests/test_fetcher.py` — `fetch_feed` parsing logic (mocked HTTP), `_extract_id`, `_parse_date`, HTML unescaping
- [x] `tests/test_db.py` — all DB functions against a temporary in-memory or temp-file database
- [x] `tests/test_player.py` — `is_mpv_available`, `play` (mock subprocess)
- [x] `tests/test_downloader.py` — `download` (mock httpx), filename sanitization
- [x] `tests/test_user_config.py` — defaults, loading, saving

---

## Phase 2 — Browse & Play

Goal: full navigable UI. User can browse sources, see episodes, and play one.

### 2.1 Textual app skeleton (`ui/app.py`)

- `PodkstrApp(App)` — main Textual app
- Two screens: `SourceScreen` and `EpisodeScreen`
- On launch: show `SourceScreen`
- Layout: main content area + persistent `PlayerBar` footer widget (initially hidden)

### 2.2 Source list screen (`ui/source_screen.py`)

- Shows a `ListView` of podcast sources loaded from `sources.json`
- Each item shows the source name
- Selecting a source pushes `EpisodeScreen` with that source's RSS URL
- Keybinding: `q` to quit

### 2.3 Episode list screen (`ui/episode_screen.py`)

On load:
1. Fetch the RSS feed for the selected source (`fetcher.fetch_feed`)
2. Show source metadata at the top: name, description, cover image (via `chafa`)
3. Show episodes in a `DataTable`: columns — `#`, title, date, duration, `[F]` favorite indicator, `[D]` downloaded indicator

Pagination:
- Show 20 episodes per page
- Keybindings: `n` next page, `p` previous page, page indicator in footer (e.g. `Page 1/5`)

Actions:
- `Enter` on an episode → play it (calls `player.play`)
- `f` on an episode → toggle favorite (updates DB, refreshes indicator)
- `d` on an episode → download it (calls `downloader.download`, updates DB)
- `F` (shift+f) → toggle filter: show all / show favorites only
- `Escape` → go back to source list

Cover image:
- Download the `image_url` to a temp file
- Call `chafa --size=20x10 <tempfile>` via subprocess and capture output
- Render the output as a `Static` widget above the episode table

### 2.4 `player.py`

```python
def play(audio_url: str) -> subprocess.Popen:
    return subprocess.Popen([
        "mpv",
        "--referrer=https://www.rtve.es/",
        "--no-video",
        audio_url
    ])
```

The app holds a reference to the process. Calling `process.terminate()` stops playback.

The `PlayerBar` footer widget shows the currently playing episode title and a `[stop]` hint. No progress bar in this phase — that requires IPC (Phase 5).

### 2.5 `PlayerBar` widget (`ui/player_bar.py`)

- A `Static` widget docked to the bottom of the screen
- Hidden when nothing is playing
- Shows: `▶ <episode title>  [s] stop`
- When the user presses `s`: terminate the mpv process, hide the bar

### 2.6 Tests for Phase 2 UI ✅

- [x] `tests/ui/test_app.py` — app starts, source screen is shown, stop playback action when nothing is playing
- [x] `tests/ui/test_source_screen.py` — source list renders all sources, selecting a source pushes `EpisodeScreen`, `a` opens the modal
- [x] `tests/ui/test_episode_screen.py` — episodes load, pagination works, `f` toggles favorite, `F` filters, `Escape` goes back
- [x] `tests/ui/test_player_bar.py` — `show` displays title, `hide` hides widget, title reactive update

---

## Phase 3 — Favorites & Downloads

Goal: favorites and downloads fully working end-to-end.

### 3.1 Favorites

- `f` key on an episode row calls `db.add_favorite` or `db.remove_favorite`
- The `[F]` column in the DataTable updates immediately (no full reload)
- `F` key toggles the view between all episodes and favorites-only
  - In favorites-only mode, the episode list is filtered to those whose `episode_id` is in `db.get_favorites(source_url)`
  - Show a visual indicator in the header: `Showing: Favorites` vs `Showing: All`

### 3.2 Downloads

`downloader.py`:

```python
async def download(episode: dict, dest_dir: str, progress_callback) -> str:
    # streams the file via httpx with a Referer header
    # calls progress_callback(bytes_downloaded, total_bytes) periodically
    # returns the local file path
```

- `dest_dir` defaults to `~/Downloads/podkstr/`
- Filename: `{episode_id} - {title}.mp3` (sanitized)
- Uses `httpx.AsyncClient` with `stream=True` to stream the download
- The `Referer: https://www.rtve.es/` header must be set (same redirect chain as playback)
- Progress shown via a `ProgressBar` widget in the episode row or a modal

In the episode list:
- `d` key on an episode triggers the download
- While downloading, show a progress indicator in the row
- Once done, `[D]` indicator appears permanently (persisted in DB)
- If already downloaded, `d` plays the local file instead of streaming

### 3.3 Tests for Phase 3 ✅

- [x] `tests/ui/test_episode_screen.py` — download action calls `downloader.download` and updates the `↓` cell; playing a downloaded episode uses the local path

---

## Phase 4 — Polish

### 4.1 Add new sources

- `a` keybinding on the source list screen opens a modal input form
- Fields: name, RSS URL
- On confirm: calls `config.add_source`, refreshes the source list

### 4.2 Error handling

- Feed fetch failure: show an error message in the episode screen instead of crashing
- Network timeout: `httpx` timeout set to 10s, show user-friendly message
- `mpv` not found: show install instructions (`brew install mpv`)
- `chafa` not found: skip image rendering silently, show source name only

### 4.3 User config

Config file at `~/.config/podkstr/config.json`:

```json
{
  "download_dir": "~/Downloads/podkstr",
  "page_size": 20
}
```

Loaded at startup with sensible defaults if not present.

### 4.4 Tests for Phase 4 ✅

- [x] `tests/ui/test_source_screen.py` — add source modal saves to `sources.json` and refreshes the list
- [x] `tests/ui/test_episode_screen.py` — feed fetch failure shows error message instead of crashing
- [x] `tests/test_user_config.py` — missing config file returns defaults, values are read correctly

### 4.5 README

- Install instructions (brew dependencies + pip)
- How to run
- Keyboard shortcuts reference
- How to run tests (`pytest tests/`)

---

## Bug fixes post-Phase 4

### End-of-episode replay (2026-03-20)

- `db.py` — nueva función `delete_position(episode_id)`
- `episode_screen._play_episode` — si `resume_pos >= total_duration - 30s`, se borra la posición y se reproduce desde el principio; evita que mpv arranque en el último segundo y termine sin reproducir nada
- Tests: `test_db.py` (2 tests para `delete_position`), `test_episode_screen.py` (2 tests para reset vs resume)

---

## Phase 5 — IPC Playback Bar (future)

Upgrade `player.py` to use `mpv`'s JSON IPC socket for full in-app control.

- Launch mpv with `--input-ipc-server=/tmp/podkstr-mpv.sock`
- Connect to the socket from the app and poll `time-pos` and `duration` every second
- Update a `ProgressBar` widget in `PlayerBar` with current position
- Add keybindings: `space` pause/resume, `←`/`→` seek ±30s
- Show elapsed / total time next to the progress bar

This phase is explicitly deferred — implement only after Phase 4 is complete and working.

---

## Keyboard Shortcuts Summary

| Key | Context | Action |
|-----|---------|--------|
| `q` | Source list | Quit |
| `Enter` | Episode list | Play episode |
| `f` | Episode list | Toggle favorite |
| `F` | Episode list | Toggle favorites filter |
| `d` | Episode list | Download episode (or play if downloaded) |
| `n` / `p` | Episode list | Next / previous page |
| `a` | Source list | Add new source |
| `s` | Global | Stop playback |
| `Escape` | Episode list | Back to source list |
