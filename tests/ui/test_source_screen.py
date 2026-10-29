import json
import pytest
from unittest.mock import patch
from textual.widgets import ListView
from tests.conftest import FIXTURE_SOURCES
from podkstr.ui.app import PodkstrApp
from podkstr.ui.source_screen import SourceScreen
from podkstr.ui.episode_screen import EpisodeScreen


async def test_source_list_shows_all_configured_sources(tmp_sources):
    with patch("podkstr.ui.source_screen.load_sources", return_value=FIXTURE_SOURCES):
        app = PodkstrApp()
        async with app.run_test(headless=True) as pilot:
            list_view = app.screen.query_one("#source-list", ListView)

            assert len(list_view) == len(FIXTURE_SOURCES)


async def test_selecting_source_pushes_episode_screen(tmp_sources):
    feed_mock = {
        "title": "Podcast A", "description": "", "image_url": "",
        "episodes": [],
    }
    with patch("podkstr.ui.source_screen.load_sources", return_value=FIXTURE_SOURCES):
        with patch("podkstr.fetcher.fetch_feed", return_value=feed_mock):
            app = PodkstrApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.press("enter")
                await pilot.pause(0.5)

                assert isinstance(app.screen, EpisodeScreen)


async def test_a_key_opens_add_source_modal(tmp_sources):
    with patch("podkstr.ui.source_screen.load_sources", return_value=FIXTURE_SOURCES):
        app = PodkstrApp()
        async with app.run_test(headless=True) as pilot:
            await pilot.press("a")
            await pilot.pause(0.2)

            from podkstr.ui.add_source_modal import AddSourceModal
            assert isinstance(app.screen, AddSourceModal)


async def test_add_source_modal_calls_add_source_on_submit(tmp_sources):
    with patch("podkstr.ui.source_screen.load_sources", return_value=FIXTURE_SOURCES):
        with patch("podkstr.ui.add_source_modal.add_source") as mock_add:
            app = PodkstrApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.press("a")
                await pilot.pause(0.2)

                from podkstr.ui.add_source_modal import AddSourceModal
                from textual.widgets import Input
                modal = app.screen
                assert isinstance(modal, AddSourceModal)

                modal.query_one("#input-name", Input).value = "New Pod"
                modal.query_one("#input-url", Input).value = "http://new.rss"
                await pilot.click("#btn-add")
                await pilot.pause(0.2)

            mock_add.assert_called_once_with("New Pod", "http://new.rss")


async def test_q_key_quits_app(tmp_sources):
    with patch("podkstr.ui.source_screen.load_sources", return_value=FIXTURE_SOURCES):
        app = PodkstrApp()
        async with app.run_test(headless=True) as pilot:
            await pilot.press("q")
