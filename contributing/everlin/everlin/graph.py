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

"""ADK graph for the two analysts and the joint briefings.

The engines write the memo before any model call. The analyst may call
`read_screening_memo`, but the text that leaves the graph is the memo the
engine stored. A model cannot change a lean by paraphrasing one.
"""

from __future__ import annotations

from typing import Any

from google.adk.tools import ToolContext

from .office import Office
from .prompts import INVESTMENT_PROMPT
from .prompts import PROMPT_VERSION
from .prompts import PROPERTY_PROMPT

DEFAULT_MODEL = "gemini-2.5-flash"

_TOOL_RULE = (
    "Call read_screening_memo once with reference_hint set to current. "
    "Return the tool result unchanged. Do not add a lean, a number, or a "
    "sentence the tool did not return."
)

_JOINT_PROMPT = (
    f"brief_version: {PROMPT_VERSION}\n"
    "You prepare the joint Everlin briefings. "
    "You do not commit capital. Jordan decides.\n"
    "Hold the Position Under Pressure\n"
    "Straight Answers Only\n"
    "Unsolicited Second Opinions"
)


def build_office_workflow(office: Office, model: str | Any = DEFAULT_MODEL):
  """Workflow named everlin_office. `model` may be a model id or a BaseLlm."""
  from google.adk import Event
  from google.adk import Workflow
  from google.adk.agents import LlmAgent
  from google.adk.models.llm_response import LlmResponse
  from google.genai import types

  def route(node_input: str):
    return Event(
        output=node_input,
        route=office.route(node_input),
        state={"office_request": node_input},
    )

  def _screen(node_input: str):
    reply = office.ask(node_input)
    return Event(
        output=reply.rendered,
        state={"canonical_memo": reply.rendered},
    )

  # One target per route. A shared successor would be an illegal edge pair.
  def compute_investment(node_input: str):
    return _screen(node_input)

  def compute_property(node_input: str):
    return _screen(node_input)

  def compute_joint(node_input: str):
    return _screen(node_input)

  def read_screening_memo(
      reference_hint: str, tool_context: ToolContext
  ) -> str:
    """Return the canonical memo for this turn.

    Args:
      reference_hint: Pass current. Any other hint is ignored.

    Returns:
      The engine memo. Repeat it unchanged.
    """
    memo = tool_context.state.get("canonical_memo", "")
    if not memo:
      return f"No memo is stored for {reference_hint}."
    return str(memo)

  def lock_memo(callback_context, llm_response):
    parts = []
    content = llm_response.content
    if content is not None and content.parts:
      parts = list(content.parts)
    if any(part.function_call for part in parts):
      return None
    memo = str(callback_context.state.get("canonical_memo", ""))
    if not memo:
      return None
    return LlmResponse(
        content=types.Content(role="model", parts=[types.Part(text=memo)])
    )

  def memo_on_model_error(callback_context, llm_request, error):
    del llm_request, error
    memo = str(callback_context.state.get("canonical_memo", ""))
    if not memo:
      return None
    return LlmResponse(
        content=types.Content(role="model", parts=[types.Part(text=memo)])
    )

  def analyst(name: str, description: str, instruction: str) -> LlmAgent:
    return LlmAgent(
        name=name,
        model=model,
        description=description,
        instruction=f"{instruction}\n{_TOOL_RULE}",
        tools=[read_screening_memo],
        include_contents="none",
        generate_content_config=types.GenerateContentConfig(temperature=0),
        after_model_callback=lock_memo,
        on_model_error_callback=memo_on_model_error,
    )

  investment_analyst = analyst(
      "investment_analyst",
      "Screens investments and writes the daily briefing.",
      INVESTMENT_PROMPT,
  )
  property_analyst = analyst(
      "property_analyst",
      "Screens property and writes site thesis documents.",
      PROPERTY_PROMPT,
  )
  joint_analyst = analyst(
      "joint_briefing",
      "Writes the weekly IC briefing and other joint replies.",
      _JOINT_PROMPT,
  )

  def seal(node_input: str, canonical_memo: str):
    published = canonical_memo or node_input
    return Event(output=published, message=published)

  return Workflow(
      name="everlin_office",
      description="Everlin Family Office analytical engine.",
      input_schema=str,
      edges=[
          ("START", route),
          (
              route,
              {
                  "investment": compute_investment,
                  "property": compute_property,
                  "joint": compute_joint,
              },
          ),
          (compute_investment, investment_analyst, seal),
          (compute_property, property_analyst, seal),
          (compute_joint, joint_analyst, seal),
      ],
  )
