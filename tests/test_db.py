import pytest
import podkstr.db as db_module


def test_init_db_creates_favorites_table(tmp_db):
    import sqlite3
    conn = sqlite3.connect(tmp_db)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [t[0] for t in tables]
    assert "favorites" in table_names


def test_init_db_creates_downloads_table(tmp_db):
    import sqlite3
    conn = sqlite3.connect(tmp_db)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [t[0] for t in tables]
    assert "downloads" in table_names


def test_is_favorite_returns_false_when_not_added(tmp_db):
    assert db_module.is_favorite("12345") is False


def test_add_favorite_makes_episode_a_favorite(tmp_db):
    db_module.add_favorite("12345", "http://source.rss")

    assert db_module.is_favorite("12345") is True


def test_remove_favorite_removes_episode(tmp_db):
    db_module.add_favorite("12345", "http://source.rss")
    db_module.remove_favorite("12345")

    assert db_module.is_favorite("12345") is False


def test_remove_favorite_on_nonexistent_episode_does_not_raise(tmp_db):
    db_module.remove_favorite("nonexistent")


def test_add_favorite_is_idempotent(tmp_db):
    db_module.add_favorite("12345", "http://source.rss")
    db_module.add_favorite("12345", "http://source.rss")

    assert db_module.is_favorite("12345") is True


def test_get_favorites_returns_episode_ids_for_source(tmp_db):
    db_module.add_favorite("12345", "http://source-a.rss")
    db_module.add_favorite("67890", "http://source-a.rss")
    db_module.add_favorite("99999", "http://source-b.rss")

    result = db_module.get_favorites("http://source-a.rss")

    assert set(result) == {"12345", "67890"}


def test_get_favorites_returns_empty_list_for_unknown_source(tmp_db):
    assert db_module.get_favorites("http://unknown.rss") == []


def test_get_favorites_does_not_return_other_source_favorites(tmp_db):
    db_module.add_favorite("12345", "http://source-b.rss")

    result = db_module.get_favorites("http://source-a.rss")

    assert "12345" not in result


def test_is_downloaded_returns_false_when_not_added(tmp_db):
    assert db_module.is_downloaded("12345") is False


def test_add_download_marks_episode_as_downloaded(tmp_db):
    db_module.add_download("12345", "http://source.rss", "/tmp/12345.mp3")

    assert db_module.is_downloaded("12345") is True


def test_get_download_path_returns_none_when_not_downloaded(tmp_db):
    assert db_module.get_download_path("12345") is None


def test_get_download_path_returns_stored_path(tmp_db):
    db_module.add_download("12345", "http://source.rss", "/tmp/12345.mp3")

    assert db_module.get_download_path("12345") == "/tmp/12345.mp3"


def test_add_download_replaces_existing_entry(tmp_db):
    db_module.add_download("12345", "http://source.rss", "/tmp/old.mp3")
    db_module.add_download("12345", "http://source.rss", "/tmp/new.mp3")

    assert db_module.get_download_path("12345") == "/tmp/new.mp3"


def test_init_db_creates_positions_table(tmp_db):
    import sqlite3
    conn = sqlite3.connect(tmp_db)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    assert "positions" in [t[0] for t in tables]


def test_get_position_returns_none_when_not_saved(tmp_db):
    assert db_module.get_position("12345") is None


def test_save_position_stores_and_retrieves_value(tmp_db):
    db_module.save_position("12345", 1500.5)

    assert db_module.get_position("12345") == 1500.5


def test_save_position_overwrites_previous(tmp_db):
    db_module.save_position("12345", 100.0)
    db_module.save_position("12345", 999.0)

    assert db_module.get_position("12345") == 999.0


def test_delete_position_removes_saved_position(tmp_db):
    db_module.save_position("12345", 1500.0)

    db_module.delete_position("12345")

    assert db_module.get_position("12345") is None


def test_delete_position_is_noop_when_not_saved(tmp_db):
    db_module.delete_position("nonexistent")

    assert db_module.get_position("nonexistent") is None


def test_favorites_and_downloads_are_independent(tmp_db):
    db_module.add_favorite("12345", "http://source.rss")

    assert db_module.is_downloaded("12345") is False
    assert db_module.is_favorite("12345") is True
