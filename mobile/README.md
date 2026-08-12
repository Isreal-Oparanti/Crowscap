# Crowscap Mobile Application (Expo / React Native)

This directory contains the cross-platform React Native / Expo application for Crowscap.

## Deployment & Updates

### Pushing Over-The-Air (OTA) Updates

For UI, layout, styling, text, and JS logic fixes (no new native plugins):

```powershell
# Push to Production APKs (Active users)
$env:EAS_SKIP_AUTO_FINGERPRINT=1
npx eas-cli update --channel production --message "fix: description of changes"

# Push to Preview Builds
$env:EAS_SKIP_AUTO_FINGERPRINT=1
npx eas-cli update --channel preview --message "fix: preview updates"
```

### Complete Troubleshooting Guide
See [`../docs/22-eas-ota-updates-troubleshooting.md`](../docs/22-eas-ota-updates-troubleshooting.md) for full channel mapping, launch behavior, and troubleshooting steps.

### Building Standalone APKs
```powershell
npx eas-cli build -p android --profile production
```
