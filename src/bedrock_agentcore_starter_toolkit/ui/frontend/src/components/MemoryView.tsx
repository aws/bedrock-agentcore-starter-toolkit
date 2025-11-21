import type { MemoryResource } from "../types";
import { StatusBadge } from "./StatusBadge";
import { MemoryStrategyCard } from "./MemoryStrategyCard";
import { Database, Calendar, Tag } from "lucide-react";

interface MemoryViewProps {
  memory: MemoryResource;
}

export function MemoryView({ memory }: MemoryViewProps) {
  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-1">
              {memory.name}
            </h3>
            <p className="text-sm text-gray-500 font-mono">
              {memory.memory_id}
            </p>
          </div>
          <StatusBadge status={memory.status} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <div className="flex items-start">
            <Calendar className="w-5 h-5 text-gray-400 mr-3 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-gray-500">Event Expiry</p>
              <p className="text-sm text-gray-900">
                {memory.event_expiry_days} days
              </p>
            </div>
          </div>

          <div className="flex items-start">
            <Tag className="w-5 h-5 text-gray-400 mr-3 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-gray-500">Memory Type</p>
              <p className="text-sm text-gray-900 capitalize">
                {memory.memory_type.replace(/-/g, " ")}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center mb-4">
          <Database className="w-5 h-5 text-gray-700 mr-2" />
          <h3 className="text-lg font-semibold text-gray-900">
            Memory Strategies
          </h3>
          <span className="ml-2 text-sm text-gray-500">
            ({memory.strategies.length})
          </span>
        </div>

        <div className="space-y-3">
          {memory.strategies.map((strategy) => (
            <MemoryStrategyCard key={strategy.strategyId} strategy={strategy} />
          ))}
        </div>
      </div>
    </div>
  );
}
