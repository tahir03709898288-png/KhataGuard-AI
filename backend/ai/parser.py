"""Part 3 transaction parser used by text, voice and handwriting flows."""
from __future__ import annotations

import json
import os
from decimal import Decimal, InvalidOperation


def _setting(name: str, default: str = "") -> str:
    try:
        import streamlit as st
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


def _validate_result(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("AI response was not a valid JSON object.")
    
    if data.get("needs_clarification") is True:
        raise ValueError(data.get("question") or "Please clarify the customer name or transaction amounts.")
        
    customer = str(data.get("customer", "")).strip()
    if not customer or len(customer) > 100:
        raise ValueError("Customer name is missing or invalid.")
        
    try:
        sale = Decimal(str(data.get("sale", 0)))
        paid = Decimal(str(data.get("paid", 0)))
    except (InvalidOperation, TypeError):
        raise ValueError("Sale and paid amounts must be numeric.") from None
        
    if not sale.is_finite() or not paid.is_finite() or sale < 0 or paid < 0:
        raise ValueError("Transaction amounts cannot be negative.")
        
    if sale == 0 and paid == 0:
        raise ValueError("Transaction must contain at least a sale or payment amount greater than zero.")
        
    return {
        "customer": customer,
        "sale": float(sale),
        "paid": float(paid),
        "needs_clarification": False,
        "question": "",
    }


def parse_transaction(text: str, api_key: str | None = None, model: str | None = None) -> dict:
    """Parse financial transactions dynamically from Urdu, Roman Urdu, Hindi, or English using Groq."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Transaction text is empty.")
        
    key = api_key or _setting("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY is not configured in Streamlit Secrets.")
        
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ValueError("The openai package is missing. Install requirements first.") from exc

    client = OpenAI(
        api_key=key,
        base_url="https://api.groq.com/openai/v1",
        timeout=30,
        max_retries=2
    )
    
    model_name = model or _setting("GROQ_MODEL", "openai/gpt-oss-20b")

    system_prompt = (
        "You are an expert financial ledger parser for Urdu, Roman Urdu, Hindi, and English spoken inputs.\n"
        "Extract EXACTLY ONE transaction and parse customer name, sale amount (goods bought, saman, bill), "
        "and paid amount (cash given, payment, recovery, debt settlement).\n\n"
        "KEY FLEXIBILITY RULES:\n"
        "1. Sentence structure and word order DO NOT MATTER. Paid can come before sale or vice versa.\n"
        "2. Paid amount CAN BE HIGHER than the sale amount (e.g., customer paying off previous debt).\n"
        "3. If only payment is mentioned, set sale=0. If only sale is mentioned, set paid=0.\n"
        "4. Output MUST be strictly valid JSON without markdown tags.\n\n"
        "JSON SCHEMA:\n"
        "{\n"
        '  "customer": "string",\n'
        '  "sale": number,\n'
        '  "paid": number,\n'
        '  "needs_clarification": boolean,\n'
        '  "question": "string"\n'
        "}"
    )

    try:
        response = client.chat.completions.create(
            model=model_name,
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text[:4000]},
            ],
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        return _validate_result(data)
    except json.JSONDecodeError:
        raise ValueError("Failed to process transaction structure from AI response.") from None
    except Exception as err:
        raise ValueError(f"Parsing error: {str(err)}") from err
