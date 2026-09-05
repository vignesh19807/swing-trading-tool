import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.data_pipeline.run_daily_update import update_technical_data

if __name__ == "__main__":
    update_technical_data()
