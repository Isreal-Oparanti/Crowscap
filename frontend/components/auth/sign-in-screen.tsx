"use client";

import {
  ArrowRight,
  BrainCircuit,
  CheckCircle2,
  Cpu,
  Database,
  Globe,
  Key,
  Layers,
  LockKeyhole,
  Sparkles,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { signIn } from "next-auth/react";
import { useState } from "react";

export function SignInScreen() {
  const [isSigningIn, setIsSigningIn] = useState(false);
  const [showCredentials, setShowCredentials] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [credError, setCredError] = useState("");

  function handleGoogleSignIn() {
    setIsSigningIn(true);
    void signIn("google", { callbackUrl: "/" }).finally(() => {
      setIsSigningIn(false);
    });
  }

  async function handleCredentialsSignIn(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) {
      setCredError("Please enter both email/username and password.");
      return;
    }
    setIsSigningIn(true);
    setCredError("");
    const res = await signIn("credentials", {
      email,
      password,
      redirect: false,
      callbackUrl: "/",
    });
    if (res?.error) {
      setCredError("Invalid credentials");
      setIsSigningIn(false);
    } else if (res?.url) {
      window.location.href = res.url;
    } else {
      window.location.reload();
    }
  }

  async function handleDemoSignIn() {
    setIsSigningIn(true);
    const res = await signIn("credentials", {
      email: "yc@crowscap.xyz",
      password: "demo2026",
      redirect: false,
      callbackUrl: "/",
    });
    if (res?.url) {
      window.location.href = res.url;
    } else {
      window.location.reload();
    }
  }

  return (
    <main className="min-h-screen bg-[#090b0e] text-[#f0f3f5] font-sans antialiased selection:bg-[#2d7058] selection:text-white">
      {/* Top Background Glow Effects */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-[25%] left-1/2 -translate-x-1/2 size-[800px] rounded-full bg-radial from-[#1e4d3c]/30 via-[#0f281f]/10 to-transparent blur-[120px]" />
        <div className="absolute top-[40%] -left-[10%] size-[500px] rounded-full bg-radial from-[#1e2c4d]/20 to-transparent blur-[100px]" />
      </div>

      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
        {/* Navigation Bar */}
        <header className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-6 py-4 backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.37)]">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#2d7058] to-[#1a4435] text-white shadow-[0_0_20px_rgba(45,112,88,0.4)]">
              <BrainCircuit size={22} className="animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-black tracking-tight text-white">Crowscap</span>
                <span className="rounded-full bg-[#2d7058]/20 border border-[#2d7058]/40 px-2 py-0.5 text-[10px] font-bold text-[#4ade80]">
                  v1.0 MemoryAgent
                </span>
              </div>
              <p className="text-xs font-medium text-[#94a3b8]">
                Source-Aware Memory Intelligence
              </p>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-6 text-xs font-semibold text-[#94a3b8]">
            <a href="#features" className="hover:text-white transition">Capabilities</a>
            <a href="#architecture" className="hover:text-white transition">Architecture</a>
            <a href="#yc-review" className="text-[#4ade80] hover:underline flex items-center gap-1.5 font-bold">
              <Zap size={14} /> YC Demo
            </a>
          </div>

          <button
            type="button"
            onClick={handleDemoSignIn}
            disabled={isSigningIn}
            className="flex items-center gap-2 rounded-xl bg-[#2d7058] px-4 py-2 text-xs font-extrabold text-white shadow-[0_0_20px_rgba(45,112,88,0.3)] transition hover:bg-[#37886b] hover:shadow-[0_0_25px_rgba(45,112,88,0.5)] disabled:opacity-50"
          >
            <Sparkles size={14} />
            <span>YC Reviewer Login</span>
          </button>
        </header>

        {/* Hero Section */}
        <section className="mt-12 lg:mt-16 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-7 space-y-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-[#2d7058]/40 bg-[#2d7058]/10 px-3.5 py-1.5 text-xs font-bold text-[#4ade80]">
              <Cpu size={14} />
              <span>Qwen Cloud Structured Intelligence & Vector Engine</span>
            </div>

            <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-[1.08]">
              Turn what you save into{" "}
              <span className="bg-gradient-to-r from-[#4ade80] via-[#2dd4bf] to-[#38bdf8] bg-clip-text text-transparent">
                knowledge you can use.
              </span>
            </h1>

            <p className="text-base sm:text-lg text-[#94a3b8] leading-relaxed max-w-2xl font-medium">
              Crowscap processes scattered notes, web links, YouTube videos, PDFs, and conversations into private, source-aware atomic memory — with full auditability, belief synthesis, and contextual recall.
            </p>

            {/* YC Application Reviewer Credentials Banner */}
            <div id="yc-review" className="rounded-2xl border border-[#2d7058]/50 bg-gradient-to-br from-[#122b22] to-[#0c1c16] p-5 shadow-[0_0_30px_rgba(45,112,88,0.15)] relative overflow-hidden">
              <div className="absolute top-0 right-0 size-24 bg-radial from-[#4ade80]/20 to-transparent blur-xl pointer-events-none" />
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2 text-[#4ade80] font-extrabold text-xs tracking-wider uppercase">
                  <Zap size={15} />
                  <span>YC Application Reviewer Quick Access</span>
                </div>
                <span className="text-[10px] font-bold bg-[#2d7058] text-white px-2 py-0.5 rounded-md">
                  Pre-Seeded Demo
                </span>
              </div>
              <p className="text-xs text-[#cbd5e1] mb-4">
                Use 1-Click Demo Login to instantly access a pre-populated workspace with sample sources, memories, and audits.
              </p>
              
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={handleDemoSignIn}
                  disabled={isSigningIn}
                  className="flex-1 min-w-[200px] h-11 inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#2d7058] to-[#1e4d3c] text-white text-xs font-black shadow-[0_4px_20px_rgba(45,112,88,0.4)] transition hover:from-[#37886b] hover:to-[#26634d] disabled:opacity-50"
                >
                  <Zap size={16} />
                  <span>{isSigningIn ? "Signing In..." : "⚡ 1-Click YC Demo Login"}</span>
                  <ArrowRight size={15} />
                </button>

                <div className="flex items-center gap-2 text-[11px] font-mono bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-[#94a3b8]">
                  <Key size={13} className="text-[#4ade80]" />
                  <span>yc@crowscap.xyz</span>
                  <span className="text-white/20">|</span>
                  <span>demo2026</span>
                </div>
              </div>
            </div>

            {/* Standard Sign-In Options */}
            <div className="space-y-4 pt-2">
              <div className="flex flex-col sm:flex-row items-stretch gap-3">
                <button
                  type="button"
                  onClick={handleGoogleSignIn}
                  disabled={isSigningIn}
                  className="flex-1 h-12 inline-flex items-center justify-center gap-3 rounded-xl border border-white/15 bg-white/5 px-5 text-xs font-extrabold text-white transition hover:bg-white/10 hover:border-white/25 shadow-lg disabled:opacity-50"
                >
                  <span className="flex size-6 items-center justify-center rounded-full bg-white text-black text-xs font-black">
                    G
                  </span>
                  <span>{isSigningIn ? "Connecting..." : "Continue with Google"}</span>
                </button>

                <button
                  type="button"
                  onClick={() => setShowCredentials(!showCredentials)}
                  className="h-12 px-5 inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.02] text-xs font-bold text-[#cbd5e1] hover:bg-white/5 transition"
                >
                  <span>{showCredentials ? "Hide Form" : "Email / Password Login"}</span>
                </button>
              </div>

              {/* Expandable Credentials Form */}
              {showCredentials && (
                <form onSubmit={handleCredentialsSignIn} className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 space-y-4 backdrop-blur-md">
                  <div className="text-xs font-extrabold text-white flex items-center gap-2">
                    <LockKeyhole size={14} className="text-[#4ade80]" />
                    <span>Account Credentials Sign In</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[10px] font-bold uppercase text-[#94a3b8] mb-1">
                        Email or Username
                      </label>
                      <input
                        type="text"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="yc@crowscap.xyz"
                        className="w-full h-10 rounded-xl border border-white/10 bg-black/40 px-3 text-xs text-white placeholder-[#64748b] focus:outline-none focus:border-[#4ade80] transition"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold uppercase text-[#94a3b8] mb-1">
                        Password
                      </label>
                      <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full h-10 rounded-xl border border-white/10 bg-black/40 px-3 text-xs text-white placeholder-[#64748b] focus:outline-none focus:border-[#4ade80] transition"
                      />
                    </div>
                  </div>
                  {credError && <p className="text-xs font-semibold text-red-400">{credError}</p>}
                  <button
                    type="submit"
                    disabled={isSigningIn}
                    className="w-full h-10 rounded-xl bg-white text-black font-extrabold text-xs hover:bg-[#e2e8f0] transition disabled:opacity-50"
                  >
                    Sign In
                  </button>
                </form>
              )}

              <p className="text-xs text-[#64748b] flex items-center gap-2">
                <ShieldCheck size={14} className="text-[#2d7058]" />
                <span>Private by design. Memory partitions remain isolated per user identity.</span>
              </p>
            </div>
          </div>

          {/* Right Showcase Column: Live Product Preview Mockup */}
          <div className="lg:col-span-5">
            <div className="relative rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.07] to-white/[0.02] p-6 backdrop-blur-2xl shadow-[0_32px_96px_rgba(0,0,0,0.6)] space-y-6">
              {/* Product UI Header Mockup */}
              <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <div className="flex items-center gap-2">
                  <div className="size-3 rounded-full bg-red-500/80" />
                  <div className="size-3 rounded-full bg-yellow-500/80" />
                  <div className="size-3 rounded-full bg-green-500/80" />
                </div>
                <div className="text-[11px] font-mono text-[#64748b]">crowscap.xyz/memory-workspace</div>
              </div>

              {/* Sample Live Memory Atom Card */}
              <div className="space-y-3">
                <div className="text-[11px] font-bold text-[#94a3b8] uppercase tracking-wider flex items-center justify-between">
                  <span>Extracted Memory Atom</span>
                  <span className="text-[#4ade80]">Confidence: 98%</span>
                </div>
                <div className="rounded-xl border border-[#2d7058]/40 bg-[#122b22]/60 p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-extrabold uppercase text-[#4ade80] bg-[#2d7058]/30 px-2 py-0.5 rounded">
                      Core Principle
                    </span>
                    <span className="text-[10px] text-[#94a3b8]">Paul Graham Essay</span>
                  </div>
                  <p className="text-xs font-semibold text-white leading-relaxed">
                    "Unscalable manual recruitment of initial users builds the early feedback loop that defines product-market fit."
                  </p>
                </div>
              </div>

              {/* Belief Audit Preview */}
              <div className="space-y-3">
                <div className="text-[11px] font-bold text-[#94a3b8] uppercase tracking-wider flex items-center justify-between">
                  <span>Topic Audit: Product Retention</span>
                  <span className="text-[#38bdf8]">3 Sources Synthesized</span>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/40 p-4 space-y-2 text-xs text-[#cbd5e1]">
                  <div className="flex items-center gap-2 text-[#38bdf8] font-bold">
                    <CheckCircle2 size={14} />
                    <span>Cohort Flattening Criterion</span>
                  </div>
                  <p className="text-[11px] text-[#94a3b8]">
                    Saved sources agree: retention curves must flatten horizontally before attempting paid scaling.
                  </p>
                </div>
              </div>

              {/* MCP Live Stream Status */}
              <div className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.02] p-3 text-xs">
                <div className="flex items-center gap-2">
                  <div className="size-2 rounded-full bg-[#4ade80] animate-ping" />
                  <span className="font-semibold text-white">Agent MCP Server</span>
                </div>
                <span className="font-mono text-[11px] text-[#4ade80]">api.crowscap.xyz/mcp/sse</span>
              </div>
            </div>
          </div>
        </section>

        {/* Feature Grid Section */}
        <section id="features" className="mt-24 border-t border-white/10 pt-16">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <span className="text-xs font-extrabold uppercase tracking-widest text-[#4ade80]">
              Built for Intentional Learners & Founders
            </span>
            <h2 className="text-3xl font-extrabold text-white sm:text-4xl">
              Memory as a Lifecycle, Not a Folder.
            </h2>
            <p className="text-sm text-[#94a3b8]">
              Capture → Extract → Structure → Relate → Recall → Audit → Adapt
            </p>
          </div>

          <div className="mt-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 space-y-3 backdrop-blur-md hover:border-[#2d7058]/50 transition">
              <div className="size-10 rounded-xl bg-[#2d7058]/20 flex items-center justify-center text-[#4ade80]">
                <Cpu size={20} />
              </div>
              <h3 className="text-base font-bold text-white">Atomic Extraction</h3>
              <p className="text-xs text-[#94a3b8] leading-relaxed">
                Qwen Cloud extracts precise claims, definitions, and action items instead of burying information in raw note graveyards.
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 space-y-3 backdrop-blur-md hover:border-[#2d7058]/50 transition">
              <div className="size-10 rounded-xl bg-[#38bdf8]/20 flex items-center justify-center text-[#38bdf8]">
                <Globe size={20} />
              </div>
              <h3 className="text-base font-bold text-white">Source Provenance</h3>
              <p className="text-xs text-[#94a3b8] leading-relaxed">
                Every extracted memory retains clickable links, timestamps, and confidence metrics pointing directly back to original sources.
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 space-y-3 backdrop-blur-md hover:border-[#2d7058]/50 transition">
              <div className="size-10 rounded-xl bg-[#a855f7]/20 flex items-center justify-center text-[#a855f7]">
                <Layers size={20} />
              </div>
              <h3 className="text-base font-bold text-white">Belief Audits</h3>
              <p className="text-xs text-[#94a3b8] leading-relaxed">
                Ask "What do I seem to know about X?" to synthesize repeated advice, weak evidence, and unapplied principles.
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 space-y-3 backdrop-blur-md hover:border-[#2d7058]/50 transition">
              <div className="size-10 rounded-xl bg-[#f59e0b]/20 flex items-center justify-center text-[#f59e0b]">
                <Database size={20} />
              </div>
              <h3 className="text-base font-bold text-white">Agentic MCP / SSE</h3>
              <p className="text-xs text-[#94a3b8] leading-relaxed">
                Connect your memory memory engine directly to AI agents (Claude, Cursor, Qwen) via Model Context Protocol.
              </p>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="mt-24 border-t border-white/10 py-8 flex flex-col sm:flex-row items-center justify-between text-xs text-[#64748b] gap-4">
          <div className="flex items-center gap-2">
            <BrainCircuit size={16} className="text-[#4ade80]" />
            <span className="font-extrabold text-white">Crowscap</span>
            <span>© 2026. Built for Qwen Cloud MemoryAgent.</span>
          </div>
          <div className="flex items-center gap-6">
            <a href="https://api.crowscap.xyz/api/v1/health" target="_blank" rel="noreferrer" className="hover:text-white transition">Backend API Health</a>
            <a href="https://api.crowscap.xyz/mcp/sse" target="_blank" rel="noreferrer" className="hover:text-white transition">MCP Stream</a>
          </div>
        </footer>
      </div>
    </main>
  );
}
