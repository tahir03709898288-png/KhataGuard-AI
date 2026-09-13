import streamlit as st
from backend.core import create_customer, get_customers_for_ui

st.set_page_config(page_title="Customers - KhataGuard", page_icon="🧑‍🤝‍🧑", layout="wide")
st.title("🧑‍🤝‍🧑 Customers")
st.caption("Real SQLite database se customers manage karein.")

with st.expander("➕ Nayi Customer Add Karein", expanded=False):
    with st.form("add_customer_form", clear_on_submit=True):
        c1,c2=st.columns(2)
        name=c1.text_input("Customer ka Naam")
        phone=c2.text_input("Phone Number (optional)")
        submitted=st.form_submit_button("Save Customer",use_container_width=True)
    if submitted:
        try:
            if not name.strip(): raise ValueError("Naam likhna zaroori hai.")
            cid=create_customer(name.strip(), phone.strip() or None)
            st.success(f"{name.strip()} add ho gaya/gayi. ID: {cid}")
            st.rerun()
        except Exception as exc: st.error(f"Customer save nahi hui: {exc}")

search=st.text_input("🔍 Customer Search karein")
try: df=get_customers_for_ui(search=search)
except Exception as exc: st.error(f"Database load nahi hua: {exc}"); st.stop()
if not df: st.info("Koi customer nahi mila.")
for row in df:
    with st.container(border=True):
        c1,c2,c3,c4=st.columns([2,1,1,1])
        c1.markdown(f"**{row['name']}**  \n📞 {row.get('phone') or '—'}")
        c2.metric("Sale",f"Rs. {float(row['total_sale']):,.0f}")
        c3.metric("Outstanding",f"Rs. {float(row['outstanding']):,.0f}")
        if c4.button("Ledger",key=f"cust_ledger_{row['id']}",use_container_width=True):
            st.session_state.selected_customer_id=int(row['id'])
            st.switch_page("pages/3_Ledger.py")
