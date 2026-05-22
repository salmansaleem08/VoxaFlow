# VoxaFlow — AI-Powered Voice Call Automation

VoxaFlow is a full-stack voice AI platform that deploys intelligent outbound AI agents to handle appointment reminders, lead qualification, and customer satisfaction surveys — automatically, with natural conversation and real-time transcription.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        VoxaFlow Architecture                     │
│                                                                   │
│  ┌──────────────┐  REST API   ┌──────────────────────────────┐  │
│  │   Next.js 15  │ ──────────▶ │        FastAPI Backend        │  │
│  │   (Vercel)    │            │          (Render)             │  │
│  │               │ ◀────────── │                              │  │
│  │  • Call Form  │  Polling   │  ┌────────┐  ┌───────────┐  │  │
│  │  • Live       │            │  │ Gemini │  │  Whisper  │  │  │
│  │    Transcript │            │  │  LLM   │  │   STT     │  │  │
│  │  • Outcome    │            │  └────────┘  └───────────┘  │  │
│  └──────────────┘            │       │            │         │  │
│                               │  ┌───▼────────────▼────┐    │  │
│                               │  │   Google TTS (gTTS)  │    │  │
│                               │  └────────────┬────────┘    │  │
│                               └───────────────│─────────────┘  │
│                                               │ TwiML + Audio   │
│                                      ┌────────▼──────────┐      │
│                                      │      Twilio        │      │
│                                      │  (Outbound Calls)  │      │
│                                      └────────┬──────────┘      │
│                                               │ Phone Call       │
│                                      ┌────────▼──────────┐      │
│                                      │      Customer      │      │
│                                      │   (Real Phone)     │      │
│                                      └───────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

## Call Flow

1. **User** fills in phone number + scenario details in the UI
2. **Frontend** POSTs to `/api/calls/initiate`
3. **Backend** generates an opening greeting via **Gemini AI** and converts it to audio via **Google TTS (gTTS)**
4. **Twilio** dials the target phone number; when answered, plays the greeting
5. **Caller speaks** → Twilio records the response
6. **Backend** downloads the WAV recording → **Whisper STT** transcribes it
7. **Gemini AI** processes the conversation context and generates the next agent response
8. **Google TTS** converts the response to audio; Twilio plays it to the caller
9. Loop continues until the conversation is resolved (`should_end_call: true`)
10. **Frontend** polls `/api/calls/{call_id}/status` every 2.5 s to show live transcript and outcome

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | Next.js 15, Tailwind CSS 3, TypeScript | Deployed to Vercel |
| Backend | FastAPI, Python 3.9+ | Deployed to Render |
| LLM | Gemini 1.5 Flash | `GEMINI_API_KEY` in env |
| STT | OpenAI Whisper (base model) | No ffmpeg needed — uses scipy WAV loader |
| TTS | Google TTS via gTTS | No credentials needed |
| Telephony | Twilio Voice | Outbound calls + webhooks |

## Scenario: Appointment Reminder & Confirmation

VoxaFlow ships with **3 pre-built scenarios**:

| Scenario | Agent | Goal |
|---|---|---|
| Appointment Reminder | "Aria" from VoxaFlow Health | Confirm, reschedule, or cancel |
| Lead Qualification | "Alex" from VoxaFlow | Qualify lead and schedule demo |
| Customer Satisfaction | "Maya" from VoxaFlow | Complete 3-question survey |

Each scenario has a custom system prompt, agent persona, and structured JSON response from Gemini that drives the conversation loop.

## Design Decisions

### Why Gemini Flash?
Fast inference (~1-2s), excellent at structured JSON output (needed for `should_end_call` + `call_outcome` signaling), and the API key was already available. The context window easily handles 10–20 conversation turns.

### Why gTTS over Google Cloud TTS?
gTTS requires no credentials or GCP project — ideal for a portable demo that anyone can run locally. Production would upgrade to Google Cloud TTS (Chirp HD voices) for higher quality.

### Why no ffmpeg for Whisper?
Whisper's `transcribe()` accepts numpy arrays directly. By loading Twilio's WAV recording with `scipy.io.wavfile` and resampling to 16 kHz with `scipy.signal`, we skip the ffmpeg dependency entirely while maintaining full STT quality.

### Why Twilio `<Record>` over Media Streams?
The `<Record>` + webhook pattern is simpler to deploy on Render without persistent WebSocket connections, more reliable at scale, and still uses our full Whisper+Gemini+TTS pipeline. Trade-off: ~2–5s turn latency vs ~500ms with media streams.

### Flexible & Dynamic Design
Per the task requirements, all scenario logic is data-driven: new scenarios can be added by registering fields in `SCENARIO_FIELDS` (frontend) and adding a system prompt branch in `gemini_service.py` (backend) — no structural changes required.

---

## Local Development Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- A [Twilio account](https://www.twilio.com) with a phone number
- [ngrok](https://ngrok.com) (for Twilio webhooks during local dev)
- Gemini API key (already in `.env`)

### 1. Clone and configure environment

```bash
git clone <your-repo-url>
cd VoxaFlow
```

The root `.env` file already contains your `GEMINI_API_KEY`. Add your Twilio credentials:

```env
GEMINI_API_KEY=AIzaSy...          # Already set
TWILIO_ACCOUNT_SID=ACxxx...
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
BACKEND_URL=https://xxxx.ngrok-free.app   # Update after step 4
FRONTEND_URL=http://localhost:3000
WHISPER_MODEL=base
```

### 2. Backend setup

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate       # macOS/Linux
# venv\Scripts\activate        # Windows

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload --port 8000
```

The backend will load the Whisper model on startup (~30s first time, then cached).

API docs: http://localhost:8000/docs

### 3. Frontend setup

```bash
cd frontend

# Install dependencies
npm install

# Copy env file
cp .env.local.example .env.local
# Edit .env.local → set NEXT_PUBLIC_API_URL=http://localhost:8000

# Start dev server
npm run dev
```

Frontend: http://localhost:3000

### 4. Expose backend with ngrok (for Twilio webhooks)

Twilio needs a public URL to send webhooks to your local backend:

```bash
ngrok http 8000
```

Copy the `https://xxxx.ngrok-free.app` URL and set it in your `.env`:

```env
BACKEND_URL=https://xxxx.ngrok-free.app
```

Then restart the backend.

---

## Production Deployment

### Backend → Render

1. Push code to GitHub
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your repo; Render auto-detects `render.yaml`
4. Add environment variables in the Render dashboard:
   - `GEMINI_API_KEY`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
   - `BACKEND_URL` = your Render service URL (e.g. `https://voxaflow-api.onrender.com`)
   - `FRONTEND_URL` = your Vercel URL
5. Deploy

**Note:** Render free tier sleeps after 15 min of inactivity. Use Render Starter ($7/mo) for always-on.

### Frontend → Vercel

1. Go to [vercel.com](https://vercel.com) → **New Project**
2. Import your GitHub repo; Vercel detects `vercel.json` (root dir = `frontend`)
3. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = your Render backend URL
4. Deploy

---

## API Reference

### `POST /api/calls/initiate`

Initiate an outbound AI call.

```json
{
  "phone_number": "+15551234567",
  "scenario": "appointment_reminder",
  "scenario_data": {
    "patient_name": "Sarah Johnson",
    "appointment_date": "Thursday, June 12th",
    "appointment_time": "2:30 PM",
    "provider_name": "Dr. Emily Carter",
    "location": "Downtown Clinic"
  }
}
```

Response:
```json
{
  "call_id": "uuid",
  "status": "pending",
  "message": "Call is being prepared."
}
```

### `GET /api/calls/{call_id}/status`

Poll for live call status and transcript.

```json
{
  "call_id": "uuid",
  "status": "in_progress",
  "outcome": null,
  "transcript": [
    { "speaker": "agent", "text": "Hello, may I speak with Sarah?", "timestamp": "..." },
    { "speaker": "user",  "text": "Yes, this is Sarah.",           "timestamp": "..." }
  ],
  "phone_number": "+15551234567",
  "scenario": "appointment_reminder",
  "created_at": "...",
  "updated_at": "..."
}
```

---

## Project Structure

```
VoxaFlow/
├── .env                      # Root env (Gemini API key + Twilio creds)
├── .gitignore
├── README.md
├── render.yaml               # Render deployment config
├── vercel.json               # Vercel deployment config
│
├── backend/
│   ├── main.py               # FastAPI app entry point
│   ├── config.py             # Pydantic settings
│   ├── requirements.txt
│   ├── .env.example
│   ├── models/
│   │   └── schemas.py        # Pydantic request/response models
│   ├── routers/
│   │   ├── calls.py          # REST endpoints: initiate, status, list
│   │   └── webhooks.py       # Twilio webhooks: answer, recording, status
│   └── services/
│       ├── call_store.py     # In-memory session storage
│       ├── gemini_service.py # Gemini LLM conversation management
│       ├── tts_service.py    # Google TTS (gTTS) audio generation
│       ├── whisper_service.py# Whisper STT (numpy pipeline, no ffmpeg)
│       └── twilio_service.py # Twilio SDK: make calls, download recordings
│
└── frontend/
    ├── app/
    │   ├── layout.tsx         # Root layout with Manrope + JetBrains Mono fonts
    │   ├── page.tsx           # Home page (landing + call form)
    │   └── globals.css        # Tailwind + CSS variables (UI-Spec)
    ├── components/
    │   ├── ui/                # Design system (Button, Input, Card, etc.)
    │   ├── navbar.tsx
    │   ├── hero-section.tsx
    │   ├── features-section.tsx
    │   ├── call-form.tsx      # Dynamic scenario form
    │   └── call-status.tsx    # Live call monitor + transcript
    ├── lib/
    │   ├── utils.ts           # cn() helper
    │   └── api.ts             # Typed fetch wrappers
    └── public/
        └── logo.svg
```

---

## Extending VoxaFlow

To add a new call scenario:

1. **Backend** — add a new branch in `services/gemini_service.py` → `_build_system_prompt()`
2. **Backend** — add the new enum value to `ScenarioType` in `models/schemas.py`
3. **Frontend** — add the scenario option in `components/call-form.tsx` → `SCENARIOS` array
4. **Frontend** — define its input fields in `SCENARIO_FIELDS`

No structural changes required — the architecture is fully data-driven.
