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

"""Small text helpers shared by the analysts."""

from __future__ import annotations


def num(value: float) -> str:
  """Format a magnitude without false trailing precision."""
  rounded = round(float(value), 2)
  if rounded == int(rounded):
    return str(int(rounded))
  return f"{rounded:.2f}".rstrip("0").rstrip(".")
