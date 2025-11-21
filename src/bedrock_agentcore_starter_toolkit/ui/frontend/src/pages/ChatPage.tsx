import { useState, useMemo } from "react";
import { Copy, Check } from "lucide-react";
import { ConfigPanel } from "../components/ConfigPanel";
import { ChatView } from "../components/ChatView";
import { MessageInput } from "../components/MessageInput";
import { NewConversationButton } from "../components/NewConversationButton";
import { ErrorDisplay } from "../components/ErrorDisplay";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ErrorToast } from "../components/ErrorToast";
import { OAuthTokenInput } from "../components/OAuthTokenInput";
import { UserIdInput } from "../components/UserIdInput";
import { useConfig } from "../hooks/useConfig";
import { useInvoke } from "../hooks/useInvoke";
import { useNewSession } from "../hooks/useNewSession";
import type { Message } from "../types";
import { sessionStorage } from "../utils/sessionStorage";

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [errorToast, setErrorToast] = useState<string | null>(null);
  const [copiedSessionId, setCopiedSessionId] = useState(false);
  const [bearerToken, setBearerToken] = useState<string>("");
  const [userId, setUserId] = useState<string>("");
  const [isTokenInputCollapsed, setIsTokenInputCollapsed] = useState(false);
  const [isUserIdInputCollapsed, setIsUserIdInputCollapsed] = useState(false);

  const { data: config, isLoading, error, refetch } = useConfig();
  const invokeMutation = useInvoke();
  const newSessionMutation = useNewSession();

  const currentSessionId = useMemo(() => {
    if (!config) return "";
    const storedSessionId = sessionStorage.getSessionId();
    const sessionId = storedSessionId || config.session_id;
    sessionStorage.setSessionId(sessionId);
    return sessionId;
  }, [config]);

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);

    try {
      console.log({ content });
      const response = await invokeMutation.mutateAsync({
        message: JSON.stringify({ prompt: content }),
        session_id: currentSessionId,
        bearer_token: bearerToken || undefined,
        user_id: userId || undefined,
      });
      console.log({ response });

      const agentMessage: Message = {
        id: `agent-${Date.now()}`,
        role: "agent",
        content:
          typeof response.response === "string"
            ? response.response
            : JSON.stringify(response.response, null, 2),
        timestamp: new Date(response.timestamp),
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (err) {
      console.error(err);
      setErrorToast(
        err instanceof Error ? err.message : "Failed to send message"
      );
    }
  };

  const handleNewConversation = async () => {
    try {
      const response = await newSessionMutation.mutateAsync();
      sessionStorage.setSessionId(response.session_id);
      setMessages([]);
      // Refetch config to update session ID
      refetch();
    } catch (err) {
      setErrorToast(
        err instanceof Error ? err.message : "Failed to create new session"
      );
    }
  };

  const handleCopySessionId = async () => {
    try {
      await navigator.clipboard.writeText(currentSessionId);
      setCopiedSessionId(true);
      setTimeout(() => setCopiedSessionId(false), 2000);
    } catch (err) {
      console.error("Failed to copy session ID:", err);
    }
  };

  if (isLoading) {
    return <LoadingSpinner size="lg" text="Loading configuration..." />;
  }

  if (error) {
    return (
      <ErrorDisplay
        message={
          error instanceof Error
            ? error.message
            : "Failed to load configuration"
        }
        onRetry={() => refetch()}
      />
    );
  }

  if (!config) {
    return <ErrorDisplay message="No configuration available" />;
  }

  // Check if OAuth token is required but not provided
  const isOAuthRequired = config.auth_method === "oauth";
  const isUserIdSupported =
    config.auth_method === "iam" || config.auth_method === "none";
  const canSendMessages = !isOAuthRequired || bearerToken.length > 0;

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">Chat</h1>
            <div className="flex items-center gap-2 mt-1">
              <p className="text-sm text-gray-500">
                Session: {currentSessionId.slice(0, 16)}...
              </p>
              <button
                onClick={handleCopySessionId}
                className="text-gray-400 hover:text-gray-600 transition-colors p-1"
                title="Copy full session ID"
              >
                {copiedSessionId ? (
                  <Check className="w-3 h-3 text-green-600" />
                ) : (
                  <Copy className="w-3 h-3" />
                )}
              </button>
            </div>
          </div>
          <NewConversationButton
            onClick={handleNewConversation}
            disabled={newSessionMutation.isPending}
          />
        </div>
      </div>

      {/* Config Panel - Collapsible */}
      <div className="bg-white border-b border-gray-200">
        <ConfigPanel
          config={{
            ...config,
            session_id: currentSessionId,
          }}
        />
      </div>

      {/* OAuth Token Input - Show when OAuth is required */}
      {isOAuthRequired && (
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <OAuthTokenInput
            onTokenChange={setBearerToken}
            currentToken={bearerToken}
            isCollapsed={isTokenInputCollapsed}
            onToggleCollapse={() =>
              setIsTokenInputCollapsed(!isTokenInputCollapsed)
            }
          />
        </div>
      )}

      {/* User ID Input - Show when IAM or local auth is used */}
      {isUserIdSupported && (
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <UserIdInput
            onUserIdChange={setUserId}
            currentUserId={userId}
            isCollapsed={isUserIdInputCollapsed}
            onToggleCollapse={() =>
              setIsUserIdInputCollapsed(!isUserIdInputCollapsed)
            }
          />
        </div>
      )}

      {/* Chat Area */}
      {messages.length === 0 ? (
        /* Empty state - centered input */
        <div className="flex-1 flex flex-col items-center justify-center px-6 bg-white">
          <div className="w-full max-w-3xl">
            <MessageInput
              onSend={handleSendMessage}
              isLoading={invokeMutation.isPending}
              disabled={!canSendMessages}
              placeholder={
                isOAuthRequired && !bearerToken
                  ? "Enter bearer token above to send messages..."
                  : undefined
              }
              onFocus={() => {
                if (isOAuthRequired) setIsTokenInputCollapsed(true);
                if (isUserIdSupported) setIsUserIdInputCollapsed(true);
              }}
            />
          </div>
        </div>
      ) : (
        /* Messages view - input at bottom */
        <div className="flex-1 overflow-hidden flex flex-col">
          <div className="flex-1 overflow-y-auto px-6 py-4 bg-white">
            <ChatView
              messages={messages}
              isLoading={invokeMutation.isPending}
            />
          </div>

          {/* Message Input - Fixed at bottom */}
          <div className="bg-white border-t border-gray-200 px-6 py-4">
            <MessageInput
              onSend={handleSendMessage}
              isLoading={invokeMutation.isPending}
              disabled={!canSendMessages}
              placeholder={
                isOAuthRequired && !bearerToken
                  ? "Enter bearer token above to send messages..."
                  : undefined
              }
              onFocus={() => {
                if (isOAuthRequired) setIsTokenInputCollapsed(true);
                if (isUserIdSupported) setIsUserIdInputCollapsed(true);
              }}
            />
          </div>
        </div>
      )}

      {errorToast && (
        <ErrorToast
          message={errorToast}
          onClose={() => setErrorToast(null)}
          onRetry={() => {
            setErrorToast(null);
            if (messages.length > 0) {
              const userMessages = messages.filter((m) => m.role === "user");
              const lastUserMessage = userMessages.at(-1);
              if (lastUserMessage) {
                handleSendMessage(lastUserMessage.content);
              }
            }
          }}
        />
      )}
    </div>
  );
}
