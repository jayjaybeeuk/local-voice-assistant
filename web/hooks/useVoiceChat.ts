"use client";

import { useState, useRef, useCallback, useEffect } from "react";

export type VoiceChatState = "idle" | "connecting" | "listening" | "speaking";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8765";
const SAMPLE_RATE = 16000;
const BUFFER_SIZE = 4096;

export function useVoiceChat() {
  const [state, setState] = useState<VoiceChatState>("idle");
  const [audioLevel, setAudioLevel] = useState(0);
  const [responseTime, setResponseTime] = useState<number | null>(null);
  const lastAudioSentAt = useRef<number>(0);
  const awaitingResponse = useRef(false);
  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const workletRef = useRef<ScriptProcessorNode | null>(null);
  const playbackCtxRef = useRef<AudioContext | null>(null);
  const playbackQueue = useRef<ArrayBuffer[]>([]);
  const isPlaying = useRef(false);

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

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: SAMPLE_RATE, channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = stream;

      const audioCtx = new AudioContext({ sampleRate: SAMPLE_RATE });
      audioCtxRef.current = audioCtx;
      playbackCtxRef.current = new AudioContext({ sampleRate: SAMPLE_RATE });

      const source = audioCtx.createMediaStreamSource(stream);
      // Use ScriptProcessorNode for broad compatibility
      const processor = audioCtx.createScriptProcessor(BUFFER_SIZE, 1, 1);
      workletRef.current = processor;

      const ws = new WebSocket(WS_URL);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      ws.onopen = () => {
        setState("listening");
        // Start sending audio
        processor.onaudioprocess = (e) => {
          const input = e.inputBuffer.getChannelData(0);
          // Compute level
          let sum = 0;
          for (let i = 0; i < input.length; i++) sum += input[i] * input[i];
          setAudioLevel(Math.sqrt(sum / input.length));

          // Convert float32 to int16 PCM
          const pcm = new Int16Array(input.length);
          for (let i = 0; i < input.length; i++) {
            const s = Math.max(-1, Math.min(1, input[i]));
            pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
          }
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(pcm.buffer);
            lastAudioSentAt.current = performance.now();
            awaitingResponse.current = true;
          }
        };
        source.connect(processor);
        processor.connect(audioCtx.destination); // needed for ScriptProcessor to fire
      };

      ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          if (awaitingResponse.current) {
            const delta = Math.round(performance.now() - lastAudioSentAt.current);
            setResponseTime(delta);
            awaitingResponse.current = false;
          }
          playbackQueue.current.push(event.data);
          if (!isPlaying.current) playNextChunk();
        }
      };

      ws.onclose = () => {
        stop();
      };

      ws.onerror = () => {
        stop();
      };
    } catch (err) {
      console.error("Voice chat error:", err);
      setState("idle");
    }
  }, [playNextChunk]);

  const stop = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (workletRef.current) {
      workletRef.current.disconnect();
      workletRef.current = null;
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
    return () => { stop(); };
  }, [stop]);

  return { state, audioLevel, responseTime, start, stop };
}
