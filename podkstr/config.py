import json
import os
import shutil
import sys

_SOURCES_PATH = os.path.expanduser("~/.config/podkstr/sources.json")


def _get_bundled_sources_path() -> str:
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base = os.path.join(os.path.dirname(__file__), "..")
    return os.path.abspath(os.path.join(base, "sources.json"))


def _ensure_sources_file() -> None:
    if os.path.exists(_SOURCES_PATH):
        return
    os.makedirs(os.path.dirname(_SOURCES_PATH), exist_ok=True)
    bundled = _get_bundled_sources_path()
    if os.path.exists(bundled):
        shutil.copy(bundled, _SOURCES_PATH)
    else:
        with open(_SOURCES_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)


def load_sources() -> list[dict]:
    _ensure_sources_file()
    with open(_SOURCES_PATH, encoding="utf-8") as f:
        return json.load(f)


def add_source(name: str, url: str) -> None:
    sources = load_sources()
    sources.append({"name": name, "url": url})
    with open(_SOURCES_PATH, "w", encoding="utf-8") as f:
        json.dump(sources, f, indent=2, ensure_ascii=False)
