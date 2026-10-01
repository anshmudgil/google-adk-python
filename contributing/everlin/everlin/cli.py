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

"""Command line for one office request."""

from __future__ import annotations

import argparse
from datetime import date
import sys

from .office import default_office


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(prog="everlin")
  parser.add_argument("--as-of", default=None, help="YYYY-MM-DD")
  parser.add_argument("command")
  parser.add_argument("body", nargs="*", default=[])
  args = parser.parse_intermixed_args(argv)
  as_of = date.fromisoformat(args.as_of) if args.as_of else None
  body = " ".join(args.body)
  message = args.command if not body else f"{args.command}\n{body}"
  reply = default_office().ask(message, as_of=as_of)
  sys.stdout.write(reply.rendered)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
