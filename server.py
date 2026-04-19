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
You are an instant expert — like Neo downloading kung fu in The Matrix.
The moment you see something through a camera, you know exactly what it is,
what state it's in, and precisely what the person in front of it needs to do.

Your job:
- Look at what's in front of the person
- Understand the situation immediately
- Give ONE clear verdict: safe to handle alone, or needs a specialist
- If they can handle it: guide them one step at a time, spoken clearly (number your steps 1. 2. 3.)
- If it needs a specialist: say who, why, and how urgent
- If there's danger: say so FIRST, immediately

Rules:
- Speak like an expert whispering in their ear — calm, clear, confident
- Never overwhelm. One thing at a time.
- Flag any danger immediately, before anything else
- Under 120 words per response — this goes straight to their earpiece
"""

STEP_PROMPT = """
You are guiding someone through a physical task step by step.
They just attempted a step and gave feedback.
Give ONE short follow-up: next step if it worked, or a fix if it didn't.
Under 40 words. Spoken aloud directly into their ear.
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


def analyze_image(image_b64: str | None, question: str) -> str:
    from google.genai import types
    if image_b64:
        img_bytes = base64.b64decode(image_b64)
        return _generate(
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                types.Part.from_text(text=question or "What do you see? What should I do?"),
            ],
            system=SYSTEM_PROMPT,
        )
    return _generate(contents=[question], system=SYSTEM_PROMPT)


def do_followup(question: str, context: str) -> str:
    return _generate(
        contents=[f"Context: {context}\n\nFeedback: {question}"],
        system=STEP_PROMPT,
    )


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


@app.post("/analyze")
def route_analyze():
    data = request.get_json()
    image_b64 = data.get("image")        # base64 JPEG, optional
    question = data.get("question", "What do you see? What should I do?")
    try:
        result = analyze_image(image_b64, question)
        return jsonify({"text": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/followup")
def route_followup():
    data = request.get_json()
    question = data.get("question", "")
    context = data.get("context", "")
    try:
        result = do_followup(question, context)
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
