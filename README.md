# FixGuide AI

An on-device voice + vision repair agent for field workers and homeowners.

Point your camera at a problem, describe it by voice, and get step-by-step guidance with a safety verdict — spoken back to you in real time.

Built with **Gemma 4 on Cactus** + **Gemini Vision** at the Cactus x Google DeepMind hackathon.

---

## What it does

- **Sees the job** — captures a photo from your webcam or phone
- **Hears the problem** — listens to your voice description
- **Analyzes on-device + cloud** — Gemma 270M locally, Gemini Vision for complex analysis
- **Guides step by step** — one step at a time, asks "did that work?" before continuing
- **Gives a safety verdict** — DIY SAFE ✓ or CALL A PROFESSIONAL ⚠️
- **Generates a work order** — when a professional is needed, creates a ready-to-send description
- **Logs every session** — saves history locally, shows last 3 sessions on startup

---

## Three modes

| Mode | What it does |
|---|---|
| 🔧 Repair Guide | Home & workplace repair — pipes, electrical, appliances |
| 🦺 Safety Inspector | Construction site hazard detection + PPE requirements |
| 🚗 Car Mechanic | Vehicle diagnostics, repair steps, cost estimate, urgency |

Switch modes anytime during a session.

---

## Setup

**1. Clone and set up Cactus**

```bash
git clone https://github.com/Evode-Manirahari/fixguide-ai
git clone https://github.com/cactus-compute/cactus
cd cactus && source ./setup && cd ..
cactus build --python
cactus download google/functiongemma-270m-it
```

**2. Install dependencies**

```bash
brew install portaudio
pip install -r requirements.txt
pip install google-genai
```

**3. Set API keys**

Get a free Gemini API key from [aistudio.google.com/api-keys](https://aistudio.google.com/api-keys)

```bash
export GEMINI_API_KEY="your-key-here"
```

**4. Run**

```bash
python main.py
```

---

## How to use

1. Choose a mode (1, 2, or 3)
2. Choose input mode — standard (keyboard + voice) or fully hands-free voice-only
3. Press Enter (or say "start") to begin a session
4. Point camera at the problem → speak your question
5. Listen to the guidance, follow steps one by one
6. Say "done" to end the session

**During a session:**
- Say **"yes"** after each step to continue
- Say **"no"** or describe the issue if a step failed — the AI troubleshoots
- Say **"done"** to finish
- Say **"mode"** to switch modes

---

## Requirements

- macOS (tested on macOS Sequoia)
- Python 3.12
- Gemini API key (free tier — 1,500 requests/day)
- Webcam or phone camera (AirDrop photos supported)

---

## Tech stack

| Layer | Technology |
|---|---|
| On-device model | Gemma 270M via Cactus Python FFI |
| Cloud vision | Gemini 2.0 Flash (google-genai) |
| Voice input | sounddevice + SpeechRecognition |
| Voice output | macOS `say` (TTS) |
| Camera | OpenCV |

---

## Hackathon

Built at the **Cactus x Google DeepMind Voice Agents Hackathon** — April 2026.

Tracks entered: Best On-Device Enterprise Agent (B2B) · Ultimate Consumer Voice Experience (B2C)
