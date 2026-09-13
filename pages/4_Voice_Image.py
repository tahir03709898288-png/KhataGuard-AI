from __future__ import annotations

import os
from datetime import date

import streamlit as st

from backend.core import create_customer, list_customers, record_payment, record_sale
from backend.features.integration import save_confirmed_transaction
from backend.features.media import (
    DEFAULT_SPEECH_MODEL,
    DEFAULT_VISION_MODEL,
    MediaProcessingError,
    ocr_handwritten_image,
    parse_with_existing_ai,
    transcribe_audio,
)

try:
    from backend.ai.parser import parse_transaction
except Exception:
    parse_transaction = None


st.set_page_config(page_title="Voice & Image - KhataGuard", page_icon="🎙️", layout="wide")
st.title("🎙️ Part 4 — Voice & Image")
st.caption("Voice/image is converted into a draft first. Nothing is saved until you confirm it.")


def setting(name: str, default: str = "") -> str:
    try:
        return st.secrets.get(name) or os.getenv(name) or default
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return os.getenv(name) or default


def set_draft(source_text: str, source_kind: str) -> None:
    if parse_transaction is None:
        raise MediaProcessingError(
            "backend.ai.parser.parse_transaction nahi mila. Part 3 parser ko project mein same path par rakhein."
        )
    result = parse_with_existing_ai(
        text=source_text,
        parser=parse_transaction,
        api_key=setting("GROQ_API_KEY"),
        text_model=setting("GROQ_MODEL", "llama-3.3-70b-versatile"),
    )
    st.session_state["p4_draft"] = {
        "customer": result.customer,
        "sale": result.sale,
        "paid": result.paid,
        "date": date.today(),
        "source_text": source_text,
        "source_kind": source_kind,
    }


def exact_customer(name: str):
    matches = [
        c for c in list_customers()
        if str(c["name"]).strip().casefold() == name.strip().casefold()
    ]
    if len(matches) > 1:
        raise ValueError("Is naam ke multiple customers hain. Customers page mein unique name use karein.")
    return matches[0] if matches else None


api_key = setting("GROQ_API_KEY")
if not api_key:
    st.warning("Streamlit Secrets mein GROQ_API_KEY add karein. Manual database data ko yeh page change nahi karta.")

voice_tab, image_tab = st.tabs(["🎤 Voice", "🖼️ Handwritten Image"])

with voice_tab:
    st.subheader("Voice → Text → Existing AI Parser")
    language_label = st.selectbox("Voice language", ["Auto", "Urdu", "English"], key="p4_lang")
    language = {"Auto": None, "Urdu": "ur", "English": "en"}[language_label]

    live_audio = st.audio_input("Record transaction", key="p4_live_audio")
    uploaded_audio = st.file_uploader(
        "Or upload audio",
        type=["wav", "mp3", "m4a"],
        key="p4_audio_upload",
    )

    left, right = st.columns(2)
    with left:
        if st.button("Process live recording", use_container_width=True, disabled=live_audio is None or not api_key):
            try:
                with st.spinner("Voice transcribe aur parse ho rahi hai..."):
                    text = transcribe_audio(
                        audio_bytes=live_audio.getvalue(),
                        filename="recording.wav",
                        api_key=api_key,
                        speech_model=setting("GROQ_SPEECH_MODEL", DEFAULT_SPEECH_MODEL),
                        language=language,
                    )
                    st.session_state["p4_transcript"] = text
                    set_draft(text, "voice")
                st.success("Draft ready hai. Neeche verify karein.")
            except Exception as exc:
                st.error(str(exc))

    with right:
        if st.button("Process uploaded audio", use_container_width=True, disabled=uploaded_audio is None or not api_key):
            try:
                with st.spinner("Uploaded audio transcribe aur parse ho rahi hai..."):
                    text = transcribe_audio(
                        audio_bytes=uploaded_audio.getvalue(),
                        filename=uploaded_audio.name,
                        api_key=api_key,
                        speech_model=setting("GROQ_SPEECH_MODEL", DEFAULT_SPEECH_MODEL),
                        language=language,
                    )
                    st.session_state["p4_transcript"] = text
                    set_draft(text, "voice_upload")
                st.success("Draft ready hai. Neeche verify karein.")
            except Exception as exc:
                st.error(str(exc))

    st.text_area(
        "Transcript (read-only preview)",
        value=st.session_state.get("p4_transcript", ""),
        height=110,
        disabled=True,
    )

with image_tab:
    st.subheader("Handwritten Khata Image → OCR → Existing AI Parser")
    st.caption("Vision model sirf image ko text mein read karta hai; transaction rules Part 3 parser hi apply karta hai.")
    image = st.file_uploader("Upload ledger image", type=["png", "jpg", "jpeg"], key="p4_image")
    if image is not None:
        st.image(image, caption="Uploaded ledger page", width=500)
    if st.button("Read & understand image", use_container_width=True, disabled=image is None or not api_key):
        try:
            with st.spinner("Handwriting read aur transaction parse ho rahi hai..."):
                ocr_text = ocr_handwritten_image(
                    image_bytes=image.getvalue(),
                    filename=image.name,
                    api_key=api_key,
                    vision_model=setting("GROQ_VISION_MODEL", DEFAULT_VISION_MODEL),
                )
                st.session_state["p4_ocr_text"] = ocr_text
                set_draft(ocr_text, "image")
            st.success("Image draft ready hai. Neeche verify karein.")
        except Exception as exc:
            st.error(str(exc))

    st.text_area(
        "OCR text (read-only preview)",
        value=st.session_state.get("p4_transcript", st.session_state.get("p4_ocr_text", "")),
        height=120,
        disabled=True,
    )

st.divider()
st.subheader("✅ Verify before saving")

draft = st.session_state.get("p4_draft")
if not draft:
    st.info("Voice ya image process karne ke baad editable draft yahan appear hoga.")
else:
    st.caption(f"Source: {draft['source_kind']}. Save se pehle har field check karein.")
    with st.form("p4_review_form"):
        customer_name = st.text_input("Customer name", value=draft["customer"])
        c1, c2 = st.columns(2)
        sale = c1.number_input("Sale (Rs.)", min_value=0.0, value=float(draft["sale"]), step=100.0)
        paid = c2.number_input("Paid / Received (Rs.)", min_value=0.0, value=float(draft["paid"]), step=100.0)
        tx_date = st.date_input("Transaction date", value=draft["date"])
        note = st.text_input("Description / note", value=draft["source_text"][:250])
        save = st.form_submit_button("Confirm & Save Transaction", use_container_width=True)

    if save:
        try:
            name = customer_name.strip()
            if not name:
                raise ValueError("Customer name required hai.")
            customer = exact_customer(name)
            if customer is None:
                customer_id = create_customer(name=name)
                customer = {"id": customer_id, "name": name}
            saved = save_confirmed_transaction(
                customer_id=int(customer["id"]),
                customer_name=str(customer["name"]),
                sale=sale,
                paid=paid,
                transaction_date=tx_date,
                description=note,
                record_sale=record_sale,
                record_payment=record_payment,
            )
            # Clear state to prevent duplicates and refresh state UI
            st.session_state.pop("p4_draft", None)
            st.session_state.pop("p4_transcript", None)
            st.session_state.pop("p4_ocr_text", None)
            st.success("Transaction database mein save ho gayi.")
            st.rerun()
        except Exception as exc:
            st.error(f"Save nahi hui: {exc}")
