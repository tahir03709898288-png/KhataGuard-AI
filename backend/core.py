"""Core business logic for KhataGuard operations."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from backend.database.customers import add_customer, get_all_customers
from backend.database.transactions import add_transaction, get_transactions_by_customer, get_all_transactions


def create_customer(name: str, phone: Optional[str] = None) -> int:
    name = (name or "").strip()
    if not name:
        raise ValueError("Customer name is required.")
    return add_customer(name=name, phone=phone)


def list_customers() -> List[Dict[str, Any]]:
    return [dict(row) for row in get_all_customers()]


def get_customers_for_ui(search: Optional[str] = None) -> List[Dict[str, Any]]:
    """Helper function for UI display with search filter and aggregated fields."""
    customers = list_customers()
    if search and search.strip():
        term = search.strip().casefold()
        customers = [c for c in customers if term in str(c.get("name", "")).casefold()]
    
    for c in customers:
        statement = get_customer_statement(c["id"])
        c["total_sale"] = statement.get("total_sale", 0.0)
        c["outstanding"] = statement.get("balance", 0.0)
    return customers


def get_customer_statement(customer_id: int) -> Dict[str, Any]:
    """Calculate running balance, sales, and payments for a customer."""
    txs = [dict(row) for row in get_transactions_by_customer(customer_id)]
    
    total_sale = 0.0
    total_paid = 0.0
    statement_rows = []
    running_balance = 0.0

    for tx in txs:
        tx_type = tx.get("tx_type", "").lower()
        amount = float(tx.get("amount", 0.0))
        
        if tx_type == "sale":
            total_sale += amount
            running_balance += amount
        elif tx_type == "payment":
            total_paid += amount
            running_balance -= amount
            
        statement_rows.append({
            "id": tx.get("id"),
            "date": tx.get("transaction_date"),
            "type": tx_type.upper(),
            "description": tx.get("description") or "—",
            "amount": amount,
            "running_balance": running_balance,
        })

    return {
        "customer_id": customer_id,
        "total_sale": total_sale,
        "total_paid": total_paid,
        "balance": running_balance,
        "transactions": statement_rows,
    }


def get_customer_summaries() -> List[Dict[str, Any]]:
    """Helper for Reports page to view overall ledger health."""
    customers = list_customers()
    summaries = []
    for c in customers:
        stmt = get_customer_statement(c["id"])
        summaries.append({
            "id": c["id"],
            "name": c["name"],
            "phone": c.get("phone") or "—",
            "total_sale": stmt["total_sale"],
            "total_paid": stmt["total_paid"],
            "balance": stmt["balance"],
        })
    return summaries


def record_sale(
    customer_name: str,
    sale_amount: float,
    paid_amount: float = 0.0,
    description: Optional[str] = None,
    transaction_date: Optional[str] = None,
) -> Dict[str, Any]:
    sale_amount = float(sale_amount)
    paid_amount = float(paid_amount)

    if sale_amount <= 0:
        raise ValueError("Sale amount must be greater than zero.")
    if paid_amount < 0:
        raise ValueError("Paid amount cannot be negative.")

    t_date = transaction_date or date.today().isoformat()
    customers = list_customers()
    matched = [c for c in customers if str(c["name"]).strip().casefold() == customer_name.strip().casefold()]

    if not matched:
        customer_id = create_customer(name=customer_name)
    else:
        customer_id = matched[0]["id"]

    sale_id = add_transaction(
        customer_id=customer_id,
        tx_type="sale",
        amount=sale_amount,
        description=description,
        transaction_date=t_date,
    )

    payment_id = None
    if paid_amount > 0:
        payment_id = add_transaction(
            customer_id=customer_id,
            tx_type="payment",
            amount=paid_amount,
            description=f"Paid against sale / advance (Ref Sale #{sale_id})",
            transaction_date=t_date,
        )

    return {
        "status": "success",
        "customer_id": customer_id,
        "sale_id": sale_id,
        "payment_id": payment_id,
        "sale_amount": sale_amount,
        "paid_amount": paid_amount,
    }


def record_payment(
    customer_name: str,
    amount: float,
    description: Optional[str] = None,
    transaction_date: Optional[str] = None,
) -> Dict[str, Any]:
    amount = float(amount)
    if amount <= 0:
        raise ValueError("Payment amount must be greater than zero.")

    t_date = transaction_date or date.today().isoformat()
    customers = list_customers()
    matched = [c for c in customers if str(c["name"]).strip().casefold() == customer_name.strip().casefold()]

    if not matched:
        customer_id = create_customer(name=customer_name)
    else:
        customer_id = matched[0]["id"]

    payment_id = add_transaction(
        customer_id=customer_id,
        tx_type="payment",
        amount=amount,
        description=description,
        transaction_date=t_date,
    )

    return {
        "status": "success",
        "customer_id": customer_id,
        "payment_id": payment_id,
        "amount": amount,
    }
