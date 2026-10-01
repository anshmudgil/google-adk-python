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

"""Daily and weekly briefings."""

from __future__ import annotations

from datetime import date
from datetime import datetime

from .clock import AEST
from .sources import freshness_note
from .sources import SourceRecord


def daily_deadline(day: date) -> datetime:
  """07:00 AEST on the briefing date."""
  return datetime(day.year, day.month, day.day, 7, 0, tzinfo=AEST)


def render_daily(
    *,
    as_of: date,
    reference: str,
    records: tuple[SourceRecord, ...],
    now: datetime,
    escalations: list[str],
    draft_note: str,
) -> str:
  by_source = {record.source: record for record in records}
  parts = [
      draft_note.strip(),
      "EVERLIN FAMILY OFFICE — DAILY BRIEFING",
      f"Reference: {reference}",
      f"Date: {as_of.isoformat()}",
      "Classification: Internal",
      "Escalation: GREEN",
      "",
      "## Overnight Moves",
      "",
      _section(by_source["AFR"], now),
      "",
      "## Earnings and Filings",
      "",
      _section(by_source["SEC EDGAR"], now),
      "",
      "## Macro Data",
      "",
      _section(by_source["FRED"], now),
      "",
      "## Escalations",
      "",
      _escalations(escalations),
      "",
      "## Property Listing Alerts",
      "",
      _section(by_source["Domain Listings"], now),
      "",
      _section(by_source["State Planning Portal"], now),
      "",
      _section(by_source["ABS"], now),
  ]
  return "\n".join(part for part in parts if part is not None).strip() + "\n"


def render_weekly(
    *,
    as_of: date,
    reference: str,
    macro: str,
    portfolio: str,
    property_pipeline: str,
    investment_pipeline: str,
    signals: str,
    actions: str,
    draft_note: str,
) -> str:
  parts = [
      draft_note.strip(),
      "EVERLIN FAMILY OFFICE — WEEKLY IC BRIEFING",
      f"Reference: {reference}",
      f"Date: {as_of.isoformat()}",
      "Classification: Internal",
      "Escalation: GREEN",
      "",
      "## Market Pulse",
      "",
      macro,
      "",
      "## Portfolio Snapshot",
      "",
      portfolio,
      "",
      "## Property Pipeline",
      "",
      property_pipeline,
      "",
      "## Investment Pipeline",
      "",
      investment_pipeline,
      "",
      "## Cross-Domain Signals",
      "",
      signals,
      "",
      "## Action Items and Upcoming Decisions",
      "",
      actions,
  ]
  return "\n".join(part for part in parts if part is not None).strip() + "\n"


def _section(record: SourceRecord, now: datetime) -> str:
  note = freshness_note(record, now)
  line = f"{record.source}: {record.summary}"
  if note:
    return f"{line}\n{note}"
  return line


def _escalations(items: list[str]) -> str:
  if not items:
    return "No AMBER or RED escalations are open."
  return "\n".join(f"- {item}" for item in items)
