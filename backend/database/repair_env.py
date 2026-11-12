"""
Safe .env Repair Utility
========================
Removes any malformed or duplicate DATABASE_URL assignments,
preserves all comments and unrelated environment variables,
and writes exactly one clean DATABASE_URL= placeholder.
Never logs or prints secrets.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def repair_env_file():
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        print("Creating fresh .env file...")
        content_lines = [
            "# ==============================================================================",
            "# Swing Trading Intelligence Platform — Local Staging Environment",
            "# ==============================================================================",
            "# CRITICAL SECURITY RULE:",
            "# Never commit this file or paste connection strings with plaintext passwords",
            "# into chat, logs, or commit messages.",
            "# ==============================================================================",
            "",
            "# Neon PostgreSQL Staging Connection String",
            "# Format: postgresql://[user]:[password]@[endpoint]-pooler.[region].aws.neon.tech/neondb?sslmode=require&channel_binding=require",
            "DATABASE_URL=",
        ]
        env_path.write_text("\n".join(content_lines) + "\n", encoding="utf-8")
        print("Clean .env created with exactly one DATABASE_URL= entry.")
        return

    raw_lines = env_path.read_text(encoding="utf-8").splitlines()
    preserved_lines = []
    database_url_found = 0

    for line in raw_lines:
        stripped = line.strip()
        if stripped.startswith("DATABASE_URL="):
            database_url_found += 1
            # Remove any malformed or previous entry
            continue
        preserved_lines.append(line)

    # Ensure clean formatting before appending DATABASE_URL
    # Trim trailing blank lines
    while preserved_lines and not preserved_lines[-1].strip():
        preserved_lines.pop()

    # Append single clean DATABASE_URL entry
    preserved_lines.append("")
    preserved_lines.append("# Neon PostgreSQL Staging Connection String")
    preserved_lines.append("# Format: postgresql://[user]:[password]@[endpoint]-pooler.[region].aws.neon.tech/neondb?sslmode=require&channel_binding=require")
    preserved_lines.append("DATABASE_URL=")

    env_path.write_text("\n".join(preserved_lines) + "\n", encoding="utf-8")
    print(f"Repaired .env: removed {database_url_found} prior DATABASE_URL line(s).")
    print("Exactly one DATABASE_URL= entry is now configured.")


if __name__ == "__main__":
    repair_env_file()
