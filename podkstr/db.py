import os
import sqlite3
from datetime import datetime, timezone

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "podkstr.db")


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(_DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(os.path.abspath(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS favorites (
                episode_id TEXT PRIMARY KEY,
                source_url TEXT NOT NULL,
                added_at   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS downloads (
                episode_id    TEXT PRIMARY KEY,
                source_url    TEXT NOT NULL,
                file_path     TEXT NOT NULL,
                downloaded_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS positions (
                episode_id TEXT PRIMARY KEY,
                position   REAL NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)


def is_favorite(episode_id: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM favorites WHERE episode_id = ?", (episode_id,)
        ).fetchone()
        return row is not None


def add_favorite(episode_id: str, source_url: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO favorites (episode_id, source_url, added_at) VALUES (?, ?, ?)",
            (episode_id, source_url, datetime.now(timezone.utc).isoformat()),
        )


def remove_favorite(episode_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM favorites WHERE episode_id = ?", (episode_id,))


def get_favorites(source_url: str) -> list[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT episode_id FROM favorites WHERE source_url = ?", (source_url,)
        ).fetchall()
        return [row["episode_id"] for row in rows]


def is_downloaded(episode_id: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM downloads WHERE episode_id = ?", (episode_id,)
        ).fetchone()
        return row is not None


def add_download(episode_id: str, source_url: str, file_path: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO downloads (episode_id, source_url, file_path, downloaded_at) VALUES (?, ?, ?, ?)",
            (episode_id, source_url, file_path, datetime.now(timezone.utc).isoformat()),
        )


def get_download_path(episode_id: str) -> str | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT file_path FROM downloads WHERE episode_id = ?", (episode_id,)
        ).fetchone()
        return row["file_path"] if row else None


def save_position(episode_id: str, position: float) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO positions (episode_id, position, updated_at) VALUES (?, ?, ?)",
            (episode_id, position, datetime.now(timezone.utc).isoformat()),
        )


def get_position(episode_id: str) -> float | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT position FROM positions WHERE episode_id = ?", (episode_id,)
        ).fetchone()
        return float(row["position"]) if row else None


def delete_position(episode_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM positions WHERE episode_id = ?", (episode_id,))
