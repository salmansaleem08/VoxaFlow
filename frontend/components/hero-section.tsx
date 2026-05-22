"use client"

import React from "react"
import { ArrowRight, Sparkles, Zap, Shield } from "lucide-react"
import { Button } from "@/components/ui/button"

export function HeroSection() {
  return (
    <section className="relative min-h-screen gradient-hero flex flex-col items-center justify-center overflow-hidden px-4 pt-16 pb-20">
      {/* Background grid */}
      <div
        className="absolute inset-0 opacity-[0.04] pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.8) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.8) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />

      {/* Glow orb */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-primary/10 blur-[120px] pointer-events-none" />

      <div className="relative z-10 max-w-5xl mx-auto text-center space-y-8">
        {/* Announcement badge */}
        <div className="animate-fade-in flex justify-center">
          <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/15 border border-primary/25 text-primary text-sm font-medium">
            <Sparkles className="size-3.5" />
            Powered by Gemini AI + Whisper STT
          </span>
        </div>

        {/* Headline */}
        <div className="animate-fade-in delay-100 space-y-4">
          <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold text-white leading-[1.05] tracking-tight">
            Voice AI That{" "}
            <span className="gradient-text">Converts</span>
            <br />
            Every Conversation
          </h1>
          <p className="max-w-2xl mx-auto text-lg sm:text-xl text-white/60 leading-relaxed">
            VoxaFlow deploys intelligent AI voice agents to handle outbound
            appointment reminders, lead qualification, and customer outreach —
            automatically, at scale, with human-like conversations.
          </p>
        </div>

        {/* CTAs */}
        <div className="animate-fade-in delay-200 flex flex-col sm:flex-row gap-4 justify-center">
          <a href="#launch-call">
            <Button size="xl" className="glow-primary-sm group w-full sm:w-auto">
              Launch Your First Call
              <ArrowRight className="size-5 group-hover:translate-x-0.5 transition-transform" />
            </Button>
          </a>
          <a href="#how-it-works">
            <Button
              size="xl"
              variant="outline"
              className="w-full sm:w-auto border-white/20 text-white hover:bg-white/10 hover:text-white bg-transparent dark:bg-transparent dark:border-white/20 dark:hover:bg-white/10"
            >
              See How It Works
            </Button>
          </a>
        </div>

        {/* Trust indicators */}
        <div className="animate-fade-in delay-300 flex flex-wrap justify-center gap-6 pt-2">
          {[
            { icon: Zap,     label: "Real-time AI responses" },
            { icon: Shield,  label: "Enterprise-grade security" },
            { icon: Sparkles,label: "Context-aware conversations" },
          ].map(({ icon: Icon, label }) => (
            <div key={label} className="flex items-center gap-2 text-white/50 text-sm">
              <Icon className="size-4 text-primary" />
              {label}
            </div>
          ))}
        </div>

        {/* Stats row */}
        <div className="animate-fade-in delay-400 grid grid-cols-3 max-w-2xl mx-auto mt-12 rounded-2xl overflow-hidden border border-white/10">
          {[
            { value: "10M+", label: "Calls Handled" },
            { value: "98%",  label: "Transcription Accuracy" },
            { value: "60%",  label: "Cost Reduction" },
          ].map(({ value, label }, i) => (
            <div
              key={label}
              className={`bg-white/5 py-6 px-4 text-center hover:bg-white/10 transition-colors ${
                i < 2 ? "border-r border-white/10" : ""
              }`}
            >
              <div className="text-3xl font-bold text-white">{value}</div>
              <div className="text-sm text-white/50 mt-1">{label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
