"use client";

import { useState } from "react";
import { AudioVisualiser } from "./AudioVisualiser";
import { TranscriptPanel } from "./TranscriptPanel";
import { Controls } from "./Controls";
import { ConnectionStatus } from "./ConnectionStatus";
import { useVoiceConnection } from "@/hooks/useVoiceConnection";
import { useAudioLevel } from "@/hooks/useAudioLevel";

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
        <ConnectionStatus status={connectionState.status} />
      </div>

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
    </div>
  );
}
