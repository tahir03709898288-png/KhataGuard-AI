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
    pass


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
    """Save only after UI confirmation; never called during OCR/transcription."""
    sale = float(sale)
    paid = float(paid)
    if sale < 0 or paid < 0 or (sale == 0 and paid == 0):
        raise IntegrationError("Sale/payment amounts invalid hain.")
    if sale > 0 and paid > sale:
        raise IntegrationError("Paid new sale se zyada nahi ho sakta.")

    shared = {
        "description": description or None,
        "transaction_date": transaction_date.isoformat(),
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
