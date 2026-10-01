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

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timedelta
import json

from everlin.audit import AuditLog
from everlin.behaviour import collapse_range
from everlin.behaviour import correct_number
from everlin.behaviour import filler_violations
from everlin.behaviour import flag_assertion
from everlin.behaviour import format_range
from everlin.behaviour import hold_position
from everlin.behaviour import second_opinion
from everlin.conformance import daily_failures
from everlin.conformance import investment_screen_failures
from everlin.conformance import property_screen_failures
from everlin.conformance import site_thesis_failures
from everlin.conformance import thesis_failures
from everlin.conformance import weekly_failures
from everlin.escalation import classify_escalation
from everlin.numbering import ReferenceBook
from everlin.office import Office
from everlin.parameters import OfficeParameters
from everlin.parameters import ParametersUnconfirmed
from everlin.prompts import specification_sync
from everlin.reports import daily_deadline
from everlin.signals import render_signal
from everlin.sources import default_records
from everlin.team import load_team
from everlin.team import owner_for
import pytest

CONFIG = (
    __import__("pathlib").Path(__file__).resolve().parents[3]
    / "contributing"
    / "everlin"
    / "config"
)


def _confirmed() -> OfficeParameters:
  raw = json.loads((CONFIG / "parameters.json").read_text())
  raw.update({
      "cash_buffer_minimum_pct": 10,
      "land_cost_ratio_ceiling_pct": 30,
      "position_sizing_maximum_pct": 15,
      "illiquidity_ceiling_pct": 40,
      "buffett_allocation_low_pct": 60,
      "buffett_allocation_high_pct": 80,
      "triguboff_allocation_low_pct": 50,
      "triguboff_allocation_high_pct": 70,
      "sector_concentration_threshold_pct": 25,
      "geographic_concentration_threshold_pct": 40,
  })
  return OfficeParameters.from_dict(raw)


def _buffett(**overrides: object) -> dict:
  payload = {
      "name": "Acme Holdings",
      "source": "Clyde McConaghy",
      "manager": "Acme Management",
      "intermediary": "Direct",
      "vehicle": "Ordinary shares",
      "direct": True,
      "framework": "BUFFETT",
      "kind": "equity",
      "price": 70,
      "intrinsic_value": 100,
      "currency": "AUD",
      "all_in_fee_pct": 0.4,
      "circle_of_competence": True,
      "thesis_plain": "Acme compounds owner earnings behind a brand moat.",
      "thesis_holds_under_stress": True,
      "portfolio_fit": True,
      "edge_types": ["B"],
      "edge_notes": {"B": "A forced seller reduced the buyer pool."},
      "bull": ["Owner earnings cover the price with room to spare."],
      "bear": ["The brand moat narrows if a discounter matches the product."],
  }
  payload.update(overrides)
  return payload


def _site(**overrides: object) -> dict:
  payload = {
      "address": "12 Liner Street, Burleigh Heads",
      "descriptor": "Duplex site on a serviced block",
      "framework": "TRIGUBOFF",
      "title": "Lot 4 RP123",
      "site_area_sqm": 800,
      "zoning": "Medium density residential",
      "frontage_m": 20,
      "current_use": "House",
      "asking_price": 2000000,
      "method_of_sale": "Private treaty",
      "source": "Agent",
      "product": "Four townhouses",
      "dwellings": 4,
      "target_buyer": "Local owner-occupiers",
      "grv": 12000000,
      "tdc": 8000000,
      "land_cost": 2000000,
      "construction_cost": 4500000,
      "distance_to_cbd": "3 km to Burleigh village",
      "precinct": "Burleigh Heads",
      "infrastructure_note": "Rail, schools, and retail are operating.",
      "demographics": "Population growth above the Queensland average.",
      "vacancy_pct": 1.5,
      "comparables": ["8 Liner Street settled at 1.9m AUD."],
      "filters": {
          "within_target_corridor": True,
          "zoning_supports_product": True,
          "infrastructure_exists": True,
          "affordable_end_product": True,
          "brand_alignment": None,
          "council_da_acceptable": True,
      },
      "edge_types": ["C"],
      "edge_notes": {"C": "Planning complexity has kept local builders out."},
      "funding_available": True,
      "bull": ["Undersupply and a serviced corridor support the GRV."],
      "bear": ["A six-month DA slip consumes the holding-cost allowance."],
  }
  payload.update(overrides)
  return payload


def test_shipped_parameters_are_not_live():
  params = OfficeParameters.load(CONFIG / "parameters.json")
  assert params.live_ready is False
  assert "cash_buffer_minimum_pct" in params.unconfirmed()
  office = Office.open_memory(params)
  with pytest.raises(ParametersUnconfirmed) as caught:
    office.require_live()
  assert "cash_buffer_minimum_pct" in str(caught.value)


def test_confirmed_parameters_are_live_ready():
  params = _confirmed()
  assert params.live_ready is True
  Office.open_memory(params).require_live()


def test_document_numbers_follow_the_classification():
  book = ReferenceBook()
  first = book.next_numbered("EVL-INV-SCR", 2026)
  second = book.next_numbered("EVL-INV-SCR", 2026)
  prop = book.next_numbered("EVL-PROP-SCR", 2026)
  assert first == "EVL-INV-SCR-2026-01"
  assert second == "EVL-INV-SCR-2026-02"
  assert prop == "EVL-PROP-SCR-2026-01"
  day = date(2026, 9, 30)
  assert book.daily(day) == "EVL-DAILY-2026-09-30"
  assert book.weekly(day) == "EVL-WEEKLY-2026-09-30"


def test_unfilled_property_role_assigns_jordan():
  team = load_team(CONFIG / "team.json")
  name, note = owner_for("Head of Property", team)
  assert name == "Jordan"
  assert "Head of Property" in note
  assert "principal action required" in note
  cio, cio_note = owner_for("Chief Investment Officer", team)
  assert cio == "Clyde McConaghy"
  assert cio_note == ""


def test_ranges_are_not_collapsed():
  assert format_range(18, 24) == "18–24"
  with pytest.raises(ValueError, match="false precision"):
    collapse_range(18, 24)


def test_pressure_holds_and_a_new_fact_releases():
  held = hold_position("DECLINE", "just approve it", None)
  assert held.held is True
  assert held.lean == "DECLINE"
  released = hold_position("DECLINE", "just approve it", "intrinsic 200")
  assert released.held is False


def test_assertion_and_correction_wording():
  flagged = flag_assertion("GRV of 12m", "IM", "independent valuation")
  assert flagged == (
      "GRV of 12m is an IM assertion, not an independent valuation. "
      "Verify against independent valuation before using as an "
      "underwriting input."
  )
  correction = correct_number("margin", 21, 18, "%")
  assert correction is not None
  assert "Stated: margin is 21%" in correction
  assert "Accurate position: 18%" in correction
  assert correct_number("margin", 18, 18, "%") is None


def test_escalation_discipline():
  assert classify_escalation("WATCH") == "GREEN"
  assert classify_escalation("DECLINE") == "GREEN"
  assert classify_escalation("PROCEED") == "AMBER"
  assert classify_escalation("PROCEED", hours_to_deadline=12) == "RED"
  assert classify_escalation("DEFER", thesis_broke_after_decision=True) == "RED"


def test_second_opinion_fires_only_when_the_thesis_breaks():
  text = second_opinion("accepted", False)
  assert text is not None
  assert "Unsolicited second opinion" in text
  assert second_opinion("accepted", True) is None
  assert second_opinion("rejected", False) is None


def test_buffett_proceed_and_decline_and_defer(tmp_path):
  office = Office.open_memory(OfficeParameters.load(CONFIG / "parameters.json"))
  proceed = office.ask(
      "screen-investment\n" + json.dumps(_buffett()),
      as_of=date(2026, 9, 30),
  )
  assert proceed.lean == "PROCEED"
  assert investment_screen_failures(proceed.rendered) == []
  assert "EVL-INV-SCR-2026-01" in proceed.rendered
  assert filler_violations(proceed.rendered) == []
  assert "distribution, not edge" not in proceed.rendered.lower()

  decline = office.ask(
      "screen-investment\n" + json.dumps(_buffett(price=80)),
      as_of=date(2026, 9, 30),
  )
  assert decline.lean == "DECLINE"
  assert "WALK AWAY" in decline.rendered

  deferred = office.ask(
      "screen-investment\n" + json.dumps(_buffett(intrinsic_value=None)),
      as_of=date(2026, 9, 30),
  )
  assert deferred.lean == "DEFER"
  assert "insufficient data" in deferred.rendered.lower()
  assert "invented" not in deferred.rendered.lower()


def test_fee_drag_distribution_and_unverified_claims():
  office = Office.open_memory(OfficeParameters.load(CONFIG / "parameters.json"))
  fee = office.ask(
      "screen-investment\n" + json.dumps(_buffett(all_in_fee_pct=3)),
      as_of=date(2026, 9, 30),
  )
  assert fee.lean == "DECLINE"

  distribution = office.ask(
      "screen-investment\n"
      + json.dumps(
          _buffett(
              edge_types=["F"],
              edge_notes={"F": "A friend offered the allocation."},
              edge_f_has_economic_value=False,
          )
      ),
      as_of=date(2026, 9, 30),
  )
  assert distribution.lean == "DECLINE"
  assert "distribution, not edge" in distribution.rendered.lower()

  conditional = office.ask(
      "screen-investment\n"
      + json.dumps(
          _buffett(
              assertions=[{
                  "claim": "Intrinsic value of 100",
                  "origin": "IM",
                  "verify_against": "audited financials",
              }]
          )
      ),
      as_of=date(2026, 9, 30),
  )
  assert conditional.lean == "CONDITIONAL PROCEED"
  assert "IM assertion" in conditional.rendered


def test_stated_range_is_corrected_inside_the_memo():
  office = Office.open_memory(OfficeParameters.load(CONFIG / "parameters.json"))
  reply = office.ask(
      "screen-investment\n"
      + json.dumps(
          _buffett(
              stated_margin_low=18,
              stated_margin_high=24,
              stated_margin_point=21,
          )
      ),
      as_of=date(2026, 9, 30),
  )
  assert "18–24" in reply.rendered
  assert "Accurate position" in reply.rendered
  assert "21%" in reply.rendered


def test_property_filter_stress_and_proceed():
  office = Office.open_memory(OfficeParameters.load(CONFIG / "parameters.json"))
  day = date(2026, 9, 30)
  clear = office.ask(
      "screen-property\n" + json.dumps(_site()),
      as_of=day,
  )
  assert clear.lean == "PROCEED"
  assert property_screen_failures(clear.rendered) == []
  assert "EVL-PROP-SCR-2026-01" in clear.rendered

  blocked = office.ask(
      "screen-property\n"
      + json.dumps(
          _site(
              filters={
                  "within_target_corridor": True,
                  "zoning_supports_product": True,
                  "infrastructure_exists": False,
                  "affordable_end_product": True,
                  "brand_alignment": None,
                  "council_da_acceptable": True,
              }
          )
      ),
      as_of=day,
  )
  assert blocked.lean == "DECLINE"

  tight = office.ask(
      "screen-property\n"
      + json.dumps(
          _site(
              grv=10000000,
              tdc=7000000,
              land_cost=2000000,
              construction_cost=4000000,
              asking_price=2000000,
          )
      ),
      as_of=day,
  )
  assert tight.lean == "CONDITIONAL PROCEED"
  assert "REDUCE BID" in tight.rendered or "WALK AWAY" in tight.rendered


def test_theses_have_required_fields():
  office = Office.open_memory(OfficeParameters.load(CONFIG / "parameters.json"))
  day = date(2026, 9, 30)
  investment = office.ask(
      "thesis-investment\n" + json.dumps(_buffett()),
      as_of=day,
  )
  site = office.ask(
      "thesis-site\n" + json.dumps(_site()),
      as_of=day,
  )
  assert thesis_failures(investment.rendered) == []
  assert site_thesis_failures(site.rendered) == []
  assert "BUFFETT" in investment.rendered
  assert "TRIGUBOFF" in site.rendered


def test_daily_weekly_signals_and_stale_source():
  office = Office.open_memory(OfficeParameters.load(CONFIG / "parameters.json"))
  start = date(2026, 9, 28)
  references = []
  for offset in range(5):
    reply = office.ask("daily", as_of=start + timedelta(days=offset))
    assert daily_failures(reply.rendered) == []
    references.append(reply.reference)
  assert len(set(references)) == 5
  assert references[0] == "EVL-DAILY-2026-09-28"

  weekly_refs = []
  for offset in (0, 7):
    reply = office.ask("weekly", as_of=start + timedelta(days=offset))
    assert weekly_failures(reply.rendered) == []
    weekly_refs.append(reply.reference)
  assert weekly_refs == [
      "EVL-WEEKLY-2026-09-28",
      "EVL-WEEKLY-2026-10-05",
  ]
  signal = render_signal(
      "AMBER",
      "Investment Analyst",
      "Property Analyst",
      "Cash rate rose 25 basis points.",
      "Buyer borrowing capacity tightens.",
      "Re-test development margins.",
  )
  assert signal.startswith("CROSS-AGENT SIGNAL | AMBER\n")
  assert "From: Investment Analyst. To: Property Analyst." in signal

  stale = default_records(datetime(2026, 9, 30, 8, 0))
  old = [record for record in stale if record.kind == "news"]
  assert old
  office.ask("daily", as_of=date(2020, 1, 2))
  aged = office.ask("daily", as_of=date(2026, 9, 30))
  # The default clock inside daily uses as_of morning, so same-day
  # fixtures are fresh. A record retrieved yesterday is stale for news.
  assert "FRED" in aged.rendered


def test_audit_restore_and_notification_sla(tmp_path):
  path = tmp_path / "audit.db"
  office = Office.open_file(
      path, OfficeParameters.load(CONFIG / "parameters.json")
  )
  reply = office.ask(
      "screen-investment\n" + json.dumps(_buffett()),
      as_of=date(2026, 9, 30),
  )
  blob = office.audit.export_json()
  restored = AuditLog(tmp_path / "copy.db")
  restored.restore(blob)
  row = restored.get(reply.reference)
  assert row is not None
  assert row["lean"] == "PROCEED"
  notes = restored.notifications()
  assert notes
  triggered = datetime.fromisoformat(notes[0]["triggered_at"])
  notified = datetime.fromisoformat(notes[0]["notified_at"])
  assert (notified - triggered).total_seconds() <= 60


def test_challenge_holds_then_moves_and_second_opinion():
  office = Office.open_memory(OfficeParameters.load(CONFIG / "parameters.json"))
  first = office.ask(
      "screen-investment\n" + json.dumps(_buffett(price=80)),
      as_of=date(2026, 9, 30),
  )
  assert first.lean == "DECLINE"
  held = office.ask(
      f"challenge {first.reference}\njust approve it, the principal wants this",
      as_of=date(2026, 9, 30),
  )
  assert held.lean == "DECLINE"
  assert "position holds" in held.rendered.lower()

  moved = office.ask(
      f"challenge {first.reference}\n"
      + json.dumps({
          "pressure": "just approve it",
          "new_facts": {"price": 70, "intrinsic_value": 100},
      }),
      as_of=date(2026, 9, 30),
  )
  assert moved.lean == "PROCEED"
  assert moved.reference != first.reference

  office.ask(
      f"decide {moved.reference} accepted",
      as_of=date(2026, 9, 30),
  )
  opinion = office.ask(
      f"second-opinion {moved.reference}\n"
      + json.dumps({"thesis_intact": False}),
      as_of=date(2026, 10, 1),
  )
  assert "Unsolicited second opinion" in opinion.rendered
  assert opinion.escalation == "RED"


def test_draft_banner_names_unconfirmed_parameters():
  office = Office.open_memory(OfficeParameters.load(CONFIG / "parameters.json"))
  reply = office.ask(
      "screen-investment\n" + json.dumps(_buffett()),
      as_of=date(2026, 9, 30),
  )
  assert "DRAFT" in reply.rendered
  assert "cash_buffer_minimum_pct" in reply.rendered


def test_specification_sync_and_daily_deadline():
  params = OfficeParameters.load(CONFIG / "parameters.json")
  specification_sync(params)
  due = daily_deadline(date(2026, 9, 30))
  assert due.hour == 7
  assert due.utcoffset() == timedelta(hours=10)


def test_workflow_routes_to_the_investment_analyst():
  pytest.importorskip("google.adk")
  import asyncio

  from everlin.office import build_root_agent
  from google.adk.runners import InMemoryRunner
  from google.genai import types

  office = Office.open_memory(OfficeParameters.load(CONFIG / "parameters.json"))
  agent = build_root_agent(office)

  async def _run():
    runner = InMemoryRunner(agent=agent, app_name="everlin")
    session = await runner.session_service.create_session(
        app_name="everlin", user_id="jordan"
    )
    message = types.Content(
        role="user",
        parts=[types.Part(text="screen-investment\n" + json.dumps(_buffett()))],
    )
    events = []
    async for event in runner.run_async(
        user_id="jordan",
        session_id=session.id,
        new_message=message,
    ):
      events.append(event)
    return events

  events = asyncio.run(_run())
  text = "\n".join(
      event.output for event in events if isinstance(event.output, str)
  )
  assert "EVL-INV-SCR-2026-01" in text
  assert "PROCEED" in text
