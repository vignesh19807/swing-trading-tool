import pathlib

p = pathlib.Path('backend/data_pipeline/test_backtest_result_service.py')
text = p.read_text(encoding='utf-8')
target = 'cls.test_db_path = pathlib.Path(cls.temp_dir.name) / "test_swing_trading.db"'
replacement = 'cls.test_db_path = pathlib.Path(cls.temp_dir.name) / "test_swing_trading.db"\n        sqlite3.connect(cls.test_db_path).close()'
assert target in text
p.write_text(text.replace(target, replacement, 1), encoding='utf-8')
print('Patched successfully.')

