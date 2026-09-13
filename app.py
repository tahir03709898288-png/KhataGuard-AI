"""KhataGuard integrated Part 1-5 Streamlit application."""
import streamlit as st
import plotly.express as px
from backend.database.database import initialize_database
from backend.core import get_customer_summaries

initialize_database()
st.set_page_config(page_title="KhataGuard", page_icon="📒", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>.block-container{padding-top:1.5rem;padding-bottom:2rem}div[data-testid="stMetric"]{border:1px solid rgba(128,128,128,.3);border-radius:12px;padding:14px}.stButton button{border-radius:10px;height:3em;font-size:1rem}</style>""", unsafe_allow_html=True)

st.title("📒 KhataGuard")
st.caption("AI-Powered Digital Khata — bolo, aur khata khud ban jaye.")

summaries = [dict(x) for x in get_customer_summaries()]
total_sale = sum(float(x["total_sale"]) for x in summaries)
total_paid = sum(float(x["total_paid"]) for x in summaries)
total_outstanding = sum(max(0.0, float(x["outstanding"])) for x in summaries)

c1,c2,c3,c4=st.columns(4)
c1.metric("Total Sale", f"Rs. {total_sale:,.2f}")
c2.metric("Total Received", f"Rs. {total_paid:,.2f}")
c3.metric("Total Outstanding", f"Rs. {total_outstanding:,.2f}")
c4.metric("Active Customers", f"{len(summaries)}")
st.divider()

st.subheader("Quick Actions")
a1,a2,a3,a4,a5=st.columns(5)
if a1.button("➕ Customers", use_container_width=True): st.switch_page("pages/1_Customers.py")
if a2.button("💰 Transactions", use_container_width=True): st.switch_page("pages/2_Transactions.py")
if a3.button("📒 Ledger", use_container_width=True): st.switch_page("pages/3_Ledger.py")
if a4.button("🎙️ Voice / Image", use_container_width=True): st.switch_page("pages/4_Voice_Image.py")
if a5.button("📊 Reports", use_container_width=True): st.switch_page("pages/5_Reports.py")

st.divider()
if summaries:
    st.subheader("Top Outstanding Customers")
    top = sorted(summaries, key=lambda x: float(x["outstanding"]), reverse=True)[:5]
    top = [x for x in top if float(x["outstanding"]) > 0]
    if top:
        fig=px.bar(top,x="name",y="outstanding",text="outstanding",labels={"name":"Customer","outstanding":"Outstanding (Rs.)"})
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig,use_container_width=True)
    else:
        st.success("Abhi koi positive outstanding balance nahi hai.")
else:
    st.info("Abhi database mein customer nahi hain. Customers page se pehla customer add karein.")
