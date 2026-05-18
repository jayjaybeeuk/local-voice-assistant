"use client";

// Controls component retained for backward compatibility but the main voice button
// is now directly in VoiceAssistant.tsx for a cleaner UX.

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
      <div className="flex items-center justify-center gap-4">
        {!isConnected ? (
          <button
            onClick={onConnect}
            disabled={isConnecting}
            className="w-20 h-20 rounded-full flex items-center justify-center bg-surface-light hover:bg-indigo-500/20 hover:ring-4 hover:ring-indigo-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <MicIcon muted={false} size={32} color="#a5b4fc" />
          </button>
        ) : (
          <button
            onClick={onDisconnect}
            className="w-20 h-20 rounded-full flex items-center justify-center bg-red-500/20 ring-4 ring-red-500/40 hover:bg-red-500/30 transition-all relative"
          >
            <span className="absolute inset-0 rounded-full animate-ping bg-red-500/20" />
            <MicIcon muted={isMuted} size={32} color="#ef4444" />
          </button>
        )}
      </div>
    </div>
  );
}

function MicIcon({ muted, size, color }: { muted: boolean; size: number; color: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
      {muted && <line x1="1" y1="1" x2="23" y2="23" stroke={color} strokeWidth="2" />}
    </svg>
  );
}
