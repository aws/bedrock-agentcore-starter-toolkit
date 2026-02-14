import { MemoryView } from "../components/MemoryView";
import { ErrorDisplay } from "../components/ErrorDisplay";
import { SkeletonLoader } from "../components/SkeletonLoader";
import { useMemory } from "../hooks/useMemory";

export function MemoryPage() {
  const { data: memory, isLoading, error, refetch } = useMemory();

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-semibold text-gray-900">Memory</h1>
        <p className="text-sm text-gray-500 mt-1">
          View and manage agent memory resources
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {isLoading ? (
          <SkeletonLoader />
        ) : error ? (
          <ErrorDisplay
            message={
              error instanceof Error
                ? error.message
                : "Failed to load memory information"
            }
            onRetry={() => refetch()}
          />
        ) : !memory ? (
          <div className="bg-white border border-gray-200 rounded-lg p-8 text-center">
            <p className="text-gray-600">
              No memory resource configured for this agent.
            </p>
          </div>
        ) : (
          <MemoryView memory={memory} />
        )}
      </div>
    </div>
  );
}
