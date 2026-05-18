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

export interface EndpointConfig {
  endpointUrl: string;
  apiKey: string;
  model: string;
}

export const defaultEndpointConfig: EndpointConfig = {
  endpointUrl: "http://localhost:11434/v1",
  apiKey: "",
  model: "qwen3:8b",
};
