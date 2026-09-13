import streamlit as st
from backend.core import get_customer_summaries

st.set_page_config(page_title="KhataGuard", page_icon="📒", layout="wide")

st.title("📒 KhataGuard")
st.caption("AI-Powered Digital Khata — bolo, aur khata khud ban jaye.")

try:
    summaries = get_customer_summaries()
except Exception as exc:
    st.error(f"Data load nahi hua: {exc}")
    summaries = []

total_sales = sum(float(x.get("total_sale", 0.0)) for x in summaries)
total_paid = sum(float(x.get("total_paid", 0.0)) for x in summaries)

# Safely check both 'balance' and 'outstanding' keys to prevent KeyError
total_outstanding = sum(
    max(0.0, float(x.get("balance", x.get("outstanding", 0.0))))
    for x in summaries
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Sales", f"Rs. {total_sales:,.2f}")
col2.metric("Total Payments", f"Rs. {total_paid:,.2f}")
col3.metric("Total Outstanding", f"Rs. {total_outstanding:,.2f}")
col4.metric("Total Customers", len(summaries))

st.divider()

st.markdown("""
### 🚀 Welcome to KhataGuard AI
Side menu se aap niche diye gaye features use kar sakte hain:
* **🧑‍🤝‍🧑 Customers:** Naye customer add karein aur unka hisaab dekhein.
* **💳 Transactions:** Manual sale ya payment record karein.
* **📑 Ledger:** Kisi bhi customer ka mukammal khata statement dekhein.
* **🎙️ Voice Image:** Aawaz (Urdu/English) ya handwriting image se auto transaction save karein.
* **📊 Reports:** Business metrics aur visual analytics dekhein.
""")
