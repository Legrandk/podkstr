from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, ListView, ListItem, Label
from textual.binding import Binding

from podkstr.config import load_sources


class SourceScreen(Screen):
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("a", "add_source", "Add source"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield ListView(*self._build_items(), id="source-list")
        yield Footer()

    def _build_items(self) -> list[ListItem]:
        sources = load_sources()
        items = []
        for source in sources:
            items.append(ListItem(Label(source["name"]), name=source["url"]))
        return items

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        url = event.item.name
        sources = load_sources()
        source = next((s for s in sources if s["url"] == url), {"name": url})
        from podkstr.ui.episode_screen import EpisodeScreen
        self.app.push_screen(EpisodeScreen(name=source["name"], url=url))

    def action_quit(self) -> None:
        self.app.exit()

    def action_add_source(self) -> None:
        from podkstr.ui.add_source_modal import AddSourceModal
        self.app.push_screen(AddSourceModal(), callback=self._on_source_added)

    def _on_source_added(self, result) -> None:
        if result:
            list_view = self.query_one("#source-list", ListView)
            sources = load_sources()
            source = sources[-1]
            list_view.append(ListItem(Label(source["name"]), name=source["url"]))
