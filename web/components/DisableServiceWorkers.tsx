"use client";

import { useEffect } from "react";

export function DisableServiceWorkers() {
  useEffect(() => {
    const cleanup = async () => {
      if (!("serviceWorker" in navigator)) {
        return;
      }

      try {
        const registrations = await navigator.serviceWorker.getRegistrations();
        await Promise.all(registrations.map((registration) => registration.unregister()));

        if ("caches" in window) {
          const keys = await caches.keys();
          await Promise.all(keys.map((key) => caches.delete(key)));
        }
      } catch {
        // Best effort cleanup; app should continue even if this fails.
      }
    };

    void cleanup();
  }, []);

  return null;
}