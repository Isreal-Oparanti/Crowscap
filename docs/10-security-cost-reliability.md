# Security, Cost, and Reliability

## Security Priorities

The link capture system invites arbitrary internet input into the backend. Treat extraction as untrusted.

## SSRF Protection

Block:
- `localhost`
- `127.0.0.0/8`
- `::1`
- private IPv4 ranges: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
- link-local ranges: `169.254.0.0/16`
- cloud metadata endpoints such as `169.254.169.254`
- non-HTTP/HTTPS schemes
- redirects to blocked destinations

Rules:
- Validate the original URL.
- Resolve DNS.
- Validate resolved IP.
- Validate every redirect.
- Enforce max redirects.
- Enforce max content length.
- Enforce timeouts.

## File Upload Safety

Rules:
- Limit file size.
- Accept only allowed MIME types for MVP.
- Store uploads outside the executable app directory.
- Generate server-side object names.
- Scan or reject suspicious files before processing when available.
- Never execute uploaded files.

## Capture Content Guardrails

All capture paths flow through the same pre-storage guardrail before extraction,
embedding, duplicate lookup, and database persistence. This currently covers text
captures, mixed chat captures, URL/article text, YouTube transcripts, and PDF
extracted text.

Reject before saving:
- password-like secrets, API keys, bearer tokens, refresh tokens, client secrets,
  and private keys.
- credit card numbers that pass Luhn validation.
- explicit bank/account-number style financial details.
- private patient-record style medical details such as MRN, DOB, patient name,
  diagnosis lines, prescriptions, or lab results tied to a person.
- obvious operational harmful/illegal instruction phrases.

Mask before saving:
- email addresses -> `[email]`
- phone numbers -> `[phone number]`
- government ID labels -> `[government id]`
- home/residential address labels -> `[address]`

Important boundary: Crowscap should not reject public health, medical research,
or policy content just because the topic is health-related. The blocker is
private patient-style information, not legitimate public knowledge.

These guardrails are deterministic and intentionally cheap. They are not a full
moderation system. A later production hardening pass can add provider-level
classification for hate/violence/illegal content, but the deterministic layer is
the first line of defense because it does not add model latency or fail closed
when the model provider is unavailable.

## AI Safety and Output Handling

Qwen Cloud applies automatic moderation to API requests and outputs. The app still needs its own graceful error handling.

Rules:
- Catch moderation and IP-infringement style errors.
- Do not show raw provider errors to users.
- Validate every model response with Pydantic.
- Store prompts and outputs only where safe and useful for debugging.
- Avoid copying long copyrighted source text into user-visible outputs.

## Cost Controls

Qwen Cloud cost guidance includes:
- Use fewer resources per task.
- Keep prompts lean.
- Match model to task complexity.
- Consider batch calling for non-real-time work.
- Use context cache when repeated prefixes make sense.

Project-specific controls:
- Clean content before Qwen calls.
- Do not send raw HTML.
- Chunk long documents.
- Deduplicate repeated chunks and memory atoms.
- Cache URL extraction by normalized URL and content hash.
- Use fast model for classification and JSON repair.
- Use stronger model for audits, tension reasoning, and difficult synthesis.
- Store token estimates per job.
- Use Qwen structured output for extraction in non-thinking mode first; use a repair pass instead of trusting malformed or schema-invalid JSON.

## Reliability

Every long-running step should be retryable.

Chat reliability has an extra rule: conversational follow-ups must resolve
against current application state before they are sent to model-based routing.
For example, if Crowscap has just asked whether to save a pasted link, a reply
such as "yes please" confirms that pending link. It must not be treated as new
text to extract. Short acknowledgements without a pending action should remain
conversation and should never become accidental memories.

Natural language around pending actions should be semantic, not limited to one
exact phrase. Crowscap passes pending state into the chat router so replies like
"sure, handle that video" or "leave it" can be interpreted against the active
link. The deterministic checks are only the fast path and safety rail; they do
not replace model-based intent understanding. If the message is ambiguous, the
safe result is a clarification, not a crash or accidental capture.

All chat failures should return JSON with a user-safe explanation. Internal
Pydantic validation errors, provider failures, and extraction errors should not
leak raw stack traces or plain-text 500 responses to the frontend.

Retryable:
- transient network errors.
- Qwen rate limit or timeout.
- temporary extractor timeout.
- Redis/DB transient failure.

Not automatically retryable:
- unsafe URL.
- unsupported file type.
- paywalled content.
- transcript missing.
- malformed user input.

## Observability

Log:
- capture_id
- job_id
- user_id hash or internal ID
- processing step
- extraction method
- token estimates
- model name
- duration
- failure category

Do not log:
- API keys.
- raw private user content in production logs.
- signed URLs.
- secrets from environment variables.

Metrics:
- captures processed.
- extraction success rate.
- average processing time.
- Qwen call latency.
- token usage estimate.
- failed validation count.
- relation detection count.
- recall completion rate.
- audit generation time.

## Rate Limits

Production API limits:
- `POST /api/v1/captures/*`: 20 requests per minute per authenticated user.
- `POST /api/v1/chat`: 30 requests per minute per authenticated user.
- `POST /api/v1/search`: 60 requests per minute per authenticated user.

The limiter is in-memory for the MVP and is active outside local development.
This is enough to protect Qwen credits during judging and early deployment. A
multi-instance deployment should move the buckets to Redis or another shared
store.

Other MVP limits:
- max file size.
- max URL fetch size.
- max Qwen calls per capture.
- max chunks per capture.

## Privacy

User data includes saved links, notes, extracted content, and inferred knowledge. Treat it as sensitive.

Requirements before public release:
- data export.
- data deletion.
- privacy policy.
- clear statement of AI provider usage.
- no public sharing by default.
