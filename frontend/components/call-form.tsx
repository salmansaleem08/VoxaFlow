"use client"

import React, { useState } from "react"
import { Phone, Loader2, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { initiateCall } from "@/lib/api"

const SCENARIOS = [
  { value: "customer_satisfaction","label": "Customer Satisfaction Survey" },
  { value: "appointment_reminder", label: "Appointment Reminder & Confirmation" },
  { value: "lead_qualification",   label: "Lead Qualification Call" },
  
]

interface ScenarioField {
  key: string
  label: string
  placeholder: string
  type?: string
}

const SCENARIO_FIELDS: Record<string, ScenarioField[]> = {
  appointment_reminder: [
    { key: "patient_name",       label: "Patient / Contact Name",   placeholder: "e.g. Sarah Johnson" },
    { key: "appointment_date",   label: "Appointment Date",          placeholder: "e.g. Thursday, June 12th",  type: "text" },
    { key: "appointment_time",   label: "Appointment Time",          placeholder: "e.g. 2:30 PM" },
    { key: "provider_name",      label: "Provider / Doctor Name",    placeholder: "e.g. Dr. Emily Carter" },
    { key: "location",           label: "Location (optional)",       placeholder: "e.g. Downtown Clinic, Suite 4" },
  ],
  lead_qualification: [
    { key: "lead_name",     label: "Lead Name",          placeholder: "e.g. James Wilson" },
    { key: "company_name",  label: "Company (optional)", placeholder: "e.g. Acme Corp" },
    { key: "interest_area", label: "Interest Area",      placeholder: "e.g. AI Voice Automation" },
    { key: "product_name",  label: "Product / Service",  placeholder: "e.g. VoxaFlow Enterprise" },
  ],
  customer_satisfaction: [
    { key: "customer_name",  label: "Customer Name",    placeholder: "e.g. Michael Brown" },
    { key: "product_name",   label: "Product / Service",placeholder: "e.g. VoxaFlow Pro" },
    { key: "purchase_date",  label: "Purchase Date",    placeholder: "e.g. last Tuesday" },
  ],
}

interface CallFormProps {
  onCallInitiated: (callId: string) => void
}

export function CallForm({ onCallInitiated }: CallFormProps) {
  const [phone, setPhone] = useState("")
  const [scenario, setScenario] = useState("customer_satisfaction")
  const [language, setLanguage] = useState("en")
  const [fields, setFields] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const scenarioFields = SCENARIO_FIELDS[scenario] ?? []

  const handleFieldChange = (key: string, value: string) => {
    setFields((prev) => ({ ...prev, [key]: value }))
  }

  const handleScenarioChange = (value: string) => {
    setScenario(value)
    setFields({})
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!phone.trim()) {
      setError("Phone number is required.")
      return
    }

    // Validate required fields (all except optional ones)
    const requiredFields = scenarioFields.filter(
      (f) => !f.label.includes("optional")
    )
    for (const f of requiredFields) {
      if (!fields[f.key]?.trim()) {
        setError(`"${f.label}" is required.`)
        return
      }
    }

    setLoading(true)
    try {
      const result = await initiateCall({
        phone_number: phone.trim(),
        scenario,
        scenario_data: fields,
        call_language: language,
      })
      onCallInitiated(result.call_id)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to initiate call. Check your backend connection."
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="w-full max-w-lg mx-auto shadow-md">
      <CardHeader className="border-b pb-6">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary/10">
            <Phone className="size-5 text-primary" />
          </div>
          <div>
            <CardTitle className="text-lg">Launch an Outbound Call</CardTitle>
            <CardDescription>
              Configure your AI agent and trigger a real call
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Phone number */}
          <div className="space-y-2">
            <Label htmlFor="phone">Phone Number</Label>
            <Input
              id="phone"
              type="tel"
              placeholder="+1 (555) 000-0000"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="h-11"
              required
            />
            <p className="text-xs text-muted-foreground">E.164 format (+1xxxxxxxxxx)</p>
          </div>

          {/* Language */}
          <div className="space-y-2">
            <Label htmlFor="language">Call Language</Label>
            <Select
              id="language"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="h-11"
            >
              <option value="en">English</option>
              <option value="ur">Urdu (اردو)</option>
            </Select>
          </div>

          {/* Scenario */}
          <div className="space-y-2">
            <Label htmlFor="scenario">Call Scenario</Label>
            <Select
              id="scenario"
              value={scenario}
              onChange={(e) => handleScenarioChange(e.target.value)}
              className="h-11"
            >
              {SCENARIOS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </Select>
          </div>

          {/* Dynamic scenario fields */}
          {scenarioFields.length > 0 && (
            <div className="space-y-4 pt-1 border-t border-border">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide pt-2">
                Scenario Details
              </p>
              {scenarioFields.map((field) => (
                <div key={field.key} className="space-y-2">
                  <Label htmlFor={field.key}>{field.label}</Label>
                  <Input
                    id={field.key}
                    type={field.type || "text"}
                    placeholder={field.placeholder}
                    value={fields[field.key] ?? ""}
                    onChange={(e) => handleFieldChange(field.key, e.target.value)}
                    className="h-11"
                  />
                </div>
              ))}
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-destructive/8 border border-destructive/20 text-destructive text-sm">
              <AlertCircle className="size-4 mt-0.5 shrink-0" />
              {error}
            </div>
          )}

          {/* Submit */}
          <Button
            type="submit"
            size="xl"
            className="w-full font-semibold"
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Preparing Call…
              </>
            ) : (
              <>
                <Phone className="size-4" />
                Launch Call Now
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
