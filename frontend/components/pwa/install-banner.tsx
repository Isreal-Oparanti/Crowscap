"use client";

import { Download } from "lucide-react";
import { useEffect, useState } from "react";

import { BrandIcon } from "@/components/ui/brand-icon";
import { registerCrowscapServiceWorker } from "@/lib/notifications";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
};

const PWA_INSTALLED_KEY = "crowscap:pwa-installed";

function isStandalonePwa() {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    Boolean((window.navigator as Navigator & { standalone?: boolean }).standalone)
  );
}

function hasInstalledMemory() {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(PWA_INSTALLED_KEY) === "true";
}

function rememberInstalled() {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(PWA_INSTALLED_KEY, "true");
}

export function InstallBanner() {
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(false);
  const [showManualInstall, setShowManualInstall] = useState(false);
  const [serviceWorkerReady, setServiceWorkerReady] = useState(false);
  const [installing, setInstalling] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    registerCrowscapServiceWorker()
      .then(() => navigator.serviceWorker.ready)
      .then(() => setServiceWorkerReady(true))
      .catch(() => setServiceWorkerReady(false));

    const updateInstalled = () => {
      setInstalled(isStandalonePwa() || hasInstalledMemory());
    };

    updateInstalled();

    const media = window.matchMedia("(display-mode: standalone)");
    media.addEventListener?.("change", updateInstalled);

    const onPrompt = (event: Event) => {
      event.preventDefault();
      if (isStandalonePwa() || hasInstalledMemory()) {
        setInstalled(true);
        return;
      }
      setDeferredPrompt(event as BeforeInstallPromptEvent);
      setShowManualInstall(false);
    };

    const onInstalled = () => {
      rememberInstalled();
      setInstalled(true);
      setDeferredPrompt(null);
      window.dispatchEvent(new Event("crowscap:pwa-installed"));
    };

    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);

    const manualTimer = window.setTimeout(() => {
      const ua = window.navigator.userAgent.toLowerCase();
      const isAppleMobile = /iphone|ipad|ipod/.test(ua);
      if (isAppleMobile && !isStandalonePwa() && !hasInstalledMemory()) {
        setShowManualInstall(true);
      }
    }, 1600);

    return () => {
      window.clearTimeout(manualTimer);
      media.removeEventListener?.("change", updateInstalled);
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  if (installed || (!deferredPrompt && !showManualInstall && !serviceWorkerReady)) {
    return null;
  }

  const handleInstall = async () => {
    if (installing) return;

    if (!deferredPrompt) {
      window.alert(
        "To install Crowscap on iOS:\n\n1. Tap the Share button in Safari (at the bottom of your screen)\n2. Scroll down and tap 'Add to Home Screen'\n3. Tap 'Add' in the top right",
      );
      return;
    }


    try {
      setInstalling(true);
      await deferredPrompt.prompt();
      const choice = await deferredPrompt.userChoice;
      if (choice.outcome === "accepted") {
        rememberInstalled();
        setInstalled(true);
        setDeferredPrompt(null);
        window.dispatchEvent(new Event("crowscap:pwa-installed"));
      } else {
        setDeferredPrompt(null);
      }
    } finally {
      setInstalling(false);
    }
  };

  const canInstall = Boolean(deferredPrompt);
  const manualOnly = showManualInstall && !canInstall;

  if (!canInstall && !manualOnly) {
    return (
      <div className="fixed bottom-4 left-4 right-4 z-[120] mx-auto max-w-xl md:bottom-6">
        <div className="flex items-center gap-3 rounded-2xl border border-black/5 bg-white px-4 py-3 shadow-[0_12px_34px_rgba(17,17,17,0.18)]">
          <div className="flex size-[38px] shrink-0 items-center justify-center rounded-[10px] border border-[#e5e7e8] bg-white">
            <BrandIcon className="size-[31px]" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[15px] font-semibold leading-tight text-[#202124]">
              Preparing install
            </p>
            <p className="truncate text-xs font-medium text-[#5f6368]">
              Crowscap is getting the app shell ready.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 left-4 right-4 z-[120] mx-auto max-w-xl md:bottom-6">
      <div className="flex items-center gap-3 rounded-2xl border border-black/5 bg-white px-4 py-3 shadow-[0_12px_34px_rgba(17,17,17,0.18)]">
        <div className="flex size-[38px] shrink-0 items-center justify-center rounded-[10px] border border-[#e5e7e8] bg-white">
          <BrandIcon className="size-[31px]" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[15px] font-semibold leading-tight text-[#202124]">
            {manualOnly ? "Add Crowscap to Home Screen" : "Install Crowscap"}
          </p>
          <p className="truncate text-xs font-medium text-[#5f6368]">
            {manualOnly ? "Use your browser menu on this device" : "crowscap.xyz"}
          </p>
        </div>
        <button
          type="button"
          onClick={handleInstall}
          disabled={installing}
          className="inline-flex shrink-0 items-center gap-2 rounded-full px-2 py-2 text-sm font-semibold text-[#202124] transition hover:bg-[#f2f3f4] disabled:opacity-60"
        >
          <Download size={15} />
          {installing ? "Opening..." : manualOnly ? "How" : "Install"}
        </button>
      </div>
    </div>
  );
}
