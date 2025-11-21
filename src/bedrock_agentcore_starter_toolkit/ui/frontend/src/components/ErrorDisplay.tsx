import { AlertCircle } from "lucide-react";

interface ErrorDisplayProps {
  message: string;
  onRetry?: () => void;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || undefined;

export function ErrorDisplay({ message, onRetry }: ErrorDisplayProps) {
  return (
    <div className="p-4">
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-start">
          <AlertCircle className="w-5 h-5 text-red-600 mr-3 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-red-900 mb-1">Error</h3>
            <p className="text-sm text-red-700 mb-2">
              An error occurred while fetching data from the API at{" "}
              {API_BASE_URL ?? "/"}.
            </p>
            <p className="text-sm text-red-700">{message}</p>
            {onRetry && (
              <button
                onClick={onRetry}
                className="mt-3 px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 transition-colors"
              >
                Try Again
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
