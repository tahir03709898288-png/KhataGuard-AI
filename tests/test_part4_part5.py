from __future__ import annotations

import io
import json
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

# Run these tests from a project root where backend/ exists.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.features import media
from backend.features.integration import IntegrationError, save_confirmed_transaction
from backend.features.reports import (
    backup_json,
    build_customer_insights,
    build_dashboard_metrics,
    daily_sales_payments,
    filter_transactions,
    normalize_whatsapp_phone,
    reminder_messages,
    statement_csv,
    statement_pdf,
    transactions_csv,
    whatsapp_share_url,
)


def tiny_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(buf, format="PNG")
    return buf.getvalue()


def test_audio_validation():
    media.validate_audio(b"RIFF" + b"0" * 100, "voice.wav")
    with pytest.raises(media.MediaProcessingError):
        media.validate_audio(b"abc", "voice.exe")


def test_image_validation_rejects_fake_image():
    with pytest.raises(media.MediaProcessingError):
        media.validate_image(b"not an image", "ledger.jpg")
    assert media.validate_image(tiny_png(), "ledger.png") == "image/png"


def test_existing_parser_pipeline_preserves_parser_as_dependency():
    calls = {}

    def fake_parser(text, api_key=None, model=None):
        calls.update(text=text, api_key=api_key, model=model)
        return {
            "customer": "Ahmed",
            "sale": 5000,
            "paid": 2000,
            "needs_clarification": False,
            "question": "",
        }

    result = media.parse_with_existing_ai(
        text="Ahmed ne 5000 ka saman liya aur 2000 diye",
        parser=fake_parser,
        api_key="test-key",
        text_model="existing-model",
    )
    assert result.as_dict() == {"customer": "Ahmed", "sale": 5000.0, "paid": 2000.0}
    assert calls["model"] == "existing-model"


def test_transcription_api_contract_is_direct_groq(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        def json(self):
            return {"text": "Ali ne 1000 ka saman liya"}

    def fake_post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return FakeResponse()

    monkeypatch.setattr(media.requests, "post", fake_post)
    text = media.transcribe_audio(
        audio_bytes=b"RIFF" + b"0" * 100,
        filename="recording.wav",
        api_key="x",
    )
    assert text.startswith("Ali")
    assert captured["url"].endswith("/audio/transcriptions")
    assert captured["data"]["model"] == "whisper-large-v3-turbo"
    assert captured["files"]["file"][0] == "recording.wav"


def test_transcription_rate_limit_error_is_exposed(monkeypatch):
    class FakeResponse:
        status_code = 429
        text = ""
        def json(self):
            return {"error": {"message": "too many requests"}}

    monkeypatch.setattr(media.requests, "post", lambda *a, **k: FakeResponse())
    with pytest.raises(media.MediaProcessingError, match="429"):
        media.transcribe_audio(audio_bytes=b"RIFF" + b"0" * 100, filename="recording.wav", api_key="x")


def test_vision_api_contract_and_ocr_text(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        def json(self):
            return {"choices": [{"message": {"content": "Ahmed 5000 sale, 2000 paid"}}]}

    def fake_post(url, **kwargs):
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(media.requests, "post", fake_post)
    text = media.ocr_handwritten_image(
        image_bytes=tiny_png(), filename="khata.png", api_key="x"
    )
    assert "Ahmed" in text
    assert captured["json"]["model"] == "qwen/qwen3.6-27b"
    user_content = captured["json"]["messages"][1]["content"]
    assert user_content[1]["type"] == "image_url"
    assert user_content[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert captured["json"]["max_completion_tokens"] <= 1000


def test_save_compatibility_old_customer_name_signature():
    calls = {}

    def old_sale(customer_name, sale_amount, paid_amount=0, description=None, transaction_date=None):
        calls.update(locals())
        return {"ok": True}

    def old_payment(customer_name, amount, description=None, transaction_date=None):
        calls.update(locals())
        return {"ok": True}

    result = save_confirmed_transaction(
        customer_id=9,
        customer_name="Ahmed",
        sale=5000,
        paid=2000,
        transaction_date=date(2026, 9, 12),
        description="voice",
        record_sale=old_sale,
        record_payment=old_payment,
    )
    assert result["ok"] is True
    assert calls["customer_name"] == "Ahmed"
    assert calls["transaction_date"] == "2026-09-12"


def test_save_compatibility_new_customer_id_signature():
    calls = {}

    def new_sale(customer_id, sale_amount, paid_amount=0, description=None, transaction_date=None):
        calls.update(locals())
        return {"ok": True}

    def new_payment(customer_id, amount, description=None, transaction_date=None):
        calls.update(locals())
        return {"ok": True}

    save_confirmed_transaction(
        customer_id=9,
        customer_name="Ahmed",
        sale=0,
        paid=1000,
        transaction_date=date(2026, 9, 12),
        description="payment",
        record_sale=new_sale,
        record_payment=new_payment,
    )
    assert calls["customer_id"] == 9
    assert calls["amount"] == 1000


def sample_data():
    summaries = [
        {"id": 1, "name": "Ahmed", "phone": "03001234567", "total_sale": 5000, "total_paid": 2000, "outstanding": 3000},
        {"id": 2, "name": "Ali", "phone": None, "total_sale": 4000, "total_paid": 4000, "outstanding": 0},
    ]
    transactions = [
        {"id": 1, "customer_id": 1, "customer_name": "Ahmed", "type": "sale", "amount": 5000, "description": "Goods", "transaction_date": "2026-09-01 10:00:00"},
        {"id": 2, "customer_id": 1, "customer_name": "Ahmed", "type": "payment", "amount": 2000, "description": "Cash", "transaction_date": "2026-09-02 10:00:00"},
        {"id": 3, "customer_id": 2, "customer_name": "Ali", "type": "sale", "amount": 4000, "description": "Goods", "transaction_date": "2026-09-02 11:00:00"},
        {"id": 4, "customer_id": 2, "customer_name": "Ali", "type": "payment", "amount": 4000, "description": "Cash", "transaction_date": "2026-09-03 11:00:00"},
    ]
    return summaries, transactions


def test_reports_metrics_insights_and_daily():
    summaries, tx = sample_data()
    metrics = build_dashboard_metrics(summaries, tx)
    assert metrics == {
        "total_sales": 9000.0,
        "total_received": 6000.0,
        "total_receivables": 3000.0,
        "active_customers": 2,
        "recovery_rate": pytest.approx(66.6666666667),
    }
    insights = build_customer_insights(summaries, tx)
    assert insights["top_debtors"][0]["name"] == "Ahmed"
    assert insights["most_frequent"][0]["transactions"] == 2
    assert len(daily_sales_payments(tx)) == 3


def test_filter_exports_pdf_and_csv():
    summaries, tx = sample_data()
    filtered = filter_transactions(
        tx,
        customer_id=1,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 30),
    )
    assert len(filtered) == 2
    csv_bytes = statement_csv("Ahmed", filtered)
    assert b"Ahmed" in csv_bytes
    pdf_bytes = statement_pdf(
        customer_name="Ahmed",
        phone="03001234567",
        transactions=filtered,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 30),
    )
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000
    assert b"customer_name" in transactions_csv(tx)
    payload = json.loads(backup_json(summaries, tx).decode("utf-8"))
    assert payload["format"] == "khataguard-part5-export-v1"
    assert len(payload["transactions"]) == 4


def test_reminders_and_whatsapp():
    messages = reminder_messages("Ahmed", 3000)
    assert "3,000.00" in messages["english"]
    assert "3,000.00" in messages["urdu"]
    assert normalize_whatsapp_phone("0300-1234567") == "923001234567"
    assert whatsapp_share_url("0300-1234567", "Hello").startswith("https://wa.me/923001234567")


def test_media_limits_stay_within_free_output_token_cap():
    source = (PROJECT_ROOT / "backend" / "features" / "media.py").read_text()
    parser = (PROJECT_ROOT / "backend" / "ai" / "parser.py").read_text()
    assert '"max_completion_tokens": 800' in source
    assert "max_completion_tokens=700" in parser


def test_statement_rows_preserves_opening_balance_for_date_range():
    from backend.features.reports import statement_rows

    tx = [
        {"id": 1, "customer_id": 1, "type": "sale", "amount": 5000, "description": "Earlier sale", "transaction_date": "2026-08-01 10:00:00"},
        {"id": 2, "customer_id": 1, "type": "payment", "amount": 1000, "description": "Earlier payment", "transaction_date": "2026-08-02 10:00:00"},
        {"id": 3, "customer_id": 1, "type": "sale", "amount": 2000, "description": "Current sale", "transaction_date": "2026-09-01 10:00:00"},
    ]
    rows, closing = statement_rows(
        tx[2:],
        opening_balance=4000,
    )
    assert rows[0]["balance"] == 6000
    assert closing == 6000


def test_statement_csv_accepts_opening_balance():
    tx = [{
        "id": 1,
        "customer_id": 1,
        "type": "sale",
        "amount": 2000,
        "description": "Current sale",
        "transaction_date": "2026-09-01 10:00:00",
    }]
    csv_bytes = statement_csv("Ahmed", tx, opening_balance=4000)
    assert b"6,000.0" in csv_bytes or b"6000.0" in csv_bytes
