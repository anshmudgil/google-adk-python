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

"""Investment screening. The lean is computed, not prompted."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .behaviour import flag_assertion
from .behaviour import format_range
from .clock import add_business_days
from .escalation import classify_escalation
from .parameters import OfficeParameters
from .team import owner_for
from .team import TeamMember
from .textutil import num

_EDGES = set("ABCDEF")
_FRAMEWORKS = {"BUFFETT", "WOOD"}
_KINDS = {"equity", "fund", "credit"}


@dataclass(frozen=True)
class WalkAway:
  condition: str
  consequence: str


@dataclass(frozen=True)
class InvestmentScreen:
  name: str
  source: str
  framework: str
  kind: str
  edge_types: tuple[str, ...]
  lean: str
  escalation: str
  confidence: str
  one_sentence: str
  structure: str
  economics: str
  bull: tuple[str, ...]
  bear: tuple[str, ...]
  edge_assessment: str
  unanswered: str
  needed: tuple[str, ...]
  walk_aways: tuple[WalkAway, ...]
  position: str
  payload: dict


def screen_investment(
    payload: dict, params: OfficeParameters
) -> InvestmentScreen:
  """Apply the Section 17 hierarchy and return a structured screen."""
  data = _require(payload)
  fails: list[str] = []
  gaps: list[str] = []
  if not data["circle_of_competence"]:
    fails.append("Outside the circle of competence.")
  thesis = data["thesis_holds_under_stress"]
  if thesis is False:
    fails.append("The thesis does not hold under stress.")
  elif thesis is None:
    gaps.append("Insufficient data: thesis stress was not assessed.")
  _price_checks(data, params, fails, gaps)
  fit = data["portfolio_fit"]
  if fit is False:
    fails.append("The position does not fit the portfolio.")
  elif fit is None:
    gaps.append("Insufficient data: portfolio fit was not assessed.")
  if not data["bear"]:
    gaps.append("Insufficient data: bear case was not supplied.")
  if not data["bull"]:
    gaps.append("Insufficient data: bull case was not supplied.")
  _edge_checks(data, fails)
  assertions = _assertions(data)
  lean = _lean(fails, gaps, assertions)
  edges = data["edge_types"]
  walk_aways = _walk_aways(data, params)
  if not walk_aways:
    gaps.append("Insufficient data: no numeric exit is available.")
    lean = _lean(fails, gaps, assertions)
  escalation = classify_escalation(
      lean,
      hours_to_deadline=data["hours_to_deadline"],
      material_risk=data["material_risk"],
  )
  return InvestmentScreen(
      name=data["name"],
      source=data["source"],
      framework=data["framework"],
      kind=data["kind"],
      edge_types=edges,
      lean=lean,
      escalation=escalation,
      confidence=_confidence(lean),
      one_sentence=_one_sentence(data),
      structure=_structure(data),
      economics=_economics(data, params),
      bull=tuple(data["bull"]),
      bear=tuple(data["bear"]),
      edge_assessment=_edge_text(data, fails),
      unanswered=_unanswered(data, gaps, assertions),
      needed=_needed(data, gaps),
      walk_aways=tuple(walk_aways),
      position=_position(data, lean),
      payload=payload,
  )


def render_investment_screen(
    screen: InvestmentScreen,
    *,
    reference: str,
    as_of: date,
    draft_note: str,
    team: tuple[TeamMember, ...],
) -> str:
  owner, note = owner_for("Chief Investment Officer", team)
  deadline = add_business_days(as_of, 5).isoformat()
  note_text = f" {note}" if note else ""
  needed_lines = []
  for index, item in enumerate(screen.needed, start=1):
    needed_lines.append(
        f"{index}. {item} — {owner}.{note_text} Deadline: {deadline}."
    )
  if not needed_lines:
    needed_lines.append(
        f"1. Confirm the walk-away price with {owner}.{note_text} "
        f"Deadline: {deadline}."
    )
  walks = [
      f"{index}. {item.condition} — {item.consequence}"
      for index, item in enumerate(screen.walk_aways, start=1)
  ]
  bulls = "\n".join(f"- {item}" for item in screen.bull)
  bears = "\n".join(f"- {item}" for item in screen.bear)
  parts = [
      draft_note.strip(),
      "EVERLIN FAMILY OFFICE — INVESTMENT SCREENING MEMO",
      screen.name,
      f"Source: {screen.source}",
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
      "## 2. Structure",
      "",
      screen.structure,
      "",
      "## 3. Fee Load / Valuation / Entry Economics",
      "",
      screen.economics,
      "",
      "## 4. Bull Case / Bear Case",
      "",
      bulls,
      "",
      bears,
      "",
      "## 5. Edge Assessment",
      "",
      screen.edge_assessment,
      "",
      "## 6. The Question This Screening Does Not Answer",
      "",
      screen.unanswered,
      "",
      "## 7. What Is Needed Before IC Paper",
      "",
      "\n".join(needed_lines),
      "",
      "## 8. Walk-Away Triggers",
      "",
      "\n".join(walks),
      "",
      "## 9. Position",
      "",
      screen.position,
  ]
  return "\n".join(part for part in parts if part is not None).strip() + "\n"


def render_investment_thesis(
    screen: InvestmentScreen,
    *,
    as_of: date,
    draft_note: str,
) -> str:
  bullets = "\n".join(f"- {item}" for item in _conviction(screen))
  triggers = "\n".join(f"- {item.condition}" for item in screen.walk_aways[:4])
  why = (
      f"We would own {screen.name} as a {screen.framework} position. "
      f"{screen.one_sentence}"
  )
  parts = [
      draft_note.strip(),
      f"## Header\n\n{screen.name}",
      f"## Why We Own It\n\n{why}",
      f"## What Our Conviction Is Based On\n\n{bullets}",
      f"## Thesis Break Triggers\n\n{triggers}",
      (
          "## Edge Classification\n\n"
          f"{', '.join(screen.edge_types)} — {screen.edge_assessment}"
      ),
      f"## Framework\n\n{screen.framework}",
      f"## Review Dates\n\nLast Reviewed: {as_of.isoformat()}",
  ]
  body = "\n\n".join(part for part in parts if part)
  return body.strip() + "\n"


def _conviction(screen: InvestmentScreen) -> tuple[str, ...]:
  points = [screen.payload.get("thesis_plain", ""), *screen.bull]
  cleaned = tuple(item for item in points if item)
  while len(cleaned) < 3:
    cleaned = (*cleaned, "Primary documents still have to be read.")
  return cleaned[:5]


def _require(payload: dict) -> dict:
  required = (
      "name",
      "source",
      "manager",
      "intermediary",
      "vehicle",
      "direct",
      "framework",
      "kind",
      "circle_of_competence",
      "thesis_plain",
      "edge_types",
      "bull",
      "bear",
  )
  for key in required:
    if key not in payload:
      raise ValueError(f"missing {key}")
  framework = payload["framework"]
  if framework not in _FRAMEWORKS:
    raise ValueError(f"framework must be one of {sorted(_FRAMEWORKS)}")
  kind = payload["kind"]
  if kind not in _KINDS:
    raise ValueError(f"kind must be one of {sorted(_KINDS)}")
  edges = tuple(payload["edge_types"])
  for edge in edges:
    if edge not in _EDGES:
      raise ValueError(f"unknown edge {edge}")
  data = dict(payload)
  data["edge_types"] = edges
  data["edge_notes"] = dict(payload.get("edge_notes") or {})
  data["bull"] = list(payload["bull"])
  data["bear"] = list(payload["bear"])
  data["assertions"] = list(payload.get("assertions") or [])
  data["needed"] = list(payload.get("needed") or [])
  data.setdefault("price", None)
  data.setdefault("intrinsic_value", None)
  data.setdefault("currency", "AUD")
  data.setdefault("all_in_fee_pct", None)
  data.setdefault("net_irr_pct", None)
  data.setdefault("net_yield_pct", None)
  data.setdefault("tam", "")
  data.setdefault("adoption_priced_in", None)
  data.setdefault("thesis_holds_under_stress", None)
  data.setdefault("portfolio_fit", None)
  data.setdefault("edge_f_has_economic_value", None)
  data.setdefault("senior_secured", None)
  data.setdefault("hours_to_deadline", None)
  data.setdefault("material_risk", False)
  data.setdefault("stated_margin_low", None)
  data.setdefault("stated_margin_high", None)
  data.setdefault("stated_margin_point", None)
  return data


def _price_checks(
    data: dict,
    params: OfficeParameters,
    fails: list[str],
    gaps: list[str],
) -> None:
  fee = data["all_in_fee_pct"]
  if fee is not None and fee > params.fee_drag_ceiling_pct:
    fails.append(
        f"All-in fee {num(fee)}% exceeds the "
        f"{num(params.fee_drag_ceiling_pct)}% ceiling."
    )
  kind = data["kind"]
  if kind == "equity" and data["framework"] == "BUFFETT":
    _buffett_price(data, params, fails, gaps)
  elif kind == "equity" and data["framework"] == "WOOD":
    _wood_price(data, fails, gaps)
  elif kind == "fund":
    irr = data["net_irr_pct"]
    floor = params.private_equity_net_irr_floor_pct
    if irr is None:
      gaps.append("Insufficient data: net IRR was not supplied.")
    elif irr < floor:
      fails.append(f"Net IRR {num(irr)}% is below the {num(floor)}% floor.")
  elif kind == "credit":
    _credit_price(data, params, fails, gaps)


def _buffett_price(
    data: dict,
    params: OfficeParameters,
    fails: list[str],
    gaps: list[str],
) -> None:
  price = data["price"]
  intrinsic = data["intrinsic_value"]
  if price is None or intrinsic is None:
    gaps.append("Insufficient data: intrinsic value was not supplied.")
    return
  if intrinsic <= 0 or price <= 0:
    gaps.append(
        "Insufficient data: price and intrinsic value must be positive."
    )
    return
  margin = (intrinsic - price) / intrinsic * 100
  floor = params.margin_of_safety_minimum_pct
  if margin < floor:
    fails.append(
        f"Margin of safety is {num(margin)}%, below the {num(floor)}% minimum."
    )


def _wood_price(data: dict, fails: list[str], gaps: list[str]) -> None:
  if not data["tam"]:
    gaps.append("Insufficient data: TAM was not supplied.")
  priced = data["adoption_priced_in"]
  if priced is None:
    gaps.append("Insufficient data: adoption pricing was not assessed.")
  elif priced:
    fails.append("The market has already priced the adoption curve.")


def _credit_price(
    data: dict,
    params: OfficeParameters,
    fails: list[str],
    gaps: list[str],
) -> None:
  if data["senior_secured"] is False:
    fails.append("The instrument is not senior secured.")
  elif data["senior_secured"] is None:
    gaps.append("Insufficient data: seniority was not stated.")
  yield_pct = data["net_yield_pct"]
  floor = params.private_credit_net_floor_pct
  if yield_pct is None:
    gaps.append("Insufficient data: net yield was not supplied.")
  elif yield_pct < floor:
    fails.append(
        f"Net yield {num(yield_pct)}% is below the {num(floor)}% floor."
    )
  gaps.append(
      "Insufficient data: interest coverage under a stressed rate "
      "was not supplied. This screen does not run a full ICR model."
  )


def _edge_checks(data: dict, fails: list[str]) -> None:
  edges = data["edge_types"]
  if not edges:
    fails.append("This is distribution, not edge.")
    return
  only_access = edges == ("F",) and not data["edge_f_has_economic_value"]
  if only_access:
    fails.append(
        "This is distribution, not edge. Access without economic "
        "value is a channel, not a reason to buy."
    )


def _assertions(data: dict) -> tuple[str, ...]:
  flagged = []
  for item in data["assertions"]:
    flagged.append(
        flag_assertion(item["claim"], item["origin"], item["verify_against"])
    )
  return tuple(flagged)


def _lean(
    fails: list[str], gaps: list[str], assertions: tuple[str, ...]
) -> str:
  if fails:
    return "DECLINE"
  if gaps:
    return "DEFER"
  if assertions:
    return "CONDITIONAL PROCEED"
  return "PROCEED"


def _confidence(lean: str) -> str:
  if lean == "DEFER":
    return "low"
  if lean == "CONDITIONAL PROCEED":
    return "medium"
  return "high"


def _one_sentence(data: dict) -> str:
  price = data["price"]
  currency = data["currency"]
  if price is None:
    return (
        f"{data['name']} is a {data['framework']} {data['kind']} "
        f"offered by {data['intermediary']}, and no entry price "
        "was supplied."
    )
  return (
      f"{data['name']} is a {data['framework']} {data['kind']} "
      f"offered by {data['intermediary']} at {num(price)} {currency}."
  )


def _structure(data: dict) -> str:
  direct = "yes" if data["direct"] else "no"
  return (
      f"Manager: {data['manager']}. Intermediary: {data['intermediary']}. "
      f"Vehicle: {data['vehicle']}. Direct access: {direct}."
  )


def _economics(data: dict, params: OfficeParameters) -> str:
  lines = []
  fee = data["all_in_fee_pct"]
  if fee is None:
    lines.append("All-in fee was not supplied.")
  else:
    lines.append(f"All-in fee: {num(fee)}% p.a.")
  if data["framework"] == "BUFFETT" and data["kind"] == "equity":
    lines.append(_buffett_economics(data, params))
  elif data["framework"] == "WOOD":
    tam = data["tam"] or "Insufficient data: TAM was not supplied."
    lines.append(f"TAM: {tam}")
  if data["kind"] == "fund" and data["net_irr_pct"] is not None:
    lines.append(f"Net IRR: {num(data['net_irr_pct'])}%.")
  for item in data["assertions"]:
    lines.append(
        flag_assertion(item["claim"], item["origin"], item["verify_against"])
    )
  low = data["stated_margin_low"]
  high = data["stated_margin_high"]
  point = data["stated_margin_point"]
  if low is not None and high is not None:
    rendered = format_range(float(low), float(high))
    lines.append(f"Stated margin range: {rendered}%.")
    if point is not None and not (low == high == point):
      lines.append(
          f"Stated: margin is {num(float(point))}%. "
          "Incorrect: that figure collapses a range into false precision. "
          f"Accurate position: {rendered}%."
      )
  return "\n".join(lines)


def _buffett_economics(data: dict, params: OfficeParameters) -> str:
  price = data["price"]
  intrinsic = data["intrinsic_value"]
  if price is None or intrinsic is None or intrinsic <= 0:
    return (
        "Insufficient data: intrinsic value was not supplied. "
        "No intrinsic value is stated because the input was absent."
    )
  margin = (intrinsic - price) / intrinsic * 100
  floor = params.margin_of_safety_minimum_pct
  ceiling = intrinsic * (1 - floor / 100)
  return (
      f"Intrinsic value {num(intrinsic)} {data['currency']} against "
      f"price {num(price)}. Margin of safety {num(margin)}% "
      f"(agent calculation). Walk-away price is {num(ceiling)} "
      f"{data['currency']}."
  )


def _edge_text(data: dict, fails: list[str]) -> str:
  notes = data["edge_notes"]
  paragraphs = []
  for edge in data["edge_types"]:
    detail = notes.get(edge, "No note was supplied for this edge.")
    paragraphs.append(f"Type {edge}. {detail}")
  if not paragraphs:
    paragraphs.append("No edge type was assigned.")
  if any("distribution, not edge" in item.lower() for item in fails):
    answer = "This is distribution, not edge."
  else:
    answer = (
        "Everlin is the buyer because the stated edge is economic, "
        "not because the asset was offered."
    )
  paragraphs.append(f"Why is Everlin the right buyer at this price? {answer}")
  return "\n".join(paragraphs)


def _unanswered(
    data: dict, gaps: list[str], assertions: tuple[str, ...]
) -> str:
  if gaps:
    return gaps[0]
  if assertions:
    return "Whether the unverified claims survive a primary-source check."
  if data["framework"] == "WOOD":
    return "What adoption rate makes this entry price fully priced?"
  return (
      "What happens to owner earnings if the moat is narrower than "
      "the pitch claims?"
  )


def _needed(data: dict, gaps: list[str]) -> tuple[str, ...]:
  items = list(data["needed"])
  items.extend(gaps)
  if data["assertions"]:
    items.append("Verify each flagged assertion against its named source.")
  return tuple(items)


def _walk_aways(data: dict, params: OfficeParameters) -> list[WalkAway]:
  walks: list[WalkAway] = []
  currency = data["currency"]
  intrinsic = data["intrinsic_value"]
  if (
      data["framework"] == "BUFFETT"
      and data["kind"] == "equity"
      and intrinsic not in (None, 0)
      and intrinsic > 0
  ):
    ceiling = intrinsic * (1 - params.margin_of_safety_minimum_pct / 100)
    walks.append(
        WalkAway(
            f"Price above {num(ceiling)} {currency}",
            "WALK AWAY",
        )
    )
  walks.append(
      WalkAway(
          f"All-in fee load above {num(params.fee_drag_ceiling_pct)}% p.a.",
          "DECLINE",
      )
  )
  if data["kind"] == "fund":
    floor = params.private_equity_net_irr_floor_pct
    walks.append(WalkAway(f"Net IRR below {num(floor)}%", "DECLINE"))
  if data["kind"] == "credit":
    floor = params.private_credit_net_floor_pct
    walks.append(WalkAway(f"Net yield below {num(floor)}%", "DECLINE"))
  return walks


def _position(data: dict, lean: str) -> str:
  first = (
      f"I screen {data['name']} as a {data['framework']} "
      f"{data['kind']} with lean {lean}."
  )
  second = (
      f"The introduction from {data['source']} is noted. "
      "The relationship does not change the lean."
  )
  third = (
      "I will move only if a new fact clears a failed check or "
      "fills a named data gap. Pressure is not a fact."
  )
  return f"{first}\n\n{second}\n\n{third}"
