import pathlib

p = pathlib.Path("backend/data_pipeline/test_week14_integration.py")
text = p.read_text(encoding="utf-8")

target = 'cls.test_db_path = pathlib.Path(cls.temp_dir.name) / "test_swing_trading.db"'
replacement = 'cls.test_db_path = pathlib.Path(cls.temp_dir.name) / "test_swing_trading.db"\n        sqlite3.connect(cls.test_db_path).close()'
assert target in text
p.write_text(text.replace(target, replacement, 1), encoding="utf-8")
print("Added sqlite3 connect creation in test_week14_integration.py")

