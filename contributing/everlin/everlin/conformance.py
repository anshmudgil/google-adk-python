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

"""Template checks for the Phase 1 checklist."""

from __future__ import annotations

import re

from .behaviour import filler_violations

_LEANS = (
    "CONDITIONAL PROCEED",
    "PROCEED",
    "DEFER",
    "DECLINE",
    "WATCH",
)

_INVESTMENT_HEADINGS = (
    "## 1. Opportunity in One Sentence",
    "## 2. Structure",
    "## 3. Fee Load / Valuation / Entry Economics",
    "## 4. Bull Case / Bear Case",
    "## 5. Edge Assessment",
    "## 6. The Question This Screening Does Not Answer",
    "## 7. What Is Needed Before IC Paper",
    "## 8. Walk-Away Triggers",
    "## 9. Position",
)

_PROPERTY_HEADINGS = (
    "## 1. Opportunity in One Sentence",
    "## 2. Site Snapshot",
    "## 3. Preliminary Feasibility",
    "## 4. Location and Demand",
    "## 5. Bull Case / Bear Case",
    "## 6. Edge Assessment",
    "## 7. Non-Negotiable Filter Check",
    "## 8. What Is Needed Before Acquisition Memo",
    "## 9. Walk-Away Triggers",
    "## 10. Position",
)

_PROPERTY_FILTERS = (
    "Within target corridor?",
    "Zoning supports intended product?",
    "Infrastructure exists (not just promised)?",
    "Affordable end product achievable?",
    "Brand alignment (Mosaic plays only)?",
    "Council DA timeline acceptable?",
)

_THESIS = (
    "## Header",
    "## Why We Own It",
    "## What Our Conviction Is Based On",
    "## Thesis Break Triggers",
    "## Edge Classification",
    "## Framework",
    "## Review Dates",
    "Last Reviewed:",
)

_SITE = (
    "## Header",
    "## Why This Site",
    "## What We Would Build",
    "## The Margin",
    "## The Risks",
    "## Edge Classification",
    "## Thesis Break Triggers",
    "## Framework",
    "## Status",
    "## Review Dates",
    "Last Reviewed:",
)

_DAILY = (
    "## Overnight Moves",
    "## Earnings and Filings",
    "## Macro Data",
    "## Escalations",
    "## Property Listing Alerts",
)

_WEEKLY = (
    "## Market Pulse",
    "## Portfolio Snapshot",
    "## Property Pipeline",
    "## Investment Pipeline",
    "## Cross-Domain Signals",
    "## Action Items and Upcoming Decisions",
)


def investment_screen_failures(text: str) -> list[str]:
  return _screen_failures(
      text,
      _INVESTMENT_HEADINGS,
      r"EVL-INV-SCR-\d{4}-\d{2}",
  )


def property_screen_failures(text: str) -> list[str]:
  failures = _screen_failures(
      text,
      _PROPERTY_HEADINGS,
      r"EVL-PROP-SCR-\d{4}-\d{2}",
  )
  failures.extend(_missing(text, _PROPERTY_FILTERS))
  return failures


def thesis_failures(text: str) -> list[str]:
  return _missing(text, _THESIS) + filler_violations(text)


def site_thesis_failures(text: str) -> list[str]:
  return _missing(text, _SITE) + filler_violations(text)


def daily_failures(text: str) -> list[str]:
  failures = _missing(text, _DAILY)
  if not re.search(r"EVL-DAILY-\d{4}-\d{2}-\d{2}", text):
    failures.append("missing daily reference")
  failures.extend(filler_violations(text))
  return failures


def weekly_failures(text: str) -> list[str]:
  failures = _missing(text, _WEEKLY)
  if not re.search(r"EVL-WEEKLY-\d{4}-\d{2}-\d{2}", text):
    failures.append("missing weekly reference")
  failures.extend(filler_violations(text))
  return failures


def _screen_failures(
    text: str, headings: tuple[str, ...], reference: str
) -> list[str]:
  failures = _missing(text, headings)
  if not re.search(reference, text):
    failures.append("missing document reference")
  if not any(f"Lean: {lean}" in text for lean in _LEANS):
    failures.append("missing lean")
  if not re.search(r"Edge Type: [A-F]", text):
    failures.append("missing edge type")
  if not re.search(r"Escalation: (GREEN|AMBER|RED)", text):
    failures.append("missing escalation")
  if not re.search(r"WALK AWAY|DECLINE|REDUCE BID|DEFER", text):
    failures.append("missing walk-away consequence")
  failures.extend(filler_violations(text))
  return failures


def _missing(text: str, required: tuple[str, ...]) -> list[str]:
  return [item for item in required if item not in text]
