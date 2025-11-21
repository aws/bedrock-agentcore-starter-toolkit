import { AlertCircle, X } from "lucide-react";

interface ErrorToastProps {
  message: string;
  onClose: () => void;
  onRetry?: () => void;
}

export function ErrorToast({ message, onClose, onRetry }: ErrorToastProps) {
  return (
    <div className="fixed bottom-4 right-4 max-w-md bg-red-50 border border-red-200 rounded-lg shadow-lg p-4 animate-slide-up">
      <div className="flex items-start">
        <AlertCircle className="w-5 h-5 text-red-600 mr-3 mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-red-900 mb-1">Error</h3>
          <p className="text-sm text-red-700">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-2 text-sm font-medium text-red-600 hover:text-red-800"
            >
              Retry
            </button>
          )}
        </div>
        <button
          onClick={onClose}
          className="ml-3 text-red-400 hover:text-red-600"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}
