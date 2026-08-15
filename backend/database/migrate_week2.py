import sqlite3
from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    PROJECT_ROOT
    / "database"
    / "swing_trading.db"
)


# ============================================================
# MIGRATION
# ============================================================

def migrate_database():

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    print("==========================================")
    print("WEEK 2 DATABASE MIGRATION")
    print("==========================================")

    # Check existing columns
    cursor.execute("PRAGMA table_info(companies)")

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    print(f"Existing columns: {columns}")

    # Add industry if it doesn't exist
    if "industry" not in columns:

        cursor.execute("""
            ALTER TABLE companies
            ADD COLUMN industry TEXT
        """)

        print("✓ Added industry column")

    else:

        print("✓ Industry column already exists")

    connection.commit()

    # Verify
    cursor.execute("PRAGMA table_info(companies)")

    final_columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    connection.close()

    print("------------------------------------------")
    print(f"Final columns: {final_columns}")
    print("==========================================")
    print("DATABASE MIGRATION COMPLETE")
    print("==========================================")


if __name__ == "__main__":
    migrate_database()