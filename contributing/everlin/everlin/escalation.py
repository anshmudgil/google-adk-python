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

"""Green, amber, and red. Not every item is urgent."""

from __future__ import annotations

_ACTIONABLE = {"PROCEED", "CONDITIONAL PROCEED", "DEFER"}


def classify_escalation(
    lean: str,
    *,
    hours_to_deadline: float | None = None,
    material_risk: bool = False,
    thesis_broke_after_decision: bool = False,
) -> str:
  """Map a lean and its context to GREEN, AMBER, or RED."""
  if material_risk or thesis_broke_after_decision:
    return "RED"
  deadline_is_today = hours_to_deadline is not None and hours_to_deadline <= 24
  if deadline_is_today and lean in {"PROCEED", "CONDITIONAL PROCEED"}:
    return "RED"
  if lean in _ACTIONABLE:
    return "AMBER"
  return "GREEN"
