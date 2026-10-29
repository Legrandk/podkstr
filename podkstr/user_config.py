import json
import os

_CONFIG_PATH = os.path.expanduser("~/.config/podkstr/config.json")

_DEFAULTS = {
    "download_dir": "~/Downloads/podkstr",
    "page_size": 20,
}


def load_user_config() -> dict:
    if not os.path.exists(_CONFIG_PATH):
        return dict(_DEFAULTS)
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {**_DEFAULTS, **data}


def save_user_config(config: dict) -> None:
    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
