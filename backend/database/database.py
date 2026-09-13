import sqlite3
from pathlib import Path


# ============================================================
# KhataGuard - Database Configuration
# ============================================================

# Project root folder:
# khataguard-part2/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# SQLite database file
DATABASE_PATH = PROJECT_ROOT / "khata.db"


# ============================================================
# Database Connection
# ============================================================

def get_connection():
    """
    Create and return a connection to the KhataGuard SQLite database.
    """

    connection = sqlite3.connect(DATABASE_PATH)

    # Enable foreign key protection
    connection.execute("PRAGMA foreign_keys = ON")

    # Return rows like dictionaries:
    # row["name"], row["phone"], etc.
    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# Initialize Database
# ============================================================

def initialize_database():
    """
    Create all required KhataGuard database tables
    if they do not already exist.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # ----------------------------------------------------
        # Customers Table
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ----------------------------------------------------
        # Transactions Table
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                transaction_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (customer_id)
                    REFERENCES customers(id)
                    ON DELETE RESTRICT
            )
        """)

        # ----------------------------------------------------
        # Indexes
        # ----------------------------------------------------

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_customer
            ON transactions(customer_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_date
            ON transactions(transaction_date)
        """)

        # Save changes
        connection.commit()

    except Exception:
        # If anything goes wrong, undo the changes
        connection.rollback()
        raise

    finally:
        # Always close the database connection
        connection.close()


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    initialize_database()
    print("KhataGuard database initialized successfully.")


# Initialize database automatically when the backend is imported.
initialize_database()
