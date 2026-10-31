import pathlib

# Fix test_backtest_result_service.py
file_path_1 = pathlib.Path("backend/data_pipeline/test_backtest_result_service.py")
c1 = file_path_1.read_text(encoding="utf-8").replace("\r\n", "\n")

old_setup = """    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = pathlib.Path(cls.temp_dir.name) / "test_swing_trading.db"
        cls.orig_db_path = b_svc.DATABASE_PATH
        b_svc.DATABASE_PATH = cls.test_db_path
        initialize_backtest_results_table()"""

new_setup = """    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = pathlib.Path(cls.temp_dir.name) / "test_swing_trading.db"
        sqlite3.connect(cls.test_db_path).close()
        cls.orig_db_path = b_svc.DATABASE_PATH
        b_svc.DATABASE_PATH = cls.test_db_path
        initialize_backtest_results_table()"""

if old_setup in c1:
    c1 = c1.replace(old_setup, new_setup, 1)
    file_path_1.write_text(c1.replace("\n", "\r\n"), encoding="utf-8")
    print("Patched test_backtest_result_service.py")
else:
    print("Could not find old_setup in test_backtest_result_service.py")

# Fix test_week14_integration.py
file_path_2 = pathlib.Path("backend/data_pipeline/test_week14_integration.py")
c2 = file_path_2.read_text(encoding="utf-8").replace("\r\n", "\n")

old_week14 = """import tempfile
import backend.data_pipeline.backtest_result_service as b_svc

class TestWeek14Integration(unittest.TestCase):"""

new_week14 = """import tempfile
import pathlib
import backend.data_pipeline.backtest_result_service as b_svc

class TestWeek14Integration(unittest.TestCase):"""

old_w14_setup = """    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = pathlib.Path(cls.temp_dir.name) / "test_swing_trading.db"
        cls.orig_db_path = b_svc.DATABASE_PATH
        b_svc.DATABASE_PATH = cls.test_db_path
        initialize_backtest_results_table()"""

new_w14_setup = """    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = pathlib.Path(cls.temp_dir.name) / "test_swing_trading.db"
        sqlite3.connect(cls.test_db_path).close()
        cls.orig_db_path = b_svc.DATABASE_PATH
        b_svc.DATABASE_PATH = cls.test_db_path
        initialize_backtest_results_table()"""

if old_week14 in c2:
    c2 = c2.replace(old_week14, new_week14, 1)
if old_w14_setup in c2:
    c2 = c2.replace(old_w14_setup, new_w14_setup, 1)
file_path_2.write_text(c2.replace("\n", "\r\n"), encoding="utf-8")
print("Patched test_week14_integration.py")

