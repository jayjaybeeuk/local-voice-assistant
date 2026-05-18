"use client";

import { useVoiceChat, VoiceChatState } from "@/hooks/useVoiceChat";
import { AudioVisualiser } from "./AudioVisualiser";
import { TranscriptPanel } from "./TranscriptPanel";
import { ConnectionStatus } from "./ConnectionStatus";

export function VoiceAssistant() {
  const { state, audioLevel, start, stop } = useVoiceChat();

  const isActive = state === "listening" || state === "speaking";

  return (
    <div className="w-full max-w-2xl mx-auto flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-100">
          <span className={isActive ? "text-green-400" : "text-gray-500"}>●</span> Voice Assistant
        </h1>
        <ConnectionStatus status={isActive ? "connected" : state === "connecting" ? "connecting" : "disconnected"} />
      </div>

      {/* Visualiser */}
      <div className="bg-surface rounded-2xl p-8 flex items-center justify-center min-h-[200px] relative">
        <AudioVisualiser level={audioLevel} isConnected={isActive} isSpeaking={state === "speaking"} />
        {state === "speaking" && (
          <div className="absolute bottom-3 text-xs text-indigo-300 animate-pulse">AI is speaking...</div>
        )}
      </div>

      {/* Voice Button */}
      <div className="flex items-center justify-center">
        <button
          onClick={isActive || state === "connecting" ? stop : start}
          disabled={state === "connecting"}
          className={`relative w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300 focus:outline-none focus:ring-4 ${
            isActive
              ? "bg-red-500/20 ring-4 ring-red-500/40 hover:bg-red-500/30"
              : state === "connecting"
              ? "bg-indigo-500/20 ring-4 ring-indigo-500/30 cursor-wait"
              : "bg-surface-light hover:bg-indigo-500/20 ring-0 hover:ring-4 hover:ring-indigo-500/30"
          }`}
        >
          {/* Pulse ring when active */}
          {isActive && (
            <span className="absolute inset-0 rounded-full animate-ping bg-red-500/20" />
          )}
          <MicIcon active={isActive} size={36} />
        </button>
      </div>
      <p className="text-center text-sm text-gray-500">
        {state === "idle" && "Tap to start voice chat"}
        {state === "connecting" && "Connecting..."}
        {state === "listening" && "Listening — speak now"}
        {state === "speaking" && "AI responding..."}
      </p>
    </div>
  );
}

function MicIcon({ active, size }: { active: boolean; size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={active ? "#ef4444" : "#a5b4fc"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}
