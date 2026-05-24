# VoxaFlow — AI Voice Call Platform

VoxaFlow makes intelligent outbound voice calls using AI. It handles appointment reminders, lead qualification, and customer satisfaction surveys — with real-time transcription shown in the browser as the call happens.

**Supports English and Urdu** — the agent automatically detects which language the caller uses and responds in the same language.

---

## How it works

```
Browser (Next.js) ──► FastAPI backend ──► Gemini AI (generates response)
                                      ──► Twilio (places phone call)
                                      ◄── Twilio webhook (caller's voice recording)
                                      ──► Deepgram (transcribes voice → text)
                                      ──► Twilio <Say> (speaks response, zero-latency)
```

1. You fill in a phone number and scenario details in the browser
2. Backend generates an opening greeting via Gemini and places the call via Twilio
3. When answered, Twilio speaks the greeting and starts recording
4. Caller's voice → Deepgram STT → Gemini generates next line → Twilio speaks it
5. Loop continues until the conversation goal is met
6. Browser shows the live transcript updated every 2.5 seconds

---

## Prerequisites

You need the following before starting:

| Requirement | Notes |
|---|---|
| **Python 3.9+** | `python3 --version` to check |
| **Node.js 18+** | `node --version` to check |
| **ngrok account** | Free. Required to expose your local backend to Twilio. [ngrok.com](https://ngrok.com) |
| **Twilio trial account** | Free. Get a phone number. [twilio.com](https://www.twilio.com) |
| **Gemini API key** | Already set in `.env` |
| **Deepgram API key** | Already set in `.env` |

### Install ngrok

```bash
# macOS (Homebrew)
brew install ngrok

# Or download from https://ngrok.com/download
```

After installing, authenticate once:
```bash
ngrok config add-authtoken YOUR_NGROK_TOKEN
```
Your token is at: https://dashboard.ngrok.com/get-started/your-authtoken

---

## Step 1 — Configure your environment

The `.env` file at the project root holds all credentials. Open it and verify/fill these values:

```env
# ── Already set ──────────────────────────────────────────────────────
GEMINI_API_KEY=...         # Gemini API key
DEEPGRAM_API_KEY=...       # Deepgram API key

# ── Twilio — find these at console.twilio.com → Dashboard ────────────
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx   # Must start with AC
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx    # Your Twilio number in E.164 format

# If you use an API Key instead of Auth Token:
# TWILIO_API_KEY=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# TWILIO_API_SECRET=your_secret

# ── Set AFTER step 3 (ngrok) ─────────────────────────────────────────
BACKEND_URL=https://xxxx.ngrok-free.app   # Your ngrok public URL
FRONTEND_URL=http://localhost:3000
```

**Twilio trial account note:** Trial accounts can only call phone numbers that are **verified** in your Twilio console. Go to: Twilio Console → Phone Numbers → Verified Caller IDs → add the number you want to call.

---

## Step 2 — Start the backend

```bash
# From the project root
cd backend

# Create a Python virtual environment (first time only)
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# Install Python dependencies
pip install -r requirements.txt

# Start the backend server
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO: VoxaFlow API is ready.
INFO: Uvicorn running on http://0.0.0.0:8000
```

The API docs are at: **http://localhost:8000/docs**

---

## Step 3 — Expose backend with ngrok

Twilio sends call events (webhooks) to your backend. For local development, ngrok creates a public tunnel to your localhost.

Open a **new terminal** and run:

```bash
ngrok http 8000
```

You will see output like:
```
Forwarding  https://abcd-1234.ngrok-free.app -> http://localhost:8000
```

Copy the `https://...ngrok-free.app` URL. Now update your `.env`:

```env
BACKEND_URL=https://abcd-1234.ngrok-free.app
```

**Restart the backend** after updating the `.env` so it picks up the new URL:

```bash
# In the backend terminal, press Ctrl+C then:
uvicorn main:app --reload --port 8000
```

> **Important:** ngrok free tier gives you a new URL every time you restart it. If ngrok restarts, update `BACKEND_URL` and restart the backend too.

---

## Step 4 — Start the frontend

Open a **new terminal**:

```bash
# From the project root
cd frontend

# Install Node dependencies (first time only)
npm install

# Create the frontend environment file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start the dev server
npm run dev
```

You should see:
```
▲ Next.js 15.x.x
- Local: http://localhost:3000
```

Open **http://localhost:3000** in your browser.

---

## Step 5 — Make your first call

1. Open http://localhost:3000
2. Scroll to **"Launch a Call"** or click "Get Started" in the navbar
3. Choose a scenario (e.g. **Appointment Reminder**)
4. Fill in the fields — use a real phone number you can answer
5. Click **Launch Call**
6. Answer the phone when it rings — you will hear the AI agent speak first
7. Respond naturally — the agent will reply within 2–4 seconds
8. Watch the live transcript update in the browser

### Expected call flow
- AI speaks greeting
- You speak → 3 seconds of silence → AI processes → AI responds
- Repeat until the conversation goal is reached
- Call ends automatically

---

## Scenarios

| Scenario | Agent | What it does |
|---|---|---|
| **Appointment Reminder** | Aria | Confirms, reschedules, or cancels an appointment |
| **Lead Qualification** | Alex | Qualifies a prospect with 2–3 questions, offers demo |
| **Customer Satisfaction** | Maya | Short 3-question satisfaction survey |

---

## Project structure

```
VoxaFlow/
├── .env                        ← All credentials (gitignored)
├── .gitignore
├── README.md
│
├── backend/
│   ├── main.py                 ← FastAPI entry point
│   ├── config.py               ← Pydantic settings (reads .env)
│   ├── requirements.txt
│   ├── .env.example            ← Template (no real values)
│   ├── models/
│   │   └── schemas.py          ← Request/response + session models
│   ├── routers/
│   │   ├── calls.py            ← REST: initiate call, poll status
│   │   └── webhooks.py         ← Twilio webhooks: answer, recording, status
│   └── services/
│       ├── call_store.py       ← In-memory session storage
│       ├── deepgram_service.py ← STT: Deepgram nova-2 (EN + UR detection)
│       ├── gemini_service.py   ← LLM: Gemini Flash conversation manager
│       ├── tts_service.py      ← TTS: gTTS (Urdu only; English uses Twilio <Say>)
│       └── twilio_service.py   ← Twilio SDK: make calls, download recordings
│
└── frontend/
    ├── app/
    │   ├── layout.tsx           ← Root layout (Manrope font, metadata)
    │   ├── page.tsx             ← Home page
    │   └── globals.css          ← Design tokens + animations
    ├── components/
    │   ├── ui/                  ← Button, Input, Card, Badge, Select
    │   ├── navbar.tsx
    │   ├── hero-section.tsx
    │   ├── call-form.tsx        ← Scenario selector + dynamic fields
    │   └── call-status.tsx      ← Live call monitor + transcript
    └── lib/
        ├── api.ts               ← Typed fetch wrappers
        └── utils.ts             ← cn() helper
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, Tailwind CSS 3, TypeScript |
| Backend | FastAPI, Python 3.9+ |
| LLM | Gemini Flash (`gemini-flash-latest`) via `google-genai` SDK |
| STT | Deepgram nova-2 — cloud, ~200 ms, telephony-optimized, EN+UR |
| TTS (English) | Twilio `<Say voice="Polly.Joanna">` — zero-latency, no file generation |
| TTS (Urdu) | Google TTS via gTTS — proper Urdu script support |
| Telephony | Twilio Voice — outbound calls + TwiML webhooks |

---

## Known limitations

| Limitation | Detail |
|---|---|
| **Twilio trial account** | Calls include a 15-second trial disclaimer before your agent speaks. Upgrade to a paid Twilio account to remove it. |
| **Verified numbers only** | Trial accounts can only call numbers verified in the Twilio console. |
| **Turn-based conversation** | The agent speaks, then listens. If you speak while the agent is talking, your speech will be captured at the start of the next recording window (3-second silence triggers recording end). This is a Twilio `<Record>` limitation — true barge-in requires WebSocket Media Streams. |
| **In-memory storage** | Call sessions are stored in RAM. Restarting the backend clears all sessions. For production, swap `call_store.py` with Redis. |
| **ngrok URL changes** | The free ngrok tier generates a new URL on every restart. Update `.env` `BACKEND_URL` and restart the backend each time. |

---

## Troubleshooting

**The phone doesn't ring**
- Check that the number is verified in Twilio Console → Phone Numbers → Verified Caller IDs
- Check that ngrok is running and `BACKEND_URL` in `.env` matches the current ngrok URL
- Check backend logs for Twilio error messages

**"I'm having trouble with the connection" loops**
- The recording download is failing. Check that `TWILIO_AUTH_TOKEN` and `TWILIO_ACCOUNT_SID` (the `AC...` one) are correct in `.env`

**Agent doesn't respond after you speak**
- The Deepgram transcription may be returning empty. Check backend logs for `Deepgram:` lines
- Make sure you stop speaking for at least 3 seconds so Twilio knows the recording is done

**Deepgram 401 error**
- Check that `DEEPGRAM_API_KEY` in `.env` is correct

**Gemini errors**
- Check that `GEMINI_API_KEY` is valid and has quota available

---

## Adding a new scenario

1. Add a new value to `ScenarioType` in `backend/models/schemas.py`
2. Add a system prompt branch in `backend/services/gemini_service.py` → `_build_system_prompt()`
3. Add the scenario to the `SCENARIOS` array in `frontend/components/call-form.tsx`
4. Add its input fields to `SCENARIO_FIELDS` in the same file

No structural changes required — the architecture is fully data-driven.
