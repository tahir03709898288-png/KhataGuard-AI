# 📒 KhataGuard-AI

**AI-Powered Digital Khata — Bolo, aur khata khud ban jaye.**

KhataGuard-AI is an intelligent, voice-enabled, multi-lingual financial ledger management application tailored for small business owners and merchants. It simplifies daily bookkeeping by allowing natural language input in Urdu, Hindi, Roman Urdu, and English via text, voice, and visual inputs.

---

## 🚀 Product Requirement Document (PRD) Overview

### 1. Core Objectives
* **Eliminate Manual Bookkeeping Errors:** Streamline transaction entries using automated AI parsing.
* **Multi-Lingual Voice Support:** Extract financial parameters from Urdu, Hindi, Roman Urdu, and English spoken inputs.
* **Flexible Accounting Logic:** Fully support debt clearances and advance payments (allowing payments to exceed current sale amounts).
* **Smart Identity Preservation:** Case-insensitive and script-normalized customer lookup to prevent duplicate accounts (e.g., merging "ALi" and "علی").

### 2. Key Features
* **🎙️ Voice & Image Input:** Real-time speech-to-ledger extraction powered by Groq OpenAI-compatible LLM endpoints.
* **💳 Dynamic Transaction Management:** Record sales and payments with auto-deducting running balances.
* **📑 Interactive Customer Ledger:** View itemized transaction histories, total sales, payments, and outstanding/advance balances per customer.
* **📊 Business Reports:** Analytics overview showing aggregate receivables, sales metrics, and total active merchant customers.

### 3. Technical Architecture
* **Frontend:** Streamlit Framework (`app.py`, `pages/`)
* **Core Logic:** Python with dynamic signature routing (`backend/core.py`, `backend/features/integration.py`)
* **Database Layer:** SQLite relational database engine (`backend/database`)
* **AI Parsing:** Groq API (`openai/gpt-oss-20b` / `llama-3.3-70b-versatile`)

---

## 🛠️ Live Links

* **Live Application:** [KhataGuard-AI Streamlit App](https://khataguard-ai-ecnadtvyq8c2rkywmdv6wv.streamlit.app/)
* **Repository:** [GitHub Source Code](https://github.com/tahir03709898288-png/KhataGuard-AI)
