#!/usr/bin/env python3
"""
FixGuide AI — Your expert in your ear.

Sees through your camera. Reasons about what's in front of you.
Talks you through it, step by step.
"""

import os
import re
import sys
import json
import time
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT / "cactus" / "python"))

WEIGHTS_DIR = REPO_ROOT / "cactus" / "weights" / "functiongemma-270m-it"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash"]
HISTORY_FILE = REPO_ROOT / "history.json"

BANNER = """
╔══════════════════════════════════════════════════════════╗
║                  FixGuide AI                             ║
║           Your expert. In your ear.                     ║
╚══════════════════════════════════════════════════════════╝
"""

SYSTEM_PROMPT = """
You are an instant expert — like Neo downloading kung fu in The Matrix.
The moment you see something through a camera, you know exactly what it is,
what state it's in, and precisely what the person in front of it needs to do.

Your job:
- Look at what's in front of the person
- Understand the situation immediately
- Give ONE clear verdict: safe to handle alone, or needs a specialist
- If they can handle it: guide them one step at a time, spoken clearly
- If it needs a specialist: say who, why, and how urgent

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


# ── history ──────────────────────────────────────────────────────────────────

def load_history() -> list:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            return []
    return []


def save_session(question: str, response: str, verdict: str):
    history = load_history()
    history.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "question": question[:80],
        "verdict": verdict,
        "summary": response[:200],
    })
    HISTORY_FILE.write_text(json.dumps(history, indent=2))


def show_history():
    history = load_history()
    if not history:
        return
    print("Recent sessions:")
    for e in history[-3:]:
        print(f"  {e['time']}  {e['verdict']}")
        print(f"  \"{e['question']}\"\n")


def extract_verdict(response: str) -> str:
    upper = response.upper()
    if any(w in upper for w in ["DANGER", "STOP", "DO NOT", "HAZARD"]):
        return "⚠️  DANGER"
    if any(w in upper for w in ["SPECIALIST", "PROFESSIONAL", "MECHANIC", "ELECTRICIAN", "CALL"]):
        return "📞 CALL SPECIALIST"
    return "✓  HANDLE IT"


def extract_steps(response: str) -> list[str]:
    steps = []
    for line in response.split("\n"):
        line = line.strip()
        if re.match(r"^\d+[\.\)]", line):
            step_text = re.sub(r"^\d+[\.\)]\s*", "", line)
            if step_text:
                steps.append(step_text)
    return steps


# ── I/O ──────────────────────────────────────────────────────────────────────

def speak(text: str):
    clean = text.replace('"', "'").replace("\n", " ")
    subprocess.run(["say", "-r", "175", clean], check=False)


def listen(seconds: int = 7, label: str = "Listening") -> str:
    import sounddevice as sd
    import soundfile as sf
    sr = 16000
    print(f"  🎤 {label} ({seconds}s)...", flush=True)
    audio = sd.rec(int(seconds * sr), samplerate=sr, channels=1, dtype="int16")
    sd.wait()
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, audio, sr)

    import speech_recognition as speech
    r = speech.Recognizer()
    with speech.AudioFile(tmp.name) as src:
        data = r.record(src)
    try:
        result = r.recognize_google(data)
        print(f"  🗣  \"{result}\"")
        return result
    except Exception:
        return ""


def capture_image() -> str | None:
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        time.sleep(0.8)
        ret, frame = cap.read()
        cap.release()
        if ret:
            tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            cv2.imwrite(tmp.name, frame)
            return tmp.name
    except Exception:
        pass

    print("\n  📱 No webcam. Send a photo from your phone (AirDrop → Downloads)")
    print("     then enter the path, or press Enter to skip.\n")
    path = input("  Path: ").strip().strip("'\"")
    return path if path and Path(path).exists() else None


# ── AI ───────────────────────────────────────────────────────────────────────

def load_model():
    try:
        from src.cactus import cactus_init, cactus_log_set_level
        cactus_log_set_level(4)
        return cactus_init(str(WEIGHTS_DIR), None, False)
    except Exception:
        print("  ⚠️  On-device model unavailable. Cloud only.")
        return None


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
                print(f"  ⚠️  {model} quota hit, trying next...")
                continue
            raise
    return "I'm having trouble connecting. Please check your API key and try again."


def analyze(image_path: str | None, question: str) -> str:
    from google.genai import types
    if image_path:
        mime = "image/jpeg" if image_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
        with open(image_path, "rb") as f:
            img = f.read()
        return _generate(
            contents=[
                types.Part.from_bytes(data=img, mime_type=mime),
                types.Part.from_text(text=question or "What do you see? What should I do?"),
            ],
            system=SYSTEM_PROMPT,
        )
    return _generate(contents=[question], system=SYSTEM_PROMPT)


def followup(question: str, context: str) -> str:
    return _generate(
        contents=[f"Context: {context}\n\nFeedback: {question}"],
        system=STEP_PROMPT,
    )


def work_order(analysis: str, question: str) -> str:
    return _generate(
        contents=[f"Situation: {analysis}\nDescription: {question}"],
        system=WORK_ORDER_PROMPT,
    )


# ── step guide ───────────────────────────────────────────────────────────────

def guide_steps(steps: list[str], voice_only: bool):
    print(f"\n  Guiding you through {len(steps)} steps...\n")
    for i, step in enumerate(steps):
        print(f"  [{i+1}/{len(steps)}] {step}")
        speak(f"Step {i + 1}. {step}")

        if i == len(steps) - 1:
            speak("That's the last step. Well done.")
            break

        speak("Did that work?")
        if voice_only:
            feedback = listen(seconds=5, label="Hearing your feedback")
        else:
            feedback = input("  (yes / describe issue): ").strip().lower()

        if not feedback or any(w in feedback for w in ["yes", "done", "worked", "good", "ok", "great"]):
            speak("Good. Next step.")
        else:
            tip = followup(feedback, step)
            print(f"  💡 {tip}")
            speak(tip)
    print()


# ── session ──────────────────────────────────────────────────────────────────

def run(model, voice_only: bool):
    # 1 — look
    speak("Point your camera. Taking photo in 3 seconds.")
    print("\n  📸 Taking photo in 3 seconds...")
    time.sleep(3)
    image_path = capture_image()
    print("  ✓ Got it." if image_path else "  No image — going voice only.")

    # 2 — listen
    speak("What's going on? Tell me.")
    question = listen(seconds=7, label="Describe the situation")
    if not question:
        question = "What do you see? What should I do next?"

    # 3 — reason
    print("\n  🧠 Thinking...\n")
    response = analyze(image_path, question)
    verdict = extract_verdict(response)

    print(f"  {verdict}\n")
    print(f"  {response}\n")
    speak(response)

    save_session(question, response, verdict)

    # 4 — step guide if handleable
    if "HANDLE IT" in verdict:
        steps = extract_steps(response)
        if steps:
            speak("Want me to walk you through it step by step?")
            confirm = listen(seconds=4, label="Say yes or no") if voice_only else input("  Step by step? (y/n): ").strip().lower()
            if "y" in confirm:
                guide_steps(steps, voice_only)

    # 5 — work order if specialist needed
    if "SPECIALIST" in verdict:
        speak("Want me to write a work order you can send right now?")
        confirm = listen(seconds=4, label="Say yes or no") if voice_only else input("  Generate work order? (y/n): ").strip().lower()
        if "y" in confirm:
            order = work_order(response, question)
            print(f"\n  📋 Work order:\n  {order}\n")
            speak("Here is your work order. " + order)

    # 6 — follow-up
    context = response
    while True:
        speak("Anything else?")
        q = listen(seconds=6, label="Ask anything") if voice_only else input("  Follow-up (or Enter to finish): ").strip()

        if not q or any(w in q.lower() for w in ["no", "done", "quit", "bye", "finish", "stop", "thank"]):
            speak("Got it. You're good.")
            break

        answer = followup(q, context)
        print(f"\n  {answer}\n")
        speak(answer)
        context += f" {answer}"


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    print(BANNER)

    if not GEMINI_API_KEY:
        print("  ⚠️  Set your key: export GEMINI_API_KEY='your-key'\n")

    show_history()

    print("  Loading model...")
    model = load_model()
    print("  ✓ Ready\n")

    print("  Input mode:")
    print("  [1] Standard   — keyboard + voice")
    print("  [2] Hands-free — voice only (earpiece)\n")
    voice_only = input("  Choose (1 or 2): ").strip() == "2"
    print()

    speak("Hands free mode. Say start whenever you're ready." if voice_only else "Ready. Press Enter whenever you need me.")

    while True:
        print("─" * 56)
        if voice_only:
            print("  Say 'start' to begin or 'quit' to exit...")
            cmd = listen(seconds=5, label="Waiting")
        else:
            print("  Press Enter to start (q to quit): ", end="", flush=True)
            cmd = input().strip().lower()

        if "quit" in cmd or cmd == "q":
            break
        if voice_only and "start" not in cmd:
            if cmd:
                speak("Say start to begin or quit to exit.")
            continue

        run(model, voice_only)

    if model:
        try:
            from src.cactus import cactus_destroy
            cactus_destroy(model)
        except Exception:
            pass
    speak("Goodbye.")
    print("\n  Goodbye.\n")


if __name__ == "__main__":
    main()
