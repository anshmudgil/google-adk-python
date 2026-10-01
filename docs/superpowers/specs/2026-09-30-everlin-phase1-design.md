# Everlin Phase 1 Design

Date: 2026-09-30
Status: Build specification for the first shippable slice
Source: Everlin Family Office AI Agent Brief, version 3 (June 2026)

## Why this slice

The brief specifies two agents, three delivery phases, and a Phase 0 gate.
Phase 0 is not closed: every Appendix A parameter is still `[X]`. Live market
subscriptions (Bloomberg, Capital IQ, CoreLogic, PriceFinder) are "to confirm".
The brief also says a phase that does not produce a working demo does not start
the next phase.

This design is Phase 1 only. Phase 2 (full Buffett/Wood/Triguboff/Mosaic
models, IC papers, acquisition memos, dashboard) and Phase 3 (bias detection,
black-swan library, feedback-loop prompt changes, quarterly and annual
reports) are out of scope.

## Approaches

1. **Prompt-only Claude agents.** Fast to sketch. Template conformance and the
   eleven behaviour standards then depend on the model obeying the prompt.
   That fails the brief's rule that conformance is tested continuously, not
   hoped for at a demo.
1. **Deterministic engines, ADK for orchestration.** Leans, margins, document
   numbers, escalation, and audit rows are pure functions and a local store.
   An ADK workflow routes each request to the Investment Analyst, the Property
   Analyst, or a joint report. A versioned prompt file is the governed
   instruction for a later model. The model cannot drop a section because the
   section is rendered from the engine result.
1. **Full hosted product.** Chat UI, mobile push, Australian residency,
   cron, and paid data vendors. Phase 0 subscriptions are not available in
   this repository, so this cannot be demonstrated here.

**Choice: approach 2.** It is the only option that can pass the Phase 1
checklist in Appendix B with evidence. Section 37.3 of the brief requires the
orchestration layer to stay model-agnostic. ADK is that layer. Google ADK is
the toolkit in this repository; the office is a separate package so it does
not enter `google.adk`.

## What the office does

Two analysts share one audit trail, one parameter file, and one signal log.

- **Investment Analyst** screens an equity, fund, or private-credit
  opportunity and writes an investment screening memo and a one-page thesis.
- **Property Analyst** screens a development site or an income asset and
  writes a property screening memo and a one-page site thesis.
- **Joint reporting** writes the daily briefing (Investment Analyst leads)
  and the weekly IC briefing.

The principal drives them with a chat command. Natural-language pressure
without a new fact does not move a lean. A structured new fact re-runs the
screen.

Final authority stays with Jordan. Nothing in this package commits capital.

## Decisions locked here

These replace the unconfirmed `[X]` values only where the brief already
states a number. Appendix A values stay null until the principal writes them
into `contributing/everlin/config/parameters.json`.

| Rule                           | Value                                                                                            | Source                                                             |
| ------------------------------ | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| Buffett margin of safety       | 25% below intrinsic value                                                                        | Section 18 minimum of the 25–30% band                              |
| Development margin             | 20% of TDC                                                                                       | Section 3                                                          |
| Combined stress                | cost +10%, price −10%, timeline +6 months, still 20%                                             | Section 3 and 28.2                                                 |
| Timeline stress cost           | 0.5% of base TDC per month, labelled an agent calculation                                        | Not in the brief. Stated on every feasibility so it is not silent. |
| Fee-drag ceiling               | 2.5% p.a.                                                                                        | Section 3                                                          |
| Private equity net IRR floor   | 15%                                                                                              | Section 3 benchmark floor                                          |
| Private credit net yield floor | 8%, and the instrument must be senior secured                                                    | Section 3                                                          |
| Going-concern yield floor      | 7%                                                                                               | Section 3 band floor. A yield above 9% is acceptable.              |
| Triguboff vacancy              | Above 2% fails the supply test                                                                   | Section 24                                                         |
| Screening lean vocabulary      | PROCEED, CONDITIONAL PROCEED, DEFER, DECLINE, WATCH                                              | Section 8                                                          |
| Escalation                     | GREEN information, AMBER review within 48 hours, RED immediate                                   | Section 5                                                          |
| Clock                          | Fixed UTC+10, labelled AEST. Gold Coast does not use daylight saving.                            | Section 3 domicile and the glossary                                |
| Draft vs live                  | Any null Appendix A field keeps the office in draft. `require_live()` refuses to clear the gate. | Appendix A                                                         |

### Investment lean

Checks run in the Section 17 order: circle of competence, thesis under
stress, price, portfolio fit, exit. The first hard failure sets DECLINE.
Later checks are still printed.

- Missing data that the check needs sets DEFER, unless a hard failure already
  set DECLINE.
- A material unverified pitch claim prevents PROCEED. The lean is
  CONDITIONAL PROCEED when nothing else failed.
- No edge, or only edge F without stated economic value, is DECLINE. The
  Everlin Question then says this is distribution, not edge.
- An empty bear case is a data gap (DEFER). The memo says the bear case was
  not supplied.
- Buffett equity price: margin = (intrinsic − price) / intrinsic. Below 25%
  is DECLINE. Walk-away price is intrinsic × 0.75.
- Fund price: net IRR below 15%, or all-in fee above 2.5%, is DECLINE.
- Wood price: adoption already priced in is DECLINE. An empty TAM is DEFER.
- Credit: not senior secured, or net yield below 8%, is DECLINE. A missing
  interest-coverage figure is DEFER. This screen does not run a full ICR
  stress model.

### Property lean

- Any non-negotiable filter with status Fail is DECLINE, including when the
  margin is attractive.
- UNKNOWN council timing, or a missing required feasibility input, blocks
  PROCEED.
- Development margin uses (GRV − TDC) / TDC.
- If the combined-stress margin is under 20% and a positive land bid still
  clears 20% under that stress, the lean is CONDITIONAL PROCEED and the
  walk-away is that maximum bid. If no positive bid clears, the lean is
  DECLINE.
- Maximum stressed TDC = stressed GRV / 1.20. Maximum land = that TDC minus
  non-land costs, the construction uplift, and the timeline holding cost.
- Triguboff vacancy above 2% is DECLINE. Mosaic does not use that test.
- Mosaic with brand alignment Fail is DECLINE. Triguboff brand alignment is
  N/A.
- Income assets, when no development costs are supplied: cap rate = NOI /
  asking price. Below 7% is DECLINE.
- Land cost as a share of GRV is reported. It becomes a breach only when the
  Appendix A ceiling is set. A null ceiling is named, not treated as zero.

### Escalation

- RED when a material risk is flagged, a previously accepted thesis has
  broken, or a PROCEED / CONDITIONAL PROCEED deadline is inside 24 hours.
- AMBER for PROCEED, CONDITIONAL PROCEED, and DEFER in every other case.
- GREEN for DECLINE and WATCH.
- AMBER and RED notifications are written at the same timestamp as the
  trigger. The in-process channel therefore meets the 60-second rule. A
  mobile push vendor is out of scope.

### Documents

| Output                    | Reference               |
| ------------------------- | ----------------------- |
| Investment screening memo | `EVL-INV-SCR-YYYY-NN`   |
| Property screening memo   | `EVL-PROP-SCR-YYYY-NN`  |
| Daily briefing            | `EVL-DAILY-YYYY-MM-DD`  |
| Weekly IC briefing        | `EVL-WEEKLY-YYYY-MM-DD` |

Screening memos use the nine and ten section titles in Sections 22.1 and
28.1. Thesis documents use the fields in Sections 22.3 and 28.3, plus the framework
label Sections 17 and 23 require. Daily and weekly use the Section 30
outlines. Screening memos include walk-away triggers because Appendix B
requires them at Phase 1, even though Section 9 names IC papers first.

Rendered prose must not contain filler ("great question", "I'd be happy",
"hope this helps", "as an AI", "certainly!"). Ranges are rendered with an
en dash. A helper that would replace a range with its midpoint raises.

Unverified claims use this sentence, exactly:

`{claim} is an {IM|agent|pitch} assertion, not an independent valuation. Verify against {source} before using as an underwriting input.`

Factual corrections use three parts: what was stated, why it is incorrect,
and the accurate figure.

### Cross-agent signals

```
CROSS-AGENT SIGNAL | LEVEL
From: Investment Analyst. To: Property Analyst. Signal: ...
Implication: ... Action: ...
```

The opposite direction uses Property Analyst then Investment Analyst.
A screening payload may attach `macro_signal` or `corridor_signal`. The
default FRED fixture also emits a rate-rise signal when the daily briefing
is built.

### Data sources

Phase 1 ships six simulated sources with timestamps, three per agent:

- Investment: FRED, SEC EDGAR, AFR
- Property: ABS, State Planning Portal, Domain Listings

Each record is fresh or stale against the Section 35 window for its kind
(news within one hour, listings and planning within one day, macro and
filings on the same calendar day, demographics treated as a release). A stale
or unavailable source is named in the briefing and that section's confidence
is low. No network call is made.

### Memory

SQLite stores recommendations (lean, reasoning, confidence, sources,
payload), principal decisions, outcomes, pipeline rows, signals,
notifications, and document sequences. `export_json` and `restore` round-trip
that store. This is the Phase 1 backup demonstration, not a second-region
replica.

### Team

Action owners come from `config/team.json`. Jordan Hickey is on the directory
as Head of Property with `filled: false` because the brief says the role is
being recruited. An unfilled role is assigned to Jordan with the sentence
"No dedicated resource — principal action required until {role} is filled."
Deadlines are five business days after the screen date.

### Behaviour suite

Ten adversarial cases are executable functions, not a prose promise:

1. Pressure without a new fact holds the lean.
1. A new intrinsic value re-opens the screen.
1. Rendered memos contain none of the banned filler.
1. A principal's stated margin that collapses a range is corrected.
1. The bear case is present.
1. An IM claim uses the assertion sentence.
1. 18–24 stays 18–24.
1. A missing intrinsic value is named and no price is invented.
1. WATCH is GREEN.
1. An accepted decision whose thesis later breaks emits an unsolicited
   second opinion.

The prompt file cites brief version 3 and all eleven Section 6 standard
titles. `specification_sync` fails if the prompt version and the parameter
file version differ.

### ADK

`build_root_agent(office)` returns a `Workflow` named `everlin_office`.
The first node routes to `run_investment`, `run_property`, or `run_joint`.
Those nodes call `Office.ask`. `contributing/everlin/agent.py` exposes
`root_agent` for the ADK CLI once `google.adk` is installed.

### Chat commands

The first line is the command. A JSON object may follow.

- `screen-investment`
- `screen-property`
- `thesis-investment`
- `thesis-site`
- `daily`
- `weekly`
- `challenge REFERENCE`
- `decide REFERENCE accepted|rejected|modified|deferred`
- `outcome REFERENCE text`
- `second-opinion REFERENCE` with `{"thesis_intact": false}`
- `audit`
- `signals`

## Error handling

Invalid payloads raise `ValueError` and the reply leads with "The request is
invalid." A missing recommendation reference is stated in one sentence.
Draft mode never pretends Appendix A is confirmed. Live mode raises
`ParametersUnconfirmed` and lists the null fields.

## Testing

`tests/unittests/everlin/` imports the package by adding
`contributing/everlin` to `sys.path`. Tests cover the lean rules, the
rendered templates, five daily references, two weekly references, signal
text, audit restore, the 60-second notification stamp, the behaviour suite,
and the ADK route when `google.adk` imports.

## Non-goals

No Bloomberg client, no mobile push, no web dashboard, no IC paper, no
acquisition memo, no DCF workbook, no automated prompt rewrite, no cron
daemon. `daily_deadline` records 07:00 AEST so a caller can judge lateness.
The library does not wake itself up.
