from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label
from textual.containers import Vertical

from podkstr.config import add_source


class AddSourceModal(ModalScreen):
    DEFAULT_CSS = """
    AddSourceModal {
        align: center middle;
    }
    AddSourceModal Vertical {
        width: 60;
        height: auto;
        padding: 2 4;
        background: $surface;
        border: tall $primary;
    }
    AddSourceModal Label {
        margin-bottom: 1;
    }
    AddSourceModal Input {
        margin-bottom: 1;
    }
    AddSourceModal Button {
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Add new podcast source", id="modal-title")
            yield Input(placeholder="Name (e.g. My Podcast)", id="input-name")
            yield Input(placeholder="RSS URL", id="input-url")
            yield Button("Add", variant="primary", id="btn-add")
            yield Button("Cancel", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-add":
            self._submit()
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _submit(self) -> None:
        name = self.query_one("#input-name", Input).value.strip()
        url = self.query_one("#input-url", Input).value.strip()

        if not name or not url:
            self.notify("Name and URL are required", severity="error")
            return

        add_source(name, url)
        self.dismiss(True)
