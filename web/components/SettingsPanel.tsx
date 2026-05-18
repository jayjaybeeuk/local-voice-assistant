"use client";

import { useState, useEffect } from "react";
import { EndpointConfig } from "@/lib/config";

interface Props {
  config: EndpointConfig;
  onSave: (config: EndpointConfig) => Promise<{ ok: boolean; error?: string }>;
  onClose: () => void;
}

export function SettingsPanel({ config, onSave, onClose }: Props) {
  const [endpointUrl, setEndpointUrl] = useState(config.endpointUrl);
  const [apiKey, setApiKey] = useState(config.apiKey);
  const [model, setModel] = useState(config.model);
  const [testStatus, setTestStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [testMessage, setTestMessage] = useState("");
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [saveError, setSaveError] = useState("");

  useEffect(() => {
    setEndpointUrl(config.endpointUrl);
    setApiKey(config.apiKey);
    setModel(config.model);
  }, [config]);

  const testConnection = async () => {
    setTestStatus("loading");
    setTestMessage("");
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;
      const res = await fetch(`${endpointUrl}/models`, { headers });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const models = data.data?.map((m: { id: string }) => m.id).slice(0, 5).join(", ") || "connected";
      setTestStatus("success");
      setTestMessage(`Models: ${models}`);
    } catch (e: unknown) {
      setTestStatus("error");
      setTestMessage(e instanceof Error ? e.message : "Connection failed");
    }
  };

  const handleSave = async () => {
    setSaveStatus("saving");
    setSaveError("");
    const result = await onSave({ endpointUrl, apiKey, model });
    if (result.ok) {
      setSaveStatus("saved");
      setTimeout(() => {
        setSaveStatus("idle");
        onClose();
      }, 800);
    } else {
      setSaveStatus("error");
      setSaveError(result.error || "Failed to save");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-surface border border-white/10 rounded-2xl p-6 w-full max-w-md space-y-5 shadow-2xl">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-100">LLM Endpoint Settings</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">&times;</button>
        </div>

        <div className="space-y-4">
          <label className="block">
            <span className="text-sm text-gray-400">Endpoint URL</span>
            <input
              type="text"
              value={endpointUrl}
              onChange={(e) => setEndpointUrl(e.target.value)}
              className="mt-1 w-full px-3 py-2 bg-surface-dark border border-white/10 rounded-lg text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
              placeholder="http://localhost:11434/v1"
            />
          </label>

          <label className="block">
            <span className="text-sm text-gray-400">API Key (optional)</span>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="mt-1 w-full px-3 py-2 bg-surface-dark border border-white/10 rounded-lg text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
              placeholder="sk-..."
            />
          </label>

          <label className="block">
            <span className="text-sm text-gray-400">Model</span>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="mt-1 w-full px-3 py-2 bg-surface-dark border border-white/10 rounded-lg text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
              placeholder="qwen3:8b"
            />
          </label>
        </div>

        {/* Test result */}
        {testStatus !== "idle" && (
          <div className={`text-sm px-3 py-2 rounded-lg ${
            testStatus === "success" ? "bg-green-500/10 text-green-400" :
            testStatus === "error" ? "bg-red-500/10 text-red-400" :
            "bg-white/5 text-gray-400"
          }`}>
            {testStatus === "loading" && "Testing..."}
            {testStatus === "success" && `✓ ${testMessage}`}
            {testStatus === "error" && `✗ ${testMessage}`}
          </div>
        )}

        {/* Save error */}
        {saveStatus === "error" && saveError && (
          <div className="text-sm px-3 py-2 rounded-lg bg-red-500/10 text-red-400">
            ✗ {saveError}
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={testConnection}
            className="flex-1 px-4 py-2 bg-surface-light hover:bg-white/10 text-gray-300 rounded-lg text-sm font-medium transition-all"
          >
            Test Connection
          </button>
          <button
            onClick={handleSave}
            disabled={saveStatus === "saving"}
            className="flex-1 px-4 py-2 bg-accent hover:bg-accent-dark text-white rounded-lg text-sm font-medium transition-all disabled:opacity-60"
          >
            {saveStatus === "saving" ? "Saving..." : saveStatus === "saved" ? "Saved ✓" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
