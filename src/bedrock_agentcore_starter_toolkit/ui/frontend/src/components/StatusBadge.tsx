import type { StrategyStatus } from "../types";

interface StatusBadgeProps {
  status: string | StrategyStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "active":
        return "bg-green-100 text-green-800";
      case "creating":
        return "bg-yellow-100 text-yellow-800";
      case "failed":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(
        status
      )}`}
    >
      {status}
    </span>
  );
}
