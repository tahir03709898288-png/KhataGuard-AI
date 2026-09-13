"""
KhataGuard Core Integration Layer

This module provides a simple interface between:
    Part 1 UI
    Part 2 Database
    Part 3 AI

The UI and AI should use these functions instead of
directly writing SQL queries.
"""

from .database.customers import (
    add_customer,
    get_customer,
    get_all_customers,
    update_customer,
    delete_customer,
)

from .database.transactions import (
    add_transaction,
    get_transaction,
    get_customer_transactions,
    get_all_transactions,
    delete_transaction,
)

from .database.ledger import (
    get_customer_balance,
    get_customer_ledger,
    get_total_sales,
    get_total_received,
    get_total_outstanding,
    get_outstanding_customers,
)


# ============================================================
# Customer Functions
# ============================================================

def create_customer(name, phone=None):
    """
    Create a new customer.

    Returns:
        customer_id
    """

    return add_customer(
        name=name,
        phone=phone
    )


def list_customers():
    """
    Return all customers.
    """

    return get_all_customers()


def find_customer_by_name(name):
    """
    Find a customer using their name.

    Matching is case-insensitive and ignores
    extra spaces.

    Raises:
        ValueError if customer is not found.
        ValueError if multiple customers have
        the same name.
    """

    if not name or not name.strip():
        raise ValueError("Customer name cannot be empty.")

    search_name = name.strip().lower()

    customers = get_all_customers()

    matches = [
        customer
        for customer in customers
        if customer["name"].strip().lower() == search_name
    ]

    if not matches:
        raise ValueError("Customer not found.")

    if len(matches) > 1:
        raise ValueError(
            "Multiple customers have the same name. "
            "Please use a unique customer name."
        )

    return matches[0]


# ============================================================
# Part 1 Transaction Function
# ============================================================

def record_sale(
    customer_name,
    sale_amount,
    paid_amount=0,
    description=None,
    transaction_date=None
):
    """
    Record a sale and optional payment for a customer.

    This function is designed specifically for the
    Part 1 transaction screen.

    Example:

        Sale = 5000
        Paid = 2000

    Database will store:

        sale     = 5000
        payment  = 2000

    Outstanding balance:

        5000 - 2000 = 3000
    """

    # --------------------------------------------------------
    # Validate customer
    # --------------------------------------------------------

    customer = find_customer_by_name(customer_name)

    customer_id = customer["id"]

    # --------------------------------------------------------
    # Validate sale amount
    # --------------------------------------------------------

    if sale_amount is None:
        raise ValueError("Sale amount is required.")

    try:
        sale_amount = float(sale_amount)
    except (TypeError, ValueError):
        raise ValueError("Sale amount must be a valid number.")

    if sale_amount <= 0:
        raise ValueError("Sale amount must be greater than zero.")

    # --------------------------------------------------------
    # Validate paid amount
    # --------------------------------------------------------

    if paid_amount is None or paid_amount == "":
        paid_amount = 0

    try:
        paid_amount = float(paid_amount)
    except (TypeError, ValueError):
        raise ValueError("Paid amount must be a valid number.")

    if paid_amount < 0:
        raise ValueError("Paid amount cannot be negative.")

    # --------------------------------------------------------
    # Prevent overpayment in normal sale entry
    # --------------------------------------------------------

    if paid_amount > sale_amount:
        raise ValueError(
            "Paid amount cannot be greater than sale amount."
        )

    # --------------------------------------------------------
    # Create SALE transaction
    # --------------------------------------------------------

    sale_transaction_id = add_transaction(
        customer_id=customer_id,
        transaction_type="sale",
        amount=sale_amount,
        description=description,
        transaction_date=transaction_date
    )

    # --------------------------------------------------------
    # Create PAYMENT transaction if payment exists
    # --------------------------------------------------------

    payment_transaction_id = None

    if paid_amount > 0:

        payment_transaction_id = add_transaction(
            customer_id=customer_id,
            transaction_type="payment",
            amount=paid_amount,
            description=description,
            transaction_date=transaction_date
        )

    # --------------------------------------------------------
    # Return useful result for UI / AI
    # --------------------------------------------------------

    balance = get_customer_balance(customer_id)

    return {
        "customer_id": customer_id,
        "customer_name": customer["name"],
        "sale_transaction_id": sale_transaction_id,
        "payment_transaction_id": payment_transaction_id,
        "sale_amount": sale_amount,
        "paid_amount": paid_amount,
        "outstanding": balance,
    }


# ============================================================
# Payment Function
# ============================================================

def record_payment(
    customer_name,
    amount,
    description=None,
    transaction_date=None
):
    """
    Record a payment from an existing customer.

    Useful for cases where the customer pays
    an already-existing outstanding balance.
    """

    customer = find_customer_by_name(customer_name)

    customer_id = customer["id"]

    transaction_id = add_transaction(
        customer_id=customer_id,
        transaction_type="payment",
        amount=amount,
        description=description,
        transaction_date=transaction_date
    )

    balance = get_customer_balance(customer_id)

    return {
        "customer_id": customer_id,
        "customer_name": customer["name"],
        "transaction_id": transaction_id,
        "payment_amount": float(amount),
        "outstanding": balance,
    }


# ============================================================
# Customer Ledger
# ============================================================

def get_customer_statement(customer_name):
    """
    Return complete ledger information for a customer.
    """

    customer = find_customer_by_name(customer_name)

    customer_id = customer["id"]

    ledger = get_customer_ledger(customer_id)

    return {
        "customer_id": customer_id,
        "customer_name": customer["name"],
        "phone": customer["phone"],
        "balance": get_customer_balance(customer_id),
        "ledger": ledger,
    }


# ============================================================
# Dashboard Summary
# ============================================================

def get_dashboard_summary():
    """
    Return all main business figures required
    by the Part 1 dashboard.
    """

    return {
        "total_sales": get_total_sales(),
        "total_received": get_total_received(),
        "total_outstanding": get_total_outstanding(),
        "outstanding_customers": get_outstanding_customers(),
    }

# ============================================================
# Customer Summaries
# ============================================================

def get_customer_summaries():
    """
    Return customer-wise financial summaries.

    Each customer will include:
        - id
        - name
        - phone
        - total_sale
        - total_paid
        - outstanding
    """

    customers = get_all_customers()

    summaries = []

    for customer in customers:

        customer_id = customer["id"]

        # Get all transactions for this customer
        transactions = get_customer_transactions(customer_id)

        total_sale = 0.0
        total_paid = 0.0

        for transaction in transactions:

            if transaction["type"] == "sale":
                total_sale += float(transaction["amount"])

            elif transaction["type"] == "payment":
                total_paid += float(transaction["amount"])

        outstanding = total_sale - total_paid

        summaries.append(
            {
                "id": customer_id,
                "name": customer["name"],
                "phone": customer["phone"],
                "total_sale": total_sale,
                "total_paid": total_paid,
                "outstanding": outstanding,
            }
        )

    return summaries


# ============================================================
# Customer List for UI
# ============================================================

def get_customers_for_ui(search=None):
    """
    Return customer data in the format required by
    the Part 1 Customers screen.

    Optional search filters customers by name or phone.
    """

    summaries = get_customer_summaries()

    if search:
        search = search.strip().lower()

        summaries = [
            customer
            for customer in summaries
            if search in customer["name"].lower()
            or (
                customer["phone"]
                and search in customer["phone"].lower()
            )
        ]

    return summaries
