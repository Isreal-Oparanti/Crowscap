import * as Application from "expo-application";
import Constants from "expo-constants";
import * as Updates from "expo-updates";

export type NativeUpdateInfo = {
  latestVersionCode: number;
  minimumVersionCode?: number;
  versionName?: string;
  apkUrl: string;
  notes?: string;
  publishedAt?: string;
};

type VersionManifest = {
  android?: NativeUpdateInfo;
};

export type NativeUpdateResult =
  | { available: false }
  | { available: true; currentVersionCode: number; update: NativeUpdateInfo };

export type OtaUpdateResult =
  | { available: false }
  | { available: true; reload: () => Promise<void> };

const MANIFEST_TIMEOUT_MS = 5000;

function getManifestUrl() {
  const extra = Constants.expoConfig?.extra as
    | { downloads?: { versionManifestUrl?: string } }
    | undefined;

  return extra?.downloads?.versionManifestUrl;
}

function getCurrentAndroidVersionCode() {
  const nativeBuild = Number(Application.nativeBuildVersion);
  const configuredBuild = Constants.expoConfig?.android?.versionCode;

  if (Number.isFinite(nativeBuild) && nativeBuild > 0) {
    return nativeBuild;
  }

  if (typeof configuredBuild === "number" && configuredBuild > 0) {
    return configuredBuild;
  }

  return 1;
}

export async function checkNativeAndroidUpdate(): Promise<NativeUpdateResult> {
  const manifestUrl = getManifestUrl();

  if (!manifestUrl) {
    return { available: false };
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), MANIFEST_TIMEOUT_MS);

  try {
    const response = await fetch(manifestUrl, {
      cache: "no-store",
      signal: controller.signal,
    });

    if (!response.ok) {
      return { available: false };
    }

    const manifest = (await response.json()) as VersionManifest;
    const update = manifest.android;

    if (!update?.apkUrl || typeof update.latestVersionCode !== "number") {
      return { available: false };
    }

    const currentVersionCode = getCurrentAndroidVersionCode();

    if (update.latestVersionCode <= currentVersionCode) {
      return { available: false };
    }

    return {
      available: true,
      currentVersionCode,
      update,
    };
  } catch {
    return { available: false };
  } finally {
    clearTimeout(timeout);
  }
}

export async function checkOtaUpdate(): Promise<OtaUpdateResult> {
  if (__DEV__ || !("isEnabled" in Updates) || !Updates.isEnabled) {
    return { available: false };
  }

  try {
    const update = await Updates.checkForUpdateAsync();

    if (!update.isAvailable) {
      return { available: false };
    }

    await Updates.fetchUpdateAsync();

    return {
      available: true,
      reload: () => Updates.reloadAsync(),
    };
  } catch {
    return { available: false };
  }
}
