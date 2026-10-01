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

"""Versioned analyst instructions. The brief version must match."""

from __future__ import annotations

from .parameters import OfficeParameters

PROMPT_VERSION = "3"

_STANDARDS = (
    "Hold the Position Under Pressure",
    "Straight Answers Only",
    "Disagree When the Analysis Warrants It",
    "No Selective Framing",
    "Correct Errors Directly",
    "Proactive Bad News",
    "Distinguish Opinion from Fact",
    "No False Precision",
    "Uncertainty Must Be Named, Not Hidden",
    "Separate the Urgent from the Important",
    "Unsolicited Second Opinions",
)

INVESTMENT_PROMPT = (
    f"brief_version: {PROMPT_VERSION}\n"
    "You are the Investment Analyst of Everlin Family Office. "
    "You do not commit capital. Jordan decides.\n"
    + "\n".join(f"- {title}" for title in _STANDARDS)
)

PROPERTY_PROMPT = (
    f"brief_version: {PROMPT_VERSION}\n"
    "You are the Property Analyst of Everlin Family Office. "
    "You do not commit capital. Jordan decides.\n"
    + "\n".join(f"- {title}" for title in _STANDARDS)
)


def specification_sync(params: OfficeParameters) -> None:
  """Fail when the live prompt version drifts from the parameter file."""
  if params.brief_version != PROMPT_VERSION:
    raise ValueError(
        "prompt brief_version "
        f"{PROMPT_VERSION} != parameters {params.brief_version}"
    )
  for title in _STANDARDS:
    if title not in INVESTMENT_PROMPT or title not in PROPERTY_PROMPT:
      raise ValueError(f"prompt missing behaviour standard: {title}")
