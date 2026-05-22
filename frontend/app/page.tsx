"use client"

import React, { useState } from "react"
import { Navbar } from "@/components/navbar"
import { HeroSection } from "@/components/hero-section"
import { FeaturesSection, HowItWorksSection } from "@/components/features-section"
import { CallForm } from "@/components/call-form"
import { CallStatus } from "@/components/call-status"
import { Phone, Twitter, Linkedin, Github } from "lucide-react"

const CURRENT_YEAR = new Date().getFullYear()

export default function Home() {
  const [activeCallId, setActiveCallId] = useState<string | null>(null)

  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Navbar />

      {/* Hero */}
      <HeroSection />

      {/* How it works */}
      <HowItWorksSection />

      {/* Features */}
      <FeaturesSection />

      {/* Use Cases */}
      <section id="use-cases" className="py-24 px-4 bg-secondary text-secondary-foreground">
        <div className="max-w-6xl mx-auto">
          <div className="text-center space-y-4 mb-14">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/20 border border-primary/30 text-primary text-sm font-medium">
              Use Cases
            </span>
            <h2 className="text-4xl sm:text-5xl font-bold text-white">
              Built for every industry
            </h2>
            <p className="max-w-xl mx-auto text-white/55 text-lg">
              VoxaFlow adapts to your vertical with configurable agent personas and conversation flows.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              {
                title: "Healthcare",
                desc: "Appointment reminders, prescription refill notifications, and post-visit follow-ups.",
                emoji: "🏥",
              },
              {
                title: "Sales",
                desc: "Lead qualification, demo scheduling, and pipeline warm-up at scale.",
                emoji: "📈",
              },
              {
                title: "Finance",
                desc: "Payment reminders, account verifications, and fraud alert confirmations.",
                emoji: "💳",
              },
              {
                title: "Events",
                desc: "Registration confirmations, attendance reminders, and post-event surveys.",
                emoji: "🎫",
              },
            ].map((item) => (
              <div
                key={item.title}
                className="p-6 rounded-xl bg-white/5 border border-white/10 hover:bg-white/8 transition-colors"
              >
                <div className="text-3xl mb-3">{item.emoji}</div>
                <h3 className="font-semibold text-white mb-2">{item.title}</h3>
                <p className="text-sm text-white/55 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Launch Call ───────────────────────────────────────────────────────── */}
      <section id="launch-call" className="py-24 px-4 bg-background">
        <div className="max-w-3xl mx-auto">
          <div className="text-center space-y-4 mb-12">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-sm font-medium">
              Live Demo
            </span>
            <h2 className="text-4xl sm:text-5xl font-bold text-foreground">
              Launch your first{" "}
              <span className="gradient-text">AI call now</span>
            </h2>
            <p className="text-muted-foreground text-lg max-w-xl mx-auto">
              Enter a phone number, choose a scenario, and watch VoxaFlow&apos;s AI agent
              handle the entire conversation — in real time.
            </p>
          </div>

          {activeCallId ? (
            <CallStatus callId={activeCallId} onReset={() => setActiveCallId(null)} />
          ) : (
            <CallForm onCallInitiated={setActiveCallId} />
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-secondary text-secondary-foreground border-t border-white/10">
        <div className="max-w-7xl mx-auto px-4 py-12">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-12">
            {/* Brand */}
            <div className="md:col-span-2 space-y-4">
              <div className="flex items-center gap-2.5">
                <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary">
                  <Phone className="size-4 text-white" />
                </div>
                <span className="text-white font-bold text-xl">
                  Voxa<span className="text-primary">Flow</span>
                </span>
              </div>
              <p className="text-white/50 text-sm leading-relaxed max-w-sm">
                The most intelligent outbound voice AI platform. Automate conversations,
                capture outcomes, and scale your customer engagement — all without lifting
                the phone.
              </p>
              <div className="flex items-center gap-3">
                {[Twitter, Linkedin, Github].map((Icon, i) => (
                  <a
                    key={i}
                    href="#"
                    className="flex items-center justify-center w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 transition-colors text-white/60 hover:text-white"
                    aria-label="Social link"
                  >
                    <Icon className="size-4" />
                  </a>
                ))}
              </div>
            </div>

            {/* Links */}
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-white/80 uppercase tracking-wide">Platform</h4>
              <ul className="space-y-2">
                {["Features", "How It Works", "Use Cases", "Pricing"].map((item) => (
                  <li key={item}>
                    <a href="#" className="text-sm text-white/50 hover:text-white transition-colors">{item}</a>
                  </li>
                ))}
              </ul>
            </div>

            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-white/80 uppercase tracking-wide">Company</h4>
              <ul className="space-y-2">
                {["About", "Blog", "Careers", "Contact"].map((item) => (
                  <li key={item}>
                    <a href="#" className="text-sm text-white/50 hover:text-white transition-colors">{item}</a>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="border-t border-white/10 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
            {/* suppressHydrationWarning prevents React hydration mismatch on year */}
            <p className="text-white/40 text-sm" suppressHydrationWarning>
              © {CURRENT_YEAR} VoxaFlow, Inc. All rights reserved.
            </p>
            <div className="flex items-center gap-4">
              {["Privacy Policy", "Terms of Service", "Security"].map((item) => (
                <a key={item} href="#" className="text-xs text-white/40 hover:text-white/70 transition-colors">
                  {item}
                </a>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
