import type { Message } from "../types";
import { MessageTimestamp } from "./MessageTimestamp";

interface UserMessageProps {
  message: Message;
}

export function UserMessage({ message }: UserMessageProps) {
  return (
    <div className="flex justify-end mb-4">
      <div className="max-w-[70%]">
        <div className="bg-gray-100 text-black rounded-full px-4 py-2">
          <p className="text-sm whitespace-pre-wrap break-words">
            {message.content}
          </p>
        </div>
        <div className="flex justify-end mt-1">
          <MessageTimestamp timestamp={message.timestamp} />
        </div>
      </div>
    </div>
  );
}
