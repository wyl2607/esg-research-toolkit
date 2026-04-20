#!/usr/bin/env python3
"""Legacy compatibility shim for the old runtime DB migration helper."""

from __future__ import annotations

import sys


def main() -> int:
    print("⚠️ scripts/migrate_db.py is now a compatibility shim and does not write schema changes.")
    print("Use Alembic commands instead:")
    print("  ./scripts/db_init.sh")
    print("  alembic upgrade head")
    print("Existing production database cutover: docs/runbooks/alembic_cutover.md")

    if len(sys.argv) > 1:
        print(f"(ignored legacy arguments: {' '.join(sys.argv[1:])})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
