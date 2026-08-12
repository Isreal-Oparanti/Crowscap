# Expo EAS OTA Updates Troubleshooting & Deployment Guide

> **Quick Reference**: How to push Over-The-Air (OTA) JavaScript and UI updates directly to installed mobile apps without rebuilding APKs.

---

## 1. Core Architecture: Channels vs. Branches

In Expo EAS Updates, installed mobile builds **do not listen directly to git branches**. They listen to **Update Channels**.

In Crowscap's [`mobile/eas.json`](../mobile/eas.json):
* **Production APKs** use `"channel": "production"`
* **Preview APKs** use `"channel": "preview"`
* **Development Builds** use `"channel": "development"`

> ⚠️ **The #1 Trapping Point**: If you run `eas update` without specifying `--channel production`, EAS uploads the JS bundle to a default branch (e.g. `main`). Installed production APKs ignore `main` and report **"No updates found"**.

---

## 2. Correct Commands to Deploy OTA Updates

### To Update Installed Production APKs (Active Users)
Always target the `production` channel explicitly:

```powershell
cd mobile
$env:EAS_SKIP_AUTO_FINGERPRINT=1
npx eas-cli update --channel production --message "fix: description of your UI/JS changes"
```

### To Update Preview Builds
```powershell
cd mobile
$env:EAS_SKIP_AUTO_FINGERPRINT=1
npx eas-cli update --channel preview --message "fix: preview update description"
```

---

## 3. How to Verify Active Channels on EAS

Run this command at any time to inspect what branch each channel is pointing to:

```powershell
cd mobile
npx eas-cli channel:list
```

**Expected Output for Production**:
```text
Channel: production
Status: Active
Branches pointed at this channel:
  Branch: production
  Most recent update group: "fix: ..." (X minutes ago)
```

---

## 4. How Expo Loads OTA Updates on the Phone

Because Crowscap uses `"checkAutomatically": "ON_LOAD"` in `app.json`:

1. **Launch 1 (Background Download)**:
   - User opens the app.
   - Expo checks the server in the background and silently downloads the new bundle.
   - The app continues displaying the old UI so the user experience is uninterrupted.
2. **Force-Close (Swipe Away)**:
   - User force-closes (swipes away) Crowscap from recent apps.
3. **Launch 2 (Apply Update)**:
   - User opens Crowscap again.
   - Expo swaps out the cached bundle with the new update—the changes display immediately!

---

## 5. When to Use `eas update` vs. `eas build`

| Change Type | Use `eas update` (OTA) | Use `eas build` (New APK) |
| :--- | :---: | :---: |
| React Native UI components & styling | ✅ Yes | ❌ Not required |
| Placeholder & text fixes | ✅ Yes | ❌ Not required |
| API URL & frontend routing changes | ✅ Yes | ❌ Not required |
| Icon / Splash image assets | ✅ Yes | ❌ Not required |
| New npm JS package (e.g. `date-fns`) | ✅ Yes | ❌ Not required |
| New native plugin (e.g. `expo-camera`) | ❌ No | ✅ Yes |
| Android Manifest / `app.json` native edits | ❌ No | ✅ Yes |

---

## 6. Emergency Troubleshooting Checklist

If an OTA update is not appearing on the device:

- [ ] **Check 1: Target Channel**: Did you use `--channel production` instead of `--branch main`?
- [ ] **Check 2: App Restart**: Did you swipe away the app from recent apps and open it a **second** time?
- [ ] **Check 3: EAS Live Channel Status**: Run `npx eas-cli channel:view production` to confirm the update group ID matches your latest deployment.
- [ ] **Check 4: Native Code Changes**: If native packages or native `app.json` fields changed, run a fresh build:
  ```powershell
  npx eas-cli build -p android --profile production
  ```
