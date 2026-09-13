"""Core business logic for KhataGuard operations."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from backend.database.customers import add_customer, get_all_customers
from backend.database.transactions import add_transaction


def create_customer(name: str, phone: Optional[str] = None) -> int:
    name = (name or "").strip()
    if not name:
        raise ValueError("Customer name is required.")
    return add_customer(name=name, phone=phone)


def list_customers() -> List[Dict[str, Any]]:
    return [dict(row) for row in get_all_customers()]


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

    # REMOVED: Rigid check 'paid_amount > sale_amount' deleted to allow debt clearance & advance payments.

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
