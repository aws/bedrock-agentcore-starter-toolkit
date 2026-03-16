/**
 * ChatView component displays the conversation history between user and agent.
 *
 * Features:
 * - Renders user and agent messages with appropriate styling
 * - Auto-scrolls to the latest message when new messages arrive
 * - Shows typing indicator while agent is processing
 * - Handles both text and markdown content in agent responses
 */

import { useEffect, useRef } from "react";
import type { Message } from "../types";
import { UserMessage } from "./UserMessage";
import { AgentMessage } from "./AgentMessage";
import { TypingIndicator } from "./TypingIndicator";

interface ChatViewProps {
  messages: Message[];
  isLoading?: boolean;
}

export function ChatView({ messages, isLoading = false }: ChatViewProps) {
  // Reference to the bottom of the message list for auto-scrolling
  const messagesEndRef = useRef<HTMLDivElement>(null);

  /**
   * Smoothly scroll to the bottom of the message list.
   * Called when new messages arrive or loading state changes.
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Auto-scroll whenever messages change or loading state changes
  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  return (
    <div className="max-w-4xl mx-auto">
      <div className="space-y-4">
        {/* Render each message with the appropriate component based on role */}
        {messages.map((message) =>
          message.role === "user" ? (
            <UserMessage key={message.id} message={message} />
          ) : (
            <AgentMessage key={message.id} message={message} />
          )
        )}
        {/* Show typing indicator while waiting for agent response */}
        {isLoading && <TypingIndicator />}
        {/* Invisible element at the bottom for scroll target */}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}
