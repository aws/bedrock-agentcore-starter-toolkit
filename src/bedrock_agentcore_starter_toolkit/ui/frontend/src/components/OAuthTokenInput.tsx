/**
 * OAuthTokenInput component for entering bearer tokens.
 *
 * Displayed when the agent uses OAuth authentication.
 * Users must provide a valid bearer token before sending messages.
 * Collapses automatically when user focuses on the message input.
 */

import { useState } from "react";
import { Key, Eye, EyeOff, ChevronDown, ChevronUp } from "lucide-react";

interface OAuthTokenInputProps {
  onTokenChange: (token: string) => void;
  currentToken?: string;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function OAuthTokenInput({
  onTokenChange,
  currentToken = "",
  isCollapsed = false,
  onToggleCollapse,
}: OAuthTokenInputProps) {
  const [token, setToken] = useState(currentToken);
  const [showToken, setShowToken] = useState(false);

  const handleTokenChange = (value: string) => {
    setToken(value);
    onTokenChange(value);
  };

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg overflow-hidden transition-all">
      {/* Header - Always visible */}
      <button
        type="button"
        onClick={onToggleCollapse}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-amber-100 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Key className="w-5 h-5 text-amber-600 flex-shrink-0" />
          <div className="text-left">
            <h3 className="text-sm font-medium text-amber-900">
              OAuth Authentication
            </h3>
            {token && (
              <p className="text-xs text-amber-600">
                ✓ Token provided ({token.length} characters)
              </p>
            )}
          </div>
        </div>
        {isCollapsed ? (
          <ChevronDown className="w-5 h-5 text-amber-600" />
        ) : (
          <ChevronUp className="w-5 h-5 text-amber-600" />
        )}
      </button>

      {/* Collapsible content */}
      {!isCollapsed && (
        <div className="px-4 pb-4 pt-1">
          <p className="text-xs text-amber-700 mb-3">
            This agent uses OAuth authentication. Please enter your bearer token
            to send messages.
          </p>
          <div className="relative">
            <input
              type={showToken ? "text" : "password"}
              value={token}
              onChange={(e) => handleTokenChange(e.target.value)}
              placeholder="Enter bearer token..."
              className="w-full px-3 py-2 pr-10 text-sm border border-amber-300 rounded-md focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent"
            />
            <button
              type="button"
              onClick={() => setShowToken(!showToken)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-amber-600 hover:text-amber-800 transition-colors"
              title={showToken ? "Hide token" : "Show token"}
            >
              {showToken ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
