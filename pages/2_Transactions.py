import streamlit as st
from datetime import date
from backend.core import list_customers, record_sale, record_payment
from backend.database.transactions import get_all_transactions

st.set_page_config(page_title="Transactions - KhataGuard", page_icon="💰", layout="wide")
st.title("💰 Transactions")
st.caption("Manual entry bhi available hai; AI voice/image entry Part 4 mein hai.")

customers=[dict(x) for x in list_customers()]
if not customers:
    st.warning("Pehle Customers page se customer add karein.")
else:
    options={int(c['id']):c for c in customers}
    selected_id=st.selectbox("Customer",list(options),format_func=lambda i: options[i]['name'])
    c=options[selected_id]
    with st.form("manual_transaction"):
        a,b=st.columns(2)
        sale=a.number_input("New Sale (Rs.)",min_value=0.0,step=100.0)
        paid=b.number_input("Payment Received (Rs.)",min_value=0.0,step=100.0)
        tx_date=st.date_input("Transaction date",value=date.today())
        note=st.text_input("Note (optional)")
        save=st.form_submit_button("Save Transaction",use_container_width=True)
    if save:
        try:
            if sale <= 0 and paid <= 0: raise ValueError("Sale ya payment mein se kam az kam ek amount enter karein.")
            if sale > 0:
                if paid > sale: raise ValueError("Paid amount sale se zyada nahi ho sakta.")
                result=record_sale(c['name'],sale,paid,note,tx_date.isoformat())
            else:
                result=record_payment(c['name'],paid,note,tx_date.isoformat())
            st.success("Transaction save ho gayi.")
            st.json(result)
            st.rerun()
        except Exception as exc: st.error(f"Save nahi hui: {exc}")

st.divider(); st.subheader("📋 Saari Transactions")
rows=[dict(x) for x in get_all_transactions()]
if rows: st.dataframe(rows,use_container_width=True,hide_index=True)
else: st.info("Abhi koi transaction nahi hai.")
