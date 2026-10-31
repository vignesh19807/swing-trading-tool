import pathlib

p = pathlib.Path("backend/data_pipeline/test_week14_integration.py")
text = p.read_text(encoding="utf-8")

# Ensure imports are present at top
if "import pathlib" not in text:
    text = "import pathlib\nimport tempfile\nimport backend.data_pipeline.backtest_result_service as b_svc\n" + text

p.write_text(text, encoding="utf-8")
print("Added imports to test_week14_integration.py")

