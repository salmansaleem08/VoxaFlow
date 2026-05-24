# VoxaFlow — AI Voice Call Platform

VoxaFlow places intelligent outbound phone calls using AI. You pick a scenario (appointment reminder, lead qualification, or customer satisfaction survey), fill in the details, and VoxaFlow calls a real phone number where an AI agent has a natural conversation — transcribed live in the browser.

**Supports English and Urdu** — select the language before placing the call.

---

## What you need before starting

You will need **four terminals** open at the same time: backend, ngrok, frontend, and your normal terminal for setup. Read through this section fully before running anything.

### Accounts and API keys to collect first

| What | Where to get it | Notes |
|---|---|---|
| **Twilio Account SID** | [console.twilio.com](https://console.twilio.com) → Dashboard | Starts with `AC` |
| **Twilio Auth Token** | Same page, click the eye icon | Keep this secret |
| **Twilio Phone Number** | Twilio Console → Phone Numbers → Active Numbers | E.164 format e.g. `+12015551234` |
| **Gemini API Key** | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) | Free quota is enough |
| **Groq API Key** | [console.groq.com](https://console.groq.com) → API Keys | Free — used as fallback if Gemini fails |
| **ngrok account** | [ngrok.com](https://ngrok.com) | Free — needed to expose your local backend to Twilio |

> **Twilio trial account — critical step before any call will work:**
> Trial accounts can only call phone numbers you have **verified**.
> Go to: **Twilio Console → Phone Numbers → Verified Caller IDs → click +**
> Add and verify every phone number you intend to call. If you skip this, calls will fail silently.

### Software requirements

| Software | Min version | Check |
|---|---|---|
| Python | 3.9+ | `python3 --version` |
| pip | Latest | `pip --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| ngrok | Any | `ngrok --version` |

**Install ngrok:**
```bash
# macOS
brew install ngrok

# Windows — download from https://ngrok.com/download, unzip, add ngrok.exe to PATH

# Linux
snap install ngrok
# or download binary from https://ngrok.com/download
```

Authenticate ngrok (one-time setup). Your auth token is at [dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken):
```bash
ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN
```

---

## Step 1 — Clone and create the `.env` file

The `.env` file lives at the **project root** — the same folder that contains `backend/` and `frontend/`. The backend reads it automatically on startup.

```
VoxaFlow/          ← project root
├── .env           ← CREATE THIS FILE HERE
├── backend/
│   ├── .env.example  ← template, copy from here
│   └── ...
└── frontend/
    └── ...
```

**Create it from the template:**

```bash
# macOS / Linux
cp backend/.env.example .env

# Windows
copy backend\.env.example .env
```

**Open `.env` and fill in your values:**

```env
# ── LLM ──────────────────────────────────────────────────────────────────────
GEMINI_API_KEY=AIzaSy...            # Your Gemini API key
GROQ_API_KEY=gsk_...                # Your Groq API key (auto-used as fallback)

# ── Twilio ────────────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx   # Must start with AC
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx    # Your Twilio number in E.164 format

# ── Twilio API Key auth (alternative to Auth Token — use one or the other) ────
# Only fill these if you use an API Key instead of Auth Token.
# TWILIO_API_KEY=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# TWILIO_API_SECRET=your_api_key_secret

# ── URLs — leave BACKEND_URL as localhost for now, update it in Step 3 ────────
BACKEND_URL=http://localhost:8000   # ← will be replaced with ngrok URL in Step 3
FRONTEND_URL=http://localhost:3000
```

Save the file. Leave `BACKEND_URL` as localhost for now — you will update it in Step 3.

---

## Step 2 — Start the backend

Open **Terminal 1** and run:

```bash
# Go to the backend folder
cd backend

# Create a Python virtual environment (first time only)
python3 -m venv venv

# Activate it
source venv/bin/activate          # macOS / Linux
venv\Scripts\activate             # Windows (Command Prompt)
# venv\Scripts\Activate.ps1      # Windows (PowerShell)

# Upgrade pip and install dependencies (first time only)
pip install --upgrade pip
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload --port 8000
```

**Expected output:**
```
INFO: Twilio auth: Account SID + Auth Token
INFO: CONFIG ERROR: BACKEND_URL is 'http://localhost:8000' — ...   ← expected, fix in Step 3
INFO: VoxaFlow API is ready.
INFO: Uvicorn running on http://127.0.0.1:8000
```

The `CONFIG ERROR` about localhost is expected at this point — you haven't set ngrok yet. The API docs are at **http://localhost:8000/docs** if you want to verify the backend is up.

> **If you see import errors:** Make sure your virtual environment is activated (you should see `(venv)` in your prompt) and that `pip install -r requirements.txt` completed without errors.

---

## Step 3 — Start ngrok and update `BACKEND_URL`

Twilio cannot reach `localhost`. ngrok creates a public HTTPS tunnel to your local backend.

Open **Terminal 2** (keep Terminal 1 running):

```bash
ngrok http 8000
```

You will see output like:
```
Forwarding   https://abcd-1234.ngrok-free.app -> http://localhost:8000
```

Copy the `https://...ngrok-free.app` URL (the HTTPS one, not HTTP).

**Open your `.env` file and update `BACKEND_URL`:**
```env
BACKEND_URL=https://abcd-1234.ngrok-free.app
```

**Go back to Terminal 1 and restart the backend:**
```bash
# Press Ctrl+C to stop, then:
uvicorn main:app --reload --port 8000
```

You should now see — with no CONFIG ERROR:
```
INFO: Twilio auth: Account SID + Auth Token
INFO: Twilio webhooks → https://abcd-1234.ngrok-free.app
INFO: VoxaFlow API is ready.
```

> **ngrok URL changes every restart.** If ngrok closes and you restart it, you get a new URL. Update `BACKEND_URL` in `.env` and restart the backend every time this happens. Paid ngrok plans have fixed URLs.

---

## Step 4 — Start the frontend

Open **Terminal 3**:

```bash
# Go to the frontend folder
cd frontend

# Install Node dependencies (first time only)
npm install

# Create the frontend environment file (first time only)
# This tells the browser where the backend API is.

# macOS / Linux:
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Windows (Command Prompt):
echo NEXT_PUBLIC_API_URL=http://localhost:8000 > .env.local

# Windows (PowerShell):
'NEXT_PUBLIC_API_URL=http://localhost:8000' | Out-File -FilePath .env.local -Encoding utf8

# Start the dev server
npm run dev
```

**Expected output:**
```
▲ Next.js 15.x.x
  - Local:   http://localhost:3000
```

Open **http://localhost:3000** in your browser. You should see the VoxaFlow landing page.

> If you get a blank page or API errors, check that `frontend/.env.local` exists and contains `NEXT_PUBLIC_API_URL=http://localhost:8000`. Restart `npm run dev` after creating the file.

---

## Step 5 — Make a call

1. Go to **http://localhost:3000**
2. Click **Get Started** or scroll down to the call form
3. The default scenario is **Customer Satisfaction Survey** — easiest to test with
4. Fill in the customer name, product, and purchase date fields
5. Enter the phone number to call — **must be a number you can answer right now**
   - Trial accounts: this number must be in your Verified Caller IDs list
   - Use E.164 format: `+923001234567` (Pakistan) or `+12015551234` (US)
6. Select **English** or **Urdu**
7. Click **Launch Call Now**

### What happens next

The status badge changes: **Preparing → Ringing → Live Call**

Your phone will ring. **Answer it.**

**If you have a Twilio trial account**, you will hear:
> *"You have a call from a Twilio trial account. Press any key to execute your call code."*

**Press any digit (1, 2, 3, etc.)** within about 5 seconds. If you don't press in time, Twilio hangs up — just click Launch again.

After you press the key, the AI agent speaks its opening line. Respond naturally. The agent replies within 2–3 seconds. The live transcript updates in the browser every 2.5 seconds.

The call ends automatically once the conversation goal is met. The agent will ask if you have any questions before hanging up.

---

## Environment variables — complete reference

All variables go in the `.env` file at the **project root**.

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Gemini Flash — primary LLM for generating responses |
| `GROQ_API_KEY` | Recommended | Groq llama-3.3-70b — auto-fallback if Gemini fails |
| `TWILIO_ACCOUNT_SID` | Yes | Your Twilio Account SID (starts with `AC`) |
| `TWILIO_AUTH_TOKEN` | Yes | Your Twilio Auth Token |
| `TWILIO_PHONE_NUMBER` | Yes | Your Twilio number in E.164 format |
| `TWILIO_API_KEY` | No | Only if using API Key auth instead of Auth Token |
| `TWILIO_API_SECRET` | No | Required if `TWILIO_API_KEY` is set |
| `BACKEND_URL` | Yes | Public ngrok HTTPS URL — must NOT be localhost |
| `FRONTEND_URL` | No | Defaults to `http://localhost:3000` |

---

## Scenarios

| Scenario | Agent | What it does | Suggested test fields |
|---|---|---|---|
| **Customer Satisfaction** | Maya | 3-question satisfaction survey | Any name, product, purchase date |
| **Appointment Reminder** | Aria | Confirms, reschedules, or cancels appointment | Patient name, date, time, doctor |
| **Lead Qualification** | Alex | Qualifies a prospect, offers demo | Lead name, company, interest area |

---

## How the call pipeline works

```
1. Browser POSTs to /api/calls/initiate
2. Backend generates opening greeting (Gemini)
3. Backend calls Twilio API to place the outbound call
4. Phone rings → callee answers
5. [Trial only] Twilio plays disclaimer → callee presses a key
6. Twilio POSTs to /api/webhooks/answer → backend returns TwiML <Gather>
7. <Gather input="speech dtmf"> listens (supports barge-in and key presses)
8. When caller stops speaking (1s silence) → Twilio transcribes speech inline
9. Twilio POSTs SpeechResult to /api/webhooks/speech
10. Backend sends transcript to Gemini (or Groq fallback) → gets response JSON
11. Backend returns TwiML <Gather><Say>response</Say></Gather>
12. Twilio speaks response → goes back to step 7
13. When should_end_call=true → <Say>closing</Say><Hangup/>
14. Browser transcript updates every 2.5s via GET /api/calls/{id}/status
```

---

## Tech stack

| Layer | Technology | Detail |
|---|---|---|
| Frontend | Next.js 15, Tailwind CSS v3, TypeScript | App Router, client-side polling |
| Backend | FastAPI, Python 3.9+, uvicorn | Async, background tasks |
| Primary LLM | Gemini Flash (`gemini-flash-latest`) | google-genai SDK, JSON mode enforced, thinking disabled |
| Fallback LLM | Groq `llama-3.3-70b-versatile` | Activates automatically on any Gemini error |
| STT | Twilio `<Gather input="speech dtmf">` | Inline — no extra STT API or recording download |
| TTS (English) | Twilio `<Say voice="Polly.Joanna">` | Zero latency — no audio file generated |
| TTS (Urdu) | gTTS (Google TTS) | MP3 file generated, served from `/media/` |
| Telephony | Twilio Voice API | Outbound calls, TwiML, status callbacks |

---

## Project structure

```
VoxaFlow/
├── .env                         ← YOUR credentials (gitignored — never commit this)
├── .gitignore
├── README.md
│
├── backend/
│   ├── main.py                  ← FastAPI app + startup config validation
│   ├── config.py                ← Pydantic settings, reads ../.env
│   ├── requirements.txt         ← Python dependencies
│   ├── .env.example             ← Credential template (no real values)
│   ├── models/
│   │   └── schemas.py           ← All Pydantic models
│   ├── routers/
│   │   ├── calls.py             ← POST /api/calls/initiate, GET /api/calls/{id}/status
│   │   └── webhooks.py          ← POST /api/webhooks/answer, /speech, /status
│   └── services/
│       ├── call_store.py        ← In-memory session store (dict)
│       ├── gemini_service.py    ← Gemini LLM + Groq fallback
│       ├── tts_service.py       ← gTTS for Urdu audio files
│       ├── twilio_service.py    ← Twilio SDK wrapper
│       └── deepgram_service.py  ← Deepgram STT (not used in primary flow; kept for reference)
│
└── frontend/
    ├── .env.local               ← NEXT_PUBLIC_API_URL (you create this in Step 4)
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx
    │   └── globals.css
    ├── components/
    │   ├── ui/                  ← Button, Input, Card, Badge, Select
    │   ├── navbar.tsx
    │   ├── hero-section.tsx
    │   ├── call-form.tsx        ← Call launch form (scenario, fields, language)
    │   └── call-status.tsx      ← Live call monitor + transcript + error banner
    └── lib/
        ├── api.ts               ← Typed fetch wrappers
        └── utils.ts
```

---

## Troubleshooting

### Phone doesn't ring at all

1. Check the backend startup log for `CONFIG ERROR` — it will say exactly what's wrong
2. Make sure the callee number is in **Twilio Console → Phone Numbers → Verified Caller IDs** (trial accounts)
3. Confirm ngrok is running and `BACKEND_URL` in `.env` matches the current ngrok URL exactly (with `https://`)
4. Restart the backend after any `.env` change

### Trial account — call connects but goes silent or drops immediately

The trial disclaimer played and nobody pressed a key in time. Try calling again and press any digit within 3–4 seconds of hearing the message.

### Agent keeps saying "Sorry, I didn't catch that"

- You may not have pressed the key to get past the Twilio disclaimer
- Speak directly into the phone microphone, not on speakerphone
- Check backend logs for lines starting with `Twilio STT` — if the value is empty (`''`), no speech was captured

### Agent says "I apologize, could you repeat that" after valid speech

Gemini returned non-JSON output. Backend logs will show `Failed to parse Gemini response`. The Groq fallback should handle this automatically if `GROQ_API_KEY` is set. If it still happens:
- Verify `GROQ_API_KEY` is in `.env`
- Check backend logs for `Groq` lines

### Gemini 404 error

Only `gemini-flash-latest` is available on this API key. Do not change the `MODEL` constant in `gemini_service.py`. Groq takes over automatically.

### Frontend shows blank page or "Failed to fetch"

- Make sure `frontend/.env.local` exists and contains `NEXT_PUBLIC_API_URL=http://localhost:8000`
- Restart `npm run dev` after creating or editing `.env.local`
- Confirm the backend is running on port 8000

### `pip install -r requirements.txt` fails

Try upgrading pip first:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

On macOS, if you get SSL errors: `brew install openssl` then retry.

### Port 8000 already in use

```bash
# Find and kill the process using port 8000
lsof -i :8000           # macOS / Linux
netstat -ano | findstr :8000   # Windows
```

Or run the backend on a different port and update `.env` and `.env.local` accordingly:
```bash
uvicorn main:app --reload --port 8001
# then: BACKEND_URL=https://....ngrok-free.app (ngrok still points to 8001)
# and: NEXT_PUBLIC_API_URL=http://localhost:8001 in frontend/.env.local
# and: ngrok http 8001
```

---

## Known limitations

| Limitation | Detail |
|---|---|
| **Trial account disclaimer** | Twilio plays a message before the agent speaks. The callee must press a digit key to proceed. Upgrade to paid to remove. |
| **Verified numbers only** | Trial accounts can only call phone numbers verified in Twilio Console. |
| **Turn-based conversation** | Agent speaks, then listens. Speech captured after 1 second of silence. True real-time barge-in during longer speech requires WebSocket Media Streams. |
| **In-memory sessions** | Call sessions live in RAM. Restarting the backend clears all history. Replace `call_store.py` with Redis for persistence. |
| **ngrok URL changes** | Free ngrok gives a new URL every restart. Update `BACKEND_URL` and restart backend each time. |
| **Urdu TTS latency** | Urdu responses require generating a gTTS audio file (~700ms extra per turn). English uses Twilio's built-in voice with zero latency. |

---

## Adding a new scenario

1. Add an entry to `ScenarioType` enum in `backend/models/schemas.py`
2. Add a system prompt branch in `backend/services/gemini_service.py` → `_build_system_prompt()`
3. Add the scenario to `SCENARIOS` array in `frontend/components/call-form.tsx`
4. Add its input fields to `SCENARIO_FIELDS` in the same file

No other changes needed — the rest of the pipeline is fully generic.
