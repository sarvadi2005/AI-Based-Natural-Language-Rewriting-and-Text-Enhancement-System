from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.database import connect


def _record_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "original_text": row["original_text"],
        "enhanced_text": row["enhanced_text"],
        "rewritten_text": row["enhanced_text"],
        "mode": row["mode"],
        "canonical_mode": row["canonical_mode"],
        "word_count_before": row["word_count_before"],
        "word_count_after": row["word_count_after"],
        "quality_score": row["quality_score"],
        "readability": row["readability"],
        "readability_label": row["readability_label"],
        "metrics": json.loads(row["metrics_json"]),
    }


def save_rewrite(
    *,
    original_text: str,
    enhanced_text: str,
    mode: str,
    canonical_mode: str,
    word_count_before: int,
    word_count_after: int,
    quality_score: int,
    readability: float | None,
    readability_label: str | None,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    created_at = datetime.now(timezone.utc).isoformat()
    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO rewrite_history (
                created_at, original_text, enhanced_text, mode, canonical_mode,
                word_count_before, word_count_after, quality_score, readability,
                readability_label, metrics_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                original_text,
                enhanced_text,
                mode,
                canonical_mode,
                word_count_before,
                word_count_after,
                quality_score,
                readability,
                readability_label,
                json.dumps(metrics, ensure_ascii=False),
            ),
        )
        row = connection.execute(
            "SELECT * FROM rewrite_history WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    if row is None:
        raise RuntimeError("The saved rewrite could not be read back from SQLite.")
    return _record_from_row(row)


def list_rewrites(limit: int = 100) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM rewrite_history ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_record_from_row(row) for row in rows]


def get_rewrite(record_id: int) -> dict[str, Any] | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM rewrite_history WHERE id = ?", (record_id,)
        ).fetchone()
    return _record_from_row(row) if row is not None else None


def delete_rewrites() -> int:
    with connect() as connection:
        cursor = connection.execute("DELETE FROM rewrite_history")
        return cursor.rowcount
