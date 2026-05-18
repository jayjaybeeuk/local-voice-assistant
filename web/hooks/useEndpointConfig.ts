"use client";

import { useState, useEffect, useCallback } from "react";
import { EndpointConfig, defaultEndpointConfig } from "@/lib/config";

const STORAGE_KEY = "llm-endpoint-config";

export function useEndpointConfig() {
  const [config, setConfig] = useState<EndpointConfig>(defaultEndpointConfig);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        setConfig({ ...defaultEndpointConfig, ...JSON.parse(stored) });
      }
    } catch {}
    setLoaded(true);
  }, []);

  const save = useCallback(async (newConfig: EndpointConfig): Promise<{ ok: boolean; error?: string }> => {
    setConfig(newConfig);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newConfig));
    try {
      const res = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newConfig),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        return { ok: false, error: (data as { error?: string }).error || `Server error ${res.status}` };
      }
      return { ok: true };
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Failed to save settings";
      return { ok: false, error: message };
    }
  }, []);

  return { config, save, loaded };
}
