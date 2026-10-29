import json
import os
import pytest
import podkstr.user_config as user_config_module


def test_load_user_config_returns_defaults_when_no_file(tmp_user_config_path):
    config = user_config_module.load_user_config()

    assert config["download_dir"] == "~/Downloads/podkstr"
    assert config["page_size"] == 20


def test_load_user_config_reads_values_from_file(tmp_user_config_path):
    with open(tmp_user_config_path, "w") as f:
        json.dump({"download_dir": "/custom/dir", "page_size": 50}, f)

    config = user_config_module.load_user_config()

    assert config["download_dir"] == "/custom/dir"
    assert config["page_size"] == 50


def test_load_user_config_merges_partial_config_with_defaults(tmp_user_config_path):
    with open(tmp_user_config_path, "w") as f:
        json.dump({"page_size": 10}, f)

    config = user_config_module.load_user_config()

    assert config["page_size"] == 10
    assert config["download_dir"] == "~/Downloads/podkstr"


def test_save_user_config_writes_file(tmp_user_config_path):
    user_config_module.save_user_config({"download_dir": "/saved/dir", "page_size": 30})

    with open(tmp_user_config_path) as f:
        data = json.load(f)
    assert data["download_dir"] == "/saved/dir"
    assert data["page_size"] == 30


def test_save_and_load_roundtrip(tmp_user_config_path):
    original = {"download_dir": "/roundtrip/dir", "page_size": 15}

    user_config_module.save_user_config(original)
    loaded = user_config_module.load_user_config()

    assert loaded["download_dir"] == "/roundtrip/dir"
    assert loaded["page_size"] == 15


def test_save_user_config_creates_parent_directory(tmp_path, monkeypatch):
    nested_path = str(tmp_path / "nested" / "dir" / "config.json")
    monkeypatch.setattr("podkstr.user_config._CONFIG_PATH", nested_path)

    user_config_module.save_user_config({"download_dir": "~/Downloads", "page_size": 20})

    assert os.path.exists(nested_path)
