# Everlin Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a testable Everlin Phase 1 office: two analyst engines, conforming memos and briefings, escalation, and an audit trail, orchestrated by an ADK workflow.

**Architecture:** Pure Python engines decide leans and render templates. SQLite holds the audit trail. An ADK `Workflow` routes chat commands to those engines. Appendix A parameters stay null until edited in JSON.

**Tech Stack:** Python 3.10+, stdlib `sqlite3` and `dataclasses`, Google ADK `Workflow` when installed, pytest.

The tasks share one package and one set of types, so they are tightly coupled. Execute them in this session rather than splitting them across implementers.

## Global Constraints

- Package root: `contributing/everlin/`. Do not add modules under `src/google/adk/`.
- Brief version string: `3`.
- Margin of safety minimum: 25. Development margin minimum: 20. Fee ceiling: 2.5. PE net IRR floor: 15. Credit net yield floor: 8. Going-concern floor: 7. Vacancy fail for Triguboff: above 2.
- Stress: construction cost +10%, sale price −10%, timeline +6 months at 0.5% of base TDC per month.
- Appendix A fields ship as JSON null. Draft banner lists them. `require_live()` raises while any are null.
- Clock offset: UTC+10, named AEST.
- Screening leans: `PROCEED`, `CONDITIONAL PROCEED`, `DEFER`, `DECLINE`, `WATCH`.
- Escalation: `GREEN`, `AMBER`, `RED`.
- Assertion sentence and signal layout match the design spec.
- Apache-2.0 header on every Python file. Two-space indent. Line length 80.
- Agents do not commit capital. Jordan is the principal.

______________________________________________________________________

### Task 1: Parameters, team, numbering

**Files:**

- Create: `contributing/everlin/config/parameters.json`
- Create: `contributing/everlin/config/team.json`
- Create: `contributing/everlin/everlin/parameters.py`
- Create: `contributing/everlin/everlin/team.py`
- Create: `contributing/everlin/everlin/numbering.py`
- Test: `tests/unittests/everlin/test_phase1.py`

**Interfaces:**

- Produces: `OfficeParameters.load(path) -> OfficeParameters`

- Produces: `OfficeParameters.unconfirmed() -> tuple[str, ...]`

- Produces: `OfficeParameters.live_ready: bool`

- Produces: `ParametersUnconfirmed`

- Produces: `load_team(path) -> tuple[TeamMember, ...]`

- Produces: `owner_for(role, team) -> tuple[str, str]` # name, note

- Produces: `add_business_days(day, n) -> date`

- Produces: `ReferenceBook.next_numbered(prefix, year) -> str`

- Produces: `ReferenceBook.daily(day) -> str`

- Produces: `ReferenceBook.weekly(day) -> str`

- Prefixes: `EVL-INV-SCR`, `EVL-PROP-SCR`

- [ ] Write failing tests for null parameters, a fully confirmed object, document numbers, and the unfilled Head of Property owner.

- [ ] Run `pytest tests/unittests/everlin/test_phase1.py -q` and confirm import or assertion failures.

- [ ] Implement the three modules and the JSON files.

- [ ] Re-run the same tests and confirm the new cases pass.

### Task 2: Behaviour and escalation

**Files:**

- Create: `contributing/everlin/everlin/behaviour.py`
- Create: `contributing/everlin/everlin/escalation.py`

**Interfaces:**

- Produces: `format_range(low, high) -> str`

- Produces: `collapse_range(low, high) -> str` # always raises ValueError

- Produces: `flag_assertion(claim, origin, verify_against) -> str`

- Produces: `correct_number(label, stated, actual, unit) -> str | None`

- Produces: `hold_position(lean, message, new_fact) -> HoldResult`

- Produces: `second_opinion(decision, thesis_intact) -> str | None`

- Produces: `filler_violations(text) -> list[str]`

- Produces: `classify_escalation(lean, *, hours_to_deadline, material_risk, thesis_broke_after_decision) -> str`

- [ ] Tests: 18–24 stays `18–24`; collapse raises; pressure holds; a new fact does not hold; WATCH is GREEN; PROCEED inside 24 hours is RED; assertion and correction strings match the spec.

- [ ] Implement and re-run.

### Task 3: Audit trail and signals

**Files:**

- Create: `contributing/everlin/everlin/audit.py`
- Create: `contributing/everlin/everlin/signals.py`

**Interfaces:**

- Produces: `AuditLog(path)` with `next_reference`, `log_recommendation`, `record_decision`, `record_outcome`, `get`, `export_json`, `restore`, `add_signal`, `notify`

- Produces: `render_signal(level, sender, receiver, signal, implication, action) -> str`

- `notify` sets `notified_at` equal to `triggered_at`.

- [ ] Test export/restore and a notification delta of zero seconds.

- [ ] Implement and re-run.

### Task 4: Investment and property engines

**Files:**

- Create: `contributing/everlin/everlin/investment.py`
- Create: `contributing/everlin/everlin/property.py`

**Interfaces:**

- Produces: `screen_investment(payload, params) -> InvestmentScreen`
- Produces: `render_investment_screen(screen, reference, as_of, draft_note) -> str`
- Produces: `render_investment_thesis(...) -> str`
- Produces: `screen_property(payload, params) -> PropertyScreen`
- Produces: `render_property_screen(...) -> str`
- Produces: `render_site_thesis(...) -> str`

Lean rules are the design spec. Do not invent a second margin threshold.

- [ ] Tests for Buffett proceed, Buffett decline at a 20% margin, missing intrinsic value, fee drag, distribution edge, unverified-claim conditional, filter-fail decline, combined-stress bid cut, and a clearing development proceed.
- [ ] Implement and re-run. Each rendered memo must list every required heading.

### Task 5: Sources, reports, office, prompts, workflow

**Files:**

- Create: `contributing/everlin/everlin/sources.py`
- Create: `contributing/everlin/everlin/reports.py`
- Create: `contributing/everlin/everlin/conformance.py`
- Create: `contributing/everlin/everlin/prompts.py`
- Create: `contributing/everlin/everlin/office.py`
- Create: `contributing/everlin/everlin/cli.py`
- Create: `contributing/everlin/everlin/__init__.py`
- Create: `contributing/everlin/agent.py`
- Create: `contributing/everlin/README.md`
- Create: `tests/unittests/everlin/conftest.py`

**Interfaces:**

- Produces: `Office.ask(message, as_of=None) -> OfficeReply`

- Produces: `Office.require_live() -> None`

- Produces: `Office.route(message) -> str` # investment, property, or joint

- Produces: `build_root_agent(office) -> Workflow`

- Produces: `specification_sync(params) -> None`

- Produces: `default_records(now) -> tuple[SourceRecord, ...]`

- Produces: `daily_deadline(day) -> datetime`

- [ ] Tests for five daily references, two weekly references, signal text, stale-source wording, specification sync, challenge hold and re-screen, and the filler ban.

- [ ] Implement.

- [ ] Run `pytest tests/unittests/everlin -q`.

- [ ] If `google.adk` imports, run the workflow test. If it does not, record that skip.

### Task 6: Format and checklist

- [ ] Run pyink and isort on `contributing/everlin` and `tests/unittests/everlin`.
- [ ] Re-run pytest. Every Appendix B Phase 1 row that this slice owns is asserted in `test_phase1.py`. Live five-day market operation and mobile push stay out of scope, as the design says.
