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

  const save = useCallback(async (newConfig: EndpointConfig) => {
    setConfig(newConfig);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newConfig));
    // Also persist to server for backend polling
    try {
      await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newConfig),
      });
    } catch {}
  }, []);

  return { config, save, loaded };
}
