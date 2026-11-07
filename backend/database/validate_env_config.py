"""
Secure Configuration Validator for Neon PostgreSQL
==================================================
Inspects .env and DATABASE_URL without ever logging, printing,
or exposing secrets, passwords, or the complete connection string.
"""

from __future__ import annotations

import sys
import subprocess
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def validate_neon_config() -> dict[str, bool | str]:
    results: dict[str, bool | str] = {
        "env_file_exists": False,
        "database_url_present": False,
        "scheme_valid": False,
        "host_is_neon": False,
        "host_is_pooled": False,
        "database_name_valid": False,
        "sslmode_required": False,
        "channel_binding_required": False,
        "masked_endpoint": "",
        "git_ignored": False,
        "git_untracked": False,
    }

    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return results
    results["env_file_exists"] = True

    # 1. Verify Git ignore & untracked status
    try:
        proc_ign = subprocess.run(
            ["git", "check-ignore", "-q", ".env"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
        )
        results["git_ignored"] = (proc_ign.returncode == 0)

        proc_stat = subprocess.run(
            ["git", "ls-files", ".env"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        results["git_untracked"] = (proc_stat.stdout.strip() == "")
    except Exception:
        pass

    # 2. Extract DATABASE_URL
    db_url = ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            db_url = line.split("DATABASE_URL=", 1)[1].strip().strip("'\"")
            break

    if not db_url:
        return results
    results["database_url_present"] = True

    # 3. Parse and inspect properties
    try:
        parts = urlsplit(db_url)
        scheme = parts.scheme.lower()
        results["scheme_valid"] = scheme in ("postgresql", "postgres")

        host = parts.hostname or ""
        results["host_is_neon"] = "neon.tech" in host
        results["host_is_pooled"] = "-pooler" in host

        dbname = parts.path.lstrip("/")
        results["database_name_valid"] = (dbname == "neondb")

        if host:
            host_parts = host.split(".")
            if len(host_parts) >= 3:
                masked_host = f"{host_parts[0][:4]}***.{'.'.join(host_parts[1:])}"
            else:
                masked_host = "neon.tech-endpoint"
            results["masked_endpoint"] = masked_host

        query_params = parse_qs(parts.query)
        sslmode = query_params.get("sslmode", [""])[0].lower()
        results["sslmode_required"] = (sslmode == "require")

        cb = query_params.get("channel_binding", [""])[0].lower()
        # Accept require or not specified if neon default, but check if required
        results["channel_binding_required"] = (cb == "require")

    except Exception:
        pass

    return results


def print_validation_report():
    res = validate_neon_config()
    print("==================================================")
    print("NEON STAGING CREDENTIAL CONFIGURATION AUDIT")
    print("==================================================")
    print(f".env File Exists:               {'[PASS]' if res['env_file_exists'] else '[FAIL]'}")
    print(f".env Git Ignored:               {'[PASS]' if res['git_ignored'] else '[FAIL]'}")
    print(f".env Git Untracked:             {'[PASS]' if res['git_untracked'] else '[FAIL]'}")
    print(f"DATABASE_URL Present:           {'[PASS]' if res['database_url_present'] else '[PENDING]'}")
    print(f"PostgreSQL Scheme:              {'[PASS]' if res['scheme_valid'] else '[FAIL/PENDING]'}")
    print(f"Neon Endpoint Domain:           {'[PASS]' if res['host_is_neon'] else '[FAIL/PENDING]'}")
    print(f"Neon Connection Pooler Host:    {'[PASS]' if res['host_is_pooled'] else '[FAIL/PENDING]'}")
    print(f"Database Name (neondb):         {'[PASS]' if res['database_name_valid'] else '[FAIL/PENDING]'}")
    print(f"SSL Mode Required:              {'[PASS]' if res['sslmode_required'] else '[FAIL/PENDING]'}")
    print(f"Channel Binding Required:       {'[PASS]' if res['channel_binding_required'] else '[FAIL/PENDING]'}")
    if res["masked_endpoint"]:
        print(f"Masked Host:                    {res['masked_endpoint']}")
    print("==================================================")
    return res


if __name__ == "__main__":
    res = print_validation_report()
    all_passed = (
        res["env_file_exists"]
        and res["git_ignored"]
        and res["git_untracked"]
        and res["database_url_present"]
        and res["scheme_valid"]
        and res["host_is_neon"]
        and res["host_is_pooled"]
        and res["database_name_valid"]
        and res["sslmode_required"]
    )
    sys.exit(0 if all_passed else 1)
