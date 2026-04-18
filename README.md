# FixGuide AI

> *Like Neo downloading kung fu — point, listen, do.*

An on-device voice + vision AI agent that sees what's in front of you, reasons about it instantly, and talks you through exactly what to do — step by step, through your earpiece.

You don't need experience. Just point and listen.

---

## How it works

```
📸 Sees      →   through your camera
🧠 Reasons   →   what it is, what state it's in, what needs to happen
🔊 Talks     →   clear, step-by-step guidance through your earpiece
```

One verdict. No confusion:
- **✓ HANDLE IT** — guides you through it, one step at a time
- **📞 CALL SPECIALIST** — tells you who, why, and how urgent
- **⚠️ DANGER** — stops you before you make it worse

---

## Features

- **Universal** — works on any physical task: repair, maintenance, inspection, diagnostics
- **Step tracker** — one step at a time, asks "did that work?", adapts if something goes wrong
- **Hands-free mode** — fully voice-operated, designed for earpiece use
- **Work order generator** — when a specialist is needed, writes a ready-to-send description
- **Session history** — logs every job locally, shows recent sessions on startup
- **On-device + cloud** — Gemma 270M on-device, Gemini Vision for analysis

---

## Setup

**1. Clone repos**

```bash
git clone https://github.com/Evode-Manirahari/fixguide-ai
git clone https://github.com/cactus-compute/cactus
```

**2. Set up Cactus**

```bash
cd cactus && source ./setup && cd ..
cactus build --python
cactus download google/functiongemma-270m-it
```

**3. Install dependencies**

```bash
brew install portaudio
pip install -r requirements.txt
pip install google-genai
```

**4. Set your Gemini API key**

Get a free key at [aistudio.google.com/api-keys](https://aistudio.google.com/api-keys)

```bash
export GEMINI_API_KEY="your-key-here"
```

**5. Run**

```bash
python main.py
```

---

## Usage

1. Choose input mode — **standard** (keyboard + voice) or **hands-free** (voice only)
2. Press Enter or say **"start"**
3. Point camera at the problem → speak what's going on
4. Listen to the verdict and follow the steps
5. Say **"yes"** after each step to continue, or describe the issue if something went wrong
6. Say **"done"** when finished

---

## Tech stack

| | |
|---|---|
| On-device model | Gemma 270M via Cactus |
| Vision + reasoning | Gemini 2.0 Flash |
| Voice input | sounddevice + SpeechRecognition |
| Voice output | macOS `say` |
| Camera | OpenCV |

---

Built at the **Cactus x Google DeepMind Voice Agents Hackathon** — April 2026
