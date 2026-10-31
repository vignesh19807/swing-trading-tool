import pathlib

p = pathlib.Path("backend/data_pipeline/test_week14_integration.py")
text = p.read_text(encoding="utf-8")

old_conn = '"database/swing_trading.db"'
# Replace occurrences of "database/swing_trading.db" in test_week14_integration with b_svc.DATABASE_PATH
text = text.replace(old_conn, "b_svc.DATABASE_PATH")
p.write_text(text, encoding="utf-8")
print("Replaced all database/swing_trading.db in test_week14_integration.py")

