#!/usr/bin/env python3
"""Create or update the initial administrator account."""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from jubilaires_membership.services import auth


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first-name", default="Kurt")
    parser.add_argument("--last-name", default="Gustafson")
    parser.add_argument("--email", required=True)
    parser.add_argument("--username", default="kurt")
    args = parser.parse_args()

    password = getpass.getpass("Admin password: ")
    confirm = getpass.getpass("Confirm password: ")
    if not password or password != confirm:
        print("Password is blank or does not match.", file=sys.stderr)
        return 1

    user = auth.upsert_admin(args.first_name, args.last_name, args.email, args.username, password)
    print(f"Administrator ready: {user['username']} ({user['email']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
