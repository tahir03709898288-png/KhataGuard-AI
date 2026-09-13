import tempfile
from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import database
from backend.database.customers import add_customer
from backend.database.transactions import add_transaction
from backend.database.ledger import (
    get_customer_balance,
    get_customer_ledger,
    get_total_sales,
    get_total_received,
    get_total_outstanding,
)


@pytest.fixture
def test_database():
    """
    Create a temporary database for testing.
    """

    temporary_directory = tempfile.TemporaryDirectory()

    test_database_path = Path(temporary_directory.name) / "test_khata.db"

    original_database_path = database.DATABASE_PATH

    database.DATABASE_PATH = test_database_path

    database.initialize_database()

    yield test_database_path

    database.DATABASE_PATH = original_database_path

    temporary_directory.cleanup()


def test_add_customer(test_database):
    """
    Test that a customer can be added successfully.
    """

    customer_id = add_customer(
        name="Ahmed",
        phone="03001234567"
    )

    assert customer_id > 0


def test_sale_and_payment_balance(test_database):
    """
    Test the main KhataGuard calculation:

    Sale = 5000
    Payment = 2000
    Balance = 3000
    """

    customer_id = add_customer("Ahmed")

    add_transaction(
        customer_id=customer_id,
        transaction_type="sale",
        amount=5000,
        description="Grocery"
    )

    add_transaction(
        customer_id=customer_id,
        transaction_type="payment",
        amount=2000,
        description="Cash payment"
    )

    balance = get_customer_balance(customer_id)

    assert balance == 3000


def test_customer_ledger(test_database):
    """
    Test customer ledger and running balance.
    """

    customer_id = add_customer("Ali")

    add_transaction(
        customer_id=customer_id,
        transaction_type="sale",
        amount=5000,
        description="Items"
    )

    add_transaction(
        customer_id=customer_id,
        transaction_type="payment",
        amount=2000,
        description="Payment"
    )

    ledger = get_customer_ledger(customer_id)

    assert len(ledger) == 2

    assert ledger[0]["debit"] == 5000
    assert ledger[0]["balance"] == 5000

    assert ledger[1]["credit"] == 2000
    assert ledger[1]["balance"] == 3000


def test_total_business_amounts(test_database):
    """
    Test total sales, total received,
    and total outstanding.
    """

    customer_id = add_customer("Usman")

    add_transaction(
        customer_id=customer_id,
        transaction_type="sale",
        amount=10000
    )

    add_transaction(
        customer_id=customer_id,
        transaction_type="payment",
        amount=4000
    )

    assert get_total_sales() == 10000
    assert get_total_received() == 4000
    assert get_total_outstanding() == 6000


def test_invalid_customer_name(test_database):
    """
    Empty customer names should be rejected.
    """

    with pytest.raises(ValueError):
        add_customer("")


def test_invalid_transaction_type(test_database):
    """
    Only sale and payment are allowed.
    """

    customer_id = add_customer("Bilal")

    with pytest.raises(ValueError):
        add_transaction(
            customer_id=customer_id,
            transaction_type="wrong_type",
            amount=1000
        )


def test_invalid_amount(test_database):
    """
    Zero and negative amounts should be rejected.
    """

    customer_id = add_customer("Hamza")

    with pytest.raises(ValueError):
        add_transaction(
            customer_id=customer_id,
            transaction_type="sale",
            amount=0
        )

    with pytest.raises(ValueError):
        add_transaction(
            customer_id=customer_id,
            transaction_type="sale",
            amount=-500
        )


def test_nonexistent_customer(test_database):
    """
    Transactions for a customer that does not exist
    should be rejected.
    """

    with pytest.raises(ValueError):
        add_transaction(
            customer_id=999999,
            transaction_type="sale",
            amount=1000
        )
