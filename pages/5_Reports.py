from __future__ import annotations

from datetime import date

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from backend.core import get_customer_summaries, list_customers
from backend.database.transactions import get_all_transactions
from backend.features.reports import (
    backup_json,
    build_customer_insights,
    build_dashboard_metrics,
    daily_sales_payments,
    filter_transactions,
    reminder_messages,
    sms_share_url,
    statement_csv,
    statement_pdf,
    transactions_csv,
    whatsapp_share_url,
)


st.set_page_config(page_title="Reports - KhataGuard", page_icon="📊", layout="wide")
st.title("📊 Part 5 — Reports & Business Features")
st.caption("All analytics are calculated from the existing KhataGuard database. No schema changes are made.")

try:
    customers = [dict(row) for row in list_customers()]
    summaries = [dict(row) for row in get_customer_summaries()]
    transactions = [dict(row) for row in get_all_transactions()]
except Exception as exc:
    st.error(f"Database data load nahi hua: {exc}")
    st.stop()

metrics = build_dashboard_metrics(summaries, transactions)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Sales", f"Rs. {metrics['total_sales']:,.2f}")
k2.metric("Payments Received", f"Rs. {metrics['total_received']:,.2f}")
k3.metric("Outstanding Receivables", f"Rs. {metrics['total_receivables']:,.2f}")
k4.metric("Active Customers", f"{metrics['active_customers']}")

st.divider()
st.subheader("Interactive Charts")

left, right = st.columns(2)
with left:
    comparison = {
        "Category": ["Sales", "Payments"],
        "Amount": [metrics["total_sales"], metrics["total_received"]],
    }
    st.plotly_chart(px.bar(comparison, x="Category", y="Amount", title="Sales vs Payments"), use_container_width=True)

with right:
    debtors = [s for s in summaries if float(s.get("outstanding", 0)) > 0]
    if debtors:
        fig = px.pie(
            debtors,
            names="name",
            values="outstanding",
            hole=0.52,
            title="Customer Debt Proportion",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Positive outstanding balance wala customer nahi hai.")

daily = daily_sales_payments(transactions)
if daily:
    line = go.Figure()
    line.add_trace(go.Scatter(x=[r["date"] for r in daily], y=[r["sales"] for r in daily], mode="lines+markers", name="Sales"))
    line.add_trace(go.Scatter(x=[r["date"] for r in daily], y=[r["payments"] for r in daily], mode="lines+markers", name="Payments"))
    line.update_layout(title="Daily Sales & Payments", xaxis_title="Date", yaxis_title="PKR")
    st.plotly_chart(line, use_container_width=True)

st.divider()
st.subheader("Customer Insights")
insights = build_customer_insights(summaries, transactions)
st.metric("Recovery Rate", f"{insights['recovery_rate']:.1f}%")

c1, c2 = st.columns(2)
with c1:
    st.write("**Top Debtors**")
    if insights["top_debtors"]:
        st.dataframe(insights["top_debtors"], use_container_width=True, hide_index=True)
    else:
        st.info("No outstanding debtors.")
with c2:
    st.write("**Most Frequent Customers**")
    if insights["most_frequent"]:
        st.dataframe(insights["most_frequent"], use_container_width=True, hide_index=True)
    else:
        st.info("No transactions yet.")

st.divider()
st.subheader("Payment Reminders — WhatsApp / SMS")
st.caption("Current database mein due-date field nahi hai, isliye positive balance ko reminder-eligible maana gaya hai.")

summary_by_id = {int(s["id"]): s for s in summaries}
overdue = [s for s in summaries if float(s.get("outstanding", 0)) > 0]
if not overdue:
    st.success("Kisi customer ka positive outstanding balance nahi hai.")
else:
    selected_id = st.selectbox(
        "Customer",
        [int(s["id"]) for s in overdue],
        format_func=lambda cid: f"{summary_by_id[cid]['name']} — Rs. {float(summary_by_id[cid]['outstanding']):,.2f}",
    )
    selected = summary_by_id[selected_id]
    messages = reminder_messages(selected["name"], selected["outstanding"])
    language = st.radio("Message", ["Urdu / Roman Urdu", "English"], horizontal=True)
    message = messages["urdu"] if language.startswith("Urdu") else messages["english"]
    edited_message = st.text_area("Reminder message", value=message, height=110)
    w1, w2 = st.columns(2)
    w1.link_button("Open WhatsApp", whatsapp_share_url(selected.get("phone"), edited_message), use_container_width=True)
    sms_url = sms_share_url(selected.get("phone"), edited_message)
    if sms_url:
        w2.link_button("Open SMS", sms_url, use_container_width=True)
    else:
        w2.button("SMS unavailable — no phone", disabled=True, use_container_width=True)

st.divider()
st.subheader("Customer Statement / Date Range Export")

if not customers:
    st.info("Statement ke liye pehle customer add karein.")
else:
    customer_map = {int(c["id"]): c for c in customers}
    selected_customer_id = st.selectbox(
        "Statement customer",
        list(customer_map),
        format_func=lambda cid: customer_map[cid]["name"],
        key="report_customer",
    )
    d1, d2 = st.columns(2)
    start = d1.date_input("From date", value=date(date.today().year, 1, 1))
    end = d2.date_input("To date", value=date.today())

    if start > end:
        st.error("From date, To date se baad nahi ho sakti.")
    else:
        all_customer_transactions = filter_transactions(
            transactions,
            customer_id=selected_customer_id,
        )
        opening_balance = sum(
            (row["amount"] if row["type"] == "sale" else -row["amount"])
            for row in all_customer_transactions
            if row["date"] < start.isoformat()
        )
        filtered = filter_transactions(
            transactions,
            customer_id=selected_customer_id,
            start_date=start,
            end_date=end,
        )
        preview = [
            {
                "Date": row["date"],
                "Type": row["type"],
                "Amount": row["amount"],
                "Description": row.get("description") or "",
            }
            for row in filtered
        ]
        st.dataframe(preview, use_container_width=True, hide_index=True)

        customer = customer_map[selected_customer_id]
        filename_base = "".join(ch if ch.isalnum() else "_" for ch in customer["name"]).strip("_") or f"customer_{selected_customer_id}"
        e1, e2 = st.columns(2)
        e1.download_button(
            "Download Customer CSV",
            data=statement_csv(customer["name"], filtered, opening_balance=opening_balance),
            file_name=f"{filename_base}_statement.csv",
            mime="text/csv",
            use_container_width=True,
        )
        e2.download_button(
            "Download Customer PDF",
            data=statement_pdf(
                customer_name=customer["name"],
                phone=customer.get("phone"),
                transactions=filtered,
                start_date=start,
                end_date=end,
                opening_balance=opening_balance,
            ),
            file_name=f"{filename_base}_statement.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

st.divider()
st.subheader("Full Backup / Export")
b1, b2 = st.columns(2)
b1.download_button(
    "Download Full JSON Backup",
    data=backup_json(customers, transactions),
    file_name="khataguard-full-export.json",
    mime="application/json",
    use_container_width=True,
)
b2.download_button(
    "Download Full CSV Export",
    data=transactions_csv(transactions),
    file_name="khataguard-transactions.csv",
    mime="text/csv",
    use_container_width=True,
)
