import os
import shutil
import subprocess
import tempfile

import httpx
from rich.markup import escape
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label, Static, LoadingIndicator
from textual.containers import Horizontal, Vertical, VerticalScroll

from podkstr import db, fetcher, player
from podkstr.fetcher import fetch_next_page
from podkstr.user_config import load_user_config

_config = load_user_config()
PAGE_SIZE = _config.get("page_size", 20)

_BUFFERING_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class EpisodeScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("space", "play_or_pause", "Play/Pause", show=True),
        Binding("s", "stop_playback", "Stop"),
        Binding("f", "toggle_favorite", "Favorite"),
        Binding("F", "toggle_filter", "Filter favorites"),
        Binding("d", "download", "Download"),
        Binding("right", "seek_forward", "→30s", priority=True),
        Binding("left", "seek_backward", "←30s", priority=True),
        Binding("n", "next_page", "Next page", priority=True),
        Binding("p", "prev_page", "Prev page", priority=True),
    ]

    def __init__(self, name: str, url: str):
        super().__init__()
        self._source_name = name
        self._source_url = url
        self._feed: dict = {}
        self._all_episodes: list[dict] = []
        self._filtered_episodes: list[dict] = []
        self._show_favorites_only = False
        self._page = 0
        self._api_page: int = 1
        self._has_more_api_pages: bool = False
        self._playing_episode_id: str | None = None
        self._playback_state: str = ""  # "", "buffering", "playing", "paused"
        self._buffering_frame_idx: int = 0
        self._buffering_timer = None
        self._position_timer = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical():
            yield Static("", id="source-meta")
            yield Static("", id="filter-indicator")
            yield LoadingIndicator(id="loading")
            with Horizontal(id="episode-list-area"):
                yield DataTable(id="episode-table", show_cursor=True, cursor_type="row")
                with VerticalScroll(id="episode-detail"):
                    yield Static("", id="episode-cover")
                    yield Static("", id="episode-description")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#episode-table", DataTable)
        table.add_columns("#", " ", "Title", "Date", "Dur.", "♥", "↓", " ")
        self.load_feed()

    @work(thread=True)
    def load_feed(self) -> None:
        try:
            feed = fetcher.fetch_feed(self._source_url)
            self.app.call_from_thread(self._on_feed_loaded, feed)
        except Exception as e:
            self.app.call_from_thread(self._on_feed_error, str(e))

    def _on_feed_error(self, error: str) -> None:
        self.query_one("#loading").display = False
        self.query_one("#source-meta", Static).update(
            f"[red]Failed to load feed:[/red] {error}\n\nCheck your network connection and try again."
        )

    def _on_feed_loaded(self, feed: dict) -> None:
        self._feed = feed
        self._all_episodes = feed["episodes"]
        self._api_page = 1
        self._has_more_api_pages = len(feed["episodes"]) >= PAGE_SIZE

        loading = self.query_one("#loading")
        loading.display = False

        meta = self.query_one("#source-meta", Static)
        meta.update(f"[bold]{escape(feed['title'])}[/bold]\n{escape(feed['description'][:200])}")

        self._apply_filter()

    def _apply_filter(self, keep_page: bool = False) -> None:
        if self._show_favorites_only:
            favs = set(db.get_favorites(self._source_url))
            self._filtered_episodes = [e for e in self._all_episodes if e["id"] in favs]
            indicator = "[yellow]Showing: Favorites only[/yellow]"
        else:
            self._filtered_episodes = self._all_episodes
            indicator = "Showing: All episodes"

        self.query_one("#filter-indicator", Static).update(indicator)
        if not keep_page:
            self._page = 0
        self._render_table()

    def _render_table(self) -> None:
        table = self.query_one("#episode-table", DataTable)
        table.clear()

        total_pages = max(1, (len(self._filtered_episodes) + PAGE_SIZE - 1) // PAGE_SIZE)
        start = self._page * PAGE_SIZE
        page_episodes = self._filtered_episodes[start: start + PAGE_SIZE]

        for i, ep in enumerate(page_episodes, start=start + 1):
            fav = "♥" if db.is_favorite(ep["id"]) else "·"
            dl = "↓" if db.is_downloaded(ep["id"]) else "·"
            raw_title = self._strip_program_name(ep["title"])
            if len(raw_title) > 50:
                raw_title = raw_title[:47] + "..."
            title = Text(raw_title, style=self._title_style(ep["id"]))
            saved_pos = db.get_position(ep["id"])
            dur = self._format_position(saved_pos) if saved_pos else ep["duration"]
            progress = self._render_progress_bar(saved_pos, self._parse_duration(ep["duration"])) if saved_pos else Text(" " * 24)
            table.add_row(str(i), self._status_icon(ep["id"]), title, ep["date"], dur, fav, dl, progress, key=ep["id"])

        self.sub_title = f"Page {self._page + 1}/{total_pages}  ({len(self._filtered_episodes)} episodes)"
        table.move_cursor(row=0)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is None:
            return
        ep_id = str(event.row_key.value)
        ep = next((e for e in self._filtered_episodes if e["id"] == ep_id), None)
        if ep:
            self._update_episode_detail(ep)

    def _update_episode_detail(self, ep: dict) -> None:
        desc = escape(ep.get("description", ""))
        self.query_one("#episode-description", Static).update(
            desc if desc else "[dim]No description available.[/dim]"
        )
        self.query_one("#episode-cover", Static).update("")
        image_url = ep.get("image_url", "")
        if image_url:
            self._render_episode_cover(image_url)

    @work(thread=True)
    def _render_episode_cover(self, image_url: str) -> None:
        if not image_url or not shutil.which("chafa"):
            return
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name
            with httpx.Client(follow_redirects=True, timeout=10) as client:
                resp = client.get(image_url)
                with open(tmp_path, "wb") as f:
                    f.write(resp.content)
            result = subprocess.run(
                ["chafa", "--format=symbols", "--symbols=block", "--colors=full", "--size=30x8", tmp_path],
                capture_output=True, text=True
            )
            art = Text.from_ansi(result.stdout) if result.stdout else Text("")
            os.unlink(tmp_path)
            self.app.call_from_thread(
                lambda: self.query_one("#episode-cover", Static).update(art)
            )
        except Exception:
            pass

    def _title_style(self, ep_id: str) -> str:
        if ep_id != self._playing_episode_id or not self._playback_state:
            return ""
        if self._playback_state == "buffering":
            return "bold orange1"
        if self._playback_state == "playing":
            return "bold green"
        if self._playback_state == "paused":
            return "bold yellow"
        return ""

    def _refresh_title_cell(self, episode_id: str) -> None:
        table = self.query_one("#episode-table", DataTable)
        start = self._page * PAGE_SIZE
        for i, ep in enumerate(self._filtered_episodes[start: start + PAGE_SIZE]):
            if ep["id"] == episode_id:
                raw_title = self._strip_program_name(ep["title"])
                if len(raw_title) > 50:
                    raw_title = raw_title[:47] + "..."
                table.update_cell_at((i, 2), Text(raw_title, style=self._title_style(episode_id)))
                break

    def _status_icon(self, ep_id: str) -> Text:
        if ep_id != self._playing_episode_id or not self._playback_state:
            return Text(" ")
        if self._playback_state == "buffering":
            frame = _BUFFERING_FRAMES[self._buffering_frame_idx]
            return Text(frame, style="orange1")
        if self._playback_state == "playing":
            return Text("▶", style="green")
        if self._playback_state == "paused":
            return Text("⏸", style="yellow")
        return Text(" ")

    def _set_playback_state(self, episode_id: str | None, state: str) -> None:
        if self._buffering_timer is not None:
            self._buffering_timer.stop()
            self._buffering_timer = None
        if self._position_timer is not None:
            self._position_timer.stop()
            self._position_timer = None
            self._restore_duration_cell()

        old_id = self._playing_episode_id
        self._playing_episode_id = episode_id
        self._playback_state = state

        if state == "buffering":
            self._buffering_frame_idx = 0
            self._buffering_timer = self.set_interval(0.12, self._advance_buffering_frame)
        elif state == "playing":
            self._position_timer = self.set_interval(1.0, self._update_position)

        if old_id:
            self._refresh_status_icon(old_id)
            self._refresh_title_cell(old_id)
        if episode_id and episode_id != old_id:
            self._refresh_status_icon(episode_id)
            self._refresh_title_cell(episode_id)

    def _advance_buffering_frame(self) -> None:
        self._buffering_frame_idx = (self._buffering_frame_idx + 1) % len(_BUFFERING_FRAMES)
        if self._playing_episode_id:
            self._refresh_status_icon(self._playing_episode_id)

    def _strip_program_name(self, title: str) -> str:
        feed_title = self._feed.get("title", "")
        if not feed_title:
            return title
        for sep in (" – ", " - ", ": ", " | "):
            prefix = feed_title + sep
            if title.lower().startswith(prefix.lower()):
                return title[len(prefix):]
        if title.lower().startswith(feed_title.lower()):
            return title[len(feed_title):].lstrip(" –-:|")
        return title

    def _parse_duration(self, duration: str) -> float:
        try:
            parts = duration.split(":")
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
        except (ValueError, AttributeError):
            pass
        return 0.0

    def _render_progress_bar(self, pos: float, total: float) -> Text:
        width = 24
        filled = round((pos / total) * width) if total > 0 else 0
        filled = max(0, min(filled, width))
        text = Text()
        text.append("█" * filled, style="cyan")
        text.append("░" * (width - filled), style="dim")
        return text

    def _refresh_progress_cell(self, episode_id: str, pos: float) -> None:
        ep = next((e for e in self._filtered_episodes if e["id"] == episode_id), None)
        if ep is None:
            return
        total = self._parse_duration(ep["duration"])
        table = self.query_one("#episode-table", DataTable)
        start = self._page * PAGE_SIZE
        for i, e in enumerate(self._filtered_episodes[start: start + PAGE_SIZE]):
            if e["id"] == episode_id:
                table.update_cell_at((i, 7), self._render_progress_bar(pos, total))
                break

    def _format_position(self, seconds: float) -> str:
        total = int(seconds)
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _update_position(self) -> None:
        if not self._playing_episode_id or not self.app.is_playing():
            return
        pos = self.app.get_time_pos()
        if pos is None:
            return
        db.save_position(self._playing_episode_id, pos)
        self._refresh_duration_cell(self._playing_episode_id, self._format_position(pos))
        self._refresh_progress_cell(self._playing_episode_id, pos)

    def _refresh_duration_cell(self, episode_id: str, value: str) -> None:
        table = self.query_one("#episode-table", DataTable)
        start = self._page * PAGE_SIZE
        for i, ep in enumerate(self._filtered_episodes[start: start + PAGE_SIZE]):
            if ep["id"] == episode_id:
                table.update_cell_at((i, 4), value)
                break

    def _restore_duration_cell(self) -> None:
        if not self._playing_episode_id:
            return
        ep = next((e for e in self._filtered_episodes if e["id"] == self._playing_episode_id), None)
        if ep:
            saved_pos = db.get_position(ep["id"])
            dur = self._format_position(saved_pos) if saved_pos else ep["duration"]
            self._refresh_duration_cell(self._playing_episode_id, dur)

    def _refresh_status_icon(self, episode_id: str) -> None:
        table = self.query_one("#episode-table", DataTable)
        start = self._page * PAGE_SIZE
        for i, ep in enumerate(self._filtered_episodes[start: start + PAGE_SIZE]):
            if ep["id"] == episode_id:
                table.update_cell_at((i, 1), self._status_icon(episode_id))
                break

    def _transition_to_playing(self, episode_id: str) -> None:
        if self._playing_episode_id == episode_id and self._playback_state == "buffering":
            if self.app.is_playing():
                self._set_playback_state(episode_id, "playing")
            else:
                self._set_playback_state(None, "")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        ep_id = str(event.row_key.value)
        ep = next((e for e in self._filtered_episodes if e["id"] == ep_id), None)
        if ep:
            self._play_episode(ep)

    def _play_episode(self, ep: dict) -> None:
        local_path = db.get_download_path(ep["id"])
        if local_path and os.path.exists(local_path):
            url = local_path
        else:
            url = ep["audio_url"]

        if not player.is_mpv_available():
            self.notify("mpv not found. Install with: brew install mpv", severity="error")
            return

        resume_pos = db.get_position(ep["id"])
        total = self._parse_duration(ep["duration"])
        if resume_pos is not None and total > 0 and resume_pos >= total - 30:
            db.delete_position(ep["id"])
            resume_pos = None
        self._set_playback_state(ep["id"], "buffering")
        self.app.play_episode(ep["title"], url, start_pos=resume_pos)
        self.set_timer(3.0, lambda: self._transition_to_playing(ep["id"]))

    def _get_cursor_episode(self) -> dict | None:
        table = self.query_one("#episode-table", DataTable)
        cursor_row = table.cursor_row
        if cursor_row < 0:
            return None
        cell_val = table.get_cell_at((cursor_row, 0))
        idx = int(cell_val) - 1
        if idx < 0 or idx >= len(self._filtered_episodes):
            return None
        return self._filtered_episodes[idx]

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_play_or_pause(self) -> None:
        if self._playback_state == "playing":
            self.app.pause()
            self._set_playback_state(self._playing_episode_id, "paused")
        elif self._playback_state == "paused":
            self.app.pause()
            self._set_playback_state(self._playing_episode_id, "playing")
        else:
            ep = self._get_cursor_episode()
            if ep:
                self._play_episode(ep)

    def action_stop_playback(self) -> None:
        self._set_playback_state(None, "")
        self.app.action_stop_playback()

    def action_toggle_favorite(self) -> None:
        table = self.query_one("#episode-table", DataTable)
        cursor_row = table.cursor_row
        if cursor_row < 0:
            return
        cell_val = table.get_cell_at((cursor_row, 0))
        idx = int(cell_val) - 1
        if idx < 0 or idx >= len(self._filtered_episodes):
            return
        ep = self._filtered_episodes[idx]

        if db.is_favorite(ep["id"]):
            db.remove_favorite(ep["id"])
            new_fav = "·"
        else:
            db.add_favorite(ep["id"], self._source_url)
            new_fav = "♥"

        table.update_cell_at((cursor_row, 5), new_fav)

        if self._show_favorites_only:
            self._apply_filter()

    def action_toggle_filter(self) -> None:
        self._show_favorites_only = not self._show_favorites_only
        self._apply_filter()

    def action_download(self) -> None:
        ep = self._get_cursor_episode()
        if ep is None:
            return
        table = self.query_one("#episode-table", DataTable)
        cursor_row = table.cursor_row
        self._start_download(ep, cursor_row)

    @work(exclusive=False)
    async def _start_download(self, ep: dict, cursor_row: int) -> None:
        from podkstr.downloader import download
        dest_dir = os.path.expanduser(_config.get("download_dir", "~/Downloads/podkstr"))

        self.notify(f"Downloading: {ep['title'][:50]}...")
        table = self.query_one("#episode-table", DataTable)
        table.update_cell_at((cursor_row, 6), "…")

        try:
            path = await download(ep, dest_dir)
            db.add_download(ep["id"], self._source_url, path)
            table.update_cell_at((cursor_row, 6), "↓")
            self.notify(f"Downloaded: {os.path.basename(path)}", severity="information")
        except Exception as e:
            table.update_cell_at((cursor_row, 6), "✗")
            self.notify(f"Download failed: {e}", severity="error")

    def action_seek_forward(self) -> None:
        self.app.seek(30)

    def action_seek_backward(self) -> None:
        pos = self.app.get_time_pos()
        if pos is not None and pos < 30:
            self.app.seek_to_end()
        else:
            self.app.seek(-30)

    def action_next_page(self) -> None:
        total_pages = max(1, (len(self._filtered_episodes) + PAGE_SIZE - 1) // PAGE_SIZE)
        if self._page < total_pages - 1:
            self._page += 1
            self._render_table()
        elif self._has_more_api_pages and not self._show_favorites_only:
            self._fetch_next_api_page()

    @work(thread=True)
    def _fetch_next_api_page(self) -> None:
        next_api_page = self._api_page + 1
        new_episodes = fetch_next_page(
            self._source_url, next_api_page, self._feed.get("image_url", "")
        )
        self.app.call_from_thread(self._on_next_page_loaded, new_episodes, next_api_page)

    def _on_next_page_loaded(self, new_episodes: list, api_page: int) -> None:
        self._api_page = api_page
        if not new_episodes:
            self._has_more_api_pages = False
            return
        self._has_more_api_pages = len(new_episodes) >= PAGE_SIZE
        self._all_episodes.extend(new_episodes)
        saved_page = self._page
        self._apply_filter(keep_page=True)
        self._page = saved_page + 1
        self._render_table()

    def action_prev_page(self) -> None:
        if self._page > 0:
            self._page -= 1
            self._render_table()
