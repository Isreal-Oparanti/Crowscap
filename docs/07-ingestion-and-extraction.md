# Ingestion and Extraction

## Goal

Accept learning fragments from realistic sources without pretending the entire web is clean. Extraction must be reliable, secure, and honest about failures.

## MVP Input Types

1. Plain text paste.
2. Article/blog URL.
3. YouTube URL when transcript/captions are available and legally accessible.
4. PDF upload.
5. Manual note or book excerpt.

Later input types:
- Browser extension.
- Mobile share sheet.
- WhatsApp/Telegram bot.
- Kindle/Readwise import.
- Screenshot OCR.
- Voice note transcription.
- Ambient browser capture.

## Extraction Router

```text
Input -> Safety check -> Type detection -> Extractor -> Cleaner -> Chunker -> Qwen extraction
```

## URL Extraction Strategy

Chat UX rule:
- Save the link immediately as a reference, with the user's surrounding words
  kept as the reason when available.
- Queue readable URL extraction as a background job. The first response should
  never block on article parsing, YouTube transcript lookup, embeddings, or
  relationship scans.
- The receipt exposes enrichment state: queued/running, succeeded with memory
  cards, or failed with a safe explanation. This lets Crowscap preserve user
  intent first and attach extracted knowledge once it is actually available.

Static HTML:
- Use Trafilatura or Readability-style extraction.
- Fast and cheap.
- Works for many blogs, articles, documentation, and plain pages.

Dynamic JavaScript pages:
- Use Playwright fallback only when needed.
- Slower and more expensive.
- Enforce timeouts and resource limits.

YouTube:
- Save reliable video metadata first: title, channel, thumbnail, URL, and the
  user's reason for saving when present. Use the YouTube Data API when
  configured, otherwise fall back to YouTube oEmbed. This prevents a useful
  video link from becoming a dead reference just because captions are blocked.
- Prefer transcript/caption extraction where available. `yt-dlp` remains the
  transcript path, but it is not treated as the only source of truth because
  YouTube can challenge server-side clients with bot checks, cookies, or PO
  token requirements.
- The minimum transcript length is duration-aware. Regular videos require 100
  words; short-form videos (3 minutes or less, e.g. YouTube Shorts) require only
  25 words, since a legitimate Shorts transcript is often under 100 words.
  Rejecting those made the same URL succeed or fail unpredictably across
  accounts and attempts.
- For short-form videos, extraction is instructed to produce only the 1-3
  genuinely distinct ideas the content contains, never padded counts.
- If transcript extraction fails but metadata is available, create metadata-only
  memories grounded in the title, channel, description when available, and user
  intent. Do not imply the transcript or full video content was read.
- If no transcript or metadata exists, keep the URL as a reference and encourage
  the user to add a short reason.
- Speech-to-text can be a later feature if needed.

PDF:
- Use PyMuPDF or equivalent library.
- Extract text per page.
- Store page numbers for citations.
- Flag image-only PDFs as requiring OCR later.

Unsupported platforms:
- Instagram, TikTok, LinkedIn, X, and many social apps should not be promised for MVP.
- Accept pasted text or URL metadata first.
- Integrations can come later.

## Security Requirements

Never fetch arbitrary URLs blindly.

Block:
- localhost and loopback addresses.
- private IP ranges.
- link-local and metadata addresses such as `169.254.169.254`.
- non-HTTP/HTTPS protocols.
- suspicious redirects to blocked hosts.
- oversized downloads.
- unsupported file types.
- very long processing times.

Protections:
- Resolve DNS and validate resolved IP before fetch.
- Re-validate each redirect target.
- Limit redirect count.
- Limit response size.
- Set connection and read timeouts.
- Use an allowlist for special extractors when possible.
- Log failure categories, not secrets.

## Chunking

Chunk by semantic boundaries when possible:
- heading sections.
- paragraphs.
- PDF pages.
- transcript time ranges.

Avoid arbitrary fixed-size chunks unless necessary.

Each chunk should store:
- source ID.
- chunk index.
- text.
- token estimate.
- location metadata.
- extraction method.

## Token and Cost Strategy

Do not send raw HTML or boilerplate to Qwen.

Reduce cost by:
- extracting main content first.
- deduplicating repeated navigation/footer text.
- chunking long documents.
- batching small classification tasks where practical.
- using cheaper models for classification/repair.
- using stronger models only for audit/tension reasoning.
- caching identical URL extraction results.
- storing extracted text at capture time.

Qwen Cloud cost docs recommend using fewer resources per task, keeping prompts lean, matching model to task complexity, and considering batch calling or context cache where useful.

## Source Snapshots

Store extracted text at capture time.

Reason:
- A URL can change later.
- The user saved what they saw then.
- Memories need stable provenance.

## Extraction Failure UX

Failure is acceptable if it is clear and recoverable.

Example categories:
- blocked_by_site
- paywalled
- transcript_missing
- unsupported_content_type
- too_large
- unsafe_url
- timeout
- extraction_empty
- model_validation_failed

Each failure should suggest a fallback:
- paste the text manually.
- upload a PDF.
- add a transcript.
- retry later.
