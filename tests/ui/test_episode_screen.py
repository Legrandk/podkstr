import subprocess
import pytest
from unittest.mock import MagicMock, patch
from textual.widgets import DataTable, Static
from tests.conftest import FIXTURE_FEED, FIXTURE_SOURCES
from podkstr.ui.app import PodkstrApp
from podkstr.ui.source_screen import SourceScreen
from podkstr.ui.episode_screen import EpisodeScreen


def build_app_with_episode_screen(feed=None, tmp_db_path=None):
    if feed is None:
        feed = FIXTURE_FEED
    app = PodkstrApp()
    return app, feed


async def navigate_to_episode_screen(pilot, app, feed):
    with patch("podkstr.fetcher.fetch_feed", return_value=feed):
        with patch("podkstr.ui.source_screen.load_sources", return_value=FIXTURE_SOURCES):
            await pilot.press("enter")
            await pilot.pause(1.5)


async def test_episodes_load_from_feed(tmp_db):
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        table = app.screen.query_one("#episode-table", DataTable)
        assert table.row_count == len(FIXTURE_FEED["episodes"])


async def test_episode_table_shows_title_and_date(tmp_db):
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        table = app.screen.query_one("#episode-table", DataTable)
        first_title = table.get_cell_at((0, 2))
        first_date = table.get_cell_at((0, 3))

        assert FIXTURE_FEED["episodes"][0]["title"] in first_title
        assert FIXTURE_FEED["episodes"][0]["date"] == first_date


async def test_source_metadata_is_displayed(tmp_db):
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        meta = app.screen.query_one("#source-meta", Static)
        assert FIXTURE_FEED["title"] in str(meta.render())


async def test_f_key_toggles_favorite_indicator(tmp_db):
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        table = app.screen.query_one("#episode-table", DataTable)
        assert table.get_cell_at((0, 5)) == "·"

        await pilot.press("f")
        await pilot.pause(0.1)

        assert table.get_cell_at((0, 5)) == "♥"


async def test_f_key_toggles_favorite_off(tmp_db):
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        await pilot.press("f")
        await pilot.pause(0.1)
        await pilot.press("f")
        await pilot.pause(0.1)

        table = app.screen.query_one("#episode-table", DataTable)
        assert table.get_cell_at((0, 5)) == "·"


async def test_shift_f_filters_to_favorites_only(tmp_db):
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        await pilot.press("f")
        await pilot.pause(0.1)

        await pilot.press("F")
        await pilot.pause(0.1)

        table = app.screen.query_one("#episode-table", DataTable)
        assert table.row_count == 1


async def test_shift_f_toggles_back_to_all_episodes(tmp_db):
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        await pilot.press("f")
        await pilot.pause(0.1)
        await pilot.press("F")
        await pilot.pause(0.1)
        await pilot.press("F")
        await pilot.pause(0.1)

        table = app.screen.query_one("#episode-table", DataTable)
        assert table.row_count == len(FIXTURE_FEED["episodes"])


async def test_escape_goes_back_to_source_screen(tmp_db):
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)
        assert isinstance(app.screen, EpisodeScreen)

        await pilot.press("escape")
        await pilot.pause(0.2)

        assert isinstance(app.screen, SourceScreen)


async def test_pagination_next_page(tmp_db):
    big_feed = {
        **FIXTURE_FEED,
        "episodes": [
            {"id": str(i), "title": f"Episode {i}", "date": f"2024-01-{i:02d}",
             "duration": "00:30:00", "audio_url": f"https://example.com/{i}.mp3",
             "description": ""}
            for i in range(1, 26)
        ],
    }
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, big_feed)

        subtitle_before = app.screen.sub_title
        await pilot.press("n")
        await pilot.pause(0.1)
        subtitle_after = app.screen.sub_title

        assert subtitle_before != subtitle_after
        assert "Page 2" in subtitle_after


async def test_pagination_prev_page_has_no_effect_on_first_page(tmp_db):
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        subtitle_before = app.screen.sub_title
        await pilot.press("p")
        await pilot.pause(0.1)

        assert app.screen.sub_title == subtitle_before


async def test_feed_error_shows_error_message(tmp_db):
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        with patch("podkstr.fetcher.fetch_feed", side_effect=Exception("Network error")):
            with patch("podkstr.ui.source_screen.load_sources", return_value=FIXTURE_SOURCES):
                await pilot.press("enter")
                await pilot.pause(1.5)

        meta = app.screen.query_one("#source-meta", Static)
        assert "Failed to load feed" in str(meta.render())


async def test_enter_plays_episode_via_app(tmp_db):
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        table = app.screen.query_one("#episode-table", DataTable)
        assert table.row_count > 0

        with patch("podkstr.player.is_mpv_available", return_value=True):
            with patch("podkstr.player.play", return_value=mock_process) as mock_play:
                with patch.object(app, "play_episode", wraps=app.play_episode) as mock_play_ep:
                    ep = FIXTURE_FEED["episodes"][0]
                    app.screen._play_episode(ep)
                    await pilot.pause(0.2)

        mock_play.assert_called_once()


async def test_d_key_triggers_download(tmp_db):
    from unittest.mock import AsyncMock
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        mock_dl = AsyncMock(return_value="/tmp/ep.mp3")
        with patch("podkstr.downloader.download", mock_dl):
            await pilot.press("d")
            await pilot.pause(0.5)

        mock_dl.assert_called_once()


async def test_space_plays_episode_when_not_playing(tmp_db):
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        with patch("podkstr.player.is_mpv_available", return_value=True):
            with patch("podkstr.player.play", return_value=mock_process) as mock_play:
                await pilot.press("space")
                await pilot.pause(0.2)

        mock_play.assert_called_once()


async def test_space_pauses_playback_when_playing(tmp_db):
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        with patch("podkstr.player.is_mpv_available", return_value=True):
            with patch("podkstr.player.play", return_value=mock_process):
                app.play_episode("My Episode", "https://example.com/audio.mp3")
                app.screen._set_playback_state(FIXTURE_FEED["episodes"][0]["id"], "playing")
                await pilot.pause(0.1)

        with patch("podkstr.player.pause") as mock_pause:
            await pilot.press("space")
            await pilot.pause(0.1)

        mock_pause.assert_called_once()
        assert app.screen._playback_state == "paused"

        table = app.screen.query_one("#episode-table", DataTable)
        assert str(table.get_cell_at((0, 1))) == "⏸"


async def test_space_resumes_playback_when_paused(tmp_db):
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        with patch("podkstr.player.is_mpv_available", return_value=True):
            with patch("podkstr.player.play", return_value=mock_process):
                app.play_episode("My Episode", "https://example.com/audio.mp3")
                app.screen._set_playback_state(FIXTURE_FEED["episodes"][0]["id"], "paused")
                await pilot.pause(0.1)

        with patch("podkstr.player.pause") as mock_pause:
            await pilot.press("space")
            await pilot.pause(0.1)

        mock_pause.assert_called_once()
        assert app.screen._playback_state == "playing"


async def test_s_key_stops_playback_when_playing(tmp_db):
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        with patch("podkstr.player.is_mpv_available", return_value=True):
            with patch("podkstr.player.play", return_value=mock_process):
                app.play_episode("My Episode", "https://example.com/audio.mp3")
                await pilot.pause(0.1)

        await pilot.press("s")
        await pilot.pause(0.1)

        mock_process.terminate.assert_called_once()
        bar = app.query_one("#player-bar")
        assert "hidden" in bar.classes


async def test_play_shows_buffering_icon_on_status_column(tmp_db):
    from podkstr.ui.episode_screen import _BUFFERING_FRAMES
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        table = app.screen.query_one("#episode-table", DataTable)
        assert str(table.get_cell_at((0, 1))) == " "

        with patch("podkstr.player.is_mpv_available", return_value=True):
            with patch("podkstr.player.play", return_value=mock_process):
                ep = FIXTURE_FEED["episodes"][0]
                app.screen._play_episode(ep)
                await pilot.pause(0.1)

        assert str(table.get_cell_at((0, 1))) in _BUFFERING_FRAMES


async def test_duration_cell_updates_with_playback_position(tmp_db):
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        with patch("podkstr.player.is_mpv_available", return_value=True):
            with patch("podkstr.player.play", return_value=mock_process):
                ep = FIXTURE_FEED["episodes"][0]
                app.screen._play_episode(ep)
                app.screen._set_playback_state(ep["id"], "playing")

        with patch.object(app, "get_time_pos", return_value=734.0):
            app.screen._update_position()
            await pilot.pause(0.1)

        table = app.screen.query_one("#episode-table", DataTable)
        assert table.get_cell_at((0, 4)) == "00:12:14"


async def test_duration_cell_shows_saved_position_on_stop(tmp_db):
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        ep = FIXTURE_FEED["episodes"][0]

        with patch("podkstr.player.is_mpv_available", return_value=True):
            with patch("podkstr.player.play", return_value=mock_process):
                app.screen._play_episode(ep)
                app.screen._set_playback_state(ep["id"], "playing")

        with patch.object(app, "get_time_pos", return_value=120.0):
            app.screen._update_position()
            await pilot.pause(0.1)

        app.screen._set_playback_state(None, "")
        await pilot.pause(0.1)

        table = app.screen.query_one("#episode-table", DataTable)
        assert table.get_cell_at((0, 4)) == "00:02:00"


async def test_detail_panel_shows_episode_description_on_highlight(tmp_db):
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        ep = FIXTURE_FEED["episodes"][0]
        app.screen._update_episode_detail(ep)
        await pilot.pause(0.1)

        desc = app.screen.query_one("#episode-description", Static)
        assert ep["description"] in str(desc.render())


async def test_progress_bar_updates_with_position(tmp_db):
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        ep = FIXTURE_FEED["episodes"][0]
        app.screen._set_playback_state(ep["id"], "playing")
        app.screen._refresh_progress_cell(ep["id"], 900.0)
        await pilot.pause(0.1)

        table = app.screen.query_one("#episode-table", DataTable)
        cell = str(table.get_cell_at((0, 7)))
        assert "█" in cell
        assert "░" in cell


async def test_strip_program_name_removes_em_dash_prefix():
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        screen = EpisodeScreen("Test", "http://example.com/feed.rss")
        screen._feed = {"title": "My Podcast"}
        assert screen._strip_program_name("My Podcast – Episode Title") == "Episode Title"


async def test_strip_program_name_removes_hyphen_prefix():
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        screen = EpisodeScreen("Test", "http://example.com/feed.rss")
        screen._feed = {"title": "My Podcast"}
        assert screen._strip_program_name("My Podcast - Episode Title") == "Episode Title"


async def test_strip_program_name_leaves_unrelated_titles_unchanged():
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        screen = EpisodeScreen("Test", "http://example.com/feed.rss")
        screen._feed = {"title": "My Podcast"}
        assert screen._strip_program_name("Unrelated Title") == "Unrelated Title"


async def test_strip_program_name_is_case_insensitive():
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        screen = EpisodeScreen("Test", "http://example.com/feed.rss")
        screen._feed = {"title": "My Podcast"}
        assert screen._strip_program_name("MY PODCAST – Episode Title") == "Episode Title"


async def test_format_position_minutes_and_seconds():
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        screen = EpisodeScreen("Test", "http://example.com/feed.rss")
        assert screen._format_position(734.0) == "00:12:14"
        assert screen._format_position(59.0) == "00:00:59"
        assert screen._format_position(3661.0) == "01:01:01"


async def test_right_arrow_seeks_forward_30s(tmp_db):
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        with patch("podkstr.player.is_mpv_available", return_value=True):
            with patch("podkstr.player.play", return_value=mock_process):
                app.play_episode("Episode", "https://example.com/audio.mp3")
                await pilot.pause(0.1)

        with patch("podkstr.player.seek") as mock_seek:
            await pilot.press("right")
            await pilot.pause(0.1)

        mock_seek.assert_called_once_with(30)


async def test_left_arrow_wraps_to_end_when_at_start(tmp_db):
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        with patch("podkstr.player.is_mpv_available", return_value=True):
            with patch("podkstr.player.play", return_value=mock_process):
                app.play_episode("Episode", "https://example.com/audio.mp3")
                await pilot.pause(0.1)

        with patch.object(app, "get_time_pos", return_value=10.0):
            with patch("podkstr.player.seek_to_end") as mock_seek_end:
                await pilot.press("left")
                await pilot.pause(0.1)

        mock_seek_end.assert_called_once()


async def test_left_arrow_seeks_backward_30s(tmp_db):
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        with patch("podkstr.player.is_mpv_available", return_value=True):
            with patch("podkstr.player.play", return_value=mock_process):
                app.play_episode("Episode", "https://example.com/audio.mp3")
                await pilot.pause(0.1)

        with patch("podkstr.player.seek") as mock_seek:
            await pilot.press("left")
            await pilot.pause(0.1)

        mock_seek.assert_called_once_with(-30)


async def test_stop_clears_status_icon(tmp_db):
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        with patch("podkstr.player.is_mpv_available", return_value=True):
            with patch("podkstr.player.play", return_value=mock_process):
                ep = FIXTURE_FEED["episodes"][0]
                app.screen._play_episode(ep)
                await pilot.pause(0.1)

        from podkstr.ui.episode_screen import _BUFFERING_FRAMES
        table = app.screen.query_one("#episode-table", DataTable)
        assert str(table.get_cell_at((0, 1))) in _BUFFERING_FRAMES

        await pilot.press("s")
        await pilot.pause(0.1)

        assert str(table.get_cell_at((0, 1))) == " "


async def test_play_episode_resets_position_when_at_end(tmp_db):
    import podkstr.db as db_module

    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    ep = FIXTURE_FEED["episodes"][0]
    # duration "00:30:00" = 1800s — save a position at the very end
    db_module.save_position(ep["id"], 1795.0)

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        with patch("podkstr.player.is_mpv_available", return_value=True):
            with patch("podkstr.player.play", return_value=mock_process) as mock_play:
                app.screen._play_episode(ep)
                await pilot.pause(0.1)

        # mpv must be called without --start (i.e. start_pos=None → plays from beginning)
        mock_play.assert_called_once_with(ep["audio_url"], start_pos=None)
        # position must be cleared from DB
        assert db_module.get_position(ep["id"]) is None


async def test_play_episode_resumes_mid_episode_position(tmp_db):
    import podkstr.db as db_module

    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    ep = FIXTURE_FEED["episodes"][0]
    # duration "00:30:00" = 1800s — save a mid-episode position
    db_module.save_position(ep["id"], 600.0)

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await navigate_to_episode_screen(pilot, app, FIXTURE_FEED)

        with patch("podkstr.player.is_mpv_available", return_value=True):
            with patch("podkstr.player.play", return_value=mock_process) as mock_play:
                app.screen._play_episode(ep)
                await pilot.pause(0.1)

        mock_play.assert_called_once_with(ep["audio_url"], start_pos=600.0)
