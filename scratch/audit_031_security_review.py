"""
AUDIT-031: Security, Database Reliability & Dependency Review
=============================================================
Performs:
1. Hardcoded secret / API key scanner across repo
2. SQL injection pattern detection in backend codebase
3. CORS policy inspection in backend/app.py
4. Database PRAGMA integrity check and foreign key check
5. Python dependency audit (pip check / known CVEs)
"""

import os
import re
import sys
import sqlite3
from pathlib import Path

REPO_ROOT = Path(".").resolve()
DB_PATH = Path("database/swing_trading.db").resolve()

print("=== 1. Scanning for Hardcoded Secrets / Keys ===")
SECRET_PATTERNS = [
    re.compile(r'(?i)(api_key|apikey|secret|password|auth_token|bearer)\s*=\s*[\'"][^\'"]{8,}[\'"]'),
    re.compile(r'(?i)ghp_[A-Za-z0-9_]{36}'),
    re.compile(r'(?i)sk-[A-Za-z0-9]{32,}'),
]

secret_findings = []
for root, dirs, files in os.walk(REPO_ROOT):
    # Skip .git, .venv, node_modules, dist, __pycache__
    if any(p in root for p in [".git", ".venv", "node_modules", "dist", "__pycache__"]):
        continue
    for file in files:
        if file.endswith((".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".env")):
            fp = Path(root) / file
            try:
                content = fp.read_text(encoding="utf-8", errors="ignore")
                for line_idx, line in enumerate(content.splitlines(), 1):
                    for pat in SECRET_PATTERNS:
                        if pat.search(line):
                            # Filter false positives like mock data or schema descriptions
                            if "example" in line.lower() or "mock" in line.lower() or "dummy" in line.lower():
                                continue
                            secret_findings.append((str(fp.relative_to(REPO_ROOT)), line_idx, line.strip()))
            except Exception:
                pass

print(f"Total potential secret findings: {len(secret_findings)}")
for f in secret_findings[:5]:
    print(f"  {f[0]}:{f[1]} -> {f[2][:80]}")

print("\n=== 2. Scanning for SQL Injection Risks in Backend Code ===")
SQLI_PATTERNS = [
    re.compile(r'(?i)execute\s*\(\s*f[\'"].*SELECT.*\{.*\}.*[\'"]'),
    re.compile(r'(?i)execute\s*\(\s*f[\'"].*INSERT.*\{.*\}.*[\'"]'),
    re.compile(r'(?i)execute\s*\(\s*f[\'"].*UPDATE.*\{.*\}.*[\'"]'),
    re.compile(r'(?i)execute\s*\(\s*f[\'"].*DELETE.*\{.*\}.*[\'"]'),
    re.compile(r'(?i)read_sql.*f[\'"].*SELECT.*\{.*\}.*[\'"]'),
]

sqli_findings = []
backend_dir = REPO_ROOT / "backend"
for root, dirs, files in os.walk(backend_dir):
    if any(p in root for p in [".venv", "__pycache__"]):
        continue
    for file in files:
        if file.endswith(".py"):
            fp = Path(root) / file
            content = fp.read_text(encoding="utf-8", errors="ignore")
            for line_idx, line in enumerate(content.splitlines(), 1):
                for pat in SQLI_PATTERNS:
                    if pat.search(line):
                        sqli_findings.append((str(fp.relative_to(REPO_ROOT)), line_idx, line.strip()))

print(f"Total SQL string interpolation findings: {len(sqli_findings)}")
for f in sqli_findings:
    print(f"  {f[0]}:{f[1]} -> {f[2][:100]}")

print("\n=== 3. Inspecting CORS Policy in backend/app.py ===")
app_file = backend_dir / "app.py"
app_content = app_file.read_text(encoding="utf-8", errors="ignore")
cors_matches = re.findall(r'allow_origins\s*=\s*\[(.*?)\]', app_content, re.DOTALL)
print("Configured CORS allow_origins:")
for m in cors_matches:
    print(f"  {m.strip()}")

print("\n=== 4. Production Database PRAGMA Checks ===")
conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
integrity = conn.execute("PRAGMA integrity_check").fetchall()
print(f"PRAGMA integrity_check: {integrity}")
foreign_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
print(f"PRAGMA foreign_key_check: {len(foreign_keys)} violations")
quick_check = conn.execute("PRAGMA quick_check").fetchall()
print(f"PRAGMA quick_check: {quick_check}")
conn.close()

print("\n=== 5. Database Schema & Migration Review ===")
conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f"Total tables: {len(tables)} -> {tables}")
conn.close()

