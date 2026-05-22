const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export interface InitiateCallPayload {
  phone_number: string
  scenario: string
  scenario_data: Record<string, string>
}

export interface TranscriptEntry {
  speaker: "agent" | "user"
  text: string
  timestamp: string
}

export interface CallStatusData {
  call_id: string
  status: "pending" | "ringing" | "in_progress" | "completed" | "failed" | "no_answer"
  outcome: string | null
  transcript: TranscriptEntry[]
  phone_number: string
  scenario: string
  created_at: string
  updated_at: string
}

export async function initiateCall(payload: InitiateCallPayload): Promise<{ call_id: string; status: string; message: string }> {
  const res = await fetch(`${API_URL}/api/calls/initiate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getCallStatus(callId: string): Promise<CallStatusData> {
  const res = await fetch(`${API_URL}/api/calls/${callId}/status`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function listCalls(): Promise<CallStatusData[]> {
  const res = await fetch(`${API_URL}/api/calls/`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
