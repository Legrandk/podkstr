# Podkstr

A terminal-based podcast player with a TUI interface.

## Requirements

- Python 3.11+
- [mpv](https://mpv.io/) — audio playback
- [chafa](https://hpjansson.org/chafa/) — cover art rendering (optional)

```bash
brew install mpv chafa
```

## Installation

```bash
git clone <repo>
cd podkstr
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
source .venv/bin/activate
python main.py
```

## Keyboard Shortcuts

| Key | Context | Action |
|-----|---------|--------|
| `Enter` | Source list | Open podcast |
| `a` | Source list | Add new source |
| `q` | Source list | Quit |
| `Enter` | Episode list | Play episode |
| `f` | Episode list | Toggle favorite |
| `F` | Episode list | Show favorites only / show all |
| `d` | Episode list | Download episode (or play local if downloaded) |
| `n` / `p` | Episode list | Next / previous page |
| `Escape` | Episode list | Back to source list |
| `s` | Global | Stop playback |

## Configuration

Optional config file at `~/.config/podkstr/config.json`:

```json
{
  "download_dir": "~/Downloads/podkstr",
  "page_size": 20
}
```

## Adding Sources

Press `a` on the source list to add a new podcast via its RSS feed URL.

RTVE RSS feed format: `http://www.rtve.es/api/programas/{program_id}/audios.rss`
