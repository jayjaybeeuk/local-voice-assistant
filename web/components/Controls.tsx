"use client";

import type { VoiceMode } from "@/lib/config";

interface Props {
  isConnected: boolean;
  isConnecting: boolean;
  mode: VoiceMode;
  isMuted: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
  onModeChange: (mode: VoiceMode) => void;
  onMuteToggle: () => void;
  showSettings: boolean;
  onSettingsToggle: () => void;
}

export function Controls({
  isConnected,
  isConnecting,
  mode,
  isMuted,
  onConnect,
  onDisconnect,
  onModeChange,
  onMuteToggle,
  showSettings,
  onSettingsToggle,
}: Props) {
  return (
    <div className="space-y-4">
      {/* Main controls */}
      <div className="flex items-center justify-center gap-4">
        {!isConnected ? (
          <button
            onClick={onConnect}
            disabled={isConnecting}
            className="px-8 py-3 bg-accent hover:bg-accent-dark rounded-full font-medium text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isConnecting ? "Connecting..." : "Connect"}
          </button>
        ) : (
          <>
            <button
              onClick={onMuteToggle}
              className={`p-3 rounded-full transition-all ${
                isMuted ? "bg-red-500/20 text-red-400" : "bg-surface-light text-gray-300 hover:text-white"
              }`}
              title={isMuted ? "Unmute" : "Mute"}
            >
              <MicIcon muted={isMuted} />
            </button>

            <button
              onClick={onDisconnect}
              className="px-6 py-3 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-full font-medium transition-all"
            >
              Disconnect
            </button>

            <button
              onClick={onSettingsToggle}
              className="p-3 rounded-full bg-surface-light text-gray-300 hover:text-white transition-all"
              title="Settings"
            >
              <SettingsIcon />
            </button>
          </>
        )}
      </div>

      {/* Settings panel */}
      {showSettings && isConnected && (
        <div className="bg-surface rounded-2xl p-4 space-y-3 animate-in fade-in">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Voice Mode</span>
            <div className="flex bg-surface-dark rounded-lg overflow-hidden">
              <button
                onClick={() => onModeChange("vad")}
                className={`px-4 py-1.5 text-xs font-medium transition-all ${
                  mode === "vad" ? "bg-accent text-white" : "text-gray-400 hover:text-white"
                }`}
              >
                Hands-free
              </button>
              <button
                onClick={() => onModeChange("ptt")}
                className={`px-4 py-1.5 text-xs font-medium transition-all ${
                  mode === "ptt" ? "bg-accent text-white" : "text-gray-400 hover:text-white"
                }`}
              >
                Push-to-talk
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function MicIcon({ muted }: { muted: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
      {muted && <line x1="1" y1="1" x2="23" y2="23" stroke="currentColor" strokeWidth="2" />}
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}
