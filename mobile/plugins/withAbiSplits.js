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
    let buildGradle = mod.modResults.contents;

    // Inject ABI splits block if not present
    if (!buildGradle.includes("splits {")) {
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
      buildGradle = buildGradle.replace(/android\s*\{/, `android {${abiSplitsBlock}`);
    }

    // Enable R8 ProGuard code & resource shrinking for Release buildType
    if (buildGradle.includes("release {")) {
      buildGradle = buildGradle.replace(
        /release\s*\{/,
        `release {
            minifyEnabled true
            shrinkResources true
            proguardFiles getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro"`
      );
    }

    mod.modResults.contents = buildGradle;
    return mod;
  });
};

module.exports = withAbiSplits;
