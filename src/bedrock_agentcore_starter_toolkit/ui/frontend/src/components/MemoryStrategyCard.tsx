import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { MemoryStrategy } from "../types";
import { StatusBadge } from "./StatusBadge";

interface MemoryStrategyCardProps {
  strategy: MemoryStrategy;
}

export function MemoryStrategyCard({ strategy }: MemoryStrategyCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors">
      <div
        className="flex items-start justify-between cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <h4 className="text-sm font-semibold text-gray-900">
              {strategy.name}
            </h4>
            <StatusBadge status={strategy.status} />
          </div>
          <p className="text-xs text-gray-500 mb-1">
            Type: <span className="font-medium">{strategy.type}</span>
          </p>
          {strategy.description && (
            <p className="text-sm text-gray-600 mt-2">{strategy.description}</p>
          )}
        </div>
        <button className="ml-4 text-gray-400 hover:text-gray-600">
          {isExpanded ? (
            <ChevronDown className="w-5 h-5" />
          ) : (
            <ChevronRight className="w-5 h-5" />
          )}
        </button>
      </div>

      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="space-y-3">
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">
                Strategy ID
              </p>
              <p className="text-sm text-gray-900 font-mono break-all">
                {strategy.strategyId}
              </p>
            </div>

            {strategy.namespaces && strategy.namespaces.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 mb-1">
                  Namespaces
                </p>
                <div className="flex flex-wrap gap-2">
                  {strategy.namespaces.map((namespace, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-2 py-1 rounded bg-blue-50 text-blue-700 text-xs font-medium"
                    >
                      {namespace}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {strategy.configuration && (
              <div>
                <p className="text-xs font-medium text-gray-500 mb-1">
                  Configuration
                </p>
                <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto">
                  {JSON.stringify(strategy.configuration, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
