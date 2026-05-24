"use client"

import React, { useEffect, useRef, useState } from "react"
import {
  Phone, PhoneOff, PhoneCall, Clock, CheckCircle2,
  XCircle, AlertCircle, User, Bot, RefreshCw, ArrowLeft,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getCallStatus, type CallStatusData } from "@/lib/api"
import { cn } from "@/lib/utils"

const STATUS_CONFIG = {
  pending:     { label: "Preparing",  color: "muted",    icon: Clock,        animate: true  },
  ringing:     { label: "Ringing",    color: "warning",  icon: PhoneCall,    animate: true  },
  in_progress: { label: "Live Call",  color: "success",  icon: Phone,        animate: true  },
  completed:   { label: "Completed",  color: "success",  icon: CheckCircle2, animate: false },
  failed:      { label: "Failed",     color: "destructive", icon: XCircle,   animate: false },
  no_answer:   { label: "No Answer",  color: "warning",  icon: PhoneOff,     animate: false },
} as const

const OUTCOME_LABELS: Record<string, { label: string; color: string }> = {
  confirmed:            { label: "Appointment Confirmed",   color: "success"     },
  reschedule_requested: { label: "Reschedule Requested",    color: "warning"     },
  cancelled:            { label: "Appointment Cancelled",   color: "destructive" },
  qualified:            { label: "Lead Qualified",          color: "success"     },
  not_qualified:        { label: "Not Qualified",           color: "muted"       },
  callback_requested:   { label: "Callback Requested",      color: "warning"     },
  survey_completed:     { label: "Survey Completed",        color: "success"     },
  declined:             { label: "Survey Declined",         color: "muted"       },
  no_answer:            { label: "No Answer",               color: "muted"       },
  in_progress:          { label: "In Progress",             color: "default"     },
}

const TERMINAL_STATUSES = ["completed", "failed", "no_answer"]

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

interface CallStatusProps {
  callId: string
  onReset: () => void
}

export function CallStatus({ callId, onReset }: CallStatusProps) {
  const [data, setData] = useState<CallStatusData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const transcriptEndRef = useRef<HTMLDivElement>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchStatus = async () => {
    try {
      const result = await getCallStatus(callId)
      setData(result)
      setError(null)

      if (TERMINAL_STATUSES.includes(result.status)) {
        if (pollRef.current) clearInterval(pollRef.current)
      }
    } catch (err) {
      setError("Unable to fetch call status. Retrying…")
    }
  }

  useEffect(() => {
    fetchStatus()
    pollRef.current = setInterval(fetchStatus, 2500)
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [callId])

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [data?.transcript?.length])

  if (!data && !error) {
    return (
      <div className="flex flex-col items-center gap-4 py-16">
        <div className="size-10 rounded-full border-2 border-primary border-t-transparent animate-spin" />
        <p className="text-muted-foreground text-sm">Loading call status…</p>
      </div>
    )
  }

  if (error && !data) {
    return (
      <Card className="max-w-lg mx-auto">
        <CardContent className="pt-8 pb-8 flex flex-col items-center gap-4 text-center">
          <AlertCircle className="size-10 text-destructive" />
          <p className="text-sm text-muted-foreground">{error}</p>
          <Button variant="outline" size="sm" onClick={fetchStatus}>
            <RefreshCw className="size-4" /> Retry
          </Button>
        </CardContent>
      </Card>
    )
  }

  const statusConf = STATUS_CONFIG[data!.status as keyof typeof STATUS_CONFIG] ?? STATUS_CONFIG.pending
  const StatusIcon = statusConf.icon
  const outcomeConf = data?.outcome ? OUTCOME_LABELS[data.outcome] : null
  const isLive = !TERMINAL_STATUSES.includes(data!.status)

  return (
    <div className="w-full max-w-2xl mx-auto space-y-4">
      {/* Status header card */}
      <Card>
        <CardContent className="pt-6 pb-6">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3">
              <div className={cn(
                "flex items-center justify-center w-10 h-10 rounded-full",
                data!.status === "in_progress" ? "bg-primary/10" :
                data!.status === "completed"   ? "bg-emerald-100 dark:bg-emerald-950/40" :
                data!.status === "failed"      ? "bg-destructive/10" :
                "bg-muted"
              )}>
                <StatusIcon className={cn(
                  "size-5",
                  data!.status === "in_progress" && statusConf.animate && "animate-pulse text-primary",
                  data!.status === "completed"   && "text-emerald-600",
                  data!.status === "failed"      && "text-destructive",
                  !["in_progress","completed","failed"].includes(data!.status) && "text-muted-foreground",
                )} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-foreground">{statusConf.label}</span>
                  {isLive && (
                    <span className="inline-flex items-center gap-1 text-xs text-primary">
                      <span className="size-1.5 rounded-full bg-primary animate-pulse" />
                      Live
                    </span>
                  )}
                </div>
                <p className="text-sm text-muted-foreground font-mono">{data!.phone_number}</p>
              </div>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              {outcomeConf && (
                <Badge variant={(outcomeConf.color as Parameters<typeof Badge>[0]["variant"])}>
                  {outcomeConf.label}
                </Badge>
              )}
              <Badge variant="outline" className="font-mono text-[10px]">
                {callId.split("-")[0]}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error banner (Twilio/config failures) */}
      {data!.status === "failed" && data!.error && (
        <div className="flex items-start gap-2.5 p-4 rounded-lg bg-destructive/8 border border-destructive/20 text-destructive text-sm">
          <AlertCircle className="size-4 mt-0.5 shrink-0" />
          <div>
            <p className="font-medium mb-0.5">Call failed</p>
            <p className="text-xs text-destructive/80 font-mono break-all">{data!.error}</p>
          </div>
        </div>
      )}

      {/* Transcript */}
      <Card>
        <CardHeader className="border-b pb-4">
          <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-2">
            Conversation Transcript
            {isLive && <span className="size-1.5 rounded-full bg-primary animate-pulse" />}
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          {data!.transcript.length === 0 ? (
            <div className="py-8 flex flex-col items-center gap-3 text-center">
              {isLive ? (
                <>
                  <div className="flex gap-1">
                    {[0, 1, 2].map((i) => (
                      <div
                        key={i}
                        className="size-2 rounded-full bg-primary animate-bounce"
                        style={{ animationDelay: `${i * 150}ms` }}
                      />
                    ))}
                  </div>
                  <p className="text-sm text-muted-foreground">Waiting for call to connect…</p>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">No transcript available.</p>
              )}
            </div>
          ) : (
            <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
              {data!.transcript.map((entry, i) => (
                <div
                  key={i}
                  className={cn(
                    "flex gap-3",
                    entry.speaker === "agent" ? "justify-start" : "justify-end flex-row-reverse"
                  )}
                >
                  <div className={cn(
                    "flex items-center justify-center w-7 h-7 rounded-full shrink-0 mt-0.5",
                    entry.speaker === "agent" ? "bg-primary/10" : "bg-secondary/10"
                  )}>
                    {entry.speaker === "agent"
                      ? <Bot className="size-3.5 text-primary" />
                      : <User className="size-3.5 text-secondary" />
                    }
                  </div>
                  <div className={cn(
                    "max-w-[75%] rounded-xl px-3.5 py-2.5 text-sm",
                    entry.speaker === "agent"
                      ? "bg-muted text-foreground rounded-tl-none"
                      : "bg-secondary text-secondary-foreground rounded-tr-none"
                  )}>
                    <p className="leading-relaxed">{entry.text}</p>
                    <p className={cn(
                      "text-[10px] mt-1",
                      entry.speaker === "agent" ? "text-muted-foreground" : "text-white/50"
                    )}>
                      {formatTime(entry.timestamp)}
                    </p>
                  </div>
                </div>
              ))}
              <div ref={transcriptEndRef} />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex justify-center pt-2">
        <Button variant="outline" size="sm" onClick={onReset} className="gap-2">
          <ArrowLeft className="size-4" />
          Start Another Call
        </Button>
      </div>
    </div>
  )
}
