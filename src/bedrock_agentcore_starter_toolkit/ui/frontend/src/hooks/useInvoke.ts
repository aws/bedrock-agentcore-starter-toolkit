import { useMutation } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { InvokeRequest } from "../types";

/**
 * Custom hook for invoking the agent with a message.
 *
 * Uses TanStack Query's useMutation to handle the async invocation,
 * providing loading states, error handling, and response data.
 *
 * @returns Mutation object with mutate function, loading state, and response data
 *
 * @example
 * const invoke = useInvoke();
 * invoke.mutate({ message: "Hello", session_id: "123" });
 */
export function useInvoke() {
  return useMutation({
    mutationFn: (data: InvokeRequest) => apiClient.invoke(data),
  });
}
