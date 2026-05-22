"use client"

import React from "react"
import {
  Brain,
  Phone,
  FileText,
  Zap,
  Globe,
  BarChart3,
  ArrowRight,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"

const features = [
  {
    icon: Brain,
    title: "Context-Aware Conversations",
    description:
      "Powered by Gemini 1.5 Flash, our AI understands nuance, handles objections, and adapts its responses in real time — just like a trained human agent.",
    color: "text-purple-500",
    bg: "bg-purple-50 dark:bg-purple-950/30",
  },
  {
    icon: Phone,
    title: "Outbound Call Automation",
    description:
      "Programmatically trigger calls to any phone number worldwide via Twilio. Schedule campaigns, set retry logic, and manage call queues — all through our API.",
    color: "text-primary",
    bg: "bg-emerald-50 dark:bg-emerald-950/30",
  },
  {
    icon: FileText,
    title: "Real-Time Transcription",
    description:
      "Every word is captured with OpenAI Whisper STT and timestamped. Full call transcripts with speaker labels are available instantly after each call.",
    color: "text-blue-500",
    bg: "bg-blue-50 dark:bg-blue-950/30",
  },
  {
    icon: Zap,
    title: "Human-Quality Voice",
    description:
      "Google TTS delivers natural, expressive speech output that sounds professional and engaging — not robotic. Your customers won't know they're talking to AI.",
    color: "text-amber-500",
    bg: "bg-amber-50 dark:bg-amber-950/30",
  },
  {
    icon: Globe,
    title: "Multi-Scenario Support",
    description:
      "Deploy appointment reminders, lead qualification scripts, customer satisfaction surveys, or payment follow-ups — each with tailored agent personas.",
    color: "text-rose-500",
    bg: "bg-rose-50 dark:bg-rose-950/30",
  },
  {
    icon: BarChart3,
    title: "Outcome Tracking",
    description:
      "Every call produces a structured outcome: confirmed, rescheduled, qualified, or declined. Feed results directly into your CRM or analytics pipeline.",
    color: "text-indigo-500",
    bg: "bg-indigo-50 dark:bg-indigo-950/30",
  },
]

export function FeaturesSection() {
  return (
    <section id="features" className="py-24 px-4 bg-background">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center space-y-4 mb-16">
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-sm font-medium">
            Platform Capabilities
          </span>
          <h2 className="text-4xl sm:text-5xl font-bold text-foreground">
            Everything you need to automate
            <br />
            <span className="gradient-text">customer conversations</span>
          </h2>
          <p className="max-w-xl mx-auto text-muted-foreground text-lg">
            A complete voice AI stack — from telephony to transcription to
            outcomes — deployed as a single unified platform.
          </p>
        </div>

        {/* Feature grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature) => (
            <Card
              key={feature.title}
              className="group hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 border-border/60"
            >
              <CardHeader>
                <div className={`inline-flex items-center justify-center w-10 h-10 rounded-lg ${feature.bg} mb-3`}>
                  <feature.icon className={`size-5 ${feature.color}`} />
                </div>
                <CardTitle className="text-base">{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-sm leading-relaxed">
                  {feature.description}
                </CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

const steps = [
  {
    number: "01",
    title: "Enter Your Details",
    description:
      "Add a phone number, select a call scenario (appointment reminder, lead qualification, survey), and fill in the context — names, dates, products.",
  },
  {
    number: "02",
    title: "AI Takes the Wheel",
    description:
      "VoxaFlow dials the number via Twilio. When answered, Aria (our AI agent) greets the caller naturally, listens with Whisper STT, and responds via Google TTS.",
  },
  {
    number: "03",
    title: "Get Structured Results",
    description:
      "Track the call live with real-time status updates. After completion, view the full transcript, outcome (confirmed, qualified, etc.), and analytics.",
  },
]

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="py-24 px-4 bg-muted/30">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center space-y-4 mb-16">
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-sm font-medium">
            How It Works
          </span>
          <h2 className="text-4xl sm:text-5xl font-bold text-foreground">
            From setup to conversation
            <br />
            <span className="gradient-text">in under 60 seconds</span>
          </h2>
        </div>

        {/* Steps */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {steps.map((step, i) => (
            <div key={step.number} className="relative flex flex-col items-start">
              {/* Connector */}
              {i < steps.length - 1 && (
                <div className="hidden md:flex absolute top-5 left-[calc(100%_-_16px)] w-8 items-center justify-center">
                  <ArrowRight className="size-4 text-muted-foreground/50" />
                </div>
              )}
              <div className="text-4xl font-bold text-primary/20 font-mono mb-3">
                {step.number}
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">{step.title}</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
