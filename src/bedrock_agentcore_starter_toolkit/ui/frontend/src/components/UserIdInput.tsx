/**
 * UserIdInput component for entering user ID.
 *
 * Displayed when the agent uses IAM or local authentication.
 * Users can optionally provide a user ID to be sent as runtimeUserId.
 * Collapses automatically when user focuses on the message input.
 */

import { useState } from "react";
import { User, ChevronDown, ChevronUp } from "lucide-react";

interface UserIdInputProps {
  onUserIdChange: (userId: string) => void;
  currentUserId?: string;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function UserIdInput({
  onUserIdChange,
  currentUserId = "",
  isCollapsed = false,
  onToggleCollapse,
}: UserIdInputProps) {
  const [userId, setUserId] = useState(currentUserId);

  const handleUserIdChange = (value: string) => {
    setUserId(value);
    onUserIdChange(value);
  };

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg overflow-hidden transition-all">
      {/* Header - Always visible */}
      <button
        type="button"
        onClick={onToggleCollapse}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-blue-100 transition-colors"
      >
        <div className="flex items-center gap-3">
          <User className="w-5 h-5 text-blue-600 flex-shrink-0" />
          <div className="text-left">
            <h3 className="text-sm font-medium text-blue-900">
              User ID (Optional)
            </h3>
            {userId && (
              <p className="text-xs text-blue-600">✓ User ID: {userId}</p>
            )}
          </div>
        </div>
        {isCollapsed ? (
          <ChevronDown className="w-5 h-5 text-blue-600" />
        ) : (
          <ChevronUp className="w-5 h-5 text-blue-600" />
        )}
      </button>

      {/* Collapsible content */}
      {!isCollapsed && (
        <div className="px-4 pb-4 pt-1">
          <p className="text-xs text-blue-700 mb-3">
            Optionally specify a user ID to be sent as runtimeUserId parameter.
          </p>
          <div className="relative">
            <input
              type="text"
              value={userId}
              onChange={(e) => handleUserIdChange(e.target.value)}
              placeholder="Enter user ID..."
              className="w-full px-3 py-2 text-sm border border-blue-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
      )}
    </div>
  );
}
