import streamlit as st
from backend.core import list_customers, get_customer_statement

st.set_page_config(page_title="Ledger - KhataGuard", page_icon="📒", layout="wide")
st.title("📒 Customer Ledger")
st.caption("Real database se customer ka complete hisaab.")
customers=[dict(x) for x in list_customers()]
if not customers: st.info("Pehle customer add karein."); st.stop()
ids={int(c['id']):c for c in customers}
default_id=st.session_state.get('selected_customer_id',next(iter(ids)))
if default_id not in ids: default_id=next(iter(ids))
selected_id=st.selectbox("Customer Chunain",list(ids),index=list(ids).index(default_id),format_func=lambda i: ids[i]['name'])
try:
    s=get_customer_statement(ids[selected_id]['name'])
    c1,c2,c3=st.columns(3)
    c1.metric("Total Sale",f"Rs. {sum(float(x['amount']) for x in s['ledger'] if x['type']=='sale'):,.2f}")
    c2.metric("Total Paid",f"Rs. {sum(float(x['amount']) for x in s['ledger'] if x['type']=='payment'):,.2f}")
    c3.metric("Outstanding",f"Rs. {float(s['balance']):,.2f}")
    st.subheader(f"📜 {s['customer_name']} ki Transaction History")
    rows=[dict(x) for x in s['ledger']]
    if rows: st.dataframe(rows,use_container_width=True,hide_index=True)
    else: st.info("Is customer ki abhi koi transaction nahi hai.")
except Exception as exc: st.error(f"Ledger load nahi hua: {exc}")
