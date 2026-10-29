import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from tests.conftest import FIXTURE_EPISODE
from podkstr.downloader import _sanitize_filename, download


def test_sanitize_filename_removes_forbidden_chars():
    result = _sanitize_filename('file<with>forbidden:chars"and/more')

    assert "<" not in result
    assert ">" not in result
    assert ":" not in result
    assert '"' not in result
    assert "/" not in result


def test_sanitize_filename_truncates_long_names():
    long_name = "a" * 300

    result = _sanitize_filename(long_name)

    assert len(result) <= 200


def test_sanitize_filename_strips_leading_dots_and_spaces():
    result = _sanitize_filename("... filename ...")

    assert not result.startswith(".")
    assert not result.startswith(" ")


def test_sanitize_filename_preserves_normal_name():
    result = _sanitize_filename("12345 - My Episode Title")

    assert result == "12345 - My Episode Title"


def build_mock_http(content: bytes = b"fake mp3 content"):
    async def fake_aiter_bytes(**kwargs):
        yield content

    mock_response = AsyncMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.aiter_bytes = fake_aiter_bytes
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_client = AsyncMock()
    mock_client.stream = MagicMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    return mock_client


async def test_download_creates_file_in_dest_dir(tmp_path):
    dest_dir = str(tmp_path / "downloads")

    with patch("podkstr.downloader.httpx.AsyncClient", return_value=build_mock_http()):
        path = await download(FIXTURE_EPISODE, dest_dir)

    assert os.path.dirname(path) == dest_dir
    assert path.endswith(".mp3")


async def test_download_includes_episode_id_in_filename(tmp_path):
    dest_dir = str(tmp_path / "downloads")

    with patch("podkstr.downloader.httpx.AsyncClient", return_value=build_mock_http()):
        path = await download(FIXTURE_EPISODE, dest_dir)

    assert FIXTURE_EPISODE["id"] in os.path.basename(path)


async def test_download_sends_referer_header(tmp_path):
    dest_dir = str(tmp_path / "downloads")

    with patch("podkstr.downloader.httpx.AsyncClient", return_value=build_mock_http()) as mock_cls:
        await download(FIXTURE_EPISODE, dest_dir)

    call_kwargs = mock_cls.call_args[1]
    assert call_kwargs.get("headers", {}).get("Referer") == "https://www.rtve.es/"
