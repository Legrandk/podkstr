import json
import os
import pytest


FIXTURE_FEED = {
    "title": "Test Podcast",
    "description": "A test description",
    "image_url": "https://example.com/image.jpg",
    "episodes": [
        {
            "id": "12345",
            "title": "Episode 1",
            "date": "2024-01-02",
            "duration": "00:30:00",
            "audio_url": "https://example.com/ztnr/12345.mp3",
            "description": "Description 1",
        },
        {
            "id": "67890",
            "title": "Episode 2",
            "date": "2024-01-01",
            "duration": "00:45:00",
            "audio_url": "https://example.com/ztnr/67890.mp3",
            "description": "Description 2",
        },
    ],
}

FIXTURE_EPISODE = FIXTURE_FEED["episodes"][0]

FIXTURE_SOURCES = [
    {"name": "Podcast A", "url": "http://example.com/a.rss"},
    {"name": "Podcast B", "url": "http://example.com/b.rss"},
]


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("podkstr.db._DB_PATH", db_path)
    import podkstr.db as db_module
    db_module.init_db()
    return db_path


@pytest.fixture()
def tmp_sources(tmp_path, monkeypatch):
    sources_path = str(tmp_path / "sources.json")
    with open(sources_path, "w") as f:
        json.dump(FIXTURE_SOURCES, f)
    monkeypatch.setattr("podkstr.config._SOURCES_PATH", sources_path)
    return sources_path


@pytest.fixture()
def tmp_user_config_path(tmp_path, monkeypatch):
    config_path = str(tmp_path / "config.json")
    monkeypatch.setattr("podkstr.user_config._CONFIG_PATH", config_path)
    return config_path
