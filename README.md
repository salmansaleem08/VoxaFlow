# VoxaFlow — AI Voice Call Platform

VoxaFlow makes intelligent outbound voice calls using AI. You fill in a phone number and scenario details in the browser, and VoxaFlow places a real phone call where an AI agent conducts a natural conversation — appointment reminders, lead qualification, or customer satisfaction surveys.

**Supports English and Urdu.** The agent responds in whichever language you select before placing the call.

---

## How it works

```
Browser (Next.js)
  └─► POST /api/calls/initiate
        └─► Gemini AI generates opening greeting
        └─► Twilio places the outbound call
              └─► Callee answers → Twilio calls /api/webhooks/answer
                    └─► <Gather input="speech dtmf"> listens (barge-in supported)
                    └─► Twilio transcribes speech inline → POSTs to /api/webhooks/speech
                          └─► Gemini (or Groq fallback) generates next response
                          └─► Twilio <Say> speaks it, then listens again
                          └─► Loop until conversation goal is reached
```

The browser polls `/api/calls/{id}/status` every 2.5 seconds and shows the live transcript.

---

## Prerequisites

Install and set up these before starting:

| Requirement | How to get it |
|---|---|
| **Python 3.10+** | `python3 --version` · [python.org](https://www.python.org/downloads/) |
| **Node.js 18+** | `node --version` · [nodejs.org](https://nodejs.org/) |
| **Twilio account** | Free trial at [twilio.com](https://www.twilio.com) — get a phone number |
| **Gemini API key** | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) |
| **Groq API key** | Free at [console.groq.com](https://console.groq.com) — used as LLM fallback |
| **ngrok** | Free at [ngrok.com](https://ngrok.com) — exposes your local backend to Twilio |

### Install ngrok

```bash
# macOS
brew install ngrok

# Or download from https://ngrok.com/download and add to PATH
```

Authenticate ngrok once (your token is at [dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)):

```bash
ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN
```

---

## Step 1 — Get your credentials

### Twilio credentials
Go to [console.twilio.com](https://console.twilio.com) → Dashboard:
- **Account SID** — starts with `AC`
- **Auth Token** — click the eye icon to reveal

Go to **Phone Numbers → Manage → Active Numbers** and copy your Twilio number.

> **Trial account limitation:** Trial accounts can only call **verified** phone numbers.
> Go to **Phone Numbers → Verified Caller IDs** → click **+** → verify the number you want to call.
> Without this, the call will fail silently.

### Gemini API key
Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) and create a key.

### Groq API key
Go to [console.groq.com](https://console.groq.com) → API Keys → Create. Free tier is sufficient.
Groq is used automatically if Gemini fails or times out.

---

## Step 2 — Configure environment variables

The `.env` file at the **project root** (next to `backend/` and `frontend/`) holds all credentials.

Create it if it doesn't exist:

```bash
cp backend/.env.example .env
```

Then open `.env` and fill in your values:

```env
# ── LLM ──────────────────────────────────────────────────────────────────────
GEMINI_API_KEY=AIza...                  # Your Gemini API key
GROQ_API_KEY=gsk_...                    # Your Groq API key (fallback)

# ── Twilio ────────────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx   # Must start with AC
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx                        # E.164 format

# ── URLs — fill BACKEND_URL after Step 4 (ngrok) ─────────────────────────────
BACKEND_URL=https://xxxx.ngrok-free.app   # ← update after starting ngrok
FRONTEND_URL=http://localhost:3000
```

**Important:** `BACKEND_URL` must be the ngrok HTTPS URL — Twilio cannot reach `localhost`.
Leave it as-is for now; you will update it in Step 4.

---

## Step 3 — Start the backend

```bash
# From the project root
cd backend

# Create a Python virtual environment (first time only)
python3 -m venv venv

# Activate it
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows

# Install dependencies (first time only, or after requirements.txt changes)
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload --port 8000
```

Expected output:
```
INFO: Twilio auth: Account SID + Auth Token
INFO: Twilio webhooks → http://localhost:8000      ← will show CONFIG ERROR until ngrok is set
INFO: VoxaFlow API is ready.
INFO: Uvicorn running on http://127.0.0.1:8000
```

The API explorer is at **http://localhost:8000/docs**

---

## Step 4 — Start ngrok

Twilio needs a public HTTPS URL to send call events to your backend. ngrok creates one.

Open a **new terminal** (keep the backend running):

```bash
ngrok http 8000
```

You will see:
```
Forwarding   https://abcd-1234.ngrok-free.app -> http://localhost:8000
```

Copy that `https://abcd-1234.ngrok-free.app` URL.

**Update your `.env`:**
```env
BACKEND_URL=https://abcd-1234.ngrok-free.app
```

**Restart the backend** to pick up the new URL:
```bash
# In the backend terminal, press Ctrl+C, then:
uvicorn main:app --reload --port 8000
```

You should now see:
```
INFO: Twilio webhooks → https://abcd-1234.ngrok-free.app
```

> **Every time ngrok restarts it gives you a new URL.** If that happens, update `BACKEND_URL` and restart the backend.

---

## Step 5 — Start the frontend

Open a **third terminal**:

```bash
cd frontend

# Install Node dependencies (first time only)
npm install

# Create the frontend env file (first time only)
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start the dev server
npm run dev
```

Expected output:
```
▲ Next.js 15.x.x
  Local:  http://localhost:3000
```

Open **http://localhost:3000** in your browser.

---

## Step 6 — Make your first call

1. Go to **http://localhost:3000**
2. Click **Get Started** or scroll to the **Launch a Call** form
3. Pick a scenario — start with **Customer Satisfaction Survey** (easiest to test)
4. Fill in the fields — use your own phone number (must be verified in Twilio for trial accounts)
5. Select language (**English** or **Urdu**)
6. Click **Launch Call Now**

What happens next:
- The form shows **Preparing** → **Ringing** → **Live Call**
- Your phone rings — **answer it**
- On a Twilio trial account: you will hear *"You have a call from a trial Twilio account. Press any key to execute your call code."* — **press any digit key (1, 2, etc.)**
- The AI agent speaks its opening line
- You respond — the agent listens and replies within 2–3 seconds
- The live transcript appears in the browser in real time
- The call ends automatically after the conversation goal is met

---

## Scenarios

| Scenario | Agent name | What happens |
|---|---|---|
| **Appointment Reminder** | Aria | Confirms, reschedules, or cancels an appointment |
| **Lead Qualification** | Alex | Qualifies a prospect, offers a demo if they fit |
| **Customer Satisfaction** | Maya | Runs a short 3-question satisfaction survey |

---

## Project structure

```
VoxaFlow/
├── .env                         ← Your credentials (gitignored, never commit)
├── .gitignore
├── README.md
│
├── backend/
│   ├── main.py                  ← FastAPI entry point + startup validation
│   ├── config.py                ← Pydantic settings (reads .env)
│   ├── requirements.txt
│   ├── .env.example             ← Template — copy to root .env, fill in values
│   ├── models/
│   │   └── schemas.py           ← Pydantic models for sessions, requests, responses
│   ├── routers/
│   │   ├── calls.py             ← REST: initiate call, poll status, list calls
│   │   └── webhooks.py          ← Twilio webhooks: answer, speech, status
│   └── services/
│       ├── call_store.py        ← In-memory session storage (dict)
│       ├── deepgram_service.py  ← Deepgram STT (kept for reference; Gather STT is primary)
│       ├── gemini_service.py    ← LLM: Gemini Flash + Groq fallback
│       ├── tts_service.py       ← TTS: gTTS for Urdu (English uses Twilio <Say>)
│       └── twilio_service.py    ← Twilio SDK: outbound calls
│
└── frontend/
    ├── app/
    │   ├── layout.tsx            ← Root layout (Manrope font, metadata)
    │   ├── page.tsx              ← Home page
    │   └── globals.css           ← Design tokens + Tailwind config
    ├── components/
    │   ├── ui/                   ← shadcn-style: Button, Input, Card, Badge, Select
    │   ├── navbar.tsx
    │   ├── hero-section.tsx
    │   ├── features-section.tsx
    │   ├── call-form.tsx         ← Scenario selector, dynamic fields, language picker
    │   └── call-status.tsx       ← Live call monitor + transcript + error display
    └── lib/
        ├── api.ts                ← Typed fetch wrappers for the backend API
        └── utils.ts              ← cn() Tailwind helper
```

---

## Tech stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | Next.js 15, Tailwind CSS 3, TypeScript | App Router |
| Backend | FastAPI, Python 3.10+ | Async, hot reload with uvicorn |
| Primary LLM | Gemini Flash (`gemini-flash-latest`) | `google-genai` SDK, JSON mode, thinking disabled |
| Fallback LLM | Groq `llama-3.3-70b-versatile` | Auto-activates if Gemini fails |
| STT | Twilio `<Gather input="speech">` | Inline transcription, no extra API needed |
| TTS (English) | Twilio `<Say voice="Polly.Joanna">` | Zero latency, no file generation |
| TTS (Urdu) | gTTS | MP3 served from backend `/media/` |
| Telephony | Twilio Voice | Outbound calls, TwiML, status callbacks |

---

## Troubleshooting

**Phone doesn't ring / call fails immediately**
- Verify the callee number in Twilio Console → Phone Numbers → Verified Caller IDs (trial accounts only)
- Check that ngrok is running and `BACKEND_URL` in `.env` matches the current ngrok URL
- Restart backend after updating `BACKEND_URL`
- Check backend startup logs — a `CONFIG ERROR` line will show exactly what's wrong

**Trial disclaimer — "press any key" doesn't connect the call**
- This is Twilio's trial account prompt. You must press a digit (1, 2, etc.) within a few seconds
- If you press too slowly or not at all, Twilio hangs up. Just try calling again
- Upgrade to a paid Twilio account to remove the disclaimer entirely

**Agent says "Sorry, I didn't catch that" repeatedly**
- Speak clearly toward the phone microphone
- Make sure you've pressed a key to get past the trial disclaimer first
- Check backend logs for `Twilio STT` lines — if they show empty strings, the STT isn't capturing audio

**Agent responds "I apologize, could you repeat that" after everything**
- Gemini returned invalid output. Check backend logs for `Failed to parse Gemini response`
- If the error is a 429 (quota exceeded) or 503, the Groq fallback will activate automatically
- Make sure `GROQ_API_KEY` is set in `.env` so the fallback is available

**Gemini API errors (404, model not found)**
- The only working model on this setup is `gemini-flash-latest`. Do not change the `MODEL` constant
- If Gemini is completely down, Groq takes over automatically

**Frontend can't reach backend (network error)**
- Make sure backend is running on port 8000
- Check that `NEXT_PUBLIC_API_URL=http://localhost:8000` is in `frontend/.env.local`
- Restart the frontend dev server after creating or editing `frontend/.env.local`

**Call shows "Ringing" in UI but phone doesn't ring**
- Check the backend log for `Call initiated:` — if it's missing, Twilio rejected the API call
- Check for a `CONFIG ERROR` about `BACKEND_URL` being localhost

**High latency / slow responses**
- Each turn: ~1s silence detection + ~1.5s Gemini = ~2.5s total. This is expected
- Groq is slightly faster than Gemini for shorter responses
- If latency is >5s, check your internet connection or Twilio region

---

## Known limitations

| Limitation | Detail |
|---|---|
| **Trial account disclaimer** | A 15-second message plays before your agent speaks. Press any digit to proceed. Removed with a paid account. |
| **Verified numbers only** | Trial accounts can only call numbers verified in Twilio Console. |
| **Turn-based conversation** | Agent speaks, then listens. Speech is captured after 1s of silence. True real-time interruption requires WebSocket Media Streams (different architecture). |
| **In-memory storage** | Sessions are lost when the backend restarts. For production, replace `call_store.py` with Redis or a database. |
| **ngrok URL changes** | Free ngrok gives a new URL on every restart. Update `BACKEND_URL` and restart backend each time. |
| **Single region** | Calls go through Twilio US region by default. High latency from other regions is expected on trial accounts. |

---

## Adding a new scenario

1. Add a value to `ScenarioType` in `backend/models/schemas.py`
2. Add a prompt branch in `backend/services/gemini_service.py` → `_build_system_prompt()`
3. Add it to `SCENARIOS` in `frontend/components/call-form.tsx`
4. Add its fields to `SCENARIO_FIELDS` in the same file

No structural changes needed — everything else is data-driven.
