# Crowscap Mobile — Implementation Plan

## Overview

This document outlines the architecture, structure, and delivery plan for the Crowscap native mobile app, built with **Expo (React Native)** and **TypeScript**.

The mobile app is a native companion to the existing web product at `crowscap.xyz`. It shares the same FastAPI backend and the same API contract documented in `docs/09-api-contract.md`. It does not duplicate backend logic.

---

## Product Identity

### Mobile App Name
**Crowscap**

### App Brand Direction
The mobile app carries the same product identity as the web: clean, focused, dark-capable, intentional learner tooling. No gamification. No visual noise.

The icon and splash use the existing Crowscap crow-cap mark, extended with subtle motion on launch (a feather unfurl).

The typography and color tokens are shared with the web product in spirit but implemented natively using React Native's `StyleSheet` and a shared design token file (`src/theme/tokens.ts`).

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Framework | Expo SDK 54 | Native push, share-sheet, file picker, background tasks |
| Language | TypeScript (strict) | Matches the frontend codebase |
| Navigation | Expo Router v4 (file-based) | Consistent with Next.js mental model. Tab + stack routing |
| Auth | Expo Auth Session + Google OAuth | Native Google sign-in flow using `expo-auth-session` |
| Auth tokens | Expo Secure Store | Replaces NextAuth cookies. Stores access token + user session |
| API | Fetch + custom typed client | Mirrors `frontend/lib/api`. Calls `api.crowscap.xyz` directly |
| State | TanStack Query v5 | Cache, polling, background refresh |
| Sharing / Capture | Expo Share Intent (plugin) | Catches URLs and text shared from any app — core mobile value |
| Push Notifications | Expo Notifications + FCM/APNs | Native push for recalls and reminders |
| Styling | React Native StyleSheet + design tokens | No external styling library |
| Storage | Expo Secure Store + AsyncStorage | Tokens in Secure Store, non-sensitive cache in AsyncStorage |
| Icons | `@expo/vector-icons` (Lucide subset) | Matches Lucide icons used on web |
| Environment | `expo-constants` + Expo public env vars | `EXPO_PUBLIC_BACKEND_URL`, `EXPO_PUBLIC_GOOGLE_CLIENT_ID_WEB`, `EXPO_PUBLIC_GOOGLE_CLIENT_ID_IOS`, `EXPO_PUBLIC_GOOGLE_CLIENT_ID_ANDROID` |

---

## Auth Architecture

The mobile app does **not** use NextAuth or the Next.js proxy. Instead:

```
Native Google OAuth (expo-auth-session/providers/google)
  → Google ID token returned to app
  → POST /api/v1/auth/mobile-session  (NEW lightweight backend endpoint)
  → Backend validates Google ID token with Google's tokeninfo endpoint
  → Backend returns a signed short-lived session token (JWT)
  → App stores token in Expo Secure Store
  → Every API call sends: Authorization: Bearer <token>
  → Backend reads user identity from the JWT, not from proxy headers
```

This is separate from the web proxy header trust model. The backend already exposes `/api/v1/auth/mobile-session` for mobile sessions.

---

## Screens and Navigation

### Tab Structure (Bottom Tabs)

| Tab | Screen | Matches Web |
|---|---|---|
| Chat | Chat / Conversation | `/` (main chat) |
| Recall | Due recalls queue | `/recall` |
| Search | Semantic memory search | `/search` |
| Settings | Profile, preferences | `/settings` |

### Stack Screens (inside tabs or modal)

| Screen | Route | Description |
|---|---|---|
| Capture Sheet | `/(modals)/capture` | Full-screen modal: paste text, share URL, record intent |
| Memory Detail | `/(modals)/memory/[id]` | Full memory atom with source, relations, recall history |
| Capture Result | `/(modals)/capture-result` | Shows extracted memories after capture |
| Sign In | `/sign-in` | Google OAuth entry screen |

---

## Folder Structure

```text
mobile/
  app/                        ← Expo Router pages (file-based routes)
    _layout.tsx               ← Root layout, auth gate, tab navigator
    sign-in.tsx               ← Google sign-in screen
    (tabs)/
      _layout.tsx             ← Bottom tab bar
      index.tsx               ← Chat (main screen)
      recall.tsx              ← Due recalls
      search.tsx              ← Semantic memory search
      settings.tsx            ← Settings and profile
    (modals)/
      capture.tsx             ← Capture sheet (text paste / URL / share intent)
      capture-result.tsx      ← Memory extraction results
      memory/
        [id].tsx              ← Memory atom detail view

  src/
    api/                      ← Typed API client (mirrors frontend/lib/api)
      client.ts               ← Base fetch client with auth headers
      chat.ts
      captures.ts
      memories.ts
      recalls.ts
      search.ts
      audits.ts
      preferences.ts
      notifications.ts
      auth.ts                 ← /auth/mobile-session endpoint

    auth/
      google.ts               ← Google OAuth flow (expo-auth-session)
      session.ts              ← Session storage and token management (SecureStore)
      context.tsx             ← Auth context provider

    components/
      chat/
        ChatBubble.tsx
        ChatInput.tsx
        ChatThread.tsx
        MemoryReceipt.tsx
      memory/
        MemoryCard.tsx
        MemoryTypeBadge.tsx
        ConfidencePill.tsx
        SourceLink.tsx
        RelationRow.tsx
      recall/
        RecallCard.tsx
        RecallAnswerInput.tsx
        RecallFeedback.tsx
      search/
        SearchBar.tsx
        SearchResultCard.tsx
        RecentMemoryRow.tsx
      capture/
        CaptureInput.tsx
        IntentPicker.tsx
        ShareIntentHandler.tsx
      shell/
        TabBar.tsx
        Header.tsx
        LoadingState.tsx
        ErrorState.tsx
        EmptyState.tsx
      ui/
        Button.tsx
        Pill.tsx
        Card.tsx
        Divider.tsx
        MarkdownText.tsx

    theme/
      tokens.ts               ← Colors, spacing, typography, radii
      typography.ts
      shadows.ts

    hooks/
      useAuth.ts
      useCapture.ts
      useRecalls.ts
      useSearch.ts
      useChat.ts
      useShareIntent.ts

    utils/
      format.ts
      validation.ts

    types/
      api.ts                  ← API response types (mirrors frontend/lib/types)
      navigation.ts

    constants/
      routes.ts
      limits.ts

  assets/
    icon.png
    splash.png
    adaptive-icon.png
    fonts/
      Manrope-Variable.ttf

  plugins/
    withShareIntent.js

  app.json
  eas.json
  package.json
  tsconfig.json
  babel.config.js
  .env.example
  .gitignore
```

---

## Dependencies (to be installed)

### Core
```
expo@~52.0.0
react-native
react
typescript
```

### Navigation
```
expo-router@~4.0.0
@react-navigation/native
@react-navigation/bottom-tabs
react-native-screens
react-native-safe-area-context
```

### Auth
```
expo-auth-session
expo-crypto
expo-secure-store
```

### Notifications and Background
```
expo-notifications
expo-device
expo-constants
expo-linking
```

### Share Intent (Core Mobile Value)
```
expo-share-intent
```

### Storage and State
```
@tanstack/react-query@^5.0.0
@react-native-async-storage/async-storage
```

### UI
```
@expo/vector-icons
expo-font
expo-splash-screen
expo-status-bar
react-native-gesture-handler
react-native-reanimated
```

---

## Direct Android Distribution And Updates

Crowscap is not using the Play Store yet. The short-term distribution path is:

1. Build an Android APK with EAS internal distribution.
2. Host the APK on the existing Alibaba ECS backend domain.
3. Host a small version manifest beside the APK.
4. Let the app check that manifest on launch and foreground.
5. Use EAS Update for JavaScript and UI changes that do not require a native rebuild.

### Hosted Files

Use the existing ECS/Nginx backend:

```text
https://api.crowscap.xyz/downloads/version.json
https://api.crowscap.xyz/downloads/crowscap-latest.apk
```

The repository contains the manifest template at:

```text
deploy/downloads/version.json
```

Manifest shape:

```json
{
  "android": {
    "latestVersionCode": 1,
    "minimumVersionCode": 1,
    "versionName": "1.0.0",
    "apkUrl": "https://api.crowscap.xyz/downloads/crowscap-latest.apk",
    "notes": "Initial Android build.",
    "publishedAt": "2026-08-01T00:00:00Z"
  }
}
```

### Native Version Check

The mobile app must not show an update banner on every launch. It should:

1. Read the installed Android build number with `expo-application`.
2. Fetch `https://api.crowscap.xyz/downloads/version.json`.
3. Compare installed `versionCode` with `android.latestVersionCode`.
4. Show the native update banner only when `latestVersionCode` is greater.
5. Open `android.apkUrl` when the user taps Download.

This is implemented in:

```text
mobile/src/utils/updates.ts
mobile/src/components/shell/AppUpdatePrompt.tsx
mobile/app/_layout.tsx
```

The check fails quietly if the user is offline or the manifest cannot be reached. It should not block login, capture, recall, or search.

### EAS Update

EAS Update is for JavaScript, styling, copy, and API-flow fixes. It cannot change native capabilities such as permissions, native modules, package identifiers, notification configuration, or SDK-level changes.

Current channels:

```text
development -> development builds
preview     -> internal APKs shared with testers
production  -> future production builds
```

For a UI/API-only update after an APK is installed:

```bash
cd mobile
npx eas update --channel preview --message "Short description of the fix"
```

The app checks for OTA updates when launched or foregrounded. If a bundle is available, it downloads it and shows a restart prompt. It should not silently reload while a user is in the middle of chat, recall, or capture.

`mobile/app.json` sets `updates.checkAutomatically` to `NEVER` because Crowscap owns the update UX. The app calls `checkForUpdateAsync()` manually, fetches the bundle, then asks the user to restart.

## Notification And Resurfacing Rules

Notifications have two different jobs, and the backend treats them differently.

### Time-Critical Reminders

Reminders and deadlines are time-driven. If a reminder is due, it wins over a normal recall. Deadline language must include the actual urgency phrase when possible:

- `today`
- `tomorrow`
- `in 2 days`
- `on Aug 12`

Good example:

```text
Deadline tomorrow
You saved this grant link for tomorrow. Submit the application before the window closes.
```

Weak example:

```text
You saved this grant link for later. The page appears to close soon.
```

The second version is too soft because it hides the time pressure. The user should feel why this matters now.

### Normal Memory Recalls

Regular saved memories must not surface only because they are old. The backend creates an eligible pool from active memories whose `next_review_at` is due, then ranks them before choosing what to push.

The ranking combines:

- Recent context match from the user's latest chat and saved memories.
- Memory confidence.
- Source strength and source type.
- Whether the user saved it with an intent such as YC, launch, customer, grant, deadline, or build.
- Recall score, so weakly remembered ideas get refreshed.
- Overdue age, with a cap so very old memories do not dominate forever.
- Memory type, with actions, warnings, principles, and intentions weighted above plain references.

The delivery table is also part of resurfacing. A memory or reminder with a previously sent `web_push` event is skipped for that exact due cycle, so Crowscap does not keep pushing the same item while other due items wait.

### Copy Quality

Push copy must be grounded in saved facts. The model receives a small JSON context containing the reminder text, due phrase, source title, source type, saved intent, and memory content. It must not invent details, deadlines, or source claims.

Avoid generic marketing openers such as:

- `Discover how`
- `Explore`
- `Dive into`
- `Unlock`

Use the user's saved context instead:

```text
Your YC video is ready
You saved this video yesterday for your YC application. It explains the interview mistakes founders make when they cannot describe the product clearly.
```

### Expo Go Limitation

Expo Go does not support Android remote push notifications through `expo-notifications` after SDK 53. The app skips native notification initialization in Expo Go to avoid warning/error overlays. Native push should be tested in a Crowscap development build or preview APK.

### Native Push Registration

The installed Android app registers an Expo push token with the backend:

```text
POST /api/v1/notifications/push/native-token
```

The existing `push_subscriptions` table stores both subscription types:

- Browser/PWA Web Push subscriptions use a normal endpoint plus VAPID keys.
- Native Expo tokens use `provider=expo` in `metadata_json`.

The worker sends through the correct channel for each subscription. This lets the same reminder and recall selection logic power web, PWA, and the Android APK.

To build native Android push, Firebase/FCM must be configured in EAS:

1. Create a Firebase project.
2. Add an Android app with package `xyz.crowscap.app`.
3. Download `google-services.json`.
4. Place it at `mobile/google-services.json`.
5. Run `npx eas credentials`.
6. Select Android, then upload/configure the FCM V1 service account key.

Do not commit Firebase service account private keys. `google-services.json` is app config and may be present for Android builds, but private service account JSON belongs in EAS credentials.

### APK Build

For a shareable Android APK:

```bash
cd mobile
npx eas build -p android --profile preview
```

After the build finishes:

1. Download the APK from EAS.
2. Upload it to `/var/www/crowscap-downloads/crowscap-latest.apk` on ECS.
3. Bump `mobile/app.json` `expo.android.versionCode` for the next native build.
4. Update `/var/www/crowscap-downloads/version.json` with the same `latestVersionCode`.

Android users who install outside the Play Store must approve the installation. Future native APK updates also require user confirmation. EAS Update reduces how often that is needed by shipping most JS/UI fixes over the air.

### iOS Reality

Without an Apple Developer account, native iOS distribution is not practical. Until then, iOS users should use the web app. The native iOS path later is TestFlight or the App Store.

### Dev
```
@types/react
@types/react-native
eslint
prettier
```

---

## Backend Changes Required

The mobile app requires one new backend endpoint:

### POST /api/v1/auth/mobile-session

Validates a Google ID token obtained natively and returns a signed JWT for the mobile app.

**Request:**
```json
{
  "id_token": "<google_id_token_from_expo_auth_session>",
  "platform": "ios"
}
```

**Response:**
```json
{
  "token": "<signed_jwt>",
  "user_id": "g_...",
  "email": "user@gmail.com",
  "name": "Display Name",
  "image_url": "https://...",
  "expires_at": "2026-07-28T22:00:00Z"
}
```

All subsequent mobile API calls carry `Authorization: Bearer <token>`. The FastAPI auth middleware must be updated to accept this alongside the existing proxy-header path.

---

## Phased Delivery

### Phase 1 — Auth + Chat + Capture (Core Loop)
- Google sign-in
- Chat screen (send / receive / view action type)
- Text and URL capture modal
- Memory receipt card after capture
- Share intent handler (URL and text from other apps)

### Phase 2 — Recall + Search
- Due recalls queue and card UI
- Recall answer flow with LLM feedback
- Semantic memory search

### Phase 3 — Notifications + Background
- Push notification registration (FCM / APNs)
- Background recall reminders
- Badge count for due recalls

### Phase 4 — Memory Detail + Settings
- Memory atom detail view
- Source viewer and relation explorer
- Settings and notification preferences
- Data export placeholder

### Phase 5 — Polish + Store Submission
- App icon, splash screen, and onboarding
- App Store and Play Store assets
- EAS production build

---

## Open Questions

Current setup notes:

1. **Google OAuth client IDs** - Google sign-in needs a Web client ID plus platform client IDs. Use `EXPO_PUBLIC_GOOGLE_CLIENT_ID_WEB`, `EXPO_PUBLIC_GOOGLE_CLIENT_ID_IOS`, and `EXPO_PUBLIC_GOOGLE_CLIENT_ID_ANDROID` in the mobile app. The backend must also allow those audiences through `AUTH_GOOGLE_ID` or `GOOGLE_CLIENT_ID`, `GOOGLE_MOBILE_IOS_CLIENT_ID`, and `GOOGLE_MOBILE_ANDROID_CLIENT_ID`.
2. **Expo Go limitation** - Expo Go cannot reliably complete the secure Google flow. Use email code sign-in while testing in Expo Go, and use a Crowscap development build for Google sign-in and native notification testing.
3. **Email code delivery** - Backend email sign-in requires `RESEND_API_KEY` and a verified `CROWSCAP_EMAIL_FROM` sender. Without those values, production cannot send login codes.
4. **Backend JWT secret** - `CROWSCAP_MOBILE_JWT_SECRET` is needed on the backend for signing and verifying mobile session tokens.
