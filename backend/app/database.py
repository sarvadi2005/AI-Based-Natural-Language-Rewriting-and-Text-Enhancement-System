from __future__ import annotations

import os
import sqlite3
from pathlib import Path


_DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "rewrite_history.sqlite3"


def database_path() -> Path:
    configured = os.getenv("TEXT_REWRITER_DB_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return _DEFAULT_DATABASE


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS rewrite_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                original_text TEXT NOT NULL,
                enhanced_text TEXT NOT NULL,
                mode TEXT NOT NULL,
                canonical_mode TEXT NOT NULL,
                word_count_before INTEGER NOT NULL,
                word_count_after INTEGER NOT NULL,
                quality_score INTEGER NOT NULL,
                readability REAL,
                readability_label TEXT,
                metrics_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_rewrite_history_created_at "
            "ON rewrite_history(created_at DESC, id DESC)"
        )


def check_database() -> None:
    with connect() as connection:
        connection.execute("SELECT 1").fetchone()
