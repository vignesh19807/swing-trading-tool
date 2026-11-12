"""
Interactive Secure Neon Staging Credential Setup
================================================
Prompts for the Neon connection string using getpass (hidden input, no echo),
validates its format without revealing secrets, and writes it directly to .env.
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    print("==================================================")
    print("Swing Trading Platform — Neon Staging Secret Setup")
    print("==================================================")
    print("Please paste your newly regenerated Neon pooled connection string.")
    print("Input will NOT be echoed on screen for security.")
    print()

    try:
        raw_url = getpass.getpass("Enter Neon DATABASE_URL: ").strip()
    except Exception as e:
        print(f"Error reading input: {e}")
        sys.exit(1)

    if not raw_url:
        print("Error: No connection string was provided.")
        sys.exit(1)

    # Basic format check without leaking
    try:
        parts = urlsplit(raw_url)
        if parts.scheme.lower() not in ("postgresql", "postgres"):
            print("Error: URL scheme must be postgresql:// or postgres://")
            sys.exit(1)
        if "neon.tech" not in (parts.hostname or ""):
            print("Error: Hostname does not appear to be a Neon endpoint (*.neon.tech).")
            sys.exit(1)
    except Exception as e:
        print(f"Error parsing connection string: {e}")
        sys.exit(1)

    # Update root .env
    env_path = PROJECT_ROOT / ".env"
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    updated = False
    new_lines = []
    for line in lines:
        if line.strip().startswith("DATABASE_URL="):
            new_lines.append(f"DATABASE_URL={raw_url}")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"DATABASE_URL={raw_url}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print()
    print("SUCCESS: DATABASE_URL successfully configured in local .env.")
    print("==================================================")


if __name__ == "__main__":
    main()
