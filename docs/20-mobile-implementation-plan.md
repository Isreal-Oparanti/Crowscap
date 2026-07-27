# Crowscap Mobile Implementation Plan

## Why Mobile Now

Crowscap should not depend on the user reopening a web app every time they want to save something. The core product behavior happens in the flow of daily learning: a user sees a YouTube video, article, WhatsApp message, PDF, or note, then wants to send it somewhere before the thought disappears.

A native mobile app gives Crowscap the right surface:

- Share into Crowscap from other apps.
- Receive real push notifications for reminders and recall.
- Open directly into the right memory, reminder, or capture flow.
- Feel like a persistent memory companion instead of a website the user has to remember to visit.

The web app remains useful for desktop work, but mobile should become the primary capture and recall surface.

## Product Goal

Build a lean React Native version of Crowscap that lets users:

- Sign in with Google.
- Save links, notes, videos, PDFs, and thoughts quickly.
- Share content into Crowscap from other apps.
- Search recent and saved memories.
- Receive reminders and recall nudges through native push notifications.
- Open notifications directly into the relevant memory or reminder.

This should be a thin mobile client over the existing Crowscap Python backend. Do not rebuild the intelligence layer in the mobile app, and do not introduce a second backend.

The backend remains the source of truth for users, memories, sources, captures, recalls, reminders, search, preferences, notifications, and Qwen calls. The mobile app is only a new client surface.

## Recommended Stack

- Expo React Native
- Expo Router
- TypeScript
- EAS Build
- Expo Notifications
- Expo SecureStore
- Expo AuthSession
- Expo Document Picker
- Expo Linking

Do not add Firebase, Supabase, Express, NestJS, or a separate mobile backend. If a mobile-only integration gap appears, add the smallest adapter inside the existing FastAPI backend after confirming the gap.

Official references:

- Expo EAS Build: https://docs.expo.dev/build/setup/
- Expo app distribution: https://docs.expo.dev/distribution/introduction/
- Expo push notifications: https://docs.expo.dev/push-notifications/overview/
- Expo notification sending: https://docs.expo.dev/push-notifications/sending-notifications/
- Google Play Console registration: https://support.google.com/googleplay/android-developer/answer/6112435
- Apple Developer Program: https://developer.apple.com/programs/enroll/
- TestFlight: https://developer.apple.com/testflight/

## App Identity

Use:

- App name: Crowscap
- Android package name: `com.crowscap.app`
- iOS bundle ID: `com.crowscap.app`

Use the existing Crowscap logo asset. Do not redraw or reinterpret the logo. Resize/crop only as needed for app icon, splash screen, and in-app usage.

## Core Screens

### 1. Login

Purpose:

- Authenticate the user with Google.
- Create or recover their Crowscap workspace.
- Store the backend access token securely.

Requirements:

- Use Google sign-in through mobile OAuth.
- Send the Google identity token to the backend.
- Store returned Crowscap token in SecureStore.
- Never store access tokens in AsyncStorage.

### 2. Capture / Chat

Purpose:

- Main app screen.
- Let the user save or ask about their knowledge.

Requirements:

- Text input for notes, questions, and links.
- Support pasted URLs.
- Support uploaded PDFs or documents where possible.
- Show memory receipts.
- Show extraction state clearly:
  - `Saved`
  - `Getting details`
  - `Details attached`
  - `Saved as reference`
  - `Could not read source`
- Do not block the UI while extraction runs.

Important behavior:

- A link should be saved immediately as a reference.
- If the user adds intent, preserve the intent as context.
- Extraction should run in the background and attach richer memory cards later.
- If extraction fails, keep the reference and explain honestly.

### 3. Recall

Purpose:

- Show due recalls and reminders in a mobile-native way.

Requirements:

- List due items first.
- Use a recall icon for knowledge recalls.
- Use a bell icon for reminders.
- Tapping an item opens a detail view.
- Reminder actions:
  - Done
  - Snooze
- Recall actions:
  - Still useful
  - I used it
  - Not now
  - Review deeper

Mobile rule:

Do not copy the desktop right-sidebar recall design. On mobile, recall should behave like a notification inbox: list first, details after tap.

### 4. Search / Memory

Purpose:

- Let the user find and inspect what they saved.

Requirements:

- Search bar at the top.
- Recent memories below the search bar.
- Full-row memory list, not cramped cards.
- Pagination or infinite loading.
- Archive/delete action.
- Open memory detail.

### 5. Settings

Purpose:

- Manage account and permissions.

Requirements:

- Google account identity.
- Logout.
- Notification permission status.
- Enable/disable reminders.
- Enable/disable recall nudges.
- Show app version.

## Native Share Flow

This is the most important mobile feature.

Target user flow:

1. User sees a link, video, article, or note in another app.
2. User taps Share.
3. User selects Crowscap.
4. Crowscap opens with the shared content.
5. User can add a short reason, or save immediately.
6. Crowscap stores the reference immediately.
7. Backend extraction runs in the background.

Expected examples:

- YouTube video shared into Crowscap.
- Browser article shared into Crowscap.
- WhatsApp text copied/shared into Crowscap.
- PDF shared into Crowscap.
- Plain text shared into Crowscap.

If a source cannot be read:

- Save the URL/reference.
- Preserve user intent if provided.
- Say clearly that Crowscap saved the reference but could not inspect the content.

Do not pretend the app read a source it could not read.

## Push Notifications

Push notifications are required for the real recall/reminder loop.

Use Expo Push Notifications first because it is the fastest reliable path for Android and iOS.

Notification types:

- Reminder due
- Memory ready for recall
- Background extraction complete
- Optional: source could not be read

Notification behavior:

- Tapping a reminder opens the reminder detail.
- Tapping a recall opens the recall detail.
- Tapping an extraction-complete notification opens the memory receipt/source detail.

Rules:

- Ask for notification permission only after login.
- Explain the value before asking.
- Do not spam the user.
- Do not notify for every background extraction unless the source was user-important or explicitly saved for later.

## Existing Backend Contract

The mobile app should call the existing FastAPI backend. In this document, "endpoint" means an API route already served by the Python backend, not a new service.

Base URL:

```text
https://api.crowscap.xyz/api/v1
```

Current useful routes:

```http
POST /api/v1/chat
POST /api/v1/chat/pdf
POST /api/v1/captures/text
POST /api/v1/captures/url
POST /api/v1/captures/pdf
POST /api/v1/jobs/captures/url
GET /api/v1/jobs/{job_id}
GET /api/v1/recalls/due
POST /api/v1/recalls/reminders/{reminder_id}/complete
POST /api/v1/recalls/reminders/{reminder_id}/snooze
POST /api/v1/recalls/{memory_id}/quick
POST /api/v1/recalls/{memory_id}/answer
GET /api/v1/memories/recent
POST /api/v1/search
POST /api/v1/memories/{id}/archive
POST /api/v1/memories/{id}/restore
GET /api/v1/sources/{source_id}
GET /api/v1/preferences/me
GET /api/v1/notifications/current
GET /api/v1/notifications/stream
```

### Backend Change Policy

For the first mobile implementation, Gemini should not rewrite backend logic. The goal is to build `/mobile` as a client over the existing API.

If Gemini finds an API gap, it should document the gap and keep going with the mobile shell. It should not invent a new backend or embed secrets into the app.

Important:

- The existing backend auth model trusts requests from the Next.js proxy using internal headers.
- A native app must not contain `CROWSCAP_PROXY_SECRET`.
- For production native login, the correct fix is a small auth adapter inside the existing FastAPI backend, not a second backend.

Possible future adapter:

```http
POST /api/v1/auth/google/mobile
```

Purpose:

- Accept Google `id_token`.
- Verify token server-side.
- Create or update user.
- Return a Crowscap mobile session token.

Possible future native push adapter:

```http
POST /api/v1/notifications/mobile/subscribe
DELETE /api/v1/notifications/mobile/subscribe
```

Purpose:

- Store Expo push token or platform-native push token.
- Associate token with the current user and device.
- Allow multiple devices per user.
- Mark inactive tokens when delivery fails.

These adapters are additive. They do not replace the existing backend, database, memory pipeline, or web app API contract.

Reminder worker:

- Find due reminders.
- Send push at the correct time.
- Avoid duplicate sends.
- Mark delivery attempts.

Recall worker:

- Select due memory using recall score, recency, and current preference signals.
- Send at the user's preferred recall time when available.
- Avoid sending too many recall notifications.

## Data Model Additions

Do not create these until native push delivery is actively being implemented. They are listed so the design is clear, not because the first mobile branch must add them immediately.

Possible future table:

```text
mobile_push_subscriptions
- id
- user_id
- expo_push_token
- platform
- device_id
- enabled
- last_seen_at
- last_error
- created_at
- updated_at

notification_deliveries
- id
- user_id
- target_type
- target_id
- push_token_id
- status
- error
- sent_at
- opened_at
- created_at
```

Possible future capture fields if extraction status is not already tracked:

```text
captures
- extraction_status
- extraction_error
- extraction_started_at
- extraction_completed_at
```

Possible statuses:

- `reference_saved`
- `extracting`
- `extracted`
- `unreadable`
- `failed_retryable`
- `failed_final`

## Error Handling

Mobile must fail gracefully.

Required states:

- No internet connection.
- Backend unavailable.
- Login failed.
- Source saved but extraction failed.
- Push permission denied.
- Push token registration failed.
- Reminder action failed.
- Search failed.

User-facing tone should be calm and specific:

- `You're offline. I will try again when your connection is back.`
- `I saved the link, but I could not read the content yet.`
- `The reminder was not updated. Try again in a moment.`
- `Notifications are off. You can still use Crowscap, but reminders will not reach your phone.`

## Build Phases

### Phase 1: Mobile Shell

- Create `/mobile` Expo app.
- Add app icon and splash screen.
- Set app name and bundle identifiers.
- Add navigation with Expo Router.
- Add login screen.
- Add authenticated app shell.

### Phase 2: Auth And API Client

- Add API client pointed at the existing FastAPI backend.
- Add secure token storage boundary.
- Do not put `CROWSCAP_PROXY_SECRET` in the app.
- If mobile auth is not available yet, keep auth as a clearly marked blocker instead of building an insecure shortcut.
- Add Google mobile sign-in only when the backend has a safe mobile token exchange.
- Store token in SecureStore.
- Add typed API client.
- Add authenticated request wrapper.
- Add logout.

### Phase 3: Capture

- Add chat/capture screen.
- Send messages to backend.
- Render assistant replies.
- Render memory receipts.
- Add loading states for:
  - Capturing
  - Getting details
  - Organizing memory
  - Saving

### Phase 4: Share Into Crowscap

- Configure Android share intent.
- Configure iOS share handling if available within Expo/EAS constraints.
- Add shared-content route.
- Pre-fill shared text/link.
- Let user save with optional reason.

### Phase 5: Recall And Search

- Build recall list.
- Build reminder/recall detail.
- Build recent memories.
- Build search.
- Add archive/delete action.

### Phase 6: Push Notifications

- Ask permission after login.
- Register Expo push token after native push backend support exists.
- Store push token through the existing Python backend, not a separate push backend.
- Add notification tap deep links.
- Add backend delivery worker.
- Test reminder delivery.
- Test recall delivery.

### Phase 7: Distribution

- Create EAS build profiles.
- Build Android APK for direct testing.
- Build Android AAB for Play Console.
- Create Play Console internal test release.
- Prepare Apple Developer account.
- Create iOS build.
- Submit to TestFlight.

## Fastest Testable Milestones

### Milestone 1

Android APK that can log in and send chat/capture requests.

### Milestone 2

Android APK that can receive shared links and save them.

### Milestone 3

Android APK that receives a push reminder and opens the correct screen.

### Milestone 4

Play Console internal testing link.

### Milestone 5

iOS TestFlight build.

## Store Readiness Checklist

Android:

- Google Play Developer account.
- App icon.
- Feature graphic.
- Screenshots.
- Privacy policy.
- App description.
- Content rating.
- Data safety form.
- Signed AAB from EAS.
- Internal testing release.

iOS:

- Apple Developer account.
- Bundle ID.
- App icon.
- Screenshots.
- Privacy policy.
- App privacy answers.
- TestFlight build.
- External testing review if using public TestFlight link.

## Gemini Starting Prompt

Use this prompt to start implementation:

```md
Create a new Expo React Native mobile app for Crowscap inside `/mobile`.

Crowscap is a private memory intelligence app. Users save links, notes, PDFs, videos, and thoughts. The backend turns them into source-aware memories, recalls them later, and supports search, reminders, and chat.

Use:
- Expo React Native
- TypeScript
- Expo Router
- Expo SecureStore
- Expo AuthSession
- Expo Notifications
- Expo Document Picker
- Expo Linking
- EAS Build

Do not rebuild backend intelligence in the app. Use the existing FastAPI backend.
Do not create a second backend.
Do not embed `CROWSCAP_PROXY_SECRET` in the mobile app.
If a safe mobile auth route is missing, mark it as a backend integration gap instead of working around it insecurely.

Core screens:
1. Login
2. Capture / Chat
3. Recall
4. Search / Memory
5. Settings

Requirements:
- Google login.
- Use the existing Crowscap Python backend as the only API backend.
- For production mobile auth, use a safe backend token exchange. If `POST /api/v1/auth/google/mobile` does not exist yet, document that as the one backend gap instead of inventing a separate backend.
- Store Crowscap access token in SecureStore.
- Attach Authorization bearer token to API calls.
- Register Expo push token after login only when the existing Python backend has native push-token support.
- Support sharing text and links into Crowscap from other apps.
- Save shared links immediately as references.
- Show extraction state while backend gets details.
- Render memory receipts.
- Build mobile-first recall list and recall detail.
- Build search with recent memories.
- Allow archiving memories.
- Use the existing Crowscap logo without redrawing it.
- Keep design serious, minimal, black and white, with restrained accent color.

Start with Android first, but keep the project iOS-compatible.
```

## Key Product Principle

The mobile app should make saving effortless.

The user should not have to think:

> Where do I put this so I remember it later?

They should simply share it to Crowscap.

That is the mobile product.
