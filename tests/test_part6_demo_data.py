from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from backend.features.demo_data import (
    DEMO_CUSTOMERS,
    DEMO_TRANSACTIONS,
    EXPECTED_OUTSTANDING,
    DemoDataError,
    generate_demo_data,
)


def test_demo_generator_populates_exact_expected_dataset(tmp_path: Path):
    db_path = tmp_path / "demo.db"

    # Create the same schema used by the real project, but in an isolated DB.
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            transaction_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
        );
        """
    )
    connection.commit()
    connection.close()

    summary = generate_demo_data(db_path, start_date=date(2026, 9, 1))

    assert summary["customer_count"] == len(DEMO_CUSTOMERS) == 5
    assert summary["transaction_count"] == len(DEMO_TRANSACTIONS) == 20
    assert summary["total_sales"] == 46700.0
    assert summary["total_paid"] == 17800.0
    assert summary["total_outstanding"] == 28900.0

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT c.name,
               COALESCE(SUM(CASE WHEN t.type='sale' THEN t.amount
                                 WHEN t.type='payment' THEN -t.amount
                                 ELSE 0 END), 0) AS balance
        FROM customers c
        LEFT JOIN transactions t ON t.customer_id = c.id
        GROUP BY c.id, c.name
        ORDER BY c.id
        """
    ).fetchall()
    connection.close()

    actual = {row["name"]: float(row["balance"]) for row in rows}
    assert actual == EXPECTED_OUTSTANDING


def test_demo_generator_refuses_non_empty_database(tmp_path: Path):
    db_path = tmp_path / "existing.db"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            transaction_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
        );
        INSERT INTO customers (name, phone) VALUES ('Real Customer', '03001234567');
        """
    )
    connection.commit()
    connection.close()

    with pytest.raises(DemoDataError, match="not empty"):
        generate_demo_data(db_path)
