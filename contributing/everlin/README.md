# Everlin Phase 1

Analytical office for Everlin Family Office, built on the Agent Development
Kit. Phase 1 screens investments and property, writes the daily and weekly
briefings, and logs every recommendation.

The engines decide the lean. The ADK workflow then runs an analyst agent, and
the published memo stays the engine text if the model paraphrases it or the
model call fails. `agent.py` exposes `root_agent`.

## Scope

In this slice:

- Investment screening memos, property screening memos, and one-page thesis documents
- Daily briefing and weekly IC briefing
- Green / amber / red escalation with an in-process notification stamp
- SQLite audit trail, including export and restore
- Appendix A parameters read from `config/parameters.json`

Not in this slice: live Bloomberg or CoreLogic calls, mobile push, the
portfolio dashboard, IC papers, acquisition memos, and the Phase 3 learning
loop. Those wait on Phase 0 subscriptions and a signed phase gate.

## Parameters

`config/parameters.json` ships with every Appendix A value set to `null`.
The office stays in draft and prints those names on every output.
`Office.require_live()` raises until the principal replaces each `null`.
Do not invent the missing percentages in code.

## Run

From the repository root:

```bash
PYTHONPATH=contributing/everlin python -m everlin.cli daily --as-of 2026-09-30
PYTHONPATH=contributing/everlin python -m pytest tests/unittests/everlin -q
```

ADK CLI, from `contributing/` after copying `everlin/.env.example` to
`everlin/.env` and setting `GOOGLE_API_KEY`:

```bash
adk run everlin
adk web .
```

Send a command as the user message, for example `daily`. The analyst model is
`gemini-2.5-flash`.

Chat commands, first line then an optional JSON body:

- `screen-investment`
- `screen-property`
- `thesis-investment`
- `thesis-site`
- `daily`
- `weekly`
- `challenge REFERENCE`
- `decide REFERENCE accepted|rejected|modified|deferred`
- `second-opinion REFERENCE`

Jordan remains the decision-maker. The office does not commit capital.
