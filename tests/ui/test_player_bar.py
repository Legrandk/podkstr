import pytest
from podkstr.ui.app import PodkstrApp
from podkstr.ui.player_bar import PlayerBar


async def test_player_bar_is_initially_hidden():
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        bar = app.query_one("#player-bar", PlayerBar)

        assert "hidden" in bar.classes


async def test_show_removes_hidden_class_and_sets_title():
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        bar = app.query_one("#player-bar", PlayerBar)

        bar.show("My Episode Title")
        await pilot.pause(0.1)

        assert "hidden" not in bar.classes
        assert bar.title == "My Episode Title"


async def test_hide_adds_hidden_class_and_clears_title():
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        bar = app.query_one("#player-bar", PlayerBar)
        bar.show("My Episode Title")
        await pilot.pause(0.1)

        bar.hide()
        await pilot.pause(0.1)

        assert "hidden" in bar.classes
        assert bar.title == ""


async def test_show_updates_displayed_text():
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        bar = app.query_one("#player-bar", PlayerBar)

        bar.show("Test Episode")
        await pilot.pause(0.1)

        from textual.widgets import Static
        text_widget = bar.query_one("#player-bar-text", Static)
        rendered = str(text_widget.render())
        assert "Test Episode" in rendered
