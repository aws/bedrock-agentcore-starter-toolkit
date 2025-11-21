import { useState } from "react";
import type { AgentConfig } from "../types";
import { Server, Bot, Key, ChevronDown, ChevronUp } from "lucide-react";

interface ConfigPanelProps {
  config: AgentConfig;
}

export function ConfigPanel({ config }: ConfigPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="px-6 py-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between w-full text-left"
      >
        <div className="flex items-center space-x-4">
          <span className="text-sm font-medium text-gray-700">
            Configuration
          </span>
          <div className="flex items-center space-x-3 text-xs text-gray-500">
            <span className="flex items-center">
              <Server className="w-3 h-3 mr-1" />
              {config.mode}
            </span>
            <span className="flex items-center">
              <Bot className="w-3 h-3 mr-1" />
              {config.agent_name}
            </span>
            <span className="flex items-center">
              <Key className="w-3 h-3 mr-1" />
              {config.auth_method}
            </span>
          </div>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {isExpanded && (
        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4 pb-2">
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1">Mode</p>
            <p className="text-sm text-gray-900 capitalize">{config.mode}</p>
          </div>

          <div>
            <p className="text-xs font-medium text-gray-500 mb-1">Agent Name</p>
            <p className="text-sm text-gray-900">{config.agent_name}</p>
          </div>

          {config.region && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">Region</p>
              <p className="text-sm text-gray-900">{config.region}</p>
            </div>
          )}

          <div>
            <p className="text-xs font-medium text-gray-500 mb-1">
              Authentication
            </p>
            <p className="text-sm text-gray-900 uppercase">
              {config.auth_method}
            </p>
          </div>

          {config.agent_arn && (
            <div className="md:col-span-2">
              <p className="text-xs font-medium text-gray-500 mb-1">
                Agent ARN
              </p>
              <p className="text-sm text-gray-900 font-mono truncate">
                {config.agent_arn}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
