#!/usr/bin/env python3
"""
FixGuide AI — Backend server for the web frontend.
Reads GEMINI_API_KEY from environment so the browser never needs it.
"""

import os
import sys
import base64
import tempfile
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

# reuse constants + functions from main.py
REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT / "cactus" / "python"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash"]

SYSTEM_PROMPT = """
You are FixGuide — a calm, knowledgeable friend who happens to be an expert in home repair, plumbing, electrical work, HVAC, cars, and anything physical.

You're having a live conversation with someone who needs help. You can see what they're pointing their camera at.

How to speak:
- Like a real person, not a report. Warm, clear, confident.
- Short sentences. Natural rhythm. Never robotic or formal.
- Guide them conversationally — "Turn that valve clockwise, the one right under the pipe" not "Step 1: Turn valve."
- One thing at a time. Never overwhelm.
- After guiding, check in naturally — "Give that a try and tell me what happens" or "Does that make sense?"
- If something is dangerous, say so immediately and firmly — but calm, not panicked.
- If they need a professional, say who and why, and offer to write a work order.

Keep responses under 80 words — this goes straight to their earpiece.
Never use numbered lists or bullet points. Just talk.
"""

WORK_ORDER_PROMPT = """
Write a short work order a person can text to a contractor right now.
Problem, location hint, urgency level. Plain text. Under 50 words.
"""


def _generate(contents, system: str) -> str:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=GEMINI_API_KEY)
    for model in GEMINI_MODELS:
        try:
            r = client.models.generate_content(
                model=model,
                config=types.GenerateContentConfig(system_instruction=system),
                contents=contents,
            )
            return r.text.strip()
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                continue
            raise
    return "I'm having trouble connecting. Please check your API key and try again."


def chat(history: list, image_b64: str | None = None) -> str:
    """Send full conversation history to Gemini for natural multi-turn dialogue."""
    from google.genai import types
    from google import genai

    client = genai.Client(api_key=GEMINI_API_KEY)
    contents = []

    for i, msg in enumerate(history):
        role = "user" if msg["role"] == "user" else "model"
        # attach image to the first user message if provided
        if role == "user" and i == 0 and image_b64:
            img_bytes = base64.b64decode(image_b64)
            contents.append(types.Content(role="user", parts=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                types.Part.from_text(text=msg["content"]),
            ]))
        else:
            contents.append(types.Content(role=role, parts=[
                types.Part.from_text(text=msg["content"]),
            ]))

    for model in GEMINI_MODELS:
        try:
            r = client.models.generate_content(
                model=model,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                contents=contents,
            )
            return r.text.strip()
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                continue
            raise
    return "I'm having trouble connecting right now. Please try again."


def do_work_order(analysis: str, question: str) -> str:
    return _generate(
        contents=[f"Situation: {analysis}\nDescription: {question}"],
        system=WORK_ORDER_PROMPT,
    )


# ── Flask app ──────────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder=str(REPO_ROOT / "web"), static_url_path="")
CORS(app)

@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok", "key_set": bool(GEMINI_API_KEY)})


@app.post("/chat")
def route_chat():
    data = request.get_json()
    history = data.get("history", [])   # [{role, content}, ...]
    image_b64 = data.get("image")       # base64 JPEG, attached to first message
    try:
        result = chat(history, image_b64)
        return jsonify({"text": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/workorder")
def route_workorder():
    data = request.get_json()
    analysis = data.get("analysis", "")
    question = data.get("question", "")
    try:
        result = do_work_order(analysis, question)
        return jsonify({"text": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    if not GEMINI_API_KEY:
        print("  ⚠️  GEMINI_API_KEY not set. Export it first.")
    else:
        print(f"  ✓ Gemini API key loaded")
    print("  Starting FixGuide AI server at http://localhost:5001\n")
    app.run(host="0.0.0.0", port=5001, debug=False)
