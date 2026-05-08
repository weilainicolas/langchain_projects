"""<one-line description of what this agent does>.

Run from repo root: python -m agents.<agent_name>.main
Requires: .env with <list keys>
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()

# EXAMPLE_KEY = os.environ["EXAMPLE_KEY"]


def main() -> None:
    print("hello from <agent_name>", file=sys.stderr)


if __name__ == "__main__":
    main()
