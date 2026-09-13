"""Compatibility helpers for saving confirmed Part 4 drafts.

The helper supports both KhataGuard core snapshots seen in the provided files:
- record_sale(customer_name=...)
- record_sale(customer_id=...)
No existing core/database code is modified.
"""
from __future__ import annotations

import inspect
from datetime import date
from typing import Any, Callable


class IntegrationError(RuntimeError):
    """User-safe exception for transaction integration failures."""


def _supports(function: Callable[..., Any], name: str) -> bool:
    return name in inspect.signature(function).parameters


def save_confirmed_transaction(
    *,
    customer_id: int,
    customer_name: str,
    sale: float,
    paid: float,
    transaction_date: date,
    description: str,
    record_sale: Callable[..., Any],
    record_payment: Callable[..., Any],
) -> Any:
    """Save transaction only after UI confirmation.
    
    Supports flexible payments where paid amount can be greater than sale amount
    to account for advance payments and old debt clearances.
    """
    try:
        sale = float(sale)
        paid = float(paid)
    except (TypeError, ValueError) as exc:
        raise IntegrationError("Amount numerical value honi chahiye.") from exc

    if sale < 0 or paid < 0:
        raise IntegrationError("Amounts negative nahi ho sakte.")
        
    if sale == 0 and paid == 0:
        raise IntegrationError("Sale ya payment mein se kam az kam ek amount zaroori hai.")

    # REMOVED: Rigid check 'if sale > 0 and paid > sale' eliminated to allow full ledger flexibility.

    shared = {
        "description": description or None,
        "transaction_date": transaction_date.isoformat() if hasattr(transaction_date, "isoformat") else str(transaction_date),
    }

    if sale > 0:
        kwargs = {"sale_amount": sale, "paid_amount": paid, **shared}
        if _supports(record_sale, "customer_id"):
            kwargs["customer_id"] = customer_id
        elif _supports(record_sale, "customer_name"):
            kwargs["customer_name"] = customer_name
        else:
            raise IntegrationError("record_sale customer identifier support nahi karta.")
        return record_sale(**kwargs)

    kwargs = {"amount": paid, **shared}
    if _supports(record_payment, "customer_id"):
        kwargs["customer_id"] = customer_id
    elif _supports(record_payment, "customer_name"):
        kwargs["customer_name"] = customer_name
    else:
        raise IntegrationError("record_payment customer identifier support nahi karta.")
    return record_payment(**kwargs)
