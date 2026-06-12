interface MessageTimestampProps {
  timestamp: Date;
}

export function MessageTimestamp({ timestamp }: MessageTimestampProps) {
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return <span className="text-xs text-gray-500">{formatTime(timestamp)}</span>;
}
