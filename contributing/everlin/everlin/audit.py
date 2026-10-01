# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Decision audit trail. One SQLite file is the institutional memory."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sqlite3

_TABLES = (
    "recommendations",
    "signals",
    "notifications",
    "sequences",
    "pipeline",
)


class AuditLog:
  """Append-only recommendations with a JSON backup round-trip."""

  def __init__(self, path: str | Path):
    self.path = str(path)
    self._conn = sqlite3.connect(self.path)
    self._conn.row_factory = sqlite3.Row
    self._create()

  def _create(self) -> None:
    self._conn.executescript("""
        CREATE TABLE IF NOT EXISTS recommendations (
          reference TEXT PRIMARY KEY,
          agent TEXT NOT NULL,
          created_at TEXT NOT NULL,
          lean TEXT NOT NULL,
          escalation TEXT NOT NULL,
          reasoning TEXT NOT NULL,
          confidence TEXT NOT NULL,
          sources TEXT NOT NULL,
          payload_json TEXT NOT NULL,
          decision TEXT,
          decision_at TEXT,
          outcome TEXT,
          outcome_at TEXT
        );
        CREATE TABLE IF NOT EXISTS signals (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          created_at TEXT NOT NULL,
          body TEXT NOT NULL,
          level TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notifications (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          reference TEXT NOT NULL,
          level TEXT NOT NULL,
          triggered_at TEXT NOT NULL,
          notified_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sequences (
          prefix TEXT NOT NULL,
          year INTEGER NOT NULL,
          value INTEGER NOT NULL,
          PRIMARY KEY (prefix, year)
        );
        CREATE TABLE IF NOT EXISTS pipeline (
          reference TEXT PRIMARY KEY,
          domain TEXT NOT NULL,
          name TEXT NOT NULL,
          framework TEXT NOT NULL,
          status TEXT NOT NULL,
          next_action TEXT NOT NULL,
          deadline TEXT NOT NULL
        );
        """)
    self._conn.commit()

  def next_reference(self, prefix: str, year: int) -> str:
    row = self._conn.execute(
        "SELECT value FROM sequences WHERE prefix = ? AND year = ?",
        (prefix, year),
    ).fetchone()
    value = 1 if row is None else int(row["value"]) + 1
    self._conn.execute(
        """
        INSERT INTO sequences (prefix, year, value)
        VALUES (?, ?, ?)
        ON CONFLICT(prefix, year) DO UPDATE SET value = excluded.value
        """,
        (prefix, year, value),
    )
    self._conn.commit()
    return f"{prefix}-{year}-{value:02d}"

  def log_recommendation(
      self,
      *,
      reference: str,
      agent: str,
      created_at: datetime,
      lean: str,
      escalation: str,
      reasoning: str,
      confidence: str,
      sources: str,
      payload: dict,
  ) -> None:
    self._conn.execute(
        """
        INSERT INTO recommendations (
          reference, agent, created_at, lean, escalation, reasoning,
          confidence, sources, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reference,
            agent,
            created_at.isoformat(),
            lean,
            escalation,
            reasoning,
            confidence,
            sources,
            json.dumps(payload),
        ),
    )
    self._conn.commit()

  def record_decision(
      self, reference: str, decision: str, at: datetime
  ) -> None:
    allowed = {"accepted", "rejected", "modified", "deferred"}
    if decision not in allowed:
      raise ValueError(f"decision must be one of {sorted(allowed)}")
    updated = self._conn.execute(
        """
        UPDATE recommendations
        SET decision = ?, decision_at = ?
        WHERE reference = ?
        """,
        (decision, at.isoformat(), reference),
    )
    if updated.rowcount != 1:
      raise ValueError(f"no recommendation {reference}")
    self._conn.commit()

  def record_outcome(self, reference: str, outcome: str, at: datetime) -> None:
    updated = self._conn.execute(
        """
        UPDATE recommendations
        SET outcome = ?, outcome_at = ?
        WHERE reference = ?
        """,
        (outcome, at.isoformat(), reference),
    )
    if updated.rowcount != 1:
      raise ValueError(f"no recommendation {reference}")
    self._conn.commit()

  def recommendations(self) -> list[dict]:
    rows = self._conn.execute(
        "SELECT * FROM recommendations ORDER BY reference"
    ).fetchall()
    return [dict(row) for row in rows]

  def get(self, reference: str) -> dict | None:
    row = self._conn.execute(
        "SELECT * FROM recommendations WHERE reference = ?",
        (reference,),
    ).fetchone()
    if row is None:
      return None
    return dict(row)

  def add_signal(self, body: str, level: str, at: datetime) -> None:
    self._conn.execute(
        "INSERT INTO signals (created_at, body, level) VALUES (?, ?, ?)",
        (at.isoformat(), body, level),
    )
    self._conn.commit()

  def signals(self) -> list[dict]:
    rows = self._conn.execute("SELECT * FROM signals ORDER BY id").fetchall()
    return [dict(row) for row in rows]

  def notify(self, reference: str, level: str, at: datetime) -> None:
    """In-process delivery. notified_at equals triggered_at."""
    stamp = at.isoformat()
    self._conn.execute(
        """
        INSERT INTO notifications (
          reference, level, triggered_at, notified_at
        ) VALUES (?, ?, ?, ?)
        """,
        (reference, level, stamp, stamp),
    )
    self._conn.commit()

  def notifications(self) -> list[dict]:
    rows = self._conn.execute(
        "SELECT * FROM notifications ORDER BY id"
    ).fetchall()
    return [dict(row) for row in rows]

  def pipeline_add(
      self,
      *,
      reference: str,
      domain: str,
      name: str,
      framework: str,
      status: str,
      next_action: str,
      deadline: str,
  ) -> None:
    self._conn.execute(
        """
        INSERT OR REPLACE INTO pipeline (
          reference, domain, name, framework, status, next_action,
          deadline
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reference,
            domain,
            name,
            framework,
            status,
            next_action,
            deadline,
        ),
    )
    self._conn.commit()

  def pipeline(self, domain: str | None = None) -> list[dict]:
    if domain is None:
      rows = self._conn.execute(
          "SELECT * FROM pipeline ORDER BY reference"
      ).fetchall()
    else:
      rows = self._conn.execute(
          "SELECT * FROM pipeline WHERE domain = ? ORDER BY reference",
          (domain,),
      ).fetchall()
    return [dict(row) for row in rows]

  def export_json(self) -> str:
    payload = {}
    for table in _TABLES:
      rows = self._conn.execute(f"SELECT * FROM {table}").fetchall()
      payload[table] = [dict(row) for row in rows]
    return json.dumps(payload)

  def restore(self, blob: str) -> None:
    payload = json.loads(blob)
    for table in _TABLES:
      self._conn.execute(f"DELETE FROM {table}")
    self._insert_rows("recommendations", payload.get("recommendations", []))
    self._insert_rows("signals", payload.get("signals", []))
    self._insert_rows("notifications", payload.get("notifications", []))
    self._insert_rows("sequences", payload.get("sequences", []))
    self._insert_rows("pipeline", payload.get("pipeline", []))
    self._conn.commit()

  def _insert_rows(self, table: str, rows: list[dict]) -> None:
    for row in rows:
      columns = list(row)
      placeholders = ", ".join("?" for _ in columns)
      names = ", ".join(columns)
      self._conn.execute(
          f"INSERT INTO {table} ({names}) VALUES ({placeholders})",
          tuple(row[column] for column in columns),
      )
