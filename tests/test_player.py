import json
import subprocess
from unittest.mock import patch, MagicMock
import podkstr.player as player_module


def test_is_mpv_available_returns_true_when_found():
    with patch("podkstr.player.shutil.which", return_value="/usr/bin/mpv"):
        assert player_module.is_mpv_available() is True


def test_is_mpv_available_returns_false_when_not_found():
    with patch("podkstr.player.shutil.which", return_value=None):
        assert player_module.is_mpv_available() is False


def test_play_returns_popen_process():
    mock_process = MagicMock(spec=subprocess.Popen)
    with patch("podkstr.player.subprocess.Popen", return_value=mock_process) as mock_popen:
        result = player_module.play("https://example.com/audio.mp3")

    assert result is mock_process


def test_play_calls_mpv_with_correct_arguments():
    mock_process = MagicMock(spec=subprocess.Popen)
    with patch("podkstr.player.subprocess.Popen", return_value=mock_process) as mock_popen:
        player_module.play("https://example.com/audio.mp3")

    args = mock_popen.call_args[0][0]
    assert args[0] == "mpv"
    assert "--referrer=https://www.rtve.es/" in args
    assert "--no-video" in args
    assert any(a.startswith("--input-ipc-server=") for a in args)
    assert "https://example.com/audio.mp3" in args


def test_play_passes_start_position_when_provided():
    mock_process = MagicMock(spec=subprocess.Popen)
    with patch("podkstr.player.subprocess.Popen", return_value=mock_process) as mock_popen:
        player_module.play("https://example.com/audio.mp3", start_pos=1500.0)

    args = mock_popen.call_args[0][0]
    assert any(a.startswith("--start=") for a in args)
    assert "--start=1500.0" in args


def test_play_omits_start_when_position_is_none():
    mock_process = MagicMock(spec=subprocess.Popen)
    with patch("podkstr.player.subprocess.Popen", return_value=mock_process) as mock_popen:
        player_module.play("https://example.com/audio.mp3", start_pos=None)

    args = mock_popen.call_args[0][0]
    assert not any(a.startswith("--start=") for a in args)


def test_play_suppresses_mpv_output():
    mock_process = MagicMock(spec=subprocess.Popen)
    with patch("podkstr.player.subprocess.Popen", return_value=mock_process) as mock_popen:
        player_module.play("https://example.com/audio.mp3")

    kwargs = mock_popen.call_args[1]
    assert kwargs.get("stdout") == subprocess.DEVNULL
    assert kwargs.get("stderr") == subprocess.DEVNULL


def _make_mock_sock():
    mock_sock = MagicMock()
    mock_sock.__enter__ = MagicMock(return_value=mock_sock)
    mock_sock.__exit__ = MagicMock(return_value=False)
    return mock_sock


def test_pause_sends_cycle_pause_command():
    mock_sock = _make_mock_sock()
    with patch("podkstr.player.socket.socket", return_value=mock_sock):
        player_module.pause()

    sent = mock_sock.sendall.call_args[0][0].decode()
    data = json.loads(sent.strip())
    assert data["command"] == ["cycle", "pause"]


def test_pause_silently_ignores_socket_errors():
    with patch("podkstr.player.socket.socket", side_effect=OSError("no socket")):
        player_module.pause()  # must not raise


def test_seek_to_end_sends_absolute_percent_command():
    mock_sock = _make_mock_sock()
    with patch("podkstr.player.socket.socket", return_value=mock_sock):
        player_module.seek_to_end()

    sent = mock_sock.sendall.call_args[0][0].decode()
    data = json.loads(sent.strip())
    assert data["command"] == ["seek", 100, "absolute-percent"]


def test_seek_to_end_silently_ignores_socket_errors():
    with patch("podkstr.player.socket.socket", side_effect=OSError("no socket")):
        player_module.seek_to_end()  # must not raise


def test_seek_sends_relative_seek_command():
    mock_sock = _make_mock_sock()
    with patch("podkstr.player.socket.socket", return_value=mock_sock):
        player_module.seek(30)

    sent = mock_sock.sendall.call_args[0][0].decode()
    data = json.loads(sent.strip())
    assert data["command"] == ["seek", 30, "relative"]


def test_seek_negative_seeks_backward():
    mock_sock = _make_mock_sock()
    with patch("podkstr.player.socket.socket", return_value=mock_sock):
        player_module.seek(-30)

    sent = mock_sock.sendall.call_args[0][0].decode()
    data = json.loads(sent.strip())
    assert data["command"] == ["seek", -30, "relative"]


def test_seek_connects_to_ipc_socket_path():
    mock_sock = _make_mock_sock()
    with patch("podkstr.player.socket.socket", return_value=mock_sock):
        player_module.seek(30)

    mock_sock.connect.assert_called_once_with(player_module._IPC_SOCK)


def test_seek_silently_ignores_socket_errors():
    with patch("podkstr.player.socket.socket", side_effect=OSError("no socket")):
        player_module.seek(30)  # must not raise


def test_get_time_pos_returns_current_position():
    response = json.dumps({"data": 734.5, "error": "success"}) + "\n"
    mock_sock = _make_mock_sock()
    mock_sock.recv.return_value = response.encode()

    with patch("podkstr.player.socket.socket", return_value=mock_sock):
        result = player_module.get_time_pos()

    assert result == 734.5


def test_get_time_pos_returns_none_on_mpv_error():
    response = json.dumps({"data": None, "error": "property unavailable"}) + "\n"
    mock_sock = _make_mock_sock()
    mock_sock.recv.return_value = response.encode()

    with patch("podkstr.player.socket.socket", return_value=mock_sock):
        result = player_module.get_time_pos()

    assert result is None


def test_get_time_pos_returns_none_on_socket_error():
    with patch("podkstr.player.socket.socket", side_effect=OSError("no socket")):
        result = player_module.get_time_pos()

    assert result is None
