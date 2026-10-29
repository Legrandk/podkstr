import subprocess

from textual.app import App, ComposeResult
from textual.binding import Binding

from podkstr import db, player
from podkstr.ui.player_bar import PlayerBar
from podkstr.ui.source_screen import SourceScreen


class PodkstrApp(App):
    TITLE = "Podkstr"
    CSS = """
    Screen {
        layers: base overlay;
    }
#source-meta {
        height: auto;
        padding: 0 1 1 1;
        color: $text-muted;
    }
    #filter-indicator {
        height: 1;
        padding: 0 1;
    }
    #loading {
        height: 3;
    }
    #episode-list-area {
        height: 1fr;
    }
    #episode-table {
        width: 2fr;
    }
    #episode-detail {
        width: 1fr;
        border-left: tall $border;
        padding: 0 1;
    }
    #episode-cover {
        height: auto;
    }
    #episode-description {
        height: auto;
        color: $text-muted;
    }
    #source-list {
        height: 1fr;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("s", "stop_playback", "Stop", show=True),
    ]

    def __init__(self):
        super().__init__()
        self._mpv_process: subprocess.Popen | None = None
        db.init_db()

    def compose(self) -> ComposeResult:
        yield PlayerBar(classes="hidden", id="player-bar")

    def on_mount(self) -> None:
        self.push_screen(SourceScreen())

    def get_time_pos(self) -> float | None:
        if self.is_playing():
            return player.get_time_pos()
        return None

    def pause(self) -> None:
        if self.is_playing():
            player.pause()

    def seek(self, seconds: int) -> None:
        if self.is_playing():
            player.seek(seconds)

    def seek_to_end(self) -> None:
        if self.is_playing():
            player.seek_to_end()

    def is_playing(self) -> bool:
        return self._mpv_process is not None and self._mpv_process.poll() is None

    def play_episode(self, title: str, url: str, start_pos: float | None = None) -> None:
        if self._mpv_process and self._mpv_process.poll() is None:
            self._mpv_process.terminate()

        if not player.is_mpv_available():
            self.notify("mpv not found. Install with: brew install mpv", severity="error")
            return

        self._mpv_process = player.play(url, start_pos=start_pos)
        self.query_one("#player-bar", PlayerBar).show(title)

    def action_stop_playback(self) -> None:
        if self._mpv_process and self._mpv_process.poll() is None:
            self._mpv_process.terminate()
            self._mpv_process = None
        self.query_one("#player-bar", PlayerBar).hide()

    def on_unmount(self) -> None:
        if self._mpv_process and self._mpv_process.poll() is None:
            self._mpv_process.terminate()
