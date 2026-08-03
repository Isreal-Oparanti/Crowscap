/**
 * Expo Config Plugin: withAbiSplits
 *
 * Injects Android ABI split configuration into the generated app/build.gradle
 * after Expo CNG creates it. This produces 3 separate APKs (one per ABI):
 *   - arm64-v8a  (~40-45MB) — modern phones (99% of devices)
 *   - armeabi-v7a (~38-42MB) — older 32-bit phones
 *   - x86_64     (~42-46MB) — emulators / some Chromebooks
 *
 * The arm64-v8a APK is the one deployed to the downloads endpoint.
 */
const { withAppBuildGradle } = require("@expo/config-plugins");

const withAbiSplits = (config) => {
  return withAppBuildGradle(config, (mod) => {
    const buildGradle = mod.modResults.contents;

    // Only inject if not already present
    if (buildGradle.includes("splits {")) {
      return mod;
    }

    // Inject ABI splits block right after `android {` opening
    const abiSplitsBlock = `
    splits {
        abi {
            enable true
            reset()
            include "arm64-v8a", "armeabi-v7a", "x86_64"
            universalApk false
        }
    }
`;

    mod.modResults.contents = buildGradle.replace(
      /android\s*\{/,
      `android {${abiSplitsBlock}`
    );

    return mod;
  });
};

module.exports = withAbiSplits;
