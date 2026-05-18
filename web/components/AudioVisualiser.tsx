"use client";

interface Props {
  level: number;
  isConnected: boolean;
}

export function AudioVisualiser({ level, isConnected }: Props) {
  const bars = 24;
  const barArray = Array.from({ length: bars }, (_, i) => {
    const distance = Math.abs(i - bars / 2) / (bars / 2);
    const height = isConnected
      ? Math.max(4, (1 - distance * 0.6) * level * 100)
      : 4;
    return height;
  });

  return (
    <div className="flex items-center gap-1 h-32">
      {barArray.map((h, i) => (
        <div
          key={i}
          className="w-2 rounded-full transition-all duration-75"
          style={{
            height: `${h}%`,
            backgroundColor: isConnected
              ? `rgba(129, 140, 248, ${0.4 + level * 0.6})`
              : "rgba(100, 100, 140, 0.3)",
            boxShadow: isConnected && level > 0.1
              ? `0 0 ${level * 10}px rgba(99, 102, 241, ${level * 0.5})`
              : "none",
          }}
        />
      ))}
      {!isConnected && (
        <div className="absolute text-gray-500 text-sm">Not connected</div>
      )}
    </div>
  );
}
