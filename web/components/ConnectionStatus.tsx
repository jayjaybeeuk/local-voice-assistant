"use client";

interface Props {
  status: "idle" | "connecting" | "connected" | "error";
}

const statusConfig: Record<Props["status"], { color: string; text: string }> = {
  idle: { color: "bg-gray-500", text: "Disconnected" },
  connecting: { color: "bg-yellow-500 animate-pulse", text: "Connecting" },
  connected: { color: "bg-emerald-500", text: "Connected" },
  error: { color: "bg-red-500", text: "Error" },
};

export function ConnectionStatus({ status }: Props) {
  const { color, text } = statusConfig[status] ?? statusConfig.idle;
  return (
    <div className="flex items-center gap-2 text-sm text-gray-400">
      <div className={`w-2 h-2 rounded-full ${color}`} />
      {text}
    </div>
  );
}
