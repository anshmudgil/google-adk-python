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

"""Deterministic checks for the behaviour standards that code can enforce."""

from __future__ import annotations

from dataclasses import dataclass

from .textutil import num

_BANNED = (
    "great question",
    "i'd be happy",
    "hope this helps",
    "as an ai",
    "certainly!",
)

_ORIGINS = {"IM", "agent", "pitch"}


@dataclass(frozen=True)
class HoldResult:
  lean: str
  held: bool
  reason: str


def format_range(low: float, high: float) -> str:
  """Render a range. Equal endpoints stay a single figure."""
  if high < low:
    raise ValueError("high is below low")
  if low == high:
    return num(low)
  return f"{num(low)}–{num(high)}"


def collapse_range(low: float, high: float) -> str:
  """Refuse to publish a midpoint in place of a range."""
  raise ValueError(
      f"false precision: report {format_range(low, high)}, not a midpoint"
  )


def flag_assertion(claim: str, origin: str, verify_against: str) -> str:
  if origin not in _ORIGINS:
    raise ValueError(f"origin must be one of {sorted(_ORIGINS)}")
  return (
      f"{claim} is an {origin} assertion, not an independent "
      f"valuation. Verify against {verify_against} before using as "
      "an underwriting input."
  )


def correct_number(
    label: str, stated: float, actual: float, unit: str
) -> str | None:
  if stated == actual:
    return None
  return (
      f"Stated: {label} is {num(stated)}{unit}. "
      "Incorrect: that figure does not match the calculation. "
      f"Accurate position: {num(actual)}{unit}."
  )


def hold_position(lean: str, message: str, new_fact: str | None) -> HoldResult:
  """Keep the lean unless a new fact was actually supplied."""
  del message  # Pressure wording does not count as evidence.
  if new_fact and new_fact.strip():
    return HoldResult(
        lean,
        False,
        "new information supplied; re-screen required",
    )
  return HoldResult(lean, True, "no new information; position holds")


def second_opinion(decision: str, thesis_intact: bool) -> str | None:
  if decision == "accepted" and not thesis_intact:
    return (
        "Unsolicited second opinion: the logged decision was "
        "accepted and the thesis has since broken. Review the "
        "position."
    )
  return None


def filler_violations(text: str) -> list[str]:
  lowered = text.lower()
  return [phrase for phrase in _BANNED if phrase in lowered]
