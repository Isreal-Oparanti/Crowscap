import Link from "next/link";
import { BrandIcon } from "@/components/ui/brand-icon";

export const metadata = {
  title: "Privacy Policy — Crowscap",
  description: "Privacy policy and data protection practices for Crowscap.",
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[#f5f5f3] text-[#111111] antialiased">
      <header className="mx-auto flex w-full max-w-[900px] items-center justify-between px-6 py-8">
        <Link href="/" className="flex items-center gap-3">
          <BrandIcon className="size-8 text-[#111111]" />
          <span className="text-[16px] font-[880] tracking-tight">Crowscap AI</span>
        </Link>
        <Link
          href="/chat"
          className="rounded-full bg-[#111111] px-5 py-2 text-[12px] font-extrabold text-white transition hover:bg-[#282a2c]"
        >
          Chat
        </Link>
      </header>

      <main className="mx-auto max-w-[900px] px-6 pb-20 pt-4">
        <div className="rounded-[20px] border border-[#e2e4e5] bg-white p-8 md:p-12">
          <p className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-[#7d8184]">Privacy &amp; Security</p>
          <h1 className="mt-3 text-[32px] font-[850] tracking-tight md:text-[40px]">Privacy Policy</h1>
          <p className="mt-2 text-[13px] font-semibold text-[#7c8083]">Effective Date: February 10, 2026</p>

          <div className="mt-8 space-y-8 text-[14px] font-medium leading-7 text-[#3d4144]">
            <section>
              <h2 className="text-[18px] font-[800] text-[#111111]">1. Commitment to Privacy</h2>
              <p className="mt-2">
                At Crowscap (&quot;we&quot;, &quot;us&quot;, or &quot;our&quot;), we treat your memory as sacred and strictly private. Your saved notes, links, videos, PDFs, and personal thoughts belong to you. We do not sell your personal data or user content to third parties, advertisers, or data brokers.
              </p>
            </section>

            <section>
              <h2 className="text-[18px] font-[800] text-[#111111]">2. Information We Collect</h2>
              <p className="mt-2">To provide our memory intelligence services, we collect:</p>
              <ul className="mt-2 list-disc space-y-1.5 pl-6 text-[#525659]">
                <li><strong>Account Information:</strong> Your email address and basic profile data provided during registration or Google sign-in.</li>
                <li><strong>User Content &amp; Memories:</strong> Text notes, saved links, YouTube URLs, PDFs, and reasons you attach to saved items.</li>
                <li><strong>Usage &amp; Interaction Data:</strong> Information about feature usage, recall interactions, and search queries strictly to improve app functionality.</li>
              </ul>
            </section>

            <section>
              <h2 className="text-[18px] font-[800] text-[#111111]">3. How We Use Your Data</h2>
              <p className="mt-2">Your information is used exclusively to:</p>
              <ul className="mt-2 list-disc space-y-1.5 pl-6 text-[#525659]">
                <li>Extract atomic memory cards, generate vector embeddings, and enable semantic concept search.</li>
                <li>Schedule spaced repetition check-ins on your Recall tab and trigger notification nudges.</li>
                <li>Synthesize belief audits across your saved sources.</li>
                <li>Maintain account security, authentication, and platform reliability.</li>
              </ul>
            </section>

            <section>
              <h2 className="text-[18px] font-[800] text-[#111111]">4. Data Security and Archiving</h2>
              <p className="mt-2">
                We implement industry-standard encryption in transit (HTTPS/TLS) and at rest to protect your memories against unauthorized access. You can archive any memory at any time to remove it from active search, recall, and audits, while preserving your original source.
              </p>
            </section>

            <section>
              <h2 className="text-[18px] font-[800] text-[#111111]">5. Third-Party Processors</h2>
              <p className="mt-2">
                We partner with trusted infrastructure providers (such as AWS and vector processing systems) solely to host, process, and secure your encrypted data. All service providers are bound by strict data protection agreements.
              </p>
            </section>

            <section>
              <h2 className="text-[18px] font-[800] text-[#111111]">6. Your Rights and Data Deletion</h2>
              <p className="mt-2">
                You have the right to export your saved memories or request complete deletion of your account and data at any time by contacting our support team at{" "}
                <a href="mailto:support@crowscap.xyz" className="font-bold text-[#111111] underline">
                  support@crowscap.xyz
                </a>.
              </p>
            </section>

            <section>
              <h2 className="text-[18px] font-[800] text-[#111111]">7. Contact Support</h2>
              <p className="mt-2">
                For privacy questions, account deletion requests, or general support, email us at{" "}
                <a href="mailto:support@crowscap.xyz" className="font-bold text-[#111111] underline">
                  support@crowscap.xyz
                </a>.
              </p>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
