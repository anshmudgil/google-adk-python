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

"""Chat entry point for the two analysts and the joint briefings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import datetime
import json
from pathlib import Path

from .audit import AuditLog
from .behaviour import hold_position
from .behaviour import second_opinion
from .clock import add_business_days
from .clock import at_morning
from .investment import render_investment_screen
from .investment import render_investment_thesis
from .investment import screen_investment
from .parameters import OfficeParameters
from .parameters import ParametersUnconfirmed
from .property import render_property_screen
from .property import render_site_thesis
from .property import screen_property
from .reports import render_daily
from .reports import render_weekly
from .signals import render_signal
from .sources import default_records
from .team import load_team
from .team import TeamMember

_RATE_SIGNAL = render_signal(
    "AMBER",
    "Investment Analyst",
    "Property Analyst",
    "Cash rate rose 25 basis points.",
    "Buyer borrowing capacity tightens.",
    "Re-test development margins.",
)


@dataclass(frozen=True)
class OfficeReply:
  reference: str
  escalation: str
  rendered: str
  lean: str | None
  agent: str


class Office:
  """Routes a command to an analyst and writes the audit trail."""

  def __init__(
      self,
      parameters: OfficeParameters,
      audit: AuditLog,
      team: tuple[TeamMember, ...],
  ):
    self.parameters = parameters
    self.audit = audit
    self.team = team

  @classmethod
  def open_memory(cls, parameters: OfficeParameters) -> Office:
    return cls(
        parameters,
        AuditLog(":memory:"),
        load_team(config_dir() / "team.json"),
    )

  @classmethod
  def open_file(cls, path: Path | str, parameters: OfficeParameters) -> Office:
    return cls(
        parameters,
        AuditLog(path),
        load_team(config_dir() / "team.json"),
    )

  def require_live(self) -> None:
    missing = self.parameters.unconfirmed()
    if missing:
      raise ParametersUnconfirmed(missing)

  def draft_note(self) -> str:
    missing = self.parameters.unconfirmed()
    if not missing:
      return ""
    names = ", ".join(missing)
    return f"STATUS: DRAFT — Appendix A parameters unconfirmed: {names}."

  def route(self, message: str) -> str:
    """Return investment, property, or joint for the ADK router."""
    head = message.strip().splitlines()[0] if message.strip() else ""
    command = head.split()[0] if head else ""
    if command in {"screen-property", "thesis-site"}:
      return "property"
    if command == "challenge" and "EVL-PROP" in head:
      return "property"
    if command in {"screen-investment", "thesis-investment", "daily"}:
      return "investment"
    if command == "challenge" and "EVL-INV" in head:
      return "investment"
    return "joint"

  def ask(self, message: str, *, as_of: date | None = None) -> OfficeReply:
    day = as_of or datetime.now(at_morning(date.today()).tzinfo).date()
    try:
      return self._dispatch(message, day)
    except ValueError as exc:
      return OfficeReply(
          reference="",
          escalation="GREEN",
          rendered=f"The request is invalid. {exc}\n",
          lean=None,
          agent="Everlin",
      )

  def _dispatch(self, message: str, day: date) -> OfficeReply:
    command, args, body = _split(message)
    stamp = at_morning(day)
    if command == "screen-investment":
      return self._screen_investment(json.loads(body), day, stamp)
    if command == "screen-property":
      return self._screen_property(json.loads(body), day, stamp)
    if command == "thesis-investment":
      return self._thesis_investment(json.loads(body), day)
    if command == "thesis-site":
      return self._thesis_site(json.loads(body), day)
    if command == "daily":
      return self._daily(day, stamp)
    if command == "weekly":
      return self._weekly(day)
    if command == "challenge":
      return self._challenge(args[0], body, day, stamp)
    if command == "decide":
      return self._decide(args[0], args[1], stamp)
    if command == "outcome":
      return self._outcome(args[0], " ".join(args[1:]) or body, stamp)
    if command == "second-opinion":
      return self._opinion(args[0], body, stamp)
    if command == "audit":
      return self._audit_listing()
    if command == "signals":
      return self._signal_listing()
    raise ValueError(
        "No structured request. Use screen-investment, "
        "screen-property, daily, or weekly."
    )

  def _screen_investment(
      self, payload: dict, day: date, stamp: datetime
  ) -> OfficeReply:
    screen = screen_investment(payload, self.parameters)
    reference = self.audit.next_reference("EVL-INV-SCR", day.year)
    text = render_investment_screen(
        screen,
        reference=reference,
        as_of=day,
        draft_note=self.draft_note(),
        team=self.team,
    )
    self._record(
        reference=reference,
        agent="Investment Analyst",
        domain="investment",
        name=screen.name,
        framework=screen.framework,
        lean=screen.lean,
        escalation=screen.escalation,
        confidence=screen.confidence,
        sources=screen.source,
        payload=payload,
        reasoning=text,
        stamp=stamp,
        next_action=screen.needed[0] if screen.needed else "Review the lean.",
        day=day,
    )
    return OfficeReply(
        reference, screen.escalation, text, screen.lean, "Investment Analyst"
    )

  def _screen_property(
      self, payload: dict, day: date, stamp: datetime
  ) -> OfficeReply:
    screen = screen_property(payload, self.parameters)
    reference = self.audit.next_reference("EVL-PROP-SCR", day.year)
    text = render_property_screen(
        screen,
        reference=reference,
        as_of=day,
        draft_note=self.draft_note(),
        team=self.team,
    )
    self._record(
        reference=reference,
        agent="Property Analyst",
        domain="property",
        name=screen.address,
        framework=screen.framework,
        lean=screen.lean,
        escalation=screen.escalation,
        confidence=screen.confidence,
        sources=str(payload.get("source", "payload")),
        payload=payload,
        reasoning=text,
        stamp=stamp,
        next_action=screen.needed[0] if screen.needed else "Review the lean.",
        day=day,
    )
    return OfficeReply(
        reference, screen.escalation, text, screen.lean, "Property Analyst"
    )

  def _thesis_investment(self, payload: dict, day: date) -> OfficeReply:
    screen = screen_investment(payload, self.parameters)
    text = render_investment_thesis(
        screen, as_of=day, draft_note=self.draft_note()
    )
    return OfficeReply(
        "", screen.escalation, text, screen.lean, "Investment Analyst"
    )

  def _thesis_site(self, payload: dict, day: date) -> OfficeReply:
    screen = screen_property(payload, self.parameters)
    text = render_site_thesis(screen, as_of=day, draft_note=self.draft_note())
    return OfficeReply(
        "", screen.escalation, text, screen.lean, "Property Analyst"
    )

  def _daily(self, day: date, stamp: datetime) -> OfficeReply:
    self._maybe_rate_signal(stamp)
    reference = f"EVL-DAILY-{day.isoformat()}"
    open_items = [
        f"{row['reference']} {row['lean']} {row['escalation']}"
        for row in self.audit.recommendations()
        if row["escalation"] in {"AMBER", "RED"}
    ]
    text = render_daily(
        as_of=day,
        reference=reference,
        records=default_records(stamp),
        now=stamp,
        escalations=open_items,
        draft_note=self.draft_note(),
    )
    return OfficeReply(reference, "GREEN", text, None, "Investment Analyst")

  def _weekly(self, day: date) -> OfficeReply:
    reference = f"EVL-WEEKLY-{day.isoformat()}"
    signal_rows = self.audit.signals()
    signal_text = (
        "\n\n".join(row["body"] for row in signal_rows)
        or "No cross-agent signals are on the log."
    )
    deadline = add_business_days(day, 5).isoformat()
    if self.parameters.live_ready:
      actions = "No action items are due."
    else:
      actions = (
          "1. Confirm Appendix A parameters — "
          f"{self.parameters.principal}. Deadline: {deadline}."
      )
    text = render_weekly(
        as_of=day,
        reference=reference,
        macro="Investment Analyst: FRED fixture is the macro input.",
        portfolio=self._portfolio(),
        property_pipeline=self._pipeline_text("property"),
        investment_pipeline=self._pipeline_text("investment"),
        signals=signal_text,
        actions=actions,
        draft_note=self.draft_note(),
    )
    return OfficeReply(reference, "GREEN", text, None, "Joint")

  def _challenge(
      self, reference: str, body: str, day: date, stamp: datetime
  ) -> OfficeReply:
    row = self._require_row(reference)
    payload = json.loads(row["payload_json"])
    pressure, new_facts = _pressure(body)
    new_fact = json.dumps(new_facts) if new_facts else None
    held = hold_position(row["lean"], pressure, new_fact)
    if held.held:
      text = (
          f"Reference: {reference}\n"
          f"Lean: {row['lean']}\n"
          "The position holds. No new information was provided.\n"
      )
      return OfficeReply(
          reference,
          row["escalation"],
          self._with_draft(text),
          row["lean"],
          row["agent"],
      )
    payload.update(new_facts)
    if reference.startswith("EVL-PROP"):
      return self._screen_property(payload, day, stamp)
    return self._screen_investment(payload, day, stamp)

  def _decide(
      self, reference: str, decision: str, stamp: datetime
  ) -> OfficeReply:
    self.audit.record_decision(reference, decision, stamp)
    row = self._require_row(reference)
    text = f"Decision on {reference}: {decision}.\n"
    return OfficeReply(
        reference,
        row["escalation"],
        self._with_draft(text),
        row["lean"],
        row["agent"],
    )

  def _outcome(
      self, reference: str, outcome: str, stamp: datetime
  ) -> OfficeReply:
    self.audit.record_outcome(reference, outcome, stamp)
    row = self._require_row(reference)
    text = f"Outcome on {reference}: {outcome}.\n"
    return OfficeReply(
        reference,
        row["escalation"],
        self._with_draft(text),
        row["lean"],
        row["agent"],
    )

  def _opinion(self, reference: str, body: str, stamp: datetime) -> OfficeReply:
    raw = json.loads(body) if body else {}
    intact = bool(raw.get("thesis_intact", True))
    row = self._require_row(reference)
    text = second_opinion(row["decision"] or "", intact)
    if text is None:
      rendered = f"No second opinion on {reference}.\n"
      return OfficeReply(
          reference,
          row["escalation"],
          self._with_draft(rendered),
          row["lean"],
          row["agent"],
      )
    self.audit.notify(reference, "RED", stamp)
    return OfficeReply(
        reference,
        "RED",
        self._with_draft(text + "\n"),
        row["lean"],
        row["agent"],
    )

  def _audit_listing(self) -> OfficeReply:
    lines = [
        f"{row['reference']} {row['lean']} decision={row['decision']}"
        for row in self.audit.recommendations()
    ]
    body = "\n".join(lines) or "The audit trail is empty."
    return OfficeReply(
        "",
        "GREEN",
        self._with_draft(body + "\n"),
        None,
        "Joint",
    )

  def _signal_listing(self) -> OfficeReply:
    rows = self.audit.signals()
    body = "\n\n".join(row["body"] for row in rows) or "No signals."
    return OfficeReply(
        "",
        "GREEN",
        self._with_draft(body + "\n"),
        None,
        "Joint",
    )

  def _record(
      self,
      *,
      reference: str,
      agent: str,
      domain: str,
      name: str,
      framework: str,
      lean: str,
      escalation: str,
      confidence: str,
      sources: str,
      payload: dict,
      reasoning: str,
      stamp: datetime,
      next_action: str,
      day: date,
  ) -> None:
    self.audit.log_recommendation(
        reference=reference,
        agent=agent,
        created_at=stamp,
        lean=lean,
        escalation=escalation,
        reasoning=reasoning,
        confidence=confidence,
        sources=sources,
        payload=payload,
    )
    if escalation in {"AMBER", "RED"}:
      self.audit.notify(reference, escalation, stamp)
    status = {
        "DECLINE": "DECLINED",
        "WATCH": "WATCH",
    }.get(lean, "SCREENING")
    self.audit.pipeline_add(
        reference=reference,
        domain=domain,
        name=name,
        framework=framework,
        status=status,
        next_action=next_action,
        deadline=add_business_days(day, 5).isoformat(),
    )

  def _maybe_rate_signal(self, stamp: datetime) -> None:
    if any(row["body"] == _RATE_SIGNAL for row in self.audit.signals()):
      return
    self.audit.add_signal(_RATE_SIGNAL, "AMBER", stamp)

  def _portfolio(self) -> str:
    if self.parameters.unconfirmed():
      names = ", ".join(self.parameters.unconfirmed())
      return (
          f"No holdings are loaded. Allocation bands are unconfirmed: {names}."
      )
    return "No holdings are loaded."

  def _pipeline_text(self, domain: str) -> str:
    rows = self.audit.pipeline(domain)
    if not rows:
      return f"No {domain} opportunities are in the pipeline."
    return "\n".join(
        f"- {row['reference']} {row['name']} {row['framework']} "
        f"{row['status']}. Next: {row['next_action']}. "
        f"Deadline: {row['deadline']}."
        for row in rows
    )

  def _require_row(self, reference: str) -> dict:
    row = self.audit.get(reference)
    if row is None:
      raise ValueError(f"no recommendation {reference}")
    return row

  def _with_draft(self, text: str) -> str:
    note = self.draft_note()
    if not note:
      return text
    return f"{note}\n{text}"


def _split(message: str) -> tuple[str, list[str], str]:
  stripped = message.strip()
  if not stripped:
    raise ValueError("empty request")
  lines = stripped.splitlines()
  parts = lines[0].strip().split()
  body = "\n".join(lines[1:]).strip()
  return parts[0], parts[1:], body


def _pressure(body: str) -> tuple[str, dict]:
  if body.startswith("{"):
    raw = json.loads(body)
    facts = raw.get("new_facts") or {}
    return str(raw.get("pressure", "")), dict(facts)
  return body, {}


def config_dir() -> Path:
  return Path(__file__).resolve().parents[1] / "config"


def default_office() -> Office:
  return Office.open_memory(
      OfficeParameters.load(config_dir() / "parameters.json")
  )


def build_root_agent(office: Office):
  """ADK workflow. Imported lazily so the engines run without the SDK."""
  from google.adk import Event
  from google.adk import Workflow

  def route(node_input: str):
    return Event(output=node_input, route=office.route(node_input))

  def run_investment(node_input: str) -> str:
    return office.ask(node_input).rendered

  def run_property(node_input: str) -> str:
    return office.ask(node_input).rendered

  def run_joint(node_input: str) -> str:
    return office.ask(node_input).rendered

  return Workflow(
      name="everlin_office",
      description="Everlin Family Office analytical engine.",
      edges=[
          ("START", route),
          (
              route,
              {
                  "investment": run_investment,
                  "property": run_property,
                  "joint": run_joint,
              },
          ),
      ],
  )
