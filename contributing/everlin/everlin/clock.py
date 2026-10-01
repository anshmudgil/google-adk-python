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

"""Office clock. Gold Coast stays on AEST (UTC+10) all year."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone

AEST = timezone(timedelta(hours=10))


def at_morning(day: date) -> datetime:
  return datetime(day.year, day.month, day.day, 6, 30, tzinfo=AEST)


def add_business_days(day: date, count: int) -> date:
  """Return the date `count` weekdays after `day`."""
  current = day
  left = count
  while left:
    current += timedelta(days=1)
    if current.weekday() < 5:
      left -= 1
  return current
