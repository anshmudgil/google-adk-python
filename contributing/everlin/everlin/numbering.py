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

"""Document classification numbers from Section 16."""

from __future__ import annotations

from datetime import date


class ReferenceBook:
  """In-memory sequence. The audit log keeps the durable copy."""

  def __init__(self) -> None:
    self._counts: dict[tuple[str, int], int] = {}

  def next_numbered(self, prefix: str, year: int) -> str:
    key = (prefix, year)
    self._counts[key] = self._counts.get(key, 0) + 1
    return f"{prefix}-{year}-{self._counts[key]:02d}"

  def daily(self, day: date) -> str:
    return f"EVL-DAILY-{day.isoformat()}"

  def weekly(self, day: date) -> str:
    return f"EVL-WEEKLY-{day.isoformat()}"
