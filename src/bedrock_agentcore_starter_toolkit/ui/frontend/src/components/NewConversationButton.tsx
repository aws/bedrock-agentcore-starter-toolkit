import { Plus } from "lucide-react";

interface NewConversationButtonProps {
  onClick: () => void;
  disabled?: boolean;
}

export function NewConversationButton({
  onClick,
  disabled = false,
}: NewConversationButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
    >
      <Plus className="w-4 h-4 mr-2" />
      New Conversation
    </button>
  );
}
