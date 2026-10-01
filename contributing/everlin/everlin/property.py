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

"""Property screening. Filters outrank an attractive margin."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .behaviour import flag_assertion
from .clock import add_business_days
from .escalation import classify_escalation
from .investment import WalkAway
from .parameters import OfficeParameters
from .team import owner_for
from .team import TeamMember
from .textutil import num

_FILTERS = (
    "within_target_corridor",
    "zoning_supports_product",
    "infrastructure_exists",
    "affordable_end_product",
    "brand_alignment",
    "council_da_acceptable",
)

_FILTER_LABELS = {
    "within_target_corridor": "Within target corridor?",
    "zoning_supports_product": "Zoning supports intended product?",
    "infrastructure_exists": "Infrastructure exists (not just promised)?",
    "affordable_end_product": "Affordable end product achievable?",
    "brand_alignment": "Brand alignment (Mosaic plays only)?",
    "council_da_acceptable": "Council DA timeline acceptable?",
}


@dataclass(frozen=True)
class PropertyScreen:
  address: str
  framework: str
  edge_types: tuple[str, ...]
  lean: str
  escalation: str
  confidence: str
  one_sentence: str
  snapshot: str
  feasibility: str
  location: str
  bull: tuple[str, ...]
  bear: tuple[str, ...]
  edge_assessment: str
  filters_text: str
  needed: tuple[str, ...]
  walk_aways: tuple[WalkAway, ...]
  position: str
  product: str
  margin_text: str
  risks: tuple[str, ...]
  payload: dict


def screen_property(payload: dict, params: OfficeParameters) -> PropertyScreen:
  data = _require(payload)
  fails: list[str] = []
  gaps: list[str] = []
  filter_rows = _filter_rows(data)
  for label, status in filter_rows:
    if status == "Fail":
      fails.append(f"Non-negotiable filter failed: {label}")
  if any(status == "UNKNOWN" for _, status in filter_rows):
    gaps.append("Insufficient data: a filter status is UNKNOWN.")
  _vacancy(data, params, fails, gaps)
  _funding(data, fails, gaps)
  feasibility, walks, margin_text = _feasibility(data, params, fails, gaps)
  if not data["bear"]:
    gaps.append("Insufficient data: bear case was not supplied.")
  if not data["bull"]:
    gaps.append("Insufficient data: bull case was not supplied.")
  _edge_checks(data, fails)
  assertions = _assertions(data)
  lean = _lean(fails, gaps, assertions)
  escalation = classify_escalation(
      lean,
      hours_to_deadline=data["hours_to_deadline"],
      material_risk=data["material_risk"],
  )
  return PropertyScreen(
      address=data["address"],
      framework=data["framework"],
      edge_types=data["edge_types"],
      lean=lean,
      escalation=escalation,
      confidence=_confidence(lean),
      one_sentence=_one_sentence(data),
      snapshot=_snapshot(data),
      feasibility=feasibility,
      location=_location(data),
      bull=tuple(data["bull"]),
      bear=tuple(data["bear"]),
      edge_assessment=_edge_text(data, fails),
      filters_text=_filters_text(filter_rows),
      needed=_needed(data, gaps),
      walk_aways=tuple(walks),
      position=_position(data, lean),
      product=data["product"],
      margin_text=margin_text,
      risks=tuple(data["bear"]) or ("Bear case was not supplied.",),
      payload=payload,
  )


def render_property_screen(
    screen: PropertyScreen,
    *,
    reference: str,
    as_of: date,
    draft_note: str,
    team: tuple[TeamMember, ...],
) -> str:
  owner, note = owner_for("Head of Property", team)
  deadline = add_business_days(as_of, 5).isoformat()
  note_text = f" {note}" if note else ""
  needed = [
      f"{index}. {item} — {owner}.{note_text} Deadline: {deadline}."
      for index, item in enumerate(screen.needed, start=1)
  ]
  if not needed:
    needed.append(
        f"1. Confirm the maximum bid with {owner}.{note_text} "
        f"Deadline: {deadline}."
    )
  walks = [
      f"{index}. {item.condition} — {item.consequence}"
      for index, item in enumerate(screen.walk_aways, start=1)
  ]
  parts = [
      draft_note.strip(),
      "EVERLIN FAMILY OFFICE — PROPERTY SCREENING MEMO",
      screen.address,
      f"Reference: {reference}",
      f"Date: {as_of.isoformat()}",
      f"Framework: {screen.framework}",
      f"Edge Type: {', '.join(screen.edge_types)}",
      f"Lean: {screen.lean}",
      f"Escalation: {screen.escalation}",
      "Classification: Confidential",
      "",
      "## 1. Opportunity in One Sentence",
      "",
      screen.one_sentence,
      "",
      "## 2. Site Snapshot",
      "",
      screen.snapshot,
      "",
      "## 3. Preliminary Feasibility",
      "",
      screen.feasibility,
      "",
      "## 4. Location and Demand",
      "",
      screen.location,
      "",
      "## 5. Bull Case / Bear Case",
      "",
      "\n".join(f"- {item}" for item in screen.bull),
      "",
      "\n".join(f"- {item}" for item in screen.bear),
      "",
      "## 6. Edge Assessment",
      "",
      screen.edge_assessment,
      "",
      "## 7. Non-Negotiable Filter Check",
      "",
      screen.filters_text,
      "",
      "## 8. What Is Needed Before Acquisition Memo",
      "",
      "\n".join(needed),
      "",
      "## 9. Walk-Away Triggers",
      "",
      "\n".join(walks),
      "",
      "## 10. Position",
      "",
      screen.position,
  ]
  return "\n".join(part for part in parts if part is not None).strip() + "\n"


def render_site_thesis(
    screen: PropertyScreen,
    *,
    as_of: date,
    draft_note: str,
) -> str:
  risks = "\n".join(f"- {item}" for item in screen.risks[:5])
  triggers = "\n".join(f"- {item.condition}" for item in screen.walk_aways[:4])
  why = (
      f"{screen.address} fits a {screen.framework} play. {screen.one_sentence}"
  )
  build = (
      f"Product: {screen.product}. "
      f"Buyer: {screen.payload.get('target_buyer', 'Not stated')}."
  )
  parts = [
      draft_note.strip(),
      f"## Header\n\n{screen.address}",
      f"## Why This Site\n\n{why}",
      f"## What We Would Build\n\n{build}",
      f"## The Margin\n\n{screen.margin_text}",
      f"## The Risks\n\n{risks}",
      (
          "## Edge Classification\n\n"
          f"{', '.join(screen.edge_types)} — {screen.edge_assessment}"
      ),
      f"## Thesis Break Triggers\n\n{triggers}",
      f"## Framework\n\n{screen.framework}",
      "## Status\n\nSCREENING",
      f"## Review Dates\n\nLast Reviewed: {as_of.isoformat()}",
  ]
  return "\n\n".join(part for part in parts if part).strip() + "\n"


def _require(payload: dict) -> dict:
  required = (
      "address",
      "framework",
      "source",
      "product",
      "asking_price",
      "edge_types",
      "bull",
      "bear",
      "filters",
  )
  for key in required:
    if key not in payload:
      raise ValueError(f"missing {key}")
  if payload["framework"] not in {"TRIGUBOFF", "MOSAIC"}:
    raise ValueError("framework must be TRIGUBOFF or MOSAIC")
  edges = tuple(payload["edge_types"])
  for edge in edges:
    if edge not in set("ABCDEF"):
      raise ValueError(f"unknown edge {edge}")
  data = dict(payload)
  data["edge_types"] = edges
  data["edge_notes"] = dict(payload.get("edge_notes") or {})
  data["filters"] = dict(payload["filters"])
  data["bull"] = list(payload["bull"])
  data["bear"] = list(payload["bear"])
  data["assertions"] = list(payload.get("assertions") or [])
  data["needed"] = list(payload.get("needed") or [])
  data["comparables"] = list(payload.get("comparables") or [])
  for key in (
      "grv",
      "tdc",
      "land_cost",
      "construction_cost",
      "current_noi",
      "market_noi",
      "vacancy_pct",
      "hours_to_deadline",
      "funding_available",
      "edge_f_has_economic_value",
  ):
    data.setdefault(key, None)
  data.setdefault("material_risk", False)
  data.setdefault("currency", "AUD")
  data.setdefault("title", "Not stated")
  data.setdefault("site_area_sqm", None)
  data.setdefault("zoning", "Not stated")
  data.setdefault("frontage_m", None)
  data.setdefault("current_use", "Not stated")
  data.setdefault("method_of_sale", "Not stated")
  data.setdefault("distance_to_cbd", "Not stated")
  data.setdefault("precinct", "Not stated")
  data.setdefault("infrastructure_note", "Not stated")
  data.setdefault("demographics", "Not stated")
  data.setdefault("dwellings", None)
  data.setdefault("target_buyer", "Not stated")
  return data


def _filter_rows(data: dict) -> list[tuple[str, str]]:
  rows = []
  framework = data["framework"]
  filters = data["filters"]
  for key in _FILTERS:
    label = _FILTER_LABELS[key]
    value = filters.get(key)
    rows.append((label, _status(key, value, framework)))
  return rows


def _status(key: str, value: object, framework: str) -> str:
  if key == "brand_alignment" and framework == "TRIGUBOFF" and value is None:
    return "N/A"
  if value is None:
    return "UNKNOWN"
  if value is True:
    return "Pass"
  if value is False:
    return "Fail"
  raise ValueError(f"filter {key} must be true, false, or null")


def _filters_text(rows: list[tuple[str, str]]) -> str:
  return "\n".join(f"{label} {status}" for label, status in rows)


def _vacancy(
    data: dict,
    params: OfficeParameters,
    fails: list[str],
    gaps: list[str],
) -> None:
  if data["framework"] != "TRIGUBOFF" or data["grv"] is None:
    return
  vacancy = data["vacancy_pct"]
  if vacancy is None:
    gaps.append("Insufficient data: vacancy was not supplied.")
    return
  ceiling = params.vacancy_undersupply_pct
  if float(vacancy) >= ceiling:
    fails.append(
        f"Vacancy {num(float(vacancy))}% is not below the "
        f"{num(ceiling)}% undersupply test."
    )


def _funding(data: dict, fails: list[str], gaps: list[str]) -> None:
  funding = data["funding_available"]
  if funding is False:
    fails.append("Funding is not available.")
  elif funding is None:
    gaps.append("Insufficient data: funding was not assessed.")


def _feasibility(
    data: dict,
    params: OfficeParameters,
    fails: list[str],
    gaps: list[str],
) -> tuple[str, list[WalkAway], str]:
  currency = data["currency"]
  walks = [
      WalkAway("Any non-negotiable filter at Fail", "DECLINE"),
  ]
  grv = data["grv"]
  tdc = data["tdc"]
  land = data["land_cost"]
  construction = data["construction_cost"]
  if None not in (grv, tdc, land, construction):
    return _development(data, params, fails, gaps, walks, currency)
  if data["current_noi"] is not None:
    return _income(data, params, fails, gaps, walks, currency)
  gaps.append(
      "Insufficient data: neither development costs nor NOI were supplied."
  )
  return (
      "Insufficient data: feasibility inputs were not supplied.",
      walks,
      "Insufficient data: margin cannot be stated.",
  )


def _development(
    data: dict,
    params: OfficeParameters,
    fails: list[str],
    gaps: list[str],
    walks: list[WalkAway],
    currency: str,
) -> tuple[str, list[WalkAway], str]:
  grv = float(data["grv"])
  tdc = float(data["tdc"])
  land = float(data["land_cost"])
  construction = float(data["construction_cost"])
  if tdc <= 0 or grv <= 0:
    gaps.append("Insufficient data: GRV and TDC must be positive.")
    return ("Insufficient data.", walks, "Insufficient data.")
  uplift = construction * params.stress_cost_uplift
  hold = (
      tdc
      * (params.monthly_holding_cost_pct_of_tdc / 100)
      * params.stress_timeline_months
  )
  price_grv = grv * (1 - params.stress_price_decline)
  scenarios = {
      "Base case": (grv, tdc),
      "Cost stress": (grv, tdc + uplift),
      "Price stress": (price_grv, tdc),
      "Timeline stress": (grv, tdc + hold),
      "Combined stress": (price_grv, tdc + uplift + hold),
  }
  lines = [
      f"GRV {num(grv)} {currency}. TDC {num(tdc)} {currency}.",
      (
          "Timeline stress adds "
          f"{num(params.monthly_holding_cost_pct_of_tdc)}% of base TDC "
          f"per month for {params.stress_timeline_months} months as an "
          "agent calculation. It is not an independent valuation."
      ),
  ]
  for name, (sale, cost) in scenarios.items():
    lines.append(f"{name}: margin {num(_margin(sale, cost))}%.")
  combined = _margin(price_grv, tdc + uplift + hold)
  base = _margin(grv, tdc)
  floor = params.development_margin_minimum_pct
  other = (tdc - land) + uplift + hold
  max_tdc = price_grv / (1 + floor / 100)
  max_land = round(max_tdc - other, 2)
  lines.append(
      f"Maximum land bid that still clears {num(floor)}% under "
      f"combined stress: {num(max_land)} {currency}."
  )
  ratio = land / grv * 100
  ceiling = params.land_cost_ratio_ceiling_pct
  if ceiling is None:
    lines.append(
        "Land cost ratio ceiling is unconfirmed. "
        f"Ratio is {num(ratio)}% of GRV. No breach can be declared."
    )
  elif ratio > ceiling:
    lines.append(
        f"Land cost ratio {num(ratio)}% exceeds the {num(ceiling)}% ceiling."
    )
  if base < floor:
    fails.append(
        f"Base margin {num(base)}% is below the {num(floor)}% minimum."
    )
  if combined < floor and max_land <= 0:
    fails.append("No positive land bid clears the combined stress margin.")
  elif combined < floor:
    gaps.append("Combined stress margin is below 20% at the asking land price.")
  walks.append(
      WalkAway(
          f"Bid above {num(max_land)} {currency}",
          "WALK AWAY",
      )
  )
  walks.append(
      WalkAway(
          f"Combined stress margin below {num(floor)}% at the asking price",
          "REDUCE BID",
      )
  )
  for item in _assertions(data):
    lines.append(item)
  margin_text = (
      f"Base margin {num(base)}%. Combined stress margin {num(combined)}%."
  )
  return ("\n".join(lines), walks, margin_text)


def _income(
    data: dict,
    params: OfficeParameters,
    fails: list[str],
    gaps: list[str],
    walks: list[WalkAway],
    currency: str,
) -> tuple[str, list[WalkAway], str]:
  asking = float(data["asking_price"])
  current = float(data["current_noi"])
  if asking <= 0:
    gaps.append("Insufficient data: asking price must be positive.")
    return ("Insufficient data.", walks, "Insufficient data.")
  cap = current / asking * 100
  floor = params.going_concern_yield_floor_pct
  lines = [
      (
          f"Current NOI {num(current)} {currency}. "
          f"Cap rate {num(cap)}% (agent calculation)."
      ),
  ]
  market = data["market_noi"]
  if market is not None:
    market_cap = float(market) / asking * 100
    lines.append(
        f"Market NOI {num(float(market))} {currency}. "
        f"Market cap rate {num(market_cap)}%."
    )
  if cap < floor:
    fails.append(f"Cap rate {num(cap)}% is below the {num(floor)}% floor.")
  walks.append(WalkAway(f"Cap rate below {num(floor)}%", "DECLINE"))
  text = f"Cap rate {num(cap)}%."
  return ("\n".join(lines), walks, text)


def _margin(sale: float, cost: float) -> float:
  return (sale - cost) / cost * 100


def _assertions(data: dict) -> tuple[str, ...]:
  return tuple(
      flag_assertion(item["claim"], item["origin"], item["verify_against"])
      for item in data["assertions"]
  )


_CONDITIONAL_GAPS = {
    "Combined stress margin is below 20% at the asking land price.",
    "Insufficient data: a filter status is UNKNOWN.",
}


def _lean(
    fails: list[str], gaps: list[str], assertions: tuple[str, ...]
) -> str:
  if fails:
    return "DECLINE"
  hard_gaps = [gap for gap in gaps if gap not in _CONDITIONAL_GAPS]
  if hard_gaps:
    return "DEFER"
  if gaps or assertions:
    return "CONDITIONAL PROCEED"
  return "PROCEED"


def _confidence(lean: str) -> str:
  if lean == "DEFER":
    return "low"
  if lean == "CONDITIONAL PROCEED":
    return "medium"
  return "high"


def _one_sentence(data: dict) -> str:
  edges = ", ".join(data["edge_types"]) or "none"
  return (
      f"{data['address']} offers {data['product']} at an asking "
      f"price of {num(float(data['asking_price']))} {data['currency']} "
      f"and the edge is {edges}."
  )


def _snapshot(data: dict) -> str:
  area = data["site_area_sqm"]
  area_text = "Not stated" if area is None else f"{num(float(area))} sqm"
  frontage = data["frontage_m"]
  front_text = "Not stated" if frontage is None else f"{num(float(frontage))} m"
  return "\n".join([
      f"Address: {data['address']}. Source: {data['source']}.",
      f"Title: {data['title']}.",
      f"Site Area: {area_text}.",
      f"Zoning: {data['zoning']}.",
      f"Frontage: {front_text}.",
      f"Current Use: {data['current_use']}.",
      f"Asking Price: {num(float(data['asking_price']))} {data['currency']}.",
      f"Method of Sale: {data['method_of_sale']}.",
  ])


def _location(data: dict) -> str:
  comps = data["comparables"] or ["No comparable was supplied."]
  vacancy = data["vacancy_pct"]
  vacancy_text = (
      "Vacancy was not supplied."
      if vacancy is None
      else f"Vacancy {num(float(vacancy))}%."
  )
  return "\n".join([
      f"Distance to CBD: {data['distance_to_cbd']}.",
      f"Precinct: {data['precinct']}.",
      f"Infrastructure: {data['infrastructure_note']}.",
      f"Demographics: {data['demographics']}.",
      vacancy_text,
      "Comparables: " + " ".join(comps),
  ])


def _edge_checks(data: dict, fails: list[str]) -> None:
  edges = data["edge_types"]
  if not edges:
    fails.append("This is distribution, not edge.")
  elif edges == ("F",) and not data["edge_f_has_economic_value"]:
    fails.append("This is distribution, not edge.")


def _edge_text(data: dict, fails: list[str]) -> str:
  lines = []
  for edge in data["edge_types"]:
    note = data["edge_notes"].get(edge, "No note was supplied.")
    lines.append(f"Type {edge}. {note}")
  if any("distribution, not edge" in item.lower() for item in fails):
    answer = "This is distribution, not edge."
  else:
    answer = (
        "Everlin is the buyer because the stated edge removes "
        "competitors, not because the site was offered."
    )
  lines.append(f"Why is Everlin the right buyer at this price? {answer}")
  buyer = _buyer_pool(data)
  lines.append(buyer)
  return "\n".join(lines)


def _buyer_pool(data: dict) -> str:
  if data["framework"] == "TRIGUBOFF":
    return (
        "Buyer pool: local buyers who can afford the end product. "
        "Builders who will not do the planning work are excluded."
    )
  return (
      "Buyer pool: owner-occupiers in the precinct. "
      "Investor-only product is excluded."
  )


def _needed(data: dict, gaps: list[str]) -> tuple[str, ...]:
  return tuple([*data["needed"], *gaps])


def _position(data: dict, lean: str) -> str:
  first = (
      f"I screen {data['address']} as a {data['framework']} play "
      f"with lean {lean}."
  )
  second = (
      f"The introduction from {data['source']} is noted. "
      "The relationship does not change the lean."
  )
  third = (
      "A failed filter or a combined-stress margin under 20% ends "
      "the screen. I will not talk the margin back up."
  )
  return f"{first}\n\n{second}\n\n{third}"
