# KhataGuard — Mobile Testing (Google Colab)

This package is a self-contained mobile-test copy of the final KhataGuard project.
It contains a CLEAN demo `khata.db` with 5 customers and 20 transactions.

## Important
- This `khata.db` is demo-only. Do NOT replace your team's real database with it.
- Voice/Image AI requires a valid Groq API key. Do not commit or upload your API key.
- The app can still be opened and the manual customer/transaction/ledger/report features can be tested without a Groq key.

## Fastest mobile method
1. Open Google Colab in your phone browser.
2. Upload `KhataGuard_Mobile_Test.zip` or upload the project files.
3. Install requirements.
4. Start Streamlit on port 8501.
5. Expose port 8501 with LocalTunnel.
6. Open the generated HTTPS URL in your phone browser.

The accompanying notebook `KhataGuard_Mobile_Test.ipynb` automates these steps.

## Groq key for Voice/Image
If you want to test Voice/Image:
- In Google Colab, use the Secrets panel and create a secret named `GROQ_API_KEY`.
- The notebook reads it without putting the key in the source code.
- Never paste the real key into a public notebook or GitHub repository.
