"use client";

interface Props {
  level: number;
  isConnected: boolean;
  isSpeaking?: boolean;
}

export function AudioVisualiser({ level, isConnected, isSpeaking }: Props) {
  const bars = 24;
  const barArray = Array.from({ length: bars }, (_, i) => {
    const distance = Math.abs(i - bars / 2) / (bars / 2);
    const height = isConnected
      ? Math.max(4, (1 - distance * 0.6) * level * 100 * 3)
      : 4;
    return height;
  });

  const color = isSpeaking
    ? "rgba(99, 102, 241, VAR)" // indigo when AI speaks
    : "rgba(74, 222, 128, VAR)"; // green when user speaks

  return (
    <div className="flex items-center gap-1 h-32">
      {barArray.map((h, i) => (
        <div
          key={i}
          className="w-2 rounded-full transition-all duration-75"
          style={{
            height: `${h}%`,
            backgroundColor: isConnected
              ? color.replace("VAR", String(0.4 + level * 0.6))
              : "rgba(100, 100, 140, 0.3)",
            boxShadow: isConnected && level > 0.05
              ? `0 0 ${level * 12}px ${isSpeaking ? "rgba(99,102,241,0.5)" : "rgba(74,222,128,0.5)"}`
              : "none",
          }}
        />
      ))}
      {!isConnected && (
        <div className="absolute text-gray-500 text-sm">Tap mic to start</div>
      )}
    </div>
  );
}
