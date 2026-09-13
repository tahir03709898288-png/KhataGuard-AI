"""Core business logic for KhataGuard operations with exact parameter alignment."""
from __future__ import annotations

import inspect
from datetime import date
from typing import Any, Dict, List, Optional

from backend.database.customers import add_customer, get_all_customers

# Safe Database Imports
try:
    from backend.database.transactions import add_transaction
except ImportError:
    add_transaction = None

try:
    from backend.database.transactions import get_all_transactions
except ImportError:
    get_all_transactions = None

try:
    from backend.database.transactions import get_transactions_by_customer
except ImportError:
    try:
        from backend.database.transactions import get_customer_transactions as get_transactions_by_customer
    except ImportError:
        get_transactions_by_customer = None


def create_customer(name: str, phone: Optional[str] = None) -> int:
    name = (name or "").strip()
    if not name:
        raise ValueError("Customer name is required.")
    return add_customer(name=name, phone=phone)


def list_customers() -> List[Dict[str, Any]]:
    return [dict(row) for row in get_all_customers()]


def _safe_add_transaction(
    customer_id: int,
    tx_type: str,
    amount: float,
    description: Optional[str] = None,
    transaction_date: Optional[str] = None,
) -> int:
    """Invokes add_transaction supporting transaction_type positional/keyword arguments."""
    if add_transaction is None:
        raise RuntimeError("Database add_transaction function not found.")

    sig = inspect.signature(add_transaction)
    params = sig.parameters

    # Case 1: If database function uses exact parameter name 'transaction_type'
    if "transaction_type" in params:
        kwargs = {
            "customer_id": customer_id,
            "transaction_type": tx_type,
            "amount": amount,
            "description": description,
            "transaction_date": transaction_date,
        }
        # Filter kwargs to only pass parameters accepted by add_transaction
        valid_kwargs = {k: v for k, v in kwargs.items() if k in params}
        return add_transaction(**valid_kwargs)

    # Case 2: Generic inspect fallback for legacy DB variants
    kwargs: Dict[str, Any] = {}
    if "customer_id" in params:
        kwargs["customer_id"] = customer_id
    elif "customer_name" in params:
        customers = list_customers()
        matched = [c for c in customers if c.get("id") == customer_id]
        if matched:
            kwargs["customer_name"] = matched[0]["name"]

    if "tx_type" in params:
        kwargs["tx_type"] = tx_type
    elif "type" in params:
        kwargs["type"] = tx_type

    if "amount" in params:
        kwargs["amount"] = amount
    if "description" in params:
        kwargs["description"] = description
    if "transaction_date" in params:
        kwargs["transaction_date"] = transaction_date
    elif "date" in params:
        kwargs["date"] = transaction_date

    try:
        return add_transaction(**kwargs)
    except TypeError:
        # Positional arguments fallback if keyword unpacking fails
        return add_transaction(customer_id, tx_type, amount, description, transaction_date)


def _fetch_customer_transactions(customer_id: int) -> List[Dict[str, Any]]:
    if get_transactions_by_customer is not None:
        try:
            return [dict(row) for row in get_transactions_by_customer(customer_id)]
        except Exception:
            pass
            
    if get_all_transactions is not None:
        try:
            all_txs = [dict(row) for row in get_all_transactions()]
            return [t for t in all_txs if t.get("customer_id") == customer_id]
        except Exception:
            pass
            
    return []


def get_customer_statement(customer_id: int) -> Dict[str, Any]:
    txs = _fetch_customer_transactions(customer_id)
    total_sale = 0.0
    total_paid = 0.0
    statement_rows = []
    running_balance = 0.0

    for tx in txs:
        tx_type = str(tx.get("transaction_type") or tx.get("tx_type") or tx.get("type") or "").lower()
        amount = float(tx.get("amount", 0.0))
        
        if tx_type == "sale":
            total_sale += amount
            running_balance += amount
        elif tx_type in ("payment", "paid"):
            total_paid += amount
            running_balance -= amount
            
        statement_rows.append({
            "id": tx.get("id"),
            "date": tx.get("transaction_date") or tx.get("date"),
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


def get_customers_for_ui(search: Optional[str] = None) -> List[Dict[str, Any]]:
    customers = list_customers()
    if search and search.strip():
        term = search.strip().casefold()
        customers = [c for c in customers if term in str(c.get("name", "")).casefold()]
    
    for c in customers:
        statement = get_customer_statement(c["id"])
        c["total_sale"] = statement.get("total_sale", 0.0)
        c["outstanding"] = statement.get("balance", 0.0)
    return customers


def get_customer_summaries() -> List[Dict[str, Any]]:
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
    sale_amount = float(sale_amount or 0.0)
    paid_amount = float(paid_amount or 0.0)

    if sale_amount <= 0:
        raise ValueError("Sale amount zero se barra hona chahiye.")
    if paid_amount < 0:
        raise ValueError("Paid amount negative nahi ho sakta.")

    t_date = transaction_date or date.today().isoformat()
    customers = list_customers()
    matched = [c for c in customers if str(c["name"]).strip().casefold() == customer_name.strip().casefold()]

    if not matched:
        customer_id = create_customer(name=customer_name)
    else:
        customer_id = matched[0]["id"]

    sale_id = _safe_add_transaction(
        customer_id=customer_id,
        tx_type="sale",
        amount=sale_amount,
        description=description,
        transaction_date=t_date,
    )

    payment_id = None
    if paid_amount > 0:
        payment_id = _safe_add_transaction(
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
    amount = float(amount or 0.0)
    if amount <= 0:
        raise ValueError("Payment amount zero se barra hona chahiye.")

    t_date = transaction_date or date.today().isoformat()
    customers = list_customers()
    matched = [c for c in customers if str(c["name"]).strip().casefold() == customer_name.strip().casefold()]

    if not matched:
        customer_id = create_customer(name=customer_name)
    else:
        customer_id = matched[0]["id"]

    payment_id = _safe_add_transaction(
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
