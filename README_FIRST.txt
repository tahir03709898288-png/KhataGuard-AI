KHATAGUARD FINAL - SAFE PATCH

This version keeps the existing KhataGuard UI, database backend, Part 3 parser,
Voice/Image flow, and Reports unchanged in behavior, while fixing Groq token-limit
issues and making Voice/Image API errors explicit.

IMPORTANT DATA NOTE:
- Your existing khata.db is intentionally NOT included in this patch ZIP.
- Do NOT delete or replace your current khata.db if it already contains another
  candidate's entered data.
- Extract/replace the project files in the SAME project folder and leave khata.db
  where it is. The app will continue using that database.
- If you move the code to a new folder, copy your existing khata.db into that
  folder before running the app.

Groq settings:
- GROQ_MODEL = openai/gpt-oss-20b
- GROQ_SPEECH_MODEL = whisper-large-v3-turbo
- GROQ_VISION_MODEL = qwen/qwen3.6-27b

The Vision request now stays below the 1,000-token output limit seen in the
current Groq account response. The Part 3 parser is also capped below 1,000 so
voice/image parsing does not hit the same class of error.

Run:
  py -m pip install -r requirements.txt
  py -m streamlit run app.py
