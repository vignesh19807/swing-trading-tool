import os
import subprocess
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXE = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
SCRIPT_PATH = PROJECT_ROOT / "backend" / "data_pipeline" / "run_daily_update.py"

# Task settings
TASK_NAME = "SwingTrading_DailyUpdate"
SCHEDULE_TIME = "18:00"  # 6:00 PM IST

def create_scheduled_task():
    print("=" * 50)
    print("Configuring Windows Task Scheduler")
    print("=" * 50)
    
    # First, try to delete if exists
    subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    command = (
        f'schtasks /Create /SC DAILY /TN "{TASK_NAME}" '
        f'/TR "\\"{PYTHON_EXE}\\" \\"{SCRIPT_PATH}\\"" '
        f'/ST {SCHEDULE_TIME} /F'
    )
    
    print(f"Executing: {command}")
    
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"\\n[OK] Successfully scheduled {TASK_NAME} to run daily at {SCHEDULE_TIME}.")
    else:
        print(f"\\n[FAIL] Failed to schedule task.")
        print(result.stderr)
        
if __name__ == "__main__":
    create_scheduled_task()
