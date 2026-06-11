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

MVP limits:
- max captures per user per hour.
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
