from .database import get_connection


# ============================================================
# Customer Balance
# ============================================================

def get_customer_balance(customer_id):
    """
    Calculate the current outstanding balance of a customer.

    Sale    = customer owes more
    Payment = customer owes less

    Example:
    Sale 5000
    Payment 2000
    Balance = 3000
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Check customer exists
        cursor.execute(
            """
            SELECT id
            FROM customers
            WHERE id = ?
            """,
            (customer_id,)
        )

        customer = cursor.fetchone()

        if customer is None:
            raise ValueError("Customer not found.")

        # Calculate balance
        cursor.execute(
            """
            SELECT
                COALESCE(
                    SUM(
                        CASE
                            WHEN type = 'sale' THEN amount
                            WHEN type = 'payment' THEN -amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS balance
            FROM transactions
            WHERE customer_id = ?
            """,
            (customer_id,)
        )

        result = cursor.fetchone()

        return float(result["balance"])

    finally:
        connection.close()


# ============================================================
# Customer Ledger
# ============================================================

def get_customer_ledger(customer_id):
    """
    Return a customer's complete ledger with running balance.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Check customer exists
        cursor.execute(
            """
            SELECT id, name, phone
            FROM customers
            WHERE id = ?
            """,
            (customer_id,)
        )

        customer = cursor.fetchone()

        if customer is None:
            raise ValueError("Customer not found.")

        # Get transactions
        cursor.execute(
            """
            SELECT
                id,
                customer_id,
                type,
                amount,
                description,
                transaction_date,
                created_at
            FROM transactions
            WHERE customer_id = ?
            ORDER BY transaction_date ASC, id ASC
            """,
            (customer_id,)
        )

        transactions = cursor.fetchall()

        ledger = []
        balance = 0.0

        for transaction in transactions:

            if transaction["type"] == "sale":
                debit = float(transaction["amount"])
                credit = 0.0
                balance += debit

            elif transaction["type"] == "payment":
                debit = 0.0
                credit = float(transaction["amount"])
                balance -= credit

            else:
                continue

            ledger.append(
                {
                    "id": transaction["id"],
                    "customer_id": transaction["customer_id"],
                    "type": transaction["type"],
                    "amount": float(transaction["amount"]),
                    "description": transaction["description"],
                    "transaction_date": transaction["transaction_date"],
                    "debit": debit,
                    "credit": credit,
                    "balance": balance,
                }
            )

        return ledger

    finally:
        connection.close()


# ============================================================
# Total Sales
# ============================================================

def get_total_sales():
    """
    Return total sales across all customers.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total_sales
            FROM transactions
            WHERE type = 'sale'
            """
        )

        result = cursor.fetchone()

        return float(result["total_sales"])

    finally:
        connection.close()


# ============================================================
# Total Received
# ============================================================

def get_total_received():
    """
    Return total payments received from all customers.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total_received
            FROM transactions
            WHERE type = 'payment'
            """
        )

        result = cursor.fetchone()

        return float(result["total_received"])

    finally:
        connection.close()


# ============================================================
# Total Outstanding
# ============================================================

def get_total_outstanding():
    """
    Return total outstanding amount across all customers.
    """

    total_sales = get_total_sales()
    total_received = get_total_received()

    return total_sales - total_received


# ============================================================
# Outstanding Customers
# ============================================================

def get_outstanding_customers():
    """
    Return customers who currently owe money.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                c.id,
                c.name,
                c.phone,
                COALESCE(
                    SUM(
                        CASE
                            WHEN t.type = 'sale' THEN t.amount
                            WHEN t.type = 'payment' THEN -t.amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS balance
            FROM customers c
            LEFT JOIN transactions t
                ON c.id = t.customer_id
            GROUP BY c.id, c.name, c.phone
            HAVING balance > 0
            ORDER BY balance DESC
            """
        )

        return cursor.fetchall()

    finally:
        connection.close()
