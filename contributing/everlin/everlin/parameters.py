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

"""Appendix A parameters. Null means the principal has not confirmed."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

UNCONFIRMED_FIELDS = (
    "cash_buffer_minimum_pct",
    "land_cost_ratio_ceiling_pct",
    "position_sizing_maximum_pct",
    "illiquidity_ceiling_pct",
    "buffett_allocation_low_pct",
    "buffett_allocation_high_pct",
    "triguboff_allocation_low_pct",
    "triguboff_allocation_high_pct",
    "sector_concentration_threshold_pct",
    "geographic_concentration_threshold_pct",
)


class ParametersUnconfirmed(Exception):
  """Raised when live mode is requested before Appendix A is locked."""

  def __init__(self, names: tuple[str, ...]):
    self.names = names
    joined = ", ".join(names)
    super().__init__(f"Appendix A parameters unconfirmed: {joined}")


@dataclass(frozen=True)
class OfficeParameters:
  """Confirmed constants plus the Appendix A register."""

  brief_version: str
  entity: str
  base_currency: str
  domicile: str
  principal: str
  cash_buffer_minimum_pct: float | None
  land_cost_ratio_ceiling_pct: float | None
  position_sizing_maximum_pct: float | None
  illiquidity_ceiling_pct: float | None
  buffett_allocation_low_pct: float | None
  buffett_allocation_high_pct: float | None
  triguboff_allocation_low_pct: float | None
  triguboff_allocation_high_pct: float | None
  sector_concentration_threshold_pct: float | None
  geographic_concentration_threshold_pct: float | None
  development_margin_minimum_pct: float
  margin_of_safety_minimum_pct: float
  fee_drag_ceiling_pct: float
  private_equity_net_irr_floor_pct: float
  private_credit_net_floor_pct: float
  going_concern_yield_floor_pct: float
  vacancy_undersupply_pct: float
  monthly_holding_cost_pct_of_tdc: float
  stress_cost_uplift: float
  stress_price_decline: float
  stress_timeline_months: int

  def unconfirmed(self) -> tuple[str, ...]:
    missing = []
    for name in UNCONFIRMED_FIELDS:
      if getattr(self, name) is None:
        missing.append(name)
    return tuple(missing)

  @property
  def live_ready(self) -> bool:
    return not self.unconfirmed()

  @classmethod
  def from_dict(cls, raw: dict) -> OfficeParameters:
    optional = set(UNCONFIRMED_FIELDS)
    values = {}
    for name in cls.__dataclass_fields__:
      if name not in raw:
        raise ValueError(f"missing parameter {name}")
      value = raw[name]
      if name in optional or value is None:
        values[name] = value
      elif name == "brief_version":
        values[name] = str(value)
      elif name in {
          "entity",
          "base_currency",
          "domicile",
          "principal",
      }:
        values[name] = str(value)
      elif name == "stress_timeline_months":
        values[name] = int(value)
      else:
        values[name] = float(value)
    return cls(**values)

  @classmethod
  def load(cls, path: Path | str) -> OfficeParameters:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return cls.from_dict(raw)
