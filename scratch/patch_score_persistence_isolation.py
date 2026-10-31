import pathlib

# Patch test_opportunity_score_persistence.py
p1 = pathlib.Path("backend/data_pipeline/test_opportunity_score_persistence.py")
text1 = p1.read_text(encoding="utf-8")

old_class_1 = """class TestOpportunityScorePersistence(unittest.TestCase):
    \"\"\"Unit and Integration tests for Opportunity Score Database Persistence.\"\"\"

    def setUp(self):
        \"\"\"Setup test environment and clean up test rows.\"\"\"
        self.test_date = "2026-08-14"
        self._cleanup_test_records()"""

new_class_1 = """import tempfile
import shutil
import backend.data_pipeline.opportunity_service as opp_svc

class TestOpportunityScorePersistence(unittest.TestCase):
    \"\"\"Unit and Integration tests for Opportunity Score Database Persistence.\"\"\"

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = pathlib.Path(cls.temp_dir.name) / "test_swing_trading.db"
        shutil.copyfile("database/swing_trading.db", cls.test_db_path)
        cls.orig_db_path = opp_svc.DATABASE_PATH
        opp_svc.DATABASE_PATH = cls.test_db_path

    @classmethod
    def tearDownClass(cls):
        opp_svc.DATABASE_PATH = cls.orig_db_path
        cls.temp_dir.cleanup()

    def setUp(self):
        \"\"\"Setup test environment and clean up test rows.\"\"\"
        self.test_date = "2026-08-14"
        self._cleanup_test_records()"""

text1 = text1.replace("DATABASE_PATH,", "DATABASE_PATH as _DEFAULT_DB_PATH,")
text1 = text1.replace("sqlite3.connect(DATABASE_PATH)", "sqlite3.connect(opp_svc.DATABASE_PATH)")
text1 = text1.replace(old_class_1, new_class_1, 1)
p1.write_text(text1, encoding="utf-8")
print("Patched test_opportunity_score_persistence.py")

# Patch test_financial_score_persistence.py
p2 = pathlib.Path("backend/data_pipeline/test_financial_score_persistence.py")
text2 = p2.read_text(encoding="utf-8")

old_class_2 = """class TestFinancialScorePersistence(unittest.TestCase):
    \"\"\"Unit and Integration tests for Financial Score Database Persistence.\"\"\"

    def setUp(self):
        \"\"\"Setup test environment and clean up test rows.\"\"\"
        self.test_date = "2026-08-14"
        self._cleanup_test_records()"""

new_class_2 = """import tempfile
import shutil
import pathlib
import backend.data_pipeline.financial_service as fin_svc

class TestFinancialScorePersistence(unittest.TestCase):
    \"\"\"Unit and Integration tests for Financial Score Database Persistence.\"\"\"

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

    def setUp(self):
        \"\"\"Setup test environment and clean up test rows.\"\"\"
        self.test_date = "2026-08-14"
        self._cleanup_test_records()"""

text2 = text2.replace("DATABASE_PATH,", "DATABASE_PATH as _DEFAULT_DB_PATH,")
text2 = text2.replace("sqlite3.connect(DATABASE_PATH)", "sqlite3.connect(fin_svc.DATABASE_PATH)")
text2 = text2.replace(old_class_2, new_class_2, 1)
p2.write_text(text2, encoding="utf-8")
print("Patched test_financial_score_persistence.py")

