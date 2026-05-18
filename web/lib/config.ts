export const config = {
  backendUrl: process.env.NEXT_PUBLIC_PIPECAT_BACKEND_URL || "http://localhost:7860",
  connectEndpoint: "/api/connect",
};

export type VoiceMode = "ptt" | "vad";

export interface TranscriptMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: number;
}
