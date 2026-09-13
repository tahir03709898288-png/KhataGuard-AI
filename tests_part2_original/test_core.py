import tempfile
from pathlib import Path
import sys

import pytest

# Project root ko Python path mein add karo
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import database
from backend.core import (
    create_customer,
    find_customer_by_name,
    record_sale,
    record_payment,
    get_customer_statement,
    get_dashboard_summary,
    get_customer_summaries,
    get_customers_for_ui,
)

@pytest.fixture
def test_database():
    """
    Create a temporary database for core-layer testing.
    """

    temporary_directory = tempfile.TemporaryDirectory()

    test_database_path = Path(
        temporary_directory.name
    ) / "test_khata.db"

    original_database_path = database.DATABASE_PATH

    database.DATABASE_PATH = test_database_path

    database.initialize_database()

    yield test_database_path

    database.DATABASE_PATH = original_database_path

    temporary_directory.cleanup()


def test_create_and_find_customer(test_database):
    """
    Test customer creation and name-based lookup.
    """

    customer_id = create_customer(
        name="Ahmed",
        phone="03001234567"
    )

    assert customer_id > 0

    customer = find_customer_by_name("Ahmed")

    assert customer["id"] == customer_id
    assert customer["name"] == "Ahmed"


def test_record_sale_with_payment(test_database):
    """
    Test the Part 1 transaction flow:

    Sale = 5000
    Paid = 2000
    Outstanding = 3000
    """

    create_customer("Ahmed")

    result = record_sale(
        customer_name="Ahmed",
        sale_amount=5000,
        paid_amount=2000,
        description="Grocery"
    )

    assert result["customer_name"] == "Ahmed"
    assert result["sale_amount"] == 5000
    assert result["paid_amount"] == 2000
    assert result["outstanding"] == 3000


def test_record_payment(test_database):
    """
    Test recording a separate payment.
    """

    create_customer("Ali")

    record_sale(
        customer_name="Ali",
        sale_amount=5000,
        paid_amount=0
    )

    result = record_payment(
        customer_name="Ali",
        amount=2000,
        description="Cash payment"
    )

    assert result["payment_amount"] == 2000
    assert result["outstanding"] == 3000


def test_customer_statement(test_database):
    """
    Test complete customer statement.
    """

    create_customer("Usman")

    record_sale(
        customer_name="Usman",
        sale_amount=10000,
        paid_amount=4000,
        description="Items"
    )

    statement = get_customer_statement("Usman")

    assert statement["customer_name"] == "Usman"
    assert statement["balance"] == 6000
    assert len(statement["ledger"]) == 2


def test_dashboard_summary(test_database):
    """
    Test dashboard totals.
    """

    create_customer("Bilal")

    record_sale(
        customer_name="Bilal",
        sale_amount=8000,
        paid_amount=3000
    )

    summary = get_dashboard_summary()

    assert summary["total_sales"] == 8000
    assert summary["total_received"] == 3000
    assert summary["total_outstanding"] == 5000



def test_customer_financial_summary(test_database):
    """
    Test customer-wise financial summary.

    Sale = 5000
    Paid = 2000
    Outstanding = 3000
    """

    create_customer(
        name="Ahmed",
        phone="03001234567"
    )

    record_sale(
        customer_name="Ahmed",
        sale_amount=5000,
        paid_amount=2000,
        description="Grocery"
    )

    summaries = get_customer_summaries()

    assert len(summaries) == 1

    customer = summaries[0]

    assert customer["name"] == "Ahmed"
    assert customer["phone"] == "03001234567"
    assert customer["total_sale"] == 5000
    assert customer["total_paid"] == 2000
    assert customer["outstanding"] == 3000



def test_get_customers_for_ui(test_database):
    customer_id = create_customer(
        name="UI Test Customer",
        phone="0300-9999999"
    )

    record_sale(
        customer_name="UI Test Customer",
        sale_amount=5000,
        paid_amount=2000
    )

    customers = get_customers_for_ui()

    customer = next(
        item for item in customers
        if item["id"] == customer_id
    )

    assert customer["name"] == "UI Test Customer"
    assert customer["phone"] == "0300-9999999"
    assert customer["total_sale"] == 5000
    assert customer["total_paid"] == 2000
    assert customer["outstanding"] == 3000

    searched = get_customers_for_ui(search="UI Test")

    assert len(searched) == 1
    assert searched[0]["id"] == customer_id
