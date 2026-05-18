"use client";

import type { TranscriptMessage } from "@/lib/config";
import { useEffect, useRef } from "react";

interface Props {
  messages: TranscriptMessage[];
}

export function TranscriptPanel({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="bg-surface rounded-2xl p-6 min-h-[160px] flex items-center justify-center">
        <p className="text-gray-500 text-sm">Conversation will appear here...</p>
      </div>
    );
  }

  return (
    <div className="bg-surface rounded-2xl p-4 max-h-[300px] overflow-y-auto space-y-3">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`max-w-[80%] px-4 py-2 rounded-2xl text-sm ${
              msg.role === "user"
                ? "bg-accent/20 text-accent-light rounded-br-md"
                : "bg-surface-light text-gray-200 rounded-bl-md"
            }`}
          >
            {msg.text}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
