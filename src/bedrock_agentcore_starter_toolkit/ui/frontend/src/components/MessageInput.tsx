import { useState, useRef, useEffect, type FormEvent } from "react";
import { ArrowUp, Loader2 } from "lucide-react";

interface MessageInputProps {
  onSend: (message: string) => void;
  isLoading: boolean;
  disabled?: boolean;
  placeholder?: string;
  onFocus?: () => void;
}

export function MessageInput({
  onSend,
  isLoading,
  disabled = false,
  placeholder = "Type your message...",
  onFocus,
}: MessageInputProps) {
  const [message, setMessage] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const wasLoadingRef = useRef(false);

  // Refocus input after response is received
  useEffect(() => {
    if (wasLoadingRef.current && !isLoading && !disabled) {
      textareaRef.current?.focus();
    }
    wasLoadingRef.current = isLoading;
  }, [isLoading, disabled]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isLoading && !disabled) {
      onSend(message.trim());
      setMessage("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const isInputDisabled = isLoading || disabled;

  return (
    <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
      <div className="relative">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={onFocus}
          placeholder={placeholder}
          className="w-full resize-none rounded-full border-2 border-gray-300 px-6 py-4 pr-14 focus:outline-none focus:border-gray-800 min-h-[56px] max-h-32 disabled:bg-gray-100 disabled:cursor-not-allowed"
          rows={1}
          disabled={isInputDisabled}
        />
        <button
          type="submit"
          disabled={!message.trim() || isInputDisabled}
          className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full flex items-center justify-center transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            backgroundColor:
              message.trim() && !isInputDisabled ? "#000" : "#e5e7eb",
          }}
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 text-white animate-spin" />
          ) : (
            <ArrowUp className="w-5 h-5 text-white" />
          )}
        </button>
      </div>
      <p className="text-xs text-gray-400 mt-2 text-center">
        {disabled
          ? "Authentication required to send messages"
          : "Press Enter to send, Shift+Enter for new line"}
      </p>
    </form>
  );
}
