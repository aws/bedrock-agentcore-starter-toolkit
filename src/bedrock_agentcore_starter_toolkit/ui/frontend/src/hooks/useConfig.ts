import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";

/**
 * Custom hook for fetching agent configuration.
 *
 * Retrieves the current agent configuration including connection mode,
 * agent details, authentication method, and session ID. The configuration
 * is cached indefinitely (staleTime: Infinity) since it doesn't change
 * during the application lifecycle.
 *
 * @returns Query object with configuration data, loading state, and error information
 *
 * @example
 * const { data: config, isLoading } = useConfig();
 * console.log(config.mode); // "local" or "remote"
 */
export function useConfig() {
  return useQuery({
    queryKey: ["config"],
    queryFn: () => apiClient.getConfig(),
    staleTime: Infinity, // Config doesn't change during app lifecycle
    retry: 3, // Retry up to 3 times on failure
  });
}
