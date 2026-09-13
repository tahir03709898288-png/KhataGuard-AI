"""Controlled demo-data seeding for the KhataGuard hackathon.

This module uses the existing KhataGuard SQLite schema.  It deliberately refuses
 to seed a non-empty database by default, because a demo-data button must never
 overwrite or mix with a user's real khata data accidentally.

For testing or a disposable demo database, pass ``database_path`` explicitly.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Final


DEMO_CUSTOMERS: Final[tuple[tuple[str, str], ...]] = (
    ("Ahmed Khan", "0300-1234567"),
    ("Bilal Ahmed", "0311-2345678"),
    ("Kashif Ali", "0322-3456789"),
    ("Usama Raza", "0333-4567890"),
    ("Tariq Mehmood", "0344-5678901"),
)


@dataclass(frozen=True)
class DemoTransaction:
    customer_index: int
    transaction_type: str
    amount: float
    days_after_start: int
    description: str


# Exactly 20 deterministic transactions: four per customer.
DEMO_TRANSACTIONS: Final[tuple[DemoTransaction, ...]] = (
    DemoTransaction(0, "sale", 4500.0, 0, "Kiryana saman"),
    DemoTransaction(0, "payment", 2000.0, 1, "Cash payment"),
    DemoTransaction(0, "sale", 3200.0, 2, "Monthly grocery"),
    DemoTransaction(0, "payment", 1000.0, 3, "Partial payment"),

    DemoTransaction(1, "sale", 5500.0, 4, "Household items"),
    DemoTransaction(1, "sale", 2800.0, 5, "Grocery items"),
    DemoTransaction(1, "payment", 3000.0, 6, "Cash received"),
    DemoTransaction(1, "sale", 1900.0, 7, "Milk and grocery"),

    DemoTransaction(2, "sale", 7500.0, 8, "Monthly grocery"),
    DemoTransaction(2, "payment", 2500.0, 9, "Partial payment"),
    DemoTransaction(2, "sale", 4100.0, 10, "General store items"),
    DemoTransaction(2, "payment", 3000.0, 11, "Cash payment"),

    DemoTransaction(3, "sale", 6200.0, 12, "Grocery purchase"),
    DemoTransaction(3, "payment", 2000.0, 13, "Cash payment"),
    DemoTransaction(3, "sale", 3500.0, 14, "Household supplies"),
    DemoTransaction(3, "payment", 1500.0, 15, "Partial payment"),

    DemoTransaction(4, "sale", 4800.0, 16, "Monthly grocery"),
    DemoTransaction(4, "payment", 1800.0, 17, "Cash received"),
    DemoTransaction(4, "sale", 2700.0, 18, "Kitchen items"),
    DemoTransaction(4, "payment", 1000.0, 19, "Partial payment"),
)


EXPECTED_OUTSTANDING: Final[dict[str, float]] = {
    "Ahmed Khan": 4700.0,
    "Bilal Ahmed": 7200.0,
    "Kashif Ali": 6100.0,
    "Usama Raza": 6200.0,
    "Tariq Mehmood": 4700.0,
}


class DemoDataError(RuntimeError):
    """Raised when demo data cannot be safely seeded."""


def _validate_existing_schema(connection: sqlite3.Connection) -> None:
    """Ensure the database has the exact tables/columns Part 2 provides."""
    required = {
        "customers": {"id", "name", "phone", "created_at"},
        "transactions": {
            "id",
            "customer_id",
            "type",
            "amount",
            "description",
            "transaction_date",
            "created_at",
        },
    }

    for table, columns in required.items():
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        if row is None:
            raise DemoDataError(f"Required table '{table}' does not exist.")

        actual = {
            item[1]
            for item in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        missing = columns - actual
        if missing:
            raise DemoDataError(
                f"Table '{table}' is missing required columns: {sorted(missing)}"
            )


def _ensure_empty_database(connection: sqlite3.Connection) -> None:
    """Never mix the deterministic demo dataset with existing customer data."""
    customer_count = connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    transaction_count = connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]

    if customer_count or transaction_count:
        raise DemoDataError(
            "Demo data seeding stopped: the selected database is not empty. "
            "Use a disposable/copy of khata.db for the hackathon demo instead of "
            "mixing demo records with existing data."
        )


def generate_demo_data(
    database_path: str | Path,
    *,
    start_date: date | str | None = None,
) -> dict[str, object]:
    """Seed five customers and twenty transactions into an EMPTY existing DB.

    Args:
        database_path: SQLite file that already has the KhataGuard Part 2 schema.
        start_date: Date for the first transaction. Defaults to 20 days ago.

    Returns:
        A deterministic summary suitable for displaying in Streamlit or tests.

    Raises:
        DemoDataError: if the schema is incompatible or the DB is not empty.
    """
    path = Path(database_path)
    if not path.exists():
        raise DemoDataError(f"Database file does not exist: {path}")

    if start_date is None:
        first_date = date.today() - timedelta(days=20)
    elif isinstance(start_date, date):
        first_date = start_date
    elif isinstance(start_date, str):
        try:
            first_date = date.fromisoformat(start_date)
        except ValueError as exc:
            raise DemoDataError(
                "start_date must be an ISO date like YYYY-MM-DD."
            ) from exc
    else:
        raise DemoDataError("start_date must be a date, ISO date string, or None.")
    connection = sqlite3.connect(path)

    try:
        _validate_existing_schema(connection)
        _ensure_empty_database(connection)

        customer_ids: list[int] = []
        for name, phone in DEMO_CUSTOMERS:
            cursor = connection.execute(
                "INSERT INTO customers (name, phone) VALUES (?, ?)",
                (name, phone),
            )
            customer_ids.append(int(cursor.lastrowid))

        for item in DEMO_TRANSACTIONS:
            transaction_date = first_date + timedelta(days=item.days_after_start)
            connection.execute(
                """
                INSERT INTO transactions
                    (customer_id, type, amount, description, transaction_date)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    customer_ids[item.customer_index],
                    item.transaction_type,
                    item.amount,
                    item.description,
                    transaction_date.isoformat(),
                ),
            )

        connection.commit()

        customer_count = connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        transaction_count = connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        total_sales = connection.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='sale'"
        ).fetchone()[0]
        total_paid = connection.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='payment'"
        ).fetchone()[0]

        return {
            "customer_ids": customer_ids,
            "customer_count": int(customer_count),
            "transaction_count": int(transaction_count),
            "total_sales": float(total_sales),
            "total_paid": float(total_paid),
            "total_outstanding": float(total_sales - total_paid),
            "expected_outstanding": dict(EXPECTED_OUTSTANDING),
            "start_date": first_date.isoformat(),
            "end_date": (first_date + timedelta(days=19)).isoformat(),
        }

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    # CLI entry point intentionally uses the project's actual DB only when it is
    # empty. It will never delete/reset existing data.
    from backend.database.database import DATABASE_PATH

    summary = generate_demo_data(DATABASE_PATH)
    print("KhataGuard demo data generated successfully.")
    print(f"Customers: {summary['customer_count']}")
    print(f"Transactions: {summary['transaction_count']}")
    print(f"Total sales: Rs. {summary['total_sales']:,.2f}")
    print(f"Total paid: Rs. {summary['total_paid']:,.2f}")
    print(f"Outstanding: Rs. {summary['total_outstanding']:,.2f}")
