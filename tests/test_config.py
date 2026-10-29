import json
import pytest
from tests.conftest import FIXTURE_SOURCES
import podkstr.config as config_module


def test_load_sources_returns_all_sources(tmp_sources):
    sources = config_module.load_sources()

    assert len(sources) == 2
    assert sources[0]["name"] == "Podcast A"
    assert sources[0]["url"] == "http://example.com/a.rss"


def test_load_sources_returns_list_of_dicts(tmp_sources):
    sources = config_module.load_sources()

    assert isinstance(sources, list)
    for source in sources:
        assert "name" in source
        assert "url" in source


def test_add_source_appends_new_entry(tmp_sources):
    config_module.add_source("Podcast C", "http://example.com/c.rss")

    sources = config_module.load_sources()
    assert len(sources) == 3
    assert sources[-1]["name"] == "Podcast C"
    assert sources[-1]["url"] == "http://example.com/c.rss"


def test_add_source_persists_to_file(tmp_sources):
    config_module.add_source("Podcast C", "http://example.com/c.rss")

    with open(tmp_sources) as f:
        data = json.load(f)
    assert any(s["name"] == "Podcast C" for s in data)


def test_add_source_preserves_existing_sources(tmp_sources):
    config_module.add_source("Podcast C", "http://example.com/c.rss")

    sources = config_module.load_sources()
    names = [s["name"] for s in sources]
    assert "Podcast A" in names
    assert "Podcast B" in names


def test_add_multiple_sources(tmp_sources):
    config_module.add_source("Podcast C", "http://example.com/c.rss")
    config_module.add_source("Podcast D", "http://example.com/d.rss")

    sources = config_module.load_sources()
    assert len(sources) == 4
