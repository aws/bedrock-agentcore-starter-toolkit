import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Copy, Check } from "lucide-react";
import type { Message } from "../types";
import { MessageTimestamp } from "./MessageTimestamp";

interface AgentMessageProps {
  message: Message;
}

export function AgentMessage({ message }: AgentMessageProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[70%]">
        <div className="bg-white text-gray-900 rounded-lg px-4 py-2">
          <div className="text-sm prose prose-sm max-w-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        </div>
        <div className="flex justify-start items-center gap-2 mt-1">
          <MessageTimestamp timestamp={message.timestamp} />
          <button
            onClick={handleCopy}
            className="text-gray-400 hover:text-gray-600 transition-colors p-1"
            title="Copy to clipboard"
          >
            {copied ? (
              <Check className="w-3 h-3 text-gray-500" />
            ) : (
              <Copy className="w-3 h-3" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
