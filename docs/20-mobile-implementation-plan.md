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
