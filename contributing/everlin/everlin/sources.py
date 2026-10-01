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

"""Simulated Phase 1 sources. No network calls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta


@dataclass(frozen=True)
class SourceRecord:
  source: str
  agent: str
  kind: str
  retrieved_at: datetime
  summary: str
  available: bool


_MAX_AGE = {
    "macro": timedelta(days=1),
    "filing": timedelta(days=1),
    "news": timedelta(hours=1),
    "listing": timedelta(days=1),
    "demographics": timedelta(days=3650),
    "planning": timedelta(days=1),
}


def default_records(now: datetime) -> tuple[SourceRecord, ...]:
  """Six fixtures, three for each analyst, stamped at `now`."""
  return (
      SourceRecord(
          "FRED",
          "investment",
          "macro",
          now,
          "Cash rate is unchanged on the fixture print. A 25 basis "
          "point rise is the signal carried for the property desk.",
          True,
      ),
      SourceRecord(
          "SEC EDGAR",
          "investment",
          "filing",
          now,
          "No new 10-K in the fixture set this morning.",
          True,
      ),
      SourceRecord(
          "AFR",
          "investment",
          "news",
          now,
          "Overnight wires are quiet in the fixture set.",
          True,
      ),
      SourceRecord(
          "ABS",
          "property",
          "demographics",
          now,
          "Queensland population growth remains above the prior release.",
          True,
      ),
      SourceRecord(
          "State Planning Portal",
          "property",
          "planning",
          now,
          "No zoning amendment in the watched Gold Coast LGAs.",
          True,
      ),
      SourceRecord(
          "Domain Listings",
          "property",
          "listing",
          now,
          "No new development site cleared the fixture filter.",
          True,
      ),
  )


def freshness_note(record: SourceRecord, now: datetime) -> str | None:
  """Return a low-confidence note when the record is stale or down."""
  if not record.available:
    return f"{record.source} unavailable. Confidence on this section: low."
  limit = _MAX_AGE[record.kind]
  if now - record.retrieved_at > limit:
    return f"{record.source} is stale. Confidence on this section: low."
  return None
