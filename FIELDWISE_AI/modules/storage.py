"""SQLite storage for KAIRO: saved fields and their recommendation history.

Uses only the standard library (sqlite3). The database is one local file,
``data/kairo.db`` by default, or the path in the KAIRO_DB_PATH environment variable.
It is created automatically on first use. Nothing leaves the machine.

Only the farmer's own answers and the computed plan are stored: no keys, no secrets.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "kairo.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS saved_plans (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT    NOT NULL,
    place         TEXT    NOT NULL,
    state         TEXT,
    soil_label    TEXT,
    water_label   TEXT,
    latitude      REAL,
    longitude     REAL,
    grid_id       TEXT,
    top_rotation  TEXT,
    top_score     REAL,
    profile_json  TEXT    NOT NULL,
    plan_json     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_saved_plans_created ON saved_plans (created_at DESC);
"""


def db_path() -> Path:
    """Database location, read each call so tests and deployments can override it."""
    override = os.environ.get("KAIRO_DB_PATH", "").strip()
    return Path(override) if override else DEFAULT_DB_PATH


def _connect(path: Optional[Path] = None) -> sqlite3.Connection:
    target = Path(path) if path else db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _json_default(value: Any):
    """Make numpy/pandas scalars JSON-safe without importing them."""
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def _top_of(plan: dict) -> tuple[Optional[str], Optional[float]]:
    rotations = plan.get("rotations") or []
    if not rotations:
        return None, None
    best = rotations[0]
    label = " → ".join(c["crop_name"] for c in best["crop_sequence"])
    return label, float(best["overall_rotation_score"])


def save_plan(profile: dict, plan: dict, path: Optional[Path] = None) -> int:
    """Store one recommendation. Returns its id."""
    top, score = _top_of(plan)
    with closing(_connect(path)) as conn, conn:
        cur = conn.execute(
            """INSERT INTO saved_plans
               (created_at, place, state, soil_label, water_label, latitude, longitude, grid_id,
                top_rotation, top_score, profile_json, plan_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                str(profile.get("district") or plan.get("district") or "Unknown place"),
                profile.get("state"),
                profile.get("soil_label"),
                profile.get("water_label"),
                profile.get("latitude"),
                profile.get("longitude"),
                profile.get("grid_id"),
                top,
                score,
                json.dumps(profile, default=_json_default),
                json.dumps(plan, default=_json_default),
            ),
        )
        return int(cur.lastrowid)


def list_plans(limit: int = 20, path: Optional[Path] = None) -> list[dict]:
    """Most recent first. Light rows only (no full plan)."""
    with closing(_connect(path)) as conn:
        rows = conn.execute(
            """SELECT id, created_at, place, state, soil_label, water_label, top_rotation, top_score
               FROM saved_plans ORDER BY created_at DESC, id DESC LIMIT ?""",
            (int(limit),),
        ).fetchall()
    return [dict(r) for r in rows]


def load_plan(plan_id: int, path: Optional[Path] = None) -> Optional[tuple[dict, dict]]:
    """Return (profile, plan) for an id, or None if it does not exist."""
    with closing(_connect(path)) as conn:
        row = conn.execute(
            "SELECT profile_json, plan_json FROM saved_plans WHERE id = ?", (int(plan_id),)
        ).fetchone()
    if row is None:
        return None
    return json.loads(row["profile_json"]), json.loads(row["plan_json"])


def delete_plan(plan_id: int, path: Optional[Path] = None) -> bool:
    with closing(_connect(path)) as conn, conn:
        cur = conn.execute("DELETE FROM saved_plans WHERE id = ?", (int(plan_id),))
        return cur.rowcount > 0


def count_plans(path: Optional[Path] = None) -> int:
    with closing(_connect(path)) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM saved_plans").fetchone()[0])
