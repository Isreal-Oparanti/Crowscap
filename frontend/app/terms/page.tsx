import Link from "next/link";
import { BrandIcon } from "@/components/ui/brand-icon";

export const metadata = {
  title: "Terms & Conditions — Crowscap",
  description: "Terms and conditions of service for Crowscap Memory Intelligence.",
};

export default function TermsPage() {
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
          <p className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-[#7d8184]">Legal Agreement</p>
          <h1 className="mt-3 text-[32px] font-[850] tracking-tight md:text-[40px]">Terms & Conditions</h1>
          <p className="mt-2 text-[13px] font-semibold text-[#7c8083]">Effective Date: February 10, 2026</p>

          <div className="mt-8 space-y-8 text-[14px] font-medium leading-7 text-[#3d4144]">
            <section>
              <h2 className="text-[18px] font-[800] text-[#111111]">1. Acceptance of Terms</h2>
              <p className="mt-2">
                By accessing, registering for, or using Crowscap (&quot;the Service&quot;), provided by Crowscap Inc., you agree to be bound by these Terms &amp; Conditions (&quot;Terms&quot;). If you do not agree to these Terms, please do not use the Service.
              </p>
            </section>

            <section>
              <h2 className="text-[18px] font-[800] text-[#111111]">2. Description of Service</h2>
              <p className="mt-2">
                Crowscap is a personal memory intelligence platform that allows users to capture, organize, search, and recall learning content, web links, notes, documents, and videos. The Service utilizes artificial intelligence and natural language processing to extract atomic memory cards and schedule resurfacing nudges.
              </p>
            </section>

            <section>
              <h2 className="text-[18px] font-[800] text-[#111111]">3. User Accounts and Content Ownership</h2>
              <p className="mt-2">
                You retain full ownership of all data, notes, sources, and content that you submit to Crowscap. By uploading content, you grant Crowscap a limited, non-exclusive, world-wide license strictly necessary to process, index, format, store, and retrieve your memories for your personal use.
              </p>
              <p className="mt-2">
                You are responsible for maintaining the confidentiality of your account credentials and for all activities occurring under your account.
              </p>
            </section>

            <section>
              <h2 className="text-[18px] font-[800] text-[#111111]">4. Acceptable Use and Restrictions</h2>
              <p className="mt-2">You agree not to:</p>
              <ul className="mt-2 list-disc space-y-1.5 pl-6 text-[#525659]">
                <li>Use the Service for any unlawful purpose or in violation of any local, state, or international laws.</li>
                <li>Attempt to gain unauthorized access to Crowscap servers, database systems, or user accounts.</li>
                <li>Reverse-engineer, decompile, or disassemble any aspect of the Service.</li>
                <li>Upload malicious code, viruses, or content designed to harm or interrupt system integrity.</li>
              </ul>
            </section>

            <section>
              <h2 className="text-[18px] font-[800] text-[#111111]">5. AI Insights Disclaimer</h2>
              <p className="mt-2">
                Crowscap uses artificial intelligence to generate summaries, memory extractions, search results, and belief audits. While we strive for precision, AI-generated outputs are provided for informational and personal learning purposes only. Crowscap does not provide professional, legal, financial, or medical advice.
              </p>
            </section>

            <section>
              <h2 className="text-[18px] font-[800] text-[#111111]">6. Limitation of Liability</h2>
              <p className="mt-2">
                To the maximum extent permitted by law, Crowscap shall not be liable for any indirect, incidental, special, consequential, or punitive damages, or any loss of data, use, or goodwill resulting from your access to or inability to access the Service.
              </p>
            </section>

            <section>
              <h2 className="text-[18px] font-[800] text-[#111111]">7. Contact Support</h2>
              <p className="mt-2">
                If you have questions regarding these Terms &amp; Conditions or need support, please contact us at{" "}
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
