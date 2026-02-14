import { useMutation } from "@tanstack/react-query";
import { apiClient } from "../api/client";

/**
 * Custom hook for creating a new conversation session.
 *
 * Generates a new session ID on the backend and returns it.
 * This is used when the user clicks "New Conversation" to start
 * a fresh conversation context with the agent.
 *
 * @returns Mutation object with mutate function and new session ID
 *
 * @example
 * const newSession = useNewSession();
 * newSession.mutate(undefined, {
 *   onSuccess: (data) => console.log("New session:", data.session_id)
 * });
 */
export function useNewSession() {
  return useMutation({
    mutationFn: () => apiClient.createNewSession(),
  });
}
