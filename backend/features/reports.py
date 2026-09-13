"""Part 5: reports, analytics, reminders and export helpers.

Read-only calculations use existing Part 2 functions/data. This file never creates or alters a DB table.
"""
from __future__ import annotations

import csv
import io
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


DANGEROUS_CSV_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _row_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    try:
        return dict(row)
    except Exception:
        return {key: getattr(row, key) for key in dir(row) if not key.startswith("_")}


def _to_date(value: Any) -> date:
    text = str(value or "").strip()
    if not text:
        raise ValueError("Transaction date missing hai.")
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        return date.fromisoformat(text[:10])


def filter_transactions(
    transactions: Iterable[Any],
    *,
    customer_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    rows = []
    for raw in transactions:
        row = _row_dict(raw)
        if customer_id is not None and int(row["customer_id"]) != int(customer_id):
            continue
        tx_date = _to_date(row["transaction_date"])
        if start_date and tx_date < start_date:
            continue
        if end_date and tx_date > end_date:
            continue
        row["date"] = tx_date.isoformat()
        row["amount"] = float(row["amount"])
        rows.append(row)
    rows.sort(key=lambda item: (item["date"], int(item.get("id", 0))))
    return rows


def build_dashboard_metrics(
    customer_summaries: Iterable[dict[str, Any]],
    transactions: Iterable[Any],
) -> dict[str, Any]:
    summaries = [dict(item) for item in customer_summaries]
    tx_rows = [_row_dict(row) for row in transactions]
    total_sales = sum(float(r["amount"]) for r in tx_rows if r.get("type") == "sale")
    total_received = sum(float(r["amount"]) for r in tx_rows if r.get("type") == "payment")
    total_receivables = sum(max(0.0, float(c.get("outstanding", 0))) for c in summaries)
    active_ids = {int(r["customer_id"]) for r in tx_rows}
    recovery_rate = (total_received / total_sales * 100.0) if total_sales else 0.0
    return {
        "total_sales": total_sales,
        "total_received": total_received,
        "total_receivables": total_receivables,
        "active_customers": len(active_ids),
        "recovery_rate": recovery_rate,
    }


def build_customer_insights(
    customer_summaries: Iterable[dict[str, Any]],
    transactions: Iterable[Any],
    *,
    limit: int = 5,
) -> dict[str, Any]:
    summaries = [dict(item) for item in customer_summaries]
    tx_rows = [_row_dict(row) for row in transactions]
    counts = Counter(int(r["customer_id"]) for r in tx_rows)
    names = {int(c["id"]): c["name"] for c in summaries}

    top_debtors = sorted(
        (
            {
                "id": int(c["id"]),
                "name": c["name"],
                "phone": c.get("phone"),
                "outstanding": float(c.get("outstanding", 0)),
            }
            for c in summaries
            if float(c.get("outstanding", 0)) > 0
        ),
        key=lambda item: item["outstanding"],
        reverse=True,
    )[:limit]

    frequent = [
        {"id": customer_id, "name": names.get(customer_id, f"Customer {customer_id}"), "transactions": count}
        for customer_id, count in counts.most_common(limit)
    ]

    metrics = build_dashboard_metrics(summaries, tx_rows)
    return {
        "top_debtors": top_debtors,
        "most_frequent": frequent,
        "recovery_rate": metrics["recovery_rate"],
    }


def daily_sales_payments(transactions: Iterable[Any]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, float]] = defaultdict(lambda: {"sale": 0.0, "payment": 0.0})
    for raw in transactions:
        row = _row_dict(raw)
        day = _to_date(row["transaction_date"]).isoformat()
        tx_type = row.get("type")
        if tx_type in {"sale", "payment"}:
            grouped[day][tx_type] += float(row["amount"])
    return [
        {"date": day, "sales": amounts["sale"], "payments": amounts["payment"]}
        for day, amounts in sorted(grouped.items())
    ]


def reminder_messages(customer_name: str, balance: float) -> dict[str, str]:
    balance_text = f"Rs. {float(balance):,.2f}"
    english = (
        f"Assalam-o-Alaikum {customer_name}, this is a friendly KhataGuard reminder that "
        f"your outstanding balance is {balance_text}. Please make the payment when convenient. Thank you."
    )
    urdu = (
        f"Assalam-o-Alaikum {customer_name}, aap ke khatay mein {balance_text} baqi hain. "
        "Meherbani karke munasib waqt par payment kar dein. Shukriya."
    )
    return {"english": english, "urdu": urdu}


def normalize_whatsapp_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    raw = "".join(ch for ch in str(phone) if ch.isdigit() or ch == "+")
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = "92" + digits[1:]
    if not 7 <= len(digits) <= 15:
        return None
    return digits


def whatsapp_share_url(phone: str | None, message: str) -> str:
    digits = normalize_whatsapp_phone(phone)
    if digits:
        return f"https://wa.me/{digits}?text={quote(message)}"
    return f"https://wa.me/?text={quote(message)}"


def sms_share_url(phone: str | None, message: str) -> str | None:
    if not phone:
        return None
    digits = "".join(ch for ch in str(phone) if ch.isdigit() or ch == "+")
    if not digits:
        return None
    separator = "&" if "?" in digits else "?"
    return f"sms:{digits}{separator}body={quote(message)}"


def _csv_safe(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(DANGEROUS_CSV_PREFIXES):
        return "'" + value
    return value


def transactions_csv(transactions: Iterable[Any]) -> bytes:
    rows = [_row_dict(row) for row in transactions]
    output = io.StringIO()
    fields = ["id", "date", "customer_id", "customer_name", "type", "amount", "description"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        prepared = {
            "id": row.get("id"),
            "date": _to_date(row.get("transaction_date")).isoformat(),
            "customer_id": row.get("customer_id"),
            "customer_name": _csv_safe(row.get("customer_name", "")),
            "type": row.get("type"),
            "amount": float(row.get("amount", 0)),
            "description": _csv_safe(row.get("description") or ""),
        }
        writer.writerow(prepared)
    return output.getvalue().encode("utf-8-sig")


def backup_json(customers: Iterable[Any], transactions: Iterable[Any]) -> bytes:
    payload = {
        "format": "khataguard-part5-export-v1",
        "customers": [_row_dict(row) for row in customers],
        "transactions": [_row_dict(row) for row in transactions],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")


def statement_rows(
    transactions: Iterable[Any],
    *,
    opening_balance: float = 0.0,
) -> tuple[list[dict[str, Any]], float]:
    """Build statement rows starting from the balance before the selected range."""
    balance = float(opening_balance)
    rows: list[dict[str, Any]] = []
    for raw in transactions:
        row = _row_dict(raw)
        amount = float(row["amount"])
        if row.get("type") == "sale":
            debit, credit = amount, 0.0
            balance += amount
        elif row.get("type") == "payment":
            debit, credit = 0.0, amount
            balance -= amount
        else:
            continue
        rows.append({
            "date": _to_date(row["transaction_date"]).isoformat(),
            "description": row.get("description") or "",
            "debit": debit,
            "credit": credit,
            "balance": balance,
        })
    return rows, balance


def statement_csv(
    customer_name: str,
    transactions: Iterable[Any],
    *,
    opening_balance: float = 0.0,
) -> bytes:
    rows, _ = statement_rows(transactions, opening_balance=opening_balance)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["Date", "Customer", "Description", "Sale", "Payment", "Balance"])
    writer.writeheader()
    for row in rows:
        writer.writerow({
            "Date": row["date"],
            "Customer": _csv_safe(customer_name),
            "Description": _csv_safe(row["description"]),
            "Sale": row["debit"],
            "Payment": row["credit"],
            "Balance": row["balance"],
        })
    return output.getvalue().encode("utf-8-sig")


def _register_unicode_font() -> str:
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            name = "KhataGuardUnicode"
            try:
                pdfmetrics.getFont(name)
            except KeyError:
                pdfmetrics.registerFont(TTFont(name, str(path)))
            return name
    return "Helvetica"


def statement_pdf(
    *,
    customer_name: str,
    phone: str | None,
    transactions: Iterable[Any],
    start_date: date | None,
    end_date: date | None,
    opening_balance: float = 0.0,
) -> bytes:
    rows, closing = statement_rows(transactions, opening_balance=opening_balance)
    buffer = io.BytesIO()
    font = _register_unicode_font()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"KhataGuard Statement - {customer_name}",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "KGTitle", parent=styles["Title"], fontName=font, alignment=TA_CENTER, fontSize=16, leading=20
    )
    body_style = ParagraphStyle("KGBody", parent=styles["BodyText"], fontName=font, fontSize=9, leading=12)

    period = "All dates"
    if start_date or end_date:
        period = f"{start_date.isoformat() if start_date else 'Start'} to {end_date.isoformat() if end_date else 'Today'}"

    story = [
        Paragraph("KhataGuard Customer Statement", title_style),
        Spacer(1, 5 * mm),
        Paragraph(f"Customer: {customer_name}", body_style),
        Paragraph(f"Phone: {phone or '-'}", body_style),
        Paragraph(f"Period: {period}", body_style),
        Paragraph(f"Opening balance: Rs. {opening_balance:,.2f}", body_style),
        Spacer(1, 4 * mm),
    ]

    table_data = [["Date", "Description", "Sale", "Payment", "Balance"]]
    for row in rows:
        table_data.append([
            row["date"],
            str(row["description"])[:60],
            f"{row['debit']:,.2f}",
            f"{row['credit']:,.2f}",
            f"{row['balance']:,.2f}",
        ])
    if len(table_data) == 1:
        table_data.append(["-", "No transactions in selected range", "0.00", "0.00", "0.00"])

    table = Table(table_data, repeatRows=1, colWidths=[24*mm, 72*mm, 26*mm, 26*mm, 28*mm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF5F4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#16384A")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C9D8D7")),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
    ]))
    total_sales = sum(row["debit"] for row in rows)
    total_payments = sum(row["credit"] for row in rows)
    story.extend([
        table,
        Spacer(1, 5 * mm),
        Paragraph(f"Total sales in period: Rs. {total_sales:,.2f}", body_style),
        Paragraph(f"Total payments in period: Rs. {total_payments:,.2f}", body_style),
        Paragraph(f"Closing balance: Rs. {closing:,.2f}", body_style),
    ])
    doc.build(story)
    return buffer.getvalue()
