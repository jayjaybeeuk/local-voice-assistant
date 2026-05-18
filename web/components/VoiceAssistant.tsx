"use client";

import { useState } from "react";
import { AudioVisualiser } from "./AudioVisualiser";
import { TranscriptPanel } from "./TranscriptPanel";
import { Controls } from "./Controls";
import { ConnectionStatus } from "./ConnectionStatus";
import { SettingsPanel } from "./SettingsPanel";
import { useVoiceConnection } from "@/hooks/useVoiceConnection";
import { useAudioLevel } from "@/hooks/useAudioLevel";
import { useEndpointConfig } from "@/hooks/useEndpointConfig";

export function VoiceAssistant() {
  const {
    connectionState,
    roomUrl,
    token,
    transcript,
    mode,
    setMode,
    isMuted,
    setIsMuted,
    connect,
    disconnect,
    addMessage,
  } = useVoiceConnection();

  const audioLevel = useAudioLevel();
  const [showSettings, setShowSettings] = useState(false);
  const [showEndpointSettings, setShowEndpointSettings] = useState(false);
  const { config: endpointConfig, save: saveEndpointConfig, loaded } = useEndpointConfig();

  const handleConnect = async () => {
    await connect();
    audioLevel.start();
  };

  const handleDisconnect = () => {
    disconnect();
    audioLevel.stop();
  };

  return (
    <div className="w-full max-w-2xl mx-auto flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-100">
          <span className="text-accent-light">●</span> Voice Assistant
        </h1>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowEndpointSettings(true)}
            className="p-2 rounded-lg bg-surface-light text-gray-400 hover:text-white transition-all"
            title="LLM Settings"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </button>
          <ConnectionStatus status={connectionState.status} />
        </div>
      </div>

      {/* Endpoint status bar */}
      {loaded && (
        <div className="flex items-center gap-2 text-xs text-gray-500 px-1">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
          <span className="truncate">{endpointConfig.model} @ {endpointConfig.endpointUrl}</span>
        </div>
      )}

      {/* Visualiser */}
      <div className="bg-surface rounded-2xl p-8 flex items-center justify-center min-h-[200px]">
        <AudioVisualiser level={audioLevel.level} isConnected={connectionState.status === "connected"} />
      </div>

      {/* Transcript */}
      <TranscriptPanel messages={transcript} />

      {/* Controls */}
      <Controls
        isConnected={connectionState.status === "connected"}
        isConnecting={connectionState.status === "connecting"}
        mode={mode}
        isMuted={isMuted}
        onConnect={handleConnect}
        onDisconnect={handleDisconnect}
        onModeChange={setMode}
        onMuteToggle={() => setIsMuted(!isMuted)}
        showSettings={showSettings}
        onSettingsToggle={() => setShowSettings(!showSettings)}
      />

      {/* Endpoint Settings Modal */}
      {showEndpointSettings && (
        <SettingsPanel
          config={endpointConfig}
          onSave={saveEndpointConfig}
          onClose={() => setShowEndpointSettings(false)}
        />
      )}
    </div>
  );
}
