"use client";

import { useState, useCallback, useRef } from "react";
import type { TranscriptMessage, VoiceMode } from "@/lib/config";

interface ConnectionState {
  status: "idle" | "connecting" | "connected" | "error";
  error?: string;
}

export function useVoiceConnection() {
  const [connectionState, setConnectionState] = useState<ConnectionState>({ status: "idle" });
  const [roomUrl, setRoomUrl] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptMessage[]>([]);
  const [mode, setMode] = useState<VoiceMode>("vad");
  const [isMuted, setIsMuted] = useState(false);

  const connect = useCallback(async () => {
    setConnectionState({ status: "connecting" });
    try {
      const res = await fetch("/api/connect", { method: "POST" });
      if (!res.ok) throw new Error("Failed to connect");
      const data = await res.json();
      setRoomUrl(data.room_url);
      setToken(data.token);
      setConnectionState({ status: "connected" });
    } catch (e: any) {
      setConnectionState({ status: "error", error: e.message });
    }
  }, []);

  const disconnect = useCallback(() => {
    setRoomUrl(null);
    setToken(null);
    setConnectionState({ status: "idle" });
    setTranscript([]);
  }, []);

  const addMessage = useCallback((role: "user" | "assistant", text: string) => {
    setTranscript((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role, text, timestamp: Date.now() },
    ]);
  }, []);

  return {
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
  };
}
