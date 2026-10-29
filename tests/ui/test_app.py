import subprocess
from unittest.mock import MagicMock, patch
import pytest
from podkstr.ui.app import PodkstrApp
from podkstr.ui.player_bar import PlayerBar
from podkstr.ui.source_screen import SourceScreen


async def test_app_starts_and_shows_source_screen():
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        assert isinstance(app.screen, SourceScreen)


async def test_stop_playback_action_when_nothing_is_playing():
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        await pilot.press("s")
        await pilot.pause(0.1)

        bar = app.query_one("#player-bar", PlayerBar)
        assert "hidden" in bar.classes


async def test_play_episode_shows_player_bar():
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        with patch("podkstr.player.is_mpv_available", return_value=True):
            with patch("podkstr.player.play", return_value=mock_process):
                app.play_episode("My Episode", "https://example.com/audio.mp3")
                await pilot.pause(0.1)

        bar = app.query_one("#player-bar", PlayerBar)
        assert "hidden" not in bar.classes
        assert bar.title == "My Episode"


async def test_stop_playback_terminates_process_and_hides_bar():
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        with patch("podkstr.player.is_mpv_available", return_value=True):
            with patch("podkstr.player.play", return_value=mock_process):
                app.play_episode("My Episode", "https://example.com/audio.mp3")
                await pilot.pause(0.1)

        await pilot.press("s")
        await pilot.pause(0.1)

        mock_process.terminate.assert_called_once()
        bar = app.query_one("#player-bar", PlayerBar)
        assert "hidden" in bar.classes


async def test_play_episode_shows_mpv_error_when_not_installed():
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        with patch("podkstr.player.is_mpv_available", return_value=False):
            app.play_episode("Episode", "https://example.com/audio.mp3")
            await pilot.pause(0.1)

        bar = app.query_one("#player-bar", PlayerBar)
        assert "hidden" in bar.classes


async def test_seek_calls_player_seek_when_playing():
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        with patch("podkstr.player.is_mpv_available", return_value=True):
            with patch("podkstr.player.play", return_value=mock_process):
                app.play_episode("My Episode", "https://example.com/audio.mp3")
                await pilot.pause(0.1)

        with patch("podkstr.player.seek") as mock_seek:
            app.seek(30)
            mock_seek.assert_called_once_with(30)


async def test_get_time_pos_delegates_to_player_when_playing():
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None

    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        with patch("podkstr.player.is_mpv_available", return_value=True):
            with patch("podkstr.player.play", return_value=mock_process):
                app.play_episode("My Episode", "https://example.com/audio.mp3")
                await pilot.pause(0.1)

        with patch("podkstr.player.get_time_pos", return_value=120.0) as mock_gtp:
            result = app.get_time_pos()
            mock_gtp.assert_called_once()
            assert result == 120.0


async def test_get_time_pos_returns_none_when_not_playing():
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        with patch("podkstr.player.get_time_pos") as mock_gtp:
            result = app.get_time_pos()
            mock_gtp.assert_not_called()
            assert result is None


async def test_seek_does_nothing_when_not_playing():
    app = PodkstrApp()
    async with app.run_test(headless=True) as pilot:
        with patch("podkstr.player.seek") as mock_seek:
            app.seek(30)
            mock_seek.assert_not_called()
