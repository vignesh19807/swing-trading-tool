import pathlib

# Fix test_opportunity_score_persistence.py
p1 = pathlib.Path("backend/data_pipeline/test_opportunity_score_persistence.py")
t1 = p1.read_text(encoding="utf-8")
if "import pathlib" not in t1[:200]:
    t1 = "import pathlib\nimport tempfile\nimport shutil\nimport backend.data_pipeline.opportunity_service as opp_svc\n" + t1
p1.write_text(t1, encoding="utf-8")

# Fix test_financial_score_persistence.py
p2 = pathlib.Path("backend/data_pipeline/test_financial_score_persistence.py")
t2 = p2.read_text(encoding="utf-8")
if "import pathlib" not in t2[:200]:
    t2 = "import pathlib\nimport tempfile\nimport shutil\nimport backend.data_pipeline.financial_service as fin_svc\n" + t2
p2.write_text(t2, encoding="utf-8")

print("Fixed module-level imports.")

