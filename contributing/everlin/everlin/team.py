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

"""Team directory used to assign action items."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class TeamMember:
  name: str
  role: str
  scope: str
  filled: bool


def load_team(path: Path | str) -> tuple[TeamMember, ...]:
  raw = json.loads(Path(path).read_text(encoding="utf-8"))
  return tuple(
      TeamMember(
          name=item["name"],
          role=item["role"],
          scope=item["scope"],
          filled=bool(item["filled"]),
      )
      for item in raw
  )


def owner_for(role: str, team: tuple[TeamMember, ...]) -> tuple[str, str]:
  """Return the owner name and a note when the role is unfilled."""
  for member in team:
    if member.role == role and member.filled:
      return member.name, ""
  note = (
      "No dedicated resource — principal action required until "
      f"{role} is filled."
  )
  return "Jordan", note
