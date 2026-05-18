"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import type { TranscriptMessage } from "@/lib/config";

export type VoiceChatState = "idle" | "connecting" | "listening" | "speaking";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8765";
const WS_TOKEN = process.env.NEXT_PUBLIC_WS_TOKEN || "";
const SAMPLE_RATE = 16000;

export function useVoiceChat() {
  const [state, setState] = useState<VoiceChatState>("idle");
  const [audioLevel, setAudioLevel] = useState(0);
  const [responseTime, setResponseTime] = useState<number | null>(null);
  const [transcript, setTranscript] = useState<TranscriptMessage[]>([]);
  const [lastError, setLastError] = useState<string | null>(null);

  const lastAudioSentAt = useRef<number>(0);
  const awaitingResponse = useRef(false);
  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const levelTimerRef = useRef<ReturnType<typeof requestAnimationFrame> | null>(null);
  const playbackCtxRef = useRef<AudioContext | null>(null);
  const playbackQueue = useRef<ArrayBuffer[]>([]);
  const isPlaying = useRef(false);

  const addTranscriptMessage = useCallback((role: "user" | "assistant", text: string) => {
    setTranscript((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role, text, timestamp: Date.now() },
    ]);
  }, []);

  const playNextChunk = useCallback(async () => {
    if (playbackQueue.current.length === 0) {
      isPlaying.current = false;
      setState((s) => (s === "speaking" ? "listening" : s));
      return;
    }
    isPlaying.current = true;
    setState("speaking");

    const chunk = playbackQueue.current.shift()!;
    const ctx = playbackCtxRef.current!;
    const int16 = new Int16Array(chunk);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 32768;
    }

    const buffer = ctx.createBuffer(1, float32.length, SAMPLE_RATE);
    buffer.copyToChannel(float32, 0);
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.onended = () => playNextChunk();
    source.start();
  }, []);

  const start = useCallback(async () => {
    setState("connecting");
    setLastError(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: SAMPLE_RATE, channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = stream;

      const audioCtx = new AudioContext({ sampleRate: SAMPLE_RATE });
      audioCtxRef.current = audioCtx;
      playbackCtxRef.current = new AudioContext({ sampleRate: SAMPLE_RATE });

      await audioCtx.audioWorklet.addModule("/audio-processor.worklet.js");

      const source = audioCtx.createMediaStreamSource(stream);
      const workletNode = new AudioWorkletNode(audioCtx, "audio-processor");
      workletNodeRef.current = workletNode;

      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;
      source.connect(analyser);
      source.connect(workletNode);

      const ws = new WebSocket(WS_URL);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      ws.onopen = () => {
        if (WS_TOKEN) {
          ws.send(JSON.stringify({ token: WS_TOKEN }));
        }
        setState("listening");

        workletNode.port.onmessage = (e) => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(e.data);
            lastAudioSentAt.current = performance.now();
            awaitingResponse.current = true;
          }
        };

        const dataArray = new Float32Array(analyser.fftSize);
        const measureLevel = () => {
          if (!analyserRef.current) return;
          analyser.getFloatTimeDomainData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) sum += dataArray[i] * dataArray[i];
          setAudioLevel(Math.sqrt(sum / dataArray.length));
          levelTimerRef.current = requestAnimationFrame(measureLevel);
        };
        measureLevel();
      };

      ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          if (awaitingResponse.current) {
            setResponseTime(Math.round(performance.now() - lastAudioSentAt.current));
            awaitingResponse.current = false;
          }
          playbackQueue.current.push(event.data);
          if (!isPlaying.current) playNextChunk();
        } else if (typeof event.data === "string") {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === "transcript") {
              addTranscriptMessage(msg.role as "user" | "assistant", msg.text);
            } else if (msg.type === "error") {
              setLastError(msg.message);
            }
          } catch {
            // ignore malformed frames
          }
        }
      };

      ws.onclose = () => stop();
      ws.onerror = () => stop();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to start voice chat";
      console.error("Voice chat error:", err);
      setLastError(message);
      setState("idle");
    }
  }, [playNextChunk, addTranscriptMessage]);

  const stop = useCallback(() => {
    if (levelTimerRef.current !== null) {
      cancelAnimationFrame(levelTimerRef.current);
      levelTimerRef.current = null;
    }
    analyserRef.current = null;
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }
    if (audioCtxRef.current) {
      audioCtxRef.current.close();
      audioCtxRef.current = null;
    }
    if (playbackCtxRef.current) {
      playbackCtxRef.current.close();
      playbackCtxRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    playbackQueue.current = [];
    isPlaying.current = false;
    setAudioLevel(0);
    setState("idle");
  }, []);

  useEffect(() => {
    return () => {
      stop();
    };
  }, [stop]);

  return { state, audioLevel, responseTime, transcript, lastError, start, stop };
}
