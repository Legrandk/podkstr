from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from textual.reactive import reactive


class PlayerBar(Widget):
    DEFAULT_CSS = """
    PlayerBar {
        height: 1;
        dock: bottom;
        background: $accent;
        color: $text;
        padding: 0 1;
    }
    PlayerBar.hidden {
        display: none;
    }
    """

    title: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        yield Static("", id="player-bar-text")

    def watch_title(self, value: str) -> None:
        self.query_one("#player-bar-text", Static).update(
            f"▶  {value}    [s] stop"
        )

    def show(self, episode_title: str) -> None:
        self.title = episode_title
        self.remove_class("hidden")

    def hide(self) -> None:
        self.title = ""
        self.add_class("hidden")
