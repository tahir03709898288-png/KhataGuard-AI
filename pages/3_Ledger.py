import streamlit as st
from backend.core import list_customers, get_customer_statement

st.set_page_config(page_title="Ledger - KhataGuard", page_icon="📑", layout="wide")
st.title("📑 Customer Ledger")
st.caption("Real database se customer ka complete hisaab.")

customers = list_customers()

if not customers:
    st.info("Abhi koi customer database mein nahi hai.")
    st.stop()

# Customer options for selectbox
customer_options = {c["name"]: c["id"] for c in customers}

# Pre-select customer if navigated from Customers page
default_index = 0
if "selected_customer_id" in st.session_state:
    target_id = st.session_state.selected_customer_id
    for idx, (c_name, c_id) in enumerate(customer_options.items()):
        if c_id == target_id:
            default_index = idx
            break

selected_name = st.selectbox(
    "Customer Chunain",
    options=list(customer_options.keys()),
    index=default_index
)

selected_id = customer_options[selected_name]

try:
    stmt = get_customer_statement(selected_id)
except Exception as exc:
    st.error(f"Ledger load nahi hua: {exc}")
    st.stop()

# Metrics Row
col1, col2, col3 = st.columns(3)
col1.metric("Total Sale", f"Rs. {stmt.get('total_sale', 0.0):,.2f}")
col2.metric("Total Paid", f"Rs. {stmt.get('total_paid', 0.0):,.2f}")

balance = stmt.get('balance', 0.0)
balance_label = "Outstanding (Baqaya)" if balance >= 0 else "Advance Credit"
col3.metric(balance_label, f"Rs. {abs(balance):,.2f}")

st.divider()
st.subheader("Transaction History")

# Safely extract rows handling both 'transactions' and 'ledger' key names
tx_rows = stmt.get("transactions") or stmt.get("ledger") or stmt.get("statement") or []

if tx_rows:
    st.dataframe(tx_rows, use_container_width=True, hide_index=True)
else:
    st.info("Is customer ki koi transaction record nahi hui.")
