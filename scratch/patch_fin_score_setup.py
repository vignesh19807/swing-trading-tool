import pathlib

p2 = pathlib.Path("backend/data_pipeline/test_financial_score_persistence.py")
text2 = p2.read_text(encoding="utf-8")

old_def = """class TestFinancialScorePersistence(unittest.TestCase):
    \"\"\"Unit and Integration tests for Financial Health Score Database Persistence.\"\"\"

    def setUp(self):"""

new_def = """class TestFinancialScorePersistence(unittest.TestCase):
    \"\"\"Unit and Integration tests for Financial Health Score Database Persistence.\"\"\"

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = pathlib.Path(cls.temp_dir.name) / "test_swing_trading.db"
        shutil.copyfile("database/swing_trading.db", cls.test_db_path)
        cls.orig_db_path = fin_svc.DATABASE_PATH
        fin_svc.DATABASE_PATH = cls.test_db_path

    @classmethod
    def tearDownClass(cls):
        fin_svc.DATABASE_PATH = cls.orig_db_path
        cls.temp_dir.cleanup()

    def setUp(self):"""

assert old_def in text2, "Could not find old_def in test_financial_score_persistence.py"
text2 = text2.replace(old_def, new_def, 1)
p2.write_text(text2, encoding="utf-8")
print("Successfully patched test_financial_score_persistence.py with setUpClass and tearDownClass.")

