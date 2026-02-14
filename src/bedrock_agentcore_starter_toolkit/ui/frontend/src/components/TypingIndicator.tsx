export function TypingIndicator() {
  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[70%]">
        <div className="bg-gray-100 text-gray-900 rounded-full px-4 py-3">
          <div className="flex items-center space-x-2">
            <div className="flex space-x-1">
              <div
                className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                style={{ animationDelay: "0ms" }}
              ></div>
              <div
                className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                style={{ animationDelay: "150ms" }}
              ></div>
              <div
                className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                style={{ animationDelay: "300ms" }}
              ></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
