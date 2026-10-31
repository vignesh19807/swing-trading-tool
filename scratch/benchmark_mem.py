import sys, os
sys.path.insert(0, os.path.abspath("."))
import time
import sqlite3
import functools
import warnings
from pathlib import Path
from unittest.mock import patch

warnings.filterwarnings("ignore")

import backend.data_pipeline.financial_service as fin
import backend.data_pipeline.data_service as ds
import backend.data_pipeline.classification_service as cs
import backend.engines.financial_engine as fe
from backend.logic.signal_integration import run_signal_pipeline

DB = Path("docs/audit_artifacts/temp_multiyear_audit_025.db").resolve()
disk = sqlite3.connect(DB)
mem = sqlite3.connect("file:fast_mem?mode=memory&cache=shared", uri=True)
disk.backup(mem)

orig_connect = sqlite3.connect
def fast_connect(database, *args, **kwargs):
    return orig_connect("file:fast_mem?mode=memory&cache=shared", uri=True)

patch("sqlite3.connect", fast_connect).start()
patch.object(fe, "analyze_financial_health", functools.lru_cache(maxsize=1024)(fe.analyze_financial_health)).start()

t0 = time.time()
for _ in range(50):
    run_signal_pipeline("SUNPHARMA", "2026-01-15")
t1 = time.time()
print(f"In-memory time for 50 evals: {t1-t0:.2f}s, per eval: {(t1-t0)/50*1000:.1f}ms")
